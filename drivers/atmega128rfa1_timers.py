# (c) Copyright 2011-2013, Synapse Wireless, Inc.
"""ATmega128RFA1 timer support
Currently covers setup for basic timing and PWM operation.
Note: Timer4 is used as SNAP's 1ms timer, and Timer5 is used by some sleep modes.

Ex.
  #Setup timer1 as 2MHz free-running counter (assumes 16MHz system clock)
  timer_init(TMR1, WGM_NORMAL, CLK_FOSC_DIV8, 0)

Ex.
  #Setup OC3C for 8-bit PWM at 2MHz, 50% duty cycle
  timer_init(TMR3, WGM_FASTPWM8, CLK_FOSC_DIV8, 0)
  set_tmr_ocr(TMR3, OCRxC, 127)  # Set C output duty cycle (127/255)
  set_tmr_output(TMR3, OCRxC, TMR_OUTP_CLR)  # Enable PWM on pin
  # ...
  set_tmr_output(TMR3, OCRxC, TMR_OUTP_OFF)  # Restore pin to regular I/O

"""

# Base address for Timers
TMR1 = 0x80
TMR3 = 0x90
TMR4 = 0xA0
TMR5 = 0x120

# ATmega128RFA1 Timer register offsets
TCCRxA = 0x00  # Timer/Counter Control Register  A
TCCRxB = 0x01  # Timer/Counter Control Register  B
TCCRxC = 0x02  # Timer/Counter Control Register  C
TCNTx  = 0x04  # Timer/Counter Low Order Byte (+1 for High Byte)
ICRx  = 0x06   # Input Capture Registers Low Order Byte (+1 for High Byte)
OCRxA = 0x08   # Output Compare Registers A Low Order Byte (+1 for High Byte)
OCRxB = 0x0A   # Output Compare Registers B Low Order Byte (+1 for High Byte)
OCRxC = 0x0C   # Output Compare Registers C Low Order Byte (+1 for High Byte)

# Compare Output Modes (COM)
TMR_OUTP_OFF = 0
TMR_OUTP_TGL = 1
TMR_OUTP_CLR = 2
TMR_OUTP_SET = 3

# Common Waveform Generation Modes
WGM_NORMAL = 0
WGM_FASTPWM8 = 5
WGM_FASTPWM16_TOP_ICR = 14
WGM_FASTPWM16_TOP_OCR = 15

# Clock Select
CLK_FOSC = 1
CLK_FOSC_DIV8 = 2
CLK_FOSC_DIV64 = 3
CLK_FOSC_DIV256 = 4
CLK_FOSC_DIV1024 = 5
CLK_EXT_FALLING = 6
CLK_EXT_RISING = 7

def set_tmr_ocr(tmr, ocr, val):
    """Set OCR register. This controls the duty cycle (duty/TOP) in some PWM modes"""
    poke(tmr + ocr + 1, (val >> 8) & 0xFF)  # high byte
    poke(tmr + ocr, val & 0xff) # low byte
    
def set_tmr_output(tmr, ocr, mode):
    """Set output mode"""
    shift = 14 - ocr
    mask = ~(0x03 << shift)
    val = peek(tmr)
    val = (val & mask) | (mode << shift)
    poke(tmr, val)
    
def get_tmr_count(tmr):
    """Read immediate count value"""
    return peek(tmr + TCNTx) | (peek(tmr + TCNTx + 1) << 8)

def set_tmr_count(tmr, count):
    """Set immediate count value"""
    poke(tmr + TCNTx + 1, (count >> 8) & 0xFF)  # high byte
    poke(tmr + TCNTx, count & 0xff) # low byte
    
def timer_init(tmr, wgm_mode, clk_sel, icr):
    """Initialize waveform generation mode, clock select, and input-capture"""
    # TCCRxA
    value = wgm_mode & 0x03  # Set COMxA/B/C = O (off), and LSBs of WGM
    poke(tmr + TCCRxA,value)

    # TCCRxB
    value = (wgm_mode & 0x0C) << 1
    value |= clk_sel & 0x07
    poke(tmr + TCCRxB,value)

    # ICRx
    poke(tmr + ICRx + 1, (icr >> 8) & 0xFF)  # high byte
    poke(tmr + ICRx, icr & 0xff) # low byte
    
