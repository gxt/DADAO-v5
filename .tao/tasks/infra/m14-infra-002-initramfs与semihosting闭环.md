# m14-infra-002: initramfs + semihosting 控制台/退出闭环

**模块**：infra
**项目里程碑**：M14
**依赖**：`m14-linux-001`（目标 `linux-initramfs` / `linux-semihosting-smoke` 与 `tools/linux/paths.py` 由该任务声明/提供）
**可并行分片**：否（init、cpio、runner 单链路）
**预估**：5–6 h
**状态**：已验证

## 背景

M14 K0 的 MVP 需要「内核日志 → 内置 initramfs 的静态 `/init` → 至少一次 syscall 往返」，控制台与测试退出闭环走 **semihosting**（不引入 UART、不新增 cfx）。K0 还没有内核，因此本任务先把**可被 K1 直接消费**的三件产物做出来并各自可验证：

1. 静态 musl 的 `init`（`write`/`getpid`/`brk` + 错误路径）；
2. 可复现的 cpio newc initramfs；
3. `SYS_EXIT` → host `$?` 的运行期脚本（先用既有 bare-metal semihosting 探针证明映射）。

现成可复用：`make build-musl` 产出 `libc.a`/crt，`make build-bootrom` 产出 `semihost_smoke.elf`/`semihost_fail.elf`，`qemu-system-dadao` 支持 `-semihosting-config` 且把 guest `SYS_EXIT` 码忠实传播到 host `$?`（实测 `semihost_fail.elf` ⇒ `64`）。

## 目标

1. **init 程序**（`tests/linux/init/`）：静态链接 musl，仅用 `write`/`getpid`/`brk`/`exit_group`：
   - 向 fd 1 写完整 banner（含 `init: pid=<n>`；处理部分写，循环补写）；
   - `getpid()` 结果 `> 0` 才继续；
   - `brk(0)` 读当前断点 → `brk(cur + 65536)` 扩一页（DADAO 普通页 = 64 KiB）→ `brk(0)` 复核（失败路径可区分）；
   - 成功 `exit_group(0)`；错误路径：写失败 `2`、`getpid` 异常 `3`、`brk` 失败 `4`（失败信息尽量写 fd 2，写不出去也按对应码退出）。
2. **host 侧错误路径单测**：用 host C 编译器 + syscall shim（`-DHOST_TEST`）注入写失败/`getpid<=0`/`brk` 失败，断言退出码 `2/3/4`；成功路径 `0`。
3. **cpio 生成**（`tools/linux/make_initramfs.py`，目标 `make linux-initramfs`）：
   - newc 格式；条目仅 `.`（dir）+ `init`（文件 0755）+ `TRAILER!!!`；
   - 确定性：mtime 固定 `0`、uid/gid `0`、条目字典序、4 字节对齐、无 build-id；
   - 产物含 initramfs 清单 JSON（路径由 `tools/linux/paths.py::linux_initramfs_manifest()` 给出；字段至少：init ELF sha256、cpio sha256、cpio 大小、syscall 号集合），供 `m14-infra-003` 读取；**不入库运行期路径**。
4. **semihosting 闭环脚本**（`tools/linux/run_semihosting_smoke.py`，目标 `make linux-semihosting-smoke`）：
   - 直接捕获 QEMU 进程 `$?`（**禁** `| tee`/管道吞码）；`semihost_smoke.elf` ⇒ `0`，`semihost_fail.elf` ⇒ `64`；
   - stdout 与源文本 oracle 逐字节一致（oracle 由 `tests/shared/bootrom/semihost_msg.inc` 独立派生，不复用 QEMU 输出）；
   - 期望值错误时非零退出（可达 FAIL）。
5. 不引入 UART/cfx/cache/DTB；不改 QEMU/gem5/chipyard 源码。

## 接口规范

**init 使用的 syscall（号值从锁定内核 `scripts/syscall.tbl` 现场取，不写死）**

| 名称 | 用途 | 备注 |
|---|---|---|
| `write` | banner/错误信息 | `fd`/`buf`/`len`，按 `contract-syscall §3` 传参 |
| `getpid` | pid 校验 | 返回值 `> 0` |
| `brk` | 堆断点 | `brk(0)` 读、`brk(x)` 设；失败返回 `-errno` |
| `exit_group` | 退出 | 退出码见上 |

