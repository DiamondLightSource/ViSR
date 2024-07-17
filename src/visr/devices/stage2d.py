from ophyd_async.epics.signal import epics_signal_rw


class Stage2d:
    def __init__(self, prefix: str, name: str = "") -> None:
        self.x = epics_signal_rw(name + "_x", prefix + ":x")
        self.y = epics_signal_rw(name + "_y", prefix + ":y")
        self.prefix = prefix
        super().__init__(name)
