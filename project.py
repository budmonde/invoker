from pathlib import Path
import re
import subprocess

from util import copy_resource, compute_resource_hash, compute_file_hash, to_camel_case

class InvokerError(Exception):
    pass

class Project:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.invoker_path = root_path / "invoker.py"

    def initialize(self):
        if self.invoker_path.exists():
            raise InvokerError(f"invoker module already exists at {self.invoker_path}.")
        copy_resource("invoker.resource.py", self.invoker_path, sign=True)
        self.validate()
        return self

    def load(self):
        self.validate()
        return self

    def validate(self):
        if not self.invoker_path.exists():
            raise InvokerError("invoker.py file is missing in project.")
        return True

    def lint(self):
        subprocess.call(['black', self.root_path])
        subprocess.call(['isort', self.root_path])
        subprocess.call(['flake8', self.root_path])

    def create_module(self, module_name):
        # Create module directory
        module_path = self.root_path / module_name
        if module_path.exists():
            raise InvokerError(f"module already exists at {module_path}.")
        module_path.mkdir()

        # Generate module __init__.py resource
        module_init_path = module_path / "__init__.py"
        copy_resource("module_init.resource.py", module_init_path, sign=True)

        # Add boilerplate module base class resource
        module_base_path = module_path / f"base_{module_name}.py"
        copy_resource(
            "module_base.resource.py",
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
            raise InvokerError(f"script already exists at {script_path}.")
        copy_resource(
            "script.resource.py",
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
            raise InvokerError(f"script does not exist at {script_path}.")
        subprocess.call(['python', 'invoker.py', 'run', script_name])

    def debug_script(self, script_name_with_line_num):
        script_match = re.match(r"^(\w+\.\w+)(?::(\d+))?$", script_name_with_line_num)
        script_name = script_match.group(1)
        embed_line_num = int(script_match.group(2)) if script_match.group(2) else None

        script_path = self.root_path / f"{script_name}"
        if not script_path.exists():
            raise InvokerError(f"script does not exist at {script_path}.")
        subprocess.call(['python', 'invoker.py', 'debug', script_name_with_line_num])

    def create_workflow(self, workflow_name):
        # Fix workflow name
        if workflow_name.endswith(".py"):
            workflow_name = workflow_name.removesuffix(".py")
        # Add boilerplate base workflow
        workflow_path = self.root_path / f"{workflow_name}.py"
        if workflow_path.exists():
            raise InvokerError(f"workflow already exists at {workflow_path}.")
        copy_resource(
            "workflow.resource.py",
            workflow_path,
            preprocess_fn=lambda l: l.replace("__WORKFLOW__", to_camel_case(workflow_name)),
        )
        workflow_path.chmod(0o744)

    def rebuild(self):
        self._rebuild_resource("invoker.resource.py", self.invoker_path, sign=True)
        for path in self.root_path.iterdir():
            if not path.is_dir():
                continue
            init_path = path / "__init__.py"
            if not init_path.exists():
                continue
            with open(init_path) as init_f:
                if not init_f.readline().startswith("# Invoker: v0.0.1"):
                    continue
            self._rebuild_resource("module_init.resource.py", init_path, sign=True)

    def _rebuild_resource(self, resource_name, path, sign=False):
        if not path.exists():
            raise InvokerError(f"{resource_name} does not exist at {path}!")

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
