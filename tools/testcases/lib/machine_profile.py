#!/usr/bin/env python3
"""machine_profile.py — 测试侧机器几何/能力的唯一读取层。

真源（三契约 + 测试侧运行布局）：

  * ``contracts/machine.yaml``      —— 机器几何（BootROM/RAM/reset_pc）、
    硬件能力（capabilities）、支持的运行模式（run_modes）；
  * ``contracts/exec-envs.yaml``    —— 执行环境 → 机型 + 引擎 + ``load.kind``；
  * ``contracts/tests-matrix.yaml`` —— 执行环境 → 套件（套件开关的唯一真源）；
  * ``tests/ee-<env>/runtime.yaml`` —— **测试侧运行布局**：entry / sp /
    image_window / kernel_base / kernel_reserved / exit_block / dump_base /
    fault_record / cfx，以及 pt_regs 转储布局的 dump_size / signature_base
    （用户裁定 2026-11-18：这些属测试资产/驱动参数，不写进
    ``contracts/machine.yaml``）。

本模块做四件事：

  * ``load(name)`` / ``all_profiles()``：按名字取合并后的 profile；
  * ``resolve(token, profile)``：把向量里的 ``@RAM_BASE`` 等符号 token
    解析为所选 profile 的 48/64 位数值；
  * ``resolve_case(case, profile)``：返回一份把几何敏感字段全部解析后的深拷贝，
    harness/validator 共用同一解析函数（禁止各写一份）；
  * ``suites(env)`` / ``suite_enabled(env, suite)``：读 ``contracts/tests-matrix.yaml``。

选择方式（驱动统一）：
  * 显式 ``--profile {tiny,vast}``；
  * 环境变量 ``DADAO_TEST_PROFILE``；
  * 缺省 ``tiny``（不改 Makefile）。

``{tiny,vast}`` 是 **FS 执行环境**（有 ``tests/ee-<env>/runtime.yaml`` 的机器环境）；
``user``（qemu-user / gem5 SE）没有 FS 几何，不在此模块。

token 语法（任务书 §3）：
  ``@RAM_BASE`` / ``@RAM_END`` / ``@SP`` / ``@BOOTROM_BASE`` / ``@ENTRY`` /
  ``@RESET_PC``，可带**单个** ``+0x…`` / ``-0x…`` 偏移。
  未解析 token、非法偏移或解析结果越 64 位 ⇒ 显式报错，绝不静默取 0。

复合计数 token（TESTCASES-092t §2）：
  ``"<count>:@TOKEN[+0x…|-0x…]"`` —— RA/RAS 值 = ``(count << 48) | addr``，
  ``count`` 为十进制或 ``0x…``，范围 ``0..0xFFFF``，要求 ``addr < 2^48``。
  只对带计数字段的 RA 值有语义（``ra0`` 的 RACNT、``ra1..ra63`` 的递归计数、
  MemRAS 条目值）；误用到 ``rd``/``rb``/地址字段会被 validator 拒绝（R7）。
"""
from __future__ import annotations

import copy
import os
import re
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

MACHINE_CONTRACT = os.path.join(REPO_ROOT, "contracts", "machine.yaml")
EXEC_ENVS_CONTRACT = os.path.join(REPO_ROOT, "contracts", "exec-envs.yaml")
TESTS_MATRIX_CONTRACT = os.path.join(REPO_ROOT, "contracts", "tests-matrix.yaml")


def runtime_layout_path(env):
    """``tests/ee-<env>/runtime.yaml``（测试侧运行布局）。"""
    return os.path.join(REPO_ROOT, "tests", "ee-%s" % env, "runtime.yaml")


# 有 FS 运行布局的机器环境。`user` 是 qemu-user / gem5 SE，没有 FS 几何，
# 因此 `--profile` 的取值集仍是 {tiny, vast}（与迁移前一致）。
FS_ENVS = ("tiny", "vast")

TOKEN_NAMES = ("RAM_BASE", "RAM_END", "SP", "BOOTROM_BASE", "ENTRY", "RESET_PC")
_TOKEN_RE = re.compile(
    r"^@(?P<name>[A-Z_]+)(?P<sign>[+-])?(?P<off>0[xX][0-9a-fA-F_]+)?$")
