"""Module for Philips quirks implementations."""

import asyncio
import dataclasses
import itertools
import logging
import time
from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    ARGS,
    BUTTON,
    COMMAND,
    COMMAND_HOLD,
    COMMAND_ID,
    COMMAND_M_LONG_RELEASE,
    COMMAND_M_SHORT_RELEASE,
    COMMAND_PRESS,
    DIM_DOWN,
    DIM_UP,
    DOUBLE_PRESS,
    LONG_PRESS,
    LONG_RELEASE,
    PRESS_TYPE,
    QUADRUPLE_PRESS,
    QUINTUPLE_PRESS,
    SHORT_PRESS,
    SHORT_RELEASE,
    TRIPLE_PRESS,
    TURN_OFF,
    TURN_ON,
    ZHA_SEND_EVENT,
)
from zhaquirks.philips.hue_entertainment import (
    DEFAULT_SMOOTHING,
    HueEntertainmentMode,
    HueEntertainmentRecord,
    HueSegment,
    HueSegment16,
)
from zhaquirks.philips.hue_light_update import HueGradientColor, HueLightUpdate

PHILIPS = "Philips"
SIGNIFY = "Signify Netherlands B.V."
_LOGGER = logging.getLogger(__name__)


class PhilipsOccupancySensing(CustomCluster, OccupancySensing):
    """Philips occupancy cluster."""

    class AttributeDefs(OccupancySensing.AttributeDefs):
        """Attribute definitions."""

        sensitivity: Final = ZCLAttributeDef(
            id=0x0030, type=t.uint8_t, manufacturer_code=0x100B
        )
        sensitivity_max: Final = ZCLAttributeDef(
            id=0x0031, type=t.uint8_t, manufacturer_code=0x100B
        )


class PhilipsBasicCluster(CustomCluster, Basic):
    """Philips Basic cluster."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        philips: Final = ZCLAttributeDef(
            id=0x0031, type=t.bitmap16, is_manufacturer_specific=True
        )

    attr_config = {AttributeDefs.philips.id: 0x000B}

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration."""
        await self.write_attributes(self.attr_config, manufacturer=0x100B)


class ButtonPressQueue:
    """Philips button queue to derive multiple press events."""

    def __init__(self):
        """Init."""
        self._ms_threshold = 300
        self._ms_last_click = 0
        self._click_counter = 1
        self._callback = lambda x: None
        self._task = None

    async def _job(self):
        await asyncio.sleep(self._ms_threshold / 1000)
        self._callback(self._click_counter)

    def press(self, callback):
        """Process a button press."""
        self._callback = callback
        now_ms = time.time() * 1000
        if now_ms - self._ms_last_click > self._ms_threshold:
            self._click_counter = 1
        else:
            self._task.cancel()
            self._click_counter += 1
        self._ms_last_click = now_ms
        self._task = asyncio.ensure_future(self._job())


class Button:
    """Represents a remote button, including string literals used in triggers and actions."""

    def __init__(
        self, id: str, trigger: str | None = None, action: str | None = None
    ) -> None:
        """Init."""
        self.id = id
        self.trigger = trigger or id
        self.action = action or id

    def __repr__(self) -> str:
        """Repr."""
        return f"<Button id={self.id}, trigger={self.trigger}, action={self.action}>"


class PressType:
    """Represents a remote button press-type, including string literals used in triggers and actions."""

    def __init__(
        self, name: str, action: str, arg: str | None = None, trigger: str | None = None
    ) -> None:
        """Init."""
        self.name = name
        self.action = action
        self.arg = arg or action
        self.trigger = trigger or name

    def __repr__(self) -> str:
        """Repr."""
        return f"<PressType name={self.name}, action={self.action}, trigger={self.trigger}, arg={self.arg}>"


