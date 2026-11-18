# 讨论项

> **组织方式（用户 2026-11-18 重排）**：`未决项` → `M14` → `M15` → `M16` → `Milestone 候选`。**所有未决/待裁定项统一放在最前**（逐个二级标题），里程碑各节只放**已定口径与现状**；Milestone 候选列**尚未立册**的后续方向。
>
> **维护规则（2026-11-13）**：本文件**只记** ① 当前未决 / 待裁定；② **仍然生效**的口径。裁定一旦落成 `spec/`、ADR、任务书或 `AGENTS.md`，**从本文件删除**（git 历史可回溯）；过程快照、已完成任务的方案叙述、过期队列状态一律不留。任务流水看 `milestones-m14/15/16.md`，M13 及以前见 `.tao/archive/`。

# 未决项

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

## N2. `escape` 合法偏移 + SBZ 的 ADR（`SPEC-180t`）

- 结论：escape 合法偏移集 `{0,+4}` + `imms18[17:1]` SBZ ⇒ ILLI；按 `docs/Process-03` 命中外部契约变更 / 多方案 / 结论固化。
- 下一步：**逐条确认 decision 后**再立 ADR；未确认前只保留为遗留（不得写为 `Accepted`）。

## N3. `ADR-0046` 仍 `Proposed`

- 等 Linux 实测后再收口；`ADR-0043`/`0045` 已 `Accepted` 且不再改其 decision。

## N4. `ADR-0057`（gem5 数据侧两阶段）的 D5 / D6 / D7

- 状态 `Candidate`；D1–D4 已定，**D5 取指/cache 未定**、D6/D7 依赖 D5。
- **D5 的前置（用户 2026-11-16 指示）**：先调整 gem5 **配置信息**——把机型/Profile 与内存层次配置分开（Tiny 与 Vast 分开），再谈 cache 参数。
- 已核事实：`configs/dadao/` 只有 `se.py`/`se_timing.py`/`fs.py`，都只用 `SimpleMemory`（`se_timing` 另有 `NoncoherentXBar`）；chipyard 侧只有 `WumingTinyConfig`（SRAM 主存、`icache/dcache = None`），**无 Vast 配置**。
- 用户已指出：`Kaiwu-Tiny` 跑在 SRAM 上**不需要** cache；`Kaiwu-Vast` 需要 cache 但 RTL 尚未增加。

## N5. M16 周期模型文档 6 处口径待确认（2026-11-14）

`m16-gem5-002` 现场解析 `docs/core-wuming-cycle-model.md` 时遇 6 处文档本身不闭合（已按类级口径自决，**需用户口头确认一次**）：

1. **16 条 FT 侧 FP 族**（`ftadd/ftsub/ftmul/ftfma/ftmax/ftmin/ftqcmp/ftsclb/ftscmp/ftrnd`、`fosub/fosclb/foscmp/fosgnj/fosgnn/fornd`）§3 无专行，只有 §2 B4「1–2」类级口径；建议把文档词法改 `ftsgn*`→`f*sgn*`、行 70 的 `fo*`→`f*` 即可逐条定死。
2. `ext` = 2 拍属**推断**（无实测），已标来源与「待复核」。
3. §3 行 75/76/77 的「全套」把 A 档写 `1`，与 §2 的 A 两档、§5 `shl.o`=2 冲突 ⇒ 表按 §2 两档解析（`shl.t`=2、`rem.st`=17）；建议文档改列消歧。
4. `clmul.o` 唯一 override（行 61 的 B1/3 是估计，行 87 + 行 117 实测 A/2）⇒ 记入表 `overrides`。
5. `jump/call/ret` 的 8/26/15 是**预取失效期上界**（文档 §5 称「`015` 收口时复测」，但 `m12-chipyard-015` 已完成、未回填）⇒ 表暂按现值；回填后**必须重跑生成器**（`check-wuming-cycles` 绑文档 sha256，会立刻红——设计意图）。
6. `B2`（1 可配）按「可配」处理，`value` 留空。

