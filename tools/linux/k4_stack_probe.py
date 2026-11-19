#!/usr/bin/env python3
"""k4_stack_probe.py — M14 K4 user-stack growth probe (`m14-linux-019` S1-S6).

The port grows a `VM_GROWSDOWN` stack inside the page-fault channel
(`arch/dadao/mm/fault.c`): a *missing*-class fault below the VMA extends it
through the generic `expand_stack_locked()`, which is where Linux's own
`stack_guard_gap` and `RLIMIT_STACK` rules apply.  The kernel side of this gate is
`arch/dadao/mm/k4_stack_selftest.c` (`CONFIG_DADAO_K4_STACK_SELFTEST`), which
raises the faults from supv mode, the vehicle the task book allows while the
U-mode closure of `m14-linux-016/017` is still open.

Cases (one image per value, because "did not grow" is a named termination):

  S1  one page down: the VMA grows by exactly one page and the page is filled;
  S2  two pages down: it grows again, size == starting size + 2 pages;
  S5  a permission-class fault (write to the fill-zero page) inside the VMA does
      not grow it — growth counter and `vm_start` unchanged;
  S3  a step that would exceed `RLIMIT_STACK` does not grow (`die-no-vma`);
  S4  a VMA without `VM_GROWSDOWN` does not grow (`die-no-vma`);
  S6  growth that would enter `stack_guard_gap` does not happen (`die-no-vma`),
      with the neighbour placed so the gap binds before the limit.

Everything is derived, never restated: the page size comes from the image's own
`.config`, the VMA edges and counters from the kernel's print, and the verdict
strings from the channel's own result names.

`--inject` corrupts one rule, rebuilds, asserts the owning case goes red,
restores with `cp` + md5 and proves the case is green again.

Exit status: 0 = every check passed; 1 = a FAIL; 2 = an input could not be
derived (config / kernel source / build tree missing).
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

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins                          # noqa: E402  (pins)
from tools.linux import make_defconfig as defconfig          # noqa: E402
from tools.linux import paths as linux_paths                 # noqa: E402
from tools.qemu import k0_boot_probe as k0                   # noqa: E402

SCRATCH = (Path(os.environ.get("K4ST_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m14-linux-017") / "check-linux-k4-stack")
SOURCE = linux_paths.linux_source_dir()

#: Every milestone probe pinned off; the case is the one per-image override
#: (`make check-config-pins`, ISS-470; an int pinned ``"n"`` is "left unset"
#: because its `depends on` is not met).
CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_TIME_STOP": "n",
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
    # m14-linux-018: the copy-on-write probe is an int with no `depends on`, so
    # it carries a concrete value rather than "unset".
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
}

#: The stack case each image carries (0 = off is not an image here: the gate
#: builds one image per case).
IMAGE_PINS = {
    "1": {"CONFIG_DADAO_K4_STACK_SELFTEST": "1"},
    "3": {"CONFIG_DADAO_K4_STACK_SELFTEST": "3"},
    "4": {"CONFIG_DADAO_K4_STACK_SELFTEST": "4"},
    "6": {"CONFIG_DADAO_K4_STACK_SELFTEST": "6"},
}

CASES = {1: ("S1", "S2", "S5"), 3: ("S3",), 4: ("S4",), 6: ("S6",)}

TIMEOUT_BUILD = int(os.environ.get("K4ST_BUILD_TIMEOUT", "2400"))
TIMEOUT_QEMU = int(os.environ.get("K4ST_QEMU_TIMEOUT", "180"))
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
        raise SystemExit(f"k4_stack_probe: kernel source missing: {rel}")
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
    """The page size the image actually runs with (its own `.config`)."""
    shift = config_value("CONFIG_PAGE_SHIFT")
    if shift is None:
        raise SystemExit("k4_stack_probe: the image has no CONFIG_PAGE_SHIFT")
    return 1 << int(shift)


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


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def build_image(case: int, label: str = "") -> int:
    # The gate's four images are the declared pins; an ad-hoc `--cases N` value
    # is a debug path and overrides just this symbol.
    overrides = IMAGE_PINS.get(str(case),
                               {"CONFIG_DADAO_K4_STACK_SELFTEST": str(case)})
    rc = defconfig.apply_config_lines(
        config_pins.config_lines(CONFIG_PINS, overrides))
    if rc != 0:
        print(f"k4_stack_probe: FAIL: config slice rc={rc}", file=sys.stderr)
        return rc
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    print(f"[INFO] build the stack case {case} image{' ' + label if label else ''} "
          f"(JOBS={JOBS})", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True,
                              text=True, timeout=TIMEOUT_BUILD)
    except subprocess.TimeoutExpired:
        print("k4_stack_probe: build timed out (124 is a FAIL)", file=sys.stderr)
        return 124
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
    return proc.returncode


def firmware() -> str:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_k4st.bin")


def boot(tag: str, rom: str) -> tuple[int, str]:
    kernel = build_dir() / "vmlinux"
    if not kernel.is_file():
        raise SystemExit(f"k4_stack_probe: {kernel} missing")
    qemu = str(linux_paths.toolchain_bin() / "qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("k4_stack_probe: qemu-system-dadao missing (make install-host)")
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

def judge_positive(rep: Report, text: str, rc: int) -> None:
    """Case 1: S1 + S2 + S5, one boot that must end by SYS_EXIT(0)."""
    page = page_size()
    begin = one(text, "K4 stack: begin")
    rep.check("B", "镜像跑到栈增长自检", "1", begin.get("case") if begin else None)
    got = begin.get("page") if begin else None
    rep.check("B", "页大小 == 镜像配置派生值", page,
              int(got, 0) if got is not None else None)
    setup = one(text, "K4 stack setup:")
    rep.check("B", "setup 行存在（VMA 边沿可用）", True, setup is not None)
    if setup:
        rep.check("B", "栈 VMA 起始大小 == 2 页", "2", setup.get("pages"))

    rows = check_lines(text)
    bad = [name for name, row in rows if row["verdict"] != "ok"]
    rep.check("B", "内核自评的每条 check 都 ok", [], bad)
    seen = " ".join(name for name, _ in rows)
    for case in CASES[1]:
        rep.check(case, f"{case} 的断言存在（vacuous ⇒ FAIL）", True,
                  case.lower() in seen.lower())

    grows = {name: row["got"] for name, row in rows if name.endswith("-grows")}
    rep.check("S1", "扩栈计数 +1（现场读值）", "0x1", grows.get("s1-grows"))
    rep.check("S2", "扩栈计数 +2（第二次也扩）", "0x2", grows.get("s2-grows"))
    rep.check("S5", "权限类故障没有扩栈（计数仍为 2）", "0x2",
              grows.get("s5-grows"))

    # Independent of the kernel's own verdict lines: the channel's fault reports
    # must show the VMA edge *at the faulting page* for the two grown faults.
    pf = pf_rows(text)
    grown = [row for row in pf
             if row.get("result") == "fill-zero" and
             row.get("vma", "").split("-")[0] == row.get("va")]
    rep.check("S1", "通道报出的 vma 起点 == 故障页，且恰好两次（现场读值）", "2",
              str(len(grown)))
    done = one(text, "K4 stack done:")
    rep.check("S1", "自检走到 done 行", True, done is not None)
    rep.check("S1", "整机 rc == 0（SYS_EXIT(0)）", 0, rc)


def judge_stop(rep: Report, text: str, rc: int, case: int) -> None:
    """Cases 3/4/6: the fault must end the boot with `die-no-vma`."""
    page = page_size()
    begin = one(text, "K4 stack: begin")
    rep.check("B", "镜像跑到栈增长自检", str(case),
              begin.get("case") if begin else None)
    got = begin.get("page") if begin else None
    rep.check("B", "页大小 == 镜像配置派生值", page,
              int(got, 0) if got is not None else None)
    setup = {3: "K4 stack s3:", 4: "K4 stack s4:", 6: "K4 stack s6:"}[case]
    row = one(text, setup)
    rep.check("B", f"case 行存在（{setup}）", True, row is not None)
    rep.check("B", "故障前没有扩过栈（现场读值）", "0",
              row.get("grows") if row else None)

    if case == 3 and row:
        # The step must be longer than RLIMIT_STACK, so the limit is the rule
        # that stopped it — nothing else in the layout can.
        rep.check("S3", "一步下沉量 > RLIMIT_STACK（构造有效）", True,
                  int(row["dist"], 0) > int(row["limit"], 0))
    if case == 6 and row:
        # Gap binds first: the address is inside the gap, and the grown size
        # would still be under the limit.
        rep.check("S6", "下沉进入 stack_guard_gap（构造有效）", True,
                  int(row["dist"], 0) < int(row["gap_budget"], 0))
        rep.check("S6", "且扩展后仍在 RLIMIT_STACK 内（gap 先于 limit）", True,
                  int(row["size"], 0) < int(row["limit"], 0))

    pf = pf_rows(text)
    rep.check(str(case), "通道判词 == die-no-vma", True,
              bool(pf) and pf[-1].get("result") == "die-no-vma")
    rep.check(str(case), "最后一条故障地址 == case 的目标", True,
              bool(pf) and row is not None and pf[-1].get("va") == row.get("target"))
    rep.check(str(case), "内核没有自报 FAIL 行", [],
              [line.strip() for line in text.splitlines()
               if line.startswith("K4 stack FAIL")])
    rep.check(str(case), "整机以终止结束（rc != 0）", True, rc != 0)
    rep.check(str(case), "终止原因 == CFXMEM 的 supv 分段（§7.1）", "0xe1",
              f"0x{(rc & 0xff):x}" if rc not in (0, 124) else f"0x{rc:x}")


INJECTIONS = {
    # name: {edits: [(file, needle, replacement)], case, why}
    "grow-any-vma": {
        "edits": [
            # Our branch's own check ...
            ("arch/dadao/mm/fault.c",
             "\tif (!vma || addr >= vma->vm_start ||\n"
             "\t    !(vma->vm_flags & VM_GROWSDOWN)) {\n",
             "\tif (!vma || addr >= vma->vm_start) {\n"),
            # ... and the generic one it leans on: a single edit can never make
            # S4 red, because `expand_downwards()` tests the flag again (that
            # double guard is why this injection has to remove both).
            ("mm/vma.c",
             "\tif (!vma_test(vma, VMA_GROWSDOWN_BIT))\n"
             "\t\treturn -EFAULT;\n",
             ""),
        ],
        "case": 4,
        "why": "去掉两处 VM_GROWSDOWN 判定（任何 VMA 可扩）⇒ S4 不再 die-no-vma",
    },
    "no-limit": {
        "edits": [
            ("mm/vma.c",
             "\t/* Stack limit test */\n"
             "\tif (size > rlimit(RLIMIT_STACK))\n"
             "\t\treturn -ENOMEM;\n",
             ""),
        ],
        "case": 3,
        "why": "去掉 RLIMIT_STACK 判定（无限扩）⇒ S3 不再 die-no-vma",
    },
    "perm-grows": {
        "edits": [
            ("arch/dadao/mm/fault.c",
             "\t\tif (pos == DADAO_SUB_NWPERM && dadao_pf_unshare_zero(vma, info))",
             "\t\tif (pos == DADAO_SUB_NWPERM)\n"
             "\t\t\tdadao_pf_grows++;\t/* injected: perm class 'grows' */\n"
             "\t\tif (pos == DADAO_SUB_NWPERM && dadao_pf_unshare_zero(vma, info))"),
        ],
        "case": 1,
        "why": "权限类也被记成一次扩栈 ⇒ S5 的扩栈计数变成 3",
    },
    "no-guard-gap": {
        "edits": [
            ("mm/vma.c",
             "\t\tif (!vma_test(prev, VMA_GROWSDOWN_BIT) &&\n"
             "\t\t    vma_is_accessible(prev) &&\n"
             "\t\t    (address - prev->vm_end < stack_guard_gap))\n"
             "\t\t\treturn -ENOMEM;\n",
             ""),
        ],
        "case": 6,
        "why": "去掉 stack_guard_gap 判定 ⇒ S6 不再 die-no-vma",
    },
}


def expect_red(rep: Report, name: str, row_ok: bool, text: str, rc: int,
               case: int) -> None:
    """The injected image must break this case's expectation."""
    if name == "perm-grows":
        grows = {n: r["got"] for n, r in check_lines(text) if n.endswith("-grows")}
        rep.check(f"INJECT {name}", "S5 的扩栈计数不再 == 2", True,
                  grows.get("s5-grows") != "0x2")
        return
    pf = pf_rows(text)
    stopped = bool(pf) and pf[-1].get("result") == "die-no-vma"
    rep.check(f"INJECT {name}", f"case {case} 不再以 die-no-vma 结束", False, stopped)
    if not stopped:
        rep.info(f"inject {name}: rc={rc} last_pf={pf[-1] if pf else None}")


