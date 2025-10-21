"""Integration tests for invoker create module command."""
import re
from pathlib import Path

from importlib import metadata

from project import Project, InvokerError
from util import compute_resource_hash, compute_file_hash, to_camel_case


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
    
    def test_create_module_creates_init_file(self, temp_project_dir):
        """Test that create module creates __init__.py in the module directory."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a module
        module_name = "test_module"
        project.create_module(module_name)
        
        # Check that __init__.py exists
        init_file = temp_project_dir / module_name / "__init__.py"
        assert init_file.exists(), "__init__.py should be created in module directory"
        assert init_file.is_file(), "__init__.py should be a regular file"
    
    def test_create_module_init_content(self, temp_project_dir):
        """Test that the module __init__.py has correct content and signature."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a module
        module_name = "my_test_module"
        project.create_module(module_name)
        
        init_file = temp_project_dir / module_name / "__init__.py"
        
        # Read the file contents
        with open(init_file, "r") as f:
            content = f.read()
            lines = content.split('\n')
        
        # Check that file is not empty
        assert len(content) > 0, "__init__.py should not be empty"
        
        # Check version header
        version_line = lines[0]
        assert version_line.startswith("# Invoker: v"), \
            "First line should contain version header"
        version_match = re.match(r"# Invoker: v(\d+\.\d+\.\d+)", version_line.strip())
        assert version_match, "Version header should have correct format"
        file_version = version_match.group(1)
        current_version = metadata.version('invoker')
        assert file_version == current_version, \
            f"File version {file_version} should match current invoker version {current_version}"
        
        # Check DO NOT EDIT warning
        assert "# DO NOT MANUALLY EDIT THIS FILE." in content, \
            "__init__.py should contain DO NOT EDIT warning"
        
        # Check hash line exists
        hash_line_found = False
        for line in lines[:10]:
            if line.startswith("# Hash:"):
                hash_line_found = True
                break
        assert hash_line_found, "__init__.py should contain hash signature in header"
        
        # Verify hash integrity
        resource_hash = compute_resource_hash("module_init.resource.py")
        cached_hash, computed_hash = compute_file_hash(init_file)
        
        assert cached_hash == resource_hash, \
            "Cached hash should match the resource hash"
        assert computed_hash == resource_hash, \
            "Computed hash should match the resource hash"
        
        # Check for key components
        assert "import importlib" in content, \
            "__init__.py should import importlib"
        assert "def get_class(mode):" in content, \
            "__init__.py should define get_class function"
        assert "_MODULE_NAME" in content, \
            "__init__.py should define _MODULE_NAME"
        assert "_CLASSES" in content, \
            "__init__.py should define _CLASSES"
    
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
        assert base_file.exists(), \
            f"base_{module_name}.py should be created in module directory"
        assert base_file.is_file(), \
            f"base_{module_name}.py should be a regular file"
    
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
        assert f"class {expected_class_name}(Module):" in content, \
            f"Should contain class definition with name {expected_class_name}"
        
        # Check that __MODULE__ placeholder was replaced
        assert "__MODULE__" not in content, \
            "Template placeholder __MODULE__ should be replaced"
        
        # Check for key module components
        assert "from invoker import Module" in content, \
            "Base module should import Module class"
        assert "def args(cls):" in content, \
            "Base module should have args method"
        assert "@classmethod" in content, \
            "Base module should use @classmethod decorator"
    
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
        assert f"class {expected_class_name}(Module):" in content, \
            f"Class name should be {expected_class_name}"
    
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
        assert init_file.parent == module_dir, \
            "__init__.py should be in module directory"
        assert base_file.parent == module_dir, \
            f"base_{module_name}.py should be in module directory"
    
    def test_create_module_fails_if_exists(self, temp_project_dir):
        """Test that create module fails when module directory already exists."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a module
        module_name = "duplicate_module"
        project.create_module(module_name)
        
        # Try to create the same module again
        try:
            project.create_module(module_name)
            assert False, "Should raise InvokerError when module already exists"
        except InvokerError as e:
            assert "already exists" in str(e), \
                "Error message should mention module already exists"
    
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
            assert base_file.exists(), \
                f"{module_name}/base_{module_name}.py should exist"
            
            # Verify each has correct class name
            with open(base_file, "r") as f:
                content = f.read()
            expected_class_name = f"Base{to_camel_case(module_name)}"
            assert f"class {expected_class_name}(Module):" in content, \
                f"{module_name} should have class {expected_class_name}"
    
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
        assert f"class {expected_class_name}(Module):" in content, \
            "Base class should inherit from Module"
        
        # Verify it calls super().args()
        assert "args = super().args()" in content, \
            "Base class should call super().args()"
        
        # Verify it updates args dictionary
        assert "args.update(dict(" in content, \
            "Base class should update args dictionary"

