"""Contains modules for interfacing with the PSLab's I2C, SPI, and UART buses."""


class classmethod_(classmethod):
    """Support chaining classmethod and property."""

    def __init__(self, f):
        self.f = f
        super().__init__(f)

    def __get__(self, obj, cls=None):
        if cls is None:
            cls = type(obj)
        if isinstance(self.f, property):
            return self.f.__get__(cls)
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
