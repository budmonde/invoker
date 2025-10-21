"""Integration tests for running invoker scripts with command-line arguments."""
import subprocess
import json
from pathlib import Path

from project import Project


class TestRunScript:
    """Test suite for running invoker scripts."""
    
    def test_run_script_with_default_values(self, temp_project_dir):
        """Test running a script with default argument values."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a test script with various argument types
        script_name = "test_args_script"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        # Modify the script to have specific arguments and write output
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class TestArgsScript(Script):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            string_arg="default_string",
            int_arg=42,
            float_arg=3.14,
            bool_arg=False,
            list_arg=["item1", "item2", "item3"]
        ))
        return args

    def run(self):
        super().run()
        # Write arguments to a JSON file for verification
        output = {
            "string_arg": self.opt.string_arg,
            "int_arg": self.opt.int_arg,
            "float_arg": self.opt.float_arg,
            "bool_arg": self.opt.bool_arg,
            "list_arg": self.opt.list_arg
        }
        output_file = "output.json"
        with open(output_file, "w") as f:
            json.dump(output, f)


if __name__ == "__main__":
    TestArgsScript(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run the script with default values
        result = subprocess.run(
            ["python", str(script_file)],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        # Check that script ran successfully
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify output file was created
        output_file = temp_project_dir / "output.json"
        assert output_file.exists(), "Output file should be created"
        
        # Verify default values were used
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["string_arg"] == "default_string", \
            "String argument should have default value"
        assert output["int_arg"] == 42, \
            "Integer argument should have default value"
        assert output["float_arg"] == 3.14, \
            "Float argument should have default value"
        assert output["bool_arg"] is False, \
            "Boolean argument should have default value"
        assert output["list_arg"] == ["item1", "item2", "item3"], \
            "List argument should have default value"
    
    def test_run_script_with_overridden_string(self, temp_project_dir):
        """Test running a script with overridden string argument."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        script_name = "string_override_script"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class StringOverrideScript(Script):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            message="default_message"
        ))
        return args

    def run(self):
        super().run()
        with open("output.json", "w") as f:
            json.dump({"message": self.opt.message}, f)


