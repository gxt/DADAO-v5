# LLVM-119t: 内联汇编 `"m"` 约束后端 ISel 崩溃（`ISS-197` / `ISS-222` ②）

**模块**：llvm
**项目里程碑**：M9
**依赖**：`LLVM-118t`（同改 `components/llvm-project/**` + 各自 `install-host`，**必须串行**：共享 `.work/build/llvm` 与安装根，并发写会互相写坏——`ISS-229`）、`LLVM-086t`（`"r"` 约束先例，已归档）、`INFRA-096t`（安装根新鲜度，`待验收`）
**状态**：待验收

> **编号（现场取号，2026-10-20）**：`llvm` 现存最大 = `LLVM-117t`（本批另占 `118`/`120`）⇒ 取 **`119`**（编写前 `grep -rn 'LLVM-119' .tao/` 零命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实

- **最小复现（`ISS-197` 原始现场 + `ISS-222` ② 再确认）**：
  ```c
  void f(void){int x;__asm__("" : "+m"(x));}
  ```
  `clang -c` ⇒ 驱动 **rc=1** + `fatal error: error in backend: Could not match memory address.  Inline asm failure!` + crash dump；`llc` ⇒ **rc=134**（SIGABRT / core）。崩溃点 = 上游 `SelectionDAGISel::SelectInlineAsmMemoryOperands` 的 `report_fatal_error`（构建树源码 `llvm/lib/CodeGen/SelectionDAG/SelectionDAGISel.cpp`，**具体行号由现场定位，勿照抄**）。
