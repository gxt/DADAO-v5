# INTEG-040t: Step 3 落地（TLB、G、A/D、PTWERR）

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0039（地址空间）、ADR-0040（PTE，Accepted）、ADR-0041（TLB，Accepted）、`INTEG-039t`（Step 2）
**状态**：已验证

## 背景

Step 2 已落地页表步进/HSJU/SPF/GPF/RWX，但还没有 TLB；`cfx_tlb` 仍是旧寄存器块（cfx5），PTE bit4 仍写“保留”，A/D 不更新。ADR-0041 已 Accepted：`cfx_tlb` 合并进 `cfx_ptw`，ASID 16 位，cg12 正交失效接口，A/D dirty 回写，`PTWERR=1<<7`，PTE bit4=G。

## 目标

1. **spec**
   - `DADAO-12` §2.2.5/§4.6：删除 `cfx_tlb`/cfx5/`tlb_enable`/`tlb_exist`；TLB 并入 `cfx_ptw`。
   - PTE flags bit4 从“保留”改为 **G**；叶子 G=1 全局，next-level G 忽略/写 0。
   - cg12 接口：rc0 `tlb_control`（op `00=none/01=clean/10=invalid/11=flush`，addr_scope `00=all/01=VA/10=range/11=reserved`，bit4 `ASID_ANY`），rc1 ASID[15:0]，rc2 start，rc3 size。
   - 正交匹配 `(ASID match) AND (address match)`；`all` 忽略 start/size，`VA` 只看 start，`range` 用 start/size（size=0→CFXREG），scope=11→CFXREG。
   - G 失效：`asid_any=1` 包含 G；`asid_any=0` 跳过 G。
   - A/D：fill 不置 dirty；读/取指置 A，写置 A/D；缺页/权限失败不更新；CLEAN 保留、FLUSH 写回后删、INVALID 不写回删；FLUSH 写回失败保留条目。
   - `PTWERR=1<<7`：A/D 回写失败进 `cfx_ptw`，不可屏蔽，`cause_info=PTE PA`。
   - 同步 contracts/spec 引用、锁 sha/changelog。
2. **QEMU**
   - 实现 TLB（可简化结构，行为必须完整）：ASID/G 匹配、命中/填充、权限同序、A/D dirty、CLEAN/FLUSH/INVALID、PTWERR。
   - 页表步进仍是唯一 fill 来源；TLB 命中不重读 PTE；没有 `tlb_enable`；写 PTBR/ASID 不自动 flush。
   - 不实现 DMA、启动、cfx 访问权限。
3. **测试**
   - ASID 隔离、G 跨 ASID 命中、指定 ASID 不失效 G、ASID_ANY 失效 G；
   - 命中权限优先级、fill 只接受合法 PTE；
   - A/D：fill 不置 dirty、读置 A、写置 A/D、CLEAN/FLUSH/INVALID、回写原子 OR、PTWERR；
   - op/scope/asid 组合、VA/range、size=0/scope=11 的 CFXREG；
   - 回归 Step 1/2 探针、页表步进、`ptw_enable=0` CFXMEM。

## 验收

- `make check`、`make check-modules`、`make check-arch-smoke`、`make check-lit`、`make check-arch`、`check-spec-readonly`、`check-spec-changelog`、`check-patch-tree`、`check-source-state` 全 rc=0。
- 新探针/测试全绿；证据 `.work/evidence/<任务号>/run.sh` 注入→FAIL→cp+md5 还原→PASS。
- 不改 DMA/启动/cfx 权限/Linux 划分；不跑 `check-full`/夜跑。
- 完成区 ≤30 行；任务书与 `milestones.md` 置 `待验收`；临时目录 `/tmp/opencode/INTEG-040t/`。

## 约束

- 只做 Step 3；G 和 PTWERR 必须一起收口，不能只做 TLB。
- 不提交、不 push；重建先申报；失败保留现场。
- 若 QEMU 实现简化导致某些行为无法验证，必须在完成区明确 BLOCKED，不能假绿。