_HEX_RE = re.compile(r"^0[xX][0-9a-fA-F_]+$")
# ``<count>:@TOKEN[±0x…]``：RA/RAS 值的 (递归) 计数与地址复合写法。
_COUNT_TOKEN_RE = re.compile(
    r"^(?P<count>\d+|0[xX][0-9a-fA-F_]+):(?P<token>@.+)$")
ADDR48_MAX = 0xFFFF_FFFF_FFFF
COUNT_MAX = 0xFFFF

# 契约侧必填（contracts/machine.yaml + contracts/exec-envs.yaml）。
REQUIRED_CONTRACT_FIELDS = ("bootrom", "ram", "capabilities", "run_modes", "name")
REQUIRED_CAPABILITIES = ("ptw", "hmon", "smon", "umon", "cache", "llc")
# 测试侧运行布局必填（tests/ee-<env>/runtime.yaml）。
REQUIRED_RUNTIME_FIELDS = (
    "entry", "sp", "image_window", "kernel_base", "kernel_reserved",
    "exit_block", "dump_base", "fault_record", "cfx",
)
# pt_regs 转储布局（`spec/Kaiwu §6.2.1`，m19-testcases-002/003）：dump 区大小与
# 紧随其后的签名区基址必须成对登记、可交叉核对。Vast 的 dump 区尚未按 pt_regs
# 定义（`tests/ee-vast/runtime.yaml` 未登记这两项），因此只对下列环境强制。
REQUIRED_RUNTIME_PT_REGS_FIELDS = ("dump_size", "signature_base")
PT_REGS_DUMP_ENVS = ("tiny",)
# 合并后扁平 profile 的必填字段（三契约 + 运行布局 + 矩阵行）。
REQUIRED_PROFILE_FIELDS = (
    ("name", "machine", "engines", "load_kind", "run_modes", "capabilities",
     "bootrom_base", "bootrom_size", "reset_pc", "ram_base", "ram_size",
     "ram_end")
    + REQUIRED_RUNTIME_FIELDS + ("suites",)
)
_INT_FIELDS = (
    "bootrom_base", "bootrom_size", "reset_pc", "ram_base", "ram_size",
    "ram_end", "entry", "sp", "image_window", "kernel_base",
    "kernel_reserved", "exit_block", "dump_base", "fault_record",
    # pt_regs 转储布局（可缺省；登记时必须是整数）
    "dump_size", "signature_base",
)
# `spec/DADAO-13 §1`：cfx3 hmon 的 SRAM 基址（Tiny/Vast 同址，异常向量初值）。
# 无 monitor 的 profile 不使用该常量；执行资产（bootrom/harness）共用此值。
HMON_BASE = 0x0FFF_0000_0000

# Tiny hmon SRAM 数据页（`spec/Kaiwu §6.2`：数据 `0x0C00`–`0x0CFF`，256 B，初值 0；
# 代码区上限 `0x0C00`）。页内帧槽是**固件/框架契约**（`m19-testcases-005` 定稿，
# 固件真源 `tests/ee-tiny/cfx_hmon_tiny.S`，构建期由 `build_tiny_bootrom.py` 校验）：
#   +0x00 cause_id、+0x08 cause_ip、+0x10 cause_info、
#   +0x18 返回地址（框架可覆盖）、+0x20 保存的 rd63、+0x28 保存的 rb63。
# 这是**唯一**的宿主/asm 常量源：`machine-tiny.inc` 由本模块生成，
# `build_test_binary.py` 直接引用；消费者不得再写裸偏移。
HMON_DATA_OFF = 0x0C00
HMON_DATA_BASE = HMON_BASE + HMON_DATA_OFF
HMON_FRAME = {
    "CAUSE_ID": 0x00,
    "CAUSE_IP": 0x08,
    "CAUSE_INFO": 0x10,
    "RETURN": 0x18,
    "RD63": 0x20,
    "RB63": 0x28,
}


class ProfileError(ValueError):
    """机器 profile 缺失/非法/无法解析。"""


# pt_regs 转储区几何（`spec/Kaiwu §6.2.1`）：rd/rb/ra/rf 四组、每组 64 项、每项 8 B。
PT_REGS_BANKS = ("rd", "rb", "ra", "rf")
PT_REGS_REGS = 64
PT_REGS_SLOT = 8
PT_REGS_DUMP_SIZE = len(PT_REGS_BANKS) * PT_REGS_REGS * PT_REGS_SLOT  # 0x800


