#!/usr/bin/env python3
"""validate_mc_vectors.py — L1 MC 向量独立 oracle（TESTCASES-029t）。

**独立 oracle**：本脚本**不**调用 ``llvm-mc``/``llc``/QEMU，也**不** import 或
调用任何子进程模块（仅用标准库 ``os.path``/``glob``/``re``/``sys`` + PyYAML）。
它从 ``contracts/opcodes.yaml``
（编码表：``op``/``ha``/``value``/``mask``/``fields``）与 ``spec/``
（``Toolchain-01 §6`` 伪指令展开规则、``§7`` 指导符宽度/大端、``§8``
``-multiple-to-single``、``§9`` 诊断、``§2.2`` ``#`` 非法）**独立派生**
每条向量的期望编码/字段/展开形态，再与向量文件内联期望比对。

向量文件 = ``tests/llvm/lit/MC/DADAO/m4-*.s``（每条新向量首行
``; UNSUPPORTED: true``）。每个向量的**输入**是代码部分，**期望值**是同一行
末尾的 ``; @<kind> <expect>`` 注释：

    add.si rd8, 1                    ; @enc 59200001
    set.rd rd6, 0x1234ABCD           ; @exp set.zw rd6, wp1, 0x1234 ; or.w rd6, wp0, 0xabcd
    .dd.w16 0x1234                   ; @dir 1234
    .word 0x1234                     ; @dirrej unknown
    nop                              ; @rej unrecognized
    add.si rd8, 131072               ; @err imms18
    add.uo {rd8, rd9}, rd10, rd11    ; @norm ADD.UO {RD8, RD9}, RD10, RD11
    ldm.o {rd8:rd10}, [rb2, rd1]     ; @mts ldm.o {rd8}, [rb2, rd1] ; add.si rd1, 8 ; ...

kind：
  enc     单条真实指令 → 4 字节大端 hex
  exp     伪指令 → 展开后的真实指令序列（`` ; `` 分隔）
  dir     数据指导符常量/表达式 → 大端字节 hex（符号 → ``ABS48``/``reject:reloc-narrow``）
  dirrej  未知/不支持的指导符 → ``unknown``/``unsupported``
  rej     被删伪指令 → ``unrecognized``
  err     诊断 → 违反的约束 token（``imms18``/``immu12``/``immu6``/``immu16``/
          ``immu18``/``align4``/``rd0-nonzero``/``illegal-token``）
  mts     ``-multiple-to-single`` 展开后的单寄存器指令序列
  norm    两种等价书写 → 必须派生出同一编码（往返规范化）

覆盖门控：五个类别（``@category``）必须全部出现；缺一即失败。

退出码：有错误 ``exit(1)`` 并逐条打印 ``FAIL``；全部通过 ``exit(0)``。
"""

import glob
import os
import re
import sys

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")


REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPCODES = os.path.join(REPO, "contracts", "opcodes.yaml")
# 向量目录默认 = 仓库内单一落点；`MC_VEC_DIR` 仅用于反例注入自检
# （在临时树副本上运行，避免污染真实仓库）。
VEC_DIR = os.environ.get("MC_VEC_DIR") or os.path.join(
    REPO, "tests", "llvm", "lit", "MC", "DADAO")
VEC_GLOB = os.path.join(VEC_DIR, "m4-*.s")

# spec/Toolchain-01 §7：4 条数据指导符（Knuth/MMIX 数据长度）
DIRECTIVE_WIDTH = {".dd.b08": 1, ".dd.w16": 2, ".dd.t32": 4, ".dd.o64": 8}
# spec/Toolchain-01 §6.2：被删的 10 条伪指令（不再实现）
DELETED_PSEUDO = ("nop", "return", "not.b", "not.w", "not.t", "not.o",
                  "neg.b", "neg.w", "neg.t", "neg.o")
# 依 spec §6.1 保留的合成型伪指令（不是 opcodes.yaml 中的真实助记符）
PSEUDO_MNEMONICS = ("set.rd", "set.rb", "set.ft", "set.fo")
CATEGORIES = ("pseudo", "directive", "option", "diagnostic", "roundtrip")

REG_BANKS = {"rd": "rd", "rb": "rb", "ra": "ra", "rf": "rf"}
REG_RE = re.compile(r"^(rd|rb|ra|rf)(\d+)$")


# --------------------------------------------------------------------------
# opcodes.yaml 装载与索引
# --------------------------------------------------------------------------

