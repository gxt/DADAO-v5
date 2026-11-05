# SPEC-193t: spec/README 精简后的外部指针修复

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-185t`（已验证；spec/README 已删除投影表/缺口表等非 spec 内容）
**状态**：待开始

## 执行环境
本地；只修文档指针，不改 spec 规范语义。

## 背景

`SPEC-185t` 删除了 `spec/README.md` 的投影表/缺口表等非 spec 内容，导致外部文档仍有指针指向已不存在的节/表。reviewer 现场确认仍悬空 5 处：

- `docs/Process-02-合约编写规范.md:20`：`spec/README.md`「登记缺口（显式 deferred）」表 / 投影表
- `docs/Process-06-spec目录保护规范.md:61`：`spec/README.md` 的历史版本表
- `.tao/knowledge/MEMORY.md:50`：`spec/README.md`（分册索引、投影/缺口表）
- `.tao/contracts/contract-asm.md:260`：`spec/README.md` 投影表 `Toolchain-01` 行 ③ 机械门控列
- `docs/README.md:26`：`spec/README.md` 投影表

已消解、无需改：根 `README.md:16`（册维护约定+版本号语义）、`docs/Process-02:34`（规范修订流程）、`MEMORY.md:17`。

## 目标

1. 逐处改为指向**现存**的 `spec/README.md` 节（如「分册清单」「册维护约定」「规范修订流程」），或删除指针并保留句子。
2. 不再引用已删除的「投影表」「登记缺口表」「历史版本表」。
3. 不新增 spec 内容，不把投影/缺口表搬回 spec/README。
4. 不改 spec 语义、ADR decision、contracts 数据、QEMU/gem5/tests。

## 范围 / 非范围

**在范围内**：`README.md`（若仍有悬空）、`docs/Process-02-合约编写规范.md`、`docs/Process-06-spec目录保护规范.md`、`docs/README.md`、`.tao/contracts/contract-asm.md`、`.tao/knowledge/MEMORY.md`、本任务书、`milestones.md`。

**不在范围内**：`spec/**`、`.tao/adr/**`、`contracts/**`、QEMU/gem5/tests、门控脚本。

## 验收标准

1. **悬空清零**：上述文件不再引用 `spec/README.md` 的「投影表」「登记缺口表」「历史版本表」；改为现存节或删除指针。
2. **句子保留**：只删/改指针，不删整段技术结论；不新增内容。
3. **引用一致**：`check-knowledge-refs`、`check-spec-refs`（若扫到）rc=0；`make check`（L1）rc=0。
4. **反例可达 FAIL**：写回一处 `spec/README.md 投影表` ⇒ 断言 FAIL；`cp`+`md5sum -c` 还原回绿。
5. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是 `SPEC-185t` 的收尾清理，不重新引入非 spec 投影表。
- 若某指针所在句子需要说明“投影已迁实现层”，用不带路径的描述，不再指向 spec/README 的已删表。
- 与 `SPEC-192t` 并行时只改不同文件；不改 `contract-see`/`Machine-v5`/ADR。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
