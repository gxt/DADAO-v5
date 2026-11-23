#!/usr/bin/env python3
"""`tests/arch/common/check_mode_env.py` — `arch-umon-011` 驱动（m16-testcases-015）。

代表用例：**cfx_umon 寄存器面**（body `umon/umon_mode_regs.body.S`）在
hmon（hypv）/ smon（supv）/ umon（user）三种运行模式下各跑一次。

判据（Independent oracle：期望值现场从 `spec/` + `.tao/contracts/` 派生，
不从 QEMU 实现反推）：

  * **运行模式**：`-d cpu` 的 `MODE:` 必须等于请求模式
    （模式编码取自 `spec/Kaiwu` §7.1 monitor 段编码），且该 MODE 至少出现在
    body 的执行窗口内（hmon/smon：`ENTRY+0x1000`；umon：`0x6000_0000`）。
  * **签名流**：8 槽，逐槽比对（槽位含义见 body 头注释）：
      槽 0 暂存寄存器写后回读（输入值 0x0123456789ABCDEF，`DADAO-12 §3.7`）
      槽 1 `cg8 rc1` 异步来源掩码初值全 1（`contract-see` §3，`ADR-0061` D5）
      槽 2 `cfx_id`（cg4 rc0）= cfx_umon 的 cfxha（`DADAO-12 §3.5`/§1）
      槽 3 第二个暂存寄存器 cg6.rc1 写后回读（`§3.5`：暂存寄存器至少 2）
            —— 槽 2/3 与交付方式无关（m16-testcases-017 起替换原入口 trap 现场）
      槽 4..7 cg7 space[0] = 0（`cfx0` 没有内部空间：`spec/Kaiwu` §1、`DADAO-12 §3.8`）
  * 退出码 0（`SYS_EXIT(0)`）；环境自己的 fail-closed 退出码（`0xE0`/`0xE1`）
    不是 PASS。

接口（`run_arch.py` 的 driver 契约）：

    check_mode_env.py --only arch-umon-011 --qemu PATH --mode hmon \\
        [--work-dir DIR] [--signature-out PATH] [--selfcheck] [--list]

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
if str(_ARCH) not in sys.path:
    sys.path.insert(0, str(_ARCH))

import machine_profile                     # noqa: E402
import paths as _paths                     # noqa: E402
import signature as _signature             # noqa: E402  真源

CASE_ID = "arch-umon-011"
MODES = ("hmon", "smon", "umon")
BODY = _ARCH / "umon" / "umon_mode_regs.body.S"
ENV_INC_DIR = _ARCH / "common" / "env"   # `-I` 传进去给共享 `cfx_perm.inc`
ENV_LDS = _ARCH / "common" / "env.lds"
ENV_DIRS = {mode: _ARCH / "common" / ("env-%s" % mode) for mode in MODES}
ARCH_YAML = _REPO / "tests" / "arch.yaml"
MODES_YAML = _REPO / "tests" / "arch" / "modes.yaml"

SIG_SLOTS = 8
# 签名区 / 栈 / umon 的 U 页都在 L1[3]（VA/PA 0x6000_0000..0x7fff_ffff），
# 与 umon 环境授予 U 位的页表项同一 512 MiB 超页；不进镜像、运行时写。
SIG_BUF = 0x62000000
STACK = 0x61FFF000
UBODY = 0x60000000
RANGE_SIZE = 0x1000                    # env / body / tail 各自的窗口

BODY_OFF = 0x1000
TAIL_OFF = 0x2000
PERM_OFF = 0x4000                      # cfx 权限准备段（`.envperm`，不拷进 U 页）
SCRATCH_PATTERN = 0x0123456789ABCDEF   # body 写进 cg6.rc0 的输入值
SCRATCH_PATTERN2 = 0xFEDCBA9876543210  # body 写进 cg6.rc1 的输入值


class SetupError(RuntimeError):
    """缺件/配置错误（退出码 2）。"""


# 用例在 `tests/arch/modes.yaml` 声明的 `cfx_access`（cfxha 列表），由
# `--cfx-access` 传入；驱动逐 cfx 产 `--defsym ENV_CFX_ACCESS_<cfxha>=1`
# 交给环境做权限准备（m16-testcases-017）。
CFX_ACCESS = []


def _toolchain(bootrom_override=None):
    bin_dir = _paths.host_toolchain_bin()
    tools = {name: bin_dir / name
             for name in ("llvm-mc", "llvm-objcopy", "ld.lld")}
    for name, path in tools.items():
        if not path.is_file():
            raise SetupError("缺 %s: %s（make install-host）" % (name, path))
    bootrom = (Path(bootrom_override) if bootrom_override
               else _paths.test_artifacts_dir() / "bootrom" / "step5"
               / "bootrom_step5.bin")
    if not bootrom.is_file():
        raise SetupError("缺 Vast step5 BootROM: %s（make build-bootrom）"
                         % bootrom)
    tools["bootrom"] = bootrom
    return tools


# ---------------------------------------------------------------------------
# 期望值（现场派生）
# ---------------------------------------------------------------------------
def mode_codes(root: Path) -> dict:
    """`spec/Kaiwu` §7.1 monitor 段编码：user/jail/supv/hypv -> 0/1/2/3。"""
    text = (root / "spec" / "Kaiwu-测试机运行环境.md").read_text(encoding="utf-8")
    m = re.search(r"`bit5:4` 为运行模式——`user`=`(\d+)`、`jail`=`(\d+)`、"
                  r"`supv`=`(\d+)`、`hypv`=`(\d+)`", text)
    if not m:
        raise SetupError("spec/Kaiwu §7.1 模式编码句未找到")
    # 该句用 2 bit 二进制写法（`10` = supv、`11` = hypv），按 base 2 解析；
    # `-d cpu` 的 `MODE:` 是同一编码的十进制值。
    codes = dict(zip(("user", "jail", "supv", "hypv"),
                     (int(g, 2) for g in m.groups())))
    if codes != {"user": 0, "jail": 1, "supv": 2, "hypv": 3}:
        raise SetupError("模式编码与 2 bit 编码不符: %r" % codes)
    return codes


def cfx_umon_code(root: Path) -> int:
    """`DADAO-12 §1` 的 cfxha 表：`cfx_umon` 的编码（= cfx_id 期望值）。"""
    text = (root / "spec" / "DADAO-12-SEE-主管系统运行环境.md").read_text(
        encoding="utf-8")
    m = re.search(r"\|\s*(\d+)\s*\|\s*umon\s*\|[^|]*user 模式", text)
    if not m:
        raise SetupError("DADAO-12 §1 cfxha 表缺 umon 行")
    return int(m.group(1))


def expected_signature(root: Path) -> list:
    """8 槽期望值（每槽来源见模块 docstring）。

    m16-testcases-017：槽 2/3 换成**与交付方式无关**的观测量（cfx_id 与第二个
    暂存寄存器写后回读）；原来的 `excp_prev_run_mode`/`excp_cause_id` 读的是
    「入口 trap」现场，而交付已改为 hmon 直接跳转（没有 trap）。
    """
    see = (root / ".tao" / "contracts" / "contract-see.md").read_text(
        encoding="utf-8")
    if not re.search(r"`cfx0`–`cfx3` 的 `cg8 rc1`（异步来源掩码）初值全 1", see):
        raise SetupError("contract-see §3 缺 cg8 rc1 异步来源掩码初值句")
    kaiwu = (root / "spec" / "Kaiwu-测试机运行环境.md").read_text(
        encoding="utf-8")
    if "`cfx0` 没有内部空间" not in kaiwu:
        raise SetupError("spec/Kaiwu §1 缺「cfx0 没有内部空间」")
    spec = (root / "spec" / "DADAO-12-SEE-主管系统运行环境.md").read_text(
        encoding="utf-8")
    if "暂存寄存器数量，至少2，最多64" not in spec:
        raise SetupError("DADAO-12 §3.5 缺「暂存寄存器至少 2」")
    return [SCRATCH_PATTERN, 0xFFFFFFFFFFFFFFFF, cfx_umon_code(root),
            SCRATCH_PATTERN2, 0, 0, 0, 0]


def body_window(mode: str) -> tuple:
    base = UBODY if mode == "umon" else machine_profile.load("vast").entry + BODY_OFF
    return base, base + RANGE_SIZE


# ---------------------------------------------------------------------------
# 构建 / 运行
# ---------------------------------------------------------------------------
def _run(cmd, timeout, cwd=None):
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout,
                              stdin=subprocess.DEVNULL, cwd=cwd)
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        return -2, exc.stdout or b""


def assemble_env(mode, tools, work, octas=None):
    cmd = [str(tools["llvm-mc"]), "--triple=dadao-unknown-elf",
           "-filetype=obj", "-I", str(_REPO / "tests" / "shared" / "asm"),
           "-I", str(ENV_INC_DIR),
           "--defsym", "ENV_SIG_BUF=%#x" % SIG_BUF,
           "--defsym", "ENV_SIG_SLOTS=%d" % SIG_SLOTS,
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


def assemble_body(tools, work):
    obj = work / "umon_mode_regs.body.o"
    rc, out = _run([str(tools["llvm-mc"]), "--triple=dadao-unknown-elf",
                    "-filetype=obj",
                    "-I", str(_REPO / "tests" / "shared" / "asm"),
                    "--defsym", "ENV_SIG_BUF=%#x" % SIG_BUF,
                    "--defsym", "ENV_SIG_SLOTS=%d" % SIG_SLOTS,
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


def build_image(mode, tools, work):
    entry = machine_profile.load("vast").entry
    body_obj = assemble_body(tools, work)
    env_obj = assemble_env(mode, tools, work)
    if mode == "umon":
        tail = section_size(tools, env_obj, ".envtail", work, "tail.bin")
        # body 与 tail 相隔 0x1000；一次连续拷贝覆盖到 tail 末尾
        octas = (TAIL_OFF - BODY_OFF + tail + 7) // 8
        env_obj = assemble_env(mode, tools, work, octas=octas)
    elf = work / ("case_%s.elf" % mode)
    rc, out = _run([str(tools["ld.lld"]), "-T", str(ENV_LDS),
                    "--defsym", "ENTRY=%#x" % entry,
                    "--defsym", "ENV_BODY_OFF=%#x" % BODY_OFF,
                    "--defsym", "ENV_TAIL_OFF=%#x" % TAIL_OFF,
                    "--defsym", "ENV_PERM_OFF=%#x" % PERM_OFF,
                    str(env_obj), str(body_obj), "-o", str(elf)], 60)
    if rc != 0:
        raise SetupError("ld.lld %s 失败 rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-400:]))
    image = work / ("case_%s.bin" % mode)
    rc, out = _run([str(tools["llvm-objcopy"]), "-O", "binary", str(elf),
                    str(image)], 60)
    if rc != 0:
        raise SetupError("llvm-objcopy 失败 rc=%d: %s"
                         % (rc, out.decode("utf-8", "replace")[-400:]))
    return image


def parse_cpu_log(text):
    """`(pc, mode)` 列表（QEMU `-d cpu` 的 `PC:` / `MODE:` 行）。"""
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


def run_mode(mode, args, tools, work):
    entry = machine_profile.load("vast").entry
    image = build_image(mode, tools, work)
    console = work / ("%s.console" % mode)
    cpu_log = work / ("%s.cpu.log" % mode)
    for stale in (console, cpu_log):
        if stale.exists():
            stale.unlink()
    machine = "kaiwu-vast,bootrom-image=" + str(tools["bootrom"])
    if getattr(args, "cache_model", "off") == "on":
        machine += ",cache-model=on"
    cmd = [args.qemu,
           "-machine", machine,
           "-kernel", str(image),
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-chardev", "file,id=semi,path=" + str(console),
           "-display", "none", "-nographic",
           "-d", "cpu", "-D", str(cpu_log)]
    rc, out = _run(cmd, args.timeout, cwd=str(work))
    problems = []
    if rc == -2:
        problems.append("qemu 超时（%ds）" % args.timeout)
    elif rc != 0:
        problems.append("qemu 退出码 %d（0x%x）" % (rc, rc) if rc > 0
                        else "qemu 退出码 %d" % rc)

    codes = mode_codes(_REPO)
    want_mode = codes["hypv" if mode == "hmon" else "supv" if mode == "smon"
                      else "user"]
    blocks = []
    if cpu_log.is_file():
        blocks = parse_cpu_log(cpu_log.read_text(encoding="utf-8",
                                                 errors="replace"))
    lo, hi = body_window(mode)
    body_modes = sorted({m for pc, m in blocks if lo <= pc < hi})
    if want_mode not in body_modes:
        problems.append(
            "运行模式未观测到：期望 body 窗口 [%#x,%#x) 内 MODE=%d，实际 %r"
            % (lo, hi, want_mode, body_modes))

    want = expected_signature(_REPO)
    blob = console.read_bytes() if console.is_file() else b""
    signature = work / ("%s.signature.bin" % mode)
    signature.write_bytes(blob)
    got = None
    try:
        got = _signature.parse(blob, SIG_SLOTS)
    except _signature.SignatureError as exc:
        problems.append("签名流: %s" % exc)
    else:
        problems.extend("签名流: " + p for p in _signature.compare(got, want))

    result = {
        "case": CASE_ID,
        "mode": mode,
        "expected_mode_code": want_mode,
        "observed_body_modes": body_modes,
        "exit_code": rc,
        "signature": str(signature),
        "signature_slots": got,
        "expected_signature": want,
        "problems": problems,
        "command": cmd,
        "cpu_log": str(cpu_log),
        "verdict": "PASS" if not problems else "FAIL",
    }
    (work / ("run_%s.json" % mode)).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# --selfcheck（不启动模拟器）
# ---------------------------------------------------------------------------
def selfcheck() -> int:
    problems = []
    print("=" * 72)
    print("check_mode_env --selfcheck（%s；不启动模拟器）" % CASE_ID)
    print("=" * 72)
    for mode in MODES:
        env = ENV_DIRS[mode] / "env.S"
        if env.is_file():
            print("  PASS  env 存在: %s" % env.relative_to(_REPO))
        else:
            problems.append("缺 env: %s" % env)
            print("  FAIL  缺 env: %s" % env)
    if not BODY.is_file():
        problems.append("缺 body: %s" % BODY)
    if not ENV_LDS.is_file():
        problems.append("缺链接脚本: %s" % ENV_LDS)
    if not problems:
        print("  PASS  body / env.lds 存在")

    profile = machine_profile.load("vast")
    missing = [m for m in ("user", "supv", "hypv")
               if m not in profile.get("run_modes", [])]
    if missing:
        problems.append("vast profile 缺运行模式: %r" % missing)
    else:
        print("  PASS  vast 支持 user/supv/hypv（三模式可进入）")

    try:
        want = expected_signature(_REPO)
    except SetupError as exc:
        problems.append(str(exc))
    else:
        if len(want) != SIG_SLOTS:
            problems.append("期望签名槽数 %d ≠ %d" % (len(want), SIG_SLOTS))
        else:
            print("  PASS  期望签名现场派生: %d 槽" % len(want))

    # 用例元数据双向核对：arch.yaml 有该 id，modes.yaml 的允许集 = 本驱动支持集
    try:
        import yaml
        index = yaml.safe_load(ARCH_YAML.read_text(encoding="utf-8"))
        modes_doc = yaml.safe_load(MODES_YAML.read_text(encoding="utf-8"))
        entry = next((c for c in index if c.get("id") == CASE_ID), None)
        modes_entry = (modes_doc.get("cases") or {}).get(CASE_ID)
    except Exception as exc:                      # noqa: BLE001
        problems.append("读索引失败: %s" % exc)
    else:
        if entry is None:
            problems.append("tests/arch.yaml 缺 %s" % CASE_ID)
        if not isinstance(modes_entry, dict):
            problems.append("tests/arch/modes.yaml 缺 %s" % CASE_ID)
        elif tuple(modes_entry.get("modes") or ()) != MODES:
            problems.append("%s 的 modes=%r ≠ 驱动支持集 %r"
                            % (CASE_ID, modes_entry.get("modes"), list(MODES)))
        elif modes_entry.get("reasons"):
            problems.append("%s 三模式全允许，不应有 reasons" % CASE_ID)
        else:
            print("  PASS  modes.yaml 允许集与驱动支持集一致: %r" % (MODES,))

    print("-" * 72)
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        print("check_mode_env: selfcheck FAIL（%d 项）" % len(problems))
        return 1
    print("check_mode_env: selfcheck PASS")
    return 0


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None)
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--mode", default="hmon", choices=MODES)
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--signature-out", default=None)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--cfx-access", default=None,
                    help="modes.yaml 的 cfx_access（cfxha 逗号列表）：逐 cfx 传 "
                         "--defsym ENV_CFX_ACCESS_<cfxha>=1 给环境做权限准备")
    ap.add_argument("--bootrom", default=None,
                    help="Vast step5 BootROM（缺省 = 安装根的 bootrom/step5）")
    ap.add_argument("--cache-model", default="off", choices=("on", "off"),
                    help="`-machine kaiwu-vast,cache-model=`（m16-qemu-001）：on 时 "
                         "cfx5 的 cache_exist 读回 0b11（contract-cache CACHE-07）；"
                         "缺省 off 与旧命令行一致")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for mode in MODES:
            print("%s %s（%s）"
                  % (CASE_ID, mode, (ENV_DIRS[mode] / "env.S").relative_to(_REPO)))
        return 0
    if args.selfcheck:
        return selfcheck()
    if args.only not in (None, CASE_ID):
        print("check_mode_env: 未知 case %r（只有 %s）"
              % (args.only, CASE_ID), file=sys.stderr)
        return 2
    if not args.qemu:
        print("check_mode_env: --qemu 必填", file=sys.stderr)
        return 2
    if args.qemu.endswith(".py"):
        print("check_mode_env: gem5 shim 尚未承载本用例（只接 QEMU）; "
              "fail-closed", file=sys.stderr)
        return 2

    global CFX_ACCESS
    if args.cfx_access:
        try:
            CFX_ACCESS = [int(x) for x in args.cfx_access.split(",") if x.strip()]
        except ValueError:
            print("check_mode_env: --cfx-access 须是 cfxha 逗号列表: %r"
                  % args.cfx_access, file=sys.stderr)
            return 2
        bad = [c for c in CFX_ACCESS if c < 0 or c > 63]
        if bad:
            print("check_mode_env: --cfx-access 含越界 cfxha: %r" % bad,
                  file=sys.stderr)
            return 2

    work = (Path(args.work_dir) if args.work_dir else
            _paths.test_artifacts_dir() / "arch" / "mode_env" / args.mode)
    work = work.resolve()          # qemu 以 work 为 cwd 运行；命令参数须为绝对路径
    work.mkdir(parents=True, exist_ok=True)
    try:
        tools = _toolchain(args.bootrom)
        result = run_mode(args.mode, args, tools, work)
    except SetupError as exc:
        print("check_mode_env: SETUP: %s" % exc, file=sys.stderr)
        return 2

    out = Path(args.signature_out) if args.signature_out else \
        work / ("%s.signature.bin" % args.mode)
    src = Path(result["signature"])
    if src != out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(src.read_bytes())

    print("  %-4s %-4s rc=%s modes=%r sig=%s"
          % (result["verdict"], args.mode, result["exit_code"],
             result["observed_body_modes"], result["signature_slots"]))
    if result["verdict"] != "PASS":
        for p in result["problems"]:
            print("  [FAIL] %s" % p)
        print("check_mode_env: FAIL（mode=%s）" % args.mode)
        return 1
    print("check_mode_env: PASS（mode=%s）" % args.mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
