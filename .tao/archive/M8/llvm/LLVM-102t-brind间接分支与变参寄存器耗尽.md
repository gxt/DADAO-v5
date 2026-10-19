# LLVM-102t: 后端能力缺口（`brind` 间接分支 ISel + 变参调用寄存器耗尽溢出）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`TESTCASES-048t`（现场来源 = A 类 222 单元 × 两档全量，`blocked 27` 中的 2 例；两档一致）、`ISS-267`（登记源；本册承接 ②③ 两项）；契约依据：`contract-isa §8.3`（`jump rbha, rdhb, imms12` 地址计算）、`contract-abi §4.1`/`§4.3`（参数寄存器 / 栈溢出区）、`§5`（可变参数已由 `ADR-0031` 收口于 **M8**）、`§6.3`/`§6.4`（`i128` 不支持 / 聚合 64 B 门槛）、`ADR-0031`（**`Accepted`**，2026-10-18：`D2` callee 快照 / `D4` 不拆半 / `D8b` 默认 `-Werror=varargs`）、`ADR-0025`（M8 范围）、真源 `spec/DADAO-21-ABI §3.3`（可变参数：七字段 `va_list` + callee 保存区 + `va_arg` 四步）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 问题根源

本册两**互相独立**的后端能力缺口，现场均来自 `TESTCASES-048t` 第 2 步全量（A 类 222 单元，静态→动态两档逐数相同：`pass 193 / fail 2 / known-fail 0 / blocked 27 / excluded 0`），均**显式失败**（编译期报错，非静默错码）。

### A（可执行）——`ISD::BRIND`（间接分支）无 ISel

- **现场（逐字）**：`Cannot select: t29: ch = brind t28, t27` —— `SingleSource/Benchmarks/Misc/evalloop`（`evalloop.c`，含 `goto *p`/计算跳转），两档一致，driver 记 `blocked`。
- **DAG 来源（结构事实）**：`SelectionDAGBuilder::visitIndirectBr()` 把 LLVM `indirectbr` 生成为 `ISD::BRIND`（链 + 目标地址），该节点与本后端既有的**跳转表**路径（`ISD::BR_JT`）是**两个节点**。
- **后端现状（本笔实读）**：
  - `DADAOISelLowering.cpp` 只对 `ISD::BR_JT` 设 `Custom` 并 `LowerBR_JT` → `DADAOISD::BR_JT`；**`ISD::BRIND` 无 action、无 pattern、selector 无分支**。
  - `DADAOISelDAGToDAG.cpp::Select()` 只对 `DADAOISD::BR_JT` 做自定义选择（其余落 `SelectCode`）⇒ `brind` 无处可选 ⇒ `Cannot select`。
- **ISA 事实（`contract-isa §8.3`，本册自包含）**：

  | 指令 | 格式 | 地址计算 |
  | --- | --- | --- |
  | `jump imms24` | iiii | `Addr = rb0 + (imms24 << 2)`（PC 相对） |
  | `jump rbha, rdhb, imms12` | rrii | `Addr = rbha + rdhb + (imms12 << 2)` |

  `ha` = **基址（RB 银行）**、`hb` = **偏移（RD 银行）**；`rb0` 是 IP（只读），`rd0` 硬连零；地址按 64 位全宽计算、取低 48 位。
- **⇒ 指令形态与目标 bank 的选择依据（本册钉死，实施须在完成区复述并附反汇编）**：绝对地址跳转只能写成 **`jump [rbX, rd0, 0]`**（`rb0` 是 IP、不能作基址；`rd0` = 0 提供零偏移；`imm12 = 0`）。C 语义里函数指针/`&&label` 是**数据**（参数走 RD、返回 `rd8`），而 `jump` 的基址必须来自 **RB** ⇒ 需 `rd2rb {rbY}, {rdX}, 0`（RD→RB 搬移，`.td` `op=0x40/ha=0x35`）或等价的 `CopyToReg` 到 `GPRB` 类虚拟寄存器。**这是「指令形态 + bank」的唯一依据链，不得用 `jump imms24`（PC 相对）冒充绝对跳转**。
- **实现候选（不预设，诊断后定）**：(甲) `setOperationAction(ISD::BRIND, MVT::Other, Custom)` + 自定义选择（与 `BR_JT` 同款，`CopyToReg GPRB` + `jump_rrii`，`rd0` 零偏移）；(乙) `.td` pattern 直接选 `jump_rrii`（若 DAG 侧能保证目标已在 `GPRB`）。两者都须说明为何**不改** `ISD::BR_JT` 既有路径。

### B（**已解阻塞**）——变参调用 + 命名参数寄存器耗尽

- **现场（逐字）**：`fatal error: error in backend: DADAO: a varargs call with register-exhausted arguments is not supported yet` —— `MultiSource/Benchmarks/Prolangs-C/plot2fig`（`arc.c` 的多次 `printf` 风格调用），两档一致，driver 记 `blocked`。
- **实现位置（本笔实读）**：`DADAOISelLowering.cpp:740-742` —— `if (VarArgSaveArea && CCInfo.getStackSize() != 0) report_fatal_error(...)`；即「变参保存区」与「栈实参」同时出现时**主动拒绝**。
- **依据（`ADR-0031` 已 `Accepted`，用户 2026-10-18 逐条确认）**：
  - `D2` = **寄存器保存区归 callee**（`va_list` 指向 callee 入口快照的保存区；每 bank 一条 `stm.o`；caller 不再写保存区）⇒ 本册须**移除上述拒绝**并按「保存区 + 栈实参同时成立」实现。
  - `D4` = **不拆半**：某 bank 不足时整值取自栈，该 bank 游标与剩余计数**不推进**。
  - `D8b` = 工具链**默认** `-Werror=varargs`（用户原话「**D8：2**」）：变参相关诊断默认升级为错误；`-Wno-error=varargs` 为显式退出（上游老代码用），**门控 / 自有代码零容忍**；**不得**把该默认关掉来「绕过」失败。
  - 真源 = `spec/DADAO-21 §3.3`（`va_list` 七字段 = 3 游标 + 3 剩余计数 + 栈指针；`va_start` 初始化；`va_arg` 四步）；契约 = `contract-abi §5` 行（**M8 收口**）/ `§4.2`（16 字节值与 `float` 低 32 位）/ `§4.3`（16 B 栈槽）。
