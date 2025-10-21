"""Integration tests for invoker rebuild command."""
import re
from pathlib import Path
from importlib import metadata
from unittest.mock import patch

from project import Project, InvokerError
from util import compute_resource_hash, compute_file_hash, copy_resource


class TestRebuild:
    """Test suite for invoker rebuild functionality."""
    
    def test_rebuild_unchanged_project(self, temp_project_dir):
        """Test that rebuilding an unchanged project is a no-op."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Get original file stats
        invoker_file = temp_project_dir / "invoker.py"
        original_mtime = invoker_file.stat().st_mtime
        
        with open(invoker_file, "r") as f:
            original_content = f.read()
        
        # Rebuild project
        project.rebuild()
        
        # Verify file wasn't changed
        with open(invoker_file, "r") as f:
            new_content = f.read()
        
        assert new_content == original_content, \
            "Unchanged file should remain the same after rebuild"
        
        # No backup should be created
        backup_file = Path(str(invoker_file) + ".bak")
        assert not backup_file.exists(), \
            "No backup should be created for unchanged files"
    
    def test_rebuild_modified_invoker_creates_backup(self, temp_project_dir):
        """Test that rebuilding modified invoker.py creates a backup."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        invoker_file = temp_project_dir / "invoker.py"
        
        # Read original content and header
        with open(invoker_file, "r") as f:
            lines = f.readlines()
        
        # Modify the file (add a comment at the end)
        with open(invoker_file, "w") as f:
            f.writelines(lines)
            f.write("\n# This is a user modification\n")
        
        # Rebuild project
        project.rebuild()
        
        # Verify backup was created
        backup_file = Path(str(invoker_file) + ".bak")
        assert backup_file.exists(), \
            "Backup should be created for modified files"
        
        # Verify backup contains the modification
        with open(backup_file, "r") as f:
            backup_content = f.read()
        assert "This is a user modification" in backup_content, \
            "Backup should contain user modifications"
        
        # Verify main file was restored from resource
        with open(invoker_file, "r") as f:
            restored_content = f.read()
        assert "This is a user modification" not in restored_content, \
            "Restored file should not contain user modifications"
    
    def test_rebuild_modified_module_creates_backup(self, temp_project_dir):
        """Test that rebuilding modified module __init__.py creates a backup."""
        # Initialize project and create module
        project = Project(temp_project_dir)
        project.initialize()
        project.create_module("test_module")
        
        init_file = temp_project_dir / "test_module" / "__init__.py"
        
        # Read and modify the file
        with open(init_file, "r") as f:
            lines = f.readlines()
        
        with open(init_file, "w") as f:
            f.writelines(lines)
            f.write("\n# User added code\n")
        
        # Rebuild project
        project.rebuild()
        
        # Verify backup was created
        backup_file = Path(str(init_file) + ".bak")
        assert backup_file.exists(), \
            "Backup should be created for modified module __init__.py"
        
        # Verify backup contains modification
        with open(backup_file, "r") as f:
            backup_content = f.read()
        assert "User added code" in backup_content, \
            "Backup should contain user modifications"
        
        # Verify restored file doesn't contain modification
        with open(init_file, "r") as f:
            restored_content = f.read()
        assert "User added code" not in restored_content, \
            "Restored file should not contain user modifications"
    
    def test_rebuild_multiple_modules(self, temp_project_dir):
        """Test rebuilding project with multiple modules."""
        # Initialize project and create multiple modules
        project = Project(temp_project_dir)
        project.initialize()
        project.create_module("module_one")
        project.create_module("module_two")
        project.create_module("module_three")
        
        # Modify one of the modules
        init_file = temp_project_dir / "module_two" / "__init__.py"
        with open(init_file, "r") as f:
            lines = f.readlines()
        with open(init_file, "w") as f:
            f.writelines(lines)
            f.write("\n# Modified\n")
        
        # Rebuild project
        project.rebuild()
        
        # Verify only modified module has backup
        backup_one = temp_project_dir / "module_one" / "__init__.py.bak"
        backup_two = temp_project_dir / "module_two" / "__init__.py.bak"
        backup_three = temp_project_dir / "module_three" / "__init__.py.bak"
        
        assert not backup_one.exists(), \
            "Unmodified module should not have backup"
        assert backup_two.exists(), \
            "Modified module should have backup"
        assert not backup_three.exists(), \
            "Unmodified module should not have backup"
    
    def test_rebuild_ignores_user_modules(self, temp_project_dir):
        """Test that rebuild ignores modules without invoker header."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a user-defined module (not created with invoker)
        user_module_dir = temp_project_dir / "user_module"
        user_module_dir.mkdir()
        
        user_init = user_module_dir / "__init__.py"
        user_init_content = """# This is a user-created module
