# DADAO for SimRISC 0.5.3

基于 `spec/` 目录下 11 份规范文档，实现 LLVM 编译器、QEMU 模拟器、Chipyard 仿真器和 Linux 内核的全栈支持。

## 当前版本号

本表是**规范版本与冻结状态的唯一来源**（不使用 `manifests/spec.lock.toml`）；版本号取自 `spec/` 各文档头部的 `> **版本：X.Y.Z**`。

| 组件 | 版本 |
|------|------|
| SimRISC | 0.5.3 |
| AEE / ABI | 0.9.2 |
| SEE / SBI | 0.7.1 |
| HEE / HBI | 0.1.2 |

版本同步要求：AEE ↔ ABI、SEE ↔ SBI、HEE ↔ HBI 必须一致，全部基于同一 SimRISC 版本号。

**冻结状态**：待冻结（由 `SPEC-008t` 核对后标注为 `已冻结`）。

## 参考目录

| 目录 | 说明 |
|------|------|
| `.work/DADAO-0628` | 基于 SimRISC 0.4.1 的完整实现（工程参考，commit 锁定于 `manifests/references.lock.toml`） |
| `.work/DADAO` | 各阶段早期的代码实现（已不再更新；`https://github.com/gxt/DADAO.git`） |

## 路线图

路线图与任务拆解**直接参考 DADAO-0628**（`.work/DADAO-0628`）：

- 里程碑：`docs/development-roadmap.md`（M0 Foundation / M1 MC+CPU Core / M2 Basic CodeGen / M2.5 clang+libc）
- 详细路线：`code-agent/designs/0001-foundation-scope.md`、`0002-detailed-roadmap.md`
- 任务：`code-agent/tasks/`（`DL`/`ML`/`KL`/`DG`/`SL`/`IN` 等流）

本仓库按**模块**组织任务（见 `.tao/README.md`）：`infra` / `spec` / `testcases` / `golden` / `llvm` / `qemu` / `verif` / `gem5` / `sail`。
