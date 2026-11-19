# 讨论项

> **组织方式（用户 2026-11-18 重排；2026-11-19 补 H1）**：`未决项` → `M14` → `M15` → `M16` → **`后续里程碑备选（尚未立册）`**（四个都是**一级标题**）。**所有未决/待裁定项统一放在最前**（逐个二级标题），里程碑各节只放**已定口径与现状**；Milestone 候选列**尚未立册**的后续方向。
>
> **维护规则（2026-11-13，用户 2026-11-19 重申）**：本文件**只记未裁决项**。裁定一旦落成 `spec/`、ADR、任务书、`AGENTS.md` 或 `docs/DDLN/`，**从本文件删除**（git 历史可回溯）——该迁的迁、无保留价值的直接删；过程快照、已完成任务的方案叙述、过期队列状态一律不留。任务流水看 `milestones-m14/15/16.md`，M13 及以前见 `.tao/archive/`。

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

## N19. D 类 `beats` 必须按起始相位算（`m16-chipyard-004` 实测发现）

- 现行 `wuming_latency.hh` 的块传送 beats 按「元素不跨 8 B 拍」推导；实测要求 **`beats = ⌈(addr%8 + N·w)/8⌉`**——非 8 B 相位起址时每组恰多 8 拍（`ldm.ub` N=8 相位 2 ⇒ 24 拍而非 16）。
- 影响：非对齐起址的 `ldm`/`stm` 模型会低估；`ldm.ub` N=8 = 16 是 8 B 相位上的值，不能外推到其它相位。
- 待定：是否改模型（改 `wuming_latency.hh` 的 beats 公式 + 表 + 探针），以及是否需要把「相位」作为表格的输入维度（当前表只有 `per_element`/`per_beat`）。
- 另记两个 N=1 地址特例（SRAM 尾拍 +11、`.text` 内 off-queue 取指 −1），已是实测例外，不解释 +1。

## N21. M15 收口时补 `idl/*.idl` 的 sha256 锁

- 用户 2026-11-18 裁定：`idl/` 目录的 `.manifests.toml` **先只列文件名**（双向集合断言），`sha256` **等 M15 完成后统一补**。
- 原因：M15 期间 `.idl` 会大量增改，逐次重算锁的成本高于收益。
- 收口检查项：M15 收尾时把 `idl/*.idl` 逐文件 sha256 写入 `idl/.manifests.toml`，并确认 `check-manifests-guard` 会校验它（schema 已支持条目级 `sha256`）。

## N22. `m14-linux-017` 的 S5（U-mode 帧 A/B 往返）→ **已裁定 A（用户 2026-11-19）**〔017 收尾时移入任务书并删除本节〕

- **核查结论（第 23 轮）**：S5 要求 A/B **交替** ⇒ handler 必须 `schedule()` 阻塞；而 umon 入口跑在**静态入口栈**（`trap.S` 把 `rb1` 设为 `dadao_umon_stack_top`，`current = SP & ~(THREAD_SIZE-1)`）⇒ 两个任务的内核续跑点会叠在同一张 64 KiB 栈上，**与帧放在哪里无关**。所以「只把帧按任务化」不足以实现 S5（F13 回退正是此机制）。
- **入口不能直接换到任务内核栈**：入口时 SP 还是用户栈，`current` 尚不可知（F28 正是为此在静态栈上刷新 `thread_info.task`）。
- **三个选项**：
  - **(A)** 新增**全局 `dadao_current_task`**（`__switch_to`/`dadao_enter_user` 写入），umon 入口读它取 `task_stack_page(task)+THREAD_SIZE` 作新 SP。单 hart、无递归 ⇒ 全局单元安全；`thread_info` 天然在各任务内核栈底。改动面：`entry.S`/`process.c`/`thread_info.h`（核心结构改动）。
  - **(B)** S5 降级为「帧按任务化 + 不阻塞的交替」（放宽判据，用帧切换模拟交替）。
  - **(C)** S5 推迟到 K5，与嵌套/抢占一起做。