def _check_pt_regs_dump(env, data):
    """交叉核对转储区与签名区（`tests/ee-<env>/runtime.yaml` 的登记值）。

    * ``dump_size`` 与 ``signature_base`` 成对登记（缺一 ⇒ 报错，不静默取默认）；
    * ``dump_size`` 必须恰为 pt_regs 四段（rd/rb/ra/rf × 64 × 8 B = 0x800）；
    * 转储区必须整段留在 RAM 内，且不得压到签名区（`SIGNATURE` 紧随其后）。
    """
    dump_size = data.get("dump_size")
    sig = data.get("signature_base")
    if (dump_size is None) != (sig is None):
        raise ProfileError(
            "profile %r: dump_size and signature_base must be registered "
            "together (got dump_size=%r, signature_base=%r)"
            % (env, dump_size, sig))
    if dump_size is None:
        return
    if dump_size != PT_REGS_DUMP_SIZE:
        raise ProfileError(
            "profile %r: dump_size %#x != pt_regs layout %#x "
            "(rd/rb/ra/rf × 64 × 8 B)" % (env, dump_size, PT_REGS_DUMP_SIZE))
    if data["dump_base"] + dump_size - 1 > data["ram_end"]:
        raise ProfileError(
            "profile %r: dump region [%#x, %#x) outside RAM (end %#x)"
            % (env, data["dump_base"], data["dump_base"] + dump_size,
               data["ram_end"]))
    if sig % PT_REGS_SLOT:
        raise ProfileError(
            "profile %r: signature_base %#x is not 8-byte aligned" % (env, sig))
    if not (data["ram_base"] <= sig <= data["ram_end"]):
        raise ProfileError(
            "profile %r: signature_base %#x outside RAM [%#x, %#x]"
            % (env, sig, data["ram_base"], data["ram_end"]))
    if sig < data["dump_base"] + dump_size:
        raise ProfileError(
            "profile %r: signature_base %#x overlaps the dump region "
            "[%#x, %#x)" % (env, sig, data["dump_base"],
                            data["dump_base"] + dump_size))


def _read_yaml(path, what):
    if not os.path.isfile(path):
        raise ProfileError("%s not found: %s" % (what, path))
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict):
        raise ProfileError("%s: top-level must be a mapping (%s)" % (what, path))
    return doc


