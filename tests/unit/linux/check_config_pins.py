#!/usr/bin/env python3
"""L1 gate: every ``CONFIG_DADAO_*`` symbol is pinned by every config slice.

Why (``ISS-470``): the same accident happened twice in ``m14-linux-017`` (F30,
F41).  A new milestone symbol (`DADAO_K4_SWITCH_SELFTEST`, then
`DADAO_K4_STACK_SELFTEST`) was added and one gate's slice did not name it, so
that image inherited whatever the shared build tree carried: one run booted an
unrelated probe image (227 false FAILs), the next stopped at a boundary it was
not testing (14 false FAILs).  Both were found by a human reading red output.

It is mechanically decidable: the Kconfig fragment is the source of truth for
*which* symbols exist, and every gate declares its pins in a module-level
``CONFIG_PINS`` dict.  This gate asserts

  C1  the Kconfig source parses to a non-empty symbol set (fail-closed: an empty
      or unreadable fragment is FAIL, never a vacuous PASS), and every symbol has
      a type;
  C2  every script that calls ``apply_config_lines`` declares ``CONFIG_PINS``
      (a new gate cannot escape), every declared dict is actually used, and its
      slice is produced by ``config_pins.config_lines(...)`` rather than by
      hand-written literals (a declared-but-unused dict would pin nothing);
  C3  for the script's image (and each ``IMAGE_PINS`` image) the pinned key set
      **equals** the Kconfig set -- a missing symbol names the script and the
      symbol, an unknown symbol names the typo.  Values are legal for the
      Kconfig type/range, and an int pinned ``"n"`` ("left unset") must really
      be invisible in that image (its ``depends on`` is not met), otherwise the
      pin would be a silent no-op;
  C4  no list/tuple element carries a hand-written ``CONFIG_DADAO_X=v`` entry:
      slices come from the pins (this is what makes C3 hold for the real image);
  C5  a module-level expectation table ``{image: {SYMBOL: value}}`` (``check_k2``
      ``IMAGE_CONFIG``, ``check_k3`` ``IMAGE_ON``) agrees with the pins, so the
      slice and the image assertions cannot drift apart.

Counts (scripts / symbols / images) are derived on the spot, never written down.
``--self-test`` builds a throw-away tree and proves six reachable FAIL paths
(missing key, unknown key, hand-written slice, int pinned unset while visible,
script without pins, empty Kconfig), restoring each time.

Usage:  python3 tests/unit/linux/check_config_pins.py [--self-test]
Exit:   0 = PASS, 1 = FAIL.
"""
from __future__ import annotations

import argparse
import ast
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.linux import config_pins  # noqa: E402

SCRIPTS_DIRS = (Path("tests") / "unit" / "linux", Path("tools") / "linux")
_ASSIGN_RE = re.compile(r"^(CONFIG_DADAO_[A-Za-z0-9_]+)=")
_SYMBOL_RE = re.compile(r"^CONFIG_DADAO_[A-Za-z0-9_]+$")
_DEP_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|&&|\|\||!|\(|\)")


class Report:
    """``[PASS]/[FAIL] <id> <name> | 期望=... 实际=...`` plus the failure list."""

    def __init__(self) -> None:
        self.fails: list[str] = []
        self.checked = 0

    def check(self, ident: str, name: str, ok: bool, expect, actual) -> bool:
        self.checked += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {ident} {name} | "
              f"期望={expect} 实际={actual}", flush=True)
        if not ok:
            self.fails.append(f"{ident} {name}: 期望={expect} 实际={actual}")
        return ok


# ---------------------------------------------------------------------------
# Kconfig dependency evaluation (only the `depends on` forms in the fragment)
# ---------------------------------------------------------------------------

def _dep_value(name: str, pins: dict[str, str]) -> bool | None:
    """Tristate truth of one dependency term; ``None`` = cannot decide."""
    symbol = name if name.startswith("CONFIG_") else "CONFIG_" + name
    value = pins.get(symbol)
    if value is None:
        return None
    if value == "y":
        return True
    if value == "n":
        return False
    return None  # an int pinned to a value: not a tristate, do not guess


