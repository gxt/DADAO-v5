#!/usr/bin/env python3
"""`tools/gem5/check_node_escape_intr.py` — `nodeEscape` 不得改写异步来源掩码
（ISS-472 / m20-gem5-001）。

判据（Independent oracle，来自 `spec/DADAO-12 §5.2(三)/§5.3` 的 0.8.0-rc
口径与 `contract-see §3`）：

  * 同步异常的进入**不保存任何来源掩码**（`§5.2` 第 4 步）；
  * 同步帧的 `escape` **不恢复任何来源掩码**（`§5.3` 第 3 步）——来源掩码是
    当前运行模式 monitor 的 `cg8 rc1`（策略，不是异常现场）；
  * 因此"同步异常 → `escape`"前后，monitor 的 `global_cfx_intr_mask`
    （`cfx0`–`cfx3 cg8 rc1`）必须逐位不变。

ISS-472 描述的 2026-11-25 前实现（m16-gem5-026 之前）在 `nodeEscape` 无条件写
`s.cfx[savedIntrMonitor].globalCfxIntrMask = savedGlobalIntrMask`。本探针的同步
帧属于当前 monitor `cfx3`：本 ROM 的 power→hmon `trap cfx3` 已把
`savedIntrMonitor` 置 3、`savedGlobalIntrMask` 置 cfx3 的复位掩码（全 1），故
026 前的实现会把 `cfx3 cg8 rc1` 写成全 1（ISS-472 报告的“写旧值/0”同源）。
探针同时观测 `cfx0`（另一 monitor），把“改写限于帧 monitor”也钉住。

探针形态（复用 `tools/testcases/arch/node_probe_prelude.py` 的 Vast ROM 装配）：

  1. hmon（cfx3/hypv）把 `cfx3 cg8 rc1`（帧 monitor）与 `cfx0 cg8 rc1`（另一
     monitor）写成非复位的已知图案，并读回确认写入生效（否则 0xE3）；
  2. 安装 hmon 的 hypv 异常向量，执行非法目标的 `escape cfx0, 0` ⇒ 当前 cfx
     （hmon）的 `CFXESC`，这是**同步异常帧**（非 `trap`）；
  3. 向量里的 handler 对"进入次数"计数后 `escape cfx3, 1` 返回 `cause_ip + 4`；
  4. 回到 hmon 后读两个 `cg8 rc1` 与第 1 步的图案比较。

报告（`rd9` 计数 + SYS_EXIT 码）：`0` 通过；`0xE1` 帧 monitor 掩码被改写；
`0xE2` 同步异常进入次数 ≠ 1；`0xE3` 初始写入未生效；`0xE4` 另一 monitor 被改写。

`--selfcheck` 额外构建一个**负控** ROM（handler 自己把 `cfx3` 掩码改掉），要求
本平台返回 `0xE1`——证明第 4 步的比较不是恒真。该负控不改引擎源码。

用法：
  check_node_escape_intr.py [--platforms gem5,qemu] [--gem5 PATH]
      [--gem5-config PATH] [--qemu PATH] [--work-dir DIR] [--timeout N]
      [--selfcheck] [--selfcheck-only]

退出码：0 全部通过；1 判据失败；2 用法/缺件/配置错误。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]

for _sub in (("tools", "testcases", "lib"), ("tools", "testcases", "arch"),
             ("tools", "infra")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)

import node_probe_prelude as P  # noqa: E402

GEM5_DEFAULT = _REPO / ".work/source/gem5/build/DADAO/gem5.opt"
GEM5_CONFIG_DEFAULT = _REPO / ".work/source/gem5/configs/dadao/fs.py"
SHIM = _REPO / "tools/testcases/parity/qemu_gem5_shim.py"
WORK_DEFAULT = _REPO / ".dadao/tests/arch/probes/node_escape_intr"

# 非复位的已知图案：bit15=TIMER、bit32=PMEM_DMA，另加 1/2 区分两个 monitor；
# 与复位值 (0xFFFFFFFFFFFFFFF7)、0、全 1 都不同（掩码是普通 RW）。
PATTERN_FRAME = (1 << 15) | (1 << 32) | 0x1
PATTERN_OTHER = (1 << 15) | (1 << 32) | 0x2

HANDLER_OFF = 0x400          # body-relative; body must end before this
HANDLER_ADDR = P.ROM_BASE + HANDLER_OFF

RC_OK = 0
RC_MASK_CHANGED = 0xE1
RC_NO_SYNC_ENTRY = 0xE2
RC_SEED_FAILED = 0xE3
RC_OTHER_CHANGED = 0xE4


def _body(negative_control: bool):
    """Return (rom, expected_rc) for the real probe or its negative control."""
    seq = P.Seq()

    # 1. Seed the frame monitor (cfx3) and another monitor (cfx0); prove both
    #    writes landed, otherwise the post-escape comparison means nothing.
    seq.e(*P.load_rd(6, PATTERN_FRAME))
    seq.e(P.cfx2rc(3, 8, 1, 6))
    seq.e(P.cfx2rd(3, 8, 1, 7))
    seq.e(*P.load_rd(8, PATTERN_FRAME))
    seq.b("ne", 7, "fail_seed", 8)
    seq.e(*P.load_rd(6, PATTERN_OTHER))
    seq.e(P.cfx2rc(0, 8, 1, 6))
    seq.e(P.cfx2rd(0, 8, 1, 7))
    seq.e(*P.load_rd(8, PATTERN_OTHER))
    seq.b("ne", 7, "fail_seed", 8)

    # 2. hmon's own hypv vector, then a synchronous exception (CFXESC) into it.
    seq.e(*P.load_rd(22, HANDLER_ADDR))
    seq.e(P.cfx2rc(3, 3, 10, 22))
    seq.e(*P.load_rd(9, 0))
    seq.e(P.escape(0, 0))          # cfx0 != current cfx 3 => CFXESC -> hmon

    # 3. handler returns here (cause_ip + 4); compare both masks with the seed.
    seq.e(P.cfx2rd(3, 8, 1, 7))
    seq.e(*P.load_rd(8, 1))
    seq.b("ne", 9, "fail_entry", 8)
    seq.e(*P.load_rd(8, PATTERN_FRAME))
    seq.b("ne", 7, "fail_mask", 8)
    seq.e(P.cfx2rd(0, 8, 1, 7))
    seq.e(*P.load_rd(8, PATTERN_OTHER))
    seq.b("ne", 7, "fail_other", 8)
    seq.e(*P.exit_seq(RC_OK))
    seq.e(P.jump_rel(0))

    for name, code in (("fail_seed", RC_SEED_FAILED),
                       ("fail_entry", RC_NO_SYNC_ENTRY),
                       ("fail_mask", RC_MASK_CHANGED),
                       ("fail_other", RC_OTHER_CHANGED)):
        seq.mark(name)
        seq.e(*P.exit_seq(code))
        seq.e(P.jump_rel(0))
    prog = seq.resolve()

    handler = []
    # Count synchronous entries instead of only flagging one: a nested/denied
    # access after the escape would enter again and make the final check 0xE2
    # instead of comparing a stale rd7 (no false pass).
    handler += [P.add_si(9, 1)]
    if negative_control:
        # Negative control: the handler itself rewrites the frame monitor's
        # mask, so the post-escape comparison must report 0xE1.
        handler += P.load_rd(10, 0)
        handler += [P.cfx2rc(3, 8, 1, 10)]
    handler += [P.escape(3, 1)]                   # return to cause_ip + 4
    handler += [P.jump_rel(0)]

    rom = P.build_rom(prog, handlers={HANDLER_OFF: handler})
    return rom, RC_OK


def _write_rom(rom: bytes, work: Path) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    path = work / "rom.bin"
    path.write_bytes(rom)
    return path


def run_qemu(rom: bytes, work: Path, qemu: str, timeout: int):
    rc, log = P.run(rom, str(work), qemu=qemu, timeout=timeout, dump=False)
    return rc, log


def run_gem5(rom: bytes, work: Path, gem5: Path, config: Path, timeout: int):
    romp = _write_rom(rom, work)
    outdir = work / "gem5-out"
    outdir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PARITY_GEM5"] = str(gem5)
    env["PARITY_GEM5_CONFIG"] = str(config)
    env["PARITY_GEM5_PROFILE"] = "vast"
    env["PARITY_WORK_ROOT"] = str(outdir)
    cmd = [sys.executable, str(SHIM),
           "-machine", "kaiwu-vast,bootrom-image=%s" % romp,
           "-nographic", "-semihosting-config", "enable=on,target=native"]
    try:
        res = subprocess.run(cmd, cwd=str(_REPO), env=env, timeout=timeout,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True)
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    log = (res.stdout or "") + (res.stderr or "")
    if res.returncode < 0:
        return None, "signal %d\n%s" % (-res.returncode, log)
    return res.returncode & 0xFF, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platforms", default="gem5,qemu")
    ap.add_argument("--gem5", default=str(GEM5_DEFAULT))
    ap.add_argument("--gem5-config", default=str(GEM5_CONFIG_DEFAULT))
    ap.add_argument("--qemu", default=str(P.default_qemu()))
    ap.add_argument("--work-dir", default=str(WORK_DEFAULT))
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--selfcheck", action="store_true",
                    help="also run the negative-control ROM (expects 0xE1)")
    ap.add_argument("--selfcheck-only", action="store_true",
                    help="only run the negative control")
    args = ap.parse_args()

    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    if not platforms:
        print("[FAIL] --platforms is empty")
        return 2
    for p in platforms:
        if p not in ("gem5", "qemu"):
            print("[FAIL] unsupported platform %r" % p)
            return 2

    gem5 = Path(args.gem5)
    config = Path(args.gem5_config)
    qemu = args.qemu
    if "gem5" in platforms:
        for path, what in ((gem5, "gem5.opt"), (config, "fs.py"), (SHIM, "shim")):
            if not Path(path).is_file():
                print("[FAIL] missing %s: %s" % (what, path))
                return 2
    if "qemu" in platforms and not os.path.isfile(qemu):
        print("[FAIL] missing qemu: %s" % qemu)
        return 2

    work = Path(args.work_dir)
    failures = 0
    checks = 0

    def report(name, expected, actual, detail=""):
        nonlocal failures, checks
        checks += 1
        ok = expected == actual
        if not ok:
            failures += 1
        print("[%s] %s: expected=%s actual=%s%s"
              % ("PASS" if ok else "FAIL", name, expected, actual,
                 (" (%s)" % detail) if detail else ""))
        return ok

    def run_platforms(rom, tag, expect):
        if "gem5" in platforms:
            rc, log = run_gem5(rom, work / (tag + "-gem5"), gem5, config,
                               args.timeout)
            report("%s/gem5 exit" % tag, expect, rc,
                   "" if rc == expect else log[-600:].replace("\n", " | "))
        if "qemu" in platforms:
            rc, log = run_qemu(rom, work / (tag + "-qemu"), qemu,
                               args.timeout)
            report("%s/qemu exit" % tag, expect, rc,
                   "" if rc == expect else (log or "")[-600:].replace("\n", " | "))

    if not args.selfcheck_only:
        rom, expect = _body(negative_control=False)
        run_platforms(rom, "sync-escape", expect)

    if args.selfcheck or args.selfcheck_only:
        neg, _ = _body(negative_control=True)
        run_platforms(neg, "negative-control", RC_MASK_CHANGED)

    print("SUMMARY checks=%d failures=%d" % (checks, failures))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
