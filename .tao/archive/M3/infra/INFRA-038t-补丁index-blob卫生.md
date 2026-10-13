# INFRA-038t: 补丁 index blob hash 卫生（new file mode 补丁）

**模块**：infra
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地（**无需**组件重建：仅补丁文件元数据）

## 目标与 resolved_by

处理 1 条无依赖的补丁卫生 issue（低优先级）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-119 | `new file mode` 补丁的 `index 0000000..<hash>` blob hash 与实际内容失配（pre-existing，不影响 `git apply`） |

`resolved_by`：本任务 `INFRA-038t`。

## 接口规范

- **输入**（主会话初筛：LLVM 7 项 + QEMU 2 项 = 9；本架构核实以任务执行时的**机械重算**为准）：
  - `components/llvm-project/patches/**/*.patch`、`components/qemu/patches/**/*.patch`。
  - 现状：`make check-patch-tree` **EXIT=0**（断言⑥只比对 scratch index 内容 vs `.work/source`，**不校验 patch 内 `index` 行字面 hash**）。
  - 架构快速抽检发现失配项与初筛数量可能不同（如 `DADAOInstrFormats.td`、`DADAOFixupKinds.h`、`DADAOMCAsmInfo.cpp`、`DADAODisassembler.cpp`、`trans_{arith,compare,extend,shift,block,logic}.c.inc` 等），**须以正式检查脚本的机械输出为准**。
- **输出**：修正后的 patch `index` 行（或经 `make_patch.py` / `series` 重生成），以及新增的**可复用检查器** `tools/infra/check_index_blobs.py`。
- **约束**：
  - 只改 `new file mode`（`index 0000000..<hash>`）补丁的字面 hash；**修改类**补丁（有 old hash）不能用此法判定，**不得**误改。
  - 修正后 `git apply` 行为**逐字节不变**（内容不变，仅 hash 元数据）。
  - 不得改补丁的**内容行**；禁止顺手重排 series。
  - 检查器须接入或提供 `make` 目标（若接入 `make check`，须可失败且不误报）。

## 验收标准

1. **机械重算**：`tools/infra/check_index_blobs.py` 对每个 `new file mode` 补丁按「diff 头 + `@@` 后 `+` 行内容」用 `git hash-object --stdin` 计算，与 `index` 行的新 hash 比对；修复后 **失配数 = 0**（给出逐条 before/after 输出；修复前先记录真实失配清单，替换初筛的 9 项）。
2. **不破坏应用**：修复后 `git apply --check`（在 scratch/worktree 上）对全部补丁 EXIT=0；`make check-patch-tree` EXIT=0（2 components、77 patches OK）。
3. **反例门控**：在临时副本把某 `new file mode` 补丁的 hash 改错 → 检查器 **EXIT≠0**；还原（或重新生成）→ EXIT=0。给出真实输出。
4. **修改类补丁不误判**：检查器对非 `new file mode` 补丁不产生断言（给出说明）。
5. `make check` EXIT=0。

## 硬约束

