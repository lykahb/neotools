import logging
from collections import OrderedDict
from enum import Enum
from typing import List

from alphatools.message import Message, MessageConst, send_message, receive_message
from alphatools.util import calculate_data_checksum, AlphatoolsError, data_from_buf, data_to_buf, int_from_buf, \
    int_to_buf, string_to_buf, string_from_buf

logger = logging.getLogger(__name__)

# Applet fields with offset and width in to the applet header data 
# (usually located at the start of the applet).
APPLET_HEADER_FORMAT = {
    'size': 0x84,  # The total size of the header
    'fields': OrderedDict([
        ('signature', (0x00, 4, int)),  # The signature word field.
        ('rom_size', (0x04, 4, int)),  # The ROM size field.
        ('ram_size', (0x08, 4, int)),  # The size of working RAM field.
        ('settings_offset', (0x0c, 4, int)),  # Settings parameters field.
        ('flags', (0x10, 4, int)),
        ('applet_id', (0x14, 2, int)),
        ('header_version', (0x16, 1, int)),  # ByteHeader version code field.
        ('file_count', (0x17, 1, int)),
        ('name', (0x18, 36, str)),  # Display name.
        ('version_major', (0x3c, 1, int)),  # Major version number field.
        ('version_minor', (0x3d, 1, int)),  # Minor version number field.
        ('version_revision', (0x3e, 1, int)),  # Revision code (ASCII) field.
        ('language_id', (0x3f, 1, int)),  # Localised language field.
        ('info', (0x40, 60, str)),  # The info (copyright) string field.
        ('min_asm_version', (0x7c, 4, int)),  # Minimum AlphaSmart Manager version required field.
        ('file_space', (0x80, 4, int)),  # The required file space field.
    ])}

APPLET_SETTINGS_FORMAT = {
    'size': None,
    'fields': OrderedDict([
        ('type', (0x00, 2, int)),
        ('ident', (0x02, 2, int)),
        ('length', (0x04, 2, int))
    ])
}
APPLET_SETTINGS_RANGE32_FORMAT = {
    'size': 12,
    'fields': {
        'default': (0x00, 4, int),
        'min': (0x04, 4, int),
        'max': (0x08, 4, int)
    }
}

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

FLAGS_HIDDEN = 0x01  # If set, the applet is hidden.

# Reading more than 7 headers will cause a crash on some Neos (1k buffer overflow?)
LIST_APPLETS_REQUEST_COUNT = 7


class AppletSettingsType(Enum):
    NONE = 0x0000  # No item is present (used to mark end of data).
    LABEL = 0x0001  # Item is a null terminated string (fixed label).
    RANGE_32 = 0x0102  # Item is an integer numeric range: {default, min, max}.
    OPTION = 0x0103  # Item is a list of item IDs: {default, a, b, c...}.
    PASSWORD_6 = 0x0105  # Item is a password (c-string). Used for AW "File Passwords" and system "Master Password". Max 6 characters.
    DESCRIPTION = 0x0106  # Item is a null terminated string constant for descriptive purposes only.
    FILE_PASSWORD = 0xc001  # Item is a file password (c-string). File is identified by the ident field.
    APPLET_ID = 0x8002  # Item is a U16 applet ID.


class AppletSettingsIdent:
    # Well known settings ident values.
    # Bit 31 is set if the ident is local to an applet, or clear if it is global (system applet).
    # Bit 30 is set for file passwords (possible security flag?)
    NONE = 0x0000  # No item is present (used to mark end of data).
    SYSTEM_ON = 0x1001  # Setting is 'on'
    SYSTEM_OFF = 0x1002  # Setting is 'off'
    SYSTEM_YES = 0x100c  # Setting is 'yes'
    SYSTEM_NO = 0x100d  # Setting is 'no'
    SYSTEM_PASSWORD = 0x400b  # Master password, as type 0x0105.
    ALPHAWORD_CLEARFILES = 0x8003  # Clear all files, as type 0x0103. Use a value of SYSTEM_ON to trigger.
    ALPHAWORD_MAXFILESIZE = 0x1010  # Get maximum file size information. Type is Range32.
    ALPHAWORD_MINFILESIZE = 0x1011  # Get minimum file size information. Type is Range32.


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


