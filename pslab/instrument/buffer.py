"""The PSLab has a sample buffer where collected data is stored temporarily."""

import pslab.protocol as CP


class ADCBufferMixin:
    """Mixin for classes that need to read or write to the ADC buffer."""

    def fetch_buffer(self, samples: int, starting_position: int = 0):
        """Fetch a section of the ADC buffer.

        Parameters
        ----------
        samples : int
            Number of samples to fetch.
        starting_position : int, optional
            Location in the ADC buffer to start from. By default samples will
            be fetched from the beginning of the buffer.

        Returns
        -------
        received : list of int
            List of received samples.
        """
        received = []
        buf_size = 128
        remaining = samples
        idx = starting_position

        while remaining > 0:
            self._device.send_byte(CP.COMMON)
            self._device.send_byte(CP.RETRIEVE_BUFFER)
            self._device.send_int(idx)
            samps = min(remaining, buf_size)
            self._device.send_int(samps)
            received += [self._device.get_int() for _ in range(samps)]
            self._device.get_ack()
            remaining -= samps
            idx += samps

        return received

    def clear_buffer(self, samples: int, starting_position: int = 0):
        """Clear a section of the ADC buffer.

        Parameters
        ----------
        samples : int
            Number of samples to clear from the buffer.
        starting_position : int, optional
            Location in the ADC buffer to start from. By default samples will
            be cleared from the beginning of the buffer.
        """
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.CLEAR_BUFFER)
        self._device.send_int(starting_position)
        self._device.send_int(samples)
        self._device.get_ack()

    def fill_buffer(self, data: list[int], starting_position: int = 0):
        """Fill a section of the ADC buffer with data.

        Parameters
        ----------
        data : list of int
            Values to write to the ADC buffer.
        starting_position : int, optional
            Location in the ADC buffer to start from. By default writing will
            start at the beginning of the buffer.
        """
        buf_size = 128
        idx = starting_position
        remaining = len(data)

        while remaining > 0:
            self._device.send_byte(CP.COMMON)
            self._device.send_byte(CP.FILL_BUFFER)
            self._device.send_int(idx)
            samps = min(remaining, buf_size)
            self._device.send_int(samps)

            for value in data[idx : idx + samps]:
                self._device.send_int(value)

            self._device.get_ack()
            idx += samps
            remaining -= samps
