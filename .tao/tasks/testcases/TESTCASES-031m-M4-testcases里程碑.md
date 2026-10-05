# TESTCASES-031m: M4 testcases 里程碑

**模块**：testcases
**项目里程碑**：M4
**状态**：待开始
**目标**：M4 的测试向量层收口（`Process-05` TDD）——① **L1 MC 向量**（伪指令/指导符/选项/诊断/往返）与独立 oracle 落地（`TESTCASES-029t`）；② **L3 执行向量**（多 TU/多段/ELF 链路）与独立 oracle 落地（`TESTCASES-030t`）。向量期望值均**独立派生自 `spec/`/`contracts/`**（不从 `llc`/QEMU 反推），每条可对反例失败。按用户裁定（2026-10-06），向量+oracle 暂存、由实现任务/`INTEG-016t` 接入门控。
**关联任务**：`TESTCASES-029t`、`TESTCASES-030t`（2 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tests/lit/MC/Dadao-m4/`（L1 向量）+ `tools/testcases/validate_mc_vectors.py`；`tests/codegen-elf/`（L3 向量 + `expected.yaml` + README）+ `tools/testcases/validate_elf_vectors.py`
- 独立 oracle：脚本无 `subprocess`/`os.system`/`Popen` 与 `llc`/`qemu` 调用；期望值可由 `contracts/opcodes.yaml`/IR 语义独立重算
- 两 validator 的反例注入（改期望值/改 IR/少覆盖）→ 非零退出 → 还原回绿（真实输出留存 `.work/log/testcases/`）
- `make check`/`make check-dirs`/`check-no-residue` EXIT=0；M3 `make test-codegen`（15/15）不回归
- 覆盖矩阵：L1 五类；L3 多 TU/多段/跨 TU call/`ABS48` 各 ≥1

## 核验记录（主会话）
（核验命令、输出与退出码；结论）
