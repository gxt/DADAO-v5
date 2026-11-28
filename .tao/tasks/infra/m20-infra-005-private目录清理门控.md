# m20-infra-005: `.work/private` 清理门控（只报警不删除）

**模块**：infra
**项目里程碑**：M20
**依赖**：`m20-infra-004`（都动 `Makefile` ⇒ **串行，004 先**）
**可并行分片**：否（动 `Makefile` + `docs/Process-07` 门控清单，全局串行）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-28 裁定：`.work/private` 清理门控**只报警、不自动删**）

`.work/private/<任务号>/` 是 m20-infra-003 引入的任务私有源/构建/安装树（`private_source.sh <c> <id>` 落 `.work/private/<id>/source/<c>`；m20-infra-004 再加 `.work/private/<id>/install` 与私有构建）。这些目录体量大、随任务收尾若不删会长期占盘。现无任何机械门控盯它们。

现实例证（可复验）：`.work/private/m20-infra-003` 现为 **1.1 G**，其任务书 `.tao/tasks/infra/m20-infra-003-*.md` `**状态**` = `已验证` ⇒ 应被本门控**真实判红**（删除动作由主会话/收尾执行，不写进门控）。

**任务号口径注意（落地前可复验，勿照抄 `check_temp_dirs.py`）**：`check_temp_dirs.py` 的 `_TASK_ID = ^[A-Z][A-Z0-9]*-\d{3,4}[a-z]?$` 是**旧 `PREFIX-nnn` 约定**，与本仓库现行 `mNN-<module>-<NNN[N]>`（如 `m20-infra-003`）**不匹配**。本任务 `.work/private/*` 目录名是现行 `mNN-` 格式 ⇒ 新脚本的任务号正则必须匹配**现行约定**（如 `^m\d+-\w+-\d{3,4}$`，含后缀时允许 `-<后缀>`），任务书查找走 `.tao/tasks/**/<任务号>[-*].md` 的 `**状态**` 字段；不得复制旧正则。

## 目标（分条，可验收）

1. 新增 `tools/infra/check_private_dirs.py` + `make check-private-dirs`，加入 L1 `_locked-check`（位置**紧邻 `check-temp-dirs`**，即 `_locked-check` 依赖列表里 `check-temp-dirs` 之后）。
2. 扫描 `.work/private/*`（`--root` 可指向临时树自测）：
   - **豁免**：目录名是任务号且 `.tao/tasks/**` 任务书 `**状态**` ∈ {`待开始`,`待验收`,`待返工`}；
   - **FAIL**：目录名非任务号、任务号不存在、任务已验证、mtime > 阈值（默认 2 h，`--max-age-hours` 参数化）；
   - 输出**体积前 5 大** + 陈旧总数/总体积；**只报告不删除**（用户口径）；
   - 无扫描根 ⇒ **PASS**（不得 vacuous 失败，照 `check_temp_dirs.py` R2.5）。
3. `--self-test` 覆盖：陈旧 FAIL / 在用任务豁免 / 已验证 FAIL / 未知任务号 FAIL / 非任务号 FAIL / 缺根 PASS / 阈值注入 / 只列前 5 大 / 不删除。
4. **现实检验**：当前 `.work/private/m20-infra-003`（1.1 G、已验证）应被**真实判红**（rc=1 且指名）；把它删掉后回绿（rc=0）——删除动作由主会话/收尾执行，**不写进门控脚本**。
5. **范围**：只加门控脚本 + `Makefile` 一行接线（`check-private-dirs:` + 加入 `_locked-check`）+ `docs/Process-07-门控分层规范.md` 门控清单表一行 + 帮助文本一行；不改清理策略、不动 `.gitignore` 语义。

## 验收（逐条贴真实 rc）

1. `make check-private-dirs` 真实 rc 对照：存在 `.work/private/m20-infra-003` 时 **rc=1**（指名该目录 + 体积）；删除后 **rc=0**。
2. `python3 tools/infra/check_private_dirs.py --self-test` **rc=0**（逐条注入可达 FAIL，含不删除断言）。
3. `make check` **全绿**（`check-private-dirs` 并入 L1 后不新增红；基线同红逐行 diff 判据）。
4. 证据脚本「运行期证据目录 `run.sh`」含「注入 → FAIL → `cp`+md5 还原 → 回绿」；每条断言有可达 FAIL。
5. `check-knowledge-refs`/`check-manifests-guard`/`check-tests-index` 不因本任务新增红。

## 约束

独立 `git worktree`；不提交 git；只改 `Makefile`（一行接线 + 帮助文本）、新增 `tools/infra/check_private_dirs.py`、`docs/Process-07-门控分层规范.md`（门控清单表一行）与本任务书；**不删除任何 `.work/private/**`**（只报告）；不改清理策略/`.gitignore` 语义；完成区不写具体 `.work/**` 路径。
