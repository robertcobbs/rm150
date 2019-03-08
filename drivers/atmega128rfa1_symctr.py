# (c) Copyright 2011-2013, Synapse Wireless, Inc.
"""
Utility functions for ATmega128RFA1 MAC Symbol Counter.
"""

def enable_sym_ctr():
    poke(0xdc, 0x30)  # Write sym-ctr control reg (SCCR0), enable and select RTC clock

def dump_sym_ctr():
    ll = peek(0xe1)
    lh = peek(0xe2)
    hl = peek(0xe3)
    hh = peek(0xe4)
    
    print "hh=", hh, ", hl=", hl, ", lh=", lh, ", ll=", ll

def zero_sym_ctr():
    poke(0xE4, 0)
    poke(0xE3, 0)
    poke(0xE2, 0)
    poke(0xE1, 0)  # writing the LSB last "strobes in" all 4 bytes

def sym_secs():
    """Return seconds elapsed since timer zeroed.  Valid for times up to 6553 secs (109 mins)"""
    # upper 16 bits is 65535/62.5 = 1049ms per count
    ll = peek(0xe1)
    h16 = peek(0xe4) << 8 | peek(0xe3)
    return h16 + (h16 * 5) / 100 + 1

def sym_msecs():
    """Return milliseconds elapsed since timer zeroed.  Valid for times up to 1049 ms"""
    # lower 16 bits is 1/62500 = 16us per count
    ll = peek(0xe1)
    l16 = peek(0xe2) << 8 | ll
    return l16 / 63 if l16 >= 0 else 512 + (0x7FFF + l16) / 63

def sym_ticks_16us():
    """Return 16-bit tick count in 16us increments. Rolls every 1.048 seconds."""
    return peek(0xe1) | (peek(0xe2) << 8)

def sym_ticks_4ms():
    """Return 16-bit tick count in 4.096ms increments. Rolls every 268 seconds."""
    peek(0xe1)  # Reading LSB latches in counter value
    return peek(0xe2) | (peek(0xe3) << 8)
