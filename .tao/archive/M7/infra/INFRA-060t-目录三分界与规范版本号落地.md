# INFRA-060t: 目录三分界与规范版本号落地（**草案形态，含待用户裁定项**）

**模块**：infra
**项目里程碑**：M7
**依赖**：无（同改 `AGENTS.md` / `Makefile` / `spec/` / `tools/` ⇒ 与 `INFRA-056t` / `INFRA-057t`、`SPEC-131t` **串行**）
**状态**：已验证

> **草案声明**：本任务书为 architect 依用户 2026-10-11 裁定**起草的草案**；**A 段**（搬迁 / 删除 / 索引重建）可进入实现，**B 段**（两册版本号 + changelog + 下游同步）**须用户逐条确认后方可写入**（见 §B 与「待用户裁定清单」）。

## 执行环境
**执行环境**：本地

## 用户裁定（2026-10-11，原话要点，**原样落纸**）

> 1. **三分界**：`spec/` = 上游基线（`SimRISC-*` / `DADAO-*`）+ v5 自定**技术规范**（`Toolchain-01` / `Machine-01`）；**`docs/` = 工程流程规范（`Process-0x`）+ 索引 + `DDLN/`**；`.tao/knowledge/` = 结论 / 设计 / 口径。
> 2. **`docs/` 给别人看；`.tao/knowledge/` 给自己看**（agent / 主会话）——作为**主判据**。
> 3. **`.work/log/` 不是默认落点**（放进去 = 随时可丢弃）⇒ 落 `AGENTS.md` 规则。
> 4. `Process-0x` **迁入 `docs/`**；`Process` **不设版本号**。
> 5. **`Toolchain-01` 与 `Machine-01` 需要版本号**：`x.y.z`，**x=0**；**大改动 y+1、有影响的小改 z+1**；**changelog 放文末**——**不用表格**、**不写“依据”**，形式为「**版本 + 日期**作小标题 + 列表写每条变更」。
> 6. `docs/` 内 6 个过期文件**可删**（「你确定没用就可以删」）；其余逐一商量。

## 接口规范

### 输入（已核实事实，直接采用；**计数以现场为准、不写死**）

- **`Process-0x` 引用面（活文件）**：`AGENTS.md`；`Makefile`（help + 注释）；**7 个 `tools/**` 脚本**（`infra/{apply_series,check_patch_tree,check_spec_readonly,fetch,make_patch,size_report}.py`、`llvm/gen_asm_list.py`、`testcases/validate_m5_vectors.py`）；6 个 `.tao/knowledge/contract-*.md`；`issues.yaml` / `lessons.md` / `MEMORY.md`；`manifests/spec-readonly.lock.toml`（**注释**）；`spec/README.md`；`docs/{README,repository-layout}.md`；`spec/Process-04/05/06` 自身内部的 `spec/Process-0x` 交叉引用；`components/*/{README.md,changelog.md,*.patch}`（补丁文本内引用，**须评估是否改**）；`tests/**` 附注。**`spec/Process-` 形态引用全仓实测 ~453**（其中**绝大多数在 `.tao/archive/**`**，按 `lessons §5.3` **不改写历史**）。
- **6 个待删文件的活引用（现场实测）**：
  - `docs/impact-matrix.md` ← `.tao/knowledge/issues.yaml`（`ISS-160` 已记其悬空）+ `docs/README.md`；
  - `docs/m2-spec-planning.md` ← `.tao/knowledge/MEMORY.md` + `.tao/knowledge/lessons.md`（历史条款）+ `docs/README.md`；
  - `docs/integ-interface-alignment.md` ← `.tao/knowledge/MEMORY.md` + `docs/README.md`；
  - `docs/spec-065t-legality-proposal.md` ← **`tools/spec/check_scope.py` `HISTORY_PREFIXES`**；
  - `docs/testcases-009t-audit.md`、`docs/self-consistency.md` ← **`tools/spec/check_asm_prose.py` `_EXCLUDE_FILES`**（该集合**还含已失效的 `docs/m1-retrospective.md`**——该文件已归档 `.tao/archive/M1/`，须一并清）。
