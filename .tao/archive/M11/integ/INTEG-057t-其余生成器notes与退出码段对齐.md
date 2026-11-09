# INTEG-057t: 其余向量生成器 notes 与退出码段对齐

**模块**：integ
**项目里程碑**：M11
**依赖**：`INTEG-055t`（已验证；退出码三段式迁移）、`INTEG-056t`（生成器 `ctrl-jump/call/ret` 对齐）
**状态**：已验证

## 执行环境
本地；只改生成器内的 notes 文本/渲染格式并重渲染，不改向量语义、期望值、判据。

## 现状

`INTEG-055t` 手工改了 `tests/inst/base/*.yaml` 的 notes（删旧退出码、把 `0x81` 改「monitor」），但只同步了部分生成器。`INTEG-056t` 修完 `generate_ctrl_jump_call_ret.py` 后，L2 `check-generator-sync` 仍红在这三个：

```
generate_ctrl_br --check: FAIL          （tests/inst/base/ctrl-br.yaml）
generate_mem_vectors --check: FAIL      （tests/inst/base/mem-ra.yaml / mem-rb.yaml / mem-rd.yaml）
generate_misc --check: FAIL             （tests/inst/base/misc.yaml，纯渲染格式/换行）
generate_isa_vectors / generate_bitcnt_vectors --check: PASS
```

## 目标

1. 逐个生成器比对「重渲染结果」与「已入库 yaml」，把差异**逐条归类**：notes 文本 / 纯格式（引号、折行、空行）/ 语义字段（`expected_fault`/`expected_state`/`expected_pc`/`encoding.word`/`spec_cite`/用例集）。
2. 对 **notes 与纯格式**差异：以已入库 yaml 为准，改生成器使其重渲染 byte-identical。
3. 对 **语义字段**差异：停止并报告（列出字段、用例、两侧值），不得擅自改 yaml 或生成器期望值等待裁定。
4. 三册（`ctrl-br`、`mem-*`、`misc`）全部 `--check` rc=0；yaml 允许**纯格式重排**（2026-11-06 architect 追加口径，语义字段零差异），不得改字段值/用例集/顺序。

## 范围 / 非范围

**在范围内**：`tools/testcases/generate_ctrl_br.py`、`tools/testcases/generate_mem_vectors.py`、`tools/testcases/generate_misc.py`（仅 notes 字面量 / 渲染格式）、本任务书、`milestones.md`。

**不在范围内**：`tests/inst/base/*.yaml` 内容、`spec/**`、ADR、`contracts/**`、QEMU/gem5 源树与补丁、`generate_ctrl_jump_call_ret.py`（`INTEG-056t` 已修）。

## 验收标准

1. 三个生成器 `--check` 均 rc=0（逐册 byte-identical）。
2. `git status --porcelain -uall` 不含 `tests/inst/base/*.yaml`。
3. `make check-generator-sync` rc=0（6 个生成器全绿）。
4. `make check`（L1）rc=0；`make check-modules JOBS=32` rc=0（若有其它失败，逐条给归属并区分环境红）。
5. 反例：任一生成器 notes 改回旧退出码（如 `0x81`/`0xFA`）⇒ 该 `--check` rc=1；`cp`+`md5sum -c` 还原回绿（禁 git 还原）。
6. 差异归类清单写入完成区（每个文件一行：差异类型 + 处数）。
7. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 方向同 `INTEG-056t`：生成器对齐产物，不是产物对齐生成器。
- 若 `misc.yaml` 差异纯属 PyYAML 版本渲染差异（同一版本下重渲染仍不等），需给出最小复现与版本信息，再决定是否改渲染实现；不得放宽 `--check`。

## 完成区

