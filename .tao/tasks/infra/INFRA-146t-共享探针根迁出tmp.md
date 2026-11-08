# INFRA-146t: 共享探针根迁出 `/tmp`（修复临时目录门控自触发）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-145t`（已合入）
**状态**：待开始

## 背景（`INFRA-145t` reviewer 的 F1）

`check-temp-dirs` 按「非活动 worktree 且 mtime > 2h」判红。但 L2 `check-arch` / `check-arch-smoke` 的探针根长期驻留在 `/tmp/opencode/` 下：

- `TESTCASES-093t`（42.1 MiB）、`TESTCASES-094t`（30.8 MiB）

它们**只在跑 L2 时才被刷新**，而 L1（`make check`）不跑 `check-arch` ⇒ 距上次 L2 超过 2 小时后，**L1 会自触发红**。实测 `--max-age-hours 0` 命中这三类。

## 目标

1. **迁移共享探针根到 `.work/`**（持久、gitignore、非临时）：把 `check-arch`/`check-arch-smoke` 的探针产物目录改到 `$(TEST_ARTIFACTS_DIR)/arch/...` 之下；`/tmp/opencode/` 只保留**每任务 scratch**。
2. **R2 豁免口径收紧**：
   - 任务号目录：若对应任务书状态 ∈ {`待开始`,`待验收`,`待返工`} ⇒ 视为在用，不判红；
   - 任务书 `已验证` 或任务号不存在 ⇒ 按 mtime 判红（保留现有行为）；
   - 非任务号目录：mtime > 2h 判红。
3. **F2：陈旧大文件报告**：扫描 `--max-age-hours` 以上的**文件**中 > 100 MiB 者，一并列出（默认只报告、计入 FAIL 前先给清单；阈值可参数化）。
4. **F3**：把 `INFRA-145t` 完成区「116」口径与清单 119 行（116 带时龄 + 3 裸名）统一说明。

## 验收

1. 迁移后跑 `make check-arch-smoke` 与 `make check-arch`，产物落在 `.work/` 下；`/tmp/opencode/` 不再出现 `TESTCASES-09x`。
2. `make check-temp-dirs` 在「L2 跑过 >2h 后」仍 **rc=0**（模拟：把 L2 探针根时间前移不可行时，改为参数 `--max-age-hours 0` 只命中真正陈旧项，且共享根不再出现）。
3. 三向注入逐条真实 rc：① 已 `已验证` 任务残留目录 ⇒ FAIL；② 在跑任务目录 >2h ⇒ **PASS**（新增豁免）；③ 非任务号目录 >2h ⇒ FAIL；均还原回绿。
4. 陈旧大文件报告可达 FAIL（造 150 MiB 文件 + 3h 前 mtime）。
5. `make check`（L1）rc=0；改动后 L2 一次 rc=0。
6. 完成区 ≤30 行、无运行期路径。

## 说明

- 迁移属**测试产物落点**变更（`TESTCASES-093t/094t` 相关脚本），不改变判据与用例。
- `/tmp` 规则本身不变：每任务 scratch 仍在 `/tmp/opencode/<任务ID>/`，收尾即删。
