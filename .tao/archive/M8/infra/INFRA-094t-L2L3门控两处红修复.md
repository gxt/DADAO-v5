# INFRA-094t: L2/L3 两处红修复（ir-lli 归类 + authoritative 运行产物）

**模块**：infra
**项目里程碑**：M8
**依赖**：无（约束：只动 `tests/llvm/ir-lli/manifest.yaml`、`.work/tests/authoritative/**` 与台账；不改实现 / 不改测试期望）
**状态**：已验证

## 背景（主会话 2026-10-19 派发，现场复现）

- `make check-modules` / `make check-full` 均 rc=2。
- **红 1（L3 `test-m6` → `diff_ir_lli`，structural）**：
  `unclassified *.ll under corpus_roots` = `f128-codegen.ll`、`indirectbr.ll`、
  `m8-varargs-stack-align.ll`、`p1-fp-libcall-log.ll`、`vec-load-widen.ll`
  （均在 `tests/llvm/lit/CodeGen/DADAO/`）。
- **红 2（L1 `check-run-artifacts`，A2）**：`A2 .work/tests/authoritative/latest is missing`。

## 判据（来自 `tests/llvm/ir-lli/README.md` + `docs/Process-08`）

- ir-lli 是**值级差分**语料：只有自带 `@main` 值通道的单 TU 模块才可进 `include`。
  上述 5 个是 `llc | FileCheck` **结构测试**（无 `@main`），进 `exclude`、
  `class: no-value-entry`；不得塞进 `include`（那会要求 `lli` 跑出值，语义错）。
- authoritative 权威跑必须落 `<UTC>-<suite>-<mode>/` 三件套目录，`authoritative/latest`
  指向最新权威跑目录；门控断言**不放宽**。

## 处置

1. `manifest.yaml` 新增 (g) 段：5 个 IR 逐条入 `exclude`，`class: no-value-entry`
   + 逐条理由（LLVM-102t/103t/105t/106t/111t）。
2. `.work/tests/authoritative/`：把 6 个真实权威跑的 run 目录（embench/libc/llvm-ts ×
   static/dynamic）从 `.dadao/tests/**` 复制进来（`run.json` 与既有平铺
   `*.json` md5 逐一致），`latest` → 最新 `20261019T072226Z-llvm-ts-user-dynamic`。
   平铺 `*.json` / `*.log`（历史 caller-facing 副本）保留不动。
3. `check_run_artifacts.py` **零改动**（断言未放宽）。

## 完成区

**测试结果**：证据脚本 12/12 PASS（5 项基线 + 3 组可达 FAIL 注入〔manifest 删条目 / A2 缺
`meta.json` / run.json 损坏〕+ 2 项回绿 + 2 项注入命中消息）。结构闭包现场解析：
`unclassified=0 / overlap=0 / missing=0` 且 `include+exclude==on-disk`；`diff_ir_lli` 19/19；
check-run-artifacts PASS；6 个 run 目录 `run.json` md5 与平铺副本逐一致。
`make check`（L1）**rc=0**；`make check-full JOBS=8` **rc=0**；`make check-modules JOBS=8`
**rc=2**，唯一红 = `build-picolibc` 的 `strtold.c`（`unsupported library call operation`），
与 `ISS-283` 既有缺口逐字一致，非本笔引入。

**修改文件**：
- `tests/llvm/ir-lli/manifest.yaml`（+5 exclude 条目 + (g) 段注释）
- `.tao/knowledge/milestones.md`（+1 行）
- `.tao/knowledge/issues.yaml`（+ISS-285）
- `.tao/tasks/infra/INFRA-094t-L2L3门控两处红修复.md`（本册）
- 非 git：`.work/tests/authoritative/**`（6 个运行目录 + `latest` 符号链接）
- 证据：`.work/evidence/INFRA-094t/run.sh`

**验收结果**：
- `.work/evidence/INFRA-094t/run.sh`：`[EVIDENCE] PASS (12 checks)`，rc=0。
- `diff_ir_lli`：`structural: on-disk=67 include=19 exclude=48 unclassified=0 overlap=0 missing=0`
  → `hits: 19/19`、`matched: 19/19` → `PASS`（rc=0）。
- `make check-run-artifacts`：`check-run-artifacts: PASS`（rc=0），
  `[PASS] A2 .work/tests/authoritative/latest -> .../20261019T072226Z-llvm-ts-user-dynamic`。
- `make check`（L1）：rc=0（含 `check-run-artifacts` / `check-milestones-fresh` / `check_issues`）。
- `make check-full JOBS=8`：rc=0（lit full 12/12、diff 19/19、Embench 38/38）。
- `make check-modules JOBS=8`：rc=2（L2 前序项全过：lit 114/114、codegen/elf/semihost PASS；
  末项 `check-picolibc-tests` → `build-picolibc` 红，= ISS-283）。

