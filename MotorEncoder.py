from machine import Pin
import time

ENCA = Pin(0, Pin.IN, Pin.PULL_UP) # Encoders are inputs of GPIO pins 0 and 1 for encoders a and b respectively
ENCB = Pin(1, Pin.IN, Pin.PULL_UP) # Pull up resistors just in case
    
count = 0 # set the count of ticks to start at 0
state = int((ENCA.value() << 1) | ENCB.value()) # gives the quaderature gray code decimal value
totalCount = 0
    
def trigger(pin):
    global count, state
    
    A = ENCA.value()
    B = ENCB.value()
    
    if state == 0:
        if A == 1 and B == 0:
            count += 1
            state = 2
        elif A == 0 and B == 1:
            count -= 1
            state = 1
    elif state == 1:
        if A == 1 and B == 1:
            count -= 1
            state = 3
        elif A == 0 and B == 0:
            count += 1
            state = 0
    elif state == 2:
        if A == 1 and B == 1:
            count += 1
            state = 3
        elif A == 0 and B == 0:
            count -= 1
            state = 0
    elif state == 3:
        if A == 1 and B == 0:
            count -= 1
            state = 2
        elif A == 0 and B == 1:
            count += 1
            state = 1

ENCA.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=trigger)
ENCB.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=trigger)

while True:
    time.sleep(1)
    print("ROTATIONS/SEC:", count/(4*823.1))
    print("CURRENT ANGLE (deg):", totalCount/(4*823.1) * 360)
    print("DIRECTION:","Clockwise" if count >=0 else "Counter-clockwise")
    totalCount += count
    count = 0
    
    
 