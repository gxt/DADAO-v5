# SPEC-111t: 归档 SimRISC-0.5.3 历史基线至 `.tao/archive/`

**模块**：spec
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

> **来源（用户裁定 2026-10-06）**：`spec/SimRISC-0.5.3/` 与现行 `spec/SimRISC-0.*` 混放，用户裁定将其移入 `.tao/archive/`（与 M1/M2 归档体例一致）。**本任务书由另一会话（非当前并发推进 M3 的会话）建立，只建不执行；实际移动须在串行空档执行**（见「并发约束」）。

---

## 背景

`spec/SimRISC-0.5.3/`（5 个文件：`SimRISC-00-指令系统设计.md`/`01-数据类指令`/`02-地址类指令`/`03-浮点类指令`/`04-系统类指令`，0.5.3 基线、只读、仅供对照）由 `SPEC-013t` 建立。现状它在 `spec/` 下，被 3 个门控脚本**按路径排除**。

## 目标

把 `spec/SimRISC-0.5.3/` 移至 **`.tao/archive/SimRISC-0.5.3/`**，并**同步全部引用**——消除指向不存在路径的「死排除/死链」。

## 改动清单（执行时逐项核对）

1. **移动**：`git mv spec/SimRISC-0.5.3 .tao/archive/SimRISC-0.5.3`（保留历史；`.tao/archive/` 下与 `M1/`、`M2/` 平级）。
2. **门控/工具（3 处硬编码该路径为"排除项"，移动后成死代码）**：
   - `tools/spec/check_asm_prose.py`：docstring L34 + L66 `ROOT / "spec" / "SimRISC-0.5.3"`；
   - `tools/spec/check_spec_codeblocks.py`：docstring L30/79 + L60 `HISTORICAL_DIR`；
   - `tools/spec/check_scope.py`：`HISTORY_PREFIXES`（L43/51）。
   - **处置**：删除该路径排除（因历史目录已不在 `spec/` 扫描面内），或在确有需要时改指 `.tao/archive/SimRISC-0.5.3/`。二者择一，须在完成区说明理由。
3. **`spec/README.md`**：删除/更新 `SimRISC-0.5.3/` 索引行（现 L34「历史基线（只读）」）；在 `.tao/archive/`（或 `spec/README.md`）保留一句指针说明归档去向。
4. **`Makefile`**：L302 注释「`spec/**/*.md` (excl. historical SimRISC-0.5.3)」更新。
5. **台账叙述（不改写历史行）**：`.tao/knowledge/MEMORY.md` L67/L74、`.tao/knowledge/lessons.md` L133 中的 `spec/SimRISC-0.5.3/` 路径引用——按需订正为归档路径，或保留为历史引用（须在完成区说明）。

## 明确不改

- **归档任务书**（`.tao/archive/M2/spec/SPEC-013t-存档0.5.3文档.md` 等）：历史快照，引用将悬空，**可接受**（同 `adr-0015` 引用已移走的 `docs/02-大道至简.md` 之先例）。
- `adr-0015`（与本次无关）。
- `spec/SimRISC-0*`（现行 12 章）、`contracts/**`、`tests/vectors/**`、`components/**`。
- `tools/spec/check_qfc_coverage.py` / `validate_encoding.py` 中的「SimRISC 0.5.3」——**仅是来源概念表述，非路径**，不改。

## 验收标准（可执行、可失败）

1. **移动结果**：`.tao/archive/SimRISC-0.5.3/` 恰含 5 个文件；`spec/SimRISC-0.5.3/` **不存在**。
2. **引用清零**：全仓 `grep -rn 'spec/SimRISC-0\.5\.3'`（**排除** `.tao/archive/**` 历史任务书）**0 命中**。（给真实 grep 输出与退出码。）
3. **门控**：3 个脚本不再含指向不存在路径的排除；`make check` **EXIT=0**（重点 `check-asm-prose`、`check-spec-codeblocks`、`check-scope` 仍 PASS）。
4. **反例门控（证明门控仍有效）**：临时把历史目录**放回 `spec/`**（或构造对应用例）⇒ 说明门控的排除若已删则应被扫描到（如触发 `check-asm-prose`/`check-spec-codeblocks` 的扫描）→ 复原。给出「注入→FAIL/命中→还原→回绿」的真实输出。
5. **不变量**：现行 `spec/SimRISC-0*`、`contracts/**`、`tests/vectors/**`、`components/**` **零改动**；`check-patch-tree` 计数不变。
6. 完成区与真实输出**逐条对齐**；证据脚本按 `AGENTS.md`「子代理硬约束」第 8 条产出。

