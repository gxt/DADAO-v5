# m15-infra-002: 清空 `.tao/knowledge/refs/`（直接删除，不归档）

**模块**：infra
**项目里程碑**：M15
**依赖**：无
**可并行分片**：否（跨 tools/docs/台账）
**预估**：1–1.5 h
**档位**：小改
**状态**：待开始

## 背景（用户 2026-11-18 裁定）

用户原话：「**N14：不做归档，按你说的 A 来办**」（A = 直接删除）。此前 2026-11-15 已定「`refs/` 下一步也要清空」。

理由：refs 里的报告**不再作为结论载体**——结论已落 `docs/TestReports/`、`docs/DDLN/`、任务书完成区与台账；refs 只剩过程快照。

## 目标

1. **删除** `.tao/knowledge/refs/` 下全部 **29 个文件**（约 3.3 MB），并删掉空目录。
2. **改写仍指向 refs 的活引用**（下节逐条），使它们在 refs 消失后不悬空。
3. **改规范落点**：`docs/Process-09` 两张表把「升格 `.tao/knowledge/refs/`」改为「结论写进任务书完成区 / `docs/TestReports/`；原始数据留运行期目录不入库（`refs/` 已废止）」。

## 引用改写清单（逐条，全部为活文档/代码）

| 位置 | 现状 | 改为 |
| --- | --- | --- |
| `tools/testcases/arch/min_rom_probe_integ007t.py:5` | 算法依据指 `refs/m12-006-cycle-design.md §11` | 指 `.tao/archive/M13/integ/m13-integ-007-hmon最小保存跳转算法.md`（同一裁决的正式归档记录，已核实含 0xD8 布局与 6 步算法） |
| `tools/testcases/parity/int_diff.py:13` | 「输出 `.tao/knowledge/refs/…`」 | 「输出到运行期证据目录；结论写任务书完成区」 |
| `tools/testcases/parity/acceptance_report.py:18/547/703` | 同上 3 处 | 同上 |
| `tools/testcases/parity/README.md:150/181/233/242` | 同上 4 处 | 同上 |
| `.tao/knowledge/issues.yaml`（`ISS-357`） | 「详见 `refs/TESTCASES-103t-timeout-recheck.md`」 | 去掉该路径，只留结论（修复方向已在该条正文） |
| `docs/Process-09-测试组织规范.md` §15 表 + §15.1 表 | 「升格 `.tao/knowledge/refs/`」 | 「结论写任务书完成区 / `docs/TestReports/`；原始数据不入库；`refs/` 已废止」 |

**不改**：`.tao/archive/**`（历史记录，含旧路径属当时事实）；`.tao/tasks/**` 里已验证任务书的历史措辞（不改写既有完成区/审阅记录）；`.cache/refs/**`（外部参考仓，只读）。

## 验收（逐条贴真实 rc）

1. `ls .tao/knowledge/refs` → `No such file or directory`（rc=2）；`du` 确认释放约 3.3 MB。
2. 全仓 `grep -rn "knowledge/refs"`（排除 `.tao/archive/**`、`.tao/tasks/**`、`.cache/**`）= **0**。
3. `make check-knowledge-refs`、`check-dirs`、`check-contracts-dir`、`check-no-residue`、`check-test-reports` 全 **rc=0**。
4. `python3 -m compileall -q tools` rc=0（改的是 docstring，仍须过编译）。
5. `make check-tests-index` rc=0（parity 文档改动不得影响索引）。
6. **1 路注入**：把 `min_rom_probe_integ007t.py` 的依据路径改回 `refs/...` ⇒ 断言 2 必须红；`cp`+md5 还原 ⇒ 回绿。
7. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**。
2. 只动：`refs/` 删除 + 上表 7 个文件；**不动** `spec/`、`.tao/contracts/`、`contracts/`、`components/`、`manifests/`。
3. 不改版本号。
4. 删除用 `git rm -r`（保留历史）；不要 `rm -rf` 后留下未跟踪残影。
5. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（无）

## 审阅记录

（待填）
