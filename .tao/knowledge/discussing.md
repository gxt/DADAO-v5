# 讨论项

> **组织方式（用户 2026-11-08）**：按里程碑分节，**M12 / M13 / M14** 各为一级标题；M11 已归档（仍有效的口径见「跨期口径」）；**不在这些里程碑内**的事项集中到「三个里程碑之外」。
>
> **维护规则（2026-11-13）**：本文件**只记** ① 当前未决 / 待裁定；② **仍然生效**的口径。裁定一旦落成 `spec/`、ADR、任务书或 `AGENTS.md`，**从本文件删除**（git 历史可回溯）；过程快照、已完成任务的方案叙述、过期队列状态一律不留。任务流水看 `milestones-m12/m13/m14.md`，历史见 `.tao/archive/`。

# 跨期口径（M11 收口后仍有效，M12/M13 共用）

> M11 已于 2026-11-09 归档（`.tao/archive/M11/`，114 册）；其任务与历史裁定不再在此保留。

- **QEMU/gem5 一致性方向**：QEMU 已实现的 syscall，gem5 必须有等价实现；差异不是「可接受限制」；gem5 通过而 QEMU 未通过不得直接接受，须定位到一致。
- **环境缺口（5 例）**：`popen`/`spawn`/`vfork`/`execle-env`/`unix-smail` 需要 guest 根内的 DADAO `/bin/sh`、`echo`；SE 返回 `ENOEXEC` 正确。QEMU 侧「通过」是执行宿主 x86-64 二进制，**非同架构 baseline**，不计 gem5 能力欠账；不采纳宿主原生执行旁路。
- **SE 动态线边界**：`mprotect` 真权限不建模；主程序 `-pie`/`ET_DYN` 不支持（用非 PIE `ET_EXEC+PT_INTERP`）；语料按 `ADR-0048 D4` 全量；单线程 TLS 由 musl 完成。
- **`SYS_TICKFREQ`**：统一 `1e9` ticks/秒（spec 未定义具体值，暂按此对照；M13 差分时可固化）。
- **`SYS_chmod` 不新增号段**：`chmod()` 经 musl 走 `fchmodat`，不虚构 ABI 号。
- **输出捕获的 stdout/stderr 顺序（`ISS-357`）**：至少 4 例受影响，修复必须保留 fd1/fd2 写序，不能只交换拼接方向。

# M12：chipyard 上跑 `Machine-v5-Tiny`（收口中）

> 已完成 34 项；剩 `m12-chipyard-028`（重生成 bootrom hex）、`029`（FMA RTL）、`016`（T0 冒烟）、`017`（T1 + 验收）。方案细节见任务书与 `components/chipyard/README.md`。

## M12 未决

- **口径残留（`spec-003`/`spec-004` 未覆盖项）**：
  - #9 `cfx2rd`/`cfx2rc` 到**保留** cfxha ⇒ `ILLI`（`Machine-v5` 现只说「不存在 cfx 寄存器 ⇒ `CFXREG`」，与 `DADAO-12 §5.2(一)` 冲突）
  - #10 reserved 集统一（正文 `19–61` vs 附录 0.4.0 `16–31、35–61`）
  - #6 退出码由 hmon handler 生成（`§7.1` 只定编码、未定生成方）
  - #3 Tiny 的 hmon 镜像装载路径（与 R13 绑定）
  - （`m13-qemu-001` 新增）`excp_cause_info` 覆盖：`Machine-v5 §4.4` 5 项 vs `DADAO-13 §2` 11 项
  - （`m13-gem5-001` 新增）`escape` 返回 cfx 取自「异常帧」，但寄存器表无 `prev_cfx` 保存寄存器（实现镜像 QEMU/Node 保持目标 cfx）
  - （`m13-gem5-001` 新增）Tiny `cfx_power` 的 cg7（BootROM start/size）与 `cg8 rc1`（power ctrl，WO）无正文
  - （`m13-gem5-001` 新增）Tiny `switch_run_mode` 写非 hypv 值：寄存器 RW 但无强制路径
- **`spec-004` 候选**：Vast 的同步异常仍是 staged 机器 fault（`DADAO-12 §5.2(一)` 要求进向量），5 个 arch 探针 oracle 依赖旧口径；统一需同步改 qemu/gem5 + 探针。

