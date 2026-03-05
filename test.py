from machine import Pin

p1 = Pin(10,Pin.OUT)
while True:
    p1.value(1)
