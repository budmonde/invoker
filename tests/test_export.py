from datetime import date
from importlib import metadata
from pathlib import Path

import pytest
from click.testing import CliRunner

from invoker import cli
from project import Project
from resource_manager import ResourceManager


@pytest.fixture()
def export_setup(temp_project_dir, monkeypatch):
    project = Project(temp_project_dir)
    project.initialize()
    sandbox = temp_project_dir / ".resources_sandbox"

    # Create a fake plugin namespace for testing
    def mock_discover():
        return {
            "invoker": Path(__file__).resolve().parent.parent / "resources",
            "test": sandbox,
        }

    monkeypatch.setattr(
        ResourceManager,
        "_discover_resource_sources",
        classmethod(lambda cls: mock_discover()),
    )
    monkeypatch.setattr(ResourceManager, "_resource_sources", None)

    # Mock editable check to return True for test namespace
    original_is_editable = ResourceManager.is_namespace_editable

    def mock_is_editable(ns):
        if ns == "test":
            return True
        return original_is_editable(ns)

    monkeypatch.setattr(
        ResourceManager,
        "is_namespace_editable",
        classmethod(lambda cls, ns: mock_is_editable(ns)),
    )

    # Ensure sandbox resources path exists
    sandbox.mkdir(parents=True, exist_ok=True)
    runner = CliRunner()
    return {
        "project": project,
        "sandbox": sandbox,
        "runner": runner,
        "root": temp_project_dir,
        "monkeypatch": monkeypatch,
    }