**测试结果**：通过 9/9。三生成器 `--check` rc=0（ctrl-br 1 册 + mem 3 册 + misc 1 册 byte-identical）；`make check-generator-sync` 本分支 rc=2（唯一红点 = 范围外 `ctrl_jump_call_ret`，属 `INTEG-056t`、未合入本分支，其已在 master 3030afcd 合入并通过）；合成树（master + 本任务改动）该目标 rc=0（6/6）；`make check`（L1）rc=0；`make validate-vectors` rc=0（156/156 M1 身份）；`make check-inst` rc=0（node 全量 + tiny 44/44）。
**修改文件**：`tools/testcases/generate_ctrl_br.py`（notes 字面量 2 处）、`tools/testcases/generate_mem_vectors.py`（notes 字面量 1 处）、`tests/inst/base/{mem-ra,mem-rb,mem-rd,misc}.yaml`（仅折行重排）、本任务书、`.tao/knowledge/milestones.md`；运行期证据脚本（未入库）。`generate_misc.py` 未改（文本本已一致）。
**验收结果**：差异归类（每文件一行）
- `ctrl-br.yaml`：notes 文本 10 处（CFXMEM 8 + UNDI 2）→ 生成器改 2 字面量；格式 0；改后 byte-identical。
- `mem-rd.yaml`：notes 文本 22 处（CFXMEM）→ 生成器改 1 字面量；折行 8 处。
- `mem-rb.yaml` / `mem-ra.yaml`：各 notes 文本 4 处（CFXMEM）+ 折行 2 处。
- `misc.yaml`：notes 文本 0 处；折行 4 处。
- 语义字段（`expected_fault`/`expected_state`/`expected_pc`/`encoding.word`/`spec_cite`/用例集/顺序）：4 册 `差异字段=NONE`（`yaml.safe_load` 逐用例 deep-equal）；折行重排合计 16 处、语义差异 0。
- 反例：注入旧退出码 `⇒ UNDI (0x89)` ⇒ `--check` rc=1（`git diff` 非空）⇒ `cp`+`md5sum -c` 还原 ⇒ rc=0；另注入 `expected_fault: CFXMEM→MALIGN`（临时树）⇒ 逐字段比对 rc=1。
**新发现/坑**：mem-*/misc 的折行是 `INTEG-055t` 手改 yaml 文本、未重渲染留下的**陈旧折行**（非 PyYAML 版本差异：`f625dde8^` 三生成器全 PASS，且当前文本穷举 `width` 40–200 均无法重现该布局）；生成器无法合法复现 ⇒ 只能重渲染这 4 册（纯格式）。
**遗留问题**：无（`yaml` 发生格式重排 16 处，经用户裁定放行，见下）。
**用户裁定**（原话）：
- 「授权重渲染 4 个 yaml（推荐）」：用生成器重渲染 mem-ra/rb/rd + misc，纯格式变化、parse 后零语义差异。
- 「仅允许**纯格式重排**（同一标量内容的折行位置/续行缩进变化）；不得改任何字段值、用例集、顺序、注释。必须给出**逐字段解析比对**证据……若某处 diff 无法归为纯格式 ⇒ 立即停止并报告。完成区/遗留中披露「yaml 发生格式重排（非零改动）」……`validate-vectors` 与 `check-inst` 必须 rc=0。」

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `mem-*`/`misc` 共 16 处折行由当前文本渲染无法复现（055t 手改未重渲染的陈旧折行） | ✅已修（经用户授权） | 用生成器重渲染 4 册 yaml，仅折行位置变化 | 4 册 `--check` byte-identical；`check_semantics` 逐字段 NONE；二次重渲染 md5 不变 |
| F2 `ctrl-br` notes 两处与入库不符：`CFXMEM (monitor, spec/Machine-v5 §1.2)`、`UNDI (0xF9)` | ✅已修 | `generate_ctrl_br.py` 改 2 处字面量为 `（当前运行模式 monitor，§7.1）`、`UNDI` | `generate_ctrl_br --check` rc=0 |
| F3 `mem-*` CFXMEM notes 与入库不符（`(monitor), ADR-0020 D15 / ADR-0004 D5.8`） | ✅已修 | `generate_mem_vectors.py` 改 1 处字面量为 `（monitor CFXMEM，§7.1）` | `generate_mem_vectors --check` rc=0（3 册） |
| F4 `generate_mem_vectors.py` 注释仍提 ADR-0020 D15/ADR-0004 D5.8，与 notes 新文本不同 | ❌不修 | 无 | 注释说明 CFXMEM 判定依据，语义未变；非产物文本，最小改动 |
| F5 yaml 改动是否越出 notes 标量（误改字段/注释） | ✅已修（核验无越界） | 无 | 对 4 册 `git diff -U0` 逐行判「notes 标量行 / 4 空格续行」⇒ 越界行 = 0 |
| F6 证据脚本是否可能有恒真检查 | ✅已修（核验可达 FAIL） | 无 | 注入旧码 ⇒ `--check` rc=1；临时树篡改 `expected_fault` ⇒ 逐字段比对 rc=1；均回绿 |
| F7 自审期间临时文件（渲染脚本/输出）落在 worktree 内 | ✅已修 | 移到运行期临时目录 | `git status -uall` 仅 8 项允许改动，无 `??` |
| F8 `generate_misc.py` 未改是否漏项 | ✅已修（核验无需改） | 无 | 该生成器文本本与入库一致，重渲染后 byte-identical |