- 临时目录 `/tmp/opencode/INFRA-038t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
- 复杂命令输出留存 `.work/log/infra/INFRA-038t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/INFRA-038t/`，**可复用检查器落 `tools/infra/check_index_blobs.py` 并随产物入库**。

## 完成区

**测试结果**：全部通过。一键证据脚本 `.work/evidence/INFRA-038t/run.sh` **10/10 PASS（EXIT=0）**；
`make check` **EXIT=0**；`make check-patch-tree` **EXIT=0**（`2 component(s), 77 patches OK`）；
`check_index_blobs.py` 修复后 **EXIT=0**（67 new-file OK / 10 modification skipped）；
注入反例 **EXIT=1**；修改类补丁注入后仍 **EXIT=0**。

**修改文件**：
- 7 份 `new file mode` 补丁的 `index` 新 hash（**仅该行**，内容行/series 未动）：
  - LLVM 4：`DADAOInstrFormats.td`（`7012c4fcb2f5`→`cbc66c39f481`）、`DADAODisassembler.cpp`（`b708270f075d`→`b522e707b657`）、`DADAOFixupKinds.h`（`466ea7d6a412`→`7bcd322cf58a`）、`DADAOMCAsmInfo.cpp`（`dbe4cd5ef41f`→`b6faaee9d1e2`）
  - QEMU 3：`trans_extend.c.inc`（`0a949140a1`→`02162a779c`）、`trans_logic.c.inc`（`d11a3e2860`→`b425533a4f`）、`trans_shift.c.inc`（`4bf3f68981`→`040affe276`）
- 新增可复用检查器 `tools/infra/check_index_blobs.py`（随产物入库；含 `--fix`）。
- `Makefile`：新增 `check-index-blobs` 目标并**接入 `make check`**（+ `.PHONY`、`help` 说明行）。
- 非入库（`.gitignore`）：`.work/evidence/INFRA-038t/{run.sh,check_tree_hashes.py}`、`.work/log/infra/INFRA-038t-*.log`。

**验收结果**（真实输出，日志见 `.work/log/infra/`）：
1. **机械重算（改前）**：`python3 tools/infra/check_index_blobs.py` → `EXIT=1`，**7 条失配**（LLVM 4 + QEMU 3），非初筛的 9 项（初筛 LLVM 7+QEMU 2；机械为准）。日志 `INFRA-038t-check-index-blobs-before.log`。
2. **修正**：`python3 tools/infra/check_index_blobs.py --fix` → `EXIT=0`，`FIXED` 7 条，`67 new-file patch(es) fixed`。日志 `INFRA-038t-check-index-blobs-fix.log`。
3. **机械重算（改后）**：`python3 tools/infra/check_index_blobs.py` → `EXIT=0`，`check-index-blobs: 67 new-file patch(es) OK; 10 modification patch(es) skipped`。
4. **仅改 hash 元数据**：`git diff --stat` = Makefile + 7 补丁；逐 patch 核对 diff **仅 `index` 行**（零串长度保持不变，如 `0000000000..` 仍 10 个 0）；10 份修改类补丁（有 old hash）**未出现在改动列表**。
5. **不破坏应用**：scratch index 全量应用后 `write-tree` == `.work/source` HEAD tree（llvm `150f145a…`、qemu `25135ee1…`）；`make check-patch-tree` EXIT=0；`make check` EXIT=0。
6. **反例门控**：临时副本改错 hash → 检查器 `EXIT=1`；`--fix` 重新生成 → `EXIT=0`；仓库原文件 sha256 不变。
7. **修改类不误判**：把修改类补丁新 hash 注入错值 → 仍 `EXIT=0`（跳过）；构造「hunk 内容里含 `new file mode` 字样」的修改类补丁 → 仍 `EXIT=0`（不误分类）。
8. 另经独立交叉核对：67 份 new-file 补丁的「按补丁重建内容」hash 与 `.work/source` 实际文件 hash **全部一致**（0 失配），日志 `INFRA-038t-crosscheck-recon.log`。

**新发现/坑**：
- **初筛 9 ≠ 机械 7**：初筛「LLVM 7 + QEMU 2」与实际不符；机械输出为 **LLVM 4 + QEMU 3**（qemu 的 `trans_arith/compare/block` 并不失配）。再次印证「以机械重算为准」，人工初筛不可作为判据。
- **`make_patch.py` 无法修复此类失配**：其 §6.2 幂等比较先 `_normalize_index`（剥掉 `index` 行）再比对，故「仅 index 行失配」会被判为「未变化」而跳过写入。这正是该 pre-existing 问题长期残留的根因；只能由专用工具修 hash（本任务 `--fix`）。
- **`git apply` 对 index 新 hash 不敏感**：故 `make check-patch-tree`（断言⑥/⑨）在本问题下仍全绿——需要一个**独立**检查器（本任务新增）才能捕获。
- **pre-existing `make help` 故障**（非本任务引入）：`Makefile:83` 帮助行含未转义 ` ```simrisc `，sh 报 `Syntax error: EOF in backquote substitution`，`make help` EXIT=2（HEAD 版本同样失败，已在 `/tmp` 用 `git show HEAD:Makefile` 复现）。本任务仅在其后追加 help 行，未修该行。
- **新检查器分类判定须按「行首」匹配**：用子串 `"new file mode"` 会因 hunk 内容里出现该字样而误分类；已改为 `^new file mode \d+$`/`^GIT binary patch$`（MULTILINE）。

