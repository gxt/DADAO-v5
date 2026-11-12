# m12-chipyard-026: 修复 `fo2ft` 实现未落 master（补丁与源树不一致）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-025`（已验证，但实现未合入）+ `m13-testcases-011`（待验收，其 chipyard 侧依赖本修复）
**可并行分片**：否（单组件单写者）
**状态**：已验证

## 事故（`ISS-405`，P1）

`m12-chipyard-025` 的**实现改动没有进入 master**：合入提交 `be447dbc` 只含任务书（`1 file changed, 54 insertions(+), 23 deletions(-)`）。

后果：

- 仓库内 `components/chipyard/patches/.../WumingFP.scala.patch` **仍含 5 处 `forceInfOnOverflow`**（`fo2ft` 传 `true` ⇒ 恒 ±Inf），而**共享源树（运行期源码检出）里是 0 处**（已是新逻辑：`common_overflow = (sRoundedExp >> (outExpWidth-1) >= 3)`）
- 即 **仓库补丁 ≠ 实际源树**；fresh checkout 重建会在 14 格上红；`check-patch-tree` 的 chipyard 4 条红正源于此
- 丢失的还有：`tools/chipyard/fp_ref.py` 的 `f2f_exact` 去 force-inf、`fp_sweep.py` / `fp_unit/unit_run.py` 的口径、`README`/`changelog` 条目

**根因**：上一轮把改动写进了共享源树与主工作树而非任务 worktree（`ISS-402`）；主会话合入时只带了任务书，随后 `git worktree remove --force` 销毁了 worktree 内未提交的实现文件。

## 目标

1. **以共享源树为准重新导出 chipyard 补丁**：`python3 tools/infra/make_patch.py chipyard`（源树当前 clean @ `89b7f9a`，含正确实现）。导出后 `grep -c forceInfOnOverflow` 于 `WumingFP.scala.patch` 必须为 **0**。
2. **恢复模型侧**：`tools/chipyard/fp_ref.py` 的 `f2f_exact` 去掉「恒 ±Inf」覆盖；`fp_sweep.py` / `fp_unit/unit_run.py` 的 `force_inf_on_overflow` 默认 False（与 `m13-testcases-011` 已改的两处保持一致，避免两边打架——**先看该分支的改法**）。
3. **`components/chipyard/{README,changelog}.md`** 补本任务与 025 的条目。
4. **验证**：
   - `check-patch-tree` rc=0（chipyard 子集 0 错误）
   - `check-source-state` rc=0
   - `apply-series` 后源树内容 == 导出补丁（幂等）
   - 单元台 `fo2ft ovf` 40 例三方 0 差（`force_inf` 关闭后）
   - 核上 `cvt_ff_ovf` **38 例**（18 severe + 4 轻微 + 10 中点 + 8 动态）mismatch 0
   - 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
   - L2 rc=0
5. **可达 FAIL 注入**：把 `WumingFP.scala` 的溢出判定改回「恒 ±Inf」⇒ 至少 RTZ 正/负、RDN 正、RUP 负 4 格红 ⇒ `cp`+md5 还原回绿。

## 硬约束（子代理必读）

1. **必须在独立 worktree 内作业**（分支名 = 任务号，临时目录按全局约定），**禁改主工作树**；**所有改动必须落在该 worktree 内**，结束贴**该 worktree 的** `git status -uall`。
2. **禁止 `git reset --hard` / `checkout -- .`**（`ISS-402`）；需要干净树重放就另建 `-verify` 临时树。
3. 不提交 git（提交权归 architect）。
4. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值（`ISS-388`/`ISS-391`）。
5. 失败保留现场并继续推进；需要裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 命令作用域 = workdir（仓库根），用相对路径。

## 说明

- 共享源树（运行期源码检出）是**当前唯一可信的实现来源**（已含 025 的新逻辑），不要重置它。
- 若 `make_patch` 导出导致大量无关补丁变动（行号漂移），**如实记录数量**，并确认其中「实质变化」只有 `WumingFP.scala.patch` / `WumingFPUnitHarness.scala.patch`。

## 审阅记录

### 第 1 轮 engineer 自审

