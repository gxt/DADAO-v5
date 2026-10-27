# TESTCASES-082t: L3 去 tset smoke（严格一层）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-076t
**状态**：待验收

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

**状态**：待验收

### 修改文件
- `Makefile`：`_locked-check-full` 去三条 `check-tset-*-smoke`；help + L2/L3 注释同步（tset smoke 只 L2、full 只夜跑；`test-m6` Embench E2E = 集成步骤）
- `docs/Process-07-门控分层规范.md`：L3 行去 tset smoke + §4 新增 tset 分工条目
- `docs/Process-09-测试组织规范.md`：§2 现行门控补夜跑；§8 L3 行去 tset smoke + tset 子条
- `tests/README.md`、`tests/INVENTORY.md`：L3 成员与 tset 归属
- `.tao/knowledge/milestones.md`：TESTCASES-082t 状态行
- `.work/evidence/TESTCASES-082t/run.sh`：证据脚本（静态 + `make -n` + 文档一致性 + 注入自检）

### 验收命令与结果
- `make check` → rc=0（L1 PASS）日志 `.work/log/testcases/TESTCASES-082t-check.log`
- `make check-modules` → rc=0（L2 PASS，四 scope smoke 含 tset×3）日志 `...-check-modules.log`
- `make -n check-full` → rc=0，`check-tset-*-smoke` 计数 **0**（`test-m6` 仍在）；日志 `...-dryrun-check-full.log`
- 静态：`_locked-check-full` 0 条 tset smoke；`_locked-check-modules` 恰 3 条；每条 tset smoke 只在唯一一层直接列出；三层均无 `check-tset-*-full`（tset full 只在 `check-night`）
- `./.work/evidence/TESTCASES-082t/run.sh` → **35/35 PASS**（rc=0）
- `run.sh --inject` → 注入 3 条回 L3 ⇒ 4/31 FAIL；`cp`+md5 还原（`8ca6d57c…` 前后一致）⇒ 31/31 PASS；SELFCHECK PASS

### 新发现/坑
- `make -n check-full` 会真实执行 gate-lock 包装的 `+` recipe（取锁 + 内层 dry-run）；证据脚本对成员集合改用 `make -n _locked-check-full`（免锁、同集合），`make -n check-full` 另行一次性核验（0 条 tset）。
- Makefile 分层注释「FP 探针仍在 L2」是 076t 后遗留错误，已改「只在 L3」（与 L2 成员一致）。

### 遗留
- 无。未跑 `check-full`/`check-night`（用户 2026-10-27 裁定不下发）。

## 审阅记录

### 第 1 轮 engineer 自审

- 逐行核对 `_locked-check-full` 依赖行：去三条 tset smoke，保留 `check-inst`/`check-arch`/`check-unit-full`/4 FP 探针/`test-m6`；`make -n` 实测 0 条 tset smoke。
- L2 依赖行未改：恰 3 条 tset smoke，与 P07/P09/README/INVENTORY 四处 L2 成员表一致。
- 四处 L3 成员表均无 tset smoke 且注明「smoke 只 L2、full 只夜跑；test-m6 Embench E2E 是集成步骤」。
- 证据脚本：35 项断言各有可达 FAIL；`--inject` 注入 3 条回 L3 ⇒ 4 项 FAIL；`cp`+md5 还原（`8ca6d57c…`）⇒ 全绿（未用 `git checkout/restore`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `make -n check-full` 会真实执行 gate-lock 的 `+` recipe（取锁 + 内层 dry-run），证据脚本依赖它会被并发锁干扰 | ✅已修 | 证据脚本成员集合改用免锁的 `make -n _locked-check-full`（同集合） | `run.sh` rc=0（35/35）；`make -n check-full` 另行核验 rc=0、0 条 tset |

- 判决：无未修 finding ⇒ 状态 `待验收`。
