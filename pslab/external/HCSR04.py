from PSL.commands_proto import CP


class HCSR04:
    """Read data from ultrasonic distance sensor HC-SR04/HC-SR05.

    Sensors must have separate trigger and output pins.
    First a 10 µs pulse is output on SQ1. SQ1 must be connected to the TRIG pin
    on the sensor prior to use.

    Upon receiving this pulse, the sensor emits a sequence of sound pulses, and
    the logic level of its output pin (which we will monitor via LA1) is also
    set high.  The logic level goes LOW when the sound packet returns to the
    sensor, or when a timeout occurs.

    The ultrasound sensor outputs a series of eight sound pulses at 40 kHz,
    which corresponds to a time period of 25 µs per pulse. These pulses reflect
    off of the nearest object in front of the sensor, and return to it. The
    time between sending and receiving of the pulse packet is used to estimate
    the distance. If the reflecting object is either too far away or absorbs
    sound, less than eight pulses may be received, and this can cause a
    measurement error of 25 µs which corresponds to 8 mm.

    The sensor requires a 5 V supply. You may set SQ2 to HIGH:
    >>> psl.pwm_generator.set_state(sq2=True)
    and use that as the power supply.

    Returns 0 in case of timeout.
    """

    def __init__(self, device):
        self._device = device

    def estimate_distance(self):
        self._device.send_byte(CP.NONSTANDARD_IO)
        self._device.send_byte(CP.HCSR04_HEADER)

        timeout_msb = int((0.3 * 64e6)) >> 16
        self._device.send_int(timeout_msb)

        A = self._device.get_long()
        B = self._device.get_long()
        tmt = self._device.get_int()
        self._device.get_ack()

        if (tmt >= timeout_msb or B == 0):
            return 0

        return 330 * (B - A + 20) / 64e6 / 2