## 完成区

**状态**：已验证

**测试结果**：新探针 `min_rom_probe_integ040t.py` 34/34；回归 044t/045t/049t/integ038t/integ039t 全 PASS；证据 49/49（四次注入→FAIL→cp+md5 还原→PASS）。

**修改文件**：
- spec：`DADAO-12`（§1 cfxha5 未分配；§2.2.1/2.2.2 TLB 查找；§2.2.3/2.2.4 bit4=G；§2.2.5 A/D+G；§4.5 增 cg12+PTWERR，删 §4.6 cfx_tlb 并重编号 4.7–4.13→4.6–4.12；§5.2；附录）、`DADAO-22`（§4 删除委托、§5 改写为 cfx_ptw TLB 维护、附录）、`DADAO-11`（§3 单 PTBR+ASID 示例、0.9.4-rc）、`DADAO-21`（版本互锁 0.9.4-rc）、`Machine-01`（§1.2/§3/附录）、`spec/README.md`（TLB 功能并入 cfx_ptw）、`manifests/spec-readonly.lock.toml`（5 册 sha）。
- contracts：`contracts/cfx-aliases.txt`、`.tao/contracts/contract-cfx-aliases.md`（重生成：删 cfx_tlb、增 cfx_ptw_tlb_*）、`contract-see.md`（TLB/A-D/PTWERR/G、测试机范围）、`tools/spec/gen_cfx_aliases.py`（未分配槽位不出别名）。
- QEMU：`.work/source/qemu/target/dadao/{cpu.h,cpu.c,helper.c}` + 三份导出补丁；`components/qemu/changelog.md`。
- 测试：新增 `tools/testcases/arch/min_rom_probe_integ040t.py`（34 例）；改 `044t` 用例描述、`tests/arch/umon/m5_perm_unimpl_cfxreg.s`（cfx_tlb→cfx_hart）、`tests/arch/umon/m5_perm_reserved_illi.s`（仅注释同步）、`expected.yaml`、两份 README；`Makefile` 的 `ARCH_CFX_PROBES`。
- 台账/证据：`milestones.md`、本任务书、`.work/evidence/INTEG-040t/run.sh`。

**验收结果**（真实输出）：`make check` rc=0（L1 PASS）；`make check-modules` rc=0（L2 PASS）；`make check-arch` rc=0（含 smoke；integ039t 37/37、integ040t 34/34）；`make check-lit` rc=0（159/159）；`check-spec-readonly`（21 册）/`check-spec-changelog`/`check-patch-tree`（205 补丁）/`check-source-state`/`check-cfx-aliases` 全 rc=0；证据 `RESULT: PASS=49 FAIL=0`（EXIT=0，四次注入各自转红后 cp+md5 还原回绿）。

**新发现/坑**：
- QEMU 自有 translation cache 按 (VA, mmu_idx) 缓存**权限结果**，不随 guest HSJU/ASID 变化 ⇒ 必须在 PTBR/ptw_enable/ASID 写、条目删除、run-mode 切换（`cfx_enter`/`escape`）时 `tlb_flush`，否则 S 模式填充的页在 H 模式被直接复用（探针 `tlb_hit_hsju_perm` 首轮即暴露）。
- 「首次写要回到 `tlb_fill` 才能置 D」：只在条目 `A_local && D_local` 已成立时才给 soft-TLB 写权限，否则 store 不会回到填充路径（ADR-0041 D4 的可观测前提）。
- PTWERR 的可测载体 = **PTBR 指向 ROM**（64 KiB 恰好一张 L1 表；PTE 放 `+0xFFF8`）：PTE 可读、A/D 回写必失败（readonly RAM）。
- `cfx2rc` 写 cg12 时若从 helper 抛异常，须显式把 `env->pc` 置回该指令（精确异常），不能沿用「pc+4」。
- `cfx_ptw_tlb_control` 的判序须是「**先判操作**」：`op=00` 为无条件 no-op，`scope=11` / `range+size=0` 的 `CFXREG` 只对 `clean/invalid/flush` 生效（否则 `none` 会被误判非法操作数）。
- 空的时间戳运行目录（中断留下的 `.dadao/tests/libc-test-user/<UTC>-*`）会让 `check-run-artifacts` A2 变红；本次现场取证后删除空目录（`check` 随即回绿）。

