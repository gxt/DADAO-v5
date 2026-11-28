# MEMORY — DADAO-v5 入口页（指针 + 反套用清单 + 权威文档地图）

> **维护规则**：本页只承载三样——① **入口指针**（导航）；② **DADAO 反套用清单**（与主流 ISA 的硬差异，防止 AI 用其他 ISA 经验补全）；③ **权威文档地图**（职责、读取顺序、冲突处置）。**不复述规范正文**；正文以 `spec/`、`contracts/`/`.tao/contracts/`、`.tao/adr/` 为准，复制必漂移。
>
> **`discussing.md` 只记未裁决项（用户 2026-11-19）**：已裁决的内容该迁到其它文档或 `docs/DDLN/` 的立即转移，没有保留价值的直接删除；裁决落定后不得留在 `discussing.md` 里堆积。

## 当前交接（滚动；每次会话切换时更新，≤12 行）

- **2026-11-27 基线**：
  - **已归档**：M14（76 册）、M15（66 册）、**M16（95 册，2026-11-27）**、**M17（46 册，2026-11-27）**、**M18（73 册，2026-11-28；Linux 测试集 + K6）** → `.tao/archive/M14/`、`M15/`、`M16/`、`M17/`、`M18/`；M19（2 件，需硬件在场）、M20 未开工。
  - **三方差分收口归 M20**（用户 2026-11-27）：现场红项（`arch-power-001/002`、`arch-umon-012/013` 回归挂死；`arch-cache-003/004` 既有红）与 `run_arch` 的 4 处工具链缺口（chipyard 腿缺 `LD_LIBRARY_PATH`、不识别 `expected-divergences`、单 case 缺承载中止整腿、power RTL 参数不通）见 `discussing.md` N40。
  - **环境（2026-11-27 重放对齐）**：qemu `e470dc56…`（源树 `a8d0796`）、gem5.opt `ebb19d0b…`（`7db7553`）、chipyard Vast `0ead2519…` / Tiny `71cbed98…`（`7b1d785`）、LLVM 11-26 07:23。组件补丁合入后必须「删源树→`make fetch`→`apply_series`→重建→`install-host`」，否则 L2/L3 的绿红都不算证据。
  - **已知基线红**：`check-patch-tree` **52 problem**（linux 51 / musl 1，`ISS-left-004`）；L3 `unit:full`/`tset:m6` 的 `stack-protector*.ll` 未归类（`ISS-left-005`）；picolibc harness `.done` 无库指纹（`ISS-504`）；`check-manifests-guard` 已 rc=0（M16 遗留登记随归档清理）。
  - **队列**：M20 先 `m20-integ-001`（三方 cfx/cg/rc 覆盖矩阵）/`m20-integ-002`（实测与缺口关闭），再接 `spec-002`/`idl-001`/`llvm-004`/`infra-002`/`qemu-001`/`gem5-005`/`chipyard-002`/`linux-001`/`testcases-006`；M17/M18 已收口归档（0 open）。
  - **open issue**：68（left 51 / m19 7 / m20 10）。

## 入口指针

| 主题 | 真源 |
| --- | --- |
| 项目总览 / 里程碑 / 版本号 | 根 `README.md` |
| 当前进度 / 任务台账（待开始·进行中·已验证） / 裁定 | `.tao/knowledge/milestones-m19.md`–`milestones-m20.md`（活册）；M18 及以前已归档（`.tao/archive/M18/`…`M11/`） |
| M18 归档 / 回顾 / 关闭 issue（Linux 测试集 + K6） | `.tao/archive/M18/`（`README.md` / `m18-retrospective.md` / `issues-closed.md`） |
| M17 归档 / 回顾 / 关闭 issue（IDL 可执行参考模型 + 四方差分，golden = IDL） | `.tao/archive/M17/`（`README.md` / `m17-retrospective.md` / `issues-closed.md`） |
| M16 归档 / 回顾 / 关闭 issue（gem5 Timing + chipyard wuming + `tests/arch` 三方载体） | `.tao/archive/M16/`（`README.md` / `m16-retrospective.md` / `issues-closed.md`） |
| M15 归档 / 回顾 / 关闭 issue（ISA 语义结构化：IDL v0 + 12 册 operation + 渲染/门控） | `.tao/archive/M15/`（`README.md` / `m15-retrospective.md` / `issues-closed.md`） |
| M14 归档 / 回顾 / 关闭 issue（Linux bring-up K0–K5） | `.tao/archive/M14/`（`README.md` / `m14-retrospective.md` / `issues-closed.md`） |
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
| 已关闭 issue 的教训 | `.tao/knowledge/lessons.md` |
| issue / 待裁定口径 | `.tao/knowledge/issues-{left,m19…m20}.yaml`（按里程碑分册，各自会话独占写）/ `discussing.md` |
| M14 内核与主流 ISA 差异盘点（八份 / 195 条 / 七根因） | `components/linux/kernel-diff-vs-mainstream-isa.md`（索引）→ 各任务书「盘点结论」段 |
| 历史归档 | `.tao/archive/M*/`（M1–M18） |
| 临时 / 一次性产物 | `/tmp/opencode/<任务ID>/` |