---

# M13：三平台差分对齐（qemu / gem5 / chipyard，含浮点）

## 范围

- **三平台差分**：qemu / gem5 / chipyard 的**指令语义**对齐，**尤其是浮点**语义。
- **riscv-tests**：移植与调整在 M13 完成（M12 不用）。
- 判据仍是「实现之间一致 + 与 spec 逐条核对」；**不允许把「两个实现一致」当正确**（多数表决 ≠ 真值）。

## M13 起点：gem5 超时与运行时间可比性（用户 2026-11-09 裁定）

- **用户原话**：「M13准备专门进行多方测试的差分对比，可以先从gem5的超时问题做起，放到208节点机上，48并行（甚至60并行，你觉得呢）；建立专门的任务，跑3600s，甚至7200s，我们测试一下qemu和gem5的运行时间的比率，对不同的任务是否具有可比性。该任务（或者你可以分解多个任务）不修改源码，不做调试，只记录结果；我来对结果进行分析和裁定。」
- **并行度结论**：**48**（留 16 核给内核/IO）；60 会引入调度/带宽争用，污染时间测量。若 3 例 × 2 次方差 < 5%，再考虑提高。
- **任务分解**：`m13-testcases-001`（static 72 例 × 3600s）、`m13-testcases-002`（dynamic 93 例 × 3600s）、`m13-testcases-003`（3600s 仍超时的例 × 7200s）。
- **只记录不改源码**：这三个任务不做根因分析、不调试；结果由用户分析裁定。
- **M13 台账**：新建 `.tao/knowledge/milestones-m13.md`（`项目里程碑 = M13`），Makefile 的 `check-milestones-fresh` 扩展为校验 M11 + M12 + M13。

## golden / Sail 定位（结论，待落流程）

- **前提**：SimRISC/DADAO 持续变更、不留历史包袱；内核/FPGA 阶段同样如此。工具按「高频变更」取舍，不按「稳定期资产」取舍。
- **Sail：搁置**。形式化模型是稳定期资产；0628 实测只做 6–8 条切片、其余 `SKIP-unsupported`；「权威性」在自有扩展上不成立。重启触发条件：ISA 冻结 / 流片前 / 需要 RTL tandem 或定理证明。
- **golden：不做全量第四实现**。只保留三个窄用途：① 歧义探测（未明处 `SpecificationGap`/`UNSPECIFIED` 显式阻断，不猜默认值）；② 精确计算（FP/位宽/舍入）；③ 裁定回归（把用户裁定固化成向量/断言，防漂移）。PR#5 的全量模型 + 万行 `INSTRUCTION_REFERENCE.md` 属稳定期资产，不并入日常门控。
- **裁判只能是用户**：工具只做「发现歧义 + 举证（各解释下的结果/依据）+ 回归」，不做拍板；差分/fuzz 的分歧须聚类归因后再上报，不把原始分歧直接丢给用户。
- **投资顺序**：规范一致性/歧义探测 > 差分 fuzz + legality 矩阵 > 精确 FP > 轻量边界生成；解释器只在「需要算给看」时写。
- **三条禁忌**：向量里写未记录来源的期望值；模型对未明处选默认值；把「两个实现一致」当正确。
- **依据（0628 / PR#5）**：0628 四方差分（interp/QEMU/gem5/Sail）AGREE 198 / DIVERGE 0，`check-golden` 故意不进 `make check`；golden 仅整数 87 条，语义取自 `spec.md`（与 ADR-0009「wiki 直派」的要求不一致）。PR#5：标量 + 66 条 FP，回放 730（173/500/0/57），49 单测，`check-golden` 进 L1；无差分运行器，FP 向量只有 `scaleb`。
- **待落地**：① 「歧义登记 → 用户裁定 → ADR/向量 → 回归」的流程；② 是否把「歧义探测」并入现有 spec 门控；③ chipyard 是否已有 DADAO 核（决定 RTL 对拍是否成为主差分）。

## 第一阶段目标（用户 2026-11-09）

- **先定义每条指令的完整且准确的语义**（尤其浮点：舍入方向、异常标志、NaN 传播、边界值）。
- **再重新生成 `tests/inst` 的测试程序**，重点是各种边界。
- 之后才做三平台差分（`m13-integ-002`/`003`）。

