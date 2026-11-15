#!/usr/bin/env python3
"""check_k0.py — M14 K0 closure gate (`make check-linux-k0`; `m14-infra-003`).

Cross-product closure over the whole K0 batch: the kernel image, the initramfs,
the toolchain matrix, the boot-ABI contract and the patch series are asserted
**together**, because each of them has its own local gate but nothing checked
that the four still agree with each other.

Every expectation is derived live — this file never restates one:

  * boot ABI numbers  -> ``contracts/linux-boot.yaml`` (the machine-readable
    projection; the human contract + the spec text are compared against it by
    ``check_boot_contract.py``, which this gate calls for K11);
  * toolchain rows    -> ``tools/linux/toolchain_matrix.json`` + live probes via
    ``check_toolchain.py`` (K10);
  * initramfs layout  -> the generator's own manifest + the projection;
  * runtime paths     -> ``tools/linux/paths.py`` (manifest-derived; no host
    path appears in this file);
  * patch series      -> ``manifests/components.lock.toml`` + ``components/linux/series``.

Assertions (each one has a reachable FAIL; ``--inject`` proves it):

  K1   vmlinux exists and parses (incremental build runs first)
  K2   ELF64 / big endian / ``e_machine`` / ``ET_EXEC`` / ``e_flags`` version
  K3   ``e_entry == kernel_base``
  K4   allowed program-header types; per ``PT_LOAD``: ``p_vaddr - p_paddr ==
       va_pa_offset``, 64 KiB page alignment/align, ``p_filesz <= p_memsz``,
       ``[p_vaddr, p_vaddr + p_memsz)`` inside the kernel image area
  K5   no ``PT_LOAD`` touches the boot reserved area, and every address stays
       inside the 42-bit memory window (BootROM lives in cfxha 63 and hmon SRAM
       in cfxha 3 => both are outside that window, so they are provably
       disjoint from a segment that satisfies this)
  K6   ``llvm-nm -u vmlinux`` is empty
  K7   initramfs ``newc``: ``.`` + ``init`` (0100755) + ``TRAILER!!!``; payload
       == the built init ELF == the manifest sha256
  K8   a second generation in a scratch directory is byte-identical
  K9   initramfs size <= the initramfs area; the init ELF is static (no
       ``PT_INTERP`` / ``PT_DYNAMIC``)
  K10  ``check_toolchain.py`` logic returns 0
  K11  ``check_boot_contract.py`` logic returns 0
  K12  ``apply-series`` is idempotent for linux: two runs rc=0, ``HEAD``
       unchanged, worktree clean, ``rev-list --count <base>..HEAD`` equal to the
       live-derived expectation (1 for a non-empty series, 0 for an empty one)
  K13  the live counts must agree with the artefacts they were parsed from:
       ``sum(p_filesz)`` of the ``PT_LOAD`` segments <= the vmlinux size, the
       ``PT_LOAD`` file ranges are pairwise non-overlapping, ``sum(entry size)``
       of the cpio entries <= the archive size, and at least ``.`` + TRAILER;
       the totals themselves are printed, never hardcoded

Fail-closed: a missing product, build tree or prerequisite is a FAIL that names
the `make` target to run.  There is **no SKIP** anywhere in this file.

Usage:

  python3 tools/linux/check_k0.py                 # gate (`make check-linux-k0`)
  python3 tools/linux/check_k0.py --no-build      # assert only, never build
  python3 tools/linux/check_k0.py --inject        # self-check on tampered copies

`--inject` copies the products / projection / matrix into a scratch directory,
tampers with the copy and asserts the *target* judgement fails; the real
artefacts are never modified (their md5 is re-checked at the end).

Exit status: 0 = every check passed; 1 = at least one FAIL; 2 = input
unreadable/unparseable (no expectation can be derived).
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.linux import make_defconfig as defconfig  # noqa: E402
from tools.linux import make_initramfs  # noqa: E402
from tools.linux import paths as linux_paths  # noqa: E402

CONTRACT_REL = Path("contracts/linux-boot.yaml")
MATRIX_REL = Path("tools/linux/toolchain_matrix.json")
COMPONENTS_LOCK_REL = Path("manifests/components.lock.toml")
TOOLCHAIN_SCRIPT_REL = Path("tools/linux/check_toolchain.py")
BOOT_CONTRACT_SCRIPT_REL = Path("tools/linux/check_boot_contract.py")
APPLY_SERIES_SCRIPT_REL = Path("tools/infra/apply_series.py")
INITRAMFS_SCRIPT_REL = Path("tools/linux/make_initramfs.py")

#: ELF constants the contract names by symbol (the numbers are the ELF ones, the
#: contract's prose is asserted to point at them -- see `Projection`).
ET_EXEC = 2
ELFCLASS64 = 2
PT_LOAD, PT_DYNAMIC, PT_INTERP, PT_NOTE, PT_GNU_STACK = 1, 2, 3, 4, 0x6474E551
#: Program-header types that are *not* loaded and that a static kernel/init image
#: legitimately carries (`ELF-PT-LOAD`: only PT_LOAD is loaded).  Anything else
#: (PT_INTERP, PT_DYNAMIC, ...) means the image is not the static executable the
#: boot ABI describes.
NON_LOADING_TYPES = {PT_NOTE: "NOTE", PT_GNU_STACK: "GNU_STACK"}
CPIO_MAGIC = b"070701"
CPIO_TRAILER = "TRAILER!!!"

#: Wall-clock guards.  `timeout` => rc 124, which is a FAIL (AGENTS.md「长任务」).
#: The image this gate inspects: the K1 stop is on, the K2 symbols are
#: explicitly off (m14-linux-006 config slices keep the shared build tree
#: deterministic no matter which gate ran last).
K0_CONFIG = [
    "CONFIG_DADAO_K1_EARLY_STOP=y",
    "CONFIG_DADAO_K2_EARLY_STOP=n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST=n",
]

TIMEOUT_VMLINUX = int(os.environ.get("K0_VMLINUX_TIMEOUT", "3600"))
TIMEOUT_INITRAMFS = int(os.environ.get("K0_INITRAMFS_TIMEOUT", "600"))
TIMEOUT_TOOLCHAIN = int(os.environ.get("K0_TOOLCHAIN_TIMEOUT", "600"))
TIMEOUT_BOOT_CONTRACT = int(os.environ.get("K0_BOOT_CONTRACT_TIMEOUT", "300"))
TIMEOUT_SERIES = int(os.environ.get("K0_SERIES_TIMEOUT", "900"))
#: `timeout`'s exit code; kept symbolic so every caller can be checked for it.
TIMEOUT_RC = 124


# ---------------------------------------------------------------------------
# paths / small helpers
# ---------------------------------------------------------------------------

def _rel(path: Path) -> str:
    """Rendering that never prints a host absolute path.

    ``tools/linux/paths.py`` returns ``realpath``-resolved paths (the work root
    may be a symlink), so anchor on the ``.work`` component instead of on the
    checkout root; everything else degrades to ``<path>``.
    """
    parts = Path(path).parts
    if ".work" in parts:
        return "/".join(parts[parts.index(".work"):])
    for base in (ROOT, ROOT.resolve()):
        try:
            return Path(path).relative_to(base).as_posix()
        except ValueError:
            continue
    return "<path>"


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fmt_hex(value: int, width: int = 0) -> str:
    digits = f"{value:0{width}x}" if width else f"{value:x}"
    return "0x" + digits


def run_script(
    rel: Path,
    args: list[str],
    *,
    timeout: int,
    env: dict[str, str] | None = None,
) -> tuple[int, str]:
    """Run a repo script; return (rc, combined output).  rc=124 means timeout."""
    cmd = [sys.executable, str(ROOT / rel), *args]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.output or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return TIMEOUT_RC, out + f"\n<timeout {timeout}s>"
    except OSError as exc:
        return 127, f"<cannot exec: {exc}>"
    return proc.returncode, proc.stdout or ""


def git_out(source: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(source), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 1, f"<git {args[0]} failed: {exc}>"
    return proc.returncode, proc.stdout or ""


# ---------------------------------------------------------------------------
# expectation projection (the single source of every number below)
# ---------------------------------------------------------------------------

class ProjectionError(RuntimeError):
    """The projection no longer carries a value this gate needs (fail-closed)."""


@dataclass
class Projection:
    """Boot-ABI expectations, derived from ``contracts/linux-boot.yaml``."""

    kernel_start: int
    kernel_end: int
    initramfs_va: int
    initramfs_limit: int
    ram_base: int
    reserved_end: int
    entry: int
    page_size: int
    va_pa_offset: int
    va_width_bits: int
    ei_data: int
    e_machine: int
    e_flags_version: int


def _rule_text(data: dict, rule_id: str) -> str:
    for rule in data.get("rules") or []:
        if rule.get("id") == rule_id:
            return str(rule.get("rule") or "")
    raise ProjectionError(f"投影缺装载规则 {rule_id}")


def derive_projection(path: Path) -> Projection:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ProjectionError(f"投影无法读取/解析: {exc}") from exc
    try:
        fields = {f["name"]: f for f in data["boot_info"]["fields"]}
        memory = {row["name"]: row for row in data["memory_map"]}
        address_model = data["address_model"]
        startup = data["startup_model"]

        kernel_start = int(memory["kernel"]["start"])
        kernel_end = int(memory["kernel"]["end"])
        initramfs_va = int(memory["initramfs"]["start"])
        initramfs_limit = int(memory["initramfs"]["end"]) - initramfs_va
        ram_base = int(fields["ram_base"]["value"])
        page_table_start = int(memory["page_table"]["start"])
        reserved_end = int(memory["boot_info"]["end"])
        entry = int(fields["kernel_base"]["value"])
        page_size = int(startup["page_size"])
        va_pa_offset = int(address_model["va_pa_offset"])
        va_width_bits = int(address_model["va_width_bits"])
        boot_info_va = int(data["boot_info"]["va"])
        boot_info_size = int(data["boot_info"]["size"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectionError(f"投影缺字段或类型不符: {exc}") from exc

    # The prose rules carry the two values that have no structured field; parse
    # them instead of restating them here.
    elf_format = _rule_text(data, "ELF-FORMAT")
    match = re.search(r"e_machine\s*=\s*(0x[0-9A-Fa-f]+)", elf_format)
    if not match:
        raise ProjectionError("ELF-FORMAT 规则未给出 e_machine 取值")
    e_machine = int(match.group(1), 16)
    if "ET_EXEC" not in elf_format:
        raise ProjectionError("ELF-FORMAT 规则未点名 ET_EXEC")
    match = re.search(r"e_flags`?\s*版本字段\s*=\s*(\d+)", elf_format)
    if not match:
        raise ProjectionError("ELF-FORMAT 规则未给出 e_flags 版本字段取值")
    e_flags_version = int(match.group(1))
    match = re.search(r"EI_DATA\s*=\s*(\d+)", elf_format)
    if not match:
        raise ProjectionError("ELF-FORMAT 规则未给出 EI_DATA 取值")
    ei_data = int(match.group(1))
    if "ELFCLASS64" not in elf_format:
        raise ProjectionError("ELF-FORMAT 规则未点名 ELFCLASS64")

    # Structured cross-checks: these values are used as *bounds*, so a
    # projection that lost its internal coherence must stop the gate here.
    if entry != kernel_start:
        raise ProjectionError(
            f"投影自身不一致: kernel_base({_fmt_hex(entry)}) != 内核区起点"
            f"({_fmt_hex(kernel_start)})")
    if boot_info_va + boot_info_size > reserved_end:
        raise ProjectionError(
            f"投影自身不一致: boot info 区终点({_fmt_hex(reserved_end)}) 小于 "
            f"va+size({_fmt_hex(boot_info_va + boot_info_size)})")
    if ram_base > page_table_start:
        raise ProjectionError(
            f"投影自身不一致: ram_base({_fmt_hex(ram_base)}) 高于页表页起点"
            f"({_fmt_hex(page_table_start)})")
    if reserved_end > kernel_start:
        raise ProjectionError("投影自身不一致: 启动保留区越过了内核区起点")
    if page_size <= 0 or page_size & (page_size - 1):
        raise ProjectionError(f"投影页大小不是 2 的幂: {page_size}")
    if reserved_end % page_size:
        raise ProjectionError(
            f"投影自身不一致: 启动保留区终点({_fmt_hex(reserved_end)}) 不是页对齐")
    if initramfs_limit <= 0:
        raise ProjectionError("投影 initramfs 区长度为 0")

    initramfs_format = _rule_text(data, "INITRAMFS-FORMAT")
    if "newc" not in initramfs_format:
        raise ProjectionError("INITRAMFS-FORMAT 规则未点名 cpio newc")

    return Projection(
        kernel_start=kernel_start,
        kernel_end=kernel_end,
        initramfs_va=initramfs_va,
        initramfs_limit=initramfs_limit,
        ram_base=ram_base,
        reserved_end=reserved_end,
        entry=entry,
        page_size=page_size,
        va_pa_offset=va_pa_offset,
        va_width_bits=va_width_bits,
        ei_data=ei_data,
        e_machine=e_machine,
        e_flags_version=e_flags_version,
    )


# ---------------------------------------------------------------------------
# independent product parsers (no llvm-readelf, no cpio library)
# ---------------------------------------------------------------------------

@dataclass
class Segment:
    p_type: int
    p_offset: int
    p_vaddr: int
    p_paddr: int
    p_filesz: int
    p_memsz: int
    p_align: int


@dataclass
class ElfImage:
    ei_class: int
    ei_data: int
    e_type: int
    e_machine: int
    e_entry: int
    e_flags: int
    segments: list[Segment]
    e_phnum: int


def parse_elf(raw: bytes) -> ElfImage:
    """Parse the ELF64 header + program headers (raises ValueError if malformed).

    The byte order is taken from ``EI_DATA`` so that a wrong-endianness image is
    still parsed and judged by K2 instead of failing as "unparseable".
    """
    if len(raw) < 64:
        raise ValueError(f"文件短于 ELF64 头（{len(raw)} B）")
    if raw[:4] != b"\x7fELF":
        raise ValueError("缺 ELF magic")
    ei_class, ei_data = raw[4], raw[5]
    if ei_data == 2:
        endian = ">"
    elif ei_data == 1:
        endian = "<"
    else:
        raise ValueError(f"EI_DATA={ei_data} 不是 1/2")
    (e_type,) = struct.unpack(f"{endian}H", raw[16:18])
    (e_machine,) = struct.unpack(f"{endian}H", raw[18:20])
    (e_entry,) = struct.unpack(f"{endian}Q", raw[24:32])
    (e_phoff,) = struct.unpack(f"{endian}Q", raw[32:40])
    (e_flags,) = struct.unpack(f"{endian}I", raw[48:52])
    (e_phentsize, e_phnum) = struct.unpack(f"{endian}HH", raw[54:58])
    if e_phnum and e_phentsize != 56:
        raise ValueError(f"e_phentsize={e_phentsize}，期望 56")
    if e_phoff + e_phnum * 56 > len(raw):
        raise ValueError("程序头表越出文件")
    segments = []
    for index in range(e_phnum):
        off = e_phoff + index * 56
        p_type, _p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = \
            struct.unpack(f"{endian}IIQQQQQQ", raw[off:off + 56])
        segments.append(Segment(p_type, p_offset, p_vaddr, p_paddr,
                                p_filesz, p_memsz, p_align))
    return ElfImage(ei_class, ei_data, e_type, e_machine, e_entry, e_flags,
                    segments, e_phnum)


@dataclass
class CpioEntry:
    name: str
    mode: int
    uid: int
    gid: int
    nlink: int
    mtime: int
    body: bytes
    raw_start: int
    raw_end: int


def parse_newc(raw: bytes) -> tuple[list[CpioEntry], list[str]]:
    """Parse a ``newc`` archive; returns (entries, problems)."""
    entries: list[CpioEntry] = []
    problems: list[str] = []
    offset = 0
    while True:
        if offset + 110 > len(raw):
            problems.append(f"偏移 {offset} 处头部被截断")
            break
        header = raw[offset:offset + 110]
        if header[:6] != CPIO_MAGIC:
            problems.append(f"偏移 {offset} 处 magic={header[:6]!r}，期望 {CPIO_MAGIC!r}")
            break

        def field(index: int) -> int:
            text = header[6 + 8 * index: 6 + 8 * (index + 1)]
            return int(text, 16)

        mode, uid, gid, nlink, mtime, size = (field(i) for i in (1, 2, 3, 4, 5, 6))
        namesize = field(11)
        name_bytes = raw[offset + 110: offset + 110 + namesize]
        if not name_bytes.endswith(b"\0"):
            problems.append(f"偏移 {offset} 处名字未以 NUL 结尾")
            break
        name = name_bytes[:-1].decode("utf-8", "replace")
        data_start = (offset + 110 + namesize + 3) & ~3
        data_end = data_start + size
        if data_end > len(raw):
            problems.append(f"{name}: 数据越出文件")
            break
        next_offset = (data_end + 3) & ~3
        entries.append(CpioEntry(name, mode, uid, gid, nlink, mtime,
                                 raw[data_start:data_end], offset, next_offset))
        offset = next_offset
        if name == CPIO_TRAILER:
            break
    tail = raw[offset:]
    if len(tail) >= 4:
        problems.append(f"TRAILER 之后有 {len(tail)} B 多余字节")
    return entries, problems


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

class Report:
    """Collects `[PASS]/[FAIL] <id> <name> | 期望=... 实际=...` lines."""

    def __init__(self) -> None:
        self.total = 0
        self.fails: list[str] = []
        self.stats: list[str] = []

    def check(self, cid: str, name: str, expected, actual) -> bool:
        self.total += 1
        ok = expected == actual
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {cid} {name} | 期望={expected} 实际={actual}")
        if not ok:
            self.fails.append(f"{cid} {name}: 期望={expected} 实际={actual}")
        return ok

    def bad(self, cid: str, name: str, expected, actual) -> None:
        self.check(cid, name, expected, actual)

    def stat(self, text: str) -> None:
        self.stats.append(text)
        print(f"  [STAT] {text}")

    def info(self, text: str) -> None:
        print(f"  [INFO] {text}")


# ---------------------------------------------------------------------------
# environment
# ---------------------------------------------------------------------------

@dataclass
class Env:
    """Every path the checks read, so `--inject` can point them at copies."""

    projection: Projection
    vmlinux: Path
    initramfs_dir: Path
    matrix: Path
    source: Path
    base_commit: str
    build: bool = True
    scratch: Path = field(default_factory=lambda: Path("/tmp/opencode/m14-infra-003"))
    state: dict = field(default_factory=dict)


def linux_component() -> tuple[str, list[str]]:
    try:
        with (ROOT / COMPONENTS_LOCK_REL).open("rb") as stream:
            manifest = tomllib.load(stream)
        component = next(c for c in manifest["component"] if c["name"] == "linux")
        base = str(component["commit"])
        patches_dir = ROOT / str(component["patch_dir"])
        series = ROOT / str(component["patch_series"])
    except (OSError, KeyError, StopIteration, tomllib.TOMLDecodeError) as exc:
        raise ProjectionError(f"组件锁里读不到 linux 的 base/series: {exc}") from exc
    entries = [
        line.strip()
        for line in series.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    missing = [name for name in entries if not (patches_dir / name).is_file()]
    if missing:
        raise ProjectionError(f"series 列出的补丁缺失: {missing}")
    return base, entries


def build_env(*, build: bool, scratch: Path, overrides: dict | None = None) -> Env:
    contract = ROOT / CONTRACT_REL
    projection = derive_projection(contract)
    base, entries = linux_component()
    env = Env(
        projection=projection,
        vmlinux=linux_paths.linux_build_dir() / "vmlinux",
        initramfs_dir=linux_paths.linux_initramfs_dir(),
        matrix=ROOT / MATRIX_REL,
        source=linux_paths.linux_source_dir(),
        base_commit=base,
        build=build,
        scratch=scratch,
    )
    env.state["patches"] = entries
    env.state["series_expected_count"] = 1 if entries else 0
    for key, value in (overrides or {}).items():
        setattr(env, key, value)
    return env


# ---------------------------------------------------------------------------
# K1-K6: the kernel image
# ---------------------------------------------------------------------------

def _build_log_tail(text: str, limit: int = 12) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[-limit:])


def phase_vmlinux(env: Env, rep: Report) -> int:
    before = len(rep.fails)
    started = time.monotonic()
    proj = env.projection

    if env.build:
        try:
            cmd, _tools = defconfig.kernel_make_base()
        except defconfig.SetupError as exc:
            rep.bad("K1", "vmlinux 可构建（前置）", "kernel_make_base() 可用", str(exc))
            rep.info("下一步: `make fetch apply-series` / `make install-host` / "
                     "`make linux-defconfig` / `make linux-vmlinux`")
            return len(rep.fails) - before
        if not (linux_paths.linux_build_dir() / ".config").is_file():
            rep.bad("K1", "vmlinux 可构建（.config）", "存在", "缺失")
            rep.info("下一步: `make linux-defconfig && make linux-vmlinux`")
            return len(rep.fails) - before
        # The build tree is shared: state the image this gate builds instead of
        # inheriting whatever the previous command left in .config
        # (m14-linux-006 config slices).
        slice_rc = defconfig.apply_config_lines(K0_CONFIG)
        if slice_rc != 0:
            rep.bad("K1", "配置切片（K1 停止边界开、K2 边界/自检关）", 0, slice_rc)
            rep.info("下一步: `make linux-defconfig`")
            return len(rep.fails) - before
        jobs = defconfig.default_jobs()
        try:
            proc = subprocess.run(
                cmd + [f"-j{jobs}", "vmlinux"],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=TIMEOUT_VMLINUX,
            )
            build_rc, build_out = proc.returncode, proc.stdout or ""
        except subprocess.TimeoutExpired:
            build_rc, build_out = TIMEOUT_RC, f"<timeout {TIMEOUT_VMLINUX}s>"
        except OSError as exc:
            build_rc, build_out = 127, f"<cannot exec make: {exc}>"
        rep.info(f"K1 增量构建 `make -C <linux-src> O=<build> -j{jobs} vmlinux` rc={build_rc}"
                 f" ({time.monotonic() - started:.1f} s)")
        if build_rc != 0:
            rep.bad("K1", "vmlinux 增量构建", 0, build_rc)
            print(_build_log_tail(build_out).replace("\n", "\n         "))
            rep.info("下一步: `make linux-defconfig` / `make linux-vmlinux` "
                     "（`make fetch apply-series` + `make install-host` 须已完成）")

    if not env.vmlinux.is_file():
        rep.bad("K1", f"vmlinux 存在（{_rel(env.vmlinux)}）", True, False)
        rep.info("下一步: `make linux-vmlinux`")
        return len(rep.fails) - before

    raw = env.vmlinux.read_bytes()
    rep.check("K1", f"vmlinux 存在且非空（{_rel(env.vmlinux)}）", True, len(raw) > 0)
    try:
        image = parse_elf(raw)
    except ValueError as exc:
        rep.bad("K1", "vmlinux 可解析（ELF64 头 + 程序头）", "可解析", f"{exc}")
        return len(rep.fails) - before
    env.state["vmlinux_size"] = len(raw)
    env.state["vmlinux_segments"] = image.segments

    # ── K2: header ────────────────────────────────────────────────────────
    rep.check("K2", "ELFCLASS64", ELFCLASS64, image.ei_class)
    rep.check("K2", "EI_DATA（大端）", proj.ei_data, image.ei_data)
    rep.check("K2", "e_type == ET_EXEC", ET_EXEC, image.e_type)
    rep.check("K2", "e_machine", _fmt_hex(proj.e_machine, 4), _fmt_hex(image.e_machine, 4))
    rep.check("K2", "e_flags 版本字段", proj.e_flags_version, image.e_flags & 0xF)

    # ── K3: entry ─────────────────────────────────────────────────────────
    rep.check("K3", "e_entry == kernel_base", _fmt_hex(proj.entry, 11),
              _fmt_hex(image.e_entry, 11))

    # ── K4: program headers / PT_LOAD layout ──────────────────────────────
    types = {seg.p_type for seg in image.segments}
    unexpected = sorted(t for t in types
                        if t != PT_LOAD and t not in NON_LOADING_TYPES)
    rep.check("K4", "程序头类型 ⊆ {LOAD, NOTE, GNU_STACK}", [],
              [_fmt_hex(t, 6) for t in unexpected])
    loads = [seg for seg in image.segments if seg.p_type == PT_LOAD]
    rep.check("K4", "PT_LOAD 段数 >= 1", True, len(loads) >= 1)
    upper_bound = min(proj.kernel_end, proj.initramfs_va)
    for index, seg in enumerate(loads):
        tag = f"K4 PT_LOAD[{index}]"
        rep.check(tag, "p_vaddr == p_paddr + va_pa_offset", proj.va_pa_offset,
                  seg.p_vaddr - seg.p_paddr)
        rep.check(tag, f"p_vaddr % 页大小({_fmt_hex(proj.page_size)})", 0,
                  seg.p_vaddr % proj.page_size)
        rep.check(tag, f"p_align >= 页大小({_fmt_hex(proj.page_size)})", True,
                  seg.p_align >= proj.page_size)
        rep.check(tag, "p_filesz <= p_memsz", True, seg.p_filesz <= seg.p_memsz)
        rep.check(tag, f">= kernel_base({_fmt_hex(proj.kernel_start, 11)})", True,
                  seg.p_vaddr >= proj.kernel_start)
        rep.check(tag, f"[vaddr, vaddr+memsz) ⊆ 内核镜像区终点({_fmt_hex(upper_bound, 11)})",
                  True, seg.p_vaddr + seg.p_memsz <= upper_bound)

        # ── K5: reserved area + the 42-bit memory window ──────────────────
        seg_end = seg.p_vaddr + seg.p_memsz
        disjoint = seg_end <= proj.ram_base or seg.p_vaddr >= proj.reserved_end
        rep.check(f"K5 PT_LOAD[{index}]",
                  f"不与启动保留区 [{_fmt_hex(proj.ram_base, 11)}, "
                  f"{_fmt_hex(proj.reserved_end, 11)}) 重叠", True, disjoint)
        rep.check(f"K5 PT_LOAD[{index}]",
                  f"落在 {proj.va_width_bits} 位内存窗口内（≠ cfxha 63 BootROM / "
                  f"cfxha 3 hmon SRAM）", True, seg_end <= (1 << proj.va_width_bits))

    # ── K6: no undefined symbols ──────────────────────────────────────────
    nm = linux_paths.toolchain_bin() / "llvm-nm"
    if not (nm.is_file() and os.access(nm, os.X_OK)):
        rep.bad("K6", f"llvm-nm 可执行（{_rel(nm)}）", True, False)
        rep.info("下一步: `make install-host`")
    else:
        try:
            proc = subprocess.run([str(nm), "-u", str(env.vmlinux)],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=300)
            undefined = [line for line in (proc.stdout or "").splitlines() if line.strip()]
        except subprocess.TimeoutExpired:
            undefined = [f"<llvm-nm -u timeout 300s ⇒ 判 FAIL>"]
        except OSError as exc:
            undefined = [f"<cannot exec llvm-nm: {exc}>"]
        rep.check("K6", "`llvm-nm -u vmlinux` 输出为空", [], undefined)

    # ── K13: the live counts must agree with the artefact they came from ──
    payload = sum(seg.p_filesz for seg in loads)
    rep.check("K13", f"PT_LOAD 载荷合计({payload} B) <= vmlinux 文件大小({len(raw)} B)",
              True, payload <= len(raw))
    # File ranges must be disjoint (a linked image does not share file bytes
    # between two PT_LOAD segments); a corrupted/overwritten p_offset trips this
    # without touching any VA rule above.
    ranges = sorted((seg.p_offset, seg.p_offset + seg.p_filesz) for seg in loads)
    overlapped = [(ranges[i], ranges[i + 1]) for i in range(len(ranges) - 1)
                  if ranges[i][1] > ranges[i + 1][0] and ranges[i][1] > ranges[i][0]]
    rep.check("K13", f"PT_LOAD 文件区间互不重叠（{len(ranges)} 段，现场统计）",
              [], [(f"0x{a[0]:x}..0x{a[1]:x}", f"0x{b[0]:x}..0x{b[1]:x}")
                  for a, b in overlapped])

    rep.stat(f"vmlinux: {env.state['vmlinux_size']} B, "
             f"程序头 {image.e_phnum} 个，PT_LOAD {len(loads)} 个，"
             f"解析耗时 {time.monotonic() - started:.1f} s")
    return len(rep.fails) - before


# ---------------------------------------------------------------------------
# K7-K9: the initramfs
# ---------------------------------------------------------------------------

def _two_generations(scratch: Path) -> tuple[bytes, bytes]:
    """Build the init ELF + cpio twice in scratch dirs (generator code)."""
    payloads = []
    for run in ("a", "b"):
        outdir = scratch / f"generation-{run}"
        _obj, elf = make_initramfs.build_init(outdir)
        payloads.append(make_initramfs.build_cpio(elf.read_bytes()))
    return payloads[0], payloads[1]


def phase_initramfs(env: Env, rep: Report) -> int:
    before = len(rep.fails)
    started = time.monotonic()
    proj = env.projection
    init_path = env.initramfs_dir / "init"
    cpio_path = env.initramfs_dir / "initramfs.cpio"
    manifest_path = env.initramfs_dir / "manifest.json"

    if env.build:
        rc, out = run_script(INITRAMFS_SCRIPT_REL, [], timeout=TIMEOUT_INITRAMFS)
        rep.info(f"K7 增量构建 `make linux-initramfs` rc={rc} "
                 f"({time.monotonic() - started:.1f} s)")
        if rc != 0:
            rep.bad("K7", "initramfs 增量构建", 0, rc)
            print(_build_log_tail(out).replace("\n", "\n         "))
            rep.info("下一步: `make build-musl` + `make install-host`，然后 "
                     "`make linux-initramfs`")

    missing = [p.name for p in (init_path, cpio_path, manifest_path) if not p.is_file()]
    rep.check("K7", f"initramfs 产物齐全（{_rel(env.initramfs_dir)}）", [], missing)
    if missing:
        rep.info("下一步: `make linux-initramfs`")
        return len(rep.fails) - before

    raw = cpio_path.read_bytes()
    entries, problems = parse_newc(raw)
    rep.check("K7", "cpio newc 可解析（无结构问题）", [], problems)
    names = [entry.name for entry in entries]
    rep.check("K7", "首条目为 '.'", ".", names[0] if names else "<空>")
    rep.check("K7", "含 'init'", True, "init" in names)
    rep.check("K7", "末条目为 TRAILER!!!", CPIO_TRAILER,
              names[-1] if names else "<空>")

    by_name = {entry.name: entry for entry in entries}
    init_bytes = init_path.read_bytes()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        rep.bad("K7", "manifest.json 可解析", "JSON 对象", str(exc))
        manifest = {}
    if not isinstance(manifest, dict):
        rep.bad("K7", "manifest.json 是对象", True, False)
        manifest = {}
    if "init" in by_name:
        entry = by_name["init"]
        rep.check("K7", "init mode == 0100755", 0o100755, entry.mode)
        rep.check("K7", "init payload sha256 == 构建的 init ELF sha256",
                  hashlib.sha256(init_bytes).hexdigest(),
                  hashlib.sha256(entry.body).hexdigest())
    rep.check("K7", "manifest init sha256 == init ELF sha256",
              hashlib.sha256(init_bytes).hexdigest(),
              (manifest.get("init") or {}).get("sha256"))
    rep.check("K7", "manifest cpio sha256 == 归档 sha256",
              hashlib.sha256(raw).hexdigest(), (manifest.get("cpio") or {}).get("sha256"))
    rep.check("K7", "manifest cpio size == 归档大小", len(raw),
              (manifest.get("cpio") or {}).get("size"))

    # ── K8: two independent generations in a scratch directory ────────────
    gen_dir = env.scratch / "k0-generations"
    if gen_dir.exists():
        shutil.rmtree(gen_dir)
    gen_dir.mkdir(parents=True, exist_ok=True)
    try:
        first, second = _two_generations(gen_dir)
    except (make_initramfs.SetupError, make_initramfs.CheckError) as exc:
        rep.bad("K8", "生成器可运行两次（scratch）", "rc=0", f"{type(exc).__name__}: {exc}")
        rep.info("下一步: `make build-musl` + `make install-host`，然后 "
                 "`make linux-initramfs`")
        first = second = b""
    if first or second:
        rep.check("K8", "二次生成 sha256 相同", hashlib.sha256(first).hexdigest(),
                  hashlib.sha256(second).hexdigest())
        rep.check("K8", "二次生成 == 交付的 initramfs.cpio", hashlib.sha256(raw).hexdigest(),
                  hashlib.sha256(first).hexdigest())

    # ── K9: size limit + static init ELF ─────────────────────────────────
    rep.check("K9", f"initramfs 大小 <= initramfs 区（{proj.initramfs_limit} B）",
              True, len(raw) <= proj.initramfs_limit)
    try:
        init_image = parse_elf(init_bytes)
    except ValueError as exc:
        rep.bad("K9", "init 可解析（ELF64 头 + 程序头）", "可解析", f"{exc}")
        init_image = None
    if init_image is not None:
        types = [seg.p_type for seg in init_image.segments]
        rep.check("K9", "init 无 PT_INTERP", False, PT_INTERP in types)
        rep.check("K9", "init 无 PT_DYNAMIC（静态链接）", False, PT_DYNAMIC in types)

    cpio_payload = sum(len(entry.body) for entry in entries)
    rep.check("K13", f"cpio 载荷合计({cpio_payload} B) <= 归档大小({len(raw)} B)",
              True, cpio_payload <= len(raw))
    rep.check("K13", "cpio 条目数 >= 2（'.' + TRAILER!!!）", True, len(entries) >= 2)

    env.state["initramfs_size"] = len(raw)
    env.state["init_size"] = len(init_bytes)
    env.state["cpio_entries"] = len(entries)
    rep.stat(f"initramfs: {len(raw)} B / 区上限 {proj.initramfs_limit} B，"
             f"cpio 条目 {len(entries)} 个，init ELF {len(init_bytes)} B，"
             f"耗时 {time.monotonic() - started:.1f} s（含二次生成）")
    return len(rep.fails) - before


# ---------------------------------------------------------------------------
# K10 / K11: the sibling gates (called, never re-implemented)
# ---------------------------------------------------------------------------

def phase_toolchain(env: Env, rep: Report) -> int:
    before = len(rep.fails)
    started = time.monotonic()
    child_env = dict(os.environ)
    child_env["DADAO_TMP"] = str(env.scratch / "toolchain-probes")
    rc, out = run_script(TOOLCHAIN_SCRIPT_REL, [], timeout=TIMEOUT_TOOLCHAIN,
                         env=child_env)
    rep.check("K10", "`check_toolchain.py` 逻辑 rc == 0（矩阵声明 == 实测）", 0, rc)
    if rc != 0:
        print(_build_log_tail(out).replace("\n", "\n         "))
        if rc == TIMEOUT_RC:
            rep.info(f"K10 超时（{TIMEOUT_TOOLCHAIN}s）⇒ 判 FAIL")
    rep.stat(f"toolchain matrix: rc={rc}，耗时 {time.monotonic() - started:.1f} s")
    return len(rep.fails) - before


def phase_boot_contract(env: Env, rep: Report) -> int:
    before = len(rep.fails)
    started = time.monotonic()
    rc, out = run_script(BOOT_CONTRACT_SCRIPT_REL, [], timeout=TIMEOUT_BOOT_CONTRACT)
    rep.check("K11", "`check_boot_contract.py` 逻辑 rc == 0（正文 ↔ 契约 ↔ 投影）", 0, rc)
    if rc != 0:
        print(_build_log_tail(out).replace("\n", "\n         "))
        if rc == TIMEOUT_RC:
            rep.info(f"K11 超时（{TIMEOUT_BOOT_CONTRACT}s）⇒ 判 FAIL")
    rep.stat(f"boot contract: rc={rc}，耗时 {time.monotonic() - started:.1f} s")
    return len(rep.fails) - before


# ---------------------------------------------------------------------------
# K12: apply-series idempotence (linux only)
# ---------------------------------------------------------------------------

def source_head_state(source: Path, base: str) -> dict:
    """HEAD / cleanliness / commit count of ``base..HEAD`` for a source tree."""
    state = {"head": "", "clean": False, "count": -1}
    rc, out = git_out(source, "rev-parse", "HEAD")
    if rc != 0:
        state["error"] = out.strip()
        return state
    state["head"] = out.strip()
    rc, out = git_out(source, "status", "--porcelain")
    state["clean"] = rc == 0 and out.strip() == ""
    rc, out = git_out(source, "rev-list", "--count", f"{base}..HEAD")
    if rc == 0:
        state["count"] = int(out.strip() or "0")
    return state


def check_head(rep: Report, cid: str, state: dict, expected_count: int) -> None:
    rep.check(cid, "rev-list --count <base>..HEAD", expected_count, state["count"])
    rep.check(cid, "工作树干净（git status --porcelain 为空）", True, state["clean"])


def components_touched(output: str) -> set[str]:
    """Component names an ``apply-series`` run actually processed.

    ``apply-series`` prints one line per component (and per submodule set); with
    ``--component linux`` the set must be exactly ``{"linux"}`` -- if the filter
    regressed, the other components show up here and K12 fails.
    """
    names: set[str] = set()
    for line in output.splitlines():
        match = re.match(r"apply-series: component=([^:]+):", line)
        if match:
            names.add(match.group(1).strip())
            continue
        match = re.match(
            r"apply-series: ([^:\s]+):? (?:already applied|\d+ applied|has an empty series"
            r"|patchless, skip)", line)
        if match:
            names.add(match.group(1).split("/")[0])
    return names


def phase_series(env: Env, rep: Report) -> int:
    before = len(rep.fails)
    started = time.monotonic()
    expected = int(env.state.get("series_expected_count", 0))
    patches = env.state.get("patches") or []

    rep.check("K12", "linux 源树存在", True, env.source.is_dir())
    if not env.source.is_dir():
        rep.info("下一步: `make fetch`")
        return len(rep.fails) - before

    pre = source_head_state(env.source, env.base_commit)
    rc1, out1 = run_script(APPLY_SERIES_SCRIPT_REL, ["--component", "linux"],
                           timeout=TIMEOUT_SERIES)
    rep.check("K12", "apply-series --component linux（第 1 次）", 0, rc1)
    post_first = source_head_state(env.source, env.base_commit)
    rc2, out2 = run_script(APPLY_SERIES_SCRIPT_REL, ["--component", "linux"],
                           timeout=TIMEOUT_SERIES)
    rep.check("K12", "apply-series --component linux（第 2 次）", 0, rc2)
    post = source_head_state(env.source, env.base_commit)

    for tag, rc, out in (("1", rc1, out1), ("2", rc2, out2)):
        if rc != 0:
            print(_build_log_tail(out).replace("\n", "\n         "))
            if rc == TIMEOUT_RC:
                rep.info(f"K12 第 {tag} 次超时（{TIMEOUT_SERIES}s）⇒ 判 FAIL")
    touched = components_touched(out1) | components_touched(out2)
    rep.check("K12", "两次运行只处理 linux（apply-series 输出点名的组件）",
              ["linux"], sorted(touched) if touched else ["<无输出>"])
    rep.check("K12", "第 1 次运行后 HEAD 未变（幂等）", pre["head"], post_first["head"])
    rep.check("K12", "第 2 次运行后 HEAD 未变（幂等）", post_first["head"], post["head"])
    check_head(rep, "K12", post, expected)
    rep.stat(f"apply-series: 补丁 {len(patches)} 个，期望 base+{expected}，"
             f"耗时 {time.monotonic() - started:.1f} s")
    return len(rep.fails) - before


PHASES = (
    ("K1-K6", "vmlinux", phase_vmlinux),
    ("K7-K9", "initramfs", phase_initramfs),
    ("K10", "toolchain matrix", phase_toolchain),
    ("K11", "boot contract", phase_boot_contract),
    ("K12", "apply-series", phase_series),
)


# ---------------------------------------------------------------------------
# --inject: tampered copies in a scratch directory
# ---------------------------------------------------------------------------

def _silent(rc_callable) -> tuple[int, str, str]:
    """Run a checker with its stdout captured: (rc, first FAIL line, full text)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = rc_callable()
    text = buf.getvalue()
    first = next((line.strip() for line in text.splitlines() if "[FAIL]" in line), "")
    return rc, first, text


