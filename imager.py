import time
import sys
import select
from machine import SPI, Pin
from Arducam import *
import gc

# ── Tuning ────────────────────────────────────────────────────────────────────
CHROMA_THRESH = 30
V_MIN         = 80
Y_MIN         = 20
Y_MAX         = 235

MIN_AREA      = 2      # Minimum pixels to be considered a blob
WIDTH         = 320
HEIGHT        = 240

# Coarse grid cell size for density search
# Smaller = more precise peak finding, more computation
CELL_SIZE     = 16      # divides 320x160 into 20x10 = 200 cells
# ─────────────────────────────────────────────────────────────────────────────

GRID_W = WIDTH  // CELL_SIZE   # 20
GRID_H = HEIGHT // CELL_SIZE   # 10


def color_mask(yuv_buf, mask, length):
    """UYVY byte order — OpenCV COLOR_BGR2YUV_Y422 output."""
    mask_idx = 0
    my = 0
    while my < HEIGHT:
        row_base = my * WIDTH * 2
        mx = 0
        while mx < WIDTH:
            mp = row_base + (mx & 0xFFFE) * 2
            u = yuv_buf[mp + 0]
            y = yuv_buf[mp + (3 if (mx & 1) else 1)]
            v = yuv_buf[mp + 2]

            cu     = u - 128
            cv     = v - 128
            chroma = (cu if cu >= 0 else -cu) + (cv if cv >= 0 else -cv)

            mask[mask_idx] = 1 if (
                Y_MIN  <= y      <= Y_MAX   and
                chroma >= CHROMA_THRESH     and
                v      >= V_MIN
            ) else 0

            mask_idx += 1
            mx += 1
        my += 1


def build_density_grid(mask, grid):
    """
    Downsample the binary mask into a coarse hit-count grid.
    Each cell = how many mask pixels are ON in that CELL_SIZE x CELL_SIZE block.
    This is O(W*H) and very cheap.
    """
    # Zero the grid
    for i in range(len(grid)):
        grid[i] = 0

    idx = 0
    py = 0
    while py < HEIGHT:
        gy = py // CELL_SIZE
        px = 0
        while px < WIDTH:
            if mask[idx]:
                gx = px // CELL_SIZE
                grid[gy * GRID_W + gx] += 1
            idx += 1
            px += 1
        py += 1


def find_peak_cell(grid):
    """Return (gx, gy) of the grid cell with the highest hit count."""
    best_count = 0
    best_gx    = 0
    best_gy    = 0

    for gy in range(GRID_H):
        for gx in range(GRID_W):
            count = grid[gy * GRID_W + gx]
            if count > best_count:
                best_count = count
                best_gx    = gx
                best_gy    = gy

    return best_gx, best_gy, best_count


def analyze_blob_local(mask, center_gx, center_gy, search_radius_cells=3):
    x0 = max(0,      (center_gx - search_radius_cells) * CELL_SIZE)
    x1 = min(WIDTH,  (center_gx + search_radius_cells + 1) * CELL_SIZE)
    y0 = max(0,      (center_gy - search_radius_cells) * CELL_SIZE)
    y1 = min(HEIGHT, (center_gy + search_radius_cells + 1) * CELL_SIZE)

    m00, m10, m01 = 0,0,0
    min_x, max_x, min_y, max_y = x1, x0, y1, y0

    py = y0
    while py < y1:
        px = x0
        while px < x1:
            if mask[py * WIDTH + px]:
                m00 += 1
                m10 += px
                m01 += py
                if px < min_x: min_x = px
                if px > max_x: max_x = px
                if py < min_y: min_y = py
                if py > max_y: max_y = py
            px += 1
        py += 1

    if m00 < MIN_AREA:
        return None

    cx = m10 // m00
    cy = m01 // m00

    bw = max_x - min_x + 1
    bh = max_y - min_y + 1

    fill_ratio_100   = (m00 * 100) // (bw * bh)
    aspect_ratio_100 = (bw * 100) // bh

    # Debug — comment out once tuned
    print(f"  [blob] area:{m00} bbox:{bw}x{bh} fill:{fill_ratio_100}% aspect:{aspect_ratio_100}%")

    # Shape check — reasonably circular
    if 50 <= aspect_ratio_100 <= 180 and 10 <= fill_ratio_100 <= 100:
        return (cx, cy, m00, fill_ratio_100)

    return None

mycam = ArducamClass()
time.sleep(1)
mycam.spi_test()
mycam.Camera_Init()
time.sleep(1)

while True:
    mycam.clear_fifo();
    mycam.clear_fifo();
    mycam.start_capture();
    while(not mycam.get_bit(0x41,0x08)):
        time.sleep(1)
    
    length = mycam.read_fifo_length()
    print(f"capture completed, fifo length: {length}") 
#     buf = bytearray(length)
#     mask = bytearray(HEIGHT*WIDTH)
#     density_grid = bytearray(GRID_W*GRID_H)
#     mycam.capture_to_buffer(buf)
#     
#     color_mask(buf, mask)
#     build_density_grid(mask, density_grid)
#     peak_gx, peak_gy, peak_count = find_peak_cell(density_grid)
# 
#     # 3 — Analyze blob only around the peak cell
#     result = None
#     if peak_count >= MIN_AREA:
#         result = analyze_blob_local(mask, peak_gx, peak_gy, search_radius_cells=3)
#         print(f"ball found")
    gc.collect()
    time.sleep(2)
    
        