## ⚠️ 并发约束（必须遵守）

本任务触碰 **`Makefile`**、**`spec/README.md`**、**`tools/spec/*.py`**、**`.tao/knowledge/MEMORY.md`**——**均为多会话共享文件**。⇒ **必须与其它 session 串行**：
- 执行**前**确认无并发构建/`make check`（另一会话高频推进 M3，每任务跑 `make build-mc` + `make check`）；
- **不得**与其它任务同时改上述共享文件；
- 建议在另一会话**任务间歇/收口空档**执行。

## 完成区

**测试结果**：
- `make check` **EXIT=0**（日志 `.work/log/spec/SPEC-111t-make-check.log`）：`check-asm-prose: PASS (0 violations)`；`check-spec-codeblocks: PASS (623 instruction line(s) checked …)`；`check-scope: PASS`；`spec drift check: PASS`；`validate_encoding: 227 条记录 OK`；`check-patch-tree: 2 component(s), 89 patches OK`；`check-lit` 60/60；`check_issues: 34 open, 12 closed`；末行 `repository checks: PASS`。
- `make check-no-residue` **EXIT=0**（`check-no-residue: PASS`）。
- 独立补充门控：`make check-spec-refs` **EXIT=0**（`结果: PASS (0 violations)`）；`make check-index-blobs` **EXIT=0**。
- 一键证据脚本 `.work/evidence/SPEC-111t/run.sh` **EXIT=0**（20 项全 PASS，含反例注入→FAIL→还原→回绿）。

**修改文件**（`git status --porcelain -uall` 逐条核对）：
- **移动（staged rename，非删+增）**：`spec/SimRISC-0.5.3/*.md`（5 文件）→ `.tao/archive/SimRISC-0.5.3/*.md`；`git diff --cached --summary` 显示 5× `rename … (100%)`；移动前后 `md5sum` 逐文件相同。
- **门控脚本（3）**：`tools/spec/check_asm_prose.py`（删 `_EXCLUDE_DIRS`/`_should_exclude` 目录排除 + docstring）、`tools/spec/check_spec_codeblocks.py`（删 `HISTORICAL_DIR` 及其 skip + docstring）、`tools/spec/check_scope.py`（`HISTORY_PREFIXES` 删 `"spec/SimRISC-0.5.3/"`）。
- **文档/台账（5）**：`spec/README.md`（删历史基线索引行，改归档指针）、`Makefile`（L336 注释去 `(excl. historical SimRISC-0.5.3)`）、`.tao/knowledge/MEMORY.md`（L67 路径→归档路径）、`.tao/knowledge/lessons.md`（L133 路径→归档路径）、`.tao/tasks/spec/SPEC-109t-…md`（L152 路径→归档路径，**仅此一行**）。
- 本任务书 `.tao/tasks/spec/SPEC-111t-…md`（完成区 + 状态）；证据脚本与日志在 `.work/`（gitignored）。

