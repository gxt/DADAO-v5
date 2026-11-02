# SPEC-154t: SimRISC 版本变更记录补全与按版本归档

**模块**：spec
**项目里程碑**：M9
**依赖**：`SPEC-153t`（**必须先完成**：两册同改 `spec/`，且本册的 `0.5.5-rc` 快照须含 153 的迁移结果）；`SPEC-111t`（`SimRISC-0.5.3` 归档体例先例）；`docs/Process-06`（`spec/` 保护 + 只读锁）；`docs/Process-04`（归档体例）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实（**先读，勿重复查证；仍须现场复核**）

- **用户原话（逐字，2026-10-21，经主会话转达）**：
  - 「**扫描 .cache/refs/DADAO.wiki 中的仓库提交记录，补充spec中确实的老版本的 版本变更与记录**」
  - 「**wiki历史里应该有0.4.1之前的版本，也做个备份保留**」
  - （承前）「**根据 SimRISC 的版本号，在 `.tao/archive/` 目录下分别保留一个副本**」
- **现场事实（architect 2026-10-21 实测；执行时逐条复核并留命令输出）**：
  1. **wiki 历史**：`.cache/refs/DADAO.wiki` = **385** 提交（2023-12-14 → 2026-06-30，HEAD `9f378f4`，「phymem→pmem全局重命名」）；顶层为 **5 册**结构 `SimRISC-00-指令系统设计.md` / `01-数据类指令` / `02-地址类指令` / `03-浮点类指令` / `04-系统类指令`（另有 DADAO-*/Guide-*/Home）。**更早期为单文件 `SimRISC.md`**（首个提交 `57720b5`）。
  2. **wiki 的版本标记很稀**：全历史逐提交解析册头 `版本：X.Y.Z`，只得到 **`0.4.0`（29 个提交）**与 **`0.4.1`（11 个提交）**；`0.4.0` 首次标记 = `85ba32a`（2026-06-27，「SimRISC-00: 版本号0.3→0.4」），`0.4.1` 首次标记 = `624fcbc`（2026-06-28，「统一patch+1…SimRISC 0.4.1」），**`0.4.1` 末次 = wiki HEAD**。⇒ 「**0.4.1 之前**」在 wiki 中**只有 `0.4.0` 有版本标记**；再早（`0.3` 及以前）**无版本标记**，只能如实登记为「不可按版本重建」，**不得**用任何现存文本冒充。
  3. **wiki 工作树未纳入锁**：`manifests/references.lock.toml` 只锁 `DADAO-0628`/`DADAO`；`.cache/refs/DADAO.wiki` **无 pin** ⇒ 清单必须记录**所用提交号**（本次 = `9f378f4`）作可复现锚点，不得依赖「当前 HEAD」。
  4. **本仓历史**：`master` = `8681b7a5`，**1159** 提交，首个 = `a08ebc82`（2026-07-14）；`3f69139c`（2026-07-14）自 wiki 同步 11 份文档。**升号提交（本仓口径）**：`0.5.0` = `73205574`（2026-07-15）、`0.5.1` = `dc07f25a`（2026-07-17）、`0.5.2` = `fecad7e9`（2026-07-18）、`0.5.3` = `eb4eff43`（2026-07-19）、`0.5.4` = `890038e2`（2026-09-28，**13 册重构**）、`0.5.5-rc` = `0f769100`（2026-10-12）。**路径分界**：升号早期在 `wiki/`，`bb98fff0`（2026-09-10）重命名为 `spec/` ⇒ **只用 `spec/` 路径查历史会漏掉 0.5.0–0.5.3**（陷阱）。
  5. **归档现状**：`.tao/archive/SimRISC-0.4.1/`（5 文件；**实测与 wiki HEAD 五文件 `sha256` 逐字节一致**）、`.tao/archive/SimRISC-0.5.3/`（5 文件，`SPEC-111t` 归档）。⇒ **缺** `0.4.0` / `0.5.0` / `0.5.1` / `0.5.2` / `0.5.4` / `0.5.5-rc`（6 个）；`spec/` 合计约 408 KB ⇒ 6 份副本约 2.4 MB（`.tao/archive/` 现 14 MB，可接受）。
  6. **归档体例**：`≤0.5.3` = **5 册**（`00-指令系统设计` / `01-数据类指令` / `02-地址类指令` / `03-浮点类指令` / `04-系统类指令`）；`≥0.5.4` = **13 册**（`SimRISC-00…12` 现行名）。
  7. **附录现状（13 册 × 7 版本，实测矩阵）**：`0.4.1`/`0.5.2`/`0.5.4`/`0.5.5-rc` **13 册齐**；缺 **`0.5.0` 4 册**（`01`/`02`/`06`/`12`）、**`0.5.1` 9 册**（`02`/`03`/`04`/`05`/`06`/`08`/`09`/`10`/`12`）、**`0.5.3` 6 册**（`01`/`04`/`08`/`09`/`10`/`12`）⇒ 合计 **19 个缺段**（现场重数，不写死）。
  8. **日期不符（须订正）**：`0.5.1` 段在 `SimRISC-07` 写 `2026-07-16/17`、`SimRISC-11` 写 `2026-07-16`；而升号提交 `dc07f25a` 日期 = **2026-07-17** ⇒ 统一口径 = **升号提交日**。
  9. **门控不受「缺段」影响**：`check_spec_changelog` 只校验「形态/逆序/册头一致/无表格/无任务号/互锁组顶部段一致」，不要求各册段集合相同 ⇒ 补段是**内容完整性**要求，不是门控驱动。

## 用户授权（`spec/` + `docs/Process-06` 改动，逐字）