- **架构侧建议 (A)**：S5 是 K4 上下文切换的核心能力，用帧切换模拟等于不测真正的交替；`current_task` 是标准做法（Linux 的 `current` 同理），单 hart 下安全。代价是核心结构改动、需扩权。
- **裁定（用户 2026-11-19，原话「A」）**：按 (A) 实现「每任务内核栈」；spec 不改。
- **实现细节（用户 2026-11-19 二次裁定，取代「全局 `dadao_current_task`」）**：用 **`cg6` 暂存寄存器 + `rd2`（reserved）** 做过渡——
  ```
  rb2rd  {rd2:rd2},{rb1:rb1},1       # rd2 ← 用户 sp
  cfx2rd cfx_umon,cg6,rc1,rd3        # rd3 ← 任务内核栈顶（__switch_to 预写）
  rd2rb  {rb1:rb1},{rd3:rd3},1       # rb1 ← 任务栈顶
  st.o   rd2,[rb1,FRAME_SP]          # 用户 sp → 新栈的帧
  ```
  （`rd2`/`rd3` 都是 reserved、编译器不分配，故全程可安全做过渡；`cg6` 只占 `rc1` 一个槽。）
  `__switch_to` 只加一行：把 `task_stack_page(next)+THREAD_SIZE` 写进 `cfx_umon cg6 rc1`。**不需要全局变量、不改 `thread_info.h`**（入口切到任务栈后 `current = SP & ~(THREAD_SIZE-1)` 自然成立）；静态栈保留为 boot 早期兜底（`cg6 rc1 == 0` 时用）。依据：`rb2rd`/`rd2rb` 见 `SimRISC-02`；`rd2–rd3` 是 reserved（编译器不分配）；`cg6` 见 `DADAO-12 §3.7`（内核专用）。**用户补充质疑已澄清**：共用的是内核态静态栈（非用户栈）；spec 未规定 `trap` 自动切栈（`§5.1/§5.2` 只定向量与 `inner_cfx_code`）；「每任务内核栈」由软件决定，故走 A 而非改 spec。

## N25. 进程页表必须复制「2 TiB 以上」的顶层项（用户 2026-11-19 裁定，`m14-linux-017` F56）〔017 收尾时移入任务书并删除本节〕

- **用户原话**：「2TiB以上是smon空间，所以，每个进程新建L1页表时，应该复制2TiB以上的完整的页表项；据我所知，其它isa应该都是这么做的」。
- **spec 依据**：`spec/Kaiwu-测试机运行环境.md` §内存窗口 —— Vast 窗口 `VA [0, 4 TiB)`；用户空间 `[0, 2 TiB)`、内核 VA 窗口 `[2 TiB, 3 TiB)`、`[3 TiB, 4 TiB)` 不定义；窗口内 `VA = PA + 2 TiB`。本端口两级页表：`L1 = VA[41:29]`（8192 项 × 512 MiB = 4 TiB）、`L2 = VA[28:16]`、页内 `[15:0]`；`USER_PTRS_PER_PGD = TASK_SIZE / PGDIR_SIZE`。
- **口径**：`pgd_alloc()` 之后把 `swapper_pg_dir` 中**下标 ≥ `USER_PTRS_PER_PGD`** 的顶层项整段复制进新表（smon/内核半区共享）；`pgd_free` 不得释放这些共享表。**禁止**用「探针窗口」之类旁路绕过切 mm（第 29 轮的 `pf_window` 路线作废）。
- **推论**：既然每个进程的 L1 都带内核半区，切换 mm 就是安全的 ⇒ S5 用「每任务真 mm + 正常 `switch_mm`」即可；`vm_mm == NULL` 的窗口空指针（F57/F58）不再是必须打补丁的路径。

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

## N15. `tests/inst.yaml` 的 `platforms:` 字段去留

- `m15-infra-001` 已把机型/引擎/套件的真源迁到 `contracts/machine.yaml` + `exec-envs.yaml` + `tests-matrix.yaml`，但 `tests/inst.yaml` 里 **273 处 `platforms:`** 仍在，与 `exec-envs.yaml` 的 `engines` 语义重叠。
- 待裁定：① 保留（改名 `engine`/`mode`）还是废弃、用例适用范围统一用 per-case `profiles:`；② `user`（qemu-user / gem5-se）在执行环境契约里已归独立 env，是否还需 per-case 标注。

## N16. M15 语法 v0 的 4 条待定

- 是否直接采用 UDB `idlc` 作为抽取器（版本/许可证/可离线），还是只借语法、自写抽取器。
- 是否在 M15 就冻结 `.idl` 语法版本（`idl/README.md`）并进 L1 门控。
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

