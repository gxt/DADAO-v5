# MEMORY — DADAO-v5 入口页（指针 + 反套用清单 + 权威文档地图）

> **维护规则**：本页只承载三样——① **入口指针**（导航）；② **DADAO 反套用清单**（与主流 ISA 的硬差异，防止 AI 用其他 ISA 经验补全）；③ **权威文档地图**（职责、读取顺序、冲突处置）。**不复述规范正文**；正文以 `spec/`、`contracts/`/`.tao/contracts/`、`.tao/adr/` 为准，复制必漂移。

## 当前交接（滚动；每次会话切换时更新，≤12 行）

- **2026-11-15（凌晨）**：M12 已验证 38 / 进行中 1（`017` 报告生成器入仓）/ 待开始 1（`integ-002`，等 `-O0` 夜跑 08:46 数据 + 一次 `integ-002` 核验）；M13 已验证 **92** / 进行中 2（`037`、`integ-003`）/ 待开始 2（`integ-005`、`spec-010`）；M14 **K1 四件已合**（已验证 18，`005` 收口门控在复核）；M16 已验证 5 / 进行中 1（`gem5-005`）/ 待开始 3。
- **今晚合入**：`chipyard-016`（embench 38 + picolibc engine parity，`SYS_FLEN` 修复）、`chipyard-002`（`sc` 去整字比较；冲突取 016 侧）、`testcases-043`（YAML 全退役）/`044`（三探针退役 +34 点）/`045`（riscv-tests 精选 32 点后退役）/`046`（spec 原语迁 `lib/`、`check_b7` 断言改吃 `.S`）、`linux-003`/`004`（K1 到 `start_kernel` + 自建页表/PTBR）。
- **口径落定（2026-11-14/15）**：`sc` 保留粒度=精确地址+宽度（三实现已改，向量 `sc.b.nn_orrr_rd.S` 点 17–21）；semihosting 服务号=`rd16`；**Vast 放弃 ISA 执行覆盖**；**YAML 全退役**（`.S` 唯一载体，`check-inst-asm` 265 id/901 镜像）；单指令 ≤127；picolibc 判据=engine parity；**生成器/证据随产物入仓**（`m12-chipyard-017`、`m13-testcases-046`）。
- **L1 状态**：`check-musl-freshness`、`check-run-artifacts`、`check-temp-dirs` 今晚由红转绿；仅 `check-patch-tree` 红（在途组件任务）。
- **安装根已刷新**：`install-host` + `build-musl-shared` 已跑（qemu `725c5da7…` 与构建树一致、`ISS-437` 关闭）⇒ 后续测试不必再用构建树二进制绕。
- 队列：M13 `037`/`integ-003` 复核 → `integ-005` 收口；M12 `017` 复核 → 08:46 后数据补齐 → `integ-002`；M14 `005` 复核 → **K2 待用户授权立册**；M16 `005` → `006` → `007`。
- 未决 issue（P1/P2）：`ISS-433`（chipyard `trap cfx_power`）、`ISS-440`（多 hart 保留清除，建议 ADR）、`ISS-425`（CodeGen RA 寄存器）、`ISS-426`（`ld.o ra0` SBZ 位）；已关：`ISS-437`。
- **待用户裁定**：① semihosting 参数指针 PA/VA；② `contract-linux-boot §1` 页表由谁建；③ `ISS-440` 是否立 ADR；④ K2 立册范围；⑤ 机器/版本命名（约 147 文件）；⑥ 运行平台×机型×用例 6 问；⑦ `spec-010` 已获「等 M12 收尾」裁定（`016` 已合、`integ-002` 未完成 ⇒ 仍挂起）。

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
