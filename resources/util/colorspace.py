import logging

from util.arraylib import arraylib


class ColorspaceLibrary:
    _colorspaces = {}
    @classmethod
    def register(cls, name):
        if name in cls._colorspaces:
            return
        if name == "XYZ":
            cls._colorspaces[name] = XYZColorspace()
        elif name == "xyY":
            cls._colorspaces[name] = xyYColorspace()
        elif name == "CIELAB":
            cls._colorspaces[name] = CIELABColorspace()
        elif name in DisplayColorspace.STANDARDS:
            cls._colorspaces[name] = DisplayColorspace(name)
        else:
            raise ValueError("Unsupported colorspace: %s", name)

    @classmethod
    def convert(cls, image, input_colorspace: str, output_colorspace: str, dim_labels: str = 'BHWC'):
        logging.debug("Converting colorspace from %s to %s", input_colorspace, output_colorspace)
        if input_colorspace == output_colorspace:
            return image

        arraylib.use_like(image)
        cls.register(input_colorspace)
        cls.register(output_colorspace)

        image_xyz = cls._colorspaces[input_colorspace].to_xyz(image, dim_labels=dim_labels)
        output = cls._colorspaces[output_colorspace].from_xyz(image_xyz, dim_labels=dim_labels)
        return output


class Colorspace:
    NUM_CHANNELS = 3

    def __init__(self, name):
        self.name = name
    
    @staticmethod
    def get_channel_dim(img, dim_labels='BHWC'):
        assert "C" in dim_labels, "dim_labels must contain 'C'"
        channel_dim = dim_labels.index("C")
        assert img.shape[channel_dim] == Colorspace.NUM_CHANNELS, "Image must have %d channels" % Colorspace.NUM_CHANNELS
        return channel_dim

    def to_xyz(self, img_abc, *args, dim_labels='BHWC', **kwargs):
        raise NotImplementedError("to_xyz is not implemented for Colorspace")
    
    def from_xyz(self, img_xyz, *args, dim_labels='BHWC', **kwargs):
        raise NotImplementedError("from_xyz is not implemented for Colorspace")


class XYZColorspace(Colorspace):
    def __init__(self):
        super().__init__("XYZ")
    
    def to_xyz(self, img, dim_labels='BHWC'):
        return img

    def from_xyz(self, img, dim_labels='BHWC'):
        return img


class xyYColorspace(Colorspace):
    def __init__(self):
        super().__init__("xyY")
    
    def to_xyz(self, img_xyy, dim_labels='BHWC'):
        arraylib.use_like(img_xyy)
        channel_dim = self.get_channel_dim(img_xyy, dim_labels=dim_labels)
        x, y, Y = arraylib.split(img_xyy, self.NUM_CHANNELS, channel_dim)
        X = x * Y / y
        Z = (1 - x - y) * Y / y
        xyz = arraylib.concat([X, Y, Z], channel_dim)
        return xyz

    def from_xyz(self, img_xyz, dim_labels='BHWC'):
        arraylib.use_like(img_xyz)
        channel_dim = self.get_channel_dim(img_xyz, dim_labels=dim_labels)
        X, Y, Z = arraylib.split(img_xyz, self.NUM_CHANNELS, channel_dim)
        x = X / (X + Y + Z)
        y = Y / (X + Y + Z)
        xyY = arraylib.concat([x, y, Y], channel_dim)
        return xyY


class XYZLinearColorspace(Colorspace):
    def __init__(self, name, ABC2XYZ, XYZ2ABC):
        super().__init__(name)
        self.ABC2XYZ = ABC2XYZ
        self.XYZ2ABC = XYZ2ABC

    @staticmethod
    def _apply_linear_transform(img, transform_matrix, dim_labels='BHWC'):
        arraylib.use_like(img)
        channel_dim = Colorspace.get_channel_dim(img, dim_labels=dim_labels)

        # Split and reassemble to avoid costly permute operation
        inp1, inp2, inp3 = arraylib.split(img, Colorspace.NUM_CHANNELS, channel_dim)
        out1 = inp1 * transform_matrix[0, 0] + inp2 * transform_matrix[0, 1] + inp3 * transform_matrix[0, 2]
        out2 = inp1 * transform_matrix[1, 0] + inp2 * transform_matrix[1, 1] + inp3 * transform_matrix[1, 2]
        out3 = inp1 * transform_matrix[2, 0] + inp2 * transform_matrix[2, 1] + inp3 * transform_matrix[2, 2]

        out = arraylib.concat([out1, out2, out3], channel_dim)
        return out
    
    def to_xyz(self, img_abc, dim_labels='BHWC'):
        return XYZLinearColorspace._apply_linear_transform(img_abc, self.ABC2XYZ, dim_labels=dim_labels)
    
    def from_xyz(self, img_xyz, dim_labels='BHWC'):
        return XYZLinearColorspace._apply_linear_transform(img_xyz, self.XYZ2ABC, dim_labels=dim_labels)



