"""Interfaces for communicating with PSLab devices."""

from serial.tools import list_ports

from .connection import ConnectionHandler
from ._serial import SerialHandler
from .wlan import WLANHandler


def detect() -> list[ConnectionHandler]:
    """Detect PSLab devices.

    Returns
    -------
    devices : list[ConnectionHandler]
        Handlers for all detected PSLabs. The returned handlers are disconnected; call
        .connect() before use.
    """
    regex = []

    for vid, pid in zip(SerialHandler._USB_VID, SerialHandler._USB_PID):
        regex.append(f"{vid:04x}:{pid:04x}")

    regex = "(" + "|".join(regex) + ")"
    port_info_generator = list_ports.grep(regex)
    pslab_devices = []

    for port_info in port_info_generator:
        device = SerialHandler(port=port_info.device, baudrate=1000000, timeout=1)

        try:
            device.connect()
        except Exception:
            pass  # nosec
        else:
            pslab_devices.append(device)
        finally:
            device.disconnect()

    try:
        device = WLANHandler()
        device.connect()
    except Exception:
        pass  # nosec
    else:
        pslab_devices.append(device)
    finally:
        device.disconnect()

    return pslab_devices


def autoconnect() -> ConnectionHandler:
    """Automatically connect when exactly one device is present.

    Returns
    -------
    device : ConnectionHandler
        A handler connected to the detected PSLab device. The handler is connected; it
        is not necessary to call .connect before use().
    """
    devices = detect()

    if not devices:
        msg = "device not found"
        raise ConnectionError(msg)

    if len(devices) > 1:
        msg = f"autoconnect failed, multiple devices detected: {devices}"
        raise ConnectionError(msg)

    device = devices[0]
    device.connect()
    return device
