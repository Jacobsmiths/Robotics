#include <stdio.h>
#include "pico/stdlib.h"
#include "pico/time.h"
#include "hardware/spi.h"
#include "hardware/i2c.h"
#include "arduCAM.h"


ArduCAM::ArduCAM(uint8_t fmt) {
    sensor_addr = 0x30;
    m_fmt = fmt;

	if (!arducam_i2c_init(sensor_addr)) {
		printf("ERROR: I2C init failed\n");
	}
}

void ArduCAM::InitCAM() {
    wrSensorReg8_8(0xff, 0x01); // switches the bank
    wrSensorReg8_8(0x12, 0x80); // triggers reset
    sleep_ms(100);
    wrSensorReg8_8(0xff, 0x00);
    sleep_ms(100);
    
    if (m_fmt == 0) {
        wrSensorRegs8_8(OV2640_JPEG_INIT);
        wrSensorRegs8_8(OV2640_YUV422);
        wrSensorRegs8_8(OV2640_JPEG);
        wrSensorReg8_8(0xff, 0x01);
        wrSensorReg8_8(0x15, 0x00);
        wrSensorRegs8_8(OV2640_320x240_JPEG);
    } else { // THIS IS WHAT WE WANT
        wrSensorRegs8_8(OV2640_QVGA); // Default RGB/YUV
        // wrSensorRegs8_8(OV2640_YUV422);
        // wrSensorReg8_8(0xff, 0x00); // Switch to Bank 0
        // wrSensorReg8_8(0x44, 0x00); // Disable JPEG En/Decoder
        // 2. Reset DSP
        wrSensorReg8_8(0xE0, 0x04);
        // 3. Set output format to RGB565
        wrSensorReg8_8(0xDA, 0x09);
        wrSensorReg8_8(0xE0, 0x00);
    }
    
}

// --- FIFO Operations ---
void ArduCAM::read_fifo_to_buffer(uint8_t* buffer, uint32_t length) {
    // 1. Start the burst sequence
    // cs needs to stay low entire transfer time
    CS_LOW();
    set_fifo_burst();
    transfer(0x00);
    transfers(buffer, length);
    CS_HIGH();
}

void ArduCAM::flush_fifo(void) {
    bus_write(ARDUCHIP_FIFO, FIFO_CLEAR_MASK);
}

void ArduCAM::start_capture(void) {
    bus_write(ARDUCHIP_FIFO, FIFO_START_MASK);
}

uint32_t ArduCAM::read_fifo_length(void) {
    uint32_t len1, len2, len3;
    len1 = bus_read(FIFO_SIZE1);
    len2 = bus_read(FIFO_SIZE2);
    len3 = bus_read(FIFO_SIZE3) & 0x7f;
    return ((len3 << 16) | (len2 << 8) | len1) & 0x07fffff;
}

uint8_t ArduCAM::read_fifo(void)
{
	uint8_t data;
	data = bus_read(SINGLE_FIFO_READ);
	return data;
}

void ArduCAM::clear_fifo_flag(void )
{
	bus_write(ARDUCHIP_FIFO, FIFO_CLEAR_MASK);
}

uint8_t ArduCAM::bus_write(int address, int value) {
    arducam_spi_write((uint8_t)(address | 0x80), (uint8_t)value);
    return 1;
}

uint8_t ArduCAM::bus_read(int address) {
	return arducam_spi_read((uint8_t)(address & 0x7F));
}

// --- Register Helpers ---
uint8_t ArduCAM::transfer(uint8_t data) {
    return arducam_spi_transfer(data);
}

void ArduCAM::transfers(uint8_t *buf, uint32_t size) {
    arducam_spi_transfers(buf, size);
}

void ArduCAM::set_fifo_burst() {
    // Note: Do NOT pull CS high here. CS must stay low 
    // during the entire subsequent burst read loop
    transfer(BURST_FIFO_READ);
}

//Set corresponding bit  
void ArduCAM::set_bit(uint8_t addr, uint8_t bit)
{
	uint8_t temp;
	temp = bus_read(addr);
	bus_write(addr, temp | bit);
}
//Clear corresponding bit 
void ArduCAM::clear_bit(uint8_t addr, uint8_t bit)
{
	uint8_t temp;
	temp = bus_read(addr);
	bus_write(addr, temp & (~bit));
}

//Get corresponding bit status
uint8_t ArduCAM::get_bit(uint8_t addr, uint8_t bit)
{
  uint8_t temp;
  temp = bus_read(addr);
  temp = temp & bit;
  return temp;
}


// --- OV2640 Specific Settings ---
void ArduCAM::OV2640_set_JPEG_size(uint8_t size) {
    switch(size) {
        case 0:   wrSensorRegs8_8(OV2640_160x120_JPEG); break;
        case 1:   wrSensorRegs8_8(OV2640_320x240_JPEG); break;
        case 2:   wrSensorRegs8_8(OV2640_640x480_JPEG); break;
        case 3:   wrSensorRegs8_8(OV2640_1024x768_JPEG); break;
        case 4:   wrSensorRegs8_8(OV2640_1600x1200_JPEG); break;
        default:  wrSensorRegs8_8(OV2640_320x240_JPEG); break;
    }
}

void ArduCAM::set_format(uint8_t fmt) {
    m_fmt = fmt;
}

// Write 8 bit values to 8 bit register address
int ArduCAM::wrSensorRegs8_8(const struct sensor_reg reglist[])
{
	arducam_i2c_write_regs(sensor_addr, reglist);
	return 1;
}

// Read/write 8 bit value to/from 8 bit register address	
uint8_t ArduCAM::wrSensorReg8_8(int regID, int regDat)
{
	arducam_i2c_write(sensor_addr, regID , regDat);
	return 1;
}
uint8_t ArduCAM::rdSensorReg8_8(uint8_t regID, uint8_t* regDat)
{	
	arducam_i2c_read(sensor_addr, regID,regDat);
	return 1;
}
