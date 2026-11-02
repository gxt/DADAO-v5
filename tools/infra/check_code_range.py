#!/usr/bin/env python3
"""check-code-range: DADAO 代码跨度门控（ADR-0036 D4/D7）。

读取**链接后**的 DADAO ELF（可执行 / DSO，链接时带 ``-Wl,--emit-relocs``），
逐产物报告：

  * ``max_rel26_edge``：最远 ``R_DADAO_REL26``（``call`` / ``jump``）边的
    字节距离，以及 ``margin = 32 MiB - max_rel26_edge``；
  * ``max_rel20_edge`` / ``max_rel14_edge``：条件分支边（只报告，ADR-0036
    只对 REL26 设硬约束）；
  * ``exec_span``：全部 ``SHF_EXECINSTR`` 段的 ``[min, max)`` 跨度。

判据（单一真源 = 本文件顶部常量；ADR-0036 D4/D7）：

  * 任一 REL26 边 > 32 MiB            ⇒ rc=1
  * ``exec_span >= 30 MiB``           ⇒ rc=1
  * 其余                              ⇒ rc=0
  * 输入不合约（非 DADAO / 非 ELF64-BE / 缺 ``.rela.*``）⇒ rc=2（fail-closed）

为什么读重定位而不是反汇编立即数：已链接指令的 ``imms24`` 本身装不下
> 32 MiB 的边（linker 先硬报错），所以「越界 ⇒ 红」的可达反例只能来自
重定位记录里的 ``S + A - P``；``--emit-relocs`` 恰好保留 ``.rela.*`` 与完整
``.symtab``，两者都在，可直接求值（ADR-0036 Context 事实 1/3）。

Usage::

    tools/infra/check_code_range.py [--self-test] [--keep] ELF [ELF ...]

临时文件：``/tmp/opencode/INFRA-106t/``。
"""
from __future__ import annotations

import argparse
import shutil
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

WORK_ROOT = Path("/tmp/opencode/INFRA-106t")

MIB = 1024 * 1024

# ── 判据阈值（单一真源；ADR-0036 D4/D7）───────────────────────────────────────
REL26_LIMIT = 32 * MIB          # 硬约束：任一 REL26 调用边 ≤ 32 MiB
REL20_LIMIT = 512 * 1024        # 仅报告（branch relaxation 目标范围）
REL14_LIMIT = 8 * 1024          # 仅报告
EXEC_SPAN_LIMIT = 30 * MIB      # 打包预算：单 DSO 可执行区跨度 < 30 MiB

# ── ELF / DADAO 常量 ──────────────────────────────────────────────────────────
EM_DADAO = 0x0DA0
ET_EXEC = 2
ET_DYN = 3
SHT_SYMTAB = 2
SHT_RELA = 4
SHT_NOBITS = 8
SHT_DYNSYM = 11
SHF_EXECINSTR = 0x4
EHDR_SIZE = 64
SHDR_SIZE = 64
SYM_SIZE = 24
RELA_SIZE = 24

# 类型号真源：.tao/contracts/contract-elf.md §2.2（REL26=1 / REL20=2 / REL14=3）
RELOC_TYPES = {1: "REL26", 2: "REL20", 3: "REL14"}

_LIMITS = {
    1: REL26_LIMIT,
    2: REL20_LIMIT,
    3: REL14_LIMIT,
}


class ElfError(Exception):
    """输入 ELF 不合约 / 无法解析（fail-closed，rc=2）。"""


@dataclass
class Section:
    index: int
    name: str
    sh_type: int
    flags: int
    addr: int
    offset: int
    size: int
    link: int
    info: int
    entsize: int


@dataclass
class Edge:
    distance: int          # abs(S + A - P)
    signed_value: int      # S + A - P
    p: int
    s: int
    addend: int
    section: str


@dataclass
class Product:
    path: Path
    exec_sections: list[Section] = field(default_factory=list)
    exec_min: int = 0
    exec_max: int = 0
    exec_span: int = 0
    max_edge: dict[int, Edge] = field(default_factory=dict)
    counts: dict[int, int] = field(default_factory=dict)
    rela_sections: int = 0


def _unpack(fmt: str, data: bytes, offset: int, what: str):
    size = struct.calcsize(fmt)
    if offset < 0 or offset + size > len(data):
        raise ElfError(f"截断的 {what}（offset=0x{offset:x}, need={size} B）")
    return struct.unpack_from(fmt, data, offset)