**遗留问题**：
- ① `make help` 的 pre-existing 语法错误未修（超出本任务范围，见「新发现/坑」）；本任务新增的两行 help 需待该行修复后才能显示。**建议**由 infra 后续小任务修 `Makefile:83`（把 ` ```simrisc ` 改为单引号/转义），无需本任务处理。
- ② `components/{llvm-project,qemu}/changelog.md` 未追加本任务条目：本任务「只改补丁 index 字面 hash」，未列 changelog 为改动对象；且纯元数据修正不改变补丁语义。若按 `spec/Process-01 §10`「每次改动一条」口径需补，建议由主会话/架构师裁定（**未擅自越界写**）。
- ③ 本任务完成后可关闭 `ISS-119`（已由 reviewer 复核为准，主会话负责在 `.tao/knowledge/issues.yaml` 置 `resolved_by: INFRA-038t`）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审方式**：全局 `subagent_depth=1`，engineer 无法起嵌套子代理，采用自主逐行审查（检查器 + Makefile 改动 + 证据脚本）。

**审查范围与结论**：逻辑正确性（未测输入/边界）、设计/惯用法、防造假（确认命令真实执行过、贴真实输出）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `is_new_file`/二进制检测用子串匹配，hunk 内容含同名字样会被误分类 | ✅已修 | 改为行首正则 `^new file mode \d+$` / `^GIT binary patch$`（MULTILINE） | 构造 hunk 内容含 `new file mode 100644` 的修改类补丁 → `check_index_blobs.py` EXIT=0（0 new-file / 1 skipped） |
| F2 显式路径不存在时抛 `FileNotFoundError` 裸 traceback | ✅已修 | `collect_patches` 增 `path not found` 明确报错 | `check_index_blobs.py /tmp/.../nope.patch` → `path not found`，EXIT=1 |
| F3 `--fix` 须保留零串长度与 mode 字段、不得动内容行 | ✅已修/验证 | `NEW_INDEX_RE` 仅替换新 hash、保留 `(0+)` 与 `(.*)` | `git diff` 显示零串长度不变（`0000000000..` 仍 10 个 0）；tree hash 相等 |
| F4 修改类补丁不得误判/误改 | ✅已修/验证 | 仅对 `new file mode` 断言，其余 skip | 10 份修改类补丁未出现在 `git status`；注入其新 hash 后仍 EXIT=0 |
| F5 内容重建须与真实文件一致（否则会「修错」） | ✅已修/验证 | 重建 `+` 行 + 处理 `\ No newline`；用 `git hash-object --stdin` | 67 份 new-file 补丁重建 hash vs `.work/source` 实际 hash **0 失配** |
| F6 修复不应改变 `git apply` 行为 | ✅已修/验证 | 仅改 index 字面 hash | 全量应用到 base 后 `write-tree` == `.work/source` HEAD tree（两组件相等） |
| F7 pre-existing `make help` 语法错误（`Makefile:83`） | ❌不修（越界） | 未动该行；仅在报 `遗留问题` 并给出建议 | `git show HEAD:Makefile` 版本 `make help` 同样 EXIT=2（已复现） |

**自审判决**：无未修 finding（F7 属任务外 pre-existing，已披露并给建议）。任务状态可置「待验收」。

#### 第 1 轮 reviewer 验收

**审查方式**：独立重跑证据脚本 + 独立注入反例 + 独立重算 hash + 独立验证 gate。

---

**1. 证据脚本审查（`.work/evidence/INFRA-038t/run.sh`）**

逐条核对：
- `run_check` 函数：正确捕获 `"$@" > log 2>&1` 后的 `$?`（非管道退出码）；`ok`/`fail` 两分支逻辑不恒真（rc=0 vs rc≠0 判定清晰）；`FAILED` 仅在期望不符时置 1。✅
- 注入操作（`corrupt_new_hash`）仅作用于 `$TMP` 临时副本，不碰仓库文件。✅
- 还原逻辑：通过 `--fix` 重写临时副本 → 再 `check` 确认回绿。✅
- 原文件不变验证：sha256 before/after 比对。✅
- 退出码汇总：`FAILED=0` → `exit 0`；`FAILED=1` → `exit 1`。结尾无 `tee` 吞退出码。✅
- 反例注入自检覆盖：new-file 注入→FAIL、--fix→回绿、修改类注入→仍 OK、内容提及→不误分类。✅

**结论**：脚本合格，不需修改。

---

**2. 重跑证据脚本**

```
$ bash .work/evidence/INFRA-038t/run.sh
== INFRA-038t evidence ==
repo: /mnt/tao/DADAO-v5
PASS  check_index_blobs(repo)                        expected=exit0 actual=exit0
PASS  make check-patch-tree                          expected=exit0 actual=exit0
PASS  apply_tree_hash_equals_source                  expected=exit0 actual=exit0
PASS  inject_new_file_hash(temp copy)                expected=nonzero actual=exit1
PASS  regenerate_temp(--fix)                         expected=exit0 actual=exit0
PASS  recheck_temp_after_fix                         expected=exit0 actual=exit0
PASS  original_new_patch_unchanged                   expected=unchanged actual=unchanged sha=6b9938d8c5a4
PASS  modification_patch_not_misjudged               expected=exit0 actual=exit0
PASS  content_mention_not_misclassified              expected=exit0 actual=exit0
PASS  make check                                     expected=exit0 actual=exit0
== summary ==
INFRA-038t evidence: ALL CHECKS PASSED
EXIT=0
```

**10/10 PASS，EXIT=0**。

---

**3. 独立验证：check_index_blobs.py**

```
$ python3 tools/infra/check_index_blobs.py --verbose
(checker-verbose.log: 67 lines OK for every new-file patch)
check-index-blobs: 67 new-file patch(es) OK; 10 modification patch(es) skipped
EXIT=0
```

**67 new-file OK / 10 modification skipped / EXIT=0**。

---

**4. 独立重算 7 条修复的 hash**

用独立 Python 脚本对 7 份补丁重建 `+` 行内容 → `git hash-object --stdin` → 比对 index 行：

| 组件 | 补丁 | index hash prefix | 全量 hash | 结果 |
|------|------|--------------------|-----------|------|
| LLVM | DADAOInstrFormats.td | cbc66c39f481 | cbc66c39f4818cb9e268a2cafba30b802142fb2f | ✅ |
| LLVM | DADAODisassembler.cpp | b522e707b657 | b522e707b6577422df6888e4a33833ce2fd08373 | ✅ |
| LLVM | DADAOFixupKinds.h | 7bcd322cf58a | 7bcd322cf58af42049496a3271e9cb97e74ecd8e | ✅ |
| LLVM | DADAOMCAsmInfo.cpp | b6faaee9d1e2 | b6faaee9d1e2f5119d29ee04b9fcc3a56bba8fc2 | ✅ |
| QEMU | trans_extend.c.inc | 02162a779c | 02162a779cd541dcb8466dc12016ae2dc76054cb | ✅ |
| QEMU | trans_logic.c.inc | b425533a4f | b425533a4f4034555b160a7760b6717a725883ea | ✅ |
| QEMU | trans_shift.c.inc | 040affe276 | 040affe276486ad52a89614f2c44ac0609468b1e | ✅ |

**7/7 全部匹配**，与 `check_index_blobs.py --verbose` 输出完全一致。

---

**5. 独立注入反例（与证据脚本不同补丁）**

注入点：`DADAOInstrFormats.td.patch`（LLVM，证据脚本用的是 `trans_extend.c.inc.patch`）

```
$ cp components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrFormats.td.patch /tmp/opencode/INFRA-038t-review/inject-test.patch
$ # 注入: cbc66c39f481 → cbc66c39f480
$ python3 tools/infra/check_index_blobs.py /tmp/opencode/INFRA-038t-review/inject-test.patch
check-index-blobs: .../inject-test.patch: index new-hash cbc66c39f480 does not match content blob cbc66c39f481 (full cbc66c39f4818cb9e268a2cafba30b802142fb2f)
check-index-blobs: 1 mismatch(es) (1 new-file patch(es), 0 modification patch(es) skipped)
EXIT=1
```

还原（`--fix`）：
```
$ python3 tools/infra/check_index_blobs.py --fix /tmp/opencode/INFRA-038t-review/inject-test.patch
FIX_EXIT=0
$ python3 tools/infra/check_index_blobs.py /tmp/opencode/INFRA-038t-review/inject-test.patch
RECHECK_EXIT=0
```

仓库原文件未受影响（`git diff` 仅显示预期的 index 行改动，非注入残留）。

---

**6. 改动范围核验**

`git diff --name-only`：
```
.tao/tasks/infra/INFRA-038t-补丁index-blob卫生.md
Makefile
components/llvm-project/patches/.../DADAOInstrFormats.td.patch
components/llvm-project/patches/.../DADAODisassembler.cpp.patch
components/llvm-project/patches/.../DADAOFixupKinds.h.patch
components/llvm-project/patches/.../DADAOMCAsmInfo.cpp.patch
components/qemu/patches/.../trans_extend.c.inc.patch
components/qemu/patches/.../trans_logic.c.inc.patch
components/qemu/patches/.../trans_shift.c.inc.patch
```

- 7 份补丁：`git diff -U0` 确认**每份仅改 `index` 行**（LLVM 零串 12 个 0、QEMU 零串 10 个 0 均保持不变）
- 10 份修改类补丁**未出现在改动列表** ✅
- Makefile：新增 `check-index-blobs` 目标 + 接入 `make check` + `.PHONY` + help 行 ✅
- 新检查器 `tools/infra/check_index_blobs.py` ✅
- `components/{llvm-project,qemu}/changelog.md` 未追加（engineer 披露）——纯元数据修正不改变补丁语义，可接受 ✅

---

**7. Gate 验证**

```
$ make check-patch-tree
check-patch-tree: 2 component(s), 77 patches OK
EXIT=0

