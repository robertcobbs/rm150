# Copyright (C) 2014 Synapse Wireless, Inc.
"""Hardware definitions - Synapse Handheld Probe
   Fully describes the hardware environment of the current running SNAPpy image.
"""


# SM200 serial IO
I2C_SDA  = 30
I2C_SCL  = 31

SPI_CLK = 26
SPI_MOSI = 25
SPI_MISO = 18

UART0_RX = 16
UART0_TX = 17

UART1_RX = 10
UART1_TX = 11

# Thermocouple ADC ADS1118RUG, SPI
# SPI: clk idle low, latch DIN on falling edge, latch DOUT on rising
ADS1118_CS1 = 28  # active low
ADS1118_CS2 = 0  # active low
ADS1118_CS = ADS1118_CS1  # Can be changed with a call to selectADC_CS

# Debug LEDs (active low)
DBG_LED_RED = 19
DBG_LED_GRN = 14

# xmega64B1 reset
XMEGA_RESET = 8  # low to reset

XMEGA_WAKE = 9

# onboard flash chip
FLASH_CS = 13   # active low

# momentary push button on front of device
PB_SWITCH = 23  # active high
PB_SWITCH_NEW = 1  # new PB Switch


BUZZER = 20  # PWM to change volume, can change frequency to generate melody.


def init_snap_hw():
   # SM200 serial IO
   uniConnect(DS_STDIO, DS_UART0)   # stdin <- uart0
   initUart(0, 1)   # 115.2k to XMEGA
   flowControl(0, False)
   uniConnect(DS_STDIO, DS_UART1)   # stdin <- uart1
   initUart(1, 1)   # 115.2k to debug J1
   stdinMode(1, False)      # Character Mode, Echo Off

   i2cInit(False)
   spiInit(False, False, True, True)  # clk idle low, DIN on falling-edge, MSB first, 4-wire
   #changed to this so that ADS1118 and Flash can co-exists without multiple calls to spiInit

   # Front side push Button
   setPinDir(PB_SWITCH_NEW, False) # input
   #monitorPin(PB_SWITCH_NEW, True)

   # Buzzer
   writePin(BUZZER, False) # set to false
   setPinDir(BUZZER, True) # set to output

   # Thermocouple ADC ADS1118RUG, SPI
   writePin(ADS1118_CS1, True)   # deselect
   setPinDir(ADS1118_CS1, True)  # output

   # Thermocouple ADC ADS1118RUG, SPI
   writePin(ADS1118_CS2, True)   # deselect
   setPinDir(ADS1118_CS2, True)  # output

   # Debug LEDs
   setPinDir(DBG_LED_RED, True) # deselect
   writePin(DBG_LED_RED, True)  # output
   setPinDir(DBG_LED_GRN, True) # deselect
   writePin(DBG_LED_GRN, True)  # output

   # Flash Chip Select
   writePin(FLASH_CS, True)   # deselect
   setPinDir(FLASH_CS, True)  # output

   # XMEGA
   writePin(XMEGA_RESET, False) # deselect
   setPinDir(XMEGA_RESET, False)   # Set as input we don't want to drive the pin unless we need to

   writePin(XMEGA_RESET, True) # deselect

   setPinDir(XMEGA_WAKE, False)  # TODO: set as output and start waking up the XMEGA

def init_pins_low_power():
   i = 0
   while i < 37:
      # Default all pins to output low
      setPinDir(i, True)
      writePin(i, False)
      i = i + 1
