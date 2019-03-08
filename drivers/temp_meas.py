# Copyright (C) 2014 Synapse Wireless, Inc.
"""Temperature measurement using the ADS1118.
   Async interface uses 1/16s sample rate, which gives good accuracy with 62.5ms sample time,
   which fits nicely with 100ms timing between steps.
   Provide blocking interface for test purposes.
"""

from ads1118_adc import *
from thermocouple import *

TEMP_ADC_SAMP_MS = 70   # ms to allow ADC to convert

# C to F conversion function
conv_func = '\x38\x2e\xf9\x01\x39\x97\x50\x85\x80\xe0\x47\x81\x55\x23\x0a\xf4\x81\xe0\x65\x2f\x66\x0f\x66\x0b\x76\x2f\x80\xfb\x3e\xf4\x50\x95\x60\x95\x70\x95\x41\x95\x5f\x4f\x6f\x4f\x7f\x4f\x09\xe0\x22\x24\x07\x9f\x30\x2d\x06\x9f\x20\x2d\x31\x0d\x05\x9f\x10\x2d\x21\x0d\x32\x1d\x04\x9f\x11\x0d\x22\x1d\x32\x1d\x40\x2d\x51\x2f\xb9\x01\x36\x95\x27\x95\x17\x95\x07\x94\x04\x0e\x51\x1f\x62\x1f\x73\x1f\x76\x95\x67\x95\x57\x95\x07\x94\x40\x2d\x15\x2f\x9b\x01\x36\x95\x27\x95\x17\x95\x07\x94\x36\x95\x27\x95\x17\x95\x07\x94\x36\x95\x27\x95\x17\x95\x07\x94\x36\x95\x27\x95\x17\x95\x07\x94\x40\x0d\x51\x1f\x62\x1f\x73\x1f\x05\x2f\x16\x2f\x27\x2f\x04\x0f\x15\x1f\x26\x1f\x27\x1e\x26\x94\x27\x95\x17\x95\x07\x95\x26\x94\x27\x95\x17\x95\x07\x95\xa8\x01\x1e\xf4\x51\x95\x41\x95\x50\x40\x52\x83\x41\x83\x01\xe0\x00\x83\x83\x2d\x08\x95'


def temp_read_step1():
    """Setup step: Initiate internal "cold junction" measurement"""
    # Transfer config for internal temp meas, start conversion
    ads_config_mask(ADS_CH1 | ADS_RNG_256 | ADS_RATE_16 | ADS_MODE_TMP | ADS_SNG_SHOT | ADS_SS_START)
    ads_read()

def temp_read_step2(offset):
    """Intermediate step: Store cold junction temperature as a corresponding ADC count based on k-table
       Returns cold junction temperature (ambient at probe connector) in tenths C.
    """
    global cold_count
    
    # Set config for external ADC
    ads_config_mask(ADS_CH1 | ADS_RNG_256 | ADS_RATE_16 | ADS_MODE_ADC | ADS_SNG_SHOT | ADS_SS_START)
    
    # Get internal temp conversion result, and start conversion of external ADC
    cold_tmp = ads_conv_internal_temp_C(ads_read())
    cold_tmp = cold_tmp + offset
    cold_count = C_to_adc(cold_tmp)
    #print "cold temp=", cold_tmp, ", cnt=", cold_count
    return cold_tmp
    
def temp_read_step3(offset):
    """Final step, returns temperature in tenths C
       Read thermocouple ADC count, compensate for cold junction offset, and convert to tenths C.
    """
    therm_count = ads_read()
    #print "therm count=", therm_count
    therm_compens = therm_count + cold_count
    tmp = adc_to_C(therm_compens)
    
    # if tmp at max/min rail don't add offset - the rail values are used to indicate an error
    if tmp < MAX_TEMP * 10 and tmp > MIN_TEMP * 10:
        tmp = tmp + offset
        
    return tmp

def c_to_f(tempr):
    """
    Converts Celsius to Fahrenheit
    For atmel only
    """
    return (call(conv_func, tempr) + 320)
