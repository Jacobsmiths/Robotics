from hbridge import MotorDriver, DriveTrain
from machine import Pin, Timer, SPI
from ultrasonic import ultraSonicSensor
from time import sleep
from imager import *
import gc

# -------- driver states ------
TARGET_BALL = 0
NO_BALL = 1
DRIVE_FORWARD = 2
STOP = 3

driver_state = STOP

# --- Setup Motors ---
motor1 = MotorDriver(10, 11)
motor2 = MotorDriver(13, 12)
driver = DriveTrain(motor1, motor2, 14)

# -- ultra sonic senosr ---
ultra = ultraSonicSensor(,2226)


# ---- intake motor ---
motor_pwm = PWM(Pin(15, Pin.OUT))
motor_pwm.freq(1000)


# ---- itmer interrupts ---
def set_capture_flag(timer):
    global capture_due
    capture_due = True
    
def get_dist(t):
    global dist
    dist = thing.measure()
    if dist<10 and dist>-1:
        print("WAIIIIT")



captureTimer = Timer(mode=Timer.PERIODIC, period=1000, callback=set_capture_flag)
capture_due = False
nx = None

ultraTimer = Timer(freq=10, mode=Timer.PERIODIC, callback=get_dist)
dist = -1

# ----------- main loop -------------
while True:
    if capture_due:
#         print("taking impag")
        capture_due = False
        nx = capture()
        if nx:
            driver_state = TARGET_BALL
        else:
            driver_state = STOP
            
            
    # --- driver code with distance stopper ----
    if dist<10 and dist>-1:
        driver.stop()
        continue
    
    if driver_state == TARGET_BALL:
        driver.steer(nx, 8000)
    elif driver_state == NO_BALL:
        driver.turnCW(8000)
    elif driver_state == DRIVE_FORWARD:
        driver.drive(0,8000)
    elif driver_state == STOP:
        driver.stop()
        
        
    
    
    gc.collect()
