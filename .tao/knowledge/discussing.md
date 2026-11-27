# 讨论项

> **组织方式（用户 2026-11-18 重排；2026-11-20 按立册重排）**：`未决项` → `M14` → `M15` → `M16` → `M17` → `M18` → `M19` → `M20` → `未立册方向`（都是**一级标题**）。**所有未决/待裁定项统一放在最前**（逐个二级标题，并按里程碑分组标注归属），里程碑各节只放**已定口径与现状**。
>
> **维护规则（2026-11-13，用户 2026-11-19 重申）**：本文件**只记未裁决项**。裁定一旦落成 `spec/`、ADR、任务书、`AGENTS.md` 或 `docs/DDLN/`，**从本文件删除**（git 历史可回溯）——该迁的迁、无保留价值的直接删；过程快照、已完成任务的方案叙述、过期队列状态一律不留。任务流水看 `milestones-m14/15/16.md`，M13 及以前见 `.tao/archive/`。

# 未决项

> **归属（主会话分诊 2026-11-20）**：未决项按里程碑分组，逐个里程碑讨论时逐条裁定。标记：**待裁** = 需你拍板；**待办** = 方向已定、只差执行；**关闭** = 已解决（保留记录，不再讨论）。
>
> - **M16**：`N1`（M12 spec 残留 9 条，待裁）、`N35`（cache 规模 256/512 KiB，待裁）
> - **M17**：无未决项（`N16`/`N21`/`N26`/`N34` 均已关闭）
> - **M18**：`N3`（ADR-0046 收口，待办）、`N9`（SBI 生产 provider/W1C，待裁）、`N29`（内核差异盘点 → 整改取舍，待裁）
> - **M19**：`N7`（cfx 待实现范围：cache/UART/IPI/多 hart，待裁）、`N10`（UART 实例号语义，待裁）、`N44`（TSI↔power 交互，待裁）、`N45`（tohost/fromhost 与结果协议，待裁）、`N46`（cfx_uart 是否开启，待裁）、`N47`（fesvr 移植范围，待裁）、`N48`（测试/三平台迁移，待办）
> - **M20**：`N4`（ADR-0057 的 D5–D7，待裁）、`N12`（长仿真心跳方案 A/B/C，待裁）
> - **未立册方向**：`N28`（Vast 地址图 ADR，待专门讨论）
> - **backlog（暂无里程碑）**：`N11`、`N13`、`N15`、`N18`
> - **已关闭**：`N17`、`N27`、`N30`/`N30 追加`、`N31`、`N32`、`N33`
- **未定里程碑**：`N43`（`escape` 重编码提案，暂不讨论）

## N43. `escape` 重编码提案（用户 2026-11-24，暂不讨论；里程碑待定）

**2026-11-24 追加（用户原话，仅记录、暂不讨论）**：`escape` 的格式**可能改为** `escape cfxHA, cgHB, rcHC, immu6`；**后六位（`immu6`）是 one-hot**。
> 与下面的「6 位 one-hot + 12 位载体（占满 `imms18`）」是**两种并列的候选**，取舍待将来讨论；本条只落记录。

`escape` 增加 **6 位 one-hot**，每种取值一种退出方式，其后 **12 位为载体**；`6 + 12 = 18` 正好占满 `imms18`。用户列出的 6 种：

1. 同步异常、**权限降低**、返回原位置，后 12 位 = 地址偏移；
2. 同步异常、**权限不变**、返回原位置，后 12 位 = 地址偏移，且有限制「只允许最低位不为 0」；
3. 同步异常、权限不变、**不返回原位置**，后 12 位待定；
4. 异步中断、返回原位置，后 12 位应为 0；
5. 异步中断、**不返回原位置**，改为 **smon/hmon 的调用**，后 12 位待定（调用号）；
6. 保留。
**性质（记录，未讨论）**：这是 `escape` 的破坏性重编码——现行 `imms18[0]`（字节偏移 bit2）、`imms18[1]`（帧选择位）、`imms18[17:2]` SBZ、合法 `{0,1,2}`/`3 ⇒ ILLI`、汇编层 `imms20 ∈ {0,4,8}` 全部作废；影响面 `spec/SimRISC-11`（正文 + IDL 渲染块）、`idl/SimRISC-11.idl`、`spec/Toolchain-01`、`contract-isa`/`contract-asm`/`opcodes.yaml`/`legality_rules.yaml`/`gen_asm_list.py`、LLVM 汇编/反汇编 + lit、IDL 执行器/向量、QEMU、RTL、`11-cfx` 的 escape 向量。
**待确认（未讨论）**：one-hot 放 `imms18[17:12]` 还是低 6 位、是否严格"恰好一位"（0/多位 ⇒ `ILLI`）；载荷单位（字节或 4 字节）与 kind 2 的「只允许最低位不为 0」是否等价于只允许 `+4`、载荷 0 是否合法；kind 1「权限降低」由谁决定（回到 `prev_run_mode` 还是强制降一级）、kind 2「权限不变」是否强制留在当前模式；kind 3 的新 IP 来源（12 位待定 ⇒ 取自哪里）；kind 5 的目标是 smon 还是 hmon、调用号对应哪张入口表；与 `cfxha`（当前 cfx）的关系；版本是否升号。当前实现仍是 `imms18[1]` 帧选择位（ADR-0060 D4），本提案未落地。

## N1. M12 spec 口径残留（`spec-003`/`spec-004` 未覆盖项，9 条）

- #9 `cfx2rd`/`cfx2rc` 到**保留** cfxha ⇒ `ILLI`（`Kaiwu` 现只说「不存在 cfx 寄存器 ⇒ `CFXREG`」，与 `DADAO-12 §5.2(一)` 冲突）
- #10 reserved 集统一（正文 `19–61` vs 附录 0.4.0 `16–31、35–61`）
- #6 退出码由 hmon handler 生成（`§7.1` 只定编码、未定生成方）
- #3 Tiny 的 hmon 镜像装载路径（与 R13 绑定）
- `excp_cause_info` 覆盖：`Kaiwu §4.4` 5 项 vs `DADAO-13 §2` 11 项
- `escape` 返回 cfx 取自「异常帧」，但寄存器表无 `prev_cfx` 保存寄存器（实现镜像 QEMU/Node 保持目标 cfx）
- Tiny `cfx_power` 的 cg7（BootROM start/size）与 `cg8 rc1`（power ctrl，WO）无正文
- Tiny `switch_run_mode` 写非 hypv 值：寄存器 RW 但无强制路径
- **`spec-004` 候选**：Vast 的同步异常仍是 staged 机器 fault（`DADAO-12 §5.2(一)` 要求进向量），5 个 arch 探针 oracle 依赖旧口径；统一需同步改 qemu/gem5 + 探针

## N3. `ADR-0046` 仍 `Proposed`

- 等 Linux 实测后再收口；`ADR-0043`/`0045` 已 `Accepted` 且不再改其 decision。

## N4. `ADR-0057`（gem5 数据侧两阶段）的 D5 / D6 / D7

- 状态 `Candidate`；D1–D4 已定，**D5 取指/cache 未定**、D6/D7 依赖 D5。
- **D5 的前置（用户 2026-11-16 指示）**：先调整 gem5 **配置信息**——把机型/Profile 与内存层次配置分开（Tiny 与 Vast 分开），再谈 cache 参数。
- 已核事实：`configs/dadao/` 只有 `se.py`/`se_timing.py`/`fs.py`，都只用 `SimpleMemory`（`se_timing` 另有 `NoncoherentXBar`）；chipyard 侧只有 `WumingTinyConfig`（SRAM 主存、`icache/dcache = None`），**无 Vast 配置**。
- 用户已指出：`Kaiwu-Tiny` 跑在 SRAM 上**不需要** cache；`Kaiwu-Vast` 需要 cache 但 RTL 尚未增加。

## N21. `idl` 清单的 sha256 锁（**已于 2026-11-20 收口**）

- 已做：`idl/*.idl` **12 个**逐文件 `sha256` 写入 `idl/.manifests.toml`；
- 顺带补了一个真缺口：`idl/lib/`（`fp.idl`，浮点语义库）**原先没有任何清单守护**——实测往里加游离文件门控仍 PASS。已新建 `idl/lib/.manifests.toml`（含 `fp.idl` 的 sha256）并在 `manifests/dir-guard-roots.toml` 注册 `idl/lib`；现门控 6 册 / 6 目录 / 59 文件 / 36 sha256，**游离文件与内容篡改各验证一次 FAIL**。

## N27. 匿名页 shared futex ⇒ 由 `m14-linux-035` 按标准流程解决（用户 2026-11-20 已裁）

- **根因（已查明）**：`arch/dadao/mm/fault.c` 是**自定义缺页通道**（`find_vma` + `dadao_pf_alloc_page()` 返回 PA + `set_pte`），**不调 `handle_mm_fault`**、**不注册 rmap** ⇒ `folio->mapping == NULL` ⇒ `kernel/futex/core.c` 的 `!mapping` 分支 `return -EFAULT`。**rmap 不是 ISA 特性**（`mm/` 通用机制），是我们绕过了它。
- **用户裁定（2026-11-20）**：「**M14，尽量按主流 ISA 的标准流程走**」⇒ 已写入 `AGENTS.md`（内核实现优先走 `mm/`/`kernel/` 通用路径，DADAO 特有处只做 arch 适配）。
- **执行**：立 `m14-linux-035 缺页路径回归 Linux 通用流程`（阶段 1 评估 PTE 兼容性与 `handle_mm_fault` 所需 arch 钩子 → 阶段 2 补 rmap/LRU/page cache）；`025` 的 F7 记录问题按实测修正（不再有「`pthread_join` 不可用」这类错结论）。
- **原 A/B/C 三选一作废**（那是基于「要不要支持一类新语义」的误解）。

## N28. `m16-chipyard-007` 的地址图改造是否立 ADR（拟编号 0058；**用户 2026-11-20：暂缓，待专门讨论**）

- **内容**：Vast 的 PA RAM `[0,2 GiB)` 由 AXI4+SimDRAM 改为 **TileLink 从端口**（理由：`+loadmem` 同时喂 fesvr；TL→AXI 单拍写触发 ToAXI4 计数断言）；RISC-V 外设移出/去掉（**Vast 侧已无 debug/UART**）；`+loadmem` 改双窗口装载（实测 9 段、7925/7925 字回读一致）。
- **用户裁定（原话）**：「这是个大问题，等我有时间了详细讨论」⇒ **暂不立 ADR**，改动本身照现状保留（已随 `m16-chipyard-007` 实施）。
- **重启条件**：讨论后决定立 ⇒ 拟编号 0058（0057 为现有最大），D1–D3（PA RAM 接入方式 / 外设取舍 / `+loadmem` 双窗口契约）逐条确认后才 `Accepted`。

## N29. M14 内核代码与主流 ISA 的差异盘点（用户 2026-11-20 已定方向）

- **用户裁定（原话）**：「M14 中增加专门的任务，或者多个任务，分子系统把已经实现的内核代码，逐个和主流 isa 的实现进行对比，找出差异」「可以，discussing 保留讨论结果，你根据已有的进展和将要进行的任务，立只读盘点的任务，可以并行；**是否立刻整改，我来定**」。
- **做法**：分子系统立**只读盘点**任务（不占 linux 写者锁、可并行），对比对象 = 仓库 Linux 源树的 `arch/riscv`（主）+ `arch/arm64`（参照）。
- **产出四类差异**（每条带两侧 `文件:行号` + 影响面 + 优先级 P0/P1/P2）：① 缺失 hook；② 语义不符（返回码/副作用/加锁/顺序）；③ 旁路 vs 通用路径；④ Kconfig 缺口（缺 `select`/`depends on` ⇒ 通用代码没编进来，如 `025` 的 `CLONE_BACKWARDS`）。
- **第一批**（与在跑/即将任务最相关）：`m14-linux-036` mm/缺页/页表、`037` syscall/ABI、`038` 时间/时钟、`039` 信号/退出、`040` Kconfig 选型。第二批（`D2` 进程/线程、`D3` trap/异常、`D7` 启动）待第一批格式确认后再立。
- **整改权归用户**：盘点只出清单与建议，**是否整改、何时整改由用户逐项决定**；P0 项若阻塞在跑任务，须先报用户再插队。

## N30. 信号帧布局与模式位（用户 2026-11-20 已裁，关闭）

- **帧尺寸 2048 B**（用户强调「我已经裁定过的！！！」）：四组各 64 槽，`rd` 组第 0 槽存 `status`、`rb` 组第 0 槽存 `ip`——因为 `rd[0]` 本来就不是寄存器（`ld` 到它 ILLI）、`rb[0]` 在硬件上就是只读 IP。
- **C 表达方式**：**匿名 union**（用户 2026-11-20「还是匿名 union 吧，这里没有歧义，无需具名」）——`regs->rd[64]` 与 `regs->status` 两个视图同址，48 处 C 引用与 12 处 asm（`PT_IP`/`PT_STATUS`）**零改动**。
- **模式位：低 4 位**（不是 2 位）放在 `status`；`spec/DADAO-12 §1` 只定义 2 位编码（0b00 user / 0b01 jail / 0b10 supv / 0b11 hypv），**高 2 位留扩展**；`user_mode(regs) = ((regs->status & 0x3) != 0)`（用户 2026-11-20 二次调整；**注意**：按 `spec/DADAO-12 §1`，jail(0b01) 属用户态，此式把 jail 判为非用户态——因 Linux 下不进 jail，当前等价；将来若支持 jail 需重裁）；**bit 4–63 保留 0**（用户「以后再说」）。
- **uapi 与 musl 同步更新**（用户原话）：`uapi/asm/ptrace.h` 的 `user_regs_struct` 与 musl 的 `sigcontext`/`mcontext_t` 都按 2048 B 同形状改。
- **`ra[0]` 的 `{RACNT, MRPTR}` 元数据保持原样**，不参与复用。

## N30 追加（用户 2026-11-20 二轮裁定，全部关闭）

- **`status` 不加 IE 位**：`trap` 进入硬件保存 `cfx_<monitor>_global_cfx_intr_mask` 并置全 1、`escape` 自动恢复（`spec/DADAO-12:876/823/954`）⇒ 软件帧不重复存；`saved_global_cfx_intr_mask` 是**内部寄存器、不暴露**（`§3.6`）⇒ `regs_irqs_disabled(regs)` **保持恒 false**，`045` 注明此接口限制即可。
- **`irqs_disabled()` 保持「读硬件 mask + `DADAO_IRQ_SOURCE_BITS` 子集判定」（用户裁定 B，2026-11-20）**：与 RISC-V `sstatus.SIE` / arm64 `DAIF` 同构——异常进入让其为 true 是**特性**（使 `might_sleep()` 能抓住「在中断里睡」），不是副作用。不采用「软件镜像 + 入口/出口同步」（两处状态易失步）。
- **`DGPTRAP` 不补读写区分**（此前我判断有误）：`DGPTRAP` = **缺页（P=0）**，填充路径与访问方向无关；**`NWPERM` = 违反写权限（P=1 且 W 不符）**，这就是明确的「写」信号（COW/`mprotect` 后写都走它）⇒ 「先只读填充、写由 `NWPERM` 判」信息完整，与 Linux `do_anonymous_page`/`do_wp_page` 分工一致。`m14-linux-035` 拒绝该推断正确。
- **K3 窗口臂保留**：主流 Linux 在 `mm == NULL` 下无缺页路径（启动期用 fixmap/`early_ioremap`），K3 的「无进程靠缺页装页」是 bring-up 特有形态 ⇒ 原样保留到 K3 退役，不为其做任何新设计。

## N32. `m15-spec-006` 的门控 2 行改动**待用户追认**（2026-11-20 挂起）

- **改动**：`tools/spec/check_spec_changelog.py` 把 `"SimRISC-" in rel`（路径子串）改成 `Path(rel).name.startswith("SimRISC-")`。
- **为什么必须改**：用户裁定的新册名 `IDL-SimRISC-ISA语义描述语言与语义库.md` 含 `SimRISC-` 子串 ⇒ 旧判据把它误判成 `SimRISC` 系列册（报「禁附录」+ 误入版本互锁组 2 条）。
- **reviewer 判为「判据对齐」非「放松」**：与 `check_numbering.py:141`/`check_spec_purity.py:70` 谓词逐字相同；23 册上新旧集合差**只有新册一册**；4 路 fixture（`SimRISC-07` 带附录 FAIL、`SimRISC-00` 缺附录 FAIL、`IDL-SimRISC-*` 带附录 PASS、真册互锁仍生效）。
- **状态**：任务 `m15-spec-006` 已 Accepted、**未合并**，等用户追认这 2 行；替代方案只有「册名去掉 `SimRISC-` 子串」，与用户命名裁定冲突。

