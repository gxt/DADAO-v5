# 讨论项

> 只记**当前未决/待裁定**事项；任务流水看 `.tao/knowledge/milestones.md`，历史与已落实项不在此保留。

## 批次授权

- **2026-11-01 M11 gem5 批次**：B0 解码核心（`GEM5-004t`）+ B1–B7（按 G1 矩阵拆分，任务书待立）+ `SPEC-181t` 语义缺口收口。
- 范围：已接受的 G1 矩阵、FS+SE M11、按 `docs/Process-09` 复用测试；不新增跨模块修改（LLVM/QEMU/picolibc 仍不动）。
- 授权：批次内可直接创建任务书、建任务分支、`/dispatch`、验证、`/complete`、合并 master；不逐任务确认。
- 停止点：批次外新任务、新增/改变 SPEC/契约语义决策、跨模块修改、push、破坏性/硬件操作、验收标准变更。
- 任务仍须落盘 `.tao/tasks/` 且有 `milestones.md` 流水行。

## 待用户裁定：ADR

### SPEC-180t 的 ADR

- 状态：待用户裁定
- 结论：escape 合法偏移集 `{0,+4}` + `imms18[17:1]` SBZ ⇒ ILLI，按 `docs/Process-03` 命中外部契约变更/多方案/结论固化
- 下一步：逐条确认 decision 后再立 ADR；未确认前只保留为遗留

### 拟议 ADR：Linux bring-up charter（M12/后续，未落文件）

- 状态：方向已确认；ADR decision 文本待逐条确认（尚未落 ADR 文件）
- 已确认方向：Linux 7.2.10、单核 QEMU MVP、semihosting console + exit、Linux 阶段不引入 UART/cache/LLC、TLB 在 K3 定义、busybox 到 K4 后再说、0628 只参考不复制
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
- TLB：当前**无规范定义**（此前实现只覆盖 invalid，没有 fill）；按 Linux K3 先定义 fill/invalidate/ASID/fault 语义再实现
- `cfx_pmem_exist`：SEE 与 SBI 语义不一致
- UART：实例号/索引语义未定义（Linux 阶段暂缓，留 M12/后续）
- 下一步：确认哪些进入 M10 后/Linux 前任务；不恢复已删除的审计文件

## 当前优先：gem5（M11，PR #3）

- **任务批次（2026-11-02）**：`SPEC-181t`、`LLVM-142t`、`QEMU-078t`、`GEM5-005t`、`TESTCASES-090t` 已一次建齐；按依赖 dispatch，不再逐任务等。记录以 `milestones.md` 流水 + 各任务书为准。
- 用户 2026-11-01 裁定：现有 Linux 开发延至 M12 或后续；先完成 gem5，gem5 成为新里程碑 M11。
- 新模块：`gem5`，任务前缀 `GEM5-`；目录 `.tao/tasks/gem5/`。Linux 模块保留，恢复时再用。
- 工作方式：**不做 PR merge、不建 worktree**；在本仓库普通任务分支上按 DADAO 最新 spec 重写/整理补丁。
- 范围：**同时包含 FS + SE**；参考 0628 的 ADR-0010，**SE 先行、FS 后接**：SE 先建立快速 ISA/ELF/syscall 参考，FS 再做 Machine-01、boot ROM、模式移交、semihosting、PTW/TLB 等；两者复用同一 ISA/执行核心，但按最新 DADAO 规范重做。
- M11 收口：FS 与 SE 都通过，并完成 QEMU/gem5 对应模式的一致性门控。
- 测试：按 `docs/Process-09` 的 `inst/arch/unit/tset` 四 scope 调整；**不新建 `tests/gem5/` 平行体系**；gem5 只作为 system/user 后端，复用现有向量、bootrom、harness 和 case 清单；该合并的合并。
- QEMU/gem5 一致性：
  - **SE ↔ QEMU user**：`tset`（libc-test/llvm-ts/Embench）与用户态 E2E，比通过/失败/退出码/架构结果。
  - **FS ↔ QEMU system**：`inst`/`arch`/裸机 E2E，比架构结果/退出码，不比时序。
  - 不允许拿 gem5 FS 与 QEMU user 冒充一致；不同模式分别出结果矩阵。
