# TESTCASES-027m: M3 testcases 里程碑

**模块**：testcases
**项目里程碑**：M3
**状态**：待开始
**目标**：M3 CodeGen 独立测试向量就绪——四类（算术/访存/分支/调用）标量 IR 程序 + **`ptr−ptr` 指针差** 用例 + 独立推导的期望值 + validator。
**关联任务**：`TESTCASES-026t`（1 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tests/codegen/*.ll`、`tests/codegen/expected.yaml`（或等价）、`tools/testcases/validate_codegen_vectors.py`
- validator 退出 0 且四类覆盖齐全，且含**大端窄访存**（C13/`ADR-0018（C13）`）、**指针算术**（C14/`ADR-0018（C14）`）与 **`ptr−ptr` 指针差**（后端选出 `sub.o_orrr_dbb`，语义见 `SPEC-100t`/`adr-0012 D9`）各 ≥1；期望值独立推导证据存在（非来自 llc/QEMU）；反例门控真实输出留存
- 跨模块影响：向量入口约定与 `INTEG-012t` harness 对齐；`ptr−ptr` 期望值按 IR 语义（地址整数差）独立派生

## 核验记录
（核验时由主会话/架构师填写：命令原样 + 退出码）
