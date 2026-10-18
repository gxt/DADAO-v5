# TESTCASES-047t: libc-test 两档用户态跑（静态档 → 动态档）

**模块**：testcases
**项目里程碑**：M8
**依赖**：`QEMU-062t`（`qemu-user` 的 DADAO 后端，**`已验证`**；`qemu-dadao` 在安装根）；`INFRA-082t`（`P1` musl 静态，**`已验证`**）、`INFRA-085t`（`P2` 动态，**`已验证`**）；`TESTCASES-044t`（`libc-test` **取源与锁定**，**`已验证`**；`patchless = true` ⇒ 源只读）、`TESTCASES-045t`（`P1` 能力边界度量，`已验证`；其 `tools/testcases/run_suite.py` 在 `dadao-m1` 路径上已硬失败 ⇒ **本册不复用其运行路径**，只复用其**建链方法论**与排除口径的教训）；`ISS-247`（**链接基址**）、`ISS-246`（**known-fail 唯一依据**）、`ISS-229`（串行）、`ISS-210`（安装根新鲜度）、`ADR-0025`（`D2`/`D6`/`D7`）；**同批三册**：`TESTCASES-046t` / `TESTCASES-047t`（本册）/ `TESTCASES-048t` ⇒ **同改共享文件（`Makefile` / `milestones.md`）⇒ 串行**。
**状态**：待开始
**阶段进度**：静态档 ✅ **fail=0**（**终局复跑（新工具链产物）**（`INFRA-079t` 后、22:44 重建产物）pass 303 / known-fail 9 / blocked 25；`pthread_create-oom` 有 qemu flake）/ 动态档 ✅ **fail=0**（**`TESTCASES-049t` 动态档用户 TU 改 `-fPIC` 后**（2026-10-18）pass **305** / known-fail **9** / blocked **23**：COPY 8 例收 7 例真跑、`math/lgammal` 归 `ADR-0030`；`musl/pleval` 仍 blocked；静态档同版驱动复跑 303 / 9 / 25 **逐例不变**——见 `TESTCASES-049t`）

> **编号（现场取号，2026-10-17）**：现存最大 = `TESTCASES-045t` ⇒ 取 **`047`**；`046` 归同批 `embench-iot` 册；全历史 `grep -E 'TESTCASES-04[678]'` **0 命中**。

## 立项来源 / 用户裁定（原话逐字引录，渠道 = 经主会话问答）

- **2026-10-15**：「**不用改D6，就按原来的顺序进行，然后增加embench和两个新的test suite的测试；测试的时候区分静态链接和动态链接，先测静态链接，再测动态链接**」⇒ 三套 × 两档、**先静态后动态**。
- **2026-10-14**（定源）：「**libc-test: https://github.com/kraj/libc-test**」＋「**三个新组件…可以入锁，libc-test取最新版本即可**」⇒ 源已锁（`TESTCASES-044t`）。
- **2026-10-15**（承接关系）：「**musl移植如果顺利完成的话，可以把新增的两个大型测试集都测完**」⇒ 「全量」由 `P3`（`qemu-user`）承接（`TESTCASES-045t` 收尾裁定）。
- **判据边界**：与 `RISC-V + musl` golden 的对照归 **`P4`**（`ADR-0025 D7`）⇒ **本册不做对照** ✗。

## 目标（两轮，顺序固定：静态档 → 动态档）

1. **第 1 轮 = 静态档**：全部可枚举的独立用例按 **musl 静态**（`crt1.o` + `libc.a`）编链，在 `qemu-dadao` 上跑。
2. **第 2 轮 = 动态档**：同一批用例按 **musl 动态**（`-dynamic-linker /lib/ld-musl-dadao.so.1` + `libc.so`）编链，同法跑。
3. **产出**：逐例结果 + 五类分类 + **`known-fail` 表（按测试名）** + `excluded` 逐条理由 + 覆盖边界声明 + 一键证据（含**可达 FAIL**）。
4. **判据**：用例**自身的判定**（`main` 返回 `t_status`，`t_error` 置非零 ⇒ 退出码非 0 即非通过）；**不**比对 DADAO/LLVM/QEMU 生成的期望值。

## 已核事实（本笔现场；执行时只作复核）

| 项 | 现场值（2026-10-17） |
|---|---|
| 源 | `.work/source/<libc-test>`（锁 `b7ec4679…`，`patchless = true` ⇒ **只读**） |
| 目录 | `src/{api,common,functional,math,musl,regression}`；`src/**/*.c` = **462** |
| 可枚举独立用例（本笔现场派生，**执行期须再派生、不写死**） | **367**（= `.c` + 含 `main` + 排除 `src/common/**` 的 harness support TU）；分布：`math` 225 / `functional` 72 / `regression` 68 / `musl` 1 / `api` 1 |
| `src/common/**` | 7 个 support TU（`fdfill.c`/`memfill.c`/`path.c`/`print.c`/`rand.c`/`setrlim.c`/`utf8.c`/`vmfill.c` 中除 `runtest.c` 外的集合；`runtest.c` 自带 `main` 且依赖 `fork`/`waitpid` ⇒ 不用） |
| 静态档产物 | `.work/source/<musl>/lib/{crt1.o,libc.a,crti.o,crtn.o}`；`libm.a`/`libpthread.a` 等为 **8 字节空归档**（musl 把 math/pthread 合进 `libc.a`）⇒ `-lm`/`-lpthread` 无副作用 |
| 动态档产物 | `.work/source/<musl>/lib/libc.so` + 目标 sysroot `lib/ld-musl-dadao.so.1`（`QEMU-062t` 已用 `-L` 路径） |
| 头文件 | 与 `build_musl.py` 同集合（`arch/dadao`、`arch/generic`、`obj/src/internal`、`src/include`、`src/internal`、`obj/include`、`include`；配 `-nostdinc`） |
| `__thread` 独立用例（本笔现场派生） | **2** 个：`src/functional/tls_init.c`、`src/functional/tls_local_exec.c`（另 3 个 `*_dso.c` 无 `main`，属 DSO helper） |
| `ISS-246` 现场 | clang `DADAO.h` `TLSSupported = false` ⇒ 编 `__thread` 源直接 `error: thread-local storage is not supported for the current target`；后端无 `GlobalTLSAddress` lowering |
| `ISS-247` 现场 | `-T dadao.lds`（`0xFC00_0000_0000`）⇒ `qemu-user` `Unable to find a guest_base…` ⇒ **本册一律 lld 默认基址** |

## 链接与运行口径（自包含；`<...>` 为占位）

- **基址**：**lld 默认**，**禁** `-T tests/scripts/dadao.lds`（`ISS-247`）。
- **编译**：`clang --target=dadao-unknown-elf -nostdinc <musl 头> -std=c99 -D_POSIX_C_SOURCE=200809L -fno-builtin -frounding-math -c <case>.c`（口径 = 上游 `config.mak.def` 减去 glibc-only 与 `-Werror=` 族；**不得**把 warning 当 build error）。
- **静态档链接**：`ld.lld -o <case>.elf <musl>/lib/crt1.o <case>.o <common 所需 support .o> -L <musl>/lib -lc`。
- **动态档链接**：同上 + `-dynamic-linker /lib/ld-musl-dadao.so.1`（`-lc` 取 `libc.so`）。
- **运行**：静态 `qemu-dadao <case>.elf`；动态 `qemu-dadao -L <target-sysroot> <case>.elf`；每例 `timeout`（默认 60 s，`124` ⇒ `blocked`）。
- **驱动**：`--link-mode static|dynamic` 显式二选一；**两档顺序执行**（static 全量 → 报告 → dynamic）。
- **`excluded` 口径的界线（重要）**：`tools/testcases/run_suite.py` 的既有 `EXCLUDED` 清单是**裸机模型**（无内核）的产物（`fork`/`waitpid`/信号/`select`/socket/SysV IPC…）。`qemu-user` **把 syscall 直通宿主** ⇒ **不得**照搬该清单；只有**结构性**不可用者才 `excluded`（如：无 `main` 的上游 harness helper / DSO 伴生 TU；C++/Fortran 源；需要 `/proc`、网络、`dlopen` 而 M8 明确不支持的用例——**最后这条须现场判定并逐条给 reason**，不得预判为通过或跳过）。

