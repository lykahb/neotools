import logging
from collections import OrderedDict
from contextlib import contextmanager
from time import sleep

import usb.core
from usb import util

from neotools.applet.constants import AppletIds
from neotools.message import Message, MessageConst, send_message
from neotools.util import NeotoolsError, calculate_data_checksum, data_from_buf

logger = logging.getLogger(__name__)

VENDOR_ID = 0x081e  # USB Vendor ID for the Neo, operating as a keyboard.
HID_PRODUCT_ID = 0xbd04  # USB Product ID for the Neo, operating as a keyboard.
COM_PRODUCT_ID = 0xbd01  # USB Product ID for the Neo, operating as a comms device
HUB_PRODUCT_ID = 0x0100
PROTOCOL_VERSION = 0x0230  # Minimum ASM protocol version that the device must support.


class Device:
    def __init__(self, dev):
        self.dev = dev
        self.in_endpoint = None
        self.out_endpoint = None
        self.is_kernel_driver_detached = None
        self.original_product = dev.idProduct

    @staticmethod
    @contextmanager
    def connect(flip_to_comms=True, dispose=True):
        device = None
        try:
            device = Device(Device.find())
            device.init(flip_to_comms)
            yield device
        except Exception as e:
            logger.exception(e)
        finally:
            if device and dispose:
                device.dispose()

    @staticmethod
    def find():
        logger.debug('Searching for device')
        devices = list(usb.core.find(find_all=True, idVendor=VENDOR_ID))
        if len(devices) == 0:
            raise NeotoolsError('Device not found')
        elif len(devices) > 1:
            raise NeotoolsError('More than one device is connected')
        return devices[0]

    def init(self, flip_to_comms=True):
        self.is_kernel_driver_detached = False
        if flip_to_comms and self.dev.idProduct == HID_PRODUCT_ID:
            if self.dev.is_kernel_driver_active(0):
                logger.debug('Detaching kernel driver')
                self.dev.detach_kernel_driver(0)
                self.is_kernel_driver_detached = True
            self.flip_to_comms_mode()
            util.dispose_resources(self.dev)
            self.dev = None
            logger.debug('Connecting to Neo in communication mode')
            while self.dev is None:
                sleep(0.1)
                self.dev = usb.core.find(idVendor=VENDOR_ID, idProduct=COM_PRODUCT_ID)

        if self.dev.idProduct == COM_PRODUCT_ID:
            cfg = self.dev[0]
            intf = cfg[(0, 0)]
            endpoints = intf.endpoints()

            def get_endpoint(direction):
                def predicate(ep):
                    return \
                        util.endpoint_type(ep.bmAttributes) == util.ENDPOINT_TYPE_BULK and \
                        util.endpoint_direction(ep.bEndpointAddress) == direction
                eps = list(filter(predicate, endpoints))
                if len(eps) == 0:
                    raise NeotoolsError('Cannot find endpoint with direction %s' % direction)
                return eps[0]

            self.in_endpoint = get_endpoint(util.ENDPOINT_IN)
            self.out_endpoint = get_endpoint(util.ENDPOINT_OUT)

    def dispose(self):
        if self.original_product == HID_PRODUCT_ID and self.dev.idProduct == COM_PRODUCT_ID:
            self.flip_to_keyboard_mode()

    def flip_to_comms_mode(self):
        logger.debug('Switching Neo to communication mode')
        # There is black magic here - the sequences used are not documented, but determined from a bus trace.
        self.dev.set_configuration()
        for i in [0xe0, 0xe1, 0xe2, 0xe3, 0xe4]:
            self.dev.ctrl_transfer(
                bmRequestType=util.CTRL_OUT | util.CTRL_TYPE_CLASS | util.CTRL_RECIPIENT_DEVICE,
                bRequest=9,  # SET_CONFIGURATION
                wValue=(0x02 << 8) | 0,  # report type and ID
                wIndex=1,  # interface
                data_or_wLength=[i]  # report value
            )

    def flip_to_keyboard_mode(self):
        logger.debug('Switching Neo to keyboard mode')
        self.dialogue_start()
        restart(self)
        self.dialogue_end()

    def read(self, length, timeout=None):
        if timeout is None:
            timeout = 1000
        result = []
        remaining = length
        while remaining > 0:
            block_size = min(8, remaining)
            buf = self.in_endpoint.read(block_size, timeout=timeout)
            result.extend(buf)
            remaining = remaining - len(buf)
            if len(buf) != 8:
                break  # terminate loop on a short read
        return bytes(result)

    def write(self, message, timeout=None):
        if timeout is None:
            timeout = 1000
        length = len(message)
        message_offset = 0

        while message_offset != length:
            block_size = min(8, length - message_offset)
            block = message[message_offset:message_offset + block_size]
            self.out_endpoint.write(block, timeout=timeout)
            message_offset = message_offset + block_size

    def dialogue_start(self, applet_id=AppletIds.SYSTEM):
        self.hello()
        self.reset()
        self.switch_applet(applet_id)

    def dialogue_end(self):
        self.reset()

    def reset(self):
        """ Reset the device to a known state. Succeeds if device is supported and working correctly. """
        command_request_reset = b'?\xff\x00reset'
        self.write(command_request_reset)

    def switch_applet(self, applet_id):
        applet_id_bytes = applet_id.to_bytes(length=2, byteorder='big')
        command_request_switch = [0x3f, 0x53, 0x77, 0x74, 0x63, 0x68, applet_id_bytes[0],
                                  applet_id_bytes[1]]  # '?SwtchXX'
        command_response_switched = b'Switched'

        self.write(command_request_switch)
        response = self.read(8)
        if response != command_response_switched:
            raise NeotoolsError('Failed to switch to applet %s' % applet_id)

    def hello(self):
        """Ping the device for the ASM protocol version number. This will put the Neo in
         to ASM mode and also return the protocol version. It is also used as a keep-alive
         test.
         """
        retries = 10
        buf = []
        while retries > 0:
            self.write([0x01], timeout=100)  # ascCommandRequestProtocol
            buf = self.read(8, timeout=100)
            if len(buf) == 2:
                break  # success
            logger.debug('Unexpected byte response %s', buf)
            retries = retries - 1
            self.reset()
            sleep(0.1)  # seconds
        if retries < 0:
            raise NeotoolsError("This device doesn't look like it wants to talk to us - bailing out.")

        version = int.from_bytes(buf[0:2], byteorder='big')
        if version < PROTOCOL_VERSION:
            raise NeotoolsError('ASM protocol version not supported: %s' % version)


