"""MLX90614 infrared thermometer.

This module provides an interface for the MLX90614 non-contact infrared
temperature sensor, connected to the PSLab via I2C.

Examples
--------
Read object (target) temperature:

>>> from pslab.external.MLX90614 import MLX90614
>>> sensor = MLX90614()
>>> sensor.get_object_temperature()
25.73

Read ambient (sensor body) temperature:

>>> sensor.get_ambient_temperature()
24.18
"""

import logging
from typing import List, Optional

from pslab.bus.i2c import I2CSlave
from pslab.connection import ConnectionHandler

logger = logging.getLogger(__name__)


class MLX90614(I2CSlave):
    """MLX90614 non-contact infrared temperature sensor.

    The MLX90614 is a passive infrared (PIR) sensor that measures
    temperature without physical contact. It can measure both the
    temperature of a target object and its own ambient temperature.

    The sensor communicates over SMBus (a subset of I2C) at address 0x5A
    and supports bus speeds up to 100 kHz.

    Parameters
    ----------
    device : :class:`ConnectionHandler`, optional
        Serial connection to PSLab device. If not provided, a new one
        will be created.

    Attributes
    ----------
    NUMPLOTS : int
        Number of data plots for GUI integration.
    PLOTNAMES : list of str
        Labels for data plots.
    name : str
        Human-readable sensor name.
    """

    _ADDRESS = 0x5A
    _OBJ_REGISTER = 0x07
    _AMB_REGISTER = 0x06
    NUMPLOTS = 1
    PLOTNAMES = ["Temp"]
    name = "PIR temperature"

    def __init__(self, device: Optional[ConnectionHandler] = None):
        super().__init__(self._ADDRESS, device=device)
        self._source = self._OBJ_REGISTER
        self.name = "Passive IR temperature sensor"

    def select_source(self, source: str):
        """Select which temperature source to read.

        Parameters
        ----------
        source : str
            Either ``'object temperature'`` or ``'ambient temperature'``.
        """
        if source == "object temperature":
            self._source = self._OBJ_REGISTER
        elif source == "ambient temperature":
            self._source = self._AMB_REGISTER

    def read_reg(self, register: int):
        """Read and log a 16-bit register value.

        Parameters
        ----------
        register : int
            Register address to read (0x00–0x20).
        """
        data = self.read(2, register)
        value = data[0] | (data[1] << 8)
        logger.info("Register %s: %s", hex(register), hex(value))

    def get_raw(self) -> Optional[List[float]]:
        """Read raw temperature from the currently selected source.

        The raw value is read as a 3-byte SMBus word (LSB, MSB, PEC)
        and converted from the sensor's internal unit (0.02 K per LSB)
        to degrees Celsius.

        Returns
        -------
        list of float or None
            Single-element list with temperature in °C, or None if
            the read failed.
        """
        data = self.read(3, self._source)

        if data and len(data) == 3:
            raw = (((data[1] & 0x007F) << 8) + data[0]) * 0.02 - 0.01
            return [raw - 273.15]

        return None

    def get_object_temperature(self) -> Optional[float]:
        """Read the temperature of the target object.

        Returns
        -------
        float or None
            Object temperature in °C, or None if the read failed.
        """
        self._source = self._OBJ_REGISTER
        result = self.get_raw()
        return result[0] if result else None

    def get_ambient_temperature(self) -> Optional[float]:
        """Read the ambient (sensor body) temperature.

        Returns
        -------
        float or None
            Ambient temperature in °C, or None if the read failed.
        """
        self._source = self._AMB_REGISTER
        result = self.get_raw()
        return result[0] if result else None
