# Copyright (C) 2014 Synapse Wireless, Inc.
"""Main file for RM150"""
# TODO:
# 1. Add audio alert option

from synapse.switchboard import *
from synapse.platforms import *
from synapse.nvparams import *

# Allow common/driver code cross-project access to 'hw_defs' module
import sys

from drivers.hw_defs import *

from drivers.CustomTemperatureLCD import *
from drivers.buzzer import *

from drivers.ads1118_adc import *
from drivers.AT45DB import *
from drivers.batmon import *
from drivers.atmega128rfa1_symctr import sym_ticks_4ms
from drivers.thermocouple import *
from drivers.temp_meas import *
from drivers.buzzer import _set_buzzer_freq
from drivers.buzzer import _set_buzzer_state

from drivers.HIH61_Humidity import *

# Script Version
VERSION = 8

# CONFIGURATION
EXT_1_ENABLED = True
EXT_2_ENABLED = True
EXT_1_MONITORED_ITEM = 0  # 0 for Temp, 1 for Door Relay
EXT_2_MONITORED_ITEM = 0  # 0 for Temp, 1 for Door Relay

GW_COMM_MCAST_GROUP = 3
GW_COMM_MCAST_TTL = 5

OFFSET_EXTERNAL_1 = 0
OFFSET_EXTERNAL_2 = 0
OFFSET_AMBIENT_1 = 0
OFFSET_AMBIENT_2 = 0
OFFSET_HUMIDITY = 0

HAS_HUMIDITY_SENSOR = False

IN_FAHRENHEIT = True

REPORT_INTV = 60  # seconds
ALERT_INTV = 30  # seconds (time between buzzers)
INTERVAL_DELAY = 5   # seconds
LCD_UPDATE_INT = INTERVAL_DELAY * 1000  # milliseconds
STARTUP_WAIT = 5  # seconds

AMB_TEMP_HIGH = 9999  # decidegrees Celcius
AMB_TEMP_LOW = -999  # decidegrees Celcius
AMB_HUMID_HIGH = 9999
AMB_HUMID_LOW = -999
EXT_1_HIGH = 275  # decidegrees Celcius
EXT_1_LOW = -999  # decidegrees Celcius
EXT_2_HIGH = 9999  # decidegrees Celcius
EXT_2_LOW = -999  # decidegrees Celcius


# CONSTANTS
STATE_ALERT = 4
STATE_REPORT_RPC_QUEUED = 3  # Waiting for callback that 'report' rpc was sent
STATE_NORMAL = 2
STATE_STARTUP = 1

DOOR_OPEN_THRESHOLD = -900

# Initialize global variables
last_amb_temp = DISABLE_VALUE
last_amb_humid = HUMID_DISABLE_VALUE
last_ext1 = DISABLE_VALUE
last_ext2 = DISABLE_VALUE

current_interval = REPORT_INTV/INTERVAL_DELAY
alert_interval = ALERT_INTV/INTERVAL_DELAY

startup_cntr = 0
report_cntr = current_interval + 1  # Send status at startup
found_alert = False
alert_cntr = 0
audio_cntr = 0
in_audio = False

report_rpc_ref = None

door_1_open = False
door_2_open = False

current_state = STATE_STARTUP
silenced = False
link_quality = 0


@setHook(HOOK_STARTUP)
def start():
    # Disable PacketSerial on UART1
    crossConnect(DS_PACKET_SERIAL, DS_NULL)

    # Initialize SM200 hardware
    init_pins_low_power()
    init_snap_hw()
    init_buzzer()

    # Initialize the flash device
    init_AT45DB(FLASH_CS)

    # Initialize command port processor
    uniConnect(DS_STDIO, DS_UART0)   # stdin <- uart0
    initUart(0, 1)  # 115.2k
    uniConnect(DS_STDIO, DS_UART1)   # stdin <- uart1
    initUart(1, 1)  # 115.2k
    stdinMode(1, False)      # Character Mode, Echo Off

    _load_config()

    AT45DB_udeep(True)

    CTLCD_set_RH(STARTUP_WAIT)
    CTLCD_set_T_amb(DISABLE_VALUE)
    CTLCD_set_T_ext1(NO_UPDATE)
    CTLCD_set_T_ext2(NO_UPDATE)
    CTLCD_updateDisplay()
    CTLCD_show_ver(VERSION)


