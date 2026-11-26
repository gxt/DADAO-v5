# m20-spec-001: cfx 寄存器布局与异常原因总纲修订（先记录，待讨论）

**模块**：spec
**项目里程碑**：M20（用户 2026-11-26 确认挂在 M20）
**依赖**：M16、M17 收口；用户逐条讨论并定稿后，才可派发
**可并行分片**：否（总纲；后续按模块拆任务）
**预估**：2–3 h（仅本总纲/影响清单；实现链另计，待讨论后估算）
**档位**：规划（不验收实现）
**状态**：待开始

## 背景（用户 2026-11-26 指示）

用户要求先记录一个 **spec 修订任务**，待 M16/M17 都收口后由用户安排派发；**有影响的模块都需要单独安排任务**。本任务只做总纲记录与影响盘点，**不派发、不实现、不改 spec**；下文 10 条均为用户原文要求，具体字段/编码/迁移顺序待讨论。

## 用户要求（原文记录，暂不解释/裁决）

1. 删除 cg6/cg7 现有内容；cg7 改为 **核芯功能扩展配置寄存器**（即原有的 cg4）；原有 cg6 中的 scratch regs 改为新的 cg7 的 rc63/rc62/…；每个 cfx **至少 2 个**（rc63/rc62 都有），余下由 cfx scratch regs num 规定。
2. 新 cg4 改为 **同步异常现场寄存器**；原有 cg5 的 rc0–rc5 移到新 cg4 的 rc0–rc5。
3. 新 cg5 改为 **退出异常现场寄存器**；原有 cg5 的 rc8–rc11 移到新 cg5 的 rc0–rc3。
4. `IGPTRAP`/`ISPTRAP`/`IGPFTRAP`/`ISPFTRAP`/`DGPTRAP`/`DSPTRAP`/`DGPFTRAP`/`DSPFTRAP` 改名为
   `MISSIGP`/`MISSISP`/`MISSIGPF`/`MISSISPF`/`MISSDGP`/`MISSDSP`/`MISSDGPF`/`MISSDSPF`。
5. `ADWBFAIL` 改为 `PTWFAIL`，改为 `1<<15`；语义 = 页表访问失败，包含原有 AD 位写回失败。
   **注意：不增加 PTWFAIL 的测试用例。**
6. 删除 `cfx_llc`。
7. `cfx_time` 的 cfx code 改为 **62**；`cfx_uart` 的 cfx code 改为 **61**。
8. `cfx_uart` 只保留 **2 个 uart**；`cg16` 参考 `cfx_pmem` 的 `cg16` 修订，每个寄存器 **2 位**。
9. 删除 `cfx_hart` 的 IPI 与 `cfx_uart` 的 UART0–UART31 中断；删除 `cfx_power` 的异常原因表的**后三项**。
10. 每个 cfx 的异常原因表**都应该有 `CFXPERM`**。

## 已决口径（2026-11-26，用户）