def _cstr(data: bytes, offset: int, end: int, what: str) -> str:
    if not 0 <= offset < end <= len(data):
        raise ElfError(f"字符串偏移越界：{what} @0x{offset:x}")
    stop = data.find(b"\0", offset, end)
    if stop < 0:
        raise ElfError(f"未终止的字符串：{what} @0x{offset:x}")
    return data[offset:stop].decode("utf-8", "replace")


def parse_elf(path: Path) -> tuple[bytes, int, list[Section]]:
    """解析 ELF64 大端 DADAO 的段表；不合约 ⇒ ``ElfError``。"""
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ElfError(f"无法读取：{exc}") from exc

    if len(data) < EHDR_SIZE:
        raise ElfError("文件短于 ELF64 头（64 B）")
    if data[:4] != b"\x7fELF":
        raise ElfError("不是 ELF 文件（magic 不符）")
    if data[4] != 2:
        raise ElfError(f"EI_CLASS={data[4]}（要求 ELFCLASS64=2）")
    if data[5] != 2:
        raise ElfError(f"EI_DATA={data[5]}（要求 ELFDATA2MSB=2；contract-elf §1.1）")

    (e_type, e_machine, _version, _entry, _phoff, shoff, _flags,
     _ehsize, _phentsize, _phnum, shentsize, shnum, shstrndx) = _unpack(
        ">HHIQQQIHHHHHH", data, 16, "Elf64_Ehdr")

    if e_machine != EM_DADAO:
        raise ElfError(f"e_machine=0x{e_machine:04x}（要求 EM_DADAO=0x0da0）")
    if e_type not in (ET_EXEC, ET_DYN):
        raise ElfError(f"e_type={e_type}（要求 ET_EXEC=2 或 ET_DYN=3 的链接产物）")
    if shnum == 0 or shoff == 0:
        raise ElfError("无段表（shnum=0 / shoff=0）")
    if shentsize != SHDR_SIZE:
        raise ElfError(f"e_shentsize={shentsize}（要求 {SHDR_SIZE}）")
    if shstrndx == 0 or shstrndx >= shnum:
        raise ElfError(f"e_shstrndx={shstrndx} 越界（shnum={shnum}）")

    raw: list[tuple[int, ...]] = []
    for i in range(shnum):
        raw.append(_unpack(">IIQQQQIIQQ", data, shoff + i * SHDR_SIZE,
                           f"section header[{i}]"))

    str_hdr = raw[shstrndx]
    str_off, str_size = str_hdr[4], str_hdr[5]
    if str_off + str_size > len(data):
        raise ElfError("shstrtab 越界")
    str_end = str_off + str_size

    sections: list[Section] = []
    for i, fields in enumerate(raw):
        (sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size,
         sh_link, sh_info, _sh_addralign, sh_entsize) = fields
        if sh_type not in (0, SHT_NOBITS) and sh_offset + sh_size > len(data):
            raise ElfError(f"段 {i} 数据越界（offset=0x{sh_offset:x} size=0x{sh_size:x}）")
        sections.append(Section(
            index=i,
            name=_cstr(data, str_off + sh_name, str_end, f"section[{i}].sh_name"),
            sh_type=sh_type,
            flags=sh_flags,
            addr=sh_addr,
            offset=sh_offset,
            size=sh_size,
            link=sh_link,
            info=sh_info,
            entsize=sh_entsize,
        ))
    return data, e_type, sections


def _symbol_value(data: bytes, symtab: Section, sym_index: int) -> int:
    entsize = symtab.entsize or SYM_SIZE
    if entsize != SYM_SIZE:
        raise ElfError(f"{symtab.name}: sh_entsize={entsize}（要求 {SYM_SIZE}）")
    if symtab.size % entsize:
        raise ElfError(f"{symtab.name}: size={symtab.size} 不是 {entsize} 的整数倍")
    count = symtab.size // entsize
    if sym_index >= count:
        raise ElfError(f"符号索引 {sym_index} 越界（{symtab.name} 有 {count} 项）")
    fields = _unpack(">IBBHQQ", data, symtab.offset + sym_index * entsize,
                     f"symbol[{sym_index}]")
    return fields[4]  # st_value