**处置说明（任务书「改动清单」第 2/3/5 项的二选一）**：
1. **3 处硬编码排除：选「删除」**。理由：移动后 `.tao/archive/**` **不在任一脚本的扫描面内**——`check_asm_prose.py` 默认扫 `spec/ docs/ .tao/knowledge/contract-* .tao/adr`，`check_spec_codeblocks.py` 只扫 `spec/`，`check_scope.py` 只扫 `tools/ contracts/ spec/ tests/ docs/ + Makefile/README/AGENTS`；保留一个指向不存在路径的 guard 即死代码。故连同其分支一并删除（非留空壳）。反例自检证明删除后门控**仍有效**：临时把历史目录放回 `spec/` ⇒ `check-spec-codeblocks` rc=1（27 条 FAIL）、`check-asm-prose --strict` rc=1（142 violations）⇒ 还原 ⇒ 双绿。
2. **`spec/README.md`：删索引行 + 保留一句归档指针**（放 `spec/README.md`，未另建 `.tao/archive/README.md`）。指针措辞用「`SimRISC-0.5.3/` 原在 `spec/` 目录下，现已归档至 `.tao/archive/SimRISC-0.5.3/`」，**不写旧路径字面量 `spec/SimRISC-0.5.3`**，以免与验收标准 2「grep 清零」冲突。
3. **台账叙述：订正为归档路径**（`.tao/knowledge/MEMORY.md` L67、`.tao/knowledge/lessons.md` L133）——均为**生效**台账/规则行（非历史日志），保留旧路径会成悬空引用。
   - **`MEMORY.md` L74 未改**：该行只含「SimRISC 0.5.3 编号」概念，**不含 `spec/SimRISC-0.5.3/` 路径**（任务书「L67/L74」表述与实际不符，L74 无需动）。
   - **`SPEC-109t` 处置（用户裁定）**：仅订正 **L152**（豁免清单散文条目）；**L332 保留不改**——L332 位于该任务书**完成区**的逐字命令输出快照（`$ git grep …` 的真实输出行 `spec/SimRISC-0.5.3/...  ← 历史版本`），改写即篡改历史证据。

**用户裁定（原话落盘，2026-10-06）**：
- 问题「`.tao/tasks/spec/SPEC-109t-…md`（状态=已验证 的历史任务书）L152/L332 含 `spec/SimRISC-0.5.3/`，如何处置？」→ 用户答：**「一并订正 SPEC-109t 该两行」**。
- 追问「L332 是**完成区里的逐字命令输出快照**（非普通引用），改写会篡改历史证据，如何处置？」→ 用户答：**「仅订正 L152，L332 保留为历史快照（推荐）」**（最终采用）。

**验收结果（真实输出）**：
```
$ git status --porcelain -uall
R  "spec/SimRISC-0.5.3/SimRISC-00-…md" -> ".tao/archive/SimRISC-0.5.3/SimRISC-00-…md"   (×5)
 M .tao/knowledge/MEMORY.md / lessons.md / SPEC-109t…md / Makefile / spec/README.md
 M tools/spec/check_asm_prose.py / check_scope.py / check_spec_codeblocks.py

$ test -e spec/SimRISC-0.5.3 ; echo $?      → 1  （不存在）
$ ls -1 .tao/archive/SimRISC-0.5.3 | wc -l  → 5  （5 文件齐全）

$ grep -rnI --exclude='*.pyc' --exclude-dir=__pycache__ "spec/SimRISC-0\.5\.3" \
    spec docs tools contracts tests Makefile README.md AGENTS.md manifests .tao/adr .tao/knowledge .tao/README.md
（无输出，EXIT=1 → 0 命中）
$ 全仓 grep（排除 .tao/archive/ 与 .tao/tasks/ 历史）→ 0 命中

$ make check         → EXIT=0 ; repository checks: PASS
$ make check-no-residue → EXIT=0
$ bash .work/evidence/SPEC-111t/run.sh → EXIT=0 ; == SPEC-111t evidence: ALL PASS ==
```
（完整输出见 `.work/log/spec/SPEC-111t-*.log` 与 `/tmp/opencode/SPEC-111t/run.out`。）

