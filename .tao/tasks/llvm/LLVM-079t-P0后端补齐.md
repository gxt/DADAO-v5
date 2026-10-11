# LLVM-079t: P0 后端补齐（FP 载入/取值/bitcast/select_cc/cttz）

**模块**：llvm
**项目里程碑**：M7
**依赖**：无（M6 已验证态；`INTEG-033k` 裁定 #4）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #4`）：**P0 后端纳入 M7** = ① `f32→f64 anyext` 载入 ② FP 比较取值 **`setcc`** ③ `f64↔i64 bitcast` ④ `f64 select_cc` ⑤ `i64 cttz`；**优先用 ISA 现成指令**（如 `ft2fo`）。
  - 缺口证据（**实测，非估算**）：`.work/log/testcases/picolibc-probe-summary.log`——341 个 picolibc test 编译探针中 **64 个 `BACKEND_CANNOT_SELECT`**，其 **distinct node 签名** = `f64,ch = load …`（40，= `f32→f64` anyext 载入）/ `i64 = setcc … ConstantFP:f64`（16+1+1）/ `i64 = cttz`（1）/ `i64 = bitcast`（1）/ `f64 = bitcast`（2）/ `f64 = select_cc … setlt`（1）。另见 `.work/log/testcases/picolibc-probe-fp.log`。
  - `ISS-188`（FP 完备性缺口）；`contract-fp.md`（FP/RF 指令）；`contracts/opcodes.yaml`（scope `fp`）——FP 指令已实现于 MC/QEMU。
