# m15-infra-002: 清空 `.tao/knowledge/refs/`（直接删除，不归档）

**模块**：infra
**项目里程碑**：M15
**依赖**：无
**可并行分片**：否（跨 tools/docs/台账）
**预估**：1–1.5 h
**档位**：小改
**状态**：已验证

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

## 待裁定（engineer 2026-11-18 登记；**删除未做完，见完成区**）

**已核实无规范级依据**：`spec/`、`contracts/`、`.tao/contracts/`、`.tao/adr/` 对 `refs/` 的引用
`git grep` 全空。

**但 20/29 个文件仍被非归档活文件引用，其中 13 份是代码的输入/输出默认值（不是 docstring）**：

1. `GEM5-002t-semantic-matrix.tsv`（224 K / 265 行）—— `gen_decode_table.py:258` 直接 `open`，按 id 交叉校验
   `mask/value/contract_ref/format/scope/opc` 与 `contracts/opcodes.yaml`（`:68-69` 的 `MATRIX_RETIRED_IDS`/
   `MATRIX_ABSENT_CONTRACT_REF` 以矩阵为基线）；`refresh_matrix_notes.py:254,271` **就地刷新**其 `g1_note`
   （`--check` 逐字节比对，`check_converge.py:333` 调用）；`check_b6.py:30`/`check_b7.py:53`/`check_converge.py:36`
   亦以它为输入。活用法：`make check-gem5-decode`（Makefile:516）、`components/gem5/README.md:569`。仓内无副本。
   ⇒ 单删它即断 gem5 解码表再生与周期注记工作流。
2. `GEM5-021t-baseline-summary.json` → `run_gem5se_ratio_user.py:79` 的 `DEFAULT_CASE_LIST`；`night_run.py:10,92`。
3. `TESTCASES-104t-dynamic-summary.json` → `night_run.py:12,93`；`tset_matrix_user.py:8`。
4. `m13-001/m13-002-*-3600s-full.json` → `gem5se_blocked_lists_user.py:48-49`（`DEFAULT_REFS`）、
   `tset_matrix_user.py:72,74`、`three_platform_matrix.py:80-81`（join 输入）、`docs/TestReports/M13-三平台差分矩阵.md:6`。
5. `m13-005-acceptance.{json,md}`（912 K）→ `acceptance_report.py:18,547,703`（输出默认）；
   `docs/TestReports/M13-三平台差分-矩阵.md:6,113` 的**逐例明细唯一来源**。
6. `m13-002-fp-diff.{json,md}` / `m13-003-int-diff.{json,md}` → `fp_diff.py:12` / `int_diff.py:13` 输出默认。
7. `m12-016-embench-picolibc.{json,md}` → `engine_parity_report.py:14,742`（默认 out-dir = refs）、
   `engine_parity_run.sh:47-48`（硬编码输出路径）。
8. `INTEG-059t-se-parity-summary.{json,md}` → `issues.yaml` 的 `new_findings` 名单、`tset_matrix_user.py:926` 生成文本、
   `docs/TestReports/M11-三平台一致矩阵.md:443` 与 `M11-…-凡例.md:79`。
9. `m12-006-cycle-design.md` → **4 处**（`min_rom_probe_integ007t.py:5` 之外还有 `tests/arch/hmon/tiny_hmon_min.S:2`、
   `tests/ee-tiny/hmon_tiny.S:3`、`components/chipyard/…/WumingCore.scala.patch:12`）；清单只列了 1 处。
10. 另有 7 份**仅被文档引用**（非代码输入）：上 8/9 条中的 `INTEG-059t-*.{json,md}` 与 `m12-006-cycle-design.md`，
    加 `GEM5-002t-REPORT.md`（`gen_decode_table.py` docstring）、`TESTCASES-103t-timeout-recheck.md`（`issues.yaml:30`）、
    `m13-001/m13-002-*-3600s-full.md`（`docs/TestReports/M13-长尾7200s.md`）。
    账：**29 = 已删 9 + 活数据源 13 + 仅文档引用 7**。

**范围与验收互斥**：任务书「只动 7 文件」 vs 验收 #2「全仓 `grep knowledge/refs`（排除 archive/tasks/cache）= 0」——
实测非归档引用面 **31 个文件**（含 `discussing.md`/`milestones-m15.md` 两个主会话台账 ⇒ 实现面 29），现范围下 #2 不可能绿。
另有两处落点口径不在清单：`AGENTS.md:67,82`（规则真源仍写「升格 `.tao/knowledge/refs/`」）、
`tools/infra/check_knowledge_refs.py:18`。

**Q1（关键）**：上述 13 份活数据源怎么办？
- **A 迁出**：新建 `.tao/knowledge/baselines/`（或用户指定落点）后改全部消费者常量 ⇒ 档位升「中改」；
  `make check-gem5-decode` 复验需 `GEM5_SRC`，本 worktree 无 ⇒ 可能 BLOCKED，须给替代证据。
