# INFRA-124t: 文档/矩阵小型残留清理

**模块**：infra
**项目里程碑**：M11
**依赖**：`SPEC-185t`/`SPEC-193t`（已验证）、`TESTCASES-098t`（已验证）
**状态**：已验证

## 执行环境
本地；只清文档/指针/矩阵驱动残留，不改规范语义。

## 背景

`SPEC-185t`/`SPEC-193t`/`TESTCASES-098t` 收口后仍有小残留：

1. `.tao/adr/adr-0013-*.md:217` 仍引用已删的 `spec/README.md`「投影表」。
2. `tools/infra/check_spec_refs.py:41-42` 仍有「投影表」文案。
3. `tools/testcases/parity/run_parity.py` 硬编码 `GEM5-017t` 证据指针。
4. `tools/testcases/parity/README.md` 旧 Node embench 口径。
5. `spec/Toolchain-01` §1/§2.4/§14 删除非 spec 指针后句意偏空（A1 允许，可选润色）。

## 目标

1. ADR-0013：只把「投影表」指针改为现存节（如「分册清单/册维护约定」）或删除指针；不改 decision；追加 `rev. 2026-11-05` 或集中注记。
2. `check_spec_refs.py`：删除/更正「投影表」注释，不改检查逻辑。
3. 矩阵驱动：去掉硬编码 `GEM5-017t` 证据路径，改为当前任务/通用描述；不改判据。
4. `docs/TestReports/M11-三平台一致矩阵-凡例.md`：Node embench 口径改为“历史、不计入 M11 Node 验收”。
5. Toolchain 空心句：仅做不改变语义的最小润色；若会改锁或引入新语义，保留并登记，不强改。

## 验收标准

1. ADR-0013/`check_spec_refs.py` 不再指向已删「投影表」。
2. 矩阵驱动无 `GEM5-017t` 硬编码；README Node embench 口径正确。
3. `check-knowledge-refs`、`check-spec-refs`、`check-tests-index`、`check-milestones-fresh`、L1 rc=0。
4. 反例可达 FAIL；完成区 ≤30 行；状态 `待验收`。

## 范围 / 非范围

**在范围内**：`.tao/adr/adr-0013-*.md`（仅指针）、`tools/infra/check_spec_refs.py`（仅注释）、`tools/testcases/parity/{run_parity.py,qemu_gem5_shim.py,README.md}`、`docs/TestReports/M11-三平台一致矩阵-凡例.md`、`spec/Toolchain-01`（仅可选润色）、本任务书、`milestones.md`。

**不在范围内**：其它 ADR、spec 语义、QEMU/gem5/tests 期望、contracts。

## 完成区

