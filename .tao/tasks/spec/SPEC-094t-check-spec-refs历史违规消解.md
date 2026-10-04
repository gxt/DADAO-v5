# SPEC-094t: `check-spec-refs` 历史违规消解

**模块**：spec
**项目里程碑**：M2
**依赖**：`SPEC-091t`（`contract-asm.md` 会引入新引用，须一并确保零新增）
**状态**：待开始

## 目标

消解 `tools/infra/check_spec_refs.py`（standalone，**不在 `make check`**）当前的 **76 条历史违规**（`ISS-086`：18 Check1 + 58 Check2），使 M2 门槛③「引用全对齐」名副其实。本任务为该违规的**归属任务**——`SPEC-090k` 核验时由用户裁定**纳入 M2**（2026-10-04）。

## 背景与现状（实测）

- `check_spec_refs.py` 校验 `contract-*.md` 的 § 引用与来源头：
  - **Check1**：`[spec §x]` 引用是否可定位；
  - **Check2**：来源头 / 版本 / 生成投影排除名单。
- 当前实测 **76 violations（18 Check1 + 58 Check2）**，与 HEAD 基线**逐项相同**（`ISS-086`，由 `SPEC-087t` 登记）——**非某一任务引入**，是历史遗留。
- 该项**不在 `make check`**，故不阻断门控；但门槛③要求引用对齐，故纳入。

## 交付物

1. **独立复现**：`python3 tools/infra/check_spec_refs.py`，记录**完整输出**（条数 + 分类），作为改前基线。
2. **逐条分类与处置**（76 条 → 归宿，可追溯）：
   - **可机械修正**（§ 名/路径陈旧等）→ 直接改对应 `contract-*.md`；
   - **排除名单应含**（生成投影等）→ 补入 `check_spec_refs.py` 的 `_EXCLUDED_CONTRACTS`，**并与 `check_spec_drift.py` 的 `EXCLUDED_CONTRACTS` 同步**（两者失同步会致误报，见 `lessons.md §5.1`）；
   - **须 deferred**（如引用上游不存在章节）→ 在 `.tao/knowledge/issues.yaml` / 完成区**显式登记理由与归属**。
3. **结果**：`check_spec_refs.py` 的 **Check1/Check2 违规 = 0**，或全部显式登记为 deferred 且各有理由。
4. **（可选，推荐）门控化**：若消解后稳定，评估把 `check_spec_refs.py` 接入 `make check`（带反例门控）；**不接入**亦须在完成区说明理由。

## 约束

- 改 `contract-*.md` 时**不改其规范语义**（只修引用 / 来源头 / 排除名单）；**不改** `spec/` 上游正文、`contracts/`、`tests/`、`components/`、`.tao/archive/**`。
- `check_spec_drift.py` 与 `check_spec_refs.py` 的排除名单**必须同步**。
- 与 `SPEC-091t` **串行**（同改 `spec/README.md`/`Process-02` 的合约清单；若 `SPEC-091t` 先落地，本任务须含其新引用，确保零新增）。
- 临时目录 `/tmp/opencode/SPEC-094t/`；**不提交 git**；失败即停、禁自动重试。
- 完成区与真实输出逐条对齐；复杂命令输出留存 `.work/log/spec/SPEC-094t-*.log`。

## 验收标准

1. `python3 tools/infra/check_spec_refs.py` → **Check1/Check2 违规 = 0**（或全部 deferred 登记）；给**真实输出 + 退出码**。
2. **逐条分类表**（76 条 → 修正 / 排除 / deferred），供 reviewer 抽查。
3. `make check` **EXIT=0**。
4. **一键证据脚本**（`.work/evidence/SPEC-094t/`）：非交互；任一检查失败即非零退出；逐项打印「检查名 + 期望/实际 + 退出码」；内置反例自检（注入 1 条**未登记**违规 → 预期 FAIL → 还原 → 回绿）；结尾不得用 `tee` 吞退出码。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
（reviewer 独立验证：重跑 + 逐条分类核 + 反例注入与还原）
