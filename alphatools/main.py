import json

import click
import logging

from alphatools.applet import read_applets
from alphatools.device import Device

logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.group()
@click.argument('file_index')
@click.pass_context
def files(ctx, file_index):
    ctx.ensure_object(dict)
    ctx.obj['file_index'] = file_index


@cli.command('applets')
def applets_cmd():
    device = Device.init()

    applets = read_applets(device)
    # for applet in applets:
    #     print(json.dumps(applet))
    print(json.dumps(applets, indent=2))


@files.command('read')
@click.pass_context
def read_file(ctx):
    print('reading index %s' % ctx.obj['file_index'])


@files.command('write')
@click.pass_context
def read_file(ctx):
    print('writing index %s' % ctx.obj['file_index'])


def main():
    cli()


if __name__ == "__main__":
    # execute only if run as a script
    main()
