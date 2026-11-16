# m14-qemu-005: QEMU TLB 按契约对齐 + 页表异常填 `cause_id[63:48]/[47:32]（wyde3/wyde2）` 子原因

**模块**：qemu
**项目里程碑**：M14
**依赖**：`m14-spec-006`（K3 的 TLB 契约，**硬依赖**：`ADR-0052 D6` 要求先定义后实现）；`m14-spec-007`（子原因编码落地到 `spec/DADAO-12` + `contract-see §6.1`，**并行来源**：位表以 `ADR-0056 D3` 为准，`spec-007` 落地后与 `§6.1` 对账）；`m14-testcases-005`（**软依赖**：其 TLB 探针是「先红后绿」的判据载体；未落地时按验收 2 的临时探针取证）
**可并行分片**：否（`components/qemu` 单写者）
**并行组**：**可**与 `m14-linux-011` / `m14-linux-012` 并行（不同组件域）；**必须晚于** `m14-testcases-005` 的探针落地才能做「先红后绿」（探针是它的判据载体）；与 `m14-qemu-002/003/004` 串行（同一组件）
**预估**：3–4 h（含 QEMU 重建与多路注入各 1 次重建）
**档位**：大改（组件源码改 + 重建 + 补丁树；复核须独立重建 + ≥4 路注入）
**状态**：待开始

## 背景

QEMU 侧 TLB 的**结构**已在（可核，`components/qemu/patches/target/dadao/`）：

- `helper.c`：`dadao_tlb_lookup`（VA+ASID 匹配，`G=1` 跨 ASID）、`dadao_tlb_check`（命中路径：级内 `frags` → HSJU → R/W/X）、`dadao_tlb_touch`（A/D 本地置位）、`dadao_tlb_writeback`（原子 OR 回写）、`dadao_tlb_insert`（替换前回写，失败不清受害条目）、`dadao_tlb_control_exec`（op/scope/ASID_ANY 三维、`none` 先判后 no-op、`CFXREG` 两种非法操作数）、`dadao_ptw_walk`（L1/L2 步进）、`dadao_cpu_tlb_fill`（`VA[47:42]` 分派 → `ptw_enable=0` 直接 `CFXMEM` → TLB 查 → 步进）；
- `cpu.h`：`DADAOTlbEntry`（va/size_log2/pa/pte_pa/asid/flags/frags/hsju/a_local/d_local/a_dirty/d_dirty/valid）+ `DADAO_TLB_CMD_*`；
- `DADAO_EXCP_PTW_FAULT` + `env->ptw_fault_cause` / `ptw_fault_info`，经 `cfx_enter()` 写入 `cg5 rc2`。

**但对照 K3 契约有三处实质缺口**（本任务就是补它们）：

1. **子原因完全没填**：`ptw_fault_cause` 只承载大类（`1<<1` / `1<<7`），`cause_id[63:48]/[47:32]（wyde3/wyde2）` 恒 0 ⇒ 内核无法区分「超页缺失 / 小页缺失 / GPF 缺失 / HSJU 不符 / R/W/X 不符 / A/D 回写失败」（`ADR-0056 D3` 的 18 位（wyde2/wyde3 分段） one-hot）。
2. **「不得部分完成」未落实**：`dadao_tlb_control_exec` 对匹配条目**逐条**回写/删除，第 N 条失败时前 N−1 条已改（`clean` 的挂起位已清、`flush` 的条目已删）⇒ 与用户口径（`clean`/`flush` 失败**不得部分完成**）冲突；`spec/DADAO-12 §4.5` 只写了「失败条目保留」，没写跨条目原子性。
3. **命中路径两支写同一结果**：`dadao_tlb_check` 里 `if (super) *cause = CFXMEM; else *cause = CFXMEM;` —— 子原因化后这两支必须分别给 `ISPTRAP`/`DSPTRAP` 与 `IGPTRAP`/`DGPTRAP`，否则该分支永远无法通过反例门控。

另有一处**语义空白**需裁定：`CFXMEM` 的「非页表类」触发（`VA[47:42]` 保留/未实现 cfx 的普通访存、`cfx_pmem` SRAM 越界——`ADR-0039` Step 1-c）在 `ADR-0056 D3` 里没有位号，而 `D2` 把子原因写成「one-hot」⇒ 这类 `CFXMEM` 的高位该是 0 还是必须有一位。

## 目标

1. **填子原因**（`ADR-0056 D3`，`cause_id[63:48]/[47:32]（wyde3/wyde2）` 恰一位）：
   - 取指侧：L1 `P=0 && SP=1` ⇒ `[17] ISPTRAP`；L1 `P=0 && SP=0` ⇒ `[16] IGPTRAP`；L1 `SP=1` 且 `SPF` 位=0 ⇒ `[19] ISPFTRAP`；L2 `P=0` ⇒ `[16] IGPTRAP`；L2 `GPF` 位=0 ⇒ `[18] IGPFTRAP`；
   - 数据侧同名：`[20] DGPTRAP` / `[21] DSPTRAP` / `[22] DGPFTRAP` / `[23] DSPFTRAP`；
   - HSJU 不符 ⇒ 按**当前运行模式**的位给 `[24] NUPERM`(user) / `[25] NJPERM`(jail) / `[26] NSPERM`(supv) / `[27] NHPERM`(hypv)；
   - R/W/X 不符 ⇒ `[28] NRPERM`(读缺 R) / `[29] NWPERM`(写缺 W) / `[30] NXPERM`(取指缺 X)；
   - A/D 回写失败 ⇒ `[32] ADWBFAIL`（替换时失败与 `clean`/`flush` 失败同一位）；
   - **命中路径与步进路径同表**（命中不重读 PTE，但检查项相同 ⇒ 子原因也必须相同）。
