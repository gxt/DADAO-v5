# TESTCASES-070t: rev 向量陈旧与 diff_ir_lli manifest（ISS-335 + ISS-336）

**模块**：testcases
**项目里程碑**：M10
**依赖**：无
**状态**：待开始

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

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