def scan(path: Path) -> Product:
    """扫描单个 ELF：exec_span + REL26/REL20/REL14 最远边。"""
    data, _e_type, sections = parse_elf(path)
    product = Product(path=path)
    product.counts = {1: 0, 2: 0, 3: 0}

    exec_sections = [s for s in sections if s.flags & SHF_EXECINSTR and s.size > 0]
    product.exec_sections = exec_sections
    if exec_sections:
        product.exec_min = min(s.addr for s in exec_sections)
        product.exec_max = max(s.addr + s.size for s in exec_sections)
        product.exec_span = product.exec_max - product.exec_min

    rela_sections = [s for s in sections if s.sh_type == SHT_RELA]
    product.rela_sections = len(rela_sections)
    if not rela_sections:
        raise ElfError("无 SHT_RELA 段：请用 -Wl,--emit-relocs 链接后再跑本门控"
                       "（ADR-0036 D7：跨度由重定位实测）")
    # `.rela.dyn` 这类动态重定位段在**未带 --emit-relocs** 的 DSO 里也存在，
    # 不能当作「链接期代码重定位已保留」的证据。必须有至少一个重定位段的
    # sh_info 指向 SHF_EXECINSTR 段（`.rela.text` / `.rela.init` …），否则
    # 无法验证代码跨度 ⇒ fail-closed，防 DSO 静默假绿。
    code_rela = [s for s in rela_sections
                 if 0 < s.info < len(sections)
                 and sections[s.info].flags & SHF_EXECINSTR]
    if not code_rela:
        raise ElfError("没有指向 SHF_EXECINSTR 段的重定位段（如 .rela.text）："
                       "请用 -Wl,--emit-relocs 链接（ADR-0036 D7）")

    for rela in rela_sections:
        if rela.link <= 0 or rela.link >= len(sections):
            raise ElfError(f"{rela.name}: sh_link={rela.link} 越界")
        symtab = sections[rela.link]
        if symtab.sh_type not in (SHT_SYMTAB, SHT_DYNSYM):
            raise ElfError(f"{rela.name}: sh_link 指向 {symtab.name}"
                           f"（sh_type={symtab.sh_type}），不是符号表")
        if rela.info >= len(sections):
            raise ElfError(f"{rela.name}: sh_info={rela.info} 越界")
        # .rela.dyn 的 sh_info 允许为 0（无单一目标段）；ET_EXEC/ET_DYN 的
        # r_offset 本身就是 VA，不需要目标段。

        entsize = rela.entsize or RELA_SIZE
        if entsize != RELA_SIZE:
            raise ElfError(f"{rela.name}: sh_entsize={entsize}（要求 {RELA_SIZE}）")
        if rela.size % entsize:
            raise ElfError(f"{rela.name}: size={rela.size} 不是 {entsize} 的整数倍")
        entries = rela.size // entsize

        for i in range(entries):
            r_offset, r_info, r_addend = _unpack(
                ">QQq", data, rela.offset + i * entsize, f"{rela.name}[{i}]")
            r_type = r_info & 0xFFFFFFFF
            if r_type not in RELOC_TYPES:
                continue
            sym_index = r_info >> 32
            s = _symbol_value(data, symtab, sym_index)
            # ELF r_offset 语义：ET_EXEC/ET_DYN 为 VA（已绝对；本工具只接受
            # 这两类链接产物），故 P = r_offset。
            p = r_offset
            value = s + r_addend - p
            distance = abs(value)
            product.counts[r_type] += 1
            best = product.max_edge.get(r_type)
            if best is None or distance > best.distance:
                product.max_edge[r_type] = Edge(
                    distance=distance,
                    signed_value=value,
                    p=p,
                    s=s,
                    addend=r_addend,
                    section=rela.name,
                )
    return product


def violations(products: list[Product]) -> list[str]:
    """按 ADR-0036 D4/D7 判据返回违规描述（空 = 绿）。"""
    found: list[str] = []
    for product in products:
        rel26 = product.max_edge.get(1)
        if rel26 is not None and rel26.distance > REL26_LIMIT:
            found.append(
                f"REL26 边 {rel26.distance} B > {REL26_LIMIT} B（32 MiB）："
                f"{product.path} {rel26.section} @0x{rel26.p:x} "
                f"S+A-P={rel26.signed_value}"
            )
        if product.exec_span >= EXEC_SPAN_LIMIT:
            found.append(
                f"exec_span {product.exec_span} B >= {EXEC_SPAN_LIMIT} B（30 MiB）："
                f"{product.path} [0x{product.exec_min:x}, 0x{product.exec_max:x})"
            )
    return found


def _mib_text(value: int) -> str:
    return f"{value / MIB:.2f} MiB"


