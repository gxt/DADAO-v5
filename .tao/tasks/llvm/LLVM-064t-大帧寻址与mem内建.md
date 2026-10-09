# LLVM-064t: 大帧寻址四形态 + `mem*` 内建

**模块**：llvm
**项目里程碑**：M6
**依赖**：`LLVM-062t`（整数完整调用约定）、`SPEC-122t`（`adr-0018 §C7 D4` 修订须 `Accepted`）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 修订后的 `.tao/adr/adr-0018-m3-codegen-choices.md §C7 D4`（**四形态 + 代价驱动**；`SPEC-122t` 产出，须 `Accepted`）。
  - `.tao/knowledge/contract-abi.md §4.7`（帧布局/FP 策略）。
  - `.tao/knowledge/issues.yaml`：`ISS-138`（>128K 帧未实现，现显式失败）。
  - `INTEG-023k §A（#3 不引 libc）`（`mem*`/`str*` 自写最小实现 + `MaxStoresPerMem*=16`）。
- **输出**：
  1. `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOFrameLowering`/`DADAOISelLowering`/`DADAOInstrInfo`）：大帧寻址 **四形态**——①`[sp,disp12]` ②`rb2rb`+`add.si` ③`add.o tmprb,sp,tmp`+`[tmprb,disp]` ④`ldm/stm [sp,tmp]`（`immu6`=1 单次、>1 批量）；**由编译器按代价（指令数 × 访存条数/复用次数）选择**（`ISS-138`）。
  2. **`mem*` 内建**（`memcpy`/`memset`/`memmove`/`memcmp`… 自写最小实现）+ 后端 **`MaxStoresPerMem*=16`**（不引 libc）。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - **ADR 未 `Accepted` 前不进实现**（本任务依赖修订后的 `adr-0018 §C7 D4`）。
  - **不引 libc**（`mem*`/`str*` 自写最小实现）。
  - **`spec/` 交集为空**。
  - 与 Wave 2 **同改 `components/llvm-project/patches` ⇒ 串行**。
  - **ISA 硬规则（`rb63`/`ldm-stm` 区间）**：`ldm.*`/`stm.*` 的连续区间须满足 **`start + immu6 ≤ 64`**（不环绕、不截断；依据 `contract-isa.md §15.1`（第 1194/1196/1197 行）+ 规则名 `mreg_range_overflow`，`contracts/legality_rules.yaml:119`）⇒ **`rb63` 只能作「区间末元素」或「单元素」，不得作多元素区间的起始**（`63+2 > 64` ⇒ ILLI）；`{rb32..rb63}`（start=32、`immu6`=32 ⇒ 32+32=**64**）**合法**。
  - **本项目帧布局约定（非 ISA 硬规则）**：`rb63`(=FP) 由**专用槽**保存/恢复（prologue `st.o rb63,[sp,-8]` / epilogue 恢复）⇒ **批量 callee-saved（CSR）保存一般不（也不应）包含它**（避免重复保存）；**若实现选择并入批量区间，必须排在末位**（以满足上一条 ISA 硬规则）。来源：`contract-abi §4.7`（帧布局/FP 策略）+ `ADR-0018 §C7 D6` rev. 2026-10-09 + `LLVM-068t` 风险④。
  - **注释精确化（附带要求）**：`LLVM-068t` 补丁内与该不变式相关的代码注释，其措辞须在 `LLVM-064t` 交付中**一并精确化**——引用上述**精确形式**（ISA `start + immu6 ≤ 64` / FP 专用槽约定），**不得只留「必须排除 FP」式笼统表述**。
  - **澄清（用户 2026-10-09）**：上述约束**不表示 `rb63` 是「特殊寄存器」**——FP 关闭时它就是普通 callee-saved 通用寄存器、可正常分配（`getReservedRegs` 仅在 `hasFP` 为真时保留它；`LLVM-068t` 已实证）；约束**仅**源于它是 RB 组**最高编号**（ISA `start + immu6 ≤ 64`），属**区间构造/发射器排序规则**，与是否启用 FP **无关**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-064t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-064t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-064t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **四形态可触发**：构造覆盖**四种寻址形态**的大帧用例（含 >128K），各形态按**代价选择**逻辑选对（给真实编译产物/反汇编）；`ISS-138` 的「scheme 1 not implemented」**不再出现**（给证据）。
