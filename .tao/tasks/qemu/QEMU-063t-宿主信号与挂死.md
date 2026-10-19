# QEMU-063t: `qemu-dadao` 宿主信号与挂死（8 例信号 + 1 例卡死）诊断与收口

**模块**：qemu
**项目里程碑**：M8
**依赖**：`QEMU-062t`（`qemu-dadao` user-mode 后端，已验证）、`TESTCASES-048t`（4 例 `SIGSEGV` 现场 + `unix-smail` 卡死现场）、`TESTCASES-047t`（`flockfile-list` `SIGBUS` / `setenv-oom` `SIGTRAP` 现场）、`TESTCASES-050t`（`lua` 宿主信号 + `lemon` guest 信号现场，2026-10-18 追加表行）、`ISS-255`/`ISS-266`/`ISS-269`（本册对应 issue）、`ISS-247`（用户态基址 = lld 默认 `0x10000`）、`ISS-248`（`blocked>0 ⇒ rc=1` 口径）、`ISS-257`（同族 `RLIMIT_AS` flake，**仅关联、非本册交付**）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 问题根源

`qemu-dadao`（`linux-user`）上 9 例非 guest 正常退出 / 卡死（8 例信号 + 1 例挂死），两档 `blocked`（driver 如实记 `rc<0` / timeout / 平台缺口，不冒充 pass/fail）：

| 例（来源） | 现场签名 |
| --- | --- |
| `MultiSource/Applications/SPASS`（`048t`） | `qemu killed by host signal 11`；`combined.out` 0 B |
| `MultiSource/Benchmarks/MiBench/consumer-typeset`（`048t`） | 同上（`large.lout`，0 B） |
| `MultiSource/Benchmarks/VersaBench/8b10b`（`048t`） | 同上（`input.txt`，0 B） |
| `MultiSource/Benchmarks/VersaBench/dbms`（`048t`） | 同上，**先产出 18151 B 后崩** |
| `regression/flockfile-list`（`047t` 静态档） | 宿主 **signal 7**（`SIGBUS`） |
| `regression/setenv-oom`（`047t` 静态档） | 宿主 **signal 5**（`SIGTRAP`）；**偶发 pass** |
| `MultiSource/Benchmarks/Prolangs-C/unix-smail`（`048t`） | 只打印 `resolve 'ALL' = 'ALL' @ '' (LOCAL)` 后**卡死**（300 s 超时，非信号） |
| `MultiSource/Applications/lua`（`050t`，**2026-10-18 追加**） | 宿主 **signal 11**（两档同签名；静态档停 `bench/process.lua` 666.9 s、动态档停 `bench/meteor.lua` 375.2 s；已并入 `ISS-266`） |
| `MultiSource/Applications/lemon`（`050t`，**2026-10-18 追加**） | **guest `SIGSEGV`**（每个 `fork` 子进程都崩；父进程 `first_error = Error while running on: <input>`、无 parser 产出；最小复现 = `example1.y`、`-O0` 亦可复现；`ISS-269`） |

- **两类新现场的区别（勿混）**：`lua` = **宿主**侧 `SIGSEGV`（与上 6 例同族，`ISS-266` 第 5 例，driver 记 `qemu killed by host signal 11`）；`lemon` = **guest** 侧 `SIGSEGV`（qemu 如实回传 guest 故障，driver 按平台缺口记 `blocked`，`ISS-269`）⇒ 前者查宿主信号帧/地址映射，后者查 guest 故障路径/指令语义。