- 通过 musl 的 `syscall(2)`/`write(2)` 调用（走 `rd15` + `rd16..`/`rb16..` + `rd8` 返回）；不使用 stdio/`malloc`。
- 编译：`clang --target=dadao-unknown-elf -static -O2`（或矩阵建议的等价参数），链接 `libc.a` + crt；产物必须 `ET_EXEC`、无 `PT_INTERP`、无 `DT_NEEDED`。
- 可复现：`SOURCE_DATE_EPOCH` 固定、`-ffile-prefix-map`、`--build-id=none`；`initramfs` 二次生成 sha256 相同。
- **cpio 布局**（`newc`，大端字段按 ASCII hex）：`.`（`S_IFDIR|0755`，size 0）、`init`（`S_IFREG|0755`，内容 = init ELF）、`TRAILER!!!`。
- **退出码映射**：guest `SYS_EXIT`（`0x18`，参数块 `{ADP_Stopped_ApplicationExit, code}`）⇒ host `$? = code`（`spec/Machine-v5 §5.5`）；`SYS_EXIT_EXTENDED` 同码规则；不得把 guest 码与 QEMU 自身错误码混淆（QEMU 启动错误另判）。

## 范围（改哪些文件）

- `tests/linux/init/init.c`、`tests/linux/init/host_test.c`（或同文件 `-DHOST_TEST` 分支）、`tests/linux/init/README.md`
- `tools/linux/make_initramfs.py`、`tools/linux/run_semihosting_smoke.py`（新建）
- 本任务书

**不改**：`Makefile`（目标已由 `m14-linux-001` 声明）、`components/`、`spec/`、`contracts/`、安装根、`tests/shared/bootrom/**`（只读复用）。

## 验收标准

1. `make linux-initramfs` rc=0；产物含 init ELF + cpio + 清单 JSON；`llvm-readelf -h/-d/-l` 证明 init 为 `ET_EXEC`、`EM_DADAO`、无 `PT_INTERP`/`DT_NEEDED`。
2. cpio 解析（独立脚本/`python3` 解析器，不复用生成器代码）：仅 `.`/`init`/`TRAILER!!!`，`init` mode `0o100755`，内容 sha256 = init ELF 现场 sha256；二次生成 cpio sha256 相同（打印两次值）。
3. syscall 范围（用户 2026-11-13 裁定「不做特殊限制，别滥用就行」）：
   - **init 自有** syscall ⊆ {`write`,`getpid`,`brk`,`exit_group`}（号值从 `scripts/syscall.tbl` 现场派生，并与 musl `bits/syscall.h` 交叉核对）；
   - `crt1` 启动期 syscall（如 `set_tid_address`）**允许**，证据中单列说明；
   - **不得滥用**：init 不引入文件/网络/额外 `mmap` 等操作——静态证据 = `init.o` imports，运行期证据 = `qemu-dadao -strace`。
4. host 单测：成功路径 rc=0；三路注入（写失败/getpid≤0/brk 失败）分别 rc=2/3/4；每例贴真实输出。
5. `make linux-semihosting-smoke` rc=0（前置 `make install-host build-bootrom`；缺前置须明确失败并提示）：`semihost_smoke.elf` ⇒ `0`、`semihost_fail.elf` ⇒ `64`；smoke 的 **stderr**（QEMU semihosting 控制台，`target=native`）与源文本 oracle 逐字节一致、stdout 为空；runner **直接**读取 `$?`（代码审查 + 注入「期望码改 65」⇒ FAIL 证明非恒真）。
6. 可复现：在同一工具链下连续两次 `make linux-initramfs`，init ELF 与 cpio 的 sha256 均相同；给出两次现场值。
7. 不引入 UART/cfx/DTB：`git status` 无 `spec/`/`components/qemu`/`components/gem5` 改动；`grep -i uart` 新增文件无命中。
8. 一键证据脚本（含注入→FAIL→`cp`+md5 还原→回绿）；完成区 ≤30 行、无运行期路径（清单 JSON 内的路径由脚本解析，不写进任务书/报告）。

## 说明

