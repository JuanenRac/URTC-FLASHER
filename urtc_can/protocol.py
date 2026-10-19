"""URTC CAN protocol: constants, tables and pure frame builders and parsers.

GENERATED from spec/can_protocol.json by tools/generate_constants.py - do not edit by hand.

Standard library only, so this file can also be copied on its own into a tool.
"""
# =============================================================================
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from __future__ import annotations

PROTOCOL_VERSION = 1
BYTE_ORDER = "big"

# --- constants ---
BITRATE = 0x7A120  # Fixed bus bitrate (bit/s)
STANDARD_ID_MAX = 0x7FF  # Highest standard 11-bit identifier
DLC_MAX = 8  # Classic CAN payload limit (bytes)
HARDWARE_ID_MAIN = 0x303CC01  # HardwareID of the tool-head board (STM32F303CCT6, revision 1)
HARDWARE_ID_SLAVE = 0x303CB01  # HardwareID of the expansion slave (STM32F303CBT6)
FLASH_PAGE_SIZE = 0x800  # Flash page of the bootloader (bytes)
HMAC_LENGTH = 0x20  # HMAC-SHA256 signature length (bytes)
HMAC_CHUNK_COUNT = 4  # Frames of 8 bytes that carry the signature
PATCH_UNKNOWN = 0xFF  # Patch value meaning not known
PATCH_FLAG = 0x80  # High byte of the minor field: a patch follows in bits 6..0
PATCH_MAX = 0x7F  # Highest patch that fits the minor field
PATCH_FLAG_ACCEPTS_IN_END_UPDATE = 1  # Flag of 0x7E9: the bootloader reads the patch from the end-of-update frame
SLAVE_VERSION_EXT_MARKER = 0xE1  # First byte of the slave extended version register; never a status code
SLAVE_I2C_ADDRESS = 0x42  # 7-bit address of the expansion slave on the link bus
TELEMETRY_PERIOD_MS = 0x96  # Period of automatic telemetry (ms)
WATCHDOG_MS = 0xFA  # Communication watchdog of heaters, laser, drill and UV (ms)
LAYER_FAN_WATCHDOG_MS = 0x3E8  # Communication watchdog of the layer fan (ms)
KEEPALIVE_INTERVAL_MS = 0x96  # Resend interval hosts use under every 250 ms watchdog (ms)
LAYER_FAN_KEEPALIVE_INTERVAL_MS = 0x190  # Resend interval hosts use under the layer fan watchdog (ms)
LED_OVERRIDE_HOLD_MS = 0x2710  # How long a 0x100 override holds (ms)
ACTIVITY_WINDOW_MS = 0x5DC  # A frame of any ID within this window turns the status LED blue (ms)
BOOT_SPLASH_MS = 0x1388  # Approximate boot splash window; movement commands are deferred (ms)
HEARTBEAT_PERIOD_MS = 0x3E8  # Bootloader heartbeat period (ms)
VERSION_QUERY_TIMEOUT_S = 1.5  # Reference timeout of a version query (s)
VERSION_PATCH_GRACE_MS = 0x12C  # Grace window for 0x7E9 after 0x7F9 (ms)
READBACK_PAGE_BYTES = 0x800  # Bytes per read-back page (bytes)
READBACK_ACK_TIMEOUT_MS = 0xBB8  # The bootloader gives up on a read-back page not acknowledged in this time (ms)
HOTEND_FAN_STALL_MS = 0xBB8  # Hotend fan at duty above 0 with 0 RPM for this long is a critical error (ms)
HEATER_SETPOINT_MAX_C = 0x1BD  # Highest heater setpoint the firmware accepts (soldering iron and hot air) (C)
NOZZLE_SETPOINT_MAX_C = 0x12C  # Highest nozzle setpoint the hosts offer (hard ceiling in the firmware: 310) (C)
AOI_STROBE_MAX_MS = 0x1F4  # Highest strobe period the hosts offer (ms)
WELD_PULSE_MAX_MS = 0x7D0  # Longest weld pulse; the firmware clamps to it (ms)
PASTE_PULSE_MAX_MS = 0xFF  # Longest paste-jetting pulse that fits the byte (ms)
THERMAL_CHUNK_BYTES = 0x20  # Bytes per thermal chunk (4 frames of 8) (bytes)
THERMAL_CHUNK_COUNT_MLX90640 = 0x30  # Chunks of a 32x24 frame (MLX90640 and MLX90642)
THERMAL_CHUNK_COUNT_MLX90641 = 0xC  # Chunks of a 16x12 frame (MLX90641)
BLACKBOX_CHUNK_COUNT = 0x16  # Chunks of the fault recorder record read by 0x1A8

# --- identifiers ---
CAN_ID_IMPACT_EVENT = 0x095  # Impact register (touch probe, maximum priority)
CAN_ID_GLOBAL_STATUS = 0x100  # Status LED, ring LED and OLED mode
CAN_ID_QUERY_ACTIVE_TOOL = 0x110  # Query the active tool and the quick state
CAN_ID_ACTIVE_TOOL_RESP = 0x111  # Active tool and quick state
CAN_ID_MOTION_CMD = 0x120  # Plain stepper move (direction and step count)
CAN_ID_SOLDER_SETPOINT = 0x130  # T12 setpoint temperature
CAN_ID_SOLDER_FEEDER_RESET = 0x131  # Reset the solder wire feeder position
CAN_ID_SOLDER_FEEDER_POS = 0x132  # Solder wire feeder position
CAN_ID_SOLDER_TELEMETRY = 0x135  # T12 temperature telemetry
CAN_ID_DRILL_CMD = 0x140  # Drill speed and direction
CAN_ID_VACUUM_TELEMETRY = 0x145  # Vacuum pickup telemetry
CAN_ID_DRILL_TELEMETRY = 0x147  # Drill RPM and endstop telemetry
CAN_ID_AOI_CMD = 0x150  # AOI ring light mode and strobe period
CAN_ID_AOI_TELEMETRY = 0x155  # AOI endstop telemetry
CAN_ID_LASER_CMD = 0x160  # Laser power and interlock
CAN_ID_LASER_TELEMETRY = 0x165  # Laser endstop telemetry
CAN_ID_PRINTER_THERMAL_MOTION = 0x170  # Nozzle setpoint and extruder motion
CAN_ID_PRINTER_LAYERFAN_CMD = 0x173  # Layer fan power
CAN_ID_PRINTER_HOTEND_TELEMETRY = 0x175  # Hotend temperature telemetry
CAN_ID_PRINTER_LAYERFAN_RPM = 0x177  # Layer fan RPM telemetry
CAN_ID_PRINTER_HOTENDFAN_CMD = 0x178  # Hotend fan power
CAN_ID_PRINTER_HOTENDFAN_RPM = 0x179  # Hotend fan RPM telemetry
CAN_ID_EXPANSION_SPI_REQ = 0x180  # Expansion SPI passthrough request
CAN_ID_EXPANSION_SPI_RESP = 0x181  # Expansion SPI passthrough response
CAN_ID_EXPANSION_DIAG0_REQ = 0x182  # Query the TMC_DIAG0 level
CAN_ID_EXPANSION_DIAG0_RESP = 0x183  # TMC_DIAG0 level
CAN_ID_FRAM_QUERY = 0x190  # Query the recovered persisted state
CAN_ID_FRAM_STATE_RESP = 0x191  # Recovered persisted state
CAN_ID_ERASE_FRAM = 0x192  # Erase the recovered persisted state
CAN_ID_SET_EXPANSION_TYPE = 0x1A0  # Set the expansion board type
CAN_ID_EXPANSION_TYPE_RESP = 0x1A1  # Expansion board type (query and response)
CAN_ID_SET_FREE_TOOL = 0x1A2  # Set the free tool configuration
CAN_ID_FREE_TOOL_CONFIG_RESP = 0x1A3  # Raw jumper reading and free tool configuration
CAN_ID_SET_DEVICE_SERIAL = 0x1A4  # Set the device serial number
CAN_ID_PERIPHERAL_INFO_RESP = 0x1A5  # Peripheral type and device serial
CAN_ID_SET_MLX_VARIANT = 0x1A6  # Set the MLX9064x sensor variant
CAN_ID_MLX_VARIANT_RESP = 0x1A7  # MLX9064x sensor variant (query and response)
CAN_ID_BLACKBOX_QUERY = 0x1A8  # Request one chunk of the fault recorder
CAN_ID_BLACKBOX_CHUNK = 0x1A9  # One chunk of the fault recorder
CAN_ID_THERMAL_STATS_QUERY = 0x1AA  # Query the lifetime thermal counters
CAN_ID_THERMAL_STATS_RESP = 0x1AB  # Lifetime thermal counters
CAN_ID_ELECTROMAGNET_CMD = 0x1B0  # Electromagnet coil
CAN_ID_SPOT_WELD_CMD = 0x1C0  # Spot welder timed pulse
CAN_ID_UV_CURING_CMD = 0x1D0  # UV curing LED duty
CAN_ID_HOTAIR_CMD = 0x1E0  # Hot-air nozzle setpoint and blower duty
CAN_ID_CRIMPING_CMD = 0x1F0  # Crimping actuator motor
CAN_ID_ULTRASONIC_WELD_CMD = 0x200  # Ultrasonic welder timed pulse
CAN_ID_SLAVE_ENTER_BOOTLOADER = 0x210  # Enter the expansion slave's bootloader
CAN_ID_SLAVE_START_UPDATE = 0x211  # Start the slave firmware update
CAN_ID_SLAVE_HMAC_CHUNK = 0x212  # Slave HMAC-SHA256 signature chunk
CAN_ID_SLAVE_DATA = 0x213  # Slave firmware data
CAN_ID_SLAVE_END_UPDATE = 0x214  # End the slave update and verify
CAN_ID_SLAVE_STATUS = 0x215  # Slave bootloader status
CAN_ID_SLAVE_PROGRESS = 0x216  # Slave update progress
CAN_ID_SLAVE_VERSION_RESP_1 = 0x217  # Slave bootloader version, part 1
CAN_ID_SLAVE_VERSION_RESP_2 = 0x218  # Slave bootloader version, part 2
CAN_ID_SLAVE_VERIFY_FAIL_REASON = 0x219  # Slave verify-fail reason
CAN_ID_SLAVE_REG_WRITE = 0x220  # Write a slave application register (generic)
CAN_ID_SLAVE_REG_READ = 0x221  # Read a slave application register (generic)
CAN_ID_PASTE_JETTING_CONFIG = 0x230  # Local PWM configuration
CAN_ID_PASTE_JETTING_PULSE = 0x231  # Local PWM pulse
CAN_ID_ADS1115_CONFIG = 0x240  # ADS1115 configuration
CAN_ID_ADS1115_TRIGGER = 0x241  # ADS1115 trigger a conversion
CAN_ID_ADS1115_RESULT = 0x242  # ADS1115 conversion result (query and response)
CAN_ID_FLYING_PROBE_BASIC = 0x243  # Basic-mode onboard ADC reading
CAN_ID_THERMAL_TRIGGER = 0x250  # Trigger a thermal capture
CAN_ID_THERMAL_STATUS = 0x251  # Thermal capture status (query and response)
CAN_ID_THERMAL_RAW_CHUNK_REQ = 0x252  # Request a raw pixel chunk
CAN_ID_THERMAL_RAW_CHUNK = 0x253  # Raw pixel chunk data
CAN_ID_THERMAL_CAL_CHUNK_REQ = 0x254  # Request a calibrated temperature chunk
CAN_ID_THERMAL_CAL_CHUNK = 0x255  # Calibrated temperature chunk data
CAN_ID_VERSION_PATCH_RESPONSE = 0x7E9  # Version patch response
CAN_ID_ENTER_BOOTLOADER = 0x7F0  # Enter the bootloader
CAN_ID_START_UPDATE = 0x7F1  # Start the firmware update
CAN_ID_DATA = 0x7F2  # Firmware data
CAN_ID_PAGE_ACK = 0x7F3  # Page written acknowledgement
CAN_ID_END_UPDATE = 0x7F4  # End the update and verify
CAN_ID_STATUS = 0x7F5  # Bootloader status
CAN_ID_HEARTBEAT = 0x7F6  # Bootloader heartbeat
CAN_ID_HMAC_CHUNK = 0x7F7  # HMAC-SHA256 signature chunk
CAN_ID_QUERY_VERSION = 0x7F8  # Query the version
CAN_ID_VERSION_RESPONSE = 0x7F9  # Version response
CAN_ID_BOOTLOADER_VERSION_RESPONSE = 0x7FA  # Bootloader's own version
CAN_ID_QUERY_ERROR_COUNTERS = 0x7FB  # Query the CAN error counters
CAN_ID_ERROR_COUNTERS_RESPONSE = 0x7FC  # CAN error counters
CAN_ID_AUTHORIZE_DOWNGRADE = 0x7FD  # Authorise a downgrade for the current update
CAN_ID_READBACK = 0x7FE  # Read back the installed application
CAN_ID_READBACK_PAGE_ACK = 0x7FF  # Read-back page acknowledgement

# --- enumerations ---
# Tool profile
TOOL_SOLDERING_IRON = 0x00
TOOL_PASTE_DISPENSER = 0x01
TOOL_LIQUID_DISPENSER = 0x02
TOOL_SCREWDRIVER = 0x03
TOOL_VACUUM_PICKUP = 0x04
TOOL_DRILL = 0x05
TOOL_GRIPPER_GIMBAL = 0x06
TOOL_GRIPPER_NEMA = 0x07
TOOL_AOI_INSPECTION = 0x08
TOOL_LASER_ENGRAVER = 0x09
TOOL_PRINTER_3D = 0x0A
TOOL_SCAN_PROBE = 0x0B
TOOL_SMT_PICKPLACE = 0x0C
TOOL_ELECTROMAGNET = 0x0D
TOOL_SPOT_WELDER = 0x0E
TOOL_CONFORMAL_COATING = 0x0F
TOOL_VACUUM_GRIPPER_LG = 0x10
TOOL_FLYING_PROBE = 0x11
TOOL_UV_CURING = 0x12
TOOL_HOTAIR_REWORK = 0x13
TOOL_PRESSFIT_INSERTER = 0x14
TOOL_CRIMPING_ACTUATOR = 0x15
TOOL_THERMAL_INSPECTION = 0x16
TOOL_PASTE_JETTING = 0x17
TOOL_ULTRASONIC_WELDER = 0x18
TOOL_INVALID = 0x19

