import time
import sys
import select
from machine import SPI, Pin
from Arducam import *

once_number = 128
mode = 0
start_capture = 0
stop_flag = 0
buffer = bytearray(once_number)

mycam = ArducamClass(OV2640)
mycam.Camera_Init()
time.sleep(1)
mycam.clear_fifo_flag()

def read_fifo_burst():
    length = mycam.read_fifo_length()
    mycam.SPI_CS_LOW()
    mycam.set_fifo_burst()
    
    count = 0
    while count < length:
        rem = length - count
        chunk = once_number if rem > once_number else rem
        
        # Read from SPI directly into buffer
        mycam.spi.readinto(buffer, 0x00) # MicroPython readinto
        # Write binary data to Serial
        sys.stdout.buffer.write(buffer[:chunk])
        
        count += chunk
        time.sleep_us(150)
        
    mycam.SPI_CS_HIGH()
    mycam.clear_fifo_flag()

while True:
    # Check if data is available on Serial (stdin)
    if select.select([sys.stdin], [], [], 0)[0]:
        cmd = sys.stdin.buffer.read(1)
        value = cmd[0]
        
        # Command Logic
        if value <= 8: # JPEG Sizes
            mycam.OV2640_set_JPEG_size(value)
        elif value == 0x10:
            mode = 1
            start_capture = 1
        elif value == 0x11:
            mycam.set_format(JPEG)
            mycam.Camera_Init()
            # Note: set_bit logic here
        elif value == 0x20:
            mode = 2
            start_capture = 2
            stop_flag = 0
        elif value == 0x21:
            stop_flag = 1
        # ... [Add the rest of your elif branches for brightness/contrast] ...

    # State Machine Logic
    if mode == 1:
        if start_capture == 1:
            mycam.flush_fifo()
            mycam.clear_fifo_flag()
            mycam.start_capture()
            start_capture = 0
        if mycam.get_bit(ARDUCHIP_TRIG, CAP_DONE_MASK):
            read_fifo_burst()
            mode = 0
            
    elif mode == 2:
        if stop_flag == 0:
            if start_capture == 2:
                mycam.flush_fifo()
                mycam.clear_fifo_flag()
                mycam.start_capture()
                start_capture = 0
            if mycam.get_bit(ARDUCHIP_TRIG, CAP_DONE_MASK):
                read_fifo_burst()
                start_capture = 2
        else:
            mode = 0