- **性质（未定根因，不预设）**：上 7 例为**宿主侧**故障/挂死（非 guest 退出码）；`lemon` 例外 = **guest** `SIGSEGV`（qemu 如实回传 guest 故障）。宿主侧可能是 `linux-user` 的地址映射 / 信号帧路径 / 指令语义 / `setrlimit(RLIMIT_AS)` 直通宿主（`setenv-oom` 同族见 `ISS-257`：guest 设 `RLIMIT_AS` 作用于**宿主 qemu 进程** ⇒ 其后宿主侧分配失败）；guest 侧查故障路径/指令语义。
- **输入数据已排除**：`048t` 已按上游 `llvm_test_data()` + `WORKDIR %S` 就位（`testimg.ppm`/`mei16v2.m2v` 等同类处理），**不得**再以「缺输入」结案。
- **时间盒（用户 2026-10-18 裁定）**：诊断**总投入 1–2 小时**（追加 `lua`/`lemon` 两例后**不变**）；超时即**登记归因 + 保留现场**（不硬耗、不无限试错），剩余面如实留在 issue。

## 接口规范

- **输入**：
  - `components/qemu/patches/linux-user/**`（含 `dadao/{cpu_loop.c,signal.c,elfload.c,target_signal.h,…}.patch`）+ `series` + `changelog.md`
  - `.work/build/qemu/qemu-dadao`（构建树）与安装根 `qemu-dadao`（**证据须注明用的哪一个**）
  - 语料：`.work/source/llvm-test-suite/**`（只读）、`.work/source/libc-test/**`（只读）
  - 驱动：`tools/testcases/run_llvm_ts_user.py`、`tools/testcases/run_libc_test_user_suite.py`
- **输出**（**二选一/逐例**，可混合）：
  - **修**：`components/qemu/patches/**` 补丁更新 + `changelog.md`；修后该例在两档 `pass`（按各自 oracle）
  - **归因**：逐例「信号来源（宿主 `si_code`/`si_addr`）+ guest `PC`（`MC_PC`）+ 命中的地址映射/系统调用 + 归属面（qemu / LLVM / musl / 语料）」写入完成区，并更新 `ISS-255`/`ISS-266`/`ISS-269` notes（**不擅自 `closed`**：归因不等于修复）
  - 证据：`.work/evidence/<任务号>/run.sh`（default + `--inject`）+ 现场日志（`-strace`/`-d in_asm`/core 或等价）落 `.work/log/qemu/`
  - 本任务书完成区
- **约束**：只改 `components/qemu/**`（+ 必要时 `tools/testcases/**` 的**过期叙述**）+ 本任务书；**不动** `spec/`、`.tao/contracts/`、`contracts/`、语料/期望值；**不得**用「抬超时/改分类/改标签」当修复。

## 复现（自包含）

```bash
# 048t 面（4 信号 + 1 卡死；静态档先行，两档同）
python3 tools/testcases/run_llvm_ts_user.py --link-mode both --jobs 1 --timeout 300 \
  --only 'SPASS$' --only 'consumer-typeset$' --only '8b10b$' --only 'dbms$' \
  --only 'unix-smail$' --work-dir /tmp/opencode/QEMU-063t

# 047t 面（2 信号；静态档）
python3 tools/testcases/run_libc_test_user_suite.py --link-mode static --timeout 300 \
  --filter 'flockfile-list|setenv-oom' --work-dir /tmp/opencode/QEMU-063t-libc

# 050t 追加面（lua 宿主信号 + lemon guest 信号；lua 取表值 840 s，两档整批约 25–35 min）
python3 tools/testcases/run_llvm_ts_user.py --link-mode both --jobs 1 --timeout 300 \
  --only 'lua$' --only 'lemon$' --work-dir /tmp/opencode/QEMU-063t

# 单例现场（示例：把 host 信号落盘）
.work/build/qemu/qemu-dadao -strace -d in_asm,cpu <elf> <args> 2> /tmp/opencode/QEMU-063t/x.log
```

> 复现口径：**基址 = lld 默认**（不得 `-T dadao.lds`，`ISS-247`）；`timeout 124` ⇒ `blocked`，不得记 pass/fail（`ISS-248`）。

## 验收标准

