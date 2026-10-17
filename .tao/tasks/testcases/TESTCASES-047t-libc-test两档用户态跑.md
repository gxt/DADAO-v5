# TESTCASES-047t: libc-test 两档用户态跑（静态档 → 动态档）

**模块**：testcases
**项目里程碑**：M8
**依赖**：`QEMU-062t`（`qemu-user` 的 DADAO 后端，**`已验证`**；`qemu-dadao` 在安装根）；`INFRA-082t`（`P1` musl 静态，**`已验证`**）、`INFRA-085t`（`P2` 动态，**`已验证`**）；`TESTCASES-044t`（`libc-test` **取源与锁定**，**`已验证`**；`patchless = true` ⇒ 源只读）、`TESTCASES-045t`（`P1` 能力边界度量，`已验证`；其 `tools/testcases/run_suite.py` 在 `dadao-m1` 路径上已硬失败 ⇒ **本册不复用其运行路径**，只复用其**建链方法论**与排除口径的教训）；`ISS-247`（**链接基址**）、`ISS-246`（**known-fail 唯一依据**）、`ISS-229`（串行）、`ISS-210`（安装根新鲜度）、`ADR-0025`（`D2`/`D6`/`D7`）；**同批三册**：`TESTCASES-046t` / `TESTCASES-047t`（本册）/ `TESTCASES-048t` ⇒ **同改共享文件（`Makefile` / `milestones.md`）⇒ 串行**。
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（自审意见、finding 处置及判决）

#### 第 1 轮 reviewer 验收
（独立重跑、约束核验、判决）
