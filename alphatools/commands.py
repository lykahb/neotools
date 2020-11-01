import logging
import sys

from alphatools.applet import AppletIds, read_applets
from alphatools.device import Device, flip_to_keyboard_mode
from alphatools.file import load_file, list_files as raw_list_files, create_file, raw_write_file
from alphatools.text_file import export_text
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
def read_file(file_index):
    device = Device.init()
    text = load_file(device, AppletIds.ALPHAWORD, file_index - 1)
    if text is None:
        print('Text file at index %s does not exist' % file_index)
        sys.exit(1)
    text = export_text_from_neo(text)
    flip_to_keyboard_mode(device)
    return text


@command_decorator
def list_applets():
    device = Device.init()
    applets = read_applets(device)
    flip_to_keyboard_mode(device)
    return applets


@command_decorator
def list_files():
    device = Device.init()
    files = raw_list_files(device, AppletIds.ALPHAWORD)
    flip_to_keyboard_mode(device)
    return files


@command_decorator
def write_file(file_index, text):
    device = Device.init()
    raw_bytes = import_text_to_neo(text)
    device.dialogue_start()
    raw_write_file(device, raw_bytes, AppletIds.ALPHAWORD, file_index, True)
    device.dialogue_end()
