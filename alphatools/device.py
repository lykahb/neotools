import logging
from time import sleep

import usb.core
from usb import util

from alphatools.applet import AppletIds
logger = logging.getLogger(__name__)

HID_VENDOR_ID = 0x081e  # USB Vendor ID for the Neo, operating as a keyboard.
HID_PRODUCT_ID = 0xbd04  # USB Product ID for the Neo, operating as a keyboard.
COM_VENDOR_ID = 0x081e  # USB Vendor ID for the Neo, operating as a comms device.
COM_PRODUCT_ID = 0xbd01  # USB Product ID for the Neo, operating as a comms device
PROTOCOL_VERSION = 0x0230  # Minimum ASM protocol version that the device must support.


class Device:
    def __init__(self, dev, in_endpoint, out_endpoint):
        self.dev = dev
        self.in_endpoint = in_endpoint
        self.out_endpoint = out_endpoint

    @staticmethod
    def init():
        devices = usb.core.find(find_all=True, idVendor=HID_VENDOR_ID, idProduct=HID_PRODUCT_ID)

        if len(devices) == 0:
            raise ValueError('Device not found')
        elif len(devices) > 1:
            raise ValueError('More than one device is connected')
        dev = devices[0]

        Device.flip_to_comms_mode(dev)
        util.dispose_resources(dev)

        # Connect to comms device
        devices = usb.core.find(find_all=True, idVendor=HID_VENDOR_ID, idProduct=COM_PRODUCT_ID)
        cfg = dev[0]
        intf = cfg[(0, 0)]

        in_endpoint = None
        out_endpoint = None
        for endpoint in intf:
            type = util.endpoint_type(endpoint.bmAttributes)
            direction = util.endpoint_direction(endpoint.bEndpointAddress)
            if type != util.ENDPOINT_TYPE_BULK:
                continue

            if direction == util.ENDPOINT_IN and in_endpoint is None:
                in_endpoint = endpoint
            if direction == util.ENDPOINT_OUT and out_endpoint is None:
                out_endpoint = endpoint

        return Device(dev, in_endpoint, out_endpoint)

    @staticmethod
    def flip_to_comms_mode(dev):
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
        # There is black magic here - the sequences used are not documented, but determined from a bus trace.
        dev.set_configuration()
        for i in [0xe0, 0xe1, 0xe2, 0xe3, 0xe4]:
            dev.ctrl_transfer(
                bmRequestType=util.CTRL_OUT | util.CTRL_TYPE_CLASS | util.CTRL_RECIPIENT_DEVICE,
                bRequest=9,  # SET_CONFIGURATION
                wValue=(0x02 << 8) | 0,  # report type and ID
                wIndex=1,  # interface
                data_or_wLength=[i]  # report value
            )

    def read(self, length, timeout=None):
        result = []
        remaining = length
        while remaining > 0:
            blocksize = min(8, remaining)
            buf = self.in_endpoint.read(blocksize)
            result.extend(buf)
            remaining = remaining - len(buf)
        return result

    def write(self, message, timeout=None):
        length = len(message)
        message_offset = 0

        while message_offset != length:
            blocksize = min(8, length - message_offset)
            block = message[message_offset:message_offset + blocksize]
            self.out_endpoint.write(block)
            message_offset = message_offset + blocksize

    def dialogue_start(self, applet_id=AppletIds.SYSTEM):
        self.hello()
        self.reset()
        self.switch_applet(applet_id)

    def dialogue_end(self):
        self.reset()

    def reset(self):
        """ Reset the device to a known state. Succeeds if device is supported and working correctly. """
        command_request_reset = [0x3f, 0xff, 0x00, 0x72, 0x65, 0x73, 0x65, 0x74]
        self.write(command_request_reset)

    def switch_applet(self, applet_id):
        applet_id_bytes = applet_id.to_bytes(length=2, byteorder='big')
        command_request_switch = [0x3f, 0x53, 0x77, 0x74, 0x63, 0x68, applet_id_bytes[0], applet_id_bytes[1]]
        command_response_switched = [0x53, 0x77, 0x69, 0x74, 0x63, 0x68, 0x65, 0x64]

        self.write(command_request_switch)
        response = self.read(8)
        if response != command_response_switched:
            raise ValueError('Failed to switch to applet %s' % applet_id)

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
            logger.warning('Unexpected byte response %s', buf)
            retries = retries - 1
            self.reset()
            sleep(0.1)  # seconds
        if retries < 0:
            raise ValueError("This device doesn't look like it wants to talk to us - bailing out.")

        version = int.from_bytes(buf[0:2], byteorder='big')
        if version < PROTOCOL_VERSION:
            raise ValueError('ASM protocol version not supported: %s' % version)
