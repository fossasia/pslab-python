"""Objects related to the PSLab's digital input channels."""

import numpy as np

DIGITAL_INPUTS = ("LA1", "LA2", "LA3", "LA4", "RES", "EXT", "FRQ")

DIGITAL_OUTPUTS = ("SQ1", "SQ2", "SQ3", "SQ4")

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
    name : {"LA1", "LA2", "LA3", "LA4", "RES", "FRQ"}
        Name of the digital channel to model.

    Attributes
    ----------
    name : str
        One of {"LA1", "LA2", "LA3", "LA4", "RES", "FRQ"}.
    number : int
        Number used to refer to this channel in the firmware.
    datatype : str
        Either "int" or "long", depending on if a 16 or 32-bit counter is used
        to capture timestamps for this channel.
    events_in_buffer : int
        Number of logic events detected on this channel, the timestamps of
        which are currently being held in the device's ADC buffer.
    buffer_idx : Union[int, None]
        Location in the device's ADC buffer where the events are stored. None
        if no events captured by this channel are currently held in the buffer.
    """

    def __init__(self, name: str):
        self.name = name
        self.number = DIGITAL_INPUTS.index(self.name)
        self.datatype = "long"
        self.events_in_buffer = 0
        self.buffer_idx = None
        self._logic_mode = MODES["any"]

    @property
    def logic_mode(self) -> str:
        """str: Type of logic event which should be captured on this channel.

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


class DigitalOutput:
    """Model of the PSLab's digital outputs.

    Parameters
    ----------
    name : {'SQ1', 'SQ2', 'SQ3', 'SQ4'}
        Name of the digital output pin represented by the instance.
    """

    def __init__(self, name: str):
        self._name = name
        self._state = "LOW"
        self._duty_cycle = 0
        self.phase = 0
        self.remapped = False

    @property
    def name(self) -> str:
        """str: Name of this pin."""
        return self._name

    @name.setter
    def name(self, value):
        if value in DIGITAL_OUTPUTS:
            self._name = value
        else:
            e = f"Invalid digital output {value}. Choose one of {DIGITAL_OUTPUTS}."
            raise ValueError(e)

    @property
    def state(self) -> str:
        """str: State of the digital output. Can be 'HIGH', 'LOW', or 'PWM'."""
        return self._state

    @property
    def duty_cycle(self) -> float:
        """float: Duty cycle of the PWM signal on this pin."""
        return self._duty_cycle

    @duty_cycle.setter
    def duty_cycle(self, value: float):
        if value == 0:
            self._state = "LOW"
        elif value < 1:
            self._state = "PWM"
        elif value == 1:
            self._state = "HIGH"
        else:
            raise ValueError("Duty cycle must be in range [0, 1].")

        self._duty_cycle = value

    @property
    def state_mask(self) -> int:
        """int: State mask for this pin.

        The state mask is used in the DOUT->SET_STATE command to set the
        digital output pins HIGH or LOW. For example:

            0x10 | 1 << 0 | 0x40 | 0 << 2 | 0x80 | 1 << 3

        would set SQ1 and SQ4 HIGH, SQ3 LOW, and leave SQ2 unchanged.
        """
        if self.name == "SQ1":
            return 0x10
        elif self.name == "SQ2":
            return 0x20
        elif self.name == "SQ3":
            return 0x40
        elif self.name == "SQ4":
            return 0x80

    @property
    def reference_clock_map(self) -> int:
        """int: Reference clock map value for this pin.

        The reference clock map is used in the WAVEGEN->MAP_REFERENCE command
        to map a digital output pin directly to the interal oscillator. This
        can be used to achieve very high frequencies, with the caveat that
        the only frequencies available are quotients of 128 MHz and powers of
        2 up to 15. For example, sending (2 | 4) followed by 3 outputs
        128 / (1 << 3) = 16 MHz on SQ2 and SQ3.
        """
        if self.name == "SQ1":
            return 1
        elif self.name == "SQ2":
            return 2
        elif self.name == "SQ3":
            return 4
        elif self.name == "SQ4":
            return 8