# Bootloader status
STATUS_LISTENING = 0x01
STATUS_ERASING = 0x02
STATUS_RECEIVING = 0x03
STATUS_VERIFYING = 0x06
STATUS_COPYING = 0x07
STATUS_VERIFY_OK = 0x04
STATUS_VERIFY_FAIL = 0x05
STATUS_ERROR = 0xFF

# Verify-fail reason
VERIFY_FAIL_REASON_INCOMPLETE = 0x01
VERIFY_FAIL_REASON_CRC32 = 0x02
VERIFY_FAIL_REASON_HMAC = 0x03
VERIFY_FAIL_REASON_HARDWARE_ID = 0x04
VERIFY_FAIL_REASON_ROLLBACK = 0x05

# Answering side
RESPONDER_APPLICATION = 0x00
RESPONDER_BOOTLOADER = 0x01

# Thermal fault code
THERMAL_FAULT_NONE = 0x00
THERMAL_FAULT_MAXTEMP = 0x01
THERMAL_FAULT_HEATING_NO_RISE = 0x02
THERMAL_FAULT_DROPPED_AT_TARGET = 0x03

# Reset cause flags
RESET_CAUSE_IWDG = 0x01
RESET_CAUSE_WWDG = 0x02
RESET_CAUSE_SOFTWARE = 0x04
RESET_CAUSE_POWER_ON = 0x08
RESET_CAUSE_PIN = 0x10
RESET_CAUSE_LOW_POWER = 0x20
RESET_CAUSE_OPTION_BYTES = 0x40

# Expansion board type
EXPANSION_BOARD_NONE = 0x00
EXPANSION_BOARD_BASIC_TMC2209 = 0x01
EXPANSION_BOARD_BASIC_TMC5160A = 0x02
EXPANSION_BOARD_ADVANCED_TMC2209 = 0x03
EXPANSION_BOARD_ADVANCED_TMC5160A = 0x04
EXPANSION_BOARD_BASIC_ADS1115 = 0x05
EXPANSION_BOARD_BASIC_MLX9064X = 0x06

# MLX9064x sensor variant
MLX_VARIANT_NONE = 0x00
MLX_VARIANT_MLX90640 = 0x01
MLX_VARIANT_MLX90641 = 0x02
MLX_VARIANT_MLX90642 = 0x03

# OLED mode
DISPLAY_MODE_STANDARD = 0x00
DISPLAY_MODE_NIGHT = 0x01
DISPLAY_MODE_STANDBY = 0x0F

# AOI ring light mode
AOI_RING_OFF = 0x00
AOI_RING_STROBE = 0x01
AOI_RING_CONTINUOUS = 0x02

# Thermal capture status
THERMAL_CAPTURE_IDLE = 0x00
THERMAL_CAPTURE_BUSY = 0x01
THERMAL_CAPTURE_READY = 0x02
THERMAL_CAPTURE_ERROR = 0xFF

# Plain stepper direction
MOTION_DIR_FORWARD = 0x01
MOTION_DIR_REVERSE = 0x00

# Drill direction
DRILL_DIR_COUNTER_CLOCKWISE = 0x01
DRILL_DIR_CLOCKWISE = 0x00

# Extruder direction
EXTRUDER_DIR_FORWARD = 0x01
EXTRUDER_DIR_RETRACT = 0x00

# Flags of the version patch frame
VERSION_FLAG_END_UPDATE_PATCH = 0x01

# Impact register
IMPACT_IMPACT = 0x01

ENUM_NAMES = {'tool': {0: 'SOLDERING_IRON',
          1: 'PASTE_DISPENSER',
          2: 'LIQUID_DISPENSER',
          3: 'SCREWDRIVER',
          4: 'VACUUM_PICKUP',
          5: 'DRILL',
          6: 'GRIPPER_GIMBAL',
          7: 'GRIPPER_NEMA',
          8: 'AOI_INSPECTION',
          9: 'LASER_ENGRAVER',
          10: 'PRINTER_3D',
          11: 'SCAN_PROBE',
          12: 'SMT_PICKPLACE',
          13: 'ELECTROMAGNET',
          14: 'SPOT_WELDER',
          15: 'CONFORMAL_COATING',
          16: 'VACUUM_GRIPPER_LG',
          17: 'FLYING_PROBE',
          18: 'UV_CURING',
          19: 'HOTAIR_REWORK',
          20: 'PRESSFIT_INSERTER',
          21: 'CRIMPING_ACTUATOR',
          22: 'THERMAL_INSPECTION',
          23: 'PASTE_JETTING',
          24: 'ULTRASONIC_WELDER',
          25: 'INVALID'},
 'bootloader_status': {1: 'LISTENING',
                       2: 'ERASING',
                       3: 'RECEIVING',
                       6: 'VERIFYING',
                       7: 'COPYING',
                       4: 'VERIFY_OK',
                       5: 'VERIFY_FAIL',
                       255: 'ERROR'},
 'verify_fail_reason': {1: 'INCOMPLETE', 2: 'CRC32', 3: 'HMAC', 4: 'HARDWARE_ID', 5: 'ROLLBACK'},
 'responder': {0: 'APPLICATION', 1: 'BOOTLOADER'},
 'thermal_fault': {0: 'NONE', 1: 'MAXTEMP', 2: 'HEATING_NO_RISE', 3: 'DROPPED_AT_TARGET'},
 'reset_cause': {1: 'IWDG', 2: 'WWDG', 4: 'SOFTWARE', 8: 'POWER_ON', 16: 'PIN', 32: 'LOW_POWER', 64: 'OPTION_BYTES'},
 'expansion_board_type': {0: 'NONE',
                          1: 'BASIC_TMC2209',
                          2: 'BASIC_TMC5160A',
                          3: 'ADVANCED_TMC2209',
                          4: 'ADVANCED_TMC5160A',
                          5: 'BASIC_ADS1115',
                          6: 'BASIC_MLX9064X'},
 'mlx_sensor_variant': {0: 'NONE', 1: 'MLX90640', 2: 'MLX90641', 3: 'MLX90642'},
 'display_mode': {0: 'STANDARD', 1: 'NIGHT', 15: 'STANDBY'},
 'aoi_ring_mode': {0: 'OFF', 1: 'STROBE', 2: 'CONTINUOUS'},
 'thermal_capture_status': {0: 'IDLE', 1: 'BUSY', 2: 'READY', 255: 'ERROR'},
 'motion_direction': {1: 'FORWARD', 0: 'REVERSE'},
 'drill_direction': {1: 'COUNTER_CLOCKWISE', 0: 'CLOCKWISE'},
 'extruder_direction': {1: 'FORWARD', 0: 'RETRACT'},
 'version_flags': {1: 'END_UPDATE_PATCH'},
 'impact_event': {1: 'IMPACT'}}
ENUM_TITLES = {'tool': {0: 'Soldering Iron',
          1: 'Paste Dispenser',
          2: 'Liquid Dispenser',
          3: 'Screwdriver',
          4: 'Vacuum Pickup',
          5: 'Drill',
          6: 'Gripper (Gimbal)',
          7: 'Gripper (NEMA)',
          8: 'AOI Inspection',
          9: 'Laser Engraver',
          10: '3D Printer',
          11: 'Scan Probe',
          12: 'SMT Pick & Place',
          13: 'Electromagnet',
          14: 'Spot Welder',
          15: 'Conformal Coating',
          16: 'Vacuum Gripper (LG)',
          17: 'Flying Probe',
          18: 'UV Curing',
          19: 'Hot Air Rework',
          20: 'Press-Fit Inserter',
          21: 'Crimping Actuator',
          22: 'Thermal Inspection',
          23: 'Paste Jetting',
          24: 'Ultrasonic Welder',
          25: 'No tool assigned'},
 'bootloader_status': {1: 'Listening',
                       2: 'Erasing backup slot',
                       3: 'Receiving firmware data',
                       6: 'Verifying (size/CRC32/HMAC/HardwareID)',
                       7: 'Copying backup into main slot',
                       4: 'Verify OK - jumping to new firmware',
                       5: 'Verify failed - main slot untouched',
                       255: 'Error'},
 'verify_fail_reason': {1: 'Incomplete transfer',
                        2: 'CRC32 mismatch',
                        3: 'HMAC signature mismatch',
                        4: 'HardwareID mismatch',
                        5: 'Rollback rejected'},
 'responder': {0: 'The running application', 1: 'The bootloader'},
 'thermal_fault': {0: 'None',
                   1: 'Temperature above the hard ceiling',
                   2: 'Heater on, no temperature rise',
                   3: 'Dropped far below the target at the target'},
 'reset_cause': {1: 'Hardware watchdog',
                 2: 'Window watchdog',
                 4: 'Software reset',
                 8: 'Power-on or brown-out',
                 16: 'NRST pin',
                 32: 'Low-power reset',
                 64: 'Option-byte load'},
 'expansion_board_type': {0: 'None installed',
                          1: 'Basic, TMC2209',
                          2: 'Basic, TMC5160A',
                          3: 'Advanced, TMC2209 + STM32F303CBT6',
                          4: 'Advanced, TMC5160A + STM32F303CBT6',
                          5: 'Basic, ADS1115 only (direct connection)',
                          6: 'Basic, MLX9064x only (direct connection)'},
 'mlx_sensor_variant': {0: 'None installed',
                        1: 'MLX90640 (32x24)',
                        2: 'MLX90641 (16x12)',
                        3: 'MLX90642 (32x24, onboard calculation)'},
 'display_mode': {0: 'Standard', 1: 'Night mode', 15: 'Standby (display off)'},
 'aoi_ring_mode': {0: 'Ring off', 1: 'Synchronous strobe', 2: 'Continuous illumination'},
 'thermal_capture_status': {0: 'Idle', 1: 'Capture in progress', 2: 'Frame available', 255: 'Sensor or I2C error'},
 'motion_direction': {1: 'Clockwise or forward', 0: 'Counter-clockwise or reverse'},
 'drill_direction': {1: 'Counter-clockwise (FRIN high)', 0: 'Clockwise (FRIN low)'},
 'extruder_direction': {1: 'Forward', 0: 'Retract'},
 'version_flags': {1: 'This bootloader reads the patch from the minor field of the end-of-update frame'},
 'impact_event': {1: 'Impact detected'}}
TOOL_NAMES = ENUM_TITLES["tool"]

# --- magic payloads: a destructive or one-shot command is only obeyed with exactly these four bytes ---
MAGIC_ENTER_BOOTLOADER = bytes.fromhex("B0071D5A")  # Reset the board (or the slave) into its bootloader (0x7F0)
MAGIC_AUTHORIZE_DOWNGRADE = bytes.fromhex("D09E12AD")  # Allow one older, validly signed image (0x7FD)
MAGIC_ERASE_FRAM = bytes.fromhex("E3A5E0FF")  # Erase the recovered persisted state (0x192)
MAGIC_SOLDER_FEEDER_RESET = bytes.fromhex("52535030")  # Reset the solder wire feeder position (ASCII RSP0) (0x131)
MAGIC_PAYLOADS = {'enter_bootloader': {'id': 2032, 'data': 'B0071D5A'},
 'authorize_downgrade': {'id': 2045, 'data': 'D09E12AD'},
 'erase_fram': {'id': 402, 'data': 'E3A5E0FF'},
 'solder_feeder_reset': {'id': 305, 'data': '52535030'}}

# --- registers of the expansion slave over the I2C link bus ---
SLAVE_BOOT_REG_STATUS = 0x00
SLAVE_BOOT_REG_START_UPDATE = 0x01
SLAVE_BOOT_REG_HMAC_EXPECTED = 0x02
SLAVE_BOOT_REG_DATA = 0x03
SLAVE_BOOT_REG_END_UPDATE = 0x04
SLAVE_BOOT_REG_PROGRESS = 0x05
SLAVE_BOOT_REG_QUERY_VERSION = 0x06
SLAVE_BOOT_REG_VERIFY_FAIL_REASON = 0x07
SLAVE_BOOT_REG_QUERY_VERSION_EXT = 0x08
SLAVE_APP_REG_APP_STATUS = 0x00
SLAVE_APP_REG_APP_VERSION = 0x01
SLAVE_APP_REG_ENTER_BOOTLOADER = 0x02
SLAVE_APP_REG_MLX_TRIGGER_CAPTURE = 0x10
SLAVE_APP_REG_MLX_CAPTURE_STATUS = 0x11
SLAVE_APP_REG_MLX_RAW_CHUNK = 0x12
SLAVE_APP_REG_MLX_CALIBRATED_CHUNK = 0x13
SLAVE_APP_REG_MLX_SENSOR_VARIANT = 0x14
SLAVE_APP_REG_ADS_CONFIGURE = 0x20
SLAVE_APP_REG_ADS_TRIGGER = 0x21
SLAVE_APP_REG_ADS_READ = 0x22
SLAVE_APP_REG_PWM_CONFIGURE = 0x30
SLAVE_APP_REG_PWM_PULSE = 0x31
SLAVE_APP_REG_PWM_STOP = 0x32

# --- SLCAN ---
SLCAN_BITRATES = [('10 kbit/s', '0'),
 ('20 kbit/s', '1'),
 ('50 kbit/s', '2'),
 ('100 kbit/s', '3'),
 ('125 kbit/s', '4'),
 ('250 kbit/s', '5'),
 ('500 kbit/s', '6'),
 ('800 kbit/s', '7'),
 ('1 Mbit/s', '8')]
SLCAN_BITRATE_DEFAULT_CODE = "6"
SLCAN_RX_BUFFER_LIMIT = 4096

