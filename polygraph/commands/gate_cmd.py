"""
polygraph/commands/gate_cmd.py
==============================
Implements ``python -m polygraph gate on|off|status``.
"""

from __future__ import annotations

from pathlib import Path

_PRIVATE_DIR = Path.home() / ".polygraph_private"
_GATE_OFF = _PRIVATE_DIR / "GATE_OFF"


def cmd_gate(action: str) -> None:
    """Create or remove GATE_OFF; print current status."""
    _PRIVATE_DIR.mkdir(parents=True, exist_ok=True)

    if action == "on":
        if _GATE_OFF.exists():
            _GATE_OFF.unlink()
        print("Gate: ON  (commit/push will be blocked when verdict is not VERIFIED)")
    elif action == "off":
        _GATE_OFF.touch()
        print("Gate: OFF  (commits allowed; verdict still recorded)")
    elif action == "status":
        state = "OFF" if _GATE_OFF.exists() else "ON"
        print(f"Gate: {state}")
