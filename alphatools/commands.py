import logging
import sys

from alphatools.applet import AppletIds, read_applets, get_settings
from alphatools.device import Device, flip_to_keyboard_mode
from alphatools import file
from alphatools.text_file import export_text_from_neo, import_text_to_neo
from alphatools.util import AlphatoolsError

logger = logging.getLogger(__name__)


def command_decorator(f):
    def new_func(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
        except AlphatoolsError as e:
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
    Device.init()


@command_decorator
def flip_to_keyboard():
    device = Device.init()
    flip_to_keyboard_mode(device)


@command_decorator
def read_file(file_index):
    device = Device.init()
    text = file.load_file(device, AppletIds.ALPHAWORD, file_index)
    if text is None:
        print('Text file at index %s does not exist' % file_index)
        sys.exit(1)
    text = export_text_from_neo(text)
    return text


@command_decorator
def list_applets():
    device = Device.init()
    applets = read_applets(device)
    return applets


@command_decorator
def list_files():
    device = Device.init()
    files = file.list_files(device, AppletIds.ALPHAWORD)
    return files


@command_decorator
def write_file(file_index, text):
    device = Device.init()
    raw_bytes = import_text_to_neo(text)
    device.dialogue_start()
    file.raw_write_file(device, raw_bytes, AppletIds.ALPHAWORD, file_index, True)
    device.dialogue_end()


@command_decorator
def applet_read_settings(applet_id, flags):
    device = Device.init()
    system_settings1 = get_settings(device, 0, 7)
    system_settings2 = get_settings(device, 0, 15)
    settings = get_settings(device, applet_id, flags)
    for system_settings in [system_settings1, system_settings2]:
        settings.labels.update(system_settings.labels)
        settings.descriptions.update(system_settings.descriptions)
    return settings.to_dict()

@command_decorator
def clear_file(file_index):
    device = Device.init()
    file.clear_file(device, AppletIds.ALPHAWORD, file_index)

@command_decorator
def clear_all_files(applet_id):
    device = Device.init()
    if applet_id is None:
        applet_id = AppletIds.ALPHAWORD
    file.clear_all_files(device, applet_id)