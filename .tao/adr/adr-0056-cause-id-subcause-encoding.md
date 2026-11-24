# ADR-0056: 页表异常的细粒度原因编码（每个 cause 独占一个 wyde：`CFXPERM`→wyde2、`CFXMEM`→wyde3）

> **取代注记（2026-11-24）**：本 ADR 的 **D2/D3**（「大类 + wyde 子原因」两级编码）与 **D4**（`CFXPERM`/`CFXMEM` 混合语义）**由 `ADR-0062` 取代/修订**；`D1`（低 16 位 one-hot）、`D5`（退出码）、`D6`/`D7`（同步义务）继续有效。**下文 decision 正文保持原样（历史记录，不改写）**；现行口径见 `ADR-0062` 与 `contract-see §6.1.1`。

**状态**：Accepted
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
- **D2 子原因字段（2026-11-16 三次裁定改版：**每个 cause 独占一个 wyde**）**：子原因区 `excp_cause_id[63:32]`，按 **16 位 wyde 分段**、**one-hot（恰一位）**：
  - **wyde2 `[47:32]` = `CFXPERM` 的子原因**；**wyde3 `[63:48]` = `CFXMEM` 的子原因**；
  - 收到 `CFXPERM` 时**只有 wyde2 有效**、收到 `CFXMEM` 时**只有 wyde3 有效**，**另一个 wyde 必须全 0**；其它 cause 下**两个 wyde 都必须全 0**；
  - `[31:16]` **保留给未来新的大类 cause**（`1<<14`–`1<<31` 可用），不得被子原因占用。
- **D3 位分配（固定表，按 wyde 分段）**：
  - **wyde2 `[47:32]`（`CFXPERM`）**：**低字节 `[39:32]` = 8 位权限类** —— `32 NUPERM`、`33 NJPERM`、`34 NSPERM`、`35 NHPERM`（HSJU 各自不符）、`36 NRPERM`、`37 NWPERM`、`38 NXPERM`（R/W/X 不符）、`39 NCFXPERM`（cfx 访问被来源掩码拒绝）；**高字节 `[47:40]` 保留（必须 0）**；
  - **wyde3 `[63:48]`（`CFXMEM`）**：**低字节 `[55:48]` = 8 位缺失类** —— `48 IGPTRAP`、`49 ISPTRAP`、`50 IGPFTRAP`、`51 ISPFTRAP`、`52 DGPTRAP`、`53 DSPTRAP`、`54 DGPFTRAP`、`55 DSPFTRAP`；**高字节 `[63:56]`** —— `56 ADWBFAIL`（A/D 回写失败）、`57 NONPTW`（非页表类 `CFXMEM`）、`58–63` 保留（必须 0）；
  - **用法（规范须写明）**：handler 拿到 `CFXPERM` 就取 `(cause_id >> 32) & 0xFFFF`，拿到 `CFXMEM` 就取 `(cause_id >> 48) & 0xFFFF`。
- **D4 `CFXMEM`/`CFXPERM` 的 `cause_info` 恒为「地址」（用户 2026-11-16 追加裁定：**一个 cause 只能有一种 info 类型**，handler 不得按子原因再分支）：
  - `CFXMEM`：访存地址；`ADWBFAIL` 子原因时 = **PTE 物理地址**；`NONPTW` 子原因时 = 被访问的核内地址；
  - `CFXPERM`：PTW/`cfxmem` 权限拒绝 = **访存地址**；`cfxexe` 拒绝 = **目标 IP**；`cfxtrap`/`cfx2r*` 拒绝（`NCFXPERM`）= **触发指令的地址**（与 `excp_cause_ip` 同值，规范须写明这是刻意统一，不是冗余错误）；
  - 其它 cause 的 `info` 语义**不变**（`CFXTRAP`/`CFXREG`/`CFXESC`/`ILLI`/`UNDI` = 指令编码；`IALIGN` = IP；`MALIGN` = 访存地址；`RASOF`/`RASUF` 原样）。
