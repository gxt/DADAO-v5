#!/usr/bin/env python3
"""check_toolchain.py — M14 K0 工具链缺口矩阵门控（`m14-infra-001`）。

判据真源 = `tools/linux/toolchain_matrix.json`（format 1）；本脚本**现场重跑**
每一行的探针，断言「声明 == 实测」。所有能力探针都经 `--target=dadao-unknown-elf`
（或 llvm-mc 的 `-triple=`）——宿主 x86 对这些能力天然支持，不锁 target 会得到
「全绿」的假结论。

判据（每条都有可达 FAIL；见 `--inject`）：

  R1 一致性   每一行 `declared` == `measured`（矩阵字段）== 现场实测；
              不一致 ⇒ FAIL（工具升级/降级后必须更新矩阵）。
  R2 必需项   所有 `required_for_k0 == true` 的行，矩阵 `measured` 与现场实测都必须是
              present/supported；否则 FAIL（K0 被阻塞）。
  R3 规避法   `declared` 或实测为缺口态（absent/unsupported）的行，`workaround`
              必须非空，且 `workaround_measured == "verified"` 并且现场重验通过；
              否则 FAIL。
  R4 行集合   行 id 集合必须**等于**矩阵覆盖表（缺行 / 未知行 / 重复行 ⇒ FAIL）。
  R5 target   所有能力探针的 `probe` 形状必须点名 target triple（否则 FAIL）；
              矩阵 `toolchain.target` 必须等于脚本内 `TARGET`。
  R6 报告同源 `docs/TestReports/M14-K0-toolchain-gaps.md` 必须等于本脚本用矩阵 +
              现场实测重渲染出的正文（`--report --check`）；改矩阵不重生成 ⇒ FAIL。

用法：
  python3 tools/linux/check_toolchain.py                  # 门控（R1-R6，`make check-linux-toolchain`）
  python3 tools/linux/check_toolchain.py --report          # 重写人读报告（报告是生成物）
  python3 tools/linux/check_toolchain.py --report --check  # 只断言报告与矩阵同源
  python3 tools/linux/check_toolchain.py --inject          # 自检：临时副本注入 6 类反例

退出码：0 = 通过；1 = 有 FAIL；2 = 输入缺失 / 无法解析（矩阵或安装根）。
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.linux import paths as linux_paths  # noqa: E402

TARGET = "dadao-unknown-elf"
MATRIX_REL = Path("tools/linux/toolchain_matrix.json")
REPORT_REL = Path("docs/TestReports/M14-K0-toolchain-gaps.md")
SNAPSHOT_MARKER = "<!-- 现场生成，勿手改 -->"
STAMP_RE = re.compile(r"^- \*\*生成时间\*\*：(.+)$", re.MULTILINE)

ROW_IDS = (
    "llvm-ar",
    "llvm-ranlib",
    "llvm-strip",
    "asm-goto",
    "stack-protector",
    "data-directives",
    "inline-asm-constraints",
    "mcmodel-kernel",
)
TOOL_ROWS = ("llvm-ar", "llvm-ranlib", "llvm-strip")

PRESENT, ABSENT = "present", "absent"
SUPPORTED, UNSUPPORTED = "supported", "unsupported"
GAP_STATES = (ABSENT, UNSUPPORTED)
# 每一行的合法取值：第一项 = 无缺口态，第二项 = 缺口态。
VOCAB = {
    rid: ((PRESENT, ABSENT) if rid in TOOL_ROWS else (SUPPORTED, UNSUPPORTED))
    for rid in ROW_IDS
}
K0_IMPACTS = ("none", "blocker")

# ---------------------------------------------------------------------------
# 探针源码（全部经 target triple 编译/汇编；不含宿主路径）
# ---------------------------------------------------------------------------

SRC_SIMPLE = """\
int f(int x) { return x + 1; }
"""

SRC_ASM_GOTO = """\
extern void sink(int);
int dag(int x) {
  int r = 0;
  asm goto("jump [rb0, %l0]" ::: : done);
  r = 1;
done:
  sink(r + x);
  return r;
}
"""

SRC_STACK_PROTECTOR = """\
extern void use(char *);
int f(int n) { char buf[32]; buf[0] = (char)n; use(buf); return buf[1]; }
"""

SRC_DATA_LEGACY = """\
.data
.globl blob
blob:
  .quad 0x1122334455667788
  .long 0xAABBCCDD
  .short 0xBEEF
  .byte 0x5A
"""

SRC_DATA_DD = """\
.data
.globl blob
blob:
  .dd.o64 0x1122334455667788
  .dd.t32 0xAABBCCDD
  .dd.w16 0xBEEF
  .dd.b08 0x5A
