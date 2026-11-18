# m15-infra-007: 两处既有死引用收口

**模块**：infra
**项目里程碑**：M15
**依赖**：`m15-infra-004`（`check_dead_refs.py` 已入仓）
**可并行分片**：否
**预估**：0.5–1 h
**档位**：小改
**状态**：待开始

## 背景（`m15-infra-004` 首次运行 `check_dead_refs.py` 抓到的现存死引用）

`tools/infra/check_dead_refs.py` 首次运行即报出两处**真实的仓内死引用**（当时记为「建议各自收口」，未修）：

1. `tools/infra/check_milestones_fresh.py:85` 的 `--file` 默认值仍指向已分册化的 `milestones.md`（现为 `milestones-m14/15/16.md`；根 `milestones.md` 是否仍存在以现场为准）。
2. `tools/qemu/check_005t_coverage.py` 仍读**已退役的 YAML 载体**（无调用者；`check_005t_coverage` 是否还在 Makefile 里以现场为准）。

## 目标

1. 两处逐一核实（现场 `grep` + 跑一次脚本），确认是「默认值过时」还是「脚本整体已退役」。
2. 按性质处置：
   - **仍在使用** ⇒ 修默认值/载体路径，使其指向现存文件；修后脚本自身 rc=0。
   - **已无调用者且载体退役** ⇒ 删除脚本（或移入 `.tao/archive/tools/`，按 `AGENTS.md`「脚本入仓判据」判断，选一种并在完成区写明理由）；同步删 Makefile 目标（若有）。
3. 不新增功能、不改判据语义。

## 验收（逐条贴真实 rc）

1. `python3 tools/infra/check_dead_refs.py` **rc=0** 且 `missing` 计数为 0（当前基线 0，修完仍 0；若你新增了路径，必须同样为 0）。
2. 两处逐一给出：现场证据（`grep` 输出 / Makefile 命中）、处置、修后验证。
3. 若删除脚本：`grep -rn "<脚本名>" Makefile tools docs` = 0（历史任务书/归档除外，逐条列明）；`make check` 相关目标不因删除而失败。
4. `check-dirs`、`check-no-residue`、`make check-tasks` rc=0。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；不改版本号。
2. 只动上述两处脚本 + 必要的 Makefile 行 + 本任务书。
3. **不碰 `components/`、`tests/`、`spec/`、`contracts/`**。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（无）

## 审阅记录

（待填）