- **D5 `§7.1` 退出码不受影响**：monitor 段的 `bit3:0` 仍取低位 cause 索引，子原因位不参与退出码编码。
- **D6 三实现与契约同步**：QEMU（填 `cause_id` 时置子原因位）、gem5（`node_cfx`）、chipyard（`GewuFile`）三处同步；`contract-see §6.1` 增「子原因」列；`tests/arch` 与 K3 探针按子原因断言。
- **D7 上游册修订**：`DADAO-12 §3.6`（把「所有异常原因编码为 one-hot（64 位）」改写为「`[15:0]` = cause one-hot；`[31:16]` 保留（未来 cause）；`[39:32]` = `CFXPERM` 的 8 位权限类（wyde2 低字节）；`[55:48]` = `CFXMEM` 的 8 位缺失类（wyde3 低字节）；`[63:56]` 其它（`ADWBFAIL`/`NONPTW` + 6 位保留）」）+ `§4.1–§4.6`（各 monitor 表注明子原因字段）+ `§2.2.6`（与"仅触发最高优先级"对齐）；`sha256` 同笔重算，注记引用用户授权原话。`SPEC-189t` 的「不再区分 IGPTRAP…/NUPERM…」口径**由本 ADR 部分取代**（历史任务书不改，只在 `discussing.md`/ADR 记明）。

## Rationale（理由）

- **为什么不扩 cause 位**：`§7.1` 的 monitor 退出码只用 `bit3:0`（11 个索引已占满大半），扩 cause 会连带改退出码编码，波及三实现与全部相关测试；而子原因放进 `cause_id` 高位**完全不动退出码**。
- **为什么不塞 `cause_info`**：`info` 现在承载地址/PTE 地址，是**诊断必需**的；塞子原因要么挤掉地址，要么改 `info` 的位域语义（改面更大）。
- **为什么 one-hot 而不是任意位图**：`§2.2.6` 规定"仅触发优先级最高的异常"，子原因天然互斥；one-hot 与低位风格一致，也给"非 0 且多位 ⇒ 错误"提供判据。
- **为什么改成「一个 cause 独占一个 wyde」**：用户 2026-11-16 三次裁定 —— ① one-hot 补一位（`NONPTW`）；② 权限类正好 8 位、字节对齐；③ 子原因整体放到 bit32 以上；④ **`CFXPERM` 用 wyde2、`CFXMEM` 用 wyde3** ⇒ handler 只需按 cause 选一次移位（`>>32` 或 `>>48`），不必知道两张表；代价是 `[47:40]`/`[58:63]` 留空、未来 cause 位被压到 `[31:14]`（18 位，仍足够）。

## Consequences（影响）

- `spec/DADAO-12` 三处修订 + 锁重算（上游只读册，须用户授权原话入锁注记）；
- `contract-see §6.1` 扩列；`m14-spec-006`（K3 TLB 契约）按本 ADR 写 fault 段（子原因断言替代"只判两类"）；
- QEMU/gem5/chipyard 三实现各加一个子原因字段；`tests/arch` 与 K3 探针增加子原因断言（每类至少一例）；
- 历史文档（`.tao/archive/**`、`ADR-0040`/`ADR-0020` 中旧名）**不改**，但需在 `ADR-0040` 加一条「口径变更注记」指向本 ADR。

## 状态说明

2026-11-16 由主会话起草；用户已确认方案并两次收窄：① 16 位分配表 + 保留 A/D 回写失败位；② 「一个 cause 只能有一种 info 类型」⇒ `CFXPERM.info` **恒为地址**，`cfxtrap`/`cfx2r*` 拒绝填**指令地址**，并新增子原因 **`NCFXPERM`（`[31]`）**、把 **`ADWBFAIL` 挪到 `[32]`** ⇒ 子原因区扩为 `[32:16]`（17 位）。用户随后对 **D1–D7 逐条确认**（原话：「同意」）⇒ 置 `Accepted`；实施按 D7 立 `m14-spec-007`（上游册三处修订 + 锁重算 + `contract-see §6.1` 加子原因列），按 D6 立三实现与探针任务。
