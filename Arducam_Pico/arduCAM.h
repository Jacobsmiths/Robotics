#ifndef ARDUCAM_H
#define ARDUCAM_H

#define ARDUCHIP_FIFO      		0x04  //FIFO and I2C control
#define FIFO_CLEAR_MASK    		0x01
#define FIFO_START_MASK    		0x02

#define BURST_FIFO_READ			0x3C  //Burst FIFO read operation
#define SINGLE_FIFO_READ		0x3D  //Single FIFO read operation

#define ARDUCHIP_TRIG      		0x41  //Trigger source
#define VSYNC_MASK         		0x01
#define CAP_DONE_MASK      		0x08

#define FIFO_SIZE1				0x42  //Camera write FIFO size[7:0] for burst to read
#define FIFO_SIZE2				0x43  //Camera write FIFO size[15:8]
#define FIFO_SIZE3				0x44  //Camera write FIFO size[18:16]

#include <stdint.h>
#include "rp2.h"
#include "ov2640_regs.h"

class ArduCAM 
{
	public:
        ArduCAM( uint8_t fmt );
        void InitCAM( void );

        /** Issue start; call wait_capture_done() after. */
        void flush_fifo(void);
        void start_capture(void);
        void clear_fifo_flag(void);
        uint8_t read_fifo(void);

        void read_fifo_to_buffer(uint8_t* buffer, uint32_t length); // I ADDED THIS JUST NOW 
        /** Hardware FIFO length (may disagree with expected on some setups). */
        uint32_t read_fifo_length(void);

        void set_fifo_burst(void);
        
        void set_bit(uint8_t addr, uint8_t bit);
        void clear_bit(uint8_t addr, uint8_t bit);
        uint8_t get_bit(uint8_t addr, uint8_t bit);

        // Write 8 bit values to 8 bit register address
        int wrSensorRegs8_8(const struct sensor_reg*);
        
        // Read/write 8 bit value to/from 8 bit register address	
        uint8_t wrSensorReg8_8(int regID, int regDat);
        uint8_t rdSensorReg8_8(uint8_t regID, uint8_t* regDat);

        void set_format(uint8_t fmt);
        
        uint8_t transfer(uint8_t data);
        void transfers(uint8_t *buf, uint32_t size);
        uint8_t bus_read(int address);
        uint8_t bus_write(int address, int value);
        void OV2640_set_JPEG_size(uint8_t size);

    protected:
        uint8_t m_fmt;
        uint8_t sensor_addr;
};




#endif