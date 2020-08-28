import time
from collections import OrderedDict
from typing import List

import numpy as np

import PSL.commands_proto as CP
from PSL import digital_channel, packet_handler

CLOCK_RATE = 64e6

PRESCALERS = {
    0: 1,
    1: 8,
    2: 64,
    3: 254,
}


class LogicAnalyzer:
    def __init__(self, device: packet_handler.Handler = None):
        self.H = device
        self._device = device
        self._channels = {
            d: digital_channel.DigitalInput(d) for d in digital_channel.DIGITAL_INPUTS
        }
        self._trigger_channel = self._channels["ID1"]
        self.trigger_mode = "disabled"
        self._trigger_mode = 0
        self.prescaler = 0
        self._channel_one_map = "ID1"
        self._channel_two_map = "ID2"

        self.digital_channel_names = digital_channel.digital_channel_names
        # This array of four instances of digital_channel is used to store data retrieved from the
        # logic analyzer section of the device.  It also contains methods to generate plottable data
        # from the original timestamp arrays.
        self.dchans = [digital_channel.digital_channel(a) for a in range(4)]

    def __calcDChan__(self, name):
        """accepts a string represention of a digital input ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
        and returns a corresponding number
        """

        if name in self.digital_channel_names:
            return self.digital_channel_names.index(name)
        else:
            # self.__print__('invalid channel', name, ' , selecting ID1 instead ')
            return 0

    def get_high_freq(self, channel: str):
        """
        retrieves the frequency of the signal connected to ID1. for frequencies > 1MHz
        also good for lower frequencies, but avoid using it since
        the oscilloscope cannot be used simultaneously due to hardware limitations.

        The input frequency is fed to a 32 bit counter for a period of 100mS.
        The value of the counter at the end of 100mS is used to calculate the frequency.

        see :ref:`freq_video`


        .. seealso:: :func:`get_freq`

        .. tabularcolumns:: |p{3cm}|p{11cm}|

        ==============  ============================================================================================
        **Arguments**
        ==============  ============================================================================================
        pin             The input pin to measure frequency from : ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
        ==============  ============================================================================================

        :return: frequency
        """
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.GET_ALTERNATE_HIGH_FREQUENCY)
        self._device.send_byte(self._channels[channel].number)
        scale = self._device.get_byte()
        counter_value = self._device.get_long()
        self._device.get_ack()

        return scale * counter_value / 1e-1  # 100 ms sampling

    def get_freq(self, channel: str, timeout: float = 1):
        """
		Frequency measurement on IDx.
		Measures time taken for 16 rising edges of input signal.
		returns the frequency in Hertz

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		channel         The input to measure frequency from. ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		timeout         This is a blocking call which will wait for one full wavelength before returning the
						calculated frequency.
						Use the timeout option if you're unsure of the input signal.
						returns 0 if timed out
		==============  ============================================================================================

		:return float: frequency


		.. _timing_example:

			* connect SQR1 to ID1

			>>> I.sqr1(4000,25)
			>>> self.__print__(I.get_freq('ID1'))
			4000.0
			>>> self.__print__(I.r2r_time('ID1'))
			#time between successive rising edges
			0.00025
			>>> self.__print__(I.f2f_time('ID1'))
			#time between successive falling edges
			0.00025
			>>> self.__print__(I.pulse_time('ID1'))
			#may detect a low pulse, or a high pulse. Whichever comes first
			6.25e-05
			>>> I.duty_cycle('ID1')
			#returns wavelength, high time
			(0.00025,6.25e-05)

		"""
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.GET_FREQUENCY)
        self._device.send_int(int(timeout * CLOCK_RATE) >> 16)
        self._device.send_byte(self._channels[channel].number)
        self._device.wait_for_data(timeout)

        buffer_overflow_or_timeout = self._device.get_byte()
        counter_diff = np.diff([self._device.get_long() for a in range(2)])[0]
        self._device.get_ack()
        rising_edges = 16
        frequency = rising_edges * CLOCK_RATE / counter_diff

        if buffer_overflow_or_timeout:
            return 0

        return frequency

    def MeasureInterval(self, channel1, channel2, edge1, edge2, timeout=0.1):
        """
		Measures time intervals between two logic level changes on any two digital inputs(both can be the same)

		For example, one can measure the time interval between the occurence of a rising edge on ID1, and a falling edge on ID3.
		If the returned time is negative, it simply means that the event corresponding to channel2 occurred first.

		returns the calculated time


		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		channel1        The input pin to measure first logic level change
		channel2        The input pin to measure second logic level change
						 -['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		edge1           The type of level change to detect in order to start the timer
							* 'rising'
							* 'falling'
							* 'four rising edges'
		edge2           The type of level change to detect in order to stop the timer
							* 'rising'
							* 'falling'
							* 'four rising edges'
		timeout         Use the timeout option if you're unsure of the input signal time period.
						returns -1 if timed out
		==============  ============================================================================================

		:return : time

		.. seealso:: timing_example_


		"""
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.INTERVAL_MEASUREMENTS)
        timeout_msb = int((timeout * 64e6)) >> 16
        self.H.__sendInt__(timeout_msb)

        self.H.__sendByte__(self.__calcDChan__(channel1) | (self.__calcDChan__(channel2) << 4))

        params = 0
        if edge1 == 'rising':
            params |= 3
        elif edge1 == 'falling':
            params |= 2
        else:
            params |= 4

        if edge2 == 'rising':
            params |= 3 << 3
        elif edge2 == 'falling':
            params |= 2 << 3
        else:
            params |= 4 << 3

        self.H.__sendByte__(params)
        A = self.H.__getLong__()
        B = self.H.__getLong__()
        tmt = self.H.__getInt__()
        self.H.__get_ack__()
        # self.__print__(A,B)
        if (tmt >= timeout_msb or B == 0): return np.NaN
        rtime = lambda t: t / 64e6
        return rtime(B - A + 20)

    def DutyCycle(self, channel='ID1', timeout=1.):
        """
		duty cycle measurement on channel

		returns wavelength(seconds), and length of first half of pulse(high time)

		low time = (wavelength - high time)

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ==============================================================================================
		**Arguments**
		==============  ==============================================================================================
		channel         The input pin to measure wavelength and high time.['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		timeout         Use the timeout option if you're unsure of the input signal time period.
						returns 0 if timed out
		==============  ==============================================================================================

		:return : wavelength,duty cycle

		.. seealso:: timing_example_

		"""
        x, y = self.MeasureMultipleDigitalEdges(channel, channel, 'rising', 'falling', 2, 2, timeout, zero=True)
        if x is not None and y is not None:  # Both timers registered something. did not timeout
            if y[0] > 0:  # rising edge occured first
                dt = [y[0], x[1]]
            else:  # falling edge occured first
                if y[1] > x[1]:
                    return -1, -1  # Edge dropped. return False
                dt = [y[1], x[1]]
            # self.__print__(x,y,dt)
            params = dt[1], dt[0] / dt[1]
            # if params[1] > 0.5:
            #     self.__print__(x, y, dt)
            return params
        else:
            return -1, -1

    def PulseTime(self, channel='ID1', PulseType='LOW', timeout=0.1):
        """
		duty cycle measurement on channel

		returns wavelength(seconds), and length of first half of pulse(high time)

		low time = (wavelength - high time)

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ==============================================================================================
		**Arguments**
		==============  ==============================================================================================
		channel         The input pin to measure wavelength and high time.['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		PulseType		Type of pulse to detect. May be 'HIGH' or 'LOW'
		timeout         Use the timeout option if you're unsure of the input signal time period.
						returns 0 if timed out
		==============  ==============================================================================================

		:return : pulse width

		.. seealso:: timing_example_

		"""
        x, y = self.MeasureMultipleDigitalEdges(channel, channel, 'rising', 'falling', 2, 2, timeout, zero=True)
        if x is not None and y is not None:  # Both timers registered something. did not timeout
            if y[0] > 0:  # rising edge occured first
                if PulseType == 'HIGH':
                    return y[0]
                elif PulseType == 'LOW':
                    return x[1] - y[0]
            else:  # falling edge occured first
                if PulseType == 'HIGH':
                    return y[1]
                elif PulseType == 'LOW':
                    return abs(y[0])
        return -1, -1

    def MeasureMultipleDigitalEdges(self, channel1, channel2, edgeType1, edgeType2, points1, points2, timeout=0.1,
                                    **kwargs):
        """
		Measures a set of timestamped logic level changes(Type can be selected) from two different digital inputs.

		Example
			Aim : Calculate value of gravity using time of flight.
			The setup involves a small metal nut attached to an electromagnet powered via SQ1.
			When SQ1 is turned off, the set up is designed to make the nut fall through two
			different light barriers(LED,detector pairs that show a logic change when an object gets in the middle)
			placed at known distances from the initial position.

			one can measure the timestamps for rising edges on ID1 ,and ID2 to determine the speed, and then obtain value of g


		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		channel1        The input pin to measure first logic level change
		channel2        The input pin to measure second logic level change
						 -['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		edgeType1       The type of level change that should be recorded
							* 'rising'
							* 'falling'
							* 'four rising edges' [default]
		edgeType2       The type of level change that should be recorded
							* 'rising'
							* 'falling'
							* 'four rising edges'
		points1			Number of data points to obtain for input 1 (Max 4)
		points2			Number of data points to obtain for input 2 (Max 4)
		timeout         Use the timeout option if you're unsure of the input signal time period.
						returns -1 if timed out
		**kwargs
		  SQ1			set the state of SQR1 output(LOW or HIGH) and then start the timer.  eg. SQR1='LOW'
		  zero			subtract the timestamp of the first point from all the others before returning. default:True
		==============  ============================================================================================

		:return : time

		.. seealso:: timing_example_


		"""
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.TIMING_MEASUREMENTS)
        timeout_msb = int((timeout * 64e6)) >> 16
        # print ('timeout',timeout_msb)
        self.H.__sendInt__(timeout_msb)
        self.H.__sendByte__(self.__calcDChan__(channel1) | (self.__calcDChan__(channel2) << 4))
        params = 0
        if edgeType1 == 'rising':
            params |= 3
        elif edgeType1 == 'falling':
            params |= 2
        else:
            params |= 4

        if edgeType2 == 'rising':
            params |= 3 << 3
        elif edgeType2 == 'falling':
            params |= 2 << 3
        else:
            params |= 4 << 3

        if ('SQR1' in kwargs):  # User wants to toggle SQ1 before starting the timer
            params |= (1 << 6)
            if kwargs['SQR1'] == 'HIGH': params |= (1 << 7)
        self.H.__sendByte__(params)
        if points1 > 4: points1 = 4
        if points2 > 4: points2 = 4
        self.H.__sendByte__(points1 | (points2 << 4))  # Number of points to fetch from either channel

        self.H.waitForData(timeout)

        A = np.array([self.H.__getLong__() for a in range(points1)])
        B = np.array([self.H.__getLong__() for a in range(points2)])
        tmt = self.H.__getInt__()
        self.H.__get_ack__()
        # print(A,B)
        if (tmt >= timeout_msb): return None, None
        rtime = lambda t: t / 64e6
        if (kwargs.get('zero', True)):  # User wants set a reference timestamp
            return rtime(A - A[0]), rtime(B - A[0])
        else:
            return rtime(A), rtime(B)

    def capture(
        self,
        channels: int,
        events: int = CP.MAX_SAMPLES // 4,
        timeout: float = None,
        modes: List[str] = 4 * ["every edge"],
        e2e_time: float = 0,
        block: bool = True,
    ):
        self.clear_buffer(0, CP.MAX_SAMPLES)
        self._invalidate_buffer()
        self._configure_trigger(channels)
        modes = [digital_channel.MODES[m] for m in modes]
        old_progress = self.get_progress()

        for e, c in enumerate(
            [self._channel_one_map, self._channel_two_map, "ID3", "ID4"][:channels]
        ):
            c = self._channels[c]
            c.events_in_buffer = events
            c.datatype = "long" if channels < 3 else "int"
            c.buffer_idx = 2500 * e * (1 if c.datatype == "int" else 2)
            c.logic_mode = modes[e]

        if channels == 1:
            self._capture_one()
        elif channels == 2:
            self._capture_two()
        elif channels == 4:
            self._capture_four(e2e_time)

        if block:
            start = time.time()
            self._wait_for_progress(old_progress)

            while self.get_progress() < events:
                if timeout is not None:
                    if time.time() - start >= timeout:
                        break
        else:
            return

        return self.fetch_data()

    def _capture_one(self):
        self._channels[self._channel_one_map].prescaler = 0
        self._device.send_byte(CP.TIMING)
        self._device.send_byte(CP.START_ALTERNATE_ONE_CHAN_LA)
        self._device.send_int(CP.MAX_SAMPLES // 4)
        self._device.send_byte(
            (self._channels[self._channel_one_map].number << 4)
            | self._channels[self._channel_one_map].logic_mode
        )
        self._device.send_byte(
            (self._channels[self._channel_one_map].number << 4) | self._trigger_mode
        )
        self._device.get_ack()

    def _capture_two(self):
        for c in list(self._channels.values())[:2]:
            c.prescaler = 0

        self._device.send_byte(CP.TIMING)
        self._device.send_byte(CP.START_TWO_CHAN_LA)
        self._device.send_int(CP.MAX_SAMPLES // 4)
        self._device.send_byte((self._trigger_channel.number << 4) | self._trigger_mode)
        self._device.send_byte(
            self._channels[self._channel_one_map].logic_mode
            | (self._channels[self._channel_two_map].logic_mode << 4)
        )
        self._device.send_byte(
            self._channels[self._channel_one_map].number
            | (self._channels[self._channel_two_map].number << 4)
        )
        self._device.get_ack()

    def _capture_four(self, e2e_time: float):
        rollover_time = (2 ** 16 - 1) / CLOCK_RATE
        if e2e_time > rollover_time * PRESCALERS[3]:
            raise ValueError("Timegap too big for four channel mode.")
        elif e2e_time > rollover_time * PRESCALERS[2]:
            self.prescaler = 3
        elif e2e_time > rollover_time * PRESCALERS[1]:
            self.prescaler = 2
        elif e2e_time > rollover_time:
            self.prescaler = 1
        else:
            self.prescaler = 0

        self._device.send_byte(CP.TIMING)
        self._device.send_byte(CP.START_FOUR_CHAN_LA)
        self._device.send_int(CP.MAX_SAMPLES // 4)
        self._device.send_int(
            self._channels["ID1"].logic_mode
            | (self._channels["ID2"].logic_mode << 4)
            | (self._channels["ID3"].logic_mode << 8)
            | (self._channels["ID4"].logic_mode << 12)
        )
        self._device.send_byte(self.prescaler)

        try:
            trigger = {0: 4, 1: 8, 2: 16,}[
                self._trigger_channel.number
            ] | self._trigger_mode
        except KeyError:
            e = "Triggering is only possible on ID1, ID2, or ID3."
            if self._trigger_channel.number == 3:
                raise NotImplementedError(e)
            else:
                raise TypeError(e)

        self._device.send_byte(trigger)
        self._device.get_ack()

    def fetch_data(self):
        counter_values = []
        channels = list(
            OrderedDict.fromkeys(
                [self._channel_one_map, self._channel_two_map, "ID3", "ID4"]
            )
        )
        for c in channels:
            c = self._channels[c]

            if c.events_in_buffer:
                if c.datatype == "long":
                    counter_values.append(self._fetch_long(c))
                else:
                    counter_values.append(self._fetch_int(c))

        prescaler = [1 / 64, 1 / 8, 1.0, 4.0][self.prescaler]
        timestamps = [cv * prescaler for cv in counter_values]

        return timestamps

    def _fetch_long(self, channel: digital_channel.DigitalInput):
        # First half of each long is stored in the first 2500 buffer positions,
        # or positions 5001-7500 for channel two.
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.RETRIEVE_BUFFER)
        self._device.send_int(channel.buffer_idx)
        self._device.send_int(channel.events_in_buffer)
        lsb = self._device.interface.read(channel.events_in_buffer * 2)
        self._device.get_ack()

        # Second half of each long is stored in positions 2501-5000,
        # or positions 7501-10000 for channel two.
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.RETRIEVE_BUFFER)
        self._device.send_int(channel.buffer_idx + CP.MAX_SAMPLES // 4)
        self._device.send_int(channel.events_in_buffer)
        msb = self._device.interface.read(channel.events_in_buffer * 2)
        self._device.get_ack()

        # Interleave byte arrays.
        lsb = [lsb[a * 2 : a * 2 + 2] for a in range(len(lsb) // 2)]
        msb = [msb[a * 2 : a * 2 + 2] for a in range(len(msb) // 2)]
        raw = [l + m for m, l in zip(msb, lsb)]

        raw_timestamps = [
            CP.Integer.unpack(raw[a])[0] for a in range(channel.events_in_buffer)
        ]
        raw_timestamps = np.array(raw_timestamps)
        raw_timestamps = np.trim_zeros(raw_timestamps)

        return raw_timestamps

    def _fetch_int(self, channel: digital_channel.DigitalInput):
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.RETRIEVE_BUFFER)
        self._device.send_int(channel.buffer_idx)
        self._device.send_int(channel.events_in_buffer)
        raw = self._device.interface.read(channel.events_in_buffer * 2)
        self._device.get_ack()

        raw_timestamps = [
            CP.ShortInt.unpack(raw[a * 2 : a * 2 + 2])[0]
            for a in range(channel.events_in_buffer)
        ]
        raw_timestamps = np.array(raw_timestamps)
        raw_timestamps = np.trim_zeros(raw_timestamps)

        for i, diff in enumerate(np.diff(raw_timestamps)):
            if diff <= 0:  # Counter has rolled over.
                raw_timestamps[i + 1 :] += 2 ** 16 - 1

        return raw_timestamps

    def get_progress(self):
        active_channels = []
        for c in self._channels.values():
            if c.events_in_buffer:
                active_channels.append(c)

        p = CP.MAX_SAMPLES // 4
        progress = self._get_initial_states_and_progress()[1]
        for i in range(len(active_channels)):
            p = min(progress[i], p)

        return p

    def get_initial_states(self):
        return self._get_initial_states_and_progress()[0]

    def get_xy(self, timestamps: np.ndarray):
        xy = []

        for e, c in enumerate(
            [self._channel_one_map, self._channel_two_map, "ID3", "ID4"][
                : len(timestamps)
            ]
        ):
            c = self._channels[c]
            if c.events_in_buffer:
                x, y = c.xy(self.get_initial_states()[c.name], timestamps[e])
                xy.append(x)
                xy.append(y)

        return xy

    def _get_initial_states_and_progress(self):
        self._device.send_byte(CP.TIMING)
        self._device.send_byte(CP.GET_INITIAL_DIGITAL_STATES)
        initial = self._device.get_int()
        progress = [0, 0, 0, 0]
        progress[0] = (self._device.get_int() - initial) // 2
        progress[1] = (self._device.get_int() - initial) // 2 - CP.MAX_SAMPLES // 4
        progress[2] = (self._device.get_int() - initial) // 2 - 2 * CP.MAX_SAMPLES // 4
        progress[3] = (self._device.get_int() - initial) // 2 - 3 * CP.MAX_SAMPLES // 4
        s = self._device.get_byte()
        initial_states = {
            "ID1": (s & 1 != 0),
            "ID2": (s & 2 != 0),
            "ID3": (s & 4 != 0),
            "ID4": (s & 8 != 0),
        }
        self._device.get_byte()  # INITIAL_DIGITAL_STATES_ERR
        self._device.get_ack()

        for e, i in enumerate(progress):
            if i == 0:
                progress[e] = CP.MAX_SAMPLES // 4
            elif i < 0:
                progress[e] = 0

        return initial_states, progress

    def _wait_for_progress(
        self, old_progress: int = CP.MAX_SAMPLES // 4, timeout: float = None
    ):
        """Wait for GET_INITIAL_DIGITAL_STATES to reset.

        Until the first event is detected, GET_INITIAL_DIGITAL_STATES returns
        old progress.
        """
        timeout = 0.1 if timeout is None else timeout
        start_time = time.time()
        while self.get_progress() == old_progress:
            if time.time() - start_time >= timeout:
                break
        return

    def configure_trigger(self, trigger_channel: str, trigger_mode: str):
        self._trigger_channel = self._channels[trigger_channel]
        self.trigger_mode = trigger_mode

    def _configure_trigger(self, channels: int):
        # For some reason firmware uses different values for trigger_mode
        # depending on number of channels.
        if channels == 1:
            self._trigger_mode = {"disabled": 0, "falling": 2, "rising": 3,}[
                self.trigger_mode
            ]
        elif channels == 2:
            self._trigger_mode = {"disabled": 0, "falling": 3, "rising": 1,}[
                self.trigger_mode
            ]
        elif channels == 4:
            self._trigger_mode = {"disabled": 0, "falling": 1, "rising": 3,}[
                self.trigger_mode
            ]

    def stop(self):
        """
		Stop any running logic analyzer function
		"""
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.STOP_LA)
        self.H.__get_ack__()

    def get_states(self):
        """
		gets the state of the digital inputs. returns dictionary with keys 'ID1','ID2','ID3','ID4'

		>>> self.__print__(get_states())
		{'ID1': True, 'ID2': True, 'ID3': True, 'ID4': False}

		"""
        self.H.__sendByte__(CP.DIN)
        self.H.__sendByte__(CP.GET_STATES)
        s = self.H.__getByte__()
        self.H.__get_ack__()
        return {
            "ID1": (s & 1 != 0),
            "ID2": (s & 2 != 0),
            "ID3": (s & 4 != 0),
            "ID4": (s & 8 != 0),
        }

    def countPulses(self, channel='SEN'):
        """

		Count pulses on a digital input. Retrieve total pulses using readPulseCount

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		channel         The input pin to measure rising edges on : ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		==============  ============================================================================================
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.START_COUNTING)
        self.H.__sendByte__(self.__calcDChan__(channel))
        self.H.__get_ack__()

    def readPulseCount(self):
        """

		Read pulses counted using a digital input. Call countPulses before using this.

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		==============  ============================================================================================
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.FETCH_COUNT)
        count = self.H.__getInt__()
        self.H.__get_ack__()
        return count

    def clear_buffer(self, starting_position, total_points):
        """
		clears a section of the ADC hardware buffer
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.CLEAR_BUFFER)
        self.H.__sendInt__(starting_position)
        self.H.__sendInt__(total_points)
        self.H.__get_ack__()

    def _invalidate_buffer(self):
        for c in self._channels.values():
            c.events_in_buffer = 0
            c.buffer_idx = None
