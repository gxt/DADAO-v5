#!/usr/bin/env python3
"""validate_vectors.py — 校验 tests/vectors 的向量 schema、覆盖率与 inventory 同步。

Spec-first：所有判定依据 `contracts/opcodes.yaml`、`contracts/legality_rules.yaml`
与 `tests/vectors/schema.md`；**不**读取 LLVM/QEMU 产物，不从实现反推。

检查项（对应 `TESTCASES-002t` 的校验内容 1–14）：
   1. 必填字段存在（`mnemonic`/`insn`/`format`/`class`/`encoding`/`input_state`/`spec_cite`）
   2. `class` ∈ {encoding, legality, semantic, boundary, overlap}
   3. `status` ∈ {active, deferred}
   4. deferred 一致性（`expected_state`/`expected_pc` 为 null，`deferred_reason` 非空）
   5. `expected_fault` ∈ {null, ILLI, UNDI, MALIGN, IALIGN, RASOF, RASUF, UNMAPPED}
   6. `encoding.word` 合法 hex 且 ≤ 0xFFFFFFFF
   7. `(insn, format)` 存在于 `opcodes.yaml` 的 M1 身份集
   8. `encoding.word` 与对应 opcode 的 `(word & mask) == value` 一致
   9. 覆盖率门控（R2：inventory 的 M1 行集 == opcodes M1 身份集，且每行声明覆盖）
  10. active semantic/boundary 必须有 `expected_state`；`rd`/`rb` 不得出现 `rd0`/`rb0`
  11. `memory.address` 为 48-bit 有效地址；`semantic` 类地址须落在 ADR-0004 RAM 区
  12. inventory 同步（R2）
  13. `expected_pc`（R4）：出现时的类型/48-bit/class 一致性
  14. F9②③④：legality `expected_state == null`；`spec_cite` 非空字符串；
      semantic memory 地址越界阻断

退出码：有错误 `exit(1)` 并列出文件 + case 序号；无错误 `exit(0)`。

注：
  - 覆盖率在 `TESTCASES-002t` 由 **inventory 覆盖矩阵**承载（本任务不含向量数据，
    数据归 `003t`~`007t`）；见 `inventory.md` 顶部说明。
  - F9①（active semantic/boundary 的 src 字段寄存器必被预置 + `orrr` shamt 守卫）
    由 `TESTCASES-003t` 追加（与 F1 数据修复同任务）。
  - `expected_pc` 的**存在性**规则由 `005t`/`006t` 追加。
"""

import glob
import os
import re
import sys

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")


ALLOWED_CLASSES = {"encoding", "legality", "semantic", "boundary", "overlap"}
ALLOWED_STATUS = {"active", "deferred"}
ALLOWED_FAULTS = {None, "ILLI", "UNDI", "MALIGN", "IALIGN",
                  "RASOF", "RASUF", "UNMAPPED"}
REQUIRED_FIELDS = ["mnemonic", "insn", "format", "class", "encoding",
                   "input_state", "spec_cite"]

# ADR-0004 D1：RAM 窗口（16 MiB）与 48-bit 有效地址上限
RAM_BASE = 0xFFFF_0000_0000
RAM_END = 0xFFFF_00FF_FFFF
ADDR48_MAX = 0xFFFF_FFFF_FFFF

HEX_RE = re.compile(r"^0x[0-9a-fA-F]+$")
REG_RE = re.compile(r"^(rd|rb|ra)\d+$")
SEP_RE = re.compile(r":?-{2,}:?")
DECL_NA = {"", "—", "-", "n/a", "na", "none"}


def _to_int(val):
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        s = val.strip()
        if s.startswith(("0x", "0X")):
            return int(s, 16)
        return int(s)
    raise ValueError("not an integer: %r" % (val,))


def _unquote(cell):
    return cell.strip().strip("`").strip()


