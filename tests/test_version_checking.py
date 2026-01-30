"""Integration tests for invoker version checking."""

from importlib import metadata
from pathlib import Path

import pytest

from project import Project


class TestVersionChecking:
    """Test suite for version checking functionality."""

    def test_load_with_matching_versions(self, temp_project_dir):
        """Test loading a project with matching CLI and project versions."""
        # Initialize project (creates invoker.py with current version)
        project = Project(temp_project_dir)
        project.initialize()

        # Load the project - versions should match, no error
        project.load()

        # Should succeed without error
        assert project.project_version == metadata.version("invoker")

    def test_load_with_mismatched_versions_warns(self, temp_project_dir, capfd):
        """Test that loading a project with version mismatch produces a warning."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()

        # Modify invoker.py to have a different version
        invoker_file = temp_project_dir / "invoker.py"
        with open(invoker_file, "r") as f:
            content = f.read()

        # Change version to 0.1.0
        current_version = metadata.version("invoker")
        modified_content = content.replace(
            f"# Invoker: v{current_version}", "# Invoker: v0.1.0"
        )

        with open(invoker_file, "w") as f:
            f.write(modified_content)

        # Load the project - should produce warning
        project2 = Project(temp_project_dir)
        project2.load()

        # Capture stderr output
        captured = capfd.readouterr()
        assert "Invoker Warning" in captured.err
        assert "Version mismatch" in captured.err
        assert "v0.1.0" in captured.err
        assert f"v{current_version}" in captured.err

    def test_load_with_missing_version_warns(self, temp_project_dir, capfd):
        """Test that loading a project without version header produces a warning."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()

        # Modify invoker.py to remove version header
        invoker_file = temp_project_dir / "invoker.py"
        with open(invoker_file, "r") as f:
            lines = f.readlines()

        # Remove the first line (version header)
        with open(invoker_file, "w") as f:
            f.writelines(lines[1:])

        # Load the project - should produce warning about missing version
        project2 = Project(temp_project_dir)
        project2.load()

        # Capture stderr output
        captured = capfd.readouterr()
        assert "Invoker Warning" in captured.err
        assert "Cannot determine project version" in captured.err

    def test_rebuild_with_matching_versions_succeeds(self, temp_project_dir):
        """Test that rebuild succeeds when versions match."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()

        # Modify invoker.py
        invoker_file = temp_project_dir / "invoker.py"
        with open(invoker_file, "r") as f:
            lines = f.readlines()
        with open(invoker_file, "w") as f:
            f.writelines(lines)
            f.write("\n# User modification\n")

        # Rebuild should succeed
        project.rebuild()

        # Verify backup was created
        backup_file = Path(str(invoker_file) + ".bak")
        assert backup_file.exists(), "Backup should be created on rebuild"

    def test_rebuild_with_mismatched_versions_raises_error(
        self, temp_project_dir, capfd
    ):
        """Test that rebuild raises error when versions don't match."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()

        # Modify invoker.py to have a different version
        invoker_file = temp_project_dir / "invoker.py"
        with open(invoker_file, "r") as f:
            content = f.read()

        # Change version to 0.1.0
        current_version = metadata.version("invoker")
        modified_content = content.replace(
            f"# Invoker: v{current_version}", "# Invoker: v0.1.0"
        )

        with open(invoker_file, "w") as f:
            f.write(modified_content)

        # Attempt to rebuild - should raise SystemExit
        project2 = Project(temp_project_dir)
        with pytest.raises(SystemExit) as exc_info:
            project2.rebuild()

        assert exc_info.value.code == 1

        # Check error output
        captured = capfd.readouterr()
        assert "Invoker Error" in captured.err
        assert "Version mismatch" in captured.err
        assert "v0.1.0" in captured.err
        assert f"v{current_version}" in captured.err

    def test_rebuild_with_missing_version_raises_error(self, temp_project_dir, capfd):
        """Test that rebuild raises error when project version cannot be determined."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()

        # Modify invoker.py to remove version header
        invoker_file = temp_project_dir / "invoker.py"
        with open(invoker_file, "r") as f:
            lines = f.readlines()

        # Remove the first line (version header) and add modification
        with open(invoker_file, "w") as f:
            f.writelines(lines[1:])
            f.write("\n# User modification\n")

        # Rebuild should raise SystemExit (cannot determine version)
        project2 = Project(temp_project_dir)
        with pytest.raises(SystemExit) as exc_info:
            project2.rebuild()

        assert exc_info.value.code == 1

        # Check error output
        captured = capfd.readouterr()
        assert "Invoker Error" in captured.err
        assert "Cannot determine project version" in captured.err

    def test_project_version_is_set(self, temp_project_dir):
        """Test that project_version is set correctly."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()

        # Version should be set
        assert project.project_version is not None
        assert project.project_version == metadata.version("invoker")

    def test_version_mismatch_error_message_concise(self, temp_project_dir, capfd):
        """Test that version mismatch error is clear and concise."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()

        # Modify to old version
        invoker_file = temp_project_dir / "invoker.py"
        with open(invoker_file, "r") as f:
            content = f.read()

        current_version = metadata.version("invoker")
        modified_content = content.replace(
            f"# Invoker: v{current_version}", "# Invoker: v99.99.99"
        )

        with open(invoker_file, "w") as f:
            f.write(modified_content)

        # Try to rebuild
        project2 = Project(temp_project_dir)
        with pytest.raises(SystemExit):
            project2.rebuild()

        # Check error output
        captured = capfd.readouterr()
        error_msg = captured.err
        # Check that error message is concise but clear
        assert "Version mismatch" in error_msg
        assert "v99.99.99" in error_msg
        assert f"v{current_version}" in error_msg
