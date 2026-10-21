# LLVM-122t: `clmul.o` 后端（MC 定义 / ISel / `llvm.dadao.clmul` / `__builtin_dadao_clmul`）

**模块**：llvm
**项目里程碑**：M9
**依赖**：`ADR-0035`（`Accepted`：编码/语义/`rd0` 规则）、`INFRA-099t`（门控互斥；门控一律串行）。**前置无 QEMU 依赖**：本册**不动** `scope`（仍 `excluded`），翻转归 `SPEC-155t`。
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 指令形态（`ADR-0035`，`Accepted`）

- `clmul.o {rdHA, rdHB}, rdHC, rdHD`（`rrrr`，`op 0x56`，`value 0x56000000`，`mask 0xFF000000`）。
- `rdHA` = 128 位结果**高 64**、`rdHB` = **低 64**；不分符号、仅 `.o`。
- **`rd0` 单侧合法**（`D6`）：低半 `clmul.o rd0, dst, a, b`；高半 `clmul.o dst, rd0, a, b`。双侧 `rd0` / 同一非 `rd0` 寄存器 ⇒ ILLI（`dst_dual_same`）。

### 现场事实（2026-10-21 核，执行前须复核）

- **双目的 `rrrr` 先例**（直接复用形态）：`DADAOInstrInfo.td` 的 `mul_uo_rd`（`(outs GPRD:$ra, GPRD:$rb)`、`(ins GPRD:$rc, GPRD:$rd)`、`Pattern = []`）；`DADAOCodeGen.td` 的 `MULHU_PSEUDO`（`mul.uo dst, rd0, a, b`）与 `UMUL_LOHI_PSEUDO`（双结果，`expandPostRAPseudo` 把 `(lo, hi)` 重排成指令的 `(high, low)`）。
- **为何必须伪指令**：纯 pattern 无法把某一路输出强制绑到 `rd0`（`rd0` 不是普通虚拟寄存器）。
- **LLVM 有通用 intrinsic** `llvm.clmul`（`llvm/include/llvm/IR/Intrinsics.td` 的 `int_clmul`，返回**低半**）。
- **无通用 CRC intrinsic**（本册不涉）。
- **目标私有 intrinsic 接法**：新建 `llvm/include/llvm/IR/IntrinsicsDADAO.td`（`let TargetPrefix = "dadao" in { … }`），在 `Intrinsics.td` **末尾** `include "llvm/IR/IntrinsicsDADAO.td"`（先例 `include "llvm/IR/IntrinsicsRISCV.td"`，`:3222`）。
- **clang builtin 接法**：现有 clang patch 面已有 `Targets/DADAO.{h,cpp}`、`CodeGen/Targets/DADAO.cpp` ⇒ 需新增 `clang/include/clang/Basic/BuiltinsDADAO.def` + `TargetBuiltins.h`/CMake 登记 + `DADAO.h::getTargetBuiltins()` + target builtin 发射（→ 私有 intrinsic）。
- **`excluded` 允许有 `.td`**：`tools/llvm/validate_instrinfo.py` 第 34 行「MC 层仍需的个别 `scope:excluded`，如 `fence`」⇒ 本册加 `.td` 不改 `scope` 是**合法状态**（`fence` 先例）。
- ⚠ **本册会打破的一个既有前提**：`tests/llvm/lit/MC/DADAO-gen/gen-excluded.s` 现有一条反例 `clmul.o {rd8, rd9}, rd10, rd11` 断言 `UNREC`（**理由是"无 `.td` ⇒ 助记符不可汇编"**）。`.td` 一落地该前提失效 ⇒ 该反例**必然**从"拒绝"变"汇编成功"，反例红。**必须同册处理**（见 §D）。

## ✅ 已裁定（2026-10-21，用户原话）

> 「`clmul.o` 的编译器可达路径」= **全给：通用 + 私有 + builtin（推荐）**

1. 通用 `llvm.clmul`（低半）→ `clmul.o`；
2. 私有 `llvm.dadao.clmul`（**高/低两半**）→ 单条 `clmul.o`；
3. `__builtin_dadao_clmul(a, b)` → `unsigned __int128`（`(hi << 64) | lo`）→ 单条 `clmul.o`。
**本册不改 `scope`**（用户选定 4 册拆分，翻转归 `SPEC-155t`）。

## 目标

