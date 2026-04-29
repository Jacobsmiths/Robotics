from machine import I2C, Pin
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400_000)
print(i2c.scan())
from machine import I2C, Pin
import time

# AS5600 I2C address and register
AS5600_ADDR = 0x36
RAW_ANGLE_REG = 0x0C  # 12-bit raw angle (2 bytes)

# Init I2C — GP0=SDA, GP1=SCL
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400_000)

def read_angle_raw():
    """Returns raw 12-bit value (0–4095)."""
    data = i2c.readfrom_mem(AS5600_ADDR, RAW_ANGLE_REG, 2)
    return ((data[0] & 0x0F) << 8) | data[1]

def read_angle_deg():
    """Returns angle in degrees (0.0–359.9)."""
    return read_angle_raw() * 360 / 4096

while True:
    raw = read_angle_raw()
    deg = read_angle_deg()
    print(f"Raw: {raw:4d}  |  Angle: {deg:6.2f}°")
    time.sleep_ms(50)