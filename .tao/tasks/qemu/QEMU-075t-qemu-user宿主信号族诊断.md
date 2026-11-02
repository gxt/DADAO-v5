# QEMU-075t: qemu-user 宿主信号族诊断（ISS-255/257/266，时盒，只诊断）

**模块**：qemu
**项目里程碑**：M10
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地（只读诊断 + 证据脚本；不改 qemu 语义）

## 接口规范

### 背景
三条 open issue 都与「`qemu-dadao` 上以**宿主信号**终止」有关：

- **ISS-255**：`libc-test` 的 `regression/flockfile-list`、`regression/setenv-oom` 以宿主 `SIGBUS`/`SIGTRAP` 结束（非 guest 退出码）；
- **ISS-257**：`regression/pthread_create-oom` 抖动：一次 `pass`，其后 5/5 pilot + 8/8 单跑全 `BLOCKED`（宿主信号 5）；疑因 guest `setrlimit(RLIMIT_AS)` 直通宿主 qemu 进程；
- **ISS-266**：`llvm-test-suite` 的 SPASS / consumer-typeset / 8b10b / dbms 在 `qemu-dadao` 上以宿主 `SIGSEGV` 终止（静态/动态一致）。

### 目标（**只诊断，不改语义**）
1. 逐例**可复现**：给出最小命令、宿主信号编号、guest 侧最后状态、日志路径；
2. **根因归类**：判定三组是否同源（`setrlimit` 直通 / 内存映射 / 信号投递 / 指令语义 / 栈溢出），给出证据（strace/`/proc`/`gdb` 宿主侧、guest 寄存器/PC、`qemu` 日志）；
3. **修法建议**：每类给出「最小修法 + 影响面 + 预估工作量」，**不实施**（语义/ABI 改动留待用户裁定）；
4. 若发现是测试侧（如 `setrlimit` 用例在 qemu-user 下本就不可判定）⇒ 明确「应记 blocked 还是可判失败」，给判据。

### 约束
- **时盒 ≤ 2 小时**；到时无论是否定根因都停下报告（保留现场）。
- **不改** `components/qemu/**`、`spec/`、`contracts/`、测试期望；只允许新增 `.work/` 证据脚本与日志。
- 若必须改 qemu 才能继续（例如加日志），先停下报告，不擅自改。

## 验收标准
1. 三条 issue 各有：最小复现命令 + 宿主信号/退出码 + 现场日志路径。
2. 同源/异源判定有证据（对照表：触发条件、信号、`setrlimit` 行为、映射差异）。
3. 每类给「最小修法 + 影响面 + 工作量」；不改任何代码。
4. 完成区贴真实命令、输出、退出码；未决项单列。

## 完成区

> 时盒：04:25 起、05:58 止（≈1 h 33 min）。**只诊断**：`components/qemu/**`、`spec/`、`contracts/`、测试期望一字未改；证据脚本 `.work/evidence/QEMU-075t/run.sh`（assert 31/31 PASS，`--inject` 2/2 反例命中）。

### 诊断结论（三组，**不同源**）

**组① QEMU 内部 abort（ISS-255 的 setenv-oom + ISS-257）**：`t_memfill()` 的 `t_vmfill()` 把地址空间填满（`mmap(PROT_NONE)` 到失败，guest strace 231 次 mmap）；linux-user 下 guest VA 与宿主同域，填满后 **qemu 自身的 TCG/malloc 也拿不到地址**（GLib `g_malloc` 失败 → `g_error` → `QEMU internal SIGTRAP`，宿主 133）。**推翻了「`setrlimit(RLIMIT_AS/DATA)` 直通宿主」的旧归因**：qemu 早已跳过 AS/DATA/STACK（`linux-user/syscall.c:11062`/`:14198`），宿主 strace 只有 `RLIMIT_DATA` 的 getrlimit、无 set（B7/B8）。
- `setenv-oom`：`.work/build/qemu/qemu-dadao .dadao/tests/libc-test-user/static/regression/setenv-oom/regression_setenv-oom.elf` ⇒ rc **133**（SIGTRAP），stderr `QEMU internal SIGTRAP {code=128}`；宿主 bt `g_malloc → tcg_constant_internal`（`tcg/tcg.c:2258`）。
- `pthread_create-oom`（static）：同命令 ⇒ rc **133**；宿主 bt `g_malloc → tcg_malloc_internal`（`tcg/tcg.c:1313`）。**dynamic 档同条件 rc=0**（guest 自己 exit 0）⇒ 抖动机制 = 「填满后 qemu 是否还需新分配（新 TB/TCG 缓冲）」，与 guest 语义无关。

