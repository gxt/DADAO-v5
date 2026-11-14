# m14-linux-003: K1 内核早期启动到 `start_kernel`（Vast）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-002`（vmlinux 骨架）、`m14-qemu-001`（Vast smon 交接）、`m14-spec-003`（VA 窗口）——均已验证
**可并行分片**：否
**预估**：2–3 h
**状态**：待开始

## 用户裁定（2026-11-14，原话）

> 「1、现在启动K1；内核所有开发都是在qemu-system vast上进行；…smon的时候应该就开启了PTBR，能进入start_kernel，开启时钟之前打印信息退出，我觉得K1就算完成」
> （控制台）「semihosting」

## 现状（K0 已完成，现场）

- Vast 上 `power → hmon → smon` 已通：smon 预建单超页表、`PTBR=0`、`ptw_enable=1`、VA 入口 `0x0200_0001_0100`、boot info 15 字段（`m14-qemu-001` 实测）；
- `vmlinux` 由 `arch/dadao` 骨架产出（56 补丁），能**进入内核窗口**但不自行退出（`m14-linux-002`）；
- 进入时：模式 `supv`、`rb17`=boot info VA、`rb16`=入口 VA、`rb3`=0、**SP 未定义**、异步中断全屏蔽（`ADR-0051 D6`）。

## 范围

1. `arch/dadao/kernel/head.S`：在任何栈使用前自建 **early stack**；保存 `rb17`（boot info VA）/`rb16`；按 `Machine-v5 §6.3` 解析 boot info 15 字段（校验 magic/version/size，非法即早退）；
2. 跳到 C 的 `start_kernel()`：本任务只要求"到达并打印"，**不做**子系统初始化；
3. **early console**：`supv` 下 `trap cfx, 0x3FF00` + semihosting `SYS_WRITE`/`SYS_WRITEC` 输出（**不引入 UART、不新增 cfx**）；打印内容至少含 `bootinfo.magic/version/kernel_size/hart_id` 与一行动工标记；
4. **退出**：在开启任何时钟/中断之前，用 semihosting `SYS_EXIT(0)` 正常退出（K1 的判据边界就到这里）。

## 验收（逐条贴真实输出）

1. **端到端**：`make build-linux`（或等价目标）产出 vmlinux；在 `dadao-vast` 上以 `bootrom-image + -kernel` 启动，**guest rc=0**；
2. 输出**逐行可核**：至少一行 `K1 bootinfo magic=… version=… size=… hart=0`，且值与构建参数一致（不写死）；
3. **进入 `start_kernel` 的证据**：在 `start_kernel` 首行打印标记（如 `start_kernel`），或提供等价的可观测证据；
4. **栈自建证据**：SP 未定义进入 ⇒ `head.S` 在第一次压栈前设好 SP（代码 + 运行时打印 SP 值）；
5. **boot info 负例**：构造 magic 错 / size 错的 boot info（改 smon 侧或用探针镜像），内核应**具名拒绝并退出非零**，不得跑进 `start_kernel`；
6. 可达 FAIL 注入 ≥2 路（破坏 boot info 校验；把 early console 的 SYS_WRITE 参数块改错 ⇒ 输出乱/无输出），`cp`+md5 还原；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`**；`build-linux` 可用（`JOBS=32`），**禁边构建边测试**。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `components/linux/**`（`arch/dadao` 补丁）、`components/linux/changelog.md`、`tools/linux/**`（探针/门控如需）、必要时 `tools/qemu/k0_boot_probe.py` 的 **K1 模式**；**不改** `spec/`、`contracts/`、`tests/**`、QEMU/chipyard RTL。
5. **只在 `qemu-system vast` 上开发与验收**（内核不跑 Tiny）；派前查节点/主控机资源，测试与构建不并行。

## 待裁定

（实现中写）

## 审阅记录

（待填）
