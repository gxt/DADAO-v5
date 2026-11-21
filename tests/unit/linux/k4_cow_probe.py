#!/usr/bin/env python3
"""k4_cow_probe.py — M14 K4 copy-on-write probe (`m14-linux-018` W1-W5).

A fork no longer copies the address space: both processes keep pointing at the
same physical pages with both PTEs write-protected, and the first write on
either side is what makes a private copy.  The kernel side is
`arch/dadao/mm/k4_cow_selftest.c` (`CONFIG_DADAO_K4_COW_SELFTEST`): case 1 runs
W1/W2/W4/W5 in one boot (the child task is created by `kernel_clone()` and runs
its write through the real `switch_mm()`), case 3 runs W3, whose verdict is a
named termination.

Cases (each assertion of the task book's five judgements has one):

  W1  the child's write moves its PTE to a different PA whose contents are the
      *old ones* (the parent's sentinel survives at offset 0 and the child's own
      word is at offset 8) — a freshly allocated page would read as zero, so
      "copied" and "zeroed" are told apart;
  W2  the parent's PTE still points at the original page, its contents are
      unchanged and the child's write is not visible in it;
  W3  a write to a read-only page of a `VM_SHARED` mapping is *not* COW: the
      channel terminates by name (CFXPERM + NWPERM, `die-perm`) and allocates
      no page;
  W4  references: 1 before the fork, 2 after it, 1 once the child copied,
      0 once the parent unmapped the mapping (the last reference frees it);
  W5  the parent's own write faults again (its PTE was still read-only) and is
      resolved in place (same PA, no second copy, no second put), and the
      invalidation the COW issued carries `ASID_ANY = 0` with the writing mm's
      ASID and the encoding contract-tlb TLB-19 gives for `invalid | VA`.

Everything is derived, never restated: the page size from the image's own
`.config`, the NWPERM bit and its class from `contract-see §6.1.1` (checked
against `asm/cause-sub.h`), the TLB command encoding from `asm/ptw.h`'s own
operand definitions, the terminal exit code from `spec/Kaiwu §7.1`, and the
probe's sentinel values from its source.

`--inject` corrupts one rule, rebuilds, asserts the owning case goes red,
restores with `cp` + md5 and proves the case is green again.  Five injections,
one per judgement path (copy, PTE install, invalidation, ASID scope, sole
reference).

The image slice is built from the module-level ``CONFIG_PINS`` through
``config_pins.config_lines()`` (`make check-config-pins`, ISS-470): every
``CONFIG_DADAO_*`` symbol of the Kconfig is named, so no image can inherit
another gate's case from the shared build tree.

Exit status: 0 = every check passed; 1 = a FAIL; 2 = an input could not be
derived (config / contract / kernel source / build tree missing).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.unit.linux import k3_page_probe as k3page               # noqa: E402
from tools.linux import config_pins                          # noqa: E402  (pins)
from tools.linux import make_defconfig as defconfig          # noqa: E402
from tools.linux import paths as linux_paths                 # noqa: E402
from tools.qemu import k0_boot_probe as k0                   # noqa: E402

SCRATCH = (Path(os.environ.get("K4COW_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-018") / "check-linux-k4-cow")
SOURCE = linux_paths.linux_source_dir()

SELFTEST_C = "arch/dadao/mm/k4_cow_selftest.c"
COW_C = "arch/dadao/mm/cow.c"
FAULT_C = "arch/dadao/mm/fault.c"
PTW_H = "arch/dadao/include/asm/ptw.h"
CAUSE_SUB_H = "arch/dadao/include/asm/cause-sub.h"

#: Every ``CONFIG_DADAO_*`` symbol of the Kconfig (`make check-config-pins`,
#: ISS-470): the COW image has no stop inside setup_arch() and no other
#: milestone's self-test compiled in.  The slice is derived from this dict by
#: `config_pins.config_lines()` -- never hand-written.
CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_TIME_STOP": "n",
    # int symbols with an unmet `depends on` are "left unset" (Kconfig has no
    # `n` for an int: the symbol is dropped from .config).
    "CONFIG_DADAO_K2_TIME_CASE": "n",
    "CONFIG_DADAO_K2_IRQ_TEST": "n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST": "n",
    "CONFIG_DADAO_K2_SELFTEST_REENTRY": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXTRAP": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXESC": "n",
    "CONFIG_DADAO_K2_SELFTEST_UNKNOWN": "n",
    "CONFIG_DADAO_K3_PF_SELFTEST": "0",
    "CONFIG_DADAO_K3_PT_SELFTEST": "n",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    # m14-linux-020: the kernel-thread probe is an image of its own; pin it
    # off so the shared build tree cannot hand this image that symbol.
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    # m14-linux-023: the user-syscall probe image; pin it off so no other
    # image inherits it from the shared build tree.
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
}

#: The COW case each image carries (one image per case: a case whose verdict is
#: a named termination ends the boot).
IMAGE_PINS = {
    "1": {"CONFIG_DADAO_K4_COW_SELFTEST": "1"},
    "3": {"CONFIG_DADAO_K4_COW_SELFTEST": "3"},
}

CASES = (1, 3)

TIMEOUT_BUILD = int(os.environ.get("K4COW_BUILD_TIMEOUT", "2400"))
TIMEOUT_QEMU = int(os.environ.get("K4COW_QEMU_TIMEOUT", "180"))
JOBS = os.environ.get("JOBS", "32")


class Report:
    def __init__(self) -> None:
        self.total = 0
        self.failed: list[str] = []

    def check(self, group: str, name: str, expected, actual) -> bool:
        self.total += 1
        ok = expected == actual
        print(f"[{'PASS' if ok else 'FAIL'}] {group}: {name}: "
              f"want={expected!r} got={actual!r}")
        if not ok:
            self.failed.append(f"{group}: {name}")
        return ok

    def info(self, text: str) -> None:
        print(f"[INFO] {text}")


# ---------------------------------------------------------------------------
# derivations
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def kernel_text(rel: str) -> str:
    path = SOURCE / rel
    if not path.is_file():
        raise SystemExit(f"k4_cow_probe: kernel source missing: {rel}")
    return path.read_text(encoding="utf-8")


def build_dir() -> Path:
    return Path(linux_paths.linux_build_dir())


def config_value(symbol: str) -> str | None:
    path = build_dir() / ".config"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(symbol + "="):
            return line.split("=", 1)[1].strip()
    return None


def page_size() -> int:
    """The page size the image runs with (its own `.config`, spec §2.2.2)."""
    shift = config_value("CONFIG_PAGE_SHIFT")
    if shift is None:
        raise SystemExit("k4_cow_probe: the image has no CONFIG_PAGE_SHIFT")
    return 1 << int(shift)


def markers() -> dict[str, int]:
    """The sentinels the probe writes, from the probe source itself."""
    text = kernel_text(SELFTEST_C)
    out = {}
    for name, value in re.findall(r"^#define\s+(COW_\w+)\s+(0x[0-9a-fA-F]+)UL",
                                  text, re.MULTILINE):
        out[name] = int(value, 16)
    for name in ("COW_MAGIC", "COW_CHILD_MARK", "COW_PARENT_MARK"):
        if name not in out:
            raise SystemExit(f"k4_cow_probe: {SELFTEST_C} does not define {name}")
    return out


def consts() -> dict[str, int]:
    """The probe's addresses (decimal or hex definitions, same source)."""
    text = kernel_text(SELFTEST_C)
    out = {}
    for name, value in re.findall(r"^#define\s+(COW_\w+)\s+([0-9]+)\b",
                                  text, re.MULTILINE):
        out[name] = int(value)
    for name in ("COW_OFF_CHILD", "COW_OFF_PARENT"):
        if name not in out:
            raise SystemExit(f"k4_cow_probe: {SELFTEST_C} does not define {name}")
    return out