- **输出**：
  1. DADAO 后端 ISel 补齐 5 类 P0 模式：范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOISelLowering.cpp`/`DADAOInstrInfo.td` 等），**优先复用 ISA 现成指令**（FP↔RD 转换/位操作已有指令，如 `ft2fo`/`rf2rd`/`rd2rf` 等，**以 `contracts/opcodes.yaml`/`contract-fp.md` 为准**）。
  2. lit / CodeGen 用例：新增覆盖 5 类模式（**期望值独立派生自 `spec`/`contracts`，禁从 `llc` 反填**）。
  3. 重建工具链（改 `components/llvm-project/patches` ⇒ 须重建；`setsid` 脱离、`JOBS=8`、`lessons §8.21`；**启动前申报预计耗时**）。
- **约束**：
  - **最小改动**：只补 P0 五类；**P1（取整/min-max/fabs/copysign）归 `LLVM-080t`**。
  - **`ft2fo` 等 ISA 现成指令优先**，不自造 lowering；无 ISA 依据的形态须显式登记。
  - **计数不写死**：探针/门控计数**现场统计**；验收写「P0 类清零」而非固定条目数。
  - 只动任务范围，越界须披露。

## 验收标准

1. **P0 类清零**：以**同一 picolibc 编译探针脚本**重跑（`.work/log/testcases/picolibc-probe-compile.sh` 及其产物 `picolibc-probe-compile-table.tsv`）——**`BACKEND_CANNOT_SELECT` 中 P0 类签名（load-anyext / setcc / bitcast / select_cc / cttz）全部清零**（现场统计真实输出；**非抽样、非估算**）。
2. **语义 E2E**：至少 1 个真实 picolibc test（P0 相关，如 `test/test-math/*` 或 `test/test-stdio/test-fprintf-*`）编/链/跑出正确退出码（QEMU semihosting）。
3. **ISA 现成指令证据**：P0 类生成的汇编中出现预期 ISA 指令（`llc -march=dadao -S`，逐类给出真实片段）。
4. **门控**：`make check`、`make check-lit`（或等价的 lit 全量档）**EXIT=0**；`check-patch-tree` EXIT=0。
5. **反例门控**：新增 lit 用例**能失败**（注入错误期望值 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：通过 **全部**。`make check` rc=0；`make check-lit` **95/95** rc=0（含新增 5 个 `p0-*.ll` + 1 个 e2e）；`check-patch-tree` rc=0（123 patches）；`check-index-blobs` rc=0；`check-no-residue` rc=0；一键证据 `.work/evidence/LLVM-079t/run.sh` **rc=0**（含注入自检：注入 rc=1 → `cp`+md5 还原 → 回绿 rc=0）。无失败项。

**修改文件**（仅本任务范围）：
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOCodeGen.td.patch`
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfoFP.td.patch`
- `tests/llvm/lit/CodeGen/DADAO/p0-fp-load-extend.ll`（新）、`p0-fp-setcc.ll`（新）、`p0-fp-bitcast.ll`（新）、`p0-fp-selectcc.ll`（新）、`p0-cttz.ll`（新）
- `tests/e2e/p0_fp_e2e.c`（新）+ `tests/e2e/lit/p0_fp_e2e.test`（新）
- `.tao/knowledge/milestones.md`（`LLVM-079t` 行 → `待验收`）
- 证据/日志（非 git）：`.work/evidence/LLVM-079t/run.sh`、`.work/log/llvm/`、`.work/log/testcases/picolibc-probe-compile-*-after.*`

**验收结果**（逐条，与真实输出对齐）：
1. **P0 类清零**：同脚本重跑（`bash .work/log/testcases/picolibc-probe-compile.sh`，rc=0，**41s**）→ **341 probed / 327 OK / `BACKEND_CANNOT_SELECT`=0**（前：261/64）。新全量日志 `picolibc-probe-compile-full-after.log` 中 `Cannot select` 行 **0**、distinct 节点签名 **0**；TSV 首错文本中 5 类 P0 形态（`anyext from f32`/`= setcc`/`= bitcast`/`= select_cc`/`cttz`）命中 **0**。剩余非 OK = 12 `FRONTEND_ERR` + 1 `MISSING_HDR` + 1 `BACKEND_OTHER`（均非后端）。
2. **语义 E2E**：真实 picolibc `test/test-math/test-add.c` 编/链/跑 → QEMU semihosting **guest rc=0**；另 `tests/e2e/p0_fp_e2e.test`（真实 CR=全 5 类）lit PASS。
3. **ISA 指令证据**（`llc -march=dadao -S`，逐类真实片段）：① `ld.t rf2,[rb4,0]`+`ft2fo {rf3},{rf2}`；② `foqcmp`+`cs.n/cs.z`（f32 走 `ftqcmp`）；③ `rf2rd {rd8},{rf16}` / `rd2rf {rf8},{rd16}`；④ `cmp.si rd4,rd16,0`+`cs.n {rd4}?,rf8,rf16,rf17`；⑤ cttz 展开为 `xnor.o/and.o/sub.uo/shr.uo/mul.uo`（**无 call**）。
4. **门控**：`make check` / `make check-lit`（95/95）/ `check-patch-tree` / `check-no-residue` 全 EXIT=0。
5. **反例门控**：注入错期望值（`p0-fp-bitcast.ll` 的 `rf2rd`→`rf2rdXX`）⇒ lit **rc=1 FAIL** ⇒ `cp`+md5 还原（md5 `4f6b40…` 一致）⇒ 回绿 **rc=0**。
6. **无残留**：`git status --porcelain -uall` 仅本任务 3 个补丁 + 7 个新测试 + 1 个 `milestones.md` 行（另有 2 个**非本任务**的未跟踪任务书，见「遗留」）；无 `*_tmp*`/`*.orig`/`*.rej`。

**新发现/坑**：
- **`ft2fo` 等 convert_ff 的目的/源寄存器范围不得重叠，否则 ILLI（`0x88`）**（`contract-fp.md §2`）。修 gap1 后 RA 合并出 `ft2fo {rf2},{rf2}` ⇒ E2E guest rc=**136**（=0x88 ILLI）；对 4 条 convert_ff 加 `@earlyclobber $rb`（`DADAOInstrInfoFP.td`）后正确（rc=0）。**这是既有隐藏缺陷**（任何 `fpext(fptrunc)` 路径都可能踩到），非本任务引入。
- **`DAGCombiner::visitFP_EXTEND` 会把 `fpext(load f32)` 折成 f64 anyext 载入**（因 `(f64<-f32) EXTLOAD` 默认 Legal）——该节点既不可选、语义也不等于 fpext；须显式标 `Expand`（同 AMDGPU/LoongArch/PPC/CSKY 做法）。
- **ISA 无 bit-scan/popcount 指令**（`contracts/opcodes.yaml` 227 条无 cttz/ctlz/ctpop）⇒ cttz/ctlz/ctpop 走通用软件展开（纯 i64 移位/与或/乘，**无 libcall、无常量池**）。
- `probe-full.log` 由探针脚本 **append**（不 truncate）⇒ 分析必须用 TSV 或重新生成的 fresh 日志，否则会读到前次运行残留。
- 探针脚本产物落 `/tmp`；仓库内 `picolibc-probe-compile-table.tsv` 为**前态**基线，后态另存 `*-after.*`。

**遗留问题**：
- **无序族 FP 谓词**（`SETUO`/`SETUNO`/`SETONE`/…，即 `isnan`/`fpclass`）在 SETCC/SELECT_CC 路径仍 `report_fatal_error`（BR_CC 路径亦然：`test/testsuite/newlib.math/dcvt.c` = 探针唯一 `BACKEND_OTHER`）。**P0 五类之外**（`ISS-188`），未动；如需支持应另行立项。
- 探针剩余 12 `FRONTEND_ERR`（缺 `COMMAND_LINE`/`MAXPATHLEN`/`TEST_FUNC`/TLS 等）+ 1 `MISSING_HDR`（`pthread.h`）与后端无关。
- picolibc 全量 test 的**链接**仍受 `INFRA-057t` sysroot 源过滤（`__heap_end`= `ISS-191`、`vfscanf`/`cacosf` 等缺符号）限制 ⇒ E2E 只选到可链者（`test-add.c`）；`LLVM-079t/080t` 落地后按 `ISS-188` 删表恢复全量属 `TESTCASES-042t`。
- `git status` 另有 2 个**非本任务**未跟踪任务书（`.tao/tasks/infra/INFRA-065t-*.md`、`.tao/tasks/spec/SPEC-134t-*.md`），非本任务产生，未动。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查 + 真实复验）

改动 4 处（`DADAOISelLowering.cpp`：extload Expand / FP SETCC·SELECT(_CC) Custom / cttz 族 Expand / `Select` 结果类型动态；`DADAOCodeGen.td`：`SDT_DADAOCS` 约束放宽 + FP 臂 `cs.*_rrrr_rf` 6 patterns + bitcast 2 patterns；`DADAOInstrInfoFP.td`：4 条 convert_ff `@earlyclobber`）。逐行核对结论：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `SDT_DADAOCS` 由「result==cond==两臂 且 int」放宽为「result==两臂；cond 必须 i64」——须确认无第二类生产者 | ✅已修（本就成立） | 用 `SDTCisVT<1,i64>` 钉住 cond 类型（去掉 `SDTCisInt<0>` 以容纳 FP 臂） | 仅 `LowerCmpSelect`/`LowerSELECT` 产生该节点，cond 恒为 i64；`make check-lit` 95/95 |
| `Select` lambda 原硬编码 `MVT::i64` 结果类型 → FP 臂会类型不符 | ✅已修 | 改为 `T.getValueType()`（两臂同型）；`LowerSELECT` 用 `Op.getOperand(2).getValueType()` | `p0-fp-selectcc.ll` 4 例 PASS；E2E guest rc=0 |
| `fpext(load f32)` 折成 anyext 载入（不可选 + 语义错） | ✅已修 | `setLoadExtAction(ISD::EXTLOAD, MVT::f64, MVT::f32, Expand)` | `p0-fp-load-extend.ll` PASS；probe 该签名 40→0 |
| **`ft2fo {rfN},{rfN}` 撞 ISA overlap→ILLI(0x88)**：自审发现的运行时缺陷（E2E 首跑 rc=136；单例 `g1` 复现 136，改不同目的寄存器后 rc=0） | ✅已修 | `ft2fo/ft2ft/fo2ft/fo2fo` 加 `Constraints="@earlyclobber $rb"` | `ft2fo {rf3},{rf2}`；`make check-lit` 95/95；E2E rc=0 |
| cttz 无 ISA 指令：确认走通用展开而非 libcall/常量池 | ✅已修（按此实现） | `CTTZ/CTTZ_ZERO_POISON/CTLZ/CTLZ_ZERO_POISON/CTPOP` → `Expand` | `p0-cttz.ll` `CHECK-NOT: call`+`mul.uo` PASS；E2E 汇编 `call=0` |
| P1（取整/min-max/`fabs`/`copysign`）**未顺手做** | ❌不修（越界） | — | 仅加 bitcast（P0 ③）后 `fabs`/`copysign` 因泛化展开可能顺带可用；未加任何 P1 专属 pattern/action |
| `DADAOFPSelCC` multiclass（FP-cmp+FP 臂 selectcc）在 SELECT_CC 转 Custom 后是否成为死代码 | ❌不修（保留 = 必要兜底） | 未动 | legalize 后的 DAGCombiner 仍可产生 `selectcc`（`isOperationLegalOrCustom` 为真）而 ISel 不再回调 Custom ⇒ 该 pattern 是唯一兜底，**非死码**；`p0-fp-selectcc.ll::sel_fp_lt` 覆盖该形态 |

判决：所有 finding 已修/已核定；无未修项，可标 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（全部独立执行，未采信 engineer 输出）：

| 项 | 命令 | rc | 备注 |
|---|---|---|---|
| make check | `make check; echo rc=$?` | 0 | spec drift/patch-tree/index-blobs/no-residue/components 全 PASS |
| make check-lit | `make check-lit; echo rc=$?` | 0 | 95/95（含 5 个 p0-*.ll + p0_fp_e2e） |
| check-patch-tree | `make check-patch-tree; echo rc=$?` | 0 | 4 组件 123 patches（断言⑥⑨均过） |
| check-index-blobs | `make check-index-blobs; echo rc=$?` | 0 | 88 new-file OK |
| check-no-residue | `make check-no-residue; echo rc=$?` | 0 | |

**探针独立重跑**：重跑 `<probe-compile.sh>`（rc=0，TSV `:>` 截断，fresh）→ **341 probed / 327 OK / BACKEND_CANNOT_SELECT=0**（前 64）；P0 五类签名（`anyext from f32`/`= setcc`/`= bitcast`/`= select_cc`/`cttz`）在非 OK 行**命中 0**；剩余 12 FRONTEND_ERR + 1 MISSING_HDR + 1 BACKEND_OTHER（dcvt.c 无序族）均非后端。

**lit 期望值独立性**：3 条抽样推导——① `p0-fp-load-extend.ll` CHECK `ld.t`+`ft2fo`：contract-fp.md §11 rf_mem（`ld.t` 4B float load）+ §2 convert_ff（`ft2fo` f32→f64）；② `p0-fp-setcc.ll` CHECK `foqcmp`+`cs.z`：§8 compare（`foqcmp` quiet compare f64）+ §10 cs_rf（`cs.z` conditional）；③ `p0-cttz.ll` CHECK-NOT `call` + CHECK `mul.uo`：ISA 227 条无 cttz/ctlz/ctpop（opcodes.yaml），Expand 走通用软件展开，最终 mul.uo 来自 contract-isa.md §6.1.4。**独立注入**：`p0-fp-setcc.ll` 改 `cs.z`→`cs.zXX`（不与 engineer 的 rf2rd→rf2rdXX 重叠）→ lit rc=1 FAIL → `cp`+md5 还原（md5 `fc6cf57…`= `fc6cf57…`）→ lit rc=0 回绿 ✓。

**ISA 指令证据**（独立 `llc -march=dadao -O2 -S`）：① gap1：`ld.t rf1,[rb16,0]` + `ft2fo {rf8},{rf1}` ✓；② gap2：`foqcmp rd4,rf16,rf17` + `cs.z`/`cs.n`（f32 走 `ftqcmp`）✓；③ gap3：`rf2rd {rd8},{rf16}` + `rd2rf {rf8},{rd16}` ✓；④ gap4：`cmp.si rd4,rd16,0` + `cs.n`，`cmp.ui rd4,rd16,0` + `cs.z`，`foqcmp` + `cs.n`（FP compare select）✓；⑤ gap5：cttz call=0（无 libcall），展开含 `xnor.o`/`and.o`/`shr.uo`/`mul.uo` ✓。

**越界 `@earlyclobber` 判定**：contract-fp.md §2 L34 "源范围与目的范围不可有任何交集（含完全重合），否则 → ILLI"；`ft2fo {rf2},{rf2}`（immu6=1，完全重叠）硬件抛 0x88（E2E rc=136 证实）。`@earlyclobber $rb` 仅加于 4 条 convert_ff（`ft2fo`/`ft2ft`/`fo2ft`/`fo2fo`），**P0 必需**且**最小**（不涉及 arith §5 等"先读后写"族）。✓

**E2E 独立重跑**：test-add.c 编/链/跑 → QEMU guest **rc=0**；`p0_fp_e2e` lit **rc=0** ✓。

**补丁纪律**：25 个 DADAO 补丁均非空（63–1515 行）；`.work/source/llvm-project` HEAD = `a1c6dfa9`（base `6dfe1677a` +1）✓；check-patch-tree 断言⑥（blob 一致性）⑨（HEAD diff == patch set）已由门控 rc=0 覆盖。

**遗留登记**：ISS-188 notes 已含 "fpclass ⇒ `setcc setuo`"（无序族 SETUO/SETUNO 等）；dcvt.c `BACKEND_OTHER`（"unsupported floating-point branch condition"）属同一缺陷族，ISS-188 承载 ✓。

**约束核验**：
- P0 五类清零 ✓（探针 0）
- ISA 现成指令优先 ✓（ft2fo/foqcmp/ftqcmp/rd2rf/rf2rd/cmp.si/cs.*）
- 计数现场统计 ✓（未写死）
- 只动任务范围 ✓（`git status` 对账一致，无越界文件）
- 无残留 ✓（无 `*_tmp*`/`*.orig`/`*.rej`）

**判定：Accepted**。无阻断项。非阻断建议：可考虑对 cttz 展开做 `CHECK-NOT: constant-pool` 补充断言（当前只 CHECK-NOT `call`，未来如有常量池路径会漏检）。主会话可执行 `/complete`。

### 第 1 轮 architect 提交与文件集审核

**档位**：正常提交（reviewer 判 `Accepted`）。
**交叉复核**（architect 独立重跑）：`make check` rc=0；`make check-lit` **95/95** rc=0；`check-patch-tree`（123 patches）rc=0；`check-index-blobs`（88 new-file）rc=0；`check-no-residue` rc=0；`check_issues.py` rc=0。任务书 `**状态**：已验证`。
**台账**：`ISS-188.notes` **追加**（既有正文未改）「P0 五类已由 `LLVM-079t` 收口（探针 `BACKEND_CANNOT_SELECT` 64→0）；剩余 P1 归 `LLVM-080t`；无序族 FP 谓词（`SETUO`/`isnan`）与 `dcvt.c` `BACKEND_OTHER` 仍缺」；`check_issues.py` rc=0。`milestones.md` `LLVM-079t` 行 → `已验证` + 完成时间 `2026-10-11 23:07`（= 落地提交时间，单行）。
**文件集对账**（`git diff --cached --name-status`）：**6 M + 7 A = 13** —— 3 补丁（M）+ 5 个 `p0-*.ll`（A）+ `p0_fp_e2e.c`/`p0_fp_e2e.test`（A）+ `milestones.md`（M）+ `issues.yaml`（M，本次收尾台账追加，非完成区列项，属授权收尾）+ 本任务书（M）。**7 个新测试全提**；与完成区「修改文件」一致，**无漏提/多提/越界**。**排除** 2 份并行任务书（`INFRA-065t`/`SPEC-134t`）与非 git 目录（`<工作区>`/`<缓存>`）。
**落地**：分支 `LLVM-079t` 提交 `3a5e117`；`master` `merge --squash` → 提交 `8812fe1`；分支已删。**未 push**（`origin/master..HEAD` = 1）。
