# M0 — DADAO 历史与设计理念

本目录收录 DADAO 的**历史**与**设计理念**（源自项目早期 wiki）。

## 素材

| 文件 | 内容 |
| --- | --- |
| `00-古法编程.md` | **DADAO 的发展历程**：0.1（2021）→ 0.2（2022）→ 0.3（2023）→ 0.4（2023）→ 202406 各版本更新；含本科毕设与课程致谢。 |
| `01-AI编程.md` | **DADAO-0628**：用 AI Agent 从零实现软件栈；四路 ISA 验证链；与前身 `gxt/DADAO` 的关系。贡献者：隋岩。 |
| `02-大道至简.md` | **设计理念 TAO**：设计顺序与 DRY；指令系统设计（8/6/6/6/6、取消 CZSO、立即数赋值、多寄存器、条件赋值）；寄存器设计（分组、RB、RAS、rf0）。 |

## 其它仓库级文档

| 文件 | 内容 |
| --- | --- |
| `spec/assembly-list.md` | **DADAO 汇编指令完整列表**（自动生成，256 条 = M1 178 + excluded 78；含模板/示例/操作数/立即数范围 u·s/编码/lit 覆盖/llvm-mc 验证；生成器 `tools/llvm/gen_asm_list.py`） |
| `spec/component-patching.md` | **组件补丁组织与构建编排规范**（v5 规范层，2026-09-23 生效）：树形补丁集 + 一文件一补丁 + `git apply`；四断言由 `make check` 的 `check-patch-tree` 校验 |
| `m2-spec-planning.md` | **M2 规范规划（讨论稿）**：规范判据（RFC 2119 + 业界对标 + 机器可检查）、业界参考、N1–N16 映射、`spec/` 对照结论、三层结构、待裁决项 |
| `m1-retrospective.md` | **M1 里程碑回顾**：事实快照 / 资产地图 / 过程度量 / 时间线 / 被否决方案 / 死胡同 / 风险台账 / 0628 对照 / M2 交接 / 复现手册 / 术语 / 审计链 |
| `impact-matrix.md` | Spec 冻结影响矩阵（章节变更 → 下游合约/实现回归定位） |
| `repository-layout.md` | 仓库布局与 `.work/` 一次性工作区约定 |
| `integ-interface-alignment.md` | 跨模块接口对齐核对清单（`INTEG-003t` 产出） |
| `testcases-009t-audit.md` | ISA 向量逐族重推导审计记录（`TESTCASES-009t` 产出） |
| `issues.yaml` | Issue registry（M1-gate 判据 + 各模块 issue 台账） |
| `self-consistency.md` | DADAO 规范自洽性审查方法（早期素材） |

## 说明

- 这两份是**原始素材**（早期 wiki 文档，属 0.4.1 时代），供后续 M0 讲义**引用/改写**；其中出现的旧助记符（如 `setzw`/`orw`/`unimp`）与旧约定，以当前规范为准。
- 后续据此整理为 **lecnote 格式**的 M0 讲义（历史篇、理念篇），并补「课程与项目路线」（M0/M1/M2 + 两条深入路线：OS→LFS、chipyard→FPGA）。
- 相关项目知识：`adr-0001`（greenfield 重建）、`MEMORY.md`（0.5.3 与 0.4.1 的差异）。
