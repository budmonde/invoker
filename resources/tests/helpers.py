import numpy as np
import torch


def make_array(lib, vals):
    # Create array/tensor directly from explicit values using float32
    if lib == "numpy":
        return np.array(vals, dtype=np.float32)
    if lib == "torch":
        return torch.tensor(vals, dtype=torch.float32)
    raise ValueError(lib)


def make_array_from_shape(lib, shape, dtype=np.float32, device="cpu"):
    # Create array/tensor by arange and reshape to shape
    size = int(np.prod(shape))
    if lib == "numpy":
        # dtype must be a numpy dtype, not a torch dtype
        if isinstance(dtype, torch.dtype) or dtype == torch.FloatTensor:
            raise ValueError(
                "Mismatched library usage in make_array_from_shape: numpy lib with torch dtype is unsupported"
            )
        return np.arange(size, dtype=np.dtype(dtype)).reshape(shape)
    if lib == "torch":
        # dtype must be a torch dtype (or FloatTensor alias), not a numpy dtype
        if not (isinstance(dtype, torch.dtype) or dtype == torch.FloatTensor):
            raise ValueError(
                "Mismatched library usage in make_array_from_shape: torch lib with numpy dtype is unsupported"
            )
        td = torch.float32 if dtype == torch.FloatTensor else dtype
        return torch.arange(size, dtype=td, device=device).reshape(shape)
    raise ValueError(lib)


def make_linspace(lib, start, end, steps):
    if lib == "numpy":
        return np.linspace(start, end, steps, dtype=np.float32)
    if lib == "torch":
        return torch.linspace(start, end, steps, dtype=torch.float32)
    raise ValueError(lib)


def assert_type_and_dtype(lib, x, expected_dtype):
    if lib == "numpy":
        assert isinstance(x, np.ndarray)
        assert x.dtype == np.dtype(expected_dtype)
    else:
        assert torch.is_tensor(x)
        exp = torch.float32 if expected_dtype == torch.FloatTensor else expected_dtype
        assert x.dtype == exp


def allclose_equal(lib, a, b, atol=1e-6):
    if lib == "numpy":
        assert np.allclose(a, b, atol=atol)
    else:
        assert torch.allclose(a, b, atol=atol, rtol=0)


def to_numpy(x):
    return x if isinstance(x, np.ndarray) else x.detach().to("cpu").contiguous().numpy()


def srgb_to_linear_ref(lib, x):
    if lib == "numpy":
        th = 0.04045
        return np.where(x > th, ((x + 0.055) / 1.055) ** 2.4, x / 12.92).astype(x.dtype)
    else:
        th = x.new_tensor(0.04045)
        return torch.where(
            x > th,
            ((x + x.new_tensor(0.055)) / x.new_tensor(1.055)) ** x.new_tensor(2.4),
            x / x.new_tensor(12.92),
        )


def linear_to_srgb_ref(lib, x):
    if lib == "numpy":
        th = 0.0031308
        return np.where(x > th, 1.055 * x ** (1.0 / 2.4) - 0.055, 12.92 * x).astype(
            x.dtype
        )
    else:
        th = x.new_tensor(0.0031308)
        return torch.where(
            x > th,
            x.new_tensor(1.055) * x ** x.new_tensor(1.0 / 2.4) - x.new_tensor(0.055),
            x.new_tensor(12.92) * x,
        )
