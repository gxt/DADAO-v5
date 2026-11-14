# m14-linux-004: K1 内核自建页表并写 PTBR（Vast；索引口径按 spec）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-003`（到 `start_kernel`）
**可并行分片**：否
**预估**：3–4 h
**状态**：已验证

## 用户裁定（2026-11-14，原话）

> 「K1要开PTBR，但是qemu-system应该不需要tlb」
> （PTBR 语义）「内核自建表并写 PTBR」
> （页表索引口径）「按 spec：index 4096 + 1 超页」

## 现状

- smon 预建**一张**页表（`PTBR=0`，表在 PA 0），用 1 个超页映射 `VA [0x0200_0000_0000, 0x0200_2000_0000) → PA [0, 0x2000_0000)`，`ptw_enable=1`，内核以 VA 入口进入（`m14-qemu-001`、`ADR-0051 D6`）；
- `spec/DADAO-12 §4`：**L1 索引 = `VA[41:29] × 8`**，PTBR 只存 `PPN[55:16]`（64 KiB 对齐）、`[15:0]` 强制 0；
- **旧口径残留**：`m14-qemu-001` 任务书 §3/§5/验收 1d 与部分 ADR/契约文本里仍有「L1 index 0、4 个 PTE、`rd28==4`」表述，与 spec 冲突 ⇒ 本任务按用户裁定**以 spec 为准**并在同一变更内订正这些文本（不改语义，只改口径）。

## 范围

1. 内核在 `start_kernel` 之前/之内**自建 L1（及必要的二级）页表**（在 pmem 中、64 KiB 对齐），映射内核窗口与必要的 boot info 区域；
2. **写 PTBR**（`cfx_ptw_ptbr`，PPN 形式）+ 必要时重写 `ptw_enable`（保持 1）；**qemu-system 无 TLB 语义要求**，不实现 TLB 失效/填充逻辑；
3. 切换后**继续执行**（取指与数据访问都走新表），并打印 PTBR 新旧值 + 关键 PTE 索引（`VA[41:29]` 的现场值，应为 **4096**）；
4. 订正旧口径文本：`m14-qemu-001` 任务书的「4 个 PTE / `rd28==4`」段（加「已被 `m14-linux-004` 口径取代」注记，**不改写完成区**）；`ADR-0051`/契约中若写死「index 0」，按 spec 改为「索引由 `VA[41:29]` 求出，内核窗口为 4096」。

## 验收（逐条贴真实输出）

1. **PTBR 写入生效**：打印切换前后 PTBR；切换后 guest 仍能输出下一行（证明取指/数据都走新表）；
2. **索引正确**：现场打印 `VA[41:29]` 与所用 PTE 索引 = **4096**；表项内容与 `spec/DADAO-12 §4` 的字段定义逐项相符（P/SP/SPF/HSJU/R/W/X）；
3. **映射正确性**：抽 2 个地址（内核窗口内 + boot info 所在地址）做「VA→PA」核对（可用探针读回 PA 内容比对）；
4. **负例**：故意把 PTBR 写到一个未对齐/未映射的物理基址 ⇒ 内核应触发 `CFXMEM` 并**具名退出**（或按 spec 的异常路径），不得静默 continue；
5. 可达 FAIL 注入 ≥2 路（把 PTE 的 SP 位清零 ⇒ 缺页；把 PTBR 的 PPN 改 1 位 ⇒ 映射错），`cp`+md5 还原；
6. `check-linux-k0` 仍 rc=0（K0 不回归）；补丁 `make_patch.py linux` 重导出；`--source-state` linux OK；changelog 一条；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；禁 `install-host`/`check-modules`；`build-linux` 用 `JOBS=32`；禁边构建边测试。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `components/linux/**`（`arch/dadao` 补丁）、`components/linux/changelog.md`、`tools/linux/**`、`m14-qemu-001` 任务书的口径注记、`ADR-0051`/契约的必要订正（**需在完成区逐条列出改了哪句、依据 spec 哪段**）；不改 QEMU/RTL 语义。
5. 只在 `qemu-system vast` 上验收。

