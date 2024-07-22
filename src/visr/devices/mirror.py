from ophyd_async.epics.motion import Motor


class Mirror(Motor):
    def __init__(self, prefix: str, name: str = "") -> None:
        self.prefix = prefix
        super().__init__(name)
        self._mirror = None