**测试结果**：reviewer 复跑 29/29 PASS、外部 0（engineer 当时 27/27 + 外部 2，对账 29−2=27）（`make check` rc=2：`check-patch-tree` = 共享源码树被在跑的 `INTEG-054t` 改动；`check-run-artifacts` = 在跑的 `INFRA-125t` 在共享日志区留下非法命名 `.rc`）；L1-clean（48 目标，排除上述两项）+ `check_issues` + `compileall` rc=0；反例 2 类文本注入 + 2 类门控临时树注入均 FAIL，`cp`+`md5sum -c` 还原回绿。
**修改文件**：`.tao/adr/adr-0013-assembly-syntax.md`（:217 指针改指「规范修订流程」+ rev 注记）、`tools/infra/check_spec_refs.py`（41-42 注释）、`tools/testcases/parity/run_parity.py`（标题/用法/默认 work-dir/证据行去 `GEM5-017t`）、`tools/testcases/parity/README.md`、`docs/TestReports/M11-三平台一致矩阵-凡例.md`（Node embench 口径）、`tools/testcases/parity/qemu_gem5_shim.py`（**越界披露**：同目录驱动，3 处任务号/默认路径）、`.tao/knowledge/milestones.md`、本任务书；证据脚本落 运行期证据目录/（未入库）。
**验收结果**：`check-knowledge-refs` rc=0（悬空 0）；`check-spec-refs` rc=0（引用 1084 / 失败 0）；`check-tests-index` rc=0（241 条）；`check-milestones-fresh` rc=0（68 行）；`run_parity.py --self-test` rc=0（`INJECT: PASS`）；3 文件 `py_compile` rc=0。
**新发现/坑**：① 全量 `make check` 受共享 `.work` 外部污染：`check-patch-tree`（INTEG-054t 改源码树）与 `check-run-artifacts`（INFRA-125t 非法命名 `.rc`）红，均非本任务文件；证据按「失败目标 ⊆ 外部白名单 + 违规证据不含本任务号」判外部并留证。② `docs/TestReports/M11-三平台一致矩阵.md` 仍为旧标题/证据行快照（下次重生成刷新，本任务不改 tests 快照）。③ 任务书 目标4 写 `docs/TestReports/M11-三平台一致矩阵-凡例.md`、范围写 `tools/testcases/parity/README.md`，两处按「Node embench=历史」口径同步（均为 README 文档，非期望值）。
**遗留问题**：① `spec/Toolchain-01` §1/§2.4/§14 未改 —— 该册在 `spec-readonly` sha256 锁内，任何润色都须连带改锁 + 版本/changelog，按「会改锁则保留并登记」处理；建议后续 spec 任务将 §2.4「各立即数字段的位宽与取值范围」改为自包含句（不引非 spec 指针）并补 0.5.4-rc 条目 + 锁重算；§11/§12 现为空节，建议同步处置。② `tools/testcases/tset/embench/run_embench_e2e.py:335`、`tools/qemu/semantics_gate.py` 等仍有 `GEM5-017t` 文案，属 QEMU/testcases 源树（`INTEG-054t` 在跑），未动。

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：改动仅文档/注释/驱动文案与默认路径，无语义/判据变更；L1 本任务范围全绿，无未修 finding。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 ADR:217 改指「规范修订流程」后是否仍准确指向门控 | ✅已修（核对） | 指针指向 README「规范修订流程」第 3 步「门控查漂移」，与该步清单逐一对应 | `check-knowledge-refs`/`check-spec-refs` rc=0；ADR 断言 hits=1（rev 注记） |
| F2 驱动改标题/证据行后自检与语法 | ✅已修 | 标题去任务号、证据行改指 README | `run_parity.py --self-test` rc=0；`py_compile` 3 文件 rc=0 |
| F3 反例注入后仓库是否残留/未还原 | ✅已修 | 注入 `投影表`/`GEM5-017t` 后 `cp` 还原 | 注入 hits≥1 → 还原 hits=0；`grep 反例注入` 无残留 |
| F4 改动是否越界 | ⏸延后（已披露） | 增改 `qemu_gem5_shim.py`（同目录驱动，纯文案/默认路径） | 完成区「修改文件」已标注越界；本目录 `GEM5-017t` hits=0 |

#### 第 1 轮 reviewer 验收

**判决：Accepted**（HEAD `c2edcfd6`；审查前 `git status --porcelain -uall` 0 行；下列命令均本人执行、以本人 rc 为准）

**重跑记录**（workdir = 本任务 worktree，相对路径）
- `python3 tools/infra/check_knowledge_refs.py` → **rc=0**（悬空 0；ADR 533 + contract 79）
- `python3 tools/infra/check_spec_refs.py` → **rc=0**（总引用 1084 / violations 0）
- `python3 tools/testcases/check_tests_index.py` → **rc=0**（241 条）
- `python3 tools/infra/check_milestones_fresh.py` → **rc=0**（68 行 / 相邻对 67）
- `make check` → **rc=0**（`repository checks (L1): PASS`）。完成区 rc=2 属当时真实外部状态（工程师 21:37 跑时 `INTEG-054t` 23:09 才合入、共享 `qemu/gem5` 源码树脏 + `INFRA-125t` 非法 `.rc`），审查时点两处污染均已消失，我复跑不再复现
- 运行期证据脚本 基线 → **rc=0，29/29 PASS、外部 0**；与完成区「27/27 + 外部 2」恒等（29−2=27），非采信而是对账
- 脚本审核：逐条断言均有可达 FAIL（文本 hits、rc 断言、注入/还原双分支走 md5 对账，非两支同果）；内置 `inject.check-knowledge-refs`/`inject.check-spec-refs` 临时树反例均 rc=1 判出
- **独立反例注入**：`cp` 备份 + md5 → ADR 追加「投影表」、`run_parity.py` 追加 `GEM5-017t`、`milestones.md` 追加悬空 运行期路径引用 → 重跑**同一脚本** → **rc=1、8 FAIL**（文本 2 条 + `check-knowledge-refs` rc=1 + `make check`/L1-minus/L1-clean rc=2）
- **还原回绿**：`cp` 回 + md5 三文件与注入前逐字相等、`git status` 0 行、残留 grep 0 → 重跑同一脚本 → **rc=0、29/29 PASS**