def _edge_line(product: Product, rtype: int) -> str:
    edge = product.max_edge.get(rtype)
    limit = _LIMITS[rtype]
    if edge is None:
        return "no relocation"
    return (f"{edge.distance} B (0x{edge.distance:x}), "
            f"S+A-P={edge.signed_value}, @0x{edge.p:x}, limit {limit} B"
            f" ({_mib_text(limit)})")


def report(products: list[Product]) -> None:
    print("check-code-range — DADAO 代码跨度门控（ADR-0036 D4/D7）")
    print(f"阈值（单一真源）：REL26 ≤ {REL26_LIMIT} B (32 MiB)；"
          f"exec_span < {EXEC_SPAN_LIMIT} B (30 MiB)")
    for product in products:
        exec_note = (f"[0x{product.exec_min:x}, 0x{product.exec_max:x}), "
                     f"{len(product.exec_sections)} 个 SHF_EXECINSTR 段")
        flag = "OVER" if product.exec_span >= EXEC_SPAN_LIMIT else "ok"
        print(f"  [{product.path}]")
        print(f"    exec_span      : {product.exec_span} B "
              f"({_mib_text(product.exec_span)}) {exec_note} [{flag}]")
        for rtype in (1, 2, 3):
            name = RELOC_TYPES[rtype]
            edge = product.max_edge.get(rtype)
            distance = edge.distance if edge is not None else 0
            margin = _LIMITS[rtype] - distance
            extra = f", margin {margin} B ({_mib_text(margin)})" if rtype == 1 else ""
            flag = ""
            if rtype == 1:
                flag = " [OVER]" if margin < 0 else " [ok]"
            print(f"    max_{name.lower()}_edge : {_edge_line(product, rtype)}{extra}{flag}")
        print(f"    relocations    : "
              f"REL26={product.counts[1]} REL20={product.counts[2]} "
              f"REL14={product.counts[3]}（现场统计，来自 {product.rela_sections} 个 .rela.* 段）")


# ---------------------------------------------------------------------------
# --self-test：纯 stdlib 合成 fixture，不依赖 toolchain / 不重构建。
# ---------------------------------------------------------------------------

def build_fixture(path: Path, sections: list[dict], symbol: dict,
                  relocs: list[dict]) -> None:
    """写一个最小 ELF64-BE DADAO 可执行镜像。

    ``sections``：``{"name", "type", "flags", "addr", "data"}``（按索引 1..n）。
    ``symbol``：``{"value", "shndx"}``（符号表第 1 项，名为 ``target``）。
    ``relocs``：``{"shndx", "offset", "type", "addend"}``（符号固定为索引 1）。
    """
    n = len(sections)
    has_rela = bool(relocs)
    # 空 rela 段不能算「带 --emit-relocs」的证据：无重定位时干脆不生成该段。
    symtab_index = n + 1 + (1 if has_rela else 0)
    strtab_index = symtab_index + 1
    shstrtab_index = strtab_index + 1

    strtab = b"\0target\0"
    symtab = b"\0" * SYM_SIZE + struct.pack(
        ">IBBHQQ", 1, 0x12, 0, symbol["shndx"], symbol["value"], 16)

    rela = b"".join(
        struct.pack(">QQq", rel["offset"], (1 << 32) | rel["type"], rel["addend"])
        for rel in relocs
    )

    names = [sec["name"] for sec in sections]
    if has_rela:
        names.append(".rela.text")
    names += [".symtab", ".strtab", ".shstrtab"]
    shstr = bytearray(b"\0")
    name_off: dict[str, int] = {}
    for name in names:
        name_off[name] = len(shstr)
        shstr += name.encode() + b"\0"

    blobs: list[tuple[str, bytes]] = []
    for sec in sections:
        blobs.append((sec["name"], sec["data"]))
    if has_rela:
        blobs.append((".rela.text", rela))
    blobs.append((".symtab", symtab))
    blobs.append((".strtab", strtab))
    blobs.append((".shstrtab", bytes(shstr)))

    body = bytearray(EHDR_SIZE)
    offsets: dict[str, int] = {}
    for name, blob in blobs:
        while len(body) % 8:
            body += b"\0"
        offsets[name] = len(body)
        body += blob
    while len(body) % 8:
        body += b"\0"
    shoff = len(body)

    headers: list[bytes] = [b"\0" * SHDR_SIZE]  # section 0
    for i, sec in enumerate(sections, start=1):
        headers.append(struct.pack(
            ">IIQQQQIIQQ",
            name_off[sec["name"]], sec["type"], sec["flags"], sec["addr"],
            offsets[sec["name"]], len(sec["data"]), 0, 0, 8, 0))
    if has_rela:
        # 所有 fixture 的重定位都挂在 section 1（.text）上。
        headers.append(struct.pack(
            ">IIQQQQIIQQ", name_off[".rela.text"], SHT_RELA, 0, 0,
            offsets[".rela.text"], len(rela), symtab_index, 1,
            8, RELA_SIZE))
    headers.append(struct.pack(
        ">IIQQQQIIQQ", name_off[".symtab"], SHT_SYMTAB, 0, 0,
        offsets[".symtab"], len(symtab), strtab_index, 1, 8, SYM_SIZE))
    headers.append(struct.pack(
        ">IIQQQQIIQQ", name_off[".strtab"], 3, 0, 0,
        offsets[".strtab"], len(strtab), 0, 0, 1, 0))
    headers.append(struct.pack(
        ">IIQQQQIIQQ", name_off[".shstrtab"], 3, 0, 0,
        offsets[".shstrtab"], len(shstr), 0, 0, 1, 0))
    body += b"".join(headers)

    ehdr = struct.pack(
        ">4sBBBB8sHHIQQQIHHHHHH",
        b"\x7fELF", 2, 2, 1, 0, b"\0" * 8,
        ET_EXEC, EM_DADAO, 1,
        sections[0]["addr"], 0, shoff, 1,
        EHDR_SIZE, 0, 0, SHDR_SIZE, len(headers), shstrtab_index)
    body[:EHDR_SIZE] = ehdr
    path.write_bytes(body)


