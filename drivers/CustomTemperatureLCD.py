# Copyright (C) 2014 Synapse Wireless, Inc.
"""Definition of Custom passive Sensor LCD interface with XMEGA"""
###############################################################################################
###############################################################################################
########                     CONSTANTS                                           ##############
###############################################################################################
###############################################################################################
ICON_STATE_OFF = 0
ICON_STATE_ON = 1
ICON_STATE_BLINK = 2

UNITS_F = 0
UNITS_C = 1

LIMITS_OFF = 0
LIMITS_LOW = 1
LIMITS_OK = 2
LIMITS_HIGH = 3

CMD_UPDATE_DISPLAY = "D"
CMD_COMSEG = "C"
CMD_TEST = "T"
CMD_ACK = "A"
CMD_NACK = "N"
CMD_VERSION = "V"

###############################################################################################
###############################################################################################
########                     Global Temperature Variables                        ##############
###############################################################################################
###############################################################################################
Alert = ICON_STATE_OFF
Battery = 0
Signal = 0
Units = UNITS_C

T_amb_limits = LIMITS_OFF
RH_limits = LIMITS_OFF
T_ext1_limits = LIMITS_OFF
T_ext2_limits = LIMITS_OFF

T_amb = 0
RH = 0
T_ext1 = 0
T_ext2 = 0

updateDisplayCallback = None

DISABLE_VALUE = 10000
ERR_VALUE = 10001  # "Err "
DASH_VALUE = 10002  # "----"
OPEN_VALUE = 10003  # "OPEn"
HUMID_DISABLE_VALUE = 255
NO_UPDATE = 10004
DOOR_OPEN = 10005
DOOR_CLOSED = 10006


###############################################################################################
###############################################################################################
########                     Global Transmit Constants                           ##############
###############################################################################################
###############################################################################################
UCSR0A = 0xC0
UCSR0B = 0xC1
UDR0   = 0xC6

UCSR1A = 0xC8
UCSR1B = 0xC9
UDR1 = 0xCE

TXCIE = 0b01000000
TXC   = 0b01000000
UDRE  = 0b00100000

###############################################################################################
###############################################################################################
########                     Transmit Methods                                    ##############
###############################################################################################
###############################################################################################


def tx_uart0(string):
    """Takes a SNAPpy string and transmits it out UART0"""
    status = peek(UCSR0B)
    # disable TX complete interrupt
    status &= ~TXCIE
    poke(UCSR0B, status)

    i = 0
    str_len = len(string)
    while i < str_len:
        # Wait for empty transmit buffer
        while not (peek(UCSR0A) & UDRE):
            pass

        poke(UDR0, ord(string[i]))
        i += 1

    poke(UCSR0A, peek(UCSR0A) | TXC)  # clear any pending interrupt
    poke(UCSR0B, peek(UCSR0B) | TXCIE)  # enable the ISR


def command_port_send(type, length, value):
    global testCmd
    
    #the XMEGA needs time to wake up...we should send a bunch of zeros
    # until it wakes up.  The zeros will be discarded on the xmega side
    #cmd = chr(type) + chr(length) + value
    testCmd = "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" + chr(type) + chr(length) + value
    tx_uart0(testCmd)


###############################################################################################
###############################################################################################
########                     SET Methods                                         ##############
###############################################################################################
###############################################################################################
def CTLCD_set_Alert(value):
    global Alert
    Alert = value

def CTLCD_set_Battery(value):
    global Battery
    Battery = value
    
def CTLCD_set_Signal(value):
    global Signal
    Signal = value

def CTLCD_set_Units(value):
    global Units 
    Units = value

def CTLCD_set_T_amb(value):
    global T_amb
    T_amb = value

def CTLCD_set_T_amb_limits(value):
    global T_amb_limits    
    T_amb_limits = value
    
def CTLCD_set_T_ext1(value):
    global T_ext1
    T_ext1 = value

def CTLCD_set_T_ext1_limits(value):
    global T_ext1_limits
    T_ext1_limits = value
    
def CTLCD_set_T_ext2(value):
    global T_ext2
    T_ext2 = value
    
def CTLCD_set_T_ext2_limits(value):
    global T_ext2_limits
    T_ext2_limits = value

def CTLCD_set_RH(value):
    global RH
    RH = value

def CTLCD_set_RH_limits(value):
    global RH_limits
    RH_limits = value

###############################################################################################
###############################################################################################
########                     Conversion Methods                                  ##############
###############################################################################################
###############################################################################################
def convBatmonToLcd(value):
    if value >= 1700 and value < 2000:
        return 0
    elif value >= 2000 and value < 2250:
        return 1
    elif value >= 2250 and value < 2775:
        return 2;
    elif value >= 2775:
        return 3;
    
