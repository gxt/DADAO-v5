#!/usr/bin/env python3
"""validate_cfx_vectors.py — L1 MC 向量独立 oracle（LLVM-060t）。

**独立 oracle**：本脚本**不**调用 ``llvm-mc``/``llvm-objdump``，也**不** import
或调用任何子进程模块（仅标准库 + PyYAML），从 **契约** 独立派生 `trap`/
`escape`/`cfx2rd`/`cfx2rc` 向量的期望编码，再与向量内联 ``@enc`` 比对：

  - 编码来源：``contracts/opcodes.yaml``（``value``/``fields`` 位域）；
  - 别名来源：``.tao/knowledge/contract-cfx-aliases.md``（标量 / 通用模板 /
    专有寄存器，含单下标数组，ADR-0017 D3/D4/D10）。

因此改一条期望字节、或改一条 ``.s`` 书写，本脚本都会**非零退出**。它测的是
**向量期望值**（契约投影），与实现无关——实现（llvm-mc）侧的编码由 lit +
``; OBJ:`` 与 `run.sh` 的字节比对承担。

向量文件 = 本目录 ``cfx2-*.s``（``-err.s`` 反例文件无 ``@enc``，自动跳过）。
每个矢量的输入是代码，期望值是行尾 ``; @enc <8hex>``；若该行前有 ``; OBJ:``
（lit FileCheck 字节），其 4 字节须等于同一独立派生编码。

退出码：有错误 ``exit(1)`` 并逐条打印 ``FAIL``；全部通过 ``exit(0)``。
"""
from __future__ import annotations

import glob
import os
import re
import sys

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(HERE)))))
OPCODES = os.path.join(REPO, "contracts", "opcodes.yaml")
ALIASES = os.path.join(REPO, ".tao", "knowledge", "contract-cfx-aliases.md")
# 向量目录默认 = 本目录；CFX_VEC_DIR 仅用于反例注入自检（在临时副本上运行，
# 避免污染真实仓库）。OPCODES/ALIASES 仍取仓库真源。
VEC_DIR = os.environ.get("CFX_VEC_DIR") or HERE
VEC_GLOB = os.path.join(VEC_DIR, "cfx2-*.s")

ENC_RE = re.compile(r";\s*@enc\s+([0-9a-fA-F]{8})\s*$")
OBJ_RE = re.compile(
    r";\s*OBJ:\s+\{\{\[0-9a-f\]\+:\}\}\s+"
    r"([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})")
SAFE_EXPR = re.compile(r"^[0-9a-fA-FxXbBoO\s()+\-*/%<>&|^~]+$")


# --------------------------------------------------------------------------
# 契约装载
# --------------------------------------------------------------------------

def load_opcodes():
    with open(OPCODES, "r", encoding="utf-8") as fh:
        recs = _yaml.safe_load(fh)
    return {r["mnemonic"]: r for r in recs}


def _cells(line: str):
    if not line.strip().startswith("|"):
        return None
    return [c.strip().strip("`") for c in line.strip().strip("|").split("|")]


def load_aliases():
    """Parse contract-cfx-aliases.md -> (scalar, generic, specific).

    scalar   : {cfx_<name>: code}
    generic  : [(tail, cg, rcLo, rcHi)]          # cfx_<cfxname>_<tail>
    specific : [(alias, cfxha, cg, rcLo, rcHi)]  # full alias
    """
    scalar, generic, specific = {}, [], []
    mode = None
    with open(ALIASES, "r", encoding="utf-8") as fh:
        for line in fh:
            cells = _cells(line)
            if not cells:
                continue
            if cells[0] == "别名" and len(cells) == 3:
                mode = "scalar"
                continue
            if cells[0] == "别名模板":
                mode = "generic"
                continue
            if cells[0] == "别名" and len(cells) == 5:
                mode = "specific"
                continue
            if all(set(c) <= set("-: ") for c in cells):
                continue  # separator row
            if mode == "scalar" and len(cells) == 3:
                name, code = cells[0], cells[1]
                if name.startswith("cfx_"):
                    scalar[name] = int(code)
            elif mode == "generic" and len(cells) == 4:
                tmpl, cg, rc = cells[0], cells[1], cells[2]
                if "⟨cfxname⟩" not in tmpl:
                    continue
                tail = tmpl.replace("cfx_⟨cfxname⟩_", "", 1)
                tail = re.sub(r"\[.*\]$", "", tail)
                lo, hi = parse_rc(rc)
                generic.append((tail, int(cg), lo, hi))
            elif mode == "specific" and len(cells) == 5:
                name, ha, cg, rc = cells[0], cells[1], cells[2], cells[3]
                lo, hi = parse_rc(rc)
                base = re.sub(r"\[.*\]$", "", name)
                specific.append((base, int(ha), int(cg), lo, hi))
    return scalar, generic, specific