def _phase_rc(phase, env: Env) -> int:
    rep = Report()
    before = len(rep.fails)
    phase(env, rep)
    return len(rep.fails) - before


def inject(env: Env, scratch: Path) -> int:
    """Tamper with copies; every case must FAIL; real artefacts stay untouched."""
    if not env.vmlinux.is_file() or not (env.initramfs_dir / "initramfs.cpio").is_file():
        print("[INJECT] 产物缺失：先跑一次 `make check-linux-k0` 再自检")
        return 1

    ok = True
    cases: list[tuple[str, str, callable]] = []

    real_md5 = {
        "vmlinux": md5_file(env.vmlinux),
        "cpio": md5_file(env.initramfs_dir / "initramfs.cpio"),
        "matrix": md5_file(env.matrix),
        "contract": md5_file(ROOT / CONTRACT_REL),
        "source_head": source_head_state(env.source, env.base_commit)["head"],
    }

    # ── I1: vmlinux copy with a rewritten e_entry ────────────────────────
    def case_entry() -> tuple[int, str, str]:
        copy = scratch / "tampered-vmlinux"
        shutil.copy2(env.vmlinux, copy)
        raw = bytearray(copy.read_bytes())
        raw[24:32] = (env.projection.entry + 0x10000).to_bytes(8, "big")
        copy.write_bytes(bytes(raw))
        if md5_file(copy) == real_md5["vmlinux"]:
            return 0, "<注入是空操作：副本与真实 vmlinux 相同>", ""
        tampered = build_env(build=False, scratch=scratch,
                             overrides={"vmlinux": copy})
        return _silent(lambda: _phase_rc(phase_vmlinux, tampered))

    cases.append(("I1 vmlinux 副本 e_entry 改值", "K3", case_entry))

    # ── I2: initramfs copy with the `init` entry removed ─────────────────
    def case_no_init() -> tuple[int, str, str]:
        target = scratch / "tampered-initramfs"
        target.mkdir(parents=True, exist_ok=True)
        for name in ("init", "manifest.json", "initramfs.cpio"):
            shutil.copy2(env.initramfs_dir / name, target / name)
        entries, problems = parse_newc((target / "initramfs.cpio").read_bytes())
        if problems:
            return 0, f"<基线归档不可解析: {problems[0]}>", ""
        raw = (target / "initramfs.cpio").read_bytes()
        pieces = [raw[e.raw_start:e.raw_end] for e in entries if e.name != "init"]
        (target / "initramfs.cpio").write_bytes(b"".join(pieces))
        if md5_file(target / "initramfs.cpio") == real_md5["cpio"]:
            return 0, "<注入是空操作：副本归档与真实归档相同>", ""
        tampered = build_env(build=False, scratch=scratch,
                             overrides={"initramfs_dir": target})
        return _silent(lambda: _phase_rc(phase_initramfs, tampered))

    cases.append(("I2 initramfs 副本删掉 init 条目", "K7", case_no_init))

    # ── I3: matrix copy with one row declared `absent` ───────────────────
    def case_matrix_row() -> tuple[int, str, str]:
        from tools.linux import check_toolchain as tc
        data = json.loads(env.matrix.read_text(encoding="utf-8"))
        row = data["rows"][0]
        original = row["declared"]
        row["declared"] = "absent" if original != "absent" else "present"
        copy = scratch / "tampered-matrix.json"
        copy.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        if md5_file(copy) == real_md5["matrix"]:
            return 0, "<注入是空操作：副本矩阵与真实矩阵相同>", ""
        live = tc.measure()
        problems, _summary = tc.validate(tc.load_matrix(copy), live)
        detail = problems[0] if problems else "无"
        text = "\n".join(f"[FAIL] {problem}" for problem in problems)
        return (1 if problems else 0), (f"[FAIL] {detail}" if problems else detail), text

    cases.append(("I3 矩阵副本改一行 declared=absent（判据 R1 声明!=实测）", "R1",
                  case_matrix_row))

    # ── I4: synthetic source tree with an extra commit / a dirty worktree ─
    def _synthetic_source(extra_commits: int, dirty: bool) -> tuple[Path, str]:
        repo = scratch / f"synthetic-linux-{extra_commits}-{int(dirty)}"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True)
        env_git = dict(os.environ)
        env_git.update({
            "GIT_AUTHOR_NAME": "k0", "GIT_AUTHOR_EMAIL": "k0@example.invalid",
            "GIT_COMMITTER_NAME": "k0", "GIT_COMMITTER_EMAIL": "k0@example.invalid",
        })
        for args in (("init", "-q", "-b", "main"),):
            subprocess.run(["git", "-C", str(repo), *args], check=True, env=env_git)
        (repo / "f.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "f.txt"], check=True, env=env_git)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"],
                       check=True, env=env_git)
        base = git_out(repo, "rev-parse", "HEAD")[1].strip()
        for index in range(extra_commits):
            (repo / "f.txt").write_text(f"base\npatch{index}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "f.txt"], check=True, env=env_git)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", f"patch{index}"],
                           check=True, env=env_git)
        if dirty:
            (repo / "g.txt").write_text("untracked\n", encoding="utf-8")
        return repo, base

    def _head_case(extra_commits: int, dirty: bool) -> tuple[int, str]:
        repo, base = _synthetic_source(extra_commits, dirty)
        state = source_head_state(repo, base)
        rep = Report()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            check_head(rep, "K12", state, 1)
        detail = next((l.strip() for l in buf.getvalue().splitlines() if "[FAIL]" in l), "")
        return (1 if rep.fails else 0), detail, buf.getvalue()

    def case_extra_commit() -> tuple[int, str, str]:
        return _head_case(2, False)

    cases.append(("I4 源树多一个 commit（应为 base+1）", "K12", case_extra_commit))

    def case_dirty() -> tuple[int, str, str]:
        return _head_case(1, True)

    cases.append(("I4b 源树临时弄脏", "K12", case_dirty))

    # ── I5: projection copy with a shrunk kernel image area ──────────────
    def case_projection() -> tuple[int, str, str]:
        text = (ROOT / CONTRACT_REL).read_text(encoding="utf-8")
        original = env.projection.kernel_end
        shrunk = env.projection.kernel_start + env.projection.page_size
        needle = f"end: {_fmt_hex(original)}"
        if text.count(needle) != 1:
            return 0, f"<注入点不唯一：{needle!r} 命中 {text.count(needle)} 处>", ""
        copy = scratch / "tampered-linux-boot.yaml"
        copy.write_text(text.replace(needle, f"end: {_fmt_hex(shrunk)}"), encoding="utf-8")
        if md5_file(copy) == real_md5["contract"]:
            return 0, "<注入是空操作：副本投影与真实投影相同>", ""
        tampered = build_env(build=False, scratch=scratch,
                             overrides={"projection": derive_projection(copy)})
        return _silent(lambda: _phase_rc(phase_vmlinux, tampered))

    cases.append(("I5 投影副本把内核区终点缩小", "K4", case_projection))

    # ── I5b: projection copy with a narrower memory window (K5 only) ──────
    def case_window() -> tuple[int, str, str]:
        text = (ROOT / CONTRACT_REL).read_text(encoding="utf-8")
        original = env.projection.va_width_bits
        needle = f"va_width_bits: {original}"
        if text.count(needle) != 1:
            return 0, f"<注入点不唯一：{needle!r} 命中 {text.count(needle)} 处>", ""
        copy = scratch / "tampered-window.yaml"
        copy.write_text(text.replace(needle, f"va_width_bits: {original - 12}"),
                        encoding="utf-8")
        if md5_file(copy) == real_md5["contract"]:
            return 0, "<注入是空操作：副本投影与真实投影相同>", ""
        tampered = build_env(build=False, scratch=scratch,
                             overrides={"projection": derive_projection(copy)})
        return _silent(lambda: _phase_rc(phase_vmlinux, tampered))

    cases.append(("I5b 投影副本把 42 位内存窗口收窄", "K5", case_window))

    # ── I6: two archives differing only in one mtime must trip K8 ────────
    def case_determinism() -> tuple[int, str, str]:
        raw = (env.initramfs_dir / "initramfs.cpio").read_bytes()
        entries, problems = parse_newc(raw)
        if problems or not entries:
            return 0, f"<基线归档不可解析: {problems[0] if problems else '空归档'}>", ""
        # mtime is field 5 of the newc header (offset 6 + 8*5 = 46, 8 hex chars).
        start = entries[0].raw_start + 46
        old = raw[start:start + 8]
        try:
            bumped = b"%08X" % ((int(old, 16) + 1) & 0xFFFFFFFF)
        except ValueError:
            return 0, f"<mtime 字段不是十六进制: {old!r}>", ""
        mutated = raw[:start] + bumped + raw[start + 8:]
        if mutated == raw:
            return 0, "<注入是空操作：归档未改变>", ""
        rep = Report()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rep.check("K8", "二次生成 sha256 相同",
                      hashlib.sha256(raw).hexdigest(),
                      hashlib.sha256(mutated).hexdigest())
        detail = next((l.strip() for l in buf.getvalue().splitlines() if "[FAIL]" in l), "")
        return (1 if rep.fails else 0), detail, buf.getvalue()

    cases.append(("I6 归档仅 mtime 不同（可复现判据）", "K8", case_determinism))

    # ── I7: the `--component` filter must be enforced and the judgement live ─
    def case_filter() -> tuple[int, str, str]:
        rc, out = run_script(APPLY_SERIES_SCRIPT_REL, ["--component", "no-such-component"],
                             timeout=TIMEOUT_SERIES)
        foreign = {"linux", "llvm-project", "qemu"}
        detected = components_touched(
            "\n".join(f"apply-series: {name}: patchless, skip" for name in foreign))
        guard_fired = rc != 0
        judgement_live = detected == foreign
        detail = (f"[FAIL] 未知组件名 apply_series rc={rc}（guard 触发={guard_fired}）"
                  f"·判据对非 linux 输出点名={sorted(detected)}（live={judgement_live}）"
                  f" {_build_log_tail(out, 1)}")
        # `rc` here is apply_series' own exit code (the guard firing is the
        # expected outcome); 0 means the filter silently ignored the request.
        # No gate-ID target: this case proves the *filter guard*, not a phase.
        return (1 if (guard_fired and judgement_live) else 0), detail, ""

    cases.append(("I7 --component 过滤（未知名须拒绝）", "", case_filter))

    # ── I8: truncated vmlinux copy (the K13 count/artefact relation) ──────
    def case_truncated() -> tuple[int, str, str]:
        copy = scratch / "truncated-vmlinux"
        raw = env.vmlinux.read_bytes()
        keep = int(len(raw) * 0.6)
        copy.write_bytes(raw[:keep])
        if md5_file(copy) == real_md5["vmlinux"]:
            return 0, "<注入是空操作：副本与真实 vmlinux 相同>", ""
        tampered = build_env(build=False, scratch=scratch,
                             overrides={"vmlinux": copy})
        return _silent(lambda: _phase_rc(phase_vmlinux, tampered))

    cases.append(("I8 vmlinux 副本截断（计数与产物不符）", "K13", case_truncated))

    for name, expect_id, case in cases:
        rc, detail, text = case()
        if rc == 0:
            ok = False
        # The labelled judgement must be *the* one that failed: a case whose
        # target ID never shows up in a [FAIL] line proves nothing about that
        # judgement (an incidental failure elsewhere is not evidence).
        target_hit = True
        if expect_id:
            target_hit = f"[FAIL] {expect_id}" in text
            if not target_hit:
                ok = False
        verdict = "PASS" if (rc != 0 and target_hit) else "FAIL"
        print(f"[INJECT] {name}: 目标={expect_id or '<filter guard>'} 期望=FAIL "
              f"实际rc={rc} 目标命中={'yes' if target_hit else 'no'} => {verdict}"
              f"  （首个判据: {detail or '无'}）")

    # The real artefacts and the real source tree must be untouched.
    checks = (
        ("真实 vmlinux md5 未变", md5_file(env.vmlinux) == real_md5["vmlinux"]),
        ("真实 initramfs.cpio md5 未变",
         md5_file(env.initramfs_dir / "initramfs.cpio") == real_md5["cpio"]),
        ("真实矩阵 md5 未变", md5_file(env.matrix) == real_md5["matrix"]),
        ("真实投影 md5 未变", md5_file(ROOT / CONTRACT_REL) == real_md5["contract"]),
        ("真实 linux 源树 HEAD 未变",
         source_head_state(env.source, env.base_commit)["head"] == real_md5["source_head"]),
    )
    for label, passed in checks:
        print(f"[INJECT] {label}: {'PASS' if passed else 'FAIL'}")
        ok = ok and passed

    print("check-linux-k0 --inject: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="M14 K0 closure gate: vmlinux + initramfs + matrix + boot contract + series")
    parser.add_argument("--no-build", dest="build", action="store_false",
                        help="assert only; never invoke the linux / initramfs builds")
    parser.add_argument("--inject", action="store_true",
                        help="self-check on tampered copies (products untouched)")
    args = parser.parse_args(argv)

    # Scratch lives under this task's temp dir (`/tmp/opencode/<task-id>/`,
    # AGENTS.md「临时目录」); the run directory is removed on exit and the
    # parent is removed again when this run created it -- a gate that runs in
    # every L2 must not leave a stale `/tmp/opencode/*` entry behind
    # (`check-temp-dirs`).
    base = Path(os.environ.get("K0_TMP", "/tmp/opencode/m14-infra-003"))
    created_base = not base.exists()
    base.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="run-", dir=base))
    os.environ.setdefault("DADAO_TMP", str(scratch))
    try:
        try:
            env = build_env(build=args.build, scratch=scratch)
        except ProjectionError as exc:
            print(f"check-linux-k0: 无法派生期望值: {exc}", file=sys.stderr)
            return 2

        print(f"check-linux-k0: 投影={CONTRACT_REL.as_posix()} "
              f"矩阵={MATRIX_REL.as_posix()} "
              f"linux base={env.base_commit[:12]} "
              f"补丁={len(env.state['patches'])}")

        if args.inject:
            return inject(env, scratch)

        rep = Report()
        started = time.monotonic()
        timings: list[tuple[str, float]] = []
        for tag, label, phase in PHASES:
            print(f"── {tag}: {label} ──")
            phase_started = time.monotonic()
            phase(env, rep)
            timings.append((f"{tag} {label}", time.monotonic() - phase_started))
        elapsed = time.monotonic() - started

        print()
        for label, seconds in timings:
            print(f"  [TIME] {label}: {seconds:.1f} s")
        print(f"  [TIME] total: {elapsed:.1f} s")

        # K13: live counts, recomputed here (never hardcoded).
        images = env.state.get("vmlinux_segments") or []
        loads = [seg for seg in images if seg.p_type == PT_LOAD]
        print(f"  [COUNT] 补丁 {len(env.state['patches'])} 个；"
              f"PT_LOAD {len(loads)} 个；cpio 条目 {env.state.get('cpio_entries', 0)} 个；"
              f"vmlinux {env.state.get('vmlinux_size', 0)} B；"
              f"initramfs {env.state.get('initramfs_size', 0)} B；"
              f"init {env.state.get('init_size', 0)} B")

        passed = rep.total - len(rep.fails)
        print(f"\n{passed}/{rep.total} 项通过（失败 {len(rep.fails)}，耗时 {elapsed:.1f} s）")
        if rep.fails:
            for failure in rep.fails:
                print(f"  [FAIL] {failure}")
            print("check-linux-k0: FAIL")
            return 1
        print("check-linux-k0: PASS")
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        if created_base:
            with contextlib.suppress(OSError):
                base.rmdir()  # only succeeds when empty; never deletes another run's files


if __name__ == "__main__":
    sys.exit(main())