1. **逐例诊断表**（9 行，每行必填）：宿主信号号 / `si_code` / `si_addr`（或 timeout 的最后一处 guest `PC` 与最后一条输出）、guest 侧落点（`MC_PC` + 反汇编附近指令）、归属判断（qemu / LLVM 后端 / musl / 语料）、处置（修 / 归因）。
2. **时间盒**：完成区写实际诊断耗时；**>2 h 必须停**，其后只做「归因落纸 + 现场归档」，不得继续试错。
3. **修的情形**：该例修后**两档** `pass`（`048t` 按参考 oracle / exit-only；`047t` 按用例退出码），且 `048t blocked 27 → 27−k`、`047t 静态 blocked 25 → 25−m`（k/m = 实际修复数，**现场派生不写死**）；**无回归**（逐例 JSON diff）。
4. **归因的情形**：不得改标 `pass`；`blocked` 保留 + `reason` 指向新证据；`ISS-255`/`ISS-266` notes 追加「归因结论 + 证据路径 + 仍待修的面」，`status` **保持 `open`**。
5. **`unix-smail` 单列**：必须给出「卡在哪一 guest 系统调用 / 宿主侧等待点」（`-strace` 末行 + 宿主 `strace`/`/proc/<pid>/stack` 之一）；若判定为上游程序语义（例如等待不存在的 DNS/交互输入）⇒ 归**语料/驱动口径**并转 `TESTCASES-050t` 处置，附证据。
6. **可达 FAIL（≥2）**：注入须能让判据真红（例如把已知 `pass` 的冒烟例改成超时、或篡改诊断表字段使一致性断言失败）⇒ `cp`+md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）。
7. **门控（各留自身 rc）**：`check-patch-tree`、`check-component-changelog`、`check-qemu-smoke`（L2 代表集，**按需单跑，不与其它测试集并发**）、`make check`(L1)；证据脚本自身 rc。
8. **构建前置申报**：改 `components/qemu/**` ⇒ 需 `make build-qemu`（+ `install-host` 后安装根复核）；**启动前申报预计耗时**、`JOBS=8`、**不并发**（`ISS-229`/`ISS-210`）。

## 不做

- **不**把超时从 300 s 直接抬到很大来「消除」卡死（超时抬升属 `TESTCASES-050t` 且只对「真慢」例；本册卡死例必须诊断）。
- **不**改语料/期望值/`known-fail` 依据表；**不**改 `spec/`、`.tao/contracts/`、`contracts/`。
- **不**做线程/`__clone`（`ISS-252`，`M9`）、TLS（`M9`）、`ISS-253`（`wchar_t`）、`ISS-254`（`INFRA-089t`）。
- **不**顺带重构 `linux-user` 其它面；`ISS-257`（`pthread_create-oom` flake）只作同族参考。

## 硬约束