## N6. M16 `st`/`stm` 的 +1 拍 → **已裁定（用户 2026-11-18）：表格分行给值，不加列**

- **裁定原话**：「表格把 ld/st/ldm/stm 分为不同的行即可，不要加列。不要把简单的事情做复杂。」
- 事实基础：`ld.*` 全宽度 9、`st.*` 全宽度 10（宽度无关）；`stm` N=1 与 N=8 都只差 1 ⇒ **+1 是每指令固定偏置、与 N 无关**。
- 实施（待立任务回填）：
  - `ld.*` 行：`cycles: '9'`（单值，去掉 `9–10` 区间）；
  - `st.*` 行：`cycles: '10'`；
  - `ldm.*` 行：保持 `per_element: 1` / `per_beat: 8`（N=8 → 72）；
  - `stm.*` 行：同系数 + 启用表内**已有**字段 `n_base: 1`（常数项，N=8 → 73、N=1 → 10）；
  - gem5：C 分支直接取值（不再用 D 公式在 N=1 求值）、D 分支加 `n_base` 常数项；
  - C/D 探针容差 ±1 → **0**。

## N7. cfx 待实现范围

- 已实现：umon / jmon / smon / hmon / ptw / pmem / time / hart / power。
- 后置：cache / llc / uart、PMEM 区域分配、IPI、多 hart。
- 下一步：按 Linux 需求拆任务（M14 启动时）。

## N8. U-mode / cg5 / 异步帧

- 结论（待讨论）：U-mode 的 cfx 目标**不设 ISA 限制**，由 OS 策略决定；cg5 单帧、同步/异步分离、递归/重入**尚未定**。
- 下一步：等 cg7 与 escape 收口后再讨论。

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

## N14. `.tao/knowledge/refs/` 清空方式

- 用户 2026-11-15 已定「下一步也要清空」；执行时间点：M13 收口前后 或 M15（M13 已归档）。
- 影响：refs 内现有报告**不再作为结论载体**；结论改落根 `README.md`、`docs/DDLN/`、`.tao/archive/M*/README.md` 与台账。
- 清空前须确认：① 还有谁在引用（任务书/台账/门控）⇒ 先改成「结论已迁至 X」；② **删除 or 归档到 `.tao/archive/M*/refs/`**；③ 是否同步改 `docs/Process-0x` 关于 refs 落点的规定。
- **在此之前新任务不得再往 `refs/` 写文件**。

## N15. `tests/inst.yaml` 的 `platforms:` 字段去留

- `m15-infra-001` 已把机型/引擎/套件的真源迁到 `contracts/machine.yaml` + `exec-envs.yaml` + `tests-matrix.yaml`，但 `tests/inst.yaml` 里 **273 处 `platforms:`** 仍在，与 `exec-envs.yaml` 的 `engines` 语义重叠。
- 待裁定：① 保留（改名 `engine`/`mode`）还是废弃、用例适用范围统一用 per-case `profiles:`；② `user`（qemu-user / gem5-se）在执行环境契约里已归独立 env，是否还需 per-case 标注。

## N16. M15 语法 v0 的 4 条待定

- 是否直接采用 UDB `idlc` 作为抽取器（版本/许可证/可离线），还是只借语法、自写抽取器。
- 是否在 M15 就冻结 `.idl` 语法版本（`contracts/isa/idl-v0.md`）并进 L1 门控。
- 渲染形态（spec 里显示格式化伪代码而非原始 IDL）是否需要单独任务。
- 语料次序：5 条样板 → 6 族各一条 → 全量，是否按此三阶段立册。

## N17. `m15-spec-001` 待返工推进方式

- 状态待返工（WIP 已保留）；用户要求「先摊开文件内容 + 逐条语句分析」再继续。
- 待定：由谁摊开（子代理 vs 主会话直接给全文）、按什么粒度逐条过（语法/语义/扩展点）。

## N18. `tests/inst` 头注释模板化（未授权）

- 272 个文件的头注释重复约 3,780 行（占 13%）；收益最大但会引入生成器。
- 需用户先定「只统一字段」还是「加自动生成」。`m15-testcases-001`（宏去重下沉）已授权在执行。