- **保留项**：`docs/fp-oracle-design.md`（**不在**删除名单；被 `spec/README.md` 投影表 + `contract-fp.md` + `contracts/fp_semantics.yaml` 引用）⇒ **不删**；`docs/repository-layout.md` 另行商量（见裁定清单）。
- **两册现状（现场实测）**：
  - `spec/Toolchain-01-汇编语言.md:3` 状态行含 `v1.1`（2026-09-25 定稿；修订 2026-09-28 双目的 / 多寄存器）；
  - `spec/Machine-01-测试机运行环境.md:3` **无版本号**；
  - 两册**均在** `manifests/spec-readonly.lock.toml` 的 `sha256` 锁内 ⇒ 改册须 `Process-06 §2` 用户授权 + **同一变更内**更新锁；
  - 下游 `.tao/knowledge/contract-asm.md:5` 头部 `版本：1.1`；`README.md`（根）「当前版本号」表 `Toolchain = 1.1`（`check-spec-drift` 机械比对两者）。
- **`check_asm_prose` 扫描面（现场实测，**先证后改**）**：`tools/spec/check_asm_prose.py` 扫描 `spec/**/*.md` **与** `docs/**/*.md`（均含）⇒ `Process-0x` **迁入 `docs/` 前后同在扫描面内**、对 asm-prose 门控**中性**；仅 `check_spec_codeblocks.py` 只扫 `spec/`（`Process-0x` 无 ```simrisc 块，无影响）。**仍要求**：搬迁**前 / 后**各跑一次 `make check-asm-prose`（或 `make check`）留证（当前基线 `check-asm-prose: PASS (0 violations)` rc=0）。
- **规则**：`AGENTS.md`「文档分层与单一真源」/「验证脚本反例门控」；`spec/Process-06 §2/§5`；`lessons §5.3`（不改写历史）、`§8.55`（被引用材料不得只放 `.work/`）。

### 输出——**A 段（可直接实现）**

1. **`Process-0x` 全量搬迁** `spec/Process-0[1-6]-*.md` → `docs/Process-0[1-6]-*.md`（保留文件名；用 `git mv` 保留 rename 历史）；**`Process` 不设版本号、不加 changelog**。
2. **全部引用同步**（活文件，**除** `.tao/archive/**`）：`AGENTS.md`、`Makefile`、7 个 `tools/**` 脚本 docstring/注释、6 个 `contract-*.md`、`issues.yaml`/`lessons.md`/`MEMORY.md`、`manifests/spec-readonly.lock.toml` 注释、`spec/README.md`、`docs/{README,repository-layout}.md`、被搬迁文件**自身内部**的 `spec/Process-0x` 交叉引用、`docs/README.md` 内各链接基址。`components/**` 补丁文本 / `tests/**` 附注是否同步须先判定（见裁定清单）。
3. **6 个过期文件删除**：`git rm` 上列 6 文件；同步两处脚本常量：
   - `tools/spec/check_scope.py` `HISTORY_PREFIXES` 删 `docs/spec-065t-legality-proposal.md`；
   - `tools/spec/check_asm_prose.py` `_EXCLUDE_FILES` 删 `docs/testcases-009t-audit.md`、`docs/self-consistency.md`，并清已失效的 `docs/m1-retrospective.md`；同步该文件 docstring 中的扫描面说明。
4. **`docs/README.md` 重建**：成为 **`DDLN/` + `Process-0x` 的索引**（删去 6 文件条目；更新 `spec/Process-*` 指针为 `docs/Process-*`；`repository-layout.md` 条目视裁定）。
5. **`spec/README.md` 更新**：分册清单「工程流程」6 行与投影表 `Process-01/02/03/05/06` 行——去 `Process` 行**或**改指针为 `docs/Process-0x`（二选一，须与「`spec/`＝技术规范」口径一致）；`spec/` 改动须授权（见约束②）。
6. **`AGENTS.md` 更新**：写入三分界口径——「`docs/` = 工程流程规范 + 索引 + `DDLN/`，**给别人看**」「`.tao/knowledge/` = 结论/设计/口径，**给自己看**（agent/主会话）」「**`.work/log/` 不是默认落点**」；并据三分界更新「文档分层与单一真源」四分类（`spec/` = 上游基线 + v5 技术规范；`docs/` = 工程流程规范 + 索引 + `DDLN/`）与「目录结构」块（增 `docs/`）。

### 输出——B 段（**须用户逐条确认后才写**）

1. **两册册头版本行**：`Toolchain-01` 改为 `0.x.y` 形态；`Machine-01` **新增**版本行。**changelog 放文末**——**不用表格、不写“依据”**，形式为「**版本 + 日期**作小标题 + 列表写每条变更」（见下「版本号回推草案表」）。
2. **写入前置**：`Process-06 §2` 用户授权原话落纸 + **同一变更内**更新 `manifests/spec-readonly.lock.toml` 两册 `sha256`。
3. **下游版本同步**：
   - `Toolchain-01` → `.tao/knowledge/contract-asm.md` 头部 `版本：1.1` + **根 `README.md`**「当前版本号」表 `Toolchain` 行（`check-spec-drift` 机械比对，**不同步即 `make check` 红**）；
   - `Machine-01` → 若要求下游 `contract-*` 版本行标注，则须**新增**根 `README.md` 版本表 `Machine` 行 **且** 扩展 `tools/infra/check_spec_drift.py` 的 `SPEC_PREFIX_TO_COMPONENT` / `SPEC_PREFIX_TO_FILENAME`（`Machine-01`）——**此项为代码改动，须单独裁定**（见裁定清单）。

### 约束

- **只动 A 段范围**；B 段**未确认前不得写入册头**（`spec/` 一字不改，留 `BLOCKED` 说明）；越界须披露。
- **改 `spec/` 须用户事先授权**（`Process-06 §2`）：A 段以用户 **2026-10-11 裁定 #4** 为依据，**授权原话落纸**；B 段另需授权。
- **两册在 `sha256` 锁内**；`Process-0x` / `spec/README.md` **不在**锁内（仍受 §2 授权流程约束）。
- **计数 / 条数不写死**（引用数、文件数一律现场 `grep`/`ls` 产出）。
- 临时目录 `/tmp/opencode/INFRA-060t/`；**不提交 git**；**禁** `git add -A` / `git add .`；**禁** `git checkout`/`restore`/`stash`（还原用 `cp` 备份 + md5 对账，或临时树注入）。

## 版本号回推草案表（**B 段；每行均「待用户逐条确认」**）

> 说明：**回推来源** = 两册 git 历史（`git log --follow`）+ 在办 / 已归档任务书 + `ADR-0013` / `ADR-0020` / `ADR-0004` + `manifests/spec-readonly.lock.toml` 变更注释。**版本号分类（x=0；大改 y+1 / 小改 z+1）与日期均须逐条裁定**；下表为**提案**，非已定。

### Toolchain-01（现册头 `v1.1`）

| 版本（提案） | 日期 | 变更 | 来源 |
| --- | --- | --- | --- |
| `0.1.0` | 2026-09-25 | 初版定稿（词法/记号/寻址/寄存器组/条件/格式类语法/伪指令与指导符/诊断/往返） | 原 `v1.1` 状态行；`ADR-0013` |
| `0.2.0` | 2026-09-28 | 双目的 `{reg,reg}` / 多寄存器组语法（**大改动**） | `SPEC-036t`（原「v1.1 修订」） |
| `0.2.1` | 2026-09-29 | cfx 系列记法约定 | `SPEC-053t` |
| `0.2.2` | 2026-10-02 | 迁移新汇编格式；术语 `cfxcode`→`cfxha`；注释符 `#`→`;` | `SPEC-078t`、`LLVM-024t`（`ADR-0013 D9`） |
| `0.2.3` | 2026-10-05 | 规范/文档一致性清理 | `SPEC-102t` |
| `0.3.0` | 2026-10-06 | 伪指令集收缩（`ADR-0013 D11`）；删 `illi`、`fence`→0x00、`swym`→0x22（**大改动**） | `SPEC-106t`、`SPEC-109t` |
| `0.3.1` | 2026-10-08 | §2.1 大小写敏感；§1 格式类口径 | `SPEC-116t` |
| `0.3.2` | 2026-10-09 | §6.1 `set.fo` 口径；`ABS48` 数据 8B | `SPEC-123t` |
| `0.4.0` | 2026-10-09 | 旧口径消除（§5 `scope: excluded` 格式列表收窄；§13 cfx 归属改 m1/excluded；§11/§12 移出为指针；去写死计数）（**大改动**） | `SPEC-129t` |
| `0.5.0` | 2026-10-10 | §7 重写：数据指示符唯一集（`.dd.b08/.dd.w16/.dd.t32/.dd.o64`）+ §7.2 对齐指示符（只留 `.p2align`）；禁 `.byte/.short/.long/.quad/.word/.octa` 与 `.align`（**大改动**） | `SPEC-130t` |
| `？`（本任务） | 2026-10-11 | 册头版本行改 `0.x.y` + 文末 changelog（**语义不变**） | 本任务 |

> **未列入上表**（同触该册、判定为纯文档搬运/派生，建议**不单独开版本**，待裁定）：`SPEC-039t`（fence 移出 M1，2026-09-29）、`SPEC-057t`（删 `rela.si`，2026-09-30）、`SPEC-067t`（删 `ftlog/folog`，2026-10-01）、`SPEC-082t`（D3/D10，2026-10-03）、`SPEC-086t`（FP scope，2026-10-03）、`SPEC-084t`/`SPEC-085t`/`INFRA-027t`（文档分层，2026-10-03）、`LLVM-025t`（`#` 非法，2026-10-02）、`INFRA-032t` 台账搬迁（2026-10-04）。

### Machine-01（现**无**版本号）

| 版本（提案） | 日期 | 变更 | 来源 |
| --- | --- | --- | --- |
| `0.1.0` | 2026-10-07 | 初版：测试机运行环境与 semihosting 正文（内存映射/复位、运行模式、cfx/权限、`trap`/`escape`/异常进入、semihosting 25 服务、加载/bootrom、退出） | `SPEC-114t`；`ADR-0020`/`ADR-0004` |
| `0.1.1` | 2026-10-08 | §1 越界路由 / RAM@0 容量口径 | `SPEC-121t` |
| `0.2.0` | 2026-10-09 | semihosting 返回寄存器统一 `rd8`（§5.2/§5.4；指针返回 `rb31`→`rb8`）（**大改动**） | `SPEC-126t` |
| `0.2.1` | 2026-10-09 | §1.1 RAM@0 唯一 RAM 段（删旧 RAM 段 + exit-port；§5.5/§7 记 exit-port 已删） | `QEMU-053t` |
| `？`（本任务） | 2026-10-11 | 册头版本行 + 文末 changelog（**语义不变**） | 本任务 |
| （M7，未落地） | — | RAM 基址改 `0xFC00_0000_0000`（cfx63 段） | `QEMU-056t`（`ADR-0004` 就地修订） |

## 待用户裁定清单（**须逐条回答后方可写 B 段**）

1. **版本回推草案逐条确认**：上两表每行「版本 / 日期 / 变更 / 来源」保留 / 修改 / 否决。
2. **起始版本号**：初版是否为 `0.1.0`（而非把原 `v1.1` 平移为 `0.1.1`）；`v1.1` 与 `0.x.y` 的对应关系。
3. **本任务是否生成新版本条目**：册内**语义不变**（仅加版本行 + 补 changelog）——是否递增（z+1）还是**不递增**（仅补历史条目）。
4. **下游同步范围**：`Toolchain` 版本是否随本任务同步根 `README.md` 表 + `contract-asm.md`（涉及 `check-spec-drift`）；`Machine-01` 是否要在根 `README.md` 版本表**新增行**并**扩展 `check_spec_drift.py` 前缀映射**（代码改动）。
5. **A 段 `spec/` 授权口径**：以用户 2026-10-11 裁定 #4（`Process-0x` 迁入 `docs/`）作为 `Process-06 §2` 的**事先授权**是否足够；删除 6 文件 + 改 `spec/README.md` 是否同授权覆盖。
6. **6 文件删除最终确认**（用户「你确定没用就可以删」）：逐个确认；`fp-oracle-design.md` **保留**、`repository-layout.md` 是否保留（其内容含三分界口径，建议保留并更新）。
7. **`Process-06` 正文措辞**：搬迁后 `Process-06 §1/§2/§6/§47 行` 中 `spec/Process-*` 字样是否同步为 `docs/Process-*`（属规范正文改动，须授权范围）——**建议同步**（否则规范与目录自相矛盾）。
8. **在办任务书边界**：`.tao/tasks/**`（`SPEC-131t`/`INFRA-057t` 等）内 `spec/Process-` 引用是否同步——**建议不同步**（任务书 = 记录，按 `lessons §5.3` 不改写历史），据此**验收口径**为「排除 `.tao/archive/**` **与** `.tao/tasks/**` 后 0 命中」。
9. **`components/**` 补丁文本 / `tests/**` 附注**内 `spec/Process-` 引用是否同步（补丁改则须重建镜像/`check-patch-tree`）——**建议同步补丁内引用**（其影响可机械校验），待裁定。
10. **`docs/README.md` 定位**：确认为「`DDLN/` + `Process-0x` 索引」，并作为「给别人看」入口。

## 用户裁定（2026-10-11，主会话下发；**原话原样落纸**）

> 「没看懂，你的A是要把文档退回到历史状态，然后重新升版吗？你的B是当前版是0.1.0吗？首先，我认为你的版本升级的Changelog总结的很好，**但是不用退回到历史状态，直接用新的版本号，然后写清楚Changelog即可**」

**解读**：册正文一字不改（不回退、不动语义）；直接采用回推所得编号作为**当前版本**——`Toolchain-01` 册头 `0.5.0`、`Machine-01` 册头 `0.2.1`；**文末 changelog** 写清完整演进（**不用表格**、**不写「依据」**，形式 =「**版本 + 日期**」作小标题 + 列表）。
**A 段 `spec/` 授权口径**（用户 2026-10-11 裁定 #4 `Process-0x` 迁入 `docs/` +「你确定没用就可以删」原话）**覆盖**：搬迁、6 文件删除、`spec/README.md` 更新。

### 「待用户裁定清单」10 项裁定结果（主会话据用户裁定与建议定）

| # | 裁定 |
|---|------|
| 1 | 按本任务书两张版本回推表执行（Toolchain 当前 `0.5.0`、Machine 当前 `0.2.1`）；表内「变更」经现场 `git log` **复核一致**（无修正） |
| 2 | 起始版本号 = `0.1.0`（**不**把原 `v1.1` 平移为 `0.1.1`） |
| 3 | 本任务**不生成新版本条目**（册内语义不变，仅写版本行 + 补历史 changelog）⇒ 当前版本即 `0.5.0` / `0.2.1` |
| 4 | 下游同步：① `Toolchain` → `contract-asm.md` 头部 + 根 `README.md` 版本表；② `Machine-01` → 根 `README.md` 版本表**新增行** + **扩展** `check_spec_drift.py` 前缀映射（代码改动，须实测） |
| 5 | A 段 `spec/` 授权口径 = 用户裁定 #4 +「你确定没用就可以删」⇒ 覆盖搬迁、6 删除、`spec/README.md` 更新 |
| 6 | 6 文件**全删**；`docs/fp-oracle-design.md` **保留**（被投影表/`contract-fp.md`/`contracts/fp_semantics.yaml` 引用）；`docs/repository-layout.md` **保留并更新** |
| 7 | `Process-06` 正文措辞**同步**为 `docs/Process-*` |
| 8 | `.tao/tasks/**` 内 `spec/Process-` 引用**同步**（活文件）；`.tao/archive/**` 一律不动；本任务书自身**保留**描述所需指代 |
| 9 | `components/**` **普通文件**（README/changelog 等）同步；**补丁文本 `patches/**/*.patch` 一律不动** ⇒ 登记为**遗留** |
| 10 | `docs/README.md` 定位 = 「`DDLN/` + `Process-0x` 索引」，作为「**给别人看**」入口 |

## 验收标准

1. **A 段搬迁**：`git grep -n 'spec/Process-'` 在**活文件**（排除 `.tao/archive/**` 与 `.tao/tasks/**`，见裁定 8）**0 命中**——留**真实 grep 输出 + rc**。
2. **门控**：`make check`（L1）**EXIT=0**（捕获**命令自身**退出码，禁 `cmd | tee` 吞码）；`make check-spec-readonly` **EXIT=0**。
3. **6 文件删除 + 常量同步**：6 文件均不存在（`ls` 真实输出）；`tools/spec/check_scope.py` `HISTORY_PREFIXES` 与 `tools/spec/check_asm_prose.py` `_EXCLUDE_FILES` 已移除失效项（`grep` 真实输出，**含**清 `docs/m1-retrospective.md`）。
4. **`check-asm-prose` 先证后改**：搬迁**前 / 后**各一次 `make check-asm-prose`（或 `make check`）**EXIT=0**（留证，证明迁移对扫描面中性）。
5. **`AGENTS.md` 口径**：含三段——「`docs/` 给别人看」「`.tao/knowledge/` 给自己看」「`.work/log/` 非默认落点」（`grep` 真实输出）+ 四分类更新 + 目录结构含 `docs/`。
6. **`docs/README.md` 重建**：不再指向 6 删除文件；含 `DDLN/` + `Process-0x` 索引（`grep` 真实输出）。
7. **B 段门禁（机械可验）**：**未获用户逐条确认前**，两册册头与文末**不得出现** `0.x.y` 版本行 / changelog——`git grep -n '0\.[0-9]' spec/Toolchain-01*.md spec/Machine-01*.md` 证「未写入」，或给出 `BLOCKED` 说明（授权原话落纸）。
8. **注入反例可失败**：把某活文件引用临时改回 `spec/Process-` ⇒ 验收脚本 / grep 断言 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）；一键证据脚本落 `.work/evidence/<任务ID>/`（**不以 `.work/` 为被引用材料**）。
9. **知识沉淀**：完成后把「新门控上线后，文档/记录里的示例路径必须用 `<>` 占位形态，否则门控自伤」写入 `.tao/knowledge/lessons.md` **§8.5x**（**实测编号 = §8.56**；**≤3 行 + 指针**）。

## 避坑（**强制执行**）

- ① **任务书 / 记录 / 文档中不得出现字面 `.work/<具体路径>` 示例**（一律用 `<>` 占位，如 `.work/log/<模块>/<任务ID>-*.log`）——否则新增门控 `check-knowledge-refs` 判**悬空**、`make check` **自伤**（本项目**已两次踩到**）。
- ② **改 `spec/` 须授权**（`Process-06 §2`）；A 段以用户裁定 #4 为依据、**原话落纸**；B 段另需授权；**未授权而拟改 `spec/` ⇒ BLOCKED**。
- ③ 两册在 `manifests/spec-readonly.lock.toml` `sha256` 锁内 ⇒ 改册**同变更内**更新锁；`Process-0x` / `spec/README.md` 不在锁内但仍受 §2 约束。
- ④ **计数 / 条数 / 引用数不写死**，一律现场 `grep`/`ls` 产出。
- ⑤ 长命令 / 构建按 `AGENTS.md`「长任务」（`setsid nohup` + 落盘标记 + **申报耗时**、`JOBS=8`、禁全核）。

## Wave / 依赖 / 串行

- **同改 `AGENTS.md` / `Makefile` / `spec/` / `tools/` ⇒ 与 `INFRA-056t` / `INFRA-057t`、`SPEC-131t` 串行**（不得与上述任务并行以免同改共享文件）。
- A 段（搬迁 + 删除 + 索引 + `AGENTS.md`）可独立落地；B 段（版本号 + 锁 + 下游同步）**以裁定为前置**，可在 A 段之后单独立项或作为本任务尾段。

## 完成区
**测试结果**：`make check`(L1) rc=0；`make check-spec-readonly` rc=0（21 册 OK）；`check-asm-prose` 搬迁前/后各 rc=0；`check-spec-drift`/`check-scope`/`check-knowledge-refs` rc=0；证据脚本 `.work/evidence/<任务ID>/run.sh` RESULT: PASS（含注入→FAIL→还原→回绿）。
**修改文件**：A 段——`git mv` 6 册 `spec/Process-0[1-6]`→`docs/`；`git rm` 6 过期 docs 文件（impact-matrix/m2-spec-planning/integ-interface-alignment/spec-065t-legality-proposal/testcases-009t-audit/self-consistency）；活引用同步（`spec/Process-`→`docs/Process-`，含 `AGENTS.md`/`Makefile`/8 个 `tools`/6 contracts/补丁外 `components`/`tests`/`adr`/`issues.yaml`/`MEMORY`/`lessons`/在办任务书）；重建 `docs/README.md`；更新 `spec/README.md`、`AGENTS.md`、`docs/repository-layout.md`、`docs/Process-06`；`check_scope.py`/`check_asm_prose.py` 常量清理。B 段——两册册头+changelog、`manifests/spec-readonly.lock.toml` 两册 `sha256`、`.tao/knowledge/contract-asm.md`、根 `README.md`、`check_spec_drift.py`；`lessons.md §8.56`。（全清单见 `git status --short`）
**验收结果**：① 活引用 `git grep 'spec/Process-'`（排除 archive/tasks/patch/本任务书）=**0 命中**（C1）；② 6 文件全删（C2=6/6）；③ 常量清理命中=0（C3）；④ `docs/README.md` 含 `docs/Process-0[1-6]`×6 + `DDLN`×6、无陈旧条目（C4）；⑤ `AGENTS.md` 三分界三句 + 目录含 `docs/`（C5）；⑥ 两册册头 `0.5.0`/`0.2.1` + changelog + 锁 `sha256` 相符（C6：`Toolchain 8bdef34e…`、`Machine f003ac98…`；旧 `3d129ba8…`/`60eb9a04…`）；⑦ 下游 `contract-asm 0.5.0`/README `Toolchain 0.5.0`+`Machine 0.2.1`/`check_spec_drift` 映射（C7）；⑧ 迁移对 asm-prose 扫描面中性（前/后 rc=0）。
**新发现/坑**：① **分支 `INFRA-060t` 下发时并不存在**（实为 `master`）⇒ 按「开工建分支」自建（未改历史、未提交）；② `git grep -l` 对非 ASCII 路径加引号 ⇒ 过滤须 `git -c core.quotepath=false`；③ `check_spec_drift.py` 仅加前缀 dict 不足以让 `Machine-01` 生效，须同时把 `Machine-\d+` 加入 `RE_SPEC_REF`；④ `lessons §8.56`（新门控上线后 `.work/` 示例须 `<>`/`*` 占位）。
**遗留问题**：① `components/**/patches/**/*.patch` 内 2 处 `spec/Process-` 未同步（裁定 9：补丁文本一律不动 ⇒ 随下次该组件补丁重建顺带改）；② `ISS-160` 的「impact-matrix 悬空」子项因文件已删而消解，未改 issue 正文（另两项仍开放）；③ 越界披露：为自洽另改了根 `README.md` 第 3 行 Process-0x 指代 + `spec/README.md` 的 `Process-02/06` 无前缀指代（属 A 段引用同步同域）。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：A 段（搬迁/引用/删除/常量/索引/AGENTS）+ B 段（两册册头/changelog/锁/下游）。自主逐行审查。
- 搬迁 `git mv`，`git status` 显 `R`（保留 rename）；04/05/06 为 `RM`（rename+自引用改写），符合预期。
- 纯替换文件 `git diff` 逐行核对：`+/-` 行**全部**含 `Process-`（除特意重写的 `docs/Process-06 §2` 措辞）。
- 锁：两册新 `sha256` 与工作树实测一致；`check-spec-readonly` 21 册 OK。
- 门控实测：`make check` rc=0；`Machine-01` 映射用临时 fixture 验证 PASS→(改错版本)FAIL→还原 PASS。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 证据脚本 C6 用 `grep -A1` 取 sha256 命中 `group` 行 ⇒ 误报 mismatch | ✅已修 | `run.sh` C6 改按 `[[spec]]` 块配对 path→sha256（awk） | 重跑 C6「相符=yes」，RESULT: PASS |
| F2 `docs/Process-06 §2`「spec/ 目录下…含 docs/Process-*」语法矛盾 | ✅已修 | 改为「（含 …）；以及工程流程规范 `docs/Process-*` 的同类改动——均必须…」 | `make check` rc=0 |
| F3 仅加两 dict 不足以让 `Machine-01` 漂移校验生效（`RE_SPEC_REF` 不含 `Machine-\d+`） | ✅已修 | `RE_SPEC_REF` 增 `Machine-\d+` | fixture 实测映射生效 |
| F4 分支不存在（下发前提有误） | ✅已处置 | 自建 `INFRA-060t` 分支 | `git branch --show-current`=INFRA-060t |

#### 第 1 轮 reviewer 验收

**独立验证**（reviewer，本轮全部命令由 reviewer 亲自执行）。

**门控**：
- `make check` rc=0 ✓；`make check-spec-readonly` rc=0（21 册 OK）✓；`make check-asm-prose` rc=0 ✓

**A 段核验**：
- `git grep 'spec/Process-'`（排除 archive/tasks/patch）rc=1（0 命中）✓；`*.patch` 残留 2 处（裁定 9 保留，已登记遗留）✓
- 6 文件全删（`ls` 确认）✓；`check_scope.py`/`check_asm_prose.py` 常量已清（grep 无残留）✓
- `git mv` R/RM rename 保留 ✓；`docs/README.md` 重建（Process×6+DDLN，无陈旧条目）✓
- `spec/README.md`：工程流程行已去 + "归 `docs/`" 注释 ✓；`AGENTS.md` 三分界三句 + 目录 docs/ ✓

**B 段核验**：
- 两册 sha256 独立重算 = lock 值（Toolchain `8bdef34e…`、Machine `f003ac98…`）✓；锁 diff 仅 2 册哈希 + 注释改，其余 19 册未动 ✓
- 册头：Toolchain `0.5.0`、Machine `0.2.1` ✓；changelog 格式 = "### 版本（日期）"+ 列表，无表格/无"依据" ✓
- `git diff -M` 两册：**仅**册头版本行 + 文末 changelog 新增，册正文一字不改 ✓
- 版本回推逐条复核（10+4 条）：每条变更/日期与 `git log --follow` + ADR-0013/ADR-0020/ADR-0004 一致，无不符 ✓
- 本任务不生成新版本条目（符合裁定 3）✓
- 下游：`contract-asm` 版本 `0.5.0` ✓；README `Toolchain 0.5.0` + `Machine 0.2.1` ✓；`check_spec_drift` Machine-01 映射（fixture 独立验证 FAIL→回绿）✓

**反例注入**：
- ① Makefile `docs/Process-01`→`spec/Process-01`：`run.sh --inject` C1 FAIL → cp+md5 还原回绿 ✓
- ② README Toolchain `0.5.0`→`0.5.1`：`check-spec-drift` rc=2 FAIL → cp+md5 还原回绿 ✓
- ③ README Machine `0.2.1`→`0.2.2`：check-spec-drift 仍 PASS（**覆盖面缺口**：无合约头以 `[Machine-01 §…]` 引用；fixture 验证映射本身有效——见 finding F-A）

**证据脚本**（`run.sh` 176 行）：一键可跑 PASS rc=0 ✓；能失败+可达 FAIL（selftest 注入）✓；结构断言 C6 ✓；计数不写死 ✓；捕获退出码 ✓。脚本 findings（非阻断）：C7 无条件 pass label；`--inject` 不注入仅报告。

**越界/披露核**：根 README line3 + spec/README.md Process 指代改动合理（A 段同步域）✓；patch 2 处按裁定 9 遗留 ✓；ISS-160 已登记 ✓

**Finding**：
- **无阻断项**
- [非阻断 F-A] README `Machine` 行无机械保护（无合约头 `[Machine-01 §…]` ⇒ drift check 不覆盖该行；映射已就位）——建议后续在 contract-see/semihosting 头部加 `[Machine-01 §N]` 引用，或补 README↔册头版本校验
- [非阻断 F-B] patch 2 处未同步（裁定 9 保留，已登记遗留）
- [非阻断 F-C] ISS-160 子项未在 issues.yaml 正文登记处置

**判定：Accepted**——验收 1–9 全通过；册正文一字不改 ✓；版本号 `0.5.0`/`0.2.1` + changelog 格式符合用户裁定 ✓；所有门控 rc=0 ✓
