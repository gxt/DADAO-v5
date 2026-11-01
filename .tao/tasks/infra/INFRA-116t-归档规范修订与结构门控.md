# INFRA-116t: Process-04 归档规范修订 + 归档结构门控

**模块**：infra
**项目里程碑**：M10 后（维护）
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（仓库根 `/mnt/tao/DADAO-v5`；临时产物只放 `/tmp/opencode/INFRA-116t/`，证据落 `.work/evidence/INFRA-116t/`）

## 背景（用户 2026-11-01 已确认，逐条）

1. **不再强制每个模块都有 `m`**：某模块需要单独里程碑验收时再加。
2. **任务流水冻结到各里程碑 `README.md`**，并从 `.tao/knowledge/milestones.md` 清理；活台账只留当前/维护任务行 + 归档指针。
3. **归档目录只允许**：`README.md`、`m<i>-retrospective.md`、`issues-closed.md` 和按模块组织的已验收任务书。
4. **任务书必须与 README 任务流水对应且为已验收**（状态/里程碑字段可机械校验）。
5. **`m` 文件数量不纠结**：M7 多 `m`、M3 缺 qemu `m`、M8–M10 缺模块 `m` 均不补、不删、不改。
6. **缺失状态补状态**（有完成证据才补）。
7. **状态非精确 `已验证` 的规范化**（括注移入状态注记/审阅记录）。
8. **模板统一**：任务清单 / 任务流水（冻结） / 终局证据 / MEMORY 摘录 / 指针。
9. M7 `notes/` 类补充记录**不得**留在 archive 根或 `notes/`，改为并入 `m<i>-retrospective.md` 附录或拒绝（具体合并归 `INFRA-117t`）。

## 预检（只读，已现场核实）

- **立项前** `INFRA-116` / `INFRA-117` 在仓库内**零命中**（任务书/文档/Makefile），编号未占用。
- `.tao/archive/M1…M10/` 均存在；每目录现有 3 件套 + 模块子目录；`M7/notes/` 5 文件（746 行）为唯一 `notes/`；M9/M10 顶层各有 1 份 `INTEG-*m-*.md` 核验册（历史放置）。
- 各归档 README 的「任务清单」模块计数与模块目录实际文件数**逐目录相符**（M1–M10 全部 `OK`）。
- 现状缺口（117 修，116 只登记）：M9/M10 README 缺「任务流水」「MEMORY 摘录」节；M2 `TESTCASES-019t`、`SPEC-064t` 状态带括注；M7 `notes/` 含 4 份无状态字段记录 + `INTEG-027t-report` 状态 `待验收`。
- `python3 tools/infra/check_milestones_fresh.py` 现绿（74 行）；`python3 tools/infra/check_tasks.py` 现绿（0 漏收尾，3 册待开始）。两者均为本任务只读基线。

## 接口规范

### A. `docs/Process-04-里程碑归档规范.md`（规则正文，必须逐条落地）

1. **文件头**：删「无专用机器 checker」表述，改指向 `tools/infra/check_archive.py`；状态日期更新。
2. **§1 生命周期**：删除「`spec`/`llvm`/`qemu`/`testcases`/`infra` 各放一个 `m`」的强制表述；改为：
   - `m`（模块里程碑核验册）为**按需产物**——仅当该模块需要单独里程碑验收时设立；
   - 项目收敛可由 `INTEG` 收尾任务（`k`/`m` 均可）承担，**不强制每模块 `m`**；
   - 明示 M7 多 `m`、M3 缺 qemu `m`、M8–M10 缺模块 `m` 均**合规**，不补不删。
3. **§2 / §4.2 / §7**：任务流水**冻结到各归档 `README.md` §2**；`milestones.md` 归档时删除该里程碑全部流水行，只留**当前/维护任务行**与**归档指针**（指针写「流水见 archive/<M>/README.md §2」）。
4. **§5 落点与结构**：根级允许项**封闭**为：
   - `README.md`、`m<i>-retrospective.md`、`issues-closed.md`；
   - `INTEG-*m-*.md` 核验册**仅历史归档（M9/M10）可置根**，新归档应放 `integ/`；
   - 其余一律模块子目录（`infra`/`integ`/`llvm`/`qemu`/`spec`/`testcases`），子目录名不得超出该集合；
   - **禁止** `notes/`、根级补充记录、其它杂项文件；补充记录只能并入 `m<i>-retrospective.md` 附录（或拒绝入库）。
5. **§4.1 判据**：任务书 `**项目里程碑**` **恰好** `M<i>`；归档册状态必须**精确** `已验证`（`t`/`k`）或 `里程碑`（`m`），**不得**带括注；缺失状态须有完成区/审阅记录证据才补。
6. **§6 模板**：统一五节——`## 1 任务清单` / `## 2 任务流水（冻结）` / `## 3 终局证据` / `## 4 MEMORY 摘录` / `## 5 指针`。
   - M1–M8 历史归档允许 `changelog` / `台账快照` 作为「任务流水」**同义别名**（标题加一句别名说明即可，不重写内容）；`终局证据` 节**仅 M9 起必需**（M1–M8 可缺，但指针须指向回顾）。
   - 任务流水表列固定 `| 编号 | 状态 | 完成时间 | 一句改动 |`；搬入时按任务书状态**规范化**，不得保留 `（登记）`。
