"""BMP180 Altimeter."""

import time
import logging
import struct
from pslab.bus import I2CSlave

# BMP180 default address
_ADDRESS = 0x77

# Operating Modes
_ULTRALOWPOWER = 0
_STANDARD = 1
_HIGHRES = 2
_ULTRAHIGHRES = 3

# BMP180 Registers
_CAL_AC1 = 0xAA  # R   Calibration data (16 bits)
_CAL_AC2 = 0xAC  # R   Calibration data (16 bits)
_CAL_AC3 = 0xAE  # R   Calibration data (16 bits)
_CAL_AC4 = 0xB0  # R   Calibration data (16 bits)
_CAL_AC5 = 0xB2  # R   Calibration data (16 bits)
_CAL_AC6 = 0xB4  # R   Calibration data (16 bits)
_CAL_B1 = 0xB6  # R   Calibration data (16 bits)
_CAL_B2 = 0xB8  # R   Calibration data (16 bits)
_CAL_MB = 0xBA  # R   Calibration data (16 bits)
_CAL_MC = 0xBC  # R   Calibration data (16 bits)
_CAL_MD = 0xBE  # R   Calibration data (16 bits)
_CONTROL = 0xF4
_TEMPDATA = 0xF6
_PRESSUREDATA = 0xF6

# Commands
_READTEMPCMD = 0x2E
_READPRESSURECMD = 0x34

_logger = logging.getLogger(__name__)


class BMP180(I2CSlave):
    """Class to interface with the BMP180 Altimeter.

    Parameters
    ----------
    mode : int, optional
        The mode of operation for the sensor, determining the oversampling setting.
        The default mode is `_HIGHRES`. This parameter affects the precision and speed
        of the temperature and pressure measurements.

    **kwargs : dict, optional
        Additional keyword arguments, such as:
        - address (int): The I2C address of the BMP180 sensor. Default is `_ADDRESS`.

    Attributes
    ----------
    temperature : float
        The measured temperature in degrees Celsius.

    pressure : float
        The measured pressure in Pa (Pascals).

    altitude : float
        The calculated altitude in meters based on the current pressure reading
        and a reference sea level pressure.
    """

    NUMPLOTS = 3
    PLOTNAMES = ["Temperature", "Pressure", "Altitude"]
    name = "BMP180 Altimeter"

    def __init__(self, mode=_HIGHRES, **kwargs):
        self._ADDRESS = kwargs.get("address", _ADDRESS)
        super().__init__(self._ADDRESS)
        self._mode = mode

        # Load calibration values
        self._ac1 = self._read_int16(_CAL_AC1)
        self._ac2 = self._read_int16(_CAL_AC2)
        self._ac3 = self._read_int16(_CAL_AC3)
        self._ac4 = self._read_uint16(_CAL_AC4)
        self._ac5 = self._read_uint16(_CAL_AC5)
        self._ac6 = self._read_uint16(_CAL_AC6)
        self._b1 = self._read_int16(_CAL_B1)
        self._b2 = self._read_int16(_CAL_B2)
        self._mb = self._read_int16(_CAL_MB)
        self._mc = self._read_int16(_CAL_MC)
        self._md = self._read_int16(_CAL_MD)

        _logger.debug(f"ac1: {self._ac1}")
        _logger.debug(f"ac2: {self._ac2}")
        _logger.debug(f"ac3: {self._ac3}")
        _logger.debug(f"ac4: {self._ac4}")
        _logger.debug(f"ac5: {self._ac5}")
        _logger.debug(f"ac6: {self._ac6}")
        _logger.debug(f"b1: {self._b1}")
        _logger.debug(f"b2: {self._b2}")
        _logger.debug(f"mb: {self._mb}")
        _logger.debug(f"mc: {self._mc}")
        _logger.debug(f"md: {self._md}")

    def _read_int16(self, addr):
        BE_INT16 = struct.Struct(">h")  # signed short, big endian
        return BE_INT16.unpack(self.read(2, addr))[0]

    def _read_uint16(self, addr):
        BE_UINT16 = struct.Struct(">H")  # unsigned short, big endian
        return BE_UINT16.unpack(self.read(2, addr))[0]

    def _read_raw_temperature(self):
        """Read the raw temperature from the sensor."""
        self.write([_READTEMPCMD], _CONTROL)
        time.sleep(0.005)
        raw = self._read_uint16(_TEMPDATA)
        return raw

    @property
    def temperature(self):
        """Get the actual temperature in degrees celsius."""
        ut = self._read_raw_temperature()
        # Calculations from section 3.5 of the datasheet
        x1 = ((ut - self._ac6) * self._ac5) >> 15
        x2 = (self._mc << 11) // (x1 + self._md)
        b5 = x1 + x2
        temp = ((b5 + 8) >> 4) / 10.0
        return temp

    @property
    def oversampling(self):
        """oversampling : int
        The oversampling setting used by the sensor. This attribute is settable and
        determines the trade-off between measurement accuracy and speed. Possible values
        include `_ULTRALOWPOWER`, `_STANDARD`, `_HIGHRES`, and `_ULTRAHIGHRES`.
        """
        return self._mode

    @oversampling.setter
    def oversampling(self, value):
        self._mode = value

    def _read_raw_pressure(self):
        """Read the raw pressure level from the sensor."""
        delays = [0.005, 0.008, 0.014, 0.026]
        self.write([_READPRESSURECMD + (self._mode << 6)], _CONTROL)
        time.sleep(delays[self._mode])
        msb = self.read_byte(_PRESSUREDATA) & 0xFF
        lsb = self.read_byte(_PRESSUREDATA + 1) & 0xFF
        xlsb = self.read_byte(_PRESSUREDATA + 2) & 0xFF
        raw = ((msb << 16) + (lsb << 8) + xlsb) >> (8 - self._mode)
        return raw

    @property
    def pressure(self):
        """Get the actual pressure in Pascals."""
        ut = self._read_raw_temperature()
        up = self._read_raw_pressure()
        # Calculations from section 3.5 of the datasheet
        x1 = ((ut - self._ac6) * self._ac5) >> 15
        x2 = (self._mc << 11) // (x1 + self._md)
        b5 = x1 + x2
        # Pressure Calculations
        b6 = b5 - 4000
        x1 = (self._b2 * (b6 * b6) >> 12) >> 11
        x2 = (self._ac2 * b6) >> 11
        x3 = x1 + x2
        b3 = (((self._ac1 * 4 + x3) << self._mode) + 2) // 4
        x1 = (self._ac3 * b6) >> 13
        x2 = (self._b1 * ((b6 * b6) >> 12)) >> 16
        x3 = ((x1 + x2) + 2) >> 2
        b4 = (self._ac4 * (x3 + 32768)) >> 15
        b7 = (up - b3) * (50000 >> self._mode)
        if b7 < 0x80000000:
            p = (b7 * 2) // b4
        else:
            p = (b7 // b4) * 2
        x1 = (p >> 8) * (p >> 8)
        x1 = (x1 * 3038) >> 16
        x2 = (-7357 * p) >> 16
        pres = p + ((x1 + x2 + 3791) >> 4)
        return pres

    @property
    def altitude(self):
        # Calculation from section 3.6 of datasheet
        pressure = float(self.pressure)
        alt = 44330.0 * (1.0 - pow(pressure / 101325.0, (1.0 / 5.255)))
        return alt
