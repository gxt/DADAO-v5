# TESTSUITE-010m: testsuite 里程碑

**模块**：testsuite
**项目里程碑**：M1
**状态**：待开始
**目标**：DADAO-v5 的独立测试向量层完成——M1 scope 内每条指令身份（`insn`）均有 ≥1 条 active 向量，5 类向量（encoding/legality/semantic/boundary/overlap）齐备，期望值全部独立派生自 `spec/` 与 `.tao/knowledge/contract-isa.md`；`verif/validate_vectors.py` 的 schema + 覆盖率 + `encoding.word` mask/value 校验全部接入 `make check` 并通过；语义向量内存地址位于 RAM、control-flow/load 的 deferred 测试已重设计或显式登记
**关联任务**：`TESTSUITE-002t`、`TESTSUITE-003t`、`TESTSUITE-004t`、`TESTSUITE-005t`、`TESTSUITE-006t`、`TESTSUITE-007t`、`TESTSUITE-008t`、`TESTSUITE-009t`

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：
  - `tests/vectors/schema.md`、`tests/vectors/inventory.md`、`tests/vectors/README.md`
  - `tests/vectors/isa/*.yaml`（M1 scope 全量向量，含 encoding/legality/semantic/boundary/overlap）
  - `verif/validate_vectors.py`
  - `Makefile`（`check` 含 `validate-vectors`）
- `python3 verif/validate_vectors.py` 零错误且覆盖率输出为 M1 scope 全覆盖
- `make check` PASS
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）