def base_va() -> int:
    text = kernel_text(SELFTEST_C)
    m = re.search(r"^#define\s+COW_VA_BASE\s+\(1UL << (\d+)\)", text,
                  re.MULTILINE)
    if not m:
        raise SystemExit(f"k4_cow_probe: {SELFTEST_C} has no COW_VA_BASE")
    return 1 << int(m.group(1))


def subcauses() -> dict[str, dict]:
    """`contract-see §6.1.1` (ADR-0056 D3), cross-checked with the header."""
    subs = k3page.contract_subcauses()
    header = k3page.header_subcauses()
    if subs["NWPERM"]["bit"] not in header.values():
        raise SystemExit("k4_cow_probe: asm/cause-sub.h disagrees with §6.1.1")
    return subs


def perm_cause_id(subs: dict[str, dict]) -> int:
    """`CFXPERM | (1 << NWPERM)` — the raw id the write fault must report."""
    row = subs["NWPERM"]
    return k3page.causes()["CFXPERM"] | (1 << row["bit"])


def tlb_expectation() -> dict[str, int]:
    """The `invalid | VA`, `ASID_ANY = 0` command value (contract-tlb TLB-19).

    Both the operand values and the field positions come from `asm/ptw.h`, the
    single place the encoding lives; nothing here restates the shifts.
    """
    text = kernel_text(PTW_H)
    ops = dict(re.findall(r"^\s*(DADAO_TLB_\w+)\s*=\s*(\d+),", text,
                          re.MULTILINE))
    shifts = {name: int(value) for name, value in
              re.findall(r"^#define\s+(DADAO_TLB_CTRL_\w+_SHIFT)\s+(\d+)",
                         text, re.MULTILINE)}
    masks = {name: int(value, 0) for name, value in
             re.findall(r"^#define\s+(DADAO_TLB_CTRL_\w+_MASK)\s+(0x[0-9a-fA-F]+)",
                        text, re.MULTILINE)}
    need = ("DADAO_TLB_INVALID", "DADAO_TLB_SCOPE_VA",
            "DADAO_TLB_CTRL_OP_SHIFT", "DADAO_TLB_CTRL_SCOPE_SHIFT",
            "DADAO_TLB_CTRL_ASID_ANY_SHIFT", "DADAO_TLB_CTRL_OP_MASK",
            "DADAO_TLB_CTRL_SCOPE_MASK")
    missing = [n for n in need
               if n not in ops and n not in shifts and n not in masks]
    if missing:
        raise SystemExit(f"k4_cow_probe: asm/ptw.h is missing {missing}")
    value = (((int(ops["DADAO_TLB_INVALID"]) & masks["DADAO_TLB_CTRL_OP_MASK"])
              << shifts["DADAO_TLB_CTRL_OP_SHIFT"]) |
             ((int(ops["DADAO_TLB_SCOPE_VA"]) & masks["DADAO_TLB_CTRL_SCOPE_MASK"])
              << shifts["DADAO_TLB_CTRL_SCOPE_SHIFT"]))
    return {"ctrl": value, "op": int(ops["DADAO_TLB_INVALID"]),
            "scope": int(ops["DADAO_TLB_SCOPE_VA"])}


