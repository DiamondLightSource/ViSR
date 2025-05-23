from pathlib import Path
from typing import Any, TypedDict

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
import numpy as np
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

# physically measured the data from here
# https://github.com/DiamondLightSource/ViSR/issues/4#issuecomment-2766099774
# NOTE: y is inverted
top_left = (-2, 3.7)
bottom_right = (4.3, 7.2)
STAGE_Z_CONSTANT = 0.01


class SpectrumRangeError(ValueError):
    pass


class ColorSpectra(TypedDict):
    red: tuple[float, float]
    green: tuple[float, float]
    blue: tuple[float, float]


class SpectrumChecker:
    def __init__(self, ranges: ColorSpectra):
        self.ranges = ranges
        self._validate_ranges()

    def _validate_ranges(self) -> None:
        # Extract ranges
        red_start, red_stop = self.ranges["red"]
        green_start, green_stop = self.ranges["green"]
        blue_start, blue_stop = self.ranges["blue"]

        # Ensure they are floats
        if not all(
            isinstance(x, float)
            for x in [
                red_start,
                red_stop,
                green_start,
                green_stop,
                blue_start,
                blue_stop,
            ]
        ):
            raise TypeError("All spectrum values must be floats.")

        # Check for non-overlapping intervals
        intervals = sorted(
            [
                (red_start, red_stop),
                (green_start, green_stop),
                (blue_start, blue_stop),
            ]
        )

        for (start1, stop1), (start2, stop2) in zip(
            intervals, intervals[1:], strict=False
        ):
            if start2 < stop1:
                raise SpectrumRangeError(
                    f"Overlapping spectra: ({start1}, {stop1}) and ({start2}, {stop2})"
                )

    def __repr__(self):
        return f"SpectrumChecker(ranges={self.ranges})"


def spectrum_checker_from_bounds(start: float, stop: float) -> SpectrumChecker:
    if not isinstance(start, float) or not isinstance(stop, float):
        raise TypeError("start and stop must be floats.")
    if start >= stop:
        raise ValueError(f"start ({start}) must be less than stop ({stop})")
    # Divide into 10 equal parts
    points = np.linspace(start, stop, 11)
    ranges = ColorSpectra(
        red=(points[2], points[3]),
        green=(points[5], points[6]),
        blue=(points[8], points[9]),
    )
    return SpectrumChecker(ranges)


VISR_RGB = spectrum_checker_from_bounds(top_left[0], bottom_right[0])


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
        "color_rois": VISR_RGB.ranges,
        "hints": {},
    }
    _md.update(metadata or {})

    @attach_data_session_metadata_decorator()
    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md=_md)
    def inner_plan():
        yield from bps.abs_set(sample_stage.z, STAGE_Z_CONSTANT)
        # yield from bps.prepare(manta, TriggerInfo(livetime=0.2, number_of_triggers=1))
        yield from bps.prepare(manta, TriggerInfo(livetime=0.2, number_of_events=1))
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
