import ast

import click


def raise_error(message):
    click.secho("Invoker Error: ", err=True, nl=False, fg="red")
    click.echo(message, err=True)
    raise SystemExit(1)


def warn(message):
    click.secho("Invoker Warning: ", err=True, nl=False, fg="yellow")
    click.echo(message, err=True)


def to_camel_case(string):
    return "".join([token.capitalize() for token in string.split("_")])


def is_editable_install_for_path(path) -> bool:
    """
    Heuristic check: returns False if path is under site-packages/dist-packages,
    True otherwise (e.g., editable/develop install from a local checkout).
    """
    from pathlib import Path

    resolved = Path(path).resolve()
    for parent in [resolved] + list(resolved.parents):
        name = parent.name.lower()
        if name in ("site-packages", "dist-packages"):
            return False
    return True


def is_editable_install() -> bool:
    """
    Check if the main invoker package is installed in editable mode.
    """
    from pathlib import Path

    resources_root = (Path(__file__).parent / "resources").resolve()
    return is_editable_install_for_path(resources_root)


class InheritanceAnalyzer:
    """
    Analyzes Python source code to detect class inheritance relationships.

    Uses AST parsing to accurately detect inheritance, including transitive
    inheritance chains (e.g., Foo inherits from Bar which inherits from Base).
    """

    def __init__(self, source: str):
        """
        Initialize the analyzer with Python source code.

        Args:
            source: Python source code to analyze
        """
        self._source = source
        self._tree = None
        self._imports: dict[str, set[str]] = {}  # module -> set of imported names
        self._class_bases: dict[str, list[str]] = {}  # class name -> base class names
        self._parsed = False

    def _parse(self):
        """Parse the source code and build internal data structures."""
        if self._parsed:
            return

        try:
            self._tree = ast.parse(self._source)
        except SyntaxError:
            self._parsed = True
            return

        # Extract imports: track module -> names imported from it
        for node in ast.walk(self._tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module not in self._imports:
                    self._imports[node.module] = set()
                for alias in node.names:
                    # Use the alias name if present, otherwise the original name
                    name = alias.asname if alias.asname else alias.name
                    self._imports[node.module].add(name)

        # Build class -> bases map
        for node in ast.walk(self._tree):
            if isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        # Handle module.ClassName style
                        bases.append(base.attr)
                self._class_bases[node.name] = bases

        self._parsed = True

    def get_imports_from(self, module: str) -> set[str]:
        """
        Get the set of names imported from a specific module.

        Args:
            module: The module name (e.g., "invoker")

        Returns: Set of imported names (using aliases if present)
        """
        self._parse()
        return self._imports.get(module, set())

    def get_class_bases(self, class_name: str) -> list[str]:
        """
        Get the base classes of a specific class.

        Args:
            class_name: The name of the class

        Returns: List of base class names
        """
        self._parse()
        return self._class_bases.get(class_name, [])

    def get_all_classes(self) -> list[str]:
        """
        Get all class names defined in the source.

        Returns: List of class names
        """
        self._parse()
        return list(self._class_bases.keys())

    def inherits_from(self, class_name: str, target_bases: set[str]) -> bool:
        """
        Check if a class inherits from any of the target base classes.

        Handles transitive inheritance within the same file.

        Args:
            class_name: The class to check
            target_bases: Set of base class names to check against

        Returns: True if class_name inherits from any target base
        """
        self._parse()
        return self._inherits_from_recursive(class_name, target_bases, set())

    def _inherits_from_recursive(
        self, class_name: str, target_bases: set[str], visited: set[str]
    ) -> bool:
        """Recursive helper for inheritance checking."""
        if class_name in visited:
            return False  # Avoid infinite loops from circular inheritance
        visited.add(class_name)

        if class_name in target_bases:
            return True

        if class_name not in self._class_bases:
            return False

        for base in self._class_bases[class_name]:
            if base in target_bases:
                return True
            if self._inherits_from_recursive(base, target_bases, visited):
                return True

        return False

    def has_subclass_of(self, module: str, class_name: str) -> bool:
        """
        Check if the source contains any class that inherits from a specific
        class imported from a specific module.

        Args:
            module: The module the target class is imported from (e.g., "invoker")
            class_name: The class name to check inheritance from (e.g., "InvokerModule")

        Returns: True if any class in the source inherits from the target class
        """
        self._parse()

        # Get all names that refer to the target class (handles aliasing)
        target_names = set()
        if module in self._imports:
            for name in self._imports[module]:
                # Check if this import corresponds to our target class
                # We need to check the original AST to handle aliases
                if self._tree:
                    for node in ast.walk(self._tree):
                        if isinstance(node, ast.ImportFrom) and node.module == module:
                            for alias in node.names:
                                if alias.name == class_name:
                                    imported_as = (
                                        alias.asname if alias.asname else alias.name
                                    )
                                    target_names.add(imported_as)

        if not target_names:
            return False

        # Check if any class inherits from the target
        for cls in self._class_bases:
            if self.inherits_from(cls, target_names):
                return True

        return False
