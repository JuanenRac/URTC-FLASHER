"""GENERATED from spec/tools.json by tools/generate_tools.py - do not edit by hand.

The tool profiles of the tool head as data (standard library only).
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
"""
from __future__ import annotations

TOOLS: tuple[dict, ...] = tuple([
    {
        "id": 0,
        "name": "SOLDERING_IRON",
        "title": "Soldering Iron",
        "display_name": "T12 Soldering Station",
        "short_name": "Soldering Iron",
        "kind": "motion",
        "category": "Shipped (v0.0)",
        "minimum": 150,
        "default": 320,
        "maximum": 445,
        "unit": "°C",
        "metric": "TIP TEMP",
        "watchdog_ms": 250,
        "expansion_board": "none",
        "features": [
            "PID Auto-Tune",
            "ADC Thermocouple Reader",
            "Sleep Mode Detection",
            "Watchdog Safety Cutoff"
        ]
    },
    {
        "id": 1,
        "name": "PASTE_DISPENSER",
        "title": "Paste Dispenser",
        "display_name": "SMT Solder Paste Dispenser",
        "short_name": "Paste Dispenser",
        "kind": "motion",
        "category": "Shipped (v0.0)",
        "minimum": 0.1,
        "default": 1.5,
        "maximum": 10,
        "unit": "mm/s",
        "metric": "DISPENSE RATE",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "Micro-step Feed Control",
            "Retract Pulse",
            "Volumetric Calibration",
            "Solder Syringe Pressure Shield"
        ]
    },
    {
        "id": 2,
        "name": "LIQUID_DISPENSER",
        "title": "Liquid Dispenser",
        "display_name": "Thermal Paste / Liquid Dispenser",
        "short_name": "Liquid Dispenser",
        "kind": "motion",
        "category": "Shipped (v0.0)",
        "minimum": 0.5,
        "default": 5,
        "maximum": 50,
        "unit": "µL/s",
        "metric": "FLOW RATE",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "Anti-Drip Retraction",
            "Fluid Viscosity Profile",
            "Pneumatic Assist"
        ]
    },
    {
        "id": 3,
        "name": "SCREWDRIVER",
        "title": "Screwdriver",
        "display_name": "Smart Electric Screwdriver",
        "short_name": "Screwdriver",
        "kind": "motion",
        "category": "Shipped (v0.0)",
        "minimum": 1,
        "default": 12,
        "maximum": 35,
        "unit": "N·cm",
        "metric": "TORQUE LIMIT",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "Dynamic Stall Detection",
            "Screw Depth Sensing",
            "Reversible Drive",
            "Torque Ramp Control"
        ]
    },
    {
        "id": 4,
        "name": "VACUUM_PICKUP",
        "title": "Vacuum Pickup",
        "display_name": "Vacuum / Pneumatic Gripper",
        "short_name": "Vacuum Pickup",
        "kind": "telemetry",
        "category": "Shipped (v0.0)",
        "minimum": -90,
        "default": -65,
        "maximum": 0,
        "unit": "kPa",
        "metric": "VACUUM LEVEL",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "Part Detect Feedback",
            "Quick Blow-Off Release",
            "Vacuum Pump PWM Control"
        ]
    },
    {
        "id": 5,
        "name": "DRILL",
        "title": "Drill",
        "display_name": "Drill / PCB Spindle (BL4260)",
        "short_name": "Drill",
        "kind": "actuator",
        "category": "Shipped (v0.0)",
        "minimum": 1000,
        "default": 12000,
        "maximum": 24000,
        "unit": "RPM",
        "metric": "SPINDLE SPEED",
        "watchdog_ms": 250,
        "expansion_board": "none",
        "features": [
            "Dynamic Braking",
            "Optical Tachometer Reading",
            "Direction Switch",
            "Dedicated Enable Line"
        ]
    },
    {
        "id": 6,
        "name": "GRIPPER_GIMBAL",
        "title": "Gripper (Gimbal)",
        "display_name": "Gimbal Gripper",
        "short_name": "Gripper (Gimbal)",
        "kind": "motion",
        "category": "Shipped (v0.0)",
        "minimum": 0.2,
        "default": 3.5,
        "maximum": 15,
        "unit": "N",
        "metric": "GRIP FORCE",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "FOC Compliance Control",
            "Soft Touch Detection",
            "Position/Torque Dual Mode"
        ]
    },
    {
        "id": 7,
        "name": "GRIPPER_NEMA",
        "title": "Gripper (NEMA)",
        "display_name": "NEMA Heavy-Duty Gripper",
        "short_name": "Gripper (NEMA)",
        "kind": "motion",
        "category": "Shipped (v0.0)",
        "minimum": 0,
        "default": 80,
        "maximum": 100,
        "unit": "%",
        "metric": "CLAMP POSITION",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "StallGuard Load Detection",
            "Variable Current Hold",
            "Auto-Homing Sequence"
        ]
    },
    {
        "id": 8,
        "name": "AOI_INSPECTION",
        "title": "AOI Inspection",
        "display_name": "AOI Camera Inspection Ring",
        "short_name": "AOI Inspection",
        "kind": "telemetry",
        "category": "Shipped (v0.0)",
        "minimum": 0,
        "default": 100,
        "maximum": 100,
        "unit": "%",
        "metric": "FLASH POWER",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "Stroboscopic Pulse (10µs)",
            "RGB Color Matrix",
            "Camera Trigger Out"
        ]
    },
    {
        "id": 9,
        "name": "LASER_ENGRAVER",
        "title": "Laser Engraver",
        "display_name": "Engraving Laser Diode (10W)",
        "short_name": "Laser Engraver",
        "kind": "actuator",
        "category": "Shipped (v0.0)",
        "minimum": 0,
        "default": 0,
        "maximum": 100,
        "unit": "%",
        "metric": "LASER POWER",
        "watchdog_ms": 250,
        "expansion_board": "none",
        "features": [
            "Hardware Watchdog Lockdown",
            "PWM Power Scale",
            "Safety Interlock Loop",
            "Air Assist Solenoid"
        ]
    },
    {
        "id": 10,
        "name": "PRINTER_3D",
        "title": "3D Printer",
        "display_name": "3D Printing Hotend",
        "short_name": "3D Printer",
        "kind": "actuator",
        "category": "Shipped (v0.0)",
        "minimum": 20,
        "default": 215,
        "maximum": 300,
        "unit": "°C",
        "metric": "NOZZLE TEMP",
        "watchdog_ms": 250,
        "expansion_board": "none",
        "features": [
            "PID Nozzle Control",
            "25kHz 4-Wire Fan Control",
            "Extruder Stepper Integration",
            "Thermal Runaway Protection"
        ]
    },
    {
        "id": 11,
        "name": "SCAN_PROBE",
        "title": "Scan Probe",
        "display_name": "3D Scanner Contact Probe",
        "short_name": "Scan Probe",
        "kind": "telemetry",
        "category": "Shipped (v0.0)",
        "minimum": 0,
        "default": 0,
        "maximum": 99999,
        "unit": "pts",
        "metric": "TRIGGER COUNT",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "Sub-microsecond Trigger Latency",
            "Hardware Debounce Filter",
            "Surface Point Digitizer"
        ]
    },
    {
        "id": 12,
        "name": "SMT_PICKPLACE",
        "title": "SMT Pick & Place",
        "display_name": "SMT Pick & Place Head",
        "short_name": "SMT Pick & Place",
        "kind": "motion",
        "category": "Expansion (v0.1)",
        "minimum": -180,
        "default": 0,
        "maximum": 180,
        "unit": "°",
        "metric": "A-AXIS ANGLE",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "360° Continuous Rotation",
            "Micro-degree Accuracy",
            "Vacuum Link Integration"
        ]
    },
    {
        "id": 13,
        "name": "ELECTROMAGNET",
        "title": "Electromagnet",
        "display_name": "Heavy-Duty Electromagnet",
        "short_name": "Electromagnet",
        "kind": "actuator",
        "category": "Expansion (v0.1)",
        "minimum": 0,
        "default": 50,
        "maximum": 100,
        "unit": "%",
        "metric": "COIL CURRENT",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "Reverse Demagnetization Pulse",
            "Duty Cycle Power Saver",
            "Thermal Protection"
        ]
    },
    {
        "id": 14,
        "name": "SPOT_WELDER",
        "title": "Spot Welder",
        "display_name": "Spot Welder Head",
        "short_name": "Spot Welder",
        "kind": "actuator",
        "category": "Expansion (v0.1)",
        "minimum": 1,
        "default": 15,
        "maximum": 100,
        "unit": "ms",
        "metric": "PULSE TIME",
        "watchdog_ms": None,
        "expansion_board": "recommended",
        "features": [
            "Pre-weld Cleanup Pulse",
            "Contact Safety Gating",
            "Energy Monitor"
        ]
    },
    {
        "id": 15,
        "name": "CONFORMAL_COATING",
        "title": "Conformal Coating",
        "display_name": "Conformal Coating Airbrush",
        "short_name": "Conformal Coating",
        "kind": "external",
        "category": "Expansion (v0.1)",
        "minimum": 5,
        "default": 25,
        "maximum": 60,
        "unit": "PSI",
        "metric": "ATOMIZER AIR",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "Fan Pattern Adjustment",
            "Solvent Purge Cycle",
            "Anti-Clog Pulsing"
        ]
    },
    {
        "id": 16,
        "name": "VACUUM_GRIPPER_LG",
        "title": "Vacuum Gripper (LG)",
        "display_name": "Large Vacuum Suction Array",
        "short_name": "Vacuum Gripper (LG)",
        "kind": "motion",
        "category": "Expansion (v0.1)",
        "minimum": -95,
        "default": -80,
        "maximum": 0,
        "unit": "kPa",
        "metric": "PANEL VACUUM",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "4-Zone Selective Vacuum",
            "Panel Seating Sensor",
            "Emergency Blow-Off"
        ]
    },
    {
        "id": 17,
        "name": "FLYING_PROBE",
        "title": "Flying Probe",
        "display_name": "Functional Flying-Probe Tester",
        "short_name": "Flying Probe",
        "kind": "telemetry",
        "category": "Expansion (v0.1)",
        "minimum": 0,
        "default": 3.3,
        "maximum": 36,
        "unit": "V",
        "metric": "MEASURED VOLT",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "16-bit ADC Resolution",
            "Resistance / Voltage Mode",
            "Kelvin 4-Wire Measurement"
        ]
    },
    {
        "id": 18,
        "name": "UV_CURING",
        "title": "UV Curing",
        "display_name": "UV Curing Lamp Head",
        "short_name": "UV Curing",
        "kind": "actuator",
        "category": "Expansion (v0.1)",
        "minimum": 0,
        "default": 80,
        "maximum": 100,
        "unit": "%",
        "metric": "UV INTENSITY",
        "watchdog_ms": 250,
        "expansion_board": "none",
        "features": [
            "Dual Wavelength Control",
            "Exposure Timer",
            "Over-Temp Thermal Throttle"
        ]
    },
    {
        "id": 19,
        "name": "HOTAIR_REWORK",
        "title": "Hot Air Rework",
        "display_name": "Hot Air Rework Nozzle",
        "short_name": "Hot Air Rework",
        "kind": "actuator",
        "category": "Expansion (v0.1)",
        "minimum": 100,
        "default": 350,
        "maximum": 445,
        "unit": "°C",
        "metric": "AIR TEMP",
        "watchdog_ms": 250,
        "expansion_board": "none",
        "features": [
            "Auto Cool-Down Standby",
            "Airflow Rate Regulation",
            "PID Temperature Hold"
        ]
    },
    {
        "id": 20,
        "name": "PRESSFIT_INSERTER",
        "title": "Press-Fit Inserter",
        "display_name": "Pneumatic Press-Fit Inserter",
        "short_name": "Press-Fit Inserter",
        "kind": "external",
        "category": "Expansion (v0.1)",
        "minimum": 10,
        "default": 250,
        "maximum": 1000,
        "unit": "N",
        "metric": "PRESS FORCE",
        "watchdog_ms": None,
        "expansion_board": "none",
        "features": [
            "Load Cell Force Profile",
            "Depth Limit Stop",
            "Double-Tap Seating"
        ]
    },
    {
        "id": 21,
        "name": "CRIMPING_ACTUATOR",
        "title": "Crimping Actuator",
        "display_name": "Wire Stripper & Crimper",
        "short_name": "Crimping Actuator",
        "kind": "motion",
        "category": "Expansion (v0.1)",
        "minimum": 0.5,
        "default": 4.2,
        "maximum": 8,
        "unit": "mm",
        "metric": "CRIMP CYCLE",
        "watchdog_ms": None,
        "expansion_board": "required",
        "features": [
            "TMC5160 10A High Current Mode",
            "StallGuard Force Peak",
            "Strip Length Control"
        ]
    },
    {
        "id": 22,
        "name": "THERMAL_INSPECTION",
        "title": "Thermal Inspection",
        "display_name": "PCB Thermal Inspection (MLX90640)",
        "short_name": "Thermal Inspection",
        "kind": "telemetry",
        "category": "Expansion (v0.1)",
        "minimum": 15,
        "default": 45,
        "maximum": 150,
        "unit": "°C",
        "metric": "MAX BOARD TEMP",
        "watchdog_ms": None,
        "expansion_board": "required",
        "features": [
            "32x24 IR Matrix Heatmap",
            "Short Circuit Auto-Detect",
            "Over-temperature Alarm"
        ]
    },
    {
        "id": 23,
        "name": "PASTE_JETTING",
        "title": "Paste Jetting",
        "display_name": "Solder Paste Jetting Valve",
        "short_name": "Paste Jetting",
        "kind": "actuator",
        "category": "Expansion (v0.1)",
        "minimum": 10,
        "default": 150,
        "maximum": 500,
        "unit": "Hz",
        "metric": "JET FREQ",
        "watchdog_ms": None,
        "expansion_board": "required",
        "features": [
            "Sub-millisecond Local PWM",
            "Viscosity Thermal Control",
            "Droplet Count Profiler"
        ]
    },
    {
        "id": 24,
        "name": "ULTRASONIC_WELDER",
        "title": "Ultrasonic Welder",
        "display_name": "Ultrasonic Plastic Welder",
        "short_name": "Ultrasonic Welder",
        "kind": "actuator",
        "category": "Expansion (v0.1)",
        "minimum": 50,
        "default": 400,
        "maximum": 2000,
        "unit": "ms",
        "metric": "WELD TIME",
        "watchdog_ms": None,
        "expansion_board": "recommended",
        "features": [
            "Resonance Frequency Lock",
            "Weld Energy Integration",
            "Solidification Hold Time"
        ]
    }
])

TOOL_NAMES: dict[int, str] = {tool["id"]: tool["short_name"] for tool in TOOLS}
TOOL_KINDS: dict[int, str] = {tool["id"]: tool["kind"] for tool in TOOLS}


def tool_by_id(tool_id: int) -> dict | None:
    """The profile of a tool identifier, or None for an identifier that is no tool."""
    for tool in TOOLS:
        if tool["id"] == tool_id:
            return tool
    return None