# --- one record per identifier ---
MESSAGES = {
    149: {'name': 'IMPACT_EVENT', 'group': 'impact', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [11]},
    256: {'name': 'GLOBAL_STATUS', 'group': 'global', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    272: {'name': 'QUERY_ACTIVE_TOOL', 'group': 'global', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    273: {'name': 'ACTIVE_TOOL_RESP', 'group': 'global', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    288: {'name': 'MOTION_CMD', 'group': 'motion', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [0, 1, 2, 3, 6, 7, 12, 16], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}},
    304: {'name': 'SOLDER_SETPOINT', 'group': 'soldering', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [0], 'gates': {'blocked_by_critical_error': True}, 'timing': {'watchdog_ms': 250}},
    305: {'name': 'SOLDER_FEEDER_RESET', 'group': 'soldering', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [0], 'gates': {'blocked_by_critical_error': True, 'needs_magic': 'solder_feeder_reset'}},
    306: {'name': 'SOLDER_FEEDER_POS', 'group': 'soldering', 'direction': 'both', 'handled_by': 'application', 'tools': [0], 'gates': {'blocked_by_critical_error': True}},
    309: {'name': 'SOLDER_TELEMETRY', 'group': 'soldering', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [0, 19], 'timing': {'period_ms': 150}},
    320: {'name': 'DRILL_CMD', 'group': 'drill', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [5], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}, 'timing': {'watchdog_ms': 250}},
    325: {'name': 'VACUUM_TELEMETRY', 'group': 'vacuum', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [4], 'timing': {'period_ms': 150}},
    327: {'name': 'DRILL_TELEMETRY', 'group': 'drill', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [5], 'timing': {'period_ms': 150}},
    336: {'name': 'AOI_CMD', 'group': 'aoi', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [8], 'gates': {'blocked_by_critical_error': True}},
    341: {'name': 'AOI_TELEMETRY', 'group': 'aoi', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [8], 'timing': {'period_ms': 150}},
    352: {'name': 'LASER_CMD', 'group': 'laser', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [9], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}, 'timing': {'watchdog_ms': 250}},
    357: {'name': 'LASER_TELEMETRY', 'group': 'laser', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [9], 'timing': {'period_ms': 150}},
    368: {'name': 'PRINTER_THERMAL_MOTION', 'group': 'printer', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [10], 'gates': {'blocked_by_critical_error': True}, 'timing': {'watchdog_ms': 250}},
    371: {'name': 'PRINTER_LAYERFAN_CMD', 'group': 'printer', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [10], 'gates': {'blocked_by_critical_error': True}, 'timing': {'watchdog_ms': 1000}},
    373: {'name': 'PRINTER_HOTEND_TELEMETRY', 'group': 'printer', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [10], 'timing': {'period_ms': 150}},
    375: {'name': 'PRINTER_LAYERFAN_RPM', 'group': 'printer', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [10], 'timing': {'period_ms': 150}},
    376: {'name': 'PRINTER_HOTENDFAN_CMD', 'group': 'printer', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [10], 'gates': {'blocked_by_critical_error': True}},
    377: {'name': 'PRINTER_HOTENDFAN_RPM', 'group': 'printer', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [10], 'timing': {'period_ms': 150}},
    384: {'name': 'EXPANSION_SPI_REQ', 'group': 'global', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    385: {'name': 'EXPANSION_SPI_RESP', 'group': 'global', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': None},
    386: {'name': 'EXPANSION_DIAG0_REQ', 'group': 'global', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    387: {'name': 'EXPANSION_DIAG0_RESP', 'group': 'global', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': None},
    400: {'name': 'FRAM_QUERY', 'group': 'global', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    401: {'name': 'FRAM_STATE_RESP', 'group': 'global', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': None},
    402: {'name': 'ERASE_FRAM', 'group': 'global', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True, 'needs_magic': 'erase_fram'}},
    416: {'name': 'SET_EXPANSION_TYPE', 'group': 'configuration', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    417: {'name': 'EXPANSION_TYPE_RESP', 'group': 'configuration', 'direction': 'both', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    418: {'name': 'SET_FREE_TOOL', 'group': 'configuration', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    419: {'name': 'FREE_TOOL_CONFIG_RESP', 'group': 'configuration', 'direction': 'both', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    420: {'name': 'SET_DEVICE_SERIAL', 'group': 'configuration', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    421: {'name': 'PERIPHERAL_INFO_RESP', 'group': 'configuration', 'direction': 'both', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    422: {'name': 'SET_MLX_VARIANT', 'group': 'configuration', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    423: {'name': 'MLX_VARIANT_RESP', 'group': 'configuration', 'direction': 'both', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    424: {'name': 'BLACKBOX_QUERY', 'group': 'diagnostics', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    425: {'name': 'BLACKBOX_CHUNK', 'group': 'diagnostics', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': None},
    426: {'name': 'THERMAL_STATS_QUERY', 'group': 'diagnostics', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    427: {'name': 'THERMAL_STATS_RESP', 'group': 'diagnostics', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': None},
    432: {'name': 'ELECTROMAGNET_CMD', 'group': 'electromagnet', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [13], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}},
    448: {'name': 'SPOT_WELD_CMD', 'group': 'welding', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [14], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}},
    464: {'name': 'UV_CURING_CMD', 'group': 'uv', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [18], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}, 'timing': {'watchdog_ms': 250}},
    480: {'name': 'HOTAIR_CMD', 'group': 'hotair', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [19], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}, 'timing': {'watchdog_ms': 250}},
    496: {'name': 'CRIMPING_CMD', 'group': 'crimping', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [21], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}},
    512: {'name': 'ULTRASONIC_WELD_CMD', 'group': 'welding', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [24], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}},
    528: {'name': 'SLAVE_ENTER_BOOTLOADER', 'group': 'slave_bridge', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True, 'needs_magic': 'enter_bootloader'}},
    529: {'name': 'SLAVE_START_UPDATE', 'group': 'slave_bridge', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    530: {'name': 'SLAVE_HMAC_CHUNK', 'group': 'slave_bridge', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    531: {'name': 'SLAVE_DATA', 'group': 'slave_bridge', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    532: {'name': 'SLAVE_END_UPDATE', 'group': 'slave_bridge', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    533: {'name': 'SLAVE_STATUS', 'group': 'slave_bridge', 'direction': 'both', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    534: {'name': 'SLAVE_PROGRESS', 'group': 'slave_bridge', 'direction': 'both', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    535: {'name': 'SLAVE_VERSION_RESP_1', 'group': 'slave_bridge', 'direction': 'both', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    536: {'name': 'SLAVE_VERSION_RESP_2', 'group': 'slave_bridge', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': None},
    537: {'name': 'SLAVE_VERIFY_FAIL_REASON', 'group': 'slave_bridge', 'direction': 'both', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    544: {'name': 'SLAVE_REG_WRITE', 'group': 'slave_bridge', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    545: {'name': 'SLAVE_REG_READ', 'group': 'slave_bridge', 'direction': 'both', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': True}},
    560: {'name': 'PASTE_JETTING_CONFIG', 'group': 'pastejetting', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [23], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}},
    561: {'name': 'PASTE_JETTING_PULSE', 'group': 'pastejetting', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [23], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}},
    576: {'name': 'ADS1115_CONFIG', 'group': 'functionaltest', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [17], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}},
    577: {'name': 'ADS1115_TRIGGER', 'group': 'functionaltest', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [17], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}},
    578: {'name': 'ADS1115_RESULT', 'group': 'functionaltest', 'direction': 'both', 'handled_by': 'application', 'tools': [17], 'gates': {'blocked_by_critical_error': True}},
    579: {'name': 'FLYING_PROBE_BASIC', 'group': 'functionaltest', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [17], 'timing': {'period_ms': 150}},
    592: {'name': 'THERMAL_TRIGGER', 'group': 'thermal', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [22], 'gates': {'blocked_by_critical_error': True, 'blocked_during_boot_sequence': True}},
    593: {'name': 'THERMAL_STATUS', 'group': 'thermal', 'direction': 'both', 'handled_by': 'application', 'tools': [22], 'gates': {'blocked_by_critical_error': True}},
    594: {'name': 'THERMAL_RAW_CHUNK_REQ', 'group': 'thermal', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [22], 'gates': {'blocked_by_critical_error': True}},
    595: {'name': 'THERMAL_RAW_CHUNK', 'group': 'thermal', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [22]},
    596: {'name': 'THERMAL_CAL_CHUNK_REQ', 'group': 'thermal', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': [22], 'gates': {'blocked_by_critical_error': True}},
    597: {'name': 'THERMAL_CAL_CHUNK', 'group': 'thermal', 'direction': 'board_to_host', 'handled_by': 'application', 'tools': [22]},
    2025: {'name': 'VERSION_PATCH_RESPONSE', 'group': 'bootloader', 'direction': 'board_to_host', 'handled_by': 'both', 'tools': None},
    2032: {'name': 'ENTER_BOOTLOADER', 'group': 'bootloader', 'direction': 'host_to_board', 'handled_by': 'application', 'tools': None, 'gates': {'blocked_by_critical_error': False, 'needs_magic': 'enter_bootloader'}},
    2033: {'name': 'START_UPDATE', 'group': 'bootloader', 'direction': 'host_to_board', 'handled_by': 'bootloader', 'tools': None},
    2034: {'name': 'DATA', 'group': 'bootloader', 'direction': 'host_to_board', 'handled_by': 'bootloader', 'tools': None},
    2035: {'name': 'PAGE_ACK', 'group': 'bootloader', 'direction': 'board_to_host', 'handled_by': 'bootloader', 'tools': None},
    2036: {'name': 'END_UPDATE', 'group': 'bootloader', 'direction': 'host_to_board', 'handled_by': 'bootloader', 'tools': None},
    2037: {'name': 'STATUS', 'group': 'bootloader', 'direction': 'board_to_host', 'handled_by': 'bootloader', 'tools': None},
    2038: {'name': 'HEARTBEAT', 'group': 'bootloader', 'direction': 'board_to_host', 'handled_by': 'bootloader', 'tools': None, 'timing': {'period_ms': 1000}},
    2039: {'name': 'HMAC_CHUNK', 'group': 'bootloader', 'direction': 'host_to_board', 'handled_by': 'bootloader', 'tools': None},
    2040: {'name': 'QUERY_VERSION', 'group': 'bootloader', 'direction': 'host_to_board', 'handled_by': 'both', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    2041: {'name': 'VERSION_RESPONSE', 'group': 'bootloader', 'direction': 'board_to_host', 'handled_by': 'both', 'tools': None},
    2042: {'name': 'BOOTLOADER_VERSION_RESPONSE', 'group': 'bootloader', 'direction': 'board_to_host', 'handled_by': 'bootloader', 'tools': None},
    2043: {'name': 'QUERY_ERROR_COUNTERS', 'group': 'bootloader', 'direction': 'host_to_board', 'handled_by': 'both', 'tools': None, 'gates': {'blocked_by_critical_error': False}},
    2044: {'name': 'ERROR_COUNTERS_RESPONSE', 'group': 'bootloader', 'direction': 'board_to_host', 'handled_by': 'both', 'tools': None},
    2045: {'name': 'AUTHORIZE_DOWNGRADE', 'group': 'bootloader', 'direction': 'host_to_board', 'handled_by': 'bootloader', 'tools': None, 'gates': {'needs_magic': 'authorize_downgrade'}},
    2046: {'name': 'READBACK', 'group': 'bootloader', 'direction': 'both', 'handled_by': 'bootloader', 'tools': None},
    2047: {'name': 'READBACK_PAGE_ACK', 'group': 'bootloader', 'direction': 'host_to_board', 'handled_by': 'bootloader', 'tools': None},
}

# --- one record per layout (the data the encoder and the decoder run on) ---
LAYOUTS = {
    'impact_event': {'id': 149, 'role': 'response', 'dlc': {'exact': 1}, 'fields': [{'name': 'event', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'global_status': {'id': 256, 'role': 'request', 'dlc': {'exact': 8}, 'fields': [{'name': 'status_r', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'status_g', 'type': 'u8', 'offset': 1, 'width': 1}, {'name': 'status_b', 'type': 'u8', 'offset': 2, 'width': 1}, {'name': 'display_mode', 'type': 'u8', 'offset': 3, 'width': 1, 'allowed': [0, 1, 15]}, {'name': 'ring_r', 'type': 'u8', 'offset': 4, 'width': 1}, {'name': 'ring_g', 'type': 'u8', 'offset': 5, 'width': 1}, {'name': 'ring_b', 'type': 'u8', 'offset': 6, 'width': 1}, {'name': 'ring_on', 'type': 'u8', 'offset': 7, 'width': 1, 'range': [0, 1]}]},
    'query_active_tool': {'id': 272, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'active_tool_resp': {'id': 273, 'role': 'response', 'dlc': {'min': 4, 'max': 6}, 'fields': [{'name': 'tool_id', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'system_error', 'type': 'u8', 'offset': 1, 'width': 1, 'range': [0, 1]}, {'name': 'can_error', 'type': 'u8', 'offset': 2, 'width': 1, 'range': [0, 1]}, {'name': 'booting', 'type': 'u8', 'offset': 3, 'width': 1, 'range': [0, 1]}, {'name': 'thermal_fault', 'type': 'u8', 'offset': 4, 'width': 1, 'optional': True}, {'name': 'reset_cause', 'type': 'u8', 'offset': 5, 'width': 1, 'optional': True}]},
    'motion_cmd': {'id': 288, 'role': 'request', 'dlc': {'exact': 5}, 'fields': [{'name': 'direction', 'type': 'u8', 'offset': 0, 'width': 1, 'allowed': [1, 0]}, {'name': 'steps', 'type': 'u32', 'offset': 1, 'width': 4}]},
    'solder_setpoint': {'id': 304, 'role': 'request', 'dlc': {'exact': 2}, 'fields': [{'name': 'setpoint_c', 'type': 'u16', 'offset': 0, 'width': 2, 'range': [0, 445]}]},
    'solder_feeder_reset': {'id': 305, 'role': 'request', 'dlc': {'exact': 4}, 'fields': [{'name': 'magic', 'type': 'bytes', 'offset': 0, 'fixed': '52535030', 'length': 4}]},
    'solder_feeder_pos_request': {'id': 306, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'solder_feeder_pos_response': {'id': 306, 'role': 'response', 'dlc': {'exact': 4}, 'fields': [{'name': 'position', 'type': 'i32', 'offset': 0, 'width': 4}]},
    'solder_telemetry': {'id': 309, 'role': 'response', 'dlc': {'exact': 2}, 'fields': [{'name': 'temperature_c', 'type': 'u16', 'offset': 0, 'width': 2}]},
    'drill_cmd': {'id': 320, 'role': 'request', 'dlc': {'exact': 2}, 'fields': [{'name': 'speed', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'direction', 'type': 'u8', 'offset': 1, 'width': 1, 'allowed': [1, 0]}]},
    'vacuum_telemetry': {'id': 325, 'role': 'response', 'dlc': {'exact': 3}, 'fields': [{'name': 'adc', 'type': 'u16', 'offset': 0, 'width': 2, 'range': [0, 4095]}, {'name': 'detected', 'type': 'u8', 'offset': 2, 'width': 1, 'range': [0, 1]}]},
    'drill_telemetry': {'id': 327, 'role': 'response', 'dlc': {'exact': 3}, 'fields': [{'name': 'rpm', 'type': 'u16', 'offset': 0, 'width': 2}, {'name': 'endstop', 'type': 'u8', 'offset': 2, 'width': 1, 'range': [0, 1]}]},
    'aoi_cmd': {'id': 336, 'role': 'request', 'dlc': {'exact': 3}, 'fields': [{'name': 'mode', 'type': 'u8', 'offset': 0, 'width': 1, 'allowed': [0, 1, 2]}, {'name': 'strobe_period_ms', 'type': 'u16', 'offset': 1, 'width': 2, 'range': [1, 500]}]},
    'aoi_telemetry': {'id': 341, 'role': 'response', 'dlc': {'exact': 1}, 'fields': [{'name': 'endstop', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 1]}]},
    'laser_cmd': {'id': 352, 'role': 'request', 'dlc': {'exact': 2}, 'fields': [{'name': 'power', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'interlock', 'type': 'u8', 'offset': 1, 'width': 1, 'range': [0, 1]}]},
    'laser_telemetry': {'id': 357, 'role': 'response', 'dlc': {'exact': 1}, 'fields': [{'name': 'endstop', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 1]}]},
    'printer_thermal_motion': {'id': 368, 'role': 'request', 'dlc': {'exact': 6}, 'fields': [{'name': 'nozzle_setpoint_c', 'type': 'u16', 'offset': 0, 'width': 2, 'range': [0, 300]}, {'name': 'extruder_direction', 'type': 'u8', 'offset': 2, 'width': 1, 'allowed': [1, 0]}, {'name': 'extruder_steps', 'type': 'u24', 'offset': 3, 'width': 3}]},
    'printer_layerfan_cmd': {'id': 371, 'role': 'request', 'dlc': {'exact': 1}, 'fields': [{'name': 'power', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'printer_hotend_telemetry': {'id': 373, 'role': 'response', 'dlc': {'exact': 2}, 'fields': [{'name': 'temperature_c', 'type': 'u16', 'offset': 0, 'width': 2}]},
    'printer_layerfan_rpm': {'id': 375, 'role': 'response', 'dlc': {'exact': 2}, 'fields': [{'name': 'rpm', 'type': 'u16', 'offset': 0, 'width': 2}]},
    'printer_hotendfan_cmd': {'id': 376, 'role': 'request', 'dlc': {'exact': 1}, 'fields': [{'name': 'power', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'printer_hotendfan_rpm': {'id': 377, 'role': 'response', 'dlc': {'exact': 2}, 'fields': [{'name': 'rpm', 'type': 'u16', 'offset': 0, 'width': 2}]},
    'expansion_spi_req': {'id': 384, 'role': 'request', 'dlc': {'min': 2, 'max': 8}, 'fields': [{'name': 'count', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [1, 7]}, {'name': 'data', 'type': 'bytes', 'offset': 1, 'rest': True, 'length_field': 'count'}]},
    'expansion_spi_resp': {'id': 385, 'role': 'response', 'dlc': {'min': 2, 'max': 8}, 'fields': [{'name': 'count', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [1, 7]}, {'name': 'data', 'type': 'bytes', 'offset': 1, 'rest': True, 'length_field': 'count'}]},
    'expansion_diag0_req': {'id': 386, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'expansion_diag0_resp': {'id': 387, 'role': 'response', 'dlc': {'exact': 1}, 'fields': [{'name': 'level', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 1]}]},
    'fram_query': {'id': 400, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'fram_state_resp': {'id': 401, 'role': 'response', 'dlc': {'exact': 8}, 'fields': [{'name': 'valid', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 1]}, {'name': 'tool_id', 'type': 'u8', 'offset': 1, 'width': 1}, {'name': 'had_error', 'type': 'u8', 'offset': 2, 'width': 1, 'range': [0, 1]}, {'name': 'setpoint_c', 'type': 'u16', 'offset': 3, 'width': 2}, {'name': 'speed', 'type': 'u8', 'offset': 5, 'width': 1}, {'name': 'dir_or_interlock', 'type': 'u8', 'offset': 6, 'width': 1, 'range': [0, 1]}, {'name': 'fan', 'type': 'u8', 'offset': 7, 'width': 1}]},
    'erase_fram': {'id': 402, 'role': 'request', 'dlc': {'exact': 4}, 'fields': [{'name': 'magic', 'type': 'bytes', 'offset': 0, 'fixed': 'E3A5E0FF', 'length': 4}]},
    'set_expansion_type': {'id': 416, 'role': 'request', 'dlc': {'min': 1, 'max': 8}, 'fields': [{'name': 'board_type', 'type': 'u8', 'offset': 0, 'width': 1, 'allowed': [0, 1, 2, 3, 4, 5, 6]}]},
    'expansion_type_resp_request': {'id': 417, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'expansion_type_resp_response': {'id': 417, 'role': 'response', 'dlc': {'exact': 1}, 'fields': [{'name': 'board_type', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'set_free_tool': {'id': 418, 'role': 'request', 'dlc': {'min': 1, 'max': 8}, 'fields': [{'name': 'selection', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 25]}]},
    'free_tool_config_resp_request': {'id': 419, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'free_tool_config_resp_response': {'id': 419, 'role': 'response', 'dlc': {'exact': 2}, 'fields': [{'name': 'jumper_reading', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 31]}, {'name': 'selection', 'type': 'u8', 'offset': 1, 'width': 1, 'range': [0, 25]}]},
    'set_device_serial': {'id': 420, 'role': 'request', 'dlc': {'min': 1, 'max': 8}, 'fields': [{'name': 'serial', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'peripheral_info_resp_request': {'id': 421, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'peripheral_info_resp_response': {'id': 421, 'role': 'response', 'dlc': {'exact': 2}, 'fields': [{'name': 'peripheral_type', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'serial', 'type': 'u8', 'offset': 1, 'width': 1}]},
    'set_mlx_variant': {'id': 422, 'role': 'request', 'dlc': {'min': 1, 'max': 8}, 'fields': [{'name': 'variant', 'type': 'u8', 'offset': 0, 'width': 1, 'allowed': [0, 1, 2, 3]}]},
    'mlx_variant_resp_request': {'id': 423, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'mlx_variant_resp_response': {'id': 423, 'role': 'response', 'dlc': {'exact': 1}, 'fields': [{'name': 'variant', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'blackbox_query': {'id': 424, 'role': 'request', 'dlc': {'min': 1, 'max': 8}, 'fields': [{'name': 'chunk_index', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 21]}]},
    'blackbox_chunk': {'id': 425, 'role': 'response', 'dlc': {'exact': 8}, 'fields': [{'name': 'data', 'type': 'bytes', 'offset': 0, 'length': 8}]},
    'thermal_stats_query': {'id': 426, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'thermal_stats_resp': {'id': 427, 'role': 'response', 'dlc': {'exact': 8}, 'fields': [{'name': 'fault_count', 'type': 'u16', 'offset': 0, 'width': 2}, {'name': 'heater_on_seconds', 'type': 'u32', 'offset': 2, 'width': 4}, {'name': 'last_fault', 'type': 'u8', 'offset': 6, 'width': 1}, {'name': 'persisted', 'type': 'u8', 'offset': 7, 'width': 1, 'range': [0, 1]}]},
    'electromagnet_cmd': {'id': 432, 'role': 'request', 'dlc': {'exact': 1}, 'fields': [{'name': 'coil', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 1]}]},
    'spot_weld_cmd': {'id': 448, 'role': 'request', 'dlc': {'exact': 3}, 'fields': [{'name': 'fire', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [1, 1]}, {'name': 'duration_ms', 'type': 'u16', 'offset': 1, 'width': 2, 'range': [1, 2000]}]},
    'uv_curing_cmd': {'id': 464, 'role': 'request', 'dlc': {'exact': 1}, 'fields': [{'name': 'duty', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'hotair_cmd': {'id': 480, 'role': 'request', 'dlc': {'exact': 3}, 'fields': [{'name': 'setpoint_c', 'type': 'u16', 'offset': 0, 'width': 2, 'range': [0, 445]}, {'name': 'blower_duty', 'type': 'u8', 'offset': 2, 'width': 1}]},
    'crimping_cmd': {'id': 496, 'role': 'request', 'dlc': {'exact': 5}, 'fields': [{'name': 'direction', 'type': 'u8', 'offset': 0, 'width': 1, 'allowed': [1, 0]}, {'name': 'steps', 'type': 'u32', 'offset': 1, 'width': 4}]},
    'ultrasonic_weld_cmd': {'id': 512, 'role': 'request', 'dlc': {'exact': 3}, 'fields': [{'name': 'fire', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [1, 1]}, {'name': 'duration_ms', 'type': 'u16', 'offset': 1, 'width': 2, 'range': [1, 2000]}]},
    'slave_enter_bootloader': {'id': 528, 'role': 'request', 'dlc': {'exact': 4}, 'fields': [{'name': 'magic', 'type': 'bytes', 'offset': 0, 'fixed': 'B0071D5A', 'length': 4}]},
    'slave_start_update': {'id': 529, 'role': 'request', 'dlc': {'exact': 8}, 'fields': [{'name': 'total_size', 'type': 'u32', 'offset': 0, 'width': 4}, {'name': 'hardware_id', 'type': 'u32', 'offset': 4, 'width': 4}]},
    'slave_hmac_chunk': {'id': 530, 'role': 'request', 'dlc': {'exact': 8}, 'fields': [{'name': 'hmac_part', 'type': 'bytes', 'offset': 0, 'length': 8}]},
    'slave_data': {'id': 531, 'role': 'request', 'dlc': {'min': 1, 'max': 8}, 'fields': [{'name': 'data', 'type': 'bytes', 'offset': 0, 'rest': True}]},
    'slave_end_update': {'id': 532, 'role': 'request', 'dlc': {'exact': 8}, 'fields': [{'name': 'crc32', 'type': 'u32', 'offset': 0, 'width': 4}, {'name': 'version_major', 'type': 'u16', 'offset': 4, 'width': 2}, {'name': 'version_minor_field', 'type': 'u16', 'offset': 6, 'width': 2}]},
    'slave_status_request': {'id': 533, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'slave_status_response': {'id': 533, 'role': 'response', 'dlc': {'exact': 1}, 'fields': [{'name': 'status', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'slave_progress_request': {'id': 534, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'slave_progress_response': {'id': 534, 'role': 'response', 'dlc': {'exact': 1}, 'fields': [{'name': 'progress', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'slave_version_resp_1_request': {'id': 535, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'slave_version_resp_1_response': {'id': 535, 'role': 'response', 'dlc': {'exact': 8}, 'fields': [{'name': 'responder', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'hardware_id', 'type': 'u32', 'offset': 1, 'width': 4}, {'name': 'version_major', 'type': 'u16', 'offset': 5, 'width': 2}, {'name': 'version_minor_high', 'type': 'u8', 'offset': 7, 'width': 1}]},
    'slave_version_resp_2': {'id': 536, 'role': 'response', 'dlc': {'one_of': [2, 5]}, 'fields': [{'name': 'version_minor_low', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'bootloader_major', 'type': 'u8', 'offset': 1, 'width': 1}, {'name': 'app_patch', 'type': 'u8', 'offset': 2, 'width': 1, 'optional': True, 'present_from_dlc': 5}, {'name': 'bootloader_minor', 'type': 'u8', 'offset': 3, 'width': 1, 'optional': True, 'present_from_dlc': 5}, {'name': 'bootloader_patch', 'type': 'u8', 'offset': 4, 'width': 1, 'optional': True, 'present_from_dlc': 5}]},
    'slave_verify_fail_reason_request': {'id': 537, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'slave_verify_fail_reason_response': {'id': 537, 'role': 'response', 'dlc': {'exact': 1}, 'fields': [{'name': 'reason', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'slave_reg_write': {'id': 544, 'role': 'request', 'dlc': {'min': 2, 'max': 8}, 'fields': [{'name': 'register', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'payload', 'type': 'bytes', 'offset': 1, 'rest': True}]},
    'slave_reg_read_request': {'id': 545, 'role': 'request', 'dlc': {'exact': 2}, 'fields': [{'name': 'register', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'length', 'type': 'u8', 'offset': 1, 'width': 1, 'range': [1, 8]}]},
    'slave_reg_read_response': {'id': 545, 'role': 'response', 'dlc': {'min': 1, 'max': 8}, 'fields': [{'name': 'data', 'type': 'bytes', 'offset': 0, 'rest': True}]},
    'paste_jetting_config': {'id': 560, 'role': 'request', 'dlc': {'exact': 3}, 'fields': [{'name': 'channel', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 3]}, {'name': 'frequency_hz', 'type': 'u16', 'offset': 1, 'width': 2, 'range': [1, 65535]}]},
    'paste_jetting_pulse': {'id': 561, 'role': 'request', 'dlc': {'exact': 3}, 'fields': [{'name': 'channel', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 3]}, {'name': 'duty_percent', 'type': 'u8', 'offset': 1, 'width': 1, 'range': [0, 100]}, {'name': 'duration_ms', 'type': 'u8', 'offset': 2, 'width': 1, 'range': [1, 255]}]},
    'ads1115_config': {'id': 576, 'role': 'request', 'dlc': {'exact': 2}, 'fields': [{'name': 'config', 'type': 'u16', 'offset': 0, 'width': 2}]},
    'ads1115_trigger': {'id': 577, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'ads1115_result_request': {'id': 578, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'ads1115_result_response': {'id': 578, 'role': 'response', 'dlc': {'exact': 2}, 'fields': [{'name': 'raw', 'type': 'i16', 'offset': 0, 'width': 2}]},
    'flying_probe_basic': {'id': 579, 'role': 'response', 'dlc': {'exact': 2}, 'fields': [{'name': 'adc', 'type': 'u16', 'offset': 0, 'width': 2, 'range': [0, 4095]}]},
    'thermal_trigger': {'id': 592, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'thermal_status_request': {'id': 593, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'thermal_status_response': {'id': 593, 'role': 'response', 'dlc': {'exact': 1}, 'fields': [{'name': 'status', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'thermal_raw_chunk_req': {'id': 594, 'role': 'request', 'dlc': {'exact': 1}, 'fields': [{'name': 'chunk', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 47]}]},
    'thermal_raw_chunk': {'id': 595, 'role': 'response', 'dlc': {'exact': 8}, 'fields': [{'name': 'data', 'type': 'bytes', 'offset': 0, 'length': 8}]},
    'thermal_cal_chunk_req': {'id': 596, 'role': 'request', 'dlc': {'exact': 1}, 'fields': [{'name': 'chunk', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 47]}]},
    'thermal_cal_chunk': {'id': 597, 'role': 'response', 'dlc': {'exact': 8}, 'fields': [{'name': 'data', 'type': 'bytes', 'offset': 0, 'length': 8}]},
    'version_patch_response': {'id': 2025, 'role': 'response', 'dlc': {'min': 3, 'max': 8}, 'fields': [{'name': 'responder', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'patch', 'type': 'u8', 'offset': 1, 'width': 1}, {'name': 'flags', 'type': 'u8', 'offset': 2, 'width': 1}]},
    'enter_bootloader': {'id': 2032, 'role': 'request', 'dlc': {'exact': 4}, 'fields': [{'name': 'magic', 'type': 'bytes', 'offset': 0, 'fixed': 'B0071D5A', 'length': 4}]},
    'start_update': {'id': 2033, 'role': 'request', 'dlc': {'exact': 8}, 'fields': [{'name': 'total_size', 'type': 'u32', 'offset': 0, 'width': 4}, {'name': 'hardware_id', 'type': 'u32', 'offset': 4, 'width': 4}]},
    'data': {'id': 2034, 'role': 'request', 'dlc': {'min': 1, 'max': 8}, 'fields': [{'name': 'data', 'type': 'bytes', 'offset': 0, 'rest': True}]},
    'page_ack': {'id': 2035, 'role': 'response', 'dlc': {'exact': 4}, 'fields': [{'name': 'page_index', 'type': 'u32', 'offset': 0, 'width': 4}]},
    'end_update': {'id': 2036, 'role': 'request', 'dlc': {'exact': 8}, 'fields': [{'name': 'crc32', 'type': 'u32', 'offset': 0, 'width': 4}, {'name': 'version_major', 'type': 'u16', 'offset': 4, 'width': 2}, {'name': 'version_minor_field', 'type': 'u16', 'offset': 6, 'width': 2}]},
    'status': {'id': 2037, 'role': 'response', 'dlc': {'min': 1, 'max': 2}, 'fields': [{'name': 'status', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'reason', 'type': 'u8', 'offset': 1, 'width': 1, 'optional': True}]},
    'heartbeat': {'id': 2038, 'role': 'response', 'dlc': {'exact': 2}, 'fields': [{'name': 'status', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'progress', 'type': 'u8', 'offset': 1, 'width': 1}]},
    'hmac_chunk': {'id': 2039, 'role': 'request', 'dlc': {'exact': 8}, 'fields': [{'name': 'hmac_part', 'type': 'bytes', 'offset': 0, 'length': 8}]},
    'query_version': {'id': 2040, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'version_response': {'id': 2041, 'role': 'response', 'dlc': {'exact': 8}, 'fields': [{'name': 'responder', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'hardware_id', 'type': 'u32', 'offset': 1, 'width': 4}, {'name': 'version_major', 'type': 'u16', 'offset': 5, 'width': 2}, {'name': 'version_minor', 'type': 'u8', 'offset': 7, 'width': 1}]},
    'bootloader_version_response': {'id': 2042, 'role': 'response', 'dlc': {'exact': 3}, 'fields': [{'name': 'major', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'minor', 'type': 'u8', 'offset': 1, 'width': 1}, {'name': 'patch', 'type': 'u8', 'offset': 2, 'width': 1}]},
    'query_error_counters': {'id': 2043, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'error_counters_response': {'id': 2044, 'role': 'response', 'dlc': {'exact': 2}, 'fields': [{'name': 'tec', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'rec', 'type': 'u8', 'offset': 1, 'width': 1}]},
    'authorize_downgrade': {'id': 2045, 'role': 'request', 'dlc': {'exact': 4}, 'fields': [{'name': 'magic', 'type': 'bytes', 'offset': 0, 'fixed': 'D09E12AD', 'length': 4}]},
    'readback_request': {'id': 2046, 'role': 'request', 'dlc': {'any': True}, 'fields': []},
    'readback_response_size': {'id': 2046, 'role': 'response', 'dlc': {'exact': 4}, 'fields': [{'name': 'total_size', 'type': 'u32', 'offset': 0, 'width': 4}]},
    'readback_response_data': {'id': 2046, 'role': 'response', 'dlc': {'min': 1, 'max': 8}, 'fields': [{'name': 'data', 'type': 'bytes', 'offset': 0, 'rest': True}]},
    'readback_page_ack': {'id': 2047, 'role': 'request', 'dlc': {'exact': 4}, 'fields': [{'name': 'page_index', 'type': 'u32', 'offset': 0, 'width': 4}]},
    'mn_discover': {'id': 1024, 'role': 'request', 'dlc': {'exact': 2}, 'fields': [{'name': 'mn_version', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'slot_ms', 'type': 'u8', 'offset': 1, 'width': 1, 'range': [1, 50]}]},
    'mn_select': {'id': 1025, 'role': 'request', 'dlc': {'exact': 3}, 'fields': [{'name': 'action', 'type': 'u8', 'offset': 0, 'width': 1, 'range': [0, 1]}, {'name': 'node', 'type': 'u8', 'offset': 1, 'width': 1, 'range': [0, 31]}, {'name': 'seq', 'type': 'u8', 'offset': 2, 'width': 1}]},
    'mn_safe_stop': {'id': 1026, 'role': 'request', 'dlc': {'exact': 1}, 'fields': [{'name': 'reason', 'type': 'u8', 'offset': 0, 'width': 1}]},
    'mn_node_info': {'id': 1056, 'role': 'response', 'dlc': {'exact': 8}, 'fields': [{'name': 'tool', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'state', 'type': 'u8', 'offset': 1, 'width': 1}, {'name': 'instance', 'type': 'u8', 'offset': 2, 'width': 1}, {'name': 'mn_version', 'type': 'u8', 'offset': 3, 'width': 1}, {'name': 'serial', 'type': 'u32', 'offset': 4, 'width': 4}]},
    'mn_node_status': {'id': 1088, 'role': 'response', 'dlc': {'exact': 4}, 'fields': [{'name': 'state', 'type': 'u8', 'offset': 0, 'width': 1}, {'name': 'error', 'type': 'u8', 'offset': 1, 'width': 1}, {'name': 'uptime_s', 'type': 'u16', 'offset': 2, 'width': 2}]},
    'mn_node_cmd': {'id': 1120, 'role': 'request', 'dlc': {'min': 2, 'max': 8}, 'fields': [{'name': 'func', 'type': 'u16', 'offset': 0, 'width': 2}, {'name': 'args', 'type': 'bytes', 'offset': 2, 'rest': True}]},
    'mn_node_resp': {'id': 1152, 'role': 'response', 'dlc': {'min': 2, 'max': 8}, 'fields': [{'name': 'func', 'type': 'u16', 'offset': 0, 'width': 2}, {'name': 'data', 'type': 'bytes', 'offset': 2, 'rest': True}]},
}

# ---------------------------------------------------------------------------
# pure encoders and decoders (the runtime below is the same in every generated copy)
# ---------------------------------------------------------------------------
_INT_LIMITS = {
    "u8": (0, 0xFF), "u16": (0, 0xFFFF), "u24": (0, 0xFFFFFF), "u32": (0, 0xFFFFFFFF),
    "i16": (-0x8000, 0x7FFF), "i32": (-0x80000000, 0x7FFFFFFF),
}
_WIDTHS = {"u8": 1, "u16": 2, "u24": 3, "u32": 4, "i16": 2, "i32": 4}


def dlc_allows(rule, length):
    """Whether a payload of this length satisfies a length rule of the specification."""
    if "exact" in rule:
        return length == rule["exact"]
    if "one_of" in rule:
        return length in rule["one_of"]
    if "min" in rule:
        return rule["min"] <= length <= rule["max"]
    return 0 <= length <= DLC_MAX


def _dlc_floor(rule):
    if "exact" in rule:
        return rule["exact"]
    if "one_of" in rule:
        return min(rule["one_of"])
    return rule.get("min", 0)


def _as_bytes(value, name):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    raise TypeError(f"{name} must be bytes")


def _int_value(field, value):
    name = field["name"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    low, high = _INT_LIMITS[field["type"]]
    if not low <= value <= high:
        raise ValueError(f"{name} {value} does not fit {field['type']}")
    if "range" in field and not field["range"][0] <= value <= field["range"][1]:
        raise ValueError(f"{name} {value} is outside {field['range'][0]}..{field['range'][1]}")
    if "allowed" in field and value not in field["allowed"]:
        raise ValueError(f"{name} {value} is not one of the defined values")
    return value


def encode(layout, **values):
    """Build (identifier, payload) for a layout. Rejects anything out of range instead of clamping it."""
    spec = LAYOUTS[layout]
    fields = spec["fields"]
    names = {f["name"] for f in fields}
    unknown = set(values) - names
    if unknown:
        raise TypeError(f"unknown field(s) for {layout}: {', '.join(sorted(unknown))}")
    derived = {f["length_field"]: f["name"] for f in fields if "length_field" in f}
    out = bytearray()
    skipped = False
    byte_values = {}
    for field in fields:
        if field["type"] == "bytes":
            if field["name"] in values:
                raw = _as_bytes(values[field["name"]], field["name"])
            elif "fixed" in field:
                raw = bytes.fromhex(field["fixed"])
            elif field.get("optional"):
                raw = None
            else:
                raise TypeError(f"missing field {field['name']}")
            if raw is not None:
                if "fixed" in field and raw != bytes.fromhex(field["fixed"]):
                    raise ValueError(f"{field['name']} must be {field['fixed']}")
                if "length" in field and len(raw) != field["length"]:
                    raise ValueError(f"{field['name']} must be {field['length']} bytes")
                byte_values[field["name"]] = raw
    for field in fields:
        name = field["name"]
        if field["type"] == "bytes":
            raw = byte_values.get(name)
            if raw is None:
                skipped = True
                continue
            if skipped:
                raise ValueError(f"{name} follows an omitted optional field")
            out += raw
            continue
        if name in derived:
            value = len(byte_values[derived[name]])
            if name in values and values[name] != value:
                raise ValueError(f"{name} must equal the length of {derived[name]}")
        elif name in values and values[name] is not None:
            value = values[name]
        elif field.get("optional"):
            skipped = True
            continue
        else:
            raise TypeError(f"missing field {name}")
        if skipped:
            raise ValueError(f"{name} follows an omitted optional field")
        value = _int_value(field, value)
        out += value.to_bytes(_WIDTHS[field["type"]], "big", signed=field["type"].startswith("i"))
    if not dlc_allows(spec["dlc"], len(out)):
        raise ValueError(f"{layout}: a payload of {len(out)} bytes does not satisfy the length rule {spec['dlc']}")
    return spec["id"], bytes(out)


def decode(layout, data, strict=False):
    """Read a payload. None when it is too short (or, with strict, when it does not satisfy the length rule).

    Optional fields that the payload is too short to hold are None: not reported, never zero.
    Extra trailing bytes are ignored unless strict. Values are reported as received, never range-checked.
    """
    spec = LAYOUTS[layout]
    data = bytes(data)
    length = len(data)
    if strict and not dlc_allows(spec["dlc"], length):
        return None
    if length < _dlc_floor(spec["dlc"]):
        return None
    result = {}
    for field in spec["fields"]:
        name = field["name"]
        offset = field["offset"]
        if field["type"] == "bytes":
            if "length_field" in field:
                size = result[field["length_field"]]
                if length - offset < size:
                    return None
                result[name] = data[offset:offset + size]
            elif "length" in field:
                if length < offset + field["length"]:
                    if field.get("optional"):
                        result[name] = None
                        continue
                    return None
                result[name] = data[offset:offset + field["length"]]
            else:
                result[name] = data[offset:]
            continue
        width = _WIDTHS[field["type"]]
        needed = field.get("present_from_dlc", offset + width)
        if length < needed or length < offset + width:
            if field.get("optional"):
                result[name] = None
                continue
            return None
        result[name] = int.from_bytes(data[offset:offset + width], "big", signed=field["type"].startswith("i"))
    return result


def minor_field_pack(minor, patch=None):
    """The 16-bit minor field of the end-of-update frame: legacy, or 0x80 | patch in the high byte."""
    if patch is None or patch == PATCH_UNKNOWN or not 0 <= patch <= PATCH_MAX:
        return minor
    return ((PATCH_FLAG | patch) << 8) | (minor & 0xFF)


def minor_field_minor(field):
    return field & 0xFF


def minor_field_patch(field):
    """The patch carried by a minor field, or None for a legacy field."""
    high = (field >> 8) & 0xFF
    return (high & PATCH_MAX) if high & PATCH_FLAG else None


def version_compare(installed, candidate):
    """Order of a candidate against the installed version, each (major, minor, patch or None).

    1 when the candidate is newer, 0 when equal, -1 when older. Major and minor decide; the patch only
    when both versions carry one.
    """
    for left, right in zip(installed[:2], candidate[:2]):
        if right != left:
            return 1 if right > left else -1
    if installed[2] is None or candidate[2] is None:
        return 0
    if candidate[2] != installed[2]:
        return 1 if candidate[2] > installed[2] else -1
    return 0

# ---------------------------------------------------------------------------
# one builder and one parser per layout
# ---------------------------------------------------------------------------
def encode_impact_event(event: int) -> tuple[int, bytes]:
    """Impact register (touch probe, maximum priority) (0x095, response)."""
    return encode("impact_event", event=event)


def decode_impact_event(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x095 (response), or None when the payload is too short."""
    return decode("impact_event", data, strict)


def encode_global_status(status_r: int, status_g: int, status_b: int, display_mode: int, ring_r: int, ring_g: int, ring_b: int, ring_on: int) -> tuple[int, bytes]:
    """Status LED, ring LED and OLED mode (0x100, request)."""
    return encode("global_status", status_r=status_r, status_g=status_g, status_b=status_b, display_mode=display_mode, ring_r=ring_r, ring_g=ring_g, ring_b=ring_b, ring_on=ring_on)


def decode_global_status(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x100 (request), or None when the payload is too short."""
    return decode("global_status", data, strict)


def encode_query_active_tool() -> tuple[int, bytes]:
    """Query the active tool and the quick state: the frame the host sends (0x110)."""
    return encode("query_active_tool")


def decode_query_active_tool(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x110 (request), or None when the payload is too short."""
    return decode("query_active_tool", data, strict)


def encode_active_tool_resp(tool_id: int, system_error: int, can_error: int, booting: int, thermal_fault: int | None = None, reset_cause: int | None = None) -> tuple[int, bytes]:
    """Active tool and quick state (0x111, response)."""
    values = {k: v for k, v in dict(tool_id=tool_id, system_error=system_error, can_error=can_error, booting=booting, thermal_fault=thermal_fault, reset_cause=reset_cause).items() if v is not None}
    return encode("active_tool_resp", **values)


def decode_active_tool_resp(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x111 (response), or None when the payload is too short."""
    return decode("active_tool_resp", data, strict)


def encode_motion_cmd(direction: int, steps: int) -> tuple[int, bytes]:
    """Plain stepper move (direction and step count) (0x120, request)."""
    return encode("motion_cmd", direction=direction, steps=steps)


def decode_motion_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x120 (request), or None when the payload is too short."""
    return decode("motion_cmd", data, strict)


def encode_solder_setpoint(setpoint_c: int) -> tuple[int, bytes]:
    """T12 setpoint temperature (0x130, request)."""
    return encode("solder_setpoint", setpoint_c=setpoint_c)


def decode_solder_setpoint(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x130 (request), or None when the payload is too short."""
    return decode("solder_setpoint", data, strict)


def encode_solder_feeder_reset(magic: bytes | None = None) -> tuple[int, bytes]:
    """Reset the solder wire feeder position (0x131, request)."""
    values = {k: v for k, v in dict(magic=magic).items() if v is not None}
    return encode("solder_feeder_reset", **values)


def decode_solder_feeder_reset(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x131 (request), or None when the payload is too short."""
    return decode("solder_feeder_reset", data, strict)


def encode_solder_feeder_pos_request() -> tuple[int, bytes]:
    """Solder wire feeder position: the frame the host sends (0x132)."""
    return encode("solder_feeder_pos_request")


def decode_solder_feeder_pos_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x132 (request), or None when the payload is too short."""
    return decode("solder_feeder_pos_request", data, strict)


def encode_solder_feeder_pos_response(position: int) -> tuple[int, bytes]:
    """Solder wire feeder position (0x132, response)."""
    return encode("solder_feeder_pos_response", position=position)


def decode_solder_feeder_pos_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x132 (response), or None when the payload is too short."""
    return decode("solder_feeder_pos_response", data, strict)


def encode_solder_telemetry(temperature_c: int) -> tuple[int, bytes]:
    """T12 temperature telemetry (0x135, response)."""
    return encode("solder_telemetry", temperature_c=temperature_c)


def decode_solder_telemetry(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x135 (response), or None when the payload is too short."""
    return decode("solder_telemetry", data, strict)


def encode_drill_cmd(speed: int, direction: int) -> tuple[int, bytes]:
    """Drill speed and direction (0x140, request)."""
    return encode("drill_cmd", speed=speed, direction=direction)


def decode_drill_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x140 (request), or None when the payload is too short."""
    return decode("drill_cmd", data, strict)


def encode_vacuum_telemetry(adc: int, detected: int) -> tuple[int, bytes]:
    """Vacuum pickup telemetry (0x145, response)."""
    return encode("vacuum_telemetry", adc=adc, detected=detected)


def decode_vacuum_telemetry(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x145 (response), or None when the payload is too short."""
    return decode("vacuum_telemetry", data, strict)


def encode_drill_telemetry(rpm: int, endstop: int) -> tuple[int, bytes]:
    """Drill RPM and endstop telemetry (0x147, response)."""
    return encode("drill_telemetry", rpm=rpm, endstop=endstop)


def decode_drill_telemetry(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x147 (response), or None when the payload is too short."""
    return decode("drill_telemetry", data, strict)


def encode_aoi_cmd(mode: int, strobe_period_ms: int) -> tuple[int, bytes]:
    """AOI ring light mode and strobe period (0x150, request)."""
    return encode("aoi_cmd", mode=mode, strobe_period_ms=strobe_period_ms)


def decode_aoi_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x150 (request), or None when the payload is too short."""
    return decode("aoi_cmd", data, strict)


def encode_aoi_telemetry(endstop: int) -> tuple[int, bytes]:
    """AOI endstop telemetry (0x155, response)."""
    return encode("aoi_telemetry", endstop=endstop)


def decode_aoi_telemetry(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x155 (response), or None when the payload is too short."""
    return decode("aoi_telemetry", data, strict)


def encode_laser_cmd(power: int, interlock: int) -> tuple[int, bytes]:
    """Laser power and interlock (0x160, request)."""
    return encode("laser_cmd", power=power, interlock=interlock)


def decode_laser_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x160 (request), or None when the payload is too short."""
    return decode("laser_cmd", data, strict)


def encode_laser_telemetry(endstop: int) -> tuple[int, bytes]:
    """Laser endstop telemetry (0x165, response)."""
    return encode("laser_telemetry", endstop=endstop)


def decode_laser_telemetry(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x165 (response), or None when the payload is too short."""
    return decode("laser_telemetry", data, strict)


def encode_printer_thermal_motion(nozzle_setpoint_c: int, extruder_direction: int, extruder_steps: int) -> tuple[int, bytes]:
    """Nozzle setpoint and extruder motion (0x170, request)."""
    return encode("printer_thermal_motion", nozzle_setpoint_c=nozzle_setpoint_c, extruder_direction=extruder_direction, extruder_steps=extruder_steps)


def decode_printer_thermal_motion(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x170 (request), or None when the payload is too short."""
    return decode("printer_thermal_motion", data, strict)


def encode_printer_layerfan_cmd(power: int) -> tuple[int, bytes]:
    """Layer fan power (0x173, request)."""
    return encode("printer_layerfan_cmd", power=power)


def decode_printer_layerfan_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x173 (request), or None when the payload is too short."""
    return decode("printer_layerfan_cmd", data, strict)


def encode_printer_hotend_telemetry(temperature_c: int) -> tuple[int, bytes]:
    """Hotend temperature telemetry (0x175, response)."""
    return encode("printer_hotend_telemetry", temperature_c=temperature_c)


def decode_printer_hotend_telemetry(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x175 (response), or None when the payload is too short."""
    return decode("printer_hotend_telemetry", data, strict)


def encode_printer_layerfan_rpm(rpm: int) -> tuple[int, bytes]:
    """Layer fan RPM telemetry (0x177, response)."""
    return encode("printer_layerfan_rpm", rpm=rpm)


def decode_printer_layerfan_rpm(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x177 (response), or None when the payload is too short."""
    return decode("printer_layerfan_rpm", data, strict)


def encode_printer_hotendfan_cmd(power: int) -> tuple[int, bytes]:
    """Hotend fan power (0x178, request)."""
    return encode("printer_hotendfan_cmd", power=power)


def decode_printer_hotendfan_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x178 (request), or None when the payload is too short."""
    return decode("printer_hotendfan_cmd", data, strict)


def encode_printer_hotendfan_rpm(rpm: int) -> tuple[int, bytes]:
    """Hotend fan RPM telemetry (0x179, response)."""
    return encode("printer_hotendfan_rpm", rpm=rpm)


def decode_printer_hotendfan_rpm(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x179 (response), or None when the payload is too short."""
    return decode("printer_hotendfan_rpm", data, strict)


def encode_expansion_spi_req(data: bytes) -> tuple[int, bytes]:
    """Expansion SPI passthrough request (0x180, request)."""
    return encode("expansion_spi_req", data=data)


def decode_expansion_spi_req(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x180 (request), or None when the payload is too short."""
    return decode("expansion_spi_req", data, strict)


def encode_expansion_spi_resp(data: bytes) -> tuple[int, bytes]:
    """Expansion SPI passthrough response (0x181, response)."""
    return encode("expansion_spi_resp", data=data)


def decode_expansion_spi_resp(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x181 (response), or None when the payload is too short."""
    return decode("expansion_spi_resp", data, strict)


def encode_expansion_diag0_req() -> tuple[int, bytes]:
    """Query the TMC_DIAG0 level: the frame the host sends (0x182)."""
    return encode("expansion_diag0_req")


def decode_expansion_diag0_req(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x182 (request), or None when the payload is too short."""
    return decode("expansion_diag0_req", data, strict)


def encode_expansion_diag0_resp(level: int) -> tuple[int, bytes]:
    """TMC_DIAG0 level (0x183, response)."""
    return encode("expansion_diag0_resp", level=level)


def decode_expansion_diag0_resp(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x183 (response), or None when the payload is too short."""
    return decode("expansion_diag0_resp", data, strict)


def encode_fram_query() -> tuple[int, bytes]:
    """Query the recovered persisted state: the frame the host sends (0x190)."""
    return encode("fram_query")


def decode_fram_query(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x190 (request), or None when the payload is too short."""
    return decode("fram_query", data, strict)


def encode_fram_state_resp(valid: int, tool_id: int, had_error: int, setpoint_c: int, speed: int, dir_or_interlock: int, fan: int) -> tuple[int, bytes]:
    """Recovered persisted state (0x191, response)."""
    return encode("fram_state_resp", valid=valid, tool_id=tool_id, had_error=had_error, setpoint_c=setpoint_c, speed=speed, dir_or_interlock=dir_or_interlock, fan=fan)


def decode_fram_state_resp(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x191 (response), or None when the payload is too short."""
    return decode("fram_state_resp", data, strict)


def encode_erase_fram(magic: bytes | None = None) -> tuple[int, bytes]:
    """Erase the recovered persisted state (0x192, request)."""
    values = {k: v for k, v in dict(magic=magic).items() if v is not None}
    return encode("erase_fram", **values)


def decode_erase_fram(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x192 (request), or None when the payload is too short."""
    return decode("erase_fram", data, strict)


def encode_set_expansion_type(board_type: int) -> tuple[int, bytes]:
    """Set the expansion board type (0x1A0, request)."""
    return encode("set_expansion_type", board_type=board_type)


def decode_set_expansion_type(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A0 (request), or None when the payload is too short."""
    return decode("set_expansion_type", data, strict)


def encode_expansion_type_resp_request() -> tuple[int, bytes]:
    """Expansion board type (query and response): the frame the host sends (0x1A1)."""
    return encode("expansion_type_resp_request")


def decode_expansion_type_resp_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A1 (request), or None when the payload is too short."""
    return decode("expansion_type_resp_request", data, strict)


def encode_expansion_type_resp_response(board_type: int) -> tuple[int, bytes]:
    """Expansion board type (query and response) (0x1A1, response)."""
    return encode("expansion_type_resp_response", board_type=board_type)


def decode_expansion_type_resp_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A1 (response), or None when the payload is too short."""
    return decode("expansion_type_resp_response", data, strict)


def encode_set_free_tool(selection: int) -> tuple[int, bytes]:
    """Set the free tool configuration (0x1A2, request)."""
    return encode("set_free_tool", selection=selection)


def decode_set_free_tool(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A2 (request), or None when the payload is too short."""
    return decode("set_free_tool", data, strict)


def encode_free_tool_config_resp_request() -> tuple[int, bytes]:
    """Raw jumper reading and free tool configuration: the frame the host sends (0x1A3)."""
    return encode("free_tool_config_resp_request")


def decode_free_tool_config_resp_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A3 (request), or None when the payload is too short."""
    return decode("free_tool_config_resp_request", data, strict)


def encode_free_tool_config_resp_response(jumper_reading: int, selection: int) -> tuple[int, bytes]:
    """Raw jumper reading and free tool configuration (0x1A3, response)."""
    return encode("free_tool_config_resp_response", jumper_reading=jumper_reading, selection=selection)


def decode_free_tool_config_resp_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A3 (response), or None when the payload is too short."""
    return decode("free_tool_config_resp_response", data, strict)


def encode_set_device_serial(serial: int) -> tuple[int, bytes]:
    """Set the device serial number (0x1A4, request)."""
    return encode("set_device_serial", serial=serial)


def decode_set_device_serial(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A4 (request), or None when the payload is too short."""
    return decode("set_device_serial", data, strict)


def encode_peripheral_info_resp_request() -> tuple[int, bytes]:
    """Peripheral type and device serial: the frame the host sends (0x1A5)."""
    return encode("peripheral_info_resp_request")


def decode_peripheral_info_resp_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A5 (request), or None when the payload is too short."""
    return decode("peripheral_info_resp_request", data, strict)


def encode_peripheral_info_resp_response(peripheral_type: int, serial: int) -> tuple[int, bytes]:
    """Peripheral type and device serial (0x1A5, response)."""
    return encode("peripheral_info_resp_response", peripheral_type=peripheral_type, serial=serial)


def decode_peripheral_info_resp_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A5 (response), or None when the payload is too short."""
    return decode("peripheral_info_resp_response", data, strict)


def encode_set_mlx_variant(variant: int) -> tuple[int, bytes]:
    """Set the MLX9064x sensor variant (0x1A6, request)."""
    return encode("set_mlx_variant", variant=variant)


def decode_set_mlx_variant(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A6 (request), or None when the payload is too short."""
    return decode("set_mlx_variant", data, strict)


def encode_mlx_variant_resp_request() -> tuple[int, bytes]:
    """MLX9064x sensor variant (query and response): the frame the host sends (0x1A7)."""
    return encode("mlx_variant_resp_request")


def decode_mlx_variant_resp_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A7 (request), or None when the payload is too short."""
    return decode("mlx_variant_resp_request", data, strict)


def encode_mlx_variant_resp_response(variant: int) -> tuple[int, bytes]:
    """MLX9064x sensor variant (query and response) (0x1A7, response)."""
    return encode("mlx_variant_resp_response", variant=variant)


def decode_mlx_variant_resp_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A7 (response), or None when the payload is too short."""
    return decode("mlx_variant_resp_response", data, strict)


def encode_blackbox_query(chunk_index: int) -> tuple[int, bytes]:
    """Request one chunk of the fault recorder (0x1A8, request)."""
    return encode("blackbox_query", chunk_index=chunk_index)


def decode_blackbox_query(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A8 (request), or None when the payload is too short."""
    return decode("blackbox_query", data, strict)


def encode_blackbox_chunk(data: bytes) -> tuple[int, bytes]:
    """One chunk of the fault recorder (0x1A9, response)."""
    return encode("blackbox_chunk", data=data)


def decode_blackbox_chunk(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1A9 (response), or None when the payload is too short."""
    return decode("blackbox_chunk", data, strict)


def encode_thermal_stats_query() -> tuple[int, bytes]:
    """Query the lifetime thermal counters: the frame the host sends (0x1AA)."""
    return encode("thermal_stats_query")


def decode_thermal_stats_query(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1AA (request), or None when the payload is too short."""
    return decode("thermal_stats_query", data, strict)


def encode_thermal_stats_resp(fault_count: int, heater_on_seconds: int, last_fault: int, persisted: int) -> tuple[int, bytes]:
    """Lifetime thermal counters (0x1AB, response)."""
    return encode("thermal_stats_resp", fault_count=fault_count, heater_on_seconds=heater_on_seconds, last_fault=last_fault, persisted=persisted)


def decode_thermal_stats_resp(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1AB (response), or None when the payload is too short."""
    return decode("thermal_stats_resp", data, strict)


def encode_electromagnet_cmd(coil: int) -> tuple[int, bytes]:
    """Electromagnet coil (0x1B0, request)."""
    return encode("electromagnet_cmd", coil=coil)


def decode_electromagnet_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1B0 (request), or None when the payload is too short."""
    return decode("electromagnet_cmd", data, strict)


def encode_spot_weld_cmd(fire: int, duration_ms: int) -> tuple[int, bytes]:
    """Spot welder timed pulse (0x1C0, request)."""
    return encode("spot_weld_cmd", fire=fire, duration_ms=duration_ms)


def decode_spot_weld_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1C0 (request), or None when the payload is too short."""
    return decode("spot_weld_cmd", data, strict)


def encode_uv_curing_cmd(duty: int) -> tuple[int, bytes]:
    """UV curing LED duty (0x1D0, request)."""
    return encode("uv_curing_cmd", duty=duty)


def decode_uv_curing_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1D0 (request), or None when the payload is too short."""
    return decode("uv_curing_cmd", data, strict)


def encode_hotair_cmd(setpoint_c: int, blower_duty: int) -> tuple[int, bytes]:
    """Hot-air nozzle setpoint and blower duty (0x1E0, request)."""
    return encode("hotair_cmd", setpoint_c=setpoint_c, blower_duty=blower_duty)


def decode_hotair_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1E0 (request), or None when the payload is too short."""
    return decode("hotair_cmd", data, strict)


def encode_crimping_cmd(direction: int, steps: int) -> tuple[int, bytes]:
    """Crimping actuator motor (0x1F0, request)."""
    return encode("crimping_cmd", direction=direction, steps=steps)


def decode_crimping_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x1F0 (request), or None when the payload is too short."""
    return decode("crimping_cmd", data, strict)


def encode_ultrasonic_weld_cmd(fire: int, duration_ms: int) -> tuple[int, bytes]:
    """Ultrasonic welder timed pulse (0x200, request)."""
    return encode("ultrasonic_weld_cmd", fire=fire, duration_ms=duration_ms)


def decode_ultrasonic_weld_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x200 (request), or None when the payload is too short."""
    return decode("ultrasonic_weld_cmd", data, strict)


def encode_slave_enter_bootloader(magic: bytes | None = None) -> tuple[int, bytes]:
    """Enter the expansion slave's bootloader (0x210, request)."""
    values = {k: v for k, v in dict(magic=magic).items() if v is not None}
    return encode("slave_enter_bootloader", **values)


def decode_slave_enter_bootloader(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x210 (request), or None when the payload is too short."""
    return decode("slave_enter_bootloader", data, strict)


def encode_slave_start_update(total_size: int, hardware_id: int) -> tuple[int, bytes]:
    """Start the slave firmware update (0x211, request)."""
    return encode("slave_start_update", total_size=total_size, hardware_id=hardware_id)


def decode_slave_start_update(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x211 (request), or None when the payload is too short."""
    return decode("slave_start_update", data, strict)


def encode_slave_hmac_chunk(hmac_part: bytes) -> tuple[int, bytes]:
    """Slave HMAC-SHA256 signature chunk (0x212, request)."""
    return encode("slave_hmac_chunk", hmac_part=hmac_part)


def decode_slave_hmac_chunk(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x212 (request), or None when the payload is too short."""
    return decode("slave_hmac_chunk", data, strict)


def encode_slave_data(data: bytes) -> tuple[int, bytes]:
    """Slave firmware data (0x213, request)."""
    return encode("slave_data", data=data)


def decode_slave_data(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x213 (request), or None when the payload is too short."""
    return decode("slave_data", data, strict)


def encode_slave_end_update(crc32: int, version_major: int, version_minor_field: int) -> tuple[int, bytes]:
    """End the slave update and verify (0x214, request)."""
    return encode("slave_end_update", crc32=crc32, version_major=version_major, version_minor_field=version_minor_field)


def decode_slave_end_update(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x214 (request), or None when the payload is too short."""
    return decode("slave_end_update", data, strict)


def encode_slave_status_request() -> tuple[int, bytes]:
    """Slave bootloader status: the frame the host sends (0x215)."""
    return encode("slave_status_request")


def decode_slave_status_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x215 (request), or None when the payload is too short."""
    return decode("slave_status_request", data, strict)


def encode_slave_status_response(status: int) -> tuple[int, bytes]:
    """Slave bootloader status (0x215, response)."""
    return encode("slave_status_response", status=status)


def decode_slave_status_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x215 (response), or None when the payload is too short."""
    return decode("slave_status_response", data, strict)


def encode_slave_progress_request() -> tuple[int, bytes]:
    """Slave update progress: the frame the host sends (0x216)."""
    return encode("slave_progress_request")


def decode_slave_progress_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x216 (request), or None when the payload is too short."""
    return decode("slave_progress_request", data, strict)


def encode_slave_progress_response(progress: int) -> tuple[int, bytes]:
    """Slave update progress (0x216, response)."""
    return encode("slave_progress_response", progress=progress)


def decode_slave_progress_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x216 (response), or None when the payload is too short."""
    return decode("slave_progress_response", data, strict)


def encode_slave_version_resp_1_request() -> tuple[int, bytes]:
    """Slave bootloader version, part 1: the frame the host sends (0x217)."""
    return encode("slave_version_resp_1_request")


def decode_slave_version_resp_1_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x217 (request), or None when the payload is too short."""
    return decode("slave_version_resp_1_request", data, strict)


def encode_slave_version_resp_1_response(responder: int, hardware_id: int, version_major: int, version_minor_high: int) -> tuple[int, bytes]:
    """Slave bootloader version, part 1 (0x217, response)."""
    return encode("slave_version_resp_1_response", responder=responder, hardware_id=hardware_id, version_major=version_major, version_minor_high=version_minor_high)


def decode_slave_version_resp_1_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x217 (response), or None when the payload is too short."""
    return decode("slave_version_resp_1_response", data, strict)


def encode_slave_version_resp_2(version_minor_low: int, bootloader_major: int, app_patch: int | None = None, bootloader_minor: int | None = None, bootloader_patch: int | None = None) -> tuple[int, bytes]:
    """Slave bootloader version, part 2 (0x218, response)."""
    values = {k: v for k, v in dict(version_minor_low=version_minor_low, bootloader_major=bootloader_major, app_patch=app_patch, bootloader_minor=bootloader_minor, bootloader_patch=bootloader_patch).items() if v is not None}
    return encode("slave_version_resp_2", **values)


def decode_slave_version_resp_2(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x218 (response), or None when the payload is too short."""
    return decode("slave_version_resp_2", data, strict)


def encode_slave_verify_fail_reason_request() -> tuple[int, bytes]:
    """Slave verify-fail reason: the frame the host sends (0x219)."""
    return encode("slave_verify_fail_reason_request")


def decode_slave_verify_fail_reason_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x219 (request), or None when the payload is too short."""
    return decode("slave_verify_fail_reason_request", data, strict)


def encode_slave_verify_fail_reason_response(reason: int) -> tuple[int, bytes]:
    """Slave verify-fail reason (0x219, response)."""
    return encode("slave_verify_fail_reason_response", reason=reason)


def decode_slave_verify_fail_reason_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x219 (response), or None when the payload is too short."""
    return decode("slave_verify_fail_reason_response", data, strict)


def encode_slave_reg_write(register: int, payload: bytes) -> tuple[int, bytes]:
    """Write a slave application register (generic) (0x220, request)."""
    return encode("slave_reg_write", register=register, payload=payload)


def decode_slave_reg_write(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x220 (request), or None when the payload is too short."""
    return decode("slave_reg_write", data, strict)


def encode_slave_reg_read_request(register: int, length: int) -> tuple[int, bytes]:
    """Read a slave application register (generic) (0x221, request)."""
    return encode("slave_reg_read_request", register=register, length=length)


def decode_slave_reg_read_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x221 (request), or None when the payload is too short."""
    return decode("slave_reg_read_request", data, strict)


def encode_slave_reg_read_response(data: bytes) -> tuple[int, bytes]:
    """Read a slave application register (generic) (0x221, response)."""
    return encode("slave_reg_read_response", data=data)


def decode_slave_reg_read_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x221 (response), or None when the payload is too short."""
    return decode("slave_reg_read_response", data, strict)


def encode_paste_jetting_config(channel: int, frequency_hz: int) -> tuple[int, bytes]:
    """Local PWM configuration (0x230, request)."""
    return encode("paste_jetting_config", channel=channel, frequency_hz=frequency_hz)


def decode_paste_jetting_config(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x230 (request), or None when the payload is too short."""
    return decode("paste_jetting_config", data, strict)


def encode_paste_jetting_pulse(channel: int, duty_percent: int, duration_ms: int) -> tuple[int, bytes]:
    """Local PWM pulse (0x231, request)."""
    return encode("paste_jetting_pulse", channel=channel, duty_percent=duty_percent, duration_ms=duration_ms)


def decode_paste_jetting_pulse(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x231 (request), or None when the payload is too short."""
    return decode("paste_jetting_pulse", data, strict)


def encode_ads1115_config(config: int) -> tuple[int, bytes]:
    """ADS1115 configuration (0x240, request)."""
    return encode("ads1115_config", config=config)


def decode_ads1115_config(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x240 (request), or None when the payload is too short."""
    return decode("ads1115_config", data, strict)


def encode_ads1115_trigger() -> tuple[int, bytes]:
    """ADS1115 trigger a conversion: the frame the host sends (0x241)."""
    return encode("ads1115_trigger")


def decode_ads1115_trigger(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x241 (request), or None when the payload is too short."""
    return decode("ads1115_trigger", data, strict)


def encode_ads1115_result_request() -> tuple[int, bytes]:
    """ADS1115 conversion result (query and response): the frame the host sends (0x242)."""
    return encode("ads1115_result_request")


def decode_ads1115_result_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x242 (request), or None when the payload is too short."""
    return decode("ads1115_result_request", data, strict)


def encode_ads1115_result_response(raw: int) -> tuple[int, bytes]:
    """ADS1115 conversion result (query and response) (0x242, response)."""
    return encode("ads1115_result_response", raw=raw)


def decode_ads1115_result_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x242 (response), or None when the payload is too short."""
    return decode("ads1115_result_response", data, strict)


def encode_flying_probe_basic(adc: int) -> tuple[int, bytes]:
    """Basic-mode onboard ADC reading (0x243, response)."""
    return encode("flying_probe_basic", adc=adc)


def decode_flying_probe_basic(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x243 (response), or None when the payload is too short."""
    return decode("flying_probe_basic", data, strict)


def encode_thermal_trigger() -> tuple[int, bytes]:
    """Trigger a thermal capture: the frame the host sends (0x250)."""
    return encode("thermal_trigger")


def decode_thermal_trigger(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x250 (request), or None when the payload is too short."""
    return decode("thermal_trigger", data, strict)


def encode_thermal_status_request() -> tuple[int, bytes]:
    """Thermal capture status (query and response): the frame the host sends (0x251)."""
    return encode("thermal_status_request")


def decode_thermal_status_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x251 (request), or None when the payload is too short."""
    return decode("thermal_status_request", data, strict)


def encode_thermal_status_response(status: int) -> tuple[int, bytes]:
    """Thermal capture status (query and response) (0x251, response)."""
    return encode("thermal_status_response", status=status)


def decode_thermal_status_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x251 (response), or None when the payload is too short."""
    return decode("thermal_status_response", data, strict)


def encode_thermal_raw_chunk_req(chunk: int) -> tuple[int, bytes]:
    """Request a raw pixel chunk (0x252, request)."""
    return encode("thermal_raw_chunk_req", chunk=chunk)


def decode_thermal_raw_chunk_req(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x252 (request), or None when the payload is too short."""
    return decode("thermal_raw_chunk_req", data, strict)


def encode_thermal_raw_chunk(data: bytes) -> tuple[int, bytes]:
    """Raw pixel chunk data (0x253, response)."""
    return encode("thermal_raw_chunk", data=data)


def decode_thermal_raw_chunk(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x253 (response), or None when the payload is too short."""
    return decode("thermal_raw_chunk", data, strict)


def encode_thermal_cal_chunk_req(chunk: int) -> tuple[int, bytes]:
    """Request a calibrated temperature chunk (0x254, request)."""
    return encode("thermal_cal_chunk_req", chunk=chunk)


def decode_thermal_cal_chunk_req(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x254 (request), or None when the payload is too short."""
    return decode("thermal_cal_chunk_req", data, strict)


def encode_thermal_cal_chunk(data: bytes) -> tuple[int, bytes]:
    """Calibrated temperature chunk data (0x255, response)."""
    return encode("thermal_cal_chunk", data=data)


def decode_thermal_cal_chunk(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x255 (response), or None when the payload is too short."""
    return decode("thermal_cal_chunk", data, strict)


def encode_version_patch_response(responder: int, patch: int, flags: int) -> tuple[int, bytes]:
    """Version patch response (0x7E9, response)."""
    return encode("version_patch_response", responder=responder, patch=patch, flags=flags)


def decode_version_patch_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7E9 (response), or None when the payload is too short."""
    return decode("version_patch_response", data, strict)


def encode_enter_bootloader(magic: bytes | None = None) -> tuple[int, bytes]:
    """Enter the bootloader (0x7F0, request)."""
    values = {k: v for k, v in dict(magic=magic).items() if v is not None}
    return encode("enter_bootloader", **values)


def decode_enter_bootloader(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7F0 (request), or None when the payload is too short."""
    return decode("enter_bootloader", data, strict)


def encode_start_update(total_size: int, hardware_id: int) -> tuple[int, bytes]:
    """Start the firmware update (0x7F1, request)."""
    return encode("start_update", total_size=total_size, hardware_id=hardware_id)


def decode_start_update(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7F1 (request), or None when the payload is too short."""
    return decode("start_update", data, strict)


def encode_data(data: bytes) -> tuple[int, bytes]:
    """Firmware data (0x7F2, request)."""
    return encode("data", data=data)


def decode_data(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7F2 (request), or None when the payload is too short."""
    return decode("data", data, strict)


def encode_page_ack(page_index: int) -> tuple[int, bytes]:
    """Page written acknowledgement (0x7F3, response)."""
    return encode("page_ack", page_index=page_index)


def decode_page_ack(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7F3 (response), or None when the payload is too short."""
    return decode("page_ack", data, strict)


def encode_end_update(crc32: int, version_major: int, version_minor_field: int) -> tuple[int, bytes]:
    """End the update and verify (0x7F4, request)."""
    return encode("end_update", crc32=crc32, version_major=version_major, version_minor_field=version_minor_field)


def decode_end_update(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7F4 (request), or None when the payload is too short."""
    return decode("end_update", data, strict)


def encode_status(status: int, reason: int | None = None) -> tuple[int, bytes]:
    """Bootloader status (0x7F5, response)."""
    values = {k: v for k, v in dict(status=status, reason=reason).items() if v is not None}
    return encode("status", **values)


def decode_status(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7F5 (response), or None when the payload is too short."""
    return decode("status", data, strict)


def encode_heartbeat(status: int, progress: int) -> tuple[int, bytes]:
    """Bootloader heartbeat (0x7F6, response)."""
    return encode("heartbeat", status=status, progress=progress)


def decode_heartbeat(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7F6 (response), or None when the payload is too short."""
    return decode("heartbeat", data, strict)


def encode_hmac_chunk(hmac_part: bytes) -> tuple[int, bytes]:
    """HMAC-SHA256 signature chunk (0x7F7, request)."""
    return encode("hmac_chunk", hmac_part=hmac_part)


def decode_hmac_chunk(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7F7 (request), or None when the payload is too short."""
    return decode("hmac_chunk", data, strict)


def encode_query_version() -> tuple[int, bytes]:
    """Query the version: the frame the host sends (0x7F8)."""
    return encode("query_version")


def decode_query_version(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7F8 (request), or None when the payload is too short."""
    return decode("query_version", data, strict)


def encode_version_response(responder: int, hardware_id: int, version_major: int, version_minor: int) -> tuple[int, bytes]:
    """Version response (0x7F9, response)."""
    return encode("version_response", responder=responder, hardware_id=hardware_id, version_major=version_major, version_minor=version_minor)


def decode_version_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7F9 (response), or None when the payload is too short."""
    return decode("version_response", data, strict)


def encode_bootloader_version_response(major: int, minor: int, patch: int) -> tuple[int, bytes]:
    """Bootloader's own version (0x7FA, response)."""
    return encode("bootloader_version_response", major=major, minor=minor, patch=patch)


def decode_bootloader_version_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7FA (response), or None when the payload is too short."""
    return decode("bootloader_version_response", data, strict)


def encode_query_error_counters() -> tuple[int, bytes]:
    """Query the CAN error counters: the frame the host sends (0x7FB)."""
    return encode("query_error_counters")


def decode_query_error_counters(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7FB (request), or None when the payload is too short."""
    return decode("query_error_counters", data, strict)


def encode_error_counters_response(tec: int, rec: int) -> tuple[int, bytes]:
    """CAN error counters (0x7FC, response)."""
    return encode("error_counters_response", tec=tec, rec=rec)


def decode_error_counters_response(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7FC (response), or None when the payload is too short."""
    return decode("error_counters_response", data, strict)


def encode_authorize_downgrade(magic: bytes | None = None) -> tuple[int, bytes]:
    """Authorise a downgrade for the current update (0x7FD, request)."""
    values = {k: v for k, v in dict(magic=magic).items() if v is not None}
    return encode("authorize_downgrade", **values)


def decode_authorize_downgrade(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7FD (request), or None when the payload is too short."""
    return decode("authorize_downgrade", data, strict)


def encode_readback_request() -> tuple[int, bytes]:
    """Read back the installed application: the frame the host sends (0x7FE)."""
    return encode("readback_request")


def decode_readback_request(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7FE (request), or None when the payload is too short."""
    return decode("readback_request", data, strict)


def encode_readback_response_size(total_size: int) -> tuple[int, bytes]:
    """Read back the installed application (0x7FE, response, size)."""
    return encode("readback_response_size", total_size=total_size)


def decode_readback_response_size(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7FE (response, size), or None when the payload is too short."""
    return decode("readback_response_size", data, strict)


def encode_readback_response_data(data: bytes) -> tuple[int, bytes]:
    """Read back the installed application (0x7FE, response, data)."""
    return encode("readback_response_data", data=data)


def decode_readback_response_data(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7FE (response, data), or None when the payload is too short."""
    return decode("readback_response_data", data, strict)


def encode_readback_page_ack(page_index: int) -> tuple[int, bytes]:
    """Read-back page acknowledgement (0x7FF, request)."""
    return encode("readback_page_ack", page_index=page_index)


def decode_readback_page_ack(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x7FF (request), or None when the payload is too short."""
    return decode("readback_page_ack", data, strict)


# ---------------------------------------------------------------------------
# multinode extension (designed not implemented in firmware): see docs/MULTINODE.md
# ---------------------------------------------------------------------------
MN_VERSION = 1  # Multinode extension version carried by the discovery frames
MN_ADDRESS_BITS = 5  # Bits of the node address
MN_ADDRESS_MASK = 0x1F  # Mask of the node address
MN_NODE_MAX = 0x20  # Highest number of nodes on one bus
MN_STATUS_PERIOD_MS = 0x3E8  # Period of the per-node status frame (ms)
MN_DISCOVER_SLOT_MS = 2  # Default spacing of the discovery answers: a node answers after its address times this (ms)
MN_NODE_TIMEOUT_MS = 0xDAC  # A node that sent no status frame for this long is treated as gone (ms)
MN_SELECT_TIMEOUT_MS = 0x7D0  # A selection lapses unless the host repeats it within this time (ms)
MN_CMD_ARGS_MAX = 6  # Argument bytes that fit in a node-addressed command (bytes)
MN_STATE_SELECTED = 0x01  # This node is the selected (active) node
MN_STATE_FAULT = 0x02  # A fault is latched on this node
MN_STATE_CONFLICT = 0x04  # Another node answered with the same address: this node ignores commands
MN_STATE_BOOTLOADER = 0x08  # The node runs its bootloader
MN_SELECT_DESELECT_ALL = 0  # No node is selected
MN_SELECT_SELECT = 1  # Select one node
MN_ID_DISCOVER = 0x400  # Ask every node to announce itself
MN_ID_SELECT = 0x401  # Select the one node that the single-head frames address
MN_ID_SAFE_STOP = 0x402  # Ask every node to enter its safe state
MN_ID_NODE_INFO_BASE = 0x420  # A node announces itself (identifier plus the node address) (+ node address, 32 identifiers)
MN_ID_NODE_STATUS_BASE = 0x440  # Periodic status of one node (+ node address, 32 identifiers)
MN_ID_NODE_CMD_BASE = 0x460  # One command to one node without selecting it (+ node address, 32 identifiers)
MN_ID_NODE_RESP_BASE = 0x480  # The answer of one node to NODE_CMD (+ node address, 32 identifiers)
MN_RANGES = {1024: 1, 1025: 1, 1026: 1, 1056: 32, 1088: 32, 1120: 32, 1152: 32}
MN_NAMES = {1024: 'DISCOVER',
 1025: 'SELECT',
 1026: 'SAFE_STOP',
 1056: 'NODE_INFO',
 1088: 'NODE_STATUS',
 1120: 'NODE_CMD',
 1152: 'NODE_RESP'}


def mn_node_id(base: int, node: int) -> int:
    """The identifier of a node-addressed frame: the base of its range plus the node address."""
    if MN_RANGES.get(base, 1) == 1:
        raise ValueError(f"0x{base:03X} is not the base of an addressed range")
    if not isinstance(node, int) or isinstance(node, bool) or not 0 <= node <= MN_ADDRESS_MASK:
        raise ValueError(f"node address {node!r} is outside 0..{MN_ADDRESS_MASK}")
    return base + node


def mn_split_id(can_id: int):
    """(name, node) for an identifier of the extension (node is None for a broadcast frame), or None for any other identifier."""
    for base, span in MN_RANGES.items():
        if base <= can_id < base + span:
            return MN_NAMES[base], (can_id - base if span > 1 else None)
    return None


def encode_mn_discover(mn_version: int, slot_ms: int) -> tuple[int, bytes]:
    """Ask every node to announce itself (0x400, request)."""
    can_id, data = encode("mn_discover", mn_version=mn_version, slot_ms=slot_ms)
    return can_id, data


def decode_mn_discover(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x400, or None when the payload is too short."""
    return decode("mn_discover", data, strict)


def encode_mn_select(action: int, node: int, seq: int) -> tuple[int, bytes]:
    """Select the one node that the single-head frames address (0x401, request)."""
    can_id, data = encode("mn_select", action=action, node=node, seq=seq)
    return can_id, data


def decode_mn_select(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x401, or None when the payload is too short."""
    return decode("mn_select", data, strict)


def encode_mn_safe_stop(reason: int) -> tuple[int, bytes]:
    """Ask every node to enter its safe state (0x402, request)."""
    can_id, data = encode("mn_safe_stop", reason=reason)
    return can_id, data


def decode_mn_safe_stop(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x402, or None when the payload is too short."""
    return decode("mn_safe_stop", data, strict)


def encode_mn_node_info(node: int, tool: int, state: int, instance: int, mn_version: int, serial: int) -> tuple[int, bytes]:
    """A node announces itself (identifier plus the node address) (0x420 + node, response)."""
    can_id, data = encode("mn_node_info", tool=tool, state=state, instance=instance, mn_version=mn_version, serial=serial)
    return mn_node_id(can_id, node), data


def decode_mn_node_info(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x420, or None when the payload is too short."""
    return decode("mn_node_info", data, strict)


def encode_mn_node_status(node: int, state: int, error: int, uptime_s: int) -> tuple[int, bytes]:
    """Periodic status of one node (0x440 + node, response)."""
    can_id, data = encode("mn_node_status", state=state, error=error, uptime_s=uptime_s)
    return mn_node_id(can_id, node), data


def decode_mn_node_status(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x440, or None when the payload is too short."""
    return decode("mn_node_status", data, strict)


def encode_mn_node_cmd(node: int, func: int, args: bytes) -> tuple[int, bytes]:
    """One command to one node without selecting it (0x460 + node, request)."""
    can_id, data = encode("mn_node_cmd", func=func, args=args)
    return mn_node_id(can_id, node), data


def decode_mn_node_cmd(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x460, or None when the payload is too short."""
    return decode("mn_node_cmd", data, strict)


def encode_mn_node_resp(node: int, func: int, data: bytes) -> tuple[int, bytes]:
    """The answer of one node to NODE_CMD (0x480 + node, response)."""
    can_id, data = encode("mn_node_resp", func=func, data=data)
    return mn_node_id(can_id, node), data


def decode_mn_node_resp(data: bytes, strict: bool = False) -> dict | None:
    """Fields of 0x480, or None when the payload is too short."""
    return decode("mn_node_resp", data, strict)
