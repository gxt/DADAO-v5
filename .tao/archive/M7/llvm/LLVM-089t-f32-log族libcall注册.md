# LLVM-089t: f32 `log` 族 libcall 注册（同类补全）

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-088t`（同改 `components/llvm-project/patches` 与 picolibc 过滤表 ⇒ **串行**）
**状态**：已验证

> 立项来源：用户 2026-10-12 裁定「**按同类补全（推荐）**」（承 `LLVM-087t` 的 `FLOG_F32` 待裁项）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：f32 `log` 族（`log`/`log10`/`log2`…）是否纳入、如何补。
- 选项：A「**按同类补全（推荐）**」／B「只补 `FLOG_F32`」／C「不补（登记范围外）」。
- **用户选择 = A「按同类补全（推荐）」** ⇒ 注册 `FLOG_F32`（及**现场确缺**的同族），并删过滤表挡 `sf_log10.c` 的那条。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## 目的 / 背景（事实）

- **ISA 无 `flog*` 指令**（`contracts/opcodes.yaml` 现场）⇒ 与**取整族同机制**：只能 **libcall 到 picolibc** 的数学函数。
- **DADAO 补丁未注册任何 `LOG_F*`**（`grep` 空）⇒ `sf_log10.c` 编译报 **`no libcall available for flog`**。
- picolibc **有实现**：`libm/math/{sf_log.c, sf_log10.c, sf_log2.c}`；sysroot `libc.a` **已有** `logf`/`log2f`/`expf`/`powf`；**`log10f` 缺**（因 **`sf_log10.c` 被过滤表挡住未编入**）。
- 受此阻塞：`test-log10`、`test-math-errhandling`（**2 条**）。

## 接口规范

- **输出**：
  1. **注册 f32 `log` 族 libcall**（`DADAOSubtarget.cpp.patch` 的 `initLibcallLoweringInfo`，与 f64 块**逐字对称**）：
     - **必做**：`FLOG_F32 → impl_logf`；
     - **按证据补**：以**现场报缺**（探针 `tools/testcases/picolibc-probe-*.sh` / 全量 test 输出 / `nm`）为准，逐条**给出证据**后补 `FLOG10_F32`/`FLOG2_F32`/`FEXP*_F32` 等；
     - ⚠️ **不得无证据扩范围**（**禁**"顺手把整个数学族都注册"）：**每条补的映射必须附现场证据**。
  2. **删过滤表**：删掉挡 `sf_log10.c`（等**现场确缺**）的条目；**核实最小必要**（删后这些源 `clang -c` rc=0；其余保留条目**仍确不能编**，抽样给失败输出）。
  3. **重建 + 全量 test**：`make check-picolibc-tests-full` ⇒ **四分类 before/after**（**before：`pass 196 / fail 0 / excluded 22 / blocked 17`**〔来源：`LLVM-088t` 落地后实基线，非 087t 时点的 `182/31`〕）+ **解锁清单**（预期 2）。
  4. 若 `nm` 前置校验出现**与预期不符**（如某实现符号在源与 sysroot 均缺）⇒ **停下报告**（**不得**自行以等价判据替代；`LLVM-087t` 教训 + `lessons §3.17`）。
  5. `.tao/knowledge/milestones.md` 流水更新 `LLVM-089t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**最小改动**；**不改** `spec/`、`contracts/`、`tests/vectors/`；**不改** f64 块；**计数不写死**。

## 验收标准

1. **注册生效**：`llc` 对 f32 `log`/`log10` 用例 **rc=0**，汇编中出现 `call [rb0, logf]`（真实片段）；**每条新增映射附现场证据**。
2. **解锁**：`test-log10`、`test-math-errhandling` **真跑 rc=0**（真实输出/退出码）；`fail` 仍须 **0**、**newly_blocked = ∅**。
3. **全量 test**：`pass` 上升、`blocked` 下降（before/after 现场统计 + 解锁清单）。
4. **越界最小**：过滤表删除条目**逐条**给"删前不能编 / 删后能编"证据；抽 ≥2 条**保留**条目仍失败。
5. **门控**：`make check`、`check-lit`、`check-patch-tree`、`check-index-blobs`、`check-no-residue`、`check-picolibc-tests` 各 EXIT=0。
6. **反例可失败**：注入（回退某条映射 / 改错实现名）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-089t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥、源树 `base+1`、`series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/llvm-project/patches/**`、`components/picolibc/patches/**`、`tests/llvm/**`、任务书、`milestones.md` 行）；越界须披露。
5. **遇显式硬约束或需语义裁定 ⇒ 先停下报告、保留现场**（**不得**自行以等价判据替代；`LLVM-087t` 教训）；**禁自拟自答**（`lessons §3.17`）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **计数不写死**。

