# LLVM-102t: 后端能力缺口（`brind` 间接分支 ISel + 变参调用寄存器耗尽溢出）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`TESTCASES-048t`（现场来源 = A 类 222 单元 × 两档全量，`blocked 27` 中的 2 例；两档一致）、`ISS-267`（登记源；本册承接 ②③ 两项）；契约依据：`contract-isa §8.3`（`jump rbha, rdhb, imms12` 地址计算）、`contract-abi §4.1`/`§4.3`（参数寄存器 / 栈溢出区）、`§5`（可变参数已由 `ADR-0031` 收口于 **M8**）、`§6.3`/`§6.4`（`i128` 不支持 / 聚合 64 B 门槛）、`ADR-0031`（**`Accepted`**，2026-10-18：`D2` callee 快照 / `D4` 不拆半 / `D8` 默认 `-Werror=varargs`）、`ADR-0025`（M8 范围）、真源 `spec/DADAO-21-ABI §3.3`（可变参数：七字段 `va_list` + callee 保存区 + `va_arg` 四步）
**状态**：待开始

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
  - `D8` = 工具链**默认** `-Werror=varargs`（用户原话「**D8：2**」）：变参相关诊断默认升级为错误；**不得**把该默认关掉来「绕过」失败。
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
4. **B（已解阻塞）**：完成区先写 `ADR-0031` 的落点（`D2` callee 快照 / `D4` 不拆半 / `D8` 默认 `-Werror=varargs`）；`repro_varargs` 修前 `varargs call with register-exhausted`、修后 `sum=136` rc=0，且命名参数（寄存器）与可变参数（保存区 + 栈）两组值都正确（独立 oracle：总和 136 由实参序列手算）；给出 `-Werror=varargs` 默认生效的可判据现场（触发 / 不触发各一例）。
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

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
