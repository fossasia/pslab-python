"""Contains modules for interfacing with the PSLab's I2C, SPI, and UART buses.

(SPI and UART still TODO)
"""
from pslab.bus.i2c import I2CMaster, I2CSlave

__all__ = (
    "I2CMaster",
    "I2CSlave",
)