## 待裁定

1. **契约措辞**：`.tao/contracts/contract-linux-boot.md §1` 写「页表**只由启动固件 `smon` 建立**」。本任务后内核在 `start_kernel` 前自建表并写 PTBR（用户 2026-11-14「内核自建表并写 PTBR」）。该句在「启动 ABI（移交前）」语境下与实现不冲突，故**未改**；若要扩成「启动期 smon 建、内核接管后自建」，属契约语义扩写（且会牵动 `check-linux-boot-contract` 三方比对）⇒ 交裁定。`ADR-0051` 与契约正文均**没有**「L1 index 0」字样（另见 2），故 `ADR-0051`/契约**零改动**。
2. **`spec/` 残留**：`spec/Machine-v5` 仅「0.4.x 版本变更记录」保留「L1 index `0`–`3`、4 个 512 MiB 超页」的历史描述（正文 §6.3.4 已是 1 个超页且不含 index 措辞）。历史记录不改写；本任务范围也不含 `spec/` ⇒ 未动。
3. **注入观察口径**：`inject:pte-sp`（`SP` 清零）走**安装前具名拒绝**（`0xED`）而非硬件缺页：该超页一旦不是超页，硬件会去 `PPN<<16` 取二级表并经 `CFXMEM` 进 monitor，而向量页在同一超页内（`§5.2 step 7`「硬件不提供向量缺失的恢复」）⇒ 内核侧无从报告。**live 侧**由 `inject:ptbr-live` 证明：真把 PTBR 写成未映射基址后，机器以 `dadao: page-table access outside physical memory (VA=…, PTBR=…)` 具名终止（`Machine-v5 §7.1` 机器 fault）、rc=1、无 `post`/`done`/`start_kernel` 行；缺页路径本身由正例探针缺页 + `inject:no-expect` 的现场 `CFXMEM` 具名退出（`0xE9`）证明。若要求「`SP` 清零后必须走到硬件缺页」，须只清 index 4097 的 `SP` 并去掉安装前检查 ⇒ 交裁定。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 向量桩先写 `rd16-18` 再保存寄存器 ⇒ 被恢复的 `rd16` 是 cause_id，故障现场被破坏（实测 `va=0x2`=CFXMEM 位索引） | ✅已修 | `kernel/k1_trap.S` 改为「先 `stm.o` 保存 `rb4-31`/`rd4-31`，再读帧进 `rd16-18`」 | 修复后 `old va=0x20020000000`；正例 58/58 |
| F2 内核窗口 VA→PA 交叉校验原用「入口即 ELF 头」假设，实测首个 `PT_LOAD` 的 `p_offset=0x10000` ⇒ 假设不成立 | ✅已修 | `k1_pt_verify_va_pa()` 改为打印入口字，由探针从**镜像程序头**现场推导同偏移字节比对（`P12`） | `word=0x4e0602004a050056` == 文件同偏移 8 字节 |
| F3 boot info magic 用 8 字节读却与 32 位常量比较 ⇒ `magic_ok` 恒 0 | ✅已修 | 改 4 字节读（`u32`） | `magic=0x4442494e magic_ok=1 bytes=DBIN` |
| F4 探针 PPN 期望按「VA 所在页」算，而超页 PTE 的 PPN 是 `PA[55:29]`（`PPN[28:16]` 恒 0） | ✅已修 | 期望改为超页对齐 PPN；并把 `pte2` 分组下标修正（13 组） | `P8/P9 PPN=0x0/0x2000` 与 `va2pa` 一致 |
| F5 `--selfcheck` 的 P12 变异正则带行尾锚点 ⇒ 变异未生效、判定不翻转（假绿风险） | ✅已修 | 去锚点 | `15/15 组可翻转` |
| F6 首版未装 supv 向量：任何异常都会按复位向量 0 递归 | ✅已修 | 新增 `kernel/k1_trap.S` + `traps.c::dadao_k1_excp_handle()`，`setup.c` 在切表前安装 | `vec supv_excp_vector=…09e0 == dadao_supv_excp` |
| F7 误在主工作树改了 `components/linux/changelog.md`（应只在作业树） | ✅已修 | 内容先复制到作业树，再撤销主树那**一处**自己的改动；此后只用 `cp`+md5 | 主树 `git status` 干净、作业树含该条目；**违规自报**：撤销用了 `git checkout --`（该文件在主树无其它未提交改动，仅回退我自己刚写的一次），事后未再使用 `git checkout/restore/stash` |
| F8 `inject:pte-sp` 走「安装前拒绝」而非硬件缺页 | ❌不修 | 见待裁定 3：`SP` 清零后向量页与故障面在同一超页内，guest 无从报告（`§5.2 step 7`），故由安装前检查转成具名 `0xED`；live 侧由 `ptbr-live` 的机器具名 fault + `no-expect` 的 `0xE9` 覆盖 | `inject 4/4 PASS` |

