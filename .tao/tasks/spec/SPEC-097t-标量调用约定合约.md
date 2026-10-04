# SPEC-097t: 标量调用约定合约落地（contract-abi §4 正文 + contracts/abi.yaml 扩展）

**模块**：spec
**项目里程碑**：M3
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）：§寄存器规范、§函数调用规范 §The Stack Frame、§传参（参数寄存器/标量参数/栈溢出规则）、§返回值（标量类型返回值）。
  - `spec/DADAO-11-AEE-应用程序运行环境.md`（0.9.2）。
  - 现有 `.tao/knowledge/contract-abi.md`（M1 最小 ABI，§4 为 `Deferred to M2` 表格）；`contracts/abi.yaml`。
- **输出**：
  - `.tao/knowledge/contract-abi.md`：把 §4「`Deferred to M2`（完整调用约定…）」替换为**已提取的标量调用约定正文**（每条带 `[DADAO-21 §章节]` 来源标注），并更新版本行/说明。
  - `contracts/abi.yaml`：新增机器可读字段（参数寄存器、返回寄存器、callee-saved、帧布局、栈对齐、`[OPEN]` 状态）。
- **约束**：
  - **Spec-first**：期望值只能来自 `spec/`，**不得**从 `contracts/abi/spec.md`（0628，0.4.1 口径）或任何实现反推；M68k/0628 仅可**只读对照**（内容溯源，非执行依赖）。
  - **范围**：**非变参标量**调用约定——参数寄存器分配（`rd16–rd31` 数据 / `rb16–rb31` 地址，独立计数从 16）、标量参数提升（<8B 符号/零扩展到 8B）、寄存器溢出栈区规则、返回值（标量→`rd31`、指针→`rb31`）、callee-saved（`rd32–rd63`/`rb32–rb63`）、栈帧布局（`rbfp`/`rbsp`，栈向下增长）、prologue/epilogue（SP-only 与 FP 两套）、内联 `Fence`。**不含**：变参、HFA/HPA、聚合传参/返回、多返回值、sret、RF 浮点、动态链接/TLS（→ M4）。
  - **`[OPEN]` 项（已判）**：现有 `contract-abi.md §6` 的 5 项中与 M3 相关者须落为**已判 M3 口径**并标注依据：**窄返回值扩展规则 → C5/`ADR-0018（C5）`**（callee 扩展 canonical、caller 不截断）；**帧指针省略策略 → C7/`ADR-0018（C7）`**（条件式 `hasFPImpl`，默认 SP-only，`getFrameRegister=hasFP?rb2:rb1`）。多返回值声明顺序仍 **M4**；`rd1`/`rb3`/`rb4` 分类按 C6 落为 reserved。无 spec 依据的项仍标 `[OPEN]`，**不得臆造**。
  - **栈溢出区（C4/`ADR-0018（C4）`）**：正文须写**全局声明序单栈区**（按参数声明序、每槽 8B），并注明窄参数由 **caller 扩展**到 8B；与 `spec/DADAO-21 §栈溢出规则` 同句两读的关系须说明（建议补 spec 澄清句）。
  - **CSR（C6）**：正文写 `CSR = rd32–63 ∪ rb32–63`；**SP(rb1) ∉ CSR**；caller-saved = `rd/rb 8–31`；`rd1–7`/`rb3–7` reserved；`rd0`/`rb0` 特殊。
  - **call/RegMask（C16/`ADR-0018（C16）`）**：正文登记 `call Defs=[rd31,rb31]`、`getCallPreservedMask`（含 rb32–63）、`ret` 不加 Defs 的调用约定事实（实现约束由 `LLVM-039t` 承担）。
  - **RF/RA 边界**：RF 整层 `Excluded`（M4）；RA 由 `call`/`ret` 管理、不属调用者/被调用者保存框架；`rb2`(FP) 保留。
  - **栈对齐 / DataLayout（C9，已判 → `ADR-0018（C9）`）**：spec 只要求 `call` 时 SP 8B 对齐；`DataLayout` 串已由 C9 定为 `E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128`（`LLVM-033t` 落地）。合约登记「`call` 时 SP 8B 对齐」与 DataLayout `S128` 的关系，说明两者不矛盾（不做 8/16 冲突裁定）。
  - 涉及**新的外部契约口径 / 多方案取舍**（帧指针策略、栈对齐、窄返回扩展）时，按 `AGENTS.md` **主动提醒用户是否立 ADR**，不擅自决定。
  - `contract-abi.md` 是归一化投影：与 `spec/` 冲突时阻断实现、走变更流程（`spec/Process-02-合约编写规范.md`）。

## 验收标准

1. `contract-abi.md` §4 已由 `Deferred to M2` 表格变为正文；每条规范句带 `[DADAO-21 §…]` 或 `[DADAO-11 §…]` 来源；无 `[OPEN]` 臆造值。
2. 参数寄存器/返回值/callee-saved/帧布局/栈对齐与 `spec/DADAO-21-ABI` 逐条**可对回**（给出抽查对照）。
3. `contracts/abi.yaml` 解析通过（`python3 -c "import yaml; yaml.safe_load(open('contracts/abi.yaml'))"`），新增字段与 `contract-abi.md` 正文一致。
4. `make check` 全绿（改动落在门控覆盖范围）；`make check-spec-refs`（如适用）不新增违规。
5. 逐条列出与 `SPEC-096k`「M68k ↔ 0628 冲突清单」相关的 M3 取舍项**落点**（C1–C17 已判，见 §5 判定与 `ADR-0018`）；仍未判者（如 M4 的 i128/多返回值约定）显式登记，不得代替用户选边。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