$ make check
Total Discovered Tests: 33
  Passed: 33 (100.00%)
repository checks: PASS
EXIT=0
```

---

**8. 初筛 9 vs 机械 7 的差异判定**

独立核验：67 份 new-file 补丁逐份用 `git hash-object` 计算，仅 7 条失配。工程师的清单（LLVM 4 + QEMU 3，即 `DADAOInstrFormats.td`、`DADAODisassembler.cpp`、`DADAOFixupKinds.h`、`DADAOMCAsmInfo.cpp` + `trans_extend/logic/shift.c.inc`）与 reviewer 独立重算**完全一致**。初筛的 `trans_arith/compare/block` 实际不失配。**以机械重算为准** ✅

---

**9. changelog 判定**

工程师未追加 `components/{llvm-project,qemu}/changelog.md`。本任务仅修正补丁元数据（index hash），不改变补丁内容/语义/应用行为。按「只改补丁 index 字面 hash」的范围，不追加 changelog 合理。**不阻塞验收**，建议主会话在关闭 ISS-119 时酌情决定是否补一条。

---

**判决：Accepted**

验收命令块在 reviewer 独立重跑下全部通过；约束无违反；独立注入反例验证脚本能失败且可还原；7 条修复的 hash 独立重算与工程师报告一致；改动范围严格限于 index 行 + Makefile + 新检查器。
