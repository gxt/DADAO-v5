# M2 规范规划（讨论稿）

> **状态**：**讨论稿（未定稿）**——记录 2026-09-22 与用户关于「插入新 M2（规范性增强）」的讨论结论，供后续 `/plan` 与任务分解使用。
> **2026-09-25 用户裁定**：**不采纳「新建规范里程碑」**——里程碑只是大任务的标志，不是推进的阻碍；当前在做的规范制定与 bug 修复都属于「修正上一阶段 + 为下一阶段铺路」，以**过渡期任务 `M1→M2`** 标注（约定见 `.tao/README.md`、`.tao/knowledge/milestones.md`）。因此 **§6 与 §7-8 不采纳**（原文保留供溯源）。
> **关联**：`docs/m1-retrospective.md`（M1 回顾，遗留/风险来源）、`.tao/knowledge/milestones.md`（里程碑路线）、`spec/`（上游规范，只读）、`.tao/knowledge/contract-*.md`（v5 归一化合约）。
> **未决事项**见 §7；本文件**不是**任务书。

---

## 1. 判据：什么是「规范」

用户的判据：**Intel / ARM / RISC-V 等 ISA 有类似物**，我们才需要制定类似规范。据此，一条「规范」应同时满足三条：

| 条件 | 含义 | M1 的反面教训 |
|---|---|---|
| ① **规范性文本** | 用 **RFC 2119 关键词**（MUST / SHOULD / MAY）书写，非叙述性文档 | 汇编语法只存在于 TableGen `AsmString`，无 normative 文本 ⇒ `wpN` 静默误编码（`LLVM-013t`） |
| ② **业界有同类物** | 能对标 Intel SDM / ARM ARM / RISC-V ISA Manual / psABI / SBI … | 无可对标物者多半是内部过程文档，应降级为工作流文档 |
| ③ **机器可检查** | 每条规范有 checker 并接入 `make check` | M1 的 `check_*` 家族（`check_issues`/`check_spec_drift`/`check_lit_bytes`/`check_qemu_trans`/`check_interface_alignment`…）证明有效；无 checker 的规范必漂移 |

---

## 2. 业界对标（参考文档）

### 2.1 已实取原文核对

| 参考 | 位置 | 要点 |
|---|---|---|
| **RFC 2119**（BCP 14） | `https://www.rfc-editor.org/rfc/rfc2119.txt` | MUST / MUST NOT / SHOULD / SHOULD NOT / MAY 的定义与用法 |
| **Linux `submitting-patches`** | `https://www.kernel.org/doc/html/latest/process/submitting-patches.html` | canonical patch format：`[PATCH M/N] subsystem: summary`、`From:`、`Signed-off-by`、`---` 分隔、`--base`、`Reviewed-by`/`Tested-by` |
| **Reproducible Builds** | `https://reproducible-builds.org/docs/source-date-epoch/` | `SOURCE_DATE_EPOCH` 规范；相关：Commandments、Stable order for inputs/outputs、Build path |

### 2.2 按名称引用（链接待逐一核对）

RISC-V **ISA Manual**（含 Unprivileged / Privileged / **Assembly Programmer's Manual** / **RVWMO** 内存模型）· RISC-V **ELF psABI** · RISC-V **Platform Spec**（RVA/RVM profiles）· RISC-V **Debug Spec** · **riscv-arch-test** / **riscv-tests** · **Spike** / **Sail** · **AAPCS64**（ARM ABI）· **System V ABI** · **ELF gABI** · **Intel SDM Vol.2**（指令语法）· **GNU as Manual** · **quilt** / **Debian `debian/patches/`** · **Devicetree Specification** · **OpenSBI** / **ARM TF-A** · **MADR** / **SemVer** / **Keep a Changelog** · Clang diagnostics / POSIX `sysexits.h` · LLVM **lit** / `FileCheck`。

> **RISC-V 规范家族的启示**：RISC-V 不是「一个规范」，而是一个**家族**（Unprivileged ISA ／ Privileged ISA ／ Assembly Programmer's Manual ／ psABI ／ Debug ／ Platform ／ SBI ／ RVWMO ／ arch-test）⇒ 新 M2 的产出形态应是**对应的 DADAO 规范家族**，而非零散文档。

---

## 3. 规范家族映射（候选清单 N1–N16）