## N33. M14 收口四问（用户 2026-11-20 已裁，全部关闭）

1. **K3 退役时点**：用户原话「**内核开发不像其它模块，每进展一个阶段，原有阶段的测试可能无法再保留，所以，随时都可以把已过时的测试退役**」⇒ 不等特定节点；**并入 `m14-linux-029` 整体退役**（删 `check-linux-k3` + `check_k3.py` + `k3_page_probe.py` + `k3_*_selftest.c`，**连带删 `035` 为它保留的 `mm == NULL` PA 直通窗口臂**），在 `Process-07 §4a` 记录。
2. **K5 收口（`029`）判据范围 = B**：含 **shared futex**（`035` 的 rmap 成果）+ **基本信号投递与帧往返**（`046`）；**不含** pthread create/join（属 K6）。
3. **K6（busybox `032/033/034`）属 M14**：做到 K6 才算 M14 完成（台账现状不变）。
4. **`ARCH_FORCE_MAX_ORDER` 改 13**（用户原话「这样最大可分配的页恰好是一个超页，512 MiB」）：`2^13 × 64 KiB = 512 MiB` = 超页（`SPF=0xFF`）⇒ buddy 最大阶与超页对齐；并入 `028`，须验 Tiny（8 MiB SRAM）不回归。

## N31. `m15-idl-001` 完成区不实 + IDL 两处待修（`m15-idl-020` 盘点发现，用户 2026-11-20 待定整改）

- **真相（`m15-idl-020` 第 2 轮 reviewer 定案）**：**不是凭空不实，是「实现过、未提交即丢失」**——该任务证据脚本开跑时（2026-11-19 11:19:07）的 `.md5_before` 记录 `idl/SimRISC-01.idl = 828191b0…`，而所有提交版（`bdc5c171`→`11136d55`→`def353ac`→合入 `a336b448`）**全是 `0c5df887…`**；`828191b0` 不在任何 git 对象、无 stash、无 reflog，丢失窗口 = **11:19 → 11:25:57（6 分钟）**。用同一 `check_semantics.py --section 4` 对现树实测：`Malign 判定 实际 0`、8 条逐个「缺构造」、`FAIL（16 处）`。⇒ **对外事实 = 合入版没有守卫**（完成区当时为真，但交付物没有）。任务书已加「⚠ 更正」注（保留原文）。
- **IDL 两处缺陷**（均「应改 IDL」）：
  1. **D1**：`jump`/`br.*` 的 `rb0` 写回——IDL 只写 `target[47:0]`，而 `SimRISC-06 §1/§2`、`ADR-0012 D8.3/D8.4`、三执行机都写完整 64 位、取低 48 位取指；
  2. **D2**：`ld.t`/`st.t`/`ldm.t`/`stm.t` 等 8 条 rf 缺对齐守卫——`SimRISC-01 §4` 正文 + 附录 B `excp_malign` 32 条 + `contracts/opcodes.yaml` 的 `aligned(4/8)` 三方一致要求 MALIGN，IDL 不判（注释前提已被 `af7ffb09` 推翻）。
- **D3（执行机侧）**：窄 `lr` 9 条 IDL 按用户 2026-11-19 裁定只写低 W 位，三执行机仍整 64 位零扩展（`MEMORY.md`/`m15-idl-012` R2 已登记）。
- **处置**：拟立 `m15-idl-021`（修 D1+D2 + 订正过期注释）；D3 属三执行机改动，另计。**是否立刻整改由用户定**（用户 2026-11-20：「修完 B/C 再分析一轮」）。

## N7. cfx 待实现范围

- 已实现：umon / jmon / smon / hmon / ptw / pmem / time / hart / power。
- 后置：cache / llc / uart、PMEM 区域分配、IPI、多 hart。
- 下一步：按 Linux 需求拆任务（M14 启动时）。

## N9. SBI 生产 provider / W1C

- 当前只有测试专用 provider；生产 provider、`DONE/ERROR` W1C、`WAIT` 属 Linux 集成阶段，不在 M10/M11 通路内实现。

## N10. CFX 审计保留的未决项

- IPI：只有接收端，没有发送服务/寄存器。
- TLB：此前实现只覆盖 invalid、没有 fill；K3 已定「先定义再实现」，正文时点在 K2 收口后由主会话提出。
- `cfx_pmem_exist`：SEE 与 SBI 语义不一致。
- UART：实例号/索引语义未定义（Linux 阶段暂缓）。
- 下一步：确认哪些进入 Linux 前任务；不恢复已删除的审计文件。

## N11. `TESTCASES-089t` 遗留

- `reserved.yaml` 是否拆册（当前同册承载「保留编码 ⇒ UNDI」与「reserved cfx 地址空间 ⇒ CFXMEM」两类语义）。
- `trap`/`escape` → reserved cfx 的 active 向量仍 deferred（`TESTCASES-033t`）。

## N12. 长仿真「证明它还在跑」的心跳方案

**问题**：单例内部零信息（只有 `ps` 和完成行），无法区分「慢」与「挂死」。

**事实（已核）**：chipyard/Verilator 的 `trace_count` 只在结束 `$fdisplay`，`+cycle-count` 也是退出时打印，`+verbose` 是逐周期 Chisel printf（代价过高）；gem5 stats 只在结束时写 `m5out/stats.txt`。受害案例：`ics170` 上 6 个 picolibc sim 跑到 11 h 25 m 无任何进度；`ISS-361` 的「72/72 全超时」本质也是缺这个能力。

**可选手段（按侵入性递增）**
- **A（零改动，先做）**：外层 runner 每 60 s 写一行 JSONL（在跑例 + 已跑时长 + `/proc/<pid>/stat` utime + `semi.out` mtime）⇒ 能看出「还在推进」，但给不出周期数。
- **B（chipyard，改 RTL 包装）**：`TestDriver.v` 加 `+heartbeat=N` ⇒ 精确周期进度 + 可算 ETA；代价 = sim md5 变化、单二进制基线要重做。
- **C（gem5，配置层零 C++）**：`configs/dadao/se_timing.py` 用分块 `m5.simulate(chunk)` 循环，每块打印 `curTick()` ⇒ 零 C++ 改动、不改结果。
- **D（统一呈现）**：三种心跳写同一格式（`ts / task / case / cycles_or_utime / eta`），由看板汇总。

**判据**：① 心跳不改仿真结果（chipyard 只写 stderr、不进 `semi.out`；gem5 走配置层分块）；② 降速 < 1%（实测开/关对比）；③ 必须能区分「慢」与「挂死」（如「最近 N 分钟周期增量 = 0」）；④ 与单二进制纪律兼容（选 B 须在批次开始登记 sim md5）。

**待裁定**：① 是否允许改 chipyard RTL 包装（影响 sim md5 与冻结基线 `079ae015…`）；② 若不允许，是否接受「宿主心跳 A + gem5 配置层 C」的折中；③ 心跳频率与落盘位置（默认 60 s / 节点运行期日志 / 看板汇总）。

## N13. `tools/` 脚本台账与孤儿清理口径

- 现状（现场统计）：`tools/**` 下约 260 个 py/sh；仅 `tools/testcases/README.md` 一份索引且只登记 3 个（该目录 120 个 ⇒ 117 无索引）；其余 7 个模块无 README，也无 `tools/README.md`；约 53 个零外部引用（如 `tests/inst` 侧的 `min_rom_probe_*` 整族、`tools/qemu/generate_{atomics,clmul,rol}_vectors.py`、`tools/gem5/check_b{1,2,4,6}.py`）。
- 待用户选口径：**A 归档到 `.tao/archive/tools/`（不删除，建议）/ B 直接删除 / C 只报告不动**。
- 建议任务形状（1–2 h）：8 模块补索引（路径/用途/入口/调用者）+ 零引用者逐个处置 + 新增 L1 `check-tools-index`（只报告不删除）。
- 另挂：`m12-chipyard-017` 里的 `engine_parity_run.sh`/`engine_parity_collect.sh` 按「一次性编排不入仓」规则待迁回运行期目录。

## N15. `tests/inst.yaml` 的 `platforms:` 字段去留

- `m15-infra-001` 已把机型/引擎/套件的真源迁到 `contracts/machine.yaml` + `exec-envs.yaml` + `tests-matrix.yaml`，但 `tests/inst.yaml` 里 **273 处 `platforms:`** 仍在，与 `exec-envs.yaml` 的 `engines` 语义重叠。
- 待裁定：① 保留（改名 `engine`/`mode`）还是废弃、用例适用范围统一用 per-case `profiles:`；② `user`（qemu-user / gem5-se）在执行环境契约里已归独立 env，是否还需 per-case 标注。

## N16. M15 语法 v0 的 4 条待定（**全部已解，关闭**）

1. **是否采用 `idlc` 作抽取器**：不采用——M17 已定执行器用 **Python**、不依赖 Ruby/`idlc`（`m17-idl-001/002` 已落）；
2. **是否冻结 `.idl` 语法版本并进 L1**：已达成——`idl/*.idl` + `lib/fp.idl` 全部 sha256 锁（`check-manifests-guard`）+ `check-idl-parse` 在 L1；
3. **渲染形态（伪代码 vs 原始 IDL）**：**保持原始 IDL 块**，不做格式化伪代码（2026-11-20 定；理由写入 `docs/DDLN/Y-研发流程/DD-Y006 §5`）；
4. **语料次序（5 样板 → 6 族 → 全量）**：已按此完成。

## N17. `m15-spec-001` 待返工推进方式

- 状态待返工（WIP 已保留）；用户要求「先摊开文件内容 + 逐条语句分析」再继续。
- 待定：由谁摊开（子代理 vs 主会话直接给全文）、按什么粒度逐条过（语法/语义/扩展点）。

## N18. `tests/inst` 头注释模板化（未授权）

- 272 个文件的头注释重复约 3,780 行（占 13%）；收益最大但会引入生成器。
- 需用户先定「只统一字段」还是「加自动生成」。`m15-testcases-001`（宏去重下沉）已授权在执行。

---


## N35. Kaiwu-Vast 的 cache 规模：256 KiB 还是 512 KiB（**待裁**）

- **背景**：`m16-chipyard-009`（D-Cache）/ `010`（I-Cache）的任务书等这个数；`discussing` 里现有 **47%–61%** 的 BRAM 占比是**纸面估算**（445 块 RAMB36；BootROM 16 + cfx SRAM 128 + cache 64/128）。
- **实测依据**：M19 的 Tiny 上板会先给出真实 LUT/FF/BRAM 占用 ⇒ 建议 **M19 资源实测后**再定，或现在按「256 KiB 先落地、512 KiB 作为参数可配」推进（I/D 各半则各 128/256 KiB）。
- **影响**：不定则 009/010 无法写死参数；但可用「参数化 + 默认值」避开阻塞。

## N36. Vast 的 DDR 怎么接（**未定**；用户 2026-11-20「今天不讨论」）

- **现状**：`m16-chipyard-007` 已把 Vast 的 PA RAM 从 AXI4+`SimDRAM` 改为 **TileLink 从端口**（理由：`+loadmem` 同时喂 fesvr、TL→AXI 单拍写触发 ToAXI4 断言）；仿真侧核心看到的是 TL。
- **上板约束**：Genesys2 的 DDR3 只能经 **MIG**（AXI4 slave）⇒ 必然要有一段 TL→AXI4。
- **两条候选（未裁）**：A = 核心保持 TL、桥放 FPGA harness（`TLToAXI4` + 位宽/burst 适配 → MIG），核与仿真同构；B = 核心改回 AXI4（与 007 结论冲突）。
- **若选 A 还需定**：DDR 映射 PA `[0,1 GiB)`、MIG UI 位宽（32/64）与时钟比、outstanding 深度、DMA 是否共用端口、板上加载通道（UART/JTAG/Flash）。
- **归属**：M16（接口契约，若需要）与 M21（FPGA-Vast，未立册）；重启讨论时先定接线，再谈桥的参数。

## N44. TSI ↔ cfx_power 的交互（**待裁**）

- **背景（未定）**：用户已提出用 TSI 装载测试程序并输出结果；TSI 是否/如何与 power 交互（boot wait）尚未裁定。
- **候选**：A = **SRAM mailbox**（host 经 TSI 写、power/hmon 轮询；不动 ISA spec，但 mailbox 地址需在 runtime/契约里定义；推荐）；B = 新增 TL 从口/CSR 窗口（把总线写翻译成 cfx 访问，类似 DM，需 spec/地址图）。
- **约束**：TSI 是 TL master，不能直接写 cfx cg/rc；Tiny 无 MMIO 窗口；TSI 无中断线，power 只能轮询。
- **待定**：boot wait / “load done” 握手、TSI 地址过滤（只允许 SRAM/mailbox，禁止 BootROM/ITCM/hmon）。

## N45. tohost/fromhost 与测试结果协议（**待裁**）

- **现状**：RISC-V HTIF 的 `tohost/fromhost` 不能直接用于 DADAO；测试现在走 semihosting `SYS_EXIT` / signature，板上无响应者。
- **待裁**：位置（SRAM 固定字 vs 其他）、宽度（64 位）、端序（大端）、原子性（8 字节写不能被 32 位 chunk 撕裂）、host 轮询/退出码、`BLOCKED`/超时语义。
- **建议**：先做 `signature + done/exit` 字（改动最小），semihosting-over-TSI 后置。

## N46. cfx_uart 是否开启（**待裁**）

- **候选**：开“最小轮询版”= `cfxha 62`、`exist=1`、仅 uart0、固定 115200 8N1、TX/RX/status、无中断/多实例；或 M19 不开，继续 TSI + signature。
- **前置**：`N10` 实例号语义（uart1–31 读什么）、cfx_uart 寄存器表（spec §4.11 只说“参照硬件协议”）、物理 UART 与 TSI 的复用（分时 / 第二根 / 帧复用）。
- **影响**：`DADAO-12 §4.11`、QEMU/gem5/RTL、测试 console；建议不把测试结果通道绑到 cfx_uart（未裁）。

## N47. fesvr 移植范围与 TSI 64 位/大端口径（**待裁**）

- **已提出（未定）**：先移植 fesvr（64 位大端），并重新制定 `tohost/fromhost` 位置。
- **待裁**：fork fesvr vs 只复用 `tsi_t` 协议 + 自写 DADAO host tool；TSI 保持 **32 位 chunk** vs 改 64 位（`TSI.WIDTH=32` 硬编码）；大端在 host 侧处理。
- **现状**：fesvr 是 RISC-V 小端/HTIF；`load_elf` 拒 BE；`TSIToTileLink` 的 body 是地址序，不是小端数值。
- **影响**：host 工具、TSI 协议文档、测试驱动、M19 验收。

## N48. 测试向量与三平台迁移（**待办**；用户 2026-11-24）

- **已定方向**：M16/M17 收尾后统一调整 Tiny 配置与所有测试程序布局；不把 FPGA 与 Verilator 做成两套。存储后端是否必须同构未定（建议功能一致、实现可不同）。
- **待办**：迁移清单/顺序——`contracts/machine.yaml` → `runtime.yaml` → `machine-tiny.inc`/`.lds`/`tests/inst` 固定偏移 → QEMU/gem5 机器 → RTL → 门控；`+loadmem`/`WumingLoadMem` 是否退役、Verilator 是否改用 `SimTSI`。
- **待裁**：QEMU/gem5 是否也走 TSI，还是保留各自 loader；256 KiB 下栈/堆的预算（软件布局）。

# M14：Linux bring-up

> **`ISS-454` / `ISS-455` 读法冲突（用户 2026-11-21 裁定 A）**：**维持 `ISS-455`**——异步过滤的 monitor 由**运行模式**选定（supv ⇒ `cfx_smon`），与 `inner_cfx_code` 无关；`contract-see §6.4` 的现有表述**正确、不改**，`arch/dadao/.../irqflags.h` 写死 `cfx_smon` **是对的**。`m14-linux-046` 曾把它改成「monitor = 当前 cfx / 首投后 `cfx_umon`」，属**语义改动**，已要求撤回（`ISS-454` 据此关闭：原命题不成立）。

> **M14 issues 处置（用户 2026-11-20「同意」）**：`ISS-444`/`ISS-457`/`ISS-470`（K1 证据、K2 可达 FAIL、门控 `CONFIG` 钉子）**并入 `m14-linux-029`**（它本就同笔改 K0–K4 门控）；`ISS-454`（`contract-see §6.4` 的「当前 cfx = `cfx_smon`」表述）**并入 `m14-linux-046`**（同批改 uapi/musl 与契约表述）。


> 2026-11-01 用户裁定：Linux 开发延至 M12 或后续；**现定为 M14**（三线分开进行）。

## 阶段与任务量（K0 后校准）

