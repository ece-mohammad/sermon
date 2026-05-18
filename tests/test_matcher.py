from sermon.checksum import compute
from sermon.data_model import FieldDefinition, SequenceDefinition
from sermon.matcher import MatchResult, SequenceMatcher


def make_matcher(*fields: FieldDefinition) -> SequenceMatcher:
    return SequenceMatcher(SequenceDefinition(fields=list(fields)))


def match(seq: SequenceDefinition, data: bytes):
    return SequenceMatcher(seq).match(data)


class TestConstMatching:
    def test_exact_match(self) -> None:
        fields = [FieldDefinition("a", "const", "AA")]
        result = match(SequenceDefinition(fields=fields), bytes([0xAA]))
        assert result is not None
        assert result.matched_bytes == bytes([0xAA])

    def test_no_match(self) -> None:
        fields = [FieldDefinition("a", "const", "AA")]
        result = match(SequenceDefinition(fields=fields), bytes([0xBB]))
        assert result is None

    def test_match_at_offset(self) -> None:
        fields = [FieldDefinition("a", "const", "AA")]
        result = match(SequenceDefinition(fields=fields), bytes([0xFF, 0xAA]))
        assert result is not None
        assert result.matched_bytes == bytes([0xAA])
        assert result.remaining == b""

    def test_multi_const(self) -> None:
        fields = [
            FieldDefinition("a", "const", "AA"),
            FieldDefinition("b", "const", "BB"),
        ]
        result = match(SequenceDefinition(fields=fields), bytes([0xAA, 0xBB]))
        assert result is not None
        assert result.matched_bytes == bytes([0xAA, 0xBB])

    def test_data_too_short(self) -> None:
        fields = [FieldDefinition("a", "const", "AABB")]
        result = match(SequenceDefinition(fields=fields), bytes([0xAA]))
        assert result is None

    def test_remaining_bytes(self) -> None:
        fields = [FieldDefinition("a", "const", "AA")]
        result = match(SequenceDefinition(fields=fields), bytes([0xAA, 0xBB, 0xCC]))
        assert result is not None
        assert result.remaining == bytes([0xBB, 0xCC])

    def test_no_match_on_random(self) -> None:
        fields = [FieldDefinition("a", "const", "AA")]
        result = match(SequenceDefinition(fields=fields), bytes([0xFF, 0xEE, 0xDD]))
        assert result is None


class TestWildcardStar:
    def test_capture_bytes(self) -> None:
        fields = [
            FieldDefinition("sof", "const", "AA"),
            FieldDefinition("p", "wildcard", capture_name="p"),
            FieldDefinition("eof", "const", "55"),
        ]
        result = match(
            SequenceDefinition(fields=fields), bytes([0xAA, 0x01, 0x02, 0x55])
        )
        assert result is not None
        assert result.captures["p"] == bytes([0x01, 0x02])

    def test_empty_capture(self) -> None:
        fields = [
            FieldDefinition("sof", "const", "AA"),
            FieldDefinition("p", "wildcard", capture_name="p"),
            FieldDefinition("eof", "const", "55"),
        ]
        result = match(SequenceDefinition(fields=fields), bytes([0xAA, 0x55]))
        assert result is not None
        assert result.captures["p"] == b""

    def test_no_capture_name_still_matches(self) -> None:
        fields = [
            FieldDefinition("sof", "const", "AA"),
            FieldDefinition("p", "wildcard"),
            FieldDefinition("eof", "const", "55"),
        ]
        result = match(SequenceDefinition(fields=fields), bytes([0xAA, 0x01, 0x55]))
        assert result is not None

    def test_no_trailing_const(self) -> None:
        fields = [
            FieldDefinition("sof", "const", "AA"),
            FieldDefinition("p", "wildcard", capture_name="p"),
        ]
        result = match(SequenceDefinition(fields=fields), bytes([0xAA, 0x01, 0x02]))
        assert result is not None
        assert result.captures["p"] == bytes([0x01, 0x02])

    def test_only_wildcard(self) -> None:
        fields = [FieldDefinition("p", "wildcard", capture_name="p")]
        result = match(SequenceDefinition(fields=fields), bytes([0x01, 0x02, 0x03]))
        assert result is not None
        assert result.captures["p"] == bytes([0x01, 0x02, 0x03])

    def test_only_wildcard_empty_data(self) -> None:
        fields = [FieldDefinition("p", "wildcard", capture_name="p")]
        result = match(SequenceDefinition(fields=fields), b"")
        assert result is not None
        assert result.captures["p"] == b""

    def test_multiple_wildcards(self) -> None:
        fields = [
            FieldDefinition("a", "wildcard", capture_name="a"),
            FieldDefinition("sep", "const", "BB"),
            FieldDefinition("b", "wildcard", capture_name="b"),
        ]
        result = match(
            SequenceDefinition(fields=fields), bytes([0x01, 0x02, 0xBB, 0x03, 0x04])
        )
        assert result is not None
        assert result.captures["a"] == bytes([0x01, 0x02])
        assert result.captures["b"] == bytes([0x03, 0x04])

    def test_greedy_gives_back(self) -> None:
        fields = [
            FieldDefinition("pre", "const", "AB"),
            FieldDefinition("x", "wildcard", capture_name="x"),
            FieldDefinition("mid", "const", "CD"),
            FieldDefinition("y", "wildcard", capture_name="y"),
            FieldDefinition("end", "const", "EF"),
        ]
        result = match(
            SequenceDefinition(fields=fields), bytes([0xAB, 0xBB, 0x03, 0xCD, 0xEF])
        )
        assert result is not None
        assert result.captures["x"] == bytes([0xBB, 0x03])
        assert result.captures["y"] == b""

    def test_wildcard_across_embedded_const_bytes(self) -> None:
        fields = [
            FieldDefinition("pre", "const", "AA"),
            FieldDefinition("x", "wildcard", capture_name="x"),
            FieldDefinition("suf", "const", "BB"),
        ]
        result = match(
            SequenceDefinition(fields=fields), bytes([0xAA, 0x01, 0xAA, 0x02, 0xBB])
        )
        assert result is not None
        assert result.captures["x"] == bytes([0x01, 0xAA, 0x02])