**遗留问题**：`docs/DDLN/C-资源管理/{DD,TT}-C00{1,7,9}` 仍写「ptw/tlb 两个 cfx」「tlb_enable/tlb_exist」（DDLN 讲义，非本任务范围，与 Step 1/2 的 DDLN 遗留同类）；DADAO-13/23 无 TLB 表述，未动。DMA、启动移交、cfx 访问权限、Linux 划分按计划不在 Step 3。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-29）

逐行审查 `helper.c` TLB/A-D/PTWERR 与 cg12 访问层、`cpu.h` 状态、`cpu.c` 复位/非屏蔽位、新探针与 spec 文本：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 run-mode 切换后 HSJU 不再被检查（QEMU 自有 translation cache 缓存了权限结果） | ✅已修 | `cfx_enter`（异常进入）与 `helper_cfx_escape`（退出）丢弃 QEMU 派生 cache；guest TLB 条目不失效 | `tlb_hit_hsju_perm` 首轮 exit=0xEE → 修复后 PASS；`tlb_hit_nwperm` 同轮暴露同类前提 |
| F2 「填充本次访问」是否置 A/D 在 spec 文本中未明说（ADR-0041 D4 只说命中） | ✅已修 | §2.2.5/§4.5 A/D 条文明确「对命中与本次访问触发填充同样适用」+ 锁 sha 重算 | 探针 `ad_read_sets_a`/`ad_write_sets_ad` 断言 A/D 值 |
| F3 user-mode 构建链接失败（`dadao_tlb_control_exec` 未定义） | ✅已修 | 加 user-mode 桩：cg12 在 user 构建被 `cfx_reg_ptr` 拒绝 ⇒ 显式 CFXREG（非静默成功） | `make build-qemu` 首次 rc=2 → 修复后 rc=0（两种构建均链接） |
| F4 `cfx2rc` 写 control 抛 PTWERR 时若沿用 `pc+4` 会破坏精确异常 | ✅已修 | 抛异常前显式 `env->pc = pc`，`cpu_loop_exit_restore(GETPC())` 且不写 pc+4 | `ptwerr_*` 三例 cause/info 精确匹配 |
| F5 `check-asm-prose` R3：`DADAO-11 §3` 仍用已删的 `cfx_tlb_*` 寄存器名 | ✅已修 | §3 改单 PTBR + 16 位 ASID + 全局页示例；册版本 0.9.4-rc；ABI 互锁同升；锁 sha 重算 | `make check` rc=2 → 修复后 rc=0 |
| F6 「首次写必须回到 `tlb_fill`」否则 D 不可观测 | ✅已修 | `dadao_tlb_prot` 仅在 `A_local && D_local` 已成立时给 soft-TLB 写权限 | 注入 B（去掉 store 置 D）⇒ `ad_write_sets_ad`/`ad_writeback_preserves_fields` 转红 |
| F7 探针自身错误：VA 偏移 0x40 与数据落点不一致、`set_page_pte` 后 `rb3` 已被改写 | ✅已修 | 统一 VA 基址；新增 `load_va_fault`/`store_va_fault` 生成精确故障 IP | 32/32 PASS |
| 范围核验 | — | 无 DMA/启动/cfx 访问权限/Linux 划分；Step 1/2 语义未改（页表步进、PTBR、ptw_enable 表达式与原探针均回归绿）；`G`/`PTWERR` 同批收口 | 044t/045t/049t/integ038t/integ039t 全 PASS |
| 未覆盖（如实登记） | ⏸延后 | 替换 dirty 条目的回写（TLB 容量属实现定义，探针不依赖 64 项）；DDLN 讲义旧 `ptw/tlb` 描述 | 见完成区「遗留问题」 |
| 判决 | — | 无未修 finding；状态 `待验收` | — |