# Not managed by invoker

def my_function():
    pass
"""
        with open(user_init, "w") as f:
            f.write(user_init_content)
        
        # Rebuild project
        project.rebuild()
        
        # Verify user module was not modified
        with open(user_init, "r") as f:
            content = f.read()
        
        assert "user-created module" in content, \
            "User module should not be modified"
        assert "my_function" in content, \
            "User module content should be preserved"
        
        # No backup should be created
        backup_file = Path(str(user_init) + ".bak")
        assert not backup_file.exists(), \
            "User modules should not be backed up"
    
    def test_rebuild_ignores_directories_without_init(self, temp_project_dir):
        """Test that rebuild ignores directories without __init__.py."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a directory without __init__.py
        other_dir = temp_project_dir / "not_a_module"
        other_dir.mkdir()
        
        some_file = other_dir / "some_file.py"
        with open(some_file, "w") as f:
            f.write("# Some content\n")
        
        # Rebuild should not raise errors
        project.rebuild()
        
        # Verify the directory and file still exist unchanged
        assert other_dir.exists()
        assert some_file.exists()
        with open(some_file, "r") as f:
            content = f.read()
        assert "Some content" in content
    
    def test_rebuild_skips_init_that_is_not_a_file(self, temp_project_dir):
        """Test that rebuild skips __init__.py if it's not a regular file."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a proper module first
        project.create_module("normal_module")
        
        # Create a directory structure where __init__.py is a directory (not a file)
        weird_module = temp_project_dir / "weird_module"
        weird_module.mkdir()
        
        # Create __init__.py as a directory instead of a file
        init_as_dir = weird_module / "__init__.py"
        init_as_dir.mkdir()
        
        # Add a file inside this directory to make it more realistic
        some_content = init_as_dir / "content.txt"
        with open(some_content, "w") as f:
            f.write("This is weird\n")
        
        # Verify __init__.py exists but is a directory
        assert init_as_dir.exists()
        assert init_as_dir.is_dir()
        assert not init_as_dir.is_file()
        
        # Rebuild should not crash and should skip this non-file __init__.py
        project.rebuild()
        
        # Verify the directory structure remains unchanged
        assert init_as_dir.exists()
        assert init_as_dir.is_dir()
        assert some_content.exists()
        with open(some_content, "r") as f:
            content = f.read()
        assert "This is weird" in content
        
        # Verify no backup was created for the directory
        backup_dir = Path(str(init_as_dir) + ".bak")
        assert not backup_dir.exists(), \
            "No backup should be created for directory named __init__.py"
        
        # Verify normal module was still rebuilt properly
        normal_init = temp_project_dir / "normal_module" / "__init__.py"
        assert normal_init.exists()
        assert normal_init.is_file()
    
    def test_rebuild_ignores_regular_files(self, temp_project_dir):
        """Test that rebuild ignores regular files in project root."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create some regular files
        script_file = temp_project_dir / "my_script.py"
        with open(script_file, "w") as f:
            f.write("# Script content\n")
        
        data_file = temp_project_dir / "data.txt"
        with open(data_file, "w") as f:
            f.write("Some data\n")
        
        # Rebuild should not raise errors
        project.rebuild()
        
        # Files should remain unchanged
        with open(script_file, "r") as f:
            assert "Script content" in f.read()
        with open(data_file, "r") as f:
            assert "Some data" in f.read()
    
    def test_rebuild_fails_if_invoker_missing(self, temp_project_dir):
        """Test that rebuild fails if invoker.py doesn't exist."""
        # Initialize but then remove invoker.py
        project = Project(temp_project_dir)
        project.initialize()
        
        invoker_file = temp_project_dir / "invoker.py"
        invoker_file.unlink()
        
        # Rebuild should raise error
        try:
            project.rebuild()
            assert False, "Should raise InvokerError when invoker.py is missing"
        except InvokerError as e:
            assert "does not exist" in str(e), \
                "Error should mention file doesn't exist"
    
    def test_rebuild_updates_hash_mismatch(self, temp_project_dir):
        """Test that rebuild updates file when resource hash changes."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        invoker_file = temp_project_dir / "invoker.py"
        
        # Read the file and manually change the stored hash
        with open(invoker_file, "r") as f:
            lines = f.readlines()
        
        # Find and modify the hash line (should be near the top)
        modified_lines = []
        for line in lines:
            if line.startswith("# Hash:"):
                # Replace with a fake hash
                modified_lines.append("# Hash:\tfakehash1234567890abcdef1234567\n")
            else:
                modified_lines.append(line)
        
        with open(invoker_file, "w") as f:
            f.writelines(modified_lines)
        
        # Rebuild should update the file (without backup since hashes don't match)
        project.rebuild()
        
        # Verify hash was corrected
        stored_hash, computed_hash = compute_file_hash(invoker_file)
        resource_hash = compute_resource_hash("invoker.resource.py")
        
        assert stored_hash == resource_hash, \
            "Hash should be corrected after rebuild"
        assert stored_hash == computed_hash, \
            "Stored and computed hashes should match"
    
    def test_rebuild_resource_updated_no_user_changes(self, temp_project_dir):
        """Test rebuild when resource is updated but user hasn't modified file."""
        # This tests the case where:
        # - cached_hash == computed_hash (user hasn't modified the file)
        # - resource_hash != cached_hash (invoker library was updated)
        
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        project.create_module("test_module")
        
        init_file = temp_project_dir / "test_module" / "__init__.py"
        
        # Store original content to verify it changes
        with open(init_file, "r") as f:
            original_content = f.read()
        
        # Verify file is in good state before mocking
        stored_hash, computed_hash = compute_file_hash(init_file)
        assert stored_hash == computed_hash, \
            "File should be unmodified initially"
        
        # Mock compute_resource_hash to return a different hash
        # This simulates the resource being updated in a new invoker version
        fake_resource_hash = "different_hash_1234567890abcdef"
        
        with patch('project.compute_resource_hash') as mock_resource_hash:
            # Make it return different hash for module_init, same for invoker
            def side_effect(resource_name):
                if resource_name == "module_init.resource.py":
                    return fake_resource_hash
                else:
                    # Return real hash for invoker.py
                    return compute_resource_hash(resource_name)
            
            mock_resource_hash.side_effect = side_effect
            
            # Rebuild should update the file (without backup)
            project.rebuild()
        
        # Verify file was updated
        with open(init_file, "r") as f:
            new_content = f.read()
        
        # Content should be refreshed from resource
        # The hash in the file should now match the "current" resource
        stored_hash_after, computed_hash_after = compute_file_hash(init_file)
        
        # The stored hash should have been updated
        assert stored_hash_after == computed_hash_after, \
            "File should be consistent after rebuild"
        
        # No backup should be created (file wasn't user-modified)
        backup_file = Path(str(init_file) + ".bak")
        assert not backup_file.exists(), \
            "No backup should be created when only resource changed"
        
        # Verify the file was actually rewritten (it should have fresh content from resource)
        # The hashes should match the real resource now
        real_resource_hash = compute_resource_hash("module_init.resource.py")
        assert stored_hash_after == real_resource_hash, \
            "File should now match the actual resource"
    
    def test_rebuild_preserves_correct_version(self, temp_project_dir):
        """Test that rebuild preserves files with correct version."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        project.create_module("versioned_module")
        
        invoker_file = temp_project_dir / "invoker.py"
        init_file = temp_project_dir / "versioned_module" / "__init__.py"
        
        # Get original content
        with open(invoker_file, "r") as f:
            original_invoker = f.read()
        with open(init_file, "r") as f:
            original_init = f.read()
        
        # Rebuild
        project.rebuild()
        
        # Content should be unchanged
        with open(invoker_file, "r") as f:
            new_invoker = f.read()
        with open(init_file, "r") as f:
            new_init = f.read()
        
        assert original_invoker == new_invoker, \
            "File with correct version should not change"
        assert original_init == new_init, \
            "Module with correct version should not change"
        
        # Verify version is correct
        current_version = metadata.version('invoker')
        with open(invoker_file, "r") as f:
            first_line = f.readline()
        assert f"v{current_version}" in first_line, \
            "Version should match current invoker version"
    
    def test_rebuild_malformed_version_line(self, temp_project_dir):
        """Test that rebuild skips files with malformed version lines."""
        # Initialize project and create module
        project = Project(temp_project_dir)
        project.initialize()
        project.create_module("malformed_module")
        
        init_file = temp_project_dir / "malformed_module" / "__init__.py"
        
        # Read the file and malform the version line
        with open(init_file, "r") as f:
            original_content = f.read()
            lines = original_content.splitlines(keepends=True)
        
        # Replace version line with malformed version
        modified_lines = []
        for line in lines:
            if line.startswith("# Invoker: v"):
                # Create malformed version (doesn't match semver pattern)
                modified_lines.append("# Invoker: vMALFORMED\n")
            else:
                modified_lines.append(line)
        
        modified_content = "".join(modified_lines)
        with open(init_file, "w") as f:
            f.write(modified_content)
        
        # Verify the malformed version is in place
        with open(init_file, "r") as f:
            first_line = f.readline()
        assert "vMALFORMED" in first_line, \
            "Malformed version should be in file before rebuild"
        
        # Rebuild should skip this file (not replace it)
        project.rebuild()
        
        # Verify version was NOT changed (file should be skipped)
        with open(init_file, "r") as f:
            content_after_rebuild = f.read()
        
        assert content_after_rebuild == modified_content, \
            "File with malformed version should be skipped (not modified)"
        
        with open(init_file, "r") as f:
            first_line = f.readline()
        assert "vMALFORMED" in first_line, \
            "Malformed version should remain unchanged"
        
        # Verify no backup was created
        backup_file = Path(str(init_file) + ".bak")
        assert not backup_file.exists(), \
            "No backup should be created for skipped files"
    
    def test_rebuild_malformed_version_invoker_file(self, temp_project_dir):
        """Test that rebuild skips invoker.py with malformed version line."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        invoker_file = temp_project_dir / "invoker.py"
        
        # Read the file and malform the version line
        with open(invoker_file, "r") as f:
            original_content = f.read()
            lines = original_content.splitlines(keepends=True)
        
        # Replace version line with malformed format (missing 'v' prefix)
        modified_lines = []
        for line in lines:
            if line.startswith("# Invoker: v"):
                modified_lines.append("# Invoker: 1.2.3\n")  # Missing 'v' prefix
            else:
                modified_lines.append(line)
        
        modified_content = "".join(modified_lines)
        with open(invoker_file, "w") as f:
            f.write(modified_content)
        
        # Verify malformed version
        with open(invoker_file, "r") as f:
            first_line = f.readline()
        assert "# Invoker: 1.2.3" in first_line, \
            "Malformed version (missing v) should be in file"
        
        # Rebuild should skip this file (not replace it)
        project.rebuild()
        
        # Verify version was NOT changed (file should be skipped)
        with open(invoker_file, "r") as f:
            content_after_rebuild = f.read()
        
        assert content_after_rebuild == modified_content, \
            "File with malformed version should be skipped (not modified)"
        
        with open(invoker_file, "r") as f:
            first_line = f.readline()
        assert "# Invoker: 1.2.3" in first_line, \
            "Malformed version should remain unchanged"
        
        # Verify no backup was created
        backup_file = Path(str(invoker_file) + ".bak")
        assert not backup_file.exists(), \
            "No backup should be created for skipped files"
    
    def test_rebuild_completely_invalid_version_line(self, temp_project_dir):
        """Test rebuild skips files with completely invalid version line format."""
        # Initialize project and create module
        project = Project(temp_project_dir)
        project.initialize()
        project.create_module("invalid_module")
        
        init_file = temp_project_dir / "invalid_module" / "__init__.py"
        
        # Read original content and replace first line with invalid format
        with open(init_file, "r") as f:
            lines = f.readlines()
        
        # Replace version line with completely invalid format
        lines[0] = "# This is not a valid version line\n"
        modified_content = "".join(lines)
        
        with open(init_file, "w") as f:
            f.write(modified_content)
        
        # Verify invalid version line
        with open(init_file, "r") as f:
            first_line = f.readline()
        assert "# This is not a valid version line" in first_line, \
            "Invalid version line should be in file"
        
        # Rebuild should skip this file (not replace it)
        project.rebuild()
        
        # Verify file was NOT changed (should be skipped)
        with open(init_file, "r") as f:
            content_after_rebuild = f.read()
        
        assert content_after_rebuild == modified_content, \
            "File with invalid version line should be skipped (not modified)"
        
        with open(init_file, "r") as f:
            first_line = f.readline()
        assert "# This is not a valid version line" in first_line, \
            "Invalid version line should remain unchanged"
        
        # Verify no backup was created
        backup_file = Path(str(init_file) + ".bak")
        assert not backup_file.exists(), \
            "No backup should be created for skipped files"
    
    def test_rebuild_complete_project_structure(self, temp_project_dir):
        """Test rebuilding a complete project with scripts and modules."""
        # Create a complete project
        project = Project(temp_project_dir)
        project.initialize()
        project.create_module("data_loader")
        project.create_module("processor")
        project.create_script("train_model")
        project.create_script("evaluate")
        
        # Modify invoker.py
        invoker_file = temp_project_dir / "invoker.py"
        with open(invoker_file, "r") as f:
            lines = f.readlines()
        with open(invoker_file, "w") as f:
            f.writelines(lines)
            f.write("\n# Modified invoker\n")
        
        # Modify one module
        init_file = temp_project_dir / "processor" / "__init__.py"
        with open(init_file, "r") as f:
            lines = f.readlines()
        with open(init_file, "w") as f:
            f.writelines(lines)
            f.write("\n# Modified module\n")
        
        # Rebuild
        project.rebuild()
        
        # Verify backups for modified files
        assert (temp_project_dir / "invoker.py.bak").exists(), \
            "Backup should exist for modified invoker.py"
        assert (temp_project_dir / "processor" / "__init__.py.bak").exists(), \
            "Backup should exist for modified module"
        
        # Verify unmodified module has no backup
        assert not (temp_project_dir / "data_loader" / "__init__.py.bak").exists(), \
            "Unmodified module should not have backup"
        
        # Verify scripts are unchanged (rebuild doesn't affect scripts)
        train_script = temp_project_dir / "train_model.py"
        eval_script = temp_project_dir / "evaluate.py"
        assert train_script.exists(), "Scripts should remain"
        assert eval_script.exists(), "Scripts should remain"
    
    def test_rebuild_skips_old_version_modules(self, temp_project_dir):
        """Test that rebuild skips modules with different version headers."""
        # Initialize project and create module
        project = Project(temp_project_dir)
        project.initialize()
        project.create_module("old_version_module")
        
        init_file = temp_project_dir / "old_version_module" / "__init__.py"
        
        # Read the file and change the version to an old version
        with open(init_file, "r") as f:
            content = f.read()
        
        # Replace version line with old version
        current_version = metadata.version('invoker')
        old_content = content.replace(
            f"# Invoker: v{current_version}",
            "# Invoker: v0.1.0"
        )
        
        with open(init_file, "w") as f:
            f.write(old_content)
        
        # Rebuild should skip this file (different version)
        project.rebuild()
        
        # Verify version was NOT updated (file should remain unchanged)
        with open(init_file, "r") as f:
            first_line = f.readline()
        
        assert "v0.1.0" in first_line, \
            "Old version should be preserved (not automatically updated)"
        assert f"v{current_version}" not in first_line, \
            "Should not be updated to current version"
        
        # Verify no backup was created
        backup_file = Path(str(init_file) + ".bak")
        assert not backup_file.exists(), \
            "No backup should be created for skipped files"
    
    def test_rebuild_creates_no_extra_files(self, temp_project_dir):
        """Test that rebuild doesn't create any unexpected files."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        project.create_module("test_module")
        
        # Get list of files before rebuild
        files_before = set(temp_project_dir.rglob("*"))
        
        # Rebuild (no modifications, should be no-op)
        project.rebuild()
        
        # Get list of files after rebuild
        files_after = set(temp_project_dir.rglob("*"))
        
        # Should be the same
        assert files_before == files_after, \
            "Rebuild should not create or remove files when no changes needed"

