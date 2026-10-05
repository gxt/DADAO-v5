# LLVM-055t: 全局数据 lower（`.data`/`.rodata`）+ `ABS48`/RELA fixup

**模块**：llvm
**项目里程碑**：M4
**依赖**：`LLVM-050t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `LLVM-050t` 的 `ABS48`/RELA fixup 与 `getRelocType` 设施；`contract-elf.md §1/§2/§5`（段对齐、`SHT_RELA`、`ABS48` 公式/3 片）。
  - M3 CodeGen（`DADAOTargetMachine` 已用 `TargetLoweringObjectFileELF`；`DADAOAsmPrinter`/`DADAOMCInstLower`）；`ADR-0018`（C9 DataLayout `E-m:e-p:64:64-i64:64-i128:128-n32:64-S128`；C2 指针 i64 通吃）。
  - `DADAO-0628 DL-061c`（globals 经标准 `ld.lld` + 链接脚本；`ML-003e` Gap 2 数据段函数指针）+ `ML-030a`（大常量折入 relocation 越界）——**只读对照**。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  - `llc` 对含**全局变量/静态数据**的模块发射正确的 `.data`/`.rodata`/`.bss` 段（对齐依 `contract-elf §5`：`.rodata`/`.data`/`.bss` 8B；大端）。
  - `GlobalAddress` 的地址材料化：跨 section/未定义符号 → `set.zw`/`or.w` 序列 + **`R_DADAO_ABS48`**（固定 3 片，`ADR-0019` D4/D5）；同 section 可解析者就地解析（不虚假发 reloc）。
  - 数据段中的符号引用（如函数指针初始化 `.quad sym`）按需发对应数据 reloc；**若需 `ADR-0019` 4 类之外的数据 reloc 类型，须停下报告**（不得自行扩类型集）。
- **约束**：
  - **reloc/fixup 坑预防（M4 硬约束）**：① 尊重 `IsResolved`；② same-section 快速路径不可靠则退回真重定位（`ML-003e`：判断「是否需重定位」须比较「目标符号 section vs fixup section」，**不是** `isUndefined()`）；③ `rb0` 禁作基址/零；④ 跳转表目标标签显式发射；⑤ **大常量/大地址先材料化，不得折入受限立即数/relocation 字段**（`ML-030a`：`GlobalAddress + 大常量偏移` 不得塞进 `imms18`/`imms12`，须寄存器算术）。
  - **不做**：完整调用约定、varargs/聚合/sret、FP/RF、clang 前端（均 M5+）。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建/串行/临时目录/留证纪律同 `LLVM-050t`；`ninja -j8`；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-055t/`；**不提交 git**。

## 验收标准

1. 构建 EXIT=0。
2. **段发射**：对一个含 `@g = global i64 42` / `@arr = global [4 x i64]` / 只读常量的 `.ll`，`llc -march=dadao -filetype=obj` EXIT=0；`llvm-readobj -h --sections` 显示 `.data`/`.rodata` 节存在、8B 对齐、内容按大端（给真实输出）。
3. **地址材料化 + RELA**：对跨 section/外部符号的 `GlobalAddress` 引用，`llvm-readobj -r` 显示 **`R_DADAO_ABS48`**，`--expand-relocs` 显示 `Addend`；反汇编显示 `set.zw`/`or.w` 序列（≤3 片）；逐例独立核对地址分片（wyde-position）。
4. **同段就地解析**：同 section（如 `.text` 内函数地址）不虚假发 reloc（`llvm-readobj -r` 无多余项）。
5. **数据段符号引用**：`.quad sym`（函数指针/全局地址）非零且带对应 reloc（`ML-003e` Gap 2）；若该类型不在 `ADR-0019` 集内，**停并报告**。
6. **不回归**：`make test-codegen`（M3 15/15）EXIT=0；`make check-lit`/`make check` EXIT=0；`check-patch-tree` OK。
7. 一键证据脚本 `.work/evidence/LLVM-055t/run.sh`（含 `--inject`：把 `ABS48` 片数改为 1 / 让跨段符号不发 reloc → 期望 FAIL → 还原+**重建** → 回绿）；完成区贴真实输出。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
