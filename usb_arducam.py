import time as utime
from machine import Pin, SPI, I2C
from OV2640_reg import *

# Camera type
OV2640 = 0

# Registers
ARDUCHIP_TIM = 0x03
VSYNC_LEVEL_MASK = 0x02
ARDUCHIP_TRIG = 0x41
CAP_DONE_MASK = 0x08

# JPEG sizes
OV2640_160x120   = 0
OV2640_176x144   = 1
OV2640_320x240   = 2
OV2640_352x288   = 3
OV2640_640x480   = 4
OV2640_800x600   = 5
OV2640_1024x768  = 6
OV2640_1280x1024 = 7
OV2640_1600x1200 = 8

# Light modes
Auto   = 0
Sunny  = 1
Cloudy = 2
Office = 3
Home   = 4

# Effects
Antique    = 0
Bluish     = 1
Greenish   = 2
Reddish    = 3
BW         = 4
Negative   = 5
BWnegative = 6
Normal     = 7

# Saturation
Saturation2  = 2
Saturation1  = 3
Saturation0  = 4
Saturation_1 = 5
Saturation_2 = 6

# Brightness
Brightness2  = 2
Brightness1  = 3
Brightness0  = 4
Brightness_1 = 5
Brightness_2 = 6

# Contrast
Contrast2  = 2
Contrast1  = 3
Contrast0  = 4
Contrast_1 = 5
Contrast_2 = 6

# Format
BMP  = 0
JPEG = 1
RAW  = 2


class ArducamClass:
    def __init__(self, Type):
        self.CameraMode = JPEG
        self.CameraType = Type

        # SPI CS pin
        self.SPI_CS = Pin(5, Pin.OUT)
        self.SPI_CS.value(1)

        # SPI
        self.spi = SPI(
            0,
            baudrate=4_000_000,
            polarity=0,
            phase=0,
            bits=8,
            sck=Pin(2),
            mosi=Pin(3),
            miso=Pin(4)
        )

        # I2C
        self.i2c = I2C(
            1,
            scl=Pin(9),
            sda=Pin(8),
            freq=1_000_000
        )

        self.I2cAddress = 0x30

        print(self.i2c.scan())

        self.Spi_write(0x07, 0x80)
        utime.sleep(0.1)
        self.Spi_write(0x07, 0x00)
        utime.sleep(0.1)

    # ------------------------
    # Camera detection
    # ------------------------
    def Camera_Detection(self):
        while True:
            self.wrSensorReg8_8(0xff, 0x01)
            id_h = self.rdSensorReg8_8(0x0a)
            id_l = self.rdSensorReg8_8(0x0b)

            if (id_h == 0x26) and (id_l in (0x40, 0x42)):
                print("CameraType is OV2640")
                break
            else:
                print("Can't find OV2640 module")

            utime.sleep(1)

    # ------------------------
    # I2C helpers
    # ------------------------
    def iic_write(self, buf):
        self.i2c.writeto(self.I2cAddress, buf)

    def iic_readinto(self, buf):
        self.i2c.readfrom_into(self.I2cAddress, buf)

    def wrSensorReg8_8(self, addr, val):
        self.iic_write(bytearray([addr, val]))

    def rdSensorReg8_8(self, addr):
        self.i2c.writeto(self.I2cAddress, bytearray([addr]), stop=False)
        data = self.i2c.readfrom(self.I2cAddress, 1)
        return data[0]

    # ------------------------
    # SPI helpers
    # ------------------------
    def SPI_CS_LOW(self):
        self.SPI_CS.value(0)

    def SPI_CS_HIGH(self):
        self.SPI_CS.value(1)

    def Spi_write(self, addr, val):
        self.SPI_CS_LOW()
        self.spi.write(bytearray([addr | 0x80, val]))
        self.SPI_CS_HIGH()

    def Spi_read(self, addr):
        self.SPI_CS_LOW()
        self.spi.write(bytearray([addr & 0x7F]))
        buf = bytearray(1)
        self.spi.readinto(buf)
        self.SPI_CS_HIGH()
        return buf

    # ------------------------
    # Core functions
    # ------------------------
    def get_bit(self, addr, bit):
        return self.Spi_read(addr)[0] & bit

    def set_bit(self, addr, bit):
        temp = self.Spi_read(addr)[0]
        self.Spi_write(addr, temp & (~bit))

    def flush_fifo(self):
        self.Spi_write(0x04, 0x01)

    def clear_fifo_flag(self):
        self.Spi_write(0x04, 0x01)

    def start_capture(self):
        self.Spi_write(0x04, 0x02)

    def set_fifo_burst(self):
        self.SPI_CS_LOW()
        self.spi.write(bytearray([0x3C]))

    def read_fifo_length(self):
        len1 = self.Spi_read(0x42)[0]
        len2 = self.Spi_read(0x43)[0]
        len3 = self.Spi_read(0x44)[0] & 0x7F
        return ((len3 << 16) | (len2 << 8) | len1) & 0x07FFFFF

    # ------------------------
    # Init
    # ------------------------
    def Camera_Init(self):
        self.wrSensorReg8_8(0xff, 0x01)
        self.wrSensorReg8_8(0x12, 0x80)
        utime.sleep(0.1)

        self.wrSensorRegs8_8(OV2640_JPEG_INIT)
        self.wrSensorRegs8_8(OV2640_YUV422)
        self.wrSensorRegs8_8(OV2640_JPEG)

        self.wrSensorReg8_8(0xff, 0x01)
        self.wrSensorReg8_8(0x15, 0x00)
        self.wrSensorRegs8_8(OV2640_320x240_JPEG)

    def wrSensorRegs8_8(self, reg_list):
        for reg in reg_list:
            addr, val = reg
            if addr == 0xFF and val == 0xFF:
                return
            self.wrSensorReg8_8(addr, val)
            utime.sleep(0.001)

    # ------------------------
    # Settings
    # ------------------------
    def set_format(self, mode):
        self.CameraMode = mode

    def OV2640_set_JPEG_size(self, size):
        tables = [
            OV2640_160x120_JPEG,
            OV2640_176x144_JPEG,
            OV2640_320x240_JPEG,
            OV2640_352x288_JPEG,
            OV2640_640x480_JPEG,
            OV2640_800x600_JPEG,
            OV2640_1024x768_JPEG,
            OV2640_1280x1024_JPEG,
            OV2640_1600x1200_JPEG
        ]
        self.wrSensorRegs8_8(tables[size] if size < len(tables) else OV2640_320x240_JPEG)