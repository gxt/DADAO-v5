#!/usr/bin/env python3
"""`tests/arch/time/check_time_rtl.py` — `cfx_time`（cfxha 34）的 RTL 承载
（`m16-chipyard-023`）。

与 QEMU/gem5 驱动（`check_time.py`）**共用同一份**槽序与期望
（`tests/arch/time/time_oracle.py`）：同一 case、同一 8 字节签名流、逐槽相同。

## 载体

`tests/arch/time/time_rtl.S`（`time_rtl.lds`）——汇编期 `--defsym` 选 case 与
运行模式：

  * `TCASE=1`（`arch-time-001`，7 槽）：`TMODE=3/2/0` 各出三个镜像；
  * `TCASE=2`（`arch-time-002`，6 槽）：只 `TMODE=3`（S/U 无同步异常处理程序）。

**RTL 与 QEMU/gem5 的差异只有「故障观察通道」**：RTL 的 hmon 是共享的 Tiny
保存-跳转处理器（cause_id 槽 = hmon SRAM + 0xE0、回落点 = +0xF8）；QEMU/gem5 的
step5 固件把 cause 写进 profile 的 `FAULT_RECORD` 并从 `cause_ip + 4` 回。判据
（cause 值、槽序）两侧相同。

## 判据（三条独立来源）

  1. **签名流**：逐槽等于 `time_oracle.expected()`（契约常量 + 探针谓词）；
  2. **运行模式**：`+verbose` 的 `cfx2 …` trace 里，`ha = cfx_time` 的访问
     `mode=` 必须全部等于请求模式（`spec/Kaiwu §7.1` 的编码）——不由探针自述；
  3. **原始读数复核**：trace 里的 `ha=34 cg=10 rc=1` 读数据（`data=`）按出现
     顺序取出 `t0/t1/t2`，`ha=15 cg=8 rc=2` 取出 `cycle`，交给
     `time_oracle.check_time_value` **重新判**单调 / 严格递增 / 增量有界 /
     epoch / 同基准（判据函数与 QEMU/gem5 侧共用）。这一条不依赖探针算出的
     谓词，是本平台对 `0 < t1-t0 < 2^32` 的**独立**复核。

用法：
  check_time_rtl.py --only arch-time-001|002 --sim PATH \\
      [--mode hmon|smon|umon] [--work-dir DIR] [--signature-out PATH]
      [--timeout N] [--nm PATH] [--root DIR] [--self-test] [--list]

退出码：0 通过；1 判据失败；2 用法/缺件/配置错误。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ARCH = _HERE.parents[1]               # tests/arch
_REPO = _HERE.parents[3]               # 仓库根

for _sub in (("tests", "shared"), ("tools", "testcases", "lib"),
             ("tools", "infra")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

import signature as _signature             # noqa: E402  真源
import time_oracle as oracle               # noqa: E402

PROBE = _HERE.with_name("time_rtl.S")
LDS = _HERE.with_name("time_rtl.lds")
DEFAULT_SIM = (_REPO / ".work" / "source" / "chipyard" / "sims" / "verilator"
               / "simulator-chipyard.harness-WumingVastConfig")
MAX_CYCLES = 5000000
TIMEOUT = 200

# 探针在 trace 里的形态（`WumingCore: cfx2 ip=… ha=.. cg=.. rc=.. … data=..`）。
CFX2_RE = re.compile(
    r"cfx2 ip=0x(?P<ip>[0-9a-f]+) ha=(?P<ha>\d+) cg=\s*(?P<cg>\d+) "
    r"rc=\s*(?P<rc>\d+) write=(?P<w>\d) ok=(?P<ok>\d) mode=(?P<mode>\d+) "
    r"data=0x(?P<data>[0-9a-f]+)")


class SetupError(RuntimeError):
    """缺件/配置错误（退出码 2）。"""


def _run(cmd, timeout, cwd=None):
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout,
                              stdin=subprocess.DEVNULL, cwd=cwd)
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        return -2, exc.stdout or b""


def tools(args):
    nm = Path(args.nm) if args.nm else None
    if nm is None:
        try:
            import paths as _paths
            nm = _paths.host_toolchain_bin() / "llvm-nm"
        except Exception as exc:                  # noqa: BLE001
            raise SetupError("无法确定 llvm-nm: %s（--nm）" % exc)
    out = {}
    for name, path in (("llvm-mc", nm.with_name("llvm-mc")),
                       ("ld.lld", nm.with_name("ld.lld")),
                       ("llvm-nm", nm)):
        if not path.is_file():
            raise SetupError("缺 %s: %s（make install-host 或 --nm）"
                             % (name, path))
        out[name] = path
    return out


def assemble(t, case_id, mode, work):
    tcase = 1 if case_id == "arch-time-001" else 2
    tmode = {"hmon": 3, "smon": 2, "umon": 0}[mode]
    obj = work / ("time_%s_%d.o" % (case_id, tmode))
    elf = work / ("time_%s_%d.elf" % (case_id, tmode))
    rc, out = _run([str(t["llvm-mc"]), "--triple=dadao-unknown-elf",
                    "-filetype=obj", "-I", str(_REPO),
                    "--defsym", "TCASE=%d" % tcase,
                    "--defsym", "TMODE=%d" % tmode,
                    str(PROBE), "-o", str(obj)], 120)
    if rc != 0:
        raise SetupError("llvm-mc 失败 rc=%d: %s"
                         % (rc, out.decode("utf-8", "replace")[-400:]))
    rc, out = _run([str(t["ld.lld"]), "-T", str(LDS), str(obj),
                    "-o", str(elf)], 120)
    if rc != 0:
        raise SetupError("ld.lld 失败 rc=%d: %s"
                         % (rc, out.decode("utf-8", "replace")[-400:]))
    return elf


def run_sim(sim, elf, work, timeout):
    out = work / (elf.stem + ".out")
    log = work / (elf.stem + ".log")
    cmd = [str(sim), "+permissive", "+verbose", "+loadmem=" + str(elf),
           "+semiout=" + str(out), "+max-cycles=%d" % MAX_CYCLES,
           "+permissive-off", "none"]
    rc, text = _run(cmd, timeout, cwd=str(work))
    log.write_bytes(text)
    return rc, out, log


def trace_facts(log: Path, time_ha: int, hart_ha: int) -> dict:
    """从 `+verbose` trace 取：模式集合、`cfx_time` 读数序列、cycle 读数。"""
    modes = set()
    times = []
    cycles = []
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = CFX2_RE.search(line)
        if not m:
            continue
        if int(m.group("w")) != 0:
            continue
        ha = int(m.group("ha"))
        cg = int(m.group("cg"))
        rc = int(m.group("rc"))
        data = int(m.group("data"), 16)
        if ha == time_ha:
            modes.add(int(m.group("mode")))
            if cg == 10 and rc == 1:
                times.append(data)
        elif ha == hart_ha and cg == 8 and rc == 2:
            cycles.append(data)
    return {"modes": sorted(modes), "times": times, "cycles": cycles}


def check(case_id, mode, args) -> int:
    t = tools(args)
    # 仿真器以 work 为 cwd 启动 ⇒ 相对路径会解析到别处：统一成绝对路径。
    sim = Path(args.sim).resolve() if args.sim else DEFAULT_SIM
    if not Path(sim).is_file():
        raise SetupError("缺 RTL 仿真器: %s（--sim 或 chipyard Vast 构建）" % sim)
    if mode not in oracle.CASE_MODES[case_id]:
        raise SetupError("%s 不允许 --mode %s（只有 %r）"
                         % (case_id, mode, list(oracle.CASE_MODES[case_id])))
    f = oracle.facts(_REPO)
    expected = oracle.expected(case_id, _REPO)
    labels = oracle.slot_labels(case_id)

    work = (Path(args.work_dir) if args.work_dir else
            _REPO / ".work" / "evidence" / "m16-chipyard-023" / "work" / "rtl"
            / ("%s_%s" % (case_id, mode))).resolve()
    work.mkdir(parents=True, exist_ok=True)
    elf = assemble(t, case_id, mode, work)
    rc, stream, log = run_sim(sim, elf, work, args.timeout)
    if rc == -2:
        raise SetupError("仿真超时（%ds）" % args.timeout)

    problems = []
    if rc != 0:
        problems.append("仿真器退出码 %d" % rc)
    got = None
    body = stream.read_bytes() if stream.is_file() else b""
    try:
        got = _signature.parse(body, len(expected))
    except _signature.SignatureError as exc:
        problems.append("签名流: %s" % exc)
    else:
        problems.extend("签名流: " + p
                        for p in _signature.compare(got, expected))

    facts = trace_facts(log, f["time"], f["hart"])
    want_mode = oracle.mode_code(f, mode)
    if not facts["modes"]:
        problems.append("trace 里没有 cfx_time 访问（探针未跑到？）")
    elif facts["modes"] != [want_mode]:
        problems.append("cfx_time 访问的运行模式 %r ≠ 请求模式 %d"
                        % (facts["modes"], want_mode))

    if case_id == "arch-time-001":
        if len(facts["times"]) < 3:
            problems.append("cfx_time 读数不足 3 次（trace 里 %d 次）"
                            % len(facts["times"]))
        elif len(facts["cycles"]) < 1:
            problems.append("trace 里没有 cfx_hart cycle 读数")
        else:
            t0, t1, t2 = facts["times"][0], facts["times"][1], facts["times"][2]
            problems.extend(oracle.check_time_value(
                t0, t1, facts["cycles"][0], t2))
            facts["delta"] = (t1 - t0) & ((1 << 64) - 1)

    out = Path(args.signature_out) if args.signature_out else \
        work / ("signature_%s_%s.bin" % (case_id, mode))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    result = {
        "case": case_id,
        "mode": mode,
        "expected_mode_code": want_mode,
        "observed_cfx_time_modes": sorted(facts["modes"]),
        "signature_slots": got,
        "expected_signature": expected,
        "slot_labels": list(labels),
        "trace": facts,
        "exit_code": rc,
        "problems": problems,
        "verdict": "PASS" if not problems else "FAIL",
    }
    (work / ("run_%s_%s.json" % (case_id, mode))).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  %-4s %-16s %-4s rc=%s cfx_time_modes=%r sig=%s"
          % (result["verdict"], case_id, mode, rc,
             result["observed_cfx_time_modes"], got))
    if "delta" in facts:
        print("        time t0=%#x t1=%#x delta=%#x cycle=%#x"
              % (facts["times"][0], facts["times"][1], facts["delta"],
                 facts["cycles"][0]))
    if problems:
        for p in problems:
            print("  [FAIL] %s" % p)
        return 1
    return 0


# ---------------------------------------------------------------------------
# --self-test（不启动模拟器）
# ---------------------------------------------------------------------------
def _arch_signature():
    """加载 arch 的签名薄壳（`tests/arch/common/signature.py`，带本模块私有名）。

    直接 `import signature` 会命中已加载的 `tests/shared/signature.py` 真源
    （它没有 `load_expected_signature`），故用 importlib 单独加载薄壳。
    """
    import importlib.util
    path = _ARCH / "common" / "signature.py"
    spec = importlib.util.spec_from_file_location("_arch_sig_shim", path)
    if spec is None or spec.loader is None:
        raise ImportError("无法加载 %s" % path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def self_test() -> int:
    problems = []
    print("=" * 72)
    print("check_time_rtl --self-test（不启动模拟器）")
    print("=" * 72)
    if PROBE.is_file() and LDS.is_file():
        print("  PASS  载体存在: time_rtl.S / time_rtl.lds")
    else:
        problems.append("缺载体 time_rtl.S / time_rtl.lds")
    try:
        f = oracle.facts(_REPO)
    except oracle.OracleError as exc:
        problems.append(str(exc))
        f = None
    if f:
        print("  PASS  判据现场派生（cfx_time=%d、freq=%d、CFXREG=%#x、"
              "cycle 行 cg8 rc2）" % (f["time"], f["freq_hz"], f["cfxreg"]))

    # 逐 case / 逐模式：槽数一致 + 每条断言可达 FAIL（mutation 必红）。
    for case_id in oracle.CASES:
        want = oracle.expected(case_id, _REPO)
        if len(want) != len(oracle.slot_labels(case_id)):
            problems.append("%s: 期望 %d 槽 ≠ 槽名 %d"
                            % (case_id, len(want),
                               len(oracle.slot_labels(case_id))))
            continue
        ok = _signature.compare(list(want), want)
        if ok:
            problems.append("%s: 正确槽流被判红（control 失败）" % case_id)
        for idx in range(len(want)):
            bad = list(want)
            bad[idx] = (bad[idx] ^ 0x1) & ((1 << 64) - 1)
            if not _signature.compare(bad, want):
                problems.append("%s: 槽 %d 的 mutation 未判红（断言恒真）"
                                % (case_id, idx))
        if len(want) == 0:
            problems.append("%s: 期望槽为空" % case_id)
        print("  PASS  %s: %d 槽 control + %d 条 mutation 均可达 FAIL"
              % (case_id, len(want), len(want)))

    # 原始读数复核函数：正确/错误两个方向都要有判据。
    good = oracle.check_time_value(100, 200, 210, 205)
    if good:
        problems.append("check_time_value: 合法读数被判红（%r）" % good)
    cases = {
        "不递增": (200, 200, 210, 205),
        "倒退": (300, 200, 210, 205),
        "增量过大": (0, (1 << 33) + 1, 210, 205),
        "高位为 1": (1 << 63, (1 << 63) + 10, 210, 205),
        "cycle 早于 time": (100, 200, 190, 205),
    }
    for name, (t0, t1, cyc, t2) in cases.items():
        if not oracle.check_time_value(t0, t1, cyc, t2):
            problems.append("check_time_value: %s 未判红（断言恒真）" % name)
    print("  PASS  check_time_value: control + %d 条反例均可达 FAIL"
          % len(cases))

    # trace 解析：合成一行 `+verbose` 输出，必须取出 (mode, data)。
    synth = ("WumingCore: cfx2 ip=0xffffff002188 ha=34 cg=10 rc= 1 write=0 "
             "ok=1 mode=2 data=0x0000000000001234 wdata=0x0 cycle= 1781\n"
             "WumingCore: cfx2 ip=0xffffff002190 ha=15 cg= 8 rc= 2 write=0 "
             "ok=1 mode=2 data=0x0000000000001300 wdata=0x0 cycle= 1790\n")
    tmp = _REPO / ".work" / "evidence" / "m16-chipyard-023" / "work" \
        / "rtl" / "selftest-trace.log"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(synth, encoding="utf-8")
    facts = trace_facts(tmp, 34, 15)
    if facts["modes"] != [2] or facts["times"] != [0x1234] \
            or facts["cycles"] != [0x1300]:
        problems.append("trace 解析未按期望取数: %r" % (facts,))
    else:
        print("  PASS  trace 解析（mode / cfx_time 读数 / cycle 读数）")

    # expected.yaml 的登记与现场派生双向核对（任一单侧改动都判红）。
    try:
        arch_sig = _arch_signature()
        yaml_path = _HERE.with_name("expected.yaml")
        for case_id in oracle.CASES:
            want = oracle.expected(case_id, _REPO)
            listed = arch_sig.load_expected_signature(yaml_path, case_id)
            if listed is None:
                problems.append("expected.yaml 缺 %s 的 signature" % case_id)
            elif listed != want:
                problems.append("expected.yaml 的 %s 登记 %r ≠ 现场派生 %r"
                                % (case_id, listed, want))
        print("  PASS  expected.yaml 登记 == 现场派生（%d case）"
              % len(oracle.CASES))
    except ImportError as exc:
        problems.append("无法加载 arch signature 薄壳: %s" % exc)

    # 用例元数据：modes.yaml 的允许集 = 本承载支持集。
    try:
        import yaml
        doc = yaml.safe_load((_ARCH / "modes.yaml").read_text(
            encoding="utf-8"))
        modes_cases = doc.get("cases") or {}
    except Exception as exc:                      # noqa: BLE001
        problems.append("读 modes.yaml 失败: %s" % exc)
    else:
        for case_id in oracle.CASES:
            entry = modes_cases.get(case_id)
            if not isinstance(entry, dict):
                problems.append("modes.yaml 缺 %s" % case_id)
            elif tuple(entry.get("modes") or ()) != oracle.CASE_MODES[case_id]:
                problems.append("%s 的 modes=%r ≠ RTL 承载支持集 %r"
                                % (case_id, entry.get("modes"),
                                   list(oracle.CASE_MODES[case_id])))
        print("  PASS  modes.yaml 允许集与 RTL 承载支持集双向核对")

    print("-" * 72)
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        print("check_time_rtl: self-test FAIL（%d 项）" % len(problems))
        return 1
    print("check_time_rtl: self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None, choices=oracle.CASES)
    ap.add_argument("--sim", default=None)
    ap.add_argument("--mode", default="hmon", choices=oracle.MODES)
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--signature-out", default=None)
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--nm", default=None)
    ap.add_argument("--root", default=None)
    ap.add_argument("--self-test", "--selfcheck", dest="self_test",
                    action="store_true",
                    help="不启动模拟器；`--selfcheck` 是 run_arch 的 driver 契约名")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for case_id in oracle.CASES:
            for mode in oracle.CASE_MODES[case_id]:
                print("%s %s（%s）" % (case_id, mode, PROBE.name))
        return 0
    if args.self_test:
        return self_test()
    if not args.only:
        print("check_time_rtl: --only 必填（%r）" % (oracle.CASES,),
              file=sys.stderr)
        return 2
    try:
        return check(args.only, args.mode, args)
    except SetupError as exc:
        print("check_time_rtl: SETUP: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
