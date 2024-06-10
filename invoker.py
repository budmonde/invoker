from pathlib import Path

import click

from project import InvokerError, Project


@click.group()
def cli():
    pass


@cli.command()
def init():
    click.secho("Initializing new project at current directory...", fg="yellow")
    project = Project(Path())
    try:
        project.initialize()
        click.secho("Success!", fg="green")
    except InvokerError as err:
        click.secho("Invoker Error: ", err=True, nl=False, fg="red")
        click.echo(err, err=True)


@cli.command()
def lint():
    project = Project(Path())
    project.load()
    project.lint()


@cli.command()
def rebuild():
    click.secho("Rebuildng project...", fg="yellow")
    project = Project(Path()).load()
    try:
        project.rebuild()
        click.secho("Success!", fg="green")
    except InvokerError as err:
        click.secho("Invoker Error: ", err=True, nl=False, fg="red")
        click.echo(err, err=True)


@cli.group()
def create():
    pass


@create.command()
@click.argument("module_name")
def module(module_name):
    click.secho(f"Creating new module {module_name}...", fg="yellow")
    project = Project(Path())
    try:
        project.load()
        project.create_module(module_name)
        project.validate()
        click.secho("Success!", fg="green")
    except InvokerError as err:
        click.secho("Invoker Error: ", err=True, nl=False, fg="red")
        click.echo(err, err=True)


@create.command()
@click.argument("script_name")
def script(script_name):
    click.secho(f"Creating new script {script_name}...", fg="yellow")
    project = Project(Path())
    try:
        project.load()
        project.create_script(script_name)
        project.validate()
        click.secho("Success!", fg="green")
    except InvokerError as err:
        click.secho("Invoker Error: ", err=True, nl=False, fg="red")
        click.echo(err, err=True)