class TestWildcardPlus:
    def test_capture_bytes(self) -> None:
        fields = [
            FieldDefinition("pre", "const", "AA"),
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
        ]
        result = match(SequenceDefinition(fields=fields), bytes([0xAA, 0x01, 0x02]))
        assert result is not None
        assert result.captures["p"] == bytes([0x01, 0x02])

    def test_rejects_empty(self) -> None:
        fields = [
            FieldDefinition("pre", "const", "AA"),
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
        ]
        result = match(SequenceDefinition(fields=fields), bytes([0xAA]))
        assert result is None

    def test_rejects_empty_data(self) -> None:
        fields = [FieldDefinition("p", "wildcard", capture_name="p", quantifier="+")]
        result = match(SequenceDefinition(fields=fields), b"")
        assert result is None

    def test_greedy_plus_then_star(self) -> None:
        fields = [
            FieldDefinition("pre", "const", "AB"),
            FieldDefinition("x", "wildcard", capture_name="x", quantifier="+"),
            FieldDefinition("mid", "const", "CD"),
            FieldDefinition("y", "wildcard", capture_name="y"),
        ]
        result = match(
            SequenceDefinition(fields=fields), bytes([0xAB, 0xCD, 0xCD, 0xEF])
        )
        assert result is not None
        # greedy x+ takes as much as possible (1 byte: CD), then CD const matches
        # at pos 2, then y* takes remaining (EF)
        assert result.captures["x"] == bytes([0xCD])
        assert result.captures["y"] == bytes([0xEF])

    def test_requires_at_least_one(self) -> None:
        fields = [
            FieldDefinition("pre", "const", "AA"),
            FieldDefinition("x", "wildcard", capture_name="x", quantifier="+"),
            FieldDefinition("suf", "const", "BB"),
        ]
        # AA must be followed by at least 1 byte before BB
        result = match(SequenceDefinition(fields=fields), bytes([0xAA, 0xBB]))
        assert result is None


