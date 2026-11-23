# m18-testcases-002: escape cg9 向量（QEMU hart-first 后）

**模块**：testcases
**项目里程碑**：M18
**依赖**：`m18-qemu-004`（QEMU 支持 `imms18=2`/cg9）
**可并行分片**：否
**预估**：1–2 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为向量补例 + 签名重生成）
**档位**：小改（向量）
**状态**：待开始
**执行环境**：本地（QEMU system；如涉及 RTL 另注）

## 背景

`m18-idl-001` 把 `escape` 的 cg9 语义放进 `idl_exec --self-test`，但**指令向量层**暂无法写「`imms18=2` ⇒ cg9」的可判定断言：

- Tiny 平台不实现 `cfx_hart`，cg9 不可达；
- QEMU 在 `m18-qemu-004` 前仍按旧 `imms18 & ~1 ⇒ ILLI`；
- 共享宏层没有 `CFXESC` 种类，新增链例检查点要重生成签名。

本任务在 QEMU hart-first 合入后补向量。

## 目标

1. `tests/inst/11-cfx/escape_ciii_cfx.S` 增 cg9 用例：
   - `imms18=2` 在 `cfx_hart` 上走 cg9：帧有效/无效、返回 IP/mask 恢复；
   - `imms18=2` 在非 `cfx_hart` 上 ⇒ `CFXESC`；
   - `imms18=3`、`[17:2]` 非零 ⇒ `ILLI`（保留）。
2. 如需要，补 `CFXESC` 宏/链例检查点；重生成 `tests/case-ledger.tsv`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`。
3. 与 QEMU 逐字节签名一致；RTL/gem5 未支持前按平台标注或排除（不得静默只跑 QEMU）。

## 验收（逐条贴真实 rc）

1. `make check-inst-asm` / `check-idl` 全绿，新增 cg9/CFXESC/ILLI 用例逐条 PASS；`check-inst-sig` 与基线一致（或按平台差异登记）。
2. 签名重生成可复现（两次生成 byte-identical）。
3. **可达 FAIL ≥2 路**：① QEMU 旧 `imms18 & ~1` ⇒ cg9 用例红；② cg9 不恢复 mask ⇒ 用例红；还原后回绿。
4. 不回归：`check-tests-index`、`check-case-ledger`、`check-inst-macro-scope`、`make check` 与基线逐行相同。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`tests/inst/11-cfx/**`、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tests/data/inst-signature/**`（生成物）、本任务书；不改 QEMU/RTL/gem5/IDL/内核。
3. 不改版本号；术语「bank = 寄存器组」；生成物用仓库工具重算。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`。

## 待裁定

无。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