def run_fsm():
    global report_cntr, current_state, found_alert, alert_cntr, alert_interval, in_audio, audio_cntr
    
    while current_state == STATE_NORMAL and not in_audio:
        sleep(2, -LCD_UPDATE_INT)

        # check button
        if readPin(PB_SWITCH_NEW):
            button_event(True)
        else:
            button_event(False)

        report_cntr += 1
        read_temps()
        _update_lcd_batt()
        _update_lcd_signal(link_quality)
        CTLCD_updateDisplay()

        if report_cntr >= current_interval:
            send_report()
            return

        if found_alert:
            alert_cntr += 1
            found_alert = False
            CTLCD_set_Alert(ICON_STATE_BLINK)
            CTLCD_updateDisplay()
            if alert_cntr >= alert_interval:
                in_audio = True
                send_report()
        elif not found_alert:
            CTLCD_set_Alert(ICON_STATE_OFF)
            CTLCD_updateDisplay()
            in_audio = False
        
    if in_audio:
        if audio_cntr == 0:
            _set_buzzer_freq(500, True)
        elif audio_cntr == 250:
            _set_buzzer_freq(250, True)
        elif audio_cntr >= 500:
            _set_buzzer_state(False)
            in_audio = False
            alert_cntr = 0
        audio_cntr += 1


def send_report():
    global current_state, report_rpc_ref, report_cntr
    mcastRpc(GW_COMM_MCAST_GROUP, GW_COMM_MCAST_TTL, "rm150_rpt", localAddr(), REPORT_INTV, last_amb_temp, last_amb_humid, last_ext1, last_ext2)
    report_rpc_ref = getInfo(9)
    current_state = STATE_REPORT_RPC_QUEUED


@setHook(HOOK_RPC_SENT)
def on_rpc_sent(ref):
    global report_rpc_ref, current_state, report_cntr
    if ref == report_rpc_ref:
        report_rpc_ref = None
        report_cntr = 0
        current_state = STATE_NORMAL


@setHook(HOOK_GPIN)
def button_event(is_set):
    global silenced, remote_test

    if is_set:
        if not silenced:
            CTLCD_set_Alert(ICON_STATE_ON)
            silenced = True


def _load_config():
    global IN_FAHRENHEIT
    
    # Display Configurations
    if IN_FAHRENHEIT:
        CTLCD_set_Units(UNITS_F)
    else:
        CTLCD_set_Units(UNITS_C)
    
    set_ext_probe(1, EXT_1_ENABLED)
    set_ext_probe(2, EXT_2_ENABLED)


