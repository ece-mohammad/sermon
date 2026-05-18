from typing import Callable


def _build_crc8_table(poly: int = 0x07) -> list[int]:
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ poly) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
        table.append(crc)
    return table


def _build_crc16r_table(poly: int = 0xA001) -> list[int]:
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 0x0001:
                crc = ((crc >> 1) ^ poly) & 0xFFFF
            else:
                crc = (crc >> 1) & 0xFFFF
        table.append(crc)
    return table


def _build_crc32r_table(poly: int = 0xEDB88320) -> list[int]:
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 0x00000001:
                crc = ((crc >> 1) ^ poly) & 0xFFFFFFFF
            else:
                crc = (crc >> 1) & 0xFFFFFFFF
        table.append(crc)
    return table


CRC8_TABLE = _build_crc8_table()
CRC16R_TABLE = _build_crc16r_table()
CRC32R_TABLE = _build_crc32r_table()


def compute_lrc(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b
    return crc & 0xFF


def compute_mod256(data: bytes) -> int:
    total = sum(data)
    return total & 0xFF


def compute_crc8(data: bytes) -> int:
    crc = 0
    for b in data:
        crc = CRC8_TABLE[(crc ^ b) & 0xFF]
    return crc & 0xFF


def compute_crc16(data: bytes) -> int:
    crc = 0
    for b in data:
        crc = ((crc >> 8) ^ CRC16R_TABLE[(crc ^ b) & 0xFF]) & 0xFFFF
    return crc & 0xFFFF


def compute_crc32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for b in data:
        crc = ((crc >> 8) ^ CRC32R_TABLE[(crc ^ b) & 0xFF]) & 0xFFFFFFFF
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


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