**组② guest 崩溃、qemu 如实转发（`-strace` 有 `--- SIGxxx` 转发行、无 `QEMU internal`）**
- `ISS-255 flockfile-list`：rc **135**，`--- SIGBUS {si_code=1(BUS_ADRALN), si_addr=0x4d80c}`；pc `0x24338`（`fdopen` 内 `st.o rd5,[rb4,96]`），`buf` 符号在 `0x4d7ac`（**4 mod 8**）⇒ 语料自带 interpose `malloc` 从 `static unsigned char buf[1<<20]` 按字节切块且基址本身不对齐 ⇒ 负载违反对齐（DADAO 8 B 访问需 8 B 对齐，`cpu_loop.c:453` 报 BUS_ADRALN）。
- `ISS-266 8b10b`：rc **139**，`--- SIGSEGV {si_code=1, si_addr=0x1c04f1e0}`，pc `0x210e0`（`calc` 的 `ld.ut rd5,[rb4,0]`）⇒ `input.txt` 首词 `38 00 00 00`（LE）被 BE 目标读成 `0x38000000`，`lookupTable3B[k<<3]` 越界 ⇒ **数据字节序**问题。

**组③ guest 崩溃、归因未定（ISS-266）**
- `consumer-typeset`：rc **135**，`--- SIGBUS {si_addr=0x7}`，pc `0xdaa78`（`ld.ut rd4,[rb16,8]`，rb16=-1 → NULL+7 的 4 B 载入）。
- `SPASS`：rc **139**，`--- SIGSEGV {si_addr=0x8}`，pc `0x51754`（`ld.o rd4,[rb39,8]`，rb39=0 → NULL+8 的 8 B 载入）。
- 两者都是「`[base+8]`、base 为 0/-1」，疑似同一来源；**时盒内未能判定**是 qemu 指令语义还是后端错编（也未排除语料自身逻辑）。
- `dbms`：**已随 `QEMU-063t` MemRAS 初始化修好** ⇒ rc 0，stdout sha256 `552a4bf3…`（= `dbms.reference_output.small` 去掉末行 `exit 0`，18151 B）逐字节一致。

### 判定口径（blocked vs 可判失败）
- **guest 崩溃类（flockfile-list / 8b10b / typeset / SPASS）⇒ 可判失败（fail / known-fail），不是 blocked**。判据：`-strace` 出现 `--- SIG...` 转发行 + stderr **无** `QEMU internal` ⇒ guest 已跑到自己的信号判定（signal.c:1311 `dump_core_and_abort`，按 target 信号回抛），不是模拟器故障。当前 driver/libc runner 的 `rc<0 → "qemu killed by host signal N" → blocked` 把两类混为一谈（`run_llvm_ts_user.py:1818`、`run_libc_test_user_suite.py:1164`）。
- **组① ⇒ 现状记 blocked（qemu 能力缺口）**，判据：死于 `QEMU internal SIGTRAP` + `GLib … failed to allocate`。**若采纳 `-R`（下）则可判 pass**，但须注记「OOM 触发来自 VA 耗尽，rlimit 本身仍未被模拟」。

