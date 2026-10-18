# INFRA-089t: musl 端口 `sigsetjmp`（`ISS-254` 归属：musl 端口面，非测试驱动）

**模块**：infra
**项目里程碑**：M8
**依赖**：`TESTCASES-047t`（现场来源 = 静态档 `functional/setjmp` `blocked`：`undefined symbol: sigsetjmp`）、`ISS-254`（本册对应 issue）、`INFRA-082t`（musl 静态最小集移植 = 本册改动面）、`ISS-242`（同信号帧面；取消重定向仍随 `arch/dadao/bits/signal.h` `[OPEN]`）、`contract-syscall §1`（`rt_sigprocmask` 号表）、`ADR-0025 D2`（无内核目标）
**状态**：已验证

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
**测试结果**：`.work/evidence/INFRA-089t/run.sh` default **28/28 PASS**（rc=0）、`--inject` **44/44 PASS**（rc=0）；2 组可达反例（删 `.s` ⇒ `undefined symbol: sigsetjmp`；`br.z→br.nz` ⇒ 探针两支互换 rc=1），均 `cp`+md5 还原后回绿。
**修改文件**：`components/musl/patches/src/signal/dadao/sigsetjmp.s.patch`（新，74 行）+ `series`（18→19）+ `patches/arch/dadao/bits/setjmp.h.patch` + `README.md` + `changelog.md`；`.work/source/musl/{src/signal/dadao/sigsetjmp.s（新）,arch/dadao/bits/setjmp.h}`（amend 进组件单提交 `474a53f`，E1 clean）；本任务书；`.work/evidence/INFRA-089t/{run.sh,repro_sigsetjmp.c,probe_sigmask.c}`。
**验收结果**：① **根因**：`src/signal/sigsetjmp.c` = **0 字节**空槽；`Makefile:23` 的 `ARCH_GLOBS = $(addsuffix /$(ARCH)/*.[csS],$(SRC_DIRS))` 要求 `src/signal/dadao/*.[csS]`，端口无此目录 ⇒ 空 `.c` 编成 **752 B 空对象**（`nm` 无符号）并作为空成员进 `libc.a`，**链接期**才报错；`arch.mak` 排除表为空（非此因）；静态/共享同一缺口。② `make build-musl JOBS=8` rc=0（**12–14 s**，smoke 10/10）、`build-musl-shared` rc=0。③ `nm libc.a`：**1927 → 1929** 个已定义符号，`removed=[]`、`added=[__sigsetjmp,sigsetjmp]`；1349 成员仅 `sigsetjmp.o`（意图）与 `version.o`（`git describe` 环境串）不同。④ `047t` 静态档 `functional/setjmp`：**blocked**（`ld.lld: error: undefined symbol: sigsetjmp`）→ **pass**（exit=0，filter 跑 `total=1 pass=1` rc=0）；12 例样本 **12/12 pass**。⑤ savemask 独立 oracle（由 POSIX/C11 + 语料语义手算）：`A(savemask=1): ret=7 usr1=1 usr2=0 | B(savemask=0): ret=9 usr1=1 usr2=1`（qemu rc=0）；语料 repro `restore=0 norestore=1`。⑥ 门控：`check-patch-tree` **174** patches rc=0、`check-index-blobs` rc=0、`check-source-state`（`HEAD=474a53f count=1 clean=True`）、`check-no-residue`/`check-component-changelog`/`check-musl-freshness`/`check-knowledge-refs` PASS、`check-tasks` rc=0、`make check`(L1) PASS（33 s）；`check-issues` 无独立目标，在 `make check` 内（66 open/26 closed）。
**新发现/坑**：① 0 字节 arch 槽编成空对象不报错 ⇒ 缺 arch asm 只在链接期暴露（诊断看 `nm` 成员）；② `.s` 不过预处理器 ⇒ DADAO asm 拒绝 `/* */`，注释须 `;`（`.S` 才可 C 注释）；③ `call [rb0, setjmp]` 的 REL26 在 `libc.so` 被 lld 本地绑定（无 PLT、不报错），共享档 `setjmp` 内部调用不可被 LD_PRELOAD 插桩；④ runner `CASE_NOTES["functional/setjmp"]`（`tools/testcases/run_libc_test_user_suite.py:361-364`）仍是旧根因，转 pass 后仍打印（文档性、未越界改）。
**遗留问题**：① 全量 `047t` 静态档未重跑（按派单口径：`--only`+nm+12 样本）；按基线 `libc-test-user-050t-static.json`（304/0/9/24）预期 `pass 304→305 / blocked 24→23`，待全量复核；② 上述 runner 陈旧 note 未改（越界，建议并入后续驱动任务）；③ `ISS-254` 未改（任务书要求「验收后」置 `closed`+`resolved_by: INFRA-089t`）；④ 按派单要求**未改任务状态**（保持 `待开始`，交主会话）。

## 审阅记录