NAMED_XYZ_COORDINATES = {
    "D65": [0.95047, 1.0, 1.08883],
}


class DisplayColorspace(XYZLinearColorspace):
    # Taken from https://github.com/gfxdisp/ColorVideoVDP
    STANDARDS = {
        "Adobe RGB (1998)": {"EOTF": "2.2", "whitepoint": "D65", "RGB2X": [0.5767309, 0.1855540, 0.1881852], "RGB2Y": [0.2973769, 0.6273491, 0.0752741], "RGB2Z": [0.0270343, 0.0706872, 0.9911085], "XYZ2R": [2.0413690, -0.5649464, -0.3446944], "XYZ2G": [-0.9692660, 1.8760108,  0.0415560], "XYZ2B": [0.0134474, -0.1183897, 1.0154096]},
        "Apple RGB":        {"EOTF": "1.8", "whitepoint": "D65", "RGB2X": [0.4497288, 0.3162486, 0.1844926], "RGB2Y": [0.2446525, 0.6720283, 0.0833192], "RGB2Z": [0.0251848, 0.1411824, 0.9224628], "XYZ2R": [2.9515373, -1.2894116, -0.4738445], "XYZ2G": [-1.0851093, 1.9908566,  0.0372026], "XYZ2B": [0.0854934, -0.2694964, 1.0912975]},
        "Best RGB":         {"EOTF": "2.2", "whitepoint": "D50", "RGB2X": [0.6326696, 0.2045558, 0.1269946], "RGB2Y": [0.2284569, 0.7373523, 0.0341908], "RGB2Z": [0.0000000, 0.0095142, 0.8156958], "XYZ2R": [1.7552599, -0.4836786, -0.2530000], "XYZ2G": [-0.5441336, 1.5068789,  0.0215528], "XYZ2B": [0.0063467, -0.0175761, 1.2256959]},
        "Beta RGB":         {"EOTF": "2.2", "whitepoint": "D50", "RGB2X": [0.6712537, 0.1745834, 0.1183829], "RGB2Y": [0.3032726, 0.6637861, 0.0329413], "RGB2Z": [0.0000000, 0.0407010, 0.7845090], "XYZ2R": [1.6832270, -0.4282363, -0.2360185], "XYZ2G": [-0.7710229, 1.7065571,  0.0446900], "XYZ2B": [0.0400013, -0.0885376, 1.2723640]},
        "Bruce RGB":        {"EOTF": "2.2", "whitepoint": "D65", "RGB2X": [0.4674162, 0.2944512, 0.1886026], "RGB2Y": [0.2410115, 0.6835475, 0.0754410], "RGB2Z": [0.0219101, 0.0736128, 0.9933071], "XYZ2R": [2.7454669, -1.1358136, -0.4350269], "XYZ2G": [-0.9692660, 1.8760108,  0.0415560], "XYZ2B": [0.0112723, -0.1139754, 1.0132541]},
        "CIE RGB":          {"EOTF": "2.2", "whitepoint": "E",   "RGB2X": [0.4887180, 0.3106803, 0.2006017], "RGB2Y": [0.1762044, 0.8129847, 0.0108109], "RGB2Z": [0.0000000, 0.0102048, 0.9897952], "XYZ2R": [2.3706743, -0.9000405, -0.4706338], "XYZ2G": [-0.5138850, 1.4253036,  0.0885814], "XYZ2B": [0.0052982, -0.0146949, 1.0093968]},
        "ColorMatch RGB":   {"EOTF": "1.8", "whitepoint": "D50", "RGB2X": [0.5093439, 0.3209071, 0.1339691], "RGB2Y": [0.2748840, 0.6581315, 0.0669845], "RGB2Z": [0.0242545, 0.1087821, 0.6921735], "XYZ2R": [2.6422874, -1.2234270, -0.3930143], "XYZ2G": [-1.1119763, 2.0590183,  0.0159614], "XYZ2B": [0.0821699, -0.2807254, 1.4559877]},
        "Don RGB 4":        {"EOTF": "2.2", "whitepoint": "D50", "RGB2X": [0.6457711, 0.1933511, 0.1250978], "RGB2Y": [0.2783496, 0.6879702, 0.0336802], "RGB2Z": [0.0037113, 0.0179861, 0.8035125], "XYZ2R": [1.7603902, -0.4881198, -0.2536126], "XYZ2G": [-0.7126288, 1.6527432,  0.0416715], "XYZ2B": [0.0078207, -0.0347411, 1.2447743]},
        "Ekta Space PS5":   {"EOTF": "2.2", "whitepoint": "D50", "RGB2X": [0.5938914, 0.2729801, 0.0973485], "RGB2Y": [0.2606286, 0.7349465, 0.0044249], "RGB2Z": [0.0000000, 0.0419969, 0.7832131], "XYZ2R": [2.0043819, -0.7304844, -0.2450052], "XYZ2G": [-0.7110285, 1.6202126,  0.0792227], "XYZ2B": [0.0381263, -0.0868780, 1.2725438]},
        "NTSC RGB":         {"EOTF": "2.2", "whitepoint": "C",   "RGB2X": [0.6068909, 0.1735011, 0.2003480], "RGB2Y": [0.2989164, 0.5865990, 0.1144845], "RGB2Z": [0.0000000, 0.0660957, 1.1162243], "XYZ2R": [1.9099961, -0.5324542, -0.2882091], "XYZ2G": [-0.9846663, 1.9991710, -0.0283082], "XYZ2B": [0.0583056, -0.1183781, 0.8975535]},
        "PAL/SECAM RGB":    {"EOTF": "2.2", "whitepoint": "D65", "RGB2X": [0.4306190, 0.3415419, 0.1783091], "RGB2Y": [0.2220379, 0.7066384, 0.0713236], "RGB2Z": [0.0201853, 0.1295504, 0.9390944], "XYZ2R": [3.0628971, -1.3931791, -0.4757517], "XYZ2G": [-0.9692660, 1.8760108,  0.0415560], "XYZ2B": [0.0678775, -0.2288548, 1.0693490]},
        "ProPhoto RGB":     {"EOTF": "1.8", "whitepoint": "D50", "RGB2X": [0.7976749, 0.1351917, 0.0313534], "RGB2Y": [0.2880402, 0.7118741, 0.0000857], "RGB2Z": [0.0000000, 0.0000000, 0.8252100], "XYZ2R": [1.3459433, -0.2556075, -0.0511118], "XYZ2G": [-0.5445989, 1.5081673,  0.0205351], "XYZ2B": [0.0000000,  0.0000000, 1.2118128]},
        "SMPTE-C RGB":      {"EOTF": "2.2", "whitepoint": "D65", "RGB2X": [0.3935891, 0.3652497, 0.1916313], "RGB2Y": [0.2124132, 0.7010437, 0.0865432], "RGB2Z": [0.0187423, 0.1119313, 0.9581563], "XYZ2R": [3.5053960, -1.7394894, -0.5439640], "XYZ2G": [-1.0690722, 1.9778245,  0.0351722], "XYZ2B": [0.0563200, -0.1970226, 1.0502026]},
        "sRGB":             {"EOTF": "sRGB","whitepoint": "D65", "RGB2X": [0.4124564, 0.3575761, 0.1804375], "RGB2Y": [0.2126729, 0.7151522, 0.0721750], "RGB2Z": [0.0193339, 0.1191920, 0.9503041], "XYZ2R": [3.2404542, -1.5371385, -0.4985314], "XYZ2G": [-0.9692660, 1.8760108,  0.0415560], "XYZ2B": [0.0556434, -0.2040259, 1.0572252]},
        "BT.709":           {"EOTF": "sRGB","whitepoint": "D65", "RGB2X": [0.4124564, 0.3575761, 0.1804375], "RGB2Y": [0.2126729, 0.7151522, 0.0721750], "RGB2Z": [0.0193339, 0.1191920, 0.9503041], "XYZ2R": [3.2404542, -1.5371385, -0.4985314], "XYZ2G": [-0.9692660, 1.8760108,  0.0415560], "XYZ2B": [0.0556434, -0.2040259, 1.0572252]},
        "BT.709-linear":    {"EOTF": "linear","whitepoint": "D65", "RGB2X": [0.4124564, 0.3575761, 0.1804375], "RGB2Y": [0.2126729, 0.7151522, 0.0721750], "RGB2Z": [0.0193339, 0.1191920, 0.9503041], "XYZ2R": [3.2404542, -1.5371385, -0.4985314], "XYZ2G": [-0.9692660, 1.8760108,  0.0415560], "XYZ2B": [0.0556434, -0.2040259, 1.0572252]},
        "Wide Gamut RGB":   {"EOTF": "2.2", "whitepoint": "D50", "RGB2X": [0.7161046, 0.1009296, 0.1471858], "RGB2Y": [0.2581874, 0.7249378, 0.0168748], "RGB2Z": [0.0000000, 0.0517813, 0.7734287], "XYZ2R": [1.4628067, -0.1840623, -0.2743606], "XYZ2G": [-0.5217933, 1.4472381,  0.0677227], "XYZ2B": [0.0349342, -0.0968930, 1.2884099]},
        "Display P3 Apple": {"EOTF": "sRGB","whitepoint": "D65", "RGB2X": [0.4866,0.2657,0.1982], "RGB2Y": [0.2290,0.6917,0.0793], "RGB2Z": [0,0.0451,1.0437], "XYZ2R": [3.2404542, -1.5371385, -0.4985314], "XYZ2G": [-0.9692660, 1.8760108,  0.0415560], "XYZ2B": [0.0556434, -0.2040259, 1.0572252]},
        "BT.2020-PQ":       {"EOTF": "PQ" , "whitepoint": "D65", "RGB2X": [0.6370, 0.1446, 0.1689], "RGB2Y": [0.2627, 0.6780, 0.0593], "RGB2Z": [0.0000, 0.0281, 1.0610]},
        "BT.2020-HLG":      {"EOTF": "HLG", "whitepoint": "D65", "RGB2X": [0.6370, 0.1446, 0.1689], "RGB2Y": [0.2627, 0.6780, 0.0593], "RGB2Z": [0.0000, 0.0281, 1.0610]},
        "BT.2020-linear":   {"EOTF": "linear" , "whitepoint": "D65", "RGB2X": [0.6370, 0.1446, 0.1689], "RGB2Y": [0.2627, 0.6780, 0.0593], "RGB2Z": [0.0000, 0.0281, 1.0610]},
    }

    def __init__(self, name):
        standard = self.STANDARDS[name]
        ABC2XYZ = arraylib.array([standard["RGB2X"], standard["RGB2Y"], standard["RGB2Z"]])
        XYZ2ABC = arraylib.array([standard["XYZ2R"], standard["XYZ2G"], standard["XYZ2B"]])
        self.eotf = standard["EOTF"]
        if standard["whitepoint"] not in NAMED_XYZ_COORDINATES:
            raise ValueError("Unsupported whitepoint: %s", standard["whitepoint"])
        self.whitepoint = standard["whitepoint"]
        super().__init__(name, ABC2XYZ, XYZ2ABC)


