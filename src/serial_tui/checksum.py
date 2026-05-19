from typing import Callable

from crccheck.crc import Crc8, Crc16Arc, Crc32


def compute_lrc(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b
    return crc & 0xFF


def compute_mod256(data: bytes) -> int:
    total = sum(data)
    return total & 0xFF


def compute_crc8(data: bytes) -> int:
    return Crc8.calc(data)


def compute_crc16(data: bytes) -> int:
    return Crc16Arc.calc(data)


def compute_crc32(data: bytes) -> int:
    return Crc32.calc(data)


_CHECKSUM_FUNCS: dict[str, Callable[[bytes], int]] = {
    "LRC": compute_lrc,
    "MOD256": compute_mod256,
    "CRC-8": compute_crc8,
    "CRC-16": compute_crc16,
    "CRC-32": compute_crc32,
}

_CHECKSUM_SIZES: dict[str, int] = {
    "LRC": 1,
    "MOD256": 1,
    "CRC-8": 1,
    "CRC-16": 2,
    "CRC-32": 4,
}


def compute(algorithm: str, data: bytes) -> int:
    func = _CHECKSUM_FUNCS.get(algorithm)
    if func is None:
        msg = f"Unknown checksum algorithm: {algorithm!r}"
        raise ValueError(msg)
    return func(data)


def checksum_size(algorithm: str) -> int:
    size = _CHECKSUM_SIZES.get(algorithm)
    if size is None:
        msg = f"Unknown checksum algorithm: {algorithm!r}"
        raise ValueError(msg)
    return size


def list_algorithms() -> list[str]:
    return list(_CHECKSUM_FUNCS.keys())