**新发现/坑**：
1. **`__main__` 脚本不自动写 `.pyc`**：改动 `check_scope.py`/`check_spec_codeblocks.py`（以 `python3 xxx.py` 直接运行）后，`tools/spec/__pycache__/*.pyc` **仍内嵌旧 docstring 字符串**，`grep -rn` 会「Binary file matches」假命中。须靠 `python -m compileall`（`make check` 已含）重建后才清零；扫描时应 `-I`/`--exclude-dir=__pycache__`。
2. **`git log --follow` 对「仅暂存、未提交」的 rename 无效**：staged rename 不在历史中，新路径 `--follow` 返回空。此阶段须以 `git diff --cached --summary`（`rename … (100%)`）+ 旧路径 `git log`（`86fdcc8 SPEC-013t: 归档 SimRISC 0.5.3 文档`）佐证；提交后 `--follow` 方可跨 rename。
3. **「指针说明」与「grep 清零」的张力**：若指针照写旧路径字面量，会与验收标准 2 冲突；用「`SimRISC-0.5.3/` 原在 `spec/` 下」的措辞即可两全（非规避——指针语义完整，旧路径不出现死链）。
4. **删除 guard 的正确性由反例证明，而非「绿」**：三门控删排除后仍需能失败；证据脚本内置「放回 `spec/`⇒FAIL⇒还原⇒回绿」，其中 `check-spec-codeblocks` 27 条 FAIL、`check-asm-prose` 142 violations 为真实反例。
5. **任务书条目漂移**：本任务书称 `Makefile` L302，实为 L336；称 `MEMORY.md` L67/L74 含路径，实际 L74 无路径。均按实际定位处置，未改动无关内容。

**遗留问题**：
- `git log --follow .tao/archive/SimRISC-0.5.3/…` 的**最终**验证需在 architect 提交本 rename 之后执行（当前 rename 仅暂存，`--follow` 尚不可用）；提交后应能追至 `86fdcc8`。
- 无其它未完成项。

## 审阅记录

#### 第 1 轮 engineer 自审

**方式**：自主逐行审查（全局 `subagent_depth=1`，无法嵌套子代理），对改动源 + 真实重跑对账；关键结论均附真实输出/退出码。

**逐项审查与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `check_asm_prose.py` 删 `_EXCLUDE_DIRS` 后 `_should_exclude` 的 dir 循环悬空 | ✅已修 | 一并删除 dir 循环，`_should_exclude` 仅查 `_EXCLUDE_FILES` | `--files spec/SimRISC-00…md` EXIT=0；默认/`--root` 模式均正常；`make check` EXIT=0 |
| F2 删除目录排除会改变 `--root` 模式行为（历史目录不再被跳过） | ✅已修（设计如此） | —— | 反例自检：放回 `spec/` ⇒ `check-spec-codeblocks` rc=1、`check-asm-prose --strict` rc=1（证明「能失败」）；还原后双绿 |
| F3 指针句若含 `spec/SimRISC-0.5.3` 字面量将违反验收标准 2 | ✅已修 | 措辞改为「`SimRISC-0.5.3/` 原在 `spec/` 下，现已归档至 …」 | 活文件 grep 0 命中（EXIT=1） |
| F4 `SPEC-109t` 是否连带改 L332 | ✅已修（按用户两轮裁定） | 仅改 L152；L332 保留为完成区命令输出快照 | 用户原话已落盘（完成区「用户裁定」） |
| F5 `MEMORY.md` L74 是否含路径 | ✅已核 | 未改 | L74 实测不含 `spec/SimRISC-0.5.3/`（仅「SimRISC 0.5.3 编号」概念） |
| F6 陈旧 `.pyc` 内嵌旧字符串致 grep 假命中 | ✅已核 | 未改源码（由 `compileall` 重建） | `make check` 后 `__pycache__` 二进制 grep = 0 |
| F7 `check_qfc_coverage.py`/`validate_encoding.py` 的「SimRISC 0.5.3」 | ❌不改（任务书明确） | —— | 二者为**来源概念**表述、非路径；grep 无 `spec/` 前缀 |
| F8 越界/残留检查 | ✅已核 | —— | `git status -uall` 仅 5 R + 8 M（+ 本任务书）；`contracts/ tests/vectors/ components/` 零改动；residue 模式无匹配 |

**其它核对**：5 文件移动前后 `md5sum` 逐条相同；`git diff --cached --summary` 5×`(100%)` rename；3 个门控脚本内 `SimRISC-0.5.3` 字样总数 = 0（grep）；`spec/README.md` 表格结构完好（删行后加 blockquote，`### 环境` 紧随）。

**判决**：无未修 finding（F1–F4 已修并复验，F5–F8 已核实/按规不改）。状态置 `待验收`，返回主会话。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：2026-10-07

---