class CIELABColorspace(Colorspace):
    def __init__(self):
        super().__init__("CIELAB")

    def to_xyz(self, img_lab, dim_labels='BHWC', whitepoint="D65"):
        arraylib.use_like(img_lab)
        channel_dim = Colorspace.get_channel_dim(img_lab, dim_labels=dim_labels)

        # Split and reassemble to avoid costly permute operation
        l, a, b = arraylib.split(img_lab, Colorspace.NUM_CHANNELS, channel_dim)
        xn, yn, zn = NAMED_XYZ_COORDINATES[whitepoint]

        finv = lambda f: arraylib.where(f > 0.206893, f ** 3.0, (f - 16.0 / 116.0) / 7.787)
        fy = (l + 16.0) / 116.0
        x = xn * finv(fy + a / 500.0)
        y = yn * finv(fy)
        z = zn * finv(fy - b / 200.0)

        xyz = arraylib.concat([x, y, z], channel_dim)
        return xyz
    
    def from_xyz(self, img_xyz, dim_labels='BHWC', whitepoint="D65"):
        arraylib.use_like(img_xyz)
        channel_dim = Colorspace.get_channel_dim(img_xyz, dim_labels=dim_labels)

        # Split and reassemble to avoid costly permute operation
        x, y, z = arraylib.split(img_xyz, Colorspace.NUM_CHANNELS, channel_dim)
        xn, yn, zn = NAMED_XYZ_COORDINATES[whitepoint]
        f = lambda t: arraylib.where(t > 0.008856, t ** (1.0 / 3.0), 7.787 * t + 16.0 / 116.0)
        l = 116.0 * f(y / yn) - 16.0
        a = 500.0 * (f(x / xn) - f(y / yn))
        b = 200.0 * (f(y / yn) - f(z / zn))

        lab = arraylib.concat([l, a, b], channel_dim)
        return lab