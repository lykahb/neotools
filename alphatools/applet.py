from collections import OrderedDict

from alphatools.message import RESPONSE_LIST_APPLETS, ASMessage

import logging
logger = logging.getLogger(__name__)

# Applet fields with offset and width in to the applet header data 
# (usually located at the start of the applet).
APPLET_HEADER_FORMAT = OrderedDict([
    ('signature', (0x00, 4)),  # Byte offset of the signature word field.
    ('rom_size', (0x04, 4)),  # Byte offset of the ROM size field.
    ('ram_size', (0x08, 4)),  # Byte offset of the size of working RAM field.
    ('settings_offset', (0x0c, 4)),  # Byte offset settings parameters field.
    ('flags', (0x10, 4)),  # Byte offset of the flags field.
    ('applet_id', (0x14, 2)),  # Byte offset of the applet ID field.
    ('header_version', (0x16, 1)),  # Byte offset of the Header version code field.
    ('file_count', (0x17, 1)),  # Byte offset of the  file count field.
    ('name', (0x18, 36)),  # Byte offset of the display name.
    ('version_major', (0x3c, 1)),  # Byte offset of the Major version number field.
    ('version_minor', (0x3d, 1)),  # Minor version number field.
    ('version_revision', (0x3e, 1)),  # Revision code (ASCII) field.
    ('language_id', (0x3f, 1)),  # Localised language field.
    ('info', (0x40, 60)),  # The info (copyright) string field.
    ('min_asm_version', (0x7c, 4)),  # Minimum AlphaSmart Manager version required field.
    ('file_space', (0x80, 4)),  # The required file space field.
])

HEADER_SIZE = 0x84  # The total size of the header.#

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
        string_fields = ['name', 'info']
        if len(buf) != HEADER_SIZE:
            raise ValueError('Invalid header size %s' % len(buf))

        applet = {
            k: int.from_bytes(buf[offset:width], byteorder='big', signed=False)
            for k, (offset, width) in APPLET_HEADER_FORMAT.items()
            if k not in string_fields
        }
        for k in string_fields:
            (offset, width) = APPLET_HEADER_FORMAT[k]
            applet[k] = str(buf[offset, width])

        if applet['signature'] != SIGNATURE:
            raise ValueError('Invalid applet signature %s', applet['signature'])

        return applet


def calculate_data_checksum(buf):
    return sum(buf) & 0xFFFF


def read_applets(device):
    applets = []
    # TODO: add dialog start/end
    while True:
        buf = raw_read_applet_headers(device, len(applets))
        header_count = int(len(buf) / HEADER_SIZE)
        for index in range(0, header_count):
            applet = Applet.from_raw_header(buf[index * HEADER_SIZE:HEADER_SIZE])
            applets.append(applet)
        if header_count < LIST_APPLETS_REQUEST_COUNT:
            break
    return applets


# returns a list of installed applets
def raw_read_applet_headers(device, index):
    message = ASMessage(RESPONSE_LIST_APPLETS, [{
        'value': index, 'offset': 1, 'width': 4
    }, {
        'value': LIST_APPLETS_REQUEST_COUNT, 'offset': 5, 'width': 2
    }])
    device.write(message.m_data)
    response = ASMessage.from_raw(device.read(8))
    size = response.argument(1, 4)
    expected_checksum = response.argument(5, 2)
    if size > LIST_APPLETS_REQUEST_COUNT * HEADER_SIZE:
        raise ValueError('rawReadAppletHeaders: reply will return too much data!')

    if size == 0:
        return []

    buf = device.read(size)
    if len(buf) % HEADER_SIZE != 0:
        logger.warning(
            'rawReadAppletHeaders: read returned a partial header (expected header size %s, bytes read %s',
            HEADER_SIZE, len(buf))
    if calculate_data_checksum(buf) != expected_checksum:
        raise ValueError('rawReadAppletHeaders: data checksum error')
    return buf
