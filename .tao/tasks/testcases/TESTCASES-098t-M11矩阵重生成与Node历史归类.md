# TESTCASES-098t: M11 矩阵重生成与 Node 历史归类

**模块**：testcases
**项目里程碑**：M11
**依赖**：M11 收口条件满足（`SPEC-186t`、退出码迁移、完整 llvm-ts 回归）
**状态**：待开始

## 执行环境
本地；只重生成矩阵与归类历史结果，不改实现、不改 spec。

## 背景

`tests/parity/matrix-M11.md` 仍是 `GEM5-017t` 的旧快照；M11 收口需要原地重生成。同时用户已定：`GEM5-016t`/`QEMU-080t` 的 Node `inst`/`embench` 结果**转历史**，不计入 M11 Node 验收；M11 Node 只验收 cfx/arch/PTW/模式；Embench 归属 Tiny（system/bare-metal）与 SE（user static/dynamic），Node 不跑 Embench。

## 目标

1. 以 M11 收口时的 QEMU/gem5 现场结果，**原地重生成** `tests/parity/matrix-M11.md`：
   - 覆盖 Tiny/Node 的 `inst`/`arch` 与 SE 的 tset 矩阵；
   - 保留 `AGREE_PASS`/`DIFF`/`QEMU_ONLY_FAIL`/`GEM5_ONLY_FAIL`/`BLOCKED` 分类与计数；
   - `math_test` 的 B7 已知差异保留 `BLOCKED` 及计数，不写 PASS。
2. 在矩阵/README 中标注历史归类：
   - `GEM5-016t`/`QEMU-080t` 的 Node `inst`/`embench` 结果标“历史、不计入 M11 Node 验收”；
   - M11 Node 验收范围写明 cfx/arch/PTW/模式；
   - Node 不跑 Embench；Tiny/SE 的 Embench 归属写明。
3. 不修改任何测试期望值、不改引擎实现；只改矩阵快照与说明。

## 接口规范

- 矩阵由 `tools/testcases/parity/run_parity.py` 现场生成，禁手改 JSON/Markdown 计数。
- Node 历史结果只作说明，不进入 M11 Node 通过/失败统计。
- `math_test` 若有差异，保留 `BLOCKED` 与 `errors/total` 现场数字；不把 blocked 计入通过数。
- 不改 `tests/parity/matrix-M11.md` 之外的矩阵快照（除非任务书现场确认需要同步索引）。

## 范围 / 非范围

**在范围内**：`tests/parity/matrix-M11.md`、`tools/testcases/parity/README.md`（仅历史归类/Node 范围说明）、本任务书、`milestones.md`、运行期证据。

**不在范围内**：QEMU/gem5/LLVM 实现、`spec/**`、`contracts/**`、`tests/inst/**`/`tests/arch/**` 期望值、`Makefile`、门控脚本。

## 验收标准

1. **现场重生成**：`run_parity.py` 用 M11 收口时的引擎身份（QEMU/gem5 md5/版本、fs.py、bootrom）生成矩阵；矩阵含引擎身份与命令；不引用旧临时目录/旧快照冒充。
2. **计数自洽**：行数 = 各分类之和；`AGREE_PASS`/`DIFF`/`QEMU_ONLY_FAIL`/`GEM5_ONLY_FAIL`/`BLOCKED` 计数由脚本现场统计；`DIFF` 必须逐条归因或登记 issue。
3. **Node 历史归类**：矩阵/README 明写 Node `inst`/`embench` 为历史、不计入 M11 Node 验收；M11 Node 只验收 cfx/arch/PTW/模式；Node 不跑 Embench。
4. **math_test**：若仍 BLOCKED，保留现场 `errors/total` 与 QEMU/gem5 对照；不得写 PASS 或从通过数中抹掉。
5. **llvm-ts**：M11 收口前完整 llvm-ts 回归结果纳入矩阵/说明；QEMU user 为基线，gem5 不能少通过；gem5 通过而 QEMU 未通过须定位到一致。
6. **门控**：`make check-tests-index`、`check-case-ledger`、`check-run-artifacts`、`make check`（L1）rc=0；矩阵文件格式与索引一致。
7. **反例可达 FAIL**：手改矩阵计数/删一行 ⇒ 校验脚本 FAIL；`cp`+`md5sum -c` 还原后回绿。
8. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务在 M11 收口时执行；未收口前不得用旧结果预生成。
- 若现场发现 spec/引擎语义不一致，保留现场并留问，不自行改期望值。
- 历史归类只写“不计入 M11 Node 验收”，不删除旧任务书的历史证据。

## 未决（下发前需确认）

1. **M11 收口条件**：`SPEC-186t`、退出码迁移、完整 llvm-ts 回归是否全部完成；未完成则本任务 BLOCKED。
2. **矩阵范围**：是否只重生成 `matrix-M11.md`，还是同时更新 README 的索引/统计说明。
3. **Node 历史归类的落点**：矩阵内注记 + README，是否还需要改 `GEM5-016t`/`QEMU-080t` 完成区（默认不改历史任务书）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
