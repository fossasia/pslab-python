"""Objects related to the PSLab's digital input channels."""

import numpy as np

DIGITAL_INPUTS = ("LA1", "LA2", "LA3", "LA4", "RES", "EXT", "FRQ")

MODES = {
    "sixteen rising": 5,
    "four rising": 4,
    "rising": 3,
    "falling": 2,
    "any": 1,
    "disabled": 0,
}


class DigitalInput:
    """Model of the PSLab's digital inputs.

    Parameters
    ----------
    name : {"LA1", "LA2", "LA3", "LA4", "RES", "EXT", "FRQ"}
        Name of the digital channel to model.

    Attributes
    ----------
    name : str
        One of {"LA1", "LA2", "LA3", "LA4", "RES", "EXT", "FRQ"}.
    number : int
        Number used to refer to this channel in the firmware.
    datatype : str
        Either "int" or "long", depending on if a 16 or 32-bit counter is used to
        capture timestamps for this channel.
    events_in_buffer : int
        Number of logic events detected on this channel, the timestamps of which are
        currently being held in the device's ADC buffer.
    buffer_idx : Union[int, None]
        Location in the device's ADC buffer where the events are stored. None if no
        events captured by this channel are currently held in the buffer.
    logic_mode
    """

    def __init__(self, name: str):
        self.name = name
        self.number = DIGITAL_INPUTS.index(self.name)
        self.datatype = "long"
        self.events_in_buffer = 0
        self._events_in_buffer = 0
        self.buffer_idx = None
        self._logic_mode = MODES["any"]

    @property
    def logic_mode(self) -> str:
        """Get or set the type of logic event which should be captured on this channel.

        The options are:
                any:            Capture every edge.
                rising:         Capture every rising edge.
                falling:        Capture every falling edge.
                four rising:    Capture every fourth rising edge.
                sixteen rising: Capture every fourth rising edge.
        """
        return {v: k for k, v in MODES.items()}[self._logic_mode]

    def _get_xy(self, initial_state: bool, timestamps: np.ndarray):
        x = np.repeat(timestamps, 3)
        x = np.insert(x, 0, 0)
        x[0] = 0
        y = np.array(len(x) * [False])

        if self.logic_mode == "any":
            y[0] = initial_state
            for i in range(1, len(x), 3):
                y[i] = y[i - 1]  # Value before this timestamp.
                y[i + 1] = not y[i]  # Value at this timestamp.
                y[i + 2] = y[i + 1]  # Value leaving this timetamp.
        elif self.logic_mode == "falling":
            y[0] = True
            for i in range(1, len(x), 3):
                y[i] = True  # Value before this timestamp.
                y[i + 1] = False  # Value at this timestamp.
                y[i + 2] = True  # Value leaving this timetamp.
        else:
            y[0] = False
            for i in range(1, len(x), 3):
                y[i] = False  # Value before this timestamp.
                y[i + 1] = True  # Value at this timestamp.
                y[i + 2] = False  # Value leaving this timetamp.

        return x, y
