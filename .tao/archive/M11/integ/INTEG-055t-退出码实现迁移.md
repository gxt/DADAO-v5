# INTEG-055t: 退出码实现迁移（QEMU/gem5/tests）

**模块**：integ
**项目里程碑**：M11
**依赖**：`SPEC-187t`（已验证；Machine-v5 §7.1 三段表）、`SPEC-192t`（已验证；表已迁 §7.1）、`SPEC-191t`（旧码清理）
**状态**：已验证

## 执行环境
本地；跨 QEMU/gem5/tests 的退出码实现迁移，按 QEMU → gem5 → tests 串行。

## 背景

`Machine-v5 §7.1` 已定稿：

- guest：`0x00–0x3F` PASS、`0x40–0x7F` FAIL
- 其它 cfx：`0x80–0xBF`（`bit5:0=cfxHA`）
- monitor：`0xC0–0xFF`（`bit5:4=运行模式`、`bit3:0=异常位索引`）
- monitor 索引：0/1/2/3/7/8/9/10/11/12/13

QEMU/gem5/tests 仍用旧码/旧公式，需迁移。同时 `DADAO-12 §2.2.6/§5.2` 已明确：页表步进/TLB 命中产生的异常进入当前运行模式 monitor（未映射/A-D 回写失败 ⇒ `CFXMEM`，HSJU/R/W/X ⇒ `CFXPERM`），不再进入 `cfx_ptw`；实现仍走旧路由，本任务一并修正。

## 目标

1. **QEMU**：machine fault 退出码改为三段式；monitor 段按当前运行模式 + 异常位索引；其它 cfx 段按 cfxHA；guest pass/fail 不变；删除旧 `0x84`/`0x87`/`0xE1` 派生；页表步进/TLB 命中异常改投当前 monitor（未映射/A-D ⇒ `CFXMEM`、HSJU/R/W/X ⇒ `CFXPERM`），删除 `PTWERR` 进 `cfx_ptw` 的路径与旧 cause。
2. **gem5**：同 QEMU，逐处对齐（含页表异常改投当前 monitor）。
3. **tests**：更新期望退出码、harness、parity 判据；matrix 重生成。
4. 三阶段串行；共享测试只在 tests 阶段改。

## 验收标准

1. QEMU/gem5 退出码与 `Machine-v5 §7.1` 逐项一致：guest / 其它 cfx / monitor。
2. `CFXTRAP`/`CFXESC` 进目标/当前 cfx 时按 `0x80–0xBF`；其余同步异常进当前 monitor。
3. 页表步进/TLB 命中：未映射/A-D 回写失败 ⇒ 当前 monitor `CFXMEM`；HSJU/R/W/X ⇒ 当前 monitor `CFXPERM`；无 `PTWERR`/`cfx_ptw` 旧路由。reserved cfx `ld/st` ⇒ `CFXMEM`、`trap`/`escape` ⇒ `ILLI`。
4. `make build-qemu`/`build-gem5`、`check-arch`/`check-inst`、L1 rc=0。
5. `matrix-M11` 重跑：`node/arch` 249 AGREE、0 fail；退出码相关行全 AGREE。
6. 反例：写回旧 `0x84`/`0x87` ⇒ FAIL；还原回绿。
7. 完成区 ≤30 行；状态 `待验收`。
8. **页表路由**：`integ039t`/`integ040t` 的页表 fault 用例改读当前 monitor cause（`CFXMEM`/`CFXPERM`）并通过；A-D 回写失败在无有效 monitor 向量时退出码为 monitor `CFXMEM`（hypv `0xF1`）。

## 范围 / 非范围

**在范围内**：`components/qemu/**`、`components/gem5/**`、`tests/**`（退出码期望/harness、页表 fault 探针）、`tools/testcases/parity/**`（判据如需）、`tools/infra/check_interface_alignment.py`（§7.1 公式断言，必要连带）、本任务书、`milestones.md`。**页表异常改投当前 monitor** 是 QEMU/gem5/tests 的共同必需项。

**不在范围内**：`spec/**`、ADR、`contracts/**`、5 个屏蔽寄存器清理（`INTEG-054t`）。

