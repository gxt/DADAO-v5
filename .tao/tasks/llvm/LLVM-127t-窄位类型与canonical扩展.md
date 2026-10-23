# LLVM-127t: 窄位类型合法化与 canonical 扩展（`i8`/`i16`/`i32` 全做）

**模块**：llvm
**项目里程碑**：M9（后端指令利用）
**依赖**：`LLVM-128t`（已验证）、`SPEC-164t`（编码已定）、`INFRA-102t`（门控已去常量）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 用户裁定
- 2026-10-22：「**窄位指令当然要用，不然定义它做什么**」+「**全做**」（`i8`/`i16`/`i32` 三档）⇒ 推翻 2026-10-10「只登记不改」（`ISS-187`）。
- `ISS-187` 补充（`LLVM-128t` 实测）：`ctlz/cttz/ctpop` 的窄位仍"提升后复用 i64"（3–6 条），本册一并评估是否做 `hd=31/15/7`。
- 同根因面：`ISS-310`（`int` 实参未按 `contract-abi §4.2` 符号扩展，现生成 `set.zw`+`or.w` 零扩展）。

### 真源（`contracts/opcodes.yaml`，实测 24 条窄位算术，全 `orrr`、`scope: m1`）
- 32 位 `op=0x41`：`add/sub/mul/div/rem.ut`（无符号）/ `.st`（有符号）
- 16 位 `op=0x42`：`.uw` / `.sw`
- 8 位 `op=0x43`：`.ub` / `.sb`
- 另有窄位比较 6 条（`cmp.sb/.sw/.st/.ub/.uw/.ut`）与窄位移 9 条（`shl.b/.t/.w`、`shr.{s,u}{b,w,t}`）

### 现场事实（2026-10-22 实测，`clang -O2`）
- `int32 a+b` → `add.uo` + `ext.so`；`int32 a*b` → `mul.uo`；`uint32 a/b` → `div.uo`；`int16/int8 a+b` → `add.uo`。
- `uint32 → uint64` 零扩展 → `set.zw` + `or.w`（未用 `ext.uo`）。
- 根因：`DADAOISelLowering.cpp` 只把 `MVT::i64` 设 legal ⇒ `i8/i16/i32` 全 promote。

## 目标

