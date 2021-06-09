import yaml
from pathlib import Path
import subprocess

from util import copy_resource, compute_resource_hash, compute_file_hash, to_camel_case

class Project:
    @property
    def scripts(self):
        return sorted(self.config["scripts"].keys())

    @property
    def modules(self):
        return sorted(self.config["modules"])

    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.options_path = root_path / "options.py"
        self.config_path = root_path / ".invoker"
        self.loaded = False

    def initialize(self):
        if self.options_path.exists():
            raise Exception(f"options.py file already exists at {self.options_path}.")
        copy_resource("options.py", self.options_path, sign=True)

        if self.config_path.exists():
            raise Exception(f"project.conf file already exists at {self.config_path}.")

        self.config = {"scripts": {}, "modules": []}
        self.commit_config_update()
        self.loaded = True
        self.validate()
        return self

    def load(self):
        self.config = yaml.load(open(self.config_path), Loader=yaml.FullLoader)
        self.loaded = True
        self.validate()
        return self

    def validate(self):
        if not self.loaded:
            raise Exception("Cannot validate project state before loading it.")

        if not self.options_path.exists():
            raise Exception("options.py file is missing in project.")
        if not self.config_path.exists():
            raise Exception("project.conf file is missing in project.")
        for script_name in self.scripts:
            script_path = self.root_path / f"{script_name}.py"
            if not script_path.exists():
                raise Exception(f"Script {script_name} is missing in project.")
        for module_name in self.modules:
            module_path = self.root_path / module_name
            if not module_path.is_dir():
                raise Exception(f"Module {module_name} is missing in project.")
            module_init_path = module_path / "__init__.py"
            if not module_init_path.exists():
                raise Exception(f"Module {module_name} is missing __init__.py file.")

        return True

    def lint(self):
        subprocess.call(['black', self.root_path])
        subprocess.call(['isort', self.root_path])
        subprocess.call(['flake8', self.root_path])

    def create_module(self, module_name):
        if module_name in self.modules:
            raise Exception(f"Module {module_name} already exists in this project.")

        # Add module to project config
        self.config["modules"].append(module_name)
        self.commit_config_update()

        # Create module directory
        module_path = self.root_path / module_name
        module_path.mkdir()

        # Generate module __init__.py resource
        module_init_path = module_path / "__init__.py"
        copy_resource("module_init.py", module_init_path, sign=True)

        # Add boilerplate module base class
        module_base_path = module_path / f"base_{module_name}.py"
        copy_resource(
            "module_base.py",
            module_base_path,
            preprocess_fn=lambda l: l.replace("Module", to_camel_case(module_name)),
        )

    def create_script(self, script_name):
        if script_name in self.scripts:
            raise Exception(f"Script {script_name} already exists in this project.")

        # Add script to project config
        self.config["scripts"][script_name] = []
        self.commit_config_update()

        # Add boilerplate base script
        script_path = self.root_path / f"{script_name}.py"
        copy_resource(
            "script.py",
            script_path,
            preprocess_fn=lambda l: l.replace("script", script_name),
        )

    def update_script_add_module(self, script_name, module_name):
        if not script_name in self.scripts:
            raise Exception(f"Script {script_name} does not exist in this project.")
        if not module_name in self.modules:
            raise Exception(f"Module {module_name} does not exist in this project.")
        if module_name in self.config["scripts"][script_name]:
            raise Exception(f"Script {script_name} already imports module {module_name}.")

        # Add module to script config
        self.config["scripts"][script_name].append(module_name)
        self.commit_config_update()

        # Import module to script
        script_path = self.root_path / f"{script_name}.py"
        with open(script_path, "r") as f:
            buf = f.readlines()

        with open(script_path, "w") as f:
            for line in buf:
                if line == "from options import build as build_options\n":
                    line += f"from {module_name} import build as build_{module_name}\n"
                if line == f'    opt = build_options(mode="{script_name}")\n':
                    line += f"    {module_name} = build_{module_name}(opt)\n"
                if line == "CONFIG = {\n":
                    line += f'    "{module_name}_mode": "base",\n'
                f.write(line)

    def commit_config_update(self):
        yaml.dump(self.config, open(self.config_path, "w"), indent=4, sort_keys=True)

    def rebuild(self):
        _rebuild_resource("options.py", self.options_path, sign=True)
        for module_name in self.modules:
            module_init_path = self.root_path / module_name / "__init__.py"
            _rebuild_resource("module_init.py", module_init_path, sign=True)

    def _rebuild_resource(self, resource_name, path, sign=False):
        if not dst_path.exists():
            raise Exception(f"{resource_name} does not exist at {dst_path}!")

        resource_hash = compute_resource_hash(resource_name)
        cached_hash, computed_hash = compute_file_hash(dst_path)
        if cached_hash != computed_hash:
            backup_path = Path(str(dst_path) + ".bak")
            dst_path.rename(backup_path)
            copy_resource(resource_name, dst_path, sign=sign)
            return
        if resource_hash != cached_hash:
            copy_resource(resource_name, dst_path, sign=sign)
            return
