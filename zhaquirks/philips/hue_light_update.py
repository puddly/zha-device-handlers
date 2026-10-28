"""Philips Hue combined light update format, used by cluster 0xFC03.

Reverse engineered by Bifrost: https://github.com/duvholt/bifrost/blob/master/doc/hue-zigbee-format.md
"""

from __future__ import annotations

from typing import Final, Self

import zigpy.types as t

# Gradient color coordinates are scaled to the bounds of the wide color gamut
GRADIENT_MAX_X: Final = 0.7347
GRADIENT_MAX_Y: Final = 0.8264


class uint12_t(t.uint_t, bits=12):
    """12-bit unsigned integer."""


class HueLightUpdateFlags(t.bitmap16):
    """Fields present in a light update."""

    ON_OFF = 1 << 0
    BRIGHTNESS = 1 << 1
    COLOR_MIREK = 1 << 2
    COLOR_XY = 1 << 3
    FADE_SPEED = 1 << 4
    EFFECT_TYPE = 1 << 5
    GRADIENT_PARAMS = 1 << 6
    EFFECT_SPEED = 1 << 7
    GRADIENT_COLORS = 1 << 8
    UNKNOWN_9 = 1 << 9


class HueEffectType(t.enum8):
    """Light effect."""

    NoEffect = 0x00
    Candle = 0x01
    Fireplace = 0x02
    Prism = 0x03
    Sunrise = 0x09
    Sparkle = 0x0A
    Opal = 0x0B
    Glisten = 0x0C
    Sunset = 0x0D
    Underwater = 0x0E
    Cosmos = 0x0F
    Sunbeam = 0x10
    Enchant = 0x11


class HueGradientStyle(t.enum8):
    """Gradient style."""

    Linear = 0x00
    Scattered = 0x02
    Mirrored = 0x04
    Segmented = 0x06


class HueColorXY(t.Struct):
    """CIE XY color, with 0x0000-0xFFFF mapping to 0.0-1.0."""

    x: t.uint16_t
    y: t.uint16_t

    @classmethod
    def from_xy(cls, x: float, y: float) -> Self:
        """Create from CIE XY coordinates."""
        return cls(x=round(x * 0xFFFF), y=round(y * 0xFFFF))

    def to_xy(self) -> tuple[float, float]:
        """Convert to CIE XY coordinates."""
        return self.x / 0xFFFF, self.y / 0xFFFF


class HueGradientColor(t.IntStruct, t.uint24_t):
    """CIE XY color, with 0x000-0xFFF mapping to 0.0-`GRADIENT_MAX_X/Y`."""

    x: uint12_t
    y: uint12_t

    @classmethod
    def from_xy(cls, x: float, y: float) -> Self:
        """Create from CIE XY coordinates."""
        return cls(
            x=round(x / GRADIENT_MAX_X * 0xFFF),
            y=round(y / GRADIENT_MAX_Y * 0xFFF),
        )

    def to_xy(self) -> tuple[float, float]:
        """Convert to CIE XY coordinates."""
        return self.x / 0xFFF * GRADIENT_MAX_X, self.y / 0xFFF * GRADIENT_MAX_Y


class HueGradientColors(t.Struct):
    """Gradient colors. `size` and `color_count` are computed when serializing."""

    size: t.uint8_t
    reserved1: t.uint4_t = t.StructField(default=0)
    color_count: t.uint4_t
    style: HueGradientStyle
    reserved2: t.uint16_t = t.StructField(default=0)
    colors: t.List[HueGradientColor] = t.StructField(length=lambda s: s.color_count)

    def serialize(self) -> bytes:
        """Serialize, computing `size` and `color_count`."""
        return t.Struct.serialize(
            self.replace(size=4 + 3 * len(self.colors), color_count=len(self.colors))
        )


class HueGradientParams(t.Struct):
    """Gradient scale and offset, in units of 1/8."""

    scale: t.uint8_t
    offset: t.uint8_t


def _flag(flag: HueLightUpdateFlags) -> t.StructField:
    return t.StructField(requires=lambda s: flag in s.flags)


class HueLightUpdate(t.Struct):
    """Combined light update. `flags` is computed when serializing."""

    flags: HueLightUpdateFlags
    on_off: t.Bool = _flag(HueLightUpdateFlags.ON_OFF)
    brightness: t.uint8_t = _flag(HueLightUpdateFlags.BRIGHTNESS)
    color_mirek: t.uint16_t = _flag(HueLightUpdateFlags.COLOR_MIREK)
    color_xy: HueColorXY = _flag(HueLightUpdateFlags.COLOR_XY)
    fade_speed: t.uint16_t = _flag(HueLightUpdateFlags.FADE_SPEED)
    effect_type: HueEffectType = _flag(HueLightUpdateFlags.EFFECT_TYPE)
    gradient_colors: HueGradientColors = _flag(HueLightUpdateFlags.GRADIENT_COLORS)
    # Effect speed, or the duration of a timed effect (see `encode_effect_duration`)
    effect_speed: t.uint8_t = _flag(HueLightUpdateFlags.EFFECT_SPEED)
    gradient_params: HueGradientParams = _flag(HueLightUpdateFlags.GRADIENT_PARAMS)
    # Reported by gradient lights, only observed value is 0
    unknown_9: t.uint8_t = _flag(HueLightUpdateFlags.UNKNOWN_9)

    def serialize(self) -> bytes:
        """Serialize, computing `flags` from the fields that are set."""
        flags = HueLightUpdateFlags(0)

        for field in self.fields[1:]:
            if getattr(self, field.name) is not None:
                flags |= HueLightUpdateFlags[field.name.upper()]

        return t.Struct.serialize(self.replace(flags=flags))


def encode_effect_duration(seconds: int) -> int:
    """Encode the duration of a timed effect (sunrise, sunset) as an effect speed."""
    seconds = max(seconds, 1)

    if seconds < 60:
        base, resolution, minimum = 0xFC, 1, 0x00
    elif seconds < 295:
        base, resolution, minimum = 0xCC, 5, 0x92
    elif seconds < 885:
        base, resolution, minimum = 0xA5, 15, 0x6B
    elif seconds < 3540:
        base, resolution, minimum = 0x79, 60, 0x3F
    else:
        base, resolution, minimum = 0x4A, 300, 0x02

    return max(minimum, base - (seconds + resolution // 2) // resolution)
