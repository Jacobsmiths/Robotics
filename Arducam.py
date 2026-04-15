import machine
import utime
from OV2640_Constants import *
# 
# 
# ARDUCHIP_FIFO = 0x04  
# FIFO_CLEAR_MASK = 0x01
# FIFO_START_MASK = 0x02
# 
# BURST_FIFO_READ = 0x3C  
# SINGLE_FIFO_READ = 0x3D
# 
# ARDUCHIP_TRIG = 0x41
# VSYNC_MASK = 0x01
# CAP_DONE_MASK = 0x08
# 
# FIFO_SIZE1 = 0x42  #Camera write FIFO size[7:0] for burst to read
# FIFO_SIZE2 = 0x43  #Camera write FIFO size[15:8]
# FIFO_SIZE3 = 0x44  #Camera write FIFO size[18:16]

class ArducamClass:
    def __init__(self):
        self.I2cAddress = 0x30
        # SPI Setup (Adjust pins for your specific MicroPython board)
        # Assuming Raspberry Pi Pico pins based on original GP numbers
        self.cs = machine.Pin(5, machine.Pin.OUT)
        self.cs.value(1)
        self.spi = machine.SPI(0, baudrate=4000000,sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
        self.i2c = machine.I2C(scl=machine.Pin(9), sda=machine.Pin(8), freq=100000)
        utime.sleep_ms(100)
        print("I2C Scan:", self.i2c.scan())
        
    def Camera_Init(self):
        print("Resetting Sensor...")
        self.wrSensorReg8_8(0xff, 0x01) # switch to bank 1
        self.wrSensorReg8_8(0x12, 0x80) # resets chip
        utime.sleep_ms(500)
        
        # jpeg mode
#         self.wrSensorRegs8_8(OV2640_JPEG_INIT)
#         utime.sleep_ms(100)
#         self.wrSensorRegs8_8(OV2640_YUV422)
#         utime.sleep_ms(100)
#         self.wrSensorRegs8_8(OV2640_JPEG)
#         utime.sleep_ms(100)
#         self.wrSensorReg8_8(0xff, 0x01)
#         self.wrSensorReg8_8(0x15, 0x00)
#         self.wrSensorRegs8_8(OV2640_320x240_JPEG)
#         utime.sleep_ms(100)

        # yuv format
        self.wrSensorRegs8_8(OV2640_QVGA)
        utime.sleep_ms(100)
        self.wrSensorRegs8_8(OV2640_YUV422) # this forces YUV
        utime.sleep_ms(100)
        self.wrSensorReg8_8(0xff, 0x00) # Switch to Bank 0 for setting image settings
        utime.sleep_ms(100)
        self.wrSensorReg8_8(0x44,0x00) # turns off jpeg comprewsion
#         utime.sleep_ms(100)
        print("done resetting")
        
    def spi_test(self):
        # this tests the SPI test register by sending it a value and then reading it
        test_val = 0x55
        print(f"Testing SPI")
        self.spi_write(0x00, test_val)
        utime.sleep_ms(100)
        read_val = self.spi_read(0x00)[0]
        if read_val == test_val:
            print(f"SPI: Success")
        else:
            print(f"FAILED: Wrote {hex(test_val)}, but read back {read_val}")
    
    def capture_to_buffer(self, buffer):
        self.cs.value(0)
        self.spi.write(bytes([0x3C]))
        self.spi.readinto(buffer)
        self.cs.value(1)
        return True
    
    def clear_fifo(self):
        self.spi_write(0x04,0x01)
    
    # SPI Communication Methods
    def start_capture(self):
        self.spi_write(0x04, 0x02) # This starts the captuer with bit 1

#     def clear_buffer(self):
#         # Reset fifo buffer (this is bit 0 + bit 4 + bit 5) for clear fifo write done flag, reset write pointer, reset fifo read pointer resp.
#         self.spi_write(0x04, 0x31)

    def read_fifo_length(self):
        """Reads fifo length"""
        len1 = self.spi_read(0x42)[0]
        len2 = self.spi_read(0x43)[0]
        len3 = self.spi_read(0x44)[0] & 0x7f
        return ((len3 << 16) | (len2 << 8) | len1) & 0x7FFFFF
    
    def set_fifo_burst(self):
        self.cs.value(0)
        self.spi.write(bytes([0x3C]))
    
    def get_bit(self, addr, mask):
        """Reads one bit via SPI of the ardubridge chip"""
        res = self.spi_read(addr)
        return res[0] & mask
    
    def spi_write(self, address, value):
        # pulls the value low to wake up spi
        self.cs.value(0)
        self.spi.write(bytes([address | 0x80, value]))
        self.cs.value(1)

    def spi_read(self, address):
        self.cs.value(0)

        # Send address
        self.spi.write(bytes([address & 0x7F]))

        # Send dummy byte (0x00) and read response
        tx = bytearray([0x00])
        rx = bytearray(1)
        self.spi.write_readinto(tx, rx)

        self.cs.value(1)
        return rx
        
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
