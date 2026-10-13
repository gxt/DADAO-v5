# INFRA-067t: 提供 `__muldc3`/`__mulsc3`（复数乘编译器辅助）

**模块**：infra
**项目里程碑**：M7
**依赖**：`LLVM-088t` 等（**同改 `components/picolibc/patches` ⇒ 与 picolibc 侧任务串行**）
**状态**：已验证

> 立项来源：用户 2026-10-12 裁定「先在 M7 内做解锁件再归档」+ 本轮讨论（**从易到难第 4 项**）；依据 `ISS-196`（clang 对 `_Complex` 乘生成 `__muldc3`/`__mulsc3`；picolibc 不提供 ⇒ 链接 `undefined` ⇒ blocked **6**）。**模块归属**：产物在 `components/picolibc/**` ⇒ `infra`（同 `INFRA-057t`/`066t`）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：`__muldc3`/`__mulsc3` 从哪来。
- 选项：(a)「**移植 compiler-rt 单文件（推荐）**」／(b) 自带简化实现（极端值语义不同）／(c) 改前端语义。
- **用户选择 = (a) 移植 compiler-rt 单文件**。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## 目的 / 根因（事实）

- clang 对 C `_Complex` 乘法生成 **`__muldc3`（double）/`__mulsc3`（float）** 调用（编译器辅助的**缩放复乘**，用于避免中间量溢出；**语义 ≠ 普通复乘**）。
- **picolibc 不提供**这两个符号 ⇒ 链接期 `undefined` ⇒ `ISS-196` 的 **6 条** test blocked。
- 注意：`LLVM-084t` 已解锁的复数函数（`ccos/csqrt/…`）**不依赖**它（picolibc 自带实现在 `libm/complex/**`）⇒ 本任务只补**编译器期望的辅助符号**。

## 接口规范

