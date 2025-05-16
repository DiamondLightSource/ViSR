from pathlib import Path
from typing import Any

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.protocols import Movable
from dodal.common import MsgGenerator, inject
from dodal.devices.motors import XYZPositioner
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from ophyd_async.core import Device, StandardDetector, TriggerInfo
from ophyd_async.epics.adaravis import AravisDetector
from ophyd_async.plan_stubs import setup_ndstats_sum
from scanspec.specs import Line, Spec

DEFAULT_WEBCAM: AravisDetector = inject("manta")
DEFAULT_MOTOR: XYZPositioner = inject("sample_stage")

ROOT_CONFIG_SAVES_DIR = Path(__file__).parent.parent.parent / "pvs" / "demo_plan"

# using snaked grid from the tutorial
# https://blueskyproject.io/scanspec/main/tutorials/creating-a-spec.html#snaked-grid

#  physically measured the data from here
# https://github.com/DiamondLightSource/ViSR/issues/4#issuecomment-2766099774
# NOTE: y is inverted
top_left = [-2, 3.7]
bottom_right = [4.3, 7.2]
STAGE_Z_CONSTANT = 0.01


def demo_plan(
    manta: AravisDetector = DEFAULT_WEBCAM,
    exposure: float = 1.0,
    sample_stage: XYZPositioner = DEFAULT_MOTOR,
    metadata: dict[str, Any] | None = None,
) -> MsgGenerator:
    detectors: set[StandardDetector] = {manta}

    devices: list[Device] = [*detectors, sample_stage]

    # this is for file writing
    yield from setup_ndstats_sum(manta)

    spec: Spec[Movable] = Line(sample_stage.x, top_left[0], bottom_right[0], 7) * ~Line(
        sample_stage.y, top_left[1], bottom_right[1], 9
    )

    _md = {
        "detectors": {device.name for device in detectors},
        "motors": {sample_stage.name},
        "plan_args": {"exposure": exposure},
        "shape": spec.shape,
        "hints": {},
    }
    _md.update(metadata or {})

    @attach_data_session_metadata_decorator()
    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md=_md)
    def inner_plan():
        yield from bps.abs_set(sample_stage.z, STAGE_Z_CONSTANT)
        yield from bps.prepare(manta, TriggerInfo(livetime=0.2, number_of_triggers=1))
        for d in spec.midpoints():
            new_x = d.get(sample_stage.x)
            new_y = d.get(sample_stage.y)
            print(f"new x {new_x}, new y: {new_y}")
            if new_x:
                yield from bps.abs_set(sample_stage.x, new_x, wait=False)
            if new_y:
                yield from bps.abs_set(sample_stage.y, new_y, wait=False)
            yield from bps.wait()
            yield from bps.trigger_and_read([*detectors])

    yield from inner_plan()
    rs_uid = yield from inner_plan()
    return rs_uid
