# INFRA-071t: `contract-*.md` 迁入 `.tao/contracts/`（Phase B）+ `check-contracts-dir` 白名单门控

> **文件名说明**：文件名仍含旧措辞 `迁移至contracts目录`（`issues.yaml` `ISS-202` notes 按**文件名**引用）⇒ **不改名**（改名会牵动归档/台账指针）；**目标目录以本任务书正文为准 = `.tao/contracts/`**（见 §目标目录变更）。

**模块**：infra
**项目里程碑**：M8
**依赖**：**用户授权**——**已得（2026-10-14）**：裁定 ①a/②a/③a + 目标目录 `.tao/contracts/`（「改主意」+「同意」）；落纸见 §用户授权落纸。**可 `/dispatch`**。

**状态**：待开始

> **立项来源**：`INFRA-070t`（`.tao/knowledge/` 顶层收拢）**Phase A 已完成并 reviewer `Accepted`（主会话收尾）**；**Phase B**（立项时口径：9 个 `contract-*.md` → `contracts/`）因**硬约束冲突**停手 ⇒ 本任务承接（`INFRA-070t` 完成区「遗留问题」+ 第 1 轮 reviewer §⑧）。
> **现状校正（2026-10-14）**：待迁份数 **9 ⇒ 11**（新增 `contract-dynlink.md`〔`SPEC-139t`〕/ `contract-syscall.md`〔`SPEC-138t`〕）；目标目录 **`contracts/` ⇒ `.tao/contracts/`**（用户 2026-10-14 二问裁定）。**份数以现场 `ls` 实测为准**（**计数不写死**）。
>
> **用户裁定原话（2026-10-13，追加）**：「`【INFRA-071t】它的项目里程碑归属怎么定？` / 用户选择 = **改标 M8（推荐）**」（2026-10-13）——本项目里程碑字段由 `M7` 改标为 `M8`（**只改该字段**；任务书仍留 `.tao/tasks/`、不归档）。

## 目标目录变更（2026-10-14；用户「**改主意**」+「**同意**」）

> **用户裁定原话（2026-10-14；渠道 = 经主会话问答）**——**原样引录**：
> - 「**我改主意了，contracts-*.md改到 .tao/contracts/ 目录下，是不是更合适**」
> - 「**同意**」（= 同意 `.tao/contracts/` 方案与主会话列出的做法）

**变更**：迁移**目标目录** `contracts/` ⇒ **`.tao/contracts/`**（**只改目标目录**；本任务其余范围、3 项裁定、命名/格式口径**均不变**）。

**理由**（现场事实）：
1. **分层归位**：11 份 `contract-*.md` = **归一化叙述正文**，性质属「**结论/口径**」层 ⇒ 归 `.tao/`（与 `.tao/knowledge/`、`.tao/adr/` 同级）；`contracts/`（仓库根）保持**纯机器可读数据**——其 `README.md:3` 自述「**从 `.tao/knowledge/contract-*.md` 与 ADR 派生**」⇒ **正文是源、`contracts/` 是派生**。
2. **改动面更小**：`contracts/` 现 5 个条目（4 YAML + `README.md`）不必再混入 11 份 `.md`；该 `README.md` 只需改**来源路径**（**无**清单/白名单扩项）。
3. **命名/格式裁定不变**：`.md` **保留 `contract-` 前缀**；`*.yaml` **不改名、不转 TOML**。

**连带影响**（本任务书已同步）：
- `check-contracts-dir` **检查路径**改 `.tao/contracts/`；`contracts/` 侧白名单的 `contract-*.md` 项**随迁出作废**；
- **引用检查覆盖须含 `.tao/contracts/**`**（否则新位置引用**悬空不报**）；
- `AGENTS.md` 目录注释 `.tao/` 行补「**契约**」。

## 背景：Phase B 停手原因（引用冲突**逐类计数**）

`INFRA-070t` 的硬约束 = **「不改 `spec/`、`contracts/`、组件补丁」**，只动范围 = `docs/**`、`.tao/knowledge/**`、`.tao/archive/M7/notes/**`、`tools/llvm/**`、`Makefile`、`tools/infra/**`、任务书。而旧路径 `.tao/knowledge/contract-*.md` 的引用**均落在只动范围之外**：

