import json
import os
import tempfile

import pytest

from sermon.data_model import (
    FieldDefinition,
    SequenceDefinition,
    sequence_from_file,
    sequence_from_json,
    sequence_to_file,
    sequence_to_json,
)


class TestFieldDefinition:
    def test_default_quantifier(self) -> None:
        f = FieldDefinition(name="x", field_type="wildcard", capture_name="p")
        assert f.quantifier == "*"

    def test_explicit_quantifier(self) -> None:
        f = FieldDefinition(
            name="x", field_type="wildcard", capture_name="p", quantifier="+"
        )
        assert f.quantifier == "+"

    def test_const_byte_length(self) -> None:
        f = FieldDefinition(name="hdr", field_type="const", value="AABB")
        assert f.byte_length() == 2

    def test_const_byte_length_with_spaces(self) -> None:
        f = FieldDefinition(name="hdr", field_type="const", value="AA BB")
        assert f.byte_length() == 2

    def test_const_empty_value(self) -> None:
        f = FieldDefinition(name="hdr", field_type="const", value="")
        assert f.byte_length() == 0

    def test_checksum_byte_length(self) -> None:
        f = FieldDefinition(
            name="crc",
            field_type="checksum",
            checksum_algorithm="CRC-16",
        )
        assert f.byte_length() == 2

    def test_wildcard_byte_length(self) -> None:
        f = FieldDefinition(name="p", field_type="wildcard", capture_name="p")
        assert f.byte_length() == 0

    def test_const_resolve(self) -> None:
        f = FieldDefinition(name="hdr", field_type="const", value="AABB")
        assert f.resolve_bytes() == bytes([0xAA, 0xBB])

    def test_const_resolve_with_spaces(self) -> None:
        f = FieldDefinition(name="hdr", field_type="const", value="AA BB")
        assert f.resolve_bytes() == bytes([0xAA, 0xBB])

    def test_wildcard_resolve_with_captures(self) -> None:
        f = FieldDefinition(name="p", field_type="wildcard", capture_name="pload")
        assert f.resolve_bytes({"pload": bytes([0x01, 0x02])}) == bytes([0x01, 0x02])

    def test_wildcard_resolve_empty_captures(self) -> None:
        f = FieldDefinition(name="p", field_type="wildcard", capture_name="pload")
        assert f.resolve_bytes() == b""

    def test_checksum_resolve_with_scope(self) -> None:
        from sermon.checksum import compute

        f = FieldDefinition(
            name="crc",
            field_type="checksum",
            checksum_algorithm="CRC-16",
            capture_name="body",
        )
        result = f.resolve_bytes({"body": bytes([0x01, 0x02])})
        expected = compute("CRC-16", bytes([0x01, 0x02])).to_bytes(2, "big")
        assert result == expected

    def test_checksum_resolve_no_captures(self) -> None:
        from sermon.checksum import compute

        f = FieldDefinition(
            name="crc",
            field_type="checksum",
            checksum_algorithm="CRC-16",
            capture_name="body",
        )
        result = f.resolve_bytes()
        expected = compute("CRC-16", b"").to_bytes(2, "big")
        assert result == expected


class TestSequenceDefinition:
    def test_empty_sequence(self) -> None:
        seq = SequenceDefinition(name="empty")
        assert seq.byte_length() == 0
        assert seq.resolve() == b""

    def test_const_only(self) -> None:
        fields = [
            FieldDefinition(name="a", field_type="const", value="AA"),
            FieldDefinition(name="b", field_type="const", value="BB"),
        ]
        seq = SequenceDefinition(name="test", fields=fields)
        assert seq.byte_length() == 2
        assert seq.resolve() == bytes([0xAA, 0xBB])

    def test_resolve_with_captures(self) -> None:
        from sermon.checksum import compute

        fields = [
            FieldDefinition(name="sof", field_type="const", value="AA"),
            FieldDefinition(name="p", field_type="wildcard", capture_name="pload"),
            FieldDefinition(
                name="crc",
                field_type="checksum",
                checksum_algorithm="CRC-16",
                capture_name="pload",
            ),
        ]
        seq = SequenceDefinition(name="pkt", fields=fields)
        captures = {"pload": bytes([0x01, 0x02])}
        result = seq.resolve(captures)
        expected_crc = compute("CRC-16", bytes([0x01, 0x02])).to_bytes(2, "big")
        assert result == bytes([0xAA, 0x01, 0x02]) + expected_crc


