from pathlib import Path
import pytest

from click.testing import CliRunner

from invoker import cli
from project import Project
from resource_manager import ResourceManager


class TestImportResources:
    def test_import_project_default_dest(self, temp_project_dir):
        project = Project(temp_project_dir)
        project.initialize()

        project.import_resource("util/image.py")

        dest = temp_project_dir / "util" / "image.py"
        assert dest.exists(), "Destination file should be created at default path"

        stored_hash, computed_hash = ResourceManager.compute_file_hash(dest)
        resource_hash = ResourceManager.compute_resource_hash("util/image.py")

        assert stored_hash == resource_hash, "Stored hash should match resource hash"
        assert computed_hash == resource_hash, "Computed hash should match resource hash"

    def test_import_project_custom_dest(self, temp_project_dir):
        project = Project(temp_project_dir)
        project.initialize()

        custom_dest = "utils/img.py"
        project.import_resource("util/image.py", dest_rel_path=custom_dest)

        dest = temp_project_dir / custom_dest
        assert dest.exists(), "Destination file should be created at custom path"

        stored_hash, computed_hash = ResourceManager.compute_file_hash(dest)
        resource_hash = ResourceManager.compute_resource_hash("util/image.py")

        assert stored_hash == resource_hash, "Stored hash should match resource hash"
        assert computed_hash == resource_hash, "Computed hash should match resource hash"

    def test_import_project_nonexistent_resource(self, temp_project_dir):
        project = Project(temp_project_dir)
        project.initialize()

        with pytest.raises(FileNotFoundError):
            project.import_resource("does/not/exist.py")

    def test_cli_import_with_dest(self, temp_project_dir, monkeypatch):
        project = Project(temp_project_dir)
        project.initialize()

        runner = CliRunner()
        monkeypatch.chdir(temp_project_dir)

        result = runner.invoke(cli, ["import", "util/image.py", "--dest", "assets/img.py"])
        assert result.exit_code == 0, f"CLI should succeed. Output: {result.output}"

        dest = temp_project_dir / "assets" / "img.py"
        assert dest.exists(), "Destination file should be created by CLI"

        stored_hash, computed_hash = ResourceManager.compute_file_hash(dest)
        resource_hash = ResourceManager.compute_resource_hash("util/image.py")

        assert stored_hash == resource_hash, "Stored hash should match resource hash"
        assert computed_hash == resource_hash, "Computed hash should match resource hash"

    def test_cli_import_nonexistent_resource(self, temp_project_dir, monkeypatch):
        project = Project(temp_project_dir)
        project.initialize()

        runner = CliRunner()
        monkeypatch.chdir(temp_project_dir)

        result = runner.invoke(cli, ["import", "no/such/resource.py"])
        assert result.exit_code != 0, "CLI should fail for nonexistent resource"

    def test_import_project_outside_resources_forbidden(self, temp_project_dir):
        project = Project(temp_project_dir)
        project.initialize()

        with pytest.raises(SystemExit):
            project.import_resource("../invoker.py")

    def test_cli_import_outside_resources_forbidden(self, temp_project_dir, monkeypatch):
        project = Project(temp_project_dir)
        project.initialize()

        runner = CliRunner()
        monkeypatch.chdir(temp_project_dir)

        result = runner.invoke(cli, ["import", "../invoker.py"])
        assert result.exit_code != 0, "CLI should fail for resource path outside resources"

    def test_import_project_disallows_resources_tests(self, temp_project_dir):
        project = Project(temp_project_dir)
        project.initialize()
        with pytest.raises(SystemExit):
            project.import_resource("tests/test_image_convert_dtype.py")

    def test_cli_import_disallows_resources_tests(self, temp_project_dir, monkeypatch):
        project = Project(temp_project_dir)
        project.initialize()
        runner = CliRunner()
        monkeypatch.chdir(temp_project_dir)
        result = runner.invoke(cli, ["import", "tests/test_image_convert_dtype.py"])
        assert result.exit_code != 0, "CLI should fail for resource path under resources/tests"

    def test_import_project_overwrite_backs_up_existing_file(self, temp_project_dir, capsys):
        project = Project(temp_project_dir)
        project.initialize()

        # Prepare existing destination file
        dest_rel = "util/overwrite_target.py"
        dest = temp_project_dir / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# old content\nVALUE = 0\n", encoding="utf-8")
        backup = Path(str(dest) + ".bak")
        if backup.exists():
            backup.unlink()

        # Import resource to same destination to trigger overwrite
        project.import_resource("util/image.py", dest_rel_path=dest_rel)

        captured = capsys.readouterr()
        assert "Overwriting existing file" in captured.err

        assert backup.exists(), "Existing file should be renamed to .bak"
        assert dest.exists(), "Newly imported file should exist at destination"

        # Imported file should be signed and match resource hash
        stored_hash, computed_hash = ResourceManager.compute_file_hash(dest)
        resource_hash = ResourceManager.compute_resource_hash("util/image.py")
        assert stored_hash == resource_hash
        assert computed_hash == resource_hash

        # Backup should contain the original content
        assert backup.read_text(encoding="utf-8").startswith("# old content")

    def test_import_project_overwrite_raises_if_backup_exists(self, temp_project_dir):
        project = Project(temp_project_dir)
        project.initialize()

        dest_rel = "util/overwrite_target_2.py"
        dest = temp_project_dir / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# old content\nVALUE = 0\n", encoding="utf-8")

        backup = Path(str(dest) + ".bak")
        backup.write_text("# existing backup\n", encoding="utf-8")

        with pytest.raises(SystemExit):
            project.import_resource("util/image.py", dest_rel_path=dest_rel)

        # Original file should remain (no rename should have happened)
        assert dest.exists()
        assert dest.read_text(encoding="utf-8").startswith("# old content")

