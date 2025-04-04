from pathlib import Path
from typing import Any

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.protocols import Readable
from dodal.common import MsgGenerator, inject
from ophyd_async.epics.adaravis import AravisDetector
from ophyd_async.fastcs.panda import HDFPanda
from ophyd_async.plan_stubs import setup_ndstats_sum

DEFAULT_WEBCAM = inject("webcam")
DEFAULT_PANDA = inject("panda1")

ROOT_CONFIG_SAVES_DIR = Path(__file__).parent.parent.parent / "pvs" / "basic_plan"


def basic_plan(
    panda: HDFPanda = DEFAULT_PANDA,
    metadata: dict[str, Any] | None = None,
    manta: AravisDetector = DEFAULT_WEBCAM,
    exposure: float = 1.0,
) -> MsgGenerator:
    """
    Description


    Args:
        panda: PandA for controlling flyable motion
        exposure: exposure time of detectors
        metadata: metadata: Key-value metadata to include in exported data,
            defaults to None.

    Returns:
        MsgGenerator: Plan

    Yields:
        Iterator[MsgGenerator]: Bluesky messages
    """
    detectors: set[Readable] = {manta}

    plan_args = {
        "exposure": exposure,
        "panda": repr(panda),
    }
    _md = {
        "detectors": {device.name for device in detectors},
        "motors": {},
        "plan_args": plan_args,
        "hints": {},
    }
    _md.update(metadata or {})

    devices = detectors

    # this is for file writing
    yield from setup_ndstats_sum(manta)

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md=_md)
    def inner_plan():
        yield from bps.trigger_and_read([*detectors])

    rs_uid = yield from inner_plan()
    return rs_uid