def eval_depends(expr: str | None, pins: dict[str, str]) -> bool | None:
    """Evaluate a ``depends on`` expression: True/False, or None if unknown.

    Supports the forms the fragment uses (``SYM``, ``!SYM``, ``A && B``,
    ``A || B``, parentheses).  Anything else -- or a term whose value is an int
    -- yields None so the caller does not invent a verdict.
    """
    if expr is None:
        return True
    tokens = _DEP_TOKEN_RE.findall(expr)
    index = 0

    def peek() -> str | None:
        return tokens[index] if index < len(tokens) else None

    def take() -> str:
        nonlocal index
        token = tokens[index]
        index += 1
        return token

    def atom() -> bool | None:
        token = peek()
        if token is None:
            return None
        if token == "!":
            take()
            value = atom()
            return None if value is None else not value
        if token == "(":
            take()
            value = expr_or()
            if peek() == ")":
                take()
            return value
        if token in ("&&", "||", ")"):
            return None
        return _dep_value(take(), pins)

    def expr_and() -> bool | None:
        value = atom()
        while peek() == "&&":
            take()
            right = atom()
            if value is False or right is False:
                value = False
            elif value is None or right is None:
                value = None
            else:
                value = True
        return value

    def expr_or() -> bool | None:
        value = expr_and()
        while peek() == "||":
            take()
            right = expr_and()
            if value is True or right is True:
                value = True
            elif value is None or right is None:
                value = None
            else:
                value = False
        return value

    result = expr_or()
    return result if index == len(tokens) else None


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _module_assign(tree: ast.Module, name: str) -> ast.Assign | None:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node
    return None


def _calls(node: ast.AST, attr: str) -> bool:
    return any(isinstance(sub, ast.Call)
               and isinstance(sub.func, ast.Attribute)
               and sub.func.attr == attr for sub in ast.walk(node))


def _hand_written_elements(tree: ast.Module) -> list[str]:
    """Container elements that spell a config value by hand."""
    bad: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            continue
        for element in node.elts:
            candidates: list[ast.Constant] = []
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                candidates = [element]
            elif isinstance(element, ast.JoinedStr):
                candidates = [part for part in element.values
                              if isinstance(part, ast.Constant)
                              and isinstance(part.value, str)]
            for constant in candidates:
                if _ASSIGN_RE.match(constant.value):
                    bad.append(f"{constant.value!r}@L{element.lineno}")
    return bad


def _expectation_dicts(tree: ast.Module) -> list[tuple[int, dict]]:
    """Module-level ``{image: {SYMBOL: value}}`` tables (not the pins themselves)."""
    found: list[tuple[int, dict]] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if any(name in ("CONFIG_PINS", "IMAGE_PINS") for name in names):
            continue
        value = node.value
        if not isinstance(value, ast.Dict) or not value.values:
            continue
        if not all(isinstance(sub, ast.Dict) for sub in value.values):
            continue
        try:
            literal: dict = ast.literal_eval(value)
        except ValueError:
            continue
        if all(isinstance(sub, dict) and sub
               and all(_SYMBOL_RE.match(key) for key in sub)
               for sub in literal.values()):
            found.append((node.lineno, literal))
    return found


# ---------------------------------------------------------------------------
# per-script audit
# ---------------------------------------------------------------------------

def _value_problem(symbol: str, value: str, pins: dict[str, str],
                   spec: config_pins.Symbol) -> str | None:
    """Why @value is not legal for @symbol in this image (None = legal)."""
    if spec.type in ("bool", "tristate"):
        return None if value in ("y", "n") else f"{symbol}={value}（bool 只接受 y/n）"
    if spec.type == "int":
        visible = eval_depends(spec.depends, pins)
        if value == "n":
            if visible is True:
                return (f"{symbol}: 钉 n 但依赖 {spec.depends or '（无依赖）'}"
                        f"满足 ⇒ 必须给具体值"
                        f"（int 无 n 值）")
            return None
        try:
            number = int(value, 0)
        except ValueError:
            return f"{symbol}={value}（int 需要整数）"
        if spec.range:
            low, high = (int(x, 0) for x in spec.range)
            if not low <= number <= high:
                return f"{symbol}={value}（超出 range {spec.range}）"
        if visible is False:
            return (f"{symbol}={value}: 依赖 {spec.depends or '（无依赖）'} 不满足 ⇒ "
                    f"olddefconfig 会丢掉该行")
        return None
    return None if value else f"{symbol} 取值为空"


