#!/usr/bin/env python3
"""执行器「依据锁」门控（`m17-idl-017`）。

为什么
------
M17 的 golden = IDL，但 `idl/tools/idl_exec.py` 是按 `.idl` 正文**手写**的（FP 走
`idl_fp` 薄封装）。语法/渲染门控（`check-idl-parse` / `check-idl-sync`）只证明 `.idl`
自身一致，**不保证正文改了实现也被复核**：三平台都没改时四方差分仍绿，漂移隐形。

本脚本锁的是**实现所依据的正文**（不是语义等价）：

  * `[[op]]`：每条 operation 自 `# id:` 行起、到下一个 `# id:` 之前的正文 sha256
    （切分**复用** `idl_render.py`，不另写一套），外加 `book`（如 `SimRISC-04.idl`）
    与 `impl`（`@sem` 注册里的实现函数名，便于回溯）；
  * `[[lib]]`：`idl/lib/*.idl` 逐文件 sha256（FP 语义在库里，只锁 operation 正文会漏掉
    `ft_scale` 这类改动）。

表由 `--update` 生成，**禁手改**。改 `.idl`（含 `lib/*.idl`）⇒ 必须 `--update`，并在评审
diff 里说明对应实现是否跟改；不跟改也要显式更新，让「正文变了、实现没动」可见。

`impl` 现场派生
---------------
* `@sem(...)` 装饰的函数 ⇒ `impl` = 该函数名；
* 族参数化注册 `_sem_params((id, ...), fn, ...)` ⇒ `impl` = `fn`（实现函数名）。
两路之外的出现 ⇒ `--update` 直接失败（不猜）；注册缺失（`.idl` 有、注册没有）或重名
（同一 id 注册两次）同样失败。注册表以**实际导入** `idl_exec.py` 后的 `SEMANTICS` 为准，
源码 AST 只用于把 id 映射到实现函数名，两者集合必须相等。

用法
----
* ``python3 idl/tools/idl_check_anchor.py --check``      # 校验（sha 差异 rc=1；集合/结构错 rc=2）
* ``python3 idl/tools/idl_check_anchor.py --update``     # 重写表（评审 diff）
* ``python3 idl/tools/idl_check_anchor.py --self-test``  # 临时树内注入自检
* ``--root DIR``：在另一棵同布局的树内运行（自检用）

退出码：0 = 一致；1 = sha 漂移（正文或库文件变了）；2 = 集合/结构错误（表缺条目/重复/
缺字段、注册缺失或重名、`impl`/`book` 与现场不符）。
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True       # idl/ 由 check-manifests-guard 做目录断言

import argparse
import ast
import hashlib
import importlib.util
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import idl_render
from idl_paths import REPO

ANCHOR_REL = "idl/data/exec_anchor.toml"
EXEC_REL = "idl/tools/idl_exec.py"
LIB_REL = "idl/lib"
SCHEMA = 1
SPEC_NAME = "sem"
FAMILY_HELPER = "_sem_params"
OP_KEYS = frozenset({"id", "book", "impl", "sha256"})
LIB_KEYS = frozenset({"file", "sha256"})
TOP_KEYS = frozenset({"schema", "op", "lib"})


class AnchorError(Exception):
    """集合/结构层面的失败（rc=2）。"""


@dataclass(frozen=True)
class OpAnchor:
    id: str
    book: str
    impl: str
    sha256: str


@dataclass(frozen=True)
class LibAnchor:
    file: str
    sha256: str


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── 现场派生：operation 正文（切分复用 idl_render）──────────────────────────

def derive_ops(root: Path) -> dict[str, tuple[str, str]]:
    """`{op_id: (book 文件名, 正文 sha256)}`；切分口径 = `idl_render.load_ops`。"""
    try:
        ops = idl_render.load_ops(root / "idl")
    except idl_render.RenderError as exc:
        raise AnchorError(f"切分 `idl/*.idl` 失败: {exc}") from exc
    return {op_id: (op.book + ".idl", sha_text(op.text)) for op_id, op in ops.items()}


def derive_libs(root: Path) -> dict[str, str]:
    """`{lib/<file>: 文件 sha256}`；库目录为空 ⇒ 拒绝（防门控空转）。"""
    libs: dict[str, str] = {}
    for path in sorted((root / "idl" / "lib").glob("*.idl")):
        libs[f"lib/{path.name}"] = sha_file(path)
    if not libs:
        raise AnchorError(f"{LIB_REL}: 没有任何 `.idl` 库文件 ⇒ 锁为空转，拒绝通过")
    return libs


# ── 现场派生：@sem 注册（id → 实现函数名）─────────────────────────────────

def _ids_of(node: ast.expr, where: str, consts: dict[str, list[str]]) -> list[str]:
    """注册调用的 id 实参（字符串字面量、字面量序列或模块级常量名）。"""
    if isinstance(node, ast.Name):
        if node.id not in consts:
            raise AnchorError(f"{where}: 引用了无法从模块常量解析的 `{node.id}`（无法派生 impl）")
        return list(consts[node.id])
    items = node.elts if isinstance(node, (ast.Tuple, ast.List, ast.Set)) else [node]
    ids: list[str] = []
    for item in items:
        if isinstance(item, ast.Starred):
            ids.extend(_ids_of(item.value, where, consts))
            continue
        if not (isinstance(item, ast.Constant) and isinstance(item.value, str)):
            raise AnchorError(f"{where}: 注册的 id 实参不是字符串字面量（无法派生 impl）")
        ids.append(item.value)
    return ids


def _literal_strs(node: ast.expr) -> list[str]:
    """模块级常量：字符串字面量或由字符串字面量组成的序列。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        out: list[str] = []
        for item in node.elts:
            if not (isinstance(item, ast.Constant) and isinstance(item.value, str)):
                raise AnchorError("不是字符串字面量")
            out.append(item.value)
        return out
    raise AnchorError("不是字符串字面量/序列")


