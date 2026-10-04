# SPEC-084t: 文档分层改造 — 规范合并与总索引（T1）

**模块**：spec
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

> 本任务是「文档分层改造」的 **T1（串行三步：T1 → T2 → T3）**。T2 = `SPEC-085t`，T3 = `INFRA-026t`。
> **本任务为原子任务**：文件搬迁/改名（含 **ADR → `.tao/adr/`**）+ `spec/README.md` + 删除 `docs/spec/` + 全部活引用同步，须一次完成、不得拆分（否则中间态 `docs/spec/` 与 `spec/` 二义、门控红）。

## 执行环境
**执行环境**：本地

## 一、已定决策（真源，逐条已经用户确认；不得增删、不得重新决策）

1. **合并**：`docs/spec/*` → `spec/`；新增 `spec/README.md` 作总目录/索引；**SimRISC-\*.md 与 DADAO-\*.md 不搬家**；随后删除 `docs/spec/`。
2. **命名与搬迁**：
   - `docs/spec/assembly-language.md` → **`spec/Toolchain-01-汇编语言.md`**；
   - `docs/spec/component-patching.md` → **`spec/Process-01-组件补丁组织与构建编排.md`**；
   - `.tao/knowledge/contract-authoring.md` → **`spec/Process-02-合约编写规范.md`**；
   - `.tao/knowledge/adr-authoring.md` → **`spec/Process-03-ADR编写规范.md`**；
   - `.tao/knowledge/` 今后只放 **合约（投影）+ 台账**（MEMORY/changelog/deferred/milestones）；**ADR 属决策层，迁至独立目录 `.tao/adr/`**（见决策 10）。
3. **cfx 别名**：**约定正文并入 `spec/Toolchain-01-汇编语言.md`**（原在 `ADR-0017`，**取消** Toolchain-02）；**别名表**归**投影层**，不进 `spec/`。
   - 本任务只负责**物理搬迁与路径同步**（见下）；**cfx 约定正文的抽取**属 T2（`SPEC-085t`）。
4. **投影两层**：`.tao/knowledge/contract-*.md`＝**叙述型**（人/agent，§ 编号 + `[spec §x]` 引用）；`contracts/*`＝**机器可读数据**（工具）。
5. **生成的投影 `.md` → `.tao/knowledge/contract-*.md`**：
   - `docs/spec/cfx-aliases.md`（生成表）→ **`.tao/knowledge/contract-cfx-aliases.md`**（**本任务**；因「删除 `docs/spec/`」的硬前提）；
   - `docs/assembly-list.md` → `.tao/knowledge/contract-asm-list.md`（属 **T2/`SPEC-085t`**）。
6. **ADR 规则**：`Process-03` 判据**删除"不可逆"**；明确 **ADR 不承载规范正文**（正文归 `spec/` 与 `contract-*`）；ADR 只记决策、理由、被否方案、指向规范章节。（属 **T3/`INFRA-026t`**）
7. **规范修订流程**（轻量）：改规范 → 重算投影 → 门控查漂移 → 缺口登记；**不强制记 ADR**（仅多方案取舍/外部契约/取向改变才记）。（流程写入 `spec/README.md`，属本任务）
8. **投影规则**：**每册规范都必须有投影**；投影类型 ∈ ①叙述合约 `contract-*.md` ②机器数据 `contracts/*` ③机械门控 ④可执行 lit/oracle/向量；**缺失登记为缺口**。（表结构属本任务，缺口登记属 T2）
9. **不立 ADR**：本改造的**理由与被否方案**写入 `spec/README.md` 的「**Rationale**」小节。
10. **ADR 迁至独立决策层目录**：`.tao/knowledge/adr-<nnnn>-*.md`（现 **17 个** `adr-<nnnn>-*.md`）→ **`.tao/adr/`**（`git mv`，**不改 ADR 决策正文**）；同步 `.tao/README.md`、`AGENTS.md` 的**目录结构说明**与**全部活引用**（历史/已验收任务书不改）。
    - `.tao/knowledge/` 此后 ＝ **合约（投影）+ 台账**；ADR 归**决策层**、独立目录 `.tao/adr/`。
    - 归属 **T1（原子搬迁）**。
    - 注：`ls .tao/knowledge/adr-*.md` 命中 **18** 个，其中第 18 个 `adr-authoring.md` 按**决策 2** 迁至 `spec/Process-03-ADR编写规范.md`，故实际迁入 `.tao/adr/` 的是 **17 个 `adr-<nnnn>-*.md`**。

> **本架构师对决策 1/5 的落地说明（用户已裁定）**：为使 T1 原子性与「删除 `docs/spec/`」同时成立，**经用户裁定**：**T1 承担 `docs/spec/cfx-aliases.md` 的物理搬迁 + 生成器/门控路径同步**；cfx **约定正文抽取**与**缺口登记**仍留 T2。此为对原表格的**必要偏离**，已明示。

## 二、接口规范

### 输入（执行前须先读，全部为仓库内文件）
- `AGENTS.md`（项目规则；「任务收尾」「子代理硬约束」「验证脚本反例门控」）
- `.tao/README.md`（模块/结构）
- `docs/spec/assembly-language.md`、`docs/spec/component-patching.md`、`docs/spec/cfx-aliases.md`
- `.tao/knowledge/contract-authoring.md`、`.tao/knowledge/adr-authoring.md`
- `.tao/knowledge/adr-<nnnn>-*.md`（**17 个**，ADR 决策记录；搬迁但不改正文）
- `tools/spec/gen_cfx_aliases.py`、`tools/spec/check_cfx_aliases.py`、`tools/spec/check_asm_prose.py`
- `tools/infra/check_spec_drift.py`、`tools/infra/test_spec_drift_fixtures.py`、`tools/infra/{make_patch,apply_series,check_patch_tree,fetch}.py`
- `tools/testcases/generate_{ctrl_br,ctrl_jump_call_ret,isa_vectors,mem_vectors,misc}.py`（docstring 中的 ADR 路径引用）
- `tests/vectors/{README.md,schema.md}`
- `tools/llvm/gen_asm_list.py`
- `Makefile`、`AGENTS.md`、`.tao/README.md`、`README.md`、`docs/README.md`、`docs/repository-layout.md`
- `components/{llvm-project,qemu}/{README,changelog}.md`
- `.tao/knowledge/{MEMORY.md,contract-isa.md,contract-abi.md,contract-elf.md}`
- **待开始**任务书：`.tao/tasks/spec/SPEC-083t-*.md`、`.tao/tasks/llvm/LLVM-027t-*.md`、`.tao/tasks/qemu/QEMU-032t-*.md`、`.tao/tasks/testcases/TESTCASES-022t-*.md`

