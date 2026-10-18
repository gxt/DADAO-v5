# LLVM-103t: `flog` libcall 最小补齐（`initLibcallLoweringInfo` 未注册 `LOG_*`）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`TESTCASES-048t`（现场来源 = A 类 222 单元 × 两档全量，`blocked 27` 中的 2 例；两档一致）、`ISS-267`（登记源，本册承接 ④）；同族先例 = `LLVM-080t`/`LLVM-087t`（f64/f32 取整与极值 libcall）、`ISS-193(b)`；契约依据：`contract-isa`（无 FP `log` 指令 ⇒ 必走库调用）、`ADR-0027`（compiler-rt 接入，与本册无关但同构建面）、`ADR-0025`（M8 范围）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 问题根源

- **现场（逐字）**：`error: no libcall available for flog`（clang 后端 fatal），两档一致、driver 记 `blocked`：
  - `MultiSource/Benchmarks/DOE-ProxyApps-C/CoMD`（`random.c`）
  - `MultiSource/Benchmarks/MiBench/consumer-lame`（`psymodel.c`）
- **报错路径（本笔实读）**：`llvm/lib/CodeGen/SelectionDAG/LegalizeDAG.cpp` 的 libcall 展开分支 —— `DAG.getLibcalls().getLibcallImpl(LC) == RTLIB::Unsupported` 时 `emitError("no libcall available for " + Node->getOperationName())`。**该消息只打印 DAG 节点名（`flog` = `ISD::FLOG`），不打印类型/`LC`** ⇒ 具体是 `LOG_F32` 还是 `LOG_F64` **必须在诊断里报出**（见验收 1）。
- **根因方向（本笔实读，待诊断确认）**：`DADAOSubtarget::initLibcallLoweringInfo()` 目前注册了 `MEM*`、f64/f32 的 `FLOOR/CEIL/TRUNC/ROUND/RINT/NEARBYINT/FMIN/FMAX`（`LLVM-080t`/`LLVM-087t`）、i128 除法/取余等，**没有任何 `RTLIB::LOG_*`**；而 `impl_log` / `impl_logf` 在 `RuntimeLibcalls.inc` 中**存在**（现场 `impl_log = 2694`）⇒ 属「已注册机制、漏注册条目」的**接线缺口**，不是新语义。
- **⚠ 口径纠正（本笔）**：`ISS-267` 原文把该例写成「**f80** `long double log`」。现场事实 = `clang/lib/Basic/Targets/DADAO.h:55` `LongDoubleWidth = LongDoubleAlign = 64`（`long double` ≡ `double`；`ADR-0030` 的 binary128 排 `M9`）⇒ 本 target 当前**不产生 f80**；诊断须**证伪/改正**该表述，并按实际 `LC` 落最小补齐。不得以「f80 不支持」为由放过。

## 接口规范

- **输入**：
  - `.work/source/llvm-project/`（组件源码检出）+ `components/llvm-project/patches/**` + `series` + `changelog.md`
  - 语料：`.work/source/llvm-test-suite/MultiSource/Benchmarks/DOE-ProxyApps-C/CoMD/`、`.../MiBench/consumer-lame/`（`patchless`，**只读**）
  - 安装根 `.dadao/cross-toolchain/`（改 `components/**` ⇒ 必须 `install-host` 后才新鲜）
