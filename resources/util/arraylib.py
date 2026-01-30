import numpy as np
import torch


class arraylib:
    _lib = None
    _lib_fn = {
        "numpy": {
            "array": np.array,
            "where": np.where,
            "split": lambda x, num_splits, axis: np.split(x, num_splits, axis=axis),
            "concat": lambda x, axis: np.concatenate(x, axis=axis),
        },
        "torch": {
            "array": torch.tensor,
            "where": torch.where,
            "split": lambda x, num_splits, axis: torch.split(x, num_splits, dim=axis),
            "concat": lambda x, axis: torch.cat(x, dim=axis),
        },
    }

    @classmethod
    def use(cls, lib="numpy"):
        if lib not in ["numpy", "torch"]:
            raise ValueError("Unsupported library: %s" % lib)
        cls._lib = lib

        for fn_name, fn in cls._lib_fn[lib].items():
            setattr(cls, fn_name, staticmethod(fn))

    @classmethod
    def use_like(cls, array):
        if isinstance(array, np.ndarray):
            cls.use("numpy")
        elif torch.is_tensor(array):
            cls.use("torch")
        else:
            raise ValueError("Unsupported array type: %s" % type(array))