def load_opcodes():
    with open(OPCODES, "r", encoding="utf-8") as fh:
        records = _yaml.safe_load(fh)
    if not isinstance(records, list):
        raise ValueError("opcodes.yaml 顶层必须是列表")
    by_mnemonic = {}
    for rec in records:
        by_mnemonic.setdefault(rec["mnemonic"], []).append(rec)
    return records, by_mnemonic


def field_span(fld):
    m = re.match(r"\[(\d+):(\d+)\]", fld["bits"])
    if not m:
        raise ValueError("bad bits: %r" % (fld["bits"],))
    return int(m.group(1)), int(m.group(2))


def find_field(rec, name):
    for f in rec["fields"]:
        if f["name"] == name:
            return f
    raise KeyError("record %s has no field %s" % (rec["id"], name))


def reg_fields(rec):
    return [f for f in rec["fields"]
            if f["role"] in ("dst", "src") and f["bank"] in REG_BANKS]


def imm_field(rec, signed=None):
    for f in rec["fields"]:
        if f["role"] == "imm":
            if signed is None or bool(f.get("signed", False)) == signed:
                return f
    raise KeyError("record %s has no imm field" % rec["id"])


def wyde_field(rec):
    for f in rec["fields"]:
        if f["role"] == "wyde_pos":
            return f
    raise KeyError("record %s has no wyde field" % rec["id"])


def encode(rec, assigns):
    """assigns: {field_name: value}；word = value_base | Σ(field << lo)。"""
    word = int(rec["value"], 16) if isinstance(rec["value"], str) else int(rec["value"])
    for name, val in assigns.items():
        f = find_field(rec, name)
        hi, lo = field_span(f)
        width = hi - lo + 1
        word |= (val & ((1 << width) - 1)) << lo
    return word


def hex8(word):
    return "%08x" % (word & 0xFFFFFFFF)


# --------------------------------------------------------------------------
# 词法工具
# --------------------------------------------------------------------------

def split_top(s):
    """按顶层逗号切分，忽略 [] 与 {} 内的逗号。"""
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


def parse_reg(tok):
    m = REG_RE.match(tok.strip().lower())
    if not m:
        return None
    return (m.group(1), int(m.group(2)))


def parse_wp(tok):
    m = re.match(r"^wp([0-3])$", tok.strip().lower())
    if not m:
        return None
    return int(m.group(1))


def parse_group(tok):
    """``{a:b}`` / ``{a}`` → 起止寄存器列表（同组）。"""
    t = tok.strip()
    if not (t.startswith("{") and t.endswith("}")):
        return None
    inner = t[1:-1].strip()
    if ":" in inner:
        lo, hi = [x.strip() for x in inner.split(":", 1)]
    else:
        lo = hi = inner
    rlo, rhi = parse_reg(lo), parse_reg(hi)
    if not rlo or not rhi or rlo[0] != rhi[0]:
        return None
    return (rlo[0], rlo[1], rhi[1])


def parse_addr(tok):
    """``[base, ...]`` → (base_reg, [其余顶层分量])。"""
    t = tok.strip()
    if not (t.startswith("[") and t.endswith("]")):
        return None
    parts = split_top(t[1:-1])
    base = parts[0].strip()
    if base == "excp_cause_ip":
        return ("excp_cause_ip", parts[1:])
    if not parse_reg(base):
        return None
    return (base, parts[1:])


SAFE_EXPR = re.compile(r"^[0-9a-fA-FxXbBoO\s()+\-*/%<>&|^~]+$")


def eval_expr(s):
    s = s.strip()
    if not SAFE_EXPR.match(s):
        raise ValueError("unsafe expr: %r" % s)
    return eval(s, {"__builtins__": {}}, {})  # noqa: S307 (whitelisted)


# --------------------------------------------------------------------------
# 指令 → 编码（按 format 分派；仅覆盖本任务向量用到的形态）
# --------------------------------------------------------------------------

class AssignError(Exception):
    pass


