# LLVM-084t: FP 无序谓词收口（`ISS-193`(a)）+ 删对应源过滤条目

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-079t`（P0，`已验证`）、`LLVM-080t`（P1，`已验证`）、`INFRA-066t`（过滤表来源，`已验证`）；同改 `components/llvm-project/patches` ⇒ **串行**
**状态**：已验证

> 立项来源：用户 2026-10-12 裁定「**先在 M7 内做解锁件再归档**」（备选 (b)）；依据 `ISS-193`(a) 与 `TESTCASES-042t` 的 blocked 量化（(a) ≈**33** 条 test）。

## 目的

`LLVM-079t` 已收口 P0 五类（含**有序** FP 比较取值 `setcc` ⇒ `foqcmp/ftqcmp` + `cs.*`）；**无序族谓词**（`SETO`/`SETUO`/`SETUNO`，即 `isnan`/`isinf`/`isfinite` 等）仍致 `s_pow`/`s_hypot`/`s_acos`/复数等 **30 条源**不可编 ⇒ `INFRA-066t` 的**最小过滤集 41 条**中包含它们。本任务补齐无序族并**删除对应过滤条目**，从而解锁 ≈33 条 picolibc test。

## 接口规范

- **输入**：`ISS-193`(a)（`notes` 含 30 条源与签名）；`contracts/opcodes.yaml`（`scope: fp`，**判断 ISA 是否已有无序/分类指令**，如 `ftcls` 等）；`.tao/knowledge/contract-fp.md`（比较/谓词语义）；`components/picolibc/patches/meson.build.patch`（过滤表，**本次要减少条目**）。
- **输出**：
  1. **后端支持无序族**（范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`）：`SETUO`/`SETUNO`（及所需 `SETO` 组合）lowering/pattern；**优先 ISA 现成指令**（如 `ftcls` 分类后再判）；无现成者用**组合/软件序列**并**逐类登记依据**。
  2. **删过滤条目**：`meson.build.patch` 中与 (a) 相关的条目**删除**（现场 `grep` 计数 before/after）；**重建** picolibc（`make build-picolibc` ~分钟级）+ 安装。
  3. **探针复跑**：`tools/testcases/picolibc-probe-compile.sh` + `picolibc-probe-fp.sh` ⇒ 现场统计（`CANNOT_SELECT`/`NOLIBCALL`/`ERROR` 计数应下降）。
  4. **picolibc test 全量重跑**（`make check-picolibc-tests-full`，`setsid` 脱离 + 落 `XXX_EXIT`；实测 ~7 min）⇒ **四分类 before/after 对比**（`pass` 上升、`blocked` 下降；**现场统计**）。
  5. `milestones.md` 流水更新 `LLVM-084t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**真源 = `spec`/`contracts`**（不从实现反推）；**不得**为通过而放宽语义；**只删"确已可编"的过滤条目**（逐条：源 → 编译证据）；计数不写死。

## 验收标准

1. **无序族收口**：`ISS-193`(a) 类签名（`SETUO`/`SETUNO` 等）**清零**（探针现场统计，**非抽样**）；`isnan`/`isfinite` 等代表源**可编**（真实 `clang -c` 输出）。
2. **过滤条目减少**：`meson.build.patch` 条目数 **before/after 现场统计**；减少数 = 实际可编源数（**逐条对应**，不得多删）。
3. **解锁量化**：`check-picolibc-tests-full` 重跑 ⇒ `pass` **上升**、`blocked` **下降**（before/after 数字 + 解锁的用例清单）。
4. **语义正确**：`isnan`/`isinf`/`isfinite` 语义构造用例（含 `NaN`/`±Inf`/`±0`）真实跑过（期望值**独立派生自 `spec`/C 标准语义**，禁从 `llc` 反填）。
5. **门控**：`make check`、`check-lit`、`check-patch-tree`、`check-index-blobs`、`check-no-residue`、`check-picolibc-tests`（快档）各 EXIT=0。
6. **反例可失败**：注入（错误期望值 / 恢复某条过滤）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）
1. 临时目录 `/tmp/opencode/LLVM-084t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥、`.work/source/llvm-project` = `base+N`、`series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/{llvm-project,picolibc}/patches/**`、`tests/**`、任务书、`milestones.md` 行）；越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时留问。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、**计数不写死**、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **长任务**（重建 / 全量 test ~7 min）：申报耗时；>10 min ⇒ `setsid nohup` + `XXX_EXIT`；`JOBS=8`、禁全核、一次一个；`124` 判 FAIL。
10. **计数不写死**。