def load_opcodes(path):
    """返回 (m1_records, by_key, duplicate_keys)。M1 判据 excluded_m1 != true。"""
    with open(path) as fh:
        records = _yaml.safe_load(fh)
    if not isinstance(records, list):
        raise ValueError("opcodes.yaml top-level must be a list")
    m1 = [r for r in records if not r.get("excluded_m1")]
    by_key = {}
    dups = []
    for rec in m1:
        key = (rec["insn"], rec["format"])
        if key in by_key:
            dups.append(key)
        by_key[key] = rec
    return m1, by_key, dups


def parse_inventory(path):
    """解析 inventory.md 中含 `insn`+`format` 表头的 Markdown 表。"""
    rows = []
    header = None
    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line.startswith("|"):
                header = None
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            low = [c.lower() for c in cells]
            if "insn" in low and "format" in low:
                header = low
                continue
            if header is None:
                continue
            if cells and all(SEP_RE.fullmatch(c) for c in cells):
                continue
            row = {header[i]: cells[i] for i in range(min(len(header), len(cells)))}
            rows.append(row)
    return rows


def _check_memory(state, tag, label, ram_required, errors):
    """校验 state.memory：元素结构、48-bit 地址、（可选）RAM 窗口。"""
    if not isinstance(state, dict):
        return
    mem = state.get("memory")
    if mem is None:
        return
    if not isinstance(mem, list):
        errors.append("%s: %s.memory must be a list" % (tag, label))
        return
    for j, ent in enumerate(mem):
        if not isinstance(ent, dict):
            errors.append("%s: %s.memory[%d] must be a mapping" % (tag, label, j))
            continue
        addr = ent.get("address")
        if not isinstance(addr, str) or not HEX_RE.match(addr.strip()):
            errors.append("%s: %s.memory[%d].address not valid hex: %r"
                          % (tag, label, j, addr))
            continue
        aval = int(addr, 16)
        if aval > ADDR48_MAX:
            errors.append("%s: %s.memory[%d].address is not a 48-bit valid "
                          "address (> 0x%x): %s"
                          % (tag, label, j, ADDR48_MAX, addr))
        if ram_required and not (RAM_BASE <= aval <= RAM_END):
            errors.append("%s: semantic %s.memory[%d].address %s outside "
                          "ADR-0004 RAM window [0x%x, 0x%x]"
                          % (tag, label, j, addr, RAM_BASE, RAM_END))


def _check_state_banks(state, tag, label, errors):
    """校验 rd/rb/ra bank：键名合法，rd/rb 不得出现 rd0/rb0。"""
    if not isinstance(state, dict):
        return
    for bank in ("rd", "rb", "ra"):
        b = state.get(bank)
        if b is None:
            continue
        if not isinstance(b, dict):
            errors.append("%s: %s.%s must be a mapping" % (tag, label, bank))
            continue
        for key in b:
            if not REG_RE.match(str(key)):
                errors.append("%s: %s.%s has invalid register key %r"
                              % (tag, label, bank, key))
            elif key in ("rd0", "rb0"):
                errors.append("%s: %s.%s must not preset %s (rd0 恒零 / rb0 为 PC)"
                              % (tag, label, bank, key))


