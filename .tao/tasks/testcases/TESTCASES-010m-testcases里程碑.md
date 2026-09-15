# TESTCASES-010m: testcases 里程碑

**模块**：testcases
**项目里程碑**：M1
**状态**：待开始
**目标**：DADAO-v5 的独立测试向量层完成——M1 scope（`contracts/opcodes.yaml` 中 `excluded_m1 != true`，178 条）内每条指令身份 `(insn, format)` 均有 ≥1 条 active 向量，5 类向量（encoding/legality/semantic/boundary/overlap）齐备，期望值全部独立派生自 `spec/`、`.tao/knowledge/contract-isa.md` 与 `.tao/knowledge/adr-0004-test-machine.md`；`tools/testcases/validate_vectors.py` 的 schema + 覆盖率 + `encoding.word` mask/value 校验全部接入 `make check` 并通过；语义向量内存地址位于 ADR-0004 RAM 区、control-flow/load 的 deferred 测试已重设计或显式登记
**关联任务**：`TESTCASES-002t`、`TESTCASES-003t`、`TESTCASES-004t`、`TESTCASES-005t`、`TESTCASES-006t`、`TESTCASES-007t`、`TESTCASES-008t`、`TESTCASES-009t`

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：
  - `tests/vectors/schema.md`、`tests/vectors/inventory.md`、`tests/vectors/README.md`
  - `tests/vectors/isa/*.yaml`（M1 scope 全量向量，含 encoding/legality/semantic/boundary/overlap）
  - `tools/testcases/validate_vectors.py`
  - `Makefile`（`check` 含 `validate-vectors`）
- `python3 tools/testcases/validate_vectors.py` 零错误且覆盖率输出为 M1 scope 全覆盖（178/178）
- `make check` PASS
- **覆盖率主键与 scope 自洽**：validator 以 `(insn, format)` 为身份、以 `excluded_m1` 为 scope 判据；M1 内的 RA 存取/块赋值（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`/`ra2rd`/`rd2ra`）与 `swym`/`illi`/`fence` 均被计入
- **测试机语义自洽**：`expected_fault` 可表达 ADR-0004 D5.8 的 `UNMAPPED`（`0x87`）；`ret` 冷 RA 的期望为 `RASUF`（非 ILLI）；相对控制流立即数用 `imm=1`（`rb0`=当前指令地址，ADR-0004 D6.5）
- **跨模块影响已处置**（见 `AGENTS.md`「模块里程碑与跨模块交互」）：
  - 向量是 `llvm`（lit 字节 oracle，`LLVM-012t`）与 `qemu`（harness `QEMU-014t`~`019t`）的公共输入；本里程碑达成前须确认无待处置的上游接口变更（`opcodes.yaml`/`legality_rules.yaml`/ADR-0004 冻结）
  - `integ`（`INTEG-002t`/`INTEG-003t`）消费向量做 E2E；若向量 schema 或故障语义在本模块内变更，须同步 `integ` 任务书
  - 若 `spec`/`qemu` 模块在本模块执行期间产生合约/接口变更（如 fault 码、地址图），本里程碑须后移或增加交互任务
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）