class Profile:
    """一个执行环境的机器 profile；字段按 YAML 名访问，另有便捷属性。"""

    def __init__(self, env, data):
        self.env = env
        self.name = env                      # 兼容旧字段：profile 名 = 环境名
        self._data = data
        for field in REQUIRED_PROFILE_FIELDS:
            if field not in data:
                raise ProfileError(
                    "profile %r missing required field %r" % (env, field))
        for field in _INT_FIELDS:
            val = data.get(field)
            if val is None:
                continue
            if not isinstance(val, int):
                raise ProfileError(
                    "profile %r field %r must be an integer or null (got %r)"
                    % (env, field, val))
        caps = data["capabilities"]
        for cap in REQUIRED_CAPABILITIES:
            if not isinstance(caps.get(cap), bool):
                raise ProfileError(
                    "profile %r capability %r must be a bool (got %r)"
                    % (env, cap, caps.get(cap)))
        if data["ram_end"] != data["ram_base"] + data["ram_size"] - 1:
            raise ProfileError(
                "profile %r: ram_end %#x != ram_base+ram_size-1 %#x"
                % (env, data["ram_end"],
                   data["ram_base"] + data["ram_size"] - 1))
        if data["kernel_base"] + data["kernel_reserved"] != data["entry"]:
            raise ProfileError(
                "profile %r: kernel_base+kernel_reserved %#x != entry %#x "
                "(kernel_base=%#x, kernel_reserved=%#x)"
                % (env, data["kernel_base"] + data["kernel_reserved"],
                   data["entry"], data["kernel_base"],
                   data["kernel_reserved"]))
        if not (data["ram_base"] <= data["kernel_base"] <= data["ram_end"]):
            raise ProfileError(
                "profile %r: kernel_base %#x outside RAM"
                % (env, data["kernel_base"]))
        if not (data["bootrom_base"] <= data["reset_pc"]
                < data["bootrom_base"] + data["bootrom_size"]):
            raise ProfileError(
                "profile %r: reset_pc %#x outside bootrom [%#x, %#x)"
                % (env, data["reset_pc"], data["bootrom_base"],
                   data["bootrom_base"] + data["bootrom_size"]))
        for field in ("entry", "sp", "exit_block", "dump_base"):
            val = data[field]
            if not (data["ram_base"] <= val <= data["ram_end"]):
                raise ProfileError(
                    "profile %r: %s %#x outside RAM [%#x, %#x]"
                    % (env, field, val, data["ram_base"], data["ram_end"]))
        fault_record = data["fault_record"]
        if fault_record is not None:
            if not isinstance(fault_record, int):
                raise ProfileError(
                    "profile %r field 'fault_record' must be an integer or null"
                    % env)
            if fault_record % 8:
                raise ProfileError(
                    "profile %r: fault_record %#x is not 8-byte aligned"
                    % (env, fault_record))
            # 16-byte record, inside RAM and strictly below the exit block so a
            # fault record can never alias the SYS_EXIT argument block or dump.
            if not (data["ram_base"] <= fault_record
                    and fault_record + 16 <= data["exit_block"]):
                raise ProfileError(
                    "profile %r: fault_record %#x+16 outside RAM below "
                    "exit_block %#x" % (env, fault_record, data["exit_block"]))
            if fault_record in (data["exit_block"], data["dump_base"]):
                raise ProfileError(
                    "profile %r: fault_record %#x collides with exit_block/"
                    "dump_base" % (env, fault_record))
        if not isinstance(data["suites"], list) or not data["suites"]:
            raise ProfileError(
                "profile %r: tests-matrix has no suite for this environment"
                % env)
        _check_pt_regs_dump(env, data)

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __contains__(self, key):
        return key in self._data

    def to_dict(self):
        """浅拷贝的扁平字段表（含 capabilities 字典与 suites 列表）。"""
        return dict(self._data)

    @property
    def machine(self):
        """QEMU/gem5 机器名（``contracts/exec-envs.yaml`` 的 engine 括号值）。"""
        return self._data["machine"]

    @property
    def ram_base(self):
        return self._data["ram_base"]

    @property
    def ram_end(self):
        return self._data["ram_end"]

    @property
    def entry(self):
        return self._data["entry"]

    @property
    def sp(self):
        return self._data["sp"]

    @property
    def bootrom_base(self):
        return self._data["bootrom_base"]

    @property
    def reset_pc(self):
        return self._data["reset_pc"]

    @property
    def exit_block(self):
        return self._data["exit_block"]

    @property
    def dump_base(self):
        return self._data["dump_base"]

    @property
    def dump_size(self):
        """pt_regs 转储区大小；未登记 pt_regs dump 的环境为 None。"""
        return self._data.get("dump_size")

    @property
    def signature_base(self):
        """签名区基址；未登记 pt_regs dump 的环境为 None。"""
        return self._data.get("signature_base")

    @property
    def image_window(self):
        return self._data["image_window"]

    @property
    def fault_record(self):
        """hmon 的 fault-record 槽地址；无 monitor 的 profile 为 None。"""
        return self._data["fault_record"]

    def token(self, name):
        """返回 @TOKEN 的数值（不做 48 位截断）。"""
        mapping = {
            "RAM_BASE": self.ram_base,
            "RAM_END": self.ram_end,
            "SP": self.sp,
            "BOOTROM_BASE": self.bootrom_base,
            "ENTRY": self.entry,
            "RESET_PC": self.reset_pc,
        }
        if name not in mapping:
            raise ProfileError("unknown machine token @%s" % name)
        return mapping[name]

    def __repr__(self):
        return "Profile(%r)" % self.env


_CACHE = None
_MATRIX_CACHE = None


def _int_field(env, prof_name, data, key, where):
    val = data.get(key)
    if val is None:
        raise ProfileError(
            "machine %r (%s): missing %r in %s" % (prof_name, env, key, where))
    if isinstance(val, bool) or not isinstance(val, int):
        raise ProfileError(
            "machine %r (%s): %r must be an integer (got %r) in %s"
            % (prof_name, env, key, val, where))
    return val


