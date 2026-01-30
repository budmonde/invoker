import hashlib
import re
import sys
from datetime import date
from importlib import metadata
from pathlib import Path

from util import InheritanceAnalyzer, is_editable_install_for_path, raise_error, warn

# Default namespace for core invoker resources
DEFAULT_NAMESPACE = "invoker"


class ResourceManager:
    """
    Handles resource hashing, file header signing, path resolution, and
    copying resources into a target project.

    Supports multiple resource sources via entry points. Plugins register
    under the "invoker.resources" entry point group and provide a callable
    that returns their resources directory path.

    Resource paths can be namespaced:
      - "script.py" -> uses default "invoker" namespace
      - "myplugin:custom_module.py" -> uses "myplugin" plugin namespace
    """

    _resource_sources = None  # Cache for discovered plugins

    @classmethod
    def _discover_resource_sources(cls) -> dict[str, Path]:
        """
        Discover all registered resource source plugins.
        Returns a dict mapping namespace -> resources directory path.
        """
        if cls._resource_sources is not None:
            return cls._resource_sources

        sources = {}

        # Add built-in invoker resources as default
        sources[DEFAULT_NAMESPACE] = Path(__file__).parent / "resources"

        # Discover plugins via entry points
        if sys.version_info >= (3, 10):
            eps = metadata.entry_points(group="invoker.resources")
        else:
            eps = metadata.entry_points().get("invoker.resources", [])

        for ep in eps:
            try:
                get_path_fn = ep.load()
                resources_path = get_path_fn()
                if resources_path.is_dir():
                    sources[ep.name] = resources_path
                else:
                    warn(
                        f"Plugin '{ep.name}' resources path does not exist: {resources_path}"
                    )
            except Exception as e:
                warn(f"Failed to load plugin '{ep.name}': {e}")

        cls._resource_sources = sources
        return sources

    @classmethod
    def clear_cache(cls):
        """Clear the cached resource sources (useful for testing)."""
        cls._resource_sources = None

    @classmethod
    def list_namespaces(cls) -> list[str]:
        """Return list of available resource namespaces."""
        return list(cls._discover_resource_sources().keys())

    @classmethod
    def _parse_namespaced_path(cls, resource_path: str) -> tuple[str, str]:
        """
        Parse a resource path into (namespace, relative_path).
        If no namespace prefix, defaults to "invoker".

        Examples:
          "script.py" -> ("invoker", "script.py")
          "myplugin:custom_module.py" -> ("myplugin", "custom_module.py")
        """
        if ":" in resource_path:
            namespace, rel_path = resource_path.split(":", 1)
            return namespace, rel_path
        return DEFAULT_NAMESPACE, resource_path

    @classmethod
    def _get_resources_path(cls, namespace: str = DEFAULT_NAMESPACE) -> Path:
        """Get the resources directory for a given namespace."""
        sources = cls._discover_resource_sources()
        if namespace not in sources:
            available = ", ".join(sorted(sources.keys()))
            raise_error(
                f"Unknown resource namespace '{namespace}'. Available: {available}"
            )
        return sources[namespace]

    @classmethod
    def _resolve_resource_path(cls, namespaced_path: str) -> tuple[str, Path]:
        """
        Resolve a namespaced resource path to its absolute path.
        Returns (namespace, resolved_path) tuple.
        """
        namespace, rel_path = cls._parse_namespaced_path(namespaced_path)
        resources_root = cls._get_resources_path(namespace).resolve()

        rel = Path(rel_path)
        if rel.is_absolute():
            raise_error("Absolute resource paths are not allowed.")

        candidate = (resources_root / rel).resolve()

        # Ensure candidate remains under resources directory
        try:
            candidate.relative_to(resources_root)
        except ValueError:
            raise_error("Resource path must be within the resources directory.")

        # Disallow importing anything from tests subdirectory
        tests_dir = (resources_root / "tests").resolve()
        try:
            candidate.relative_to(tests_dir)
            raise_error("Resources under 'tests' are not importable.")
        except ValueError:
            pass

        return namespace, candidate

    @staticmethod
    def _get_header_template_path() -> Path:
        """Get the header template from the templates directory."""
        return Path(__file__).parent / "templates" / "header.txt"

    @classmethod
    def build_invoker_header(cls, namespaced_path: str):
        """
        Build the invoker header lines for a given resource path.
        Computes the resource file hash internally.
        Returns a list of strings (each ending with newline) for callers to write.
        """
        namespace, resource_path = cls._resolve_resource_path(namespaced_path)
        with resource_path.open("rb") as f:
            file_hash = cls._compute_hash(f.read())

        # Store the full namespaced path in the header for later reference
        _, rel_path = cls._parse_namespaced_path(namespaced_path)
        if namespace != DEFAULT_NAMESPACE:
            resource_ref = f"{namespace}:{rel_path}"
        else:
            resource_ref = rel_path

        template = cls._get_header_template_path().read_text(encoding="utf-8")
        formatted = template.format(
            version=metadata.version("invoker"),
            resource=resource_ref,
            date=date.today().strftime("%Y-%m-%d"),
            hash=file_hash,
        )
        return [formatted]

    @classmethod
    def parse_invoker_header(cls, path: Path):
        """
        Parse the top of a file and determine if it contains an invoker header.
        The header is matched using a regex generated from the header template.
        If matched, returns (num_lines, fields) where:
          - num_lines is the number of lines occupied by the header template
          - fields is a dict with keys: version, resource, date, hash
        Otherwise returns (0, {}).
        """
        template = cls._get_header_template_path().read_text(encoding="utf-8")
        # Build a regex from the template by escaping literal text
        # and replacing placeholders with capturing groups.
        pattern = re.escape(template)
        pattern = pattern.replace(re.escape("{version}"), r"(?P<version>\d+\.\d+\.\d+)")
        pattern = pattern.replace(re.escape("{resource}"), r"(?P<resource>[^\n]+)")
        pattern = pattern.replace(re.escape("{date}"), r"(?P<date>\d{4}-\d{2}-\d{2})")
        pattern = pattern.replace(re.escape("{hash}"), r"(?P<hash>[0-9a-f]{32})")
        # Match from start of file
        text = path.read_text(encoding="utf-8")
        m = re.match(pattern, text)
        if not m:
            return 0, {}
        header_num_lines = len(template.splitlines())
        return header_num_lines, {
            "version": m.group("version"),
            "resource": m.group("resource"),
            "date": m.group("date"),
            "hash": m.group("hash"),
        }

    @classmethod
    def strip_invoker_header(cls, path: Path):
        """
        Remove invoker-generated header (including resource line and trailing blanks)
        from the top of a file at 'path', if present. Returns a new list of lines.
        """
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        header_num_lines, _ = cls.parse_invoker_header(path)
        if header_num_lines == 0:
            return lines
        idx = header_num_lines
        # Skip any following blank lines
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1
        return lines[idx:]

    @staticmethod
    def _compute_hash(raw_bytes: bytes) -> str:
        hasher = hashlib.md5()
        hasher.update(raw_bytes)
        return hasher.hexdigest()

    @classmethod
    def compute_resource_hash(cls, namespaced_path: str) -> str:
        """Compute the hash of a resource file."""
        _, resource_path = cls._resolve_resource_path(namespaced_path)
        try:
            with resource_path.open("rb") as f:
                return cls._compute_hash(f.read())
        except FileNotFoundError:
            raise_error(f"Resource not found: {namespaced_path}")

    @classmethod
    def compute_file_hash(cls, path: Path) -> tuple[str, str]:
        """
        Compute hashes for a file with an invoker header.
        Returns (stored_hash, computed_hash) tuple.
        """
        header_num_lines, fields = cls.parse_invoker_header(path)
        if header_num_lines == 0:
            raise_error(f"Missing invoker header in file '{path}'.")
        stored_hash = fields["hash"]
        stripped_lines = cls.strip_invoker_header(path)
        computed_hash = cls._compute_hash("".join(stripped_lines).encode("ascii"))
        return stored_hash, computed_hash

    @classmethod
    def import_resource(
        cls,
        namespaced_path: str,
        dst_path: Path,
        sign: bool = False,
        preprocess_fn=lambda line: line,
    ):
        """
        Import a resource into a project.

        Args:
            namespaced_path: Resource path, optionally with namespace prefix
                            (e.g., "script.py" or "myplugin:custom_module.py")
            dst_path: Destination path in the project
            sign: Whether to add invoker header to the file
            preprocess_fn: Optional function to transform each line
        """
        _, resource_path = cls._resolve_resource_path(namespaced_path)
        with resource_path.open("r", encoding="utf-8") as inf, open(
            dst_path, "w"
        ) as outf:
            if sign:
                header_lines = cls.build_invoker_header(namespaced_path)
                outf.writelines(header_lines)
            for line in inf:
                outf.write(preprocess_fn(line))

    @classmethod
    def is_namespace_editable(cls, namespace: str) -> bool:
        """Check if a namespace's resources are in an editable installation."""
        resources_path = cls._get_resources_path(namespace)
        return is_editable_install_for_path(resources_path)

    @classmethod
    def export_resource(cls, src_path: Path, namespaced_dest: str):
        """
        Export a project file to a resource namespace.

        Args:
            src_path: Source file path in the project
            namespaced_dest: Destination with required namespace prefix
                            (e.g., "myplugin:custom_module.py" or "invoker:util/helper.py")

        Raises:
            SystemExit: If namespace is missing, unknown, or not editable
        """
        # Require explicit namespace for export
        if ":" not in namespaced_dest:
            raise_error(
                f"Export requires explicit namespace prefix (e.g., 'invoker:{namespaced_dest}' "
                f"or 'myplugin:{namespaced_dest}'). Available namespaces: {', '.join(cls.list_namespaces())}"
            )

        namespace, rel_path = cls._parse_namespaced_path(namespaced_dest)

        # Check if namespace exists
        sources = cls._discover_resource_sources()
        if namespace not in sources:
            available = ", ".join(sorted(sources.keys()))
            raise_error(
                f"Unknown resource namespace '{namespace}'. Available: {available}"
            )

        # Check if namespace is editable
        if not cls.is_namespace_editable(namespace):
            raise_error(
                f"Cannot export to '{namespace}': package is not installed in editable mode. "
                f"Reinstall with 'pip install -e .' to enable exports."
            )

        dest = cls._get_resources_path(namespace) / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)

        header_num_lines, _ = cls.parse_invoker_header(src_path)
        if header_num_lines > 0:
            cls._export_existing_resource(src_path, dest)
        else:
            cls._export_new_resource(src_path, dest)

    @classmethod
    def _export_existing_resource(cls, src_path: Path, dest: Path):
        """
        Export logic for an existing invoker-generated file (has header).
        - If stored hash == computed hash: skip export (no manual edits).
        - Else: overwrite destination with stripped content.
        """
        stored_hash, computed_hash = cls.compute_file_hash(src_path)
        if stored_hash == computed_hash:
            warn(f"No changes detected in '{src_path}'. Skipping export.")
            return

        cleaned_lines = cls.strip_invoker_header(src_path)
        cleaned_text = "".join(cleaned_lines)
        if dest.exists():
            warn(f"Overwriting existing resource at {dest}")
        with open(dest, "w", encoding="utf-8") as outf:
            outf.write(cleaned_text)

    @classmethod
    def _export_new_resource(cls, src_path: Path, dest: Path):
        """
        Export logic for a new resource (no header present).
        Simply write the file content as-is to the destination.
        """
        text = src_path.read_text(encoding="utf-8")
        with open(dest, "w", encoding="utf-8") as outf:
            outf.write(text)

    # -------------------------------------------------------------------------
    # Module (directory) import/export support
    # -------------------------------------------------------------------------

    @classmethod
    def resolve_resource_type(cls, namespaced_path: str) -> str:
        """
        Determine if a resource path refers to a file, module (directory), or is ambiguous.

        Resolution rules:
          - Ends with "/" -> module
          - Ends with ".py" or other extension -> file
          - Otherwise -> check if both file and directory exist

        Returns: "file", "module", or "ambiguous"
        Raises: SystemExit if resource doesn't exist
        """
        namespace, rel_path = cls._parse_namespaced_path(namespaced_path)
        resources_root = cls._get_resources_path(namespace).resolve()

        # Explicit module reference (trailing slash)
        if rel_path.endswith("/"):
            return "module"

        # Explicit file reference (has extension)
        if "." in Path(rel_path).name:
            return "file"

        # Ambiguous - check what exists
        file_path = resources_root / f"{rel_path}.py"
        dir_path = resources_root / rel_path

        file_exists = file_path.exists()
        dir_exists = dir_path.is_dir()

        if file_exists and dir_exists:
            return "ambiguous"
        elif dir_exists:
            return "module"
        elif file_exists:
            return "file"
        else:
            # Neither exists - check if it could be a file without .py extension
            if (resources_root / rel_path).exists():
                return "file"
            raise_error(
                f"Resource not found: {namespaced_path}. "
                f"Neither '{rel_path}.py' nor '{rel_path}/' exists in namespace '{namespace}'."
            )

    @classmethod
    def get_module_files(
        cls, module_path: Path, auto_discover: bool = False
    ) -> list[str]:
        """
        Get the list of files belonging to a module from its __init__.py.

        Reads the __invoker_files__ variable from the module's __init__.py.
        Always includes __init__.py itself in the returned list.

        Args:
            module_path: Path to the module directory
            auto_discover: If True and __invoker_files__ not found, auto-discover
                          files that contain InvokerModule subclasses

        Returns: List of relative file paths within the module
        Raises: SystemExit if __init__.py doesn't exist (and not auto_discover)
        """
        init_path = module_path / "__init__.py"
        if not init_path.exists():
            raise_error(f"Module __init__.py not found: {init_path}")

        init_content = init_path.read_text(encoding="utf-8")

        # Parse __invoker_files__ from the init file
        # Look for: __invoker_files__ = [...]
        match = re.search(
            r"__invoker_files__\s*=\s*\[(.*?)\]",
            init_content,
            re.DOTALL,
        )

        if match:
            # Extract file list from the match
            files_str = match.group(1)
            # Parse the list items (handles both single and double quotes)
            files = re.findall(r'["\']([^"\']+)["\']', files_str)
        elif auto_discover:
            # Auto-discover files containing InvokerModule subclasses
            warn(
                f"Module {module_path.name} does not have __invoker_files__ defined in __init__.py. "
                f"Auto-discovering InvokerModule files..."
            )
            files = cls._discover_module_files(module_path)
        else:
            raise_error(
                f"Module {module_path.name} does not have __invoker_files__ defined in __init__.py. "
                f"Add __invoker_files__ = ['file1.py', 'file2.py', ...] to track module files."
            )

        # Always include __init__.py
        if "__init__.py" not in files:
            files = ["__init__.py"] + files

        return files

    @classmethod
    def _file_has_invoker_module_subclass(cls, content: str) -> bool:
        """
        Check if a Python file contains any class that inherits from InvokerModule.

        Uses AST parsing to accurately detect inheritance, including transitive
        inheritance (e.g., Foo inherits from Bar which inherits from InvokerModule).

        Args:
            content: The Python source code to analyze

        Returns: True if the file contains an InvokerModule subclass
        """
        analyzer = InheritanceAnalyzer(content)
        return analyzer.has_subclass_of("invoker", "InvokerModule")

    @classmethod
    def _discover_module_files(cls, module_path: Path) -> list[str]:
        """
        Auto-discover files in a module that contain InvokerModule subclasses.

        Scans all .py files in the module directory (non-recursive) and uses
        AST parsing to detect classes that inherit from InvokerModule, including
        transitive inheritance (e.g., Foo -> Bar -> InvokerModule).

        Returns: List of discovered file names
        """
        discovered = []

        for py_file in module_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                if cls._file_has_invoker_module_subclass(content):
                    discovered.append(py_file.name)
            except Exception:
                # Skip files that can't be read
                pass

        # Also include common config file patterns
        for config_pattern in ["*.yaml", "*.yml", "*.json", "*.toml"]:
            for config_file in module_path.glob(config_pattern):
                discovered.append(config_file.name)

        return sorted(discovered)

    @classmethod
    def _update_init_invoker_files(cls, module_path: Path, files: list[str]):
        """
        Update the __init__.py file with the discovered __invoker_files__ list.

        If __invoker_files__ doesn't exist, append it to the file.
        """
        init_path = module_path / "__init__.py"
        init_content = init_path.read_text(encoding="utf-8")

        # Filter out __init__.py from the list we write
        files_to_write = [f for f in files if f != "__init__.py"]

        # Format the list
        files_formatted = ",\n    ".join(f'"{f}"' for f in files_to_write)
        invoker_files_block = f"""__invoker_files__ = [
    {files_formatted},
]
"""

        # Check if __invoker_files__ already exists
        if "__invoker_files__" in init_content:
            # Replace existing definition
            init_content = re.sub(
                r"__invoker_files__\s*=\s*\[.*?\]",
                invoker_files_block.strip(),
                init_content,
                flags=re.DOTALL,
            )
        else:
            # Append to file
            if not init_content.endswith("\n"):
                init_content += "\n"
            init_content += f"\n{invoker_files_block}"

        init_path.write_text(init_content, encoding="utf-8")

    @classmethod
    def import_module(
        cls,
        namespaced_path: str,
        dst_dir: Path,
        sign_python_files: bool = True,
    ):
        """
        Import an entire module (directory) into a project.

        Args:
            namespaced_path: Module path with optional namespace prefix
                            (e.g., "data_loader" or "myplugin:data_loader/")
            dst_dir: Destination directory in the project
            sign_python_files: Whether to add invoker headers to .py files
        """
        namespace, rel_path = cls._parse_namespaced_path(namespaced_path)

        # Strip trailing slash if present
        rel_path = rel_path.rstrip("/")

        resources_root = cls._get_resources_path(namespace).resolve()
        module_src = resources_root / rel_path

        if not module_src.is_dir():
            raise_error(
                f"Module not found: {namespaced_path} (expected directory at {module_src})"
            )

        # Get list of files to import
        files = cls.get_module_files(module_src)

        # Create destination directory
        dst_dir.mkdir(parents=True, exist_ok=True)

        # Import each file
        for filename in files:
            src_file = module_src / filename
            dst_file = dst_dir / filename

            if not src_file.exists():
                warn(
                    f"File listed in __invoker_files__ not found: {src_file}. Skipping."
                )
                continue

            # Create parent directories if needed (for nested files)
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            # Determine if we should sign this file
            should_sign = (
                sign_python_files
                and filename.endswith(".py")
                and filename != "__init__.py"
            )

            if should_sign:
                # Build namespaced path for the file
                file_namespaced = (
                    f"{namespace}:{rel_path}/{filename}"
                    if namespace != DEFAULT_NAMESPACE
                    else f"{rel_path}/{filename}"
                )
                cls.import_resource(file_namespaced, dst_file, sign=True)
            else:
                # Copy file as-is (config files, __init__.py, etc.)
                import shutil

                shutil.copy2(src_file, dst_file)

    @classmethod
    def export_module(cls, src_dir: Path, namespaced_dest: str):
        """
        Export an entire module (directory) to a resource namespace.

        Args:
            src_dir: Source module directory in the project
            namespaced_dest: Destination with required namespace prefix
                            (e.g., "myplugin:data_loader" or "invoker:util/helper_module")

        Raises:
            SystemExit: If namespace is missing, unknown, not editable, or module invalid
        """
        # Require explicit namespace for export
        if ":" not in namespaced_dest:
            raise_error(
                f"Export requires explicit namespace prefix (e.g., 'invoker:{namespaced_dest}' "
                f"or 'myplugin:{namespaced_dest}'). Available namespaces: {', '.join(cls.list_namespaces())}"
            )

        namespace, rel_path = cls._parse_namespaced_path(namespaced_dest)
        rel_path = rel_path.rstrip("/")

        # Check if namespace exists and is editable
        sources = cls._discover_resource_sources()
        if namespace not in sources:
            available = ", ".join(sorted(sources.keys()))
            raise_error(
                f"Unknown resource namespace '{namespace}'. Available: {available}"
            )

        if not cls.is_namespace_editable(namespace):
            raise_error(
                f"Cannot export to '{namespace}': package is not installed in editable mode. "
                f"Reinstall with 'pip install -e .' to enable exports."
            )

        if not src_dir.is_dir():
            raise_error(f"Source module directory not found: {src_dir}")

        # Get list of files to export (with auto-discovery if __invoker_files__ not set)
        files = cls.get_module_files(src_dir, auto_discover=True)

        # If files were auto-discovered, update the __init__.py
        init_content = (src_dir / "__init__.py").read_text(encoding="utf-8")
        if "__invoker_files__" not in init_content:
            cls._update_init_invoker_files(src_dir, files)
            warn(f"Updated {src_dir / '__init__.py'} with discovered __invoker_files__")

        dest_dir = cls._get_resources_path(namespace) / rel_path
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Export each file
        for filename in files:
            src_file = src_dir / filename
            dest_file = dest_dir / filename

            if not src_file.exists():
                warn(
                    f"File listed in __invoker_files__ not found: {src_file}. Skipping."
                )
                continue

            # Create parent directories if needed
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Check if this is a Python file with an invoker header
            if filename.endswith(".py") and filename != "__init__.py":
                header_num_lines, _ = cls.parse_invoker_header(src_file)
                if header_num_lines > 0:
                    cls._export_existing_resource(src_file, dest_file)
                else:
                    cls._export_new_resource(src_file, dest_file)
            else:
                # Copy non-Python files and __init__.py as-is
                cls._export_new_resource(src_file, dest_file)