7. **§7 原台账处理**：更新 `milestones.md` 行为「删除 ≤ 达成日流水行 + 加归档指针」，不再「移入 README 后保留」。
8. **§8 验收与纪律**：增加 `make check-archive`（L1）与 `--self-test`；写明 116→117 过渡期允许 `--pending-ok`，117 完成后必须严格。

### B. `tools/infra/check_archive.py`（新增，结构门控）

- 扫描 `.tao/archive/M<数字>/`（**排除** `SimRISC-*`），只读、不依赖 `.work/`。
- 每目录检查（任一不满足 ⇒ FAIL，fail-closed）：
  1. **三件套**：`README.md` / `m<i>-retrospective.md` / `issues-closed.md` 存在且非空。
  2. **根文件封闭**：仅允许三件套 + `INTEG-*m-*.md`（历史核验册）；其它根文件 ⇒ FAIL。
  3. **子目录**：仅允许 6 个模块名；`notes/` 或其它目录 ⇒ FAIL。
  4. **任务书字段**：模块子目录与根级 `m` 册的每份 `*.md` 必须含 `**状态**`（任意位置）且值 ∈ {`已验证`,`里程碑`}；`**项目里程碑**` 值 == `M<i>`；缺失/不符 ⇒ FAIL。
  5. **任务清单计数**：README §1 的模块计数 == 模块目录实际 `*.md` 数（现场统计，不写死）；根级 `m` 单列不计入模块计数。
  6. **任务流水对应**：README 的「任务流水 / changelog / 台账快照」节须有表格；M7+（编号列格式）要求流水 ID 集合 == 模块任务书 ID 集合（根级 `m` 可入可不入）；M1–M6 历史 `changelog`（日期列）只要求表格存在 + 任务清单计数对应；行状态须等于任务书状态。
  7. **MEMORY / 指针**：README 须有含「MEMORY」的节与含「指针」或「相关索引」的节；M9+ 另须含「终局证据」节。
  8. **issues 快照**：`issues-closed.md` 须含至少一条 `ISS-<数字>` 或等价计数表，空壳 ⇒ FAIL。
- **过渡模式**：`--pending-ok` 仅豁免**显式常量** `PENDING_117`（初始 = M2 两册状态括注、`M7/notes` 目录、M9/M10 README 缺流水/MEMORY）；默认（无 flag）严格，`PENDING_117` 命中即 FAIL。117 完成后删除该常量与 flag。
- `--self-test`：临时树基线 PASS + **≥6 类注入各自 FAIL**（根杂项文件、`notes/`、状态非终态、里程碑字段不符、清单计数不符、流水缺册/多册、缺 issues 快照、`--pending-ok` 边界）。
- `--root DIR` 供自检；退出码 0/1；打印现场计数（不写死）。

### C. `docs/Process-07-门控分层规范.md`

- §1.1 增行 `make check-archive`：**L1**，判据 = 归档目录结构/任务书字段/README 三节对应/issues 快照，`--self-test` 可达 FAIL；注明 116 过渡期 `--pending-ok`、117 后严格。
- §2 触发点：L1 默认包含；不新增收尾专项。

### D. `Makefile`

- 新增 `check-archive` 目标（`$(PYTHON) tools/infra/check_archive.py --pending-ok`，注释标 `INFRA-116t 过渡；117 去 flag`）。
- 加入 `.PHONY`、`_locked-check` 依赖列表、`make help` 一行。
- **不得**把 `check-archive` 放进 L2/L3 或 `check-milestone`（一层一列）。

## 验收标准

1. `python3 tools/infra/check_archive.py --self-test` **rc=0**，输出逐项列出 ≥6 类注入的 FAIL 命中。
2. `python3 tools/infra/check_archive.py --pending-ok` **rc=0**，且打印的 PENDING 项**恰好**等于 `PENDING_117` 常量（逐条对账）。
3. `python3 tools/infra/check_archive.py`（严格）**rc=1**，VIOLATION 集合**只**包含 `PENDING_117` 项（证明非过渡模式确实能红）。
4. `make check` **rc=0**（L1 已含新目标）；`make check-milestones-fresh` 仍 **rc=0**。
5. Process-04 逐条核对表：用户 9 条 → 文档节号/行号，9/9 命中；`grep` 不再出现「各模块…各放一个 `m`」强制句。
6. `git diff --name-only` 仅含 `docs/Process-04*`、`docs/Process-07*`、`tools/infra/check_archive.py`、`Makefile`、本任务书、`milestones.md`；`.tao/archive/**` **零改动**。
7. 证据脚本 `.work/evidence/INFRA-116t/run.sh` 可一键重跑（含反例注入→FAIL→`cp`+md5 还原→回绿），reviewer 独立注入一次。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