def _build_profile(env, machines, envs, matrix):
    """按 env 合并三契约 + 测试侧运行布局，返回 Profile。"""
    if env not in envs:
        raise ProfileError(
            "environment %r missing from %s" % (env, EXEC_ENVS_CONTRACT))
    entry = envs[env]
    if not isinstance(entry, dict):
        raise ProfileError("env %r must be a mapping in %s"
                           % (env, EXEC_ENVS_CONTRACT))
    machine_name_ = entry.get("machine")
    if not isinstance(machine_name_, str):
        raise ProfileError("env %r has no machine name in %s"
                           % (env, EXEC_ENVS_CONTRACT))
    load_block = entry.get("load")
    if (not isinstance(load_block, dict)
            or not isinstance(load_block.get("kind"), str)):
        raise ProfileError("env %r has no load.kind in %s"
                           % (env, EXEC_ENVS_CONTRACT))
    engines = entry.get("engines")
    if not isinstance(engines, list) or not engines:
        raise ProfileError("env %r has no engines in %s"
                           % (env, EXEC_ENVS_CONTRACT))

    # machine.yaml 的 profile 键（tiny/vast）与 env 名一致，但以 `name` 字段匹配，
    # 避免「键名巧合」成为隐式契约。
    matches = [(k, v) for k, v in machines.items()
               if isinstance(v, dict) and v.get("name") == machine_name_]
    if len(matches) != 1:
        raise ProfileError(
            "env %r machine %r must match exactly one profile in %s (got %d)"
            % (env, machine_name_, MACHINE_CONTRACT, len(matches)))
    mach_key, mach = matches[0]
    for field in REQUIRED_CONTRACT_FIELDS:
        if field not in mach:
            raise ProfileError(
                "machine %r (%s) missing required field %r in %s"
                % (mach_key, machine_name_, field, MACHINE_CONTRACT))
    bootrom, ram, caps = mach["bootrom"], mach["ram"], mach["capabilities"]
    for block, keys in ((bootrom, ("base", "size", "reset_pc")),
                        (ram, ("base", "size"))):
        if not isinstance(block, dict):
            raise ProfileError("machine %r: geometry block must be a mapping"
                               % machine_name_)
        for key in keys:
            if key not in block:
                raise ProfileError(
                    "machine %r: geometry block missing %r in %s"
                    % (machine_name_, key, MACHINE_CONTRACT))
    if not isinstance(caps, dict):
        raise ProfileError("machine %r: capabilities must be a mapping"
                           % machine_name_)
    run_modes = mach["run_modes"]
    if not isinstance(run_modes, list) or not run_modes:
        raise ProfileError("machine %r: run_modes must be a non-empty list"
                           % machine_name_)

    ram_base = _int_field(env, machine_name_, ram, "base", MACHINE_CONTRACT)
    ram_size = _int_field(env, machine_name_, ram, "size", MACHINE_CONTRACT)
    data = {
        "name": env,
        "machine": machine_name_,
        "engines": list(engines),
        "load_kind": load_block["kind"],
        "run_modes": list(run_modes),
        "capabilities": dict(caps),
        "bootrom_base": _int_field(env, machine_name_, bootrom, "base",
                                   MACHINE_CONTRACT),
        "bootrom_size": _int_field(env, machine_name_, bootrom, "size",
                                   MACHINE_CONTRACT),
        "reset_pc": _int_field(env, machine_name_, bootrom, "reset_pc",
                               MACHINE_CONTRACT),
        "ram_base": ram_base,
        "ram_size": ram_size,
        "ram_end": ram_base + ram_size - 1,
    }
    # 能力平铺（`prof["ptw"]` 等旧调用点保持不变；capabilities 仍是真源）。
    for cap in REQUIRED_CAPABILITIES:
        data[cap] = caps.get(cap)

    layout_path = runtime_layout_path(env)
    layout = _read_yaml(layout_path, "runtime layout")
    for field in REQUIRED_RUNTIME_FIELDS:
        if field not in layout:
            raise ProfileError(
                "profile %r: runtime layout %s missing required field %r"
                % (env, layout_path, field))
    for field in REQUIRED_RUNTIME_FIELDS:
        data[field] = layout[field]
    # pt_regs 转储布局字段：登记了 pt_regs dump 的环境必须给出（Vast 未启用）。
    if env in PT_REGS_DUMP_ENVS:
        for field in REQUIRED_RUNTIME_PT_REGS_FIELDS:
            if field not in layout:
                raise ProfileError(
                    "profile %r: runtime layout %s missing required field %r "
                    "(pt_regs dump layout)" % (env, layout_path, field))
    for field in REQUIRED_RUNTIME_PT_REGS_FIELDS:
        if field in layout:
            data[field] = layout[field]

    data["suites"] = list(matrix.get(env) or [])
    return Profile(env, data)