> 见上「用户原话」三条（2026-10-21，经主会话转达）。
>
> **授权范围** = ① 按版本在 `.tao/archive/SimRISC-<ver>/` 新增副本（**不改**已有副本）；② 13 册 `SimRISC-*` 附录「版本与变更记录」的**补缺/订正**（含 `0.5.1` 日期统一）；③ `spec/README.md` 的归档指针更新；④ 版本归档规则写入 `docs/Process-06` 并加机械门控；⑤ 上述导致的只读锁 `sha256` 重算。**不含**任何指令语义/编码改动，**不含** `contracts/**`、`components/**`、`.tao/archive/M*/**`。

## 目标

把 SimRISC 的**版本账**做实：清单可复现、快照可追溯、附录不失实、规则可机械约束。

1. **清单**（派生，不手写）：历代版本 → 首/末次提交、日期、来源仓库、文件数、版本组合 `sha256`。
2. **归档**：每个版本一份 `.tao/archive/SimRISC-<ver>/`（已存在的 `0.4.1`/`0.5.3` **不动**；新增 6 个）。
3. **附录**：19 个缺段按**实际 diff** 补齐（无 diff 不补、标 `diff=∅`）；`0.5.1` 日期统一；每条新增/订正条目**能指到具体提交**；对不上的标「待核」。
4. **规则**：`docs/Process-06` 固化「升版必落归档」+ **加**机械门控（结论与依据见「门控决策」）。
5. **指针**：`spec/README.md` 的归档指针列全 8 个版本（不悬空）。

## 接口规范

- **输入（真源）**：
  - `.cache/refs/DADAO.wiki`（**只读**；记录所用 HEAD `9f378f4`）；
  - 本仓 `git` 历史（`wiki/` → `spec/` 双路径）；
  - `spec/SimRISC-*.md` 的册头与附录（补段落点）；
  - `manifests/spec-readonly.lock.toml`（改册须重算）。
- **输出**：
  1. `tools/spec/gen_spec_archive.py`（**新，入 git**；`--list` 打印清单 TSV、`--apply` 落缺失目录、`--verify` 校验清单 ↔ 目录 ↔ `sha256`）；
  2. `tools/spec/check_spec_archive.py`（**新门控**）+ `Makefile` 目标 `check-spec-archive` 并入 `make check`（L1）；
  3. `.tao/archive/SimRISC-{0.4.0,0.5.0,0.5.1,0.5.2,0.5.4,0.5.5-rc}/`（6 个新目录）；
  4. 13 册 `spec/SimRISC-*.md` 附录补段/订正 + 册头版本不变（仍 `0.5.5-rc`）；
  5. `spec/README.md`（历史基线节 → 8 版本归档清单）；
  6. `docs/Process-06-spec目录保护规范.md`（新增 §8「SimRISC 版本归档」）；
  7. `manifests/spec-readonly.lock.toml`（**仅改动册** `sha256` 重算 + 授权注记）；
  8. `.work/evidence/SPEC-154t/**`（default + `--inject`）、`.work/log/spec/SPEC-154t/**`。
- **约束**：
  - **快照取法（唯一定义）**：版本 `V` 的快照 = **`V` 的末次提交**，即「下一个版本标记**首次出现**的提交的父提交」（`git rev-parse <next>^`）；`0.5.5-rc`（未发布）= **当前 HEAD**（含 `SPEC-153t` 结果）；wiki 侧 `0.4.0`/`0.4.1` = wiki 中该版本串**末次出现**的提交。
  - **只新增，不改旧**：`SimRISC-0.4.1`/`SimRISC-0.5.3` 目录内容**一个字节都不改**；差异（若有）只报告。
  - **不得以当前 `spec/` 冒充历史**：取不到 ⇒ 标「不可重建」并留命令输出。
  - **`-rc` 目录 = 时点快照**：内容随将来升版会自然与工作树分叉；门控**只校验存在性与文件集**，不校验内容 ⇒ 须在 `Process-06 §8` 写明。
  - 附录条目**不带任务号/ADR/ISS 号**（`check_spec_changelog` 断言 6）；追溯证据统一写提交号 `（<7 位 sha>）` 或 `（<sha>..<sha>）`。

## 做（顺序：清单 → 归档 → 附录 → 规则/门控 → 证据）

### 阶段 0：开工前置

1. 核 `SPEC-153t` 已 `已验证` 且已落在本分支历史中（`git log --oneline -- spec/SimRISC-11-其它.md` 有 153 提交）；否则**停**。
2. `git status --porcelain -uall` 干净；记 `git rev-parse HEAD`、`git -C .cache/refs/DADAO.wiki rev-parse HEAD`（应 = `9f378f4…`）。
3. 复核「现场事实」1–9（尤其 7 的缺段矩阵与 8 的日期），输出留 `.work/log/spec/SPEC-154t/**`。

### 阶段 A：清单派生（脚本先行）

1. 写 `tools/spec/gen_spec_archive.py`：**两源独立派生**
   - 源 A（wiki）：逐提交取 `SimRISC*.md`（注意早期单文件 `SimRISC.md`、非 ASCII 名用 `git -c core.quotepath=false ls-tree`），解析册头 `版本：`；
   - 源 B（本仓）：按「版本标记首次出现的提交」建立升号序列，覆盖 `wiki/` 与 `spec/` 两段路径；
   - 输出 TSV 列：`版本 | 首标记提交 | 末次提交(快照) | 日期 | 来源仓库 | 文件数 | 版本组合 sha256`。
