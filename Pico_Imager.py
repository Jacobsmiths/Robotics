import machine
import utime
import sys
from machine import Pin
import gc
from Arducam import ArducamClass
import math
import array

mycam = ArducamClass()
mycam.spi_test()
mycam.Camera_Init()
utime.sleep(1)

frame_buffer = bytearray(38400)

def capture_and_send():
    gc.collect()
    mycam.clear_buffer()
    utime.sleep_ms(10)
    mycam.start_capture()
    
    # poll the done flag
    start_wait = utime.ticks_ms()
    while not (mycam.get_bit(0x41, 0x08)):
        if utime.ticks_diff(utime.ticks_ms(), start_wait) > 1000:
            return False
        utime.sleep_ms(5)

    # reads the fifo buffer
    length = mycam.read_fifo_length()
    
    # Read SPI into buffer
    ret = mycam.capture_to_buffer(frame_buffer) # Dummy read required by Arducam hardware
    return length

# --- Main Loop


while True:
    length = capture_and_send()
    total_y = 0
    count = 0

    # Skip by 2 to grab every Y byte in the [Y, U, Y, V] pattern
    for i in range(0, len(frame_buffer), 2):
        y_pixel = frame_buffer[i]
        total_y += y_pixel
        count += 1

    avg_y = total_y / count
    print(f"Average Brightness: {avg_y}")
    print(f"fifo length: {length}")
    utime.sleep(2)
