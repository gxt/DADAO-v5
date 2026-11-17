# MEMORY — DADAO-v5 入口页（指针 + 反套用清单 + 权威文档地图）

> **维护规则**：本页只承载三样——① **入口指针**（导航）；② **DADAO 反套用清单**（与主流 ISA 的硬差异，防止 AI 用其他 ISA 经验补全）；③ **权威文档地图**（职责、读取顺序、冲突处置）。**不复述规范正文**；正文以 `spec/`、`contracts/`/`.tao/contracts/`、`.tao/adr/` 为准，复制必漂移。

## 当前交接（滚动；每次会话切换时更新，≤12 行）

- **2026-11-18 00:20（夜间续跑）**：`m14-linux-016` 已收尾（合入 `6ddb3bbd`，F5 打通、101/101）；`m14-linux-017` 已派单（夜跑，7–9 h：`switch_to`+调度+U-mode 帧往返+最小 clockevent+F3/init）。**`m15-testcases-012` 仍待合入**（与 011 16 处链接冲突，明早按「crt0/runtime/dadao-* → ee-user；kaiwu-tiny*.lds → ee-tiny；`-L` 并存」解）。
- **2026-11-17 23:40（夜间交接）**：`m15-testcases-011` 已收尾（tiny 资产 → `tests/ee-tiny/`）；**`m15-testcases-012` 复核 Accepted 但未合入**——与 011 在 16 个链接点冲突（`-L` 需并存 `ee-tiny`+`ee-user`，`crt0/runtime/dadao-*` 走 `ee-user`，`kaiwu-tiny*.lds` 走 `ee-tiny`），明早解冲突后合入并跑 `check-tests-index`+链接冒烟。`m14-linux-016` 复核判 Needs Revision（`--selfcheck` 循环迭代单字符），修复中；提交时必须显式 stage `components/linux/patches/init/main.c.patch`。
- **2026-11-17 14:05（M16 收口 + K3 收尾中）**：`m16-chipyard-001` 已收尾（周期模型全量复测，实测 261+可配 2；B1/B3 裁定={①}，R2/R3 作废）；`m14-linux-012` 已收尾（196/196、9 路注入）；`m14-linux-015` reviewer Accepted，L3 `check-arch` 由主会话在跑，之后处理 3 条非阻断 finding 再收尾。`m15-testcases-009`、`m14-qemu-007` 已收尾。
- **在跑**：`m14-linux-015`（待验收 + L3）。**待开始/待返工**：`m15-spec-001`（待返工，等用户定推进方式）。**待裁定**：chipyard 补 TLB、`cg3 rc0–rc3` 合并、gem5 SE `--semihost` 开关、心跳方案、`tools/` 孤儿清理、`refs/` 清空方式。
- **已完成待合入**：`m15-testcases-006`（伪指令+lds 统一）、`m14-qemu-003/004/005`（已合入）；**待开始**：`m14-linux-012`（等 linux-010 合入）、`m14-linux-015`（等 012）、`m15-testcases-009`（等 007）。
- **磁盘**：`/mnt/tao` 29%（333G）；今夜两次 ENOSPC（`ISS-464`/`ISS-465`）已登记；`check-temp-dirs`/`check-run-artifacts`/`check-knowledge-refs` 已回绿。

