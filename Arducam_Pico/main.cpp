#include <stdio.h>
#include <cstdlib>
#include "pico/stdlib.h"
#include "pico/stdio_usb.h"
#include "arduCAM.h"

#define IMAGE_FORMAT 1  // 1 = YUV422 (raw)

int main() {
    if (!wiring_init()) {
        return -1;
    }

    while (!stdio_usb_connected()) {
        sleep_ms(100);
    }
    sleep_ms(500);

    printf("=== ArduCAM OV2640 — YUV422 USB transfer mode ===\n");

    ArduCAM myCAM(IMAGE_FORMAT);

    myCAM.bus_write(0x00, 0x55);
    if (myCAM.bus_read(0x00) != 0x55) {
        printf("ERROR: SPI interface failed\n");
        while (1);
    }
    printf("SPI OK\n");

    myCAM.InitCAM();
    // NOTE: Do NOT call OV2640_set_JPEG_size() here.
    // That function writes JPEG-specific register tables which will
    // corrupt YUV422 output. InitCAM() already sets QVGA (320x240)
    // via OV2640_QVGA when IMAGE_FORMAT != 0.
    sleep_ms(1000);

    printf("Capturing YUV422 320x240...\n");

    myCAM.flush_fifo();
    myCAM.clear_fifo_flag();
    myCAM.start_capture();

    while (!myCAM.get_bit(ARDUCHIP_TRIG, CAP_DONE_MASK));
    printf("Capture complete.\n");

    uint32_t len = myCAM.read_fifo_length();

    // YUV422 at 320x240 is always exactly 320 * 240 * 2 = 153600 bytes.
    // If read_fifo_length() returns something wildly different the
    // capture failed — bail rather than sending garbage.
    // const uint32_t EXPECTED = 320 * 240 * 2;
    // if (len == 0 || len >= 0x07ffff) {
    //     printf("ERROR: Bad FIFO length: %lu (expected %lu)\n", len, EXPECTED);
    //     return -1;
    // }
    // if (len != EXPECTED) {
    //     printf("WARNING: FIFO length %lu != expected %lu, sending anyway\n", len, EXPECTED);
    // }
    printf("Image size: %lu bytes\n", len);

    printf("SENDING_IMAGE:%lu\n", len);
    stdio_flush();
    sleep_ms(50);

    // myCAM.set_fifo_burst();

    // for (uint32_t i = 0; i < len; i++) {
    //     putchar_raw((int)myCAM.transfer(0x00));
    // }

    // CS_HIGH();
    uint32_t buffer_length = 240*320*2;
    uint8_t* image_buffer = (uint8_t*)malloc(buffer_length);

    // Capture logic...
    // This one line replaces the loop and the manual CS management
    myCAM.read_fifo_to_buffer(image_buffer, buffer_length);

    for (uint32_t i = 0; i < len; i++) {
        putchar_raw((int)image_buffer[i]);
    }


    stdio_flush();
    sleep_ms(100);

    printf("IMAGE_DONE\n");
    stdio_flush();

    printf("Transfer complete.\n");
    return 0;
}