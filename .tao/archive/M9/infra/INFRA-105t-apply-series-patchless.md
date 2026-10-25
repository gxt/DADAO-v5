# INFRA-105t: `apply_series.py` 支持 `patchless` 组件（`ISS-224`+`ISS-231` 合并）

**模块**：infra
**项目里程碑**：M9（用户 2026-10-24 裁定「M9 内做」）
**依赖**：无
**状态**：已验证

## 立项来源

`ISS-224` 与 `ISS-231` 是**同一条缺陷**（`ISS-231` 为 P2 主条，`ISS-224` 为较早登记）：`tools/infra/apply_series.py` 对 `patchless` 组件（`manifests/components.lock.toml` 中 `chipyard`/`linux`/`llvm-test-suite`/`libc-test`）报 `KeyError: 'patch_dir'`，`make apply-series` rc=2。

## 目标

1. `apply_series.py` 识别 `patchless` 组件：**跳过**并给出明确日志（`component=<name>: patchless, skip`），不得静默、不得 rc≠0。
2. `make apply-series` 在含 `patchless` 组件的清单上 rc=0。
3. 合并 `ISS-224` 到 `ISS-231`（或反之），保留一条并标 `merged`。

## 验收

1. `make apply-series` rc=0（全清单）；日志含每个 `patchless` 组件的 skip 行（贴真实输出）。
2. 有补丁组件的行为**不变**（应用/回退各 1 次对比）。
3. **可达 FAIL**：把 `patchless` 处理去掉 ⇒ `KeyError` 复现、rc=2（贴输出）。
4. `make check`(L1) rc=0；证据 `.work/evidence/<任务ID>/run.sh`。

## 约束

- 只改 `tools/infra/apply_series.py`（必要时 `Makefile`）；不 commit/push；临时目录 `/tmp/opencode/INFRA-105t/`。

## 完成区

**测试结果**：通过 30/30（`.work/evidence/INFRA-105t/run.sh` rc=0，日志 `.work/log/infra/INFRA-105t-evidence.log`）；失败：无
**修改文件**：`tools/infra/apply_series.py`（+13 行：docstring 5 行 + `main()` 循环首部 `patchless` 守卫 8 行）；`.tao/knowledge/issues.yaml`（`ISS-231` → closed/`resolved_by: INFRA-105t`；`ISS-224` 合并进 `ISS-231` → closed + `merged_into: ISS-231` + notes 合并标记）；`.work/evidence/INFRA-105t/run.sh`（新，`.work/` 不入库）
**验收结果**：
1. `make apply-series` **rc=0**；5 个 patchless 组件各一行 `apply-series: component=<name>: patchless, skip`（ansibench / chipyard / libc-test / linux / llvm-test-suite），其后 `musl` 照常 `already applied`；A3/A4 为 manifest 现算集合与日志集合的**双向**比对（不写死计数/清单）。
2. 有补丁组件行为不变（B 节实跑）：`embench-iot` `reset --hard <base>` → `make apply-series` ⇒ tree `85fa078e67b6…` 与回退前**一致**、`base..HEAD`=1、worktree 干净；二次运行幂等（tree 不变、0 新 commit、日志 `already applied`）。
3. 可达 FAIL（C 节实跑）：删掉守卫 ⇒ `KeyError: 'patch_dir'`、`make: *** [Makefile:224: apply-series] Error 1`、**rc=2**；注入前后 md5 相异（非空注入），`cp` 还原后 md5 复原、rc=0、5 条 skip 行回归。
4. 门控：`check-patch-tree` rc=0、`check-components` rc=0、`make check`(L1) rc=0（含 `check_issues`：18 open / 78 closed）。
**新发现/坑**：
- `check_issues.py` 只接受 `open`/`closed`，「merged」不能作 status ⇒ `ISS-224` 用 `status: closed` + `merged_into: ISS-231` + notes 合并标记表达，L1 绿。
- manifest 现有 **5** 个 patchless 组件（任务书写 4 个：`ansibench` 后加入）；实现用通用守卫，无写死清单。
- 证据脚本 C 节的可达 FAIL 依赖 `.work/source/chipyard` 已 fetch（若缺源会先撞 `missing source` 的 SystemExit=1，C1 会如实报 FAIL）；A5 已顺带断言 patchless 源的 HEAD/worktree 未被跳过逻辑触碰。
**遗留问题**：无（`docs/Process-01 §7` 未写「patchless 跳过」一句，按任务约束未改文档，已记新发现）