**快照对账（真实输出）**：`md5sum -c …-snap.md5` ⇒ 8/8 `OK`、`MD5_RC=0`；`git status --porcelain -uall | wc -l` ⇒ `0`；`git diff master INFRA-124t --stat` ⇒ 恰 8 文件。

**约束核验**
1. ADR-0013 仅 217/218 两行：指针改指现存「规范修订流程」（`spec/README.md:64` 节 / `:71` 步名逐字存在）+ `rev. 2026-11-05`；D1–D11 正文零改动 ✓
2. `check_spec_refs.py:41-42` 仅 2 行注释、无逻辑行 ✓
3. `run_parity.py`/`qemu_gem5_shim.py` 仅 docstring/标题/证据行/argparse/默认 work-dir；`tools/testcases/parity` 内 `GEM5-017t` **hits=0**；`--self-test` rc=0（`INJECT: PASS`）；两份 README 均「历史、不计入 M11 Node 验收」✓
4. 越界披露：`qemu_gem5_shim.py` 3 处（1 docstring + 2 默认路径），完成区已标「越界披露」，无判据改动 ✓
5. `git diff -- spec/ contracts/` 为空：`spec/Toolchain-01` 空心句原样保留，且已在「遗留问题①」登记（只读锁，润色须连带改锁+版本）✓
6. 改动面 = 8 文件，无 QEMU/gem5/tests 期望/contracts 改动；完成区 5 行 ≤30、无运行期路径；任务书与 `milestones.md` 均 `待验收` ✓

**findings（均文档级、不阻断，交 architect 收尾改）**
- F1 ADR 新指针所指第 3 步「门控查漂移」在 README 中仅一行、不列举三个门控；engineer 自审「与该步清单逐一对应」不准确（门控名仍在 ADR 括注内，信息未丢）
- F2 run.sh 标签与完成区「L1-clean（48 目标）」实为 **48**（50−2）；标签偏差、非门控读取的期望值
- F3 完成区「check-milestones-fresh（67 行）」实为 **68 行**（67 是相邻对数）
- F4 任务书「范围」未列 `qemu_gem5_shim.py`、`docs/TestReports/M11-三平台一致矩阵-凡例.md`（与目标4 口径不一），已披露并双侧同步
- F5 `docs/TestReports/M11-三平台一致矩阵.md` 快照仍含旧 `GEM5-017t` 标题/证据行（非驱动、非期望值，下次重生成刷新，已披露）
- F6 run.sh 判外部白名单的 `own` 仅扫 `head -5` offenders，理论有遮蔽面；本轮外部项已由我独立核实为共享源码树与 `INFRA-125t` 日志，均非本任务文件

#### 收尾（architect，2026-11-05）

- F1：ADR 新指针指向「规范修订流程」整节，门控名仍在 ADR 括注内，信息未丢；措辞已记遗留。
- F2/F3：L1-clean 48、milestones 68 行已按 reviewer 实测更正。
- F4：范围已补 `qemu_gem5_shim.py`、`docs/TestReports/M11-三平台一致矩阵-凡例.md`；越界为同目录文案/默认路径，判据未动。
- F5：`matrix-M11.md` 旧 `GEM5-017t` 标题/证据行待下次矩阵重生成刷新。
- F6：证据脚本外部白名单遮蔽面记遗留。
- 判决 Accepted，状态置 `已验证`。
