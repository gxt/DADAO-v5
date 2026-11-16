# ADR-0056: 页表异常的细粒度原因编码（`cause_id[31:16]` 子原因 one-hot）

**状态**：Candidate
**日期**：2026-11-16
**关联**：`SPEC-186t`/`SPEC-189t`（M11：§5.2 重写 + 跨节原因表收敛）、`ISS-344`、`spec/DADAO-12 §2.2.6`/`§3.6`/`§4.1–§4.6`、`contract-see §6.1`、`Kaiwu §7.1`、`m14-spec-006`（K3 TLB 契约）

## Context（背景）

M11 期间用户裁定「执行过程中的同步异常和异步中断应该先进对应运行模式的 monitor」并把 `unmapped` 归入当前 monitor 的 `CFXMEM`；随后 `SPEC-186t` 重写 `DADAO-12 §5.2`、`SPEC-189t` 跨节同步（登记 `ISS-344`）。

`SPEC-189t` 的任务书把口径写成「取指/读写**不再区分** `IGPTRAP`…/`NUPERM`…」，于是 `IGPTRAP/ISPTRAP/IGPFTRAP/ISPFTRAP/DGPTRAP/DSPTRAP/DGPFTRAP/DSPFTRAP`、`NUPERM/NJPERM/NSPERM/NHPERM`、`NXPERM/NWPERM/NRPERM` 与 `PTWERR` 一并从 `spec/` 消失。

用户 2026-11-16 指出**收敛过头**：「当时只是删除 `PTWERR`，没有要删除后面的各种缺页/权限类的 ptw 相关的同步异常；否则，怎么判断错误原因？」事实核实：

- 这些细名**从未有过独立的 cause 位**（`cfx0–cfx3` 的原因表一直只有 11 个 `1 << n`）；它们原先只作为 `§2.2.6` 的**散文名**、异常投递给 `cfx_ptw`；
- 现状 `cause_info` 只承载**地址/指令编码**，**没有**子原因 ⇒ 内核无法区分"超页缺失 / 小页缺失 / GPF 缺失 / HSJU 不符 / R/W/X 不符"。

## Decision（决策）

- **D1 低 16 位不变**：`excp_cause_id[15:0]` 仍是现有的 11 项 one-hot 大类（`CFXTRAP`…`IALIGN`），编码与现有表**一字不改**。
- **D2 子原因字段**：`excp_cause_id[31:16]` 为**子原因 one-hot**（恰一位置位），**仅在 `CFXMEM`（`1<<1`）或 `CFXPERM`（`1<<7`）时有效**；其它 cause 下 `[31:16]` **必须全 0**（非 0 ⇒ 按 `§3.6`「未列出位被错误触发」处理）。
- **D3 位分配（固定表）**：
  - `[16]` `IGPTRAP`（取指 L1 `P=0`(SP=0) / L2 `P=0`）、`[17]` `ISPTRAP`（取指超页缺失）、`[18]` `IGPFTRAP`（取指 GPF 位=0）、`[19]` `ISPFTRAP`（取指 SPF 位=0）；
  - `[20]` `DGPTRAP`、`[21]` `DSPTRAP`、`[22]` `DGPFTRAP`、`[23]` `DSPFTRAP`（数据侧同名语义）；
  - `[24]` `NUPERM`、`[25]` `NJPERM`、`[26]` `NSPERM`、`[27]` `NHPERM`（HSJU 四位各自不符）；
  - `[28]` `NRPERM`、`[29]` `NWPERM`、`[30]` `NXPERM`（R/W/X 不符）；
  - `[31]` `ADWBFAIL`（A/D 回写失败；原 `PTWERR` 的情形，**不恢复为独立 cause**，此时 `cause_info` = PTE 物理地址）。
- **D4 `cause_info` 语义不变**：仍是访存地址（`CFXMEM`）/ PTE 物理地址（A/D 回写失败）/ 访存地址或指令编码（`CFXPERM`）；不把子原因塞进 `info`。
- **D5 `§7.1` 退出码不受影响**：monitor 段的 `bit3:0` 仍取低位 cause 索引，子原因位不参与退出码编码。
- **D6 三实现与契约同步**：QEMU（填 `cause_id` 时置子原因位）、gem5（`node_cfx`）、chipyard（`GewuFile`）三处同步；`contract-see §6.1` 增「子原因」列；`tests/arch` 与 K3 探针按子原因断言。
- **D7 上游册修订**：`DADAO-12 §3.6`（cause 编码总述增分层说明）+ `§4.1–§4.6`（各 monitor 表注明子原因字段）+ `§2.2.6`（与"仅触发最高优先级"对齐）；`sha256` 同笔重算，注记引用用户授权原话。`SPEC-189t` 的「不再区分 IGPTRAP…/NUPERM…」口径**由本 ADR 部分取代**（历史任务书不改，只在 `discussing.md`/ADR 记明）。

## Rationale（理由）

- **为什么不扩 cause 位**：`§7.1` 的 monitor 退出码只用 `bit3:0`（11 个索引已占满大半），扩 cause 会连带改退出码编码，波及三实现与全部相关测试；而子原因放进 `cause_id` 高位**完全不动退出码**。
- **为什么不塞 `cause_info`**：`info` 现在承载地址/PTE 地址，是**诊断必需**的；塞子原因要么挤掉地址，要么改 `info` 的位域语义（改面更大）。
- **为什么 one-hot 而不是任意位图**：`§2.2.6` 规定"仅触发优先级最高的异常"，子原因天然互斥；one-hot 与低位风格一致，也给"非 0 且多位 ⇒ 错误"提供判据。
- **为什么保留 `[31:16]` 而不是 `[63:32]`**：把 `[63:32]` 留给未来新的大类 cause 位（`1<<32` 起），子原因固定在 `[31:16]`，两层不抢空间。

## Consequences（影响）

- `spec/DADAO-12` 三处修订 + 锁重算（上游只读册，须用户授权原话入锁注记）；
- `contract-see §6.1` 扩列；`m14-spec-006`（K3 TLB 契约）按本 ADR 写 fault 段（子原因断言替代"只判两类"）；
- QEMU/gem5/chipyard 三实现各加一个子原因字段；`tests/arch` 与 K3 探针增加子原因断言（每类至少一例）；
- 历史文档（`.tao/archive/**`、`ADR-0040`/`ADR-0020` 中旧名）**不改**，但需在 `ADR-0040` 加一条「口径变更注记」指向本 ADR。

## 状态说明

2026-11-16 由主会话起草；用户已确认方案（16 位分配表照提案、第 31 位保留、同意先出 ADR 草案）。**D1–D7 须逐条确认**，确认后置 `Accepted` 并按 D7 立 spec 任务、D6 立三实现任务。