- **为什么 K0 能验 `SYS_EXIT` 映射**：既有 bare-metal semihosting 探针在 QEMU 上走同一台机器/同一 `SYS_EXIT` 服务；用它证明「guest 码 → host `$?`」链路，K1 接内核后复用同一 runner 即可。
- **init 不能在本任务运行**：DADAO 无 `linux-user`（P3 未实现），K0 无反内核；因此 init 的**语义**验收 = 静态（ELF/syscall 集合/cpio）+ host 单测（错误路径逻辑），不伪造「跑起来了」。
- **musl 依赖**：`make build-musl` 完成后再跑；缺 `libc.a`/crt 时目标须明确失败并提示，不得静默降级到 picolibc。
- 参考实现只读：`.cache/refs/DADAO/ENV-linux` 的 initramfs 构建方式可对照（**内容溯源，非执行必需**），不复制。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数/sha/退出码写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 用户裁定/授权原话不得编造；自定事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→回绿」；**禁** `git checkout/restore/stash` 还原。
9. 复杂命令输出/构建日志留存运行期日志目录（`docs/Process-08`）。
10. 证据脚本基线钉**派单前 commit 常量**或现场文件 md5，不得取 `HEAD`。
11. runner 不得用 `| tee`/`| tail` 等管道吞掉被检进程退出码。

## 用户授权

（本任务不改 `spec/`/`docs/Process-*`；如必须改，先停并登记「待裁定」。）

## 待裁定

### T1 验收 3 的 syscall 范围（**已裁定**，用户 2026-11-13）

- **用户原话**：「不做特殊限制，别滥用就行」。
- **背景**：原验收 3 写「全 ELF syscall ⊆ {write,getpid,brk,exit_group}」，与「链接 musl `crt1.o` + `libc.a`」互斥——`crt1` 启动期必发 `set_tid_address`，`static_init_tls`/secure-exec 分支在 ELF 内留有**不可达**的 `mmap`/`openat`/`ppoll` 常量（空 `main` 参照构建同样存在）。
- **裁定落点**（验收 3 已按此改写）：判据只约束 **init 自有** syscall ⊆ 4；`crt1` 启动期 syscall 允许且单列说明；不得滥用（文件/网络/额外 `mmap` 等）。
- **证据**：静态 `init.o` imports = {write,getpid,syscall,_Exit,___errno_location}（无 open/openat/mmap/execve/fork/vfork/clone）；运行期 `qemu-dadao -strace` = `set_tid_address`（startup）+ `getpid`、`write`×2、`brk`×3、`exit_group`。

（需用户语义裁定的事项写这里：问题 + 选项 + 建议 + 自决的临时处置；返回主会话。）

## 完成区