### 修法建议（均**未实施**）
1. **`-R 4G`（reserved_va）隔离 guest VA —— 最小、已验证**：实测 `setenv-oom` / `pthread_create-oom`（static+dynamic）全部 **rc=0**，`dbms` 输出 sha256 不变、`heapsort` 与不带 `-R` 逐字节相同。改动面 = 2 个 driver 的 qemu 启动行（libc-test / llvm-ts）≈ 10 行，**0 行 qemu 代码**；风险 = guest VA 限 4 GiB（大内存用例需另行确认），**工作量 1–2 h**。
2. **在 DADAO 端口默认设 `reserved_va`**（替代方案，若不想在 runner 加旗标）：`linux-user/main.c` 启动默认值 ≈ 5–10 行；**影响全量 user-mode**（需全量回归，含依赖地址布局的用例），**0.5 天**。
3. **rlimit 虚拟化（正确但非本二例所必需）**：qemu 现对 guest `setrlimit(AS/DATA/STACK)` **返回 0 但不生效**（语义谎报，`syscall.c:11062`）⇒ 记账 guest brk/mmap 用量并在 get/setrlimit、mmap/brk 上实现；**1–2 天**，建议单独立 issue（P3）。
4. **flockfile-list ⇒ known-fail（语料）**：语料只读、不可修；runner 侧加 known-fail 注记 ≈ 0.5 h。
5. **8b10b ⇒ known-fail/excluded（语料数据 LE vs BE 目标）**：runner 侧注记 ≈ 0.5 h（或生成 BE 输入，属测试侧改造）。
6. **typeset/SPASS ⇒ 单开诊断任务**：用 `-d in_asm,op` 回溯 `rb16=-1` / `rb39=0` 的来源（cmp/跳转/上位载入），并做 clang 侧同源比对；**1–2 天**。

### 完成区字段

**测试结果**：证据脚本 **31/31 PASS**（`bash .work/evidence/QEMU-075t/run.sh`，rc=0）；反例 **2/2 命中**（`--inject`：故意写错的两条期望均被判 FAIL，`INJECT-OK`，rc=0）；官方 driver 复核 2 例（`dbms`=`pass`、`8b10b`=`blocked`/`qemu killed by host signal 11`）。
**修改文件**：`.tao/tasks/qemu/QEMU-075t-qemu-user宿主信号族诊断.md`（本文件）；新增 `.work/evidence/QEMU-075t/run.sh`；新增日志 `.work/log/qemu/QEMU-075t-{evidence,evidence-inject,gdb-flockfile-list,gdb-setenv-oom,gdb-setenv-oom-trap,gdb-pthread_create-oom-trap,gdb-SPASS,gdb-consumer-typeset,gdb-8b10b,host-strace-setenv-oom}.log`。**未改任何 qemu/spec/contracts/测试期望代码**。
**验收结果**：`summary: 31 PASS / 0 FAIL` + `QEMU-075t evidence: PASS`；逐例宿主信号/退出码：flockfile-list 135、setenv-oom 133、pthread_create-oom(static) 133 / (dynamic,-L) 0、SPASS 139、consumer-typeset 135、8b10b 139、dbms 0；`-R 4G`：setenv/pco(static,dynamic) 全 0。安装根二进制与 `.work/build` 同一 md5（`ed228c45…`），用 `.dadao/cross-toolchain/bin/qemu-dadao` 复跑：setenv/pco 无 `-R` 均 133、带 `-R 4G` 均 0（故结论对 driver 实际使用的二进制同样成立）。
**新发现/坑**：① `rc<0 → blocked` 把「qemu 内部 abort」与「guest 崩溃被转发」混为一谈（8b10b 实证）；② 没有 `qemu: uncaught target signal … core dumped` 打印**不能**证明内部故障（`core_dumped==0` 时不打印，本机 `core_pattern` 是 apport pipe）；③ 判据应取 `-strace` 的 `--- SIG…` 转发行（`handle_pending_signal → print_taken_signal`）；④ **旧归因（`QEMU-063t`/`run_libc_test_user_suite.py:388-393` 的「RLIMIT 直通」）已被证伪**，勿再沿用；⑤ `-R` 是 runner 级一行修法，实测四例转绿且两个正常程序输出不变；⑥ 证据脚本初版 `run()` 用 `echo $?` 致 rc 恒 0（28P/3F 假红），改 `return $?` 后 31P/0F —— 抓 rc 必须返回而非打印。
**遗留问题**：① `consumer-typeset`/`SPASS` 根因未定（时盒到）——建议立诊断任务；② 驱动四处的 reason 文案（`run_llvm_ts_user.py:1818-1820`、`run_libc_test_user_suite.py:388-393,1164-1166`）与新结论相反，**待新任务修改**（本任务禁改）；③ rlimit 虚拟化缺口建议单开 issue；④ `-R` 只做了样本级回归（dbms/heapsort），未跑 llvm-ts 全量；⑤ 未测 `-R` 对依赖高地址 `mmap`（固定地址）用例的影响。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行审阅 `.work/evidence/QEMU-075t/run.sh`（本任务唯一可执行交付物）与全部结论/日志的对应关系：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `run()` 末尾用 `echo $?` 打印 rc，调用点用 `rc=$?` 取到的是 `echo` 的状态 ⇒ 所有 rc 断言恒 0（首跑 28P/3F 假红：A4/A7/A10） | ✅已修 | `run()` 改 `return $?`；全部调用点改「`run …` 换行 `rc=$?`」 | 修后 `.work/log/qemu/QEMU-075t-evidence.log`：`31 PASS / 0 FAIL`，rc=0 |
| F2 反例 `INJ1` 用 `"$(run …)"` 命令替换，`run` 的 FAIL 路径被吞（命令替换不传播非零） | ✅已修 | 拆成 `run se …; rc_se=$?; check … "$rc_se"` | `.work/log/qemu/QEMU-075t-evidence-inject.log`：2 条 `FAIL …(wrong expectation on purpose)` + `INJECT-OK`，脚本 rc=0 |
| F3 逐条核「可达 FAIL」：A2/A5/A8/A11 为 `grep -q PAT || echo no`，模式不命中 ⇒ 值变 `no` ⇒ 断言红；B4 要求 guest 侧 `Cannot allocate memory`；B7 要求宿主 strace **无** `RLIMIT_DATA, {`（若 qemu 恢复直通即红）；C1–C4/D1–D4/E1–E3 为退出码/`cmp`/`sha256` 比对 | ❌不修（已核对） | — | 反例跑实测两条独立 FAIL 分支可红（F2）；其余分支逐条对照命令输出成立 |
| F4 `A11` 只校验 `si_addr=0x…` 前缀（未钉死数值），可能过宽 | ❌不修（附理由） | — | 该地址随 ASLR/堆布局变化（本轮 `0x1c04f1e0`、`QEMU-063t` 记录 `0x703ac78`），钉死会假红；配合 A10（rc=139）+ A12（stdout 0 B）+ A5/A8 的精确 `si_addr` 已足够定位 |
| F5 `D2` 的 oracle sha256 是硬编码常量 | ❌不修（已注明来源） | — | 常量 = `dbms.reference_output.small` 去掉末尾 `exit 0` 行（18158−7=18151 B）的哈希；已用 `sha256sum`/`head -c` 现场核对，非「写死计数」 |
| F6 脚本不跑 gdb（宿主侧 bt 是手工证据） | ❌不修（附理由） | — | gdb 输出随 libglib/调试信息版本漂移，纳入 PASS 会假红；宿主侧结论由 B2/B3（`QEMU internal SIGTRAP` + `failed to allocate`）+ B7/B8（宿主无 set）机械支撑，bt 仅作 `.work/log` 佐证 |

