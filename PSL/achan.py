import time
from typing import List, Tuple, Union

import numpy as np

from PSL.analyticsClass import analyticsClass
import PSL.commands_proto as CP
from PSL import packet_handler

GAIN_VALUES = (1, 2, 4, 5, 8, 10, 16, 32, 1 / 11)

ANALOG_CHANNELS = (
    "CH1",
    "CH2",
    "CH3",
    "MIC",
    "CAP",
    "SEN",
    "AN8",
)

INPUT_RANGES = {
    "CH1": (16.5, -16.5),  # Specify inverted channels explicitly by reversing range!
    "CH2": (16.5, -16.5),
    "CH3": (-3.3, 3.3),  # external gain control analog input
    "MIC": (-3.3, 3.3),  # connected to MIC amplifier
    "CAP": (0, 3.3),
    "SEN": (0, 3.3),
    "AN8": (0, 3.3),
}

PIC_ADC_MULTIPLEX = {
    "CH1": 3,
    "CH2": 0,
    "CH3": 1,
    "MIC": 2,
    "AN4": 4,
    "SEN": 7,
    "CAP": 5,
    "AN8": 8,
}

MAX_SAMPLES = 10000


class AnalogInput:
    """
    """

    def __init__(self, name: str, connection: packet_handler.Handler):
        self.name = name  # The generic name of the input. like 'CH1', 'IN1' etc.
        self.connection = connection

        if self.name == "CH1":
            self.programmable_gain_amplifier = 1
        elif self.name == "CH2":
            self.programmable_gain_amplifier = 2
        else:
            self.programmable_gain_amplifier = None

        self._gain = 1
        self._resolution = 2 ** 10 - 1
        self.buffer = None
        self._scale = np.poly1d(0)
        self._unscale = np.poly1d(0)
        self.chosa = PIC_ADC_MULTIPLEX[self.name]
        self._calibrate()

    @property
    def gain(self) -> Union[int, float, None]:
        """Get or set the analog gain.

        Setting a new gain level will automatically recalibrate the channel.
        On channels other than CH1 and CH2 gain is None.

        Raises
        ------
        TypeError
            If gain is set on a channel which does not support it.
        ValueError
            If a gain value other than 1, 2, 4, 5, 8, 10, 16, 32, 1 / 11 is set.
        """
        if self.name in ("CH1", "CH2"):
            return self._gain
        else:
            return None

    @gain.setter
    def gain(self, value: Union[int, float]):
        if self.name not in ("CH1", "CH2"):
            raise TypeError(f"Analog gain is not available on {self.name}.")

        if value not in GAIN_VALUES:
            raise ValueError(f"Invalid gain. Valid values are {GAIN_VALUES}.")

        if value == 1 / 11:
            value = 1  # External attenuator mode. Set gain 1x.

        gain_idx = GAIN_VALUES.index(value)
        self.connection.send_byte(CP.ADC)
        self.connection.send_byte(CP.SET_PGA_GAIN)
        self.connection.send_byte(self.programmable_gain_amplifier)
        self.connection.send_byte(gain_idx)
        self.connection.get_ack()
        self._gain = value
        self._calibrate()

    @property
    def resolution(self) -> int:
        """Get or set the resolution in bits.

        Setting a new resolution will automatically recalibrate the channel.

        Raises
        ------
        ValueError
            If a resolution other than 10 or 12 is set.
        """
        return int(np.log2((self._resolution + 1)))

    @resolution.setter
    def resolution(self, value: int):
        if value not in (10, 12):
            raise ValueError("Resolution must be 10 or 12 bits.")
        self._resolution = 2 ** value - 1
        self._calibrate()

    def _calibrate(self):
        A = INPUT_RANGES[self.name][0] / self._gain
        B = INPUT_RANGES[self.name][1] / self._gain
        slope = B - A
        intercept = A
        self._scale = np.poly1d([slope / self._resolution, intercept])
        self._unscale = np.poly1d(
            [self._resolution / slope, -self._resolution * intercept / slope]
        )

    def scale(self, raw: Union[int, List[int]]) -> float:
        """Translate raw integer value from device to corresponding voltage.

        Inverse of :meth:`unscale. <PSL.achan.AnalogInputSource.unscale>`.

        Parameters
        ----------
        raw : int, List[int]
            An integer, or a list of integers, received from the device.

        Returns
        -------
        float
            Voltage, translated from raw based on channel range, gain, and resolution.
        """
        return self._scale(raw)

    def unscale(self, voltage: float) -> int:
        """Translate a voltage to a raw integer value interpretable by the device.

        Inverse of :meth:`scale. <PSL.achan.AnalogInputSource.scale>`.

        Parameters
        ----------
        voltage : float
            Voltage in volts.

        Returns
        -------
        int
            Corresponding integer value, adjusted for resolution and gain and clipped
            to the channel's range.
        """
        level = self._unscale(voltage)
        level = np.clip(level, 0, self._resolution)
        level = np.round(level)
        return int(level)