class TestJSONSerialization:
    def test_roundtrip(self) -> None:
        fields = [
            FieldDefinition(name="a", field_type="const", value="AA"),
            FieldDefinition(name="p", field_type="wildcard", capture_name="pload"),
        ]
        seq = SequenceDefinition(name="test", fields=fields)
        json_str = sequence_to_json(seq)
        seq2 = sequence_from_json(json_str)
        assert seq2.name == seq.name
        assert len(seq2.fields) == len(seq.fields)
        assert seq2.fields[0].name == seq.fields[0].name
        assert seq2.fields[0].value == seq.fields[0].value
        assert seq2.fields[1].capture_name == seq.fields[1].capture_name
        assert seq2.fields[1].quantifier == seq.fields[1].quantifier

    def test_roundtrip_all_field_types(self) -> None:
        fields = [
            FieldDefinition(name="sof", field_type="const", value="AA"),
            FieldDefinition(
                name="p", field_type="wildcard", capture_name="pload", quantifier="+"
            ),
            FieldDefinition(
                name="crc",
                field_type="checksum",
                checksum_algorithm="CRC-16",
                checksum_scope=[0, 1],
                capture_name="pload",
            ),
        ]
        seq = SequenceDefinition(name="full", fields=fields)
        seq2 = sequence_from_json(sequence_to_json(seq))
        assert seq2.fields[2].checksum_algorithm == "CRC-16"
        assert seq2.fields[2].checksum_scope == [0, 1]
        assert seq2.fields[1].quantifier == "+"

    def test_json_structure(self) -> None:
        f = FieldDefinition(name="x", field_type="const", value="FF")
        seq = SequenceDefinition(name="s", fields=[f])
        data = json.loads(sequence_to_json(seq))
        assert data["name"] == "s"
        assert data["fields"][0]["name"] == "x"

    def test_file_roundtrip(self) -> None:
        fields = [
            FieldDefinition(name="a", field_type="const", value="01"),
        ]
        seq = SequenceDefinition(name="file_test", fields=fields)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            sequence_to_file(seq, path)
            seq2 = sequence_from_file(path)
            assert seq2.name == seq.name
        finally:
            os.unlink(path)

    def test_from_invalid_json(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            sequence_from_json("{bad json}")

    def test_empty_fields(self) -> None:
        seq = sequence_from_json('{"name": "empty", "fields": []}')
        assert len(seq.fields) == 0
        assert seq.name == "empty"


class TestEdgeCases:
    def test_const_with_odd_hex_raises(self) -> None:
        f = FieldDefinition(name="bad", field_type="const", value="A")
        with pytest.raises(ValueError):
            f.resolve_bytes()

    def test_checksum_with_unknown_algo(self) -> None:
        f = FieldDefinition(
            name="bad",
            field_type="checksum",
            checksum_algorithm="NOT-REAL",
        )
        with pytest.raises(ValueError):
            f.byte_length()

    def test_sequence_byte_length_with_wildcard(self) -> None:
        fields = [
            FieldDefinition(name="c", field_type="const", value="AA"),
            FieldDefinition(name="w", field_type="wildcard", capture_name="x"),
            FieldDefinition(
                name="crc", field_type="checksum", checksum_algorithm="CRC-8"
            ),
        ]
        seq = SequenceDefinition(fields=fields)
        assert seq.byte_length() == 2  # const=1 + wildcard=0 + checksum=1