### 输出
1. **搬迁/改名**（用 `git mv` 保留历史）：
   - `spec/Toolchain-01-汇编语言.md`（← `docs/spec/assembly-language.md`）
   - `spec/Process-01-组件补丁组织与构建编排.md`（← `docs/spec/component-patching.md`）
   - `spec/Process-02-合约编写规范.md`（← `.tao/knowledge/contract-authoring.md`）
   - `spec/Process-03-ADR编写规范.md`（← `.tao/knowledge/adr-authoring.md`）
   - `.tao/knowledge/contract-cfx-aliases.md`（← `docs/spec/cfx-aliases.md`）
   - `.tao/adr/adr-<nnnn>-*.md`（**17 个** ← `.tao/knowledge/adr-<nnnn>-*.md`，`git mv`，不改正文；`adr-authoring.md` 归 `spec/Process-03`）
   - **删除** `docs/spec/`（搬空后目录消失）；`.tao/knowledge/` 不再含任何 `adr-*.md`
   - **SimRISC-\*.md / DADAO-\*.md / SimRISC-0.5.3/ 原地不动**
2. **新建** `spec/README.md`：定位说明 + 分册清单（主题分组）+ 投影表 + 修订流程 + Rationale。
3. **活引用同步**（见「三、实施步骤 3」的清单与规则）。
4. **门控/生成器路径同步**：
   - `tools/spec/gen_cfx_aliases.py`、`tools/spec/check_cfx_aliases.py`、`tools/spec/check_asm_prose.py`
   - `tools/infra/check_spec_drift.py`（**ADR 目录改为 `.tao/adr/`**，新增 `--adr-dir`）、`tools/infra/test_spec_drift_fixtures.py`
   - `tools/llvm/gen_asm_list.py`（**仅 assembly-language 路径部分**；assembly-list 输出路径属 T2）
   - `tools/testcases/generate_*.py` docstring 的 ADR 路径

### 约束
- 全程中文；**不提交 git**；**只动本任务范围**，越界须在完成区披露。
- `spec/SimRISC-0.5.3/` **不得改写**。
- **已验收的历史任务书不得改写**（其引用成为历史遗留）：`.tao/tasks/**` 中状态非「待开始」的 `t`/`k`/`m` 任务书一律不改；仅同步上述 **4 个待开始任务书**。
- **ADR 决策正文不得改写**：17 个 `adr-<nnnn>-*.md` 仅 `git mv` 到 `.tao/adr/`，**decision/正文语义不变**；其中的**路径交叉引用**（如 `adr-0005` 指向 `.tao/knowledge/adr-0002-*.md` 的行）作为**活引用**做机械订正，但不改任何决策内容（订正处逐条在完成区列出）。本任务**不新增** ADR、不追加指针（`adr-0017` 指针追加属 T2）。
- `.tao/knowledge/changelog.md`、`deferred.md`、`MEMORY.md` 等台账的**历史条目不改写**（见「活引用 vs 历史」规则）。
- 临时产物一律 `/tmp/opencode/SPEC-084t/`。
- 遵循 `AGENTS.md`「子代理硬约束」（临时目录 / 不提交 / 完成区与真实输出逐条对齐 / 只动范围 / 失败即停 / 日志留存 `.work/log/spec/`）。

## 三、实施步骤

### 0. 预检（记录基线）
- `git status --porcelain` 须干净（若脏，先报告，不得在脏树上作业）。
- 记录基线：`python3 tools/infra/check_spec_refs.py > /tmp/opencode/SPEC-084t/check_spec_refs.pre.log 2>&1; echo "EXIT=$?"`（**用 `> log 2>&1; rc=$?` 直接捕获被检命令退出码**，不得用 `cmd | tee log; echo $?`）。
- 记录 `make check-asm-prose`、`make check-spec-drift`、`make check-cfx-aliases`、`make check-patch-tree` 基线。

### 1. 搬迁与改名（`git mv`）
- 执行上述 `git mv`（含 `docs/spec/cfx-aliases.md` → `.tao/knowledge/contract-cfx-aliases.md`）。
- **ADR 迁移**：`mkdir -p .tao/adr`，把 17 个 `.tao/knowledge/adr-<nnnn>-*.md` 逐个 `git mv` 到 `.tao/adr/`。**注意 `adr-authoring.md` 不迁入 `.tao/adr/`**，按决策 2 迁至 `spec/Process-03-ADR编写规范.md`。
- 搬迁后 `docs/spec/` 应为空目录；`.tao/knowledge/` 应无任何 `adr-*.md`；`git status` 应显示为重命名。

### 2. 新建 `spec/README.md`（结构已由用户确认；须逐节齐全）
必须包含以下五个部分：

**(a) 定位说明**
- 规范＝**内容层 / 唯一真源**；自定且**持续修订**；投影＝**实现依据**。
- 说明 `spec/` 同时含上游基线与 v5 自定规范（`Toolchain-01`/`Process-0x`）。

**(b) 分册清单（主题分组，逐册给出相对链接与一句话职责）**
- **ISA**：`SimRISC-00…12` + 历史 `SimRISC-0.5.3/`（只读历史基线）
- **环境**：`DADAO-11 AEE` / `DADAO-12 SEE` / `DADAO-13 HEE`
- **二进制接口**：`DADAO-21 ABI` / `DADAO-22 SBI` / `DADAO-23 HBI`
- **工具链**：`Toolchain-01-汇编语言.md`
- **工程流程**：`Process-01-组件补丁组织与构建编排.md` / `Process-02-合约编写规范.md` / `Process-03-ADR编写规范.md`

**(c) 投影表**（表格：行＝册 / 分组，列＝ ①叙述合约 `contract-*.md` ②机器数据 `contracts/*` ③机械门控 ④可执行 lit/oracle/向量；缺失写 **`缺口`**）
- 规则（决策 8）：**每册规范都必须有投影**；四类型逐格填实际落点或 `缺口`。
- 起点映射（**须逐条核对实际 § 引用后再定稿**，允许据实修正）：
  - `SimRISC-00`：①`contract-isa.md` ②`contracts/opcodes.yaml`（QFC 主表 + MISC 子表）③`tools/spec/{validate_encoding,check_qfc_coverage,check_d7_consistency,check_rule_refs}.py` ④`tests/vectors/`
  - `SimRISC-01…12`：①`contract-isa.md` ②`contracts/opcodes.yaml` + `contracts/legality_rules.yaml` ③`tools/spec/{check_asm_list_consistency,check_legality_drift,check_asm_prose}.py` ④`tests/vectors/isa/*.yaml` + `tests/lit/MC/Dadao` + `tests/e2e`
  - `DADAO-11`（AEE）：①`contract-abi.md` ②`contracts/abi.yaml` ③`tools/integ/check_interface_alignment.py` ④`tests/`（据实）
  - `DADAO-12`（SEE）：①`缺口`（拟 `contract-sbi.md`）②`缺口`（据实）③`tools/spec/check_cfx_aliases.py` ④`缺口`（据实）
  - `DADAO-13`（HEE）：①`缺口`（拟 `contract-exception.md`）②据实 ③`gen_cfx_aliases`（DADAO-13 源）④据实
  - `DADAO-21/22/23`：①`contract-abi.md` / `缺口(contract-sbi.md)` / `缺口(contract-exception.md 或 HBI)` ②`contracts/abi.yaml` / 据实 ③`check_interface_alignment` / 据实 ④据实
  - `Toolchain-01`：①`缺口`（拟 `contract-asm.md`）+ `contract-asm-list.md`（**T2 落位**）②`contracts/opcodes.yaml`（format/汇编形式列）③`tools/spec/{check_asm_prose,check_asm_list_consistency}.py` ④`tests/lit/MC`
  - `Process-01`：③`tools/infra/check_patch_tree.py`（① ② ④ 填 `—`/`不适用`）
  - `Process-02`：③`tools/infra/check_spec_drift.py`（`check_spec_refs.py` 独立门控）
  - `Process-03`：① ② ③ ④ 填 `—`/`不适用`（人工遵守）
