#!/usr/bin/env python3
"""SimRISC IDL 子集解析器（Python 标准库）——`.idl` → AST + 构造签名门控（m17-idl-002）。

为什么
------
M17 的执行器用 Python 重写 IDL 前端（用户 2026-11-20：不用 Ruby/`idlc`）。UDB 的
`idl.treetop` 有 652 行语法，本仓只用到其中一小部分——**实现口径的唯一依据**是
[`idl/syntax-subset.md`](syntax-subset.md)（68 类构造，逐类现场计数 + 首个出处）。
本模块只实现该册 §10「必须覆盖」列出的构造；§8 的未使用构造（`while`/`assert`/
`sizeof`/`struct`/`bitfield`/`tuple`/`include`/`fetch`/`X[]`/`CSR[]`/`$encoding`/
复合赋值/变量作复制次数）与 UDB 其余语法**一律显式报错**（`UnsupportedConstruct`），
绝不静默跳过。

本模块**不做语义**：不求值、不做类型推导（那是 `m17-idl-003`）。字面量**原样保留
文本与位宽标注**（`width`/`signed`/`base`/`digits` 逐字留档，不转成整数）——有符号
字面量与无位宽字面量的位宽在 `width-rules.md` §7 里是 `U04`/`U07`（本仓规范未定义），
解析器不得内置假设。同理 `` `* `` 结果宽度（`U06`）、普通二元运算结果宽度与截断（`U10`）
只由 AST 形状表达，不推进任何宽度推导。

AST 节点 ↔ 构造表（`syntax-subset.md`，逐个 S-ID 对齐）
-------------------------------------------------------
| 构造 | AST 表达 |
| --- | --- |
| S01 `# id:` | `Operation(id, body)`（行级切分，不进语法） |
| S02 `#` 注释 | 词法丢弃（不产节点） |
| S03 `%version:` | `SourceUnit.version`（只记字符串） |
| S04 `enum` | `EnumDecl` + `EnumMember` |
| S05 `Enum::Member` | `EnumRef` |
| S06 `Bits<N>` | `BitsType(width=原文)`——**位宽原文留档，不判值** |
| S07 `U32` | `U32Type` |
| S08 `Boolean` | `BooleanType`；字面量 `true`/`false` = `BoolLit` |
| S09 带初值声明 | `VarDecl(init=…)` |
| S66 无初值声明 | `VarDecl(init=None)` |
| S10 `function` | `FunctionDecl` + `Param` + `Description`（散文不进构造签名） |
| S11 `?` 后缀名 | 名字的一部分（`Call.name`/`FunctionDecl.name`） |
| S12 `if` | `If(cond, then, orelse)` |
| S13 `else if` | `orelse` 位置的嵌套 `If` |
| S14 `else { … }` | `Block` |
| S15 `for` | `For(init, cond, step, body)` |
| S16 `return` | `Return(expr=None 表示无值)` |
| S17 `++` | `Incr(op="++")` |
| S18 赋值 | `Assign(lhs, rhs)` |
| S19 切片赋值 | 左值为 `Slice` |
| S20 单比特赋值 | 左值为 `Index` |
| S21–S23 加宽运算 | `Binary(op="`+"/"`<<"/"`*")`（宽度公式 `U06`/`U10` 未定义 ⇒ 不推导） |
| S24–S30 二元运算 | `Binary(op=原文)` |
| S31 三目 | `Ternary` |
| S32 拼接 | `Concat` |
| S33 复制 | `Replicate(count=IntLit, value=…)` |
| S34 位切片 | `Slice(base, msb, lsb)` |
| S35/S36 取位/链式下标 | `Index`（可嵌套：`rd[x][31:0]` = `Slice(Index(…))`） |
| S37 `$signed(x)` | `SignedCast` |
| S38–S40 字面量 | `IntLit(raw/width/signed/base/digits)`——**原文留档，不求值**（`U04`/`U07` 未定义） |
| S41/S48–S59 调用 | `Call(name, args)`；语句位置的调用 = `ExprStmt` |
| S42–S47 寄存器组访问 | `Index(Ident("rd"/"rb"/"rf"/"ra"/"fo"/"ft"), …)` |
| S60–S65 不使用构造 | **显式报错**（`UnsupportedConstruct`，绝不静默跳过） |

漂移防护
--------
每个 operation / function / enum / 全局常量的 AST 冻结成构造签名（AST 规范化
S 表达式的 sha256 + 节点数 + 各节点种类计数），落在 `idl/idl_parse_fixture.json`。
`--check` 现场重算逐条比对；改了 `.idl` 或改了本解析器的 AST 形状 ⇒ 红，必须显式
`--update` 并评审 diff。**fixture 是冻结物，不是判据真源**：判据真源是 `.idl` +
`syntax-subset.md`。

用法
----
* `python3 idl/idl_parser.py --check`    # 全量解析 + fixture + 拒绝/接受集（`make check-idl-parse`）
* `python3 idl/idl_parser.py --update`   # 重新生成 fixture（改 `.idl` 后显式执行）
* `python3 idl/idl_parser.py --stats`    # 打印现场统计（文件/operation/function/enum）
* `python3 idl/idl_parser.py --ast <id>` # 打印某条 operation 的 AST（S 表达式）
* `python3 idl/idl_parser.py --self-test`# 临时树注入自检（各类注入须 FAIL，还原须回绿）
* `--root DIR`：在另一棵同布局的树内运行（自检/注入用）

退出码：0 = 通过；1 = 任一检查失败。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
REPO = _HERE.parent
IDL_REL = "idl"
LIB_REL = "idl/lib"
FIXTURE_REL = "idl/idl_parse_fixture.json"
CASES_REL = "idl/idl_parse_cases.toml"
OPCODES_REL = "contracts/opcodes.yaml"

ID_LINE_RE = re.compile(r"^#\s*id:\s*(\S+)\s*$")
VERSION_LINE_RE = re.compile(r"^%version:\s*(\S+)\s*$")


# ── 错误类型 ────────────────────────────────────────────────────────────────

class IdlError(Exception):
    """语法错误（含「构造不在子集内」）。"""


class UnsupportedConstruct(IdlError):
    """子集外构造：必须显式报错，不得静默跳过（`syntax-subset.md` §8）。"""


# ── AST ─────────────────────────────────────────────────────────────────────

class Node:
    """一种节点：`kind` + 有序字段。字段顺序参与规范化（构造签名据此冻结）。"""

    __slots__ = ("kind", "fields", "line")

    def __init__(self, kind: str, line: int = 0, **fields):
        self.kind = kind
        self.fields = fields
        self.line = line

    def __repr__(self) -> str:                       # 便于调试
        return sexpr(self)


def sexpr(value) -> str:
    """规范化 S 表达式：同 AST ⇒ 同文本（digest 与 fixture 据此比对）。"""
    if isinstance(value, Node):
        parts = [value.kind]
        parts += [f"{name}={sexpr(val)}" for name, val in value.fields.items()]
        return "(" + " ".join(parts) + ")"
    if isinstance(value, list):
        return "[" + " ".join(sexpr(v) for v in value) + "]"
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def walk(value):
    """深度优先遍历节点（支持顶层为 list）。"""
    if isinstance(value, Node):
        yield value
        for val in value.fields.values():
            yield from walk(val)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def signature(value) -> dict:
    """构造签名：AST 规范化文本的 sha256 + 节点数 + 各节点种类计数。"""
    kinds: dict[str, int] = {}
    total = 0
    for node in walk(value):
        kinds[node.kind] = kinds.get(node.kind, 0) + 1
        total += 1
    return {
        "sha256": hashlib.sha256(sexpr(value).encode("utf-8")).hexdigest(),
        "nodes": total,
        "kinds": dict(sorted(kinds.items())),
    }


# ── 词法 ────────────────────────────────────────────────────────────────────

# 多字符运算符按长度降序匹配（`>>>=` 先于 `>>>` 先于 `>>`，`<<=` 先于 `<<`）。
_OPS = [
    ">>>", "<<", ">>", "<=", ">=", "==", "!=", "&&", "||", "++", "--",
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=", ">>>=",
    "`+", "`*", "`<<", "::",
    "+", "-", "*", "/", "%", "&", "|", "^", "~", "!", "(", ")", "{", "}", "[", "]",
    ";", ",", ":", "?", "<", ">", "=",
]
_OPS.sort(key=len, reverse=True)

COMPOUND_ASSIGN = frozenset({"+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
                             "<<=", ">>=", ">>>="})

# 词法：Verilog 定宽/不定宽字面量（`6'd0`/`'shFD`/`'s0`）、C 风格十六进制/二进制、十进制。
# 一律只切 token，**不判值、不补位宽**（U04/U07 未定义，见模块 docstring）。
RE_VERILOG = re.compile(r"\d*'[sS]?[dhboDHBO]?[0-9a-fA-F_]+")
RE_SIGNED_ZERO = re.compile(r"\d+s\b")        # `0s`：无撇号的有符号字面量（U04，原文留档）
RE_HEX = re.compile(r"0[xX][0-9a-fA-F_]+")
RE_BIN = re.compile(r"0[bB][01_]+")
RE_DEC = re.compile(r"\d[\d_]*")
RE_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
RE_BUILTIN = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*")


@dataclass
class Tok:
    kind: str        # ident / int / op / desc / eof
    text: str
    line: int
    col: int


def literal_fields(raw: str) -> dict:
    """把字面量原文拆成 `width`/`signed`/`base`/`digits`（**原文留档，不求值**）。"""
    m = re.match(r"(\d*)'([sS]?)([dhboDHBO]?)([0-9a-fA-F_]+)$", raw)
    if m:
        return {"raw": raw, "width": m.group(1) or None, "signed": bool(m.group(2)),
                "base": (m.group(3) or "d").lower(), "digits": m.group(4)}
    m = re.match(r"(\d+)s$", raw)                       # `0s`（U04：位宽未定义，不猜）
    if m:
        return {"raw": raw, "width": None, "signed": True, "base": "d", "digits": m.group(1)}
    low = raw[:2].lower()
    if low == "0x":
        return {"raw": raw, "width": None, "signed": False, "base": "h", "digits": raw[2:]}
    if low == "0b":
        return {"raw": raw, "width": None, "signed": False, "base": "b", "digits": raw[2:]}
    return {"raw": raw, "width": None, "signed": False, "base": "d", "digits": raw}


class Lexer:
    """`.idl` 词法：`#` 行尾注释、`description { … }` 自由文本块、字面量、运算符。"""

    def __init__(self, text: str, path: str, line_offset: int = 0):
        self.text = text
        self.path = path
        self.i = 0
        self.line = 1 + line_offset
        self.col = 1

    def error(self, msg: str) -> None:
        raise IdlError(f"{self.path}:{self.line}:{self.col}: {msg}")

    def _advance_to(self, j: int) -> None:
        seg = self.text[self.i:j]
        nl = seg.count("\n")
        if nl:
            self.line += nl
            self.col = len(seg) - seg.rfind("\n")
        else:
            self.col += len(seg)
        self.i = j

    def tokenize(self) -> list[Tok]:
        text, n = self.text, len(self.text)
        toks: list[Tok] = []
        while self.i < n:
            ch = text[self.i]
            if ch == "\n":
                self.i += 1
                self.line += 1
                self.col = 1
                continue
            if ch in " \t\r":
                self.i += 1
                self.col += 1
                continue
            if ch == "#":                              # 行尾注释：到行尾（保留换行给上面处理）
                j = text.find("\n", self.i)
                self._advance_to(n if j < 0 else j)
                continue

            start_line, start_col = self.line, self.col

            if ch.isdigit() or ch == "'":
                m = RE_VERILOG.match(text, self.i)
                if m is None and ch.isdigit():
                    m = (RE_SIGNED_ZERO.match(text, self.i) or RE_HEX.match(text, self.i)
                         or RE_BIN.match(text, self.i) or RE_DEC.match(text, self.i))
                if m is None:
                    self.error(f"无法识别的字面量（以 {ch!r} 开头）")
                toks.append(Tok("int", m.group(0), start_line, start_col))
                self._advance_to(m.end())
                continue

            if ch.isalpha() or ch == "_":
                m = RE_IDENT.match(text, self.i)
                name, end = m.group(0), m.end()
                # `?` 属于名字的一部分（谓词函数 `is_sp_nan?`，S11）：仅当其后（可隔空格）
                # 紧跟 `(`（调用）或 `{`（声明）时归并，否则留给三目运算符（`a ? b : c`）。
                if end < n and text[end] == "?":
                    k = end + 1
                    while k < n and text[k] in " \t":
                        k += 1
                    if k < n and text[k] in "({":
                        name += "?"
                        end += 1
                if name == "description":
                    # 自由文本块：散文里会引述伪码（`+Inf`/`floor(…)`），不是语法 ⇒ 整段吞掉
                    j = end
                    while j < n and text[j] in " \t\r\n":
                        j += 1
                    if j < n and text[j] == "{":
                        depth, k = 0, j
                        while k < n:
                            if text[k] == "{":
                                depth += 1
                            elif text[k] == "}":
                                depth -= 1
                                if depth == 0:
                                    break
                            k += 1
                        if k >= n:
                            self.error("`description {` 自由文本块未闭合")
                        raw = text[j + 1:k]
                        toks.append(Tok("ident", name, start_line, start_col))
                        toks.append(Tok("desc", raw, start_line, start_col))
                        self._advance_to(k + 1)
                        continue
                toks.append(Tok("ident", name, start_line, start_col))
                self._advance_to(end)
                continue

            if ch == "$":
                m = RE_BUILTIN.match(text, self.i)
                if m is None:
                    self.error("`$` 后缺内建名")
                toks.append(Tok("ident", m.group(0), start_line, start_col))
                self._advance_to(m.end())
                continue

            matched = False
            for op in _OPS:
                if text.startswith(op, self.i):
                    toks.append(Tok("op", op, start_line, start_col))
                    self._advance_to(self.i + len(op))
                    matched = True
                    break
            if matched:
                continue
            if ch == '"':
                self.error('字符串字面量不在子集内（本语言无字符串；`include "…"` 是 §8 子集外构造）')
            self.error(f"无法识别的字符 {ch!r}")
        toks.append(Tok("eof", "<eof>", self.line, self.col))
        return toks


# ── 语法 ────────────────────────────────────────────────────────────────────

# 子集外构造（`syntax-subset.md` §8：脚本断言这些构造在 13 个源里出现 0 次）。
UNSUPPORTED = {
    "while": "`while` 循环（S60）",
    "assert": "`assert`（S61）",
    "sizeof": "`sizeof`（S61）",
    "struct": "`struct`（S62）",
    "bitfield": "`bitfield`（S62）",
    "tuple": "`tuple` 多返回值（S62）",
    "include": "`include`（S62）",
    "fetch": "`fetch` 块（S63）",
    "switch": "`switch`",
    "break": "`break`",
    "continue": "`continue`",
    "builtin": "`builtin function`（S10 只计带 body 的 `function`，本仓 0 次）",
    "implemented": "`implemented?`",
    "implemented?": "`implemented?`",
}

# 关键字（不能当表达式/类型/形参名用）
RESERVED = frozenset({"if", "else", "for", "return", "function", "returns", "arguments",
                      "description", "body", "enum", "true", "false"})

# 运算符优先级（低 → 高；同级左结合）。加宽运算（S21–S23）与普通运算符同层。
BIN_LEVELS: list[tuple[str, ...]] = [
    ("||",),
    ("&&",),
    ("|",),
    ("^",),
    ("&",),
    ("==", "!="),
    ("<", "<=", ">", ">="),
    ("<<", ">>", ">>>", "`<<"),
    ("+", "-", "`+"),
    ("*", "/", "%", "`*"),
]
UNARY_OPS = frozenset({"!", "~", "-", "+"})


class Parser:
    def __init__(self, toks: list[Tok], path: str):
        self.toks = toks
        self.path = path
        self.i = 0

    # -- 基础 ---------------------------------------------------------------
    def peek(self, k: int = 0) -> Tok:
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def at(self, text: str) -> bool:
        return self.peek().text == text

    def take(self) -> Tok:
        tok = self.peek()
        if tok.kind != "eof":
            self.i += 1
        return tok

    def error(self, tok: Tok, msg: str) -> None:
        raise IdlError(f"{self.path}:{tok.line}:{tok.col}: {msg}"
                       f"（实得 `{tok.text}`）")

    def unsupported(self, tok: Tok, why: str | None = None) -> None:
        label = why or UNSUPPORTED.get(tok.text, f"`{tok.text}`")
        raise UnsupportedConstruct(
            f"{self.path}:{tok.line}:{tok.col}: 构造不在子集内：{label}"
            f"——`idl/syntax-subset.md` §8 断言该构造在 13 个源里 0 次，"
            f"解析器不实现（不得静默跳过）")

    def expect(self, text: str) -> Tok:
        tok = self.peek()
        if tok.text != text:
            self.error(tok, f"期望 `{text}`")
        return self.take()

    def expect_ident(self, what: str) -> str:
        tok = self.peek()
        if tok.kind != "ident" or tok.text in RESERVED or tok.text.startswith("$"):
            self.error(tok, f"期望{what}")
        self.take()
        return tok.text

    # -- 文件级 -------------------------------------------------------------
    def parse_program(self) -> list[Node]:
        """文件级声明（`enum` / `function` / 全局常量）。"""
        decls: list[Node] = []
        while self.peek().kind != "eof":
            tok = self.peek()
            if tok.kind == "ident" and tok.text in UNSUPPORTED:
                self.unsupported(tok)
            if tok.kind == "ident" and tok.text == "enum":
                decls.append(self.parse_enum())
            elif tok.kind == "ident" and tok.text == "function":
                decls.append(self.parse_function())
            elif tok.kind == "ident" and self.looks_like_decl():
                decls.append(self.parse_decl())
            else:
                self.error(tok, "文件级只允许 `enum` / `function` / 类型化全局声明")
        return decls

    def parse_enum(self) -> Node:
        tok = self.expect("enum")
        name = self.expect_ident("枚举名")
        self.expect("{")
        members: list[Node] = []
        while not self.at("}"):
            mtok = self.peek()
            mname = self.expect_ident("枚举成员名")
            val = self.peek()
            if val.kind != "int":
                self.error(val, f"枚举成员 `{mname}` 缺字面值")
            self.take()
            members.append(Node("EnumMember", line=mtok.line, name=mname,
                                value=Node("IntLit", line=val.line, **literal_fields(val.text))))
        self.expect("}")
        if not members:
            self.error(tok, f"枚举 `{name}` 没有任何成员")
        return Node("EnumDecl", line=tok.line, name=name, members=members)

    def parse_function(self) -> Node:
        tok = self.expect("function")
        name = self.expect_ident("函数名")
        self.expect("{")
        returns: Node | None = None
        args: list[Node] = []
        desc: Node | None = None
        body: Node | None = None
        while not self.at("}"):
            sect = self.peek()
            if sect.kind != "ident":
                self.error(sect, "function 段只允许 `returns`/`arguments`/`description`/`body`")
            if sect.text == "returns":
                if returns is not None:
                    self.error(sect, "`returns` 段重复")
                self.take()
                returns = self.parse_type()
            elif sect.text == "arguments":
                if args:
                    self.error(sect, "`arguments` 段重复")
                self.take()
                args = self.parse_arguments()
            elif sect.text == "description":
                if desc is not None:
                    self.error(sect, "`description` 段重复")
                self.take()
                dtok = self.peek()
                if dtok.kind != "desc":
                    self.error(dtok, "`description` 后须紧跟 `{ … }` 自由文本块")
                self.take()
                desc = Node("Description", line=dtok.line)
            elif sect.text == "body":
                if body is not None:
                    self.error(sect, "`body` 段重复")
                self.take()
                body = self.parse_block()
            else:
                self.error(sect, "function 段只允许 `returns`/`arguments`/`description`/`body`")
        self.expect("}")
        if body is None:
            self.error(tok, f"函数 `{name}` 缺 `body`（`builtin function` 不在子集内）")
        return Node("FunctionDecl", line=tok.line, name=name, returns=returns,
                    arguments=args, description=desc, body=body)

    def parse_arguments(self) -> list[Node]:
        args: list[Node] = []
        while True:
            typ = self.parse_type()
            nt = self.peek()
            if nt.kind != "ident" or nt.text in RESERVED or nt.text.startswith("$"):
                self.error(nt, "形参缺名字（`arguments` 每项须为「类型 + 名字」）")
            self.take()
            args.append(Node("Param", line=nt.line, type=typ, name=nt.text))
            if self.at(","):
                self.take()
                continue
            return args

    def parse_type(self) -> Node:
        tok = self.peek()
        if tok.kind != "ident" or tok.text.startswith("$") or tok.text in RESERVED:
            self.error(tok, "此处需要类型标注（`Bits<N>` / `U32` / `Boolean` / 枚举名）")
        self.take()
        if tok.text == "Bits":
            self.expect("<")
            wid = self.peek()
            if wid.kind != "int":
                self.error(wid, "`Bits<N>` 的 N 必须是字面常量")
            self.take()
            self.expect(">")
            return Node("BitsType", line=tok.line, width=wid.text)
        if tok.text == "U32":
            return Node("U32Type", line=tok.line)
        if tok.text == "Boolean":
            return Node("BooleanType", line=tok.line)
        return Node("NamedType", line=tok.line, name=tok.text)

    # -- 语句 ---------------------------------------------------------------
    def looks_like_decl(self) -> bool:
        """`Bits<N>`/`U32`/`Boolean`，或「枚举类型名 + 变量名」两连标识符。"""
        tok = self.peek()
        if tok.kind != "ident":
            return False
        if tok.text in ("Bits", "U32", "Boolean"):
            return True
        return self.peek(1).kind == "ident"

    def parse_decl(self, expect_semicolon: bool = True) -> Node:
        tok = self.peek()
        typ = self.parse_type()
        name = self.expect_ident("变量名")
        init: Node | None = None
        if self.at("="):
            self.take()
            init = self.parse_expr()
        if expect_semicolon:
            self.expect(";")
        return Node("VarDecl", line=tok.line, type=typ, name=name, init=init)

    def parse_statements(self) -> list[Node]:
        out: list[Node] = []
        while self.peek().kind != "eof" and not self.at("}"):
            out.append(self.parse_statement())
        return out

    def parse_block(self) -> Node:
        tok = self.expect("{")
        body = self.parse_statements()
        self.expect("}")
        return Node("Block", line=tok.line, body=body)

    def parse_statement(self) -> Node:
        tok = self.peek()
        if tok.kind == "ident":
            if tok.text in UNSUPPORTED:
                self.unsupported(tok)
            if tok.text == "if":
                return self.parse_if()
            if tok.text == "for":
                return self.parse_for()
            if tok.text == "return":
                return self.parse_return()
            if tok.text in RESERVED:
                self.error(tok, "此处不允许该关键字")
        if tok.text == "{":
            return self.parse_block()
        if self.looks_like_decl():
            return self.parse_decl()
        return self.parse_simple_stmt()

    def parse_if(self) -> Node:
        tok = self.expect("if")
        self.expect("(")
        cond = self.parse_expr()
        self.expect(")")
        then = self.parse_block()
        orelse: Node | None = None
        if self.at("else"):
            self.take()
            # `else if` = orelse 位置的嵌套 If（S13）；`else { … }` = 块（S14）
            orelse = self.parse_if() if self.at("if") else self.parse_block()
        return Node("If", line=tok.line, cond=cond, then=then, orelse=orelse)

    def parse_for(self) -> Node:
        tok = self.expect("for")
        self.expect("(")
        if self.looks_like_decl():
            init: Node | None = self.parse_decl(expect_semicolon=False)
        elif self.at(";"):
            init = None
        else:
            init = self.parse_assign_tail(self.parse_expr(), terminator=None)
        self.expect(";")
        cond = self.parse_expr()
        self.expect(";")
        step = self.parse_for_step()
        self.expect(")")
        body = self.parse_block()
        return Node("For", line=tok.line, init=init, cond=cond, step=step, body=body)

    def parse_for_step(self) -> Node:
        tok = self.peek()
        target = self.parse_expr()
        if self.at("++"):
            self.take()
            return Node("Incr", line=tok.line, target=target, op="++")
        if self.at("--"):
            self.unsupported(self.peek(), "自减 `--` 不在子集内（S17 只有 `++`）")
        if self.at("="):
            self.take()
            return Node("Assign", line=tok.line, lhs=target, rhs=self.parse_expr())
        if self.peek().text in COMPOUND_ASSIGN:
            self.unsupported(self.peek(), f"复合赋值 `{self.peek().text}`（§5：本仓 0 次）")
        self.error(self.peek(), "`for` 步进只支持 `x++` 或 `x = …`")

    def parse_return(self) -> Node:
        tok = self.expect("return")
        if self.at(";"):
            self.take()
            return Node("Return", line=tok.line, expr=None)
        expr = self.parse_expr()
        self.expect(";")
        return Node("Return", line=tok.line, expr=expr)

    def parse_simple_stmt(self) -> Node:
        tok = self.peek()
        lhs = self.parse_expr()
        if self.at("="):
            self.take()
            return self.parse_assign_tail(lhs, terminator=";", line=tok.line)
        if self.peek().text in COMPOUND_ASSIGN:
            self.unsupported(self.peek(), f"复合赋值 `{self.peek().text}`（§5：本仓 0 次）")
        if self.at("++") or self.at("--"):
            optok = self.take()
            self.expect(";")
            return Node("Incr", line=tok.line, target=lhs, op=optok.text)
        if lhs.kind == "Call":
            self.expect(";")
            return Node("ExprStmt", line=tok.line, expr=lhs)
        self.error(self.peek(), "不是赋值语句（左值后须有 `=`）")

    def parse_assign_tail(self, lhs: Node, terminator: str | None, line: int = 0) -> Node:
        rhs = self.parse_expr()
        if terminator is not None:
            self.expect(terminator)
        return Node("Assign", line=line or lhs.line, lhs=lhs, rhs=rhs)

    # -- 表达式 -------------------------------------------------------------
    def parse_expr(self) -> Node:
        return self.parse_ternary()

    def parse_ternary(self) -> Node:
        cond = self.parse_binary(0)
        if self.at("?"):
            tok = self.take()
            then = self.parse_expr()
            self.expect(":")
            orelse = self.parse_ternary()      # 右结合
            return Node("Ternary", line=tok.line, cond=cond, then=then, orelse=orelse)
        return cond

    def parse_binary(self, level: int) -> Node:
        if level >= len(BIN_LEVELS):
            return self.parse_unary()
        left = self.parse_binary(level + 1)
        ops = BIN_LEVELS[level]
        while self.peek().kind == "op" and self.peek().text in ops:
            tok = self.take()
            right = self.parse_binary(level + 1)
            left = Node("Binary", line=tok.line, op=tok.text, left=left, right=right)
        return left

    def parse_unary(self) -> Node:
        tok = self.peek()
        if tok.kind == "op" and tok.text in UNARY_OPS:
            self.take()
            return Node("Unary", line=tok.line, op=tok.text, operand=self.parse_unary())
        if tok.kind == "ident" and tok.text.startswith("$"):
            if tok.text != "$signed":
                self.unsupported(tok, f"内建 `{tok.text}`（S37 只用到 `$signed`）")
            self.take()
            self.expect("(")
            expr = self.parse_expr()
            self.expect(")")
            return Node("SignedCast", line=tok.line, expr=expr)
        return self.parse_postfix()

    def parse_postfix(self) -> Node:
        node = self.parse_primary()
        while True:
            tok = self.peek()
            if tok.text == "[":
                self.take()
                first = self.parse_expr()
                if self.at(":"):
                    self.take()
                    second = self.parse_expr()
                    self.expect("]")
                    node = Node("Slice", line=tok.line, base=node, msb=first, lsb=second)
                else:
                    self.expect("]")
                    node = Node("Index", line=tok.line, base=node, index=first)
            elif tok.text == "(":
                if node.kind != "Ident":
                    self.error(tok, "只有函数名可以被调用")
                name = node.fields["name"]
                self.take()
                args: list[Node] = []
                if not self.at(")"):
                    args.append(self.parse_expr())
                    while self.at(","):
                        self.take()
                        args.append(self.parse_expr())
                self.expect(")")
                node = Node("Call", line=tok.line, name=name, args=args)
            else:
                return node

    def parse_primary(self) -> Node:
        tok = self.take()
        if tok.kind == "int":
            return Node("IntLit", line=tok.line, **literal_fields(tok.text))
        if tok.kind == "desc":
            self.error(tok, "`description` 块只能出现在 `function` 声明里")
        if tok.kind == "ident":
            if tok.text.startswith("$"):
                self.unsupported(tok, f"内建 `{tok.text}`（S37 只用到 `$signed`）")
            if tok.text in ("true", "false"):        # Boolean 字面量（S08 一类）
                return Node("BoolLit", line=tok.line, value=(tok.text == "true"))
            if tok.text in UNSUPPORTED:
                self.unsupported(tok)
            if tok.text in RESERVED:
                self.error(tok, "关键字不能作表达式")
            if self.at("::"):
                self.take()
                mtok = self.peek()
                if mtok.kind != "ident":
                    self.error(mtok, "`Enum::Member` 缺成员名")
                self.take()
                return Node("EnumRef", line=tok.line, enum=tok.text, member=mtok.text)
            if tok.text in ("X", "CSR") and self.at("["):
                self.unsupported(tok, f"RISC-V 式 `{tok.text}[…]`（S64）")
            return Node("Ident", line=tok.line, name=tok.text)
        if tok.text == "(":
            expr = self.parse_expr()
            self.expect(")")
            return expr
        if tok.text == "{":
            return self.parse_brace(tok)
        self.error(tok, "表达式里出现意外 token")

    def parse_brace(self, tok: Tok) -> Node:
        first, second = self.peek(), self.peek(1)
        if first.kind == "int" and second.text == "{":
            self.take()
            self.expect("{")
            value = self.parse_expr()
            self.expect("}")
            self.expect("}")
            return Node("Replicate", line=tok.line,
                        count=Node("IntLit", line=first.line, **literal_fields(first.text)),
                        value=value)
        if first.kind == "ident" and second.text == "{":
            self.unsupported(first, "变量作复制次数（S65：`{N{a}}` 的 N 必须是字面常量）")
        items = [self.parse_expr()]
        while self.at(","):
            self.take()
            items.append(self.parse_expr())
        self.expect("}")
        return Node("Concat", line=tok.line, items=items)


# ── 源文件 → SourceUnit ─────────────────────────────────────────────────────

@dataclass
class Operation:
    id: str
    line: int
    body: list[Node]


@dataclass
class SourceUnit:
    path: str                     # 相对仓库根（posix），如 `idl/SimRISC-01.idl`
    version: str | None
    decls: list[Node]
    operations: list[Operation]


def _split_version(lines: list[str], path: str) -> tuple[list[str], str | None]:
    """取出 `%version:` 文件头（行级，S03）；只允许出现在首个代码行之前。"""
    version: str | None = None
    seen_code = False
    out = list(lines)
    for i, line in enumerate(lines):
        m = VERSION_LINE_RE.match(line)
        if m:
            if seen_code:
                raise IdlError(f"{path}:{i + 1}: `%version:` 只能出现在文件头（首个代码行之前）")
            if version is not None:
                raise IdlError(f"{path}:{i + 1}: 重复的 `%version:` 行")
            version = m.group(1)
            out[i] = ""                       # 抹掉正文，保留行号
            continue
        if line.strip() and not line.lstrip().startswith("#"):
            seen_code = True
    return out, version


def parse_text(text: str, path: str = "<memory>") -> SourceUnit:
    """解析一份 `.idl` 源文本：`# id:` 分块 → operation；否则整文件是声明。"""
    if "\r" in text:
        raise IdlError(f"{path}: 含 CR 行尾，拒绝解析（按 LF 切行）")
    lines = text.split("\n")
    id_lines = [(i, m.group(1)) for i, m in
                ((i, ID_LINE_RE.match(line)) for i, line in enumerate(lines)) if m]

    if not id_lines:
        body, version = _split_version(lines, path)
        toks = Lexer("\n".join(body), path).tokenize()
        return SourceUnit(path=path, version=version,
                          decls=Parser(toks, path).parse_program(), operations=[])

    version: str | None = None
    header, version = _split_version(lines[:id_lines[0][0]], path)
    for i, line in enumerate(header):
        if line.strip() and not line.lstrip().startswith("#"):
            raise IdlError(f"{path}:{i + 1}: 首个 `# id:` 之前不得有内容（{line!r}）")

    operations: list[Operation] = []
    seen: set[str] = set()
    for k, (start, op_id) in enumerate(id_lines):
        end = id_lines[k + 1][0] if k + 1 < len(id_lines) else len(lines)
        if op_id in seen:
            raise IdlError(f"{path}:{start + 1}: operation id 重复: `{op_id}`")
        seen.add(op_id)
        chunk = lines[start:end]
        while chunk and not chunk[-1].strip():
            chunk.pop()
        if len(chunk) < 2:
            raise IdlError(f"{path}:{start + 1}: operation `{op_id}` 只有 `# id:` 行、没有正文")
        toks = Lexer("\n".join(chunk), path, line_offset=start).tokenize()
        parser = Parser(toks, path)
        body = parser.parse_statements()
        if parser.peek().kind != "eof":
            parser.error(parser.peek(), "operation 正文没有解析完")
        operations.append(Operation(id=op_id, line=start + 1, body=body))
    return SourceUnit(path=path, version=version, decls=[], operations=operations)


# ── 仓库级装载 ──────────────────────────────────────────────────────────────

def idl_files(root: Path) -> list[Path]:
    """扫描面 = `idl/SimRISC-*.idl` + `idl/lib/*.idl`（与 `syntax-subset.md` §1 一致）。"""
    books = sorted((root / IDL_REL).glob("SimRISC-*.idl"))
    libs = sorted((root / LIB_REL).glob("*.idl"))
    if not books or not libs:
        raise IdlError(f"{IDL_REL}: 扫描面为空（books={len(books)}, lib={len(libs)}）")
    return books + libs


def load_units(root: Path) -> list[SourceUnit]:
    units: list[SourceUnit] = []
    seen_ops: dict[str, str] = {}
    for path in idl_files(root):
        unit = parse_text(path.read_text(encoding="utf-8"), path.relative_to(root).as_posix())
        for op in unit.operations:
            if op.id in seen_ops:
                raise IdlError(f"{unit.path}:{op.line}: operation id 跨文件重复: "
                               f"`{op.id}`（已见于 {seen_ops[op.id]}）")
            seen_ops[op.id] = unit.path
        units.append(unit)
    return units


def opcode_ids(root: Path) -> list[str]:
    """`contracts/opcodes.yaml` 的 `- id:` 清单（独立对账，不从 IDL 自证）。"""
    text = (root / OPCODES_REL).read_text(encoding="utf-8")
    ids = re.findall(r"^-\s+id:\s*(\S+)\s*$", text, re.M)
    if not ids:
        raise IdlError(f"{OPCODES_REL}: 没有解析到 `- id:` 条目")
    return ids


# ── fixture（构造签名冻结）──────────────────────────────────────────────────

def build_fixture(units: list[SourceUnit]) -> dict:
    files: dict[str, dict] = {}
    for unit in units:
        entry: dict = {"operations": {}, "enums": {}, "globals": {}, "functions": {}}
        if unit.version is not None:
            entry["version"] = unit.version
        for decl in unit.decls:
            if decl.kind == "EnumDecl":
                entry["enums"][decl.fields["name"]] = signature(decl)
            elif decl.kind == "FunctionDecl":
                entry["functions"][decl.fields["name"]] = signature(decl)
            elif decl.kind == "VarDecl":
                entry["globals"][decl.fields["name"]] = signature(decl)
            else:                                   # 不会发生：parse_program 只产这三类
                raise IdlError(f"{unit.path}: 未预期的文件级节点 `{decl.kind}`")
        for op in unit.operations:
            entry["operations"][op.id] = signature(op.body)
        files[unit.path] = entry
    return {
        "schema": 1,
        "note": "idl/idl_parser.py --update 生成；改 .idl 或改 AST 形状后须显式重生成并评审 diff。"
                "sha256 = 该 operation/function/enum/常量的 AST 规范化 S 表达式摘要；kinds = 节点种类计数。",
        "files": files,
    }


def dump_fixture(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _compare_group(where: str, want: dict, have: dict, out: list[str], limit: int = 8) -> None:
    missing = sorted(set(want) - set(have))
    extra = sorted(set(have) - set(want))
    if missing:
        out.append(f"{where}: fixture 里有、现场解析没有: {', '.join(missing[:limit])}")
    if extra:
        out.append(f"{where}: 现场解析多出（fixture 未冻结）: {', '.join(extra[:limit])}")
    for name in sorted(set(want) & set(have)):
        w, h = want[name], have[name]
        if w.get("sha256") != h.get("sha256"):
            out.append(f"{where}.{name}: AST 摘要变了（fixture {w.get('sha256','')[:12]} ≠ "
                       f"现场 {h.get('sha256','')[:12]}）")
        elif w.get("nodes") != h.get("nodes"):
            out.append(f"{where}.{name}: 节点数变了（fixture {w.get('nodes')} ≠ 现场 {h.get('nodes')}）")
        elif w.get("kinds") != h.get("kinds"):
            out.append(f"{where}.{name}: 节点种类计数变了（fixture {w.get('kinds')} ≠ "
                       f"现场 {h.get('kinds')}）")


def compare_fixture(want: dict, have: dict) -> list[str]:
    out: list[str] = []
    wfiles, hfiles = want.get("files", {}), have.get("files", {})
    for path in sorted(set(wfiles) - set(hfiles)):
        out.append(f"{path}: fixture 里有、现场没有（源文件被删/改名？）")
    for path in sorted(set(hfiles) - set(wfiles)):
        out.append(f"{path}: 现场多出源文件（fixture 未冻结）")
    for path in sorted(set(wfiles) & set(hfiles)):
        w, h = wfiles[path], hfiles[path]
        for key in ("version",):
            if w.get(key) != h.get(key):
                out.append(f"{path}.{key}: fixture {w.get(key)!r} ≠ 现场 {h.get(key)!r}")
        for key, label in (("operations", "operation"), ("functions", "function"),
                           ("enums", "enum"), ("globals", "全局常量")):
            _compare_group(f"{path}:{label}", w.get(key, {}), h.get(key, {}), out)
    return out


# ── 独立 oracle：源码正则统计 ⇔ AST 节点计数 ────────────────────────────────
#
# fixture 只能证明「AST 没变」（自比）。本节用**另一条代码路径**（源码正则，不经语法分析）
# 独立数一遍构造出现次数，与 AST 的节点计数逐项对账：解析器少收/多收语句、漏掉调用、
# 把 `Bits<N>` 吃掉、把 `else if` 丢支——都会在这里露出来。

CALL_RE = re.compile(r"(?<![\w$.])([A-Za-z_]\w*\??)\s*\(")
CALL_SKIP = frozenset({"if", "for", "while", "return", "assert", "sizeof"})
CROSS_CHECKS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("`if (`", re.compile(r"\bif\s*\("), "If"),
    ("`for (`", re.compile(r"\bfor\s*\("), "For"),
    ("`return`", re.compile(r"\breturn\b"), "Return"),
    ("`++`", re.compile(r"\+\+"), "Incr"),
    ("`Enum::Member`", re.compile(r"::"), "EnumRef"),
    ("`$signed(`", re.compile(r"\$signed\s*\("), "SignedCast"),
    ("`Bits<`", re.compile(r"\bBits<"), "BitsType"),
)
DESC_OPEN_RE = re.compile(r"^\s*description\s*\{\s*$")
DESC_CLOSE_RE = re.compile(r"^\s*\}\s*$")


def code_text(text: str) -> str:
    """抹掉 `#` 行尾注释与 `description { … }` 自由文本（与 `subset_stats.py` 同口径）。

    散文里会引述伪码（`` `floor(…)` ``、`` `raise(…)` `` 之类），按字面统计会把散文误计成语法。
    """
    out: list[str] = []
    in_desc = False
    for line in text.split("\n"):
        if in_desc:
            if DESC_CLOSE_RE.match(line):
                in_desc = False
            out.append("")
            continue
        if DESC_OPEN_RE.match(line):
            in_desc = True
            out.append("")
            continue
        out.append(line.split("#", 1)[0])
    return "\n".join(out)


def cross_check(unit: SourceUnit, raw: str) -> tuple[list[str], set[str]]:
    """源码正则统计 ⇔ AST 节点计数。返回（不一致明细, 该文件出现的 call 名字集合）。"""
    code = code_text(raw)
    ast_calls: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for node in walk([unit.decls, [op.body for op in unit.operations]]):
        kinds[node.kind] = kinds.get(node.kind, 0) + 1
        if node.kind == "Call":
            name = node.fields["name"]
            ast_calls[name] = ast_calls.get(name, 0) + 1

    problems: list[str] = []
    rx_calls: dict[str, int] = {}
    for m in CALL_RE.finditer(code):
        name = m.group(1)
        if name in CALL_SKIP:
            continue
        rx_calls[name] = rx_calls.get(name, 0) + 1
    for name in sorted(set(rx_calls) | set(ast_calls)):
        if rx_calls.get(name, 0) != ast_calls.get(name, 0):
            problems.append(f"{unit.path}: 调用 `{name}(` 源码 {rx_calls.get(name, 0)} 处 ⇔ "
                            f"AST {ast_calls.get(name, 0)} 个 Call 节点")
    for label, pattern, kind in CROSS_CHECKS:
        n_rx = len(pattern.findall(code))
        if n_rx != kinds.get(kind, 0):
            problems.append(f"{unit.path}: {label} 源码 {n_rx} 处 ⇔ AST {kinds.get(kind, 0)} 个 "
                            f"`{kind}` 节点")
    return problems, set(rx_calls) | set(ast_calls)


# ── 拒绝集 / 接受集 ─────────────────────────────────────────────────────────

def load_cases(root: Path) -> tuple[list[dict], list[dict]]:
    """读拒绝集/接受集（TOML 数据文件；`idl_parse_cases.toml`）。

    用数据文件而非 Python 模块：`idl/` 由 `check-manifests-guard` 做双向目录集合断言，
    import 会落 `__pycache__` ⇒ 门控自己把树弄脏。TOML 多行字面量能**逐字**承载样例源码。
    """
    try:
        import tomllib
    except ModuleNotFoundError as exc:      # Python < 3.11
        raise IdlError("需要 Python ≥ 3.11（`tomllib` 是标准库）") from exc
    path = root / CASES_REL
    if not path.is_file():
        raise IdlError(f"{CASES_REL}: 不存在")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    reject, accept = data.get("reject", []), data.get("accept", [])
    # 下限 = 任务书验收门槛（拒绝集 ≥3 类语法错误；接受集 ≥2 例防过度拒绝）；
    # 具体条数现场统计，不写死。
    if len(reject) < 3:
        raise IdlError(f"{CASES_REL}: 拒绝集只有 {len(reject)} 条（任务要求 ≥3 类语法错误）")
    if len(accept) < 2:
        raise IdlError(f"{CASES_REL}: 接受集只有 {len(accept)} 条（≥2 例，防过度拒绝）")
    return reject, accept


def run_cases(root: Path, verbose: bool = True) -> tuple[int, int, list[str]]:
    """跑拒绝集（必须报错且错误类别相符）与接受集（必须通过且含预期节点）。

    返回（通过数, 总数, 失败明细）。
    """
    reject_cases, accept_cases = load_cases(root)
    problems: list[str] = []
    total = passed = 0
    for case in reject_cases:
        total += 1
        name = case["name"]
        try:
            parse_text(case["code"], f"<reject:{name}>")
        except IdlError as exc:             # UnsupportedConstruct 是其子类
            msg = str(exc)
        else:
            problems.append(f"拒绝集 `{name}`: 解析器没报错（静默放过）")
            continue
        expect = re.compile(case["expect"])
        if not expect.search(msg):
            problems.append(f"拒绝集 `{name}`: 报错类别不符（/{case['expect']}/ 未命中）: {msg}")
            continue
        passed += 1
        if verbose:
            print(f"  [reject] {name}: 按预期报错 —— {case['why']}")
    for case in accept_cases:
        total += 1
        name = case["name"]
        try:
            unit = parse_text(case["code"], f"<accept:{name}>")
        except IdlError as exc:
            problems.append(f"接受集 `{name}`: 合法样例被拒: {exc}")
            continue
        kinds = {node.kind for node in walk([unit.decls, [op.body for op in unit.operations]])}
        missing = sorted(set(case["must_kinds"]) - kinds)
        if missing:
            problems.append(f"接受集 `{name}`: 缺预期节点 {missing}（实得 {sorted(kinds)}）")
            continue
        passed += 1
        if verbose:
            print(f"  [accept] {name}: 解析通过，节点 {sorted(case['must_kinds'])} 齐全")
    return passed, total, problems


# ── 门控入口 ────────────────────────────────────────────────────────────────

def check(root: Path, quiet: bool = False) -> int:
    """全量解析 + fixture 比对 + opcodes 对账 + 拒绝/接受集。rc=0 才算过。"""
    say = (lambda *a: None) if quiet else print
    try:
        units = load_units(root)
    except IdlError as exc:
        print(f"idl-parse: FAIL —— 解析失败: {exc}", file=sys.stderr)
        return 1

    n_books = len([u for u in units if not u.path.startswith(LIB_REL + "/")])
    n_lib = len(units) - n_books
    ops = sum(len(u.operations) for u in units)
    funcs = sum(1 for u in units for d in u.decls if d.kind == "FunctionDecl")
    enums = sum(1 for u in units for d in u.decls if d.kind == "EnumDecl")
    globs = sum(1 for u in units for d in u.decls if d.kind == "VarDecl")
    say(f"[idl-parse] 源 {len(units)} 个（册 {n_books} + 库 {n_lib}）："
        f"operation {ops} / function {funcs} / enum {enums} / 全局常量 {globs}")

    problems: list[str] = []

    # 1) opcodes.yaml 独立对账（条数 + id 成员；不从 IDL 自证）
    try:
        known = opcode_ids(root)
    except (IdlError, OSError) as exc:
        print(f"idl-parse: FAIL —— {exc}", file=sys.stderr)
        return 1
    unknown = sorted({op.id for u in units for op in u.operations} - set(known))
    if len(known) != ops:
        problems.append(f"operation 数不自洽: 解析 {ops} 条 ⇔ {OPCODES_REL} `- id:` {len(known)} 条")
    elif unknown:
        problems.append(f"operation id 不在 {OPCODES_REL}: {', '.join(unknown[:8])}")
    else:
        say(f"[idl-parse] {OPCODES_REL}: {len(known)} 条 ⇔ 解析出的 operation {ops} 条一致、id 全在表内")

    # 2) 构造签名 fixture（漂移防护）
    fixture_path = root / FIXTURE_REL
    if not fixture_path.is_file():
        problems.append(f"{FIXTURE_REL}: 不存在（先跑 `python3 idl/idl_parser.py --update`）")
    else:
        try:
            want = json.loads(fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{FIXTURE_REL}: 不是合法 JSON: {exc}")
            want = None
        if want is not None:
            have = build_fixture(units)
            drift = compare_fixture(want, have)
            if drift:
                problems.extend(drift[:20])
                problems.append(f"构造签名与 fixture 不一致（共 {len(drift)} 处）"
                                f"⇒ 若为有意的语法/AST 变更，跑 `--update` 并评审 diff")
            else:
                say(f"[idl-parse] fixture: {FIXTURE_REL} 与现场 AST 逐条一致"
                    f"（operation {ops} + function {funcs} + enum {enums} + 常量 {globs}）")

    # 3) 独立 oracle：源码正则统计 ⇔ AST 节点计数（fixture 只证「没变」，这步证「没收错」）
    all_names: set[str] = set()
    cross_problems: list[str] = []
    for unit in units:
        raw = (root / unit.path).read_text(encoding="utf-8")
        found, names = cross_check(unit, raw)
        cross_problems.extend(found)
        all_names |= names
    if cross_problems:
        problems.extend(cross_problems[:20])
    else:
        say(f"[idl-parse] 独立 oracle：源码正则统计 ⇔ AST 节点计数逐项一致"
            f"（call 名字 {len(all_names)} 个 + 结构类 {len(CROSS_CHECKS)} 项 × {len(units)} 个源）")

    # 4) 拒绝集 / 接受集（静默跳过 = FAIL）
    try:
        passed, total, case_problems = run_cases(root, verbose=not quiet)
    except IdlError as exc:
        problems.append(f"拒绝/接受集: {exc}")
    else:
        problems.extend(case_problems)
        if not case_problems:
            say(f"[idl-parse] 拒绝集+接受集: {passed}/{total} 全部符合预期")

    if problems:
        print("idl-parse: FAIL", file=sys.stderr)
        for item in problems:
            print(f"  - {item}", file=sys.stderr)
        return 1
    say("idl-parse: PASS")
    return 0


def update(root: Path) -> int:
    try:
        units = load_units(root)
    except IdlError as exc:
        print(f"idl-parse: FAIL —— 解析失败: {exc}", file=sys.stderr)
        return 1
    payload = build_fixture(units)
    path = root / FIXTURE_REL
    path.write_text(dump_fixture(payload), encoding="utf-8")
    ops = sum(len(u.operations) for u in units)
    print(f"idl-parse: WROTE {FIXTURE_REL}（源 {len(units)} 个 / operation {ops} 条）")
    return 0


def stats(root: Path) -> int:
    try:
        units = load_units(root)
    except IdlError as exc:
        print(f"idl-parse: FAIL —— {exc}", file=sys.stderr)
        return 1
    for unit in units:
        kinds: dict[str, int] = {}
        for op in unit.operations:
            for node in walk(op.body):
                kinds[node.kind] = kinds.get(node.kind, 0) + 1
        funcs = [d for d in unit.decls if d.kind == "FunctionDecl"]
        enums = [d for d in unit.decls if d.kind == "EnumDecl"]
        globs = [d for d in unit.decls if d.kind == "VarDecl"]
        print(f"{unit.path}: operation {len(unit.operations)} / function {len(funcs)} / "
              f"enum {len(enums)} / 全局常量 {len(globs)}"
              + (f" / version {unit.version}" if unit.version else ""))
        if kinds:
            print("    节点: " + ", ".join(f"{k}×{v}" for k, v in sorted(kinds.items())))
    ops = sum(len(u.operations) for u in units)
    print(f"-- 合计: 源 {len(units)} 个 / operation {ops} 条")
    return 0


def dump_ast(root: Path, op_id: str) -> int:
    try:
        units = load_units(root)
    except IdlError as exc:
        print(f"idl-parse: FAIL —— {exc}", file=sys.stderr)
        return 1
    for unit in units:
        for op in unit.operations:
            if op.id == op_id:
                print(sexpr(op.body))
                return 0
    print(f"idl-parse: FAIL —— 找不到 operation `{op_id}`", file=sys.stderr)
    return 1


# ── 注入自检（临时树；不改真实树）──────────────────────────────────────────

def _first_error(root: Path) -> tuple[str, str] | None:
    """返回（首个解析失败的文件, 错误消息）；全部通过则 None。"""
    for path in idl_files(root):
        try:
            parse_text(path.read_text(encoding="utf-8"), path.relative_to(root).as_posix())
        except IdlError as exc:
            return path.relative_to(root).as_posix(), str(exc)
    return None


def self_test() -> int:
    """临时树内注入自检：基线 PASS、各类注入 FAIL（且错误类别相符）、还原后 PASS。"""
    tmp_parent = Path(tempfile.gettempdir()) / "opencode"
    tmp_parent.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="idl-parse-", dir=tmp_parent))
    ok = True

    def copy_tree(dst: Path) -> None:
        shutil.copytree(REPO / IDL_REL, dst / IDL_REL)
        (dst / "contracts").mkdir()
        shutil.copy2(REPO / OPCODES_REL, dst / OPCODES_REL)

    def first_book(root: Path) -> Path:
        return sorted((root / IDL_REL).glob("SimRISC-*.idl"))[0]

    def rewrite(path: Path, mutate) -> None:
        before = path.read_text(encoding="utf-8")
        after = mutate(before)
        if after == before:
            raise IdlError(f"空注入（{path.name} 内容未变）")
        path.write_text(after, encoding="utf-8")

    cases = ["baseline", "drop-paren", "ast-drift", "unsupported-while", "restored"]
    try:
        for idx, name in enumerate(cases, 1):
            root = tmpdir / f"{idx}-{name}"
            root.mkdir()
            copy_tree(root)
            expect_error: str | None = None
            if name == "drop-paren":
                rewrite(first_book(root), lambda t: t.replace(
                    "if (rdHA == 6'd0) {", "if (rdHA == 6'd0 {", 1))
                expect_error = "期望 `)`"
            elif name == "ast-drift":
                # 合法语法，但改变了 AST ⇒ 解析通过、构造签名 fixture 必须红
                def add_stmt(t: str) -> str:
                    lines = t.split("\n")
                    starts = [i for i, line in enumerate(lines) if ID_LINE_RE.match(line)]
                    if len(starts) < 2:
                        raise IdlError("注入准备失败：找不到第二条 `# id:`")
                    lines.insert(starts[1], "  rd[rdHA] = 1'b0;")
                    return "\n".join(lines)
                rewrite(first_book(root), add_stmt)
            elif name == "unsupported-while":
                def add_while(t: str) -> str:
                    lines = t.split("\n")
                    starts = [i for i, line in enumerate(lines) if ID_LINE_RE.match(line)]
                    if len(starts) < 2:
                        raise IdlError("注入准备失败：找不到第二条 `# id:`")
                    lines.insert(starts[1], "  while (1'b1) { }")
                    return "\n".join(lines)
                rewrite(first_book(root), add_while)
                expect_error = "不在子集内"
            elif name == "restored":
                shutil.rmtree(root)
                root.mkdir()
                copy_tree(root)

            err = _first_error(root)
            rc = check(root, quiet=True)
            expect_zero = name in ("baseline", "restored")
            good = (rc == 0) == expect_zero
            if expect_error is not None:
                good = good and err is not None and expect_error in err[1]
            if not expect_zero and expect_error is None:
                good = good and err is None          # 语法合法（漂移由 fixture 抓）
            print(f"[self-test {idx}/{len(cases)}] {name}: rc={rc} "
                  f"期望 {'0' if expect_zero else '!=0'} ⇒ {'PASS' if good else 'FAIL'}")
            if err:
                print(f"    首个解析错误: {err[1][:160]}")
            ok = ok and good
    except (IdlError, OSError) as exc:
        print(f"[self-test] 注入准备失败: {exc}", file=sys.stderr)
        ok = False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("idl-parse self-test: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ── 入口 ────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SimRISC IDL 子集解析器（.idl → AST + 构造签名门控）")
    ap.add_argument("--check", action="store_true", help="全量解析 + fixture + 拒绝/接受集（默认）")
    ap.add_argument("--update", action="store_true", help="重新生成构造签名 fixture")
    ap.add_argument("--stats", action="store_true", help="打印现场统计")
    ap.add_argument("--ast", metavar="ID", help="打印某条 operation 的 AST")
    ap.add_argument("--self-test", action="store_true", help="临时树注入自检")
    ap.add_argument("--root", type=Path, default=REPO, help="另一棵同布局的树（默认仓库根）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.update:
        return update(args.root)
    if args.stats:
        return stats(args.root)
    if args.ast:
        return dump_ast(args.root, args.ast)
    return check(args.root)


if __name__ == "__main__":
    sys.exit(main())
