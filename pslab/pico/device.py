"""High-level PSLab Pico device entry point."""

from __future__ import annotations

from typing import Optional

from pslab.pico.transport import PicoTransport, PicoUsbTransport, PicoWifiTransport, ScpiClient


class PicoDevice:
    """Connected PSLab Pico firmware device.

    The Pico firmware speaks SCPI over USB CDC or over the ESP32-C3 TCP bridge.
    This object owns the shared SCPI client used by future Pico instruments.
    """

    def __init__(self, client: ScpiClient) -> None:
        self.scpi = client

    @classmethod
    def usb(
        cls,
        port: Optional[str] = None,
        baudrate: int = 115200,
        timeout: Optional[float] = 2.0,
    ) -> "PicoDevice":
        """Create a Pico device using USB CDC."""

        return cls(ScpiClient(PicoUsbTransport(port, baudrate, timeout)))

    @classmethod
    def wifi(
        cls,
        host: str,
        port: int = PicoWifiTransport.DEFAULT_PORT,
        timeout: Optional[float] = 2.0,
    ) -> "PicoDevice":
        """Create a Pico device using the ESP TCP SCPI bridge."""

        return cls(ScpiClient(PicoWifiTransport(host, port, timeout)))

    @classmethod
    def from_transport(cls, transport: PicoTransport) -> "PicoDevice":
        """Create a Pico device from a custom transport."""

        return cls(ScpiClient(transport))

    def connect(self) -> None:
        """Open the underlying transport."""

        self.scpi.connect()

    def close(self) -> None:
        """Close the underlying transport."""

        self.scpi.close()

    def identify(self) -> str:
        """Return the firmware identification string."""

        return self.scpi.identify()

    def reset(self) -> None:
        """Reset all instrument state in the firmware."""

        self.scpi.reset()

    def clear_status(self) -> None:
        """Clear the SCPI status and error queues."""

        self.scpi.clear_status()

    def set_transport(self, mode: str) -> None:
        """Select capture data transport: ``USB``, ``WIFI``, or ``AUTO``."""

        self.scpi.set_transport(mode)

    def get_transport(self) -> str:
        """Return the selected capture data transport."""

        return self.scpi.get_transport()

    def wifi_status(self):
        """Return Wi-Fi transport status counters."""

        return self.scpi.wifi_status()

    def __enter__(self) -> "PicoDevice":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
