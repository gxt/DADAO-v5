# INFRA-028t: 组件源文件规模规则与 size-report 工具

**模块**：infra
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

> **归属说明**：规则正文写入 `spec/Process-01-组件补丁组织与构建编排.md`（该规范本就属 **组件补丁/构建编排** 域，归 infra 维护），报告工具 `make size-report` + `tools/infra/size_report.py` 亦属 infra ⇒ 单一任务归 **infra**（不做 `k`/`m`，为普通 `t`）。编号已核对：`.tao/tasks/infra/` 最大 `027` → `028`；`.tao/tasks/spec/` 最大 `085`。

## 一、用户裁定（真源，已确认；不得增删）

1. **规则（非强制，但必须让用户知道）**：我们**新增**的组件源文件建议 **≤1000 行**；**>1000** 须**提醒用户**；**>2000** 须**考虑拆分**。
2. **判据口径**：
   - **只统计「我们新增的文件」的整文件行数**；
   - **修改上游文件只看「我们的增量行」**（`git diff <base> HEAD` 的 `+` 行数），**不以上游文件总行数计**。
3. **写入** `spec/Process-01-组件补丁组织与构建编排.md`（新增一节）。
4. **配 `make size-report`**：**仅报告、不进门控**（避免「非强制」变成阻断），列出 **>1000 行**的新增文件（含**组件 / 路径 / 行数**），并**明确提示 >2000 会建议拆分**。

## 二、实测基线（2026-10-03，供本任务引用/验收对照；**口径**：`.work/source/<c>` 现状 HEAD = base+1）

- **口径 A（我们新增，整文件行数）**：
  - `>1000` = **2**：
    - `llvm-project`：`llvm/lib/Target/DADAO/DADAOInstrInfo.td` = **1304**
    - `llvm-project`：`llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp` = **1091**
  - `>2000` = **0**
  - **逼近**：`qemu`：`target/dadao/insn_trans/trans_arith.c.inc` = **927**
- **口径 B（修改上游，只看我们的增量）**：最大增量 = **12**（`llvm-project/llvm/lib/TargetParser/Triple.cpp`）；其余 ≤3。
- 生成方式（engineer 须自行复算，不得直接采信本表）：`git -C .work/source/<c> diff --name-status <base> HEAD` 区分 `A`/`M`；`A` 取 `wc -l`，`M` 取 `git diff --numstat <base> HEAD -- <path>` 的 `+` 数。

## 三、接口规范

### 输入
- `spec/Process-01-组件补丁组织与构建编排.md`（现行 §1–§12；§10 文档约定、§11 边界情况、§12 迁移与变更记录）
- `manifests/components.lock.toml`（`component[].name`/`commit`/`enabled`、`work_root`）
- `.work/source/{llvm-project,qemu}`（现状 HEAD=base+1、clean）
- `Makefile`（`check:` 依赖行、`--help` 列表、`.PHONY`）
- 参照：`tools/infra/check_spec_drift.py`（`--repo-root` 可重定位 ROOT 的既有惯用法）、`tools/spec/check_asm_list_drift.py`（报告型工具结构）

### 输出
1. `spec/Process-01-组件补丁组织与构建编排.md`：**新增一节**「组件源文件规模约定」（内容见 §四.1）；§末变更记录追加 rev 行。
2. `tools/infra/size_report.py`：**报告型**脚本（见 §四.2）。
3. `Makefile`：新增 `.PHONY` `size-report` + 目标（**不加入 `check:` 依赖行**）+ `--help` 一行。
4. （可选）若 `spec/README.md` 投影表 `Process-01` 行 ③门控 列**列出了具体门控/工具名**，则**不**把 `size-report` 混入门控列（它是「报告」非「门控」）；如需提及，另注「报告（非门控）」。

