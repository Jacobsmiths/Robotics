import machine
import utime
import sys
###### THIS IS THE ARDUCAM.PY FILE ########
import gc
from OV2640_Constants import *

# Constants
OV2640 = 0
MAX_FIFO_SIZE = 0x7FFFFF
ARDUCHIP_FRAMES = 0x01
ARDUCHIP_TIM = 0x03
VSYNC_LEVEL_MASK = 0x02
ARDUCHIP_TRIG = 0x41
CAP_DONE_MASK = 0x08

# Resolution Constants
OV2640_160x120 = 0
OV2640_176x144 = 1
OV2640_320x240 = 2
OV2640_352x288 = 3
OV2640_640x480 = 4
OV2640_800x600 = 5
OV2640_1024x768 = 6
OV2640_1280x1024 = 7
OV2640_1600x1200 = 8

# Effect and Setting Constants
Auto, Sunny, Cloudy, Office, Home = 0, 1, 2, 3, 4
Antique, Bluish, Greenish, Reddish, BW, Negative, BWnegative, Normal = 0, 1, 2, 3, 4, 5, 6, 7
BMP, JPEG, RAW, YUV = 0, 1, 2, 3
Saturation2, Saturation1, Saturation0, Saturation_1, Saturation_2 = 2, 3, 4, 5, 6
Brightness2, Brightness1, Brightness0, Brightness_1, Brightness_2 = 2, 3, 4, 5, 6
Contrast2, Contrast1, Contrast0, Contrast_1, Contrast_2 = 2, 3, 4, 5, 6
Compression_Off, Compression_1, Compression_2, Compression_3, Compression_4, Compression_Full = 0, 1, 2, 3, 4, 5

class ArducamClass:
    def __init__(self, mode=YUV):
        self.CameraMode = mode
        self.I2cAddress = 0x30
        
        # SPI Setup (Adjust pins for your specific MicroPython board)
        # Assuming Raspberry Pi Pico pins based on original GP numbers
        self.SPI_CS = machine.Pin(5, machine.Pin.OUT)
        self.SPI_CS.value(1)
        
        # Software SPI or Hardware SPI (using bus 0)
        self.spi = machine.SPI(0, baudrate=4000000, polarity=0, phase=0, 
                               sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
        
        # I2C Setup (Software I2C to match bitbangio behavior)
        self.i2c = machine.SoftI2C(scl=machine.Pin(9), sda=machine.Pin(8), freq=100000)
        
        print("I2C Scan:", self.i2c.scan())
        
        self.Spi_write(0x07, 0x80)
        utime.sleep(0.1)
        self.Spi_write(0x07, 0x00)
        utime.sleep(0.1)

    def Camera_Detection(self):
        while True:
            self.I2cAddress = 0x30
            self.wrSensorReg8_8(0xff, 0x01) # Select Bank 1
            utime.sleep_ms(10)
            
            id_h = self.rdSensorReg8_8(0x0a)
            id_l = self.rdSensorReg8_8(0x0b)
        
            if id_h == 0x26 and (id_l == 0x40 or id_l == 0x41 or id_l == 0x42):
                print('CameraType is OV2640')
                break
            else:
                print(f"Detected wrong ID: {hex(id_h)}{hex(id_l)}. Retrying...")
            utime.sleep(1)
            
    def Set_Camera_mode(self, mode):
        self.CameraMode = mode

    # I2C Communication Methods
    def wrSensorReg16_8(self, addr, val):
        buf = bytearray([(addr >> 8) & 0xff, addr & 0xff, val])
        self.i2c.writeto(self.I2cAddress, buf)

    def rdSensorReg16_8(self, addr):
        buf = bytearray([(addr >> 8) & 0xff, addr & 0xff])
        self.i2c.writeto(self.I2cAddress, buf)
        return self.i2c.readfrom(self.I2cAddress, 1)[0]

    def wrSensorReg8_8(self, addr, val):
        self.i2c.writeto(self.I2cAddress, bytearray([addr, val]))

    def rdSensorReg8_8(self, addr):
        self.i2c.writeto(self.I2cAddress, bytearray([addr]))
        return self.i2c.readfrom(self.I2cAddress, 1)[0]

    # SPI Communication Methods
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

    def Spi_Test(self):
        while True:
            self.Spi_write(0x00, 0x56)
            value = self.Spi_read(0x00)
            if value and value[0] == 0x56:
                print('SPI interface OK')
                break
            else:
                print('SPI interface Error')
            utime.sleep(1)

    def Camera_Init(self):
        print("Resetting Sensor...")
        self.wrSensorReg8_8(0xff, 0x01)
        self.wrSensorReg8_8(0x12, 0x80) 
        utime.sleep_ms(500)

        print("Loading 96x96 Configuration...")
        self.wrSensorRegs8_8(OV2640_YUV_96x96)
        utime.sleep_ms(100)

        # --- ARDUCHIP CONFIGURATION (The "Secret Sauce") ---
        # Register 0x07 controls the FIFO. 
        # We need to ensure Bit 0 is 0 (Normal FIFO mode, not JPEG mode)
        self.Spi_write(0x07, 0x00) 
        
        # Register 0x01: Ensure Arducam isn't in 'one-shot' mode prematurely
        # and isn't looking for JPEG magic numbers.
        self.Spi_write(0x01, 0x00) 
        
        print("FIFO configured for RAW/YUV stream.")
        
    def flush_fifo(self):
            self.Spi_write(0x04, 0x01)
    
    def clear_fifo_flag(self):
        self.Spi_write(0x04, 0x01)

    def read_fifo_length(self):
        len1 = self.Spi_read(0x42)[0]
        len2 = self.Spi_read(0x43)[0]
        len3 = self.Spi_read(0x44)[0] & 0x7f
        return ((len3 << 16) | (len2 << 8) | len1) & 0x7FFFFF
    
    def get_bit(self, addr, mask):
        # We need to ensure we are reading from the SPI register correctly
        res = self.Spi_read(addr)
        if res:
            return res[0] & mask
        return 0

    def start_capture(self):
        # 0x04 is the ARDUCHIP_FIFO register
        # 0x02 starts the capture
        self.Spi_write(0x04, 0x00) # Reset FIFO control
        self.Spi_write(0x04, 0x02) # Start Capture
        
    def wrSensorRegs8_8(self, reg_value):
        for addr, val in reg_value:
            if addr == 0xff and val == 0xff:
                return
            self.wrSensorReg8_8(addr, val)
            utime.sleep_ms(1)

    def OV2640_set_JPEG_size(self, size):
        if self.CameraMode == YUV:
            print("Mode is YUV. [set_JPEG_size] not possible. Please init Camera with mode=JPEG")
            return

        if size == OV2640_160x120:
            self.wrSensorRegs8_8(OV2640_160x120_JPEG)
        elif size == OV2640_176x144:
            self.wrSensorRegs8_8(OV2640_176x144_JPEG)
        elif size == OV2640_320x240:
            self.wrSensorRegs8_8(OV2640_320x240_JPEG)
        elif size == OV2640_352x288:
            self.wrSensorRegs8_8(OV2640_352x288_JPEG)
        elif size == OV2640_640x480:
            self.wrSensorRegs8_8(OV2640_640x480_JPEG)
        elif size == OV2640_800x600:
            self.wrSensorRegs8_8(OV2640_800x600_JPEG)
        elif size == OV2640_1024x768:
            self.wrSensorRegs8_8(OV2640_1024x768_JPEG)
        elif size == OV2640_1280x1024:
            self.wrSensorRegs8_8(OV2640_1280x1024_JPEG)
        elif size == OV2640_1600x1200:
            self.wrSensorRegs8_8(OV2640_1600x1200_JPEG)
            print("Max")
        else:
            self.wrSensorRegs8_8(OV2640_320x240_JPEG)

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

    def OV2640_set_JPEG_Compression(self, compression):
        '''
            compression int 0 - 5
        '''
        if self.CameraMode == YUV:
            print("Mode is YUV. [set_JPEG_size] not possible. Please init Camera with mode=JPEG")
            return

        if compression == Compression_Off:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x44, 0x00)
        elif compression == Compression_1:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x44, 0x33)
        elif compression == Compression_2:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x44, 0x66)
        elif compression == Compression_3:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x44, 0x99)
        elif compression == Compression_4:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x44, 0xcc)
        elif compression == Compression_Full:
            self.wrSensorReg8_8(0xff, 0x00)
            self.wrSensorReg8_8(0x44, 0xff)


