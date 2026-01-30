from pathlib import Path

import click

from project import Project
from resource_manager import ResourceManager


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
    click.secho("Rebuilding project...", fg="yellow")
    project = Project(Path()).load()
    project.rebuild()
    click.secho("Success!", fg="green")


@cli.group()
def create():
    pass


@cli.command(name="import")
@click.argument("resource_path")
@click.option(
    "--dest",
    "dest_path",
    default=None,
    help="Optional destination relative path in project",
)
def import_cmd(resource_path, dest_path):
    """Import a resource (file or module) into the project.

    RESOURCE_PATH can be a file or module directory, optionally namespaced.

    \b
    Path resolution:
      - 'name.py' or 'name.yaml' -> file (explicit extension)
      - 'name/' -> module directory (explicit trailing slash)
      - 'name' -> auto-detect (error if both file and directory exist)

    \b
    Examples:
        invoker import script.py                # Import single file
        invoker import myplugin:custom.py       # Import from plugin namespace
        invoker import data_loader/             # Import module directory
        invoker import myplugin:data_loader     # Import module from plugin
    """
    click.secho(f"Importing {resource_path}...", fg="yellow")
    project = Project(Path())
    project.load()
    project.import_resource(resource_path, dest_rel_path=dest_path)
    click.secho("Success!", fg="green")


@cli.command(name="export")
@click.argument("src_path")
@click.argument("dest_path")
def export_cmd(src_path, dest_path):
    """Export a project file or module to a resource namespace.

    SRC_PATH is the file or directory to export.
    DEST_PATH must include a namespace prefix.

    \b
    Examples:
        invoker export my_script.py myplugin:my_script.py     # Export file
        invoker export data_loader/ myplugin:data_loader      # Export module
        invoker export lib/helper.py invoker:util/helper.py   # Export to core
    """
    click.secho(f"Exporting {src_path} to {dest_path}...", fg="yellow")
    project = Project(Path())
    project.load()
    project.export_resource(src_path, dest_path)
    click.secho("Success!", fg="green")


@cli.command(name="resources")
def list_resources():
    """List available resource namespaces."""
    namespaces = ResourceManager.list_namespaces()
    click.secho("Available resource namespaces:", fg="cyan")
    for ns in sorted(namespaces):
        path = ResourceManager._get_resources_path(ns)
        editable = ResourceManager.is_namespace_editable(ns)
        status = (
            click.style("(editable)", fg="green")
            if editable
            else click.style("(read-only)", fg="yellow")
        )
        click.echo(f"  {ns}: {path} {status}")


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