### 约束
- 全程中文；**不提交 git**；只动任务书范围，越界须披露。
- **不改决策语义**：规则为**新增约定**，不动 `Process-01` §1–§12 既有内容与 `ADR-0002 D4`。
- **不得**把 `size-report` 并入 `make check` 的**阻断**路径（用户明示「非强制」）：`check:` 依赖行不得含 `size-report`；报告脚本默认**退出码 0**（报告型），不得让 `make check` 因它 FAIL。
- 历史台账（`changelog.md`/`deferred.md` 历史条目）、已验收任务书、`spec/SimRISC-0.5.3/` 不改。
- 临时产物 `/tmp/opencode/INFRA-028t/`；证据留 `.work/log/infra/INFRA-028t-*.log`（`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`）。
- 遵循 `AGENTS.md`「子代理硬约束」。

## 四、实施步骤

### 1. `Process-01` 新增「组件源文件规模约定」一节
内容须**逐条**含：
- **规则**：新增的组件源文件建议 **≤1000 行**；**>1000 须提醒用户**；**>2000 须考虑拆分**。**非强制**——不在 `make check` 阻断。
- **判据口径**：只统计**我们新增文件**的**整文件行数**；**修改上游文件只看我们的增量行**（不以上游文件总行数计）。
- **报告**：`make size-report`（仅报告、不阻断）列出 >1000 的新增文件（组件/路径/行数）与 >2000 的拆分提示；修改类文件报告我们的增量。
- **判读**：报告为**提示性**，是否拆分由人决定；模板/生成物可按需例外（若适用，须写明）。
- **位置/编号**：建议紧跟 §10 文档约定（作为 §11，原 §11/§12 顺延），**或**作为末节；由 engineer 据文件实际结构择一，**须**全仓 `grep -rn "Process-01 §"` 核对既有编号引用并同步（若无引用则记「无」）。§末变更记录追加 `rev. 2026-10-03（INFRA-028t）`。

### 2. `tools/infra/size_report.py`（报告型）
- 签名（建议）：`size_report.py [--repo-root DIR] [--warn 1000] [--split 2000]`；默认 `--repo-root`＝仓库根，从 `manifests/components.lock.toml` 读 `work_root`/enabled 组件与 `commit`。
- 对每个 `.work/source/<name>`（存在且可 `git`）：
  - `base = component.commit`；`git diff --name-status <base> HEAD`：
    - **`A`（新增文件）**：`wc -l` 整文件行数；列表 **> `--warn`** 者（组件/路径/行数，降序）；**> `--split`** 者标注「**建议拆分**」。
    - **`M`（修改上游）**：我们的增量 = `git diff --numstat <base> HEAD -- <path>` 的 `+` 数；**不用**上游文件总行数；报告 >`--warn` 的增量（通常为空），并打印口径 B 的**最大增量**一行以供对照。
  - 组件源缺失 ⇒ 明确打印「跳过」。
- **输出摘要**：`>1000` 计数、`>2000` 计数、逐条明细，以及固定提示行（示例）：`提示：新增文件 >1000 行须提醒用户；>2000 行建议拆分（非强制，不阻断 make check）。`
- **退出码**：始终 `0`（报告型）；参数错误/无法读 manifest 等硬错误可返回非零（但不得是「发现大文件」）。
- **不修改任何源文件/产物**（只读）。
- **`--repo-root` 必须可重定位**（供 `/tmp` fixture 反例使用）。

### 3. `Makefile`
- `.PHONY` 增 `size-report`；新增目标：
  ```
  # 组件源文件规模报告 (INFRA-028t): 仅报告（非强制），不进门控。
  size-report:
  	@$(PYTHON) tools/infra/size_report.py
  ```
- `--help` 增一行 `make size-report  Report added-component-file sizes (advisory, not a gate)`。
- **`check:` 依赖行不得含 `size-report`**。

## 五、验收标准（每项均可失败；报告须能「检出」但不得让 `make check` FAIL）

> 证据留 `.work/log/infra/INFRA-028t-*.log`；反例须可复原（fixture 优先）；`git status` 无残留。

