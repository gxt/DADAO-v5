# INFRA-121t: 运行期日志命名清理（check-run-artifacts 7 条既有红）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-120t`（已验证；任务书运行期路径清零）
**状态**：已验证

## 执行环境
本地；只清理运行期日志，不改仓库跟踪文件、不改门控逻辑。

## 背景

`make check-run-artifacts` 当前报 7 条既有非法命名日志：

- 3 条无任务号/无 `check-` 前缀的通用日志
- 4 条 `GEM5-018t` 旧构建日志使用 `.EXIT`/`.start` 后缀

这些是运行期临时日志，不是源码、不是测试资产；规则只接受 `check-<name>.log` 或 `<TASK-ID>-<purpose>.(log|json|txt)`。

`INFRA-120t` 已把 L1 的 `check-knowledge-refs` 清零；本任务是 L1 最后一个非任务红。

## 任务

1. 以 `make check-run-artifacts` 现场输出为准，确认恰为 7 条。
2. 删除或重命名为合法名称；优先删除旧临时日志，不保留非法命名。
3. 不把文件加入 baseline 豁免，不改 `check-run-artifacts` 规则。
4. 若任务书/知识库引用这些日志，改为“运行期证据已清理，未归档；结果见完成区”的历史说明，不保留具体路径。
5. 重跑 `make check-run-artifacts`、`make check-no-residue`、`make check-milestones-fresh`；确认 L1 不再因该门控失败。

## 验收

- `make check-run-artifacts` rc=0、无 7 条问题；
- 文件被删除或改为合法名，现场 `find`/门控证明无残留；
- 不新增代码/配置/门控改动；
- 完成区 ≤30 行，真实 rc；状态 `待验收`。

## 说明

- 不改 `tools/infra/check_run_artifacts.py`；
- 不改 `.run-artifacts-baseline` 掩盖；
- 不删除有效测试产物；只处理门控列出的 7 条。

## 完成区

**测试结果**：清理门控列出的 7 条既有非法命名运行期日志后，`make check-run-artifacts` **rc=0**（A3 2810 new files，0 illegal）。
**修改文件**：仅运行期日志目录（不入库）；任务书、milestones。
**验收结果**：`check-run-artifacts` rc=0；保留的日志命名合法；未改门控、未加入 baseline 豁免、未改代码。
**新发现/坑**：旧任务书正文仍提到这些日志名作为历史说明；不是路径引用，保留。
**遗留问题**：无。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-05）

**重跑记录**（本人在主工作树执行，真实 rc）：
- `make check-run-artifacts` → **rc=0**；`[PASS] A3 2810 new file(s) checked, 0 illegal, 5939 exempt`；`check-run-artifacts: PASS`（与完成区 2810/0 一致）
- `make check-knowledge-refs` → **rc=0**（悬空 `.work` 引用 0；小节级 ADR 533 + contract 79）
- `make check-milestones-fresh` → **rc=0**（流水 45 行，状态一致/覆盖/倒序全过）
- `make check-no-residue` → **rc=0**
- `git status --porcelain -uall` → 空、rc=0；`git diff HEAD` → 空

**7 条旧日志核对**（清单取自历史门控输出 `.work/log/infra/INFRA-120t-L1-after.log`：`2815 checked, 7 illegal`）：
- 通用 3 条 `mergetree.out`、`krefs-final.log`、`qemu/disk-free-r2.log` —— 逐个 `[ -e ]` 检查均 gone
- GEM5-018t 4 条 `GEM5-018t-build{,2}.{EXIT,start}` —— 均 gone；`find .work/log -name 'GEM5-018t*'` 仅剩合法的 `GEM5-018t-build.log`/`build2.log`
- **计数闭环**：`2815 − 7 + 2（22:34 后新建 GEM5-019t-build.log / -exit.txt，birth time 证实）= 2810` ⇒ 恰好只删 7 条、无多删
- 独立复刻 A3 逻辑（不跑门控脚本）：`checked=2810 illegal=0 exempt_baseline=5939`，与门控逐字一致；1218 个旧非法名全在 baseline 且 baseline/epoch mtime 仍为 10-19（未被改动）

**独立反例注入**（新建 `.work/log/review-inject-counterexample.log`，非 git 还原）：
- 注入后 `python3 tools/infra/check_run_artifacts.py` → **rc=1**，`FAIL (1 problem(s))` 列出该文件；`make check-run-artifacts` → **rc=2**（make 包装码，历史日志同为 `Error 1` 口径）
- `rm` 删除后重跑 → **rc=0**、`2810/0`；`check-no-residue` 复跑 rc=0，注入零残留

**约束核验**：① 门控 rc=0、0 illegal、7 条已不在 ✓ ② 三门控真实 rc 全 0 ✓ ③ git 干净、无未跟踪残留 ✓；完成区数字与我方输出逐条一致 ✓；两笔提交 `--name-only` 均只有本册 + milestones ✓ ④ 注入→FAIL→还原→回绿 ✓ ⑤ 未改门控脚本/未动 baseline/未加豁免/未改代码（`git diff HEAD` 空）✓；未触碰 SPEC-184t worktree ✓

**判决：Accepted**（口径备注：任务要求的"rc=1"指门控脚本退出码，实测 1；经 `make` 入口为 2，属 make 包装码，非缺陷）
