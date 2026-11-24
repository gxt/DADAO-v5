#!/usr/bin/env python3
"""`tests/arch/cache/check_cache_rtl.py` — cfx5 的 RTL 承载（`m16-testcases-009`）。

与 QEMU/gem5 驱动（`check_cache.py`）**共用同一份**槽序与期望
（`tests/arch/cache/cache_oracle.py`）：同一 case、同一 8 字节签名流、逐槽相同。

## 载体

`tests/arch/cache/cache_rtl.S`（`cache_rtl.lds`）——汇编期 `--defsym` 选 case
（`CCASE=1/2/3`）与运行模式（`TMODE=3/2/0`）；页表/地址/控制字来自
`cache_rtl_tables.inc`（`cache_oracle.emit_rtl_inc`）。`arch-cache-004` 是
`cache-model=off` 的机器维度，RTL 没有该开关（CACHE-27 把「是否暴露」留给
实现）⇒ 本承载返回 77（`GAP`，登记在 `rtl-coverage.yaml`）。

## 判据（三条独立来源）

  1. **签名流**：逐槽等于 `cache_oracle.expected()`；
  2. **运行模式**：`+verbose` 的 `cfx2 …` trace 里，`ha = cfx_cache` 的访问
     `mode=` 必须全部等于请求模式（`spec/Kaiwu §7.1`）——不由探针自述；
  3. **缓存日志**（`WumingCache[icache|dcache]`）：
     * `I|clean` 是 no-op（CACHE-19）⇒ 日志里不得出现 `icache ... op=1`；
     * `D|flush` 写回且删除 ⇒ 有 `wb=1` 的 flush 命令，其后的同一行读必须 miss；
     * `enable=0` 的 `D|invalidate` 不发出（CACHE-08）⇒ 该行只有启用后的那一次；
     * `PA 区间` 只枚举区间内两行（CACHE-17），区间外行不出现；
     * `all` 的 invalidate/clean/flush 各自的日志语义。

用法：
  check_cache_rtl.py --only arch-cache-001 --sim PATH --mode hmon \\
      [--work-dir DIR] [--signature-out PATH] [--timeout N] [--root DIR]
      [--selfcheck] [--list]

退出码：0 通过；1 判据失败；77 登记的 RTL 缺口（GAP）；2 用法/缺件/配置错误。
"""
from __future__ import annotations

import argparse
import json
import re
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
import cache_oracle as oracle              # noqa: E402

PROBE = _HERE.with_name("cache_rtl.S")
LDS = _HERE.with_name("cache_rtl.lds")
DEFAULT_SIM = (_REPO / ".work" / "source" / "chipyard" / "sims" / "verilator"
               / "simulator-chipyard.harness-WumingVastConfig")
MAX_CYCLES = 5000000
TIMEOUT = 240
GAP_RC = 77

CFX2_RE = re.compile(
    r"cfx2 ip=0x(?P<ip>[0-9a-f]+) ha=\s*(?P<ha>\d+) cg=\s*(?P<cg>\d+) "
    r"rc=\s*(?P<rc>\d+) write=(?P<w>\d) ok=(?P<ok>\d) mode=(?P<mode>\d+) "
    r"data=0x(?P<data>[0-9a-f]+)")
LOG_RE = re.compile(r"^WumingCache\[(icache|dcache)\]: (\S+)(.*)$")

CASES = ("arch-cache-001", "arch-cache-002", "arch-cache-003",
         "arch-cache-004")
TMODE = {"hmon": 3, "smon": 2, "umon": 0}


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
    bin_dir = _REPO / ".dadao" / "cross-toolchain" / "bin"
    if not bin_dir.is_dir():
        try:
            import paths as _paths
            bin_dir = _paths.host_toolchain_bin()
        except Exception as exc:                  # noqa: BLE001
            raise SetupError("无法确定工具链: %s（--llvm-mc）" % exc)
    out = {}
    for name in ("llvm-mc", "ld.lld"):
        path = bin_dir / name
        if not path.is_file():
            raise SetupError("缺 %s: %s（make install-host）" % (name, path))
        out[name] = path
    return out


