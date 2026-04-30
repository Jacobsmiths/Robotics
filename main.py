from hbridge import MotorDriver, DriveTrain
from machine import Pin, Timer, SPI
from time import sleep
from imager import *
import gc

# --- Setup Motors ---
motor1 = MotorDriver(21, 20, 17)
motor2 = MotorDriver(19, 18, 16)
driver = DriveTrain(motor1, motor2, 14, 15)

# --- Setup Stop Pins ---
# stop1 = Pin(14, Pin.IN, Pin.PULL_UP)
# stop2 = Pin(15, Pin.IN, Pin.PULL_UP)
# 
# # --- Debounce state ---
# overCurrentDebounce = False
# debounceTimer = Timer()

# --- Interrupt Callback ---
# def overCurrentCheck(pin):
#     global overCurrentDebounce
#     if overCurrentDebounce:
#         return
#     overCurrentDebounce = True
#     debounceTimer.init(mode=Timer.ONE_SHOT, period=50, callback=overCurrentStop)
#     
# def overCurrentStop(timer):
#     global overCurrentDebounce
#     overCurrentDebounce = False
#     if stop1.value() or stop2.value():
#         print("STOP confirmed")
#         driver.stop()
#         
# stop1.irq(trigger=Pin.IRQ_FALLING, handler=overCurrentCheck)
# stop2.irq(trigger=Pin.IRQ_FALLING, handler=overCurrentCheck)


# --- Ball capture flag ---
# capture_due = False
# 
# def set_capture_flag(timer):
#     global capture_due
#     capture_due = True
# 
# captureTimer = Timer()
# captureTimer.init(mode=Timer.PERIODIC, period=1000, callback=set_capture_flag)
# 
# driver.driveForward()
# while True:
#     if capture_due:
#         capture_due = False
#         result = capture()
#         if result:
#             cx, cy = result
#             steer_to_ball(cx)
#         else:
#             driver.driveForward()  # lost ball, go straight
#     gc.collect()
driver.steer(0)