- **输出**：
  1. **移植 compiler-rt 的 `muldc3.c` / `mulsc3.c`** 入 `components/picolibc/patches/**`（**一文件一补丁**；`series` 追加）：
     - **必须标注出处与许可**：来源 = `compiler-rt/lib/builtins/{muldc3.c,mulsc3.c}`（LLVM 系，**Apache-2.0 WITH LLVM-exception**）；在补丁/文件头写明**文件路径 + 版本（commit 或 llvmorg tag）+ 许可**（`AGENTS.md`「参考来源」：第三方源码随产物入库须标出处，**不得**只写在 commit message）。
     - **不得修改其算法**（保持与 clang 期望的语义一致）；如与 picolibc 现有符号/头冲突（重名/宏）⇒ **停下报告**（不擅自改名/改语义）。
  2. **重建 picolibc**（`make build-picolibc`；~秒级）+ 链接验证（目标端 `ld.lld` 解析到符号）。
  3. **全量 test**：`make check-picolibc-tests-full` ⇒ **四分类 before/after**（before：`pass 152 / fail 0 / excluded 18 / blocked 65`）+ **解锁用例清单**（预期 6 条）。
  4. `.tao/knowledge/milestones.md` 流水更新 `INFRA-067t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**最小改动**（只加 2 个符号的实现）；**不改** `spec/`、`contracts/`、`tests/vectors/`；**不改** LLVM 侧；**计数不写死**。

## 验收标准

1. **符号存在**：`nm` 在 **picolibc sysroot** 中证明 `__muldc3`/`__mulsc3` **有定义**（真实输出；`T`）。
2. **可链接可跑**：原 blocked 用例（抽 ≥3，含复数乘路径）**链接 + QEMU 真跑 rc=0**（真实输出/退出码）；**`fail` 仍须 0**。
3. **全量 test**：`pass` **上升**、`blocked` **下降**（before/after 现场统计 + 解锁清单）。
4. **出处许可**：补丁/文件头含**来源路径 + 版本 + 许可**（`grep` 证据）；**算法未被修改**（相对上游 diff 仅移植适配，逐条说明）。
5. **门控**：`make check`、`check-patch-tree`、`check-no-residue`、`check-picolibc-tests`（快档）各 EXIT=0。
6. **反例可失败**：注入（移除该符号 / 改错期望）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-067t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥、`.work/source/picolibc` = `base+N`、`series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/picolibc/**`、任务书、`milestones.md` 行）；越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时**停止并报告**（禁自拟自答）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **计数不写死**。

## 完成区

**测试结果**：`make check-picolibc-tests-full`（全量 **235**，现场统计）before `pass 197 / fail 0 / excluded 22 / blocked 16` → after `pass 203 / fail 0 / excluded 22 / blocked 10`（**+6 / −6**）。**解锁 6**（均 rc=0）：`test-cacos`、`test-cacosh`、`test-casin`、`test-casinh`、`test-catanh`、`test-complex-funcs`；**移因 1**：`test-math-funcs`（本任务后**已可链接**，改撞 `ISS-195`：QEMU 软浮点 2-NaN `signal 6`——该缺口**基线已阻 7 条**，非本任务引入）；`newly_blocked=∅`。聚焦复跑 6 条复数乘用例整跑 rc=0。
**修改文件**：（新）`components/picolibc/patches/libm/common/{mulsc3.c,muldc3.c,compiler_rt_builtins.h}.patch`；（改）`components/picolibc/patches/libm/common/meson.build.patch`（**纯插入**）、`components/picolibc/series`、`components/picolibc/{README.md,changelog.md}`、`.tao/knowledge/milestones.md`、本任务书。另：picolibc 组件工作树（`.work/source/<组件>`）本地 commit（`base+1`，**不进 upstream、永不 push**）。
**验收结果**：`make build-picolibc` rc=0（`libc.a` **1,799,920 → 1,803,498 B**）；`nm` sysroot `libc.a`：`T __muldc3`=1、`T __mulsc3`=1（**有定义**）；两 `.o` 的 `nm -u` **为空**（零 runtime 符号依赖）；vendored 函数体 vs 上游 `cmp` **逐字相同**（仅头注释/`#include` 行适配）；补丁头含 **来源路径 + `6dfe1677ab8dffbc6ec13d53a1e0215d75147689` + `llvmorg-23.1.1` + `Apache-2.0 WITH LLVM-exception`**。门控 `make check` / `check-patch-tree` / `check-index-blobs` / `check-no-residue` / `check-picolibc-tests` / `check-patch-tree --source-state` **全 rc=0**。反例：**I1**（删补丁中 `muldc3.c` 条目 ⇒ 结构断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）、**I2**（改源内 `__mulsc3` 名 + 重建 ⇒ `nm`=`U` 且 `test-casin` blocked ⇒ 还原+重建 ⇒ `T` 回绿）；一键证据 `.work/evidence/<任务ID>/run.sh`（`--inject`）**rc=0**。
**新发现/坑**：① clang 对 `_Complex` 乘**仅**在「实部与虚部皆 NaN」时走 `complex_mul_libcall` 调 `__muldc3`/`__mulsc3`（正常路径 inline 展开）——该辅助是**缩放复乘**，语义 ≠ 普通复乘。② ABI：compiler-rt `Dcomplex` = `double _Complex`（`__STDC_VERSION__>=199901L` 分支），LLVM 返回 `{double,double}`，与 clang 的 `declare {double,double} @__muldc3(double,double,double,double)` **一致**。③ 两文件**零 runtime 依赖**：`__builtin_isnan/isinf/copysign{,f}/huge_val{,f}` 在 DADAO 全 inline lowering（`fosgnj`/位操作）⇒ 不需 `scalbn`/`fmax` 等。④ **`ISS-196` 的 blocker 面实为 7 条**（issue 文本记 6，漏 `test-math-funcs`）——建议收口时更正计数并置 `resolved_by=INFRA-067t`（本任务按范围**未动 `issues.yaml`**）。⑤ picolibc lib 源带 `-Wmissing-prototypes`（**非 `-Werror`**）⇒ shim 内补两条 ABI 原型（与 compiler-rt 在 `int_lib.h` 声明 runtime 原型同惯例）。
**遗留问题**：① `test-math-funcs` 仍 blocked，但归 `ISS-195`（QEMU 软浮点 2-NaN）——**非本任务范围**，不修。② `issues.yaml` 的 `ISS-196` 未更新（越界，见坑④，待主会话收口）。③ **未扩范围证据**：未动 compiler-rt 上游（`git diff <llvm base> -- compiler-rt/lib/builtins/{muldc3,mulsc3}.c` 为空）、未动 `spec/`/`contracts/`/`tests/vectors/`、未动 LLVM/QEMU、未引入外部依赖。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查对象**：`components/picolibc/patches/libm/common/**`（3 新 + 1 改）、`components/picolibc/series`、`README.md`/`changelog.md`、picolibc 组件工作树（`.work/source/<组件>`）的 `libm/common/**`（vendored 源）、证据脚本 `.work/evidence/<任务ID>/run.sh`。

**逐行审查**：
- `muldc3.c`/`mulsc3.c`：函数体 `cmp` 与上游逐字相同（改动仅头注释 + 两 `#include` → 一行 shim）；`crt_*`/`CRT_INFINITY` 映射与 `int_math.h` 语义一致（`CRT_INFINITY` 依 `DOUBLE_PRECISION` 选 `huge_val/huge_valf`，与上游同构）。
- `compiler_rt_builtins.h`：`_Complex` 需 C99+（本构建 `-std=c18`）；仅被两个 vendored TU include ⇒ 无符号/宏外泄；`Fcomplex`/`Dcomplex` 不与 picolibc 头冲突（全库无重名，已 `grep`）。
- `meson.build`：两源加入 `srcs_common`（→ `libc.a`，因 picolibc 1.7+ libc/libm 合并）；补丁为**纯插入**（不夹带行尾空白清理）。
- 证据脚本：每条断言均有**可达 FAIL 路径**（I1 结构 / I2 行为实证）；覆盖计数**现场统计**（无写死总数）；还原一律 `cp`+md5（**未用** `git checkout/restore/stash`）；结尾无 `tee` 吞码。

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 shim 缺原型 ⇒ 两 vendored 源各 1 条 `-Wmissing-prototypes` 警告 | ✅已修 | shim 增 `COMPILER_RT_ABI Dcomplex __muldc3(...)`/`Fcomplex __mulsc3(...)` 原型 | 重编两源 rc=0 且**零警告**（真实编译输出） |
| F2 证据脚本 I1 断言 `[ x -eq N - 1 ]`（参数错，恒 FAIL） | ✅已修 | 改 `n_expect_i=$(( ${#VENDORED[@]} - 1 ))` 后比较 | `--inject` 全绿 `rc=0` |
| F3 `meson.build` 补丁原夹带 `]  ` 行尾空白清理（非必要改动） | ✅已修 | 还原该行尾空白，使补丁成为**纯插入** | 新补丁 `-   'signgam.c'`/`+…`，`]  ` 为上下文；`check-patch-tree`/`check-index-blobs` rc=0 |
| F4 `test-math-funcs` 未如预判 pass（原 expected 含它） | ❌不修（非本任务） | — | 现可链接、移因 `ISS-195`（基线同类 7 条 `signal 6`）；见完成区「移因 1」 |

**判决**：finding 全部已修（F4 为非本任务的既有缺口，已披露）⇒ 状态 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**（workdir=仓库根，相对路径；真实输出/退出码）：
- 门控：`make check` rc=0（L1 PASS）；`make check-patch-tree` rc=0（`4 component(s), 127 patches OK`）；`make check-index-blobs` rc=0（`91 new-file patch(es) OK`）；`make check-no-residue` rc=0（PASS）；`make check-picolibc-tests` rc=0（fast `total=20 pass=17 fail=0 excluded=2 blocked=1`）；`tools/infra/check_issues.py` rc=0（24 open, 8 closed）。
- 出处/许可/版本：`grep` 两补丁头 ⇒ `Source: llvm-project, compiler-rt/lib/builtins/{muldc3,mulsc3}.c` + `Version: commit 6dfe1677ab8dffbc6ec13d53a1e0215d75147689 (llvmorg-23.1.1)` + `License: Apache-2.0 WITH LLVM-exception` 齐备，**与 `manifests/components.lock.toml` 锁定 commit/shallow_ref 逐字一致**；shim 头 SPDX+Source/Version/License 齐。`diff <(sort series) <(find patches -name '*.patch')` rc=0（18 条一致）。
- **算法未改（本人独立 diff）**：自补丁抽新文件体（79/77 行，与 `@@ -0,0 +1,N` 相符）vs `.work/source/<上游>/compiler-rt/lib/builtins/*` ⇒ **仅**头注释 14 行插入 + `int_lib.h`/`int_math.h` → `compiler_rt_builtins.h` 一行 include；函数体（`/^COMPILER_RT_ABI/,$`）`cmp` **rc=0×2 逐字相同**；上游 4 文件 `<锁定commit>..HEAD` `diff --stat` 空（本地参考=锁定版本）；shim 宏映射与上游 `int_math.h`/`int_types.h` 语义一致。
- 依赖核：`ar p` sysroot `libc.a` 两 `.o` ⇒ `nm` 各仅 `T __mul{dc,sc}3`，`nm -u` **undef=0**（零 runtime 依赖、无新增符号）。
- 符号与解锁：`nm libc.a` ⇒ `T __muldc3`/`T __mulsc3` 各 1；抽 **6 条**真跑 `--only test-cacos,…,test-complex-funcs` ⇒ `6/6 pass exit 0`、fail=0、rc=0；`test-math-funcs` 真跑 ⇒ blocked，log 含 `softfloat-parts.c.inc:108:parts64_pick_nan: code should not be reached` + `signal 6`（= `ISS-195` 签名），基线同类 signal6 blocked **7 条** ⇒ **移因归因如实**（链接已通，撞既有 QEMU 缺口）。
- 全量（本人重跑 `--stage full`）：`total=235 pass=203 fail=0 excluded=22 blocked=10` rc=0；vs before `197/0/22/16` 差值 **+6/−6**；`newly_blocked=[]`；解锁 6 与声称一致；inventory 同（235）。
- 补丁纪律：新补丁 `@@ -0,0 +1,N` + 非全零 blob；`check-patch-tree --source-state` rc=0；`.work/source/<组件>` = `base+1`（2 commit）且 status 干净；`meson.build.patch` 净插入（仅 `'signgam.c'`→补逗号）。
- 证据脚本：逐条断言可达 FAIL、计数现场统计（`${#NEW_PATCHES[@]}` 等）、还原 `cp`+md5、无 `tee` 吞码；`run.sh` 重跑 **rc=0**（ALL CHECKS PASSED，31 条记录全 `rc=0`）。
- **独立注入 I3（非 I1/I2）**：shim `COMPLEX_*` 宏体互换（`.work/source/<组件>/…shim` 与 `<补丁>` 同步，md5 `84242c14…→3bdaf250…`/`158f6a9d…→1f6bfb74…`）⇒ 重编 rc=0 且 `.o` md5 `8e44ce7e…→f0497e04…`（注入确进产物）⇒ **run.sh rc=1 FAILED**（`make check`=2、`check-patch-tree`=2、`check-index-blobs`=2、`--source-state`=1）⇒ `cp`+md5 还原（两 md5 逐字回前）⇒ 重编 `.o` md5 回 `8e44ce7e…` ⇒ run.sh rc=0 回绿。如实记录：FAIL 经补丁 blob-hash/patch-tree/source-state 断言暴露；6 条解锁 test 未回归（`__mul*3` 仅「实虚部皆 NaN」角径被调）⇒ 语义正确性锚在「算法未改 diff」，测试仅锁链接。
- 工作区对账：结束 `git status --porcelain -uall` 与开工快照**逐行一致**、目标文件 md5 全 OK（我仅新增本审阅记录）；未提交 git。

**约束核验**：临时目录 `/tmp/opencode/<任务ID>-review/` ✓ 仓库无残留（check-no-residue PASS）✓ 未改被测实现（注入均还原+md5 对账，未用 git checkout/restore/stash）✓ 与真实输出逐条对齐 ✓ 无需用户裁定 ✓ 无字面具体 `.work/` 路径 ✓ 范围核对：改动集=完成区「修改文件」声明，`spec/`/`contracts/`/`tests/vectors/` 零改动 ✓

**判决：Accepted**。阻断项：无。非阻断建议：① 收口时更新 `ISS-196`（blocker 6→7、`resolved_by=INFRA-067t`，如坑④）；② 6 条解锁 test 不覆盖 `__mul*3` NaN 角径语义（正确性锚在逐字 diff），如需行为覆盖建议另立小向量。

#### architect 提交与文件集审核（第 1 轮验收后）

- **档位**：reviewer 第 1 轮判决 **Accepted** ⇒ **正常提交**（非 `WIP:`）。
- **分支提交** = `76f512b`（`INFRA-067t` 分支内）；**落地** = `master` `5d0e37f`（`merge --squash`，落地时间 `2026-10-12 18:01`，与 `milestones.md` 流水行一致）；分支已删（`git branch -D INFRA-067t`）。
- **文件集对账**（显式 staging、逐个路径，**未**用 `git add -A`）：`git diff --cached --name-status` = **10** 项，与完成区「修改文件」逐条一致 ⇒ **漏提/多提/越界 = 0**；**不含** 3 份外来未跟踪任务书（`INFRA-069t` / `INFRA-070t` / `SPEC-135t`，仍 `??`）。标注差异 1 处：完成区把 `patches/libm/common/meson.build.patch` 记「（改）」，实为**新增文件**（`A`），内容 = 向 `libm/common/meson.build` 的 `srcs_common` 加两源（纯插入）；顶层 `patches/meson.build.patch` **未改**。
- **收口追加（超出完成区声明，已披露）**：`issues.yaml` 的 `ISS-196` → `closed` + `resolved_by: INFRA-067t`（计数更正 6→7）；`check_issues` 24/8 → **23/9** rc=0。系任务书 step 1 授权的收口项。
- **未 push**：`origin/master..HEAD` = **1**（待主会话 push）。
