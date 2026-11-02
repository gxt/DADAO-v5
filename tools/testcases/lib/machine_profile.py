#!/usr/bin/env python3
"""machine_profile.py — 测试侧机器几何的唯一读取层（TESTCASES-091t）。

真源：``tests/shared/machine-profiles.yaml``。本模块只做三件事：

  * ``load(name)`` / ``all_profiles()``：按名字取 profile；
  * ``resolve(token, profile)``：把向量里的 ``@RAM_BASE`` 等符号 token
    解析为所选 profile 的 48/64 位数值；
  * ``resolve_case(case, profile)``：返回一份把几何敏感字段全部解析后的深拷贝，
    harness/validator 共用同一解析函数（禁止各写一份）。

选择方式（驱动统一）：
  * 显式 ``--profile {tiny,node}``；
  * 环境变量 ``DADAO_TEST_PROFILE``；
  * 缺省 ``tiny``（不改 Makefile）。

token 语法（任务书 §3）：
  ``@RAM_BASE`` / ``@RAM_END`` / ``@SP`` / ``@BOOTROM_BASE`` / ``@ENTRY`` /
  ``@RESET_PC``，可带**单个** ``+0x…`` / ``-0x…`` 偏移。
  未解析 token、非法偏移或解析结果越 64 位 ⇒ 显式报错，绝不静默取 0。
"""
from __future__ import annotations

import copy
import os
import re
import sys

import yaml

PROFILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))),
    "tests", "shared", "machine-profiles.yaml")

TOKEN_NAMES = ("RAM_BASE", "RAM_END", "SP", "BOOTROM_BASE", "ENTRY", "RESET_PC")
_TOKEN_RE = re.compile(
    r"^@(?P<name>[A-Z_]+)(?P<sign>[+-])?(?P<off>0[xX][0-9a-fA-F_]+)?$")
_HEX_RE = re.compile(r"^0[xX][0-9a-fA-F_]+$")
REQUIRED_FIELDS = (
    "bootrom_base", "bootrom_size", "reset_pc", "bootrom_load",
    "ram_base", "ram_size", "ram_end",
    "entry", "sp", "host_loader", "image_window",
    "kernel_base", "kernel_reserved",
    "ptw", "hmon", "smon", "cfx", "semihosting", "arch", "embench",
    "picolibc", "default_run_mode",
    "exit_block", "dump_base",
    "qemu_ram_base", "qemu_ram_size", "qemu_bootrom_base",
    "qemu_bootrom_size", "qemu_reset_pc",
)
_INT_FIELDS = (
    "bootrom_base", "bootrom_size", "reset_pc", "ram_base", "ram_size",
    "ram_end", "entry", "sp", "image_window", "kernel_base",
    "kernel_reserved", "exit_block", "dump_base",
    "qemu_ram_base", "qemu_ram_size", "qemu_bootrom_base",
    "qemu_bootrom_size", "qemu_reset_pc",
)


class ProfileError(ValueError):
    """机器 profile 缺失/非法/无法解析。"""


class Profile:
    """一个机器 profile；字段按 YAML 名访问，另有便捷属性。"""

    def __init__(self, name, data):
        self.name = name
        self._data = data
        for field in REQUIRED_FIELDS:
            if field not in data:
                raise ProfileError(
                    "profile %r missing required field %r in %s"
                    % (name, field, PROFILE_PATH))
        for field in _INT_FIELDS:
            val = data[field]
            if val is None:
                continue
            if not isinstance(val, int):
                raise ProfileError(
                    "profile %r field %r must be an integer or null (got %r)"
                    % (name, field, val))
        if data["ram_end"] != data["ram_base"] + data["ram_size"] - 1:
            raise ProfileError(
                "profile %r: ram_end %#x != ram_base+ram_size-1 %#x"
                % (name, data["ram_end"],
                   data["ram_base"] + data["ram_size"] - 1))
        if data["kernel_base"] + data["kernel_reserved"] != data["entry"]:
            raise ProfileError(
                "profile %r: kernel_base+kernel_reserved %#x != entry %#x"
                % (name, data["kernel_base"] + data["kernel_reserved"],
                   data["entry"]))
        if not (data["ram_base"] <= data["kernel_base"] <= data["ram_end"]):
            raise ProfileError(
                "profile %r: kernel_base %#x outside RAM"
                % (name, data["kernel_base"]))
        if not (data["bootrom_base"] <= data["reset_pc"]
                < data["bootrom_base"] + data["bootrom_size"]):
            raise ProfileError(
                "profile %r: reset_pc %#x outside bootrom [%#x, %#x)"
                % (name, data["reset_pc"], data["bootrom_base"],
                   data["bootrom_base"] + data["bootrom_size"]))
        for field in ("entry", "sp", "exit_block", "dump_base"):
            val = data[field]
            if not (data["ram_base"] <= val <= data["ram_end"]):
                raise ProfileError(
                    "profile %r: %s %#x outside RAM [%#x, %#x]"
                    % (name, field, val, data["ram_base"], data["ram_end"]))

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

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
    def image_window(self):
        return self._data["image_window"]

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
        return "Profile(%r)" % self.name


_CACHE = None


def all_profiles():
    """返回 {name: Profile}（首次调用读盘；缺字段立即报错）。"""
    global _CACHE
    if _CACHE is not None:
        return dict(_CACHE)
    if not os.path.isfile(PROFILE_PATH):
        raise ProfileError("machine profile source not found: %s" % PROFILE_PATH)
    with open(PROFILE_PATH, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict) or not isinstance(doc.get("profiles"), dict):
        raise ProfileError("%s: top-level must be a mapping with 'profiles'"
                           % PROFILE_PATH)
    _CACHE = {name: Profile(name, data)
              for name, data in doc["profiles"].items()}
    if not _CACHE:
        raise ProfileError("%s: no profiles defined" % PROFILE_PATH)
    return dict(_CACHE)


def load(name=None):
    """按名字加载 profile；名字缺省取 DADAO_TEST_PROFILE，再缺省 tiny。"""
    profiles = all_profiles()
    if name is None:
        name = os.environ.get("DADAO_TEST_PROFILE") or "tiny"
    name = str(name).strip().lower()
    if name not in profiles:
        raise ProfileError(
            "unknown machine profile %r (valid: %s)"
            % (name, ", ".join(sorted(profiles))))
    return profiles[name]


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


def resolve(value, profile=None):
    """解析一个 token 或普通整数/十六进制字符串。

    * 普通值原样返回整数；
    * ``@TOKEN`` / ``@TOKEN+0x…`` / ``@TOKEN-0x…`` 按 profile 解析；
    * 未解析 token 或非法偏移 ⇒ ProfileError（不静默取 0）。
    """
    prof = profile if isinstance(profile, Profile) else load(profile)
    if not isinstance(value, str):
        return _parse_int(value) if not isinstance(value, int) else value
    s = value.strip()
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
        print("%-5s bootrom=%#x+%#x ram=%#x..%#x entry=%#x sp=%#x ptw=%s"
              % (name, prof.bootrom_base, prof["bootrom_size"], prof.ram_base,
                 prof.ram_end, prof.entry, prof.sp, prof["ptw"]))


if __name__ == "__main__":
    try:
        print_profiles()
    except ProfileError as exc:
        print("machine_profile: ERROR: %s" % exc, file=sys.stderr)
        raise SystemExit(1)