---

# M14：Linux bring-up

> 2026-11-01 用户裁定：Linux 开发延至 M12 或后续；**现定为 M14**（三线分开进行）。

## 收口范围：到 K6

- `ADR-0052` 已于 2026-11-17 就地修订：M14 出口扩展到 **K6**（busybox 用户态）。
- UART / cache / LLC / gem5 侧仍**不阻塞**收口。

## K4 / K5 / K6 分界（用户 2026-11-17 选 A）

- **K4** = 内核侧进程/线程原语：`copy_process` / `kernel_thread` / `kthreadd` / 调度 / COW / 用户栈增长 + 最小 U-mode 闭环。
- **K5** = 用户态：用户 `clone`（`CLONE_VM`/`CLONE_SETTLS`/`CLONE_THREAD`）、TLS（`rb3 = rbtp`）用户面、`futex`、pthread 类测试；另含 `clocksource`(cfx_time) + `clockevent`(cfx_hart) 升级到通用框架（原 `m14-linux-021`）。
- **K6** = 用户态应用：静态 busybox、最小 applet（`sh ls cat echo mkdir rm cp mv grep ps`）、不做 `/proc`、不做作业控制；出口 = `sh` 启动后 5 条命令正确。

## 阶段与任务量（K0 后校准）

- K0 基线与契约：5–7 个任务（补丁组件、工具链缺口、启动 ABI、syscall/errno/TLS、initramfs/semihosting、门控）。
- K1 启动与控制台：4–6 个；K2 异常与时间：5–7 个；K3 内存与 TLB：6–8 个；K4 进程与上下文：5–7 个；K5 用户态闭环：5–7 个；K6 用户态应用：4–6 个。
- 合计约 34–48 个。

## 已定口径（仍生效）

- **TLB 失效语义 = 同步**（`m14-spec-006`）：`cfx_ptw_tlb_control` 写指令**返回即生效**；`clean`/`flush` 需回写 A/D，**回写失败在该写指令上报 `CFXMEM`**（`flush` 失败不删条目、`clean` 失败不清挂起位），不得出现「部分完成」。
- **单 hart**：`tlb_control` per-hart；跨 hart 一致性**不在 M14/K3 范围**（`ISS-459`，同 `ISS-440` 类）。
- **M14 只做 QEMU**；chipyard/gem5 不要求 TLB；但 `tests/arch` 必须新增 TLB 探针（Vast + PTW）。
- **内存异常判定顺序**（用户 2026-11-16）：**先看 `VA[47:42]`**——≠0 ⇒ cfx 核内空间（不走 PTW/TLB）；=0 ⇒ 再看 `ptw_enable`：`0` ⇒ `CFXMEM`（不查 TLB）；`1` ⇒ 进 PTW/TLB（未映射 ⇒ `CFXMEM`、权限 ⇒ `CFXPERM`）。
- **规范不引入「缺页/COW」**：`DADAO-12 §2.2.6` 的规范句是「页表未映射（含超页/小页缺失）与 A/D 回写失败 ⇒ `CFXMEM`；HSJU 或 R/W/X 不符 ⇒ `CFXPERM`」；内核把它解释成缺页/COW/真越权属**内核判定**。
- **K3 内存范围 = 按需分页 + 共享零页**（「简单验证即可」）；COW 与用户栈增长全归 K4。
- **semihosting 指针 = PA**（`spec/Kaiwu §5.2` + `contract-semihosting §2`）；QEMU 侧缺口 `ISS-450`。
- **中断 mask 口径**（2026-11-16）：异步源轴查**当前运行模式 monitor** 的行（`DADAO-12 §5.2（三）步骤 3`），与 `inner_cfx_code` 无关。
- **阶段推进即退役过时判据**：`docs/Process-07 §4a`。
- **`cause_info` 编码**（`ADR-0056` Accepted）：`cause_id[15:0]` one-hot 不变；`[31:16]` 保留；wyde2 `[47:32]` = `CFXPERM` 子原因、wyde3 `[63:48]` = `CFXMEM` 子原因（`[56] ADWBFAIL`/`[57] NONPTW`）；另一 wyde 必须全 0；`cause_info` 恒为地址。