## M13 未决

- 差分矩阵的判据、参与引擎、失败归因口径（启动 M13 时专门讨论）。
- **3600s 长尾结论（2026-11-10，`m13-testcases-001` 全量）**：72/72 例 gem5 SE 仍超时，qemu 72/72 全 pass；最小例（qemu 0.0 s）也吃满 3600 s ⇒ 疑挂死而非慢（`ISS-361`）。
  ~~待用户定 7200s 还是定位挂死~~ **已定（2026-11-10）**：按 qemu 时耗 30 s 分 A/B 组——A 组 7200 s（60 例，已出结果 40 pass/17 blocked/3 fail），B 组无上限（90 例，进行中）。
- **3600s 长尾结论（2026-11-10，`m13-testcases-002` 全量 dynamic）**：93 例中 gem5 **78 blocked / 14 pass / 1 fail**，比值 `n=12`（min 172、median 289、max 1942）；
  qemu 93/93 pass。⇒ dynamic 有一小部分可测、static 全不可测。`neural` 为 gem5 侧 oracle mismatch（`ISS-362`）。

---

# M14：Linux bring-up

> 2026-11-01 用户裁定：Linux 开发延至 M12 或后续；**现定为 M14**（三线分开进行）。此前方向沿用。

## 已确认方向（2026-11-01，用户逐条确认）

- **模块归属**：新建 `linux` 模块，任务前缀 `LINUX-`；目录 `.tao/tasks/linux/`。
- **内核基线**：Linux **7.2.10**，commit `7b20d05f…`；不采用 5.4。
- **平台**：恢复时只做 QEMU system 模式，单核；**不纳入 gem5**。
- **MVP**：内核日志 → built-in initramfs 的静态 `/init` → 至少一次 Linux 系统调用往返；不要求 login/shell。
- **控制台**：**semihosting** 负责控制台输出与测试退出闭环；**不引入 UART**，不新增 cfx。
- **initramfs**：先放静态 musl 自定义 init（write/getpid/brk + 错误路径），**busybox 到 K4 之后再决定**。
- **TLB**：当前**没有规范定义**（DDLN 只是讲义，不是规范）；K3 先定义 fill/invalidate/ASID/fault 语义，再实现；K0 不定义。
- **cache/LLC**：该阶段不引入，留到后续。
- **0628**：只参考阶段划分、踩坑和测试思路；不复制 `arch/dadao`、补丁或实现代码。

## 补丁策略（已由 `m14-linux-001` 承载）

- 口径不变：复用同一 7.2.10 commit 转受补丁组件（`patch_dir`/`patch_series`）、按 `docs/Process-01` 一文件一补丁、不直接改源树作真源、不复制 0628 补丁集。落地细节见任务书。

## 阶段与任务量（K0 后校准）

- K0 基线与契约：5–7 个任务（补丁组件、工具链缺口、启动 ABI、syscall/errno/TLS、initramfs/semihosting、门控）。
- K1 启动与控制台：4–6 个。
- K2 异常与时间：5–7 个。
- K3 内存与 TLB：6–8 个（含 TLB 规范定义）。
- K4 进程与上下文：5–7 个。
- K5 用户态闭环：5–7 个。
- 合计约 30–42 个任务；收口只到 K5，busybox/UART/cache/LLC/gem5 等不阻塞。

## K0 兼容性缺口（已由 `m14-infra-001` 承载）

- 缺口清单与逐项判据进工具链矩阵任务（`llvm-ar/ranlib/strip`、`asm goto`、栈保护、`.quad/.long/.short/.byte`、inline asm、`-mcmodel=kernel`）；入口判据 = 缺口全部有规避法 + `arch/dadao` 骨架能出 vmlinux。

## 待办（K0 已立册）

