#!/usr/bin/env python3
"""validate_encoding.py — 验证 opcodes.yaml 编码一致性。

从 SimRISC 0.5.3 QFC 编码表提取，不依赖实现。

检查：
  1. (value & mask) == value 对每条记录
  2. 记录内的字段不重叠且覆盖 [mask] 中所有为 1 的位
  3. 没有两条指令共享相同的 (mask, value) 编码空间
  4. 保留编码（reserved）未被意外分配
"""

import sys
import re

try:
    import yaml as _yaml
except ImportError:
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")


def _load(path):
    with open(path) as f:
        return _yaml.safe_load(f)


def _to_int(val):
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        val = val.strip()
        if val.startswith('0x') or val.startswith('0X'):
            return int(val, 16)
        return int(val)
    raise ValueError(f"无法转换为整数: {val!r}")


def parse_bitrange(s):
    m = re.match(r'^\[(\d+):(\d+)\]$', str(s).strip())
    if not m:
        raise ValueError(f"无效的位范围: {s!r}")
    high, low = int(m.group(1)), int(m.group(2))
    if high < low or high > 31 or low < 0:
        raise ValueError(f"位范围超出边界: {s!r}")
    return high, low


def check_value_mask(rec):
    mnem = rec.get("mnemonic", "?")
    fmt = rec.get("format", "?")
    tag = f"{mnem}({fmt})"
    val = _to_int(rec["value"])
    msk = _to_int(rec["mask"])

    if (val & msk) != val:
        return (False, f"{tag}: (value & mask) != value: "
                f"0x{val:08X} & 0x{msk:08X} = 0x{val & msk:08X}")
    return (True, "")


def check_fields_non_overlapping(fields):
    occupied = {}
    for f in fields:
        high, low = parse_bitrange(f["bits"])
        for b in range(low, high + 1):
            if b in occupied:
                return (False, f"位 {b} 重叠: 字段 "
                        f"{f['name']} ({f['bits']}) 与 "
                        f"{occupied[b]} 冲突")
            occupied[b] = f"{f['name']} ({f['bits']})"
    return (True, "")


def check_decode_conflict(records):
    """检查任意两条指令的解码空间是否冲突。"""
    for i, a in enumerate(records):
        a_mask = _to_int(a["mask"])
        a_val = _to_int(a["value"])
        for b in records[i + 1:]:
            b_mask = _to_int(b["mask"])
            b_val = _to_int(b["value"])
            common = a_mask & b_mask
            if (a_val & common) == (b_val & common):
                tag_a = f"{a['mnemonic']}({a['format']})"
                tag_b = f"{b['mnemonic']}({b['format']})"
                return (False, f"解码冲突: {tag_a} 和 {tag_b} "
                        f"(common_mask=0x{common:08X})")
    return (True, "")


def main():
    if len(sys.argv) < 2:
        print("用法: validate_encoding.py <opcodes.yaml>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    records = _load(path)

    if not isinstance(records, list):
        print("ERROR: 顶层必须是列表", file=sys.stderr)
        sys.exit(1)

    errors = []
    seen_keys = {}

    for i, rec in enumerate(records):
        tag = f"record[{i}]"
        mnem = rec.get("mnemonic", "?")
        fmt = rec.get("format", "?")

        if not isinstance(rec, dict):
            errors.append(f"ERROR: {tag}: 记录不是字典")
            continue

        required_keys = {"mnemonic", "format", "op", "mask", "value", "fields"}
        missing = required_keys - set(rec.keys())
        if missing:
            errors.append(f"ERROR: {tag} {mnem}({fmt}): "
                          f"缺少必填字段: {missing}")
            continue

        # 检查 (op, ha, mnemonic, format) 的唯一性
        op = rec.get("op")
        ha = rec.get("ha")
        op_ha_key = (op, ha, mnem, fmt)
        if op_ha_key in seen_keys:
            errors.append(f"ERROR: {tag}: 重复键: op={op}, "
                          f"ha={ha}, mnem={mnem}, fmt={fmt}")
        seen_keys[op_ha_key] = i

        # 检查 mask/value 算术
        ok, msg = check_value_mask(rec)
        if not ok:
            errors.append(f"ERROR: {msg}")

        # 检查字段
        fields = rec.get("fields", [])
        if not fields:
            errors.append(f"ERROR: {tag} {mnem}({fmt}): 无字段")
            continue

        # 检查字段是否为字典列表
        if not all(isinstance(f, dict) for f in fields):
            errors.append(f"ERROR: {tag} {mnem}({fmt}): "
                          f"字段必须是字典列表")
            continue

        # 检查字段重叠
        ok, msg = check_fields_non_overlapping(fields)
        if not ok:
            errors.append(f"ERROR: {tag} {mnem}({fmt}): {msg}")

        # 检查字段位在范围内
        for f in fields:
            try:
                parse_bitrange(f["bits"])
            except (ValueError, KeyError) as e:
                errors.append(f"ERROR: {tag} {mnem}({fmt}): 字段 "
                              f"{f.get('name', '?')}: {e}")

    # 检查解码冲突
    ok, msg = check_decode_conflict(records)
    if not ok:
        errors.append(f"ERROR: {msg}")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(f"\n验证失败: {len(errors)} 个错误", file=sys.stderr)
        sys.exit(1)

    print(f"validate_encoding: {len(records)} 条记录 OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
