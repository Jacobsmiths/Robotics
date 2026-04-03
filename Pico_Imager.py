import machine
import utime
from machine import Pin
import gc
from Arducam import ArducamClass
import array
import micropython
from micropython import const

# ── Tuning ────────────────────────────────────────────────────────────────────
CHROMA_THRESH = const(30)
V_MIN         = const(80)
Y_MIN         = const(20)
Y_MAX         = const(235)
WIDTH         = const(96)
HEIGHT        = const(96)
MIN_AREA      = const(2)
CELL_SIZE     = const(16)
GRID_W        = const(WIDTH//CELL_SIZE)
GRID_H        = const(HEIGHT//CELL_SIZE)
SEARCH_RADIUS = const(3)

FRAME_BYTES   = const(WIDTH*HEIGHT*2)    # WIDTH * HEIGHT * 2  — used for FIFO validation
# ─────────────────────────────────────────────────────────────────────────────

# ── Persistent allocations ────────────────────────────────────────────────────
frame_buffer = bytearray(FRAME_BYTES)
density_grid = array.array('i', [0] * (GRID_W * GRID_H))
result_buf   = array.array('i', [0, 0, 0, 0])
# ─────────────────────────────────────────────────────────────────────────────

@micropython.viper
def color_mask(yuv_buf: ptr8):
    """
    Classify every pixel in the UYVY frame and write the binary mask back
    into the first half of the same buffer (in-place, no extra RAM).

    UYVY byte layout — matches both OpenCV COLOR_BGR2YUV_Y422 and the
    OV2640's native YUV422 output when configured with OV2640_YUV422:
        mp+0 : U  (shared by even and odd pixel of the macro-pixel)
        mp+1 : Y₀ (even pixel luminance)
        mp+2 : V  (shared by even and odd pixel)
        mp+3 : Y₁ (odd pixel luminance)

    Why we process TWO pixels per iteration (macro-pixel at a time)
    ---------------------------------------------------------------
    Both pixels share U (at mp+0).  If we wrote the even-pixel mask result
    to buf[write_idx] before reading U for the odd pixel, and write_idx
    happened to equal mp+0, we would corrupt U.  Processing the full
    macro-pixel — reading all 4 bytes first, then writing both mask bytes —
    guarantees reads always precede their corresponding writes regardless of
    byte order.

    Safety of the in-place overwrite
    ---------------------------------
    write_idx for even pixel  = my * WIDTH + mx          (1 byte/px stride)
    read  base (mp)           = my * WIDTH * 2 + mx * 2  (2 bytes/px stride)

    At the start of each row:   mp = my*640,  write_idx = my*320
    After k macro-pixels:       mp = my*640 + k*4,  write_idx = my*320 + k*2
    Gap = mp - write_idx = my*320 + k*2  ≥ 0 always.
    For my=0, k=0 both are 0 — but we read all 4 bytes before writing either,
    so no byte is read after it has been written.
    """
    chroma_thresh = int(CHROMA_THRESH)
    v_min  = int(V_MIN)
    y_min  = int(Y_MIN)
    y_max  = int(Y_MAX)
    width  = int(WIDTH)
    height = int(HEIGHT)

    write_idx = 0
    my = 0
    while my < height:
        row_base = my * width * 2
        mx = 0
        while mx < width:          # step += 2 at bottom — one macro-pixel/iter
            mp = row_base + mx * 2

            # ── Read all 4 bytes BEFORE any write ────────────────────────────
            # UYVY order: U, Y₀, V, Y₁
            u  = int(yuv_buf[mp])
            y0 = int(yuv_buf[mp + 1])
            v  = int(yuv_buf[mp + 2])
            y1 = int(yuv_buf[mp + 3])

            # ── Chroma magnitude (Manhattan distance from grey) ──────────────
            cu = u - 128
            cv = v - 128
            if cu < 0: cu = -cu
            if cv < 0: cv = -cv
            chroma = cu + cv

            # ── Classify even pixel (Y₀) ─────────────────────────────────────
            if y0 >= y_min and y0 <= y_max and chroma >= chroma_thresh and v >= v_min:
                yuv_buf[write_idx] = 1
            else:
                yuv_buf[write_idx] = 0
            write_idx += 1

            # ── Classify odd pixel (Y₁) — same U/V, different Y ─────────────
            if y1 >= y_min and y1 <= y_max and chroma >= chroma_thresh and v >= v_min:
                yuv_buf[write_idx] = 1
            else:
                yuv_buf[write_idx] = 0
            write_idx += 1

            mx += 2   # advance by one macro-pixel (2 pixels)
        my += 1


@micropython.viper
def build_density_grid(mask_in: ptr8, grid: ptr32):
    cell   = int(CELL_SIZE)
    width  = int(WIDTH)
    height = int(HEIGHT)
    grid_w = int(GRID_W)
    total  = int(GRID_W) * int(GRID_H)

    i = 0
    while i < total:
        grid[i] = 0
        i += 1

    idx = 0
    py = 0
    while py < height:
        gy = py // cell
        px = 0
        while px < width:
            if mask_in[idx]:
                gx = px // cell
                gi = gy * grid_w + gx
                grid[gi] = grid[gi] + 1
            idx += 1
            px += 1
        py += 1


@micropython.viper
def find_peak_cell(grid: ptr32) -> int:
    """
    Returns a packed int:  gx | (gy << 8) | (peak_count << 16)
    """
    grid_w     = int(GRID_W)
    grid_h     = int(GRID_H)
    best_count = 0
    best_gx    = 0
    best_gy    = 0

    gy = 0
    while gy < grid_h:
        gx = 0
        while gx < grid_w:
            count = int(grid[gy * grid_w + gx])
            if count > best_count:
                best_count = count
                best_gx    = gx
                best_gy    = gy
            gx += 1
        gy += 1

    return best_gx | (best_gy << 8) | (best_count << 16)


@micropython.viper
def analyze_blob_local(mask_in: ptr8, result: ptr32, center_gx: int, center_gy: int) -> int:
    cell     = int(CELL_SIZE)
    width    = int(WIDTH)
    height   = int(HEIGHT)
    min_area = int(MIN_AREA)
    radius   = int(SEARCH_RADIUS)

    x0 = (center_gx - radius) * cell
    x1 = (center_gx + radius + 1) * cell
    y0 = (center_gy - radius) * cell
    y1 = (center_gy + radius + 1) * cell
    if x0 < 0:      x0 = 0
    if x1 > width:  x1 = width
    if y0 < 0:      y0 = 0
    if y1 > height: y1 = height

    m00   = 0
    m10   = 0
    m01   = 0
    min_x = x1
    max_x = x0
    min_y = y1
    max_y = y0

    py = y0
    while py < y1:
        row = py * width
        px  = x0
        while px < x1:
            if mask_in[row + px]:
                m00 += 1
                m10 += px
                m01 += py
                if px < min_x: min_x = px
                if px > max_x: max_x = px
                if py < min_y: min_y = py
                if py > max_y: max_y = py
            px += 1
        py += 1

    if m00 < min_area:
        return 0

    cx       = m10 // m00
    cy       = m01 // m00
    bw       = max_x - min_x + 1
    bh       = max_y - min_y + 1
    fill_100 = (m00 * 100) // (bw * bh)
    aspect   = (bw * 100) // bh

    if aspect >= 50 and aspect <= 180 and fill_100 >= 20 and fill_100 <= 100:
        result[0] = cx
        result[1] = cy
        result[2] = m00
        result[3] = fill_100
        return 1

    return 0


def read_frame_chunked():
    """
    Read FRAME_BYTES from the ArduCAM FIFO into frame_buffer in CHUNK_SIZE
    pieces using a memoryview so there are zero heap allocations in the loop.
 
    Fixes vs. previous version
    --------------------------
    1. FIFO length is validated BEFORE we start reading — if it looks wrong we
       bail immediately without touching the buffer.
    2. The dummy byte required after the 0x3C burst-read command is consumed
       before data reads begin (omitting it shifts every byte by 1).
    3. spi.readinto(mv[i:i+chunk]) slices the memoryview — this is a zero-copy
       view, not a bytearray copy, so no heap allocation happens per chunk.
       Critically, a memoryview slice CANNOT grow the underlying buffer, so an
       oversized FIFO length can never cause a MemoryError.
    4. We loop to exactly FRAME_BYTES, not `length`.  The FIFO may have a byte
       or two of padding; we don't care — we read exactly what we need.
    """
    length = mycam.read_fifo_length()
 
    # Validate before touching the FIFO.  If the sensor is still capturing or
    # the SPI read glitched, length will be wrong.  96×96×2 = 18432.
    if abs(length - FRAME_BYTES) > 512:
        print(f"Bad FIFO length: {length} (expected {FRAME_BYTES})")
        return False
 
    chunk_size = int(CHUNK_SIZE)
    total      = int(FRAME_BYTES)
 
    mycam.cs.value(0)
    mycam.spi.write(bytes([0x3C]))  # burst read command
    mycam.spi.read(1)               # consume dummy byte — REQUIRED, fixes 1-byte shift
    
    i = 0
    while i < total:
        chunk = chunk_size if (total - i) >= chunk_size else (total - i)
        # memoryview slice: zero-copy, zero-allocation, cannot extend the buffer
        mycam.spi.readinto(_frame_mv[i : i + chunk])
        i += chunk
 
    mycam.cs.value(1)
    return True
 
 
def process():
    gc.collect()
 
    if not read_frame_chunked():
        mycam.clear_buffer()
        return None
 
    color_mask(frame_buffer)
    build_density_grid(frame_buffer, density_grid)
 
    packed     = find_peak_cell(density_grid)
    peak_gx    = packed & 0xFF
    peak_gy    = (packed >> 8) & 0xFF
    peak_count = packed >> 16
 
    if peak_count >= MIN_AREA:
        if analyze_blob_local(frame_buffer, result_buf, peak_gx, peak_gy):
            return (result_buf[0], result_buf[1], result_buf[2], result_buf[3])
 
    return None
 


# ── Main loop ─────────────────────────────────────────────────────────────────
mycam = ArducamClass()
utime.sleep(1)
mycam.spi_test()
mycam.Camera_Init()
utime.sleep(1)
mycam.clear_buffer()

while True:
    mycam.clear_fifo()
    mycam.clear_buffer()
    mycam.start_capture()
 
    if not mycam.get_bit(0x41, 0x08):
        result = process()
        mycam.clear_buffer()
        if result:
            cx, cy, area, fill = result
            print(f"Target! x:{cx} y:{cy} area:{area} fill:{fill}%")
        else:
            print("No target")
    utime.sleep_ms(500)