2. **版本组合 `sha256` 定义**（脚本与门控同一实现）：对目录内 `SimRISC-*.md` 按**文件名排序**，拼 `<sha256>  <basename>\n` 后取 `sha256`。
3. `--list` 输出与「现场事实」对齐：`0.4.0`/`0.4.1`（wiki）、`0.5.0…0.5.4`/`0.5.5-rc`（本仓）共 **8** 行；`0.3` 及更早⇒「无版本标记，不可重建」（不入清单，单独一行披露）。

### 阶段 B：归档落地

1. `--apply`：只**新增**缺失 6 目录；已存在 `0.4.1`/`0.5.3` **跳过**并 `--verify` 比对（若有差异 ⇒ 报告、**不覆盖**、登记「新发现/坑」）。
2. 逐目录人工抽查（`ls -1 | wc -l`、`head -4`）：`≤0.5.3` 必须 5 文件、`≥0.5.4` 必须 13 文件；`0.5.5-rc` 的 `SimRISC-11`/`12` 必须已含 153 的迁移结果（`grep -c "^## 6. 原子指令" .tao/archive/SimRISC-0.5.5-rc/SimRISC-11-其它.md` = 1）。
3. `--verify` rc=0；清单 TSV 存 `.work/log/spec/SPEC-154t/**`（并整表抄入完成区，压缩为一行/版本）。

### 阶段 C：附录补全与订正（13 册）

1. 逐册逐版本取 diff（`git diff <快照前>..<快照> -- <该册路径>`；`≤0.5.3` 需映射到祖先册：`01 数据类`→`SimRISC-01…`、`02 地址类`→`SimRISC-05…`、`03 浮点类`→`SimRISC-07`、`04 系统类`→`SimRISC-11/12`，**映射须写明依据**）。
2. **补段规则**：有实质变更 ⇒ 补段 `### <ver>（<日期>）` + 1–3 条**聚合** bullet，bullet 末 `（<sha>）`；无实质变更 ⇒ **不补段**，在完成区矩阵标 `diff=∅`（附 diff 为空证据）。位置按逆序插入。
3. **订正**：`0.5.1` 段日期统一 `2026-07-17`（依据 `dc07f25a`，2 册）；段内与 diff 明显不符者按 diff 改；无法核者标「待核」并登记「遗留问题」（**禁**虚构）。
4. `python3 tools/spec/check_spec_changelog.py` rc=0（21 册形态/逆序/无任务号）。

### 阶段 D：规则固化 + 门控

1. `docs/Process-06` 新增 **§8「SimRISC 版本归档（MUST）」**（**不动既有 §1–§7 编号**）：
   - 每次 **SimRISC 版本升号**（含开启 `-rc` 段）同笔落 `.tao/archive/SimRISC-<ver>/`（rc = 升号时点快照，发布时复核刷新）；
   - 快照内容 = 该版本**末次提交**的 `SimRISC-*.md` 全集（`≤0.5.3` 5 册、`≥0.5.4` 13 册）；
   - 已存在目录**不覆盖**；门控 `make check-spec-archive`（L1）。
2. **门控决策 = 加**（依据：规则若无机械约束必然再次漂移；成本 ≈ 一个只读脚本；**被否方案**：校验归档内容 `sha256` 与当前 `spec/` 相等——`-rc` 段随每次改动演进，必然天天红；被否方案：只写文档不进门控——`0.4.0`–`0.5.5-rc` 缺失正是无门控的结果）。**结论与理由写进 §8**。
3. `tools/spec/check_spec_archive.py`：断言（全部现场派生）
   - A1：`spec/SimRISC-*.md` 册头版本 ∪ 附录三级标题版本（含 `-rc`）⇒ 每个 `.tao/archive/SimRISC-<ver>/` 存在；
   - A2：该目录含 `SimRISC-*.md` ≥1 且必有 `SimRISC-00*`；
   - A3：目录内文件数 = 清单里该版本的文件数（清单由 `gen_spec_archive.py --list` 提供；清单缺失 ⇒ 只查 A1/A2）；
   - `--self-test`：内置三类反例（目录缺失 / 目录空 / 册头版本新于目录）。
4. `Makefile`：`check-spec-archive` 目标 + 加入 `check:` 依赖链（L1），并在 `help` 段加一行。

### 阶段 E：只读锁 + README + 证据

1. 只对**实际改动**的册重算 `sha256`；锁文件每册上一条注释写授权原话摘要。
2. `spec/README.md`「历史基线（已归档）」改为 **8 版本清单**（版本 / 提交 / 文件数），路径全部指向 `.tao/archive/SimRISC-<ver>/` 且**逐个存在**。
3. `.work/evidence/SPEC-154t/**`：① 清单 ↔ 目录 ↔ `sha256` 三向；② 旧目录未改（与 `master` 逐文件 `sha256` 比对）；③ 附录新段映射（每个新段 ≥1 条 `（sha）`，且该 sha 在本仓/ wiki 可解析）；④ 门控矩阵；⑤ `--inject`（`cp` 备份 + `md5` 还原，**禁** `git checkout/restore/stash`）。

## 验收标准（逐条可机械判）