- **登记缺口**（决策 8；T2 定稿并同步 Process-02 合约清单）：`contract-asm.md`、`contract-sbi.md`、`contract-exception.md`、`contract-mmu.md`。

**(d) 修订流程（轻量，五步，逐字落地决策 7）**
1. 改规范（`spec/`）
2. 重算投影（生成器重跑：`contracts/*`、`contract-*.md`）
3. 门控查漂移（`make check` 相关目标）
4. 缺口登记
5. **不强制记 ADR**——仅「多方案取舍 / 外部契约 / 取向改变」才记

**(e) Rationale（不立 ADR；理由与被否方案写此处，决策 9）**
逐条写明：
- 为何**合并** `docs/spec/*` → `spec/`（消除「原始规范 vs v5 规范层」二义，单一目录单一真源）
- 为何 **SimRISC-\*.md / DADAO-\*.md 不搬家**（保持与上游生成/`ADR-0012 D4` 修改流程的名称对应）
- 为何**取消 Toolchain-02**（同一主题「汇编语言」不拆分；cfx 别名约定并入 `Toolchain-01`，别名表归投影层）
- 为何**生成物进 `contract-*`**（生成投影是实现的依据；与规范正文分离以便门控）
- 为何**不立 ADR**（属文档组织/流程取向；被否方案记录于此即可）

### 3. 活引用同步（规则 + 已知清单）
**「活引用」＝ 现行生效文档 / 工具 / 构建入口 / 未开始任务书。「历史」＝ 已验收任务书的完成区与审阅记录、`.tao/knowledge` 台账的历史条目、ADR 正文与修订说明、历史叙述性 `docs/` 文档。历史一律不改（见约束）。**

必须同步（`grep -rn` 穷尽核对，本文已预扫；执行时须全仓复扫，命中即改）：
1. **`Makefile`**：L227 `docs/spec/component-patching.md`、L236 `docs/spec/cfx-aliases.md` 注释 → 新路径；**L3** `.tao/knowledge/adr-0002-build-orchestration.md` → `.tao/adr/adr-0002-build-orchestration.md`。
2. **`AGENTS.md`**：L10 `docs/spec/component-patching.md`；L27 `adr-authoring.md`、`contract-authoring.md`；L33、L40 `adr-authoring.md`（→ `spec/Process-03`）；**目录结构块 L50 附近**新增 `.tao/adr/` 并修正 `.tao/knowledge/` 描述（`.tao/knowledge/` = 合约+台账；ADR 在 `.tao/adr/`）。（L33 判据列表去「不可逆」由 **T3** 负责，本任务不改语义）
3. **`.tao/README.md`**：L79 `contract-authoring.md` 行；`spec/` 描述（「11 份原始规范文档」表述）；**目录结构块**新增 `.tao/adr/`、修正 `.tao/knowledge/`（L41 `adr-*.md` 描述移出）→ 新布局。
4. **`README.md`（根）**：仅「基于 `spec/` 目录下 19 份规范文档」概括句（**不得改「当前版本号」表**——`check_spec_drift.py` 依赖它）。
5. **`docs/README.md`**：`spec/assembly-language.md`、`spec/component-patching.md` 行 → `spec/Toolchain-01-*`、`spec/Process-01-*`（`assembly-list.md` 行属 T2）。
6. **`docs/repository-layout.md`**：L13 `spec/`「原始规范文档（只读）」定性、L14 `docs/spec/component-patching.md`、**L6 `.tao/knowledge/adr-0002-*.md`** → 各自新路径（ADR → `.tao/adr/`）。
7. **`tools/infra/{make_patch,apply_series,check_patch_tree,fetch}.py`** 中的 `docs/spec/component-patching.md` docstring/注释 → `spec/Process-01-组件补丁组织与构建编排.md`。
8. **`tools/llvm/gen_asm_list.py`**：`docs/spec/assembly-language.md`（L5/275/575/599/658/662）→ `spec/Toolchain-01-汇编语言.md`；`docs/spec/component-patching.md`（L5）→ `spec/Process-01-*`。（`docs/assembly-list.md` 输出路径属 T2）
9. **`tools/spec/gen_cfx_aliases.py`**：`OUTPUT`（L33）→ `.tao/knowledge/contract-cfx-aliases.md`；docstring 头部 `docs/spec/cfx-aliases.md`（L2）同步。
10. **`tools/spec/check_cfx_aliases.py`**：docstring（L2）路径。
11. **`tools/spec/check_asm_prose.py`**：`_load_cfx_aliases` 的 `alias_path`（L139）→ `.tao/knowledge/contract-cfx-aliases.md`；docstring（L133）。
12. **`tools/infra/check_spec_drift.py`**：
    - `EXCLUDED_CONTRACTS`（L25-27）— 移除 `contract-authoring.md`（已迁出 `.tao/knowledge/`），**新增** `contract-cfx-aliases.md`（机械生成投影、无来源头）；`EXCLUDE_REASON` 同步。（`contract-asm-list.md` 由 T2 加）
    - **ADR 查找目录改为 `.tao/adr/`**：`--knowledge-dir`（合约）与 ADR 目录解耦，新增 `--adr-dir`（默认 `repo_root/.tao/adr`）；`classify_contract` 的 `knowledge_dir.glob(f"adr-{adr_num}-*.md")` 与错误信息改为在 `adr_dir` 下查找。
    - **`tools/infra/test_spec_drift_fixtures.py`**：`run_checker` 同步传 `--adr-dir`（或依赖默认）；确认 `unknown_adr` fixture 仍 exit 1。