自审判定：F1/F2 已修并复验，F3–F6 有据不修；无未修缺陷 ⇒ 状态可置 `待验收`。

#### 第 1 轮 reviewer 验收

**判决：Accepted**（2026-10-26）。以下均 reviewer 亲跑，不采信完成区转述。

**重跑记录（真实输出/退出码）**：
- `bash .work/evidence/QEMU-075t/run.sh` ⇒ `31 PASS / 0 FAIL`、`QEMU-075t evidence: PASS`、**exit=0**（`.work/log/qemu/QEMU-075t-reviewer-evidence.log`）。
- `… --inject` ⇒ 2 条 `FAIL …(wrong expectation on purpose)` + `INJECT-OK`、**exit=0**。
- **独立注入**（reviewer 自做，非复用 --inject）：`run.sh` 的 A1 期望 135→134 后重跑 ⇒ `FAIL A1 (expected=134 actual=135)`、`30 PASS / 1 FAIL`、**exit=1**；`cp` 还原后 md5 `d1ebb24f…` 与备份逐字相等，重跑回绿 31P/0F exit=0。
- 抽 2 例最小复现：`setenv-oom` ⇒ rc **133** + `QEMU internal SIGTRAP {code=128}` + `GLib: … failed to allocate`（guest strace 尾部 mmap 全 `errno=12`）；`flockfile-list` ⇒ rc **135** + `--- SIGBUS {si_code=1, si_addr=0x4d80c}`。
- 官方 driver 复核（reviewer 补跑，完成区此条原无留档）：`run_llvm_ts_user.py --only dbms --only 8b10b` ⇒ `dbms PASS exit=0（oracle byte-exact）`、`8b10b BLOCKED: qemu killed by host signal 11`，与完成区声明一致（`.work/log/qemu/QEMU-075t-reviewer-driver.log`）。