---

# M15：ISA 语义结构化

> **定位（用户 2026-11-12/13）**：只做「**结构化**」——把 `spec/` 升级为「每条指令一段**可解析的 operation**」，**不执行**（执行归 Milestone 候选：IDL 可执行参考模型）。M13 不加 IDL 任务；M14 已分配给内核。

## 目标与出口

- `spec/` 的每条指令记录带一段 operation 块（语法可解析、语义单元唯一），与编码字段、合法性规则、异常语义一一对应。
- 出口：264 条记录 **100%** 有 operation 块且 id 一对一；抽取结果与仓库内 `.idl` **逐字节一致**；6 族各一条完整族通过；`check-spec-*` 全绿。

## 候选任务

- `m15-spec-001`（**已立册，待返工**）：语法 v0（`contracts/isa/idl-v0.md`）+ 5 条样板（add.so / ld.o / br.eq / lr.o.nn / trap）+ `extract.py` 原型；3–5 天。
- `m15-spec-002`（未立）：6 族形状定稿（alu/mem/ctrl/atomic/system/fp 各一条完整族）+ 共享函数层；5–8 天。
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

## 设计取向（用户 2026-11-13 裁定）

- **以 `riscv-unified-db` 的 IDL 为准**（`doc/idl.adoc`：`Bits<N>` / `X(rs1)` / `jump()` / `raise(ExceptionCode::…)` / `function` / 配置常量），**优先复用其语法与工具**（`idlc`、`yamlidl`）；只在不合适处扩展。
- 扩展方式优先用 IDL 的 **`function` 定义**（四 bank 读写、48 位地址、大端访存、cfx 分发）；确需语法扩展时单列「扩展提案」逐条裁定。

## 对标维度（讨论提纲）

1. **载体**：operation 写在 spec 正文每条指令旁，还是独立 `.idl` 文件（spec 只保留渲染视图）？
2. **语法**：表达式/语句形态（赋值、条件、位切片、内存访问、异常触发）；是否允许共享函数与参数化族。
3. **粒度**：一条指令一段，还是「族 + 参数」薄 block（264 → ~90 个语义单元）。
4. **单一真源**：spec 正文 ↔ `.idl` ↔ 契约投影 ↔ 测试期望，谁是源、谁是派生、如何机械校验（逐字节 / AST / 语义等价）。
5. **可执行接口**：为可执行参考模型预留什么（签名、状态结构、内存与异常模型），但 M15 **不实现**执行。
6. **不自造第二套规范**：operation 不得成为与正文并列的「第二真源」；冲突时抽取器 fail-closed。

---

# M16：gem5 时序模型对齐 chipyard-wuming

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

## 已裁定：C 类（`ld/st`）拍数口径（用户 2026-11-17 选 ①）

- 承认 chipyard 实测 `ld.*` = **9**、`st.*` = **10** 为真值；`docs/core-wuming-cycle-model.md` 的 C 行「4–7」记为**外推失效**，由 `m16-chipyard-001` 回填并把来源改为「实测」。
- 依据：`m16-gem5-006` 用文档 **D 类**（块传送）模型在 **N=1** 处求值 ⇒ 得 9/10，13/13 落在 ≤1 拍容差内；四源一致且 D 模型在 N=1 的自洽性有算术依据。

## 已定：二期把执行核改成两阶段（用户 2026-11-16 选 ②）

- 给 DADAO 补 `StaticInst::initiateAcc`/`completeAcc` 并让 bundle 可续跑；目标 CPU = `TimingSimpleCPU`（`AtomicSimpleCPU` 不走两阶段）。
- **随之必须同笔做**：① 周期表里 `ld/st` 的 9/10 拍（`ld.o` 7–16、`st.o` 10–21，含背压）**清零**，否则双重计费；② 一个 bundle 可能含多条访存 ⇒ 需能「停在中间」（记录子操作序号与未完成请求数），`ldm`/`stm` 的 N 个元素如何发请求（串行 or 并发）在 ADR 里定；③ 取指侧 8 拍/指令（无 icache）是既有事实，两阶段只解决数据侧。
- 落地载体：`ADR-0057`（`Candidate`，D5–D7 见 N4）。