def _fixture_specs() -> dict[str, tuple[list[dict], dict, list[dict]]]:
    """正常 / 远距 REL26 / 超预算 exec_span / 缺重定位 四类 fixture。"""
    text = {"name": ".text", "type": 1, "flags": 0x4 | 0x2, "addr": 0x1000,
            "data": b"\0" * 16}
    small_relocs = [
        {"shndx": 1, "offset": 0x1004, "type": 1, "addend": 0},
        {"shndx": 1, "offset": 0x1008, "type": 2, "addend": 0},
        {"shndx": 1, "offset": 0x100C, "type": 3, "addend": 0},
    ]
    normal = ([text], {"value": 0x1008, "shndx": 1}, small_relocs)

    # 远距 REL26：目标放在非可执行远端段，隔离「REL26 判据」本身
    # （exec_span 由下面的 span fixture 单独测）。
    far_target = {"name": ".far", "type": 1, "flags": 0, "addr": 0x2002000,
                  "data": b"\0" * 16}
    far_value = 0x2002008  # P=0x1004 ⇒ S+A-P = 0x2001004 > 32 MiB
    far_rel26 = ([text, far_target], {"value": far_value, "shndx": 2},
                 [{"shndx": 1, "offset": 0x1004, "type": 1, "addend": 0}])

    # 可执行区跨度 = 30 MiB + 16 B ≥ 30 MiB（REL26 边仍很小）。
    text_a = dict(text, addr=0x1000)
    text_b = dict(text, name=".text.b", addr=0x1000 + EXEC_SPAN_LIMIT)
    span = ([text_a, text_b], {"value": 0x1008, "shndx": 1},
            [{"shndx": 1, "offset": 0x1004, "type": 1, "addend": 0}])

    # 无 .rela.*：输入不合约（未带 --emit-relocs）⇒ fail-closed。
    no_relocs = ([text], {"value": 0x1008, "shndx": 1}, [])
    return {
        "normal.elf": normal,
        "far_rel26.elf": far_rel26,
        "far_span.elf": span,
        "no_relocs.elf": no_relocs,
    }


def _write_fixtures(root: Path) -> dict[str, Path]:
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, (sections, symbol, relocs) in _fixture_specs().items():
        path = root / name
        build_fixture(path, sections, symbol, relocs)
        paths[name] = path
    return paths


