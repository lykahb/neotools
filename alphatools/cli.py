import json
import logging
from enum import Enum

import click

from alphatools import commands

logger = logging.getLogger(__name__)


@click.group(
    help='For scripts that issue multiple commands, add them between the'
         'initialize and keyboard commands to avoid repeated initialization.')
@click.option('--verbose', '-v', default=False, is_flag=True)
@click.pass_context
def cli(ctx, verbose):
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    if verbose:
        logging.basicConfig(level=logging.DEBUG)


@cli.command('switch', help='Low-level command for switching keyboard/comms mode.')
@click.argument('target', type=click.Choice(['comms', 'keyboard']))
def switch_device(target):
    if target == 'comms':
        commands.flip_to_communicator()
    if target == 'keyboard':
        commands.flip_to_keyboard()


@cli.group(help='Manage files for AlphaWord and other applets.')
def files():
    pass


@cli.group(help='Applet detailed information and settings.')
def applets():
    pass


@applets.command('list')
def applets_list():
    applets = commands.list_applets()
    print(json.dumps(applets, indent=2))


@applets.command('read-settings')
@click.argument('applet_id', type=int)
@click.argument('flag', type=int)
def applet_read_settings(applet_id, flag):
    settings = commands.applet_read_settings(applet_id, flag)
    print(json.dumps(settings, indent=2, default=json_default))


@files.command("list")
def list_all_files():
    files = commands.list_files()
    print(json.dumps(files, indent=2, default=json_default))


@files.command('read')
@click.argument('file_index', type=int)
def read_file(file_index):
    text = commands.read_file(file_index)
    print(text)


@files.command('write')
@click.argument('path', type=click.Path())
@click.argument('file_index', type=int)
def write_file(path, file_index):
    print(path, file_index)
    contents = open(path).read()
    commands.write_file(file_index, contents)


@files.command('clear')
@click.argument('file_index', type=int)
def clear_file(file_index):
    commands.clear_file(file_index)


@files.command('clearall')
@click.option('--applet_id', type=int)
def clear_all_files(applet_id):
    commands.clear_all_files(applet_id)


def json_default(val):
    if isinstance(val, Enum):
        return val.name
    elif isinstance(val, bytes):
        return str(val)[2:-1]
    elif isinstance(val, object) and hasattr(val, '__dict__'):
        return val.__dict__
    else:
        return str(val)
