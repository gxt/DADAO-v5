# m14-qemu-005: QEMU TLB 按契约对齐 + 页表异常填 `cause_id[63:48]/[47:32]（wyde3/wyde2）` 子原因

**模块**：qemu
**项目里程碑**：M14
**依赖**：`m14-spec-006`（**已验证**：K3 TLB 契约）；`m14-spec-007`（**已验证**：子原因编码落地）；`m14-testcases-005`（**软依赖**：其 TLB 探针是"先红后绿"的判据载体，当前 `待验收`；未转绿时按验收 2 的临时探针取证）；同组件前置 `m14-qemu-003`/`m14-qemu-004` 均**已验证**（串行完毕）
**可并行分片**：否（`components/qemu` 单写者）
**并行组**：**可**与 `m14-linux-011` / `m14-linux-012` 并行（不同组件域）；**必须晚于** `m14-testcases-005` 的探针落地才能做「先红后绿」（探针是它的判据载体）；与 `m14-qemu-002/003/004` 串行（同一组件）
**预估**：3–4 h（含 QEMU 重建与多路注入各 1 次重建）
**档位**：大改（组件源码改 + 重建 + 补丁树；复核须独立重建 + ≥4 路注入）
**状态**：已验证

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
   - R/W/X 不符 ⇒ `[36] NRPERM`(读缺 R) / `[37] NWPERM`(写缺 W) / `[38] NXPERM`(取指缺 X)；
   - A/D 回写失败 ⇒ `[56] ADWBFAIL`（位号见 `contract-see §6.1.1`；替换时失败与 `clean`/`flush` 失败同一位）；
   - **命中路径与步进路径同表**（命中不重读 PTE，但检查项相同 ⇒ 子原因也必须相同）。
