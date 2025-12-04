import numpy as np
import pytest
import torch

from util.image import EOTF


# --------------- Helpers ---------------
def make_array(lib, vals):
	if lib == 'numpy':
		return np.array(vals, dtype=np.float32)
	if lib == 'torch':
		return torch.tensor(vals, dtype=torch.float32)
	raise ValueError(lib)


def make_linspace(lib, start, end, steps):
	if lib == 'numpy':
		return np.linspace(start, end, steps, dtype=np.float32)
	if lib == 'torch':
		return torch.linspace(start, end, steps, dtype=torch.float32)
	raise ValueError(lib)


def assert_type_and_dtype(lib, x):
	if lib == 'numpy':
		assert isinstance(x, np.ndarray)
		assert x.dtype == np.float32
	else:
		assert torch.is_tensor(x)
		assert x.dtype == torch.float32


def allclose_equal(lib, a, b, atol=1e-6):
	if lib == 'numpy':
		assert np.allclose(a, b, atol=atol)
	else:
		assert torch.allclose(a, b, atol=atol, rtol=0)


def srgb_to_linear_ref(lib, x):
	if lib == 'numpy':
		th = 0.04045
		return np.where(x > th, ((x + 0.055) / 1.055) ** 2.4, x / 12.92).astype(x.dtype)
	else:
		th = x.new_tensor(0.04045)
		return torch.where(x > th, ((x + x.new_tensor(0.055)) / x.new_tensor(1.055)) ** x.new_tensor(2.4), x / x.new_tensor(12.92))


def linear_to_srgb_ref(lib, x):
	if lib == 'numpy':
		th = 0.0031308
		return np.where(x > th, 1.055 * x ** (1.0 / 2.4) - 0.055, 12.92 * x).astype(x.dtype)
	else:
		th = x.new_tensor(0.0031308)
		return torch.where(x > th, x.new_tensor(1.055) * x ** x.new_tensor(1.0 / 2.4) - x.new_tensor(0.055), x.new_tensor(12.92) * x)


# --------------- Tests ---------------
@pytest.mark.parametrize("lib", ["numpy", "torch"])
@pytest.mark.parametrize("vals", [
	[0.0, 0.020, 0.04045, 0.5, 1.0],
])
def test_srgb_to_linear(lib, vals):
	x = make_array(lib, vals)
	y = EOTF.convert(x, 'sRGB', 'linear')
	exp = srgb_to_linear_ref(lib, x)
	assert_type_and_dtype(lib, y)
	allclose_equal(lib, y, exp)


@pytest.mark.parametrize("lib", ["numpy", "torch"])
@pytest.mark.parametrize("vals", [
	[0.0, 0.001, 0.0031308, 0.2, 1.0],
])
def test_linear_to_srgb(lib, vals):
	x = make_array(lib, vals)
	y = EOTF.convert(x, 'linear', 'sRGB')
	exp = linear_to_srgb_ref(lib, x)
	assert_type_and_dtype(lib, y)
	allclose_equal(lib, y, exp)


@pytest.mark.parametrize("lib", ["numpy", "torch"])
def test_linear_identity(lib):
	x = make_linspace(lib, 0, 1, 9)
	y = EOTF.convert(x, 'linear', 'linear')
	if lib == 'numpy':
		assert np.array_equal(y, x)
	else:
		assert torch.equal(y, x)


@pytest.mark.parametrize("lib", ["numpy", "torch"])
@pytest.mark.parametrize("gamma", [1.8, 2.2, 2.4])
def test_gamma_round_trip(lib, gamma):
	x = make_linspace(lib, 0, 1, 17)
	y = EOTF.convert(x, gamma, 'linear')          # decode gamma
	z = EOTF.convert(y, 'linear', gamma)          # encode gamma
	allclose_equal(lib, z, x)


@pytest.mark.parametrize("lib", ["numpy", "torch"])
def test_invalid_encoding_raises(lib):
	x = make_array(lib, [0.1, 0.5])
	with pytest.raises(ValueError):
		_ = EOTF.convert(x, 'not_an_encoding', 'linear')
	with pytest.raises(ValueError):
		_ = EOTF.convert(x, 'linear', 'not_an_encoding')

