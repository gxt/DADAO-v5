# m20-infra-005: 私有目录清理门控（只报警不删除）

**模块**：infra
**项目里程碑**：M20
**依赖**：`m20-infra-004`（都动 `Makefile` ⇒ **串行，004 先**）
**可并行分片**：否（动 `Makefile` + `docs/Process-07` 门控清单，全局串行）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（用户 2026-11-28 裁定：私有目录清理门控**只报警、不自动删**）

`.work/private/<任务号>/` 是 m20-infra-003 引入的任务私有源/构建/安装树（`private_source.sh <c> <id>` 落 `.work/private/<id>/source/<c>`；m20-infra-004 再加 `.work/private/<id>/install` 与私有构建）。这些目录体量大、随任务收尾若不删会长期占盘。现无任何机械门控盯它们。

现实例证（可复验）：已验证任务 `m20-infra-003` 的私有目录现为 **1.1 G**，其任务书 `.tao/tasks/infra/m20-infra-003-*.md` `**状态**` = `已验证` ⇒ 应被本门控**真实判红**（删除动作由主会话/收尾执行，不写进门控）。

**任务号口径注意（落地前可复验，勿照抄 `check_temp_dirs.py`）**：`check_temp_dirs.py` 的 `_TASK_ID = ^[A-Z][A-Z0-9]*-\d{3,4}[a-z]?$` 是**旧 `PREFIX-nnn` 约定**，与本仓库现行 `mNN-<module>-<NNN[N]>`（如 `m20-infra-003`）**不匹配**。本任务扫描的私有目录名是现行 `mNN-` 格式 ⇒ 新脚本的任务号正则必须匹配**现行约定**（如 `^m\d+-\w+-\d{3,4}$`，含后缀时允许 `-<后缀>`），任务书查找走 `.tao/tasks/**/<任务号>[-*].md` 的 `**状态**` 字段；不得复制旧正则。

## 目标（分条，可验收）

1. 新增 `tools/infra/check_private_dirs.py` + `make check-private-dirs`，加入 L1 `_locked-check`（位置**紧邻 `check-temp-dirs`**，即 `_locked-check` 依赖列表里 `check-temp-dirs` 之后）。
2. 扫描 `.work/private/<任务号>/`（`--root` 可指向临时树自测）：
   - **豁免**：目录名是任务号且 `.tao/tasks/**` 任务书 `**状态**` ∈ {`待开始`,`待验收`,`待返工`}；
   - **FAIL**：目录名非任务号、任务号不存在、任务已验证、mtime > 阈值（默认 2 h，`--max-age-hours` 参数化）；
   - 输出**体积前 5 大** + 陈旧总数/总体积；**只报告不删除**（用户口径）；
   - 无扫描根 ⇒ **PASS**（不得 vacuous 失败，照 `check_temp_dirs.py` R2.5）。
3. `--self-test` 覆盖：陈旧 FAIL / 在用任务豁免 / 已验证 FAIL / 未知任务号 FAIL / 非任务号 FAIL / 缺根 PASS / 阈值注入 / 只列前 5 大 / 不删除。
4. **现实检验**：当前 `m20-infra-003` 的私有目录（1.1 G、已验证）应被**真实判红**（rc=1 且指名）；把它删掉后回绿（rc=0）——删除动作由主会话/收尾执行，**不写进门控脚本**。
5. **范围**：只加门控脚本 + `Makefile` 一行接线（`check-private-dirs:` + 加入 `_locked-check`）+ `docs/Process-07-门控分层规范.md` 门控清单表一行 + 帮助文本一行；不改清理策略、不动 `.gitignore` 语义。

## 验收（逐条贴真实 rc）

1. `make check-private-dirs` 真实 rc 对照：存在已验证任务的私有目录（现为 1.1 G 那一个）时 **rc=1**（指名该目录 + 体积）；删除后 **rc=0**。
2. `python3 tools/infra/check_private_dirs.py --self-test` **rc=0**（逐条注入可达 FAIL，含不删除断言）。
3. `make check` **全绿**（`check-private-dirs` 并入 L1 后不新增红；基线同红逐行 diff 判据）。
4. 证据脚本「运行期证据目录 `run.sh`」含「注入 → FAIL → `cp`+md5 还原 → 回绿」；每条断言有可达 FAIL。
5. `check-knowledge-refs`/`check-manifests-guard`/`check-tests-index` 不因本任务新增红。