| 类 | 命中（`git grep '\.tao/knowledge/contract-'`，现场行数） | 性质 |
|---|---|---|
| `spec/Toolchain-01-汇编语言.md` | 5 | **只读哈希锁册**（`manifests/spec-readonly.lock.toml` 的 `path`+`sha256`）⇒ 改须**用户事先授权**（`Process-06 §2`） |
| `spec/README.md` | 2 | v5 自定册（不在锁内，但 `spec/` 改动仍须授权） |
| `contracts/`（4 `*.yaml` + `README.md`） | 8 | 含 `abi.yaml` 的 `contract:`（`:30`）/`detail_contract:`（`:59`）**嵌套字段**（**机器读取值**）⇒ 与「内容不动」冲突 |
| `tools/**` | 36 | 生成器/校验器/探针硬编码旧路径（如 `check_fp_contract.py`）；其中 `tools/{testcases,qemu,integ}` = 17 |
| `components/**`（补丁注释 / README） | 13 | 组织/生成/应用/校验受 `docs/Process-01` 约束 |
| `tests/**`（README / 向量脚本） | 12 | 向量/README 引用 |

> 计数为本任务书**立项时**（2026-10-13）现场实测（`git grep -c`，**按行**）；`contracts/` 8 = `abi.yaml` 4 + `fp_semantics.yaml`/`legality_rules.yaml`/`opcodes.yaml` 各 1 + `README.md` 1。
> **本节保留为立项依据（历史）**；**现行范围与口径**见下 §引用同步范围（2026-10-14，按**出现次数**、**排除归档**）。**执行时须重测**，不采信任何写死值（**计数不写死**）。

**结论**：Phase B **不是**纯 `.tao/knowledge/` 内操作——会触及**只读锁册**与 `contracts/` **内容** ⇒ **须用户按下列待裁定项逐条裁定后方可开工**（3 项**已裁定**，见 §用户授权落纸）。

## 引用同步范围（2026-10-14 更新；**排除 `.tao/archive/**`** ✗）

**计数口径**：`git grep -o '\.tao/knowledge/contract-'`（**出现次数**，非行数）；**architect 2026-10-14 现场实测** ⇒ **执行时须重测，不写死**。

| 需同步（非归档）区域 | 现场次数 | 说明（高价值项已点名） |
|---|---|---|
| `.tao/adr/` | 33 | ADR 内指针（`adr-0019`/`adr-0025` 等） |
| `.tao/knowledge/` | 25 | 含 `MEMORY.md:18` **入口指针** + 各 `contract-*.md` **互指/自引** + 台账（`milestones.md`/`issues.yaml`） |
| `.tao/tasks/` | 19 | **活**任务书（**不含** `.tao/archive/**`） |
| `tools/spec/` | 12 | **生成器/门控**：`generate_opcodes.py`/`gen_cfx_aliases.py`/`check_asm_list_drift.py`/`check_fp_contract.py`/`check_qfc_coverage.py`/`check_cfx_aliases.py`/`check_d7_consistency.py`/`check_asm_prose.py` |
| `tests/llvm/` | 10 | `lit/MC/DADAO/README-m4.md`/`README-m5.md`、`codegen/m5/README.md`、`m6/README.md`、`validate_cfx_vectors.py` |
| `tools/qemu/` | 9 | `min_rom_probe_034t…047t.py`（7 份） |
| `components/qemu/` | 8 | 5 份**补丁注释**（`helper.c.patch` ×3、`common-semi-target.c.patch` ×2 等） |
| `tools/testcases/` | 7 | 向量生成/校验器（`validate_m5_vectors.py`/`validate_m6_vectors.py`/`generate_isa_vectors.py` 等 5 份） |
| `spec/Toolchain-01-汇编语言.md` | **6**（5 行） | **只读哈希锁册**（`manifests/spec-readonly.lock.toml`）⇒ 改后**重算 `sha256`**（裁定 ①a） |
| `tools/llvm/` | 5 | `gen_cfx_alias_table.py`(3)、`gen_asm_list.py`(2) |
| `contracts/abi.yaml` | 4 | 含**结构化字段** `contract:`（`:30`）/`detail_contract:`（`:59`）＋ 2 处注释 |
| `components/llvm-project/` | 3 | 3 份补丁**注释** |
| `tools/infra/` | 2 | **门控自身**：`check_spec_refs.py`、`check_spec_drift.py` |
| `tests/vectors/` | 2 | `README.md`、`schema.md` |
| `spec/README.md` | 2 | v5 自定册（**不在锁内**；改仍属 `spec/` ⇒ 裁定 ①a 覆盖） |
| `docs/fp-oracle-design.md` | 2 | 语义真源指针 |
| `components/picolibc/` | 2 | 1 份补丁注释 + `README.md` |
| `docs/Machine-00-执行环境分层-Draft.md` | 2 | 指针（含 `contract-*` 通配） |
| `tools/integ/` | 1 | `run_m5_e2e.py` |
| `contracts/{opcodes,legality_rules,fp_semantics}.yaml` | 各 1 | YAML **注释** |
| `contracts/README.md` | 1 | 来源路径句（`:3`） |
| 顶层 `Makefile` | 2 | `:522`/`:549` **注释** |
| 顶层 `README.md`、`AGENTS.md` | 各 1 | 指针 |
| **合计（非归档）** | **162** | —— |