def run_injection(rep: Report, name: str, rom: str) -> None:
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
        expect_red(rep, name, True, out, rc, case)
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
                rows = check_lines(out2)
                rep.check(f"INJECT {name}", "还原后回绿（自评全 ok）", [],
                          [n for n, r in rows if r["verdict"] != "ok"])
            else:
                pf = pf_rows(out2)
                rep.check(f"INJECT {name}", "还原后回绿（die-no-vma 回来）",
                          "die-no-vma", pf[-1].get("result") if pf else None)


def selfcheck() -> int:
    """Prove the judging can fail: a console with a wrong verdict must be red."""
    rep = Report()
    text = (
        "K4 stack: begin case=1 page=0x1000\n"
        "K4 stack setup: vma=0x1000-0x3000 pages=3 rlimit=1 gap=1 grows=0\n"
        "K4 check s1-value want=0x0 got=0x0 ok\n"
        "K4 check s1-grows want=0x1 got=0x2 BAD\n"
        "K4 check s5-grows want=0x2 got=0x3 BAD\n"
        "K3 pf: n=1 id=0x2 cause=CFXMEM sub=DGPTRAP ip=0x1 va=0x14000030000 "
        "vma=0x14000040000-0x14000060000 pte=0x0 pool=1 try=1 result=fill-zero\n"
    )
    judge_positive(rep, text, 1)
    red = rep.failed
    print(f"[SELFCHECK] red checks: {len(red)}")
    for name in red[:8]:
        print(f"[SELFCHECK]   {name}")
    if not red:
        print("[SELFCHECK] FAIL: a broken console produced no red check")
        return 1
    print("[SELFCHECK] PASS: the judging goes red on a broken console")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inject", metavar="NAME")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--cases", default="1,3,4,6")
    args = ap.parse_args()

    if args.list:
        for name, spec in INJECTIONS.items():
            files = ",".join(rel for rel, _n, _r in spec["edits"])
            print(f"{name}: {files} (case {spec['case']}) — {spec['why']}")
        return 0
    if args.selfcheck:
        return selfcheck()

    rep = Report()
    rom = firmware()

    if args.inject:
        run_injection(rep, args.inject, rom)
    else:
        for case in [int(x) for x in args.cases.split(",") if x.strip()]:
            rc = build_image(case)
            if rc != 0:
                rep.check(f"case{case}", "镜像可构建", 0, rc)
                continue
            rc, text = boot(f"case{case}", rom)
            pf = pf_rows(text)
            rep.info(f"case {case}: rc={rc} pf={len(pf)} last="
                     f"{pf[-1] if pf else None}")
            if case == 1:
                judge_positive(rep, text, rc)
            else:
                judge_stop(rep, text, rc, case)

    print(f"k4_stack_probe: {rep.total - len(rep.failed)}/{rep.total} checks "
          f"passed, {len(rep.failed)} failed")
    for name in rep.failed:
        print(f"  - {name}")
    return 0 if not rep.failed else 1


if __name__ == "__main__":
    sys.exit(main())
