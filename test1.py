"""
Periodic capture every 4 seconds using a Timer interrupt + micropython.schedule.

The timer IRQ only requests work; capture runs on the main MicroPython thread.
(SPI/I2C must not run inside hardware interrupt callbacks.)
"""
print("ok")
import micropython
print("ok")
import time
print("ok")

from machine import Timer
print("ok")

import arduCAM
print("ok")

# --- configuration ---
CAPTURE_INTERVAL_MS = 4000
CAM_FORMAT = 1  # same as ArduCAM(1) in your driver (QVGA / RGB path)

# ---------------------------------------------------------------------------
busy = False

print("ok")

def capture_frame(_):
    """Runs in main context (scheduled), not inside the timer ISR."""
    global busy
    if busy:
        return
    busy = True
    try:
        cam.flush_fifo()
        cam.clear_fifo_flag()
        cam.start_capture()
        try:
            cam.wait_capture_done(5000)
        except OSError:
            print("capture: timeout waiting for VSYNC/FIFO")
            return

        n = cam.fifo_length()
        if n == 0:
            print("capture: empty FIFO")
            return

        buf = bytearray(n)
        cam.read_fifo_to_buffer(buf)

        # --- your image processing / storage goes here ---
        print("frame bytes:", n, "head:", bytes(buf[:16]))

    finally:
        busy = False


def timer_irq(t):
    # Keep this minimal: only defer to main context.
    micropython.schedule(capture_frame, None)


# ---------------------------------------------------------------------------
arduCAM.wiring_init()
cam = arduCAM.ArduCAM(CAM_FORMAT)
cam.init_cam()
print("ok")

tim = Timer(-1)
tim.init(period=CAPTURE_INTERVAL_MS, mode=Timer.PERIODIC, callback=timer_irq)
print("ok")

print("Capturing every %d ms; main thread stays free for other work." % CAPTURE_INTERVAL_MS)

try:
    # Main thread: put your non-blocking control loop / state machine here.
    while True:
        time.sleep_ms(500)
except KeyboardInterrupt:
    pass
finally:
    tim.deinit()
    cam.deinit()
    print("stopped.")
print("ok")