- K0 七件已落 `.tao/tasks/{linux,spec,infra}/m14-*`（`milestones-m14.md` 台账）；`m14-linux-001`、`m14-spec-001` 已派。
- **启动 ABI 值已冻结（用户 2026-11-13）**：内核 `0x0010_0000`、boot info PA `0x0001_0000`、initramfs `0x0400_0000`、`rb17` 承载、入口 `supv` + 身份映射。
- **spec/Process 授权（2026-11-13）**：`m14-spec-001` 可改 `spec/Machine-v5`+锁、`m14-linux-001` 可改 `docs/Process-01`、`m14-infra-003` 可改 `docs/Process-07`；其余仍需逐次授权。
- **initramfs 的 syscall 范围（用户 2026-11-13）**：**不做特殊限制，别滥用就行**——不要求「ELF syscall 全集 ⊆ 4」；验收以「init 自有 syscall = write/getpid/brk/exit_group」+ 运行期 trace 说明为准。
- **LLVM/汇编器缺口裁定（用户 2026-11-13）**：
  - **数据伪指令 `.quad/.long/.short/.byte` 与 `.align` 不做支持**；内核与汇编统一用 DADAO 支持的 `.dd.o64/.dd.t32/.dd.w16/.dd.b08` 与 `.p2align/.balign`。
  - **代码模型只有两个**：`default`（= `CodeModel::Small`，可写 `-mcmodel=small`）与 `large`；`kernel/medium/tiny` 按 ADR-0036 设计上拒绝，**不算缺口**。
  - **CFI 崩溃**（`llvm-mc` 断言 `RAReg <= 255`）：与"64 位 DWARF"无关，是 DADAO 缺 DWARF 寄存器编号、return-address 寄存器编号 >255；先立任务（正面支持编号表，或至少改报错不 abort）。
  - **`llvm-link`/`llvm-config`/`llvm-profdata`/`llvm-size`/`llvm-cov`**：并入 `m14-llvm-001` 同批补齐。
  - **`-fpatchable-function-entry`**：立 `m14-llvm-003` 现在补。
- **栈保护 SSP（用户 2026-11-13）**：**现在补后端**（DADAO 后端 stackguard lowering），不再长期用 `-fno-stack-protector` 规避；K0 内核按 KSPP 默认开 `-fstack-protector-strong`。
- **工具链缺口（用户 2026-11-13）**：`llvm-ar`/`llvm-ranlib`/`llvm-strip` **先补进工具链**，不长期用 GNU ar / `llvm-objcopy` 规避。
- **内核地址空间（用户 2026-11-13 修订，取代原"从低地址身份映射"）**：内核 VA 窗口 = **`[3 TiB, 4 TiB)`**（= `[0x0000_0300_0000_0000, 0x0000_0400_0000_0000)`），用户空间 = `[0, 3 TiB)`。**已冻结的四个地址整体 +3 TiB**：
  - 首张页表页 `0x0000_0300_0000_0000`（`PTBR` 仍指 PA 0）
  - boot info `0x0000_0300_0001_0000`
  - 内核镜像区 `[0x0000_0300_0010_0000, 0x0000_0300_0400_0000)`（`kernel_base = 0x0000_0300_0010_0000`）
  - initramfs 区 `[0x0000_0300_0400_0000, 0x0000_0300_0600_0000)`
  - 映射形如 `VA[K, K+64MiB) → PA[0, 64MiB)`（偏置 3 TiB），不再是全域身份映射；smon 只建内核窗口 + 低端必要页。
- **启动 ABI 口径（用户 2026-11-13，已落 spec/ADR）**：
  - ABI 地址一律 **VA**（`addr[41:0]`）；PA 只出现在页表项、`PTBR`、loader 写内存。
  - 启动模型 **M1**：进入内核前已有 64 KiB 页身份映射 `VA[0,2GiB)→PA[0,2GiB)`、`PTBR` 指向、`ptw_enable=1`；VA 入口。依据：`ptw_enable=0` 时内存窗口取指/访存 ⇒ `CFXMEM`，不存在 MMU 关运行。
  - **身份页表由 smon 固件预建**；宿主 loader 只装镜像（ELF/raw）到对应 PA，不代写页表页。
  - ADR：`adr-0051-linux-boot-abi.md`（`Accepted`，D1–D8 已逐条确认）。

## 待裁定 ADR：Linux bring-up charter（未落文件）

- **状态**：方向已确认；ADR decision 文本待逐条确认（尚未落 ADR 文件）。
- 已确认方向见上（7.2.10、单核 QEMU MVP、semihosting、不引入 UART/cache/LLC、TLB 在 K3、busybox 后置、0628 只参考）。
- **下一步**：把上述方向写成 D1–D7，逐条确认后再落正式 ADR。

---

# 三个里程碑之外

## 待用户裁定：ADR

