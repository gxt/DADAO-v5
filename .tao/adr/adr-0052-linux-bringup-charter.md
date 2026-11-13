# ADR-0052: Linux bring-up 宪章（基线、平台、控制台与阶段边界）

**状态**：Accepted（2026-11-13 用户逐条确认 `D1`–`D7`；同日确认 `D5` 四项基线、`D2` gem5 只读对照、`D6` 措辞与 `D7` 纪律）
**日期**：2026-11-13
**接受日期**：2026-11-13
**关联**：ADR-0025（M8 Linux 用户态路线，`D1`/`D2`）、ADR-0051（Linux 启动 ABI，`D1`–`D8`）、ADR-0008（QEMU 基线）、ADR-0047/ADR-0048（gem5 基线与一致性）、ADR-0049（测试运行环境分层）、ADR-0020/ADR-0038（semihosting）、ADR-0011（exit-port，本 charter 不采用）；`spec/Machine-v5` `§1`/`§5`/`§6.3`、`spec/DADAO-12` `§2.2`/`§4.5`、`spec/DADAO-21` `§4`；`.tao/contracts/contract-linux-boot.md`（0.2.0）、`contract-semihosting.md`、`contract-syscall.md`（0.10.0）；任务 `m14-linux-001`、`m14-linux-002`、`m14-qemu-001`、`m14-spec-001`–`m14-spec-003`、`m14-infra-001`–`m14-infra-003`；台账 `.tao/knowledge/milestones-m14.md`

## Context（背景）

M14 = **Linux bring-up**（用户 2026-11-13 定位）：首次把 Linux 内核移植到 `Machine-v5-Vast`，阶段划分 K0 基线与契约 → K1 启动与控制台 → K2 异常与时间 → K3 内存与 TLB → K4 进程与上下文 → K5 用户态闭环。此前 M8（ADR-0025 `D2`）刻意**无内核**，只做 musl + QEMU user 的 Linux 用户态栈；M14 首次引入内核、SEE 异常路由、页表与用户态切换，涉及 `linux` / `spec` / `qemu` / `infra` / `testcases` 多模块，且多项值（基线、平台、控制台、MVP）一旦冻结再改代价高，命中 `docs/Process-03` 判据 1–6（高代价、跨模块、多方案、外部依赖、结论固化、定位）。

**方向来源**：`.tao/knowledge/discussing.md`「M14：Linux bring-up」节，用户 2026-11-01 逐条确认（模块归属、7.2.10、QEMU 单核、semihosting、initramfs、TLB 后置、0628 只参考）。本 ADR 把该方向固化为 `D1`–`D7`，并于 2026-11-13 经主会话问答逐条确认后转 `Accepted`（`AGENTS.md`「ADR decision 逐条确认」）。

**分工**：本 ADR 只承载**方向、边界与取舍**。启动字段/地址/进入态归 `spec/Machine-v5 §6.3` 与 `contract-linux-boot.md`（决策见 ADR-0051）；syscall/errno/TLS 归 `contract-syscall.md`（`§1`、`§8`–`§11`）；semihosting 归 `spec/Machine-v5 §5` 与 `contract-semihosting.md`；编码/ABI 归 `spec/SimRISC-*`、`spec/DADAO-21`、`contract-abi.md`、`contract-elf.md`。本文不复制规范正文。

**已落地前提**（避免把已完成项重复决策）：`m14-linux-001` 已把 `linux` 转为受补丁组件（空补丁集首态）；`m14-spec-001`/`m14-spec-003` 已冻结启动 ABI 与内核 VA 窗口 `[2 TiB, 3 TiB)`；`m14-infra-002` 已交付确定性 newc initramfs 与 semihosting 退出闭环；工具链缺口矩阵见 `m14-infra-001`。

## Decision（决策）

- **D1 基线锁定 Linux `7.2.10`，由 `linux` 模块以受补丁组件承载**：内核基线的版本身份固定为 commit `7b20d05fd38de8e0be168956f6fd241d750c7d69`（annotated tag `v7.2.10` 的 peel commit，锁在 `manifests/components.lock.toml` 的 `linux` 条目）；模块归属 = `linux`（任务 `mNN-linux-NNN`，任务书落 `.tao/tasks/linux/`）；不采用 5.4，版本身份只认 commit，不以 tag/分支作锁定依据。
  - 理由：syscall 号表契约已按该 commit 锁定（`contract-syscall.md §1.2`）；补丁组件形态已就绪（`m14-linux-001`）；5.4 是参考实现（0628）的时代基线，其号表/ABI/补丁形状与 v5 冻结口径不同，切换等于重做 K0 且需重新锁定号表。
  - 被否：内核 5.4（旧基线、为迁就外部补丁形状）；以 tag/分支作版本身份（可移动、不可复现，违 component lock）。
