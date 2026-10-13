# LLVM-080t: P1 后端补齐（取整 / fmin-fmax / fabs-copysign 双精度）

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-079t`（P0；同改 `components/llvm-project/patches` ⇒ 串行）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #6`）：**P1 后端纳入 M7** = `floor`/`ceil`/`trunc`/`round`/`rint`/`nearbyint`、`fmin`/`fmax`、`fabs`/`copysign`（**双精度**）。
  - 缺口证据（实测）：`.work/log/testcases/picolibc-probe-fp.log`——`floor_d/ceil_d/trunc_d/round_d/rint_d/nearbyint_d` = `NOLIBCALL`；`fmin_d/fmax_d` = `NOLIBCALL`；`fabs_d/copysign_d` = `CANNOT_SELECT`（`bitcast`）。`ISS-188`。
  - `contract-fp.md`、`contracts/opcodes.yaml`（scope `fp`）——ISA FP 指令集（取整类如 `ftroot`/`ftcls` 等**以合约/编码表为准**）。
- **输出**：
  1. 补齐 P1 类 ISel/lowering：范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`；**优先 ISA 现成指令**，无现成指令者按 `spec`/`contracts` 口径（libcall 或软件序列，须显式登记依据）。
  2. lit / CodeGen 用例（期望值独立派生，禁反填）。
  3. 重建工具链（`setsid` 脱离、`JOBS=8`、申报耗时）。
- **约束**：
  - **依赖 `LLVM-079t` 已落地**（P0 的 `bitcast`/`setcc` 是 P1 部分项的前置）；同改补丁集 ⇒ **串行**。
  - **计数不写死**：以探针现场统计为准。
  - 只动任务范围，越界须披露。

## 验收标准

1. **P1 类清零**：重跑同一 FP 探针脚本——`NOLIBCALL`/`CANNOT_SELECT` 中 **P1 类（取整六项 / fmin-fmax / fabs-copysign 双精度）清零**（现场统计真实输出）。
2. **语义 E2E**：至少 1 个 FP 相关 picolibc test（如 `test/test-math/test-floor.c`/`test-ceil.c`）编/链/跑出正确退出码（QEMU semihosting）。
3. **ISA/口径证据**：逐类给出 `llc -S` 真实片段或登记所用 libcall/软件序列依据。
4. **门控**：`make check` + lit 全量档 **EXIT=0**；`check-patch-tree` EXIT=0。
5. **反例门控**：新增用例**能失败**（注入错误期望值 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：全部通过。`make check` rc=0；`make check-lit` **99/99** rc=0（含新增 3 个 `p1-*.ll` + 1 个 P1 sign E2E）；`make check-lit-full` 12/12 rc=0；`check-patch-tree`（123 patches，断言⑥⑨）、`check-index-blobs`、`check-no-residue` 均 rc=0；一键证据 `<evidence>/<任务ID>/run.sh` **rc=0**（含注入自检：注入 rc=1 → `cp`+md5 还原 → 回绿 rc=0）。无失败项。

**修改文件**（仅本任务范围）：
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOSubtarget.cpp.patch`（注册 8 个 f64 取整/fmin-fmax libcall）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`（FCOPYSIGN/FABS `MVT::f64` → `Legal`）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOCodeGen.td.patch`（`fosgnj` copysign/fabs 模式）
- `tests/llvm/lit/CodeGen/DADAO/p1-fp-round-libcall.ll`、`p1-fp-minmax-libcall.ll`、`p1-fp-sign.ll`（新）
- `tests/e2e/p1_fp_e2e.c` + `tests/e2e/lit/p1_fp_e2e.test`（新）
- `.tao/knowledge/milestones.md`（`LLVM-080t` 行）
- 证据/日志（非 git）：`.work/evidence/<任务ID>/`、`.work/log/<模块>/`、`.work/log/testcases/` 重建的 FP 探针脚本 + `-after` 结果

