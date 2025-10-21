"""Invoker Python Project Manager

This script enables bootstrappable python script authoring that are easy to configure with command line arguments, interactive debugging, profiling, logging infrastructure, and dynamic module loading. To create a bootstrapped script, inherit from the "InvokerScript" class and implement the run() function. For example:

```
import logging

from invoker import InvokerScript


class MyScript(InvokerScript):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(key = "default_value"))
        return args

    def run(self):
        super().run()
        logging.info(f'Hello World! You've passed {self.opt.key} from the command line.')
```

To use modules, import the module classes and specify them in the modules() method:

```
import logging

from invoker import InvokerScript
from my_modules import DataLoader


class MyScript(InvokerScript):
    @classmethod
    def modules(cls):
        mods = super().modules()
        mods.update(dict(
            my_data_loader=DataLoader
        ))
        return mods

    def run(self):
        super().run()
        logging.info(f'Data path: {self.my_data_loader.opt.path}')
```

To run the script, run
```
python invoker.py run my_script.py --key custom_value
```

To pass module options from command line:
```
python invoker.py run my_script.py --my_data_loader.path /data/input
```

To enter an interactive ipython session at a specific line within the script, run
```
python invoker.py debug my_script.py:14
```

Invoker projects can also be managed using a python CLI tool. For more information, see https://github.com/budmonde/invoker
"""
import argparse
import copy
import cProfile as profile
import importlib
import importlib.util
import inspect
import logging
import logging.config
import os
import pprint
import pstats
import re
import sys
from pathlib import Path


class InvokerScript:
    """
        @args_dict         : keyword argument overrides to default values of self.args()
        @args_list         : argv list passed into argparse. args_dict takes priority
        @run_as_root_script: run script as the entry point of the program
        @log_to_console    : whether to emit logs to console or not
        @logfile_root      : root path to logfiles
    """
    def __init__(
            self,
            args_dict = None,
            args_list = None,
            run_as_root_script: bool = False,
            log_to_console: bool = True,
            logfile_root: str = None,
    ):
        if run_as_root_script:
            _initialize_logger(log_to_console, logfile_root, _to_underscore_case(type(self).__name__))

        parser_manager = ParserManager()
        parser_manager.add_arguments(self.args())
        for attr_name, module_cls in self.modules().items():
            parser_manager.add_arguments(module_cls.args(), key_prefix = attr_name)
        script_config = self.build_config(parser_manager.parse_args(args_dict, args_list))

        module_conf = {}
        for attr_name, module_cls in self.modules().items():
            is_valid_module_conf = lambda key: len(key.split(".")) == 2
            module_conf_matches_module = lambda key: key.split(".")[0] == attr_name
            get_module_conf_key = lambda key: key.split(".")[1]
            module_args = {
                get_module_conf_key(key) : value
                for key, value in script_config.items()
                if is_valid_module_conf(key) and module_conf_matches_module(key)
            }

            cls_inst = module_cls(module_args)
            setattr(self, attr_name, cls_inst)
            module_conf[attr_name] = _serialize_opt(cls_inst.opt)
            for module_arg in module_args.keys():
                del script_config[".".join([attr_name, module_arg])]
        script_config.update(module_conf)
        self.opt = _deserialize_config(script_config)

        logging.info("Initialized script %s with options:\n%s", type(self).__name__, pprint.pformat(script_config, sort_dicts=False))

    @classmethod
    def args(cls):
        return {}

    @classmethod
    def modules(cls):
        return {}

    @classmethod
    def build_config(cls, args):
        return args

    def run(self):
        logging.info("Running script %s", type(self).__name__)
        pass

    def profile(self, top=10):
        logging.info("Profiling script %s", type(self).__name__)
        prof = profile.Profile()
        prof.enable()
        self.run()
        prof.disable()
        stats = pstats.Stats(prof).strip_dirs().sort_stats("cumtime")
        stats.print_stats(top)

    def embed(self):
        from IPython.terminal.embed import InteractiveShellEmbed
        caller_frame = inspect.currentframe().f_back
        module = get_module(caller_frame.f_globals["__file__"])
        shell = InteractiveShellEmbed(user_module=module)

        local_namespace = dict(caller_frame.f_locals)
        module.__dict__.update(local_namespace)
        shell()


