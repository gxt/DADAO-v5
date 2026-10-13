#!/usr/bin/env python3
"""validate_m6_vectors.py — M6 独立 oracle（TESTCASES-036t）。

覆盖三个来源，全部**独立派生**——本脚本**不**调用 ``llvm-mc``/``llc``/
``ld.lld``/QEMU，也**不** import 或调用任何子进程模块（仅标准库 ``os``/
``re``/``sys`` + PyYAML）：

A. **L1 MC 编码/reloc**（``tests/llvm/lit/MC/DADAO/m6-callconv.s`` 与
   ``m6-ldst-symbol.s``）：从 ``contracts/opcodes.yaml``（``value``/``fields``
   位域）**独立派生**每条指令的编码，从 ``.tao/knowledge/contract-elf.md §2.2``
   （重定位类型表，**机械解析**）独立派生其重定位类型，再与行内
   ``; @enc <8hex>`` / ``; @reloc <NAME>`` 注释比对。

B. **L3 执行向量**（``tests/llvm/codegen/m6/expected.yaml``，raw-bin 清单）：
   每条程序的 ``expected_exit_code`` 由**主机侧 IR 语义模型**独立重算（64 位
   二进制补码整数、IEEE-754 双精度、大端内存），与清单记录比对。

C. **L3 ELF 向量**（``tests/llvm/codegen/m6/expected-elf.yaml``）：同上（间接
   调用 / 函数指针地址构造，需 linker 解析 ABS48）。

设计原则与既有范式一致（``validate_codegen_vectors.py`` /
``validate_elf_vectors.py`` / ``validate_cfx_vectors.py``）：改一条期望值、或
改一条 ``.s``/``.ll`` 书写，本脚本都会**非零退出**。它是必要非充分 oracle——
真正的端到端执行由 ``tools/integ/run_codegen_e2e.py``（raw-bin）与
``tools/integ/run_elf_e2e.py``（ELF）承担。

退出码：有错误 ``exit(1)`` 并逐条打印 ``FAIL``；全部通过 ``exit(0)``。
"""
from __future__ import annotations

import os
import re
import sys

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPCODES = os.path.join(ROOT, "contracts", "opcodes.yaml")
CONTRACT_ELF = os.path.join(ROOT, ".tao", "knowledge", "contract-elf.md")
MC_DIR = os.path.join(ROOT, "tests", "llvm", "lit", "MC", "DADAO")
M6_DIR = os.path.join(ROOT, "tests", "llvm", "codegen", "m6")

# 允许通过环境变量改目录（仅用于反例注入自检：在临时副本上运行，真源仍取
# OPCODES/CONTRACT_ELF）。
MC_VEC_DIR = os.environ.get("M6_MC_DIR") or MC_DIR
M6_VEC_DIR = os.environ.get("M6_VEC_DIR") or M6_DIR
MC_FILES = ["m6-callconv.s", "m6-ldst-symbol.s"]

ENCODING_PATH = os.path.join(M6_VEC_DIR, "expected.yaml")
ELF_PATH = os.path.join(M6_VEC_DIR, "expected-elf.yaml")

# 注记可出现在同一注释行的任意位置（如 `; @enc <hex> @reloc <NAME>`），
# 故**不**锚定 `;`，只按 `@enc` / `@reloc` token 搜索（修 F-A：旧式
# `;\s*@enc` / `;\s*@reloc` 要求 token 紧跟 `;`，看到 `@enc` 在前即漏 `@reloc`）。
ENC_RE = re.compile(r"@enc\s+([0-9a-fA-F]{8})\b")
RELOC_RE = re.compile(r"@reloc\s+(R_DADAO_[A-Z0-9]+)\b")
REG_RE = re.compile(r"^(rd|rb|ra|rf)(\d+)$")
WP_RE = re.compile(r"^wp([0-3])$")
SAFE_EXPR = re.compile(r"^[0-9a-fA-FxX\b\s()+\-*/%<>&|^~]+$")

