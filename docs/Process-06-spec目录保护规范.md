# spec 目录保护规范

> **状态**：生效（2026-10-07）｜**上位依据**：无——属**工程过程规范**（可逆、单项目、无外部契约，不命中 ADR 判据，见 `docs/Process-03`）。
> **缘起**：`SPEC-114t` 的工程师**未获授权擅自修改上游只读册** `spec/DADAO-12`、`spec/DADAO-22`（各插入 2 行）事故。用户 2026-10-07 裁定「**所有针对 spec 目录的修改，都应该经过我的允许，不能擅自进行**」；本规范把该纪律落为**机械门控**（清单 + 哈希）+ **三处固定检查**（下发 / 验收 / 提交）。
> **关键词**：本规范用「**必须**（MUST）／**应当**（SHOULD）／**可以**（MAY）」表达规范性等级。§1–§5 均标 **MUST**。

---

## 1. 上游只读册只作只读引用（MUST）

任务书「输出」**不得**把上游只读册（清单见 §6）列为**可改对象**：对上游册只作**只读引用**——引其 `§` 章节号，**不改一字**。需要的新正文一律落 **v5 自定规范**（技术册 `spec/Machine-*`、工程流程规范 `docs/Process-*` 等）。

## 2. 任何 `spec/` 改动须用户事先明确允许（MUST）

`spec/` 目录下**任何新增 / 修改 / 删除**（含 v5 自定技术册 `spec/Machine-*` 与 `spec/README.md`），以及**工程流程规范** `docs/Process-*` 的同类改动——**均必须**先取得用户**事先**明确允许，并在任务书 / 审阅记录中**留存授权原话**（子会话问答对父会话不可见，见 `AGENTS.md`「子代理不得直接向用户提问」）。**未获授权而拟改 `spec/` ⇒ BLOCKED**，不得动笔。

> 注：本规则**不止**约束上游只读册——`spec/` 下**任何**册（含 v5 自定册与索引 `spec/README.md`）都须用户事先授权。

## 3. 下发前预检：第 5 项（MUST）

`/dispatch` 前，主会话**必须**把**拟改文件清单 × `spec/` 清单**逐一对照：凡**命中 `spec/`** 而任务书**无用户授权原话**者 ⇒ **BLOCKED**。据此，`AGENTS.md`「下发前预检」由 **4 项扩为 5 项**（新增本项）。

## 4. reviewer / architect 固定检查（MUST）

- **reviewer** 验收与 **architect** 提交前，**必须**固定执行 `git diff --name-only`（提交前为 `git diff --cached --name-only`）并与 `spec/` 清单交叉；
- **有交集而缺用户授权证据** ⇒ **reviewer 判 `Needs Revision` / architect 拒绝提交**。

## 5. 只读册清单 + 哈希校验机制（MUST）

`spec/` 下每个文件（上游只读册 20 册 + v5 自定册 `spec/Kaiwu` + 目录索引 `spec/README.md`）登记于 **`spec/.manifests.toml`**，逐文件 `sha256`，由 **`make check-manifests-guard`** 校验（L1，已纳入 `make check`）。确需**新增 / 修改 / 删除**某册（**须先经用户授权**，见 §2）时，**同一变更**内**必须**同步更新 `spec/.manifests.toml`（登记新条目 / 删条目 / 重算 `sha256`）+ 在完成区记录授权原话；**未同步即动册 ⇒ 门控 FAIL**。

