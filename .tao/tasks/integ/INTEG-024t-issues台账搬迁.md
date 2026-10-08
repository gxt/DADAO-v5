# INTEG-024t: issues 台账搬迁（规划 / 阻塞 / 待裁定 → `milestones.md`）

**模块**：integ
**项目里程碑**：M6
**依赖**：`INTEG-022t`（M5 归档与回顾，`已验证`；`milestones.md` 已定位为「当前进度」载体）；无硬前置
**状态**：已验证

> **本任务性质（务必先读）**：**只做「分流」**——把 `issues.yaml` 中属「规划 / 阻塞 / 待裁定」的条目**移入** `milestones.md`（用户 2026-10-08 定位其为「当前进度」载体），`issues.yaml` 只保留**真正的 issue**（缺陷 / 欠账 / 技术债）。**不改任何条目的归属结论、不 close、不裁决**（归属未定者**原样**搬去 `milestones.md` 的「待裁定」列表，**并给用户选项**）。
> **与 `Process-04 §3` 的关系**：`§3` 是**归档前置**的台账梳理（含 close / scope 校正 / 边界拆分）；本任务**不是**归档前置，**不重复** `§3` 的裁决动作，只新增「按性质分流」这一步。若发现某条目同时命中 `§3` 动作（如已消解仍 `open`），**登记提请**、**不由本任务擅自处置**。

