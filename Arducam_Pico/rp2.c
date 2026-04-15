#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include "hardware/i2c.h"
#include "rp2.h"

#define SPI_PORT       spi0
#define PIN_MISO       4
#define PIN_CS         5
#define PIN_SCK        2
#define PIN_MOSI       3

#define I2C_PORT       i2c0
#define PIN_SDA        8
#define PIN_SCL        9

#define SPI_SPEED      1000000 // 1MHz this was in the arducam docs

bool wiring_init(void) {
    stdio_init_all();

    // SPI Initialization
    spi_init(SPI_PORT, SPI_SPEED);
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SCK,  GPIO_FUNC_SPI);
    gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);
    
    // Chip Select is handled manually for better control with Arducam and set to high, low when transferring
    gpio_init(PIN_CS);
    gpio_set_dir(PIN_CS, GPIO_OUT);
    CS_HIGH();

    return true;
}

bool arducam_i2c_init(uint8_t sensor_addr) {
    // I2C Initialization at 100Khz
    i2c_init(I2C_PORT, 100 * 1000); // this was in pico sdk documentation
    gpio_set_function(PIN_SDA, GPIO_FUNC_I2C);
    gpio_set_function(PIN_SCL, GPIO_FUNC_I2C);
    gpio_pull_up(PIN_SDA);
    gpio_pull_up(PIN_SCL);
    return true;
}

void arducam_delay_ms(uint32_t delay) {
    sleep_ms(delay);
}

void arducam_spi_write(uint8_t address, uint8_t value) {
    uint8_t data[2] = {address, value};
    CS_LOW();
    spi_write_blocking(SPI_PORT, data, 2);
    CS_HIGH();
}

uint8_t arducam_spi_read(uint8_t address) {
    uint8_t value;
    uint8_t read_addr = address & 0x7F;
    CS_LOW();
    spi_write_blocking(SPI_PORT, &read_addr, 1);
    spi_read_blocking(SPI_PORT, 0x00, &value, 1);
    CS_HIGH();
    
    return value;
}

void arducam_spi_transfers(uint8_t *buf, uint32_t size) {
    /* Full-duplex in-place; caller must manage CS. Prefer arducam_spi_fifo_read_bytes for FIFO bursts. */
    spi_write_read_blocking(SPI_PORT, buf, buf, size);
}

uint8_t arducam_spi_transfer(uint8_t data) {
    uint8_t out;
    spi_write_read_blocking(SPI_PORT, &data, &out, 1);
    return out;
}

uint8_t arducam_i2c_write(uint8_t sensor_addr, uint8_t regID, uint8_t regDat) {
    uint8_t buf[2] = {regID, regDat};
    int ret = i2c_write_blocking(I2C_PORT, sensor_addr, buf, 2, false);
    return (ret != PICO_ERROR_GENERIC);
}

uint8_t arducam_i2c_read(uint8_t sensor_addr, uint8_t regID, uint8_t* regDat) {
    i2c_write_blocking(I2C_PORT, sensor_addr, &regID, 1, true);
    int ret = i2c_read_blocking(I2C_PORT, sensor_addr, regDat, 1, false);
    return (ret != PICO_ERROR_GENERIC);
}

// Helper for the loop-based register writes
int arducam_i2c_write_regs(uint8_t sensor_addr, const struct sensor_reg reglist[]) {
    const struct sensor_reg *next = reglist;
    while ((next->reg != 0xff) || (next->val != 0xff)) {
        if (!arducam_i2c_write(sensor_addr, next->reg, next->val)) return 0;
        next++;
    }
    return 1;
}

void inline CS_HIGH(void) {
    gpio_put(PIN_CS, 1);
}

void inline CS_LOW(void) {
    gpio_put(PIN_CS, 0);
}