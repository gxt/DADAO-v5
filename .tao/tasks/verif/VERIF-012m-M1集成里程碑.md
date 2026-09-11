# VERIF-012m: M1 集成里程碑

**模块**：verif
**项目里程碑**：M1
**状态**：待开始
**目标**：verif 模块 M1 验证基础设施全部就位——QEMU 语义 harness 可对向量做独立差分验证，QFC/lit 字节/issue/trans/spec 引用检查工具可运行，MC↔QEMU 端到端冒烟打通，形成「向量 → QEMU 执行 → 结果比对」与「MC 汇编 → QEMU 执行 → 退出码」的集成闭环。
**关联任务**：`VERIF-002t`、`VERIF-003t`、`VERIF-004t`、`VERIF-005t`、`VERIF-006t`、`VERIF-007t`、`VERIF-008t`、`VERIF-009t`、`VERIF-010t`、`VERIF-011t`

## 核验

- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：
  - `verif/legality_rules.yaml`（`VERIF-002t`）
  - `tests/scripts/build_test_binary.py`、`tests/scripts/run_qemu_test.py`、`tests/scripts/gen_trampoline.py`、`tests/scripts/trampoline.bin`、`tests/scripts/README.md`（`VERIF-003t`~`VERIF-009t`）
  - `verif/check_qfc_coverage.py`、`verif/check_lit_bytes.py`（`VERIF-005t`）
  - `docs/issues.yaml`、`verif/check_issues.py`、`verif/check_qemu_trans.py`（`VERIF-007t`）
  - `tests/e2e/*.s`、`tests/lit/E2E/*.test`、`tests/lit/E2E/lit.cfg`（`VERIF-010t`）
  - `verif/check_spec_refs.py`（`VERIF-011t`）
- 集成验收：`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/` 0 failed；`llvm-lit tests/lit/E2E/` 全 PASS
- 项目里程碑联动：将 `knowledge/milestones.md` 中 M1 行的 `verif` 列更新为 `VERIF-012m`

（核验通过后，主会话将 `**状态**` 置为 `里程碑`）
