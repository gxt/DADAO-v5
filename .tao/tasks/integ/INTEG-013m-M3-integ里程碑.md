# INTEG-013m: M3 integ 里程碑

**模块**：integ
**项目里程碑**：M3
**状态**：待开始
**目标**：M3 项目门槛达成——`make test-codegen` 全绿：标量整数/指针函数经 `llc → .s → llvm-mc → obj → flat binary → qemu-system-dadao` 端到端执行，≥1 算术/访存/分支/调用函数结果正确。
**关联任务**：`INTEG-012t`（1 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tests/scripts/codegen_crt0.s`、`tools/integ/run_codegen_e2e.py`、`Makefile::test-codegen`、`.work/log/integ/INTEG-012t-*.log`
- `make test-codegen` 退出 0 且四类函数端到端通过（含大端窄访存 C13、指针算术 C14 各 ≥1）；反例门控（注入→FAIL→还原→回绿）真实输出在案
- 不回归 `make check-lit`；`make check-no-residue` 干净
- 跨模块影响：`LLVM-042m`、`TESTCASES-027m` 均已达成；无未处置项

## 核验记录
（核验时由主会话/架构师填写：命令原样 + 退出码）