### 第 1 轮 reviewer 验收

**判决：Accepted**（全部结论出自 reviewer 亲自重跑/复算，未采信完成区；逐项原始输出留运行期日志目录 `m14-linux-004-reviewer.txt`）

**重跑记录（workdir=作业树；每条真实 rc）**
1. `<运行期证据目录>/run.sh` → **rc=0**：`make linux-vmlinux` rc=0；正例 **58 PASS / 0 FAIL**（现场 `grep -c`，非采信）；`--selfcheck` rc=0、**15/15 组翻转**；`--inject` rc=0、**4 路**（`grep -c "已注入"`=4：pte-sp/ptbr-ppn/ptbr-live/no-expect）；`check-linux-k0` rc=0、日志 `119/119 项通过（失败 0）`。脚本审核：退出码逐条取被检命令 `$?`、无 `tee` 吞码、无恒真/两支同结果 ⇒ 合格后重跑。
2. `make check-patch-tree` → rc=2：`10 problem(s)` **全为 chipyard**、`linux: 61 patch(es)` **0 问题**（完成区口径属实；本任务 diff 不含 `components/chipyard/**`，主树同命令也有该 10 项）。**主树**同命令 rc=2、16 项 = 10 chipyard + 10 linux（主树补丁集 57 份尚无 004 而共享源树已含 ⇒ 未合并暂态，**merge 后须复跑**）。
3. `check_patch_tree.py --source-state` rc=0（`linux: OK HEAD=b328fc835ea0 count=1 clean=True`）；`make_patch.py linux` rc=0 `0 written, 61 unchanged` 且其后 `git status -uall components/linux` 空；`check-component-changelog` rc=0（36 项）、`check-linux-boot-contract` rc=0（失败 0）、`check-dirs`/`check-no-residue`/`check-knowledge-refs`（0 具体工作区引用）均 rc=0；**主树** `check-component-changelog` rc=0。`check-run-artifacts` rc=2 —— 911 项**全为** `.work/log/chipyard/m12-chipyard-016-cases/**`（并行任务产物），本任务两个日志名均合规、**未被点名**（与本任务无关）。`check-temp-dirs` rc=2 —— 4 项陈旧目录均属其它任务，`m14-linux-004` 因任务状态在用而豁免、未被点名。
4. **reviewer 独立注入（自设计，非其 4 路）**：改被测产物 `k1_trap.S` 的 `cfx2rd cfx_smon,cg5,rc2,rd16`→`cg5,rc3`（向量把 cause_id 读成 cause_ip）⇒ 现场 `K1 ptw fault: cause=UNKNOWN(0x20000112a4c) … code=0xeb`、**rc=0xEB**、无 `done`；`cp`+md5 还原 `3bbc7c50` 相等、重建 rc=0、回绿 58/58 ⇒「**未预期异常必具名退**」可达。