**测试结果**：一键证据脚本（`.work/evidence/<任务ID>/run.sh`）= **79/79 PASS，rc=0**；`make linux-initramfs` rc=0、`make linux-semihosting-smoke` rc=0（各跑两次）；host 单测 7/7（ok=0、ok_short=0、write_fail=2、pid_zero=3、brk_read/grow/recheck=4）；4 路反例（mode 0644 / `--inject mtime` / 期望码 65 / brk 注入关闭）均「注入→FAIL→`cp`+md5 还原→回绿」。
**修改文件**：`tests/linux/init/init.c`、`tests/linux/init/host_test.c`、`tests/linux/init/README.md`、`tools/linux/make_initramfs.py`、`tools/linux/run_semihosting_smoke.py`（均新增）；本任务书（完成区/自审/状态）。
**验收结果**：
1. init ELF：`ET_EXEC` / `EM_DADAO(da0)` / 大端；无 `PT_INTERP`、无 dynamic section/`DT_NEEDED`、无 build-id（`llvm-readelf -h/-l/-d/-S` 现场）。
2. cpio（独立解析器，不复用生成器）：条目 `.`(040755,size0) / `init`(0100755,uid=gid=mtime=0,nlink=1) / `TRAILER!!!`；init 载荷 sha256 == init ELF 现场 sha256；两次生成 init `45d50209…a51a`、cpio `784aadf6…fda4`（18872 B）完全相同。
3. syscall 号 {write=64,getpid=172,brk=214,exit_group=94} 现场取自锁定内核 `scripts/syscall.tbl`，与 musl `bits/syscall.h` 交叉一致；**init 自有** syscall ⊆ 4（用户 2026-11-13 裁定）：init.o 仅引用 {write,getpid,syscall,_Exit,___errno_location}，无 open/openat/mmap/execve/fork/vfork/clone；`crt1` 启动期 `set_tid_address` 单独列出。
4. host 单测逐例真实输出（证据脚本日志）：成功路径 `init: pid=<n>` + `init: brk +65536 ok`；ok_short 证 5 字节部分写被循环补写；三路错误 fd2 诊断 + 码 2/3/4。
5. semihosting：`semihost_smoke.elf` ⇒ `$?=0`、`semihost_fail.elf` ⇒ `$?=64`（直接读进程状态，无管道）；**stderr**（semihosting 控制台，`target=native`）与源文本 oracle 1136 B 逐字节一致、stdout 空；注入「期望 65」⇒ FAIL。
6. 无 UART/DTB/cfx：新文件 `grep -i uart` 无命中；`spec/`/`components/qemu`/`components/gem5` 无改动。
**新发现/坑**：
- syscall 判据口径（用户 2026-11-13 裁定「不做特殊限制，别滥用就行」）：只约束 init **自有** call——静态 init.o imports + 运行期 `qemu-dadao -strace`（自有恰为 getpid/write×2/brk×3/exit_group；startup 仅 set_tid_address）；不再要求「全 ELF ⊆ 4」（musl crt1 必带 startup，ELF 内另有不可达 secure-exec 分支 mmap/openat/ppoll）。
- 任务书「DADAO 无 linux-user」过时：安装根有 `qemu-dadao`（QEMU-062t，v11.1.1），init 实测可直接跑通（rc=0、banner 正确）——仅作补充证据，不替代静态+host 单测。
- QEMU semihosting 控制台走 **stderr**（`target=native`），stdout 为空。
- bash `local a=$1 b="…$a"` 会先展开全部词（用旧值），须拆两行。
**遗留问题**：无未完成项。R1–R3 处置：R1 证据脚本 §8 兼容「已提交/未提交」两态（tracked-clean 与 `??` 均判绿、`MODIFIED` 先判非空）⇒ 交付态 79/79 PASS、rc=0；R2 验收 5 文本改 **stderr**；R3 验收 3 按用户 2026-11-13 裁定改为「init 自有 syscall ⊆ 4」。另：本分支 `check-milestones-fresh` FAIL 归因于台账未移表（本任务 + m14-infra-001/m14-spec-002 仍在「待开始」表，另有 m13 台账遗留项），属主会话职责，非本任务产物。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`init.c` / `host_test.c` / `make_initramfs.py` / `run_semihosting_smoke.py` / 证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 验收 3「全 ELF syscall ⊆ 4」与「链接 crt1+libc.a」互相矛盾（musl startup 必带 set_tid_address / 不可达 mmap/openat） | ✅已修（判据收窄为可机械判定的 init 自有 syscall，并在完成区明示） | `make_initramfs.py` 校验 init.o imports；证据脚本加运行期 `-strace` 断言 | 76/76 PASS；trace=`[set_tid_address,getpid,write,brk,brk,brk,write,exit_group]` |
| F2 `_Exit` 缺 `<stdlib.h>`（首编译失败） | ✅已修 | init.c 增 include、去掉无用 `sys/types.h` | `make linux-initramfs` rc=0 |
| F3 `paths.py` 无 `repo_root()`，musl 路径回退失败 | ✅已修 | 改用 `paths.linux_source_dir().parent/"musl"`（work_root 派生） | 生成器 rc=0 |
| F4 证据脚本 cpio 解析器把 data 起点算在未 4 对齐处 → 假 FAIL | ✅已修 | data 起点 = align4(header+name)、下一项 = align4(data_off+size) | 解析 3 条目、trailer padding=0 B、载荷 sha 相等 |
| F5 注入证明用 `git diff` 对新文件恒空（未跟踪） | ✅已修 | 改为 md5 前后不等 + `git status --porcelain -- <file>` | I1/I2/I3 均打印 md5 前后值 |
| F6 `git diff --name-only` 无差异也 rc=0 → 「无 spec/qemu/gem5 改动」恒绿 | ✅已修 | 改 `git diff --quiet`（期望 rc=0） | 检查项 PASS，且注入路径另有反例 |
| F7 `local a=$1 b="…$a"` 用旧值 → `restore()` 恢复了错误的文件（md5 不符、回绿失败） | ✅已修 | `backup`/`restore` 拆两行赋值 | 三处 restored md5 与注入前一致、回绿 PASS |
| F8 生成器 `--inject` 选项无消费者（死代码） | ✅已修 | 证据脚本新增 I1b（`--inject mtime`：两次 sha 必须不同）与 I1c（mode 注入必须被拒） | 两次 sha 现场不同；mode 注入 rc=1、去除后 rc=0 |
| F9 `--inject mtime` 用秒级时间戳，同秒内两次运行可能相同（注入不生效） | ✅已修 | 改毫秒时间戳 `& 0xFFFFFFFF` | I1b 两次 sha 现场不同 |
| F10 部分写/失败注入只覆盖 fd1，未见「fd2 也写不出去仍按码退出」 | ❌不修（`init_fail` 返回值不依赖 fd2 写成功，代码路径已覆盖；新增场景收益低） | — | `init_fail` 忽略写 fd2 的返回值并 `return code`；host 单测 write_fail=2 已证 |

