# INFRA-089t: musl 端口 `sigsetjmp`（`ISS-254` 归属：musl 端口面，非测试驱动）

**模块**：infra
**项目里程碑**：M8
**依赖**：`TESTCASES-047t`（现场来源 = 静态档 `functional/setjmp` `blocked`：`undefined symbol: sigsetjmp`）、`ISS-254`（本册对应 issue）、`INFRA-082t`（musl 静态最小集移植 = 本册改动面）、`ISS-242`（同信号帧面；取消重定向仍随 `arch/dadao/bits/signal.h` `[OPEN]`）、`contract-syscall §1`（`rt_sigprocmask` 号表）、`ADR-0025 D2`（无内核目标）
**状态**：待开始

> **归属说明（二选一裁定：本笔取「单立本册」）**：`ISS-254` 的改动面在 **musl 端口**（`components/musl/patches/src/signal/**`、`arch/dadao/bits/setjmp.h`），不在测试驱动；`TESTCASES-050t` 只做「驱动与口径」，故**不并入** `TESTCASES-050t`。`TESTCASES-050t` 仅在本册交付后按需复跑该例（其册内不承担 `ISS-254` 实现）。

## 执行环境
**执行环境**：本地

## 问题根源

- **现场（逐字）**：`libc-test` 静态档 `functional/setjmp` ⇒ 链接期 `undefined symbol: sigsetjmp`（driver 记 `blocked`，`TESTCASES-047t` 静态档 `blocked 25` 之一）。
- **端口现状（本笔实读）**：
  - `arch/dadao/bits/setjmp.h:29-34` 明写「**sigsetjmp is NOT provided by this port** … a program using sigsetjmp fails to link rather than getting a silently wrong frame」；`__jmp_buf` = **161 octas**（保存 `ra0..ra63` + `rb1` + `rd32..rd63` + `rb32..rb63` + `rf32..rf63`，即全部 callee-saved + 硬件 RAS 快照）。
  - 端口只实现了 `setjmp`/`longjmp`：`components/musl/patches/src/setjmp/dadao/setjmp.S.patch`（`__setjmp`/`_setjmp`/`setjmp` 三个符号）、`longjmp.S`/`longjmp.c`。
  - 上游 `src/signal/sigsetjmp.c` 是 **0 字节**空槽（每个 arch 用自己的 `src/signal/<arch>/sigsetjmp.s` 填）；`src/signal/sigsetjmp_tail.c` 已提供通用 `__sigsetjmp_tail(sigjmp_buf jb, int ret)`（走 `SYS_rt_sigprocmask`，`ret?` 决定 set/restore）。
- **用例要求（本笔实读 `libc-test/src/functional/setjmp.c`）**：`sigsetjmp(sjb, 1)` 后 block `SIGUSR1` 再 `siglongjmp` ⇒ **必须恢复**掩码；`sigsetjmp(sjb, 0)` ⇒ **必须不恢复**。⇒ 不是「链接一下就行」，**savemask 语义必须真**（依赖 `rt_sigprocmask` 在 `qemu-dadao` 下可用）。
- **判定分支（诊断后二选一，不预设）**：
  - **（甲）实现**：新增 `components/musl/patches/src/signal/dadao/sigsetjmp.s.patch`（照 `src/signal/riscv64/sigsetjmp.s` 形态：`savemask==0` ⇒ 直接转 `setjmp`；否则 `call setjmp` 后尾调 `__sigsetjmp_tail(jb, ret)`）。⚠ **DADAO 差异**：`call`/`ret` 由硬件 RAS 管理（`contract-abi §2.3`），riscv 那套「显式保存 `ra`/`s0`」**不能照抄**——须先诊断确认「`sigsetjmp` 返回路径 + `longjmp` 恢复后的 RAS 一致性」（`jmp_buf` 已含 `ra0..ra63` 快照）。
  - **（乙）显式不支持**：仅当诊断证明掩码面在 `M8` 不可达（`arch/dadao/bits/signal.h` 的 `mcontext_t` 仍 `[OPEN]`）⇒ 提供**显式可判失败**形态（**不得**静默桩、不得返回未定义值），并**留问**用户：该例归 `known-fail`/`excluded` 须**用户裁定**（本册**不擅自改标**）。

## 接口规范

- **输入**：
  - `.work/source/musl/`（端口源；`patchless = false`，改动须落 `components/musl/patches/**`）
  - 既有补丁：`components/musl/patches/{arch/dadao/bits/setjmp.h.patch, src/setjmp/dadao/*, series, changelog.md}`
  - 上游参考（**内容溯源，非执行必需**）：同仓 `src/signal/riscv64/sigsetjmp.s`、`src/signal/sigsetjmp_tail.c`
  - 语料：`.work/source/libc-test/src/functional/setjmp.c`（只读）
- **输出**：
  - `components/musl/patches/src/signal/dadao/sigsetjmp.s.patch`（一文件一补丁）+ `series` +1 + `changelog.md` 一条；必要时改 `arch/dadao/bits/setjmp.h.patch` 的 LIMITATION 文字（删「sigsetjmp 不提供」段）
  - 证据：`.work/evidence/<任务号>/run.sh`（default + `--inject`；含 `nm`/符号表断言 + 用例真跑）
  - 本任务书完成区 + `ISS-254` 处置（验收后 `closed` + `resolved_by: INFRA-089t`；乙案则保持 `open` 并写清待裁）