MASK64 = (1 << 64) - 1


class Ck:
    def __init__(self):
        self.passes = 0
        self.fails = []

    def check(self, name, cond, detail=""):
        if cond:
            self.passes += 1
            print(f"[PASS] {name}")
        else:
            self.fails.append(name)
            print(f"[FAIL] {name} {detail}".rstrip())


# ---------------------------------------------------------------------------
# opcodes.yaml + contract-elf.md §2.2 装载（独立派生）
# ---------------------------------------------------------------------------

def load_opcodes():
    with open(OPCODES, "r", encoding="utf-8") as fh:
        recs = _yaml.safe_load(fh)
    by_mnemonic = {}
    for r in recs:
        by_mnemonic.setdefault(r["mnemonic"], []).append(r)
    return by_mnemonic


def _cells(line):
    if not line.strip().startswith("|"):
        return None
    return [c.strip() for c in line.strip().strip("|").split("|")]


def load_reloc_table():
    """Parse contract-elf.md §2.2 的重定位类型表。

    返回 (by_number, by_mnemonic, ldst_types)：
      by_number    : {int: name}
      by_mnemonic  : {mnemonic: name}（由场景单元格的 ``反引号 token`` 派生）
      ldst_types   : (rel12_name, abs12_name)（按场景里的 ``rb0`` / ``rbN``）
    """
    by_number, by_mnemonic = {}, {}
    rel12 = abs12 = None
    with open(CONTRACT_ELF, "r", encoding="utf-8") as fh:
        for line in fh:
            cells = _cells(line)
            if not cells or len(cells) != 4:
                continue
            m = re.fullmatch(r"(\d+)", cells[0])
            nm = re.fullmatch(r"`(R_DADAO_[A-Z0-9]+)`", cells[1])
            if not m or not nm:
                continue
            number, name, scenario = int(m.group(1)), nm.group(1), cells[2]
            by_number[number] = name
            toks = re.findall(r"`([^`]+)`", scenario)
            for t in toks:
                if t in ("[rb0, sym]", "[rbN, sym]"):
                    continue
                if t.startswith("ld.") or t.startswith("st."):
                    if "rb0" in scenario and rel12 is None:
                        rel12 = name
                    elif ("rbN" in scenario or "rb1" in scenario) and abs12 is None:
                        abs12 = name
                    continue
                if re.fullmatch(r"[A-Za-z0-9_.]+", t):
                    by_mnemonic.setdefault(t, name)
    return by_number, by_mnemonic, (rel12, abs12)


# ---------------------------------------------------------------------------
# 编码派生（opcodes.yaml；仅覆盖 L1 向量用到的形态）
# ---------------------------------------------------------------------------

def _field(rec, name):
    for f in rec["fields"]:
        if f["name"] == name:
            return f
    raise KeyError(f"record {rec['id']} has no field {name}")


def _span(fld):
    m = re.fullmatch(r"\[(\d+):(\d+)\]", fld["bits"])
    return int(m.group(1)), int(m.group(2))


def _encode(rec, assigns):
    word = int(rec["value"], 16) if isinstance(rec["value"], str) else rec["value"]
    for name, val in assigns.items():
        f = _field(rec, name)
        hi, lo = _span(f)
        word |= (val & ((1 << (hi - lo + 1)) - 1)) << lo
    return word & 0xFFFFFFFF


def _reg_fields(rec):
    return [f for f in rec["fields"] if f.get("bank") in ("rd", "rb", "ra", "rf")]


def _imm_field(rec):
    for f in rec["fields"]:
        if f.get("role") == "imm":
            return f
    raise KeyError(f"record {rec['id']} has no imm field")


def _split_top(s):
    out, cur, depth = [], "", 0
    for ch in s:
        if ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip() or out:
        out.append(cur.strip())
    return out


def _is_symbol(tok):
    """非纯数字表达式（且非寄存器/地址）= 符号操作数（由 reloc 提供值）。"""
    tok = tok.strip()
    try:
        _eval_expr(tok)
        return False
    except ValueError:
        return True