def _load_matrix():
    global _MATRIX_CACHE
    if _MATRIX_CACHE is not None:
        return _MATRIX_CACHE
    doc = _read_yaml(TESTS_MATRIX_CONTRACT, "tests matrix")
    matrix = doc.get("matrix")
    if not isinstance(matrix, dict) or not matrix:
        raise ProfileError(
            "%s: top-level must be a mapping with 'matrix'"
            % TESTS_MATRIX_CONTRACT)
    for env, suites in matrix.items():
        if not isinstance(suites, list) or not suites:
            raise ProfileError(
                "%s: env %r must list at least one suite"
                % (TESTS_MATRIX_CONTRACT, env))
    _MATRIX_CACHE = matrix
    return _MATRIX_CACHE


def all_profiles():
    """返回 {env: Profile}（首次调用读盘；缺字段/缺契约立即报错）。"""
    global _CACHE
    if _CACHE is not None:
        return dict(_CACHE)
    machines = _read_yaml(MACHINE_CONTRACT, "machine contract").get("profiles")
    if not isinstance(machines, dict) or not machines:
        raise ProfileError(
            "%s: top-level must be a mapping with 'profiles'"
            % MACHINE_CONTRACT)
    envs = _read_yaml(EXEC_ENVS_CONTRACT, "exec-envs contract").get("envs")
    if not isinstance(envs, dict) or not envs:
        raise ProfileError(
            "%s: top-level must be a mapping with 'envs'"
            % EXEC_ENVS_CONTRACT)
    matrix = _load_matrix()
    _CACHE = {env: _build_profile(env, machines, envs, matrix)
              for env in FS_ENVS}
    return dict(_CACHE)


def load(name=None):
    """按名字加载 profile；名字缺省取 DADAO_TEST_PROFILE，再缺省 tiny。"""
    profiles = all_profiles()
    if name is None:
        name = os.environ.get("DADAO_TEST_PROFILE") or "tiny"
    env = getattr(name, "env", name)
    env = str(env).strip().lower()
    if env not in profiles:
        raise ProfileError(
            "unknown machine profile %r (valid: %s)"
            % (env, ", ".join(sorted(profiles))))
    return profiles[env]


def machine_name(profile=None):
    """profile 名（或 Profile）-> QEMU `-M` 机器名；未登记 ⇒ ProfileError。"""
    prof = profile if isinstance(profile, Profile) else load(profile)
    return prof.machine


def suites(env="tiny"):
    """执行环境的套件清单（``contracts/tests-matrix.yaml`` 矩阵行）。"""
    matrix = _load_matrix()
    key = getattr(env, "env", env)
    key = str(key).strip().lower()
    if key not in matrix:
        raise ProfileError(
            "unknown execution environment %r (tests-matrix has: %s)"
            % (key, ", ".join(sorted(matrix))))
    return list(matrix[key])


def suite_enabled(env, suite):
    """该执行环境是否跑 `suite`（``inst``/``arch``/``tset/embench``/``unit/picolibc``…）。"""
    return suite in suites(env)


def _parse_int(text):
    if isinstance(text, bool):
        raise ProfileError("boolean is not a value: %r" % (text,))
    if isinstance(text, int):
        return text
    if isinstance(text, str):
        s = text.strip()
        if _HEX_RE.match(s):
            return int(s.replace("_", ""), 16)
        try:
            return int(s, 0)
        except ValueError:
            raise ProfileError("not an integer/token: %r" % (text,)) from None
    raise ProfileError("not an integer/token: %r" % (text,))


def is_token(value):
    return isinstance(value, str) and value.strip().startswith("@")


def is_count_token(value):
    """True iff ``value`` uses the ``<count>:@TOKEN`` composite form."""
    return isinstance(value, str) and _COUNT_TOKEN_RE.match(value.strip()) is not None


