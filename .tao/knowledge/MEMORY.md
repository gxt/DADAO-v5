# MEMORY — DADAO-v5 入口页（指针 + 反套用清单 + 权威文档地图）

> **维护规则**：本页只承载三样——① **入口指针**（导航）；② **DADAO 反套用清单**（与主流 ISA 的硬差异，防止 AI 用其他 ISA 经验补全）；③ **权威文档地图**（职责、读取顺序、冲突处置）。**不复述规范正文**；正文以 `spec/`、`contracts/`/`.tao/contracts/`、`.tao/adr/` 为准，复制必漂移。

## 当前交接（滚动；每次会话切换时更新，≤12 行）

- **2026-11-13**：M12 已验证 34 / 待开始 4；M13 已验证 41 / 待开始 23；进行中 **0**。
- 最近合入：`spec-005`（`ldm` 禁地址寄存器重叠）、`spec-006`（FMA 溢出按 IEEE）、`qemu-006`/`gem5-008`（`ldm` ILLI 实现）、`qemu-008`/`gem5-009`（FMA：两平台**本就合规**，只补断言）、`gem5-010`（hmon fixture 迁移）、`chipyard-027`（RTL ILLI）、`testcases-013`（235/235 三平台）。
- 下一件：`m13-testcases-014`（`02-reg-copy` 16 id，2–3 h）；`m12-chipyard-028`（重生成 `bootrom.tiny.hex`，补齐 `pending_followups` 最后一条）；`m12-chipyard-029`（FMA RTL，须按 spec 实测，**不得**用 QEMU/gem5 结论推定）。`028` 与 `029` 组件互斥，串行。
- 未决 issue：`ISS-410`（hmon 自装 workaround，待 028 后撤）、`ISS-416`（生成器漂移）、`ISS-417`（DDLD 残留扫描面）、`ISS-420`（FMA 常驻门控，载体 `testcases-021/022`）、`ISS-421`（chipyard README/changelog）。
- 节点：6 台同构（2×64 + 4×40 vCPU）。`207/208` 已引导（L1 绿、gem5 已建、musl 已建）；`ics150–180` 已同步仓库 + `.cache`，`install-host`/`musl`/`gem5` **未建**，chipyard conda 环境**全 6 台未建**。
- 裁定（原话见 `discussing.md` 末）：节点只作评测；测试时长 15m/6h/24h 分档且**不含构建时间**；`ldm` 禁重叠 / `stm` 允 / RA·RF 不适用。

## 入口指针

| 主题 | 真源 |
| --- | --- |
| 项目总览 / 里程碑 / 版本号 | 根 `README.md` |
| 当前进度 / 任务台账（待开始·进行中·已验证） / 裁定 | `.tao/knowledge/milestones-m12.md`（M12）+ `milestones-m13.md`（M13）；M11 及以前已归档（`.tao/archive/M11/`） |
| M11 归档 / 回顾 / 关闭 issue | `.tao/archive/M11/`（`README.md` / `m11-retrospective.md` / `issues-closed.md`） |
| M10 及以前归档 | `.tao/archive/M10/` … `.tao/archive/M1/` |
| M1–M9 历史 | `.tao/archive/M1/` … `.tao/archive/M9/` |
| 决策（ADR：架构 / 契约 / 流程） | `.tao/adr/` |
| 交互目录（`$TAO_ROOT` / 结构 / 模块表） | `.tao/README.md` |
| 角色 / 流程 / 命令 | `AGENTS.md`「角色与流程」+ `.opencode/agents/`、`.opencode/commands/` |
| 任务文件 | `.tao/tasks/<module>/` |
| 技术规范（上游 + v5 自定；索引 / 分册清单） | `spec/` + `spec/README.md` |
| 工程流程规范 + 仓库级索引 | `docs/Process-0x` + `docs/README.md` |
| DDLN 讲义（篇目索引） | `docs/DDLN/README.md`（**讲义，不是实现判据**；`DD-*` 是唯一真源，直接编辑） |
| 合约（归一化叙述 / 机器可读数据） | `.tao/contracts/contract-*.md` / `contracts/` |
| 代码模型 / 打包规范（REL26 边 ≤ 32 MiB；单 DSO 可执行区跨度 < 30 MiB） | `.tao/adr/adr-0036-code-model.md` §D4/D7 + `make check-code-range` |
| 构建 / 测试节点（机型 / 组网 / 软件包 / 就绪判据） | `.tao/knowledge/nodes.md` |
| 参考仓库（只读工作树 / 锁文件） | `.cache/refs/` + `manifests/` |
| issue / 教训 | `.tao/knowledge/issues.yaml` / `.tao/knowledge/lessons.md` |
| 历史归档 | `.tao/archive/M*/`（M1–M11） |
| 临时 / 一次性产物 | `/tmp/opencode/<任务ID>/` |