## 完成区

**测试结果**：全部通过。`make check` / `check-lit`(102/102) / `check-patch-tree` / `check-index-blobs` / `check-no-residue` / `check-picolibc-tests`(fast 20) 均 rc=0；一键证据 `<证据目录>/run.sh` rc=0，`--inject` rc=0（lit 注入错期望→FAIL→`cp`+md5 还原→回绿；过滤条目注入→计数 11→12→md5 还原）。

**修改文件**（仅本任务范围）：
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`（FP 分支/取值补 `SETUO`/`SETO`/`SETONE`/`SETUEQ` + 6 个整数型 don't-care 码）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOCodeGen.td.patch`（`DADAOFPSelCC` 增 4 条 ISel 兜底 pattern）
- `components/picolibc/patches/meson.build.patch`（删 30 条 (a) 类过滤条目，41→11）
- `tests/llvm/lit/CodeGen/DADAO/fp-unordered-pred.ll`、`tests/e2e/fp_unordered_e2e.c`、`tests/e2e/lit/fp_unordered_e2e.test`（均新建）
- `.tao/knowledge/milestones.md`（`LLVM-084t` 行）
- 证据/日志（非 git）：`<证据目录>/`、`<日志目录>/`

**验收结果**（与真实输出逐条对齐）：
1. **无序族收口**：30 个 (a) 源**逐条** `clang -c` 全 OK（before：29 `FP_BRANCH`+1 `FP_SELECTCC`，均 rc=1）；探针 backend 类失败 **0**（`BACKEND_CANNOT_SELECT`=0、`BACKEND_OTHER` 1→0，341 源现场统计）。
2. **过滤条目**：`meson.build.patch` **41→11**（删 30，= 逐条可编源数，**未多删**）。
3. **解锁量化**：`check-picolibc-tests-full` **pass 132→152（+20）、blocked 85→65（−20）**、fail=0、excluded=18；解锁清单（20）＝test-acos/acosh/asin/catan/ccos/ccosh/cexp/clog/csin/csinh/csqrt/exp10/exp2/hypot/j0/j1/jn/long-double/pow/sqrt。
4. **语义正确**：`isnan`/`isinf`/`isfinite`（NaN/±Inf/±0）f64+f32、取值+分支两形态 → QEMU guest **rc=0**（期望值独立派生自 IEEE754/C `<math.h>` 语义，非 llc 反填）。
5. **门控**：同上「测试结果」（各 EXIT=0）。
6. **反例可失败**：见 `--inject`（两条注入各 FAIL、`cp`+md5 还原回绿）。
7. 完成区与真实输出逐条对齐（计数均现场统计、未写死）。

**新发现/坑**：
- 真源归纳：`isnan`=`fcmp uno`(**SETUO**)、`isfinite`=`fcmp one (fabs x),+Inf`(**SETONE**)、`isinf`=`fcmp oeq`（既有）；(a) 类实需 **SETUO/SETONE**，另补 `SETO`/`SETUEQ`。
- `dcvt.c` 根因实为 **FP 操作数上的整数型 don't-care 码 `setge`**（`fmul nnan` ⇒ DAG 规范化为 `SETGE`），非 `ISS-193` 记的 `SETUO`；须一并补 `SETEQ/SETNE/SETLT/SETLE/SETGT/SETGE`（`ISDOpcodes.h` 定义：NaN 时结果 undefined ⇒ 按 ordered 对应码降级）。
- 判无序依据（全用现成 ISA，未用 `ftcls`）：FP 比较按 `contract-fp.md §8` 有序返回 −1/0/1、无序返回**正 qNaN**（QEMU `trans_fp.c.inc` 实测 fo=`0x7FF8…`、ft=`0x7FC00000`，符号位 0），整型解读 > 1 ⇒ `cmp.si rd,1` 分离（`contract-isa §6.2`），再接 `br.*`/`cs.*`（§6.5）+ `and.o`/`or.o`（§6.1）。
- 解锁后暴露**更深缺口**（非本任务引入，仍 blocked）：`__muldc3`（复数乘，6）、`ISS-195`（QEMU 2-NaN abort，5）、`REL26`/`ISS-194`（27）、`ISS-193(b)`(10)/(d)(14)/(e)(2)、`setjmp`(1)。
- 补丁 workflow：改 `<源树>` → `git -C <源树> commit --amend`（保 `base+1`）→ `tools/infra/make_patch.py <组件>` 导出。

