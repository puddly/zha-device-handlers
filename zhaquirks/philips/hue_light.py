"""Philips Hue devices."""

from typing import Final

from zha.application.helpers import safe_read
from zha.application.platforms import AttrConfig, ClusterConfig
from zha.application.platforms.light import HueLight
from zha.application.platforms.light.const import (
    EFFECT_OFF,
    ColorMode,
    FlashMode,
    LightEntityFeature,
)
from zigpy.zcl import AttributeReadEvent, AttributeReportedEvent, AttributeUpdatedEvent

from zhaquirks.builder import QuirkBuilder
from zhaquirks.philips import PHILIPS, SIGNIFY, PhilipsHueLightCluster
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

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCX004")
    .friendly_name(
        model="Hue Gradient lightstrip",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .replaces_entity(HueLight, HueEffectLight, endpoint_id=11)
    .add_to_registry()
)

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