- **旧 cg7 的内部空间描述寄存器先整体移到新的 cg6**：新 cg6 = 旧 cg7（每 4 个 rc 描述一个空间、`rc0–rc63`、只读等语义照旧）；不在本批删除内部空间描述机制。
- 配合第 1 条：新 cg7 = 旧 cg4（配置寄存器）+ 旧 cg6 的 scratch（落在 rc63/rc62/…）；新 cg4/新 cg5 按第 2/3 条重排。
- 因而“删除 cg6/cg7 现有内容”应理解为：旧 cg6 的 scratch 迁到新 cg7 高 rc；旧 cg7 的内容迁到新 cg6；不是丢弃内部空间描述。
- **新 cg7 的 scratch 分配（2026-11-26 用户确认）**：`scratch_regs_num = N` 表示 scratch **总数**，范围 **2..16**；N=2 ⇒ `rc63/rc62`，N=3 ⇒ `rc63/rc62/rc61`，从 rc63 向下连续；N=16 ⇒ `rc63..rc48`，rc47 及以下不再作为 scratch；语义沿用旧 cg6（RW、初值未定义、`rc >= N`/不存在访问 ⇒ `CFXREG`）；旧 cg4 的 `rc0–rc6`（含 `scratch_regs_num` 本身）保留在新 cg7 低位，不参与 scratch 编号。
- **新 cg4/cg5 的 reserved 范围（2026-11-26 用户确认）**：新 cg4 只保留 `rc0–rc5`（旧 cg5 入口记录），`rc6+` 全部 reserved；新 cg5 只保留 `rc0–rc3`（旧 cg5 出口意图），`rc4+` 全部 reserved；旧 cg5 `rc6`/`rc7` 随重排作废、不保留语义。所有 reserved 访问 ⇒ `CFXREG`。
- **PTW 故障结构（2026-11-26 用户选择）**：所有 PTW 相关 fault 的细节放 `cfx_ptw cg8 rc4`，采用 **one-hot**（`[15:0]`，`[63:16]` 保留）；同步异常表只保留一个 `PTWFAULT`（`1<<15`）；高位 PTW 位图（`[32:38]`/`[48:55]`/`[56]`）随本方案删除。
- **PTW 细节读取方案（2026-11-26 用户确认）**：采用现有 `hypv_cg_reg_deleg`——`cfx_ptw cg3 rc12` 的 bit8 清 0，允许 supv 访问 `cfx_ptw cg8`；`cfx_ptw cg2 rc2`（`supv_cfxreg`）**只放行 cfx2（smon）**，不放行 cfx0/cfx1；`cfx_hmon` 为 hypv，可直接读；`trap cfx_ptw` 仅作 fallback/调试，不作主路径。
- **cfx 编号迁移（2026-11-26 用户确认）**：删除 `cfx_llc`；原 **33/34 归 reserved**（`cfx_time` 旧 34 不保留兼容入口）；`cfx_time` 新 code = **62**，`cfx_uart` 新 code = **61**，`cfx_power` 保持 63；**不保留旧编号别名**，所有 spec/契约/别名/LLVM/引擎/内核/测试按新编号重写。
- **cfx_uart 实例（2026-11-26 用户确认）**：只保留 **2 个 UART**，按 cg/bit 编号称为 **UART32/UART33**，寄存器组用 **cg32/cg33**；中断位用 **bit32/bit33**。`cfx_uart cg16` 的 `rc16 mask`/`rc17 pending`/`rc18 ack` 是 64 位位图，只使用 **bit32/bit33**（不是 bit0/bit1 的 2 位字段），其余位保留；`(pending & ~mask)` 只判这两位。旧 UART0/UART1 的命名不再保留（位置/编号按 32/33 重写）。
- **UART 中断投递（2026-11-26 用户确认）**：按 cfx code 编号，作为**异步源**触发 `cfx_hart` 中断——源身份 = **cfxha 61**（`cfx_uart`），`cg16` 的 bit32/33 为 UART32/UART33 子事件；`mask`/`pending`/`ack` 语义同 `cfx_pmem cg16`；`cfx_uart` 自己的异常原因表不再列 UART0–31 中断；Linux 通过 `cfx_uart cg16` 读 pending/ack。
- **中断删除（2026-11-26 用户确认）**：删除 `cfx_hart` 的 `1<<8 IPI`；删除 `cfx_power` 异常原因表后三项 `1<<8 POWEROFF`/`1<<9 HARD_RESET`/`1<<10 SOFT_RESET`；`cfx_uart` 只保留 UART32/33 的 cg16 异步子事件，删除 UART0–31 中断行。
- **每 cfx 的异常原因表（2026-11-26 用户确认）**：所有**非 reserved** cfx 都统一包含五种同步原因：`1<<0 CFXTRAP`、`1<<1 CFXMEM`、`1<<2 CFXREG`、`1<<3 CFXESC`、`1<<7 CFXPERM`；`cfx_ptw` 也包含（不再只有 CFXTRAP/CFXESC）。reserved cfx 不实现寄存器面，不列原因表。
- **版本与 ADR（2026-11-26 用户确认）**：本批以 **0.8.1 定版**（`DADAO-12` 等从 `0.8.1-rc` 收为 `0.8.1`，相关 contracts/版本锁同步）；**不立 ADR**。
- **`cfx_ptw cg8 rc4` 位映射（2026-11-26 用户确认）**：`bit0..7` = MISSIGP/MISSISP/MISSIGPF/MISSISPF/MISSDGP/MISSDSP/MISSDGPF/MISSDSPF；`bit8..14` = NUPERM/NJPERM/NSPERM/NHPERM/NRPERM/NWPERM/NXPERM；`bit15` = **PTWFAIL**（原 ADWBFAIL 的 PTE 物理访问/回写失败）。读到 0 或多位的处理由**软件**定义。
- **并入 `m18-spec-001` 的既有口径**（原任务待开始，未实施）：每个**非 reserved** cfx 的 `scratch_regs_num` 缺省值 = **2**（范围 2..64）；reserved cfx 不实现该寄存器（访问仍 `CFXREG`）；原 QEMU/gem5/chipyard 的默认 4 改为 2，相关 `tests/arch`/`tests/inst/11-cfx` 期望与探针随本批统一调整。该任务不再单独派发，内容全部并入本总纲。