| # | 主题 | 业界同类规范 | 应制定的规范（建议名称） | 参考文档 |
|---|---|---|---|---|
| **N1** | 汇编语法 | RISC-V Assembly Programmer's Manual；GNU as；Intel SDM Vol.2；ARM armasm | **《DADAO 汇编语言手册》** | RISC-V Assembly Manual；GAS；SDM Vol.2 |
| **N1a** | 伪指令 | RISC-V 手册「Pseudo-instructions」 | 同上（独立章） | 同上 |
| **N1b** | 寄存器 ABI 名 | RISC-V psABI；AAPCS64 | **《DADAO ABI 命名规范》** | RISC-V psABI；AAPCS64 |
| **N2** | 补丁/组件工作流 | Linux submitting-patches；quilt；Debian patches | **《组件补丁与构建编排规范》** | Linux submitting-patches ✓；quilt；Debian Policy |
| **N3** | Bare-metal 硬件状态 | RISC-V Privileged / Platform；Devicetree；SBI | **《DADAO 测试机平台规范》** | RISC-V Privileged/Platform；Devicetree；本项目 SEE/SBI |
| **N4** | 诊断与错误消息 | Clang/GCC diagnostics；POSIX `sysexits.h` | **《工具链诊断规范》** | Clang Diagnostics；`sysexits(3)` |
| **N5** | 可复现构建 | Reproducible Builds | **《可复现构建规范》** | reproducible-builds.org ✓ |
| **N6** | 验证与证据 | riscv-arch-test；Spike/Sail；LLVM lit | **《验证与证据规范》** | riscv-arch-test；Sail/Spike；LLVM lit |
| **N7** | 元规范 | RFC 2119；MADR；SemVer；Keep a Changelog | **《工程过程规范》** | RFC 2119 ✓；MADR；SemVer |
| **N8** | 跨模块接口 | System V ABI；RISC-V ELF psABI；ELF gABI | **《DADAO psABI》** | System V ABI；RISC-V psABI；ELF gABI |
| **N9** | 汇编↔反汇编往返 | （属测试约定） | 汇编手册的 normative 条款 + `make check` 子项 | LLVM MC 测试约定 |
| **N10** | 外部接口（CodeGen 前置） | AAPCS64；RISC-V psABI；SBI | **《调用约定》/《重定位》/《外设平台》规范** | AAPCS64；RISC-V psABI；SBI |
| **N11** | 内存模型/屏障 | RISC-V **RVWMO**；ARM memory model | **《DADAO 内存模型规范》** | RISC-V RVWMO |
| **N12** | 异常/中断模型 | RISC-V Privileged（traps） | **《DADAO 异常模型规范》** | RISC-V Privileged |
| **N13** | 启动/固件协议 | OpenSBI；ARM TF-A；UEFI PI | **《DADAO 启动协议规范》** | OpenSBI；TF-A |
| **N14** | 指令编码 | ISA manual 编码表 | **《DADAO 指令编码规范》** | RISC-V ISA Manual |
| **N15** | 术语与写作风格 | Google Style Guides；ISO 术语约定 | **《术语与写作规范》** | Google Style Guides |
| **N16** | 工具链 CLI | GCC/Clang CLI conventions | **《工具链 CLI 规范》** | `gcc(1)`；Clang CLI |

**每条规范的标配**：规范文本（RFC 2119 关键词）+ 机器可读数据（可选）+ **checker（入 `make check`）** + 「参考业界规范」一节。

---

## 4. 与 `spec/` 已有规范的对照结论

`spec/` 共 **11 份**（均带版本头）：SimRISC-00~04（`0.5.3`）、DADAO-11/21（AEE/ABI `0.9.2`）、DADAO-12/22（SEE/SBI `0.7.1`）、DADAO-13/23（HEE/HBI `0.1.2`）。

### 4.1 覆盖情况