def write_bit() -> int:
    """`_PAGE_WRITE`'s bit number, from the page-table header (not a literal)."""
    m = re.search(r"^#define\s+_PAGE_WRITE\s+\(_AC\(1, UL\) << (\d+)\)",
                  kernel_text("arch/dadao/include/asm/pgtable.h"), re.MULTILINE)
    if not m:
        raise SystemExit("k4_cow_probe: asm/pgtable.h has no _PAGE_WRITE")
    return int(m.group(1))


def terminal_code(cause: str) -> int:
    """`spec/Kaiwu §7.1` monitor segment for a supv-mode termination."""
    return k3page.monitor_code("supv", cause)


# ---------------------------------------------------------------------------
# console parsing
# ---------------------------------------------------------------------------

def kv(line: str) -> dict[str, str]:
    out = {}
    for token in line.split():
        if "=" in token:
            key, value = token.split("=", 1)
            out[key] = value
    return out


def num(text: str | None, default: int = -1) -> int:
    if text is None:
        return default
    try:
        return int(text, 0)
    except (TypeError, ValueError):
        return default


def check_lines(text: str) -> list[tuple[str, dict[str, str]]]:
    out = []
    for line in text.splitlines():
        m = re.match(r"K4 check (\S+) want=(\S+) got=(\S+) (ok|BAD)$", line)
        if m:
            out.append((m.group(1), {"want": m.group(2), "got": m.group(3),
                                     "verdict": m.group(4)}))
    return out


def named(text: str, prefix: str) -> list[dict[str, str]]:
    return [kv(line) for line in text.splitlines() if line.startswith(prefix)]


def one(text: str, prefix: str) -> dict[str, str] | None:
    rows = named(text, prefix)
    return rows[0] if rows else None


def pf_rows(text: str) -> list[dict[str, str]]:
    return named(text, "K3 pf: ")


def die_row(text: str) -> dict[str, str] | None:
    """The terminal line `traps.c` prints before stopping (`mode`/`code`)."""
    rows = named(text, "dadao: die ")
    return rows[-1] if rows else None


def die_name_row(text: str) -> dict[str, str] | None:
    """The named termination line: `dadao: <why> cause=NAME(0x..) ip=.. info=..`."""
    return k3page.die_line(text)


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def build_image(case: int, label: str = "") -> int:
    # The gate's images are the declared pins; an ad-hoc `--cases N` value is a
    # debug path and overrides just this symbol.
    overrides = IMAGE_PINS.get(str(case),
                               {"CONFIG_DADAO_K4_COW_SELFTEST": str(case)})
    rc = defconfig.apply_config_lines(
        config_pins.config_lines(CONFIG_PINS, overrides))
    if rc != 0:
        print(f"k4_cow_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the COW case {case} image"
          f"{' ' + label if label else ''} (JOBS={JOBS})", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_BUILD)
    except subprocess.TimeoutExpired:
        print("k4_cow_probe: build timed out (124 is a FAIL)", file=sys.stderr)
        return 124
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
    return proc.returncode


