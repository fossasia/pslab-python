"""Classes and functions related to the PSLab's logic analyzer instrument.

Example
-------
>>> from PSL.logic_analyzer import LogicAnalyzer
>>> la = LogicAnalyzer()
>>> t = la.capture(channels=2, events=1600, modes=["falling", "any"])
"""

import time
from collections import OrderedDict
from typing import Dict, List, Tuple, Union

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
    """Investigate digital signals on up to four channels simultaneously.

    Parameters
    ----------
    device : :class:`Handler`, optional
        Serial interface for communicating with the PSLab device. If not provided, a
        new one will be created.

    Attributes
    ----------
    trigger_channel : str
        See :meth:`configure_trigger`.
    trigger_mode : str
        See :meth:`configure_trigger`.
    """

    def __init__(self, device: packet_handler.Handler = None):
        self._device = packet_handler.Handler() if device is None else device
        self._channels = {
            d: digital_channel.DigitalInput(d) for d in digital_channel.DIGITAL_INPUTS
        }
        self.trigger_channel = "ID1"
        self._trigger_channel = self._channels["ID1"]
        self.trigger_mode = "disabled"
        self._trigger_mode = 0
        self._prescaler = 0
        self._channel_one_map = "ID1"
        self._channel_two_map = "ID2"

    def get_frequency(
        self, channel: str, simultaneous_oscilloscope: bool = False, timeout: float = 1
    ) -> float:
        """Measure the frequency of a signal.

        Parameters
        ----------
        channel : {"ID1", "ID2", "ID3", "ID4"}
            Name of the digital input channel in which to measure the frequency.
        simultaneous_oscilloscope: bool, optional
            Set this to True if you need to use the oscilloscope at the same time.
            Uses firmware instead of software to measure the frequency, which may fail
            and return 0. Will not give accurate results above 10 MHz. The default
            value is False.
        timeout : float, optional
            Timeout in seconds before cancelling measurement. The default value is
            1 second.

        Returns
        -------
        float
            The signal's frequency in Hz.
        """
        if simultaneous_oscilloscope:
            return self._get_frequency_firmware(channel, timeout)
        else:
            tmp = self._channel_one_map
            self._channel_one_map = channel
            t = self.capture(1, 2, modes=["sixteen rising"], timeout=timeout)[0]
            self._channel_one_map = tmp
            period = (t[1] - t[0]) * 1e-6 / 16
            frequency = period ** -1

            if frequency >= 1e7:
                frequency = self._get_high_frequency(channel)

            return frequency

    def _get_frequency_firmware(
        self, channel: str, timeout: float, retry: bool = True
    ) -> float:
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.GET_FREQUENCY)
        self._device.send_int(int(timeout * 64e6) >> 16)
        self._device.send_byte(self._channels[channel].number)
        self._device.wait_for_data(timeout)

        error = self._device.get_byte()
        t = [self._device.get_long() for a in range(2)]
        self._device.get_ack()
        edges = 16
        period = (t[1] - t[0]) / edges / CLOCK_RATE

        if error or period == 0:
            # Retry once.
            if retry:
                return self._get_frequency_firmware(channel, timeout, False)
            else:
                return 0
        else:
            return period ** -1

    def _get_high_frequency(self, channel: str) -> float:
        # The input frequency is fed to a 32 bit counter for a period of 100 ms. The
        # value of the counter at the end of 100 ms is used to calculate the frequency.
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.GET_ALTERNATE_HIGH_FREQUENCY)
        self._device.send_byte(self._channels[channel].number)
        scale = self._device.get_byte()
        counter_value = self._device.get_long()
        self._device.get_ack()

        return scale * counter_value / 1e-1  # 100 ms sampling

    def measure_interval(
        self, channels: List[str], modes: List[str], timeout: float = 1
    ) -> float:
        """Measure the time between two events.

        This method cannot be used at the same time as the oscilloscope.

        Parameters
        ----------
        channels : List[str]
            A pair of digital inputs, ID1, ID2, ID3, or ID4. Both can be the same.
        modes : List[str]
            Type of logic event to listen for on each channel. See
            :class:`DigitalInput` for available modes.
        timeout : float, optional
            Timeout in seconds before cancelling measurement. The default value is
            1 second.

        Returns
        -------
        float
            Time between events in microseconds. A negative value means that the event
            on the second channel happend first.
        """
        tmp_trigger = self._trigger_channel.name
        self.configure_trigger(channels[0], self.trigger_mode)
        tmp_map = self._channel_one_map, self._channel_two_map
        self._channel_one_map = channels[0]
        self._channel_two_map = channels[1]

        if channels[0] == channels[1]:
            # 34 edges contains 17 rising edges, i.e two
            # 'every sixteenth rising edge' events.
            t = self.capture(1, 34, modes=["any"], timeout=timeout)[0]
            initial = self.get_initial_states()[self._channel_one_map]
            t1 = self._get_first_event(t, modes[0], initial)

            if modes[0] == modes[1]:
                idx = 1 if modes[1] == "any" else 2
                initial = initial if idx == 2 else not initial
                t2 = self._get_first_event(t[idx:], modes[1], initial)
            else:
                t2 = self._get_first_event(t, modes[1], initial)
        else:
            t1, t2 = self.capture(2, 1, modes=modes, timeout=timeout)

            t1, t2 = t1[0], t2[0]

        self.configure_trigger(tmp_trigger, self.trigger_mode)
        self._channel_one_map = tmp_map[0]
        self._channel_two_map = tmp_map[1]

        return t2 - t1

    @staticmethod
    def _get_first_event(events: np.ndarray, mode: str, initial: bool) -> np.ndarray:
        if mode == "any":
            return events[0]
        elif mode == "rising":
            return events[int(initial)]
        elif mode == "falling":
            return events[int(not initial)]
        elif mode == "four rising":
            return events[initial::2][3]
        elif mode == "sixteen rising":
            return events[initial::2][15]

    def get_duty_cycle(self, channel: str, timeout: float = 1) -> Tuple[float]:
        """Measure duty cycle and wavelength.

        This method cannot be used at the same time as the oscilloscope.

        Parameters
        ----------
        channel : {"ID1", "ID2", "ID3", "ID4"}
            Digital input on which to measure.
        timeout : float, optional
            Timeout in seconds before cancelling measurement. The default value is
            1 second.

        Returns
        -------
        float, float
            Wavelength in microseconds and duty cycle as a value between 0 - 1.
        """
        tmp_trigger_mode = self.trigger_mode
        tmp_trigger_channel = self._trigger_channel.name
        self.configure_trigger(trigger_channel=channel, trigger_mode="rising")
        tmp_map = self._channel_one_map
        self._channel_one_map = channel
        t = self.capture(1, 2, modes=["any"], timeout=timeout)[0]
        self._channel_one_map = tmp_map
        self.configure_trigger(tmp_trigger_channel, tmp_trigger_mode)

        period = t[1]
        # First change is HIGH -> LOW since we trigger on rising.
        duty_cycle = t[0] / t[1]

        return period, duty_cycle

    def capture(
        self,
        channels: int,
        events: int = CP.MAX_SAMPLES // 4 - 1,
        timeout: float = None,
        modes: List[str] = 4 * ("any",),
        e2e_time: float = None,
        block: bool = True,
    ) -> Union[List[np.ndarray], None]:
        """Capture logic events.

        This method cannot be used at the same time as the oscilloscope.

        Parameters
        ----------
        channels : {1, 2, 3, 4}
            Number of channels to capture events on. Events will be captured on ID1,
            ID2, ID3, and ID4, in that order.
        events : int, optional
            Number of logic events to capture on each channel. The default and maximum
            value is 2499.
        timeout : float, optional
            Timeout in seconds before cancelling measurement. By default there is
            no timeout.
        modes : List[str], optional
            List of strings specifying the type of logic level change to capture on
            each channel. See :class:`DigitalInput` for available modes. The default
            value is ("any", "any", "any", "any").
        e2e_time : float, optional
            The maximum time between events in seconds. This is only required in three
            and four channel mode, which uses 16-bit counters as opposed to 32-bit
            counters which are used in one and two channel mode. The 16-bit counter
            normally rolls over after 1.024 milliseconds, so if the time between events
            is greater than that the timestamp calculations will be incorrect. By
            setting this to a value greater than 1.024 ms, the counter will be slowed
            down by a prescaler, which can extend the maximum allowed event-to-event
            time gap to up to 0.26 seconds. If the time gap is greater than that, three
            and four channel mode cannot be used. One and two channel mode supports
            timegaps up to 67 seconds.
        block : bool, optional
            Whether to block while waiting for events to be captured. If this is False,
            this method will return None and the captured events must be manually
            fetched by calling :meth:`fetch_data`. The default value is True.

        Returns
        -------
        Union[List[numpy.ndarray], None]
            List of numpy.ndarrays containing timestamps in microseconds when logic
            events were detected, or None if block is False. The length of the list is
            equal to the number of channels that were used to capture events, and each
            list element corresponds to a channel.

        Raises
        ------
        ValueError if too many events are requested, or
        ValueError if too many channels are selected, or
        RuntimeError is the timeout is exceeded.
        """
        self._check_arguments(channels, events)
        events += 1  # Capture an extra event in case we get a spurious zero.
        self.clear_buffer(0, CP.MAX_SAMPLES)
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
            c._logic_mode = modes[e]

        if channels == 1:
            self._capture_one()
        elif channels == 2:
            self._capture_two()
        else:
            self._capture_four(e2e_time)

        if block:
            self._wait_for_progress(old_progress, timeout)
            self._timeout(events, timeout)
        else:
            return

        timestamps = self.fetch_data()
        timestamps = [t[: events - 1] for t in timestamps]  # Remove extra events.

        return timestamps[:channels]  # Discard 4:th channel if user asked for 3.

    @staticmethod
    def _check_arguments(channels: int, events: int):
        max_events = CP.MAX_SAMPLES // 4 - 1
        if events > max_events:
            raise ValueError(f"Events must be fewer than {max_events}.")
        elif channels < 0 or channels > 4:
            raise ValueError("Channels must be between 1-4.")

    def _timeout(self, events: int, timeout: float):
        start = time.time()
        while self.get_progress() < events:
            if timeout is not None:
                if time.time() - start >= timeout:
                    raise RuntimeError("Capture timed out.")

    def _capture_one(self):
        self._channels[self._channel_one_map]._prescaler = 0
        self._device.send_byte(CP.TIMING)
        self._device.send_byte(CP.START_ALTERNATE_ONE_CHAN_LA)
        self._device.send_int(CP.MAX_SAMPLES // 4)
        self._device.send_byte(
            (self._channels[self._channel_one_map].number << 4)
            | self._channels[self._channel_one_map]._logic_mode
        )
        self._device.send_byte(
            (self._channels[self._channel_one_map].number << 4) | self._trigger_mode
        )
        self._device.get_ack()

    def _capture_two(self):
        for c in list(self._channels.values())[:2]:
            c._prescaler = 0

        self._device.send_byte(CP.TIMING)
        self._device.send_byte(CP.START_TWO_CHAN_LA)
        self._device.send_int(CP.MAX_SAMPLES // 4)
        self._device.send_byte((self._trigger_channel.number << 4) | self._trigger_mode)
        self._device.send_byte(
            self._channels[self._channel_one_map]._logic_mode
            | (self._channels[self._channel_two_map]._logic_mode << 4)
        )
        self._device.send_byte(
            self._channels[self._channel_one_map].number
            | (self._channels[self._channel_two_map].number << 4)
        )
        self._device.get_ack()

    def _capture_four(self, e2e_time: float):
        rollover_time = (2 ** 16 - 1) / CLOCK_RATE
        e2e_time = 0 if e2e_time is None else e2e_time

        if e2e_time > rollover_time * PRESCALERS[3]:
            raise ValueError("Timegap too big for four channel mode.")
        elif e2e_time > rollover_time * PRESCALERS[2]:
            self._prescaler = 3
        elif e2e_time > rollover_time * PRESCALERS[1]:
            self._prescaler = 2
        elif e2e_time > rollover_time:
            self._prescaler = 1
        else:
            self._prescaler = 0

        self._device.send_byte(CP.TIMING)
        self._device.send_byte(CP.START_FOUR_CHAN_LA)
        self._device.send_int(CP.MAX_SAMPLES // 4)
        self._device.send_int(
            self._channels["ID1"]._logic_mode
            | (self._channels["ID2"]._logic_mode << 4)
            | (self._channels["ID3"]._logic_mode << 8)
            | (self._channels["ID4"]._logic_mode << 12)
        )
        self._device.send_byte(self._prescaler)

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

    def fetch_data(self) -> List[np.ndarray]:
        """Collect captured logic events.

        Returns
        -------
        List[numpy.ndarray]
            List of numpy.ndarrays holding timestamps in microseconds when logic events
            were detected. The length of the list is equal to the number of channels
            that were used to capture events, and each list element corresponds to a
            channel.
        """
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
                    raw_timestamps = self._fetch_long(c)
                else:
                    raw_timestamps = self._fetch_int(c)
                counter_values.append(self._trim_zeros(c, raw_timestamps))

        prescaler = [1 / 64, 1 / 8, 1.0, 4.0][self._prescaler]
        timestamps = [cv * prescaler for cv in counter_values]

        return timestamps

    def _trim_zeros(
        self, channel: digital_channel.DigitalInput, timestamps: np.ndarray
    ) -> np.ndarray:
        """Discard spurious zeros.

        This is necessary because DMA will copy the current value of the timer to
        the buffer any time the capture condition is fulfilled, even if the trigger
        condition hasn't been fulfilled yet.

        For example, if trigger_mode is 'falling' and logic_mode is 'rising' and a
        rising edge occurs before a falling edge, DMA will copy the current value
        of the timer (which is zero since it hasn't triggered yet) into the buffer.
        """
        if self.trigger_mode == "disabled":
            return timestamps
        elif self.trigger_mode == channel.logic_mode:
            return timestamps
        elif self.trigger_mode == "any":
            return timestamps
        else:
            return np.trim_zeros(timestamps)

    def _fetch_long(self, channel: digital_channel.DigitalInput) -> np.ndarray:
        # First half of each long is stored in the first 2500 buffer positions,
        # or positions 5001-7500 for channel two.
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.RETRIEVE_BUFFER)
        self._device.send_int(channel.buffer_idx)
        self._device.send_int(channel.events_in_buffer)
        lsb = self._device.interface.read(channel.events_in_buffer * 2)
        self._device.get_ack()

        while lsb[-1] == 0:
            if len(lsb) == 0:
                return np.array([])
            lsb = lsb[:-1]

        # Second half of each long is stored in positions 2501-5000,
        # or positions 7501-10000 for channel two.
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.RETRIEVE_BUFFER)
        self._device.send_int(channel.buffer_idx + CP.MAX_SAMPLES // 4)
        self._device.send_int(channel.events_in_buffer)
        msb = self._device.interface.read(channel.events_in_buffer * 2)
        self._device.get_ack()
        msb = msb[: len(lsb)]  # More data may have been added since we got LSB.

        lsb = [lsb[a * 2 : a * 2 + 2] for a in range(len(lsb) // 2)]
        msb = [msb[a * 2 : a * 2 + 2] for a in range(len(msb) // 2)]
        # Interleave byte arrays.
        raw_timestamps = [CP.Integer.unpack(b + a)[0] for a, b in zip(msb, lsb)]
        raw_timestamps = np.array(raw_timestamps)
        raw_timestamps = np.trim_zeros(raw_timestamps, trim="b")

        return raw_timestamps

    def _fetch_int(self, channel: digital_channel.DigitalInput) -> np.ndarray:
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

        if raw_timestamps[0] == 0:
            raw_timestamps = np.trim_zeros(raw_timestamps)
            raw_timestamps = np.insert(raw_timestamps, 0, 0)
        else:
            raw_timestamps = np.trim_zeros(raw_timestamps)

        for i, diff in enumerate(np.diff(raw_timestamps)):
            if diff <= 0:  # Counter has rolled over.
                raw_timestamps[i + 1 :] += 2 ** 16 - 1

        return raw_timestamps

    def get_progress(self) -> int:
        """Return the number of captured events per channel currently held in buffer.

        Returns
        -------
        int
            Number of events held in buffer. If multiple channels have events in
            buffer, the lowest value will be returned.
        """
        active_channels = []
        for c in self._channels.values():
            if c.events_in_buffer:
                active_channels.append(c)

        p = CP.MAX_SAMPLES // 4
        progress = self._get_initial_states_and_progress()[1]
        for i in range(len(active_channels)):
            p = min(progress[i], p)

        return p

    def get_initial_states(self) -> Dict[str, bool]:
        """Return the initial state of each digital input at the beginning of capture.

        Returns
        -------
        dict of four str: bool pairs
            Dictionary containing pairs of channel names and the corresponding initial
            state, e.g. {'ID1': True, 'ID2': True, 'ID3': True, 'ID4': False}.
            True means HIGH, False means LOW.
        """
        return self._get_initial_states_and_progress()[0]

    def get_xy(self, timestamps: List[np.ndarray]) -> List[np.ndarray]:
        """Turn timestamps into plottable data.

        Parameters
        ----------
        timestamps : List[numpy.ndarray]
            List of timestamps as returned by :meth:`capture` or :meth:`fetch_data`.

        Returns
        -------
        List[numpy.ndarray]
            List of x, y pairs suitable for plotting using, for example,
            matplotlib.pyplot.plot.
        """
        xy = []

        for e, c in enumerate(
            [self._channel_one_map, self._channel_two_map, "ID3", "ID4"][
                : len(timestamps)
            ]
        ):
            c = self._channels[c]
            if c.events_in_buffer:
                x, y = c._get_xy(self.get_initial_states()[c.name], timestamps[e])
                xy.append(x)
                xy.append(y)

        return xy

    def _get_initial_states_and_progress(self) -> Tuple[Dict[str, bool], List[int]]:
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
        """Setup trigger channel and trigger condition.

        Parameters
        ----------
        trigger_channel : {"ID1", "ID2", "ID3", "ID4"}
            The digital input on which to trigger.
        trigger_condition : {"disabled", "falling", "rising"}
            The type of logic level change on which to trigger.
        """
        self.trigger_channel = trigger_channel
        self._trigger_channel = self._channels[trigger_channel]
        self.trigger_mode = trigger_mode

    def _configure_trigger(self, channels: int):
        # For some reason firmware uses different values for trigger_mode
        # depending on number of channels.
        if channels == 1:
            self._trigger_mode = {
                "disabled": 0,
                "any": 1,
                "falling": 2,
                "rising": 3,
                "four rising": 4,
                "sixteen rising": 5,
            }[self.trigger_mode]
        elif channels == 2:
            self._trigger_mode = {"disabled": 0, "falling": 3, "rising": 1,}[
                self.trigger_mode
            ]
        elif channels == 4:
            self._trigger_mode = {"disabled": 0, "falling": 1, "rising": 3,}[
                self.trigger_mode
            ]

    def stop(self):
        """Stop a running :meth:`capture` function.
        """
        self._device.send_byte(CP.TIMING)
        self._device.send_byte(CP.STOP_LA)
        self._device.get_ack()

    def get_states(self) -> Dict[str, bool]:
        """Return the current state of the digital inputs.

        Returns
        -------
        dict of four str: bool pairs
            Dictionary containing pairs of channel names and the corresponding current
            state, e.g. {'ID1': True, 'ID2': True, 'ID3': True, 'ID4': False}.
            True means HIGH, False means LOW.
        """
        self._device.send_byte(CP.DIN)
        self._device.send_byte(CP.GET_STATES)
        s = self._device.get_byte()
        self._device.get_ack()
        return {
            "ID1": (s & 1 != 0),
            "ID2": (s & 2 != 0),
            "ID3": (s & 4 != 0),
            "ID4": (s & 8 != 0),
        }

    def count_pulses(
        self, channel: str, interval: float = 1, block: bool = True
    ) -> Union[int, None]:
        """	Count pulses on a digital input.

        The counter is 16 bits, so it will roll over after 65535 pulses. This method
        can be used at the same time as the oscilloscope.

        Parameters
        ----------
        channel : {"ID1", "ID2", "ID3", "ID4"}
            Digital input on which to count pulses.
        interval : float, optional
            Time in seconds during which to count pulses. The default value is
            1 second.
        block : bool, optional
            Whether to block while counting pulses or not. If False, this method will
            return None, and the pulses must be manually fetched using
            :meth:`fetch_pulse_count`. Additionally, the interval argument has no
            meaning if block is False, the counter will keep counting even after the
            interval time has expired. The default value is True.

        Returns
        -------
        Union[int, None]
            Number of pulses counted during the interval, or None if block is False.
        """
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.START_COUNTING)
        self._device.send_byte(self._channels[channel].number)
        self._device.get_ack()

        if block:
            time.sleep(interval)
        else:
            return

        return self.fetch_pulse_count()

    def fetch_pulse_count(self) -> int:
        """Return the number of pulses counted since calling :meth:`count_pulses`.

        Returns
        -------
        int
            Number of pulses counted since calling :meth:`count_pulses`.
        """
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.FETCH_COUNT)
        count = self._device.get_int()
        self._device.get_ack()
        return count

    def clear_buffer(self, starting_position: int, total_points: int):
        """Clear a section of the ADC hardware buffer.

        Parameters
        ----------
        starting_position : int
            Starting position from which to clear the buffer. Should be a value between
            0 and 9999.
        total_points : int
            Total points to clear from the buffer. Should be a value between 0 and
            10000.
        """
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.CLEAR_BUFFER)
        self._device.send_int(starting_position)
        self._device.send_int(total_points)
        self._device.get_ack()
        self._invalidate_buffer()

    def _invalidate_buffer(self):
        for c in self._channels.values():
            c.events_in_buffer = 0
            c.buffer_idx = None
