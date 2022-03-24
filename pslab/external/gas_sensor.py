"""Gas sensors can be used to measure the concentration of certain gases."""

from typing import Callable, Union

from pslab import Multimeter
from pslab.serial_handler import SerialHandler


class MQ135:
    """MQ135 is a cheap gas sensor that can detect several harmful gases.

    The MQ135 is most suitable for detecting flammable gases, but can also be
    used to measure CO2.

    Parameters
    ----------
    gas : {CO2, CO, EtOH, NH3, Tol, Ace}
        The gas to be detected:
            CO2: Carbon dioxide
            CO: Carbon monoxide
            EtOH: Ethanol
            NH3: Ammonia
            Tol: Toluene
            Ace: Acetone
    r_load : float
        Load resistance in ohm.
    device : :class:`SerialHandler`, optional
        Serial connection to PSLab device. If not provided, a new one will be
        created.
    channel : str, optional
        Analog input on which to monitor the sensor output voltage. The default
        value is CH1. Be aware that the sensor output voltage can be as high
        as 5 V, depending on load resistance and gas concentration.
    r0 : float, optional
        The sensor resistance when exposed to 100 ppm NH3 at 20 degC and 65%
        RH. Varies between individual sensors. Optional, but gas concentration
        cannot be measured unless R0 is known. If R0 is not known,
        :meth:`measure_r0` to find it.
    temperature : float or Callable, optional
        Ambient temperature in degC. The default value is 20. A callback can
        be provided in place of a fixed value.
    humidity : float or Callable, optional
        Relative humidity between 0 and 1. The default value is 0.65. A
        callback can be provided in place of a fixed value.
    """

    # Parameters manually extracted from data sheet.
    # ppm = A * (Rs/R0) ^ B
    _PARAMS = {
        "CO2": [109, -2.88],
        "CO": [583, -3.93],
        "EtOH": [76.4, -3.18],
        "NH3": [102, -2.49],
        "Tol": [44.6, -3.45],
        "Ace": [33.9, -3.42],
    }

    # Assuming second degree temperature dependence and linear humidity dependence.
    _TEMPERATURE_CORRECTION = [3.28e-4, -2.55e-2, 1.38]
    _HUMIDITY_CORRECTION = -2.24e-1

    def __init__(
        self,
        gas: str,
        r_load: float,
        device: SerialHandler = None,
        channel: str = "CH1",
        r0: float = None,
        temperature: Union[float, Callable] = 20,
        humidity: Union[float, Callable] = 0.65,
    ):
        self._multimeter = Multimeter(device)
        self._params = self._PARAMS[gas]
        self.channel = channel
        self.r_load = r_load
        self.r0 = r0
        self.vcc = 5

        if isinstance(temperature, Callable):
            self._temperature = temperature
        else:

            def _temperature():
                return temperature

            self._temperature = _temperature

        if isinstance(humidity, Callable):
            self._humidity = humidity
        else:

            def _humidity():
                return humidity

            self._humidity = _humidity

    @property
    def _voltage(self):
        return self._multimeter.measure_voltage(self.channel)

    @property
    def _correction(self):
        """Correct sensor resistance for temperature and humidity.

        Coefficients are averages of curves fitted to temperature data for 33%
        and 85% relative humidity extracted manually from the data sheet.
        Humidity dependence is assumed to be linear, and is centered on 65% RH.
        """
        t = self._temperature()
        h = self._humidity()
        a, b, c, d = *self._TEMPERATURE_CORRECTION, self._HUMIDITY_CORRECTION
        return a * t**2 + b * t + c + d * (h - 0.65)

    @property
    def _sensor_resistance(self):
        return (self.vcc / self._voltage - 1) * self.r_load / self._correction

    def measure_concentration(self):
        """Measure the concentration of the configured gas.

        Returns
        -------
        concentration : float
            Gas concentration in ppm.
        """
        try:
            return (
                self._params[0] * (self._sensor_resistance / self.r0) ** self._params[1]
            )
        except TypeError:
            raise TypeError("r0 is not set.")

    def measure_r0(self, gas_concentration: float):
        """Determine sensor resistance at 100 ppm NH3 in otherwise clean air.

        For best results, monitor R0 over several hours and use the average
        value.

        The sensor resistance at 100 ppm NH3 (R0) is used as a reference
        against which the present sensor resistance must be compared in order
        to calculate gas concentration.

        R0 can be determined by calibrating the sensor at any known gas
        concentration.

        Parameters
        ----------
        gas_concentration : float
            A known concentration of the configured gas in ppm.

        Returns
        -------
        r0 : float
            The sensor resistance at 100 ppm NH3 in ohm.
        """
        return self._sensor_resistance * (gas_concentration / self._params[0]) ** (
            1 / -self._params[1]
        )
