# QEMU-020m: QEMU 核心里程碑

**模块**：qemu
**项目里程碑**：M1
**状态**：待开始
**目标**：DADAO-v5 的 QEMU 标量核心完成——`qemu-system-dadao` 在 MMU-off 裸机模式执行 M1 标量程序；RD 整数语义、RD load/store（含 MALIGN 精确异常）、控制流与 RB/RA 指令（含 RegRAS/MemRAS）按 `.tao/knowledge/contract-isa.md` 与 `contracts/opcodes.yaml` 独立 oracle 实现；**全部 M1 向量经 harness 执行且结果比对一致**（硬性要求）；`make build-qemu` 全绿。
**关联任务**：`QEMU-002t`、`QEMU-003t`、`QEMU-004t`、`QEMU-005t`、`QEMU-006t`、`QEMU-007t`、`QEMU-008t`、`QEMU-009t`、`QEMU-010t`、`QEMU-011t`、`QEMU-012t`、`QEMU-013t`、`QEMU-014t`、`QEMU-015t`、`QEMU-016t`、`QEMU-017t`、`QEMU-018t`、`QEMU-019t`

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：
  - `.tao/knowledge/adr-0008-qemu-baseline.md`
  - `.tao/knowledge/adr-0009-qemu-harness-methodology.md`（`QEMU-014t` 交付，Candidate）
  - `manifests/components.lock.toml`（qemu `enabled = true` + 完整 commit）
  - `components/qemu/patches/0001-dadao-target-skeleton.patch`
  - `components/qemu/patches/0002-dadao-decodetree.patch`
  - `components/qemu/patches/0003-dadao-rd-arith.patch`
  - `components/qemu/patches/0004-dadao-load-store.patch`（含 MALIGN/TEMP_EBB 修订）
  - `components/qemu/patches/0005-dadao-ctrl-flow.patch`（含 rela/ldm.o-rb 修订）
  - `components/qemu/patches/0006-dadao-div-label-fix.patch`
  - `components/qemu/patches/0007-dadao-branch-call-fix.patch`
  - `components/qemu/patches/0008-dadao-ra-semantics.patch`（`QEMU-013t` 交付）
  - `components/qemu/patches/series`（含 0001–0008）
  - `target/dadao/insn.decode`（apply 后）
  - `tests/scripts/build_test_binary.py`、`tests/scripts/run_qemu_test.py`、`tests/scripts/gen_trampoline.py`、`tests/scripts/trampoline.bin`（`QEMU-014t` 产出）
  - `tools/qemu/check_qemu_trans.py`（`QEMU-019t` 产出）
- `make build-qemu` PASS；`qemu-system-dadao -M ?` 显示约定机器名
- **全部 M1 向量经 harness 执行且结果比对一致**（硬性要求）：`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/*.yaml` 全量 PASS（0 FAIL，deferred 允许但须记录）
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）