def assign_fields(rec, insn_text):
    ops = split_top(insn_text)
    fmt = rec["format"]
    regs = reg_fields(rec)

    if fmt == "riii":
        if len(ops) == 2 and ops[1].startswith("["):
            # br.* {reg}?, [rb0, imm]（地址：字节 → 编码 >>2）
            inner = ops[0].strip().rstrip("?").strip()
            grp = parse_group(inner)
            if not grp:
                raise AssignError("bad cond group: %r" % ops[0])
            addr = parse_addr(ops[1])
            if not addr or len(addr[1]) != 1:
                raise AssignError("bad branch address: %r" % ops[1])
            off = eval_expr(addr[1][0])
            if regs[0]["bank"] != grp[0]:
                raise AssignError("bank mismatch")
            imm = imm_field(rec)
            return {regs[0]["name"]: grp[1], imm["name"]: off >> 2}
        if len(ops) == 2:
            r = parse_reg(ops[0])
            if not r or r[0] != regs[0]["bank"]:
                raise AssignError("bank mismatch")
            imm = imm_field(rec)
            return {regs[0]["name"]: r[1], imm["name"]: eval_expr(ops[1])}
        raise AssignError("riii arity")

    if fmt == "rrii":
        if len(ops) == 2 and ops[0].strip().endswith("?") and ops[1].startswith("["):
            # br.eq/ne {r1, r2}?, [rb0, imm]（地址 >>2）
            grp = split_top(ops[0].strip().rstrip("?").strip()[1:-1])
            if len(grp) != 2 or len(regs) < 2:
                raise AssignError("br.eq cond arity")
            regs2 = [parse_reg(g) for g in grp]
            if any(not x for x in regs2):
                raise AssignError("bad cond reg")
            addr = parse_addr(ops[1])
            if not addr or len(addr[1]) != 1:
                raise AssignError("bad branch address")
            assigns = {}
            for f, (bank, num) in zip(regs, regs2):
                if f["bank"] != bank:
                    raise AssignError("bank mismatch")
                assigns[f["name"]] = num
            imm = imm_field(rec)
            assigns[imm["name"]] = eval_expr(addr[1][0]) >> 2
            return assigns
        if len(ops) == 3:
            # cmp.* rd, rd, imm（立即数非地址）
            r0, r1 = parse_reg(ops[0]), parse_reg(ops[1])
            if not r0 or not r1 or len(regs) < 2:
                raise AssignError("bad cmp operands")
            if regs[0]["bank"] != r0[0] or regs[1]["bank"] != r1[0]:
                raise AssignError("bank mismatch")
            imm = imm_field(rec)
            return {regs[0]["name"]: r0[1], regs[1]["name"]: r1[1],
                    imm["name"]: eval_expr(ops[2])}
        if len(ops) == 2 and ops[1].startswith("["):
            # ld/st rd, [rb, imm]（访存偏移字节，不 >>2）
            r = parse_reg(ops[0])
            if not r or r[0] != regs[0]["bank"]:
                raise AssignError("bank mismatch")
            addr = parse_addr(ops[1])
            if not addr or len(addr[1]) != 1:
                raise AssignError("bad mem address")
            base = parse_reg(addr[0])
            rb_fields = [f for f in regs[1:] if f["bank"] == "rb"]
            if not base or base[0] != "rb" or len(rb_fields) != 1:
                raise AssignError("bad mem base")
            imm = imm_field(rec)
            return {regs[0]["name"]: r[1], rb_fields[0]["name"]: base[1],
                    imm["name"]: eval_expr(addr[1][0])}
        raise AssignError("rrii arity")

    if fmt == "iiii":
        if len(ops) != 1:
            raise AssignError("iiii arity")
        addr = parse_addr(ops[0])
        if not addr or len(addr[1]) != 1 or parse_reg(addr[0])[1] != 0:
            raise AssignError("iiii must be [rb0, imm]")
        imm = imm_field(rec)
        return {imm["name"]: eval_expr(addr[1][0]) >> 2}

    if fmt == "rwii":
        if len(ops) != 3:
            raise AssignError("rwii arity")
        r, wp = parse_reg(ops[0]), parse_wp(ops[1])
        if not r or wp is None or r[0] != regs[0]["bank"]:
            raise AssignError("rwii operands")
        return {regs[0]["name"]: r[1], wyde_field(rec)["name"]: wp,
                imm_field(rec)["name"]: eval_expr(ops[2])}

    if fmt == "orrr":
        if len(ops) != 3:
            raise AssignError("orrr arity")
        rs = [parse_reg(o) for o in ops]
        if any(not r for r in rs) or len(regs) < 3:
            raise AssignError("orrr operands")
        assigns = {}
        for f, (bank, num) in zip(regs, rs):
            if f["bank"] != bank:
                raise AssignError("bank mismatch")
            assigns[f["name"]] = num
        return assigns

    if fmt == "rrrr":
        if len(ops) == 3 and ops[0].startswith("{"):
            grp = split_top(ops[0].strip()[1:-1])
            if len(grp) != 2 or len(regs) < 4:
                raise AssignError("rrrr double-dst arity")
            rs = [parse_reg(g) for g in grp] + [parse_reg(ops[1]), parse_reg(ops[2])]
            if any(not r for r in rs):
                raise AssignError("rrrr operands")
            assigns = {}
            for f, (bank, num) in zip(regs, rs):
                if f["bank"] != bank:
                    raise AssignError("bank mismatch")
                assigns[f["name"]] = num
            return assigns
        raise AssignError("rrrr form")

    if fmt == "orri":
        if len(ops) == 2 and ops[0].startswith("{"):
            # 块赋值/格式转换 {dst:…}, {src:…}
            dst, src = parse_group(ops[0]), parse_group(ops[1])
            if not dst or not src or (dst[2] - dst[1]) != (src[2] - src[1]):
                raise AssignError("block group mismatch")
            df = [f for f in rec["fields"] if f["role"] == "dst"]
            sf = [f for f in rec["fields"] if f["role"] == "src"]
            if len(df) != 1 or len(sf) != 1:
                raise AssignError("block field roles")
            if df[0]["bank"] != dst[0] or sf[0]["bank"] != src[0]:
                raise AssignError("block bank mismatch")
            return {df[0]["name"]: dst[1], sf[0]["name"]: src[1],
                    imm_field(rec)["name"]: dst[2] - dst[1] + 1}
        if len(ops) == 3:
            r0, r1 = parse_reg(ops[0]), parse_reg(ops[1])
            if not r0 or not r1 or len(regs) < 2:
                raise AssignError("orri operands")
            if regs[0]["bank"] != r0[0] or regs[1]["bank"] != r1[0]:
                raise AssignError("bank mismatch")
            return {regs[0]["name"]: r0[1], regs[1]["name"]: r1[1],
                    imm_field(rec)["name"]: eval_expr(ops[2])}
        raise AssignError("orri arity")

    if fmt == "rrri":
        if len(ops) != 2:
            raise AssignError("rrri arity")
        grp, addr = parse_group(ops[0]), parse_addr(ops[1])
        if not grp or not addr or len(addr[1]) != 1:
            raise AssignError("rrri operands")
        base = parse_reg(addr[0])
        offr = parse_reg(addr[1][0])
        if not base or not offr:
            raise AssignError("rrri address regs")
        # 组字段 = 第一个寄存器字段（ldm 为 dst、stm 为 src）；
        # 另两个寄存器字段按 bank 区分为 rb 基址与 rd 偏移。
        group_f = regs[0]
        rest_regs = regs[1:]
        base_fs = [f for f in rest_regs if f["bank"] == "rb"]
        off_fs = [f for f in rest_regs if f["bank"] == "rd"]
        if group_f["bank"] != grp[0] or len(base_fs) != 1 or len(off_fs) != 1:
            raise AssignError("rrri reg roles")
        if base_fs[0]["bank"] != base[0] or off_fs[0]["bank"] != offr[0]:
            raise AssignError("rrri bank mismatch")
        return {group_f["name"]: grp[1],
                base_fs[0]["name"]: base[1],
                off_fs[0]["name"]: offr[1],
                imm_field(rec)["name"]: grp[2] - grp[1] + 1}

    raise AssignError("unsupported format %s" % fmt)


