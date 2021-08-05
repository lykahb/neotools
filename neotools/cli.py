import json
import logging
from enum import Enum
from functools import partial

import click

from neotools import commands

logger = logging.getLogger(__name__)

file_name_or_space_arg = partial(click.argument, 'file_name_or_space')
applet_id_option = partial(click.option, '--applet-id', '-a', type=int)
format_option = partial(
    click.option, '--format', '-f', 'format_',
    help='Format for the file names. For example, "{name}-{space}-{date:%x}.txt" '
         'may produce "File 3-3-11/02/20.txt" depending on your locale. '
         'See more date formatting options at'
         ' https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes')


@click.group()
@click.option('--verbose', '-v', default=False, is_flag=True)
@click.version_option()
@click.pass_context
def cli(ctx, verbose):
    """
    For scripts that issue multiple commands, use the mode command to
    avoid repeated initialization.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    if verbose:
        logging.basicConfig(level=logging.DEBUG)


@cli.command('mode', help='Neo keyboard/comms mode. Mostly useful for scripting where the tool is called many times.')
@click.option('--keyboard', 'target_mode', flag_value='keyboard')
@click.option('--comms', 'target_mode', flag_value='comms')
def mode(target_mode):
    if target_mode is None:
        commands.get_mode()
    if target_mode == 'comms':
        commands.flip_to_communicator()
    elif target_mode == 'keyboard':
        commands.flip_to_keyboard()


@cli.group(help='Manage files for AlphaWord and other applets.')
def files():
    pass


@cli.group()
def applets():
    """ Inspect applets and manage their settings. """
    pass


@applets.command('list')
def list_applets():
    """ Get a list of installed applets. """
    applet_list = commands.list_applets()
    print(json.dumps(applet_list, indent=2))


@applets.command('get-settings')
@click.argument('applet_id', type=int)
@click.argument('flag', type=int, nargs=-1)
def applet_get_settings(applet_id, flag):
    """
    List settings of an applet. Note that it is possible for the call to return
    different subsets of settings on multiple runs.

    The meaning of the flag depends on the applet and is not documented.
    The values that commonly give non-empty results are 0, 7, 15.
    """
    settings = commands.applet_read_settings(applet_id, flag)
    print(json.dumps(settings, indent=2, default=json_default))


@applets.command('set-settings',
                 short_help='Update settings. Use this at your own risk - invalid settings' +
                            ' may disrupt work of an applet or the device.')
@click.argument('applet_id', type=int)
@click.argument('ident', type=int)
@click.argument('value', nargs=-1)
def applet_set_settings(applet_id, ident, value):
    """
    Use this at your own risk - invalid settings may disrupt work of
    an applet or the device. There is validation for options and applet ids,
    but not for the open-ended values such as ranges and strings.

    To learn what settings are available for an applet, run get-settings.

    The value depends on type of the setting: number for option id and applet id,
    string for passwords, and three numbers for the ranges.

    Examples:

    \b
    * Enable two-button on mode: applets set-settings 0 16400 4097
    * Set idle time to ten minutes: applets set-settings 0 16388 10 4 59
    * Set password for an AlphaWord file: applets set-settings 40960 32790 write2
    * Delete all AlphaWord files: applets set-settings 40960 32771 4097
    """
    commands.applet_write_settings(applet_id, ident, value)


@applets.command('fetch')
@click.argument('applet_id', type=int)
@click.argument('path', type=click.Path())
def fetch_applet(applet_id, path):
    """
    Fetch the applet file from the device and write to file.

    Get a list of applets to find out the ids. The id 0 would fetch the firmware ROM.
    """
    commands.fetch_applet(applet_id, path)


@applets.command('remove-all')
def remove_applets():
    """ Delete all applets from the device. """
    click.confirm(text='Are you sure you want to remove all applets?', abort=True)
    commands.remove_applets()


@applets.command('remove',
                 short_help="Experimental. Delete an applet from the device. Note that it does not free the space.")
@click.argument('applet_id', type=int)
def remove_applet(applet_id):
    """ Delete an applet from the device. """
    click.confirm(text='Are you sure you want to remove applet?' +
                       'It will not free up the space and is meant only for development.', abort=True)
    commands.remove_applet(applet_id)


@applets.command('install', short_help="Experimental. Install an applet. Use this at your own risk.")
@click.argument('path', type=click.Path(exists=True, dir_okay=False))
@click.option('--force', '-f', default=False, is_flag=True, help='Skip check if the applet exists')
def install_applet(path, force):
    click.confirm(text='Are you sure you want to install an applet? ' +
                       'This is an experimental feature.', abort=True)
    commands.install_applet(path, force)


@files.command("list")
@applet_id_option()
@click.option('--verbose', '-v', default=False, is_flag=True, help='All file attributes')
def list_all_files(applet_id, verbose):
    files_list = commands.list_files(applet_id, verbose)
    print(json.dumps(files_list, indent=2, default=json_default))


@files.command('read')
@applet_id_option()
@file_name_or_space_arg()
@click.option('--path', '-p', type=click.Path())
@format_option()
def read_file(file_name_or_space, applet_id, path, format_):
    commands.read_file(applet_id, file_name_or_space, path, format_)


@files.command('read-all')
@applet_id_option()
@click.option('--path', '-p', type=click.Path(exists=True, file_okay=False, writable=True), required=True)
@format_option()
def read_all_files(applet_id, path, format_):
    commands.read_all_files(applet_id, path, format_)


@files.command('write')
@click.argument('path', type=click.Path(exists=True, dir_okay=False))
@file_name_or_space_arg()
def write_file(path, file_name_or_space):
    contents = open(path).read()
    commands.write_file(file_name_or_space, contents)


@cli.command('info')
def system_info():
    """ General system information """
    info = commands.system_info()
    print(json.dumps(info, indent=2))


@files.command('clear')
@applet_id_option()
@file_name_or_space_arg()
def clear_file(applet_id, file_name_or_space):
    commands.clear_file(applet_id, file_name_or_space)


def json_default(val):
    if isinstance(val, Enum):
        return val.name
    elif isinstance(val, bytes):
        return str(val)[2:-1]
    elif isinstance(val, object) and hasattr(val, '__dict__'):
        return val.__dict__
    else:
        return str(val)