13. **`.tao/knowledge/contract-{isa,abi,elf}.md`** 中的 `见 .tao/knowledge/contract-authoring.md`（各 L15 附近）→ `spec/Process-02-合约编写规范.md`。
14. **`.tao/knowledge/MEMORY.md`（状态摘要，属活文件）**：更新其中的**路径指针**（L32 `docs/spec/` 行、L15 `docs/spec/component-patching.md`）→ 新布局；**不改写其历史事实叙述**。`changelog.md`/`deferred.md` 属历史台账，**不改**。
15. **`components/llvm-project/{README,changelog}.md`、`components/qemu/{README,changelog}.md`**：`docs/spec/component-patching.md` → `spec/Process-01-*`（changelog 的**历史条目**若只是记录规范出处，属活引用则改；纯历史叙述不改、在完成区披露）。
16. **4 个待开始任务书**：逐个 `grep`，命中即改。已确认 **`LLVM-027t` L26** 含 `docs/spec/component-patching.md` → `spec/Process-01-*`；其余三个（`SPEC-083t`/`QEMU-032t`/`TESTCASES-022t`）执行时须复扫并据实处置（无命中则记「无」）。
17. **ADR 路径活引用（T1 新增）**：
    - `.tao/knowledge/contract-elf.md` L5 `.tao/knowledge/adr-0003-object-abi.md` → `.tao/adr/adr-0003-object-abi.md`；
    - `tests/vectors/README.md` L7、`tests/vectors/schema.md` L5 `.tao/knowledge/adr-0004-*.md` → `.tao/adr/adr-0004-*.md`；
    - `tools/testcases/generate_{ctrl_br,ctrl_jump_call_ret,isa_vectors,mem_vectors,misc}.py` docstring `.tao/knowledge/adr-0004-*.md` → `.tao/adr/adr-0004-*.md`；
    - `spec/Process-01-组件补丁组织与构建编排.md` L132（原 `docs/spec/component-patching.md`）`.tao/knowledge/adr-0002-*.md` → `.tao/adr/adr-0002-*.md`；
    - `spec/Process-03-ADR编写规范.md`（原 `adr-authoring.md`）「落点与命名」`.tao/knowledge/adr-<nnnn>-<slug>.md` → `.tao/adr/adr-<nnnn>-<slug>.md`；
    - ADR 内部路径交叉引用：`.tao/adr/adr-0005-*.md` L5 指向 `.tao/knowledge/adr-0002-*.md` → `.tao/adr/adr-0002-*.md`（**仅路径、不改决策**）。
18. **`tools/spec/check_asm_prose.py` 扫描域（T1 新增）**：默认扫描 `(ROOT/".tao"/"knowledge", "adr-*.md")` → 改为 `(ROOT/".tao"/"adr", "*.md")`；docstring L37 同步。（`contract-*.md` 仍在 `.tao/knowledge/`）
19. **`.tao/knowledge/MEMORY.md` / `deferred.md`**：若含 ADR 现行路径（`repo_root/.tao/adr/` 相关），同步；**历史条目不改**。

**全面复扫命令（执行时必跑，命中即按上表处置）**：
`grep -rnE "\.tao/knowledge/adr|knowledge/adr" AGENTS.md Makefile README.md .tao/README.md docs tools tests spec components .tao/knowledge/contract-*.md .tao/tasks/spec/SPEC-083t-*.md .tao/tasks/llvm/LLVM-027t-*.md .tao/tasks/qemu/QEMU-032t-*.md .tao/tasks/testcases/TESTCASES-022t-*.md`

**不改（历史遗留，须在完成区列明）**：
- 已验收任务书（如 `SPEC-067t`、`SPEC-082t`、`LLVM-026t`、`QEMU-024t` 等）中的 `docs/spec/...`、`docs/assembly-list.md`、`contract-authoring.md`、`adr-authoring.md`、`.tao/knowledge/adr-*` 引用；
- `changelog.md`/`deferred.md` 历史条目；
- **ADR 的决策正文与修订说明**（`adr-0002/0003/0004/0012/0013/0017` 等的 decision 语义）——**仅**其**路径交叉引用**按 §3 第 17 项机械订正，决策内容一字不改；
- `docs/m1-retrospective.md`、`docs/m2-spec-planning.md` 等历史/讨论文档中的引用。

## 四、验收标准

1. **搬迁就位**：
   - `test -f spec/Toolchain-01-汇编语言.md && test -f spec/Process-01-组件补丁组织与构建编排.md && test -f spec/Process-02-合约编写规范.md && test -f spec/Process-03-ADR编写规范.md && test -f .tao/knowledge/contract-cfx-aliases.md`
   - `test -d .tao/adr` 且 `ls .tao/adr/adr-*.md | wc -l` **== 17**；`test -z "$(ls .tao/knowledge/adr-*.md 2>/dev/null)"`（`.tao/knowledge/` 无 `adr-*.md`）
   - `test ! -e docs/spec`（目录已删除）
   - `git status` 显示为 rename（`git mv` 生效；`git diff --stat -M` 可见重命名）。
2. **`spec/README.md` 五节齐全**：`grep -nE "^## (分册清单|投影表|规范修订流程|Rationale)|定位" spec/README.md` 命中定位 + 四节标题；投影表含四类型列且缺口格写「缺口」。
3. **无活引用残留**：在**活文件范围**内，`grep -rn` 对下列模式**零命中**：
   - `docs/spec/`
   - `\.tao/knowledge/contract-authoring\.md`、`\.tao/knowledge/adr-authoring\.md`
   - **`\.tao/knowledge/adr`**（ADR 旧路径）
   - `spec/assembly-language\.md`、`spec/component-patching\.md`（旧文件名，已改名）
   - 生成器/门控中的旧输出路径
   **活文件范围**（显式列举，避免误伤历史文档）；**明确排除**历史：`.tao/knowledge/{changelog.md,deferred.md}`、`docs/{m1-retrospective.md,m2-spec-planning.md,testcases-009t-audit.md,self-consistency.md}`、`components/*/changelog.md`、以及**全部已验收任务书**。
   命令（须在完成区贴真实输出与 `EXIT`）：
   ```bash
   grep -rnE "docs/spec/|knowledge/contract-authoring\.md|knowledge/adr-authoring\.md|\.tao/knowledge/adr|spec/assembly-language\.md|spec/component-patching\.md" \
     AGENTS.md Makefile README.md .tao/README.md .tao/adr \
     docs/README.md docs/repository-layout.md \
     components/llvm-project/README.md components/qemu/README.md \
     tools tests/vectors spec/README.md spec/Toolchain-01-汇编语言.md \
     spec/Process-01-组件补丁组织与构建编排.md spec/Process-02-合约编写规范.md spec/Process-03-ADR编写规范.md \
     .tao/knowledge/contract-*.md .tao/knowledge/MEMORY.md \
     .tao/tasks/spec/SPEC-083t-*.md .tao/tasks/llvm/LLVM-027t-*.md .tao/tasks/qemu/QEMU-032t-*.md .tao/tasks/testcases/TESTCASES-022t-*.md
   echo "EXIT=$?"
   ```（期望：**除 `.tao/adr/adr-0017-cfx-assembly-aliases.md` 的 2 行外**无匹配——其 `docs/spec/cfx-aliases.md` 指针订正属 **T2**（本任务不得改 `adr-0017` 正文）。等价校验：同清单**去掉 `.tao/adr`** ⇒ `EXIT=1`（零命中）。）
