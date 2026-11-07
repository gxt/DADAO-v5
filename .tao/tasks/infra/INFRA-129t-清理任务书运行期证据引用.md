# INFRA-129t: 清理任务书中的运行期证据引用（fresh clone L1 可绿）

**模块**：infra
**项目里程碑**：M11
**依赖**：无（与 `GEM5-030t` 文件域不重叠）
**状态**：待开始

## 背景与事实

新节点是 **fresh clone**，跑 `make check`（L1）时 `check-knowledge-refs` 失败：

```
结果: FAIL (20 悬空 `.work/**` 引用)
```

原因是若干任务书/知识文件里写了**具体运行期证据文件**（`<运行期目录>/evidence/<任务>/run.sh`、`<运行期目录>/log/...`）。这些文件只在跑过该任务的机器上存在，fresh clone 上没有 ⇒ 判悬空。主控机之所以通过，只是因为本机恰好有这些文件。

这违反「任务书不得写运行期路径」，也让新机器无法直接拿 L1 绿。

## 目标

把下列位置中**指向运行期证据/日志的具体文件或目录引用**，改成「运行期证据（未归档）」「运行期日志（未归档）」或等价措辞；保留原句的结论与上下文，不改判据、不改结论。

- `.tao/knowledge/MEMORY.md:78`
- `.tao/knowledge/refs/DADAO-0628-对照分析.md:12,76`
- `.tao/knowledge/refs/GEM5-021t-baseline-findings.md:60`
- `.tao/tasks/gem5/GEM5-019t-SYS_ELAPSED与TICKFREQ时钟一致.md:212`
- `.tao/tasks/infra/INFRA-121t-运行期日志命名清理.md:62`
- `.tao/tasks/integ/INTEG-053t-cfxha重编号与作用域.md:199,214,224`
- `.tao/tasks/spec/SPEC-184t-Node-D10与ISS-340收口.md:155,158,183`
- `.tao/tasks/spec/SPEC-185t-spec非spec引用清理.md:87,113,125`

注意：`check-knowledge-refs` 对**构建树/源码树**前缀有豁免；只处理「证据/日志」这类具体运行期路径，不要顺手改豁免项，也不要改 `spec/` 与 `contracts/`。

## 范围 / 非范围

**在范围内**：上述文件与行、本任务书、`milestones.md`。

**不在范围**：门控逻辑（`check_knowledge_refs.py` 不改）、spec/contracts、任何代码、其它任务书。

## 验收标准

1. **模拟 fresh clone**：在仓库外临时目录用 `git archive HEAD`（或 `git clone` 到临时目录）导出一份**不含运行期目录**的树，对这份树跑 `python3 tools/infra/check_knowledge_refs.py --root <临时树>` ⇒ **rc=0、悬空 0**。
2. 主工作树 `make check`（L1）rc=0。
3. 逐行核对：只改措辞，报告/结论/数字不变（给出 `git diff` 统计与抽样对照）。
4. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是「让新机器可直接 L1 绿」的前置清理；不新增文档、不改门控。
- 若某处引用其实是**长期证据**（例如确实要入库的快照），改为指向仓库内可跟踪路径，而不是删掉结论。