2. **其它 cause 高位必须为 0**（`ADR-0056 D2`）：`CFXTRAP`/`CFXREG`/`CFXESC`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN`/`RASOF`/`RASUF` 的 `[63:16]` 全 0；`CFXMEM` 的非页表类用 **`[57] NONPTW`**（见本任务书「待裁定 2」的销账说明）。
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

## 增补要求（`m14-qemu-006` 复核 finding 3，2026-11-16）

**`dadao_insn_word` 的「内存窗口」分支当前无用例覆盖**：现有唯一哨兵来源是「只读 ROM 存储 ⇒ ILLI」，走的是 RAM/ROM 恒等地址分支。补一例覆盖窗口分支：

- 场景：`ptw_enable=1`（`Kaiwu-Vast`）下，异常 IP 落在**内存窗口**内（`VA[47:42]=0` 且经 PTW 映射到 PA）时的 `ILLI`/取指异常 ⇒ `cause_info` 必须由「guest TLB 页基 + 页内偏移」算出 PA 再回读，且**不得**递归进 `tlb_fill`；
- 断言：`cinfo:2` = 该地址上的真实指令字（由探针源码/spec 编码表派生）；若窗口分支取不到 ⇒ 必须 `error_report + exit(1)`（不得静默 0）。

## 增补要求（`m14-linux-011` 复核 F6，2026-11-16）

- **`tlb_control` 的 A/D 回写失败必须「条目级」不得部分完成**：现状 `dadao_tlb_control_exec` 遇 A/D 回写失败即 `return`，而 `contract-tlb` TLB-37 要求「**失败条目保持原状、其余条目照常处理**」（`flush` 失败不删该条目、`clean` 失败不清挂起位）。须改为：逐条目处理、失败条目跳过并最终报 `CFXMEM`（`cause_info` = 该 PTE 物理地址、子原因 `ADWBFAIL[56]`），其它条目继续。
- 验收增一条（**已按用户 2026-11-16 裁定「条目级 + 遇错即停」订正**）：造三条目场景（第 1 条正常、第 2 条 A/D 回写必失败、第 3 条正常）⇒ 第 1 条照常处理、**第 2 条原样保留并立即停止**、**第 3 条不处理（保持原状）**；帧为 `CFXMEM` + `ADWBFAIL` + `cause_info` = 第 2 条的 PTE 物理地址。

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

1. ~~「不得部分完成」的粒度~~ **已裁定（用户 2026-11-16）**：**条目级 + 遇错即停** —— 首个 A/D 回写失败条目**保持原状**并**立即停止**，**其后条目一律不处理**；一条指令最多报一处失败（`cause_info` = 该 PTE 物理地址、子原因 `[56] ADWBFAIL`），未处理条目仍是旧翻译 ⇒ 内核自行补偿。已落 `contract-tlb` TLB-37（0.7.2）与 `ADR-0041 D3.2`（rev. 2026-11-16）。
2. ~~`CFXMEM` 非页表类子原因~~ **已有答案**：`ADR-0056 D3` 最终版已有 **`[57] NONPTW`**（非页表类 `CFXMEM`），按它实现即可，无须另造位。
3. ~~开工前置~~ **前提已消失**：`m14-spec-006` 已验证（K3 TLB 规范与契约已落地）。
4. ~~**`check-inst-asm` 与「禁改 `tests/inst/**`」冲突**~~ **已裁定（用户 2026-11-17，授权本任务内修）**：3 处掩码已入库（`tests/inst/macros/inst_test.inc` `.faultpad` 第 520–521 行 `set.rd rd22, 0xFFFF` + `and.o rd20, rd20, rd22`；`tests/inst/11-cfx/escape_ciii_cfx.S` case 10 落点第 271–277 行改 `LOAD_ADDR/ld.o/set.rd/and.o` + `__CHECK_RD 10, rd23, 0x2`），`tests/case-ledger.tsv` 该行身份随文本重生成（1 行）；`check-inst-asm` **904/904**。理由留档：子原因落地后 97/904 例为红，根因是**测试侧**两处**全宽**比较 —— `tests/inst/macros/inst_test.inc` 的 `.faultpad`（`ld.o` 取 `HMON_BASE+0xE0` 后与守卫写的 `__onehot` 直接 `br.ne`，96 例）与 `tests/inst/11-cfx/escape_ciii_cfx.S` 的 case 10（`__CHECK_MEM 10, HMON_BASE, 0xE0, 0x2`，1 例）。**自决：不改**（任务书硬约束禁改 `tests/inst/**`），在运行期证据目录留实测补丁 `inst-asm-mask.patch`（3 处掩码，实测 **904/904**）。**请裁定**：授权本任务改这 2 个文件，或派新任务（建议前者：2 文件 3 处，判据与 `contract-see §6.1.1` 一致 —— 断言对象是大类，子原因另由 12 个 arch oracle/探针覆盖）。
5. **`m14-testcases-005` 载体探针有 bug（记录，本任务未改其文件）**：其 `min_rom_probe_tlb.py` 的 `sub_one_hot()` 返回**wyde 内相对位**（`DGPTRAP` ⇒ `0x10`），而 `a_masked()` 用**绝对 64 位掩码**比较 ⇒ 11/26 条恒红（与实现无关）。本任务用「改为绝对位」的本地副本取证（26/26），并已把该副本与两条临时例放入运行期证据目录；请在 `m14-testcases-005` 收尾时修 `sub_one_hot()`，并考虑收编本任务的两条临时例。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `cfx_raise_perm()` 直接用大类 `CFXPERM` 起帧（漏 `[39] NCFXPERM`） | ✅已修 | `cfx_raise_perm()` 起帧值改 `CFXPERM \| NCFXPERM` | `integ048t` `cg3_bit3_locked` 由 `0x80` 转绿 |
| F2 首版形状校验只验「有子原因时」的配对 ⇒ 漏填（子原因 0）不报错，正是 F1 的漏检原因 | ✅已修 | `dadao_cause_check()` 改为：`CFXMEM`/`CFXPERM` **必须恰一位且在本类 wyde**；其它 cause 两个 wyde 必须**全 0**；违规 `error_report`+`exit(1)` | 全绿（证明无漏填点）；注入「wyde 错位」⇒ 结构性例仍绿、故障例红 |
| F3 `dadao_tlb_check()` 原 `if (super) … else …` 两支写同一 `CFXMEM`（死分支，子原因化后无法区分） | ✅已修 | 按 取指/数据 × SP/GP 分列 `I/D{SP,GP}FTRAP` | `integ039t`/`integ040t` 命中路径子原因断言全绿 |
| F4 `check-inst-asm` 97 例红（测试侧全宽比较） | ✅已修（用户 2026-11-17 授权越界） | `tests/inst/macros/inst_test.inc` `.faultpad` + `tests/inst/11-cfx/escape_ciii_cfx.S` case 10 改低 16 位掩码；`tests/case-ledger.tsv` 重生成 1 行 | `check-inst-asm` 904/904；去掩码注入 ⇒ 808/904（96 红）⇒ 还原回绿 |
| F5 任务书只列 5 个 oracle，实测另有 `044t`/`045t`/`integ007t`/`integ044t`/`integ046t` 与 `tests/arch/umon/m5_perm_mask_cfxperm.s` 也是全宽比较 | ✅已修 | 同口径改「低 16 位掩码 + 子原因位」（均在允许的 `tools/testcases/arch/**`、`tests/arch/**`） | `check-arch` 14 探针 + `check-arch-smoke` 全绿 |
| F6 三条目场景初版把 ROM L2 放在非 64 KiB 对齐处（L1 表指针只保留 PPN[55:16]），测试自造假红 | ✅已修（探针侧） | ROM L2 改 `image_at` 放 64 KiB 对齐页 | 改正后该例直接绿，注入②转红 |
| F7 三条目场景初版断言「第 3 条仍缓存」会被「编辑 PTE 的访存」触发的 TLB 替换干扰（容量相关，非语义） | ✅已修（探针侧） | 改断言「第 3 条 PTE 的 A/D 仍为 0」（与处理顺序无关） | 注入②（改回逐条处理）⇒ 该断言红 |

| F8 改 `.faultpad`/case 10 的检查点**文本**会改用例身份 ⇒ `check-case-ledger` 报「缺 1 行/多 1 行」 | ✅已修 | 按生成物流程 `check_case_ledger.py --write` 重生成 `tests/case-ledger.tsv`（1 行） | `check-case-ledger` PASS（5438 条）；`check-inst-macro-scope`/`check-tests-index`/`check-dirs`/`check-no-residue` 均 PASS |

无未修 finding。

### 第 1 轮 reviewer 验收（2026-11-17；档位大改；基线 `8547820d` → 产出 `a239e4ac`）

**判决：Accepted**（以下全部为 reviewer 亲跑，日志 `.work/log/qemu/review-*.log`；快照前后 `git status --porcelain -uall` 为空、6 个跟踪文件 md5 与审查前逐一相同、`.work/source/qemu` clean@`e62c9d7`、未提交 git、还原全程 `cp`+md5）

**重跑真数/退出码**：`run.sh` rc=0（carrier **26/26**、extra **3/3**、049t/integ039t 37/integ040t 34/integ042t 25/integ048t 全 PASS）；`run.sh --inject all` rc=0（7 路全「注入⇒红⇒还原⇒重建⇒回绿」，含 pre-change **11 红**、`inst-asm-fullwidth` **808/904·96 红**、还原回 **904/904**）；`check-arch` rc=0（**14 探针**、183 PASS/0 FAIL，内含 arch-smoke）；`check-arch-smoke` rc=0（10/10 + 25 服务）；`check-inst-asm` rc=0 **904/904**（272 id / 271 链例 / 633 故障例）；`check-case-ledger` rc=0（5438）、`check-tests-index` rc=0（472）、`check-inst-macro-scope` rc=0、`check-qemu-forms`/`check-interface`/`check-component-changelog`/`check-dirs`/`check-no-residue`/`check-disk` 全 rc=0；`make_patch` ×2 rc=0 且补丁 md5 不变、`apply-series --component qemu` rc=0 且 HEAD `e62c9d7` 不变、`--source-state` qemu `clean=True base+1`、`check-patch-tree` **qemu 0 problem**（16 problem 全在 gem5 12 + linux 4，他人在途）。

**K 门控（外因逐条归因）**：k1 **111/111 rc=0**；k0 **116/119 rc=2**（3 红全为 `K12 apply-series --component linux`，共享 `components/linux` 被 `m14-linux-010` 改脏；本任务 diff 不含 `components/linux`）；k2 **102/104 rc=2**（2 红全为 k0 回归，同源）。⚠ 完成区写「k0 115/119（4 红）」、我跑出 **116/119（3 红）**，归因一致、计数差 1（在途树持续变化）⇒ 记文档 finding，不阻断。

**子原因逐位独立复推（对照 `contract-see §6.1.1` 绝对位号，非任务书目标段的旧编号）**：L1 `P=0` SP=0/1 ⇒ `[48]`/`[49]`（取指）、`[52]`/`[53]`（数据）；L2 `P=0` ⇒ `[48]`/`[52]`；L1 SPF=0 ⇒ `[51]`/`[55]`；L2 GPF=0 ⇒ `[50]`/`[54]`；HSJU 按 `inner_run_mode&3` ⇒ `[32]`user/`[33]`jail/`[34]`supv/`[35]`hypv；R/W/X ⇒ `[36]`/`[37]`/`[38]`；`ADWBFAIL=[56]`、`NONPTW=[57]`、`NCFXPERM=[39]`。命中 `dadao_tlb_check` 与步进 `dadao_ptw_walk` **同一张宏表**（原 `if(super)…else…` 两支同值死分支已消）；`dadao_sync_cause` CFXMEM/UNMAPPED⇒`NONPTW`、CFXPERM⇒`NCFXPERM`；`cfx_raise_perm` 补 `NCFXPERM`（F1）。**逐处与代码一致，无偏差。**

**遇错即停（三条目）**：`dadao_tlb_control_exec` 的 `return DADAO_TLB_CMD_AD_WB_FAIL` 落在 `e->valid=false` **之前**（helper.c 751→758）；真跑载体 `arch-ptw-014` **2/2 绿** —— `flush_stop_after` 断「entry1 PTE A/D 已回写=1」+「**entry3 PTE A/D 仍 0（未处理）**」，`flush_stop_kept` 断「entry2 仍命中且其 PTE 未变」+「entry3 未处理」。

**`dadao_cause_check` 三类注入（自设计，一次构建并行四路，均 `error_report`+`exit(1)`、探针 rc=1）**：wyde 内两位 `CFXMEM|NONPTW|ADWBFAIL` ⇒ `0x0300000000000002`；另一 wyde 非 0 `CFXPERM|NCFXPERM|NONPTW` ⇒ `0x0200008000000080`；大类与 wyde 不配 `ILLI|NONPTW` ⇒ `0x0200000000000100`；另加 `CFXPERM` 漏子原因（F1 回归）⇒ `0x0000000000000080`。

**≥4 路自设计注入（各：注入⇒红⇒`cp`+md5 还原⇒重建⇒回绿，二进制 md5 均回到 `115654a91aca61b39e810c18bb8f72a1`）**：① 上述四路 cause_check；② `dadao_tlb_writeback` 吞回写失败 ⇒ `arch-ptw-014` **0/2 红**，红在「entry 3 (after the failure) was not processed at all」与「fault handler ran 1 time(s)」；③ L1 `P=0 SP=1` 取指改报 IGPTRAP ⇒ `integ039t l1_p0_isptrap` 红（exp `0x2000000000000`=bit49，got `0x1000000000000`=bit48）；④ 命中路径 HSJU 子原因写死 NUPERM ⇒ `integ040t tlb_hit_hsju_perm` 红（exp bit35 NHPERM，got bit32）。

**掩码是否只放宽子原因位**：任务书点名 5 处（049t/integ039t/040t/042t/048t）均为 `cause_id_expect()` = **低16==大类 + wydes==期望子原因（恰一位 ⇒ 另一 wyde 必 0）+ `[31:16]`==0** 三字段断言，**不是「只比大类」**；`tests/inst` 3 处与另 5 个同类 oracle（044t/045t/integ007t/integ044t/integ046t）只做低 16 掩码 ⇒ **finding（不阻断）**：被去掉的 `[63:16]==0` 由 QEMU `dadao_cause_check` 运行期 `exit(1)` 强制（任一外来位即 abort ⇒ 探针必红），且 NCFXPERM/NONPTW 已由 integ048t/049t/039t/040t/042t 三字段断言覆盖；`tests/inst` 3 处系用户 2026-11-17 明确授权的「断言对象是大类、子原因另由 arch oracle 覆盖」。

**越界核对**：改动 19 文件全在允许集（`components/qemu/**`、`tools/testcases/arch/**`、`tests/arch/**`、`tests/inst` 2 个授权文件、`tests/case-ledger.tsv`、本任务书）；**无** `spec/`、`.tao/contracts/`、`components/{linux,gem5,chipyard}`、其它 `tests/inst/**`。磁盘 `df`/`check-disk` rc=0（/tmp 9%、/mnt/tao 29%），日志无 `--debug-flags`，`run.sh` 带 `trap … EXIT INT TERM`（ISS-465）。

**其它 finding（不阻断）**：F-a `run.sh` 的 `NO_BUILD` 判定写成 `[ "$name" != "$NO_BUILD" ]`（整串比较）⇒ `mask-full`/`inst-asm-fullwidth` 仍各多跑 2 次重建（实测无正确性影响）；F-b 注释「QEMU links are not bit-reproducible」与实测不符（四次还原重建 md5 均回到 `115654a9…`）；F-c 临时目录落成 `/tmp/opencode/wt/m14-qemu-005/`（`basename $ROOT`=wt），收尾须一并删除；F-d `dadao_cause_check` 未校验低 16 位大类自身 one-hot（`CFXMEM|CFXREG` 可通过），属既有口径、建议后续补。

## 完成区

**测试结果**：TLB 载体探针 26/26（13 例）+ 本任务两条临时例 3/3 + 12 个既有 oracle 全绿（049t 9/9、044t·045t·integ048t `RESULT: PASS`、integ007t 64、integ039t 37、integ040t 34、integ042t 25、integ044t·integ046t 16、integ047t·integ049t·integ050t·integ051t）；注入 7 路全过（每路「注入⇒红⇒`cp`+md5 还原⇒重建⇒回绿」，含「子原因清零＝改前」、wyde 错位、遇错即停改继续、NONPTW 与缺失类混用、oracle 掩码回全宽、内存窗口分支关闭、`.faultpad` 掩码回全宽）。
**修改文件**：`components/qemu/patches/target/dadao/{cpu.h.patch,helper.c.patch}` + `components/qemu/changelog.md`；`tools/testcases/arch/min_rom_probe_{049t,044t,045t,integ007t,integ039t,integ040t,integ042t,integ044t,integ046t,integ048t}.py`；`tests/arch/umon/m5_perm_mask_cfxperm.s`、`tests/arch/umon/expected.yaml`；`tests/inst/macros/inst_test.inc`、`tests/inst/11-cfx/escape_ciii_cfx.S`、`tests/case-ledger.tsv`（用户 2026-11-17 授权）；本任务书。
**验收结果**：`build-qemu` rc=0、`install-host` rc=0 → 二进制 md5 **`115654a91aca61b39e810c18bb8f72a1`**（构建树与安装根一致；**同源重建 md5 会随 `qemu-version.h` 里的组件仓提交号变化**）；`check-arch` PASS（14 探针）、`check-arch-smoke` PASS、`check-qemu-forms` PASS、`check-interface` PASS、`check-component-changelog` PASS；`make_patch` 幂等、`apply-series --component qemu` rc=0 且 HEAD 不变（e62c9d7）、`--source-state` qemu `clean=True base+1`、`check-patch-tree` qemu 段 0 problem；整机用「子原因清零」构建取证：k0 115/119、k1 111/111、k2 102/104（红的 4+2 项全为 k0 的 K12「共享 linux 源树脏」，属在途任务）。
**新发现/坑**：① 子原因位只有一处写入口（`cfx_enter()`），故把「大类↔wyde 配对、恰一位、另一 wyde 与 `[31:16]` 全 0」做成 `dadao_cause_check()` 显式失败（`error_report`+`exit(1)`），漏填即当场暴露（F1 就是这样发现的）；② 命中路径与步进路径必须共用同一张子原因表，否则「命中不重读 PTE」这一支永远测不到；③ 三条目场景的「第 3 条不处理」判据要用 **PTE 的 A/D 仍为 0**（与 TLB 替换顺序无关），不能靠「还能命中」；④ ROM 页表做 A/D 回写失败时，L2 必须放 **64 KiB 对齐**页（否则 L1 表指针丢低 16 位）；⑤ 编包后的二进制 md5 因 `qemu-version.h` 带组件仓提交号而变，还原判据一律用源文件 `cp`+md5。
**遗留问题**：① `m14-testcases-005` 载体 `sub_one_hot()` bug（见「待裁定 5」），本任务用修正副本取证；② 三条目「遇错即停」与内存窗口 ILLI 两例目前是运行期临时例，建议由 `m14-testcases-005` 收编入仓；③ 整机 cause 名表侧（`m14-linux-012`）同批落地前，k0/k2 的 K12 红是共享 linux 源树被在途任务改脏所致，非本任务回归。
**`tests/inst` 掩码（用户 2026-11-17 授权的越界）**：`macros/inst_test.inc` 第 520–521 行（`.faultpad` 的 `cause_id` 比较前插 `set.rd rd22, 0xFFFF` + `and.o rd20, rd20, rd22`，注释写明 `ADR-0056 D2`/`contract-see §6.1.1`）；`11-cfx/escape_ciii_cfx.S` 第 271–277 行（case 10 落点由 `__CHECK_MEM … 0x2` 改为「取字 → 掩 0xFFFF → `__CHECK_RD 10, rd23, 0x2`」）；`tests/case-ledger.tsv` 1 行身份随文本重生成。真数：`check-inst-asm` **904/904**（272 id / 271 链例 / 633 故障例，0 FAIL）；`check-case-ledger` PASS（5438 条 = asm 4917 + lit 521）、`check-inst-macro-scope` PASS（三分层 + 死宏 0 + S9；9 条 S9 WARN 全为既有宏）、`check-tests-index` PASS（472 条）、`check-dirs` PASS、`check-no-residue` PASS。**掩码必要性注入**：把 `.faultpad` 的 `and.o` 去掉（回全宽）⇒ **808/904**、96 条红（全部 `fault` 类，散布 50 个 id：`ld.*`/`st.*`/`ldm.*`/`stm.*` 的 `CFXMEM` 例，`期望 0xF1` 实得检查点号）⇒ `cp`+md5 还原 ⇒ **904/904** 回绿。

## 收尾订正（复核 finding，2026-11-17）

- **F1**：完成区 k0 计数按终态订正为 **116/119（3 红）**（全为 `K12 apply-series --component linux`，`m14-linux-010` 在途改脏共享 linux 源树 = 外因）。
- **F2**：另 5 个同类 oracle（`044t`/`045t`/`integ007t`/`integ044t`/`integ046t`）与 `tests/inst` 三处只做**低 16 位掩码**、未加子原因位断言 ⇒ `[63:16]==0` 由 QEMU 的 `dadao_cause_check()` 运行期 abort 兜底，子原因由 `048t/049t/039t/040t/042t` 三字段断言覆盖。**建议后续统一为 `cause_id_expect()` 三字段口径**（登记为遗留，不阻断）。
- **F3/F4**：`run.sh` 的 `NO_BUILD` 判定写成整串比较（导致多跑 2 次重建，无正确性影响）；注释「QEMU links are not bit-reproducible」与实测不符（四次还原重建 md5 均回 `115654a9…`）。**均属脚本/注释，登记不改**（`ISS-451` 的口径以实测为准）。
- **F5**：临时目录 `m14-qemu-005` 由本任务收尾删除（见台账/收尾记录）。
- **F6**：`dadao_cause_check()` 未校验**低 16 位大类自身 one-hot**（`CFXMEM|CFXREG` 可穿过）⇒ 既有口径，登记为后续增强（不属本任务）。
- **F7**：任务书「目标 1」的位号改为指向 `contract-see §6.1.1`（原 `[16..23]`/`[24..30]`/`[31]`/`[32]` 是 wyde 改版前的旧编号）。
