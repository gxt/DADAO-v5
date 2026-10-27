# TESTCASES-082t: L3 去 tset smoke（严格一层）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-076t
**状态**：待开始

## 背景
`TESTCASES-076t` 后，`check-full`（L3）仍直接列 `check-tset-{libc,llvm,embench}-smoke`，与 L2 的 `check-modules` 重复，违反「一个检查只在一层」。用户 2026-10-27 要求严格化。

## 目标
1. `_locked-check-full`（L3）**移除**三条 `check-tset-*-smoke` 直接成员；L2 保留四 scope smoke。
2. tset 覆盖由 `check-night` 的 tset full 三套件承担；`test-m6` 内既有 Embench E2E 作为集成步骤保留（说明其归属，不算 tset smoke 重复）。
3. 同步 `docs/Process-07`（L2/L3 表、§4 注）、`docs/Process-09`、`tests/README`、`tests/INVENTORY`、Makefile help；明确「tset full 只在夜跑」。
4. 不改变任何测试期望/断言；只调门控成员。

## 验收
- `make -n check-full` / Makefile 静态核验：L3 直接成员无 `check-tset-*-smoke`；L2 有且仅有三条 tset smoke；无目标跨两层。
- `make check` rc=0；`make check-modules` rc=0（L2 不变）。
- 文档与 Makefile 成员表逐项一致（可加机械断言/证据脚本）。
- 证据 `.work/evidence/<任务号>/run.sh`（注入「把 tset smoke 加回 L3」⇒ FAIL；`cp`+md5 还原 ⇒ PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-082t/`。

## 约束
- 只改 `Makefile`、`docs/Process-07`、`docs/Process-09`、`tests/README`/`INVENTORY`、任务书/milestones；不改测试语义。
- **不跑全量 `check-full`/夜跑**（用户 2026-10-27：全量+夜跑不下发）；用结构/`make -n`/L2 验证。
- 不提交、不 push。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
