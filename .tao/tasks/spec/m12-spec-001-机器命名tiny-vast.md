# m12-spec-001: 机器命名定稿 `Tiny` / `Vast`（spec + contracts + docs）

**模块**：spec
**项目里程碑**：M12
**类型**：task
**状态**：已验证

## 用户裁定（原话）

- 「同意用dadao-tiny/dadao-node」→ 后续修正为：「dadao-vast，B」
- 「ADR可以不改」「可以，授权」（spec 改名 + 同笔更新锁）「可以」（契约命令行示例）

## 目标（范围 B：profile 与机器名一次改到位）

把 `Node` 统一改名为 **`Vast`**，机器名为 `dadao-tiny` / `dadao-vast`：

1. `spec/Machine-v5-测试机运行环境.md`
   - `profile` 概念 `Tiny`/`Node` → `Tiny`/`Vast`（约 22 处，含 §1.1 表与正文）
   - 定位行里的机器名 `dadao-m1` → `dadao-tiny` / `dadao-vast`
   - 文末附录**新开 `0.4.1-rc（未发布）` 段**，条目只写「profile 与机器命名：Node→Vast、dadao-m1→dadao-tiny/dadao-vast（语义不变）」；册头状态行版本同步 `0.4.1-rc`
   - 同笔更新 `manifests/spec-readonly.lock.toml` 的 sha256
2. `.tao/contracts/contract-elf.md`（7 处）、`contract-see.md`（5 处）、`contract-syscall.md`（1 处 + 命令行示例）：`Node`→`Vast`、`-M dadao-m1`→`-M dadao-tiny`；`contract-elf` 两处 `-machine dadao-m1` 示例改 `dadao-tiny`
3. `spec/README.md`（索引措辞）、`docs/Machine-00-执行环境分层-Draft.md`（2 处）
4. **不改**：`.tao/adr/**`（历史，用户裁定不改）、历史任务书、组件 changelog、`components/**`

## 范围 / 非范围

**在范围内**：上述 spec/contracts/docs + 锁文件 + 本任务书 + `milestones-m12.md`。

**不在范围**：qemu 代码与测试（`m12-qemu-00x`）、`tests/shared/machine-profiles.yaml` 与生成 `.inc`（属 qemu-002）。

## 验收标准

1. `make check-spec-readonly` rc=0（锁与新内容一致，其余 20 册哈希不变）
2. `make check-spec-changelog` rc=0（`0.4.1-rc` 段在首、册头一致、逆序）
3. `make check-spec-drift` rc=0
4. `grep -rn 'Node' spec/Machine-v5-测试机运行环境.md` 在 profile 语境下 **0 命中**（"node" 其它语义如节点机需人工确认）；**豁免**：新开 `0.4.1-rc` 变更记录行本身（须写 `Node→Vast`）
5. `grep -rn 'dadao-m1' spec/ .tao/contracts/ docs/` 为 0；**豁免**同上（变更记录行须写 `dadao-m1→…`）
6. `make check`（L1）rc=0
7. 完成区 ≤30 行、无运行期路径

## 说明

- 这是**规范文字变更**（命名），不改变 Tiny/Vast 的几何或语义
- 只读册纪律：改册 + 锁必须同笔；授权原话已在本任务书顶部

## 完成区