## 约束

独立 `git worktree`；不提交 git；只改 `Makefile`（一行接线 + 帮助文本）、新增 `tools/infra/check_private_dirs.py`、`docs/Process-07-门控分层规范.md`（门控清单表一行）与本任务书；**不删除任何 `.work/private/**`**（只报告）；不改清理策略/`.gitignore` 语义；完成区不写具体 `.work/**` 路径。

## 审阅记录

### 第 1 轮 engineer 自审

- 逐行审查 `tools/infra/check_private_dirs.py`：任务号正则只认现行 `mNN-<module>-<NNN[N]>`（含 `-<后缀>`），负例 `foo` / `M20-INFRA-003` / `m20-infra-003-` 均不匹配；任务书查找走 `.tao/tasks/**` 的 `**状态**` 首 40 行。
- 判定口径：mtime 未超阈值 ⇒ 跳过（陈旧门控）；超阈值时在用状态豁免、其余判红；无根 PASS；扫描为只读，脚本无 `rm`/`unlink`/`rmtree`。
- 边界：符号链接子目录跳过（防 `du` 出界）；扫描失败 fail-closed；`du` 异常回落 0 不影响判红原因。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 旧 `check_temp_dirs.py` 任务号正则不匹配现行号 | ❌不修（不在本任务） | 新脚本另立 `_TASK_ID` | 负例/正例探针输出正确 |
| `make` 把失败 recipe 包装为 rc=2，非脚本 rc=1 | ✅已修（证据口径） | 证据脚本分列捕获脚本 rc 与 make rc | 存在：script=1/make=2；删除：0/0 |
| `.work` 跨 worktree 共享，证据脚本不能由自身路径推 repo 根 | ✅已修 | 改用 `git rev-parse --show-toplevel`（可 `REPO_ROOT` 覆盖） | 证据脚本 17/17 PASS |
| 环境既有基线红（check-patch-tree / check-musl-freshness / check-run-artifacts / check-interface / check-milestones-fresh / check-temp-dirs） | ⏸延后（非本任务引入） | 无 | 与 master 干净树失败集归一化后 `diff` 为空 |

### 第 1 轮 reviewer 验收

**重跑记录（均在本 worktree、仓库根执行，输出为本人终端真实输出）**

- `python3 tools/infra/check_private_dirs.py --self-test` ⇒ **rc=0**，13 条全 PASS（缺根 PASS / 新鲜未陈旧 / 空根 / 非任务号 / 未知任务号 / 已验证 / 待验收·待返工·待开始+`-work` 豁免 / 阈值 -1 h 注入判红后恢复 2 h 回绿 / 7 个陈旧只列前 5 大且降序 / 目录仍在）。
- `--root <不存在的目录>`（运行期临时树）⇒ **rc=0**（无根 PASS，非 vacuous 失败）。
- 任务号正则实测：`m20-infra-003`→组1 `m20-infra-003`；`m20-infra-003-work`→组1 `m20-infra-003`；`M18-001`/`foo`/`M20-INFRA-003`/`m20-infra-003-`/`m20-infra-12345` → 不匹配（按非任务号）；对照旧正则 `^[A-Z][A-Z0-9]*-\d{3,4}[a-z]?$`：`M18-001` 匹配、`m20-infra-003` 不匹配 ⇒ 确为现行 `mNN-<module>-<NNN[N]>`（含 `-<后缀>`）。
- **独立注入**：在私有目录扫描根（运行期目录）造 3 个 1 MiB、mtime 3 h 的子目录 —— `m20-infra-005`（待验收）/ `m20-infra-004`（已验证）/ `not-a-task`（非任务号）⇒ script **rc=1**，输出 `m20-infra-005: 状态 待验收 ⇒ 视为在用`（豁免）、`m20-infra-004: 任务 … 状态 已验证（非在用）`、`not-a-task: 目录名非现行任务号`；**运行后 `ls` 三目录全在**；删自造目录后 **rc=0**。
- **真实 rc 对照**（2 MiB / 3 h / 已验证号）：script **rc=1**、`make check-private-dirs` **rc=2**（make 输出 `Error 1` 即脚本 1 的包装码），指名 + `2.0 MiB`；删除后 script=0、make=0。
- 证据脚本「运行期证据目录内的 `run.sh`」重跑 ⇒ **rc=0，`evidence: PASS 17/17`**；`temp.restore-cp-md5 after=a1128910b92c4b77fe815eee05381e6d` 与完成区一致（非转述）。
- `make -k check` ⇒ **rc=2**，失败 7 项：check-patch-tree / check-index-blobs / check-run-artifacts / check-temp-dirs / check-musl-freshness / check-milestones-fresh / check-interface；`check-private-dirs` 在 L1 内 PASS。
- **基线对照**：`git worktree add --detach` 干净 master（`.work`/`.dadao` 软链同主树）跑 `make -k check` ⇒ rc=2，失败 6 项，与 worktree 归一化（路径 / `Makefile:N` / 时龄）后**逐行相同**；差集仅 `check-milestones-fresh`——红因为台账 `milestones-m20.md` 005 行含 `.work/` 路径（派单提交带入，台账不在本任务改动集，主会话 16:33 已在 master 订正）。注：`git archive master` 临时树直接跑会额外红 `check-dirs/check-no-residue/check-manifests-guard`（树内无 `.git`，`git ls-files`/`check-ignore` 失败），属环境差，故改用真 worktree 对照。