**遗留问题**：
- (a) 清零后 picolibc test 仍 blocked 65 条（(b)–(f) + `ISS-194`/`ISS-195`），属后续任务范围。
- td 兜底 pattern 未被测试直接触发（pre-legalize `SELECT_CC` 走 Custom lowering），与 C++ lowering 同构、TableGen 已校验，为防御性条目。
- `ISS-193` 台账「(a)≈33 test」为估算；实测解锁 **20**（其余 13 移因其它已登记缺口，非回归）。

## 审阅记录

#### 第 1 轮 engineer 自审（自主逐行审查 + 真实复验）

改动 2 处：`DADAOISelLowering.cpp`——`LowerBR_CC`/`LowerCmpSelect` 的 FP 块各新增 `Unordered` 助手 + `SETUO/SETO/SETONE/SETUEQ` + 6 个 don't-care 码；`DADAOCodeGen.td`——`DADAOFPSelCC` 增 4 条 pattern。逐行核对结论：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `SETUO` 判据「rc>1」是否成立（NaN 幅值未在合约明写） | ✅已修（依据成立） | 用 `cmp.si rd,rc,1` | `contract-fp.md §8`（有序恰 −1/0/1）+ QEMU `trans_fp.c.inc`（无序恒写正 qNaN）⇒ 有序≤1<无序；生成 `foqcmp;cmp.si;cs.p` |
| `SETONE/SETUEQ` 需两条件组合（单次 cs 不可表达） | ✅已修 | `and.o`/`or.o` 组合 ordered 标志与 equal/not-equal 标志 | asm：`cs.z…;cmp.si;cs.p;and.o`/`or.o`；e2e guest rc=0 |
| 遗漏 `SETO`/`SETUNO`（本项目无 SETUNO 枚举，仅 `SETO`/`SETUO`） | ✅已修 | 增 `SETO`（`!SETUO`），与 `SETUO` 成对 | `pred.ll` 两式均出 `cmp.si`；`fp-unordered-pred.ll` PASS |
| don't-care 码（`SETEQ..SETGE`）在 FP 操作数上可达（`dcvt.c`） | ✅已修 | FP 块补 6 码，按 ordered 对应码降级（NaN 为 undefined，合法选择） | `dcvt.c` 探针 BACKEND_OTHER 1→0；`fp-ge_nnan` CHECK `foqcmp;cs.p;CHECK-NOT cmp.si` PASS |
| 新分支是否误伤整数路径（`SETEQ/SETNE/SETLT/…` 与整数 `switch` 冲突） | ❌不修（结构隔离） | FP 块由 `isFloatingPoint()` 守卫，整数 `switch (CC)` 独立 | `make check-lit` 102/102 全绿；探针 341 源 0 backend 失败 |
| td pattern 类型正确性（`cs_p_rd` vs `cs_p_rrrr_rf`、嵌套 `cmp_si_rd`） | ✅已修 | SETONE/SETUEQ 旗标改用 `cs_p_rd`/`cs_z_rd` | TableGen + `ninja LLVMDADAOCodeGen` rc=0；全量重建后 test 数字不变 |
| td pattern 可达性无法构造用例直接触发 | ⏸延后（已披露） | 保留（与既有 10 条对称、与 C++ lowering 同构） | 记入「遗留问题」；`check-lit` 不回归 |
| `default: report_fatal_error` 是否应删（现几近不可达） | ❌不修（显式失败保留） | 保留 | 未覆盖码仍显式报错（硬约束：不静默成功） |
| 探针/全量计数是否现场统计（无写死） | ✅已修（本就如此） | — | 证据脚本用 grep/awk/wc 现场计数；before/after 数字取自 JSON |

