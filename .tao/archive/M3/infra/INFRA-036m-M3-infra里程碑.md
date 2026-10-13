# INFRA-036m: M3 infra 里程碑

**模块**：infra
**项目里程碑**：M3
**状态**：里程碑
**目标**：LLVM 构建设施产出 `llc`（CodeGen 侧可构建、可执行），为 M3 CodeGen 提供构建入口。
**关联任务**：`INFRA-035t`（1 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`Makefile` 中 `llc` 构建目标 + 构建证据（`.work/log/infra/`）
- `make build-mc`（或 `make build-llc`）产出 `llc`；`llc --version` 含 dadao
- `make check-patch-tree` 通过（若触及补丁集）；`make check-no-residue` 干净

## 核验记录（主会话 2026-10-05）

- 关联任务 `INFRA-035t`：`**状态**：已验证`。
- 产出：`Makefile` 含 `llc` 构建入口（`build-mc` 工具列表）；`.work/build/llvm/bin/llc` 存在。
- `llc --version | grep -i dadao` → **EXIT=0**。
- `make check-patch-tree` → **EXIT=0**（`80 patches OK`）。
- `make check-no-residue` → **EXIT=0**。
- 追加：`INFRA-041t`（M3 收官 issue 清扫）亦已验证。
- **结论：置 `里程碑`。**
