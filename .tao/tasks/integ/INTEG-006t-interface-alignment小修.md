# INTEG-006t: check_interface_alignment 两处缺陷

**模块**：integ
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述（来自 `deferred.md`）

1. **第三处调用的 `isdir` 守卫不一致**（`INTEG-005t` reviewer N3/C1）：`check_opcodes_cross()` 内为 `if os.path.isdir(qemu_patches_dir): for pf in iter_patch_files(...)`，而前两处（`check_elf_fields()`/`check_adr_alignment()`）**无守卫**、直接调用。后果：若 `components/qemu/patches/` 不存在，第三处**不**触发空集硬错误，而静默产出「期望 256 trans_*，实际 0」的误导 FAIL。建议：删 `isdir` 判断，交由 `iter_patch_files()` 统一处理（三处一致）。
2. **`_is_comment()` 只识别全行注释**（`LLVM-014t` reviewer 第 3 轮）：`_is_comment()` 只识别 `//`/`/*`/`*`/`*/` 开头的**全行**注释；**行尾注释 / 块注释中间行**内的误导文本仍可先于真实 call 命中 ⇒ **假绿**。建议：改读**真实产物**（`llvm-mc` + `llvm-readobj` 解析 `Flags`），或至少收紧 token 匹配（要求独占行/真实 call 形态）。

## 约束

- 只做上述 2 项；不改其他检查逻辑
- 逐条核对，禁止正则批量替换；命令缺失 → 停下报告
- 完成后 `make check` EXIT=0；`check_interface_alignment` 80/80

## 验收标准

1. 三处 `iter_patch_files()` 调用一致（无 `isdir` 守卫差异）；目录缺失时**统一硬错误**
2. `_is_comment` 假绿消除（行尾/块注释内的误导文本不再致假绿）；**反例**（构造行尾注释内含 `setELFHeaderEFlags(` 但无真实 call）→ 检查 FAIL
3. `check_interface_alignment` 80/80 EXIT=0；`make check` EXIT=0
4. 反例验证（两处各自可达 FAIL）

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
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）