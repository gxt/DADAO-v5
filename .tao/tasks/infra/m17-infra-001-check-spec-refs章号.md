# m17-infra-001: `check-spec-refs` 校验标题型引用的章号（ISS-447）

**模块**：infra
**项目里程碑**：M17
**依赖**：无
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

`ISS-447`：`check-spec-refs` 对**标题型引用**（如 `[SimRISC-00 §5.1 标题]`）只剥前导章号后比标题文本，**不校验章号**——把 `§5.1` 改成 `§9.9` 仍 rc=0（`m13-spec-011` 复核实测）。这让「章号写错」这类漂移漏网。

## 要做

1. `tools/infra/check_spec_refs.py`：标题型引用的 `§N[.M[.K]]` 与标题文本**同时**校验——章号必须指向该册中标题文本所在的那个节；章号与标题不匹配 ⇒ FAIL（指名文件/行/引用/实际节号）；
2. 保留现有「非标题型引用」行为；对无法判定的形态（跨册、范围、附录字母）维持既有跳过并**打印跳过原因**（不静默）；
3. `--self-test` 增两类注入：标题正确但章号错 ⇒ FAIL；章号对但标题错 ⇒ FAIL；还原后 PASS；
4. `docs/Process-07` 中 `check-spec-refs` 行补一句「标题型引用同时校章号」。

## 不做

