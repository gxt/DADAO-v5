# LLVM-130t: 64 位缺省与 DWARF64

**模块**：llvm
**项目里程碑**：M10
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（LLVM 重建 `make install-host` 由主会话执行，属长任务）

## 接口规范

### 背景事实（实测，2026-10-25，ADR-0036 关联）
- `MCAsmInfo` 默认 `CodePointerSize = 4`、`CalleeSaveStackSlotSize = 4`（`llvm/include/llvm/MC/MCAsmInfo.h:89/93`）；DADAO 的 `DADAOMCAsmInfo.cpp` **两个都没设**（整份 patch 中零命中）。
- 后果 1：`clang --target=dadao-unknown-elf -g -c` 报
  `relocatable operand in '.dd.b08/.dd.w16/.dd.t32' is not supported`；实测 `-gdwarf64 -S` 输出里 `.debug_addr` 头为 `Address size = 4`，地址落 4 字节字段 ⇒ 3 处报错。
- 后果 2：`CalleeSaveStackSlotSize=4` 直接用于 `MCDwarf.cpp:1340 getDataAlignmentFactor()`（CFI 的 `data_alignment_factor`）；当前 `ExceptionsType=None` 无 CFI，属潜伏缺陷，本次一并修正。
- 对照：AArch64 / RISC-V 均显式设 `CodePointerSize = CalleeSaveStackSlotSize = 8`。
- 选项存在性：clang 已有 `-gdwarf64` 与 `-gdwarf32`（`clang/include/clang/Options/Options.td:5141/5145`）。

### 输入
- `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch`
- `components/llvm-project/patches/clang/lib/Driver/ToolChains/DADAO.cpp.patch`（若必须改共享文件，完成区须单列理由）

### 输出
1. `DADAOMCAsmInfo` 构造加 `CodePointerSize = CalleeSaveStackSlotSize = 8;`（注释指明 64 位原生 / ADR-0036）。
2. **DADAO 默认 DWARF64**：启用调试信息时驱动默认追加 `-gdwarf64`；用户显式 `-gdwarf32` ⇒ **明确报错**（DADAO 无 32 位重定位通道，不得静默降级）；用户显式 `-gdwarf64` 时保持。
3. 位宽探针 `tools/llvm/check-width-sizes.py` + Makefile 目标 `check-width-sizes`（L1）：
   - 静态断言编译：`sizeof(void*/long/size_t)==8`、`_Alignof(max_align_t)==16`、`sizeof(long double)==16`、`__BIGGEST_ALIGNMENT__==16`；
   - 产物：`llvm-readelf -h` Class=ELF64、`.rela` entsize=24、`.got` 项=8；
   - `-g` 产物：`llvm-dwarfdump --debug-info` 的 `Address Size: 8`；
   - 每条断言有**可达 FAIL** 路径。

### 约束
- 只动上述文件 + `tools/llvm/` 新脚本 + `Makefile` 一行目标；不改 `spec/`、不改数据指令、不改其它 target。
- 先留**失败现场**（修复前 `-g` 的真实报错），再改。

## 验收标准
1. `clang --target=dadao-unknown-elf -g -c` rc=0；`llvm-dwarfdump --debug-info` 显示 `Address Size: 8`，`DW_AT_low_pc` 与符号地址一致。
2. `clang -g` 链接产物可被 `llvm-dwarfdump` 正常解析（`.debug_info` / `.debug_line`）。
3. `make check-width-sizes` 绿；**反例注入**（改被检字段使断言 FAIL）→ 红 → `cp` 还原 → 绿（禁 `git checkout` 还原）。
4. `make install-host` 后 `make check` 绿；L2 代表集绿。
5. 完成区贴真实命令、退出码、日志路径。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