## 完成区
**测试结果**：picolibc full 现场统计（JSON 见 `.work/evidence/<任务ID>/`）：before `pass 196 / fail 0 / excluded 22 / blocked 17` → after `pass 197 / fail 0 / excluded 22 / blocked 16`（total 235；`unlocked=1`、`newly_blocked=∅`、`pass +1`/`blocked −1`）。解锁 1 = `test-log10`（真跑 `exit 0`，log `max ulp 2` / `PASSED`）。⚠️ **未达任务书预期解锁 2**：越过 log10f 链接后，`test-math-errhandling`/`math_test` 撞**既有 QEMU softfloat 断言**（`softfloat-parts.c.inc:108 parts64_pick_nan`，signal 6；before 基线已有 5 条同类 `test-remquo-quo`/`test-ctan`/`test-ctanh`/`test-cpow`/`test-fma`），`test-math-funcs` 转缺 `__mulsc3/__muldc3`（`ISS-193`(a) 复数族）。**log10f 阻塞已清零**（四 test 聚焦跑现场 `log10f` 计数 = 0）。`nm` sysroot `libc.a`：before `logf T`/**`log10f` 缺** → after `logf T`/`log10f T`。
**修改文件**：① `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOSubtarget.cpp.patch`（`initLibcallLoweringInfo` 增 `RTLIB::LOG_F32 → RTLIB::impl_logf` + 依据注释；f32 族 8→9；f64 八条与 mem 四条**未动**）；② `components/picolibc/patches/meson.build.patch`（**越界披露**：删最后一条 (b) `sf_log10.c` + 其 3 行注释，过滤表 **3→2**）；③ `tests/llvm/lit/CodeGen/DADAO/p1-fp-libcall-logf.ll`（新增）；④ `.tao/knowledge/milestones.md` 本行；⑤ 任务书。**未改** `spec/`、`contracts/`、`tests/vectors/`、picolibc 源、f64 块（`git diff` 证据）。
**验收结果**：门控 `make check`(L1 PASS)、`check-lit`(**107/107**)、`check-patch-tree`(4 comp,123 patches OK)、`check-index-blobs`(88 new-file OK)、`check-no-residue`、`check-picolibc-tests`(fast 20: 17/0/2/1) 各 **EXIT=0**（`run.sh` 现场）。重建均 `setsid nohup` 脱离：`BUILD_MC_EXIT=0`（实测 284 s）、`INSTALL_HOST_EXIT=0`（162 s）、`BUILD_PICOLIBC_EXIT=0`（7 s）。`llc`（build 树）对 `llvm.log.f32` **rc=0**，asm `call [rb0, logf]`；installed `clang -S` 对 `sf_log10.c` **rc=0** 且含 `call [rb0, logf]`（before 同档 rc=1 `no libcall available for flog`）。证据 `.work/evidence/<任务ID>/run.sh` **rc=0**；`--inject` **rc=0**（I1 lit 错期望⇒rc=1；I2 删 `LOG_F32` 行⇒count 1→0；I3 源回退+重建 llc⇒IR rc=1+`no libcall available for flog`⇒`cp`+md5 还原⇒重建回绿 rc=0；三处还原 md5 逐一相等）。
**新发现/坑**：① 预期解锁 2 未达成，根因 = **跨模块既有缺陷**（QEMU softfloat NaN 断言；证据脚本 H 段现场计数 `pre_existing_same_crash=5`）+ `__muldc3` 缺口，**非本任务引入**（本任务只加注册 + 删过滤条目）。② `log10f` 唯一来源 `libm/math/sf_log10.c`，且该源**无 `__OBSOLETE_MATH_FLOAT` 守护**（`sf_log2`/`sf_log`/`sf_exp`/`sf_pow` 均有、走 `libm/common/sf_*`；**「无守护」非普遍：`sf_*` 中另有 31 个亦无守护，但均不消费 f32 数学 libcall；「唯一 `flog` 消费者」结论仅就本次 707 源扫描范围内成立**）⇒ 全库只有它需要 `flog`。③ **最小范围证据**：707 个 `libm/**/*.c` 逐源按真实 `-Oz -D_LIBC` 档编译，`no libcall available` **唯一集合 = {flog}（1 处）** ⇒ 只注册 `LOG_F32`，未注册 `LOG10/LOG2/EXP/POW_F32`（无现场证据）。④ `check-patch-tree` 断言⑨ 要求补丁文本与 `git diff base HEAD` **逐字相等**（含 hunk 头行号/计数），手改须同步；new-file 补丁须 `check-index-blobs --fix` 重算 blob。
**遗留问题**：① `test-math-errhandling`/`math_test` 待 QEMU softfloat NaN 修复（`QEMU-058t` 规划中）；② `test-math-funcs` 待 `__muldc3/__mulsc3`（`INFRA-067t` 待开始）；③ 组件 `changelog` 未加条目（`079t`–`088t` 同，从众）；④ 工作树另有**非本任务**外来件（`INFRA-069t/070t`、`SPEC-135t` 任务书，他会话产物，未触碰；证据脚本 scope 段显式打印）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查对象**：`DADAOSubtarget.cpp.patch`（新增 1 条注册 + 注释、hunk 头 `+1,90`、blob 重算）、`meson.build.patch`（删 (b) 1 条 + 注释、两个 hunk 头行号）、`p1-fp-libcall-logf.ll`、`.work/evidence/<任务ID>/run.sh`（逐行）。

**逐行审查结论**：① `RTLIB::LOG_F32 → RTLIB::impl_logf` 名字取自 `RuntimeLibcalls.inc` 现场（`LOG_F32 = 793`、`impl_logf = 2707`，**非猜测**）；`DADAOISelLowering.cpp` 早已把 `ISD::FLOG` 对 `{f32,f64}` 标 `Expand`（现场 187–194 行）⇒ 只补 impl 即足、**无需**改 lowering（最小改动）。② f64 八条 + mem 四条 + 087t f32 八条**未动**（脚本锚：f64 count=8、f32 count=9）。③ **未扩范围有证据**：707 源扫描唯一缺失 = `flog`；亦核 `sf_log10.c` 无 `__OBSOLETE_MATH_FLOAT` 守护故为唯一 `flog` 消费者（**该「唯一消费者」仅就本次 707 源扫描范围内成立**：`sf_*` 另有 31 个无守护条目不消费 f32 数学 libcall）。④ 过滤表仅删 `sf_log10.c`（3 行注释同步），保留 2 条**逐条**复验仍失败（`hash_page.c`→`Cannot select: i64 = bswap`；`atold_engine.c`→`unsupported library call`）。⑤ lit 钉**库名**（`call [rb0, logf]`）而非「能编过」，addend 防尾调用假绿；`CHECK` 与真实 asm 逐字对齐（现场 `llc` 输出)。⑥ 证据脚本每条断言可达 FAIL（I1–I3 现场 rc/计数/消息三重），计数全部现场统计。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1 任务书「预期解锁 2」未达成；实际解锁 1，另 3 条转**不同**既有缺口 | ✅已核实并如实登记（非本任务引入） | 完成区「测试结果/新发现①/遗留①②」 | after JSON 现场分桶；`pre_existing_same_crash=5`（before 基线同断言）；聚焦跑 `log10f` 计数 0 |
| 2 手写补丁与 `git diff base HEAD` 不逐字一致（3 处：new-file 计数 88→90、picolibc `+1924,38`→37、`+1971`→1970） | ✅已修 | 更正 3 处 hunk 头；`check-index-blobs --fix` 重算 new-file blob（`159425c6e`→`a8d5ed2e4`） | `check-patch-tree` 断言⑨ rc=0；与真实 `git diff` 逐字 `diff` 为空（两补丁） |
| 3 证据脚本首轮 scope 检查 FAIL（`milestones.md` 流水行未落） | ✅已修 | 补 `LLVM-089t` 行（状态 `待验收`/`完成时间` `—`） | 复跑 `run.sh` rc=0（scope `count=4`） |
| 4 证据脚本 F 段源路径写错（`libc/string/hash_page.c`、`libc/stdlib/atold_engine.c`）⇒ 首轮**假 FAIL**（clang「no such file」rc=1 被误当「确不能编」） | ✅已修 | 改实际路径（`libc/search/`、`libc/stdio/`），断言改为「rc!=0 **且**命中真实错误消息正则」 | 复跑 `hit=1`（bswap / unsupported library call） |
| 5 注入 I2/I3 的 `sed` 模式失效（`\(`…`\);` 在 BRE 下不匹配）⇒ 首轮 `--inject` 3 条假 FAIL | ✅已修 | 改字面模式 `\#Info.setLibcallImpl(RTLIB::LOG_F32, RTLIB::impl_logf)#d` | 复跑 `--inject` rc=0：I2 count 1→0、I3 md5 differs + IR rc=1 `msg=1` |
| 6 `tools/testcases/picolibc-probe-fp.sh` 未加 f32 `log` 探针 | ⏸不修 | 未改（该文件非本任务输出） | 验收 1 由 `llc`/`clang -S` + lit 直证；「非抽样」由 **707 源全量扫描**覆盖，强于单探针 |
| 7 087t 注释「…ffloor/flog」举例在本次注册后略陈旧 | ⏸延后 | 未改（最小改动，不碰既有注释） | 该注释描述 087t 当时缺口，属历史依据 |
| 8 组件 `changelog` 未加条目 | ⏸延后 | 与 `079t`–`088t` 从众 | — |

