import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import serial as pyserial

from sermon.data_model import FieldDefinition, SequenceDefinition, TriggerRule
from sermon.serial_manager import SerialConfig
from sermon.session import (
    SessionData,
    load_session,
    save_session,
    session_from_dict,
    session_to_dict,
)


class TestSessionRoundtrip:
    def test_empty_session(self) -> None:
        s = SessionData()
        d = session_to_dict(s)
        s2 = session_from_dict(d)
        assert s2.port_config is None
        assert s2.sequences == []
        assert s2.trigger_rules == []
        assert s2.hex_mode is False
        assert s2.tx_echo is True
        assert s2.tx_history == []

    def test_with_all_fields(self) -> None:
        seq = SequenceDefinition(
            name="ping",
            fields=[FieldDefinition(name="sof", field_type="const", value="AA")],
        )
        rule = TriggerRule(name="test", receive_sequence=seq, active=True)
        s = SessionData(
            port_config=SerialConfig(
                port="/dev/ttyUSB0",
                baudrate=9600,
                bytesize=pyserial.EIGHTBITS,
                parity=pyserial.PARITY_NONE,
                stopbits=pyserial.STOPBITS_ONE,
                timeout=0.1,
            ),
            sequences=[seq],
            trigger_rules=[rule],
            hex_mode=True,
            tx_echo=False,
            tx_history=[("AA BB", True), ("hello", False)],
        )
        d = session_to_dict(s)
        s2 = session_from_dict(d)

        assert s2.port_config is not None
        assert s2.port_config.port == "/dev/ttyUSB0"
        assert s2.port_config.baudrate == 9600
        assert s2.port_config.bytesize == pyserial.EIGHTBITS
        assert s2.port_config.parity == pyserial.PARITY_NONE
        assert s2.port_config.stopbits == pyserial.STOPBITS_ONE
        assert s2.port_config.timeout == 0.1

        assert len(s2.sequences) == 1
        assert s2.sequences[0].name == "ping"
        assert len(s2.sequences[0].fields) == 1

        assert len(s2.trigger_rules) == 1
        assert s2.trigger_rules[0].name == "test"
        assert s2.trigger_rules[0].active is True
        assert s2.trigger_rules[0].receive_sequence is not None

        assert s2.hex_mode is True
        assert s2.tx_echo is False
        assert s2.tx_history == [("AA BB", True), ("hello", False)]

    def test_various_serial_configs(self) -> None:
        configs = [
            SerialConfig(port="/dev/ttyS0", baudrate=115200),
            SerialConfig(
                port="COM1",
                baudrate=4800,
                bytesize=pyserial.SEVENBITS,
                parity=pyserial.PARITY_EVEN,
                stopbits=pyserial.STOPBITS_TWO,
            ),
            SerialConfig(
                port="/dev/ttyUSB0",
                baudrate=2400,
                bytesize=pyserial.FIVEBITS,
                parity=pyserial.PARITY_MARK,
                stopbits=pyserial.STOPBITS_ONE_POINT_FIVE,
            ),
        ]
        for cfg in configs:
            s = SessionData(port_config=cfg)
            d = session_to_dict(s)
            s2 = session_from_dict(d)
            assert s2.port_config is not None
            assert s2.port_config.port == cfg.port
            assert s2.port_config.baudrate == cfg.baudrate
            assert s2.port_config.bytesize == cfg.bytesize
            assert s2.port_config.parity == cfg.parity
            assert s2.port_config.stopbits == cfg.stopbits


class TestSessionFileIO:
    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "sermon" / "session.json"
            with patch("sermon.session._session_path", return_value=session_path):
                s = SessionData(
                    port_config=SerialConfig(port="/dev/ttyAMA0", baudrate=57600),
                    hex_mode=True,
                    tx_echo=True,
                    tx_history=[("test", False)],
                )
                save_session(s)

                assert session_path.exists()
                raw = json.loads(session_path.read_text())
                assert raw["port_config"]["port"] == "/dev/ttyAMA0"
                assert raw["port_config"]["baudrate"] == 57600
                assert raw["hex_mode"] is True

                s2 = load_session()
                assert s2 is not None
                assert s2.port_config is not None
                assert s2.port_config.port == "/dev/ttyAMA0"
                assert s2.port_config.baudrate == 57600
                assert s2.hex_mode is True

    def test_load_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "nonexistent" / "session.json"
            with patch("sermon.session._session_path", return_value=session_path):
                result = load_session()
                assert result is None

    def test_load_corrupted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "sermon" / "session.json"
            session_path.parent.mkdir(parents=True)
            session_path.write_text("{invalid json}")
            with patch("sermon.session._session_path", return_value=session_path):
                result = load_session()
                assert result is None

    def test_port_config_excluded_when_empty(self) -> None:
        s = SessionData(port_config=SerialConfig())
        d = session_to_dict(s)
        assert "port_config" not in d or d["port_config"]["port"] == ""
