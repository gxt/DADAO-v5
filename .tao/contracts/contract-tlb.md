# TLB 与失效接口合约（K3）

> **来源**：`spec/DADAO-12-SEE-主管系统运行环境.md`（0.8.0）的 `§2.2`/`§4.5`/`§3.6`/`§5.2`；测试机运行环境正文 `spec/Kaiwu-测试机运行环境.md`（0.4.7-rc，`§3.1`/`§6.3.5`）；决策 `.tao/adr/adr-0041-tlb-ad.md`（`ADR-0041`，Accepted）、`.tao/adr/adr-0056-cause-id-subcause-encoding.md`（`ADR-0056`，Accepted；其 **D2/D3 两级 wyde 编码由 `ADR-0062` 取代**）与 `.tao/adr/adr-0062-flat-cause-bitmap.md`（`ADR-0062`，Accepted，扁平位图唯一口径）；K3 的三条测试机约定（§9）为用户 2026-11-16 问答结论。**本合约不设版本号**（用户 2026-11-24 裁定；来源以上游册与 ADR 为准）。
>
> **范围**：`cfx_ptw` 的 TLB——匹配键、命中检查、填充条件、A/D 状态机与原子 OR 回写、`cfx_ptw_tlb_control` 失效接口（三维、判序、三操作、三档范围、`ASID_ANY` 与 `G`）、异常路由与**高位位图归属**、访存判定顺序；消费方 = QEMU 的 PTW/TLB 实现（`m14-qemu-*`）与 `tests/arch` 的 PTW/TLB 探针。页表项字段格式、两级页表步进与页权限的**位定义**归 `contract-see §2`，本合约只收 TLB 侧语义。
>
> **来源标注**：每条规范性断言句末以方括号标注来源——上游册写 `DADAO-12` + `§` + 章节名，测试机正文写 `Machine-01` + `§N`；上游未规定、由用户 2026-11-16 逐条确认的测试机约定，句末另标决策标记（本合约仅 §9 三条）。不写行号。
>
> **说明**：本合约由 spec/ 归一化投影而来，只做归一化 + 指针、不复制上游正文；面向实现与探针，与 spec/ 冲突时阻断实现，走变更流程（见 `docs/Process-02-合约编写规范.md`）。

---

## §1 归属与基本状态

- TLB-01 **归属**：TLB 属 `cfx_ptw`；没有独立的 TLB 核芯功能扩展，也没有 `tlb_enable`/`tlb_exist` 位——`ptw_enable = 1` 即参与查找，`ptw_enable = 0` 时地址转换整体旁路（TLB 不参与）。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-02 **条目内容**：一条 TLB 条目保存虚拟页、页大小、ASID、`G`、PPN、HSJU、R/W/X、SPF/GPF 与本地 A/D；条目数、组织与替换策略**由实现决定**。[DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-03 **复位状态**：PTBR = 0、ASID = 0、`ptw_enable = 0`、TLB 为空。[DADAO-12 §2.2 虚实地址转换][DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-04 **寄存器位**：`cfx_ptw_tlb_control` 为 `cg12 rc0`、WO（写即执行、无完成状态），`cfx_ptw_tlb_asid` 为 `cg12 rc1`（`[15:0]`，所有值可用，`[63:16]` 读 0），`cfx_ptw_tlb_addr_start`（`VA[41:0]`）与 `cfx_ptw_tlb_addr_size`（字节数）为 `cg12 rc2`/`rc3`。[DADAO-12 §4.5 cfx_ptw - page table walker]

## §2 匹配键与查找

- TLB-05 **匹配条件** = （ASID 匹配）AND（地址匹配）：条目的虚拟页必须覆盖本次访问地址；条目 `G = 0` 时其 ASID 须等于 `cfx_ptw_tlb_asid`，`G = 1` 时跨 ASID 匹配。[DADAO-12 §4.5 cfx_ptw - page table walker][DADAO-12 §2.2.5 操作系统页管理]
- TLB-06 **超页 / 普通页共用同一查找流程**：超页条目的虚拟页覆盖 512 MiB 对齐区间、普通页条目的虚拟页覆盖 64 KiB 对齐区间，页大小随条目记录，匹配规则同 TLB-05。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §2.2.3 一级页表条目格式][DADAO-12 §2.2.4 二级页表条目格式]
- TLB-07 **命中不重读 PTE**：命中时直接用条目中的 SPF/GPF、HSJU 与 R/W/X 做检查，不访问页表内存。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-08 **未命中**：继续页表步进（`DADAO-12 §2.2.1`/`§2.2.2` 第三步）。[DADAO-12 §2.2.2 普通页的地址转换]

## §3 命中检查顺序与填充条件

- TLB-09 **命中检查顺序**（与页表步进一致）：① 条目 SPF/GPF 中对应小页标记位 = 0 ⇒ 只置缺失类位图 `[51]`/`[55]`；② HSJU 不符 ⇒ 只置 `[32]`–`[35]` 之一；③ R/W/X 不符 ⇒ 只置 `[36]`–`[38]` 之一（取指要 `X`、读要 `R`、写要 `W`）；三步均低位 cause = 0、`CFXPERM`/`CFXMEM` = 0。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §2.2.6 异常检查优先级]
- TLB-10 **命中且检查通过**：跳过页表步进，更新 A/D 后形成最终物理地址。[DADAO-12 §2.2.1 超页的地址转换]
- TLB-11 **只有步进成功才填充**：PTE 有效且全部检查通过才把结果填入 TLB；缺页/权限失败**不填充**，也**不更新 A/D**。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §2.2.2 普通页的地址转换][DADAO-12 §2.2.5 操作系统页管理]
- TLB-12 **替换须先回写**：替换（或失效）带未回写 A/D 的条目时须先回写。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §4.5 cfx_ptw - page table walker]