| # | 主题 | `spec/` 覆盖 | 调整 |
|---|---|---|---|
| N1 | 汇编语法 | **部分**：逐指令操作数形式已在（`fence immu18`、`escape cfx_<name>, imms18`、`操作数类型：oiii`）；**directives/选项**在 DADAO-11 §汇编兼容性（`.dd.b08/w16/t32/o64`、`-multiple-to-single`） | 降级为「归一化 + checker」；仅「LLVM MC 实现层语法」为 v5 自定 |
| N1a | 伪指令 | **已覆盖**：SimRISC-00 §伪指令 | 归一化 |
| N1b | 寄存器 ABI 名 | **已覆盖**：DADAO-21 §寄存器规范 | 归一化 |
| N2 | 补丁/组件工作流 | **未覆盖** | v5 自定 |
| N3 | Bare-metal 硬件状态 | **部分**：DADAO-12 §2 地址空间 / §4 寄存器 / §5 异常进入退出；**测试机内存映射/复位值全集/exit 协议不在 `spec/`** | 拆两层：ISA 层归一化 + 测试机层 v5 自定 |
| N4/N5/N6/N7 | 诊断/可复现/验证/元规范 | **未覆盖** | v5 自定 |
| N8 | psABI | **已覆盖**：DADAO-21（寄存器/数据表示/函数调用/系统调用）+ DADAO-11（地址空间/汇编兼容） | 归一化 |
| N9 | 往返 | **未覆盖** | v5 自定 |
| N10 | CodeGen 前置 | **已覆盖**：调用约定（DADAO-21 §函数调用规范：Stack Frame/传参/可变参数/返回值）、外设（DADAO-12 §4 `cfx_timer`/`cfx_uart`/`cfx_power`/`cfx_cache`/`cfx_tlb`… + DADAO-22 §10–12）、启动移交（DADAO-13 §3 / DADAO-23 §3） | 大幅降级；仅「重定位」为 v5 自定 |
| N11 | 内存模型 | **部分**：SimRISC-04 §fence（屏障类型位 + SBZ）；**无完整内存模型** | 归一化 fence + 判断是否需 v5 内存模型 |
| N12 | 异常模型 | **已覆盖**：DADAO-12 §5 + SimRISC-00/04 | 归一化 |
| N13 | 启动协议 | **部分**：DADAO-13/23 §启动与引导移交（hypervisor 级）；**测试机启动不在** | 拆两层 |
| N14 | 指令编码 | **已覆盖**：SimRISC-00 §指令设计/§指令域说明/QFC 编码表 | 归一化 |
| N15/N16 | 术语/CLI | **未覆盖** | v5 自定 |

**结论**：上游 `spec/` 是**权威 ISA/平台层**，已覆盖 N1(部分)/N1a/N1b/N8/N10/N12/N14 与 N3/N11/N13 的部分 ⇒ **v5 的主要工作是「归一化 + checker」**，真正的「新规范」集中在**工程层**。

### 4.2 `spec/` 自身暴露、需在 v5 侧处置的问题（`spec/` 只读，不改上游）

| # | 现象（实测） | 影响 | v5 侧处置 |
|---|---|---|---|
| 1 | **规范性关键词缺失**：11 份文档 `MUST`/`SHALL` = **0**；「应/必须/可」混用（DADAO-12「应」77 次、「可」82 次、「必须」仅 2 次） | 无法机械判定硬约束 | 归一化时**显式标注规范性等级** |
| 2 | **重复小节**：SimRISC-01 与 SimRISC-02 各有「### 寄存器组之间块赋值」「### 立即数常数赋值」 | 两处漂移风险（M1 块赋值语义争议源于此） | 归一化时**单一来源 + 交叉引用** |
| 3 | **实现细节混入规范**：DADAO-12 §4 各 `cfx_*` 含「初始化/内部实现代码/功能调用示例」；DADAO-22 亦然 | 规范与示例混杂 | 归一化时**分离条款与示例** |
| 4 | **「退出指令」≠ 程序停机**：SimRISC-04 §退出指令是 `escape cfx_<name>, imms18`（**退出特权态**） | v5 的 halt 无处可依 | v5 自定 exit port（ADR-0004 D3）⇒ 记入**偏离台账** |
| 5 | **`fence` SBZ 语义**：上游「bits[17:4] 应为零（SBZ），**非零值行为保留**」；v5 定 **ILLI**（`misc[4]` 期望 ILLI） | 上游「保留」vs v5「ILLI」是**决策** | 记入**偏离台账**；亦是 `fence` deferred 的规范侧根因 |
| 6 | **测试机层整体缺失**：内存映射/复位值全集/exit 协议/启动协议 | ADR-0004 已自定但未升格 | 升格为《测试机平台规范》 |
| 7 | **ELF/Object ABI 整体缺失**：`spec/` 无 ELF 内容 | ADR-0003 已自定 | 升格为《DADAO psABI/ELF》 |
| 8 | **M1 排除项**：浮点（SimRISC-03 全篇）、特权 cfx（DADAO-12/13）、LR-SC | M1 不实现但规范仍在 | 统一「Excluded from M1」口径（`opcodes.yaml` 已有 `excluded_m1`） |

---

## 5. 调整后的 M2 规范清单（三层结构）

### 第 1 层 — **归一化层**（上游已有 → 提取为 contract + checker，**不新写 ISA 规范**）

