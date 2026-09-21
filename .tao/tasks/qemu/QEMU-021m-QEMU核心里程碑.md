# QEMU-021m: QEMU 核心里程碑

**模块**：qemu
**项目里程碑**：M1
**状态**：待开始
**目标**：DADAO-v5 的 QEMU 标量核心完成——`qemu-system-dadao` 在 MMU-off 裸机模式执行 M1 标量程序；RD 整数语义、RD load/store（含 MALIGN 精确异常）、控制流与 RB/RA 指令（含 RegRAS/MemRAS）按 `.tao/knowledge/contract-isa.md` 与 `contracts/opcodes.yaml` 独立 oracle 实现；**全部 M1 向量经 harness 执行且结果比对一致**（硬性要求）；`make build-qemu` 全绿。
**关联任务**：`QEMU-002t`、`QEMU-003t`、`QEMU-004t`、`QEMU-005t`、`QEMU-006t`、`QEMU-007t`、`QEMU-008t`、`QEMU-009t`、`QEMU-010t`、`QEMU-011t`、`QEMU-012t`、`QEMU-013t`、`QEMU-014t`、`QEMU-015t`、`QEMU-016t`、`QEMU-017t`、`QEMU-018t`、`QEMU-019t`、`QEMU-022t`

> **ADR-0010 D3 修订（2026-09-19）**：补丁清单更新为 0001–0007（合并后）；关联任务新增 `QEMU-020t`（harness dumper 改造）。**2026-09-21 更新**：新增 `0008`（TB 续接缺陷修复）与 `QEMU-022t`；`020t` 范围缩窄为 TB 安全分段 dumper。**2026-09-21 再更新**：`QEMU-020t` **已关闭**（交付物 #1 由 `015t` 落地；分段 dumper 因 `022t` 根治 TB 缺陷而不再必要），从关联任务移除。

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：
  - `.tao/knowledge/adr-0008-qemu-baseline.md`
  - `.tao/knowledge/adr-0009-qemu-harness-methodology.md`（`QEMU-014t` 交付）
  - `.tao/knowledge/adr-0010-qemu-task-restructure.md`（Accepted）
  - `manifests/components.lock.toml`（qemu `enabled = true` + 完整 commit）
  - `components/qemu/patches/0001-dadao-target-skeleton.patch`（`QEMU-003t`）
  - `components/qemu/patches/0002-dadao-decodetree.patch`（`QEMU-004t`）
  - `components/qemu/patches/0003-dadao-rd-arith.patch`（`QEMU-005t`）
  - `components/qemu/patches/0004-dadao-load-store.patch`（`QEMU-006t`，含 MALIGN + jump-rrii/br.nz，ADR-0010 D1/D3 合并）
  - `components/qemu/patches/0005-dadao-translate-split.patch`（`QEMU-007t`，纯重构，ADR-0010 D2）
  - `components/qemu/patches/0006-dadao-ctrl-flow.patch`（`QEMU-008t`，含 `QEMU-010t` ldm.o-rb 修订）
  - `components/qemu/patches/0007-dadao-ra-semantics.patch`（`QEMU-013t` 交付）
  - `components/qemu/patches/0008-dadao-tb-chain-fix.patch`（`QEMU-022t` 交付，TB 续接缺陷修复）
  - `components/qemu/patches/series`（含 0001–0008）
  - **注**：`QEMU-009t`（rela 验证）、`QEMU-011t`（div label 验证）、`QEMU-012t`（分支/call 验证）为**验证任务，不产出补丁**
  - `target/dadao/insn.decode`（apply 后）
  - `target/dadao/insn_trans/trans_*.c.inc`（10 个文件，`QEMU-007t` 拆分）
  - `tests/scripts/build_test_binary.py`、`tests/scripts/run_qemu_test.py`、`tests/scripts/gen_trampoline.py`、`tests/scripts/trampoline.bin`（`QEMU-014t` 产出）
  - `tools/qemu/check_qemu_trans.py`（`QEMU-019t` 产出）
- `make build-qemu` PASS；`qemu-system-dadao -M ?` 显示约定机器名
- **全部 M1 向量经 harness 执行且结果比对一致**（硬性要求）：`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/*.yaml` 全量 PASS（0 FAIL，deferred 允许但须记录）
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）