import os, sys

import numpy as np
import pytest
import torch

from resources.image import transpose_image


def make_np(shape):
    size = int(np.prod(shape))
    arr = np.arange(size, dtype=np.float32).reshape(shape)
    return arr


def make_torch(shape):
    size = int(np.prod(shape))
    arr = torch.arange(size, dtype=torch.float32).reshape(shape)
    return arr


# ----------------------------
# Identity and basic reorders
# ----------------------------
@pytest.mark.parametrize("labels,shape", [
    ("HWC", (5, 7, 3)),
    ("CHW", (3, 5, 7)),
    ("BHWC", (1, 5, 7, 3)),
    ("BCHW", (1, 3, 5, 7)),
])
def test_identity_numpy(labels, shape):
    x = make_np(shape)
    y = transpose_image(x, labels, labels)
    assert y.shape == x.shape
    assert np.array_equal(y, x)


@pytest.mark.parametrize("labels,shape", [
    ("HWC", (5, 7, 3)),
    ("CHW", (3, 5, 7)),
    ("BHWC", (1, 5, 7, 3)),
    ("BCHW", (1, 3, 5, 7)),
])
def test_identity_torch(labels, shape):
    x = make_torch(shape)
    y = transpose_image(x, labels, labels)
    assert tuple(y.shape) == tuple(x.shape)
    assert torch.equal(y, x)


@pytest.mark.parametrize("inp,out,shape,expected_perm", [
    # HWC -> CHW
    ("HWC", "CHW", (5, 7, 3), (2, 0, 1)),
    # BHWC -> BCHW
    ("BHWC", "BCHW", (1, 5, 7, 3), (0, 3, 1, 2)),
])
def test_reorder_numpy(inp, out, shape, expected_perm):
    x = make_np(shape)
    y = transpose_image(x, inp, out)
    assert y.shape == tuple(shape[i] for i in expected_perm)
    assert np.array_equal(y, np.transpose(x, expected_perm))


@pytest.mark.parametrize("inp,out,shape,expected_perm", [
    ("HWC", "CHW", (5, 7, 3), (2, 0, 1)),
    ("BHWC", "BCHW", (1, 5, 7, 3), (0, 3, 1, 2)),
])
def test_reorder_torch(inp, out, shape, expected_perm):
    x = make_torch(shape)
    y = transpose_image(x, inp, out)
    assert tuple(y.shape) == tuple(shape[i] for i in expected_perm)
    assert torch.equal(y, x.permute(*expected_perm))


# ----------------------------
# Insertion and squeezing axes
# ----------------------------
def test_insert_batch_numpy():
    x = make_np((5, 7, 3))  # HWC
    y = transpose_image(x, "HWC", "BHWC")
    assert y.shape == (1, 5, 7, 3)
    assert np.array_equal(y[0], x)


def test_insert_batch_torch():
    x = make_torch((5, 7, 3))  # HWC
    y = transpose_image(x, "HWC", "BHWC")
    assert tuple(y.shape) == (1, 5, 7, 3)
    assert torch.equal(y[0], x)


def test_squeeze_batch_numpy():
    x = make_np((1, 5, 7, 3))  # BHWC
    y = transpose_image(x, "BHWC", "HWC")
    assert y.shape == (5, 7, 3)
    assert np.array_equal(y, x[0])


def test_squeeze_batch_torch():
    x = make_torch((1, 5, 7, 3))  # BHWC
    y = transpose_image(x, "BHWC", "HWC")
    assert tuple(y.shape) == (5, 7, 3)
    assert torch.equal(y, x[0])


# ----------------------------
# Error cases
# ----------------------------
def test_drop_non_singleton_raises_numpy():
    x = make_np((2, 5, 7, 3))  # BHWC with B=2
    with pytest.raises(ValueError):
        _ = transpose_image(x, "BHWC", "HWC")  # dropping non-singleton B


def test_drop_non_singleton_raises_torch():
    x = make_torch((2, 5, 7, 3))  # BHWC with B=2
    with pytest.raises(ValueError):
        _ = transpose_image(x, "BHWC", "HWC")


def test_duplicate_labels_raise():
    x = make_np((5, 7, 3))
    with pytest.raises(ValueError):
        _ = transpose_image(x, "HHW", "HWC")
    with pytest.raises(ValueError):
        _ = transpose_image(x, "HWC", "HWW")


def test_unsupported_labels_raise():
    x = make_np((5, 7, 3))
    with pytest.raises(ValueError):
        _ = transpose_image(x, "HXW", "HWC")
    with pytest.raises(ValueError):
        _ = transpose_image(x, "HWC", "HWX")


# ----------------------------
# 'F' axis handling (frames)
# ----------------------------
def test_insert_F_axis_numpy():
    x = make_np((5, 7, 3))  # HWC
    y = transpose_image(x, "HWC", "FHWC")
    assert y.shape == (1, 5, 7, 3)
    assert np.array_equal(y[0], x)


def test_reorder_with_F_torch():
    x = make_torch((1, 3, 5, 7))  # BCHW
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
    x = make_np((H, W, C))
    y = transpose_image(x, "HWC", "BCHW")
    assert y.shape == (1, C, H, W)
    assert np.array_equal(y, np.transpose(x[None, ...], (0, 3, 1, 2)))


def test_complex_torch():
    # Start BHWC -> target CHW (drop B=1 and move)
    B, H, W, C = 1, 4, 6, 3
    x = make_torch((B, H, W, C))
    y = transpose_image(x, "BHWC", "CHW")
    assert tuple(y.shape) == (C, H, W)
    assert torch.equal(y, x[0].permute(2, 0, 1))


