"""Classes and functions related to the PSLab's oscilloscope instrument.

Example
-------
>>> from PSL.oscilloscope import Oscilloscope
>>> scope = Oscilloscope()
>>> x, y1, y2, y3, y4 = scope.capture(channels=4, samples=1600, timegap=2)
"""

import time
from typing import Tuple, Union

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

    MAX_SAMPLES = 10000
    CH234 = ["CH2", "CH3", "MIC"]

    def __init__(self, device: packet_handler.Handler = None):
        self._device = packet_handler.Handler() if device is None else device
        self._channels = {
            a: achan.AnalogInput(a, self._device) for a in achan.ANALOG_CHANNELS
        }
        self.channel_one_map = "CH1"
        self._trigger_voltage = 0
        self._trigger_enabled = False
        self._trigger_channel = "CH1"

    def capture(
        self,
        channels: int,
        samples: int,
        timegap: float,
    ) -> np.ndarray:
        """Capture an oscilloscope trace from the specified input channels.

        This is a blocking call.

        Parameters
        ----------
        channels : {1, 2, 4}
            Number of channels to sample from simultaneously. By default, samples are
            captured from CH1, CH2, CH3 and MIC. CH1 can be remapped to any other
            channel (CH2, CH3, MIC, CAP, RES, VOL) by setting the channel_one_map
            attribute of the Oscilloscope instance to the desired channel.
        samples : int
            Number of samples to fetch. Maximum 10000 divided by number of channels.
        timegap : float
            Time gap between samples in microseconds. Will be rounded to the closest
            1 / 8 µs. The minimum time gap depends on the type of measurement:
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
            Sample resolution is set automatically based on the above limitations; i.e.
            to get 12-bit samples only one channel may be sampled, there must be no
            active trigger, and the time gap must be 1 µs or greater.

        Example
        -------
        >>> from PSL.oscilloscope import Oscilloscope
        >>> scope = Oscilloscope()
        >>> x, y = scope.capture(1, 3200, 1)

        Returns
        -------
        numpy.ndarray
            (:channels:+1)-dimensional array with timestamps in the first dimension
            and corresponding voltages in the following dimensions.

        Raises
        ------
        ValueError
            If :channels: is not 1, 2 or 4, or
            :samples: > 10000 / :channels:, or
            :channel_one_map: is not one of CH1, CH2, CH3, MIC, CAP, RES, VOL, or
            :timegap: is too low.
        """
        xy = np.zeros([channels + 1, samples])
        xy[0] = self.capture_nonblocking(channels, samples, timegap)
        time.sleep(1e-6 * samples * timegap + 0.01)

        while not self.progress()[0]:
            pass

        active_channels = ([self.channel_one_map] + self.CH234)[:channels]
        for e, c in enumerate(active_channels):
            xy[e + 1] = self.fetch_data(c)

        return xy

    def capture_nonblocking(
        self, channels: int, samples: int, timegap: float
    ) -> np.ndarray:
        """Tell the pslab to start sampling the specified input channels.

        This method is identical to
        :meth:`capture <PSL.oscilloscope.Oscilloscope.capture>`,
        except it does not block while the samples are being captured. Collected
        samples must be manually fetched by calling
        :meth:`fetch_data<PSL.oscilloscope.Oscilloscope.fetch_data>`.

        Parameters
        ----------
        See :meth:`capture <PSL.oscilloscope.Oscilloscope.capture>`.

        Example
        -------
        >>> import time
        >>> from PSL.oscilloscope import Oscilloscope
        >>> scope = Oscilloscope()
        >>> x = scope.capture_nonblocking(1, 3200, 1)
        >>> time.sleep(3200 * 1e-6)
        >>> y = scope.fetch_data("CH1")

        Returns
        -------
        numpy.ndarray
            One-dimensional array of timestamps.

        Raises
        ------
        See :meth:`capture <PSL.oscilloscope.Oscilloscope.capture>`.
        """
        self._check_args(channels, samples, timegap)
        timegap = int(timegap * 8) / 8
        self._capture(channels, samples, timegap)
        return timegap * np.arange(samples)

    def _check_args(self, channels: int, samples: int, timegap: float):
        if channels not in (1, 2, 4):
            raise ValueError("Number of channels to sample must be 1, 2, or 4.")

        max_samples = self.MAX_SAMPLES // channels
        if not 0 < samples <= max_samples:
            e1 = f"Cannot collect more than {max_samples} when sampling from "
            e2 = f"{channels} channels."
            raise ValueError(e1 + e2)

        min_timegap = self._lookup_mininum_timegap(channels)
        if timegap < min_timegap:
            raise ValueError(f"timegap must be at least {min_timegap}.")

        if self.channel_one_map not in self._channels:
            e1 = f"{self.channel_one_map} is not a valid channel. "
            e2 = f"Valid channels are {list(self._channels.keys())}."
            raise ValueError(e1 + e2)

    def _lookup_mininum_timegap(self, channels: int) -> float:
        channels_idx = {
            1: 0,
            2: 1,
            4: 2,
        }
        min_timegaps = [[0.5, 0.75], [0.875, 0.875], [1.75, 1.75]]

        return min_timegaps[channels_idx[channels]][self.trigger_enabled]

    def _capture(self, channels: int, samples: int, timegap: float):
        self._invalidate_buffer()
        chosa = self._channels[self.channel_one_map].chosa
        self._channels[self.channel_one_map].resolution = 10
        self._device.send_byte(CP.ADC)

        CH123SA = 0  # TODO what is this?
        chosa = self._channels[self.channel_one_map].chosa
        self._channels[self.channel_one_map].samples_in_buffer = samples
        self._channels[self.channel_one_map].buffer_idx = 0
        if channels == 1:
            if self.trigger_enabled:
                self._device.send_byte(CP.CAPTURE_ONE)
                self._device.send_byte(chosa | 0x80)  # Trigger
            elif timegap >= 1:
                self._channels[self.channel_one_map].resolution = 12
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
            self._device.send_byte(chosa | (0x80 * self.trigger_enabled))
        else:
            for e, c in enumerate(self.CH234):
                self._channels[c].resolution = 10
                self._channels[c].samples_in_buffer = samples
                self._channels[c].buffer_idx = (e + 1) * samples
            self._device.send_byte(CP.CAPTURE_FOUR)
            self._device.send_byte(
                chosa | (CH123SA << 4) | (0x80 * self.trigger_enabled)
            )

        self._device.send_int(samples)
        self._device.send_int(int(timegap * 8))  # 8 MHz clock
        self._device.get_ack()

    def _invalidate_buffer(self):
        for c in self._channels.values():
            c.samples_in_buffer = 0
            c.buffer_idx = None

    def fetch_data(self, channel: str) -> np.ndarray:
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
        >>> y1 = scope.fetch_data("CH1")
        >>> y2 = scope.fetch_data("CH2")

        Returns
        -------
        numpy.ndarray
            One-dimensional array holding the requested voltages.
        """
        data = bytearray()
        channel = self._channels[channel]
        samples = channel.samples_in_buffer

        for i in range(int(np.ceil(samples / CP.DATA_SPLITTING))):
            self._device.send_byte(CP.COMMON)
            self._device.send_byte(CP.RETRIEVE_BUFFER)
            offset = channel.buffer_idx + i * CP.DATA_SPLITTING
            self._device.send_int(offset)
            self._device.send_int(CP.DATA_SPLITTING)  # Ints to read
            # Reading int by int sometimes causes a communication error.
            data += self._device.read(CP.DATA_SPLITTING * 2)
            self._device.get_ack()

        data = [CP.ShortInt.unpack(data[s * 2 : s * 2 + 2])[0] for s in range(samples)]

        return channel.scale(np.array(data))

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

    def configure_trigger(self, channel: str, voltage: float, prescaler: int = 0):
        """Configure trigger parameters for 10-bit capture routines.

        The capture routines will wait until a rising edge of the input signal crosses
        the specified level. The trigger will timeout within 8 ms, and capture will
        start regardless.

        To disable the trigger after configuration, set the trigger_enabled attribute
        of the Oscilloscope instance to False.

        Parameters
        ----------
        channel : {'CH1', 'CH2', 'CH3', 'MIC', 'CAP', 'RES', 'VOL'}
            The name of the trigger channel.
        voltage : float
            The trigger voltage in volts.
        prescaler : int, optional
            The default value is 0.

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
        self._trigger_channel = channel

        if channel == self.channel_one_map:
            channel = 0
        elif channel in self.CH234:
            channel = self.CH234.index(channel) + 1
        elif self.channel_one_map == "CH1":
            e = f"Cannot trigger on {channel} unless it is remapped to CH1."
            raise TypeError(e)
        else:
            e = f"Cannot trigger on CH1 when {self.channel_one_map} is mapped to CH1."
            raise TypeError(e)

        self._device.send_byte(CP.ADC)
        self._device.send_byte(CP.CONFIGURE_TRIGGER)
        # Trigger channel (4lsb) , trigger timeout prescaler (4msb)
        self._device.send_byte((prescaler << 4) | (1 << channel))  # TODO prescaler?
        level = self._channels[self._trigger_channel].unscale(voltage)
        self._device.send_int(level)
        self._device.get_ack()
        self._trigger_enabled = True

    @property
    def trigger_enabled(self) -> bool:
        """Activate or deactivate a trigger set by :meth:`configure_trigger`.

        Becomes True automatically when calling :meth:`configure_trigger`.

        If trigger_enabled is set to True without first calling
        :meth:`configure_trigger`, the trigger will be configured with a trigger
        voltage of 0 V on CH1.
        """
        return self._trigger_enabled

    @trigger_enabled.setter
    def trigger_enabled(self, value: bool):
        self._trigger_enabled = value
        if self._trigger_enabled:
            self.configure_trigger(self._trigger_channel, self._trigger_voltage)

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
        >>> from PSL.oscilloscope import Oscilloscope
        >>> scope = Oscilloscope()
        >>> scope.select_range('CH1', 8)
        # Gain set to 2x on CH1. Voltage range ±8 V.
        """
        ranges = [16, 8, 4, 3, 2, 1.5, 1, 0.5]
        if voltage_range in ranges:
            idx = ranges.index(voltage_range)
            gain = achan.GAIN_VALUES[idx]
            self._channels[channel].gain = gain
        else:
            e = f"Invalid range: {voltage_range}. Valid ranges are {ranges}."
            raise ValueError(e)