## 说明

- 这是 `SPEC-187t` 的实现落地；不改 spec。
- 旧的 `0x80 | cause_bit` 公式不再使用；monitor 段不是简单 `0x80 | index`。
- 若某测试的期望码需人工推导，按 §7.1 计算并在完成区给出公式/示例。

## 完成区

**测试结果**：`build-qemu`/`install-host`/`build-gem5`/`build-bootrom` 全 PASS；`check-arch` PASS（smoke 10/10 + 13 探针，含 integ039t 37/37、integ040t 34/34）；`check-inst` PASS（node 965/970、0 failed、5 deferred；tiny 44/44）；`check-gem5-decode` PASS（264/264+388/388+28/28+2/2）；`check_b6` PASS（30/30）；`make check`（L1）PASS。parity 全量 PASS：node/arch 269 / **249 AGREE / 0 fail / 20 BLOCKED**、node/inst 965、tiny/inst 1005、tiny/picolibc 17，diff/gem5_only/qemu_only 全 0。证据：基线 **25/25**、`--inject` **31/31**。
**修改文件**：`components/qemu/patches/target/dadao/{cpu.c,cpu.h,helper.c}.patch`、`components/qemu/changelog.md`；`components/gem5/patches/src/arch/dadao/{fs_machine.hh,fs_machine.cc,inst.cc,node_tlb.cc,node_cfx.hh,node_cfx.cc}.patch`、`components/gem5/{README.md,changelog.md}`；`tests/shared/bootrom/step5/hmon.S`；`tests/arch/umon/*.s`+`expected.yaml`；`tests/inst/{schema.md,base/*.yaml}`；`docs/TestReports/M11-三平台一致矩阵.md`；`tools/testcases/arch/*`（13 探针+prelude+run_m5_e2e）、`tools/testcases/lib/{run_qemu_test,build_test_binary,verify_harness_dump,README}`、`tools/testcases/parity/*`、`tools/testcases/{picolibc_tests,validate_vectors,unit/*,tset/*,generate_*}`；`tools/infra/check_interface_alignment.py`（§7.1 公式断言，必要连带）；本任务书、`milestones.md`。
**验收结果**：exit code 三段式与 `Machine-v5 §7.1` 一致——monitor `0xC0|mode<<4|index`（Tiny ILLI `0xF8`、Tiny CFXMEM `0xF1`、Node supv ILLI `0xE8`）；其它 cfx `0x80|cfxHA` 由公式宏/`machineFaultExitCode` 实现并带编译期自检。页表步进/TLB 命中异常改投当前 monitor：缺页/碎片/A-D 回写失败 ⇒ `CFXMEM`、HSJU/R/W/X ⇒ `CFXPERM`；删除 `PTWERR`/页级 one-hot cause 与 `cfx_ptw` 路由。新增 `integ040t --only ptwerr_monitor_cfxmem_exit`：A/D 回写失败 + 无效 monitor 向量 ⇒ 退出码 `0xF1`（monitor hypv CFXMEM）。反例：注入旧 `0x80|index` ⇒ Tiny ILLI `0x88` FAIL、Tiny CFXMEM `0x81` FAIL；`cp`+md5 还原重建后回绿。
**新发现/坑**：① 页表 monitor 处理器必须切到 hypv 运行：supv 模式下 `cg_reg_deleg` 会拒绝对其它 monitor cg5 的读取；每个 monitor 用独立 handler 变体（读自身 cause + 自身 escape）。② `integ040t` 原 `CFX63_OOB = RAM_BASE+RAM_SIZE` 实为 cfxha0 内存窗口，改为真正的 cfxha63 地址，避免页表 miss 进 monitor 后无处理器死循环。③ 证据脚本的 `check … "$(…)" $?` 会先展开替换再取 `$?`，必须先把 rc 落变量；矩阵/`md5sum -c` 两条已用副本验证可达 FAIL。④ 编译期自检会直接拒绝旧公式，运行期反例需同时停用自检。⑤ 新增退出码用例放在 `EXTRA_CASES`（仅 `--only`），不改变 parity 冻结的 269 例计数。
**遗留问题**：① “其它 cfx”段（`0x80–0xBF`）当前无可达 machine-fault 路径（`CFXTRAP`/`CFXESC` 均进向量），仅有公式/编译期自检与 gem5 `machineFaultToCfx` API，无运行期用例；② 旧 standalone Tiny 探针数值已按 hypv 重映射，但其 raw-kernel 256 B 前缀检查为既有问题，仍不可直接运行（不在任何门控内）。