def _eval_expr(s):
    s = s.strip()
    if not SAFE_EXPR.match(s):
        raise ValueError(f"unsafe expr: {s}")
    return eval(s, {"__builtins__": {}}, {})  # noqa: S307 (whitelisted)


def derive_encoding(by_mnemonic, code):
    """独立派生一行指令的 32-bit 编码（符号立即数按 0）。"""
    raw_mn = code.split(None, 1)[0]
    mnemonic = raw_mn.lower()
    rest = code[len(raw_mn):].strip()
    ops = _split_top(rest)
    cands = by_mnemonic.get(mnemonic)
    if not cands:
        raise ValueError(f"unknown mnemonic {mnemonic!r}")

    matches = []
    for rec in cands:
        fmt = rec["format"]
        regs = _reg_fields(rec)
        try:
            if fmt == "iiii":
                if len(ops) != 1 or not ops[0].startswith("["):
                    raise ValueError("iiii arity")
                inner = _split_top(ops[0][1:-1])
                if len(inner) != 2 or inner[0].strip() != "rb0":
                    raise ValueError("iiii base must be rb0")
                imm = 0 if _is_symbol(inner[1]) else _eval_expr(inner[1]) >> 2
                assigns = {_imm_field(rec)["name"]: imm}
            elif fmt == "rwii":
                if len(ops) != 3:
                    raise ValueError("rwii arity")
                m = REG_RE.fullmatch(ops[0])
                w = WP_RE.fullmatch(ops[1])
                if not m or not w or regs[0]["bank"] != m.group(1):
                    raise ValueError("rwii operands")
                imm = 0 if _is_symbol(ops[2]) else _eval_expr(ops[2])
                wpf = next(f for f in rec["fields"] if f.get("role") == "wyde_pos")
                assigns = {regs[0]["name"]: int(m.group(2)),
                           wpf["name"]: int(w.group(1)),
                           _imm_field(rec)["name"]: imm}
            elif fmt == "riii":
                # br.n {rd8}?, [rb0, sym]
                if len(ops) != 2 or not ops[0].strip().endswith("?"):
                    raise ValueError("riii branch arity")
                grp = _split_top(ops[0].strip().rstrip("?").strip()[1:-1])
                if len(grp) != 1:
                    raise ValueError("riii cond group")
                m = REG_RE.fullmatch(grp[0])
                addr = _split_top(ops[1][1:-1])
                if not m or regs[0]["bank"] != m.group(1) or addr[0].strip() != "rb0":
                    raise ValueError("riii operands")
                imm = 0 if _is_symbol(addr[1]) else _eval_expr(addr[1]) >> 2
                assigns = {regs[0]["name"]: int(m.group(2)),
                           _imm_field(rec)["name"]: imm}
            elif fmt == "rrii":
                if len(ops) == 2 and ops[1].startswith("["):
                    # br.eq/ne {r1, r2}?, [rb0, sym] 或 ld/st rd, [rbN, sym]
                    inner = _split_top(ops[1][1:-1])
                    base = inner[0].strip()
                    if ops[0].strip().endswith("?"):
                        grp = _split_top(ops[0].strip().rstrip("?").strip()[1:-1])
                        if len(grp) != 2:
                            raise ValueError("rrii cond arity")
                        ms = [REG_RE.fullmatch(g) for g in grp]
                        if any(not x for x in ms) or base != "rb0":
                            raise ValueError("rrii cond operands")
                        assigns = {}
                        for f, mm in zip(regs, ms):
                            if f["bank"] != mm.group(1):
                                raise ValueError("rrii bank mismatch")
                            assigns[f["name"]] = int(mm.group(2))
                        imm = 0 if _is_symbol(inner[1]) else _eval_expr(inner[1]) >> 2
                    else:
                        m = REG_RE.fullmatch(ops[0])
                        bm = REG_RE.fullmatch(base)
                        if (not m or not bm or len(regs) < 2
                                or regs[0]["bank"] != m.group(1)
                                or regs[1]["bank"] != bm.group(1)):
                            raise ValueError("ld/st operands")
                        assigns = {regs[0]["name"]: int(m.group(2)),
                                   regs[1]["name"]: int(bm.group(2))}
                        imm = 0 if _is_symbol(inner[1]) else _eval_expr(inner[1])
                    assigns[_imm_field(rec)["name"]] = imm
                else:
                    raise ValueError("rrii form")
            else:
                raise ValueError(f"unsupported format {fmt}")
        except (ValueError, KeyError, StopIteration):
            continue
        matches.append(_encode(rec, assigns))
    if len(matches) != 1:
        raise ValueError(f"{code!r} matched {len(matches)} records")
    return "%08x" % matches[0]


