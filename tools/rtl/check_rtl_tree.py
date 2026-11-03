#!/usr/bin/env python3
from __future__ import annotations

import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = (
    "rtl/dadao/build.sbt",
    "rtl/dadao/project/build.properties",
    "rtl/dadao/src/main/scala/dadao/DADAOParams.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOAddressMap.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOBlockMemExec.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOMemPort.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOByteLane.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOLoadExec.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOStoreExec.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOCfx.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOControlExec.scala",
    "rtl/dadao/src/main/scala/dadao/DADAORas.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOCore.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOCpu.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOTile.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOTileLink.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOConfig.scala",
    "rtl/dadao/src/main/scala/dadao/DADAOElaborator.scala",
    "rtl/dadao/src/test/scala/dadao/DADAOMemPortSpec.scala",
    "rtl/dadao/src/test/scala/dadao/DADAOAddressMapSpec.scala",
    "rtl/dadao/src/test/scala/dadao/DADAOBlockMemExecSpec.scala",
    "rtl/dadao/src/test/scala/dadao/DADAOLoadExecSpec.scala",
    "rtl/dadao/src/test/scala/dadao/DADAOStoreExecSpec.scala",
    "rtl/dadao/src/test/scala/dadao/DADAOCpuSpec.scala",
    "rtl/dadao/src/test/scala/dadao/DADAOBubbleSortProgram.scala",
    "rtl/dadao/src/test/scala/dadao/DADAOBubbleSortSpec.scala",
    "rtl/dadao/src/test/scala/dadao/DADAOTLAdapterSpec.scala",
    "rtl/dadao/src/test/scala/dadao/DADAOTLMemorySpec.scala",
    "tests/rtl/core/RTL-012t-bubble-sort-program.yaml",
    "tests/rtl/core/RTL-012t-bubble-sort-program.hex",
    "tests/rtl/core/RTL-012t-bubble-sort-program.bin",
    "tools/rtl/generate_dadao_bubble_sort.py",
)


