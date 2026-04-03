from machine import Pin, SPI, I2C
import time
# These must be separate .py files on your Pico containing the register arrays
from OV2640_reg import *

# Constants
OV2640 = 0
OV5642 = 1
JPEG = 1
RAW = 2
BMP = 0

ARDUCHIP_TIM = 0x03
VSYNC_LEVEL_MASK = 0x02
ARDUCHIP_TRIG = 0x41
CAP_DONE_MASK = 0x08

class ArducamClass(object):
    def __init__(self, Type):
        self.CameraMode = JPEG
        self.CameraType = Type
        self.I2cAddress = 0x30
        
        # Hardware Setup for Pi Pico
        # SPI 0: SCK=GP2, MOSI=GP3, MISO=GP4. CS=GP5
        self.spi = SPI(0, baudrate=4000000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
        self.SPI_CS = Pin(5, Pin.OUT, value=1)
        
        # I2C 0: SCL=GP9, SDA=GP8
        self.i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=400000)
        
        # Reset the ArduChip via SPI
        self.Spi_write(0x07, 0x80)
        time.sleep(0.1)
        self.Spi_write(0x07, 0x00)
        time.sleep(0.1)

    def Camera_Init(self):
        """The actual initialization sequence for the sensors"""
        if self.CameraType == OV2640:
            self.wrSensorReg8_8(0xff, 0x01)
            self.wrSensorReg8_8(0x12, 0x80) # Reset
            time.sleep(0.1)
            
            # These constants come from OV2640_reg.py
            self.wrSensorRegs8_8(OV2640_JPEG_INIT)
            self.wrSensorRegs8_8(OV2640_YUV422)
            self.wrSensorRegs8_8(OV2640_JPEG)
            
            self.wrSensorReg8_8(0xff, 0x01)
            self.wrSensorReg8_8(0x15, 0x00)
            self.wrSensorRegs8_8(OV2640_320x240_JPEG)
            print("OV2640 Init OK")
            
        elif self.CameraType == OV5642:
            self.wrSensorReg16_8(0x3008, 0x80) # Software Reset
            time.sleep(0.1)
            if self.CameraMode == RAW:
                self.wrSensorRegs16_8(OV5642_1280x960_RAW)
                self.wrSensorRegs16_8(OV5642_640x480_RAW)
            else:
                self.wrSensorRegs16_8(OV5642_QVGA_Preview1)
                self.wrSensorRegs16_8(OV5642_QVGA_Preview2)
                time.sleep(0.1)
                if self.CameraMode == JPEG:
                    self.wrSensorRegs16_8(OV5642_JPEG_Capture_QSXGA)
                    self.wrSensorRegs16_8(ov5642_320x240)
            print("OV5642 Init OK")

    # --- Helper Methods to process register lists ---
    def wrSensorRegs8_8(self, reg_list):
        for addr, val in reg_list:
            if addr == 0xff and val == 0xff: break
            self.wrSensorReg8_8(addr, val)
            time.sleep_ms(1)

    def wrSensorRegs16_8(self, reg_list):
        for addr, val in reg_list:
            if addr == 0xffff and val == 0xff: break
            self.wrSensorReg16_8(addr, val)
            time.sleep_ms(1)

    # --- Low Level I2C/SPI ---
    def wrSensorReg8_8(self, addr, val):
        self.i2c.writeto(self.I2cAddress, bytearray([addr, val]))

    def rdSensorReg8_8(self, addr):
        self.i2c.writeto(self.I2cAddress, bytearray([addr]))
        return self.i2c.readfrom(self.I2cAddress, 1)[0]

    def wrSensorReg16_8(self, addr, val):
        buf = bytearray([(addr >> 8) & 0xff, addr & 0xff, val])
        self.i2c.writeto(self.I2cAddress, buf)

    def rdSensorReg16_8(self, addr):
        buf = bytearray([(addr >> 8) & 0xff, addr & 0xff])
        self.i2c.writeto(self.I2cAddress, buf)
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
    def set_fifo_burst(self): self.spi.write(bytearray([0x3c]))
    def flush_fifo(self): self.Spi_write(0x04, 0x01)
    def clear_fifo_flag(self): self.Spi_write(0x04, 0x01)
    def start_capture(self): self.Spi_write(0x04, 0x02)
    def get_bit(self, addr, bit): return self.Spi_read(addr)[0] & bit

    def read_fifo_length(self):
        len1 = self.Spi_read(0x42)[0]
        len2 = self.Spi_read(0x43)[0]
        len3 = self.Spi_read(0x44)[0] & 0x7f
        return (len3 << 16) | (len2 << 8) | len1
        
    def Spi_Test(self):
        self.Spi_write(0x00, 0x55)
        if self.Spi_read(0x00)[0] == 0x55:
            print("SPI Bus OK")
        else:
            print("SPI Bus Error")

    def set_format(self, mode):
        self.CameraMode = mode

    def set_bit(self, addr, bit):
        temp = self.Spi_read(addr)[0]
        self.Spi_write(addr, temp | bit)
            
    def OV2640_set_JPEG_size(self, size):
        # Maps the 'value' from your pico_imager loop to specific registers
        sizes = {
            0: OV2640_160x120_JPEG, 1: OV2640_176x144_JPEG,
            2: OV2640_320x240_JPEG, 3: OV2640_352x288_JPEG,
            4: OV2640_640x480_JPEG, 5: OV2640_800x600_JPEG,
            6: OV2640_1024x768_JPEG, 7: OV2640_1280x1024_JPEG,
            8: OV2640_1600x1200_JPEG
        }
        if size in sizes:
            self.wrSensorRegs8_8(sizes[size])