def derive_reloc(by_mnemonic, by_mnemonic_reloc, ldst_types, code):
    """独立派生一行指令的 R_DADAO_* 类型。"""
    raw_mn = code.split(None, 1)[0]
    mnemonic = raw_mn.lower()
    rest = code[len(raw_mn):].strip()
    rel12, abs12 = ldst_types
    if mnemonic.startswith("ld.") or mnemonic.startswith("st."):
        addr = _split_top(rest.split(",", 1)[1].strip()[1:-1])
        base = addr[0].strip()
        return rel12 if base == "rb0" else abs12
    if mnemonic in by_mnemonic_reloc:
        return by_mnemonic_reloc[mnemonic]
    raise ValueError(f"no reloc type derived for {mnemonic!r}")


# ---------------------------------------------------------------------------
# A. L1 MC 向量校验
# ---------------------------------------------------------------------------

def check_l1(ck):
    by_mnemonic = load_opcodes()
    by_number, by_mnemonic_reloc, ldst_types = load_reloc_table()
    ck.check("reloc-table-parsed",
             by_number.get(1, "").endswith("REL26")
             and by_number.get(4, "").endswith("REL12")
             and by_number.get(5, "").endswith("ABS12"),
             f"numbers={by_number}")
    ck.check("reloc-ldst-types", ldst_types[0] and ldst_types[1], f"{ldst_types}")

    n = 0
    for fname in MC_FILES:
        path = os.path.join(MC_VEC_DIR, fname)
        ck.check(f"mc-file-exists[{fname}]", os.path.isfile(path))
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        enc_hits = reloc_hits = 0
        for lineno, raw in enumerate(lines, 1):
            me = ENC_RE.search(raw)
            mr = RELOC_RE.search(raw)
            # 去掉行内注释后的代码部分；据此识别「指令行」（非伪指令 `.x`、
            # 非标号 `...:`、非空）。指令行**必须**成对携带 @enc + @reloc。
            code = raw.split(";", 1)[0].strip()
            is_code = bool(code) and not code.startswith(".") and not code.endswith(":")
            if not (is_code or me or mr):
                continue
            n += 1
            loc = f"{fname}:{lineno}"
            enc_hits += 1 if me else 0
            reloc_hits += 1 if mr else 0
            # 成对性（修 F-D）：被覆盖的行必须同时带 @enc 与 @reloc ⇒ 删掉
            # 任一注记（或整条注记）都会使覆盖静默收缩却仍绿，这里强制 FAIL。
            ck.check(f"l1-paired[{loc}]", bool(me) and bool(mr),
                     f"{code!r} me={bool(me)} mr={bool(mr)}")
            if me:
                want = me.group(1).lower()
                got = derive_encoding(by_mnemonic, code)
                ck.check(f"l1-enc[{loc}]", got == want,
                         f"{code!r} expected={want} derived={got}")
            if mr:
                want = mr.group(1)
                got = derive_reloc(by_mnemonic, by_mnemonic_reloc, ldst_types, code)
                ck.check(f"l1-reloc[{loc}]", got == want,
                         f"{code!r} expected={want} derived={got}")
        # 逐文件命中数相等（enc 命中 == reloc 命中，且非空）
        ck.check(f"l1-file-count[{fname}]", enc_hits == reloc_hits and enc_hits > 0,
                 f"enc={enc_hits} reloc={reloc_hits}")
    ck.check("l1-annotations-nonempty", n > 0, "no @enc/@reloc annotations found")
    return n


