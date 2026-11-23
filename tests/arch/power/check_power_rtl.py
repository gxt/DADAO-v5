#!/usr/bin/env python3
"""`tests/arch/power/check_power_rtl.py` — cfx_power 用例的 **RTL（chipyard
`WumingVastConfig`）承载**（`m16-testcases-016`，按需跑）。

为什么不在 `run_arch.py` 里：`common/platform.py` 的 chipyard 后端仍是
**fail-closed**（RTL 后端接入由 `m16-chipyard-018`/`check-arch-vast` 承担）；
本文件是同一用例的**按需第三方证据**：探针由 `gen_power_rtl.py` 从
`power_vast.py` 的**同一张探针表**生成，签名流与 QEMU/gem5 逐槽同源比对。

RTL 侧的差异（`gen_power_rtl.py` 文件头）：故障走固件 hmon
（`HMON_BASE+0xE0` / `+0xF8`），测试体固定交付为 `cfx_power`（cfx63）/hypv
（无 U/S 进入链）⇒ `arch-power-001` 只跑一次。

用法：
  check_power_rtl.py --only arch-power-001 [--sim PATH] [--work-dir DIR]
  check_power_rtl.py --selfcheck
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

GEN = _HERE.with_name("gen_power_rtl.py")
LDS = _HERE.with_name("power_rtl.lds")
DEFAULT_SIM = (_REPO / ".work" / "source" / "chipyard" / "sims" / "verilator"
               / "simulator-chipyard.harness-WumingVastConfig")
TIMEOUT = 900


class SetupError(RuntimeError):
    pass


def _load_gen():
    spec = importlib.util.spec_from_file_location("_arch_gen_power_rtl", GEN)
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


def build(case_id: str, work: Path, bin_dir: Path = None) -> Path:
    gen = _load_gen()
    carrier = gen.load_carrier()
    if case_id != "diagnose" and case_id not in carrier.CASES:
        raise SetupError("未知 case %r（允许 %s）"
                         % (case_id, list(carrier.CASES)))
    bin_dir = Path(bin_dir) if bin_dir else _paths.host_toolchain_bin()
    llvm_mc = bin_dir / "llvm-mc"
    ld_lld = bin_dir / "ld.lld"
    for path in (llvm_mc, ld_lld, LDS):
        if not path.is_file():
            raise SetupError("缺件 %s（make install-host）" % path)
    work.mkdir(parents=True, exist_ok=True)
    asm = work / ("power_%s.S" % case_id)
    text = gen.render_diagnose() if case_id == "diagnose" else gen.render(case_id)
    asm.write_text(text, encoding="utf-8")
    obj = work / ("power_%s.o" % case_id)
    rc, out = _run([str(llvm_mc), "--triple=dadao-unknown-elf", "-filetype=obj",
                    "-I", str(_REPO), str(asm), "-o", str(obj)])
    if rc != 0:
        raise SetupError("llvm-mc 失败 rc=%d: %s" % (rc, out[-600:]))
    elf = work / ("power_%s.elf" % case_id)
    rc, out = _run([str(ld_lld), "-T", str(LDS), str(obj), "-o", str(elf)])
    if rc != 0:
        raise SetupError("ld.lld 失败 rc=%d: %s" % (rc, out[-600:]))
    return elf


def run_diagnose(sim: Path, work: Path, timeout: int, bin_dir: Path) -> int:
    """诊断探针（不参与判据）：打印每探针的 cause 与读回值。"""
    import json

    gen = _load_gen()
    carrier = gen.load_carrier()
    elf = build("diagnose", work, bin_dir)
    result = chipyard_engine.run(str(elf), str(work / "sim"), sim=str(sim),
                                 timeout=timeout)
    n = 2 * len(carrier.DIAG_PROBES)
    out = {"exit_code": result.get("guest_exit"),
           "timed_out": bool(result.get("timed_out")), "probes": {}}
    try:
        slots = _signature.parse(result.get("semiout") or b"", n)
    except _signature.SignatureError as exc:
        out["error"] = str(exc)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1
    for idx, (label, _, _, _) in enumerate(carrier.DIAG_PROBES):
        out["probes"][label] = {"cause": slots[2 * idx],
                                "value": slots[2 * idx + 1]}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["exit_code"] == 0 else 1


def selfcheck() -> int:
    """不启动仿真：核对生成文本与探针表一一对应（`__REC` 槽数、cfx2* 目标）。"""
    problems = []
    print("=" * 72)
    print("check_power_rtl --selfcheck（不启动仿真）")
    print("=" * 72)
    try:
        gen = _load_gen()
        carrier = gen.load_carrier()
    except SetupError as exc:
        print("  FAIL  加载生成器: %s" % exc)
        return 1
    if not LDS.is_file():
        problems.append("缺链接脚本 %s" % LDS)

    names = {carrier.cfx_codes()["power"]: "cfx_power",
             carrier.cfx_codes()["hmon"]: "cfx_hmon"}
    for case_id in carrier.CASES:
        text = gen.render(case_id)
        table = carrier.slot_table(case_id)
        want = carrier.expected_values(case_id)
        n_rec = text.count("__REC")
        if n_rec != len(table):
            problems.append("%s: __REC %d ≠ %d 个槽" % (case_id, n_rec,
                                                        len(table)))
            continue
        # 槽序核对：把生成文本里的 cfx2rd/cfx2rc 目标按顺序抽出来比对。
        reads, writes = [], []
        for line in text.splitlines():
            items = line.strip().split("\t")
            if len(items) < 2:
                continue
            mnemonic = items[0]
            operands = [x.strip() for x in items[1].split(",")]
            if len(operands) < 4:       # 只关心 cfx2rd/cfx2rc 的四操作数形式
                continue
            target = ", ".join(operands[:3])
            if mnemonic == "cfx2rd" and (
                    "cfx_power" in target or "cfx_hmon" in target):
                reads.append(target)
            elif mnemonic == "cfx2rc" and (
                    "cfx_power" in target or "cfx_hmon" in target):
                writes.append(target)
        exp_reads, exp_writes = [], []
        for _, _, spec in table:
            target = "%s, cg%d, rc%d" % (names[spec[1]], spec[2], spec[3])
            if spec[0] == "rw":
                exp_writes.append(target)
                exp_reads.append(target)
            elif spec[0] == "fault_wr":
                exp_writes.append(target)
            else:                       # reg / ip_in_rom / fault_rd
                exp_reads.append(target)
        if reads != exp_reads or writes != exp_writes:
            problems.append("%s: 生成文本的 cfx2rd/cfx2rc 目标与探针表不一致"
                            "（读 %r vs %r；写 %r vs %r）"
                            % (case_id, reads, exp_reads, writes, exp_writes))
        else:
            print("  PASS  %s: %d 槽，__REC 与 cfx2rd/cfx2rc 目标逐一对应；"
                  "期望 %s" % (case_id, len(table),
                               ", ".join("%#x" % v for v in want)))
        # 故障面每槽必须「清 cause 槽 + 读 cause 槽」各一次（不靠残留值），
        # 且入口把回落点设成 abort（意外异常 ⇒ __EXIT 126，不是 PASS）。
        n_fault = sum(1 for _, _, s in table if s[0].startswith("fault"))
        if text.count("[rb20, 0xE0]") != 2 * n_fault:
            problems.append("%s: cause 槽访问 %d 次 ≠ 2 × %d 个故障槽"
                            % (case_id, text.count("[rb20, 0xE0]"), n_fault))
        if text.count("[rb20, 0xF8]") != n_fault + 1:
            problems.append("%s: 回落点写入 %d 次 ≠ %d 个故障槽 + 1（入口 abort）"
                            % (case_id, text.count("[rb20, 0xF8]"), n_fault))
        if n_fault and "abort:" not in text:
            problems.append("%s: 有故障槽但缺 `abort` 回落点" % case_id)
        if "__EXIT\t126" not in text:
            problems.append("%s: 缺 fail-closed 退出（__EXIT 126）" % case_id)

    print("-" * 72)
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        print("check_power_rtl: selfcheck FAIL（%d 项）" % len(problems))
        return 1
    print("check_power_rtl: selfcheck PASS")
    return 0


DIVERGENCES = _ARCH / "expected-divergences.yaml"


def declared_divergences(case_id: str) -> dict:
    """`expected-divergences.yaml` 里登记的 RTL 逐槽例外：{slot: (id, 值)}。

    差异必须**登记才放行**（不静默跳过）；同时校验条目的 scope 含 chipyard，
    否则视为配置错误（fail-closed）。
    """
    import yaml

    if not DIVERGENCES.is_file():
        raise SetupError("缺件 %s" % DIVERGENCES)
    try:
        doc = yaml.safe_load(DIVERGENCES.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SetupError("expected-divergences.yaml 解析失败: %s" % exc)
    out = {}
    for entry in (doc or {}).get("divergences") or []:
        if not isinstance(entry, dict):
            continue
        for slot in entry.get("slots") or []:
            if not isinstance(slot, dict) or slot.get("case") != case_id:
                continue
            if "chipyard" not in (entry.get("scope") or []):
                raise SetupError("%s 的逐槽例外未声明 scope: chipyard"
                                 % entry.get("id"))
            idx = int(slot["slot"])
            if idx in out:
                raise SetupError("%s 的槽 %d 被多条差异登记" % (case_id, idx))
            out[idx] = (entry.get("id"), int(slot["chipyard"]))
    return out


def run_case(case_id: str, sim: Path, work: Path, timeout: int,
             bin_dir: Path = None) -> int:
    gen = _load_gen()
    carrier = gen.load_carrier()
    if case_id not in carrier.CASES:
        print("check_power_rtl: 未知 case %r（允许 %s）"
              % (case_id, list(carrier.CASES)), file=sys.stderr)
        return 2
    if not sim.is_file():
        raise SetupError("缺 RTL 仿真器: %s（--sim 或 chipyard Vast 构建）" % sim)
    elf = build(case_id, work, bin_dir)
    outdir = work / "sim"
    result = chipyard_engine.run(str(elf), str(outdir), sim=str(sim),
                                 timeout=timeout)
    want = carrier.expected_values(case_id)
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
    # 落一份签名流给逐槽比对用（QEMU/gem5 侧的流在 run_arch 的
    # `<work>/<case>/<platform>/signature.bin`）。
    (work / "signature.bin").write_bytes(blob)
    got = None
    try:
        got = _signature.parse(blob, len(want))
    except _signature.SignatureError as exc:
        problems.append("签名流: %s" % exc)
    else:
        # 逐槽比对：登记的例外（`expected-divergences.yaml` 的 `slots`）按
        # 登记值判，其余按规范派生值判。例外被修好时登记值不再成立 ⇒ 判红，
        # 提示删除条目（不让差异长期潜伏）。
        exceptions = declared_divergences(case_id)
        for idx, (g, w) in enumerate(zip(got, want)):
            if idx in exceptions:
                div_id, declared = exceptions[idx]
                if g is None:
                    problems.append("签名流: 槽 %d 未写（登记差异 %s）"
                                    % (idx, div_id))
                elif g != declared:
                    problems.append(
                        "签名流: 槽 %d 实测 %#x ≠ 登记差异 %s 的值 %#x"
                        "（差异已变：或已修好，需更新/删除登记）"
                        % (idx, g, div_id, declared))
                else:
                    print("  DIVERGED %s 槽 %d = %#x（登记差异 %s；规范值 %#x）"
                          % (case_id, idx, g, div_id, w))
                continue
            if g is None:
                problems.append("签名流: 槽 %d 未写（期望 0x%016x）" % (idx, w))
            elif g != w:
                problems.append("签名流: 槽 %d 期望 0x%016x 实际 0x%016x"
                                % (idx, w, g))
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
    ap.add_argument("--toolchain-bin", default=None,
                    help="llvm-mc/ld.lld 所在目录（缺省 = 安装根 host 工具链）")
    ap.add_argument("--diagnose", action="store_true",
                    help="跑未纳入判据的差分探针（写 0/cg4/cg6）")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    if not args.only and not args.diagnose:
        print("check_power_rtl: --only 或 --diagnose 必填", file=sys.stderr)
        return 2
    work = (Path(args.work_dir) if args.work_dir
            else Path(_paths.test_artifacts_dir()) / "arch" / "power_rtl"
            / args.only)
    work = work.resolve()
    try:
        bin_dir = (Path(args.toolchain_bin) if args.toolchain_bin
                   else _paths.host_toolchain_bin())
        if args.diagnose:
            return run_diagnose(Path(args.sim).resolve(),
                                work / "diagnose", args.timeout, bin_dir)
        return run_case(args.only, Path(args.sim).resolve(), work, args.timeout,
                        bin_dir=bin_dir)
    except SetupError as exc:
        print("check_power_rtl: SETUP: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