- 清单体例（`.manifests.toml` schema v1，数据文件：**只写数据、不写过程注记**，变更依据看 `git log`）：`schema = 1` + `owner = "spec"` + `subdirs = []` + `recursive = false` + 每册一条 `[files."<name>"]`（`sha256`）。清单**自身不计入集合**，`files` 的键是**该目录的直接子文件**。可选 `[subdir_owners]`（`子目录名 = "模块"`）为**声明性**子目录归属映射：门控只打印不判红，但**键必须属于 `subdirs`**（悬空 owner ⇒ FAIL），故归属也须写成数据而非注记；不填合法（`spec/`、`.tao/`、`.tao/knowledge/` 均不填）。
- 校验器：`tools/infra/check_manifests_guard.py`——**双向**断言（目录实际文件集合 == `files`，新增册与删除册**都红**）+ 逐字节 `sha256`；`owner` 只打印不判红。同一清单机制也覆盖 `.tao/`、`.tao/knowledge/`（口径见 `docs/Process-07`）。
- **必需清单注册表**：`manifests/dir-guard-roots.toml`（`schema = 1` + `roots = [...]`）列出「必须有 `.manifests.toml` 的目录」。门控**按注册表逐个校验**（不是「扫到什么管什么」）：登记目录**缺清单** / **目录不存在** / **注册表自身缺失或不可解析** ⇒ FAIL；**游离清单**（磁盘上有但目录未登记）⇒ FAIL（只提示会让新增清单被静默忽略 = 另一个 fail-open）。删某份清单**不再**等于关闭该目录的约束。

## 6. 只读册清单（判据，21 册 + 索引）

> `sha256` 真源见 **`spec/.manifests.toml`**（本节只列册与分组，避免双份哈希漂移）。

| group | 册 |
|-------|----|
| `dadao-1x` | `spec/DADAO-11-AEE-应用程序运行环境.md`、`spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/DADAO-13-HEE-超管系统运行环境.md` |
| `dadao-2x` | `spec/DADAO-21-ABI-应用程序二进制接口.md`、`spec/DADAO-22-SBI-主管系统二进制接口.md`、`spec/DADAO-23-HBI-超管系统二进制接口.md` |
| `simrisc-00..12` | `spec/SimRISC-00-指令系统设计.md` … `spec/SimRISC-12-其它指令.md`（共 13 册） |
| `toolchain-01` | `spec/Toolchain-01-汇编语言.md` |
| `kaiwu` | `spec/Kaiwu-测试机运行环境.md` |

> **不在 `spec/` 清单内**：`docs/Process-0x`（工程流程规范）——其正当修订由 §2 的授权流程把关。`spec/README.md` 是**目录索引**，已在 `spec/.manifests.toml` 内（新增 / 修改 / 删除同样须授权 + 同步清单）。

## 7. 与其它规范的关系

- `docs/Process-03`（ADR）：本规范属**工程过程规范**，不命中 ADR 判据（可逆、单项目、无外部契约），**不立 ADR**、**不承载 ADR 决策**；
- `docs/Process-01`（组件补丁）：组件补丁的机械校验与此无关；
- `AGENTS.md`：本规范落地其「下发前预检」「提交分档与角色」中的 `spec/` 保护要求。

## 8. SimRISC 版本归档（MUST）

**规则**：每次 **SimRISC 正式版本升号**（去 `-rc` 发布）**必须同笔**落 `.tao/archive/SimRISC-<ver>/`；**`-rc` 预发布段不归档**（用户 2026-10-25 裁定：`SimRISC-0.5.5-rc` 目录已删除），并在其中写 `PROVENANCE.md`。归档是**只读历史快照**：不参与 `spec/` 门控扫描，任何引用须指向该目录、不得改写其内容。