def pick_and_encode(by_mnemonic, insn_text):
    """从 opcodes.yaml 独立派生 ``insn_text`` 的编码；返回 (hex8, rec)。"""
    raw_mn = insn_text.split(None, 1)[0]
    mnemonic = raw_mn.lower()
    rest = insn_text[len(raw_mn):].strip()
    cands = by_mnemonic.get(mnemonic)
    if not cands:
        raise AssignError("unknown mnemonic %r" % mnemonic)
    matches = []
    for rec in cands:
        try:
            assigns = assign_fields(rec, rest)
        except (AssignError, ValueError, KeyError):
            continue
        # 寄存器合法性（rd0/rb0）由 legality 决定，仅编码不校验
        matches.append((rec, assigns))
    if len(matches) != 1:
        raise AssignError("%r matched %d records" % (insn_text, len(matches)))
    rec, assigns = matches[0]
    return hex8(encode(rec, assigns)), rec


# --------------------------------------------------------------------------
# 伪指令展开（spec/Toolchain-01 §6.1）
# --------------------------------------------------------------------------

def _min_rd_imm_expansion(val):
    """``set.rd rd, imm64`` 常量：最少指令数（set.zw/set.ow + or.w/andn.w）。"""
    val &= (1 << 64) - 1
    wydes = [(val >> (16 * i)) & 0xFFFF for i in range(4)]  # wp0..wp3

    def plan(fill, seed_op, corr_op):
        diff = [i for i in range(3, -1, -1) if wydes[i] != fill]
        seq = []
        if not diff:
            seq.append(("seed", seed_op, 0, fill))
        else:
            seq.append(("seed", seed_op, diff[0], wydes[diff[0]]))
            for i in diff[1:]:
                seq.append(("corr", corr_op, i, wydes[i] if fill == 0
                            else (~wydes[i]) & 0xFFFF))
        return seq

    zero = plan(0, "set.zw", "or.w")
    ones = plan(0xFFFF, "set.ow", "andn.w")
    if len(ones) < len(zero):
        return ones
    if len(zero) < len(ones):
        return zero
    # tie：优先 set.zw（fill 0）；向量应避免 tie，使此分支不可达
    return zero


