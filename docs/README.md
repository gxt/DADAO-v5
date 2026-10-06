# docs/ — 仓库级文档索引

本目录收录 DADAO 的仓库级文档；**历史与设计理念素材**已移至 `DDLN/`（Dadao Lecture Notes）。

## 其它仓库级文档

| 文件 | 内容 |
| --- | --- |
| `.tao/knowledge/contract-asm-list.md` | **DADAO 汇编指令表（新语法，生成投影）**：228 条，按 **取数存数/寄存器复制/16位立即数操作/64位数据运算/64位地址运算/控制流/浮点运算/32位数据运算/16位数据运算/8位数据运算/其它/待定** 分章，列为 助记符 / format / feature / 汇编形式（字段名） / id（自动生成）；**浮点运算（44 条，`scope: fp`，已实现）与待定（11 条，deferred）**，其余 152 条为 `scope: m1` 当前有效书写形式 |
| `spec/Toolchain-01-汇编语言.md` | **DADAO 汇编语言规范（v1.1，生效 2026-09-25；修订 2026-09-28：双目的/多寄存器语法）**：词法/记号/地址表达式 `[]`/寄存器组 `{}` 与条件 `?`/格式类语法/伪指令与指导符/诊断/往返/实现缺口 |
| `spec/Process-01-组件补丁组织与构建编排.md` | **组件补丁组织与构建编排规范**（v5 规范层，2026-09-23 生效，rev. 2026-09-25）：树形补丁集 + 一文件一补丁 + `git apply`；`patches/` 为纯镜像、清单在 `components/<name>/series`；五断言由 `make check` 的 `check-patch-tree` 校验 |
| `m2-spec-planning.md` | **M2 规范规划（讨论稿）**：规范判据（RFC 2119 + 业界对标 + 机器可检查）、业界参考、N1–N16 映射、`spec/` 对照结论、三层结构、待裁决项 |
| `.tao/archive/M1/m1-retrospective.md` | **M1 里程碑回顾**（**已归档**，2026-10-03 移入 `.tao/archive/M1/`）：事实快照 / 资产地图 / 过程度量 / 时间线 / 被否决方案 / 死胡同 / 风险台账 / 0628 对照 / M2 交接 / 复现手册 / 术语 / 审计链 |
| `impact-matrix.md` | Spec 冻结影响矩阵（章节变更 → 下游合约/实现回归定位） |
| `repository-layout.md` | 仓库布局与 `.work/` 一次性工作区约定 |
| `integ-interface-alignment.md` | 跨模块接口对齐核对清单（`INTEG-003t` 产出） |
| `testcases-009t-audit.md` | ISA 向量逐族重推导审计记录（`TESTCASES-009t` 产出） |
| `.tao/knowledge/issues.yaml` | Issue registry（M1-gate 判据 + 各模块 issue 台账） |
| `self-consistency.md` | DADAO 规范自洽性审查方法（早期素材） |
