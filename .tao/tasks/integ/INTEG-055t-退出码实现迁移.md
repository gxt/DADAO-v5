# INTEG-055t: 退出码实现迁移（QEMU/gem5/tests）

**模块**：integ
**项目里程碑**：M11
**依赖**：`SPEC-187t`（已验证；Machine-v5 §7.1 三段表）、`SPEC-192t`（已验证；表已迁 §7.1）、`SPEC-191t`（旧码清理）
**状态**：待开始

## 执行环境
本地；跨 QEMU/gem5/tests 的退出码实现迁移，按 QEMU → gem5 → tests 串行。

## 背景

`Machine-v5 §7.1` 已定稿：

- guest：`0x00–0x3F` PASS、`0x40–0x7F` FAIL
- 其它 cfx：`0x80–0xBF`（`bit5:0=cfxHA`）
- monitor：`0xC0–0xFF`（`bit5:4=运行模式`、`bit3:0=异常位索引`）
- monitor 索引：0/1/2/3/7/8/9/10/11/12/13

QEMU/gem5/tests 仍用旧码/旧公式，需迁移。

## 目标

1. **QEMU**：machine fault 退出码改为三段式；monitor 段按当前运行模式 + 异常位索引；其它 cfx 段按 cfxHA；guest pass/fail 不变；删除旧 `0x84`/`0x87`/`0xE1` 派生。
2. **gem5**：同 QEMU，逐处对齐。
3. **tests**：更新期望退出码、harness、parity 判据；matrix 重生成。
4. 三阶段串行；共享测试只在 tests 阶段改。

## 验收标准

1. QEMU/gem5 退出码与 `Machine-v5 §7.1` 逐项一致：guest / 其它 cfx / monitor。
2. `CFXTRAP`/`CFXESC` 进目标/当前 cfx 时按 `0x80–0xBF`；其余同步异常进当前 monitor。
3. 未映射/A-D 回写失败 ⇒ `CFXMEM` monitor；reserved cfx `ld/st` ⇒ `CFXMEM`、`trap`/`escape` ⇒ `ILLI`。
4. `make build-qemu`/`build-gem5`、`check-arch`/`check-inst`、L1 rc=0。
5. `matrix-M11` 重跑：`node/arch` 249 AGREE、0 fail；退出码相关行全 AGREE。
6. 反例：写回旧 `0x84`/`0x87` ⇒ FAIL；还原回绿。
7. 完成区 ≤30 行；状态 `待验收`。

## 范围 / 非范围

**在范围内**：`components/qemu/**`、`components/gem5/**`、`tests/**`（退出码期望/harness）、`tools/testcases/parity/**`（判据如需）、本任务书、`milestones.md`。

**不在范围内**：`spec/**`、ADR、`contracts/**`、5 个屏蔽寄存器清理（`INTEG-054t`）。

## 说明

- 这是 `SPEC-187t` 的实现落地；不改 spec。
- 旧的 `0x80 | cause_bit` 公式不再使用；monitor 段不是简单 `0x80 | index`。
- 若某测试的期望码需人工推导，按 §7.1 计算并在完成区给出公式/示例。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