- **约束**：只改 `components/musl/**`（+ 本任务书 + 台账）；**不动** `spec/`、`.tao/contracts/`、`contracts/`、语料；**不**改 `setjmp`/`longjmp` 既有帧布局（161 octas 冻结）。

## 最小复现（自包含）

```c
/* /tmp/opencode/INFRA-089t/repro_sigsetjmp.c：savemask 两支语义 */
#include <setjmp.h>
#include <signal.h>
#include <stdio.h>
int main(void) {
    sigjmp_buf sjb; sigset_t set, cur; int r = 0;
    sigemptyset(&set); sigaddset(&set, SIGUSR1);
    sigprocmask(SIG_UNBLOCK, &set, 0);
    if (!sigsetjmp(sjb, 1)) {
        sigprocmask(SIG_BLOCK, &set, 0);
        siglongjmp(sjb, 1);
    }
    sigprocmask(SIG_SETMASK, 0, &cur);
    int blocked_after_restore = sigismember(&cur, SIGUSR1);   /* 期望 0 */
    if (!sigsetjmp(sjb, 0)) {
        sigprocmask(SIG_BLOCK, &set, 0);
        siglongjmp(sjb, 1);
    }
    sigprocmask(SIG_SETMASK, 0, &cur);
    int blocked_after_norestore = sigismember(&cur, SIGUSR1); /* 期望 1 */
    printf("restore=%d norestore=%d\n", blocked_after_restore, blocked_after_norestore);
    return (blocked_after_restore == 0 && blocked_after_norestore == 1) ? 0 : 1;
}
```

编链：`clang -target dadao-unknown-elf -nostdinc -I <MUSL>/{arch/dadao,arch/generic,obj/src/internal,src/include,src/internal,obj/include,include} -O2 -c` ⇒ `ld.lld -o repro.elf repro.o <MUSL>/lib/crt1.o <MUSL>/lib/libc.a` ⇒ `qemu-dadao repro.elf`；修前须能复现 `undefined symbol: sigsetjmp`。

## 验收标准

1. **诊断先落盘**：完成区写「`sigsetjmp` 缺失面（空槽 + 端口未填）+ savemask 语义依赖（`__sigsetjmp_tail` → `rt_sigprocmask`）+ DADAO RAS 差异（为何不照抄 riscv 的 `ra`/`s0` 保存）」；若走乙案，须给出「掩码面不可达」的**现场证据**（非推理）。
2. **甲案（实现）**：`repro_sigsetjmp` 修前链接失败、修后 `restore=0 norestore=1` rc=0；`functional/setjmp` 静态档 `blocked → pass`；`047t` 静态档 `blocked 25 → 24`、`pass 303 → 304`、`fail 0`/`known-fail 9` 不变（**无回归**，逐例 JSON diff）。
3. **乙案（显式不支持）**：写出「可判失败」的真实形态与用例现场输出；该例**不改标**，并**留问**用户（归 `known-fail`/`excluded` 须裁定）；`ISS-254` 保持 `open`。
4. **独立 oracle**：`restore/norestore` 两支期望值由 `libc-test/src/functional/setjmp.c` 的语义**手算**（savemask=1 恢复、=0 不恢复），不从实现反推；符号面独立断言（`nm`/`llvm-nm` 见 `sigsetjmp` 与 `__sigsetjmp`，`longjmp.c` 见 `siglongjmp`）。
5. **可达 FAIL（≥2）**：① 删 `sigsetjmp.s` 补丁 ⇒ 链接失败；② 把 savemask 分支写反（`==0` 走 tail）⇒ `restore/norestore` 断言红；`cp`+md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）。
6. **门控（各留自身 rc）**：`check-patch-tree`、`check-component-changelog`、`check-musl-freshness`、`make build-musl`（rc=0；**声明预计耗时**）、`make check`(L1)。
7. 完成区（≤30 行）与真实输出逐条对齐；计数由基线 JSON **现场派生**，不写死。

## 不做

- **不改** `setjmp`/`longjmp` 的 161-octa 帧布局、不动 `MemRAS` 已知限制（`bits/setjmp.h` LIMITATION 保留）。
- **不做**取消重定向/信号帧（`ISS-242` 的剩余面、`arch/dadao/bits/signal.h` `[OPEN]`）、线程/TLS（`M9`）。
- **不**改语料、不用「链接到假符号」绕过。
- **不动** `spec/`、`.tao/contracts/`、`contracts/`。

## 硬约束

1. 临时目录 `/tmp/opencode/INFRA-089t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕被检命令自身退出码；长日志落 `.work/log/infra/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；**乙案/改标须用户裁定**时留问。
6. 用户裁定须把**原话**写入本任务书。
7. 补丁导出纪律：`/tmp` 写入、非空 blob、`check-patch-tree` 全绿；一文件一补丁。

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