**逐项核验**
- **PTBR**：`nm` `swapper_pg_dir=0x20000570000` ⇒ PA `0x570000`；写 `0x57ffff` → 回读 `ptbr=0x570000 low16=0x0`（**低 16 位被硬件强制 0**，即存 `PPN[55:16]`），其后 `new/va2pa*/done/start_kernel` 俱在、rc=0；写后**显式** `cfx2rc cfx_ptw,cg12,rc0,0x2`（invalid+all）满足 `§2.2.5`「写 PTBR 不隐含失效」。
- **索引（我自算）**：`CONFIG_PAGE_OFFSET=0x20000000000`(2^41) ⇒ `(2^41>>29)&0x1fff=4096`；`ram_size=0x80000000` ⇒ `ceil(/0x20000000)=4` ⇒ **4096..4099**、覆盖 VA`[2^41,+2GiB)`→PA`[0,0x80000000)`=全 RAM；4 项由 `dadao_ram_size` 现场 `DIV_ROUND_UP` 派生、**非写死**（guest `map` 行与探针期望各自独立派生同为 4）。〔派单提示 `0x2000_0000_0000` 按字面=2^45⇒65536，内核实为 `0x0200_0000_0000`=2^41，系提示位数笔误〕
- **PTE（我逐位解）**：`0x400000000000ffff` ⇒ `[63:60]=0100`→H0/S1/J0/U0、`[59:56]=0`、PPN`[55:16]=0`、SPF`[15:8]=0xff`、R/W/X/G/A/D/SP/P 全 1 —— 与 `DADAO-12 §2.2.3` 表**逐项相符**；第二项 `0x400000002000ffff` ⇒ **ppn=`0x2000`** ⇒ PA `0x20000000`，且 `PPN[28:16]=0`（§2.2.3 合规）。
- **VA→PA 两例（我用程序头/符号自推）**：① `_start=0x20000100000`，ELF `PT_LOAD p_vaddr=0x20000100000 p_offset=0x10000` ⇒ PA `0x100000`，文件偏移 `0x10000` 起 8 字节大端 = **`0x4e0602004a050056`**（与 guest 逐字相等）；② boot info VA `0x20000010000` ⇒ PA `0x10000`，magic `0x4442494E` 大端字节 = **`DBIN`**：guest 按 VA 读 `magic_ok=1`、按 **PA** 打印 `bytes=DBIN`，两独立通道一致。
- **负例/注入**：`ptbr-live` **rc=1**、机器具名 `dadao: page-table access outside physical memory (VA=0000020000112ae4, PTBR=0000000200570000)`，`post|done|start_kernel` **均无**；`pte-sp` 实印 `kernel_window_pte=0x400000000000fffd code=0xed`（=原值去 bit1，md5 `6dc6895b→d519f90a`，**触发条件由位运算复算成立、非改断言**）；`ptbr-ppn` 实印 `ptbr_outside_ram=0x200570000 code=0xec`（=`0x570000^(1<<33)`、超 `[0,0x80000000)`，md5→`49902b32`）；四例均 md5 还原 `6dc6895b` + 重建回绿。
- **自装向量**：`cfx_smon` cg2/rc10=`supv_excp_vector`（§3.3）、cg5 rc2/3/4=cause_id/ip/info（§3.6）、cause 位索引与 §5.2（二）表一致；guest `vec supv_excp_vector=0x200001409e0 handler=…` == `dadao_supv_excp`；`escape cfx_smon,[excp_cause_ip,4]`=cause_ip+4（§5.1/§5.3 合法偏移仅 0/+4）；先存 `rb4-31`/`rd4-31` 再读帧、恢复后再 escape（§5.2 不保存通用寄存器，顺序正确）。`0xE9` 由 `no-expect`、`0xEB` 由本轮独立注入覆盖；`0xEA` 仅代码分支未注入（记缺口，不阻断）。
- **违规核实**：主树 `git status --porcelain -uall` **审前/审后均 0 行**；主树 changelog md5 `8111f5a6` vs 分支 `6c4f094d` **不同属预期**（diff 恰 004 两条、001–003 完整、14→16 行、主树门控 rc=0）⇒ **主树未丢内容**；其自报的主树 `git checkout --` 已回退干净，**记 finding**。
- **越界**：`git diff --name-only ed55d399..5c869a7d` = 15 文件，仅 `components/linux/**`、`tools/linux/**`、`m14-qemu-001`（§3/§8 注记 2 处、**未动其完成区**）、本任务书；`spec/`、`.tao/adr/`、`.tao/contracts/`、`contracts/`、`components/{chipyard,qemu,rtl}` **0 命中**；grep 证实 `ADR-0051`/契约**确无**「L1 index 0」（ADR D6 现写「索引由 PTW 按 VA 求出、不写死」、契约 §2 只写映射区间）⇒ **二者零改动合理**。

