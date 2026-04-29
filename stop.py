from machine import Pin, PWM
from time import sleep

class MotorDriver:
    def __init__(self, in1, in2, en):
        self.input1 = Pin(in1, Pin.OUT)
        self.input2 = Pin(in2, Pin.OUT)
        self.enable = PWM(Pin(en, Pin.OUT))
        self.enable.freq(20000)  # 80 MHz is too high, use ~20kHz
        self.enable.duty_u16(65535)
    
    def cwDrive(self):
        self.input1.value(1)
        self.input2.value(0)
        self.enable.duty_u16(0)
    
    def ccwDrive(self):
        self.input1.value(0)
        self.input2.value(1)
        self.enable.duty_u16(0)
    
    def stop(self):
        self.input1.value(1)
        self.input2.value(1)
        self.enable.duty_u16(65535)
        
class Drive:
    def __init__(self, mtr1, mtr2):
        self.motor1 = mtr1
        self.motor2 = mtr2
    
    def driveForward(self):
        self.motor1.cwDrive()
        self.motor2.ccwDrive()
    
    def driveBackward(self):
        self.motor1.ccwDrive()
        self.motor2.cwDrive()
    
    def stop(self):
        self.motor1.stop()
        self.motor2.stop()
    
    def turnCW(self):
        self.motor1.ccwDrive()
        self.motor2.ccwDrive()
    
    def turnCCW(self):
        self.motor1.cwDrive()
        self.motor2.cwDrive()


# --- Setup Motors ---
motor1 = MotorDriver(2, 3, 0)
motor2 = MotorDriver(4, 5, 1)
driveTrain = Drive(motor1, motor2)
driveTrain.stop()

    
