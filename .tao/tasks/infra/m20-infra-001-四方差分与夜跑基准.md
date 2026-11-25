# m20-infra-001: 四方差分与夜跑基准定义（M20 首件）

**模块**：infra
**项目里程碑**：M20
**依赖**：M16 `tests/arch` 收尾；`m17-idl-020`/`m17-testcases-006`（274 例基线）
**可并行分片**：否（定义类任务，单写者）
**预估**：2–3 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（M20 定位，用户 2026-11-25）

M20 = **把当前能修的 issue 全修完**（`.tao/knowledge/issues-m20.yaml`）+ **给四方差分与夜跑定基准**。本任务是"定基准"那一半：现在四方差分（idl/qemu/gem5/chipyard）与夜跑（`night-run`）的成员、口径、GAP 裁决散落在任务书与脚本里，没有一份可引用的基准。

## 目标

1. **四方差分基准**（书面 + 可执行）：
   - 参与集：哪些镜像/例进四方（`tests/inst` 274 例 + `tests/arch` 服务集？），哪些只跑两方（并写明原因）；
   - 比对口径：签名槽 / 退出码 / 字节流，各自判据与容差（例如 gem5 的 GAP 项按 `expected-divergences.yaml` 裁决）；
   - 命令：一条可复现命令（含 `--platforms`、jobs、超时）；
   - 已知 GAP 与裁决入口：指向 `tests/arch/expected-divergences.yaml` 与 `issues-m20.yaml` 的对应条目。
2. **夜跑基准**：
   - 成员清单（真源对齐 `l3_run.DEFAULT_MEMBERS` / `night-run` 目标）；
   - 时长上限与"慢 vs 挂死"判据（心跳/进度）；
   - 失败判据与报告落点（`<test-artifacts>/night/<UTC>/`）；
   - 一条可复现命令。
3. 落点：`docs/Process-07`（门控分层）或 `.tao/knowledge/`（结论类）择一，**不新增重复文档**；若落 docs，需在 `docs/README.md` 加索引。

## 验收（逐条贴真实 rc）

1. 基准文档存在，且**每条口径都能指到真源**（脚本变量/门控/清单），不出现"应当""建议"这类不可执行表述。
2. 两条命令实跑（或 `--dry-run`/`--list`）能列出现场派生的成员与判据；给出真实输出与退出码。
3. 与现状对账：文档写的成员集 == 脚本现场派生集（`diff` 为空）；不一致项逐条解释。
4. 门控：`check-knowledge-refs`、`check-milestones-fresh`、`check-tests-index` 真 rc。

## 约束

独立 `git worktree`；不提交 git；只改文档 + 必要的引用（`docs/README.md`/`MEMORY.md` 指针）与本任务书；**不改**门控判据与脚本行为（如发现判据错误，写进「待裁定」另立任务）。