## 审阅记录

#### 第 1 轮 engineer 自审

**方式**：自主逐行审查（`subagent_depth=1`，无嵌套子代理）。逐行核对 QEMU `cpu.h/helper.c`、gem5 `fs_machine.{hh,cc}/node_tlb.cc`、`hmon.S` 策略、harness/探针期望与 parity 判据；每项 finding 均以真实门控或探针复验。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| Node ILLI 运行时探针实际由 bootrom `hmon.S` 固件写码，不能验证 QEMU 公式 | ✅已修 | 注入反例改用 Tiny ILLI（`mem-rb.yaml#1`）；Node ILLI 保留为固件/端到端检查 | `--inject` 中 Tiny ILLI 得 `0x88` FAIL、还原后 `0xF8` PASS |
| 注入旧公式时编译期自检先拒绝构建，脚本未还原而留下脏源树 | ✅已修 | 注入同时停用 `_Static_assert`，并加失败分支恢复+重建；`cp`+md5 校验 | 源树 `status` 干净、md5 一致、`check-source-state` OK |
| guest 段重映射后旧 pass token `0x40–0x7F` 落入 FAIL、旧 fail `0x01` 落入 PASS | ✅已修 | umon 10 个 pass token → `0x10–0x30`；探针 fail 码 → `0x60–0x7F`；`build_test_binary` FAIL `0x01→0x40` | `check-arch-smoke` 10/10、`check-inst` 965/970 + 44/44 |
| Node inst fault 码来自 `hmon.S` 而非 QEMU 映射，漏改则 parity 假绿失败 | ✅已修 | `HMON_FAULT_CODE` 改 `0xF1–0xFD`（hypv 基址） | `check-inst` Node 965/965 执行项、parity node/inst 0 diff |
| `run_parity --allow-repo-write` 将矩阵写进工作树，产生未跟踪产物 | ✅已修 | 改用仓库外临时目录，清理已生成产物 | `git status -uall` 无 `parity-*`/`evidence/` 残留 |
| `check_milestones_fresh` 因流水次序/登记注/状态不一致红 | ✅已修 | 流水行上移、补 `（登记）`、表状态与任务书同步 `待验收` | 最终 L1 待复跑（见验收结果） |
| `tools/infra/check_interface_alignment.py` 仍断言旧逐码常量 | ✅已修（范围外披露） | 改为 monitor/other-cfx 公式 + 旧常量清零断言 | `check-interface` 88/88 PASS |
| **reviewer 阻断 1**：证据脚本 `check … "$(…)" $?` 先展开替换再取 `$?`，矩阵/md5 断言恒真 | ✅已修 | 改为先 `rc=$?` 落变量再传 `check`；矩阵副本期望改 999、md5 副本期望改全 0 均 FAIL，真脚本 25/25 + 31/31 绿 | `matrix-copy` RC=1（zero_fail=False）、`md5-copy` RC=1（checksum did NOT match）、真脚本 RC=0 |
| **reviewer 阻断 2**：页表/A-D 回写失败仍进 cfx_ptw，验收 3 未落地 | ✅已修 | QEMU：`tlb_check`/`ptw_walk` 缺页/A-D→`CFXMEM`、HSJU/R/W/X→`CFXPERM`，`PTW_FAULT` 改进当前 monitor，删 `PTWERR`/页级 cause；gem5：`NodePtwFault` 改投 `s.runMode`，删 `CausePtwErr`/页级 cause，TLB control A-D 失败→monitor `CFXMEM` | `integ039t` 37/37、`integ040t` 34/34、`ptwerr_monitor_cfxmem_exit` 0xF1、parity node/arch 269/249/0 |
| 非阻断：check_interface 范围、旧公式注释、schema/validator `UNMAPPED`、061t `0xEE`、Node supv `exit=` | ✅已修 | 完成区补文件；三处注释改 `0xC0|(mode<<4)|index`；schema/validator 删除 `UNMAPPED` 合法项；061t 哨兵 `0xEE→0x7E`；048t PASS 输出 `exit=0x..`，证据断言 `exit=0xe8` | L1 PASS、`validate-vectors` PASS、`061t` 语法/PASS、证据 `exit=0xe8` |