## 失败分类（计数运行期派生，禁写死）

| 类 | 定义 | 判定后果 |
|---|---|---|
| `pass` | 编链成功 + 退出码 `0`（用例自身 `t_status == 0`） | 计入 pass |
| `fail`（**真失败**） | 编链成功 + 退出码非 `0`，且**不能**归因到 `known-fail` 依据 | 计入 fail |
| `known-fail` | 失败**可逐条归因**到 `ISS-246`（`__thread`） | 单列，**不计 pass** |
| `blocked` | 编链失败 / 缺符号 / 后端或链接器缺口 / `qemu` 崩 / `timeout` | 计入 blocked；**`blocked>0 ⇒ 本档 rc=1`**（`ISS-248` 口径） |
| `excluded` | **开工前**声明、结构性范围外，逐条 reason + 现场计数 | 唯一 skip 通道 |

### `known-fail` 表（**按测试名逐条列出**；本册唯一依据 = `ISS-246`）

**表的生成方式（机械、可复核，禁人肉猜）**：

1. 运行期对**全部可枚举用例**做源码扫描：`grep -l '__thread\|_Thread_local\|thread_local'`（现场须打印命中清单与计数）；
2. 命中且**实际失败**的用例进表；命中但**通过**的不进表（如实记录「命中但 pass」）；
3. **未命中 `__thread` 的失败一律 `fail`** —— 不得因为「可能和 TLS 有关」而入 known-fail；
4. 若某用例既含 `__thread` 又失败于其它原因（如缺符号 / 编译参数），按**实际首错**归类：能归 `__thread` 才入表，否则 `fail`。

**表格式（完成区/报告内逐条，禁汇总成一行）**：

| 测试名（`src/...`） | 症状（逐字首错行） | 归因依据 | 分类 |
|---|---|---|---|
| `<case id>` | `<error: thread-local storage is not supported for the current target>` 等 | `ISS-246`（+ 依据行号/证据指针） | `known-fail` |

**本笔现场预期**：`__thread` 独立用例 = **2**（`src/functional/tls_init.c`、`src/functional/tls_local_exec.c`）；执行期以现场扫描为准，**若为 0 或 >2 须如实记录差异并说明原因**（源锁定，正常应同值）。

## 接口规范

- **输入**：`.work/source/<libc-test>`（只读）、musl 静态/动态产物、`qemu-dadao`。
- **输出**：① 驱动（入 git，建议 `tools/testcases/run_suite_user.py`）；② 逐例 JSON/CSV + 报告（落 `.work/log/testcases/`）；③ `.work/evidence/<任务ID>/run.sh`（非交互、任一失败非零、含可达 FAIL）；④ 可选 `Makefile` target（**不入** L1/L2/L3，理由同 `TESTCASES-045t`）；⑤ 完成区 + 报告摘要（含 `known-fail` 表）。
- **约束**：不改 `.work/source/**`（`patchless`）；不改 `spec/`、`.tao/contracts/`、`contracts/`、`components/**`；`--inject` 注入用 `cp` + md5 还原。

## 验收标准

1. **两档顺序正确且各自完整**：static 轮先跑完、dynamic 轮后开始；两档各自 rc、total/pass/fail/known-fail/blocked/excluded 六数（现场派生）。
2. **枚举封闭**：`执行集 == 枚举集`（枚举 = 运行期 glob + `main` 判定 + `src/common/**` 排除）；少一个即 FAIL；**不得**只跑 curated 子集冒充全量（如为控时拆批，须在报告中写明批次划分与理由，且**每批都跑**）。
3. **基址 = lld 默认**：每档 ≥1 例 `readelf -l` / `llvm-readobj` 现场输出，证明最低 `PT_LOAD` ≠ `0xFC00_0000_0000`；命令留证（无 `-T dadao.lds`）。
4. **两档形态可核**：静态档**无** `PT_INTERP`；动态档**有** `PT_INTERP = /lib/ld-musl-dadao.so.1` 且给出 `ldso` 真跑证据（成功用例的 `AT_BASE`/装载可观察证据或等价现场）。
5. **`known-fail` 表合规**：按测试名逐条；每条含症状**逐字首错行** + `ISS-246` 依据 + 现场扫描清单与计数；**无**「非 `__thread` 失败被归入 known-fail」的条目（须可核：给出的扫描输出能覆盖表内每一条）。
6. **分类可信**：`fail` 逐条含命令 + 首错行；`excluded` 逐条 reason（并说明为何**结构性**而非「没跑」）；`blocked` 逐条含根因指针（缺符号名 / 链接错误 / timeout 秒数）。
7. **可达 FAIL**：注入 1 例期望值错误（或错判 1 条 `known-fail`）⇒ 驱动 rc=1 且恰该例报 `FAIL`；`cp` + md5 还原 ⇒ 回绿（三态输出留证）。
8. **不回归**：既有 `picolibc-tests` 门控（L2）rc=0、`make check`(L1) rc=0；`check-patch-tree` **预期 177**（本册不改组件）。
9. **报告与覆盖边界**：明写「哪些用例不在本次枚举范围（如非 C 后缀、无 `main` 的 helper、`External/**` 类）」+ 各自现场计数；**不得**把子集表述为「全量通过」。
10. **前置申报**：开工前申报预计耗时；如需 `make install-host` ⇒ 申报 **≈5 min**、`JOBS=8`、**不并发**、改后必须跑（`ISS-210`）；本册预期不改组件 ⇒ 只核安装根新鲜度。
11. **完成区 ≤30 行**，与真实输出逐条对齐；长输出落 `.work/log/testcases/`。

## 判据边界（本批**不做** ✗）

- **不做** `ISS-246`（`__thread`）修复 ⇒ 归 **`LLVM-100t`**；本册只以其为 `known-fail` 依据。
- **不做**与 `RISC-V + musl` golden 对照 ⇒ 归 **`P4`**（`ADR-0025 D7`）。
- **不做** `dlopen` / TLS 动态重定位（`D2` 已推迟 `M9+`）的**能力补齐**；撞上即按分类登记。
- **不做**改 `tests/scripts/dadao.lds`（须用户授权）、不改组件 / `spec/` / 契约。
- **不做** `embench-iot` / `llvm-test-suite`（各自独立成册）。

## 硬约束

