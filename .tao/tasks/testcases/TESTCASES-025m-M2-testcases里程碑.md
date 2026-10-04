# TESTCASES-025m: M2 testcases 里程碑

**模块**：testcases
**项目里程碑**：M2
**状态**：里程碑
**目标**：独立测试向量层与生成器随 M2 的 spec/汇编格式变更对齐——新汇编语法与字节化、`id` 改名（`insn`→`mnemonic` 体系）、`st` 零号寄存器/RA/`ret rd0`/`mreg_range_overlap` 语义修正与向量重写、`spec_cite` 对齐；`validate_vectors` 152/152、data coverage gaps 0、`make check` 全绿。
**关联任务**：`TESTCASES-013t`、`TESTCASES-014t`、`TESTCASES-015t`、`TESTCASES-016t`、`TESTCASES-017t`、`TESTCASES-018t`、`TESTCASES-019t`、`TESTCASES-020t`、`TESTCASES-021t`、`TESTCASES-022t`、`TESTCASES-023t`（11 个）

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出是否存在：`tests/vectors/schema.md`、`tests/vectors/inventory.md`、`tests/vectors/isa/*.yaml`、`tools/testcases/generate_isa_vectors.py`、`tools/testcases/validate_vectors.py`
- `validate_vectors` 152/152、data coverage gaps 0；`make check` 全绿

## 核验记录（2026-10-04，architect 核验）

**关联任务**：`TESTCASES-013t`~`TESTCASES-023t`（11/11）全部 `已验证`（`019t` 经第 3 轮返工后、`020t` 推翻 M1 RA 向量期望值）。

**命令核验（真实输出，2026-10-04）**：
```
$ python3 tools/testcases/validate_vectors.py ; echo rc=$?
validate_vectors: 152/152 M1 identities covered OK (inventory sync OK; 15 data files, 694 cases; data coverage gaps: 0)
rc=0
```
（`make check` 成员；EXIT=0。）

**跨模块影响**：向量是 `llvm`（lit 字节 oracle）与 `qemu`（harness）的公共输入；M2 期间 schema/格式/语义变更已由 `LLVM-*`/`QEMU-*` 对应任务同步消费，`check-interface` 80/80、`check_qemu_trans` 227/227 通过 ⇒ 无未处置项。

**结论**：核验通过，置 `里程碑`。
