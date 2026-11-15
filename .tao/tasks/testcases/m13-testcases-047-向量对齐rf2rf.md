# m13-testcases-047: `.S` 向量对齐 `rf2rf`（删 2 加 1）+ 补「`.S` id 必须在 opcodes 里」门控

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-010`（spec 侧已合 `cb8ca30d`：删 `ft2ft`/`fo2fo`、加 `rf2rf`；id 264→263）
**可并行分片**：否
**预估**：1.5–2 h
**档位**：中改（看 diff + ≥2 路注入 + 相关门控）
**状态**：待开始

## 背景

`m13-spec-010` 只改了 spec 侧。现场仍有一处**仓库自相矛盾**：`contracts/opcodes.yaml` 已无 `ft2ft`/`fo2fo`，但 `tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S` 仍在且被 `tests/inst.yaml` 索引（2 条），**没有任何门控能发现**。本任务把该组件面与 spec 对齐。

## 任务

1. 删 `tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S`；新增 `rf2rf_orri_rf.S`（或与既有块复制族同形）；
2. `tests/inst.yaml` 删 2 条加 1 条；`tests/case-ledger.tsv` 重生成；`tests/inst/{MIGRATION.md,README.md,inventory.md}` 同步（263 id → 现场值）；
3. **补门控**：让 `validate-vectors` 或 `check-tests-index` 校验「每个 `.S` 载体 stem 必须能在 `contracts/opcodes.yaml` 找到 id」（现在缺失 ⇒ 这次才漏过去）；新断言必须**可红**（注入一个不存在 id 的 `.S` 应报错）。

## 验收（逐条贴真实 rc）

1. 旧指令在**本组件面**归零：`grep -rn "ft2ft\|fo2fo"` 在 `tests/inst/` = 0（历史归档/ADB/任务书豁免）；
2. 新指令 `rf2rf` 在本组件面落地：载体存在、索引 1 条、`check-inst-asm` 现场计数与 `case-ledger` 一致；
3. 门控：`check-inst-asm`、`check-tests-index`、`validate-vectors`、`check-case-ledger`、`check-no-residue`、`check-knowledge-refs` 全 rc=0；
4. **≥2 路可达 FAIL 注入**（`cp`+md5 还原）：① 新增一个 stem 不在 opcodes 的 `.S` ⇒ 新门控应红；② 把 `rf2rf` 载体点号改断号 ⇒ `check-inst-asm` 应红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束

- 只改 `tests/inst/**`、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tools/testcases/{validate_vectors.py,check_tests_index.py}`（仅新门控）、`tests/inst/{MIGRATION.md,README.md}`、本任务书；
- 不改 `spec/`、`contracts/`（已由 `m13-spec-010` 定稿；如需改，停下写「待裁定」）；
- 禁 `install-host`/`check-modules`/`build-*`（组件重建除外，按需并在完成区申报耗时）；不 sync/reset 节点；
- 不提交 git；注入还原用 `cp`+md5。
