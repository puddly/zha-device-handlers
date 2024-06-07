"""Module for Legrand Cable Outlet with pilot wire functionality."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import add_to_registry_v2
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.legrand import LEGRAND, MANUFACTURER_SPECIFIC_CLUSTER_ID

DEVICE_MODE_WIRE_PILOT_ON = [0x02, 0x00]
DEVICE_MODE_WIRE_PILOT_OFF = [0x01, 0x00]


class LegrandCluster(CustomCluster):
    """LegrandCluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "Legrand"
    ep_attribute = "legrand_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        device_mode = ZCLAttributeDef(
            id=0x0000,
            type=t.data16,
            is_manufacturer_specific=True,
        )
        led_dark = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        led_on = ZCLAttributeDef(
            id=0x0002,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        wire_pilot_mode = ZCLAttributeDef(
            id=0x4000,
            type=t.Bool,
            is_manufacturer_specific=True,
        )

    async def write_attributes(self, attributes, manufacturer=None) -> list:
        """Write attributes to the cluster."""

        attrs = {}
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            if attr_def == LegrandCluster.AttributeDefs.wire_pilot_mode:
                attrs[LegrandCluster.AttributeDefs.device_mode.id] = (
                    DEVICE_MODE_WIRE_PILOT_ON if value else DEVICE_MODE_WIRE_PILOT_OFF
                )
            else:
                attrs[attr] = value
        return await super().write_attributes(attrs, manufacturer)

    def _update_attribute(self, attrid, value) -> None:
        super()._update_attribute(attrid, value)
        if attrid == LegrandCluster.AttributeDefs.device_mode.id:
            self._update_attribute(
                LegrandCluster.AttributeDefs.wire_pilot_mode.id,
                (value == DEVICE_MODE_WIRE_PILOT_ON),
            )


class HeatMode(t.enum8):
    """Heat mode."""

    Comfort = 0x00
    Comfort_minus_1 = 0x01
    Comfort_minus_2 = 0x02
    Eco = 0x03
    Frost_protection = 0x04
    Off = 0x05


class LegrandWirePilotCluster(CustomCluster):
    """Legrand wire pilot manufacturer-specific cluster."""

    cluster_id = 0xFC40
    name = "Legrand Wire Pilot"
    ep_attribute = "legrand_wire_pilot"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for LegrandCluster."""

        heat_mode = ZCLAttributeDef(
            id=0x00,
            type=HeatMode,
            is_manufacturer_specific=True,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        set_heat_mode = ZCLCommandDef(
            id=0x00,
            schema={"mode": HeatMode},
            is_manufacturer_specific=True,
        )


(
    add_to_registry_v2(f" {LEGRAND}", " Cable outlet")
    .replaces(LegrandCluster)
    .replaces(LegrandWirePilotCluster)
    .replaces(LegrandCluster, cluster_type=ClusterType.Client)
    .switch(
        attribute_name=LegrandCluster.AttributeDefs.wire_pilot_mode.name,
        cluster_id=LegrandCluster.cluster_id,
        translation_key="wire_pilot_mode",
    )
)