def _module_consts(tree: ast.Module) -> dict[str, list[str]]:
    consts: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.value is not None:
            name, value = node.target.id, node.value
        else:
            continue
        try:
            consts[name] = _literal_strs(value)
        except AnchorError:
            continue
    return consts



def impl_index(exec_path: Path) -> dict[str, str]:
    """源码 AST 派生 `{op_id: 实现函数名}`：`@sem` 装饰 + `_sem_params` 族注册。"""
    try:
        tree = ast.parse(exec_path.read_text(encoding="utf-8"), filename=str(exec_path))
    except OSError as exc:
        raise AnchorError(f"{EXEC_REL}: 读取失败: {exc}") from exc
    except SyntaxError as exc:
        raise AnchorError(f"{EXEC_REL}: 语法错误: {exc}") from exc

    index: dict[str, str] = {}
    consts = _module_consts(tree)

    def add(op_id: str, impl: str) -> None:
        if op_id in index:
            raise AnchorError(
                f"{EXEC_REL}: operation `{op_id}` 重复注册（{index[op_id]} 与 {impl}）")
        index[op_id] = impl

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name)
                        and dec.func.id == SPEC_NAME):
                    continue
                if dec.keywords:
                    raise AnchorError(
                        f"{EXEC_REL}: `@{SPEC_NAME}` 的 id 以关键字实参给出（无法派生 impl）")
                for op_id in _ids_of_args(dec, f"{EXEC_REL}: `@{SPEC_NAME}`", consts):
                    add(op_id, node.name)
            continue
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
            continue
        call = node.value
        if not (isinstance(call.func, ast.Name) and call.func.id == FAMILY_HELPER):
            continue
        if len(call.args) < 2:
            raise AnchorError(f"{EXEC_REL}: `{FAMILY_HELPER}` 调用缺少 (ids, fn) 实参")
        fn = call.args[1]
        if not isinstance(fn, ast.Name):
            raise AnchorError(f"{EXEC_REL}: `{FAMILY_HELPER}` 的实现实参不是函数名（无法派生 impl）")
        for op_id in _ids_of(call.args[0], f"{EXEC_REL}: `{FAMILY_HELPER}`", consts):
            add(op_id, fn.id)
    if not index:
        raise AnchorError(f"{EXEC_REL}: 没有派生到任何 `@{SPEC_NAME}` 注册 ⇒ 拒绝通过")
    return index


