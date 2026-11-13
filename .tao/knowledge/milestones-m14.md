# 项目里程碑

> **项目里程碑 = M14**（M14 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；M12 = `milestones-m12.md`、M13 = `milestones-m13.md`）

> **本页只维护 M14 任务台账**：M11 及以前已归档（`.tao/archive/M11/`）；历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **M14 定位（用户 2026-11-13）**：**Linux bring-up**。基线 Linux `7.2.10`；平台 = QEMU system 模式**单核**；控制台 = **semihosting**（不引入 UART、不新增 cfx）；initramfs = 静态 musl `init`；启动传参 = **固定 boot info 结构**（不引入设备树）；TLB 规范在 K3、K0 不定义；不引入 cache/LLC。参考实现（`DADAO` / `DADAO-0628`）只借鉴阶段划分与踩坑，`arch/dadao` 按当前冻结契约重写。

本页分三张**任务表**，**表位置 = 任务状态**（不另设状态列）：

| 表 | 收录 | 列 |
| --- | --- | --- |
| 待开始（未开工） | 尚未派单的 `待开始` | `编号` / `预估时间` / `一句改动` |
| 进行中（已派单） | 已派单未合并：`待开始`（实现中）、`待验收`、`待返工` | `编号` / `派单时间` / `预估时间` / `一句改动` |
| 已验证 | `已验证` | `编号` / `完成时间` / `一句改动` |

- **派单即移入**：「待开始」表 = 尚未派单；**派单时**把该行移入「进行中」表并填**派单时间**（不引入新状态）。
- **派单时间**：`YYYY-MM-DD HH:MM`，派单动作发生时由主会话填写。
- **预估时间**：人工估值，只作参考；格式 `N h` / `N–M h` / `N 天` / `N–M 天` / `N min`。
- **完成时间**：`YYYY-MM-DD HH:MM`；「已验证」表按完成时间**倒序**（同时间按编号升序）。
- **一句改动**：≤120 字符，只作索引，细节在任务书。

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| m14-linux-001 | 4–5 h | Linux 基线接入与补丁组件化（去 `patchless`、建空 series、`apply-series` 幂等） |
| m14-spec-001 | 6–7 h | 启动 ABI 契约：Vast 装载/入口状态/内存映射/固定 boot info 结构 |
| m14-spec-002 | 3–4 h | 内核侧 syscall/errno/TLS 契约（`rb3=rbtp`、clone/futex 原子性） |
| m14-infra-001 | 4–5 h | 工具链缺口矩阵 + `check-linux-toolchain` 门控 |
| m14-infra-002 | 5–6 h | initramfs（静态 musl init）+ semihosting 控制台/退出闭环 |
| m14-linux-002 | 6–7 h | `arch/dadao` 最小骨架，`make ARCH=dadao` 出 vmlinux（不要求启动） |
| m14-infra-003 | 4–5 h | K0 收口门控 `check-linux-k0`（vmlinux/initramfs/工具链矩阵/反例注入） |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