def audit_scripts(root: Path, rep: Report) -> tuple[int, int, int]:
    """Return (scripts with pins, images, symbols)."""
    symbols = config_pins.parse_kconfig(config_pins.kconfig_path(root))
    expected = set(symbols)
    pinned, images_seen = 0, 0
    script_paths = []
    for scripts_dir in SCRIPTS_DIRS:
        script_paths += [(scripts_dir, p) for p in sorted((root / scripts_dir).glob("*.py"))]
    for scripts_dir, path in script_paths:
        rel = f"{scripts_dir.as_posix()}/{path.name}"
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            rep.check("C2", f"{path.name} 可解析", False, "语法合法", str(exc))
            continue
        slices = _calls(tree, "apply_config_lines")
        assign = _module_assign(tree, "CONFIG_PINS")
        if slices and assign is None:
            rep.check("C2", f"{rel} 切片脚本声明 CONFIG_PINS", False,
                      "一个模块级 CONFIG_PINS 字典", "未声明（新增门控不能逃逸）")
            continue
        if assign is None:
            continue
        rep.check("C2", f"{rel} 切片脚本声明 CONFIG_PINS", slices,
                  "该脚本调用 apply_config_lines（不然钉子无从落地）",
                  "是" if slices else "否")
        if not slices:
            continue

        try:
            base = ast.literal_eval(assign.value)
        except ValueError:
            base = None
        if not (isinstance(base, dict) and base
                and all(isinstance(k, str) and isinstance(v, str)
                        for k, v in base.items())):
            rep.check("C2", f"{rel} CONFIG_PINS 是字面量字典", False,
                      "非空 dict[str, str] 字面量", "无法静态求值/形状不对")
            continue
        rep.check("C2", f"{rel} 切片由 config_lines 派生",
                  _calls(tree, "config_lines"),
                  "调用 config_pins.config_lines(...)",
                  "是" if _calls(tree, "config_lines") else "否（声明即使用）")
        pinned += 1

        overrides: dict[str, dict[str, str]] = {}
        image_assign = _module_assign(tree, "IMAGE_PINS")
        if image_assign is not None:
            try:
                overrides = ast.literal_eval(image_assign.value)
            except ValueError:
                overrides = {}
            ok_shape = isinstance(overrides, dict) and all(
                isinstance(name, str) and isinstance(sub, dict)
                and all(isinstance(k, str) and isinstance(v, str)
                        for k, v in sub.items())
                for name, sub in overrides.items())
            rep.check("C2", f"{rel} IMAGE_PINS 是字面量字典", ok_shape,
                      "dict[str, dict[str, str]]",
                      "字面量" if ok_shape else "无法静态求值/形状不对")
            if not ok_shape:
                overrides = {}

        images: dict[str, dict[str, str]] = {"": dict(base)}
        aliases: set[str] = set()
        for name, extra in overrides.items():
            if not extra:  # names the base image (expectation tables use it)
                aliases.add(name)
                continue
            merged = dict(base)
            merged.update(extra)
            images[name] = merged

        problems: list[str] = []
        # The base image carries the complete set; an override image re-uses it
        # and can only replace values, so only the replaced values are re-judged
        # (an override key that names an unknown symbol is its own problem).
        for name, pins in images.items():
            images_seen += 1
            label = f"{path.name}{'[' + name + ']' if name else ''}"
            if not name:
                missing = sorted(expected - set(pins))
                extra_keys = sorted(set(pins) - expected)
                if missing:
                    problems.append(f"{label} 缺 " + "、".join(missing))
                if extra_keys:
                    problems.append(f"{label} 多出不存在符号 "
                                    + "、".join(extra_keys))
                changed = sorted(pins)
            else:
                changed = sorted(overrides[name])
                extra_keys = sorted(set(changed) - expected)
                undeclared = sorted(set(changed) - set(base))
                if extra_keys:
                    problems.append(f"{label} 多出不存在符号 "
                                    + "、".join(extra_keys))
                if undeclared:
                    problems.append(f"{label} 覆盖了未在 CONFIG_PINS 声明的符号 "
                                    + "、".join(undeclared))
            for symbol in changed:
                value = pins[symbol]
                spec = symbols.get(symbol)
                if spec is None:
                    continue  # already reported as an extra key
                why = _value_problem(symbol, value, pins, spec)
                if why:
                    problems.append(f"{label} {why}")
        rep.check("C3", f"{rel} 钉子全集 == Kconfig（{len(images)} 镜像 × "
                  f"{len(expected)} 符号）", not problems,
                  "每镜像键集合 == Kconfig 且取值合法",
                  "全部通过" if not problems else "；".join(problems))

        bad = _hand_written_elements(tree)
        rep.check("C4", f"{rel} 无手写切片字面量", not bad,
                  "切片来自 CONFIG_PINS", bad or "无")

        for lineno, table in _expectation_dicts(tree):
            drift = []
            for image, sub in table.items():
                pins = images.get(image)
                if pins is None and image in aliases:
                    pins = images[""]
                for symbol, value in sub.items():
                    if pins is None:
                        drift.append(f"{image}: 没有这个镜像")
                    elif pins.get(symbol) != value:
                        drift.append(f"{image}/{symbol}: 表={value} "
                                     f"钉子={pins.get(symbol)}")
            rep.check("C5", f"{rel}:{lineno} 期望表与钉子一致", not drift,
                      "表值 == 钉子值", drift or "无")
    return pinned, images_seen, len(symbols)