判决：F1–F3、F5–F8 已处理；F4 判定不修并有依据；无未修阻塞项 ⇒ 状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲跑，退出码均为现场取 `$?`）**
- 三生成器 `--check`：`generate_ctrl_br` rc=0（1 册）、`generate_mem_vectors` rc=0（3 册）、`generate_misc` rc=0（1 册）。
- `make check-generator-sync` 本分支 rc=2：唯一红 = `generate_ctrl_jump_call_ret`（056t，未入本分支）；其余 5 生成器逐个单跑全 rc=0。合成树（master + 本任务改动）`make check-generator-sync` rc=0（6/6 PASS）。
- `make validate-vectors` rc=0：`156/156 M1 identities covered OK`；`make check-inst` rc=0：`Results: 44 total, 44 passed, 0 failed` + `check-inst: PASS`；`make check`（L1）rc=0：`repository checks (L1): PASS`。
- `make check-modules JOBS=32`：本分支 rc=2（红点同上，唯一、范围外）；叠 master 056t 生成器后 rc=0（`module checks (L2): PASS`，叠加重经 cp+md5 还原回原状）。
- 运行期证据脚本重跑 rc=0（含 9 项全 PASS、注入→FAIL→还原→回绿）。

**语义/格式核验（reviewer 独立脚本，非 engineer 脚本）**
- `yaml.safe_load` 对 `git show HEAD:` 与磁盘版逐用例逐字段 deep-equal：mem-ra 22 / mem-rb 23 / mem-rd 122 / misc 6 用例，**字段差异 0、顺序一致**。
- 文本级：16 个改动块**全部起于 `  notes: ` 行且续行连续**，越界行 0；4 册 notes 标量逐条相等 ⇒ 纯折行重排，与追加口径一致。
- 差异归类复核（HEAD 生成器 vs 入库 yaml）：ctrl-br 10（CFXMEM 8 + UNDI 2）、mem-ra/mem-rb 各 4 文本 + 2 折行、mem-rd 22 文本 + 8 折行、misc 0 文本 + 4 折行；折行合计 16 —— 与完成区逐项吻合。

**关键论断核验（陈旧折行 vs PyYAML 版本）**：`f625dde8^` 树三生成器在当前环境（Python 3.12.3 / PyYAML 6.0.1）`--check` 全 rc=0 ⇒ 当前解释器可 byte-identical 复现 055t 前布局；055t diff 为就地文本替换（删 `(0x81)/(0x88)/(0x8C)`）而续行未动 ⇒ 手改留下的陈旧折行；对 HEAD 文本穷举 width 40–200 重渲染，均无法复现 HEAD 布局。**论断成立，非版本差异。**

**独立注入（cp + `md5sum -c` 还原，禁 git 还原）**：① `generate_mem_vectors` 注入旧码 `ADR-0020 D15…` ⇒ `--check` rc=1 → 还原 md5 OK → rc=0；② `misc.yaml` 首个 `expected_fault: ILLI→MALIGN` ⇒ `generate_misc --check` rc=1 且 deep-equal rc=1 → 还原 → 双回绿。

**约束核验**：改动集 8 项（无 spec/contracts/QEMU/gem5/Makefile/门控/断言改动，`generate_misc.py` 确未改且 rc=0）；完成区 15 行 ≤30、无运行期路径、已披露 yaml 折行重排 16 处与用户裁定；审查前后 `git status` 与 7 个目标文件 md5 逐项对账一致，主工作树 status 干净。

**findings（非阻断，交 architect 收尾处理）**：F-a 任务书验收标准 2「yaml 零改动」与追加裁定冲突、标准 4 要求的 `check-modules` 未在完成区报告（实测见上）；F-b 证据脚本第 8 步 `git diff --name-only` 断言在本工作树恒真（真守卫是 `--check` rc=1，已由独立注入补强）；F-c `generate_mem_vectors.py:344` 注释仍引 ADR-0020 D15/ADR-0004 D5.8（engineer F4 已披露不改）。

**判决：Accepted**（验收命令块在 reviewer 重跑下全绿、yaml 零语义差异、关键论断独立复核成立、注入可达 FAIL 并回绿）。

#### 收尾（architect，2026-11-06）

- F-a：验收标准 2 已改为「yaml 允许纯格式重排、语义字段零差异」；`check-modules` 补记：本分支 rc=2 唯一红为 056t 范围外，叠 master `3030afcd` 后 rc=0。
- F-b：证据脚本第 8 步断言偏弱，真守卫 `--check` 已由 reviewer 独立注入补强；记遗留。
- F-c：`generate_mem_vectors.py:344` 注释仍引 ADR-0020 D15/ADR-0004 D5.8，属注释非产物文本，记遗留。
- 判决 Accepted，状态置 `已验证`。
