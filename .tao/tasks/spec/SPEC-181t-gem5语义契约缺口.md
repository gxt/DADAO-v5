# SPEC-181t: gem5 语义契约缺口收口

**模块**：spec
**项目里程碑**：M11
**依赖**：`GEM5-002t`（语义矩阵，已验证）
**状态**：待开始

## 用户授权

用户 2026-11-01 接受 G1 语义矩阵，允许修 SPEC/契约任务；本任务只修规范/契约/ADR 状态，不写 gem5 实现。

## 已确认口径（2026-11-01 用户裁决）

- **F2**：`ADR-0044` 置 `Accepted`（decision 已确认）。
- **F5.1**：`ftrem/forem` 按 IEEE 754 remainder；`y=0`/`x=Inf`/sNaN ⇒ NV+qNaN；`y=Inf` ⇒ x；不置 NX/OF/UF。
- **F5.2 C1**：`ftsclb`/`fosclb` 第三操作数 `rfHD → rdHD`；同 `orrr` 编码，不新增 opcode/格式；`rdHD` 为 64 位有符号整数指数；`rd0` 作指数 = 0；旧 `rf,rf,rf` 写法失效。
- **F5.3**：`convert_f2i` 按 IEEE 754-2019；有限 inexact ⇒ NX；NaN/Inf/超范围 ⇒ 饱和 + NV。
- **F7**：`call` 返回地址 = 当前指令地址 + 4（相对/绝对两种形式一致）。
- **F8.1**：M11 保留粒度 = 精确地址 + 访问宽度。
- **F8.2**：`sc` 的 `rdHB = rd0` ⇒ ILLI（新增 `dst_rd0` 规则）。

## 目标

按 `GEM5-002t` 的矩阵与报告，处理已识别的规范缺口，形成可实现的明确口径：

1. **F1 `lr` 合法性**：当前矩阵 12 行 `legality` 为空，但 `SimRISC-12 §1.1` 要求 `hb == rd0`，否则 ILLI；确认并同步 `contracts`/`spec`，补测试项。
2. **F2 ADR-0044 状态**：`ADR-0044` 仍 `Proposed`，而 spec/contracts 已按 `fence ciii` 冻结；核对 decision 是否全部成立，按用户逐条确认后再改状态（不得自行 `Accepted`）。
3. **F5 FP 未明点**：`ftrem`/`ftsclb` 边界、`convert_f2i` NX 等；逐条定口径或明确保留为未实现/异常。
4. **F7 `call` 返回地址**：确认并写明 `IP+4` 语义（当前 spec 未逐字写）。
5. **F8 `lr/sc`**：保留标记粒度、`sc` 目的 `rd0` 合法性；明确平台/ISA 边界。
6. 输出逐条「结论 → 修改文件/章节 → 矩阵行 → 测试影响」，供 B1–B7 引用。

## 文件范围

- `spec/` 对应册（只改经确认的语义文字）
- `contracts/` 机器数据（`opcodes.yaml`/`legality_rules.yaml` 等）
- `.tao/adr/adr-0044-*`（仅状态/decision 经用户确认后）
- 本任务书、`.tao/knowledge/milestones.md`

**不改**：gem5 代码、tests、components、Makefile。

## 验收

1. F1/F2/F5/F7/F8 逐条有结论；每条注明用户授权/ADR decision 状态。
2. `contracts` 与 `spec` 同步；`check-legality-invariants`、`check-spec-*`、`check-contracts-*` 按现场实际跑并留真实 rc。
3. 矩阵行可回溯到修改后的 spec/contracts 依据；无“同助记符默认复用”。
4. 不自行把 ADR-0044 置 Accepted；如 decision 未确认，保持 Proposed 并登记遗留。
5. 完成区 ≤30 行，状态 `待验收`。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