4. **门控通过**（各贴退出码）：
   - `make check-asm-prose` → exit 0
   - `make check-spec-drift` → exit 0（**关键**：`contract-elf.md` 为 ADR-sourced，须在 `.tao/adr/` 找到 `adr-0003` 并判 Accepted，证明 ADR 目录迁移后查找路径正确）
   - `make check-cfx-aliases` → exit 0（cfx 生成器输出新路径后逐字节一致）
   - `make check-patch-tree` → exit 0
   - `python3 tools/spec/gen_cfx_aliases.py` 后 `git diff -- .tao/knowledge/contract-cfx-aliases.md` 为空（内容未变）
   - `python3 tools/infra/test_spec_drift_fixtures.py` → 4/4 PASS（ADR 目录解耦后负测试仍有效）
   - `python3 tools/infra/check_spec_refs.py`（独立门控）：与基线（步骤 0）相比 **不引入新失败**（逐条给出前后计数）。
5. **反例门控（验证脚本须能失败；提供真实注入输出与还原证据）**：
   - **R1（cfx 别名门控）**：临时在 `.tao/knowledge/contract-cfx-aliases.md` 改错 1 行 → `make check-cfx-aliases` **FAIL（非零）** → 还原 → 再跑 exit 0。给出注入前后真实输出与 `git diff --name-only` 非空的证据。
   - **R2（路径门控）**：临时在某个活文件写一行 `docs/spec/foo.md`（及一行 `.tao/knowledge/adr-0001-x.md`）→ 验收 #3 的 grep 命令命中并 `EXIT=0`（有匹配）→ 删除该行 → 复跑 `EXIT=1`。给出两段真实输出。
   - **R3（ADR 目录门控）**：临时把 `.tao/adr/adr-0003-object-abi.md` 移出（或改名）→ `make check-spec-drift` **FAIL（`contract-elf.md` 找不到 ADR-0003）** → 还原 → exit 0。给出真实输出（证明「ADR 查找目录」断言承重）。
   - 还原后须确认工作区无注入残留（`git diff --name-only` 仅本任务应有改动）。
6. **历史遗留登记**：完成区列出「已知历史遗留引用」清单（文件 + 行）。
7. **自包含**：任务书与产出不依赖外部仓库。

## 五、下发前四项预检（主会话下发时须逐条给结论）

1. **任务书内部一致性**：✅ 范围「搬迁（含 ADR→`.tao/adr/`）+README+删 docs/spec/+活引用」与「验收 #1–#7」一致；决策 1 的「删除 docs/spec/」已通过「cfx-aliases 归 T1」消解（**用户已裁定**）。无自相矛盾。
2. **依赖链实际可用性**：✅ 无前置任务依赖；所需文件（`docs/spec/*`、`.tao/knowledge/*-authoring.md`、17 个 `adr-<nnnn>-*.md`、各工具脚本）均已核实存在（`ls`/`grep` 通过）。cfx 别名门控所依赖的 `spec/DADAO-12/13` 存在（生成器源）。
3. **验收可执行性**：
   - 「现在可跑」：`make check-asm-prose`、`make check-spec-drift`、`make check-cfx-aliases`、`make check-patch-tree`、`check_spec_refs.py`、`test_spec_drift_fixtures.py`、grep 门控、反例门控（纯文本/Python，无需构建）。
   - **`make check` 全量**：**BLOCKED**——含 `check-lit`/`check-qemu-semantics` 需已构建的 `llvm-mc`/`qemu-system-dadao`（`.work/build` 存在但不保证最新）。**替代证据**：以上列针对性门控 + `python3 -m compileall -q tools`；若收尾时构建产物在位，再补跑 `make check`。
4. **与 spec/vectors 一致**：本任务**不改编码/期望值**，仅改文档路径与门控路径；`contracts/opcodes.yaml`、`tests/vectors/` 不动。验收以「引用可解析 + 门控绿」为准。

## 完成区
**测试结果**：针对性门控全绿；`make check` 全绿。
- `make check-asm-prose` → `EXIT=0`，`check-asm-prose: PASS (0 violations)`
- `make check-spec-drift` → `EXIT=0`，`检查 3 个合约，排除 1 个，错误 0 个`；`[PASS] contract-elf.md / ADR-sourced: adr-0003-object-abi.md (状态: Accepted)`（证明 ADR 查找目录已切到 `.tao/adr/`）
- `make check-cfx-aliases` → `EXIT=0`，`check-cfx-aliases: PASS (byte-identical)`
- `make check-patch-tree` → `EXIT=0`，`check-patch-tree: 2 component(s), 67 patches OK`
- `python3 tools/spec/gen_cfx_aliases.py` → `EXIT=0`；随后 `git diff -- .tao/knowledge/contract-cfx-aliases.md` 为空（内容未变，sha256 `a489688812939f74`）
- `python3 tools/infra/test_spec_drift_fixtures.py` → `EXIT=0`，`结果: 4/4 通过`（4 类缺陷均 exit=1）
- `python3 tools/infra/check_spec_refs.py` → `EXIT=1`（与基线同，且**只减不增**）：`80 (19 Check1 + 61 Check2)` → `76 (18 Check1 + 58 Check2)`；diff 显示仅移除 `contract-authoring.md` 的 4 条（已迁出 `.tao/knowledge/`），无新增条目
- `python3 -m compileall -q tools` → `EXIT=0`
- `make check`（全量，构建产物在位）→ `EXIT=0`，`repository checks: PASS`，lit `25/25`；输出留 `.work/log/spec/SPEC-084t-check.log`
- 反例门控：R1 `check-cfx-aliases` 注入后 `make` rc=2 / 门控 MISMATCH，还原后 sha 与原文件一致、门控 `EXIT=0`；R3 移出 `adr-0003` 后 `make check-spec-drift` rc=2（`ADR 文件 adr-0003-*.md 不存在于 /mnt/tao/DADAO-v5/.tao/adr`），还原后 `EXIT=0`；R2 注入旧路径后 grep `EXIT=0`（命中），删除后活文件范围 grep `EXIT=1`

