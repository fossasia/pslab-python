"""Contains modules for interfacing with the PSLab's I2C, SPI, and UART buses."""

import sys


class classmethod_(classmethod):
    """Support chaining classmethod and property."""

    def __init__(self, f):
        self.f = f
        super().__init__(f)

    def __get__(self, obj, cls=None):
        # classmethod() to support chained decorators; new in python 3.9.
        if sys.version_info < (3, 9) and isinstance(self.f, property):
            return self.f.__get__(cls)
        else:
            return super().__get__(obj, cls)


from pslab.bus.i2c import I2CMaster, I2CSlave  # noqa: E402
from pslab.bus.spi import SPIMaster, SPISlave  # noqa: E402
from pslab.bus.uart import UART  # noqa: E402

__all__ = (
    "I2CMaster",
    "I2CSlave",
    "SPIMaster",
    "SPISlave",
    "UART",
)