class PhilipsRemoteCluster(CustomCluster):
    """Philips remote cluster."""

    cluster_id = 0xFC00
    name = "PhilipsRemoteCluster"
    ep_attribute = "philips_remote_cluster"

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions."""

        notification = foundation.ZCLCommandDef(
            id=0x0000,
            schema={
                "button": t.uint8_t,
                "param2": t.uint24_t,
                "press_type": t.uint8_t,
                "param4": t.uint8_t,
                "param5": t.uint16_t,
            },
            is_manufacturer_specific=True,
        )

    BUTTONS: dict[int, Button] = {}

    PRESS_TYPES: dict[int, PressType] = {
        # We omit "short_press" and "short_release" on purpose, so it
        # won't interfere with simulated multi-press events. We emit
        # them in the multi-press code later on.
        # 0: SHORT_PRESS,
        1: PressType(LONG_PRESS, COMMAND_HOLD),
        # 2: SHORT_RELEASE,
        3: PressType(LONG_RELEASE, COMMAND_M_LONG_RELEASE),
    }

    MULTI_PRESS_EVENTS: dict[int, PressType] = {
        2: PressType(DOUBLE_PRESS, "double_press"),
        3: PressType(TRIPLE_PRESS, "triple_press"),
        4: PressType(QUADRUPLE_PRESS, "quadruple_press"),
        5: PressType(QUINTUPLE_PRESS, "quintuple_press"),
    }
    SIMULATE_SHORT_EVENTS = [
        PressType(SHORT_PRESS, COMMAND_PRESS),
        PressType(SHORT_RELEASE, COMMAND_M_SHORT_RELEASE),
    ]

    def __init__(self, endpoint, is_server=True):
        """Initialize button press queue for each button."""
        super().__init__(endpoint, is_server)
        self.button_press_queue = {k: ButtonPressQueue() for k in self.BUTTONS}

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ):
        """Handle the cluster command."""
        _LOGGER.debug(
            "%s - handle_cluster_request tsn: [%s] command id: %s - args: [%s]",
            self.__class__.__name__,
            hdr.tsn,
            hdr.command_id,
            args,
        )

        button = self.BUTTONS.get(args[0])
        # Bail on unknown buttons. (This gets rid of dial button "presses")
        if button is None:
            _LOGGER.debug(
                "%s - handle_cluster_request unknown button id [%s]",
                self.__class__.__name__,
                args[0],
            )
            return
        _LOGGER.debug(
            "%s - handle_cluster_request button id: [%s], button name: [%s]",
            self.__class__.__name__,
            args[0],
            button,
        )

        press_type = self.PRESS_TYPES.get(args[2])
        if (
            press_type is None
            and self.SIMULATE_SHORT_EVENTS is not None
            and args[2] == 2
        ):
            press_type = self.SIMULATE_SHORT_EVENTS[1]
        if press_type is None:
            _LOGGER.debug(
                "%s - handle_cluster_request unknown button press type: [%s]",
                self.__class__.__name__,
                press_type,
            )
            return

        duration = args[4]
        _LOGGER.debug(
            "%s - handle_cluster_request button press type: [%s], duration: [%s]",
            self.__class__.__name__,
            press_type,
            duration,
        )

        event_args = {
            BUTTON: button.id,
            PRESS_TYPE: press_type.arg,
            COMMAND_ID: hdr.command_id,
            "duration": duration,
            ARGS: args,
        }

        def send_press_event(click_count):
            _LOGGER.debug(
                "%s - send_press_event click_count: [%s]",
                self.__class__.__name__,
                click_count,
            )
            press_type = None
            if click_count == 1:
                press_type = self.PRESS_TYPES.get(0) or self.SIMULATE_SHORT_EVENTS[0]
            elif click_count > 1:
                press_type = self.MULTI_PRESS_EVENTS[min(click_count, 5)]

            _LOGGER.debug(
                "%s - send_press_event evaluated press_type: [%s]",
                self.__class__.__name__,
                press_type,
            )
            if press_type is not None:
                # Override PRESS_TYPE
                event_args[PRESS_TYPE] = press_type.arg
                event_args[ARGS] = list(event_args[ARGS])
                event_args[ARGS][2] = 0 if click_count < 2 else 2 + min(click_count, 5)
                action = f"{button.action}_{press_type.action}"
                _LOGGER.debug(
                    "%s - send_press_event emitting action: [%s] event_args: %s",
                    self.__class__.__name__,
                    action,
                    event_args,
                )
                self.listener_event(ZHA_SEND_EVENT, action, event_args)

            # simulate short release event, if needed for this device type
            if (
                press_type.name == SHORT_PRESS
                and self.SIMULATE_SHORT_EVENTS is not None
            ):
                press_type = self.PRESS_TYPES.get(2) or self.SIMULATE_SHORT_EVENTS[1]
                sim_event_args = event_args.copy()
                sim_event_args[PRESS_TYPE] = press_type.arg
                sim_event_args[ARGS] = sim_event_args[ARGS].copy()
                sim_event_args[ARGS][2] = 2
                action = f"{button.action}_{press_type.action}"
                _LOGGER.debug(
                    "%s - send_press_event emitting simulated action: [%s], event_args: %s",
                    self.__class__.__name__,
                    action,
                    sim_event_args,
                )
                self.listener_event(ZHA_SEND_EVENT, action, sim_event_args)

        # Derive Multiple Presses
        if press_type.name == SHORT_RELEASE:
            _LOGGER.debug(
                "%s - handle_cluster_request handling short release. Push to button press queue for button %s",
                self.__class__.__name__,
                args[0],
            )
            self.button_press_queue[args[0]].press(send_press_event)
        else:
            action = f"{button.action}_{press_type.action}"
            self.listener_event(ZHA_SEND_EVENT, action, event_args)

    @classmethod
    def generate_device_automation_triggers(cls, additional=None):
        """Generate automation triggers based on device buttons and press-types."""
        triggers = {}
        for button in cls.BUTTONS.values():
            press_types = [cls.PRESS_TYPES.values()]
            if cls.SIMULATE_SHORT_EVENTS is not None:
                press_types.append(cls.SIMULATE_SHORT_EVENTS)
                press_types.append(cls.MULTI_PRESS_EVENTS.values())
            for press_type in itertools.chain(*press_types):
                triggers[(press_type.trigger, button.trigger)] = {
                    COMMAND: f"{button.action}_{press_type.action}"
                }

        if additional:
            triggers.update(additional)

        return triggers


class PhilipsRwlRemoteCluster(PhilipsRemoteCluster):
    """Philips remote cluster for RWL devices."""

    BUTTONS = {
        1: Button("on", TURN_ON),
        2: Button("up", DIM_UP),
        3: Button("down", DIM_DOWN),
        4: Button("off", TURN_OFF),
    }


class PhilipsHueLightCluster(CustomCluster):
    """Philips Hue manufacturer cluster."""

    cluster_id: Final[t.uint16_t] = 0xFC03
    ep_attribute: Final[str] = "philips_hue_light_cluster"
    name: Final[str] = "PhilipsHueLightCluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # Current state, as a serialized `HueLightUpdate`
        state: Final = ZCLAttributeDef(
            id=0x0002, type=t.LVBytes, manufacturer_code=0x100B
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        multicolor: Final = ZCLCommandDef(
            id=0x00,
            schema={"data": HueLightUpdate},
            is_manufacturer_specific=True,
        )


@dataclasses.dataclass
class HueSegmentState:
    """State of one streamed segment."""

    on: bool = False
    brightness: int = 254
    xy_color: tuple[float, float] = (0.3127, 0.3290)


@dataclasses.dataclass(kw_only=True, frozen=True)
class HueSegmentsUpdatedEvent:
    """Event generated when the segment states of an entertainment stream change."""

    event_type: Final[str] = "hue_segments_updated"

    device_ieee: str
    endpoint_id: int
    streaming: bool
    segments: list[HueSegmentState]


class PhilipsHueEntertainmentCluster(CustomCluster):
    """Philips Hue entertainment cluster, streaming the colors of segments."""

    cluster_id: Final[t.uint16_t] = 0xFC01
    ep_attribute: Final[str] = "philips_hue_entertainment"
    name: Final[str] = "Philips Hue Entertainment Cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        max_segment_count: Final = ZCLAttributeDef(
            id=0x0002, type=t.uint8_t, access="r", manufacturer_code=0x100B
        )
        pixel_count: Final = ZCLAttributeDef(
            id=0x0004, type=t.uint8_t, access="rp", manufacturer_code=0x100B
        )
        light_balance: Final = ZCLAttributeDef(
            id=0x0005, type=t.uint8_t, manufacturer_code=0x100B
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        frame: Final = ZCLCommandDef(
            id=0x01,
            schema={
                "counter": t.uint32_t,
                "smoothing": t.uint16_t,
                "records": t.List[HueEntertainmentRecord],
            },
            manufacturer_code=0x100B,
        )
        reset: Final = ZCLCommandDef(
            id=0x03,
            schema={
                "unknown1": t.uint8_t,
                "unknown2": t.uint8_t,
                "counter": t.uint32_t,
            },
            manufacturer_code=0x100B,
        )

        # The layout and map commands come in get/set pairs, all starting with an
        # offset. Only offset 0 has been tried. Replies start with a status and the
        # offset, which is 0xFF for a malformed request. Setting a layout with no
        # segments empties it. An LCX004 (1.116.5) supports commands 0x01 and 0x03-0x09
        # only, and ships with a layout of 3 segments of 5, 6, and 5 pixels.
        get_segment_layout: Final = ZCLCommandDef(
            id=0x04,
            schema={"offset": t.uint8_t},
            manufacturer_code=0x100B,
        )
        set_segment_layout: Final = ZCLCommandDef(
            id=0x05,
            schema={
                "offset": t.uint8_t,
                "segments": t.LVList[HueSegment, t.uint8_t],
            },
            manufacturer_code=0x100B,
        )
        get_segment_map: Final = ZCLCommandDef(
            id=0x06,
            schema={"offset": t.uint8_t},
            manufacturer_code=0x100B,
        )
        # Gives each segment a virtual network address for frame records
        set_segment_map: Final = ZCLCommandDef(
            id=0x07,
            schema={
                "offset": t.uint8_t,
                "addresses": t.LVList[t.uint16_t, t.uint8_t],
            },
            manufacturer_code=0x100B,
        )
        get_segment_layout_16: Final = ZCLCommandDef(
            id=0x08,
            schema={"offset": t.uint8_t},
            manufacturer_code=0x100B,
        )
        set_segment_layout_16: Final = ZCLCommandDef(
            id=0x09,
            schema={
                "offset": t.uint8_t,
                "segments": t.LVList[HueSegment16, t.uint8_t],
            },
            manufacturer_code=0x100B,
        )

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions, replies to the server commands."""

        get_segment_layout_rsp: Final = ZCLCommandDef(
            id=0x04,
            schema={
                "status": foundation.Status,
                "offset": t.uint8_t,
                "segments": t.Optional(t.LVList[HueSegment, t.uint8_t]),
            },
            manufacturer_code=0x100B,
        )
        set_segment_layout_rsp: Final = ZCLCommandDef(
            id=0x05,
            schema={"status": foundation.Status, "offset": t.uint8_t},
            manufacturer_code=0x100B,
        )
        get_segment_map_rsp: Final = ZCLCommandDef(
            id=0x06,
            schema={
                "status": foundation.Status,
                "offset": t.uint8_t,
                "addresses": t.Optional(t.LVList[t.uint16_t, t.uint8_t]),
            },
            manufacturer_code=0x100B,
        )
        set_segment_map_rsp: Final = ZCLCommandDef(
            id=0x07,
            schema={"status": foundation.Status, "offset": t.uint8_t},
            manufacturer_code=0x100B,
        )
        get_segment_layout_16_rsp: Final = ZCLCommandDef(
            id=0x08,
            schema={
                "status": foundation.Status,
                "offset": t.uint8_t,
                "segments": t.Optional(t.LVList[HueSegment16, t.uint8_t]),
            },
            manufacturer_code=0x100B,
        )
        set_segment_layout_16_rsp: Final = ZCLCommandDef(
            id=0x09,
            schema={"status": foundation.Status, "offset": t.uint8_t},
            manufacturer_code=0x100B,
        )

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the stream state."""
        super().__init__(*args, **kwargs)
        # One state per segment of the layout, or `None` if the layout was not read yet
        self.segments: list[HueSegmentState] | None = None
        self.streaming = False
        self._counter = 0

    async def read_segment_layout(self) -> None:
        """Read the segment layout from the light, resetting the segment states."""
        rsp = await self.get_segment_layout(offset=0)
        self.segments = [HueSegmentState() for _ in rsp.segments]

    async def write_segment_count(self, count: int) -> None:
        """Split the pixels of the light evenly into `count` segments."""
        await self.stop_stream()

        pixels = self.get(self.AttributeDefs.pixel_count.name)
        starts = [round(index * pixels / count) for index in range(count + 1)]

        await self.set_segment_layout(
            offset=0,
            segments=[
                HueSegment(start=start, length=end - start)
                for start, end in itertools.pairwise(starts)
            ],
        )
        await self.read_segment_layout()

    async def _reset_stream(self) -> None:
        await self.reset(
            unknown1=0,
            unknown2=1,
            counter=self._counter,
            expect_reply=False,
            disable_default_response=True,
        )

    async def send_segments(self) -> None:
        """Stream the segment states, starting the stream if needed."""
        # Segments are addressed by the network address plus the segment index
        nwk = self.endpoint.device.nwk

        if not self.streaming:
            await self._reset_stream()
            await self.write_attributes({self.AttributeDefs.light_balance: 0xFE})
            await self.set_segment_map(
                offset=0,
                addresses=[nwk + segment for segment in range(len(self.segments))],
                expect_reply=False,
                disable_default_response=True,
            )
            self.streaming = True

        await self.frame(
            counter=self._counter,
            smoothing=DEFAULT_SMOOTHING,
            records=[
                HueEntertainmentRecord(
                    address=nwk + segment,
                    mode=HueEntertainmentMode.Segment,
                    brightness=round(state.brightness / 255 * 0x7FF) if state.on else 0,
                    color=HueGradientColor.from_xy(*state.xy_color),
                )
                for segment, state in enumerate(self.segments)
            ],
            expect_reply=False,
            disable_default_response=True,
        )
        self._counter += 1
        self._emit_segments_updated()

    async def stop_stream(self) -> None:
        """Stop streaming, returning the light to its normal state."""
        if not self.streaming:
            return

        await self._reset_stream()
        self.streaming = False

        for state in self.segments:
            state.on = False

        self._emit_segments_updated()

    def _emit_segments_updated(self) -> None:
        self.emit(
            HueSegmentsUpdatedEvent.event_type,
            HueSegmentsUpdatedEvent(
                device_ieee=str(self.endpoint.device.ieee),
                endpoint_id=self.endpoint.endpoint_id,
                streaming=self.streaming,
                segments=[dataclasses.replace(state) for state in self.segments],
            ),
        )