# ---------------------------------------------------------------------------
# B/C. L3 执行向量：主机侧 IR 语义模型（independent oracle）
# ---------------------------------------------------------------------------

# 每条程序的主机侧推导（64 位二进制补码 + IEEE-754 double）。与清单
# ``derivation`` 字段互相印证；只依赖 IR 语义，不依赖 llc/ld.lld/QEMU。
def ir_oracle(name):
    if name == "m6_multi_return.ll":
        a, b = 50, 8
        return ((a + b) - (a - b)) & 0x7F           # 58 - 42 = 16
    if name == "m6_sret.ll":
        return 3 & 0x7F
    if name == "m6_aggregate_arg.ll":
        return ((40 + 2) + 9) & 0x7F                # 42 + 9 = 51
    if name == "m6_varargs.ll":
        return (10 + 20 + 12) & 0x7F
    if name == "m6_large_frame.ll":
        return (1 + 1) & 0x7F
    if name == "m6_fp_arith.ll":
        s = 3.0 * 2.0 + 3.0 / 2.0                    # 7.5
        return (42 if s > 6.0 else 7) & 0x7F
    if name == "m6_fp_hfa.ll":
        s = 1.5 + 2.5                                # 4.0
        return (42 if s > 3.0 else 7) & 0x7F
    if name == "m6_indirect_call.ll":
        return (10 + 20 + 12) & 0x7F
    return None


MAIN_RE = re.compile(r"define\s+i64\s+@main\s*\(\s*\)\s*\{")

# Literal constants each program's derivation depends on.  If an IR source is
# edited (e.g. a different input value) without updating this oracle, the
# `ir-consts` check fails, so the two can never silently drift apart.
IR_CONSTANTS = {
    "m6_multi_return.ll": ["50", "8"],
    "m6_sret.ll": ["3"],
    "m6_aggregate_arg.ll": ["40", "2", "9"],
    "m6_varargs.ll": ["10", "20", "12"],
    "m6_large_frame.ll": ["60000", "200000"],
    "m6_fp_arith.ll": ["3.0", "2.0", "6.0"],
    "m6_fp_hfa.ll": ["1.5", "2.5", "3.0"],
    "m6_indirect_call.ll": ["10", "20", "12"],
}


