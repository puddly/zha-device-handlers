"""Philips Hue entertainment streaming format, used by cluster 0xFC01.

Reverse engineered by Bifrost: https://github.com/duvholt/bifrost/blob/master/crates/hue/src/zigbee/entertainment.rs
"""

from __future__ import annotations

from typing import Final

import zigpy.types as t

from zhaquirks.philips.hue_light_update import HueGradientColor

# Fade time between frames, where 0xFFFF is about 2.56 seconds
DEFAULT_SMOOTHING: Final = 0x0400


class uint11_t(t.uint_t, bits=11):
    """11-bit unsigned integer."""


class HueEntertainmentMode(t.enum5):
    """Whether a record addresses a whole light or one of its segments."""

    Segment = 0b00000
    Device = 0b01011


class HueSegment(t.Struct):
    """Pixels of a gradient light making up one segment."""

    start: t.uint8_t
    length: t.uint8_t


class HueSegment16(t.Struct):
    """Pixels of a gradient light making up one segment, with 16-bit fields."""

    start: t.uint16_t
    length: t.uint16_t


class HueEntertainmentRecord(t.Struct):
    """Color and brightness of a light, or of one of its segments."""

    # Network address of the light, plus the segment index in segment mode
    address: t.uint16_t
    mode: HueEntertainmentMode
    brightness: uint11_t
    color: HueGradientColor