def firmware() -> str:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_k4cow.bin")


def boot(tag: str, rom: str) -> tuple[int, str]:
    kernel = build_dir() / "vmlinux"
    if not kernel.is_file():
        raise SystemExit(f"k4_cow_probe: {kernel} missing")
    qemu = str(linux_paths.toolchain_bin() / "qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("k4_cow_probe: qemu-system-dadao missing (make install-host)")
    log_dir = SCRATCH / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    cmd = [qemu, "-machine", f"kaiwu-vast,bootrom-image={rom}", "-nographic",
           "-semihosting-config", "enable=on,target=native", "-kernel", str(kernel)]
    proc = subprocess.Popen(cmd, cwd=str(_REPO), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=TIMEOUT_QEMU)
        rc = proc.returncode & 0xFF
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        rc = 124
    text = (err or "") + (out or "")
    (log_dir / f"{tag}.log").write_text(text, encoding="utf-8")
    return rc, text


# ---------------------------------------------------------------------------
# judging
# ---------------------------------------------------------------------------

def judge_shared(rep: Report, text: str, rc: int, d: dict) -> None:
    """Case 1: W1 + W2 + W4 + W5, one boot that must end by SYS_EXIT(0)."""
    va = d["va"]
    begin = one(text, "K4 cow: begin")
    rep.check("B", "镜像跑到 COW 自检", "1", begin.get("case") if begin else None)
    rep.check("B", "页大小 == 镜像配置派生值（§2.2.2）", d["page"],
              num(begin.get("page")) if begin else None)
    rep.check("B", "COW 窗口基址 == 探针源码", va,
              num(begin.get("shared")) if begin else None)

    mm = one(text, "K4 cow mm:")
    rep.check("B", "地址空间行存在", True, mm is not None)
    if mm:
        rep.check("B", "mm 有自己的 ASID（≠ 内核的 0）", True,
                  num(mm.get("asid")) > 0)

    rows = check_lines(text)
    bad = [name for name, row in rows if row["verdict"] != "ok"]
    rep.check("B", "内核自评的每条 check 都 ok", [], bad)
    seen = " ".join(name for name, _row in rows)
    for case in ("w1-", "w2-", "w4-", "w5-"):
        rep.check(case[:2].upper(), f"{case}* 断言存在（vacuous ⇒ FAIL）", True,
                  case in seen)

    # ---- the sharing the fork created -----------------------------------
    setup = one(text, "K4 cow setup:")
    rep.check("W1", "写前页引用计数 == 1", 1,
              num(setup.get("count")) if setup else None)
    rep.check("W1", "写前内容是探针的哨兵", d["marks"]["COW_MAGIC"],
              num(setup.get("content")) if setup else None)
    fork = one(text, "K4 cow fork:")
    rep.check("W1", "fork 行存在", True, fork is not None)
    rep.check("W1", "子任务存在（pid > 0）", True,
              num(fork.get("pid")) > 0 if fork else None)
    rep.check("W1", "父子 PA 相同（共享，不是私有复制）", 1,
              num(fork.get("same")) if fork else None)
    rep.check("W1", "子侧 PTE 只读（隔离的前提）", 0,
              num(fork.get("w_child")) if fork else None)
    rep.check("W1", "父侧 PTE 只读（fork 写保护）", 0,
              num(fork.get("w_parent")) if fork else None)
    rep.check("W1", "arch 钩子看到了共享页（dup_pages >= 1）", True,
              num(fork.get("dup_pages")) >= 1 if fork else None)
    rep.check("W1", "没有子侧仍可写的共享页", 0,
              num(fork.get("dup_writable")) if fork else None)

    # ---- W1: the copy ---------------------------------------------------
    child = one(text, "K4 cow child:")
    rep.check("W1", "子任务真的跑了（独立地址空间）", True, child is not None)
    if child:
        rep.check("W1", "子读到的就是父写的哨兵", d["marks"]["COW_MAGIC"],
                  num(child.get("read")))
        rep.check("W1", "子写后自己读回新值", 1, num(child.get("store_ok")))
        rep.check("W1", "子写前看到的是共享 PA", num(child.get("pa")),
                  num(fork.get("parent_pa")) if fork else None)
    w1 = one(text, "K4 cow w1:")
    rep.check("W1", "W1 行存在", True, w1 is not None)
    if w1:
        rep.check("W1", "写侧 PTE PA 已换（≠ 原 PA）", True,
                  num(w1.get("child_new_pa")) != num(w1.get("orig_pa")))
        rep.check("W1", "新页第 0 字 == 旧页哨兵（复制而非清零）",
                  d["marks"]["COW_MAGIC"], num(w1.get("content0")))
        rep.check("W1", "新页第 8 字 == 子写的值", d["marks"]["COW_CHILD_MARK"],
                  num(w1.get("content1")))
        rep.check("W1", "写侧 PTE 现在可写", 1, num(w1.get("child_w")))
        rep.check("W1", "新页引用计数 == 1", 1, num(w1.get("new_count")))
        rep.check("W1", "PA 已按页对齐", 0,
                  num(w1.get("child_new_pa")) % d["page"])

    cov = [row for row in named(text, "K4 cow: kind=") if row.get("kind") == "copy"]
    rep.check("W1", "通道记了一次复制（kind=copy，恰好一次）", 1, len(cov))
    if cov:
        row = cov[0]
        rep.check("W1", "复制用的是写侧的 VA", va + d["consts"]["COW_OFF_CHILD"],
                  num(row.get("va")))
        rep.check("W1", "复制前引用计数 == 2（fork 的第二份）", 2, num(row.get("count")))
        rep.check("W1", "复制后旧页引用计数 == 1（put_page 到位）", 1,
                  num(row.get("after")))

    # ---- W2: non-interference -------------------------------------------
    w2 = one(text, "K4 cow w2:")
    rep.check("W2", "W2 行存在", True, w2 is not None)
    if w2:
        rep.check("W2", "父侧 PA == 原 PA", num(setup.get("pa")) if setup else None,
                  num(w2.get("parent_pa")))
        rep.check("W2", "父侧内容 == 写前内容", d["marks"]["COW_MAGIC"],
                  num(w2.get("content0")))
        rep.check("W2", "父侧看不到子写的那一字", 0, num(w2.get("content1")))
        rep.check("W2", "父侧页引用计数已减回 1", 1, num(w2.get("count")))

    # ---- W5: the invalidation and the in-place upgrade -------------------
    w5 = one(text, "K4 cow w5:")
    rep.check("W5", "W5 行存在", True, w5 is not None)
    if w5:
        rep.check("W5", "父写又进了一次通道（PTE 仍只读）", 1, num(w5.get("entries")))
        rep.check("W5", "第二次写就地升级（没有第二次复制）", 1, num(w5.get("inplace")))
        rep.check("W5", "第二次写没有复制", 0, num(w5.get("copies")))
        rep.check("W5", "第二次写没有 put（唯一引用）", 0, num(w5.get("puts")))
        rep.check("W5", "就地升级不改 PA", num(setup.get("pa")) if setup else None,
                  num(w5.get("pa")))
        rep.check("W5", "父侧内容 == 父写的值", d["marks"]["COW_PARENT_MARK"],
                  num(w5.get("content")))
        rep.check("W5", "失效命令 == contract-tlb TLB-19 的 invalid|VA（ASID_ANY=0）",
                  d["tlb"]["ctrl"], num(w5.get("ctrl")))
        rep.check("W5", "失效的 ASID_ANY == 0（不碰 G=1 内核映射）", 0,
                  num(w5.get("flush_any")))
        rep.check("W5", "失效的 ASID == 写侧 mm 的 ASID", num(w5.get("mm_asid")),
                  num(w5.get("flush_asid")))
        # The kernel invalidates the *page* the fault belongs to: a TLB entry
        # covers a page and `invalid|VA` matches the entries containing the
        # address it names (contract-tlb TLB-23), so a page-aligned start is
        # the correct operand.  The check still fails on a wrong page.
        rep.check("W5", "失效的 VA 落在故障页（TLB-23：页内偏移不参与匹配）", va,
                  num(w5.get("flush_va")) & ~(d["page"] - 1))
    if cov and child:
        # The copy's own invalidation names the *child's* ASID: the copy is the
        # child's, so its stale translation is the child's to drop.
        rep.check("W5", "复制的失效 ASID == 子 mm 的 ASID",
                  num(child.get("asid")), num(cov[0].get("asid")))
        rep.check("W5", "复制的失效 ASID_ANY == 0", 0, num(cov[0].get("any")))
        rep.check("W5", "复制的失效命令值 == invalid|VA", d["tlb"]["ctrl"],
                  num(cov[0].get("ctrl")))

    # ---- W4: the last reference -----------------------------------------
    w4 = one(text, "K4 cow w4:")
    rep.check("W4", "W4 行存在", True, w4 is not None)
    if w4:
        rep.check("W4", "unmap 前引用计数 == 1（末引用）", 1,
                  num(w4.get("refs_before")))
        rep.check("W4", "unmap 后引用计数 == 0（页回池）", 0,
                  num(w4.get("refs_after")))
        rep.check("W4", "unmap 后该 VA 不再有 PTE", 0, num(w4.get("pte")))

    # ---- the channel's own verdicts for the two writes -------------------
    pf = pf_rows(text)
    id_nwperm = d["nwperm_id"]
    # Three NWPERM entries: the parent's own population before the fork
    # (`replace-zero`), the child's write (`cow-copy`) and the parent's write
    # (`cow-write`) — and each `cause_info` is that access's own address (§6.1).
    nwperm = [row for row in pf if row.get("sub") == "NWPERM"]
    rep.check("B", "通道报了三笔 NWPERM（建页 + 子写 + 父写）", 3, len(nwperm))
    rep.check("B", "三笔 NWPERM 的 cause_info 就是各自的故障地址（§6.1）",
              [va, va + d["consts"]["COW_OFF_CHILD"],
               va + d["consts"]["COW_OFF_PARENT"]],
              [num(row.get("va")) for row in nwperm])
    rep.check("B", "三笔 NWPERM 的 cause_id 都是 CFXPERM|NWPERM",
              [hex(id_nwperm)] * 3, [row.get("id") for row in nwperm])
    rep.check("B", "分支次序：建页 → 子写复制 → 父写就地",
              ["replace-zero", "cow-copy", "cow-write"],
              [row.get("result") for row in nwperm])

    done = one(text, "K4 cow done:")
    rep.check("W1", "自检走到 done 行", True, done is not None)
    rep.check("W1", "整机 rc == 0（SYS_EXIT(0)）", 0, rc)
    rep.check("B", "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K4 cow FAIL")])


