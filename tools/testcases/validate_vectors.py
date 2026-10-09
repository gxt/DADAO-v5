#!/usr/bin/env python3
"""validate_vectors.py — 校验 tests/vectors 的向量 schema、覆盖率与 inventory 同步。

Spec-first：所有判定依据 `contracts/opcodes.yaml`、`contracts/legality_rules.yaml`
与 `tests/vectors/schema.md`；**不**读取 LLVM/QEMU 产物，不从实现反推。

检查项（对应 `TESTCASES-002t` 的校验内容 1–14）：
   1. 必填字段存在（`mnemonic`/`id`/`format`/`class`/`encoding`/`input_state`/`spec_cite`）
   2. `class` ∈ {encoding, legality, semantic, boundary, overlap}
   3. `status` ∈ {active, deferred}
   4. deferred 一致性（`expected_state`/`expected_pc` 为 null，`deferred_reason` 非空）
   5. `expected_fault` ∈ {null, ILLI, UNDI, MALIGN, IALIGN, RASOF, RASUF, UNMAPPED}
   6. `encoding.word` 合法 hex 且 ≤ 0xFFFFFFFF
   7. `id` 存在于 `opcodes.yaml` 的 M1 身份集
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
REQUIRED_FIELDS = ["mnemonic", "id", "format", "class", "encoding",
                   "input_state", "spec_cite"]

# ADR-0004 R3 / ADR-0020 D15（C1 step2）：RAM@0 窗口（16 MiB）与 48-bit 有效地址上限
RAM_BASE = 0x0000_0000_0000
RAM_END = 0x0000_00FF_FFFF
ADDR48_MAX = 0xFFFF_FFFF_FFFF

# ADR-0004 D2.2 + tests/vectors/isa/ctrl-br.yaml 头部约定：
# 向量中指令地址 = RAM@0 入口 rb0 = 0x0000_0000_0000；
# br.* 非跳转（not-taken）后继 PC = rb0 + 4。ISS-025 结构性守卫据此分类 taken/not-taken。
RB0_PC = 0x0000_0000_0000
BR_NOT_TAKEN_PC = RB0_PC + 4

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


def _field_val(word_int, fld):
    """从编码字中取命名字段的值（按 opcodes.yaml 的 bits=[hi:lo]）。"""
    m = re.match(r"\[(\d+):(\d+)\]", fld.get("bits", ""))
    if not m:
        return None
    hi, lo = int(m.group(1)), int(m.group(2))
    return (word_int >> lo) & ((1 << (hi - lo + 1)) - 1)


def load_opcodes(path):
    """返回 (m1_records, by_id, duplicate_ids, all_records)。
    M1 判据 scope == "m1"；all_records 含全部 228 条（含 scope fp/excluded/m3）。
    """
    with open(path) as fh:
        records = _yaml.safe_load(fh)
    if not isinstance(records, list):
        raise ValueError("opcodes.yaml top-level must be a list")
    m1 = [r for r in records if r.get("scope") == "m1"]
    by_id = {}
    dups = []
    for rec in m1:
        rid = rec["id"]
        if rid in by_id:
            dups.append(rid)
        by_id[rid] = rec
    return m1, by_id, dups, records


def parse_inventory(path):
    """解析 inventory.md 中含 `id`+`format` 表头的 Markdown 表。"""
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
            if "id" in low and "format" in low:
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


def validate_file(filepath, by_key, m1_keys, all_records, errors):
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

        # 1/2/3/4/5. 必填字段、class、status、fault（保留编码仍须有这些字段，值为 null）
        for field in REQUIRED_FIELDS:
            if field not in case:
                errors.append("%s: missing required field '%s'" % (tag, field))

        mnem = case.get("mnemonic")
        case_id = case.get("id")
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

        # 保留编码标志（提前检测，供后续分支使用）
        is_reserved = isinstance(encoding, dict) and \
            encoding.get("reserved") is True

        # 7. id 必须存在于 M1 身份集（保留编码已豁免）
        key = None
        if not is_reserved and isinstance(case_id, str):
            key = case_id
            if key not in m1_keys:
                errors.append("%s: id = '%s' is not an M1 identity in "
                              "opcodes.yaml" % (tag, case_id))

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

        # ── 保留编码分支（TESTCASES-008t 方案 A）──────────────────
        # encoding.reserved: true → QFC/子表空白单元格，无 id 身份
        if is_reserved:
            # R1: class 必须为 legality
            if cls != "legality":
                errors.append("%s: reserved encoding must have class='legality', "
                              "got %r" % (tag, cls))
            # R2: expected_fault 必须为 UNDI
            if fault != "UNDI":
                errors.append("%s: reserved encoding must have "
                              "expected_fault='UNDI', got %r" % (tag, fault))
            # R3: status 必须为 active
            if status != "active":
                errors.append("%s: reserved encoding must have status='active', "
                              "got %r" % (tag, status))
            # R3.5: word 必须存在（保留编码须指定具体 word）
            if word is None:
                errors.append("%s: reserved encoding must have encoding.word "
                              "(non-null)" % tag)
            # R4: word 不得为 0x00000000（全零字 = 保留编码，op=0x00 → UNDI，§2.9）
            # R8: word 不得匹配 opcodes.yaml 中任何已定义记录（含 scope fp/excluded）
            if word is not None:
                try:
                    wval_r = int(word, 16) if isinstance(word, str) else word
                except (ValueError, TypeError):
                    wval_r = None  # hex 格式错误由后续检查捕获
                if wval_r is not None:
                    if wval_r == 0:
                        errors.append("%s: reserved encoding word must not be "
                                      "0x00000000 (全零字 = 保留编码，op=0x00 → UNDI, §2.9)"
                                      % tag)
                    # R8: 遍历 opcodes.yaml 全部记录（含 scope fp/excluded），
                    # 若 (word & mask) == value 命中则说明该 word 是已定义编码，
                    # 不得标 reserved
                    for rec in all_records:
                        try:
                            mask = _to_int(rec["mask"])
                            value = _to_int(rec["value"])
                        except (KeyError, ValueError):
                            continue
                        if (wval_r & mask) == value:
                            errors.append(
                                "%s: reserved encoding word %s matches defined "
                                "encoding in opcodes.yaml (id=%s, format=%s, "
                                "scope=%s); reserved only for QFC/子表 "
                                "blank cells"
                                % (tag, word, rec.get("id"),
                                   rec.get("format"),
                                   rec.get("scope", "?")))
                            break
            # R5: notes 必须非空（须给出 reserved 依据）
            notes_val = case.get("notes")
            if not isinstance(notes_val, str) or not notes_val.strip():
                errors.append("%s: reserved encoding must have non-empty 'notes' "
                              "with QFC/子表 position evidence" % tag)
            # R6: spec_cite 必须非空（已由通用检查覆盖，此处冗余确认）
            if not isinstance(spec_cite, str) or not spec_cite.strip():
                errors.append("%s: reserved encoding must have non-empty "
                              "'spec_cite'" % tag)
            # R7: 不得伪造 id 身份
            if isinstance(case_id, str) and case_id.strip():
                errors.append("%s: reserved encoding must not have id identity "
                              "(got %r); use null" % (tag, case_id))

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

        # ── F7: expected_pc existence for PC-affecting instructions (TESTCASES-005t/006t) ──
        # Active semantic cases for PC-affecting instructions MUST have expected_pc.
        # Scope: ctrl-br (br.*), ctrl-jump (jump-*), ctrl-call (call-*), ctrl-ret (ret-*).
        if status == "active" and cls == "semantic" and isinstance(case_id, str):
            if case_id.startswith("br."):
                if expected_pc is None:
                    errors.append(
                        "%s: active semantic br.* case must have expected_pc "
                        "(PC-affecting instruction; taken=rb0+(imm<<2), "
                        "not-taken=rb0+4)" % tag)
            elif case_id.startswith("jump"):
                if expected_pc is None:
                    errors.append(
                        "%s: active semantic jump case must have expected_pc "
                        "(PC-affecting instruction; Addr=rb0+(imms24<<2) or "
                        "rbha+rdhb+(imms12<<2))" % tag)
            elif case_id.startswith("call"):
                if expected_pc is None:
                    errors.append(
                        "%s: active semantic call case must have expected_pc "
                        "(PC-affecting instruction; Addr=rb0+(imms24<<2) or "
                        "rbha+rdhb+(imms12<<2), plus RA push)" % tag)
            elif case_id.startswith("ret"):
                if expected_pc is None:
                    errors.append(
                        "%s: active semantic ret case must have expected_pc "
                        "(PC-affecting instruction; PC=ra63 low 48 bits)" % tag)

        # ── F9 guards (TESTCASES-003t) ──────────────────────────────
        # F9③: class↔fault/state 一致性
        if cls == "encoding":
            if expected_state is not None:
                errors.append("%s: encoding case must have expected_state == null"
                              % tag)
            if fault is not None:
                errors.append("%s: encoding case must have expected_fault == null"
                              % tag)
        if cls == "legality":
            # 保留编码已由 reserved 分支强制 fault == "UNDI"
            if not is_reserved and fault is None:
                errors.append("%s: legality case must have non-null "
                              "expected_fault" % tag)
        if cls == "semantic":
            if fault is not None:
                errors.append("%s: semantic case must have expected_fault == null"
                              % tag)
        if cls in ("boundary", "overlap"):
            if cls == "boundary":
                if fault is not None and fault not in ("ILLI", "UNMAPPED"):
                    errors.append("%s: %s case expected_fault must be null, "
                                  "ILLI, or UNMAPPED, got %r"
                                  % (tag, cls, fault))
            else:  # overlap
                if fault is not None and fault != "ILLI":
                    errors.append("%s: %s case expected_fault must be null or "
                                  "ILLI, got %r" % (tag, cls, fault))

        # ── ISS-097: overlap 同组块赋值的语义门控（mreg_range_overlap）──
        # 依据 contract-isa.md §寄存器组之间块赋值 / legality_rules.yaml::mreg_range_overlap：
        # 同寄存器组块赋值（rd2rd/rb2rb，及 scope fp 的 convert_ff 四条）源范围与目的
        # 范围有任何交集（含完全重合）→ ILLI。此处按 word 的 dst/src 字段 + immu6
        # 机械重算 [start..start+immu6-1] 区间交集；有交集而 expected_fault != ILLI ⇒ 报错。
        # 跨组块赋值（ra2rd/rd2ra/rd2rb/rb2rd 等）源与目的分属不同 bank，结构性不可能
        # 重叠，不适用本规则（由 bank 相等判据自动排除）。
        if cls == "overlap" and key is not None and key in by_key \
                and isinstance(word, str) and HEX_RE.match(word.strip()):
            rec = by_key[key]
            flds = rec.get("fields", [])
            dst_f = next((f for f in flds if f.get("role") == "dst"), None)
            src_f = next((f for f in flds if f.get("role") == "src"), None)
            imm_f = next((f for f in flds if f.get("name") == "immu6"), None)
            if dst_f is not None and src_f is not None and imm_f is not None \
                    and dst_f.get("bank") == src_f.get("bank") \
                    and dst_f.get("bank") in ("rd", "rb", "rf"):
                wval_o = int(word, 16)
                dst_i = _field_val(wval_o, dst_f)
                src_i = _field_val(wval_o, src_f)
                cnt = _field_val(wval_o, imm_f)
                if dst_i is not None and src_i is not None \
                        and cnt is not None and cnt > 0:
                    dst_lo, dst_hi = dst_i, dst_i + cnt - 1
                    src_lo, src_hi = src_i, src_i + cnt - 1
                    if not (dst_hi < src_lo or src_hi < dst_lo):
                        if fault != "ILLI":
                            errors.append(
                                "%s: overlap %s same-bank ranges "
                                "[%d..%d] ∩ [%d..%d] ≠ ∅ but expected_fault=%r "
                                "(must be ILLI per mreg_range_overlap)"
                                % (tag, key, dst_lo, dst_hi, src_lo, src_hi,
                                   fault))

        # F9①: active semantic/boundary src field register pre-set guard
        if status == "active" and cls in ("semantic", "boundary") and \
                isinstance(input_state, dict) and \
                isinstance(encoding, dict) and "word" in encoding and \
                isinstance(case_id, str) and isinstance(fmt, str):
            key = case_id
            wval = int(encoding["word"], 16) if isinstance(
                encoding["word"], str) else encoding["word"]
            if key in by_key:
                rec = by_key[key]
                fields = rec.get("fields", [])
                # Collect pre-set registers
                rd_preset = set()
                rb_preset = set()
                ra_preset = set()
                inp_rd = input_state.get("rd", {})
                inp_rb = input_state.get("rb", {})
                inp_ra = input_state.get("ra", {})
                if isinstance(inp_rd, dict):
                    rd_preset = set(inp_rd.keys())
                if isinstance(inp_rb, dict):
                    rb_preset = set(inp_rb.keys())
                if isinstance(inp_ra, dict):
                    ra_preset = set(inp_ra.keys())

                # Check each src field (bank ∈ {rd, rb, ra}, role = src)
                for fld in fields:
                    if fld.get("role") != "src":
                        continue
                    bank = fld.get("bank")
                    if bank not in ("rd", "rb", "ra"):
                        continue
                    # Extract field value from word
                    bits_str = fld.get("bits", "")
                    m = re.match(r"\[(\d+):(\d+)\]", bits_str)
                    if not m:
                        continue
                    hi, lo = int(m.group(1)), int(m.group(2))
                    field_val = (wval >> lo) & ((1 << (hi - lo + 1)) - 1)
                    reg_name = "%s%d" % (bank, field_val)
                    # rd0/rb0 are hardwired, don't need preset
                    if reg_name in ("rd0", "rb0"):
                        continue
                    preset = rd_preset if bank == "rd" else (
                        rb_preset if bank == "rb" else ra_preset)
                    if reg_name not in preset:
                        errors.append(
                            "%s: active %s src field %s = %s not preset "
                            "in input_state.%s" % (tag, cls, fld["name"],
                                                   reg_name, bank))

                # F9①定向守卫: orrr shl/shr/ext shamt register
                mnemonic = case.get("mnemonic", "")
                if fmt == "orrr" and isinstance(mnemonic, str) and \
                        any(mnemonic.startswith(p)
                            for p in ("shl.", "shr.", "ext.")):
                    # shamt register = word[5:0]
                    shamt_reg = wval & 0x3F
                    shamt_name = "rd%d" % shamt_reg
                    if shamt_name == "rd0":
                        # rd0 = 0 is valid shamt for any N
                        shamt_val = 0
                    elif shamt_name in rd_preset:
                        shamt_val = int(str(inp_rd[shamt_name]), 0)
                    else:
                        errors.append(
                            "%s: orrr %s shamt register %s not preset "
                            "in input_state.rd" % (tag, mnemonic, shamt_name))
                        shamt_val = None
                    if shamt_val is not None:
                        # Determine N from mnemonic suffix
                        if ".ub" in mnemonic or ".sb" in mnemonic:
                            N = 7
                        elif ".uw" in mnemonic or ".sw" in mnemonic:
                            N = 15
                        elif ".ut" in mnemonic or ".st" in mnemonic:
                            N = 31
                        else:
                            N = 63
                        if shamt_val > N:
                            errors.append(
                                "%s: orrr %s shamt %d > N=%d (from %s)"
                                % (tag, mnemonic, shamt_val, N, shamt_name))

        # ── F10 guards (TESTCASES-004t) ─────────────────────────────
        # Encoding class: memory instructions must satisfy F10 constraints.
        # Applies to id prefix ld./st./ldm./stm. (访存 encoding).
        if cls == "encoding" and isinstance(case_id, str) and \
                isinstance(fmt, str) and isinstance(encoding, dict) and \
                "word" in encoding and isinstance(input_state, dict) and \
                any(case_id.startswith(p) for p in ("ld.", "st.", "ldm.", "stm.")):
            key = case_id
            if key in by_key:
                wval = int(encoding["word"], 16) if isinstance(
                    encoding["word"], str) else encoding["word"]
                rec = by_key[key]
                fields = rec.get("fields", [])

                # Collect pre-set registers from input_state
                inp_rb = input_state.get("rb", {})
                rb_preset = {}
                if isinstance(inp_rb, dict):
                    rb_preset = inp_rb

                # Extract field values
                def _extract_field(fname):
                    """Return integer value of named field from word, or None."""
                    for fld in fields:
                        if fld["name"] == fname:
                            bits_str = fld.get("bits", "")
                            m2 = re.match(r"\[(\d+):(\d+)\]", bits_str)
                            if m2:
                                hi, lo = int(m2.group(1)), int(m2.group(2))
                                return (wval >> lo) & ((1 << (hi - lo + 1)) - 1)
                    return None

                # F10①: base field (rbhb) != rb1, rb2
                # rb0 allowed as base for ld.*/st.* (PC-relative, ADR-0015 D4)
                hb_val = _extract_field("rbhb")
                if hb_val is not None:
                    if hb_val == 0:
                        # rb0 as base is valid for ld/st (PC-relative addressing)
                        # Per ADR-0015 D4: ld/st may use rb0 as base register
                        pass  # rb0 allowed; no error
                    elif hb_val in (1, 2):
                        errors.append(
                            "%s: F10: encoding base field hb=%d (rb%d occupied "
                            "by D6.5 entry state), must use unused rb register"
                            % (tag, hb_val, hb_val))

                    # F10②: base register must be preset in input_state.rb
                    # with value in RAM window
                    # Skip for rb0 (hardwired to PC, ADR-0015 D1)
                    base_name = "rb%d" % hb_val
                    if hb_val == 0:
                        pass  # rb0 is hardwired; no preset needed
                    elif base_name not in rb_preset:
                        errors.append(
                            "%s: F10: encoding base register %s not preset "
                            "in input_state.rb" % (tag, base_name))
                    else:
                        try:
                            base_val = _to_int(rb_preset[base_name])
                            if not (RAM_BASE <= base_val <= RAM_END):
                                errors.append(
                                    "%s: F10: encoding base %s value 0x%x "
                                    "outside RAM window [0x%x, 0x%x]"
                                    % (tag, base_name, base_val,
                                       RAM_BASE, RAM_END))
                        except (ValueError, TypeError):
                            errors.append(
                                "%s: F10: encoding base %s value not parseable: "
                                "%r" % (tag, base_name, rb_preset[base_name]))

                # F10③: rrri (multi) immu6 >= 1
                if fmt == "rrri":
                    immu6_val = _extract_field("immu6")
                    if immu6_val is not None and immu6_val < 1:
                        errors.append(
                            "%s: F10: rrri encoding immu6=%d, must be >= 1"
                            % (tag, immu6_val))

                # F10④: dest ha != rd0/ra0 (role=dst only; src allowed)
                # Per ADR-0015 D2/D3: rd0 as source reads 0 (LEGAL for st.*/stm.*)
                # Check rdha field: only flag if role=dst and value=0
                for fld in fields:
                    if fld["name"] == "rdha" and fld.get("role") == "dst":
                        ha_val = _extract_field("rdha")
                        if ha_val is not None and ha_val == 0:
                            errors.append(
                                "%s: F10: encoding dest rdha=0 (rd0), "
                                "must use non-zero register for destination"
                                % tag)
                        break

                # F10④b: RB variant — rbha as dest must not be rb0
                # Only for ld.o-rb (rbha=dst) and ldm.o-rb (rbha=dst)
                # st.o-rb/stm.o-rb have rbha=src, which is LEGAL (ADR-0015 D3)
                for fld in fields:
                    if fld["name"] == "rbha" and fld.get("role") == "dst":
                        rbha_val = _extract_field("rbha")
                        if rbha_val is not None and rbha_val == 0:
                            errors.append(
                                "%s: F10: encoding dest rbha=0 (rb0=PC), "
                                "must use non-zero register for destination"
                                % tag)
                        break

    return len(cases)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

    opcodes_path = os.path.join(repo_dir, "contracts", "opcodes.yaml")
    if not os.path.exists(opcodes_path):
        print("ERROR: contracts/opcodes.yaml not found", file=sys.stderr)
        sys.exit(1)

    try:
        _m1, by_id, dups, all_records = load_opcodes(opcodes_path)
    except (ValueError, KeyError) as exc:
        print("ERROR: cannot load contracts/opcodes.yaml: %s" % exc,
              file=sys.stderr)
        sys.exit(1)

    errors = []
    for rid in dups:
        errors.append("opcodes.yaml: duplicate M1 id '%s'" % rid)
    m1_keys = set(by_id)

    inventory_path = os.path.join(repo_dir, "tests", "vectors", "inventory.md")
    if not os.path.exists(inventory_path):
        print("ERROR: tests/vectors/inventory.md not found", file=sys.stderr)
        sys.exit(1)

    inv_rows = parse_inventory(inventory_path)
    inv_keys = set()
    declared = {}
    # Data-level coverage: per id, track which classes are ✓
    declared_classes = {}  # id -> set of class names with ✓
    for row in inv_rows:
        rid = _unquote(row.get("id", ""))
        if not rid:
            continue
        if rid in inv_keys:
            errors.append("inventory.md: duplicate row id '%s'" % rid)
            continue
        inv_keys.add(rid)
        class_names = ("encoding", "legality", "semantic", "boundary", "overlap")
        cells = [_unquote(row.get(c, "")) for c in class_names]
        declared[rid] = any(c.lower() not in DECL_NA for c in cells)
        # Track per-class ✓ marks
        cls_set = set()
        for ci, cn in enumerate(class_names):
            cell_low = cells[ci].lower()
            if cell_low.startswith("deferred"):
                continue  # deferred 声明不计缺口
            if cell_low not in DECL_NA:
                cls_set.add(cn)
        declared_classes[rid] = cls_set

    # 12. inventory 同步（R2）：M1 行集 == opcodes M1 身份集
    for rid in sorted(m1_keys - inv_keys):
        errors.append("INVENTORY MISSING: M1 id '%s' has no inventory.md row"
                      % rid)
    for rid in sorted(inv_keys - m1_keys):
        errors.append("INVENTORY EXTRA: inventory.md row '%s' is not an M1 "
                      "identity" % rid)

    # 9. 覆盖率门控：每个 M1 身份须在 inventory 中声明至少一类覆盖
    covered = 0
    for rid in m1_keys:
        if rid in inv_keys and declared.get(rid):
            covered += 1
        elif rid in inv_keys:
            errors.append("COVERAGE MISSING: '%s' has no coverage "
                          "declaration in inventory.md" % rid)

    # 1/2/3/4/5/6/7/8/10/11/13/14. 向量数据逐 case 校验
    isa_dir = os.path.join(repo_dir, "tests", "vectors", "isa")
    yaml_files = (sorted(glob.glob(os.path.join(isa_dir, "*.yaml")))
                  if os.path.isdir(isa_dir) else [])
    total_cases = 0
    # Data-level coverage map: (id, class) -> count of active cases
    data_coverage = {}
    # ISS-025: br.* 双路径覆盖图 — id -> set{taken, not-taken}
    # 分类依据 expected_pc（结构字段，不读 notes/文本）：
    #   not-taken ⇔ expected_pc == BR_NOT_TAKEN_PC（rb0+4）；否则视为 taken。
    br_paths = {}
    for fpath in yaml_files:
        total_cases += validate_file(fpath, by_id, m1_keys, all_records, errors)
        # Build data-level coverage from this file
        try:
            with open(fpath) as fh:
                cases = _yaml.safe_load(fh)
        except Exception:
            continue
        if not cases or not isinstance(cases, list):
            continue
        for c in cases:
            if not isinstance(c, dict):
                continue
            # Skip reserved encoding cases (no identity)
            enc = c.get("encoding")
            if isinstance(enc, dict) and enc.get("reserved"):
                continue
            c_id = c.get("id")
            c_cls = c.get("class")
            c_status = c.get("status", "active")
            if not c_id or not c_cls:
                continue
            if c_status != "active":
                continue
            cov_key = (c_id, c_cls)
            data_coverage[cov_key] = data_coverage.get(cov_key, 0) + 1

            # ISS-025: 收集 br.* 的 taken / not-taken 语义覆盖
            if isinstance(c_id, str) and c_id.startswith("br.") \
                    and c_cls == "semantic":
                epc = c.get("expected_pc")
                if isinstance(epc, str) and HEX_RE.match(epc.strip()) \
                        and int(epc, 16) == BR_NOT_TAKEN_PC:
                    path = "not-taken"
                else:
                    path = "taken"
                br_paths.setdefault(c_id, set()).add(path)

    # ── ISS-025: br.* 双路径（taken + not-taken）结构性守卫 ────────────
    # 每个 M1 br.* 指令须同时存在 taken 与非 taken 的 active semantic 用例；
    # 删任一条 ⇒ 报错。分类仅依赖 expected_pc（结构字段），不依赖注释/文本。
    for rid in sorted(m1_keys):
        if not rid.startswith("br."):
            continue
        paths = br_paths.get(rid, set())
        missing = [p for p in ("taken", "not-taken") if p not in paths]
        if missing:
            errors.append(
                "BR DUAL-PATH GAP: id='%s' missing %s active semantic "
                "case(s) (need both taken=rb0+(imm<<2) and "
                "not-taken=rb0+4; ADR-0004 D2.2)"
                % (rid, ", ".join(missing)))

    # ── Data-level coverage gate (TESTCASES-009t 验收标准 7) ──────────
    # For each id in inventory with ✓ for some class,
    # verify at least 1 active case of that class exists in isa/*.yaml.
    # reserved.yaml cases (encoding.reserved: true) have no id
    # identity and are excluded from this check.
    data_coverage_gaps = []
    for rid in sorted(inv_keys):
        if rid not in declared_classes:
            continue
        for cls_name in declared_classes[rid]:
            cov_key = (rid, cls_name)
            if cov_key not in data_coverage:
                data_coverage_gaps.append(
                    "DATA COVERAGE GAP: id='%s' declares '%s' in "
                    "inventory.md but no active %s case found in "
                    "tests/vectors/isa/*.yaml"
                    % (rid, cls_name, cls_name))
    # Report gaps and block validation (TESTCASES-011t: gate tightening)
    if data_coverage_gaps:
        for gap in data_coverage_gaps:
            print(gap, file=sys.stderr)
        print("DATA COVERAGE: %d gap(s) found (inventory declares ✓ but "
              "no active data case); see above for details"
              % len(data_coverage_gaps), file=sys.stderr)
        sys.exit(1)

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print("validate_vectors: FAILED (%d error(s))" % len(errors),
              file=sys.stderr)
        sys.exit(1)

    print("validate_vectors: %d/%d M1 identities covered OK "
          "(inventory sync OK; %d data files, %d cases; "
          "data coverage gaps: %d)"
          % (covered, len(m1_keys), len(yaml_files), total_cases,
             len(data_coverage_gaps)))
    sys.exit(0)


if __name__ == "__main__":
    main()
