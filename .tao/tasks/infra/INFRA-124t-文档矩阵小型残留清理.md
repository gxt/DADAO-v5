# INFRA-124t: 文档/矩阵小型残留清理

**模块**：infra
**项目里程碑**：M11
**依赖**：`SPEC-185t`/`SPEC-193t`（已验证）、`TESTCASES-098t`（已验证）
**状态**：待开始

## 执行环境
本地；只清文档/指针/矩阵驱动残留，不改规范语义。

## 背景

`SPEC-185t`/`SPEC-193t`/`TESTCASES-098t` 收口后仍有小残留：

1. `.tao/adr/adr-0013-*.md:217` 仍引用已删的 `spec/README.md`「投影表」。
2. `tools/infra/check_spec_refs.py:41-42` 仍有「投影表」文案。
3. `tools/testcases/parity/run_parity.py` 硬编码 `GEM5-017t` 证据指针。
4. `tools/testcases/parity/README.md` 旧 Node embench 口径。
5. `spec/Toolchain-01` §1/§2.4/§14 删除非 spec 指针后句意偏空（A1 允许，可选润色）。

## 目标

1. ADR-0013：只把「投影表」指针改为现存节（如「分册清单/册维护约定」）或删除指针；不改 decision；追加 `rev. 2026-11-05` 或集中注记。
2. `check_spec_refs.py`：删除/更正「投影表」注释，不改检查逻辑。
3. 矩阵驱动：去掉硬编码 `GEM5-017t` 证据路径，改为当前任务/通用描述；不改判据。
4. `tests/parity/README.md`：Node embench 口径改为“历史、不计入 M11 Node 验收”。
5. Toolchain 空心句：仅做不改变语义的最小润色；若会改锁或引入新语义，保留并登记，不强改。

## 验收标准

1. ADR-0013/`check_spec_refs.py` 不再指向已删「投影表」。
2. 矩阵驱动无 `GEM5-017t` 硬编码；README Node embench 口径正确。
3. `check-knowledge-refs`、`check-spec-refs`、`check-tests-index`、`check-milestones-fresh`、L1 rc=0。
4. 反例可达 FAIL；完成区 ≤30 行；状态 `待验收`。

## 范围 / 非范围

**在范围内**：`.tao/adr/adr-0013-*.md`（仅指针）、`tools/infra/check_spec_refs.py`（仅注释）、`tools/testcases/parity/{run_parity.py,README.md}`、`spec/Toolchain-01`（仅可选润色）、本任务书、`milestones.md`。

**不在范围内**：其它 ADR、spec 语义、QEMU/gem5/tests 期望、contracts。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