def judge_perm(rep: Report, text: str, rc: int, d: dict) -> None:
    """Case 3: W3 — a VM_SHARED read-only page is a genuine violation."""
    va = d["va"]
    begin = one(text, "K4 cow: begin")
    rep.check("B", "镜像跑到 COW 自检的 W3 镜像", "3",
              begin.get("case") if begin else None)
    rep.check("B", "页大小 == 镜像配置派生值（§2.2.2）", d["page"],
              num(begin.get("page")) if begin else None)

    w3 = one(text, "K4 cow w3:")
    rep.check("W3", "W3 前置行存在", True, w3 is not None)
    if w3:
        rep.check("W3", "映射确实是 VM_SHARED（构造有效）", 1, num(w3.get("shared")))
        rep.check("W3", "页已映射", True, num(w3.get("pa")) > 0)
        rep.check("W3", "页 PTE 只读（构造有效）", 0, num(w3.get("w")))
        rep.check("W3", "页按页对齐", 0, num(w3.get("pa")) % d["page"])

    pf = pf_rows(text)
    rep.check("W3", "通道只进了一次（不重试、不复制）", 1, len(pf))
    if pf:
        row = pf[0]
        rep.check("W3", "大类 == CFXPERM", "CFXPERM", row.get("cause"))
        rep.check("W3", "子原因 == NWPERM", "NWPERM", row.get("sub"))
        rep.check("W3", "原始 cause_id == CFXPERM|NWPERM", hex(d["nwperm_id"]),
                  row.get("id"))
        rep.check("W3", "分支 == die-perm（真越权，不走 COW）", "die-perm",
                  row.get("result"))
        rep.check("W3", "cause_info == 故障 VA", va, num(row.get("va")))
    rep.check("W3", "没有分配页（COW 没有插手）", "0",
              pf[0].get("pool") if pf else None)

    die = die_row(text)
    named_die = die_name_row(text)
    rep.check("W3", "终止行存在", True, die is not None)
    rep.check("W3", "带原因名的终止行存在", True, named_die is not None)
    if die:
        rep.check("W3", "终止的退出段 == §7.1 monitor(supv, CFXPERM)",
                  hex(terminal_code("CFXPERM")), die.get("code"))
        rep.check("W3", "终止时的运行模式 == supv（§7.1 段里的 mode）", 2,
                  num(die.get("mode")))
    if named_die:
        rep.check("W3", "终止原因名 == CFXPERM", "CFXPERM",
                  named_die.get("cause"))
        rep.check("W3", "终止的 cause_info == 故障 VA", hex(va),
                  named_die.get("info"))
    rep.check("W3", "整机以该段结束", terminal_code("CFXPERM"), rc & 0xFF)
    rep.check("W3", "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K4 cow FAIL")])