class TestChecksumVerification:
    def test_lrc_match(self) -> None:
        payload = bytes([0x10, 0x20, 0x30])
        lrc = compute("LRC", payload)
        fields = [
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
            FieldDefinition(
                "crc",
                "checksum",
                checksum_algorithm="LRC",
                checksum_scope=[0],
                capture_name="p",
            ),
        ]
        result = match(SequenceDefinition(fields=fields), payload + bytes([lrc]))
        assert result is not None
        assert result.captures["p"] == payload

    def test_lrc_mismatch(self) -> None:
        fields = [
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
            FieldDefinition(
                "crc",
                "checksum",
                checksum_algorithm="LRC",
                checksum_scope=[0],
                capture_name="p",
            ),
        ]
        result = match(SequenceDefinition(fields=fields), bytes([0x01, 0x02, 0xFF]))
        assert result is None

    def test_mod256_match(self) -> None:
        payload = bytes([0xA0, 0xB0])
        chk = compute("MOD256", payload)
        fields = [
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
            FieldDefinition(
                "crc",
                "checksum",
                checksum_algorithm="MOD256",
                checksum_scope=[0],
                capture_name="p",
            ),
        ]
        result = match(SequenceDefinition(fields=fields), payload + bytes([chk]))
        assert result is not None

    def test_mod256_mismatch(self) -> None:
        fields = [
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
            FieldDefinition(
                "crc",
                "checksum",
                checksum_algorithm="MOD256",
                checksum_scope=[0],
                capture_name="p",
            ),
        ]
        result = match(SequenceDefinition(fields=fields), bytes([0x01, 0xFF]))
        assert result is None

    def test_crc8_match(self) -> None:
        payload = bytes([0x05, 0x06])
        chk = compute("CRC-8", payload)
        fields = [
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
            FieldDefinition(
                "crc",
                "checksum",
                checksum_algorithm="CRC-8",
                checksum_scope=[0],
                capture_name="p",
            ),
        ]
        result = match(SequenceDefinition(fields=fields), payload + bytes([chk]))
        assert result is not None

    def test_crc8_mismatch(self) -> None:
        fields = [
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
            FieldDefinition(
                "crc",
                "checksum",
                checksum_algorithm="CRC-8",
                checksum_scope=[0],
                capture_name="p",
            ),
        ]
        result = match(SequenceDefinition(fields=fields), bytes([0x05, 0x06, 0xFF]))
        assert result is None

    def test_crc16_match(self) -> None:
        payload = bytes([0x01, 0x02])
        chk = compute("CRC-16", payload)
        fields = [
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
            FieldDefinition(
                "crc",
                "checksum",
                checksum_algorithm="CRC-16",
                checksum_scope=[0],
                capture_name="p",
            ),
        ]
        result = match(
            SequenceDefinition(fields=fields), payload + chk.to_bytes(2, "big")
        )
        assert result is not None

    def test_crc16_mismatch(self) -> None:
        fields = [
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
            FieldDefinition(
                "crc",
                "checksum",
                checksum_algorithm="CRC-16",
                checksum_scope=[0],
                capture_name="p",
            ),
        ]
        result = match(
            SequenceDefinition(fields=fields), bytes([0x01, 0x02, 0x00, 0x00])
        )
        assert result is None

    def test_crc32_match(self) -> None:
        payload = bytes([0x01, 0x02, 0x03])
        chk = compute("CRC-32", payload)
        fields = [
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
            FieldDefinition(
                "crc",
                "checksum",
                checksum_algorithm="CRC-32",
                checksum_scope=[0],
                capture_name="p",
            ),
        ]
        result = match(
            SequenceDefinition(fields=fields), payload + chk.to_bytes(4, "big")
        )
        assert result is not None

    def test_crc32_mismatch(self) -> None:
        fields = [
            FieldDefinition("p", "wildcard", capture_name="p", quantifier="+"),
            FieldDefinition(
                "crc",
                "checksum",
                checksum_algorithm="CRC-32",
                checksum_scope=[0],
                capture_name="p",
            ),
        ]
        result = match(
            SequenceDefinition(fields=fields),
            bytes([0x01, 0x02, 0x03]) + bytes([0xDE, 0xAD, 0xBE, 0xEF]),
        )
        assert result is None

    def test_multiple_checksums(self) -> None:
        p1 = bytes([0x01])
        p2 = bytes([0x02])
        c1 = compute("CRC-8", p1)
        c2 = compute("CRC-16", p2)
        fields = [
            FieldDefinition("a", "const", "AA"),
            FieldDefinition("p1", "wildcard", capture_name="p1", quantifier="+"),
            FieldDefinition(
                "c1",
                "checksum",
                checksum_algorithm="CRC-8",
                checksum_scope=[1],
                capture_name="p1",
            ),
            FieldDefinition("p2", "wildcard", capture_name="p2", quantifier="+"),
            FieldDefinition(
                "c2",
                "checksum",
                checksum_algorithm="CRC-16",
                checksum_scope=[3],
                capture_name="p2",
            ),
            FieldDefinition("eof", "const", "BB"),
        ]
        data = (
            bytes([0xAA])
            + p1
            + bytes([c1])
            + p2
            + c2.to_bytes(2, "big")
            + bytes([0xBB])
        )
        result = match(SequenceDefinition(fields=fields), data)
        assert result is not None
        assert result.captures["p1"] == p1
        assert result.captures["p2"] == p2


