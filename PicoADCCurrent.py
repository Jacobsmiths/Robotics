from machine import ADC, Pin, Timer

adc = ADC(Pin(26))

def sample(timer):
    value = adc.read_u16()
    voltage = 3.3 * (value/65535)
    print(voltage)

tim = Timer()
tim.init(freq=1000, mode=Timer.PERIODIC, callback=sample)