def get_available_space(device):
    device.dialogue_start()
    message = Message(MessageConst.REQUEST_GET_AVAIL_SPACE, [])
    response = send_message(device, message, MessageConst.RESPONSE_GET_AVAIL_SPACE)
    result = {
        'free_rom': response.argument(1, 4),
        'free_ram': response.argument(5, 2) * 256
    }
    device.dialogue_end()
    return result


def restart(device):
    message = Message(MessageConst.REQUEST_RESTART, [])
    send_message(device, message, MessageConst.RESPONSE_RESTART)


REVISION_FORMAT = {
    'size': None,
    'fields': OrderedDict([
        ('unknown', (0x00, 3, int)),
        ('revision_major', (0x04, 1, int)),
        ('revision_minor', (0x05, 1, int)),
        ('name', (0x06, 19, str)),
        ('build_date', (0x19, 39, str))
    ])
}


def get_version(device):
    device.dialogue_start()
    message = Message(MessageConst.REQUEST_VERSION, [])
    response = send_message(device, message, MessageConst.RESPONSE_VERSION)
    size = response.argument(1, 4)
    expected_checksum = response.argument(5, 2)

    buf = device.read(size)
    checksum = calculate_data_checksum(buf)
    if calculate_data_checksum(buf) == expected_checksum:
        # OS 3.6 Neo device appear to calculate the checksum wrongly (off by one error?)
        logger.debug(f'Ignoring data checksum error. Wanted {expected_checksum}, got {checksum}')
    device.dialogue_end()
    return data_from_buf(REVISION_FORMAT, buf)
