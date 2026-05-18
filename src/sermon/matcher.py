from __future__ import annotations

from dataclasses import dataclass, field

from sermon.checksum import checksum_size, compute
from sermon.data_model import FieldDefinition, SequenceDefinition


@dataclass
class MatchResult:
    captures: dict[str, bytes] = field(default_factory=dict)
    matched_bytes: bytes = b""
    remaining: bytes = b""


class SequenceMatcher:
    def __init__(self, sequence: SequenceDefinition) -> None:
        self.sequence = sequence

    def match(self, data: bytes) -> MatchResult | None:
        for start in range(len(data) + 1):
            result = self._try_match(data, start)
            if result is not None:
                return result
        return None

    def match_all(self, data: bytes) -> list[MatchResult]:
        results: list[MatchResult] = []
        pos = 0
        while pos < len(data):
            result = self._try_match(data, pos)
            if result is not None:
                results.append(result)
                pos += len(result.matched_bytes)
            else:
                pos += 1
        return results

    def _try_match(self, data: bytes, start: int) -> MatchResult | None:
        captures: dict[str, bytes] = {}
        field_bytes: list[bytes] = []

        result = self._match_fields(
            self.sequence.fields, data, start, captures, field_bytes, 0
        )
        if result is not None:
            end_pos, matched = result
            return MatchResult(
                captures=dict(captures),
                matched_bytes=matched,
                remaining=data[end_pos:],
            )
        return None

    def _match_fields(
        self,
        fields: list[FieldDefinition],
        data: bytes,
        pos: int,
        captures: dict[str, bytes],
        field_bytes: list[bytes],
        field_idx: int,
    ) -> tuple[int, bytes] | None:
        if field_idx >= len(fields):
            return (pos, b"")

        field = fields[field_idx]

        if field.field_type == "const":
            return self._match_const(
                field, fields, data, pos, captures, field_bytes, field_idx
            )

        if field.field_type == "checksum":
            return self._match_checksum(
                field, fields, data, pos, captures, field_bytes, field_idx
            )

        if field.field_type == "wildcard":
            return self._match_wildcard(
                field, fields, data, pos, captures, field_bytes, field_idx
            )

        return None

    def _match_const(
        self,
        field: FieldDefinition,
        fields: list[FieldDefinition],
        data: bytes,
        pos: int,
        captures: dict[str, bytes],
        field_bytes: list[bytes],
        field_idx: int,
    ) -> tuple[int, bytes] | None:
        expected = field.resolve_bytes()
        if pos + len(expected) > len(data):
            return None
        if data[pos : pos + len(expected)] != expected:
            return None
        field_bytes.append(expected)
        rest = self._match_fields(
            fields, data, pos + len(expected), captures, field_bytes, field_idx + 1
        )
        if rest is not None:
            end, suffix = rest
            return (end, expected + suffix)
        return None

    def _match_checksum(
        self,
        field: FieldDefinition,
        fields: list[FieldDefinition],
        data: bytes,
        pos: int,
        captures: dict[str, bytes],
        field_bytes: list[bytes],
        field_idx: int,
    ) -> tuple[int, bytes] | None:
        size = checksum_size(field.checksum_algorithm)
        if pos + size > len(data):
            return None

        scope_data = b"".join(
            field_bytes[i] for i in field.checksum_scope if i < len(field_bytes)
        )
        expected_val = compute(field.checksum_algorithm, scope_data)
        expected_bytes = expected_val.to_bytes(size, byteorder="big")

        actual_bytes = data[pos : pos + size]
        if actual_bytes != expected_bytes:
            return None

        field_bytes.append(actual_bytes)
        rest = self._match_fields(
            fields, data, pos + size, captures, field_bytes, field_idx + 1
        )
        if rest is not None:
            end, suffix = rest
            return (end, actual_bytes + suffix)
        return None

    def _match_wildcard(
        self,
        field: FieldDefinition,
        fields: list[FieldDefinition],
        data: bytes,
        pos: int,
        captures: dict[str, bytes],
        field_bytes: list[bytes],
        field_idx: int,
    ) -> tuple[int, bytes] | None:
        min_needed = self._min_bytes_for_fields(fields, field_idx + 1)
        min_consume = 1 if field.quantifier == "+" else 0

        max_consume = len(data) - pos - min_needed
        if max_consume < min_consume:
            return None

        for end in range(pos + max_consume, pos + min_consume - 1, -1):
            consumed = data[pos:end]
            field_bytes.append(consumed)
            rest = self._match_fields(
                fields, data, end, captures, field_bytes, field_idx + 1
            )
            if rest is not None:
                if field.capture_name:
                    captures[field.capture_name] = consumed
                end_pos, suffix = rest
                return (end_pos, consumed + suffix)
            field_bytes.pop()

        return None

    @staticmethod
    def _min_bytes_for_fields(fields: list[FieldDefinition], start_idx: int) -> int:
        total = 0
        for f in fields[start_idx:]:
            if f.field_type == "const":
                total += f.byte_length()
            elif f.field_type == "checksum":
                total += checksum_size(f.checksum_algorithm)
            elif f.field_type == "wildcard" and f.quantifier == "+":
                total += 1
        return total
