#!/usr/bin/env python3
"""`tests/arch/common/platform.py` — arch 载体适配接口（qemu / gem5 / chipyard）。

三个平台是同一 arch scope 的三种**承载**（`tests/arch/PLAN.md §1/§3`），不是三个
scope。本文件只定义统一入口与 fail-closed 约定：

  * `qemu`：已实现。`kind: driver` 调 scope 内驱动（`--only/--qemu/--work-dir/
    --signature-out`），`kind: asm` 转调既有 `tools/testcases/arch/run_m5_e2e.py`
    （迁移期保持门控不变）。
  * `gem5`：**已实现 driver 承载**（`m16-testcases-010`）。同一 scope 内驱动经
    `tools/testcases/parity/qemu_gem5_shim.py` 跑（`-machine kaiwu-vast`、
    `--profile vast`；shim 支持 `cache-model=on` → `--caches`，当前 ptw 载体不依赖
    cache）；`kind: asm` 仍未接，显式抛 `PlatformError`（不静默跳过）。
  * `chipyard`：**未实现**（RTL cfx4 由 `m16-chipyard-018` 接）。一律抛
    `PlatformError`；调用方必须记 SKIP 并以非零退出，禁止静默降级为「其余平台
    通过」。

产物：每 case × 平台一份 `run.json`（进程命令、rc、日志路径、签名流路径）；
有签名流期望的 case 另有一份 `signature.bin`。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

BACKENDS = ("qemu", "gem5", "chipyard")

# fail-closed 开关：未实现的后端不得假绿。`--self-test` 会探测这两个开关，
# 若被改成 True 而实际没有载体，自检必须失败（证据脚本的注入点）。
# gem5 的 driver 承载由 `m16-testcases-010` 接入（qemu_gem5_shim）；asm 载体仍未接，
# 由 `_run_gem5` 显式抛 PlatformError。RTL 由 `m16-chipyard-018` 接入。
GEM5_IMPLEMENTED = True
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
                "chipyard: Vast arch 载体未实现（RTL cfx4 PTW/TLB 由 "
                "m16-chipyard-018 接入；cfx5 只有阵列，由 m16-chipyard-016；"
                "cfx0/2/15/32/34 仍缺）。不得静默跳过或降级。")
        return
    raise PlatformError("未知载体 %r（允许 %s）" % (platform, list(BACKENDS)))


def self_test_fail_closed() -> list:
    """`--self-test` 用：后端接线与 fail-closed 探针。

    返回问题列表；空 = gem5 driver 承载已接、chipyard 仍以 `PlatformError` 拒绝。
    """
    problems = []
    if not implemented("gem5"):
        problems.append("gem5: GEM5_IMPLEMENTED=False，但 cfx4 driver 承载应由 "
                        "qemu_gem5_shim 提供（m16-testcases-010）")
    try:
        run("chipyard", [], None)
    except PlatformError:
        pass
    except Exception as exc:  # 任何静默成功/其它异常都不是 fail-closed
        problems.append("chipyard: 探针得到非 PlatformError 异常 %s: %s"
                        % (type(exc).__name__, exc))
    else:
        problems.append("chipyard: 未实现后端未 fail-closed（假绿）")
    return problems


def run(platform: str, cases, ctx):
    """跑一个平台的全部 case；返回结果列表。未实现后端抛 `PlatformError`。"""
    ensure_implemented(platform)
    if not cases:
        return []
    if platform == "qemu":
        return [_run_qemu(case, ctx) for case in cases]
    if platform == "gem5":
        _ensure_gem5_ready(ctx)
        return [_run_gem5(case, ctx) for case in cases]
    if platform == "chipyard":
        return []
    raise PlatformError("未知载体 %r" % platform)


def _ensure_gem5_ready(ctx) -> None:
    """gem5 承载前置（shim + gem5.opt + fs.py）；缺失时显式 fail-closed。"""
    for path, what in ((getattr(ctx, "gem5_shim", None), "qemu_gem5_shim.py"),
                       (getattr(ctx, "gem5", None), "gem5.opt"),
                       (getattr(ctx, "gem5_config", None), "configs/dadao/fs.py")):
        if path is None or not Path(path).is_file():
            raise PlatformError(
                "gem5: 缺件 %s = %r（driver 承载经 qemu_gem5_shim 跑；"
                "不得静默跳过或降级）" % (what, path))
    if not os.access(str(ctx.gem5), os.X_OK):
        raise PlatformError("gem5: gem5.opt 不可执行: %s" % ctx.gem5)


# ---------------------------------------------------------------------------
# 载体路径（qemu / gem5 共用）
# ---------------------------------------------------------------------------
def _carrier_path(ctx, case) -> Path:
    """`tests/arch.yaml` 的 `file` 相对 `tests/`：返回仓库内绝对路径。"""
    return Path(ctx.repo_root) / "tests" / case["file"]


def _expected_yaml(ctx, case) -> Path:
    # `common/` 下的跨 cfx 驱动由 `run_arch.load_index` 给出逻辑 cfx 目录
    # （`cfx_dir`）；缺省退回 `file` 的第二段（旧调用方）。
    cfx_dir = case.get("cfx_dir")
    if not cfx_dir:
        parts = PurePosixPath(case["file"]).parts
        cfx_dir = parts[1] if len(parts) > 1 else ""
    return Path(ctx.arch_root) / cfx_dir / "expected.yaml"


def _run_qemu(case, ctx) -> dict:
    if case.get("kind", "asm") == "driver":
        return _run_driver(case, ctx, "qemu", ctx.qemu)
    return _run_qemu_asm(case, ctx)


def _run_gem5(case, ctx) -> dict:
    """gem5 承载：同一 scope 内驱动经 qemu_gem5_shim（`-machine kaiwu-vast`）。"""
    if case.get("kind", "asm") != "driver":
        # 每个 cfx 的 gem5 asm 载体另行接入；这里显式失败，不静默漏跑。
        raise PlatformError(
            "gem5: kind=asm 载体未实现（cfx=%s case=%s）；driver 承载经 "
            "qemu_gem5_shim，asm 请另行接线。不得静默跳过或降级。"
            % (case.get("cfx"), case["id"]))
    return _run_driver(case, ctx, "gem5", ctx.gem5_shim,
                       _gem5_env(ctx, case["id"]))


def _gem5_env(ctx, case_id) -> dict:
    """shim 的环境（gem5.opt / fs.py / profile / 运行期目录）。"""
    return {
        "DADAO_TEST_PROFILE": "vast",
        "PARITY_GEM5": str(ctx.gem5),
        "PARITY_GEM5_CONFIG": str(ctx.gem5_config),
        "PARITY_GEM5_PROFILE": "vast",
        "PARITY_WORK_ROOT": str(Path(ctx.work) / case_id / "gem5" / "shim"),
    }


def _run_driver(case, ctx, platform, engine, extra_env=None) -> dict:
    """driver 型 case：调 scope 内驱动，产物与签名流按平台分目录。

    运行模式（m16-testcases-015）：只有**声明了多个允许模式**的 driver 才收
    `--mode`，这样既有单模式驱动（如 ptw 的 `check_tlb.py`）的命令行不变；
    单模式用例仍按 `hmon` 语义运行。

    环境型驱动（同一门槛：声明多模式）另收两件（m16-testcases-017）：
      * `--cfx-access <cfxha,...>`：`modes.yaml` 的 `cfx_access` 声明，驱动据此
        逐 cfx 传 `--defsym ENV_CFX_ACCESS_<cfxha>=1` 给环境做权限准备；
      * `--bootrom <path>`：本驱动用显式 BootROM（`run_arch --bootrom`），保证
        asm 与 driver 两条路径跑同一份固件。
    """
    case_dir = Path(ctx.work) / case["id"] / platform
    driver_dir = case_dir / "driver"
    case_dir.mkdir(parents=True, exist_ok=True)
    signature = case_dir / "signature.bin"
    cmd = [sys.executable, str(_carrier_path(ctx, case)),
           "--only", case["id"], "--qemu", str(engine),
           "--work-dir", str(driver_dir),
           "--signature-out", str(signature)]
    modes = case.get("modes") or ["hmon"]
    if len(modes) > 1:
        cmd += ["--mode", getattr(ctx, "mode", "hmon")]
        access = case.get("cfx_access") or []
        if access:
            cmd += ["--cfx-access", ",".join(str(c) for c in access)]
        bootrom = getattr(ctx, "bootrom", None)
        if bootrom:
            cmd += ["--bootrom", str(bootrom)]
        cache_model = getattr(ctx, "cache_model", None)
        if cache_model:
            cmd += ["--cache-model", str(cache_model)]
    return _finish(case, ctx, case_dir, cmd, signature,
                   "driver(%s): %s" % (platform, case["file"]),
                   platform=platform, extra_env=extra_env)


def _run_qemu_asm(case, ctx) -> dict:
    mode = getattr(ctx, "mode", "hmon")
    if mode != "hmon":
        raise PlatformError(
            "qemu: kind=asm 载体尚未接运行模式环境（--mode %s，case=%s）；"
            "只有 kind=driver 且声明多模式的用例支持 --mode。不得静默按 hmon 跑。"
            % (mode, case["id"]))
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
                   "asm: %s" % case["file"], signature_count=0,
                   platform="qemu")


def _finish(case, ctx, case_dir, cmd, signature, note,
            signature_count=None, platform="qemu", extra_env=None) -> dict:
    log = case_dir / "run.log"
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=ctx.timeout,
                              stdin=subprocess.DEVNULL, env=env)
        rc, output = proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        rc, output = -2, exc.stdout or b""
    log.write_bytes(output)
    result = {
        "case": case["id"],
        "platform": platform,
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
        if want is None:
            # 未接线的检查：显式写 0 槽空流，跨平台比较按「空流 == 空流」。
            if not signature.is_file():
                signature.write_bytes(b"")
            result["signature_count"] = 0
        elif rc == 0:
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