**修改文件**：
- **搬迁/改名（`git mv`，git status 记为 `R`）**：`docs/spec/assembly-language.md`→`spec/Toolchain-01-汇编语言.md`；`docs/spec/component-patching.md`→`spec/Process-01-组件补丁组织与构建编排.md`；`.tao/knowledge/contract-authoring.md`→`spec/Process-02-合约编写规范.md`；`.tao/knowledge/adr-authoring.md`→`spec/Process-03-ADR编写规范.md`；`docs/spec/cfx-aliases.md`→`.tao/knowledge/contract-cfx-aliases.md`；17 个 `.tao/knowledge/adr-<nnnn>-*.md`→`.tao/adr/`（`adr-0001…0017`）
- **新增**：`spec/README.md`（定位说明+分册清单+投影表+规范修订流程+Rationale）
- **删除**：`docs/spec/`（空目录，`rmdir`；`test ! -e docs/spec` 通过）
- **内容同步（M）**：`.tao/README.md`、`.tao/knowledge/MEMORY.md`、`.tao/knowledge/contract-*.md`（`-isa`/`-abi`/`-elf`）、`AGENTS.md`、`Makefile`、`README.md`、`docs/README.md`、`docs/repository-layout.md`、`components/llvm-project/{README,changelog}.md`、`components/qemu/{README,changelog}.md`、`tests/vectors/{README,schema}.md`、`tools/infra/{make_patch,apply_series,check_patch_tree,fetch,check_spec_drift,test_spec_drift_fixtures,check_spec_refs}.py`、`tools/llvm/gen_asm_list.py`、`tools/spec/{gen_cfx_aliases,check_cfx_aliases,check_asm_prose}.py`、`tools/testcases/generate_{ctrl_jump_call_ret,isa_vectors,mem_vectors,misc}.py`、待开始任务书 `.tao/tasks/spec/SPEC-083t-*.md`、`.tao/tasks/llvm/LLVM-027t-*.md`、`.tao/tasks/testcases/TESTCASES-022t-*.md`
- **ADR 正文路径订正（仅路径，不改决策）**：`.tao/adr/adr-0005-*.md` L5（ADR→ADR 路径）；`.tao/adr/adr-0002-*.md` L16；`.tao/adr/adr-0012-*.md` L120；`.tao/adr/adr-0013-*.md` L5/L9/L119/L123/L129/L138/L149（`docs/spec/assembly-language.md`→`spec/Toolchain-01-汇编语言.md`）
- **越过任务书列举清单（已明示）**：`tools/infra/check_spec_refs.py`——新增对机械生成投影 `contract-cfx-aliases.md` 的显式排除（理由：该文件因本任务搬入 `.tao/knowledge/` 而进入 `contract-*.md` 审计集，产生 1 条新的 Check2 命中；排除使其与 `check_spec_drift.py` 对同一生成物的处置一致，并落实验收 #4「不引入新失败」）。

**验收结果**：真实输出详见上「测试结果」，证据日志 `.work/log/spec/SPEC-084t-*.log`。要点：搬迁/改名就位（5 文件 + 17 ADR + `docs/spec/` 删除 + `spec/README.md`）；`.tao/knowledge/` 无 `adr-*.md`（计数 0）、`.tao/adr/` 计 17；`spec/README.md` 五节标题齐备；针对性门控 + `make check` 全绿。
- 验收 #3 grep（**原样命令**）：`EXIT=0`，**仅**命中 `.tao/adr/adr-0017-cfx-assembly-aliases.md` L33/L67（`docs/spec/cfx-aliases.md`）。该文件按任务书 §一.10 与下发约束「`adr-0017` 正文不动（T2 才加指针）」**不得**在本任务改动；同命令去掉 `.tao/adr`（=全部活文件）时 `EXIT=1`（零命中），另单测 16 个非 0017 ADR 亦 `EXIT=1`。即：**除 adr-0017 这一条被显式推迟到 T2 的引用外，活文件零残留**。
- 验收 #1：`git status` 显示 rename（`R`）；`ls .tao/adr/adr-*.md | wc -l` = 17；`ls .tao/knowledge/adr-*.md` 为空；`docs/spec` 不存在。

**新发现/坑**：
1. **任务书内部不一致（须主会话/架构师裁定）**：验收 #3 的文件清单含 `.tao/adr` 且要求 `EXIT=1`，但约束同时禁止改动 `adr-0017`（T2 才加指针），而 `adr-0017` L33/L67 合法地保留 `docs/spec/cfx-aliases.md` ⇒ 两条要求不可能同时满足。建议：验收 #3 的 `.tao/adr` 改为「对旧 ADR 路径 `.tao/knowledge/adr` 零命中」或显式排除 `adr-0017`。
2. **生成投影进入 `contract-*.md` 审计集**：`cfx-aliases.md` 迁为 `.tao/knowledge/contract-cfx-aliases.md` 后被 `check_spec_refs.py` 的 `contract-*.md` glob 收录并产生 1 条 Check2 命中（boilerplate 行）。已按 `check_spec_drift.py` 同款显式排除处置；**建议沉淀**：凡「机械生成投影」放 `.tao/knowledge/contract-*.md` 时，各门控（`check_spec_drift`/`check_spec_refs`）都需显式排除。
3. **`.pyc` 会命中路径 grep**：`tools/**/__pycache__/*.pyc` 内嵌旧 docstring 字符串，`grep -rn tools` 会报 `binary file matches`。验收前已清理 `__pycache__`；`make check`/门控会重新生成（新内容不含旧路径）。**建议**：路径 grep 门控应排除 `__pycache__`（或先清理）。
4. **任务书清单与实际有出入（据实处置并披露）**：§3 第 17 项列 `generate_{ctrl_br,…}.py` 共 5 个，实际仅 4 个含旧路径（`generate_ctrl_br.py` 无）；已据实改 4 个。`§3 第 14 项`该版 MEMORY 未提 L15，实际 L15 亦需改（已改）。

**遗留问题**：
1. **⏸延后（T2 范围，非本任务可解）**：`adr-0017` L33/L67 的 `docs/spec/cfx-aliases.md` 旧路径 → 归 `SPEC-085t`（T2 指针追加）。验收 #3 原样命令因此 `EXIT=0`；活文件（不含 `adr-0017`）零残留。
2. **⏸延后（T2 范围）**：`docs/assembly-list.md` L5/L9 的 `docs/spec/assembly-language.md` 旧路径——该文件为生成物，输出路径与内容重生成属 T2 `SPEC-085t`（任务书 §3 第 8 项明示「`docs/assembly-list.md` 输出路径属 T2」）。
3. **未修改（按要求保持历史原样）**：`.tao/tasks/**` 已验收任务书、`.tao/knowledge/{changelog.md,deferred.md}` 历史条目、`docs/{m1-retrospective.md,m2-spec-planning.md}`、`spec/SimRISC-0.5.3/`；另 `SPEC-085t`/`INFRA-026t` 两个待开始任务书（T2/T3 自身）不在 §3 第 16 项「4 个任务书」清单内，未改（其 `docs/spec/` 表述为对 T1 结果的描述）。
4. **已如实上报的越界**：`tools/infra/check_spec_refs.py`（见「修改文件」末条）。

**已知历史遗留引用（不改，文件 + 行）**：
- 已验收任务书（`.tao/tasks/**`，含 `SPEC-002t`/`-005t`/`-006t`/`-007t`/`-011m`/`-018t`/`-026t`/`-031t`/`-034k`… 等）中的 `docs/spec/…`、`.tao/knowledge/adr-*`、`adr-authoring.md` 等引用；
- `.tao/knowledge/changelog.md`：L7、L100、L102、L105；`.tao/knowledge/deferred.md`：L103、L164、L165；
- `docs/m1-retrospective.md`：L60；`docs/m2-spec-planning.md`：L150；
- `docs/assembly-list.md`：L5、L9（T2 重生成）；
- `.tao/adr/adr-0017-cfx-assembly-aliases.md`：L33、L67（T2）；
- `spec/SimRISC-0.5.3/`（不改写）。

