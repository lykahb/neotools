import json
import sys

import click
import logging

from alphatools.applet import read_applets, AppletIds
from alphatools.device import Device
from alphatools.file import load_file
from alphatools.text_file import export_text
from alphatools.util import AlphatoolsError

logger = logging.getLogger(__name__)


def command_decorator(f):
    def new_func(ctx, *args, **kwargs):
        try:
            f(ctx, *args, **kwargs)
        except AlphatoolsError as e:
            if ctx.obj['verbose']:
                logger.exception(e)
            else:
                logger.error(e)
        sys.exit(1)

    from functools import update_wrapper
    return update_wrapper(new_func, f)


@click.group()
@click.option('--verbose', '-v', default=False, is_flag=True)
@click.pass_context
def cli(ctx, verbose):
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    if verbose:
        logging.basicConfig(level=logging.DEBUG)


@cli.group()
@click.argument('file_index')
@click.pass_context
def files(ctx, file_index):
    ctx.ensure_object(dict)
    ctx.obj['file_index'] = int(file_index)


@cli.command('applets')
@click.pass_context
@command_decorator
def applets_cmd(ctx):
    device = Device.init()
    applets = read_applets(device)
    print(json.dumps(applets, indent=2))
    device.dispose()


@files.command('read')
@click.pass_context
@command_decorator
def read_file(ctx):
    index = ctx.obj['file_index']
    device = Device.init()
    text = load_file(device, AppletIds.ALPHAWORD, index)
    if text is None:
        print('Text file at index %s does not exist' % index)
        sys.exit(1)
    print(export_text(text))


@files.command('write')
@click.pass_context
def write_file(ctx):
    print('writing index %s' % ctx.obj['file_index'])


def main():
    cli()


if __name__ == "__main__":
    # execute only if run as a script
    main()
