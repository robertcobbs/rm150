# Copyright (C) 2014 Synapse Wireless, Inc.
"""Thermocouple calculations.  Uses a NIST table for K-type thermocouples to convert
   between ADC counts (16bit, 256mV full-scale) to Celsius temperatures.
"""

DO_UNIT_TESTS = False

# K-type thermocouple table (see k_type.py)
k_table = '\xfe9\xfea\xfe\x8a\xfe\xb5\xfe\xe1\xff\x0e\xff=\xffl\xff\x9c\xff\xce\x00\x00\x003\x00f\x00\x9a\x00\xce\x01\x03\x018\x01m\x01\xa2\x01\xd7\x02\x0c\x02A\x02v\x02\xaa\x02\xde\x03\x12\x03E\x03x\x03\xac\x03\xdf\x04\x12\x04E\x04x\x04\xac\x04\xe0\x05\x14\x05H\x05|\x05\xb1\x05\xe6\x06\x1b\x06P\x06\x85\x06\xba\x06\xf0\x07&\x07[\x07\x91\x07\xc7\x07\xfd\x083\x08i\x08\x9f\x08\xd5\t\x0c\tB\tx\t\xaf\t\xe5\n\x1c\nR\n\x89\n\xc0\n\xf6\x0b-\x0bc\x0b\x9a\x0b\xd1\x0c\x07\x0c=\x0ct\x0c\xaa\x0c\xe1\r\x17\rM\r\x83\r\xb9\r\xef\x0e%\x0e[\x0e\x91\x0e\xc6\x0e\xfc\x0f1\x0ff\x0f\x9b\x0f\xd0\x10\x05\x10:\x10o\x10\xa3\x10\xd8\x11\x0c\x11@\x11t\x11\xa8\x11\xdc\x12\x0f\x12C\x12v\x12\xaa\x12\xdd\x13\x10\x13C\x13v\x13\xa8\x13\xdb\x14\r\x14?\x14q\x14\xa3\x14\xd5\x15\x07\x158\x15j\x15\x9b\x15\xcc\x15\xfd\x16.\x16_\x16\x8f\x16\xc0\x16\xf0\x17 \x17P\x17\x7f\x17\xaf'
TABLE_SIZE = 127   # 16 bit ints

# Temp limits in tenths C; range selected to fit in 255 byte string with 10degC intervals
MIN_TEMP = -100
MAX_TEMP = +1160
MIN_ADC = ord(k_table[0]) << 8 | ord(k_table[1])
MAX_ADC = ord(k_table[(TABLE_SIZE-1)*2]) << 8 | ord(k_table[(TABLE_SIZE-1)*2 + 1])

def ktable(i):
    """Return indexed 16-bit int from k_table"""
    i *= 2
    return ord(k_table[i]) << 8 | ord(k_table[i+1])

def C_to_adc(temp):
    """Convert temperature in tenths of degree C to ADC count from k-table"""
    if temp >= MAX_TEMP * 10:
        return MAX_ADC
    elif temp <= MIN_TEMP * 10:
        return MIN_ADC
        
    i = (temp - MIN_TEMP * 10) / 100
    
    low = ktable(i)
    high = ktable(i + 1)
    mod = temp % 100
    
    # Correct for SNAPpy's non-pythonic handling of negative modulus!
    if mod < 0:
        mod += 100
        
    adc = low + ((high - low) * mod) / 100
    return adc

def adc_to_C(adc_count):
    """Use table-lookup and interpolation to convert adc_count to temperature (tenths C)"""
    if adc_count >= MAX_ADC:
        return MAX_TEMP*10
    elif adc_count <= MIN_ADC:
        return MIN_TEMP*10
    
    start = ((adc_count - MIN_ADC) * 5) / 262
    i = start
    val = ktable(i)
    
    if val == adc_count:
        temp = ((i * 10) + MIN_TEMP)*10
        return temp

    while (i < start + 4 and val <= adc_count):
        i += 1
        prev = val
        val = ktable(i)
    
    # Temp is between a low of just over the prev index, and a high of the next one
    low = (((i-1) * 10) + MIN_TEMP) * 10
    inc = ((adc_count - prev) * 100) / (val - prev)
    temp = low + inc
    return temp


if DO_UNIT_TESTS:
    
    # Validate a few test points per NIST table values at precise 1 degree intervals
    test_temps = ( (-455, MIN_TEMP*10),
                   (-399, -860),
                   (-287, -600),
                   (-50, -100),
                   (0, 0),
                   (113, 220),
                   (154, 300),
                   (3729, 7000),
                   (6015, 11500),
                   (6063, MAX_TEMP*10)
                )
               
    def abs(x):
        return x if x > 0 else -x
                
    # Verify no more than +-1/10 degree or 1 ADC count error in calculations
    def test_therm():
        i = 0
        while i < len(test_temps):
            adc = test_temps[i][0]
            c = test_temps[i][1]
            calc_c = adc_to_C(adc)
            if abs(calc_c - c) > 1:
                print "Error: calc_temp=", calc_c, ", actual=", c
            
            calc_adc = C_to_adc(c)
            if abs(calc_adc - adc) > 1:
                print "Error: calc_adc=", calc_adc, ", actual=", adc

            i += 1
        
        print "Test Complete."

    

