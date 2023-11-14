import time
from pslab.bus import I2CSlave


class CCS811(I2CSlave):
    MODE_IDLE = 0  # Idle (Measurements are disabled in this mode)
    MODE_CONTINUOUS = 1  # Constant power mode, IAQ measurement every 1s
    MODE_PULSE = 2  # Pulse heating mode IAQ measurement every 10 seconds
    MODE_LOW_POWER = 3  # Low power pulse heating mode IAQ measurement every 60 seconds
    MODE_CONTINUOUS_FAST = 4  # Constant power mode, sensor measurement every 250ms

    _ADDRESS = 0x5A

    # Figure 14: CCS811 Application Register Map
    _STATUS = 0x00  # STATUS # R 1 byte Status register
    # MEAS_MODE # R/W 1 byte Measurement mode and conditions register Algorithm result.
    # The most significant 2 bytes contain a up to ppm estimate of the equivalent
    # CO2 (eCO2) level, and
    _MEAS_MODE = 0x01
    # ALG_RESULT_DATA # R 8 bytes the next two bytes contain appb estimate of the total
    # VOC level. Raw ADC data values for resistance and current source.
    _ALG_RESULT_DATA = 0x02
    # RAW_DATA # R 2 bytes used. Temperature and humidity data can be written to
    _RAW_DATA = 0x03
    # ENV_DATA # W 4 bytes enable compensation Thresholds for operation when interrupts
    # are only
    _ENV_DATA = 0x05
    # THRESHOLDS # W 4 bytes generated when eCO2 ppm crosses a threshold The encoded
    # current baseline value can be read. A
    _THRESHOLDS = 0x10
    # BASELINE # R/W 2 bytes previously saved encoded baseline can be written.
    _BASELINE = 0x11
    _HW_ID = 0x20  # HW_ID # R 1 byte Hardware ID. The value is 0x81
    # HW Version # R 1 byte Hardware Version. The value is 0x1X FirmwareBoot Version.
    # The first 2 bytes contain the
    _HW = 0x21
    # FW_Boot_Version # R 2 bytes firmware version number for the boot code. Firmware
    # Application Version. The first 2 bytes contain
    _FW_BOOT_VERSION = 0x23
    # FW_App_Version # R 2 bytes the firmware version number for the application code
    _FW_APP_VERSION = 0x24
    # Internal_State # R 1 byte Internal Status register Error ID. When the status
    # register reports an error its
    _INTERNAL_STATE = 0xA0
    # ERROR_ID # R 1 byte source is located in this register If the correct 4 bytes
    # ( 0x11 0xE5 0x72 0x8A) are written
    _ERROR_ID = 0xE0
    # SW_RESET # W 4 bytes to this register in a single sequence the device will reset
    # and return to BOOT mode.
    _SW_RESET = 0xFF

    # Figure 25: CCS811 Bootloader Register Map
    # Address Register R/W Size Description
    _STATUS = 0x00
    _HW_ID = 0x20
    _HW_Version = 0x21
    _APP_ERASE = 0xF1
    _APP_DATA = 0xF2
    _APP_VERIFY = 0xF3
    _APP_START = 0xF4
    _SW_RESET = 0xFF

    def __init__(self, address=None, device=None):
        super().__init__(address or self._ADDRESS, device)
        self.fetchID()
        self.softwareReset()

    def softwareReset(self):
        self.write([0x11, 0xE5, 0x72, 0x8A], self._SW_RESET)

    def fetchID(self):
        hardware_id = (self.read(1, self._HW_ID))[0]
        time.sleep(0.02)  # 20ms
        hardware_version = (self.read(1, self._HW_Version))[0]
        time.sleep(0.02)  # 20ms
        boot_version = (self.read(2, self._FW_BOOT_VERSION))[0]
        time.sleep(0.02)  # 20ms
        app_version = (self.read(2, self._FW_APP_VERSION))[0]

        return {
            "hardware_id": hardware_id,
            "hardware_version": hardware_version,
            "boot_version": boot_version,
            "app_version": app_version,
        }

    def app_erase(self):
        self.write([0xE7, 0xA7, 0xE6, 0x09], self._APP_ERASE)
        time.sleep(0.3)

    def app_start(self):
        self.write([], self._APP_START)

    def set_measure_mode(self, mode):
        self.write([mode << 4], self._MEAS_MODE)

    def get_measure_mode(self):
        print(self.read(10, self._MEAS_MODE))

    def get_status(self):
        status = (self.read(1, self._STATUS))[0]
        return status

    def decode_status(self, status):
        s = ""
        if (status & (1 << 7)) > 0:
            s += "Sensor is in application mode"
        else:
            s += "Sensor is in boot mode"
        if (status & (1 << 6)) > 0:
            s += ", APP_ERASE"
        if (status & (1 << 5)) > 0:
            s += ", APP_VERIFY"
        if (status & (1 << 4)) > 0:
            s += ", APP_VALID"
        if (status & (1 << 3)) > 0:
            s += ", DATA_READY"
        if (status & 1) > 0:
            s += ", ERROR"
        return s

    def decode_error(self, error_id):
        s = ""
        if (error_id & (1 << 0)) > 0:
            s += (
                ", The CCS811 received an I²C write request addressed to this station "
                "but with invalid register address ID"
            )
        if (error_id & (1 << 1)) > 0:
            s += (
                ", The CCS811 received an I²C read request to a mailbox ID that is "
                "invalid"
            )
        if (error_id & (1 << 2)) > 0:
            s += (
                ", The CCS811 received an I²C request to write an unsupported mode to "
                "MEAS_MODE"
            )
        if (error_id & (1 << 3)) > 0:
            s += (
                ", The sensor resistance measurement has reached or exceeded the "
                "maximum range"
            )
        if (error_id & (1 << 4)) > 0:
            s += ", The Heater current in the CCS811 is not in range"
        if (error_id & (1 << 5)) > 0:
            s += ", The Heater voltage is not being applied correctly"
        return "Error: " + s[2:]

    def measure(self):
        data = self.read(8, self._ALG_RESULT_DATA)
        eCO2 = data[0] * 256 + data[1]
        eTVOC = data[2] * 256 + data[3]
        status = data[4]
        error_id = data[5]
        # raw_data = 256 * data[6] + data[7]
        # raw_current = raw_data >> 10
        # raw_voltage = (raw_data & ((1 << 10) - 1)) * (1.65 / 1023)

        result = {"eCO2": eCO2, "eTVOC": eTVOC, "status": status, "error_id": error_id}

        if error_id > 0:
            raise RuntimeError(self.decodeError(error_id))
        return result
