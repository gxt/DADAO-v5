# m20-llvm-004: LLVM cfx 别名/汇编反汇编迁移

**模块**：llvm
**项目里程碑**：M20
**依赖**：`m20-spec-002`（cfx 别名/契约冻结）；M16/M17 收口后派发
**可并行分片**：否（LLVM 单写者）
**预估**：2–4 h
**档位**：中改
**状态**：待开始

## 背景

执行 `m20-spec-001` 已决口径：cfx 编号/别名（删 llc、33/34 reserved、time=62/uart=61）、新 cg4/5/6/7、PTW/UART 名称。LLVM 侧只涉及 cfx 别名、汇编/反汇编立即数与 lit，不实现引擎语义。

## 范围

- `components/llvm-project/**` 中 cfx 别名/表/汇编器/反汇编器相关；
- `tests/unit/llvm/lit/**` 与 `tests/inst` 中受影响的汇编立即数/别名；
- 组件补丁序列/changelog；`cfx-aliases` 生成物按契约。

## 验收

1. 新 cfx 代码/别名与契约一致；旧编号/旧名称残留 0；不引入旧别名。
2. `make check-lit`、`check-instrinfo`、`check-patch-tree` 的 llvm 段 0 problem；安装根/构建树 `llvm-mc`/`llvm-objdump` md5 一致。
3. 至少一条可达 FAIL（旧别名/旧编号注入 ⇒ 红；`cp`+md5 还原后回绿）。
4. 证据落运行期证据目录内 `run.sh`。

## 约束

独立 worktree（分支 = `m20-llvm-004`）；不提交 git；不改 `spec/`、契约、引擎、`Makefile`；组件补丁按 `docs/Process-01` 重导。

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