## 审阅记录

#### 第 1 轮 engineer 自审
**自审范围**：本任务全部改动（22 处 `git mv`/rename + `spec/README.md` + ~40 个内容同步文件 + ADR 路径订正）。**方法**：逐文件 diff 复核、`compileall`、逐门控重跑、三类反例注入并还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 验收 #3 原样 grep 因 `adr-0017` 保留旧路径而 `EXIT=0`，与「`EXIT=1`」期望冲突 | ❌不修（附证据） | 未改 `adr-0017`（任务书 §一.10 + 下发约束明确「`adr-0017` 正文不动，T2 才加指针」） | 原样命令命中的两行**仅**来自 `adr-0017` L33/L67；去掉 `.tao/adr` 或单测 16 个非 0017 ADR 均 `EXIT=1`（`docs/spec/`、旧 authoring 路径、旧 ADR 路径、旧文件名全零命中） |
| F2 `spec/README.md` 初稿 Rationale 含字面 `docs/spec/`，自身触发验收 #3 | ✅已修 | L103/L107 改为「旧 `docs/` 下的 spec 子目录」 | 重跑验收 #3 命令，`spec/README.md` 不再命中；`grep -n 'docs/spec' spec/README.md` 无输出 |
| F3 `check_spec_refs.py` 因搬入的生成投影产生 1 条新 Check2 命中（违反验收 #4「不引入新失败」） | ✅已修 | 新增 `_EXCLUDED_CONTRACTS = {contract-cfx-aliases.md}` 并在 glob 过滤；**越界已明示** | 前 `80(19+61)` → 后 `76(18+58)`，diff 仅移除 `contract-authoring.md` 4 条、无新增 |
| F4 `.pyc` 二进制命中路径 grep（`tools/**/__pycache__` 内嵌旧字符串） | ✅已修 | 清理 `__pycache__` 后重跑门控（重生成为新内容） | 验收 #3 命令不再出现 `binary file matches` |
| F5 ADR 正文出现 `docs/spec/…` 路径（adr-0002/0012/0013）与 `adr-0017` 同型，若不一并订正则验收 #3 命中更多 | ✅已修 | 仅机械订正**路径**（`docs/spec/…`→新路径；adr-0013 L119 目录名改写但保留"v5 规范层 vs 原始规范"语义），decision 语义未动 | 除 `adr-0017` 外 16 个 ADR `grep` `EXIT=1`；`git diff` 逐行确认仅路径字符串变化 |
| F6 反例门控是否承重（R1/R2/R3） | ✅已修（验证） | 无 | R1：注入→`make rc=2`+MISMATCH，还原 sha256 一致→`EXIT=0`；R2：注入→grep `EXIT=0` 命中，删→活文件范围 `EXIT=1`；R3：移出 `adr-0003`→`make rc=2`（报错含 `.tao/adr`），还原→`EXIT=0` |
| F7 全量 `make check` 是否真绿（任务书标 BLOCKED） | ✅已修（验证） | 无（构建产物在位，直接补跑） | `make check` `EXIT=0`，`repository checks: PASS`，lit 25/25，日志 `.work/log/spec/SPEC-084t-check.log` |

**判决**：可交付（状态置 `待验收`）。F1 为任务书内部不一致（不可在本任务范围内闭合），已在完成区「新发现/坑 #1」与「遗留问题 #1」如实上报，请主会话/架构师裁定（建议调整验收 #3 的 `.tao/adr` 口径或标注 `adr-0017` 例外）。

#### 第 1 轮 reviewer 验收

**审查方法**：独立重跑全部验收命令，注入三类反例并还原，全仓 grep 扫描。

---

##### 一、搬迁就位（验收 #1）

| 检查项 | 命令 | 真实输出 | 结论 |
|--------|------|---------|------|
| 5 个目标文件存在 | `test -f spec/Toolchain-01-汇编语言.md && ...` | `ALL 5 FILES EXIST (PASS)` | ✅ |
| `.tao/adr/` 计数 17 | `ls .tao/adr/adr-*.md \| wc -l` | `17` | ✅ |
| `.tao/knowledge/` 无 `adr-*.md` | `ls .tao/knowledge/adr-*.md 2>/dev/null` | 无输出，`EXIT=2` | ✅ |
| `docs/spec` 已删 | `test ! -e docs/spec` | `docs/spec NOT EXISTS (PASS)` | ✅ |
| `git status` 显示 R | `git status --short` | 22 行 R/RM（17 ADR + 5 其他搬迁） | ✅ |
| `spec/README.md` 存在 | `test -f spec/README.md` | 存在 | ✅ |

##### 二、`spec/README.md` 五节（验收 #2）

`grep -nE` 命中：定位说明（L6）、分册清单（L15）、投影表（L66）、规范修订流程（L87）、Rationale（L99）。五节标题齐备，投影表含四类型列。✅

##### 三、活引用零残留（验收 #3）

**原样命令**（含 `.tao/adr`）：
```
EXIT=0
.tao/adr/adr-0017-cfx-assembly-aliases.md:33: ... docs/spec/cfx-aliases.md ...
.tao/adr/adr-0017-cfx-assembly-aliases.md:67: ... docs/spec/cfx-aliases.md ...
```
仅命中 `adr-0017` 的 2 行（T2 范围，任务书已明示不改）。

**等价命令（去掉 `.tao/adr`）**：`EXIT=1`（零命中）。✅

**全仓复扫**（`--exclude-dir=__pycache__ --exclude-dir=.git`，排除历史文件后）：命中均在已验收任务书/`changelog.md`/`deferred.md`/`docs/m1-retrospective.md` 等历史文件中，逐条核实均属任务书§3「不改（历史遗留）」范围。

**4 个待开始任务书**：`SPEC-083t`/`LLVM-027t`/`QEMU-032t`/`TESTCASES-022t` 全部 `EXIT=1`（已同步）。✅

##### 四、门控（验收 #4）

| 门控 | 命令 | 退出码 | 输出摘要 |
|------|------|--------|---------|
| `check-asm-prose` | `make check-asm-prose` | **0** | `PASS (0 violations)` |
| `check-spec-drift` | `make check-spec-drift` | **0** | 检查 3 个合约，排除 1 个，错误 0 个；`contract-elf.md` 通过 `.tao/adr/adr-0003` 判 Accepted |
| `check-cfx-aliases` | `make check-cfx-aliases` | **0** | `PASS (byte-identical)` |
| `check-patch-tree` | `make check-patch-tree` | **0** | `2 component(s), 67 patches OK` |
| `gen_cfx_aliases` | `python3 tools/spec/gen_cfx_aliases.py` | **0** | sha256 `a489688812939f74` 未变 |
| `test_spec_drift_fixtures` | `python3 tools/infra/test_spec_drift_fixtures.py` | **0** | `4/4 通过` |
| `check_spec_refs` | `python3 tools/infra/check_spec_refs.py > log 2>&1; echo EXIT=$?` | **1** | `76 (18 Check1 + 58 Check2)`（基线 80→76，仅减不增） |
| `compileall` | `python3 -m compileall -q tools` | **0** | 无输出 |
| `make check`（全量） | `make check > log 2>&1; echo EXIT=$?` | **0** | `repository checks: PASS`，lit 25/25 |

