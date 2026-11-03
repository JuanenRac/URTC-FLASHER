# =============================================================================
# URTC-COMMON - src/urtc_common/heater_sim.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A simulated soldering iron: a first-order thermal plant driven by a PID loop, for the virtual board.

The plant is ``C * dT/dt = P - L * (T - T_ambient)`` with ``P`` the heater power times the duty the loop asks for
(0 to 1). The loop is a PID with a clamped integral and anti-windup. The host sets the target with the frame 0x130; if
the frame is not repeated within the watchdog time the loop gives up the target and the iron cools (a real head does the same).
The board answers with the temperature telemetry (0x135) every telemetry period.

Every number comes from ``heater_model.json`` (or from a dictionary passed in), never from the code. They are estimates for
tests, not measurements of a real iron, and nothing here replaces a bench run.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import protocol

Frame = tuple[int, bytes]

_DEFAULTS: dict[str, Any] = {
    "ambient_c": 25.0, "heater_power_w": 65.0, "heat_capacity_j_per_k": 1.8, "loss_w_per_k": 0.16, "step_s": 0.01,
    "kp": 0.04, "ki": 0.004, "kd": 0.0, "integral_limit": 1.0, "setpoint_watchdog_ms": 250, "telemetry_period_ms": 150,
    "max_temperature_c": 445.0,
}
CONFIG_PATH = Path(__file__).with_name("heater_model.json")


def load_config(path: Path | None = None, **overrides: Any) -> dict[str, Any]:
    """The parameters: built-in fallbacks, then the JSON file, then the overrides."""
    config = dict(_DEFAULTS)
    source = path or CONFIG_PATH
    try:
        loaded = json.loads(Path(source).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        loaded = {}
    config.update({k: v for k, v in loaded.items() if k in _DEFAULTS})
    config.update({k: v for k, v in overrides.items() if k in _DEFAULTS})
    return config


class SolderingIronModel:
    """The plant and the loop, advanced in fixed steps of simulated time."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = load_config() if config is None else {**_DEFAULTS, **config}
        self.temperature_c = float(self.config["ambient_c"])
        self.setpoint_c = 0
        self.duty = 0.0
        self._integral = 0.0
        self._previous_error = 0.0
        self._since_setpoint_ms = 0.0
        self._since_telemetry_ms = 0.0
        self.peak_c = self.temperature_c

    def set_target(self, setpoint_c: int) -> None:
        """A setpoint frame arrived: it also restarts the watchdog."""
        self.setpoint_c = max(0, min(int(setpoint_c), int(self.config["max_temperature_c"])))
        self._since_setpoint_ms = 0.0

    def _step(self, dt: float) -> None:
        cfg = self.config
        if self._since_setpoint_ms > cfg["setpoint_watchdog_ms"]:
            self.setpoint_c = 0
        if self.setpoint_c <= 0:
            self.duty, self._integral, self._previous_error = 0.0, 0.0, 0.0
        else:
            error = self.setpoint_c - self.temperature_c
            derivative = (error - self._previous_error) / dt if dt > 0 else 0.0
            self._previous_error = error
            raw = cfg["kp"] * error + self._integral + cfg["kd"] * derivative
            # Anti-windup: the integral only grows while the output is not saturated against the error.
            if not ((raw >= 1.0 and error > 0) or (raw <= 0.0 and error < 0)):
                limit = float(cfg["integral_limit"])
                self._integral = max(-limit, min(limit, self._integral + cfg["ki"] * error * dt))
            self.duty = max(0.0, min(1.0, raw))
        power = cfg["heater_power_w"] * self.duty
        loss = cfg["loss_w_per_k"] * (self.temperature_c - cfg["ambient_c"])
        self.temperature_c += (power - loss) / cfg["heat_capacity_j_per_k"] * dt
        self.peak_c = max(self.peak_c, self.temperature_c)

    def advance(self, seconds: float) -> list[Frame]:
        """Run the model for ``seconds`` of simulated time; the telemetry frames that fall due in it."""
        frames: list[Frame] = []
        step = float(self.config["step_s"])
        remaining = max(0.0, float(seconds))
        while remaining > 1e-12:
            dt = min(step, remaining)
            remaining -= dt
            self._step(dt)
            self._since_setpoint_ms += dt * 1000.0
            self._since_telemetry_ms += dt * 1000.0
            if self._since_telemetry_ms >= self.config["telemetry_period_ms"] - 1e-6:
                self._since_telemetry_ms -= self.config["telemetry_period_ms"]
                frames.append(self.telemetry())
        return frames

    def telemetry(self) -> Frame:
        """The 0x135 frame with the temperature rounded to whole degrees."""
        return protocol.encode("solder_telemetry", temperature_c=max(0, int(round(self.temperature_c))))
