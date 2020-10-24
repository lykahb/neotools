import click
import logging

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
def applets():
    device = Device.init()
    print('Getting applets')


@files.command('read')
@click.pass_context
def read_file(ctx):
    print('reading index %s' % ctx.obj['file_index'])


@files.command('write')
@click.pass_context
def read_file(ctx):
    print('writing index %s' % ctx.obj['file_index'])


if __name__ == '__main__':
    logger.warning('hi')
    cli()