1. 三条路径都**只生成 1 条 `clmul.o`**（允许必要 `mov`；`FileCheck` 断言计数）；
2. MC 层编解码正确（与 `contracts/opcodes.yaml` 的 `0x56` 一致，round-trip）；
3. 不回归 `__int128` 乘法/除法路径（`mul.uo`/`UMUL_LOHI_PSEUDO` 既有用例）；
4. `scope` 保持 `excluded`（`opcodes.yaml` 逐字节不变）。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/**`（`DADAOInstrInfo.td`、`DADAOCodeGen.td`、`DADAOISelLowering.cpp`、`Intrinsics.td`、新 `IntrinsicsDADAO.td`）、`components/llvm-project/patches/clang/**`、`tests/llvm/lit/**`、`tools/testcases/generate_lit_vectors.py`。
- **输出**：
  1. `clmul_o_rd : DADAORrrr<"clmul.o">`（双目的、`op = 0x56`、`Pattern = []`，镜像 `mul_uo_rd`）；
  2. 伪指令三条（低半 / 高半 / 双半；双半用于私有 intrinsic）+ `expandPostRAPseudo` 重排；
  3. `llvm.dadao.clmul` + `clang` builtin；
  4. lit（三条正例 + `rd0` 反例 + MC round-trip）+ `gen-excluded.s` 前提修正；
  5. 证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`、`contracts/`、`tests/vectors/`、门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 指令定义与伪指令

- 定义照 `mul_uo_rd`（两路 out、两路 in、`Pattern = []`）。
- 低半：`(set GPRD:$dst, (clmul $a, $b))` → `clmul.o rd0, $dst, $a, $b`。
- 高半：`(set GPRD:$hi, (int_dadao_clmulhi $a, $b))` → `clmul.o $hi, rd0, $a, $b`。
- 双半：`(outs $lo, $hi)` → 单条 `clmul.o $hi, $lo, $a, $b`，`expandPostRAPseudo` 按指令 `(high, low)` 排（镜像 `UMUL_LOHI_PSEUDO`）。

### B. `llvm.dadao.clmul` 返回形态（二选一，完成区写明理由）

- **甲**：返回 `{i64 lo, i64 hi}` ⇒ 多结果，pattern 直接匹配；builtin 侧再拼 `i128`（须验证拼接指令被折叠或满足"1 条"判据）。
- **乙**：返回 `i128` ⇒ builtin 直接可用；需处理类型合法化拆分（成本高）。
- **判据**：`llc` 输出中 `clmul.o` **恰好 1 条**，且 builtin 路径无多余 `shl/or`；达标者取简单方案。

### C. clang builtin

- `BuiltinsDADAO.def`：`__builtin_dadao_clmul(unsigned long long, unsigned long long) -> unsigned __int128`。
- `TargetBuiltins.h` + CMake 登记；`DADAO.h::getTargetBuiltins()` 指向生成表。
- 发射走 `CodeGen/Targets/DADAO.cpp`；参数类型不匹配 ⇒ 正常 clang 诊断（**不得**静默截断）。

### D. `gen-excluded.s` 前提修正（**必须，否则 lit 红**）

- 现状反例断言的是「**无 `.td` ⇒ UNREC**」。`.td` 落地后必须：把**已有 `.td` def 的 excluded 记录**从 UNREC 反例集里排除（判据用 `.td` 是否存在，而非手写名单），并保留**合法性**反例（`rd0` 双侧 / 同寄存器）作为真正的负例。
- 该逻辑应在 `generate_lit_vectors.py` 里可机械判（生成时检测 `.td` def），避免下次同类问题。

### E. 回归面

- `__int128` 乘法（`aha-mont64` 类）、`mulhu`、`udivmodti4` 路径不变。
- 生成侧**不得**产出双侧 `rd0` / 同寄存器；汇编器对 `clmul.o r1, r1, a, b`、`clmul.o rd0, rd0, a, b` 须拒绝（与 `dst_dual_same` 一致）。

## 验收标准

1. `llc`（`-O2`）三条路径各 **1 条** `clmul.o`（FileCheck + 真实输出）。
2. `llvm-mc` 编码 == `0x56xxxxxx`；round-trip 绿。
3. 反例：同寄存器 / 双侧 `rd0` ⇒ 汇编失败，有真实输出。
4. `check-instrinfo` **0 errors**（excluded 允许有 `.td`，不得报 orphan）；`check-scope` 计数不变（`excluded` 仍 28）。
5. `check_qemu_trans --strict` **仍 259/260**（`ISS-317` 既有 known-red，本册不改变它）。
6. `check_lit_gen` / `check-lit` / `check-lit-full` 绿（含 §D 修正后的 `gen-excluded.s`）。
7. **改 `.td` 后必须 `make install-host`**，随后 `make build-builtins` + `make build-musl-shared`（否则新鲜度门控红，`ISS-210` 同类）。
8. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
9. **可达 FAIL ≥ 2**（注入 → 红 → `cp`+md5 还原 → 绿）：(a) 高低半绑反 ⇒ FileCheck 红；(b) 删 `expandPostRAPseudo` 重排（或删伪指令）⇒ 结果错/`Cannot select` 红。
10. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（`mul_uo_rd`/伪指令先例、`Intrinsics.td` include 位置、clang patch 面、`gen-excluded.s` 生成逻辑）。
2. MC 定义 + 编码 round-trip（先让 `clmul.o` 能编码）。
3. ISel：低半 → 高半 → 双半，各加 FileCheck。
4. `llvm.dadao.clmul` + clang builtin + 类型诊断用例。
5. §D 的前提修正（排除"已有 `.td`"的记录）。
6. `install-host` + builtins/musl 重装 + L1/L2 + 反例注入 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 高低半绑反（临时改伪指令展开顺序）⇒ FileCheck 红；还原 ⇒ 绿。
- 删掉 `expandPostRAPseudo` 的重排 ⇒ 结果错/选不出；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不改 `scope`（`SPEC-155t`）；不做 `clmulr`/`clmulh` 独立指令（`D4`）。
- 不做常量折叠优化（如 `clmul(x,1) → x`），不作为验收前提。
- 不做向量化（无向量 ISA）；不加 CRC intrinsic。
- `check_qemu_trans` 的 259/260 由 `QEMU-068t` 收口。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
