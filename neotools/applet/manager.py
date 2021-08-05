import logging
from usb.core import USBError

from neotools.applet.applet import read_applet_list
from neotools.file import read_extended_data

from neotools.device import get_available_space

from neotools.applet.constants import *
from neotools.message import Message, MessageConst, send_message, receive_message
from neotools.util import calculate_data_checksum, NeotoolsError, data_from_buf, int_from_buf

logger = logging.getLogger(__name__)


# This function can also install ROM. I haven't tried it though.
# For proper ROM installation it may be necessary to clean segments.
def install_applet(device, content: bytes, force=False):
    applet_type = classify_applet(content)

    if applet_type != AppletType.REGULAR:
        raise NeotoolsError(
            f'This is a ROM file for {applet_type_to_str(applet_type)}. ' +
            f'Installing ROM has never been tried and can brick your device.')

    logger.debug(f'Type of applet {applet_type_to_str(applet_type)}')

    if applet_type == AppletType.REGULAR:
        header = data_from_buf(APPLET_HEADER_FORMAT, content[0: APPLET_HEADER_FORMAT['size']])

        if not force:
            applet_list = read_applet_list(device)
            if any(header['applet_id'] == applet['applet_id'] for applet in applet_list):
                raise NeotoolsError(f'Applet {header["name"]} is already installed')

        required_size = header['ram_size'] + header['file_space']
        required_rom_size = header['rom_size']

        available_space = get_available_space(device)
        logger.info(f'Applet details\n{header}')
        logger.info(f'available_space={available_space}')

        # NEO Manager uses 0xff000000
        if required_rom_size > 0xff000000 or required_rom_size > available_space['free_rom']:
            raise NeotoolsError('Required ROM size too big.')

        if required_size > 0xff000000 or required_size > available_space['free_ram']:
            raise NeotoolsError('Required RAM size too big.')

        print(f'Installing applet {header["name"]}')

        device.dialogue_start()

        print('Initialization for writing the applet')
        some_size_requirement = required_rom_size | (required_size & 0xffff0000) << 8
        message = Message(MessageConst.REQUEST_WRITE_APPLET, [
            (some_size_requirement, 1, 4), (required_size, 5, 2)])

        send_message(device, message, MessageConst.RESPONSE_WRITE_APPLET, timeout=5000)
        print('Initialized writing the applet')

        _write_applet_content(device, content)

        print('Finalizing writing the applet. This may take a minute')
        message = Message(MessageConst.REQUEST_FINALIZE_WRITING_APPLET, [])
        device.write(message.m_data, timeout=24000)

        # NeoManager has a loop receiving a message with condition on ENOMEM.
        # Perhaps that only matters for updating ROM.
        retry_count = 10
        while retry_count > 0:
            try:
                receive_message(device, MessageConst.RESPONSE_FINALIZE_WRITING_APPLET, timeout=5000)
            except USBError as e:
                logger.info(f'Waiting for finalization, {e}')
                pass  # likely this is a timeout
            retry_count -= 1

        print('Finalized writing the applet')


def _write_applet_content(device, content):
    print('Started writing applet content')

    remaining = len(content)
    offset = 0
    while remaining > 0:
        block_size = min(0x400, remaining)
        block = content[offset:offset + block_size]
        checksum = calculate_data_checksum(block)

        message = Message(MessageConst.REQUEST_BLOCK_WRITE, [(block_size, 1, 4), (checksum, 5, 2)])
        send_message(device, message, MessageConst.RESPONSE_BLOCK_WRITE, timeout=600)

        device.write(block, timeout=600)
        receive_message(device, MessageConst.RESPONSE_BLOCK_WRITE_DONE, timeout=300)

        message = Message(MessageConst.REQUEST_PROGRAMMING_APPLET_BLOCK, [])
        send_message(device, message, MessageConst.RESPONSE_PROGRAMMING_APPLET_BLOCK, timeout=5000)

        offset = offset + block_size
        remaining = remaining - block_size

    print('Completed writing applet content')


class ROMSignature:
    SYSTEM_3 = b'System 3          '
    OS3000_SMALL_ROM = b'OS 3000 Small ROM '
    ALPHASMART_UPDATER = b'AlphaSmart Updater'
    SYSTEM_3_NEO = b'System 3 Neo      '
    OS3KNEO_SMALL_ROM = b'OS 3KNeo Small ROM'


def applet_type_to_str(applet_type):
    mapping = {
        AppletType.REGULAR: 'Applet program',
        AppletType.SYSTEM_3: 'System 3',
        AppletType.OS3000_SMALL_ROM: 'OS3000 Small ROM',
        AppletType.ALPHASMART_UPDATER: 'Alphasmart Updater',
        AppletType.SYSTEM_3_NEO: 'System 3 Neo',
        AppletType.OS3KNEO_SMALL_ROM: 'OS3KNeo Small ROM'
    }
    if applet_type in mapping:
        return mapping[applet_type]
    else:
        raise NeotoolsError(f'Invalid applet type {applet_type}')


def classify_applet(content: bytes):
    if int_from_buf(content, 0, 4) == SIGNATURE_START:
        if int_from_buf(content, len(content) - 4, 4) != SIGNATURE_END:
            raise NeotoolsError('Invalid applet')
        else:
            return AppletType.REGULAR
    else:
        sig_string = content[0x400:0x412]
        if sig_string == ROMSignature.SYSTEM_3:
            return AppletType.SYSTEM_3
        elif sig_string == ROMSignature.OS3000_SMALL_ROM:
            return AppletType.OS3000_SMALL_ROM
        elif sig_string == ROMSignature.ALPHASMART_UPDATER:
            return AppletType.ALPHASMART_UPDATER
        elif sig_string == ROMSignature.SYSTEM_3_NEO:
            return AppletType.SYSTEM_3_NEO
        elif sig_string == ROMSignature.OS3KNEO_SMALL_ROM:
            return AppletType.OS3KNEO_SMALL_ROM
        else:
            raise NeotoolsError('Unknown type of applet')


def remove_applet(device, applet_id):
    logger.info(f'Removing applet {applet_id}.')
    device.dialogue_start()
    message = Message(MessageConst.REQUEST_REMOVE_APPLET, [(5, 1, 4), (applet_id, 5, 2)])
    send_message(device, message, success_code=MessageConst.RESPONSE_REMOVE_APPLET)
    device.dialogue_end()


def remove_applets(device):
    logger.info(f'Removing applets. This may take a minute.')
    device.dialogue_start()
    message = Message(MessageConst.REQUEST_ERASE_APPLETS, [])
    send_message(device, message, success_code=MessageConst.RESPONSE_RESPONSE_ERASE_APPLETS, timeout=90000)
    device.dialogue_end()


def fetch_applet(device, applet_id):
    logger.info(f'Retrieving applet {applet_id}')
    device.dialogue_start()

    message = Message(MessageConst.REQUEST_READ_APPLET, [
        (0, 1, 4), (applet_id, 5, 2)])

    response = send_message(device, message, MessageConst.RESPONSE_READ_FILE)
    size = response.argument(1, 4)

    content = read_extended_data(device, size)

    device.dialogue_end()
    return content