1. 临时目录 `/tmp/opencode/TESTCASES-047t/`；命令在 workdir 内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不用** `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原（一律 `cp` + md5）。
3. **只动**：`tools/testcases/**`、`Makefile`（可选）、`.work/**`（gitignored）、本任务书、`milestones.md`（如需）。**不动** `spec/` / `.tao/contracts/` / `contracts/` / `components/**` / `.work/source/**`。
4. 完成区与真实输出逐条对齐；**禁** `cmd | tail` 接进 `&&`、**禁** `cmd | tee` 吞码。
5. **不提交**（提交权归 architect）；用户裁定须把**原话**写入本任务书。
6. **失败保留现场并继续推进**（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定**时留问。
7. 长任务（单档预计 >10 min）⇒ `setsid nohup` + 落 `XXX_EXIT=$rc`，**不在会话内等待**；**一次只跑一档**。
8. 与 `TESTCASES-046t`/`048t` 同改 `Makefile`/`milestones.md` ⇒ **串行**。

## 完成区
**测试结果**：静态档（`qemu-dadao`、lld 默认基址、显式 `<musl>/lib/libc.a`）现场派生 **discovered=367 / excluded=30 / executed=337：pass=299、fail=10、known-fail=3、blocked=25**；driver rc=1（`blocked>0 ⇒ 非零`，`ISS-248` 口径）。证据脚本默认 rc=0、`--inject` rc=0（3 处注入同次前台闭合，driver 末态 md5 `3e3feceebedd2f0bbd02984cf3ae6e25`）。动态档未跑（下一笔）。
known-fail（3 条；唯一依据 `ISS-246`；现场 TLS 扫描 3 命中 / 0「命中但 pass」）：
| 测试名（`src/...`） | 症状（逐字首错行） | 依据 |
|---|---|---|
| `functional/tls_init.c` | `tls_init.c:4:1: error: thread-local storage is not supported for the current target` | `ISS-246`①（clang `DADAO.h` `TLSSupported=false`） |
| `functional/tls_local_exec.c` | `tls_local_exec.c:6:8: error: thread-local storage is not supported for the current target` | `ISS-246`① |
| `functional/tls_align.c` | 同诊断，来自上游 `.mk` 静态档联入的 `tls_align_dso.c:1:1` | `ISS-246`① |
fail（10；逐例首错行 + 链接命令见 `.work/log/testcases/libc-test-user-static.log`）：**A 组 4 条同根因**（musl 端口 `__dadao_argmask` 只列 12 个 syscall ⇒ 指针参数落 rd 银行）：`ipc_msg`（`ipc_msg.c:60: qid_ds.msg_perm.mode & 0x1ff == 0666 failed: got 0, want 666`）、`ipc_sem`（`ipc_sem.c:58: semctl(...IPC_STAT...) failed: Bad address`）、`ipc_shm`（`ipc_shm.c:57: ...mode ... got 0, want 666`）、`socket`（`socket.c:29: sendto(...)==1 failed: errno = Invalid argument`）；**B 组 5 条**（`LDBL_MANT_DIG=53`，`_l` 实现在语料 double 向量上偏 1.5–10 ulp）：`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`；**C 组 1 条**：`strptime`（musl `%s` 对 `tm` 无效果，`src/time/strptime.c:133-139`）。
blocked（25）：**`__clone` 缺口 20 条**（18 条线程用例 + `popen`/`spawn` 经 `posix_spawn→__clone` 得 `ENOSYS`；端口 `src/thread/clone.c` 返回 `-ENOSYS`、无 `clone.s`，`INFRA-082t` 单线程边界）；`setjmp`（`undefined symbol: sigsetjmp`，`INFRA-082t` 遗留⑧）；`tgmath`（`undefined symbol: __muldc3`：链接行无 compiler-rt builtins，补 `.work/build/compiler-rt-builtins/lib/linux/libclang_rt.builtins-dadao.a` 实测 exit=0）；`mbsrtowcs-overflow`（musl `typedef int wchar_t` vs clang `__WCHAR_TYPE__=unsigned int`）；`regression/{flockfile-list,setenv-oom}`（qemu 宿主 SIGBUS/SIGTRAP）。
excluded（30；逐条 reason 见 stdout/JSON）：26 = `src/math/gen/**`（上游只构建 `src/*/*.c`；该树是"测试生成器" + `___` 模板）；4 = dlopen 依赖（`functional/dlopen.c`、`tls_align_dlopen.c`、`tls_init_dlopen.c`、`regression/tls_get_new-dtv.c`；静态镜像无装载器，`ADR-0025 D2`）。
**修改文件**：`tools/testcases/run_libc_test_user_suite.py`（新驱动；`--link-mode static|dynamic` 必选，无默认）；gitignored：`.work/evidence/TESTCASES-047t/run.sh`、`.work/log/testcases/libc-test-user-static.json`、`.work/log/testcases/libc-test-user-static.log`、`.work/log/testcases/libc-test-user-static.stdout`、`.work/log/testcases/libc-test-user-static.stderr`、`.work/log/testcases/TESTCASES-047t-evidence.log`、`.work/tmp/TESTCASES-047t/`、`.dadao/tests/libc-test-user/`；本任务书。
**验收结果**：① 基址/形态：331 张 ELF 全部 `min PT_LOAD=0x10000`（唯一值 ≠`0xFC00_0000_0000`）、`PT_INTERP`=0、`PT_DYNAMIC`=0；337 条 link 行全含 `lib/libc.a`、无 `-T`/`dadao.lds`/`-dynamic-linker`。② 独立 oracle：判据 = 语料自身 `t_error→t_status→main`（非从 LLVM/QEMU 反推）；重放 `argv`/`sin`/`pleval`=exit 0，真失败对照 `ipc_msg`=exit 1 且打印自身断言行。③ `--inject`：期望退出码 0→1 ⇒ `argv` 判 FAIL、rc=1；中和门控（fail>0 仍 rc=0）⇒ `ISS-248` 规则判 violation；把 `tls_init` 记录改标 pass ⇒ 审计 per-case invariant 拒绝；三处 `cp`+md5 复原（`3e3fecee…`）。④ 门控（各自 rc）：`validate-vectors` 0、`check-no-residue` 0、`check-tasks` 0、`check-knowledge-refs` 0、`check-component-changelog` 0、`tools/infra/check_issues.py` 0、`check-patch-tree` **177**（rc=0）；`make check`(L1) **最终 rc=0**（16:37 并行窗口内曾 rc=2，唯一失败项 = 并行新增 `check-contracts-pending` 报 5 条既有 `.tao/contracts/**` `[待定]` 缺指针；该批契约陈旧已由 `INFRA-086t`/`9389210` 清理，复跑 rc=0）；未跑 L3/`install-host`/`build-mc|lld|qemu`/`build-musl`（`libc.a` 13:49 ≥ musl 源 mtime，证据脚本已核新鲜）。⑤ 耗时：全量静态档 509 s；证据脚本 default/`--inject` ≈9–11 min。
**新发现/坑**：① 静态档必须显式 `lib/libc.a`（同目录 `-lc` 选 `libc.so`），同 `TESTCASES-046t`。② `-g` 在本 target 全不可用（DWARF 4 字节重定位被汇编器拒：`relocatable operand in a 1/2/4-byte data field`）⇒ 上游 CFLAGS 的 `-g` 须剔除。③ `__dadao_argmask`（`arch/dadao/syscall_arch.h:63`）覆盖不足 ⇒ 4 条 fail 同根因；`wchar_t` 有符号性冲突（1 条 blocked）。④ 端口无 `clone.s` ⇒ 线程/`posix_spawn`/`popen` 全不可用（20 条 blocked）。⑤ compiler-rt builtins 只在 `.work/build`（未安装）⇒ `_Complex` 乘法链接失败。⑥ 上游 `src/math/gen/**` 不在上游构建集；任务书 367 的递归口径含其 26 个文件，本册按 excluded 逐条列。⑦ 同树曾有两实例并发跑同一 driver（互 rmtree 用例目录）⇒ 现证据脚本带并发守卫 + 隔离 `--work-dir`。
**遗留问题**：动态档（`--link-mode dynamic` 已实现、**未执行**，下一笔）；`P4` golden 对照、`ISS-246` 修复不在本册。**待架构裁定**：blocked=25（是否登记 issue：musl `__clone`/argmask/`wchar_t`、compiler-rt 安装）与 fail=10（argmask 同根因 4 / long-double 5 / strptime 1）。无阻塞项。

### 第 2 轮（`ISS-249` 收口后按册重跑，2026-10-17 engineer）

**测试结果**：静态档重跑（`qemu-dadao` = **`.work/build/qemu/` 新构建**，未跑 `install-host`；`libc.a` 由 `make build-musl` 重建）⇒ discovered 367 / excluded 30 / total 337：**pass 301、fail 8、known-fail 3、blocked 25**（driver rc=1，`blocked>0` 按 `ISS-248` 口径）。对照首轮 **pass 299 → 301、fail 10 → 8、无回归**（原 299 条 pass 全在）。fail 8 逐条归属：`ipc_sem`（`semctl` 的 `union semun` 可变参未送达 = codegen 缺陷，**新发现**）、`ipc_shm`（mode 断言已过，卡 `shmdt(p)`：`shmat()` 指针返回值未落 `rb8`，**新发现**）、`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`（`ADR-0030` → M9 binary128）、`strptime`（`ISS-251`，本笔范围外）；`ipc_msg`、`socket` 转 pass。blocked 25 分类同首轮（20 线程/`posix_spawn` → `ISS-252`/M9；`setjmp` → `ISS-254`；`tgmath` → compiler-rt；`mbsrtowcs-overflow` → `ISS-253`；2 条 qemu 宿主信号 → `ISS-255`）。
**修改文件**：`components/musl/patches/{arch/dadao/syscall_arch.h,src/thread/dadao/syscall_cp.s}.patch`、`components/musl/changelog.md`；`components/qemu/patches/linux-user/dadao/cpu_loop.c.patch`、`components/qemu/changelog.md`；`tools/qemu/check_syscall_abi.py`（三载体逐项对账 + 完整性 + mask 块搬运数）、`Makefile`（`check-syscall-abi`，L1）、`docs/Process-07-门控分层规范.md`（§1.1 登记一行）、`.tao/knowledge/issues.yaml`（`ISS-249` 处置）；gitignored：`.work/evidence/ISS-249/{run.sh,repro.c}`、`.work/log/testcases/ISS-249-static.json`（同目录另有 `.report` 改名前的日志 + `.stdout`/`.stderr`）、`/tmp/opencode/ISS-249/`。
**验收结果**：① 三载体一致：`make check-syscall-abi` **69/69** rc=0（guest/host 各 **245** 条、asm **41** 号 / **16** mask 类，逐项掩码全等、块搬运数 = 掩码位值）。② 功能：guest 复现 `-strace` 实测 `sendto(...,16)=1`、`recvfrom(...,ptr)=1`、`msg mode=666`、`shm mode=666`（修复前分别 `EINVAL`/`EFAULT`/`0`/`0`）。③ 可达 FAIL：`.work/evidence/ISS-249/run.sh` 3 处注入（host mask `0x32→0x02`、guest 丢一条 case、asm 块少一条 `rd2rb`）逐一 `[FAIL]` ⇒ `cp`+md5 还原 ⇒ 回绿，脚本 **rc=0**。④ 门控（各自 rc）：`check-patch-tree` 0（**177** 补丁 / 5 组件）、`check-index-blobs` 0、`check-source-state` 0、`check-no-residue` 0、`check-tasks` 0、`check-knowledge-refs` 0、`check-component-changelog` 0、`check_issues.py` 0、`check-syscall-abi` 0、`make check`(L1) **rc=0**。⑤ 耗时：静态档重跑 508 s；musl 增量构建 ~10 s、qemu 增量构建 ~6 s。
**新发现/坑**：① 两条**函数调用 ABI 面的独立 codegen 缺陷**（与 argmask 无关，须 LLVM 侧处置）：(a) `union` 作可变参时调用侧放 rb、`va_arg` 侧按间接读 ⇒ `semctl(IPC_STAT, arg)` 的 `arg.buf` 读成 0（`ipc_sem`）；(b) 指针返回经 `syscall()`（宏 → `__syscall_ret` 尾调用）时未落 `rb8`（`contract-abi §4.4`），`shmat()` 返回值丢失（`ipc_shm`）。② 首轮「4 例同根因」仅对 `socket` 成立；`ipc_msg`/`ipc_shm` 的 mode 位宽问题属大端 `ipc_perm` 布局，用 musl 既有 `SYSCALL_IPC_BROKEN_MODE` 补偿。③ `build-musl` 走工具链戳增量，改 `arch/dadao/*.h` 后须核受影响对象确实重建（本次核过 `shmdt.o`/`sendto.o` mtime > 头文件）。
**遗留问题**：动态档未跑（按册下一笔）；`ipc_sem`/`ipc_shm` 两条新发现 **待 architect 立项**（本笔不擅自开号）；`long double` 5 条随 M9（`ADR-0030`）；`strptime` 归 `ISS-251`；未跑 `install-host`（重跑用 `.work/build/qemu/qemu-dadao`，安装根仍是旧二进制）。

### 第 3 轮（安装根复跑 + `ISS-251` 归口，2026-10-17 engineer）

**测试结果**：安装根（`.dadao/cross-toolchain/bin/{clang,ld.lld,qemu-dadao}`；`make build-musl` 戳记变更 ⇒ clean 全编 10.3 s）复跑静态档 ⇒ **discovered 367 / excluded 30 / total 337：pass 303、fail 5、known-fail 4、blocked 25**（driver rc=1，`blocked>0` 按 `ISS-248`）。对照第 2 轮 `301/8/3/25` 与安装根首跑 `303/6/3/25`：`fail 6→5`（`strptime` → `known-fail`，依据 `ISS-251`）、`known-fail 3→4`、`pass` 303 不变（原 303 条全在）。**flaky 披露**：`regression/pthread_create-oom` 在一次全量中记 pass（304/24），随后 5/5 套件 pilot + 8/8 单跑均 BLOCKED（guest `setrlimit(RLIMIT_AS)` 直通宿主 ⇒ QEMU `SIGTRAP`/GLib 分配失败）；未改标签，同类 `ISS-255`。
**known-fail（4 条，逐例依据）**：`functional/strptime` = `ISS-251`（musl `src/time/strptime.c:133-139` parse-only + 语料 `:112` 调用点 + 该例 `%s` 诊断）；`functional/tls_align`/`tls_init`/`tls_local_exec` = `ISS-246`（live TLS 扫描命中 + clang 诊断，均无 ELF/exit）。
**fail（5 条）**：`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`，全部 `ulperr` 诊断、`LDBL_MANT_DIG=53` ⇒ 按 `ADR-0030` 归 `known-fail` 口径、**M9 binary128 实施后消失**（runner 标签仍 `fail`：`INFRA-087t` 准入仅 `ISS-246`/`ISS-251`）。**blocked 25** 归属不变（`ISS-252`/`ISS-253`/`ISS-254`/`ISS-255`/compiler-rt）。
**修改文件**：`tools/testcases/run_libc_test_user_suite.py`（`known-fail` 逐例依据表 + 反向校验；`CASE_NOTES["functional/strptime"]`；JSON 增 `known_fail_basis`/`known_fail_evidence`）；`.tao/knowledge/issues.yaml`（`ISS-251` 处置）；`.tao/tasks/infra/INFRA-087t-strptime语义归属与分类.md`；本任务书；gitignored：`.work/evidence/{TESTCASES-047t,INFRA-087t}/run.sh`（047t 审计扩 `ISS-251`）、`.work/log/testcases/INFRA-087t-*.log`。
**验收结果**：① 安装根新鲜度：clang/lld/llvm-mc md5 == `.work/build/llvm/bin/*`、qemu-dadao == `.work/build/qemu/`；mtime ≥ 最新补丁。② `./.work/evidence/INFRA-087t/run.sh --inject` rc=0（独立审计对 JSON 复算；2 注入可达 `[FAIL]` + `cp`/md5 回绿）。③ 门控：`check-patch-tree` 0（177）、`check-syscall-abi` 0（69/69）、`check-index-blobs` 0、`check-source-state` 0、`check-no-residue` 0、`check-tasks` 0、`check-knowledge-refs` 0、`check-component-changelog` 0、`check_issues.py` 0、`make check`(L1) 0。④ 语料只读自证：`git -C .work/source/libc-test status --porcelain -uall` 0 行。⑤ 未跑 `install-host`/L2/L3；未提交。
**遗留问题**：动态档未跑；`ISS-251` 待 reviewer 验收后由主会话置 `closed`；`long double` 5 条随 M9（`ADR-0030`）。

### 第 4 轮（`long double` 5 条并入 `known-fail`，2026-10-17 engineer）

**测试结果**：安装根复跑静态档 ⇒ **discovered 367 / excluded 30 / total 337：pass 303、fail 0、known-fail 9、blocked 25**（driver rc=1 仅因 `blocked>0`）。对照第 3 轮 `303/5/4/25`：`fail 5→0`、`known-fail 4→9`，`pass`/`blocked` 不变。`known-fail` 9 = `ISS-246` 3（TLS）+ `ISS-251` 1（`strptime %s`）+ **`ADR-0030` 5**（`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`，`ulperr` 精度类；ADR `Accepted` 2026-10-17、`D1` binary128、`D7`→M9；target `LDBL_MANT_DIG=53` 现场事实）。
**修改文件**：`tools/testcases/run_libc_test_user_suite.py`（`adr0030_evidence` + 依据表第 3 行 + 反向校验/未分类 `fail` 拒绝）；`.tao/knowledge/issues.yaml`（`ISS-250` notes 追加，`status` 保持 `open`）；`.tao/tasks/infra/INFRA-087t-...md`（第 3 轮）；本任务书；gitignored：`.work/evidence/INFRA-087t/run.sh`、`.work/log/testcases/INFRA-087t-*.log`。
**验收结果**：`./.work/evidence/INFRA-087t/run.sh --inject` rc=0（含新增注入 C：禁用 ADR 准入 ⇒ `[FAIL] unclassified failure(s) remain`；`cp`+md5 还原回绿）；门控各 rc 见 `INFRA-087t` 完成区第 3 轮。未跑 `install-host`/L2/L3；未提交。
**遗留问题**：动态档未跑；`ISS-250` 保持 `open`（M9 后复核关闭）；`ISS-251` 待收尾。

### 第 5 轮（动态档全量，2026-10-17 engineer）

**测试结果**：动态档全量（安装根 `qemu-dadao`；lld 默认基址；`libc.so` + `-dynamic-linker /lib/ld-musl-dadao.so.1`）⇒ **discovered 367 / excluded 30 / total 337：pass 298、fail 0、known-fail 8、blocked 31**（driver rc=1 仅因 `blocked>0`，`ISS-248`）。静态档用同版驱动复跑 ⇒ **303/0/9/25**（与第 4 轮一致；首跑一次 `malloc-oom` 被 qemu 宿主 `SIGTRAP` 打掉，单跑 3/3 pass、整轮重跑复现 303，按 `ISS-255/257` 类 flake 记录）。**动态档 rc/耗时**：9 min 29 s（静态 8 min 29 s；证据脚本 default/`--inject` ≈ 1 min）。
**静态→动态逐例变化（12 条，无 pass→fail / fail→pass）**：`pass→blocked` 8 = `functional/env`（`environ`）、`math/{lgamma,lgammaf}`（`signgam`）、`regression/{fflush-exit,fgetwc-buffering,rewind-clear-error,setvbuf-unget}`（`stdout`/`stdin`）7 条 **COPY 重定位**（非 PIC 可执行文件引用 libc 数据对象 ⇒ lld 显式拒绝，`ADR-0026 D7②` / `contract-dynlink §10②`）+ `musl/pleval`（`__pleval` 为 musl hidden 内部符号，`libc.so` 不导出；上游 `pleval.mk` 明写动态档不构建）；`known-fail→blocked` 1 = `math/lgammal`（同为 `signgam` COPY）；`blocked→pass` 3 = `functional/tgmath`（真增益：`libc.so` 链入 compiler-rt builtins，`cpow` 的 hidden `__muldc3` 在库内解析）+ `regression/{setenv-oom,pthread_create-oom}`（**OOM 类 flake**，static 为 blocked，不计真增益）。
**known-fail（8 条，逐例依据）**：`ISS-246` 3（`tls_align`/`tls_init`/`tls_local_exec`；现场 TLS 扫描命中 3 / 0「命中但 pass」）、`ISS-251` 1（`strptime`，musl `%s` parse-only）、`ADR-0030` 4（`math/{acoshl,asinhl,erfcl,tgammal}`，`ulperr` + `LDBL_MANT_DIG=53`；`lgammal` 因 COPY 改记 blocked）。
**blocked 31 归属复核（`ISS-252/253/254/255` 仍成立 + 新形态 2 类）**：`ISS-252` 19（17 线程用例 + `popen`/`spawn` 经 `__clone → ENOSYS`）、`ISS-254` 1（`setjmp`，`undefined symbol: sigsetjmp`）、`ISS-253` 1（`mbsrtowcs-overflow`，`wchar_t` 有符号性）、`ISS-255` 1（`flockfile-list`，宿主 `SIGBUS`）、**COPY 8**（上述）、**`pleval` 1**（hidden 符号）。**新形态**：动态档独有 = COPY 链接期拒绝（已由 `ADR-0026 D7②` 声明，非缺陷；`-fPIC` 同一用例 `functional/env` 实测 link rc=0 / guest exit 0，证据脚本已固化）与 hidden 内部符号（非缺陷）。
**驱动修正（影响两档，静态已复跑证不回归）**：`MUSL_USER_INCLUDE_DIRS` 改为**公共头集合**（`arch/dadao`/`arch/generic`/`obj/include`/`include`）。旧集合把 musl 内部 `src/include` 排在前面 ⇒ 用户 TU 的 `errno` 绑定到 `___errno_location`（`libc.a` 有定义、`libc.so` 为 LOCAL HIDDEN）⇒ 静态可链、动态 `undefined hidden symbol`（首轮 pilot 已现，修后 `ipc_*`/`socket`/`setenv-oom` 等不再误 blocked）。另：`DYNAMIC_EXCLUSION_REASONS`（4 条 dlopen 用例的动态档 reason，静态措辞不再复用）、`MODE_CASE_NOTES[("dynamic","musl/pleval")]`。
**验收结果**：① 形态：323 张 ELF 全部 `min PT_LOAD=0x10000`、`PT_INTERP=/lib/ld-musl-dadao.so.1`；323 条 link 行全含 `-dynamic-linker` + `lib/libc.so`、无 `-T`/`dadao.lds`。② loader 真跑：`tests/scripts/dadao_user_dyn_probe.c` ⇒ `AT_BASE=0x790c20250000`（≠0、页对齐）、`AT_ENTRY`/`AT_PHNUM`/`AT_PHENT` 与 ELF 头逐项相等、`/proc/self/maps` 命中 `ld-musl-dadao.so.1`；**dlopen 现场**：简单非 TLS DSO（`dlopen_dso.so`）实测 `dlopen/dlsym` **exit 0** ⇒ 4 条 dlopen 用例的 excluded 是 **M8 范围裁定**（`ADR-0025 D2`/`INFRA-085t ⑦`）+ 驱动不建 DSO helper，**不是**装载能力不足（如实记，供 M9 收编）。③ 独立审计（`cp`+md5，非 driver 汇总）：六数与 JSON 逐项相等、census 433/462/26 现场复算、逐例不变量 337 条 PASS。④ 证据脚本 `.work/evidence/TESTCASES-047t-dyn/run.sh`：default **68 PASS / rc=0**；`--inject` **rc=0**（I1 期望退出码 0→1 ⇒ `functional/argv` 判 FAIL、driver rc=1；I2 known-fail 改标 pass ⇒ audit 拒；I3 清空 `PT_INTERP` ⇒ 形态不变量拒；三者 `cp`+md5 还原，driver md5 `d2fbab33…`、JSON md5 `cf8ee211…`）。
**修改文件**：`tools/testcases/run_libc_test_user_suite.py`（公共头集合、动态档 exclusion reason、pleval note）；本任务书；gitignored：`.work/evidence/TESTCASES-047t-dyn/run.sh`、`.work/log/testcases/{libc-test-user-dynamic.{json,log,stdout,stderr},libc-test-user-static.{json,log,stdout,stderr},047t-dyn-evidence*.log}`、`.work/tmp/TESTCASES-047t-dyn/`。
**遗留问题**：动态档 8 条 COPY 用例（非 PIC 用户可执行）在 `ADR-0026 D7②` 下不可链；`-fPIC` 可绕（实测），是否把动态档用户编译改为 `-fPIC`/`-pie` 属口径决策（**待架构裁定**，本笔不改）。`pleval` 动态档按上游 `.mk` 本不应构建，本驱动保留执行以维持两档同一枚举集（记 blocked）。OOM 三条（`malloc-oom`/`setenv-oom`/`pthread_create-oom`）宿主侧不稳定（`ISS-255/257`）。



### 终局复跑（`INFRA-079t` 后端 + `libc.so` 重建后，2026-10-17 22:12–22:41）

**测试结果**：按派单**只跑测**（未改 `musl`/`LLVM`/`QEMU` 源码、未动 `Makefile`、未 `install-host`），顺序 static → dynamic、逐组落日志（`.work/log/testcases/final-rerun/`）：静态 **discovered 367 / excluded 30 / total 337：pass 303、fail 0、known-fail 9、blocked 25**（driver rc=1 仅因 `blocked>0`，`ISS-248`；8 分 29 秒）；动态 **pass 298、fail 0、known-fail 8、blocked 31**（rc=1 同口径；9 分 29 秒）。
**与基线对比（逐例）**：两档 337/337 例分类**逐例全等**（`diff_baseline.py` ⇒ transitions=0，无增删例）；**无 `pass→fail`、无新 `fail`**。static→dynamic 差异仍为第 5 轮那 12 条（COPY 8 / `pleval` 1 / OOM flake 3），本笔**无新增**。
**`known-fail` 准入（未变更）**：依据集合仍 = `ISS-246` + `ISS-251` + `ADR-0030`（静态 9 = 3+1+5；动态 8 = 3+1+4，`math/lgammal` 因 COPY 记 blocked）；逐例均带 `known_fail_basis` 并经反向校验，**无无依据条目**；live TLS 扫描 337 例 / 命中 3 / `pass_hits=0`。
**验收结果**：① 逐例不变量（独立复核 96 项全绿）：`fail=0`、`total == discovered - excluded`、`closure_ok`/`classification_ok` 为真、静态 331 / 动态 323 张 ELF 最低 `PT_LOAD=0x10000`（≠`0xFC00…`，样例 `functional/argv` 现场核对）、静态无 `PT_INTERP`/动态 `=/lib/ld-musl-dadao.so.1`、链接行含 `libc.a`/`libc.so` 且无 `-T`；② 证据：`/tmp/opencode/FINAL-RERUN/run.sh` **default rc=0**、**`--inject` rc=0**（I0 篡改 JSON 翻红 + `cp`/md5 回绿；本册动态 3 处既有注入亦红→绿）；③ 门控各自 rc=0：`check-musl-freshness`/`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check_issues.py`/`make check`(L1)；④ 产物口径：`libc.a` sha256 `a65c3351…`、`libc.so` `d5fa2da3…`（新 sha），安装根 clang/lld/qemu 与构建树 md5 全等。
**修改文件**：本任务书（仅追加本节 + `阶段进度`）；无源码/驱动改动。gitignored：`.work/log/testcases/final-rerun/`。
**新发现/坑**：与 046t 同一条（`cp` 还原抬高 musl 源 mtime ⇒ mtime 代理假红；终局脚本快照/还原 2592 个源 mtime 并复核内容门控）。另：`pthread_create-oom` 本轮静态 blocked / 动态 pass，与第 5 轮分类一致，无新增 flake。
**遗留问题**：沿用第 5 轮——COPY 8 条（`-fPIC` 口径待架构裁定）、`musl/pleval`（上游 `.mk` 本不构建动态档）、OOM 三条宿主 flake；`P4` golden 对照、`ISS-246` 修复不在本册。

### 终局复跑（新工具链产物，2026-10-17 22:44–23:07）

> **上一轮（22:12–22:41）作废**：其 `libc.a`/`libc.so` 是 **19:49 旧 clang** 编的（`install-host` 21:26 换新工具链后未重建），L2 `check-musl-freshness` 当场报 `toolchain stamp != current clang/ld.lld`。已 `make build-musl-shared JOBS=8` **rc=0**（21 s，22:43:40→22:44:01）重建，`check-musl-freshness` **PASS**；本节数字 = 新产物上的**最终作数**。

**测试结果**：按派单只跑测（未改源码、未动 `Makefile`、未 `install-host`），顺序 static → dynamic、逐组落日志（`.work/log/testcases/final-rerun-round2/`）：静态 **discovered 367 / excluded 30 / total 337：pass 303、fail 0、known-fail 9、blocked 25**（rc=1 仅因 `blocked>0`，`ISS-248`；8 分 30 秒）；动态 **pass 298、fail 0、known-fail 8、blocked 31**（rc=1 同口径；9 分 30 秒）。
**与上轮对比（逐例）**：两档 337/337 逐例**全等**（`diff_baseline2.py` ⇒ transitions=0、无增删例）；**无 `pass→fail`、无新 `fail`**；static→dynamic 仍为第 5 轮那 12 条（COPY 8 / `pleval` 1 / OOM flake 3），本笔无新增。
**`known-fail` 准入（未变更）**：仍 = `ISS-246` + `ISS-251` + `ADR-0030`（静态 9 = 3+1+5；动态 8 = 3+1+4，`math/lgammal` 因 COPY 记 blocked），逐例带 `known_fail_basis` 且经反向校验；live TLS 扫描 337 / 命中 3 / `pass_hits=0`。
**产物/工具链指纹（证明吃的是新产物）**：`libc.a`（**2 660 248 B，mtime 22:44:00，sha256 `a65c3351…`**）、`libc.so`（**1 046 488 B，mtime 22:43:59，sha256 `d5fa2da3…`**，字节未变）、sysroot `libc.so` 同 sha；`clang` `854dd25e…`/`ld.lld` `cfd64e80…`/`qemu-dadao` `c40bc7f9…` 安装根 == 构建树；驱动实吃路径：静态 `<musl>/lib/libc.a`、动态 `<musl>/lib/libc.so`（逐例链接行核）；**静态 331 / 动态 323 张 ELF mtime 均晚于产物 mtime**。
**验收结果**：① `prove_products.py` 全绿；② `verify_groups.py` **96/96 PASS**（六数、闭包、`closure_ok`/`classification_ok`、最低 `PT_LOAD=0x10000`、`PT_INTERP` 形态、无 `-T`）；③ 门控各自 rc=0：`check-musl-freshness`/`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check_issues.py`/`make check`(L1)。
**修改文件**：本任务书（仅追加本节）；无源码/驱动改动。gitignored：`.work/log/testcases/final-rerun-round2/`。
**新发现/坑**：与 046t 同条——**「sha 不变」≠「未重建」**（本轮 `libc.a`/`libc.so` sha 与旧构建逐字节相同，唯一证据是 22:43:59/22:44:00 的 mtime + toolchain stamp）；`check-musl-freshness` 的 toolchain stamp 正是为这类**跨代际错配**设的。
**遗留问题**：沿用第 5 轮——COPY 8 条（`-fPIC` 口径待架构裁定）、`musl/pleval`（上游 `.mk` 本不构建动态档）、OOM 三条宿主 flake；`P4` golden 对照、`ISS-246` 修复不在本册。

### 第 6 轮（动态档用户 TU 改 `-fPIC`；`TESTCASES-049t` 执行落点，2026-10-18 engineer）

**测试结果**：仅改驱动口径 + 重跑（未改源码、未动 `Makefile`、未 `install-host`，产物未重建）。动态档 ⇒ **discovered 367 / excluded 30 / total 337：pass 305、fail 0、known-fail 9、blocked 23**（driver rc=1 仅 `blocked>0`，`ISS-248`；**571 s**）；静态档对照 ⇒ **303 / 0 / 9 / 25**（**509 s**），337 例分类与 guest exit **逐例零变化**。对照第 5 轮动态 `298/0/8/31`：转移**恰 8 条**，无 `pass→fail`/`fail→pass`、无新增 `fail`。
**逐例记账（COPY 8）**：`blocked→pass` 7 = `functional/env`（`environ`）、`math/{lgamma,lgammaf}`（`signgam`）、`regression/{fflush-exit,fgetwc-buffering,rewind-clear-error,setvbuf-unget}`（`stdout`/`stdin`），均 guest exit 0（证据脚本用 qemu 独立重放逐例 0）；`blocked→known-fail` 1 = `math/lgammal`（`signgam` 链上后真跑，`ulperr -10.465` ⇒ `ADR-0030` 依据现场重算成立）；`musl/pleval` **仍 blocked**（`undefined symbol: __pleval`，上游 `pleval.mk` 明写动态档不构建）。静态档侧 `math/lgammal` 仍 `known-fail`，两档 `known-fail` 集合（9 条）现已一致。
**驱动改动（可审计）**：`DYNAMIC_USER_CFLAGS = ("-fPIC",)`（新常量，注释写明 `ADR-0026 D7②` / `contract-dynlink §10②` 与"仅动态档"边界）；`build_and_run` 内 `mode_cflags = list(DYNAMIC_USER_CFLAGS) if cfg["mode"] == "dynamic" else []` 插在 `BASE_CFLAGS + extra` 与 `PER_CASE_CFLAGS` 之间；新增逐例 `compile_cmd` 落 JSON/report。静态档 flag 表与命令构造不变（证据脚本以 `git show HEAD:` 的 AST 常量 + `-fPIC` 计数双重校验）。
**验收结果**：`.work/evidence/TESTCASES-049t/run.sh` default **62 PASS / rc=0**、`--inject` **rc=0**（3 处可达 FAIL：清空 `-fPIC` ⇒ 8 例真跑重回 `blocked` + 审计拒；`functional/env` 记录改回 `blocked` ⇒ 转移审计拒；`BASE_CFLAGS` 注入 `-fPIC` ⇒ 静态不变量审计拒；均 `cp`+md5 还原，driver md5 `4e2fc691…`）；门控各自 rc=0：`check-musl-freshness`/`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check_issues.py`/`make check`(L1)。
**修改文件**：`tools/testcases/run_libc_test_user_suite.py`；本任务书（本节 + `阶段进度`）；`.tao/tasks/testcases/TESTCASES-049t-动态档fPIC.md`；`.tao/knowledge/issues.yaml`（`ISS-259`）。gitignored：`.work/evidence/TESTCASES-049t/`、`.work/log/testcases/libc-test-user-{static,dynamic}.*`、`.work/log/testcases/049t-*`。
**遗留问题**：`musl/pleval` 动态档仍 `blocked`（上游口径，非缺陷）；其余 `blocked 23` 归属不变（`ISS-252/253/254/255` + OOM flake）；`P4` golden 对照、`ISS-246` 修复不在本册。

### 台账迁入（2026-10-18，`INFRA-091t`；原只在 `milestones.md` 流水行）

- `ISS-256`：`ipc_sem`/`ipc_shm` 两个 codegen 缺陷 ⇒ 执行落点 `LLVM-101t`（可变参聚合 + `shmat()` 指针返回 bank）。
- `ISS-257`：`pthread_create-oom` 的 `RLIMIT_AS` 直通宿主 flake（计数抖动，非目标缺陷）。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查 driver（含 16:21 并入的 TLS 扫描 / `classification_ok` 校验，已复核判据）与证据脚本（16:26 被并行改为「仓库内临时目录 + JSON 独立审计 + 3 处注入」版本，已复核并保留，未覆盖），并以真实重跑对齐（非抽样）。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| F1 | `glob` 只到三层 ⇒ 漏 `src/math/gen/template/**`（17 个含 `main` 模板），discovered=350 而非 367 | ✅已修 | `**/*.c` 递归 + 深度 ≥2 计数 | `discovered=367` / `excluded=30`（26 gen + 4 dlopen） |
| F2 | 相对路径基准不一致（`discover()` 相对 `<src>/src`，`build_and_run()` 相对 `<src>`）⇒ dlopen/pleval/api 缺口表全不命中 | ✅已修 | 统一 `cfg["src_root"]` | `dlopen` 进 excluded；`pleval` 加 per-case 旗标后 pass |
| F3 | `options.h` 生成函数返回文件路径却被当 `-I` 目录 ⇒ api 全 `fatal error: 'options.h' file not found` | ✅已修 | 返回 `dirname` | `api/main` pass（78 TU + `unistd.c` 单列 excluded） |
| F4 | 上游 `-g` 在本 target 触发 19 条汇编器错误，harness 编译被误判死 | ✅已修 | `BASE_CFLAGS` 去 `-g` 并注明原因 | harness 9 TU 全过；现场 `-w -g`⇒19 errors、`-w`⇒0 |
| F5 | `pleval.c` 的 chained comparison 在 clang 23 是 **error**（`-w` 降不了） | ✅已修 | per-case flags（引上游 `pleval.mk`） | `musl/pleval` exit=0 |
| F6 | 线程失败原记 `fail`（`pthread_cond-smasher` 等无 `pthread_create` 首错行）⇒ 归因不一致 | ✅已修 | `uses_thread` 非 pass ⇒ `blocked` + 根因指针（保留现场症状） | 18 条统一 blocked；`fail` 10 条均非线程依赖 |
| F7 | `posix_spawn`/`popen` 的 `ENOSYS` 记 `fail`（实为同 `__clone` 缺口） | ✅已修 | 新增 gap signature（`got 38`/`errno = 38`） | 两条 blocked，原因串含 `posix_spawn.c:198` |
| F8 | 闭包守卫不可失败：注入「丢 1 例」仍 PASS | ✅已修 | 在 `main` 用 `discovered_with_main` 重算 census | 注入 ⇒ `[FAIL] census: cases(336)+excluded(30) != discovered_with_main(367)`、rc=1；`cp`+md5 回绿 |
| F9 | 机器故障退出码被当成 128+signo（0x87 会报成 SIGBUS） | ✅已修 | 恢复 `FAULT_NAMES`（`ADR-0004 D5.8`），先判机器故障 | 本轮 0 例触发（fail 全 exit=1），路径逐行核对 |
| F10 | `tls_align` 漏上游 `.mk` 的静态 DSO 目标 ⇒ `undefined symbol: t`（误记 blocked） | ✅已修 | `EXTRA_CASE_SOURCES`（引 `tls_align.mk`） | 转 known-fail，症状来自 `tls_align_dso.c:1:1` |
| F11 | 审计把「编译失败无 ELF」算缺件、把空 link 行当违约 | ✅已修 | 仅 pass/fail 要求 artifact 与 link 行 | 337 条审计全 PASS |
| F12 | 按工作目录 glob 取 ELF 会带历史残留（334 报成真实数） | ✅已修 | 改按 JSON 记录的 `elf` 列表 | `331 ELF images … PT_INTERP 0` |
| F13 | 证据脚本被并行修订（并发守卫 + 隔离 work dir + 审计 + 3 注入） | ✅已复核 | 未再改动（避免覆盖并行工作） | 该版本 default/`--inject` rc=0，见完成区 |

判决：无未修 finding；静态档实现、五类分类、证据与门控完成，交验收（动态档按册留待下一笔；blocked=25 / fail=10 的 issue 登记待架构裁定）。

**重派实例复核（同一轮，16:39–16:48）**：以最终版 `run.sh`（并发守卫 + 隔离 `--work-dir` + audit 现场复算 + 3 注入）**独立重跑** ⇒ `59 PASS / 0 FAIL`、rc=0；六数与 JSON 逐项一致（discovered 367 / excluded 30 / total 337 / pass 299 / fail 10 / known-fail 3 / blocked 25）；`llvm-readobj`、抽样重放、注入与 md5 还原见 `.work/log/testcases/TESTCASES-047t-evidence.log`。判决同上：交验收。

#### 第 1 轮 reviewer 验收
（独立重跑、约束核验、判决）

#### 第 2 轮 engineer 自审（`ISS-249` 收口）

逐行审查 `__dadao_argmask`/`__dadao_trap`（mask 分投、两 bank 独立计数、`rd21`/`rb21` 尾槽）、`syscall_cp.s`（41 号派发 + 16 个 mask 块：先全部 `rd2rb` 再升序 `rd2rd`，逐块核「目的号 < 源号」）、`cpu_loop.c` 镜像表、`check_syscall_abi.py`（解析/完整性/块条数/可达 FAIL）与 `Makefile`/`Process-07` 接线；并以「表 → 反汇编」对照核 `shmat`/`shmdt` 实参落点。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| F1 | 只按「musl 源码出现的 `SYS_*`」派生会拉进端口 `bits/syscall.h.in` 未定义的名字（`SYS_riscv_flush_icache`）⇒ musl 全量编不过 | ✅已修 | 有效集 = musl 源码名 ∩ 端口 `__NR_` 名 ∩ 锁号表 | 245 条；`make build-musl` rc=0 |
| F2 | 旧 `__dadao_trap` 只有 5 个 data 槽 + 1 个地址槽 ⇒ 6 参调用丢第 6 个 | ✅已修 | 按 mask 分投 6+6 槽 | `-strace`：`sendto(...,16)=1`、`recvfrom(...,ptr)=1` |
| F3 | qemu 表内注释用 tab，与该文件 4 空格风格不一致 | ✅已修 | 该函数区 `:\t/*` → `: /*` | `make build-qemu` rc=0；`check-syscall-abi` 69/69 |
| F4 | 证据脚本注入会临时改组件树，与套件重跑并发会污染编译 | ✅已修（按序执行） | 注入只在套件结束后跑 | 508 s 跑完后注入，3 注入均红→回绿 |
| F5 | `ipc_shm` 重跑换了失败位置（mode → `shmdt`） | ❌不修（越界，登记） | 不改 musl/LLVM 代码 | `p` 实测栈地址 vs 宿主 `shmat` 返回 `0x2aaaaaaab000`；`shmat.o` 反汇编（尾调用，无 `rb8` 落值） |
| F6 | `ipc_sem` 仍 fail（`va_arg(union)` 得 0） | ❌不修（越界，登记） | 同上 | 最小复现 `.work/evidence/ISS-249/repro.c` + 反汇编 |

判决：本笔范围内 finding 全修；F5/F6 为**独立 codegen 缺陷**（非 argmask），越界不修、已按现场登记并给出候选修法（LLVM 侧尾调用返回 bank / 可变参聚合；或 musl 侧改用 `__syscall`）。状态 → `待验收`。

#### 第 5 轮 engineer 自审（动态档）

逐行审查驱动改动（公共头集合、`DYNAMIC_EXCLUSION_REASONS`、`MODE_CASE_NOTES`、`attribute_port_gaps(case, mode)`）与证据脚本（审计逐条、loader 探针、重放、COPY/dlopen 探针、3 注入），并以「首跑→修→静态/动态整轮重跑」对齐；未抽样。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| F1 | 用户 TU 误用 musl 内部头（`src/include/errno.h` ⇒ hidden `___errno_location`）⇒ 动态首轮 pilot 5 例假 blocked | ✅已修 | `MUSL_USER_INCLUDE_DIRS`（公共头视图） | pilot 复跑 `ipc_*`/`socket`/`setenv-oom` pass；静态整轮 303/0/9/25 不回归 |
| F2 | 静态档 exclusion reason 在动态档为假命题（「静态镜像无装载器」） | ✅已修 | `DYNAMIC_EXCLUSION_REASONS`（4 条） | 动态 summary 4 条均以「dynamic round」开头；审计模式措辞检查 PASS |
| F3 | `musl/pleval` 动态档链接失败（`__pleval` hidden）易被误判 fail/放宽为 excluded | ✅已修（分类） | 保留执行 + `MODE_CASE_NOTES` 引上游 `.mk`；记 blocked | JSON reason + 任务书逐条依据；审计 blocked 前缀/根因 PASS |
| F4 | 8 条 COPY 链接失败可能被误当 known-fail 或驱动缺陷 | ⏸不修（口径外） | 不改 lld/契约；记 blocked + 依据 `ADR-0026 D7②` | `-fPIC` 同例 link rc=0/exit 0；审计 COPY 归因检查 PASS |
| F5 | 第 1 次静态整轮 `malloc-oom` 被宿主 `SIGTRAP` 打掉（303→302） | ✅已处置（重试 1 次） | 未改代码 | 单跑 3/3 pass；整轮重跑 303/0/9/25 |
| F6 | OOM 三条在动态档偶然 pass（`setenv-oom`/`pthread_create-oom`），易被当作真实增益 | ✅已披露 | 任务书对比单列 flake；`tgmath` 单独说明真因 | 静态档同例为 blocked；连续两次动态/静态结果不一致仅限 OOM 类 |
| F7 | 4 条 dlopen 用例在动态档排除可能被读作「装载能力不足」 | ✅已披露 + 现场探针 | 证据脚本增非 TLS DSO `dlopen/dlsym` 探针 | 探针 exit 0；任务书标明「范围裁定」并留 M9 收编 |

判决：本笔可修 finding 已修；F4/F7 为**口径/范围**事项（不越界改 lld/契约/组件），已按现场登记并留架构裁定。动态档实现、五类分类、对比、证据与门控完成。