def parse_rc(rc: str):
    """'0-63' -> (0,63); '8-15' -> (8,15); '3' -> (3,3); '0-(N-1)' -> (0,63)."""
    m = re.match(r"^(\d+)\s*[-−]\s*\(?N", rc.strip())
    if m:
        return int(m.group(1)), 63
    m = re.match(r"^(\d+)\s*[-−]\s*(\d+)$", rc.strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d+)$", rc.strip())
    if m:
        return int(m.group(1)), int(m.group(1))
    raise ValueError("unparsable rc column: %r" % rc)


# --------------------------------------------------------------------------
# 操作数 / 编码
# --------------------------------------------------------------------------

def split_top(s: str):
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


def eval_expr(s: str) -> int:
    s = s.strip()
    if not SAFE_EXPR.match(s):
        raise ValueError("unsafe expr: %r" % s)
    return eval(s, {"__builtins__": {}}, {})  # noqa: S307 (whitelisted)


def resolve_scalar(tok: str, scalar: dict) -> int:
    tok = tok.strip()
    m = re.match(r"^cfx(\d+)$", tok)
    if m:
        v = int(m.group(1))
        if not 0 <= v <= 63:
            raise ValueError("cfxha out of range: %s" % tok)
        return v
    if tok in scalar:
        return scalar[tok]
    raise ValueError("unknown cfx scalar: %r" % tok)


def resolve_reg(alias: str, scalar, generic, specific):
    m = re.match(r"^(.*)\[(\d+)\]$", alias.strip())
    if m:
        base, sub = m.group(1), int(m.group(2))
    else:
        base, sub = alias.strip(), None

    for name, ha, cg, lo, hi in specific:
        if name != base:
            continue
        if sub is None:
            if hi != lo:
                raise ValueError("%s is an array; a subscript is required" % base)
            return ha, cg, lo
        if not 0 <= sub <= hi - lo:
            raise ValueError("subscript %d out of range for %s" % (sub, base))
        return ha, cg, lo + sub

    for sname, code in scalar.items():
        if not base.startswith(sname + "_"):
            continue
        tail = base[len(sname) + 1:]
        for ttail, cg, lo, hi in generic:
            if ttail != tail:
                continue
            if sub is None:
                if hi != lo:
                    raise ValueError("%s is an array; a subscript is required"
                                     % base)
                return code, cg, lo
            if not 0 <= sub <= hi - lo:
                raise ValueError("subscript %d out of range for %s" % (sub, base))
            return code, cg, lo + sub
    raise ValueError("unknown cfx register alias: %r" % alias)


def field_span(fld):
    m = re.match(r"\[(\d+):(\d+)\]", fld["bits"])
    if not m:
        raise ValueError("bad bits: %r" % (fld["bits"],))
    return int(m.group(1)), int(m.group(2))


