import argparse
import copy
import importlib
import logging
import logging.config
import yaml
from pathlib import Path


# Add script configurations to project.yml. E.g.
# modules:
# - data_loader
# - model
# scripts:
#   experiment:
#     - data_loader
#     - model
#     - sampler
#   evaluation:
#     - model
#     - sampler
mode_to_config = yaml.load(open("project.yml"), Loader=yaml.FullLoader)


def build(mode):
    # Load Script Config
    script_module = importlib.import_module(mode)
    script_args = script_module.args()
    # TODO: Add argparser here
    script_config = script_module.build_config(script_args)
    logger_dict = {
        "version": 1,
        "formatters": {
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            }
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console"]
        }
    }
    logging.config.dictConfig(logger_dict)

    # Load Module Config
    for module in mode_to_config["scripts"][mode]:
        module_mode = script_config[f"{module}_mode"]
        module_config = _load_module_config(module, module_mode)
        module_deps = _load_module_deps(module, module_mode)
        for dep in module_deps:
            dep_path = Path(script_config[f"{dep}_path"]) / "config.json"
            module_config[dep] = _load_dep_config(dep, dep_path)
        script_config[module] = module_config

    # Save Config
    if "path" in script_config:
        save_root = Path(script_config["path"])
        save_root.mkdir(parents=True, exist_ok=True)
        json.dump(script_config, open(save_root / "config.json", "w"))

    return _deserialize_config(script_config)


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


def _load_module_config(module, module_mode):
    return importlib.import_module(module).config(module_mode)


def _load_module_deps(module, module_mode):
    return importlib.import_module(module).deps(module_mode)


def _load_dep_config(dep, dep_path):
    return json.load(open(dep_path))