---

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/knowledge/issues.yaml`（**现状实测 2026-10-08**：`39 open / 0 closed`，`tools/infra/check_issues.py` EXIT=0）。
  - `.tao/knowledge/milestones.md`（现 16 行；「当前进度」下已有 `- **规划中**：…` 与 `- **阻塞与待裁定**：…` 两条**列表**；**用户 2026-10-08 定位其为「当前进度」载体**：规划中 / 阻塞与待裁定**列表**）。
  - 用户 2026-10-08 指示（**原话，逐字**）：
    > 「issues中的很多内容都属于规划或阻塞或待裁定的，可以移动到该文件中，而不要留在issues里，至少不必重复记录；这个可以作为一个单独的任务来处理；」
  - 门控：`tools/infra/check_issues.py`（∈ `make check`；**EXIT 0** 是硬约束）。
  - 先例体例：`.tao/archive/M5/integ/INTEG-022t-M5归档与回顾.md`（`Process-04 §3` 台账梳理的**逐条判定表**写法；本任务沿用其「id → 动作 + 依据」的表格体例，但**动作集不同**——本任务只有「移出 / 保留」两种）。
- **输出**：
  1. `.tao/knowledge/milestones.md`：
     - 「当前进度」下新增/扩写**两条列表**（**沿用现体例：列表，不用表格**）：
       - **`- **规划中**：…`**——承载**属「规划」**（判据 ①）的移出项；
       - **`- **阻塞与待裁定**：…`**——承载**属「阻塞」或「待裁定」**（判据 ②③）的移出项。
     - 每个移出项以**子列表项**列出：`**id**`（**原 scope 原样括注**）+ 一句话事实 + 依据指针（任务书/notes/ADR）+（属「待裁定」者）**用户选项**。
  2. `.tao/knowledge/issues.yaml`：
     - **删除**所有移出项（**整条移除**）；
     - **只保留真 issue**（判据 ④）；
     - 文件头注释新增说明：「**原 `ISS-xxx`（规划/阻塞/待裁定）已迁 `.tao/knowledge/milestones.md`；`id` 不复用**」+ 迁出 id 清单（可追溯）。
  3. 本任务书「完成区」：**逐条判定表**（`id → 类别 → 动作〔移出/保留〕→ 依据`，覆盖 `issues.yaml` **全部现存 open 条目**）+ `check_issues.py` 真实输出 + 「不重复记录」机械检查的真实输出 + 迁出/保留计数对账。
- **约束**：见「硬约束」。

## 判据（分流口径，须逐条给依据）

> **四类判据**（一次判定给一个主类别；**语义判定须逐条给依据**，见「机械可核项」）：

| 类别 | 判据 | 动作 |
|---|---|---|
| ① **规划** | **未开始的能力 / 里程碑待办**（尚不存在的功能、明确挂在某里程碑的待办；不含「已实现但有缺陷」） | **移出** → `milestones.md`「规划中」 |
| ② **阻塞** | **当前无法推进且已指明依赖**（如「须用户授权方可收口」「须某能力先实现才能补验」） | **移出** → `milestones.md`「阻塞与待裁定」 |
| ③ **待裁定** | **等用户 / 决策才能动**（归属里程碑未定、须用户选方案、须用户授权） | **移出** → `milestones.md`「阻塞与待裁定」+ **给用户选项** |
| ④ **真 issue** | **缺陷（defect）、欠账（debt）、技术债（tech-debt）**——已实现物上的错误 / 遗留 / 待修项 | **保留** 在 `issues.yaml` |

- **②与③可重叠**（如「须授权方可收口 ⇒ 既阻塞又待裁定」）⇒ 归 `milestones.md`「阻塞与待裁定」同一列表即可，**不必强行二分**。
- **①与④的边界**：某功能**完全未实现且挂在里程碑** ⇒ ①；某功能**已实现但存缺陷 / 遗留**（如 reloc 类型落错、诊断枚举隐患）⇒ ④。
- **「归属存疑」项**（现 `issues.yaml` 标「待裁定」者）⇒ **一律 ③**，**原样**移出并**给用户选项**；**不得**由本任务裁定其归属 / 是否关闭。

### 机械可核项（须在完成区给真实输出）

1. **`check_issues.py` EXIT 0**（`issues.yaml` 仍是合法 list、字段合法）。
2. **id 不复用**：迁出的 `ISS-*` id **不得**出现在 `issues.yaml` 的新条目里（`grep -n 'id: ISS-<n>' issues.yaml` 对每个迁出 id → 无命中）；也不得改写既有条目 id。
3. **不重复记录**（核心验收）：**同一 id** 与**同一事项**（标题/主题）**不同时**出现在两文件：
   - `grep -F 'ISS-<n>'` 在两个文件中不同时命中（迁出 id 只在 `milestones.md` 命中一次）；
   - 真 issue 的 id 只在 `issues.yaml` 命中；
   - 对「事项」级：迁出项的**标题关键词**不得在 `issues.yaml` 残留同义条目（逐条比对，非抽样）。
4. **迁出 / 保留计数对账**：`39 = 移出数 + 保留数`；且 `issues.yaml` 剩余 open 数 == 保留数（`check_issues.py` 输出核对）。

## M6 参考：`milestones.md` 落点体例（示例，**内容以逐条判定为准**）

> **示例仅示**「列表体例 + 字段」，**不预设**具体条目；最终以「完成区逐条判定表」为准。

```markdown
## 当前进度
- **里程碑**：M6（`INTEG-023k`「M6 启动与分解」）
- **规划中**（M6 待办；**原 `issues.yaml` 移入**）：
  - `ISS-xxx`（原 `[M6]`）：<一句话事实> —— <依据/归属>
- **阻塞与待裁定**（**原 `issues.yaml` 移入**）：
  - `ISS-yyy`（原 `[spec, M5]`）：<一句话事实> —— **待用户裁定**；选项 A <…> / B <…> / C <…>