## 参考材料分工（`.cache/refs/`，只读参考、不复制实现）

- **`riscv-unified-db`**（`manifests/references.lock.toml` 已登记）：机器可读 ISA 数据的形态。
- **`DADAO-0628`**：Python 解释器与 Sail 两套独立实现的经验。
- **`DADAO-v5-pr4`**：RTL 侧微操作分层与「生成器 vs 独立校验器」对偶。
- 落盘方式：这两份参考材料**不用 git 镜像**，改为 **tarball 快照**（`manifests/reference-snapshots.toml` 记录 URL/commit/sha256）。

---

# Milestone 候选

> 尚未立册的后续方向；立项时把「目标 / 出口判据 / 首件任务」补进对应小节。

## IDL 可执行参考模型

把 M15 的 `.idl` 跑起来，作**第四方差分参照**（不追求全量第四实现）。

- **候选任务**：`m17-idl-001` lexer/parser/AST/类型检查（12–16 天）；`m17-idl-002` 解释器：加载 ELF、四 bank 状态、48 位地址/大端、异常与 monitor、trace（10–14 天）；`m17-idl-003` 差分接入：273（整数）+ 167（访存）+ 67（控制流）逐例与 QEMU 一致、纳入 L2（8–10 天）；`m17-idl-004` 向量「算期望」派生（输入仍人挑，期望由 IDL 算，**不做输入自动生成**，8–10 天）；`m17-idl-005` FP 特殊值语义（NaN/Inf/次正规/五类标志，15–20 天）。
- **出口**：507 例与 QEMU 逐例一致；每个 operation 分支至少被一个向量走到；`make check-idl` 进 L2；分歧归因落 spec 裁定（**不是「IDL 一定对」**）。
- **与 M15 的边界**：M15 只结构化、不执行；可执行在此。

## 流水线处理器核（gem5-minor / chipyard-wuqing）

- **当前状态**：gem5 侧只用 `TimingSimpleCPU`（加每指令延迟的钩子），Minor 尚未接入；chipyard 侧**只有 `WumingTinyConfig`**（SRAM + cfx 测试机、无 MMU/TLB），`wuqing` 的 RTL 尚未出现。
- **开启条件**：`wuqing` RTL 可用（用户 2026-11-13：等其 RTL 出现后再开）。
- **待定**：Minor 的 `initiateAcc`/`completeAcc` 两阶段是 `ADR-0057` 在 `TimingSimpleCPU` 上先验证；迁到 Minor 时周期表哪些行仍然生效。

## 乱序处理器核（gem5-o3 / chipyard-wuxing）

- **当前状态**：同上，O3 与 `wuxing` 均未开始；gem5 O3 的访存两阶段与 `ADR-0057` 的 bundle 续跑模型需要重新评估。
- **开启条件**：`wuxing` RTL 可用。
- **待定**：乱序下每指令延迟钩子是否还成立（钩子假设顺序退休），或需改为对拍式建模。

## Vivado

- **当前状态**：尚无内容。
- **立项时需补**：目标板卡/器件、综合与实现流程、与 chipyard 交付物的关系（谁产出 bitstream/报告）、门控判据（时序收敛、资源占用）与许可证/环境要求。

## LFS

- **当前状态**：尚无内容。
- **立项时需补**：LFS 的定位（构建缓存 / 大文件载体）、与 `.cache/` + `manifests/` 锁的关系、容量与清理策略。

## 向量支持

- **当前状态**：尚无内容（spec 与 encode 层尚未定义向量扩展）。
- **立项时需补**：先由 spec 定义（长度/掩码/寄存器组语义），再谈编码、`.idl` operation、测试向量与差分（QEMU/gem5/chipyard 三方能力矩阵）。