def self_test(keep: bool = False) -> int:
    print("=" * 72)
    print("check-code-range --self-test（合成 fixture；正常绿、远距红）")
    print("=" * 72)
    root = WORK_ROOT / "code-range-selftest"
    paths = _write_fixtures(root)
    print(f"fixtures: {root}（现场生成，{len(paths)} 个）")

    failures = 0

    def case(label: str, expected_rc: int, products_spec: list[Path],
             must_contain: tuple[str, ...] = ()) -> None:
        nonlocal failures
        try:
            products = [scan(path) for path in products_spec]
            bad = violations(products)
            actual_rc = 1 if bad else 0
            text = "\n".join(bad)
        except ElfError as exc:
            actual_rc = 2
            text = str(exc)
        hit = all(item in text for item in must_contain)
        ok = actual_rc == expected_rc and hit
        if not ok:
            failures += 1
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: expected rc={expected_rc}"
              f"{' + ' + repr(must_contain) if must_contain else ''}, "
              f"actual rc={actual_rc}")
        for line in text.splitlines():
            print(f"        | {line}")
        if expected_rc == 0 and actual_rc == 0:
            for product in products:
                edge = product.max_edge.get(1)
                print(f"        | {product.path.name}: exec_span={product.exec_span} B, "
                      f"max_rel26={edge.distance if edge else 0} B, "
                      f"counts={product.counts}")

    case("normal fixture ⇒ green", 0, [paths["normal.elf"]])
    case("far REL26 fixture ⇒ red + names product/edge", 1,
         [paths["far_rel26.elf"]],
         must_contain=("REL26", "far_rel26.elf", str(0x2002008 - 0x1004)))
    case("far exec_span fixture ⇒ red + names product/span", 1,
         [paths["far_span.elf"]],
         must_contain=("exec_span", "far_span.elf", str(EXEC_SPAN_LIMIT + 16)))
    case("missing .rela.* fixture ⇒ fail-closed rc=2", 2,
         [paths["no_relocs.elf"]], must_contain=("emit-relocs",))
    case("multi-file: normal + far ⇒ red (any product fails)", 1,
         [paths["normal.elf"], paths["far_rel26.elf"]],
         must_contain=("far_rel26.elf",))

    # 逐条核对上面的「正常」不是恒绿：改阈值（内存内）后同一 fixture 必须转红。
    global REL26_LIMIT, _LIMITS  # noqa: PLW0603 - test-only, restore below
    saved = REL26_LIMIT
    try:
        REL26_LIMIT = 1
        _LIMITS[1] = 1
        product = scan(paths["normal.elf"])
        bad = violations([product])
        ok = bool(bad) and "REL26" in bad[0]
        if not ok:
            failures += 1
        print(f"[{'PASS' if ok else 'FAIL'}] threshold injection: "
              f"expected red at REL26 limit=1, actual={bad or 'green'}")
    finally:
        REL26_LIMIT = saved
        _LIMITS[1] = saved
    product = scan(paths["normal.elf"])
    ok = not violations([product])
    if not ok:
        failures += 1
    print(f"[{'PASS' if ok else 'FAIL'}] threshold restore: expected green, "
          f"actual={'green' if ok else violations([product])}")

    if keep:
        print(f"self-test: fixtures kept at {root}")
    else:
        shutil.rmtree(root, ignore_errors=True)

    print("-" * 72)
    if failures:
        print(f"check-code-range --self-test: FAIL ({failures} case(s))")
        return 1
    print("check-code-range --self-test: PASS（正常绿 / 远距红 / 缺重定位 fail-closed）")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="DADAO 代码跨度门控（ADR-0036 D4/D7）")
    parser.add_argument("elf", nargs="*", type=Path,
                        help="一个或多个 DADAO ELF（链接时带 -Wl,--emit-relocs）")
    parser.add_argument("--self-test", action="store_true",
                        help="跑合成 fixture 自检（不依赖 toolchain / 不重构建）")
    parser.add_argument("--keep", action="store_true",
                        help="自检后保留 fixture（打印路径）")
    args = parser.parse_args()

    if args.self_test:
        if args.elf:
            parser.error("--self-test 不接受 ELF 参数")
        return self_test(keep=args.keep)
    if not args.elf:
        parser.error("至少给一个 ELF 路径（或用 --self-test）")

    products: list[Product] = []
    input_errors = 0
    for path in args.elf:
        try:
            products.append(scan(path))
        except ElfError as exc:
            input_errors += 1
            print(f"  [INPUT ERROR] {path}: {exc}", file=sys.stderr)

    if products:
        report(products)
    bad = violations(products)

    print("-" * 72)
    for line in bad:
        print(f"  VIOLATION: {line}")
    if input_errors:
        print(f"check-code-range: INPUT ERROR（{input_errors} 个产物无法验证；"
              "fail-closed）")
        return 2
    if bad:
        print(f"check-code-range: FAIL（{len(bad)} 项越界；ADR-0036 D4/D7）")
        return 1
    print("check-code-range: PASS（REL26 边 ≤ 32 MiB 且 exec_span < 30 MiB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