**1. 证据脚本审查（`.work/evidence/SPEC-111t/run.sh`）**

| 检查项 | 结果 |
|--------|------|
| 无 `tee`（不吞退出码） | ✅ 所有命令直接 `> log 2>&1; rc=$?` |
| FAIL 路径存在 | ✅ `ck`/`ck_rc` 两支 `[PASS]`/`[FAIL]`，无恒真 |
| 反例注入完整性 | ✅ `cp -a` 注入→门控 FAIL→`rm -rf` 还原→md5 比对→回绿 |
| 注入有效性检查 | ✅ `git status --porcelain` 检查注入是否产生改动 |
| 退出码传播 | ✅ `FAIL=0`；任一 `[FAIL]` 设 `FAIL=1`；末尾 `$FAIL` 判退出 |
| **脚本缺陷** | ⚠️ 第45行 `git diff --cached --summary` 检测暂存区 rename——提交 `39281b9` 后暂存区已空，此检查恒报0。**非产物缺陷**，建议改为 `git show --name-status HEAD` 或条件判断。 |

---

**2. 重跑证据脚本（真实输出）**

```
$ bash .work/evidence/SPEC-111t/run.sh > /tmp/opencode/SPEC-111t-review/run.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=1
```

输出（19 PASS /1 FAIL）：
```
== SPEC-111t evidence @ 2026-10-06T21:02:27Z ==

-- 1. 移动结果 --
[PASS] 旧目录不存在  期望=不存在 实际=不存在
[PASS] 归档目录存在  期望=存在 实际=存在
[PASS] 归档恰含 5 个 .md  期望=5 实际=5
[FAIL] 5 文件以 100% rename 暂存  期望=5 实际=0
[PASS] 旧路径有历史（建立提交）  期望=非空 实际=39281b9 WIP: SPEC-111t 归档 SimRISC-0.5.3（待验收）

-- 2. 旧路径引用清零（活/生效文件）--
[PASS] live 文件命中数  期望=0 实际=0
[PASS] 全仓命中数（排除 .tao/archive/ 与 .tao/tasks/ 历史）  期望=0 实际=0

-- 3. 无死排除代码（3 个门控脚本）--
[PASS] 3 脚本剩余 'SimRISC-0.5.3' 字样总数  期望=0 实际=0

-- 4. 不变量 --
[PASS] contracts/tests/vectors/components 改动文件数  期望=0 实际=0
[PASS] check-patch-tree (退出码)  期望=0 实际=0
[PASS] 补丁计数不变  期望=89 实际=89

-- 5. 门控全绿 --
[PASS] make check (退出码)  期望=0 实际=0
[PASS] make check-no-residue (退出码)  期望=0 实际=0

-- 6. 反例自检 --
[PASS] 注入有效性  期望=>0 实际=1
[PASS] 注入后 check-spec-codeblocks 应 FAIL  期望=rc≠0 实际=rc=1 (27条FAIL)
[PASS] 注入后 check-asm-prose --strict 应 FAIL  期望=rc≠0 实际=rc=1 (142 violations)
[PASS] 还原：spec/SimRISC-0.5.3 已移除
[PASS] 还原：归档目录 md5 未变
[PASS] 还原后 check-spec-codeblocks  期望=0 实际=0
[PASS] 还原后 check-asm-prose --strict  期望=0 实际=0
```

唯一 FAIL 项「5 文件以 100% rename 暂存」：**时序问题**（architect 已提交 `39281b9`，暂存区清空）。`git show --name-status 39281b9` 已独立证实 5× R100 rename。**非产物缺陷，不影响判决。**

---

**3. 独立逐项验证（reviewer 独立执行，不采信 engineer 输出）**