**结论**：上述 finding（含 reviewer 两条阻断与全部非阻断项）均已修并复验；无未修项。

#### 第 1 轮 reviewer 验收

**判决：Needs Revision**（2 项阻断见「失败项」；其余逐条核验通过）。我只改了本审阅记录。**快照对账**：审前/审后 `git status --porcelain -uall` 均 94 行、0 未跟踪、`diff` 一致；QEMU/gem5 4 个被测源文件 md5 与审前相同；`check-patch-tree --source-state` rc=0（`qemu: OK HEAD=4e1276b93b0d count=1 clean=True`、`gem5: OK HEAD=d95cbd4e2ffe count=1 clean=True`）。

**重跑记录（我的输出/退出码）**：`build-qemu` rc=0、`install-host` rc=0、`build-gem5` rc=0、`build-bootrom` rc=0；`make check`(L1) rc=0（`repository checks (L1): PASS`）；`check-gem5-decode` rc=0（264/264、388/388、28/28、2/2，failures 0）；`python3 tools/gem5/check_b6.py` rc=0（`b6 ids 30/30 … failures 0`）；`check-arch` rc=0；`check-inst` rc=0（node `970 total, 965 passed, 0 failed, 5 deferred`；tiny `44/44`）；`check-patch-tree` rc=0；`check_interface_alignment.py` rc=0（5+34+41+8 = **88/88** 全 PASS）。证据脚本重跑：baseline `SUMMARY: checks=22 failures=0` **rc=0**；`--inject` `checks=28 failures=0` **rc=0**（注入旧码→Tiny ILLI `Exit code: 0x88` FAIL、Tiny CFXMEM `0x81` FAIL，还原后 `0xF8`/`0xF1` PASS）。parity 独立重跑 `run_parity --profiles node --scopes arch` **rc=0**：`node/arch 269 | 249 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 0`，与入库矩阵逐列一致；矩阵头部引擎 md5/路径已刷新为本工作树 ⇒ 确系重生成。

**独立注入（`cp`+`md5sum -c`，未用 git 还原）**：把 `target/dadao/helper.c` 中 `case DADAO_EXCP_UNMAPPED: index = 1` 改为 `index = 8`（静态断言/grep 不受影响），重建 rc=0 后重跑**同一脚本** → **rc=1、3 FAIL**：`FAIL runtime Tiny CFXMEM … actual: rc=1 Exit code: 0xF8`、`FAIL check-patch-tree rc=1`、`FAIL check-source-state rc=1`；`cp` 还原 + `md5sum -c` → `helper.c: OK`，重建 rc=0 后重跑 → `checks=22 failures=0` **rc=0**。

**约束核验**：QEMU 旧逐码 enum 已删，`DADAO_EXIT_CFX(cfxHA)`= `0x80|(cfxha&0x3F)`、`DADAO_EXIT_MONITOR(mode,index)`= `0xC0|((mode&3)<<4)|(index&0xF)`，`dadao_excp_to_exit_code(env, …)` 按 `env->inner_run_mode` 编段，`UNMAPPED`→CFXMEM(1)，索引 1/2/7/8/9/10/11/12/13 与 spec §7.1 逐项一致（`0x87`/`0xE1` 仅存于 `_Static_assert` 自检）。gem5 `MachineFaultCause` 为 DADAO 位索引（0/1/2/3/7..13），`machineFaultExitCode(cause, runMode, targetCfxha)` 编 monitor/其它 cfx 段，Node 取 `nodeState().runMode`、Tiny 回退名义 `3`，`FaultUNMAPPED`→`FaultCFXMEM`。hmon `0xF1–0xFD` = `0xF0|index`（hypv）；umon pass token 10/10 ∈`0x00–0x3F`（`0x10–0x30`），mismatch `0x71/0x72`、探针 fail `0x60–0x7E` ∈`0x40–0x7F`；parity 故障判据 `0x80 <= rc <= 0xFF`（三段）。无 `spec/`、ADR、`contracts/` 改动；完成区 5 行 ≤30、状态`待验收`、无运行期路径、无未跟踪残留。

