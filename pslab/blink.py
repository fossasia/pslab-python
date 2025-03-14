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
    toggle = time.time()
    state = 0

    while True:
        if period / 2 < (time.time() - toggle) * 1000:
            if state:
                # Turn off LED.
                psl.rgb_led((0, 0, 0))
            else:
                # Turn on LED.
                psl.rgb_led(color)

            state = not state
            toggle = time.time()


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
