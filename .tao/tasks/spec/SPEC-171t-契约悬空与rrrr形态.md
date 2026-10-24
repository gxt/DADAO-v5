# SPEC-171t: 契约悬空引用 13 条 + `rrrr` 单目的三源形态入格式表（`ISS-219`/`ISS-331`）

**模块**：spec
**项目里程碑**：M9（收尾前，用户 2026-10-24 裁定「M9 内做」）
**依赖**：`SPEC-167t`（册名/结构已稳定）
**状态**：待开始

## 立项来源

- `ISS-219`：契约正文存在 **13 条小节级悬空引用**（`INFRA-080t` 门控诊断发现）
- `ISS-331`：`Toolchain-01 §6` 格式表缺「`rrrr` 单目的 + 三源」形态；`check_asm_prose` 的 R6 假设 `rrrr` 必带 `{}` ⇒ 该形态无字面量门控（`ftfma`/`fofma` 受此影响）

## 目标

1. 逐条修正 13 条悬空引用（改指现存小节或删除）；每条给出"原指向 → 新指向 / 删除理由"。
2. `Toolchain-01 §6` 格式表补「`rrrr`：1 目的 + 3 源」（与双目的 `{rdHA, rdHB}` 区分写法）。
3. `check_asm_prose` 的 R6 改为**按实际形态判定**（单目的 rrrr 不要求 `{}`），并补 1 条正例（`ftfma rf8, rf9, rf10, rf11`）+ 1 条反例（把单目的写成 `{}` ⇒ 红）。

## 验收

1. `check_spec_refs` / `check_spec_cite_targets` / `check-contracts-dir` rc=0；13 条悬空 **0**。
2. `check-asm-prose --strict` rc=0；`ftfma` 单目的形态有门控覆盖（注入错写法 ⇒ 红）。
3. **可达 FAIL ≥2**：① 塞回一条悬空引用 ⇒ 契约门控红；② 把 `ftfma` 写成双目的 `{}` ⇒ prose 红。
4. 证据 `.work/evidence/<任务ID>/run.sh`。
5. 受影响门控 + `make check`(L1) rc=0。

## 约束

- 不改指令语义/编码；不 commit/push；开工 `git switch -c SPEC-171t`；临时目录 `/tmp/opencode/SPEC-171t/`。
