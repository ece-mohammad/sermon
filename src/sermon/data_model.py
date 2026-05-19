from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Literal

FieldType = Literal["const", "checksum", "wildcard"]
Quantifier = Literal["*", "+"]


@dataclass
class FieldDefinition:
    name: str
    field_type: FieldType = "const"
    value: str = ""
    checksum_algorithm: str = ""
    checksum_scope: list[int] = field(default_factory=list)
    capture_name: str = ""
    quantifier: Quantifier = "*"

    def byte_length(self) -> int:
        if self.field_type == "checksum":
            from sermon.checksum import checksum_size

            return checksum_size(self.checksum_algorithm)
        if self.field_type == "const":
            if not self.value:
                return 0
            val = self.value.replace(" ", "").replace("\t", "")
            return len(val) // 2
        return 0

    def resolve_bytes(self, captures: dict[str, bytes] | None = None) -> bytes:
        if self.field_type == "const":
            val = self.value.replace(" ", "").replace("\t", "")
            return bytes.fromhex(val)
        if self.field_type == "checksum":
            from sermon.checksum import compute

            if captures and self.capture_name in captures:
                scope_data = captures[self.capture_name]
            else:
                scope_data = b""
            result = compute(self.checksum_algorithm, scope_data)
            size = self.byte_length()
            return result.to_bytes(size, byteorder="big")
        if self.field_type == "wildcard" and captures:
            return captures.get(self.capture_name, b"")
        return b""


@dataclass
class SequenceDefinition:
    name: str = ""
    fields: list[FieldDefinition] = field(default_factory=list)

    def byte_length(self) -> int:
        return sum(f.byte_length() for f in self.fields)

    def resolve(self, captures: dict[str, bytes] | None = None) -> bytes:
        return b"".join(f.resolve_bytes(captures) for f in self.fields)


def _field_to_dict(f: FieldDefinition) -> dict:
    d = asdict(f)
    d["field_type"] = f.field_type
    return d


def sequence_to_json(seq: SequenceDefinition, indent: int = 2) -> str:
    d = asdict(seq)
    return json.dumps(d, indent=indent)


def sequence_from_json(data: str) -> SequenceDefinition:
    d = json.loads(data)
    fields = [FieldDefinition(**f) for f in d.get("fields", [])]
    return SequenceDefinition(name=d.get("name", ""), fields=fields)


def sequence_to_file(seq: SequenceDefinition, path: str) -> None:
    with open(path, "w") as f:
        f.write(sequence_to_json(seq))


def sequence_from_file(path: str) -> SequenceDefinition:
    with open(path) as f:
        return sequence_from_json(f.read())


@dataclass
class TriggerRule:
    name: str = ""
    send_sequence: SequenceDefinition | None = None
    receive_sequence: SequenceDefinition | None = None
    active: bool = True


def trigger_to_json(rule: TriggerRule, indent: int = 2) -> str:
    d = {"name": rule.name, "active": rule.active}
    if rule.send_sequence:
        d["send_sequence"] = asdict(rule.send_sequence)
    if rule.receive_sequence:
        d["receive_sequence"] = asdict(rule.receive_sequence)
    return json.dumps(d, indent=indent)


def trigger_from_json(data: str) -> TriggerRule:
    d = json.loads(data)
    send = None
    if "send_sequence" in d:
        fields = [FieldDefinition(**f) for f in d["send_sequence"].get("fields", [])]
        send = SequenceDefinition(
            name=d["send_sequence"].get("name", ""), fields=fields
        )
    recv = None
    if "receive_sequence" in d:
        fields = [FieldDefinition(**f) for f in d["receive_sequence"].get("fields", [])]
        recv = SequenceDefinition(
            name=d["receive_sequence"].get("name", ""), fields=fields
        )
    return TriggerRule(
        name=d.get("name", ""),
        send_sequence=send,
        receive_sequence=recv,
        active=d.get("active", True),
    )