- K0 基线与契约：5–7 个任务（补丁组件、工具链缺口、启动 ABI、syscall/errno/TLS、initramfs/semihosting、门控）。
- K1 启动与控制台：4–6 个；K2 异常与时间：5–7 个；K3 内存与 TLB：6–8 个；K4 进程与上下文：5–7 个；K5 用户态闭环：5–7 个；K6 用户态应用：4–6 个。
- 合计约 34–48 个。

## issues（分诊到本册，2026-11-20）

- `ISS-444`【P3】K1 门控的「阶段顺序」证据是**间接**的：共享 BootROM 固件的 power/hmon/smon **不打印任何东西**，而 K1 任务禁 `-d` 逐指令日志，故 …
- `ISS-454`【P2】`contract-see §6.4` 的实例表述「当前 cfx = `cfx_smon`」在**首投之后不成立**：`spec/DADAO-12 §5.3` 的 `escap…
- `ISS-457`【P3】K2 两条派单口径缺「可达 FAIL」断言（`m14-linux-008` 复核实测）：① 把 `local_irq_save` 的 `flags` 截成低 32 位 ⇒ `k…
- `ISS-470`【P2】门控切片未钉住兄弟 `CONFIG` 符号 ⇒ 探针镜像继承开发期开关、产生假红（`m14-linux-017` F30 实测）：k3 突然 227/247 红（`exit_t…

# M15：ISA 语义结构化

> **定位（用户 2026-11-12/13）**：只做「**结构化**」——把 `spec/` 升级为「每条指令一段**可解析的 operation**」，**不执行**（执行归 Milestone 候选：IDL 可执行参考模型）。M13 不加 IDL 任务；M14 已分配给内核。

## 目标与出口

- `spec/` 的每条指令记录带一段 operation 块（语法可解析、语义单元唯一），与编码字段、合法性规则、异常语义一一对应。
- 出口：264 条记录 **100%** 有 operation 块且 id 一对一；抽取结果与仓库内 `.idl` **逐字节一致**；6 族各一条完整族通过；`check-spec-*` 全绿。

## 候选任务

- `m15-spec-001`（**已立册，方向反转后重写**）：`idl/` 语义源 v0（`idl/README.md`）+ 5 条样板（add.so / ld.o / br.eq / lr.o.nn / trap）+ `idl/render.py`；2–3 天。
- `m15-spec-004`（未立）：6 族形状定稿（alu/mem/ctrl/atomic/system/fp 各一条完整族）+ 共享函数层；5–8 天。
- `m15-spec-003`（未立）：全量 operations，264 条记录 → 约 90 个语义单元；25–35 天。
- `m15-infra-004`（未立）：抽取器 + L1 门控「spec 抽取结果 == 仓库 `.idl` 逐字节」；6–8 天。
- `m15-infra-005`（未立）：文档渲染（spec 里显示格式化 operation，不是原始 IDL）；4–5 天。
- `m15-spec-006`（未立）：版本与只读锁同步、`Process-03` 附录条目；1–2 天。

## 对标材料（先对标，再定语法）

> 只读参考、不复制实现；引用须带版本/commit。目的是**取形态不取内容**。

- **`riscv-unified-db`**：机器可读 ISA 数据的**形态**——`operation()` 挂在编码旁、`resolved spec` 展开、生成器矩阵；**不复制**其扩展体系、CSR、`X[]` 结构。
- **`DADAO-0628`**：Python 解释器（逐指令 handler + 合法性单列）与 Sail 两套独立实现的**经验**——「独立投影同一份散文规范」的纪律。
- **`DADAO-v5-pr4`**：RTL 侧**微操作分层**（24 个 op code + 28 字段 exec descriptor）与「生成器 vs 独立校验器」对偶；**微操作只留在 RTL 层**。
- **`DADAO`（旧仓）**：`ENV-linux` 与 opcodes/runtime 目录的早期编码与运行时假设（历史对照）。
- **仓内既有资产**：`contracts/opcodes.yaml`（编码真源）、`contracts/fp_semantics.yaml`、`contracts/legality_rules.yaml`、`spec/SimRISC-0x` 附录 A、`docs/DDLN/B002`。
- **外部标准形态**：ARM ASL、RISC-V Sail、x86/ARM 手册的「伪代码块」体例。

## 对标维度（讨论提纲）

1. **载体**：operation 写在 spec 正文每条指令旁，还是独立 `.idl` 文件（spec 只保留渲染视图）？
2. **语法**：表达式/语句形态（赋值、条件、位切片、内存访问、异常触发）；是否允许共享函数与参数化族。
3. **粒度**：一条指令一段，还是「族 + 参数」薄 block（264 → ~90 个语义单元）。
4. **单一真源**：spec 正文 ↔ `.idl` ↔ 契约投影 ↔ 测试期望，谁是源、谁是派生、如何机械校验（逐字节 / AST / 语义等价）。
5. **可执行接口**：为可执行参考模型预留什么（签名、状态结构、内存与异常模型），但 M15 **不实现**执行。
6. **不自造第二套规范**：operation 不得成为与正文并列的「第二真源」；冲突时抽取器 fail-closed。

---

## 观察：`ldm.*` 的注释与向量缺口（用户 2026-11-20）

- **1. 注释有误（`ldm.t`）**：`tests/inst/01-load-store/ldm.t_rrri_rf.S:5` 写「`rf0` 作目的合法（按 FCSR 写掩码）」——**不准确**。`.t` 只写目的低 32 位，`rf0` 在此写入窗口内**只有 `[4:0]` 可写**（`[33:32]` 舍入模式与只读 qNaN/SBZ 均保持原值，见 `spec/SimRISC-01 §4` 的写入宽度注）。应改为「只写低 32 位；`rf0` 内仅 `[4:0]` 可写」。`ldm.o_rrri_rf.S:5` 的同句对 `.o` 成立，不需改。
- **2. 缺 `rf0` 作目的的用例（`ldm.t`）**：`ldm.o` 有 `{rf0:rf1}` 合法性用例（`ldm.o_rrri_rf.S:67`），`ldm.t` **没有**（全文件 `rf0` 只出现在第 5 行注释里），而注释宣称它合法 ⇒ 需补一例（同时验「高 32 位保持 + `[4:0]` 写入」）。
- **3. `immu6=63` 边界只在 `ldm.ub`**：`ldm.ub_rrri_rd.S:50-58` 有「最大合法个数 63」整组装入 + 回写；`ldm.ut`/`ldm.uw` 没有（其余 `ldm.{sb,st,sw,t}` 也没有）。建议在 `ldm.ut`/`ldm.uw` 各补一例（至少覆盖 `{rd1:rd63}` 整组 + 回读）。
- **注意**：2/3 会改动对应镜像的指令流 ⇒ 该镜像的「实测总拍数」记录作废（**按指令类的周期表不受影响**，它只依赖同族样本）；改动时在完成区写明需重测的镜像清单。
- **归属**：M15 已收口，建议由 **M17 的 testcases 任务**承接（`m17-testcases-002`，与 `m17-testcases-001` 同批）；注释一条可独立先修（`.text` 不变）。

# M16：gem5 时序模型对齐 chipyard-wuming

## M16 三方差分（Vast arch）批次裁定（用户 2026-11-22，已定；随任务书落地后迁出本文件）

> 用户指示：本轮裁定先集中记在这里，任务书引用本节，避免跑完一两个任务后重复询问。

### 范围与判据

- `tests/arch` **只测 Kaiwu-Vast**：不含 Tiny、不含 linux-user（QEMU user-mode）；U-mode 仍要测（cfx0 umon）。
- cfx 范围：**0/2/3/4/5/15/32/34/63**（umon/smon/hmon/ptw/cache/hart/pmem/time/power）；不含 1 jmon、33 llc、62 uart。
- **中断源、fence、HSU 纳入**；**J 和多核不纳入**。
- 判据：**三方（QEMU/gem5/RTL）签名逐槽一致**；期望值独立派生自 `spec/`/`contract`；不一致由用户裁定（用户是 oracle）。
- 仿真**不进常规门控**（L2/L3）；只作按需/里程碑收口命令。

### 载体

- 优先**同一 ELF** 三方跑（入口在 PA RAM）；做不到的 cfx 用各自载体、签名对齐。
- **不预先造通用启动链**；按 cfx 选最小载体，功能覆盖优先；RTL 侧启动改造按需，不为统一改 BootROM。

### cache

- QEMU 与 gem5 **都补 cache 模型**，复用各自已有其它 ISA 的实现。
- QEMU：`-machine kaiwu-vast,cache-model=off|on`，默认 **off**；`off` = 现有直通（Linux/K0/inst 不变）；`on` = 完整**影子写回 D-Cache** + cfx5 命令面，只给 arch；I 侧只做命令语义（`tb_invalidate_phys_range`），不做 I 阵列；DMA/装载直连底层。
- **Linux 内核现在没有 cache，以后会加**：M16 期间固定 `off`；将来内核加 cache 支持后再接 `on`（登记 backlog）。
- gem5：`cache-model=on` 映射 `--caches`；前置补 `IsLoad/IsStore/IsAtomic`；cfx5 命令复用 ARM `dc cvac/civac/ivac` 的 `Request::CLEAN|INVALIDATE` 机制。
- `cache-model` 与 cfx5 口径（用户 2026-11-22 已定）：**off = cfx5 存在但 no-op**——`cache_exist` 读 0，`cache_ctrl` 写被接受、不报 `CFXREG`、不产生效果；`on` = `cache_exist=0b11`，命令真维护。理由：Linux 内核缺省带 cache 维护逻辑（其它 ISA 不会为“无 cache”单独编译内核），机器配置只决定 cfx5 有没有效果，不决定它是否存在。**off 下非法编码仍报 `CFXREG`**（编码校验不受机器维度影响，用户 2026-11-22 已定）。RTL Vast 始终有 cfx5、Tiny 无（不跑 Linux）。需同步 `integ042t` 期望与 CACHE-27 契约（`m16-spec-002`）。
- **RTL cfx0/2 分两件**（用户 2026-11-22）：先 **A**=`m16-chipyard-019`（寄存器面 + 权限，不改主控制流），再 **B**=`m16-chipyard-020`（U/S 模式进入路由、`switch_run_mode`、异常帧）；A 合入后才派 B。
- **`expected-divergences.yaml`**（用户 2026-11-22 同意）：已建 `tests/arch/expected-divergences.yaml`，永久 3 条（QEMU 时序/替换、gem5 I-Cache 性能、RTL 预取/I-D 一致性）+ 临时 3 条（ADWBFAIL、cfx0/2 U/S 进入、cfx15/32/34 缺口）；每条写影响面 + 裁定日期；临时项在对应任务合入后删除。
- **ADWBFAIL**（用户 2026-11-22 选 C）：正常路径不可达（PA RAM 全可写），**不单列 M16 用例**，登记 GAP（`ISS-515`）；保留 RTL `CASE_ADWB` 手工证据，QEMU/gem5 不加测试专用注入。
- **check-arch-smoke 模式与代表集**（用户 2026-11-22 选 A）：smoke/arch 用 `cache-model=off`（不测 cache，cfx5 的 on 用例进按需 `check-arch-vast`）；`tests/arch` 成型后再重选 smoke 代表集——不需要多、覆盖面稍广、**三个平台分开**（QEMU/gem5/RTL 各自代表），并控制测试时间（QEMU smoke 目标 ≤5 min；RTL 仿真不塞进 L2/L3）。**现在不提前立任务/不选用例**，等 `tests/arch` 成型后由用户确认再排。
- **cfx5 用例覆盖**（用户 2026-11-22 确认）：`m16-testcases-009` 必须覆盖寄存器面、D 侧 clean/invalidate/flush（all/单行/区间、I/D）、DMA 直读可见性、使能门控、I 侧 clean no-op + invalidate 取指重取（**gem5 必须**）；QEMU 时序/替换、gem5 I-Cache 命中/缺失、RTL 预取/I-D 一致性只登记差异；不穷举替换矩阵。
- **HSU**（用户 2026-11-22 选 A）：拆到已有任务，不单独立件——PTE 的 `H/S/U × R/W/X` 进 cfx4 用例（`m16-testcases-010` / `m16-chipyard-018`），运行模式 U/S/H 进 cfx0/2 模式路由（`m16-chipyard-020`）；**J 不测**，未覆盖项写入各任务书。
- **cfx63 power**（用户 2026-11-22 选 A）：单独一件基础用例 `m16-testcases-016`「cfx63 power 基础用例」（寄存器面 + power→hmon 移交，三方；复用 step5 与 `prevcfx.S` 检查点）；不把 step5 启动链当作 cfx63 的完整覆盖。**2026-11-23 用户裁定 B**：`m16-testcases-016` 登记的 `DIV-12`（RTL Vast BootROM 64 KiB vs 契约 4 MiB）按"修 RTL"处置——窗口 base/size 与复位向量规则是硬件，镜像布局是构建/装载侧；`build_step5_bootrom.py` 已产标准 Vast 4 MiB 镜像、资源生成器吃稀疏 hex ⇒ 新立 `m16-chipyard-025`「RTL Vast 4 MiB BootROM（窗口 + 稀疏镜像 + 启动路径）」，完成即删 `DIV-12`。
- **cfx5 的 reset 向量**（2026-11-23，`m16-gem5-024` 复核）：gem5/QEMU 为 `(5<<42)+2^42-64K`、RTL 为 0；`DADAO-12 §3.4` 规定“无内部 SRAM 的 cfx 由平台/实现定义”，且各平台 trap 前都必须写向量 ⇒ **不登记差异**，当前用例显式写向量。
- **cfx5 `cache_enable=0` 口径**（2026-11-22，`m16-chipyard-017` 复核）：只门控维护命令、不旁路正常访存；`DADAO-12 §4.6`/`CACHE-07/08/23/30` 只规定“该侧不被维护”，不要求旁路，与任务书/009 口径一致。命令级 `ADWBFAIL` 不可达登记 `ISS-516`；`CACHE-21` 双侧同选用例缺失登记 `ISS-517`。
- **gem5 cfx5 两轴权限/trap/escape**（用户 2026-11-22 选 A）：补 `m16-gem5-024`——cfx5 进 `kCfxhaMap`，接 `<mode>_cfxtrap/cfxreg/cfxmem/cfxexe`、`trap`/`escape cfx_cache`，与 QEMU/RTL 对齐；H/S/U 下默认仅 hmon，env 打开后允许。
- **`tests/arch` 命名规范**（用户 2026-11-22）：env 目录用 `common/env-{hmon,smon,umon}/`（共享 `common/env.lds`）；汇编统一 `.S`、驱动 `check_*`、生成器 `gen_*`、载体 `<cfx>_<name>.py`、body `<prefix>_<name>.body.S`；不建 `data/`、不在 `tools/` 加 arch 专用脚本、不乱起名。规范已写 `tests/arch/README.md`；现有文件由 `m16-testcases-018` 整理。
- **H/S/U 三模式的 cfx 访问权限**（用户 2026-11-22 选 A）：由 env 负责“权限准备”——用例在 `modes.yaml` 声明 `cfx_access`，env 在降模式前由 hmon 打开该 cfx 的 `<mode>_cfxreg/cfxmem/cfxtrap/cfxexe` 掩码，退出时还原；不放宽默认掩码。`m16-testcases-017`。
- **cfx0/2/15/32/34 的三方用例归属**（用户 2026-11-22 选 B）：不另立 5 件 testcases，写进各 RTL 补实现任务（019/020/021/022/023）；**同一 case 定义/期望只写一份**，RTL 与 QEMU/gem5 复用载体，非必要不为每个平台写三份；由 `check-arch-vast` 按需跑三方。
- **M16 收口执行计划**（用户 2026-11-22 记）：任务清完后，跑一次 `check-arch-vast`，覆盖 QEMU/gem5/RTL 的**代表集**（非全部组合）；QEMU/gem5 目标 ≤10 min，RTL 按需（全量重建约 30 min/次，排主控机空闲或节点）。出一份 `docs/TestReports/M16-三方差分.md`：各 cfx 三方在位、差异、`expected-divergences.yaml` 快照。归档时机仍由用户定。
- **M16 关键路径**（用户 2026-11-22 确认）：QEMU 链 `qemu-001 → qemu-004 → qemu-002 → qemu-003 → testcases-009`；RTL 链 `chipyard-017 → 018 → 019 → 020 → 021 → 022 → 023`；testcases 链 `015 → 016`，`013/014` 等 `021/022` 合入后升三方，`012` 等 `qemu-004`。两条主链并行，同组件串行。
  **020 优先**（用户 2026-11-22 纠正）：每个 cfx 的测试都应在 **H/S/U 三种运行模式**下跑，所以先把 cfx0/2 的 U/S 模式路由（020）做稳，再补 cfx15/32/34；不把 020 挪到最后。各 cfx 用例任务书（009/012/013/014/016/018/019/020/021/022/023）已加“三模式”要求：经 `tests/arch/common/env/` 在 hmon/smon/umon 各跑一次，权限不允许的模式显式标注排除原因。
- **M16 收口判据**（用户 2026-11-22）：**三方一致**（QEMU/gem5/RTL）为准；**有差异必须由用户裁定**，登记 `tests/arch/expected-divergences.yaml`；**不作逐位/逐组合穷举**，但各功能面应尽量覆盖；**任务清完后由用户定何时归档**（不自动立归档任务）。**issue 要求（用户 2026-11-22 选 A）**：M16 引入的 issue 必须关闭或转 GAP 登记（如 `ISS-432` 由 `qemu-004` 关闭、`ISS-515` 保留 GAP）；基线红（`ISS-507`/`ISS-509` 等）保留 open，不作为 M16 收口阻断。
- **tests/arch 运行模式环境**（用户 2026-11-22）：增加 `hmon`/`smon`/`umon` 构建环境，把测试 body 与运行模式分离（进入模式、栈、异常向量、退出、签名区由 env 负责）；`run_arch.py --mode` 选择；每用例标 `modes` 允许集；先迁移 1 个代表用例，其余逐件迁。`m16-testcases-015`。
- **中断源**（用户 2026-11-22；**2026-11-23 按 ADR-0060 改 hart-first**）：两个 cfx 分开测试——`m16-testcases-013`（cfx15 timer）与 `m16-testcases-014`（cfx32 pmem DMA 完成）；**投递目标统一 `cfx_hart`（cfxha 15）的 supv 单向量**，现场/mask/pending 在 `cfx_hart cg9`（pending 位=cause id `1<<17`/`1<<18`，mask 位=源 cfxha 15/32），`escape` 用 `imms18=2` 选 cg9；`m16-chipyard-021` 先补 `cfx_hart cg9`，`022` 再接 pmem 完成中断；`020` 只保留同步路由与两轴 CFXPERM，异步部分移交 021/022。
  M18：`m18-qemu-002`（monitor-first）不合入、留参考；`m18-qemu-003` 被取代；新立 `m18-qemu-004`（QEMU hart-first）与 `m18-testcases-001`（旧探针迁 hart-first），依赖 `m18-spec-002`。
- **异步模型修订（用户 2026-11-23 逐条裁定，落 `ADR-0061` Proposed）**：`spec/DADAO-12 0.8.0-rc` 自相矛盾一事按"改写模型"解决——① 来源掩码归 **monitor**（`cfx0–3 cg8 rc1`，复位全 1，位=源 cfxha），删 `cg9 rc8–rc12` 与各 cfx `cg0–3 rc4`，trap/escape 不再保存/恢复掩码；② 源身份统一 **cfxha**，取消 `1<<17`/`1<<18` 宏 cause（一源 cfx 至多一个异步 cause，细节回源 cfx 读）；③ `src_frame`/`src_pending` **硬件写、软件只读**，帧只由 `escape` 结束、源只在源 cfx ack；④ 同一界面多源**一帧承载**（位图并集），不串行开两帧；⑤ `cg9` 精简七槽、表移 `§4.7`、新增第 5 章异步进入/退出专节；⑥ 精确点写死（上一条已提交、`async_cause_ip`=提交后的 `rb0`）；⑦ **`escape` 暂不改**（保留 `imms18[1]` 选择位）。落地任务：`m18-spec-004`、`m18-qemu-005`、`m16-chipyard-024`，改写 `m16-testcases-013/014`、`m16-chipyard-022`；在跑的 `m18-testcases-001/002`、`m18-linux-021` 与已合入的 `m18-qemu-004`、`m16-chipyard-021` 需按新模型修订。
  2026-11-23 用户裁定：**三件在跑任务按旧口径作废**（`m18-testcases-001`「旧异步探针迁 hart-first」、`m18-testcases-002`「`escape` cg9 向量」、`m18-linux-021`「内核 hart-first 异步入口/返回/调度」），按新模型重排为 `m18-testcases-003`「旧异步探针迁新模型 + `escape` cg9 向量」与 `m18-linux-022`「内核异步新模型」；`m18-qemu-004`「QEMU hart-first 异步仲裁」的修订任务为 `m18-qemu-005`「QEMU 异步模型修订」，`m16-chipyard-021`「RTL cfx15 hart」的修订任务为 `m16-chipyard-024`「RTL 异步模型修订」。
  2026-11-23 用户裁定：**M18 任务只在 M18 会话派发**。`m18-spec-004`「异步模型修订（掩码归 monitor、源索引统一 cfxha、cg9 七槽）」已在 M16 会话开跑（收口后交回）；由 M18 会话派发：`m18-qemu-005`「QEMU 异步模型修订」（依赖 spec-004）、`m18-testcases-003`「旧异步探针迁新模型 + escape cg9 向量」、`m18-linux-022`「内核异步新模型」（依赖 qemu-005）。M16 侧继续：`m16-chipyard-018`「cfx4 RTL PTW/TLB 探针纳管」（在跑）、`m16-chipyard-024`「RTL 异步模型修订」（等 spec-004 合入）、`m16-testcases-009`「cfx5 用例三方跑」、`m16-testcases-013`「cfx15 timer 中断」、`m16-testcases-014`「cfx32 pmem DMA 完成中断 + 同帧多源」、`m16-chipyard-022`「RTL cfx32 pmem」、`m16-chipyard-023`「RTL cfx34 time」。
  2026-11-23 用户裁定 **R2**（就地修订 `ADR-0061`，不新立 ADR）：`cg9` 是**进入瞬间的捕获缓冲**（每次异步进入覆盖、硬件不因 `src_frame != 0` 拒绝、无 `frame_valid`、无软件清 `src_frame`）；入口为「异步进 hart → 关中断窗口搬 cg9+GPR 到 `task_pt_regs` → 进 `cfx_smon`」，smon 为普通系统态、嵌套由软件处理；`escape imms18=2` **不再异步返回**（cg9 捕获后丢弃，返回走 smon/umon）；mask/monitor/源索引/同界多源不变。落地：`m18-spec-005`（spec/契约/旧文档收尾 + 锁）、`m18-qemu-006`、`m18-testcases-003`、`m18-linux-022` 按 R2 改写；`m18-idl-002` 的目标（escape 释放帧）已被 R2 取代，须由 architect 重排。R2 后 `m16-testcases-013/014` 的 `escape` cg9 返回断言同步作废。
- **musl 源树同样过期（2026-11-27，未处置）**：`.work/source/musl` 停在 11-24 09:51，而 `components/musl/patches/arch/dadao/bits/signal.h.patch` 已被 `m18-linux-010`（11-24 23:42）更新 ⇒ `check_patch_tree` 仍报 2 个 problem（其余组件已在 M16 收口前重放：qemu `a8d0796`、gem5 `7db7553`、chipyard `7b1d785`）。musl 归 M18 linux 面、且 `m18-linux-006`（LTP）在跑，M16 不动它；重放+重建会替换安装根 libc，需该会话自行处理。
- **共享安装根过期导致 arch 门控假红（2026-11-27，`ISS-m16-013`）**：`m18-qemu-008/009/010` 合入后 qemu 源树/安装根没有重放重建（树停 11-25、`qemu-system-dadao` `8b49d6d9…`），而 BootROM 已用新 LLVM 重建 ⇒ 新 `escape` 编码在旧 QEMU 上非法，`arch-umon-001..010` 进异常死循环。修复：删源树→`make fetch`→`apply_series.py --component qemu`（`a8d0796`）→`make install-host`（rc=0，`e470dc56…`）；`check-arch-smoke` 与 `run_arch --self-test` 复绿。**口径**：组件补丁合入后必须「重放 + 重建 + `install-host`」，否则 L2/L3 的绿/红都不算证据；`check_patch_tree`（全量，`make check` 内）能抓出「树 ≠ 补丁集」，`--source-state` 抓不出。
- **M16 收口暂停、等 M18 两个 chipyard 任务（用户 2026-11-26）→ 已解除（2026-11-27）**：`m18-spec-007`（0.8.0）重排 `cg9`（rc0–5 入口记录 RO、rc14 switch、rc15 vector）、`cg5`（rc0–3 prev_*、rc8–11 出口意图）与 `escape`（`imms18` 必须为 0）⇒ 现有 RTL/QEMU/gem5 与 `tests/arch/hart`/`pmem`、`check_cfx15` oracle 全部过时（`ISS-m16-012`；master 的 `run_arch --self-test` 已 rc=1）。用户裁定：**暂停 M16 的 chipyard 侧任务（`m16-chipyard-033` 已停、`030` 未派），等 `m18-chipyard-002`（RTL 异步 escape 出口）与 `m18-chipyard-003`（源接口与 cg15）结束、spec-007 全链对齐后再继续**；M16 收口（`check-arch-vast` + 报告）相应顺延。 `m18-chipyard-002/003` 与 `m16-chipyard-033/030` 均已合入；三方差分移交 M20（N40）；**M16 于 2026-11-27 归档**（`.tao/archive/M16/`，95 册）。
- **fence**（用户 2026-11-22 选 A）：先 `m16-qemu-004` 修 `ISS-432`（QEMU 保留集改为 `6–14, 16–31, 35–61`），再由 `m16-testcases-012` 做**基础验证**（all/指定 cfx/六位/保留集采样/`hb≠0`）；**完整覆盖（全部 cfx × 六位）不作验收要求**，未覆盖项登记。
- **cfx_pmem DMA 与 D-cache 一致性**（用户 2026-11-24 裁定 A）：**不保证硬件一致**——软件在 `START` 前对源区间 `clean`、完成后对目标区间 `invalidate`；硬件不 snoop、不自动失效；未按此操作读到旧值属软件错误。由 `m16-spec-003` 落 `DADAO-12 §4.9` + `contract-see`（ISS-531）。
- **RTL cfx15/32/34**（用户 2026-11-22）：三个都补、每个 cfx 一件（`021`/`022`/`023`），串行。**中断源只有 cfx15 的 timer 与 cfx32 的 pmem DMA 完成；cfx34（time）与 cfx63（power）没有中断**（用户 2026-11-22 说明）。
  **2026-11-24 对齐 R2**（`m18-spec-005` 已合入，spec-first）：M16 侧按 R2 重排——新立 `m16-chipyard-026`「RTL 异步捕获缓冲（R2）」（每次进入覆盖、无帧门控、`escape imms18=2 ⇒ CFXESC`）；`m16-chipyard-022`「RTL cfx32 pmem」依赖 `026`；`m16-testcases-013`「cfx15 timer 中断」与 `m16-testcases-014`「cfx32 pmem 完成中断 + 同界多源」的 `escape` cg9 返回/无嵌套断言作废，改为捕获快照、覆盖语义、`escape` 拒绝、掩码/pending/ack。
- **gem5 I 侧自修改**（用户 2026-11-22 选 B，但先证伪）：现有 `cfx5_selfmod.s` 是 base probe（无 cfx5、无 `D|clean`），不能证明 cfx5 I 侧不可用；RTL 是 VIPT 但索引在 64 KiB 页内（`PA[15:0]==VA[15:0]`，无别名），021 用 PA 索引/标签正确。先由 `m16-gem5-022` 补「写码 → D clean → I invalidate → 跳转」的正确用例并修 020 的 monitor 脏行；022 已证伪（正确构造下 I 侧可用），**不需要改取指侧模型**；`m16-gem5-023` 号已用于「off 下 cfx5 no-op」，不再表示取指侧修复。

### 落点

- arch 用例/脚本/数据集中 `tests/arch/<cfx>/`；驱动 `tests/arch/run_arch.py`；矩阵/数据 `tests/arch/`。
- 签名机制（`tests/shared/asm/signature.inc` + host 侧 `signature.py`）集中 `tests/shared/`。
- `tools/` 只放跨 scope 共享；修订 `docs/Process-09` §3/§5/§6/§7：scope 专用脚本随 scope、`arch.yaml` 支持驱动型 case 与 `machine` 字段。
- Tiny 的 `arch-hmon-001` 与 `tests/arch/hmon/` 移出 arch，落 **`tests/unit/gem5/`**（用户 2026-11-22 选 A）；`unit` scope 的 `platforms` 增加 `system`，并登记 `unit-gem5-hmon-001`。
- **门控**（用户 2026-11-22）：`check-arch-smoke` 按新的 `tests/arch` 重写；**`check-arch` 与 `check-arch-smoke` 一致**（同一代表集），L3 的 arch 成员保留，不另跑旧 15 个 min-ROM 探针。

### 阶段与任务（短任务）

- 批次 1：`m16-testcases-004`（三平台 cfx 盘点 + 落点/规范方案，只读）、`m16-testcases-005`（签名脚本迁 `tests/shared/`）。
- 批次 2：`m16-qemu-001`（cache-model + 影子 D-Cache + cfx5）、`m16-gem5-020`（`--caches` + flags + cfx5）、`m16-chipyard-016`（RTL cfx5 补实现）。
- 批次 3 起：cfx4 ptw → cfx5 用例 → cfx0/2/3/63 → cfx15/32/34/中断/fence → 收口（`m16-integ-001`）。
- `m16-chipyard-011` 空号留给总收口或废弃。

> **定位（用户 2026-11-13）**：范围只做 **Timing**（`Minor`/`O3` 对应 `wuqing`/`wuxing`，等其 RTL 出现后再开，见「Milestone 候选」）。设计取向：**保留 gem5 `TimingSimpleCPU` 原汁原味**，只加「每指令延迟」——钩子默认 0、`timing.cc` 仅 1 行、延迟表由周期模型文档现场生成；块传送用微操作展开；访存交给 `NoncoherentXBar` + `SimpleMemory`。`AtomicSimpleCPU` 不动，只作零成本基线。

## 现场：gem5/chipyard 比值 3.1–4.0×，主因是 gem5 取指无 icache

`m16-gem5-007` 实测（同 ELF、`-O2`）：

- `ud`：chipyard 11 476 575 拍 / gem5 35 628 680 拍 ⇒ **3.10×**
- `aha-mont64`：6 949 075 / 25 574 829 ⇒ **3.68×**
- `depthconv`：10 079 080 / 39 767 332 ⇒ **3.95×**

- **归因**：gem5 **取指/基础项占 |Δ| 的 80.2%–87.0%**——`TimingSimpleCPU` 无 icache，每指令 8 拍（7 拍 SRAM 往返 + 1 拍执行）；chipyard 是 8-beat 摊销（~0.06 拍/指令）。次项：chipyard 取指摊销 `A` −1.13…−1.54、分支 `A2` −3.30…−7.77、块复制 `D′` −1.02…−1.67；正项 `B1` 乘法（模型 3 拍 vs 实测 1.00–1.30）。
- **含义**：当前比值**不是周期模型本身的误差**，而是 gem5 配置（无 icache）与 chipyard（8-beat 摊销）的结构差异。要「模型对标」，应先决定是否给 gem5 配 icache 再比（见 N4）。
- **同批发现的模型偏差**（`m16-chipyard-001` 一并复核）：`B1` 乘法实测 ≈1 拍（模型初值 3）；`B3` 除法硬件 1 拍（文档「待实测」、模型 0）。
- **gem5 SE 完全没有 semihosting** ⇒ Tiny 应用在 SE 上不可直接跑；`m16-gem5-011` 已把 `--semihost` 默认改为 **off**（显式开）。

## Kaiwu-Vast on chipyard（TLB / PTW / Cache；用户 2026-11-19 已定口径）

- **现状**：chipyard 只有 `WumingTinyConfig`（SRAM、`useVM=false`、无 MMU/PTW；`WumingCompatCoreParams` 里 `pgLevels=3` 是 RISC-V 残留）；gem5 侧 Vast 已完整（两级步查、cfx 模型、pmem DMA、time/hart），但 TLB 是**单数组 16 条全相联 + 轮转**、超页与普通页混存。
- **用户裁定（2026-11-19）**：只设**一级 TLB、分 I/D**（I/D 分离是**设计**不是实现细节；I-TLB 无 dirty 位）；普通页 **16 条 = 2 组 × 8 路、不设 sectored**；超页 **4 条全相联 + LRU**（4 条就够）；**无特殊条目**（rocket 的 special entry 为 PMP，DADAO 无 PMP）；**gem5 与 chipyard 在这些方面保持统一**（含组相联与超页个数）。
- **WumingVast 恢复（用户 2026-11-19 反悔）**：`WumingVast` 与 **gem5 `TimingSimpleCPU` 的 Vast** 都要做（`m16-chipyard-006/007/008` + `m16-gem5-015`）；**最终目标是上 FPGA**（Genesis2：1 GiB DDR3 + 片上 64 KiB ROM / 512 KiB cfx SRAM / 256–512 KiB cache，见 Vivado 节）。
- **落地方式**：归 **M16**（`milestones-m16.md`，用户 2026-11-19 裁定「这是 M16 的任务」）：`m16-chipyard-006`（核参数/地址通路/`cfx_ptw` 寄存器面）→ `007`（PTW 两级步查 + A/D）→ `008`（I/D TLB）→ `009`（D-Cache）→ `010`（I-Cache + 大存储/地址图）→ `011`（三方差分收口）；gem5 侧 `m16-gem5-014`（TLB 双表 + 2×8 + 4 超页 LRU）。
- **顺序理由**：cache 会改变 M16 已标定的周期基线（`docs/core-wuming-cycle-model.md` 在 SRAM/无 cache 上标定）⇒ **cache 单独排**，不与功能改动混做。
- **待定**：① 分片（`frags`）在 RTL 侧与 cache 的交互（64 KiB 页 = 1024 × 64 B block）；② `spike`/gem5 侧的 PTW 延迟是否要建模（当前 atomic，无时序）；③ `ISS-340`（gem5 Vast 仍 identity，而 spec 要求 `VA = PA + 2 TiB` 内核窗口）何时对齐。

## issues（分诊到本册，2026-11-20）

- `ISS-407`【P3】**覆盖声明与探针状态不一致**（`m13-qemu-004`）：完成区称「另加 sNaN 在右（ft/fo）」两例，但 reviewer 用探针 dump 证明两例机器状态*…
- `ISS-418`【P3】`m13-qemu-006` 证据脚本的 `8/8`（CFXMEM/guest FAIL 数）是**字面期望**而非现场计数 ⇒ 若日后设计变更（例如新增非法例）会**假红**…
- `ISS-426`【P2】`ld.o ra0`/`rd2ra {ra0}` 未丢弃 `[63:54]` 的 SBZ 位：`SimRISC-00 §2.4` 规定 `ra0 = {SBZ(10),RACN…
- `ISS-432`【P2】`fence` 的保留 cfx 集三平台不一致：保留集真源是 `Kaiwu §1.2` + `DADAO-12 §1` 的编号表 = `6–14, 16–31, 35–61`（…
- `ISS-433`【P2】`trap cfx_power` 三平台不一致：QEMU/gem5 进 power 向量、**chipyard 报 ILLI**。`m13-testcases-027` 实测…
- `ISS-435`【P2】`sc` 保留（reservation）粒度三平台不一致：`spec/SimRISC-12 §1`/`ADR-0034 D6` 是**精确地址+宽度**（同字异址写入不应清标记…
- `ISS-440`【P2】`lr`/`sc` 的「另一 hart 对同一精确地址+相同宽度 store ⇒ 清保留」**三平台均无实现路径**：`m13-qemu-014` 删掉整字值 CAS 后，QE…
- `ISS-443`【P1】`sc` 的「异常/中断进入 ⇒ 清保留」**三平台均不实现**（`spec/SimRISC-12 §1` 明列为清除事件）：`m13-testcases-037` 四条路径实…
- `ISS-448`【P3】`WumingDecoder` 的 `rfRows[2]`/`rfRows[3]` 为 `0x7F`，而 `contracts/opcodes.yaml` 同两行为 `0xFF…
- `ISS-467`【P2】`m16-chipyard-003` 收尾后遗留 5 条非阻断 finding（两轮 reviewer 一致）：① `components/chipyard/changelog…
- `ISS-469`【P2】QEMU 的 `cfx2rd`/`cfxtrap` 掩码拒绝时 `CFXPERM` 的 `cause_info` 给的是**指令编码**，而 `contract-see §6.…
- `ISS-473`【P3】`tests/inst/11-cfx/escape_ciii_cfx.S` 链例 12 的注释称「第 3 次到达判红（不挂死）」，实测不成立（`m15-testcases-01…
- `ISS-477`【P2】`tools/testcases/arch/min_rom_probe_035t.py` 的执行通道整体失效（`m15-testcases-020` 实测）：该探针按「裸 RO…

# M17：IDL 可执行参考模型 + 四方差分

## 阶段一批次（用户 2026-11-22 同意）

- **范围**：`m17-idl-005`–`009`（非 FP 222 镜像的四方差分：IDL/QEMU/gem5/chipyard）。
- **验收**：各任务书验收 + `009` 收口（`pending` 清零、222 例四方零红、`check-idl` L2 真跑）；picolibc/embench 只抽样。
- **顺序**：005→006→007→008→009（`006`–`008` 同改 `idl/idl_exec.py`，串行，禁并行派单）。
- **停止点**：`AGENTS.md §1`「提交确认」（批次外、新语义/契约、跨模块、破坏性操作）。

## IDL 可执行参考模型

把 M15 的 `.idl` 跑起来，作**第四方差分参照**（不追求全量第四实现）。

- **已定（用户 2026-11-20）**：册已建（`milestones-m17.md`），**执行器用 Python**，**不依赖 Ruby/`idlc`**（`idlc` 前端 ≈2.6 万行 Ruby、本机 gem 环境不可用）；**golden = IDL**（QEMU/gem5/RTL 均为被测方）。
- **首批四件（已立、已验证）**：`m17-idl-001` 语法子集 + 宽度规则表；`002` Python 解析器（`check-idl-parse` 进 L1）；`003` 执行器核心；`004` 逐指令 trace 与 QEMU 比对。
- **四方差分口径（用户 2026-11-22 定）**：底座 = `tests/inst` 272 镜像（Kaiwu-Tiny），不含 Linux/`ee-user`（musl）/`ee-vast`/arch probes；判据 = **签名槽 + 退出码**四方一致，trace 仅红后归因；阶段一非 FP 222 镜像（`m17-idl-005`–`009`），阶段二 FP 50 镜像（等 FP 语义批）；`make check-idl` 进 L2；picolibc(fast)/embench 只抽样。
- **阶段一（2026-11-22 收口）**：`m17-idl-005`–`010` 已验证；`check-idl` 进 L2（默认 IDL+QEMU，实测 19–33 s）；**222/222** 四方零红（gem5/chipyard 全四方 3 次独立复核，3552 槽）；`pending` 硬断言为空（`010`）；picolibc fast / embench 各 3 例抽样通过（不进判据）。
- **N34（2026-11-22 裁定 A + `m17-idl-011` 落地）**：U04–U09 按 UDB 原文重述进语言规范册 §1.1；U10 = 赋值取低 N 位（UDB §626 同结果，本版固化）；未定义只剩 U01–U03（`.idl` 不使用）。
- **期望差异清单（2026-11-22 用户裁）**：**不建**——实测 0 差异（M13 FP 232/232、阶段一 222/222），白名单无对象；真出现差异再立。
- **`ISS-480`（2026-11-22 裁定）**：`__pycache__` 是**生成物**，`check-manifests-guard` 是**文件系统**双向集合断言（不读 `.gitignore`），故冲突真实存在；修法 = 清单新增 `ignore = ["__pycache__"]`（**数据面**声明，非代码硬编码），且条目须被 `git check-ignore` 判为忽略、不得与已登记项同名；其它游离目录仍红。
- **执行器依据锁（2026-11-22 裁 B）**：`idl/data/exec_anchor.toml` 锁 263 个 op 正文 + `idl/lib/*.idl` 的 sha256；`check-idl-exec-anchor` 进 L1；改 `.idl` ⇒ 必须 `--update` 并在评审里说明实现是否跟改。**不**声称语义等价（`m17-idl-017`）。
- **已知红（2026-11-27 收口实测）**：`check-idl-full` **274/274**、逐指令 trace **274/274**（`m17-testcases-008` 与 `m17-idl-025` 合入后）；M17 已归档（`.tao/archive/M17/`，46 册）。仍在的基线红均非 M17：`check-patch-tree` 52 problem（linux/musl，`ISS-left-004`）、L3 `stack-protector*.ll` 未归类（`ISS-left-005`）、`m18-linux-027` 未入表（M18 会话修）。
- **多 hart 不在范围（2026-11-27 用户裁定）**：不实现、不登记多 hart 相关事项；`ISS-459`（TLB 跨 hart shootdown）已删除，相关语义等将来明确要支持多 hart 时再重新提出。
- **M17 收口授权（用户 2026-11-27，已完成）**：`m17-testcases-008` **正常完成**（经 reviewer Accepted、合入）后，主会话可直接把 M17 置「里程碑」并归档，不再逐次请示。收口前置：`check-idl-full` 274/274、trace 274/274、L1/L3 门控真实 rc、`issues-m17` 清零；归档按 `docs/Process-04`（`check-archive` rc=0）——已于 2026-11-27 完成（`m17-integ-001`，46 册，达成日 2026-11-27）。
- **页表与 ADWBFAIL（2026-11-25 用户裁定）**：页表必须放内存、PTE 一律用内存物理地址；把页表放 BootROM 的构造违反软件契约，不得作载体；**ADWBFAIL 不需要测试**，不构造用例、不登记 DIV；`m17-chipyard-001` 的「PTE 越窗 RTL CFXMEM vs QEMU exit(1)」**不登记**，由 **`m16-testcases-023`**（已立，同口径且含 `DIV-14`/`DIV-04`/`ISS-515` 收口）删除该测试路径；M17 不另立重复任务。
- **`opcodes.yaml` 维护约束（2026-11-25 用户确认 D1–D5）**：yaml 为编码数据真源（非语义真源）、生成器唯一写者、L1 `check-opcodes-repro` 只防漂移、D4 修改流程、16 个直接读点按跨模块处理；ADR-0063 Accepted，新开不并入 0032。
- **权限编码扁平化（2026-11-24 用户裁 B）**：PTW 权限/访存故障只置高位位图（`[32..38]`/`[48..56]`），`CFXPERM`/`CFXMEM` 归一（分别只表示 cfx 掩码/非 PTW 访存）；**删除 `[39] NCFXPERM`、`[57] NONPTW`**；不新增 cause；PTW 的 monitor 路由与退出码属 Vast、待定。先 `m17-spec-001`（ADR-0062 + 影响清单），平台任务待 ADR 定稿后拆。
- **cfx 权限轴（2026-11-23 裁 B）**：补 `cfxreg`/`cfxexe` 掩码 + 2 个拒绝路径载体（`CFXPERM`，272→274）；`cfxmem`（cfx SRAM/MMIO 窗口）单列不建模；平台分叉（如 `ISS-469`）只归因不改组件（`m17-idl-020`）。
- **`check-inst-sig` 退役（2026-11-22 裁 A）**：`check-idl` 在 272 例上对每一方都比同一份 `expected.tsv`，且含四方互比 ⇒ `check-inst-sig` 退出 L2 并删除 target；保留 `inst-signature-data`（期望值生成）、`signature.py` 与脚本 `--write`（`m17-testcases-003`）。
- **gem5/chipyard 常驻门控（2026-11-22 裁 B）**：全四方进 `night-run`（新成员 `idl:four-way` → `make check-idl-full`）；L1/L2/L3 不变（L2 仍 IDL+QEMU）；缺引擎该成员 rc=2 可见、不静默跳过；`m17-idl-014` 落地。
- **阶段二完成（2026-11-23）**：`m17-idl-013` 把 FP 50 纳入四方，**272/272**；016 后 master 复跑 `check-idl-full` 272/272（122 s，四方聚合 md5 同值）；`check-idl-exec-anchor` 进 L1、`check-inst-sig` 退役；台账 20 件已验证。**收口/归档等用户安排**。
- **阶段二（`m17-idl-013`，A 路线）**：FP 50 镜像复用 `idl_fp`；`ISS-397/399/403/409/420` 经核为**过期**（spec 已由 `m13-spec-002/006` 改、覆盖已落 `m13-testcases-011/021/022`），按证据逐条关闭，不另立语义裁定；`ISS-476` 已随 `m15-idl-019` 关闭。
- **Rust 的触发条件**：若随机指令流差分规模上到 >10⁷ 步/例或需并行 fuzz，再把**执行核**换 Rust（边界用 JSON/子进程隔离，前端不动）；否则不引入 Rust 工具链。
- **trap/cfx/monitor 语义**：由 golden 模型按「最小可跑 `tests/inst` 同步异常例」实现——`003` + `006`–`008` 已覆盖；平台差异按 issue 登记，不另立机制。
- **与 M15 的边界**：M15 只结构化、不执行；可执行在此。

## `idl/` 目录与文档结构（2026-11-20 讨论结论；不立任务，暂记）

- **三份文档保持分开**：`diff-vs-udb.md`（UDB 语义差异 263 条）/ `syntax-subset.md`（68 类语法构造统计）/ `width-rules.md`（28 条宽度规则 + 10 条未定义）服务不同读者，并入一份会变杂烩；`syntax-subset` 与 `width-rules` 属同一类（实现口径），合并只省一个文件、要改 16 处引用 ⇒ **收益小，暂不动**。
- **AST fixture 保留**：`sha256` 锁挡「源被改」（`idl/*.idl` 12 份 + `lib/fp.idl`），`idl_parse_fixture.json` 挡「同样的源、parser 输出被改」（parser 重构时的语义漂移）。二者不可互相替代；等 `m17-idl-003` 执行器成为真正 oracle 后，可降级为只校验构造签名。
- **目录整理（折中方案，待 `003` 合入后做）**：books 留根目录（`idl/SimRISC-01..12.idl` 被 55 个文件引用），只分三处——
  `idl/tools/{render.py,subset_stats.py,idl_parser.py}`、`idl/data/{idl_parse_cases.toml,idl_parse_fixture.json}`、`idl/docs/{syntax-subset.md,width-rules.md,diff-vs-udb.md}`。
  需同时改：`idl_parser.py` 的 4 个路径常量、`subset_stats.py`/`render.py` 扫描面、`manifests/dir-guard-roots.toml` 注册三个子目录、三份 `.manifests.toml`、Makefile 目标与引用清扫（`check-dirs`/`check-knowledge-refs` 兜底）。预估 1–2 h。
- **新增语义库的固定三步**（`lib/` 以后会加整数/向量库）：① 放文件；② `idl/lib/.manifests.toml` 加一行 `[files."x.idl"]` + sha256（否则门控红）；③ 更新 `syntax-subset.md` 第 1 行与第 11 行的「12 册 + `lib/fp.idl` / 共 13 个文件」。工具侧零改动（三处都是 `glob("lib/*.idl")`）。

## issues（分诊到本册，2026-11-20）

- `ISS-362`【P1】gem5 SE（dynamic）`MultiSource/Benchmarks/FreeBench/neural` **oracle mismatch**： 输出长度相同（35…
- `ISS-367`【P1】gem5 SE（static）`MultiSource/Benchmarks/FreeBench/pcompress2` oracle mismatch：gem5 跑完（440…
- `ISS-397`【P1】按新规则（IEEE-754 2019 为准）需审计的 FP 偏离清单：① **`fo2ft` 溢出恒 ±Inf** —— `SimRISC-07 §1.4`/`contract…
- `ISS-399`【P2】**`spec/SimRISC-07 §2.5` 的 FMA 溢出表述与 IEEE §7.4 同类冲突**（`m13-spec-002` 发现、未在其范围内修）：原文「融合乘加…
- `ISS-403`【】【P2·**已部分澄清**】`fo2ft` 的 `OF` 判定口径：`m13-gem5-007` 的 reviewer 用 IEEE 754-2019 §7.4 原文 + 实测…
- `ISS-409`【P2】**FP 指令计数的三个口径不一致**：`discussing.md` 写「47 条」，`spec/SimRISC-07` 附录 A 列 **52** 行，`contracts…
- `ISS-416`【P2】**`tools/spec/generate_opcodes.py` 与 `contracts/opcodes.yaml` 漂移**（`m13-spec-005` 发现）：自 …
- `ISS-420`【P3】FMA 溢出的 70/48 格矩阵**没有常驻门控**：`m13-qemu-008`（QEMU 本就合规）与 `m13-gem5-009`（gem5 本就合规）只把格子放进各自…
- `ISS-447`【P2】`check-spec-refs` 对**标题型引用**不校验章号：`m13-spec-011` 复核时把 `contract-isa` 里的 `[SimRISC-00 §5.…
- `ISS-475`【P3】`m15-idl-003` 证据脚本的「散文零改动」断言取 `HEAD` 作基线 ⇒ 提交后恒真（`m15-idl-003` 复核查出）：`run.sh` 用 `git dif…
- `ISS-476`【P2】`ftsclb_orrr_rf` 的临时写法在指数极值处会下溢（合 §2.1/IEEE 应为溢出）：`e64 = off + n` 以 64 位有符号视图越过 2^63 变负 …
- `ISS-480`【P2】`idl/` 的双向目录集合门控与 `__pycache__` 冲突：任何 `import idl.render`/`idl.idl_parser` 都会生成 `__pycac…
- `ISS-481`【P3】签名流在 QEMU/gem5 上实际走逐字节 `SYS_WRITEC` 回退：两平台的 `SYS_WRITE` handle 1 需先 `SYS_OPEN(":tt")`，未打…

# M18：Linux 测试集（含 K6 入口批次）

## Linux 测试集（选择与修复）

- **已定（用户 2026-11-20）**：册已建（`milestones-m18.md`）。**K6 从 M14 移入**（原 `m14-linux-032/033/034` → `m18-linux-001/002/003`）作为入口批次；**M14 收口判据收到 K5（`m14-linux-029`）+ K3 退役**，M14 不再声称「能当 Linux 用」。
- **已定（用户 2026-11-22）**：**两套件都跑**（`kselftest` 先、`LTP` 子集后，共用运行骨架）；**开发阶段用测试驱动内核完善，不迁就现状**——缺 `ldso` 就补、4 KiB 页假设的用例改成 64 KiB 页、客观无法完成的用例记录原因/证据/复评条件，禁静默跳过。口径全文已迁 `milestones-m18.md`「测试集口径」。
- **批次授权 M18-A（2026-11-22）**：`m18-linux-005`（测试集运行骨架 + kselftest 试点首轮分诊）、`m18-infra-002`（musl ldso 动态链接闭环）；停止点按 `AGENTS.md §1`。
- **未决**：① 首轮基线通过率目标（首轮分诊后再定）；② LTP 子集清单与按子系统分片；③ 测试适配补丁的长期承载（试点先落 `tests/unit/linux/suite/patches/`，收口前评估是否并入组件补丁集）；④ 节点 RTL Linux 的前置（需 MMU/TLB，非本册）。
- **已知缺口**：`pthread` create/join（`m14-linux-029` 判为 K6 范围）尚无任务书；用户 2026-11-20 定「建册时再定」⇒ 待后续批次补立。
- **cfx5 维护（Linux，待 M16 前置）**：`arch/dadao/include/asm/cacheflush.h` 现在是空宏（`flush_dcache_page`/`flush_icache_range`/`flush_icache_user_page` 全为 `do {} while (0)`）；要补成 cfx5 的 clean/invalidate/flush，DMA API 加 clean/invalidate。**前置：M16 的 QEMU `cache-model=off|on` 语义稳定**（off = cfx5 存在但 no-op、on = 真维护，见 M16 节裁定）；M16 QEMU 准备好后再拆任务，不提前立。
- **当前状态**：K6 五件已验证；套件级回归为空白，M18 主体未拆解。

## issues（分诊到本册，2026-11-20）

（无）

# M19：FPGA-Tiny

## Vivado

- **已定（用户 2026-11-20）**：**FPGA-Tiny 提前到 Minor+wuqing 之前**，独自成册 **M19**（`milestones-m19.md`）；**FPGA-Vast 归「未立册方向」，不预留里程碑号**。Vivado 装**部分节点**，装完更新 `nodes.md`，派单按 `remote.py status` 选机；版本须锁进 `manifests/`。
- **漏项（已核）**：chipyard 的 `fpga/fpga-shells/xilinx/` **没有 Genesys2**（只有 vc707/arty/arty_a7_100/nexys_video/vcu118/zcu102/alinx_axku040）⇒ M19 要新写 shell。
- **当前状态**：尚无内容（**尚无一次综合实测**）；以下是用户 2026-11-19 的初步方向与手头数据。
- **目标板卡 / 器件**：**Genesys2**（Digilent），`XC7K325T-2FFG900C`（Kintex-7，-2 速度等级）（厂商参考手册，运行期下载、未入库）。
- **器件资源（手册原文）**：**50,950 logic slices**（≈203,800 LUT6 / 407,600 FF）、**块 RAM「close to 16 Mbits」= 16,020 Kb = 445 × RAMB36 ≈ 1.91 MiB**、840 DSP、板载 **1 GiB DDR3**（32-bit/1800 Mbps）、32 MiB 配置 Flash。
- **用户初步想法（2026-11-19）**：FPGA 上先跑 **Kaiwu-Tiny**，**SRAM 缩为 256 KiB**（不接 DDR）。
- **BRAM 预算（64 位宽折算）**：64 位下 1 块 RAMB36 = **512 × 64 bit = 4 KiB**。
- **Vast 的存储划分（用户 2026-11-19 纠正）**：**Vast 不设「主 SRAM」**——主存就是 DDR3；片上 SRAM 只给**多个 cfx 各自使用**（合计约 **512 KiB**）；此外要加 **TLB + cache**，cache 规模按 **256 KiB 或 512 KiB** 考虑。
  - BootROM 64 KiB ⇒ **16 块**
  - cfx SRAM 512 KiB ⇒ **128 块**
  - cache 256 KiB ⇒ **64 块**（合计 **208 / 445 = 47%**，余 237）
  - cache 512 KiB ⇒ **128 块**（合计 **272 / 445 = 61%**，余 173）
  - 余量还要容纳：核（wuqing ~2 万 LUT 量级）、**MIG**（DDR3 控制器，含 FIFO）、UART、调试。
- **Tiny 的预算（用户初步想法：SRAM 缩 256 KiB）**：BootROM 64 KiB = 16 块 + SRAM 256 KiB = 64 块 ⇒ **80 / 445（18%）**，余 365 块给核/cache/UART。
- **空间够不够（实测/估计依据）**：`tests/inst` 单镜像 ≈ 40 KiB（`inst_tiny.lds` 布局）；**Embench 实测最大 66.2 KiB**（`nsichneu` O0，按 ELF `LOAD.memsz` 求和，76 个 ELF 现场统计）；picolibc 未实测（现每次现场构建）；栈建议 **16 KiB**、堆建议 **32 KiB** ⇒ 峰值 ≈ **114 KiB < 256 KiB**。
- **DDR 的必要性（用户 2026-11-19 修正）**：**Tiny** 不上 DDR 只能缩 SRAM（256 KiB）；**Vast 必须上 DDR3**——它没有主 SRAM，主存 = DDR3（PA RAM 从 2 GiB 缩到 **1 GiB**），BootROM 从 4 MiB 缩到 **64 KiB**。⇒ **Genesys2 可以跑 Vast/Linux**，前提是接 MIG；裸机 Tiny 则完全不接 DDR。
- **落地要点（待立项）**：新增 profile（如 `tiny-fpga`：ROM 64 KiB + SRAM 256 KiB），**不改** `Tiny` 本体；`DadaoConfigs.scala` 加 `WumingTinyFpgaConfig`；`+loadmem=` 窗口按新 SRAM 参数化；`tests/ee-tiny/*.lds` 的 SRAM 区参数化（现在 `picolibc_tiny.ld` 写死 8 MiB 布局、栈 4 KiB）。
- **需用户授权**：`spec/Kaiwu §1.1` 目前冻结「SRAM 8 MiB」，新 profile 需在 spec 补一段「FPGA 实现可用缩减 profile」。
- **待定**：① 是否保留 8 MiB 地址窗口、只实现前 256 KiB（不建议：会出现「写了读不回」）；② 栈/堆水位实测方法（栈填 `0xA5` 扫高水位 + `sbrk` 记峰值）是否立任务；③ 首次 Vivado 综合的判据（时序收敛频率、LUT/FF/BRAM 占用阈值）。

- **已定（用户 2026-11-24）**：
  - 应用入口重定到 `SRAM base + 0x100`（不再是 `0xffff_ff01_0100`）；
  - BootROM 布局重调；所有测试向量的入口与布局重调；
  - **M16/M17 收尾后**统一调整 Tiny 配置与测试布局；
  - 未明确的事项不默认同意。
- **已定（用户 2026-11-27，FPGA Tiny 硬件几何）**：
  - **Boot 存储 = TL ROM 8 KiB**（`0xFFFF_FFFF_0000`）；不是 ITCM 取指口；hmon 源在 ROM，按 §6.2 复制到 hmon SRAM 执行；
  - **hmon SRAM 8 KiB**（`0x0FFF_0000_0000`）；
  - **主 SRAM 256 KiB**（`0xFFFF_FF00_0000`）；
  - **入口 `0xFFFF_FF00_0100`**（`base + 0x100`）；
  - BRAM：主 SRAM 64 + ROM 2 + hmon 2 = **68 / 445（15.3%）**，余 **377** 留作后续使用（本册不展开）。
- **初步方向 / 建议（未裁，见 `N44`–`N48`）**：
  - TSI ↔ power 优先 **SRAM mailbox**（不新增 cfx 桥）；
  - `tohost/fromhost` 放 SRAM 固定字，配 `signature + done/exit`；
  - cfx_uart 只开最小轮询版（前提是物理 UART 能与 TSI 复用）；
  - fesvr 只复用 `tsi_t` 协议，64 位/大端在 host 侧处理。

## issues（分诊到本册，2026-11-20）

- `ISS-429`【P2】节点上的 chipyard 模拟器在**固件/hex 变更后不会自动失效**：`sims/verilator/simulator-chipyard.harness-Wuming…
- `ISS-451`【P3】qemu 二进制 md5 依赖**源树 git 状态**：`scripts/qemu-version.sh` 用 `git describe --dirty`，源树脏时版本串带…
- `ISS-453`【P3】chipyard sim 二进制的 md5 只在**同一时段/同一环境**内可复现：`m16-chipyard-002` 复核从同一改前源码（`983612df` 补丁态）独立…
- `ISS-474`【P3】chipyard 构建必须用 chipyard 自带 conda 环境（`components/chipyard/README.md:197` 已写明，我未照做，连续失败 4 …

# M20：gem5 Minor + chipyard wuqing

## 流水线处理器核（gem5-minor / chipyard-wuqing）

- **已定（用户 2026-11-20）**：册已建（`milestones-m20.md`），Minor 与 wuqing **一起开发、对比验证**；**golden = wuming RTL**（两边各自先对齐 wuming，都稳了再做直接对比）。首两件：`m20-gem5-001` Minor 接入、`m20-chipyard-001` wuqing 规格 + 骨架（规格先行）。
- **前置**：`m17-idl-003` 的逐指令 trace 格式；`m16-chipyard-010`；M19 的 FPGA 资源实测（任务待补，反推 wuqing 参数）。
- **当前状态**：gem5 侧只用 `TimingSimpleCPU`（加每指令延迟的钩子），Minor 尚未接入；chipyard 侧**只有 `WumingTinyConfig`**（SRAM + cfx 测试机、无 MMU/TLB），**`wuqing` 的 RTL 为零**。
- **周期**：Minor 与 wuqing 的周期表**必须重标**——现有 264 行是按 `TimingSimpleCPU` + Wuming SRAM 实测标定的，不能搬。
- **前置条件（用户 2026-11-19 追加）：随机指令流差分测试**，参考 RISC-V 的 `riscv-dv` 思路——在接入 Minor / `wuqing` **之前**先具备「随机生成合法指令流 + 多模型逐指令比对」的能力，否则流水线核的时序/功能差异会被定向向量掩盖（定向用例只覆盖已知路径）。
  - **TestRIG**（**RISC-V International 官方项目**，比 `riscv-dv` 更接近我们要的形态）：用 **QuickCheck**（Haskell 属性测试）**生成随机指令流**，经 **DII 接口**（Design-Under-Test Interface）喂给**两个实现**，比对两侧 **RVFI trace**（RISC-V Formal Interface：逐指令的寄存器/内存读写与提交记录），不一致时**自动收缩（shrink）出最小反例**。两条可借的东西：① **RVFI 式逐指令 trace** 作为比对载体（比「比对最终内存」强得多，能定位到哪一条指令、哪个字段）；② **属性测试 + 自动收缩**（反例从几千条缩到十几条，才可能人工归因）。
  - 待定：生成器的合法性约束来源（`contracts/opcodes.yaml` + `legality_rules.yaml` 派生，**不照抄 riscv-dv / TestRIG 的 RISC-V 约束**）；比对模型组合（QEMU / gem5 / RTL / IDL 参考模型取哪几方）；失败归因判据（谁是 golden）；**DADAO 侧要不要先定义「DII 等价接口 + 逐指令 trace 格式」**（没有它，RVFI 这套方法论落不了地——可能要先为此立一个 infra 任务）。
- **待定**：Minor 的 `initiateAcc`/`completeAcc` 两阶段是 `ADR-0057` 在 `TimingSimpleCPU` 上先验证；迁到 Minor 时周期表哪些行仍然生效。

## issues（分诊到本册，2026-11-20）

- `ISS-345`【P3】gem5 SE futex 细节与 Linux/QEMU 不完全一致：`FUTEX_UNLOCK_PI` 未校验调用者是否为 owner （Linux 返回 EPERM）；`F…
- `ISS-361`【P1】gem5 SE 长尾 **72/72 在 3600s 仍超时**（qemu 侧 72/72 全 pass），且最小时耗例 （`functional/clocale_mbfunc…
- `ISS-363`【P2】gem5 `tinyEnter` 直接取 `switch_run_mode` 作为新运行模式：guest 先把该寄存器写成 !=3 再触发同步异常，就会**离开 hypv**…
- `ISS-471`【P2】`tools/gem5/check_tiny_hmon.py` 有与 semihosting 无关的预存在红（`m15-testcases-018` 复核时发现）：期望 `ca…
- `ISS-472`【P3】gem5 `nodeEscape` 缺 QEMU 的 `saved_intr_mask_valid` 守卫（`m16-gem5-013` 复核查出）：从**同步异常帧** `e…

# 未立册方向


## 架构符合性测试套件（参考 `riscv-arch-test` / ACT）

- **参考对象**：`riscv-arch-test`（ACT）——RISC-V International 维护的**架构符合性测试套件**：每条指令一组自检用例，把结果写进固定**签名（signature）区**，由框架与参考签名比对；用例用统一宏（TEST_* / RVTEST_*）表达，天然适配「换一个核就重跑」。
- **当前状态**：尚无内容。本仓现有 `tests/inst/**` 是**逐指令语义向量**（期望值内联、三方差分），与 ACT 的「签名 + 参考签名」形态不同：前者证明「语义对不对」，后者证明「实现是否**符合规范**（可移植性/合规）」。
- **为什么值得单列**：M15 的 IDL reference model + `tests/inst` 已能测语义，但**缺一个「规范符合性」的对外可交付物**；ACT 的形态（每题固定签名、可跨实现比对）是现成的模板。
- **不能照搬**：ACT 的用例是 **RISC-V 指令**（`RV32I/RV64I/M/A/F/D…`）与 RISC-V 的陷阱/CSR 模型，与 DADAO（四组寄存器、16 位立即数分片、`rd0/rb0` 特殊、cg/cfx 模型）全部不同 ⇒ **只借方法论与框架形态**，用例须从 `contracts/opcodes.yaml` + `spec/SimRISC-*` 重新派生。
- **待定**：① 覆盖口径（全 263 id？还是按册分层）；② 签名格式与存放位置（`tests/data/`？）；③ 比对组合（IDL reference model / QEMU / RTL 取哪几方做 golden）；④ 与 `tests/inst/**` 的分工（避免两套向量重复维护）。


## 乱序处理器核（gem5-o3 / chipyard-wuxing）

- **当前状态**：同上，O3 与 `wuxing` 均未开始；gem5 O3 的访存两阶段与 `ADR-0057` 的 bundle 续跑模型需要重新评估。
- **开启条件**：`wuxing` RTL 可用。
- **待定**：乱序下每指令延迟钩子是否还成立（钩子假设顺序退休），或需改为对拍式建模。

## LFS

- **当前状态**：尚无内容。
- **立项时需补**：LFS 的定位（构建缓存 / 大文件载体）、与 `.cache/` + `manifests/` 锁的关系、容量与清理策略。

## 向量支持

- **当前状态**：尚无内容（spec 与 encode 层尚未定义向量扩展）。
- **主要目标（用户 2026-11-19）**：向量指令扩展的**主要目标是支持各类密码算法**（国密 SM 系、ZUC、FIPS 系等）——即向量通道要能高效承载分组密码、杂凑、流密码、大数模运算的数据并行部分。
- **立项时需补**：先由 spec 定义（长度/掩码/寄存器组语义），再谈编码、`.idl` operation、测试向量与差分（QEMU/gem5/chipyard 三方能力矩阵）。
- **测试集候选（用户 2026-11-19 提出，待评估）**：
  1. **CAVP**（Cryptographic Algorithm Validation Program）：NIST 的算法验证项目，为 FIPS 批准 / NIST 推荐的密码算法提供**已知答案测试向量**（KAT），并定义黑盒验证流程。定位 = **已知答案**来源，覆盖标准算法；
  2. **开源实现交叉 oracle**：以独立开源实现作第二份真值，做逐字节差分。
     - **GmSSL**：国密专用，SM2/SM3/SM4/SM9/ZUC 齐全；
     - **Tongsuo**（原 TaSSL，OpenSSL 国密分支）：`test/` 自带向量，如 `sm3_internal_test.c`、`evpciph_sm4.txt`；
  3. **Wycheproof**（Google）：面向**密码库**的测试向量集，重点是**已知攻击与畸形输入**——每组向量标注 `valid`/`invalid`/`acceptable` 的**期望结论**，覆盖非规范编码、截断/篡改的标签与签名、弱/异常密钥、边界长度等。定位 = **对抗性输入**来源，补 CAVP 只有「正确答案」的缺口。
- **候选用途（主会话整理 2026-11-19，未裁定）**：① 密码/PQC（已定主目标；PQC 的 NTT 蝶形要 32/64 位模乘模加）；② 内存搬移（`memcpy`/`memset`/页清零/`uaccess`，内核与 libc 立刻收益，且能顺带验证向量状态保存）；③ 窄整数点积（覆盖量化推理、DSP、媒体 SAD/DCT）；④ 字符串与位操作（`shuffle`/`permute`/位扫描/压缩解包）；⑤ 端序转换（本核**大端**，与网络序/小端数据交换频繁，向量化 byte 置换收益明显）；⑥ 数据库类过滤与 compress；⑦ 浮点向量（收益大但代价大：精度口径/时序/上下文，建议二期）。
- **立项时必须同时定的三件（主会话整理，未裁定）**：① **状态保存**——向量寄存器组进入 `switch_to` 与信号帧，是否惰性保存要早定（`m14-linux-017` 刚打通内核帧往返，再叠加会显著抬高切换成本）；② **ABI**——caller/callee-saved 划分直接影响所有库的调用约定（需立 ADR）；③ **异常语义**——部分生效、越界 lane、非对齐访问的 fault 口径必须逐条进 spec，否则三方模拟器必然分叉。
- **评价要点（待定）**：两类来源都只覆盖**算法结果**，不覆盖**向量 ISA 自身**（编码/掩码/越界/原子性）——编码层与执行层向量仍需自建（`docs/Process-05` 一能力一向量），两来源只作算法正确性的 oracle；另需明确「跨实现差分」在国密算法上的口径统一（填充、端序、参数缺省）。**Wycheproof 的向量多落在「算法 API 的输入校验语义」层**（如 AEAD 标签校验、签名编码合法性），不是向量指令本身能直接吃的东西 ⇒ 它的用处是：等密码库在 DADAO 上跑起来后验证「拒绝路径」是否与规范一致，以及为向量指令的**边界/非法输入分支**提供用例素材。


## FPGA-Vast（未立册；不预留里程碑号）

- **内容**：DDR3（MIG）接入、cache（256/512 KiB）、Linux 外设（UART/定时器/设备树）、资源预算实测后校正。
- **前置**：M19 的 Genesys2 shell 与资源实测（复用同一 shell 骨架）、`m16-chipyard-009/010`、M18 的 Linux 套件。
- **不预分配里程碑号**（用户 2026-11-20）：等 Tiny 上板与 Vast RTL 稳定后再立册。

## SBI 的设计与开发（**里程碑号待用户定**；用户 2026-11-24 立案，暂不立册）

- **裁定**：新增里程碑**「SBI（主管系统二进制接口）的设计与开发」**，**参考 OpenSBI 进行**。**号位由用户 2026-11-24 明确：等用户来定**（当前活册已用到 M20，M21 不自动占用；定号后再建 `milestones-m<NN>.md` 与本条目迁入）。
- **现状事实**：`spec/DADAO-22-SBI-主管系统二进制接口.md`（**0.8.0-rc**）已给出调用约定与 umon/jmon、smon、`cfx_ptw`（地址转换/TLB）、`cfx_cache`、`cfx_hart`、`cfx_llc`、`cfx_pmem`、`cfx_time`、`cfx_uart` 各节；同族有 `DADAO-12-SEE`、`DADAO-23-HBI`。但**当前只是规范 + 最小探针**（M14/M18 的 K0–K6 用自研 hmon/smon 起步），没有独立固件层的 SBI 实现，也没有 OpenSBI 作为组件。
- **OpenSBI 现状**：仓库内仅在 chipyard 子模块锁（`software/firemarshal/boards/default/firmware/opensbi`）与只读参考 `.cache/refs/vivado-risc-v` 里出现，**未作为 `components/` 组件接入**（无锁、无补丁集、无 `.cache` 裸仓库）。
- **首期范围（用户 2026-11-24 二次裁定）**：**先做扩展层，不做独立固件**。即按 `DADAO-22-SBI` 把各核芯功能扩展的调用语义逐条做实（umon/jmon、smon、`cfx_ptw`、`cfx_cache`、`cfx_hart`、`cfx_llc`、`cfx_pmem`、`cfx_time`、`cfx_uart`），挂在现有 monitor/探针路径上验证；**不**先做 M-mode 固件、不改引导链、不 fork OpenSBI。OpenSBI 只作**设计参考**（扩展注册/错误码/状态机/DEVICE 树解析的既有做法），不引入其代码。
  - 由此收敛：上述待裁定的第 1、3、4 条按此口径先搁置（不做固件 ⇒ 不涉及 fork 与 hmon/smon 替换）；第 6 条（是否新增 `components/opensbi`）本轮**不做**。
  - 仍需裁定（缩小后）：① **扩展优先级顺序**（建议先 `cfx_time`/`cfx_uart`/`cfx_pmem` 这类已在 K0–K6 用到的，再 `cfx_hart`/`cfx_ptw`/`cfx_cache`/`cfx_llc`）；② 每扩展的**验收平台**（QEMU 单平台先行，还是与 gem5/chipyard 三方一致）；③ 与 RISC-V SBI 扩展清单的**取舍**（哪些语义对齐、哪些按 DADAO 自有）；
- **立册前必须裁定（未定，逐条问用户）**：
  1. **参考方式**：① fork OpenSBI 改造成 DADAO 后端（借其 hart 状态机/扩展注册/设备树解析/打印框架）；② 只借架构与接口分层、自研实现；③ 混合——先 fork 拿骨架、把 SBI 调用层换成 DADAO `trap cfxha` 约定。
  2. **SBI 与 RISC-V SBI 的关系**：DADAO-22 的 `trap cfxha, immu18` 与 RISC-V ecall 不同 ⇒ 需要明确「接口语义按 DADAO-22、扩展清单是否对齐 RISC-V SBI（TIME/IPI/RFENCE/HSM/CPPC 等）」。
  3. **目标平台与形态**：M-mode 固件 ELF？覆盖 QEMU / gem5 FS / chipyard RTL / Genesys2（M19 shell）中的哪些？tiny 与 vast 是否同源。
  4. **与现有 hmon/smon 的关系**：替换、并存、还是分阶段（先 smon 扩展 → 再独立固件）。
  5. **交付与验收判据**：Linux 经 SBI 引导成功（替代当前直连 monitor 路径）、`cfx_time`/IPI/hart start-stop/RFENCE 等扩展逐条可用、三平台签名/引导一致；是否需要 `check-*` 门控与三平台矩阵。
  6. **工程面**：是否新增 `components/opensbi`（锁 + 补丁集 + `.cache` 镜像 + 节点 synced），以及版本/许可（BSD-2-Clause）记录与 `manifests/` 锁口径。

## 未立册方向（2026-11-25，原 M20 内容转出）

用户 2026-11-25 重定 M20 为「修完可修 issue + 定四方差分/夜跑基准」，原 M20 的两项内容**不占号**，暂列于此，待后续立册：

- **gem5 Minor 接入**（原 `m20-gem5-001`，估 4–6 天）：`initiateAcc`/`completeAcc` + `ldm/stm` 微操作 + trace；与 wuming 对拍 ≥20 例。前置：逐指令 trace 格式（`m17-idl-003`）、访存时序（`m16-gem5-006`）。
- **wuqing 微架构规格与 generator 骨架**（原 `m20-chipyard-001`，估 5–7 天）：规格先行；资源与 Genesys2 预算对账。前置：`m16-chipyard-010`（I-Cache）、M19 的 FPGA 资源实测（任务待补，反推参数）。
- 两者同属「golden = wuming RTL、Minor 与 wuqing 各自先对齐再对比」的路线（用户 2026-11-20），立册时按该口径重写，不与新 M20 的 issue 清理混算。

## issues（backlog，2026-11-20 分诊）

- `ISS-355`【P2】`tools/gem5/build_gem5.py:191` 在 运行期目录 不存在时抛 `ValueError`： 首次 `make build-gem5` rc=2，需先跑…
- `ISS-356`【P3】`check_milestone_tasks.py` 两处基线残留：① 新式核验册名 `mNN-<module>-*` 不被 `MBOOK_NAME_RE` 命中，会按「无 m…
- `ISS-366`【P2】`run_engine_ratio.py` **逐套件串行**执行（`for suite in selection: for engine: run_driver`）： 当某分…
- `ISS-372`【P2】`run_pool` 与派单流程 4 项缺陷（`m13-testcases-008` 现场发现）：① 队列键只有 `case`，同一 case 的 static/dynamic…
- `ISS-373`【P1】**并行任务共享安装根导致互相打断**：`m13-qemu-002` 重建共享 `.dadao/` 安装根 QEMU 时，`m13-gem5-005` 正在跑的 `check-…
- `ISS-377`【P1】**任务收尾未做「修改文件 ↔ git 对账」导致交付文件丢失**：`m13-gem5-005` 完成区声明新增 4 个文件（`tests/arch/hmon/tiny_hmo…
- `ISS-379`【P2】`make check-arch` / `check-arch-smoke` 在本机 `EXIT=2`：`CMake Error: The source directory "…
- `ISS-384`【P2】**需用户裁定**：`m13-spec-001` 只授权就地修订 `ADR-0004`，但两处活正文仍写旧 guest 分区——`ADR-0009 D5`（decision 正…
- `ISS-389`【P2】**任务 worktree 的 `.work/` 未软链到主工作树时会从零编 LLVM（13 GB）并撑爆 tmpfs**（`m12-chipyard-012` 实测）。主工作…
- `ISS-393`【P2】**把「仍在跑」写成「全部跑完」**：`m13-testcases-009` 收口时依据 3 份 ratio JSON 判定 A 组长尾「48 h 内全部跑完」，但 runne…
- `ISS-395`【P2】**并发派单事故：改变差分参照的任务与使用该参照验收的任务并行**。`m13-qemu-003`（改 QEMU 比较族 NV 语义）与 `m12-chipyard-013`（以…
- `ISS-408`【P3】`m13-testcases-011` 文档级：① 完成区「L1 4 红」实为 **5 红**、`check-patch-tree` 实为 **6 条**（chipyard 4…
- `ISS-411`【P3】`tests/inst` 汇编重构**仅剩 1 项遗留**：`st.o rb0`（源 = 被测指令自身地址）未覆盖 —— 宏层拿不到该地址，`tests/inst/MIGRAT…
- `ISS-412`【P3】`m13-testcases-012` 文档级：① **encoding 类实为「寄存器字段极值 + 语义」而非 mask/value 校验**（审阅记录曾声称「已在 §2 与…
- `ISS-415`【P3】`m13-spec-004` 完成区用「根 `README` 在研列未变」佐证 `DADAO-12 0.7.3-rc` 未发布，但 README 该列实为 `0.7.2-rc`…
- `ISS-417`【P3】`m13-spec-005` 的残留扫描面偏窄：`checks.py` 的 S11–S13 只扫 `spec/` 与 `contracts/`，不含 `docs/DDLN/` …
- `ISS-425`【P2】LLVM DADAO **CodeGen 侧** `DADAORegisterInfo.cpp` 仍以 `DADAO::RBSP`（= SP）作 RA 寄存器，与 MC 侧（`…
- `ISS-427`【P2】节点组件树（运行期目录<name>`）的 `dadao: <name> patch series` 提交会随主控机补丁集演进而**无法重放**：`apply_series --…
- `ISS-428`【P2】节点（server207）上 `tools/qemu/k0_boot_probe.py` 复跑失败（`main` 段 guest exit 1、`-d cpu` dump 0 …
- `ISS-430`【P2】`m14-llvm-005` 后 `.set VD, L1-L0` 再 `set.zw rbX, wpN, VD` 由「静默 0」变为**报错**（`VD` 是 Absolut…
- `ISS-431`【P2】`run_asm_suite.py` 默认共享 work-dir（`harness/inst-asm`）在**两批 suite 并发**时会互相覆盖产物，产生**假红**（`m…
- `ISS-442`【P3】`inst_sweep`/`bit_sweep`/`ctrl_sweep`/`fp_sweep` 退役后，`sweep_expect.bin` 的 md5 `2d4d94651…
- `ISS-445`【P3】子代理异常取消（`Task cancelled`）：`m12-chipyard-017` 第 1 次运行时被取消，落盘状态 = 4 个脚本已在工作树落位（`tools/test…
- `ISS-446`【P3】picolibc 的 long-double 阻塞仍引用**已关闭**的 `ISS-193`：`ISS-193` 已于 M9 归档（`.tao/archive/M9/issue…
- `ISS-449`【P3】L1 门控自己在 `/tmp/opencode/<门控ID>/` 建空 scratch 目录却不清，命名又与任务 ID 同形：`check-code-range`(INFRA-…
- `ISS-456`【P2】证据脚本按**脚本自身路径**推仓库根，在任务 worktree 里会经 `.work` 软链解析到**主工作树**，从而把产物误写进 `master`：`m14-linux-…
- `ISS-458`【P3】证据脚本的「改前基线」若取 `git archive HEAD`（或任何指向**当前**提交的引用），**提交后重跑就变成自比假绿**：`m15-testcases-002` …
- `ISS-459`【P3】TLB 的**跨 hart 失效传播（shootdown）**在 v5 侧无任何规定：`cfx_ptw_tlb_control` 只描述「本 hart 的 TLB」操作（`DA…
- `ISS-461`【P3】`check-inst-macro-scope` 的 S8（「已整例宏化的 `.S` 正文不得再有裸 `__CHECK_*`」）以**行首 ` `** 为界，而 `llvm-m…
- `ISS-462`【P2】「同组件单写者」按**组件**划分不够，实际冲突发生在**共享构建树**：非 linux 组件任务（如 `m14-qemu-006` 跑 `k2_*` 探针）同样会写 运行期目…
- `ISS-463`【P3】在途任务的**共享源树**推进会让 master 上的 `check-patch-tree` 假红：任务分支的 engineer/reviewer 在 运行期目录<组件>` 里…
- `ISS-464`【P2】构建期撞工作盘 **ENOSPC**（`m14-qemu-004` 实测）：共享构建树 + 运行期证据目录长期累积（`.work` 95 G，其中 运行期目录 24 G），一次…
- `ISS-465`【P2】探针超时后遗留的 **`gem5.opt` 进程 + 巨大 `-D cpu` trace** 把工作盘写满（`m16-gem5-010` 实测，与 `ISS-464` 同夜的第…
- `ISS-466`【P3】子代理 session 因 provider 报 `Invalid API Key` 连续 3 次失败（`m16-gem5-009` 复核，session `ses_e19ef…
- `ISS-468`【P2】`llvm-objdump` 对 `rf` 寄存器组寄存器号断言崩溃（`DADAOInstPrinter::getRegisterName` 越界），`tests/inst/*…
- `ISS-478`【P3】子代理 provider 阻断：`m17-idl-001` 第 1 轮 reviewer session 返回 `Provider blocked the response`（…

## M18 异步 escape 出口帧：任务链（用户 2026-11-26 要求显式化）

**目标**：把 `m18-spec-007`（DADAO 0.8.0 / ADR-0061 R3）的出口帧落到所有实现，并按依赖串行推进，禁止“改完一个就跳”。

1. **`m18-llvm-002`（链①，先做）**：LLVM/opcodes 支持 `escape cfxHA`（`imms18` 恒 0）、反汇编/legality/生成物。**所有探针与内核汇编都依赖它**；LLVM 写者先等 `m20-llvm-003` 释放。
2. **`m18-testcases-004`（链②）**：独立派生向量（cg5/cg9 新布局、进入自动填、escape 五类判据、`rc11` 整字）；作为 QEMU/RTL/gem5/IDL/内核的共同 oracle。
3. **`m18-qemu-008`（链③，进行中）**：QEMU 实现新布局与 escape；探针用 ① 的语法、② 的向量。
4. **`m18-chipyard-002`（链④）** / **`m18-gem5-004`（链⑤）**：依赖 ①②，各自写者窗口串行；与 QEMU 同 ELF 签名对照。
5. **`m18-idl-003`（链⑥）**：IDL 执行器 + `IDL-ISA §4.6` + `SimRISC-11` 渲染块（补 `m18-spec-007` 的 F3）。
6. **`m18-linux-026`（链⑦）**：内核迁移（`cg5 rc8–rc11` 出口、`escape cfx_hart`、去 jmon、同步桩迁 `rc10`）；依赖 ③ 合入。
7. **`m18-linux-025`（链⑧）**：负载自旋修复（等 ⑦ 的新模型）。
8. **`m18-linux-006`（链⑨）**：LTP 两轮一致复跑（等 ⑦⑧）。
9. **`m18-qemu-007`（链⑩）**：移除 QEMU 的 `cfx_jmon`（等 ⑦）。

## M18 波2：每源 pending/mask/ack（`m18-spec-008`，ADR-0064）

**目标**：中断源的 pending/mask/ack 归源；显式 W1C ack；pending ack 才清；`cfx_hart` 捕获 `cg9→cg15`，monitor mask `cg8 rc1→cg15 rc3`；timer `cfx_hart cg16 rc0/rc1/rc16/17/18`；DMA `cfx_pmem cg16 rc16/17/18`、删 `IRQ_EN`；`cg15 rc4/rc5` 聚合；`escape rc11` 写 `cg15 rc3`；版本 `0.8.1-rc`。

**链**：`m18-spec-008`（已验证）→ `m18-qemu-009`（已验证）→ `m18-testcases-005`（向量）→ 各实现「先出口帧、后源接口」→ 重启 `m18-linux-026`（两项一起）→ 跨实现测试。

**用户 2026-11-26 排序要求**：escape 退出帧与中断源接口**相互协作**，**两个功能都更新完再统一测试**；实现按组件顺序：

- RTL：`m18-chipyard-002`（R3 出口帧）→ `m18-chipyard-003`（源接口）→ 测
- gem5：`m18-gem5-004`（R3 出口帧）→ `m18-gem5-005`（源接口）→ 测
- IDL：`m18-idl-003`（已合入）→ `m18-idl-004`（源接口）→ 测
- 内核：重启 `m18-linux-026` 时**同时**含 R3 出口帧与 `cg15/cg16` 源接口（原 `m18-linux-027` 并入 026；不再单独派）
- 统一测试（`m18-testcases-005` 复跑 + 025 自旋 + 006 LTP）放在以上实现齐备后；此前的跨实现红一律记 KNOWN-RED，不作为判据。

## chipyard 写者交接（用户 2026-11-26）

`m18-chipyard-003` 合入后，**chipyard 写者交还 M16**：`m16-chipyard-033`（RegRAS 环形缓冲，暂停条件=002/003 + spec-007）解除暂停；`m16-chipyard-030`（cfx15 flake）可继续；`028/029/031` 待验收由 M16 收口。M18 侧不再派 chipyard 任务，直到 M16 明确释放。

## N40. M16 三方差分收口移交 M20（用户 2026-11-27 裁定）

- **裁定**：M18/M20 对 spec 改动很多，**差分与收口统一归 M20**（`m20-integ-001`/`m20-integ-002`）；M16 不再单独跑 `check-arch-vast`、不出 `docs/TestReports/M16-三方差分.md`。
- **2026-11-27 全量三方现场结果**（`run_arch --level full --platforms qemu,gem5,chipyard --cache-model on`，27 个 case）：qemu / gem5 各 **20 PASS / 7 FAIL**；chipyard 腿在首个 case `arch-umon-011` 处因无 RTL 承载直接中止（该腿 0 结果）。
- **回归（此前有绿证据，非 M16 引入）**：
  - `arch-power-001`/`arch-power-002`：qemu 与 gem5 均挂死（`-d cpu` 135 MB 超限终止）。11-26 03:34 `m16-chipyard-031` 的运行期证据显示 qemu/gem5 均 PASS。
  - `arch-umon-012`/`arch-umon-013`（fence）：qemu 与 gem5 均挂死。11-23 `m16-testcases-012` 证据显示 qemu PASS。
  - 对照实验：换成 11-22 的旧 BootROM 仍挂死 ⇒ 与 11-26 的 BootROM/LLVM 重建无关，指向 `m18-qemu-008/009/010`（gem5 侧对应 `m18-gem5-004/005`）。
- **既有红（11-26 即红，非今日引入）**：`arch-cache-003`/`arch-cache-004` 在 qemu/gem5 上槽值不匹配——11-26 17:09 `m18-gem5-004` 复核在 0.8.0 历史树上同样红；`arch-cache-004` 的 RTL 侧无 cache-model 开关（`rtl-coverage.yaml` 已记 gap）。
- **无承载（设计缺口）**：`arch-umon-011..013` 的 gem5 侧驱动明确「shim 尚未承载本用例」；cfx0/2/3 没有 `check_umon_rtl.py`（`DIV-05` 的 close_when 未满足）。
- **收口工具链缺口（`run_arch`）**：① chipyard 腿不继承 conda 环境（缺 `libriscv.so` ⇒ 仿真器 rc=127、0 槽），需把 `LD_LIBRARY_PATH` 指向 chipyard 的 `riscv-tools/lib`；② 不识别 `expected-divergences.yaml`（`DIV-17` 的 2 槽会让 `arch-hart-001` 整案 FAIL，且失败时不落 signature）；③ 单个 case 缺承载会中止整条 chipyard 腿；④ `check_power_rtl.py` 不接受 `run_arch` 传入的 `--signature-out`/`--mode`（既有 M18 issue）。
- **交接**：以上红项与工具链缺口由 M20 会话登记进 `issues-m20.yaml`，在 `m20-integ-001/002` 收口；M16 侧任务已全部完成，`ISS-m16-012` 按「实现链已对齐、剩余差分归 M20」关闭。

## N41. 交接：给 M18 / M20 的具体待办（2026-11-27 会话关闭）

**背景**：M16 已归档（`.tao/archive/M16/`，95 册），差分收口按 N40 交给 M20；本会话不再有在跑任务。

### 给 M18

1. **chipyard 写者已完全交还**：M16 侧无任何在跑 chipyard/仿真任务，`m18-*` 可自由使用共享 chipyard 树。
2. **共享环境已重放对齐（本会话做过，勿重复）**：qemu 源树 `a8d0796` + 安装根 `e470dc56…`（含 `m18-qemu-008/009/010`）、gem5 源树 `7db7553` + `gem5.opt` `ebb19d0b…`、chipyard `7b1d785` + Vast `0ead2519…` / Tiny `71cbed98…`、LLVM 11-26 07:23。若再合入组件补丁，按 `lessons.md` 的「重放+重建+`install-host`」执行。
3. **musl 源树落后补丁集**：`.work/source/musl` 停在 11-24，`components/musl/patches/arch/dadao/bits/signal.h.patch` 已被 `m18-linux-010` 更新 ⇒ `check_patch_tree` 报 2 个 problem（`make check` 会红）。重放会让安装根 libc 变化，**必须在 LTP（`m18-linux-006`）等跑批的空窗做**，并与正在跑的任务串行。
4. **M18 台账有 1 处机械违规**：`milestones-m18.md` 的 `m18-linux-027` 行预估写「—」，且 `.tao/tasks/linux/m18-linux-027-内核源接口ack迁移.md` 无头部 `**状态**` ⇒ `check-milestones-fresh` 红。该任务已「并入 026」，建议把该行改为说明性文本（移出「待开始」表）并补任务书状态。
5. **疑似回归（需与 M20 协同 bisect）**：`arch-power-001/002`、`arch-umon-012/013` 在 qemu/gem5 上挂死，11-26/11-23 有绿证据；M16 探针未改，指向 `m18-qemu-008/009/010`（gem5 侧 `m18-gem5-004/005`）。`arch-umon-011` 的 qemu 槽 1 期望 `0xffff…` 实际 `0x0123…`，同批线索。

6. **worktree 清点**：`git worktree list` 仍见 4 个 `m18-*` 工作树（`m18-linux-024-2` 为 detached；`m18-linux-025`/`m18-testcases-001`/`m18-testcases-002` 分支已合入 master 但工作树有未提交改动）——请 M18 各自确认后提交或删除，本会话未动（避免误删在途改动）。
### 给 M20

1. **差分接手顺序**：`m20-integ-001`（三方 cfx/cg/rc 覆盖矩阵与口径）→ 先修下面 4 个 `run_arch` 缺口 → `m20-integ-002`（实测与缺口关闭）。现场数据与红项清单见 **N40**。
2. **先修 `run_arch` 4 个缺口**（否则现场红不可信）：
   - chipyard 腿不继承 conda 运行时库（缺 `libriscv.so` ⇒ rc=127 / 0 槽）⇒ 传 `LD_LIBRARY_PATH` 或让驱动自带环境；
   - 不识别 `tests/arch/expected-divergences.yaml`（`DIV-17` 的 2 槽会让 `arch-hart-001` 整案 FAIL，失败时还不落 signature）；
   - 单 case 缺承载（如 `arch-umon-011` 无 `check_umon_rtl.py`）会**中止整条 chipyard 腿**，应改为该 case 记 GAP/SKIP 并继续；
   - `check_power_rtl.py` 不接受 `run_arch` 的 `--signature-out`/`--mode`（既有 M18 issue，power 三方必须先修）。
3. **登记位置**：红项要进 `issues-m20.yaml`（该文件 M20 独占写，本会话未代写）；M16 的未解决 backlog 只有 `ISS-535`（已进 `issues-left.yaml`）。
4. **既有红不是回归**：`arch-cache-003/004` 在 11-26 的 0.8.0 历史树上同样红（`m18-gem5-004` 复核证据），别按新回归处理；`arch-cache-004` 的 RTL 侧是登记 gap（无 cache-model 开关）。
5. **可用基线**：qemu/gem5 各 20 PASS / 7 FAIL（27 case，`--cache-model on`）；`arch-hart-001` 三平台已同为 124 槽（RTL 仅 `DIV-17` 2 槽差异），说明 spec-007 对齐已进二进制，差的是 runner 识别与上述红项。

## N41. M18 会话交接（2026-11-27）

**队列与状态**

- `m18-linux-025`（`ISS-m18-001` 自旋根因）：实现完成、`待验收`；根因 = umon 返回路径 `DADAO_GPR_RESTORE_AT` 先恢复用户 SP、`escape cfx_umon` 尚未执行，supv 异步门仍开 ⇒ 异步 handler 在用户栈上跑，栈页未驻留时同一 `st.o` 无限重入。修法 = 两条返回路径 restore 前 `DADAO_CLOSE_SUPV_ASYNC`（置 `cfx_smon cg15 rc3` 源位 15/32）。修前 30/200（15%）、修后 0/1000 + 2048 启 0。
- `m18-linux-006`（LTP 两轮）：`待返工`，**等 025 合入后**在新内核 + 新 QEMU 上复跑；LTP 入口本身在 025 期间仍不可用。
- **M18 范围（用户 2026-11-27 明确）**：只关心「Linux 在 QEMU 上跑 busybox / LTP / kselftest」；跨实现（QEMU/gem5/RTL/IDL）对拍**不属 M18**，归 M20 `m20-integ-001/002`。M18 收口 = busybox（K6）+ kselftest + LTP 子集两轮一致、非 PASS 全部有分诊。
- `m20-spec-001` 已承接原 `m18-spec-001`（cg4 `scratch_regs_num` 缺省 2）；M18 侧不再派。
- chipyard 写者已交还 M16（002/003 合入后），M18 不再派 chipyard，直到 M16 明确释放。

**基线红（`make check` rc=2 时的既定红集，判据=与基线逐行相同）**

- `check-arch-self-test`：任务 worktree 缺 Vast step5 BootROM 产物（主工作树有）⇒ 产物缺口，非代码红。
- `check-interface`：LLVM lit 294≠309，既有偏差。
- `check-milestones-fresh`：M16 台账 10 处（9 条 A1 状态不一致 + `m16-chipyard-033` worktree 与「待开始」不符），**M16 会话负责**。
- `check-temp-dirs`：其它会话陈旧临时目录 + 磁盘占用。
- `check-patch-tree`：全仓 rc=1 来自 qemu/gem5/musl 既有漂移（分段各自 0 problem）；判据用分段。
- `check-musl-freshness`：只建静态 musl 时红，`make build-musl-shared` 后回绿。
- `check-isa-coverage`：缺 `llvm-mc`（环境级）；`ISS-m18-003`（`check_power_rtl` 不收 `--signature-out/--mode`）另记。

**低频残余（未闭合，勿当回归）**

- `ISS-m18-004`：2000 启中 1 次极早停摆（`workingset` 后、`M45 begin` 前），2048 启未复现。
- `ISS-m18-005`：suite 随机 case `HOST_TIMEOUT`（`futex-wait-timeout`/`mm-pfnmap`），独立 suite 两轮 + 64 次启动 0 复现。
- `ISS-m18-006`：`handle_softirqs` `die=0xe4`（`pf-va=0x10`）低频签名（025 修后 1/200），与 `ISS-m18-001` 的静默自旋根因不同，独立计数。
- 判据纪律：命中即计数重跑（每轮 ≤3 次），**不得**放宽 `window_reds == 0`、不得把 `HOST_TIMEOUT` 吞掉。

**易失与残留**

- 026/qemu-007 的 worktree 已删，其运行期证据随之消失；关键数字已落各自任务书「完成区/审阅记录」。后续任务证据要落非易失位置。
- 仍有 3 个旧 worktree 带未跟踪改动（`m18-linux-024-2`、`m18-testcases-001/002`，后两者已作废），`git worktree remove` 需 `--force`，未处理、待用户确认。
- 会话教训：① 并发写者误判（同一 worktree 曾同时存在两个 engineer，接管方及时停手未写）；② `run.sh`「恒真断言」在 024/026 两次出现（`soak` 的 `ok=True`），修复后必须有「注入→FAIL→还原→回绿」。

## N42. M20 指令批授权（2026-11-27 16:40）

- **用户裁定**：`m20-testcases-007` 调研完成后，指令类移植**立即开始**，不必等 `m20-testcases-006`；不设条数上限，按缺口逐条立项。
- **批次清单**：`m20-testcases-008`（A6 位操作）→ `009`（A8 单精浮点）→ `010`（A9 双精浮点）→ `011`（A4 乘除余 + A5 存取）→ `012`（A1–A3 + A10）；全链逐件串行。
- **共享写者**：`tests/inst/**`、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tests/data/inst-signature/*` 与 `m20-testcases-006`、`m20-infra-002` 互斥，不得并行；本链内部亦串行。
- **验收**：每件 `check-inst-asm` + `check-idl`（四方签名槽）+ `inst-signature-data` 同步 + `check-tests-index`/`check-case-ledger`/`check-index-blobs`/`check-inst-macro-scope`/`check-knowledge-refs`；证据用「注入→FAIL→cp+md5 还原→回绿」。
- **停止点**：不 push；不改 `spec/`/`.tao/contracts/`/`opcodes.yaml`/引擎。系统批（S1–S3）仍等 cfx W1–W3 + `m20-integ-002`，不在本批次。

## 会话交接（2026-11-27，M17 收口后）

- **M17 已归档**：`.tao/archive/M17/`（46 册，达成 2026-11-27）；活册只剩 M18/M19/M20。M17 任务面 0 遗留、`issues-m17` 0 open。
- **跨平台 RAS 统一约定（用户 2026-11-27「都采用环形」）**：物理槽 `0` = `ra0` 元数据；`phys(i) = 1 + ((base + i) % 63)`（`i ∈ 1..63`）；`base` 6 位、0..62、复位 0、不可架构访问；`call` ⇒ `+1`、`ret` ⇒ `−1`（模 63）；所有架构访问经映射。四平台已实现（QEMU `ra_phys`、gem5 `ras::phys`、IDL `Machine._ra_phys`、RTL `WumingRegFile`）——**任何平台改布局必须四处同步**，否则 trace 的「全 64 槽按值比」会假红。
- **trace 计数口径**：确定性计数（`cg4 rc2/rc3/rc5` 等）**严格相等**（入口态 seed `cg4`/`cg15`）；只有历史依赖计数才允许阈值/增量（当前无实例，不预造机制）。见 `idl/docs/trace-format.md`。
- **`check-idl-full` 已支持 `expected-divergences` 逐槽例外**（`m17-idl-026`，见 `idl/docs/four-way.md §7`）；Tiny 缺 `cg4`/`cg15 rc3` 按 `DIV-18` `slots` 声明（真触发 CFXREG、不写常量、不跳过）。M20 不需重复实现该能力。
- **已知基线红（非 M17，均已登记）**：`check-patch-tree` 52 problem（linux 51/musl 1，`ISS-left-004`）；L3 `stack-protector*.ll` 未归类（`ISS-left-005`）；`check-milestones-fresh` 的 `m18-linux-027` 未入表（M18 会话）；`check-manifests-guard` 的 M16 归档遗留 2 条登记。
- **证据位置**：本轮门控/注入日志在运行期证据目录（不入库）；结论已写进归档 `README.md §3`、`m17-retrospective.md` 与各任务书完成区/审阅记录。
