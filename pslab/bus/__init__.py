"""Contains modules for interfacing with the PSLab's I2C, SPI, and UART buses."""

from pslab.bus.i2c import I2CMaster, I2CSlave
from pslab.bus.spi import SPIMaster, SPISlave
from pslab.bus.uart import UART

__all__ = (
    "I2CMaster",
    "I2CSlave",
    "SPIMaster",
    "SPISlave",
    "UART",
)