1. **清单派生**：`python3 tools/spec/gen_spec_archive.py --list` 输出 **8** 行；`--list` 两次运行**逐字节相同**（确定性）；每行「首/末次提交」可用 `git log/show` 复核；**不含手写值**（脚本内无版本表常量——版本集合由扫描得出）。
2. **归档集合 = 清单集合**：`ls -d .tao/archive/SimRISC-*` 与清单差集为空；`0.4.0`/`0.5.0`/`0.5.1`/`0.5.2`/`0.5.4`/`0.5.5-rc` 各有目录；文件数逐版 = 5/5/5/5/5/5/5/13（按清单）；`0.5.5-rc` 的 11/12 册含 153 结果（`grep -c` 见阶段 B.2）。
3. **旧副本未动**：`git status --porcelain -uall .tao/archive/SimRISC-0.4.1 .tao/archive/SimRISC-0.5.3` = 空；与 `master` 逐文件 `sha256` 相同（`git diff --stat master -- .tao/archive/` 只显示新增目录）。
4. **附录完整性**：19 个缺段逐条有结论（补段 or `diff=∅`+证据）；`0.5.1` 日期在 13 册内**一致**为 `2026-07-17`；每个新增/订正条目末有 `（<sha>）` 且该 sha 解析成功；「待核」条目逐条列出（0 条亦可）。
5. **规则与门控**：`docs/Process-06 §8` 含「升版必落归档」+ 门控结论与依据；`make check-spec-archive` rc=0；`python3 tools/spec/check_spec_archive.py --self-test` 全绿（三类反例各自 FAIL 可达）。
6. **门控矩阵全绿**：`check-spec-numbering`、`check-spec-changelog`、`check-spec-readonly`、`check-spec-refs`、`check-spec-drift`、`check-legality-drift`、`check-legality-invariants`、`check-asm-list`、`check-asm-list-drift`、`check-knowledge-refs`、`check-no-residue`、`check-tasks`、`check-milestones-fresh` + **`make check`（L1，一次）rc=0**。
7. **可达 FAIL ≥2（`run.sh --inject` 现场输出）**：① 临时移走 `.tao/archive/SimRISC-0.5.2/` ⇒ `check-spec-archive` rc=1（A1 红）；② 向 `.tao/archive/SimRISC-0.5.1/SimRISC-00-指令系统设计.md` 追加一行 ⇒ `--verify` 组合 `sha256` 不符 rc=1；③ 临时把某册册头改 `0.5.6-rc` ⇒ A1 红。三例 `md5` 还原后回绿。
8. **证据脚本**：`.work/evidence/SPEC-154t/**` 下的 `run.sh` 全绿、`--inject` 三例 FAIL 且还原；脚本**不写死**版本数/文件数（现场统计）。

## 独立 oracle（不从当前 `spec/` 反推）

- **版本清单** ← 两个**互不依赖**的来源：wiki 的 `git log`（≤0.4.1）与本仓的升号提交序列（0.5.x）；两者的交集/缺口逐条显示。
- **快照内容** ← `git show <commit>:<path>`（版本控制真源），**不**从工作树复制、**不**用 `.tao/archive/` 已有副本回填。
- **附录条目** ← 对应版本区间的 `git diff`（提交对 → 文件 → 变更行），不从正文自述反推。

## 不留白的边界（写进完成区「遗留问题」）

1. `0.3` 及更早**无版本标记**（wiki 早期为单文件 `SimRISC.md`）⇒ 如实登记「不可按版本重建」，**不伪造快照**。
2. `.cache/refs/DADAO.wiki` 未纳入 `manifests/references.lock.toml` ⇒ 清单记录 `9f378f4` 为锚点；若将来该工作树被重建/更新，清单的 wiki 侧提交须按记录复现（不要在无记录情况下重跑）。
3. `0.5.5-rc` 目录内容会随后续 spec 改动与工作树分叉（`-rc` 语义如此），门控只保证存在性。
4. 本册**不改** `contracts/**`、`components/**`、`.tao/adr/**`、`.tao/archive/M*/**`。