def _ids_of_args(call: ast.Call, where: str, consts: dict[str, list[str]]) -> list[str]:
    """`@sem("a", *IDS)` 的 id 实参（逐个位置参数）。"""
    if not call.args:
        raise AnchorError(f"{where}: 没有任何 id 实参")
    ids: list[str] = []
    for arg in call.args:
        ids.extend(_ids_of(arg, where, consts))
    return ids


def load_registry(exec_path: Path) -> dict[str, str]:
    """以**实际导入**后的 `SEMANTICS` 为准，校验与 AST 派生的实现映射集合相等。"""
    index = impl_index(exec_path)
    spec = importlib.util.spec_from_file_location("_idl_exec_anchor_probe", exec_path)
    if spec is None or spec.loader is None:
        raise AnchorError(f"{EXEC_REL}: 无法 import 以读取 `SEMANTICS`")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:                       # noqa: BLE001 — 注册重名在此抛 ExecError
        raise AnchorError(f"导入 `{EXEC_REL}` 失败（@sem 注册重名会在此报错）: "
                          f"{type(exc).__name__}: {exc}") from exc
    live = getattr(module, "SEMANTICS", None)
    if not isinstance(live, dict) or not live:
        raise AnchorError(f"{EXEC_REL}: 导入后没有 `SEMANTICS` 注册表")
    unknown = sorted(set(live) - set(index))
    stale = sorted(set(index) - set(live))
    if unknown:
        raise AnchorError(f"{EXEC_REL}: 现场注册的 id 无法从源码定位实现函数: "
                          f"{', '.join(unknown[:8])}")
    if stale:
        raise AnchorError(f"{EXEC_REL}: 源码有注册但现场注册表没有: {', '.join(stale[:8])}")
    return {op_id: index[op_id] for op_id in live}


# ── 锚点表读写 ──────────────────────────────────────────────────────────────

def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_anchor(ops: list[OpAnchor], libs: list[LibAnchor]) -> str:
    lines = [
        f"schema = {SCHEMA}",
        "# 本文件由 `idl/tools/idl_check_anchor.py --update` 生成，禁手改。",
        "# op.sha256 = operation 正文（`# id:` 行起、至下一条 `# id:` 之前；切分口径同 idl_render.py）。",
        "# lib.sha256 = `idl/lib/*.idl` 文件全文。改 `.idl` 后必须 `--update`，并在评审说明实现是否跟改。",
        "",
    ]
    for op in ops:
        lines += ["[[op]]", f"id = {_quote(op.id)}", f"book = {_quote(op.book)}",
                  f"impl = {_quote(op.impl)}", f"sha256 = {_quote(op.sha256)}", ""]
    for lib in libs:
        lines += ["[[lib]]", f"file = {_quote(lib.file)}",
                  f"sha256 = {_quote(lib.sha256)}", ""]
    return "\n".join(lines)