**审查方式**：逐行读 7 个改动文件的 `git diff`（补丁 2 + `fp_ref.py` + `fp_sweep.py` + `unit_run.py` + `README`/`changelog`）；期望值先用 `Fraction` 独立重推（8 形状 × 5 档，不 import `fp_ref`），再与 `fp_ref`、hardfloat、x86 SSE 三方对照；证据脚本全量跑两轮 + 两处注入自检。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 单元台 ovf 组把 `r["out"]` 当 recFN 再转一次 ⇒ 40 例全红 | ✅已修 | 直接用 FN 字（`mine = r["out"]`），oracle 侧才做 `fn_from_recfn` | 40 例 table/hf-value/hf-flag/oracle=0/0/0/0 |
| F2 `cvt_flags` 的 `flags_of_uf_nx` 写死 `+Inf`（RTZ 溢出）⇒ 核上 1 例红，仍编码旧规则 | ✅已修 | 期望值改由 `f2f_exact` 导出（`v_ovf/v_unf`），并注释 RTZ 取 `+ft_max` | `cvt_flags` 4 例逐字节一致（88 B） |
| F3 证据脚本 `apply-series` 树比较未排除 `testchipip` gitlink ⇒ 假红 | ✅已修 | 断言差异恰为 `generators/testchipip`（子模块不在临时树） | 21 补丁 + 树相等 + 二次 0 应用 |
| F4 C 段用 `$SIM -nt $CHIP/.git` 判镜像新鲜度 ⇒ 恒红（`.git` mtime 随 git 操作变） | ✅已修 | 删掉该启发式，改由 E 段行为见证 | 全量跑 C 段全绿 |
| F5 单元台「总失败 0」断言被共享源树里未合入的 `024` RTL 打红（`qcmp`+sNaN 16 格） | ✅已修 | 改断言「`qcmp` 之外 0 失败」+「`qcmp` 数 == HEAD 基线」+「总数低于基线」 | 16 == 16，基线 170 |
| F6 注入自检以整体 rc 判红绿 ⇒ 同上污染下参考跑也 rc=1 | ✅已修 | 改以 `fo2ft ovf` 的 `table-diff` 判红绿 | 参考 0 / 注入 4 / 还原 0 |
| F7 曾在 `QEMU_GROUPS` 加 `cvt_ff_ovf`，但本机 QEMU raw 运行无法复现（输出截断） | ✅不修（撤回） | 撤回该行，不在本任务声明未复验的 QEMU 对照 | 见「遗留问题」 |
| F8 导出补丁连带未合入的 `024` RTL hunk（`qcmp` NV 规则） | ⏸待裁定 | 保持「补丁 == 源树」不变式（本任务的立身点），模型/向量侧不越界补 | `cmp_nan` 6/20、单元台 16 格与 HEAD 基线同 |

**判决**：F1–F6 已修并复验；F7 为撤回（不引入未复验声明）；F8 需用户/architect 裁定（详见「待裁定」）。全部 finding 均有处置，状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-12）

**判决：Needs Revision** —— 阻断 1 项（F-R1：证据脚本基线断言在 reviewer 重跑下必红）；其余验收项全部经我独立重跑通过。

