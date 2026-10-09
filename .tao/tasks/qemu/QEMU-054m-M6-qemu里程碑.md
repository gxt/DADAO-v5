# QEMU-054m: M6 qemu 里程碑

**模块**：qemu
**项目里程碑**：M6
**状态**：待开始
**目标**：QEMU 支持 M6——**改走 `load_elf()`**（取消自建 `dadao_load_regions[]` 白名单；多段 `PT_LOAD`/RELA/`e_entry`/栈初始化作验证项）；**RAM@0 step2**（旧向量/harness/`crt0`/e2e 迁 `0` + 删旧 RAM 段 `0xffff_0000_0000` + 收紧 `check-interface` 断言）并含 **`ISS-169`**（6 个 M1/M2 手写探针退出通道改 `SYS_EXIT`）；`make check`/`check-interface`/`check-qemu-semantics` 绿。
**关联任务**：`QEMU-052t`、`QEMU-053t`、`QEMU-055t`

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`components/qemu/patches/{hw/dadao/**,target/dadao/**}`、`series`/`changelog.md`；迁移后的旧向量/harness/`crt0`/e2e（EA=0 语义已更新）
- 不回归：`make check`/`check-interface`/`check-qemu-semantics` EXIT=0；`check-patch-tree` 断言⑥绿
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）

## 审阅记录

#### 第 1 轮 reviewer 验收
（审查者独立验证：关联任务状态、产出存在性、门控重跑、跨模块（`ISS-165`/`ISS-169`）处置、判决）
