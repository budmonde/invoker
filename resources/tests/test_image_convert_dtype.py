import os, sys

import numpy as np
import pytest
import torch

from util.image import convert_dtype


def make_np(shape, dtype=np.float32):
    size = int(np.prod(shape))
    return np.arange(size, dtype=dtype).reshape(shape)


def make_torch(shape, dtype=torch.float32, device='cpu'):
    size = int(np.prod(shape))
    return torch.arange(size, dtype=dtype, device=device).reshape(shape)


def test_numpy_to_numpy_float32():
    x = make_np((2, 3), dtype=np.float32)
    y = convert_dtype(x, dtype=np.float32)
    assert isinstance(y, np.ndarray)
    assert y.dtype == np.float32
    assert np.array_equal(x, y)


def test_numpy_to_numpy_uint8_cast():
    x = make_np((2, 3), dtype=np.float32)
    y = convert_dtype(x, dtype=np.uint8)
    assert isinstance(y, np.ndarray)
    assert y.dtype == np.uint8
    assert np.array_equal(y, x.astype(np.uint8))


def test_numpy_to_torch_float32_cpu():
    x = make_np((2, 3), dtype=np.float32)
    y = convert_dtype(x, dtype=torch.float32, device='cpu')
    assert torch.is_tensor(y)
    assert y.dtype == torch.float32
    assert y.device.type == 'cpu'
    assert np.array_equal(y.cpu().numpy(), x.astype(np.float32))


def test_numpy_to_torch_FloatTensor_alias():
    x = make_np((2, 3), dtype=np.float32)
    y = convert_dtype(x, dtype=torch.FloatTensor, device='cpu')
    assert torch.is_tensor(y)
    assert y.dtype == torch.float32
    assert y.device.type == 'cpu'
    assert np.array_equal(y.cpu().numpy(), x.astype(np.float32))


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_numpy_to_torch_cuda_dtype():
    x = make_np((2, 3), dtype=np.float32)
    y = convert_dtype(x, dtype=torch.float16, device='cuda')
    assert torch.is_tensor(y)
    assert y.dtype == torch.float16
    assert y.device.type == 'cuda'
    assert np.array_equal(y.float().cpu().numpy(), x.astype(np.float32))


def test_torch_to_torch_dtype_and_device_cpu():
    x = make_torch((2, 3), dtype=torch.float32, device='cpu')
    y = convert_dtype(x, dtype=torch.float16, device='cpu')
    assert torch.is_tensor(y)
    assert y.dtype == torch.float16
    assert y.device.type == 'cpu'
    assert np.array_equal(y.float().cpu().numpy(), x.cpu().numpy())


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_torch_to_torch_dtype_and_device_cuda():
    x = make_torch((2, 3), dtype=torch.float32, device='cpu')
    y = convert_dtype(x, dtype=torch.float32, device='cuda')
    assert torch.is_tensor(y)
    assert y.dtype == torch.float32
    assert y.device.type == 'cuda'
    assert np.array_equal(y.float().cpu().numpy(), x.cpu().numpy())


def test_torch_to_numpy_float32():
    x = make_torch((2, 3), dtype=torch.float32, device='cpu')
    y = convert_dtype(x, dtype=np.float32)
    assert isinstance(y, np.ndarray)
    assert y.dtype == np.float32
    assert np.array_equal(y, x.cpu().numpy())


def test_torch_to_numpy_uint8():
    x = make_torch((2, 3), dtype=torch.uint8, device='cpu')
    y = convert_dtype(x, dtype=np.uint8)
    assert isinstance(y, np.ndarray)
    assert y.dtype == np.uint8
    assert np.array_equal(y, x.cpu().numpy())


def test_invalid_dtype_raises_numpy_input():
    x = make_np((2, 3), dtype=np.float32)
    with pytest.raises(ValueError):
        _ = convert_dtype(x, dtype="not_a_dtype")


def test_invalid_dtype_raises_torch_input():
    x = make_torch((2, 3), dtype=torch.float32, device='cpu')
    with pytest.raises(ValueError):
        _ = convert_dtype(x, dtype="not_a_dtype")


