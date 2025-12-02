from pathlib import Path
from datetime import date
from importlib import metadata
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
    monkeypatch.setattr(ResourceManager, "_get_resources_path", lambda: sandbox)
    monkeypatch.setattr("project.is_editable_install", lambda: True)
    # Ensure sandbox resources path and header template exist
    sandbox.mkdir(parents=True, exist_ok=True)
    header_path = sandbox / "_header.txt"
    # Load the real header template from the repository resources
    repo_header = (Path(__file__).resolve().parent.parent / "resources" / "_header.txt").read_text(encoding="utf-8")
    header_path.write_text(repo_header, encoding="utf-8")
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

        rel_path = "util/custom_export.py"
        src_file = root / rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)
        content = "# custom export file\nVALUE = 1\n"
        src_file.write_text(content, encoding="utf-8")

        project.export_resource(rel_path)

        dest = sandbox / rel_path
        assert dest.exists(), "Export should create the new resource in package resources"
        assert dest.read_text(encoding="utf-8") == content, "Exported content should match source"

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
        project.export_resource(first_src_rel, dest_rel_path=dest_rel)

        dest = sandbox / dest_rel
        assert dest.exists(), "Destination resource should be created on first export"
        assert dest.read_text(encoding="utf-8") == first_content

        second_content = "# second version\nVALUE = 2\n"
        first_src.write_text(second_content, encoding="utf-8")
        project.export_resource(first_src_rel, dest_rel_path=dest_rel)

        assert dest.read_text(encoding="utf-8") == second_content, "Destination resource should be overwritten"

    def test_cli_export_new_resource(self, export_setup):
        project = export_setup["project"]
        sandbox = export_setup["sandbox"]
        root = export_setup["root"]
        monkeypatch = export_setup["monkeypatch"]
        runner = export_setup["runner"]

        rel_path = "util/cli_export.py"
        src_file = root / rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)
        content = "# cli export\nVALUE = 7\n"
        src_file.write_text(content, encoding="utf-8")

        monkeypatch.chdir(root)
        result = runner.invoke(cli, ["export", rel_path])
        assert result.exit_code == 0, f"CLI export should succeed. Output: {result.output}"

        dest = sandbox / rel_path
        assert dest.exists(), "CLI export should create the new resource in package resources"
        assert dest.read_text(encoding="utf-8") == content, "Exported content should match source"

    def test_project_export_strips_invoker_header(self, export_setup):
        project = export_setup["project"]
        sandbox = export_setup["sandbox"]
        root = export_setup["root"]

        rel_path = "util/strip_header.py"
        src_file = root / rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)

        # Compose a fake generated header using the template
        header_template = (sandbox / "_header.txt").read_text(encoding="utf-8")
        header_text = header_template.format(
            version="0.0.0",
            resource="util/original.py",
            date=date.today().strftime("%Y-%m-%d"),
            hash="0" * 32,
        )
        body = ["VALUE = 42\n", "print(VALUE)\n"]
        src_file.write_text(header_text + "".join(body), encoding="utf-8")

        project.export_resource(rel_path)

        dest = sandbox / rel_path
        assert dest.exists(), "Destination should exist after export"
        dest_text = dest.read_text(encoding="utf-8")

        # Header should be stripped; only body should remain
        assert dest_text == "".join(body), "Export should strip invoker header from source file"

    def test_project_export_existing_unchanged_skips(self, export_setup, capsys):
        project = export_setup["project"]
        sandbox = export_setup["sandbox"]
        root = export_setup["root"]

        rel_path = "util/existing_unchanged.py"
        src_file = root / rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)

        # Build a valid header for the file with body hash, implying no manual edits
        body = "VALUE = 123\nprint(VALUE)\n"
        body_hash = ResourceManager._compute_hash(body.encode("ascii"))
        header_template = (sandbox / "_header.txt").read_text(encoding="utf-8")
        header_text = header_template.format(
            version=metadata.version('invoker'),
            resource=rel_path,
            date=date.today().strftime("%Y-%m-%d"),
            hash=body_hash,
        )
        src_file.write_text(header_text + body, encoding="utf-8")

        dest = sandbox / rel_path
        if dest.exists():
            dest.unlink()

        project.export_resource(rel_path)

        # No file should be written since there are no manual edits
        captured = capsys.readouterr()
        assert "Skipping export" in captured.err
        assert not dest.exists(), "Export should be skipped for unchanged generated resources"

    def test_project_export_existing_modified_overwrites(self, export_setup, capsys):
        project = export_setup["project"]
        sandbox = export_setup["sandbox"]
        root = export_setup["root"]

        rel_path = "util/existing_modified.py"
        src_file = root / rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)

        # Stored hash corresponds to original body, but file contains a modified body
        body_original = "VALUE = 1\nprint(VALUE)\n"
        body_modified = "VALUE = 2\nprint(VALUE)\n"
        stored_hash = ResourceManager._compute_hash(body_original.encode("ascii"))
        header_template = (sandbox / "_header.txt").read_text(encoding="utf-8")
        header_text = header_template.format(
            version=metadata.version('invoker'),
            resource=rel_path,
            date=date.today().strftime("%Y-%m-%d"),
            hash=stored_hash,
        )
        src_file.write_text(header_text + body_modified, encoding="utf-8")

        # Ensure destination exists so the overwrite branch is hit
        dest = sandbox / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# old content\n", encoding="utf-8")

        project.export_resource(rel_path)

        captured = capsys.readouterr()
        assert "Overwriting existing resource" in captured.err
        # Exported file should be stripped (no header) and contain only modified body
        assert dest.read_text(encoding="utf-8") == body_modified

    def test_cli_export_non_editable_install_raises(self, export_setup):
        project = export_setup["project"]
        sandbox = export_setup["sandbox"]
        root = export_setup["root"]
        monkeypatch = export_setup["monkeypatch"]
        runner = export_setup["runner"]

        # Override editable check to simulate non-editable install
        monkeypatch.setattr("project.is_editable_install", lambda: False)

        rel_path = "util/non_editable.py"
        src_file = root / rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("print('hello')\n", encoding="utf-8")

        monkeypatch.chdir(root)
        result = runner.invoke(cli, ["export", rel_path])
        assert result.exit_code != 0, "CLI export should fail for non-editable install"
        assert "editable mode" in result.stderr or "editable mode" in result.output

    def test_cli_export_missing_source_raises(self, export_setup):
        project = export_setup["project"]
        root = export_setup["root"]
        monkeypatch = export_setup["monkeypatch"]
        runner = export_setup["runner"]

        rel_path = "util/does_not_exist.py"
        # Do not create the file

        monkeypatch.chdir(root)
        result = runner.invoke(cli, ["export", rel_path])
        assert result.exit_code != 0, "CLI export should fail when source file is missing"
        assert "Source file does not exist" in (result.stderr or result.output)