- **排除 ✗**：`.tao/archive/**`（**182 个文件 / 741 处**）**一律不改**——历史留痕（`Process-04` 归档**不得回改**）。
- **与派单口径差异（如实披露）**：派单称「共 343 处，其中归档 182 处、其余约 161 处」；本次实测 = **非归档 162 处 / 归档 182 个文件（741 处）**——**「归档 182」「非归档 ≈161」两端一致**，总数差异系**计数口径**（出现次数 vs 文件数/行数）⇒ **以现场重测为准**，上表只作**范围清单**、不作目标值。
- **同号误伤警示 ✗**：归档内另有 `LLVM-077t`/`SPEC-077t`/`LLVM-081t`/`SPEC-081t` 等**同号不同任务** ⇒ 同步**只替换旧路径串**（`.tao/knowledge/contract-`），**不得**顺带改任务号/文件名。
- **逐目录核对（硬要求）**：执行后按上表**逐目录**重测 ⇒ 非归档区域**全部 0**（含顶层三文件 `AGENTS.md`/`README.md`/`Makefile`）；归档计数**不变**（证未误伤）。
- **「历史语境」逐条判定（硬要求）**：残留若非 0，须**逐条**判定并写入完成区（行号 + 理由）：
  - **现状指引类**（读者/工具据此找"**现在**在哪"：`MEMORY.md` 入口指针、`spec/README.md`、`AGENTS.md`、各 README、生成器/门控/探针常量、ADR 指针、`contracts/*.yaml` 字段值） ⇒ **必须改**；
  - **历史记录类**（台账流水行、`issues.yaml` 已登记 notes 等，语义 = "**当时**落在哪"） ⇒ **保留原路径 + 追加迁移注记**（如「（2026-10-14 迁 `.tao/contracts/`）」），**不得**改写成"当时就在新路径"（伪造史实 ✗）；
  - **本任务书自身 / 其 `.work/evidence` 日志**（描述**迁移动作**的必然提及） ⇒ **豁免**（`:(exclude)` 排除并**列出**排除行）。

## 待用户裁定项（逐条列选项；立项后由主会话问）

1. **是否授权改只读锁册**：`spec/Toolchain-01-汇编语言.md` 在 `manifests/spec-readonly.lock.toml`（`path`+`sha256` 锁册）。选项：
   - (a) **授权改 + 重算** `sha256` 回填锁册（走 `Process-06 §2` 授权流程）；
   - (b) 授权改但**不重算**（会触发 `check-spec-readonly` 红 —— 不可取）；
   - (c) **不授权** ⇒ `spec/Toolchain-01` 保留旧路径（Phase B 引不同步，须缩范围）。
2. **`contracts/*.yaml` 内嵌旧路径字段如何处置**：`abi.yaml` 的 `contract:`（`:30`）/`detail_contract:`（`:59`）为**机器读取值**。选项：
   - (a) **同批改**新路径（**与「内容不动」冲突，须显式授权**）；
   - (b) **加映射 / 别名**（保留旧字段 + 新增转换层）；
   - (c) **不动**（该 2 字段将指向不存在路径 ⇒ 悬空，须登记 issue）。
3. **只动范围是否扩到 `tools/**` / `components/**` / `tests/**`**：选项：
   - (a) **全扩**（一次改净，含生成器/探针/README）；
   - (b) 仅扩 `tools/**`（生成器面）；
   - (c) **均不扩** ⇒ 引用不同步 ⇒ `check-knowledge-refs`/`check-spec-refs` 悬空红（不可取）。

> **不得臆造用户已授权**：三项**已逐条确认（①a②a③a，2026-10-14）**，落纸见 §用户授权落纸；**授权既得**，`**状态**` 仍 `待开始`（**未开工**），由主会话 `/dispatch`（`AGENTS.md`「下发前预检」照跑）。
> **目标目录复核（2026-10-14 追加）**：上列选项的**目标目录**按 §目标目录变更 = **`.tao/contracts/`**（原为 `contracts/`）。

## 接口规范

