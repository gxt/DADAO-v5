# LLVM-122t: `clmul.o` 后端（MC 定义 / ISel / `llvm.dadao.clmul` / `__builtin_dadao_clmul`）

**模块**：llvm
**项目里程碑**：M9
**依赖**：`ADR-0035`（`Accepted`：编码/语义/`rd0` 规则）、`INFRA-099t`（门控互斥；门控一律串行）。**前置无 QEMU 依赖**：本册**不动** `scope`（仍 `excluded`），翻转归 `SPEC-155t`。
**状态**：已验证

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

**测试结果**：通过 — `.work/evidence/LLVM-122t/run.sh` default **42/42 rc=0**；注入 `--inject half` / `--inject pair` 各 **7/7 rc=0**（注入→红→`cp`+md5 还原→重建→绿）
**修改文件**：
- 组件（**10 改 + 7 新增**，`series` 83→90、`check-patch-tree` 185→192）：`DADAOInstrInfo.td`、`DADAOCodeGen.td`、`DADAOInstrInfo.cpp`、`DADAOISelDAGToDAG.cpp`、`DADAOISelLowering.{h,cpp}`、`AsmParser/DADAOAsmParser.cpp`、`clang/lib/Basic/Targets/DADAO.{h,cpp}`、`clang/lib/CodeGen/Targets/DADAO.cpp`；新增 `clang/include/clang/Basic/BuiltinsDADAO.def`、`clang/include/clang/Basic/TargetBuiltins.h`（patch）、`clang/lib/CodeGen/{CGBuiltin.cpp,CodeGenFunction.h}`（patch）、`llvm/include/llvm/IR/{Intrinsics.td,IntrinsicsDADAO.td,CMakeLists.txt}`（patch）
- 生成物：`tests/llvm/lit/MC/DADAO-gen/{gen-rrrr.s,gen-excluded.s}`、`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`
- 工具：`tools/testcases/{generate_lit_vectors.py,check_lit_gen.py}`（判据改机械）、`tools/llvm/validate_instrinfo.py`（allow-list 1 条）
- 用例：`tests/llvm/lit/CodeGen/DADAO/clmul.ll`、`tests/llvm/lit/MC/DADAO/clmul-legality.s`、`tests/e2e/lit/clmul_builtin.test` + `tests/e2e/clmul_builtin.c`
- 台账：`components/llvm-project/changelog.md`（1 条）
**验收结果**：三条路径 `llc -O2` 各 **1** 条（`{rd0, rd8}` / `{rd8, rd0}` / 双半；`mul.uo` 0 条）；builtin `clang -O2 -S` 1 条 `{rd8, rd9}, rd16, rd17`、无 shl/or；MC 三形态 `0x56xxxxxx` + `--disassemble` 回原文；`{rd7,rd7}`/`{rd0,rd0}` rc=1 指名 `dst_dual_same`；`check-instrinfo` 0 errors；`check-scope` excluded **28**（总 260 不变）；`check_qemu_trans --strict` 260/260；`check_lit_gen` 64/64；lit（MC+CodeGen+E2E）130/130；`check-lit-full` 12/12；L1/L2 rc=0；`install-host`+`build-builtins`+`build-musl-shared` PASS
**新发现/坑**：① `Intrinsics.td` 的 include **不足**以给出 `Intrinsic::dadao_*` —— 须在 `llvm/include/llvm/IR/CMakeLists.txt` 加 `-intrinsic-prefix=dadao` 的 `IntrinsicsDADAO.h`（否则 `IntrinsicImpl.inc` 有名字、枚举缺失，3 个 .cpp 报 “not a member of llvm::Intrinsic”）；② `ISD::CLMUL` 在 `TargetLoweringBase` **默认 `Expand`**（一条摊成 14 条 `mul.uo`+and/or），只加 pattern 不设 `Legal` 是“静默变慢”而非报错；③ 大端 i128 返回部件序为 `rd8=高、rd9=低`（非“先低后高”），半绑定须用「单 i64 返回落 rd8」独立观测，不能凭直觉断言；④ 两结果 target intrinsic 是 `INTRINSIC_WO_CHAIN`（结果列表），TableGen pattern 绑不上 ⇒ 手工 `Select`；⑤ `.td` 一落地「无 def ⇒ UNREC」前提失效，`gen-excluded` 判据必须机械化为「有 `.td` def ⇒ 汇编器受理」
**遗留问题**：无（`scope` 仍 `excluded` 按派单，翻转归 `SPEC-155t`；向量/运行期语义归 `TESTCASES-057t`/`QEMU-068t`）

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-22）