判决：finding 均 ✅已修 / ⏸已披露 / ❌已核定，无未处置项，可标 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑**（全部 reviewer 亲自执行，仓库根相对路径；长任务 `setsid` 脱离 + `XXX_EXIT`）：
1. 门控 6 项各 EXIT=0：`check` / `check-lit`(Passed 102) / `check-patch-tree` / `check-index-blobs` / `check-no-residue` / `check-picolibc-tests`(fast：total=20 pass=15 fail=0 excluded=1 blocked=4)。
2. `<证据目录>/run.sh` 基线重跑 rc=0（13 项全绿，自报 `probed=341`）。
3. 全量 `check-picolibc-tests-full JOBS=8`（`XXX_EXIT=0`）⇒ **我的统计 total=235 pass=152 fail=0 excluded=18 blocked=65**，四数与自述一致；对 (a) 归因 before 33 条逐条对账 = **20 pass + 13 移因其它缺口**（__muldc3 6 / QEMU signal 6 4 / (b) 2 / REL26 1）；解锁 20 清单与自述逐条一致，test-pow/hypot/j0/j1/sqrt/acos/clog/csqrt 等实跑 exit 0。
4. 过滤表独立提取=11 条；用 `<构建树>/compile_commands.json` 权威编译项**全量**（非抽样）编 41 源：被删 30/30 rc=0（复数/s_pow/s_hypot/s_fma 全过）、保留 11/11 仍 rc=1（flog/frint/ftrunc、bswap、trunc-store、'r' 约束、strtod，签名对齐 ISS-193 (b)-(f)）⇒ **不多删/不少删**。
5. 无序族语义（期望值独立派生自 `contract-fp §8`+`contract-isa §6.2`+IEEE754/C，非 llc 反填；`trans_fp.c.inc` 佐证 qNaN=0x7FF8…/0x7FC00000 整型>1 ⇒ `cmp.si rc,1` 判据成立）：自写 45+ 断言（NaN/±Inf/±0/正常 × f32/f64 × 取值/分支，isnan/isinf/isfinite/isunordered/islessgreater/ueq/ord）guest **O0/O1/O2 均 rc=0**；期间我一处期望式写错曾致 rc=133，修正后 0（向量非恒真）。
6. ISA 证据（自写 llc 片段）：`foqcmp/ftqcmp→cmp.si→cs.p`（SETUO/SETO 臂互换）、SETONE=`cs.z+cmp.si+cs.p+and.o`、SETUEQ=`…+or.o`、分支形 `br.np`；`DADAOISD::CMP→cmp_si_rd`（**有符号**，rc=−1 若按无符号会误判）——与 C++/td 同构。
7. 反例（我的独立注入，与 engineer 两条不同）：改 e2e 语义期望值（md5 `43708264…`→`53cfd3a7…`）⇒ `run.sh` rc=1（lit e2e + check-lit 双 FAIL）；`cp`+md5 还原（`43708264…` 命中）⇒ 重跑 `run.sh` rc=0 回绿。
8. 补丁纪律：series llvm 71/picolibc 14；`<源树>`=base+1 且干净；无空/微型 patch。
9. 约束核验：改动限 3 patch + 3 测试 + milestones 行 + 任务书；验收前后 7 目标文件 md5 **SNAPSHOT-MATCH**、git status 逐行一致；临时物全在 `/tmp/opencode/LLVM-084t-review/`；未提交 git、未改被测实现。
10. 采信（before 不可复现，指针在证据目录）：pass 132/blocked 85、29 FP_BRANCH+1 FP_SELECTCC、BACKEND_OTHER 1→0。

