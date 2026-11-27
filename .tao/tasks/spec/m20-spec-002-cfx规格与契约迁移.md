# m20-spec-002: cfx 规格正文与契约迁移（0.8.1）

**模块**：spec
**项目里程碑**：M20
**依赖**：`m20-spec-001` 已决口径；M16/M17 收口后派发
**可并行分片**：否（spec/contracts 单写者）
**预估**：4–8 h
**档位**：大改（规格/契约）
**状态**：待开始

## 背景

执行 `m20-spec-001` 的 2026-11-26 已决口径：cg4/5/6/7 重排、scratch 2..16、PTWFAULT/PTWACCERR、cfx 编号、UART、中断删除、每 cfx 五种原因、0.8.1 定版（不立 ADR）。本任务只做 **spec 正文 + contracts + cfx 别名/合法性 + 版本锁**，不改引擎/IDL/LLVM。

## 范围

- `spec/DADAO-12`/`DADAO-13`/`DADAO-23`/`Kaiwu` 等涉及 cfx 的正文；
- `.tao/contracts/` 与 `contracts/` 的 cfx/异常/PTW/UART/时间相关表与别名；
- cfx 别名表/合法性表/opcodes 中受影响条目；版本锁/清单；0.8.1 定版。

## 验收

1. 正文/契约逐条实现 `m20-spec-001` 的已决口径；无旧 cg/编号/名称残留（按现场 grep 清单）。
2. `check-spec-*`、`check-contracts-*`、`check-cfx-aliases`、`check-cfx-alias-table`、`check-isa-coverage`、`check-manifests-guard` 真 rc。
3. 版本：`DADAO-12` 等 0.8.1-rc → 0.8.1；相关锁/README 同步；不立 ADR。
4. 与 `m20-idl-001`/`m20-llvm-004` 的边界：本任务不改 IDL/LLVM 实现；生成物/别名表可由本任务更新但要列明。
5. 证据落运行期证据目录内 `run.sh`；不写具体构建/临时路径。

## 约束

独立 worktree（分支 = `m20-spec-002`）；不提交 git；不改 `components/**`、引擎、内核；术语 bank = 寄存器组。

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
