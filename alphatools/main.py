import json
import logging

import click

from alphatools import commands

logger = logging.getLogger(__name__)


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
def applets_cmd(ctx):
    applets = commands.list_applets()
    print(json.dumps(applets, indent=2))


@files.command("list")
@click.pass_context
def list_all_files(ctx):
    files = commands.list_files()
    output = list(map(lambda f: f.__dict__, files))
    print(json.dumps(output, indent=2))


@files.command('read')
@click.pass_context
def read_file(ctx):
    index = ctx.obj['file_index']
    text = commands.read_file(index)
    print(text)


@files.command('write')
@click.argument('path')
@click.pass_context
def write_file(ctx, path):
    contents = open(path).read()
    commands.write_file(ctx.obj['file_index'], contents)


def main():
    cli()


if __name__ == "__main__":
    # execute only if run as a script
    main()