1. **规则落位**：`grep -nE "1000|2000|建议拆分|须提醒用户|增量行|整文件行数" spec/Process-01-组件补丁组织与构建编排.md` 命中新节；新节含「非强制」「`make size-report`」「只统计新增文件整文件 / 修改文件只看增量」三项。
2. **报告正例（真实源树）**：`make size-report` → **EXIT=0**；输出列出**恰好 2 个** `>1000` 新增文件：`llvm-project … DADAOInstrInfo.td **1304**`、`llvm-project … DADAOAsmParser.cpp **1091**`；`>2000` 计数为 **0**；打印 >2000 建议拆分提示行；**口径 B** 显示最大增量 12（`Triple.cpp`）且**未**把该上游文件按总行数误报。
   - **可失败对照**：先以 `grep -c` 断言报告行数；若脚本漏列任一文件 ⇒ 断言失败（给真实输出）。
3. **报告不进门控**：`grep -n "size-report" Makefile` 命中 `.PHONY`/目标/help，**不命中** `check:` 依赖行；`make -n check \| grep size-report` 为空。
4. **检出能力（反例，fixture，不污染真实源树）**：在 `/tmp/opencode/INFRA-028t/fixture/` 造独立仓库（`manifests/components.lock.toml` + `.work/source/dummy`：base 提交 + base+1 提交，新增 `big.c` **2100 行**、`mid.c` **1100 行**，并「修改」一个上游 `upstream.c`（总 5000 行、仅 `+3` 行））：
   - `python3 tools/infra/size_report.py --repo-root <fixture>` → **EXIT=0**；
   - 列出 `big.c 2100`（标 **建议拆分**）与 `mid.c 1100`；
   - **不**列 `upstream.c`（证明「修改文件只看增量」）；
   - 给创建命令、脚本输出与还原（fixture 在 `/tmp`，无需还原真实源树）。
   - 若因环境无法建 fixture，**替代**：在**真实** `.work/source` 临时向某新增文件追加行越过 2000 → 报告列出并提示 → **还原**（恢复 base+1、clean）→ `make check-source-state` EXIT=0；给注入前后与还原证据。
5. **不误报（口径区分）**：真实源树跑 `make size-report` 输出中，**无**任何「修改上游文件」被按总行数列为 >1000（尤其 `Triple.cpp`、`TargetDataLayout.cpp`、`CMakeLists.txt` 等）；**可失败对照**：若脚本误把 `M` 文件按总行数统计，`Triple.cpp`（上游数千行）会出现在 >1000 列表 ⇒ 断言失败。
6. **`make check` 不受影响**：`make check` → **EXIT=0**（lit 25/25、`repository checks: PASS`）；加入 `size-report` 前后 `make check` 均绿 ⇒ 证明非阻断。
7. **不改决策语义/无越界**：`git diff --name-only` 仅 `spec/Process-01-…`、`tools/infra/size_report.py`、`Makefile`（+如需 `spec/README.md`）；`git diff --name-only -- components/ spec/SimRISC-0.5.3/ .tao/adr/` 为空；`Process-01` §1–§10 既有正文 `git diff` 无改动（仅新增节 + 变更记录行）。
8. **脚本只读**：跑报告后 `git status --porcelain` 无新增改动、源文件/产物 mtime 与内容不变。

## 六、下发前四项预检（主会话下发时须逐条给结论）

1. **任务书内部一致性**：✅ 裁定 4 条 ↔ 产出/验收一一对应；「非强制」↔「不进门控 + 退出码 0」一致；口径 A/B 在规则、工具、验收三处表述一致。无自相矛盾。
2. **依赖链实际可用性**：✅ 无前置任务；`.work/source/{llvm-project,qemu}` 已核实存在且 **BASE+1 且 clean**；`manifests/components.lock.toml` 可读；实测数已复现（1304/1091/927/12）。
3. **验收可执行性**：「现在可跑」全部项（工具 + `Makefile` + 文档，**无需构建**）；`make check` 全量需构建产物——**当前在位**（T3 已跑通 25/25）；缺失时 **BLOCKED**，替代证据为 `make size-report` + `grep Makefile` + fixture 反例 + `check-no-residue`。
4. **与 spec/vectors 一致**：本任务不涉及编码/期望值/向量；不读改 `contracts/opcodes.yaml`；仅统计组件源文件行数。

