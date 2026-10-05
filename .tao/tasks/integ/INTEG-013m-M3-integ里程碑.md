# INTEG-013m: M3 integ 里程碑

**模块**：integ
**项目里程碑**：M3
**状态**：里程碑
**目标**：M3 项目门槛达成——`make test-codegen` 全绿：标量整数/指针函数经 `llc → .s → llvm-mc → obj → flat binary → qemu-system-dadao` 端到端执行，≥1 算术/访存/分支/调用函数结果正确（含 **`ptr−ptr` 指针差**，执行依赖 `QEMU-040t` 的 `sub.o` trans）。
**关联任务**：`INTEG-012t`（1 个）；**跨模块前置**：`QEMU-040t`（`sub.o` trans，须已 `已验证`）

## 核验
- 关联任务是否均已 `已验证`；跨模块前置 `QEMU-040t` 已 `已验证`
- 产出是否存在：`tests/scripts/codegen_crt0.s`、`tools/integ/run_codegen_e2e.py`、`Makefile::test-codegen`、`.work/log/integ/INTEG-012t-*.log`
- `make test-codegen` 退出 0 且四类函数端到端通过（含大端窄访存 C13、指针算术 C14、**`ptr−ptr`（`sub.o`）** 各 ≥1）；反例门控（注入→FAIL→还原→回绿）真实输出在案
- 不回归 `make check-lit`；`make check-no-residue` 干净
- 跨模块影响：`LLVM-042m`、`TESTCASES-027m` 均已达成；新增指令编码 (`SPEC-100t`) 与三条既有 RB 算术指令改名/改编码 (`SPEC-101t`) 与 QEMU (`QEMU-040t` + `SPEC-101t` 的 QEMU 部分) 一致；无未处置项

## 核验记录（主会话 2026-10-05）

- 关联任务 `INTEG-012t`：`**状态**：已验证`；跨模块前置 `QEMU-040t`：`已验证`。
- 产出存在：`tests/scripts/codegen_crt0.s`、`tools/integ/run_codegen_e2e.py`、`Makefile::test-codegen`、`.work/log/integ/INTEG-012t-*.log`。
- `make test-codegen` → **EXIT=0**（`Results: 15/15 passed, 0 failed`）；四类 + 大端窄访存 + `add.o` base+offset + `cmp.uo` dbb + `ptr−ptr`（`sub.o_orrr_dbb`）各 ≥1；反例门控（注入→FAIL→还原→回绿）在案。
- `make check-lit` → **EXIT=0**（34/34）；`make check-no-residue` → **EXIT=0**。
- 跨模块：`LLVM-042m`、`TESTCASES-027m` 均达成；新指令编码（`SPEC-100t`）与三条既有 RB 算术指令改名/改编码（`SPEC-101t`）与 QEMU（`QEMU-040t` + `SPEC-101t` QEMU 部分）一致；**无未处置项**。
- **结论：置 `里程碑`。**
