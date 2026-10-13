#!/usr/bin/env python3
"""Validate the M4 (multi-TU / multi-section ELF) L3 vectors under
``tests/llvm/codegen/m4/``.

This is the **independent oracle** required by ``Process-05`` §2/§4 and the
project "Independent oracle" hard rule: the expected exit codes are re-derived
on the host from the **LLVM IR semantics** of the actual ``*.ll`` sources.  The
script **never** invokes ``llc``, ``ld.lld`` or QEMU -- there is no
``subprocess`` / ``os.system`` / ``Popen`` import anywhere in this file.

Checks (all fail-closed, exit non-zero on any failure):

  1. ``m4/expected.yaml`` exists, parses, has ``schema == codegen-elf-vectors-v1``.
  2. Every program record has ``name`` / ``category`` / ``sources`` /
     ``expected_exit_code`` / ``derivation`` (and an optional ``coverage`` list
     drawn from a fixed vocabulary).
  3. Multi-TU shape: every program lists **>= 2** distinct existing ``*.ll``
     sources; the union of all sources equals the ``*.ll`` files on disk
     exactly (no missing, no orphan, no reuse across programs).
  4. IR parse + host execution: a small interpreter of the IR subset actually
     used (integer arithmetic, ``icmp``, ``load``/``store``, ``getelementptr``,
     ``ptrtoint``/``zext``/``sext``/``trunc``, direct ``call``, ``br``/``ret``)
     runs ``@main`` over all TUs of a program and returns its ``i64`` value.
     ``expected_exit_code`` must equal ``returned & 0xFF`` **and** the
     hand-derived value recorded in this file, and must land in ``0x00..0x7F``
     (ADR-0004 D3 guest partition).
  5. Suite coverage derived **structurally from the IR** (not trusted from the
     manifest): multi-TU, cross-TU call, cross-TU global, ``.text`` /
     ``.rodata`` / ``.data`` / ``.bss`` sections, run-time global read/write,
     and the ABS48 / REL26 / REL20 / REL14 reloc *forms* (global address
     materialisation, undefined-symbol call, signed loop branch, eq/ne branch).

The interpreter is deliberately restricted: any construct outside the subset
raises and the check fails (no silent mis-modelling).  This is a necessary but
not sufficient oracle -- the true end-to-end ELF execution is owned by
``INTEG-016t``.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VEC_DIR = ROOT / "tests" / "llvm" / "codegen" / "m4"
EXPECTED_PATH = VEC_DIR / "expected.yaml"

SCHEMA = "codegen-elf-vectors-v1"
CATEGORIES = {"arithmetic", "memory", "branch", "call", "reloc"}

# Manifest coverage vocabulary (informational; coverage is re-derived from IR).
COVERAGE_VOCAB = {
    "multi-tu", "cross-tu.call", "cross-tu.global",
    "reloc.abs48", "reloc.rel26", "reloc.rel20", "reloc.rel14",
    "sec.text", "sec.rodata", "sec.data", "sec.bss",
    "data.runtime-write", "data.runtime-read",
    "branch.cond-eq", "branch.cond-loop",
    "ptr.diff-pos", "ptr.diff-neg",
}

# Coverage facts that the suite MUST exhibit (re-derived structurally from IR).
REQUIRED_COVERAGE = {
    "multi-tu", "cross-tu.call", "cross-tu.global",
    "reloc.abs48", "reloc.rel26", "reloc.rel20", "reloc.rel14",
    "sec.text", "sec.rodata", "sec.data", "sec.bss",
    "data.runtime-write", "data.runtime-read",
}

REQUIRED_FIELDS = ("name", "category", "sources", "expected_exit_code", "derivation")

# Independent hand derivation of every program, recorded separately from the
# interpreter so the two can be cross-checked.  See m4/README.md for the full
# reasoning; each value is plain 64-bit two's-complement arithmetic.
HAND_DERIVED = {
    "multi_tu_call": (20 + 11 + 11) & 0xFF,          # 42
    "multi_section_loop": (2 + 3 + 5 + 7 + 9 + 4) & 0xFF,  # 30
    "cross_tu_pdiff": (7 ^ ((3 - 10) & 0x7F)) & 0xFF,      # 0x7E = 126
    # TESTCASES-032t: bitwise complement (~x) at 64 bits, then fold 64->7.
    # y = ~0 ^ ~(-1) ^ ~0x0102030405060708 = 0x0102030405060708;
    # fold = (y * 0x9E3779B97F4A7C15) >> 57 = 0x6C = 108.
    "notneg_not": 0x6C,
    # TESTCASES-032t: signed negation (0 - x) at 8/16/32/64 bits, sign-extended,
    # XORed and folded 64->7.  x5 = 0x800000007FFF8040;
    # fold = (x5 * 0x9E3779B97F4A7C15) >> 57 = 0x08 = 8.
    "notneg_neg": 0x08,
}

MASK64 = (1 << 64) - 1
STEP_LIMIT = 1_000_000

LINKAGE_KEYWORDS = {
    "internal", "private", "external", "common", "weak", "weak_odr",
    "linkonce", "linkonce_odr", "available_externally", "hidden", "protected",
    "dso_local", "thread_local", "unnamed_addr", "local_unnamed_addr",
}


class IrError(Exception):
    """Raised on any IR construct the restricted interpreter cannot model."""


# ---------------------------------------------------------------------------
# IR parsing
# ---------------------------------------------------------------------------

def strip_comments(text: str) -> list:
    out = []
    for line in text.splitlines():
        i = line.find(";")
        if i >= 0:
            line = line[:i]
        out.append(line)
    return out


def type_size(ty: str) -> int:
    ty = ty.strip()
    m = re.match(r"\[(\d+)\s+x\s+(.+)\]$", ty)
    if m:
        return int(m.group(1)) * type_size(m.group(2).strip())
    if ty in ("i8", "i16", "i32", "i64"):
        return int(ty[1:]) // 8
    raise IrError(f"unsupported type size: {ty!r}")


def element_type(ty: str) -> str:
    m = re.match(r"\[(\d+)\s+x\s+(.+)\]$", ty.strip())
    if m:
        return element_type(m.group(2).strip())
    return ty.strip()


def last_token(s: str) -> str:
    return s.strip().rsplit(None, 1)[-1]


def split_toplevel(s: str) -> list:
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "[(":
            depth += 1
        elif ch in "])":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out]


def split_type_init(s: str):
    s = s.strip()
    if s.startswith("["):
        depth = 0
        for i, ch in enumerate(s):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return s[: i + 1], s[i + 1:].strip()
        raise IrError(f"unbalanced type in {s!r}")
    parts = s.split(None, 1)
    return parts[0], (parts[1].strip() if len(parts) > 1 else "")


def _strip_global_suffixes(body: str) -> str:
    while True:
        new = re.sub(r',\s*(?:align\s+\d+|section\s+"[^"]*")\s*$', "", body).strip()
        if new == body:
            return body
        body = new


def parse_global(line: str) -> dict:
    m = re.match(r"^@([\w.$-]+)\s*=\s*(.+)$", line.strip())
    if not m:
        raise IrError(f"bad global line: {line!r}")
    name, body = m.group(1), _strip_global_suffixes(m.group(2))
    linkage, kind, rest = "external", None, body
    while True:
        w = rest.split(None, 1)[0] if rest else ""
        if w in LINKAGE_KEYWORDS:
            linkage = w
            rest = rest.split(None, 1)[1] if len(rest.split(None, 1)) > 1 else ""
            continue
        if w in ("constant", "global"):
            kind = w
            rest = rest.split(None, 1)[1] if len(rest.split(None, 1)) > 1 else ""
            break
        break
    if kind is None:
        raise IrError(f"global without constant/global keyword: {line!r}")
    ty, init = split_type_init(rest)
    return {"name": name, "linkage": linkage, "kind": kind, "ty": ty, "init": init}


def global_kind(g: dict) -> str:
    """Mirror LLVM's ELF section choice: constant -> .rodata, non-constant with
    a non-zero initialiser -> .data, otherwise .bss (NOBITS)."""
    if g["kind"] == "constant":
        return "rodata"
    init = g["init"]
    if init in ("", "zeroinitializer", "0"):
        return "bss"
    return "data"


def _parse_arg_list(argstr: str):
    args = []
    for a in split_toplevel(argstr):
        a = a.strip()
        if not a or a == "...":
            continue
        m = re.match(r"(.+?)\s+%([\w.$-]+)$", a)
        if not m:
            raise IrError(f"bad function argument: {a!r}")
        args.append((m.group(1).strip(), m.group(2)))
    return args


def parse_source(path: Path) -> dict:
    lines = strip_comments(path.read_text(encoding="utf-8"))
    globals_defs, globals_ext = {}, set()
    funcs, func_decls = {}, set()
    global_refs, calls = set(), set()
    has_icmp_eq = has_icmp_loop = has_cond_br = False
    has_ptrtoint = has_sub = False
    has_global_store = has_global_load = False

    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("@"):
            buf = line
            while not (buf.count("[") == buf.count("]")):
                if i + 1 >= len(lines):
                    raise IrError(f"unterminated global definition: {line!r}")
                i += 1
                buf += " " + lines[i]
            g = parse_global(buf)
            if g["linkage"] == "external" and g["init"] == "":
                globals_ext.add(g["name"])
            else:
                globals_defs[g["name"]] = g
            i += 1
            continue
        if s.startswith("define "):
            buf = line
            while "{" not in buf:
                if i + 1 >= len(lines):
                    raise IrError(f"unterminated define header: {line!r}")
                i += 1
                buf += "\n" + lines[i]
            header, _, inline = buf.partition("{")
            m = re.match(r"^define\s+([\w]+)\s+@([\w.$-]+)\((.*?)\)\s*([^{]*)$",
                         header.strip() + " ")
            if not m:
                raise IrError(f"bad define header: {header!r}")
            retty, fname, argstr = m.group(1), m.group(2), m.group(3)
            params = _parse_arg_list(argstr)
            body_lines = []
            if inline.strip():
                body_lines.append(inline)
            i += 1
            while i < len(lines) and lines[i].strip() != "}":
                body_lines.append(lines[i])
                i += 1
            i += 1  # skip closing brace
            blocks, order, cur = {}, [], None
            for bl in body_lines:
                st = bl.strip()
                if not st:
                    continue
                lm = re.match(r"^([\w.$-]+):$", st)
                if lm:
                    cur = lm.group(1)
                    blocks[cur] = []
                    order.append(cur)
                    continue
                if cur is None:
                    raise IrError(f"instruction before any label in @{fname}: {st!r}")
                blocks[cur].append(st)
                # structural feature collection
                if re.search(r"\bicmp\s+(eq|ne)\b", st):
                    has_icmp_eq = True
                if re.search(r"\bicmp\s+(slt|sle|sgt|sge|ult|ule|ugt|uge)\b", st):
                    has_icmp_loop = True
                if re.match(r"^br\s+i1\b", st):
                    has_cond_br = True
                if re.search(r"\bptrtoint\b", st):
                    has_ptrtoint = True
                if re.match(r"^%\S+\s*=\s*sub\s", st):
                    has_sub = True
                if re.match(r"^store\b", st) and "@" in st:
                    has_global_store = True
                if re.match(r"^%\S+\s*=\s*load\b", st) and "@" in st:
                    has_global_load = True
                cm = re.search(r"\bcall\s+\S+\s+@([\w.$-]+)\(", st)
                if cm:
                    calls.add(cm.group(1))
                elif re.search(r"\b(?:load|store|getelementptr|ptrtoint)\b", st):
                    for gm in re.finditer(r"@([\w.$-]+)", st):
                        global_refs.add(gm.group(1))
            funcs[fname] = {"params": params, "blocks": blocks, "order": order,
                            "retty": retty, "entry": order[0] if order else None}
            continue
        if s.startswith("declare "):
            m = re.match(r"^declare\s+[\w]+\s+@([\w.$-]+)\(", s)
            if m:
                func_decls.add(m.group(1))
            i += 1
            continue
        i += 1

    return {
        "path": path,
        "globals_defs": globals_defs,
        "globals_ext": globals_ext,
        "funcs": funcs,
        "func_decls": func_decls,
        "global_refs": global_refs,
        "calls": calls,
        "has_cond_eq": has_icmp_eq and has_cond_br,
        "has_cond_loop": has_icmp_loop and has_cond_br,
        "has_ptrtoint": has_ptrtoint,
        "has_sub": has_sub,
        "has_global_store": has_global_store,
        "has_global_load": has_global_load,
    }


# ---------------------------------------------------------------------------
# Restricted host-side IR interpreter (the independent oracle)
# ---------------------------------------------------------------------------

class Interp:
    def __init__(self, sources):
        self.globals = {}   # name -> (addr, size, ty)
        self.mem = {}       # addr -> byte
        self.funcs = {}
        self.steps = 0
        parsed = [parse_source(p) for p in sources]
        base = 0x1000
        for src in parsed:
            for name, g in sorted(src["globals_defs"].items()):
                if name in self.globals:
                    raise IrError(f"duplicate global definition: @{name}")
                size = type_size(g["ty"])
                base = (base + 7) & ~7
                self.globals[name] = (base, size, g["ty"])
                self._init_global(base, g["ty"], g["init"])
                base += size
                base = (base + 7) & ~7
        for src in parsed:
            for name, f in src["funcs"].items():
                self.funcs[name] = f

    # -- memory ----------------------------------------------------------
    def _mem_write(self, addr, n, val):
        val &= (1 << (8 * n)) - 1
        for k in range(n):
            self.mem[addr + k] = (val >> (8 * (n - 1 - k))) & 0xFF

    def _mem_read(self, addr, n):
        v = 0
        for k in range(n):
            v = (v << 8) | (self.mem.get(addr + k, 0) & 0xFF)
        return v

    def _init_global(self, addr, ty, init):
        if init in ("", "zeroinitializer"):
            return
        if ty.startswith("["):
            elem = element_type(ty)
            esz = type_size(elem)
            inner = init.strip()
            if not (inner.startswith("[") and inner.endswith("]")):
                raise IrError(f"bad array initializer: {init!r}")
            for k, item in enumerate(split_toplevel(inner[1:-1])):
                if not item:
                    continue
                self._mem_write(addr + k * esz, esz, int(last_token(item), 0))
            return
        self._mem_write(addr, type_size(ty), int(init, 0))

    # -- values ----------------------------------------------------------
    def value(self, tok, frame):
        tok = tok.strip()
        if tok.startswith("%"):
            key = tok[1:]
            if key not in frame:
                raise IrError(f"use of undefined value {tok}")
            return frame[key]
        if tok.startswith("@"):
            name = tok[1:]
            if name not in self.globals:
                raise IrError(f"reference to undefined global @{name}")
            return self.globals[name][0]
        if tok == "true":
            return 1
        if tok == "false":
            return 0
        return int(tok, 0)

    # -- execution -------------------------------------------------------
    def run_main(self):
        if "main" not in self.funcs:
            raise IrError("no @main defined")
        return self.call("main", []) & MASK64

    def call(self, name, args):
        if name not in self.funcs:
            raise IrError(f"call to undefined function @{name}")
        f = self.funcs[name]
        if len(args) != len(f["params"]):
            raise IrError(f"@${name}: arity {len(args)} != {len(f['params'])}")
        frame = {}
        for (_pty, pname), val in zip(f["params"], args):
            frame[pname] = val & MASK64
        label = f["entry"]
        while True:
            kind, payload = self._exec_block(f, frame, label)
            if kind == "ret":
                return payload
            label = payload

    def _exec_block(self, f, frame, label):
        if label not in f["blocks"]:
            raise IrError(f"branch to unknown label %{label}")
        for ins in f["blocks"][label]:
            self.steps += 1
            if self.steps > STEP_LIMIT:
                raise IrError("instruction step limit exceeded")
            kind, payload = self._exec(ins, frame)
            if kind in ("br", "ret"):
                return kind, payload
        raise IrError(f"block %{label} fell through without a terminator")

    def _exec(self, ins, frame):
        m = re.match(r"^br\s+label\s+%([\w.$-]+)$", ins)
        if m:
            return "br", m.group(1)
        m = re.match(
            r"^br\s+i1\s+([%@][\w.$-]*|-?\d+),\s*label\s+%([\w.$-]+),\s*label\s+%([\w.$-]+)$",
            ins,
        )
        if m:
            return "br", (m.group(2) if self.value(m.group(1), frame) else m.group(3))
        if ins.startswith("ret "):
            rest = ins[4:].strip()
            if rest.startswith("void"):
                return "ret", 0
            return "ret", self.value(rest.split(None, 1)[1].strip(), frame) & MASK64
        if ins.startswith("store"):
            m = re.match(r"^store\s+(?:volatile\s+)?(i\d+)\s+(.+?),\s*(.+)$", ins)
            if not m:
                raise IrError(f"bad store: {ins!r}")
            bits = int(m.group(1)[1:])
            vstr = m.group(2).strip()
            rest = re.sub(r",\s*align\s+\d+\s*$", "", m.group(3)).strip()
            addr = self.value(last_token(rest), frame)
            self._mem_write(addr, bits // 8, self.value(vstr, frame))
            return "next", None
        if ins.startswith("unreachable"):
            raise IrError("unreachable executed")
        m = re.match(r"^%([\w.$-]+)\s*=\s*(.+)$", ins)
        if not m:
            raise IrError(f"unsupported instruction: {ins!r}")
        dst, rhs = m.group(1), m.group(2).strip()
        frame[dst] = self._eval_rhs(rhs, frame)
        return "next", None

    def _eval_rhs(self, rhs, frame):
        m = re.match(
            r"^(add|sub|mul|and|or|xor|shl|lshr|ashr)\s+i(\d+)\s+(.+?),\s*(.+)$", rhs)
        if m:
            op, bits = m.group(1), int(m.group(2))
            a = self.value(m.group(3), frame)
            b = self.value(m.group(4), frame)
            return self._arith(op, a, b, bits)

        m = re.match(
            r"^icmp\s+(eq|ne|slt|sle|sgt|sge|ult|ule|ugt|uge)\s+i(\d+)\s+(.+?),\s*(.+)$",
            rhs)
        if m:
            pred, bits = m.group(1), int(m.group(2))
            a = self.value(m.group(3), frame)
            b = self.value(m.group(4), frame)
            return self._icmp(pred, a, b, bits)

        m = re.match(r"^load\s+(?:volatile\s+)?(i\d+)\s*,\s*(.+)$", rhs)
        if m:
            bits = int(m.group(1)[1:])
            rest = re.sub(r",\s*align\s+\d+\s*$", "", m.group(2)).strip()
            addr = self.value(last_token(rest), frame)
            return self._mem_read(addr, bits // 8)

        m = re.match(r"^getelementptr\s+(?:inbounds\s+)?(.+)$", rhs)
        if m:
            parts = split_toplevel(m.group(1))
            if len(parts) < 2:
                raise IrError(f"bad getelementptr: {rhs!r}")
            ty0 = parts[0]
            base = self.value(last_token(parts[1]), frame)
            indices = [self.value(last_token(p), frame) for p in parts[2:]]
            offset = 0
            if indices:
                offset += indices[0] * type_size(ty0)
            if len(indices) >= 2:
                offset += indices[1] * type_size(element_type(ty0))
            return (base + offset) & MASK64

        m = re.match(r"^ptrtoint\s+(.+?)\s+([%@][\w.$-]+)\s+to\s+i\d+$", rhs)
        if m:
            return self.value(m.group(2), frame) & MASK64

        m = re.match(r"^(zext|sext|trunc)\s+i(\d+)\s+([%@][\w.$-]+)\s+to\s+i(\d+)$", rhs)
        if m:
            op, srcbits, tok, dstbits = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
            v = self.value(tok, frame)
            if op == "zext":
                return v & ((1 << srcbits) - 1)
            if op == "sext":
                return self._signed(v, srcbits) & MASK64
            return v & ((1 << dstbits) - 1)

        m = re.match(r"^call\s+(i\d+|void|ptr)\s+@([\w.$-]+)\((.*)\)$", rhs)
        if m:
            retty, fname, argstr = m.group(1), m.group(2), m.group(3)
            args = []
            if argstr.strip():
                args = [self.value(last_token(a), frame) for a in split_toplevel(argstr)]
            rv = self.call(fname, args)
            return rv if retty != "void" else 0

        raise IrError(f"unsupported rhs: {rhs!r}")

    @staticmethod
    def _signed(v, bits):
        v &= (1 << bits) - 1
        if v >> (bits - 1):
            return v - (1 << bits)
        return v

    def _arith(self, op, a, b, bits):
        mask = (1 << bits) - 1
        a &= mask
        b &= mask
        if op == "add":
            r = a + b
        elif op == "sub":
            r = a - b
        elif op == "mul":
            r = a * b
        elif op == "and":
            r = a & b
        elif op == "or":
            r = a | b
        elif op == "xor":
            r = a ^ b
        elif op == "shl":
            r = a << (b & (bits - 1))
        elif op == "lshr":
            r = (a & mask) >> (b & (bits - 1))
        elif op == "ashr":
            r = self._signed(a, bits) >> (b & (bits - 1))
        else:  # pragma: no cover
            raise IrError(f"unknown arithmetic op {op}")
        return r & mask

    def _icmp(self, pred, a, b, bits):
        mask = (1 << bits) - 1
        ua, ub = a & mask, b & mask
        sa, sb = self._signed(a, bits), self._signed(b, bits)
        if pred == "eq":
            return int(ua == ub)
        if pred == "ne":
            return int(ua != ub)
        if pred == "slt":
            return int(sa < sb)
        if pred == "sle":
            return int(sa <= sb)
        if pred == "sgt":
            return int(sa > sb)
        if pred == "sge":
            return int(sa >= sb)
        if pred == "ult":
            return int(ua < ub)
        if pred == "ule":
            return int(ua <= ub)
        if pred == "ugt":
            return int(ua > ub)
        if pred == "uge":
            return int(ua >= ub)
        raise IrError(f"unknown icmp predicate {pred}")  # pragma: no cover


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------

class Checker:
    def __init__(self) -> None:
        self.passes = 0
        self.fails = []

    def check(self, name, cond, detail=""):
        if cond:
            self.passes += 1
            print(f"[PASS] {name}")
        else:
            self.fails.append(name)
            print(f"[FAIL] {name} {detail}".rstrip())


def load_expected(ck: Checker):
    if not EXPECTED_PATH.is_file():
        ck.check("expected-file-exists", False, f"missing {EXPECTED_PATH}")
        return None
    ck.check("expected-file-exists", True)
    try:
        data = yaml.safe_load(EXPECTED_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        ck.check("yaml-parses", False, f"{exc}")
        return None
    ck.check("yaml-parses", True)
    ck.check("schema", isinstance(data, dict) and data.get("schema") == SCHEMA,
             f"schema != {SCHEMA!r}")
    programs = data.get("programs") if isinstance(data, dict) else None
    ck.check("programs-nonempty", isinstance(programs, list) and len(programs) > 0,
             "programs must be a non-empty list")
    return programs if isinstance(programs, list) else []


def check_records(ck: Checker, programs):
    fields_ok = cats_ok = vocab_ok = range_ok = deriv_ok = src_ok = True
    names, sources_all = [], []
    for i, rec in enumerate(programs):
        if not isinstance(rec, dict):
            fields_ok = False
            continue
        for field in REQUIRED_FIELDS:
            if field not in rec:
                fields_ok = False
                print(f"       record #{i} missing field {field!r}")
        name = rec.get("name")
        if isinstance(name, str):
            names.append(name)
        if rec.get("category") not in CATEGORIES:
            cats_ok = False
            print(f"       record #{i} bad category {rec.get('category')!r}")
        cov = rec.get("coverage")
        if cov is None:
            pass  # optional field: the mandated schema is the 5 fields listed above
        elif not (isinstance(cov, list) and cov):
            vocab_ok = False
            print(f"       record #{i} coverage must be a non-empty list when present")
        else:
            bad = [x for x in cov if not isinstance(x, str) or x not in COVERAGE_VOCAB]
            if bad:
                vocab_ok = False
                print(f"       record #{i} unknown coverage token(s): {bad}")
        code = rec.get("expected_exit_code")
        if isinstance(code, bool) or not isinstance(code, int) or not (0 <= code <= 0x7F):
            range_ok = False
            print(f"       record #{i} expected_exit_code out of 0x00..0x7F: {code!r}")
        deriv = rec.get("derivation")
        if not isinstance(deriv, str) or not deriv.strip():
            deriv_ok = False
            print(f"       record #{i} empty derivation")
        srcs = rec.get("sources")
        if not (isinstance(srcs, list) and len(srcs) >= 2
                and all(isinstance(s, str) for s in srcs)):
            src_ok = False
            print(f"       record #{i} requires >= 2 string sources (multi-TU)")
        else:
            sources_all.extend(srcs)

    ck.check("record-fields", fields_ok)
    ck.check("categories-known", cats_ok)
    ck.check("coverage-vocab", vocab_ok)
    ck.check("exit-code-range-0x00-0x7f", range_ok)
    ck.check("derivation-nonempty", deriv_ok)
    ck.check("name-unique", len(names) == len(set(names)), "duplicate program names")
    ck.check("multi-tu-sources", src_ok, "every program needs >= 2 sources")

    # sources refer to existing files, no duplicates, no reuse across programs
    missing = [s for s in sources_all if not (VEC_DIR / s).is_file()]
    dup = len(sources_all) != len(set(sources_all))
    ck.check("sources-exist", not missing, f"missing={missing}")
    ck.check("sources-unique", not dup, "a source is listed by more than one program")

    files = sorted(p.name for p in VEC_DIR.glob("*.ll"))
    ck.check("files-match", sorted(sources_all) == files,
             f"yaml={sorted(sources_all)} disk={files}")


def derive_coverage(programs):
    """Re-derive coverage facts structurally, from the IR itself."""
    facts = {
        "multi-tu": True,
        "cross-tu.call": False,
        "cross-tu.global": False,
        "reloc.abs48": False,
        "reloc.rel26": False,
        "reloc.rel20": False,
        "reloc.rel14": False,
        "sec.text": False,
        "sec.rodata": False,
        "sec.data": False,
        "sec.bss": False,
        "data.runtime-write": False,
        "data.runtime-read": False,
    }
    for rec in programs:
        if not isinstance(rec, dict):
            continue
        srcs = rec.get("sources")
        if not (isinstance(srcs, list) and len(srcs) >= 2):
            facts["multi-tu"] = False
            continue
        if any(not (VEC_DIR / s).is_file() for s in srcs):
            facts["multi-tu"] = False
            continue
        parsed = [parse_source(VEC_DIR / s) for s in srcs]
        if any(p["funcs"] for p in parsed):
            facts["sec.text"] = True
        defined_global = {}
        for idx, p in enumerate(parsed):
            for name, g in p["globals_defs"].items():
                kind = global_kind(g)
                facts[f"sec.{kind}"] = True
                defined_global.setdefault(name, idx)
        defined_func = {}
        for idx, p in enumerate(parsed):
            for name in p["funcs"]:
                defined_func.setdefault(name, idx)
        for idx, p in enumerate(parsed):
            if p["global_refs"]:
                facts["reloc.abs48"] = True
            if p["has_global_store"]:
                facts["data.runtime-write"] = True
            if p["has_global_load"]:
                facts["data.runtime-read"] = True
            if p["has_cond_loop"]:
                facts["reloc.rel20"] = True
            if p["has_cond_eq"]:
                facts["reloc.rel14"] = True
            for callee in p["calls"]:
                if defined_func.get(callee, idx) != idx:
                    facts["cross-tu.call"] = True
                    facts["reloc.rel26"] = True
            for gref in p["global_refs"]:
                if defined_global.get(gref, idx) != idx:
                    facts["cross-tu.global"] = True
    return facts


def check_programs(ck: Checker, programs):
    # coverage derived from IR
    facts = derive_coverage(programs)
    for token in sorted(REQUIRED_COVERAGE):
        ck.check(f"coverage[{token}]", facts.get(token, False),
                 "required coverage fact not present in IR")
    # no manifest record may reference an unknown set of sources
    for rec in programs:
        if not isinstance(rec, dict):
            continue
        name = rec.get("name")
        if not isinstance(name, str):
            continue
        srcs = rec.get("sources")
        if not isinstance(srcs, list) or len(srcs) < 2:
            continue
        if any(not (VEC_DIR / s).is_file() for s in srcs):
            ck.check(f"oracle[{name}]", False, "missing source file(s)")
            continue
        # oracle: host execution of the IR subset
        try:
            interp = Interp([VEC_DIR / s for s in srcs])
            value = interp.run_main()
        except IrError as exc:
            ck.check(f"oracle[{name}]", False, f"IR error: {exc}")
            continue
        exit_code = value & 0xFF
        ck.check(f"oracle[{name}]", value <= 0x7F,
                 f"returned {value!r} out of 0x00..0x7F")
        ck.check(f"oracle-vs-expected[{name}]",
                 exit_code == rec.get("expected_exit_code"),
                 f"expected={rec.get('expected_exit_code')!r} oracle={exit_code!r}")
        hand = HAND_DERIVED.get(name)
        ck.check(f"hand-vs-oracle[{name}]", hand == value,
                 f"hand={hand!r} oracle={value!r}")


def main() -> int:
    ck = Checker()
    programs = load_expected(ck)
    if programs:
        check_records(ck, programs)
        check_programs(ck, programs)
    print("-" * 60)
    if ck.fails:
        print(f"validate_elf_vectors: FAIL ({len(ck.fails)} failed, {ck.passes} passed)")
        for name in ck.fails:
            print(f"  - {name}")
        return 1
    print(f"validate_elf_vectors: PASS ({ck.passes} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