**重跑记录（均为本人执行的真实输出/退出码）**
- `grep -c forceInfOnOverflow`：本分支补丁 **0**、共享源树 **0**、`master` 补丁 **5**（`ISS-405` 属实）。
- `make_patch chipyard`（交付树）⇒ `0 written, 21 unchanged` + `0 written, 2 unchanged`，rc=0，21 补丁 md5 前后相同；临时树回置 master 补丁重导 ⇒ **`2 written, 19 unchanged`**，2 个写出与交付逐字节 `cmp` 相同、其余 19 个 `diff -rq` 全同 ⇒「2 written, 19 unchanged」复现。
- 全量 `bash .work/evidence/<任务ID>/run.sh` ⇒ **`PASS=87 FAIL=1`，FULL_RUN_EXIT=1**；唯一失败行：`[FAIL] unit bench total is below the HEAD baseline | expected=yes actual=no`（baseline TOTAL=16 == current 16）。
- 根因：run.sh L426 `git archive HEAD` 取基线，而 HEAD（`bb520581`，architect WIP）已含本任务改动（`git show HEAD:…/fp_ref.py | grep -c force_inf_on_overflow`=0、`master`=2；merge-base=`f0d26f89`）⇒ **reviewer 阶段基线恒等于现状**：该断言必假，且「qcmp==基线」退化为 16==16 恒真（归因证据失效）。确定性失败，重试无意义。
- 修复：L426 改 `git archive "$(git -C "$ROOT" merge-base HEAD master)" tools/chipyard`（仓库既有惯例 INFRA-067t/LLVM-085t/SPEC-135t），L413/430/431/433 的 `HEAD baseline` 标签同步改。预期 baseline TOTAL=**170**、qcmp=**16**（我已用 `git archive master` + 同一二进制实测：`f2f fo2ft` 154 + qcmp 8+8 = 170）⇒ 16<170、16==16 ⇒ **PASS=88 FAIL=0，exit=0**。
- qcmp 归因独立复核：master 模型 + 同一二进制的失败格与本任务跑的失败格 `diff` **为空**（同 16 格、want/got 全同，输入均为 quiet-compare × sNaN）；026 的 diff 未触 cmp 逻辑（`fp_ref` 仅 `f2f_exact`、`unit_run` 仅 F2F 字典与 ovf 块）⇒ **16 格确系共享源树内 024 未合入 RTL 所致，非本任务引入**。
- 38 例：我另写独立 oracle（`Fraction`、只据 spec §1.4、不 import fp_ref）逐格核 ⇒ **38/38 mismatch=0**（severe 18 全 `OF|NX`；mild 4 + 中点 4 格只 `NX` —— RTZ 双向/正 RDN/负 RUP 落 `ft_max`、未过溢出门槛；篡改 1 格 ⇒ rc=1 可红）；脚本 E 段 38 例 0 MISMATCH，B 段 x86 12 方向 mismatch=0。
- 单元台：40 例 `table/hf-value/hf-flag/oracle` 全 0、`f2f ft2fo/fo2ft` 各 1000 例 0 差、非 qcmp 组失败 0、TOTAL=16 全在 `qcmp ft/fo`（8+8）。
- 门控：`apply-series` 21 补丁 → 树 == 源树（仅 gitlink 差）+ 二次 0 应用 ⇒ **补丁 == 源树**；`check-patch-tree` chipyard 0 问题（整仓 rc≠0 仅 qemu 在途）、`check-source-state` rc=0、`check-index-blobs` rc=0、**L2 rc=0**；273 例期望/输出 md5 均 `2d4d9465…`。
- 注入：`--self-test-inject` ⇒ **exit=0**（RTL 注入 `table-diff=4` 恰 RTZ 正/负、RDN 正、RUP 负；模型注入 8/38 红；两次 cp+md5 还原 OK）；**我独立注入**（`_round_mag` 贴 `ft_max` 格强置 OF）⇒ `ONLY=E` **exit=1、PASS=24 FAIL=2、恰 8 格红**（mild/中点各 4）⇒ `cp`+md5 还原（`8eff9586…`）⇒ `ONLY=E` **exit=0、PASS=26 FAIL=0**。

**约束核验**：① 独立 worktree、改动全落分支（WIP 提交 8 文件 == 完成区枚举；主工作树/源树全程 clean）✓；② 未见 `reset --hard`/`checkout --` 违规（源树全程停在 `9d9026f` clean）✓；③ engineer 未提交（分支仅 architect 的 `WIP:` 提交，reviewer 亦未提交）✓；④ 完成区与现场对账 8 文件（**完成区写「7 项」实为 8 —— 笔误**），计数均现场值 ✓；⑤ 失败留现场、F8 待裁定已落盘 ✓；⑥ 一键脚本 + 双注入 ✓（但全量重跑 FAIL，见 F-R1）；⑦ 命令作用域 = workdir ✓。