class AppletSettings:
    def __init__(self, item_list):
        self.item_list = item_list
        self.labels = {}
        self.descriptions = {}
        self.settings = {}
        self.classify_data(item_list)

    def classify_data(self, item_list):
        for item in item_list:
            if item.type == AppletSettingsType.LABEL:
                self.labels[item.ident] = item
            elif item.type == AppletSettingsType.DESCRIPTION:
                self.descriptions[item.ident] = item
            else:
                self.settings[item.ident] = item

    def to_dict(self):
        result = []

        def label_for_ident(ident):
            label = self.labels.get(ident)
            text = label.data if label else 'Unknown'
            return '%s (%s)' % (text, ident)

        for item in self.settings.values():
            description = self.descriptions.get(item.ident)
            item_dict = {'label': label_for_ident(item.ident), 'ident': item.ident, 'type': item.type,
                         'value': item.data}
            if description:
                item_dict['description'] = description.data
            if item.type == AppletSettingsType.OPTION:
                item_dict['value'] = {
                    'selected': label_for_ident(item.data[0]),
                    'options': list(map(label_for_ident, item.data[1:]))
                }
            result.append(item_dict)
        result = sorted(result, key=lambda item: item.get('label'))
        return result

    def merge_settings(self, settings):
        self.labels.update(settings.labels)
        self.descriptions.update(settings.descriptions)
        self.settings.update(settings.settings)