def read_temps():
    """
    Read the temps/humidity from enabled sensors and update displays
    """
    global report_cntr, current_interval, last_amb_temp, last_ext1, last_ext2, silenced, last_amb_humid, found_alert, door_1_open, door_2_open
    
    if HAS_HUMIDITY_SENSOR:
        HIH61_start_conversion()

    selectADC_CS(ADS1118_CS1)
    temp_read_step1()  # ext probe 1

    sleep(2, -TEMP_ADC_SAMP_MS)

    tempr = temp_read_step2(OFFSET_AMBIENT_1)  # ext probe 1

    if True: #tempr != HTU32_ERR_VAL:
        last_amb_temp = tempr
        if last_amb_temp < AMB_TEMP_LOW:
            CTLCD_set_T_amb_limits(LIMITS_LOW)
            found_alert = True
        elif last_amb_temp > AMB_TEMP_HIGH:
            CTLCD_set_T_amb_limits(LIMITS_HIGH)
            found_alert = True
        else:
            CTLCD_set_T_amb_limits(LIMITS_OK)
        if IN_FAHRENHEIT:
            tempr = c_to_f(tempr)
        CTLCD_set_T_amb(tempr)

    if EXT_1_ENABLED:
        sleep(2, -TEMP_ADC_SAMP_MS)

        tempr = last_ext1 = temp_read_step3(OFFSET_EXTERNAL_1)  # ext probe 1

        if EXT_1_MONITORED_ITEM == 1:
            # Attached to a door sensor
            if tempr < DOOR_OPEN_THRESHOLD:
                CTLCD_set_T_ext1(DOOR_OPEN)
                last_ext1 = 1
                if not door_1_open:
                    door_1_open = True
                    report_cntr = current_interval + 1  # Send a update on change
            else:
                CTLCD_set_T_ext1(DOOR_CLOSED)
                last_ext1 = 0
                if door_1_open:
                    door_1_open = False
                    report_cntr = current_interval + 1  # Send a update on change
        else:
            if last_ext1 < EXT_1_LOW:
                CTLCD_set_T_ext1_limits(LIMITS_LOW)
                found_alert = True
            elif last_ext1 > EXT_1_HIGH:
                CTLCD_set_T_ext1_limits(LIMITS_HIGH)
                found_alert = True
            else:
                CTLCD_set_T_ext1_limits(LIMITS_OK)
            if tempr >= MAX_TEMP * 10 or tempr <= MIN_TEMP * 10:
                tempr = ERR_VALUE
            elif IN_FAHRENHEIT:
                tempr = c_to_f(tempr)
            CTLCD_set_T_ext1(tempr)

    if EXT_2_ENABLED:
        selectADC_CS(ADS1118_CS2)
        temp_read_step1()  # ext probe 2

    sleep(2, -TEMP_ADC_SAMP_MS)

    if HAS_HUMIDITY_SENSOR:
        tempr = HIH61_get_humid(OFFSET_HUMIDITY)
        last_amb_humid = tempr
        # currently not displaying Humidity, only reporting it
        if False:
            if last_amb_humid < AMB_HUMID_LOW:
                CTLCD_set_RH_limits(LIMITS_LOW)
                found_alert = True
            elif last_amb_humid > AMB_HUMID_HIGH:
                CTLCD_set_RH_limits(LIMITS_HIGH)
                found_alert = True
            else:
                CTLCD_set_RH_limits(LIMITS_OK)
            CTLCD_set_RH(last_amb_humid)

    if EXT_2_ENABLED:
        temp_read_step2(OFFSET_AMBIENT_2)  # ext probe 2

        sleep(2, -TEMP_ADC_SAMP_MS)

        tempr = last_ext2 = temp_read_step3(OFFSET_EXTERNAL_2)  # ext probe 2

        if EXT_2_MONITORED_ITEM == 1:
            # Attached to a door sensor
            if tempr < DOOR_OPEN_THRESHOLD:
                CTLCD_set_T_ext2(DOOR_OPEN)
                last_ext2 = 1
                if not door_2_open:
                    door_2_open = True
                    report_cntr = current_interval + 1  # Send a update on change
            else:
                CTLCD_set_T_ext2(DOOR_CLOSED)
                last_ext2 = 0
                if door_2_open:
                    door_2_open = False
                    report_cntr = current_interval + 1  # Send a update on change
        else:
            if last_ext2 < EXT_2_LOW:
                CTLCD_set_T_ext2_limits(LIMITS_LOW)
                found_alert = True
            elif last_ext2 > EXT_2_HIGH:
                CTLCD_set_T_ext2_limits(LIMITS_HIGH)
                found_alert = True
            else:
                CTLCD_set_T_ext2_limits(LIMITS_OK)
            if tempr >= MAX_TEMP * 10 or tempr <= MIN_TEMP * 10:
                tempr = ERR_VALUE
            elif IN_FAHRENHEIT:
                tempr = c_to_f(tempr)
            CTLCD_set_T_ext2(tempr)


@setHook(HOOK_1S)
def on_1s(ms):
    global startup_cntr, current_state

    if current_state == STATE_STARTUP:

        if not (readPin(PB_SWITCH_NEW) or readPin(PB_SWITCH)):
            startup_cntr += 1

        if startup_cntr > STARTUP_WAIT:
            current_state = STATE_NORMAL
            rx(False)
            CTLCD_set_RH(last_amb_humid)
            CTLCD_set_T_amb(last_amb_temp)
            CTLCD_set_T_ext1(last_ext1)
            CTLCD_set_T_ext2(last_ext2)
        else:
            pulsePin(DBG_LED_RED, 250, False)
            CTLCD_set_RH(STARTUP_WAIT-startup_cntr)
        CTLCD_updateDisplay()


@setHook(HOOK_1MS)
def on_1ms(ms):
    run_fsm()


def set_ext_probe(which, enable):
    if which == 1:
        if not enable:
            CTLCD_set_T_ext1(DISABLE_VALUE)
    elif which == 2:
        if not enable:
            CTLCD_set_T_ext2(DISABLE_VALUE)


def _update_lcd_batt():
    CTLCD_set_Battery(convBatmonToLcd(batmon_mv()))


def _update_lcd_signal(lq):
    CTLCD_set_Signal(convSignalToLcd(lq))


def selectADC_CS(cs_pin):
    global ADS1118_CS
    ADS1118_CS = cs_pin