def _resolve_count_token(value, prof):
    """``<count>:@TOKEN[±0x…]`` -> ``(count << 48) | resolved_addr``。"""
    m = _COUNT_TOKEN_RE.match(value.strip())
    count = int(m.group("count").replace("_", ""), 0)
    if not 0 <= count <= COUNT_MAX:
        raise ProfileError(
            "count token %r: count %d outside 0..0x%X"
            % (value, count, COUNT_MAX))
    token = m.group("token")
    mt = _TOKEN_RE.match(token)
    if not mt:
        raise ProfileError(
            "malformed count token %r (expected <count>:@TOKEN[±0x…])" % value)
    addr = resolve(token, prof)
    if addr > ADDR48_MAX:
        raise ProfileError(
            "count token %r: resolved address %#x does not fit in 48 bits"
            % (value, addr))
    result = (count << 48) | addr
    if result > 0xFFFF_FFFF_FFFF_FFFF:
        raise ProfileError(
            "count token %r resolves outside 64 bits: %#x" % (value, result))
    return result


def resolve(value, profile=None):
    """解析一个 token 或普通整数/十六进制字符串。

    * 普通值原样返回整数；
    * ``@TOKEN`` / ``@TOKEN+0x…`` / ``@TOKEN-0x…`` 按 profile 解析；
    * ``<count>:@TOKEN[+0x…|-0x…]`` ⇒ ``(count << 48) | addr``（RA/RAS 值）；
    * 未解析 token 或非法偏移 ⇒ ProfileError（不静默取 0）。
    """
    prof = profile if isinstance(profile, Profile) else load(profile)
    if not isinstance(value, str):
        return _parse_int(value) if not isinstance(value, int) else value
    s = value.strip()
    if is_count_token(s):
        return _resolve_count_token(s, prof)
    if not s.startswith("@"):
        return _parse_int(s)
    m = _TOKEN_RE.match(s)
    if not m:
        raise ProfileError("malformed machine token %r (allowed: %s with one "
                           "+0x/-0x offset)"
                           % (value, ", ".join("@" + n for n in TOKEN_NAMES)))
    name = m.group("name")
    base = prof.token(name)
    signed = 0
    if m.group("sign"):
        if not m.group("off"):
            raise ProfileError("token %r has a sign but no offset" % value)
        signed = int(m.group("off").replace("_", ""), 16)
        if m.group("sign") == "-":
            signed = -signed
    result = base + signed
    if result < 0 or result > 0xFFFF_FFFF_FFFF_FFFF:
        raise ProfileError("token %r resolves outside 64 bits: %#x"
                           % (value, result))
    return result


def resolve_case(case, profile=None):
    """返回把几何敏感字段全部解析后的深拷贝。

    解析字段（任务书 §3）：``input_state.rd/rb/ra``、``input_state.memory[]``
    的 address/value、``expected_state`` 的寄存器/内存值、``expected_pc``。
    非 token 字符串/整数保持不变。
    """
    prof = profile if isinstance(profile, Profile) else load(profile)
    out = copy.deepcopy(case)
    if not isinstance(out, dict):
        return out
    for state_key in ("input_state", "expected_state"):
        state = out.get(state_key)
        if not isinstance(state, dict):
            continue
        for bank in ("rd", "rb", "ra"):
            regs = state.get(bank)
            if isinstance(regs, dict):
                for reg in list(regs):
                    regs[reg] = resolve(regs[reg], prof)
        mem = state.get("memory")
        if isinstance(mem, list):
            for entry in mem:
                if not isinstance(entry, dict):
                    continue
                if "address" in entry:
                    entry["address"] = resolve(entry["address"], prof)
                if "value" in entry:
                    entry["value"] = resolve(entry["value"], prof)
    if out.get("expected_pc") is not None:
        out["expected_pc"] = resolve(out["expected_pc"], prof)
    return out


def add_profile_argument(parser, default=None):
    """给 argparse.ArgumentParser 增加统一 ``--profile``。"""
    parser.add_argument(
        "--profile", default=default,
        choices=sorted(all_profiles()),
        help="machine profile (default: $DADAO_TEST_PROFILE or tiny)")
    return parser


def print_profiles():
    for name, prof in sorted(all_profiles().items()):
        print("%-5s machine=%s bootrom=%#x+%#x ram=%#x..%#x entry=%#x sp=%#x "
              "ptw=%s suites=%s"
              % (name, prof.machine, prof.bootrom_base, prof["bootrom_size"],
                 prof.ram_base, prof.ram_end, prof.entry, prof.sp,
                 prof["ptw"], ",".join(prof["suites"])))

if __name__ == "__main__":
    try:
        print_profiles()
    except ProfileError as exc:
        print("machine_profile: ERROR: %s" % exc, file=sys.stderr)
        raise SystemExit(1)
