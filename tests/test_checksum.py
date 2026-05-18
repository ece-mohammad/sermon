import pytest

from sermon.checksum import (
    checksum_size,
    compute,
    compute_crc8,
    compute_crc16,
    compute_crc32,
    compute_lrc,
    compute_mod256,
    list_algorithms,
)


class TestKnownVectors:
    """Verify against well-known CRC test vectors ("123456789")."""

    DATA = b"123456789"

    def test_crc8(self) -> None:
        assert compute_crc8(self.DATA) == 0xF4

    def test_crc16(self) -> None:
        assert compute_crc16(self.DATA) == 0xBB3D

    def test_crc32(self) -> None:
        assert compute_crc32(self.DATA) == 0xCBF43926


class TestLRC:
    def test_simple(self) -> None:
        assert compute_lrc(b"") == 0

    def test_single_byte(self) -> None:
        assert compute_lrc(bytes([0xAB])) == 0xAB

    def test_multi_byte(self) -> None:
        assert compute_lrc(bytes([0x01, 0x02, 0x03])) == 0x00

    def test_odd_parity(self) -> None:
        assert compute_lrc(bytes([0x01, 0x02, 0x03, 0x04])) == 0x04

    def test_all_same(self) -> None:
        assert compute_lrc(bytes([0xFF, 0xFF, 0xFF])) == 0xFF


class TestMOD256:
    def test_empty(self) -> None:
        assert compute_mod256(b"") == 0

    def test_single(self) -> None:
        assert compute_mod256(bytes([0x01])) == 0x01

    def test_sum_under_256(self) -> None:
        assert compute_mod256(bytes([0x10, 0x20, 0x30])) == 0x60

    def test_sum_over_256(self) -> None:
        assert compute_mod256(bytes([0xFF, 0x01])) == 0x00

    def test_wraparound(self) -> None:
        assert compute_mod256(bytes([0xFF, 0xFF])) == 0xFE


class TestCRC8:
    def test_empty(self) -> None:
        assert compute_crc8(b"") == 0x00

    def test_single_byte(self) -> None:
        data = bytes([0x41])
        crc = compute_crc8(data)
        assert isinstance(crc, int) and 0 <= crc <= 0xFF

    def test_different_inputs_differ(self) -> None:
        assert compute_crc8(b"hello") != compute_crc8(b"world")


class TestCRC16:
    def test_empty(self) -> None:
        assert compute_crc16(b"") == 0x0000

    def test_small_input(self) -> None:
        crc = compute_crc16(b"ab")
        assert isinstance(crc, int) and 0 <= crc <= 0xFFFF

    def test_different_inputs_differ(self) -> None:
        assert compute_crc16(b"hello") != compute_crc16(b"world")

    def test_known(self) -> None:
        assert compute_crc16(bytes([0x01, 0x02])) == 0x5180


class TestCRC32:
    def test_empty(self) -> None:
        assert compute_crc32(b"") == 0x00000000

    def test_range(self) -> None:
        crc = compute_crc32(b"hello")
        assert isinstance(crc, int) and 0 <= crc <= 0xFFFFFFFF

    def test_different_inputs_differ(self) -> None:
        assert compute_crc32(b"hello") != compute_crc32(b"world")


class TestGenericCompute:
    DATA = b"test data"

    def test_all_algorithms_accessible(self) -> None:
        for algo in list_algorithms():
            result = compute(algo, self.DATA)
            assert isinstance(result, int)

    def test_invalid_algorithm(self) -> None:
        with pytest.raises(ValueError, match="Unknown checksum algorithm"):
            compute("BAD-ALGO", b"")

    def test_consistency(self) -> None:
        for algo in list_algorithms():
            assert compute(algo, b"") == compute(algo, b"")


class TestChecksumSize:
    def test_sizes(self) -> None:
        assert checksum_size("LRC") == 1
        assert checksum_size("MOD256") == 1
        assert checksum_size("CRC-8") == 1
        assert checksum_size("CRC-16") == 2
        assert checksum_size("CRC-32") == 4

    def test_invalid_algorithm(self) -> None:
        with pytest.raises(ValueError, match="Unknown checksum algorithm"):
            checksum_size("BAD")


class TestListAlgorithms:
    def test_returns_all(self) -> None:
        algos = list_algorithms()
        expected = {"LRC", "MOD256", "CRC-8", "CRC-16", "CRC-32"}
        assert set(algos) == expected

    def test_order_stable(self) -> None:
        assert list_algorithms() == list_algorithms()
