from machine import Pin, PWM
import time

# ===================== CALIBRATED Thresh/ constants =====================
# Empty (Black Plastic) was ~450
# Ball Present was ~2500
INTENSITY_THRESHOLD = 1000

MIN_DUTY, MAX_DUTY = 3277, 6553

CENTER = 90
RANGE = 45
SERVO_CLOSED = CENTER + RANGE
SERVO_OPEN   = CENTER - RANGE

RED_REF   = (320, 90, 85)
GREEN_REF = (1325, 1500, 900)
BLUE_REF  = (95, 130, 310)

class kicker:
    def __init__(self, servo_pin):
        self.servo = PWM(Pin(servo_pin))
        self.servo.freq(50)
        self.current_angle = CENTER
        self.servo.duty_u16(angle_to_duty(self.current_angle))
        self._move_timer = Timer()
        self._target_angle = self.current_angle
        self._step = 6
        self._moving = False

        self.motor1, self.motor2 = PWM(Pin(16)), PWM(Pin(17))
        self.motor1.freq(1000), self.motor2.freq(1000)
        self.motor1_scale, self.motor2_scale = 1.0, 0.30
        
        self.S0, self.S1 = Pin(22, Pin.OUT), Pin(21, Pin.OUT)
        self.S2, self.S3 = Pin(20, Pin.OUT), Pin(19, Pin.OUT)
        self.OUT = Pin(0, Pin.IN)

        self.S0.value(1) # Frequency Scaling 20% (Stable)
        self.S1.value(0) 

# ===================== SERVO SETUP =====================
    def angle_to_duty(self, angle):
        angle = max(0, min(180, angle))
        return int(MIN_DUTY + (angle / 180) * (MAX_DUTY - MIN_DUTY))

    def _move_step(self, timer):
        if self.current_angle == self._target_angle:
            timer.deinit()
            self._moving = False
            return

        step = self._step if self.current_angle < self._target_angle else -self._step
        next_angle = self.current_angle + step

        # Clamp so we don't overshoot the target
        if step > 0:
            next_angle = min(next_angle, self._target_angle)
        else:
            next_angle = max(next_angle, self._target_angle)

        self.current_angle = next_angle
        self.servo.duty_u16(self.angle_to_duty(self.current_angle))

    def move_smooth(self, target, step=6, delay_ms=5):
        """Non-blocking smooth move to target angle."""
        if self._moving:
            self._move_timer.deinit()   # Cancel any in-progress move

        self._target_angle = max(0, min(180, target))
        self._step = step
        self._moving = True
        self._move_timer.init(
            mode=Timer.PERIODIC,
            period=delay_ms,
            callback=self._move_step
        )

    def open_gate(self):
        move_smooth(SERVO_OPEN)
        self.current_angle = SERVO_OPEN
        print("Gate OPEN")

    def close_gate(self):
        move_smooth(current_angle, SERVO_CLOSED)
        self.current_angle = SERVO_CLOSED
        print("Gate CLOSED")

# ===================== MOTOR SETUP =====================
    def set_speed(self, percent):
        percent = max(0, min(100, percent))
        base = (percent / 100) * 65535
        d1 = int(base * motor1_scale)
        d2 = int(base * motor2_scale)
        if percent > 0: d2 = max(d2, 8000)
        self.motor1.duty_u16(d1)
        self.motor2.duty_u16(d2)

    def motor_on(self):
        self.motor1.duty_u16(50000)
        self.motor2.duty_u16(50000)
        time.sleep(0.05)
        self.set_speed(60)
        print("Flywheels ON")

    def motor_off(self):
        set_speed(0)
        print("Flywheels OFF")

# ===================== COLOR SENSOR SETUP =====================
    def read_frequency(self, duration_ms=40):
        start = time.ticks_ms()
        count = 0
        last = OUT.value()
        while time.ticks_diff(time.ticks_ms(), start) < duration_ms:
            v = OUT.value()
            if v != last:
                count += 1
                last = v
        return count

    def read_color(self, s2, s3):
        self.S2.value(s2)
        self.S3.value(s3)
        time.sleep_ms(10)
        return read_frequency()

    def average_rgb(self, samples=2):
        r = sum(read_color(0, 0) for _ in range(samples)) // samples
        b = sum(read_color(0, 1) for _ in range(samples)) // samples
        g = sum(read_color(1, 1) for _ in range(samples)) // samples
        return r, g, b

# ===================== DETECTION LOGIC =====================
    def normalize(self, rgb):
        total = sum(rgb)
        return (0,0,0) if total == 0 else (rgb[0]/total, rgb[1]/total, rgb[2]/total)

    def detect_color(self, R, G, B):
        sample = normalize((R, G, B))
        dists = {
            "RED": sum(abs(sample[i] - normalize(RED_REF)[i]) for i in range(3)),
            "GREEN": sum(abs(sample[i] - normalize(GREEN_REF)[i]) for i in range(3)),
            "BLUE": sum(abs(sample[i] - normalize(BLUE_REF)[i]) for i in range(3))
        }
        best = min(dists, key=dists.get)
        return best if dists[best] < 0.5 else "UNCERTAIN"

    def ball_present(self):
        # Read Clear Channel
        S2.value(1); S3.value(0)
        time.sleep_ms(10)
        val = read_frequency(duration_ms=50)
        print(f"Sensor Intensity: {val}")
        return val > INTENSITY_THRESHOLD

# ===================== MAIN LOOP =====================
while True:
    if not ball_present():
        motor_off()
        close_gate()
        time.sleep(0.1) # Faster polling
        continue

    print("!!! Ball detected !!!")
    
    # 1. Warm up the motors BEFORE opening the gate
    # This ensures the first ball is sucked out immediately
    motor_on() 
    time.sleep(0.4) 

    # 2. Final color check while motors are spinning
    counts = {"RED": 0, "GREEN": 0, "BLUE": 0}
    for _ in range(5): # Fast 5-sample check
        R, G, B = average_rgb(samples=1)
        res = detect_color(R, G, B)
        if res in counts: counts[res] += 1
    
    final_color = max(counts, key=counts.get)
    print(f"FINAL COLOR: {final_color}")

    # 3. THE QUICK SNAP
    # We open the gate and close it VERY quickly
    open_gate()
    
    # TWEAK THIS: How long does it take for ONE ball to roll 2 inches?
    # If two balls still escape, lower this to 0.3 or 0.2
    time.sleep(0.2) 
    
    close_gate() # Slam it shut to catch the second ball
    print("Gate snapped shut - catching next ball")

    # 4. Keep motors on a bit longer to finish launching the first ball
    time.sleep(0.8)
    
    motor_off()
    print("Cycle complete.\n")
    
    # 5. Mandatory pause to let the next ball roll down and settle
    time.sleep(0.5)