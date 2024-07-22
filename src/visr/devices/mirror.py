from ophyd_async.device import Device
from ophyd_async.epics import Readable
from ophyd_async.epics.signal import epics_signal_rw


class Mirror(Device, Readable):
    def __init__(self, prefix: str, name: str = "") -> None:
        self.signal = epics_signal_rw(prefix, name="signal")
        self.prefix = prefix
        super().__init__(name)
        self._mirror = None
