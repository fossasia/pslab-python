"""FOSSASIA Summit 2025 - PSLab Development 101 exercises."""

import time

import pslab
import pslab.protocol as CP


def blink(psl: pslab.ScienceLab, color: tuple[int, int, int], period: int) -> None:
    """Blink the onbard RGB LED.

    Parameters
    ----------
    psl : pslab.ScienceLab
    color : tuple[int, int, int]
        Green, red, blue, each in range 0-255.
    period : int
        Blink period in milliseconds.
    """


def blink_c(psl: pslab.ScienceLab, color: tuple[int, int, int], period: int) -> None:
    """Blink the RGB LED using firmware implementation.

    Parameters
    ----------
    psl : pslab.ScienceLab
    color : tuple[int, int, int]
        Green, red, blue, each in range 0-255.
    period : int
        Blink period in milliseconds.
    """
    if not period:
        cmd = CP.NONSTANDARD_IO + CP.Byte.pack(11)
        psl.device.exchange(cmd)
        psl.rgb_led(color)
        return

    cmd = CP.NONSTANDARD_IO + CP.Byte.pack(10)
    args = CP.ShortInt.pack(period)
    args += bytes(color)
    psl.device.exchange(cmd, args)