- ⚠️ **A 与 B 相互独立**：可分别实现与验收；B 的契约前置已满足（不再是停点）。

## 接口规范

- **输入**：
  - `.work/source/llvm-project/`（组件源码检出，`git` 干净基线）
  - `components/llvm-project/patches/**`（树形补丁集，一文件一补丁）+ `series` + `changelog.md`
  - 语料：`.work/source/llvm-test-suite/SingleSource/Benchmarks/Misc/evalloop.c`、`.work/source/llvm-test-suite/MultiSource/Benchmarks/Prolangs-C/plot2fig/`（`patchless`，**只读**）
  - 安装根 `.dadao/cross-toolchain/`（改 `components/**` ⇒ 必须 `install-host` 后才新鲜）
  - 契约：`contract-isa §8.3`、`contract-abi §4/§5/§6`（只读引用）+ `ADR-0031`（`Accepted`；变参口径真源 = `spec §3.3`）
- **输出**：
  - `components/llvm-project/patches/**` 更新（A；B 待裁定后同法）+ `series` 计数变化 + `changelog.md` 一条
  - lit 向量：`llvm/test/CodeGen/DADAO/` 下新增**最小**用例（A：`indirectbr` ⇒ `jump` 形态 + `rd2rb`/`jump` 两条指令 + bank 断言；B 视裁定）
  - 端到端证据：`.work/evidence/<任务号>/run.sh`（default + `--inject`）、反汇编文本、编译日志
  - 本任务书完成区（与真实输出逐条对齐）
- **约束**：只改 `components/llvm-project/**` + 本任务书（+ 台账按裁决）；**不动** `spec/`、`.tao/contracts/`、`contracts/`、语料；**不改** `ISD::BR_JT` 既有路径行为（不回归）。

## 最小复现（自包含）

**A：间接分支**

```c
/* /tmp/opencode/LLVM-102t/repro_brind.c */
#include <stdio.h>
int main(void) {
    int acc = 0;
    void *p = &&L1;
    goto *p;                       /* ⇒ ISD::BRIND */
L1: acc += 1;
    void *q = acc ? &&L2 : &&L3;
    goto *q;
L2: acc += 2; goto done;
L3: acc += 4;
done:
    printf("acc=%d\n", acc);       /* 期望 3 */
    return acc == 3 ? 0 : 1;
}
```

编链口径（与 `TESTCASES-048t` 同源、静态档）：`clang -target dadao-unknown-elf -nostdinc -I <MUSL>/{arch/dadao,arch/generic,obj/src/internal,src/include,src/internal,obj/include,include} -O2 -c` ⇒ `ld.lld -o repro.elf repro.o <MUSL>/lib/crt1.o <MUSL>/lib/libc.a --start-group <builtins> --end-group` ⇒ `qemu-dadao repro.elf`。修前须能复现 `Cannot select: ... brind`。

**B：变参 + 寄存器耗尽**（裁定后启用）

```c
/* /tmp/opencode/LLVM-102t/repro_varargs.c：17 个整型实参（rd16–rd31 用尽）+ 变参尾 */
#include <stdio.h>
#include <stdarg.h>
static long sum(int n, ...) { va_list ap; va_start(ap, n); long s = 0;
    for (int i = 0; i < n; i++) s += va_arg(ap, int); va_end(ap); return s; }
int main(void) {
    long s = sum(16, 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16); /* 期望 136 */
    printf("sum=%ld\n", s);
    return s == 136 ? 0 : 1;
}
```

## 验收标准

1. **A 诊断与形态**：完成区写「`brind` 由哪个 pass 产生、dev 后端缺哪一环、所选指令形态（`jump [rbX, rd0, 0]`）与 bank 搬移依据（`contract-isa §8.3` + `rd0` 零值 + RD 是数据面）」+ 修后 `llvm-objdump -d` 片段（含 `rd2rb` 与 `0x71` `jump`）。
2. **A 端到端**：`repro_brind` 修前 `Cannot select`（编译 rc≠0，留输出）、修后 `qemu-dadao` 打印 `acc=3` rc=0。
3. **A 向量**：新增 lit 用例在 `check-lit`（或 `ninja check-llvm-codegen-dadao` 等价目标）中 **PASS**，并断言「`indirectbr` 不再产生 `Cannot select`」+ 指令形态（`FileCheck` 两条 `jump`/`rd2rb`）；向量须能对**修前**后端 FAIL（以归档修前产物或注入方式证明可达 FAIL）。
4. **B（已解阻塞）**：完成区先写 `ADR-0031` 的落点（`D2` callee 快照 / `D4` 不拆半 / `D8b` 默认 `-Werror=varargs`）；`repro_varargs` 修前 `varargs call with register-exhausted`、修后 `sum=136` rc=0，且命名参数（寄存器）与可变参数（保存区 + 栈）两组值都正确（独立 oracle：总和 136 由实参序列手算）；给出 `-Werror=varargs` 默认生效的可判据现场（触发 / 不触发各一例），并验证 `-Wno-error=varargs` 可显式退出（同一触发例降为 warning、编译 rc=0），且**默认档本仓自有代码 / 门控零 `varargs` 告警**。
5. **`TESTCASES-048t` 复跑（只跑受影响例 + 两档）**：`--only 'evalloop$'` 与 `--only 'plot2fig$'` 两档转 `pass`；`blocked 27 → 25`、`pass 193 → 195`、`fail 2`/`known-fail 0`/`excluded 0` **不变**；**无回归**（逐例 JSON diff，类别变化仅限本节列出的例）。
6. **可达 FAIL**：≥2 处注入（形状自选，例如：把 `jump_rrii` 的基址改回 `rb0`、把 `rd2rb` 搬移删掉、把 `ISD::BRIND` action 改回默认）⇒ 对应断言 `[FAIL]`、脚本 rc=1 ⇒ `cp` + md5 还原 ⇒ 回绿、rc=0（**禁** `git checkout`/`restore`/`stash`）。
7. **门控（各留自身 rc，现场计数不写死）**：`check-patch-tree`、`check-instrinfo`（若改 `.td`）、`check-component-changelog`、`check-lit_gen`、`make check`(L1)。
8. **`install-host` 前置申报**：改 `components/llvm-project/**` ⇒ **单跑** `install-host`（`JOBS=8`、不并发、`ISS-210`；启动前申报预计耗时），完成后核安装根 `clang --version` 新鲜并用安装根复跑第 2/5 条。