### 第 1 轮 reviewer 验收（2026-10-29）

**重跑记录（reviewer 独立执行，真实 rc，未采信完成区转述）**：
- 门控：`make check`=0、`check-modules`=0、`check-arch-smoke`=0、`check-lit`=0（`Passed: 159`）、`check-arch`=0（`integ039t 37/37`、`integ040t 32/32`、m5 向量 10/10 含 `cfx_hart→CFXREG`）、`check-spec-readonly`=0（21 册）、`check-spec-changelog`=0、`check-patch-tree`=0（205 补丁）、`check-source-state`=0（`qemu: OK HEAD=0d88b7757cf0 count=1 clean=True`）、`check-cfx-aliases`=0（byte-identical）。未跑 `check-full`/夜跑。
- 探针：`min_rom_probe_integ040t.py`=0（32/32）；回归 `044t`/`045t`/`049t`=0（PASS）、`integ038t`=0（16/16）、`integ039t`=0（37/37）。
- 证据：`bash .work/evidence/INTEG-040t/run.sh` → `RESULT: PASS=41 FAIL=0`、`RUNSH_EXIT=0`；三次注入均 `probe rc=1` 后 `md5 before=8f5fa8da78a1cfe747960d4ac70bcf71 after=同` 且重建回绿——与完成区「41/41（三次注入）」逐条一致；脚本断言均有可达 FAIL、无恒真/同支同结果、留证直接取 `$?`。
- **独立注入（cp+md5，未用 checkout/restore/stash）**：删失效接口的 G 跳过（`if (!asid_any && (G || asid!=cur))` → 去掉 G 分支）⇒ `build=0`、`--only tlb_g_kept_asid_invalid` **rc=1 FAIL**（`rd6 exp=…7788 got=…ff00`），对照 `tlb_g_removed_asid_any`/`tlb_asid_any0_mismatch` rc=0；`cp` 还原后 md5=8f5fa8da…（相等）、`git -C .work/source/qemu status` 空 ⇒ 重建 `build=0`、探针 **32/32 rc=0**、`make check`=0、`make check-arch`=0。
- 快照对账：开工 / 门控后 / 收尾三份 `git status --porcelain -uall` 逐行一致（`diff` rc=0，24 行），关键 5 文件 md5 与注入前相同，无 `*.preinject`/`*.bak` 残留，DADAO-v5 无本任务提交、无 push。

**约束核验**：① 只做 Step 3——diff 无 DMA/启动/cfx 权限/Linux 改动，变更记录仍写明其不在范围；② 未重开 Step 2——页表步进/优先级文本未改（仅 bit4 保留→G，系 ADR-0040 Consequences 明示要求），038t/039t 回归绿；③ 语义逐条核过：G=bit4（spec 表/`DADAO_PTE_G`/探针）、指定 ASID 失效跳过 G、ASID_ANY 含 G、命中不重读 PTE、fill 不置 dirty、读置 A/写置 A/D、CLEAN 保留/FLUSH 写回后删/INVALID 不写回、FLUSH 失败保留条目、`PTWERR=1<<7` 且 `cause_info=PTE PA` 并入 `cause_nonmaskable`、cg12 op/scope/ASID_ANY 三维正交、`VA` 只看 start、`range size=0` 与 `scope=11`⇒CFXREG——spec/ADR/QEMU/探针四方一致；④ 完成区 24 行（≤30）、本轮 40 行内，任务书与 `milestones.md` 均 `待验收`，临时物在 `/tmp/opencode/INTEG-040t/`；⑤ 组件源 clean、补丁↔源机器一致、锁 sha 21 册通过、changelog 通过；⑥ 凑绿核查：`git diff` 改动范围与任务书清单吻合，无弱化断言/删检查（`m5_perm_unimpl_cfxreg` 换 `cfx_hart` 系别名删除的必要同步，行为仍为 CFXREG）。