## 完成区
**测试结果**：`make check` **EXIT=0**（补丁 149/149、lit **25/25**、`repository checks: PASS`、`check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)`）；`make size-report` EXIT=0；fixture 反例 EXIT=0；`python3 -m compileall -q tools` EXIT=0。全部验收项通过。

**修改文件**：
- `spec/Process-01-组件补丁组织与构建编排.md`（**新增 §11「组件源文件规模约定」**；原 §11 边界情况→§12、原 §12 迁移与变更记录→§13；§13 追加 `rev. 2026-10-03（INFRA-028t）`）
- `spec/README.md`（投影表 `Process-01` 行 ③ 列附注「报告，**非门控**：`tools/infra/size_report.py`，见 §11」——不混入门控）
- `Makefile`（`.PHONY` 增 `size-report`；新增 `size-report` 目标；`--help` 增一行；**未**加入 `check:` 依赖行）
- `tools/infra/size_report.py`（**新增**，报告型）
- 本任务书（完成区/自审/状态）

**验收结果**（逐条真实命令 + 退出码，日志 `.work/log/infra/INFRA-028t-*.log`）：
1. **规则落位** `grep -nE "1000|2000|建议拆分|须提醒用户|增量行|整文件行数" spec/Process-01-…md` → 命中 §11（L169/171/172/173/174/181/182）与 §13 rev 行（L203）；三要件齐备：「非强制」（L167/174）、「`make size-report`」（L173）、「只统计新增文件整文件行数 / 修改上游文件只看我们的增量行」（L171/172）。
2. **报告正例** `make size-report` **EXIT=0**：`grep -cE '^\s+\[>1000\]'` = **2**；`DADAOInstrInfo.td  1304 行`、`DADAOAsmParser.cpp  1091 行`；`>2000 行新增文件: 0 个`；`[逼近] qemu  target/dadao/insn_trans/trans_arith.c.inc  927 行`；`口径 B 最大增量: 12 行 (llvm-project llvm/lib/TargetParser/Triple.cpp)`；`Triple.cpp` 仅出现在该对照行、**未**按上游总行数进入 >1000 列表。固定提示行 `提示：新增文件 >1000 行须提醒用户；>2000 行建议拆分（非强制，不阻断 make check）。`
3. **不进门控** `grep -n size-report Makefile` → L44（`.PHONY`）、L87（help）、L243（目标）；`check:` 依赖行（L219）**不含**；`make -n check | grep size-report` 为空（grep rc=1）。
4. **检出能力（反例 fixture，`/tmp/opencode/INFRA-028t/fixture`）**：base + base+1 提交，`big.c` 2100、`mid.c` 1100、上游 `upstream.c` 总 5003 行仅 `+3`。`python3 tools/infra/size_report.py --repo-root <fixture>` **EXIT=0**：`[>1000] dummy  big.c  2100 行  ⚠ 建议拆分`、`[>1000] dummy  mid.c  1100 行`、`[>2000] dummy  big.c  2100 行  ⚠ 建议拆分`；`grep -E '\[>1000\].*upstream\.c'` rc=1（**未**列上游文件）；`口径 B 最大增量: 3 行 (dummy upstream.c)`。创建脚本 `/tmp/opencode/INFRA-028t/make_fixture.sh`（fixture 在 `/tmp`，不污染真实源树，无需还原）。
5. **不误报** 真实源树输出中 >1000 列表仅 A 类新增文件；`Triple.cpp`/`TargetDataLayout.cpp`/`CMakeLists.txt` 等 M 类**均未**出现。**可失败对照**：`grep -q 'DADAOInstrInfo.td  9999'` rc=1、`grep -cE '^\s+\[>1000\]' | grep -qx 3` rc=1 ⇒ grep 断言能失败。
6. **`make check` 不受影响**：`make check` **EXIT=0**（lit 25/25；`repository checks: PASS`）。`size-report` 不在 `check:` 依赖 ⇒ 非阻断。
7. **不改决策语义/无越界**：`git diff --name-only` = `Makefile`、`spec/Process-01-…md`、`spec/README.md`；新增 `tools/infra/size_report.py`；`git diff --name-only -- components/ spec/SimRISC-0.5.3/ .tao/adr/` **为空**；`Process-01` diff 仅 §10 末尾之后（新增 §11、§11→§12、§12→§13 标题、§13 追加 rev 行），**§1–§10 正文无改动**。
8. **脚本只读**：跑报告前后 llvm `8354cd1f…`/qemu `9c88ac5…` HEAD 不变、两源树 `git status --porcelain` 空。

