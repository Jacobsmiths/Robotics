#ifndef RP2_H
#define RP2_H
#ifdef __cplusplus
extern "C" {
#endif

struct sensor_reg {
	uint16_t reg;
	uint16_t val;
};

extern bool wiring_init(void);
extern bool arducam_i2c_init(uint8_t sensor_addr);
extern void arducam_spi_write(uint8_t address, uint8_t value);
extern uint8_t arducam_spi_read(uint8_t address);

extern uint8_t arducam_spi_transfer(uint8_t data);
extern void arducam_spi_transfers(uint8_t *buf, uint32_t size);

// Delay execution for delay milliseconds
extern void arducam_delay_ms(uint32_t delay);

// Read/write 8 bit value to/from 8 bit register address
extern uint8_t arducam_i2c_write(uint8_t sensor_addr, uint8_t regID, uint8_t regDat);
extern uint8_t arducam_i2c_read(uint8_t sensor_addr, uint8_t regID, uint8_t* regDat);

// Write 8 bit values to 8 bit register address
extern int arducam_i2c_write_regs(uint8_t sensor_addr, const struct sensor_reg reglist[]);

extern void CS_HIGH(void);
extern void CS_LOW(void);

#ifdef __cplusplus
}
#endif


#endif 