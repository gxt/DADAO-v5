# ADR-0036: 代码模型与代码跨度（default / large）

**状态**：Accepted（2026-10-25，`D1`–`D8` 经用户逐条确认）
**日期**：2026-10-25
**关联**：ADR-0018（DataLayout / ABI）、ADR-0019（重定位类型）、ADR-0026（动态链接）、ADR-0029（`rela.si` 配对）、`spec/DADAO-12`（地址空间）、`.tao/contracts/contract-elf.md`、`.tao/contracts/contract-dynlink.md`、任务 `LLVM-130t` / `LLVM-131t` / `INFRA-106t`

## Context（背景）

后续目标 = **Linux 内核 + qemu-system + busybox + 完整 LFS（含大量动态库）**。这些场景下**单镜像代码量**会远超当前测试程序，需要先钉住「代码模型」：**代码能放多远、超了怎么办**。

### 事实基线（实测，2026-10-25）

1. **直接 `call` / `jump` = REL26**（`imms24` 字偏移）⇒ **±32 MiB**。实测把两个函数放 64 MiB 开外，LLD 报
   `relocation R_DADAO_REL26 out of range: 16515066 is not in [-8388608, 8388607]`（**硬错误、不静默截断**）；放 16 MiB 开外可正常链接。
2. **条件分支**：`br.eq` / `br.ne` = REL14（±8 KiB）、`br.n/nn/z/nz/p/np` = REL20（±512 KiB）；`BranchRelaxation` 已接入（反向短分支 + 长 `jump`）。
3. **数据**：静态 = ABS48 三步（`set.zw` + `or.w` + `or.w`）⇒ 48 位任意地址；PIC = `aip.si` + `ld.o`（PCREL_HI/LO）⇒ **±512 MiB、4 KiB 粒度**。
4. **动态链接**：PLT 条目 12 B，实测紧贴 `.text`（`.text@0x20240`、`.plt@0x20260`）⇒ 跨 DSO 调用的 `call`→PLT 天然在 ±32 MiB 内。
5. **现状**：`DADAOTargetMachine.cpp` 默认 `CodeModel::Small`，但 DADAO 后端**零处** `getCodeModel()`（模型未被读取）；驱动拒绝 `-mcmodel=large/medium`（`unsupported argument`）。
6. **LLVM 语义对照**：`medium` = 代码近、数据远；`kernel` = 代码 / 数据分区。DADAO 的**数据本来就绝对寻址**（第 3 条）⇒ 这两个模型与默认行为**语义重合**（加了也是假开关）。

### 问题

- ±32 MiB 对多数包够用，但 LFS 中 `clang` / `libLLVM` / `cc1plus` 这类单镜像会超；
- 需要决定：模型做几种、超范围走哪条路、如何在打包与门控上落地。

## Decision（决策）

**D1 — 只定义两种代码模型**

- `default`（无 `-mcmodel`）：**同一镜像内代码两点 ≤ 32 MiB**（直接 `call` / `jump` 可达）；**数据任意 48 位**（静态 ABS48 / PIC ±512 MiB）。
- `large`：**代码任意**；超范围的直接调用改间接（见 `D5`）。

**D2 — 不提供 `medium` / `kernel` / `tiny`**

- `medium` / `kernel` 与 `default` 语义重合（数据已绝对）；
- `tiny` 不适用（48 位地址、无专用基址寄存器）。

**D3 — 驱动口径**

- 接受 `-mcmodel=default` 与 `-mcmodel=large`；
- `-mcmodel=small` 作为 `default` 的**别名**接受（兼容常见构建脚本），文档注明其语义 = `default`；
- `-mcmodel=medium|kernel|tiny` ⇒ **明确报错**（不静默接受）。

**D4 — LFS / 大包的主策略 = 拆 DSO，不是 `large`**

- **硬约束**：任一 REL26 调用边 ≤ **32 MiB**（由链接器强制；推导见 `Rationale`）。
- **打包预算**：单 DSO 的**可执行区跨度**（`.text` + `.plt` + `.init` + `.fini` + `.text.*`）**< 30 MiB**（= 32 MiB − 2 MiB 余量，余量构成见 `Rationale`）。
- 跨 DSO 调用走 PLT（在调用者 DSO 内，天然可达）；
- 大包用组件库拆分（如 LLVM 组件库），**不得**为可拆分的包启用 `large`。

**D5 — `large` 的形态**