- **输入**：`INFRA-070t` §追加范围（下）+ 用户对上述 **3 项**的逐条裁定 + **§目标目录变更**（目标目录 = `.tao/contracts/`）。
- **输出**（`INFRA-070t` §追加范围 + 本任务书 §目标目录变更）：
  1. **11 份 `contract-*.md` 迁入 `.tao/contracts/` 顶层**（**禁**建子目录 ✗；引用**全量同步**，现场 `grep` before/after 计数）。**份数 = 现场实测**（`ls .tao/knowledge/contract-*.md | wc -l`，2026-10-14 architect 实测 = **11**；较 `INFRA-070t` 立项时的 9 份**多 2** = 期间新增 `contract-dynlink.md`〔`SPEC-139t`〕/ `contract-syscall.md`〔`SPEC-138t`〕）⇒ **执行时重测，不写死**。
  2. **命名/格式**：不统一前缀；`.md` **保留 `contract-` 前缀**；`contracts/*.yaml` **不改名、不转 TOML**（保持 YAML）。
  3. **两边 README 互指**：新建 `.tao/contracts/README.md` = **叙述型正文清单**（逐份一句话）+ **一行反向指针**「机器可读投影在 `../../contracts/`」；`contracts/README.md`（仓库根）**来源路径改指 `.tao/contracts/contract-*.md`** + 加一句「**人读契约正文在 `../.tao/contracts/`**」，**保留**分工规则一行（*"扁平锁/清单 → TOML（如 `manifests/*.toml`）；嵌套合约数据 → YAML（本目录）"*）。
  4. **`.tao/contracts/` 三要素**（迁移后须齐备）：① **正文** = 11 份 `contract-*.md`；② **许可** = 随迁**保留的用户授权链留纸**（§待用户裁定项裁定 ①a②a③a + §目标目录变更原话）；③ **`README.md`（新建）**。
     > ⚠ **口径留痕**：「许可」= 主会话派单口径；本仓库**无** `LICENSE`/署名文件惯例 ⇒ **若其意指随附许可文件，执行前须向用户澄清**，**不得自拟** ✗。
  5. **`check-contracts-dir` 白名单门控（守两处）**：`contracts/` 顶层只允许 `*.yaml` / `README.md` / 子目录（`contract-*.md` 项**随迁出作废**）；**`.tao/contracts/` 顶层只允许 `contract-*.md` / `README.md` / 子目录**；白名单外即 **FAIL**；**纳入 L1**。**文件/`make` 目标名建议保留** `check-contracts-dir`（目标名稳定），**检查路径**改 `.tao/contracts/`；若改名 ⇒ 须同步 `Makefile` + `AGENTS.md` 门控清单 + 完成区披露。
  6. **引用检查覆盖扩展（新增硬要求，防"新位置悬空不报"）**——**现场证据（2026-10-14 实测）**：
     - `tools/infra/check_spec_refs.py:612-616`：`--contract-dir` 默认 = `.tao/knowledge` ⇒ **改 `.tao/contracts`**；
     - `tools/infra/check_spec_drift.py:258-261`：`contract_dir = args.contract_dir or knowledge_dir` ⇒ 须**显式改默认/传参**（否则枚举到 0 份 ⇒ 假绿/空转）；
     - `tools/infra/check_knowledge_refs.py`：扫描根 = `AGENTS.md` / `spec/**/*.md` / `.tao/knowledge/**/*.md` / `.tao/tasks/**/*.md` ⇒ **加 `.tao/contracts/**/*.md`**；
     - `tools/infra/check_knowledge_dir.py`：`_ALLOWED_GLOBS = ("contract-*.md",)` ⇒ 迁后**作废**，须清理/改（并披露）。
  7. **`.tao/knowledge/` 侧收尾**：11 份迁出后顶层不再含 `contract-*.md`；`MEMORY.md` 入口指针（`:18`）等**现状指引**同步。
- **约束**：**不改** `spec/`（除裁定 ①a 范围）、`tests/vectors/`、组件补丁（除裁定 ③a 范围）；**不改 `.tao/archive/**`** ✗；**计数不写死**。

## 验收标准

（沿用 `INFRA-070t` §验收 **8–10** + 本次追加 **11–12**，全部以**现场真实输出**为准）

