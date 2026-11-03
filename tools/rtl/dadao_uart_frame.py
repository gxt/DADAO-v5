#!/usr/bin/env python3
"""Test-only DADAO UART frame codec.

Wire format, all multi-byte fields are big-endian:

    MAGIC(4) | VERSION(1) | TYPE(1) | SEQ(2) |
    ADDRESS(8) | LENGTH(4) | PAYLOAD(LENGTH) | CRC32(4)

MAGIC is ASCII "DDAO". CRC32 covers VERSION through PAYLOAD. The format is
test infrastructure only and is not part of the DADAO architecture.
"""

from __future__ import annotations

import argparse
import json
import struct
import zlib
from dataclasses import dataclass
from typing import Final


MAGIC: Final[bytes] = b"DDAO"
VERSION: Final[int] = 1
HEADER: Final[struct.Struct] = struct.Struct(">4sBBHQI")
CRC: Final[struct.Struct] = struct.Struct(">I")
CRC_REGION: Final[struct.Struct] = struct.Struct(">BBHQI")
MIN_FRAME_BYTES: Final[int] = HEADER.size + CRC.size

FRAME_TYPE_CODES: Final[dict[str, int]] = {
    "load": 0x01,
    "run": 0x02,
    "result": 0x03,
    "error": 0x7F,
}
FRAME_TYPE_NAMES: Final[dict[int, str]] = {
    code: name for name, code in FRAME_TYPE_CODES.items()
}