**失败项 1（阻断）证据脚本两条断言恒真、无可达 FAIL 路径**（`run.sh`）：`check "matrix-M11 …" "$(cat …)" $?` 与 `check "inject: cp restore md5 matches" "$(tail -1 …)" $?` —— bash 同命令内先展开 `$(…)` 再展开 `$?`，`$?` 取到的是 `cat`/`tail` 的 0。用脚本**副本**诊断（未改交付脚本）：矩阵期望 `agree_pass == 249` 改 `999`（python 退出1）→ 仍 `PASS … actual: total=269 agree=249 zero_fail=False`、整脚本 **rc=0**；md5 期望改全 0（`md5sum -c` 报 `FAILED`）→ 仍 `PASS … actual: md5sum: WARNING: 1 computed checksum did NOT match`、**rc=0**。改法：两处先 `rc=$?` 落变量再传 `check … "$rc"`。脚本不合格 ⇒ 判 Needs Revision，reviewer 不代改脚本。

**失败项 2（阻断，需 architect 裁定）验收标准 3 的「A-D 回写失败 ⇒ CFXMEM monitor」未实现且未披露**：QEMU `DADAO_EXCP_PTW_FAULT` → `cfx_enter(…, DADAO_CFXHA_PTW, …)`（cause 置 `DADAO_CAUSE_PTWERR`）；gem5 `node_tlb.cc` `NodePtwFault(CausePtwErr, …)`，L23 注释仍写 delivered to cfx_ptw；spec `DADAO-12 §2.2.6/§5.2`（SPEC-189t）与 `Machine-v5 §7.1` 要求「归当前运行模式 monitor 的 CFXMEM、不进入 cfx_ptw 异常入口」。探针 `integ040t/ptwerr_*` 断言旧路由，两引擎均 PASS ⇒ parity AGREE 测不出。SPEC-189t 任务书已把 QEMU/gem5/tests 实现划给「后续实现任务」，但 `.tao/tasks/`、`discussing.md` 尚无该任务 ⇒ 请裁定：本任务补做，或修订验收口径并在完成区披露 + 立后续任务。

**非阻断 finding（文档级，交 architect 收尾）**：① 完成区「修改文件」未列 `tools/infra/check_interface_alignment.py`（仅遗留③披露），staging 对账需补；② 3 处注释仍写旧公式 `0x80|cause`：`build_test_binary.py:24/551`、`run_embench_user_suite.py:57`、`run_codegen_e2e.py:343-346`；③ `tests/inst/schema.md:30/148` 与 `validate_vectors.py:51` 仍把 `UNMAPPED` 列为合法 `expected_fault`，而 harness `fault_name()` 已不产出该名；④ `min_rom_probe_061t.py` 不可达出口哨兵 `0xEE` 落 monitor 段（非法索引14），宜改 guest FAIL 段；⑤ 证据项 `runtime Node supv ILLI = 0xE8` 只断言 `[PASS]`、`actual` 中 `exit=` 为空（0xE8 实由该探针内部断言保证），展示与断言不对齐。

#### 第 2 轮 reviewer 验收

**判决：Accepted**（两条阻断均已修复并由我独立复验；非阻断项全部落实）。本轮我只改本审阅记录。**终态对账**：审前/审后 `git status -uall` 均 97 行、0 未跟踪、`diff` 一致；QEMU/gem5 40 个被测源文件 md5 与审前逐个相同（`md5sum -c` 全 OK）；`matrix-M11.md` md5 还原 OK；`check-patch-tree` rc=0、`check-patch-tree --source-state` rc=0（`qemu: OK HEAD=c0aecada0e44 count=1 clean=True`、`gem5: OK HEAD=5812f78a74a9 count=1 clean=True`）。