def _to_underscore_case(string):
    return "_".join([token.lower() for token in re.findall("[A-Z][^A-Z]*", string)])


def _to_camel_case(string):
    return "".join([token.capitalize() for token in string.split("_")])


def _initialize_logger(log_to_console, logfile_root, logfile_name):
    logger_dict = {
        "version": 1,
        "formatters": {},
        "handlers": {},
        "root": {
            "level": os.getenv("INVOKER_LOGLEVEL", "INFO"),
            "handlers": []
        }
    }

    if log_to_console:
        logger_dict["formatters"]["pretty"] = {
            "format": "%(asctime)s [%(levelname)-8s] %(filename)s:%(lineno)d.%(funcName)s() %(message)s",
            "datefmt": "%H:%M:%S",
            "class": "invoker.InvokerFormatter" if (__package__ == "") or (__package__ == None) else ".".join([__package__, "invoker.InvokerFormatter"]),
        }
        logger_dict["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "formatter": "pretty",
            "stream": "ext://sys.stdout"
        }
        logger_dict["root"]["handlers"].append("console")

    if logfile_root is not None:
        logfile_root = Path(logfile_root)
        logfile_root.mkdir(exist_ok=True, parents=True)
        logfile_path = logfile_root / f"{logfile_name}.log"
        do_rollover = True if logfile_path.exists() else False
        logger_dict["formatters"]["verbose"] = {
            "format": "%(asctime)s,%(msecs)d [%(levelname)-8s] %(filename)s:%(lineno)d.%(funcName)s() %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
        logger_dict["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "verbose",
            "filename": logfile_path,
            "maxBytes": 1048576,  # 1MB
            "backupCount": 20,
        }
        logger_dict["root"]["handlers"].append("file")

    logging.config.dictConfig(logger_dict)

    if (logfile_root is not None) and do_rollover:
        logging.getLogger("root").handlers[1].doRollover()


class InvokerFormatter(logging.Formatter):
    LVL2COLOR = {
        logging.DEBUG: "\x1b[38m", #  grey
        logging.INFO: "\x1b[36m", #  blue
        logging.WARNING: "\x1b[33m", #  yellow
        logging.ERROR: "\x1b[31m", #  red
        logging.CRITICAL: "\x1b[31;1m", #  bold_red
    }
    RESET = "\x1b[0m"

    def format(self, record):
        super().format(record)
        color = self.LVL2COLOR.get(record.levelno)
        return color + logging.Formatter.format(self, record) + self.RESET


class ParserManager:
    def __init__(self):
        super().__init__()
        self.parser = argparse.ArgumentParser()

    def add_arguments(self, default_args, key_prefix=None):
        for k, v in default_args.items():
            try:
                if type(v) == list:
                    self.parser.add_argument(
                        _build_key(k, key_prefix),
                        type=type(v[0]) if len(v) > 0 else str,
                        nargs="+",
                        default=v
                    )
                elif type(v) == bool:
                    self.parser.add_argument(
                        _build_key(k, key_prefix),
                        action="store_true" if not v else "store_false",
                    )
                else:
                    self.parser.add_argument(
                        _build_key(k, key_prefix),
                        type=type(v),
                        default=v
                    )
            except argparse.ArgumentError:
                logging.warn("Script defaults over-riding module arg %s.", k)

    def parse_args(self, args_dict, fallback_args_list, key_prefix=None):
        if args_dict is not None:
            args_list = []
            for k, v in args_dict.items():
                if type(v) == list:
                    args_list.append(_build_key(k, key_prefix))
                    for item in v:
                        args_list.append(str(item))
                elif type(v) == bool:
                    if v != self.parser.get_default(k):
                        args_list.append(_build_key(k, key_prefix))
                else:
                    args_list.append(_build_key(k, key_prefix))
                    args_list.append(str(v))
            return self._parse_args(args_list)
        elif fallback_args_list is not None:
            return self._parse_args(fallback_args_list)
        else:
            return self._parse_args(None)

    def _parse_args(self, args_list):
        return vars(self.parser.parse_args(args_list))


def _build_key(kname: str, key_prefix: str =None) -> str:
    return f"--{kname}" if key_prefix is None else f"--{key_prefix}.{kname}"


class InvokerModule:
    def __init__(self, args_dict=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if args_dict is not None:
            conf = self.build_config(args_dict)
        else:
            conf = self.build_config(self.args())
        self.opt = _deserialize_config(conf)

    @classmethod
    def args(cls):
        return {}

    @classmethod
    def build_config(cls, args):
        return args


def _serialize_opt(opt):
    out = vars(copy.deepcopy(opt))
    for k, v in out.items():
        if isinstance(v, argparse.Namespace):
            out[k] = _serialize_opt(v)
        else:
            out[k] = v
    return out


def _deserialize_config(config):
    opt = argparse.Namespace()
    for k, v in config.items():
        if isinstance(v, dict):
            setattr(opt, k, _deserialize_config(v))
        else:
            setattr(opt, k, v)
    return opt


def get_module(file_name):
    if file_name is None:
        return None
    module_name = file_name.replace(os.sep, ".").replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, file_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_embed_instrumented_module(file_name, instrument_line_num, instrument_line):
    with open(file_name, "r") as fp:
        lines = fp.readlines()

    script_class_name = _to_camel_case(file_name.replace(".py", ""))
    try:
        script_line_number = next(
            i for i, line in enumerate(lines)
            if line.startswith(f"class {script_class_name}")
        )
    except StopIteration:
        raise RuntimeError("Invalid script %s", file_name)

    get_indent = lambda line: len(line) - len(line.lstrip())

    valid_instrument_line = instrument_line_num is not None and instrument_line_num < len(lines)
    if not valid_instrument_line:
        in_run = False
        for index in range(script_line_number, len(lines) - 1):
            line = lines[index]
            if line.lstrip().startswith("def run"):
                in_run = True
                indent_size = get_indent(line) + 4
            elif in_run:
                if len(line.strip()) > 0 and get_indent(line) < (indent_size or 0):
                    instrument_line_num = index - 1
                    break
        if not valid_instrument_line:
            instrument_line_num = len(lines) - 1
    else:
        indent_size = get_indent(lines[instrument_line_num - 1])

    instrument_line = " " * indent_size + f"{instrument_line}\n"

    new_lines = list(lines)
    new_lines.insert(instrument_line_num, instrument_line)
    new_file = file_name.replace(".py", "_instrumented.py")

    with open(new_file, "w") as fp:
        fp.writelines(new_lines)

    module = get_module(new_file)
    module.__file__ = file_name

    os.remove(new_file)
    return module


def get_script(file_name, instrument=False, instrument_line_num=None, instrument_line="exit()"):
    if not instrument:
        module = get_module(file_name)
    else:
        module = get_embed_instrumented_module(file_name, instrument_line_num, instrument_line)
    class_name = _to_camel_case(file_name.replace(os.sep, ".").replace(".py", ""))
    script = getattr(module, class_name)
    return script


if __name__ == "__main__":
    _initialize_logger(True, None, "invoker")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices = ["run", "debug"], type=str, help="Invoker script command.")
    parser.add_argument("script_name", type=str, help="Target invoker script name. Optionally include line number to run until as <script_name>:<line_numbrer>")

    if (len(sys.argv) < 3):
        parser.print_help(sys.stderr)
        exit()

    args = parser.parse_args(sys.argv[1:3])
    script_match = re.match(r"^(\w+\.\w+)(?::(\d+))?$", args.script_name)
    if not script_match:
        logging.error("Invalid script name: %s.", args.script_name)
        exit()
    script_name = script_match.group(1)
    instrument_line_num = int(script_match.group(2)) if script_match.group(2) else None

    if args.command == "run":
        script = get_script(script_name, instrument = instrument_line_num is not None, instrument_line_num = instrument_line_num, instrument_line = "exit()")
    elif args.command == "debug":
        script = get_script(script_name, instrument = True, instrument_line_num = instrument_line_num, instrument_line = "self.embed()")
    else:
        logging.error("Invalid command: %s.", args.command)

    script(args_list = sys.argv[3:], run_as_root_script=True).run()
