"""Tests for the Philips Hue combined light update format."""

import pytest
import zigpy.types as t

from zhaquirks.philips.hue_light_update import (
    GRADIENT_MAX_X,
    GRADIENT_MAX_Y,
    HueColorXY,
    HueEffectType,
    HueGradientColor,
    HueGradientColors,
    HueGradientParams,
    HueGradientStyle,
    HueLightUpdate,
    HueLightUpdateFlags,
    encode_effect_duration,
)


@pytest.mark.parametrize(
    "data",
    [
        # Examples from the Bifrost documentation
        "50010000135000fffff3620c400f5bf4120d400f5b0cf4f43858",
        "ab00012e6f2f40100f7f",
        "51010104000d30040000fa441eb7cb49bff65f1800",
        "19000132518f530400",
        "1100000800",
        "bb0001feb575156904000a80",
        "51010104001350020000fa441e590834b7cb49ff8857bff65f2800",
        "530101c00400135000000094031fda1955b98347f00468c426792800",
        # Captured from the Hue app
        "500104001350000000b0498a5c0a888fea89eb0b7ee15c742800",
        "21000101",
        "200000",
        # Reported by gradient lights
        "000200",
    ],
)
def test_round_trip(data: str) -> None:
    """Test that updates deserialize and serialize back to the same bytes."""
    update, rest = HueLightUpdate.deserialize(bytes.fromhex(data))

    assert rest == b""
    assert update.serialize().hex() == data


def test_deserialize() -> None:
    """Test deserializing an update with all simple fields."""
    update, _ = HueLightUpdate.deserialize(bytes.fromhex("bb0001feb575156904000a80"))

    assert update == HueLightUpdate(
        flags=(
            HueLightUpdateFlags.ON_OFF
            | HueLightUpdateFlags.BRIGHTNESS
            | HueLightUpdateFlags.COLOR_XY
            | HueLightUpdateFlags.FADE_SPEED
            | HueLightUpdateFlags.EFFECT_TYPE
            | HueLightUpdateFlags.EFFECT_SPEED
        ),
        on_off=t.Bool.true,
        brightness=254,
        color_xy=HueColorXY(x=0x75B5, y=0x6915),
        fade_speed=4,
        effect_type=HueEffectType.Sparkle,
        effect_speed=128,
    )


def test_deserialize_gradient() -> None:
    """Test deserializing an update with gradient colors."""
    update, _ = HueLightUpdate.deserialize(
        bytes.fromhex("51010104000d30040000fa441eb7cb49bff65f1800")
    )

    assert update.gradient_colors == HueGradientColors(
        size=13,
        color_count=3,
        style=HueGradientStyle.Mirrored,
        colors=[
            HueGradientColor(x=0x4FA, y=0x1E4),
            HueGradientColor(x=0xBB7, y=0x49C),
            HueGradientColor(x=0x6BF, y=0x5FF),
        ],
    )
    assert update.gradient_params == HueGradientParams(scale=0x18, offset=0x00)


def test_serialize_computes_flags_and_sizes() -> None:
    """Test that flags, gradient size, and color count are computed."""
    update = HueLightUpdate(
        on_off=True,
        fade_speed=4,
        gradient_colors=HueGradientColors(
            style=HueGradientStyle.Scattered,
            colors=[HueGradientColor(x=0x123, y=0x456)],
        ),
        gradient_params=HueGradientParams(scale=0x08, offset=0x00),
    )

    assert update.serialize() == bytes.fromhex("510101040007100200002361450800")


def test_gradient_color_packing() -> None:
    """Test the 12-bit gradient color packing."""
    color = HueGradientColor(x=0x123, y=0x456)

    assert color.serialize() == bytes([0x23, 0x61, 0x45])
    assert HueGradientColor.deserialize(bytes([0x23, 0x61, 0x45])) == (color, b"")


def test_color_xy_conversion() -> None:
    """Test converting colors to and from CIE XY coordinates."""
    assert HueColorXY.from_xy(0.5, 1.0) == HueColorXY(x=0x8000, y=0xFFFF)
    assert HueColorXY(x=0xFFFF, y=0x0000).to_xy() == (1.0, 0.0)

    assert HueGradientColor.from_xy(GRADIENT_MAX_X, GRADIENT_MAX_Y) == (
        HueGradientColor(x=0xFFF, y=0xFFF)
    )
    assert HueGradientColor(x=0xFFF, y=0xFFF).to_xy() == (
        GRADIENT_MAX_X,
        GRADIENT_MAX_Y,
    )

    for value in range(0x1000):
        color = HueGradientColor(x=value, y=value)
        assert HueGradientColor.from_xy(*color.to_xy()) == color


@pytest.mark.parametrize(
    ("milliseconds", "encoded"),
    [
        # Last millisecond producing each value, from Bifrost's conformance test
        (1499, 251),
        (2499, 250),
        (57499, 195),
        (58499, 194),
        (59499, 193),
        (62499, 192),
        (67499, 191),
        (287499, 147),
        (294499, 146),
        (802499, 112),
        (817499, 111),
        (884499, 107),
        (929499, 106),
        (3449499, 64),
        (3539499, 63),
        (3749499, 62),
        (4049499, 61),
        (20849499, 5),
        (21449499, 3),
        (21600000, 2),
        # Sniffed from a Hue bridge
        (5 * 60_000, 145),
        (10 * 60_000, 125),
        (15 * 60_000, 106),
        (30 * 60_000, 91),
        (60 * 60_000, 62),
    ],
)
def test_encode_effect_duration(milliseconds: int, encoded: int) -> None:
    """Test encoding timed effect durations."""
    assert encode_effect_duration((milliseconds + 500) // 1000) == encoded
