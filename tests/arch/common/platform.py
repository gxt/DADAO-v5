#!/usr/bin/env python3
"""`tests/arch/common/platform.py` — arch 载体适配接口（qemu / gem5 / chipyard）。

三个平台是同一 arch scope 的三种**承载**（`tests/arch/PLAN.md §1/§3`），不是三个
scope。本文件只定义统一入口与 fail-closed 约定：

  * `qemu`：已实现。`kind: driver` 调 scope 内驱动（`--only/--qemu/--work-dir/
    --signature-out`），`kind: asm` 转调既有 `tools/testcases/arch/run_m5_e2e.py`
    （迁移期保持门控不变）。
  * `gem5` / `chipyard`：**骨架，未实现**。Vast 载体落地前（`m16-gem5-020` /
    `m16-chipyard-016` 之后）一律抛 `PlatformError`；调用方必须记 SKIP 并以非零
    退出，禁止静默降级为「其余平台通过」。

产物：每 case × 平台一份 `run.json`（进程命令、rc、日志路径、签名流路径）；
有签名流期望的 case 另有一份 `signature.bin`。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

BACKENDS = ("qemu", "gem5", "chipyard")

# fail-closed 开关：未实现的后端不得假绿。`--self-test` 会探测这两个开关，
# 若被改成 True 而实际没有载体，自检必须失败（证据脚本的注入点）。
GEM5_IMPLEMENTED = False
CHIPYARD_IMPLEMENTED = False


class PlatformError(RuntimeError):
    """后端不可用/未实现；调用方据此记 SKIP 并非零退出。"""


def implemented(platform: str) -> bool:
    if platform == "qemu":
        return True
    if platform == "gem5":
        return GEM5_IMPLEMENTED
    if platform == "chipyard":
        return CHIPYARD_IMPLEMENTED
    raise PlatformError("未知载体 %r（允许 %s）" % (platform, list(BACKENDS)))


def ensure_implemented(platform: str) -> None:
    """未实现的后端在此**显式失败**；不返回、不回退。"""
    if platform == "qemu":
        return
    if platform == "gem5":
        if not GEM5_IMPLEMENTED:
            raise PlatformError(
                "gem5: Vast arch 载体未实现（缺 Vast FS 用例与 cfx 探针；"
                "m16-gem5-020 之后接入）。不得静默跳过或降级。")
        return
    if platform == "chipyard":
        if not CHIPYARD_IMPLEMENTED:
            raise PlatformError(
                "chipyard: Vast arch 载体未实现（RTL 侧缺 cfx0/2/15/32/34，"
                "cfx5 只有阵列；m16-chipyard-016 之后接入）。不得静默跳过或降级。")
        return
    raise PlatformError("未知载体 %r（允许 %s）" % (platform, list(BACKENDS)))


def self_test_fail_closed() -> list:
    """`--self-test` 用：未实现的后端必须以 `PlatformError` 拒绝。

    返回问题列表；空 = 两个未实现后端都 fail-closed。
    """
    problems = []
    for platform in ("gem5", "chipyard"):
        try:
            run(platform, [], None)
        except PlatformError:
            continue
        except Exception as exc:  # 任何静默成功/其它异常都不是 fail-closed
            problems.append("%s: 探针得到非 PlatformError 异常 %s: %s"
                            % (platform, type(exc).__name__, exc))
        else:
            problems.append("%s: 未实现后端未 fail-closed（假绿）" % platform)
    return problems


def run(platform: str, cases, ctx):
    """跑一个平台的全部 case；返回结果列表。未实现后端抛 `PlatformError`。"""
    ensure_implemented(platform)
    if not cases:
        return []
    if platform == "qemu":
        return [_run_qemu(case, ctx) for case in cases]
    if platform == "gem5":
        # 骨架：接入 Vast FS 载体前不产出任何结果；run_arch 会把「0 结果」判红。
        return []
    if platform == "chipyard":
        return []
    raise PlatformError("未知载体 %r" % platform)


# ---------------------------------------------------------------------------
# qemu 后端
# ---------------------------------------------------------------------------
def _carrier_path(ctx, case) -> Path:
    """`tests/arch.yaml` 的 `file` 相对 `tests/`：返回仓库内绝对路径。"""
    return Path(ctx.repo_root) / "tests" / case["file"]


def _expected_yaml(ctx, case) -> Path:
    parts = PurePosixPath(case["file"]).parts
    cfx_dir = parts[1] if len(parts) > 1 else ""
    return Path(ctx.arch_root) / cfx_dir / "expected.yaml"


def _run_qemu(case, ctx) -> dict:
    if case.get("kind", "asm") == "driver":
        return _run_qemu_driver(case, ctx)
    return _run_qemu_asm(case, ctx)


def _run_qemu_driver(case, ctx) -> dict:
    case_dir = Path(ctx.work) / case["id"] / "qemu"
    driver_dir = case_dir / "driver"
    case_dir.mkdir(parents=True, exist_ok=True)
    signature = case_dir / "signature.bin"
    cmd = [sys.executable, str(_carrier_path(ctx, case)),
           "--only", case["id"], "--qemu", str(ctx.qemu),
           "--work-dir", str(driver_dir),
           "--signature-out", str(signature)]
    return _finish(case, ctx, case_dir, cmd, signature,
                   "driver: %s" % case["file"])


def _run_qemu_asm(case, ctx) -> dict:
    case_dir = Path(ctx.work) / case["id"] / "qemu"
    runner_dir = case_dir / "runner"
    case_dir.mkdir(parents=True, exist_ok=True)
    if not ctx.llvm_mc or not ctx.llvm_objcopy:
        raise PlatformError(
            "qemu asm 载体需要 llvm-mc/llvm-objcopy（--llvm-mc/--llvm-objcopy）")
    if not ctx.bootrom:
        raise PlatformError("qemu asm 载体需要 Vast step5 BootROM（--bootrom）")
    cfx_dir = _carrier_path(ctx, case).parent
    cmd = [sys.executable, str(ctx.m5_runner), "--only", PurePosixPath(
               case["file"]).stem,
           "--vectors-dir", str(cfx_dir),
           "--expected", str(cfx_dir / "expected.yaml"),
           "--work-dir", str(runner_dir),
           "--qemu", str(ctx.qemu),
           "--llvm-mc", str(ctx.llvm_mc),
           "--llvm-objcopy", str(ctx.llvm_objcopy),
           "--bootrom", str(ctx.bootrom)]
    signature = case_dir / "signature.bin"
    # asm 载体当前未登记签名流（umon 的判据是 exit code + console）；显式写
    # 0 槽空流，`run.json` 里记 signature_count=0，避免把 console 误当签名。
    signature.write_bytes(b"")
    return _finish(case, ctx, case_dir, cmd, signature,
                   "asm: %s" % case["file"], signature_count=0)


def _finish(case, ctx, case_dir, cmd, signature, note,
            signature_count=None) -> dict:
    log = case_dir / "run.log"
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=ctx.timeout,
                              stdin=subprocess.DEVNULL)
        rc, output = proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        rc, output = -2, exc.stdout or b""
    log.write_bytes(output)
    result = {
        "case": case["id"],
        "platform": "qemu",
        "kind": case.get("kind", "asm"),
        "carrier": note,
        "command": cmd,
        "rc": rc,
        "log": str(log),
        "signature": str(signature),
        "signature_count": signature_count,
        "verdict": "PASS" if rc == 0 else "FAIL",
        "reason": "" if rc == 0 else "载体 rc=%d（见 run.log）" % rc,
    }
    if signature_count is None:
        # driver：按 expected.yaml 的签名流期望解析并比对。
        from . import signature as arch_sig

        want = arch_sig.load_expected_signature(_expected_yaml(ctx, case),
                                                case["id"])
        if want is not None and rc == 0:
            result["signature_count"] = len(want)
            try:
                got = arch_sig.parse(signature.read_bytes(), len(want))
            except arch_sig.SignatureError as exc:
                result["verdict"] = "FAIL"
                result["reason"] = "签名流: %s" % exc
            else:
                problems = arch_sig.compare(got, want)
                if problems:
                    result["verdict"] = "FAIL"
                    result["reason"] = "签名流: " + "; ".join(problems)
                else:
                    result["signature_actual"] = got
    (case_dir / "run.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
