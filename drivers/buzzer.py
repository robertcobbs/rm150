# Copyright (C) 2014 Synapse Wireless, Inc.
"""Buzzer related functions for the remote monitor"""

from hw_defs import *
from atmega128rfa1_timers import *

def init_buzzer():
    setPinDir(BUZZER, True)  # set to output
    writePin(BUZZER, False)

def _set_buzzer_freq(freq, enable):
    """Set the buzzer to a frequency"""
    # gotta do some funky math since our base clock freqency is
    # 16,000,000 / 64 = 250Khz
    icr = 31250 / freq
    icr *= 8
    rem = 31250 % freq
    trim = rem * 8
    trim /= freq
    icr += trim
    #print "ICR = "+str(icr)
    timer_init(TMR3, WGM_FASTPWM16_TOP_ICR, CLK_FOSC_DIV64, icr)
    set_tmr_count(TMR3, 0)
    set_tmr_ocr(TMR3, OCRxB, icr>>1)  # Set B output duty cycle to 1/2
    if enable:
        _set_buzzer_state(True)

def _set_buzzer_state(enabled):
    if enabled:
        set_tmr_output(TMR3, OCRxB, TMR_OUTP_CLR)  # Enable PWM on pin
    else:
        set_tmr_output(TMR3, OCRxB, TMR_OUTP_OFF)  # Restore pin to regular I/O
