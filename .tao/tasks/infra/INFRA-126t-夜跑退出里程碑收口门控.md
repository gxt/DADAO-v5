# INFRA-126t: 夜跑退出里程碑收口门控（改为观测口径）

**模块**：infra
**项目里程碑**：M11
**依赖**：无（与 `TESTCASES-101t` 独立；只改门控与文档，不改测试）
**状态**：已验证

## 用户裁定（2026-11-06）

> 「我觉得，对于夜跑，你有些误解；Dadao并不是完整、成型的系统，夜跑是需要随时调整的，其目的也并非是为了里程碑」
>
> 选 **A：夜跑只做观测，不阻断收口** —— 「本轮照常跑一次夜跑，红项逐条分诊/登记；M11 收口不要求报告全绿（需调整 check-night-report/check-milestone 依赖或用例口径）」。

## 现状

`make check-milestone` 的依赖里含 `check-night-report`，而 `check-night-report` 要求**最近一次夜跑报告存在且全部 rc=0**。效果：夜跑被当成里程碑验收动作，任何用例红都会阻断收口；而 DADAO 仍在演进，夜跑成员/期望/known-fail 本就需要随时调整。

`check-l3-report` 保持现状（L3 是可重复的全量验证，不属本次调整范围）。

## 目标

1. `Makefile`：`check-milestone` **去掉** `check-night-report` 依赖；保留 `check-l3-report`、`check-spec-archive`、`check-spec-archive-verify`、`check-sync-nonmaskable`、`check_milestone_tasks.py`、`check_tasks.py --strict`。
2. `check-night-report` 目标**保留可用**（仍是「报告存在性 + 结构 + 结果」检查），但改为**按需诊断**，不再被里程碑门控调用；其自身判据与 `--self-test` 不改。
3. 同步文档与帮助文本：
   - `Makefile` 中 `check-milestone` / `check-night-report` 的注释与 `make help` 文案（夜跑 = 观测，按需消费；不再列入里程碑依赖）。
   - `docs/Process-07-门控分层规范.md`：§ 表格中 `check-milestone` 依赖与「夜跑（非三层之一）」行的口径；触发点描述。
   - `docs/Process-09-测试组织规范.md`：里程碑门控组成与夜跑定位（两处）。
4. 记录口径：夜跑红项按「真缺陷 / 语料假设过时 / 环境」分诊，真缺陷立任务或 issue；不以「一次全绿」为里程碑条件。
5. 不改夜跑成员集合、不改 `night_run.py` 行为、不改任何测试用例与期望。

## 范围 / 非范围

**在范围内**：`Makefile`、`docs/Process-07-门控分层规范.md`、`docs/Process-09-测试组织规范.md`、`tools/testcases/check_night_report.py`（仅文档字符串措辞，如提及里程碑层）、本任务书、`milestones.md`、`discussing.md`。

**不在范围**：`check-l3-report` 及 L3 口径、`check-night-report` 判据逻辑、`night_run.py`、测试用例/期望、QEMU/gem5/LLVM 组件。

## 验收标准

1. `make -n check-milestone` 不再包含 `check-night-report`；仍包含 `check-l3-report` 等其余依赖。
2. `make check-night-report` 仍可用：对现有报告按原判据给出 rc（红报告仍 rc=1，`--self-test` rc=0）。
3. `make check`（L1）rc=0；`make check-milestone` 在本任务改动后可达（m 册存在时）或至少不再因夜跑缺失而失败。
4. 文档三处口径一致：夜跑 = 观测/按需消费，不阻断收口；L3 仍为收口门控。
5. 反例：临时把 `check-night-report` 依赖加回 ⇒ `make -n check-milestone` 断言 FAIL；还原后回绿（`cp`+`md5sum -c`，禁 git 还原）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是**门控口径**调整，不是降低测试覆盖：夜跑照常跑、结果照常落报告，只是不再作为收口硬条件。
- 若后续希望恢复硬门控，可另立任务改回（本任务把口径写清即可）。

## 完成区