### `SPEC-180t` 的 ADR

- 状态：待用户裁定。
- 结论：escape 合法偏移集 `{0,+4}` + `imms18[17:1]` SBZ ⇒ ILLI，按 `docs/Process-03` 命中外部契约变更/多方案/结论固化。
- 下一步：逐条确认 decision 后再立 ADR；未确认前只保留为遗留。

### ADR 状态（其余）

- `ADR-0043`/`0045`：已 `Accepted`。
- `ADR-0046`：仍 `Proposed`，等 Linux 实测后再收口。
- 不再改 0043/0045 的 decision；0046 保持 `Proposed`。

## 架构未决项

### cfx 范围（M10 后）

- 已实现：umon/jmon/smon/hmon/ptw/pmem/time/hart/power。
- 后置：cache/llc/uart、PMEM 区域分配、IPI、多 hart。
- 下一步：按 Linux 需求拆任务（M14 启动时）。

### U-mode / cg5 / 异步帧

- 状态：待讨论。
- 结论：U-mode 的 cfx 目标不设 ISA 限制，由 OS 策略决定；cg5 单帧、同步/异步分离、递归/重入尚未定。
- 下一步：等 cg7 与 escape 收口后再讨论。

### SBI 生产 provider / W1C

- 状态：后置。
- 结论：当前只有测试专用 provider；生产 provider、`DONE/ERROR` W1C、`WAIT` 属 Linux 集成阶段。
- 下一步：不在 M10/M11 通路内实现。

### CFX 审计保留的未决项

- IPI：只有接收端，没有发送服务/寄存器。
- TLB：当前**无规范定义**（此前实现只覆盖 invalid，没有 fill）；按 Linux K3 先定义再实现。
- `cfx_pmem_exist`：SEE 与 SBI 语义不一致。
- UART：实例号/索引语义未定义（Linux 阶段暂缓）。
- 下一步：确认哪些进入 Linux 前任务；不恢复已删除的审计文件。

### `TESTCASES-089t` 遗留

- `reserved.yaml` 是否拆册（当前同册承载「保留编码 ⇒ UNDI」与「reserved cfx 地址空间 ⇒ CFXMEM」两类语义）。
- `trap`/`escape` → reserved cfx 的 active 向量仍 deferred（`TESTCASES-033t`）。

## 待裁定：`-bios` 的 legacy trampoline 窗口（2026-11-11）

`m13-qemu-002` 的 reviewer 发现：`Machine-v5 §6` 字面要求 `-bios` 装**同一固定固件**、不再带 trampoline；但实现保留了 **≤4096 B 的 legacy 窗口**（44 例 `tests/inst` Tiny 中 43 例的 `expected_fault` 退出码口径依赖它）。

两条路：
- **① 绑 `m12-chipyard-019`**：故障分派进 hmon 后，把那 44 例 oracle 迁到新口径，再删 legacy 窗口（口径收敛、无历史包袱）。
- **② 修 `Machine-v5 §6`**：承认该窗口为测试机约定（改动小，但 spec 多一条历史例外）。

reviewer 建议 ①（随 `019` 做）。**待用户裁定。**

## IDL 里程碑归属（用户 2026-11-12 裁定）

- **M13 不加任何 IDL 任务**（M13 收口判据不变：三平台差分矩阵冻结）。
- **M14 已分配给内核**，不占用。
- IDL 分 **M15 / M16**，分界 = **不执行 / 执行**：
  - **M15「ISA 语义结构化」**：把 spec 升级为「每条指令一段可解析的 operation」，但**不执行**。
  - **M16「可执行参考模型」**：把 M15 的 `.idl` 跑起来，作为第四方差分参照。

### M15 候选任务（未立册，待批次授权后立）

| 候选号 | 内容 | 估时 |
|---|---|---|
| `m15-spec-001` | 语法 v0（`contracts/isa/idl-v0.md`）+ 5 条样板（add.so / ld.o / br.eq / lr.o.nn / trap）+ `extract.py` 原型 | 3–5 天 |
| `m15-spec-002` | 6 族形状定稿（alu/mem/ctrl/atomic/system/fp 各一条完整族）+ 共享函数层 | 5–8 天 |
| `m15-spec-003` | 全量 operations：264 条记录 → 约 90 个语义单元（按族参数化，共享函数 + 薄 block） | 25–35 天 |
| `m15-infra-004` | 抽取器 + L1 门控「spec 抽取结果 == 仓库 `.idl` 逐字节」 | 6–8 天 |
| `m15-infra-005` | 文档渲染：spec 里显示格式化 operation（不是原始 IDL） | 4–5 天 |
| `m15-spec-006` | 版本与只读锁同步、`Process-03` 附录条目 | 1–2 天 |

