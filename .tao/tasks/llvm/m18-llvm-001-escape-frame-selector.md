# m18-llvm-001: escape frame selector 的 LLVM 汇编/反汇编支持

**模块**：llvm
**项目里程碑**：M18
**依赖**：`m18-spec-003`（`SimRISC-11`/Toolchain-01/contract-asm 的编码真源）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为编码/汇编器/反汇编器 + lit，取 1.5–2× 中位）
**档位**：中改（工具链编码）
**状态**：待开始
**执行环境**：本地（`build-mc`；lit）

## 背景

`m18-spec-002/003` 给 `escape` 增加 **frame selector bit1**：

- `imms18` bit1：0=cg5，1=cg9；
- 合法 `imms18 ∈ {0,1,2}`（cg5 偏移 0/+4、cg9 偏移 0），`3 ⇒ ILLI`；
- 汇编层 `imms20 ∈ {0,4,8}`（8=cg9 偏移 0）；
- `imms18[17:2]` SBZ。

LLVM 侧目前只接受/生成 `imms20 ∈ {0,4}`，需要同步，否则内核/探针无法汇编 `escape ..., 8`。

## 目标

1. **汇编器**：`escape cfxha, [excp_cause_ip, <imm>]` 接受 `imm ∈ {0,4,8}`；`8` 编码为 `imms18=2`（bit1=1、bit0=0）；拒绝其它值并给出诊断；`imms18[17:2]` 非零的诊断/编码规则与 spec 一致。
2. **反汇编器**：把 `imms18` bit1 解回 frame selector；输出可区分 cg5/cg9（助记符/注释/操作数形式由 spec-003 的汇编语法定，遵循 Toolchain-01）。
3. **测试**：`tests/unit/llvm/lit/MC/DADAO` 增 `escape` 的 0/4/8 正向、非法值负向、bit1 编解码往返；必要时 `check-codegen` 补一条最小程序。
4. **补丁/文档**：`components/llvm/patches/**` 经 `make_patch.py llvm` 重导；`components/llvm/changelog.md` 记录；不改 `spec/`/contracts。

## 验收（逐条贴真实 rc）

1. `make build-mc` rc=0；`llvm-mc` 手测 `escape ..., 0/4/8` 编码与 `llvm-objdump` 反汇编往返正确；非法值（1/2/3/5/6/7…）报错。
2. 新增 lit 用例全绿；`make check-lit`（或 `check-lit-full`）rc=0；`check-unit` 与基线逐行相同。
3. **可达 FAIL ≥1 路**：回退编码（只允许 0/4）⇒ 新增 `8` 用例红；`cp`+md5 还原后回绿。
4. `check-patch-tree` llvm 段 0 problem；`check-component-changelog` rc=0；`make check` 与基线逐行相同。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/llvm/patches/**`、`components/llvm/changelog.md`、`tests/unit/llvm/**`、本任务书。不改 `spec/`、`.tao/contracts/`、`Makefile`、QEMU/RTL/gem5/内核。
3. 组件补丁经 `make_patch.py llvm` 重导；不改版本号；术语「bank = 寄存器组」。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
5. 期望值以 `SimRISC-11`/`Toolchain-01`/`contract-asm` 为准，不从现有实现反推。

## 待裁定

无（若 spec-003 的汇编语法/操作数形式有歧义，停下写「待裁定」）。

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
