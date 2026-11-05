# SPEC-191t: 退出码旧码残留清理（ADR/DDLN/Machine-00）

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-187t`（已验证；Machine-v5 三段退出码表、ADR-0004 D5.8 指针化）
**状态**：待开始

## 执行环境
本地；只清理旧退出码字面，不改决策语义；ADR decision 改动须用户逐条确认。

## 用户裁定（2026-11-05，逐项）

> 「A：`ADR-0004` 所有活 decision 文本（D1/D3/D4/D5.1–D5.6/D6.2/D6.3/Rationale/Consequences）的旧退出码字面指针化；`## 修订` 历史段不改。」
> 「A：`ADR-0009` 表删除旧码列，改指针；`ADR-0041` D7/D10 的 `PTWERR` 改为 `CFXMEM` 当前 monitor + 指针；两册 `## 修订` 历史段不改。」
> 「A：DDLN `D-D002`/`TT-D002` Q4 按新模型改写（不再区分 CFXMEM/unmapped）；`Machine-00` 的 `0x81–0x8D` 改三段式描述；不改规范语义。」
> 「无需另立任务，原地修订 `ADR-0009 D5`。」（2026-11-05，用户原话）

## 背景

`SPEC-187t` 已把 `Machine-v5 §1.2` 改为完整三段表，`ADR-0004 D5.8` 指针化。但以下地方仍有旧码字面：

- `ADR-0004` 其它 decision：
  - D1 / D3 / D4 / D6.2 / D6.3 / Rationale / Consequences 仍有 `0x87`/`0x88`/`0x8C` 等旧码
- `docs/DDLN/D-运行平台/DD-D002` 与 `TT-D002`
- `docs/Machine-00`
- `ADR-0009`
- `ADR-0041`

这些与 `D5.8` 的新指针并存，读者会看到两套码。

## 目标

1. 把上述位置的旧码字面改为指针：“退出码分段/逐码见 `spec/Machine-v5 §7.1`”；不复制逐码表。`ADR-0004` 的 D1/D3/D4/D5.1–D5.6/D6.2/D6.3/Rationale/Consequences 全部纳入；`## 修订` 历史段不改。
2. `ADR-0004` 其它 decision 只做**指针化修订**，不改决策结论；每处追加 `rev. 2026-11-05` 或集中“修订”注记。
3. DDLN `D-D002`/`TT-D002` 的 Q4 按新模型改写；`Machine-00` 的 `0x81–0x8D` 改三段式；`ADR-0009 D5` 原地修订为三段式分区；只改旧码解释，不改技术结论。
4. 不改 QEMU/gem5/tests/contracts；不改 Machine-v5（已由 187t 定稿）。

## 范围 / 非范围

**在范围内**：`.tao/adr/adr-0004-test-machine.md`（仅旧码字面/指针）、`.tao/adr/adr-0009-*`、`.tao/adr/adr-0041-*`、`docs/DDLN/D-运行平台/DD-D002`、`docs/DDLN/D-运行平台/TT-D002`、`docs/Machine-00`、本任务书、`milestones.md`。

**不在范围内**：`spec/Machine-v5`（已定稿）、`DADAO-12/13/22/23`、QEMU/gem5/tests、`contracts/**`、DDLN 其它册。

## 验收标准

1. 上述活文件旧码/`PTWERR`/`unmapped` 字面 0 命中（历史/修订段除外）。
2. 全部改为指针，不复制逐码表；决策结论不变。
3. ADR 修订有 `rev. 2026-11-05` 或集中注记；用户逐条确认记录在任务书 §用户裁定。
4. 门控：`check-spec-refs`/`check-spec-purity`/`check-knowledge-refs`/`check-milestones-fresh`/`make check`（L1）rc=0。
5. 反例可达 FAIL；完成区 ≤30 行；状态 `待验收`。

## 未决（已裁定）

1. ADR decision：`ADR-0004`/`ADR-0009`/`ADR-0041` 均选 A（活 decision 指针化，`## 修订` 不改）。
2. `docs/Machine-00`：按讲义处理，只改 `0x81–0x8D` 旧码说明，不改技术结论。
3. DDLN：只改 `D-D002`/`TT-D002`，其它册不动。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
