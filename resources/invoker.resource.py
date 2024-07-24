import argparse
import copy
import cProfile as profile
import importlib
import logging
import logging.config
import os
import pprint
import pstats
import re
from pathlib import Path


class Script:
    """
        @inp_args_dict     : keyword argument overrides to default values of self.args()
        @args_list         : argv list passed into argparse. If left none, argv from command line used directly
        @run_as_root_script: run script as the entry point of the program
        @log_to_console    : whether to emit logs to console or not
        @logfile_root      : root path to logfiles
    """
    def __init__(
            self,
            inp_args_dict = None,
            args_list = None,
            run_as_root_script: bool = False,
            log_to_console: bool = True,
            logfile_root: str = None,
    ):
        if run_as_root_script:
            _initialize_logger(log_to_console, logfile_root, _to_underscore_case(type(self).__name__))

        parser = _build_argparser(self.args())
        for module_name, module_mode in self.modules().items():
            cls = importlib.import_module(module_name).get_class(module_mode)
            parser = _build_argparser(cls.args(), module_name, parser)

        if inp_args_dict is None:
            all_args = vars(parser.parse_args(args_list))
        else:
            all_args = _parse_args_dict(inp_args_dict, parser)

        conf = self.build_config(all_args.copy())

        module_conf = {}
        for module_name, module_mode in self.modules().items():
            cls = importlib.import_module(module_name).get_class(module_mode)
            module_args = {
                k.split(".")[1]: v
                for k, v in conf.items()
                if len(k.split(".")) == 2 and k.split(".")[0] == module_name
            }
            cls_inst = cls(module_args)
            setattr(self, module_name, cls_inst)
            module_conf[module_name] = _serialize_opt(cls_inst.opt)
        conf.update(module_conf)
        self.opt = _deserialize_config(conf)

        logging.info("Initialized script %s with options:\n%s", type(self).__name__, pprint.pformat(conf, sort_dicts=False))

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
        prof = profile.Profile()
        prof.enable()
        self.run()
        prof.disable()
        stats = pstats.Stats(prof).strip_dirs().sort_stats("cumtime")
        stats.print_stats(top)


class Module:
    def __init__(self, inp_args=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Build Config
        if inp_args is None:
            conf = self.build_config(self.args())
        else:
            conf = self.build_config(inp_args)
        self.opt = _deserialize_config(conf)

    @classmethod
    def args(cls):
        return {}

    @classmethod
    def build_config(cls, args):
        return args


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
            "class": "invoker.InvokerFormatter",
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


def _build_key(kname: str, key_prefix: str =None) -> str:
    return f"--{kname}" if key_prefix is None else f"--{key_prefix}.{kname}"


def _build_argparser(default_args, key_prefix=None, parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()
    for k, v in default_args.items():
        try:
            if type(v) == list:
                parser.add_argument(
                    _build_key(k, key_prefix),
                    type=type(v[0]) if len(v) > 0 else str,
                    nargs="+",
                    default=v
                )
            elif type(v) == bool:
                parser.add_argument(
                    _build_key(k, key_prefix),
                    action="store_true" if not v else "store_false",
                )
            else:
                parser.add_argument(
                    _build_key(k, key_prefix),
                    type=type(v),
                    default=v
                )
        except argparse.ArgumentError:
            logging.warn("Script defaults over-riding module arg %s.", k)
            pass
    return parser


def _parse_args_dict(args_dict: dict, parser: argparse.ArgumentParser, key_prefix: str =None) -> list[str]:
    cmd_args = []
    for k, v in args_dict.items():
        if type(v) == list:
            cmd_args.append(_build_key(k, key_prefix))
            for item in v:
                cmd_args.append(str(item))
        elif type(v) == bool:
            if v != parser.get_default(k):
                cmd_args.append(_build_key(k, key_prefix))
        else:
            cmd_args.append(_build_key(k, key_prefix))
            cmd_args.append(str(v))
    return vars(parser.parse_args(cmd_args))


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


def _to_camel_case(string):
    return "".join([token.capitalize() for token in string.split("_")])


def _to_underscore_case(string):
    return "_".join([token.lower() for token in re.findall("[A-Z][^A-Z]*", string)])
