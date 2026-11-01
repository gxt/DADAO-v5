# TESTCASES-070t: rev 向量陈旧与 diff_ir_lli manifest（ISS-335 + ISS-336）

**模块**：testcases
**项目里程碑**：M10
**依赖**：无
**状态**：已验证

## 背景
- **ISS-335**：`generate_rev_vectors.py --check` 红，62/62 例 `spec_cite` 陈旧（入库 `tests/vectors/rev/rev.yaml` 未随 spec 同步；`rev` 不在门控）⇒ 生成器确定性没问题，是数据漂移。
- **ISS-336**：`make test-m6` 的 `diff_ir_lli` 报 `unclassified=2`：`cmp-u-branch.ll`、`code-model-large.ll`（LLVM-131t/133t 后 manifest 未更新），既有缺口。

## 目标
1. **ISS-335**：
   - 运行 `python3 tools/testcases/generate_rev_vectors.py` 重生成 `tests/vectors/rev/rev.yaml`（按脚本默认落点；若需 `--out` 再显式指定）；
   - `--check` rc=0；把 `--check` 接进门控（新增 `make check-rev-vectors`，纳入 L1 `_locked-check`；或并入既有 `check-case-ledger` 同层，二选一，保持单一层）。
2. **ISS-336**：
   - 在 `tests/llvm/ir-lli/manifest.yaml` 的 `include`/`exclude` 给 `cmp-u-branch.ll`、`code-model-large.ll` 归类（按既有语义：能编/能比对 ⇒ include；有意排除 ⇒ exclude + 理由），不得用 `unclassified` 放行；
   - `python3 tools/integ/diff_ir_lli.py`（或 `make test-m6` 的 `[2/3]`）rc=0。
3. `issues.yaml`：ISS-335、ISS-336 `closed`，`resolved_by: TESTCASES-070t`。

## 验证
- `make check` rc=0；新门控 `check-rev-vectors` rc=0。
- `make test-m6` rc=0（含 `diff_ir_lli` 无 unclassified、Embench 38/38；若耗时 >10 min，夜间跑并落 `XXX_EXIT`）。
- `check-case-ledger` rc=0（若 rev.yaml 变更影响 ledger，用 `--write` 重生成）。

## 约束
- 只改 `tests/vectors/rev/rev.yaml`、`tests/llvm/ir-lli/manifest.yaml`、`Makefile`（新门控）、`issues.yaml`、任务书/`milestones.md`；不改 spec/qemu/其它向量。
- 临时目录 `/tmp/opencode/TESTCASES-070t/`；不提交。

## 完成区

**状态**：已验证

### 测试结果
- `make check`（L1）：rc=0（`repository checks (L1): PASS`，含新门控 `check-rev-vectors`）
- `make check-rev-vectors` rc=0；`generate_rev_vectors.py --check` rc=0（62 例：semantic/boundary 重算 39、legality 19、合法 (id,k) 覆盖 18/18）
- `check-case-ledger` rc=0（1958 条；ledger 键不含 `spec_cite` ⇒ 无需 `--write`）
- `make test-m6` rc=0（lit 12/12、`diff_ir_lli` unclassified=0 matched 19/19、Embench 38/38）
- 证据脚本 `./.work/evidence/TESTCASES-070t/run.sh` rc=0（9 项检查，含 2 条注入反例）

### 修改文件
- `tests/vectors/rev/rev.yaml`（重生成 62 例 `spec_cite`，其余字节不变）
- `tests/llvm/ir-lli/manifest.yaml`（2 例 → `exclude` / `class: no-value-entry`）
- `Makefile`（新增 `check-rev-vectors`；`.PHONY`/`_locked-check`/help 同步）
- `.tao/knowledge/issues.yaml`（ISS-335/336 `closed` + `resolved_by` + 关闭说明）
- `.tao/knowledge/milestones.md`（行状态）、本任务书、`.work/evidence/TESTCASES-070t/run.sh`

### 验收结果
- rev：`generate_rev_vectors --check: PASS（逐字节一致 + 全量 oracle 重算 + 合法集复核）`
- diff：`structural: on-disk=93 include=19 exclude=74 unclassified=0 overlap=0 missing=0`；`matched: 19/19`
- test-m6：`test-m6: PASS (lit full + lli value-level diff + Embench E2E)`

