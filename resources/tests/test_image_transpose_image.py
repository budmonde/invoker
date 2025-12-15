import os, sys

import numpy as np
import pytest
import torch

from util.image import transpose_image
from .helpers import make_array_from_shape


# ----------------------------
# Identity and basic reorders
# ----------------------------
@pytest.mark.parametrize("lib", ["numpy", "torch"])
@pytest.mark.parametrize("labels,shape", [
    ("HWC", (5, 7, 3)),
    ("CHW", (3, 5, 7)),
    ("BHWC", (1, 5, 7, 3)),
    ("BCHW", (1, 3, 5, 7)),
])
def test_identity(lib, labels, shape):
    dtype = np.float32 if lib == "numpy" else torch.float32
    x = make_array_from_shape(lib, shape, dtype=dtype)
    y = transpose_image(x, labels, labels)
    if lib == "numpy":
        assert y.shape == x.shape
        assert np.array_equal(y, x)
    else:
        assert tuple(y.shape) == tuple(x.shape)
        assert torch.equal(y, x)


@pytest.mark.parametrize("lib", ["numpy", "torch"])
@pytest.mark.parametrize("inp,out,shape,expected_perm", [
    ("HWC", "CHW", (5, 7, 3), (2, 0, 1)),
    ("BHWC", "BCHW", (1, 5, 7, 3), (0, 3, 1, 2)),
])
def test_reorder(lib, inp, out, shape, expected_perm):
    dtype = np.float32 if lib == "numpy" else torch.float32
    x = make_array_from_shape(lib, shape, dtype=dtype)
    y = transpose_image(x, inp, out)
    if lib == "numpy":
        assert y.shape == tuple(shape[i] for i in expected_perm)
        assert np.array_equal(y, np.transpose(x, expected_perm))
    else:
        assert tuple(y.shape) == tuple(shape[i] for i in expected_perm)
        assert torch.equal(y, x.permute(*expected_perm))


# ----------------------------
# Insertion and squeezing axes
# ----------------------------
@pytest.mark.parametrize("lib", ["numpy", "torch"])
def test_insert_batch(lib):
    dtype = np.float32 if lib == "numpy" else torch.float32
    x = make_array_from_shape(lib, (5, 7, 3), dtype=dtype)  # HWC
    y = transpose_image(x, "HWC", "BHWC")
    if lib == "numpy":
        assert y.shape == (1, 5, 7, 3)
        assert np.array_equal(y[0], x)
    else:
        assert tuple(y.shape) == (1, 5, 7, 3)
        assert torch.equal(y[0], x)


@pytest.mark.parametrize("lib", ["numpy", "torch"])
def test_squeeze_batch(lib):
    dtype = np.float32 if lib == "numpy" else torch.float32
    x = make_array_from_shape(lib, (1, 5, 7, 3), dtype=dtype)  # BHWC
    y = transpose_image(x, "BHWC", "HWC")
    if lib == "numpy":
        assert y.shape == (5, 7, 3)
        assert np.array_equal(y, x[0])
    else:
        assert tuple(y.shape) == (5, 7, 3)
        assert torch.equal(y, x[0])


# ----------------------------
# Error cases
# ----------------------------
@pytest.mark.parametrize("lib", ["numpy", "torch"])
def test_drop_non_singleton_raises(lib):
    dtype = np.float32 if lib == "numpy" else torch.float32
    x = make_array_from_shape(lib, (2, 5, 7, 3), dtype=dtype)  # BHWC with B=2
    with pytest.raises(ValueError):
        _ = transpose_image(x, "BHWC", "HWC")  # dropping non-singleton B


@pytest.mark.parametrize("lib", ["numpy", "torch"])
def test_duplicate_labels_raise(lib):
    dtype = np.float32 if lib == "numpy" else torch.float32
    x = make_array_from_shape(lib, (5, 7, 3), dtype=dtype)
    with pytest.raises(ValueError):
        _ = transpose_image(x, "HHW", "HWC")
    with pytest.raises(ValueError):
        _ = transpose_image(x, "HWC", "HWW")


@pytest.mark.parametrize("lib", ["numpy", "torch"])
def test_unsupported_labels_raise(lib):
    dtype = np.float32 if lib == "numpy" else torch.float32
    x = make_array_from_shape(lib, (5, 7, 3), dtype=dtype)
    with pytest.raises(ValueError):
        _ = transpose_image(x, "HXW", "HWC")
    with pytest.raises(ValueError):
        _ = transpose_image(x, "HWC", "HWX")


# ----------------------------
# 'F' axis handling (frames)
# ----------------------------
def test_insert_F_axis_numpy():
    x = make_array_from_shape("numpy", (5, 7, 3), dtype=np.float32)  # HWC
    y = transpose_image(x, "HWC", "FHWC")
    assert y.shape == (1, 5, 7, 3)
    assert np.array_equal(y[0], x)


def test_reorder_with_F_torch():
    x = make_array_from_shape("torch", (1, 3, 5, 7), dtype=torch.float32)  # BCHW
    # Target: FBCHW -> insert F in front and keep order
    y = transpose_image(x, "BCHW", "FBCHW")
    assert tuple(y.shape) == (1, 1, 3, 5, 7)
    assert torch.equal(y[0], x)


# ----------------------------
# Mixed complex transform
# ----------------------------
def test_complex_numpy():
    # Start HWC -> target BCHW (insert B, move C)
    H, W, C = 4, 6, 3
    x = make_array_from_shape("numpy", (H, W, C), dtype=np.float32)
    y = transpose_image(x, "HWC", "BCHW")
    assert y.shape == (1, C, H, W)
    assert np.array_equal(y, np.transpose(x[None, ...], (0, 3, 1, 2)))


def test_complex_torch():
    # Start BHWC -> target CHW (drop B=1 and move)
    B, H, W, C = 1, 4, 6, 3
    x = make_array_from_shape("torch", (B, H, W, C), dtype=torch.float32)
    y = transpose_image(x, "BHWC", "CHW")
    assert tuple(y.shape) == (C, H, W)
    assert torch.equal(y, x[0].permute(2, 0, 1))


@pytest.mark.parametrize("lib", ["numpy", "torch"])
def test_non_string_dim_labels_raise(lib):
    dtype = np.float32 if lib == "numpy" else torch.float32
    x = make_array_from_shape(lib, (5, 7, 3), dtype=dtype)
    with pytest.raises(ValueError):
        _ = transpose_image(x, ["H", "W", "C"], "HWC")
    with pytest.raises(ValueError):
        _ = transpose_image(x, "HWC", None)


def test_non_array_input_raises():
    with pytest.raises(AttributeError):
        _ = transpose_image("not-an-array", "HWC", "CHW")