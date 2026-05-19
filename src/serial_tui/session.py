from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

import serial as pyserial

from serial_tui.data_model import (
    SequenceDefinition,
    TriggerRule,
    sequence_from_json,
    trigger_from_json,
    trigger_to_json,
)
from serial_tui.serial_manager import SerialConfig

_BYTESIZE_TO_LABEL = {
    pyserial.FIVEBITS: "5",
    pyserial.SIXBITS: "6",
    pyserial.SEVENBITS: "7",
    pyserial.EIGHTBITS: "8",
}
_LABEL_TO_BYTESIZE = {v: k for k, v in _BYTESIZE_TO_LABEL.items()}

_PARITY_TO_LABEL = {
    pyserial.PARITY_NONE: "None",
    pyserial.PARITY_EVEN: "Even",
    pyserial.PARITY_ODD: "Odd",
    pyserial.PARITY_MARK: "Mark",
    pyserial.PARITY_SPACE: "Space",
}
_LABEL_TO_PARITY = {v: k for k, v in _PARITY_TO_LABEL.items()}

_STOPBITS_TO_LABEL = {
    pyserial.STOPBITS_ONE: "1",
    pyserial.STOPBITS_ONE_POINT_FIVE: "1.5",
    pyserial.STOPBITS_TWO: "2",
}
_LABEL_TO_STOPBITS = {v: k for k, v in _STOPBITS_TO_LABEL.items()}


@dataclass
class SessionData:
    port_config: SerialConfig | None = None
    sequences: list[SequenceDefinition] = field(default_factory=list)
    trigger_rules: list[TriggerRule] = field(default_factory=list)
    hex_mode: bool = False
    tx_echo: bool = True
    tx_history: list[tuple[str, bool]] = field(default_factory=list)


def _session_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / "serial-tui"
    return Path.home() / ".local" / "share" / "serial-tui"


def _session_path() -> Path:
    return _session_dir() / "session.json"


def _serial_config_to_dict(cfg: SerialConfig) -> dict:
    return {
        "port": cfg.port,
        "baudrate": cfg.baudrate,
        "bytesize": _BYTESIZE_TO_LABEL.get(cfg.bytesize, str(cfg.bytesize)),
        "parity": _PARITY_TO_LABEL.get(cfg.parity, cfg.parity),
        "stopbits": _STOPBITS_TO_LABEL.get(cfg.stopbits, str(cfg.stopbits)),
        "timeout": cfg.timeout,
    }


def _serial_config_from_dict(d: dict) -> SerialConfig:
    return SerialConfig(
        port=d.get("port", ""),
        baudrate=d.get("baudrate", 115200),
        bytesize=_LABEL_TO_BYTESIZE.get(d.get("bytesize", "8"), pyserial.EIGHTBITS),
        parity=_LABEL_TO_PARITY.get(d.get("parity", "None"), pyserial.PARITY_NONE),
        stopbits=_LABEL_TO_STOPBITS.get(d.get("stopbits", "1"), pyserial.STOPBITS_ONE),
        timeout=d.get("timeout", 0.05),
    )


def session_to_dict(session: SessionData) -> dict:
    d: dict = {}
    if session.port_config and session.port_config.port:
        d["port_config"] = _serial_config_to_dict(session.port_config)
    d["hex_mode"] = session.hex_mode
    d["tx_echo"] = session.tx_echo
    d["tx_history"] = list(session.tx_history)
    d["sequences"] = [asdict(seq) for seq in session.sequences]
    d["trigger_rules"] = [
        json.loads(trigger_to_json(rule)) for rule in session.trigger_rules
    ]
    return d


def session_from_dict(d: dict) -> SessionData:
    port_config = None
    if "port_config" in d:
        port_config = _serial_config_from_dict(d["port_config"])
    sequences = [sequence_from_json(json.dumps(s)) for s in d.get("sequences", [])]
    trigger_rules = [
        trigger_from_json(json.dumps(t)) for t in d.get("trigger_rules", [])
    ]
    return SessionData(
        port_config=port_config,
        sequences=sequences,
        trigger_rules=trigger_rules,
        hex_mode=d.get("hex_mode", False),
        tx_echo=d.get("tx_echo", True),
        tx_history=[tuple(h) for h in d.get("tx_history", [])],
    )


def save_session(session: SessionData) -> None:
    path = _session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    d = session_to_dict(session)
    path.write_text(json.dumps(d, indent=2))


def load_session() -> SessionData | None:
    path = _session_path()
    if not path.exists():
        return None
    try:
        d = json.loads(path.read_text())
        return session_from_dict(d)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None
