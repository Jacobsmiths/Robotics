import machine
import utime
from OV2640_Constants import *

# Constants
MAX_FIFO_SIZE = 0x7FFFFF
ARDUCHIP_FRAMES = 0x01
ARDUCHIP_TIM = 0x03
VSYNC_LEVEL_MASK = 0x02
ARDUCHIP_TRIG = 0x41
CAP_DONE_MASK = 0x08

# Effect and Setting Constants
Auto, Sunny, Cloudy, Office, Home = 0, 1, 2, 3, 4
Antique, Bluish, Greenish, Reddish, BW, Negative, BWnegative, Normal = 0, 1, 2, 3, 4, 5, 6, 7
Saturation2, Saturation1, Saturation0, Saturation_1, Saturation_2 = 2, 3, 4, 5, 6
Brightness2, Brightness1, Brightness0, Brightness_1, Brightness_2 = 2, 3, 4, 5, 6
Contrast2, Contrast1, Contrast0, Contrast_1, Contrast_2 = 2, 3, 4, 5, 6

class ArducamClass:
    def __init__(self):
        self.I2cAddress = 0x30
        
        # SPI Setup (Adjust pins for your specific MicroPython board)
        # Assuming Raspberry Pi Pico pins based on original GP numbers
        self.cs = machine.Pin(5, machine.Pin.OUT)
        self.cs.value(1)

        self.spi = machine.SPI(0, baudrate=4000000, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
        self.i2c = machine.I2C(scl=machine.Pin(9), sda=machine.Pin(8), freq=50000)
        
        utime.sleep_ms(100)
        print("I2C Scan:", self.i2c.scan())
        
    def Camera_Init(self):
        # most of this is the I2C settings except last part is SPI clear buffer
        print("Resetting Sensor...")
        # this sets it to bank 1 which allows the total reset of image settings
        self.wrSensorReg8_8(0xff, 0x01)
        utime.sleep_ms(100)
        # this resets the actual OV2640 chip
        self.wrSensorReg8_8(0x12, 0x80) 
        utime.sleep_ms(100)
        
        print("Setting Resolution to 160x120...")
        # This sets the frame size/windowing
        self.wrSensorRegs8_8(OV2640_160x120_JPEG) 
        utime.sleep_ms(500)

        print("Setting Output Format to YUV422...")
        # This switches the DSP from JPEG compression to raw YUV bytes
        self.wrSensorRegs8_8(OV2640_YUV422)
        utime.sleep_ms(500)
        # This officially forces YUV mode and not to use JPEG compression
        self.wrSensorReg8_8(0xff, 0x00) # Switch to Bank 0 for setting image settings
        utime.sleep_ms(100)
        self.wrSensorReg8_8(0xDA, 0x00) # 0x00 = YUV, setting actual YUV value 
        utime.sleep_ms(100)
        
        self.clear_buffer()
        print("Camera Ready for YUV Capture.")

    def spi_test(self):
        # this tests the SPI test register by sending it a value and then reading it
        test_val = 0x55
        print(f"Testing SPI")
    
        self.spi_write(0x00, test_val)
        utime.sleep_ms(100)
        read_val = self.spi_read(0x00)
        
        if read_val and read_val[0] == test_val:
            print(f"SPI: Success")
        else:
            actual_byte = read_val[0] if read_val else "None"
            print(f"FAILED: Wrote {hex(test_val)}, but read back {hex(actual_byte)}")
    
    def capture_to_buffer(self, buffer):
        self.SPI_CS.value(0)
        self.spi.write(bytearray([0x3C]))
        self.spi.read(1)
        self.spi.readinto(buffer)
        self.SPI_CS.value(1)
        return True
    
    # SPI Communication Methods
    def start_capture(self):
        # This starts the captuer with bit 1
        self.spi_write(0x04, 0x02)
        
    def clear_buffer(self):
        # Reset fifo buffer (this is bit 0 + bit 4 + bit 5) for clear fifo write done flag, reset write pointer, reset fifo read pointer resp.
        # added another spi_write of bit 0 becuase other codes do it twice?
        self.spi_write(0x04, 0x31)  # Clear capture done flag
    
    def read_fifo_length(self):
        """Reads fifo length"""
        len1 = self.spi_read(0x42)[0]
        len2 = self.spi_read(0x43)[0]
        len3 = self.spi_read(0x44)[0] & 0x7f
        return ((len3 << 16) | (len2 << 8) | len1) & 0x7FFFFF
    
    def get_bit(self, addr, mask):
        """Reads one bit via SPI of the ardubridge chip"""
        res = self.spi_read(addr)
        if res:
            return res[0] & mask
        return 0
    
    def spi_write(self, address, value):
        # pulls the value low to wake up spi
        self.SPI_CS.value(0)
        self.spi.write(bytearray([address | 0x80, value]))
        self.SPI_CS.value(1)

    def spi_read(self, address):
        self.SPI_CS.value(0)
        self.spi.write(bytearray([address & 0x7f]))
        data = self.spi.read(1)
        self.SPI_CS.value(1)
        return data
        
    # I2C Communication Methods
    def wrSensorReg8_8(self, addr, val):
        """writes one register of the OV2640"""
        self.i2c.writeto(self.I2cAddress, bytearray([addr, val]))
                                          
    def wrSensorRegs8_8(self, reg_value):
        """Writes multiple registers of the OV2640"""
        for addr, val in reg_value:
            if addr == 0xff and val == 0xff:
                return
            self.wrSensorReg8_8(addr, val)
            utime.sleep_ms(1)

    def rdSensorReg8_8(self, addr):
        """Reads one register of the OV2640"""
        self.i2c.writeto(self.I2cAddress, bytearray([addr]))
        return self.i2c.readfrom(self.I2cAddress, 1)[0]

    def OV2640_set_Light_Mode(self, result):
        if result == Auto:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0xc7, 0x00)
        elif result == Sunny:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0xc7, 0x40)
            self.wrSensorReg8_8(0xcc, 0x5e)
            self.wrSensorReg8_8(0xcd, 0x41)
            self.wrSensorReg8_8(0xce, 0x54)
        elif result == Cloudy:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0xc7, 0x40)
            self.wrSensorReg8_8(0xcc, 0x65)
            self.wrSensorReg8_8(0xcd, 0x41)
            self.wrSensorReg8_8(0xce, 0x4f)
        elif result == Office:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0xc7, 0x40)
            self.wrSensorReg8_8(0xcc, 0x52)
            self.wrSensorReg8_8(0xcd, 0x41)
            self.wrSensorReg8_8(0xce, 0x66)
        elif result == Home:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0xc7, 0x40)
            self.wrSensorReg8_8(0xcc, 0x42)
            self.wrSensorReg8_8(0xcd, 0x3f)
            self.wrSensorReg8_8(0xce, 0x71)
        else:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0xc7, 0x00)

    def OV2640_set_Color_Saturation(self, Saturation):
        if Saturation == Saturation2:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x02)
            self.wrSensorReg8_8(0x7c, 0x03)
            self.wrSensorReg8_8(0x7d, 0x68)
            self.wrSensorReg8_8(0x7d, 0x68)
        elif Saturation == Saturation1:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x02)
            self.wrSensorReg8_8(0x7c, 0x03)
            self.wrSensorReg8_8(0x7d, 0x58)
            self.wrSensorReg8_8(0x7d, 0x58)
        elif Saturation == Saturation0:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x02)
            self.wrSensorReg8_8(0x7c, 0x03)
            self.wrSensorReg8_8(0x7d, 0x48)
            self.wrSensorReg8_8(0x7d, 0x48)
        elif Saturation == Saturation_1:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x02)
            self.wrSensorReg8_8(0x7c, 0x03)
            self.wrSensorReg8_8(0x7d, 0x38)
            self.wrSensorReg8_8(0x7d, 0x38)
        elif Saturation == Saturation_2:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x02)
            self.wrSensorReg8_8(0x7c, 0x03)
            self.wrSensorReg8_8(0x7d, 0x28)
            self.wrSensorReg8_8(0x7d, 0x28)

    def OV2640_set_Brightness(self, Brightness):
        if Brightness == Brightness2:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x04)
            self.wrSensorReg8_8(0x7c, 0x09)
            self.wrSensorReg8_8(0x7d, 0x40)
            self.wrSensorReg8_8(0x7d, 0x00)
        elif Brightness == Brightness1:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x04)
            self.wrSensorReg8_8(0x7c, 0x09)
            self.wrSensorReg8_8(0x7d, 0x30)
            self.wrSensorReg8_8(0x7d, 0x00)
        elif Brightness == Brightness0:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x04)
            self.wrSensorReg8_8(0x7c, 0x09)
            self.wrSensorReg8_8(0x7d, 0x20)
            self.wrSensorReg8_8(0x7d, 0x00)
        elif Brightness == Brightness_1:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x04)
            self.wrSensorReg8_8(0x7c, 0x09)
            self.wrSensorReg8_8(0x7d, 0x10)
            self.wrSensorReg8_8(0x7d, 0x00)
        elif Brightness == Brightness_2:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x04)
            self.wrSensorReg8_8(0x7c, 0x09)
            self.wrSensorReg8_8(0x7d, 0x00)
            self.wrSensorReg8_8(0x7d, 0x00)

    def OV2640_set_Contrast(self, Contrast):
        if Contrast == Contrast2:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x04)
            self.wrSensorReg8_8(0x7c, 0x07)
            self.wrSensorReg8_8(0x7d, 0x20)
            self.wrSensorReg8_8(0x7d, 0x28)
            self.wrSensorReg8_8(0x7d, 0x0c)
            self.wrSensorReg8_8(0x7d, 0x06)
        elif Contrast == Contrast1:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x04)
            self.wrSensorReg8_8(0x7c, 0x07)
            self.wrSensorReg8_8(0x7d, 0x20)
            self.wrSensorReg8_8(0x7d, 0x24)
            self.wrSensorReg8_8(0x7d, 0x16)
            self.wrSensorReg8_8(0x7d, 0x06)
        elif Contrast == Contrast0:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x04)
            self.wrSensorReg8_8(0x7c, 0x07)
            self.wrSensorReg8_8(0x7d, 0x20)
            self.wrSensorReg8_8(0x7d, 0x20)
            self.wrSensorReg8_8(0x7d, 0x20)
            self.wrSensorReg8_8(0x7d, 0x06)
        elif Contrast == Contrast_1:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x04)
            self.wrSensorReg8_8(0x7c, 0x07)
            self.wrSensorReg8_8(0x7d, 0x20)
            self.wrSensorReg8_8(0x7d, 0x20)
            self.wrSensorReg8_8(0x7d, 0x2a)
            self.wrSensorReg8_8(0x7d, 0x06)
        elif Contrast == Contrast_2:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x04)
            self.wrSensorReg8_8(0x7c, 0x07)
            self.wrSensorReg8_8(0x7d, 0x20)
            self.wrSensorReg8_8(0x7d, 0x18)
            self.wrSensorReg8_8(0x7d, 0x34)
            self.wrSensorReg8_8(0x7d, 0x06)

    def OV2640_set_Special_effects(self, Special_effect):
        if Special_effect == Antique:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x18)
            self.wrSensorReg8_8(0x7c, 0x05)
            self.wrSensorReg8_8(0x7d, 0x40)
            self.wrSensorReg8_8(0x7d, 0xa6)
        elif Special_effect == Bluish:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x18)
            self.wrSensorReg8_8(0x7c, 0x05)
            self.wrSensorReg8_8(0x7d, 0xa0)
            self.wrSensorReg8_8(0x7d, 0x40)
        elif Special_effect == Greenish:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x18)
            self.wrSensorReg8_8(0x7c, 0x05)
            self.wrSensorReg8_8(0x7d, 0x40)
            self.wrSensorReg8_8(0x7d, 0x40)
        elif Special_effect == Reddish:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x18)
            self.wrSensorReg8_8(0x7c, 0x05)
            self.wrSensorReg8_8(0x7d, 0x40)
            self.wrSensorReg8_8(0x7d, 0xc0)
        elif Special_effect == BW:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x18)
            self.wrSensorReg8_8(0x7c, 0x05)
            self.wrSensorReg8_8(0x7d, 0x80)
            self.wrSensorReg8_8(0x7d, 0x80)
        elif Special_effect == Negative:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x40)
            self.wrSensorReg8_8(0x7c, 0x05)
            self.wrSensorReg8_8(0x7d, 0x80)
            self.wrSensorReg8_8(0x7d, 0x80)
        elif Special_effect == BWnegative:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x58)
            self.wrSensorReg8_8(0x7c, 0x05)
            self.wrSensorReg8_8(0x7d, 0x80)
            self.wrSensorReg8_8(0x7d, 0x80)
        elif Special_effect == Normal:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x7c, 0x00)
            self.wrSensorReg8_8(0x7d, 0x00)
            self.wrSensorReg8_8(0x7c, 0x05)
            self.wrSensorReg8_8(0x7d, 0x80)
            self.wrSensorReg8_8(0x7d, 0x80)