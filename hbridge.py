from machine import Pin, PWM, Timer

MAX_SPEED = 1000
OFF = 65535

class MotorDriver:
    def __init__(self, in1, in2, en):
        self.input1 = Pin(in1, Pin.OUT)
        self.input2 = Pin(in2, Pin.OUT)
        self.enable = PWM(Pin(en, Pin.OUT))
        self.enable.freq(20000)
        self.enable.duty_u16(OFF)

    def _speed_to_duty(self, speed):
        speed = max(0, min(MAX_SPEED, speed))
        return int(OFF - (speed / MAX_SPEED) * OFF)

    def cwDrive(self, speed=MAX_SPEED):
        self.input1.value(1)
        self.input2.value(0)
        self.enable.duty_u16(self._speed_to_duty(speed))

    def ccwDrive(self, speed=MAX_SPEED):
        self.input1.value(0)
        self.input2.value(1)
        self.enable.duty_u16(self._speed_to_duty(speed))

    def stop(self):
        self.input1.value(1)
        self.input2.value(1)
        self.enable.duty_u16(OFF)


class DriveTrain:
    def __init__(self, mtr1, mtr2, oc_pin1, oc_pin2):
        self.motor1 = mtr1  # left motor
        self.motor2 = mtr2  # right motor

        # --- Overcurrent protection ---
        self._oc1 = Pin(oc_pin1, Pin.IN, Pin.PULL_UP)
        self._oc2 = Pin(oc_pin2, Pin.IN, Pin.PULL_UP)
        self._oc_debounce = False
        self._oc_timer = Timer()

        self._oc1.irq(trigger=Pin.IRQ_FALLING, handler=self._over_current_check)
        self._oc2.irq(trigger=Pin.IRQ_FALLING, handler=self._over_current_check)

    # --- Overcurrent interrupt & debounce ---

    def _over_current_check(self, pin):
        if self._oc_debounce:
            return
        self._oc_debounce = True
        self._oc_timer.init(
            mode=Timer.ONE_SHOT,
            period=50,
            callback=self._over_current_stop
        )

    def _over_current_stop(self, timer):
        self._oc_debounce = False
        if self._oc1.value() or self._oc2.value():
            print("STOP confirmed — overcurrent detected")
            self.stop()

    # --- Drive methods ---

    def driveForward(self, speed=MAX_SPEED):
        self.motor1.cwDrive(speed)
        self.motor2.ccwDrive(speed)

    def driveBackward(self, speed=MAX_SPEED):
        self.motor1.ccwDrive(speed)
        self.motor2.cwDrive(speed)

    def steer(self, vector, speed=MAX_SPEED):
        """
        vector: -1.0 = full left, 0 = straight, 1.0 = full right
        """
        vector = max(-1.0, min(1.0, vector))
        left_speed  = int(min(MAX_SPEED, speed * (1.0 + vector)))
        right_speed = int(min(MAX_SPEED, speed * (1.0 - vector)))
        self.motor1.cwDrive(left_speed)
        self.motor2.ccwDrive(right_speed)

    def turnCW(self, speed=MAX_SPEED):
        self.motor1.ccwDrive(speed)
        self.motor2.ccwDrive(speed)

    def turnCCW(self, speed=MAX_SPEED):
        self.motor1.cwDrive(speed)
        self.motor2.cwDrive(speed)

    def stop(self):
        self.motor1.stop()
        self.motor2.stop()