class AppletSettingsItem:
    def __init__(self, type, ident, data):
        self.type = type
        self.ident = ident
        self.data = data

    def to_raw(self):
        data_len = 0
        buf = []

        write_data = None

        if self.type in [AppletSettingsType.LABEL, AppletSettingsType.DESCRIPTION]:
            # Can we update the labels???
            data_len = len(self.data) + 1
            write_data = lambda: string_to_buf(buf, 6, len(self.data), self.data)
        elif self.type == AppletSettingsType.OPTION:
            data_len = len(self.data) * 2

            def write_option():
                for (i, val) in enumerate(self.data):
                    int_to_buf(buf, 6 + i * 2, 2, val)

            write_data = write_option
        elif self.type == AppletSettingsType.RANGE_32:
            data_len = APPLET_SETTINGS_RANGE32_FORMAT['size']
            write_data = lambda: data_to_buf(APPLET_SETTINGS_RANGE32_FORMAT, buf, self.data, buf_offset=6)
        elif self.type in [AppletSettingsType.FILE_PASSWORD, AppletSettingsType.PASSWORD_6]:
            data_len = 6
            write_data = lambda: string_to_buf(buf, 6, 6, self.data)
        elif self.type == AppletSettingsType.APPLET_ID:
            data_len = 4
            write_data = lambda: int_to_buf(buf, 6, 4, self.data)
        total_len = 6 + data_len + (data_len & 1)
        buf = [0] * total_len

        obj = self.__dict__
        obj['length'] = data_len
        obj['type'] = self.type.value
        data_to_buf(APPLET_SETTINGS_FORMAT, buf, obj)
        write_data()

        return buf

    @staticmethod
    def item_from_raw(item_obj, buf):
        data = None
        item_type = item_obj['type'] = AppletSettingsType(item_obj['type'])
        if item_type == AppletSettingsType.RANGE_32:
            data = data_from_buf(APPLET_SETTINGS_RANGE32_FORMAT, buf[6:])
        elif item_type == AppletSettingsType.OPTION:
            data = []
            offset = 0
            while offset < item_obj['length']:
                data.append(int_from_buf(buf, 6 + offset, 2))
                offset = offset + 2
        elif item_type in [AppletSettingsType.PASSWORD_6, AppletSettingsType.DESCRIPTION,
                           AppletSettingsType.FILE_PASSWORD, AppletSettingsType.LABEL]:
            data = string_from_buf(buf, 6, item_obj['length'])
        elif item_type == AppletSettingsType.APPLET_ID:
            data = int_from_buf(buf, 6, 4)
        del item_obj['length']
        return AppletSettingsItem(**item_obj, **{'data': data})

    def change_setting(self, values: List[str]):
        if self.type == AppletSettingsType.RANGE_32:
            assert len(values) == 3
            self.data = {
                'default': int(values[0]),
                'min': int(values[1]),
                'max': int(values[2])
            }
        if self.type == AppletSettingsType.OPTION:
            assert len(values) == 1
            ident = int(values[0])
            if ident not in self.data:
                raise AlphatoolsError('Identifier must be a member of %s' % self.data[1:])
            self.data[0] = ident
        elif self.type in [AppletSettingsType.PASSWORD_6, AppletSettingsType.FILE_PASSWORD]:
            assert len(values) == 1
            password = values[0]
            assert len(password) >= 6
            self.data = password
        elif self.type == AppletSettingsType.APPLET_ID:
            assert len(values) == 1
            applet_id = int(values[0])
            # The caller must check that the applet exists
            self.data = applet_id

    @staticmethod
    def list_from_raw(buf):
        offset = 0
        items = []
        while True:
            if len(buf) < offset + 6:
                # not even space for a single header
                break
            item_obj = data_from_buf(APPLET_SETTINGS_FORMAT, buf[offset:])
            length = item_obj['length']
            if item_obj['type'] == 0 and item_obj['ident'] == 0 and length == 0:
                break

            item_total_length = 6 + length + (length & 1)  # Two byte alignment

            item = AppletSettingsItem.item_from_raw(item_obj, buf[offset:offset + item_total_length])
            items.append(item)
            offset = offset + item_total_length
        return items


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
    logger.info('Requesting to read list of applets with index=%s', index)
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
    response = send_message(device, message, MessageConst.RESPONSE_GET_USED_SPACE)
    result = {
        'ram': response.argument(1, 4),
        'file_count': response.argument(5, 2)
    }
    device.dialogue_end()
    return result


def get_settings(device, applet_id, flags):
    device.dialogue_start()
    logger.info('Requesting settings for applet_id=%s, flags=%s', applet_id, flags)
    message = Message(MessageConst.REQUEST_GET_SETTINGS, [(flags, 1, 4), (applet_id, 5, 2)])
    response = send_message(device, message, MessageConst.RESPONSE_GET_SETTINGS)
    response_size = response.argument(1, 4)
    expected_checksum = response.argument(5, 2)
    logger.info('Retrieving settings data')
    result = device.read(response_size)
    assert calculate_data_checksum(result) == expected_checksum
    device.dialogue_end()
    settings_list = AppletSettingsItem.list_from_raw(result)
    return AppletSettings(settings_list)


def set_settings(device, applet_id, settings):
    settings_buf = settings.to_raw()
    checksum = calculate_data_checksum(settings_buf)
    device.dialogue_start()
    logger.info('Requesting to write settings for applet_id=%s', applet_id)
    message = Message(MessageConst.REQUEST_SET_SETTINGS,
                      [(len(settings_buf), 1, 4), (checksum, 5, 2)])
    send_message(device, message, MessageConst.RESPONSE_BLOCK_WRITE)
    logger.info('Writing settings')
    device.write(settings_buf)
    receive_message(device, MessageConst.RESPONSE_BLOCK_WRITE_DONE)

    message = Message(MessageConst.REQUEST_SET_APPLET, [(0, 1, 4), (applet_id, 5, 2)])
    send_message(device, message, MessageConst.RESPONSE_SET_APPLET)
    device.dialogue_end()
