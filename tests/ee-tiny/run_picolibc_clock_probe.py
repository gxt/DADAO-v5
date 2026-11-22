#!/usr/bin/env python3
"""run_picolibc_clock_probe.py — picolibc ``clock()`` 一致性探针（m16-testcases-011）。

背景
----
``tests/ee-tiny/picolibc_clock_probe.c`` 只验证 picolibc 的时间口径：同一段
忙等里 ``clock()/CLOCKS_PER_SEC`` 与 ``gettimeofday()`` 的秒数必须一致
（ADR-0058 D5 ①）。picolibc 的 ``clock()`` 经 ``times()`` 返回 ``SYS_ELAPSED``
的 tick；``times()`` 自 ``m15-infra-010`` 起按
``sys_semihost_tickfreq()/CLOCKS_PER_SEC`` 缩放（ISS-502 已闭合），所以二者
一致。修前 ``clock()`` 曾大 1000×（当时基线 raw≈94.7 s vs wall≈0.095 s，仅作
历史对照，不作断言）。

本探针与 ansibench 四件**无依赖**（``m16-testcases-011`` 归位前它被塞在
``run_ansibench_tiny.py`` 的 ``probe`` 子用例里）：ansibench 驱动的计时数字只
记录不断言，本驱动才是 clock() 口径的唯一判定方。

链接契约（与 picolibc 自测/ansibench 四件同一条）
-----------------------------------------------
    安装版 ``lib/picolibc_noflash.ld``
  + ``tests/ee-tiny/crt0_tiny_picolibc.S``（栈桩：Tiny ``-kernel`` 路径不设 rb1）
  + ``lib/crt0-semihost.o``（``--redefine-sym _start=_picolibc_start``）
  + 探针目标文件
  + ``libc.a`` / ``libm.a`` / ``libsemihost.a`` / compiler-rt builtins

``crt0_tiny_picolibc.S`` 必须排在 ld.lld 输入第一个（``.text.start`` 决定
e_entry = Tiny 固定应用入口）。

判定（fail-closed）
------------------
* guest ``exit 0``；
* 结果行 ``probe clock=<s> wall=<s> rel=<r>`` 命中；
* ``wall >= PROBE_MIN_WALL``（忙等太短时比较没有意义，gettimeofday 分辨率有限）；
* ``|rel| <= PROBE_TOLERANCE``（5%，用户 2026-11-22 要求）。

退出码：0 = PASS；1 = FAIL；2 = 环境/参数错误（含自检未按预期翻红）。
``--inject`` 把容差改坏后重新判定：注入后的判定**必须**为 FAIL，因此该模式
**以 rc=1 结束**（与真实 FAIL 同一条路径）；若改坏后仍 PASS，说明比较不是活的，
rc=2 并点名原因。

本驱动不启用 ``writer_guard``：任务书要求退出码只有 0/1/2，而读守卫的拒绝码是
75（``ISS-373``）。探针只读安装根，单次 < 2 min。
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# `tests/ee-tiny/run_picolibc_clock_probe.py` ⇒ 仓库根在 2 层之上。
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "infra"))
import paths  # noqa: E402
sys.path.insert(0, str(_REPO_ROOT / "tools" / "testcases" / "lib"))
import machine_profile  # noqa: E402
import run_qemu_test  # noqa: E402

REPO_ROOT = paths.repo_root()
TOOLCHAIN_BIN = paths.host_toolchain_bin()
SYSROOT = paths.target_sysroot_dir()
PROBE_SRC = REPO_ROOT / "tests" / "ee-tiny" / "picolibc_clock_probe.c"
CRT0_STUB = REPO_ROOT / "tests" / "ee-tiny" / "crt0_tiny_picolibc.S"
PICOLIBC_LDS = SYSROOT / "lib" / "picolibc_noflash.ld"
TINY_BOOTROM = paths.test_artifacts_dir() / "bootrom" / "tiny" / "bootrom_tiny.bin"

CLANG = TOOLCHAIN_BIN / "clang"
LLD = TOOLCHAIN_BIN / "ld.lld"
LLVM_MC = TOOLCHAIN_BIN / "llvm-mc"
LLVM_OBJCOPY = TOOLCHAIN_BIN / "llvm-objcopy"
LLVM_NM = TOOLCHAIN_BIN / "llvm-nm"
LLVM_SIZE = TOOLCHAIN_BIN / "llvm-size"
QEMU = TOOLCHAIN_BIN / "qemu-system-dadao"

DEFAULT_TIMEOUT = 120
DEFAULT_WORK_DIR = REPO_ROOT / ".work" / "build" / "picolibc-clock-probe"
#: 一致性容差（用户 2026-11-22 要求：5%）。
PROBE_TOLERANCE = 0.05
#: 最短忙等（秒）：低于它比较没有意义（gettimeofday 分辨率有限）。
PROBE_MIN_WALL = 0.05
#: 注入用容差：负值 ⇒ 任何 |rel| >= 0 都超限，必然翻红。
INJECT_TOLERANCE = -1.0

RESULT_RE = re.compile(
    r"probe clock=([-0-9.]+) wall=([-0-9.]+) rel=([-+0-9.]+)")

BASE_CFLAGS = ("-target", "dadao-unknown-elf", "-O2", "-std=gnu99",
               "-fno-builtin")


def run(cmd, timeout=None):
    """Run ``cmd``; return ``(rc, combined output, timed_out)``.

    The child's own exit code is captured directly (no shell pipe can swallow
    it).  ``rc`` is ``None`` on timeout.
    """
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        out = exc.output or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return None, out, True
    return res.returncode, res.stdout, False


def _require(path: Path, what: str) -> None:
    if not path.exists():
        sys.stderr.write("picolibc-clock-probe: ERROR: %s 不存在：%s\n"
                         "                         先跑 'make install-host' / "
                         "'make build-picolibc' / 'make build-bootrom'\n"
                         % (what, path))
        raise SystemExit(2)


def builtins_archive() -> Path:
    """compiler-rt builtins 归档（由驱动自己报路径，不猜 resource-dir）。"""
    rc, out, _ = run([str(CLANG), "-target", "dadao-unknown-elf",
                      "-rtlib=compiler-rt", "-print-libgcc-file-name"])
    lines = (out or "").strip().splitlines()
    path = Path(lines[0]) if rc == 0 and lines else None
    if path is None or not path.is_file():
        sys.stderr.write("picolibc-clock-probe: ERROR: compiler-rt builtins "
                         "归档找不到（驱动报 %r）；先跑 'make install-host'\n"
                         % (path,))
        raise SystemExit(2)
    return path


def build_prelude(out_dir: Path) -> list[Path]:
    """栈桩 + 改名的 picolibc crt0（每次运行重建，随源码变化）。"""
    stub = out_dir / "crt0_tiny_picolibc.o"
    rc, out, _ = run([str(LLVM_MC), "--triple=dadao-unknown-elf",
                      "-filetype=obj", "-I", str(REPO_ROOT),
                      str(CRT0_STUB), "-o", str(stub)])
    if rc != 0:
        sys.stderr.write("picolibc-clock-probe: ERROR: 汇编 %s 失败 rc=%s\n%s\n"
                         % (CRT0_STUB.name, rc, out))
        raise SystemExit(2)
    crt = out_dir / "crt0-semihost-renamed.o"
    rc, out, _ = run([str(LLVM_OBJCOPY), "--redefine-sym",
                      "_start=_picolibc_start",
                      str(SYSROOT / "lib" / "crt0-semihost.o"), str(crt)])
    if rc != 0:
        sys.stderr.write("picolibc-clock-probe: ERROR: 改名 crt0-semihost.o "
                         "失败 rc=%s\n%s\n" % (rc, out))
        raise SystemExit(2)
    return [stub, crt]


def build_probe(work: Path, prelude: list[Path]) -> Path:
    """编译 + 链接探针；返回 ELF（失败 ⇒ rc=2，构建错误不是判定失败）。"""
    d = work / "probe"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    obj = d / "probe.o"
    rc, out, timed = run([str(CLANG), *BASE_CFLAGS, "-c", str(PROBE_SRC),
                          "-o", str(obj)])
    if timed or rc != 0:
        sys.stderr.write("picolibc-clock-probe: ERROR: 编译探针失败 rc=%s\n%s\n"
                         % (rc, out[-2000:]))
        raise SystemExit(2)
    elf = d / "probe.elf"
    cmd = [str(LLD), "-L", str(SYSROOT / "lib"), "-T", str(PICOLIBC_LDS),
           *map(str, prelude), str(obj),
           str(SYSROOT / "lib" / "libc.a"),
           str(SYSROOT / "lib" / "libm.a"),
           str(SYSROOT / "lib" / "libsemihost.a"),
           str(builtins_archive()), "-o", str(elf)]
    rc, out, timed = run(cmd)
    if timed or rc != 0:
        sys.stderr.write("picolibc-clock-probe: ERROR: 链接探针失败 rc=%s\n%s\n"
                         % (rc, out[-2000:]))
        raise SystemExit(2)
    return elf


def run_qemu(elf: Path, timeout: int):
    # argv[0] 即 guest 的 program name（探针不读 argv，传一个标识即可）。
    cfg = "enable=on,target=native,arg=probe"
    return run([str(QEMU), "-machine",
                "kaiwu-tiny,bootrom-image=" + str(TINY_BOOTROM),
                "-kernel", str(elf), "-semihosting-config", cfg,
                "-display", "none", "-nographic", "-monitor", "none"],
               timeout=timeout)


def elf_size(elf: Path) -> int | None:
    """``text + data + bss``（只记录，不作判据）。"""
    rc, out, _ = run([str(LLVM_SIZE), str(elf)])
    if rc != 0:
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and all(p.isdigit() for p in parts[:3]):
            return sum(int(p) for p in parts[:3])
    return None


def elf_symbols(elf: Path) -> list[str]:
    """最终 ELF 定义的全局符号（只记录 ``clock``/``gettimeofday`` 是否被拉起）。"""
    rc, out, _ = run([str(LLVM_NM), "--defined-only", "--extern-only", str(elf)])
    if rc != 0:
        return []
    defined = {line.split()[-1] for line in out.splitlines() if line.split()}
    return [s for s in ("clock", "times", "gettimeofday", "printf")
            if s in defined]


def judge(rc, out: str, tolerance: float = PROBE_TOLERANCE,
          min_wall: float = PROBE_MIN_WALL) -> tuple[str, list[str], list[str]]:
    """判定唯一真源（``--inject`` 走同一函数，只换容差）。

    Returns ``(status, reasons, evidence)``.
    """
    reasons: list[str] = []
    evidence: list[str] = []
    if rc is None:
        return "TIMEOUT", ["主机超时：guest 没给出退出码"], evidence
    if rc != 0:
        why = run_qemu_test.fault_name(rc) if rc > 0 else "signal %d" % -rc
        reasons.append("guest exit %s (%s)" % (rc, why))
    m = RESULT_RE.search(out)
    if m is None:
        reasons.append("结果行未命中（probe clock=… wall=… rel=…）：%r"
                       % out[-300:])
        return "FAIL", reasons, evidence
    _clk, wall, rel = (float(v) for v in m.groups())
    # clock 秒数已随结果行进 evidence；判定只用 wall（最短忙等）与 rel（相对差）。
    evidence.append(m.group(0).strip())
    if wall < min_wall:
        reasons.append("忙等太短（%.6fs < %.2fs），比较无意义"
                       % (wall, min_wall))
    if abs(rel) > tolerance:
        reasons.append("clock()/CLOCKS_PER_SEC 与 gettimeofday 差 %+.2f%% > "
                       "%.0f%%" % (rel * 100.0, tolerance * 100.0))
    return ("FAIL" if reasons else "PASS"), reasons, evidence


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile",
                    default=os.environ.get("DADAO_TEST_PROFILE") or "tiny",
                    choices=sorted(machine_profile.all_profiles()),
                    help="机器 profile（本驱动只支持 tiny）")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help="主机超时（秒，默认 %d）" % DEFAULT_TIMEOUT)
    ap.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR))
    ap.add_argument("--inject", action="store_true",
                    help="反例自检：把容差改坏后重新判定，必须 FAIL（期望 rc=1）")
    args = ap.parse_args()

    prof = machine_profile.load(args.profile)
    if prof.name != "tiny":
        sys.stderr.write("picolibc-clock-probe: ERROR: 探针只跑 Tiny"
                         "（profile=%r）\n" % prof.name)
        return 2
    if not machine_profile.suite_enabled(prof, "unit/picolibc"):
        sys.stderr.write("picolibc-clock-probe: ERROR: profile %r 不跑 picolibc"
                         "（contracts/tests-matrix.yaml）\n" % prof.name)
        return 2

    for path, what in ((CLANG, "clang"), (LLD, "ld.lld"),
                       (LLVM_MC, "llvm-mc"), (LLVM_OBJCOPY, "llvm-objcopy"),
                       (LLVM_NM, "llvm-nm"), (LLVM_SIZE, "llvm-size"),
                       (QEMU, "qemu-system-dadao"), (TINY_BOOTROM, "Tiny BootROM"),
                       (SYSROOT / "lib" / "libc.a", "picolibc libc.a"),
                       (SYSROOT / "lib" / "libsemihost.a",
                        "picolibc libsemihost.a"),
                       (PICOLIBC_LDS, "picolibc_noflash.ld")):
        _require(path, what)

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    prelude = build_prelude(work)
    elf = build_probe(work, prelude)

    sys.stdout.write("picolibc-clock-probe: crt0=%s；lds=%s\n"
                     % (CRT0_STUB.name, PICOLIBC_LDS.name))
    t0 = time.monotonic()
    rc, out, _ = run_qemu(elf, args.timeout)
    wall_host = time.monotonic() - t0

    status, reasons, evidence = judge(rc, out)
    size = elf_size(elf)
    sys.stdout.write("  probe     %-7s exit=%-4s wall=%6.1fs size=%s\n"
                     % (status, "-" if rc is None else rc, wall_host,
                        "-" if size is None else size))
    for line in evidence:
        sys.stdout.write("            [out] %s\n" % line)
    symbols = elf_symbols(elf)
    if symbols:
        sys.stdout.write("            [record] 已链接符号: %s\n"
                         % ", ".join(symbols))
    for reason in reasons:
        for i, line in enumerate(reason.splitlines()):
            sys.stdout.write("            [%s] %s\n"
                             % ("why" if i == 0 else "   ", line))
    sys.stdout.flush()

    if args.inject:
        # 反例：容差改成负值 ⇒ 任何 |rel| 都超限，判定必须翻红。
        # 基线本身没 PASS 时注入无意义（改坏后必然 FAIL 证明不了任何事）。
        if status != "PASS":
            sys.stderr.write("INJECT: 基线判定 %s，注入无意义（先让探针 PASS）\n"
                             % status)
            return 2
        injected, inj_reasons, _ = judge(rc, out, tolerance=INJECT_TOLERANCE)
        sys.stdout.write("INJECT: 容差 %.2f -> %.2f\n"
                         % (PROBE_TOLERANCE, INJECT_TOLERANCE))
        if injected == "FAIL":
            sys.stdout.write("INJECT: 注入后判定为 FAIL（%s）—— 断言是活的；"
                             "该模式期望 rc=1\n" % inj_reasons[0])
            return 1
        sys.stderr.write("INJECT: 未按预期翻红（判定仍 %s）—— 比较不是活的\n"
                         % injected)
        return 2

    if status != "PASS":
        sys.stdout.write("picolibc-clock-probe: FAIL\n")
        return 1
    sys.stdout.write("picolibc-clock-probe: PASS（|rel| ≤ %.0f%%）\n"
                     % (PROBE_TOLERANCE * 100.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