## 阶段与任务量（K0 后校准）

- K0 基线与契约：5–7 个任务（补丁组件、工具链缺口、启动 ABI、syscall/errno/TLS、initramfs/semihosting、门控）。
- K1 启动与控制台：4–6 个；K2 异常与时间：5–7 个；K3 内存与 TLB：6–8 个；K4 进程与上下文：5–7 个；K5 用户态闭环：5–7 个；K6 用户态应用：4–6 个。
- 合计约 34–48 个。

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

## Kaiwu-Vast on chipyard（TLB / PTW / Cache；用户 2026-11-19 已定口径）

- **现状**：chipyard 只有 `WumingTinyConfig`（SRAM、`useVM=false`、无 MMU/PTW；`WumingCompatCoreParams` 里 `pgLevels=3` 是 RISC-V 残留）；gem5 侧 Vast 已完整（两级步查、cfx 模型、pmem DMA、time/hart），但 TLB 是**单数组 16 条全相联 + 轮转**、超页与普通页混存。
- **用户裁定（2026-11-19）**：只设**一级 TLB、分 I/D**（I/D 分离是**设计**不是实现细节；I-TLB 无 dirty 位）；普通页 **16 条 = 2 组 × 8 路、不设 sectored**；超页 **4 条全相联 + LRU**（4 条就够）；**无特殊条目**（rocket 的 special entry 为 PMP，DADAO 无 PMP）；**gem5 与 chipyard 在这些方面保持统一**（含组相联与超页个数）。
- **WumingVast 暂停（用户 2026-11-19）**：不做 Wuming 版 Vast；`m16-chipyard-006/007/008` 冻结，转 `wuqing` 路线。可复用部分 = **`cfx_ptw` 寄存器面（SoC 侧）**；PTW/TLB 待重启时按「独立模块 + 核适配层」重写。
- **落地方式**：归 **M16**（`milestones-m16.md`，用户 2026-11-19 裁定「这是 M16 的任务」）：`m16-chipyard-006`（核参数/地址通路/`cfx_ptw` 寄存器面）→ `007`（PTW 两级步查 + A/D）→ `008`（I/D TLB）→ `009`（D-Cache）→ `010`（I-Cache + 大存储/地址图）→ `011`（三方差分收口）；gem5 侧 `m16-gem5-014`（TLB 双表 + 2×8 + 4 超页 LRU）。
- **顺序理由**：cache 会改变 M16 已标定的周期基线（`docs/core-wuming-cycle-model.md` 在 SRAM/无 cache 上标定）⇒ **cache 单独排**，不与功能改动混做。
- **待定**：① 分片（`frags`）在 RTL 侧与 cache 的交互（64 KiB 页 = 1024 × 64 B block）；② `spike`/gem5 侧的 PTW 延迟是否要建模（当前 atomic，无时序）；③ `ISS-340`（gem5 Vast 仍 identity，而 spec 要求 `VA = PA + 2 TiB` 内核窗口）何时对齐。

# 后续里程碑备选（尚未立册）

> 以下为 M16 之后的方向候选：每条只记**当前状态 / 开启条件 / 待定项**，立册时按 `docs/Process-02` 转任务书。

## 架构符合性测试套件（参考 `riscv-arch-test` / ACT）

- **参考对象**：`riscv-arch-test`（ACT）——RISC-V International 维护的**架构符合性测试套件**：每条指令一组自检用例，把结果写进固定**签名（signature）区**，由框架与参考签名比对；用例用统一宏（TEST_* / RVTEST_*）表达，天然适配「换一个核就重跑」。
- **当前状态**：尚无内容。本仓现有 `tests/inst/**` 是**逐指令语义向量**（期望值内联、三方差分），与 ACT 的「签名 + 参考签名」形态不同：前者证明「语义对不对」，后者证明「实现是否**符合规范**（可移植性/合规）」。
- **为什么值得单列**：M15 的 IDL reference model + `tests/inst` 已能测语义，但**缺一个「规范符合性」的对外可交付物**；ACT 的形态（每题固定签名、可跨实现比对）是现成的模板。
- **不能照搬**：ACT 的用例是 **RISC-V 指令**（`RV32I/RV64I/M/A/F/D…`）与 RISC-V 的陷阱/CSR 模型，与 DADAO（四组寄存器、16 位立即数分片、`rd0/rb0` 特殊、cg/cfx 模型）全部不同 ⇒ **只借方法论与框架形态**，用例须从 `contracts/opcodes.yaml` + `spec/SimRISC-*` 重新派生。
- **待定**：① 覆盖口径（全 263 id？还是按册分层）；② 签名格式与存放位置（`tests/data/`？）；③ 比对组合（IDL reference model / QEMU / RTL 取哪几方做 golden）；④ 与 `tests/inst/**` 的分工（避免两套向量重复维护）。