- **D2 平台与范围 = QEMU system 模式、`Machine-v5-Vast`、单核**：M14 只在 QEMU system 模式上运行内核，仅 `hart_id = 0` 在线；**不纳入 gem5**（M14 期间 gem5 只作只读对照、不投入，不废止 ADR-0047/ADR-0048），不引入多核/SMP 启动与停核协议。
  - 理由：只有 system 模式能承载 SEE、页表、异常与用户态；gem5 基线（ADR-0047/0048）仍在，但 M14 出口不依赖它，移植平台模型与维持双平台一致性在 K0–K5 无回报；SMP 协议在 `spec/Machine-v5 §6.3` 显式不定义，单核足以验证全部出口判据。
  - 被否：gem5（额外平台移植 + 双引擎一致性成本，且性能/统计不是 M14 目标）；QEMU user（无内核/无异常/无页表，属 M8 路线）；SMP 与多核启动（无规范、无收益）。
- **D3 启动与 ABI 只消费 ADR-0051 的冻结契约**：内核装载与进入一律按 `spec/Machine-v5 §6.3` + `contract-linux-boot.md` 的 M1 模型（smon 预建页表、VA 入口、固定 boot info）；本 charter 不新增、不改写任何启动字段或地址；新增需求须按 `size` 向前兼容扩展或**新增 ADR**。
  - 理由：启动 ABI 已 `Accepted` 且四处同笔（spec / 人读契约 / `contracts/linux-boot.yaml` / 检查器），charter 重述会造第二真源；`ptw_enable = 0` ⇒ `CFXMEM` 的硬约束决定了「进入前表已就绪」不是选项而是前提（ADR-0051 `D6`）。
  - 被否：在 charter 中重述地址/字段（必然漂移）；内核自建首张页表或引入设备树（受 `CFXMEM` 限制、K0 无枚举对象，ADR-0051 `D6`/`D8` 已否）。
- **D4 控制台与退出闭环只用 semihosting**：内核日志、`/init` 输出与测试结论全部经 semihosting（`spec/Machine-v5 §5`、`contract-semihosting.md §1`–`§5`）输出，测试以 `SYS_EXIT` 固定码闭环；M14 **不引入 UART、不新增 cfx**，不使用 exit-port。
  - 理由：semihosting 是 M5 起的既有契约、QEMU 已实现，测试机无需设备枚举；UART 需要新 cfx/设备模型/中断路由与绑定，K0 无收益；确定性退出必须走 `SYS_EXIT`（ADR-0020 `D8` 已取代 exit-port）。
  - 被否：8250 UART（新 cfx + 设备 + 中断）；SBI console（K0 无 SBI 服务面，ADR-0051 `D6` 已否）；exit-port（`ADR-0004 D3` 已被 ADR-0020 `D8` 取代，且需 MMIO 设备）。
- **D5 initramfs 内建、用户态 MVP 只到最小 syscall 往返**：initramfs 为**内核内建**的确定性 `cpio` newc（上限按 `contract-linux-boot.md §2`），内容为静态 musl 的 `/init`；M14 用户态出口 = 内核日志 → `/init` → **至少一次 syscall 往返**（实现基线 = `write`/`getpid`/`brk`/`exit_group` 四项，含错误路径；不设硬限制、不得滥用），不要求 login/shell；busybox 在 K4 之后再决定，不作 M14 出口条件。
  - 理由：内建 initramfs 免块设备与文件系统驱动；静态 musl 免动态链接器；最小 syscall 集即可证明「异常进入 → 内核处理 → 返回用户态」闭环；号表/errno/TLS 已有内核侧契约（`contract-syscall.md §8`–`§11`）。
  - 被否：外置 rootfs/块设备（驱动 + FS 成本，K0 无收益）；busybox 进 K0（体积、依赖与诊断面扩大）；动态链接 init（需 ldso 与 TLS 运行期，属 M8 另一条线）。
- **D6 TLB 在 K3 先定义后实现；cache/LLC 不在本 charter 内**：K0–K2 不定义也不实现 TLB 的 fill/invalidate/ASID/fault 生命周期语义（只消费 smon 预建的映射）；K3 的**第一步**是在 `spec/` + `contract-*` 定义该语义（含门控），**第二步**才实现；cache/LLC 在 M14 内不引入（`cfx5` 保持「已分配未实现」）。
  - 理由：v5 侧尚无 TLB 的可执行规范（`spec/Machine-v5 §6.3` 显式排除 TLB 填充/失效/ASID；`spec/DADAO-12 §2.2`/`§4.5` 是上游核行为描述，尚未收编为 v5 契约与门控；`docs/DDLN/C-资源管理/DD-C006-资源管理--TLB与地址转换维护.md` 只是讲义）；先定义再实现可避免 QEMU 与内核各自猜；cache 缺维护指令与一致性模型，引入会把 K0 拖入非必要面。
  - 被否：按 DDLN 讲义直接实现（讲义不是规范正文）；K0 顺手定义 TLB（把未验证能力写进冻结契约，与 ADR-0051 `D8` 同理）；M14 内引入 cache/LLC（无契约、无收益）。
