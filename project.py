import re
import subprocess
from importlib import metadata
from pathlib import Path

from resource_manager import ResourceManager
from util import raise_error, to_camel_case, warn


class Project:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.invoker_path = root_path / "invoker.py"
        self.project_version = None

    def initialize(self):
        if self.invoker_path.exists():
            raise_error(f"invoker module already exists at {self.invoker_path}!")
        ResourceManager.import_resource("invoker.py", self.invoker_path, sign=True)
        self.project_version = metadata.version("invoker")
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
            error_message = (
                f"Cannot determine project version from {self.invoker_path}."
            )
            raise_error(error_message) if error_on_mismatch else warn(error_message)
            return

        if self.project_version != metadata.version("invoker"):
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
        subprocess.call(["black", self.root_path])
        subprocess.call(["isort", self.root_path])
        subprocess.call(["flake8", self.root_path])

    def create_module(self, module_name):
        # Create module directory
        module_path = self.root_path / module_name
        if module_path.exists():
            raise_error(f"module already exists at {module_path}!")
        module_path.mkdir()

        # Create __init__.py with __invoker_files__ tracking
        module_init_path = module_path / "__init__.py"
        base_filename = f"base_{module_name}.py"
        init_template_path = Path(__file__).parent / "templates" / "module_init.txt"
        init_content = init_template_path.read_text(encoding="utf-8").format(
            module_name=module_name,
            base_filename=base_filename,
        )
        module_init_path.write_text(init_content, encoding="utf-8")

        # Add boilerplate module base class resource
        module_base_path = module_path / base_filename
        ResourceManager.import_resource(
            "module_base.py",
            module_base_path,
            preprocess_fn=lambda line: line.replace(
                "__MODULE__", to_camel_case(module_name)
            ),
        )

    def create_script(self, script_name):
        # Fix script name
        if script_name.endswith(".py"):
            script_name = script_name.removesuffix(".py")
        # Add boilerplate base script
        script_path = self.root_path / f"{script_name}.py"
        if script_path.exists():
            raise_error(f"script already exists at {script_path}!")
        ResourceManager.import_resource(
            "script.py",
            script_path,
            preprocess_fn=lambda line: line.replace(
                "__SCRIPT__", to_camel_case(script_name)
            ),
        )
        script_path.chmod(0o744)

    def run_script(self, script_name):
        # Fix script name
        if not script_name.endswith(".py"):
            script_name = script_name + ".py"
        script_path = self.root_path / f"{script_name}"
        if not script_path.exists():
            raise_error(f"script does not exist at {script_path}!")
        subprocess.call(["python", "invoker.py", "run", script_name])

    def debug_script(self, script_name_with_line_num):
        script_match = re.match(r"^(\w+\.\w+)(?::(\d+))?$", script_name_with_line_num)
        if not script_match:
            raise_error(
                f"Invalid script name format: {script_name_with_line_num}. "
                "Expected format: script.py or script.py:line_number"
            )

        script_name = script_match.group(1)

        script_path = self.root_path / f"{script_name}"
        if not script_path.exists():
            raise_error(f"script does not exist at {script_path}!")
        subprocess.call(["python", "invoker.py", "debug", script_name_with_line_num])

    def import_resource(self, namespaced_path: str, dest_rel_path: str = None):
        """
        Import a resource (file or module) into the project.

        Args:
            namespaced_path: Resource path, optionally with namespace prefix
                            (e.g., "script.py", "myplugin:custom.py", "data_loader/")
            dest_rel_path: Optional destination path in project (defaults to
                          the relative path portion of namespaced_path)

        Resolution rules:
          - Ends with "/" -> module directory
          - Ends with ".py" or other extension -> single file
          - Otherwise -> auto-detect (error if ambiguous)
        """
        self.validate()

        resource_type = ResourceManager.resolve_resource_type(namespaced_path)

        if resource_type == "ambiguous":
            if ":" in namespaced_path:
                namespace, rel_path = namespaced_path.split(":", 1)
                raise_error(
                    f"Ambiguous resource path '{namespaced_path}': both '{rel_path}.py' and '{rel_path}/' exist. "
                    f"Use '{namespace}:{rel_path}.py' for the file or '{namespace}:{rel_path}/' for the module."
                )
            else:
                raise_error(
                    f"Ambiguous resource path '{namespaced_path}': both '{namespaced_path}.py' and '{namespaced_path}/' exist. "
                    f"Use '{namespaced_path}.py' for the file or '{namespaced_path}/' for the module."
                )

        if ":" in namespaced_path:
            _, rel_path = namespaced_path.split(":", 1)
        else:
            rel_path = namespaced_path

        rel_path = rel_path.rstrip("/")

        target_rel_path = dest_rel_path if dest_rel_path is not None else rel_path

        if resource_type == "module":
            self._import_module(namespaced_path, target_rel_path)
        else:
            self._import_file(namespaced_path, target_rel_path)

    def _import_file(self, namespaced_path: str, target_rel_path: str):
        """Import a single file resource."""
        dest_path = self.root_path / target_rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if dest_path.exists():
            backup_path = Path(str(dest_path) + ".bak")
            warn(
                f"Overwriting existing file at {dest_path}. Backing up to {backup_path}"
            )
            if backup_path.exists():
                raise_error(
                    f"Backup file already exists: {backup_path}. Aborting import."
                )
            dest_path.rename(backup_path)

        ResourceManager.import_resource(namespaced_path, dest_path, sign=True)

    def _import_module(self, namespaced_path: str, target_rel_path: str):
        """Import a module directory."""
        dest_dir = self.root_path / target_rel_path

        if dest_dir.exists():
            backup_dir = Path(str(dest_dir) + ".bak")
            warn(
                f"Overwriting existing module at {dest_dir}. Backing up to {backup_dir}"
            )
            if backup_dir.exists():
                raise_error(
                    f"Backup directory already exists: {backup_dir}. Aborting import."
                )
            dest_dir.rename(backup_dir)

        ResourceManager.import_module(namespaced_path, dest_dir)

    def export_resource(self, src_rel_path: str, namespaced_dest: str):
        """
        Export a project file or module to a resource namespace.

        Args:
            src_rel_path: Source file/directory path relative to project root
            namespaced_dest: Destination with required namespace prefix
                            (e.g., "myplugin:custom.py" or "myplugin:data_loader/")

        Resolution rules:
          - If src_rel_path is a directory -> export as module
          - If src_rel_path is a file -> export as file
        """
        self.validate()
        src = self.root_path / src_rel_path

        if not src.exists():
            raise_error(f"Source does not exist: {src}")

        if src.is_dir():
            ResourceManager.export_module(src, namespaced_dest)
        else:
            # Export as file
            ResourceManager.export_resource(src, namespaced_dest)

    def rebuild(self):
        self.check_version(error_on_mismatch=True)
        for path in self.root_path.rglob("*.py"):
            header_num_lines, fields = ResourceManager.parse_invoker_header(path)
            if header_num_lines == 0:
                continue
            resource_name = fields.get("resource")
            if not resource_name:
                warn(f"Missing resource name in header for '{path}'. Skipping.")
                continue
            self._rebuild_resource(resource_name, path, sign=True)

    def _rebuild_resource(self, resource_name, path, sign=False):
        if not path.exists():
            raise_error(f"{resource_name} does not exist at {path}!")

        resource_hash = ResourceManager.compute_resource_hash(resource_name)
        cached_hash, computed_hash = ResourceManager.compute_file_hash(path)
        if cached_hash != computed_hash:
            backup_path = Path(str(path) + ".bak")
            path.rename(backup_path)
            ResourceManager.import_resource(resource_name, path, sign=sign)
            return
        if resource_hash != cached_hash:
            ResourceManager.import_resource(resource_name, path, sign=sign)
            return