## §4 A/D 状态机与原子 OR 回写

- TLB-13 **填充取值**：`A_local = PTE.A`、`D_local = PTE.D`、`A_dirty = D_dirty = 0`；填充本身**不产生回写**。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-14 **访问置位**：读/取指在 `A_local = 0` 时置 `A_local = 1`、`A_dirty = 1`；写除上述置位外，还须在 `D_local = 0` 时置 `D_local = 1`、`D_dirty = 1`；该规则对「命中」与「本次访问触发填充」同样适用。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-15 **回写语义**：只把挂起的 A/D 位做**原子 OR** 写入 PTE（保留其它字段），成功后清挂起位；页表页必须可写。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-16 **回写失败**：只置 `[56] ADWBFAIL`（`CFXMEM` = 0、低位 cause = 0），进入当前运行模式 monitor，`cause_info` = PTE 物理地址；**失败条目保留**（不静默丢 A/D）。[DADAO-12 §4.5 cfx_ptw - page table walker][DADAO-12 §2.2.6 异常检查优先级]
- TLB-17 **三种操作对条目的作用**：`clean` 回写后**保留**条目、`invalid` **不写回**直接删除、`flush` 回写后删除（回写失败时**不删除该条目**）。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-18 **软件责任**：软件清 PTE 的 A/D 后必须显式失效对应条目（硬件不自动重读 PTE）。[DADAO-12 §2.2.5 操作系统页管理]

## §5 `cfx_ptw_tlb_control` 的编码与判序

