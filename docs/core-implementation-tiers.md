# 核实现分层（core implementation tiers）

> **定位**：本册定义 `dadao-wuming` / `wuqing` / `wuxing` 三个**核实现型号**的分层口径、平台映射与不变量；是**实现口径**，不是 ISA 规范。
> **真源关系**：ISA 可见语义以 `spec/` 为准；本册只回答「有哪些核型号、各自对应什么微架构、在哪些平台验证」。
> **周期细节**：`wuming` 的逐族周期见 `docs/core-wuming-cycle-model.md`；本册不复制周期表。
> **状态**：口径已冻结（2026-11-13 用户裁定）；`wuqing` / `wuxing` 尚无 RTL 实现。

## 1. 两条正交轴

- **轴 A：微架构类别**——决定 RTL 结构与验证重点（见 §2）。
- **轴 B：机器能力**——Tiny / Vast；cache / MMU / FPU / 中断 / 多 hart。

两轴独立组合：机器能力不随核型号改变，核型号不隐含机器能力。Linux bring-up 只依赖轴 B 的 Vast + MMU，不被核演进阻塞。

## 2. 三个核型号

### `dadao-wuming` — 非流水化 / 多周期

- 无流水寄存器，逐拍推进；「单周期」只是历史称呼，**不是每条指令 1 拍**——多寄存器、`ldm`/`stm`、FP 除法/开方都为多周期。
- 现状：chipyard `WumingTinyConfig`（`Kaiwu-Tiny`，无 cache、无 MMU）。
- 下一步：**Vast + MMU**；不在本核上做流水化改造。

### `dadao-wuqing` — 顺序流水线 / 单发射

- 经典 IF-ID-EX-MEM-WB；重点是**可时序评估**。
- 后续可扩为**顺序多发射**（宽度参数化，不新建 generator）。
- 结构溯源：DADAO 参考实现的 5 级核（Sodor 血统，仅结构参考，不复制代码）。

### `dadao-wuxing` — 乱序执行

- 对标 BOOM 类乱序核；**设计复杂度与发射宽度现在不讨论**。
- 可参考的参数区间（chipyard BOOM）：Small decode 1 宽 / ROB 32；Medium 2 / 64；Large 3 / 96；Mega 4 / 128。

## 3. 平台映射

- gem5 的 `AtomicSimpleCPU` 对应 `wuming`（功能 / 语义）。
- 同一核型号在 chipyard RTL 与 gem5 模型上要求一致：**语义一致 = 同向量同结果**；是否含时序 / 性能口径，待对应型号立项时定义。
- 现状缺口：gem5 只有 `AtomicSimpleCPU`，无 cache / 时序；`DadaoInst` 未实现 `isControl` / `isMemRef` 等分类接口 ⇒ 接 `Minor` / `O3` 须另立项。

## 4. 不变量

1. 分层只改 RTL/config 命名与验证目标，**不改 ISA / ABI / spec 可见语义**。
2. 一个 ELF machine；不复制 binutils 的 `bfd_mach_dadao_*` 三编号；不按型号分 `-mcpu` 语义。
3. 同一微架构族参数化（BOOM 式），不做多套独立 RTL 树。

## 5. 与其他文档的关系

- `spec/`：ISA / ABI / 机器语义的唯一真源；本册不重复。
- `docs/core-wuming-cycle-model.md`：`wuming` 的逐族周期（实现口径）。
- `spec/Kaiwu-测试机运行环境.md`：Tiny / Vast 的机器定义。