def read_anchor(path: Path) -> tuple[list[OpAnchor], list[LibAnchor], list[str]]:
    """读表；**任何**结构问题都进 problems（返回后统一判 rc=2），不抛异常。"""
    import tomllib

    problems: list[str] = []
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], [], [f"{ANCHOR_REL}: 不存在（先跑 `python3 idl/tools/idl_check_anchor.py --update`）"]
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [], [], [f"{ANCHOR_REL}: 读取/解析失败: {exc}"]

    top = sorted(set(doc) - TOP_KEYS)
    if top:
        problems.append(f"{ANCHOR_REL}: 未知顶层键 {top}（允许 {sorted(TOP_KEYS)}）")
    if doc.get("schema") != SCHEMA:
        problems.append(f"{ANCHOR_REL}: `schema` 期望 {SCHEMA}，实得 {doc.get('schema')!r}")

    ops: list[OpAnchor] = []
    seen: dict[str, int] = {}
    raw_ops = doc.get("op")
    if not isinstance(raw_ops, list) or not raw_ops:
        problems.append(f"{ANCHOR_REL}: `[[op]]` 缺失或为空")
        raw_ops = []
    for i, entry in enumerate(raw_ops, 1):
        where = f"{ANCHOR_REL}: op[{i}]"
        if not isinstance(entry, dict):
            problems.append(f"{where}: 不是表")
            continue
        extra = sorted(set(entry) - OP_KEYS)
        missing = sorted(OP_KEYS - set(entry))
        if extra:
            problems.append(f"{where}: 未知键 {extra}（允许 {sorted(OP_KEYS)}）")
        if missing:
            problems.append(f"{where}: 缺键 {missing}")
            continue
        values = {key: entry[key] for key in OP_KEYS}
        bad = {k: v for k, v in values.items() if not isinstance(v, str) or not v}
        if bad:
            problems.append(f"{where}: 键值须为非空字符串: {sorted(bad)}")
            continue
        if entry["id"] in seen:
            problems.append(f"{where}: id `{entry['id']}` 重复（第 {seen[entry['id']]} 条）")
            continue
        seen[entry["id"]] = i
        ops.append(OpAnchor(**values))

    libs: list[LibAnchor] = []
    seen_libs: dict[str, int] = {}
    raw_libs = doc.get("lib")
    if not isinstance(raw_libs, list) or not raw_libs:
        problems.append(f"{ANCHOR_REL}: `[[lib]]` 缺失或为空")
        raw_libs = []
    for i, entry in enumerate(raw_libs, 1):
        where = f"{ANCHOR_REL}: lib[{i}]"
        if not isinstance(entry, dict):
            problems.append(f"{where}: 不是表")
            continue
        extra = sorted(set(entry) - LIB_KEYS)
        missing = sorted(LIB_KEYS - set(entry))
        if extra:
            problems.append(f"{where}: 未知键 {extra}（允许 {sorted(LIB_KEYS)}）")
        if missing:
            problems.append(f"{where}: 缺键 {missing}")
            continue
        values = {key: entry[key] for key in LIB_KEYS}
        bad = {k: v for k, v in values.items() if not isinstance(v, str) or not v}
        if bad:
            problems.append(f"{where}: 键值须为非空字符串: {sorted(bad)}")
            continue
        if entry["file"] in seen_libs:
            problems.append(f"{where}: 库 `{entry['file']}` 重复（第 {seen_libs[entry['file']]} 条）")
            continue
        seen_libs[entry["file"]] = i
        libs.append(LibAnchor(**values))
    return ops, libs, problems


# ── 校验 ────────────────────────────────────────────────────────────────────

def check(root: Path, registry: dict[str, str], quiet: bool = False) -> int:
    def say(*args) -> None:
        if not quiet:
            print(*args)

    def fail(*args) -> None:
        if not quiet:
            print(*args, file=sys.stderr)

    try:
        live_ops = derive_ops(root)
        live_libs = derive_libs(root)
    except AnchorError as exc:
        fail(f"idl-anchor: FAIL — {exc}")
        return 2

    anchor_ops, anchor_libs, problems = read_anchor(root / ANCHOR_REL)
    drift: list[str] = []
    a_map = {a.id: a for a in anchor_ops}
    l_map = {a.file: a for a in anchor_libs}

    for op_id in sorted(set(live_ops) - set(a_map)):
        problems.append(f"`{op_id}`: 现场有该 operation、表里没有")
    for op_id in sorted(set(a_map) - set(live_ops)):
        problems.append(f"`{op_id}`: 表里有、现场没有（删/改名？）")
    for op_id in sorted(set(live_ops) & set(a_map)):
        book, sha = live_ops[op_id]
        entry = a_map[op_id]
        if entry.book != book:
            problems.append(f"`{op_id}`: book 期望 {entry.book}、实得 {book}")
            continue
        impl = registry.get(op_id)
        if impl is None:
            problems.append(f"`{op_id}`: `{EXEC_REL}` 的 @sem 注册里没有该 id")
        elif entry.impl != impl:
            problems.append(f"`{op_id}`: impl 期望 {entry.impl}、实得 {impl}")
        if entry.sha256 != sha:
            drift.append(f"id={op_id} book={book} expected={entry.sha256[:16]} actual={sha[:16]}")

    for lib in sorted(set(live_libs) - set(l_map)):
        problems.append(f"`{lib}`: 现场有该库文件、表里没有")
    for lib in sorted(set(l_map) - set(live_libs)):
        problems.append(f"`{lib}`: 表里有、现场没有（删/改名？）")
    for lib in sorted(set(live_libs) & set(l_map)):
        sha = live_libs[lib]
        if l_map[lib].sha256 != sha:
            drift.append(f"lib={lib} expected={l_map[lib].sha256[:16]} actual={sha[:16]}")

    for op_id in sorted(set(live_ops) - set(registry)):
        problems.append(f"`{op_id}`: 现场有该 operation、`{EXEC_REL}` 的 @sem 注册里没有")
    for op_id in sorted(set(registry) - set(live_ops)):
        problems.append(f"`{op_id}`: @sem 注册了、但没有任何 `.idl` operation")

    say(f"[idl-anchor] 现场派生：op {len(live_ops)} 条（表里 {len(anchor_ops)} 条）/ "
        f"lib {len(live_libs)} 个文件（表里 {len(anchor_libs)} 个）")
    if problems:
        for msg in problems[:40]:
            say(f"  [FAIL] {msg}")
        if len(problems) > 40:
            say(f"  … 其余 {len(problems) - 40} 条见 --check 全量输出")
        fail(f"idl-anchor: FAIL（结构/集合错误 {len(problems)} 处；"
             f"表须由 `--update` 生成且禁手改）")
        return 2
    if drift:
        for msg in drift[:40]:
            say(f"  [DRIFT] {msg}")
        if len(drift) > 40:
            say(f"  … 其余 {len(drift) - 40} 条见 --check 全量输出")
        say(f"idl-anchor: FAIL（sha 漂移 {len(drift)} 处；改 `.idl`（含 `{LIB_REL}/*.idl`）"
            f"后必须 `--update` 并在评审说明实现是否跟改）")
        return 1
    say(f"idl-anchor: PASS（op {len(live_ops)}/{len(anchor_ops)} 条、"
        f"lib {len(live_libs)}/{len(anchor_libs)} 个文件：集合相等、无重复、sha 逐条命中、"
        f"impl 均在 @sem 注册）")
    return 0