| 规范 | 上游来源 | 现有 v5 产出 |
|---|---|---|
| 汇编语法与伪指令 | SimRISC-00 §伪指令/§指令设计 + 01/02/04 + DADAO-11 §汇编兼容性 | 部分（`AsmString`，**未成文**） |
| 寄存器与调用约定 | DADAO-21 §寄存器规范/§函数调用规范 | `contract-abi.md`（M1 最小集；**完整约定待提取**） |
| 指令编码 | SimRISC-00 §指令设计/QFC | `opcodes.yaml` + `contract-isa.md` ✓ |
| 异常模型 | DADAO-12 §5 + SimRISC-00/04 | `contract-isa.md §9`（部分） |
| 内存序（fence） | SimRISC-04 §fence | `contract-isa.md §7.3` ✓ |
| 外设/平台（UART/timer/power） | DADAO-12 §4 + DADAO-22 §10–12 | **无**（M2 CodeGen 需要） |
| 启动与引导 | DADAO-13 §3 / DADAO-23 §3 | **无**（测试机启动在 ADR-0004） |

### 第 2 层 — **v5 工程层**（上游无 → v5 自定）

《工具链 CLI 规范》《工具链诊断规范》《可复现构建规范》《组件补丁与构建编排规范》《验证与证据规范》《工程过程规范（元规范）》《汇编器实现层语法（LLVM MC）》《重定位规范》

### 第 3 层 — **偏离与自洽台账**（建议作为 M2 首要交付物）

- **上游 ↔ v5 偏离台账**：exit port（vs `escape`）、`fence` SBZ 非零→ILLI、测试机地址映射/复位值、`ra0=0`（MemRAS 简化）、`e_flags` 版本字段、M1 排除口径
- **上游自洽性问题清单**（§4.2 的 1/2/3 类，供归一化规避，可选反馈上游）

---

## 6. 对 M2 的定位影响

> **❌ 不采纳（2026-09-25 用户裁定）**：本节 §6.1–§6.3 的「新 M2 重定义为『规范与接口冻结』、Basic CodeGen 顺延为 M3」**不予采纳**。用户裁定：里程碑只是大任务的标志，不是推进的阻碍；当前工作属「修正上一阶段 + 为下一阶段铺路」，以过渡期任务 `M1→M2` 标注即可，**不需要构建所谓的新 M2**。`milestones.md` 的 M2 行保持「Basic CodeGen 待开始」不变。**本节原文保留**，仅供溯源；其下的 ⚠️ ADR 提醒**仍然有效**（汇编语法、测试机平台规范、诊断格式、psABI 升格仍须各自按判据立 ADR）。

1. 现 `milestones.md` 的 **M2「Basic CodeGen」需顺延为 M3**（引用同步：`milestones.md`、`README.md`、`docs/m1-retrospective.md §9` 等）
2. 新 M2 建议命名：**「M2 — 规范与接口冻结（Normative Freeze）」**
3. 新 M2 的门槛建议：`make check` 全绿 **且** 新增 checker 全部接入（含反例门控）

> ⚠️ **ADR 提醒**（`AGENTS.md` 强制）：本 M2 多项主题触及 ADR 判据（外部契约 / 不可逆 / 跨模块 / 结论固化）——汇编语法、测试机平台规范、诊断格式、psABI 升格均建议立 ADR；补丁工作流属内部过程（可逆），建议**不**立 ADR。

---

## 7. 待裁决项

1. **范围**：N1–N10 照单，还是加上 N11–N16？（建议至少纳入 N11/N12/N14/N15——均有 M1 直接痛点）
2. **第 1 层是否只做「归一化 + checker」**（不新写 ISA 规范）？
3. **第 3 层「偏离台账」是否作为 M2 的**首要**交付物**？
4. **`spec/` 的问题**是否反馈上游，还是只在 v5 侧规避？
5. **落点**：归一化产物放 `docs/spec/`（v5 规范层，与只读的 `spec/` 区分）还是扩 `.tao/knowledge/contract-*.md`？
6. **命名前缀**：《**DADAO** … 规范》还是《**DADAO-v5** …》？
7. **对标清单是否逐一实取原文核对**（GitHub 侧本次超时；可换镜像/官方 HTML 版）？
8. 是否先把本讨论整理为 **`M2` 的 `k`（启动/分解）任务书草案**，走 `/plan` 再定？
   > **❌ 不采纳（2026-09-25 用户裁定）**：不构建新 M2，故不产出该 `k` 任务书。§7-1~7-7 保留为**候选工作清单**（不再作为里程碑定义）。
