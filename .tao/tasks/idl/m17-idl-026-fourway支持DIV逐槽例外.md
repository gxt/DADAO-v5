# m17-idl-026: `idl_four_way` 支持 `expected-divergences` 的逐槽例外

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-testcases-008`（`escape_ciii_cfx` 按平台期望，同一批次）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（用户 2026-11-27 裁定 1）

Tiny 缺 `cg4`/`cg15 rc3`（`DIV-18`，用户 2026-11-26 裁定保持 M16 面）。用户 2026-11-27 裁定：**不造假常量、不跳过**，改为

- 用例在 Tiny 上验证「访问 ⇒ CFXREG」（缺失本身是被验证的行为），签名槽记录真实的 `cause_id`/`cause_info`；
- 该用例登记 `expected-divergences.yaml`，`check-idl-full` **按平台期望**判定（Tiny 用声明值，IDL/QEMU/gem5 仍按规范值并保持三方一致）。

`tests/arch/expected-divergences.yaml` 已有可选 `slots` 机制（`case` + 0 基 `slot` + `chipyard` 期望值，供 `tests/arch` 承载使用），但 `idl/tools/idl_four_way.py` **完全不读**该文件（grep `divergence` 0 命中，`m17-chipyard-002` 已核实）。

## 要做

1. `idl/tools/idl_four_way.py` 读取 `tests/arch/expected-divergences.yaml`（路径按仓库根；文件缺失/格式错 ⇒ 明确报错，不静默）：
   - 只采用与**用例镜像**匹配、且含 `slots` 的条目（`case` 取 `.S` 路径或用例 id，与现有机制一致）；
   - 对声明平台（如 `chipyard`）的对应槽：与声明值比对，**不参与**四方逐字节一致判定；
   - 对其它平台：仍按 `expected.tsv` 与该三方一致性判定（不得因例外而放宽）；
   - 例外条目**未生效**（用例未出现该差异 / 声明值不符）⇒ 判红并提示「条目应删除或值需更新」，防静默逃逸；
2. 输出与 JSON 中标注「已应用的 DIV 例外」（id + slot），便于复核；
3. 不影响未声明例外的 273 个用例（比较逻辑保持原样）；
4. 文档：`idl/docs/four-way.md` 或等价处补一段「DIV 逐槽例外如何生效/失效」。

## 不做

- 不改 HLD/QEMU/gem5/RTL/IDL 语义；不改 `expected.tsv` 槽数；
- 不改 `tests/arch` 承载（其用法不变）。

## 约束

- 独立 `git worktree`；不提交 git；只动 `idl/tools/idl_four_way.py`、`idl/docs/four-way.md`、必要时 `tests/arch/expected-divergences.yaml` 的**注释**（不改条目）、本任务书；完成区 ≤30 行。

## 验证

1. 与 `m17-testcases-008` 合并后：`make check-idl-full` **274/274**（chipyard 在 `escape_ciii_cfx` 上按 DIV 声明值判，IDL/QEMU/gem5 三方仍逐字节一致）；
2. **可达 FAIL ①**：把 DIV 声明的 `chipyard` 槽值改错 ⇒ 该例必红；还原回绿；
3. **可达 FAIL ②**：把例外条目的 `case` 改错（不匹配）⇒ 该例因四方不一致仍红（且提示条目未生效）；还原回绿；
4. 回归：其余 273 例判定不变（改动前后同一批日志逐行对比，仅新增例外输出）；
5. `git status -uall` 仅允许文件 + 任务书。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-27）

**范围**：`idl_four_way.py` 的 `load_divergences` / `div_case_matches` / `case_divergences` / `expected_problems` / `compare_case` 与 main 接线；`four-way.md §7`。
**逻辑**：声明槽仅在「实测≠其它方一致值」且「实测=声明值」时生效；无差异/值不符分别红；其它平台（含 qemu/gem5 与 expected.tsv）和其余槽位判据不变；退出码不放宽。
**fail-closed**：缺件、坏 YAML、结构错、重复登记（含 `.S` 路径与 id 别名命中同槽）、槽超界均判红或 rc=2；`--platforms qemu` 时 chipyard 例外不参与。
**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 初版「无差异」文案把实测值当声明值打印 | ✅已修 | 先判 `actual==first`，文案同时打印 declared 与 actual | run.sh `stale_entry_message` PASS |
| F2 run.sh 的 `check_has` 误要求注入路 rc=0，5 项假 FAIL | ✅已修 | 内容断言只 grep 文件，rc 仅打印 | 重跑 run.sh 27/27 PASS |
| F3 别名 `case` 可重复命中同一槽 | ✅已修 | main 启动期预跑 `case_divergences`，重复 ⇒ rc=2 | 临时 dup.yaml 实测 `ManifestError: DIV 例外重复…` |

**判决**：无未修 finding，状态→待验收。

### 第 1 轮 reviewer 复核（2026-11-27）

- **重跑**：仓库根执行运行期证据目录内的 `run.sh` ⇒ 27 PASS / 0 FAIL，`rc=0`；其中全量 IDL+QEMU `274/274`、0 条 FAIL、与改动前基线日志 `diff` 为空（仅差 EXIT 行）、DIV 文件 md5 还原一致。
- **fail-closed 单测（独立执行）**：缺件 / 坏 YAML / 缺 `divergences` / `slots` 缺 `close_when` / `scope` 平台在槽项缺值 / 槽值非整数 / 负槽 ⇒ 均 `ManifestError`；`.S` 路径与 id 别名命中同槽 ⇒ `case_divergences` 抛 `ManifestError`（`load_divergences` 单层不判重，靠主入口启动期预跑兜底，已实测）。
- **端到端 rc**：缺 DIV 文件 ⇒ `rc=2`；条目缺 `close_when` ⇒ `rc=2`，两者文案均明确；`cp` 还原后 md5 与原一致。
- **独立注入（自写包装改第 0 槽）**：临时条目生效 ⇒ `rc=0` 且输出 `DIV DIV-REV026 槽 0（0 基）`、JSON `records[].divergences` 含 id/slot/platform/declared/spec；声明值改错 ⇒ `rc=1`「声明值不符，条目值需更新」；`cp` 还原回绿 `rc=0`、md5 相等。
- **四平台抽例 3/3**（qemu,gem5,chipyard）⇒ `rc=0` 3/3；换回 HEAD 版本同参复跑 ⇒ 两份输出逐行相同（`diff` rc=0），文件已 `cp` 还原且 md5 一致（1820fcbbea…）。
- **越界**：`git status -uall` 仅 `idl/tools/idl_four_way.py`、`idl/docs/four-way.md`、本任务书；三文件 md5 与审查前快照逐项相同。
- **文档 finding（不阻断）**：`four-way.md §7` 称「匹配口径与 `tests/arch` 一致（`.S` 路径/文件名/id 均可）」，实测 `tests/arch` 只按用例 id 精确匹配 ⇒ 建议改为「四方口径比 `tests/arch` 更宽」。
- **端到端依赖**：四平台 274/274 待 `m17-testcases-008` 合入后复跑（`make check-idl-full`）；临时条目 + 包装已覆盖同一代码路径。
- **判决：Accepted**（无阻断项）。

## 完成区

**测试结果**：一键证据（运行期证据目录内 `run.sh`）= 27/27 PASS，`SCRIPT_RC=0`；全量 IDL+QEMU **274/274**，改动前后日志逐行相同。四平台 274/274 **待 `m17-testcases-008` 合入**（当前 `escape_ciii_cfx` 的 chipyard 仍 0 字节，属 008 载体范围）。
**修改文件**：`idl/tools/idl_four_way.py`、`idl/docs/four-way.md`、本任务书。
**验收结果**：
- 读文件缺失/坏 YAML ⇒ `ManifestError`（rc=2 路径），文案含「缺件」「解析失败」；`slots` 缺 `close_when`、别名重复槽同样报错。
- 生效路（临时 DIV 条目 + chipyard 包装注入真实槽差）：rc=0，输出 `DIV DIV-T026 槽 0（0 基）...`；JSON `records[].divergences` 含 id/slot/platform/declared/spec。
- 可达 FAIL①：声明值 `0xab→0xac` ⇒ rc=1 +「声明值不符，条目值需更新」；还原 ⇒ rc=0。
- 可达 FAIL②：`case` 写错 ⇒ rc=1 +「槽流不一致」+「槽 0（0 基）无生效的 DIV 逐槽例外」；还原 ⇒ rc=0。
- 附加：无差异仍留条目 ⇒ rc=1 +「条目应删除」；把声明改到槽 1 ⇒ 槽 0 仍按原判据红（声明槽外不放宽）。
- 回归：全量日志 `diff` 改动前基线 = 相同（仅多 EXIT 行）；DIV 文件 md5 还原 `4baa39a1…`、无临时条目残留。
- `git status -uall`：仅上述 3 个文件。
**新发现/坑**：`tests/arch` 的 `load_divergence_slots` 不判「无差异仍留条目」；四方按任务要求更严（实测无差异即红）。PyYAML 已是 `tests/arch` 依赖，仅复用未新增外部依赖。`case` 兼容 `.S` 路径/文件名/id，避免 008 与 `tests/arch` 两种写法冲突。
**遗留问题**：端到端 `make check-idl-full` 274/274 待 `m17-testcases-008`（Tiny 条件化 + `DIV-18.slots`）合入后复跑；本任务已用临时 DIV 条目 + chipyard 包装注入验证同一代码路径。