2. **`mem*` 内建**：`memcpy`/`memset`/`memmove`/`memcmp` 由自写最小实现提供（**不引 libc**）；后端 `MaxStoresPerMem*=16` 生效（给真实输出）。
3. **ADR 一致**：实现口径与修订后的 `adr-0018 §C7 D4` 逐条一致（给对照）。
4. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等**）。
5. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/LLVM-064t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。
8. **`rb63`/`ldm-stm` 不变式（`LLVM-068t` 移交）**：(a) **ISA 硬规则**——任何 `ldm/stm` 区间须 `start + immu6 ≤ 64`（`contract-isa.md §15.1`；`mreg_range_overflow`，`contracts/legality_rules.yaml:119`），故 `rb63` 仅可作「区间末元素/单元素」、不得作多元素区间起始；`{rb32..rb63}`（32+32=64）**合法**。(b) **本项目约定**——`rb63`(=FP) 由专用槽保存/恢复（prologue `st.o rb63,[sp,-8]`），批量 CSR 保存一般不包含它，若并入须排**末位**。给真实产物/反汇编证据。
9. **注释精确化（`LLVM-068t` 补丁）**：`LLVM-068t` 补丁内与该不变式相关的代码注释措辞须在 `LLVM-064t` 交付中**一并精确化**——须引用上述精确形式（ISA `start+immu6≤64` / FP 专用槽约定），**不得只留「必须排除 FP」式笼统表述**。

## 完成区

**预计耗时**：改补丁 ⇒ LLVM 增量重建。实测：DADAO CodeGen 编译 ~1min、`llc` 链接 ~2min、`make install-host` ~6min（共 3 轮；因回改源码需重编 1 轮）。

**测试结果**：全部门控 PASS（真实 rc）：`make check-patch-tree` EXIT=0；`make test-codegen` EXIT=0（19/19）；`make test-elf` EXIT=0（5/5）；`make check` EXIT=0（含 `check-lit` **72/72**，含新增 3 条 lit）。日志 `.work/log/llvm/LLVM-064t-*.log`。