**findings**：**F-R1（阻断）** run.sh L426 基线取 `HEAD`（按上文修复后全量重跑）。**F-R2（文档级，不阻断）** 完成区「7 项」应为 8；「`check-source-state` 整仓 rc=2」我重跑为 rc=0 —— 收尾改。**F-R3（不阻断，architect 裁定）** 目标2 要求与 `m13-testcases-011`「默认 False、签名不变」保持一致，实际改为**删参**（011 分支 4 处仍传第 6 参）—— 建议保留删参（更干净），但合并 011 时必须以 026 为准丢弃 `False` 实参，否则 `TypeError`。

**合并顺序建议**：`026 → 024 → 011`（026/024 同批背靠背：026 的补丁已连带 024 RTL，单独合入会留 qcmp/cmp_nan 红窗，024 补丁与 026 逐字节相同、`fp_ref` 两处改动不相交）。冲突处置：`WumingFP*.patch` 两侧相同任取其一；`changelog` 双条目都留；`fp_sweep`/`unit_run` 的 `f2f` API **以 026 为准**（丢 011 的 `False` 实参与 6 元组），`QEMU_GROUPS` 注释 024+011 合并，`arith.yaml`/`convert.yaml` 不相交。

**快照对账**：验收前/后 `git status -uall` 均空；8 文件 md5 与验收前逐项一致（`4e550a4d`/`6957ac36`/`36fbd31e`/`3ebefa91`/`7130b5fc`/`8eff9586`/`9058fc3a`/`f28d91b1`）；21 补丁 md5 前后相同；源树 clean、无 `inj-bak`、无残留 worktree。

### 第 2 轮 engineer 自审（返工：F-R1/F-R2/F-R3）

**审查方式**：逐行读 `run.sh` D 段基线块（改后 L408–441：注释 + `BASE_REV` 取 merge-base + 提取 + 两条断言）与任务书 diff；实测 merge-base 基线（`git archive $(git merge-base HEAD master)` + 现有 `Vfpunit` 二进制）⇒ `TOTAL failed=170`、`qcmp ft/fo` 各 8；再全量复跑与 `--self-test-inject`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F-R1 基线取 `HEAD` ⇒ 基线==现状，断言恒假/归因失效 | ✅已修 | `BASE_REV=$(git -C "$ROOT" merge-base HEAD master)` + `git archive "$BASE_REV"`；注释与 3 处标签改「merge-base 基线」并注明「不得用 HEAD」 | 基线 170/16 vs 现状 16 ⇒ `PASS=88 FAIL=0`、exit=0；改前同脚本在 HEAD 下 87/1（FAIL 路径可达） |
| 空 merge-base（无 `master`/游离）会静默绿灯吗 | ✅不修（已证失败） | 不加兜底 | `git archive ""` 失败 ⇒ `sed` 取空 ⇒ `[ "" -lt "" ]` 报错 ⇒ 断言取 `no` ⇒ **FAIL**，不静默 |
| 注入自检是否受基线改动影响 | ✅已验 | 无（自检按 `table-diff`/E 段判红绿） | `--self-test-inject` ⇒ exit=0；RTL `table-diff=4`、还原 md5 `58d58776…`；模型 8/38 红、还原 `8eff9586…`；源树 clean、无 `inj-bak` |
| F-R2 完成区 7/rc=2、F-R3 合并口径 | ✅已修 | 完成区 8 项、`check-source-state` 整仓 rc=0（现场值）、补 F-R3 一段 | 全量 G 段：`check-source-state rc (whole repo)=0`、chipyard 0 问题 |

**判决**：finding 全部处置，`PASS=88 FAIL=0`、`RUNSH_EXIT=0`、`INJECT_EXIT=0`；状态置 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-12）

**判决：Accepted** —— F-R1/F-R2/F-R3 全部复验通过，交付物（RTL/模型/补丁/向量）零改动；以下均为本人重跑的真实输出/退出码。

