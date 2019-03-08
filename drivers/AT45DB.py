# Copyright (C) 2014 Synapse Wireless, Inc.


AT45DB_CS_PIN = None

ULTRA_DEEP_CMD = '\x79'
READ_LOW_POWER = '\x01'  # Continuous Array Read (Low Power Mode)

AT45DB_PAGE_SIZE = 264
AT45DB_MAX_BYTES = 122
CLK_STRING = '\x00' * AT45DB_MAX_BYTES

AT45DB_sleeping = False
AT45DB_cache = ''
AT45DB_last_addr = -AT45DB_MAX_BYTES


def init_AT45DB(cs_pin):
    global AT45DB_CS_PIN

    AT45DB_CS_PIN = cs_pin
    setPinDir(cs_pin, True)
    writePin(cs_pin, True)

def _AT45DB_xfer(data):
    """
    Asserts the CS pin and does a SPI transfer
    """
    global AT45DB_cache

    writePin(AT45DB_CS_PIN, False)
    AT45DB_cache = spiXfer(data)
    writePin(AT45DB_CS_PIN, True)

    return AT45DB_cache

def AT45DB_udeep(enable):
    global AT45DB_sleeping
    """
    Ultra-Deep Power-Down Mode
    Buffer is not maintained
    """
    if enable and not AT45DB_sleeping:
        #if it's already alseep sending this command will wake it up
        #causing an extra 20uA draw.
        #lets make sure that if it's already asleep we don't send it any more commands
        #before we sleep again.
        _AT45DB_xfer(ULTRA_DEEP_CMD)  # 3uS max time till in ultra deep sleep
        already_udeep = True
    elif not enable:
        _AT45DB_xfer('\x00')  # Docs say send arbitrary command to wake
        already_udeep = False
        # 240 uS max time to wake

def AT45DB_lowpwr_read(address, num_bytes):
    """
    Expects a 3-byte address
    """
    global AT45DB_last_addr, AT45DB_cache

    addr_int = _addr_int(address)
    if address <= "\x00\xF6\xAD" and addr_int >= AT45DB_last_addr and (addr_int + num_bytes) <= (AT45DB_last_addr + AT45DB_MAX_BYTES):
        #print "CACHE HIT!!!"
        loc = 4 + (addr_int - AT45DB_last_addr)
        return AT45DB_cache[loc:loc + num_bytes]
    #mcastRpc(1, 2, "rprint", address)
    #print "normal path!!!"

    if (addr_int + num_bytes) <= 32767:
        AT45DB_last_addr = addr_int
    else:
        AT45DB_last_addr = -AT45DB_MAX_BYTES

    _AT45DB_xfer(READ_LOW_POWER + address + CLK_STRING[:AT45DB_MAX_BYTES])

    return AT45DB_cache[4:4 + num_bytes]

def _addr_int(location_bytes):
    """
    Converts a 3-byte location string to an integer
    """
    page_ofs = (ord(location_bytes[0]) << 8) + (ord(location_bytes[1]) & 0x7FE) >> 1
    return page_ofs * AT45DB_PAGE_SIZE + ((ord(location_bytes[1]) << 8) + ord(location_bytes[2]) & 0x1FF)