| # | 验收项 | 命令 | 真实输出 | 结果 |
|---|--------|------|---------|------|
| 1 | 旧目录不存在 | `test -e spec/SimRISC-0.5.3; echo $?` | `1` | ✅ |
| 1 | 归档恰含5文件 | `ls -1 .tao/archive/SimRISC-0.5.3/ \| wc -l` | `5` | ✅ |
| 1 | blob 内容一致 | `git ls-tree` 对比5文件 blob sha | 5× `same` | ✅ |
| 1 | rename 100% | `git show --name-status 39281b9` | 5× `R100` | ✅ |
| 1 | git log --follow | `git log --follow --oneline -- .tao/archive/.../SimRISC-00-*.md` | `39281b9→86fdcc8→bb98fff→...` | ✅ |
| 2 | 引用清零 | `grep -rnI "spec/SimRISC-0\.5\.3" spec docs tools ...` | 无输出，EXIT=1 | ✅ |
| 2 | 全仓宽搜 | `grep ... . \| grep -v archive \| grep -v tasks` | 无输出，EXIT=1 | ✅ |
| 3 | 3脚本零字样 | `grep -c "SimRISC-0.5.3" 3脚本` | `0:0:0`，EXIT=1 | ✅ |
| 4 | 不变量零改动 | `git status -- contracts tests/vectors components` | 空 | ✅ |
| 5 | make check | `make check` | EXIT=0；repository checks: PASS | ✅ |
| 5 | check-patch-tree | 日志内 | 2 component(s), 89 patches OK | ✅ |
| 5 | check-lit | 日志内 | 60/60 Passed | ✅ |
| 5 | check-no-residue | `make check-no-residue` | EXIT=0；PASS | ✅ |
| 5 | check-asm-prose | 日志内 | PASS (0 violations) | ✅ |
| 5 | check-spec-codeblocks | 日志内 | PASS (623 instruction line(s) checked) | ✅ |
| 5 | check-scope | 日志内 | PASS | ✅ |
| 5 | validate_encoding | 日志内 | 227 条记录 OK | ✅ |
| 6 | SPEC-109t L152 | `grep -n "SimRISC-0.5.3" SPEC-109t` | L152: `.tao/archive/SimRISC-0.5.3/**` | ✅ |
| 6 | SPEC-109t L332 | `sed -n '330,335p' SPEC-109t` | 保留原文 `spec/SimRISC-0.5.3/...  ← 历史版本` | ✅ |

---

**4. 独立注入（与 engineer 不同方式）**

**方式**：直接 `cp -a .tao/archive/SimRISC-0.5.3 spec/SimRISC-0.5.3`（不走脚本内置逻辑）。

**注入前 md5**（`/tmp/opencode/SPEC-111t-review/independent-md5.pre`）：
```
0847be3824a5e97110a247589574f101  SimRISC-00-指令系统设计.md
26b1b81d485b167f38fc16c19715bdb3  SimRISC-03-浮点类指令.md
be543b0991640904524518c8d1e7cbe7  SimRISC-01-数据类指令.md
db8b00000ec29390e3dee2428670eb9c  SimRISC-02-地址类指令.md
de2971926d5af43b91193589e5a24b64  SimRISC-04-系统类指令.md
```

**注入有效性**：`git status --porcelain -- spec/SimRISC-0.5.3` → `?? spec/SimRISC-0.5.3/` ✅

**注入后门控**：
- `check-spec-codeblocks`: EXIT=1，27 条 FAIL（样例：`'ldm.sb' 操作数个数 4 不在合法集合 [2]`）✅
- `check-asm-prose --strict`: EXIT=1，142 violations ✅

**还原**：`rm -rf spec/SimRISC-0.5.3` → `test -e` 确认不存在 ✅

**还原后 md5**（`/tmp/opencode/SPEC-111t-review/independent-md5.post`）：
```
0847be3824a5e97110a247589574f101  SimRISC-00-指令系统设计.md
26b1b81d485b167f38fc16c19715bdb3  SimRISC-03-浮点类指令.md
be543b0991640904524518c8d1e7cbe7  SimRISC-01-数据类指令.md
db8b00000ec29390e3dee2428670eb9c  SimRISC-02-地址类指令.md
de2971926d5af43b91193589e5a24b64  SimRISC-04-系统类指令.md
```

`diff pre post` → exit=0（完全一致）✅

**还原后回绿**：
- `check-spec-codeblocks`: EXIT=0 ✅
- `check-asm-prose --strict`: EXIT=0 ✅

---

**5. 工作区快照对账**