## 完成区
**测试结果**：`.work/evidence/SPEC-154t/run.sh` rc=0（C1–C5 + 14 个门控 + `make check`(L1) 全绿，0 MISMATCH）；`run.sh --inject` rc=0（3/3 注入变红、3/3 cp+md5 还原回绿）；`check_spec_archive.py --self-test` 4 类反例均 FAIL(预期)。日志 `.work/log/spec/SPEC-154t/`。
**修改文件**：`tools/spec/gen_spec_archive.py`（新）、`tools/spec/check_spec_archive.py`（新）、`Makefile`（`check-spec-archive` + 入 L1 + help）、`docs/Process-06-spec目录保护规范.md`（§8）、`spec/README.md`（8 版本归档表 + 同号冲突注记）、`spec/SimRISC-04-64位数据运算.md`（补 0.5.1/0.5.3 两段）、`spec/SimRISC-07-浮点运算.md`、`spec/SimRISC-11-其它.md`（0.5.1 日期 + sha）、`manifests/spec-readonly.lock.toml`（3 册 sha + 授权注记）、`.tao/archive/SimRISC-{0.4.0,0.5.0,0.5.1,0.5.2,0.5.4,0.5.5-rc}/`（新增 6 目录，5/5/5/5/13/13 册 + `PROVENANCE.md`）、`.work/evidence/SPEC-154t/{run.sh,checks.py}`、`.work/log/spec/SPEC-154t/*`。
**验收结果**：
- 清单 8 行（`0.4.0/0.4.1`←wiki@`9f378f4`，`0.5.0…0.5.4/0.5.5-rc`←本仓），两次运行**逐字节相同**；文件数 5/5/5/5/5/5/5/13（现场统计）；每版「首次/快照提交」`git cat-file` 可解析。
- `gen --verify` rc=0（8/8）；旧目录 `0.4.1`/`0.5.3` 与 `master` 逐文件 sha256 相同、`git status` 空（未改一字节）。
- **19 缺段矩阵**：0.5.0×[01∅ 02∅ 06∅ 12∅]；0.5.1×[02∅ 03∅ **04补** 05∅ 06∅ 08∅ 09∅ 10∅ 12∅]；0.5.3×[01∅ **04补** 08∅ 09∅ 10∅ 12∅] ⇒ **2 补段 + 17 diff=∅**（C4 逐条以映射章节 diff 证明「有段⇔有实质 diff」）。
- 0.5.1 段日期在 5 册内一致 `2026-07-17`；新/订正条目末 sha（`68ceb3f8`/`aba64274`/`55230e29`）均可解析。
- 归档集 = 清单集（8/8）；6 个新目录 `PROVENANCE.md` 快照可解析；`0.5.5-rc/SimRISC-11` 含 153 迁移结果（`## 6. 原子指令`=1）。
- 门控全绿：`check-spec-archive`(新)/`-numbering`/`-changelog`/`-readonly`/`-refs`/`-drift`、`check-legality-{drift,invariants}`、`check-asm-list{,-drift}`、`check-knowledge-refs`、`check-no-residue`、`check-tasks`、`check-milestones-fresh`、`make check`(L1) rc=0。
**新发现/坑**：① wiki 历史文件名用 **U+2010**（`SimRISC‐00‐…`）而非 ASCII `-`，按精确名取会「不存在」；脚本双形匹配、落盘归一，`PROVENANCE` 记录条数。② 本仓 `wiki/`→`spec/`（`bb98fff0`）与 `spec/SimRISC-0.5.3/` 曾作归档子目录（`86fdcc8`）⇒ 必须同时扫两路径且只取**直接位于**根目录的文件，否则文件数虚高（13/10）。③ **同号冲突**：`0.4.1` wiki（`9f378f4`）与本仓（`7dde864`）内容不同（组合 sha `a019d006…` vs `901454aa…`）⇒ 归档取 wiki 版、只报告不合并；本仓 0.4.1 期修订随 0.5.0 发布。④ 附录「段=开发区间（上一版号提交→本版号提交）」与归档「快照=末次声明」口径不同：0.5.3 号头自 07-19 保持到 09-28，故 0.5.3 归档含被判入 0.5.4 段的 7 月改动（已写入 `Process-06 §8`）。⑤ `check-run-artifacts` 约束 `.work/log` 文件名（`<TASK-ID>-<purpose>.(log|json|txt)`），`.tsv`/`run-default.log` 判 illegal（已改名）。
**遗留问题**：① 「待核」= **0 条**（19 段均有 diff 结论）。② 0.5.3 归档 ↔ 0.5.4 段的口径差异为**记录在案**（非缺陷）；若须「归档=发布快照」，需用户裁定把 0.5.3 重切到 `640b879`——本任务禁改既有归档，未做。③ `0.3` 及更早无版本标记，不重建。④ 未改 `contracts/**`、`.cache/refs/DADAO.wiki`、既有归档（engineer 返回时亦未 commit/push、未改 `**状态**`；提交与置 `待验收` 由 architect 本笔完成）。

**口径披露（architect 提交前现场核，2026-10-21）**：`0.5.3` 归档取 **「末次声明」= `86fdcc8`**（= `890038e2^`，2026-09-28「`SPEC-013t`: 归档 SimRISC 0.5.3 文档」；五册与目录内文件**逐字节一致**），其中**含附录归入 `0.5.4` 段的 7 月改动**（`640b879..86fdcc8` 共 **275** 提交）；**≠「发布快照」`640b879`**（2026-07-19，当时路径 `wiki/SimRISC-0{0..4}`，与归档五册**五册全不同**）。⇒ 口径差异 **待用户裁定**（须「归档 = 发布快照」则另立任务重切 `0.5.3`）；本笔**未改**既有归档（`0.4.1`/`0.5.3` `git status` 空）。

## 审阅记录

### 第 1 轮 engineer 自审
- 逐行审 `gen_spec_archive.py`：派生链（rev-list→册头版本→首次/快照）无版本表常量；`snapshot = parent(first(next))` 与任务定义一致；`--verify` 改为**以 PROVENANCE 快照为锚**（`-rc` 未来分叉不会假红）；组合 sha 用归档名（归一后）计算，与 0.4.0 的 U+2010 名一致。
- 逐行审 `check_spec_archive.py`：A1/A2/A3 全部现场派生；A3 派生失败降级；`--self-test` 3 类反例 + A3 反例均可达 FAIL，正向样例 PASS。
- 审 `checks.py`：C1–C5 真源 = git 历史/wiki；C4 的 `(pre)` 只对 04 生效且剔除版本行（否则每区间都「有 diff」）；注入 1 用同文件系统改名（跨设备 rename 报 EXDEV）。
- 审附录/文档：只加 2 段、只改 2 处日期；`check_spec_changelog`/`check_numbering` PASS；`spec-readonly` 3 册 sha 同步。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 0.4.0 组合 sha 用未归一文件名，`--verify` 假红 | ✅已修 | `enrich` 用归一 basename | `--verify` 8/8 OK |
| `--verify` 对 `-rc` 以当前 HEAD 组合 sha 比对，未来必红 | ✅已修 | 改以 `PROVENANCE` 快照派生期望值（pin 驱动） | `--verify` 8/8 OK；I2 注入仍 rc=1 |
| I1 跨设备 `rename` 失败（EXDEV） | ✅已修 | 同文件系统改名到 `.tao/archive/.inject-bak-*` | `--inject` I1 rc=1→还原 rc=0 |
| I2 以 `git diff` 判「空注入」，未跟踪文件恒 0 | ✅已修 | 改比注入前后 md5 | I2 CHANGED，还原 md5 MATCH |
| I3 经 `make` 包装 rc=2（非 1） | ✅已修 | 直调 `check_spec_archive.py` 期望 rc=1 | I3 rc=1，还原 rc=0 |
| `.work/log` 文件名违规（`.tsv`/`run-default.log`） | ✅已修 | 统一 `<TASK-ID>-<purpose>.{log,txt}` | `make check-run-artifacts` rc=0 |
| 新门控只进了 `.PHONY`/help，漏进 `check:` 依赖链 | ✅已修 | `Makefile check:` 加 `check-spec-archive` | `make check` 日志含 `check-spec-archive: PASS`，rc=0 |

