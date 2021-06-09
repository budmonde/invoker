import importlib
import importlib.resources
import inspect


# Import all module classes
_PACKAGE_NAME = "".join([token.capitalize() for token in __package__.split("_")])
_CLASSES = {
    name: cls
    for list_of_classes in [
        inspect.getmembers(module, inspect.isclass)
        for module in [
            importlib.import_module(f"{__package__}.{fname.rstrip('.py')}")
            for fname in importlib.resources.contents(__package__)
            if fname.endswith(".py") and fname != "__init__.py"
        ]
    ]
    for name, cls in list_of_classes
    if name.endswith(_PACKAGE_NAME)
}


def _get_class(mode):
    cls_name = (
        "".join([token.capitalize() for token in mode.split("_")])
        + _PACKAGE_NAME
    )
    if cls_name not in _CLASSES.keys():
        raise TypeError(f"Invalid {__package__} mode: {cls_name}")
    return _CLASSES[cls_name]


def build(opt):
    mode = getattr(opt, f"{__package__}_mode")
    cls = _get_class(mode)
    return cls(getattr(opt, __package__))


def config(mode):
    cls = _get_class(mode)
    return cls.config()


def deps(mode):
    cls = _get_class(mode)
    return cls.deps()
