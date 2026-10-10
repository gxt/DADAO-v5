# INTEG-026m: M6 integ 里程碑（整体收敛点）

**模块**：integ
**项目里程碑**：M6
**状态**：里程碑
**目标**：M6 端到端闭环——驱动 `lli` 值级对拍 / Embench / lit 全量档；新 target **`test-m6`**（**opt-in，不进 `make check`**）；`make check` 收口。**M6 整体收敛点**——依赖的各模块 `m` 均 `里程碑` ⇒ 主会话置项目里程碑 `达成`（`spec/Process-04 §1`）。
**关联任务**：`INTEG-025t`

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tools/integ/**`（M6 E2E 驱动）、`Makefile` 的 `test-m6`（opt-in）目标
- `make test-m6` EXIT=0；不回归：`make check` EXIT=0
- 各模块 `m` 均 `里程碑`：`INFRA-052m`/`SPEC-125m`/`LLVM-067m`/`QEMU-054m`/`TESTCASES-040m`
- 跨模块影响已处置（无未处置项）
（核验通过后，主会话将 `**状态**` 置为 `里程碑`；依赖模块 `m` 均达成后置项目里程碑 `M6` 为 `达成`）

## 完成区（整体收敛 + M6 归档，2026-10-11）

**测试结果**（真实输出；日志 `.work/log/integ/INTEG-026m-{check,test-m6}.log`）：
- `make check` **EXIT=0**（`repository checks: PASS`；`check-lit` 89/89；`check_issues` 24 open / 18 closed）。
- `make test-m6` **EXIT=0**（opt-in）：① `check-lit-full` 12/12；② `diff_ir_lli` hits 19/19 / matched 19/19；③ Embench 19 基准 × `-O0`/`-O2` = **38/38**（judge guest exit 0）。
- 核验项：`INTEG-025t` = `已验证`；5 模块 `m` 均 `里程碑`；产出存在（`tools/integ/run_embench_e2e.py` + `Makefile:test-m6`）。

**修改文件**：
- `.tao/archive/M6/**`：新建 `README.md` / `m6-retrospective.md` / `issues-closed.md`；`git mv` **45** 份 M6 任务书入 `<模块>/`（+ 本 `m` 自归档 = **46**）。
- `.tao/tasks/**`：45 份任务书移出；本 `INTEG-026m` 自身末步 `git mv`。
- `.tao/knowledge/milestones.md`（M6=**达成** + M7 遗留 + 任务流水/当前进度收敛）、`issues.yaml`（提取 18 closed + 头指针 + scope 枚举 M6=已达成）、`changelog.md`（M6 归档指针 + 移出 1 条）、`MEMORY.md`（M6 归档指针行）。

**验收结果**（逐条对齐）：
1. 关联任务 `INTEG-025t` = `已验证` ✓；2. 6 模块 `m` 全 `里程碑` ✓；3. `make check`/`make test-m6` 均 **EXIT=0** ✓；4. 项目里程碑 **M6 置「达成」**（`milestones.md`）✓；5. M7 遗留（`ISS-187`/`188`/`189`、`check-spec-refs`、`components/qemu/README.md:10`、`LLVM-074t` 遗留、`ISS-108`/`164`/`074`/`167`）已显式登记（= 已处置）✓；6. M6 已关 issue **18** 条提取入 `issues-closed.md`（活台账 open 24 / closed 0，`check_issues` rc=0）✓；7. **`spec/` 交集为空** ✓。

**新发现/坑**：
- **台账待收敛（如实登记，未擅自处置）**：`ISS-043`/`045`/`138`/`148`/`156`/`159`/`162` 七条由 M6 任务（`LLVM-062t`/`064t`、`SPEC-123t`）完成区**声称已修/已收口**，但 `issues.yaml` 中 `resolved_by` 仍 `null`、`status` 仍 `open`（父任务提交未回填台账）。按 `Process-04 §3` 步骤 1 本应在归档前回填 `closed`；`INTEG-024t` 已将裁决动作显式留待 `§3` ⇒ 本条**只登记、不改**，提请 M7 `§3` 梳理收口（亦记于 `issues-closed.md`「待收敛」、`milestones.md` 遗留）。
- **归档 `git mv` 相似度**：任务书内容膨胀 + 追加审阅记录 ⇒ 逐个 rename 检测相似度可能 <50%（`Process-04 §4.1` 自归档先例 `INTEG-022t`，`lessons §7.25`/`§8.19`）。

**遗留问题**：见 `milestones.md`「遗留（M6→M7）」；本 `m` 无未修 finding。

## 审阅记录

#### 第 1 轮 architect 里程碑核验 + 归档（2026-10-11）

**范围**：M6 整体收敛核验（门槛重跑 + 模块 `m` 状态 + 跨模块处置）+ M6 归档（任务书 `git mv` + `README.md`/`m6-retrospective.md`/`issues-closed.md` 新建 + 台账收敛）。

**核验（真实输出，逐项）**：
- `make check` = **EXIT=0**（lit 89/89、`repository checks: PASS`、`check_issues` 24 open/18 closed）。
- `make test-m6` = **EXIT=0**（`check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench 38/38）。
- 关联任务/模块 `m`：`INTEG-025t` = `已验证`；`INFRA-052m`/`SPEC-125m`/`LLVM-067m`/`QEMU-054m`/`TESTCASES-040m` 均 `里程碑`（逐个 grep 任务书 `**状态**`）。

**归档**：`git mv` **45** 份 M6 任务书入 `.tao/archive/M6/<模块>/`（`infra 5 / spec 9 / llvm 17 / qemu 4 / testcases 6 / integ 4`）；本 `INTEG-026m` **自归档**（末步 `git mv`，共 **46**）。`issues.yaml` 提取 18 条 closed（`resolved_by` = M6 任务）入 `issues-closed.md` 并移出活台账（`check_issues` rc=0）；`changelog.md`/`MEMORY.md`/`milestones.md` 归档指针与 M6 达成同步。

**跨模块处置**：M6 遗留全部已登记（= 已处置）——见 `milestones.md`；**无未处置项**。**台账待收敛 7 条**如实登记（见完成区「新发现/坑」），未擅自 close。

**判决**：核验项全通过 ⇒ `**状态**` = `里程碑`；**项目里程碑 M6 = 达成**。

