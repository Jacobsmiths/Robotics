from machine import Pin, PWM, Timer

MAX_SPEED = 5000
OFF = 65535

class MotorDriver:
    def __init__(self, in1, in2):
        self.input1 = PWM(Pin(in1, Pin.OUT))
        self.input1.freq(20000)
        self.input1.duty_u16(OFF)
        self.input2 = PWM(Pin(in2, Pin.OUT))
        self.input2.freq(20000)
        self.input2.duty_u16(OFF)

    def cwDrive(self, speed=MAX_SPEED):
        self.input1.duty_u16(speed)
        self.input2.duty_u16(OFF)

    def ccwDrive(self, speed=MAX_SPEED):
        self.input2.duty_u16(speed)
        self.input1.duty_u16(OFF)

    def stop(self):
        self.input1.duty_u16(OFF)
        self.input2.duty_u16(OFF)


class DriveTrain:
    def __init__(self, mtr1, mtr2, oc_pin):
        self.motor1 = mtr1  # left motor
        self.motor2 = mtr2  # right motor

        # --- Overcurrent protection ---
        self._oc = Pin(oc_pin, Pin.IN, Pin.PULL_UP)
        self._oc_debounce = False
        self._oc_timer = Timer()
        self._debounce_timer = Timer()
        self.oc_triggered = False
        self._oc.irq(trigger=Pin.IRQ_FALLING, handler=self._over_current_check)

    # --- Overcurrent interrupt & debounce ---
    def _over_current_check(self, pin):
        print(self._oc_debounce, self.oc_triggered)
        if self._oc_debounce or self.oc_triggered:
            return
        print("debounce started")
        self._oc_debounce = True
        self._debounce_timer.init(
            mode=Timer.ONE_SHOT,
            period=500,
            callback=self._oc_stop_enable
        )

    def _oc_stop_enable(self, timer):
        print("stop check")
        if not self._oc.value():
            print("debounce true")
            self.oc_triggered = True      # ← Guard is up BEFORE debounce clears
            self._oc_debounce = False     # ← No window: oc_triggered is already True
            self.stop()
            self._oc_timer.init(
                mode=Timer.ONE_SHOT,
                period=500,
                callback=self._oc_stop_disable
            )
        else:
            self._oc_debounce = False     # ← Only clear if no fault confirmed
        
    def _oc_stop_disable(self, timer):
        self.oc_triggered = False
        
    # --- Drive methods ---

    def driveForward(self, speed=MAX_SPEED):
        self.motor1.cwDrive(speed)
        self.motor2.ccwDrive(speed)

    def driveBackward(self, speed=MAX_SPEED):
        self.motor1.ccwDrive(speed)
        self.motor2.cwDrive(speed)

    def steer(self, vector, speed):
        """
        vector: -1.0 = full left, 0 = straight, 1.0 = full right
        """
        if self.oc_triggered:
            return

        vector = max(-1.0, min(1.0, vector))
        left_speed  = int(max(MAX_SPEED, min(speed,OFF) * (1.0 + vector)))
        right_speed = int(max(MAX_SPEED, min(speed,OFF) * (1.0 - vector)))
        self.motor1.cwDrive(left_speed)
        self.motor2.ccwDrive(right_speed)

    def turnCW(self, speed=MAX_SPEED):
        if self.oc_triggered:
            return
        self.motor1.ccwDrive(speed)
        self.motor2.ccwDrive(speed)

    def turnCCW(self, speed=MAX_SPEED):
        if self.oc_triggered:
            return
        self.motor1.cwDrive(speed)
        self.motor2.cwDrive(speed)

    def stop(self):
        self.motor1.stop()
        self.motor2.stop()