"""Assembly `.ascii` payload parsing shared by the Linux gates.

Extracted from the retired bare-metal semihosting smoke driver: K1 needs the
same source-text oracle to rebuild a console stream from `.ascii` literals
without asking the assembler or QEMU.
"""
from __future__ import annotations

import re

_ESCAPES = {
    "n": b"\n", "t": b"\t", "r": b"\r", "0": b"\0",
    "\\": b"\\", '"': b'"', "'": b"'",
}


class CheckError(RuntimeError):
    """A required property did not hold (exit 1)."""


def decode_asm_string(text: str) -> bytes:
    """Decode one `.ascii "…"` payload (C escapes only; UTF-8 stays verbatim)."""
    out = bytearray()
    i = 0
    while i < len(text):
        char = text[i]
        if char != "\\":
            out += char.encode("utf-8")
            i += 1
            continue
        if i + 1 >= len(text):
            raise CheckError("dangling backslash in an .ascii literal")
        esc = text[i + 1]
        if esc in _ESCAPES:
            out += _ESCAPES[esc]
            i += 2
            continue
        raise CheckError(f"unsupported escape '\\{esc}' in an .ascii literal")
    return bytes(out)


def ascii_payloads(line: str) -> list[bytes]:
    return [decode_asm_string(m) for m in re.findall(r'\.ascii\s+"((?:[^"\\]|\\.)*)"', line)]