def run_checks(root: Path) -> tuple[int, Report]:
    rep = Report()
    print("── CONFIG_DADAO_* 钉子全集检查（Kconfig 真源 ↔ 每个切片脚本）──")
    path = config_pins.kconfig_path(root)
    rep.check("C1", "Kconfig 真源存在（fail-closed）", path.is_file(),
              "文件存在", "缺失" if not path.is_file() else "存在")
    symbols: dict[str, config_pins.Symbol] = {}
    if path.is_file():
        symbols = config_pins.parse_kconfig(path)
        rep.check("C1", "解析到 CONFIG_DADAO_* 符号（fail-closed）",
                  bool(symbols), "≥1 个符号", f"{len(symbols)} 个")
        untyped = sorted(name for name, spec in symbols.items()
                         if spec.type == "unknown")
        rep.check("C1", "每个符号都声明了类型", not untyped,
                  "bool/int/...", untyped or "全部有类型")
    if not symbols:
        print("  [INFO] Kconfig 解析不到符号 ⇒ 直接判红，不再逐脚本比对"
              "（fail-closed，防空转）")
        pinned = images_seen = symbol_count = 0
    else:
        pinned, images_seen, symbol_count = audit_scripts(root, rep)
    print(f"\n现场统计：切片脚本 {pinned} 个、Kconfig 符号 {symbol_count} 个、"
          f"镜像 {images_seen} 个")
    rc = 1 if rep.fails else 0
    print(f"\n结果：{'PASS' if rc == 0 else 'FAIL'}"
          f"（检查 {rep.checked} 项，失败 {len(rep.fails)} 项，退出码 {rc}）")
    for line in rep.fails:
        print(f"  - {line}")
    return rc, rep


# ---------------------------------------------------------------------------
# self-test: six reachable FAIL paths on a throw-away tree
# ---------------------------------------------------------------------------