### 机型 × 平台承载方式（tiny / vast / user）

真源：`contracts/machine.yaml`（几何与能力）；本表只记「各平台用哪个入口选机型」。

| 平台 / 入口 | tiny | vast | user |
| --- | --- | --- | --- |
| QEMU system `qemu-system-dadao` | `-M kaiwu-tiny` | `-M kaiwu-vast` | 不支持（system 无此机型） |
| QEMU user `qemu-dadao` | — | — | 二进制本身即 user 机型，无 `-machine` |
| gem5 FS `configs/dadao/fs.py` | `--profile tiny` | `--profile vast` | — |
| gem5 SE `configs/dadao/se.py` | — | — | `--profile user`（默认） |
| chipyard RTL | `WumingTinyConfig` | `WumingVastConfig`（`m16-chipyard-006`） | —（RTL 不跑 SE） |

- **QEMU**：**编译期注册 QOM 机器类型**，每个类型固定一份 `DadaoMachineDesc`（走 `class_data`）。`kaiwu-tiny`/`kaiwu-vast` 不接受运行期 `profile=`；`-M dadao-m1` 报 machine not found（别名 M12 后已删，`-M help` 只有两台）。
- **gem5**：`PROFILES` 字典给地址与容量，两个分支给内存对象与 **MMU/TLB 类**（tiny → `DadaoFsMMU`/`DadaoFs*CPU`，vast → `DadaoNodeMMU`/`DadaoNode*CPU`）；CPU 类型由 `--cpu-type {atomic,timing}` 正交选择（`se.py`/`fs.py` 的 `choices` 实为这两个；`minor`/`o3` 待 wuqing/wuxing RTL 到位后再扩，2026-11-20 按 `m16-gem5-019` 盘点订正）。
- **chipyard**：Scala config 类（`DadaoConfigs.scala`），**编译期**生成 RTL；`user` 机型无 RTL 形态。


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
- **cfx 不是 CSR**：用 `trap`/`escape`/`cfx2rd`/`cfx2rc`；`escape` 的 `imms18` bit1 选帧（0=cg5、1=cg9），cg5 偏移 0/+4、cg9 只允许 0（汇编 `imms20 ∈ {0,4,8}`，其它 ILLI）；`excp_cause_ip` 可写不等于安全边界。
- **两轴权限 + 保留 cfxha**：不要套 RISC-V 中断/CSR 模型；cfx 异常/中断按 `spec/DADAO-12` 的流程。
- **指令「条数/功能」的判据是 id，不是助记符**（用户 2026-11-19）：id = **助记符 + 格式 + 寄存器组**（如 `ld.o` 有 `_ra`/`_rb`/`_rd`/`_rf` 四个 id，分属四节）。数指令、判覆盖、分任务、写 operation 一律以 `contracts/opcodes.yaml` 的 `id` 为准；**同一助记符在不同节/不同寄存器组出现时不得重复计数或跨节合并**（实例：按助记符统计曾把 01 册 38 条算成 90 条）。
- **窄读不改高位**（用户 2026-11-19，`m15-idl-012` R2）：`lr.b`/`lr.w`/`lr.t` 只写 `rd` 的低 8/16/32 位，**高位保持原值**——既不是 `ld.ub/uw/ut` 的零扩展，也不是 RISC-V `lr.w` 的符号扩展（`X[xd] = sext(load_value[31:0], 32)`）。见 `discussing.md` N24。
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
- **M14 已定口径（曾记于 `discussing.md`，已按「只记未决项」规则移出）**：TLB 失效=同步语义见 `m14-spec-006`；内存异常判定顺序（先看 `VA[47:42]`）与「规范不引入缺页/COW」见 `DADAO-12 §2.2.6`；semihosting 指针=PA 见 `contract-semihosting §2`；中断 mask 查当前运行模式 monitor 行见 `DADAO-12 §5.2（三）`；`cause_info` 编码见 `ADR-0056`；异常帧内禁 semihosting 见 `DADAO-12 §5.2/§5.3` + `m14-linux-017`。

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

- 任务台账：`.tao/knowledge/milestones-m19.md`–`milestones-m20.md`（活册；三分表：待开始 / 进行中 / 已验证；按任务书 `**项目里程碑**` 分派）；**M12–M18 台账已合并进 `.tao/archive/M12/`、`M13/`、`M14/`、`M15/`（2026-11-22，`m15-integ-001`）、`M16/`（2026-11-27，`m16-integ-001`）、`M17/`（2026-11-27，`m17-integ-001`）、`M18/`（2026-11-28，`m18-integ-002`）并删除**，M11 及以前同。
- M10 完成任务书与 issue 快照：`.tao/archive/M10/`。
- 已归档 issue：`.tao/archive/M*/issues-closed.md`（按 `closed_in` 取集）；**收尾后活台账不再保留已归档的 `closed` 项**（用户 2026-11-25）：`--check` 在删除前一次性核对、`--verify` 在删除后自检快照；`issues-left` 只放未解决项。
- 一次性过程与长日志：运行期日志目录（可删、未归档）；临时产物：`/tmp/opencode/<任务ID>/`。