class TestExport:
    def test_project_export_new_resource(self, export_setup):
        project = export_setup["project"]
        sandbox = export_setup["sandbox"]
        root = export_setup["root"]

        src_rel_path = "util/custom_export.py"
        src_file = root / src_rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)
        content = "# custom export file\nVALUE = 1\n"
        src_file.write_text(content, encoding="utf-8")

        project.export_resource(src_rel_path, "test:util/custom_export.py")

        dest = sandbox / "util/custom_export.py"
        assert (
            dest.exists()
        ), "Export should create the new resource in package resources"
        assert (
            dest.read_text(encoding="utf-8") == content
        ), "Exported content should match source"

    def test_project_export_overwrite_resource(self, export_setup):
        project = export_setup["project"]
        sandbox = export_setup["sandbox"]
        root = export_setup["root"]

        dest_rel = "util/export_overwrite.py"

        first_src_rel = "util/src_overwrite.py"
        first_src = root / first_src_rel
        first_src.parent.mkdir(parents=True, exist_ok=True)
        first_content = "# first version\nVALUE = 1\n"
        first_src.write_text(first_content, encoding="utf-8")
        project.export_resource(first_src_rel, f"test:{dest_rel}")

        dest = sandbox / dest_rel
        assert dest.exists(), "Destination resource should be created on first export"
        assert dest.read_text(encoding="utf-8") == first_content

        second_content = "# second version\nVALUE = 2\n"
        first_src.write_text(second_content, encoding="utf-8")
        project.export_resource(first_src_rel, f"test:{dest_rel}")

        assert (
            dest.read_text(encoding="utf-8") == second_content
        ), "Destination resource should be overwritten"

    def test_cli_export_new_resource(self, export_setup):
        sandbox = export_setup["sandbox"]
        root = export_setup["root"]
        monkeypatch = export_setup["monkeypatch"]
        runner = export_setup["runner"]

        src_rel_path = "util/cli_export.py"
        src_file = root / src_rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)
        content = "# cli export\nVALUE = 7\n"
        src_file.write_text(content, encoding="utf-8")

        monkeypatch.chdir(root)
        result = runner.invoke(cli, ["export", src_rel_path, "test:util/cli_export.py"])
        assert (
            result.exit_code == 0
        ), f"CLI export should succeed. Output: {result.output}"

        dest = sandbox / "util/cli_export.py"
        assert (
            dest.exists()
        ), "CLI export should create the new resource in package resources"
        assert (
            dest.read_text(encoding="utf-8") == content
        ), "Exported content should match source"

    def test_project_export_strips_invoker_header(self, export_setup):
        project = export_setup["project"]
        sandbox = export_setup["sandbox"]
        root = export_setup["root"]

        src_rel_path = "util/strip_header.py"
        src_file = root / src_rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)

        # Compose a fake generated header using the template
        header_template = ResourceManager._get_header_template_path().read_text(
            encoding="utf-8"
        )
        header_text = header_template.format(
            version="0.0.0",
            resource="util/original.py",
            date=date.today().strftime("%Y-%m-%d"),
            hash="0" * 32,
        )
        body = ["VALUE = 42\n", "print(VALUE)\n"]
        src_file.write_text(header_text + "".join(body), encoding="utf-8")

        project.export_resource(src_rel_path, "test:util/strip_header.py")

        dest = sandbox / "util/strip_header.py"
        assert dest.exists(), "Destination should exist after export"
        dest_text = dest.read_text(encoding="utf-8")

        # Header should be stripped; only body should remain
        assert dest_text == "".join(
            body
        ), "Export should strip invoker header from source file"

    def test_project_export_existing_unchanged_skips(self, export_setup, capsys):
        project = export_setup["project"]
        sandbox = export_setup["sandbox"]
        root = export_setup["root"]

        src_rel_path = "util/existing_unchanged.py"
        src_file = root / src_rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)

        # Build a valid header for the file with body hash, implying no manual edits
        body = "VALUE = 123\nprint(VALUE)\n"
        body_hash = ResourceManager._compute_hash(body.encode("ascii"))
        header_template = ResourceManager._get_header_template_path().read_text(
            encoding="utf-8"
        )
        header_text = header_template.format(
            version=metadata.version("invoker"),
            resource=src_rel_path,
            date=date.today().strftime("%Y-%m-%d"),
            hash=body_hash,
        )
        src_file.write_text(header_text + body, encoding="utf-8")

        dest = sandbox / "util/existing_unchanged.py"
        if dest.exists():
            dest.unlink()

        project.export_resource(src_rel_path, "test:util/existing_unchanged.py")

        # No file should be written since there are no manual edits
        captured = capsys.readouterr()
        assert "Skipping export" in captured.err
        assert (
            not dest.exists()
        ), "Export should be skipped for unchanged generated resources"

    def test_project_export_existing_modified_overwrites(self, export_setup, capsys):
        project = export_setup["project"]
        sandbox = export_setup["sandbox"]
        root = export_setup["root"]

        src_rel_path = "util/existing_modified.py"
        src_file = root / src_rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)

        # Stored hash corresponds to original body, but file contains a modified body
        body_original = "VALUE = 1\nprint(VALUE)\n"
        body_modified = "VALUE = 2\nprint(VALUE)\n"
        stored_hash = ResourceManager._compute_hash(body_original.encode("ascii"))
        header_template = ResourceManager._get_header_template_path().read_text(
            encoding="utf-8"
        )
        header_text = header_template.format(
            version=metadata.version("invoker"),
            resource=src_rel_path,
            date=date.today().strftime("%Y-%m-%d"),
            hash=stored_hash,
        )
        src_file.write_text(header_text + body_modified, encoding="utf-8")

        # Ensure destination exists so the overwrite branch is hit
        dest = sandbox / "util/existing_modified.py"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# old content\n", encoding="utf-8")

        project.export_resource(src_rel_path, "test:util/existing_modified.py")

        captured = capsys.readouterr()
        assert "Overwriting existing resource" in captured.err
        # Exported file should be stripped (no header) and contain only modified body
        assert dest.read_text(encoding="utf-8") == body_modified

    def test_export_requires_namespace(self, export_setup, capsys):
        """Test that export without namespace prefix raises an error."""
        project = export_setup["project"]
        root = export_setup["root"]

        src_rel_path = "util/no_namespace.py"
        src_file = root / src_rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("print('hello')\n", encoding="utf-8")

        with pytest.raises(SystemExit):
            project.export_resource(src_rel_path, "util/no_namespace.py")

        captured = capsys.readouterr()
        assert "requires explicit namespace prefix" in captured.err

    def test_export_non_editable_namespace_raises(
        self, export_setup, capsys, monkeypatch
    ):
        """Test that export to non-editable namespace raises an error."""
        project = export_setup["project"]
        root = export_setup["root"]

        # Override editable check to return False for test namespace
        monkeypatch.setattr(
            ResourceManager,
            "is_namespace_editable",
            classmethod(lambda cls, ns: False),
        )

        src_rel_path = "util/non_editable.py"
        src_file = root / src_rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("print('hello')\n", encoding="utf-8")

        with pytest.raises(SystemExit):
            project.export_resource(src_rel_path, "test:util/non_editable.py")

        captured = capsys.readouterr()
        assert "not installed in editable mode" in captured.err

    def test_cli_export_missing_source_raises(self, export_setup, capsys):
        root = export_setup["root"]
        monkeypatch = export_setup["monkeypatch"]

        src_rel_path = "util/does_not_exist.py"
        # Do not create the file

        monkeypatch.chdir(root)
        with pytest.raises(SystemExit):
            cli.main(
                args=["export", src_rel_path, "test:util/does_not_exist.py"],
                prog_name="invoker",
                standalone_mode=False,
            )
        captured = capsys.readouterr()
        assert "Source does not exist" in captured.err