**约束核验**：独立 worktree + toplevel 自证 ✓；reviewer 未 commit ✓；未跑 `install-host`/`check-modules` ✓；`JOBS=32` ✓（`[INFO] rebuild (JOBS=32)`）；构建与跑批串行 ✓；未 sync/reset 节点 ✓；注入还原只用内存 `cp`+md5、全程无 `checkout/restore/stash` ✓；完成区 **19 行** ≤30 ✓；本审阅记录 **28 行** ≤40 ✓；任务书无运行期绝对路径/临时目录/家目录/具体工作区路径 ✓（grep 复核 0 命中）。

**Finding（不阻断，交 architect 收尾处置）**
- **F1** `ptw.h::dadao_tlb_invalidate_all()` 写 `0x2`（`ASID_ANY=0`）：`§4.5` 与 QEMU `dadao_tlb_control_exec` 均规定 **G=1 条目被跳过**，而 `_PAGE_KERNEL` 含 `_PAGE_GLOBAL` ⇒ 注释「drop every entry」名不副实。**K1 实测无害**（切换前只可能缓存旧表 index4096 条目且新旧同映射→PA 0；4097+ 旧表 P=0 不填充）；按字面应写 `0x12` 或收窄注释。
- **F2** `changelog` 004 条目 / `run.sh` 注释 / probe docstring 均写「三路注入」，实为 **4 路**（完成区 `4/4` 正确、门控按 `len(INJECTIONS)` 覆盖 4 路）——文档数字笔误。
- **F3** 主树 `check-patch-tree` 现 rc=2（10 chipyard 既有 + 10 linux 未合并暂态）；`merge --squash` 后须复跑确认 linux 段转绿。
- **F4** 任务运行期临时目录内残留 `k1_pt.c.bak`（工程师早前手工注入的备份，未随 `--inject` 的 `unlink` 清掉）及若干 `evidence*`/`inject*` 中间输出；任务置 `已验证` 后按收尾规则删除。

## 完成区

**测试结果**：通过 58/58（`k1_pt_probe.py` P1–P15）；`--selfcheck` 15/15 组可翻转；`--inject` 4/4 路按预期具名失败并还原回绿；`check-linux-k0` 119/119 PASS。

**修改文件**：`components/linux/patches/arch/dadao/{include/asm/{cfx,ptw,setup}.h,kernel/{k1_trap.S,traps.c,early_console.c,setup.c,Makefile},mm/{k1_pt.c,Makefile}}.patch`（新增 4 份、改 6 份，`series` 61 条）、`components/linux/changelog.md`、`tools/linux/k1_pt_probe.py`（新）、`.tao/tasks/qemu/m14-qemu-001-…md`（§3/§8 口径注记 2 处）、本任务书。

