# INFRA-068t: `setjmp`/`longjmp` 真实现（用 RA 存取/块赋值）

**模块**：infra
**项目里程碑**：M7
**依赖**：`INFRA-067t`（同改 `components/picolibc/patches` ⇒ **串行**）
**状态**：已验证

> 立项来源：用户 2026-10-12 裁定「先在 M7 内做解锁件再归档」+ 本轮讨论（**从易到难第 6 项**，原判"最难/不可为"）；依据 blocked **1**（`setjmp` 桩）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：`setjmp/longjmp` 因 RegRAS 深度问题如何处理。
- 选项：A「**真实现（推荐）**」／B「记 `excluded`」／C「先做最小可行性验证」。
- **用户选择 = A「真实现（推荐）」**。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## **事实修正（本任务的核心前提）**

- 现行 `setjmp.S`（`INFRA-057t`）是**显式失败桩**，其注释称「ISA 除 `ret` 外**无指令**可弹/恢复 RegRAS 条目」——**该陈述错误** ✗。
- **ISA 事实上提供**（`contract-isa §1.3.4` 明文）：
  - **`ra0`–`ra63` 可读写**（「`ra0` 作目的或源均不触发异常（**可读写**）」）；
  - 覆盖指令：**`ld.o`/`st.o`、`ldm.o`/`stm.o`**（`SimRISC-01 §存取RA寄存器`）与 **`rd2ra`/`ra2rd`**（`SimRISC-02 §寄存器组之间块赋值`）；
  - **深度与溢出状态就在 `ra0`**：`[53:48] = RACNT`（RegRAS 有效条目数 0–63）、`[47:0] = MRPTR`（MemRAS 栈顶地址，**0 = 未启用 MemRAS**）；`ra1–ra63` = 每条（递归计数 + 返回地址），**`ra63` 恒为栈顶**；有效性判据 = `RACNT`（不看条目值）。
- ⇒ **`setjmp/longjmp` 可软件完整实现**：保存/恢复 `ra0` + `ra1..ra63`（+ callee-saved GPR + `rsp`）即可恢复"深度 + 条目" ✓。
- **唯一限制**：`MRPTR != 0`（启用 **MemRAS** 溢出区）时，`longjmp` 后的新 `call` 可能覆盖 MemRAS 中"恢复所需但未弹出"的条目 ⇒ 该情形需连 **MemRAS 内容**一并保存（复杂）⇒ **本任务只做 `MRPTR == 0`（纯 RegRAS，≤63 深度）路径**，并**显式登记该限制**；**实测** M7 运行环境（`Machine-01`/bootrom）**是否启用 MemRAS**（预期未启用）。

## 接口规范