**findings（不阻断，交 architect 收尾处置）**：F-1 `tests/arch/umon/m5_perm_reserved_illi.s` 未列入完成区「修改文件」（仅注释别名清单同步，无行为变化，需补申报）；F-2 `spec/README.md:108`（contract-sbi 行）仍把 `tlb` 列作 DADAO-22 §2–§12 功能表 cfx，与本次改写的 DADAO-22 §5 不符（索引叙述，未申报）；F-3 `DADAO-11 §3` 示例标题/上文「切到新 ASID」与代码不符（代码写入 `old_asid` 后按其失效，未写新 ASID；cg12 语义本身正确）；F-4 角点歧义：`op=00(none)` 遇 `scope=11`/`range+size=0` 时实现先校验操作数⇒CFXREG，与 DADAO-12 §4.5「`00 = none` 不产生异常」可两读，`tlb_op_none_noop` 用 scope=all 未覆盖；F-5 DDLN `DD/TT-C001/007/009` 旧 `tlb` 表述（已由完成区如实登记为遗留）。

**判决：Accepted** —— 全部验收命令在我自己的重跑下 rc=0、探针与证据全绿、独立注入红→还原→回绿，硬约束无违反；上述 finding 属文档级（AGENTS 6.5），不构成返工理由，待 architect 终审与收尾提交。

### 第 2 轮 engineer 自审（2026-10-29，reviewer 4 项非阻断 finding）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F-4 `op=00` 被判序后置，可能被 `scope=11`/`range size=0` 先判 CFXREG | ✅已修 | `dadao_tlb_control_exec` 把 `op==0` 早退移到 scope/size 校验之前；`DADAO-12 §4.5`/`DADAO-22 §5.1` 写明「先判操作、`none` 无条件 no-op」 | 新增 `tlb_op_none_scope_reserved`/`tlb_op_none_range_size0`（rc=0、`rd10=0`、条目未动）；注入 C（恢复旧判序）⇒ 两例转红、`tlb_op_none_noop` 仍绿；探针 34/34 |
| F-1 完成区漏列 `m5_perm_reserved_illi.s` | ✅已修 | 完成区「修改文件」补该文件（仅注释同步） | 与 `git status` 清单逐条对齐 |
| F-2 `spec/README.md:108` 仍把 `tlb` 列为 DADAO-22 功能 cfx | ✅已修 | 改为 `ptw/cache/hart/llc/pmem/time/uart/power` 并注明「TLB 维护已并入 `cfx_ptw`，无独立 `tlb` 功能」 | `grep -n "ptw/cache/hart" spec/README.md` |
| F-3 `DADAO-11 §3` 示例注释「切到新 ASID」与代码（写 `old_asid` 后失效）不符 | ✅已修 | 注释与正文改为「先按旧 ASID 失效非全局条目，再写新 ASID」，示例补写 `new_asid` 两行 | 示例与 `DADAO-12 §4.5`（写 ASID 不隐含失效）一致 |
| F-5 DDLN 旧 `ptw/tlb` 表述 | ⏸延后 | 按 reviewer 意见保留为遗留（非本任务范围） | 完成区「遗留问题」 |
| 判决 | — | 4 项均已修（F-5 按指示保留）；状态 `待验收` | — |

### 第 2 轮 reviewer 增量验收（2026-10-29）