- **D7 参考仓库只读、只借鉴阶段与踩坑、不复制实现**：`DADAO-0628`/`DADAO` 只经 `.cache/refs/**` 只读访问（由 `manifests/` 锁定 commit 幂等重建），只用于**阶段划分、踩坑与测试思路**的对照；不复制 `arch/dadao` 代码、补丁集或实现细节，也不采用其地址/镜像格式/移交方式（如 `0x8000_0000`、flat Image、ROM handoff）。
  - 理由：v5 的启动 ABI（VA 偏置、boot info、semihosting）与参考仓库不同，复制会把外部假设带进契约；补丁集必须能按 `docs/Process-01` 一文件一补丁重建；`AGENTS.md`「参考来源与任务自包含」要求参考内容标「内容溯源，非执行必需」，不得作执行依赖。
  - 被否：直接移植 0628 补丁（契约漂移、不可审计）；与参考实现双真源并行（维护两套、门控无法判定）；把参考仓库当执行依赖（fresh clone 不可复现）。

## Rationale（理由）

- **先定边界，再定值**：charter 只回答「用哪条基线、跑在哪个平台、谁提供控制台、做到哪一步、哪些能力后置、参考仓库怎么用」；具体字段值仍由已冻结的 `spec/`/`contract-*` 承载，避免 ADR 与规范双真源。
- **每一项都可由门控机械判定**：基线 = manifest 的 commit；平台 = QEMU 单核启动配置；控制台 = semihosting 调用与 `SYS_EXIT` 码；MVP = init 的 syscall 轨迹；TLB = K3 的 spec/contract 存在性与门控；参考纪律 = 补丁集可重建且与 0628 无复制关系。
- **与既有决策自洽**：不推翻 ADR-0025（Linux 语义映射）、ADR-0051（启动 ABI）、ADR-0049（运行环境归属）、ADR-0047/0048（gem5 基线仍有效，只是不在 M14 路径上）。
- **最小化 K0–K5 面**：UART、cache/LLC、busybox、SMP、gem5 全部显式排除，避免「顺手支持」把未验证能力写进冻结契约。

## Consequences（影响）

- **K0 出口**：`linux` 组件可重建（空/非空补丁集按 `docs/Process-01`）；工具链缺口矩阵无 blocker；`arch/dadao` 最小骨架能出可解析 vmlinux；启动 ABI 检查器绿。K0 不定义 TLB、不引入 UART/cache。
- **K1–K2**：QEMU 侧最小 smon 按 ADR-0051 建表并移交；内核侧只消费进入态；控制台与退出全部走 semihosting，门控须能从宿主观测 `SYS_EXIT` 码且与 guest 侧语义一致。
- **K3**：新增 TLB 规范正文与契约投影（fill/invalidate/ASID/fault）是**实现的前置**；未落地前不得以「参考仓库有实现」为由先行编码。
- **K4–K5**：进程/上下文与用户态闭环按 `contract-syscall.md §8`–`§11`；busybox、UART、cache/LLC、gem5、SMP 均不阻塞 M14 收口，后续若引入须各自新增 ADR。
- **演进约束**：基线、平台、控制台、MVP 边界任一变更 ⇒ 新增 ADR 或标注本 ADR `Superseded`；不得就地改写 `D1`–`D7` 的语义（经用户授权的修订须在「状态说明」留原话摘要与渠道）。

## 状态说明

- **确认记录（2026-11-13，渠道 = 主会话问答）**：`D1`–`D7` 全部确认，本 ADR 由 `Proposed` 转 `Accepted`。
  - 方向已在 2026-11-01 逐条确认（模块归属、7.2.10、QEMU 单核、semihosting、initramfs、TLB 后置、0628 只参考）。
  - 2026-11-13 经主会话问答逐条确认 `D1`–`D7`，并确认四项调整：① `D5` syscall 实现基线 = `write`/`getpid`/`brk`/`exit_group`，**不设硬限制**（「别滥用」）；② `D2` M14 期间 gem5 **只作只读对照、不投入**，不废止 ADR-0047/ADR-0048；③ `D6` 按「上游行为描述、尚未收编为 v5 契约」表述（TLB 当前无 v5 规范定义，K3 先定义再实现）；④ `D7` 保持「0628/DADAO 只读、不复制」。
  - 用户原话摘要：「立 ADR（推荐）」「四项基线（推荐）」「gem5 只读对照（推荐）」。
  - 任务前缀口径：`mNN-linux-NNN`（`discussing.md` 旧文 `LINUX-` 属历史，本 ADR 不引用）。
- 本 ADR 不承载规范正文：字段、地址、进入态、semihosting 服务表、syscall 号表分别以 `spec/Machine-v5 §6.3`、`contract-linux-boot.md`、`spec/Machine-v5 §5`、`contract-semihosting.md`、`contract-syscall.md` 为准。
- 决策变更时**新增 ADR 或标注 `Superseded`**；经用户授权的**就地修订**须在本节记录授权原话摘要与渠道。