**新发现/坑**：
- `git diff --numstat <base> HEAD` **会把新增文件也列为全量 `+`**（新文件同样显示 `+N`）；区分口径 A/B **必须**先用 `git diff --name-status` 按 `A`/`M` 分类，不能只看 numstat，否则会把新增文件误当「修改上游」。
- `git diff --name-status` 的 `R`/`C` 状态行含**两个路径**（制表符分隔），解析时按 `status[0]` 归类为「其它」并跳过（对应 `Process-01` §12 待定项），避免路径解析错位。
- 全仓 `grep -rn` 会扫进 `.git/`（`COMMIT_EDITMSG` 等）且极慢（本轮一次 120s 超时）；核对 § 引用时应限定 `--include` 或排除 `.git`/`.work`。
- 建议沉淀：`size_report.py` 为**报告型**工具范式——「发现异常但退出码恒 0、不接入 `make check:` 依赖」，可在 `.tao/knowledge` 记入「报告 vs 门控」的区分（门控须能 FAIL，报告只提示）。

**遗留问题**：无（见下「自审」finding 处置）。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查 `tools/infra/size_report.py` 与 `Process-01`/`Makefile` 改动。

- **逻辑正确性**：口径 A 用 `count(b"\n")`（等价 `wc -l`，复现基线 1304/1091/927）；口径 B 用 `numstat` 首列 `+`；A/M 由 `--name-status` 分类，避免 numstat 把新文件计入增量；`head`/`base` 均取自真实 `rev-parse`/manifest。边界：manifest 缺失/解析失败→exit 2；源树缺失/非 git/commit 未锁定→打印「跳过」并继续；`other`（rename/delete 等）计数并提示未统计。**无恒真/无 FAIL 路径缺失问题**（grep 断言已验证能失败）。
- **设计/惯用法**：`--repo-root` 可重定位（fixture 已验证）；`subprocess.run(capture_output=True)` 无 shell 注入；`tomllib`、`parents[2]` 与既有 `status.py`/`check_spec_drift.py` 一致；报告型退出码恒 0 与「不进门控」一致。
- **防造假**：所有输出取自真实命令，日志留 `.work/log/infra/`；fixture 为独立仓库、可复现。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1：非 git 目录会误报「无法读取 HEAD」 | ✅已修 | `scan_component` 改判 `rev-parse --git-dir` 的 `returncode`，非仓库直接打印「非 git 仓库」 | 改后 `make size-report` EXIT=0、`grep -cE '^\s+\[>1000\]'`=2；fixture EXIT=0；`compileall` EXIT=0 |
| F2：接受项 4「不列 upstream.c」与口径 B 最大增量行会点名 upstream.c 是否冲突 | ❌不修（设计如此） | — | 任务书 §四.2 明确要求「打印口径 B 的最大增量一行」；fixture 中 `grep -E '\[>1000\].*upstream\.c'` rc=1，证明未按 5003 总行数误列 |
| F3：逼近带取 `warn-100` 而非硬编码 900 | ✅保留 | — | 默认 `--warn=1000` ⇒ 逼近带 900–1000，`927` 命中；`--warn` 仅脚本级、不入 Makefile（裁定 2） |