- 不批量修现有引用（若门控收紧后暴露存量错误，逐条列出交主会话，不在本任务顺手改内容）；
- 不改 spec 正文。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；只动 `tools/infra/check_spec_refs.py`、`docs/Process-07`、本任务书；完成区 ≤30 行。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-spec-refs` rc=0（若暴露存量错误，逐条列清单并说明本任务不修）；
2. `--self-test` 全过；
3. **可达 FAIL 2 路**（真注入）：改一处标题型引用的章号（如 `contract-isa` 里 `[SimRISC-00 §5.1 …]` → `§9.9`）⇒ rc≠0 并指名；改标题文本一字 ⇒ rc≠0；均 `cp`+md5 还原后回绿；
4. `check-spec-refs` 的扫描面与跳过项计数现场派生。

## 完成区

**测试结果**：运行期证据目录内的 `run.sh` 29/29 通过（rc=0）；`make check-spec-refs` rc=0（引用 1381 / 失败 0）；`--self-test` 5/5；`check_spec_refs_selftest.py` 8/8。
**修改文件**：`tools/infra/check_spec_refs.py`（任务书写 `tools/spec/…`，实际路径为 `tools/infra/`，`make` 目标即引此）、`docs/Process-07-门控分层规范.md`（`check-spec-refs` 行）、本任务书。
**验收结果**：
- 实现：`_header_matches` 在引用带章号（`N[.M[.K]] `）时要求章号 == 标题所在节编号，标题文本一致也不能兜底；`chapter_mismatch_hint` 报「引用 §N，标题「…」实际位于 §M」。
- 基线无存量错误：收紧前后命中统计一致（标题 1368 / 粗体 10 / 正文 0 / 失败 0）⇒ 无需另立改正文任务。
- 真注入 A（`contract-syscall.md:120` `§3.1 指令域说明`→`§9.9`）：rc=1，输出 `章号与标题不匹配: 引用 §9.9，标题「指令域说明」实际位于 §3.1`；旧版（HEAD）同一注入 rc=0（证明为新增能力）；`cp`+md5 还原后 rc=0。
- 真注入 B（同处标题改 `指令域说明X`，章号对）：rc=1，输出 `节标题未找到` 并指名该引用；还原后 rc=0。
- 跳过项：3 处模板占位，摘要打印「跳过原因: 格式占位，非真实引用」；引用/跳过/违规条数均现场派生。
**新发现/坑**：① 任务书路径 `tools/spec/check_spec_refs.py` 不存在，实为 `tools/infra/check_spec_refs.py`；② 该脚本原本无 `--self-test`，本轮内新增（合成 fixture 用 `tempfile.mkdtemp()` 建、用后自清理，仓库脚本不含运行期路径），未改 `tools/spec/check_spec_refs_selftest.py`（不在允许文件集）；③ 收紧后「父节号+子节标题」（如 `§2.2 普通页的地址转换` 实际在 2.2.2）会 FAIL，存量无此形态。
**遗留问题**：无。

## 审阅记录

### 第 1 轮 engineer 自审

**判决**：通过（无未修 finding）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书要求 `--self-test` 两类注入，脚本原无该选项 | ✅已修 | 新增 `self_test()`：合成 fixture 基线 PASS → 章号错 FAIL → 还原 PASS → 标题错 FAIL → 还原 PASS | `--self-test` rc=0（5/5） |
| F2 章号不符须指名「实际节号」 | ✅已修 | 新增 `_heading_numbers_with_title`/`chapter_mismatch_hint`，violation reason 改为具体提示 | 注入 A 输出 `实际位于 §3.1` |
| F3 跳过项不得静默 | ✅已修 | 摘要行改为「跳过原因: 格式占位，非真实引用」，计数现场派生 | `run.sh` 断言「跳过原因行存在」 |
| F4 收紧可能误伤非编号/占位/父节号形态 | ✅已核验 | 仅当引用带 `N[.M[.K]] ` 才约束章号；占位 `[A-Za-z]+` 仍跳过 | matcher-selftest 8/8；基线 1381 引用失败 0 |
| F5 还原不得用 `git checkout`/`restore` | ✅已核验 | `run.sh` 用 `cp -p` + md5 对账；结尾断言注入目标不在 `git diff` 改动集 | md5 三次一致、目标不在改动集 |

### 第 1 轮 reviewer 复核

**重跑（reviewer 亲自执行，退出码均为实测）**
- 运行期证据目录内 `run.sh`：`rc=0`，`run.sh: PASS（0 项失败）`，29 项断言全 `[OK]`（含注入 A/B 的 rc、指名行、还原 md5、改动集⊆允许集）。
- `make check-spec-refs`：`rc=0`；总引用 1381 / 失败 0 / 命中 标题=1368 粗体=10 正文=0 / 跳过 3（打印「跳过原因: 格式占位」）。
- `python3 tools/infra/check_spec_refs.py --self-test`：`rc=0`，5/5（基线 PASS→章号错 FAIL→还原→标题错 FAIL→还原）。
- `python3 tools/spec/check_spec_refs_selftest.py`：`rc=0`，8/8。

**独立注入（换文件 `contract-tlb.md`，未复用工程两路；`cp`+md5 备份/还原）**
- 章号 `§4.5 cfx_ptw…`→`§9.9`：`rc=1`，报「章号与标题不匹配: 引用 §9.9，标题「cfx_ptw - page table walker」实际位于 §4.5」；**HEAD 版同一注入 `rc=0`**；还原（md5 `282dfb33…` 一致）后 `rc=0`。
- 标题改 `…walkerZ`：`rc=1`，报「节标题未找到」；还原后 `rc=0`。
- 全量扫描面注入：在册前缀 269 处标题型引用章号全改 `§99.9` ⇒ **269/269 全部 FAIL**（原因 269 条全为章号不匹配、0 条漏网）。

**约束核验**：改动集 = 3 文件（`tools/infra/check_spec_refs.py`、`docs/Process-07-门控分层规范.md`、本任务书），与完成区声明一致，快照对账 `SNAPSHOT_MATCH`；`spec/` 正文与 `tools/spec/check_spec_refs_selftest.py` 未改；`Process-07` 行已补「标题型引用同时校章号」；diff 无弱化既有断言。

| finding | 判定 | 说明 |
|---|---|---|
| F1 `--self-test` 把运行期临时目录绝对路径（含任务 ID）硬编码进仓库脚本 | 非阻断 | 建议改用 `tempfile` 默认目录（行为正确，仅可移植性欠佳） |
| F2 完成区写了具体临时目录路径 | 非阻断 | 记录用语应写「运行期证据目录」，由 architect 收尾改 |
| F3 `[Kaiwu §…]` 前缀不在 `_PREFIX_ANCHOR`（存量范围缺口，HEAD 同） | 非阻断·存量 | 与本任务无关，建议另立任务评估 |
| F4 `make check` rc=2 卡 `check-isa-coverage`「找不到 llvm-mc」；`check-knowledge-refs` 红（`m19-infra-001` 任务书 3 处具体 `.work` 路径引用） | 环境/他任务基线红 | 与本改动无因果（本改动仅 3 文件），均非本任务引入 |

**判决：Accepted**（阻断项：无）


### 第 2 轮 engineer 自审（reviewer 收尾项）

**判决**：通过（两条收尾项已修，状态保持 `待验收`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 `--self-test` 硬编码运行期绝对路径 | ✅已修 | 删 `_SELFTEST_ROOT`，改 `tempfile.mkdtemp(prefix="check-spec-refs-selftest-")`（临时根由 `tempfile` 自选），`finally` 仍 `rmtree` | 脚本内已无运行期路径字面量；`--self-test` 5/5 rc=0；临时目录残留 0 |
| R2 完成区含具体临时目录路径 | ✅已修 | 「测试结果」改「运行期证据目录内的 `run.sh`」；「新发现」改述 `tempfile.mkdtemp()` 建用后清理 | 任务书内已无运行期路径字面量；完成区 14 行 |
