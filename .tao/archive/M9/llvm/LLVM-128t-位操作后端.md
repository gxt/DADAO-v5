# LLVM-128t: 位操作后端（`ctlz`/`cttz`/`ctpop` + `rev`）

**模块**：llvm
**项目里程碑**：M9（后端指令利用）
**依赖**：`SPEC-164t`（已验证：`OPC-MISC` 迁 `op 0x47`，`ct*` 已并入）
**状态**：已验证

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

**测试结果**：通过 39/39（`run.sh --gates`）；核心 27/27 + `--inject ctlz` 6/6 + `--inject hd` 6/6。
**实现路径**：**.td pattern 为主**（`ctlz`/`cttz`/`ctpop` 含 `*_zero_poison` 两态 → `hd=63`；`bswap` i64 → `rev.o k=8`；`bitreverse` i64 → `rev.o k=1`）。**唯 1 处 Custom**：`bswap i32`（i32 非合法类型，promote 会成 `srl(bswap i64),32` 两条）⇒ `ReplaceNodeResults` 发 `rev.t k=8` + TRUNCATE。另**必须**覆写 `isCheapToSpeculateCtlz/Cttz=true`：否则 CodeGenPrepare `despeculateCountZeros` 把 defined 变体包成 3 分支（实测 7 条）。
**实测指令计数**（`llc -O2`，install root；C `__builtin_*` 同）：`clzll→ctlz rd8, rd16, 63` 1 条；`ctzll→cttz` 1 条；`popcountll→ctpop` 1 条；`bswap64→rev.o rd8, rd16, 8` 1 条；`bswap32→rev.t rd8, rd16, 8` 1 条（无 `call`/`mul.uo`）。
**零值用例**：运行期（QEMU，oracle=ISA §6.4.4 `hd+1`）`ctlz(0)=64`、`cttz(0)=64`、i32 路径 `32/32`、`ctpop(0)=0` ⇒ guest exit 15；lit 侧 `bitops.ll` 的 `ctlz64_zero`/`cttz64_zero` 断言 `hd=63`。
**反例**：① `dst` 约束**不适用**——`ct*`/`rev` 的 `rdhb != rd0` 是**执行期 ILLI**（td 注释/`ISS-211`），MC 层无静态检查，实测 `ctlz rd0,…`/`rev.o rd0,…` 均 rc=0，故不新增（不假装有）。② 反汇编 round-trip：5 个发射形态 `llvm-mc -disassemble` 逐条回原文，且编码与 `contracts/opcodes.yaml` 派生字一致（`rev.o=0x40308408`、`rev.t=0x41308408`、`ctlz=0x4798843f`、`cttz=0x479c843f`、`ctpop=0x4794843f`）。
**可达 FAIL ≥2**：`--inject ctlz`（删两条 ctlz pattern→llc `Cannot select` rc=134）红；`--inject hd`（i64 `hd` 63→31）⇒ 断言 `63≠31`、FileCheck 红、**零值运行期 exit 0≠15** 红；两次均 cp+md5 还原（md5 `d6be60c2…`）后重建回绿。
**门控 rc**：`check-instrinfo` 0 errors（262 defs）、`check-scope` 0（实测 m1=156/fp=64/excluded=2/m3=1/m8=7/m9=34/264；**册子写的 excluded 31/fp 60 是 SPEC-164t 前口径**，本任务未改 scope）、`check_qemu_trans --strict` 0（264/264）、`check_lit_gen` 0（64/64）、`check-lit` 0（**132/132**）、`make check`(L1) 0、`make check-modules`(L2) 0、`check-patch-tree` 192 OK、`check-isa-coverage` PASS（矩阵 yes 126→131）；`install-host`/`build-builtins`/`build-musl-shared` 均 PASS；`diff_ir_lli`（L3 值级对拍/manifest 闭包）19/19、结构 79=19+60、0 unclassified。
**修改文件**：`components/llvm-project/patches/…/{DADAOCodeGen.td,DADAOISelLowering.cpp,DADAOISelLowering.h,DADAOInstrInfo.td}.patch`（4 份改；`series` 仍 90）、`components/llvm-project/changelog.md`、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（重生成）、`tests/llvm/lit/CodeGen/DADAO/{bitops.ll,bitops-narrow.ll}`（新增）、`tests/llvm/ir-lli/manifest.yaml`（删 `p0-cttz` 项 + 登记两个新 lit）、`.tao/knowledge/milestones.md`（流水行状态 → `待验收`，L1 `check-milestones-fresh` 要求）、`.work/evidence/LLVM-128t/{run.sh,builtins.c,e2e/*}`。
**覆盖变化（披露）**：**新增** `bitops.ll`（5 条验收 + 零值 hd 断言 + `bitreverse` + zero-poison 两态）、`bitops-narrow.ll`（i32/i16/i8 提升路径 9 例）；**删除** `p0-cttz.ll`（其前提「ISA 无位扫描/计数指令」已被 SPEC-143t 否定，内容整体由上述两文件取代）；**未修改任何既有 lit 用例**（`tests/llvm/ir-lli/manifest.yaml` 的登记随删除/新增同步）。
**遗留问题**：① 窄 i32/i16/i8 仍是「提升后复用 i64」（3–6 条），未做各宽度 `hd=31/15/7` 的 1 条形态（需 3 个 Custom 结果合法化，任务书标「成本低一并」但无验收用例，**已披露不做**）；② `rev.w`/`rev.b` 无对应 LLVM 节点（`bswap16` 走 `rev.o`+`shr`），仍 MC-only；③ 零值运行期用例落在证据目录（`tests/llvm/codegen` 需同步改 `validate_codegen_vectors.py` 的 host oracle，越本任务输入范围）；④ 长门控日志留 `.work/log/llvm/LLVM-128t-*.log`。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：4 份组件补丁（`DADAOCodeGen.td` / `DADAOISelLowering.{cpp,h}` / `DADAOInstrInfo.td` 注释）、2 个 lit、证据脚本、矩阵重生成。

