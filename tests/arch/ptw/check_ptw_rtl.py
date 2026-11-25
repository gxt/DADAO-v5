#!/usr/bin/env python3
"""`tests/arch/ptw/check_ptw_rtl.py` — cfx4 的 RTL（chipyard
`WumingVastConfig`）承载驱动（`m16-chipyard-018`，`kind: driver`）。

**同一 case id、同一期望**：本文件按 `tests/arch/ptw/rtl-coverage.yaml` 把
`m16-testcases-010` 的 14 条 `arch-ptw-*` 映射到 RTL 承载：

  * `signature`（002/006/007/013）：跑 `ptw_sig.S` 的同一 case，签名流与
    QEMU/gem5 逐槽比较；期望值来自 `expected.yaml`（唯一真源），登记的 RTL
    差异来自 `tests/arch/expected-divergences.yaml` 的 `slots`（当前无条目：
    ADWBFAIL 不做用例，`DIV-04`）；
  * `guest`（001/003/004/005/008/009/010/011/012）：同一 `ptw_sig.S` 的 case，
    由 guest 内断言判（非零退出 = 该检查失败）；签名流 0 槽（QEMU/gem5 侧也是
    0 槽，跨平台比较按空流登记）；
  * `partial`（当前无条目）：同上，但只覆盖 QEMU 检查点的一部分（原因在清单里）；
  * `gap`（015）：RTL 当前没有等价观测面，登记原因与 `close_when`；
    只返回 `GAP`（退出码 77），**不**把「没跑」当成通过。

判据不写魔数：几何/PTE/期望槽全部由 `gen_ptw_sig_tables.py` 现场算出，并与
`expected.yaml` 双向核对；cause 编码来自 `contract-see §6.1/§6.1.1`。

用法（`run_arch.py` 的 chipyard 后端按此契约调用）：
  check_ptw_rtl.py --only arch-ptw-002 --sim PATH --work-dir DIR \
      --signature-out PATH
  check_ptw_rtl.py --selfcheck
  check_ptw_rtl.py --list
退出码：0 通过；1 判据失败；2 用法/缺件/配置错误；77 已登记的 RTL 缺口。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ARCH = _HERE.parents[1]
_REPO = _HERE.parents[3]
for _sub in (("tools", "testcases", "lib"), ("tools", "infra"), ("tests", "shared"),
             ("tests", "arch")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)

import chipyard_engine                   # noqa: E402
import paths as _paths                   # noqa: E402
import signature as _signature           # noqa: E402
from common import signature as _arch_sig  # noqa: E402

GEN = _HERE.with_name("gen_ptw_sig_tables.py")
ASM = _HERE.with_name("ptw_sig.S")
LDS = _HERE.with_name("ptw_sig.lds")
COVERAGE = _HERE.with_name("rtl-coverage.yaml")
EXPECTED = _HERE.with_name("expected.yaml")
DIVERGENCES = _ARCH / "expected-divergences.yaml"
GAP_RC = 77
DEFAULT_SIM = (_REPO / ".work" / "source" / "chipyard" / "sims" / "verilator"
               / "simulator-chipyard.harness-WumingVastConfig")
TIMEOUT = 900


class SetupError(RuntimeError):
    pass


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise SetupError("无法加载 %s" % path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_gen():
    return _load_module("_arch_gen_ptw_sig", GEN)


def load_expected():
    """`expected.yaml` 的签名槽（唯一真源；不另写期望）。"""
    return _arch_sig


def coverage() -> dict:
    """RTL 覆盖清单：{case_id: {status, rtl_case, reason, close_when}}。"""
    import yaml

    if not COVERAGE.is_file():
        raise SetupError("缺件 %s（RTL 覆盖清单）" % COVERAGE)
    try:
        doc = yaml.safe_load(COVERAGE.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SetupError("rtl-coverage.yaml 解析失败: %s" % exc)
    out = {}
    for cid, entry in ((doc or {}).get("cases") or {}).items():
        if not isinstance(entry, dict):
            raise SetupError("rtl-coverage.yaml: %s 不是映射" % cid)
        status = entry.get("status")
        if status not in ("signature", "guest", "partial", "gap"):
            raise SetupError("%s: 未知 status %r" % (cid, status))
        if status != "gap" and not isinstance(entry.get("rtl_case"), int):
            raise SetupError("%s: 非 gap 必须给 rtl_case" % cid)
        if status in ("gap", "partial"):
            for key in ("reason", "close_when"):
                if not entry.get(key):
                    raise SetupError("%s: %s 缺 %s" % (cid, status, key))
        out[cid] = entry
    return out


def declared_divergences(case_id: str) -> dict:
    """`expected-divergences.yaml` 的逐槽 RTL 例外：{slot: (id, value)}。"""
    try:
        return _arch_sig.load_divergence_slots(DIVERGENCES, case_id, "chipyard")
    except ValueError as exc:
        raise SetupError(str(exc))


# ---------------------------------------------------------------------------
# 构建
# ---------------------------------------------------------------------------
def build(case_no: int, work: Path, bin_dir: Path = None) -> Path:
    bin_dir = Path(bin_dir) if bin_dir else _paths.host_toolchain_bin()
    llvm_mc = bin_dir / "llvm-mc"
    ld_lld = bin_dir / "ld.lld"
    for path in (llvm_mc, ld_lld, ASM, LDS):
        if not path.is_file():
            raise SetupError("缺件 %s（make install-host）" % path)
    work.mkdir(parents=True, exist_ok=True)
    inc = work / "ptw_sig_tables.inc"
    proc = subprocess.run([sys.executable, str(GEN), "--emit", "inc"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise SetupError("生成器失败 rc=%d: %s"
                         % (proc.returncode, proc.stderr.decode("utf-8", "replace")[-600:]))
    inc.write_bytes(proc.stdout)

    obj = work / ("ptw_sig_%d.o" % case_no)
    proc = subprocess.run(
        [str(llvm_mc), "--triple=dadao-unknown-elf", "-filetype=obj",
         "-I", str(_REPO), "-I", str(work), "--defsym", "PTW_CASE=%d" % case_no,
         str(ASM), "-o", str(obj)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        raise SetupError("llvm-mc rc=%d: %s"
                         % (proc.returncode,
                            proc.stdout.decode("utf-8", "replace")[-600:]))
    elf = work / ("ptw_sig_%d.elf" % case_no)
    proc = subprocess.run([str(ld_lld), "-T", str(LDS), str(obj), "-o", str(elf)],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        raise SetupError("ld.lld rc=%d: %s"
                         % (proc.returncode,
                            proc.stdout.decode("utf-8", "replace")[-600:]))
    return elf


# ---------------------------------------------------------------------------
# 判据
# ---------------------------------------------------------------------------
def run_case(case_id: str, sim: Path, work: Path, timeout: int,
             bin_dir: Path = None) -> tuple:
    """返回 (rc, blob, detail)。rc=0 通过、1 失败、77 已登记缺口。"""
    table = coverage()
    if case_id not in table:
        raise SetupError("%s 不在 rtl-coverage.yaml（fail-closed）" % case_id)
    entry = table[case_id]
    if entry["status"] == "gap":
        print("  GAP   rtl        %-22s %s" % (case_id, entry["reason"]))
        return GAP_RC, b"", entry["reason"]
    if not sim.is_file():
        raise SetupError("缺 RTL 仿真器: %s（--sim 或 chipyard Vast 构建）" % sim)
    case_no = int(entry["rtl_case"])
    elf = build(case_no, work, bin_dir)
    result = chipyard_engine.run(str(elf), str(work / "sim"), sim=str(sim),
                                 timeout=timeout)
    problems = []
    if result.get("timed_out"):
        problems.append("RTL 仿真超时（%ds）" % timeout)
    if result.get("verilator_error"):
        problems.append("Verilator %Error（见 sim.log）")
    if result.get("unimplemented_op") is not None:
        problems.append("semihosting 服务未实现: %r" % result.get("unimplemented_op"))
    if not result.get("sim_stable"):
        problems.append("仿真器二进制 md5 前后不一致: %r -> %r"
                        % (result.get("sim_md5_before"),
                           result.get("sim_md5_after")))
    expected = load_expected().load_expected_signature(EXPECTED, case_id)
    blob = result.get("semiout") or b""
    slots = None
    if expected is not None:
        try:
            slots = _signature.parse(blob, len(expected))
        except _signature.SignatureError as exc:
            problems.append("签名流: %s" % exc)
        else:
            exceptions = declared_divergences(case_id)
            for idx, (got, want) in enumerate(zip(slots, expected)):
                if idx in exceptions:
                    div_id, declared = exceptions[idx]
                    if got is None:
                        problems.append("槽 %d 未写（登记差异 %s）" % (idx, div_id))
                    elif got != declared:
                        problems.append(
                            "槽 %d 实测 %#x ≠ 登记差异 %s 的值 %#x"
                            "（差异已变：或已修好，需更新/删除登记）"
                            % (idx, got, div_id, declared))
                    else:
                        print("  DIVERGED %s 槽 %d = %#x（登记差异 %s；规范值 %#x）"
                              % (case_id, idx, got, div_id, want))
                    continue
                if got is None:
                    problems.append("槽 %d 未写（期望 0x%016x）" % (idx, want))
                elif got != want:
                    problems.append("槽 %d 期望 0x%016x 实际 0x%016x"
                                    % (idx, want, got))
    else:
        # 未接线签名的 case：判据 = guest 内断言（rc=0）。
        if len(blob):
            problems.append("未接线签名的 case 不应输出字节（收到 %d B）" % len(blob))
    if result.get("guest_exit") != 0:
        problems.append("guest 退出码 %r（0 = 通过；非 0 = 该镜像内第 N 条断言失败）"
                        % result.get("guest_exit"))
    print("  %-4s rtl        %-22s rc=%s slots=%s"
          % ("PASS" if not problems else "FAIL", case_id,
             result.get("guest_exit"), slots))
    for p in problems:
        print("  [FAIL] %s" % p)
    return (0 if not problems else 1), blob, ("; ".join(problems) or "ok")


# ---------------------------------------------------------------------------
# 自检 / 清单
# ---------------------------------------------------------------------------
def selfcheck() -> int:
    import yaml

    problems = []
    print("=" * 72)
    print("check_ptw_rtl --selfcheck（不启动仿真）")
    print("=" * 72)
    for path in (ASM, LDS, GEN, COVERAGE, EXPECTED):
        if not path.is_file():
            problems.append("缺件 %s" % path)
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        return 1

    # 1) 生成器与 expected.yaml 的签名槽双向核对。
    gen = load_gen()
    try:
        proc = subprocess.run([sys.executable, str(GEN), "--selfcheck"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        text = proc.stdout.decode("utf-8", "replace").strip()
        print("  %s  gen --selfcheck: %s"
              % ("PASS" if proc.returncode == 0 else "FAIL", text.splitlines()[-1]))
        if proc.returncode != 0:
            problems.append("gen_ptw_sig_tables --selfcheck rc=%d" % proc.returncode)
    except OSError as exc:
        problems.append("无法运行生成器: %s" % exc)

    # 2) 覆盖清单 == arch.yaml 的 cfx4 14 条；signature 集 == expected.yaml 的
    #    `signature:` 集（机械核对，不靠人记）。
    table = coverage()
    arch = yaml.safe_load((_REPO / "tests" / "arch.yaml").read_text(encoding="utf-8"))
    ptw_ids = sorted(e["id"] for e in arch
                     if isinstance(e, dict) and str(e.get("file", "")).startswith(
                         "arch/ptw/") and e.get("kind") == "driver"
                     and e.get("id", "").startswith("arch-ptw-"))
    if sorted(table) != ptw_ids:
        problems.append("覆盖清单与 arch.yaml 不一致：清单 %r vs %r"
                        % (sorted(table), ptw_ids))
    exp = yaml.safe_load(EXPECTED.read_text(encoding="utf-8"))
    sig_ids = sorted(e["id"] for e in exp.get("cases") or []
                     if any(c.get("signature") for c in e.get("checks") or []))
    cov_sig = sorted(cid for cid, e in table.items()
                     if e["status"] == "signature")
    if sig_ids != cov_sig:
        problems.append("signature 覆盖与 expected.yaml 不一致：%r vs %r"
                        % (cov_sig, sig_ids))
    status_count = {}
    for cid, e in table.items():
        status_count[e["status"]] = status_count.get(e["status"], 0) + 1
    print("  PASS  覆盖清单: %d 条 = %s"
          % (len(table), ", ".join("%s=%d" % (k, status_count[k])
                                   for k in sorted(status_count))))

    # 3) 登记的差异槽必须与生成器的 RTL 观测值一致。
    for cid, e in table.items():
        if e["status"] != "signature":
            continue
        try:
            div = declared_divergences(cid)
        except SetupError as exc:
            problems.append(str(exc))
            continue
        case_no = int(e["rtl_case"])
        want = gen.rtl_slots(case_no)
        for idx, (div_id, value) in div.items():
            if idx >= len(want) or want[idx] != value:
                problems.append("%s 槽 %d：差异 %s 的值 %#x ≠ 生成器 RTL 槽 %r"
                                % (cid, idx, div_id, value, want))

    # 4) gap/partial 必须写原因与 close_when（coverage() 已查）；打印。
    for cid, e in sorted(table.items()):
        if e["status"] in ("gap", "partial"):
            print("  DECL  %-22s %-9s %s" % (cid, e["status"], e["reason"]))

    print("-" * 72)
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        print("check_ptw_rtl: selfcheck FAIL（%d 项）" % len(problems))
        return 1
    print("check_ptw_rtl: selfcheck PASS")
    return 0


def list_plan() -> int:
    for cid, e in sorted(coverage().items()):
        print("%-22s %-9s rtl_case=%s %s"
              % (cid, e["status"], e.get("rtl_case"), e.get("reason", "")))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None)
    ap.add_argument("--sim", default=None,
                    help="chipyard Vast Verilator 仿真器（缺省 = 构建树）")
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--signature-out", default=None)
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--toolchain-bin", default=None)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    if args.list:
        return list_plan()
    if not args.only:
        print("check_ptw_rtl: --only 必填（或 --selfcheck/--list）", file=sys.stderr)
        return 2
    work = (Path(args.work_dir) if args.work_dir
            else Path(_paths.test_artifacts_dir()) / "arch" / "ptw_rtl" / args.only)
    sig_out = (Path(args.signature_out) if args.signature_out
               else work / "signature.bin")
    sim = (Path(args.sim) if args.sim else DEFAULT_SIM)
    try:
        bin_dir = (Path(args.toolchain_bin) if args.toolchain_bin
                   else _paths.host_toolchain_bin())
        rc, blob, detail = run_case(args.only, sim.resolve(), work.resolve(),
                                    args.timeout, bin_dir)
    except SetupError as exc:
        print("check_ptw_rtl: SETUP: %s" % exc, file=sys.stderr)
        return 2
    work.mkdir(parents=True, exist_ok=True)
    sig_out.parent.mkdir(parents=True, exist_ok=True)
    sig_out.write_bytes(blob if rc == 0 else b"")
    (work / "run.json").write_text(json.dumps(
        {"case": args.only, "rc": rc, "detail": detail,
         "signature_bytes": len(blob), "sim": str(sim)},
        ensure_ascii=False, indent=2), encoding="utf-8")
    if rc == GAP_RC:
        return GAP_RC
    return rc


if __name__ == "__main__":
    sys.exit(main())