**判决**：findings 1–5 ✅已修/已核实，6–8 ⏸延后（有先例/超范围、非阻断）；状态 → `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**（全部本机真实输出/退出码，workdir=仓库根）：
1. 门控：`make check`、`check-lit`、`check-patch-tree`、`check-index-blobs`、`check-no-residue`、`check-picolibc-tests` **各 EXIT=0**（`check-lit` `Total 107 / Passed 107`；`check-patch-tree: 4 component(s), 123 patches OK`；`check-index-blobs: 88 new-file patch(es) OK`；`check-picolibc-tests` `stage=fast total=20 pass=17 fail=0 excluded=2 blocked=1`）。
2. 证据脚本 `<>/run.sh --inject` **rc=0**：A–L 全绿（`LOG_F32` count=1、f64 count=8、f32 count=9、`call [rb0, logf]` count=1、`log10f`/`logf` 各 T、`pre_existing_same_crash=5`）；I1 lit rc=1 / I2 count 1→0 / I3 `rc=1,msg=1`，三处 md5 还原逐一相等。脚本逐条断言均有可达 FAIL 路径、计数现场统计、无恒真。（engineer 3 次重建 `*_EXIT=0` 采信未重跑，产物正确性由 llc/nm/门控直证。）
3. 全量我自己重跑（`setsid nohup`、`--jobs 8`、`FULL_EXIT=0`）：`total=235 pass=197 fail=0 excluded=22 blocked=16`；对照 before JSON（`196/0/22/17`）：`unlocked=[test-log10]`、`newly_blocked=[]`、`pass +1`、`blocked −1`、`fail=0`、`same_inventory=True`、after `log10f` 阻塞=0。**四数差值 +1/−1 属实**。

**「按证据补=0」独立复核**：真实档（`-Oz -nostdlib -D_LIBC`）抽样编译 **24** 个 `libm/**/*.c`（含 `sf_log.c`/`sf_log2.c`/`sf_log10.c`/`sf_exp.c`/`sf_pow.c`/`s_log10.c`）⇒ 24/24 rc=0、`no libcall available` 零命中；另独立全扫 **707** 源 ⇒ `no libcall available` **零命中**（227 个报错源全在 `libm/ld/**` 与 `libm/machine/{aarch64,hexagon,spu}`，非 f32 数学 libcall 消费者）。⇒ 无其它 f32 数学 libcall 确缺，只注册 `LOG_F32` 成立。

**注册核**：`git diff` 逐条——mem 4 条 + f64 8 条与 HEAD 逐行同（未动）；新增仅 `LOG_F32 → impl_logf` 1 条（`LOG_F32=793`/`impl_logf=2707` 现场核，非猜测）；f32 8→9。我自跑 `llc` rc=0 + `call [rb0, logf]`；`clang -S sf_log10.c` rc=0 且含 `call [rb0, logf]`；`nm libc.a` `logf T` / **`log10f T`**（现为 T）。

**解锁核**：`test-log10` 我自己真跑 **exit 0**（`max ulp 2`/`PASSED`）；`log10f` 阻塞计数=0；`newly_blocked=∅`、`fail=0`。

**未解锁 2 条归因核（如实，非掩盖）**：我的 after 现场——`test-math-errhandling`/`math_test` 均 `softfloat-parts.c.inc:108:parts64_pick_nan: code should not be reached`（signal 6）；before 基线同断言 **5** 条（`test-remquo-quo`/`test-ctan`/`test-ctanh`/`test-cpow`/`test-fma`）⇒ after 7 条，确为既有 QEMU softfloat 缺陷、非本任务引入。`test-math-funcs`：`ld.lld: error: undefined symbol: __mulsc3`（reason 字段 `__muldc3`）⇒ 复数乘法缺口，归因成立。

**越界核**：过滤表 3→2（`git diff` 仅删 `sf_log10.c` 1 条 + 注释同步，无其它误删）；删前 rc=1 `no libcall available for flog`（留存日志）/ 删后我编 rc=0；保留 2 条我复跑仍 rc=1：`hash_page.c` `Cannot select: ... bswap`、`atold_engine.c` `unsupported library call`。最小必要 ✓。

**我的独立注入（非 I1/I2/I3）**：`impl_logf`→**存在但错误**的 `impl_log2`（补丁+源树同步、`ninja llc` rc=0）⇒ asm 变 `call [rb0, log2]`；同一脚本 **rc=1**：A `LOG_F32->impl_logf` count=0、B `call [rb0, logf]` count=0、`make check`/`check-patch-tree`/`check-index-blobs` FAIL；`cp`+md5 还原（patch `7475e66e…`、src `a7d2e1a1…` 与备份相等）+ 重建 ⇒ 同一脚本回绿 **rc=0**（`ALL CHECKS PASSED`）。

**快照对账**：验收前后 `git status --porcelain -uall` 逐行相同、5 个目标文件 md5 全等；与「修改文件」5 项一致（外来件 INFRA-069t/070t、SPEC-135t 未触碰）。

**约束核验**：最小改动 ✓；不改 `spec/`/`contracts/`/`tests/vectors/` ✓；f64/mem 块未动 ✓；计数不写死 ✓；反例可达 FAIL + `cp`/md5 还原（禁 git restore）✓；无契约/断言弱化、无凑绿 ✓；临时文件全在 `/tmp/opencode/<任务ID>-review/` ✓。

**判决：Accepted**（工程师交付达标：注册正确且最小、越界最小必要、全量 +1/−1、门控全绿、证据链独立复核成立）。阻断项：无。**供架构师定夺（非工程师可修）**：任务书验收标准 2 的 `test-math-errhandling`/`math_test` 半条未达（预期解锁 2 实际 1）——撞既有 QEMU softfloat NaN 缺陷（`QEMU-058t`）与 `__muldc3/__mulsc3` 缺口（`INFRA-067t`），均越界不可修、归因有据、已如实登记。
非阻断建议：① engineer 自审②「其余 f32 数学函数有 `__OBSOLETE_MATH_FLOAT` 守护」过宽（`sf_acos.c` 等 31 个 `sf_*` 无守护，实为不依赖 f32 数学 libcall），建议措辞收窄；② 任务书接口规范 before `182/31` 系 087t 时点陈旧数（真基线 = 088t 后 `196/0/22/17`），下发前宜对齐。