**finding**：
- **阻断 F1（完成区失真，验收标准 7 不满足）**：完成区①与自审表所称「**347 源现场统计**」与真实不符——我重跑与 engineer 自有日志**均为 341**（`run.sh` 自报 `probed=341`，源清单机械数=341）。整改：2 处 347→341，其余不动。
- 非阻断 F2（承载/量化，`/complete` 沉淀项）：`__muldc3`(6) 无 `ISS-*` 承载；`ISS-194` 26→**27**、`ISS-195` 1→**5**、`ISS-193`(b) 8→**10** 未同步（任务书已披露数字；issues.yaml 超任务范围故未改，处置正确）。
- 非阻断 F3：`ISS-193`(a) 估算 33 vs 实测 20 已在任务书「遗留问题」如实登记且经我独立验证（20/13 拆分）；`ISS-193` notes 无更正指针，建议沉淀时补。
- 观察 F4：未跟踪 `INFRA-065t`/`LLVM-085t`/`docs/Machine-00-*` 不在本任务「修改文件」声明内，疑主会话产物，请 `/complete` 确认归属。

**判决：Needs Revision**（仅 F1；语义/过滤表/解锁量化/门控/反例/补丁纪律全部通过，整改面=2 个数字）。

#### 返工 1（计数对齐）engineer

**触发**：第 1 轮 reviewer 阻断 F1（347→341）。本返工**仅**计数对齐 + 现场复验，**未改**实现/补丁/测试/`issues.yaml`。
**347→341 更正（显式 2 处）**：① 完成区「验收结果」①末句「347 源现场统计」→「**341 源现场统计**」；② 自审表第 5 行复验列「探针 **347 源** 0 backend 失败」→「**341 源**」。依据：`<证据目录>/run.sh` 现场输出 `act=341`（`probed=$(wc -l compile.tsv)`=341），探针脚本末行 `DONE total=341`。

**计数逐条对账**（值＝现场/日志；"一致"=本轮重新核对通过）：

| # | 计数项（出处） | 任务书值 | 真实值（证据） | 处置 |
|---|---|---|---|---|
| 1 | (a) 源数（目的/验收①/完成区①） | 30 | 30（`scan30-*` 30 行，after 30×rc=0） | 一致 |
| 2 | before 分类（完成区①） | 29 FP_BRANCH+1 FP_SELECTCC | 29/1（`scan30-before` summary） | 一致 |
| 3 | 探针 backend 类失败（完成区①） | C_SELECT=0 / OTHER 1→0 | 0 / 1→0（before,after tsv） | 一致 |
| 4 | 探针源数（完成区①、自审表5） | 347 → **341** | 341（run.sh `act=341`；`DONE total=341`） | **✅已修** |
| 5 | 过滤条目（目的/验收②/完成区②③） | 41→11（删30、未多删） | 11；`git diff` 删30 加0 | 一致 |
| 6 | full 四数（完成区③） | pass132→152／blocked85→65／fail0／excl18 | 同（`full-{before,after}.json`+`.log`；total 235=235） | 一致 |
| 7 | 解锁清单+回归（完成区③） | 20 项命名清单 | 20 项逐名一致（blocked→pass）；regressed=0 | 一致 |
| 8 | check-lit（测试结果/自审表5） | 102/102 | 102（Passed 102, 100%） | 一致 |
| 9 | picolibc-tests 快档（测试结果） | 20 | total=20 pass15 fail0 excl1 blocked4 | 一致 |
| 10 | 反例注入计数（测试结果） | 11→12→md5还原 | act=12；md5 `e7547603…` 还原命中 | 一致 |
| 11 | don't-care 码数（修改文件） | 6 | 6（`ISD::SET{EQ,NE,LT,LE,GT,GE}`） | 一致 |
| 12 | td 兜底 pattern 数（修改文件） | 4 | 4（SETUO/SETO/SETONE/SETUEQ 各1） | 一致 |
| 13 | 新建测试文件数（修改文件） | 3 | 3（ll / c / e2e.test 均在） | 一致 |
| 14 | 更深缺口计数（新发现） | muldc3 6／195 5／REL26·194 27／(b)10／(d)14／(e)2／setjmp 1 | 同（after.json blocked65 分类 6+5+27+10+14+2+1=65） | 一致 |
| 15 | 遗留 blocked（遗留问题） | 65 | 65（after.json） | 一致 |
| 16 | (a) 估算 33 vs 实测 20 / 移因 13 | 33估、20实测、13移因 | 20（reviewer 独立核 20/13 拆分） | 一致（已披露） |