def require_text(path: Path, snippets: tuple[str, ...], errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for snippet in snippets:
        if snippet not in text:
            errors.append(f"{path.relative_to(ROOT)}: missing {snippet!r}")


def require_pattern(path: Path, patterns: tuple[tuple[str, str], ...], errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    code = strip_comments(text)
    for label, pattern in patterns:
        if re.search(pattern, code) is None:
            errors.append(f"{path.relative_to(ROOT)}: missing {label}")


def strip_comments(text: str) -> str:
    output: list[str] = []
    index = 0
    block_comment_depth = 0
    quote: str | None = None

    while index < len(text):
        current = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""

        if block_comment_depth > 0:
            if current == "/" and following == "*":
                block_comment_depth += 1
                index += 2
            elif current == "*" and following == "/":
                block_comment_depth -= 1
                index += 2
            else:
                if current == "\n":
                    output.append("\n")
                index += 1
            continue

        if quote is not None:
            output.append(current)
            if current == "\\" and following:
                output.append(following)
                index += 2
            else:
                if current == quote:
                    quote = None
                index += 1
            continue

        if current == "/" and following == "/":
            while index < len(text) and text[index] != "\n":
                index += 1
            continue

        if current == "/" and following == "*":
            block_comment_depth = 1
            index += 2
            continue

        if current in ('"', "'"):
            quote = current

        output.append(current)
        index += 1

    return "".join(output)


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing required file: {relative}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    build = ROOT / "rtl/dadao/build.sbt"
    props = ROOT / "rtl/dadao/project/build.properties"
    params = ROOT / "rtl/dadao/src/main/scala/dadao/DADAOParams.scala"
    address_map = (
        ROOT / "rtl/dadao/src/main/scala/dadao/DADAOAddressMap.scala"
    )
    block_mem = (
        ROOT / "rtl/dadao/src/main/scala/dadao/DADAOBlockMemExec.scala"
    )
    mem = ROOT / "rtl/dadao/src/main/scala/dadao/DADAOMemPort.scala"
    core = ROOT / "rtl/dadao/src/main/scala/dadao/DADAOCore.scala"
    cpu = ROOT / "rtl/dadao/src/main/scala/dadao/DADAOCpu.scala"
    tile = ROOT / "rtl/dadao/src/main/scala/dadao/DADAOTile.scala"
    tilelink = ROOT / "rtl/dadao/src/main/scala/dadao/DADAOTileLink.scala"
    config = ROOT / "rtl/dadao/src/main/scala/dadao/DADAOConfig.scala"
    elaborator = ROOT / "rtl/dadao/src/main/scala/dadao/DADAOElaborator.scala"

    require_pattern(
        build,
        (
            ("Scala 2.13.16", r'scalaVersion\s*:=\s*"2\.13\.16"'),
            ("Chisel 6.7.0", r'"org\.chipsalliance"\s+%%\s+"chisel"\s+%\s+"6\.7\.0"'),
            ("Chisel plugin 6.7.0", r'"org\.chipsalliance"\s+%\s+"chisel-plugin"\s+%\s+"6\.7\.0"'),
            ("chiseltest 6.0.0", r'"edu\.berkeley\.cs"\s+%%\s+"chiseltest"\s+%\s+"6\.0\.0"'),
        ),
        errors,
    )
    require_text(props, ("sbt.version=1.8.2",), errors)
    require_text(
        params,
        (
            "resetVector",
            "ramBase",
            "bootRomBase",
            "bootRomSize",
            "uartBase",
            "uartSize",
            "addrBits",
            "dataBits",
        ),
        errors,
    )
    require_text(
        mem,
        (
            "class DADAOMemReq",
            "val addr",
            "val write",
            "val size",
            "val wdata",
            "val kind",
            "class DADAOMemResp",
            "val rdata",
            "val fault",
            "val faultCode",
            "class DADAOMemPort",
            "val req",
            "val resp",
        ),
        errors,
    )
    require_pattern(
        address_map,
        (
            ("DADAOAccessCheck class", r"class\s+DADAOAccessCheck\b"),
            ("RAM mapping", r"ramHit\b"),
            ("BootROM mapping", r"bootRomHit\b"),
            ("UNMAPPED fault", r"DADAOFaultCode\.Unmapped\b"),
            ("MALIGN fault", r"DADAOFaultCode\.Malign\b"),
            ("ILLI fault", r"DADAOFaultCode\.Illi\b"),
        ),
        errors,
    )
    require_pattern(
        block_mem,
        (
            ("DADAOBlockMemExec class", r"class\s+DADAOBlockMemExec\b"),
            ("RD/RB/RA target bank", r"DADAORegBank\.(Rd|Rb|Ra)\b"),
            ("block count", r"val\s+count\s*=\s*io\.decoded\.word\(5, 0\)"),
            ("block write data", r"requestWdata\b"),
            ("block load extension", r"loadValue\b"),
        ),
        errors,
    )
    require_pattern(
        core,
        (
            ("DADAOCore class", r"class\s+DADAOCore\b"),
            ("memory port", r"val\s+mem\b"),
            ("pc port", r"val\s+pc\b"),
        ),
        errors,
    )
    require_pattern(
        tile,
        (
            ("DADAOTile class", r"class\s+DADAOTile\b"),
            ("DADAOTileModuleImp class", r"class\s+DADAOTileModuleImp\b"),
            ("BaseTile inheritance", r"extends\s+BaseTile\b"),
            ("CPU top instantiation", r"Module\s*\(\s*new\s+DADAOCpuTop\b"),
        ),
        errors,
    )
    require_pattern(
        cpu,
        (
            ("DADAOCpuTop class", r"class\s+DADAOCpuTop\b"),
            ("Core instantiation", r"Module\s*\(\s*new\s+DADAOCore\b"),
            ("TileLink adapter", r"Module\s*\(\s*new\s+DADAOTLAdapter\b"),
            ("TileLink crossbar", r"Module\s*\(\s*new\s+DADAOTLXbar\b"),
            ("BootROM manager", r"Module\s*\(\s*new\s+DADAOTLROM\b"),
            ("RAM manager", r"Module\s*\(\s*new\s+DADAOTLRAM\b"),
        ),
        errors,
    )
    require_pattern(
        tilelink,
        (
            ("Adapter class", r"class\s+DADAOTLAdapter\b"),
            ("Crossbar class", r"class\s+DADAOTLXbar\b"),
            ("BootROM class", r"class\s+DADAOTLROM\b"),
            ("RAM class", r"class\s+DADAOTLRAM\b"),
            ("Get message", r"\bGet\s*:\s*Int\s*=\s*4"),
            ("PutFullData message", r"\bPutFullData\s*:\s*Int\s*=\s*0"),
            ("PutPartialData message", r"\bPutPartialData\s*:\s*Int\s*=\s*1"),
        ),
        errors,
    )
    require_pattern(
        config,
        (
            ("DADAOConfig class", r"class\s+DADAOConfig\b"),
            ("WithDADAOTile class", r"class\s+WithDADAOTile\b"),
            ("DADAO tile attach", r"DADAOTileAttachParams\b"),
        ),
        errors,
    )
    require_pattern(
        elaborator,
        (
            ("DADAOElaborator object", r"object\s+DADAOElaborator\b"),
            ("DADAOTop class", r"class\s+DADAOTop\b"),
            ("Tile instantiation", r"LazyModule\s*\(\s*new\s+DADAOTile\b"),
            ("CHIRRTL emission", r"emitCHIRRTL\b"),
        ),
        errors,
    )

    forbidden = ("wuming", "wuming_1stage", "wuming_5stage", "setzw", "breq", "brne", "unimp")
    for path in (ROOT / "rtl/dadao").rglob("*.scala"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token.lower() in text.lower():
                errors.append(f"{path.relative_to(ROOT)}: forbidden legacy token {token!r}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("rtl tree check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
