# m13-gem5-004: gem5 SE 页表故障未投递给 guest（`lemon` 的 `GenericPageTableFault` 根因与修复）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-gem5-003`（非对齐 `.bss` 修复后 `lemon` 才能装载）；与 `m13-gem5-003` **同一组件，须串行**
**可并行分片**：否（组件单写者）
**状态**：待开始

## 背景

`m13-gem5-003` 修掉 `ISS-359` 后，dynamic `llvm-ts` 的 7 例从 `blocked` 转为可装载。其中：

- `Burg`、`spiff` ⇒ pass；
- `obsequi`/`sqlite3`/`bc`/`mafft` ⇒ 可装载，600 s 预算内未完成（属长尾，见 `m13-testcases-003`）；
- **`lemon` ⇒ 可装载并运行 56.5 s，随后 abort（`rc=-6`），日志为 gem5 内部的 `GenericPageTableFault`**；engineer 称「static 基线上同签名」。

用户 2026-11-10 裁定：**立任务查根因并修复**（放 M13）。

## 现象与待查

- 触发点：dynamic `lemon`（`MultiSource/Applications/lemon`）运行期出现 guest **未映射访问**。
- gem5 的反应是**仿真器内部 fatal/abort**，而不是把故障按 SE 语义投递给 guest（SIGSEGV）。
- QEMU 侧同一 ELF/同一套件**通过**（`m13-testcases-002` 结果），说明这不是程序自身必错，而是 gem5 的行为差异。
- 需要先确认：`static` 基线是否真同签名（用户已知悉 engineer 的声称，但**须用未改动的基线二进制独立复现**），若 static 不同签名，说明与 dynamic 装载路径相关，根因范围不同。

## 目标

1. **根因**：定位 `GenericPageTableFault` 的产生点（哪个地址、哪条翻译路径、是 SE 的 `seWorkload` 缺页处理还是 `process.cc` 的段映射缺失），给出最小复现命令与关键日志/调用栈。
2. **修复**：guest 访问未映射地址时，按 SE 语义**向 guest 投递故障**（SIGSEGV / guest 可见异常），**不得**让仿真器自身 abort；`lemon` 的最终结果与 QEMU 一致（pass 或按 oracle 的确定 fail，不得死于仿真器）。
3. **不掩盖**：若是 gem5 自身映射表错误（如段未登记）而非「guest 真越界」，则修映射而不是把 fatal 降级为 warning——两者必须在完成区明确区分。

## 验收标准

1. 根因说明：触发地址 / 翻译路径 / 为何 abort，附最小复现命令与真实输出（`rc`、日志行、调用栈）
2. 修复后 `lemon`（dynamic）结果与 QEMU 一致；给出 run 时耗与退出码
3. **基线对照**：用未改动的基线二进制复现 static 同例，判定是否同签名（结论写清）
4. 回归：`check-inst`（Vast 980/985 + 5 deferred、Tiny 44/44）、`check-inst-smoke`、`check-arch`、`check-unit`、L2 零回归；`check-patch-tree`/`check-source-state` rc=0
5. 补丁由 `make_patch.py gem5` 导出（非手改），`series`/`changelog.md` 同笔
6. 一键证据脚本（含可达 FAIL 注入：回退修复应使 `lemon` 重新 abort）
7. 完成区 ≤30 行、无运行期路径

## 非范围

- 不处理 4 例 timeout（`obsequi`/`sqlite3`/`bc`/`mafft`，属 `m13-testcases-003` 长尾预算）
- 不改 QEMU / chipyard / spec
- 不做性能优化

## 说明

- 组件单写者：`m13-gem5-003` 收口（合并到 master）后方可开始。
- 构建在主控机（`JOBS=8`）；节点 207/208 正跑 `m13-testcases-003`，**不要占用**。
- 若根因涉及 `spec/` 语义（例如 SE 是否应向 guest 投递 SIGSEGV），先登记冲突、按现有 spec + QEMU 行为推进，不擅自改 spec。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定时留问。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. **不得写入未经主会话转达的用户裁定**；自定事项写「自决」（`ISS-365`）。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