def expand_pseudo(insn_text):
    """返回展开后的真实指令文本列表（无伪指令）。"""
    raw_mn = insn_text.split(None, 1)[0]
    mnemonic = raw_mn.lower()
    rest = insn_text[len(raw_mn):].strip()
    ops = split_top(rest)
    if mnemonic not in PSEUDO_MNEMONICS:
        raise AssignError("not a implemented pseudo: %r" % mnemonic)

    if mnemonic == "set.rd":
        if len(ops) != 2:
            raise AssignError("set.rd arity")
        dst, src = ops[0].strip(), ops[1].strip()
        rs = parse_reg(src)
        if rs:
            op = {"rb": "rb2rd", "rf": "rf2rd", "ra": "ra2rd", "rd": "rd2rd"}[rs[0]]
            return ["%s {%s}, {%s%d}" % (op, dst, rs[0], rs[1])]
        seq = _min_rd_imm_expansion(eval_expr(src))
        return ["%s %s, wp%d, 0x%x" % (op, dst, wp, v) for _, op, wp, v in seq]

    if mnemonic == "set.rb":
        if len(ops) != 2:
            raise AssignError("set.rb arity")
        dst, src = ops[0].strip(), ops[1].strip()
        rs = parse_reg(src)
        if rs:
            if rs[0] not in ("rd", "rb"):
                raise AssignError("set.rb bad src")
            op = "rd2rb" if rs[0] == "rd" else "rb2rb"
            return ["%s {%s}, {%s%d}" % (op, dst, rs[0], rs[1])]
        val = eval_expr(src) & ((1 << 64) - 1)
        wydes = [(val >> (16 * i)) & 0xFFFF for i in range(4)]
        diff = [i for i in range(3, -1, -1) if wydes[i] != 0]
        seq = []
        if not diff:
            seq.append("set.zw %s, wp0, 0x0" % dst)
        else:
            seq.append("set.zw %s, wp%d, 0x%x" % (dst, diff[0], wydes[diff[0]]))
            for i in diff[1:]:
                seq.append("or.w %s, wp%d, 0x%x" % (dst, i, wydes[i]))
        return seq

    if mnemonic == "set.ft":
        if len(ops) != 2:
            raise AssignError("set.ft arity")
        dst, src = ops[0].strip(), ops[1].strip()
        rs = parse_reg(src)
        if rs:
            if rs[0] == "rd":
                return ["rd2rf {%s}, {%s%d}" % (dst, "rd", rs[1])]
            if rs[0] == "rf":
                return ["ft2ft {%s}, {%s%d}" % (dst, "rf", rs[1])]
            raise AssignError("set.ft bad src")
        val = eval_expr(src) & 0xFFFFFFFF
        return ["set.w %s, wp1, 0x%x" % (dst, (val >> 16) & 0xFFFF),
                "set.w %s, wp0, 0x%x" % (dst, val & 0xFFFF)]

    if mnemonic == "set.fo":
        if len(ops) != 2:
            raise AssignError("set.fo arity")
        dst, src = ops[0].strip(), ops[1].strip()
        rs = parse_reg(src)
        if rs:
            if rs[0] == "rd":
                return ["rd2rf {%s}, {%s%d}" % (dst, "rd", rs[1])]
            if rs[0] == "rf":
                return ["fo2fo {%s}, {%s%d}" % (dst, "rf", rs[1])]
            raise AssignError("set.fo bad src")
        val = eval_expr(src) & ((1 << 64) - 1)
        if val == 0:
            raise AssignError("set.fo imm 0 的 rd2rf 特例不在 spec §6.1（本任务不覆盖）")
        return ["set.w %s, wp3, 0x%x" % (dst, (val >> 48) & 0xFFFF),
                "set.w %s, wp2, 0x%x" % (dst, (val >> 32) & 0xFFFF),
                "set.w %s, wp1, 0x%x" % (dst, (val >> 16) & 0xFFFF),
                "set.w %s, wp0, 0x%x" % (dst, val & 0xFFFF)]

    raise AssignError("unhandled pseudo %r" % mnemonic)


