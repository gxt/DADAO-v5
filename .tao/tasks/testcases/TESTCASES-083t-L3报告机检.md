# TESTCASES-083t: L3 结果报告与 check-milestone 机检

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-076t、TESTCASES-082t
**状态**：待开始

## 背景
`TESTCASES-076t` 只加了夜跑报告存在性；`check-milestone` 的「L3 结果」仍无机检载体（076 遗留⑥），无法审计 `check-full` 是否真的全绿。

## 目标
1. `check-full` 外层（或新包装目标）在运行时写机器可读报告：
   - `.dadao/tests/l3/<UTC>/manifest.tsv`：`scope<TAB>suite<TAB>rc<TAB>log`，逐成员一行；
   - `meta.json`（命令/时间/commit/工具链摘要）；
   - `run.log`（汇总 + `[exit marker] rc=N`）。
   复用 `night_run.py` 的 manifest 语义，避免两套格式。
2. 新增 `check-l3-report`（里程碑收尾专项，不入 L1/L2/L3 日常）：
   - 最新 L3 报告存在、结构完整、至少覆盖四 scope、任一 rc≠0 ⇒ FAIL；
   - 未跑 L3 ⇒ 明确 FAIL（不是 SKIP）；
   - `--self-test` 覆盖：缺文件、空 manifest、rc 非零、缺 scope、伪造全绿等可达 FAIL。
3. `check-milestone` 增加对 `check-l3-report` 的依赖（与 `check-night-report` 并列）。
4. 文档：`docs/Process-07`/`Process-09`、`tests/README` 说明报告落点/格式/触发点。

## 验收
- `check-l3-report --self-test` rc=0（每个反例可达 FAIL）；无报告时 rc=1 且报错明确。
- 用**临时 fixture**（不跑全量）构造全绿/红报告，验证 PASS/FAIL 与 `check-milestone` 依赖接线。
- `make check` rc=0；`make check-milestone` 的报告项在 fixture 下可验证（真实 L3 未跑时按设计红）。
- 证据 `.work/evidence/<任务号>/run.sh`（含注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-083t/`。

## 约束
- 只改 `tools/testcases/`、`Makefile`、`docs/Process-07`/`09`、`tests/README`、任务书/milestones；不改测试期望。
- **不跑全量 `check-full`/夜跑**（用户 2026-10-27：全量+夜跑不下发）；fixture/自检即可。
- 不提交、不 push。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
