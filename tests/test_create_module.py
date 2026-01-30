"""Integration tests for invoker create module command."""

import pytest

from project import Project
from util import to_camel_case


class TestCreateModule:
    """Test suite for invoker module creation."""

    def test_create_module_creates_directory(self, temp_project_dir):
        """Test that create module creates a module directory."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()

        # Create a module
        module_name = "my_module"
        project.create_module(module_name)

        # Check that module directory exists
        module_dir = temp_project_dir / module_name
        assert module_dir.exists(), f"{module_name} directory should be created"
        assert module_dir.is_dir(), f"{module_name} should be a directory"

    def test_create_module_init_file(self, temp_project_dir):
        """Test that the module __init__.py is created as an empty file."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()

        # Create a module
        module_name = "my_test_module"
        project.create_module(module_name)

        init_file = temp_project_dir / module_name / "__init__.py"

        # Check that file exists
        assert init_file.exists(), "__init__.py should exist"
        assert init_file.is_file(), "__init__.py should be a file"

        # Read the file contents
        with open(init_file, "r") as f:
            content = f.read()

        # Check that file contains __invoker_files__ for module tracking
        assert (
            "__invoker_files__" in content
        ), "__init__.py should contain __invoker_files__"
        assert (
            f"base_{module_name}.py" in content
        ), "__init__.py should list the base module file"

    def test_create_module_creates_base_file(self, temp_project_dir):
        """Test that create module creates base_<module_name>.py file."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()

        # Create a module
        module_name = "my_module"
        project.create_module(module_name)

        # Check that base file exists
        base_file = temp_project_dir / module_name / f"base_{module_name}.py"
        assert (
            base_file.exists()
        ), f"base_{module_name}.py should be created in module directory"
        assert base_file.is_file(), f"base_{module_name}.py should be a regular file"

    def test_create_module_base_content(self, temp_project_dir):
        """Test that the base module file has correct content with substitutions."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()

        # Create a module
        module_name = "my_test_module"
        project.create_module(module_name)

        base_file = temp_project_dir / module_name / f"base_{module_name}.py"

        # Read the file contents
        with open(base_file, "r") as f:
            content = f.read()

        # Check that file is not empty
        assert len(content) > 0, f"base_{module_name}.py should not be empty"

        # Check that the module name was properly substituted in camel case
        expected_class_name = f"Base{to_camel_case(module_name)}"
        assert (
            f"class {expected_class_name}(InvokerModule):" in content
        ), f"Should contain class definition with name {expected_class_name}"

        # Check that __MODULE__ placeholder was replaced
        assert (
            "__MODULE__" not in content
        ), "Template placeholder __MODULE__ should be replaced"

        # Check for key module components
        assert (
            "from invoker import InvokerModule" in content
        ), "Base module should import InvokerModule class"
        assert "def args(cls):" in content, "Base module should have args method"
        assert (
            "@classmethod" in content
        ), "Base module should use @classmethod decorator"

    def test_create_module_with_underscores(self, temp_project_dir):
        """Test module creation with underscore names converts to CamelCase properly."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()

        # Create a module with underscores
        module_name = "my_complex_module_name"
        project.create_module(module_name)

        base_file = temp_project_dir / module_name / f"base_{module_name}.py"

        # Read the file contents
        with open(base_file, "r") as f:
            content = f.read()

        # Check that the class name is in CamelCase
        expected_class_name = "BaseMyComplexModuleName"
        assert (
            f"class {expected_class_name}(InvokerModule):" in content
        ), f"Class name should be {expected_class_name}"

    def test_create_module_structure(self, temp_project_dir):
        """Test that module has complete directory structure."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()

        # Create a module
        module_name = "complete_module"
        project.create_module(module_name)

        module_dir = temp_project_dir / module_name
        init_file = module_dir / "__init__.py"
        base_file = module_dir / f"base_{module_name}.py"

        # Verify complete structure
        assert module_dir.is_dir(), "Module directory should exist"
        assert init_file.is_file(), "__init__.py should exist"
        assert base_file.is_file(), f"base_{module_name}.py should exist"

        # Verify files are in the same directory
        assert (
            init_file.parent == module_dir
        ), "__init__.py should be in module directory"
        assert (
            base_file.parent == module_dir
        ), f"base_{module_name}.py should be in module directory"

    def test_create_module_fails_if_exists(self, temp_project_dir):
        """Test that create module fails when module directory already exists."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()

        # Create a module
        module_name = "duplicate_module"
        project.create_module(module_name)

        # Try to create the same module again
        with pytest.raises(SystemExit) as exc_info:
            project.create_module(module_name)

        assert exc_info.value.code == 1

    def test_create_multiple_modules(self, temp_project_dir):
        """Test that multiple modules can be created in the same project."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()

        # Create multiple modules
        module_names = ["module_one", "module_two", "module_three"]
        for module_name in module_names:
            project.create_module(module_name)

        # Verify all modules exist
        for module_name in module_names:
            module_dir = temp_project_dir / module_name
            init_file = module_dir / "__init__.py"
            base_file = module_dir / f"base_{module_name}.py"

            assert module_dir.exists(), f"{module_name} directory should exist"
            assert init_file.exists(), f"{module_name}/__init__.py should exist"
            assert (
                base_file.exists()
            ), f"{module_name}/base_{module_name}.py should exist"

            # Verify each has correct class name
            with open(base_file, "r") as f:
                content = f.read()
            expected_class_name = f"Base{to_camel_case(module_name)}"
            assert (
                f"class {expected_class_name}(InvokerModule):" in content
            ), f"{module_name} should have class {expected_class_name}"

    def test_create_module_and_script_coexist(self, temp_project_dir):
        """Test that modules and scripts can coexist in the same project."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()

        # Create a module
        module_name = "my_module"
        project.create_module(module_name)

        # Create a script
        script_name = "my_script"
        project.create_script(script_name)

        # Verify both exist
        module_dir = temp_project_dir / module_name
        script_file = temp_project_dir / f"{script_name}.py"

        assert module_dir.exists(), "Module directory should exist"
        assert script_file.exists(), "Script file should exist"

        # Verify they don't interfere with each other
        assert module_dir.is_dir(), "Module should be a directory"
        assert script_file.is_file(), "Script should be a file"

    def test_create_module_base_class_inheritance(self, temp_project_dir):
        """Test that the base module class properly inherits from Module."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()

        # Create a module
        module_name = "inheritance_test"
        project.create_module(module_name)

        base_file = temp_project_dir / module_name / f"base_{module_name}.py"

        # Read the file contents
        with open(base_file, "r") as f:
            content = f.read()

        # Verify proper inheritance
        expected_class_name = f"Base{to_camel_case(module_name)}"
        assert (
            f"class {expected_class_name}(InvokerModule):" in content
        ), "Base class should inherit from Module"

        # Verify it calls super().args()
        assert (
            "args = super().args()" in content
        ), "Base class should call super().args()"

        # Verify it updates args dictionary
        assert "args.update(" in content, "Base class should update args dictionary"
