from pathlib import Path

import click

from project import Project


@click.group()
def cli():
    pass


@cli.command()
def init():
    click.secho("Initializing new project at current directory...", fg="yellow")
    project = Project(Path())
    project.initialize()
    click.secho("Success!", fg="green")


@cli.command()
def lint():
    project = Project(Path())
    project.load()
    project.lint()


@cli.command()
def rebuild():
    click.secho("Rebuildng project...", fg="yellow")
    project = Project(Path()).load()
    project.rebuild()
    click.secho("Success!", fg="green")


@cli.group()
def create():
    pass


@cli.command(name="import")
@click.argument("resource_path")
@click.option("--dest", "dest_path", default=None, help="Optional destination relative path in project")
def import_cmd(resource_path, dest_path):
    click.secho(f"Importing {resource_path}...", fg="yellow")
    project = Project(Path())
    project.load()
    project.import_resource(resource_path, dest_rel_path=dest_path)
    click.secho("Success!", fg="green")


@create.command()
@click.argument("module_name")
def module(module_name):
    click.secho(f"Creating new module {module_name}...", fg="yellow")
    project = Project(Path())
    project.load()
    project.create_module(module_name)
    project.validate()
    click.secho("Success!", fg="green")


@create.command()
@click.argument("script_name")
def script(script_name):
    click.secho(f"Creating new script {script_name}...", fg="yellow")
    project = Project(Path())
    project.load()
    project.create_script(script_name)
    project.validate()
    click.secho("Success!", fg="green")


@cli.command()
@click.argument("script_name")
def run(script_name):
    click.secho(f"Running script {script_name}...", fg="yellow")
    project = Project(Path())
    project.load()
    project.run_script(script_name)


@cli.command()
@click.argument("script_name")
def debug(script_name):
    click.secho(f"Running script {script_name}...", fg="yellow")
    project = Project(Path())
    project.load()
    project.debug_script(script_name)