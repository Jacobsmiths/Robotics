from machine import Pin, SPI, I2C
import time
from OV2640_reg import *

# Constants
OV2640=0
OV5642=1
MAX_FIFO_SIZE=0x7FFFFF
ARDUCHIP_FRAMES=0x01
ARDUCHIP_TIM=0x03
VSYNC_LEVEL_MASK=0x02
ARDUCHIP_TRIG=0x41
CAP_DONE_MASK=0x08
OV5642_CHIPID_HIGH=0x300a
OV5642_CHIPID_LOW=0x300b

# Resolution and Quality Enums (Truncated for brevity, keep your original lists)
OV2640_320x240 = 2
JPEG = 1
# ... [Include all other constants from your original file here] ...

class ArducamClass(object):
    def __init__(self, Type):
        self.CameraMode = JPEG
        self.CameraType = Type
        self.I2cAddress = 0x30
        
        # SPI Setup (Pico Pins: SCK=GP2, MOSI=GP3, MISO=GP4)
        self.spi = SPI(0, baudrate=4000000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
        self.SPI_CS = Pin(5, Pin.OUT, value=1)
        
        # I2C Setup (Pico Pins: SCL=GP9, SDA=GP8)
        self.i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=1000000)
        
        print("I2C Scan:", self.i2c.scan())
        
        self.Spi_write(0x07, 0x80)
        time.sleep(0.1)
        self.Spi_write(0x07, 0x00)
        time.sleep(0.1)

    def Camera_Detection(self):
        while True:
            if self.CameraType == OV2640:
                self.I2cAddress = 0x30
                self.wrSensorReg8_8(0xff, 0x01)
                id_h = self.rdSensorReg8_8(0x0a)
                id_l = self.rdSensorReg8_8(0x0b)
                if id_h == 0x26 and (id_l == 0x40 or id_l == 0x42):
                    print('CameraType is OV2640')
                    break
            elif self.CameraType == OV5642:
                self.I2cAddress = 0x3c
                self.wrSensorReg16_8(0xff, 0x01)
                id_h = self.rdSensorReg16_8(OV5642_CHIPID_HIGH)
                id_l = self.rdSensorReg16_8(OV5642_CHIPID_LOW)
                if id_h == 0x56 and id_l == 0x42:
                    print('CameraType is OV5642')
                    break
            print('Camera not found, retrying...')
            time.sleep(1)

    def wrSensorReg16_8(self, addr, val):
        buf = bytearray([(addr >> 8) & 0xff, addr & 0xff, val])
        self.i2c.writeto(self.I2cAddress, buf)
        time.sleep_ms(3)

    def rdSensorReg16_8(self, addr):
        buf = bytearray([(addr >> 8) & 0xff, addr & 0xff])
        self.i2c.writeto(self.I2cAddress, buf)
        return self.i2c.readfrom(self.I2cAddress, 1)[0]

    def wrSensorReg8_8(self, addr, val):
        self.i2c.writeto(self.I2cAddress, bytearray([addr, val]))

    def rdSensorReg8_8(self, addr):
        self.i2c.writeto(self.I2cAddress, bytearray([addr]))
        return self.i2c.readfrom(self.I2cAddress, 1)[0]

    def Spi_write(self, address, value):
        self.SPI_CS.value(0)
        self.spi.write(bytearray([address | 0x80, value]))
        self.SPI_CS.value(1)

    def Spi_read(self, address):
        self.SPI_CS.value(0)
        self.spi.write(bytearray([address & 0x7f]))
        data = self.spi.read(1)
        self.SPI_CS.value(1)
        return data

    def SPI_CS_LOW(self): self.SPI_CS.value(0)
    def SPI_CS_HIGH(self): self.SPI_CS.value(1)

    def set_fifo_burst(self):
        self.spi.write(bytearray([0x3c]))

    def read_fifo_length(self):
        len1 = self.Spi_read(0x42)[0]
        len2 = self.Spi_read(0x43)[0]
        len3 = self.Spi_read(0x44)[0] & 0x7f
        return (len3 << 16) | (len2 << 8) | len1

    def flush_fifo(self): self.Spi_write(0x04, 0x01)
    def clear_fifo_flag(self): self.Spi_write(0x04, 0x01)
    def start_capture(self): self.Spi_write(0x04, 0x02)
    def get_bit(self, addr, bit): return self.Spi_read(addr)[0] & bit

    def wrSensorRegs8_8(self, reg_list):
        for addr, val in reg_list:
            if addr == 0xff and val == 0xff: return
            self.wrSensorReg8_8(addr, val)
            time.sleep_ms(1)
            
    # Include your existing OV2640_set_JPEG_size and other helper methods here, 
    # ensuring they use the self.wrSensorRegs methods defined above.