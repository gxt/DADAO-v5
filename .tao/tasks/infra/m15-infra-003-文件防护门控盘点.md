# m15-infra-003: 文件防护门控盘点（防新增 / 防修改）

**模块**：infra
**项目里程碑**：M15
**依赖**：无
**可并行分片**：否（跨全部门控与目录）
**预估**：2–3 h
**档位**：小改（只调研与文档，不改门控实现）
**状态**：待开始

## 背景（用户 2026-11-18）

现有 `make check` 体系里有 60+ 个 `check-*` 目标，但**没有一张表说明「哪些门控在防止文件被新增或被修改」**。结果是：新增一个目录/文件时，没人知道会不会被门控挡住；改动一个受保护文件时，也不知道哪一层会红。

本任务只做**盘点与缺口分析**，**不新增、不修改任何门控**。

## 目标

产出一张**文件防护门控清单**，覆盖 `Makefile` 里全部 `^check-*:` 目标（现场 `grep` 计数，不写死），每条回答三个问题：

1. **是否扫描文件系统**（目录/文件），扫描面是什么（逐条写具体路径或 glob）。
2. **是否防新增**：白名单 / 许可集 / 新文件命名规则 / 覆盖要求。
3. **是否防修改**：sha256 锁 / git blob index / 内容逐字节比对 / 生成物一致性。

## 覆盖范围（必须逐条过，不得抽样）

`Makefile` 全部 `^check-[a-z0-9-]*:` 目标（当前 64 个，现场统计），以及它们调用的 `tools/**` 检查脚本。至少覆盖以下已知相关项并**核准其真实判据**（不得照抄本文措辞）：

- 白名单/防新增类：`check-dirs`、`check-contracts-dir`、`check-knowledge-dir`、`check-run-artifacts`、`check-no-residue`、`check-temp-dirs`、`check-test-reports`、`check-archive`
- 锁/防修改类：`check-spec-readonly`、`check-index-blobs`、`check-patch-tree`、`check-source-state`、`check-spec-drift`、`check-contracts-pending`、`check-musl-freshness`、`check-builtins-freshness`
- 命名/结构类：`check-asm-list`、`check-asm-list-drift`、`check-tests-index`、`check-tasks`、`check-milestones-fresh`、`check-writer-guards`
- 生成物一致性类：`check-wuming-cycles`、`check-decodetree-repro`、`check-instrinfo`、`check-interface`

输出表格列（每行一个门控）：

```
门控名 | 层级(L1/L2/L3) | 扫描面 | 防新增 | 防修改 | 判据出处(文件:行) | 缺口
```

## 缺口分析（本任务的核心产出）

1. **哪些目录没有白名单**：`tests/`、`tools/`、`docs/`、`.tao/`、`components/`、`manifests/`、`contracts/` 各自是否被某个门控约束「只能放什么」；列出无约束的目录与后果（如随手新建文件不会被拦）。
2. **哪些受保护文件只靠「人不改」**：没有 sha256 / blob 校验的规范类或配置类文件清单。
3. **重复与空白**：同一防护被两个门控覆盖（冗余）或某类防护完全没有（如「新增 `.py` 必须有 README 登记」目前只在 `tools/` 有？）。
4. **结论只给事实与缺口**，**不提改造方案**（改造另立任务）。

## 落点

- 主产出写入 `docs/Process-07-门控分层规范.md` 新增一节（`§N 文件防护门控清单`），或若该文件已过长，写入 `.tao/knowledge/` 并在 `Process-07` 留一行指针。
- 需给出「层级」时以 `Process-07` 现有分层表为准，**不自行改分层**。

## 验收（逐条贴真实 rc）

1. `grep -c "^check-[a-z0-9-]*:" Makefile` 的现场值与清单行数**相等**（差额必须逐条解释，不得静默略过）。
2. 表格每行的「判据出处」给 `文件:行`，抽查 10 行由 reviewer 现场核对存在且语义一致。
3. 缺口分析至少给出：无白名单目录清单、无哈希保护文件清单、冗余/空白各 ≥1 例（若确实没有，写「经核无」并给核验方法）。
4. 文档门控：`make check-knowledge-refs`、`check-dirs`、`check-test-reports` rc=0。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**。
2. **只写文档**：不改任何 `check-*` 目标、不改 `tools/**` 脚本、不改版本号。
3. 引用门控判据必须**读源码/读 `Process-07`**，不得凭门控名猜。
4. 临时文件放 `/tmp/opencode/m15-infra-003/`；`cp`+md5 还原。

## 待裁定

（无）

## 审阅记录

（待填）
