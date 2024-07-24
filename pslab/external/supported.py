import inspect

from pslab.external import HMC5883L
from pslab.external import MPU6050
from pslab.external import MLX90614
from pslab.external import BMP180
from pslab.external import TSL2561
from pslab.external import SHT21
from pslab.external import BH1750
from pslab.external import SSD1306
from pslab.external import VL531X

supported = {
    0x68: MPU6050,  # 3-axis gyro,3-axis accel,temperature
    0x1E: HMC5883L,  # 3-axis magnetometer
    0x5A: MLX90614,  # Passive IR temperature sensor
    0x77: BMP180,  # Pressure, Temperature, altitude
    0x39: TSL2561,  # Luminosity
    0x40: SHT21,  # Temperature, Humidity
    0x23: BH1750,  # Luminosity
    # 0x3C:SSD1306,    #OLED display
    0x29: VL531X,  # Time-of-Flight Proximity Sensor
}

# auto generated map of names to classes
nameMap = {}
for a in supported:
    nameMap[supported[a].__name__.split('.')[-1]] = (supported[a])
