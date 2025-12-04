import numpy as np
import pytest
import torch

from util.image import EOTF
from .helpers import (
	make_array,
	make_linspace,
	assert_type_and_dtype,
	allclose_equal,
	srgb_to_linear_ref,
	linear_to_srgb_ref,
)


@pytest.mark.parametrize("lib", ["numpy", "torch"])
@pytest.mark.parametrize("vals", [
	[0.0, 0.020, 0.04045, 0.5, 1.0],
])
def test_srgb_to_linear(lib, vals):
	x = make_array(lib, vals)
	y = EOTF.convert(x, 'sRGB', 'linear')
	exp = srgb_to_linear_ref(lib, x)
	assert_type_and_dtype(lib, y, x.dtype)
	allclose_equal(lib, y, exp)


@pytest.mark.parametrize("lib", ["numpy", "torch"])
@pytest.mark.parametrize("vals", [
	[0.0, 0.001, 0.0031308, 0.2, 1.0],
])
def test_linear_to_srgb(lib, vals):
	x = make_array(lib, vals)
	y = EOTF.convert(x, 'linear', 'sRGB')
	exp = linear_to_srgb_ref(lib, x)
	assert_type_and_dtype(lib, y, x.dtype)
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