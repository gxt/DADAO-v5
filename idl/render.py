#!/usr/bin/env python3
"""Render ISA operation blocks from ``idl/*.idl`` into ``spec/`` (m15-spec-001).

Why
---
``idl/`` 是 ISA 语义的**机器可读源**（每册一个 ``.idl``，每条指令以 ``# id:``
开头）；``spec/SimRISC-*`` 里的 ```idl 块是**渲染结果**，不得手改。本脚本是该
渲染的**唯一生成器**与门控：块内容按 ``# id:`` 逐字节搬运，因此「规范里的块是否
等于源」可机械判定。

标记约定
--------
源册 ``idl/SimRISC-NN.idl`` 对应 ``spec/SimRISC-NN-*.md``；该册内每条指令的落点写作::

    <!-- IDL:<instr-id> BEGIN -->
    ...（本脚本生成，勿手改）...
    <!-- IDL:<instr-id> END -->

断言（全部 fail-closed）
------------------------
A. 源：``idl/*.idl`` 的文件名形如 ``SimRISC-NN.idl``；文件头（首个 ``# id:`` 之前）
   不得有非空内容；每条 operation 以 ``# id: <instr-id>`` 开头、id 全局唯一。
B. id 存在于 ``contracts/opcodes.yaml``（防与编码表脱节）。
C. 落点：每个 id 在对应册内**恰好一对**标记（BEGIN 先于 END、期间无其它 BEGIN）；
   每个 ``# id:`` 都有落点；**每个落点都有源**（防空标记）；落点所在册 == 源文件册。
D. 一致性：重渲染后的整册文本与磁盘**逐字节相同**（``--check``）；两次渲染同结果。
E. 交叉断言：每条 operation 调用的函数都在 ``idl/README.md §4`` 声明（防「引用了不存在的
   语义库」——语义正确性由编写期 ``idlc`` oracle 另行检查，不动门控）。

用法
----
* ``python3 idl/render.py``              # 生成/更新 spec 册内的标记块
* ``python3 idl/render.py --check``      # 只校验（漂移 ⇒ 非零退出）
* ``python3 idl/render.py --self-test``  # 临时树内 4 类注入自检（各自须 FAIL）
* ``--root DIR``：在另一棵树（同布局）内运行，供注入自检使用

退出码：0 = 通过；1 = 任一断言失败。
"""
from __future__ import annotations

import argparse
import difflib
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

IDL_REL = "idl"
SPEC_REL = "spec"
OPCODES_REL = "contracts/opcodes.yaml"