- **输出**：
  1. **真实现 `libc/machine/dadao/setjmp.S`**（`components/picolibc/patches/**`）：
     - **`setjmp`**：保存 **callee-saved 寄存器集合**（按 `contract-abi`/`ADR-0018` 的 ABI 约定，现场核**哪些 GPR/FP 寄存器跨调用保留**）+ **`rsp`** + **`ra0`**（含 `RACNT`/`MRPTR`）+ **`ra1..ra63`**（**优先用块赋值 `ldm.o`/`ra2rd`**，否则逐条 `ld.o`）；返回 0；
     - **`longjmp`**：**反向恢复**（含写回 `ra0` 的 `RACNT`/`MRPTR` 与 `ra1..ra63`）+ 按 C 语义**令 `setjmp` 返回非 0 值**（`val`，`val==0` ⇒ 1）；
     - **`sigsetjmp`/`siglongjmp`**（若 picolibc 需要）同法或按现场。
  2. **更正桩注释**：删除"ISA 无指令"错误陈述，改为**如实**写明 RA 存取依据（`contract-isa §1.3.4`）+ **`MRPTR != 0` 的限制与登记**。
  3. **重建 picolibc**（`make build-picolibc`）+ 全量 test：`make check-picolibc-tests-full` ⇒ **四分类 before/after**（before：`pass 152 / fail 0 / excluded 18 / blocked 65`）+ 解锁清单（预期 1 条：`test-setjmp`）。
  4. `.tao/knowledge/milestones.md` 流水更新 `INFRA-068t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**用 ISA 现成手段**（`ld.o`/`st.o`/`ldm.o`/`stm.o`/`rd2ra`/`ra2rd`），不自造；**不改** `spec/`、`contracts/`、`tests/vectors/`、LLVM 侧；**计数不写死**。

## 验收标准

1. **语义正确（重点，非抽样）**：自建最小用例（**调用深度 ≥3**、跨函数 `longjmp`、循环内 `setjmp`、`val=0/非0`）**真跑 rc=0**，且**证明顺序返回**（`longjmp` 后 `ret` 沿**原调用链**正确返回——用「各层返回后打印/退出码」类证据）。
2. **深度恢复可证**：构造"`setjmp` 前深度 D，`longjmp` 时深度 D+k"的用例，核恢复后**不再有多余条目**（可另用 `ra0` 的 `RACNT` 读回核对）。
3. **`test-setjmp`**：真跑 **rc=0**（真实输出/退出码）；**`fail` 仍须 0**。
4. **桩注释已更正**：`grep` 证明错误陈述**已不存在**，新注释**引 `contract-isa`/`SimRISC-01/02`** 依据。
5. **限制已登记**：`MRPTR != 0`（MemRAS）限制写入完成区「遗留」；**实测** M7 环境 `MRPTR` 状态（读 `ra0`）。
6. **全量 test**：`pass` **上升**、`blocked` **下降**（before/after 现场统计 + 解锁清单）。
7. **门控**：`make check`、`check-patch-tree`、`check-no-residue`、`check-picolibc-tests`（快档）各 EXIT=0。
8. **反例可失败**：注入（**去掉 RA 恢复** / 只恢复部分条目）⇒ 用例 **FAIL/错乱**（可达 FAIL）⇒ `cp`+md5 还原 ⇒ 回绿。
9. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-068t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥、`.work/source/picolibc` = `base+N`、`series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/picolibc/**`、任务书、`milestones.md` 行）；越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时**停止并报告**（禁自拟自答）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **计数不写死**。

## 完成区

**测试结果**：通过 3/3 最小用例；失败：无。证据脚本 `.work/evidence/<任务ID>/run.sh` rc=0（`ALL CHECKS PASSED (inject=0)`；`--inject` rc=0）。`test-setjmp` rc=0/status=pass。全量四分类：before `pass 203 / fail 0 / excluded 22 / blocked 10`（total 235）→ after `pass 205 / fail 0 / excluded 22 / blocked 8`；`newly_blocked=∅`；unlocked = `test-setjmp`,`test-double-free`。门控：`make check`/`check-patch-tree`/`check-index-blobs`/`check-no-residue`/`check-picolibc-tests`/`check-patch-tree --source-state` 各 rc=0。
**修改文件**：`components/picolibc/patches/libc/machine/dadao/setjmp.S.patch`（真实现）；`components/picolibc/patches/libc/include/machine/setjmp.h.patch`（`_JBLEN` 129）；`components/picolibc/{README.md,changelog.md}`；`.tao/knowledge/milestones.md`；**越界（已披露）** `tools/testcases/picolibc_tests.py`（删陈旧 `UNSUPPORTED_TESTS["test-setjmp"]`，防真 abort 被误判 `blocked`）。组件工作树（`.work/source/<component>`）已 amend 为 `base+1`。
**验收结果**：
- ①语义：`t_deep`（深度 3 跨函数 `longjmp`，`r=7`；longjmp 后新嵌套链顺序返回 `chain seq=123`）；`t_vals`（`val0->1`、`val5->5`、循环 `10/11/12`）；`t_depth` rc=0。
- ②深度恢复：`t_depth` `base depth=2`（读回 `ra0` 的 RACNT）→ `deep depth=4` → `longjmp` → `after depth=2`（相等，无多余条目）。
- ④桩注释：`no instruction to pop|NOT IMPLEMENTED YET|cannot be repaired from software` count=0；新注释引 `contract-isa`/`存取RA寄存器`/`寄存器组之间块赋值` count=3。
- ⑤`MRPTR` 实测（M7 QEMU `dadao-m1`，读回 `ra0` 低 48 位）= **0**。
- ⑦反例（可达 FAIL）：I1 仅去 `ra0` 恢复 ⇒ depth 用例 rc=2；I2 去 `ra0`+`ra1..ra63` 恢复 ⇒ 跨函数用例 rc=139；I3 回填错误陈述 ⇒ 注释检查 count=1>0；三者 `cp`+md5 还原后 md5 一致、回绿。
**新发现/坑**：`test-double-free`（before blocked「machine fault RASOF」）亦随本任务解锁——它经 `sigsetjmp`/`siglongjmp` 宏调用 setjmp/longjmp；旧桩下 `siglongjmp`→`abort`→SIGABRT handler→再 `siglongjmp` 递归，RACNT 达 63 触发 RASOF（**RASOF 根因即桩**）。故解锁 2 条。**披露**：`tools/testcases/picolibc_tests.py` 的 `UNSUPPORTED_TESTS["test-setjmp"]` 已删（桩已不存在，留之会把真 abort 误判 `blocked`）；`before` JSON 采自改动前的 harness、`after` 采自改动后，该改动仅影响 `test-setjmp` 的 `rc==134` 分支（其余分类逻辑不变），故 before/after 可比。
**口径修正（用户裁定 2026-10-12）**：本轮发现 `contracts/abi.yaml`（`rf32–63 callee_saved: true`，spec 事实）与 LLVM 后端 CSR（`rd32..63 ∪ rb32..63 ∪ rf32..63`）**含 RF**，而 `contract-abi §4.5` CSR 条**未列 RF** ⇒ 口径不一致（**§4.5 为偏差方**）；**用户 2026-10-12 原话「以"含 RF"为准（推荐）」** ⇒ 本次修正落点 = `contract-abi §4.5`（CSR 条追加 `∪ rf32–rf63` + 末条补「M4 起 RF 已启用 ⇒ CSR 含 `rf32–rf63`」）。
**遗留问题**：`MRPTR != 0`（MemRAS 溢出区启用）时 `jmp_buf` **不保存 MemRAS 内容** ⇒ 该类深递归 `longjmp` 不保证精确；本任务仅保证 `MRPTR == 0`（纯 RegRAS，≤63 深度）路径，已写入 `setjmp.S` 注释 + `README`。M7 环境实测 `MRPTR=0`（非生效路径）。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查 `setjmp.S`（含未测边界）：
- **寄存器约定**：`setjmp` 仅用 caller-saved scratch（`rd17/18/19`）+ 入参 `rb16`；在保存 callee-saved 前不触碰之，不改 `rsp` ✓。
- **保存/恢复对称**：`st.o ra0`↔`ld.o ra0`、`stm.o {ra1:ra63}`↔`ldm.o {ra1:ra63}`、`st.o rb1`↔`ld.o rb1`、`stm.o {rd32:rd63}/{rb32:rb63}`↔`ldm.o ...` 逐条对齐（现场 grep + objdump 核实编码）✓。
- **返回语义**：`setjmp` 用 `ret rd8, 0`(=0)；`longjmp` 保存点为「setjmp 内 `ret` 之前」，恢复整栈后 `ret` 即执行 setjmp 的返回 ⇒ 回到 setjmp 调用者 ✓。
- **`val==0⇒1`**：`cs.z rd16,rd8,rd8,rd16` + 预置 `rd8=1`，与 QEMU `trans_cs_z` 语义（`if rdha==0 rdhb=rdhc else rdhd`）逐字段对齐 ✓；负 `val` 走 else 分支原样返回 ✓。
- **顺序/基址**：恢复阶段基址恒用 `rb16`（caller-saved，未恢复），`rd17/18/19` 亦不属恢复区间（32–63）✓；SP 恢复不早于需要 `rb16` 的加载 ✓。
- **`_JBLEN=129`** 与布局（64+1+32+32）一致、8B 对齐满足 `stm.o/ldm.o` 对齐要求 ✓。
- **边界（未测）**：`MRPTR!=0` 路径不可保证——已登记为遗留（非静默）。未测 `RACNT==0` 的非法 setjmp（C 调用必有 call 帧，恒 ≥1）。
- **防造假**：所有结论均对真实 QEMU 运行输出/退出码，`objdump` 复核编码；反例均可达 FAIL 并 md5 对账。
判决：finding 0 条，无需返工；状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**（全部 reviewer 亲跑，退出码取命令本身，无 `tee` 吞码）：
- 门控：`make check`/`check-patch-tree`/`check-index-blobs`/`check-no-residue`/`check-picolibc-tests`/`check_issues.py`/`check-patch-tree --source-state` 各 rc=0。
- 证据脚本 `<evidence>/<ID>/run.sh` 基线 rc=0（ALL CHECKS PASSED）；逐项真实输出与完成区一致（t_deep `r=7`/`chain seq=123`；t_vals `val0->1`/`val5->5`/loop 10,11,12；t_depth `base 2→deep 4→after 2`；`MRPTR=0`）。
- 全量 test 亲跑 2 次均 `total=235 pass=205 fail=0 excluded=22 blocked=8`（rc=0）；与 before(203/0/22/10) 逐条对比（我自己的 JSON）：`unlocked={test-setjmp,test-double-free}`、`newly_blocked=∅`、`fail=0`、差值 **+2/−2** ✓。
- 独立最小用例（自建非 engineer 文件）：`rv_deep`（setjmp 于 level3 内、longjmp 深 3 层；自读 `ra0` RACNT **base 3→after 3**、`MRPTR=0`；后续 `ret` 链 ret-layer 1/2/3 逐层打印；rc=0）；`rv_vals`（`val0→1`/`val-3→-3`/`val5→5`/循环 10,11,12；rc=0）⇒ 语义用例 ≥4 真跑 ✓。
- 桩注释：`grep` 错误陈述 count=0（含 README）；新注释引 `contract-isa`/`存取RA寄存器`/`寄存器组之间块赋值` count=3 ✓。`_JBLEN` 66→129 属实；布局核算 64+1+32+32=129×8B=1032，偏移 0/8/512/520/776 与汇编立即数逐一对齐、8B 对齐（`stm.o/ldm.o` 要求）✓。
- 解锁核：`test-setjmp` 亲跑 rc=0/status=pass（其源码真覆盖跨函数 longjmp 与 `longjmp(env,0)⇒1`，非跳过）；`test-double-free` before=blocked「machine fault RASOF (0x8A)」，其源码经 `sigsetjmp`/`siglongjmp`+SIGABRT handler ⇒ 旧桩 `abort` 递归打满 RegRAS ⇒ RASOF，**归因成立** ✓。越界删除 `UNSUPPORTED_TESTS["test-setjmp"]` **恰当**：harness 仅对该表命中且 rc==134 判 blocked，删除后真 abort 显示 `fail`，本次真跑 exit 0、未藏入 pass ✓。
- 独立反例注入 **R4**（与 I1/I2/I3 不重复）：源树 `cs.z`⇒`set.zw rd8,wp0,1`（longjmp 恒返 1）⇒ run.sh **rc=1**（`vals` case `act=rc=2` FAIL，另 t_deep/门控同报 FAIL）⇒ `cp`+md5 还原 `217af805…` 前后相等 ⇒ 重跑 **rc=0 回绿**。
- 越界/范围核：改动集 = 声明 6 文件 + 任务书本身；`spec/contracts/tests/vectors` 零改动 ✓；`series` 18=补丁 18 ✓；组件源树 `base+1` clean ✓；完成区 14 行 ≤30 ✓。

**阻断（Needs Revision）——callee-saved 集合不完整：漏存 `rf32–rf63`（FP callee-saved）**：
- 依据：`contracts/abi.yaml` rf32–63 `callee_saved: true`（spec 事实）；LLVM 后端 `CSR = rd32..63 ∪ rb32..63 ∪ rf32..63`（`DADAORegisterInfo.cpp`/`DADAOCallingConv.td`：call-preserved mask 含 RF，M6/LLVM-066t 口径）；任务接口明写「核哪些 GPR/**FP** 寄存器跨调用保留」。本实现只存 `rd32–63`/`rb32–63`/SP/RA。
- 实证（C 级可复现，交付态两次复跑均现）：自建用例 FP 值经编译器分配活在 `rf32–63` 跨 `setjmp`，中间帧占用同 bank 后 `longjmp` ⇒ 值损坏（`expect=4.75 got=3.25`，rc=2）；**对照实验**同寄存器压力（holder 58/clobber 22 处 RF 引用）但正常返回 ⇒ rc=0 值完好 ⇒ 根因=**longjmp 不恢复 RF bank**，非 LLVM callee-save 缺陷。
- 后果：C 7.13.2.1 保证不变的非 volatile 局部量被静默改写（罕见错乱，FP 场景）。
- 修法：setjmp 增存 `rf32–rf63`（`stm.o-rf`/`ldm.o-rf` 或逐条 `st.o/ld.o`，均 `scope:fp` 已实现）、longjmp 反向恢复；`_JBLEN` 129→**161**（+32）；setjmp.S/setjmp.h 注释与 README/changelog 同步；证据脚本补 FP callee-saved 可达 FAIL 用例（我的用例模式可复用）。
- 附带（供架构师定夺，非 engineer 责任）：`contract-abi §4.5`（CSR 无 RF，M3 口径）与后端 CSR（含 RF）口径不一致，建议登记知识库口径修订。

**非阻断建议**：run.sh「RACNT restored」断言只检 rc+标记（经 t_depth rc=2 可达 FAIL，可接受）；`MRPTR=0` grep 未锚定（`MRPTR=012` 会误命中）；记录标签 `rose=1/fell=1` 与实际 `-ge 1` 判据不一致。

**判决：Needs Revision**——阻断项 = RF callee-saved（`rf32–rf63`）漏存漏复（C 级实证损坏）；其余验收项（语义、深度恢复、桩注释、解锁、全量、门控、反例、范围）经亲跑全部通过。

## 返工 1（补 RF callee-saved）engineer 处置（2026-10-12）

> 触发：第 1 轮 reviewer 判 **Needs Revision**（阻断：callee-saved 集合不完整，漏存/漏复 FP 银行 `rf32–rf63`）。本节**追加**，不改写上文。

**finding 原文要点**：`contracts/abi.yaml` `rf32–63 callee_saved: true`；LLVM 后端 CSR = `rd32..63 ∪ rb32..63 ∪ rf32..63`（call-preserved mask 含 RF）⇒ `setjmp` 必须保存/恢复 FP 银行。C 级实证：FP 局部量跨 `setjmp`、中间帧占用同 bank 后 `longjmp` ⇒ 值损坏（`expect=4.75 got=3.25`，rc=2）；同压力下正常返回 rc=0 ⇒ 根因 = longjmp 未恢复 RF 银行。

**改了什么**（仅 `components/picolibc/**`；`.work/source/picolibc` amend 为 `base+1`=HEAD `2daed25f…`）：
- `libc/machine/dadao/setjmp.S`：`setjmp` 增 `set.zw rd19, wp0, 1032` + `stm.o {rf32:rf63}, [rb16, rd19]`；`longjmp` 对称增 `set.zw rd19, wp0, 1032` + `ldm.o {rf32:rf63}, [rb16, rd19]`（RF 形态，`SimRISC-01 §3.4`，`scope:fp`）。
- `libc/include/machine/setjmp.h`：`_JBLEN` **129 → 161**。
- 注释/文档同步：`setjmp.S` 布局注释（161 布局 + CSR 依据）、`setjmp.h` 注释、`README.md` 移植要点、`changelog.md` 追加「返工 1」条。

**`_JBLEN` 算式（自算，以实际保存项为准）**：`ra0..ra63`(64) + `rsp`(1) + `rd32..rd63`(32) + `rb32..rb63`(32) + `rf32..rf63`(32) = **161** 项 × 8 B（`_JBTYPE long long`）= 1288 B；块字节偏移 0/512/520/776/1032，均 8B 对齐（`stm.o`/`ldm.o` 要求）。`llvm-objdump` 立即数 `0x8/0x208/0x308/0x408` 与之一致。

**真实输出**：
- FP 用例 `t_fp`（`f2s` 带副作用 ⇒ 8 值在 `setjmp` 前算出、跨 `setjmp` 存活于 `rf32–rf44`；`clobber` 把 base 写 `rf32` 后永不返回）：修复前（inject 去 RF）`rc=2 fp CORRUPTED expect=4.75 got=3.25`；修复后 `rc=0 fp ok expect=4.75 got=4.75`。对照 `t_fp_ctl`（同形状正常返回）恒 `rc=0` ⇒ 根因是 longjmp 未恢复 RF，非 LLVM callee-save 缺陷。
- 证据脚本 `<evidence>/<ID>/run.sh`：基线 rc=0（含 FP 用例、`_JBLEN=161`、RF 块结构断言）；`--inject` rc=0（I1..I4 各可达 FAIL，I4 = 去 RF ⇒ t_fp rc=2）。
- 全量（`--stage full`，`<evidence>/<ID>/picolibc-full-{before,after}-rf.json`）：before（= 本任务原 after，pre-RF 交付态）`pass 205 / fail 0 / excluded 22 / blocked 8` → after（RF）`pass 205 / fail 0 / excluded 22 / blocked 8`（**不回归**；`pass_regressed=∅`、`newly_blocked=∅`、inventory 同、`test-setjmp` 仍 pass）。全量命令 rc=0。
- 门控：`make check`/`check-patch-tree`/`check-index-blobs`/`check-no-residue`/`check-picolibc-tests` 各 rc=0。

**非阻断（reviewer 指出，已顺手修）**：① `MRPTR=0` 断言由无锚定 `grep -q 'MRPTR=0'` 改为锚定行尾的数值提取 + `= 0` 比较（`MRPTR=012` 不再误命中）；② 标签 `rose=1`/`fell=1` 改为 `rose>=0`/`fell>=0` 并与 `regressed=∅`/`newly=∅` 合判（标签与判据一致）。③ 另修 `run.sh` 一个真回归风险：EXIT trap 的 `cleanup()` 原会误用**上次运行残留**的 `$TMP/*.bak` 覆盖工作树（本轮实测触发一次）⇒ 改为仅 `--inject` 生效 + 启动时清残留 bak。

**登记（只登记不改）**：`contracts/abi.yaml` 与 LLVM 后端 CSR 含 RF，而 `contract-abi §4.5`（CSR 表）未列 RF ⇒ 口径不一致，交 architect/后续处理（未改 `contracts/`、`spec/`、LLVM 侧）。

**还原对账**：I4 注入 `.work/source/picolibc/.../setjmp.S` 前后 md5 一致（`3c67dbd0…`）；一律 `cp`+md5，未用 `git checkout/restore/stash`。

**改动文件（本返工轮）**：`components/picolibc/patches/libc/machine/dadao/setjmp.S.patch`、`components/picolibc/patches/libc/include/machine/setjmp.h.patch`（`_JBLEN` 161）、`components/picolibc/{README.md,changelog.md}`；组件工作树 `.work/source/<component>`（setjmp.S/setjmp.h）已 amend 为 `base+1`=HEAD `2daed25f…`；`<evidence>/<ID>/run.sh`（+`t_fp.c`/`t_fp_ctl.c`/两个 `-rf` JSON）；本任务书。
**范围披露**：`contracts/`、`spec/`、`tests/vectors/`、LLVM 侧本轮**未动**；`tools/testcases/picolibc_tests.py`（md5 `63e7740a…`）与 `.tao/knowledge/milestones.md`（md5 `2ad6344f…`）为**上轮产物、本轮保持原样**；**未提交 git**。
**遗留**：阻断项（RF）✅已修；两处非阻断 ✅已修；未修项 = **无**（`MRPTR != 0` MemRAS 限制为上轮登记项，仍成立）。

#### 第 2 轮 engineer 自审（返工 1）
**范围**：`setjmp.S`（RF 增存/复）、`setjmp.h`（`_JBLEN`）、README/changelog、`<evidence>/run.sh`（FP 用例 + I4 + 两处非阻断 + trap 修复）。
**逐项审查**：
- 布局/偏移：`ra0..ra63`(0..504)/`rsp`(512)/`rd32..rd63`(520)/`rb32..rb63`(776)/`rf32..rf63`(1032)，末项 1032+31×8=1280 < 161×8=1288 ✓；全 8B 对齐（`stm.o/ldm.o` 要求）；`llvm-objdump` 立即数 `0x208/0x308/0x408` 逐一对应 ✓。
- 对称/寄存器安全：`setjmp` 增 `stm.o {rf32:rf63}` ↔ `longjmp` 增 `ldm.o {rf32:rf63}` 对称；地址偏移寄存器恒用 caller-saved `rd17/18/19`（∉ 恢复区间 32–63），基址恒 `rb16`（∉ 恢复区间）✓；`rd19` 复用于 ra/rb/rf 三处偏移，均在用后即用、无交叉依赖 ✓。
- 语义：`rf0`（FCSR）不在块内（块自 `rf32` 起），故不误存/复 FCSR ✓；`ra0` 恢复晚于 SP/rf 恢复、`ret` 居末，`val==0⇒1` 逻辑未动 ✓。
- 防造假：所有输出对真实 QEMU 退出码；I4 注入 → 重建 → FP 用例 `rc=2`（可达 FAIL）→ `cp`+md5 还原 → 重建 → `rc=0`；反例与还原均留全日志。
- 边界（未测/已登记）：`MRPTR != 0`（MemRAS）路径不保证精确（上轮登记，非静默）；FP 用例依赖寄存器分配（`f2s` 副作用使其不可重算 ⇒ 实测确落 `rf32–rf44`，I4 可达 FAIL 反证其有效性）。
**finding 处置**：
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| B1（reviewer 阻断）RF 银行 `rf32–rf63` 漏存漏复 | ✅已修 | `setjmp.S` 增 `stm.o {rf32:rf63}`/`ldm.o {rf32:rf63}`；`_JBLEN` 161；注释/README/changelog 同步 | `objdump` 见 RF 形态编码；`t_fp` 修复后 rc=0（`expect==got=4.75`），I4 去 RF ⇒ rc=2（`got=3.25`）⇒ 还原回绿 |
| N5（reviewer 非阻断）`MRPTR=0` grep 未锚定 | ✅已修 | 改行尾锚定数值提取 + `= 0` 比较 | `run.sh` 基线 rc=0，M7 断言 act=`MRPTR=0` |
| N6（reviewer 非阻断）标签 `rose=1/fell=1` 与 `-ge 1` 不一致 | ✅已修 | 改 `rose>=0`/`fell>=0` 并与 `regressed=∅`/`newly=∅` 合判（标签=判据） | `run.sh` 基线该两条 rc=0；`pass_regressed=`/`newly_blocked=` 空 |
| F1（自审新发现）`run.sh` EXIT trap 会误用上次残留 `$TMP/*.bak` 覆盖工作树（本轮实测触发，改坏 setjmp.S） | ✅已修 | `cleanup()` 仅 `--inject` 生效 + 启动清残留 bak | 基线/注入两轮后 `.work/source` 干净、patch `rf32:rf63` 计数=2 |
**判决**：B1/N5/N6/F1 均 ✅已修，findings 无未修项；全量不回归 + 门控全绿 ⇒ 标 `待验收`。

#### 第 2 轮 reviewer 复验轮（回证 B1）

- ①RF 存/复核：`stm.o {rf32:rf63},[rb16,rd19]`（setjmp）↔ `ldm.o {rf32:rf63},[rb16,rd19]`（longjmp）对称；我自 `objdump` 核编码 `3f 81 04 e0`=stm.o-rf(0x3F)/`3e 81 04 e0`=ldm.o-rf(0x3E)，rd/rb/ra 块形态齐全；偏移 1032、块 index 129..160、四 bank 偏移 0/520/776/1032 全 8B 对齐 ✓。
- ②`_JBLEN` 我自算 64+1+32+32+32=**161**×8B=1288B；rf 末项止于 1288=缓冲区尺寸 ⇒ **无越界写**；`setjmp.S` 注释与 `setjmp.h` 均 161 一致 ✓。
- ③FP 核心：我自建 `rv_fp3`（上轮实证损坏用例）现 rc=0（`t1=4.75`）；`--inject` I4（去 RF）⇒ t_fp `expect=4.75 got=3.25` rc=2 **可达 FAIL** ⇒ `cp`+md5 还原 `3c67dbd0…` 相等 ⇒ 回绿 rc=0 ✓。
- ④全量我亲跑（`<tmp>`/r2-full-rv.json）：`235/205/0/22/8` rc=0，与 pre-RF 逐条对比 `pass_regressed=∅`、`newly_blocked=∅`、`test-setjmp` 仍 pass ✓。
- ⑤门控 `make check`/`check-patch-tree`/`check-index-blobs`/`check-no-residue`/`check-picolibc-tests` 各 rc=0；`run.sh` 基线与回绿均 rc=0 ✓。
- ⑥非阻断修复核：MRPTR 锚定提取实测（`MRPTR=012` 不再判 0；旧 grep 误命中已消）；`rose>=0,regressed=none`/`fell>=0,newly=none` 标签=判据 ✓。
- ⑦trap 修复核：`cleanup()` 仅 `--inject` 生效 + 启动 `rm` 残留 bak；**实测**植入垃圾 `.bak` 跑非 inject 轮 ⇒ 源树 md5 不变（`3c67dbd0…`）、bak 被清 ⇒「残留 bak 覆盖工作树」隐患消除；终局 `git status` 快照与开工逐行一致、6 产物 md5 对账不变（我仅写本审阅记录）✓。
- ⑧独立注入 **R5**（与 I1–I4 不重复：`stm.o` RF 块偏移 1032→**1024**，与 rb 块重叠）⇒ `run.sh` **rc=1**（`vals`/`fp` case rc=136 错乱 FAIL）⇒ `cp`+md5 还原前后相等 ⇒ 回绿 rc=0 ✓。
- ⑨**判定：Accepted**——阻断项 B1（RF 银行漏存漏复）已修且双向可证（修复后绿 / 去 RF 必红）；本轮复验项①–⑧全过；`contract-abi §4.5` 无 RF 的口径不一致维持登记（非本任务阻断，交 architect）。