class FrameError(ValueError):
    """A deterministic UART frame validation failure."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        message = reason if not detail else f"{reason}: {detail}"
        super().__init__(message)


@dataclass(frozen=True)
class Frame:
    frame_type: str
    sequence: int
    address: int
    payload: bytes


def _check_uint(value: int, bits: int, field: str) -> None:
    if value < 0 or value >= (1 << bits):
        raise FrameError(
            "field-range",
            f"{field}={value} does not fit in {bits} bits",
        )


def _normalize_type(frame_type: str | int) -> tuple[str, int]:
    if isinstance(frame_type, str):
        name = frame_type.lower()
        if name not in FRAME_TYPE_CODES:
            raise FrameError("unknown-type", frame_type)
        return name, FRAME_TYPE_CODES[name]

    if frame_type not in FRAME_TYPE_NAMES:
        raise FrameError("unknown-type", str(frame_type))
    return FRAME_TYPE_NAMES[frame_type], frame_type


def crc32_region(
    frame_type: int,
    sequence: int,
    address: int,
    payload: bytes,
) -> int:
    if frame_type not in FRAME_TYPE_NAMES:
        raise FrameError("unknown-type", str(frame_type))
    _check_uint(sequence, 16, "sequence")
    _check_uint(address, 64, "address")
    _check_uint(len(payload), 32, "length")

    region = CRC_REGION.pack(
        VERSION,
        frame_type,
        sequence,
        address,
        len(payload),
    ) + payload
    return zlib.crc32(region) & 0xFFFFFFFF


def encode_frame(
    frame_type: str | int,
    sequence: int,
    address: int,
    payload: bytes = b"",
) -> bytes:
    _, type_code = _normalize_type(frame_type)
    crc = crc32_region(type_code, sequence, address, payload)
    header = HEADER.pack(
        MAGIC,
        VERSION,
        type_code,
        sequence,
        address,
        len(payload),
    )
    return header + payload + CRC.pack(crc)


def decode_frame(data: bytes) -> Frame:
    if len(data) < MIN_FRAME_BYTES:
        raise FrameError(
            "truncated",
            f"got {len(data)} bytes, need at least {MIN_FRAME_BYTES}",
        )

    magic, version, type_code, sequence, address, length = (
        HEADER.unpack_from(data, 0)
    )
    if magic != MAGIC:
        raise FrameError("bad-magic", magic.hex())
    if version != VERSION:
        raise FrameError("bad-version", str(version))
    if type_code not in FRAME_TYPE_NAMES:
        raise FrameError("unknown-type", str(type_code))

    expected_length = HEADER.size + length + CRC.size
    if len(data) != expected_length:
        raise FrameError(
            "length-mismatch",
            f"header says {expected_length}, got {len(data)}",
        )

    payload_start = HEADER.size
    payload_end = payload_start + length
    payload = data[payload_start:payload_end]
    (received_crc,) = CRC.unpack_from(data, payload_end)
    expected_crc = crc32_region(
        type_code,
        sequence,
        address,
        payload,
    )
    if received_crc != expected_crc:
        raise FrameError(
            "crc-mismatch",
            f"expected {expected_crc:08x}, got {received_crc:08x}",
        )

    return Frame(
        frame_type=FRAME_TYPE_NAMES[type_code],
        sequence=sequence,
        address=address,
        payload=payload,
    )


def _expect_error(
    name: str,
    reason: str,
    data: bytes,
) -> int:
    try:
        decode_frame(data)
    except FrameError as error:
        if error.reason != reason:
            raise AssertionError(
                f"{name}: expected {reason}, got {error.reason}"
            ) from error
        print(f"[PASS] negative {name}: {error}")
        return 1
    raise AssertionError(f"{name}: decoder accepted invalid frame")


def selftest(force_failure: bool = False) -> int:
    payload = b"DDAO\xa5\x5a\x00\xff"
    positive = encode_frame("load", 0x1234, 0xFC0000000000, payload)
    decoded = decode_frame(positive)
    if decoded != Frame(
        frame_type="load",
        sequence=0x1234,
        address=0xFC0000000000,
        payload=payload,
    ):
        raise AssertionError("roundtrip mismatch")

    zero = decode_frame(encode_frame("run", 0, 0, b""))
    if zero.payload != b"" or zero.frame_type != "run":
        raise AssertionError("empty-payload roundtrip mismatch")
    print("[PASS] positive roundtrip with magic bytes inside payload")
    print(f"[INFO] frame_crc32=0x{positive[-4:].hex().upper()}")

    negative_cases = 0
    corrupted_magic = bytearray(positive)
    corrupted_magic[0] ^= 0xFF
    negative_cases += _expect_error(
        "bad-magic",
        "bad-magic",
        bytes(corrupted_magic),
    )

    corrupted_version = bytearray(positive)
    corrupted_version[4] = 2
    negative_cases += _expect_error(
        "bad-version",
        "bad-version",
        bytes(corrupted_version),
    )

    corrupted_type = bytearray(positive)
    corrupted_type[5] = 0x55
    negative_cases += _expect_error(
        "unknown-type",
        "unknown-type",
        bytes(corrupted_type),
    )

    corrupted_crc = bytearray(positive)
    corrupted_crc[-1] ^= 0x01
    negative_cases += _expect_error(
        "crc-mismatch",
        "crc-mismatch",
        bytes(corrupted_crc),
    )

    negative_cases += _expect_error(
        "missing-crc-byte",
        "length-mismatch",
        positive[:-1],
    )
    negative_cases += _expect_error(
        "truncated-header",
        "truncated",
        positive[:10],
    )
    negative_cases += _expect_error(
        "trailing-byte",
        "length-mismatch",
        positive + b"\x00",
    )

    if force_failure:
        raise AssertionError("forced selftest failure")

    print(f"[PASS] negative_cases={negative_cases}")
    print(f"SELFTEST PASS negative_cases={negative_cases}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Encode, decode, or selftest DADAO test UART frames."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    encode_parser = subparsers.add_parser("encode")
    encode_parser.add_argument(
        "--type",
        choices=sorted(FRAME_TYPE_CODES),
        required=True,
    )
    encode_parser.add_argument("--seq", type=lambda value: int(value, 0), required=True)
    encode_parser.add_argument(
        "--address",
        type=lambda value: int(value, 0),
        required=True,
    )
    encode_parser.add_argument("--payload-hex", default="")

    decode_parser = subparsers.add_parser("decode")
    decode_parser.add_argument("--frame-hex", required=True)

    selftest_parser = subparsers.add_parser("selftest")
    selftest_parser.add_argument("--force-failure", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "encode":
            payload = bytes.fromhex(args.payload_hex)
            frame = encode_frame(
                args.type,
                args.seq,
                args.address,
                payload,
            )
            print(frame.hex().upper())
            return 0
        if args.command == "decode":
            frame = decode_frame(bytes.fromhex(args.frame_hex))
            print(
                json.dumps(
                    {
                        "type": frame.frame_type,
                        "sequence": frame.sequence,
                        "address": f"0x{frame.address:016x}",
                        "payload_hex": frame.payload.hex().upper(),
                    },
                    sort_keys=True,
                )
            )
            return 0
        return selftest(args.force_failure)
    except (FrameError, ValueError) as error:
        print(f"ERROR: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