###### THIS IS THE IMAGER FILE ##########

mycam = ArducamClass(OV2640)
mycam.Camera_Detection()
mycam.Spi_Test()
mycam.Camera_Init()
utime.sleep(1)

def capture_and_analyze():
    # 1. Clean up memory before starting a heavy task
    gc.collect()
    
    # Trigger Capture
    mycam.Spi_write(0x04, 0x01)
    mycam.Spi_write(0x04, 0x01) 
    mycam.Spi_write(0x04, 0x02) 
    
    timeout = 2000 
    start_time = utime.ticks_ms()
    while not (mycam.Spi_read(0x41)[0] & 0x08):
        if utime.ticks_diff(utime.ticks_ms(), start_time) > timeout:
            print("Capture Timeout")
            return None
        utime.sleep_ms(1)

    length = mycam.read_fifo_length()
    
    # Check if we actually got a full 96x96 frame (18432 bytes)
    # If the length is less, the math below will crash with IndexError
    if length < 18432:
        print(f"Skipping frame: Short read ({length}/18432)")
        return None

    # 2. Read raw data
    raw_data = bytearray(length)
    mycam.SPI_CS.value(0)
    mycam.spi.write(bytearray([0x3C]))
    mycam.spi.read(1) # Skip dummy byte
    mycam.spi.readinto(raw_data)
    mycam.SPI_CS.value(1)

    # 3. Extract Mid-Section (48x48) safely
    crop_w, crop_h = 48, 48
    start_row, start_col = 24, 24
    
    # Resulting grayscale array (Y-channel only)
    mid_section = bytearray(crop_w * crop_h)
    
    try:
        for y in range(crop_h):
            # Pre-calculate row offset to save CPU cycles
            row_offset = (start_row + y) * 96 * 2
            for x in range(crop_w):
                # We want the Y byte. In YUV422 (YUYV), Y is at index 0 and 2.
                # In UYVY, Y is at index 1 and 3. 
                # Let's target index 1 to be safe for most ArduCam YUV configs.
                pixel_offset = (start_col + x) * 2
                raw_idx = row_offset + pixel_offset + 1
                
                mid_section[y * crop_w + x] = raw_data[raw_idx]
    except IndexError:
        print("Data corruption detected during cropping.")
        return None
    finally:
        # 4. Explicitly delete the huge buffer and collect garbage
        del raw_data
        gc.collect()

    return mid_section

# Main Loop
while True:
    pixels = capture_and_analyze()
    # 1. Send the raw binary data
    sys.stdout.buffer.write(pixels)

    # 2. Force the data out immediately
    # (Sometimes the Pico waits for a full "packet" before sending)
    sys.stdout.buffer.flush()
    
    if pixels:
        print(f"Mid-section processed. Size: {len(pixels)} bytes")
        # Now 'pixels' is a tiny 48x48 grayscale array!
    utime.sleep(5)