class TestMatchAll:
    def test_non_overlapping(self) -> None:
        fields = [FieldDefinition("a", "const", "AA")]
        matcher = make_matcher(*fields)
        results = matcher.match_all(bytes([0xAA, 0xBB, 0xAA, 0xCC, 0xAA]))
        assert len(results) == 3

    def test_no_matches(self) -> None:
        fields = [FieldDefinition("a", "const", "AA")]
        matcher = make_matcher(*fields)
        results = matcher.match_all(bytes([0xBB, 0xCC]))
        assert len(results) == 0

    def test_empty_data(self) -> None:
        fields = [FieldDefinition("a", "const", "AA")]
        matcher = make_matcher(*fields)
        results = matcher.match_all(b"")
        assert len(results) == 0

    def test_contiguous_matches(self) -> None:
        fields = [FieldDefinition("a", "const", "AA")]
        matcher = make_matcher(*fields)
        results = matcher.match_all(bytes([0xAA, 0xAA, 0xAA]))
        assert len(results) == 3

    def test_match_all_with_wildcard(self) -> None:
        fields = [
            FieldDefinition("sof", "const", "AA"),
            FieldDefinition("p", "wildcard", capture_name="p"),
            FieldDefinition("eof", "const", "55"),
        ]
        matcher = make_matcher(*fields)
        results = matcher.match_all(bytes([0xAA, 0x01, 0x55, 0xAA, 0x02, 0x55]))
        # greedy * captures everything up to the last AA, backtracking to last 55
        # For non-overlapping matches, only 1 match is found because * is greedy
        # and absorbs the bytes before the final 55 AA 02 55
        assert len(results) == 1
        assert results[0].captures["p"] == bytes([0x01, 0x55, 0xAA, 0x02])


class TestMatchResultStructure:
    def test_captures_is_dict(self) -> None:
        r = MatchResult()
        assert isinstance(r.captures, dict)

    def test_matched_bytes_is_bytes(self) -> None:
        r = MatchResult()
        assert isinstance(r.matched_bytes, bytes)

    def test_remaining_is_bytes(self) -> None:
        r = MatchResult()
        assert isinstance(r.remaining, bytes)


class TestGreedyBacktracking:
    def test_wildcard_gives_back_for_trailing_const(self) -> None:
        fields = [
            FieldDefinition("x", "wildcard", capture_name="x"),
            FieldDefinition("end", "const", "FF"),
        ]
        result = match(SequenceDefinition(fields=fields), bytes([0x01, 0x02, 0xFF]))
        assert result is not None
        assert result.captures["x"] == bytes([0x01, 0x02])

    def test_multiple_give_backs(self) -> None:
        fields = [
            FieldDefinition("a", "const", "AB"),
            FieldDefinition("x", "wildcard", capture_name="x"),
            FieldDefinition("b", "const", "CD"),
            FieldDefinition("y", "wildcard", capture_name="y"),
            FieldDefinition("c", "const", "EF"),
        ]
        # AB xx CD yy EF — x and y must split the middle bytes
        result = match(
            SequenceDefinition(fields=fields),
            bytes([0xAB, 0x01, 0x02, 0xCD, 0x03, 0x04, 0xEF]),
        )
        assert result is not None
        assert result.captures["x"] == bytes([0x01, 0x02])
        assert result.captures["y"] == bytes([0x03, 0x04])

    def test_deep_backtrack_on_plus(self) -> None:
        fields = [
            FieldDefinition("a", "const", "AB"),
            FieldDefinition("x", "wildcard", capture_name="x", quantifier="+"),
            FieldDefinition("b", "const", "CD"),
            FieldDefinition("y", "wildcard", capture_name="y"),
        ]
        # AB CD CD EF → greedy x+ takes max (1 byte: CD), CD const matches at pos 2,
        # y* takes remaining (EF)
        result = match(
            SequenceDefinition(fields=fields), bytes([0xAB, 0xCD, 0xCD, 0xEF])
        )
        assert result is not None
        assert result.captures["x"] == bytes([0xCD])
        assert result.captures["y"] == bytes([0xEF])


class TestEdgeCases:
    def test_unknown_field_type_returns_none(self) -> None:
        f = FieldDefinition("x", field_type="invalid_type")  # type: ignore[arg-type]
        result = match(SequenceDefinition(fields=[f]), bytes([0x01]))
        assert result is None

    def test_empty_fields_list(self) -> None:
        result = match(SequenceDefinition(fields=[]), bytes([0x01, 0x02]))
        assert result is not None
        assert result.matched_bytes == b""

    def test_whitespace_in_hex_value(self) -> None:
        fields = [FieldDefinition("a", "const", "AA BB")]
        result = match(SequenceDefinition(fields=fields), bytes([0xAA, 0xBB]))
        assert result is not None

    def test_partial_prefix_match(self) -> None:
        fields = [FieldDefinition("a", "const", "AABB")]
        result = match(SequenceDefinition(fields=fields), bytes([0xFF, 0xAA]))
        assert result is None

    def test_long_data_stream(self) -> None:
        fields = [
            FieldDefinition("sof", "const", "AA"),
            FieldDefinition("p", "wildcard", capture_name="p"),
            FieldDefinition("eof", "const", "55"),
        ]
        payload = bytes(range(1, 100))
        data = bytes([0xAA]) + payload + bytes([0x55])
        result = match(SequenceDefinition(fields=fields), data)
        assert result is not None
        assert result.captures["p"] == payload
        assert len(result.matched_bytes) == 101