def derivations() -> dict:
    subs = subcauses()
    return {
        "page": page_size(),
        "va": base_va(),
        "marks": markers(),
        "consts": consts(),
        "tlb": tlb_expectation(),
        "nwperm_id": perm_cause_id(subs),
        "write_bit": write_bit(),
    }


# ---------------------------------------------------------------------------
# injections: corrupt one rule, rebuild, prove the owning case goes red
# ---------------------------------------------------------------------------

INJECTIONS = {
    "alloc-no-copy": {
        "edits": [(COW_C,
                   "\t\tmemcpy(__va(pa), __va(old_pa), PAGE_SIZE);\n",
                   "\t\t/* injected: the old contents are not carried over */\n")],
        "case": 1,
        "why": "复制时不清零（新页不拷旧内容）⇒ W1 的哨兵丢失",
    },
    "pte-stays-old": {
        "edits": [(COW_C,
                   "\t\tfresh = __pte((pa & _PAGE_PFN_MASK) |\n"
                   "\t\t\t      (pte_val(entry) & ~_PAGE_PFN_MASK));\n",
                   "\t\tfresh = entry;\t/* injected: the PTE keeps the old PA */\n")],
        "case": 1,
        "why": "分配了但 PTE 仍指旧 PA ⇒ W1 的 PA 没换（写到的还是旧页）",
    },
    "no-invalidate": {
        "edits": [(COW_C,
                   "\tcow_invalidate(vma, addr);\n\n#if CONFIG_DADAO_K4_COW_SELFTEST",
                   "\t/* injected: the stale translation is not dropped */\n\n"
                   "#if CONFIG_DADAO_K4_COW_SELFTEST")],
        "case": 1,
        "why": "装了新 PTE 不失效 ⇒ 重试的写仍命中旧翻译 ⇒ W1/W5 红",
    },
    "asid-any": {
        "edits": [(COW_C,
                   "\tbool asid_any = false;\n\tunsigned long asid",
                   "\tbool asid_any = true;\t/* injected: ASID_ANY = 1 */\n"
                   "\tunsigned long asid")],
        "case": 1,
        "why": "失效用 ASID_ANY=1（顺带清 G=1）⇒ 命令不再键到本 mm 的 ASID",
    },
    "sole-ref-copies": {
        "edits": [(COW_C,
                   "\tif (count == 1) {\n",
                   "\tif (0) {\t/* injected: the sole reference copies too */\n")],
        "case": 1,
        "why": "page_count==1 也走复制（独占页不就地升级）⇒ 父侧第二次写换了 PA ⇒ W5 红",
    },
}