**重跑记录（reviewer 独立执行，真实 rc）**：`make check`=0（L1 PASS）、`make check-arch`=0（`integ040t 34/34`、`integ039t 37/37`）、`min_rom_probe_integ040t.py`=0（**34/34**，含 `tlb_op_none_scope_reserved`/`tlb_op_none_range_size0` PASS）、`check-spec-readonly`=0（21 册）、`check-spec-changelog`=0、`check-patch-tree`=0（205 补丁）、`check-source-state`=0（`qemu: OK HEAD=3deaea75a33f count=1 clean=True`）、`check-cfx-aliases`=0（byte-identical）、`bash .work/evidence/INTEG-040t/run.sh` → **`RESULT: PASS=49 FAIL=0`、`RUNSH_EXIT=0`**（四次注入各自 `probe rc=1`、四次 `md5 before=d600809e445e580a277f742076b6ee1e after=同` 还原回绿）——与完成区「34/34、49/49、四次注入」逐条一致。

**F-4 语义核验**：`dadao_tlb_control_exec` 源码与补丁均为 `if (op == 0x0) return OK;` **先于** `scope==3`/`range&&size==0` 校验；`DADAO-12 §4.5`（「`00 = none`：无条件 no-op，`scope=11`/`range size=0` 在该操作下同样不报异常」）与 `DADAO-22 §5.1`（「⇒ `CFXREG`（**仅** `clean`/`invalid`/`flush`；`op=none` 优先按 no-op）」）措辞一致，且与 ADR-0041 D3.2「`00` 为 no-op，不报异常」对齐；两新例各断言 `exit=PASS + rd10=0 + 条目未动` 三重条件，非恒真。

**独立注入（我执行，cp+md5，未用 checkout/restore/stash）**：`if (op == 0x0)` → `if (0 && op == 0x0)`（复用注入 C 锚点、自行执行）⇒ `build=0` → `--only tlb_op_none_scope_reserved` **rc=1 FAIL**（`rd10 exp=0x0 got=0x4`）、`--only tlb_op_none_range_size0` **rc=1 FAIL**（同），对照 `tlb_op_none_noop` rc=0 ⇒ 两新例确有可达 FAIL 路径；`cp` 还原 md5=`d600809e445e580a277f742076b6ee1e`（相等）、qemu `git status` 空、无备份残留 ⇒ 重建 `build=0`、探针 **34/34 rc=0**（回绿）。

**约束核验（增量）**：F-1 完成区已补 `m5_perm_reserved_illi.s`；F-2 `spec/README.md` 改动真实（`ptw/cache/hart/llc/pmem/time/uart/power` + 「TLB 并入 cfx_ptw」，该册不在 spec-readonly 锁内、无需 sha）；F-3 `DADAO-11 §3` 叙述与示例已一致（先按旧 ASID 失效→再写 `new_asid`）；锁 sha/别名仍一致；快照对账：`git status -uall` 归一化后 **25 行**与本轮开工清单逐行一致（`diff` rc=0），无新提交、无 push、未跑 check-full/夜跑，QEMU 补丁↔源一致、源树 clean。

**findings（文档级，按 6.5 记录、不阻断，交 architect 收尾一并改）**：F-6 **`spec/README.md` 修好 F-2 后仍未列入完成区「修改文件」**，engineer 表中「与 `git status` 清单逐条对齐」与事实不符（staging 前须补申报）；F-7 `components/qemu/changelog.md`（含同句 `scope=11 ⇒ CFXREG` 缺 `none` 限定）与 `.tao/knowledge/milestones.md` 仍写「**32 例**」（现 34）；F-8 `.tao/contracts/contract-see.md:31` 未补「仅 `clean`/`invalid`/`flush`」限定，与 DADAO-12 新措辞在 `op=none` 角点可两读（其自身引用的 ADR-0041 D3.2 已支持 no-op 读法）；F-9 DDLN 旧表述（沿用上轮遗留）。

**判决：Accepted（可提交）** —— 门控/探针/证据在我重跑下全 rc=0、`49/49`，新增 no-op 用例经我独立注入证实可达 FAIL 并还原回绿，F-1..F-4 处置真实；上述 4 项均为文档级（6.5 明令不得因此返工），建议 architect 在收尾提交中连同 F-6~F-8 的一行修补一并显式 staging；最终接受由 architect 终审。