- 约束：其它模块（LLVM/QEMU/picolibc/测试/基础设施）如需修改，先经用户同意；测试调整**单独立任务**，不与实现补丁混在一起。
- PR：`gxt/DADAO-v5#3`，标题“gem5: 提交 DADAO 裸机功能闭环里程碑（GEM5-008m）”，当前 **draft**、`mergeable=false`、`mergeable_state=dirty`。
- 分支：head `JeffffHu:DADAO-v5:pr/gem5-008m-milestone`，head commit `7ea82cfe…`；base 为 `gxt:master` 的 `c6fbcbae…`；差异约 **97 文件 / +7710 行**。
- 本地试合并（基于当前 master）冲突 **12 项**，主要来自 M10 归档后的任务删除、`tests/llvm` 迁 `tests/unit`、Makefile、LLVM/QEMU/picolibc 补丁、ADR 编号碰撞。
- 下一步：先做 M11 gap matrix（FS/SE 共用 ISA、FS/SE 分叉、测试复用/合并、其它模块依赖），再按最新 spec 重做 `components/gem5` 补丁与测试；不直接采用 PR 的旧计数/旧证据。
- M11 子阶段（参考 0628 ADR-0010 修订）：G0 gap/契约 → **G1 共用 ISA 核心 + SE** → **G2 FS 全系统** → G3 QEMU/gem5 双向一致性与测试收口 → G4 里程碑核验。SE 先行拿快速功能参考，FS 后接系统态；两者同属 M11。
- 0628 参考结论（仅参考，不复制代码）：ADR-0010 明确 **SE 先行、FS 留后**；先做 `SEWorkload`/`Process`、真实 ELF、RB1/栈、brk/mmap，再上 Machine-01/PTW/TLB/timer。已知坑：`SEWorkload` 与 `Process` 概念混淆、LLD 多段 ELF 装载、QEMU trampoline 的 RB1 不可照搬到 SE、RB bank/RegClass/rd0/rb0 语义、不要整体克隆 RISC-V arch 充当骨架。
- **语义复用禁令**：编码相同、助记符相同 **不等于** 语义可复用；每条指令必须从当前 `spec/`/`contracts/` 重新推导，单独核对操作数/结果/异常/FP 舍入/标志/内存副作用，并与 0628/PR 的变化逐条对照。G1 先产出“语义重导矩阵”，不得按旧 opcode 表直接搬运。
- 任务量粗估：G0 4–6；G1 SE + 共用 ISA 10–15；G2 FS 15–25；G3 测试/一致性 5–8；G4 1–2；合计约 **35–56**，以 G0 matrix 校准。
- **2026-11-02 裁定**：B7 收口后先做 `GEM5-013t` 全 264 条执行收敛，再进 G1 SE；SE 分阶段，静态 ELF/静态 tset 先行，动态链接、TLS、线程/futex 后补；M11 最终仍按 ADR-0048 D4 覆盖完整 tset，不降级。ADR-0048 原文待恢复或重新裁定。
- **2026-11-02 授权**：用户同意 ADR-0048 按现有讨论重建；同意 G1 任务链（`GEM5-013t` → SE 骨架/ELF/syscall/VMA-TLS/静态 tset → 动态/线程后补 → G2 FS）；不支持 syscall 默认失败报告、不静默忽略；该链内不再逐任务确认，只有新语义/跨模块/破坏性/push 才停。
- **2026-11-02 测试机 RAM 映射裁定**：分简单/复杂两个 profile。简单 profile：BootROM 保持 256 KiB / `0xffff_fffc_0000`–`0xffff_ffff_ffff` / 复位向量 `0xffff_ffff_0000`，其下放 4 MiB `cfx_power` SRAM，程序 image/rodata 由 loader 装入 SRAM，不塞 BootROM；覆盖 Embench 与完整 picolibc 测试集。复杂 profile：RAM 为物理 `[0, 64 MiB)`，hmon 直接驱动 cfx_pmem、建立一级页表（`SPF=0x01`）并在 hypv 下跑测试；`power → hmon → smon` 路径保留给内核/smon 测试；不做双映射，直接迁移并逐项修问题；不新立 ADR，修改 ADR-0004/0039/0040/0043 与 `spec/Machine-01`。