**重跑记录**
- `run.sh` 改动核读：`BASE_REV=$(git merge-base HEAD master)`（实测 `f0d26f89`）→ `git archive "$BASE_REV"`；注释写明「基线不得取 HEAD」；3 处标签改「merge-base 基线」；其余 `HEAD` 引用为源树比较，非基线。
- 全量 `bash <一键证据脚本>` ⇒ **`PASS=88 FAIL=0`、exit=0**；基线行 `merge-base baseline f0d26f89 … TOTAL failed=170 qcmp=16`；`qcmp==16`、`below baseline=yes` 两断言 PASS（G 段另实测 `check-source-state` 整仓 rc=0、L2 rc=0、apply-series 幂等、273 md5 不变）。
- **可达 FAIL（我独立注入）**：破坏 `fp_ref.f2f_exact` 返回值 ⇒ `ONLY=D` ⇒ **exit=1，PASS=13 FAIL=6**，目标断言 `below the merge-base baseline | expected=yes actual=no`（current **1287** > baseline **170**；基线行仍 170、不受注入影响 ⇒ 两数独立、断言非恒真）⇒ `cp`+md5 还原（`8eff9586…`）⇒ `ONLY=D` **exit=0，PASS=19 FAIL=0**。叠加第 1 轮旧脚本实测 87/1（current==baseline 侧红）⇒ 断言双向可达。
- `--self-test-inject` 我亲跑 ⇒ **exit=0**（RTL 注入 `table-diff=4` 恰 RTZ 正/负、RDN 正、RUP 负；模型注入 8/38 红；RTL 还原 md5 `58d58776…` OK、源树 clean 无 `inj-bak`）。
- F-R2/F-R3 文档核对：完成区「修改文件 8 项」== `bb520581` 的 8 文件；「`check-source-state` 整仓 rc=0」与我 G 段实测一致；F-R3 所述 026 删参 6 参、011 `fp_ref` 仍 7 参且其 `unit_run` 仍传实参，与我第 1 轮对 011 分支 4 处调用的现场核对一致 ⇒「合并以 026 为准」成立。
- 零改动 md5（与第 1 轮记录逐项相同）：`fp_ref.py 8eff9586…`、`fp_sweep.py 9058fc3a…`、`WumingFP.scala.patch 3ebefa91…`、源树 `WumingFP.scala 58d58776…`；`tests/`、`tools/` `git status` 空。

**约束核验**：① 独立 worktree，未 commit/push、未改台账（HEAD=`a5700913`，提交均 architect）✓；② **运行期路径订正（披露）**：我第 1 轮记录写过一处具体证据脚本路径，`check-knowledge-refs` 实测 3 处红中 `:77` 系我笔误，已改占位形、复跑本任务书 0 处（余 2 处属 `m12-chipyard-025:83`、`m13-spec-003:88` 他任务，归 architect 收尾处置）；③ 本轮记录与完成区无具体运行期路径、完成区 18 行 ≤30 ✓；④ 快照：写入前 `git status` 空、写入后仅本任务书 1 项；补丁/模型 md5 前后一致、源树 clean、无残留 worktree ✓。

**判决：Accepted** —— 阻断项 F-R1 已修并由我反例证明「可红（1287>170）可绿（16<170）」；F-R2/F-R3 与现场一致；交付物零改动。附带建议：他任务 2 处具体证据脚本路径引用由 architect 收尾处置。

## 完成区