def expect_red(rep: Report, name: str, text: str, rc: int, case: int,
               d: dict) -> None:
    """The injected image must break the case's expectation."""
    if case == 1:
        bad = [n for n, row in check_lines(text) if row["verdict"] != "ok"]
        rep.check(f"INJECT {name}", "内核自评出现 BAD（或整机不再 rc=0）", True,
                  bool(bad) or rc != 0)
        if not bad:
            rep.info(f"inject {name}: rc={rc}, no BAD check line "
                     f"(named termination is also red)")
        return
    pf = pf_rows(text)
    stopped = bool(pf) and pf[-1].get("result") == "die-perm"
    rep.check(f"INJECT {name}", f"case {case} 不再以 die-perm 结束", False, stopped)


def run_injection(rep: Report, name: str, rom: str, d: dict) -> None:
    spec = INJECTIONS[name]
    case = spec["case"]
    why = spec["why"]
    saved: list[tuple[Path, bytes, str]] = []
    try:
        for rel, needle, repl in spec["edits"]:
            path = SOURCE / rel
            original = path.read_bytes()
            saved.append((path, original, md5(path)))
            text = original.decode()
            if needle not in text:
                rep.check(f"INJECT {name}", f"注入点存在于源码（{rel}）", True, False)
                return
            path.write_text(text.replace(needle, repl, 1), encoding="utf-8")
        rc = build_image(case, f"injected:{name}")
        if rc != 0:
            rep.check(f"INJECT {name}", f"注入后镜像可构建（{why}）", 0, rc)
            return
        rc, out = boot(f"inject-{name}", rom)
        expect_red(rep, name, out, rc, case, d)
    finally:
        for path, original, before in saved:
            path.write_bytes(original)
            rep.check(f"INJECT {name}", f"还原 {path.name}（cp + md5 对账）",
                      before, md5(path))
        rc = build_image(case, "restored")
        rep.check(f"INJECT {name}", "还原后可构建", 0, rc)
        if rc == 0:
            rc2, out2 = boot(f"restored-{name}", rom)
            if case == 1:
                rep.check(f"INJECT {name}", "还原后回绿（自评全 ok 且 rc=0）", [],
                          [n for n, r in check_lines(out2) if r["verdict"] != "ok"])
                rep.check(f"INJECT {name}", "还原后整机 rc == 0", 0, rc2)
            else:
                pf = pf_rows(out2)
                rep.check(f"INJECT {name}", "还原后回绿（die-perm 回来）",
                          "die-perm", pf[-1].get("result") if pf else None)


