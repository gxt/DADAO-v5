#!/usr/bin/env python3
"""`tests/arch/umon/umon_fence.py` — `fence cfxHA, immu18` 基础验证载体
（`m16-testcases-012`）。

一个载体、两个 case（`arch-umon-012` 放行面 / `arch-umon-013` 保留面），
由 `tests/arch/umon/check_fence.py` 按 `run_arch.py` 的 driver 契约调起。

## 判据来源（Independent oracle，现场派生，不写死）

  * `cfxha` 允许集与 `hb`（`immu18[17:12]`）SBZ 规则：`contracts/opcodes.yaml`
    的 `fence_ciii_cfx.legality`（`cfxha <= 5 || cfxha == 15 ||
    (cfxha >= 32 && cfxha <= 34) || cfxha >= 62`、`immu18[17:12] == 0`）；
  * 「`hb != 0` ⇒ ILLI」「保留 cfxha ⇒ ILLI」「`pred = succ = 0` 合法 no-op」：
    `spec/SimRISC-11 §5`（屏障指令）；
  * `ILLI` 的 `excp_cause_id` 值：`.tao/contracts/contract-see.md §6.1`
    （`1 << 8`，monitor 视角同步原因表）；
  * `pred`/`succ` 六位资源域的位号：`spec/SimRISC-11 §5` 的位表
    （bit0–5 = `cr`/`cw`/`ci`/`co`/`mr`/`mw`）。

期望值的唯一真源是上述派生函数；`tests/arch/umon/expected.yaml` 的
`cases[].checks[].signature` 只是登记，由 `--selfcheck` 与本模块**双向**核对。

## 载体（为什么不是 `env-*/env.S`）

本载体用 `tools/testcases/arch/node_probe_prelude.py` 现场生成 4 MiB BootROM
镜像（power → hmon 预置页表/PTW → body），不需要外部 BootROM、`llvm-mc` 或 ELF：
一个 ROM 通过 `-machine kaiwu-vast,bootrom-image=` 在 QEMU 与 gem5（经
`qemu_gem5_shim.py`）上是**同一份字节**。运行模式由 body 自己按
`tests/arch/common/env-README.md` 的同一协议切换（`cfx_hmon` 的 `<mode>` 行
`switch_run_mode` + `excp_vector` + `trap cfx_hmon`），因此 hmon/smon/umon
三种模式各跑一次同一套 probe；切换前后签名区都在 L1[3]（U+J）。

## 观测（签名流，槽 = 一个 probe）

每个 probe 写 1 槽：

  * 放行面（`arch-umon-012`）：先清零故障槽 → 执行 `fence` → 读回故障槽。
    `0` = 未异常（fence 正常执行）；若意外异常，hmon 的本地处理程序把
    `excp_cause_id` 写进该槽并 `escape` 回 `cause_ip + 4` ⇒ 槽 ≠ 0，判红。
  * 保留面（`arch-umon-013`）：同上，期望 `ILLI`。

smon/umon 下没有可装载的当前模式监视器（`common/env-README.md`「已知限制」：
step5 链不装载 `cfx_smon`；user 的同步异常需要 `cfx_umon` 的 U 页处理程序），
故保留面只在 hmon 跑（`tests/arch/modes.yaml` 显式排除并写原因）；放行面在
smon/umon 下用「fence 之后写槽」作见证，意外异常会走未装载的监视器 ⇒ 镜像
中止/短流（不是 PASS）。

## 未覆盖项

完整 cfx × 六位组合的穷举**不做**（用户 2026-11-22 裁定）；清单见
`tests/arch/README.md`「fence 基础验证未覆盖项」。

用法：
  umon_fence.py --only arch-umon-012 --mode hmon --qemu PATH \\
      [--work-dir DIR] [--signature-out PATH] [--selfcheck] [--list]
退出码：0 通过；1 判据失败；2 用法/缺件/配置错误。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ARCH = _HERE.parents[1]               # tests/arch
_REPO = _HERE.parents[3]               # 仓库根

for _sub in (("tools", "testcases", "arch"), ("tools", "testcases", "lib"),
             ("tools", "infra"), ("tests", "shared")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_ARCH) not in sys.path:
    sys.path.insert(0, str(_ARCH))

import node_probe_prelude as P          # noqa: E402
import signature as _signature          # noqa: E402
import machine_profile                   # noqa: E402

CASES = ("arch-umon-012", "arch-umon-013")
MODES = ("hmon", "smon", "umon")
CASE_MODES = {
    "arch-umon-012": ("hmon", "smon", "umon"),
    "arch-umon-013": ("hmon",),
}

# 签名区在 L1[3]（0x6000_0000..0x7fff_ffff，预置页表映射）内，不进 ROM 镜像。
SIG_BUF = 0x7000_0000
# 故障槽（`arch-umon-013` 与 hmon 下的放行面）：L1[3] 内、避开
# PT_PA(0x7ff0_0000)、FAULT_RECORD(0x7ffc_0000)、EXIT_BLOCK(0x7ffd_0000)。
FAULT_SLOT = 0x7ffb_0000
# 故障处理程序在 body 之后的固定偏移（ROM_BASE 相对；运行时按 body 长度校验）。
HAND_OFF = 0x1800
# 模式切换保存区（cfx_hmon hypv 行的向量 + switch_run_mode 原值）。
SAVE_SLOT = 0x7ffb_0100

ROM_BASE = P.ROM_BASE
TIMEOUT = 60
SIG = _signature.Emitter(P)     # word-builder 形态的签名机制（单一实现）

# `fence` 编码（`contracts/opcodes.yaml`：opc 0x79、mask 0xFF000000、
# cfxha[23:18]、immu18[17:0]）。
FENCE_OPC = 0x79
FENCE_MASK = 0xFF000000


class SetupError(RuntimeError):
    """缺件/配置错误（退出码 2）。"""


# ---------------------------------------------------------------------------
# 合约 / 规范现场解析
# ---------------------------------------------------------------------------
def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SetupError("cannot read %s: %s" % (path, exc))


def mode_codes() -> dict:
    """`spec/Kaiwu` §7.1 monitor 段编码：user/jail/supv/hypv -> 0/1/2/3。"""
    text = _read(_REPO / "spec" / "Kaiwu-测试机运行环境.md")
    m = re.search(r"`bit5:4` 为运行模式——`user`=`(\d+)`、`jail`=`(\d+)`、"
                  r"`supv`=`(\d+)`、`hypv`=`(\d+)`", text)
    if not m:
        raise SetupError("spec/Kaiwu §7.1 模式编码句未找到")
    codes = dict(zip(("user", "jail", "supv", "hypv"),
                     (int(g, 2) for g in m.groups())))
    if codes != {"user": 0, "jail": 1, "supv": 2, "hypv": 3}:
        raise SetupError("模式编码与 2 bit 编码不符: %r" % codes)
    return {"hmon": codes["hypv"], "smon": codes["supv"],
            "umon": codes["user"]}


def fence_legality() -> dict:
    """从 `contracts/opcodes.yaml` 取 fence 的合法性与编码字段。"""
    import yaml

    path = _REPO / "contracts" / "opcodes.yaml"
    try:
        data = yaml.safe_load(_read(path))
    except yaml.YAMLError as exc:
        raise SetupError("opcodes.yaml 解析失败: %s" % exc)
    entry = next((e for e in data if isinstance(e, dict)
                  and e.get("id") == "fence_ciii_cfx"), None)
    if entry is None:
        raise SetupError("opcodes.yaml 缺 fence_ciii_cfx")
    for key, want in (("opc", FENCE_OPC), ("mask", FENCE_MASK)):
        try:
            got = int(str(entry.get(key)), 16)
        except (TypeError, ValueError):
            raise SetupError("fence 的 %s 不可解析: %r" % (key, entry.get(key)))
        if got != want:
            raise SetupError("fence 的 %s=%#x 与本载体编码常量 %#x 不符"
                             % (key, got, want))
    fields = {f.get("name"): f.get("bits") for f in entry.get("fields") or []}
    if fields.get("cfxha") != "[23:18]" or fields.get("immu18") != "[17:0]":
        raise SetupError("fence 字段位域与规范不符: %r" % fields)
    legality = [str(x) for x in entry.get("legality") or []]
    cfx_rule = next((x for x in legality if "cfxha" in x), None)
    hb_rule = next((x for x in legality if "immu18[17:12]" in x), None)
    if cfx_rule is None or hb_rule is None:
        raise SetupError("fence legality 缺 cfxha/hb 规则: %r" % legality)
    return {"cfxha": cfx_rule, "hb": hb_rule}


def allowed_cfx(cfx_rule: str) -> set:
    """解析 `cfxha <= 5 || cfxha == 15 || (32..34) || cfxha >= 62` 为集合。

    只接受本任务的规则形态；文本一变就显式失败（不静默猜）。
    """
    text = cfx_rule.replace("`", "")
    specs = []
    for m in re.finditer(r"cfxha\s*(<=|==|>=)\s*(\d+)"
                         r"(?:\s*&&\s*cfxha\s*(<=|>=)\s*(\d+))?", text):
        specs.append(m.groups())
    if not specs:
        raise SetupError("fence cfxha 规则不可解析: %r" % cfx_rule)
    allowed = set()
    for op1, n1, op2, n2 in specs:
        lo, hi = 0, 63
        if op1 == "<=":
            hi = min(hi, int(n1))
        elif op1 == ">=":
            lo = max(lo, int(n1))
        else:
            lo = hi = int(n1)
        if op2:
            if op2 == "<=":
                hi = min(hi, int(n2))
            else:
                lo = max(lo, int(n2))
        allowed.update(range(lo, hi + 1))
    return allowed


def hb_is_sbz(hb_rule: str) -> bool:
    text = hb_rule.replace("`", "").replace(" ", "")
    if text != "immu18[17:12]==0":
        raise SetupError("fence hb 规则不是 SBZ: %r" % hb_rule)
    return True


def illi_cause() -> int:
    """`.tao/contracts/contract-see.md §6.1`：`ILLI` 的 excp_cause_id。"""
    text = _read(_REPO / ".tao" / "contracts" / "contract-see.md")
    m = re.search(r"^\|\s*`1 << (\d+)`\s*\|\s*`ILLI`\s*\|", text, re.M)
    if not m:
        raise SetupError("contract-see §6.1 缺 ILLI 行")
    return 1 << int(m.group(1))


def domain_bits() -> dict:
    """`spec/SimRISC-11 §5` 的 pred/succ 位表：bitN -> cr/cw/ci/co/mr/mw。"""
    text = _read(_REPO / "spec" / "SimRISC-11-核芯功能扩展指令.md")
    start = text.find("`pred`/`succ` 的位含义相同")
    end = text.find("汇编器为上述 12 个位提供同名宏")
    if start < 0 or end < 0:
        raise SetupError("spec/SimRISC-11 §5 位表未找到")
    bits = {}
    for line in text[start:end].splitlines():
        m = re.match(r"^\|\s*bit(\d)\s*\|\s*`([a-z]{2})`\s*\|", line.strip())
        if m:
            bits[int(m.group(1))] = m.group(2)
    if bits != {0: "cr", 1: "cw", 2: "ci", 3: "co", 4: "mr", 5: "mw"}:
        raise SetupError("spec/SimRISC-11 §5 资源域位表不符: %r" % bits)
    if "`pred = 0` 且 `succ = 0` 是合法的 no-op" not in text:
        raise SetupError("spec/SimRISC-11 §5 缺零掩码 no-op 句")
    if "`hb != 0` ⇒ ILLI" not in text:
        raise SetupError("spec/SimRISC-11 §5 缺 hb != 0 ⇒ ILLI 句")
    return bits


# ---------------------------------------------------------------------------
# 探针表（覆盖点见模块 docstring；完整组合不做）
# ---------------------------------------------------------------------------
def probe_table():
    """返回 [(label, cfxha, hb, pred, succ, 说明)]。

    位值由 `domain_bits()` 现场给出；本表只写「用哪个资源域的位」。
    顺序即签名槽顺序（`expected.yaml` 同一顺序登记）。
    """
    bits = domain_bits()
    name_to_bit = {name: bit for bit, name in bits.items()}
    table = []

    def add(label, cfx, dom, hb=0, why=""):
        pred = 1 << name_to_bit[dom]
        table.append((label, cfx, hb, pred, pred, why))

    # --- 放行面（arch-umon-012）-----------------------------------------
    table.append(("cfx0_zero_mask", 0, 0, 0, 0, "cfx0 = all cfx；pred=succ=0 合法 no-op"))
    table.append(("cfx0_full_mask", 0, 0, 0x3F, 0x3F, "cfx0 = all cfx；六位全选"))
    for bit in sorted(bits):
        add("domain_%s" % bits[bit], 0, bits[bit], why="资源域 %s 单一位" % bits[bit])
    for cfx, name in ((3, "hmon"), (4, "ptw"), (5, "cache"), (32, "pmem"),
                      (33, "llc"), (34, "time")):
        add("cfx%d_%s" % (cfx, name), cfx, "cr",
            why="指定 cfx（%s）" % name)
    for cfx, name in ((15, "hart"), (62, "uart"), (63, "power")):
        add("boundary_cfx%d_%s" % (cfx, name), cfx, "mw",
            why="允许集边界（%s）" % name)

    # --- 保留面（arch-umon-013）-----------------------------------------
    for cfx in (16, 17, 18):
        add("reserved_cfx%d" % cfx, cfx, "cr", why="保留集采样")
    for cfx in (6, 14, 31, 35, 61):
        add("reserved_boundary_cfx%d" % cfx, cfx, "cw",
            why="保留集边界采样")
    table.append(("hb_bit12", 0, 1, 0, 0, "hb = immu18[12] = 1（非 0）"))
    table.append(("hb_all", 0, 0x3F, 0, 0, "hb = immu18[17:12] 全 1"))
    return table


def split_table(table):
    """按 cfxha 是否在允许集拆成两个 case 的探针列表。"""
    legal = fence_legality()
    allowed = allowed_cfx(legal["cfxha"])
    hb_is_sbz(legal["hb"])
    pass_probes, fault_probes = [], []
    for entry in table:
        label, cfx, hb, pred, succ, why = entry
        if hb != 0 or cfx not in allowed:
            fault_probes.append(entry)
        else:
            pass_probes.append(entry)
    return pass_probes, fault_probes


def expected_values(probes, illi):
    """按同一合法性规则派生每槽期望：异常（hb≠0 / 保留 cfxha）⇒ ILLI，否则 0。"""
    legal = fence_legality()
    allowed = allowed_cfx(legal["cfxha"])
    hb_is_sbz(legal["hb"])
    out = []
    for label, cfx, hb, pred, succ, why in probes:
        out.append(illi if (hb != 0 or cfx not in allowed) else 0)
    return out


def case_probes(case_id):
    table = probe_table()
    pass_probes, fault_probes = split_table(table)
    if case_id == "arch-umon-012":
        return pass_probes
    if case_id == "arch-umon-013":
        return fault_probes
    raise SetupError("未知 case %r（允许 %s）" % (case_id, list(CASES)))


def fence_word(cfx, hb, pred, succ):
    if not 0 <= cfx <= 63 or not 0 <= hb <= 0x3F:
        raise SetupError("fence 字段越界 cfxha=%r hb=%r" % (cfx, hb))
    if not 0 <= pred <= 0x3F or not 0 <= succ <= 0x3F:
        raise SetupError("fence 掩码越界 pred=%r succ=%r" % (pred, succ))
    return ((FENCE_OPC << 24) | (cfx << 18) | (hb << 12)
            | (pred << 6) | succ)


# ---------------------------------------------------------------------------
# 镜像构造
# ---------------------------------------------------------------------------
def _load_rd4(rd, val):
    """固定 4 字的 64 位立即数装入（地址两遍 patch 需要固定长度）。"""
    out = [P.set_zw_rd(rd, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        out.append(P.or_w_rd(rd, wp, (val >> (16 * wp)) & 0xFFFF))
    return out


class _AddrSites:
    """记录 `_load_rd4` 装入的位置，`resolve()` 后按标签地址回填。"""

    def __init__(self):
        self.sites = []                 # [(label, word_index, rd)]

    def emit(self, seq, rd, label):
        idx = len(seq.w)
        seq.e(*_load_rd4(rd, 0))
        self.sites.append((label, idx, rd))

    def patch(self, seq, labels):
        for label, idx, rd in self.sites:
            seq.w[idx:idx + 4] = _load_rd4(rd, labels[label])


def _fault_handler():
    """hmon 同步异常：记 cause_id 到故障槽，回到 `cause_ip + 4`。"""
    seq = P.Seq()
    seq.e(P.cfx2rd(3, 5, 2, 5))         # cfx_hmon cg5 rc2 = excp_cause_id
    seq.e(P.st_o(5, 7, 0))              # [FAULT_SLOT] = cause
    seq.e(P.escape(3, 1))               # escape cfx_hmon, [cause_ip, +4]
    return seq.resolve()


def build_program(case_id, mode):
    """返回 (body words, handler words, labels)；labels 用于测试/诊断。"""
    if mode not in CASE_MODES[case_id]:
        raise SetupError("%s 不允许 --mode %s" % (case_id, mode))
    probes = case_probes(case_id)
    illi = illi_cause()
    seq = P.Seq()
    addr = _AddrSites()

    SIG.begin(seq, SIG_BUF, len(probes))

    hmon_observe = (mode == "hmon")     # hmon：读故障槽；smon/umon：直接写 0
    if hmon_observe:
        # 故障处理程序放在 body 之后的固定偏移；地址先占位，body 定长后回填
        addr.emit(seq, 22, "HANDLER")
        seq.e(P.cfx2rc(3, 3, 10, 22))   # cfx_hmon.hypv.excp_vector
        seq.e(*P.load_rb(7, FAULT_SLOT))

    if mode != "hmon":
        # 保存 cfx_hmon 的 hypv 行（向量 + switch_run_mode），收尾还原
        seq.e(P.cfx2rd(3, 3, 10, 5))
        seq.e(*P.load_rb(7, SAVE_SLOT), P.st_o(5, 7, 0))
        seq.e(P.cfx2rd(3, 3, 8, 5))
        seq.e(P.st_o(5, 7, 8))
        row = 2 if mode == "smon" else 0     # supv / user 行
        # 该模式行的收尾向量：trap cfx_hmon 回到 hypv 的 HYPV_RET
        addr.emit(seq, 6, "HYPV_RET")
        seq.e(P.cfx2rc(3, row, 10, 6))
        seq.e(*_load_rd4(6, mode_codes()["hmon"]), P.cfx2rc(3, row, 8, 6))
        # hypv 行：进入目标模式
        addr.emit(seq, 6, "MODE_ENTRY")
        seq.e(P.cfx2rc(3, 3, 10, 6))
        seq.e(*_load_rd4(6, mode_codes()[mode]), P.cfx2rc(3, 3, 8, 6))
        seq.e(P.trap(3, 0), P.swym())
        seq.mark("MODE_ENTRY")

    for label, cfx, hb, pred, succ, why in probes:
        word = fence_word(cfx, hb, pred, succ)
        if hmon_observe:
            seq.e(P.st_o(0, 7, 0))       # 清故障槽
            seq.e(word)
            seq.e(P.ld_o(5, 7, 0))
            SIG.upd(seq, 5)
        else:
            seq.e(word)
            SIG.upd(seq, 0)              # 见证：执行过 fence 才写这一槽

    if mode != "hmon":
        seq.e(P.trap(3, 0), P.swym())    # 回到 hypv（经该模式行）
        seq.mark("HYPV_RET")
        seq.e(*P.load_rb(7, SAVE_SLOT))
        seq.e(P.ld_o(5, 7, 0), P.cfx2rc(3, 3, 10, 5))
        seq.e(P.ld_o(5, 7, 8), P.cfx2rc(3, 3, 8, 5))

    SIG.dump(seq, SIG_BUF, len(probes))
    seq.e(*P.exit_seq(0))
    seq.resolve()

    body_len = 4 * len(seq.w)
    if body_len > HAND_OFF:
        raise SetupError("body %d B 超过故障处理程序偏移 0x%x"
                         % (body_len, HAND_OFF))
    labels = {name: ROM_BASE + 4 * idx for name, idx in seq.lab.items()}
    labels["HANDLER"] = ROM_BASE + HAND_OFF
    addr.patch(seq, labels)
    handler = _fault_handler() if hmon_observe else []
    return seq.w, handler, labels


def build_rom(case_id, mode):
    """返回 (4 MiB 镜像, 标签表, body 字节数)；body 大小用于模式窗口核对。"""
    body, handler, labels = build_program(case_id, mode)
    handlers = {HAND_OFF: handler} if handler else None
    return P.build_rom(body, handlers=handlers), labels, 4 * len(body)


# ---------------------------------------------------------------------------
# 运行
# ---------------------------------------------------------------------------
def _parse_cpu_log(text):
    blocks, pc = [], None
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


def run_case(case_id, mode, qemu, work, timeout=TIMEOUT):
    rom, labels, body_len = build_rom(case_id, mode)
    work.mkdir(parents=True, exist_ok=True)
    console = work / "console.bin"
    cpu_log = work / "cpu.log"
    for stale in (console, cpu_log):
        if stale.exists():
            stale.unlink()
    rom_path = work / "rom.bin"
    rom_path.write_bytes(rom)
    cmd = [str(qemu), "-machine",
           "%s,bootrom-image=%s" % (machine_profile.machine_name(P.PROFILE),
                                    rom_path),
           "-nographic",
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-chardev", "file,id=semi,path=%s" % console,
           "-d", "cpu", "-D", str(cpu_log)]
    rc, blob, _ = _signature.run(cmd, out=str(console), timeout=timeout)
    problems = []
    if rc == -2:
        problems.append("模拟器超时（%ds）" % timeout)
    elif rc != 0:
        problems.append("模拟器退出码 %d（0x%x）" % (rc, rc) if rc > 0
                        else "模拟器退出码 %d" % rc)

    probes = case_probes(case_id)
    want = expected_values(probes, illi_cause())
    got = None
    try:
        got = _signature.parse(blob, len(want))
    except _signature.SignatureError as exc:
        problems.append("签名流: %s" % exc)
    else:
        problems.extend("签名流: " + p
                        for p in _signature.compare(got, want))

    # 运行模式由模拟器现场观测（-d cpu 的 MODE:），不由 body 自述。
    blocks = []
    if cpu_log.is_file():
        blocks = _parse_cpu_log(cpu_log.read_text(encoding="utf-8",
                                                  errors="replace"))
    body_lo, body_hi = ROM_BASE, ROM_BASE + body_len
    seen = sorted({m for pc, m in blocks if body_lo <= pc < body_hi})
    if mode_codes()[mode] not in seen:
        problems.append(
            "运行模式未观测到：期望 body 窗口 [%#x,%#x) 内 MODE=%d，实际 %r"
            % (body_lo, body_hi, mode_codes()[mode], seen))

    result = {
        "case": case_id,
        "mode": mode,
        "exit_code": rc,
        "observed_body_modes": seen,
        "signature_slots": got,
        "expected_signature": want,
        "problems": problems,
        "command": cmd,
        "verdict": "PASS" if not problems else "FAIL",
    }
    (work / "run.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result, blob


# ---------------------------------------------------------------------------
# --selfcheck（不启动模拟器）
# ---------------------------------------------------------------------------
def selfcheck() -> int:
    import yaml

    problems = []
    print("=" * 72)
    print("umon_fence --selfcheck（不启动模拟器）")
    print("=" * 72)
    try:
        legal = fence_legality()
        allowed = allowed_cfx(legal["cfxha"])
        hb_is_sbz(legal["hb"])
        illi = illi_cause()
        bits = domain_bits()
    except SetupError as exc:
        print("  FAIL  合约/规范派生: %s" % exc)
        return 1
    reserved = sorted(set(range(64)) - allowed)
    print("  PASS  fence 编码: opc %#x mask %#x；允许 cfxha %s；保留 %s"
          % (FENCE_OPC, FENCE_MASK, sorted(allowed), reserved))
    print("  PASS  ILLI = %#x（contract-see §6.1）" % illi)
    print("  PASS  资源域位: %s" % bits)

    table = probe_table()
    pass_probes, fault_probes = split_table(table)
    if not pass_probes or not fault_probes:
        problems.append("探针表拆分后一侧为空")
    print("  PASS  探针表: 放行 %d 条 / 保留 %d 条（合计 %d）"
          % (len(pass_probes), len(fault_probes), len(table)))

    # 覆盖点现场统计（不写死条数）
    covered_cfx = {p[1] for p in pass_probes if p[1] != 0}
    need_cfx = {3, 4, 5, 32, 33, 34}
    if not need_cfx <= covered_cfx:
        problems.append("放行面缺指定 cfx: %r" % sorted(need_cfx - covered_cfx))
    else:
        print("  PASS  放行面覆盖指定 cfx: %s" % sorted(need_cfx))
    got_bits = set()
    for label, cfx, hb, pred, succ, why in pass_probes + fault_probes:
        for b in range(6):
            if pred & (1 << b) or succ & (1 << b):
                got_bits.add(b)
    if got_bits != set(range(6)):
        problems.append("六位资源域覆盖缺: %r" % sorted(set(range(6)) - got_bits))
    else:
        print("  PASS  六位资源域各至少 1 个组合: %s" % sorted(bits[b] for b in
                                                          sorted(got_bits)))

    # 期望清单双向核对（expected.yaml 的登记值 == 现场派生值）
    path = _ARCH / "umon" / "expected.yaml"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        print("  FAIL  读 expected.yaml: %s" % exc)
        return 1
    entries = {c.get("id"): c for c in (doc.get("cases") or [])
               if isinstance(c, dict)}
    for case_id in CASES:
        probes = case_probes(case_id)
        want = expected_values(probes, illi)
        entry = entries.get(case_id)
        if entry is None:
            problems.append("expected.yaml 缺 %s" % case_id)
            continue
        got = [int(v) for chk in entry.get("checks") or []
               for v in chk.get("signature") or []]
        if got != want:
            problems.append("%s 的 expected.yaml 签名与现场派生不一致（%d 槽 vs %d 槽）"
                            % (case_id, len(got), len(want)))
        else:
            print("  PASS  %s: expected.yaml 与现场派生一致（%d 槽）"
                  % (case_id, len(want)))
        # 每个允许模式都能构造镜像（不启动模拟器）
        for mode in CASE_MODES[case_id]:
            try:
                body, handler, _ = build_program(case_id, mode)
            except SetupError as exc:
                problems.append("%s/%s 镜像构造: %s" % (case_id, mode, exc))
                continue
            if not body:
                problems.append("%s/%s body 为空" % (case_id, mode))
            print("  PASS  %s/%s 镜像构造: body %d 字 / handler %d 字"
                  % (case_id, mode, len(body), len(handler)))

    print("-" * 72)
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        print("umon_fence: selfcheck FAIL（%d 项）" % len(problems))
        return 1
    print("umon_fence: selfcheck PASS")
    return 0


def list_cases() -> int:
    for case_id in CASES:
        for mode in CASE_MODES[case_id]:
            probes = case_probes(case_id)
            want = expected_values(probes, illi_cause())
            print("%s %-4s %2d 槽: %s" % (
                case_id, mode, len(want),
                ", ".join("%s=%#x" % (p[0], w)
                          for p, w in zip(probes, want))))
    return 0


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None)
    ap.add_argument("--mode", default="hmon", choices=MODES)
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--signature-out", default=None)
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--list", action="store_true")
    # `run_arch` 的多模式 driver 契约会附带这两个参数；本载体不需要。
    ap.add_argument("--bootrom", default=None)
    ap.add_argument("--cache-model", default=None)
    ap.add_argument("--cfx-access", default=None)
    args = ap.parse_args(argv)

    if args.list:
        return list_cases()
    if args.selfcheck:
        return selfcheck()
    if args.only not in CASES:
        print("umon_fence: 未知 case %r（允许 %s）"
              % (args.only, list(CASES)), file=sys.stderr)
        return 2
    if args.mode not in CASE_MODES[args.only]:
        print("umon_fence: %s 不允许 --mode %s（允许 %s）"
              % (args.only, args.mode, list(CASE_MODES[args.only])),
              file=sys.stderr)
        return 2
    if not args.qemu:
        print("umon_fence: --qemu 必填", file=sys.stderr)
        return 2
    if args.cfx_access:
        print("umon_fence: fence 用例不访问任何 cfx，不接受 --cfx-access: %r"
              % args.cfx_access, file=sys.stderr)
        return 2
    work = (Path(args.work_dir) if args.work_dir
            else Path(P.TMP_ROOT) / args.only / args.mode)
    work = work.resolve()
    try:
        result, blob = run_case(args.only, args.mode, args.qemu, work,
                                timeout=args.timeout)
    except SetupError as exc:
        print("umon_fence: SETUP: %s" % exc, file=sys.stderr)
        return 2

    out = (Path(args.signature_out) if args.signature_out
           else work / "signature.bin")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)

    # 顶层 PASS/FAIL 行：`run_arch` 的跨引擎 `checks_equal` 按行首比对（不 strip），
    # 故这里不缩进。
    print("%-4s %-10s %-4s rc=%s modes=%r slots=%s"
          % (result["verdict"], result["case"], args.mode,
             result["exit_code"], result["observed_body_modes"],
             result["signature_slots"]))
    if result["verdict"] != "PASS":
        for p in result["problems"]:
            print("  [FAIL] %s" % p)
        print("umon_fence: FAIL（%s / %s）" % (args.only, args.mode))
        return 1
    print("umon_fence: PASS（%s / %s）" % (args.only, args.mode))
    return 0


if __name__ == "__main__":
    sys.exit(main())