**判决**：finding 均已处置（F1 已修、F2 设计如此有证据、F3 保留），状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**判决：Accepted**

**重跑证据摘要**（全部由 reviewer 独立执行，日志 `/tmp/opencode/INFRA-028t-review/`）：

| 验收项 | 命令 | 真实输出/退出码 |
|--------|------|-----------------|
| 报告正确性 | `make size-report` | **EXIT=0**；>1000=2：`DADAOInstrInfo.td 1304`、`DADAOAsmParser.cpp 1091`；逼近 `trans_arith.c.inc 927`；>2000=0；口径 B 最大增量=12（`Triple.cpp`） |
| 不误报 | `grep -E '\[>1000\].*Triple\.cpp' size-report.log` | rc=1（未按上游总行数误列） |
| 不进门控 | `make -n check \| grep size-report` | 空（grep rc=1） |
| 不进门控 | `check:` 依赖行（L219） | 不含 `size-report` |
| make check | `make check` | **EXIT=0**；lit 25/25；`repository checks: PASS` |
| compileall | `python3 -m compileall -q tools` | **EXIT=0** |
| check-no-residue | `make check-no-residue` | **EXIT=0** |
| 反例 fixture | `--repo-root /tmp/…/fixture`（big.c=2100, mid.c=1100, upstream.c=5003/+3） | **EXIT=0**；big.c 标⚠建议拆分；mid.c=1100 列出；upstream.c **未**误列（grep rc=1）；口径 B=3(upstream.c) |
| §重编号 | `grep -n "Process-01 §" tools/*.py` | `size_report.py` → §12（正确）；`make_patch.py` → §6.3（未受影响） |
| 投影表 | `grep "Process-01" spec/README.md` | L81 标注「报告，**非门控**：`tools/infra/size_report.py`，见 §11」 |
| 只读 | 两源树 `git status --porcelain` | 空；HEAD 不变（llvm=8354cd1f, qemu=9c88ac5） |
| 无越界 | `git diff --name-only -- components/ spec/SimRISC-0.5.3/ .tao/adr/` | 空；§1–§10 零改动 |
| 断言可失败 | `grep -cE '^\s+\[>1000\]' … \| grep -qx 3` | rc=1（注入错值后能失败） |

**约束核验**：规则落位（§11 三项要件齐备）、非门控（`check:` 不含、`make check` 不因它 FAIL）、报告数字对齐（1304/1091/927/12）、反例检出（2100⚠/1100/上游不误列）、§重编号无破引用、只读、无越界——全部通过。

## 收尾与提交（用户裁定，2026-10-03）
- **执行期不提交**：engineer/reviewer 子代理**不得** `git commit`/`git add`。
- **收尾后提交一次**：本任务经 `/complete` 通过、`**状态**` 置为 `已验证` 后，**主会话**为该任务做一次独立提交；**未收尾不得提交**。
- 提交前满足项目 `AGENTS.md`「任务收尾」的收尾检查。

## 开放问题（只列不决）
1. **报告呈现的「逼近」带**：是否在报告中加一档「900–1000（逼近）」提示（如 `trans_arith.c.inc` 927）？默认**不加**，仅列 >1000。
2. **阈值可配置**：`--warn`/`--split` 默认 1000/2000；是否需要 `Makefile` 变量覆盖（如 `SIZE_WARN=`）——默认不加。
3. **口径 B 的报告粒度**：是否也要列「增量 >1000 的修改文件」（当前无实例）；默认只打印「最大增量」对照行。
4. **新节编号/位置**：§11（原 §11/§12 顺延）vs 末节——由 engineer 据文件结构定（须核对既有编号引用）。
5. **模板/生成物例外**：如生成器产物（若将来纳入组件树）是否豁免 1000 行规则——默认按普通新增文件计，必要时再议。
