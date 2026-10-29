# ADR-0040: PTE 格式、页表步进与页权限

**状态**：Accepted
**日期**：2026-10-29
**关联**：ADR-0039（地址空间/PTBR）、ADR-0041（TLB/A-D）；`spec/DADAO-12` §2.2.3–§2.2.6；任务 `INTEG-039t`（Step 2）

## Context（背景）

地址空间已由 ADR-0039 固定为 42 位 VA、56 位 PA。需要定义 64 位 PTE 的字段、两级页表步进、HSJU 模式权限、SPF/GPF 小页存在位，以及页表异常的优先级。TLB/A-D 回写留到 ADR-0041，避免 Step 2 先写一版再返工。

## Decision（决策）

- **D1 PTE 64 位**：HSJU `[63:60]`，保留 `[59:56]`，PPN `[55:16]`（超页 `[55:29]`），SPF/GPF `[15:8]`，flags `[7:0]`：`P=0`、`SP=1`、`D=2`、`A=3`、`G=4`、`X=5`、`W=6`、`R=7`。
- **D2 两级页表**：L1/L2 表均 64 KiB、8192 项；VA `[41:29]` 选 L1，`[28:16]` 选 L2，`[15:0]` 为 64 KiB 页内偏移。
- **D3 L1 next-level**：`SP=0`、`P=1` 表示指向 L2 表；PPN `[55:16]` 为 L2 表基址；非叶子只认 P，不使用 HSJU/RWX/A/D/G（G 必须写 0，硬件忽略）。
- **D4 L1 超页**：`SP=1` 为 512 MiB 超页；PPN `[55:29]`，`[28:16]` 为 0；SPF 8 位对应 8 个 64 MiB 小页，`VA[28:26]` 选位；位 0 → `ISPFTRAP/DSPFTRAP`；叶子 G=1 表示全局页（见 D11）。
- **D5 L2 普通页**：`SP=0` 为 64 KiB 页；PPN `[55:16]`；GPF 8 位对应 8 个 8 KiB 小页，`VA[15:13]` 选位；位 0 → `IGPFTRAP/DGPFTRAP`；叶子 G=1 表示全局页（见 D11）。
- **D6 HSJU**：当前模式对应位为 1 才可访问；否则 `NUPERM/NJPERM/NSPERM/NHPERM`。硬件不做 S 自动覆盖 U、H 自动覆盖 S；用户页/内核页组合是 OS 策略，架构不强制。
- **D7 R/W/X**：取指要求 X=1（否则 NXPERM），读要求 R=1（否则 NRPERM），写要求 W=1（否则 NWPERM）；与 HSJU 正交。
- **D8 异常优先级**：`P=0`/超页缺失 → SPF/GPF 对应位=0 → HSJU 不符 → R/W/X 不符。只报最高优先级异常。
- **D9 保留位/对齐**：保留位软件写 0、硬件忽略；PPN 低位非对齐时硬件强制清零，不 fault；`P=0` 时其它字段忽略。
- **D10 A/D**：Step 2 只定义 A/D 位，不更新；A/D 硬件维护、TLB dirty 回写与 CLEAN/FLUSH/INVALID 留 ADR-0041。
- **D11 G（Global）**：`G=1` 的叶子页在 TLB 中不按 ASID 匹配，可跨 ASID 复用；`G=0` 按 ASID 匹配。next-level 的 G 无意义。软件必须保证 G 页在所有地址空间中的映射一致；失效规则见 ADR-0041 D3.1。

## Rationale（理由）

HSJU 四位掩码取代旧“HMON/SMON 00/01/10”两位语义，避免模式与页类型绑死；SPF/GPF 作为小页存在位，支持稀疏加载而不改页大小；异常优先级把“不存在”放在“权限”之前，便于 OS 区分缺页与保护错误。A/D 与 TLB 一起做能避免先写直写 PTE、再改 dirty 回写的返工。

## Consequences（影响）

- `spec/DADAO-12` §2.2.3/§2.2.4 的 PTE 表要从旧 32 位 PPN/顶部 SPF 改为本布局；Step 1 留下的过渡态必须由 Step 2 收口。
- G 位（bit4）在 Step 3 落地 TLB 时补进 spec/QEMU 测试；Step 2 已验收的页表步进不需要重开，但规格中的 bit4“保留”必须同步改为 G。
- QEMU 需要页表步进与 HSJU/RWX/SPF/GPF 检查；A/D 更新在 Step 3 才验证。
- `NUPERM/NJPERM/NSPERM/NHPERM` 保留；不再使用旧 PTBR 模式权限。

## 状态说明

Step 2 已由 `INTEG-039t` 落地并验收；G 的 TLB 行为在 Step 3 实现，本 ADR 决策已接受。
