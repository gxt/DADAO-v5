# LLVM-137t: i64 常量移位立即数选择

**模块**：llvm
**项目里程碑**：M10
**依赖**：LLVM-136t（干净基线）
**状态**：待开始

## 背景
当前 i64 的 `shl`/`lshr`/`ashr` 常量移位会先物化移位量、再走寄存器移位；ISA 已有 `shl.o`/`shr.uo`/`shr.so` 立即数形态（`immu6`）。PR（commit `3d77f7bb`）的 64 位常量化部分可作为输入，但必须在 136t 的干净基线上重放，不得夹带 code model/tailjmp 回退。

## 目标
1. 在 `DADAOISelDAGToDAG.cpp` 的常量移位选择中支持 `MVT::i64`，`0 <= shamt < 64` 时选 `shl_o_orri`/`shr_uo_orri`/`shr_so_orri`；`shamt == 0` 保持规范 copy 语义；变量移位保留寄存器形态。
2. 不改变 poison 语义；不为 `shamt >= 64` 构造立即数；不影响窄整数移位（137 只改 i64 分支）。
3. 新增/重放 lit：0、1、31、32、63、变量移位；补 `shamt >= 64` 负例（若 IR 合法可构造）与窄移位回归。
4. QEMU 运行期 oracle：用独立 Python 按 u64 截断/有符号右移派生期望，跑至少 0/1/31/32/63 + 变量；不仅看汇编。

## 验收
- 新增 lit 全绿；完整 `check-lit` 不回归（现场统计）。
- QEMU 运行期结果与独立 oracle 一致；变量移位/窄整数回归不变。
- `make check` rc=0；`check-patch-tree` rc=0；证据 `.work/evidence/<任务号>/run.sh`（注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/LLVM-137t/`。

## 约束
- 只改 i64 常量移位选择与对应测试/补丁；不碰 code model、tailjmp、窄 extension、指针 PHI。
- 不改 spec/contracts/ABI；不改 QEMU。
- **不提交、不 push**；重建申报；全量/夜跑未授权时不跑。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
