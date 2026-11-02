# QEMU-078t: scaleB C1 与 sc rd0

**模块**：qemu
**项目里程碑**：M11
**依赖**：`SPEC-181t`
**状态**：待验收

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

**测试结果**：`.work/evidence/QEMU-078t/run.sh` rc=0（checks=31 failures=0；行为 17/17：scaleB 新路径 + 极端 64 位指数 + `rdHC=rd0` + 12 条 `sc rd0` ILLI）。两次注入均可达 FAIL：恢复旧 `load_rf(a->hd)` ⇒ scaleB 2/2 FAIL；删除 sc 守卫 ⇒ 12 条 rd0 全 FAIL；`cp`+md5 还原后均回绿。回归 `atomics-lrsc` 125/125 PASS。增量重建 `make build-qemu JOBS=8` rc=0（约 1 min/次）。
**修改文件**：`components/qemu/patches/target/dadao/{helper.c,translate.c,insn_trans/trans_fp.c.inc}.patch`；`components/qemu/changelog.md`；本任务书；`.tao/knowledge/milestones.md`。组件源树（非 v5 跟踪）同三文件；证据 `.work/evidence/QEMU-078t/`（gitignored）。`insn.decode` 未改。
**验收结果**：`check-patch-tree` rc=0（5 comp/205 patches）；`check-source-state` rc=0（qemu OK HEAD=f98216a count=1 clean=True）；`check_qemu_trans --strict` 264/264、orphan 0；`validate_decodetree` PASS；`check-qemu-forms` rc=0；`insn.decode` 重生成逐字节相同。llvm-mc：新语法编出 `0x44544043/0x44744043`，objdump 反汇编为 `rd3`；旧语法 rc=1 拒绝（LLVM-142t）。
**新发现/坑**：① QEMU 只吃编码，新旧写法共享同一 `orrr` 位模式，无法也不应在 QEMU 侧区分；旧路径的证明是「rf3=10.0 诱饵仍在、rd3=2 生效 ⇒ 6.0 而非 1536.0」。② 任务书说“改 insn.decode 第三字段 bank”，但 decodetree 不表达 bank；bank 只在 `contracts/opcodes.yaml`，故重生成逐字节不变，改的是 trans/helper 的 `load_rd`。③ `fp_scaleb_exp` 对超 int 的 64 位指数按 IEEE 754 饱和，已用 `2^63-1`/`-2^63` 例验证。
**遗留问题**：① `tests/` 向量归 `TESTCASES-090t`（本任务按边界未动）；② 按任务要求未跑全量 L3；③ 旧语法拒绝由 LLVM-142t 承担，QEMU 侧无独立可测面。④ `make check` rc=2，唯一 FAIL=`check-isa-coverage`（`gen-orrr.s` 缺 `ftsclb/fosclb rf,rf,rd` 行 + `tools/llvm/llvm-isa-backend-matrix.*` patch 行号漂移）；属 LLVM-142t/TESTCASES-090t 范围，未重试、未越界修改；其余 L1 门控（patch-tree/source-state/qemu_trans/forms/interface/changelog/milestones）均 rc=0。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：逐行审 `trans_fp.c.inc`/`helper.c`/`translate.c` 改动与 3 份导出补丁；重跑证据脚本与 atomics 回归。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F-1 64 位指数超 int 时截断会错 | ✅已修 | `fp_scaleb_exp()` 饱和到 `INT_MAX/INT_MIN` | `ftsclb_exp_max/min` 2 例 PASS |
| F-2 `sc rd0` 必须在任何内存/状态操作前 ILLI | ✅已修 | `gen_sc` 首部静态 `gen_exception_illegal` | 删除守卫注入 ⇒ 12 条 FAIL；还原回绿 |
| F-3 scaleB 仍可能走旧 `rfHD` | ✅已修 | `is_sclb ? load_rd : load_rf` 分支 | 恢复旧路径注入 ⇒ scaleB 2/2 FAIL |
| F-4 `insn.decode` 未改是否漏同步 | ❌不修 | decodetree 无 bank 字段，重生成逐字节相同 | 生成器 diff rc=0；`validate_decodetree` PASS |
| F-5 `sc` 非 rd0 路径回归 | ✅已修 | 未改非 rd0 逻辑，仅加前置 ILLI | `atomics-lrsc` 125/125 PASS |
