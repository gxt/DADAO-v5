# M14 回顾 — Linux bring-up（K0–K5）

> **里程碑**：M14（2026-11-13 起，**2026-11-22 达成**）｜ **归档**：2026-11-22（`.tao/archive/M14/`）
> **性质**：本册是 M14 的**权威摘要**；任务细节在 `README.md §2` 指向的各任务书（本目录模块子目录）。
> **收口判据（用户 2026-11-20 修订）**：**K5 用户态闭环（`m14-linux-029`）+ K3 退役**即收口；**K6 移 M18**（`m18-linux-001`–`003`），M14 **不声称**「能当 Linux 用」。

## 1 定位与边界（用户 2026-11-13）

**Linux bring-up**：基线 Linux `7.2.10`，平台 = QEMU system 模式**单核 Vast**，控制台 = **semihosting**（不引入 UART、不新增 cfx），initramfs = 静态 musl `init`，启动传参 = **固定 boot info 结构**（不引入设备树）；TLB 规范在 K3 落地、K0 不定义；**不引入 cache/LLC**。参考实现（`DADAO` / `DADAO-0628`）只借鉴阶段划分与踩坑，`arch/dadao` 按当时冻结契约重写。

## 2 阶段推进（K0 → K5）

| 阶段 | 交付 | 代表任务 |
|---|---|---|
| K0 工具链/启动契约 | 补丁组件化（空系列首态 + make 目标）、工具链缺口矩阵、启动 ABI 契约（`ADR-0051`）、initramfs 与 semihosting 退出闭环、K0 收口门控（119→146 项） | `m14-infra-001/002/003`、`m14-spec-001`、`m14-linux-001` |
| K1 早期启动 | `arch/dadao` 骨架出 vmlinux（56 补丁）、到 `start_kernel`、自建页表 + 写 PTBR、K1 门控 | `m14-linux-002/003/004/005`、`m14-qemu-001` |
| K2 异常/时钟/中断 | 异常入口与 cause 分派、`cfx_time`/`cfx_hart` 最小时间框架、中断使能与屏蔽、K2 门控（104 项） | `m14-linux-006`–`009`、`m14-spec-005` |
| K3 页表/缺页 | 内核页表原语与 TLB 维护、页故障通道与按需分页、COW、栈增长（**后两者按裁定移至 K4**）、K3 门控（263 项） | `m14-linux-010`–`015`、`m14-spec-006/007` |
| K3 退役 | 用户 2026-11-20 裁定「每推进一个阶段，过时门控可随时退役」⇒ **K3 阶段整体退役**（`check-linux-k3` + `k3_*` 探针/自检 + 窗口臂），退役台账入 `docs/Process-07 §4a.2` | `m14-linux-029` |
| K4 进程/线程 | 进程抽象与 fork/execve、上下文切换与 U-mode 帧往返、COW、用户栈增长（并入 017）、clone/线程、futex 与原子性 | `m14-linux-016`–`020`、`025` |
| K5 用户态闭环 | 用户态 syscall 闭环、异常帧四组寄存器、clocksource/clockevent 通用框架、信号与退出面、**64 KiB ABI**、K5 收口门控（280 项） | `m14-linux-021`(退役)/`022`–`028`、`029`、`m14-infra-005` |
| 支撑批 | LLVM 7 册（工具族/SSP/patchable/DWARF/符号差/weak 重定位）、QEMU 7 册（smon 交接/semihosting 按 PA/cause 子原因/Vast 单路由）、SPEC 9 册、testcases 3 册 | `m14-llvm-*`、`m14-qemu-*`、`m14-spec-*`、`m14-testcases-005/006/007` |
| 收口与盘点 | 八份「内核 vs 主流 ISA」差异盘点（195 条）；两份「通用 mm / entry-exit 工作循环」回归整改 | `m14-linux-035`–`047` |

## 3 关键决策

- **启动面**：内核 VA 窗口 `[2TiB,3TiB)`（`ADR-0051`）；boot info 15 字段由 smon 建预建表；`escape` 恢复 `inner_cfx_code`（`cg5 rc1 = excp_prev_cfx_code`，`m14-spec-009`）。
- **同步/异步异常**：`cause_id` 子原因编码 18 位（CFXPERM/CFXMEM，`m14-spec-007`）；Vast 同步异常单路由进 monitor（`m14-qemu-006`）；IE 旋钮收敛为 monitor 单行（`m14-linux-010`，`ISS-454/455`）。
- **时间**：K2 只做 jiffies 最小框架；K5 升级到 `clocksource(cfx_time)` + `clockevent(cfx_hart)` 通用框架（`m14-linux-026` 接手 `021` 的正文）。
- **用户 ABI**：64 KiB 页（`AT_PAGESZ`/`mmap` 对齐/`PT_LOAD`/`brk`，`m14-linux-028`）；信号帧 2048 B 四组 + `SA_RESTORER`（`m14-linux-046` + `m14-infra-005` musl 侧）。
- **命名**：测试机整机名 `Machine-v5` → **`Kaiwu`**（`ADR-0055`；QEMU 串 `kaiwu-tiny`/`kaiwu-vast`，无旧名别名）。