2. **其它 cause 高位必须为 0**（`ADR-0056 D2`）：`CFXTRAP`/`CFXREG`/`CFXESC`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN`/`RASOF`/`RASUF` 的 `[63:16]` 全 0；`CFXMEM` 的非页表类按「待裁定 2」的结论落地。
3. **「不得部分完成」**：`clean`/`flush` 命中多条时，任一 PTE 回写失败 ⇒ **匹配集合一条都不改**（不写回、不删条目、不清挂起位），并在该写指令上报 `CFXMEM` + `ADWBFAIL`，`cause_info` = 失败那条 PTE 的物理地址（`DADAO-12 §4.5`）。落地方式二选一并在完成区写明理由：
   - **A 补偿事务**（推荐，因为「PA 是否可写」在 QEMU 里不能直接预检）：先记录每条命中条目的 `(pte_pa, 原 PTE 值)` 日志，按序回写；任一条失败 ⇒ 用日志把**已写**的条目写回原值，再报错；全部成功后才执行删除（`flush`）；
   - **B 预检后提交**：若 QEMU 侧存在可靠的「该 PA 可写」判据（如 `memory_region` 的读写属性查询），先全量预检再写。
   - `cause_info` 的取值不变（失败那条 PTE 的物理地址），与 A/B 选型无关。
4. **逐条对齐契约**（现有实现逐项核对，不一致就改）：fill 只在步进成功且全部检查通过后；缺页/权限失败不填条目、不动 A/D；`invalid` 不回写；`clean` 回写保条目；`flush` 回写后删除；范围三档（`all` 忽略 start/size；`VA` 只看起始地址所在页；`range` 与 `[start,start+size)` 相交；`scope=11` 或 `range && size=0` ⇒ `CFXREG`）；`none` 无条件 no-op（不校验 scope/size）；`ASID_ANY=0` 只处理 `G=0` 且 ASID 匹配者、**不碰** `G=1`；`ASID_ANY=1` 含 `G=1`；写 `PTBR`/`ASID`/`ptw_enable=1` **不**清 TLB。

## 增补要求（`m14-qemu-006` 复核的跨任务耦合，2026-11-16）

**5 个既有 `CFXMEM` oracle 断言 `cause_id` 的「全宽」**（`docs`/`tests` 侧见 `tools/testcases/arch/{049t,integ039t,integ040t,integ042t}` 与 `integ048t` 的 `cause_id` 断言）。本任务一旦开始填子原因 wyde（`cause_id[63:48]`），这些**精确等于 `1<<1`** 的断言会立刻红。

处置（本任务内一并改）：

- 把这 5 处改为「**低 16 位 == `1<<1`（掩码比较）** + 期望的子原因位」；子原因位按各例的真实情形给（`NONPTW`/缺失类/`ADWBFAIL`），**从 spec 派生、不读实现输出**；
- 每处注明「原为全宽相等 ⇒ 改为掩码 + 子原因」，并在完成区列表。

## 增补要求（`m14-linux-011` 复核 F6，2026-11-16）

- **`tlb_control` 的 A/D 回写失败必须「条目级」不得部分完成**：现状 `dadao_tlb_control_exec` 遇 A/D 回写失败即 `return`，而 `contract-tlb` TLB-37 要求「**失败条目保持原状、其余条目照常处理**」（`flush` 失败不删该条目、`clean` 失败不清挂起位）。须改为：逐条目处理、失败条目跳过并最终报 `CFXMEM`（`cause_info` = 该 PTE 物理地址、子原因 `ADWBFAIL[56]`），其它条目继续。
- 验收增一条：造两条目场景（一条 A/D 回写必失败、一条正常）⇒ 正常条目仍被 `clean`/`flush` 处理、失败条目原样保留、退出码/帧为 `CFXMEM`+`ADWBFAIL`。

## 验收（逐条贴真实 rc，期望值现场派生）

1. 重建：`make build-qemu` rc=0、`make install-host` rc=0（贴二进制 md5）；`make_patch` 幂等、`check-patch-tree` rc=0（一文件一补丁、无空 blob）。
2. **先红后绿**（载体 = `m14-testcases-005` 的 TLB 探针；若探针尚未落地，用运行期临时探针并在完成区说明，**临时探针不入仓**）：至少 4 路注入，逐路「注入 ⇒ 红（指出哪条断言、期望 vs 实际）⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿」：
   - ① `invalid` 里把 `ASID_ANY` 恒当 1（⇒ `ASID_ANY=0` 也动 `G` 条目）⇒ ASID/G 探针红；
   - ② `flush` 只删不回写 ⇒ A/D 回写探针红；
   - ③ 子原因不置位（只填大类）⇒ 子原因探针红（逐位）；
   - ④ 命中路径改为重读 PTE ⇒ 「命中不重读」探针红；
   - ⑤ `CFXREG` 分支给 `cause_id` 高位带上残留（比如复用上一次的子原因）⇒ 「其它 cause 高位为 0」断言红；
   - ⑥ 回写失败改为「已处理的条目保留处理结果」（回到逐条语义）⇒ 「不得部分完成」断言红。
3. **断言清单必须逐条可达 FAIL**（每条注明来源章节）：上列目标 1–4 的每一项各至少一条；`CFXMEM`/`CFXPERM` 的 `cause_info`：访问类 = 访存地址、`ADWBFAIL` = PTE 物理地址（两条分别断言，禁共用一条）。
4. **不回归**：`make check-arch-smoke` rc=0、`make check-arch` rc=0（探针登记后）；`check-linux-k0`、`check-linux-k1`（`check-linux-k2` 若已落地）rc=0。
5. 完成区 ≤30 行、无运行期路径（不写临时目录/构建树具体路径）；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；动手前 `git rev-parse --show-toplevel` 自证等于本 worktree；禁改主工作树。
2. **只改** `components/qemu/**`（`patches/target/dadao/{helper.c,cpu.h,translate.c}.patch`、`changelog.md` 及按 `docs/Process-01` 生成的补丁树）+ 本任务书；**不改** `tests/**`（探针归 `m14-testcases-005`）、`components/linux/**`、`tools/linux/**`、`spec/**`、`.tao/contracts/**`。
3. 不提交 git；注入还原一律 `cp` + md5（禁 `git checkout/restore/stash`），注入中途失败也要还原并重建。
4. 重建前申报「重建 QEMU，预计 N 分钟」；`JOBS=32`；禁边构建边跑批。
5. 期望值**现场派生**：位号从 `contract-see §6.1`（或 `ADR-0056 D3`）解析，页大小 64 KiB 从 `spec/DADAO-12 §2.2.2` 派生；禁写死总断言条数。

## 跨任务顺序风险（必须处理，否则整机门控会红）

QEMU 一旦开始填 `cause_id[63:48]/[47:32]（wyde3/wyde2）`，**内核侧的 cause 名表会立刻失配**：`arch/dadao/kernel/traps.c` 的 `dadao_trap_handler()` 用 `dadao_cause_name(cause)` 做**整值**查表，查不到就 `dadao_die()`（`unknown cause` 属异常终止）。于是每一次页表故障都会变成「未知原因终止」，`check-linux-k0/-k1/-k2` 全红。

⇒ 处置（两件必须同批落地，顺序写在下面）：
- **内核侧**（归 `m14-linux-012`）：入口先 `cause_id[15:0]` 取大类查表、`[63:48]/[47:32]` 单独解析；未知**高位**不等于未知 cause（大类在表内即可），未列出的高位组合才终止。
- **本任务**侧：在「内核侧掩码」尚未落地前，`check-linux-k0/-k1/-k2` 的不回归**只能用「子原因位注入为 0」的 QEMU 构建取证**，并在完成区写明「整机回归待 `m14-linux-012` 同批落地后由该任务/`m14-linux-015` 覆盖」；**不得**把整机回归红当成 QEMU 侧的问题忽视，也不得据此改动内核（越界）。

## 待裁定

1. **「不得部分完成」的粒度**：命令级原子（本任务默认：全程失败 ⇒ 一条都不改）vs 条目级（`ADR-0041 D3.2` 现文只保证失败条目保留）。建议命令级（用户原话「不得部分完成」）；代价是每条命令多一趟记账/补偿，且 `flush` 的失败点从「第 N 条」变成「命令」。**须由主会话确认，并在 `m14-spec-006` 的契约正文里写清**（否则实现与契约不同步）。
2. **`CFXMEM` 非页表类子原因**：段映射/未实现 cfx 的普通访存、`cfx_pmem` SRAM 越界这类 `CFXMEM` 没有 `ADR-0056 D3` 的位号。建议：这类 `CFXMEM` 的 `[63:48]/[47:32] = 0`，并把 `ADR-0056 D2` 的 one-hot 表述收窄为「页表类 `CFXMEM`/`CFXPERM` 恰一位，非页表类 `CFXMEM` 为 0」；替代方案是给它们造一位（18 位（wyde2/wyde3 分段）已满，需扩到 `[33]` 并改 `D2` 的保留区说法）。**建议前者**，须与 `m14-spec-006` 同步。
3. **开工前置**：若 `m14-spec-006` 在派单时仍未落地，是否允许以 `ADR-0041`+`ADR-0056` 为临时依据先行编码、`spec-006` 落地后对账？`ADR-0052 D6` 的「先定义后实现」默认**不允许**；本任务据此按「等 `spec-006`」排期。

## 审阅记录

（待填）
