#!/usr/bin/env python3
"""`tests/arch/cache/check_cache.py` — cfx5（`cfx_cache`）QEMU/gem5 驱动
（`m16-testcases-009`）。

四条 case 共用本驱动，与 RTL 承载（`check_cache_rtl.py`）共用**同一份**槽序与
期望（`tests/arch/cache/cache_oracle.py`）：

  * `arch-cache-001`（hmon/smon/umon，21 槽）：寄存器面 + D 单行维护 + I 侧
    取指重取 + `enable=0` 不维护 + 编码 no-op / 无行 PA 无效果 + I+D 同选
    （CACHE-21，`ISS-517`）；
  * `arch-cache-002`（hmon/smon/umon，12 槽）：D 侧范围（单行边界、区间、all）；
  * `arch-cache-003`（只 hmon，16 槽）：拒绝面（`CFXREG` + 非法命令无维护动作）；
  * `arch-cache-004`（只 hmon，15 槽，`cache-model=off`，CACHE-27）。

## 载体

Env 机制（`m16-testcases-015`/`017`）：运行模式由
`tests/arch/common/env-{hmon,smon,umon}/env.S` 负责（进入模式、栈、异常向量、
签名输出、退出），body 只写「测什么」（`cache.body.S`，汇编期 `CACHE_CASE`
选 case）。镜像布局与 `.envperm` 权限准备段的构造同
`tests/arch/common/check_mode_env.py`。

## 判据（Independent oracle，现场派生）

  1. **运行模式**：QEMU/gem5 的 `-d cpu`（shim 映射为 `--trace-cpu`）里，body
     窗口内出现的 `MODE:` 必须等于请求模式的编码（`spec/Kaiwu §7.1`）；body
     自述不作数。
  2. **签名流**：逐槽比对 `cache_oracle.expected()`（契约常量 + 激励推出的
     值）；长度不符、任一槽不等 ⇒ 非零。

I 侧「`clean` 是 no-op」在三方逐槽里不可判：QEMU 的写回会经 RAM 写自动使 TB
失效（`m16-qemu-003` 新发现①），因此「D clean 后未发 I 命令仍取到新码」在
QEMU 上恒成立。该点的独立判据由 RTL 承载的缓存日志承担（`icache` 不得出现
`op=clean` 命令、`flush` 后必须重缺失），见 `check_cache_rtl.py` 与
`expected-divergences.yaml` 的登记。

用法：
  check_cache.py --only arch-cache-001 --qemu PATH --mode hmon \\
      [--work-dir DIR] [--signature-out PATH] [--cfx-access 5]
      [--bootrom PATH] [--cache-model on|off] [--timeout N]
      [--selfcheck] [--list]

退出码：0 通过；1 判据失败；2 用法/缺件/配置错误。
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
if str(_ARCH) not in sys.path:
    sys.path.insert(0, str(_ARCH))

import machine_profile                     # noqa: E402
import paths as _paths                     # noqa: E402
import signature as _signature             # noqa: E402  真源
import cache_oracle as oracle              # noqa: E402
from common import runlimit                # noqa: E402

CASES = oracle.CASES
MODES = oracle.MODES
BODY = _HERE.with_name("cache.body.S")
ENV_INC_DIR = _ARCH / "common" / "env"     # 共享 `cfx_perm.inc`
ENV_LDS = _ARCH / "common" / "env.lds"
ENV_DIRS = {mode: _ARCH / "common" / ("env-%s" % mode) for mode in MODES}
ARCH_YAML = _REPO / "tests" / "arch.yaml"
MODES_YAML = _REPO / "tests" / "arch" / "modes.yaml"

# 签名区 / 栈 / umon 的 U 页：都在 L1[3]（0x6000_0000..0x7fff_ffff），与 umon
# 环境授予 U 位的页表项同一 512 MiB 超页；不进镜像、运行时写。cfx5 的数据行
# 取 0x7000_0000 起的同一超页（PA = VA），三模式都可访。
SIG_BUF = 0x62000000
STACK = 0x61FFF000
UBODY = 0x60000000
RANGE_SIZE = 0x1000
BODY_OFF = 0x1000
TAIL_OFF = 0x2000
PERM_OFF = 0x4000

CFX_ACCESS = []
SIG_SLOTS = 0
TIMEOUT = runlimit.DEFAULT_TIMEOUT       # 失败路径短时限（ISS-522；env 可放宽）


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


def _toolchain(bootrom_override=None):
    bin_dir = _paths.host_toolchain_bin()
    tools = {name: bin_dir / name
             for name in ("llvm-mc", "llvm-objcopy", "ld.lld")}
    for name, path in tools.items():
        if not path.is_file():
            raise SetupError("缺 %s: %s（make install-host）" % (name, path))
    bootrom = (Path(bootrom_override) if bootrom_override
               else _paths.test_artifacts_dir() / "bootrom" / "step5"
               / "bootrom_step5.bin").resolve()
    if not bootrom.is_file():
        raise SetupError("缺 Vast step5 BootROM: %s（make build-bootrom）"
                         % bootrom)
    tools["bootrom"] = bootrom
    return tools


# ---------------------------------------------------------------------------
# 镜像构造（同 `tests/arch/common/check_mode_env.py` 的 env 机制）
# ---------------------------------------------------------------------------
def _engine_is_gem5_shim(engine) -> bool:
    return str(engine).endswith(".py")


def assemble_env(mode, tools, work, octas=None):
    cmd = [str(tools["llvm-mc"]), "--triple=dadao-unknown-elf",
           "-filetype=obj", "-I", str(_REPO / "tests" / "shared" / "asm"),
           "-I", str(ENV_INC_DIR),
           "--defsym", "ENV_SIG_BUF=%#x" % SIG_BUF,
           "--defsym", "ENV_SIG_SLOTS=%d" % SIG_SLOTS,
           "--defsym", "ENV_BODY_RUN=%#x" % (
               UBODY if mode == "umon"
               else machine_profile.load("vast").entry + BODY_OFF),
           "--defsym", "ENV_STACK=%#x" % STACK,
           "--defsym", "ENV_BODY_SRC=%#x" % (machine_profile.load("vast").entry
                                             + BODY_OFF),
           "--defsym", "ENV_TAIL=%#x" % (machine_profile.load("vast").entry
                                         + TAIL_OFF)]
    for cfx in CFX_ACCESS:
        cmd += ["--defsym", "ENV_CFX_ACCESS_%d=1" % cfx]
    if octas is not None:
        cmd += ["--defsym", "ENV_COPY_OCTAS=%d" % octas]
    obj = work / ("env_%s.o" % mode)
    rc, out = _run(cmd + [str(ENV_DIRS[mode] / "env.S"), "-o", str(obj)], 60)
    if rc != 0:
        raise SetupError("llvm-mc env-%s 失败 rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-400:]))
    return obj


def assemble_body(case_id, mode, tools, work):
    inc = work / "cache_tables.inc"
    with inc.open("w", encoding="utf-8") as stream:
        oracle.emit_inc(_REPO, stream)
    obj = work / ("cache_%s.o" % case_id)
    rc, out = _run([str(tools["llvm-mc"]), "--triple=dadao-unknown-elf",
                    "-filetype=obj",
                    "-I", str(_REPO / "tests" / "shared" / "asm"),
                    "-I", str(ENV_INC_DIR),
                    "-I", str(work),
                    "--defsym", "CACHE_CASE=%d"
                    % (CASES.index(case_id) + 1),
                    "--defsym", "ENV_SIG_BUF=%#x" % SIG_BUF,
                    "--defsym", "ENV_SIG_SLOTS=%d" % SIG_SLOTS,
                    "--defsym", "ENV_BODY_RUN=%#x" % (
                        UBODY if mode == "umon"
                        else machine_profile.load("vast").entry + BODY_OFF),
                    str(BODY), "-o", str(obj)], 60)
    if rc != 0:
        raise SetupError("llvm-mc body 失败 rc=%d: %s"
                         % (rc, out.decode("utf-8", "replace")[-400:]))
    return obj


def section_size(tools, obj, section, work, name):
    out = work / name
    rc, log = _run([str(tools["llvm-objcopy"]), "-O", "binary",
                    "--only-section=" + section, str(obj), str(out)], 60)
    if rc != 0:
        raise SetupError("llvm-objcopy %s 失败 rc=%d: %s"
                         % (section, rc, log.decode("utf-8", "replace")[-400:]))
    return out.stat().st_size


def build_image(case_id, mode, tools, work):
    entry = machine_profile.load("vast").entry
    body_obj = assemble_body(case_id, mode, tools, work)
    env_obj = assemble_env(mode, tools, work)
    if mode == "umon":
        tail = section_size(tools, env_obj, ".envtail", work, "tail.bin")
        octas = (TAIL_OFF - BODY_OFF + tail + 7) // 8
        env_obj = assemble_env(mode, tools, work, octas=octas)
    elf = work / ("case_%s_%s.elf" % (case_id, mode))
    rc, out = _run([str(tools["ld.lld"]), "-T", str(ENV_LDS),
                    "--defsym", "ENTRY=%#x" % entry,
                    "--defsym", "ENV_BODY_OFF=%#x" % BODY_OFF,
                    "--defsym", "ENV_TAIL_OFF=%#x" % TAIL_OFF,
                    "--defsym", "ENV_PERM_OFF=%#x" % PERM_OFF,
                    str(env_obj), str(body_obj), "-o", str(elf)], 60)
    if rc != 0:
        raise SetupError("ld.lld %s/%s 失败 rc=%d: %s"
                         % (case_id, mode, rc,
                            out.decode("utf-8", "replace")[-400:]))
    image = work / ("case_%s_%s.bin" % (case_id, mode))
    rc, out = _run([str(tools["llvm-objcopy"]), "-O", "binary", str(elf),
                    str(image)], 60)
    if rc != 0:
        raise SetupError("llvm-objcopy 失败 rc=%d: %s"
                         % (rc, out.decode("utf-8", "replace")[-400:]))
    return image


def parse_cpu_log(text):
    """`(pc, mode)` 列表（QEMU `-d cpu` / shim 的 `--trace-cpu` 同格式）。"""
    blocks = []
    pc = None
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^PC: ([0-9a-fA-F]+)$", line)
        if m:
            pc = int(m.group(1), 16)
            continue
        m = re.match(r"^MODE: (\d+)$", line)
        if m and pc is not None:
            blocks.append((pc, int(m.group(1))))
            pc = None
    return blocks


def body_window(mode: str) -> tuple:
    base = UBODY if mode == "umon" else \
        machine_profile.load("vast").entry + BODY_OFF
    return base, base + RANGE_SIZE


def run_mode(case_id, mode, args, tools, work):
    f = oracle.facts(_REPO)
    expected = oracle.expected(case_id, _REPO)
    image = build_image(case_id, mode, tools, work)
    console = work / ("%s_%s.console" % (case_id, mode))
    cpu_log = work / ("%s_%s.cpu.log" % (case_id, mode))
    for stale in (console, cpu_log):
        if stale.exists():
            stale.unlink()
    lo, hi = body_window(mode)
    machine = "kaiwu-vast,bootrom-image=" + str(tools["bootrom"])
    if args.cache_model == "on":
        machine += ",cache-model=on"
    cmd = [str(args.qemu),
           "-machine", machine,
           "-kernel", str(image),
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-chardev", "file,id=semi,path=" + str(console),
           "-display", "none", "-nographic",
           "-d", "cpu", "-D", str(cpu_log)]
    cmd += runlimit.dfilter(lo, hi)
    res = runlimit.run(cmd, timeout=args.timeout, dump=cpu_log, cwd=str(work))
    rc = res.rc
    problems = []
    if res.timed_out:
        problems.append("模拟器超时（%ds）" % res.timeout)
    elif res.dump_capped:
        problems.append("`-d cpu` dump %d B 超过上限 %d B（已终止）"
                        % (res.dump_bytes, runlimit.max_dump_bytes()))
    elif rc != 0:
        problems.append("模拟器退出码 %d" % rc)

    want_mode = oracle.mode_code(f, mode)
    blocks = []
    if cpu_log.is_file():
        blocks = parse_cpu_log(cpu_log.read_text(encoding="utf-8",
                                                 errors="replace"))
    runlimit.finish_dump(cpu_log, res)
    body_modes = sorted({m for pc, m in blocks if lo <= pc < hi})
    if want_mode not in body_modes:
        problems.append(
            "运行模式未观测到：期望 body 窗口 [%#x,%#x) 内 MODE=%d，实际 %r"
            % (lo, hi, want_mode, body_modes))

    blob = console.read_bytes() if console.is_file() else b""
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

    result = {
        "case": case_id,
        "mode": mode,
        "cache_model": args.cache_model,
        "expected_mode_code": want_mode,
        "observed_body_modes": body_modes,
        "exit_code": rc,
        "timeout_s": res.timeout,
        "dump_bytes": res.dump_bytes,
        "dump_capped": res.dump_capped,
        "signature": str(signature),
        "signature_slots": got,
        "expected_signature": expected,
        "slot_labels": list(oracle.slot_labels(case_id)),
        "problems": problems,
        "command": cmd,
        "cpu_log": str(cpu_log),
        "verdict": "PASS" if not problems else "FAIL",
    }
    (work / ("run_%s_%s.json" % (case_id, mode))).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# --selfcheck（不启动模拟器）
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
    print("check_cache --selfcheck（不启动模拟器）")
    print("=" * 72)
    for mode in MODES:
        env = ENV_DIRS[mode] / "env.S"
        if env.is_file():
            print("  PASS  env 存在: %s" % env.relative_to(_REPO))
        else:
            problems.append("缺 env: %s" % env)
            print("  FAIL  缺 env: %s" % env)
    if BODY.is_file():
        print("  PASS  body 存在: %s" % BODY.relative_to(_REPO))
    else:
        problems.append("缺 body: %s" % BODY)
    if ENV_LDS.is_file():
        print("  PASS  env.lds 存在")
    else:
        problems.append("缺链接脚本: %s" % ENV_LDS)

    profile = machine_profile.load("vast")
    missing = [m for m in ("user", "supv", "hypv")
               if m not in profile.get("run_modes", [])]
    if missing:
        problems.append("vast profile 缺运行模式: %r" % missing)
    else:
        print("  PASS  vast 支持 user/supv/hypv（三模式可进入）")

    try:
        f = oracle.facts(_REPO)
    except oracle.OracleError as exc:
        problems.append(str(exc))
        f = None
    else:
        print("  PASS  判据现场派生（cfx5 面 / CFXREG / 控制字 / 模式编码）")
        print("        cfx5 = cfxha %d，pa_bits = %d，CFXREG = %#x"
              % (f["regs"]["cfxha"], f["regs"]["pa_bits"], f["cfxreg"]))

    if f is not None:
        for case_id in CASES:
            try:
                want = oracle.expected(case_id, _REPO)
            except oracle.OracleError as exc:
                problems.append(str(exc))
                continue
            if len(want) != len(oracle.slot_labels(case_id)):
                problems.append("%s: 期望 %d 槽 ≠ 槽名 %d"
                                % (case_id, len(want),
                                   len(oracle.slot_labels(case_id))))
            else:
                print("  PASS  %s 期望 %d 槽（现场派生）"
                      % (case_id, len(want)))

        try:
            arch_sig = _arch_signature()
            yaml_path = _HERE.with_name("expected.yaml")
            for case_id in CASES:
                want = oracle.expected(case_id, _REPO)
                listed = arch_sig.load_expected_signature(yaml_path, case_id)
                if listed is None:
                    problems.append("expected.yaml 缺 %s 的 signature"
                                    % case_id)
                elif listed != want:
                    problems.append(
                        "expected.yaml 的 %s 登记 %r ≠ 现场派生 %r"
                        % (case_id, listed, want))
            if not problems:
                print("  PASS  expected.yaml 登记 == 现场派生（%d case）"
                      % len(CASES))
        except ImportError as exc:
            problems.append("无法加载 arch signature 薄壳: %s" % exc)

    try:
        import yaml
        index = yaml.safe_load(ARCH_YAML.read_text(encoding="utf-8"))
        modes_doc = yaml.safe_load(MODES_YAML.read_text(encoding="utf-8"))
        ids = {c.get("id") for c in index}
        modes_cases = modes_doc.get("cases") or {}
    except Exception as exc:                      # noqa: BLE001
        problems.append("读索引失败: %s" % exc)
    else:
        for case_id in CASES:
            if case_id not in ids:
                problems.append("tests/arch.yaml 缺 %s" % case_id)
            entry = modes_cases.get(case_id)
            if not isinstance(entry, dict):
                problems.append("tests/arch/modes.yaml 缺 %s" % case_id)
                continue
            if tuple(entry.get("modes") or ()) != oracle.CASE_MODES[case_id]:
                problems.append("%s 的 modes=%r ≠ 驱动支持集 %r"
                                % (case_id, entry.get("modes"),
                                   list(oracle.CASE_MODES[case_id])))
            model = entry.get("cache_model")
            if model != oracle.CASE_CACHE_MODEL[case_id]:
                problems.append("%s 的 cache_model=%r ≠ %r"
                                % (case_id, model,
                                   oracle.CASE_CACHE_MODEL[case_id]))
        print("  PASS  arch.yaml / modes.yaml 条目与驱动支持集双向核对")

    print("-" * 72)
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        print("check_cache: selfcheck FAIL（%d 项）" % len(problems))
        return 1
    print("check_cache: selfcheck PASS")
    return 0


# ---------------------------------------------------------------------------
def main() -> int:
    global CFX_ACCESS, SIG_SLOTS
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None, choices=CASES)
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--mode", default="hmon", choices=MODES)
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--signature-out", default=None)
    ap.add_argument("--timeout", type=int, default=None,
                    help="模拟器时限（秒）；缺省 = $DADAO_ARCH_TIMEOUT 或 %d"
                         % TIMEOUT)
    ap.add_argument("--cfx-access", default=None,
                    help="modes.yaml 的 cfx_access（cfxha 逗号列表）")
    ap.add_argument("--bootrom", default=None,
                    help="Vast step5 BootROM（缺省 = 安装根的 bootrom/step5）")
    ap.add_argument("--cache-model", default="on", choices=("on", "off"))
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for case_id in CASES:
            for mode in oracle.CASE_MODES[case_id]:
                print("%s %s（%s，cache-model=%s）"
                      % (case_id, mode, BODY.name,
                         oracle.CASE_CACHE_MODEL[case_id]))
        return 0
    if args.selfcheck:
        return selfcheck()
    if not args.qemu:
        print("check_cache: --qemu 必填", file=sys.stderr)
        return 2
    if not args.only:
        print("check_cache: --only 必填（%r）" % (CASES,), file=sys.stderr)
        return 2
    case_id = args.only
    if args.mode not in oracle.CASE_MODES[case_id]:
        print("check_cache: %s 不允许 --mode %s（只有 %r）"
              % (case_id, args.mode, list(oracle.CASE_MODES[case_id])),
              file=sys.stderr)
        return 2
    if args.cache_model != oracle.CASE_CACHE_MODEL[case_id]:
        print("check_cache: %s 的机器维度是 cache-model=%s（CACHE-27）；"
              "收到 %r" % (case_id, oracle.CASE_CACHE_MODEL[case_id],
                           args.cache_model), file=sys.stderr)
        return 2
    # 引擎以 work 为 cwd 启动 ⇒ 相对路径会解析到别处：统一成绝对路径。
    args.qemu = str(Path(args.qemu).resolve())
    if args.timeout is None:
        args.timeout = runlimit.timeout()
    expected = oracle.expected(case_id, _REPO)
    SIG_SLOTS = len(expected)

    CFX_ACCESS = [5]
    if args.cfx_access:
        try:
            CFX_ACCESS = [int(x) for x in args.cfx_access.split(",")
                          if x.strip()]
        except ValueError:
            print("check_cache: --cfx-access 须是 cfxha 逗号列表: %r"
                  % args.cfx_access, file=sys.stderr)
            return 2
        bad = [c for c in CFX_ACCESS if c < 0 or c > 63]
        if bad:
            print("check_cache: --cfx-access 含越界 cfxha: %r" % bad,
                  file=sys.stderr)
            return 2

    work = (Path(args.work_dir) if args.work_dir else
            _paths.test_artifacts_dir() / "arch" / "cache" / case_id
            / args.mode)
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    try:
        tools = _toolchain(args.bootrom)
        result = run_mode(case_id, args.mode, args, tools, work)
    except SetupError as exc:
        print("check_cache: SETUP: %s" % exc, file=sys.stderr)
        return 2
    except runlimit.RunLimitError as exc:
        print("check_cache: SETUP: %s" % exc, file=sys.stderr)
        return 2

    out = Path(args.signature_out) if args.signature_out else \
        work / ("%s_%s.signature.bin" % (case_id, args.mode))
    src = Path(result["signature"])
    if src != out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(src.read_bytes())

    print("  %-4s %-16s %-4s rc=%s modes=%r sig=%s"
          % (result["verdict"], case_id, args.mode, result["exit_code"],
             result["observed_body_modes"], result["signature_slots"]))
    if result["verdict"] != "PASS":
        for p in result["problems"]:
            print("  [FAIL] %s" % p)
        print("check_cache: FAIL（%s/%s）" % (case_id, args.mode))
        return 1
    print("check_cache: PASS（%s/%s）" % (case_id, args.mode))
    return 0


if __name__ == "__main__":
    sys.exit(main())