## Linux（M12 或后续，暂缓）

> 2026-11-01 用户裁定：现有 Linux 开发延至 **M12 或后续**；此前记录的方向在恢复时沿用，但不再作为当前里程碑。

### 已确认方向（2026-11-01，用户逐条确认）

- **模块归属**：新建 `linux` 模块，任务前缀 `LINUX-`；目录 `.tao/tasks/linux/`。
- **内核基线**：Linux **7.2.10**，commit `7b20d05f…`；不采用 5.4。
- **平台**：恢复时只做 QEMU system 模式，单核；**不纳入 gem5**。
- **MVP**：内核日志 → built-in initramfs 的静态 `/init` → 至少一次 Linux 系统调用往返；不要求 login/shell。
- **控制台**：**semihosting** 负责控制台输出与测试退出闭环；**不引入 UART**，不新增 cfx。
- **initramfs**：先放静态 musl 自定义 init（write/getpid/brk + 错误路径），**busybox 到 K4 之后再决定**，不预设进该阶段。
- **TLB**：当前**没有规范定义**（DDLN 只是讲义，不是规范）；K3 先定义 fill/invalidate/ASID/fault 语义，再实现；K0 不定义。
- **cache/LLC**：该阶段不引入，留到后续。
- **0628**：只参考阶段划分、踩坑和测试思路；不复制 `arch/dadao`、补丁或实现代码。

### Linux 补丁策略（待 K0 落任务书）

- 当前 `manifests/components.lock.toml` 的 `linux` 条目是 `patchless = true`，角色仅为 syscall 号表参考。
- 恢复时建议复用同一 7.2.10 commit，转为受补丁组件：`patch_dir = components/linux/patches`、`patch_series = components/linux/series`，角色改为“Linux 内核移植目标 + syscall 参考”。
- 按 `docs/Process-01`：`.work/source/linux` 为干净 git 基线；一文件一补丁；新增 `arch/dadao/**` 也用 `new file mode` 补丁；`make apply-series` + `check-source-state`。
- 不直接改 `.work/source/linux` 作为真源，不复制 0628 的补丁集。

### 阶段与任务量（K0 后校准）

- K0 基线与契约：5–7 个任务（补丁组件、工具链缺口、启动 ABI、syscall/errno/TLS、initramfs/semihosting、门控）。
- K1 启动与控制台：4–6 个。
- K2 异常与时间：5–7 个。
- K3 内存与 TLB：6–8 个（含 TLB 规范定义）。
- K4 进程与上下文：5–7 个。
- K5 用户态闭环：5–7 个。
- 合计约 30–42 个任务；Linux 阶段收口只到 K5，busybox/UART/cache/LLC/gem5 等不阻塞。

### 待办

- Linux 恢复时立定义与 K0 任务书（`linux` 模块）；拟议 ADR 的 decision 逐条确认。
- K0 前不写内核代码；先冻结补丁策略、启动 ABI、工具链缺口和测试门控。

### K0 兼容性缺口（待矩阵化）

- 兼容性缺口：`arch/dadao`、`llvm-ar/ranlib/strip`、`asm goto` 输出、栈保护、`.quad/.long/.short/.byte`、inline asm 约束、`-mcmodel=kernel`
- 入口判据：spike 清单归零或有规避法 + 工具链就位 + `arch/dadao` 最小骨架能 `make ARCH=dadao` 出 vmlinux
- 详细兼容性记录不在此展开；K0 落任务书/矩阵后移入对应文档

## 现行约定（非讨论项）

- 任务流水体例由 `make check-milestones-fresh` 机械校验（状态一致 / 覆盖 / ≤120 字符 / 倒序 / 格式），不在本文复述。