- **2026-11-16（m14-infra-004）**：**测试机整机名 = `Kaiwu`（开物，`ADR-0055` 已 Accepted）**——`spec/Kaiwu-测试机运行环境.md`（册改名 + 锁 path/sha256 同笔重算）、QEMU 机器串 `kaiwu-tiny`/`kaiwu-vast`（**无旧名别名**）、全仓 `Kaiwu-Tiny`/`Kaiwu-Vast` 机械替换（`docs/DDLN/**` 改、`.tao/archive/**` 不动）；`DADAO`/`Wuming`/`Gewu` 与三元组 `dadao-unknown-elf` 不变。命名与机器串见下「反套用清单」命名条。
- **2026-11-15（晚）**：**M13 已收口并归档**（107 件全已验证、台账已删）；**M15 `m15-testcases-001` 已收口**（`tests/inst` 10 宏下沉共享层、镜像 904/904 与 md5 22/22 均不变）；M12 已收口且已归档；M14 K1 收口（19）、**K2 待授权立册**；M16 已验证 9 / 待开始 1（`chipyard-001`，等 M13 收口→现已解锁）；M15 `m15-spec-001` 待返工（WIP `0584a64b`，用户要求先摊开文件 + 逐条语句分析）。
- **M13 收口事实**：矩阵冻结 `docs/TestReports/M13-三平台差分-矩阵.md`（整数 637 + FP 227 = **864 镜像三平台逐例一致、差异 0、未归因 0**）；报告记 `input commit`；新增链例字节级断言；`refs/m13-005-acceptance.*` 是 **refs/ 最后一批产物**。
- **rf2rf 批（全部合入）**：`spec-010`（264→263 id）+ llvm/qemu/gem5/chipyard 四实现 + 向量 `02-reg-copy/rf2rf_orri_rf.S`；伪指令体系迁入 `SimRISC-00 §5`（现行位置 `Toolchain-01 §6.2`）、`SimRISC-03` 按 rd/rb/rf 拆三章；7 个伪指令载体（`pseudo_set.*`，113 点）；RMW 合成序 `atomic_rmw.S`；`atomics` 5 探针退役改执行型 `atomics_e2e`；`set.fo` 最小指令数展开。
- **sim md5 / qemu md5**：chipyard **`71574df4dbd0033b6c0a7b133239b95a`**（`m14-infra-004`：改名 `Kaiwu`；旧 `bd5e75b3…` 作废）；qemu **`50752f5feeda4e15fe35de6a6a260a4e`**（`m14-infra-004`：机器串 `kaiwu-tiny`/`kaiwu-vast`；旧 `9750c139…` 作废）；**两者都只在同一构建环境/时段内可比**（`ISS-451`/`ISS-453`）。
- **L1 全绿**（`check-inst-asm` 904/904、`check-lit` 177/177、`check-interface` 89/89、`check-musl-freshness` PASS）。
- **规则新增（2026-11-15）**：派单顺序（先提交任务书再建 worktree，R2 机械校验）、台账时间戳取 `date`/`git log`、复核分档（小改 1 路注入 ≤15 min）、脚本入仓判据=会不会再跑。
- 队列：M13 收口完成 → **`refs/` 清空**（用户已定，方式待选）+ **M13 归档**；M16 `chipyard-001` 已解锁；M14 K2 待授权。
- **待用户裁定**：① `refs/` 清空方式（直接删 / 归档到 `archive/<M>/refs/`）；② 平台×机型×用例 6 问；③ gem5 SE `--semihost` 开关；④ `ISS-440`/`ISS-443`/`ISS-433` 是否合批做 ADR；⑤ K2 立册范围；⑥ `m15-spec-001` 的推进方式（先摊开文件 + 逐条语句分析）。

## 入口指针

| 主题 | 真源 |
| --- | --- |
| 项目总览 / 里程碑 / 版本号 | 根 `README.md` |
| 当前进度 / 任务台账（待开始·进行中·已验证） / 裁定 | `.tao/knowledge/milestones-m14.md`（M14）等活册；M13 及以前已归档（`.tao/archive/M13/`…`M11/`） |
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
- **测试机不是通用平台**：BootROM/RAM/复位/地址映射按 `spec/Kaiwu` + `ADR-0004`。
- **三层命名不互换**（`ADR-0055`）：项目/ISA = `DADAO`（三元组 `dadao-unknown-elf`）、核 = `Wuming`（generator `dadao-wuming`）、cfx 寄存器堆 = `Gewu`（generator `dadao-gewu`）、**整机 = `Kaiwu`**（机型 `tiny`/`vast`；QEMU 机器串 `kaiwu-tiny`/`kaiwu-vast`，**无旧名别名**）。改名只换名字，编码/几何/契约值不变。
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

- 任务台账：`.tao/knowledge/milestones-m14.md`（M14）等活册（三分表：待开始 / 进行中 / 已验证；按任务书 `**项目里程碑**` 分派）；**M12/M13 台账已于 2026-11-15 合并进 `.tao/archive/M12/`、`M13/` 并删除**，M11 及以前同。
- M10 完成任务书与 issue 快照：`.tao/archive/M10/`。
- 已归档 issue：`.tao/archive/M*/issues-closed.md`；活 `issues.yaml` 只留未关闭项。
- 一次性过程与长日志：运行期日志目录（可删、未归档）；临时产物：`/tmp/opencode/<任务ID>/`。