## 审阅记录

### 第 1 轮 engineer 自审
- 守卫位置：`name` 之后、`base`/`source`/`patch_dir` 之前；patchless 组件无补丁可应用，故先于「源缺失」检查跳过（与 `check_patch_tree.py --source-state` 同序），源存在性由 `fetch`/`manifest-check` 负责。
- 日志字面与任务书一致（`component=<name>: patchless, skip`），非静默；未加静默兼容桩。
- 回归面：A4 断言非 patchless 组件仍被逐条处理；B 节以 **tree 哈希**（非仅 rc）证明补丁落地内容不变。
- 防造假：注入以 md5 相异证明非空；还原用 `cp` + md5（未用 `git checkout/restore`）；EXIT trap 防中断留脏。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `ISS-224` 标 «merged» 与 `check_issues.py` 仅接受 open/closed 冲突 | ✅已修 | 用 closed + `merged_into` + notes 标记表达合并 | `check_issues.py` rc=0（E1–E5 PASS） |
| `docs/Process-01 §7` 未记 patchless 跳过，仅实现层有守卫 | ⏸延后 | 任务约束只改 py；已记入「新发现/坑」 | 需后续文档任务补一行 |
| 证据 C 节依赖 chipyard 源已 fetch（否则 FAIL 路径不同） | ❌不修 | 保留明确失败（C1 如实红）；A5 另行断言源未被触碰 | `run.sh` 30/30 PASS；缺源时会红而非假绿 |

### 第 1 轮 reviewer 验收
- 重跑证据脚本：`.work/evidence/INFRA-105t/run.sh` ⇒ `PASS=30 FAIL=0`，rc=0（脚本逐条断言均有可达 FAIL 路径，A3/A4 双向集合比对、C 节注入断言非空且 md5 对账，无恒真）。
- 独立重跑 `make apply-series`：**rc=0**，日志含 **5** 行 `apply-series: component=<name>: patchless, skip`（chipyard/linux/llvm-test-suite/libc-test/ansibench），musl 照常 `already applied`。
- 有补丁组件不变（**独立**取 `musl`，非脚本用的 embench-iot）：`reset --hard <base>` → apply ⇒ tree `735cbb785a55…` 与回退前**一致**、base+1、worktree 干净；二次运行 rc=0、tree 不变、日志 `already applied`。
- 可达 FAIL（自发注入，`cp`+md5）：删守卫 ⇒ `KeyError: 'patch_dir'`（`apply_series.py:113`）、**rc=2**；`cp` 还原 md5 复原 `86b6e3b5…` ⇒ rc=0、5 条 skip 回归。
- issue 合并合规：`ISS-224` = closed + `merged_into: ISS-231` + notes 合并标记；`ISS-231` closed + `resolved_by: INFRA-105t`；`check_issues.py` rc=0（18 open / 78 closed，resolved_by 约束 OK）。
- 门控独立重跑：`check-patch-tree` rc=0（198 patches OK）、`check-components` rc=0、`make check`(L1) rc=0。
- 改动范围核验：`git show --stat` 仅 `apply_series.py`（177→190 行）+ `issues.yaml` + `milestones.md` + 本任务书；`Makefile` 未改（md5 `ddbd8493…` 前后相同）；审查前后工作树快照干净、`apply_series.py` md5 复原。
- 判决：**Accepted**（skip 生效非静默、有补丁组件行为不变、注入红、issue 合并合规、门控全绿）。