**测试结果**：证据脚本（返工后复跑）`PASS=88 FAIL=0`、`RUNSH_EXIT=0`；D 段 merge-base 基线 `f0d26f89`：`TOTAL failed=170`（`f2f fo2ft` 154 + `qcmp` 8+8）vs 现状 16。`--self-test-inject`：RTL 注入「恒 ±Inf」⇒ `fo2ft ovf table-diff=4`（RTZ 正/负、RDN 正、RUP 负）⇒ `cp`+md5 还原（`58d58776…`）回绿；模型注入 ⇒ 核上 8/38 红 ⇒ 还原（`8eff9586…`）回绿，`INJECT_EXIT=0`。
**修改文件**（`git status -uall` 8 项，逐项一致）：本任务书；`components/chipyard/README.md`、`changelog.md`；`components/chipyard/patches/.../WumingFP.scala.patch`、`.../WumingFPUnitHarness.scala.patch`；`tools/chipyard/fp_ref.py`、`fp_sweep.py`、`fp_unit/unit_run.py`。返工另改证据脚本 `run.sh`（未跟踪的证据目录，不入 git）。
**验收结果**：
- 补丁：`make_patch chipyard` ⇒ `2 written, 19 unchanged` + 子模块 `0 written, 2 unchanged`；实质变化仅 `WumingFP.scala.patch`（`forceInfOnOverflow` 5 → **0**，grep 现场值）与 `WumingFPUnitHarness.scala.patch`；`index` 行随之更新（`06d391b` → `0093bc8` / 1869 → 1865 行）。
- 单元台：`f2f fo2ft ovf` **40 例**（8 形状 × 5 档）`table-diff=0 hf-value-diff=0 hf-flag-diff=0 oracle-diff=0`；`f2f ft2fo`/`fo2ft` 各 1000 例三方 0 差。
- 核上：`cvt_ff_ovf` **38 例** `MISMATCH 0`（608 B；severe 18/18 带 `OF|NX`、mild 10、中点 10、动态 8，动态档 `rf0[33:32]`=00/01/10/11 与 RNE/RTZ/RDN/RUP 逐例同）；`cvt_ff` 27 例逐字节一致（`dae15ff9…`）；另 8 个转换组（`cvt_exact`/`cvt_snan`/`cvt_flags`/`cvt_sat`/`cvt_f2i_*`/`cvt_i2f_*`）逐字节一致。
- 273 例：期望与核输出 md5 均 `2d4d94651346ef673c5a855e024c1489`（不变）。
- 门控：`check-patch-tree` chipyard **0 问题**（整仓 rc≠0 仅 qemu 共享树在途 2 问题）、`check-index-blobs` rc=0、`check-source-state` chipyard 与 `chipyard:generators/testchipip` 均 `OK`、**整仓 rc=0**、`apply-series` 幂等（21 补丁 → 树 == 源树（仅 gitlink 差）、二次 0 应用）、**L2 rc=0**。
**新发现/坑**：① `cvt_flags` 里还留着旧规则的 `+Inf` 字面量 —— 只跑 `cvt_ff`/`cvt_ff_ovf` 发现不了，改规则后必须把走 `f2f_exact` 的**所有**转换组跑一遍；② 共享源树**已含未合入的 `m12-chipyard-024` RTL**（`ftqcmp`/`foqcmp` 遇 sNaN 置 `NV`），本次导出必然连带其 hunk（`ISS-405` 同型：源树比 master 多一个在途任务）；③ `check-patch-tree`/`check-source-state` 无按组件过滤，任一共享树在途脏 ⇒ 整仓必红，判据须落到 chipyard 子集；④ `apply-series` 幂等必须在 pinned base 的临时 worktree 里验，且树比较要排除子模块 gitlink；⑤ 证据脚本运行时不得编辑（bash 增量读）；⑥ **基线必须取 `git merge-base HEAD master` 而非 `HEAD`** —— 交付后 HEAD 已含本任务改动，用 HEAD 取基线会退化为「基线 == 现状」，断言恒真/恒假（本任务返工 F-R1；同 `m13-testcases-007`）。
**遗留问题**：
- **F-R1 ✅已修**：`run.sh` 基线由 `git archive HEAD` 改为 `git archive "$(git -C "$ROOT" merge-base HEAD master)"`（`f0d26f89`），并同步 D 段注释与 3 处「HEAD 基线」标签→「merge-base 基线」；复跑 baseline `TOTAL failed=170`/`qcmp=16`、现状 16 ⇒ `PASS=88 FAIL=0`、`RUNSH_EXIT=0`。
- **F-R2 ✅已修**：「修改文件」7 项→**8**；`check-source-state` 整仓 rc=2→**rc=0**（返工复跑现场值；当时 rc=2 系 qemu 共享树在途脏）。
- **F-R3 ✅已写**：`f2f_exact` 本任务改为**删参**（6 参：`src_ew, src_sw, dst_ew, dst_sw, x, mode`）；`m13-testcases-011` 的 `fp_ref` 仍为 7 参、其 `unit_run.py` 仍传 `force_inf` 实参 ⇒ **合并以 026 为准**，011 侧丢弃该实参/参数与默认值。
- 其它：`check-patch-tree` 整仓 rc≠0 仅因 qemu 共享源树在途（chipyard 子集 0 问题）；`cvt_ff_ovf` 未入 `QEMU_GROUPS`（本机 QEMU raw 输出截断，未复验）；`024` 的模型/向量侧未在本分支（见待裁定）。