> 注1：(b)=10 = reason 显式「f32 libcall missing」5 + `undefined symbol: *f`（lgammaf_r/log10f/tgammaf/nearbyintf）5；(d)=14 = `vfscanf`11+`vfwscanf`3。
> 注2：reviewer 记录第 2 条称「13 项全绿」——`run.sh` 实打印 **12** 条 record（2 过滤+3 探针+2 lit+5 门控）；该行属 reviewer 记录，按原文保留，此处更正留档。

**重跑取证**（仓库根相对路径；脚本/门控退出码直捕，未 `tee`）：
- `<证据目录>/run.sh` 基线 **rc=0**（12 项 record 全绿，`act=341`）；`--inject` **rc=0**（lit 错期望→FAIL rc=1→md5 `6c6b841e…` 还原→绿；过滤 11→12→md5 `e7547603…` 还原）。
- 门控：`make check` rc=0、`check-lit` rc=0（102/102）、`check-picolibc-tests`(fast) rc=0。
- 未改证据：返工前后 3 patch + 3 测试 md5 **全等**（`DADAOISelLowering.cpp.patch 63fc24ee…`、`CodeGen.td.patch 3c36fa37…`、`meson.build.patch e7547603…`、`fp-unordered-pred.ll 6c6b841e…`、`fp_unordered_e2e.c 43708264…`、`fp_unordered_e2e.test 711ac7bf…`）。

**F2/F3/F4 处置**：F2 ❌不改（超范围）→ 交 architect 同步 `issues.yaml`：`ISS-194` 26→**27**、`ISS-195` 1→**5**、`ISS-193`(b) 8→**10**；并立 `__muldc3`(6，复数乘)**无 `ISS-*` 承载**。F3 ⏸已登记（完成区遗留第 3 条如实写 33 估 vs 20 实测），建议 `/complete` 在 `ISS-193` notes 补更正指针。F4 ❌不改（未跟踪 `INFRA-065t`/`LLVM-085t`/`docs/Machine-00-*` 非本任务产物，未触碰，交 `/complete` 核归属）。

**判决**：F1 已修（2 处 347→341），计数逐条对账无其它不符（1 处 reviewer 记录行更正留档）；无未处置 finding ⇒ 状态 `待验收`。

#### 第 1 轮 reviewer 复验（计数对齐返工｜复验轮）

1. **阻断项已修**：`grep 347` 仅存 reviewer 历史记录行（原文）与返工说明引用；完成区①/自审表5 已为 **341**，与现场三方一致——探针源清单机械数=**341**、`compile.tsv`=341 行、`run.sh` `act=341`。
2. **对账表抽查 7 项**（要求≥5）：#4 源数 341 ✓；#5 过滤 41→11（`git diff` 删 30/加 0、现集 grep=11）✓；#6 全量四数 pass152/fail0/excl18/blocked65（我方 full 日志重算）✓；#8 check-lit 102/102（本轮现场）✓；#9 fast 20（15/0/1/4）✓；#11 don't-care 码 6（`SET{EQ,NE,LT,LE,GT,GE}`，BR_CC/Select 各一份）✓；#12 td pattern 4 ✓；且缺口分桶 27+6+5+14+1+2+10=**65** 自洽 ✓。
3. **我的记录更正（engineer 指出属实）**：上轮记录第 2 条「13 项全绿」为笔误——`run.sh` 实打印 **12** 条 record（我方日志 `| exp=` 计数=12）；**更正：应读「12 项 record 全绿」**，上轮原文保留、以此行为准；engineer 仅留档未改写，处置正确。
4. **门控**（本轮自跑）：`make check`=0、`check-lit`=0（Passed 102）、`check-picolibc-tests`=0（total=20 pass=15 fail=0 excluded=1 blocked=4）。
5. **未波及**：3 patch + 3 测试 md5 与上轮快照逐个全等（`63fc24ee…`/`3c36fa37…`/`e7547603…`/`6c6b841e…`/`43708264…`/`711ac7bf…`）。

**判定：Accepted**（F1 已修并现场复核；F2/F3/F4 仍为 `/complete` 沉淀项，非阻断、不改判）。
