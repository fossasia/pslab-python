"""Classes and functions related to the PSLab's oscilloscope instrument.

Example
-------
>>> from PSL.oscilloscope import Oscilloscope
>>> scope = Oscilloscope()
>>> x, y1, y2, y3 = scope.capture(channels=3, samples=1600, timegap=2)
"""

import time
from typing import List, Tuple, Union

import numpy as np

import PSL.commands_proto as CP
from PSL import achan, packet_handler


class Oscilloscope:
    """Capture varying voltage signals on up to four channels simultaneously.

    Parameters
    ----------
    device : :class:`Handler`, optional
        Serial interface for communicating with the PSLab device. If not provided, a
        new one will be created.

    Attributes
    ----------
    channel_one_map : str
        Remap the first sampled channel. The default value is "CH1".
    trigger_enabled
    """

    _CH234 = ["CH2", "CH3", "MIC"]

    def __init__(self, device: packet_handler.Handler = None):
        self._device = packet_handler.Handler() if device is None else device
        self._channels = {a: achan.AnalogInput(a) for a in achan.ANALOG_CHANNELS}
        self._channel_one_map = "CH1"
        self._trigger_voltage = 0
        self._trigger_enabled = False
        self._trigger_channel = "CH1"
        self._set_gain("CH1", 1)
        self._set_gain("CH2", 1)

    def capture(
        self,
        channels: int,
        samples: int,
        timegap: float,
        trigger: Union[bool, float] = None,
        trigger_channel: str = None,
        block: bool = True,
    ) -> List[np.ndarray]:
        """Capture an oscilloscope trace from the specified input channels.

        This is a blocking call.

        Parameters
        ----------
        channels : str or {1, 2, 3, 4}
            Number of channels to sample from simultaneously, or the name
            (CH1, CH2, CH3, MIC, CAP, RES, VOL) of a single channel to sample
            from. If channel is an integer, the oscilloscope will sample the
            first one, two, three, or four channels in the aforementioned list.
        samples : int
            Number of samples to fetch. Maximum 10000 divided by number of
            channels.
        timegap : float
            Time gap between samples in microseconds. Will be rounded to the
            closest 1 / 8 µs. The minimum time gap depends on the type of
            measurement:
                +--------------+------------+----------+------------+
                | Simultaneous | No trigger | Trigger  | No trigger |
                | channels     | (10-bit)   | (10-bit) | (12-bit)   |
                +==============+============+==========+============+
                | 1            | 0.5 µs     | 0.75 µs  | 1 µs       |
                +--------------+------------+----------+------------+
                | 2            | 0.875 µs   | 0.875 µs | N/A        |
                +--------------+------------+----------+------------+
                | 4            | 1.75 µs    | 1.75 µs  | N/A        |
                +--------------+------------+----------+------------+
            Sample resolution is set automatically based on the above
            limitations; i.e. to get 12-bit samples only one channel may be
            sampled, there must be no active trigger, and the time gap must be
            1 µs or greater.
        trigger : float, optional
            Voltage at which to trigger sampling. Triggering is disabled by
            default. Trigger settings persist between calls; disable by setting
            trigger=False.
        trigger_channel : str, optional
            Wait for the voltage level on this channel to cross the trigger
            value before sampling. Same as the first sampled channel by
            default.
        block : bool, optional
            Whether or not to block while sampling. If False, return timestamps
            immediately without waiting for corresponding voltages. User is
            responsible for waiting an appropriate amount of time before
            collecting samples with :meth:`fetch_data`. True by default.

        Example
        -------
        >>> from PSL.oscilloscope import Oscilloscope
        >>> scope = Oscilloscope()
        >>> x, y = scope.capture(1, 3200, 1)

        Returns
        -------
        list of numpy.ndarray
            List of numpy arrays holding timestamps and corresponding voltages.
            In non-blocking mode, only timestamps are returned; voltages must
            be fetched using :meth:`fetch_data`.

        Raises
        ------
        ValueError
            If :channels: is not 1, 2, 3, 4, or one of CH1, CH2, CH3, MIC, CAP,
            RES, VOL, or
            :samples: > 10000 / :channels:, or
            :timegap: is too low.
        """
        if isinstance(channels, str):
            self._channel_one_map = channels
            channels = 1

        if trigger is False:
            self._trigger_enabled = False
        elif trigger is not None:
            if trigger_channel is None:
                self._trigger_channel = self._channel_one_map
            else:
                self._trigger_channel = trigger_channel
            self.configure_trigger(voltage=trigger)

        self._check_args(channels, samples, timegap)
        timegap = int(timegap * 8) / 8
        self._capture(channels, samples, timegap)
        x = [timegap * np.arange(samples)]

        if block:
            time.sleep(1e-6 * samples * timegap)

            while not self.progress()[0]:
                pass

            # Discard MIC if user requested three channels.
            y = self.fetch_data()[:channels]

            return x + y
        else:
            return x

    def _check_args(self, channels: int, samples: int, timegap: float):
        if channels not in (1, 2, 3, 4):
            raise ValueError("Number of channels to sample must be 1, 2, 3, or 4.")

        max_samples = CP.MAX_SAMPLES // channels
        if not 0 < samples <= max_samples:
            e1 = f"Cannot collect more than {max_samples} when sampling from "
            e2 = f"{channels} channels."
            raise ValueError(e1 + e2)

        min_timegap = self._lookup_mininum_timegap(channels)
        if timegap < min_timegap:
            raise ValueError(f"timegap must be at least {min_timegap}.")

        if self._channel_one_map not in self._channels:
            e1 = f"{self._channel_one_map} is not a valid channel. "
            e2 = f"Valid channels are {list(self._channels.keys())}."
            raise ValueError(e1 + e2)

    def _lookup_mininum_timegap(self, channels: int) -> float:
        channels_idx = {
            1: 0,
            2: 1,
            4: 2,
        }
        min_timegaps = [[0.5, 0.75], [0.875, 0.875], [1.75, 1.75]]

        return min_timegaps[channels_idx[channels]][self._trigger_enabled]

    def _capture(self, channels: int, samples: int, timegap: float):
        self._invalidate_buffer()
        chosa = self._channels[self._channel_one_map].chosa
        self._channels[self._channel_one_map].resolution = 10
        self._device.send_byte(CP.ADC)

        CH123SA = 0  # TODO what is this?
        chosa = self._channels[self._channel_one_map].chosa
        self._channels[self._channel_one_map].samples_in_buffer = samples
        self._channels[self._channel_one_map].buffer_idx = 0
        if channels == 1:
            if self._trigger_enabled:
                self._device.send_byte(CP.CAPTURE_ONE)
                self._device.send_byte(chosa | 0x80)  # Trigger
            elif timegap >= 1:
                self._channels[self._channel_one_map].resolution = 12
                self._device.send_byte(CP.CAPTURE_DMASPEED)
                self._device.send_byte(chosa | 0x80)  # 12-bit mode
            else:
                self._device.send_byte(CP.CAPTURE_DMASPEED)
                self._device.send_byte(chosa)  # 10-bit mode
        elif channels == 2:
            self._channels["CH2"].resolution = 10
            self._channels["CH2"].samples_in_buffer = samples
            self._channels["CH2"].buffer_idx = 1 * samples
            self._device.send_byte(CP.CAPTURE_TWO)
            self._device.send_byte(chosa | (0x80 * self._trigger_enabled))
        else:
            for e, c in enumerate(self._CH234):
                self._channels[c].resolution = 10
                self._channels[c].samples_in_buffer = samples
                self._channels[c].buffer_idx = (e + 1) * samples
            self._device.send_byte(CP.CAPTURE_FOUR)
            self._device.send_byte(
                chosa | (CH123SA << 4) | (0x80 * self._trigger_enabled)
            )

        self._device.send_int(samples)
        self._device.send_int(int(timegap * 8))  # 8 MHz clock
        self._device.get_ack()

    def _invalidate_buffer(self):
        for c in self._channels.values():
            c.samples_in_buffer = 0
            c.buffer_idx = None

    def fetch_data(self) -> List[np.ndarray]:
        """Fetch samples captured from specified channel.

        Parameters
        ----------
        channel : {'CH1', 'CH2', 'CH3', 'MIC', 'CAP', 'RES', 'VOL'}
            Name of the channel from which to fetch captured data.

        Example
        -------
        >>> from PSL.oscilloscope import Oscilloscope
        >>> scope = Oscilloscope()
        >>> scope.capture_nonblocking(channels=2, samples=1600, timegap=1)
        >>> y1, y2 = scope.fetch_data()

        Returns
        -------
        list of numpy.ndarray
            List of numpy arrays holding sampled voltages.
        """
        channels = [c for c in self._channels.values() if c.samples_in_buffer]
        data = [None] * len(channels)

        for i, channel in enumerate(channels):
            samples = channel.samples_in_buffer
            data[i] = bytearray()

            for j in range(int(np.ceil(samples / CP.DATA_SPLITTING))):
                self._device.send_byte(CP.COMMON)
                self._device.send_byte(CP.RETRIEVE_BUFFER)
                offset = channel.buffer_idx + j * CP.DATA_SPLITTING
                self._device.send_int(offset)
                self._device.send_int(CP.DATA_SPLITTING)  # Ints to read
                # Reading int by int sometimes causes a communication error.
                data[i] += self._device.read(CP.DATA_SPLITTING * 2)
                self._device.get_ack()

            data[i] = [
                CP.ShortInt.unpack(data[i][s * 2 : s * 2 + 2])[0]
                for s in range(samples)
            ]
            data[i] = channel.scale(np.array(data[i]))

        return data

    def progress(self) -> Tuple[bool, int]:
        """Return the status of a capture call.

        Returns
        -------
        bool, int
            A boolean indicating whether the capture is complete, followed by the
            number of samples currently held in the buffer.
        """
        self._device.send_byte(CP.ADC)
        self._device.send_byte(CP.GET_CAPTURE_STATUS)
        conversion_done = self._device.get_byte()
        samples = self._device.get_int()
        self._device.get_ack()

        return bool(conversion_done), samples

    def configure_trigger(
        self,
        channel: str = None,
        voltage: float = 0,
        prescaler: int = 0,
        enable: bool = True,
    ):
        """Configure trigger parameters for 10-bit capture routines.

        The capture routines will wait until a rising edge of the input signal crosses
        the specified level. The trigger will timeout within 8 ms, and capture will
        start regardless.

        To disable the trigger after configuration, set the trigger_enabled attribute
        of the Oscilloscope instance to False.

        Parameters
        ----------
        channel : {'CH1', 'CH2', 'CH3', 'MIC', 'CAP', 'RES', 'VOL'}, optional
            The name of the trigger channel. First sampled channel by default.
        voltage : float, optional
            The trigger voltage in volts. The default value is 0.
        prescaler : int, optional
            The default value is 0.
        enable_trigger : bool, optional
            Set this to False to disable the trigger. True by default.

        Examples
        --------
        >>> from PSL.oscilloscope import Oscilloscope
        >>> scope = Oscilloscope()
        >>> scope.configure_trigger(channel='CH1', voltage=1.1)
        >>> xy = scope.capture(channels=1, samples=800, timegap=2)
        >>> diff = abs(xy[1, 0] - 1.1)  # Should be small unless a timeout occurred.

        Raises
        ------
        TypeError
            If the trigger channel is set to a channel which cannot be sampled.
        """
        if enable is False:
            self._trigger_enabled = False
            return

        if channel is not None:
            self._trigger_channel = channel

        if self._trigger_channel == self._channel_one_map:
            channel = 0
        elif self._trigger_channel in self._CH234:
            channel = self._CH234.index(self._trigger_channel) + 1
        else:
            raise TypeError(f"Cannot trigger on {self._trigger_channel}.")

        self._device.send_byte(CP.ADC)
        self._device.send_byte(CP.CONFIGURE_TRIGGER)
        # Trigger channel (4lsb) , trigger timeout prescaler (4msb)
        self._device.send_byte((prescaler << 4) | (1 << channel))  # TODO prescaler?
        level = self._channels[self._trigger_channel].unscale(voltage)
        self._device.send_int(level)
        self._device.get_ack()
        self._trigger_enabled = True

    def select_range(self, channel: str, voltage_range: Union[int, float]):
        """Set appropriate gain automatically.

        Setting the right voltage range will result in better resolution.

        Parameters
        ----------
        channel : {'CH1', 'CH2'}
            Channel on which to apply gain.
        voltage_range : {16, 8, 4, 3, 2, 1.5, 1, .5}

        Examples
        --------
        Set 2x gain on CH1. Voltage range ±8 V:
        >>> from PSL.oscilloscope import Oscilloscope
        >>> scope = Oscilloscope()
        >>> scope.select_range('CH1', 8)
        """
        ranges = [16, 8, 4, 3, 2, 1.5, 1, 0.5]
        gain = achan.GAIN_VALUES[ranges.index(voltage_range)]
        self._set_gain(channel, gain)

    def _set_gain(self, channel: str, gain: int):
        self._channels[channel].gain = gain
        pga = self._channels[channel].programmable_gain_amplifier
        gain_idx = achan.GAIN_VALUES.index(gain)
        self._device.send_byte(CP.ADC)
        self._device.send_byte(CP.SET_PGA_GAIN)
        self._device.send_byte(pga)
        self._device.send_byte(gain_idx)
        self._device.get_ack()
