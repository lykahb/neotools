import logging
from collections import OrderedDict

from alphatools.message import Message, MessageConst, send_message, assert_success
from alphatools.util import calculate_data_checksum, AlphatoolsError, data_from_buf

logger = logging.getLogger(__name__)

# Applet fields with offset and width in to the applet header data 
# (usually located at the start of the applet).
APPLET_HEADER_FORMAT = {
    'size': 0x84,  # The total size of the header
    'fields': OrderedDict([
        ('signature', (0x00, 4, int)),  # Byte offset of the signature word field.
        ('rom_size', (0x04, 4, int)),  # Byte offset of the ROM size field.
        ('ram_size', (0x08, 4, int)),  # Byte offset of the size of working RAM field.
        ('settings_offset', (0x0c, 4, int)),  # Byte offset settings parameters field.
        ('flags', (0x10, 4, int)),  # Byte offset of the flags field.
        ('applet_id', (0x14, 2, int)),  # Byte offset of the applet ID field.
        ('header_version', (0x16, 1, int)),  # Byte offset of the Header version code field.
        ('file_count', (0x17, 1, int)),  # Byte offset of the file count field.
        ('name', (0x18, 36, str)),  # Byte offset of the display name.
        ('version_major', (0x3c, 1, int)),  # Byte offset of the Major version number field.
        ('version_minor', (0x3d, 1, int)),  # Minor version number field.
        ('version_revision', (0x3e, 1, int)),  # Revision code (ASCII) field.
        ('language_id', (0x3f, 1, int)),  # Localised language field.
        ('info', (0x40, 60, str)),  # The info (copyright) string field.
        ('min_asm_version', (0x7c, 4, int)),  # Minimum AlphaSmart Manager version required field.
        ('file_space', (0x80, 4, int)),  # The required file space field.
    ])}

SIGNATURE = 0xc0ffeead  # The expected value of the signature word.#

# Known applet flags:
# *
# *  AlphaWord:      0xff0000ce      1100.1110
# *  KAZ:            0xff000000      0000.0000
# *  Calculator:     0xff000000      0000.0000
# *  Beamer:         0xff000000      0000.0000
# *  Control Panel:  0xff000080      1000.0000
# *  Spell Check:    0xff000001      0000.0001
# *  Thesaurus:      0xff000001      0000.0001
# *  Font files:     0xff000031      0011.0001
# *  System:         0xff000011      0001.0001

FLAGS_HIDDEN = 0x01  # If set, the applet is hidden.#

# Reading more than 7 headers will cause a crash on some Neos (1k buffer overflow?)
LIST_APPLETS_REQUEST_COUNT = 7


class AppletIds:
    INVALID = 0xffff
    SYSTEM = 0X000  # OS applet id
    ALPHAWORD = 0xa000
    DICTIONARY = 0xa005


class Applet:
    @staticmethod
    def from_raw_header(buf):
        applet = data_from_buf(APPLET_HEADER_FORMAT, buf)
        if applet['signature'] != SIGNATURE:
            raise AlphatoolsError('Invalid applet signature %s', applet['signature'])

        return applet


def read_applets(device):
    applets = []
    logger.info('Retrieving applets')
    device.dialogue_start()
    header_size = APPLET_HEADER_FORMAT['size']
    while True:
        buf = raw_read_applet_headers(device, len(applets))
        header_count = int(len(buf) / header_size)
        for index in range(0, header_count):
            applet_raw = buf[index * header_size:(index + 1) * header_size]
            applet = Applet.from_raw_header(applet_raw)
            applets.append(applet)
        if header_count < LIST_APPLETS_REQUEST_COUNT:
            break
    device.dialogue_end()
    return applets


# returns a list of installed applets
def raw_read_applet_headers(device, index):
    header_size = APPLET_HEADER_FORMAT['size']
    message = Message(MessageConst.REQUEST_LIST_APPLETS, [
        (index, 1, 4), (LIST_APPLETS_REQUEST_COUNT, 5, 2)])
    response = send_message(device, message)
    size = response.argument(1, 4)
    expected_checksum = response.argument(5, 2)
    if size > LIST_APPLETS_REQUEST_COUNT * header_size:
        raise AlphatoolsError('rawReadAppletHeaders: reply will return too much data!')

    if size == 0:
        return []

    buf = device.read(size)
    if len(buf) % header_size != 0:
        logger.warning(
            'rawReadAppletHeaders: read returned a partial header (expected header size %s, bytes read %s',
            header_size, len(buf))
    if calculate_data_checksum(buf) != expected_checksum:
        raise AlphatoolsError('rawReadAppletHeaders: data checksum error')
    return buf


def get_applet_resource_usage(device, applet_id):
    device.dialogue_start()
    message = Message(MessageConst.REQUEST_GET_USED_SPACE, [(0x00000001, 1, 4), (applet_id, 5, 2)])
    response = send_message(device, message)
    assert_success(response, MessageConst.RESPONSE_GET_USED_SPACE)
    result = {
        'ram': response.argument(1, 4),
        'file_count': response.argument(5, 2)
    }
    device.dialogue_end()
    return result