**约束核验**：脚本零删除调用（`grep -nw rm`=无命中；`unlink`/`rmtree` 仅出现在 R1.4 否定句文档串；无 `shutil`；运行后目录仍在）；`_locked-check` 仅新增 `check-private-dirs` 且紧邻 `check-temp-dirs`，对 master 61 vs 60 项、去新增后同序；`docs/Process-07` 仅 +1 行；`git status -uall` 恰 4 项（任务书 / Makefile / Process-07 / 新脚本），证据未入库；`make check-knowledge-refs`=0（0 具体 `.work/**` 引用）、`check-dirs`/`check-no-residue`/`check-tests-index`/`check-manifests-guard` 均 rc=0；任务书 `.work/` 引用全为 `<任务号>`/`<id>` 占位；前后快照：三份交付物（`Makefile` / `docs/Process-07` / 新脚本）审前审后 md5 一致（`db3fe8da…` / `1dc8b8d3…` / `a40a3ef2…`），改动面仅任务书（本轮审阅记录写入）；无越界改动。

**finding（不阻断）**：脚本文档串 R1.4 出现字面 `rmtree`/`unlink`（否定句），按"全文禁词"字面 grep 会命中；代码零删除调用、行为已验证，建议改措辞。

**判决：Accepted**

## 完成区

**测试结果**：`--self-test` 全 PASS（rc=0）；`make -k check` 与 master 干净树失败集逐行相同（归一化 Makefile 行号/时龄小数后 `diff` 为空）；本门控在 L1 内 PASS。证据脚本 17/17 PASS。
**修改文件**：新增 `tools/infra/check_private_dirs.py`；`Makefile`（`check-private-dirs:` + 加入 `_locked-check`、`.PHONY`、帮助文本）；`docs/Process-07-门控分层规范.md`（§7 门控清单一行）；本任务书。运行期证据目录内 `run.sh`。
**验收结果**：在 `.work/private/<已验证任务号>/` 造 2 MiB 陈旧目录 ⇒ 门控脚本 rc=1、`make check-private-dirs` rc=2（make 对失败 recipe 的包装码），输出指名目录 + 体积；删除后两者 rc=0。证据注入：任务书 `**状态**` 待验收→已验证 ⇒ FAIL；`cp` 还原后 md5 `a1128910…` 一致且 `cmp` 相同 ⇒ 回绿；含“只报告不删除”断言。
**新发现/坑**：① `make` 对失败 recipe 返回 2（脚本本身 1），验收须分列；② `.work` 在 worktree 间共享，证据脚本须靠 `git rev-parse` 定位仓库根；③ 基线红与 master 逐行相同：check-patch-tree / check-index-blobs / check-musl-freshness / check-milestones-fresh（台账 005 一句改动含私有目录路径）/ check-run-artifacts / check-interface / check-temp-dirs（`/tmp` 遗留）。
**遗留问题**：无新增；上述基线红均为既有问题（`check-milestones-fresh` 的台账行由主会话订正）。
