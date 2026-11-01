# LLVM-142t: scaleB C1 与 sc rd0 合法性

**模块**：llvm
**项目里程碑**：M11
**依赖**：`SPEC-181t`（待验收）
**状态**：待开始

## 用户授权

用户 2026-11-01 裁决：`ftsclb`/`fosclb` 第三源 `rf → rd`（同 `orrr` 编码，C1）；`sc rdHB=rd0 ⇒ ILLI`；授权分别建 LLVM/QEMU 任务。

## 目标

1. **scaleB C1**
   - `ftsclb`/`fosclb` 第三操作数从 `rfHD` 改为 `rdHD`；编码/opc/ha 不变。
   - MC/AsmParser/InstPrinter：语法 `ftsclb rfHB, rfHC, rdHD`；旧 `rf,rf,rf` 拒绝。
   - CodeGen：`DADAOScalb`/`ISD::FLDEXP` 的指数走 RD（有符号 64 位），不再 `f64/f32` 转 int。
   - 指令属性/寄存器类/编码验证与 SPEC-181t 一致。
2. **sc rd0**
   - 汇编期对 `sc rdHB, rdHC, [rbHD]` 且 `rdHB=rd0` 硬报错（Error 级，非 warning），与 spec ILLI 口径一致；
   - 编码/反汇编路径不静默成功；不改变 sc 编码。
3. 不修改 `tests/**`/`spec/**`/`contracts/**`/`components/qemu/**`/`components/gem5/**`；测试另立任务。

## 文件范围

- `components/llvm-project/**`（TD、MC、AsmParser、CodeGen、changelog、series）
- 本任务书、`milestones.md`

## 验收

1. `make install-host` 后：新旧语法汇编检查、反汇编/编码检查。
2. `check-instrinfo`、`check-scope`、`check-isa-coverage`（依赖 SPEC 分支）真实 rc=0。
3. `make check-lit`（或 targeted lit）真实 rc=0；旧 `rf` 写法必须失败。
4. 不修改测试资产；证据 `.work/evidence/<任务ID>/`；完成区 ≤30 行，状态 `待验收`。
5. 失败保留现场；不猜 spec；不复制 QEMU/gem5 实现。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
