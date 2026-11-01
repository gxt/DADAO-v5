# QEMU-078t: scaleB C1 与 sc rd0

**模块**：qemu
**项目里程碑**：M11
**依赖**：`SPEC-181t`
**状态**：待开始

## 用户授权

用户 2026-11-01：scaleB C1 `ftsclb/fosclb` 第三源 `rfHD → rdHD`（同编码）；`sc rdHB=rd0 ⇒ ILLI`；授权 QEMU 独立任务。

## 目标

1. **scaleB C1**：
   - `insn.decode` 第三字段 bank 改为 `rdhd`；语法 `ftsclb rf,rf,rd`；
   - `trans_fp`/`helper_fp_arith` 的 scaleB 直接读 RD 指数（64 位有符号），不再 `floatXX_to_int32(rfHD)`；
   - 旧 `rf,rf,rf` 编码/汇编路径拒绝。
2. **sc rd0**：
   - `sc rdHB, rdHC, [rbHD]` 且 `rdHB=rd0` 静态 ILLI；
   - 不写内存、不置成功/失败状态；
   - 编码不变。
3. 不改 `tests/**`/`spec/**`/`contracts/**`/LLVM/gem5/Makefile；测试另任务。

## 文件范围

- `components/qemu/**`（补丁、series、changelog）
- 本任务书、`milestones.md`

## 验收

1. `make check-patch-tree`、`make check-source-state` rc=0。
2. 重新构建 QEMU 后：scaleB 新/旧语法、`sc rd0` ILLI 反例真实 rc；`check_qemu_trans` 相关项 rc=0。
3. 不跑全量 L3；证据 `.work/evidence/<任务ID>/`；完成区 ≤30 行，状态待验收。
4. 失败保留现场；不猜 spec；不复制 LLVM/gem5 实现。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
