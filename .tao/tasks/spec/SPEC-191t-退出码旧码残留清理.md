# SPEC-191t: 退出码旧码残留清理（ADR/DDLN/Machine-00）

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-187t`（已验证；Machine-v5 三段退出码表、ADR-0004 D5.8 指针化）
**状态**：待开始

## 执行环境
本地；只清理旧退出码字面，不改决策语义；ADR decision 改动须用户逐条确认。

## 背景

`SPEC-187t` 已把 `Machine-v5 §1.2` 改为完整三段表，`ADR-0004 D5.8` 指针化。但以下地方仍有旧码字面：

- `ADR-0004` 其它 decision：
  - D1 / D3 / D4 / D6.2 / D6.3 / Rationale / Consequences 仍有 `0x87`/`0x88`/`0x8C` 等旧码
- `docs/DDLN/D-D002`
- `docs/Machine-00`
- `ADR-0009`
- `ADR-0041`

这些与 `D5.8` 的新指针并存，读者会看到两套码。

## 目标

1. 把上述位置的旧码字面改为指针：“退出码分段/逐码见 `spec/Machine-v5 §1.2`”；不复制逐码表。
2. `ADR-0004` 其它 decision 只做**指针化修订**，不改决策结论；每处追加 `rev. 2026-11-05` 或集中“修订”注记。
3. DDLN/Machine-00/ADR-0009/ADR-0041 只改旧码解释，不改技术结论。
4. 不改 QEMU/gem5/tests/contracts；不改 Machine-v5（已由 187t 定稿）。

## 范围 / 非范围

**在范围内**：`.tao/adr/adr-0004-test-machine.md`（仅旧码字面/指针）、`.tao/adr/adr-0009-*`、`.tao/adr/adr-0041-*`、`docs/DDLN/D-D002`、`docs/Machine-00`、本任务书、`milestones.md`。

**不在范围内**：`spec/Machine-v5`（已定稿）、`DADAO-12/13/22/23`、QEMU/gem5/tests、`contracts/**`、DDLN 其它册。

## 验收标准

1. 上述活文件旧码/`PTWERR`/`unmapped` 字面 0 命中（历史/修订段除外）。
2. 全部改为指针，不复制逐码表；决策结论不变。
3. ADR 修订有 `rev. 2026-11-05` 或集中注记；用户逐条确认记录在任务书 §用户裁定。
4. 门控：`check-spec-refs`/`check-spec-purity`/`check-knowledge-refs`/`check-milestones-fresh`/`make check`（L1）rc=0。
5. 反例可达 FAIL；完成区 ≤30 行；状态 `待验收`。

## 未决（下发前必须确认）

1. **ADR decision 逐条确认**：ADR-0004 其它 decision、ADR-0009、ADR-0041 的旧码指针化是否授权；未确认前不得改 ADR，不得置 `已验证`。
2. `docs/Machine-00` 是否属规范真源，还是讲义；默认只改旧码说明。
3. 是否把 DDLN 其它册一并清理；默认只列 D-D002。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