**测试结果**：证据脚本 16/16 PASS（rc=0）。`make -n check-milestone`：无 `check-night-report`、有 `check-l3-report`（rc=0）。`make check-night-report`：rc=2（最新夜跑目录三件套缺失 ⇒ 红，按现状如实记录）；`check_night_report.py --self-test` 8/8 PASS（rc=0）。`make check`（L1）当时 rc=2，唯一失败为共享组件源树的并行任务漂移（`check-patch-tree`），与本任务改动无关（该漂移已在并行任务合入后消失，reviewer 复跑主树 L1 rc=0）；`make -k check` 其余目标全 PASS。`make check-milestone` rc=2：归档结构/内容 sha、sync-nonmaskable、`check-l3-report` 均 PASS，红在「M11 无 m 册」，不再红在 night-report。反例：依赖行加回 `check-night-report` ⇒ dry-run 断言检出（命中 1 处）；`cp`+md5 还原后 md5 一致、复绿。
**修改文件**：`Makefile`、`docs/Process-07-门控分层规范.md`、`docs/Process-09-测试组织规范.md`、`tools/testcases/check_night_report.py`（仅 docstring 措辞）、`.tao/knowledge/milestones.md`（状态行）、本任务书；证据脚本在运行期证据目录（未入库）。
**验收结果**：夜跑=观测/按需消费、不阻断收口；L3 仍为收口门控（Makefile 注释/help、Process-07 三处、Process-09 两处口径一致）。未改 `night_run.py`、测试用例/期望、`check-night-report` 判据逻辑。
**新发现/坑**：worktree 原无 `.cache`，`check-spec-archive-verify` 会先红；以符号链接指向主工作树共享缓存目录后可达后续检查（环境处置，非代码改动）。共享组件源树漂移曾使 L1 `check-patch-tree` 红（并行任务所致），需另行处置。
**遗留问题**：`make check`（L1）因上述共享源树漂移未达 rc=0（非本任务引入）；M11 m 册未建 ⇒ `check-milestone` 按预期红在 m 册（本任务只保证不再红在夜跑）；`docs/DDLN/F001/F005/F007` 与 `discussing.md` 仍写夜跑由里程碑消费（不在本任务范围；后者仅主会话可改），待收尾统一定口径。

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：改动为门控依赖 + 文档口径，无语义/判据变更；验收项经证据脚本与真实 rc 逐条对齐，无未修 finding。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 夜跑是否仍可能从 check-milestone 侧被调用 | ✅已修 | 依赖行去 `check-night-report` | `make -n` 0 处调用、`check_l3_report.py` 1 处；`make check-milestone` 输出 0 处 night-report |
| check-night-report 是否被误删/改判据 | ✅不修（保留） | 目标与 recipe 原样；仅 docstring 措辞 | 目标可调（有 report dir 行、无 No rule）；`--self-test` 8/8 rc=0 |
| 文档口径是否一致 | ✅已修 | Makefile 注释/help + Process-07 ×3 + Process-09 ×2 | 三处均写「观测/按需消费，不阻断收口；L3 仍为收口门控」 |
| 是否越界改夜跑成员/用例/期望 | ✅未越界 | 仅上述 6 文件（含共享台账状态行） | `git diff --stat` 6 文件，无 `night_run.py`/tests/期望 |
| 反例是否可达 FAIL | ✅已修 | 临时加回依赖 | 注入后 dry-run 检出 1 处；`cp`+md5 还原后一致、复绿 |

#### 第 1 轮 reviewer 验收

**判决**：**Accepted**（4 条非阻断 finding，交 architect 收尾处置）。以下 rc 均为我本机重跑，未采信完成区。

**重跑记录**
- `make -n check-milestone` **rc=0**（7 行 recipe）：`check_night_report.py`/`check-night-report` 命中 **0**；`check_spec_archive.py`、`gen_spec_archive.py --verify`、`check_sync_nonmaskable.py`、`check_l3_report.py`、`check_milestone_tasks.py`、`check_tasks.py --strict` 各 **1**（`make -n` 只打印 recipe，故以脚本名对应目标名核计）。
- `make check-night-report` **rc=2**（最新夜跑三件套缺失，按现状红）；`check_night_report.py --self-test` **rc=0**（8/8）。
- `make check-milestone` **rc=2**：spec-archive（7 版本 OK）/ sync-nonmaskable / `check-l3-report` PASS；红因唯一 =「当前里程碑 M11 无 m 册 … 结果: FAIL (1 项)」；全日志 `night` 命中 **0**。
- `make check`（L1，任务树）**rc=2**；`make -k check` **rc=2** 且唯一 `***` = `check-patch-tree`（libc-test ⑨⑥，2 problem），其余 1575 行目标全 PASS ⇒ 排除该红后 L1 其余项全绿。
- **与完成区「主工作树同红」不符（如实记）**：主树 `check-patch-tree` **rc=0**、`make check`（L1）**rc=0**。根因：主树 HEAD 已前进 `8ae27072`（09:55:55 合入 TESTCASES-101t，libc-test patch +29 行），任务分支基线陈旧，而共享组件源树已被并行任务更新 ⇒ 任务树红 = **基线陈旧 + 共享源树漂移**，非本任务改动引入（6 文件不含 patch/manifest/源树）；squash 合入 master 后该红消失。
- 运行期证据脚本重跑 **rc=0，16/16 PASS**；逐条审过：断言有可达 FAIL 路径、无恒真/双支同果，反例断言由脚本自身注入证实。
- **独立注入**（reviewer 自做）：`cp` 备份 → 依赖行加回 `check-night-report` → `make -n` 命中 **1**（断言 FAIL）→ `cp` 还原 → `md5sum -c` **OK**（`417bf21e…`）→ `make -n` 复绿 **0**；`git status` 前/后/末三快照逐行一致，6 文件 md5 全 `OK`（未用任何 git 还原）。

**约束核验**：范围 = 6 文件（无 `night_run.py`/tests/期望/`contracts/`）；`check_night_report.py` 去 docstring 后与 HEAD **逐字节相同**（零逻辑差异）；`check-night-report` 目标与 recipe 未动、**无任何其它目标依赖它**；完成区 **8 行 ≤30**、状态 `待验收`、无绝对/家目录/临时路径。

**finding（均非阻断）**：F1 `tests/README.md:83` 仍标 `check-night-report` 为「里程碑层」（该文件不在本任务声明范围）；F2 `docs/DDLN/F-测试体系/DD-F001:31`、`DD-F005:42`、`DD-F007:6` 仍写「夜跑次日由里程碑消费」（DDLN 超范围）；F3 `.tao/knowledge/discussing.md:24` 仍隐含「夜跑红先修再收口」（仅主会话可改）；F4 完成区「主工作树同红」在 09:55 合入后已不成立，且出现组件源树检出路径（AGENTS「任务书不写运行期路径」体例小错；architect 收尾已按原意脱敏）。

#### 收尾（architect，2026-11-06）

- F1：`tests/README.md` 仍标 `check-night-report` 为「里程碑层」，并入 `INFRA-127t` 文档同步。
- F2：DDLN `DD-F001/F005/F007` 同类口径，并入 `INFRA-127t`。
- F3：`discussing.md` 由主会话同步。
- F4：完成区已改写；运行期路径已移除。
- 判决 Accepted，状态置 `已验证`。