def validate_file(filepath, by_key, m1_keys, errors):
    """校验单个向量 YAML，返回 case 数。"""
    try:
        with open(filepath) as fh:
            cases = _yaml.safe_load(fh)
    except _yaml.YAMLError as exc:
        errors.append("%s: YAML parse error: %s" % (filepath, exc))
        return 0
    if cases is None:
        return 0
    if not isinstance(cases, list):
        errors.append("%s: top-level must be a list" % filepath)
        return 0

    for i, case in enumerate(cases):
        tag = "%s case[%d]" % (filepath, i)
        if not isinstance(case, dict):
            errors.append("%s: case is not a mapping" % tag)
            continue

        for field in REQUIRED_FIELDS:
            if field not in case:
                errors.append("%s: missing required field '%s'" % (tag, field))

        mnem = case.get("mnemonic")
        insn = case.get("insn")
        fmt = case.get("format")
        cls = case.get("class")
        status = case.get("status", "active")
        fault = case.get("expected_fault")
        encoding = case.get("encoding")
        input_state = case.get("input_state")
        expected_state = case.get("expected_state")
        expected_pc = case.get("expected_pc")
        spec_cite = case.get("spec_cite")

        # 2. class / 3. status / 5. fault
        if cls not in ALLOWED_CLASSES:
            errors.append("%s: invalid class %r" % (tag, cls))
        if status not in ALLOWED_STATUS:
            errors.append("%s: invalid status %r" % (tag, status))
        if fault not in ALLOWED_FAULTS:
            errors.append("%s: invalid expected_fault %r" % (tag, fault))

        # 14(F9③). spec_cite 非空字符串
        if "spec_cite" in case and (not isinstance(spec_cite, str)
                                    or not spec_cite.strip()):
            errors.append("%s: spec_cite must be a non-empty string" % tag)

        # 7. (insn, format) 必须存在于 M1 身份集
        key = None
        if isinstance(insn, str) and isinstance(fmt, str):
            key = (insn, fmt)
            if key not in m1_keys:
                errors.append("%s: (insn, format) = (%s, %s) is not an M1 "
                              "identity in opcodes.yaml" % (tag, insn, fmt))

        # 6/8. encoding.word 合法 hex、范围、mask/value 一致
        word = None
        if encoding is not None and not isinstance(encoding, dict):
            errors.append("%s: encoding must be a mapping" % tag)
        elif isinstance(encoding, dict):
            if "word" not in encoding:
                errors.append("%s: encoding.word is required" % tag)
            word = encoding.get("word")
        if word is not None:
            if not isinstance(word, str) or not HEX_RE.match(word.strip()):
                errors.append("%s: encoding.word not valid hex: %r" % (tag, word))
            else:
                wval = int(word, 16)
                if wval > 0xFFFFFFFF:
                    errors.append("%s: encoding.word > 0xFFFFFFFF: %s"
                                  % (tag, word))
                elif key is not None and key in by_key:
                    rec = by_key[key]
                    try:
                        mask = _to_int(rec["mask"])
                        value = _to_int(rec["value"])
                    except (KeyError, ValueError) as exc:
                        errors.append("%s: opcodes.yaml record for %s has bad "
                                      "mask/value: %s" % (tag, key, exc))
                    else:
                        if (wval & mask) != value:
                            errors.append(
                                "%s: encoding.word %s does not match %s "
                                "mask/value (expected (word & 0x%08X) == 0x%08X)"
                                % (tag, word, key, mask, value))

        # input_state 必须为 mapping
        if input_state is not None and not isinstance(input_state, dict):
            errors.append("%s: input_state must be a mapping" % tag)

        # 10/11. state banks 与 memory
        ram_required = (cls == "semantic")
        for label, state in (("input_state", input_state),
                             ("expected_state", expected_state)):
            _check_state_banks(state, tag, label, errors)
            _check_memory(state, tag, label, ram_required, errors)

        # 4. deferred 一致性
        if status == "deferred":
            if expected_state is not None:
                errors.append("%s: status=deferred but expected_state is not null"
                              % tag)
            if expected_pc is not None:
                errors.append("%s: status=deferred but expected_pc is not null"
                              % tag)
            reason = case.get("deferred_reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append("%s: status=deferred but deferred_reason is "
                              "empty/missing" % tag)

        # 10. active semantic/boundary 必须有 expected_state
        if status == "active" and cls in ("semantic", "boundary"):
            if expected_state is None:
                errors.append("%s: active %s case must have expected_state"
                              % (tag, cls))

        # 14(F9②). legality 类 expected_state 必须为 null
        if cls == "legality" and expected_state is not None:
            errors.append("%s: legality case must have expected_state == null"
                          % tag)

        # 13. expected_pc（R4）：类型 / 48-bit / class 一致性
        if expected_pc is not None:
            if cls in ("legality", "encoding"):
                errors.append("%s: %s case must not carry non-null expected_pc"
                              % (tag, cls))
            if not isinstance(expected_pc, str) or not HEX_RE.match(
                    expected_pc.strip()):
                errors.append("%s: expected_pc not valid hex: %r"
                              % (tag, expected_pc))
            else:
                pval = int(expected_pc, 16)
                if pval > ADDR48_MAX:
                    errors.append("%s: expected_pc is not a 48-bit valid "
                                  "address (> 0x%x): %s"
                                  % (tag, ADDR48_MAX, expected_pc))

    return len(cases)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

    opcodes_path = os.path.join(repo_dir, "contracts", "opcodes.yaml")
    if not os.path.exists(opcodes_path):
        print("ERROR: contracts/opcodes.yaml not found", file=sys.stderr)
        sys.exit(1)

    try:
        _m1, by_key, dups = load_opcodes(opcodes_path)
    except (ValueError, KeyError) as exc:
        print("ERROR: cannot load contracts/opcodes.yaml: %s" % exc,
              file=sys.stderr)
        sys.exit(1)

    errors = []
    for key in dups:
        errors.append("opcodes.yaml: duplicate M1 identity (%s, %s)" % key)
    m1_keys = set(by_key)

    inventory_path = os.path.join(repo_dir, "tests", "vectors", "inventory.md")
    if not os.path.exists(inventory_path):
        print("ERROR: tests/vectors/inventory.md not found", file=sys.stderr)
        sys.exit(1)

    inv_rows = parse_inventory(inventory_path)
    inv_keys = set()
    declared = {}
    for row in inv_rows:
        insn = _unquote(row.get("insn", ""))
        fmt = _unquote(row.get("format", ""))
        if not insn or not fmt:
            continue
        key = (insn, fmt)
        if key in inv_keys:
            errors.append("inventory.md: duplicate row (%s, %s)" % key)
            continue
        inv_keys.add(key)
        cells = [_unquote(row.get(c, "")) for c in
                 ("encoding", "legality", "semantic", "boundary", "overlap")]
        declared[key] = any(c.lower() not in DECL_NA for c in cells)

    # 12. inventory 同步（R2）：M1 行集 == opcodes M1 身份集
    for key in sorted(m1_keys - inv_keys):
        errors.append("INVENTORY MISSING: M1 identity (%s, %s) has no "
                      "inventory.md row" % key)
    for key in sorted(inv_keys - m1_keys):
        errors.append("INVENTORY EXTRA: inventory.md row (%s, %s) is not an "
                      "M1 identity" % key)

    # 9. 覆盖率门控：每个 M1 身份须在 inventory 中声明至少一类覆盖
    covered = 0
    for key in m1_keys:
        if key in inv_keys and declared.get(key):
            covered += 1
        elif key in inv_keys:
            errors.append("COVERAGE MISSING: (%s, %s) has no coverage "
                          "declaration in inventory.md" % key)

    # 1/2/3/4/5/6/7/8/10/11/13/14. 向量数据逐 case 校验
    isa_dir = os.path.join(repo_dir, "tests", "vectors", "isa")
    yaml_files = (sorted(glob.glob(os.path.join(isa_dir, "*.yaml")))
                  if os.path.isdir(isa_dir) else [])
    total_cases = 0
    for fpath in yaml_files:
        total_cases += validate_file(fpath, by_key, m1_keys, errors)

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print("validate_vectors: FAILED (%d error(s))" % len(errors),
              file=sys.stderr)
        sys.exit(1)

    print("validate_vectors: %d/%d M1 identities covered OK "
          "(inventory sync OK; %d data files, %d cases)"
          % (covered, len(m1_keys), len(yaml_files), total_cases))
    sys.exit(0)


if __name__ == "__main__":
    main()
