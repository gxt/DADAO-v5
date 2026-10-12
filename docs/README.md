# docs/ — 工程文档索引（**给别人看**）

> **定位**：本目录收录 **工程流程规范（`Process-0x`）+ 仓库级索引 + `DDLN/` 讲义素材**，面向「**给别人看**」（读者 / 协作者）。结论 / 设计 / 口径（给自己看 = agent / 主会话）归 `.tao/knowledge/`；技术规范（上游基线 + v5 自定技术册）归 `spec/`。三分界口径见 `AGENTS.md`「文档分层与单一真源」。

## 工程流程规范（`Process-0x`）

| 文件 | 内容 |
| --- | --- |
| `docs/Process-01-组件补丁组织与构建编排.md` | **组件补丁组织与构建编排规范**：树形补丁集 + 一文件一补丁 + `git apply`；`patches/` 为纯镜像、清单在 `components/<name>/series`；五断言由 `make check` 的 `check-patch-tree` 校验 |
| `docs/Process-02-合约编写规范.md` | 合约（投影）文件组织、写法要点、版本管理 |
| `docs/Process-03-ADR编写规范.md` | ADR 判据、提醒义务、落点命名与模板、流程 |
| `docs/Process-04-里程碑归档规范.md` | 里程碑达成后的任务书 / 台账归档（判据、落点、README 模板、原台账处理、验收） |
| `docs/Process-05-里程碑TDD规范.md` | 里程碑测试驱动开发（三层向量 L1/L2/L3、规模与移植原则、反例门控、落点） |
| `docs/Process-06-spec目录保护规范.md` | `spec/` 目录保护：上游只读册只读引用、`spec/` 改动须用户事先授权、下发 / 验收 / 提交三处固定检查、只读册 `sha256` 哈希锁门控 |
| `docs/Process-07-门控分层规范.md` | **门控分层规范**：L1/L2/L3 分层定义与各层组成、触发点、新检查归属规则、层间不重复、每层须可达 FAIL、与 `AGENTS.md` 分工 |

> **不设版本号**：`Process-0x` 属**工程过程规范**（可逆、单项目），不设 `x.y.z` 版本，亦不见于根 `README.md` 版本表。

## 仓库级文档

| 文件 | 内容 |
| --- | --- |
| `docs/repository-layout.md` | **仓库布局**：纳入版本控制的目录（含三分界）、一次性工作区 `.work/`、持久对象库 `.cache/` |
| `docs/fp-oracle-design.md` | **FP 独立 oracle 方案**（被 `spec/README.md` 投影表、`contract-fp.md`、`contracts/fp_semantics.yaml` 引用） |

## 历史与设计理念素材（`DDLN/`）

| 文件 | 内容 |
| --- | --- |
| `docs/DDLN/README.md` | DDLN 索引 |
| `docs/DDLN/DD-A001-发展历程--古法编程.md` | **DADAO 的发展历程**：0.1（2021）→ 0.4（2023）各版本更新；含本科毕设与课程致谢 |
| `docs/DDLN/DD-A002-发展历程--AI编程-0628.md` | **DADAO-0628**：用 AI Agent 从零实现软件栈；四路 ISA 验证链；与前身 `gxt/DADAO` 的关系 |
| `docs/DDLN/DD-B001-大道至简--设计理念.md` | **设计理念 TAO**：设计顺序与 DRY；指令系统设计；寄存器设计 |