## DADAO 反套用清单

> 以下为**硬约束**；涉及这些内容时先查 `spec/` 对应篇目与相关 ADR，不得套用 RISC-V / x86 / ARM 经验补全。

- **页大小 64 KiB**，不是 4 KiB；VA 42 位 / PA 56 位，单 PTBR；不要套多级页表/4K 页。
- **IP = 当前指令地址**，不是 PC+4；分支/相对寻址按当前 IP 计算。
- **大端**，不是小端。
- **8 字节访问要求 8 字节对齐**；不要假设非对齐自动可用。
- **四组寄存器 `rd/rb/rf/ra` 分离**；指针在 RB，返回在 `rd8/rb8/rf8`；不要套统一 GPR/常规栈帧。
- **没有 CZSO/flags 条件码**；用 `cmp` 三值与 `br.*`/`cs.*`。
- **立即数是 16 位 wyde-position/分片拼接**，不是 RISC-V `lui/addi` 那套。
- **cfx 不是 CSR**：用 `trap`/`escape`/`cfx2rd`/`cfx2rc`；`escape` 偏移只允许 0/+4；`excp_cause_ip` 可写不等于安全边界。
- **两轴权限 + 保留 cfxha**：不要套 RISC-V 中断/CSR 模型；cfx 异常/中断按 `spec/DADAO-12` 的流程。
- **`rb0`/`ra0` 特殊**：`rb0` 是当前 IP，`ra0` 是 DADAO MemRAS；`ret rd0, 0` 等边界不能按其他 ISA 猜。
- **浮点/ABI**：`rf0` 状态位、`long double = binary128`、聚合/多返回值规则按 `contract-abi`/`spec/DADAO-21` 为准。
- **浮点行为以 IEEE-754 2019 为准（用户 2026-11-12）**：浮点设计与实现过程中出现的**任何差分**（本核 / QEMU / gem5 / hardfloat / `spec/SimRISC-07` 之间），一律以 **IEEE-754 2019** 规定的行为裁决；`SimRISC` 指令系统与各模拟器须据此**更新和修订**。**「与既有实现一致」不构成保留依据**；若确有偏离，必须在 spec 里显式写明为有意偏离并给理由。
- **测试机不是通用平台**：BootROM/RAM/复位/地址映射按 `spec/Machine-v5` + `ADR-0004`。
- **不确定时**：先查 `spec/` 对应篇目；不猜；spec 冲突或语义不明，直接问用户。

## 权威文档地图

### spec/ — 技术规范正文

- 承载 DADAO 的行为、编码、ABI、异常、测试机等**技术真源**。
- 入口：`spec/README.md`（分册清单、册维护约定、规范修订流程）。
- 实现前先查对应分册；DDLN 只作讲义，不作实现判据。
- 与其它文档冲突时，以 spec + 已 Accepted ADR 为准；冲突未消解时停下问用户。

### contracts/ 与 .tao/contracts/ — 合约与投影

- `contracts/`：机器可读数据（`opcodes.yaml`、合法性规则、cfx 别名等）。
- `.tao/contracts/`：人读归一化合约（`contract-isa`/`contract-abi`/`contract-see` 等）。
- 作用：投影 spec、门控与验收的输入；**不是第二套自由文本**。
- spec ↔ 合约不一致时，按门控修正源/投影，不静默选择一边。

### docs/Process-0x — 工程流程

- 承载角色、任务状态机、门控分层、测试组织、归档、文档规范。
- 入口：`docs/README.md`、`docs/Process-07-门控分层规范.md`。
- 只回答“怎么做工程”，不回答“DADAO 语义是什么”。

### .tao/adr/ — 决策与理由

- 承载架构/契约/流程决策；`Accepted` 决策有约束力。
- 决策变更按 `docs/Process-03`：新增 ADR、标 `Superseded`，或经用户授权的就地修订。
- ADR 与 spec/contract 冲突、或 ADR 本身不明时：**停下问用户**，不自行裁决。

## 历史与归档

- 任务台账：`.tao/knowledge/milestones-m12.md`（M12）+ `milestones-m13.md`（M13，均三分表：待开始 / 进行中 / 已验证；按任务书 `**项目里程碑**` 分派）；M11 及以前已归档，历史见 `.tao/archive/`。
- M10 完成任务书与 issue 快照：`.tao/archive/M10/`。
- 已归档 issue：`.tao/archive/M*/issues-closed.md`；活 `issues.yaml` 只留未关闭项。
- 一次性过程与长日志：运行期日志目录（可删、未归档）；临时产物：`/tmp/opencode/<任务ID>/`。
