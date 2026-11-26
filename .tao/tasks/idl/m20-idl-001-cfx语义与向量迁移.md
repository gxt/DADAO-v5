# m20-idl-001: IDL 的 cfx 语义/cause 名称/向量迁移

**模块**：idl
**项目里程碑**：M20
**依赖**：`m20-spec-002`（契约冻结）；M16/M17 收口后派发
**可并行分片**：否（IDL 单写者）
**预估**：2–4 h
**档位**：中改
**状态**：待开始

## 背景

执行 `m20-spec-001` 已决口径中的 IDL 投影：cg4/5/6/7、PTWFAULT/PTWFAIL、cfx 编号、UART32/33、每 cfx 五种原因、cause 名称迁移。

## 范围

- `idl/SimRISC-*.idl` 中 cfx 寄存器/异常原因/escape 相关语义与名称；
- IDL 向量/夹具、`idl/data` 中受影响条目；
- `check-idl-parse`/`check-idl-exec-anchor`/`check-idl` 的期望与锁（按生成器）。

## 验收

1. IDL 与 `m20-spec-002` 的正文/契约一致；旧名称/旧 cg/旧编号残留 0。
2. `check-idl-parse`、`check-idl-exec-anchor`、`check-idl`（或最小代表集）真 rc；锁按生成器更新。
3. 不改引擎/QEMU/gem5/RTL；需要语义解释的偏离写入「待裁定」。
4. 证据落运行期证据目录内 `run.sh`。

## 约束

独立 worktree（分支 = `m20-idl-001`）；不提交 git；不改 `components/**`、`spec/`、契约、`Makefile`。

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
