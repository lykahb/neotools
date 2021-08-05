import logging
from functools import partial
from typing import List

from neotools.applet.constants import *
from neotools.message import Message, MessageConst, send_message, receive_message
from neotools.util import calculate_data_checksum, NeotoolsError, data_from_buf, data_to_buf, int_from_buf, \
    int_to_buf, string_to_buf, string_from_buf

logger = logging.getLogger(__name__)


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
            return f'{text} ({ident})'

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
        result = sorted(result, key=lambda item_dict: item_dict.get('label'))
        return result

    def merge_settings(self, settings):
        self.labels.update(settings.labels)
        self.descriptions.update(settings.descriptions)
        self.settings.update(settings.settings)


class AppletSettingsItem:
    def __init__(self, item_type, ident, data):
        self.type = item_type
        self.ident = ident
        self.data = data

    def to_raw(self):
        data_len = 0
        buf = []

        write_data = None

        if self.type in [AppletSettingsType.LABEL, AppletSettingsType.DESCRIPTION]:
            # Can we update the labels???
            data_len = len(self.data) + 1
            write_data = partial(string_to_buf, buf, 6, len(self.data), self.data)
        elif self.type == AppletSettingsType.OPTION:
            data_len = len(self.data) * 2

            def write_option():
                for (i, val) in enumerate(self.data):
                    int_to_buf(buf, 6 + i * 2, 2, val)

            write_data = write_option
        elif self.type == AppletSettingsType.RANGE_32:
            data_len = APPLET_SETTINGS_RANGE32_FORMAT['size']
            write_data = partial(data_to_buf, APPLET_SETTINGS_RANGE32_FORMAT, buf, self.data, buf_offset=6)
        elif self.type in [AppletSettingsType.FILE_PASSWORD, AppletSettingsType.PASSWORD_6]:
            data_len = 6
            write_data = partial(string_to_buf, buf, 6, 6, self.data)
        elif self.type == AppletSettingsType.APPLET_ID:
            data_len = 4
            write_data = partial(int_to_buf, buf, 6, 4, self.data)
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
        item_type = AppletSettingsType(item_obj['type'])
        del item_obj['type']
        item_obj['item_type'] = item_type

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
                raise NeotoolsError('Identifier must be a member of %s' % self.data[1:])
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