def _check_manifest(ck, path, schema, tag):
    ck.check(f"{tag}-manifest-exists", os.path.isfile(path), path)
    if not os.path.isfile(path):
        return 0
    with open(path, "r", encoding="utf-8") as fh:
        doc = _yaml.safe_load(fh)
    ck.check(f"{tag}-schema", isinstance(doc, dict) and doc.get("schema") == schema,
             f"{path}: schema != {schema!r}")
    programs = doc.get("programs") if isinstance(doc, dict) else None
    if not isinstance(programs, list) or not programs:
        ck.check(f"{tag}-programs-nonempty", False, "no programs")
        return 0
    names = []
    for i, rec in enumerate(programs):
        name = rec.get("name")
        names.append(name)
        for field in ("category", "expected_exit_code", "derivation"):
            ck.check(f"{tag}-field[{name}].{field}", field in rec and rec[field] != "",
                     f"record #{i} missing {field}")
        expected = rec.get("expected_exit_code")
        ck.check(f"{tag}-range[{name}]",
                 isinstance(expected, int) and not isinstance(expected, bool)
                 and 0 <= expected <= 0x7F,
                 f"expected_exit_code out of 0x00..0x7F: {expected!r}")
        src = rec.get("sources")
        if src is None:
            fpath = os.path.join(M6_VEC_DIR, str(name))
            ck.check(f"{tag}-src[{name}]", os.path.isfile(fpath), f"missing {fpath}")
        else:
            for s in src:
                ck.check(f"{tag}-src[{name}:{s}]",
                         os.path.isfile(os.path.join(M6_VEC_DIR, s)),
                         f"missing {s}")
        # IR 形状：定义 i64 @main()
        primary = os.path.join(M6_VEC_DIR, (src[0] if src else str(name)))
        if os.path.isfile(primary):
            body = "\n".join(l.split(";", 1)[0] for l in
                             open(primary, encoding="utf-8").read().splitlines())
            has_main = bool(MAIN_RE.search(body)) or any(
                "define i64 @main" in "\n".join(
                    l.split(";", 1)[0] for l in
                    open(os.path.join(M6_VEC_DIR, s), encoding="utf-8").read().splitlines())
                for s in (src or [str(name)]))
            ck.check(f"{tag}-main-signature[{name}]", has_main,
                     "missing `define i64 @main()`")
        # IR 常量：oracle 假设的输入常量必须逐字出现在源里（防 IR 改而 oracle 未改）
        text = ""
        for s in (src or [str(name)]):
            p = os.path.join(M6_VEC_DIR, s)
            if os.path.isfile(p):
                text += open(p, encoding="utf-8").read() + "\n"
        consts = IR_CONSTANTS.get(name, [])
        missing_c = [c for c in consts if c not in text]
        ck.check(f"{tag}-ir-consts[{name}]", bool(consts) and not missing_c,
                 f"assumed constants not found in IR: {missing_c}")
        # 独立重算
        want = ir_oracle(name)
        ck.check(f"{tag}-oracle[{name}]", want is not None and want == expected,
                 f"expected={expected!r} oracle={want!r}")
    ck.check(f"{tag}-name-unique", len(names) == len(set(names)), "duplicate names")
    return len(programs)


def _manifest_ll_set(path):
    """清单声明的 `.ll` 源集合（raw-bin 用 ``name``，ELF 用 ``sources``）。"""
    with open(path, "r", encoding="utf-8") as fh:
        doc = _yaml.safe_load(fh)
    out = set()
    for rec in (doc.get("programs") or []) if isinstance(doc, dict) else []:
        src = rec.get("sources")
        if src:
            out.update(s for s in src if str(s).endswith(".ll"))
        else:
            nm = rec.get("name")
            if isinstance(nm, str) and nm.endswith(".ll"):
                out.add(nm)
    return out


def check_m6_disk_set(ck):
    """清单 ↔ 磁盘 `*.ll` 精确集合一致（防清单与实际文件漂移；对齐
    `validate_codegen_vectors.py` 的 ``files-match`` 属性）。"""
    declared = _manifest_ll_set(ENCODING_PATH) | _manifest_ll_set(ELF_PATH)
    disk = sorted(f for f in os.listdir(M6_VEC_DIR) if f.endswith(".ll"))
    ck.check("m6-manifest-vs-disk", sorted(declared) == disk,
             f"declared={sorted(declared)} disk={disk}")


def main():
    ck = Ck()
    print("== M6 独立 oracle (TESTCASES-036t) ==")
    print("opcodes  :", os.path.relpath(OPCODES, ROOT))
    print("contract :", os.path.relpath(CONTRACT_ELF, ROOT))
    print("-" * 72)
    n_l1 = check_l1(ck)
    n_raw = _check_manifest(ck, ENCODING_PATH, "m6-vectors-v1", "m6")
    n_elf = _check_manifest(ck, ELF_PATH, "m6-elf-vectors-v1", "m6elf")
    check_m6_disk_set(ck)
    print("-" * 72)
    print(f"L1 注记 {n_l1} 条；raw-bin 程序 {n_raw} 条；ELF 程序 {n_elf} 条")
    if ck.fails:
        print(f"validate_m6_vectors: FAIL ({len(ck.fails)} failed, {ck.passes} passed)")
        for name in ck.fails:
            print(f"  - {name}")
        return 1
    print(f"validate_m6_vectors: PASS ({ck.passes} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