# --------------------------------------------------------------------------
# 指导符 / 选项 / 诊断
# --------------------------------------------------------------------------

def derive_directive(insn_text):
    """``.dd.xxx value[, value...]``：大端字节。符号 → 重定位 token。"""
    parts = insn_text.split(None, 1)
    if len(parts) != 2 or parts[0].lower() not in DIRECTIVE_WIDTH:
        raise AssignError("bad directive: %r" % insn_text)
    directive, rest = parts[0].lower(), parts[1]
    width = DIRECTIVE_WIDTH[directive]
    out = []
    for tok in split_top(rest):
        try:
            val = eval_expr(tok)
        except (ValueError, NameError, SyntaxError):
            # 符号 / 可重定位
            if width == 8:
                return "ABS48"
            return "reject:reloc-narrow"
        out.append(("%0*x" % (width * 2, val & ((1 << (width * 8)) - 1))))
    return "".join(out)


def check_dirrej(code, expect):
    """未知/不支持指导符、超宽、窄字段重定位——返回 (got, ok)。"""
    parts = code.split(None, 1)
    directive = parts[0].lower()
    if directive not in DIRECTIVE_WIDTH:
        got = "unsupported" if directive in (".octa",) else "unknown"
        return got, (got == expect)
    width = DIRECTIVE_WIDTH[directive]
    if expect == "range":
        for tok in split_top(parts[1]):
            try:
                val = eval_expr(tok)
            except (ValueError, NameError, SyntaxError):
                return "symbol", False
            if not (-(1 << (width * 8 - 1)) <= val < (1 << (width * 8))):
                return "range", True
        return "in-range", False
    if expect == "reloc-narrow":
        try:
            eval_expr(parts[1])
            return "literal", False
        except (ValueError, NameError, SyntaxError):
            pass
        if width < 8:
            return "reloc-narrow", True
        return "wide", False
    return "n/a", False


def derive_multi_to_single(insn_text):
    """``-multiple-to-single`` 展开（spec §8 + §4.2）。"""
    raw_mn = insn_text.split(None, 1)[0]
    mnemonic = raw_mn.lower()
    rest = insn_text[len(raw_mn):].strip()
    ops = split_top(rest)
    suffix = mnemonic.split(".", 1)[1] if "." in mnemonic else ""
    width = {"b": 1, "w": 2, "t": 4, "o": 8}.get(suffix)

    if mnemonic.startswith(("ldm.", "stm.")):
        grp, addr = parse_group(ops[0]), parse_addr(ops[1])
        if not grp or not addr or width is None:
            raise AssignError("bad multi load/store: %r" % insn_text)
        base, offreg = addr[0], addr[1][0]
        n = grp[2] - grp[1] + 1
        seq = []
        for k in range(n):
            reg = "%s%d" % (grp[0], grp[1] + k)
            seq.append("%s {%s}, [%s, %s]" % (mnemonic, reg, base, offreg))
            step = width if k < n - 1 else -(n - 1) * width
            if n > 1:
                seq.append("add.si %s, %d" % (offreg, step))
        return seq

    # orri 块赋值 / 格式转换：每个元素一条（count = 1）
    dst, src = parse_group(ops[0]), parse_group(ops[1])
    if not dst or not src or (dst[2] - dst[1]) != (src[2] - src[1]):
        raise AssignError("bad block move: %r" % insn_text)
    n = dst[2] - dst[1] + 1
    return ["%s {%s%d}, {%s%d}" % (mnemonic, dst[0], dst[1] + k, src[0], src[1] + k)
            for k in range(n)]


