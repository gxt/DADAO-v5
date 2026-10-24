# INFRA-105t: `apply_series.py` 支持 `patchless` 组件（`ISS-224`+`ISS-231` 合并）

**模块**：infra
**项目里程碑**：M9（用户 2026-10-24 裁定「M9 内做」）
**依赖**：无
**状态**：待开始

## 立项来源

`ISS-224` 与 `ISS-231` 是**同一条缺陷**（`ISS-231` 为 P2 主条，`ISS-224` 为较早登记）：`tools/infra/apply_series.py` 对 `patchless` 组件（`manifests/components.lock.toml` 中 `chipyard`/`linux`/`llvm-test-suite`/`libc-test`）报 `KeyError: 'patch_dir'`，`make apply-series` rc=2。

## 目标

1. `apply_series.py` 识别 `patchless` 组件：**跳过**并给出明确日志（`component=<name>: patchless, skip`），不得静默、不得 rc≠0。
2. `make apply-series` 在含 `patchless` 组件的清单上 rc=0。
3. 合并 `ISS-224` 到 `ISS-231`（或反之），保留一条并标 `merged`。

## 验收

1. `make apply-series` rc=0（全清单）；日志含每个 `patchless` 组件的 skip 行（贴真实输出）。
2. 有补丁组件的行为**不变**（应用/回退各 1 次对比）。
3. **可达 FAIL**：把 `patchless` 处理去掉 ⇒ `KeyError` 复现、rc=2（贴输出）。
4. `make check`(L1) rc=0；证据 `.work/evidence/<任务ID>/run.sh`。

## 约束

- 只改 `tools/infra/apply_series.py`（必要时 `Makefile`）；不 commit/push；临时目录 `/tmp/opencode/INFRA-105t/`。
