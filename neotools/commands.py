import logging
import sys
from datetime import datetime
from pathlib import Path

from neotools import file
from neotools.applet import AppletIds, read_applets, get_settings, AppletSettingsType, set_settings, AppletSettings
from neotools.device import Device, HID_PRODUCT_ID, COM_PRODUCT_ID
from neotools.text_file import export_text_from_neo, import_text_to_neo
from neotools.util import NeotoolsError

logger = logging.getLogger(__name__)


def command_decorator(f):
    def new_func(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
        except NeotoolsError as e:
            if logger.level == logging.DEBUG:
                logger.exception(e)
            else:
                logger.error(e)
            sys.exit(1)
        return result

    from functools import update_wrapper
    return update_wrapper(new_func, f)


@command_decorator
def flip_to_communicator():
    with Device.connect(flip_to_comms=True, dispose=False):
        pass


@command_decorator
def flip_to_keyboard():
    with Device.connect(flip_to_comms=False) as device:
        if device.original_product == COM_PRODUCT_ID:
            device.flip_to_keyboard_mode()


@command_decorator
def get_mode():
    with Device.connect(flip_to_comms=False) as device:
        mapping = {HID_PRODUCT_ID: 'keyboard', COM_PRODUCT_ID: 'comms'}
        mode = mapping.get(device.original_product, 'unknown')
        print(mode)


@command_decorator
def read_all_files(applet_id, path, name_format):
    if applet_id is None:
        applet_id = AppletIds.ALPHAWORD
    with Device.connect() as device:
        files = file.list_files(device, applet_id)
        for file_attrs in files:
            text = read_text(device, applet_id, file_attrs)
            if len(text):
                write_file_with_format(file_attrs, text, path, name_format)


def read_text(device, applet_id, file_attrs):
    text = file.read_file(device, applet_id, file_attrs, file_attrs.space)
    if applet_id == AppletIds.ALPHAWORD:
        text = export_text_from_neo(text)
    return text


def write_file_with_format(file_attrs, text, path, name_format):
    name_format = name_format or '{name}.txt'
    date = datetime.now()
    data = {'name': file_attrs.name, 'index': file_attrs.space, 'date': date}
    file_name = name_format.format(**data)
    file_path = Path(path) / file_name
    with open(file_path, mode='w') as f:
        logger.info('Writing file path=%s size=%s', file_path, len(text))
        f.write(text)


@command_decorator
def read_file(applet_id, file_index, path, name_format):
    if applet_id is None:
        applet_id = AppletIds.ALPHAWORD

    with Device.connect() as device:
        file_attrs = file.get_file_attributes(device, applet_id, file_index)
        if file_attrs is None:
            print('Text file at index %s does not exist' % file_index)
            sys.exit(1)

        text = read_text(device, applet_id, file_attrs)
        if path:
            write_file_with_format(file_attrs, text, path, name_format)
        else:
            print(text)


@command_decorator
def list_applets():
    with Device.connect() as device:
        return read_applets(device)


@command_decorator
def list_files(applet_id):
    if applet_id is None:
        applet_id = AppletIds.ALPHAWORD
    with Device.connect() as device:
        return file.list_files(device, applet_id)


@command_decorator
def write_file(file_index, text):
    with Device.connect() as device:
        raw_bytes = import_text_to_neo(text)
        device.dialogue_start()
        file.raw_write_file(device, raw_bytes, AppletIds.ALPHAWORD, file_index, True)
        device.dialogue_end()


@command_decorator
def applet_read_settings(applet_id, flags):
    default_flags = [0, 7, 15]
    if len(flags) == 0:
        flags = default_flags

    with Device.connect() as device:
        # Retrieve system labels for better UI.
        system_settings = AppletSettings([])
        for flag in default_flags:
            system_settings.merge_settings(get_settings(device, 0, flag))

        settings = AppletSettings([])
        for flag in flags:
            s = get_settings(device, applet_id, flag)
            settings.merge_settings(s)

        settings.labels.update(system_settings.labels)
        settings.descriptions.update(system_settings.descriptions)
        return settings.to_dict()


@command_decorator
def applet_write_settings(applet_id, ident, values):
    with Device.connect() as device:
        for flag in [7, 15]:
            settings = get_settings(device, applet_id, flag)
            item = settings.settings.get(ident)
            if item:
                break
        if item is None:
            raise NeotoolsError('Settings item with id=%s not found' % ident)
        if item.type == AppletSettingsType.APPLET_ID:
            applets = read_applets(device)
            if not any(item.data == applet.id for applet in applets):
                raise NeotoolsError('Applet with id=%s not found' % item.data)
        item.change_setting(values)
        set_settings(device, applet_id, item)


@command_decorator
def clear_file(applet_id, file_index):
    if applet_id is None:
        applet_id = AppletIds.ALPHAWORD
    with Device.connect() as device:
        file.clear_file(device, applet_id, file_index)
