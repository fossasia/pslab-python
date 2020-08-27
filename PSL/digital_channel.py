import numpy as np

DIGITAL_INPUTS = ('ID1', 'ID2', 'ID3', 'ID4', 'SEN', 'EXT', 'CNTR')
digital_channel_names = DIGITAL_INPUTS

MODES = {
    "every_sixteenth_rising_edge": 5,
    "every_fourth_rising_edge": 4,
    "every_rising_edge": 3,
    "every_falling_edge": 2,
    "every_edge": 1,
    "disabled": 0,
}


class DigitalInput:
    def __init__(self, name: str):
        self.name = name
        self.number = DIGITAL_INPUTS.index(self.name)
        self.datatype = "long"
        self.samples_in_buffer = 0
        self.buffer_idx = None
        self.logic_mode = MODES["every_edge"]

    def xy(self, initial_state: bool, timestamps: np.ndarray):
        x = np.repeat(timestamps, 3)
        x = np.insert(x, 0, 0)
        x[0] = 0
        y = np.zeros(len(x))

        if self.logic_mode == MODES["disabled"]:
            y[:] = initial_state
        elif self.logic_mode == MODES["every_edge"]:
            y[0] = initial_state
            for i in range(1, len(x), 3):
                y[i] = y[i - 1]  # Value before this timestamp.
                y[i + 1] = not y[i]  # Value at this timestamp.
                y[i + 2] = y[i + 1]  # Value leaving this timetamp.
        elif self.logic_mode == MODES["every_falling_edge"]:
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


class digital_channel:
    EVERY_SIXTEENTH_RISING_EDGE = 5
    EVERY_FOURTH_RISING_EDGE = 4
    EVERY_RISING_EDGE = 3
    EVERY_FALLING_EDGE = 2
    EVERY_EDGE = 1
    DISABLED = 0

    def __init__(self, a):
        self.gain = 0
        self.channel_number = a
        self.digital_channel_names = digital_channel_names
        self.name = self.digital_channel_names[a]
        self.xaxis = np.zeros(20000)
        self.yaxis = np.zeros(20000)
        self.timestamps = np.zeros(10000)
        self.length = 100
        self.initial_state = 0
        self.prescaler = 0
        self.datatype = 'int'
        self.trigger = 0
        self.dlength = 0
        self.plot_length = 0
        self.maximum_time = 0
        self.maxT = 0
        self.initial_state_override = False
        self.mode = self.EVERY_EDGE

    def set_params(self, **keys):
        self.channel_number = keys.get('channel_number', self.channel_number)
        self.name = keys.get('name', 'ErrOr')

    def load_data(self, initial_state, timestamps):
        if self.initial_state_override:
            self.initial_state = (self.initial_state_override - 1) == 1
            self.initial_state_override = False
        else:
            self.initial_state = initial_state[self.name]
        self.timestamps = timestamps
        self.dlength = len(self.timestamps)
        # print('dchan.py',self.channel_number,self.name,initial_state,self.initial_state)
        self.timestamps = np.array(self.timestamps) * [1. / 64, 1. / 8, 1., 4.][self.prescaler]

        if self.dlength:
            self.maxT = self.timestamps[-1]
        else:
            self.maxT = 0

    def generate_axes(self):
        HIGH = 1  # (4-self.channel_number)*(3)
        LOW = 0  # HIGH - 2.5
        state = HIGH if self.initial_state else LOW

        if self.mode == self.DISABLED:
            self.xaxis[0] = 0
            self.yaxis[0] = state
            n = 1
            self.plot_length = n

        elif self.mode == self.EVERY_EDGE:
            self.xaxis[0] = 0
            self.yaxis[0] = state
            n = 1
            for a in range(self.dlength):
                self.xaxis[n] = self.timestamps[a]
                self.yaxis[n] = state
                state = LOW if state == HIGH else HIGH
                n += 1
                self.xaxis[n] = self.timestamps[a]
                self.yaxis[n] = state
                n += 1

            self.plot_length = n

        elif self.mode == self.EVERY_FALLING_EDGE:
            self.xaxis[0] = 0
            self.yaxis[0] = HIGH
            n = 1
            for a in range(self.dlength):
                self.xaxis[n] = self.timestamps[a]
                self.yaxis[n] = HIGH
                n += 1
                self.xaxis[n] = self.timestamps[a]
                self.yaxis[n] = LOW
                n += 1
                self.xaxis[n] = self.timestamps[a]
                self.yaxis[n] = HIGH
                n += 1
            state = HIGH
            self.plot_length = n

        elif self.mode == self.EVERY_RISING_EDGE or self.mode == self.EVERY_FOURTH_RISING_EDGE or self.mode == self.EVERY_SIXTEENTH_RISING_EDGE:
            self.xaxis[0] = 0
            self.yaxis[0] = LOW
            n = 1
            for a in range(self.dlength):
                self.xaxis[n] = self.timestamps[a]
                self.yaxis[n] = LOW
                n += 1
                self.xaxis[n] = self.timestamps[a]
                self.yaxis[n] = HIGH
                n += 1
                self.xaxis[n] = self.timestamps[a]
                self.yaxis[n] = LOW
                n += 1
            state = LOW
            self.plot_length = n
            # print(self.channel_number,self.dlength,self.mode,len(self.yaxis),self.plot_length)

    def get_xaxis(self):
        return self.xaxis[:self.plot_length]

    def get_yaxis(self):
        return self.yaxis[:self.plot_length]