自审判定：F1–F9 已修并复验，F10 不修（有代码级理由）；无未修 finding，状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 独立执行，worktree `wt`，命令+真实退出码）**
- `GATE_LOCK_WAIT=600 make linux-initramfs` ×2 → **rc=0/0**；`sha256sum`：init `45d50209…a51a`、cpio `784aadf6…fda4`（18872 B）两次逐位相同。
- `make linux-semihosting-smoke` → **rc=0**、6×`[PASS]`，smoke `$?=0` / fail `$?=64`；直跑 QEMU（stdout/stderr 分离）：stderr=1136 B、stdout=0 B、两 stderr `cmp` 相同；reviewer 独立从 `semihost_msg.inc`+`EXCL` 派生 oracle=1136 B、sha256 前缀 `0a5441c53aadc793` == runner 期望/实测。
- host 单测（reviewer 自编译 `cc -DHOST_TEST`）7 场景 rc = 0/0/2/3/4/4/4，fd2 诊断齐。
- `llvm-nm -u init.o` = {_Exit,___errno_location,getpid,syscall,write}；`qemu-dadao -strace init` rc=0，trace = set_tid_address→getpid,write,brk×3,write,exit_group，banner 正确。
- **证据脚本 `bash .work/evidence/<任务ID>/run.sh` → rc=1，75 PASS / 4 FAIL**，4 项全在 §8：`injection target missing`×3 + `unexpected tracked modification(s)`；§0–§7（含 4 路自带反例）全绿。
- reviewer 独立注入：`mtime = 0`→`1`（md5 `a60c184d`→`7962d147`）⇒ 脚本报 `[PROBLEM] init uid/gid/mtime=0/0/1, expected 0/0/0`、`[FAIL] cpio newc layout/attributes/payload`（另 2 项回绿检查转红）；`cp` 还原 md5 复等 `a60c184d`，重跑回基线 75/4（同 4 名）。全程无 `git checkout/restore/stash`。

**判决：Needs Revision**（唯一阻断项 = 验收 8 证据脚本在交付态红；完成区「79/79 PASS，rc=0」在交付态不复现）
- 根因：`run.sh` §8 假定「产物尚未提交」——① `case "$st"` 把 tracked-clean(`""`) 判成 `injection target missing`（提交后注入目标必然 tracked+clean）；② `MODIFIED` 为空时 `printf '%s\n' ""` 输出空行，`grep -qv '^ M …'` 命中 ⇒ 伪 FAIL（违反「提交后仍须回绿」）。
- 改法（`.work/evidence/<任务ID>/run.sh` §8）：case 改 `"" | "?? "*) ok …`（或加 `git diff --quiet -- "$f"` 复核）；`MODIFIED` 先判非空再 grep。预期交付态 **79/79 PASS、rc=0**（§0–§7 已实测 75 项全绿）；修后重跑并把完成区数字改现场值。