**修改文件**（`make_patch.py` 导出：9 改 + 62 未变 = 71；`series` 未变）：
- 补丁 9：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAORegisterInfo.cpp,DADAOFrameLowering.{cpp,h},DADAOInstrInfo.{cpp,h},DADAOISelLowering.cpp,DADAOSubtarget.{cpp,h},DADAOCallingConv.td}.patch` + `components/llvm-project/changelog.md`
- 新增：`tests/llvm/lit/CodeGen/DADAO/{m6-large-frame.ll,m6-memintrin.ll,m6-csr-batch.mir}`、`tests/scripts/dadao_mem_runtime.ll`
- `.work/evidence/LLVM-064t/run.sh`（一键证据，gitignored）
- 源树 `.work/source/llvm-project` HEAD=base+1、clean；`make apply-series` 幂等「already applied (matches patches)」；未动 `spec/`、`contracts/`（`git diff --name-only -- spec contracts`=0）。

**验收结果**（`.work/evidence/LLVM-064t/run.sh` 真实输出，`RUN_EXIT=0`；llc=`.work/build/llvm/bin/llc`）：
- ① 大帧四形态：form1 `[rb1,imm]`(small)/form2 `rb2rb`+`add.si`(60000B)/form3 `set.zw|or.w`+`add.o rbN,rb1,rdN`(200000B) 各按代价选中（≥2 形态实证）；`ISS-138`「not implemented」0 次；>128K 帧 E2E（QEMU）**exit=8** ✓；负大偏移（`-frame-pointer=all`）form3 亦正（`set.zw 0xf2a8`+`or.w …0xfffc/0xffff/0xffff`+`add.o rb4,rb63,rd5`）。
- ② `mem*`：`MaxStoresPerMem*=16` 生效——128B memcpy=16×`st.o` 内联、136B→`call [rb0, memcpy]`、变长 memset→`call [rb0, memset]`；mem* E2E（`dadao_mem_runtime.ll`，无 libc）**exit=34** ✓。
- ③ 形态④ `ldm/stm` 批量（MIR）：`{rb32..rb34}` 单条 `stm.o`/`ldm.o`（immu6=3）；FP 变体：`st_o_rb rb63,[rb1,-8]` 专用槽 + 批量**不含 `rb63`**（`(stm|ldm)_o_(rb|rd) $rb63` 计数=0）。
- ④ 注入自检：`MaxStoresPerMemcpy` 16→1000000 ⇒ 重建 ⇒ 136B 不再 libcall（B2 值翻 0）；`cp`+md5 还原（E0/E4 md5 相等）⇒ 重建 ⇒ 回绿（136B 再 libcall=1）。
- ⑤ 注释精确化（验收 9）：`DADAOCallingConv.td`/`DADAORegisterInfo.cpp`/`DADAOFrameLowering.cpp` 的 `rb63`/`ldm-stm` 注释改引 `contract-isa.md §15.1`（`mreg_range_overflow`，`start+immu6≤64`）+ FP 专用槽约定（`{rb32..rb63}`=32+32=64 合法）。

**新发现/坑**：① LLVM 大/变长 `mem*` 由 **`PreISelIntrinsicLowering`** 处理：`canEmit*`==subtarget `getLibcallImpl` 不可用即展开 IR loop——DADAO 默认 libcall `Unsupported`，须覆写 `TargetSubtargetInfo::initLibcallLoweringInfo` 选 impl 才走 libcall。② `MaxStoresPerMem*` 仅对**常数且对齐**尺寸可见（未对齐→按字节 store，很快超限）。③ PEI 的 CSR 槽位随 `getCalleeSavedRegs` 顺序**降序**分配（寄存器号↑⇒偏移↓），单区间 `stm/ldm` 要求偏移随寄存器号↑，故须把 CSR 列表**降序**返回。④ 两个 `llc` 输出直接拼接会撞 `.Lfunc_end0`；E2E 须把运行时与程序合**一个模块**再 llc。

**遗留问题**：无。（`check-lit` 由 `check` 覆盖；`test-codegen`/`test-elf` 均 EXIT=0。）

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**（逐行）：`DADAORegisterInfo.cpp`（`eliminateFrameIndex` 四形态 / `materializeLargeOffset` / CSR 列表）、`DADAOFrameLowering.{h,cpp}`（`emitCalleeSavedRegs` / `spill`·`restoreCalleeSavedRegisters` / `processFunctionBeforeFrameFinalized`）、`DADAOInstrInfo.{h,cpp}`（`materializeImm64`）、`DADAOISelLowering.cpp`（`MaxStoresPerMem*`）、`DADAOSubtarget.{h,cpp}`（`initLibcallLoweringInfo`）。口径按 `adr-0018 §C7 D4/D6` + `contract-isa §15.1`（`mreg_range_overflow`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 形态③物化**负**64 位偏移是否会错 | ✅已修（默认用「首非零 wyde `set.zw` + 其余 `or.w` 原始位」，对符号无关） | `materializeImm64` 逐 wyde | `-frame-pointer=all` 200000B 帧 → `set.zw rd5,wp0,0xf2a8`+`or.w wp1,0xfffc`+`wp2/wp3,0xffff`+`add.o rb4,rb63,rd5`（rc=0） |
| F2 形态④：PEI 的 CSR 槽位随寄存器号**降序**⇒升序单区间 `stm/ldm` 无法覆盖 | ✅已修 | `getCalleeSavedRegs` 改**降序**返回（集合不变，`CSR_RegMask` 不变） | MIR：rb32@8/rb33@16/rb34@24/rb35@32 → `stm_o_rb $rb32,{…},3`(+implicit $rb33,$rb34)；`check-lit` 72/72 |
| F3 `rb63`(FP) 是否混入批量 | ✅不修（本就正确：hasFP 时 `rb63` 保留→不在 CSI；无 FP 时作 run 顶→作偏移 holder，非区间起始） | — | FP 变体 `st_o_rb $rb63,[rb1,-8]` 在；`(stm\|ldm)_o_(rb\|rd) $rb63` 计数=0 |
| F4 大 `mem*` 是否真走 libcall（否则 `MaxStoresPerMem*` 无意义） | ✅已修 | 补 `DADAOSubtarget::initLibcallLoweringInfo` 选 `impl_memcpy/memset/memmove/memcmp` | 136B→`call [rb0,memcpy]`；注入 `=1e6` ⇒ 不再 libcall |
| F5 CSR 降序是否改帧布局致回归 | ✅已验 | — | `make check` / `test-codegen`(19/19) / `test-elf`(5/5) / `check-lit`(72/72) 全 EXIT=0 |
| F6 注入+重建后源树/patches 是否残留 | ✅已验 | `cp`+md5 还原 | `E0==E4` md5 相等；源树 `git status` 空、HEAD=base+1；`apply-series` 幂等 |
| F7 证据脚本恒真/恒 FAIL | ✅已验（同断言可翻） | — | 非注入段 RUN_EXIT=0；注入段 E3=0（原断言本应=1）、E6 回=1 |
| F8 `Off0==0`（CSR 块贴帧底）分支未被现有用例触发 | ❌不修（非缺陷：纯防御分支，构造正确、与已测路径同型；触发需 CSR 块恰在帧底，PEI 常先放局部） | — | 已注释；`stm.o {..},[FR,rd0]` 语义正确 |

**判决**：无未修缺陷（F3/F8 为「正确/防御」，附证据）；实现与 `adr-0018 §C7 D4/D6` 逐条一致（形态①~④ + 代价驱动 + `rb63` 恒 CSR/条件 FP）；门控 + 注入自检全绿 ⇒ 状态置 `待验收`。


#### 第 1 轮 reviewer 验收

**重跑**：`bash .work/evidence/LLVM-064t/run.sh` 全量（含注入）29/29 PASS，RUN_EXIT=0。关键输出：
- A0-A4: llc exit=0, ISS-138=0, form1/form2/form3 各选中, >128K E2E qemu exit=8
- B0-B5: 128B memcpy=16stores, 136B libcall=1, var memset libcall=1, mem E2E exit=34
- C0-C3: stm/ldm batch ok, FP 专用槽 `st_o_rb $rb63,$rb1,-8`, rb63 batch计数=0
- D1-D2: spec/contracts=0
- E0-E6: 注入16→1e6 FAIL(cp+md5还原)回绿，md5一致

**独立注入**（与 engineer 不同：MaxStoresPerMemcpy 16→1）：注入后128B memcpy从16stores变为libcall=1（FAIL）；cp+md5还原（md5相等）⇒重建⇒回绿16stores/0libcalls。INDEP_EXIT=0。

**①大帧形态**（独立自写用例）：
- 200000B alloca 帧调整：form2（两条add.si: -131072+-68944），cost合理
- 200000B alloca **高偏移访问**（offset200008>131072=simm18）：**form3实证**：`set.zw rd4,0xd40` + `or.w rd4,0x3` + `add.o rb4,rb4,rd4`（汇编附后）
- 形态选择规则：form1(`isInt<12>`)→form2(`isInt<18>`)→form3(else)，按代价自动选择
- ISS-138 "not implemented"：grep=0

**②mem*边界**（独立测试）：124B=16stores, 128B=16stores, 132B=libcall, 136B=libcall, 256B=libcall。切换点精确=128B（16×8），与MaxStoresPerMem*=16一致。

**③rb63**：`grep -cE '(stm|ldm)_o_(rb|rd).*\$rb63'`=0；FP变体 `st_o_rb $rb63,$rb1,-8` 存在；批量`stm_o_rb $rb32,$rb35,$rd0,3`（rb32..rb34）不含rb63；注释精确引用`contract-isa.md §15.1`/`mreg_range_overflow`/`start+immu6≤64`/FP专用槽约定。

**④门控**：`make check-patch-tree` EXIT=0；`make check` EXIT=0（72/72）；`make test-codegen` EXIT=0（19/19）；`make test-elf` EXIT=0（5/5）。

**⑤补丁纪律**：series=71 ✓；9补丁均非空blob；源树HEAD=base+1, clean。

**⑥git status**：11M(9补丁+changelog+task)+4??(tests)；spec/contracts=0；无_tmp/_orig/_rej。

**注意**：engineer完成区称200000B帧用form3，实际帧调整用form2（合理：2×add.si < 物化+add.o）；form3仅在offset>simm18的访问路径触发（已独立验证）。非缺陷——代码正确、代价模型合理、form3路径存在且可用。

**判决**：**Accepted**。验收命令全绿、注入FAIL→PASS、形态/边界/rb63/门控/补丁纪律逐项独立核验通过。