class AnalogAcquisitionHandler:
    """
    """

    MAX_SAMPLES = 10000
    CH234 = ["CH2", "CH3", "MIC"]

    def __init__(self, connection: packet_handler.Handler = None):
        self.connection = packet_handler.Handler() if connection is None else connection
        self.channels = {a: AnalogInput(a, self.connection) for a in ANALOG_CHANNELS}
        self.channel_one_map = "CH1"
        self._trigger_voltage = 0
        self.trigger_enabled = False
        self._trigger_channel = "CH1"
        self.data_splitting = CP.DATA_SPLITTING

    def capture(self, channels: int, samples: int, timegap: float,) -> np.ndarray:
        """Blocking call that fetches an oscilloscope trace from the specified input channels.

        Parameters
        ----------
        channels : {1, 2, 4}
            Number of channels to sample from simultaneously. By default, samples are
            captured from CH1, CH2, CH3 and MIC. CH1 can be remapped to any other
            channel (CH2, CH3, MIC, CAP, SEN, AN8) by setting the channel_one_map
            attribute of the AnalogAcquisitionHandler instance to the desired channel.
        samples : int
            Number of samples to fetch. Maximum 10000 divided by number of channels.
        timegap : float
            Timegap between samples in microseconds. Will be rounded to the closest
            1 / 8 µs. The minimum timegap depends on the type of measurement:
                When sampling a single, untriggered channel with 10 bits of resolution,
                the timegap must be exactly 0.5 µs (2 Msps).
                When sampling a single channel with 12 bits of resolution, the timegap
                must be 2 µs or greater (500 ksps).
                When sampling two or more channels, the timegap must be 0.875 µs or
                greater (1.1 Msps).

        Example
        -------
        >>> from PSL import achan
        >>> analog_channels = achan.AnalogAcquisitionHandler()
        >>> x, y = analog_channels.capture(1, 3200, 1)

        Returns
        -------
        numpy.ndarray
            (:channels:+1)-dimensional array with timestamps in the first dimension
            and corresponding voltages in the following dimensions.

        Raises
        ------
        ValueError
            If :channels: > 4 or
            :samples: > 10000 / :channels:, or
            :channel_one_map: is not one of CH1, CH2, CH3, MIC, CAP, SEN, AN8, or
            :timegap: is too low.
        """
        self.capture_nonblocking(channels, samples, timegap)
        time.sleep(1e-6 * samples * timegap + 0.01)

        while not self.progress()[0]:
            pass

        xy = np.zeros([channels + 1, samples])
        xy[0] = timegap * np.arange(samples)
        active_channels = [
            self.channels[k] for k in ([self.channel_one_map] + self.CH234)[:channels]
        ]
        for e, c in enumerate(active_channels):
            xy[e + 1] = c.scale(self.fetch_data(c.buffer, samples))

        return xy

    def capture_nonblocking(self, channels: int, samples: int, timegap: float):
        """Tell the pslab to start sampling the specified input channels.

        This method is identical to :meth:`capture <PSL.achan.AnalogAcquisitionHandler.capture>`,
        except it does not block while the samples are being captured. Collected
        samples must be manually fetched by calling :meth:`fetch_data <PSL.achan.AnalogAcquisitionHandler.fetch_data>`.

        Parameters
        ----------
        See :meth:`capture <PSL.achan.AnalogAcquisitionHandler.capture>`.

        Example
        -------
        >>> import numpy as np
        >>> from PSL import achan
        >>> analog_channels = achan.AnalogAcquisitionHandler()
        >>> analog_channels.capture_nonblocking(1, 3200, 1)
        >>> x = 1 * np.arange(3200)
        >>> y = analog_channels.fetch_data(0, 3200)

        Raises
        ------
        See :meth:`capture <PSL.achan.AnalogAcquisitionHandler.capture>`.
        """
        self._check_args(channels, samples, timegap)
        timegap = int(timegap * 8) / 8
        self._capture(channels, samples, timegap)

    def _check_args(self, channels: int, samples: int, timegap: float):
        if channels not in (1, 2, 4):
            raise ValueError("Number of channels to sample must be 1, 2, or 4.")

        max_samples = self.MAX_SAMPLES // channels
        if not 0 < samples <= max_samples:
            e1 = f"Cannot collect more than {max_samples} when sampling from "
            e2 = f"{channels} channels."
            raise ValueError(e1 + e2)

        min_timegap = 0.5 + 0.375 * (channels > 1 or self.trigger_enabled)
        if timegap < min_timegap:
            raise ValueError(f"timegap must be at least {min_timegap}.")

        if self.channel_one_map not in self.channels:
            e1 = f"{self.channel_one_map} is not a valid channel. "
            e2 = f"Valid channels are {list(self.channels.keys())}."
            raise ValueError(e1 + e2)

    def _capture(self, channels: int, samples: int, timegap: float):
        chosa = self.channels[self.channel_one_map].chosa
        self.channels[self.channel_one_map].buffer = 0
        self.channels[self.channel_one_map].resolution = 10
        self.connection.send_byte(CP.ADC)

        CH123SA = 0  # TODO what is this?
        chosa = self.channels[self.channel_one_map].chosa
        if channels == 1:
            if self.trigger_enabled:
                self.channels[self.channel_one_map].resolution = 12
                # Rescale trigger voltage for 12-bit resolution.
                self.configure_trigger(
                    self.channels[self.channel_one_map], self.trigger_voltage
                )
                self.connection.send_byte(CP.CAPTURE_12BIT)
                self.connection.send_byte(chosa | 0x80)  # Trigger
            elif timegap >= 1:
                self.channels[self.channel_one_map].resolution = 12
                self.connection.send_byte(CP.CAPTURE_DMASPEED)
                self.connection.send_byte(chosa | 0x80)  # 12-bit mode
            else:
                self.connection.send_byte(CP.CAPTURE_DMASPEED)
                self.connection.send_byte(chosa)  # 10-bit mode
        elif channels == 2:
            self.channels["CH2"].resolution = 10
            self.channels["CH2"].buffer = 1
            self.connection.send_byte(CP.CAPTURE_TWO)
            self.connection.send_byte(chosa | (0x80 * self.trigger_enabled))
        else:
            for e, c in enumerate(self.CH234):
                self.channels[c].resolution = 10
                self.channels[c].buffer = e + 1
            self.connection.send_byte(CP.CAPTURE_FOUR)
            self.connection.send_byte(
                chosa | (CH123SA << 4) | (0x80 * self.trigger_enabled)
            )

        self.connection.send_int(samples)
        self.connection.send_int(int(timegap * 8))  # 8 MHz clock
        self.connection.get_ack()

    def fetch_data(self, offset_index, samples) -> np.ndarray:
        """Fetch the requested number of samples from specified buffer index.

        The ADC hardware buffer can store up to 10000 samples. During simultaneous
        sampling of multiple channels, the location of the stored samples are offset
        based on the capturing channel. The first channel (which can be remapped with
        the channel_one_map attribute of AnalogAcquisitionHandler instances) has an
        offset of 0. The second, third, and fourth channels are offset by one, two, or
        three multiplied by the number of requested samples.

        Parameters
        ----------
        offset_index : {0, 1, 2, 3}
            Zero-indexed capture channel from which to fetch data. Index 0 fetches data
            from whichever channel was mapped to channel one during capture. Indices
            1-3 fetch data from channels CH2, CH3, and MIC.
        samples : int
            Fetch this many samples from the buffer.

        Example
        -------
        >>> from PSL import achan
        >>> analog_channels = achan.AnalogAcquisitionHandler()
        >>> analog_channels.capture_nonblocking(channels=2, samples=1600, timegap=1)
        # Get the first 1600 samples in the buffer, i.e. indices 0-1599.
        >>> y1 = analog_channels.fetch_data(0, 1600)
        # Get another 1600 samples from the buffer, starting from index 1600.
        >>> y2 = analog_channels.fetch_data(1, 1600)

        Returns
        -------
        numpy.ndarray
            One-dimensional array holding the requested voltages.
        """
        data = bytearray()

        for i in range(int(np.ceil(samples / self.data_splitting))):
            self.connection.send_byte(CP.COMMON)
            self.connection.send_byte(CP.RETRIEVE_BUFFER)
            offset = offset_index * samples + i * self.data_splitting
            self.connection.send_int(offset)
            self.connection.send_int(self.data_splitting)  # Ints to read
            # Reading int by int sometimes causes a communication error.
            data += self.connection.interface.read(self.data_splitting * 2)
            self.connection.get_ack()

        data = [CP.ShortInt.unpack(data[s * 2 : s * 2 + 2])[0] for s in range(samples)]

        return np.array(data)

    def progress(self) -> Tuple[bool, int]:
        """Return the status of a capture call.

        Returns
        -------
        bool, int
            A boolean indicating whether the capture is complete, followed by the
            number of samples currently held in the buffer.
        """
        self.connection.send_byte(CP.ADC)
        self.connection.send_byte(CP.GET_CAPTURE_STATUS)
        conversion_done = self.connection.get_byte()
        samples = self.connection.get_int()
        self.connection.get_ack()

        return bool(conversion_done), samples

    def configure_trigger(self, channel: str, voltage: float, prescaler: int = 0):
        """Configure trigger parameters for capture routines.

        The capture routines will wait until a rising edge of the input signal crosses
        the specified level. The trigger will timeout within 8 ms, and capture will
        start regardless.

        To disable the trigger after configuration, set the trigger_enabled attribute
        of the AnalogAcquisitionHandler instance to False.

        Parameters
        ----------
        channel : {'CH1', 'CH2', 'CH3', 'MIC', 'CAP', 'SEN', 'AN8'}
            The name of the trigger channel.
        voltage : float
            The trigger voltage in volts.
        prescaler : int, optional
            The default value is 0.

        Examples
        --------
        >>> from PSL import achan
        >>> analog_channels = achan.AnalogAcquisitionHandler()
        >>> analog_channels.configure_trigger(channel='CH1', voltage=1.1)
        >>> xy = analog_channels.capture(channels=1, samples=800, timegap=2)
        >>> diff = abs(xy[1, 0] - 1.1)  # Should be small unless a timeout occurred.
        """
        self._trigger_channel = channel

        if channel == self.channel_one_map:
            channel = 0
        else:
            channel == self.CH234.index(channel) + 1

        self.connection.send_byte(CP.ADC)
        self.connection.send_byte(CP.CONFIGURE_TRIGGER)
        # Trigger channel (4lsb) , trigger timeout prescaler (4msb)
        self.connection.send_byte((prescaler << 4) | (1 << channel))  # TODO prescaler?
        level = self.channels[self._trigger_channel].unscale(voltage)
        self.connection.send_int(level)
        self.connection.get_ack()

    def select_range(self, channel: str, voltage_range: Union[int, float]):
        """Set appropriate gain automatically.

        Setting the right voltage range will result in better resolution. In case the
        range specified is 160, an external 10 MΩ resistor must be connected in series
        with the device.

        Parameters
        ----------
        channel : {'CH1', 'CH2'}
            Channel on which to apply gain.
        voltage_range : {16,8,4,3,2,1.5,1,.5,160}

        Examples
        --------
        >>> from PSL import achan´
        >>> analog_channels = achan.AnalogAcquisitionHandler()
        >>> analog_channels.select_range('CH1', 8)
        # Gain set to 2x on CH1. Voltage range ±8 V.
        """
        ranges = [16, 8, 4, 3, 2, 1.5, 1, 0.5, 160]
        if voltage_range in ranges:
            idx = ranges.index(voltage_range)
            gain = GAIN_VALUES[idx]
            self.channels[channel] = gain
        else:
            e = f"Invalid range: {voltage_range}. Valid ranges are {ranges}."
            raise ValueError(e)