**T1 结论（提请架构师改任务书文本）**：收窄成立、未弱化「init 只用 4 项服务」的语义；应改验收 3 措辞，**不要求**实现避开 crt1。
- 实测：链接后 ELF 的 rd15 立即数含 `0x38 openat / 0x49 ppoll / 0x60 set_tid_address / 0xde mmap / 0x5d exit`（对照锁定 `scripts/syscall.tbl`）⇒ 原文「全 ELF syscall ⊆ 4」字面必红，选项 C 不可达。
- init 自有面两路齐备：静态 imports ⊆ 5（无 open/mmap/execve/stdio/malloc）+ 运行期 strace 恰 4 个（错误路径由 host 单测覆盖，源码只经 write/getpid/syscall/_Exit）⇒ 语义仍被完整证明，未被削弱。
- 选项 B 与目标 1「静态 musl init（crt1+libc.a）」及接口规范冲突，且 errno/TLS 依赖 `__init_tp` ⇒ 代价不值；建议验收 3 改为「init 自有 syscall ⊆ 4（静态 imports + `-strace` 双证）」。

**约束核验**：`git show --stat HEAD` = 6 文件（tests/linux/init×3、tools/linux×2、本任务书），未动 Makefile/spec/components/contracts；新文件 `grep -i uart` 无命中；完成区 15 行 ≤30、无绝对运行期路径；审查前后 `git status -uall` 全空、7 个交付文件 md5 逐位一致（快照 diff 仅差 reviewer 漏抄的 branch 两行）；未提交 git、未重建组件。

**非阻断 findings（architect 收尾处理）**
- ① 验收 5 文本「stdout 与 oracle 逐字节一致」与实测不符：控制台在 **stderr**（`target=native`），stdout 恒空；`spec/Machine-v5 §5` 未规定宿主流路由（grep `stderr` 无命中），§5.5 退出码传播已实测 0/64 ⇒ 改任务书文本即可。
- ② 完成区「check-milestones-fresh 因本任务台账行 FAIL」归因不全：`make` 实际先停在 m13 台账 `m13-testcases-016`（R1）；m14 台账另 4 项（A1 状态「待验收」vs 表「待开始」+ R1×3：m14-spec-002 / m14-infra-001 / 本任务），均属主会话移表，非本任务产物。
- ③ 完成区「79/79 PASS」仅在提交前成立，须随 ① 的修复重跑刷新为现场值。

### 第 2 轮 engineer 自审（返工 R1–R3）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 证据脚本在**交付态**（产物已提交）rc=1：`case "$st"` 把 tracked-clean（porcelain 空串）判成 `missing`；`MODIFIED` 空时 `printf '%s\n' ""` 产生空行、`grep -qv` 命中 ⇒ 伪 FAIL | ✅已修 | §8 的 case 改 `"" \| "?? "*) ok "injection target unchanged"`；`MODIFIED` 先 `[ -z ]` 判空，非空才 grep（并附 `\|\| true` 兜住 grep 无命中码） | 交付态重跑：**79/79 PASS，rc=0**（§8 四项全绿：3 个 injection target unchanged + 「only the task book …」，或未改书时「no tracked file modified」） |
| R2 验收 5 文本「stdout 与 oracle 逐字节」与实测不符（控制台在 stderr，`target=native`；`spec/Machine-v5 §5` 未规定宿主路由） | ✅已修（改条款文本 + 完成区同步） | 验收 5 改为「**stderr** 与控制台 oracle 逐字节一致、stdout 为空」；完成区验收 5 同步 | runner 实测：stderr=1136 B == oracle、stdout=0 B；`make linux-semihosting-smoke` rc=0 |
| R3 验收 3 的 syscall 范围（用户 2026-11-13 裁定「不做特殊限制，别滥用就行」） | ✅已修（改条款 + 删不可达要求） | 验收 3 改为「**init 自有** syscall ⊆ 4；`crt1` 启动期 syscall 允许并单列；不得滥用（文件/网络/额外 mmap）」；「全 ELF ⊆ 4」删除；保留静态 imports + 运行期 `-strace` 双证据 | init.o imports = {write,getpid,syscall,_Exit,___errno_location}；strace = set_tid_address + getpid/write×2/brk×3/exit_group |

