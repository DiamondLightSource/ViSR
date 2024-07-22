from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional

import bluesky.preprocessors as bpp
from bluesky.preprocessors import finalize_decorator
from dls_bluesky_core.core import MsgGenerator, inject
from dodal.devices.linkam3 import Linkam3
from dodal.devices.tetramm import free_tetramm
from ophyd_async.core import (
    HardwareTriggeredFlyable,
    SameTriggerDetectorGroupLogic,
    StandardDetector,
)
from ophyd_async.panda import PandA


def one_plan() -> MsgGenerator:
    """
    A plan that does one thing.
    long description
    """
    dets = []
    plan_args = []
    # yield from
