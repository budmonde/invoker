import imageio.v3 as iio
import numpy as np
import torch
import warnings


INFERRED_EOTF_FROM_DTYPE = {
    np.uint8: 'sRGB',
    np.float32: 'linear',
}

EOTF_TABLE = {
    ('sRGB', 'linear'): lambda x: x ** 2.2,
    ('linear', 'sRGB'): lambda x: x ** (1.0 / 2.2),
}

def convert_eotf(image, input_eotf, output_eotf):
    if input_eotf == output_eotf:
        return image
    if (input_eotf, output_eotf) not in EOTF_TABLE:
        raise ValueError("Unsupported EOTF conversion: %s -> %s" % (input_eotf, output_eotf))
    return EOTF_TABLE[(input_eotf, output_eotf)](image)

class Image:
    def __init__(self, image, dim_labels, eotf=None, label=None):
        self.image = image
        self.eotf = eotf
        self.dim_labels = dim_labels
        self.label = label

        if len(image.shape) != len(dim_labels):
            raise ValueError("Image shape %s does not match dim labels %s" % (image.shape, dim_labels))

        # Determine input EOTF (Electronic Optical Transfer Function)
        if eotf is None:
            if self.image.dtype in INFERRED_EOTF_FROM_DTYPE:
                self.eotf = INFERRED_EOTF_FROM_DTYPE[self.image.dtype]
            else:
                raise ValueError("Unsupported image dtype: %s" % self.image.dtype)
        else:
            self.eotf = eotf
    
    @classmethod
    def read(self, path, eotf=None):
        arr = iio.imread(path)
        if arr.dtype == np.uint8:
            arr = arr.astype(np.float32) / 255.0
        elif arr.dtype == np.float32:
            pass
        else:
            raise ValueError("Unsupported image dtype: %s" % self.image.dtype)
        return Image(arr, dim_labels="HWC", eotf=eotf, label=path)
    
    def get(self, eotf='linear', dim_labels='BHWC', dtype=np.float32, device='cpu'):
        output = convert_eotf(self.image, self.eotf, eotf)
        output = transpose_image(output, self.dim_labels, dim_labels)
        output = convert_dtype(output, dtype, device=device)
        return output
    
    def write(self, path, eotf='sRGB', format='png'):
        image = self.get(eotf=eotf, dim_labels="HWC", dtype=np.float32)
        image = np.nan_to_num(image, nan=0.0, posinf=1.0, neginf=0.0)
        if image.shape[-1] == 1:
            image = np.repeat(image, 3, axis=-1)
        image_u8 = (np.clip(image, 0, 1) * 255.0).astype(np.uint8)
        iio.imwrite(path, image_u8)


def transpose_image(image, input_dim_labels, output_dim_labels):
    if not isinstance(input_dim_labels, str) or not isinstance(output_dim_labels, str):
        raise ValueError("Input and output dim labels must be strings")

    valid_labels = set("BFHWC")
    if (set(input_dim_labels) - valid_labels) or (set(output_dim_labels) - valid_labels):
        raise ValueError("Unsupported dim labels. Only characters in 'BFHWC' are allowed.")
    if len(set(input_dim_labels)) != len(input_dim_labels):
        raise ValueError("Duplicate labels in input_dim_labels are not allowed.")
    if len(set(output_dim_labels)) != len(output_dim_labels):
        raise ValueError("Duplicate labels in output_dim_labels are not allowed.")
    if input_dim_labels == output_dim_labels:
        return image

    arr = image
    # Assign functions based on input type (arr is defined)
    is_numpy = isinstance(arr, np.ndarray)
    is_tensor = torch.is_tensor(arr)
    if not (is_numpy or is_tensor):
        raise ValueError("transpose_image expects a numpy.ndarray or torch.Tensor")
    move_axis_fn = np.moveaxis if is_numpy else torch.movedim
    expand_dims_fn = np.expand_dims if is_numpy else torch.unsqueeze
    squeeze_axis_fn = np.squeeze if is_numpy else torch.squeeze

    current_labels = list(input_dim_labels)

    # Delete singleton axes
    omitted = [lbl for lbl in input_dim_labels if lbl not in output_dim_labels]
    for lbl in list(omitted):
        src_idx = current_labels.index(lbl)
        if arr.shape[src_idx] != 1:
            raise ValueError(
                "Cannot drop non-unit axis '%s' of size %d when converting %s -> %s"
                % (lbl, arr.shape[src_idx], "".join(input_dim_labels), "".join(output_dim_labels))
            )
        arr = squeeze_axis_fn(arr, src_idx)
        del current_labels[src_idx]

    # Build correspondence: move/insert axes to match output order exactly
    for i, lbl in enumerate(output_dim_labels):
        if lbl in current_labels:
            src_idx = current_labels.index(lbl)
            if src_idx == i:
                continue
            arr = move_axis_fn(arr, src_idx, i)
            current_labels.insert(i, current_labels.pop(src_idx))
        else:
            # Insert a size-1 axis where needed (e.g., adding batch 'B')
            arr = expand_dims_fn(arr, axis=i)
            current_labels.insert(i, lbl)
    
    for lbl in zip(current_labels, output_dim_labels):
        if lbl[0] != lbl[1]:
            raise ValueError("Dimension labels do not match: %s -> %s" % (lbl[0], lbl[1]))
    
    return arr


def convert_dtype(image, dtype=np.float32, device='cpu'):
    """
    Convert between numpy ndarray and torch Tensor, with dtype and device handling.
    - dtype may be a numpy dtype (e.g., np.float32) or a torch dtype (e.g., torch.float32) or torch.FloatTensor.
    - device is used only when returning a torch Tensor.
    """
    numpy_to_torch = {
        np.float32: torch.float32,
        np.uint8: torch.uint8,
        np.int64: torch.int64,
        np.int32: torch.int32,
        np.float16: torch.float16,
        np.float64: torch.float64,
    }

    def as_numpy_dtype(dt):
        try:
            return np.dtype(dt)
        except Exception:
            return None

    def is_torch_dtype(dt):
        return isinstance(dt, torch.dtype) or (dt == torch.FloatTensor)

    if isinstance(image, np.ndarray):
        if is_torch_dtype(dtype):
            target_torch_dtype = torch.float32 if dtype == torch.FloatTensor else dtype
            return torch.from_numpy(image).to(dtype=target_torch_dtype, device=device)
        np_dtype = as_numpy_dtype(dtype)
        if np_dtype is not None:
            return image.astype(np_dtype, copy=False)
        raise ValueError("Unsupported dtype conversion (numpy input): %s" % dtype)

    if torch.is_tensor(image):
        if is_torch_dtype(dtype):
            target_torch_dtype = torch.float32 if dtype == torch.FloatTensor else dtype
            return image.to(dtype=target_torch_dtype, device=device)
        np_dtype = as_numpy_dtype(dtype)
        if np_dtype is not None:
            interm_torch_dtype = numpy_to_torch.get(np_dtype.type, None) or numpy_to_torch.get(np_dtype, None)
            tensor_cpu = image.detach().to('cpu')
            if interm_torch_dtype is not None:
                tensor_cpu = tensor_cpu.to(dtype=interm_torch_dtype)
            return tensor_cpu.contiguous().numpy().astype(np_dtype, copy=False)
        raise ValueError("Unsupported dtype conversion (torch input): %s" % dtype)

    raise ValueError("Unsupported input type for convert_dtype: %s" % type(image))


