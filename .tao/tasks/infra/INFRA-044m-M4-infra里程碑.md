# INFRA-044m: M4 infra 里程碑

**模块**：infra
**项目里程碑**：M4
**状态**：待开始
**目标**：构建基础设施支持 M4——① 新增构建入口产出 `ld.lld`（`.work/build/llvm/bin/ld.lld`），且 `build-mc`/`build-qemu` 既有目标不回归（为 `LLVM-056t`（DADAO LLD target）与 `INTEG-016t`（`make test-elf`）提供链接器产物）；② `tests/` 组件先行重排（`tests/llvm/{lit/{MC,CodeGen,tools}/DADAO, codegen}` + `tests/qemu/` + `tests/e2e/lit/`，对齐上游 `llvm/test/{MC,CodeGen,tools}`），迁移后 `make check`/`check-lit`/`test-codegen` 全绿、无残留。
**关联任务**：`INFRA-043t`、`INFRA-045t`（2 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`Makefile` 新目标、`.work/build/llvm/bin/ld.lld`（构建证据 `.work/log/infra/INFRA-043t-*.log`）；`tests/llvm/lit/MC/DADAO/`、`tests/llvm/lit/CodeGen/DADAO/`、`tests/llvm/lit/tools/DADAO/`、`tests/llvm/codegen/`、`tests/qemu/`、`tests/e2e/lit/`（重排后）
- `ld.lld --version` EXIT=0
- `build-mc` 不回归（`llc`/`llvm-mc`/`llvm-objcopy`/`llvm-readobj` 仍可用）
- `make check`/`make check-lit`（通过数与重排前逐项相等）/`make test-codegen`（15/15）EXIT=0；旧路径 `tests/lit/MC/Dadao`/`tests/lit/E2E`/`tests/codegen` 无残留
- `make check-no-residue` 干净；`make check` 全绿

## 核验记录（主会话）
（核验命令、输出与退出码；结论）
