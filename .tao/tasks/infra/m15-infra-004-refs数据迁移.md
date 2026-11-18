# m15-infra-004: refs 活数据源迁移 + 死引用通用检查

**模块**：infra
**项目里程碑**：M15
**依赖**：`m15-infra-002`（已删 9 个孤儿；本任务接着处理剩余 20 个文件）——分支直接基于 `m15-infra-002` 的 WIP 提交
**可并行分片**：否（跨 tools/tests/docs）
**预估**：3–4 h
**档位**：中改
**状态**：待开始

## 背景（用户 2026-11-18）

`m15-infra-002` 在删 `.tao/knowledge/refs/` 前核查发现：**20 个文件仍被非归档活文件引用，其中 13 份是代码的输入/输出默认值**（删了会断 `check-gem5-decode`、gem5-SE 长尾驱动、M13 差分矩阵来源）。任务停在「待裁定」。

用户裁定：
1. **不做归档**（002 的 9 个孤儿已删）。
2. **先不加门控**，本任务做**迁移 + 通用检查**；门控如何接入另议。

## 目标（三件，按顺序）

### 1. 迁移 13 份活数据源出 refs，并改全部消费者

落点：**`tests/data/`**（新建；机器可读的测试输入/基线数据）。若 `check-dirs` 对 `tests/` 有目录白名单，**先在该白名单登记 `data/`**（登记不等于新增门控，是让现有门控认识新目录；若这被判为「改门控」，停在完成区写待裁定）。

逐份列出：新路径、性质（输入默认值 / 就地刷新的工作数据 / 报告唯一来源）、消费者 `文件:行`、改动前后行为等价证据。

已知 13 份（以现场 `grep` 为准，不照抄）：

- `GEM5-002t-semantic-matrix.tsv` — `gen_decode_table.py` 直接读、`refresh_matrix_notes.py` 就地刷新、`check_b6/b7/converge` 输入、`make check-gem5-decode`
- `GEM5-021t-baseline-summary.json` — `run_gem5se_ratio_user.py` 的 `DEFAULT_CASE_LIST`
- `TESTCASES-104t-dynamic-summary.json` — `tset_matrix_user.py` 等
- `m13-001-static-3600s-full.json`、`m13-002-dynamic-3600s-full.json` — `gem5se_blocked_lists_user.py`、`three_platform_matrix.py`
- `m13-002-fp-diff.json`、`m13-003-int-diff.json`、`m13-005-acceptance.json` — 报告来源 / 生成器默认输出
- 其余由现场引用面清单补齐（`.tao/knowledge/refs/` 逐文件 × 非归档引用）

**就地刷新类**（`refresh_matrix_notes.py` 会改写 `GEM5-002t-semantic-matrix.tsv`）要特别说明：迁移后写路径如何解析、写入是否有门控保护（当前无）。

### 2. 迁移后清空 `.tao/knowledge/refs/`

剩余 11 份人读报告（13 份迁走后）**直接删除**（用户已定不归档）。删后目录必须不存在。

### 3. 死引用通用检查（**只出脚本，不注册门控**）

写 `tools/infra/check_dead_refs.py`（或同职责的单文件）：

- 扫描面：`tools/**/*.py`、`tests/**/*.py`、`Makefile` 中的**仓内路径字符串常量**；
- 判据：解析出的仓内路径（排除 `.work/`、`/tmp/`、URL、glob、`<…>` 占位）必须存在于工作树；
- 输出：缺失路径 + 引用处 `文件:行`；存在缺失 ⇒ 非零退出；
- **必须能 FAIL**：给出一次注入证明（把一个路径改错 ⇒ 红，`cp`+md5 还原 ⇒ 绿）；
- **不接入 `make check`、不加 Makefile 目标**（用户明确「先不要加门控」）；用法写进脚本 docstring。

## 验收（逐条贴真实 rc）

1. `ls .tao/knowledge/refs` → `No such file or directory`（rc=2）。
2. `tests/data/` 下 13 份在位，md5 与迁移前逐一致（`git show <base>:<old>` 对比）。
3. 全仓 `grep -rn "knowledge/refs"`（排除 `.tao/archive/**`、`.tao/tasks/**`、`.cache/**`）= **0**。
4. 消费者真实跑绿：`make check-gem5-decode`、`make check-wuming-cycles`，以及 gem5-SE 长尾驱动的 `--help`/清单类调用（不跑长任务）。
5. `check_dead_refs.py` 对当前树 rc=0；注入 1 路 ⇒ rc≠0；还原 ⇒ rc=0。
6. `make check-knowledge-refs`、`check-dirs`、`check-contracts-dir`、`check-no-residue`、`check-test-reports`、`check-tests-index` 全 rc=0。
7. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree（分支基于 `m15-infra-002` 的 WIP `1c29c916`）；禁改主工作树；**禁提交 git**。
2. **不改任何现有门控**、不改 `Makefile` 的 `check-*` 目标、不改版本号。
3. 组件补丁若因注释路径需重新导出（如 `components/gem5/patches/**`、chipyard `.scala.patch`），必须走 `make_patch` 且 `check-patch-tree` 回绿；不能手改 index。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。
5. 若发现第 14 份活数据源或消费者无法等价改写，**停在待裁定**，不要臆断。

## 待裁定

（执行中如有 → 写入本节并返回主会话）

## 审阅记录

（待填）
