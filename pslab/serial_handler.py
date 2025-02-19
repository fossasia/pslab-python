"""Deprecated provider of SerialHandler."""

import warnings

from pslab.connection import SerialHandler, autoconnect

warnings.warn(
    "pslab.serial_handler is deprecated and will be removed in a future release. "
    "Use pslab.connection instead."
)


class _SerialHandler(SerialHandler):
    def __init__(
        self,
        port: str | None = None,
        baudrate: int = 1000000,
        timeout: float = 1.0,
    ) -> None:
        if port is None:
            tmp_handler = autoconnect()
            port = tmp_handler.port
            tmp_handler.disconnect()

        super().__init__(port=port, baudrate=baudrate, timeout=timeout)
        self.connect()


SerialHandler = _SerialHandler