**验收前**：`git status --porcelain -uall` → 仅任务文件自身修改（审阅记录待填）
**验收后**：`git status --porcelain -uall` → 同上（注入已清除，无残留）
**与 39281b9 文件集比对**：5× R100 + 9× M，与完成区「修改文件」声明一致
**越界检查**：`contracts/`、`tests/vectors/`、`components/` 零改动 ✅

---

**6. 约束核验**

| 约束 | 结果 |
|------|------|
| 临时目录 `/tmp/opencode/SPEC-111t-review/` | ✅ 所有日志/备份在此 |
| 未提交 git | ✅ `git status` 仅任务文件修改 |
| 禁 `git checkout/restore/stash` | ✅ 全程 `cp`/`rm`，未使用 |
| `tee` 不吞退出码 | ✅ 证据脚本与独立验证均用 `> log 2>&1; rc=$?` |
| 不改产物 | ✅ 归档目录 md5 注入前后一致 |

---

**判决：Accepted**

工程师产出满足任务书全部验收标准与硬约束：

1. ✅ `spec/SimRISC-0.5.3/` 不存在；`.tao/archive/SimRISC-0.5.3/` 恰含5文件；内容 blob sha 完全一致
2. ✅ 引用清零（grep 0命中）
3. ✅ 门控全绿（`make check` EXIT=0，含全部检查器；`check-no-residue` EXIT=0；`check-patch-tree` 89 未变）
4. ✅ 反例门控有效（注入→FAIL 27+142→还原→回绿），独立注入验证通过
5. ✅ 不变量零改动（contracts/tests/vectors/components）
6. ✅ SPEC-109t 仅 L152 订正、L332 保留，符合用户裁定
7. ✅ `git log --follow` 可追至 `86fdcc8`
8. ✅ 零越界

证据脚本「rename 暂存检查」FAIL 为时序问题（提交后暂存区为空），非产物缺陷——建议 engineer 后续修正脚本检查逻辑。

#### architect 提交记录（2026-10-07）

- **档位**：`WIP:`（任务书状态 `待验收`，reviewer 未验收）。
- **提交号**：`39281b9` — `WIP: SPEC-111t 归档 SimRISC-0.5.3（待验收）`（本地，**未 push**；`git status -sb` = `ahead 1`）。
- **staging 方式**：显式逐路径 `git add`（5 处 rename 已在索引中，另显式 stage 9 个修改文件）；**未用 `git add -A`**。
- **文件集对账**（`git diff --cached --name-status`/`--summary` vs 完成区「修改文件」声明）：**一致**。
  - rename：`spec/SimRISC-0.5.3/*.md`（5）→ `.tao/archive/SimRISC-0.5.3/*.md`，`R100` / `rename … (100%)`，`--numstat` 5×`0 0`（非删+增）✅
  - 修改：`tools/spec/{check_asm_prose,check_scope,check_spec_codeblocks}.py`、`spec/README.md`、`Makefile`、`.tao/knowledge/{MEMORY,lessons}.md`、`.tao/tasks/spec/SPEC-109t-…md`（**仅 L152**，L332 保留）、本任务书（共 9）✅
  - **漏提**：无。**多提**：无。**越界**：无。
  - 范围外零改动核对：`contracts/`、`tests/vectors/`、`components/` 无改动（`git status --` 三路径空）✅；无并行会话改动卷入（无其它 untracked/unstaged）✅
  - `git show --stat` 计 14 files（5 rename 显示 `| 0` + 9 修改），与声明逐条吻合。
- **`git log --follow` 验证**（提交后）：`git log --follow --oneline -- .tao/archive/SimRISC-0.5.3/SimRISC-00-指令系统设计.md` 输出首行 `39281b9`（本次）→ **`86fdcc8 SPEC-013t: 归档 SimRISC 0.5.3 文档`** → 更早 `bb98fff …`；**已能跨 rename 追至 `86fdcc8`** ✅（消除完成区「遗留问题」第 1 条）。
- **提交后工作树**：`git status --porcelain -uall` 除本段留痕追加外为空。
- **未 push**：按规则 push 由主会话在 `/complete` 后、将本任务本地提交 squash/amend 成单一「已验证」提交再执行。
