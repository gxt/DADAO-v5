# 资源管理 -- cfx 寄存器模型

**本册要点**

- `cg`/`rc` 两级编号：`cg` 在 `hb`、`rc` 在 `hc`、`rd` 在 `hd`。
- `cg0`–`cg7` 通用；`cg8`+ 专有。
- 通用面：version、masks、switch、vector、exception、scratch、SRAM。
- scratch 至少 2、最多 64。
- 寄存器不在 48 位地址空间；只能用 `cfx2rd`/`cfx2rc`。
- `cfx2rd`/`cfx2rc` 只连 `rd`；`rb`/`rf` 经 `set.rd`。

## 1. 为什么用 `cg`/`rc` 两级编号，而不是平铺地址？

**答：** 因为一个 cfx 的寄存器远多于 64 个，而 `cfx2rd`/`cfx2rc` 只有三个 6 位字段可用；`cg`/`rc` 两级正好把“组”和“组内编号”分开，还能让通用组和专有组各占一段。

- **字段**：`cfx2rd cfxHA, cgHB, rcHC, rdHD`——`cg` 在 `hb`、`rc` 在 `hc`、`rd` 在 `hd`，各 6 位。
- **容量**：6 + 6 = 12 位，最多 64 组 × 64 个 = 4096 个寄存器。
- **分区**：`cg0`–`cg7` 通用，`cg8`+ 专有；平铺 12 位会把通用/专有混在一起。
- **对比**：RISC-V CSR 12 位平铺；x86 MSR 32 位；PowerPC SPR 10 位；MIPS CP0 5 位；ARM system register 16 位编码——cfx 用“组 + 组内号”，更适合“通用 + 专有”的分层。

## 2. 为什么 `cg0`–`cg7` 是所有 cfx 通用的？

**答：** 因为每个 cfx 都要能被通用软件发现、配置、异常处理；identity/version/masks/switch/exception/scratch/SRAM 是“资源的最小公共面”。

- **`cg0`**：version、global mask、指令类型 mask、switch mode/mask、异常向量、异常原因 mask（按模式）。
- **`cg3`**：`hypv` 模式的同一组字段。
- **`cg4`**：`cfx_id`、`version`、`trap_num`/`excp_sync_num`/`excp_async_num`/`escape_num`、`scratch_regs_num`。
- **`cg5`**：prev mode/mask、cause id/ip/info、pending、nonmaskable。
- **`cg6`**：scratch 寄存器。
- **`cg7`**：SRAM 的 `block_sel`/`sram_addr`。
- **为什么**：通用 handler/探测代码只认这 8 组；各 cfx 不必重新发明“版本、mask、异常状态”。
- **对比**：x86 有 MSR 但字段各异；ARM system register 有统一编码但语义分散；RISC-V CSR 有标准/非标准分区；cfx 把“每个资源都需要的字段”固定成 cg0–7。

## 3. 为什么 scratch 至少 2 个、最多 64 个？

**答：** 至少 2 个是因为 handler 至少要保存“旧状态”和一个工作寄存器，而不必先访存；上限 64 是因为 `rc` 只有 6 位。

- **数量**：`cfx_<name>_scratch_regs_num` 给出 N；有效 rc = 0..N−1；rc ≥ N → `CFXREG`。
- **为什么至少 2**：handler 可能在栈/地址转换还没准备好时运行；用 scratch 保存旧 mask + 一个中间值，避免先访存。
- **为什么最多 64**：`rc` 6 位；再多的寄存器要另设 cg。
- **对比**：x86/ARM/RISC-V/MIPS/SPARC/PowerPC 都没有“每资源 scratch”，handler 一般用通用寄存器 + 栈；cfx 把“最小现场保存”做成资源自带。

## 4. 为什么 cfx 寄存器只能通过 `cfx2rd`/`cfx2rc` 访问，不能像 MMIO 一样直接 `ld`/`st`？

**答：** 因为 cfx 寄存器不在 48 位地址空间里，而是 cfx 内部的 `cg`/`rc` 命名空间；用 `cfx2rd`/`cfx2rc` 访问才能同时带 `cfxha`、`cg`、`rc`，并做权限/存在性检查。

- **地址窗口 vs 寄存器**：`ld`/`st` 打的是 cfx 的 64 KiB 窗口；寄存器是窗口之外的另一套命名空间。
- **检查**：`cfx2rd`/`cfx2rc` 会检查 cfxha/cg/rc 是否存在、权限是否匹配；不通过 → `CFXREG`。
- **副作用**：RO/WO/HW 寄存器不能靠普通 `ld`/`st` 表达“写无效/只写/硬件写”。
- **对比**：x86 `RDMSR`/`WRMSR`、ARM `MRS`/`MSR`、RISC-V `csrrw`、MIPS `mfc0`/`mtc0`、SPARC `RDASR`/`WRASR`、PowerPC `MFSPR`/`MTSPR`——都是专用指令，不是 MMIO；cfx 沿用这个思路，但把编号拆成 `cfxha` + `cg` + `rc`。

## 5. 为什么 `cfx2rd`/`cfx2rc` 只连 `rd`，`rb`/`rf` 要经 `set.rd` 中转？

**答：** 因为 cfx2rd/cfx2rc 的数据通路只连 `rd`；`rb`/`rf` 先用 `rb2rd`/`rf2rd` 转到 `rd`，汇编器用 `set.rd` 简化。

- **格式**：`crrr` 的最后一个字段是 `rd`；没有 `rb`/`rf` 变体。
- **中转**：`rb` → `rb2rd`；`rf` → `rf2rd`；汇编器 `set.rd rd, rs` 自动展开。
- **为什么**：cfx2rd/cfx2rc 只接一个数据寄存器类，减少寄存器堆端口与格式变体；`rb`/`rf` 的搬运已有块赋值指令。
- **对比**：x86 `RDMSR` 用 EAX/EDX；ARM `MRS` 用 Rt；RISC-V `csrrw` 用 rd；MIPS `mfc0` 用 rt；SPARC `RDASR` 用 rd；PowerPC `MFSPR` 用 rd——都是“一个 GPR”，cfx 选 `rd`。

## 背景知识

### 术语与概念

- **寄存器组（`cg`）**：cfx 寄存器的第一级编号；0–7 为所有 cfx 通用，8+ 为专有。
- **`rc`**：组内编号；不同 `cg` 的 `rc` 含义不同。
- **scratch**：cfx 提供的暂存寄存器，至少 2 个、最多 64 个，供 handler 保存现场。
- **`CFXREG`**：访问不存在的 cfx/cg/rc 或权限不符时触发的异常。
- **RO/WO/HW**：只读、只写、硬件写；写入语义与普通 RW 不同。
- **复位值**：mask 类通常复位为全 1（屏蔽），权限类按 cfx 不同（如 `ptw` 的 user/jail 全 0、supv/hypv 全 1）。

### 对照

**x86-64**：MSR 按 32 位地址访问，`RDMSR`/`WRMSR` 用 ECX 选号；没有“组/组内号”。

**ARM64**：system register 按 16 位编码访问，`MRS`/`MSR`；按 EL 控制可见性。

**RISC-V**：CSR 12 位地址，`csrrw`/`csrrs`/`csrrc`；标准/非标准分区。

**MIPS**：CP0 5 位寄存器号，`mfc0`/`mtc0`；只覆盖处理器控制。

**SPARC**：ASR 按编号访问，`RDASR`/`WRASR`；资源分散。

**PowerPC**：SPR 10 位编号，`MFSPR`/`MTSPR`；MSR 管模式。