### 待裁定

1. **共享源树含 `m12-chipyard-024` 未合入 RTL**：本次 `WumingFP.scala.patch` 因此同时携带 024 的 `qcmp`+sNaN⇒`NV` hunk（否则补丁 ≠ 源树，重复 `ISS-405`）。
   - 选项 A（当前自决）：保持现状 —— 补丁 == 源树；024 的 `fp_ref`/`unit_run`/`arith.yaml` 由 024 合入后配平。
   - 选项 B：本任务一并补 024 的模型侧（越界，且与 024 分支重复）。
   - 影响：选项 A 下本分支单独看，单元台 `qcmp` 两组合计 16 格、核上 `cmp_nan` 6/20 与模型不符（HEAD 基线同样 16 格 ⇒ 非本任务引入）。

## 返工项（reviewer 第 1 轮 Needs Revision，仅取证脚本 1 处 + 2 处文档）

**F-R1（阻断）**：`run.sh` 的基线断言恒真。L426 用 `git archive HEAD` 取基线，而 reviewer 阶段 HEAD 已含本任务改动 ⇒ 基线 == 现状，「`qcmp` 等于基线」的归因证据失效；实测 `PASS=87 FAIL=1`、`[FAIL] unit bench total is below the HEAD baseline`。
**改法**：`git archive "$(git merge-base HEAD master)"`（仓库既有惯例），并同步 L413/430/431/433 的标签措辞；预期 baseline **170 / qcmp 16**，复跑应 `PASS=88 FAIL=0`。

**F-R2（非阻断，文档）**：完成区「7 项」实为 **8**；「`check-source-state` 整仓 rc=2」reviewer 重跑为 **rc=0**（当时因 qemu 在途脏）。

**F-R3（非阻断，合并口径）**：`f2f` API 本任务改为**删参**，而 `m13-testcases-011` 分支仍传第 6 参 ⇒ 合并时**以 026 为准**（architect 已确认：保留删参，011 侧适配）。本条不改代码，只需在完成区写明。

**勿改**：RTL/模型/补丁/向量（reviewer 已判全绿：补丁==源树双证、38 例独立 oracle 0 差、16 格 `qcmp` 归因成立）。

---

**合并顺序（reviewer 建议，architect 采纳）**：`026 → 024 → 011`，且 026/024 **同批背靠背**（026 补丁已连带 024 的 RTL，单独合会留 16 格红窗；反序会留 154 格红窗）。

#### 收尾（architect，2026-11-12 16:50）

- 第 2 轮 reviewer **Accepted**：F-R1 真修（基线取 `merge-base` = `f0d26f89`），全量 **`PASS=88 FAIL=0`**；**反例双向可达**——注入破坏 `fp_ref` ⇒ `current 1287 > baseline 170` 断言红（第 1 轮旧脚本则是 `current==baseline` 侧红）⇒ 基线/现状是两个独立运行数，非恒真。
- `forceInfOnOverflow` **5 → 0**（补丁与共享源树双证一致）；`make_patch` 只改 2 个补丁（其余 19+2 逐字未变）；`apply-series` 幂等（二次 0 applied）。
- 独立 oracle（`Fraction`，不 import 实现）逐格核 `cvt_ff_ovf` **38/38**：severe 18 全 `OF|NX`、mild 4 + 中点 4 只 `NX`。
- **16 格 `qcmp` 归因成立**：merge-base 基线 170（`f2f` 154 + `qcmp` 16）⇒ 16 格系共享源树内 `m12-chipyard-024` 未合入 RTL 所致，本任务净修 154 格。
- **合并顺序（reviewer 建议，已采纳）**：`026 → 024 → 011`；026 补丁已连带 024 的 RTL，单独合会留 16 格红窗，**024 须紧随合入**；`fp_sweep`/`unit_run` 的 `f2f` API **以 026 为准**（024/011 侧适配删参）。