def check_error(by_mnemonic, insn_text, token):
    """校验 ``insn_text`` 确实违反约束 ``token``（否则向量期望错误）。"""
    stripped = insn_text.strip()
    if token == "illegal-token":
        if not stripped.startswith("#"):
            raise AssignError("not an illegal '#' token: %r" % insn_text)
        return
    if token == "rd0-nonzero":
        mnemonic = stripped.split(None, 1)[0].lower()
        rest = stripped[len(mnemonic):].strip()
        ops = split_top(rest)
        r = parse_reg(ops[0]) if ops else None
        if mnemonic != "ret" or not r or r[1] != 0 or eval_expr(ops[1]) == 0:
            raise AssignError("not a ret rd0, non-zero: %r" % insn_text)
        return
    if token == "align4":
        addr_part = None
        for m in re.finditer(r"\[[^\]]*\]", insn_text):
            addr_part = m.group(0)
        if not addr_part:
            raise AssignError("no address operand: %r" % insn_text)
        addr = parse_addr(addr_part)
        if not addr or len(addr[1]) != 1:
            raise AssignError("bad address: %r" % insn_text)
        off = eval_expr(addr[1][0])
        if off % 4 == 0:
            raise AssignError("%r is 4-aligned, not an error" % insn_text)
        return
    if token.startswith("imm"):
        mnemonic = stripped.split(None, 1)[0].lower()
        rest = stripped[len(mnemonic):].strip()
        # 找立即数操作数（cmp.* 的第 3 个；其余指令的最后立即数）
        ops = split_top(rest)
        if mnemonic in ("cmp.ui", "cmp.si") or token in ("immu12",):
            val = eval_expr(ops[2])
        elif mnemonic in ("swym", "fence"):
            val = eval_expr(ops[0])
        else:
            # add.si / ret / shl.uo / set.zw ... 最后一个非寄存器、非地址操作数
            cand = None
            for o in ops:
                if parse_reg(o) or o.startswith("["):
                    continue
                cand = o
            val = eval_expr(cand)
        rec = None
        for r in by_mnemonic.get(mnemonic, []):
            try:
                assign_fields(r, rest)
                rec = r
                break
            except (AssignError, ValueError, KeyError):
                continue
        if rec is None:
            raise AssignError("no record for %r" % insn_text)
        f = imm_field(rec)
        hi, lo = field_span(f)
        width = hi - lo + 1
        if f.get("signed", False):
            lo_v, hi_v = -(1 << (width - 1)), (1 << (width - 1)) - 1
        else:
            lo_v, hi_v = 0, (1 << width) - 1
        if lo_v <= val <= hi_v:
            raise AssignError("%r value %d is in range [%d,%d]"
                              % (insn_text, val, lo_v, hi_v))
        exp_token = "%s%d" % ("imms" if f.get("signed") else "immu", width)
        if token != exp_token:
            raise AssignError("expected token %s but field is %s" % (token, exp_token))
        return
    raise AssignError("unknown err token %r" % token)


# --------------------------------------------------------------------------
# 向量文件解析
# --------------------------------------------------------------------------

ANNOT_RE = re.compile(r";\s*@(enc|exp|dir|dirrej|rej|err|mts|norm)\s+(.*)$")
CATEGORY_RE = re.compile(r";\s*@category\s+(\S+)")
# `; OBJ: {{[0-9a-f]+:}} <b0> <b1> <b2> <b3>{{.*}}<mnemonic>...` — lit FileCheck
# byte pattern (same shape as `tools/llvm/check_lit_bytes.py`).  TESTCASES-032t
# requires the encoding vectors to carry the object bytes inline; we re-derive
# them from opcodes.yaml and require them to equal the `@enc` value of the
# instruction on the following line (so changing either fails).
OBJ_RE = re.compile(
    r";\s*OBJ:\s+\{\{\[0-9a-f\]\+:\}\}\s+"
    r"([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})")


def norm_text(s):
    return re.sub(r"\s+", " ", s.strip())


def parse_vectors():
    files = sorted(glob.glob(VEC_GLOB))
    vectors = []          # (path, lineno, kind, code, expect, obj_bytes)
    seen_categories = {}
    for path in files:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        if not lines or "UNSUPPORTED:" not in lines[0]:
            raise ValueError("%s: 首行缺少 'UNSUPPORTED:' 标记" % path)
        cat = None
        pending_obj = None    # 最近一条 `; OBJ:` 的字节（供下一条 @enc 引用）
        for lineno, raw in enumerate(lines, 1):
            mc = CATEGORY_RE.search(raw)
            if mc and cat is None:
                cat = mc.group(1)
            elif mc:
                raise ValueError("%s:%d 重复 @category" % (path, lineno))
            mo = OBJ_RE.search(raw)
            if mo:
                pending_obj = "".join(mo.groups())
                continue
            ma = ANNOT_RE.search(raw)
            if not ma:
                continue
            code = raw[:raw.index(";")].strip()
            vectors.append((path, lineno, ma.group(1), code,
                            ma.group(2).strip(), pending_obj))
            pending_obj = None
        if cat is None:
            raise ValueError("%s: 缺少 @category 标记" % path)
        seen_categories[cat] = path
    return files, vectors, seen_categories