**范围**：组件 10 改 + 7 新增、2 个生成器判据改动、1 个 allow-list、3 个 lit + 1 个 e2e + 1 个 .c、生成物重生成、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `Intrinsic::dadao_*` 不可见（缺 `-intrinsic-prefix` 枚举头；构建红） | ✅已修 | `llvm/IR/CMakeLists.txt` 加 `IntrinsicsDADAO.h`；3 个 .cpp 改 include 该头 | 构建 PASS；lit 130/130 |
| F2 `ISD::CLMUL` 默认 `Expand`（`clmul_lo` 出 14 条 `mul.uo`，语义对但违“1 条”） | ✅已修 | `setOperationAction(ISD::CLMUL, MVT::i64, Legal)` | `llc-llvm-clmul-1-insn`=1、`llc-generic-no-mul-expansion`=0 |
| F3 首版把双半/i128 的 `{rd9, rd8}` 当期望（凭“先低后高”直觉，实为大端 `rd8=高`） | ✅已修 | 测试与证据改为经 `rd8` 的 `*_lo`/`*_hi` 探针观测半绑定 | `llc-pair-lo-in-rdhb`/`llc-pair-hi-in-rdha`/`llc-wide-lo-in-rdhb`/`llc-wide-pair-order` 全 PASS |
| F4 注入② marker 不唯一（`UMUL_LOHI`/`SMUL_LOHI` 同形文本） | ✅已修 | 锚点扩到 `BuildMI(… clmul_o_rd)` 三行 | `--inject pair` 7/7 rc=0 |
| F5 证据脚本 `chk` 语义误用（“期望非零”的检查传了 rc=1） | ✅已修 | 3 处改 `chk NAME 1 $rc 0` | default 42/42 rc=0 |
| F6 builtin 类型诊断用例用 `double`（隐式转换合法，不报错 ⇒ 断言空转） | ✅已修(用例) | e2e 改用不可转换的 `struct S` | `clang-builtin-type-diag` expected=1 actual=1 rc=1 |
| F7 注入“文件是否真变”只靠 md5 事后比对 | ✅加固 | 注入后先比 md5 证“已变”，还原后再比 md5 | `inject-changed-file`/`restore-md5-equal` 均 PASS |

**判决**：已发现的 7 条 finding 全部修复或加固，无未修项；`scope` / `spec/` / `contracts/` 未动 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-22）

**判决：Accepted**（HEAD=`80c732c6`，工作树 `git status --porcelain -uall` 全程为空）

**重跑记录（reviewer 自跑，非采信完成区）**
- 三条路径自写最小用例：`llc -O2 -march=dadao` → p1 `clmul.o {rd0, rd8}`、p2 `{rd9, rd8}`、p3(builtin) `{rd8, rd9}`；逐文件现场计数 `clmul.o=1 mul.uo=0 shl/or/=0`（三文件均 `rc=0` 通过比对）。
- QEMU 实跑（自建 freestanding 管线 + 独立 GF(2) oracle，非采信）：`llvm.dadao.clmul` **54/54 pass**、`__builtin_dadao_clmul` i128 **42/42 pass**；含 `clmul(a,1)==a`、`(1<<63)*2 ⇒ hi=1 lo=0`、随机、全1*全1 ⇒ **rd8=高/rd9=低**闭环。
- `rd0` 规则：`{rd0,rd9}`/`{rd8,rd0}`/`{rd0,rd63}`/`{rd63,rd0}` **rc=0** 且编码 `0x56xxxxxx`；`{rd7,rc7}`→`{rd7,rd7}`、`{rd0,rd0}` **rc=1**，stderr 指名 `dst_dual_same`（原文两条）。
- 门控：`check-instrinfo` rc=0 `=== Result: 0 errors ===`；`check-scope` rc=0 `excluded 28` / `total 260`；`check_qemu_trans --strict` rc=0 `260/260`；`check_lit_gen` rc=0 `64 passed, 0 failed`；`make check` rc=0、`make check-modules` rc=0（6m49s）、`make check-lit-full` rc=0 `12/12`、`make check-patch-tree` rc=0 `192 patches OK`。
- 新鲜度：`check-musl-freshness`/`check-builtins-freshness` **PASS**。
- 证据脚本：`.work/evidence/LLVM-122t/run.sh` **default 42/42 rc=0**（7m36s）、`--inject pair` **7/7 rc=0**。

**约束核验**：`spec/**`、`contracts/**`、`tests/vectors/**` 零 diff；`opcodes.yaml` md5=`dbfe9829…` == HEAD；`scope` 仍 `excluded`；未 commit/push；注入全程 `cp`+md5（禁 git checkout/restore/stash），无 `| tee`。

**独立注入（reviewer 自做）**：改 `.work/source/…/DADAOInstrInfo.cpp` 的 `CLMUL_LOHI_PSEUDO` `{hi,lo}` 交换（md5 `6c9270c1…`→`a12b0fb9…`）→ `ninja llc` → 形状 `{rd9,rd8}`→`{rd8,rd9}` 红、QEMU **hi.byte0=0(want1)/lo.byte0=1(want0) RED** → `cp` 还原 md5 相等 → 重建 → 形状绿、QEMU **hi=1/lo=0 GREEN**；终态 build llc md5 == 安装根 llc md5 `f5b018eb…`。

**gen-excluded 机械判（临时树注入，未碰仓库）**：判据为正则读 `.td` 补丁 def（非手写名单）；基线生成 `diff` 仓库 `gen-excluded.s` rc=0；删 `clmul_o_rd` def 块后反例集**多出** `clmul.o {rd8,rd9}, rd10, rd11` 的 UNREC 行、正例 `rrrr=17→16`（注入前后 md5 已记）。仓库快照 md5 前后一致、`git status` 空。

**观察（非阻塞）**：① run.sh 的 `qemu-trans-all-covered` 期望串 `260/260` 硬编码，与同段注释「never hardcoded」措辞不符（实际值由被测脚本现场统计）；② 注入模式依赖 `.work/build/llvm` 存在且无前置检查（新克隆会红）；③ reviewer 单独跑 L2 会经 `check-modules → test-semihost → install-host`（Makefile:69）重写安装根工具链 mtime，致其后 `check-musl-freshness` 的 toolchain stamp 过期——首次 `run.sh` 因此 rc=1（`toolchain stamp == current clang/ld.lld: different`），`make build-musl-shared JOBS=8` 刷新后第 2 次 rc=0；系本册既有门控嵌套行为与本次验收动作的环境副作用，非交付物缺陷，重试 1 次（已留现场 `run_default.log`/`musl_fresh.log`）。