1. `i8/i16/i32` 设 legal（`addRegisterClass`），对**有窄位指令的**操作把 action 改 `Legal`：`ADD/SUB/MUL/SDIV/UDIV/SREM/UREM`、`SHL/SRL/SRA`、`SETCC`（窄比较）。
2. `.td` 补三档 pattern（有/无符号各一条），覆盖 24 条算术 + 6 条比较 + 9 条位移中所需的组合。
3. **canonical 扩展**：窄位结果落回 64 位寄存器时按类型正确扩展（`contract-abi §4.2`）；并入 `ISS-310`（`int` 实参按符号扩展，零扩展场景改用 `ext.uo`）。
4. 不改 `spec/`、`contracts/`、`scope`。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOISelLowering.cpp.patch,DADAOISelLowering.h.patch,DADAOInstrInfo.td.patch,DADAOCodeGen.td.patch}`、`tests/llvm/lit/**`。
- **输出**：legal 类型 + pattern + lowering 扩展逻辑；lit（每宽度正例 + `ISS-310` 复现用例 + 反例）；证据脚本。
- **约束**：不 commit/push；临时目录 `/tmp/opencode/LLVM-127t/`。

## 设计要点

### A. 只对**有指令支撑**的组合设 Legal
`AND/OR/XOR` 无 8/16/32 位变体（ISA 只有 `.o`/`.w` 部分）⇒ 保持 Promote，**不要**盲目全设 Legal（否则选不出指令、退化更差）。逐个 opcode 现场核 `contracts/opcodes.yaml`。

### B. 扩展语义（**关键**）
窄位结果在 64 位寄存器里的高半部必须是"按源类型扩展后的 canonical 值"，否则后续 64 位运算会读脏。做法二选一（完成区写明）：① 选 `*_s*`/`*_u*` 编码本身即完成扩展（`add.st` 符号扩展 / `add.ut` 零扩展）；② 显式补 `ext.so`/`ext.uo`。**优先 ①**（一条顶两条）。

### C. 与调用约定/ABI 的交互
`ISS-310` 的修法依赖本册的 canonical 规则：参数入栈/入寄存器前按 `contract-abi §4.2` 扩展；返回值同理。二者必须一致，**同一提交内**保证。

## 验收

1. `llc -O2`：`int32 a+b` → `add.st`（或 `add.ut`，按符号性）**1 条**；`int16` → `add.sw`/`add.uw`；`int8` → `add.sb`/`add.ub`；`mul32` → `mul.ut`/`mul.st`（**单目的**，不再 128 位双目的 `mul.uo`）。
2. `ISS-310` 复现：`int f(int x){ ext(x,-1,5); return x; }` ⇒ 参数按 `§4.2` 符号扩展（不再 `set.zw`+`or.w` 零扩展）。
3. 窄位比较/位移各 1 条正例。
4. 门控：`check-instrinfo`、`check-scope`（excluded 31 / fp 60 不变）、`check_qemu_trans --strict` 264/264、`check-isa-coverage`、`check_lit_gen`、`check-lit`、L1、L2。
5. **可达 FAIL ≥2**：① 把 `i32` 改回 Promote ⇒ 窄位断言红；② 去掉符号扩展 ⇒ `ISS-310` 用例红。
6. 重建：`install-host` + `build-builtins` + `build-musl-shared`。
7. **回归**：libc-test 静态档 + embench 冒烟（i32 代码生成面全变，须有代表性证据；若 >2 个代表用例 2 h 内无法定位 ⇒ **保留 WIP 先报 architect**，不得放宽断言）。

## 完成区

**测试结果**：lit 135/135（原 132，+3）；L1 `make check` PASS；L2 `make check-modules` PASS（含 rnd 785+3102、minmax、picolibc 69/69）；libc-test 静态档 337 例：pass 331 / fail **0** / known-fail 1（ISS-251，既有）/ blocked 5（`flockfile-list` SIGTRAP + 4 个 OOM 用例 SIGBUS，与本册前基线同集）；embench 38/38（19 例 × O0/O2）；证据脚本 29/29；注入 41/41。
**修改文件**：`components/llvm-project/patches/{llvm/lib/Target/DADAO/{DADAOISelLowering.cpp,DADAOISelDAGToDAG.cpp,DADAOCodeGen.td,DADAORegisterInfo.td},clang/lib/CodeGen/Targets/DADAO.cpp}.patch`；`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`（生成物）；`tests/llvm/lit/CodeGen/DADAO/{narrow-int.ll,abi-narrow-extend.ll}`（新）、`{bitops.ll,bitops-narrow.ll,atomics-store.ll,atomics-cas-narrow-sext.ll,m6-not-neg.ll}`（期望随新码更新）；`tests/e2e/{narrow_int_e2e.c,narrow_int_e2e_abi.s}` + `tests/e2e/lit/narrow_int_e2e.test`（新）；`.work/evidence/LLVM-127t/run.sh`。**覆盖披露**：新增 lit 用例 3（132→135）、新增 C/asm E2E 探针 2 文件；删除 0；未静默删/放宽任何断言（仅 5 个既有用例按新指令序列更新期望，语义更强的 CHECK-NOT 保留）。
**注**：`.work/source/llvm-project` 保持 `base+1`（补丁链由 `apply_series` 自身本地提交；末次 patch 再生用 `git commit --amend --no-edit` 维持“单提交 == 补丁集”不变量，未在 DADAO-v5 仓库提交/推送）；`check-patch-tree`/`check-index-blobs` 均 PASS。
**验收结果**：`int32 a+b` → `add.st`×1（无 `add.uo`）；`int16`→`add.sw`、`int8`→`add.sb`；`mul32`→`mul.st`×1（无 `mul.uo`）；窄比较 `cmp.st`/`cmp.ut`，窄位移 `shl.t`/`shr.st`/`shr.ut`（常量走 1 条 orri）；`ext.uo` 首次启用（zext/trunc，1 条）；ISS-310：`ext.so rd16,rd16,31` 于 call 前、`-1` 用 `set.ow`，旧 `set.zw…0xffff`+`or.w` 消失（E2E 运行期 `ext_reg(-1)==-1` 通过）。门控逐条 rc=0：check-instrinfo / check-scope（m1 156, fp 64, excluded 2, total 264，均未变）/ check_qemu_trans 264/264 / check-isa-coverage / check_lit_gen 64 检查 / check-lit / L1 / L2。反例：① 去掉 i32 legal → `narrow-int.ll` 红；② 去掉调用点 SExt → `abi-narrow-extend.ll` 红；两者还原后回绿（md5 对账）。重建链：install-host + build-builtins + build-musl-shared 均 PASS。
**新发现/坑**：① **RegTypes 顺序致命**：`RegisterClass` 的 `RegTypes` 首项被 `legalclasstypes_begin` 当“自然类型”，把 i8 放首位使 inline-asm 的 `ConstraintVT==Other` 分支把函数指针截成 i8（musl `__libc_start_main` 的 `"+r"(stage2)` → 跳到 0x18）；必须 `[i64,i32,i16,i8]` 且显式 `let Size=64`（否则 spill 槽按首项 1 B）。② `SIGN_EXTEND_INREG` 的 action 按 *inner* 类型查（LegalizeDAG），对 i32 设 Expand 会连带废掉 i64←i32 的 `ext.so`（无符号窄比较规范化依赖它）。③ `SIGN_EXTEND_INREG ..,i1` 的窄结果形态（wcwidth 的 `(a>0)-(b>0)`）需单独 pattern。④ 窄无符号 `cmp.u*` 结果按宽度零扩展（-1→0xFFFFFFFF），`cs.n/br.n` 前必须补 `ext.so` 规范化。⑤ `immu6` 操作数是 i64 而移位量是 i64 指针型 → 常量移位只能在 custom selector 折 orri。⑥ 工具坑：`apply_series.py` 对 `patchless=true` 的 chipyard 缺 `patch_dir` 抛 KeyError（既有，未修）；新增 `.work/log/**.EXIT` 会被 `check-run-artifacts` 判非法名，须用 `-exit.txt`。
**遗留问题**：① `ISS-187` 剩余（`rev.w/rev.b` 无 LLVM 节点、`bswap16` 已用 `rev.w`；窄 rotate 仍 Expand）；② 窄 `UDIV/UREM by 常量` 仍走 i64 magic（正确但非最优）；③ `ISS-310` 的 issue 状态收口、`ISS-187` 余项登记留给主会话；`check-testcases-suites` 的 path B 已撤回（driver 自述），本册回归改用 `run_libc_test_user_suite.py --link-mode static`；④ 5 个 libc-test blocked 为既有环境项（qemu-user SIGBUS/TRAP），未放宽判定。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查了 4 个 backend 文件 + clang ABI 分类 + 5 个改动的 lit 用例；用真实运行期证据交叉验证（L2 探针、libc-test、embench、E2E qemu）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `RegTypes` 首项=i8 使 inline-asm RegVT=i8（musl 启动崩溃） | ✅已修 | `DADAORegisterInfo.td` 改 `[i64,i32,i16,i8]` + 注释说明；`run.sh` 还原改 `cp`（非 `-p`，防 ninja 跳过重建） | `nowrite`/`hello` 经 qemu-dadao 运行 rc=0/7；rnd O0 785/785；L2 PASS |
| F2 窄无符号 cmp 结果零扩展致 `cs.n` 失效（fp_unordered E2E 红） | ✅已修 | `LowerBR_CC`/`LowerCmpSelect` 对 Unsigned 窄比较补 `SIGN_EXTEND_INREG`（`ext.so`） | `fp_unordered_e2e` PASS；`cmp_ult` 断言 + 运行期无符号比较 8 例 |
| F3 `SIGN_EXTEND_INREG` 按 inner type 取 action，i32 设 Expand 连带废 i64 形态 | ✅已修 | 构造函数不再设 Expand；补 `(i32/i16 (sext_inreg .., i8/i16))` pattern | `zext64/sext64/cmp_ult` 输出 `ext.so/ext.uo` |
| F4 `sext_inreg .., i1` 窄结果不可选（picolibc wcwidth `Cannot select`） | ✅已修 | `DADAOCodeGen.td` 补 3 条 `i1` inner pattern（`ext.so hd=0`） | `wcwidth.c` 编译通过；picolibc 69/69 |
| F5 常量移位无法用 TableGen 立即数叶（DAG 移位量 i64 vs immu6 i64 但叶类型不同） | ✅已修 | `DADAOISelDAGToDAG::Select` 加窄常量移位折叠（限于 `Sh < W`，防 ILLI） | `shlc32`/`srac32` 各 1 条 orri |
| F6 窄负数/`0-x` 走常量 0 物化（2 条） | ✅已修 | selector 用 `rd0` 折 `sub.s{b,w,t} dst, rd0, src` | `m6-not-neg.ll`（2 条：sub + 返回 ext.so，语义正确） |
| F7 证据脚本还原用 `cp -p` 致 ninja 跳过重建（注入后未回绿） | ✅已修 | `run.sh` 还原改普通 `cp` + md5 对账 | `--inject` 41/41（两次注入均 FAIL→还原回绿） |
| F8 兜底 | ⏸延后 | 窄 `udiv by const` 仍 i64 magic；`ISS-187` 的 `rev.w/rev.b` 节点——非本册验收项，登记遗留 | — |

**判决**：F1–F7 已修并复验，F8 属能力项（不阻断），任务可标 `待验收`。L1/L2/lit/E2E/回归全绿。

### 第 1 轮 reviewer 验收

**判决：Accepted**（判决仅基于本 reviewer 亲自重跑，未采信 engineer 输出）。审查前/后 `git status --porcelain -uall` 均为空行，`llc` md5 审前审后同为 `8d130d90…`，注入源文件 `md5sum -c` 全 OK。

**重跑记录（真实输出/退出码）**
- 三档（自编 `/tmp/opencode/LLVM-127t-review/t32.ll`，非 engineer 文件）：`add.st/add.sw/add.sb` 各 1；`mul.st`×1 且 `grep mul.uo`=0；div/rem 窄位实测 `div.ut`、`rem.sw`、`div.ub`、`rem.ub` 各 1 —— llc rc=0。
- canonical 扩展（自编 `abi.ll`，依 `contract-abi §4.2` 独立判据）：`signext i32` call → `ext.so rd16,rd16,31`、`zeroext i32` → `ext.uo …31`、`i16 signext` → `ext.so …15`、`i8 signext` → `ext.so …7`；`zext→ext.uo`、`sext→ext.so` 各成立；C 层 `addi signext + ret ext.so`／`addu zeroext + ret ext.uo`／short、char signext 一致。QEMU 运行期抽 5 式（`vi+48==-15`、`(unsigned short)vs==45536`、`(long)vs==-20000`、`vc*2==-200`、`vu/3u`）`REGRUN_EXIT=0`。
- ISS-310 复现式（自编）：IR 3 处实参 `signext`（含 `signext -1`）；asm `ext.so rd32,rd16,31` + `-1` 走 `set.ow`，旧 `set.zw 0xffff`+`or.w` 消失；运行期 `ext_reg(-1)==-1`（`rev.c` exit=0）。修复是 call 前**一条** `ext.so`（前端 `getExtend`），非"正确但更慢"绕行。
- 3 个自修 bug 抽 2（独立注入，非采信）：② 窄无符号 cmp 的 `SIGN_EXTEND_INREG` 删除 ⇒ `narrow-int.ll:172 CHECK-NEXT` 红 + 自编 `noinline` 无符号比较运行期 `exit=20`；还原 ⇒ 运行期 exit=0。③ 删 3 条 `sext_inreg …,i1` narrow pattern ⇒ picolibc `wcwidth` 经 llc 报 `LLVM ERROR: Cannot select: i32 = sign_extend_inreg … i1`（rc=141）；还原 ⇒ rc=0。① 未注入：源码确认 `RegTypes=[i64,i32,i16,i8]`+`let Size=64`，musl 启动经 libc-test 331 pass 佐证。
- 回归（自己跑）：libc-test 静态 337 = pass **331** / fail **0** / known-fail 1（ISS-251）/ blocked 5（flockfile-list + 4 OOM，与前基线同集）；embench **38/38**（json `counts pass=38 fail=0`）；lit **135/135**（50 CodeGen + 73 MC + 12 E2E，`make check-lit` rc=0 `Passed: 135`）。
- 门控：`check-instrinfo` rc=0（0 errors）；`check-scope` rc=0，现场计数 **m1=156, fp=64, excluded=2, total=264**（与要求一致）；`check_qemu_trans --strict` **264/264** rc=0；`check-isa-coverage` PASS（264 记录）；`check_lit_gen.py` **64 checks 0 failed**；`check-patch-tree` PASS（5 组件 192 补丁）；L1 `make check` rc=0；L2 `make check-modules` rc=0（lit 135、minmax 3102×2 PASS）。
- 注入（要求 2，实做 4，均 `cp` 备份 + `md5sum -c` 还原回绿）：i32 回 Promote ⇒ `narrow-int.ll` FAIL 1/1；去 call 点 `SExt` ⇒ `abi-narrow-extend.ll` FAIL（line 27/60 `expected string not found`）；另加 ②③ 两处如上。

**约束核验**：`git diff … -- spec/ contracts/` 为空（未改）✓；`check-patch-tree` 绿 ✓；临时产物全在 `/tmp/opencode/LLVM-127t-review/` 与 `.work/log/llvm/` ✓；engineer 未提交/推送（HEAD 仍 `f49d65b9`）✓；`run.sh` 审查：29 条断言均为 `want=got` 实值比较、两条注入有 `assert old in s` 锚点，可达 FAIL 路径成立 ✓。

**覆盖披露核验**：`--diff-filter=A` 新增 lit 3（`narrow-int.ll`、`abi-narrow-extend.ll`、`narrow_int_e2e.test`）+ E2E 探针 2（`narrow_int_e2e.c`、`narrow_int_e2e_abi.s`）属实；`D` 删除 **0**。修改 5 个既有 lit：`m6-not-neg`（+`CHECK-NEXT ext.so`）、`bitops-narrow`（hd 63→31/15/7 单条 +多条 `CHECK-NOT`）、`atomics-cas-narrow-sext`（+`CHECK-NOT set.ow/andn.w`）为**收紧**；`atomics-store`（`add.si`→`add.sb/sw/st` 寄存器形态、CHECK 顺序随新码）、`bitops.ll bswap32`（目的寄存器 `rd8`→通配，因 `ext.so/ext.uo` 占 rd8）为**随新码适配**——两者的缺陷触发断言与既有 `CHECK-NOT`（`rb2rd`/`rev.o`/`shr.uo`）均保留，未删断言、未放宽缺陷可达路径 ⇒ **不判放宽**。

**备注**：L1 首跑 rc=2，根因是我并行跑回归产生的 `.dadao/tests/*/…Z-*` 目录在 `check-run-artifacts` 扫描时缺 `run.json`（**审查者自身并发干扰**，非交付物缺陷），串行重跑 1 次 rc=0（已记录重试次数）；任务书验收第 4 条"excluded 31 / fp 60"与现场（2/64）不符属任务书陈旧数字，以 reviewer 指定口径（156/64/2/264）为准。
