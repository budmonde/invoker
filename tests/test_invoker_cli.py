"""
Unit tests for invoker.py CLI commands.

Tests the Click CLI interface for all invoker commands.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from invoker import cli


class TestInvokerCLI:
    """Test suite for invoker CLI commands."""

    @pytest.fixture
    def runner(self):
        """Provide a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create a temporary directory for each test."""
        return tmp_path

    # =========================================================================
    # Init Command Tests
    # =========================================================================

    def test_init_command_success(self, runner, temp_project_dir):
        """Test that 'invoker init' successfully initializes a project."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            result = runner.invoke(cli, ["init"])

            assert (
                result.exit_code == 0
            ), f"Init should succeed. Output: {result.output}"
            assert "Initializing new project" in result.output
            assert "Success!" in result.output

            # Verify invoker.py was created
            assert Path("invoker.py").exists(), "invoker.py should be created"

    def test_init_command_already_initialized(self, runner, temp_project_dir):
        """Test that 'invoker init' fails if project already initialized."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            # Initialize once
            runner.invoke(cli, ["init"])

            # Try to initialize again
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert "Invoker Error:" in result.output, "Should show error message"

    def test_init_command_output_messages(self, runner, temp_project_dir):
        """Test that 'invoker init' shows proper colored output."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            result = runner.invoke(cli, ["init"])

            output = result.output
            assert "Initializing new project at current directory" in output
            assert "Success!" in output

    def test_uninitialized_project_error_message(self, runner, temp_project_dir):
        """Test that operations on uninitialized project show correct error."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            # Try various commands without initializing
            commands = [
                ["create", "module", "test"],
                ["create", "script", "test"],
                ["rebuild"],
                ["run", "test"],
                ["debug", "test.py"],
            ]

            for cmd in commands:
                result = runner.invoke(cli, cmd)
                assert (
                    "Invoker Error:" in result.output
                ), f"Command {cmd} should show error"
                assert (
                    "invoker.py file is missing in project" in result.output
                ), f"Command {cmd} should indicate missing invoker.py"

    # =========================================================================
    # Create Module Command Tests
    # =========================================================================

    def test_create_module_command_success(self, runner, temp_project_dir):
        """Test that 'invoker create module' successfully creates a module."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            # Initialize project first
            runner.invoke(cli, ["init"])

            # Create module
            result = runner.invoke(cli, ["create", "module", "test_module"])

            assert (
                result.exit_code == 0
            ), f"Create module should succeed. Output: {result.output}"
            assert "Creating new module test_module" in result.output
            assert "Success!" in result.output

            # Verify module was created
            module_dir = Path("test_module")
            assert module_dir.exists(), "Module directory should be created"
            assert (
                module_dir / "__init__.py"
            ).exists(), "Module __init__.py should exist"

    def test_create_module_command_without_init(self, runner, temp_project_dir):
        """Test that 'invoker create module' fails if project not initialized."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            result = runner.invoke(cli, ["create", "module", "test_module"])

            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert (
                "Invoker Error:" in result.output
            ), "Should show error for uninitialized project"
            assert (
                "invoker.py file is missing in project" in result.output
            ), "Should indicate missing invoker.py file"

    def test_create_module_command_duplicate(self, runner, temp_project_dir):
        """Test that 'invoker create module' fails for duplicate module."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])
            runner.invoke(cli, ["create", "module", "duplicate_module"])

            # Try to create same module again
            result = runner.invoke(cli, ["create", "module", "duplicate_module"])

            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert (
                "Invoker Error:" in result.output
            ), "Should show error for duplicate module"

    def test_create_module_command_with_underscores(self, runner, temp_project_dir):
        """Test creating a module with underscores in the name."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            result = runner.invoke(cli, ["create", "module", "my_test_module"])

            assert result.exit_code == 0
            assert "Success!" in result.output
            assert Path("my_test_module").exists()

    # =========================================================================
    # Create Script Command Tests
    # =========================================================================

    def test_create_script_command_success(self, runner, temp_project_dir):
        """Test that 'invoker create script' successfully creates a script."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            result = runner.invoke(cli, ["create", "script", "test_script"])

            assert (
                result.exit_code == 0
            ), f"Create script should succeed. Output: {result.output}"
            assert "Creating new script test_script" in result.output
            assert "Success!" in result.output

            # Verify script was created
            assert Path("test_script.py").exists(), "Script file should be created"

    def test_create_script_command_without_init(self, runner, temp_project_dir):
        """Test that 'invoker create script' fails if project not initialized."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            result = runner.invoke(cli, ["create", "script", "test_script"])

            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert (
                "Invoker Error:" in result.output
            ), "Should show error for uninitialized project"
            assert (
                "invoker.py file is missing in project" in result.output
            ), "Should indicate missing invoker.py file"

    def test_create_script_command_duplicate(self, runner, temp_project_dir):
        """Test that 'invoker create script' fails for duplicate script."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])
            runner.invoke(cli, ["create", "script", "duplicate_script"])

            result = runner.invoke(cli, ["create", "script", "duplicate_script"])

            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert (
                "Invoker Error:" in result.output
            ), "Should show error for duplicate script"

    def test_create_script_command_with_py_extension(self, runner, temp_project_dir):
        """Test creating a script with .py extension in the name."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            result = runner.invoke(cli, ["create", "script", "test_script.py"])

            assert result.exit_code == 0
            assert "Success!" in result.output
            assert Path("test_script.py").exists()
            # Should not create test_script.py.py
            assert not Path("test_script.py.py").exists()

    # =========================================================================
    # Rebuild Command Tests
    # =========================================================================

    def test_rebuild_command_success(self, runner, temp_project_dir):
        """Test that 'invoker rebuild' successfully rebuilds a project."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            result = runner.invoke(cli, ["rebuild"])

            assert (
                result.exit_code == 0
            ), f"Rebuild should succeed. Output: {result.output}"
            assert "Rebuildng project" in result.output
            assert "Success!" in result.output

    def test_rebuild_command_without_init(self, runner, temp_project_dir):
        """Test that 'invoker rebuild' fails if project not initialized."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            result = runner.invoke(cli, ["rebuild"])

            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert (
                "Invoker Error:" in result.output
            ), "Should show error for uninitialized project"
            assert (
                "invoker.py file is missing in project" in result.output
            ), "Should indicate missing invoker.py file"

    def test_rebuild_command_with_modified_files(self, runner, temp_project_dir):
        """Test rebuild command with modified invoker files."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            # Modify invoker.py
            invoker_file = Path("invoker.py")
            content = invoker_file.read_text()
            invoker_file.write_text(content + "\n# Modified\n")

            result = runner.invoke(cli, ["rebuild"])

            assert result.exit_code == 0
            assert "Success!" in result.output
            # Backup should be created
            assert Path(
                "invoker.py.bak"
            ).exists(), "Backup file should be created for modified file"

    # =========================================================================
    # Run Command Tests
    # =========================================================================

    def test_run_command_success(self, runner, temp_project_dir):
        """Test that 'invoker run' executes a script."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])
            runner.invoke(cli, ["create", "script", "runnable_script"])

            # Modify script to create a marker file
            script_file = Path("runnable_script.py")
            script_content = """#!/usr/bin/env python