#### 第 1 轮 engineer 自审
**改动**：`src/signal/dadao/sigsetjmp.s`（新，68 行）+ `arch/dadao/bits/setjmp.h` 注释（删「sigsetjmp 不提供」段）+ 补丁/`series`/README/changelog。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `savemask` 分支方向/可达性：`br.z` 写反则语义静默错误 | ✅已修 | 反汇编核对 `br.z {rd16}?, [rb0, 32]` 目标 = 0x20（`.Lplain`） | `--inject` B：`br.z→br.nz` ⇒ 探针 `A…usr2=1`、`B…usr2=0`（期望相反）rc=1；还原后回绿 |
| F2 scratch 槽 1288 与 `__ss` 冲突（`__sigsetjmp_tail` 会写 `jb->__ss`） | ✅已修 | 取 `__fl`（1288），`__ss` 起 1296、`_NSIG/8=8` 只写 1296–1303 | 偏移按 `setjmp.h` 结构手算；语料 `memset(&sjb,-1,…)` 路径 pass |
| F3 RAS 一致性：riscv 的 `ra`/`s0` 落栈不能照抄（DADAO `call`/`ret` 由硬件 RAS 管） | ✅已修 | 不落 `ra`；`setjmp` 已存 `ra0..ra63`（含本 `call` 的返回地址），`longjmp` 的 `ret` 弹回本函数 | 依据 `contract-abi §2.3` + 现有 `setjmp.S`；两条返回路径（首返/经 `siglongjmp`）探针均 pass |
| F4 `env` 跨 `call setjmp` 丢失（caller-saved 不可依赖） | ✅已修 | `rb32`（callee-saved）持 `jb`，原值存 1288，返回后重载 | 两次 `siglongjmp` 后 12 例样本 pass；`nm` 符号面无额外 helper |
| F5 `.s` 文件用 `/* */` 注释导致汇编失败 | ✅已修 | 全文件改 `;` 注释（`syscall_cp.s` 同法） | 初版汇编 rc=1（逐行 `unexpected token`）；改后 rc=0 |
| F6 共享档是否因 REL26 指向 default-visibility `setjmp` 而链接失败 | ✅已修 | 无需改：lld 本地绑定 | `build-musl-shared` rc=0；`nm -D libc.so` 三符号；反汇编 `call [rb0,-240]` 已解析 |
| F7 补丁集 E1/E3 与「一文件一补丁」 | ✅已修 | 只改 2 文件 + `git commit --amend`（组件单提交） | `check-source-state` `HEAD=474a53f count=1 clean=True`；`check-patch-tree` 174 |
| F8 证据脚本防造假：断言恒真/`tee` 吞码/注入还原 | ✅已修 | 每条断言独立 rc；计数现场统计；注入用 `cp`+md5，不用 `git checkout` | default 28 PASS / inject 44 PASS；两注入均 rc=1 后回绿 |
| F9 全量 `047t` 静态档未重跑 | ⏸延后 | 按派单口径（`--only`+nm+12 样本） | 预期 `304→305 / 24→23`，已给出基线 JSON 与派生依据 |

**判决**：无未修 finding；F9 为派单口径下的延后项（已在完成区「遗留问题」登记）。任务状态按派单要求保持 `待开始`，交主会话验收。

#### 第 1 轮 reviewer 验收
**重跑（2026-10-18 独立）**：default **28 PASS / 0 FAIL rc=0** ✓；`--inject` **44 PASS / 0 FAIL rc=0** ✓。
- **注入 A**（删 `sigsetjmp.s`）：链接报 `undefined symbol: sigsetjmp`，cp+md5 还原后回绿 ✓。
- **注入 B**（`br.z`→`br.nz`）：探针两支互换（`usr1↔usr2`），cp+md5 还原后回绿 ✓。
**逐条核验**：① `sigsetjmp`/`__sigsetjmp`/`siglongjmp` 三符号 defined ✓；② repro `restore=0 norestore=1` ✓；③ probe oracle `A…usr1=1 usr2=0 | B…usr1=1 usr2=1` ✓；④ 符号增量 `+[__sigsetjmp,sigsetjmp]`、0 removals ✓；⑤ series 含 `sigsetjmp.s.patch`、74 行、非空 blob ✓；⑥ check-patch-tree(180) rc=0 ✓；⑦ check-musl-freshness PASS ✓；⑧ L1 rc=0 ✓。
**约束**：只改 musl patches ✓；一文件一补丁 ✓；series=22（089t+092t 合计）✓；未碰 setjmp/longjmp 帧布局 ✓；未越界。
**如实性抽查**：3 符号 `nm` 确认 ✓；probe output exact match ✓；patch 74 行 + `br.z` 存在 ✓。
**判决**：**Accepted**。

#### 提交留痕（architect，2026-10-18）
- **档位**：正常提交（按主会话派单明示；reviewer 尚未判决）。
- **分支**：`INFRA-089t`（开工自 `master` = `c7b6128`，工作树已含本任务产物）；`commit` 落本分支，**未 `push`**。
- **提交号**：本分支单提交，终态 = `git log --oneline -1`（本段留痕随该提交；留痕前的原始提交为 `4d50790`）。
- **文件集对账**（`git diff --cached --name-only`，9 个路径，显式 staging、未用 `git add -A`）：
  - 完成区「修改文件」声明内（6）：`components/musl/patches/src/signal/dadao/sigsetjmp.s.patch`（A）、`components/musl/series`、`components/musl/patches/arch/dadao/bits/setjmp.h.patch`、`components/musl/README.md`、`components/musl/changelog.md`、`INFRA-089t` 本任务书；
  - **架构师台账笔（派单授权，完成区未声明 ⇒ 属「多提」已披露）**（3）：`.tao/knowledge/milestones.md`（本行 `待开始`→`待验收`+日期+实现摘要）、`.tao/tasks/integ/INTEG-036m-M8-integ里程碑核验.md`（行 + 核验段同步）、`.tao/knowledge/issues.yaml`（`ISS-254` notes 追加 + 新登记 `ISS-270`）；
  - **漏提**：无；**越界**：无（`.work/**` 不入谱）。
- **门控（真实 rc）**：`make check`(L1) **0**（`check_issues` 67 open / 26 closed）、`check-patch-tree` **0**（**174** patches）、`check-source-state` **0**（musl `HEAD=474a53f count=1 clean=True`）、`check-index-blobs`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-syscall-abi`/`check-musl-freshness`/`check_issues.py` 均 **0**；日志 `/tmp/opencode/INFRA-089t/`。
