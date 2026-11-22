#!/usr/bin/env python3
"""run_ansibench_tiny.py — ansibench 四件在 Kaiwu-Tiny 上的 picolibc 实际应用验证
（m15-testcases-023）。

背景
----
picolibc 此前只有自测/冒烟，没有真实应用跑通。embench 不再拆
freestanding/picolibc 两套，改用 ansibench 语料里「text+data+bss < 64 KiB
（Tiny 装载窗口 image_window）」的四个基准作为 picolibc 的实际应用验证：

    coremark   dhrystone   linpack   whetstone

范围外的 ansibench 件（不是懒加载，是结构不适用）：``stream``（默认数组 bss
809 KB）、``hint``（fopen 文件）、``nbench``（popen/pipe）、``tripforce``
（OpenSSL）。

链接契约（与 picolibc 自测驱动同一条）
-------------------------------------
    安装版 ``lib/picolibc_noflash.ld``
  + ``tests/ee-tiny/crt0_tiny_picolibc.S``（栈桩：Tiny ``-kernel`` 路径不设 rb1）
  + ``lib/crt0-semihost.o``（``--redefine-sym _start=_picolibc_start``）
  + 语料目标文件
  + ``libc.a`` / ``libm.a`` / ``libsemihost.a`` / compiler-rt builtins

``crt0_tiny_picolibc.S`` 必须排在 ld.lld 输入的第一个（它的 ``.text.start``
决定 e_entry = Tiny 固定应用入口）；``-Map`` 不需要。

判定（fail-closed，逐件）
-------------------------
* guest ``exit 0``；
* 关键输出行 **逐条** 命中（CoreMark ``Correct operation validated.``、
  其余件的结果行 / 浮点结果行以正则断言）；
* 由 picolibc 归档实际拉起的 **能力符号** 都在最终 ELF 里被定义
  （printf / malloc / free / clock / times / libm 数学函数 …）：归档成员只有
  被引用才会被拉入，所以「符号已定义」= 该能力真的被这条链接用到；
* ``text+data+bss <= 65536``（Tiny ``image_window``，来自
  ``tests/ee-tiny/runtime.yaml``；上限现场从 machine_profile 读取）；
* 计时数字 **只记录**，从不断言（见下）。

clock() 口径（ADR-0058 D5；ISS-502 已由 m15-infra-010 闭合）
-----------------------------------------------------------------
picolibc 的 ``clock()`` 经 ``times()`` 返回 SYS_ELAPSED 的 tick；``times()``
现在按 ``sys_semihost_tickfreq()/CLOCKS_PER_SEC`` 缩放（m15-infra-010），所以
``clock()/CLOCKS_PER_SEC`` 与 ``gettimeofday`` 一致。修前它曾大 1000×
（ISS-502；当时基线日志 raw≈94.7 s vs wall≈0.095 s，仅作历史对照，不作断言）。

* clock() 一致性的**判定**由 picolibc 驱动
  ``tests/ee-tiny/run_picolibc_clock_probe.py`` 承担（同一段忙等里比较
  ``clock()/CLOCKS_PER_SEC`` 与 ``gettimeofday``，要求 ≤5%，D5 ①）。本驱动
  不做该比较（``m16-testcases-011``：探针与 ansibench 四件无依赖）；
* 基准自身依赖 clock() 的输出（CoreMark iterations/sec、Dhrystone 速率、
  Linpack 的 Time(s)/KFLOPS、Whetstone Duration）**只记录、不断言**；
* 本驱动不再用任何 clock() shim：linpack 的 ``while (linpack() < 10.)``
  按真实秒自停（修后语义正确）。

缓存（ISS-504 提醒）：本驱动 **不落地判定缓存**——每次运行都 ``rm -rf``
单件的对象目录、重新编译/链接/执行，判定只用本次进程内的输出；所以没有
``.done`` 之类的复用键，也不受 picolibc 库指纹变化影响。

退出码：0 = 四件全 PASS；1 = 有 FAIL；2 = 环境/参数错误。
``--inject`` 把一条期望改坏后重新判定（必须 FAIL），用于证明比较是活的。

参数按 Tiny 缩小（单件 < 2 min；耗时不设阈值，只记录）：coremark 迭代 300
（语料自校验要求 >=10 s，100 迭代只有 ~5.4 s 会报 invalid）、dhrystone runs
100000、linpack N 100、whetstone n 20000（200000 实测 101 s）。
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# `tests/ee-tiny/run_ansibench_tiny.py` ⇒ 仓库根在 2 层之上。
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "infra"))
import paths  # noqa: E402
import writer_guard  # noqa: E402
sys.path.insert(0, str(_REPO_ROOT / "tools" / "testcases" / "lib"))
import machine_profile  # noqa: E402
import run_qemu_test  # noqa: E402

REPO_ROOT = paths.repo_root()
TOOLCHAIN_BIN = paths.host_toolchain_bin()
SYSROOT = paths.target_sysroot_dir()
ANSIBENCH_SRC = REPO_ROOT / ".work" / "source" / "ansibench"
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

DEFAULT_TIMEOUT = 300
DEFAULT_WORK_DIR = REPO_ROOT / ".work" / "build" / "ansibench-tiny"

BASE_CFLAGS = ("-target", "dadao-unknown-elf", "-O2", "-std=gnu99",
               "-fno-builtin")


@dataclass(frozen=True)
class Case:
    """一件 ansibench 基准：构建输入 + 判据。

    ``expect`` 是必须逐条命中 stdout 的字面行；``patterns`` 是需要正则命中的
    结果行（浮点/数值，只要求格式，不锁定数值）；``symbols`` 是必须被链接进
    最终 ELF 的 picolibc 能力符号；``records`` 是只记录不断言的计时行。
    """

    name: str
    sources: tuple[str, ...]
    includes: tuple[str, ...]
    defines: tuple[str, ...]
    argv: tuple[str, ...]
    expect: tuple[str, ...]
    patterns: tuple[tuple[str, str], ...]
    symbols: tuple[str, ...]
    caps: str
    records: tuple[str, ...] = ()


CASES = (
    Case(
        name="coremark",
        sources=tuple("coremark/src/%s.c" % s for s in (
            "core_main", "core_matrix", "core_list_join", "core_state",
            "core_util", "core_portme")),
        includes=("coremark/include",),
        defines=('-DUINTPTR_TYPE',
                 '-DFLAGS_STR="-O2 picolibc Tiny"',
                 '-DMEM_LOCATION="Main memory (heap)"'),
        argv=("coremark", "0x0", "0x0", "0x66", "300", "7", "1", "2000"),
        expect=("2K performance run parameters for coremark.",
                "Correct operation validated.",
                "CoreMark 1.0 :"),
        patterns=(("float printf (Total time (secs), %f)",
                   r"Total time \(secs\): \d+\.\d{6}"),),
        symbols=("printf", "malloc", "free", "clock", "times"),
        caps="printf(%f) malloc free clock",
        records=(r"Total time \(secs\): .*",
                 r"Iterations/Sec   : .*"),
    ),
    Case(
        name="dhrystone",
        sources=("dhrystone/src/dhry_1.c", "dhrystone/src/dhry_2.c"),
        includes=("dhrystone/include",),
        defines=("-DMSC_CLOCK",),
        argv=("dhrystone", "100000"),
        expect=("Dhrystone Benchmark, Version 2.1 (Language: C)",
                "Execution ends",
                "should be:   DHRYSTONE PROGRAM, 2'ND STRING",
                "Dhrystones per Second:",
                "Microseconds for one run through Dhrystone:"),
        patterns=(("float printf (Dhrystones per Second, %.1f)",
                   r"Dhrystones per Second:\s+\d+\.\d"),),
        symbols=("printf", "malloc", "free", "clock", "times"),
        caps="printf(%f) malloc free clock",
        records=(r"Microseconds for one run through Dhrystone:.*",
                 r"Dhrystones per Second:.*"),
    ),
    Case(
        name="linpack",
        sources=("linpack/src/linpack.c",),
        includes=(),
        defines=(),
        argv=("linpack", "100"),
        expect=("LINPACK benchmark, Double precision.",
                "Array size 100 X 100.",
                "Average rolled and unrolled performance:"),
        patterns=(("linpack result row (Reps/Time/KFLOPS)",
                   r"(?m)^\s*\d+\s+\d+\.\d\d\s+\d+\.\d\d%.*\d+\.\d{3}$"),),
        symbols=("printf", "malloc", "free", "fabs", "clock"),
        caps="printf(%f) malloc free fabs clock",
        records=(r"(?m)^\s*\d+\s+\d+\.\d\d\s+.*$",),
    ),
    Case(
        name="whetstone",
        sources=("whetstone/src/whetstone.c",),
        includes=(),
        defines=(),
        argv=("whetstone", "20000"),
        expect=("Loops: 20000, Iterations: 1, Duration:",
                "C Converted Double Precision Whetstones:"),
        patterns=(("float printf (Whetstone KIPS/MWIPS, %.1f)",
                   r"C Converted Double Precision Whetstones: \d+\.\d [MK]WIPS"),),
        symbols=("printf", "sin", "cos", "atan", "log", "exp", "sqrt",
                 "time"),
        caps="printf(%f) libm(sin/cos/atan/log/exp/sqrt) time()",
        records=(r"Loops: .*", r"C Converted Double Precision Whetstones: .*"),
    ),
)


@dataclass
class Result:
    name: str
    status: str = "ERROR"          # PASS / FAIL / TIMEOUT / ERROR
    rc: int | None = None
    wall: float = 0.0
    size: int | None = None
    reasons: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    records: list[str] = field(default_factory=list)
    caps: str = ""
    symbols: set[str] = field(default_factory=set)

    @property
    def ok(self) -> bool:
        return self.status == "PASS"


def run(cmd, timeout=None, env=None):
    """Run ``cmd``; return ``(rc, combined output, timed_out)``.

    The child's own exit code is captured directly (no shell pipe can swallow
    it).  ``rc`` is ``None`` on timeout.
    """
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        out = exc.output or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return None, out, True
    return res.returncode, res.stdout, False


def _require(path: Path, what: str) -> None:
    if not path.exists():
        sys.stderr.write("ansibench-tiny: ERROR: %s 不存在：%s\n"
                         "                先跑 'make install-host' / "
                         "'make build-picolibc' / 'make build-bootrom'\n"
                         % (what, path))
        raise SystemExit(2)


def builtins_archive() -> Path:
    """compiler-rt builtins 归档（由驱动自己报路径，不猜 resource-dir）。"""
    res = run([str(CLANG), "-target", "dadao-unknown-elf", "-rtlib=compiler-rt",
               "-print-libgcc-file-name"])
    lines = (res[1] or "").strip().splitlines()
    path = Path(lines[0]) if res[0] == 0 and lines else None
    if path is None or not path.is_file():
        sys.stderr.write("ansibench-tiny: ERROR: compiler-rt builtins 归档找不到"
                         "（驱动报 %r）；先跑 'make install-host'\n" % (path,))
        raise SystemExit(2)
    return path


def build_prelude(out_dir: Path) -> list[Path]:
    """栈桩 + 改名的 picolibc crt0（每次运行重建，随源码变化）。"""
    stub = out_dir / "crt0_tiny_picolibc.o"
    rc, out, _ = run([str(LLVM_MC), "--triple=dadao-unknown-elf",
                      "-filetype=obj", "-I", str(REPO_ROOT),
                      str(CRT0_STUB), "-o", str(stub)])
    if rc != 0:
        sys.stderr.write("ansibench-tiny: ERROR: 汇编 %s 失败 rc=%s\n%s\n"
                         % (CRT0_STUB.name, rc, out))
        raise SystemExit(2)
    crt = out_dir / "crt0-semihost-renamed.o"
    rc, out, _ = run([str(LLVM_OBJCOPY), "--redefine-sym",
                      "_start=_picolibc_start",
                      str(SYSROOT / "lib" / "crt0-semihost.o"), str(crt)])
    if rc != 0:
        sys.stderr.write("ansibench-tiny: ERROR: 改名 crt0-semihost.o 失败 "
                         "rc=%s\n%s\n" % (rc, out))
        raise SystemExit(2)
    return [stub, crt]


def compile_case(case: Case, obj_dir: Path):
    """编译一件；返回 ``(objs, error_text)``。"""
    d = obj_dir / case.name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    incs = [x for rel in case.includes for x in ("-I", str(ANSIBENCH_SRC / rel))]
    objs = []
    for rel in case.sources:
        src = ANSIBENCH_SRC / rel
        obj = d / (src.stem + ".o")
        rc, out, timed = run([str(CLANG), *BASE_CFLAGS, *case.defines, *incs,
                              "-c", str(src), "-o", str(obj)])
        if timed or rc != 0:
            return None, "compile %s rc=%s\n%s" % (src.name, rc, out[-2000:])
        objs.append(obj)
    return objs, ""


def link_case(case: Case, objs: list[Path], prelude: list[Path],
              obj_dir: Path):
    """链接一件；返回 ``(elf, error_text)``。"""
    elf = obj_dir / case.name / (case.name + ".elf")
    cmd = [str(LLD), "-L", str(SYSROOT / "lib"),
           "-T", str(PICOLIBC_LDS), *map(str, prelude), *map(str, objs),
           str(SYSROOT / "lib" / "libc.a"),
           str(SYSROOT / "lib" / "libm.a"),
           str(SYSROOT / "lib" / "libsemihost.a"),
           str(builtins_archive()), "-o", str(elf)]
    rc, out, timed = run(cmd)
    if timed or rc != 0:
        return None, "link rc=%s\n%s" % (rc, out[-2000:])
    return elf, ""


def elf_size(elf: Path) -> int | None:
    """``text + data + bss``（Berkeley ``llvm-size`` 行的前三列）。"""
    rc, out, _ = run([str(LLVM_SIZE), str(elf)])
    if rc != 0:
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and all(p.isdigit() for p in parts[:3]):
            return sum(int(p) for p in parts[:3])
    return None


def elf_symbols(elf: Path) -> set[str]:
    """最终 ELF 定义的全局符号（= 归档里被真正拉起的成员）。"""
    rc, out, _ = run([str(LLVM_NM), "--defined-only", "--extern-only", str(elf)])
    if rc != 0:
        return set()
    return {line.split()[-1] for line in out.splitlines() if line.split()}


def image_window() -> int:
    """Tiny 装载窗口（``tests/ee-tiny/runtime.yaml`` 的 ``image_window``）。"""
    prof = machine_profile.load("tiny")
    return int(prof.get("image_window"))


def judge(case: Case, rc, out: str, symbols: set[str], size: int | None,
          window: int, expect_override=None) -> tuple[str, list[str], list[str]]:
    """单件判定（唯一真源，``--inject`` 走同一函数）。

    Returns ``(status, reasons, evidence)``.
    """
    expect = case.expect if expect_override is None else expect_override
    reasons: list[str] = []
    evidence: list[str] = []

    if rc is None:
        return "TIMEOUT", ["主机超时：guest 没给出退出码"], evidence
    if rc != 0:
        why = run_qemu_test.fault_name(rc) if rc > 0 else "signal %d" % -rc
        reasons.append("guest exit %s (%s)" % (rc, why))
    for line in expect:
        if line in out:
            evidence.append(line)
        else:
            reasons.append("缺关键输出行：%r" % line)
    for label, pat in case.patterns:
        m = re.search(pat, out)
        if m:
            evidence.append(m.group(0).strip())
        else:
            reasons.append("结果行未命中（%s）：/%s/" % (label, pat))
    missing = [s for s in case.symbols if s not in symbols]
    if missing:
        reasons.append("能力符号未链接进 ELF：%s" % ", ".join(missing))
    else:
        evidence.append("symbols: " + ", ".join(case.symbols))
    if size is None:
        reasons.append("llvm-size 读不到 text+data+bss")
    elif size > window:
        reasons.append("text+data+bss=%d 超出 Tiny 装载窗口 %d" % (size, window))
    return ("FAIL" if reasons else "PASS"), reasons, evidence


def record_lines(case: Case, out: str) -> list[str]:
    """只记录不断言的计时行（ADR-0058 D4：耗时数字不设阈值）。"""
    got = []
    for pat in case.records:
        found = re.findall(pat, out)
        if found:
            got.append(found[-1].strip())
    return got


def run_qemu(elf: Path, argv: tuple[str, ...], timeout: int):
    cfg = "enable=on,target=native" + "".join(",arg=" + a for a in argv)
    return run([str(QEMU), "-machine",
                "kaiwu-tiny,bootrom-image=" + str(TINY_BOOTROM),
                "-kernel", str(elf), "-semihosting-config", cfg,
                "-display", "none", "-nographic", "-monitor", "none"],
               timeout=timeout)


def run_case(case: Case, prelude: list[Path], obj_dir: Path,
             timeout: int) -> tuple[Result, str]:
    """构建 + 跑一件；返回 ``(Result, raw_output)``。"""
    res = Result(name=case.name, caps=case.caps)
    objs, err = compile_case(case, obj_dir)
    if objs is None:
        res.status = "FAIL"
        res.reasons.append(err)
        return res, ""
    elf, err = link_case(case, objs, prelude, obj_dir)
    if elf is None:
        res.status = "FAIL"
        res.reasons.append(err)
        return res, ""
    res.size = elf_size(elf)
    res.symbols = elf_symbols(elf)
    t0 = time.monotonic()
    rc, out, _ = run_qemu(elf, case.argv, timeout)
    res.wall = time.monotonic() - t0
    res.rc = rc
    res.status, res.reasons, res.evidence = judge(
        case, rc, out, res.symbols, res.size, image_window())
    res.records = record_lines(case, out)
    if res.status == "TIMEOUT":
        res.reasons = ["主机超时 %ds：guest 没给出退出码" % timeout]
    return res, out


def report(res: Result, window: int, stream=sys.stdout) -> None:
    head = ("  %-9s %-7s exit=%-4s wall=%6.1fs size=%s/%d"
            % (res.name, res.status,
               "-" if res.rc is None else res.rc, res.wall,
               "-" if res.size is None else res.size, window))
    stream.write(head + "\n")
    if res.caps:
        stream.write("            caps: %s\n" % res.caps)
    for line in res.evidence:
        stream.write("            [out] %s\n" % line)
    for line in res.records:
        stream.write("            [record] %s\n" % line)
    for reason in res.reasons:
        for i, line in enumerate(reason.splitlines()):
            stream.write("            [%s] %s\n"
                         % ("why" if i == 0 else "   ", line))
    stream.flush()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile",
                    default=os.environ.get("DADAO_TEST_PROFILE") or "tiny",
                    choices=sorted(machine_profile.all_profiles()),
                    help="机器 profile（本驱动只支持 tiny）")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help="单件主机超时（秒，默认 %d）" % DEFAULT_TIMEOUT)
    ap.add_argument("--only", default=None,
                    help="逗号分隔的子集（coremark,dhrystone,linpack,whetstone）")
    ap.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR))
    ap.add_argument("--inject", action="store_true",
                    help="反例自检：改坏一条期望后重新判定，必须 FAIL")
    writer_guard.add_arguments(ap)
    args = ap.parse_args()

    prof = machine_profile.load(args.profile)
    if prof.name != "tiny":
        sys.stderr.write("ansibench-tiny: ERROR: ansibench 四件只跑 Tiny"
                         "（profile=%r）\n" % prof.name)
        return 2
    if not machine_profile.suite_enabled(prof, "unit/picolibc"):
        sys.stderr.write("ansibench-tiny: ERROR: profile %r 不跑 picolibc"
                         "（contracts/tests-matrix.yaml）\n" % prof.name)
        return 2

    for path, what in ((CLANG, "clang"), (LLD, "ld.lld"),
                       (LLVM_MC, "llvm-mc"), (LLVM_OBJCOPY, "llvm-objcopy"),
                       (LLVM_NM, "llvm-nm"), (LLVM_SIZE, "llvm-size"),
                       (QEMU, "qemu-system-dadao"), (TINY_BOOTROM, "Tiny BootROM"),
                       (SYSROOT / "lib" / "libc.a", "picolibc libc.a"),
                       (SYSROOT / "lib" / "libsemihost.a", "picolibc libsemihost.a"),
                       (PICOLIBC_LDS, "picolibc_noflash.ld")):
        _require(path, what)
    if not ANSIBENCH_SRC.is_dir():
        sys.stderr.write("ansibench-tiny: ERROR: ansibench 语料不存在：%s\n"
                         "                先跑 'make fetch'（组件 ansibench）\n"
                         % ANSIBENCH_SRC)
        return 2

    selected = [c for c in CASES]
    if args.only:
        wanted = {x.strip() for x in args.only.split(",") if x.strip()}
        unknown = wanted - {c.name for c in CASES}
        if unknown:
            sys.stderr.write("ansibench-tiny: ERROR: --only 未知项：%s\n"
                             % ", ".join(sorted(unknown)))
            return 2
        selected = [c for c in CASES if c.name in wanted]

    guard = writer_guard.start_guard(
        args, [str(CLANG), str(LLD), str(LLVM_MC), str(LLVM_OBJCOPY),
               str(LLVM_NM), str(QEMU), str(TINY_BOOTROM),
               str(SYSROOT / "lib" / "libc.a"),
               str(SYSROOT / "lib" / "libm.a"),
               str(SYSROOT / "lib" / "libsemihost.a")], label="ansibench_tiny")

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    window = image_window()

    prelude = build_prelude(work)

    sys.stdout.write(
        "ansibench-tiny: Tiny 装载窗口 %d B；crt0=%s；lds=%s\n"
        % (window, CRT0_STUB.name, PICOLIBC_LDS.name))
    sys.stdout.write(
        "  clock() 一致性由 picolibc 驱动 run_picolibc_clock_probe.py 判定；"
        "基准计时只记录\n")
    sys.stdout.flush()

    results: list[Result] = []
    raw: dict[str, tuple] = {}
    for case in selected:
        res, out = run_case(case, prelude, work, args.timeout)
        report(res, window)
        results.append(res)
        raw[case.name] = (res.rc, out, res.symbols, res.size)

    passed = [r for r in results if r.ok]
    sys.stdout.write("\nansibench-tiny: %d/%d PASS (逐项现场统计)\n"
                     % (len(passed), len(results)))

    # ---- 内建反例自检（可达 FAIL 的活比较） -----------------------------
    if args.inject:
        target = next((r for r in results if r.ok), None)
        if target is None:
            sys.stderr.write("INJECT: FAIL —— 没有 PASS 的用例可注入\n")
            return 2
        case = next(c for c in CASES if c.name == target.name)
        rc, out, syms, size = raw[case.name]
        wrong = (case.expect[0] + " (injected-wrong)",) + case.expect[1:]
        status, reasons, _ = judge(case, rc, out, syms, size, window,
                                   expect_override=wrong)
        sys.stdout.write("INJECT: %s 首条期望 -> %r\n"
                         % (case.name, wrong[0]))
        if status == "FAIL":
            sys.stdout.write("INJECT: PASS —— 改坏期望后判定为 FAIL（%s）\n"
                             % reasons[0])
        else:
            sys.stderr.write("INJECT: FAIL —— 改坏期望后仍然 PASS，比较不是活的\n")
            return 1
        return 0 if writer_guard.finish_guard(guard) else 1

    guard_ok = writer_guard.finish_guard(guard)
    if not passed:
        sys.stdout.write("ansibench-tiny: FAIL\n")
        return 1
    if len(passed) != len(results):
        failed = ", ".join(r.name for r in results if not r.ok)
        sys.stdout.write("ansibench-tiny: FAIL（%s）\n" % failed)
        return 1
    if not guard_ok:
        return 1
    sys.stdout.write("ansibench-tiny: PASS\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