def update(root: Path, registry: dict[str, str]) -> int:
    try:
        live_ops = derive_ops(root)
        live_libs = derive_libs(root)
    except AnchorError as exc:
        print(f"idl-anchor: FAIL — {exc}", file=sys.stderr)
        return 2
    missing = sorted(set(live_ops) - set(registry))
    extra = sorted(set(registry) - set(live_ops))
    if missing:
        print(f"idl-anchor: FAIL — {EXEC_REL} 的 @sem 注册缺失: {', '.join(missing[:8])}",
              file=sys.stderr)
        return 2
    if extra:
        print(f"idl-anchor: FAIL — @sem 注册了但没有对应 `.idl` operation: "
              f"{', '.join(extra[:8])}", file=sys.stderr)
        return 2

    ops = [OpAnchor(op_id, book, registry[op_id], sha)
           for op_id, (book, sha) in sorted(live_ops.items())]
    libs = [LibAnchor(file, sha) for file, sha in sorted(live_libs.items())]
    text = render_anchor(ops, libs)
    path = root / ANCHOR_REL
    old = path.read_bytes() if path.is_file() else b""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    state = "未变" if old == text.encode("utf-8") else "已更新"
    print(f"idl-anchor: WROTE {ANCHOR_REL}（{state}：op {len(ops)} 条 / lib {len(libs)} 个文件）")
    return 0


# ── 自检（临时树内注入）────────────────────────────────────────────────────

def _rewrite(path: Path, mutate) -> None:
    before = path.read_text(encoding="utf-8")
    after = mutate(before)
    if after == before:
        raise AnchorError(f"空注入（{path.name} 内容未变）")
    path.write_text(after, encoding="utf-8")


def _first_op(path: Path) -> tuple[str, int]:
    """`(op_id, `# id:` 行下标)`；取该册第一条。"""
    lines = path.read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        m = idl_render.ID_RE.match(line)
        if m:
            return m.group(1), i
    raise AnchorError(f"{path.name}: 找不到 `# id:` 行")


def _char_injection(path: Path) -> None:
    """在首个 operation 正文行尾加一个空格（正文 sha 必变、id 不变）。"""
    _op_id, idx = _first_op(path)

    def mutate(text: str) -> str:
        lines = text.split("\n")
        for k in range(idx + 1, len(lines)):
            if lines[k].strip() and idl_render.ID_RE.match(lines[k]) is None:
                lines[k] = lines[k] + " "
                return "\n".join(lines)
        raise AnchorError(f"{path.name}: 首个 operation 没有正文行")

    _rewrite(path, mutate)


