from machine import Pin
from machine import Timer
import time

class ultraSonicSensor:
    def __init__(self, trig, echo):
        self.trigger_pin = Pin(trig, Pin.OUT)
        self.echo_pin = Pin(echo, Pin.IN)
        self.trigger_pin.value(0)
    
    def pulse(self):
        # trigger the bat screetch
        self.trigger_pin.value(1)
        time.sleep_us(10)
        self.trigger_pin.value(0)
        
        # create a hardware timer and return time til response
        pulse_time = machine.time_pulse_us(self.echo_pin, 1, 11661) # third parameter is timeout, (2M /343) * 1e6 (conversion)
        return pulse_time
    
    def measure(self):
        '''returns the distance to detected object or -1 if nothing detected'''
        pulse_time = self.pulse()
        
        # run calculations to get distance in cm
        cm = pulse_time * 10 // 582
        return cm

thing = ultraSonicSensor(3,2)
dist = -1

def timer_handler(t):
    global dist
    dist = thing.measure()
    if dist<10 and dist>-1:
        print("WAIIIIT")

tim = Timer(-1,freq=10, mode=Timer.PERIODIC, callback=timer_handler)
