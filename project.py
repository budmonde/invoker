from importlib import metadata
from pathlib import Path
import re
import click
import subprocess

from util import copy_resource, compute_resource_hash, compute_file_hash, to_camel_case

def raise_error(message):
    click.secho("Invoker Error: ", err=True, nl=False, fg="red")
    click.echo(message, err=True)
    raise SystemExit(1)

def warn(message):
    click.secho("Invoker Warning: ", err=True, nl=False, fg="yellow")
    click.echo(message, err=True)

class Project:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.invoker_path = root_path / "invoker.py"
        self.project_version = None

    def initialize(self):
        if self.invoker_path.exists():
            raise_error(f"invoker module already exists at {self.invoker_path}!")
        copy_resource("invoker.py", self.invoker_path, sign=True)
        self.project_version = metadata.version('invoker')
        self.validate()
        return self

    def load(self):
        self.validate()
        return self

    def validate(self):
        if not self.invoker_path.exists():
            raise_error("invoker.py file is missing in project!")
        self.check_version(error_on_mismatch=False)
        return True

    def check_version(self, error_on_mismatch=True):
        self._set_project_version()
        if self.project_version is None:
            error_message = f"Cannot determine project version from {self.invoker_path}."
            raise_error(error_message) if error_on_mismatch else warn(error_message)
            return
        
        if self.project_version != metadata.version('invoker'):
            error_message = f"Version mismatch: project v{self.project_version}, CLI v{metadata.version('invoker')}."
            raise_error(error_message) if error_on_mismatch else warn(error_message)
            return

    def _set_project_version(self):
        if not self.invoker_path.exists():
            self.project_version = None
            return
            
        with open(self.invoker_path, "r") as f:
            first_line = f.readline()
            
        # Match version line format: # Invoker: v1.2.3
        version_match = re.match(r"# Invoker: v(\d+\.\d+\.\d+)", first_line.strip())
        if version_match:
            self.project_version = version_match.group(1)
        else:
            self.project_version = None

    def lint(self):
        subprocess.call(['black', self.root_path])
        subprocess.call(['isort', self.root_path])
        subprocess.call(['flake8', self.root_path])

    def create_module(self, module_name):
        # Create module directory
        module_path = self.root_path / module_name
        if module_path.exists():
            raise_error(f"module already exists at {module_path}!")
        module_path.mkdir()

        # Create empty __init__.py to make it a Python package
        module_init_path = module_path / "__init__.py"
        module_init_path.touch()

        # Add boilerplate module base class resource
        module_base_path = module_path / f"base_{module_name}.py"
        copy_resource(
            "module_base.py",
            module_base_path,
            preprocess_fn=lambda l: l.replace("__MODULE__", to_camel_case(module_name)),
        )

    def create_script(self, script_name):
        # Fix script name
        if script_name.endswith(".py"):
            script_name = script_name.removesuffix(".py")
        # Add boilerplate base script
        script_path = self.root_path / f"{script_name}.py"
        if script_path.exists():
            raise_error(f"script already exists at {script_path}!")
        copy_resource(
            "script.py",
            script_path,
            preprocess_fn=lambda l: l.replace("__SCRIPT__", to_camel_case(script_name)),
        )
        script_path.chmod(0o744)

    def run_script(self, script_name):
        # Fix script name
        if not script_name.endswith(".py"):
            script_name = script_name + ".py"
        script_path = self.root_path / f"{script_name}"
        if not script_path.exists():
            raise_error(f"script does not exist at {script_path}!")
        subprocess.call(['python', 'invoker.py', 'run', script_name])

    def debug_script(self, script_name_with_line_num):
        script_match = re.match(r"^(\w+\.\w+)(?::(\d+))?$", script_name_with_line_num)
        if not script_match:
            raise_error(f"Invalid script name format: {script_name_with_line_num}. Expected format: script.py or script.py:line_number")
        
        script_name = script_match.group(1)
        embed_line_num = int(script_match.group(2)) if script_match.group(2) else None

        script_path = self.root_path / f"{script_name}"
        if not script_path.exists():
            raise_error(f"script does not exist at {script_path}!")
        subprocess.call(['python', 'invoker.py', 'debug', script_name_with_line_num])

    def rebuild(self):
        self.check_version(error_on_mismatch=True)
        self._rebuild_resource("invoker.py", self.invoker_path, sign=True)

    def _rebuild_resource(self, resource_name, path, sign=False):
        if not path.exists():
            raise_error(f"{resource_name} does not exist at {path}!")

        resource_hash = compute_resource_hash(resource_name)
        cached_hash, computed_hash = compute_file_hash(path)
        if cached_hash != computed_hash:
            backup_path = Path(str(path) + ".bak")
            path.rename(backup_path)
            copy_resource(resource_name, path, sign=sign)
            return
        if resource_hash != cached_hash:
            copy_resource(resource_name, path, sign=sign)
            return