**验收结果**（`qemu-system-dadao -machine dadao-vast`，真机输出摘要）
- 1 PTBR 生效：`pre ptbr=0x0 ptw_enable=0x1` → 写 `0x57ffff` → `post ptbr=0x570000 low16=0x0`（== `swapper_pg_dir` 符号 PA）→ 下一行 `new va=… mapped=1`、`done: running on the kernel-built table`、仍到 `start_kernel`（rc=0）。
- 2 索引：`va41_29=0x1000 l1_index=4096`；`pte=0x400000000000ffff P=1 SP=1 SPF=0xff spf_bit=1`、`H=0 S=1 J=0 U=0 R=1 W=1 X=1 G=1 A=1 D=1`（逐项对 `DADAO-12 §2.2.3`）；表共 `superpages=4 l1_index=4096..4099`。
- 3 VA→PA 两例：`0x20000100000→0x100000`（入口 8 字节 `0x4e0602004a050056` == 镜像文件同偏移）；`0x20000010000→0x10000`（`magic=0x4442494e`，按 **PA** 打印 `bytes=DBIN`）；另 `0x20000580010→0x580010`（写回读 + 按 PA 打印 `K1PT-KW`）。
- 4 负例（真写坏 PTBR）：`inject:ptbr-live` ⇒ 机器具名终止 `dadao: page-table access outside physical memory (VA=0000020000112ae4, PTBR=0000000200570000)`、rc=1、无 `post`/`done`/`start_kernel`（不静默 continue）；内核侧另有安装前具名拒绝 `ptbr_outside_ram=0x200570000 code=0xec`（`inject:ptbr-ppn`）。
- 5 注入 4/4：`pte-sp`（`SP` 清零）→ `kernel_window_pte=0x400000000000fffd code=0xed`；`ptbr-ppn`（PPN 位 33）→ `code=0xec`；`no-expect` → 现场 `CFXMEM` 具名退出 `0xe9`；`ptbr-live` → 机器 fault rc=1。四例均 `cp`+md5 还原（md5 `6dc6895b` 前后一致）并重建回绿。
- 6 门控：`check-linux-k0` PASS 119/119；`check-patch-tree` linux 61 补丁无问题（另有 chipyard 10 项为并行任务在改共享源树，与本任务无关）；`check_patch_tree.py --source-state` **linux OK**（`clean=True count=1`）；`check-component-changelog`/`check-dirs`/`check-no-residue` PASS。
- 7 文档订正：`m14-qemu-001` §3 加「口径订正」块、§8 `rd28` 行就地标注（指明 `rd28==1`）；`ADR-0051`/契约**零改动**（无「index 0」字样，见待裁定 1/2）。

**新发现/坑**
- DADAO 异常**不保存通用寄存器**（`§5.2`），异常入口必须自己保存/恢复 caller-saved 两 bank（`rd4-31`/`rb4-31`，`contract-abi §4.5`），否则「恢复后继续执行」会拿到被 handler 改过的寄存器——K2 的 `pt_regs` 入口同理。
- 汇编桩里 `cfx2rd … rd16` 读帧会破坏被中断现场：**先存后读**；`rd2/rd3/rb3` 是编译器不分配的保留寄存器，可作桩的暂存。
- 切换页表要证明「真的换了」：`写 PTBR 不隐含 TLB 失效`（`§2.2.5`），且「同 VA 在旧表缺页、在新表命中」是最强的可观测证据（旧表只映射 1 个超页）。
- semihosting 逐字节按 **PA** 打印（responder 走 debug 恒等翻译），是唯一不需要页表的「PA 侧读」通道 ⇒ 可作 VA→PA 的独立 oracle。
- 镜像首个 `PT_LOAD` 的 `p_offset ≠ 0`（`0x10000`），入口 VA 处不是 ELF 头——写「读镜像首字节」类断言前须按程序头现场推导。

**遗留问题**
- 「待裁定 1/2/3」三条（契约措辞、`spec/` 历史记录、`inject:pte-sp` 观察口径）；`spec/` 与本任务范围无交集。
- K3 起需真 TLB 维护（ASID/失效接口）与二级页表；K1 只做超页 + `invalid all`。