### 新发现/坑
- rev.yaml 漂移**只在 `spec_cite`**（62 行）：`contracts/opcodes.yaml` 已细化为 `SimRISC-0x: rev.x`，入库物仍是分册级旧串；期望值/编码全未变。
- `check_case_ledger` 的键 = (file,id,class,word,fault,status,index)，不含 `spec_cite` ⇒ 重生成不触发 ledger 变化。
- 两个 `.ll` 均为 `llc|FileCheck` 结构测试（无 `@main`/value channel）⇒ `no-value-entry`，与既有 (e)–(j) 同语义；未用 unclassified 放行。

### 遗留
- 无

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查改动：Makefile 新目标只读（`--check`）、未进 `GATE_LOCKED_TARGETS`（无需写共享状态）；manifest 两条 `class` 在 `CLASS_VOCAB` 内且 `ir` 路径存在；issues 字段满足 `check_issues`（closed ⇒ resolved_by 非空）；rev.yaml 为生成物、最终态与生成器输出逐字节一致（非手改）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 证据脚本 L1 接线断言原用 `(^\| )`，ERE 中行内 `^` 语义不明确 | ✅已修 | 改 `[[:space:]]` 边界，并加「L2/L3 不含该目标」反断言 | 证据第 2 项 PASS：`L1=1 / L2\|L3=0` |
| 注入 A 可能「空注入」假绿（sed 未命中 ⇒ 文件未变） | ✅已修 | 增加 `git diff --name-only` 非空断言 | 证据 A：`diff=yes / inject rc=1 / md5=equal / restore rc=0` |
| 注入 B 若就地改 manifest 会污染工作树 | ✅已修 | 改为生成临时 manifest 传给 `--manifest`（临时树注入，不碰真文件） | 证据 B：`rc=1 / unclassified=2`，真 manifest 未变 |

判决：3 条 finding 全部已修，无未修项 ⇒ 状态标 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（rc 均取被检命令自身）**：`make check`=0（`repository checks (L1): PASS`）；`make check-rev-vectors`=0
（`cases=62，semantic/boundary=39，legality=19，覆盖 18/18`）；`check-case-ledger`=0（1958 条 PASS）；
`diff_ir_lli`=0（`unclassified=0 matched: 19/19`）；`bash .work/evidence/TESTCASES-070t/run.sh`=0（9/9 PASS）；
`make test-m6`=0（lit 12/12、diff 19/19、Embench 38/38，日志 `.work/log` 外存 `/tmp/opencode/TESTCASES-070t/`）。
**语义核验**：`git show b3f24298 -- rev.yaml` 124 行改动全为 `spec_cite`（62-/62+，键集相同，期望值/编码未变）；
`check-rev-vectors` 仅出现在 `_locked-check`(L1)（Makefile 行 68/194/837/1348，L2 `_locked-check-modules`/L3 `_locked-check-full` 均无）；
manifest 两 `.ll` 均 `exclude`+`no-value-entry`（include=19/exclude=74/unclassified=0/overlap=0/missing=0）；
ISS-335/336 `closed` + `resolved_by: TESTCASES-070t` + 关闭说明。
**独立反例（不复用 engineer）**：① python 精确替换首条 `spec_cite` 为 `rev.REVIEWER-STALE` ⇒
`make check-rev-vectors` FAIL（`Error 1`/rc=2），`cp` 还原后 md5 `b18a7579…` 相等、rc=0；
② yaml 生成临时 manifest 仅去掉 `cmp-u-branch.ll` 一条 exclude ⇒ `unclassified=1` + `FAIL (structural)` rc=1，
真 manifest md5 `75c3bb70…` 全程未变，真 manifest 复跑 PASS。全程禁 git checkout/restore/stash。
**残留/越界**：验收前后 `git status --porcelain -uall` 空（干净）；commit 改动文件 = 完成区声明 6 项，无越界。
**finding（不阻断）**：ISS-335 notes 中 `tools/tests/generate_rev_vectors.py` 路径笔误（实际 `tools/testcases/`），
系 TESTCASES-067t 登记时既有文本、本提交未改 ⇒ 文档级小错，请 architect 收尾时顺手改。
**判决：Accepted**（验收命令全绿 + 独立反例注入→FAIL→还原→回绿 + 约束无违反）。