## 不做

- **不做** B 的自行补契约/自行改 ABI 口径（`ADR-0031` 已 `Accepted`；实现与 `spec §3.3` 逐条对齐）；**不做**关掉 `-Werror=varargs` 默认的规避。
- **不改** `spec/`、`.tao/contracts/`、`contracts/`、语料/期望值。
- **不做** `ISD::BR_JT` 重构、`switch` 跳转表优化、`musttail` 变参（既有 `musttail` 拒绝路径不动）。
- **不做** `clang` 前端崩溃 2 例（`lencod`/`obsequi`，`ISS-267` ①，未派册）、`flog` libcall（`LLVM-103t`）。

## 硬约束

1. 临时目录 `/tmp/opencode/LLVM-102t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕**被检命令自身**退出码（禁 `cmd | tee` 吞码）；复杂输出落 `.work/log/llvm/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时留问（B 即此类：裁定前不得动手）。
6. 用户裁定须把**原话**写入本任务书。
7. 补丁导出纪律：`/tmp` 写入、非空 blob、`check-patch-tree` 断言全绿。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

### A 段（`brind`）

**测试结果**：A 段全部通过（详见 `.work/log/llvm/LLVM-102t-A-*.log`、`.work/evidence/LLVM-102t-A/`）。
**修改文件**（本仓）：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOISelLowering.h,DADAOISelLowering.cpp,DADAOCodeGen.td,DADAOISelDAGToDAG.cpp,DADAOInstrInfo.cpp,DADAOMCInstLower.cpp}.patch`（6 份改；`series` 78 不变）、`components/llvm-project/changelog.md`（+1 条）、`tests/llvm/lit/CodeGen/DADAO/indirectbr.ll`（新增）、`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`（补丁行号漂移重派生）、本任务书；证据 `.work/evidence/LLVM-102t-A/{run.sh,probe/**,pre/**}`（`.work` 不入 git）。
**验收结果**：
- **ISA 事实**（`spec/SimRISC-06 §3.2` :25/:26/:99-103、`contract-isa §8.3`）：绝对跳转只有 `jump [rbHA, rdHB, imms14]`，`Addr = rbHA + rdHB + (imms12 << 2)`（64 位全宽、取低 48 位）；`ha` 必须是 RB（基址，**只读**），`hb` 是 RD（偏移）；`rb0` 读出为 IP ⇒ **不能作基址**；`rd0` 硬连零 ⇒ 绝对目标 = `jump [rbTarget, rd0, 0]`。C 的函数指针/`&&label` 是数据（RD/`rd8`）⇒ 必须 `CopyToReg` 到 GPRB（跨行 `rd2rb`），**不用** PC 相对 `jump imms24` 冒充。
- **实现**：`setOperationAction(ISD::BRIND, MVT::Other, Custom)` + `LowerBRIND`（目标 → 新建 GPRB vreg 的 `CopyToReg` → retag `DADAOISD::BRIND`）→ selector 发 `jump_rrii`（`rd0`、`imm12=0`）。另需块地址物化：新 `BLOCK_ADDR` 伪指令 + `ISD::BlockAddress` 选择 + `MO_BlockAddress` MC 下降（`set.zw/or.w` 三片 `R_DADAO_ABS48`，结果 GPRB）。**不改** `BR_JT` 路径。
- **修前原文**：evalloop `Cannot select: t29: ch = brind t28, t27`（`pre/evalloop_brind_before.err`）；`indirectbr.ll` 用 `pre/indirectbr_lit_before.err` 亦为 `Cannot select: t3: ch = brind t2:1, t2`；`&&label` 先撞 `Cannot select: t5: i64 = BlockAddress<@main, %L1>`。
- **修后汇编**（`indirectbr.ll`）：`rd2rb {rb4}, {rd16}` / `jump [rb4, rd0, 0]`（`0x71`）；`indirectbr_ptr` 无 bank 移动直接 `jump [rb16, rd0, 0]`。
- **三个探针（独立 oracle 自算）**：① `&&label` computed goto ⇒ `acc=3` rc=0；② 表 + `& ~3` 的 RD 目标（oracle：argc=1→`tbl[1]`→L2）⇒ `two` rc=2；③ 函数指针数组调用（`call_rrii` 不回归）⇒ `f1` rc=0；`-O0/-O1/-O2/-Os/-O3/-fPIC` 均 rc/输出正确。
- **evalloop 两档**：`run_llvm_ts_user.py --only 'evalloop$' --link-mode both`（构建树 clang/lld）⇒ static `pass=1/exit 0`、dynamic `pass=1/exit 0`，上游参考 stdout+exit `matched (fpcmp)`。
- **无回归**：lit CodeGen 目录 **33/33 PASS**（含新向量）；11 例 SingleSource 参考 oracle **11/11 pass**；`clang`/`llc` rc=0。
- **补丁/门控**：`check-patch-tree` **174 patches OK**（基线 174，`series` 78 不变）；`check-instrinfo`/`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check_lit_gen`/`make check`(L1) **各 rc=0**；`check-isa-coverage` 因补丁行号漂移先红、重派生矩阵后 rc=0。
- **证据脚本**：`.work/evidence/LLVM-102t-A/run.sh` default **rc=0**（全 CHECK rc=0）；`--inject` **rc=0**：I1 基址改回 `rb0` ⇒ qemu 超时 124、I2 删 `rd2rb` ⇒ SIGSEGV 139、I3 flip FileCheck ⇒ FAIL；`cp`/md5 对账原件未变、默认回绿。

**新发现/坑**：① `goto *p`（`&&label`）的首个后端缺口其实是 `ISD::BlockAddress` 无物化路径，修 BRIND 前须先补块地址取值（勿误判为只缺 ISel 分支）。② 空 `asm("" : "+r"(a))` 不能阻止 SimplifyCFG 把已知目标的 `indirectbr` 折成直接分支；要构造 RD 目标探针须经「表 + 运行期下标 + 位运算」并核对反汇编确有 `rd2rb`。③ 4 字节对齐标签地址不能 `& ~7`（会落进上一条指令中段，现场表现为打印垃圾 `p`）；oracle 的掩码须与 ISA 对齐约束一致。④ 改 DADAO 补丁会整体平移 `tools/llvm/llvm-isa-backend-matrix.*` 的行号证据；`check-isa-coverage` 是本次唯一需要重派生的既有门控（勿手改矩阵）。
**遗留问题**：**B 段（变参 ABI）未做**（本笔只做 A，B 另派）；`install-host` / L2 / L3 **未跑**（主会话执行，`ISS-210`）；本笔未 commit/push（提交权归 architect）。

### B 段（变参，`ADR-0031`）

**测试结果**：B 段实现完成；8 个可执行探针全过、`-Werror=varargs` 两态符合、lit 33/33、`make check`(L1) rc=0。**libc 运行时复跑 BLOCKED**：`libc.a` 仍是旧 `void*` va_list（未 `build-musl`），凡 libc 内 `va_arg`（`printf`/`vfprintf`）读垃圾 ⇒ 依赖 `printf` 输出比对的用例（含 A 段 evidence）须主会话 `install-host`+`build-musl` 后复跑。
**修改文件**：`components/llvm-project/patches/**` **10 份**（3 新增：`clang/include/clang/Basic/TargetInfo.h`、`clang/lib/AST/ASTContext.cpp`、`llvm/lib/Target/DADAO/DADAOMachineFunctionInfo.h`；7 改：`clang/lib/Basic/Targets/DADAO.h`、`clang/lib/CodeGen/Targets/DADAO.cpp`、`clang/lib/Driver/ToolChains/DADAO.{h,cpp}`、`llvm/lib/Target/DADAO/DADAOISelLowering.{h,cpp}`、`DADAOTargetMachine.h`）；`series` **78→81**、`check-patch-tree` **174→177**；`changelog.md`（B 段 +1 条）、`tests/llvm/lit/CodeGen/DADAO/m6-varargs.ll`（改写为三游标 ABI）、`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`（行号漂移重派生）、本任务书；证据 `.work/evidence/LLVM-102t-B/**`（`.work` 不入 git）。
**验收结果**：
- **`va_list`（D1）**：`__builtin_va_list` = `__va_list_tag[1]`，七字段 `rd_next,rb_next,rf_next,rd_left,rb_left,rf_left,stack_next`，偏移 0/8/16/24/32/40/48、`sizeof=56`/`align=8`（`void*`×4 + `long`×3）；`_Static_assert` 全过。
- **保存区 / `va_start`（D2）**：按命名参数实占算 `start`（`TRI->getEncodingValue`），RD/RB/RF 各一条 `stm.o {rXstart:rX31}`（未用槽 live-in；RD 区 1 槽 pad 使游标 bit3 = 槽号奇偶）；七字段落盘，`left=32-start`，`stack_next = incoming_sp + 命名栈字节数`（`p_edge` 实测 16 RD+栈）。lit 断言三条 `stm.o`、`rd_left=0xf`、`CHECK-NOT` caller 保存区。
- **`va_arg` 五步（D3–D6）**：HFA→RF（每叶 1 槽）/HPA→RB/通用→RD 块/`>64 B`→RB 指针按值复制；`left>=need` 取寄存器，否则**整值取栈、游标与 left 不推进**；16 B 偶号配对（奇号跳 1 槽、`need=3`）；HFA 按叶还原（f32 寄存器槽低 32 位 ⇒ big-endian `+4`，栈槽 `+0`）；`va_copy`=56 B memcpy（`VACOPY` Custom）、`va_end` 空操作；通用聚合 clang 侧 coerce `[N x i64]`（命名/变参同一套）。
- **探针（独立手算 oracle，按返回码断言）**：① 全类型 `int/void*/double/long/char`；② 跨 bank 混排 20 参（10+10=20）；③ 耗尽：20 int（210）、17 double（16 RF+1 栈=153）、16 RD+栈；④ HFA `{double,double}` 寄存器 3.75 / RF 耗尽整组栈 15.25、`{float,float,float}`=123；⑤ `va_copy` + `va_list` 传参；⑥ `>64 B`（80 B→55）、12 B/union/1 B。全在 `-O0/-O1/-O2/-Os/-O3`、`-fPIC`、`-verify-machineinstrs` 通过。
- **`-Werror=varargs`（D8b）**：`va_arg(ap,float)` 默认 **rc=1**（`[-Werror,-Wvarargs]`）；`-Wno-error=varargs` **rc=0** 且降为 warning。
- **field cases**：`plot2fig` 两档**编译通过**，链接停既有 `undefined symbol: re_comp`（musl 无 BSD regex，上游条件构建；与 archie-client 同因，reason 不含 varargs）；`consumer-lame` 两档**编译+链接通过**，运行 `qemu killed by host signal 11`（旧 libc 未重建，非 varargs）。
- **无回归/门控**：lit CodeGen **33/33 PASS**、`check_lit_gen` rc=0、`clang`/`llc` rc=0；11 例 SingleSource 8 pass、3 例因旧 libc `printf` 输出不符（待重建复跑）；`check-instrinfo`/`check-patch-tree`/`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-issues`/`make check` **各 rc=0**（`check-isa-coverage` 重派生后 rc=0）。
- **证据脚本**：`.work/evidence/LLVM-102t-B/run.sh` default **rc=0**；`--inject` **rc=0**（I1 缩短 RF 保存区→rc=3；I2 翻转 oracle→rc=8；I3 flip FileCheck→FAIL；md5 对账、默认回绿）。
**新发现/坑**：① 旧 musl 与新 ABI **不可混跑**：`va_list` 变七字段后未重建的 `printf`/`vfprintf` 仍按旧 caller 保存区取参 ⇒ 实测输出 `0 (null) 0.000000 0`（预期不兼容切换，非 codegen 缺陷）。② `plot2fig` 下一停点 = **`re_comp`**（`ISS-267⑥` 平台缺口，不得造 stub）。③ **调用方 16 B 分组缺口**：TableGen CC 逐 piece 分配、无法表达「参数组」，仅剩 1 槽时调用方会拆半（`va_arg` 已按 D4 整组）；需后续 CC 组分配器。④ 本实现 `rbfp == incoming_sp`（prologue 设 FP=entrySP），与 `contract-abi §4.3` 字面 `rbfp+8` 不符；`stack_next` 用 fixed-object 取 `incoming_sp`，与既有栈参数路径一致。
**遗留问题**：`install-host`/`build-musl`/L2/L3 未跑（主会话；`ISS-210`）；`plot2fig`/`consumer-lame` 与 A 段 libc 运行时复跑待 musl 重建；16 B「仅剩 1 槽」的调用方整组回退待 CC 组分配器；本笔未 commit/push、未改 `**状态**`（仍 `待开始`）。

#### B 段安装根复验（`install-host` 后 + 新 musl）

**测试结果**：安装根 clang/ld.lld/qemu-dadao（clang md5 `98d342204f7d99aae4bc8ab66f221e82` = 构建树）+ 重建 musl 后，B 段运行时真值全部补齐；唯一新 fail = `functional/fcntl`（见下，musl 侧 `va_arg` 类型不匹配，**未改判据**）。
**验收结果**：
- **musl 重建**：`make build-musl-shared JOBS=8` **rc=0**（18:04:20→18:05:33，≈70 s；`libc.a`/`libc.so` 18:05:31–32）；`make check-musl-freshness` **PASS**，原文末行 `check-musl-freshness: PASS (installed libc.so built from the current musl sources + toolchain)`。
- **`va_list` 布局**：安装根 clang 编译 `check_valist.c`（56 B/七偏移/类型）rc=0。
- **真实 `printf`**：`printf("%d %s %f %ld %c\n", 42, "ok", 2.5, 123456789L, 'Z')` ⇒ 逐字输出 **`42 ok 2.500000 123456789 Z`**（修前旧 libc 为 `0 (null) 0.000000 0`），qemu rc=0。
- **6 组探针**（安装根 clang + 新 musl，`-O2`）：`p_types`（全类型/跨 bank）rc=0；`p_all`（HFA 寄存器/RF 耗尽栈、`va_copy`、`va_list` 传参、16 B/12 B/union/1 B）rc=0；`p_edge`（16 RD+栈、16 RB+栈）rc=0；`p_small` rc=0；`p_named`（命名聚合不回归）rc=0；`p_big`（>64 B 间接）rc=0；`p_exhaust`（20 int=210、混合 20 参=20）rc=0；`repro_varargs` 输出 **`sum=136`** rc=0；`-Werror=varargs` 默认 rc=1（`-Werror,-Wvarargs`）/`-Wno-error=varargs` rc=0。
- **`plot2fig`（两档）**：编译通过；reason 逐字 **`link error rc=1: ld.lld: error: undefined symbol: re_comp`**（不含 `varargs`；`ISS-267⑥` 平台缺口）。
- **`consumer-lame`（两档）**：**PASS**，`exit=0`，`output+exit (...reference_output): matched (byte-exact), exit 0`（每档 ≈31.5 s）。
- **3 例回归**：`dt`/`fp-convert`/`lowercase` 静态+动态 **3/3 pass**（此前因旧 libc `printf` 输出不符）。
- **`047t` 10 例小样本**（`api/main`、`functional/{argv,fcntl,env,fnmatch,inet_pton,time}`、`regression/daemon-failure`、`math/{sin,exp}`）：静态 **9 pass / 1 fail**、动态 **9 pass / 1 fail**（两档一致）；fail = `functional/fcntl`，原文 `fcntl(fd, 6, &fl)==0 failed: errno = Bad address`（`errno=14 EFAULT`）。**根因（新增发现，非 codegen 缺陷）**：musl `src/fcntl/fcntl.c:12` 用 `va_arg(ap, unsigned long)` 取第三参，而调用方传的是 `struct flock *`；旧 ABI（caller 单槽保存区）下二者同槽故侥幸可用，`ADR-0031 D3` 按类型分流后指针落 RB、`unsigned long` 读 RD ⇒ 取到 0 ⇒ EFAULT。最小复现：`fcntl(fd, F_SETLK, &fl)` ⇒ `r=-1 errno=14`，而 `fcntl(fd, F_SETFL, 0)`（整数参）⇒ `r=0`（整数路径正常）。**建议**：musl 端口按 `cmd` 分流（指针类命令读 `va_arg(ap, void*)`，整数命令读 `unsigned long`）；属 `components/musl` 另册，本笔不改判据、不造 stub。
- **A 段复跑**：`.work/evidence/LLVM-102t-A/run.sh` 在新 musl 下 **rc=0**（`evalloop` 两档 pass、11 例 SingleSource 11/11）；此前「旧 libc 读垃圾」的临时失效已消除。
- **门控**：`check-musl-freshness`/`check-patch-tree`（**177**）/`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check-issues`/`make check`(L1) **各 rc=0**；证据 `.work/evidence/LLVM-102t-B/run.sh` default **rc=0**（安装根 + 新 musl；含 printf/consumer-lame/047t/回归）、`--inject` **rc=0**（三条注入仍全红）。
**遗留问题**：`functional/fcntl`（及同族「同一变参槽内 int/指针混用」的 musl 调用）需 musl 端口另册修复（见上）；`plot2fig` 的 `re_comp` 仍属平台缺口；L2/L3 未跑（主会话）。

**订正（2026-10-18，`INFRA-092t` 收口后）**：上条 `functional/fcntl` 的失败**已由 `INFRA-092t` 修复**（musl 封装 `va_arg` 类型面：`fcntl` 按 `cmd` 分支、`syscall()` 按 `__dadao_argmask` 分 bank）；复跑 `047t fcntl` **静态 1/1、动态 1/1 pass**。本册 B 段仍**余 `D4` caller 侧**（16 B「仅剩 1 槽」整组回退，需 CC 组分配器）**待裁**。

#### D4 caller 侧（`ADR-0031 D4`，2026-10-18）

**测试结果**：整组分配实现完成；`p_d4` 7 项边界探针修前 **exit 86**（bits 2|4|16|64）→ 修后 **0**；f128/HPA/12 B/命名聚合探针全 0；lit **34/34**、SingleSource **11/11**、047t 10 例 **static/dynamic 10/10**；证据脚本 default/`--inject` rc=0。
**修改文件**：`components/llvm-project/patches/**` **3 份改**（`clang/lib/CodeGen/Targets/DADAO.cpp`、`llvm/lib/Target/DADAO/DADAOISelLowering.{h,cpp}`；`series` 81 不变、`check-patch-tree` **180 不变**）；`changelog.md` +1 条；`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`（行号漂移重派生）；本任务书；证据 `.work/evidence/LLVM-102t-D4/**`（`.work` 不入 git）。
**验收结果**：
- **诊断（修前）**：`llc` 汇编（安装根 pre-D4 编译器，`pre/llc_pre.s`）显示 `odd_rd` 的 16 B 值落 `ld.o rd17` + `rd18`（奇号起、本应偶号）；`one_rd`（RD 仅剩 rd31）为 `rd31` + 栈两块；`one_rf`（RF 仅剩 rf31）为 `rf31` + 栈两叶；`one_rd24` 三块亦拆半 ⇒ 运行 exit **86**。**确认会拆半**。
- **实现**：`DADAOTargetLowering::functionArgumentNeedsConsecutiveRegisters` 对 HFA/HPA/通用块类型返回 true，SelectionDAGBuilder 给 pieces 打 `InConsecutiveRegs`/`...Last`；`reassignDADAOArgLocs` 在 `LowerCall` 与 `LowerFormalArguments` **同一套**重算每 bank 槽位/栈偏移：整组够 ⇒ 连续寄存器；不够 ⇒ 整组连续栈、bank 游标与 `left` 不推进；RD 两块的 16 B 组偶号起、奇号先跳 1 槽、不足则整值栈；f128 按 RF 偶对同规则；`va_arg` 侧既有 `left`/奇偶判定与此逐条一致。clang 侧把 HFA/HPA/`_Complex` 改为 `[N x 叶子]` 单 IR 实参（`getDirect(struct)` 会被 CodeGen 展开成多个实参、丢组）。
- **修后汇编**：`odd_rd` = `ld.o rd18` + `ld.o rd19`（跳 rd17）；`one_rd` = 两半 `[sp,0]/[sp,8]` 连续、后续 int 落 `rd31`；`one_rf` = 两叶连续栈、后续 double 落 `rf31`；f128 同款（`rf18/19` 或连续 16 B 栈 + 后续 `rf31`）。
- **探针**：① 偶 RD/奇 RD（15 空槽，跳 1 槽成对）/RD 仅 1 槽（整值栈）；② RF 偶/奇/仅 1 槽（HFA 整组栈）；③ 24 B 三块整组栈；④ f128 偶/奇/仅 1 槽/命名对；⑤ HPA 仅 1 槽；⑥ 12 B 奇游标；⑦ 命名 LL/DD（caller/callee 同改）；`-O0/-O2/-Os/-O3/-fPIC`、`-verify-machineinstrs` 全过。
- **无回归/门控**：CodeGen lit **34/34**、`check_lit_gen` rc=0；11 例 SingleSource **11/11**；047t 10 例（含 `execle` 变参）**两档 10/10**；`check-instrinfo`/`check-patch-tree`(**180**)/`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-issues`/`make check`(L1) **各 rc=0**（`check-isa-coverage` 重派生后 rc=0）。
- **证据脚本**：`.work/evidence/LLVM-102t-D4/run.sh` default **rc=0**；`--inject` **rc=0**（I1 asm 对寄存器改回奇号→rc=2；I2 oracle 翻转→rc=7；I3 删 call 侧重算→grep FAIL；md5 对账 + 默认回绿）。
**新发现/坑**：① clang `getDirect(StructType)` 会把聚合**展开成多个 IR 实参**，SelectionDAGBuilder 无法识别参数组；HFA/HPA/`_Complex` 必须 coerce 为 `[N x 叶子]` 数组保持单实参（通用聚合本就 `[N x i64]`）。② 9–15 B 通用聚合（两块）也采用「偶号起」约定：D6 只对 16 B 强制，但后端无法从 `[2 x i64]` 区分 12 B/16 B，`va_arg` 侧同步用 `Slots==2` 判定以保持一致（不改变 16 B 语义；仅多耗 1 槽）。③ f128/16 B 的栈上两块按**连续 8 B** 放置（不做 16 B 补位），与 `va_arg` 的 `stack_next` 推进一致；D7 的绝对 16 B 对齐仍属独立事项。④ 安装根 clang 为 pre-D4，修前产物已存 `pre/`；构建树为 post-D4（本轮不 `install-host`）。
**遗留问题**：`install-host`/L2/L3 未跑（主会话）；9–15 B 的偶号约定与 D7 绝对 16 B 栈对齐（见坑②③）；本笔未 commit/push、未改 `**状态**`（仍 `待开始`）。

**执行期偏差（2026-10-18）**：① 9–15 B 两块聚合同样按「偶号起」（`D6` 只强制 16 B，后端无法从 `[2 x i64]` 区分 12/16 B，`va_arg` 用 `Slots==2` 同步）→ **待裁**；② `f128` 在栈上为两个连续 8 B，未做 16 B 补位（`D7` 字面要求 16 B 对齐）→ **待裁**。

### 安装根复验（2026-10-19，`verify-102t-106t`）

**环境**：安装根 clang md5 `738387826812e316314920f2e7de6129` = 构建树 `clang-23`；`qemu-dadao`/`ld.lld`/`llc` 取 `.dadao/cross-toolchain/bin/`；musl = `.work/source/musl`（`check_musl_freshness` PASS）。脚本 `.work/evidence/verify-102t-106t/run.sh`（含 `--inject`），运行产物全落 `/tmp/opencode/verify-102-106/`。

**`brind`（A）**：`&&label` 探针 `acc=3` rc=0，汇编含 `jump [rbX, rd0, 0]`；标签表 + 运行期下标 `two` exit=2，汇编含 `rd2rb {rb4},{rd4}` + `jump [rb4, rd0, 0]`；标量函数指针 + 函数指针数组（volatile 阻断去虚拟化）输出 `f1/arr/f1/scalar` rc=0，汇编含 `call [rbX, rd0, 0]`。
**变参三游标（B）**：`printf` 全类型逐字 `42 ok 2.500000 123456789 Z`；`p_types`（跨 bank 混排）/`p_exhaust`（20 int=210、混合 20 参=20）/`p_edge`（17 RD+栈、16 RB+栈）rc=0；`p_all` -O0/-O2/-Os rc=0（HFA 寄存器与 RF 耗尽整组栈、`va_copy`、`va_list` 传参、16 B/12 B）；`vprintf` 式转发逐字同上。
**D4**：`p_d4` -O0/-O2 rc=0（偶/奇 RD、仅 1 槽整值栈、24 B 三块、偶/奇 RF、仅 1 槽 HFA）。
**`-Werror=varargs`**：默认 rc=1 且含 `-Werror,-Wvarargs`；`-Wno-error=varargs` rc=0 且降为 `warning: ... [-Wvarargs]`。
**回归抽样**：046t 静态 -O2 **19/19 pass**（权威 38/38 两档，子集一致）；048t `Misc/{evalloop,lowercase}` 两档 **2/2 + 2/2 pass**（权威 201/3/0/16/2）；047t 10 例两档 **10/10 + 10/10**（权威静态 309/0/4/24、动态 312/0/4/21）。
**门控**：`check_musl_freshness` rc=0、`check_patch_tree` rc=0（**181 patches OK**）、`check_milestones_fresh` rc=0、`check_issues` rc=0。
**结论**：默认 **112/112 rc=0**；`--inject` **11/11 rc=0**（I1 `p_all` oracle 153→154 ⇒ exit 8；I2 ABI 存储偏移对调 ⇒ 断言 FAIL；I3 `A_HI`+1 ⇒ e2e 非零）。**未暴露实现缺陷**。
**复验坑**：`-O2` 会丢弃未使用的命名实参并去虚拟化函数指针；探针须使用全部参数 / `volatile` 指针才能观察到真实 ABI 形态。
**验收依据**：安装根复验由**独立会话**（`verify-102t-106t`）完成 ✓ —— 112/112 证据 + 11/11 注入 ✓、与权威基线一致 ✓、无缺陷 ✓

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

**审查范围**：6 个后端源文件 diff + 补丁、lit 向量、证据脚本、生成矩阵。逐行核对：BRIND 的目标类型恒为 i64（`getPointerTy`）、`CopyToReg` 链序先于 `jump_rrii`、`jump_rrii` 的 `rd0`/`imm12=0` 编码、`BLOCK_ADDR` 三片 `R_DADAO_ABS48`、`MO_BlockAddress` 的 offset/target-flags 传递、`BR_JT` 路径未动。判决：实现与 `contract-isa §8.3` 逐条一致，无未决 finding。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 首次编辑 `DADAOInstrInfo.cpp`/`DADAOISelDAGToDAG.cpp` 时 `case` 标签被一并吃掉（编译报 `case label not within a switch`） | ✅已修 | 补回 `case DADAO::PCREL_LOAD:`、`case DADAOISD::CALL:` | `ninja` rc=0（18 步）；`llc/clang` 重跑探针全绿 |
| F2 初版 `goto *p`+`asm("+r")` 探针被 SimplifyCFG 折成直接分支，未真正走到 BRIND，无法证明 `rd2rb` | ✅已修 | 改为「`&&label` 表 + 运行期下标 + `& ~3`」探针，先核对汇编有 `rd2rb`+`jump` 再入证据 | `probe_rd2rb` 汇编 `rd2rb {rb4},{rd4}` / `jump [rb4, rd0, 0]`；qemu `two` rc=2 |
| F3 `& ~7` 作用在 4 字节对齐标签上，跳到上一条 `jump` 指令中段（qemu 输出垃圾 `p`） | ✅已修 | 掩码改 `& ~3`（与 4 字节指令对齐一致） | 重跑三种模式输出/退出码正确；oracle 重算（argc=1→tbl[1]→L2→two, rc=2） |
| F4 `check-isa-coverage` 红：补丁行号整体漂移 | ✅已修 | 用 `tools/llvm/gen_isa_coverage.py` 重派生 `matrix.{tsv,md}`（非手改） | `make check-isa-coverage` rc=0；`make check` rc=0 |
| F5 证据脚本注入 I1/I2 对 `.c` 调 `llc`、且把装配失败误判为「注入成功」 | ✅已修 | 改用 `clang -S` 产汇编；`run_asm` 的 3/4 视为 harness 失败单独红 | `--inject` rc=0：I1 124、I2 139、I3 FileCheck FAIL；md5 前后一致、默认回绿 |

#### 第 2 轮 engineer 自审（B 段）
**审查范围**：10 个组件文件 diff + 补丁、`m6-varargs.ll`、证据脚本、矩阵。逐行核对：七字段偏移/大小、`start` 计算（`getEncodingValue`）、`stm.o` 范围 `start+count<=64`、`stack_next` 与命名栈字节数、`left/next` 推进语义、16 B 配对、f32 两条路径（寄存器 `+4` / 栈 `+0`）、`va_copy` 56 B、`-Werror` 优先级。判决：实现与 `ADR-0031` D1–D8b 逐条一致；F8 为**基础设施限制**（已登记遗留），其余 finding 全修。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `stm.o` 起始寄存器误写 `rd16 + Start`（Start 是槽号 16..32，产出过 `{rd33:rd47}`） | ✅已修 | 改为 `rd16 + (Start - 16)`（RB/RF 同） | 汇编 `stm.o {rd17:rd31}`/`{rb16:rb31}`/`{rf16:rf31}`；探针全过 |
| F2 `stack_next` 固定取 `incoming_sp`，命名参数溢出时把命名栈槽当成首个变参 | ✅已修 | MFI 记 `VarArgStackOffset = CCInfo.getStackSize()`，`va_start` 的 fixed object 偏移用它 | `p_edge`（16 RD+1 栈+变参 18/19、16 RB+栈指针）rc=0（修前会错位） |
| F3 `CreateConstInBoundsByteGEP` 要求 Address 元素类型为 i8，HFA 临时 alloca 是 struct ⇒ clang assert | ✅已修 | 用 `Tmp.withElementType(Int8Ty)` 做字节 GEP、返回带 MemTy 的 Address | 编译通过；`p_all` HFA 用例 rc=0 |
| F4 不透明指针与 i64 直接 `CreateAnd` ⇒ `BinaryOperator` 断言 | ✅已修 | 先 `CreatePtrToInt` 再判奇偶 | 编译通过；16 B 聚合用例 rc=0 |
| F5 旧 `m6-varargs.ll` 断言 caller 保存区（旧 ABI）⇒ lit 1/33 红 | ✅已修 | 改写为三游标 ABI（三条 `stm.o`、`rd_left=0xf`、`CHECK-NOT` caller 保存区） | CodeGen lit **33/33 PASS** |
| F6 `_Complex long double` / transparent union 分类偏差；`va_start` 多次调用重复建 fixed object | ✅已修 | complex 用 `isFloatingType`；`classifyArgumentType` 加 `useFirstFieldIfTransparentUnion`；`VarArgStackFI` 只建一次 | 重建 + 探针/lit 全绿 |
| F7 证据脚本用 `llc` 的新鲜度对比 clang 源文件 ⇒ 假红 | ✅已修 | clang-23 只比 clang 源、llc 只比 LLVM 源 | evidence default rc=0 |
| **F8（已解，2026-10-18）** 调用方 16 B 值的偶号配对/仅剩 1 槽整组回退：TableGen CC 逐 piece 分配、无「参数组」通道 | ✅已修（2026-10-18） | `functionArgumentNeedsConsecutiveRegisters` 覆盖 + `reassignDADAOArgLocs` 在 `LowerCall`/`LowerFormalArguments` 重算整组；clang HFA/HPA/`_Complex` 改 `[N x 叶子]` 单 IR 实参 | `p_d4` 修前 exit 86 → 修后 0；llc `rd18/rd19`、连续栈；lit 34/34、047t 10/10；证据 `.work/evidence/LLVM-102t-D4/` |

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）

#### 第 1 轮 architect 提交（A 段）
**档位**：A 段产物正常提交（`1d7ec16`）+ 台账 `WIP:`（`f924c38`）⇒ `git merge --squash` 落地 `master`（本提交）。册状态仍 `待开始`（B 段未做）。
**文件集对账**：`git diff --cached --name-only` = 13 项，全在完成区「修改文件」声明内（6 补丁 + `changelog.md` + `indirectbr.ll` + 矩阵 `.{tsv,md}` + 本册）+ 台账 2（`milestones.md`/`issues.yaml`，本笔 architect 更新）；无漏提 / 无多提 / 无越界。`check-patch-tree` 实核 **174 patches OK**。
**门控**：`make check`(L1) rc=0；`check-lit` rc=2（读 `.dadao/cross-toolchain` 旧安装根，未 `install-host`，`ISS-210` ⇒ 不据此判红，留主会话安装后复跑）。

#### 第 2 轮 architect 提交（B 段）
**档位**：B 段产物**正常提交**（本任务分支第 1 笔）；册 `**状态**` **保持 `待开始`**（B 段**余 `D4` caller 侧**整组回退，**待裁**）。
**文件集对账**：`git diff --cached --name-only` = **17 项** = 10 补丁（7 改 + 3 新）+ `series`（78→81）+ `changelog.md` + `m6-varargs.ll` + 矩阵 `.{tsv,md}` + 本册 + `milestones.md`（本行）；与完成区「修改文件」逐条对齐，**无漏提 / 无多提 / 无越界**（`components/musl/**` 与 `INFRA-092t` 册归第 2 笔）。
**门控（真实 rc）**：`make check`(L1) rc=0「repository checks (L1): PASS」；`check-patch-tree` 全树 **180 patches OK**（本笔落地后 177；第 2 笔 +3 musl 补丁）；`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-milestones-fresh`/`check-musl-freshness`/`check-syscall-abi` 各 rc=0；`check_issues` rc=0（67 open / 27 closed）。
**订正**：上「B 段安装根复验」末条 `functional/fcntl` 的失败已追加订正（`INFRA-092t` 修复、`047t fcntl` 两档 pass）。