# --------------------------------------------------------------------------
# 校验
# --------------------------------------------------------------------------

def run(verbose=True):
    _, by_mnemonic = load_opcodes()
    try:
        files, vectors, categories = parse_vectors()
    except ValueError as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        return 1
    errors = []

    if not files:
        errors.append("未找到任何 m4-*.s 向量文件")

    missing = [c for c in CATEGORIES if c not in categories]
    if missing:
        errors.append("覆盖门控：缺少类别 %s" % ", ".join(missing))

    if verbose:
        print("== L1 MC 向量独立 oracle (TESTCASES-029t) ==")
        print("opcodes.yaml: %s" % os.path.relpath(OPCODES, REPO))
        print("向量文件 %d 个：%s" % (len(files), ", ".join(
            os.path.relpath(f, REPO) for f in files)))
        print("类别：%s" % ", ".join(sorted(categories)))
        print("-" * 72)

    for path, lineno, kind, code, expect, obj_bytes in vectors:
        loc = "%s:%d" % (os.path.relpath(path, REPO), lineno)
        try:
            if kind == "enc":
                got, _ = pick_and_encode(by_mnemonic, code)
                ok = (got == expect.lower())
                # `; OBJ:` 字节（若存在）必须等于同一独立派生编码
                if obj_bytes is not None and obj_bytes.lower() != got:
                    errors.append("%s: [enc/OBJ] %s — ; OBJ: 期望 %r，独立派生 %r"
                                  % (loc, code, obj_bytes, got))
                    if verbose:
                        print("FAIL %s [enc/OBJ] %r: ; OBJ: %r，独立派生 %r"
                              % (loc, code, obj_bytes, got))
                    continue
            elif kind == "exp":
                seq = expand_pseudo(code)
                for real in seq:
                    pick_and_encode(by_mnemonic, real)  # 展开项必须可编码
                ok = (norm_text(" ; ".join(seq)) == norm_text(expect))
                got = " ; ".join(seq)
            elif kind == "dir":
                got = derive_directive(code)
                ok = (got == expect)
            elif kind == "dirrej":
                got, ok = check_dirrej(code, expect)
            elif kind == "rej":
                mnemonic = code.split(None, 1)[0]
                if mnemonic not in DELETED_PSEUDO:
                    got = "not-in-deleted-set"
                    ok = False
                elif mnemonic in by_mnemonic:
                    got = "known-mnemonic"
                    ok = False
                else:
                    got = "unrecognized"
                    ok = (expect == "unrecognized")
            elif kind == "err":
                check_error(by_mnemonic, code, expect)
                got = expect
                ok = True
            elif kind == "mts":
                seq = derive_multi_to_single(code)
                ok = (norm_text(" ; ".join(seq)) == norm_text(expect))
                got = " ; ".join(seq)
            elif kind == "norm":
                a, _ = pick_and_encode(by_mnemonic, code)
                b, _ = pick_and_encode(by_mnemonic, expect)
                got = "%s == %s" % (a, b)
                ok = (a == b)
            else:  # pragma: no cover
                raise ValueError("unknown kind %r" % kind)
        except (AssignError, ValueError, KeyError) as exc:
            errors.append("%s: [%s] %s — %s" % (loc, kind, code, exc))
            if verbose:
                print("FAIL %s [%s] %r: %s" % (loc, kind, code, exc))
            continue
        if ok:
            if verbose:
                print("PASS %s [%s] %s" % (loc, kind, code))
        else:
            errors.append("%s: [%s] %s — 期望 %r，独立派生 %r"
                          % (loc, kind, code, expect, got))
            if verbose:
                print("FAIL %s [%s] %r: 期望 %r，独立派生 %r"
                      % (loc, kind, code, expect, got))

    if verbose:
        print("-" * 72)
        print("向量 %d 条，检查 %d 类覆盖，错误 %d 条"
              % (len(vectors), len(categories), len(errors)))

    if errors:
        for e in errors:
            print("ERROR: %s" % e, file=sys.stderr)
        return 1
    return 0


def main():
    return run(verbose=True)


if __name__ == "__main__":
    sys.exit(main())