- **对照面（优雅失败）**：`"f"` 未映射 ⇒ frontend `invalid input constraint 'f' in asm`（rc=1），**无 core**。
- **既有已解锁项**：`"r"`/`"=r"`/`"+r"`/`"=&r"` 已由 `LLVM-086t` 映射到 `GPRD`（`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch:558-580`）；`"i"` 走泛型。
- **真实消费者（本册动机）**：musl 默认 `GETFUNCSYM` 用 `"+m"`（`ldso/dlstart.c` 的 `GETFUNCSYM(&dls2, __dls2, …)`）；当前 DADAO 端口以 arch 特化绕开——`components/musl/patches/arch/dadao/reloc.h.patch:85-95` 注释逐字记录了该崩溃与绕行理由。**本册不要求撤除该特化**（是否回退另议）。
- **口径依据**：用户 2026-10-12 裁定 C「**只解锁，不立约定**」（`LLVM-086t`，逐字见该册第 13-14 行）⇒ 本册**不新增** `"b"`/`"f"` 等字母、**不立** `spec/Toolchain-01` 约定；只处理内存操作数约束的**可用 / 显式不可用**。
- **`ISS-222` ①（`%0` 代入空串）不属本册**，归 `LLVM-118t`。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOISelLowering.*`、`DADAOISelDAGToDAG.cpp`、`DADAOAsmPrinter.*`、`DADAORegisterInfo.*` 等，按诊断结果）、`components/llvm-project/patches/series`、安装根工具链、`tests/llvm/lit/**`。
- **输出**：
  1. **诊断记录**：崩溃链（IR → SelectionDAG → `SelectInlineAsmMemoryOperands` → 哪一步无可匹配的 memory operand 形态）逐环给出 `file:line`（构建树源码 + 我方补丁位置）；
  2. **实现**：使 `"m"`/`"=m"`/`"+m"`/`"=&m"` 可用（正确寻址）**或**（仅在证实本 target 结构性不可行时）显式诊断；两条路都必须消除 core；
  3. lit 用例（`tests/llvm/lit/CodeGen/DADAO/**` 或 `MC/DADAO/**`，按实际层）+ 运行时探针（`.work/evidence/<任务ID>/`）+ 证据脚本 `run.sh` + 日志 `.work/log/llvm/LLVM-119t-*.log`。
- **约束**：**不改** `spec/` / `contracts/` / `.tao/contracts/**` / `tests/vectors/**`；**不改** musl 组件（`components/musl/**`）——若判断须回退 `reloc.h` 的 `GETFUNCSYM` 特化，**停下报告**；改 `components/llvm-project/**` 后 **必须** `make install-host` 再验证（长构建，按 `AGENTS.md` 申报）；不 commit/push。

## 验收标准

1. **无崩溃（硬判据）**：对下列全部形态，`clang -c` 与 `llc` 的 rc ∈ {0, 1}，**无 SIGABRT（134）、无 core**（测试时 `ulimit -c 0`，临时目录 `/tmp/opencode/LLVM-119t/`）：`"m"`、`"=m"`、`"+m"`、`"=&m"`；空 asm 与非空 asm；操作数为局部标量 / 结构体字段 / 数组元素 / 解引用指针。
2. **语义正确（若实现支持）**——独立 oracle（手算期望，不由编译器输出反推）：
   - `int x; __asm__("set.rd %0, 7" : "=m"(x));` ⇒ `x == 7`；
   - `"+m"` 读改写（如 `__asm__("add.si %0, %0, 5" : "+m"(x));`，`x` 初值 10 ⇒ 15）；
   - 结构体字段/数组元素：写字段后其余字段不被破坏（逐字节比对）；
   - 大端语义：写入 8 字节值后按大端读回（`llvm-objdump`/运行时 memcpy + 手算字节序）。
3. **真实消费面**：把 musl 默认 `GETFUNCSYM`（`"+m"` 形态）复制到**临时文件**（`/tmp/opencode/LLVM-119t/getfuncsym.c`）⇒ `clang -c` rc=0（不要求改 musl 仓）。
4. **失败面仍可达**：不能因为「都变成 rc=1」而掩盖问题——若某形态仍不支持，诊断须**指名约束与原因**（不是 `Could not match memory address` 的 fatal），且 lit/探针断言该诊断文本；不得静默降级、不得输出错码。
5. **可达 FAIL ≥ 2**（真实输出 + `cp`+md5 还原后回绿）：
   - (a) **修前现场**：`llc` rc=134 + 同一 fatal 文案（改前复现、改后消失）；
   - (b) **注入回退**：临时树回退补丁（或改坏 memory operand 匹配）⇒ 崩溃/探针红；
   - (c) **错误值注入**：把探针期望值改错（如 7→8、字段偏移错位）⇒ 探针 rc≠0。
6. **门控**：`make check`(L1) rc=0；`check-lit`（L2 子集）/ `check-instrinfo` / `check-patch-tree` / `check-lit-full`（若改 MC 表）各留 rc；`series` 与补丁数一致（`check-patch-tree` 断言）。
7. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` 的 `ISS-197`（及 `ISS-222` ② 注记）按实况回填。
8. **不跑** `git commit`/`push`；未 `install-host` 就跑门控属无效验证（须披露）。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-119t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）；core 关闭（`ulimit -c 0`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（接受「显式不支持」边界 / 改 musl 特化 / 改 `spec/`）时留问。
6. 复杂命令输出留 `.work/log/llvm/`；重建按 `AGENTS.md` 申报耗时、`JOBS=8`。
7. **`install-host` 前置**：改组件后先装再验，否则读旧安装根 = 假绿（`ISS-210`）。

## 完成区

**测试结果**：① lit `MC/DADAO`+`CodeGen/DADAO`（构建树工具 overlay）**110/110**、`check_lit_gen` **64/64**、`check-instrinfo` **0 errors**；② 运行期 12 探针 `guest exit 0`（`--inject` oracle/code 两处注入各「红→绿」）；③ `046t` 静态 `crc32 -O2` **1/1**、`047t` 10 例**两档 10/10 + 10/10**；④ L1 `make -k check` **唯一 FAIL = `check-musl-freshness`**（1 项：musl 记的 builtins digest `77b3384a…` ≠ 现值 `18aafe21…`，补救 `make build-musl-shared` 按派单禁跑），其余 268 条 PASS。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOISelDAGToDAG.cpp,DADAOAsmPrinter.h,DADAOAsmPrinter.cpp,DADAOISelLowering.h,DADAOISelLowering.cpp}.patch`（5 份改；`series` 仍 83、`check-patch-tree` **185** 不变）；`components/llvm-project/changelog.md`；`tests/llvm/lit/CodeGen/DADAO/inline-asm-m.ll`、`inline-asm-m-reject.ll`（新增）；`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（真源重派生，证据行号随补丁位移）；`.tao/knowledge/{issues.yaml,milestones.md}`；本册；`.work/evidence/LLVM-119t/**`（run.sh + 4 个源/IR + 修前日志，`.work/` 不入库）。
**验收结果**：① **无崩溃**（`ulimit -c 0`）：`m`/`=m`/`+m`/`=&m`/`rm`/`=rm`/`p` × {空/非空 asm} × {局部标量/结构体字段/数组元素（常量+变量下标）/解引用指针/全局} ⇒ `clang -c` `-O0`/`-O2` 与 `llc` `-O0`/`-O2`(+`-verify-machineinstrs`) 全 **rc=0**，`grep "Could not match memory address"` = 0；`llc` 最小复现改前 **rc=134**（`LLVM ERROR: Could not match memory address.` + stack dump）/ 改后 0。② **语义**（独立 oracle，探针按 C 手算期望）：`"=m"` 写 7 读回 7；`"+m"` 10→15；`"m"`+`"=m"` 拷贝 `0x1234+base`；`"rm"`/`"=rm"` 42/0x77；栈数组 `a[i]`（变量下标）值对且 8 字节写不破坏邻居；结构体 `s.b=0x2a` 且 `s.a/s.c` 不变；全局 `"m"` 读 `0x55`、`"=m"` 写 99；大端字节序 `0x0102030405060708` 逐字节 = `01..08`；`"=&m"` 0x3c。③ **真实消费面**：musl 默认 `GETFUNCSYM`（`"+m"(static_func_ptr)`）⇒ `clang -c` **0**、`llc` **0**。④ **失败面**：`"V"` ⇒ `clang`/`llc` **rc=1** + `unknown asm constraint 'V'`（改前为 `SelectionDAGBuilder` 断言 SIGABRT），lit `inline-asm-m-reject.ll` 钉死该文本。⑤ **可达 FAIL**：C2 = 安装根「修前」llc（md5 `16198938…` ≠ 当前构建树 `a00838b7…`）跑同一 `repro.ll` ⇒ rc=134 + fatal；`--inject` 2 处（oracle 15→16、asm 常量 5→6）⇒ guest rc=3 红，`cp`+md5 还原后回绿。⑥ **门控**（各自 rc）：`check-patch-tree` 0（**185**）、`check-instrinfo` 0、`check-index-blobs` 0、`check-source-state` 0、`check-no-residue` 0、`check-tasks` 0、`check-knowledge-refs` 0、`check-component-changelog` 0、`check-milestones-fresh` 0、`check-run-artifacts` 0、`check-syscall-abi` 0、`check_lit_gen` 0、`check_issues` 0；`make -k check`(L1) rc=2 仅 `check-musl-freshness`。⑦ 重建申报：`ninja clang llc` 3×（3m06s / 3m14s / 3m41s，`-j8`）+`make build-builtins`（4m / 3.5s / 4s，148 目标）。⑧ **未**跑 `install-host`/L2/L3；**未** commit/push；**未**改本册 `**状态**`。
**新发现/坑**：① **两条根因**（现场逐环）：`DADAODAGToDAGISel` 缺 `SelectInlineAsmMemoryOperand` 覆写（基类默认 `return true`，`SelectionDAGISel.h:118-127`）⇒ `SelectionDAGISel.cpp:2354` `report_fatal_error`；`DADAOAsmPrinter` 缺 `PrintAsmMemoryOperand` 覆写（`AsmPrinterInlineAsm.cpp:511` 默认 `return true`）⇒ `$0` 印空串。② **`p` 同为 Kind::Mem**：`C_Address` 也走同一钩子，只补 `m`/`o` 会把 `"p"` 留在 fatal 上，故一并支持（打印 `[rb, off]` 即 DADAO 唯一地址形态）。③ **`V` 是上游枚举缺口**：`getConstraintType` 归 C_Memory 但 `InlineAsm::ConstraintCode` 无 `V` ⇒ 断言；`Q/R/S/T` 走 C_Unknown 本就优雅报错，`V` 需 target 侧显式拒绝。④ **基址 bank**：基址若是数据 bank 值（常量地址、整数运算得的地址）必须 `COPY_TO_REGCLASS`→GPRB（RA 落 `rd2rb`），否则打印出 `[rdN, off]` 非法汇编；`isPointerBankValue` 已覆盖常见来源，故正常代码零额外指令。⑤ **`%N` 仍不可用于寄存器操作数**（`ISS-222` ①，归 `LLVM-118t`）⇒ 探针/lit 里寄存器一律写字面 `rdN`+clobber 或局部寄存器变量；`"p"`/`"m"` 能被 `%0` 正确打印正是本册新能力。⑥ **builtins 归档字节在 clang 换代间变化**（`dc10ddc0…`→`18aafe21…`；同 clang 连续两次重建稳定），但 154/154 builtins TU 按实际 flags 全量 `-S` 复核 **0 处内联汇编** ⇒ 与 `m`/`p` 改动无关；来源未查明，归 `ISS-301` 族（`INFRA-098t`）。⑦ 安装根旧 binary 是天然的「修前产物」（未 install-host 期间），`run.sh` C2 用它做 rc=134 对照，并在 md5 相同时显式 SKIP（不静默）。
**遗留问题**：① **`check-musl-freshness` 唯一 FAIL**：musl 构建树记的 builtins digest 仍为任务前归档 `77b3384a…`，现值 `18aafe21…`（改组件后 `check-builtins-freshness` 要求重建 builtins，两者互锁）；补救 = `make build-musl-shared JOBS=8`（派单**禁跑**，且 `LLVM-118t` 串行约束）⇒ 交 architect 在 `install-host` 后统一做。② **`make check-lit`（安装根）= 118/120**：新 2 例在「修前」安装根 llc 上按预期红（正是其可达 FAIL 证明）；`install-host` 后应 120/120。③ musl `arch/dadao/reloc.h` 的 `GETFUNCSYM` arch 特化**未回退**（本册范围外，是否回退另议）。④ 清掉 `.dadao/tests/llvm-ts-user/` 两处**既存空 run 目录**（各 0 文件，非本册产物；`check-run-artifacts` A2 由此转绿）——越界处置，如实披露。

## 审阅记录

#### 第 1 轮 engineer 自审
**范围**：5 份补丁（`DADAOISelDAGToDAG.cpp` / `DADAOAsmPrinter.{h,cpp}` / `DADAOISelLowering.{h,cpp}`）逐行；证据脚本 `run.sh` 逐段；2 份 lit、探针源、`issues.yaml`/`milestones.md`/changelog 改动。
**判决**：finding 全部处置（6 ✅已修 / 2 ⏸延后并给理由），无未修阻断项；实现已用构建树工具全量复验（lit 110/110 + 运行期探针 + 四项回归抽样）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 只补 `m`/`o`：`"p"` 同属 Kind::Mem（C_Address）仍走 fatal | ✅已修 | ISel 钩子增 `case InlineAsm::ConstraintCode::p` | `llc` 手写 `"p"` IR rc=0，打印 `ld.o rd5, [rb16, 0]`；lit `ptr_constraint` |
| F2 `"V"` 改前是 `SelectionDAGBuilder` 断言（SIGABRT）而非诊断 | ✅已修 | `DADAOTargetLowering::getConstraintType("V")→C_Unknown` + lit 反例册 | `clang -c`/`llc` rc=1 + `unknown asm constraint 'V'`；证据 C14 |
| F3 基址可能是 GPRD 值 ⇒ 打印 `[rdN, off]` 非法汇编 | ✅已修 | 非指针 bank 基址 `COPY_TO_REGCLASS`→GPRB（RA 落 `rd2rb`）；frame index 仍留 PEI | 常量地址用例汇编 `set.zw rd4,0x1000; rd2rb {rb4},{rd4}`；证据 C7 `badbase=0` |
| F4 printer 默认实现让 `$0` 印空串（即使选择成功） | ✅已修 | 新增 `PrintAsmMemoryOperand`（`[rb, off]`，无 modifier、非物理基址/非 imm 偏移显式返回错误） | lit 8 处打印断言 + `-verify-machineinstrs` |
| F5 探针 11 用未初始化的局部寄存器变量取值（C UB，实测返回 0 而非 asm 写入值） | ✅已修 | 改成两个内存操作数（`ld.o rd5,%1`+`st.o rd5,%0`） | 探针 11 由 FAIL(1) 转 pass；guest exit 0 |
| F6 证据脚本 `local d="$WORK/$tag"` 与 `$tag` 同行：`set -u` 下变量未赋值即崩 | ✅已修 | 拆成两条 `local` | `run.sh` default 14/14 rc=0、`--inject` rc=0 |
| F7 安装根与构建树同 md5 时 C2 无法复现「修前崩溃」 | ⏸延后 | 脚本改为显式 `[SKIP]` 打印（不静默、不影响 rc） | 现网 md5 不同 → C2 `rc=134 hits=1` |
| F8 builtins 归档跨 clang 换代字节差异来源未查明 | ⏸延后 | 未改代码；以「154/154 TU 无内联汇编」证与 `m`/`p` 无关 | `.work/log/llvm/LLVM-119t-build-builtins*.log`；交 `INFRA-098t`/`ISS-301` |

#### 第 1 轮 reviewer 验收

**重跑**（workdir=仓库根；`master=61e7ece`、树净；安装根 `llc`==构建树 md5 `ee236c50…`、`clang`==`c2b4750d…`；自跑日志落 `/tmp/opencode/REVIEW-FIX4/`，派单限定临时物、未写 `.work/log/`）：
- `bash .work/evidence/LLVM-119t/run.sh` ⇒ **rc=0**，`summary: pass=13 fail=0 skip=1`。C2 **显式 SKIP**（安装根已 `install-host`、无「修前」二进制可对照，脚本不静默）；其余 C1/C3–C14 全 PASS（`C6 运行期 12 探针 guest exit 0`、`C7 in-APP [rb..]=18 badbase=0`、`C12 1/1`、`C13 static 10/10 dynamic 10/10`、`C14 rc=1 named=1`）。
- `run.sh --inject` ⇒ **rc=0**：`inj-oracle`（15→16）/`inj-code`（asm 5→6）各「guest rc=3 红 → `cp`+md5 还原（`59eaeb9a…`）→ 回绿」。
- **两半根因均有实现**（读补丁）：`DADAOISelDAGToDAG.cpp.patch:239` `SelectInlineAsmMemoryOperand`（`m`/`o`/`p`，`SelectAddr` 产 (GPRB, simm12)，非指针 bank 基址 `COPY_TO_REGCLASS`→GPRB）+ `DADAOAsmPrinter.cpp.patch:230` `PrintAsmMemoryOperand`（`[rb, off]`；修饰符非空 / 操作数形态不符 ⇒ 显式返回错，不吞不空印）。
- **12 探针语义**（读 `sem_probes.c` 逐条 + 实跑 guest exit 0）：`=m` 写 7 / `m`+`=m` 拷贝 / `+m` 10→15 / `rm` / `=rm` / 数组 `a[i]` 变量下标 / 8B 写**不破坏邻居** / 结构体字段 `s.b` 且 `s.a,s.c` 不变 / 全局读 `0x55` / 全局写 99 / **大端** `0x0102030405060708` 逐字节 `01..08` / `=&m` —— 与派单 12 项逐条对上 ✓。
- **`"V"` 约束**：C14 `llc` rc=1 + `unknown asm constraint 'V'`（`DADAOISelLowering.cpp.patch:558` `getConstraintType("V")→C_Unknown`），lit `inline-asm-m-reject.ll:17` 钉死该文本；**显式诊断、非断言崩溃** ✓。
- **lit 真值（自跑）**：`llvm-lit tests/llvm/lit/{MC,CodeGen}/DADAO` ⇒ **111/111** rc=0（脚本 C10 同值 `Passed: 111`）；`make check-lit`（MC+CodeGen+e2e）⇒ **121/121** rc=0；`check-instrinfo` rc=0（0 errors）、`check-patch-tree` rc=0（**185**）。
- **独立注入（非脚本自带 2 处）**：`tests/llvm/lit/CodeGen/DADAO/inline-asm-m.ll` CHECK 期望 `rd5→rd6`（`cp`+md5 `51363ed6…`）⇒ 同脚本 rc=1、`C9` FAIL + `C10` FAIL（`Passed: 110 (99.10%)`，可达 FAIL 证明）⇒ 还原 md5 相等 ⇒ 再跑 rc=0（13 pass / 1 skip）。
- **「修前 rc=134」现场**：今天不可复现（安装根==构建树 ⇒ C2 SKIP），采信修前留档 `.work/evidence/LLVM-119t/prefix-llc.log`（真实 `LLVM ERROR: Could not match memory address` + stack dump、程序行 = 当时安装根 `llc repro.ll`）+ 源码事实（两覆写缺位时基类默认 `return true` ⇒ `report_fatal_error`）。

**约束核验**：`git show 84a5231 --stat` = 14 文件，与「修改文件」逐条对上（5 补丁 + `changelog.md` + 2 新 lit + `llvm-isa-backend-matrix.{md,tsv}` + `issues.yaml` + `milestones.md` + 本册，另含派单的 TESTCASES-054t 立册）；`spec/`/`contracts/`/`tests/vectors/`/`components/musl/**` **零改动** ✓；`series` 83 不变 ✓；未 commit/push ✓；`make check`(L1) rc=0（本轮末自跑）。

**文档不符（非阻断，交收尾订正）**：① **lit 计数三值互斥**：`issues.yaml` `ISS-197` 收口段「109/109」、本册/milestones「110/110」、今日现场 **111/111** —— 本批前基线 108，`77153a2` +2 = 110、`16e40bf` +1 = 111 ⇒ **109 无对应盘上状态**（写死计数漂移）。**判定：算必改**（P3 文档一致性，按「计数现场派生」口径订正或去写死），但**不构成 Needs Revision**（交付物功能/测试全绿，差异非本册缺陷）。② 同段「default 13/13」vs 完成区「14/14」——今日 = 13 pass + 1 skip（共 14 项），两处均欠准确。③ 同段称 `V`「前端断言…**未改**」，与现场（已改、显式诊断 + lit 钉死）**不符** ⇒ 同批订正。

**判决：Accepted** —— 验收 1–8 逐条达标（无崩溃 / 语义 12 项 / GETFUNCSYM rc=0 / 失败面指名诊断 / 可达 FAIL 2+1 / 门控 rc=0 / 完成区对齐 / 未 commit）；上述 3 处文档不一致为收尾订正项（P3），不阻断。

#### 提交记录（architect，2026-10-20）
- 档位：`待验收`（reviewer 未验收；按主会话指令以任务号正常提交，与既有 `QEMU-066t` 同例，无 `WIP:` 前缀）
- 提交：分支 `LLVM-119t` 上 `00f493f` ⇒ `master` squash `84a5231`
- 文件集对账：13 文件 = 完成区「修改文件」逐条命中（5 补丁 + `changelog.md` + 2 新 lit + `llvm-isa-backend-matrix.{md,tsv}` + `issues.yaml` + `milestones.md` + 本册），无漏提 / 多提 / 越界；`check-patch-tree` **185**、L1 `make check` rc=0
