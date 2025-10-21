"""Integration tests for invoker create script command."""
import os
import stat
from pathlib import Path

from project import Project
import pytest
from util import to_camel_case


class TestCreateScript:
    """Test suite for invoker script creation."""
    
    def test_create_script_creates_file(self, temp_project_dir):
        """Test that create script creates a script file with the given name."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a script
        script_name = "my_test_script"
        project.create_script(script_name)
        
        # Check that script file exists
        script_file = temp_project_dir / f"{script_name}.py"
        assert script_file.exists(), f"{script_name}.py should be created"
        assert script_file.is_file(), f"{script_name}.py should be a regular file"
    
    def test_create_script_with_py_extension(self, temp_project_dir):
        """Test that create script works when .py extension is provided."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a script with .py extension
        script_name = "my_script.py"
        project.create_script(script_name)
        
        # Check that script file exists (should strip .py and add it back)
        script_file = temp_project_dir / "my_script.py"
        assert script_file.exists(), "my_script.py should be created"
    
    def test_create_script_content(self, temp_project_dir):
        """Test that the created script has correct content with proper substitutions."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a script
        script_name = "my_test_script"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        # Read the file contents
        with open(script_file, "r") as f:
            content = f.read()
        
        # Check that file is not empty
        assert len(content) > 0, f"{script_name}.py should not be empty"
        
        # Check that the script name was properly substituted in camel case
        expected_class_name = to_camel_case(script_name)
        assert f"class {expected_class_name}(InvokerScript):" in content, \
            f"Should contain class definition with name {expected_class_name}"
        
        # Check that all occurrences of __SCRIPT__ were replaced
        assert "__SCRIPT__" not in content, \
            "Template placeholder __SCRIPT__ should be replaced"
        
        # Check for key script components
        assert "#!/usr/bin/env python" in content, \
            "Script should have shebang line"
        assert "from invoker import InvokerScript" in content, \
            "Script should import InvokerScript class"
        assert "def args(cls):" in content, \
            "Script should have args method"
        assert "def modules(cls):" in content, \
            "Script should have modules method"
        assert "def build_config(cls, args):" in content, \
            "Script should have build_config method"
        assert "def run(self):" in content, \
            "Script should have run method"
        assert 'if __name__ == "__main__":' in content, \
            "Script should have main entry point"
        assert f"{expected_class_name}(run_as_root_script=True).run()" in content, \
            f"Script should instantiate {expected_class_name} class"
    
    def test_create_script_with_underscores(self, temp_project_dir):
        """Test script creation with underscore names converts to CamelCase properly."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a script with underscores
        script_name = "my_complex_script_name"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        # Read the file contents
        with open(script_file, "r") as f:
            content = f.read()
        
        # Check that the class name is in CamelCase
        expected_class_name = "MyComplexScriptName"
        assert f"class {expected_class_name}(InvokerScript):" in content, \
            f"Class name should be {expected_class_name}"
        assert f"{expected_class_name}(run_as_root_script=True).run()" in content, \
            f"Should instantiate {expected_class_name}"
    
    def test_create_script_permissions(self, temp_project_dir):
        """Test that the created script has executable permissions."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a script
        script_name = "my_executable_script"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        # Check file permissions
        file_stat = os.stat(script_file)
        file_mode = stat.filemode(file_stat.st_mode)
        
        # Check that file is executable by owner
        assert file_stat.st_mode & stat.S_IXUSR, \
            "Script should be executable by owner"
        assert file_stat.st_mode & stat.S_IRUSR, \
            "Script should be readable by owner"
        assert file_stat.st_mode & stat.S_IWUSR, \
            "Script should be writable by owner"
        
        # Verify the exact mode is 0o744 (rwxr--r--)
        # Get just the permission bits
        permission_bits = stat.S_IMODE(file_stat.st_mode)
        assert permission_bits == 0o744, \
            f"Script should have permissions 0o744, but has {oct(permission_bits)}"
    
    def test_create_script_fails_if_exists(self, temp_project_dir):
        """Test that create script fails when script already exists."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a script
        script_name = "duplicate_script"
        project.create_script(script_name)
        
        # Try to create the same script again
        with pytest.raises(SystemExit) as exc_info:
            project.create_script(script_name)
        
        assert exc_info.value.code == 1
    
    def test_create_multiple_scripts(self, temp_project_dir):
        """Test that multiple scripts can be created in the same project."""
        # Initialize project first
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create multiple scripts
        script_names = ["script_one", "script_two", "script_three"]
        for script_name in script_names:
            project.create_script(script_name)
        
        # Verify all scripts exist
        for script_name in script_names:
            script_file = temp_project_dir / f"{script_name}.py"
            assert script_file.exists(), f"{script_name}.py should exist"
            
            # Verify each has correct class name
            with open(script_file, "r") as f:
                content = f.read()
            expected_class_name = to_camel_case(script_name)
            assert f"class {expected_class_name}(InvokerScript):" in content, \
                f"{script_name}.py should have class {expected_class_name}"

