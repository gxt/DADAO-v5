# m20-llvm-003: 允许 `.set` 定义的 Absolute 符号作指令立即数（ISS-430）

**模块**：llvm
**项目里程碑**：M20
**依赖**：`m20-llvm-001/002` 已合入；同改 `components/llvm-project`，须串行
**可并行分片**：否（单组件 AsmParser）
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（issues-left 分诊，2026-11-25）

`ISS-430`：`m14-llvm-005` 后，下面这种合法写法从「静默 0」变成报错：

```
.set VD, L1-L0
L0:
...
set.zw rb1, wp0, VD
L1:
```

`VD` 已由 `.set` 固化为 **Absolute** 符号（值可编码），但 AsmParser 仍按
「symbol difference ('A - B')」拒绝，诊断文案也不准确。禁止未解析的符号差是对的，
但不该连带拒绝已求值的 Absolute 符号。

## 目标

1. AsmParser 在指令立即数路径上对**已求值的 Absolute 符号**放行（`evaluateAsAbsolute`
   成功即可编码）；未解析的 `A - B`、未定义符号仍按原语义拒绝。
2. 诊断文案只在真的是未解析符号差时使用“symbol difference”；Absolute 符号失败时
   给出与值/宽度相关的诊断。
3. 新增 lit 正例/负例：`.set VD, L1-L0` + `set.zw ... VD` 编码正确；未定义/不可求值
   的符号差仍 rc≠0；不改变既有 `symdiff-imm-err.s` 中真正应拒绝的用例。

## 验收（逐条贴真实 rc）

1. 最小复现：修复前 `llvm-mc` rc≠0（记录原文）；修复后 rc=0，目标指令编码与手算
   （`VD` 的绝对值 + 字段布局）一致。
2. `symdiff-imm-err.s`/`symdiff-addr-err.s` 中未解析符号差的负例仍全部 rc≠0；
   新增正例通过。给出注入（把 Absolute 分支关掉 ⇒ 正例红；`cp`+md5 还原回绿）。
3. `make check-lit`、`check-instrinfo`、`check-patch-tree` 的 llvm 段 0 problem；
   `series` 数按实际（不得为过门控改数）。
4. 重建/安装按仓库纪律；记录 `llvm-mc` 安装根与构建树 md5 一致。证据落运行期证据
   目录内 `run.sh`；不写具体构建/临时路径。

## 约束

独立 `git worktree`（分支 = `m20-llvm-003`）；不提交 git；只改
`components/llvm-project/**`、对应 lit 与本任务书；不改 `spec/`、契约、`Makefile`。
当前 gem5 任务在独立源/构建树，LLVM 无活跃写者；不要碰 gem5。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