def _char_anywhere(path: Path) -> None:
    """在首个非空行行尾加一个空格（用于没有 `# id:` 的库文件：文件 sha 必变）。"""
    def mutate(text: str) -> str:
        lines = text.split("\n")
        for k, line in enumerate(lines):
            if line.strip():
                lines[k] = line + " "
                return "\n".join(lines)
        raise AnchorError(f"{path.name}: 没有非空行")

    _rewrite(path, mutate)


def _drop_id(path: Path) -> str:
    """删**第二条** `# id:` 行（保留首条，避免触发「首个 `# id:` 之前不得有内容」）。"""
    lines = path.read_text(encoding="utf-8").split("\n")
    starts = [(i, idl_render.ID_RE.match(line).group(1))
              for i, line in enumerate(lines) if idl_render.ID_RE.match(line)]
    if len(starts) < 2:
        raise AnchorError(f"{path.name}: 少于两条 `# id:`，无法注入")
    idx, op_id = starts[1]
    del lines[idx]
    path.write_text("\n".join(lines), encoding="utf-8")
    return op_id


def _drop_anchor_op(path: Path) -> str:
    """从表里删掉第一个 `[[op]]` 块；返回被删的 id。"""
    lines = path.read_text(encoding="utf-8").split("\n")
    starts = [i for i, line in enumerate(lines) if line == "[[op]]"]
    if not starts:
        raise AnchorError("表里没有 `[[op]]` 块")
    start = starts[0]
    end = start + 1
    while end < len(lines) and not lines[end].startswith("[["):
        end += 1
    block = lines[start:end]
    id_line = next((line for line in block if line.startswith('id = "')), None)
    if id_line is None:
        raise AnchorError("被删块里找不到 id 行")
    op_id = id_line[len('id = "'):-1]
    del lines[start:end]
    path.write_text("\n".join(lines), encoding="utf-8")
    if op_id in {a.id for a in read_anchor(path)[0]}:
        raise AnchorError("空注入（表里仍能读到该 id）")
    return op_id


def _wrong_impl(path: Path) -> str:
    """把第一个 `[[op]]` 的 impl 改成不存在的函数名；返回该 id。"""
    text = path.read_text(encoding="utf-8")
    m = re.search(r'^id = "([^"]+)"$', text, re.M)
    if m is None:
        raise AnchorError("表里没有 id 行")
    op_id = m.group(1)
    _rewrite(path, lambda t: re.sub(r'^impl = "([^"]+)"$', 'impl = "_no_such_impl"',
                                    t, count=1, flags=re.M))
    return op_id


