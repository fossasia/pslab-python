import numpy as np

DIGITAL_INPUTS = ('ID1', 'ID2', 'ID3', 'ID4', 'SEN', 'EXT', 'CNTR')
digital_channel_names = DIGITAL_INPUTS

MODES = {
    "every sixteenth rising edge": 5,
    "every fourth rising edge": 4,
    "every rising edge": 3,
    "every falling edge": 2,
    "every edge": 1,
    "disabled": 0,
}


class DigitalInput:
    def __init__(self, name: str):
        self.name = name
        self.number = DIGITAL_INPUTS.index(self.name)
        self.datatype = "long"
        self.events_in_buffer = 0
        self.buffer_idx = None
        self.logic_mode = MODES["every edge"]

    def xy(self, initial_state: bool, timestamps: np.ndarray):
        x = np.repeat(timestamps, 3)
        x = np.insert(x, 0, 0)
        x[0] = 0
        y = np.zeros(len(x))

        if self.logic_mode == MODES["disabled"]:
            y[:] = initial_state
        elif self.logic_mode == MODES["every edge"]:
            y[0] = initial_state
            for i in range(1, len(x), 3):
                y[i] = y[i - 1]  # Value before this timestamp.
                y[i + 1] = not y[i]  # Value at this timestamp.
                y[i + 2] = y[i + 1]  # Value leaving this timetamp.
        elif self.logic_mode == MODES["every falling edge"]:
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
