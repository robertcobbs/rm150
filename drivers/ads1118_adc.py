# Copyright (C) 2014 Synapse Wireless, Inc.
"""ADS1118 Driver - SPI 16-bit ADC
  Assumes SPI already initialized:
    spiInit(False, False, True, True)  # clk idle low, DIN on falling-edge, MSB first, 4-wire
"""

from hw_defs import ADS1118_CS

# Defs for ads_config (channel, range, rate, mode)
ADS_CH1 = 0x0000       # AINP is AIN0 and AINN is AIN1
ADS_CH2 = 0x3000       # AINP is AIN2 and AINN is AIN3
ADS_RNG_6144 = 0x0000  # Full scale range is +- 6144mV
ADS_RNG_4096 = 0x0200
ADS_RNG_2048 = 0x0400
ADS_RNG_1024 = 0x0600
ADS_RNG_512  = 0x0800
ADS_RNG_256  = 0x0a00
ADS_RATE_8   = 0x0000  # 8 samples per second (SPS)
ADS_RATE_16  = 0x0020
ADS_RATE_32  = 0x0040
ADS_RATE_64  = 0x0060
ADS_RATE_128 = 0x0080
ADS_RATE_250 = 0x00a0
ADS_RATE_475 = 0x00c0
ADS_RATE_860 = 0x00e0
ADS_MODE_ADC = 0x0000
ADS_MODE_TMP = 0x0010  # Temperature data
ADS_IS_DATA  = 0x0002  # Valid config data, not NOP

ADS_SNG_SHOT = 0x0100  # Single shot - one conversion then sleep
ADS_SLEEP    = 0x0100  # Aka "single shot" (SS) mode
ADS_SS_START = 0x8000  # Start conversion on read() when powered down (data available next read after conversion)

ads_config_i16 = ADS_SS_START | ADS_CH1 | ADS_RNG_256 | ADS_RATE_16 | ADS_MODE_ADC | ADS_IS_DATA
ads_config_str = "%c%c" % (ads_config_i16 >> 8, ads_config_i16 & 0xff)


def ads_read():
    """Transfer new config, and return most recent 16-bit conversion result"""
    writePin(ADS1118_CS, False)
    s = spiXfer(ads_config_str)
    writePin(ADS1118_CS, True)
    return ord(s[0]) << 8 | ord(s[1])

def ads_config_mask(mask):
    """Set configuration string, applied on next read()"""
    global ads_config_i16
    ads_config_i16 = mask | ADS_IS_DATA
    ads_make_cfg_str()
    
def ads_make_cfg_str():
    global ads_config_str
    ads_config_str = chr(ads_config_i16 >> 8) + chr(ads_config_i16 & 0x00FF)

def ads_sleep(do_sleep):
    """Enter sleep (2uA) or wake to 'continuous conversion' (250uA) mode.
       Note:
          Sleep also serves as "single shot" mode. Each 'read()' operation triggers a conversion (unless one
          is already in progress), and returns the result of last conversion.
    """
    global ads_config_i16
    if do_sleep:
        ads_config_i16 |= ADS_SLEEP
    else:
        ads_config_i16 &= ~ADS_SLEEP
        
    ads_make_cfg_str()
    ads_read()

def ads_config_internal_temp():
    """Configure for internal temperature sensor"""
    ads_config_mask(ADS_CH1 | ADS_RNG_256 | ADS_RATE_16 | ADS_MODE_TMP | ADS_SNG_SHOT | ADS_SS_START)

def ads_config_ch1_hirez():
    """Configure to measure hi resolution mV source, e.g. K-type thermocouple"""
    ads_config_mask(ADS_CH1 | ADS_RNG_256 | ADS_RATE_16 | ADS_MODE_ADC | ADS_SNG_SHOT | ADS_SS_START)
    
def ads_conv_internal_temp_C(a2d_value):
    """Return tenths of deg C"""
    t = ((a2d_value >> 2) * 10) / 32
    return t

def ads_wait_conversion():
    """Block waiting for conversion complete; DOUT/DRDY will go low"""
    timeout = 2000
    writePin(ADS1118_CS, False)
    while(readPin(SPI_MISO) == 1) and (timeout > 0):
        timeout -= 1
    if timeout == 0:
        print "ADC READ Timeout=", timeout
    writePin(ADS1118_CS, True)

def ads_blocking_internal_temp():
    ads_config_internal_temp()
    val = ads_blocking_read()
    return ads_conv_internal_temp_C(val)

def ads_blocking_read():
    """Initiate and return a new 16-bit conversion result"""
    # Ensure prior conversion is complete
    ads_wait_conversion()
    # Initiate conversion, while transfering current configuration to ADS
    ads_read()
    ads_wait_conversion()
    return ads_read()
