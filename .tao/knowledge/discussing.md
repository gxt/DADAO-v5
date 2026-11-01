# 讨论项

> 只记**当前未决/待裁定**事项；任务流水看 `.tao/knowledge/milestones.md`，历史与已落实项不在此保留。

## 待用户裁定：ADR

### SPEC-180t 的 ADR

- 状态：待用户裁定
- 结论：escape 合法偏移集 `{0,+4}` + `imms18[17:1]` SBZ ⇒ ILLI，按 `docs/Process-03` 命中外部契约变更/多方案/结论固化
- 下一步：逐条确认 decision 后再立 ADR；未确认前只保留为遗留

### 拟议 ADR：M11 Linux bring-up charter（未落文件）

- 状态：方向已确认；ADR decision 文本待逐条确认（尚未落 ADR 文件）
- 已确认方向：Linux 7.2.10、单核 QEMU MVP、semihosting console + exit、M11 不引入 UART/cache/LLC、TLB 在 K3 定义、busybox 到 K4 后再说、0628 只参考不复制
- 下一步：把上述方向写成 D1–D7，逐条确认后再落正式 ADR；当前只在 discussing 记录

### ADR 状态

- `ADR-0043`/`0045`：已 `Accepted`
- `ADR-0046`：仍 `Proposed`，等 Linux 实测后再收口
- 下一步：不再改 0043/0045 的 decision；0046 保持 `Proposed`

## 待立项 / 后续

### M10 后的 cfx 范围

- 已实现：umon/jmon/smon/hmon/ptw/pmem/time/hart/power
- 后置：cache/llc/uart、PMEM 区域分配、IPI、多 hart
- 下一步：M10 收尾后按 Linux 需求拆任务

### U-mode / cg5 / 异步帧

- 状态：待讨论
- 结论：U-mode 的 cfx 目标不设 ISA 限制，由 OS 策略决定；cg5 单帧、同步/异步分离、递归/重入尚未定
- 下一步：等 cg7 与 escape 收口后再讨论

### SBI 生产 provider / W1C

- 状态：后置
- 结论：当前只有测试专用 provider；生产 provider、`DONE/ERROR` W1C、`WAIT` 属 Linux 集成阶段
- 下一步：不在 M10 通路内实现

### TESTCASES-089t 遗留

- `reserved.yaml` 是否拆册（当前同册承载「保留编码 ⇒ UNDI」与「reserved cfx 地址空间 ⇒ CFXMEM」两类语义）
- `trap`/`escape` → reserved cfx 的 active 向量仍 deferred（`TESTCASES-033t`）

### CFX 审计保留的未决项

- IPI：只有接收端，没有发送服务/寄存器
- TLB：当前**无规范定义**（此前实现只覆盖 invalid，没有 fill）；按 M11 K3 先定义 fill/invalidate/ASID/fault 语义再实现
- `cfx_pmem_exist`：SEE 与 SBI 语义不一致
- UART：实例号/索引语义未定义（M11 不引入，留 M12）
- 下一步：确认哪些进入 M10 后/Linux 前任务；不恢复已删除的审计文件

## 下一里程碑：M11 Linux（单核 MVP）

### 已确认方向（2026-11-01，用户逐条确认）

- **模块归属**：新建 `linux` 模块，任务前缀 `LINUX-`；目录 `.tao/tasks/linux/`。
- **内核基线**：Linux **7.2.10**，commit `7b20d05f…`；不采用 5.4。
- **平台**：M11 只做 QEMU system 模式，单核；**不纳入 gem5**。
- **MVP**：内核日志 → built-in initramfs 的静态 `/init` → 至少一次 Linux 系统调用往返；不要求 login/shell。
- **控制台**：**semihosting** 负责控制台输出与测试退出闭环；**不引入 UART**，不新增 cfx。
- **initramfs**：先放静态 musl 自定义 init（write/getpid/brk + 错误路径），**busybox 到 K4 之后再决定**，不预设进 M11。
- **TLB**：当前**没有规范定义**（DDLN 只是讲义，不是规范）；K3 先定义 fill/invalidate/ASID/fault 语义，再实现；K0 不定义。
- **cache/LLC**：M11 不引入，留到 M12/后续。
- **0628**：只参考阶段划分、踩坑和测试思路；不复制 `arch/dadao`、补丁或实现代码。

### Linux 补丁策略（待 K0 落任务书）

- 当前 `manifests/components.lock.toml` 的 `linux` 条目是 `patchless = true`，角色仅为 syscall 号表参考。
- M11 建议复用同一 7.2.10 commit，转为受补丁组件：`patch_dir = components/linux/patches`、`patch_series = components/linux/series`，角色改为“Linux 内核移植目标 + syscall 参考”。
- 按 `docs/Process-01`：`.work/source/linux` 为干净 git 基线；一文件一补丁；新增 `arch/dadao/**` 也用 `new file mode` 补丁；`make apply-series` + `check-source-state`。
- 不直接改 `.work/source/linux` 作为真源，不复制 0628 的补丁集。

### 阶段与任务量（K0 后校准）

- K0 基线与契约：5–7 个任务（补丁组件、工具链缺口、启动 ABI、syscall/errno/TLS、initramfs/semihosting、门控）。
- K1 启动与控制台：4–6 个。
- K2 异常与时间：5–7 个。
- K3 内存与 TLB：6–8 个（含 TLB 规范定义）。
- K4 进程与上下文：5–7 个。
- K5 用户态闭环：5–7 个。
- 合计约 30–42 个任务；M11 收口只到 K5，busybox/UART/cache/LLC/gem5 等不阻塞。

### 待办

- 立 M11 定义与 K0 任务书（`linux` 模块）；拟议 ADR 的 decision 逐条确认。
- K0 前不写内核代码；先冻结补丁策略、启动 ABI、工具链缺口和测试门控。

### K0 兼容性缺口（待矩阵化）

- 兼容性缺口：`arch/dadao`、`llvm-ar/ranlib/strip`、`asm goto` 输出、栈保护、`.quad/.long/.short/.byte`、inline asm 约束、`-mcmodel=kernel`
- 入口判据：spike 清单归零或有规避法 + 工具链就位 + `arch/dadao` 最小骨架能 `make ARCH=dadao` 出 vmlinux
- 详细兼容性记录不在此展开；K0 落任务书/矩阵后移入对应文档

## 现行约定（非讨论项）

- 任务流水体例由 `make check-milestones-fresh` 机械校验（状态一致 / 覆盖 / ≤120 字符 / 倒序 / 格式），不在本文复述。
