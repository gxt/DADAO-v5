# MEMORY — DADAO-v5 入口页（指针 + 反套用清单 + 权威文档地图）

> **维护规则**：本页只承载三样——① **入口指针**（导航）；② **DADAO 反套用清单**（与主流 ISA 的硬差异，防止 AI 用其他 ISA 经验补全）；③ **权威文档地图**（职责、读取顺序、冲突处置）。**不复述规范正文**；正文以 `spec/`、`contracts/`/`.tao/contracts/`、`.tao/adr/` 为准，复制必漂移。

## 当前交接（滚动；每次会话切换时更新，≤12 行）

- **2026-11-14（夜）**：M12 已验证 37 / 进行中 1（`m12-chipyard-016`）/ 待开始 1；M13 **已验证 81** / 进行中 1（`spec-009`）/ 待开始 5；M14 全部收口；M16 已验证 5。
- 今日合入（续）：`030`（`.S` 入门控 `check-inst-asm` 264 id/897 镜像 + 三册 YAML 退役 + trampoline 退役）、`gem5-013`/`qemu-015`（`ld.t rf0` 的两侧修复）、`036`（lit/codegen 用 64 KiB 固件）。
- 今日合入：`qemu-011`（`-bios` 只收 64 KiB）+ `testcases-034`（Tiny oracle 迁 hmon）同批 ⇒ `check-inst` **44/44 + vast full PASS**；`032`（NaN canonical/rootn ±0，`divrem.yaml[23]` 退役）；`spec-008` + `gem5-012` + `testcases-033`（`ext` 的 `hd=rdHD[5:0]`，`ISS-422` 已闭）；`029`（`12-misc` 4 id）；`infra-003`（写者护栏 + `check-writer-guards` 27/27）；`qemu-014`（`sc` 保留粒度=精确地址+宽度）。
- 裁定（2026-11-14）：**semihosting 服务号 = `rd16`**（`immu18[17:8]==0x3FF` 只是固定标记；ARM/RISC-V 同惯例）⇒ `m13-spec-009` 修三处旧句；**picolibc 判据 = engine parity**（qemu 自身有 1 fail/22 excluded/4 blocked，全绿不可达）；**`sc` 保留粒度 = 精确地址+宽度**（已落 qemu/chipyard/向量三件）。
- 裁定（2026-11-14）：**embench `-O0` 开 12h 夜跑窗口**（模型 1.76 k 周期/秒，4h 预算不够；M12 判据保持 38/38）；**picolibc = engine parity + budget 单列**（qemu 自身 1 fail/22 excluded/4 blocked）。
- `m12-chipyard-016` 进度（2026-11-14 20:50）：**embench `-O2` 19/19 全 PASS**；`-O0` 18 例夜跑中（`server208` jobs 18 / 12 h，`xgboost` 排队）、`ics160` 另有 12 个 6 h 预算的 `-O0`；**picolibc** 三池 union（`ics150` 20+18、`ics170` 19+memmem、`server207` 62）预计 21:30 收齐，当前 92 pass / 22 excluded / 55 blocked（多为 40 min 预算超时，重跑中）/ 0 fail。
- **chipyard 写者今晚被 016 占用**：`chipyard-002`（`sc` 粒度 RTL）必须等 016 的 sim 不再启动新批次后才能重编，否则会改 `sim md5` 使在途批次体判 FAIL（`xgboost -O0` 仍在排队）。同理 `spec-010`（等 M12 收尾）、`integ-003`（等 `chipyard-002`）今晚都不具备条件。
- **待办（有共享影响）**：安装根 qemu 仍是 `b34ed7f9…`，落后构建树 `49174499…`（`qemu-014`）⇒ **等 `m12-chipyard-016` 收尾、无并发写者时补跑一次 `install-host`**（禁边构建边测试）；`ISS-437`（musl 未随新 clang 重建）同窗口处理。
- 队列：`chipyard-002`（`sc` RTL 去整字比较，等 016 让出写者）、`testcases-037`（`sc` 粒度正式向量）、`testcases-036`（lit/codegen 用 64 KiB 固件，复核中）、`gem5-013`、`testcases-030`、`integ-002/003/005`（后三件用户标注暂不进行）。
- 未决 issue（P1/P2）：`ISS-433`（chipyard `trap cfx_power` 报 ILLI）、`ISS-435`（余 chipyard RTL + 向量）、`ISS-437`（musl）、`ISS-440`（多 hart 保留清除无实现，上多 hart 前必补，建议立 ADR）、`ISS-441`（`mem_sweep.py` 悬挂引用）、`ISS-426`（QEMU 侧已由 `qemu-012` 修、`030` 实测不再复现，待核 gem5 侧后关闭）。
- 规则新增（2026-11-14）：**构建 32 核 / 测试「全量核 − 2」**（主控机·`server20x`=62、`ics*`=38）；**禁边构建边测试**；发测试前查内存/磁盘；`make check-modules` 会装共享安装根 ⇒ 并行窗口禁跑。

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
| issue / 待裁定口径 | `.tao/knowledge/issues.yaml` / `discussing.md` |
| 历史归档 | `.tao/archive/M*/`（M1–M11） |
| 临时 / 一次性产物 | `/tmp/opencode/<任务ID>/` |

## 设计取向（用户 2026-11-14 裁定）

- **设计选择的首要判据是「该设计是否更优秀、更符合 DADAO 理念」，不是改动代价。** 代价必须列出（供用户权衡），但**不得作为推荐或取舍的理由**；也不得因「改动少 / 三实现已一致」就把既有实现当成规范口径（既有实现与规范冲突时，以规范为准，改实现）。

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