- 超出 ±32 MiB 的 `call` / `jump` ⇒ `ABS48` 物化 48 位目标 + 间接 `call rb, rd, imm12` / `jump [rb, rd, imm]`；
- 动态导入（走 PLT）保持直接调用（PLT 与 `.text` 同 DSO 相邻）；
- 条件分支仍由 `BranchRelaxation` 处理，**不引入链接器 thunk**。

**D6 — `large` 的使用白名单**

- 内核模块（加载期才能定地址，无法直接 `call`）；
- 无法拆分的 >32 MiB 静态单体（如 `cc1plus`）；
- 受 KASAN 等膨胀超 32 MiB 的内核镜像；
- **内核本体保持 `default`**（性能）。

**D7 — 门控与打包指标**

- 新增 `check-code-range`：链接后扫 REL26 / REL14 / REL20，报告每个产物的**最远 REL26 调用边**与**距离余量**（`32 MiB − 实测最远边`），以及**可执行区跨度**（打包判据）；越界即红。
- 打包规范：单 DSO 可执行区跨度 **< 30 MiB**，超标即红。

**D8 — 落地顺序**

1. 本 ADR 定案；
2. `D7` 门控与打包规范（先做，成本低、能提前暴露问题）；
3. `D3` 驱动口径 + `D5` 后端 `large` 实现（**另立任务**，触发条件 = 内核模块或静态单体确实需要）。

## Rationale（理由）

- **两种而非三种**：数据侧「任意远」的能力已由 ABS48 / PCREL 提供，`medium`、`kernel` 无额外语义；`small` 只是省一条指令的微优化，且 **PIC 路径已经免费享有**（2 条指令的 `aip.si` + `ld.o`），静态包收益未实测前不值得增加第二条寻址路径与测试矩阵。
- **大包靠 DSO 拆分而非 `large`**：动态链接基础设施已有，PLT 紧贴 `.text`（实测），拆 DSO 零额外工具链成本；`large` 让调用变 4 条指令，应只用于无法拆的场景。
- **越界必须响亮**：REL26 越界已是硬错误（实测），门控只是把「事后报错」提前为「事前余量可见」。
- **数字的来历**：
  - **32 MiB** = REL26 字段推导：`imms24` 是有符号 **字**偏移（`>>2`）⇒ `[-2^23, 2^23-1]` 字 = `[-33,554,432, +33,554,428]` B，即 ±32 MiB；这是**调用点到目标**的距离上限。
  - **30 MiB 预算** = 32 MiB − 2 MiB 余量；余量覆盖 `.plt`（12 B × 外部调用目标数，10 万目标 ≈ 1.2 MB）、段间页对齐（64 KiB 级）与少量插空。体积只是**保守代理**，最终以门控实测的**最远调用边**为准。

**被否方案（记录）**：

- **五种模型全做**：假开关（`medium`/`kernel` 与默认重合）、测试矩阵翻倍。
- **只做 `default`、超限即报错**：LFS 的单体大包（`cc1plus`）无法落地。
- **链接器 thunk / veneer**：需 LLD 合成代码（复杂度高），且 `large` 已能兜底；若后续实测证明 `large` 的调用开销不可接受，再另立 ADR。
- **固定基址寄存器（GP）式 `small`**：放弃 PIC 的零额外寄存器优势，且需占用一个 `rb`。
- **以 `.text` 体积作判据（如「< 24 MiB」）**：体积不是正确性约束（40 MiB 的 `.text` 若调用都在局部仍可链接）；已改为「可执行区跨度预算 + 门控实测最远边」。

## Consequences（影响）

- **正面**：模型矩阵小（2 × {static, PIC}），门控可机械判；LFS 打包有明确指标；`-mcmodel=medium` 等不再造成「以为支持、实则无效」的误解。
- **负面**：`large` 下调用 4 条指令（以局部函数为主）；大包需拆 DSO（打包工作量）；已有构建脚本若传 `-mcmodel=medium` 需改写。
- **后续约束**：单 DSO 可执行区跨度超标必须拆；`check-code-range` 纳入 L2 门控（待定层）。

## 状态说明

- `D1`–`D8` 已由用户逐条确认（2026-10-25）。
- **确认记录**：用户原话「**可以；刚才的64位和现在的模型建任务，开始处理**」（经主会话问答，2026-10-25）⇒ 对 `D1`–`D8`（含 `D4`/`D7` 的 32 MiB / 30 MiB 修订版）一并确认，并批准立册。
- **落地任务**：`LLVM-130t`（64 位缺省 + DWARF64，与 D1–D8 独立、先行）、`INFRA-106t`（`check-code-range` + 打包规范）、`LLVM-131t`（驱动 `-mcmodel` + 后端 `large`）。
