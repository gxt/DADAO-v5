# LLVM-129t: 让 LLVM 用上 `ldm`/`stm`（多寄存器 load/store）

**模块**：llvm
**项目里程碑**：M9（用户 2026-10-23 裁定「M9 做」）
**依赖**：`LLVM-127t`（窄位类型已稳定）、`INFRA-102t`（门控已去常量）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状

### 用户裁定
2026-10-23：「4、M9做」（在「`ldm`/`stm` 立不立项」一问中选 M9 内完成）。

### 现场事实（2026-10-24 核，执行前须复核）
- ISA 已有 `ldm.*`/`stm.*`（`rrri`，`immu6` = 寄存器个数；`immu6 = 0` 触发 ILLI，`legality_rules.yaml::mreg_zero`）。
- `contract-abi §1.3` 明确：`rb32`–`rb63` 是**连续 callee-saved 池**，「可整段用 `stm`/`ldm` 批量保存/恢复」；`rd32`–`rd63` 同为 callee-saved。
- LLVM **完全未使用**它们（`gen_isa_coverage`：`ldm.*`/`stm.*` 全部 `L2_isel=no`）；当前序言/尾声与拷贝都是逐条 `ld.o`/`st.o`。
- LLVM 的 `MaxStoresPerMemcpy/Memset/Memmove = 16`、`MaxLoadsPerMemcmp = 16`（`DADAOISelLowering.cpp`）。

## 目标

让 LLVM 在**不改变语义**的前提下发射 `ldm`/`stm`，至少覆盖：

1. **函数序言/尾声**：多个连续 callee-saved 寄存器的保存/恢复合并为 1 条 `stm`/`ldm`；
2. **连续栈槽的 spill/reload 突发**（若可行）；
3. 一般相邻访存（可选，命中率低）。

**实现机制不预设**：post-RA 机器层合并（参考 `llvm/lib/Target/ARM/ARMLoadStoreOptimizer.cpp`）、pre-RA 聚拢、或其它方案，由工程师论证并在完成区写明**选择理由与代价**。

## 边界（必须写进完成区）

- **不承诺 `memset`**：`stm` 写的是「寄存器组 → 连续地址」，每个寄存器值不同；`memset` 是同一值重复，用 `stm` 需先把值复制到 n 个连续寄存器，收益为零或负。
- `memcpy`：内联展开路径（≤16 次存取）可能受益，但依赖 RA 后寄存器连续；不承诺一定能合并。
- **`MaxStoresPer*` 阈值在本册完成前不改**；合并机制落地后再**用 embench 实测**决定是否调整（无实测不动）。

## 验收

1. **可测量的合并**：构造一个使用 ≥8 个 callee-saved 寄存器的函数，`-O2` 汇编中序言/尾声出现 `stm`/`ldm`（贴前后对比：逐条 `st.o` 条数 → `stm` 条数）。
2. **语义不变**：`libc-test` 静态档、`embench` 38/38、`lit` 全绿；`check_qemu_trans --strict` 266/266。
3. **不误合并**：中间有 `call`、别名写、跨 bank、`immu6 = 0`、寄存器不连续等场景**不得合并**（各 1 条反例，用汇编观察）。
4. **可达 FAIL ≥2**：① 关掉合并 pass ⇒ 序言/尾声断言红；② 故意允许跨 `call` 合并 ⇒ 正确性用例红。
5. 门控：`check-instrinfo`、`check-isa-coverage`、`check-scope`、`check_qemu_trans 266/266`、`check_lit_gen`、`check-lit`、L1、L2；`check-patch-tree`（新增 pass 文件须进补丁树与 `series`）。
6. 覆盖披露：新增/删除/修改用例数。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（新增 pass 文件 + `DADAOTargetMachine.cpp` 挂载 + `DADAOInstrInfo.td` 若无 pattern 需补）、`tests/llvm/lit/**`。
- **输出**：合并 pass（或等价机制）+ lit 正/反例 + 前后对比数据。
- **约束**：不改 ISA / `spec/` / `contracts/`；不改 `scope`；不 commit/push；临时目录 `/tmp/opencode/LLVM-129t/`。

## 风险与纪律

- **正确性优先**：多寄存器指令的寄存器顺序、基址/偏移语义、异常边界（未对齐）必须逐条核对 `SimRISC-01`/`SimRISC-12`；任何不确定就不合并。
- 改 `.td` ⇒ `install-host` + `build-builtins` + `build-musl-shared`。
- 回归超预期（>2 个代表用例 2 h 内定位不了）⇒ 保留 WIP、停在该阶段、报 architect。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