- **输出**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOSubtarget.cpp.patch`（`initLibcallLoweringInfo` 增补）+ `series`（不增删文件则计数不变）+ `changelog.md` 一条
  - lit 向量：`llvm/test/CodeGen/DADAO/` 最小 `.ll`（`llvm.log.f64` / 需要时 `llvm.log.f32`）⇒ FileCheck 断言生成到 `log`/`logf` 的调用
  - 证据：`.work/evidence/<任务号>/run.sh`（default + `--inject`）、修前/修后编译日志、反汇编或 `.s` 片段
  - 本任务书完成区
- **约束**：只改 `components/llvm-project/**` + 本任务书（+ 台账）；**不动** `spec/`、`.tao/contracts/`、`contracts/`、语料；**只补实际被需要的**条目（见验收 2），不得顺手扩成「全部数学 libcall 大表」。

## 最小复现（自包含）

```c
/* /tmp/opencode/LLVM-103t/repro_flog.c */
#include <math.h>
#include <stdio.h>
volatile double x = 2.718281828459045;
int main(void) {
    double y = log(x);              /* ⇒ ISD::FLOG ⇒ libcall */
    printf("y=%.6f\n", y);          /* 期望 1.000000 */
    return (y > 0.999999 && y < 1.000001) ? 0 : 1;
}
```

- 编链口径同 `TESTCASES-048t` 静态档（`clang -target dadao-unknown-elf -nostdinc -I <MUSL>/…` + `ld.lld` + compiler-rt builtins `--start-group`）。
- 修前须复现 `no libcall available for flog`；修后 `qemu-dadao` 打印 `y=1.000000` rc=0。
- 若 f32 面亦被需要：同法加 `float`/`logf` 变体，**不得**只凭猜测添加。

## 验收标准

1. **诊断先落盘**：完成区写「命中的 `LC`（`RTLIB::LOG_F32` / `LOG_F64`，逐例）+ 该 `LC` 在 `initLibcallLoweringInfo` 中的现状 + `ISS-267` 的 f80 表述为何不成立（或成立的反证）」+ 修前报错原文。
2. **最小补齐清单**：逐条列出**实际新增**的 `Info.setLibcallImpl(RTLIB::<X>, RTLIB::impl_<y>)`（含行号与理由——「哪个用例需要」）；**未新增**的同类项也须一句说明（例如「`EXP_*` 未被任何现场例需要 ⇒ 不加」）。禁止无现场依据的批量铺开。
3. **两例转绿（两档）**：`CoMD`、`consumer-lame` 修前 `blocked`（报错原文）⇒ 修后 `pass`（参考 oracle 或 exit-only 判定沿用 `048t` 规则），两档一致。
4. **`TESTCASES-048t` 复跑**：`--only 'CoMD$' --only 'consumer-lame$'` 两档；`blocked 27 → 25`、`pass 193 → 195`、`fail 2`/`known-fail 0`/`excluded 0` **不变**；**无回归**（逐例 JSON diff，类别变化仅这 2 例）。
5. **向量**：新增 lit 用例 PASS，且对**修前**后端 FAIL（可达 FAIL 证据：归档修前 `.s`/报错 或注入）。
6. **可达 FAIL（≥2）**：例如删掉新增的 `setLibcallImpl` 行、把 `impl_log` 改成错误 impl ⇒ 断言/编译失败 ⇒ `cp`+md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）。
7. **门控（各留自身 rc）**：`check-patch-tree`、`check-instrinfo`（若改 `.td`）、`check-component-changelog`、`check-lit_gen`、`make check`(L1)。
8. **`install-host` 前置申报**：改 `components/**` ⇒ **单跑** `install-host`（`JOBS=8`、不并发、`ISS-210`；启动前申报预计耗时），完成后核安装根新鲜并复跑第 3/4 条。

## 不做

- **不做** 全量数学 libcall 家族补齐（`exp`/`pow`/`sin`/`cos`/`log10`… 无现场需求者不加）。
- **不做** `long double` / binary128（`ADR-0030` → `M9`）、f80 支持。
- **不做** `clang` 前端崩溃 2 例（`ISS-267` ①，未派册）、`brind`/varargs（`LLVM-102t`）、`ISS-265`（参考可移植性，待裁）。
- **不改** `spec/`、`.tao/contracts/`、`contracts/`、语料/期望值。

## 硬约束

1. 临时目录 `/tmp/opencode/LLVM-103t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕被检命令自身退出码；长输出落 `.work/log/llvm/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（如「某例需要的是 `EXP_*` 而不只是 `LOG_*`」导致范围变化）时留问。
6. 用户裁定须把**原话**写入本任务书。
7. 补丁导出纪律：`/tmp` 写入、非空 blob、`check-patch-tree` 全绿。

## 完成区
**测试结果**：证据 `./.work/evidence/LLVM-103t/run.sh` default **18 PASS / 0 FAIL（rc=0）**；`--inject` **4 条注入全部转红**（I1 删 `LOG_F64` 注册行 / I2 错符号 / I3 翻 lit CHECK / I4 翻 e2e 期望 ⇒ `y=2.302585`），注入用临时副本、原文件 md5 前后一致（`8475e994…`），收尾复跑 default rc=0。
**修改文件**：① `.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOSubtarget.cpp`（+23 行：L129 `LOG_F64`、L138 `LOG10_F64` + 注释）；② `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOSubtarget.cpp.patch`（`make_patch.py`：1 写 / 77 未变，`series` 仍 78）；③ `components/llvm-project/changelog.md`（+1 条 M8）；④ `tests/llvm/lit/CodeGen/DADAO/p1-fp-libcall-log.ll`（新增，`log`+`log10`）；⑤ `.work/evidence/LLVM-103t/**`（run.sh + probe + results，gitignored）。
**验收结果**：
- **诊断**：`flog` 命中 **`RTLIB::LOG_F64`**（非 f32/f80）：CoMD `random.c`、consumer-lame `psymodel.c` 的 IR 均为 `llvm.log.f64`（`-emit-llvm` 现场）；修前 `LOG_F32` 已注册（L117）、`LOG_F64` 未注册 ⇒ `LegalizeDAG` 报 `error: no libcall available for flog`（048t JSON 原文：`compile error rc=1 on random.c: error: no libcall available for flog`）。`ISS-267`「f80 long double log」不成立：`clang/lib/Basic/Targets/DADAO.h:55` `LongDoubleWidth=LongDoubleAlign=64`。
- **最小补齐**：L129 `RTLIB::LOG_F64 -> RTLIB::impl_log`（CoMD/consumer-lame）；L138 `RTLIB::LOG10_F64 -> RTLIB::impl_log10`（`quantize.c` 在 flog 修后新暴露）。符号 `log`/`log10` 在 musl `libc.a`（`llvm-nm` 有 `T log`/`T log10`）、**builtins archive 0 命中**（非 builtins 归属）；未加 `EXP_*`/`POW_*`/`LOG2_*`/`LOG10_F32`——两程序全部 TU 现场扫描无需求。
- **探针/lit**：`llvm.log.f64` 修前 rc=1 原文 ⇒ 修后 `call [rb0, log]`；`llvm.log10.f64` ⇒ `call [rb0, log10]`；新增 lit PASS、CodeGen 目录 **32/32**。
- **实跑（构建树 clang、`--timeout 300`）**：**CoMD 两档 pass**（参考输出 byte-exact、exit 0）；**consumer-lame 两档仍 blocked**，根因前移为 `timestatus.c` 的 `DADAO: a varargs call with register-exhausted arguments is not supported yet`（`LLVM-102t` 未落地，非 libcall）；两例无其它 `no libcall available`。
- **补丁/构建**：`check-patch-tree` **rc=0、173 补丁（173→173 不变）**；组件树 `HEAD=base+1`、clean；`ninja -C .work/build/llvm clang` **rc=0（245.51 s）**、`llc` relink rc=0（85.6 s）。
- **门控**：`check-instrinfo`/`check_lit_gen`(64/0)/`check-patch-tree`/`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-issues`/`make check`(L1) **各 rc=0**。
**新发现/坑**：① 只 `ninja clang` 不重链 `llc`（静态库已新、exe 仍旧）⇒ lit 读到旧注册表并假报 `no libcall available for flog`；判 lit 前须同建 `llc`。② 任务书「最小复现」的 `volatile double x` + `log(x)` 前端保留 `call log`、不进 libcall 路径；触发 `flog` 需值域可推断（CoMD `rsq∈(0,1]`）⇒ 证据改用 intrinsic `.ll` 探针 + 真实源。③ `install-host` 前安装根仍旧后端，048t 全量数字须安装后复跑。
**遗留问题**：① **未跑** `install-host`/L2/L3/`build-musl*`（派单）；② **未** commit/push、**未改**任务 `**状态**`；③ `consumer-lame` 转绿依赖 **`LLVM-102t`**（varargs），故 `blocked 27→25`/`pass 193→195` 本笔不可达：两档实测 `pass 1/2、blocked 1/2`；④ 全量 222 例未复跑（按派单仅 `--only` 两例）。

## 审阅记录

#### 第 1 轮 engineer 自审
**自审范围**：`DADAOSubtarget.cpp` 两个新增注册（逐行核对枚举↔impl 对应：生成物 `RuntimeLibcalls.inc` L16193 `LOG_F64 -> impl_log`、L16194 `LOG10_F64 -> impl_log10`）、新增 lit `.ll`、证据脚本全文。判决：无遗留代码缺陷；注入自检初版有假绿，已修。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 证据脚本 `local a=$1 b=$W/$a` 在 `set -u` 下报 `name: unbound variable` | ✅已修 | 拆成两行赋值（`asm_check`/`e2e_check`） | default/inject 均跑到结尾 |
| F2 注入自检 I1–I3 期望串与实际串不等（多带 `(FAIL)`）⇒ 被误判红；且 `FAILED=0` 在复跑前清掉了注入失败，可能假绿 | ✅已修 | 改比较数值 rc=1；用 `injfailed` 保存注入结果后再复跑 | inject 日志：I1–I4 全 `expect=1/actual=1 rc=0`、`INJECT OK`，`inject_rc=0` |
| F3 `build-tree-fresh` 用 `ninja -n` 判「no work」，但组件 HEAD amend 触发 VCSRevision 恒脏 ⇒ 无关 FAIL | ✅已修 | 改判 `clang-23`/`llc` mtime 新于源文件 | `CHECK build-tree-fresh … rc=0` |
| F4 任务书最小复现的 `volatile x`+`log(x)` 不触发 libcall（前端保留 `call log`） | ✅已修 | 证据改用 `llvm.log.f64` intrinsic `.ll` + C 驱动 e2e | `e2e-dlog` 0/0/0/0、`y=1.000000` |
| F5 只建 `clang` 后 `llc` 未重链 ⇒ lit 读旧注册表、假报 `flog` | ✅已修 | 同批 `ninja clang llc` | lit PASS、CodeGen 32/32 |
| F6 任务书期望 consumer-lame 转绿，但 `timestatus.c` 变参寄存器耗尽属 `LLVM-102t`（待开始），本册不可修 | ⏸延后 | 未改（越界）；已把「flog→flog10→varargs」链与现场原文写入完成区/证据 | 两档均 `blocked` 且 reason 含 varargs；`json_check … residual` rc=0 |

#### 第 1 轮 reviewer 验收

**重跑记录**：
- default rc=0（18 CHECK 全 PASS）：src-log-f64 / src-log10-f64 / patch-log-f64 / patch-log10-f64 / series-vs-patches(81=81) / check-patch-tree(180) / llc-log / llc-log10 / lit-p1-fp-libcall-log / e2e-dlog(0/0/0/0, y=1.000000) / comd-static(pass) / comd-dynamic(pass) / consumer-lame-static(blocked, varargs) / consumer-lame-dynamic(blocked, varargs) / build-tree-fresh
- inject rc=0（4 注入全红 + originals-untouched + 复跑回绿）：I1 删 LOG_F64→grep miss(1) / I2 wrong-symbol(1) / I3 flipped-FileCheck(1) / I4 wrong-oracle(y=2.302585≠1.000000) / md5 before=after
- check-patch-tree: 180 patches OK（与 050t 同次；LLVM-103t 不增补丁文件）
- `llvm-nm libc.a`：T log / T log10 各 1 命中；builtins 0 命中 ⇒ musl 归属 ✓

**约束核验**：
- 只改 components/llvm-project/** + 本任务书 ✓（未触碰 spec/contracts/语料）
- 补丁纪律：1 写 / 77 未变（series 81，check-patch-tree 180）✓
- 未提交 git / 未 push ✓
- 独立注入：temp copy 删 lit CHECK 中 `call [rb0, log]` → `WRONG_SYMBOL` ⇒ FileCheck rc=1 ✓；原文件 md5 未变 ✓

**特别核查**：
- LOG_F64 真注册：源文件 L129 `Info.setLibcallImpl(RTLIB::LOG_F64, RTLIB::impl_log)` ✓
- LOG10_F64 真注册：源文件 L138 `Info.setLibcallImpl(RTLIB::LOG10_F64, RTLIB::impl_log10)` ✓
- 符号归属：musl `libc.a` 有 `T log` / `T log10`；builtins 0 命中 ✓
- consumer-lame 仍 blocked 根因为 varargs（LLVM-102t），非 libcall 缺口 ✓

**判决**：**Accepted** — 18/18 CHECK 全绿、4 注入全红且还原、约束无违反。

#### 第 1 轮 architect 提交与文件集审核（2026-10-18；**只追加**）
- **档位**：reviewer 第 1 轮**尚无判决**（占位未填）⇒ 流程档位本应 `WIP:`；本笔按派单给定文案**逐字提交**（无前缀）⇒ **如实披露**（同 `INFRA-079t` 先例）。**提交号**：随本条同 commit 落地 ⇒ 不内嵌自身 hash；现场取证 = `git log --oneline -1`。只 `commit`、**未 `push`**；`merge --ff-only` 落地 `master`。
- **文件集对账**（显式 staging 逐个路径，**禁** `git add -A`/`.`）：`M` 本任务书 + `M` `components/llvm-project/changelog.md` + `M` `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOSubtarget.cpp.patch` + `A` `tests/llvm/lit/CodeGen/DADAO/p1-fp-libcall-log.ll` + `M` `.tao/knowledge/milestones.md`（本任务行，architect 台账职责）= 与完成区「修改文件」①–④ **逐条对齐**（`.work/evidence/**` gitignored 不入库）；**无漏提 / 无多提 / 越界 0**（**未**触碰 `tools/testcases/**`、`TESTCASES-*` 册 —— 属并行任务 `TESTCASES-050t`，按路径分笔）。
- **验收面状态**：`**状态**` = `待验收`（待 reviewer 独立重跑）；`consumer-lame` 仍 `blocked` 且根因已前移为变参寄存器耗尽（`LLVM-102t` 待开始）——**本册不因此改判**，`048t` 的 `blocked 27→25 / pass 193→195` 待 `LLVM-102t` 落地后合并作数。