- **B 退役**：声明 gem5 B0–B7 工具链 + gem5-SE 长尾驱动退役，删代码 + 删数据（语义决策）。
- **C 保留**：refs 只删「零活引用」文件（已删 9 个），其余 20 个保留为**活数据源**，引用改写为
  「只读活数据源」措辞。
- **建议**：**C + 另立 002b**（数据迁出/工具收口，中改，含 `check-gem5-decode` 与 parity 生成器复验）。

**Q2**：`AGENTS.md:67,82` 与 `check_knowledge_refs.py:18` 的「升格 refs/」口径是否本任务同批改？（AGENTS.md 是规则真源，改它需授权）

**Q3**：`components/chipyard/…/WumingCore.scala.patch:12` 注释含 refs 路径——改注释会改补丁内容与哈希（`check-patch-tree`），是否动 patch？

**Q4**：`docs/TestReports/M11*`/`M13*` 共 5 处引用被删数据文件——是否随数据迁出同批改写？

**engineer 临时处置**：只删 9 个「非归档引用实测 = 0」的文件（授权范围内、无悬挂）；
其余 20 个与 7 条改写**未动**，等 Q1 裁定。证据：`/tmp/opencode/m15-infra-002/progress.md`（逐文件活引用面）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-18）

无代码改动（只删 9 个无引用数据文件 + 本任务书）。自审针对删除面：① 9 个文件名逐名
`git grep --fixed-strings`（排除 archive/tasks/refs/cache）⇒ 全 0；② 无目录级 `listdir`/glob 依赖
（live 代码对 refs 只有常量级 `os.path.join` 与 `MATRIX`/`DEFAULT_*` 常量）；③ 6 门控 + `compileall` 全 rc=0。
**判决**：已删部分可交付；未删/未改部分**阻塞于待裁定**（非 finding，不得据此判完成）。

## 完成区

**测试结果**：6 门控全绿（check-knowledge-refs / check-dirs / check-contracts-dir / check-no-residue /
check-test-reports / check-tests-index，各 rc=0）+ `python3 -m compileall -q tools` rc=0；**任务目标未完成**
（20/29 文件未删、7 条改写未做）。
**修改文件**：`.tao/knowledge/refs/` 下 `git rm` 9 个（清单见 `git status`）；本任务书（待裁定 + 完成区）。代码零改动。
**验收结果**（逐条，真实 rc）：
1. `ls .tao/knowledge/refs` ⇒ **目录仍存在**（20 文件 / 3.1 MB；9 个已删共释放 108 K）⇒ **未达成**。
2. `git grep knowledge/refs`（排除 archive/tasks/.cache）⇒ **31 文件**（实现面 29）⇒ **未达成**。
3. 6 门控 rc=0 ✓（删前基线同样 rc=0；日志 `/tmp/opencode/m15-infra-002/{base,after}_*.log`）。
4. `python3 -m compileall -q tools` rc=0 ✓。
5. `make check-tests-index` rc=0 ✓。
6. 注入：**未执行** —— 断言 2 的目标值（0）本身不可达，构造不出「绿→红→绿」路径。
6b. 追加跑（删后）`check-knowledge-dir`/`check-archive`/`check-run-artifacts`/`check-spec-refs` 各 rc=0；
   `make check` rc=2 —— 卡在 `check-isa-coverage`「找不到 llvm-mc」（本 worktree 无 `.work/build/llvm/bin`，
   环境前置缺失，与本次改动无关）；`check-milestones-fresh` rc=2 —— `VIOLATION: R1: m15-infra-003 有 worktree
   但未列入「进行中」/「已验证」表`（兄弟任务的台账项，归主会话，非本任务改动所致）。
7. 完成区 ≤30 行 ✓；`**状态**` 保持 `待开始`（阻塞待裁定，不写 `待验收`）。
**新发现/坑**：
- `GEM5-002t-semantic-matrix.tsv` **不是快照而是活数据源**：`gen_decode_table.py:258` 用它和
  `contracts/opcodes.yaml` 逐列互校，`refresh_matrix_notes.py` 就地刷新 `g1_note` ⇒ 「refs 全是过程快照」前提对它不成立。
- 同一基线的 `.json` 与 `.md` 引用面不同：只按 `.json` 判会把 `m13-001/002-…-3600s-full.md` 误当孤儿
  （实际被 `docs/TestReports/M13-长尾7200s.md` 引用）。
- 建议沉淀（可门控）：`.tao/knowledge/**` 下文件若被「非归档」文件引用，即标「活数据源」并拒删——
  作为清空类任务的前置检查。
**遗留问题**：见「待裁定」Q1–Q4；**20 个 refs 文件未删、7 条引用改写未做**。