**验收结果**（逐条，与真实输出对齐）：
1. **P1 类清零**：同 FP 探针集重跑（脚本据原输入重建并落盘，O0/O1/O2 全档）——`floor_d/ceil_d/trunc_d/round_d/rint_d/nearbyint_d`、`fmin_d/fmax_d` 由 `NOLIBCALL` → **OK**；`fabs_d/copysign_d` 由 `CANNOT_SELECT` → **OK**。
2. **语义 E2E**：真实 picolibc `test/test-math/test-{floor,ceil,round}.c` 编/链/跑 → QEMU semihosting **guest rc=0**（输出 `PASSED`/`max ulp 0`）；另 P1 全类驱动（trunc/rint/nearbyint/fmin/fmax）guest rc=0，`tests/e2e/lit/p1_fp_e2e.test`（fabs/copysign）lit PASS。
3. **ISA/口径证据**：取整六项/fmin/fmax → `call [rb0, <name>]`（libcall 符号 = RTLIB impl 名，picolibc `libm/**/s_*.c` 逐个 `nm` 证实）；copysign → `fosgnj`；fabs → `rd2rf {rfN},{rd0}` + `fosgnj`（contract-fp.md §7）。
4. **门控**：全 EXIT=0（含 lit 全量 12/12）。
5. **反例门控**：注入错期望值（`p1-fp-sign.ll` 的 `fosgnj`→`fosgnjXX`）⇒ lit rc=1 FAIL ⇒ `cp`+md5 还原（md5 一致）⇒ 回绿 rc=0。
6. **无残留**：`git status --porcelain -uall` 仅本任务 3 补丁 + 5 个新测试 + `milestones.md`（另有 2 份**非本任务**未跟踪任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

**新发现/坑**：
- **FABS 若停在 `Expand` 而 FCOPYSIGN 为 `Legal` ⇒ legalize/combine 死循环**：`ExpandFABS` 把 `fabs(x)` 改写为 `fcopysign(x,+0.0)`，DAGCombiner 又把 `fcopysign(x,+正数)` 规范化回 `fabs(x)`（实测 `llc` 挂死；`-debug-only=dagcombine` 见 `tN→tN+1 fabs` 无限）。修法：FABS 亦设 `Legal` 并直接出 pattern，不经 `ExpandFABS`。
- **fabs 需 +0 符号源**：ISA 仅有 `sgnj`(=copySign)/`sgnn`(=neg)、**无 sgnx**；`fabs(x)=sgnj(x,+0)`，+0 由 `rd2rf {rfN},{rd0}`（rd0 硬零）产生；不可用 `sgnj(x,x)`（那是 copy）。
- picolibc `test/test-math/*` 同时测 f32/f64（会调 `floorf` 等 **f32** libcall）⇒ 测 f64 需 `-DSKIP_BINARY32`（P1 仅双精度）。
- sysroot `libm/` 被 INFRA-057t **整目录排除**（恢复属 TESTCASES-042t）⇒ picolibc math test 链接需**直接编译** picolibc `libm/` 源。
- 原 FP 探针**驱动脚本未落盘**（仅输入 `.c` + 输出 log）⇒ 本任务据输入重建并固化（探针集/label/flag/分类与原 log 一致）。

**遗留问题**：
- `fmin_f`（f32）仍 `NOLIBCALL`；`isnan_d`/`isfinite_d`（无序族谓词 `SETUO`/`SETUNO`）仍 `report_fatal_error`——均 **P1 范围外**，属 `ISS-188`（P0 已记；其分类由 `CANNOT_SELECT`→`ERROR` 是 P0 后既有变化，非本任务引入）。
- `git status` 另有 2 个**非本任务**未跟踪任务书（`INFRA-065t`/`SPEC-134t`），未动。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查 + 真实复验）

改动 3 处（`DADAOSubtarget.cpp`：8 个 f64 FP libcall；`DADAOISelLowering.cpp`：FCOPYSIGN/FABS f64 → Legal；`DADAOCodeGen.td`：`fosgnj` 两条 pattern）。逐行核对结论：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| FABS `Expand` + FCOPYSIGN `Legal` → `fabs↔fcopysign(x,+0)` 死循环（自审发现：`fabs` 探测 `timeout` rc=124，`-debug-only=dagcombine` 显示无限 `tN→tN+1 fabs`） | ✅已修 | `setOperationAction(ISD::FABS, MVT::f64, Legal)` + `(fabs f64:$a)→(fosgnj_orrr_rf $a,(rd2rf_orri_rf rd0,1))` | `fabs` 探测 rc=0；probe `fabs_d`=OK；E2E `fabs(-1.5)`=1.5 |
| 取整/fmin-fmax 无 ISA 指令：确认 libcall 而非自造 | ✅已修（按此实现） | `setLibcallImpl(RTLIB::{FLOOR,CEIL,TRUNC,ROUND,RINT,NEARBYINT,FMIN,FMAX}_F64, impl_*)` | `opcodes.yaml` scope fp 无取整/min-max；探针 8 项 OK；`make check-lit` 99/99 |
| libcall 符号名须与 picolibc 一致（否则链接失败） | ✅已核 | — | `nm` 证实 picolibc `s_floor/s_ceil/s_trunc/s_round/s_rint/s_nearbyint/s_fmin/s_fmax.c` 分别定义同名符号；E2E 链接通过、guest rc=0 |
| `rd2rf_orri_rf rd0` 嵌套 pattern 是否可行/正确（rd0 硬零 → +0.0） | ✅已核 | — | llc：`rd2rf {rf1},{rd0}` + `fosgnj rf8,rf16,rf1`；E2E `fabs/copysign` 值全对 |
| f32 路径（P1 外）是否被回归 | ✅已核 | f32 仍 `Expand` | probe `fabs_f/copysign_f`=OK；`make check-lit` 99/99 |
| 越界：是否动 `DADAOInstrInfoFP.td`（P0 曾越界） | ❌不修（无需） | 未动 | `git status` 对账仅 3 补丁；`check-patch-tree` rc=0 |