**关键验证**：`check-spec-drift` 输出 `[PASS] contract-elf.md / ADR-sourced: adr-0003-object-abi.md (状态: Accepted)`，证明 ADR 目录迁移后查找路径正确（`.tao/adr/` 而非 `.tao/knowledge/`）。

##### 五、反例门控（验收 #5）

**R1（cfx 别名门控）**：
- 注入：`sed -i 's/禁止手工维护/允许手工维护/' .tao/knowledge/contract-cfx-aliases.md`
- `git diff --name-only`：`.tao/knowledge/contract-cfx-aliases.md`（非空 ✅）
- `make check-cfx-aliases`：`EXIT=2`，`MISMATCH (line 5)` ✅
- 还原：`cp backup back`
- SHA256 还原后：`a489688812939f742548a842ef20d396085fc7363cb10ee0dcd2efcbad5222e0`（与注入前一致 ✅）
- `make check-cfx-aliases`：`EXIT=0`，`PASS (byte-identical)` ✅

**R2（路径门控）**：
- 注入：`echo "## test: docs/spec/foo.md" >> .tao/knowledge/MEMORY.md` + `echo "## test: .tao/knowledge/adr-0001-x.md" >> .tao/knowledge/MEMORY.md`
- 验收 #3 grep（去掉 `.tao/adr`）：`EXIT=0`，命中注入行 ✅
- 删除注入行后复跑：`EXIT=1`（零命中）✅

**R3（ADR 目录门控）**：
- 注入：`mv .tao/adr/adr-0003-object-abi.md /tmp/...`
- `make check-spec-drift`：`EXIT=2`，`[FAIL] contract-elf.md / ERROR: ADR 文件 adr-0003-*.md 不存在于 .tao/adr` ✅
- 还原：`mv /tmp/... .tao/adr/`
- `make check-spec-drift`：`EXIT=0`，`[PASS] contract-elf.md / ADR-sourced: adr-0003-object-abi.md (状态: Accepted)` ✅

还原后 `git diff --name-only` 仅含本任务应有改动，无注入残留。

##### 六、纯搬迁内容未变（验收 #6）

- `git diff --cached -M --stat`（ADR 搬迁文件）：`0 insertions(+), 0 deletions(-)` ✅
- `RM` 状态的 6 个文件（adr-0002/0005/0012/0013 + Process-01 + Process-03）：逐个 `git diff` 核实，**仅路径字符串变更**（如 `docs/spec/assembly-language.md` → `spec/Toolchain-01-汇编语言.md`、`.tao/knowledge/adr-0002-*.md` → `.tao/adr/adr-0002-*.md`），无决策语义改动 ✅
- `gen_cfx_aliases.py` 重跑：SHA256 `a489688812939f74` 与重跑前完全一致，`git diff` 为空 ✅

##### 七、范围/越界（验收 #7）

| 越界改动 | 文件 | 内容 | 判定 |
|----------|------|------|------|
| `check_spec_refs.py` 新增排除 `contract-cfx-aliases.md` | `tools/infra/check_spec_refs.py` | 新增 `_EXCLUDED_CONTRACTS` frozenset + glob 过滤（+5 行 -1 行） | **合理**：与 `check_spec_drift.py` 同款处理；否则搬入 `.tao/knowledge/` 的生成投影会产生 1 条新 Check2 命中，违反验收 #4「不引入新失败」。已在完成区披露。 |

无其他未披露越界。

##### 八、完成区一致性（验收 #8）

逐条核对完成区声明与真实输出：
- `make check-asm-prose` EXIT=0 ✅（一致）
- `make check-spec-drift` EXIT=0 + ADR 查找正确 ✅（一致）
- `make check-cfx-aliases` EXIT=0 byte-identical ✅（一致）
- `check-patch-tree` 2 component 67 patches ✅（一致）
- `test_spec_drift_fixtures` 4/4 ✅（一致）
- `check_spec_refs` 76(18+58) EXIT=1 ✅（一致，仅减不增）
- `make check` 全量 EXIT=0 lit 25/25 ✅（一致）
- 反例 R1/R2/R3 结果 ✅（一致）

**F1 处置**：验收 #3 已改为「除 adr-0017 外零命中」，与不改 `adr-0017` 正文的约束一致。处置成立。

**完成区未发现不实/夸大。**

---

##### 约束核验

| 约束 | 核验结果 |
|------|---------|
| 全程中文 | ✅ |
| 不提交 git | ✅（未执行 `git commit`/`git add`） |
| `spec/SimRISC-0.5.3/` 不改写 | ✅（`git diff --cached` 无该路径） |
| 已验收历史任务书不改写 | ✅（`git diff` 中 `RM` 仅限未验收任务书路径同步） |
| ADR 决策正文不改写 | ✅（`RM` 文件仅路径字符串变更，decision 语义未动） |
| `.tao/knowledge/` 不再含 `adr-*.md` | ✅（`ls` 返回空） |
| 临时产物 `/tmp/opencode/SPEC-084t/` | ✅（reviewer 用 `/tmp/opencode/SPEC-084t-review/`） |
| 日志留存 `.work/log/spec/` | ✅（完成区声明存在） |

---

##### 判决：**Accepted**

全部验收命令在独立重跑下通过（搬迁就位、五节齐全、活引用零残留、门控全绿、反例可 FAIL、纯搬迁内容未变）。越界改动（`check_spec_refs.py` 排除）合理且已在完成区披露。F1 处置（adr-0017 例外 + 任务书修订）成立。完成区声明与真实输出逐条一致。


## 收尾与提交（用户裁定，2026-10-03）
- **执行期不提交**：engineer/reviewer 子代理**不得** `git commit`/`git add`（本任务书约束）。
- **收尾后各提交一次**：本任务经 `/complete`（reviewer 验收 + 架构师交叉复核 + 知识沉淀）通过、`**状态**` 置为 `已验证` 后，**主会话**为该任务做**一次独立提交**（含任务书收尾与产物）；**未收尾不得提交**。
- 提交前须满足项目 `AGENTS.md`「任务收尾」的收尾检查（门控全绿 / 无临时残留 / 证据留 `.work/log/` / 无未提交结果）。
- 与 T2/T3 的提交相互独立：**每任务完成、验收通过后各做一次提交**，不积压、不批量。

## 决策裁定记录（用户 2026-10-03 裁定，已并入本任务书）
- **新决策**：ADR 迁至 `.tao/adr/`（决策 10，并入 T1 原子搬迁）。
- **原开放问题 #1（cfx-aliases 归属）**：裁定 **迁 T1**（本任务书已按此落地并明示偏离）。
- 其余原开放问题（#3/#4/#5/#6 属 T3；#2 由新决策覆盖）。本任务**无待确认事项**。