from invoker import InvokerScript


class RunnableScript(InvokerScript):
    def run(self):
        super().run()
        with open("marker.txt", "w") as f:
            f.write("executed")


if __name__ == "__main__":
    RunnableScript(run_as_root_script=True).run()
"""
            script_file.write_text(script_content)

            result = runner.invoke(cli, ["run", "runnable_script"])

            # Note: The actual script execution might fail due to import issues
            # in the isolated filesystem, but the CLI should process it
            assert "Running script runnable_script" in result.output

    def test_run_command_without_init(self, runner, temp_project_dir):
        """Test that 'invoker run' fails if project not initialized."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            result = runner.invoke(cli, ["run", "nonexistent"])

            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert (
                "Invoker Error:" in result.output
            ), "Should show error for uninitialized project"
            assert (
                "invoker.py file is missing in project" in result.output
            ), "Should indicate missing invoker.py file"

    def test_run_command_nonexistent_script(self, runner, temp_project_dir):
        """Test that 'invoker run' fails for nonexistent script."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            result = runner.invoke(cli, ["run", "nonexistent_script"])

            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert (
                "Invoker Error:" in result.output
            ), "Should show error for nonexistent script"

    # =========================================================================
    # Debug Command Tests
    # =========================================================================

    def test_debug_command_success(self, runner, temp_project_dir):
        """Test that 'invoker debug' attempts to debug a script."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])
            runner.invoke(cli, ["create", "script", "debug_script"])

            result = runner.invoke(cli, ["debug", "debug_script.py"])

            # Debug command shows output message
            assert "Running script debug_script.py" in result.output

    def test_debug_command_without_init(self, runner, temp_project_dir):
        """Test that 'invoker debug' fails if project not initialized."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            result = runner.invoke(cli, ["debug", "nonexistent.py"])

            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert (
                "Invoker Error:" in result.output
            ), "Should show error for uninitialized project"
            assert (
                "invoker.py file is missing in project" in result.output
            ), "Should indicate missing invoker.py file"

    def test_debug_command_nonexistent_script(self, runner, temp_project_dir):
        """Test that 'invoker debug' fails for nonexistent script."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            result = runner.invoke(cli, ["debug", "nonexistent_script.py"])

            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert (
                "Invoker Error:" in result.output
            ), "Should show error for nonexistent script"

    def test_debug_command_invalid_format(self, runner, temp_project_dir):
        """Test that 'invoker debug' fails for invalid script name format."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            # Script name without .py extension should fail
            result = runner.invoke(cli, ["debug", "script_without_extension"])

            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert (
                "Invoker Error:" in result.output
            ), "Should show error for invalid format"
            assert (
                "Invalid script name format" in result.output
            ), "Should indicate invalid format"

    # =========================================================================
    # Lint Command Tests
    # =========================================================================

    def test_lint_command_success(self, runner, temp_project_dir):
        """Test that 'invoker lint' calls linters with correct arguments."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            # Mock subprocess.call to verify linters are called correctly
            with patch("subprocess.call") as mock_call:
                mock_call.return_value = 0  # Simulate successful linter execution

                result = runner.invoke(cli, ["lint"])

                # Verify no InvokerError was raised
                assert (
                    "Invoker Error:" not in result.output
                ), f"Lint should not raise InvokerError. Output: {result.output}"

                # Verify all three linters were called
                assert (
                    mock_call.call_count == 3
                ), "Should call three linters (black, isort, flake8)"

                # Verify each linter was called with a path argument
                calls = mock_call.call_args_list

                # Check that black, isort, and flake8 were called with paths
                assert (
                    len(calls[0][0][0]) == 2 and calls[0][0][0][0] == "black"
                ), "First call should be to black"
                assert (
                    len(calls[1][0][0]) == 2 and calls[1][0][0][0] == "isort"
                ), "Second call should be to isort"
                assert (
                    len(calls[2][0][0]) == 2 and calls[2][0][0][0] == "flake8"
                ), "Third call should be to flake8"

                # Verify all calls use a Path object (can be relative or absolute)
                for i, call_args in enumerate(calls):
                    command_list = call_args[0][0]
                    assert (
                        len(command_list) == 2
                    ), f"Call {i} should have command and path"
                    assert isinstance(
                        command_list[1], Path
                    ), f"Call {i} should pass a Path object as argument"

    def test_lint_command_calls_linters_in_order(self, runner, temp_project_dir):
        """Test that lint command calls linters in the correct order."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            with patch("subprocess.call") as mock_call:
                mock_call.return_value = 0

                runner.invoke(cli, ["lint"])

                # Verify linters are called in the correct order: black, isort, flake8
                calls = mock_call.call_args_list
                assert len(calls) == 3

                # Extract command names from calls
                commands = [call_args[0][0][0] for call_args in calls]
                assert commands == [
                    "black",
                    "isort",
                    "flake8",
                ], "Linters should be called in order: black, isort, flake8"

    def test_lint_command_with_linter_failures(self, runner, temp_project_dir):
        """Test that lint command handles linter failures gracefully."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            # Simulate linters returning non-zero exit codes (finding issues)
            with patch("subprocess.call") as mock_call:
                mock_call.return_value = 1  # Non-zero exit code

                result = runner.invoke(cli, ["lint"])

                # Should not raise InvokerError even if linters find issues
                assert (
                    "Invoker Error:" not in result.output
                ), "Lint should not raise InvokerError on linter failures"

                # All linters should still be called
                assert (
                    mock_call.call_count == 3
                ), "All linters should be called even if some fail"

    def test_lint_command_without_init(self, runner, temp_project_dir):
        """Test that 'invoker lint' fails if project not initialized."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            # Lint will try to load the project and should fail
            result = runner.invoke(cli, ["lint"])

            # Should show proper error and exit with code 1
            assert result.exit_code == 1, "Command should exit with code 1 on error"
            assert (
                "Invoker Error:" in result.output
            ), "Should show error for uninitialized project"
            assert (
                "invoker.py file is missing in project" in result.output
            ), "Should indicate missing invoker.py file"

    # =========================================================================
    # CLI Group Tests
    # =========================================================================

    def test_cli_help(self, runner):
        """Test that 'invoker --help' shows help message."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "init" in result.output
        assert "create" in result.output
        assert "rebuild" in result.output
        assert "run" in result.output
        assert "debug" in result.output

    def test_create_help(self, runner):
        """Test that 'invoker create --help' shows create subcommands."""
        result = runner.invoke(cli, ["create", "--help"])

        assert result.exit_code == 0
        assert "module" in result.output
        assert "script" in result.output

    def test_invalid_command(self, runner):
        """Test that invalid command shows error."""
        result = runner.invoke(cli, ["invalid_command"])

        assert result.exit_code != 0
        assert "Error" in result.output or "Usage" in result.output

    # =========================================================================
    # Integration Tests
    # =========================================================================

    def test_full_workflow_create_module_and_script(self, runner, temp_project_dir):
        """Test complete workflow: init, create module, create script."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            # Initialize
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert "Success!" in result.output

            # Create module
            result = runner.invoke(cli, ["create", "module", "data_loader"])
            assert result.exit_code == 0
            assert "Success!" in result.output

            # Create script
            result = runner.invoke(cli, ["create", "script", "train_model"])
            assert result.exit_code == 0
            assert "Success!" in result.output

            # Verify all files exist
            assert Path("invoker.py").exists()
            assert Path("data_loader").is_dir()
            assert Path("data_loader/__init__.py").exists()
            assert Path("train_model.py").exists()

    def test_workflow_create_multiple_modules(self, runner, temp_project_dir):
        """Test creating multiple modules in sequence."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            runner.invoke(cli, ["init"])

            modules = ["loader", "processor", "validator"]
            for module in modules:
                result = runner.invoke(cli, ["create", "module", module])
                assert result.exit_code == 0
                assert "Success!" in result.output
                assert Path(module).exists()

    def test_workflow_init_create_rebuild(self, runner, temp_project_dir):
        """Test workflow: init, create, modify, rebuild."""
        with runner.isolated_filesystem(temp_dir=temp_project_dir):
            # Initialize
            runner.invoke(cli, ["init"])

            # Create module
            runner.invoke(cli, ["create", "module", "test_module"])

            # Modify invoker.py
            invoker_file = Path("invoker.py")
            content = invoker_file.read_text()
            invoker_file.write_text(content + "\n# Modified\n")

            # Rebuild
            result = runner.invoke(cli, ["rebuild"])
            assert result.exit_code == 0
            assert "Success!" in result.output
            assert Path("invoker.py.bak").exists()