**逐行结论**：pattern 与 SDT 形状一致（`ctlz`/`cttz`/`ctpop`/`bswap`/`bitreverse` 均一元、`GPRD` 约束 i64）；`rev.o k=8` = 整块 8 字节元素反转 = bswap64、`k=1` = 位反序（§6.4.3 表）；`bswap32` Custom 只取低 32 位块、高半 don't-care 成立（实测 `bswap i32 (trunc i64)` 仍 1 条）；`hd=63` 与「全 0 字段 ⇒ hd+1」自洽（0→64）；zero-poison 与 defined 同映射不改变可观察语义；窄类型提升式语义逐宽度手工核算（ctlz 减 64−N / cttz 或入 `1<<N` / ctpop 掩码），且 i32 零值运行期复验 32/32；相邻宽度（bswap16、bitreverse32、ctlz i128、常量折叠）实测不崩、结果正确；证据脚本每条断言均有可达 FAIL（两条注入已跑通），计数全部现场统计、无写死。

**finding 与处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| defined `ctlz`/`cttz` 被 CodeGenPrepare `despeculateCountZeros` 包成 3 分支（7 条，破坏「1 条」验收） | ✅已修 | 覆写 `isCheapToSpeculateCtlz/Cttz=true`（`DADAOISelLowering.h`） | `llc -O2` 前后：7 条 → `ctlz rd8, rd16, 63` 1 条；`bitops.ll` 绿 |
| `DADAOInstrInfo.td` 注释仍写「MC layer only … never reach CodeGen」（已失真） | ✅已修 | rev/ct 两段注释改为写明 CodeGen 映射与 `hd=63` 语义 | `check-instrinfo` 0 errors；`check-patch-tree` 192 OK |
| 证据脚本 `local a=$1 b=$2 c="$d-$b"` 在 `set -u` 下先展开后赋值 ⇒ unbound | ✅已修 | 拆成独立 `local` 行；注入周期改用子 shell 隔离计数 | `bash -n` rc=0；`run.sh --gates` 39/39 |
| `CHECK-NOT: ctlz` 误匹配 `.size ctlz64`（FileCheck 红） | ✅已修 | 收窄为 `CHECK-NOT: ctlz rd`（同理 cttz/ctpop） | FileCheck rc=0（default + 注入还原两轮） |
| 既有 `p0-cttz.ll` 前提「ISA 无位扫描/计数指令」已被 SPEC-143t 否定 | ✅已修（披露删除） | 删该文件，内容由 `bitops.ll`（i64+零值）与 `bitops-narrow.ll`（i32/i16/i8）取代 | lit 132/132；覆盖变化已写入完成区 |
| 任务书门控期望「excluded 31 / fp 60」与实际不符 | ❌不修（记录） | 未改 scope | 实测 `m1=156 fp=64 excluded=2 m3=1 m8=7 m9=34 total=264`（SPEC-164t 后口径），与 `MEMORY.md` 第 6 项一致 |
| 任务书「`dst` 约束反例 1 条」 | ❌不修（不适用） | 未加用例 | `ctlz rd0,…` / `rev.o rd0,…` 实测 rc=0：该规则是**执行期 ILLI**（td 注释/`ISS-211`），MC 层无静态检查 |

