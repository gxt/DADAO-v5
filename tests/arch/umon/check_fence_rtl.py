#!/usr/bin/env python3
"""`tests/arch/umon/check_fence_rtl.py` — fence 用例的 **RTL（chipyard
`WumingVastConfig`）承载**（`m16-testcases-012`，按需跑）。

为什么不在 `run_arch.py` 里：`common/platform.py` 的 chipyard 后端仍是
**fail-closed**（RTL 后端接入由 `m16-chipyard-018`/`check-arch-vast` 承担）；
本文件是同一用例的**按需第三方证据**：探针由 `gen_fence_rtl.py` 从
`umon_fence.py` 的**同一张探针表**生成，签名流与 QEMU/gem5 逐槽同源比对。

RTL 与 QEMU/gem5 的差异只有故障观察通道（固件 hmon：cause 在
`HMON_BASE + 0xE0`、回落点 `+0xF8`），见 `gen_fence_rtl.py` 文件头。

用法：
  check_fence_rtl.py --only arch-umon-012 [--sim PATH] [--work-dir DIR]
  check_fence_rtl.py --selfcheck
退出码：0 通过；1 判据失败；2 用法/缺件/配置错误。
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ARCH = _HERE.parents[1]
_REPO = _HERE.parents[3]

for _sub in (("tools", "testcases", "arch"), ("tools", "testcases", "lib"),
             ("tools", "infra"), ("tests", "shared")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)

import chipyard_engine                   # noqa: E402
import paths as _paths                   # noqa: E402
import signature as _signature           # noqa: E402

GEN = _HERE.with_name("gen_fence_rtl.py")
LDS = _HERE.with_name("fence_rtl.lds")
DEFAULT_SIM = (_REPO / ".work" / "source" / "chipyard" / "sims" / "verilator"
               / "simulator-chipyard.harness-WumingVastConfig")
TIMEOUT = 900


class SetupError(RuntimeError):
    pass


def _load_gen():
    spec = importlib.util.spec_from_file_location("_arch_gen_fence_rtl", GEN)
    if spec is None or spec.loader is None:
        raise SetupError("无法加载 %s" % GEN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run(cmd, timeout=120):
    import subprocess
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout,
                              stdin=subprocess.DEVNULL)
        return proc.returncode, proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as exc:
        return -2, (exc.stdout or b"").decode("utf-8", "replace")


def build(case_id: str, work: Path) -> Path:
    gen = _load_gen()
    carrier = gen.load_carrier()
    bin_dir = _paths.host_toolchain_bin()
    llvm_mc = bin_dir / "llvm-mc"
    ld_lld = bin_dir / "ld.lld"
    for path in (llvm_mc, ld_lld, LDS):
        if not path.is_file():
            raise SetupError("缺件 %s（make install-host）" % path)
    work.mkdir(parents=True, exist_ok=True)
    asm = work / ("fence_%s.S" % case_id)
    asm.write_text(gen.render(case_id), encoding="utf-8")
    obj = work / ("fence_%s.o" % case_id)
    rc, out = _run([str(llvm_mc), "--triple=dadao-unknown-elf", "-filetype=obj",
                    "-I", str(_REPO), str(asm), "-o", str(obj)])
    if rc != 0:
        raise SetupError("llvm-mc 失败 rc=%d: %s" % (rc, out[-400:]))
    elf = work / ("fence_%s.elf" % case_id)
    rc, out = _run([str(ld_lld), "-T", str(LDS), str(obj), "-o", str(elf)])
    if rc != 0:
        raise SetupError("ld.lld 失败 rc=%d: %s" % (rc, out[-400:]))
    if not carrier.CASES or case_id not in carrier.CASES:
        raise SetupError("未知 case %r" % case_id)
    return elf


def selfcheck() -> int:
    problems = []
    print("=" * 72)
    print("check_fence_rtl --selfcheck（不启动仿真）")
    print("=" * 72)
    try:
        gen = _load_gen()
        carrier = gen.load_carrier()
    except SetupError as exc:
        print("  FAIL  加载生成器: %s" % exc)
        return 1
    if not LDS.is_file():
        problems.append("缺链接脚本 %s" % LDS)
    for case_id in carrier.CASES:
        text = gen.render(case_id)
        probes = carrier.case_probes(case_id)
        want = carrier.expected_values(probes, carrier.illi_cause())
        n_word = text.count(".dd.t32")
        n_rec = text.count("__REC")
        if n_word != len(probes) or n_rec != len(probes):
            problems.append("%s: .dd.t32 %d / __REC %d ≠ %d 个 probe"
                            % (case_id, n_word, n_rec, len(probes)))
            continue
        # 每个编码值必须与 carrier 的 fence_word 一致（回读校验）
        words = [line.split(".dd.t32")[1].split("@@")[0].strip()
                 for line in text.splitlines() if ".dd.t32" in line]
        got = [int(w, 16) for w in words]
        exp_words = [carrier.fence_word(p[1], p[2], p[3], p[4]) for p in probes]
        if got != exp_words:
            problems.append("%s: 生成编码与 fence_word 不一致" % case_id)
        else:
            print("  PASS  %s: %d 个 probe，编码回读一致，期望 %s"
                  % (case_id, len(probes),
                     ", ".join("%#x" % w for w in want)))
    print("-" * 72)
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        print("check_fence_rtl: selfcheck FAIL（%d 项）" % len(problems))
        return 1
    print("check_fence_rtl: selfcheck PASS")
    return 0


def run_case(case_id: str, sim: Path, work: Path, timeout: int) -> int:
    gen = _load_gen()
    carrier = gen.load_carrier()
    if case_id not in carrier.CASES:
        print("check_fence_rtl: 未知 case %r（允许 %s）"
              % (case_id, list(carrier.CASES)), file=sys.stderr)
        return 2
    if not sim.is_file():
        raise SetupError("缺 RTL 仿真器: %s（--sim 或 chipyard Vast 构建）" % sim)
    elf = build(case_id, work)
    outdir = work / "sim"
    result = chipyard_engine.run(str(elf), str(outdir), sim=str(sim),
                                 timeout=timeout)
    probes = carrier.case_probes(case_id)
    want = carrier.expected_values(probes, carrier.illi_cause())
    problems = []
    if result.get("timed_out"):
        problems.append("RTL 仿真超时（%ds / max-cycles）" % timeout)
    if result.get("verilator_error"):
        problems.append("Verilator %Error（见 sim.log）")
    if result.get("unimplemented_op") is not None:
        problems.append("semihosting 服务未实现: %r"
                        % result.get("unimplemented_op"))
    if result.get("guest_exit") != 0:
        problems.append("guest 退出码 %r（0 = 通过；126 = abort）"
                        % result.get("guest_exit"))
    if not result.get("sim_stable"):
        problems.append("仿真器二进制 md5 前后不一致: %r -> %r"
                        % (result.get("sim_md5_before"),
                           result.get("sim_md5_after")))
    blob = result.get("semiout") or b""
    got = None
    try:
        got = _signature.parse(blob, len(want))
    except _signature.SignatureError as exc:
        problems.append("签名流: %s" % exc)
    else:
        problems.extend("签名流: " + p
                        for p in _signature.compare(got, want))
    print("  %-4s rtl        %-22s rc=%s slots=%s"
          % ("PASS" if not problems else "FAIL", case_id,
             result.get("guest_exit"), got))
    for p in problems:
        print("  [FAIL] %s" % p)
    return 0 if not problems else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None)
    ap.add_argument("--sim", default=str(DEFAULT_SIM))
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    if not args.only:
        print("check_fence_rtl: --only 必填", file=sys.stderr)
        return 2
    work = (Path(args.work_dir) if args.work_dir
            else Path(_paths.test_artifacts_dir()) / "arch" / "fence_rtl"
            / args.only)
    work = work.resolve()
    try:
        return run_case(args.only, Path(args.sim).resolve(), work, args.timeout)
    except SetupError as exc:
        print("check_fence_rtl: SETUP: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