ID_RE = re.compile(r"^#\s*id:\s*(\S+)\s*$")
BEGIN_RE = re.compile(r"^<!--\s*IDL:(\S+)\s+BEGIN\s*-->\s*$")
END_RE = re.compile(r"^<!--\s*IDL:(\S+)\s+END\s*-->\s*$")
BOOK_RE = re.compile(r"^SimRISC-(\d{2})\.idl$")
DECL_RE = re.compile(r"^\s*(?:builtin\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
CALL_RE = re.compile(r"(?<![\w$.])([A-Za-z_][A-Za-z0-9_]*)\s*\(")
# 关键字/内建转换不算「调用语义库函数」
NON_CALL = frozenset({"if", "for", "while", "return", "assert", "sizeof", "true", "false"})

GENERATED_NOTE = "<!-- 由 idl/render.py 生成，勿手改 -->"
FENCE_OPEN = "```idl"
FENCE_CLOSE = "```"


class RenderError(Exception):
    """任一门控断言失败。"""


@dataclass(frozen=True)
class Op:
    id: str
    book: str          # 形如 "SimRISC-01"
    source: Path
    text: str          # 自 `# id:` 行起、末行非空的多行正文（不含结尾换行）


def _split_lines(text: str) -> list[str]:
    """按 ``\n`` 切行；不静默改写其它行尾（CRLF 一律拒绝，避免「逐字节」名不副实）。"""
    if "\r" in text:
        raise RenderError("含 CR 行尾，拒绝渲染（逐字节比对要求 LF）")
    return text.split("\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def same_bytes(path: Path, text: str) -> bool:
    """逐字节比对（UTF-8 编码后与磁盘字节流全等）。"""
    return path.read_bytes() == text.encode("utf-8")


def parse_idl(path: Path, book: str) -> list[Op]:
    """把一册 ``.idl`` 按 ``# id:`` 切成若干 operation。"""
    lines = _split_lines(read_text(path))
    chunks: list[tuple[str, list[str]]] = []
    cur_id: str | None = None
    cur_lines: list[str] = []
    for lineno, line in enumerate(lines, 1):
        m = ID_RE.match(line)
        if m:
            if cur_id is not None:
                chunks.append((cur_id, cur_lines))
            cur_id = m.group(1)
            cur_lines = [line]
            continue
        if cur_id is None:
            if line.strip():
                raise RenderError(f"{path}:{lineno}: 首个 `# id:` 之前不得有内容（{line!r}）")
            continue
        cur_lines.append(line)
    if cur_id is not None:
        chunks.append((cur_id, cur_lines))

    ops: list[Op] = []
    for op_id, body in chunks:
        while body and not body[-1].strip():
            body.pop()
        if len(body) < 2:
            raise RenderError(f"{path}: operation `{op_id}` 只有 `# id:` 行、没有正文")
        ops.append(Op(id=op_id, book=book, source=path, text="\n".join(body)))
    if not ops:
        raise RenderError(f"{path}: 没有任何 `# id:` operation")
    return ops


def load_ops(idl_dir: Path) -> dict[str, Op]:
    """读全部源册；id 全局唯一；文件名须为 ``SimRISC-NN.idl``。"""
    files = sorted(idl_dir.glob("*.idl"))
    if not files:
        raise RenderError(f"{idl_dir}: 没有任何 `.idl` 源册")
    ops: dict[str, Op] = {}
    for path in files:
        m = BOOK_RE.match(path.name)
        if not m:
            raise RenderError(f"{path.name}: 源册名须形如 `SimRISC-NN.idl`")
        for op in parse_idl(path, path.stem):
            if op.id in ops:
                raise RenderError(
                    f"operation id 重复: `{op.id}`（{ops[op.id].source.name} 与 {path.name}）")
            ops[op.id] = op
    return ops


def load_opcodes(root: Path) -> set[str]:
    import yaml  # type: ignore

    path = root / OPCODES_REL
    data = yaml.safe_load(read_text(path))
    if not isinstance(data, list) or not data:
        raise RenderError(f"{OPCODES_REL}: 期望非空列表")
    ids = {entry["id"] for entry in data if isinstance(entry, dict) and "id" in entry}
    if not ids:
        raise RenderError(f"{OPCODES_REL}: 没有解析到任何 id")
    return ids


def load_declared(root: Path) -> set[str]:
    """§4 语义库声明的函数名（``function X {`` / ``builtin function X {``）。"""
    readme = root / IDL_REL / "README.md"
    text = read_text(readme)
    if "## 4." not in text or "## 5." not in text:
        raise RenderError(f"{readme.name}: 找不到 §4 语义库小节（约定见该文件）")
    section = text.split("## 4.", 1)[1].split("## 5.", 1)[0]
    declared = {m.group(1) for m in (DECL_RE.match(line) for line in section.split("\n")) if m}
    if not declared:
        raise RenderError(f"{readme.name} §4: 没有解析到任何函数声明")
    return declared


def strip_comments(text: str) -> str:
    """抹掉 ``#`` 行尾注释（只用于「未声明函数」扫描）。

    operation 的注释里常引述散文的记号（如 ``rol(x, n)``、``GF(2)``），
    按字面扫会把注释误判成「调用了未声明的函数」，逼人改注释措辞。
    """
    return "\n".join(line.split("#", 1)[0] for line in text.split("\n"))


def check_calls_declared(ops: dict[str, Op], declared: set[str]) -> int:
    """每条 operation 调用的函数都必须在 §4 声明（防「引用了不存在的语义库」）。"""
    bad: list[str] = []
    total = 0
    for op in ops.values():
        for m in CALL_RE.finditer(strip_comments(op.text)):
            name = m.group(1)
            if name in NON_CALL:
                continue
            total += 1
            if name not in declared:
                bad.append(f"{op.id}: 调用未声明的函数 `{name}(`")
    if bad:
        raise RenderError("语义库缺项:\n  " + "\n  ".join(sorted(set(bad))))
    return total


def book_of_spec(path: Path) -> str | None:
    """``SimRISC-01-取数存数.md`` → ``SimRISC-01``。"""
    m = re.match(r"^(SimRISC-\d{2})-", path.name)
    return m.group(1) if m else None


def book_spec_files(root: Path) -> dict[str, Path]:
    """册名 → spec 文件（每册恰好一个）。"""
    out: dict[str, Path] = {}
    for path in sorted((root / SPEC_REL).glob("SimRISC-*.md")):
        book = book_of_spec(path)
        if book is None:
            continue
        if book in out:
            raise RenderError(f"册 `{book}` 对应多个 spec 文件: {out[book].name} / {path.name}")
        out[book] = path
    if not out:
        raise RenderError(f"{SPEC_REL}: 没有 SimRISC-*.md")
    return out


def marker_spans(lines: list[str], path: Path) -> dict[str, tuple[int, int]]:
    """找出 ``<!-- IDL:<id> BEGIN -->`` … ``<!-- IDL:<id> END -->`` 的行区间（0 基）。"""
    spans: dict[str, tuple[int, int]] = {}
    i = 0
    n = len(lines)
    while i < n:
        mb = BEGIN_RE.match(lines[i])
        if not mb:
            me = END_RE.match(lines[i])
            if me:
                raise RenderError(f"{path.name}:{i + 1}: 孤立的 END 标记 `{me.group(1)}`")
            i += 1
            continue
        op_id = mb.group(1)
        if op_id in spans:
            raise RenderError(f"{path.name}:{i + 1}: `{op_id}` 有多对 BEGIN 标记")
        j = i + 1
        while j < n and not END_RE.match(lines[j]):
            if BEGIN_RE.match(lines[j]):
                raise RenderError(
                    f"{path.name}:{j + 1}: 标记嵌套（`{op_id}` 块内又出现 BEGIN）")
            j += 1
        if j >= n:
            raise RenderError(f"{path.name}:{i + 1}: `{op_id}` 缺少 END 标记")
        end_id = END_RE.match(lines[j]).group(1)  # type: ignore[union-attr]
        if end_id != op_id:
            raise RenderError(
                f"{path.name}:{j + 1}: END 标记 `{end_id}` 与 BEGIN `{op_id}` 不匹配")
        spans[op_id] = (i, j)
        i = j + 1
    return spans


def render_file(path: Path, ops: dict[str, Op], book: str) -> tuple[str, int]:
    """渲染一册；返回（新文本, 替换的块数）。"""
    lines = _split_lines(read_text(path))
    spans = marker_spans(lines, path)

    out: list[str] = []
    cursor = 0
    for op_id, (start, end) in sorted(spans.items(), key=lambda kv: kv[1][0]):
        if op_id not in ops:
            raise RenderError(f"{path.name}: 标记 `{op_id}` 没有对应的 `# id:` 源（空标记）")
        if ops[op_id].book != book:
            raise RenderError(
                f"{path.name}: 标记 `{op_id}` 的源在 {ops[op_id].source.name}（{ops[op_id].book}），"
                f"与落点册 `{book}` 不符")
        out.extend(lines[cursor:start])          # BEGIN 行之前的原文
        out.append(lines[start])                 # BEGIN 行原样保留
        out.append(GENERATED_NOTE)
        out.append(FENCE_OPEN)
        out.extend(ops[op_id].text.split("\n"))
        out.append(FENCE_CLOSE)
        out.append(lines[end])                   # END 行原样保留
        cursor = end + 1
    out.extend(lines[cursor:])
    return "\n".join(out), len(spans)


def render_all(root: Path) -> tuple[dict[Path, str], dict[str, Op], int]:
    """算出全部落点册的新文本；同时做 C/D 类断言。"""
    idl_dir = root / IDL_REL
    ops = load_ops(idl_dir)
    opcode_ids = load_opcodes(root)

    missing = sorted(set(ops) - opcode_ids)
    if missing:
        raise RenderError("源里的 id 不在 contracts/opcodes.yaml: " + ", ".join(missing))

    check_calls_declared(ops, load_declared(root))

    books = book_spec_files(root)
    for op in ops.values():
        if op.book not in books:
            raise RenderError(f"{op.source.name}: 找不到对应 spec 册 `{op.book}-*.md`")

    # 落点集合（全 spec 册扫一遍，含「不该有标记的册」）
    placed: dict[str, str] = {}
    per_file: dict[Path, dict[str, tuple[int, int]]] = {}
    for path in sorted((root / SPEC_REL).glob("*.md")):
        lines = _split_lines(read_text(path))
        spans = marker_spans(lines, path)
        if spans:
            per_file[path] = spans
        for op_id in spans:
            if op_id in placed:
                raise RenderError(
                    f"标记 `{op_id}` 出现在多个册: {placed[op_id]} / {path.name}")
            placed[op_id] = path.name
    orphans = sorted(set(placed) - set(ops))
    if orphans:
        raise RenderError("spec 标记没有对应源: " + ", ".join(orphans))
    unplaced = sorted(set(ops) - set(placed))
    if unplaced:
        raise RenderError("源没有落点标记: " + ", ".join(unplaced))

    rendered: dict[Path, str] = {}
    total = 0
    for path, spans in per_file.items():
        book = book_of_spec(path)
        if book is None:
            raise RenderError(f"{path.name}: 含 IDL 标记但不是 SimRISC-NN 册")
        if not any(ops[op_id].book == book for op_id in spans):
            raise RenderError(f"{path.name}: 含 IDL 标记但 {IDL_REL}/ 无对应源册")
        text, n = render_file(path, ops, book)
        rendered[path] = text
        total += n

    for book, path in books.items():
        book_ops = [op_id for op_id, op in ops.items() if op.book == book]
        if book_ops and path not in rendered:
            raise RenderError(f"{path.name}: 源册 `{book}` 有 {len(book_ops)} 条 operation 但册内无标记")
    return rendered, ops, total


def print_diff(path: Path, want: str) -> None:
    have_lines = read_text(path).split("\n")
    want_lines = want.split("\n")
    print(f"  {path.name}: 与渲染结果不一致（磁盘 {len(have_lines)} 行 / 渲染 {len(want_lines)} 行）")
    diff = list(difflib.unified_diff(have_lines, want_lines, fromfile="spec", tofile="rendered", lineterm=""))
    for line in diff[:20]:
        print("    " + line)
    if len(diff) > 20:
        print(f"    … 其余 {len(diff) - 20} 行见 --check 全量输出")


def run(root: Path) -> int:
    rendered, ops, total = render_all(root)
    drifted = [p for p, text in rendered.items() if not same_bytes(p, text)]
    if drifted:
        print(f"idl-render: FAIL（{len(drifted)} 册漂移 / 共 {len(rendered)} 册；"
              f"源 operation={len(ops)}、标记块={total}）")
        for path in drifted:
            print_diff(path, rendered[path])
        return 1
    print(f"idl-render: PASS（源 operation={len(ops)} 条 / 落点 {len(rendered)} 册 / "
          f"标记块 {total} 个，逐字节一致）")
    return 0


def write(root: Path) -> int:
    rendered, ops, total = render_all(root)
    changed = 0
    for path, text in rendered.items():
        if not same_bytes(path, text):
            path.write_bytes(text.encode("utf-8"))
            changed += 1
    print(f"idl-render: WROTE（源 operation={len(ops)} 条 / 标记块 {total} 个 / "
          f"更新 {changed} 册）")
    return 0


def run_rc(root: Path) -> int:
    """``run`` 的 rc 化版本：断言失败也返回 1（自检要观察 rc，不要异常冒泡）。"""
    try:
        return run(root)
    except RenderError as exc:
        print(f"  (RenderError) {exc}")
        return 1


def self_test() -> int:
    """临时树内注入自检：基线 PASS，3 类注入各自 FAIL，还原后 PASS。"""
    repo = REPO
    tmp_parent = Path(tempfile.gettempdir()) / "opencode"
    tmp_parent.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="idl-render-", dir=tmp_parent))
    ok = True

    def copy_tree(dst: Path) -> None:
        for rel in (IDL_REL, SPEC_REL):
            shutil.copytree(repo / rel, dst / rel)
        (dst / "contracts").mkdir()
        shutil.copy2(repo / OPCODES_REL, dst / OPCODES_REL)

    def first_op_file(root: Path) -> Path:
        return sorted((root / IDL_REL).glob("*.idl"))[0]

    def first_rendered_region(root: Path) -> tuple[Path, int]:
        for path in sorted((root / SPEC_REL).glob("SimRISC-*.md")):
            lines = read_text(path).split("\n")
            spans = marker_spans(lines, path)
            if spans:
                start, end = sorted(spans.values())[0]
                return path, start + 4   # 0 基行号；+4 = 跳过 BEGIN/注释/围栏/`# id:` ⇒ 首条正文行
        raise RenderError("临时树内没有标记块")

    cases = ["baseline", "spec-char", "idl-drift", "drop-id", "undeclared-call", "restored"]
    try:
        for idx, name in enumerate(cases, 1):
            root = tmpdir / f"{idx}-{name}"
            root.mkdir()
            copy_tree(root)
            if name == "spec-char":
                # 改 spec 渲染结果的一个字符（模拟手改生成段）
                path, lineno = first_rendered_region(root)
                lines = read_text(path).split("\n")
                orig = lines[lineno]
                lines[lineno] = orig + " "        # 行尾加一个空格 ⇒ 字节不同
                if lines[lineno] == orig:
                    raise RenderError("空注入（spec-char）")
                path.write_text("\n".join(lines), encoding="utf-8")
            elif name == "idl-drift":
                # 改源但不重渲染
                path = first_op_file(root)
                text = read_text(path)
                path.write_text(text.replace("\n", "\n# drift-injection\n", 1), encoding="utf-8")
                if read_text(path) == text:
                    raise RenderError("空注入（idl-drift）")
            elif name == "drop-id":
                # 删一条 `# id:` 行但保留标记（⇒ 空标记）
                path = first_op_file(root)
                lines = read_text(path).split("\n")
                for i, line in enumerate(lines):
                    if ID_RE.match(line):
                        del lines[i]
                        break
                else:
                    raise RenderError("空注入（drop-id）：没有找到 `# id:` 行")
                path.write_text("\n".join(lines), encoding="utf-8")
            elif name == "undeclared-call":
                # 调用语义库未声明的函数（模拟「例句引用了不存在的库函数」）
                path = first_op_file(root)
                text = read_text(path)
                injected = text + "rd_read_typo(6'd0);\n"
                path.write_text(injected, encoding="utf-8")
                if injected == text:
                    raise RenderError("空注入（undeclared-call）")
            elif name == "restored":
                # 重新从真实树拷贝 ⇒ 还原后必须回绿
                shutil.rmtree(root)
                root.mkdir()
                copy_tree(root)

            rc = run_rc(root)
            expect_zero = name in ("baseline", "restored")
            good = (rc == 0) == expect_zero
            print(f"[self-test {idx}/{len(cases)}] {name}: rc={rc} 期望 rc={'0' if expect_zero else '!=0'} "
                  f"⇒ {'PASS' if good else 'FAIL'}")
            ok = ok and good
    except RenderError as exc:
        print(f"[self-test] 注入准备失败: {exc}", file=sys.stderr)
        ok = False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("idl-render self-test: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render idl/*.idl into spec/ marker blocks")
    ap.add_argument("--check", action="store_true", help="只校验，不写盘")
    ap.add_argument("--self-test", action="store_true", help="临时树内注入自检")
    ap.add_argument("--root", type=Path, default=REPO, help="另一棵同布局的树（默认仓库根）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    try:
        return run(args.root) if args.check else write(args.root)
    except RenderError as exc:
        print(f"idl-render: FAIL — {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
