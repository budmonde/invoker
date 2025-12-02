from pathlib import Path
from datetime import date
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

        # Compose a fake generated header + body
        header = []
        header.append("# Invoker: v0.0.0\n")
        header.append("# DO NOT MANUALLY EDIT THIS FILE.\n")
        header.append("#\n")
        header.append("# This script was generated with invoker.\n")
        header.append("# To regenerate file, run `invoker rebuild`.\n")
        header.append(f"# Invoker resource: util/original.py\n")
        header.append(f"# Date: {date.today().strftime('%Y-%m-%d')}\n")
        header.append("# Hash:\tabc123\n")
        header.append("\n")
        body = ["VALUE = 42\n", "print(VALUE)\n"]
        src_file.write_text("".join(header + body), encoding="utf-8")

        project.export_resource(rel_path)

        dest = sandbox / rel_path
        assert dest.exists(), "Destination should exist after export"
        dest_text = dest.read_text(encoding="utf-8")

        # Header should be stripped; only body should remain
        assert dest_text == "".join(body), "Export should strip invoker header from source file"


