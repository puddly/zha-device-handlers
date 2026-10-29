"""Philips Hue devices."""

from typing import Any, Final

from zha.application.helpers import safe_read
from zha.application.platforms import (
    AttrConfig,
    ClusterConfig,
    EntityCategory,
    ZclPlatformEntity,
)
from zha.application.platforms.light import BaseLight, HueLight
from zha.application.platforms.light.const import (
    EFFECT_OFF,
    ColorMode,
    FlashMode,
    LightEntityFeature,
)
from zha.application.platforms.number import BaseNumber
from zigpy.zcl import AttributeReadEvent, AttributeReportedEvent, AttributeUpdatedEvent

from zhaquirks.builder import QuirkBuilder
from zhaquirks.philips import (
    PHILIPS,
    SIGNIFY,
    HueSegmentState,
    HueSegmentsUpdatedEvent,
    PhilipsHueEntertainmentCluster,
    PhilipsHueLightCluster,
)
from zhaquirks.philips.hue_gradient_scenes import HUE_GRADIENT_SCENES
from zhaquirks.philips.hue_light_update import HueColorXY, HueEffectType, HueLightUpdate

HUE_EFFECTS: Final = {
    effect.name.lower(): effect
    for effect in HueEffectType
    if effect is not HueEffectType.NoEffect
}


class HueEffectLight(HueLight):
    """Hue light with Hue effects."""

    _server_cluster_config = {
        **HueLight._server_cluster_config,
        PhilipsHueLightCluster.cluster_id: ClusterConfig(
            attributes={
                PhilipsHueLightCluster.AttributeDefs.state: AttrConfig(
                    read_on_startup=True
                ),
            },
        ),
    }

    _effect_list: list[str]

    # Gradient scenes, listed as effects
    _GRADIENT_SCENES: dict[str, HueLightUpdate] = {}

    def __init__(self, endpoint, device, **kwargs) -> None:
        """Initialize the light."""
        self._hue_cluster = endpoint.zigpy_endpoint.in_clusters[
            PhilipsHueLightCluster.cluster_id
        ]
        super().__init__(endpoint, device, **kwargs)

    def on_add(self) -> None:
        """Run when entity is added."""
        super().on_add()

        for event_type in (
            AttributeReadEvent,
            AttributeReportedEvent,
            AttributeUpdatedEvent,
        ):
            self._on_remove_callbacks.append(
                self._hue_cluster.on_event(
                    event_type.event_type, self.handle_hue_state_updated
                )
            )

    def recompute_capabilities(self) -> None:
        """Recompute capabilities."""
        super().recompute_capabilities()
        self._supported_features |= LightEntityFeature.EFFECT
        self._effect_list = [*self._effect_list, *HUE_EFFECTS, *self._GRADIENT_SCENES]
        self._update_hue_effect(
            self._hue_cluster.get(PhilipsHueLightCluster.AttributeDefs.state.name)
        )

    def _update_hue_effect(self, state: bytes | None) -> None:
        if state is None:
            return

        update, _ = HueLightUpdate.deserialize(state)

        if update.effect_type not in (None, HueEffectType.NoEffect):
            self._effect = update.effect_type.name.lower()
        elif self._effect in HUE_EFFECTS:
            self._effect = EFFECT_OFF

    def handle_hue_state_updated(
        self,
        event: AttributeReadEvent | AttributeReportedEvent | AttributeUpdatedEvent,
    ) -> None:
        """Update the effect from the Hue state."""
        if event.attribute_id != PhilipsHueLightCluster.AttributeDefs.state.id:
            return

        self._update_hue_effect(event.value)
        self.maybe_emit_state_changed_event()

    async def async_update(self) -> None:
        """Attempt to retrieve the state from the light."""
        await super().async_update()

        if (
            self.is_transitioning
            or not self.device.gateway.config.allow_polling
            or not self.device.available
        ):
            return

        await safe_read(
            self._hue_cluster,
            [PhilipsHueLightCluster.AttributeDefs.state.name],
            allow_cache=False,
            only_cache=False,
        )

    async def async_turn_on(
        self,
        *,
        transition: float | None = None,
        brightness: int | None = None,
        effect: str | None = None,
        flash: FlashMode | None = None,
        color_temp: int | None = None,
        xy_color: tuple[float, float] | None = None,
    ) -> None:
        """Turn the entity on."""
        if effect in HUE_EFFECTS:
            update = HueLightUpdate(on_off=True, effect_type=HUE_EFFECTS[effect])
        elif effect in self._GRADIENT_SCENES:
            # The gradient replaces any running effect
            update = self._GRADIENT_SCENES[effect].replace(
                on_off=True, effect_type=HueEffectType.NoEffect
            )
        else:
            if effect is not None and (
                self._effect in HUE_EFFECTS or self._effect in self._GRADIENT_SCENES
            ):
                await self._hue_cluster.multicolor(
                    data=HueLightUpdate(effect_type=HueEffectType.NoEffect)
                )
                self._effect = EFFECT_OFF

            await super().async_turn_on(
                transition=transition,
                brightness=brightness,
                effect=effect,
                flash=flash,
                color_temp=color_temp,
                xy_color=xy_color,
            )
            return

        # Turn on, set the color, and start the effect in a single update

        if transition is not None:
            update.fade_speed = int(10 * transition)

        if brightness is not None:
            update.brightness = min(254, brightness)

        if color_temp is not None:
            update.color_mirek = color_temp

        if xy_color is not None:
            update.color_xy = HueColorXY.from_xy(*xy_color)

        await self._hue_cluster.multicolor(data=update)

        self._state = True
        self._effect = effect

        if update.brightness is not None:
            self._brightness = update.brightness

        if color_temp is not None:
            self._color_mode = ColorMode.COLOR_TEMP
            self._color_temp = color_temp
            self._xy_color = None

        if xy_color is not None:
            self._color_mode = ColorMode.XY
            self._xy_color = xy_color
            self._color_temp = None

        self.maybe_emit_state_changed_event()