**新发现/坑**：
- `check-modules` 的红**不只有** ir-lli / run-artifacts：`check-picolibc-tests` →
  `build-picolibc` 在 `strtold.c` 处 `fatal error: error in backend: unsupported library
  call operation`（i128→f128 UINT_TO_FP 缺 `__floatuntitf`）= 既有 `ISS-283`；LLVM-110t
  当日 10:52 的日志同签名，证明非 LLVM-112t / 本笔引入。
- 权威跑的 `.json/.log` 平铺副本（`--json-out` 指到 `authoritative/`）**不是**运行目录；
  运行目录留在默认 `--work-dir`（`.dadao/tests/**`）。补齐权威集必须复制**真实运行目录**
  （含真 `meta.json`），不得凭空补 `meta.json`（会造假证据）。

**遗留问题**：`make check-modules` 要回绿需修 `ISS-283`（注册
`RTLIB::{SINT,UINT}TOFP_I128_F128`）——属实现面，本笔按边界未动。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-19）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| ① 证据脚本结构断言写死 `67/19/48/0`（违「计数现场统计」） | ✅已修 | `run.sh` 改为现场解析 structural 行，并与 manifest 的 `len(include)/len(exclude)`、`include+exclude==on-disk` 对账 | `run.sh` 12/12 PASS，含该检查 |
| ② manifest (g) 段注释把 106t 等误标为 M8/M7（f128 属 M9） | ✅已修 | 注释改为「later LLVM tasks」 | manifest 解析 + `diff_ir_lli` PASS |
| ③ 完成区写「4/4 项」与证据脚本 12 项不符 | ✅已修 | 完成区改为 12/12 并补 L1 结果 | `make check` rc=0 |
| ④ 自审复核「`check_run_artifacts.py` 零改动」是否够 | ✅不修 | 断言 A2 与 `docs/Process-08` §1.2 一致，红因是**产物缺失**而非断言过严；放宽会掩盖真问题 | `make check-run-artifacts` rc=0 + 注入②可达 FAIL |

#### 第 1 轮 reviewer 验收

**审阅范围**：manifest.yaml exclude 条目、authoritative 目录结构+latest、check_run_artifacts.py diff、证据脚本 default、独立注入、check-patch-tree、check_milestones_fresh。

**重跑记录**（真实输出/退出码）：

| 命令 | 期望 | 实际 | rc |
|------|------|------|----|
| manifest 5 exclude `no-value-entry` | 5/5 PASS | 5/5 PASS, include=19, exclude=48 | 0 |
| `check_pairs.py` | 6/6 md5 match | 6/6 match | 0 |
| `git diff check_run_artifacts.py` | 空 | 空 | 0 |
| `check-run-artifacts` | PASS | PASS (57 A2 + A3) | 0 |
| `check-patch-tree` | 181 patches OK | 181 patches OK | 0 |
| `check_milestones_fresh.py` | PASS | PASS (71 行) | 0 |
| 独立注入（manifest 删 1 条 exclude） | diff_ir_lli rc=1 | rc=1, unclassified 含 f128-codegen.ll | 1 |

**证据脚本审阅**：`run.sh` 12 项检查，baseline 5 项 + 注入 3 组 + 回绿 2 项。重跑结果：baseline 中 `diff_ir_lli` 和 `structural closure` 报 FAIL（rc=1），根因 = LLVM-113t/114t 新增 2 个 `.ll`（`m8-f128-math-libcall.ll`、`m8-i128-f128-libcall.ll`）未入 manifest，导致 `on-disk=69 > include+exclude=67`。**此为环境漂移**（其它任务 commit 引入），非 INFRA-094t 缺陷。注入 3 组全部可达 FAIL + 还原 ✓。

**约束核验**：
- ✅ manifest.yaml 5 个 `.ll` 在 exclude（class: no-value-entry），不在 include
- ✅ authoritative/ 有 6 个真实运行目录 + latest 符号链接 → `20261019T072226Z-llvm-ts-user-dynamic`
- ✅ 6 对 run.json md5 与平铺副本逐一致
- ✅ `check_run_artifacts.py` 零改动（git diff 为空）
- ✅ 可达 FAIL：删 1 条 exclude ⇒ diff_ir_lli rc=1；缺 meta.json ⇒ A2 FAIL；corrupt run.json ⇒ pair check FAIL
- ✅ 未改 spec/contracts/实现代码

**环境漂移说明**：`diff_ir_lli` 基线 FAIL 源于 LLVM-113t/114t commit（b996e9a/0e52cdb）新增 2 个 `.ll` 文件未入 manifest。manifest 需随后续任务更新，不在 INFRA-094t 范围。INFRA-094t 的三项改动（manifest 5 条 exclude、authoritative 目录、check_run_artifacts.py 未改）均正确。

**判决**：**Accepted** — INFRA-094t 自身改动全部正确，约束无违反。`diff_ir_lli` 基线漂移源于其它任务 commit，非本笔缺陷，建议后续任务补 manifest。