| R4 第 1 轮 reviewer 记录含 2 处具体 `.work/**` 路径 ⇒ `check-knowledge-refs` 按 ISS-352 判 FAIL | ✅已修（机械归一，不改判决/数据） | 两处改为 `.work/evidence/<任务ID>/run.sh` 占位 | `make check-knowledge-refs` PASS（0 具体引用） |

自审判定：R1 为阻断项（已修并复验交付态 79/79 绿）；R2/R3 为条款文本（已改，实现无需改动）；状态保持 `待验收`。

### 第 2 轮 reviewer 验收

**重跑记录（reviewer 独立执行，命令 + 真实退出码）**
- 交付态全量：树干净（产物已提交）下 `bash .work/evidence/<任务ID>/run.sh` → **rc=0，79 PASS / 0 FAIL**；§8 = `injection target unchanged`×3 + `no tracked file modified (delivered/committed state)`；跑后 3 个交付文件 md5 不变（`a60c184d…`/`db86c55e…`/`b4b07e8a…`）、`git status -uall` 空。
- 越界检测（reviewer 自设计）：`cp` 备份 `README.md`（md5 `a210ab12…`）→ 追加 1 行 → `run.sh --inject-only` → **rc=1**、`[FAIL] tracked change(s) outside this task's deliverables: README.md`；`cp` 还原 md5 复等 `a210ab12…`、`git status` 空 ⇒ 越界改动仍被抓到（未放宽判据）。
- 回归：`GATE_LOCK_WAIT=600 make linux-initramfs` ×2 → **rc=0/0**，init `45d50209…a51a`、cpio `784aadf6…fda4`（与第 1 轮同值，`diff` rc=0）；`make linux-semihosting-smoke` → **rc=0**、6×`[PASS]`，`$?`=0/64、stderr 1136 B == oracle（`0a5441c5…`）、stdout 0 B；host 单测 7 场景 rc = 0/0/2/3/4/4/4。
- `make check-knowledge-refs` → **rc=0，PASS（0 具体 `.work/**` 引用；0 悬空）**；任务书残留 `.work/…` 命中均为 `<任务ID>` 占位形（豁免）。

**返工核验**
- R1（原阻断项）✅：§8 case 改 `"" | "?? "*) ok`（tracked-clean 与 untracked 两态均绿）、`MODIFIED` 先 `[ -z ]` 判空、`UNEXPECTED` 以 `git diff --name-only`+`--cached` 对交付集正则过滤 ⇒ 交付态 79/79 rc=0 实测通过，越界注入实测报红（见上）。
- R2 ✅：验收 5 已改「**stderr**（QEMU semihosting 控制台，`target=native`）与源文本 oracle 逐字节一致、stdout 为空」，完成区/验收结果同步，与实测一致。
- R3 ✅：验收 3 按用户 2026-11-13 裁定改为「init 自有 syscall ⊆ 4；`crt1` 启动期允许并单列；不得滥用（文件/网络/额外 mmap）」，静态 imports + 运行期 `-strace` 双证据保留；T1 标「已裁定」并落用户原话「不做特殊限制，别滥用就行」（与主会话转达一致）；README 同步引用。
- R4 ✅：第 1 轮记录 2 处具体 `.work/**` 已机械占位化；我核对其余数据（75 PASS/4 FAIL、79/79、md5、sha 前缀）逐字未变，判决未被改写。
- 范围：返工提交仅动本任务书 + `tests/linux/init/README.md`；`run.sh` §8 改动在证据目录（不入库，md5 `f10516dc`→`2fe65595`）；完成区仍 15 行 ≤30。

**判决：Accepted** —— 验收命令块在本轮重跑下全绿：交付态 79/79 rc=0、越界 FAIL 可达、回归（initramfs×2/smoke/host 7 场景）与 `check-knowledge-refs` 全过；返工只动阻断项与条款文本，无越界、无凑绿。审查前后 `git status -uall` 空、交付文件 md5 与快照一致；未提交 git、未重建组件。本记录写入后（任务书 `M` ∈ 交付集）复跑 `--inject-only` 验证 §8 第二分支：实测 **rc=0**、`[PASS] tracked changes confined to this task's deliverables`（23 checks 全绿）⇒ §8 三分支（干净交付态 / 集合内修改 / 越界修改）均已覆盖。
