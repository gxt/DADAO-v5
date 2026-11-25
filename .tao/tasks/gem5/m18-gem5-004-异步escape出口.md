# m18-gem5-004: gem5 实现异步 escape 出口（cg5 rc8–rc11、cg9 新布局）

**模块**：gem5
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入）、`m18-llvm-002`（汇编）、`m18-testcases-004`（向量）
**可并行分片**：否（同 `components/gem5`）
**预估**：3–4 h（标定：同档 gem5-001/002 2–3 h；本任务含布局 + escape + 入口，取 1.2–1.5×）
**档位**：大改（gem5 异常模型）
**状态**：待开始
**执行环境**：本地

## 背景

`m18-spec-007`/`ADR-0061 R3`：`cg5 rc0`–`rc3` 入口记录（只读）、`rc8`–`rc11` 出口意图；`cg9 rc0`–`rc4`/`rc14`/`rc15`；`escape cfxHA` 按 `rc8`–`rc11` 返回并整字写目标 monitor `cg8 rc1`。gem5 仍是 R2。

## 目标

1. 寄存器面：`cg5` 新布局（`rc0`–`rc3` 只读、`rc4/rc5`、`rc8`–`rc11`、`rc11` 复位全 1、删 pending）；`cg9` 新槽位；`cg0`–`cg3` switch/vector → `rc14`/`rc15`，旧 `rc8`/`rc10` ⇒ `CFXREG`。
2. 进入：同步写目标 cfx `cg5 rc0`–`rc5`+`rc8`–`rc11`；异步写 `cg9 rc0`–`rc4` + hart `cg5 rc8`–`rc11`。
3. `escape`：`imms18=0`（非 0 ⇒ `ILLI`）；`cfxha`=当前 cfx；不得升权；目标未实现/无 monitor ⇒ `CFXESC`；跳 `rc10`；`rc11` 整字写；`escape_num` +1。
4. 与 QEMU/RTL 同 ELF 签名一致；不一致登记 `expected-divergences.yaml`（含 `DIV-*` 增删）。
5. 不做：不改 QEMU/RTL/IDL/LLVM/内核/spec。

## 验收（逐条贴真实 rc）

1. 构建与单测 rc=0；`m18-testcases-004` 向量在 gem5 上可跑条目通过。
2. 同 ELF 与 QEMU 签名一致；`expected-divergences` 更新且 `check-*` rc=0。
3. 可达 FAIL ≥2 路（`rc11` 增量写；升权不判），`cp`+md5 还原回绿。
4. 不回归：既有 gem5 cfx/缓存代表集；`check-patch-tree` gem5 段 0 problem；`check-component-changelog` rc=0。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/gem5/patches/**`、`components/gem5/changelog.md`、`tests/arch/**`、`tests/arch/expected-divergences.yaml`、本任务书。
3. 不改其它实现/spec/契约/Makefile；不改版本号；`cp`+md5 还原；等 gem5 写者窗口。

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
