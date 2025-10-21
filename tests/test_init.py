"""Integration tests for invoker init command."""
import re
from pathlib import Path

from importlib import metadata

from project import Project
from util import compute_resource_hash, compute_file_hash


class TestInit:
    """Test suite for invoker initialization."""
    
    def test_init_creates_invoker_file(self, temp_project_dir):
        """Test that invoker init creates an invoker.py file in the project directory."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Check that invoker.py exists
        invoker_file = temp_project_dir / "invoker.py"
        assert invoker_file.exists(), "invoker.py should be created after initialization"
        assert invoker_file.is_file(), "invoker.py should be a regular file"
    
    def test_init_file_contents(self, temp_project_dir):
        """Test that the created invoker.py file has correct contents."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        invoker_file = temp_project_dir / "invoker.py"
        
        # Read the file contents
        with open(invoker_file, "r") as f:
            content = f.read()
        
        # Check that file is not empty
        assert len(content) > 0, "invoker.py should not be empty"
        
        # Read header lines
        with open(invoker_file, "r") as f:
            lines = f.readlines()
        
        # Check version header
        version_line = lines[0]
        assert version_line.startswith("# Invoker: v"), "First line should contain version header"
        version_match = re.match(r"# Invoker: v(\d+\.\d+\.\d+)", version_line.strip())
        assert version_match, "Version header should have correct format"
        file_version = version_match.group(1)
        current_version = metadata.version('invoker')
        assert file_version == current_version, f"File version {file_version} should match current invoker version {current_version}"
        
        # Check DO NOT EDIT warning
        assert "# DO NOT MANUALLY EDIT THIS FILE." in lines[1], "Second line should contain DO NOT EDIT warning"
        
        # Check hash line exists
        hash_line_found = False
        for line in lines[:10]:  # Check first 10 lines for hash
            if line.startswith("# Hash:"):
                hash_line_found = True
                break
        assert hash_line_found, "File should contain hash signature in header"
        
        # Verify hash integrity
        resource_hash = compute_resource_hash("invoker.resource.py")
        cached_hash, computed_hash = compute_file_hash(invoker_file)
        
        assert cached_hash == resource_hash, "Cached hash should match the resource hash"
        assert computed_hash == resource_hash, "Computed hash should match the resource hash"
        
        # Check that key components are present in the file
        assert "class InvokerScript:" in content, "invoker.py should contain InvokerScript class"
        assert "class InvokerModule:" in content, "invoker.py should contain InvokerModule class"
        assert "def __init__" in content, "invoker.py should contain initialization methods"
        assert "if __name__ == \"__main__\":" in content, "invoker.py should have main entry point"
    
    def test_init_fails_if_already_initialized(self, temp_project_dir):
        """Test that invoker init fails when project is already initialized."""
        import pytest
        
        # Initialize project first time
        project = Project(temp_project_dir)
        project.initialize()
        
        # Try to initialize again
        project2 = Project(temp_project_dir)
        with pytest.raises(SystemExit) as exc_info:
            project2.initialize()
        
        assert exc_info.value.code == 1