判决：所有 finding 已修/已核定；无未修项，可标 `待验收`。

### 第 2 轮 reviewer 验收

**门控（独立重跑，6 项均 rc=0）**：
`make check` rc=0（3/3 组件可用）；`check-lit` 99/99 rc=0（含 3 个 p1-*.ll + p1_fp_e2e）；`check-lit-full` 12/12 rc=0；`check-patch-tree` 123 patches OK；`check-index-blobs` 88 new OK；`check-no-residue` PASS。

**FP 探针独立重跑**（独立 OUT 目录，38 行）：P1 类 10 行 × O0/O1/O2 全 OK（floor\_d/ceil\_d/trunc\_d/round\_d/rint\_d/nearbyint\_d/fmin\_d/fmax\_d/fabs\_d/copysign\_d）。pre-fix 对照：floor 等 8 项原 NOLIBCALL、fabs/copysign 原 CANNOT\_SELECT。fmin\_f/isnan\_d/isfinite\_d 非 P1，状态不变。

**libcall 符号存在性**：用 target clang 编译 picolibc `s_floor.c` 等 8 源 → `nm` 各 T{floor/ceil/...}。⚠ sysroot `libm.a` = 876 字节空壳（仅 `empty.c.o`）——INFRA-057t 整目录排除，TESTCASES-042t 恢复。P1 符号在 picolibc 源/目标对象中已证；严格按 dispatch 字面"缺失即阻断"，根因在 INFRA-057t 既知缺口（已登记，恢复归 TESTCASES-042t），非本任务引入。**分类 = 跨任务缺口，供架构师定夺**；建议恢复后 nm 复核。

**fosgnj 依据**：contract-fp.md §7 确认 `sgnj(rfHC,rfHD)=copySign`，rd0 恒零（contract-isa.md §1.3.1）。构造用例（我的驱动，guest rc=0）：copysign(-3,+2)==+3, copysign(+3,-2)==-3, fabs(-1.5)==1.5, fabs(-0.0) bits==0, copysign(+0,-0)==-0(0x8000…0), fabs(-3)==3, copysign(-0,+2)==+0。

**llc 死循环修复**：`timeout 60 llc` 三档（O0/O1/O2）均 rc=0（非 124）。修法：FABS/FCOPYSIGN 均 Legal（不经 ExpandFABS），最小且正确。

**lit 期望值 + 独立注入**：期望值由 RTLIB 名 + contract-fp §7 推导（CHECK 注释显式溯源）。我的注入：`p1-fp-round-libcall.ll` `nearbyint`→`nearbyintXX` → lit rc=1 FAIL；cp+md5 还原（md5 一致）→ rc=0 回绿。

**E2E 重跑**：run.sh 内 picolibc test-floor/ceil/round rc=0；P1 class driver rc=0；我的构造驱动 rc=0。

**脚本落点合规**：`git check-ignore` 确认 `<probe>/picolibc-probe-fp.sh` 和 `<probe>/picolibc-probe-compile.sh` 由 `.gitignore:2:.work/` 排除。AGENTS.md 要求"被引用材料不得只放 .work/"+"脚本随产物保留（优先 tools/）"。**Finding（非阻断，整改项）**：新固化的 FP 探针脚本应移至 `tools/<module>/` 并提交，避免 `.work/` 清理丢失可复用验证能力。

**补丁纪律**：`series` 71 行；check-patch-tree 断言⑦⑧⑨均绿（源树 clean、HEAD=base+1、diff=patch set）；3 补丁非空（67+1121+643 行）。ws 快照前后一致（git status/md5 无变动）。

**遗留登记核**：ISS-188 已承载 fmin\_f(f32, via fminnum/fmaxnum)、isnan/isfinite（via SETUO/无序族）。

**判决：Accepted**。
- 阻断项：无（sysroot libm.a 空壳属 INFRA-057t 跨任务缺口，非 080t 实现缺陷）。
- 非阻断整改项（2 项）：(1) FP 探针脚本移至 `tools/<module>/` 并提交；(2) TESTCASES-042t 恢复 libm 后以 `nm` 复核 8 符号。

**披露（architect 收尾，2026-10-12）**：上轮 architect 在后台证据脚本未完成时提前返回、未提交；本轮（重试）完成复核与提交。