8. **迁入生效**：`.tao/contracts/` 顶层含 **11 份** `.md`（`ls | wc -l` 现场实测）；**旧路径 `.tao/knowledge/contract-*.md` 不再存在**（`ls` 证据）；引用全量同步（`git grep -o` **逐目录** before/after 计数；**非归档**残留 = 0，历史语境/本任务书残留**逐条列理由**）；`check-knowledge-refs` rc=0。
9. **命名/格式未动**：`git diff --name-status` 显示 4 个 `*.yaml` **无 `R`（未改名）**、内容未变（仅 `contract:`/`detail_contract:` 等**字段值/注释**指向新路径）；**两边 README 互指**（`grep` 真实输出：`contracts/README.md` 含 `../.tao/contracts/`；`.tao/contracts/README.md` 含 `../../contracts/`）。
10. **`check-contracts-dir`**：常态 rc=0（**两处**白名单）；注入白名单外文件 ⇒ **FAIL** ⇒ 还原 ⇒ 回绿；**已入 `make check`（L1）**。
11. **门控覆盖扩展（可达 FAIL）**：在 `.tao/contracts/` 内**注入悬空引用** ⇒ `check-spec-refs`（或 `check-knowledge-refs`）**FAIL** ⇒ 还原 ⇒ 回绿；`check-spec-refs`/`check-spec-drift` **实际枚举到 11 份**（非空转，现场输出份数）。
12. **只读锁册同步**：`spec/Toolchain-01-汇编语言.md` + `spec/README.md` 旧路径改新；`manifests/spec-readonly.lock.toml` 的 `sha256` **同一变更内重算回填**；`check-spec-readonly` rc=0。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-071t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；显式 staging（禁 `git add -A`）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动**用户授权后**的范围；越界须披露。
5. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
6. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
7. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
8. **计数不写死**。
9. **不改 `.tao/archive/**`** ✗（历史留痕，182 文件 / 741 处；`git grep` 须显式 `:(exclude)` 并在完成区披露排除范围）。
10. **同号误伤禁止** ✗：同步只替换旧路径串，**不得**顺带改任务号/文件名（归档内 `LLVM-077t`/`SPEC-077t`/`LLVM-081t`/`SPEC-081t` 为同号不同任务）。
11. **`components/**` 仅改注释 ⇒ 不重建**（构建成本规则豁免，理由留证：不改编译输入）；`spec/**` 改动仅限裁定 ①a 范围且属**引用同步**（非语义改动）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 用户授权落纸（2026-10-14，architect 追加；**只追加**）

**用户裁定（2026-10-14，原话 = 「1、a；2、a；3、a」；渠道 = 经主会话问答）**——对应上文 §待用户裁定项 逐条：

| 待裁定项 | 裁定 | 性质 / 备注 |
|---|---|---|
| ① **只读锁册** `spec/Toolchain-01`（`manifests/spec-readonly.lock.toml` 哈希锁册） | **(a) 授权改 + 重算 `sha256`** | 性质 = **引用同步**，**非语义改动** |
| ② **`contracts/*.yaml` 内嵌旧路径字段**（8 处） | **(a) 改字段值指向新路径** | `contract:` / `detail_contract:` 等 |
| ③ **只动范围** | **(a) 扩到 `tools/**` / `components/**` / `tests/**`** | **唯一能闭合**；⚠️ 写明：`components/**` **仅改注释** ⇒ **不重建**（构建成本规则豁免，理由留证） |

**结论**：**授权已得，可执行**（上述 3 项均已逐条裁定）。`**状态**` 仍为 `待开始`（**不改**），由后续执行任务推进。

### 追加裁定（2026-10-14，第二问；architect 追加；**只追加**）

**用户裁定原话（2026-10-14；渠道 = 经主会话问答）**——**原样引录**：
- 「**我改主意了，contracts-*.md改到 .tao/contracts/ 目录下，是不是更合适**」
- 「**同意**」（= 同意 `.tao/contracts/` 方案与主会话列出的做法）

**效力**：**迁移目标目录 `contracts/` ⇒ `.tao/contracts/`**（详见 §目标目录变更）；上文 3 项裁定（①a②a③a）**继续有效**。

**architect 同步点清单（本次落纸，2026-10-14）**：
| 文件 | 同步点 |
|---|---|
| `.tao/tasks/infra/INFRA-071t-…md`（本文件） | H1 目标目录；新增 §目标目录变更、§引用同步范围；§接口规范 输出 1–7；§验收 8–12；§硬约束 9–11（本条追加） |
| `.tao/README.md` | `:12` 删除「**当前活跃 = …**」半句（README **不记录进行中/状态**；模块表已列全部模块） |
| `AGENTS.md` | 目录树 `.tao/` 行注释补「契约」⇒ `（任务/知识/ADR/日志/契约）`；`contracts/` 行**保持**「机器可读合约数据」 |
| `.tao/knowledge/milestones.md` | `INFRA-071t` 流水行/规划区同步新目标目录 + 本条裁定 |

## 审阅记录