## 4 终局证据（摘要；真实 rc 见 `README.md §3`）

- **K5 收口**：`make check-linux-k5` **rc=0、280/280**；`--selfcheck` 8 次翻转全 PASS；`--all-inject` 316/316。
- **不回归**：K0 146 / K1 112 / K2 170 / k4 cow 86 / switch 76 / stack 44 / kthread 112 全 rc=0。
- **既有偶发红**：`k4_fork_probe` F5（`ISS-493`，A/B 对照证明非本批引入）、`k4_kthread_probe` 竞态（`ISS-494`）——**登记不重试**，替代判据 = `check-linux-k5` 的 C/G 组。
- **归档门控**：`check-archive`、`check-milestones-fresh`（M15–M20）、`check_issues`、`check-knowledge-refs`、`check-dirs`、`check-no-residue` 全 rc=0（本归档任务现跑）。

## 5 退役与遗留

- **退役（`已验证` + `> **已退役**` 注记，不放宽门控）**：`m14-linux-021`（clocksource/clockevent 接线）未实施，正文由 `m14-linux-026` 原样接手落地——与 `013/014/019` 同形，**不新增状态**。K3 阶段对象（`check-linux-k3` 及 `k3_*` 探针）**整体退役**，非任务册。
- **早期按裁定退役**：`m14-linux-013`/`014`（COW / 栈增长移 K4）、`019`（并入 `017`）——同为 `已验证` + 退役注记，历史值不改写；理由见各自任务书与 `README.md §2` 的「一句改动」。
- **转交 M18（open 项，`issues.yaml` 已改 `milestone: M18`）**：`ISS-444`（K1 门控只能间接证明阶段顺序）、`ISS-457`（K2 两条断言缺可达 FAIL）、`ISS-486`（libc/内核措辞）、`ISS-487`（clocksource 静态断言与退役台账）、`ISS-488`（`TASK_UNMAPPED_BASE` 断言）、`ISS-493`（F5 偶发挂死）、`ISS-494`（kthread 时序竞态）。
- **本批关闭**：`ISS-470`（门控 `CONFIG` 钉子已修）、`ISS-482`（同节 weak 重定位，`m14-llvm-007` 修复）。
- **范围外**：pthread create/join 归 K6（`m14-linux-029` 按用户 2026-11-20 裁定范围 B 不做）。

## 6 教训

1. **阶段门控会随阶段过时**：K3 的页故障窗口在 K4/K5 已不成立 ⇒ 退役须**同时**写替代判据（`docs/Process-07 §4a`），否则留下恒真项。
2. **开发期 `CONFIG` 必须在所有门控镜像里显式钉 `n`**（`ISS-470`）：否则新开关会让探针镜像串味，产生假红/假绿。
3. **既有偶发红先做 A/B 对照再定性**：`ISS-493` 用「master vs 分支各 5 跑」把「本任务引入」与「既有缺陷」分开，避免为绿而加重试。
4. **`arch/dadao` 的差异盘点不能当判据**：八份盘点只做索引与分流，整改权归用户（`components/linux/kernel-diff-vs-mainstream-isa.md`）。
5. **归档不放宽门控、不新增状态**：未实施但内容由他册接手的册沿用先例——`已验证` + `> **已退役**` 注记（`m12-integ-003` 曾「按不放宽门控撤回」）；真相由注记承载，不靠第三态。

## 7 归档说明

- 任务书 **76** 册已 `git mv` 入本目录模块子目录（`infra`5 / `integ`1 / `linux`44 / `llvm`7 / `qemu`7 / `spec`9 / `testcases`3）；流水 76 条冻结在 `README.md §2`。
- 活台账 `.tao/knowledge/milestones-m14.md` 已删除、`Makefile` 的 `MILESTONES_M14` 已移除；`MEMORY.md` 纯 M14 滚动行已移除（摘要见 `README.md §4`）。
- 关闭 issue 快照 `issues-closed.md`（10 条）由 `tools/infra/archive_issues.py` 生成，`--check` 可复核。