**判决**：finding 全部已修或已证不适用；状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-23，独立重跑）

**重跑记录（本人命令 + 真实 rc，install 根 = `.dadao/cross-toolchain/bin`）**
- 5 条各 1 条（自建 `rev-128t.c`/`rev-128t.ll`，非复用 engineer 文件）：`clang --target=dadao-unknown-elf -O2 -S` rc=0 与 `llc -march=dadao -O2` rc=0，逐函数各 1 条：`ctlz rd8, rd16, 63` / `cttz rd8, rd16, 63` / `ctpop rd8, rd16, 63` / `rev.o rd8, rd16, 8` / `rev.t …, 8`；全文件 `call=0`、`mul.uo=0`。
- 零值语义（独立判据）：`spec/SimRISC-04 §2.2.2`（行 265/276）「全 0 ⇒ ctlz=cttz=hd+1」⇒ hd=63 ⇒ 64；自建 QEMU 向量实跑 `rc=0 guest exit=7`（含 ctlz(0)=64、cttz(0)=64、ctpop(0)=0、ctlz(1)=63、cttz(1)=0、i32 32/32），产物汇编确含 `ctlz/cttz/ctpop …,63` 真指令。
- `isCheapToSpeculateCtlz/Cttz` 覆写**必要**（实证）：删两条覆写行（cp+md5）重建后 `llc -O2` 的 `my_ctlz` 由 3 条退化为 `set.zw+br.z+ctlz+ret` + 块分裂（CodeGenPrepare `despeculateCountZeros`）；源码侧默认 `TargetLowering.h:744 return false` 吻合。还原 md5 相等、重建回绿。
- 门控（本人重跑，逐条 rc 落盘）：`check-patch-tree` 0（192 OK）、`check-instrinfo` 0（0 errors/262 defs）、`check-isa-coverage` 0（yes 131）、`check-scope` 0（m1=156/fp=64/excluded=2/m3=1/m8=7/m9=34/264）、`check_qemu_trans --strict` 0（264/264）、`check_lit_gen` 0（64/64）、`check-lit` 0（132/132）、L1 `make check` 0、L2 `make check-modules` 0。
- 注入（均 cp+md5 还原，还原后 md5 与基线逐一相等、源码树/工作树回净）：① 删 2 条 `ctlz` pattern → `llc` rc=134 abort（bitops.ll 与自建 IR 双红）→ 还原重建回绿；② i64 `hd` 63→31 → 汇编 `ctlz rd8, rd16, 31` + 零值运行期 `rc=1 actual=0≠7` 红 → 还原重建 `exit=7` 绿；③ `bitops-narrow.ll` 断言：删除 CHECK 行**只会更宽松仍绿**（删除非红路径，字面口径不成立），改错 1 条断言（ctpop32 `63→62`）→ FileCheck rc=1 红 → 还原 rc=0 绿（该文件手写、无生成器）。
- 改动面：`git diff --stat 17b72904~1..3ff63a28` 13 文件，`spec/`、`contracts/` diff 为空；矩阵 yes 现场计数 126→131；`p0-cttz.ll` 全仓无活引用残留（仅 archive 历史）。

**覆盖替代判定（p0-cttz.ll → bitops{,-narrow}.ll）**：原 2 个函数 4 条断言（`cttz64`/`cttz64_zp` 各 `CHECK-NOT: call` + `CHECK: mul.uo`）逐条比对——两函数在 `bitops.ll` 均有正断言 `CHECK: cttz rd8, rd16, 63`（libcall 回归会抹掉 cttz 使正断言必红，no-libcall 性质**隐含保留**，且 run.sh 另有显式 `no mul.uo/call=0` 断言）；新增零值/hd/窄宽度覆盖 ⇒ **实质替代、覆盖增强，无静默降级**。

**finding（非阻断）**：① `components/llvm-project/changelog.md`「摘要（真值）」段写「`check-scope` excluded **31** / fp **60** 不变」，与本人实测及任务书自测（fp=64/excluded=2，check-scope 现场输出）**矛盾**（SPEC-164t/160t 前旧口径）；任务书完成区已披露，但 changelog 是入 git 记录，建议提交前改对该行数字。②「删 1 条断言⇒红」字面口径不成立（见注入③），已以改错断言验证可达 FAIL。

**判决**：**Accepted**（指令计数、零值语义含运行期、覆盖替代、9 项门控 rc=0、2+1 项注入红/还原绿、未改 spec/contracts 全部经本人重跑证实）；finding ① 提请 architect 提交前定夺。

