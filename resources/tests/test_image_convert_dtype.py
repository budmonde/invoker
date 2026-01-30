import numpy as np
import pytest
import torch

from util.image import convert_dtype

from .helpers import assert_type_and_dtype, make_array_from_shape


@pytest.mark.parametrize("target_dtype", [np.float32, np.uint8])
def test_numpy_to_numpy(target_dtype, shape=(2, 3)):
    x = make_array_from_shape("numpy", shape, dtype=np.float32)
    y = convert_dtype(x, dtype=target_dtype)
    assert_type_and_dtype("numpy", y, target_dtype)
    exp = x if target_dtype == np.float32 else x.astype(np.uint8)
    assert np.array_equal(y, exp)


@pytest.mark.parametrize("target_dtype", [torch.float32, torch.FloatTensor])
def test_numpy_to_torch_cpu(target_dtype, shape=(2, 3)):
    x = make_array_from_shape("numpy", shape, dtype=np.float32)
    y = convert_dtype(x, dtype=target_dtype, device="cpu")
    assert torch.is_tensor(y)
    assert y.device.type == "cpu"
    assert y.dtype == (
        torch.float32 if target_dtype == torch.FloatTensor else target_dtype
    )
    assert np.array_equal(y.cpu().numpy(), x.astype(np.float32))


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_numpy_to_torch_cuda(shape=(2, 3)):
    x = make_array_from_shape("numpy", shape, dtype=np.float32)
    y = convert_dtype(x, dtype=torch.float16, device="cuda")
    assert torch.is_tensor(y)
    assert y.dtype == torch.float16
    assert y.device.type == "cuda"
    assert np.array_equal(y.float().cpu().numpy(), x.astype(np.float32))


@pytest.mark.parametrize("src_dtype,target_dtype", [(torch.float32, torch.float16)])
def test_torch_to_torch_cpu(src_dtype, target_dtype, shape=(2, 3)):
    x = make_array_from_shape("torch", shape, dtype=src_dtype, device="cpu")
    y = convert_dtype(x, dtype=target_dtype, device="cpu")
    assert torch.is_tensor(y)
    assert y.dtype == target_dtype
    assert y.device.type == "cpu"
    assert np.array_equal(y.float().cpu().numpy(), x.cpu().numpy())


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_torch_to_torch_cuda(shape=(2, 3)):
    x = make_array_from_shape("torch", shape, dtype=torch.float32, device="cpu")
    y = convert_dtype(x, dtype=torch.float32, device="cuda")
    assert torch.is_tensor(y)
    assert y.dtype == torch.float32
    assert y.device.type == "cuda"
    assert np.array_equal(y.float().cpu().numpy(), x.cpu().numpy())


@pytest.mark.parametrize("target_dtype", [np.float32, np.uint8])
def test_torch_to_numpy(target_dtype, shape=(2, 3)):
    x = make_array_from_shape(
        "torch",
        shape,
        dtype=(torch.float32 if target_dtype == np.float32 else torch.uint8),
        device="cpu",
    )
    y = convert_dtype(x, dtype=target_dtype)
    assert isinstance(y, np.ndarray)
    assert y.dtype == np.dtype(target_dtype)
    assert np.array_equal(y, x.cpu().numpy().astype(target_dtype, copy=False))


@pytest.mark.parametrize("lib", ["numpy", "torch"])
def test_invalid_dtype_raises(lib):
    x = make_array_from_shape(
        lib, (2, 3), dtype=(np.float32 if lib == "numpy" else torch.float32)
    )
    with pytest.raises(ValueError):
        _ = convert_dtype(x, dtype="not_a_dtype")


def test_unsupported_input_type_raises():
    # Input that is neither numpy.ndarray nor torch.Tensor should raise
    with pytest.raises(ValueError):
        _ = convert_dtype("not-an-array", dtype=np.float32)