**阻断 1 复验（两处断言可达 FAIL，我独立注入、不采信副本）**：① 直接改**被测产物** `docs/TestReports/M11-三平台一致矩阵.md` 的 `node/arch agree 249→250` → 真脚本 **RC=1**：`FAIL matrix-M11 node/arch 269/249/0 | … actual: total=269 agree=250 zero_fail=False`、`SUMMARY: checks=25 failures=1`；`cp`+`md5sum -c` 还原 OK。② md5 断言用**我自己的**脚本副本（期望哈希改全 0）跑 `--inject` → **RC=1**：`FAIL inject: cp restore md5 matches | actual: md5sum: WARNING: 1 computed checksum did NOT match`（日志 `cpu.h: FAILED`）、`SUMMARY: checks=31 failures=1`；还原后真脚本回 **31/31 RC=0**。逐条审计 run.sh 全部 31 处 `check`：除 `$([ … ]; echo $?)`（自校验、正确）外无 `$(…)`+`$?` 混用、无恒真。

**阻断 2 复验（页表/A-D 统一进当前 monitor）**：QEMU `DADAO_EXCP_PTW_FAULT → cfx_enter(…, env->inner_run_mode, …)`；缺页/fragment/TLB-miss/A-D 回写失败一律 `DADAO_CAUSE_CFXMEM`，HSJU/R/W/X → `DADAO_CAUSE_CFXPERM`；`DADAO_TLB_CMD_PTWERR → DADAO_TLB_CMD_AD_WB_FAIL`；源码 `PTWERR`/`ISPFTRAP`/`NUPERM`/`NXPERM` 等旧 cause **清零**（仅一句注释说明“无 PTWERR”），`spec` 正文（变更记录之前）也无 `PTWERR`。gem5 `NodePtwFault::invoke → nodeCfxRaise(cause, s.runMode, …)`、缺页/A-D → `CauseCfxMem`、权限 → `CauseCfxPerm`、`CausePtwErr` 清零，`node_cfx.cc` TLB 控制回写失败 → `CauseCfxMem`+`s.runMode`+`errPa`。探针 `integ039t`/`integ040t` 改 cfx0–3 monitor handler（读自身 cause 帧），`049t CFX63_OOB` 改真 cfxha63 地址；`expected_fault: UNMAPPED` 全仓为 0。

**重跑记录（我的真实 rc）**：`build-qemu`/`install-host`/`build-gem5`/`build-bootrom` 全 rc=0；`make check`(L1，含 validate-vectors/check-interface/check-case-ledger) **rc=0**（`repository checks (L1): PASS`，check-interface 5+34+41+8=**88/88**）；`check-gem5-decode` rc=0（264/264、388/388、28/28、2/2，failures 0）；`check_b6` rc=0（30/30）；`check-arch` rc=0（arch-smoke PASS、integ039t **37/37**、integ040t **34/34**、0 FAIL）；`check-inst` rc=0（node **965/970** 0 failed 5 deferred、tiny **44/44**）；证据脚本 baseline **25/25 RC=0**、`--inject` **31/31 RC=0**（旧公式注入→Tiny ILLI `0x88`、Tiny CFXMEM `0x81` FAIL，还原 `0xF8`/`0xF1` PASS）。

**parity 独立重跑（两条命令，均为我的真实 rc）**：① `run_parity --profiles node --scopes arch` **rc=0**（273 s，`run_parity: PASS`）→ `node/arch 269|249|0|0|0|0|0|0|20|0`；② 全量 `run_parity --jobs 8` **rc=0**（`run_parity: PASS`）→ node/inst `1014|965|…|5|44`、tiny/inst `1014|1005|…|5|4`、tiny/picolibc `20|17|0|0|0|0|0|0|1|2`、node+tiny embench `38|38`。两者的 node/arch 行与入库 `matrix-M11.md` **逐列逐格相同**（269 total / 249 AGREE / 0 fail/diff / 20 BLOCKED）；矩阵头部引擎 md5（QEMU `6088607e…`/`c0aecad`、gem5 `20b071c2…`/`5812f78a`）已刷新为本轮构建 ⇒ 重生成属实。