if __name__ == "__main__":
    StringOverrideScript(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with overridden string value
        result = subprocess.run(
            ["python", str(script_file), "--message", "custom_value"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify overridden value was used
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["message"] == "custom_value", \
            "String argument should be overridden"
    
    def test_run_script_with_overridden_numeric(self, temp_project_dir):
        """Test running a script with overridden numeric arguments."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        script_name = "numeric_override_script"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class NumericOverrideScript(Script):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            count=10,
            rate=0.5
        ))
        return args

    def run(self):
        super().run()
        with open("output.json", "w") as f:
            json.dump({
                "count": self.opt.count,
                "rate": self.opt.rate
            }, f)


if __name__ == "__main__":
    NumericOverrideScript(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with overridden numeric values
        result = subprocess.run(
            ["python", str(script_file), "--count", "99", "--rate", "0.75"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify overridden values were used
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["count"] == 99, \
            "Integer argument should be overridden"
        assert output["rate"] == 0.75, \
            "Float argument should be overridden"
    
    def test_run_script_with_overridden_list(self, temp_project_dir):
        """Test running a script with overridden list argument."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        script_name = "list_override_script"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class ListOverrideScript(Script):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            items=["a", "b", "c"]
        ))
        return args

    def run(self):
        super().run()
        with open("output.json", "w") as f:
            json.dump({"items": self.opt.items}, f)


if __name__ == "__main__":
    ListOverrideScript(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with overridden list value
        result = subprocess.run(
            ["python", str(script_file), "--items", "x", "y", "z"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify overridden list was used
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["items"] == ["x", "y", "z"], \
            "List argument should be overridden"
    
    def test_run_script_with_boolean_flag(self, temp_project_dir):
        """Test running a script with boolean flag argument."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        script_name = "bool_flag_script"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class BoolFlagScript(Script):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            verbose=False,
            debug=True
        ))
        return args

    def run(self):
        super().run()
        with open("output.json", "w") as f:
            json.dump({
                "verbose": self.opt.verbose,
                "debug": self.opt.debug
            }, f)


if __name__ == "__main__":
    BoolFlagScript(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with boolean flags (verbose=True, debug=False)
        result = subprocess.run(
            ["python", str(script_file), "--verbose", "--debug"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify boolean flags were toggled
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["verbose"] is True, \
            "Boolean argument (default False) should be toggled to True"
        assert output["debug"] is False, \
            "Boolean argument (default True) should be toggled to False"
    
    def test_run_script_with_mixed_overrides(self, temp_project_dir):
        """Test running a script with multiple argument types overridden."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        script_name = "mixed_args_script"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class MixedArgsScript(Script):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            name="default",
            count=5,
            rate=1.0,
            enable=False,
            tags=["tag1"]
        ))
        return args

    def run(self):
        super().run()
        with open("output.json", "w") as f:
            json.dump({
                "name": self.opt.name,
                "count": self.opt.count,
                "rate": self.opt.rate,
                "enable": self.opt.enable,
                "tags": self.opt.tags
            }, f)


if __name__ == "__main__":
    MixedArgsScript(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with some values overridden, some default
        result = subprocess.run(
            ["python", str(script_file),
             "--name", "custom",
             "--count", "20",
             "--enable",
             "--tags", "alpha", "beta", "gamma"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify mixed values
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["name"] == "custom", "String should be overridden"
        assert output["count"] == 20, "Integer should be overridden"
        assert output["rate"] == 1.0, "Float should keep default value"
        assert output["enable"] is True, "Boolean should be toggled"
        assert output["tags"] == ["alpha", "beta", "gamma"], \
            "List should be overridden"
    
    def test_run_script_via_invoker_py(self, temp_project_dir):
        """Test running a script through invoker.py run command."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        script_name = "invoker_run_test"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class InvokerRunTest(Script):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            value=100
        ))
        return args

    def run(self):
        super().run()
        with open("output.json", "w") as f:
            json.dump({"value": self.opt.value}, f)


if __name__ == "__main__":
    InvokerRunTest(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run via invoker.py run command
        invoker_file = temp_project_dir / "invoker.py"
        result = subprocess.run(
            ["python", str(invoker_file), "run", f"{script_name}.py", "--value", "200"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run via invoker.py. stderr: {result.stderr}"
        
        # Verify value was passed correctly
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["value"] == 200, \
            "Argument should be passed through invoker.py run command"
    
    def test_run_script_with_empty_list_default(self, temp_project_dir):
        """Test running a script with empty list as default."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        script_name = "empty_list_script"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class EmptyListScript(Script):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            items=[]
        ))
        return args

    def run(self):
        super().run()
        with open("output.json", "w") as f:
            json.dump({"items": self.opt.items}, f)


if __name__ == "__main__":
    EmptyListScript(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with default empty list
        result = subprocess.run(
            ["python", str(script_file)],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify empty list was used
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["items"] == [], "Empty list should be preserved as default"
        
        # Now run with overridden list
        result = subprocess.run(
            ["python", str(script_file), "--items", "new_item"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify list was populated
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["items"] == ["new_item"], \
            "Empty list should be overridable"
    
    def test_run_script_with_module_default_config(self, temp_project_dir):
        """Test running a script with a module using default configuration."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a module
        module_name = "data_loader"
        project.create_module(module_name)
        
        # Modify the base module to have specific arguments
        module_base_file = temp_project_dir / module_name / f"base_{module_name}.py"
        module_content = '''from invoker import Module


class BaseDataLoader(Module):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            path="default_path.txt",
            batch_size=32,
            shuffle=True,
            workers=4
        ))
        return args
'''
        
        with open(module_base_file, "w") as f:
            f.write(module_content)
        
        # Create a script that uses this module
        script_name = "train_model"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class TrainModel(Script):
    @classmethod
    def modules(cls):
        mods = super().modules()
        mods.update(dict(
            data_loader="base"
        ))
        return mods

    def run(self):
        super().run()
        # Access module configuration
        output = {
            "path": self.data_loader.opt.path,
            "batch_size": self.data_loader.opt.batch_size,
            "shuffle": self.data_loader.opt.shuffle,
            "workers": self.data_loader.opt.workers
        }
        with open("output.json", "w") as f:
            json.dump(output, f)


if __name__ == "__main__":
    TrainModel(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run the script with default module configuration
        result = subprocess.run(
            ["python", str(script_file)],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify module used default configuration
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["path"] == "default_path.txt", \
            "Module string argument should have default value"
        assert output["batch_size"] == 32, \
            "Module integer argument should have default value"
        assert output["shuffle"] is True, \
            "Module boolean argument should have default value"
        assert output["workers"] == 4, \
            "Module integer argument should have default value"
    
    def test_run_script_with_module_overridden_config(self, temp_project_dir):
        """Test running a script with module configuration overridden via command line."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a module
        module_name = "processor"
        project.create_module(module_name)
        
        # Modify the base module
        module_base_file = temp_project_dir / module_name / f"base_{module_name}.py"
        module_content = '''from invoker import Module


class BaseProcessor(Module):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            method="default_method",
            iterations=10,
            rate=0.5
        ))
        return args
'''
        
        with open(module_base_file, "w") as f:
            f.write(module_content)
        
        # Create a script that uses this module
        script_name = "process_data"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class ProcessData(Script):
    @classmethod
    def modules(cls):
        mods = super().modules()
        mods.update(dict(
            processor="base"
        ))
        return mods

    def run(self):
        super().run()
        output = {
            "method": self.processor.opt.method,
            "iterations": self.processor.opt.iterations,
            "rate": self.processor.opt.rate
        }
        with open("output.json", "w") as f:
            json.dump(output, f)


if __name__ == "__main__":
    ProcessData(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with overridden module configuration
        result = subprocess.run(
            ["python", str(script_file),
             "--processor.method", "custom_method",
             "--processor.iterations", "50",
             "--processor.rate", "0.9"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify module configuration was overridden
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["method"] == "custom_method", \
            "Module string argument should be overridden"
        assert output["iterations"] == 50, \
            "Module integer argument should be overridden"
        assert output["rate"] == 0.9, \
            "Module float argument should be overridden"
    
    def test_run_script_with_multiple_modules(self, temp_project_dir):
        """Test running a script with multiple modules each with their own config."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create first module
        module1_name = "loader"
        project.create_module(module1_name)
        
        module1_base_file = temp_project_dir / module1_name / f"base_{module1_name}.py"
        module1_content = '''from invoker import Module


class BaseLoader(Module):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            source="default_source"
        ))
        return args
'''
        
        with open(module1_base_file, "w") as f:
            f.write(module1_content)
        
        # Create second module
        module2_name = "transformer"
        project.create_module(module2_name)
        
        module2_base_file = temp_project_dir / module2_name / f"base_{module2_name}.py"
        module2_content = '''from invoker import Module


class BaseTransformer(Module):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            format="json"
        ))
        return args
'''
        
        with open(module2_base_file, "w") as f:
            f.write(module2_content)
        
        # Create a script that uses both modules
        script_name = "pipeline"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class Pipeline(Script):
    @classmethod
    def modules(cls):
        mods = super().modules()
        mods.update(dict(
            loader="base",
            transformer="base"
        ))
        return mods

    def run(self):
        super().run()
        output = {
            "loader_source": self.loader.opt.source,
            "transformer_format": self.transformer.opt.format
        }
        with open("output.json", "w") as f:
            json.dump(output, f)


if __name__ == "__main__":
    Pipeline(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with mixed module configurations (one default, one overridden)
        result = subprocess.run(
            ["python", str(script_file),
             "--transformer.format", "xml"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify module configurations
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["loader_source"] == "default_source", \
            "First module should use default value"
        assert output["transformer_format"] == "xml", \
            "Second module should use overridden value"
    
    def test_run_script_with_module_list_argument(self, temp_project_dir):
        """Test module configuration with list argument type."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a module with list argument
        module_name = "filter"
        project.create_module(module_name)
        
        module_base_file = temp_project_dir / module_name / f"base_{module_name}.py"
        module_content = '''from invoker import Module


class BaseFilter(Module):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            columns=["col1", "col2", "col3"]
        ))
        return args
'''
        
        with open(module_base_file, "w") as f:
            f.write(module_content)
        
        # Create a script using the module
        script_name = "filter_data"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class FilterData(Script):
    @classmethod
    def modules(cls):
        mods = super().modules()
        mods.update(dict(
            filter="base"
        ))
        return mods

    def run(self):
        super().run()
        output = {
            "columns": self.filter.opt.columns
        }
        with open("output.json", "w") as f:
            json.dump(output, f)


if __name__ == "__main__":
    FilterData(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with overridden list argument
        result = subprocess.run(
            ["python", str(script_file),
             "--filter.columns", "name", "age", "email"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify list was overridden
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["columns"] == ["name", "age", "email"], \
            "Module list argument should be overridden"
    
    def test_run_script_with_module_boolean_flag(self, temp_project_dir):
        """Test module configuration with boolean flag."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a module with boolean arguments
        module_name = "validator"
        project.create_module(module_name)
        
        module_base_file = temp_project_dir / module_name / f"base_{module_name}.py"
        module_content = '''from invoker import Module


class BaseValidator(Module):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            strict=False,
            verbose=True
        ))
        return args
'''
        
        with open(module_base_file, "w") as f:
            f.write(module_content)
        
        # Create a script using the module
        script_name = "validate"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class Validate(Script):
    @classmethod
    def modules(cls):
        mods = super().modules()
        mods.update(dict(
            validator="base"
        ))
        return mods

    def run(self):
        super().run()
        output = {
            "strict": self.validator.opt.strict,
            "verbose": self.validator.opt.verbose
        }
        with open("output.json", "w") as f:
            json.dump(output, f)


if __name__ == "__main__":
    Validate(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with boolean flags toggled
        result = subprocess.run(
            ["python", str(script_file),
             "--validator.strict",
             "--validator.verbose"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify boolean flags were toggled
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["strict"] is True, \
            "Module boolean (default False) should be toggled to True"
        assert output["verbose"] is False, \
            "Module boolean (default True) should be toggled to False"
    
    def test_run_script_with_script_and_module_mixed_args(self, temp_project_dir):
        """Test script with both script-level and module-level arguments."""
        # Initialize project
        project = Project(temp_project_dir)
        project.initialize()
        
        # Create a module
        module_name = "engine"
        project.create_module(module_name)
        
        module_base_file = temp_project_dir / module_name / f"base_{module_name}.py"
        module_content = '''from invoker import Module


class BaseEngine(Module):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            threads=1
        ))
        return args
'''
        
        with open(module_base_file, "w") as f:
            f.write(module_content)
        
        # Create a script with both script and module args
        script_name = "compute"
        project.create_script(script_name)
        
        script_file = temp_project_dir / f"{script_name}.py"
        
        script_content = '''#!/usr/bin/env python
from invoker import Script
import json


class Compute(Script):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            output="result.txt",
            verbose=False
        ))
        return args
    
    @classmethod
    def modules(cls):
        mods = super().modules()
        mods.update(dict(
            engine="base"
        ))
        return mods

    def run(self):
        super().run()
        output = {
            "script_output": self.opt.output,
            "script_verbose": self.opt.verbose,
            "module_threads": self.engine.opt.threads
        }
        with open("output.json", "w") as f:
            json.dump(output, f)


if __name__ == "__main__":
    Compute(run_as_root_script=True).run()
'''
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with both script and module arguments overridden
        result = subprocess.run(
            ["python", str(script_file),
             "--output", "custom.txt",
             "--verbose",
             "--engine.threads", "8"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, \
            f"Script should run successfully. stderr: {result.stderr}"
        
        # Verify both script and module configurations
        output_file = temp_project_dir / "output.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        
        assert output["script_output"] == "custom.txt", \
            "Script-level string argument should be overridden"
        assert output["script_verbose"] is True, \
            "Script-level boolean should be toggled"
        assert output["module_threads"] == 8, \
            "Module-level integer argument should be overridden"