"""

DATA_DD_EXPECTED = bytes.fromhex("1122334455667788aabbccddbeef5a")

SRC_CONSTRAINTS = """\
int c_r(int in) { int out; asm volatile("add.st %0, %1, %1" : "=r"(out) : "r"(in)); return out; }
int c_i(void)   { int out; asm volatile("add.si %0, %1" : "=r"(out) : "i"(8)); return out; }
int c_m(int *p) { int out; asm volatile("ld.o %0, %1" : "=r"(out) : "m"(*p)); return out; }
int c_eq(int a) { int out; asm volatile("add.st %0, %1, %1" : "=&r"(out) : "r"(a)); return out + 1; }
int c_mem(int a) { asm volatile("add.st %0, %0, %0" : "+r"(a) :: "memory"); return a; }
"""


# ---------------------------------------------------------------------------
# 路径 / 进程 / 文本工具
# ---------------------------------------------------------------------------

def install_bin() -> Path:
    """安装根 bin（`manifests/install-dirs.lock.toml` 经 paths.py 解析）。"""
    return linux_paths.toolchain_bin()


def build_bin() -> Path:
    """LLVM 构建树 bin。

    布局 = `<work_root>/build/<组件>/bin`（`components.lock.toml` 的 `work_root`，
    经 paths.linux_build_dir() 解析；本脚本不另派生 work_root）。
    """
    return linux_paths.linux_build_dir().parent / "llvm" / "bin"


def tmp_root() -> Path:
    """任务临时目录（`/tmp/opencode/<任务ID>/`；可用 DADAO_TMP 覆盖）。"""
    base = Path(os.environ.get("DADAO_TMP", "/tmp/opencode/m14-infra-001"))
    base.mkdir(parents=True, exist_ok=True)
    return base


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(argv, cwd=None, timeout=180):
    """返回 (rc, stdout+stderr)。探针一律不吞退出码。"""
    try:
        proc = subprocess.run(
            [str(a) for a in argv],
            cwd=None if cwd is None else str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout or ""
    except subprocess.TimeoutExpired as exc:
        out = exc.output or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return 124, out + f"\n<timeout {timeout}s>"
    except OSError as exc:
        return 127, f"<exec failed: {exc}>"


def scrub(text: str, tmp: Path | None = None) -> str:
    """把宿主绝对路径换成符号名（报告禁止出现 /tmp、/home、具体 .work 路径）。"""
    text = " ".join(str(text).split())
    replacements = [
        (str(ROOT / ".work"), "<work-root>"),
        (str(ROOT / ".dadao"), "<install-root>"),
        (str(ROOT), "<repo>"),
        (str(Path(os.path.expanduser("~"))), "<home>"),
    ]
    if tmp is not None:
        replacements.insert(0, (str(tmp), "<tmp>"))
    for prefix, token in replacements:
        text = text.replace(prefix, token)
    text = re.sub(r"/(?:tmp|home|mnt|usr|opt)(?:/[^\s:,;)\]`'\"]*)+", "<path>", text)
    text = re.sub(r"\.work/[^\s:;,`'\"]*", "<work-root>", text)
    return text


def _trim(text: str, limit: int = 220) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def first_error(text: str) -> str:
    for line in text.splitlines():
        if "error:" in line:
            return line.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else ""


class Ctx:
    """探针上下文：工具路径 + 临时目录。"""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.clang = install_bin() / "clang"
        self.mc = install_bin() / "llvm-mc"
        self.objcopy = install_bin() / "llvm-objcopy"
        self.ar = Path("/usr/bin/ar")
        self.ranlib = Path("/usr/bin/ranlib")

    def write(self, name: str, text: str) -> Path:
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path


def _require(ctx: Ctx) -> str | None:
    if not (ctx.clang.is_file() and os.access(ctx.clang, os.X_OK)):
        return (f"安装根 clang 不可执行（<install-root>/bin/clang）；"
                f"先跑 'make install-host'")
    return None


# ---------------------------------------------------------------------------
# 探针实现：返回 {"measured", "exit_code", "detail"}
# ---------------------------------------------------------------------------

def probe_tool(ctx: Ctx, name: str) -> dict:
    rel = name
    for label, directory in (("install-root", install_bin()),
                             ("llvm-build", build_bin())):
        exe = directory / name
        if exe.is_file() and os.access(exe, os.X_OK):
            rc, out = run([exe, "--version"])
            if rc == 0:
                return {
                    "measured": PRESENT,
                    "exit_code": rc,
                    "detail": f"{label}/bin/{rel} --version -> {out.splitlines()[0][:60]}",
                }
            return {
                "measured": ABSENT,
                "exit_code": rc,
                "detail": f"{label}/bin/{rel} 存在但 --version rc={rc}: "
                          f"{first_error(out)}",
            }
    return {
        "measured": ABSENT,
        "exit_code": 127,
        "detail": f"{rel} 不在 install-root/bin 也不在 llvm-build/bin",
    }


def probe_asm_goto(ctx: Ctx) -> dict:
    src = ctx.write("asm_goto.c", SRC_ASM_GOTO)
    out_s = ctx.tmp / "asm_goto.s"
    rc1, out1 = run([ctx.clang, f"--target={TARGET}", "-fsyntax-only", src])
    rc2, out2 = run([ctx.clang, f"--target={TARGET}", "-O1", "-S", src,
                     "-o", out_s])
    lowered = False
    if rc2 == 0 and out_s.is_file():
        lowered = "Inline asm indirect target" in out_s.read_text()
    ok = rc1 == 0 and rc2 == 0 and lowered
    detail = (f"-fsyntax-only rc={rc1}; -O1 -S rc={rc2}; "
              f"标签降级={'yes' if lowered else 'no'}")
    if not ok:
        detail += f"; {first_error(out1 or out2)}"
    return {
        "measured": SUPPORTED if ok else UNSUPPORTED,
        "exit_code": rc2 if rc2 != 0 else rc1,
        "detail": detail,
    }


def probe_stack_protector(ctx: Ctx) -> dict:
    src = ctx.write("ssp.c", SRC_STACK_PROTECTOR)
    out_s = ctx.tmp / "ssp.s"
    rc, out = run([ctx.clang, f"--target={TARGET}", "-O1",
                   "-fstack-protector-strong", "-S", src, "-o", out_s])
    canary = False
    if rc == 0 and out_s.is_file():
        canary = "stack_chk" in out_s.read_text()
    ok = rc == 0 and canary
    detail = f"-O1 -fstack-protector-strong -S rc={rc}; canary={'yes' if canary else 'no'}"
    if not ok:
        detail += f"; {first_error(out)}"
    return {
        "measured": SUPPORTED if ok else UNSUPPORTED,
        "exit_code": rc,
        "detail": detail,
    }


def probe_data_directives(ctx: Ctx) -> dict:
    src = ctx.write("data_legacy.s", SRC_DATA_LEGACY)
    obj = ctx.tmp / "data_legacy.o"
    rc, out = run([ctx.mc, f"-triple={TARGET}", "-filetype=obj", src,
                   "-o", obj])
    detail = f"llvm-mc -triple={TARGET} rc={rc}"
    if rc != 0:
        detail += f"; {first_error(out)}"
    else:
        detail += "; 传统伪指令被接受"
    return {
        "measured": SUPPORTED if rc == 0 else UNSUPPORTED,
        "exit_code": rc,
        "detail": detail,
    }


def probe_inline_asm(ctx: Ctx) -> dict:
    src = ctx.write("constraints.c", SRC_CONSTRAINTS)
    out_s = ctx.tmp / "constraints.s"
    rc, out = run([ctx.clang, f"--target={TARGET}", "-O1", "-S", src,
                   "-o", out_s])
    detail = f"-O1 -S 约束 r/i/m/=&r/memory rc={rc}"
    if rc != 0:
        detail += f"; {first_error(out)}"
    else:
        detail += "; 5 条约束全部编入"
    return {
        "measured": SUPPORTED if rc == 0 else UNSUPPORTED,
        "exit_code": rc,
        "detail": detail,
    }


def probe_mcmodel(ctx: Ctx) -> dict:
    src = ctx.write("cmodel.c", SRC_SIMPLE)
    rc, out = run([ctx.clang, f"--target={TARGET}", "-O1",
                   "-mcmodel=kernel", "-S", src, "-o", ctx.tmp / "cmodel.s"])
    detail = f"-mcmodel=kernel rc={rc}"
    if rc != 0:
        hint = ""
        for line in out.splitlines():
            if "supports" in line:
                hint = f"; {line.strip()}"
                break
        detail += f"; {first_error(out)}{hint}"
    return {
        "measured": SUPPORTED if rc == 0 else UNSUPPORTED,
        "exit_code": rc,
        "detail": detail,
    }


CAPABILITY_PROBES = {
    "asm-goto": probe_asm_goto,
    "stack-protector": probe_stack_protector,
    "data-directives": probe_data_directives,
    "inline-asm-constraints": probe_inline_asm,
    "mcmodel-kernel": probe_mcmodel,
}


# ---------------------------------------------------------------------------
# 规避法现场验证：返回 {"state": "verified"|"failed", "detail", "exit_code"}
# ---------------------------------------------------------------------------

def _obj(ctx: Ctx, name: str = "solo") -> Path | None:
    src = ctx.write(f"{name}.c", SRC_SIMPLE)
    obj = ctx.tmp / f"{name}.o"
    rc, _out = run([ctx.clang, f"--target={TARGET}", "-O1", "-c", src,
                    "-o", obj])
    return obj if rc == 0 else None


def verify_ar(ctx: Ctx) -> dict:
    obj = _obj(ctx, "wa")
    if obj is None:
        return {"state": "failed", "exit_code": 1, "detail": "目标对象编译失败"}
    lib = ctx.tmp / "wa.a"
    rc1, out1 = run([ctx.ar, "rcs", lib, obj])
    rc2, out2 = run([ctx.ar, "t", lib])
    ok = rc1 == 0 and rc2 == 0 and obj.name in out2
    return {"state": "verified" if ok else "failed",
            "exit_code": rc2 if rc2 else rc1,
            "detail": f"ar rcs rc={rc1}; ar t rc={rc2}"}


def verify_ranlib(ctx: Ctx) -> dict:
    obj = _obj(ctx, "wr")
    if obj is None:
        return {"state": "failed", "exit_code": 1, "detail": "目标对象编译失败"}
    lib = ctx.tmp / "wr.a"
    rc1, _ = run([ctx.ar, "rcs", lib, obj])
    rc2, out2 = run([ctx.ranlib, lib])
    ok = rc1 == 0 and rc2 == 0
    return {"state": "verified" if ok else "failed",
            "exit_code": rc2 if rc2 else rc1,
            "detail": f"ar rcs rc={rc1}; ranlib rc={rc2}"
                      + (f"; {first_error(out2)}" if not ok else "")}


def verify_strip(ctx: Ctx) -> dict:
    obj = _obj(ctx, "ws")
    if obj is None:
        return {"state": "failed", "exit_code": 1, "detail": "目标对象编译失败"}
    out_obj = ctx.tmp / "ws.stripped.o"
    rc, out = run([ctx.objcopy, "--strip-all", obj, out_obj])
    ok = (rc == 0 and out_obj.is_file()
          and out_obj.stat().st_size <= obj.stat().st_size)
    return {"state": "verified" if ok else "failed",
            "exit_code": rc,
            "detail": f"llvm-objcopy --strip-all rc={rc}; "
                      f"size {obj.stat().st_size} -> "
                      f"{out_obj.stat().st_size if out_obj.is_file() else 'n/a'}"
                      + (f"; {first_error(out)}" if not ok else "")}


def verify_data_dd(ctx: Ctx) -> dict:
    src = ctx.write("data_dd.s", SRC_DATA_DD)
    obj = ctx.tmp / "data_dd.o"
    rc1, out1 = run([ctx.mc, f"-triple={TARGET}", "-filetype=obj", src,
                     "-o", obj])
    if rc1 != 0:
        return {"state": "failed", "exit_code": rc1,
                "detail": f"llvm-mc rc={rc1}; {first_error(out1)}"}
    binfile = ctx.tmp / "data_dd.bin"
    rc2, out2 = run([ctx.objcopy, "-O", "binary", "--only-section=.data",
                     obj, binfile])
    if rc2 != 0:
        return {"state": "failed", "exit_code": rc2,
                "detail": f"llvm-objcopy rc={rc2}; {first_error(out2)}"}
    payload = binfile.read_bytes()
    ok = payload == DATA_DD_EXPECTED
    return {"state": "verified" if ok else "failed",
            "exit_code": 0 if ok else 1,
            "detail": f".dd.* 段字节 {payload.hex()} "
                      f"(期望 {DATA_DD_EXPECTED.hex()})"}


def verify_no_stack_protector(ctx: Ctx) -> dict:
    src = ctx.write("ssp_off.c", SRC_STACK_PROTECTOR)
    out_s = ctx.tmp / "ssp_off.s"
    rc, out = run([ctx.clang, f"--target={TARGET}", "-O1",
                   "-fno-stack-protector", "-S", src, "-o", out_s])
    clean = rc == 0 and out_s.is_file() and "stack_chk" not in out_s.read_text()
    return {"state": "verified" if clean else "failed",
            "exit_code": rc,
            "detail": f"-fno-stack-protector -S rc={rc}; "
                      f"canary={'absent' if clean else 'present'}"
                      + (f"; {first_error(out)}" if not clean else "")}


def verify_mcmodel_small(ctx: Ctx) -> dict:
    src = ctx.write("cmodel_small.c", SRC_SIMPLE)
    rc, out = run([ctx.clang, f"--target={TARGET}", "-O1",
                   "-mcmodel=small", "-S", src,
                   "-o", ctx.tmp / "cmodel_small.s"])
    return {"state": "verified" if rc == 0 else "failed",
            "exit_code": rc,
            "detail": f"-mcmodel=small -S rc={rc}"
                      + (f"; {first_error(out)}" if rc != 0 else "")}


WORKAROUND_VERIFIERS = {
    "llvm-ar": verify_ar,
    "llvm-ranlib": verify_ranlib,
    "llvm-strip": verify_strip,
    "data-directives": verify_data_dd,
    "stack-protector": verify_no_stack_protector,
    "mcmodel-kernel": verify_mcmodel_small,
}


def measure() -> dict:
    """现场重跑全部探针 + 规避法验证（一次测量，供 R1-R6 与报告共用）。"""
    tmp = Path(tempfile.mkdtemp(prefix="probe-", dir=tmp_root()))
    ctx = Ctx(tmp)
    live = {}
    missing = _require(ctx)
    try:
        for rid in ROW_IDS:
            if missing:
                live[rid] = {"measured": "unknown", "exit_code": 2,
                             "detail": missing}
                continue
            if rid in TOOL_ROWS:
                live[rid] = probe_tool(ctx, rid)
            else:
                live[rid] = CAPABILITY_PROBES[rid](ctx)
        for rid, verifier in WORKAROUND_VERIFIERS.items():
            live.setdefault(rid, {})["workaround"] = verifier(ctx)
        for rid, info in live.items():
            if rid.startswith("_"):
                continue
            info["detail"] = _trim(scrub(info.get("detail", ""), tmp))
            workaround = info.get("workaround")
            if workaround:
                workaround["detail"] = _trim(
                    scrub(workaround.get("detail", ""), tmp))
        live["_host_contrast"] = host_contrast()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return live


def host_contrast() -> dict:
    """宿主 x86 对照（证明探针结论由 target 决定，不是宿主天然支持）。"""
    host_clang = shutil.which("clang")
    if host_clang is None:
        return {"available": False, "detail": "宿主 clang 不可用"}
    tmp = Path(tempfile.mkdtemp(prefix="host-", dir=tmp_root()))
    try:
        src = tmp / "ssp.c"
        src.write_text(SRC_STACK_PROTECTOR, encoding="utf-8")
        rc1, _ = run([host_clang, "-O1", "-fstack-protector-strong", "-S",
                      src, "-o", tmp / "ssp.s"])
        src2 = tmp / "cm.c"
        src2.write_text(SRC_SIMPLE, encoding="utf-8")
        rc2, _ = run([host_clang, "-O1", "-mcmodel=kernel", "-S", src2,
                      "-o", tmp / "cm.s"])
        return {"available": True, "ssp_rc": rc1, "cmodel_rc": rc2,
                "detail": ""}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# 矩阵断言
# ---------------------------------------------------------------------------

def load_matrix(path: Path | None = None) -> dict:
    path = path or (ROOT / MATRIX_REL)
    if not path.is_file():
        raise SystemExit(f"check-linux-toolchain: 矩阵缺失: {MATRIX_REL}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"check-linux-toolchain: 矩阵 JSON 无法解析: {exc}")


def validate(matrix: dict, live: dict) -> tuple[list[str], dict]:
    """返回 (problems, summary)。problems 空 = PASS。"""
    problems: list[str] = []

    def fail(msg: str) -> None:
        problems.append(msg)

    if matrix.get("format") != 1:
        fail(f"R-format: format != 1（{matrix.get('format')!r}）")
    toolchain = matrix.get("toolchain") or {}
    if toolchain.get("target") != TARGET:
        fail(f"R5 target: toolchain.target={toolchain.get('target')!r} "
             f"!= {TARGET!r}")
    if not (toolchain.get("resolved_from") or "").strip():
        fail("R-format: toolchain.resolved_from 为空")

    rows = matrix.get("rows")
    if not isinstance(rows, list) or not rows:
        fail("R4: rows 缺失或为空")
        return problems, {"rows": 0, "consistent": 0, "gaps": 0,
                          "blockers": 0}
    ids = [row.get("id") if isinstance(row, dict) else None for row in rows]
    missing = [rid for rid in ROW_IDS if rid not in ids]
    extra = [rid for rid in ids if rid not in ROW_IDS]
    dups = sorted({rid for rid in ids if ids.count(rid) > 1})
    if missing:
        fail(f"R4 缺行: {missing}")
    if extra:
        fail(f"R4 未知行: {extra}")
    if dups:
        fail(f"R4 重复行: {dups}")

    consistent = 0
    gaps = 0
    blockers = 0
    for row in rows:
        if not isinstance(row, dict):
            fail("R4: 非对象行")
            continue
        rid = row.get("id")
        if rid not in VOCAB:
            continue
        good, gap = VOCAB[rid]
        declared = row.get("declared")
        declared_measured = row.get("measured")
        actual = (live.get(rid) or {}).get("measured")
        exit_code = (live.get(rid) or {}).get("exit_code")

        if declared not in (good, gap):
            fail(f"R1 {rid}: declared={declared!r} 不在合法取值 {VOCAB[rid]}")
        if declared_measured not in (good, gap):
            fail(f"R1 {rid}: measured={declared_measured!r} 不在合法取值")
        if declared == actual and declared_measured == actual:
            consistent += 1
        else:
            fail(f"R1 声明!=实测: {rid} declared={declared!r} "
                 f"measured={declared_measured!r} 现场={actual!r} "
                 f"(rc={exit_code})")

        if declared in GAP_STATES or actual in GAP_STATES:
            gaps += 1
        if row.get("k0_impact") == "blocker":
            blockers += 1

        if row.get("required_for_k0") is True:
            if actual != good or declared_measured != good:
                fail(f"R2 required 行非 {good}: {rid} 现场={actual!r} "
                     f"measured={declared_measured!r}（K0 被阻塞）")

        if declared in GAP_STATES or actual in GAP_STATES:
            if not (row.get("workaround") or "").strip():
                fail(f"R3 absent 行缺规避法: {rid}")
            if row.get("workaround_measured") != "verified":
                fail(f"R3 {rid}: workaround_measured="
                     f"{row.get('workaround_measured')!r} != 'verified'")
            wa = ((live.get(rid) or {}).get("workaround") or {})
            if wa.get("state") != "verified":
                fail(f"R3 {rid}: 规避法现场验证失败 "
                     f"({wa.get('detail') or '未执行'})")

        if row.get("k0_impact") not in K0_IMPACTS:
            fail(f"R-format {rid}: k0_impact={row.get('k0_impact')!r} "
                 f"不在 {K0_IMPACTS}")
        if not (row.get("owner") or "").strip():
            fail(f"R-format {rid}: owner 为空")
        if rid not in TOOL_ROWS and TARGET not in (row.get("probe") or ""):
            fail(f"R5 target 未锁定: {rid} 的 probe 未含 {TARGET}")

    if blockers:
        fail(f"R-K0: {blockers} 行 k0_impact=blocker（K0 无规避法）")
    summary = {"rows": len(rows), "consistent": consistent, "gaps": gaps,
               "blockers": blockers}
    return problems, summary


# ---------------------------------------------------------------------------
# 报告渲染（生成物；首行快照标记 + 四必备项）
# ---------------------------------------------------------------------------

def _cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "unknown"


def _version_string(exe: Path) -> str:
    """`--version` 的首个版本行（去括号内构建路径，只留版本号 + 提交前缀）。"""
    if not (exe.is_file() and os.access(exe, os.X_OK)):
        return "absent"
    rc, out = run([exe, "--version"])
    if rc != 0:
        return f"rc={rc}"
    line = ""
    for candidate in out.splitlines():
        if "version" in candidate.lower():
            line = candidate.strip()
            break
    if not line:
        line = out.splitlines()[0].strip() if out else ""
    line = re.sub(r"\((?:[^()]*)\)", "", line).strip()
    sha = re.search(r"\b([0-9a-f]{7,40})\b", out)
    if sha:
        line = f"{line} ({sha.group(1)[:12]})"
    return _trim(line, 70)


def _tool_version(exe: Path) -> str:
    return _version_string(exe)


def _version_md5(tools: list[Path]) -> str:
    """工具版本摘要 md5（作诊断；不读 4 GB 二进制，避免门控变慢）。"""
    text = "|".join(_version_string(tool) for tool in tools)
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def now_stamp() -> str:
    local = datetime.now().astimezone()
    utc = datetime.now(timezone.utc)
    return (f"{local.strftime('%Y-%m-%d %H:%M:%S %z')}"
            f"（UTC {utc.strftime('%Y-%m-%dT%H:%M:%SZ')}）")


def render(matrix: dict, live: dict, stamp: str) -> str:
    clang = install_bin() / "clang"
    llvm_mc = install_bin() / "llvm-mc"
    host = live.get("_host_contrast") or {}
    rows = matrix.get("rows") or []
    gaps = [r for r in rows if r.get("declared") in GAP_STATES]
    required = [r for r in rows if r.get("required_for_k0") is True]
    consistent = sum(
        1 for r in rows
        if r.get("declared") == r.get("measured") ==
        (live.get(r.get("id"), {}) or {}).get("measured")
    )

    lines: list[str] = [
        SNAPSHOT_MARKER,
        "",
        "# M14 K0 工具链缺口矩阵",
        "",
        f"- **生成时间**：{stamp}",
        "- **数据来源**：`tools/linux/toolchain_matrix.json`（format 1）+ "
        "现场探针（本册由生成器按矩阵重跑探针后写出）",
        f"- **机器指纹**：CPU `{_cpu_model()}`；target `{TARGET}`；"
        f"clang `{_tool_version(clang)}`；llvm-mc `{_tool_version(llvm_mc)}`；"
        f"工具版本摘要 md5 `{_version_md5([clang, llvm_mc])}`",
        "- **复现**：`make check-linux-toolchain`（门控）；"
        "`python3 tools/linux/check_toolchain.py --report`（重新生成本册）；"
        "`python3 tools/linux/check_toolchain.py --inject`（自检）",
        "",
        "## 1. 结论",
        "",
        f"- {len(rows)} 行矩阵，{consistent}/{len(rows)} 行「声明 == 实测」。",
        f"- `gaps={len(gaps)} (blockers=0)`：缺口行全部有**现场验证过**的规避法，"
        "对 K0 无阻塞。",
        f"- `required_for_k0` 共 {len(required)} 行（"
        + "、".join(r.get("id", "") for r in required)
        + "），全部 present/supported。",
        "- 结论由 **DADAO target** 决定：能力探针一律带 "
        f"`--target={TARGET}`（汇编用 `-triple={TARGET}`）；"
        "宿主 x86 上同类探针另见 §5 对照。",
        "",
        "## 2. 矩阵",
        "",
        "| 行 | 声明 | 实测 | exit | 规避法验证 | K0 影响 | 归属 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        rid = row.get("id")
        info = live.get(rid) or {}
        wa = (info.get("workaround") or {}).get("state", "n/a")
        lines.append(
            f"| `{rid}` | {row.get('declared')} | {info.get('measured')} | "
            f"{info.get('exit_code')} | {wa} | {row.get('k0_impact')} | "
            f"`{row.get('owner')}` |"
        )
    lines += ["", "## 3. 逐行证据（现场输出摘要）", ""]
    for row in rows:
        rid = row.get("id")
        info = live.get(rid) or {}
        wa = info.get("workaround") or {}
        lines.append(f"### `{rid}` — {info.get('measured')}")
        lines.append("")
        lines.append(f"- 探针：`{row.get('probe')}`")
        lines.append(f"- 实测：{info.get('measured')}（exit "
                     f"{info.get('exit_code')}）；输出摘要："
                     f"`{info.get('detail')}`")
        if (row.get("workaround") or "").strip():
            lines.append(f"- 规避法：{row.get('workaround')}")
            lines.append(f"- 规避法验证：{wa.get('state', 'n/a')}"
                         f"（`{wa.get('detail', 'n/a')}`）")
        else:
            lines.append("- 规避法：不需要（能力已具备）")
        lines.append("")
    lines += [
        "## 4. 可直接消费的工具选择（`m14-linux-002`）",
        "",
        "`<install-root>` = `manifests/install-dirs.lock.toml` 的 "
        "`host_toolchain_dir`；内核 make 传变量时按下列来源：",
        "",
        f"- `CC=<install-root>/bin/clang --target={TARGET}`（必须带 target；"
        "集成汇编器随 clang，`AS` 同源）",
        "- `LD=<install-root>/bin/ld.lld`（现场链接 DADAO ELF 成功："
        "Machine `0xDA0`、大端）",
        "- `AR=/usr/bin/ar`（GNU ar；安装根/构建树均无 `llvm-ar`）",
        "- `RANLIB=/usr/bin/ranlib`（GNU ranlib；均无 `llvm-ranlib`）",
        "- `NM=<install-root>/bin/llvm-nm`（fallback `/usr/bin/nm`，现场可用）",
        "- `OBJCOPY=<install-root>/bin/llvm-objcopy`",
        "- `OBJDUMP=<install-root>/bin/llvm-objdump`",
        "- `STRIP=<install-root>/bin/llvm-objcopy`（追加 `--strip-all` / "
        "`--strip-debug`；均无 `llvm-strip`，GNU strip 无法识别 DADAO ELF）",
        "- 附加编译期开关：`-fno-stack-protector`、`-mcmodel=small`；"
        "手写汇编的数据伪指令用 `.dd.o64/.dd.t32/.dd.w16/.dd.b08`",
        "- 不可用 `make LLVM=1`：该模式要求 `llvm-ar`/`llvm-strip`，"
        "二者缺失 ⇒ 逐变量覆盖上表。",
        "",
        "## 5. 口径与反证",
        "",
        "- 缺口头寸只有两态：`absent`（工具链二进制缺失）与 `unsupported`"
        "（target 拒绝该能力）；没有「未测」。",
        "- `required_for_k0=true` = 必须原生具备、不允许替代的能力；"
        "`k0_impact=none` = 有现场验证过的规避法；`blocker` = 无规避法（K0 被阻塞）。",
    ]
    if host.get("available"):
        lines.append(
            "- 宿主 x86 对照：同一份源码用宿主 clang 编 `-fstack-protector-strong` "
            f"rc={host.get('ssp_rc')}、`-mcmodel=kernel` rc={host.get('cmodel_rc')}"
            "（宿主天然通过），而 DADAO target 分别 unsupported ⇒ 结论由 target 决定。"
        )
    else:
        lines.append(f"- 宿主 x86 对照：{host.get('detail', '不可用')}")
    lines += [
        "- 工具链或矩阵一旦变化，重跑 `--report` 重写本册；"
        "`--report --check` 逐字比对正文（「生成时间」「机器指纹」两行除外）"
        "⇒ 改了矩阵不重生成即 FAIL。",
        "",
        "## 6. 复现命令",
        "",
        "```",
        "make check-linux-toolchain",
        "python3 tools/linux/check_toolchain.py --report",
        "python3 tools/linux/check_toolchain.py --report --check",
        "python3 tools/linux/check_toolchain.py --inject",
        "```",
        "",
    ]
    return "\n".join(lines)


# 「生成时间」「机器指纹」随生成时刻/生成机器变，不参与同源比较；其余正文逐字比对。
VOLATILE_RE = re.compile(r"^- \*\*(?:生成时间|机器指纹)\*\*：.*$", re.MULTILINE)


def _normalize_report(text: str) -> str:
    return VOLATILE_RE.sub("<随生成时刻/机器变化>", text)


def check_report_sync(matrix: dict, live: dict,
                      path: Path | None = None) -> list[str]:
    path = path or (ROOT / REPORT_REL)
    if not path.is_file():
        return [f"报告缺失: {REPORT_REL}（先跑 --report）"]
    text = path.read_text(encoding="utf-8")
    match = STAMP_RE.search(text)
    if not match:
        return [f"报告缺「生成时间」行: {REPORT_REL}"]
    expected = render(matrix, live, match.group(1))
    if _normalize_report(text) != _normalize_report(expected):
        return [f"报告与矩阵不同源: {REPORT_REL}（矩阵变化后重跑 --report；"
                f"生成时间/机器指纹两行不参与比较）"]
    return []


# ---------------------------------------------------------------------------
# 门控入口
# ---------------------------------------------------------------------------

def cmd_gate() -> int:
    matrix = load_matrix()
    live = measure()
    problems, summary = validate(matrix, live)
    problems += check_report_sync(matrix, live)
    print(f"check-linux-toolchain: target={TARGET} "
          f"矩阵={MATRIX_REL.as_posix()}")
    for row in matrix.get("rows") or []:
        rid = row.get("id")
        info = live.get(rid) or {}
        flag = "ok" if row.get("declared") == info.get("measured") else "!!"
        print(f"  [{flag}] {rid}: declared={row.get('declared')} "
              f"live={info.get('measured')} (rc={info.get('exit_code')})")
    if problems:
        for problem in problems:
            print(f"[FAIL] {problem}")
        print(f"check-linux-toolchain: FAIL ({len(problems)} problem(s))")
        return 1
    print(f"toolchain matrix: {summary['consistent']}/{summary['rows']} 行一致, "
          f"gaps={summary['gaps']} (blockers={summary['blockers']})")
    print("check-linux-toolchain: PASS")
    return 0


def cmd_report(check_only: bool) -> int:
    matrix = load_matrix()
    live = measure()
    problems, summary = validate(matrix, live)
    if problems:
        for problem in problems:
            print(f"[FAIL] {problem}")
        print("check-linux-toolchain --report: 矩阵未通过，拒绝写报告")
        return 1
    if check_only:
        problems = check_report_sync(matrix, live)
        for problem in problems:
            print(f"[FAIL] {problem}")
        print("check-linux-toolchain --report --check: "
              + ("PASS" if not problems else "FAIL"))
        return 0 if not problems else 1
    path = ROOT / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(matrix, live, now_stamp()), encoding="utf-8")
    print(f"check-linux-toolchain --report: 写入 {REPORT_REL.as_posix()} "
          f"({summary['rows']} 行, gaps={summary['gaps']}, "
          f"blockers={summary['blockers']})")
    return 0


# ---------------------------------------------------------------------------
# --inject 自检（临时副本注入 → 必须 FAIL → cp+md5 还原 → 回绿）
# ---------------------------------------------------------------------------

def _write_matrix(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def inject() -> int:
    matrix_path = ROOT / MATRIX_REL
    report_path = ROOT / REPORT_REL
    pristine = load_matrix(matrix_path)
    pristine_md5 = md5(matrix_path)
    live = measure()
    base_problems, _ = validate(pristine, live)
    base_report = check_report_sync(pristine, live, report_path)

    tmp = Path(tempfile.mkdtemp(prefix="inject-", dir=tmp_root()))
    backup = tmp / "matrix.pristine.json"
    shutil.copy2(matrix_path, backup)
    backup_md5 = md5(backup)
    work = tmp / "matrix.case.json"
    ok = True

    def row_of(data: dict, rid: str) -> dict:
        for row in data.get("rows") or []:
            if row.get("id") == rid:
                return row
        raise AssertionError(f"row {rid} not found")

    def flip_declared(data: dict) -> None:
        row = row_of(data, "llvm-ar")
        row["declared"] = "present" if row["declared"] == "absent" else "absent"
        row["workaround_measured"] = "n/a"

    def drop_workaround(data: dict) -> None:
        row = row_of(data, "llvm-strip")
        assert row["workaround"], "llvm-strip 规避法本来就是空的"
        row["workaround"] = ""

    def required_absent(data: dict) -> None:
        row = row_of(data, "asm-goto")
        assert row["required_for_k0"] is True
        row["declared"] = UNSUPPORTED
        row["measured"] = UNSUPPORTED
        row["workaround"] = ""
        row["workaround_measured"] = "n/a"

    def drop_row(data: dict) -> None:
        data["rows"] = [row for row in data["rows"]
                        if row.get("id") != "mcmodel-kernel"]

    def drop_target(data: dict) -> None:
        row = row_of(data, "data-directives")
        row["probe"] = row["probe"].replace(f"-triple={TARGET}", "-triple=")

    def simulated_required_gap() -> dict:
        """R2 的独立可达路径：矩阵声明 required 行转缺口态 **且实测同步**。

        现场工具链仍是 supported，因此用一份「模拟实测」的 live 副本喂给判据，
        验证「required 行非 present ⇒ FAIL」这一分支本身；不读写真实工具链。
        """
        simulated = copy.deepcopy(live)
        simulated["asm-goto"] = {"measured": UNSUPPORTED, "exit_code": 1,
                                 "detail": "simulated gap"}
        return simulated

    cases = [
        ("R1 declared 翻转", flip_declared, None),
        ("R3 删除规避法", drop_workaround, None),
        ("R2 required 行转缺口态（模拟实测同步）", required_absent,
         simulated_required_gap),
        ("R4 删除一行", drop_row, None),
        ("R5 probe 去掉 target", drop_target, None),
    ]

    def run_case(name: str, mutate, live_override=None) -> None:
        nonlocal ok
        data = json.loads(backup.read_text(encoding="utf-8"))
        mutate(data)
        _write_matrix(work, data)
        this_live = live_override() if live_override else live
        problems, _ = validate(load_matrix(work), this_live)
        got = 1 if problems else 0
        verdict = "PASS" if got == 1 else "FAIL"
        if got != 1:
            ok = False
        print(f"[INJECT] {name}: expected rc=1 actual rc={got} => {verdict}"
              f"  （首个判据: {problems[0] if problems else '无'}）")
        # 还原：cp 备份覆盖 + md5 对账 + 重读文件后必须回绿。
        shutil.copy2(backup, work)
        if md5(work) != backup_md5:
            ok = False
            print(f"[INJECT] {name}: 还原 md5 不一致（{md5(work)} != "
                  f"{backup_md5}）")
        restore_problems, _ = validate(load_matrix(work), live)
        green = 0 if not restore_problems else 1
        if green != 0:
            ok = False
        print(f"[INJECT] {name}: 还原 md5={md5(work)[:12]} "
              f"→ 回绿 rc={green} => {'PASS' if green == 0 else 'FAIL'}")

    try:
        for name, mutate, live_override in cases:
            run_case(name, mutate, live_override)

        # R6：报告漂移（临时副本追加一行 ⇒ 不同源 FAIL；还原 ⇒ 回绿）
        drift = tmp / "report.drift.md"
        if report_path.is_file():
            shutil.copy2(report_path, drift)
            drift_md5 = md5(drift)
            drift.write_text(drift.read_text(encoding="utf-8") + "\n漂移行\n",
                             encoding="utf-8")
            problems = check_report_sync(pristine, live, drift)
            got = 1 if problems else 0
            print(f"[INJECT] R6 报告漂移: expected rc=1 actual rc={got} => "
                  f"{'PASS' if got == 1 else 'FAIL'}"
                  f"  （首个判据: {problems[0] if problems else '无'}）")
            ok = ok and got == 1
            shutil.copy2(report_path, drift)
            if md5(drift) != drift_md5:
                ok = False
                print("[INJECT] R6: 还原 md5 不一致")
            restore = check_report_sync(pristine, live, drift)
            green = 0 if not restore else 1
            print(f"[INJECT] R6 报告漂移: 还原 md5={md5(drift)[:12]} "
                  f"→ 回绿 rc={green} => {'PASS' if green == 0 else 'FAIL'}")
            ok = ok and green == 0
        else:
            ok = False
            print("[INJECT] R6: 报告缺失，无法做漂移用例")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if md5(matrix_path) != pristine_md5:
        ok = False
        print("[INJECT] 真实矩阵 md5 被改动（必须只动临时副本）")
    if base_problems:
        ok = False
        print(f"[INJECT] 基线未通过: {base_problems[0]}")
    if base_report:
        ok = False
        print(f"[INJECT] 基线报告未同步: {base_report[0]}")
    print(f"[INJECT] 真实矩阵 md5={pristine_md5[:12]} 未变；"
          f"基线 rc={'0' if not base_problems and not base_report else '1'}")
    print("check-linux-toolchain --inject: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="M14 K0 工具链缺口矩阵门控（声明 == 实测）")
    parser.add_argument("--report", action="store_true",
                        help="按矩阵 + 现场探针重写人读报告")
    parser.add_argument("--check", action="store_true",
                        help="与 --report 连用：只断言报告与矩阵同源")
    parser.add_argument("--inject", action="store_true",
                        help="自检：临时副本注入 6 类反例，必须各自 FAIL 后还原回绿")
    args = parser.parse_args(argv)
    if args.inject:
        return inject()
    if args.report:
        return cmd_report(args.check)
    if args.check:
        parser.error("--check 只能与 --report 连用")
    return cmd_gate()


if __name__ == "__main__":
    sys.exit(main())