```

## 判据起点（**实测基线，工程师须逐条复核后出最终表**；不预设动作）

> **实测 2026-10-08**：`issues.yaml` = `39 open / 0 closed`。以下为**建议起点**（供核对，**非结论**）；**标注「存疑」者**与**全部「待裁定」项**须给用户选项、不擅自定。

**建议 ① 规划（M6 待办 / 未开始能力；`scope` 已含 `M6`）**：
`ISS-003`（LR-SC 原子，`SimRISC-12` `lr_*`/`sc_*` 未实现）、`ISS-005`（完整调用约定未交付部分）、`ISS-006`（ABI 5 项 `[OPEN]`）、`ISS-110`（`cfxld`/`cfxst` + `crii` + `SPEC-075t` 别名缺口）、`ISS-165`（RAM@0 C1 step2 迁移）、`ISS-168`（「`-bios`+ELF」组合加载 / ELF loader 扩 RAM@0 / 组合 ADR）、`ISS-169`（6 个 M1/M2 探针 `exit-port` → `SYS_EXIT` 迁移）。

**建议 ③ 待裁定（归属存疑 8 项；现均 `open` 且 `scope` 含已达成 `M5` ⇒ 亦属「`scope` 悬挂」）**：
`ISS-019`、`ISS-026`、`ISS-047`、`ISS-074`、`ISS-081`、`ISS-163`、`ISS-164`、`ISS-167`。
- 其中 `ISS-163`/`ISS-167` **须用户授权**方可收口上游只读册 ⇒ 亦可归 **② 阻塞**；本任务**不裁定**，归入「阻塞与待裁定」列表 + 给选项即可。
- `ISS-047` **存疑**：`llvm-objdump` 的 `e_machine` 未映射——**已实现物上的缺陷**（④）**抑或**「LLVM 工具待办」（①）？⇒ 请给用户选项。

**建议 ④ 真 issue（保留 `issues.yaml`）**：
`ISS-043`、`ISS-045`、`ISS-054`、`ISS-058`、`ISS-064`、`ISS-078`、`ISS-090`、`ISS-093`、`ISS-098`、`ISS-102`、`ISS-108`、`ISS-118`、`ISS-120`、`ISS-125`、`ISS-126`、`ISS-138`、`ISS-148`、`ISS-151`、`ISS-154`、`ISS-156`、`ISS-159`、`ISS-160`、`ISS-161`、`ISS-162`。
- **存疑项**：`ISS-126`（FP 开放点固定取值，供 GOLDEN 参照——④ spec 欠账 抑或 ① GOLDEN 待办？）、`ISS-138`（`>128K` 帧未实现——① 未开始能力 抑或 ④ llvm 欠账？）、`ISS-156`（`set.fo rf,0` 口径不一——④ 待核缺陷）。⇒ 逐条给依据；若判为「须决策才能动」则改归 ③ + 给选项。

## 硬约束

- **`id` 不复用**：迁出的 `ISS-*` id **不重用**（`issues.yaml` 头部须如实说明「原 `ISS-xxx` 已迁 `milestones.md`」）；**不改写**既有条目 id 或标题。
- **`check_issues.py` EXIT 0**（硬性）。
- **禁改 `spec/`**（`spec/Process-06` + 用户裁定）：本任务**不需要**改任何 `spec/` 册；`git diff --name-only | grep -E '^spec/'` **必须为空**。若发现必须改 ⇒ **停下报告**（须用户事先授权）。
- **任一「待裁定」项须给用户选项**（**不擅自定**）：在 `milestones.md` 列出选项（如 `ISS-019`：A 归 M6「欠账收口」/ B 另立 golden 里程碑 / C 保留待规划），并**提请用户裁定**。
- **禁改其它台账语义**：不改 `lessons.md`、不改各条目的 `resolved_by`、不做「关闭 / 边界拆分 / scope 归属」裁决（这些属 `Process-04 §3`，非本任务）。
- **`scope` 悬挂校正（父项指明，一并做）**：`M5` 已达成、已归档；open issue 的 `scope` 仍含 `M5`（现 8 条）属**悬挂引用**。本任务**移出**这 8 条 ⇒ 悬挂自然消解；`issues.yaml` 头部 `scope` 枚举同步注明 `M5 = 已达成（不再作 open 项 scope）`；若**移出后**仍有保留项含悬挂值，须逐条说明理由。
- **无残留 / 无断行**：改动后 `milestones.md`、`issues.yaml` 无表内空行、无连续空行、文件尾单换行；`issues.yaml` 每个条目字段合法。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **临时目录 `/tmp/opencode/INTEG-024t/`**；日志/证据留 `.work/log/integ/`、`.work/evidence/`（`.work/` 已 gitignore）。
- **失败即停、禁自动重试**；**完成区与真实输出逐条对齐**；命令留证**须捕获被检命令自身退出码**（**禁** `cmd | tee log; echo $?`）。
- **不跑 `make`**（`check_issues.py` 直接 `python3` 调用即可；改动仅 `.tao/knowledge/**`，属纯台账/文档，可豁免 `make check` 并说明）。
- **一键证据脚本** `.work/evidence/INTEG-024t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。

## 验收标准

1. **逐条判定表**：完成区含覆盖 **`issues.yaml` 全部现存 open 条目（39 条）** 的 `id → 类别 → 动作 + 依据`；**无遗漏、无凭空新增**。
2. **搬迁完成**：所有判为 ①②③ 的条目**已从 `issues.yaml` 删除**、**已在 `milestones.md` 以列表承载**（体例一致、非表格）；所有判为 ④ 的条目**原样保留**。
3. **机械检查**（给真实输出）：`check_issues.py` **EXIT 0**；**id 不复用**（迁出 id 在 `issues.yaml` 无命中）；**不重复记录**（迁出 id 只在 `milestones.md` 一次命中；真 issue id 只在 `issues.yaml` 命中；事项级逐条比对无重复）；**计数对账** `39 = 移出 + 保留`。
4. **待裁定项有选项**：每条 ③ 项在 `milestones.md` 列出**用户选项**，并**提请用户裁定**（不擅自定）。
5. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出（`git status --porcelain -uall` 亦不遗留）。
6. **`issues.yaml` 头部说明**：含「原 `ISS-xxx` 已迁 `milestones.md`」+ 迁出 id 清单 + 「id 不复用」。
7. **无残留**：`git status --porcelain -uall` 仅含 `.tao/knowledge/{issues.yaml,milestones.md}` + 本任务书；无 `*_tmp*`/`*.orig`/`*.rej`/`*.preinject`。

## 完成区

> 说明：本任务书**验收标准 1** 要求完成区含「覆盖全部 39 条 open 的逐条判定表」，故完成区**超**通用 ≤30 行限长（该表为任务显式产出，非注水）；明细表亦留 `.work/log/integ/INTEG-024t-逐条判定表.md`。

**测试结果**：
- `python3 tools/infra/check_issues.py` → **EXIT=0**；`check_issues: 24 open, 0 closed (0 blocking M1-gate: 0)`。
- 一键证据脚本 `bash .work/evidence/INTEG-024t/run.sh` → **SCRIPT_EXIT=0**（`ALL PASS`；含注入→FAIL→`cp`+md5→回绿）。日志 `.work/log/integ/INTEG-024t-evidence-run.log`。
- **计数对账（实测）**：迁移前 open **39** = **移出 15**（①规划 7 + ②③阻塞/待裁定 8）+ **保留 24**（④真 issue）；迁移后 `issues.yaml` open **24** == 保留数。实测数与任务书「39」一致。
- **不重复记录（机械）**：迁出 id 作为 `issues.yaml` 条目 **0 命中**；迁出项**标题**在 `issues.yaml` **0 命中**；保留 id 在 `milestones.md` **0 命中**；迁出 id 在 `milestones.md` 全命中（**0 漏**）。
- **门控**：纯 `.tao` 台账改动 ⇒ 按 `AGENTS.md` 豁免 `make check`（**未跑 `make`**，后台 LLVM 长构建勿扰）。

**修改文件**：
- `.tao/knowledge/issues.yaml`：删 15 条移出项；头部加「台账性质分流」说明 + 迁出 id 清单 + 「`id` 不复用」+ `M5` scope 枚举注「不再作 open 项 scope」；**未改**任何保留条目字段（逐条比对与 HEAD 字节一致）。
- `.tao/knowledge/milestones.md`：「当前进度」两条列表**新增**子项（规划中 7、阻塞与待裁定 8〔含量化**用户选项**〕）；**既有条目与任务流水行原样保留**（纯新增，diff 无删除行）。
- `.tao/tasks/integ/INTEG-024t-issues台账搬迁.md`（本任务书：完成区 + 状态）。
- 证据/脚本（`.work/`，gitignored）：`.work/evidence/INTEG-024t/{run.sh,verify.py,moved_items.tsv}`、`.work/INTEG-024t/edit_issues.py`、`.work/log/integ/INTEG-024t-{evidence-run.log,逐条判定表.md}`。

**验收结果（逐条判定表；覆盖迁移前 39 条 open）**：

| id | 类别 | 动作 | 依据 |
|---|---|---|---|
| ISS-003 | ①规划 | 移出→规划中 | LR-SC 原子（`SimRISC-12` ISA 扩展整体 deferred；M6 显式排除） |
| ISS-005 | ①规划 | 移出→规划中 | 完整调用约定未交付部分；M6 主题显式含 |
| ISS-006 | ①规划 | 移出→规划中 | ABI 5 项 `[OPEN]`；M6 待办（`contract-abi.md §6`） |
| ISS-110 | ①规划 | 移出→规划中 | `cfxld`/`cfxst`+`crii`+别名缺口（MC 未实现）；M6 待办 |
| ISS-165 | ①规划 | 移出→规划中 | C1 step2（RAM@0 收口）；M6 待办 |
| ISS-168 | ①规划 | 移出→规划中 | 「`-bios`」+ELF 组合加载/ELF loader/组合 ADR；M6 待办 |
| ISS-169 | ①规划 | 移出→规划中 | 6 探针 `exit-port`→`SYS_EXIT`；归 `QEMU-053t`（M6） |
| ISS-019 | ③待裁定 | 移出→阻塞与待裁定 | golden/FP oracle 归属未定；给选项 |
| ISS-026 | ③待裁定 | 移出→阻塞与待裁定 | `imm` 语义守卫依赖 golden（同 019）；给选项 |
| ISS-047 | ③待裁定 | 移出→阻塞与待裁定 | objdump `e_machine` 未映射；④缺陷抑或①工具待办存疑；给选项 |
| ISS-074 | ③待裁定 | 移出→阻塞与待裁定 | `cs.*` overlap 语义（C-27）未指定；给选项 |
| ISS-081 | ③待裁定 | 移出→阻塞与待裁定 | FP 后续衔接点；FP 不在 M6 显式范围；给选项 |
| ISS-163 | ②③阻塞/待裁定 | 移出→阻塞与待裁定 | `Toolchain-01` 旧口径；**须授权**收口上游只读册；给选项 |
| ISS-164 | ②③阻塞/待裁定 | 移出→阻塞与待裁定 | cfx mask 屏蔽路径不可观测；须后续里程碑补验；给选项 |
| ISS-167 | ②③阻塞/待裁定 | 移出→阻塞与待裁定 | `DADAO-12 §5` prose/伪代码张力；**须授权**收口；给选项 |
| ISS-043 | ④真 issue | 保留 | 越界立即数静默截断（`LLVM-006t` 缺陷） |
| ISS-045 | ④真 issue | 保留 | `getFixupKindForInstr` default 未白名单化（缺陷） |
| ISS-054 | ④真 issue | 保留 | 探针手算分支偏移易错→标签化框架（技术债） |
| ISS-058 | ④真 issue | 保留 | `decodetree.py` 依赖 `PYTHONHASHSEED`（非可复现） |
| ISS-064 | ④真 issue | 保留 | `longjmp` 泄漏 MMIO re-entrancy 守卫（缺陷） |
| ISS-078 | ④真 issue | 保留 | `focls`/`ftcls` 外 FP 指令未复核（欠账） |
| ISS-090 | ④真 issue | 保留 | qemu `changelog.md` 缺任务级记录（欠账） |
| ISS-093 | ④真 issue | 保留 | 行内 code span 检测 deferred（技术债） |
| ISS-098 | ④真 issue | 保留 | harness `ret` 语义用例 pre-existing 失败（缺陷） |
| ISS-102 | ④真 issue | 保留 | 覆盖门控 `(id,class)` 粒度（欠账） |
| ISS-108 | ④真 issue | 保留 | 2 文件 >1000 行（跟踪/技术债） |
| ISS-118 | ④真 issue | 保留 | lit 覆盖断言粒度限制（欠账） |
| ISS-120 | ④真 issue | 保留 | `min_rom_probe` 群 FAIL / 009t-audit 漂移（缺陷） |
| ISS-125 | ④真 issue | 保留 | 生成器↔向量预存漂移（欠账） |
| ISS-126 | ④真 issue | 保留 | FP 开放点固定取值记录（spec 欠账）；**存疑已核**：取值已落地，非须决策 |
| ISS-138 | ④真 issue | 保留 | >128K 帧方案1 未实现（欠账）；**存疑已核**：能力已实现（方案2），仅分支遗留、显式失败 |
| ISS-148 | ④真 issue | 保留 | `gen_m1_asm.py` docstring 计数陈旧（欠账） |
| ISS-151 | ④真 issue | 保留 | 访存符号偏移 reloc 落 `REL20`（缺陷） |
| ISS-154 | ④真 issue | 保留 | `contract-elf.md` ABS48 数据表示缺失（spec 欠账） |
| ISS-156 | ④真 issue | 保留 | `set.fo rf,0` 口径不一（待核缺陷） |
| ISS-159 | ④真 issue | 保留 | lower `not`/`neg` 未走 `xnor.o`/`sub.sX`（技术债） |
| ISS-160 | ④真 issue | 保留 | `SPEC-106t` 范围外残留（欠账） |
| ISS-161 | ④真 issue | 保留 | `REL12` 未添加 / `FK_Data` 静默 0（缺陷+欠账） |
| ISS-162 | ④真 issue | 保留 | AsmParser 诊断枚举缺 `FIRST_TARGET_MATCH_RESULT_TY` 偏移（隐患） |

**验收结果（真实输出）**：
```
$ python3 tools/infra/check_issues.py
check_issues: 24 open, 0 closed (0 blocking M1-gate: 0)                  EXIT=0
$ bash .work/evidence/INTEG-024t/run.sh
VERIFY_FULL_RC=0 ; MD5_BEFORE=c5f98134509b44e11c904c4484cc28fd ; INJECT_EFFECTIVE=yes
FAIL  C5(注入检查) 迁出 id 未作为 issues.yaml 条目 | expected=0 actual=1 | rc=1   ← 注入后（预期 FAIL）
VERIFY_MOVED_PRESENT_RC=1（期望 1）；RESTORE_MD5_MATCH=yes；VERIFY_BACK_RC=0
== INTEG-024t evidence: ALL PASS ==                                      SCRIPT_EXIT=0
$ python3 -c 'yaml.safe_load(...)'  →  条目 24，open 24，closed 0
$ git -c core.quotePath=false status --porcelain -uall
 M Makefile                                       ← 改前基线（INFRA-050t 长构建），非本任务
 M .tao/knowledge/issues.yaml
 M .tao/knowledge/milestones.md
 M .tao/tasks/integ/INTEG-024t-issues台账搬迁.md
$ git diff --name-only | grep -E '^spec/'         →  （空；spec/ 交集为空）
```
（完整输出见 `.work/log/integ/INTEG-024t-evidence-run.log`。）

**新发现/坑**：
1. **`issues.yaml` 存在「无空行紧邻」的条目对**：`ISS-047` 的 `notes:` 行后**直接**跟 `- id: ISS-054`（无空行分隔）。按「空行分块」写的移除脚本会**连带误删** `ISS-054`（实测发生，见自审 F1）—— 应**以字段行（两空格缩进）界定块**，并以 `yaml.safe_load` **条目数/集合对账**兜底。
2. **迁出 id 清单须写入 `issues.yaml` 头部**（本任务硬约束）⇒ 裸 `grep -F 'ISS-<n>'` 会命中头部注释；「不重复记录」须按**条目级**（`- id:` 行 / YAML 节点）判定，裸子串检查会**假阳性**（脚本已按条目级实现）。
3. **`milestones.md` 既有「阻塞与待裁定」行**（含 8 个 id 的斜杠摘要）**必须保留** ⇒ 迁出 id 在该文件命中 **≥1 次**（非字面「命中一次」）；机制检查按「存在性」判并如实注明。
4. **`Makefile` 在改前即 dirty**（`INFRA-050t` 后台 LLVM 长构建所致，非本任务）⇒「无残留」以「**我的改动集 == 3 文件**（2 台账 + 本任务书）」判，`Makefile` 单列为改前基线。

**遗留问题**：
- **待裁定 8 项**（已在 `milestones.md`「阻塞与待裁定」列出**用户选项**并提请裁定；**用户未答（夜跑）**，按指示**不阻塞**）：`ISS-019`/`026`/`047`/`074`/`081`/`163`/`164`/`167`（选项见该文件；`ISS-163`/`167` 须**授权**收口上游只读册）。
- **存疑已核、判为 ④（未改归属）**：`ISS-126`（spec 欠账）/ `ISS-138`（llvm 欠账）/ `ISS-156`（待核缺陷）—— 依据见判定表。
- `Makefile` 改前 dirty：非本任务改动，**未触碰**（待 `INFRA-050t` 自身收尾）。

## 审阅记录

#### 第 1 轮 engineer 自审

**方式**：自主逐行审查（subagent_depth=1，无法嵌套子代理）+ 真实重跑对账；判决附真实输出/退出码。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 移除脚本首版按「空行分块」⇒ 因 `ISS-047` notes 后**无空行**紧邻 `ISS-054`，**误删 ISS-054**（24→23） | ✅已修 | 块界改为「连续两空格缩进字段行」+ `yaml.safe_load` 集合对账 | `yaml` 条目**24**；`missing=[]`；`removed` 恰为 15 个目标 id |
| F2 首版脚本连带误删 4 个 section 注释块（spec/infra/testcases、llvm/qemu/integ、原 backlog） | ✅已修 | 同上（块界只在字段行内） | `grep '^# ──'` 六段 section 头**全在** |
| F3 `milestones.md` 两条列表头用嵌套 `**…**`（markdown 非法嵌套加粗） | ✅已修 | 改为只加粗标签 `**`issues.yaml` 移入**`（…） | 目视复核两行；渲染无嵌套 |
| F4 `issues.yaml` M5 scope 枚举行「已达成」重复 | ✅已修 | 精简为「…门控…；**不再作 open 项 scope**…」 | `grep 不再作 open 项 scope` = 1 |
| F5 迁出 id 在 `issues.yaml` 中命中均为**注释行**（历史头 + 新清单），非条目 | ✅已核 | —— | 逐 id：`- id:` 条目命中 **0**；非注释行命中 **0** |
| F6 越界/残留：我的改动集须恰为 3 文件（2 台账 + 任务书）；`Makefile` 改前既有 | ✅已核 | —— | `git status -uall` = 3 文件 + 改前 ` M Makefile`；`spec/` 交集 **0** |
| F7 存疑项 `ISS-126`/`138`/`156` 逐条给依据、判 ④、**未改归属** | ✅已核 | —— | 判定表 3 行依据；三者仍在 `issues.yaml`（open） |
| F8 注入自检**能失败**（非恒真） | ✅已核 | —— | 注入后 md5 变（`c5f9…`→`fd04…`）、`C5` 报 **FAIL rc=1**、`cp` 还原 md5 一致、回绿 `rc=0` |
| F9 无连续空行 / 尾单换行 / 无尾随空白 | ✅已核 | —— | `awk` 连续空行=0；两文件尾单 `\n`；`grep ' +$'` 无 |
| F10 `make` 未跑（纯 `.tao` 豁免；后台 LLVM 长构建） | ✅已核 | —— | 未调用 `make`；`check_issues.py` 直接 `python3` 调用 |

**判决**：F1–F4 已修并复验；F5–F10 已核实。无未修 finding ⇒ 状态置 `待验收`，返回主会话。
**（待用户裁定，未擅自处置）**：8 项（`ISS-019/026/047/074/081/163/164/167`）—— 见完成区「遗留问题」。

#### 第 1 轮 reviewer 验收

**重跑**：`bash .work/evidence/INTEG-024t/run.sh` → **EXIT=0**（38 项 PASS，0 FAIL；含注入→FAIL→cp+md5→回绿全流程）。

**独立注入反例**（临时树 `/tmp/opencode/INTEG-024t-review/inject/`）：
- 追加 ISS-003 → `PRE_MD5=41d017…` → `INJECTED_MD5=1f7c1d…`（不同=注入生效）→ `git diff --name-only` 非空
- `verify.py moved-present` → **FAIL rc=1**（`expected=0 actual=1`）
- `cp` 还原 → `RESTORED_MD5=41d017…` == `PRE_MD5`（md5 一致）→ `verify.py full` → **FULL_RC=0**（回绿）
- 未用 `git checkout/restore/stash`

**独立核算**：issues.yaml open **24**；移出 id 集 15 ∩ 保留 id 集 24 = **∅**；15+24=**39**；移出 id 在 milestones.md 全命中（≥1）；保留 id 在 milestones.md **0 命中**。`milestones.md` diff 对比 `ec343b9` 版：**纯新增行（`>`），无删除行（`<`）**——既有条目完整保留。

**约束核验**：
| # | 约束 | 结果 |
|---|---|---|
| ① | `spec/` 交集为空 | ✅ `git diff`/`git status` 均 0 |
| ② | 只动 `.tao/knowledge/{issues.yaml,milestones.md}` + 本任务书 | ✅ 3 文件；`Makefile` 改前既有（`INFRA-050t` WIP，非本任务） |
| ③ | milestones.md 既有条目未删/改写 | ✅ diff 纯新增 |
| ④ | 无 `_tmp/_orig/_rej/_preinject` 残留 | ✅ |
| ⑤ | 8 项待裁定均有用户选项 | ✅ 各项 `grep 选项` 命中 2–7 |
| ⑥ | `check_issues.py` EXIT 0 | ✅ |
| ⑦ | 计数 39=移出15+保留24 | ✅ |
| ⑧ | 不提交 git | ✅ |

**判决**：**Accepted**——全量重跑全绿、独立注入可失败且可还原、独立核算一致、约束全通过。

#### architect 收尾 · 提交（第 1 轮 reviewer Accepted 后）

- **档位**：**正常提交**（reviewer 判 `Accepted`）。
- **文件集对账**：显式 staging 3 文件，`git diff --cached --name-only` == 任务书「修改文件」声明的 3 项（`issues.yaml`、`milestones.md`、本任务书）；**无漏提/多提/越界**；`Makefile`（`INFRA-050t` WIP）**未纳入**。
- **提交**：`61b3229` —— `INTEG-024t: issues 台账按性质分流…`（**只 commit，未 push**）。
- **收尾**：任务书 `**状态**` → `已验证`；`milestones.md`「任务流水」新增 `INTEG-024t` 行（开始 10-09 00:00 / 结束 10-09 00:05，取自制品 mtime）。
- **lessons.md**：本任务两坑（YAML 无空行条目致分块解析误删；id 清单裸子串假阳性）判定可复用，但受提交文件集约束（3 文件 + 对账）**未追加**——坑已留任务书完成区，提请主会话按需另立条目。
- **交叉复核**：`check_issues.py` EXIT=0（24 open）；证据脚本 `SCRIPT_EXIT=0` 独立重跑；`spec/` 交集 ∅；无越界。
