"""Proof of concept TCD1304 driver.

This driver can only drive the TCD1304 in normal mode, not electronic shutter
mode. This is because the PSLab can (currently) only output two different PWM
frequencies simultaneously, and electronic shutter mode requires three.

Furthermode, the clock frequencies are locked to 2 MHz (master) and 125 Hz (SH
and ICG). The reason is the following:

The ICG period must be greater than the readout period, which is:
    master clock period * 4 * number of pixels = 7.4 ms
7.4 ms -> 135 Hz, which is therefore the fastest the ICG clock can run.

The lowest possible frequency the PSLab can generate with sufficient
clock precision is 123 Hz. Below that the 16-bit timer that drives the
PWM must be prescaled so much that we can no longer satisfy the TCD1304's
timing requirements.

Thus, the range of possible ICG frequencies is [123, 135], which is so small
that it makes more sense to just lock it to 125 Hz, which has the added
advantage of being an even divisor of the PSLab's MCU frequency (64 MHz).

It should be possible to increase the master clock to 4 MHz, which would also
make ICG frequencies up to 250 Hz possible. However, the readout period would
be 3.7 ms, which the PSLab's oscilloscope might struggle to capture with good
quality.
"""

from typing import List

from numpy import ndarray

from pslab import Oscilloscope
from pslab import PowerSupply
from pslab import PWMGenerator
from pslab.instrument.waveform_generator import _get_wavelength
from pslab.protocol import MAX_SAMPLES
from pslab.serial_handler import SerialHandler


class TCD1304:
    def __init__(self, device: SerialHandler):
        self._pwm = PWMGenerator(device)
        self._oscilloscope = Oscilloscope(device)
        self._sh_frequency = 125

    def start_clocks(self, inverted: bool = True):
        """Start the Master, SH, and ICG clocks.

        Parameters
        ----------
        inverted : bool, optional
            The TCD1304 datasheet recommends placing a hex inverter between the
            sensor and the MCU. By default, the clocks are therefore inverted
            relative to what they should be to drive the sensor. If you do not
            use a hex inverter, set this to False.

        Returns
        -------
        None.

        """
        self._pwm.map_reference_clock("SQ1", 6)  # 2 MHz

        resolution = _get_wavelength(self._sh_frequency)[0] ** -1
        # Timing requirements:
        # (1) The SH clock must go high between 100 ns to 1000 ns after the ICG
        # clock goes low.
        # (2) The SH clock must stay high for at least 1 µs.
        # (3) The ICG clock must stay low at least 1 µs after the SH clock goes
        # low.
        # I got the following numbers through trial and error. They meet the
        # above requirements.
        # TODO: Calculate appropriate duty cycles and phases.
        magic_numbers = [
            12 * resolution,
            48 * resolution,
            16 * resolution,
            1 - 42 * resolution,
        ]

        if inverted:
            self._pwm.generate(
                ["SQ2", "SQ3"],
                frequency=self._sh_frequency,
                duty_cycles=[1 - magic_numbers[0], magic_numbers[1]],
                phases=[magic_numbers[2], 0],
            )
        else:
            self._pwm.generate(
                ["SQ2", "SQ3"],
                frequency=self._sh_frequency,
                duty_cycles=[magic_numbers[0], 1 - magic_numbers[1]],
                phases=[magic_numbers[3], 0],
            )

    def stop_clocks(self):
        """Stop the Master, SH, and ICG clocks.

        Returns
        -------
        None.

        """
        self._pwm.set_state(sq1=0, sq2=0, sq3=0)

    def read(self, analogin: str = "CH1", trigger: str = "CH2") -> List[ndarray]:
        """Read the sensor's analog output.

        Connect one of the PSLab's analog inputs to the sensor's analog output.

        Parameters
        ----------
        channel : str, optional
            The analog input connected to the sensor's OS pin.
            Defaults to "CH1".
        trigger : str, optional
            The analog input connected to the sensor's ICG pin.
            Defaults to "CH2".

        Returns
        -------
        List[ndarray]
            Timestamps and corresponding voltages.

        """
        return self._oscilloscope.capture(
            analogin, 8000, 1, trigger=3, trigger_channel=trigger
        )
