# LLVM-128t: 位操作后端（`ctlz`/`cttz`/`ctpop` + `rev`）

**模块**：llvm
**项目里程碑**：M9（后端指令利用）
**依赖**：`SPEC-164t`（已验证：`OPC-MISC` 迁 `op 0x47`，`ct*` 已并入）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 用户裁定（2026-10-22）
用户要求盘点「SimRISC 已支持、LLVM 未用」并落实；本轮实测确认 `ctlz`/`cttz`/`ctpop`/`rev.*` 七条**从未被 LLVM 发射**（`__builtin_clzll` → 10 条位运算；`__builtin_bswap64` → 7 条组合）。

### 真源
- `contracts/opcodes.yaml`：`ctpop`/`ctlz`/`cttz` 已于 `SPEC-164t` 迁入 **`OPC-MISC`（`op 0x47`）**，`ha = 0x25/0x26/0x27`；`rev.o/.t/.w/.b` 在 `op 0x40/0x41/0x42/0x43 ha 0x0C`；均 `orri`、`scope: m8`。
- `contracts/qemu` 侧已实现：`trans_bitcnt.c.inc.patch`（ctlz/cttz/ctpop）、`trans_rev.c.inc.patch`（rev）。

### 语义要点（**与实现强相关**）
- `ctlz`/`cttz` 的操作数范围 = `rdHC[hd:0]`，`hd` 为编码里的位宽参数；`rdHC[hd:0]` **全 0 ⇒ ctlz = cttz = hd + 1**（ISA 已定义，消除 UB）。
- `ctpop` = `rdHC[hd:0]` 内 1 的个数。
- `rev.b/.w/.t/.o` = 8/16/32/64 位整字位反转。

## 目标

1. `DADAOInstrInfo.td` 补 7 条 pattern：`CTLZ`/`CTTZ`/`CTPOP`（i64/i32/i16/i8 中实际需要的宽度）、`BSWAP`（i64/i32）、`BITREVERSE`（可选）。
2. **验收断言（各 1 条指令）**：`__builtin_clzll` → `ctlz`、`__builtin_ctzll` → `cttz`、`__builtin_popcountll` → `ctpop`、`__builtin_bswap64` → `rev.o`、`__builtin_bswap32` → `rev.t`。
3. `ctlz(0)`/`cttz(0)` 语义必须与 LLVM 的 **defined** 变体一致（64/32 等），不得用 `ctlz_zero_undef`/`cttz_zero_undef` 映射（避免把 ISA 的已定义值变成死角）。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOInstrInfo.td.patch,DADAOCodeGen.td.patch}`、`tests/llvm/lit/**`。
- **输出**：7 条 pattern + lit（≥5 条正例 + 1 条零值用例 + `dst` 约束反例）+ 证据脚本。
- **约束**：不改 `spec/`、`contracts/`（这些记录已存在且已实现）；不改 `scope`；不 commit/push。

## 设计要点

### A. 位宽参数 `hd` 的选择
`ctlz`/`cttz`/`ctpop` 都是 `orri` + `hd` 决定操作宽度。i64 用 `hd=63`、i32 用 `31`、i16 用 `15`、i8 用 `7`。LLVM 的 `CTLZ i64` 语义（0 → 64）与 `hd=63`（0 → 64）**一致**；其余宽度同理，须逐宽度现场核。

### B. 走 pattern 还是 Custom
优先 `.td` pattern（`Pat<(ctlz i64:$x), (ctlz_... $x, 63)>` 形态）。若 `orri` 的立即数字段在 TableGen 里无法直接约束，再退化到 `DADAOISelDAGToDAG.cpp` 的 Custom 匹配；**二选一，须在完成区写明实际路径**。

### C. 与既有 `rol` 的关系
`rev` 与 `rol` 无关，不共用 pattern；但两者都在 `orri`/`orrr` 的 MISC 表，注意 `check_tables` 只覆盖 4 张 MISC 子表这一已知缺口（`ISS-325`），**不得据此放宽断言**。

## 验收

1. 上述 5 条各 **1 条指令**（`llc -O2` 现场计数，贴真实输出）。
2. `ctlz(0)`/`cttz(0)` 用例：返回 64/32（与 ISA 定义一致），有 1 条 lit。
3. 反例：`dst` 约束（若适用）1 条；反汇编 round-trip 1 条。
4. 门控：`check-instrinfo`（0 errors）、`check-isa-coverage`、`check-scope`（excluded 31 / fp 60 不变）、`check_qemu_trans --strict`（264/264）、`check_lit_gen`、`check-lit`、`make check`(L1)、`make check-modules`(L2)。
5. **可达 FAIL ≥2**：① 删掉 `ctlz` pattern ⇒ 「1 条」断言红；② 把 `hd` 写成 31（对 i64）⇒ 零值用例红。
6. 重建：`make install-host` + `build-builtins` + `build-musl-shared`；证据 `.work/evidence/<任务ID>/run.sh`（rc 落盘、禁 `| tee`）。

## 完成区
（执行后填写，≤30 行：改动文件 / 实测指令计数 / 反例 / 门控 rc / 遗留）

## 审阅记录