**第 1 轮 5 条非阻断项落实**：① `tools/infra/check_interface_alignment.py` 已入完成区「修改文件」；② 3 处 `0x80|cause` 注释已改新公式（全仓 grep 计 0）；③ `tests/inst/schema.md` 与 `tools/testcases/validate_vectors.py` 已删 `UNMAPPED` 合法项（`expected_fault: UNMAPPED` 全仓 0）；④ `061t`/`049t` 不可达哨兵 `0xEE→0x7E`；⑤ 048t 证据断言改 `exit=0xe8`，实测 `actual: rc=0 exit=0xe8`。

**独立注入③（旧路由复活：可达 FAIL + 还原回绿）**：把 QEMU 页表 fault 的 `cfx_enter` target 由 `env->inner_run_mode` 改回 `DADAO_CFXHA_PTW`，重建 rc=0 → 真脚本 **RC=1、4 FAIL**：`runtime page-table miss -> monitor CFXMEM cause rc=1`、`runtime A/D write-back -> monitor CFXMEM cause rc=1`（`exit exp=0x0 got=0xf1; cid3 exp=0x2 got=0x1`）、`check-patch-tree rc=1`、`check-source-state rc=1`；`cp`+`md5sum -c` 还原 OK、重建 rc=0 → **25/25 RC=0**。全程未用 git checkout/restore/stash。

**约束核验**：退出码三段式与 `Machine-v5 §7.1` 逐项一致（QEMU `DADAO_EXIT_CFX`/`DADAO_EXIT_MONITOR`+`_Static_assert`、`dadao_excp_to_exit_code(env,…)` 按 `inner_run_mode`、`UNMAPPED`→CFXMEM(1)；gem5 `MachineFaultCause` 位索引 + `machineFaultExitCode` + Node 取 runMode/Tiny 名义 hypv、`FaultUNMAPPED`→`FaultCFXMEM`）；hmon `0xF1–0xFD`=`0xF0|index`；umon pass token 10/10 ∈`0x00–0x3F`、探针 fail `0x60–0x7E` ∈`0x40–0x7F`；无 `spec/`、ADR、`contracts/` 改动；97 个改动文件与完成区「修改文件」逐一对账（含新增 `node_cfx.{cc,hh}.patch`、`validate_vectors.py`、`check_interface_alignment.py`）；完成区 5 行 ≤30、状态`待验收`、无运行期路径、无未跟踪残留。

**非阻断 finding（不改判，供 architect 收尾参考）**：① `ptwerr_monitor_cfxmem_exit` 对路由不敏感——旧路由注入下它仍 PASS（末段直接 machine fault 的退出码由 `inner_run_mode` 决定），路由判别实际由另两条 runtime 检查承担；若要它同时判别路由，应断言 monitor cause 帧/进入路径。② run.sh 静态项未 grep 新路由（如 `PTW_FAULT` 目标必须是 `inner_run_mode`、fault 路径不得出现 `DADAO_CFXHA_PTW`），可加一条静态断言做 fail-fast（现由 3 条 runtime 覆盖）。③ 入库矩阵不含 embench 行（与历史快照口径一致，完成区亦未宣称）。

#### 收尾（architect，2026-11-06）

- 两条阻断（证据脚本恒真、页表/A-D 路由）已返工，reviewer 独立复验：旧路由复活注入 ⇒ 4 FAIL，`cp`+md5 还原重建 ⇒ 25/25 回绿。
- 全量 parity 与矩阵逐列一致：node/arch 269 = 249 AGREE + 20 BLOCKED，0 fail/diff；node/inst 965、tiny/inst 1005、tiny/picolibc 17。
- 非阻断 5 条已落实（`check_interface_alignment.py` 入完成区、旧公式注释清零、`UNMAPPED` 合法项删除、`061t` 哨兵 `0x7E`、048t `exit=0xe8` 实测）。
- 遗留：`ptwerr_monitor_cfxmem_exit` 对路由不敏感（路由判别由两条 runtime 检查承担）；证据脚本可加 `PTW_FAULT` 目标 fail-fast 静态断言；矩阵不含 embench 行（历史口径）。
- 判决 Accepted，状态置 `已验证`。
