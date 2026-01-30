"""Integration tests for invoker rebuild command."""

from importlib import metadata
from pathlib import Path
from unittest.mock import patch

import pytest

from project import Project
from resource_manager import ResourceManager


class TestRebuild:
    """Test suite for invoker rebuild functionality."""

    def test_rebuild_unchanged_project(self, temp_project_dir):
        """Test that rebuilding an unchanged project is a no-op."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()

        # Get original file content
        invoker_file = temp_project_dir / "invoker.py"

        with open(invoker_file, "r") as f:
            original_content = f.read()

        # Rebuild project
        project.rebuild()

        # Verify file wasn't changed
        with open(invoker_file, "r") as f:
            new_content = f.read()

        assert (
            new_content == original_content
        ), "Unchanged file should remain the same after rebuild"

        # No backup should be created
        backup_file = Path(str(invoker_file) + ".bak")
        assert (
            not backup_file.exists()
        ), "No backup should be created for unchanged files"

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
        assert backup_file.exists(), "Backup should be created for modified files"

        # Verify backup contains the modification
        with open(backup_file, "r") as f:
            backup_content = f.read()
        assert (
            "This is a user modification" in backup_content
        ), "Backup should contain user modifications"

        # Verify main file was restored from resource
        with open(invoker_file, "r") as f:
            restored_content = f.read()
        assert (
            "This is a user modification" not in restored_content
        ), "Restored file should not contain user modifications"

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

    def test_rebuild_fails_if_invoker_missing(self, temp_project_dir, capfd):
        """Test that rebuild fails if invoker.py doesn't exist."""
        # Initialize but then remove invoker.py
        project = Project(temp_project_dir)
        project.initialize()

        invoker_file = temp_project_dir / "invoker.py"
        invoker_file.unlink()

        # Rebuild should raise error during check_version
        with pytest.raises(SystemExit) as exc_info:
            project.rebuild()

        assert exc_info.value.code == 1

        # Verify it's the version check error
        captured = capfd.readouterr()
        assert "Cannot determine project version" in captured.err

    def test_rebuild_updates_hash_mismatch(self, temp_project_dir):
        """Test that rebuild updates file when resource hash changes."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()

        invoker_file = temp_project_dir / "invoker.py"

        # Replace the entire header with a valid header but fake hash
        header_template = ResourceManager._get_header_template_path().read_text(
            encoding="utf-8"
        )
        header_text = header_template.format(
            version=metadata.version("invoker"),
            resource="invoker.py",
            date="2099-01-01",
            hash="0" * 32,
        )
        body_lines = ResourceManager.strip_invoker_header(invoker_file)
        with open(invoker_file, "w", encoding="utf-8") as f:
            f.write(header_text)
            f.writelines(body_lines)

        # Rebuild should update the file (without backup since hashes don't match)
        project.rebuild()

        # Verify hash was corrected
        stored_hash, computed_hash = ResourceManager.compute_file_hash(invoker_file)
        resource_hash = ResourceManager.compute_resource_hash("invoker.py")

        assert stored_hash == resource_hash, "Hash should be corrected after rebuild"
        assert stored_hash == computed_hash, "Stored and computed hashes should match"

    def test_rebuild_updates_when_resource_template_changes(self, temp_project_dir):
        """Test rebuild updates file when resource template changes (simulating CLI upgrade)."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()

        invoker_file = temp_project_dir / "invoker.py"

        # Verify file has matching hashes (no user modifications)
        stored_hash, computed_hash = ResourceManager.compute_file_hash(invoker_file)
        assert stored_hash == computed_hash, "File should have no user modifications"

        # Mock compute_resource_hash to return a different hash
        # This simulates the resource template being updated (e.g., CLI tool upgrade)
        fake_new_resource_hash = "newresourcehash1234567890abcdef123"

        with patch(
            "resource_manager.ResourceManager.compute_resource_hash",
            return_value=fake_new_resource_hash,
        ):
            # Rebuild should detect hash mismatch and update the file
            project.rebuild()

        # File should be updated with new content from resource
        stored_hash_after, computed_hash_after = ResourceManager.compute_file_hash(
            invoker_file
        )
        resource_hash = ResourceManager.compute_resource_hash("invoker.py")

        # After rebuild, hashes should match the actual resource
        assert (
            stored_hash_after == resource_hash
        ), "File should be updated with current resource hash"
        assert (
            stored_hash_after == computed_hash_after
        ), "Stored and computed hashes should match after rebuild"

        # No backup should be created since stored and computed matched before rebuild
        backup_file = Path(str(invoker_file) + ".bak")
        assert (
            not backup_file.exists()
        ), "No backup should be created when hashes match (no user modifications)"

    def test_rebuild_warns_when_header_found_but_missing_resource(
        self, temp_project_dir, capfd, monkeypatch
    ):
        """Rebuild should warn when header is detected but resource name is missing."""
        project = Project(temp_project_dir)
        project.initialize()

        target = temp_project_dir / "header_missing_resource.py"
        target.write_text("# dummy\nprint('x')\n", encoding="utf-8")

        # Simulate header present (7 lines) but no resource in parsed fields
        monkeypatch.setattr(
            "resource_manager.ResourceManager.parse_invoker_header",
            lambda p: (7, {"version": "0.0.0", "date": "2099-01-01", "hash": "0" * 32}),
        )

        project.rebuild()

        captured = capfd.readouterr()
        assert "Missing resource name in header" in captured.err

    def test_rebuild_modified_util_image_creates_backup(self, temp_project_dir):
        """Rebuild should restore modified util/image.py and create a backup."""
        project = Project(temp_project_dir)
        project.initialize()

        # Import util/image.py into project
        project.import_resource("util/image.py")
        image_util = temp_project_dir / "util" / "image.py"

        # Modify the file to simulate user change
        with open(image_util, "r") as f:
            lines = f.readlines()
        with open(image_util, "w") as f:
            f.writelines(lines)
            f.write("\n# user modification\n")

        # Rebuild should create a backup and restore from resource
        project.rebuild()

        backup_file = Path(str(image_util) + ".bak")
        assert (
            backup_file.exists()
        ), "Backup should be created for modified util/image.py"
        with open(backup_file, "r") as f:
            backup_content = f.read()
        assert (
            "user modification" in backup_content
        ), "Backup should contain user modification"

        with open(image_util, "r") as f:
            restored_content = f.read()
        assert (
            "user modification" not in restored_content
        ), "Restored file should not contain user modification"

    def test_rebuild_nonexistent_resource_in_header_raises(
        self, temp_project_dir, capfd
    ):
        """Rebuild should fail clearly if a generated file references a missing resource."""
        project = Project(temp_project_dir)
        project.initialize()

        ghost = temp_project_dir / "ghost.py"
        body = "print('ghost')\n"
        stored_hash = ResourceManager._compute_hash(body.encode("ascii"))

        with open(ghost, "w") as f:
            header_template = ResourceManager._get_header_template_path().read_text(
                encoding="utf-8"
            )
            header_text = header_template.format(
                version=metadata.version("invoker"),
                resource="util/does_not_exist.py",
                date="2099-01-01",
                hash=stored_hash,
            )
            f.write(header_text + body)

        with pytest.raises(SystemExit) as exc_info:
            project.rebuild()
        assert exc_info.value.code == 1
        captured = capfd.readouterr()
        assert "Resource not found: util/does_not_exist.py" in captured.err

    def test_rebuild_preserves_correct_version(self, temp_project_dir):
        """Test that rebuild preserves files with correct version."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        project.create_module("versioned_module")

        invoker_file = temp_project_dir / "invoker.py"

        # Get original content
        with open(invoker_file, "r") as f:
            original_invoker = f.read()

        # Rebuild
        project.rebuild()

        # Content should be unchanged
        with open(invoker_file, "r") as f:
            new_invoker = f.read()

        assert (
            original_invoker == new_invoker
        ), "File with correct version should not change"

        # Verify version is correct
        current_version = metadata.version("invoker")
        with open(invoker_file, "r") as f:
            first_line = f.readline()
        assert (
            f"v{current_version}" in first_line
        ), "Version should match current invoker version"

    def test_rebuild_malformed_version_invoker_file(self, temp_project_dir, capfd):
        """Test that rebuild raises error when invoker.py has malformed version line."""
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
        assert (
            "# Invoker: 1.2.3" in first_line
        ), "Malformed version (missing v) should be in file"

        # Rebuild should raise error due to malformed version
        with pytest.raises(SystemExit) as exc_info:
            project.rebuild()

        assert exc_info.value.code == 1

        # Check error message
        captured = capfd.readouterr()
        assert "Invoker Error" in captured.err
        assert "Cannot determine project version" in captured.err

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
        assert (
            files_before == files_after
        ), "Rebuild should not create or remove files when no changes needed"

    def test__rebuild_resource_missing_path_raises(self, temp_project_dir):
        """Directly calling _rebuild_resource with a non-existent path should raise."""
        project = Project(temp_project_dir)
        project.initialize()

        missing_path = temp_project_dir / "does_not_exist.py"
        assert not missing_path.exists()

        import pytest

        with pytest.raises(SystemExit) as exc_info:
            project._rebuild_resource("script.py", missing_path, sign=True)
        assert exc_info.value.code == 1
