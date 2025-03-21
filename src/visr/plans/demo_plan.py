from pathlib import Path
from typing import Any

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.protocols import Movable
from dodal.common import MsgGenerator, inject
from dodal.devices.motors import XYZPositioner
from ophyd_async.core import Device, StandardDetector
from ophyd_async.epics.adaravis import AravisDetector
from ophyd_async.plan_stubs import setup_ndstats_sum
from scanspec.specs import Line, Spec

DEFAULT_WEBCAM = inject("webcam")
DEFAULT_MOTOR: XYZPositioner = inject("sample_stage")

ROOT_CONFIG_SAVES_DIR = Path(__file__).parent.parent.parent / "pvs" / "demo_plan"

# using snaked grid from the tutorial
# https://blueskyproject.io/scanspec/main/tutorials/creating-a-spec.html#snaked-grid
# todo spec needs to be revised in person physically
DEMO_LINE: Spec[Movable] = Line("x", 1, 2, 5) * ~Line("y", 1, 2, 5)


# todo the plan should accept a trajectory of points from scanspec
def demo_plan(
    manta: AravisDetector = DEFAULT_WEBCAM,
    exposure: float = 1.0,
    sample_stage: XYZPositioner = DEFAULT_MOTOR,
    spec=DEMO_LINE,
    metadata: dict[str, Any] | None = None,
) -> MsgGenerator:
    detectors: set[StandardDetector] = {manta}

    plan_args = {
        "exposure": exposure,
    }
    _md = {
        "detectors": {device.name for device in detectors},
        "motors": {sample_stage},
        "plan_args": plan_args,
        "hints": {},
    }
    _md.update(metadata or {})

    devices: list[Device] = [*detectors, sample_stage]

    # this is for file writing
    yield from setup_ndstats_sum(manta)

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md=_md)
    def inner_plan():
        for d in spec.midpoints():
            print(d)
            new_x = d.get("x")
            if new_x:
                yield from bps.mv(sample_stage.x, new_x)
            new_y = d.get("y")
            if new_y:
                yield from bps.mv(sample_stage.y, new_y)
            yield from bps.trigger_and_read([*detectors])

    rs_uid = yield from inner_plan()
    return rs_uid