def convSignalToLcd(value):
    #this is supposed to be in negative dB but there is no minus
    value = -value
    
    if value < -85:
        return 0
    elif value >= -85 and value < -75:
        return 1
    elif value >= -75 and value < -65:
        return 2
    elif value >= -65 and value < -55:
        return 3
    elif value >= -55:
        return 4
###############################################################################################
###############################################################################################
########                     Display Update Methods                              ##############
###############################################################################################
###############################################################################################


###############################################################################################
###############################################################################################
########                     Bit/Byte packing positions                          ##############
###############################################################################################
###############################################################################################
#     |----------------------------------------------------------------------------------------
#     |     7    |    6     |    5     |   4      |   3      |   2      |    1     |   0      |
#-----|---------------------|--------------------------------|---------------------|----------|
# B0  |       ALERT         |           signal (ANT)         |      Battery        |  Units   |
#-----|---------------------------------------------------------------------------------------|
# B1  |   Limits Ambient    |    Limits Rel Hum   |     Limits T1       |     Limits T2       |
#-----|---------------------------------------------------------------------------------------|
# B2  |                                Temp Amb [15:8]                                        |
#-----|---------------------------------------------------------------------------------------|
# B3  |                                Temp Amb [7:0]                                         |
#-----|---------------------------------------------------------------------------------------|
# B4  |                                rel Hum  [7:0]                                         |
#-----|---------------------------------------------------------------------------------------|
# B5  |                                Temp Ext1 [15:8]                                       |
#-----|---------------------------------------------------------------------------------------|
# B6  |                                Temp Ext1 [7:0]                                        |
#-----|---------------------------------------------------------------------------------------|
# B7  |                                Temp Ext2 [15:8]                                       |
#-----|---------------------------------------------------------------------------------------|
# B8  |                                Temp Ext2 [7:0]                                        |
#-----|---------------------------------------------------------------------------------------|
   
#builds a temperature command tlv string
def CTLCD_updateDisplay():
    """ build a tlv string from the variables in this file and update the display """
    global Alert, Signal, Battery, Units, T_amb, T_amb_limits
    global RH, RH_limits, T_ext1, T_ext1_limits, T_ext2, T_ext2_limits
    
    b0 = Alert << 6
    b0 |= (Signal & 0x7) << 3
    b0 |= (Battery & 0x3) << 1
    b0 |= (Units & 0x1)
    
    #printString = "A="+str(Alert)+" S="+str(Signal)+" B="+str(Battery)+" U="+str(Units)
    #mcastRpc(1, 2, 'rprint', printString)
    
    b1 = (T_amb_limits & 0x3) << 6
    b1 |= (RH_limits & 0x3) << 4
    b1 |= (T_ext1_limits & 0x3) << 2
    b1 |= (T_ext2_limits & 0x3)
    
    b2 = T_amb >> 8
    b3 = T_amb & 0xFF
    
    b4 = RH & 0xFF
    
    b5 = T_ext1 >> 8
    b6 = T_ext1 & 0xFF
    
    b7 = T_ext2 >> 8
    b8 = T_ext2 & 0xFF

    value = chr(b0) + chr(b1) + chr(b2) + chr(b3) + chr(b4) + chr(b5) + chr(b6) + chr(b7) + chr(b8)
    length = len(value)
    t = ord(CMD_UPDATE_DISPLAY) #display update
    command_port_send(t, length, value)

def CTLCD_set_comseg(com, seg, state):
    """ Set a single pixel on the display """
    value = chr(com) + chr(seg) + chr(state)
    length = len(value)
    t = ord(CMD_COMSEG) #com seg update
    command_port_send(t, length, value)

def CTLCD_show_ver(snappy_ver):
    """Display the current software version of the LCD driver"""
    command_port_send(ord(CMD_VERSION), 2, chr(snappy_ver >> 8) + chr(snappy_ver & 0xff))

###############################################################################################
###############################################################################################
########                     test functions                                      ##############
###############################################################################################
###############################################################################################
def test_GTLC_allSegOff():
    value = chr(ICON_STATE_OFF)
    length = len(value)
    t = ord(CMD_TEST) #test command
    command_port_send(t, length, value)
    
def test_GTLC_allSegOn():
    value = chr(ICON_STATE_ON)
    length = len(value)
    t = ord(CMD_TEST) #test command
    command_port_send(t, length, value)

def test_GTLC_allSegInit():
    value = chr(2)
    length = len(value)
    t = ord(CMD_TEST) #test command
    command_port_send(t, length, value)