# ---------------------------------------------------------------------------
# self-check: the judging itself must be able to fail
# ---------------------------------------------------------------------------

def selfcheck() -> int:
    """Prove the judging can fail: a corrupted console must be red."""
    d = derivations()
    rep = Report()
    va = d["va"]
    text = (
        f"K4 cow: begin case=1 page=0x{d['page']:x} shared=0x{va:x}\n"
        "K4 cow mm: mm=0x1000 pgd=0x2000 asid=1 ptbr=0x2000 page=65536 shift=16\n"
        f"K4 cow setup: va=0x{va:x} pa=0x40000 content=0x4b34434f57000001 "
        f"count=1 w=1 copies=0 inplace=0 puts=0\n"
        f"K4 cow fork: pid=1 parent_pa=0x40000 child_pa=0x40000 same=1 "
        f"w_parent=0 w_child=0 count=2 dup_pages=1 dup_writable=0\n"
        # ... and the same values corrupted, one per judgement:
        f"K4 cow w1: orig_pa=0x40000 child_pa=0x40000 child_new_pa=0x40000 "
        f"child_w=1 content0=0x0 content1=0x0 new_count=1\n"
        f"K4 cow w2: parent_pa=0x41000 content0=0x0 content1=0xdead count=2\n"
        f"K4 cow w5: entries=2 copies=1 inplace=0 puts=1 pa=0x41000 "
        f"content=0x0 ctrl=0x1f asid=1 flush_asid=9 flush_any=1 flush_va=0x0 "
        f"mm_asid=1\n"
        f"K4 cow w4: refs_before=2 refs_after=7 puts=0 va=0x{va:x} pte=0x1\n"
        "K4 cow: kind=copy va=0x8000000008 page=0x10000 old_pa=0x40000 "
        "new_pa=0x41000 count=3 after=5 ctrl=0x1f asid=3 any=1 copies=1 "
        "inplace=0 puts=0\n"
        "K4 check w1-pa-moved want=0x1 got=0x0 BAD\n"
    )
    judge_shared(rep, text, 1, d)
    red = rep.failed
    print(f"[SELFCHECK] red checks: {len(red)}")
    for name in red[:10]:
        print(f"[SELFCHECK]   {name}")
    if not red:
        print("[SELFCHECK] FAIL: a broken console produced no red check")
        return 1
    groups = {name.split(":")[0] for name in red}
    print(f"[SELFCHECK] groups that went red: {sorted(groups)}")
    if len(groups) < 3:
        print("[SELFCHECK] FAIL: too few groups catch the corruption")
        return 1
    print("[SELFCHECK] PASS: the judging goes red on a broken console")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inject", metavar="NAME")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--cases", default="1,3")
    args = ap.parse_args()

    if args.list:
        for name, spec in INJECTIONS.items():
            files = ",".join(rel for rel, _n, _r in spec["edits"])
            print(f"{name}: {files} (case {spec['case']}) — {spec['why']}")
        return 0
    if args.selfcheck:
        return selfcheck()

    d = derivations()
    print(f"[INFO] page={d['page']} va={hex(d['va'])} "
          f"nwperm_id={hex(d['nwperm_id'])} ctrl={hex(d['tlb']['ctrl'])} "
          f"marks={ {k: hex(v) for k, v in d['marks'].items()} }", flush=True)
    rep = Report()
    rom = firmware()

    if args.inject:
        run_injection(rep, args.inject, rom, d)
    else:
        for case in [int(x) for x in args.cases.split(",") if x.strip()]:
            if case not in CASES:
                rep.check(f"case{case}", "已知的 case 编号", list(CASES), case)
                continue
            rc = build_image(case)
            if rc != 0:
                rep.check(f"case{case}", "镜像可构建", 0, rc)
                continue
            rc, text = boot(f"case{case}", rom)
            pf = pf_rows(text)
            rep.info(f"case {case}: rc={rc} pf={len(pf)} last="
                     f"{pf[-1] if pf else None}")
            if case == 1:
                judge_shared(rep, text, rc, d)
            else:
                judge_perm(rep, text, rc, d)

    print(f"k4_cow_probe: {rep.total - len(rep.failed)}/{rep.total} checks "
          f"passed, {len(rep.failed)} failed")
    for name in rep.failed:
        print(f"  - {name}")
    return 0 if not rep.failed else 1


if __name__ == "__main__":
    sys.exit(main())