## 影响面（初步，待定稿后逐项拆任务）

- `spec/`：`DADAO-12`（cg/rc 表、异常原因表、PTW 故障、cfx 路由）、`DADAO-13`、`Kaiwu`（机型/地址/中断）、`SimRISC-*`（若涉及编码/cfx 访问）。
- `.tao/contracts/` 与 `contracts/`：`contract-see`、`contract-isa`、`contract-abi`、`opcodes.yaml`、`cfx-aliases`、`legality_rules`、`machine`/执行环境/测试矩阵。
- `idl/`：cfx 相关 operation、cause 名称、IDL 向量/锁。
- `qemu/`：cfx 寄存器与别名、异常原因、PTW/PTWFAIL、time/uart/hart/power 寄存器面、中断路由。
- `gem5/`：`node_cfx`/`tiny_cfx`/`fs_machine`/PTW/TLB、cause 名称、cfx 路由、time/uart 面。
- `chipyard`（RTL）：cfx 寄存器组、cause 位图、PTW、time/uart/hart/power、中断。
- `llvm/`：cfx 别名/编号、汇编/反汇编立即数、lit 与测试向量。
- `linux/`：`arch/dadao` 的 cfx 访问、异常原因解码、PTW 故障、time/uart/hart 驱动、SEE/SBI 映射。
- `testcases/`：`tests/inst/11-cfx`、`tests/arch`、`tests/unit/gem5`、签名数据、case-ledger、异常原因向量。
- `infra/`：cfx 别名/opcodes/ledger 生成器与门控、迁移脚本；可能需 ADR。
- `docs/DDLN/`：若讲义引用旧 cg/rc/名称，需同步；ADR 判定（跨模块 + 契约变更，原则上必须立 ADR）。

## 待讨论问题（先记录，不自行裁决）

1. **新 cg6（旧 cg7）**：搬移是否保持“每 4 rc 一个空间、16 块、只读”全部语义？新 cg6 是否还有 reserved/扩展空间。
2. **PTWFAIL / PTWFAULT**：所有 PTW 相关 fault 的细节放 `cfx_ptw cg8 rc4`，one-hot `[15:0]`；同步异常表只留 `PTWFAULT`（`1<<15`）；高位 PTW 位图删除。监视器读取选现有 delegation（`cfx_ptw cg3 rc12` bit8=0；`cg2 rc2` 仅放行 cfx2，不放行 cfx0/cfx1；hmon 为 hypv 直接读）；`trap cfx_ptw` 仅 fallback。仍待定：HBI 初始化清单、`PTWFAIL`/`ADWBFAIL` 名称关系、零/多位非法判据、写入/清除/嵌套/多 hart 语义、高位位图删除后的 handler/测试迁移、`cause_info` 口径、无专用测试时如何证明一致。
3. **测试策略**：除“PTWFAIL 不增加用例”外，其余名称/编号/cg 迁移是否补最小回归；哪些测试只需生成器刷新、哪些需新向量。

## 约束

- 本任务只记录总纲与影响清单，**不改** `spec/`、`contracts/`、任何实现或测试；不建 worktree、不派单。
- M16/M17 收口后由用户安排；每个受影响模块单独建任务，不得把实现塞进本总纲任务。
- 术语：`bank` = **寄存器组**；cfx 编号/名称以定稿 spec 为准，不从实现反推。

## 完成区

**测试结果**：未执行（规划记录）
**修改文件**：本任务书
**验收结果**：待用户讨论
**新发现/坑**：
**遗留问题**：cg4/cg5/cg6/cg7 映射已定（旧 cg7→新 cg6、scratch 2..16/rc63 向下、缺省 2、cg4 rc0–5 / cg5 rc0–3 之外的 reserved）；PTW 采用 `PTWFAULT 1<<15` + `cfx_ptw cg8 rc4` one-hot，16 位映射、软件处理 0/多位、delegation（仅放行 cfx2）已定；cfx 编号（删 llc、33/34 reserved、time=62/uart=61、无旧别名）已定；UART32/UART33 用 cg32/cg33、bit32/bit33、cg16 用 bit32/33、异步源 cfxha61 已定；中断删除（IPI/power 后三项/UART0–31）与每 cfx 五种原因（含 CFXPERM）已定；版本 0.8.1 定版、不立 ADR 已定；测试策略与 cg6 细节仍待讨论；影响模块任务未拆。
