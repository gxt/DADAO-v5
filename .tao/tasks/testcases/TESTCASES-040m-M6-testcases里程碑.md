# TESTCASES-040m: M6 testcases 里程碑

**模块**：testcases
**项目里程碑**：M6
**状态**：待开始
**目标**：M6 测试资产就位——新能力向量（调用约定/reloc/大帧/FP-RF 的 L1 编码 + L3 执行，**独立 oracle**）；lit 量产（骨架生成 + 期望值**从 `spec`/`contracts` 机械派生**、**禁反填**；快档入 `make check`、全量档 opt-in）；上游 IR 素材 + `lli` **值级对拍**；**Embench 接入**（board shim + 最小运行时 + `md5sum` 大端适配；首验收 = 最小基准 QEMU 正确退出码）。
**关联任务**：`TESTCASES-036t`、`TESTCASES-037t`、`TESTCASES-038t`、`TESTCASES-039t`

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tests/vectors/**`（新能力 L1/L3）、`tests/llvm/lit/**`（快档）、`tests/llvm/codegen/m6/**`、上游 IR 素材与 `lli` 对拍驱动、Embench 接入产物（`tests/**` 或 `components/embench-iot/**` 依赖）
- L1/L3 期望值**独立派生**（非从 LLVM/QEMU 反填）；计数由脚本/门控现场统计（**不写死**）
- 不回归：`make check`/`check-lit` EXIT=0
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）

## 审阅记录

#### 第 1 轮 reviewer 验收
（审查者独立验证：关联任务状态、产出存在性、oracle 独立性、门控重跑、判决）