**结论独立核对**：
- 组①根因「guest VA 耗尽外溢」成立：宿主 strace（reviewer 自跑）**只有** `RLIMIT_DATA/STACK … NULL, {…}`（get），**无 set**；qemu 源码 `syscall.c` setrlimit/prlimit64 分支确跳过 AS/DATA/STACK（返回 0 不生效）；gdb 留档 bt `g_malloc→tcg_constant_internal`(tcg.c:2258) / `tcg_malloc_internal`(tcg.c:1313)。「RLIMIT 直通」旧归因证伪成立。
- 组②语料/数据问题成立：flockfile-list 语料 interpose `malloc` 从 `static unsigned char buf[1<<20]` 无对齐切块（源码在 `.work/source/libc-test/src/regression/flockfile-list.c:15,24-35`），`nm` 核 `buf=0x4d7ac`（4 mod 8）、`si_addr=0x4d80c=buf+96` 吻合；8b10b `input.txt` 首词 `38 00 00 00`（LE），`si_addr 0x1c04f1e0 = 0x38000000<<3 + 0x4f1e0` 与 `lookupTable3B[16]`（calc.c:132,173）越界精确吻合。qemu 侧为如实转发（`cpu_loop.c` MALIGN→BUS_ADRALN、signal.c:1311 `dump_core_and_abort`）。
- 组③如实：typeset rc=135/`si_addr=0x7`、SPASS rc=139/`si_addr=0x8` 复跑确认，报告明确「时盒内未能判定」。
- dbms：rc=0，stdout sha256 `552a4bf3…` —— reviewer 由 `dbms.reference_output.small`（18158 B）去末行 `exit 0`（→18151 B）**独立重算**一致，非写死。
- `-R 4G` 最小性：C1/C2/C3（setenv/pco 静+动）rc=0、C4 flockfile 仍 135（不误修）、D4/E3 dbms/heapsort 输出逐字节不变；安装根二进制（md5 `ed228c45…` 与 .work/build 同）复跑 plain=133 / `-R 4G`=0；pco 动态无 `-R` 实测 rc=0。报告明确「均未实施、只建议」。

**约束核验**：`git status`（前后快照逐行对账，均 0 行）、`git diff master...QEMU-075t` 仅任务书 1 文件；`components/qemu/**`、`spec/`、`contracts/`、测试期望**零改动**；`.work/` 产物被 gitignore，符合任务书「只允许新增 .work/」；run.sh 注入已按 cp+md5 纪律还原。证据脚本逐条审过：无恒真断言，B7 的 FAIL 路径（qemu 若恢复 host `setrlimit(RLIMIT_DATA,{…})` 直通即红）可达，D2 常量来源已独立重算。

**非阻断 finding（architect 收尾时处置）**：① `run_libc_test_user_suite.py:388-393` 的 flockfile-list/setenv-oom 旧文案与新结论相反（报告已指出，本册禁改，需立任务改）；②「driver 复核」原无落盘日志，reviewer 已补跑证实，建议后续此类声明随附日志指针。

**后续 issue/任务建议（供 architect 定夺）**：① driver/runner 判定口径改造（`--- SIG…` 转发行 ⇒ guest 崩溃可判 fail/known-fail，`QEMU internal` ⇒ blocked，改 `run_llvm_ts_user.py`/`run_libc_test_user_suite.py` 两处 reason 文案）——立 1 任务；② `-R 4G`（reserved_va）落地 + 全量回归（libc/llvm-ts 两档 driver 启动行）——立 1 任务，含大内存/固定地址用例影响面确认；③ rlimit 虚拟化（guest brk/mmap 记账 + get/setrlimit 生效）单开 issue（P3）；④ typeset/SPASS 根因诊断（`-d in_asm,op` 回溯 rb16=-1/rb39=0 + clang 侧比对）单开诊断任务；⑤ `QEMU-063t`/ISS-255/ISS-257/ISS-266 的 issue notes 中「RLIMIT 直通」旧归因需按本册结论订正（已在报告「新发现/坑④」警示）。