- **快照定义**：版本 `V` 的快照 = **末次声明 `V` 的提交**，即「下一版本标记首次出现的提交的父提交」。
- **快照内容**：该提交下 `SimRISC-*.md` **全集**（`≤0.5.3` 为 5 分册、`≥0.5.4` 为 13 分册），逐文件原样落盘；wiki 历史文件名中的 Unicode 连字符（U+2010）在落盘时归一为 ASCII `-`，`PROVENANCE.md` 须记录。
- **只增不改**：已存在的归档目录**一个字节都不改**（差异只报告、不覆盖）；`0.5.3` 及以前建立的既有目录（`SimRISC-0.4.1`、`SimRISC-0.5.3`）建立时无 `PROVENANCE.md`，其来源以 `spec/SimRISC-00` 的「附录：版本与变更记录」与本规范为准，**不回填改写**。
- **生成与校验**：`tools/spec/gen_spec_archive.py --list|--apply|--verify`（清单派生 / 只新增 / 三向校验），清单列 = 版本 / 首次提交 / 快照提交 / 首次标记日期 / 来源仓库 / 文件数 / 版本组合 `sha256`；版本组合 `sha256` 定义 = 按文件名排序拼 `<file sha256>  <basename>\n` 后取 `sha256`。
- **门控**：`make check-spec-archive`（**里程碑收尾**，由 `make check-milestone` 触发；**不入 L1**，2026-10-25 用户裁定）。断言 A1（册头 ∪ 附录声明的每个版本都有目录）、A2（目录非空且含 `SimRISC-00*`）、A3（文件数 = 派生清单）、A4（**反向**：磁盘上每个 `.tao/archive/SimRISC-*/` 目录都必须出现在派生清单里）⇒ **双向**（清单 ⊆ 磁盘 且 磁盘 ⊆ 清单）；**只校验存在性与文件集，不校验内容**；`-rc` 版本**不参与**门控（脚本按后缀过滤）。`--self-test` 内置 5 类反例（含「磁盘多出清单元」）各自须 FAIL。
- **门控决策（采纳）与依据**：规则若无机械约束必然再次漂移——`0.4.0`…`0.5.4` 及当时在研的 `-rc` 快照共六版本缺失正是无门控的结果；成本仅一个只读脚本 + 秒级派生。**被否方案**：① 校验归档内容 `sha256` 与当前 `spec/` 相等——`-rc` 段每次改动都会红；② 只写文档不进门控——无强制力。
- **附录口径（避免与归档混淆）**：附录 `### <ver>` 段记录的是**该版本开发区间**的改动，即 `git diff <上一版号提交> <本版号提交>`（`0.5.0` 段自 `0.4.1` 同步基线段起算）；归档则按上面的「末次声明」取快照。二者在版本号未及时升号的长区间（如 `0.5.3` 头自 2026-07-19 保持到 2026-09-28）会**有意不一致**：该区间的改动用 `0.5.4` 段记载，而 `SimRISC-0.5.3/` 归档含这段改动。逐条 diff 指针写 `（<sha>）`。

## 9. 生成段不许手改（MUST）

**规则**：`spec/` 里凡是**由工具生成**的区段，一律**只由生成器写**——手改生成的字节视为违规，由门控判红；改源头而不是改结果。

- **已登记的生成段**（每段都有起止标记，标记之间**只能**由生成器改写）：

  | 生成段 | 标记 | 源 | 生成器 | 门控 |
  |--------|------|----|--------|------|
  | 指令执行语义（IDL） | `<!-- IDL:<instr-id> BEGIN -->` … `<!-- IDL:<instr-id> END -->` | 仓库根 `idl/SimRISC-NN.idl`（`# id:` 分段） | `idl/tools/idl_render.py` | `make check-idl-sync`（L1） |
  | 汇编速查表 | `<!-- ASSEMBLY_LIST_START -->` … `<!-- ASSEMBLY_LIST_END -->` | `contracts/opcodes.yaml` | `tools/llvm/gen_asm_list.py` | `make check-asm-list`（L1） |
  | 合法性清单 | `<!-- LEGALITY_START -->` … `<!-- LEGALITY_END -->` | `contracts/legality_rules.yaml` | `tools/spec/gen_legality_list.py` | `make check-legality-drift`（L1） |

- **IDL 段的约定**：一条指令一个标记对；标记名 = 该指令在 `contracts/opcodes.yaml` 的 id；**每个源 operation 必有落点、每个落点必有源**（空标记 ⇒ FAIL）；落点册必须与源文件册（`idl/SimRISC-NN.idl` ↔ `spec/SimRISC-NN-*.md`）一致；标记之间不得放其它标记（禁嵌套）。
- **改字的正确姿势**：改语义 ⇒ 改 `idl/*.idl` 后跑 `python3 idl/tools/idl_render.py`；只想让门控变绿而改 `spec/` 里的块 ⇒ 下一次 `check-idl-sync` 必红（该门控是**逐字节**比对，不是「格式检查」）。
- **审计口径**：`spec/` 的任何改动仍须用户事先允许（§2）并同笔更新 `spec/.manifests.toml`（§5）；本节的附加要求是「生成段的改动必须能追到源」。