## IDL 可执行参考模型

把 M15 的 `.idl` 跑起来，作**第四方差分参照**（不追求全量第四实现）。

- **候选任务**：`m17-idl-001` lexer/parser/AST/类型检查（12–16 天）；`m17-idl-002` 解释器：加载 ELF、四 bank 状态、48 位地址/大端、异常与 monitor、trace（10–14 天）；`m17-idl-003` 差分接入：273（整数）+ 167（访存）+ 67（控制流）逐例与 QEMU 一致、纳入 L2（8–10 天）；`m17-idl-004` 向量「算期望」派生（输入仍人挑，期望由 IDL 算，**不做输入自动生成**，8–10 天）；`m17-idl-005` FP 特殊值语义（NaN/Inf/次正规/五类标志，15–20 天）。
- **出口**：507 例与 QEMU 逐例一致；每个 operation 分支至少被一个向量走到；`make check-idl` 进 L2；分歧归因落 spec 裁定（**不是「IDL 一定对」**）。
- **与 M15 的边界**：M15 只结构化、不执行；可执行在此。

## 流水线处理器核（gem5-minor / chipyard-wuqing）

- **当前状态**：gem5 侧只用 `TimingSimpleCPU`（加每指令延迟的钩子），Minor 尚未接入；chipyard 侧**只有 `WumingTinyConfig`**（SRAM + cfx 测试机、无 MMU/TLB），`wuqing` 的 RTL 尚未出现。
- **开启条件**：`wuqing` RTL 可用（用户 2026-11-13：等其 RTL 出现后再开）。
- **前置条件（用户 2026-11-19 追加）：随机指令流差分测试**，参考 RISC-V 的 `riscv-dv` 思路——在接入 Minor / `wuqing` **之前**先具备「随机生成合法指令流 + 多模型逐指令比对」的能力，否则流水线核的时序/功能差异会被定向向量掩盖（定向用例只覆盖已知路径）。
  - **TestRIG**（**RISC-V International 官方项目**，比 `riscv-dv` 更接近我们要的形态）：用 **QuickCheck**（Haskell 属性测试）**生成随机指令流**，经 **DII 接口**（Design-Under-Test Interface）喂给**两个实现**，比对两侧 **RVFI trace**（RISC-V Formal Interface：逐指令的寄存器/内存读写与提交记录），不一致时**自动收缩（shrink）出最小反例**。两条可借的东西：① **RVFI 式逐指令 trace** 作为比对载体（比「比对最终内存」强得多，能定位到哪一条指令、哪个字段）；② **属性测试 + 自动收缩**（反例从几千条缩到十几条，才可能人工归因）。
  - 待定：生成器的合法性约束来源（`contracts/opcodes.yaml` + `legality_rules.yaml` 派生，**不照抄 riscv-dv / TestRIG 的 RISC-V 约束**）；比对模型组合（QEMU / gem5 / RTL / IDL 参考模型取哪几方）；失败归因判据（谁是 golden）；**DADAO 侧要不要先定义「DII 等价接口 + 逐指令 trace 格式」**（没有它，RVFI 这套方法论落不了地——可能要先为此立一个 infra 任务）。
- **待定**：Minor 的 `initiateAcc`/`completeAcc` 两阶段是 `ADR-0057` 在 `TimingSimpleCPU` 上先验证；迁到 Minor 时周期表哪些行仍然生效。

## 乱序处理器核（gem5-o3 / chipyard-wuxing）

- **当前状态**：同上，O3 与 `wuxing` 均未开始；gem5 O3 的访存两阶段与 `ADR-0057` 的 bundle 续跑模型需要重新评估。
- **开启条件**：`wuxing` RTL 可用。
- **待定**：乱序下每指令延迟钩子是否还成立（钩子假设顺序退休），或需改为对拍式建模。

## Vivado

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
