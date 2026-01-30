import logging

import imageio.v3 as iio
import numpy as np
import torch


class Image:
    @classmethod
    def read(self, path, encoding=None, colorspace="sRGB"):
        arr = iio.imread(path)
        dtype = arr.dtype.type

        if encoding is None:
            encoding = self.infer_encoding(dtype, colorspace)

        if dtype == np.uint8:
            arr = arr.astype(np.float32) / 255.0
        elif dtype == np.float32:
            pass
        else:
            raise ValueError("Unsupported image dtype: %s", dtype)

        return Image(
            arr, dim_labels="HWC", encoding=encoding, colorspace=colorspace, label=path
        )

    @classmethod
    def infer_encoding(cls, dtype, colorspace):
        INFERRED_ENCODING_FROM_DTYPE = {
            np.uint8: "sRGB",
            np.float32: "linear",
        }
        if colorspace == "sRGB":
            encoding = INFERRED_ENCODING_FROM_DTYPE[dtype]
            logging.info("Inferring encoding from dtype %s as %s", dtype, encoding)
        else:
            logging.info(
                "Importing Colorspace module for non-sRGB (%s) colorspace", colorspace
            )
            from util.colorspace import Colorspaces

            encoding = Colorspaces.get_eotf(colorspace)
            logging.info(
                "Inferring encoding from colorspace %s as %s", colorspace, encoding
            )
        return encoding

    def __init__(
        self, image, dim_labels, encoding="linear", colorspace=None, label=None
    ):
        if image is None:
            raise ValueError("Image array must be provided")
        if dim_labels is None:
            raise ValueError("Explicit dim_labels must be provided")
        dim_labels = validate_dim_labels(dim_labels, image.shape)

        if colorspace is not None:
            channel_dim = list(dim_labels).index("C")
            num_channels = image.shape[channel_dim]
            if colorspace is not None and num_channels != 3:
                raise ValueError(
                    "Image in %s colorspace has %d channels, expected 3",
                    colorspace,
                    num_channels,
                )

        self.image = image
        self.encoding = encoding
        self.colorspace = colorspace
        self.dim_labels = dim_labels
        self.label = label

    def get(
        self,
        dim_labels="BHWC",
        encoding="linear",
        colorspace=None,
        dtype=np.float32,
        device="cpu",
    ):
        output = self.image
        if (
            self.colorspace is None
            or colorspace is None
            or self.colorspace == colorspace
        ):
            output = EOTF.convert(output, self.encoding, encoding)
        else:
            logging.info(
                "Importing ColorspaceLibrary for (%s -> %s) colorspace conversion",
                self.colorspace,
                colorspace,
            )
            from util.colorspace import ColorspaceLibrary

            output = EOTF.convert(output, self.encoding, "linear")
            output = ColorspaceLibrary.convert(
                output, self.colorspace, colorspace, dim_labels=self.dim_labels
            )
            output = EOTF.convert(output, "linear", encoding)

        output = transpose_image(output, self.dim_labels, dim_labels)
        output = convert_dtype(output, dtype, device=device)
        return output

    def write(self, path, encoding="sRGB", colorspace="sRGB", fmt="png"):
        image = self.get(
            encoding=encoding, colorspace=colorspace, dim_labels="HWC", dtype=np.float32
        )
        if fmt == "png":
            image = np.nan_to_num(image, nan=0.0, posinf=1.0, neginf=0.0)
            if image.shape[-1] == 1:
                image = np.repeat(image, 3, axis=-1)
            image_u8 = (np.clip(image, 0, 1) * 255.0).astype(np.uint8)
            iio.imwrite(path, image_u8)
        else:
            raise ValueError("Unsupported format: %s", fmt)


class EOTF:
    eotfs = {
        ("linear", "linear"): lambda x: x,
        ("sRGB", "linear"): lambda x: (x > 0.04045) * ((x + 0.055) / 1.055) ** 2.4
        + (x <= 0.04045) * (x / 12.92),
        ("linear", "sRGB"): lambda x: (x > 0.0031308)
        * (1.055 * x ** (1.0 / 2.4) - 0.055)
        + (x <= 0.0031308) * (12.92 * x),
    }

    @classmethod
    def convert(cls, image, input_encoding, output_encoding):
        logging.debug(
            "Converting encoding from %s to %s", input_encoding, output_encoding
        )
        if input_encoding == output_encoding:
            return image

        cls._ensure_gamma_coders(input_encoding)
        cls._ensure_gamma_coders(output_encoding)

        to_linear_fn = cls.eotfs.get((input_encoding, "linear"))
        if to_linear_fn is None:
            raise ValueError("Unsupported EOTF: %s -> linear", input_encoding)
        image_linear = to_linear_fn(image)

        from_linear_fn = cls.eotfs.get(("linear", output_encoding))
        if from_linear_fn is None:
            raise ValueError("Unsupported EOTF: linear -> %s", output_encoding)
        output = from_linear_fn(image_linear)
        return output

    @classmethod
    def _ensure_gamma_coders(cls, node):
        if not isinstance(node, (int, float)):
            return
        gamma = float(node)
        if (gamma, "linear") not in cls.eotfs:
            cls.eotfs[(gamma, "linear")] = lambda x: x**gamma
        if ("linear", gamma) not in cls.eotfs:
            cls.eotfs[("linear", gamma)] = lambda x: x ** (1.0 / gamma)


def validate_dim_labels(dim_labels, shape=None):
    if not isinstance(dim_labels, str):
        raise ValueError("Dim labels must be a string, got %s", type(dim_labels))
    if shape is not None and len(shape) != len(dim_labels):
        raise ValueError("Shape %s does not match dim labels %s", shape, dim_labels)

    valid_labels = set("BFHWC")
    if set(dim_labels) - valid_labels:
        raise ValueError(
            "Unsupported dim labels. Only characters in 'BFHWC' are allowed."
        )
    if len(set(dim_labels)) != len(dim_labels):
        raise ValueError("Duplicate labels in dim_labels are not allowed.")

    return dim_labels


def transpose_image(image, input_dim_labels, output_dim_labels):
    input_dim_labels = validate_dim_labels(input_dim_labels, image.shape)
    output_dim_labels = validate_dim_labels(output_dim_labels)
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
                "Cannot drop non-unit axis '%s' of size %d when converting %s -> %s",
                lbl,
                arr.shape[src_idx],
                "".join(input_dim_labels),
                "".join(output_dim_labels),
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

    return arr


def convert_dtype(image, dtype=np.float32, device="cpu"):
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
        raise ValueError("Unsupported dtype conversion (numpy input): %s", dtype)

    if torch.is_tensor(image):
        if is_torch_dtype(dtype):
            target_torch_dtype = torch.float32 if dtype == torch.FloatTensor else dtype
            return image.to(dtype=target_torch_dtype, device=device)
        np_dtype = as_numpy_dtype(dtype)
        if np_dtype is not None:
            interm_torch_dtype = numpy_to_torch.get(
                np_dtype.type, None
            ) or numpy_to_torch.get(np_dtype, None)
            tensor_cpu = image.detach().to("cpu")
            if interm_torch_dtype is not None:
                tensor_cpu = tensor_cpu.to(dtype=interm_torch_dtype)
            return tensor_cpu.contiguous().numpy().astype(np_dtype, copy=False)
        raise ValueError("Unsupported dtype conversion (torch input): %s", dtype)

    raise ValueError("Unsupported input type for convert_dtype: %s", type(image))