def _self_test() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="config-pins-selftest-"))
    try:
        (tmp / config_pins.KCONFIG_REL).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config_pins.kconfig_path(REPO), tmp / config_pins.KCONFIG_REL)
        for scripts_dir in SCRIPTS_DIRS:
            shutil.copytree(REPO / scripts_dir, tmp / scripts_dir,
                            ignore=shutil.ignore_patterns("__pycache__"))

        print("── self-test 基线（未注入应 PASS）──")
        rc, _ = run_checks(tmp)
        if rc != 0:
            print(f"self-test: 基线未通过（rc={rc}）", file=sys.stderr)
            return 1

        k0 = tmp / SCRIPTS_DIRS[0] / "check_k0.py"
        k3 = tmp / SCRIPTS_DIRS[0] / "check_k3.py"
        kconfig = tmp / config_pins.KCONFIG_REL
        originals = {path: path.read_text(encoding="utf-8")
                     for path in (k0, k3, kconfig)}

        def mentions(rep: Report, *needles: str) -> bool:
            return any(all(needle in line for needle in needles)
                       for line in rep.fails)

        cases = [
            ("缺一个符号", k3,
             '    "CONFIG_DADAO_K2_SELFTEST_CFXESC": "n",\n', "",
             lambda rep: mentions(rep, "check_k3.py", "CONFIG_DADAO_K2_SELFTEST_CFXESC", "缺")),
            ("多一个不存在的符号", k0, "CONFIG_PINS = {\n",
             'CONFIG_PINS = {\n    "CONFIG_DADAO_FAKE_SELFTEST": "n",\n',
             lambda rep: mentions(rep, "CONFIG_DADAO_FAKE_SELFTEST", "多出")),
            ("手写切片字面量", k0,
             "K0_CONFIG = config_pins.config_lines(CONFIG_PINS)\n",
             "K0_CONFIG = config_pins.config_lines(CONFIG_PINS)\n"
             'EXTRA = ["CONFIG_DADAO_K1_EARLY_STOP=y"]\n',
             lambda rep: mentions(rep, "手写切片", "CONFIG_DADAO_K1_EARLY_STOP=y")),
            ("int 钉 n 但依赖满足", k3,
             '    "CONFIG_DADAO_K2_TIME_STOP": "n",\n',
             '    "CONFIG_DADAO_K2_TIME_STOP": "y",\n',
             lambda rep: mentions(rep, "CONFIG_DADAO_K2_TIME_CASE", "必须给具体值")),
        ]
        failures = 0
        for label, path, old, new, reason in cases:
            text = originals[path]
            count = text.count(old)
            print(f"\n── self-test 注入：{label}（命中 {count} 处）──")
            if count != 1:
                print("  [FAIL] 注入点不唯一，判据失效", file=sys.stderr)
                failures += 1
                continue
            path.write_text(text.replace(old, new), encoding="utf-8")
            rc_bad, rep_bad = run_checks(tmp)
            hit = reason(rep_bad)
            print(f"  [{'PASS' if rc_bad != 0 and hit else 'FAIL'}] 注入后应非零且点名"
                  f" | expected=rc!=0 且原因命中 actual=rc={rc_bad} 命中={hit}")
            if rc_bad == 0 or not hit:
                failures += 1
            path.write_text(text, encoding="utf-8")
            rc_good, _ = run_checks(tmp)
            print(f"  [{'PASS' if rc_good == 0 else 'FAIL'}] 还原后应回绿"
                  f" | expected=rc=0 actual=rc={rc_good}")
            if rc_good != 0:
                failures += 1

        escape = tmp / SCRIPTS_DIRS[0] / "check_k9.py"
        escape.write_text(
            "from tools.linux import make_defconfig as defconfig\n"
            "def go():\n"
            "    return defconfig.apply_config_lines(['CONFIG_DADAO_K1_EARLY_STOP=y'])\n",
            encoding="utf-8")
        print("\n── self-test 注入：切片脚本没有 CONFIG_PINS ──")
        rc_bad, rep_bad = run_checks(tmp)
        hit = mentions(rep_bad, "check_k9.py", "CONFIG_PINS")
        print(f"  [{'PASS' if rc_bad != 0 and hit else 'FAIL'}] 应红并点名 "
              f"| expected=rc!=0 且点名 check_k9.py actual=rc={rc_bad} 命中={hit}")
        if rc_bad == 0 or not hit:
            failures += 1
        escape.unlink()
        rc_good, _ = run_checks(tmp)
        print(f"  [{'PASS' if rc_good == 0 else 'FAIL'}] 删除后应回绿"
              f" | expected=rc=0 actual=rc={rc_good}")
        if rc_good != 0:
            failures += 1

        print("\n── self-test 注入：Kconfig 解析不到符号（fail-closed）──")
        kconfig.write_text(
            "diff --git a/arch/dadao/Kconfig.debug b/arch/dadao/Kconfig.debug\n"
            "--- /dev/null\n+++ b/arch/dadao/Kconfig.debug\n"
            "@@ -0,0 +1 @@\n+# nothing here\n", encoding="utf-8")
        rc_bad, rep_bad = run_checks(tmp)
        hit = mentions(rep_bad, "C1", "fail-closed")
        print(f"  [{'PASS' if rc_bad != 0 and hit else 'FAIL'}] 应红 "
              f"| expected=rc!=0 且命中 fail-closed actual=rc={rc_bad} 命中={hit}")
        if rc_bad == 0 or not hit:
            failures += 1
        kconfig.write_text(originals[kconfig], encoding="utf-8")
        rc_good, _ = run_checks(tmp)
        print(f"  [{'PASS' if rc_good == 0 else 'FAIL'}] 还原后应回绿"
              f" | expected=rc=0 actual=rc={rc_good}")
        if rc_good != 0:
            failures += 1

        total = len(cases) + 2
        print(f"\nself-test: {total} 类注入，失败 {failures} 项")
        return 0 if failures == 0 else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="CONFIG_DADAO_* 钉子全集门控")
    parser.add_argument("--self-test", action="store_true",
                        help="6 类注入自检（临时树）")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    rc, _rep = run_checks(REPO)
    return rc


if __name__ == "__main__":
    sys.exit(main())