### 第 1 轮 reviewer 验收（2026-10-21，独立重跑；**判决：Needs Revision**）

- **重跑（我方命令 + 真实退出码）**：`python3 tools/spec/gen_spec_archive.py --list` 跑 2 次 + `cmp` **rc=0**（8 行；文件数 5/5/5/5/5/5/5/13；日志 `/tmp/opencode/REVIEW-154t/list{1,2}.tsv`）；`gen --verify` **rc=0**（8/8 OK）；`./.work/evidence/SPEC-154t/run.sh` **rc=0**（22 步全 `expect rc=0 actual rc=0 OK`，含 `make check (L1)` 与 14 个门控、`--self-test` 4 反例 FAIL(预期)，`MISMATCH` 计数 0）；`run.sh --inject` **rc=0**（I1/I2/I3 各 rc=1 → md5 `MATCH` → rc=0）；`--self-test` 单跑 rc=0。完成区转述与我方输出一致。
- **清单复现（两源各抽 1–2 版，组合 sha 由我按 §8 定义独立重算）**：wiki 源 `0.4.1`（首 `624fcbc` 2026-06-28、末 `9f378f4`、5 文件、组合 `a019d006…`）与 `0.4.0`（首 `85ba32a`、快照 `624fcbc^`=`c8861ec`、组合 `51ae2247…`）；本仓源 `0.5.0`（首 `73205574` 2026-07-15、快照 `dc07f25a^`=`fc3d814`、5 文件、组合 `ab82f65f…`）⇒ commit/日期/文件数/sha 与清单**逐项一致**；两次运行逐字节相同。
- **归档逐目录**：8 目录文件数 5/5/5/5/5/5/5/13；6 个新目录**逐文件** sha256 == `git show <PROV 快照>:<源路径>` 内容、PROV 逐文件表 == 实际文件；`0.4.1`/`0.5.3`：`git status --porcelain -uall` 空、`git log -- <两目录>` 最新仍为 `1d6ce0e2`/`6487758a`（无本笔）、`487d1673 --name-status` 对二者**无 M/D** ⇒ **未被改动 ✓**。
- **附录可追溯（抽 3 条真取到 diff）**：`SimRISC-04` `0.5.1`→`68ceb3f8`（diff 第 322→323 行 rd0 约定收窄）、`SimRISC-04` `0.5.3`→`aba64274`（`add.si rrii→riii`、`imms12→imms18`）、`SimRISC-11` `0.5.1`→`55230e29`（`RASUP→RASUF`）。**`diff=∅` 抽 2 段**：0.5.0×12（`3f69139c..73205574` 旧04 仅 1 个 hunk、`grep SRAM`=0）、0.5.1×09（`73205574..dc07f25a` 旧01 只动「(pre) rd0」与「存取RD寄存器」，映射章节未动）⇒ **确无变更，非偷懒**；`### 0.5.1（` 5 册全为 `2026-07-17`。
- **规则/门控 + 我方独立注入（红→还原→绿）**：`docs/Process-06 §8` = **+12/−0**（§1–§7 未动），含「升版必落归档」+ 门控结论与两条被否方案；`Makefile check:` 依赖链确含 `check-spec-archive`（L1）。我方注入：`mv .tao/archive/SimRISC-0.5.4` 出树 ⇒ 门控 `FAIL A1 目录缺失` **rc=1**、`checks.py c5` **rc=1** ⇒ `mv` 还原 + 目录 md5 `cmp` **rc=0** ⇒ 门控 **rc=0**、c5 **rc=0**。
- **门控 (a) 判定：可接受（不阻断），缺口如实记录**。实测注入 B（造未声明目录 `SimRISC-0.9.9/`）⇒ 门控 **rc=0**、`gen --verify` **rc=0**、**仅 c5 报 FAIL**；注入 C（改仅在清单的 `0.4.0` 文件）⇒ 门控 **rc=0**、`--verify` **rc=1**；即 A1 确为**单向**（打印「7 个版本目录」而磁盘 8）。**理由**：§8 规则本身是「升版必落归档」，缺档方向已被 A1 覆盖且可红（注入 A 证实）；`0.4.0` 属 wiki 早期、现行附录未声明属正常；「归档集=清单集」是验收 2 的一次性机械项、由 c5 承担（我方核 **8==8**）。**建议**（供 architect 定夺，非阻断）：门控补「磁盘 ⊆ 清单」断言，当前 8==8 可即绿。
- **⚠ Needs Revision（唯一阻断项；验收标准 1「sha256 可复核」/ 阶段 A.2「脚本与门控同一实现」+ 证据脚本可达 FAIL）**：`.tao/archive/SimRISC-0.4.0/PROVENANCE.md:9`「版本组合 sha256」= `549f5ba96340…` **算错**——按 §8 定义用**该文件自己列的逐文件表**重算 = `51ae22475ce3…`（= 目录实际组合 = `--list`/`SPEC-154t-manifest.txt` 行）；`549f5ba9…` 恰为**未归一 U+2010 文件名**的旧值，即 engineer 自审 finding#1 只修了 `enrich`、未重写已落盘 PROV（`--apply` 对已存在目录 skip）。其余 5 个新目录 PROV 组合自洽 ✓、8 目录逐文件 sha 全对 ✓。
- **为何全绿没抓到（可达 FAIL 缺失）**：`gen --verify` 只读 PROV 的「快照提交」、不校验其 composite；`checks.py:281` 的 PROV 断言是子串存在式 `"版本组合 sha256" in text` ⇒ 我把该值改成全 0 后 `c5` 仍 **PASS rc=0**、`--verify` 仍 **rc=0**（已 `cp`+md5 还原，`cmp`=0）。**必改**：① 该行改为 `51ae22475ce3085affedc2afdd5f80eaf39c88b585289bb1be60a547fbe890e9`（本目录系本笔新增，属修正自身产出：`cp` 备份 + 单行替换 + md5 对账）；② `verify_one` 与 `c5` 增「PROV composite == 按其逐文件表重算」断言并给出**可达 FAIL**（反例注入证明）；③ 重跑 `run.sh`（default + `--inject`）回绿。
- **0.5.3 口径披露：✅ 如实**——册内遗留②与「口径披露」明写「末次声明 `86fdcc8` vs 发布快照 `640b879`」「⇒ **待用户裁定**、本笔未改既有归档」，**未**当成已裁定；commit message 同口径；`0.5.3`/`0.4.1` 目录未动。
- **另一处口径（非阻断，记录在案）**：`0.5.5-rc` 目录 pin = `a04d34ee`（含 153 迁移 ✓、**不含**本笔 3 处附录改动），目录组合 `a0a27cbc…`；清单行随 HEAD 漂移为 `487d1673`/`883388a1…` ⇒ `--verify` 对 -rc 实为「目录↔PROV」两向（脚本 docstring、§8、README `a04d34e` 均已写明 -rc 时点语义）。此为任务书「-rc 快照=当前 HEAD」与「只增不改」的固有张力，**不判缺陷**；若须严格三向一致，需 architect 定 -rc 口径。
- **约束逐条**：快照取法唯一定义 ✓；只新增不改旧 ✓；不以当前 `spec/` 冒充历史 ✓（8 目录内容 == `git show` 快照）；`-rc` 只查存在性与文件集且已写入 §8 ✓；附录条目无任务号/ADR/ISS（`check-spec-changelog` rc=0）、追溯统一 7 位 sha ✓；未碰 `contracts/**`、`components/**`、`.tao/adr/**`、`.tao/archive/M*/**` ✓（本笔 64 个改动路径逐一对账，与完成区「修改文件」一致；`milestones.md`/两册任务文件为 architect 状态与台账变更）。
- **快照对账与声明**：验收前、后 `git status --porcelain -uall` 均 **0 行**（我方共 4 次注入全部还原，无 `.inject-bak-*`/`SimRISC-0.9.9` 残留，`check-no-residue` rc=0；写入本段后应恰为 1 个 `M`=本册）。我本会话**只写本段**、**未改任何代码/数据/门控**、**未 commit/push**。