class HueGradientLight(HueEffectLight):
    """Hue gradient light, with gradient scenes. Using it stops segment streaming."""

    _GRADIENT_SCENES = HUE_GRADIENT_SCENES

    def __init__(self, endpoint, device, **kwargs) -> None:
        """Initialize the light."""
        self._entertainment_cluster = endpoint.zigpy_endpoint.in_clusters[
            PhilipsHueEntertainmentCluster.cluster_id
        ]
        super().__init__(endpoint, device, **kwargs)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self._entertainment_cluster.stop_stream()
        await super().async_turn_on(**kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self._entertainment_cluster.stop_stream()
        await super().async_turn_off(**kwargs)


class HueSegmentLight(BaseLight, ZclPlatformEntity):
    """Segment of a Hue gradient light, controlled by entertainment streaming."""

    _attr_primary = False
    _cluster: PhilipsHueEntertainmentCluster

    def __init__(self, endpoint, device, *, segment: int, **kwargs) -> None:
        """Initialize the segment."""
        self._segment = segment
        super().__init__(endpoint, device, **kwargs)
        self._supported_color_modes = {ColorMode.XY}
        self._color_mode = ColorMode.XY

    def _is_supported(self) -> bool:
        # Segments come and go with the segment count of the light
        segments = self._cluster.segments
        return segments is not None and self._segment < len(segments)

    @property
    def _segment_state(self) -> HueSegmentState:
        assert self._cluster.segments is not None
        return self._cluster.segments[self._segment]

    @property
    def is_on(self) -> bool:
        """Return true if the segment is on."""
        return self._segment_state.on

    @property
    def brightness(self) -> int:
        """Return the brightness of the segment."""
        return self._segment_state.brightness

    @property
    def xy_color(self) -> tuple[float, float]:
        """Return the color of the segment."""
        return self._segment_state.xy_color

    def on_add(self) -> None:
        """Run when entity is added."""
        super().on_add()
        self._on_remove_callbacks.append(
            self._cluster.on_event(
                HueSegmentsUpdatedEvent.event_type, self.handle_segments_updated
            )
        )

    def handle_segments_updated(self, event: HueSegmentsUpdatedEvent) -> None:
        """Update the state when the segments change."""
        self.maybe_emit_state_changed_event()

    async def async_turn_on(
        self,
        *,
        transition: float | None = None,
        brightness: int | None = None,
        effect: str | None = None,
        flash: FlashMode | None = None,
        color_temp: int | None = None,
        xy_color: tuple[float, float] | None = None,
    ) -> None:
        """Turn the segment on."""
        state = self._segment_state
        state.on = True

        if brightness is not None:
            state.brightness = brightness

        if xy_color is not None:
            state.xy_color = xy_color

        await self._cluster.send_segments()

    async def async_turn_off(self, *, transition: float | None = None) -> None:
        """Turn the segment off."""
        self._segment_state.on = False
        await self._cluster.send_segments()


class HueSegmentCountNumber(BaseNumber, ZclPlatformEntity):
    """Number of segments a Hue gradient light is evenly split into."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_step = 1
    _cluster: PhilipsHueEntertainmentCluster

    _server_cluster_config = {
        PhilipsHueEntertainmentCluster.cluster_id: ClusterConfig(
            attributes={
                PhilipsHueEntertainmentCluster.AttributeDefs.max_segment_count: (
                    AttrConfig(read_on_startup=True)
                ),
                PhilipsHueEntertainmentCluster.AttributeDefs.pixel_count: AttrConfig(
                    read_on_startup=True
                ),
            },
        ),
    }

    def on_add(self) -> None:
        """Run when entity is added."""
        super().on_add()

        # The segment lights are only created once the layout is known
        if self._cluster.segments is None:
            self._tracked_tasks.append(
                self.device.gateway.async_create_background_task(
                    self._async_read_segment_layout(),
                    name=f"read_segment_layout_{self.unique_id}",
                    eager_start=True,
                    untracked=True,
                )
            )

    async def _async_read_segment_layout(self) -> None:
        await self._cluster.read_segment_layout()
        await self.device.recompute_entities()
        self.maybe_emit_state_changed_event()

    @property
    def native_max_value(self) -> float:
        """Return the maximum segment count of the light."""
        return self._cluster.get(
            PhilipsHueEntertainmentCluster.AttributeDefs.max_segment_count.name
        )

    @property
    def native_value(self) -> int | None:
        """Return the segment count."""
        if self._cluster.segments is None:
            return None

        return len(self._cluster.segments)

    async def async_set_native_value(self, value: float) -> None:
        """Split the light into a new number of segments."""
        await self._cluster.write_segment_count(int(value))
        await self.device.recompute_entities()
        self.maybe_emit_state_changed_event()


(
    QuirkBuilder()
    .applies_to(SIGNIFY, "929004608001")
    .applies_to(SIGNIFY, "929004608101")
    .applies_to(SIGNIFY, "929004608201")
    .friendly_name(
        model="Hue OmniGlow lightstrip",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "929004610402")
    .friendly_name(
        model="Hue Flux gradient lightstrip",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCX001")
    .applies_to(SIGNIFY, "LCX002")
    .applies_to(SIGNIFY, "LCX003")
    .applies_to(SIGNIFY, "LCX005")
    .applies_to(SIGNIFY, "LCX006")
    .friendly_name(
        model="Hue Play gradient lightstrip",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCX012")
    .applies_to(SIGNIFY, "LCX015")
    .applies_to(SIGNIFY, "LCX016")
    .applies_to(SIGNIFY, "LCX017")
    .friendly_name(
        model="Hue Festavia gradient light string",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCX024")  # 91ft
    .applies_to(SIGNIFY, "LCX025")  # 45ft
    .applies_to(SIGNIFY, "LCX026")  # Likely model for 22ft
    .friendly_name(
        model="Hue Festavia globe outdoor string lights",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LTB003")
    .friendly_name(
        model="Hue White Ambiance BR30 E26",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "929003116301")
    .applies_to(SIGNIFY, "929003116401")
    .applies_to(SIGNIFY, "929003116501")
    .applies_to(SIGNIFY, "929003116601")
    .friendly_name(
        model="Hue Perifo light tube",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "4080248U9")
    .applies_to(SIGNIFY, "915005987101")
    .applies_to(PHILIPS, "915005987101")
    .applies_to(SIGNIFY, "915005987201")
    .applies_to(SIGNIFY, "915005987501")
    .applies_to(SIGNIFY, "915005987601")
    .applies_to(SIGNIFY, "915005987701")
    .applies_to(SIGNIFY, "915005987801")
    .applies_to(SIGNIFY, "929003479601")
    .applies_to(SIGNIFY, "929003479701")
    .friendly_name(
        model="Hue Signe gradient floor lamp",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "915005986901")
    .applies_to(SIGNIFY, "915005987001")
    .applies_to(SIGNIFY, "915005987401")
    .applies_to(SIGNIFY, "915005987301")
    .friendly_name(
        model="Hue Signe gradient table lamp",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "915005987901")
    .applies_to(SIGNIFY, "915005988001")
    .applies_to(SIGNIFY, "915005988101")
    .applies_to(SIGNIFY, "915005988201")
    .applies_to(SIGNIFY, "915005988401")
    .applies_to(SIGNIFY, "915005988501")
    .friendly_name(
        model="Hue Play gradient light tube",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LTA001")
    .friendly_name(
        model="Hue white ambiance E27 with Bluetooth",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LWU001")
    .friendly_name(
        model="Hue P45 light bulb",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(PHILIPS, "7602031P7")
    .applies_to(PHILIPS, "7602031U7")
    .friendly_name(
        model="Hue Go",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(PHILIPS, "1743130P7")
    .applies_to(PHILIPS, "1743430P7")
    .applies_to(PHILIPS, "1743230P7")
    .applies_to(PHILIPS, "1745430A7")
    .applies_to(PHILIPS, "1745430P7")
    .friendly_name(
        model="Hue Impress outdoor Pedestal",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCD003")
    .friendly_name(
        model="Hue Akari downlight",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(PHILIPS, "1743530P7")
    .friendly_name(
        model="Hue Discover outdoor floodlight",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCL008")
    .friendly_name(
        model="Hue Lightstrip Solo",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .replaces_entity(HueLight, HueEffectLight, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(PHILIPS, "1746330P7")
    .friendly_name(
        model="Hue Appear Outdoor wall light",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

# Segment lights beyond the segment count of a light are not created
LCX004_MAX_SEGMENTS: Final = 10

lcx004 = (
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCX004")
    .friendly_name(
        model="Hue Gradient lightstrip",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .replaces(PhilipsHueEntertainmentCluster, endpoint_id=11)
    .replaces_entity(HueLight, HueGradientLight, endpoint_id=11)
    .adds_entity(
        HueSegmentCountNumber,
        endpoint_id=11,
        cluster_id=PhilipsHueEntertainmentCluster.cluster_id,
        unique_id_suffix="segment_count",
        fallback_name="Segment count",
    )
)

for segment in range(LCX004_MAX_SEGMENTS):
    lcx004.adds_entity(
        HueSegmentLight,
        endpoint_id=11,
        cluster_id=PhilipsHueEntertainmentCluster.cluster_id,
        segment=segment,
        unique_id_suffix=f"segment_{segment + 1}",
        fallback_name=f"Segment {segment + 1}",
    )

lcx004.add_to_registry()

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCA007")
    .applies_to(SIGNIFY, "LCE001")
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .replaces_entity(HueLight, HueEffectLight, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCX029")
    .friendly_name(
        model="Hue Festavia globe outdoor string lights",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCT016")
    .friendly_name(
        model="Hue white and color ambiance E26/E27/E14",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCA009")
    .friendly_name(
        model="Hue white and color ambiance E26/A19 1600lm",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCL001")
    .friendly_name(
        model="Hue white and color ambiance LightStrip plus",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "929003528702")
    .friendly_name(
        model="Hue Sana wall light",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LTA008")
    .friendly_name(
        model="Hue white ambiance E27 with Bluetooth",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LTW004")
    .friendly_name(
        model="Hue white ambiance E26/E27",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LTO005")
    .friendly_name(
        model="Hue white ambiance G40 E26 filament globe with Bluetooth",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "929003531502")
    .friendly_name(
        model="Hue white ambiance ceiling white Enrave M with Bluetooth",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)
