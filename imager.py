import time
from machine import SPI, Pin, Timer
from Arducam import ArducamClass
import gc

WIDTH  = 320
HEIGHT = 240
GRID_W = 20
GRID_H = 15

buf  = bytearray(WIDTH * HEIGHT * 2)
grid = bytearray(GRID_W * GRID_H)
_out = bytearray(8)


PRIMED = 0
WAITING = 1
DONE = 2
state = PRIMED

@micropython.viper
def _build_grid(buf: ptr8, grid: ptr8):
    """
    ── Byte order fix ──────────────────────────────────────────────────────────
    ArduCam FIFO outputs RGB565 little-endian (low byte first).
    FIX: pixel = (b2 << 8) | b1   ← swapped vs original code

    ── Hue detection (0-255 hue scale, each unit ≈ 1.4°) ─────────────────────
    Red   hue ≈   0 (0°)   tolerance ±12 units (±17°)
    Green hue ≈  85 (120°) tolerance ±12 units (±17°)
    Blue  hue ≈ 171 (240°) tolerance ±12 units (±17°)

    Division-free check:  |ch_diff| * 43 ≤ delta * HUE_TOL
      HUE_TOL = 12  →  ±17° cone around each pure hue

    Other hardcoded gates
    ┌─────────────────────────────────────────────────────────────────┐
    │ V_MIN   = 40    brightness floor  (lowered for darker balls)    │
    │ V_MAX   = 245   brightness ceiling (raised for bright lighting) │
    │ D_MIN   = 40    min delta; rejects near-grey pixels             │
    │ S_MULT  = 80    saturation gate: delta*255 ≥ 80*maxc            │
    │                 → saturation ≥ ~31%                             │
    │ HUE_TOL = 12    hue tolerance in 0-255 scale units (≈ ±17°)    │
    └─────────────────────────────────────────────────────────────────┘
    """
    i = 0
    while i < 300:                         # clear 20*15 grid
        grid[i] = 0
        i += 1

    py = 0
    while py < 240:
        gy       = py >> 4
        row_base = py * 640
        px = 0
        while px < 320:
            j  = row_base + (px << 1)
            b1 = int(buf[j])
            b2 = int(buf[j + 1])

            # ── BYTE ORDER FIX: little-endian (b2 is high byte) ──────────────
            px16 = (b2 << 8) | b1

            r = ((px16 >> 11) & 0x1F) << 3
            g = ((px16 >> 5)  & 0x3F) << 2
            b = ( px16        & 0x1F) << 3

            maxc = r
            if g > maxc: maxc = g
            if b > maxc: maxc = b
            minc = r
            if g < minc: minc = g
            if b < minc: minc = b
            delta = maxc - minc

            hit = 0
            # Gate: value [V_MIN=40, V_MAX=245]
            # Gate: chroma floor [D_MIN=40]
            # Gate: saturation   [S_MULT=80 → delta*255 ≥ 80*maxc]
            if maxc >= 40 and maxc <= 245 and delta >= 40 and delta * 255 >= 80 * maxc:

                # ── Red  (hue ≈ 0 ± 17°) ─────────────────────────────────────
                # h = (g-b)*43/delta ≈ 0  →  |g-b|*43 ≤ delta*12
                if maxc == r:
                    diff = g - b
                    if diff < 0: diff = -diff
                    if diff * 43 <= delta * 12:    # [HUE_TOL = 12]
                        hit = 1

                # ── Green  (hue ≈ 85 ± 17°) ──────────────────────────────────
                # h = 85 + (b-r)*43/delta ≈ 85  →  |b-r|*43 ≤ delta*12
                elif maxc == g:
                    diff = b - r
                    if diff < 0: diff = -diff
                    if diff * 43 <= delta * 12:    # [HUE_TOL = 12]
                        hit = 1

                # ── Blue  (hue ≈ 171 ± 17°) ──────────────────────────────────
                # h = 171 + (r-g)*43/delta ≈ 171  →  |r-g|*43 ≤ delta*12
                else:
                    diff = r - g
                    if diff < 0: diff = -diff
                    if diff * 43 <= delta * 12:    # [HUE_TOL = 12]
                        hit = 1

            if hit:
                gx   = px >> 4
                cell = gy * 20 + gx
                cv   = int(grid[cell])
                if cv < 255:
                    grid[cell] = cv + 1

            px += 1
        py += 1


@micropython.viper
def _find_peak(grid: ptr8) -> int:
    best = 0; best_gx = 0; best_gy = 0
    gy = 0
    while gy < 15:
        gx = 0
        while gx < 20:
            c = int(grid[gy * 20 + gx])
            if c > best:
                best = c; best_gx = gx; best_gy = gy
            gx += 1
        gy += 1

    if best < 10:                          # [MIN_PEAK = 10]
        return 0

    # Cluster check: ≥ 2 neighbours with count ≥ 4
    neighbors = 0
    dy = -1
    while dy <= 1:
        dx = -1
        while dx <= 1:
            if dx != 0 or dy != 0:
                nx = best_gx + dx
                ny = best_gy + dy
                if nx >= 0 and nx < 20 and ny >= 0 and ny < 15:
                    if int(grid[ny * 20 + nx]) >= 4:
                        neighbors += 1
            dx += 1
        dy += 1

    if neighbors < 2:
        return 0

    return best_gx | (best_gy << 8) | (best << 16)