### 返工（2026-10-21，第 1 轮 reviewer Needs Revision 三项）

- **① 0.4.0 组合 sha 订正**：`PROVENANCE.md:9` `549f5ba9…`（未归一 U+2010 文件名旧值）→ **`51ae2247…`**（`cp` 备份 `/tmp/opencode/SPEC-154t-rework/bak/`，md5 `e8db9d3e→4358284b`，diff 仅此 1 行）。8 目录逐个按 §8 算法重算：磁盘 == `git show <PROV 快照>` == PROV 表 == 组合值；**0.4.1/0.5.3 无 PROV**，磁盘 == 快照 == 清单值；**除 0.4.0 外无同类错**（8 条逐项见返工 `c5` 输出）。
- **② c5 改精确比对**：解析 PROV「逐文件 sha256」表 + 「版本组合 sha256」，与 `git show <快照>` 实算**全等**（`==`，无 `in`/前缀/子串）；`gen verify_one` 增「表 == 快照」「声明 == 按表重算」两条断言。反例 I4：0.5.2 表内 sha 末位改 1 位 ⇒ `c5`/`--verify` **rc=1**，`cp`+md5 `MATCH` 回绿；旧错值回归亦红（写回 `549f5ba9…` ⇒ `--verify` rc=1）。
- **③ 门控补 A4（磁盘 ⊆ 清单）**：`check_spec_archive` 增反向断言（当前 8==8 即绿；`--self-test` 增反例⑤）；`Process-06 §8` 写明「**双向**（清单 ⊆ 磁盘 且 磁盘 ⊆ 清单）」。反例 I5：造 `.tao/archive/SimRISC-0.9.9/` ⇒ `FAIL A4 目录不在清单` rc=1，清理后 rc=0。
- **证据真值**：`run.sh` default **rc=0**（22 步，0 MISMATCH）、`--inject` **rc=0**（5/5 变红 + 5/5 还原回绿）、`--self-test` rc=0（5 类反例）、`make check-spec-archive` 与 L1 `make check` rc=0；未改 `spec/`、归档内容（仅上述 1 行）、`**状态**` 未改、未 commit。
- **③ 附**：为使「双向」字面成立，A3 同时要求清单里每个版本都有目录（临时移走 `0.4.0/` ⇒ `A3 清单版本缺目录` rc=1，还原 rc=0）。
- **自审（第 2 轮 engineer，逐行）**：`provenance_pairs` 无「解析失败即跳过」分支（格式不符必红）；`verify_one` 三条精确比对（表↔快照、声明↔重算、磁盘↔快照）；`check_spec_archive` 的 A3/A4 计数均现场派生、不写死；`inject4/inject5` 各有可达 FAIL 且 run.sh 捕获真实 rc（无 `tee`）。判决：无未修 finding。

### 第 2 轮 reviewer 验收（2026-10-21，仅复验三项；**判决：Accepted**）