**测试结果**：通过 13/13（证据脚本 full）；失败：无
**修改文件**：`spec/Machine-v5-测试机运行环境.md`、`spec/README.md`、`manifests/spec-readonly.lock.toml`、`.tao/contracts/contract-elf.md`、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-syscall.md`、`docs/Machine-00-执行环境分层-Draft.md`、`.tao/knowledge/milestones-m12.md`、本任务书
**验收结果**：
1. `make check-spec-readonly` rc=0（`21 read-only spec volume(s) OK`）
2. `make check-spec-changelog` rc=0（`files=21 segments=48 rc_segments=9`；逆序/册头/无表格/无任务号/互锁一致）
3. `make check-spec-drift` rc=0（`检查 9 个合约，排除 2 个，错误 0 个`；PASS）
4. `grep -n 'Node'` 本册：**1 命中**＝新开 `0.4.1-rc` 段改名记录行自身；记录行之外 **0**（改名 22 处现场统计：11 处 `Machine-v5-Node` + 11 处裸 `Node`）
5. `grep -rn 'dadao-m1' spec/ .tao/contracts/ docs/`：**1 命中**＝同一改名记录行；其余 **0**
6. `make check`（L1）rc=0（`repository checks (L1): PASS`）
7. 证据脚本（任务证据目录，运行期）`full` rc=0、`inject` rc=0：只读册漂移 / 变更记录乱序 / 契约回填旧机名 三类反例各自「预期 FAIL → `cp`+md5 还原 → 回绿」
**新发现/坑**：
- 验收 4/5 的「字面 0 命中」与任务书要求的条目原文（须写 `Node→Vast`、`dadao-m1→…`）互斥：改名记录行必含两个旧名 ⇒ 脚本断言改为「记录行之外 0 命中」并现场打印。若须字面 0，改该行措辞即可（一行改动，待裁定）。
- 0.4.0 附录段内 5 处 `Node` 一并改名（任务书「约 22 处」含附录；改名本身已在 `0.4.1-rc` 段记录），历史语义未变。
- `contract-syscall` 原文为通指 system 模式（两机皆适用）⇒ 命令行示例写作 `-M dadao-tiny` / `-M dadao-vast`；`contract-elf` 两处 `-machine` 示例按 Tiny 语境改 `dadao-tiny`。
- 新工作树无构建/安装树 ⇒ L1 的 `check-isa-coverage` / `check-width-sizes` / `check-builtins-freshness` 需工具前置；本任务**只读借用**主工作树的构建/安装树（符号链接）满足前置，未重建、未写产物（文档变更不影响其判据）。
- 台账行原在「待开始」，`check-milestones-fresh` 的 R1（有 worktree 却未移入「进行中」）判红 ⇒ 按「派单即移入」移入「进行中」，派单时间取 worktree 创建时刻 `2026-11-08 22:09`，待 architect 以实际派单时间校正。
**遗留问题**：无。范围外发现（未改）：`tools/testcases/arch/min_rom_probe_integ046t.py`、`build_step5_bootrom.py` 两处 docstring 仍写 `Machine-v5-Node`，不在本任务文件清单内。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

逐行核对改动前后 diff：① 22 处替换均为 profile/机器名语境，中文「完整系统节点」与 `profile=node` 未误伤；② 段落/表格/引用未断；③ 锁只改本册哈希 + 一条授权注释；④ 契约 7/5/1 处逐条对照上下文。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 验收 4/5 字面 0 命中与条目原文互斥 | ❌不修（按任务书原文，脚本改断言口径并披露） | 未改正文；脚本断言「记录行之外 0」 | `run.sh --no-l1`：Node/dadao-m1 总数各 1、残留 0 |
| F2 0.4.0 附录段历史条目被改写是否越界 | ✅已修（判定：不越界） | 无改动，仅确认「约 22 处」口径含附录 | diff：22 处全部替换，数目与任务书一致 |
| F3 `milestones-m12.md` 派单时间非主会话原值 | ⏸延后（gate 强制，值来自 worktree 创建时刻） | 移行 + 填 `2026-11-08 22:09` | `make check-milestones-fresh` rc=0 |
| F4 L1 依赖借用构建/安装树是否掩盖问题 | ❌不修（环境前置，非改动引入；已披露） | 无 | 改动前后同一前置缺失；`make check` rc=0 |
| F5 契约命令行示例机器名语境选择 | ✅已修（Tiny 语境 `dadao-tiny`；system 模式通指写两机） | 3 处示例 | 契约 grep 旧名 0；`check-spec-drift` rc=0 |

### 第 1 轮 reviewer 验收（独立重跑，判决 Accepted）

**重跑记录（我自己的输出，workdir = 任务 worktree，相对路径）**
- `make check-spec-readonly` → `check-spec-readonly: 21 read-only spec volume(s) OK`，rc=0
- `make check-spec-changelog` → `files=21 segments=48 rc_segments=9 bullets=232`，PASS，rc=0
- `make check-spec-drift` → `检查 9 个合约，排除 2 个，错误 0 个` / `spec drift check: PASS`，rc=0
- 证据脚本 full（含 L1）→ `checks=13 fails=0 RESULT: PASS` rc=0，其中 `[PASS] make check（L1） rc=0`、`repository checks (L1): PASS`
- 证据脚本 `--inject` → `checks=10 fails=0 RESULT: PASS` rc=0；A 只读册漂移 / B 记录段乱序 / C 契约回填旧机名 三例均「注入→`rc!=0`→`cp`+md5 还原→回绿」，还原 md5 与注入前逐一相同
- `grep -rn 'Node' spec/Machine-v5-测试机运行环境.md` → 仅第 274 行（0.4.1-rc 记录行自身，行内 2 处字面）；`grep -rn 'dadao-m1' spec/ .tao/contracts/ docs/` → 仅同一行 ⇒ 豁免行之外 0
- `grep -rniE 'dadao-node|\bmega\b|\bhuge\b' spec/` → 无命中（rc=1）；HEAD 本册 `Machine-v5-Node`=11、`Node` 合计=22，与完成区 11+11 一致
- 锁：`git diff` 仅 1 条 `sha256` 换值 + 5 行授权注释；21 条 `^sha256` 中其余 20 条与 HEAD 逐字相同；册实测 `f9743cd3…82493` == 锁值

**独立注入（engineer 未用的一例）**：把 `contract-see.md` 首处 `Machine-v5-Vast` 改回 `Node` → 证据脚本 `--no-l1` 打出 `[FAIL] 契约+docs+spec索引 旧名残留 expected=0 actual=1`、`checks=12 fails=1` rc=1 → `cp` 还原 md5 `ce209d69…3f3e877` 相同 → 重跑 12/12 rc=0。附带：同注入下 `check-spec-drift/spec-refs/contracts-dir/spec-purity` 仍 rc=0 ⇒ 仓库门控不查契约旧 profile 名（记录为 finding F-c）。

**现场对账**：注入前后 `git status --porcelain -uall` 快照逐行相同（9 个 M，无新增）；8 个目标文件 md5 与审查前一致；主工作树的构建树/安装树自 22:09 起 **0 个文件被改** ⇒ 符号链接只读、无产物落本 worktree（本 worktree 内仅 `__pycache__` 与 `gate.lock` 被门控产生，均 gitignore）。

**约束逐条**：①锁只动 Machine-v5 一册 ✅；②`0.4.1-rc（未发布）` 为附录首段、册头状态行 `0.4.1-rc`、段内仅 1 条且只记命名 ✅；③改名 22 处、`Node`/`dadao-m1` 豁免外 0 命中 ✅；④契约 7/5/1 处与两处 `-machine` 示例语境正确（Tiny→`dadao-tiny`、system 模式通指写两机）✅；⑤完成区 17 非空行 ≤30、全书无运行期绝对路径 ✅；⑥改动 9 文件与完成区清单逐项一致 ✅；⑦未改 `components/**`、ADR、历史任务书 ✅。

**台账越界**：engineer 将 `milestones-m12.md` 该行移入「进行中」并填派单时间 `2026-11-08 22:09`。我以 HEAD 版本回灌验证：`check-milestones-fresh` rc=2（`A1 MISMATCH` + `R1 有 worktree 但台账在「待开始」`）⇒ 该移行是 L1 绿的必需条件；但**主工作树（master，干净）已由主会话完成同一移行，时间是 `22:07`**，两版本仅差该时间戳。**处置：该行维护权属主会话；合并时以主工作树为准（保留 `22:07`），不得用本 worktree 的 `22:09` 覆盖**（我未改台账）。

**findings（均非阻断）**：F-a `docs/DDLN/D-运行平台/DD-D002-运行平台--测试机运行环境.md` 2 处 `Node` 未改且未列入遗留（超出任务书列明文件，验收 4/5 不覆盖）；F-b `tests/`、`tools/` 的旧名/旧 profile 残留属 m12-qemu/testcases 范围，仅记录；F-c 仓库门控不查契约旧 profile 名（见上）。

**判决：Accepted** —— 验收命令块在我自己的重跑下全绿、反例可达 FAIL 且已还原回绿、约束无违反；F-a/F-b/F-c 交 architect 收尾处置。

#### 收尾（architect，2026-11-08 22:25）

- 判决 **Accepted**：reviewer 自跑 `check-spec-readonly`/`check-spec-changelog`/`check-spec-drift`/L1 全 rc=0；锁 21 条中仅 Machine-v5 一条换值、其余 20 条逐字未动；自选注入（`contract-see` 回填 `Node`）⇒ 红 ⇒ `cp`+md5 还原 ⇒ 回绿。
- **台账**：以主工作树为准（`2026-11-08 22:07`），未采用 worktree 的 `22:09`。
- **F-a**：`docs/DDLN/…DD-D002` 2 处 `Node` 属讲义（非规范），不在本任务范围，转 `m12-testcases-001` 一并清扫。
- **F-b/F-c**：`tests/`、`tools/` 旧名归 `m12-testcases-001`；「门控不查契约旧 profile 名」记为遗留（证据脚本 grep 已能红，暂不新增门控）。