def assemble(t, case_id, mode, work):
    inc = work / "cache_rtl_tables.inc"
    with inc.open("w", encoding="utf-8") as stream:
        oracle.emit_rtl_inc(_REPO, stream)
    obj = work / ("cache_rtl_%s_%d.o" % (case_id, TMODE[mode]))
    elf = work / ("cache_rtl_%s_%d.elf" % (case_id, TMODE[mode]))
    rc, out = _run([str(t["llvm-mc"]), "--triple=dadao-unknown-elf",
                    "-filetype=obj",
                    "-I", str(_REPO / "tests" / "shared" / "asm"),
                    "-I", str(work),
                    "--defsym", "CCASE=%d" % (CASES.index(case_id) + 1),
                    "--defsym", "TMODE=%d" % TMODE[mode],
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


# ---------------------------------------------------------------------------
# trace / cache log
# ---------------------------------------------------------------------------
def trace_mode_sequence(log: Path, cfxha: int):
    """cfx5 访问的运行模式序列（按 trace 顺序，含重复）。"""
    modes = []
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = CFX2_RE.search(line)
        if m and int(m.group("ha")) == cfxha:
            modes.append(int(m.group("mode")))
    return modes


def mode_problem(sequence, want_mode: int):
    """S/U 承载的模式判据：hypv（3）只允许出现在降模式之前。

    降模式前在 hypv 写两轴掩码/`cg3 rc12`（carrier 的权限准备）是合法准备，
    不是 body 访问；一旦进入请求模式，cfx5 的任何访问都必须是它——否则
    `mode=` 观测就会把「body 在 hypv 偷跑」放过去。
    """
    if want_mode not in sequence:
        return "运行模式未观测到：期望 cfx2 trace 里 mode=%d，实际 %r" % (
            want_mode, sequence)
    first = sequence.index(want_mode)
    if any(m != want_mode for m in sequence[first:]):
        return ("cfx5 的访问出现了非请求模式（进入后）: %r（期望进入后全为 %d）"
                % (sequence, want_mode))
    before = set(sequence[:first])
    if not before <= {3}:
        return ("降模式前的 cfx5 访问出现了非 hypv 模式: %r（允许 {3}）"
                % sorted(before))
    return None


def parse_cache_log(text):
    events = []
    for line in text.splitlines():
        m = LOG_RE.match(line)
        if not m:
            continue
        side, kind, rest = m.group(1), m.group(2), m.group(3)
        fields = {}
        for key, value in re.findall(r"(\w+)=\s*(\S+)", rest):
            if value.startswith("0x"):
                try:
                    fields[key] = int(value, 16)
                except ValueError:
                    fields[key] = value
            else:
                try:
                    fields[key] = int(value)
                except ValueError:
                    fields[key] = value
        events.append((side, kind, fields, line))
    return events


def _cyc(ev):
    value = ev[2].get("cycle")
    return value if isinstance(value, int) else -1


def _find(events, side, kind, **want):
    return [e for e in events
            if e[0] == side and e[1] == kind
            and all(e[2].get(k) == v for k, v in want.items())]


def _after(events, side, kind, line, cycle):
    return [e for e in _find(events, side, kind, line=line)
            if _cyc(e) > cycle]


def check_log(case_id, events):
    """缓存日志的独立断言（CACHE-08/17/19/20）。"""
    fails = []
    icmds = [e for e in events if e[0] == "icache" and e[1] == "cmd"]
    dcmds = [e for e in events if e[0] == "dcache" and e[1] == "cmd"]

    # 1. I|clean 是 no-op：核不得把 clean 发给 I 侧（CACHE-19）。
    bad = [e for e in icmds if e[2].get("op") == 1]
    if bad:
        fails.append("%d I|clean command(s) reached the icache" % len(bad))

    if case_id == "arch-cache-001":
        pa_d = oracle.RTL_PA_D
        pa_out = oracle.RTL_PA_OUT
        pa_code = oracle.RTL_PA_CODE
        # 2. 代码行：D clean 写回、I invalidate 发出、其后的取指 missing。
        d_clean = _find(events, "dcache", "cmd", op=1, scope=1,
                        line=pa_code, wb=1)
        if not d_clean:
            fails.append("no dcache clean-with-writeback for the code line")
        i_inval = _find(events, "icache", "cmd", op=2, scope=1, line=pa_code)
        if not i_inval:
            fails.append("no icache invalidate of the code line")
        if d_clean and i_inval:
            if not (_cyc(d_clean[0]) < _cyc(i_inval[0])):
                fails.append("the icache invalidate is not after the D clean")
            if not _after(events, "icache", "miss", pa_code,
                          _cyc(i_inval[0])):
                fails.append("the fetch after I|invalidate did not miss")
        # 3. D|flush|single 写回并删除：后续 D 读同一行必须 miss。
        flushes = _find(events, "dcache", "cmd", op=3, scope=1, line=pa_d)
        if not flushes:
            fails.append("no dcache flush of the D line")
        elif not [e for e in _find(events, "dcache", "cmd", op=3, scope=1,
                                   line=pa_d, wb=1)]:
            fails.append("the D flush did not write the line back")
        elif not _after(events, "dcache", "miss", pa_d, _cyc(flushes[0])):
            fails.append("the D read after flush did not miss "
                         "(line was not dropped)")
        # 4. enable=0 的该侧 D|invalidate 不发出（CACHE-08）：A_OUT 上只有
        #    启用后的那一次 invalidate-single。
        inv_out = _find(events, "dcache", "cmd", op=2, scope=1, line=pa_out)
        if len(inv_out) != 1:
            fails.append("dcache invalidate-single of the enable-test line "
                         "ran %d times, expected 1 (the enable=0 one must "
                         "not be issued)" % len(inv_out))
        # 5. 无行 PA：命令到达 cache 且报 miss（无效果、不报异常）。
        # `CACHE-18`：维护范围按完整 56 位 PA 比较，日志里的行地址不得被
        # 截断（ISS-534）。
        no_line = oracle.PA_NOLINE & ~0x3F
        mmio = _find(events, "dcache", "cmd", op=2, scope=1, line=no_line)
        if not mmio:
            fails.append("the no-line invalidate did not reach the dcache")
        elif mmio[0][2].get("miss") != 1:
            fails.append("the no-line invalidate was not reported as a miss")

    if case_id == "arch-cache-002":
        pa_r0, pa_r1 = oracle.RTL_PA_R0, oracle.RTL_PA_R1
        pa_d, pa_out = oracle.RTL_PA_D, oracle.RTL_PA_OUT
        for pa, name in ((pa_r0, "R0"), (pa_r1, "R1")):
            if not _find(events, "dcache", "cmd", op=2, scope=2, line=pa):
                fails.append("range invalidate did not enumerate %s" % name)
            if not _find(events, "dcache", "cmd", op=1, scope=2, line=pa,
                         wb=1):
                fails.append("range clean did not write %s back" % name)
            if not _find(events, "dcache", "cmd", op=3, scope=2, line=pa,
                         wb=1):
                fails.append("range flush did not write %s back" % name)
        # 区间外的行不得被区间命令枚举（CACHE-17 的边界）。
        if _find(events, "dcache", "cmd", scope=2, line=pa_out):
            fails.append("a range command enumerated the out-of-range line")
        # all：invalidate 丢弃、clean/flush 写回，flush 后读 miss。
        if not _find(events, "dcache", "cmd", op=2, scope=0):
            fails.append("no dcache invalidate-all enumeration")
        if not _find(events, "dcache", "cmd", op=1, scope=0, line=pa_d,
                     wb=1):
            fails.append("clean-all did not write the D line back")
        fl_all = _find(events, "dcache", "cmd", op=3, scope=0, line=pa_d,
                       wb=1)
        if not fl_all:
            fails.append("flush-all did not write the D line back")
        elif not _after(events, "dcache", "miss", pa_d, _cyc(fl_all[0])):
            fails.append("the D read after flush-all did not miss")
    return fails


# ---------------------------------------------------------------------------
def check(case_id, mode, args) -> int:
    t = tools(args)
    sim = Path(args.sim).resolve() if args.sim else DEFAULT_SIM
    if not Path(sim).is_file():
        raise SetupError("缺 RTL 仿真器: %s（--sim 或 chipyard Vast 构建）"
                         % sim)
    if mode not in oracle.CASE_MODES[case_id]:
        raise SetupError("%s 不允许 --mode %s（只有 %r）"
                         % (case_id, mode,
                            list(oracle.CASE_MODES[case_id])))
    expected = oracle.expected(case_id, _REPO)
    work = (Path(args.work_dir) if args.work_dir else
            _HERE.parent / "cache_rtl_work" / case_id / mode)
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=True)

    elf = assemble(t, case_id, mode, work)
    rc, out, log = run_sim(sim, elf, work, args.timeout)
    problems = []
    if rc == -2:
        problems.append("仿真超时（%ds）" % args.timeout)
    elif rc != 0:
        problems.append("仿真器退出码 %d" % rc)

    blob = out.read_bytes() if out.is_file() else b""
    signature = work / ("%s_%s.signature.bin" % (case_id, mode))
    signature.write_bytes(blob)
    got = None
    try:
        got = _signature.parse(blob, len(expected))
    except _signature.SignatureError as exc:
        problems.append("签名流: %s" % exc)
    else:
        problems.extend("签名流: " + p
                        for p in _signature.compare(got, expected))

    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() \
        else ""
    want_mode = oracle.mode_code(oracle.facts(_REPO), mode)
    observed = trace_mode_sequence(log, oracle.facts(_REPO)["regs"]["cfxha"]) \
        if log.is_file() else []
    mode_issue = mode_problem(observed, want_mode)
    if mode_issue:
        problems.append(mode_issue)

    problems.extend("缓存日志: " + p for p in
                    check_log(case_id, parse_cache_log(text)))

    result = {
        "case": case_id, "mode": mode, "expected_mode_code": want_mode,
        "observed_cfx_modes": observed, "exit_code": rc,
        "signature": str(signature), "signature_slots": got,
        "expected_signature": expected,
        "slot_labels": list(oracle.slot_labels(case_id)),
        "problems": problems, "log": str(log),
        "verdict": "PASS" if not problems else "FAIL",
    }
    (work / "run.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if not problems else 1


def gap(case_id, work, mode="hmon"):
    """登记 RTL 缺口，返回 77（不是 PASS）。"""
    detail = ("RTL 无 `cache-model` 机器开关（CACHE-27 把是否暴露留给实现）；"
              "%s 的 off 分支只在 QEMU/gem5 上判" % case_id)
    work = (Path(work) if work else _HERE.parent / "cache_rtl_work" / case_id)
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    (work / "run.json").write_text(
        json.dumps({"case": case_id, "verdict": "GAP", "detail": detail},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print("  GAP   %-22s %s/%s %s" % (case_id, case_id, mode, detail))
    return GAP_RC


# ---------------------------------------------------------------------------
def _arch_signature():
    import importlib.util
    path = _ARCH / "common" / "signature.py"
    spec = importlib.util.spec_from_file_location("_arch_sig_shim", path)
    if spec is None or spec.loader is None:
        raise ImportError("无法加载 %s" % path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def selfcheck() -> int:
    problems = []
    print("=" * 72)
    print("check_cache_rtl --selfcheck（不启动仿真器）")
    print("=" * 72)
    for path, what in ((PROBE, "探针"), (LDS, "链接脚本")):
        if path.is_file():
            print("  PASS  %s: %s" % (what, path.relative_to(_REPO)))
        else:
            problems.append("缺 %s: %s" % (what, path))
    try:
        f = oracle.facts(_REPO)
        oracle.rtl_build_include(_REPO)
        for case_id in CASES:
            want = oracle.expected(case_id, _REPO)
            if len(want) != len(oracle.slot_labels(case_id)):
                problems.append("%s: 期望 %d 槽 ≠ 槽名 %d"
                                % (case_id, len(want),
                                   len(oracle.slot_labels(case_id))))
        print("  PASS  cfx5 = cfxha %d；RTL 地址/PTE 现场派生；4 条 case 槽数一致"
              % f["regs"]["cfxha"])
    except oracle.OracleError as exc:
        problems.append(str(exc))

    try:
        arch_sig = _arch_signature()
        yaml_path = _HERE.with_name("expected.yaml")
        for case_id in CASES:
            want = oracle.expected(case_id, _REPO)
            listed = arch_sig.load_expected_signature(yaml_path, case_id)
            if listed is None:
                problems.append("expected.yaml 缺 %s 的 signature" % case_id)
            elif listed != want:
                problems.append("expected.yaml 的 %s 登记 ≠ 现场派生"
                                % case_id)
        print("  PASS  expected.yaml 登记 == 现场派生（%d case）" % len(CASES))
    except ImportError as exc:
        problems.append("无法加载 arch signature 薄壳: %s" % exc)

    try:
        import yaml
        index = yaml.safe_load((_REPO / "tests" / "arch.yaml").read_text(
            encoding="utf-8"))
        modes = yaml.safe_load((_REPO / "tests" / "arch" / "modes.yaml")
                               .read_text(encoding="utf-8"))["cases"]
        coverage = yaml.safe_load((_HERE.with_name("rtl-coverage.yaml"))
                                  .read_text(encoding="utf-8"))
        ids = {c.get("id") for c in index}
    except Exception as exc:                      # noqa: BLE001
        problems.append("读索引失败: %s" % exc)
    else:
        for case_id in CASES:
            if case_id not in ids:
                problems.append("tests/arch.yaml 缺 %s" % case_id)
            entry = modes.get(case_id) or {}
            if tuple(entry.get("modes") or ()) != oracle.CASE_MODES[case_id]:
                problems.append("%s 的 modes=%r ≠ %r"
                                % (case_id, entry.get("modes"),
                                   list(oracle.CASE_MODES[case_id])))
        gaps = {(c.get("case"), c.get("mode") or "hmon")
                for c in (coverage.get("cases") or [])
                if c.get("verdict") == "gap"}
        # cfx5 的 common face 已在 RTL 落地（`m16-chipyard-027`）：只剩
        # `cache-model=off` 这一机器维度没有 RTL 开关。
        want_gaps = {("arch-cache-004", "hmon")}
        missing = sorted(want_gaps - gaps)
        extra = sorted(gaps - want_gaps)
        if missing:
            problems.append("rtl-coverage.yaml 缺 gap: %r" % missing)
        if extra:
            problems.append("rtl-coverage.yaml 有未登记的 gap: %r" % extra)
        print("  PASS  arch.yaml / modes.yaml / rtl-coverage.yaml 双向核对")

    print("-" * 72)
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        print("check_cache_rtl: selfcheck FAIL（%d 项）" % len(problems))
        return 1
    print("check_cache_rtl: selfcheck PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None, choices=CASES)
    ap.add_argument("--sim", default=None)
    ap.add_argument("--mode", default="hmon", choices=tuple(TMODE))
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--signature-out", default=None)
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--root", default=None)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for case_id in CASES:
            for mode in oracle.CASE_MODES[case_id]:
                print("%s %s（CCASE=%d TMODE=%d）"
                      % (case_id, mode, CASES.index(case_id) + 1,
                         TMODE[mode]))
        return 0
    if args.selfcheck:
        return selfcheck()
    if not args.only:
        print("check_cache_rtl: --only 必填（%r）" % (CASES,), file=sys.stderr)
        return 2
    case_id = args.only
    if args.mode not in oracle.CASE_MODES[case_id]:
        print("check_cache_rtl: %s 不允许 --mode %s（只有 %r）"
              % (case_id, args.mode,
                 list(oracle.CASE_MODES[case_id])), file=sys.stderr)
        return 2
    if case_id == "arch-cache-004":
        return gap(case_id, args.work_dir, args.mode)
    try:
        rc = check(case_id, args.mode, args)
    except SetupError as exc:
        print("check_cache_rtl: SETUP: %s" % exc, file=sys.stderr)
        return 2
    work = (Path(args.work_dir) if args.work_dir else
            _HERE.parent / "cache_rtl_work" / case_id / args.mode)
    sig = work / ("%s_%s.signature.bin" % (case_id, args.mode))
    if args.signature_out and sig.is_file():
        out = Path(args.signature_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(sig.read_bytes())
    if rc == 0:
        print("check_cache_rtl: PASS（%s/%s）" % (case_id, args.mode))
    else:
        print("check_cache_rtl: FAIL（%s/%s）" % (case_id, args.mode))
    return rc


if __name__ == "__main__":
    sys.exit(main())
