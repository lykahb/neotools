import json
import sys

import click
import logging

from alphatools.applet import read_applets, AppletIds
from alphatools.device import Device
from alphatools.file import load_file
from alphatools.text_file import export_text

logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.group()
@click.argument('file_index')
@click.pass_context
def files(ctx, file_index):
    ctx.ensure_object(dict)
    ctx.obj['file_index'] = int(file_index)


@cli.command('applets')
def applets_cmd():
    device = Device.init()
    applets = read_applets(device)
    print(json.dumps(applets, indent=2))


@files.command('read')
@click.pass_context
def read_file(ctx):
    index = ctx.obj['file_index']
    device = Device.init()
    text = load_file(device, AppletIds.ALPHAWORD, index)
    if text is None:
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