- **① 组合 sha**：`0.4.0/PROVENANCE.md:9` 现为 `51ae22475ce3085affedc2afdd5f80eaf39c88b585289bb1be60a547fbe890e9`；我按 §8 算法（按文件名排序拼 `<sha256>  <basename>\n` 再取 sha256）独立重算 **3 个目录**：`0.4.0`（按 PROV 自身逐文件表、按目录实际文件两种算法）、`0.5.0`=`ab82f65f…`、`0.5.4`=`2a983b4b…` ⇒ **PROV 声明 == PROV 表重算 == 目录重算 == `--list` 行**（全等 True）；`gen --verify` rc=0。
- **② `c5`/`--verify` 可失败（我方注入，改 1 位）**：`0.4.0` PROV 组合 sha 末位 `9→8` ⇒ `checks.py c5` **rc=1**（`[FAIL] SimRISC-0.4.0 组合 sha256 == 按快照重算（精确）`）、`gen --verify` **rc=1**（`PROVENANCE 组合 sha256 与逐文件表重算不符`）⇒ `cp`+md5 还原（记录值 `4358284b…`，`cmp`=0）⇒ c5 **rc=0**、`--verify` **rc=0**。
- **③ 双向门控（两向各红一次）**：(a) 造临时件 `.tao/archive/SimRISC-0.9.9/` ⇒ `FAIL A4 目录不在清单（磁盘 9 个 / 清单 8 个）` **rc=1** ⇒ 删除 ⇒ **rc=0**；(b) 移走仅在清单的 `0.4.0/` ⇒ `FAIL A3 清单版本缺目录（清单文件数 5）` **rc=1** ⇒ `mv` 还原 + md5 `cmp`=0 ⇒ **rc=0**；`--self-test` **5 类反例全 FAIL(预期)** rc=0，PASS 行 =「声明 7、磁盘 8、A3/A4 启用」。
- **④ 证据与 L1**：`run.sh` **rc=0**（22/22 `expect rc=0 actual rc=0 OK`、`MISMATCH`=0，含 `C5 PROV 精确比对`、14 门控、`make check (L1)` rc=0）；`run.sh --inject` **rc=0**（I1–I5 共 14 步全 OK，5/5 红→md5 还原→绿，`.tao/archive` 无 `inject`/`0.9.9` 残留）。
- **约束/范围**：返工只落我上轮点名处（`0.4.0/PROVENANCE.md` **+1/−1** 单行值改、`checks.py` 逐文件表与组合 sha 改**精确全等**比对并覆盖 `0.4.1`/`0.5.3`、`check_spec_archive.py` A3 反向 + **A4** + self-test⑤、`gen --verify` 校验 PROV 组合、`Process-06 §8` 措辞、`run.sh` 增 I4/I5）；**未碰** `spec/**`、既有 `0.4.1`/`0.5.3` 归档、`contracts/**`、`Makefile`；**未 commit/push**。
- **⚠异常披露**：`git status --porcelain -uall` 实为 **5 个 M** = engineer 返工 4 件（PROV / `check_spec_archive.py` / `gen_spec_archive.py` / `Process-06`，**尚未提交**，提交权归 architect）+ 本册（含第 1、2 轮记录），**非**「只有 1 个 M」⇒ 请 architect 先 `commit` 返工再处置本册；另 `c5`/`--verify` 失败信息中 expect/actual 同截 16 位、改 1 位时两串显示相同（以 rc=1 为准），纯显示问题、不阻断。
- **声明**：本会话只写本段；4 次注入（PROV 改 1 位、造多余目录、移走 `0.4.0`、及 run.sh 内 5 例）全部 `cp`/`mv`+md5 还原并 `cmp`=0；**未改任何代码/数据/门控**、**未 commit/push**。

### 提交（architect，2026-10-21）
- **档位**：正常提交（reviewer 第 2 轮 `Accepted`）⇒ 分支 `spec154t-complete` **唯一提交**（本册所在提交；本段追加前为 `3c7e25bf`，`--amend` 后号更新，`git log -1 --stat` 可验 8 项文件集）；经 `merge --squash` 一次落地 `master`；**未 push**。
- **文件集对账（`git -c core.quotepath=false diff --cached --name-only` = 8 项）**：返工 4 件 = `.tao/archive/SimRISC-0.4.0/PROVENANCE.md`（组合 sha 1 行）、`tools/spec/check_spec_archive.py`（A3 反向 + A4 + self-test⑤）、`tools/spec/gen_spec_archive.py`（PROV 精确比对）、`docs/Process-06`（§8 双向措辞）—— 均在本册「修改文件」声明内；收尾 4 件 = 本册（`**状态**` → `已验证` + 两轮审阅/返工段）、`.tao/knowledge/milestones.md`（流水行转 `已验证`/16:14、按时间倒序上移）、`.tao/knowledge/lessons.md`（§2.44）、`.tao/knowledge/issues.yaml`（`ISS-314` → `closed`、`resolved_by: SPEC-154t`）⇒ **无漏提 / 无多提 / 无越界**（未含 `spec/**`、`contracts/**`、`Makefile`、既有归档 `0.4.1`/`0.5.3`）。
- **门控**：`make check-spec-archive` **rc=0**（`声明 7 个版本目录，磁盘 8 个，A3/A4 启用`）；`make check`(L1) **rc=0**（`check_issues: 57 open, 31 closed`、`resolved_by 约束 OK`、`repository checks (L1): PASS`）。日志 `/tmp/opencode/SPEC-154t-complete/{check-spec-archive,make-check}.log`。
- **保留待裁**：`0.5.3` 归档口径（`86fdcc8` vs `640b879`）披露仍在（本册「口径披露」+「遗留问题 ②」），**未改**归档。
