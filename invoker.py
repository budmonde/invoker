from pathlib import Path

import click

from project import Project


@click.group()
def cli():
    pass


@cli.command()
def init():
    click.echo("Initializing new project at current directory...")
    project = Project(Path()).initialize()
    click.echo("Success!")


@cli.command()
def lint():
    project = Project(Path()).load()
    project.lint()


@cli.command()
def rebuild():
    click.echo("Rebuildng project...")
    project = Project(Path()).load()
    project.rebuild()
    click.echo("Success!")


@cli.group()
def create():
    pass


@create.command()
@click.argument("module_name")
def module(module_name):
    click.echo(f"Creating new module {module_name}...")
    project = Project(Path()).load()
    project.create_module(module_name)
    project.validate()
    click.echo("Success!")


@create.command()
@click.argument("script_name")
def script(script_name):
    click.echo(f"Creating new script {script_name}...")
    project = Project(Path()).load()
    project.create_script(script_name)
    project.validate()
    click.echo("Success!")


@cli.group()
@click.argument("script_name")
@click.pass_context
def update(ctx, script_name):
    ctx.ensure_object(dict)
    ctx.obj['script_name'] = script_name


@update.command()
@click.argument("module_name")
@click.pass_context
def add(ctx, module_name):
    script_name = ctx.obj['script_name']
    click.echo(f"Adding module {module_name} to script {script_name}...")
    project = Project(Path()).load()
    project.update_script_add_module(script_name, module_name)
    project.validate()
    click.echo("Success!")
