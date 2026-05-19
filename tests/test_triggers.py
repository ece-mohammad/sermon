import json

from sermon.data_model import (
    FieldDefinition,
    SequenceDefinition,
    TriggerRule,
    trigger_from_json,
    trigger_to_json,
)
from sermon.matcher import SequenceMatcher


class TestTriggerRule:
    def test_default_active(self) -> None:
        rule = TriggerRule(name="test")
        assert rule.active is True

    def test_custom_active(self) -> None:
        rule = TriggerRule(name="test", active=False)
        assert rule.active is False

    def test_with_sequences(self) -> None:
        recv = SequenceDefinition(
            name="recv",
            fields=[
                FieldDefinition(name="sof", field_type="const", value="AA"),
                FieldDefinition(name="p", field_type="wildcard", capture_name="pload"),
            ],
        )
        send = SequenceDefinition(
            name="send",
            fields=[
                FieldDefinition(name="resp", field_type="const", value="BB"),
            ],
        )
        rule = TriggerRule(name="test", send_sequence=send, receive_sequence=recv)
        assert rule.name == "test"
        assert rule.send_sequence is send
        assert rule.receive_sequence is recv


class TestTriggerSerialization:
    def test_roundtrip_empty(self) -> None:
        rule = TriggerRule(name="empty")
        data = trigger_to_json(rule)
        rule2 = trigger_from_json(data)
        assert rule2.name == "empty"
        assert rule2.active is True
        assert rule2.send_sequence is None
        assert rule2.receive_sequence is None

    def test_roundtrip_inactive(self) -> None:
        rule = TriggerRule(name="off", active=False)
        rule2 = trigger_from_json(trigger_to_json(rule))
        assert rule2.active is False

    def test_roundtrip_with_sequences(self) -> None:
        recv = SequenceDefinition(
            name="recv",
            fields=[
                FieldDefinition(name="sof", field_type="const", value="AA"),
            ],
        )
        send = SequenceDefinition(
            name="send",
            fields=[
                FieldDefinition(name="resp", field_type="const", value="BB"),
            ],
        )
        rule = TriggerRule(name="trigger", send_sequence=send, receive_sequence=recv)
        rule2 = trigger_from_json(trigger_to_json(rule))
        assert rule2.name == "trigger"
        assert rule2.send_sequence is not None
        assert rule2.send_sequence.name == "send"
        assert rule2.send_sequence.resolve() == bytes([0xBB])
        assert rule2.receive_sequence is not None
        assert rule2.receive_sequence.name == "recv"
        assert rule2.receive_sequence.resolve() == bytes([0xAA])

    def test_json_structure(self) -> None:
        recv = SequenceDefinition(
            name="rx",
            fields=[FieldDefinition(name="hdr", field_type="const", value="FF")],
        )
        rule = TriggerRule(name="t", send_sequence=None, receive_sequence=recv)
        data = json.loads(trigger_to_json(rule))
        assert data["name"] == "t"
        assert data["active"] is True
        assert "send_sequence" not in data
        assert data["receive_sequence"]["name"] == "rx"


class TestTriggerMatching:
    def test_match_triggers_response(self) -> None:
        recv = SequenceDefinition(
            name="ping",
            fields=[
                FieldDefinition(name="sof", field_type="const", value="AA"),
                FieldDefinition(
                    name="payload", field_type="wildcard", capture_name="p"
                ),
            ],
        )
        send = SequenceDefinition(
            name="pong",
            fields=[
                FieldDefinition(name="resp", field_type="const", value="BB"),
                FieldDefinition(name="echo", field_type="wildcard", capture_name="p"),
            ],
        )
        data = bytes([0xAA, 0x01, 0x02, 0x03])
        matcher = SequenceMatcher(recv)
        result = matcher.match(data)
        assert result is not None
        assert result.captures["p"] == bytes([0x01, 0x02, 0x03])
        assert result.matched_bytes == data

        tx_bytes = send.resolve(result.captures)
        assert tx_bytes == bytes([0xBB, 0x01, 0x02, 0x03])

    def test_trigger_no_match(self) -> None:
        recv = SequenceDefinition(
            name="ping",
            fields=[FieldDefinition(name="sof", field_type="const", value="AA")],
        )
        data = bytes([0xBB, 0xCC])
        matcher = SequenceMatcher(recv)
        result = matcher.match(data)
        assert result is None

    def test_trigger_checksum_verify_reject(self) -> None:
        from sermon.checksum import compute

        body = bytes([0x01, 0x02])
        scope_data = bytes([0xAA]) + body
        crc = compute("CRC-16", scope_data).to_bytes(2, "big")
        recv = SequenceDefinition(
            name="pkt",
            fields=[
                FieldDefinition(name="sof", field_type="const", value="AA"),
                FieldDefinition(name="body", field_type="wildcard", capture_name="b"),
                FieldDefinition(
                    name="crc",
                    field_type="checksum",
                    checksum_algorithm="CRC-16",
                    checksum_scope=[0, 1],
                    capture_name="b",
                ),
            ],
        )
        send = SequenceDefinition(
            name="ack",
            fields=[FieldDefinition(name="ack", field_type="const", value="CC")],
        )
        good_data = bytes([0xAA]) + body + crc
        matcher = SequenceMatcher(recv)
        result = matcher.match(good_data)
        assert result is not None
        tx_bytes = send.resolve(result.captures)
        assert tx_bytes == bytes([0xCC])

        bad_crc = bytes([0x00, 0x00])
        bad_data = bytes([0xAA]) + body + bad_crc
        result2 = matcher.match(bad_data)
        assert result2 is None

    def test_match_all_with_triggers(self) -> None:
        recv = SequenceDefinition(
            name="sof",
            fields=[FieldDefinition(name="sof", field_type="const", value="AA")],
        )
        data = bytes([0xAA, 0xAA, 0xAA])
        matcher = SequenceMatcher(recv)
        results = matcher.match_all(data)
        assert len(results) == 3
        assert results[0].matched_bytes == bytes([0xAA])
        assert results[1].matched_bytes == bytes([0xAA])
        assert results[2].matched_bytes == bytes([0xAA])


class TestTriggerEdgeCases:
    def test_no_send_sequence(self) -> None:
        recv = SequenceDefinition(
            name="detect",
            fields=[FieldDefinition(name="sof", field_type="const", value="AA")],
        )
        data = bytes([0xAA])
        matcher = SequenceMatcher(recv)
        result = matcher.match(data)
        assert result is not None
        assert result.matched_bytes == bytes([0xAA])
        send = SequenceDefinition(name="empty")
        tx_bytes = send.resolve(result.captures)
        assert tx_bytes == b""

    def test_no_receive_sequence_no_match(self) -> None:
        rule = TriggerRule(name="incomplete")
        assert rule.receive_sequence is None

    def test_captures_used_in_multiple_fields(self) -> None:
        recv = SequenceDefinition(
            name="req",
            fields=[
                FieldDefinition(name="id", field_type="wildcard", capture_name="id"),
                FieldDefinition(name="sep", field_type="const", value="FF"),
            ],
        )
        send = SequenceDefinition(
            name="resp",
            fields=[
                FieldDefinition(name="ack", field_type="const", value="CC"),
                FieldDefinition(
                    name="echo_id", field_type="wildcard", capture_name="id"
                ),
            ],
        )
        data = bytes([0x01, 0x02, 0xFF])
        matcher = SequenceMatcher(recv)
        result = matcher.match(data)
        assert result is not None
        assert result.captures["id"] == bytes([0x01, 0x02])
        tx = send.resolve(result.captures)
        assert tx == bytes([0xCC, 0x01, 0x02])