1. 临时目录 `/tmp/opencode/QEMU-063t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕被检命令自身退出码；长日志落 `.work/log/qemu/`（`timeout` 的 `124` 判 FAIL/超时，不得当 pass）。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；**时间盒到点即归因留问**（属「需用户语义裁定」之外的可自行处置面，但**不得**扩大试错）。
6. 用户裁定须把**原话**写入本任务书；本册已落：「**同意**」（= 6 个宿主信号**追 1–2 小时**、定位不了就登记归因）。
7. 补丁导出纪律：`/tmp` 写入、非空 blob、`check-patch-tree` 全绿。

## 完成区
**测试结果**：`dbms` 静态+动态 **PASS**（oracle 逐字节一致）；048t 抽样（sqlite3/treecc/15-trie/fixoutput/IntMM）两档 **10/10**；`check-qemu-semantics` **161/161**、`check-qemu-smoke` **90/90**、`ninja` 双目标 rc=0；证据脚本 **12 PASS / 0 FAIL, rc=0**（2 处注入均先红后绿）。诊断耗时 ≈1 h 45 min（01:24–02:02，含构建/复跑）。

**逐例诊断表**（si_addr/pc 均来自 `.work/log/qemu/QEMU-063t-*`；qemu = 构建树 `.work/build/qemu/qemu-dadao`）

| 例 | 现象 | 根因（函数/行） | 归属 | 处置 |
| --- | --- | --- | --- | --- |
| SPASS | 宿主 SIGSEGV，si_addr=8，pc=0x51c70 `ld.o rd4,[rd43+8]`，racnt=7 | `cnf_OptimizedSkolemFormula` 内联 `cnf_StrongSkolemization`：`term_Delete(list_Top(newvariables))`（`cnf.c:3029-3035`）；循环需删 2（rd8=4、acc_length=2）而 `newvariables` 已空 ⇒ rd43=0 | 未定（guest 值 vs 后端） | 登记 ISS-266（证据 `QEMU-063t-gdb-SPASS.log`） |
| consumer-typeset | 修前 SIGSEGV/ACCERR（RASOF），`call` pc=0x52884，racnt=63/mrptr=0 | linux-user 未初始化 MemRAS（`ra0[47:0]=0`） | qemu-user（loader 缺口） | MemRAS 已修；修后输出 57 735 B，随后 guest `NULL+7` SIGBUS（`BUS_ADRALN`）⇒ 仍未通过（`postfix.out`） |
| 8b10b | SIGSEGV si_addr=0x703ac78，pc=0x21118 `ld.ut [rb5]`；rd17(k)=0x380000 | `input.txt` 是 LE u32 表，BE 读首词 0x38→0x38000000 ⇒ `lookupTable3B[k<<3]` OOB | 语料（BE 不适用） | 登记 ISS-266（`QEMU-063t-8b10b.strace`） |
| dbms | 修前 SIGSEGV/ACCERR（RASOF），`call` pc=0x27704，racnt=63/mrptr=0 | 同上（MemRAS 未初始化） | qemu-user | **已修**：`init_main_thread` 预留 1 MiB MemRAS + MRPTR 哨兵 ⇒ 两档 PASS |
| flockfile-list | 宿主 SIGBUS `BUS_ADRALN`，si_addr=0x394fc，`do_st8_mmu` | 语料 interpose `malloc` 从 `unsigned char buf[]` 切块、不保证 8 B 对齐；DADAO 8 B 访问要求对齐 | 语料 | 登记 ISS-255（`QEMU-063t-gdb-flockfile-list.log`） |
| setenv-oom | 宿主 SIGTRAP（`QEMU internal SIGTRAP`，GLib 分配 512 B 失败） | `setrlimit(RLIMIT_AS)` 直通宿主，未虚拟化（同 ISS-257 族） | qemu-user（限制） | 登记 ISS-255（`QEMU-063t-setenv-oom.log`） |
| unix-smail | 300 s 超时，最后输出 `resolve 'ALL' = 'ALL' @ '' (LOCAL)` | `popen("/bin/sh -c …")` 失败（guest root 无 DADAO `/bin/sh`）⇒ `deliver.c:252-260` 重试 10×`sleep(60)`；宿主 strace 末 = `nanosleep(60)` | 语料/驱动环境 | 登记 ISS-266 + 转 TESTCASES-050t（`QEMU-063t-unix-smail-host.strace`） |
| lua | 宿主 SIGSEGV（静态 673 s / 动态 375 s） | 时间盒内未诊断（崩点太晚） | 未定 | 登记 ISS-266（050t JSON 现场） |
| lemon | guest SIGSEGV/ACCERR @ **取指** pc=rb32=0x…daf0（栈） | LLVM 后端：`Configtable_clear(0)` 调用点 `buildshifts` 0x24ee0（`lemon.c:1127-1133`）漏写 `rb16`，callee 入口 `rb32←rb16`；最小同形态却正确 | LLVM 后端 | 登记 ISS-269 + 新 **ISS-277**（`QEMU-063t-gdb-lemon.log`） |

**最小复现**（cwd = 各例 `run/`，qemu = `.work/build/qemu/qemu-dadao`）：`dbms`：`$Q ../dbms.elf -i dbms.train.in`；`consumer-typeset`：`$Q ../consumer-typeset.elf -x -I data/include -D data/data -F data/font -C data/maps -H data/hyph large.lout`；`8b10b`：`$Q ../8b10b.elf input.txt 2000`；`SPASS`：`$Q ../SPASS.elf small_problem.dfg -DocProof`；`lemon`：`$Q ../lemon.elf example1.y`；`unix-smail`：`$Q ../unix-smail.elf -v ALL`；`flockfile-list`/`setenv-oom`：在 `.dadao/tests/libc-test-user/static/regression/<例>/` 下 `$Q ./regression_<例>.elf`；`lua`：`$Q ../lua.elf alltests.lua`（≈400 s）。

**修改文件**：`components/qemu/patches/linux-user/dadao/cpu_loop.c.patch`、`components/qemu/changelog.md`、`.tao/knowledge/issues.yaml`（ISS-255/266/269 notes + 新 ISS-277）、本任务书完成区、`.work/evidence/QEMU-063t/run.sh`（新）、`.work/log/qemu/QEMU-063t-*`（证据）；组件检出 `.work/source/qemu` 已 `commit --amend`（E1：HEAD=base+1、clean）。
**验收结果**：`check-patch-tree` **180 patches OK** rc=0（qemu 59，1 份修改、无新增）；`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-issues`/`make check`(L1) 全部 rc=0。
**新发现/坑**：① **MemRAS 缺口**：linux-user 从未初始化 `ra0[47:0]`，RegRAS 63 项即上限；`consumer-typeset`/`dbms` 均先死于 RASOF，修后可推进（dbms 全绿、consumer-typeset 暴露第二处 guest `NULL+7`）。② **lemon 归 LLVM**：`fp` 参数 bank 分配在特定上下文漏写 `rb16` ⇒ 取指到栈。③ `flockfile-list` 的 fake malloc 破坏对齐假设。④ `-strace` 在 guest `dup3(3,2)` 后会被重定向到 guest 的 stderr 文件（诊断陷阱）。⑤ 8b10b 的 BE 语料越界是同族里最干净的反例。
**遗留问题**：`lua` 未诊断；`consumer-typeset` 剩余 `NULL+7`；`SPASS` 未判定 guest/后端；`setenv-oom` 需 rlimit 虚拟化；**未 `install-host`** ⇒ 安装根仍是旧二进制，需在 `make install-host` 后复验：`dbms` 两档、048t 抽样 10 例、`.work/evidence/QEMU-063t/run.sh`。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查（深度 1，无嵌套子代理）：

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 MemRAS 哨兵语义：pop 在 RACNT=0 时读 MRPTR 必须得 RASUF，不得越界 | ✅已修 | `mrptr = base+size-8`，先 `cpu_stq_be_data(env, mrptr, 0)` 再写 `ra0`（契约 D4b `mem_hi==0 ⇒ RASUF`） | `ninja` rc=0；`check-qemu-semantics` 161/161；证据 S4/S5/S6 |
| F2 `target_mmap` 失败时静默保持 `ra0=0`（退回旧行为） | ❌不修（有据） | 注释说明；与修复前行为一致，不新增失败面 | 代码路径审查；`init_main_thread` 失败分支不改 `ra0` |
| F3 证据脚本 rc 语义（`grep -q` 无匹配=1）可能误报 | ✅已修 | S2 用「期望 rc=1」；注入 A 实测 S1 由 0→1，`cp`+md5 还原后回 0 | `.work/log/qemu/QEMU-063t-evidence.log`（S8/S9/S10） |
| F4 ISS-277 的「函数指针走 rb16」归因是否站得住 | ✅已核 | 回读 `contract-abi §4.1/§4.2`；ELF：callee 0x33098 `rb2rb {rb32},{rb16}`，caller 0x24ee0 前无 `rb16` 写 | `QEMU-063t-gdb-lemon.log` + `llvm-objdump` 反汇编 |
| F5 完成区缺「每例最小复现命令」 | ✅已修 | 补「最小复现」一行（8 例命令，lua 标 ≈400 s） | 本文件 |
| F6 只改 qemu + 补丁 + 任务书，未越界 | ✅已核 | `git status -uall` = 4 个 tracked 文件（issues/任务书/qemu 补丁/changelog） | `git diff --stat` |

#### 第 1 轮 reviewer 验收（2026-10-19）

**重跑记录**（脚本重定向 WD/PATCH_BAK 至 `/tmp/opencode/review-A/work/QEMU-063t/`，4 处 driver 调用补 `--json-out` 以符合 INFRA-093t 新规矩）：
- default rc=0，12/12 PASS：S1 MemRAS 补丁在场 ✓、S2 组件源 clean ✓、S3 base+1 commit ✓、S4 dbms static PASS ✓、S5 dbms dynamic PASS ✓、S6 sample 15-trie+fixoutput 两档 PASS ✓、S7 setenv-oom rc=133（SIGTRAP，预期）✓、S8–S10 注入 A（剥离 MemRAS → 红 → cp+md5 还原 → 绿）✓、S11–S12 注入 B（wrong oracle → driver FAIL + oracle mismatch 消息）✓

**约束核验**：
1. 逐例诊断表 9 行均填根因 ✓（SPASS:rd43=0 未定; consumer-typeset:MemRAS→修; 8b10b:BE语料; dbms:MemRAS→修; flockfile-list:对齐语料; setenv-oom:rlimit直通; unix-smail:/bin/sh缺失; lemon:rb16漏写归LLVM; lua:未诊断）
2. dbms 两档 pass ✓（S4+S5）
3. semantics 161/161 ✓（独立重跑 `make check-qemu-semantics` rc=0）
4. smoke 90/90 ✓（独立重跑 `make check-qemu-smoke` rc=0）
5. 可达 FAIL ✓（注入 A 剥 MemRAS hunk→S1 FAIL→cp 还原→回绿；注入 B wrong oracle→driver rc=1→grep oracle mismatch）
6. 门控 ✓：check-patch-tree 180 ✓、`make check`(L1) ✓、check-run-artifacts ✓

**如实性抽查**：① dbms 动态档 `.work/source/llvm-test-suite/.../dbms` 实跑 PASS ✓；② `git -C .work/source/qemu status` 干净 ✓；③ 注入 A md5 前后一致 ✓

**判决**：**Accepted** — 所有验收标准逐条通过，两处注入闭环，9 例诊断表均有根因或处置归宿。

#### architect 提交留痕（2026-10-19）
档位：**正常提交**（无 `WIP:` 前缀，按父会话明确指令）。**如实披露**：本笔提交时本册「第 1 轮 reviewer 验收」为**空**、`**状态**` = `待验收` ⇒ 严格按角色规则应为 `WIP:`；本笔依主会话指令执行，若后续判 `Needs Revision`，返工提交仍落本分支并随 squash 收口。开工分支 `QEMU-063t` 实现提交 `c674604`（本留痕随后单独提交），squash 落 `master`（单提交；**未 push**）。
文件集 **7 项**对账：`components/qemu/patches/linux-user/dadao/cpu_loop.c.patch`（**1 份改**；`series` 不变、`check-patch-tree` **180**）、`components/qemu/changelog.md`、`.tao/knowledge/issues.yaml`（`ISS-255`/`ISS-266`/`ISS-269` notes + 新 `ISS-277`→`LLVM-108t`）、本册 = 完成区「修改文件」逐条一致；**architect 账面/立册 3 项**（`.tao/knowledge/milestones.md`、`.tao/tasks/integ/INTEG-036m-M8-integ里程碑核验.md`、**新增** `.tao/tasks/llvm/LLVM-108t-lemon调用点漏写rb16.md`）= 已披露的**多提**（台账范围）；`.work/evidence/**` / `.work/log/**` 由 `.gitignore` 排除、不入库。**无漏提 / 无越界**。