def self_test() -> int:
    """临时树注入自检：基线 PASS、各类注入按预期 rc 红、还原后回绿。"""
    tmp_parent = Path(tempfile.gettempdir()) / "opencode"
    tmp_parent.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="idl-anchor-", dir=tmp_parent))
    ok = True

    def copy_tree(dst: Path) -> None:
        shutil.copytree(REPO / "idl", dst / "idl")

    def first_book(root: Path) -> Path:
        return sorted((root / "idl").glob("SimRISC-*.idl"))[0]

    cases = ["baseline", "book-char", "drop-id", "anchor-drop", "anchor-impl",
             "lib-char", "restored"]
    total = len(cases) + 2                      # 另加：注册缺失 / 注册重名
    try:
        registry = load_registry(REPO / EXEC_REL)
        for idx, name in enumerate(cases, 1):
            root = tmpdir / f"{idx}-{name}"
            root.mkdir()
            copy_tree(root)
            expect_rc = 0
            expect_named: str | None = None
            if name == "book-char":
                book = root / "idl" / "SimRISC-06.idl"
                expect_named = _first_op(book)[0]
                _char_injection(book)
                expect_rc = 1
            elif name == "drop-id":
                expect_named = _drop_id(first_book(root))
                expect_rc = 2
            elif name == "anchor-drop":
                expect_named = _drop_anchor_op(root / ANCHOR_REL)
                expect_rc = 2
            elif name == "anchor-impl":
                expect_named = _wrong_impl(root / ANCHOR_REL)
                expect_rc = 2
            elif name == "lib-char":
                lib = root / "idl" / "lib" / "fp.idl"
                _char_anywhere(lib)
                expect_named = "lib/fp.idl"
                expect_rc = 1
            elif name == "restored":
                shutil.rmtree(root)
                root.mkdir()
                copy_tree(root)

            rc = check(root, registry, quiet=True)
            good = rc == expect_rc
            if expect_named is not None:
                with_named = _check_mentions(root, registry, expect_named)
                good = good and with_named
            print(f"[self-test {idx}/{total}] {name}: rc={rc} 期望 rc={expect_rc} ⇒ "
                  f"{'PASS' if good else 'FAIL'}")
            ok = ok and good

        # 8) 注册缺失（删一条单 id 的 `@sem("…")` 装饰行）⇒ `--update` 直接失败
        root = tmpdir / "8-update-missing"
        root.mkdir()
        copy_tree(root)
        exec_copy = root / EXEC_REL
        text = exec_copy.read_text(encoding="utf-8")
        m = re.search(r'^@sem\("([^"]+)"\)$', text, re.M)
        if m is None:
            raise AnchorError("找不到单 id 的 `@sem(\"…\")` 行")
        exec_copy.write_text(text.replace(m.group(0) + "\n", "", 1), encoding="utf-8")
        partial = load_registry(exec_copy)
        rc, _buf = _quiet(update, root, partial)
        good = rc == 2
        print(f"[self-test 8/{total}] update-missing-reg: rc={rc} 期望 rc=2 ⇒ "
              f"{'PASS' if good else 'FAIL'}")
        ok = ok and good

        # 9) 注册重名（重复一条 `@sem`）⇒ 现场派生直接失败
        root = tmpdir / "9-dup-reg"
        root.mkdir()
        copy_tree(root)
        exec_copy = root / EXEC_REL
        text = exec_copy.read_text(encoding="utf-8")
        m = re.search(r'^@sem\("([^"]+)"\)$', text, re.M)
        if m is None:
            raise AnchorError("找不到单 id 的 `@sem(\"…\")` 行")
        exec_copy.write_text(
            text + f'\n\n@sem("{m.group(1)}")\ndef _dup_probe(m, insn):\n    pass\n',
            encoding="utf-8")
        try:
            load_registry(exec_copy)
        except AnchorError:
            good = True
        else:
            good = False
        print(f"[self-test 9/{total}] duplicate-reg: raises=yes 期望 raises=yes ⇒ "
              f"{'PASS' if good else 'FAIL'}")
        ok = ok and good
    except (AnchorError, OSError) as exc:
        print(f"[self-test] 注入准备失败: {exc}", file=sys.stderr)
        ok = False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("idl-anchor self-test: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def _quiet(fn, *args):
    """调用并吞掉输出；返回 `(返回值, 输出文本)`（自检用）。"""
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        result = fn(*args)
    return result, buf.getvalue()


def _check_mentions(root: Path, registry: dict[str, str], needle: str) -> bool:
    """`check` 的输出里必须点名 `needle`（自检确认「指名」而非只变红）。"""
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        check(root, registry, quiet=False)
    text = buf.getvalue()
    hit = needle in text
    if not hit:
        print(f"    期望输出点名 `{needle}`，实得：\n{text[:400]}")
    return hit


# ── 入口 ────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="IDL 执行器「依据锁」门控")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="校验（sha 差异 rc=1；结构错 rc=2）")
    group.add_argument("--update", action="store_true", help="重写 `idl/data/exec_anchor.toml`")
    group.add_argument("--self-test", action="store_true", help="临时树内注入自检")
    ap.add_argument("--root", type=Path, default=REPO, help="另一棵同布局的树（默认仓库根）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    try:
        registry = load_registry(args.root / EXEC_REL)
    except AnchorError as exc:
        print(f"idl-anchor: FAIL — {exc}", file=sys.stderr)
        return 2
    if args.update:
        return update(args.root, registry)
    return check(args.root, registry)


if __name__ == "__main__":
    sys.exit(main())