M15 exit：264 条记录 **100%** 有 operation 块且 id 一对一；抽取结果与 `.idl` 逐字节一致；6 族各一条完整通过；`check-spec-*` 全绿。

### M16 候选任务（未立册）

| 候选号 | 内容 | 估时 |
|---|---|---|
| `m16-infra-001` | lexer / parser / AST / 类型检查（Python） | 12–16 天 |
| `m16-infra-002` | 解释器：加载 ELF、四 bank 状态、48 位地址/大端、异常与 monitor、trace | 10–14 天 |
| `m16-testcases-003` | 差分接入：273（整数）+ 167（访存）+ 67（控制流）逐例与 QEMU 一致，纳入 L2 | 8–10 天 |
| `m16-testcases-004` | 向量「算期望」派生（输入仍人挑，期望由 IDL 算；**不做输入自动生成**） | 8–10 天 |
| `m16-chipyard-005` | FP 特殊值语义（NaN/Inf/次正规/五类标志；数值舍入交引用库并显式标注） | 15–20 天 |

M16 exit：507 例与 QEMU 逐例一致；每个 operation 分支至少被一个向量走到；`make check-idl` 进 L2；分歧归因落 spec 裁定（**不是「IDL 一定对」**）。

### 参考材料分工（`.cache/refs/`，只读参考、不复制实现）

- **`riscv-unified-db`**（`manifests/references.lock.toml` 已登记）：机器可读 ISA 数据的**形态**——`operation()` 挂在编码旁、`resolved spec` 展开、生成器矩阵（文档/ISS/头文件/解码包）；**不复制其 RISC-V 专属结构**（扩展体系、CSR、`X[]`）。
- **`DADAO-0628`**：Python 解释器（逐指令 handler + 合法性单列）与 Sail 两套独立实现的**经验**；尤其「独立投影同一份散文规范」的纪律。
- **`DADAO-v5-pr4`**（本次新增）：RTL 侧的**微操作分层**（24 个 op code + width/signed/dual/aux 的 28 字段 exec descriptor）与「生成器 vs 独立校验器」对偶、negative gate 的写法；**微操作只留在 RTL 层，不进规范与分类**。

### 参考材料落盘方式（2026-11-12 实测调整）

`riscv-unified-db` 与 `DADAO-v5-pr4` 两份参考材料**不用 git 镜像**，改为 **tarball 快照**（`manifests/reference-snapshots.toml` 记录 URL/commit/sha256）。

原因：当日 GitHub git 协议不可用（`clone --mirror` 超时、`--depth 1` 触发低速阈值），而 codeload 的 tar.gz 走普通 HTTPS 正常（约 1.4 MB/s，UDB 56 MB / PR#4 8 MB 均成功）。

影响：两份材料**可读、可 grep，但不能 `git log`/`blame`/`diff` 历史**；需要历史版本时另找网络时段做全量克隆，或走镜像（源需用户确认）。

## 规则修订待办（待裁定；2026-11-13 起 `lessons.md` 退役）

> 口径：**可执行规则**进 `AGENTS.md`，**可复用经验**进 `docs/DDLN/Y-研发流程`，**未定案**留本节。以下三项尚未定：

1. **证据脚本的静态门控**：目前「禁恒真 / 禁同源自比 / 禁 `tee` 吞码」靠 reviewer 人工审脚本；是否做成对证据脚本的静态扫描并进 L2（误报率待评估）。
2. **「已知红」豁免载体统一**：现存三种写法（issue 号 / 任务书登记 / 门控 defer 清单）；是否统一为「issue 号 + 门控精确 id 清单」双写，其余禁止。
3. **经验落 DDLN 的粒度**：本次按「既有 Y 册各追加一节一句话结论」；若条目继续增长，是否改为单独「工程经验清单」分册（先生效观察一轮再定）。