- TLB-19 **编码**：`[1:0]` 操作 = `00=none`/`01=clean`/`10=invalid`/`11=flush`；`[3:2]` 地址范围 = `00=all`/`01=VA`/`10=range`/`11=reserved`；`bit4 = ASID_ANY`；其余位保留。[DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-20 **三维正交**：操作、地址范围、ASID 三个维度互相独立，不互相隐含。[DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-21 **判序**：先判操作（`[1:0]`），再判地址范围与操作数——`none` 不进入范围判定；只有 `clean`/`invalid`/`flush` 才校验范围编码与 `size`。[DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-22 **`none` 无条件 no-op**：不报异常，且**不检查**范围编码与 `size`（`地址范围 = 11` 或 `range` 且 `size = 0` 在该操作下同样不报）；`ASID_ANY`/start/size 均被忽略。[DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-23 **三档地址范围**（仅 `clean`/`invalid`/`flush` 生效）：`all` 忽略 start/size；`VA` 只匹配**包含** `tlb_addr_start` 的条目（忽略 size）；`range` 匹配与 `[start, start+size)` **相交**的条目。[DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-24 **非法编码/操作数**：`地址范围 = 11`，或 `range` 且 `size = 0` ⇒ `CFXREG`（`cause_info` = 指令编码）。[DADAO-12 §4.5 cfx_ptw - page table walker]

## §6 ASID 维度与 `G`

- TLB-25 **`ASID_ANY = 1`**：包含 `G = 1` 的条目（所有 ASID 的条目都在处理范围）。[DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-26 **`ASID_ANY = 0`**：只处理 `G = 0` 且 ASID 匹配的条目，**不碰 `G` 条目**。[DADAO-12 §4.5 cfx_ptw - page table walker][DADAO-12 §2.2.5 操作系统页管理]
- TLB-27 **`G` 的语义**：叶子 PTE 的 `G = 1` 表示全局页——在 TLB 中跨 ASID 复用；软件必须保证 `G = 1` 的页在所有地址空间中映射一致；L1 非叶子条目的 `G` 无意义（软件写 0、硬件忽略）。[DADAO-12 §2.2.5 操作系统页管理]
- TLB-28 **正常完成不报异常**：`none`/`clean`/`invalid`/`flush` 的正常完成（含 `none` 的退化操作数）都不产生异常；异常只有 `CFXREG`（TLB-24）与回写失败的 `[56] ADWBFAIL`（TLB-16）。[DADAO-12 §4.5 cfx_ptw - page table walker]

## §7 不隐含失效的写操作

- TLB-29 **写 PTBR / ASID / `ptw_enable = 1` 均不隐含 TLB 失效**：TLB 的失效只能由软件显式发出（TLB-19 的三种操作）。[DADAO-12 §2.2 虚实地址转换][DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw - page table walker]
- TLB-30 **进程切换四步**：① 写新 ASID 或新 PTBR；② **显式** invalidate TLB；③ 置 `ptw_enable = 1`；④ 保存/恢复 `cg6` 暂存寄存器。[DADAO-12 §2.2.5 操作系统页管理]

## §8 异常路由、`cause_info` 与高位位图

- TLB-31 **路由**：TLB 命中与页表步进产生的异常都进**当前运行模式 monitor**（`user→cfx0`、`jail→cfx1`、`supv→cfx2`、`hypv→cfx3`），不进入 `cfx_ptw` 自身向量。[DADAO-12 §2.2.6 异常检查优先级][DADAO-12 §5.2 异常进入流程]
- TLB-32 **函数映射（扁平）**：页表未映射（L1/L2 `P = 0`、SPF/GPF 对应位 = 0）⇒ 只置缺失类位图 `[48]`–`[55]` 之一；A/D 回写失败 ⇒ 只置 `[56] ADWBFAIL`；HSJU 或 R/W/X 不符 ⇒ 只置权限类位图 `[32]`–`[38]` 之一。上述故障低位 cause = 0、`CFXMEM`/`CFXPERM` = 0。[DADAO-12 §2.2.6 异常检查优先级][DADAO-12 §2.2.5 操作系统页管理]
- TLB-33 **`cause_info` 恒为地址**：`CFXMEM` = 被访问的核内地址；`[32..38]`/`[48..55]` = 访问的 VA；`[56] ADWBFAIL` = PTE 物理地址；`CFXPERM` 按 §8 的地址三形态（`cfxmem` 轴访存地址 / `cfxexe` 目标 IP / `cfxtrap`、`cfx2rd`、`cfx2rc` 触发指令地址）。[DADAO-12 §3.6 cg5 - 异常现场寄存器]
- TLB-34 **高位位图（扁平）**：PTW 权限拒绝只置 **`[32]`–`[38]` 之一**（`NUPERM`/`NJPERM`/`NSPERM`/`NHPERM`/`NRPERM`/`NWPERM`/`NXPERM`；`[39]` 删除、恒 0；`[47:40]` 保留），PTW 缺失只置 **`[48]`–`[55]` 之一**（`IGPTRAP`/`ISPTRAP`/`IGPFTRAP`/`ISPFTRAP`/`DGPTRAP`/`DSPTRAP`/`DGPFTRAP`/`DSPFTRAP`），A/D 回写失败只置 **`[56] ADWBFAIL`**（`[57]` 删除、恒 0；`[63:58]` 保留）；上述位与低位 cause **互斥**（PTW 故障 `[15:0]` 全 0，不置 `CFXPERM`/`CFXMEM`），64 位内恰一位为 1。逐位见 `contract-see §6.1.1`。[DADAO-12 §3.6 cg5 - 异常现场寄存器][DADAO-12 §2.2.6 异常检查优先级][ADR-0062 D1/D3]
- TLB-35 **前缀与优先级**：取指用 `I` 前缀的位、数据读写用 `D` 前缀的位；多条同时满足时只报最高优先级一条（`ptw_enable = 0` ⇒ L1 `P = 0` ⇒ L1 SPF 位 = 0 ⇒ L2 `P = 0` ⇒ GPF 位 = 0 ⇒ HSJU ⇒ R/W/X），后续检查不再执行。[DADAO-12 §2.2.6 异常检查优先级]
- TLB-36 **退出码不承载 PTW 故障**：monitor 段退出码的 `bit3:0` 取**低位** cause 索引；PTW 权限/缺失与 A/D 回写失败低位 cause = 0、只置高位位图，**不进入该退出码编码**。`Kaiwu-Vast` 的 PTW 故障测试直接读 `excp_cause_id` 判因，不沿用 `0xF0 | bit3:0`；`Kaiwu-Tiny` 无 PTW，不受影响。[DADAO-12 §3.6 cg5 - 异常现场寄存器][Machine-01 §7.1 退出码][ADR-0062 D6]

## §9 测试机约定（同步完成 / per-hart / 实现范围）

- TLB-37 **失效写指令同步完成 + 首个失败即停**：`cfx_ptw_tlb_control` 的写指令**同步完成**——指令返回即生效，其后的访存必见失效结果（无 busy/done 位、无异步完成信号）；`clean`/`flush` 的回写失败**在该写指令上**只置 `[56] ADWBFAIL`（`CFXMEM` = 0、低位 cause = 0，进入当前运行模式 monitor；`cause_info` = PTE 物理地址），且**不得部分完成**——按**条目级 + 遇错即停**解释：命令按条目处理，**首个失败条目保持原状**（`flush` 失败不删除该条目、`clean` 失败不清其挂起位）并**立即停止**，**其后条目一律不处理、保持原状**；一条指令**最多报一处失败**（异常帧只有一个 `cause_info`）⇒ 未处理的条目仍是旧翻译，**内核须自行补偿**（重发同一命令逐次收敛，或用 `scope=VA` 逐条重试），契约不提供"其余条目照常处理"的保证。[Machine-01 §3.1 TLB 的测试机约定][DADAO-12 §4.5 cfx_ptw - page table walker][spec-decision，用户 2026-11-16 裁定「条目级」+「遇错即停」]
- TLB-38 **per-hart**：TLB 与 `cfx_ptw_tlb_control` 都是 **per-hart** 状态，失效命令只作用于执行该指令的 hart；跨 hart 的失效传播与一致性**不在本版范围**（重开点登记为 `ISS-459`，与多 hart 机型一并处理）。[Machine-01 §3.1 TLB 的测试机约定][DADAO-12 §4.5 cfx_ptw - page table walker][spec-decision]
- TLB-39 **实现范围**：本版 TLB 建模由 **QEMU** 机器模型承担；`tests/arch` 的 PTW/TLB 探针是**跨实现判据**（chipyard/gem5 不在本阶段验收面）。[Machine-01 §3.1 TLB 的测试机约定][spec-decision]

## §10 访存判定顺序（先地址类、再 `ptw_enable`）

- TLB-40 **第一步先分地址类**：`VA[47:42] ≠ 0` ⇒ 属 cfx 核内地址空间，按核内空间语义处理，**不进入 PTW/TLB 流程**、不产生 TLB 条目。[DADAO-12 §2.1 核内地址空间][DADAO-12 §2.2 虚实地址转换]
- TLB-41 **第二步看 `ptw_enable`**：`VA[47:42] = 0` 且 `ptw_enable = 0` ⇒ 访存（含取指）**直接 `CFXMEM`**（非 PTW 类，不置高位位图），**不查 TLB、不产生条目、不直通物理存储器**。[DADAO-12 §2.2 虚实地址转换][DADAO-12 §2.2.6 异常检查优先级]
- TLB-42 **第三步才进 PTW/TLB**：`VA[47:42] = 0` 且 `ptw_enable = 1` ⇒ 走 `DADAO-12 §2.2.1`/`§2.2.2` 的四步流程；未映射 ⇒ 只置缺失类位图 `[48]`–`[55]` 之一、权限不符 ⇒ 只置权限类位图 `[32]`–`[38]` 之一（均进当前运行模式 monitor，低位 cause = 0、`CFXMEM`/`CFXPERM` = 0）。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §2.2.2 普通页的地址转换]
- TLB-43 **判定顺序即异常优先级**：`ptw_enable = 0` 的 `CFXMEM` 是页表异常判定的第 1 步（先于 P=0/小页缺失/HSJU/R/W/X）。[DADAO-12 §2.2.6 异常检查优先级]

## §11 门控建议（13 条 `tests/arch` 探针；本节只设计，不含实现）

口径：探针**只按硬件语义断言**（未映射 ⇒ 高位位图；写只读页 ⇒ 高位位图），位从 `excp_cause_id` 的**绝对位号**取（如 `(cause_id >> 52) & 1`），`cause_info` 断言按 TLB-33 取地址。[DADAO-12 §3.6 cg5 - 异常现场寄存器]

载体：不需要自建页表的走 `tests/arch/ptw/*.s` + `tests/arch/ptw/expected.yaml`（在 `tests/arch.yaml` 登记、`platforms: [system]`）；需要改 PTE / 改 PTBR 的走 `tools/testcases/arch/min_rom_probe_*.py` 并登记到 `Makefile` 的 `ARCH_CFX_PROBES`。回写失败子用例在本机 PA RAM 全可写的条件下无机器级可达路径，改由实现层注入 PTE 写失败覆盖。[Machine-01 §3.1 TLB 的测试机约定]

| # | 探针 | 构造要点 | 断言点（cause / 高位位图位） | 载体 |
|---|------|----------|---------------------------|------|
| ① | fill 后命中 | 同一有效页连续访问两次（首次未命中⇒步进⇒填充） | 无异常（`cause_id[15:0]` 无 one-hot）；高位位图全 0；两次数据一致 | `arch/ptw` |
| ② | 命中不重读 PTE | 首次访问后把该 PTE 的 PPN 改成另一 PA（不 invalidate），第二次访问 | 无异常；高位位图全 0；读到**旧** PA 的数据（证明命中不重读 PTE） | `min_rom_probe` |
| ③ | `invalid` + VA | 两页各 fill 一次，`op=invalid`/`scope=VA`/`start=` 页 X | 无异常；高位位图全 0；X 重步进（读新生效 PPN）、Y 仍命中旧条目 | `min_rom_probe` |
| ④ | `invalid` + range | `start`/`size` 覆盖页 X 不覆盖页 Y，`op=invalid`/`scope=range` | 无异常；高位位图全 0；范围内页重步进、范围外页仍命中 | `min_rom_probe` |
| ⑤ | `ASID_ANY` 与 `G` | 条 A（`G=0`, ASID=0）、条 B（`G=1`）；切 ASID=1 后分别发 `ASID_ANY=0`/`=1` 的 `invalid` | 无异常；高位位图全 0；`ASID_ANY=0` 后 B 仍命中（不碰 `G`）、`=1` 后 B 重步进 | `min_rom_probe` |
| ⑥ | `clean` 回写 A/D vs `invalid` 不回写 | 两页各做读+写（置挂起位）；对 X 发 `clean`、对 Y 发 `invalid` | 无异常；高位位图全 0；X 的 PTE 回写 `A=1`/`D=1` 且条目保留；Y 的 PTE A/D 仍为 0 | `arch/ptw` |
| ⑦ | `flush` 回写+删除 · 失败不删 | 正常路径：置挂起位后 `flush`，再读 PTE 并重新访问；失败路径（本机 PA RAM 全可写 ⇒ 机器级不可达，由实现层注入 PTE 写失败覆盖） | 正常：无异常 + 高位位图全 0 + `A`/`D` 已 OR 回写 PTE + 条目消失（再访问重步进）；失败（实现层）：只置 `[56] ADWBFAIL`（`CFXMEM` = 0、低位 cause = 0）+ 条目**保留** | `min_rom_probe`（失败子用例 = 实现层注入） |
| ⑧ | 写 PTBR/ASID/`ptw_enable` 不隐含 invalidate | 改 PTE 的 PPN 后依次重写 PTBR、ASID、`ptw_enable=1`（同值），再访问 | 无异常；高位位图全 0；仍命中**旧**条目（读到旧 PA 数据） | `min_rom_probe` |
| ⑨a | `ptw_enable=0` 直接 `CFXMEM` | 选一个此前未被访问的页，置 `ptw_enable=0` 后访问 `VA[47:42]=0` 的该页地址 | `CFXMEM`（高位位图全 0）；`cause_info` = 访存地址；旁路期间不查 TLB、不产生条目（该页 PTE 的 `A`/`D` 仍为 0） | `arch/ptw` |
| ⑨b | 页表未映射 ⇒ 缺失类位图 | `ptw_enable=1`，数据读一个 L1 `P=0`（`SP=0`，普通页路径）的 VA | 只置 `[52] DGPTRAP`（取指则 `[48] IGPTRAP`；低位 cause = `CFXMEM`/`CFXPERM` = 0）；`cause_info` = 访存地址 | `arch/ptw` |
| ⑩ | 写只读页 ⇒ 权限类位图 | 对 `R=1`/`W=0` 的有效页做 `st` | 只置 `[37] NWPERM`（低位 cause = 0、`CFXPERM` = 0、`[63:32]` 其余位全 0）；`cause_info` = 访存地址；与 ⑨b 的位图区间互斥 | `arch/ptw` |
| ⑪ | 改 PTE 不 invalidate / invalid 后生效 | 改 PTE 的 PPN 不失效 ⇒ 仍读旧页；再 `invalid` + VA ⇒ 读新页 | 前半：无异常 + 高位位图全 0 + 旧数据；后半：无异常 + 高位位图全 0 + 新数据（证明失效是唯一生效路径） | `min_rom_probe` |
| ⑫ | `VA[47:42] ≠ 0` 不走 PTW/TLB | 访问 cfx 核内地址：合法的 hmon/pmem 段一次 + 非法子区间一次（`ptw_enable` 保持 1） | 合法：无异常 + 高位位图全 0（无 TLB 条目、不读页表）；非法：`CFXMEM`（高位位图全 0） | `arch/ptw` |

- 探针计数 = 13 条（①–⑧ 为基础集、⑨a/⑨b/⑩/⑪/⑫ 为 K3 扩展集）；每条都有可达 FAIL 路径（断言「读到旧数据 / 位图位不符 / 条目未被删除」任一不成立即判负）。[Machine-01 §3.1 TLB 的测试机约定]
- 探针实现与 `tests/arch.yaml` 登记归后续任务；本合约只固定断言点与载体形态（不改 `tests/**`）。[Machine-01 §3.1 TLB 的测试机约定]

## §12 变更记录

- **扁平位图（2026-11-24，`m17-spec-002`，`ADR-0062`；不设版本号）**：TLB-16/34/41 与 §11 探针的「子原因 wyde 归属」改为扁平位图——PTW 权限只置 `[32..38]` 之一、缺失只置 `[48..55]` 之一、A/D 回写失败只置 `[56]`，低位 cause = 0；`CFXPERM`/`CFXMEM` 只保留各自单一含义。TLB-36 改写为「退出码不承载 PTW 故障」：monitor `bit3:0` 取低位 cause 索引，PTW 故障低位 cause = 0 ⇒ 不进该编码；`Kaiwu-Vast` 直接读 `cause_id`、`Kaiwu-Tiny` 无 PTW。头部版本段删除（用户 2026-11-24 裁定本合约不设版本号）。[DADAO-12 §3.6 cg5 - 异常现场寄存器][ADR-0062 D1/D3/D6]

- **0.7.2（2026-11-16）**：TLB-37 的失败处理由「其余条目照常处理」改为**条目级 + 遇错即停**（用户 2026-11-16 裁定原话：「条目级」/「遇错即停」）：首个失败条目保持原状并立即停止，其后条目不处理；一条指令最多报一处失败（帧只有一个 `cause_info`）⇒ 内核须自行重发命令补偿。同步 `ADR-0041 D3.2`。版本号按 `docs/Process-02` 递增（内容变更）。
- **0.7.1（2026-11-16）**：首版。收编 `DADAO-12 §2.2.1`–`§2.2.6`、`§4.5`、`§3.6`、`§5.2` 的 TLB 语义（TLB-01…TLB-36、TLB-40…TLB-43），三条测试机约定（TLB-37…TLB-39，用户 2026-11-16 确认）与 13 条门控建议（§11）。版本取 `README.md` 版本表的 SEE / SBI 已发布版。