@micropython.viper
def _blob_roi(buf: ptr8, out: ptr8, center_gx: int, center_gy: int) -> int:
    x0 = (center_gx - 3) * 16;  x1 = (center_gx + 4) * 16
    y0 = (center_gy - 3) * 16;  y1 = (center_gy + 4) * 16
    if x0 < 0:    x0 = 0
    if x1 > 320:  x1 = 320
    if y0 < 0:    y0 = 0
    if y1 > 240:  y1 = 240

    m00 = 0; m10 = 0; m01 = 0
    min_x = x1; max_x = x0
    min_y = y1; max_y = y0

    py = y0
    while py < y1:
        row_base = py * 640
        px = x0
        while px < x1:
            j  = row_base + (px << 1)
            b1 = int(buf[j])
            b2 = int(buf[j + 1])

            # ── same byte-order fix ───────────────────────────────────────────
            px16 = (b2 << 8) | b1

            r = ((px16 >> 11) & 0x1F) << 3
            g = ((px16 >> 5)  & 0x3F) << 2
            b = ( px16        & 0x1F) << 3

            maxc = r
            if g > maxc: maxc = g
            if b > maxc: maxc = b
            minc = r
            if g < minc: minc = g
            if b < minc: minc = b
            delta = maxc - minc

            hit = 0
            if maxc >= 40 and maxc <= 245 and delta >= 40 and delta * 255 >= 80 * maxc:
                if maxc == r:
                    diff = g - b
                    if diff < 0: diff = -diff
                    if diff * 43 <= delta * 12:
                        hit = 1
                elif maxc == g:
                    diff = b - r
                    if diff < 0: diff = -diff
                    if diff * 43 <= delta * 12:
                        hit = 1
                else:
                    diff = r - g
                    if diff < 0: diff = -diff
                    if diff * 43 <= delta * 12:
                        hit = 1

            if hit:
                m00 += 1; m10 += px; m01 += py
                if px < min_x: min_x = px
                if px > max_x: max_x = px
                if py < min_y: min_y = py
                if py > max_y: max_y = py
            px += 1
        py += 1

    if m00 < 50:
        return 0

    bw = max_x - min_x + 1
    bh = max_y - min_y + 1
    aspect_100 = (bw * 100) // bh
    fill_100   = (m00 * 100) // (bw * bh)

    if aspect_100 < 70 or aspect_100 > 143:
        return 0
    if fill_100 < 30:
        return 0

    cx = m10 // m00
    cy = m01 // m00

    out[0] = cx  & 0xFF;  out[1] = (cx  >> 8) & 0xFF
    out[2] = cy  & 0xFF;  out[3] = (cy  >> 8) & 0xFF
    out[4] = m00 & 0xFF;  out[5] = (m00 >> 8) & 0xFF
    out[6] = fill_100 & 0xFF; out[7] = (fill_100 >> 8) & 0xFF
    return 1


def detect_ball():
    _build_grid(buf, grid)
    packed = _find_peak(grid)
    if packed == 0:
        return None
    gx = packed & 0xFF
    gy = (packed >> 8) & 0xFF
    if not _blob_roi(buf, _out, gx, gy):
        return None
    cx       = _out[0] | (_out[1] << 8)
    cy       = _out[2] | (_out[3] << 8)
    area     = _out[4] | (_out[5] << 8)
    fill_pct = _out[6] | (_out[7] << 8)
    return cx, cy, area, fill_pct

def check_bit(timer):
    global state
    if mycam.get_bit(0x41, 0x08):
        state = DONE
    
    
# def capture():
#     global state
#     if state == DONE: # process image
#         if mycam.read_fifo_length() == EXPECTED_LEN:
#             mycam.capture_to_buffer(buf)
#             result = detect_ball()
#             if result is None:
#                 print("no ball")
#             else:
#                 cx, cy, area, fill = result
#                 nx = (cx - 160) / 160.0
#                 ny = (cy - 120) / 120.0
#                 print(f"BALL ({cx},{cy}) norm=({nx:.2f},{ny:.2f}) area={area} fill={fill}%")
#                 
#         gc.collect()  
#         pollTimer.deinit()
#         state = PRIMED
#         
#     elif state == WAITING:
#         return
#     
#     elif state == PRIMED:
#         mycam.clear_fifo()
#         mycam.clear_fifo()
#         mycam.start_capture()
#     
#         pollTimer.init(mode=Timer.PERIODIC, freq=10000, callback=check_bit)
#         state = WAITING

def capture():
    mycam.clear_fifo()
    mycam.clear_fifo()
    mycam.start_capture()

    deadline = time.ticks_add(time.ticks_ms(), 1000)
    while not mycam.get_bit(0x41, 0x08):
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            print("capture timeout")
            break
        time.sleep_ms(5)

    if mycam.read_fifo_length() == EXPECTED_LEN:
        mycam.capture_to_buffer(buf)

        result = detect_ball()

        if result is None:
            print("no ball")
        else:
            cx, cy, area, fill = result
            nx = (cx - 160) / 160.0
            ny = (cy - 120) / 120.0
            print(f"BALL ({cx},{cy}) norm=({nx:.2f},{ny:.2f}) area={area} fill={fill}%")
            return nx
        return None
    

# ── Hardware init ─────────────────────────────────────────────────────────────
mycam = ArducamClass()
time.sleep(1)
mycam.spi_test()
mycam.Camera_Init()
time.sleep(1)
print("ready for capture")
EXPECTED_LEN = 153608

pollTimer = Timer()