def derive(code: str, opcodes, scalar, generic, specific) -> str:
    mnem, _, rest = code.strip().partition(" ")
    rec = opcodes.get(mnem)
    if rec is None:
        raise ValueError("unknown mnemonic %r" % mnem)
    by_name = {f["name"]: f for f in rec["fields"]}
    ops = split_top(rest)
    assigns = {}

    if mnem in ("cfx2rd", "cfx2rc"):
        if len(ops) == 4:
            ha = resolve_scalar(ops[0], scalar)
            cg = int(re.fullmatch(r"cg(\d+)", ops[1]).group(1))
            rc = int(re.fullmatch(r"rc(\d+)", ops[2]).group(1))
            rd = int(re.fullmatch(r"rd(\d+)", ops[3]).group(1))
        elif len(ops) == 2:
            ha, cg, rc = resolve_reg(ops[0], scalar, generic, specific)
            rd = int(re.fullmatch(r"rd(\d+)", ops[1]).group(1))
        else:
            raise ValueError("cfx2rd/cfx2rc arity: %r" % code)
        assigns = {"cfxha": ha, "cghb": cg, "rchc": rc, "rdhd": rd}
    elif mnem == "trap":
        if len(ops) != 2:
            raise ValueError("trap arity: %r" % code)
        assigns = {"cfxha": resolve_scalar(ops[0], scalar),
                   "immu18": eval_expr(ops[1])}
    elif mnem == "escape":
        if len(ops) != 2 or not ops[1].startswith("["):
            raise ValueError("escape arity: %r" % code)
        inner = split_top(ops[1][1:-1])
        if len(inner) != 2 or inner[0] != "excp_cause_ip":
            raise ValueError("escape base must be excp_cause_ip: %r" % code)
        bytes_ = eval_expr(inner[1])
        if bytes_ % 4 != 0:
            raise ValueError("escape offset not %%4: %r" % code)
        assigns = {"cfxha": resolve_scalar(ops[0], scalar),
                   "imms18": bytes_ >> 2}
    else:
        raise ValueError("mnemonic not covered by this oracle: %r" % mnem)

    word = int(rec["value"], 16)
    for name, val in assigns.items():
        if name not in by_name:
            raise ValueError("record %s has no field %s" % (rec["id"], name))
        hi, lo = field_span(by_name[name])
        width = hi - lo + 1
        word |= (val & ((1 << width) - 1)) << lo
    return "%08x" % (word & 0xFFFFFFFF)


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

def run(verbose=True):
    opcodes = load_opcodes()
    scalar, generic, specific = load_aliases()
    files = sorted(glob.glob(VEC_GLOB))
    files = [f for f in files if not f.endswith("-err.s")]
    errors = []
    n = 0

    if verbose:
        print("== L1 MC cfx 向量独立 oracle (LLVM-060t) ==")
        print("opcodes  : %s" % os.path.relpath(OPCODES, REPO))
        print("aliases  : %s" % os.path.relpath(ALIASES, REPO))
        print("vectors  : %s" % ", ".join(os.path.relpath(f, REPO) for f in files))
        print("-" * 72)

    if not files:
        print("FAIL: 未找到 cfx2-*.s 向量文件", file=sys.stderr)
        return 1

    for path in files:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        pending_obj = None
        for lineno, raw in enumerate(lines, 1):
            mo = OBJ_RE.search(raw)
            if mo:
                pending_obj = "".join(mo.groups())
                continue
            me = ENC_RE.search(raw)
            if not me:
                continue
            code = raw[:raw.index(";")].strip()
            expect = me.group(1).lower()
            n += 1
            loc = "%s:%d" % (os.path.relpath(path, REPO), lineno)
            try:
                got = derive(code, opcodes, scalar, generic, specific)
            except (ValueError, AttributeError) as exc:
                errors.append("%s: %s — %s" % (loc, code, exc))
                if verbose:
                    print("FAIL %s %r: %s" % (loc, code, exc))
                pending_obj = None
                continue
            if got != expect:
                errors.append("%s: [@enc] %s — 期望 %s，独立派生 %s"
                              % (loc, code, expect, got))
                if verbose:
                    print("FAIL %s [@enc] %r: 期望 %r，独立派生 %r"
                          % (loc, code, expect, got))
            elif pending_obj is not None and pending_obj.lower() != got:
                errors.append("%s: [OBJ] %s — ; OBJ: %r，独立派生 %r"
                              % (loc, code, pending_obj, got))
                if verbose:
                    print("FAIL %s [OBJ] %r: ; OBJ: %r，独立派生 %r"
                          % (loc, code, pending_obj, got))
            elif verbose:
                print("PASS %s %s" % (loc, code))
            pending_obj = None

    if verbose:
        print("-" * 72)
        print("向量 %d 条，错误 %d 条" % (n, len(errors)))
    if errors:
        for e in errors:
            print("ERROR: %s" % e, file=sys.stderr)
        return 1
    if n == 0:
        print("FAIL: 未解析到任何 @enc 向量", file=sys.stderr)
        return 1
    return 0


def main():
    return run(verbose=True)


if __name__ == "__main__":
    sys.exit(main())
