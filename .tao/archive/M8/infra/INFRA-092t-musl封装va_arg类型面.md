# INFRA-092t: musl 系统调用封装函数的 `va_arg` 类型面（三 bank 下按实参真实类型取）

**模块**：infra
**项目里程碑**：M8
**依赖**：`ADR-0031`（`Accepted`：三 bank 变参 ABI 的真源）；`LLVM-102t`（**B 段**：变参三游标 ABI 落到安装根 —— 本册的两个缺陷**由该 ABI 暴露**；执行前须确认安装根工具链已含 B 段，否则 `functional/fcntl` 复现不出来）；`TESTCASES-047t`（验收载体 + 现场来源）；`LLVM-101t`（`A` 项 = `union semun` 变参聚合的**编译器侧**取法，与本册「`semctl` 不改」判定互为印证）；`ISS-271`（本册登记源）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 用户裁定（原话逐字引录，渠道 = 经主会话问答，2026-10-18）

> 「**检查musl中的所有系统调用的封装函数，凡是类似情况都修改封装函数，va_arg改为正确的数据类型**」

## 问题根源

- `ADR-0031 D1`/`D3`/`D5`：变参实参按**类型**分流到三个 bank —— **指针 → RB**、**整数 → RD**、**浮点 → RF**；`va_arg(ap, T)` 从 **`T` 所属 bank** 的游标取槽、推进该 bank（`D4`）。同理「指针」与「整数」在三 bank 下**不再是同一块寄存器/同一段内存**。
- musl 的若干系统调用封装函数历史上依赖「**实现内类型双关**」：函数的 POSIX/Linux 声明里第三参类型由 `cmd`/`request` 决定（`fcntl(int, int, ...)`），而实现统一按 `unsigned long` 读再强转成指针（`components/musl/src/fcntl/fcntl.c:12` ⇒ `arg = va_arg(ap, unsigned long);`，`fcntl.c:44` 又把它 `(void *)arg` 送进 `syscall()`）。旧 ABI 下「同一 8 字节/同一寄存器序列」天然成立；**三 bank 分离后不成立**：调用方把 `struct flock *` 放进 RB，被调方从 RD 读 ⇒ 读到 **0**。
- **现场（架构师实测，2026-10-18；探针 `.work/evidence/INFRA-092t/probe.c`，输出 `probe.out`，静态链安装根 `libc.a`，`qemu-dadao` 跑，rc=0）**：

  ```
  A ptr-read-as-long  = 0  (addr=135915734183168)        <- 指针进 RB，按 long(RD) 读 = 0
  B ptr-read-as-ptr   = 7b9d590e2d00  (addr=7b9d590e2d00) <- 按 void* 读正常
  C int-read-as-int   = 77                               <- int 进 RD，按 int 读正常
  D int-read-as-ptr   = 39f10  (want 0)                  <- 反向双关：int 进 RD，按 void*(RB) 读 = 垃圾
  E syscall(SYS_uname,&u) = -1 errno=14 sysname=''       <- syscall() 缺陷（EFAULT）
  F open(O_CREAT) = 3 errno=0
  G fcntl(F_GETFD) = 0
  H fcntl(F_SETFD,FD_CLOEXEC) = 0 then F_GETFD = 1       <- 整型类命令正常
  I fcntl(F_SETLK,&flk) = -1 errno=14 (want 0)           <- fcntl() 缺陷（EFAULT）
  ```
- **语料现场（两档一致）**：`.work/log/testcases/libc-test-user-static.log:14` / `...-dynamic.log:13`
  `FAIL functional/fcntl exit=1 ... fcntl.c:27: fcntl(fd, 6, &fl)==0 failed: errno = Bad address`（`6 = F_SETLK`）。
- **不是 `nm`、不是链接、不是编译器 bug**：`B`/`C`/`H` 证明变参 ABI 本身正确；错的是**封装函数按错的类型去取**。

## 目标

把 musl 里**所有**变参封装（系统调用封装 + 同类 varargs 封装）的 `va_arg` 类型改成**实参的真实类型**，使 `ADR-0031` 三 bank 分类下取值 bank 正确；并保证修完后 `syscall()` 的**调用点**与 `__dadao_argmask()` 的槽位分类一致（见 §调用点一致性）。

## 全量审计（初判；执行期须逐点复核并补正）

**枚举口径（可复核）**：`grep -rn "va_arg" .work/source/musl/src/` = **81 处**（22 文件）；`grep -rn "va_start" .work/source/musl/src/` = **43 处**。逐点判定 = `va_arg` 类型的 bank vs 调用方按声明/POSIX 传的真实类型的 bank。

**依据码**（表内「依据」列）：
- `B1` = C 标准 6.5.2.2 默认实参提升（`char`/`short`→`int`、`float`→`double`）+ `ADR-0031 D8`
- `B2` = `ADR-0031 D3`（union 不展开 ⇒ 通用聚合 ⇒ RD；HFA/HPA 除外）
- `B3` = POSIX / Linux 手册与 musl 头文件声明（接口规范里的真实类型）
- `B4` = `contract-syscall §3` + `arch/dadao/syscall_arch.h` 的 `__dadao_argmask()`（三载体不变量，`make check-syscall-abi` 门控）
- `B5` = 本册现场探针（上「问题根源」的 A–I，`.work/evidence/INFRA-092t/probe.c` + `probe.out`）
- `B6` = 目标不编译（`obj/` 下无该 `.o`，或 `SYS_*` 未在该 arch 定义）

| 文件:行 | 函数 | 原 `va_arg` 类型（bank） | 实参真实类型（bank） | 需改 | 依据 |
| --- | --- | --- | --- | --- | --- |
| `src/fcntl/fcntl.c:12` | `fcntl` | unsigned long（RD） | 指针类 cmd：`struct flock *`/`struct f_owner_ex *`/`uint64_t *`（RB）；整型类 cmd：`int`/`long`（RD） | **改**（按 cmd 分支） | B3+B5 |
| `src/fcntl/open.c:12` | `open` | mode_t=unsigned int（RD） | `int mode`（RD） | 否 | B3 |
| `src/fcntl/openat.c:12` | `openat` | mode_t（RD） | `int mode`（RD） | 否 | B3 |
| `src/ipc/semctl.c:28` | `semctl` | union semun（D3 通用聚合→RD 1 槽） | POSIX：`union semun`（RD 1 槽） | 否（注 ①） | B2+B3 |
| `src/legacy/ulimit.c:13` | `ulimit` | long（RD） | POSIX：`long`；常见调用点传 `int`（RD） | 否 | B3 |
| `src/linux/clone.c:39` | `__clone` | pid_t *（RB） | `pid_t *`（RB） | 否 | B3 |
| `src/linux/clone.c:41` | `__clone` | void *（RB） | `void *`（RB） | 否 | B3 |
| `src/linux/clone.c:42` | `__clone` | pid_t *（RB） | `pid_t *`（RB） | 否 | B3 |
| `src/linux/prctl.c:11` | `prctl` | unsigned long ×4（RD） | Linux：`unsigned long arg2..arg5`（RD）；`argmask(SYS_prctl)=0` | 否（注 ②） | B3+B4 |
| `src/linux/ptrace.c:14` | `ptrace` | pid_t（RD） | `pid_t`（RD） | 否 | B3 |
| `src/linux/ptrace.c:15` | `ptrace` | void *（RB） | `void *addr`（RB） | 否 | B3 |
| `src/linux/ptrace.c:16` | `ptrace` | void *（RB） | `void *data`（RB） | 否 | B3 |
| `src/linux/ptrace.c:20` | `ptrace` | void *（RB） | `void *addr2`（RB；SPARC 专有分支） | 否 | B3 |
| `src/locale/strfmon.c:66` | `strfmon` | double（RF） | `double`（C 提升后，RF） | 否 | B1 |
| `src/misc/ioctl.c:133` | `ioctl` | void *（RB） | 指针类请求 `void *`（RB）；整型类请求 `int`（RD） | 否（注 ③，残留） | B5 |
| `src/misc/syscall.c:13` | `syscall` | syscall_arg_t=long（RD，槽 0） | 按 `SYS_*` 原型：地址→`void *`（RB）、其余→`long`（RD）；位 = `__dadao_argmask(n)` bit 0 | **改**（按 mask 逐槽取） | B4+B5 |
| `src/misc/syscall.c:14` | `syscall` | syscall_arg_t=long（RD，槽 1） | 同上（bit 1） | **改** | B4+B5 |
| `src/misc/syscall.c:15` | `syscall` | syscall_arg_t=long（RD，槽 2） | 同上（bit 2） | **改** | B4+B5 |
| `src/misc/syscall.c:16` | `syscall` | syscall_arg_t=long（RD，槽 3） | 同上（bit 3） | **改** | B4+B5 |
| `src/misc/syscall.c:17` | `syscall` | syscall_arg_t=long（RD，槽 4） | 同上（bit 4） | **改** | B4+B5 |
| `src/misc/syscall.c:18` | `syscall` | syscall_arg_t=long（RD，槽 5） | 同上（bit 5） | **改** | B4+B5 |
| `src/mman/mremap.c:25` | `mremap` | void *（RB） | `void *new_address`（RB） | 否 | B3 |
| `src/mq/mq_open.c:14` | `mq_open` | mode_t（RD） | `int mode`（RD） | 否 | B3 |
| `src/mq/mq_open.c:15` | `mq_open` | struct mq_attr *（RB） | `struct mq_attr *`（RB） | 否 | B3 |
| `src/mq/x32/mq_open.c:15` | `mq_open` | mode_t（RD） | 同 `mq/mq_open.c`（RD） | —（不编译） | B6 |
| `src/mq/x32/mq_open.c:16` | `mq_open` | struct mq_attr *（RB） | 同 `mq/mq_open.c`（RB） | —（不编译） | B6 |
| `src/process/execl.c:9` | `execl` | const char *（RB） | `const char *`（RB） | 否 | B3 |
| `src/process/execl.c:17` | `execl` | char *（RB） | `char *`（RB） | 否 | B3 |
| `src/process/execle.c:9` | `execle` | const char *（RB） | `const char *`（RB） | 否 | B3 |
| `src/process/execle.c:18` | `execle` | char *（RB） | `char *`（RB） | 否 | B3 |
| `src/process/execle.c:19` | `execle` | char **（RB） | `char **envp`（RB） | 否 | B3 |
| `src/process/execlp.c:9` | `execlp` | const char *（RB） | `const char *`（RB） | 否 | B3 |
| `src/process/execlp.c:17` | `execlp` | char *（RB） | `char *`（RB） | 否 | B3 |
| `src/stdio/vfprintf.c:112` | `pop_arg` | void *（RB） | `%p`/`%s` 的实参（RB） | 否 | B1 |
| `src/stdio/vfprintf.c:113` | `pop_arg` | int（RD） | `int` | 否 | B1 |
| `src/stdio/vfprintf.c:114` | `pop_arg` | unsigned int（RD） | `unsigned int` | 否 | B1 |
| `src/stdio/vfprintf.c:115` | `pop_arg` | long（RD） | `long` | 否 | B1 |
| `src/stdio/vfprintf.c:116` | `pop_arg` | unsigned long（RD） | `unsigned long` | 否 | B1 |
| `src/stdio/vfprintf.c:117` | `pop_arg` | unsigned long long（RD） | `unsigned long long` | 否 | B1 |
| `src/stdio/vfprintf.c:118` | `pop_arg` | int（RD） | `short`/`char` 提升后 `int` | 否 | B1 |
| `src/stdio/vfprintf.c:119` | `pop_arg` | int（RD） | `unsigned short` 提升后 `int` | 否 | B1 |
| `src/stdio/vfprintf.c:120` | `pop_arg` | int（RD） | `signed char` 提升后 `int` | 否 | B1 |
| `src/stdio/vfprintf.c:121` | `pop_arg` | int（RD） | `unsigned char` 提升后 `int` | 否 | B1 |
| `src/stdio/vfprintf.c:122` | `pop_arg` | long long（RD） | `long long` | 否 | B1 |
| `src/stdio/vfprintf.c:123` | `pop_arg` | size_t（RD） | `size_t` | 否 | B1 |
| `src/stdio/vfprintf.c:124` | `pop_arg` | intmax_t（RD） | `intmax_t` | 否 | B1 |
| `src/stdio/vfprintf.c:125` | `pop_arg` | uintmax_t（RD） | `uintmax_t` | 否 | B1 |
| `src/stdio/vfprintf.c:126` | `pop_arg` | ptrdiff_t（RD） | `ptrdiff_t` | 否 | B1 |
| `src/stdio/vfprintf.c:127` | `pop_arg` | void *（RB） | `uintptr` 实参（RB） | 否 | B1 |
| `src/stdio/vfprintf.c:128` | `pop_arg` | double（RF） | `double`（RF） | 否 | B1 |
| `src/stdio/vfprintf.c:129` | `pop_arg` | long double（RF） | `long double`（RF） | 否 | B1 |
| `src/stdio/vfprintf.c:485` | `printf_core` | int（RD） | `int`（`*` 宽度） | 否 | B1 |
| `src/stdio/vfprintf.c:498` | `printf_core` | int（RD） | `int`（`.` 精度） | 否 | B1 |
| `src/stdio/vfscanf.c:50` | `vfscanf` | void *（RB） | `%n$` 跳过的指针实参（RB） | 否 | B3 |
| `src/stdio/vfscanf.c:51` | `vfscanf` | void *（RB） | `%n$` 定位指针实参（RB） | 否 | B3 |
| `src/stdio/vfscanf.c:117` | `vfscanf` | void *（RB） | 目标缓冲指针（RB） | 否 | B3 |
| `src/stdio/vfwprintf.c:105` | `pop_arg` | void *（RB） | `%p`/`%s` 的实参（RB） | 否 | B1 |
| `src/stdio/vfwprintf.c:106` | `pop_arg` | int（RD） | `int` | 否 | B1 |
| `src/stdio/vfwprintf.c:107` | `pop_arg` | unsigned int（RD） | `unsigned int` | 否 | B1 |
| `src/stdio/vfwprintf.c:108` | `pop_arg` | long（RD） | `long` | 否 | B1 |
| `src/stdio/vfwprintf.c:109` | `pop_arg` | unsigned long（RD） | `unsigned long` | 否 | B1 |
| `src/stdio/vfwprintf.c:110` | `pop_arg` | unsigned long long（RD） | `unsigned long long` | 否 | B1 |
| `src/stdio/vfwprintf.c:111` | `pop_arg` | int（RD） | `short`/`char` 提升后 `int` | 否 | B1 |
| `src/stdio/vfwprintf.c:112` | `pop_arg` | int（RD） | `unsigned short` 提升后 `int` | 否 | B1 |
| `src/stdio/vfwprintf.c:113` | `pop_arg` | int（RD） | `signed char` 提升后 `int` | 否 | B1 |
| `src/stdio/vfwprintf.c:114` | `pop_arg` | int（RD） | `unsigned char` 提升后 `int` | 否 | B1 |
| `src/stdio/vfwprintf.c:115` | `pop_arg` | long long（RD） | `long long` | 否 | B1 |
| `src/stdio/vfwprintf.c:116` | `pop_arg` | size_t（RD） | `size_t` | 否 | B1 |
| `src/stdio/vfwprintf.c:117` | `pop_arg` | intmax_t（RD） | `intmax_t` | 否 | B1 |
| `src/stdio/vfwprintf.c:118` | `pop_arg` | uintmax_t（RD） | `uintmax_t` | 否 | B1 |
| `src/stdio/vfwprintf.c:119` | `pop_arg` | ptrdiff_t（RD） | `ptrdiff_t` | 否 | B1 |
| `src/stdio/vfwprintf.c:120` | `pop_arg` | void *（RB） | `uintptr` 实参（RB） | 否 | B1 |
| `src/stdio/vfwprintf.c:121` | `pop_arg` | double（RF） | `double`（RF） | 否 | B1 |
| `src/stdio/vfwprintf.c:122` | `pop_arg` | long double（RF） | `long double`（RF） | 否 | B1 |
| `src/stdio/vfwprintf.c:206` | `wprintf_core` | int（RD） | `int`（`*` 宽度） | 否 | B1 |
| `src/stdio/vfwprintf.c:219` | `wprintf_core` | int（RD） | `int`（`.` 精度） | 否 | B1 |
| `src/stdio/vfwscanf.c:50` | `vfwscanf` | void *（RB） | `%n$` 跳过的指针实参（RB） | 否 | B3 |
| `src/stdio/vfwscanf.c:51` | `vfwscanf` | void *（RB） | `%n$` 定位指针实参（RB） | 否 | B3 |
| `src/stdio/vfwscanf.c:140` | `vfwscanf` | void *（RB） | 目标缓冲指针（RB） | 否 | B3 |
| `src/thread/sem_open.c:106` | `sem_open` | mode_t（RD） | `int mode`（RD） | 否 | B3 |
| `src/thread/sem_open.c:107` | `sem_open` | unsigned（RD） | `unsigned value`（RD） | 否 | B3 |

**统计（现场派生）**：`va_arg` **81 处** = **79 处参与本 target 编译** + **2 处 `src/mq/x32/**` 不编译**（`obj/src/mq/x32/` 无 `.o`）。**初判需改 = 2 个文件 / 7 个 `va_arg` 表达式**（`syscall.c` 6 + `fcntl.c` 1）+ **2 个 `syscall()` 调用点**（见下节）。**另 18 个文件只有 `va_start` 无 `va_arg`**（`src/misc/syslog.c`、`src/legacy/err.c`、`src/ldso/dlerror.c` + `src/stdio/` 的 15 个 `va_list` 转发入口：`{as,}printf`/`dprintf`/`f{,w}printf`/`f{,w}scanf`/`snprintf`/`sprintf`/`sscanf`/`s{,w}printf`/`wprintf`/`wscanf`）⇒ **无本册问题**（它们把 `va_list` 交给 `vfprintf`/`vsnprintf`，格式驱动由表内 `B1` 行覆盖）。

**注（审计判定的理由，逐条）**
- **① `semctl` 不改**：`va_arg(ap, union semun)` 就是 POSIX 声明的真实类型；`ADR-0031 D3` 规定 union 不展开 ⇒ 通用聚合 ⇒ RD 1 槽，调用方按 `union semun` 传值也落 RD ⇒ **同 bank**。历史上 `functional/ipc_sem` 的 `Bad address` 属**编译器侧**两侧取法不一致（`LLVM-101t A`），**不是**本册的 musl 封装缺陷。执行期须用探针复核（见验收 3）。
- **② `prctl` 不改**：Linux `prctl(2)` 把 `arg2..arg5` 声明为 `unsigned long`（RD），`argmask(SYS_prctl) = 0`，musl 自身调用点（`src/thread/pthread_{set,get}name_np.c`）也显式 `(unsigned long)` 转换 ⇒ **同 bank**。残留：调用方若传裸指针（文档外用法）会取错 bank（见「残留风险」）。
- **③ `ioctl` 不改（残留）**：第三参的 C 类型**由 request 决定**（`TIOCGWINSZ` 指针、`TIOCSCTTY` 整型），musl 上游统一按 `void *` 读；本 target 的 `argmask(SYS_ioctl) = 0x04` 也按「指针」登记。指针类请求正确；**整型类请求**在本 ABI 下会取 RB 垃圾（探针 `D`）⇒ 本册**不修**（需 request→类型表，另立），如实计入残留风险 + `ISS-271`。
- **④ `open`/`openat`/`sem_open`/`mq_open` 的 `mode_t` 不改**：`mode_t = unsigned int`（RD），与声明的 `int mode` 同 bank；`mq_open` 的 `struct mq_attr *` 本来就是 RB。**不得**为「看起来一致」把这些改成别的类型（无缺陷、改了只增加噪声）。

**执行期复核补正（engineer，2026-10-18；表为交付物，按验收 1 更正 —— 依据见下，均现场派生）**

- **`va_arg` 计数**：`git grep -c va_arg HEAD~1 -- src` = **81**（22 文件）；`va_start` **43**（36 文件，其中 **18** 文件只有 `va_start`）；`src/mq/x32/**` = **2** ⇒ 与本表口径一致。改后 `grep` = **84** = 81 − 1（`fcntl` 原一处）+ 3（按 `cmd` 三分支）+ 1（`syscall.c` 注释里的 `va_arg(void *)` 字样，非表达式）⇒ **表达式 83**。
- **`fcntl` 指针类清单补 `F_GETOWNER_UIDS`（本表与 §改法 B 均漏）**：内核 `fs/fcntl.c:522` → `f_getowner_uids(filp, arg)`，`:308-325` 把 `arg` 当 `uid_t __user *dst` 做 `put_user` ⇒ **指针类**。已按 `void *` 取（`include` 侧 `arch/generic/bits/fcntl.h:46` 有定义）。
- **§调用点一致性 的适用边界（重要，现场实测）**：musl 内部 `syscall(...)` 是**宏**（`src/internal/syscall.h:45` `#define syscall(...) __syscall_ret(__syscall(__VA_ARGS__))`）⇒ 展开为 `__syscallN(SYS_*, __scc(...))`（**固定 `long` 形参**），实参 C 类型不进变参封装，bank 由 `__dadao_trap()` 按掩码搬运。证据：`llvm-objdump --syms lib/libc.a` 中 **0** 个对象引用未定义符号 `syscall`（全库 2118 个函数）；`mprotect.o` 反汇编直接 `rd2rb …; trap cfx0, 0`（无 `call`）。⇒ 「实参 C 类型必须与掩码位一致」只对**外部调用者走 C 封装**成立；§改法 B/C 两处是本册要求的**源形归一**（语义中性），实测无行为差异。
- **重跑数字（`.work/evidence/INFRA-092t/scan_callsites.py`，括号配对 + 掩码表解析）**：`syscall(SYS_*, …)` 顶层调用点 **207 处**（全在 `src/**/*.c`，`ldso/**` = **0**）；其中 **37 处（26 个号名）** 落在端口 `bits/syscall.h` **未定义**的 `SYS_*` 上 ⇒ 不编译（含本表点名的 `src/ipc/shmat.c:14`、`src/unistd/lseek.c:8`）⇒ **实际编译 170 处**。任务书「209 / 2 / 2」：**「2」= 本表点名那两处**（在 37 内）；**「209」现场为 207**（本脚本把 37 处字面命中计入总数；只算可编译则 170）。逐点复核**多出 1 处形状不一致**：`src/mman/mprotect.c:10` 把 `size_t start` 传在地址槽（掩码 `0x01`）——与 §改法 C 同类，但**不改**：非本册范围，且实测无行为影响（`mprotect` 探针 rc=0，`-strace` 显示宿主收到正确页地址），因内部走宏路径；记入残留风险。

## `syscall()` 调用点一致性（本册新增的载重约束）

`syscall()` 改为「按 `__dadao_argmask(n)` 逐槽选 `void *`/`long`」后，**调用点的实参 C 类型必须与该号的 mask 位一致**（此前调用点的类型无关紧要：`syscall()` 一律按 `long` 读、stub 再按 mask 摆位）。全量核对：

- 扫描口径：`syscall(SYS_*, …)` 调用点（含跨行）**209 处**（`src/**` + `ldso/**`；脚本按括号配对解析，`__syscall*`/`syscall_cp` 不算）。
- **不一致 2 处（必须改）**：
  - `src/fcntl/fcntl.c:44`：`syscall(SYS_fcntl, fd, cmd, (void *)arg)` —— 指针表达式落在 **mask 0**（`SYS_fcntl` 的第三参按内核原型是 `unsigned long`，mask = `0x00`）⇒ 改传 `arg`（整数）。
  - `src/misc/getrlimit.c:9`：`syscall(SYS_prlimit64, 0, resource, 0, rlim)` —— 槽 2 是地址位（mask `0x0c`）但传了整型字面量 `0` ⇒ 改传 `(void *)0`。
- **2 处字面命中但目标不编译（不改）**：`src/ipc/shmat.c:14`（`#ifdef SYS_ipc` 分支，`SYS_ipc` 在 DADAO 未定义）、`src/unistd/lseek.c:8`（`#ifdef SYS__llseek`，未定义）—— 现场 `grep __NR__llseek/__NR_ipc obj/include/bits/syscall.h` 均无命中（326 个 `__NR_*`）。
- **其余 205 处**：指针实参落在地址位、整型实参落在数据位（含 `sizeof *buf`、`f->fd`、`x[0]` 等）⇒ 一致。执行期须重跑该扫描并给出「209 / 2 / 2」三数（禁写死，现场派生）。

## 改法（逐文件；允许实现细节重构，语义不许变）

### A. `src/misc/syscall.c`（6 个 `va_arg` → mask 驱动）

参考形态（`__dadao_argmask` 由 `"syscall.h"` → `syscall_arch.h` 引入，`static inline int`）：

```c
long syscall(long n, ...)
{
	va_list ap;
	syscall_arg_t a,b,c,d,e,f;
	int m = __dadao_argmask(n);
	va_start(ap, n);
	a = (m & 0x01) ? (syscall_arg_t)va_arg(ap, void *) : va_arg(ap, syscall_arg_t);
	/* b..f 同法，位 0x02/0x04/0x08/0x10/0x20 */
	va_end(ap);
	return __syscall_ret(__syscall(n,a,b,c,d,e,f));
}
```
约束：**按声明序**逐槽读取（bank 游标只按声明序推进）；未登记的号 ⇒ mask = 0 ⇒ 全 RD（与现状同，见残留风险）。

### B. `src/fcntl/fcntl.c`（1 个 `va_arg` 按 `cmd` 分支 + 1 个调用点）

- 读取分支（**必须覆盖**，`include/fcntl.h` 均已定义）：指针类 = `F_GETLK`/`F_SETLK`/`F_SETLKW`/`F_OFD_GETLK`/`F_OFD_SETLK`/`F_OFD_SETLKW`/`F_GETOWN_EX`/`F_SETOWN_EX`/`F_GET_RW_HINT`/`F_SET_RW_HINT`/`F_GET_FILE_RW_HINT`/`F_SET_FILE_RW_HINT` ⇒ `arg = (unsigned long)va_arg(ap, void *);`
- 整型类：`F_NOTIFY`（Linux 声明为 `long`）⇒ `arg = va_arg(ap, long);`；**其余**（`F_DUPFD`/`F_DUPFD_CLOEXEC`/`F_SETFD`/`F_SETFL`/`F_SETOWN`/`F_SETSIG`/`F_SETLEASE`/`F_SETPIPE_SZ`/`F_ADD_SEALS` 等）⇒ `arg = va_arg(ap, int);`
- 尾部既有 `switch (cmd)` 里 `return syscall(SYS_fcntl, fd, cmd, (void *)arg);` 改为 `return syscall(SYS_fcntl, fd, cmd, arg);`（见上节 mask = 0）。`F_SETLKW` 的 `syscall_cp(SYS_fcntl, fd, cmd, (void *)arg)` **保持原样**（`syscall_cp` 是固定 `long` 形参，不是变参，指针转 `long` 后落 RD，与 mask 0 一致）。

### C. `src/misc/getrlimit.c:9`

`syscall(SYS_prlimit64, 0, resource, 0, rlim)` → 槽 2 传 `(void *)0`（槽 3 `rlim` 本来就是指针）。

### D. 补丁集落盘（`docs/Process-01`；**禁手工编辑补丁**）

- 改 `.work/source/musl/` 工作树 → 本地 commit 保持干净 → `python3 tools/infra/make_patch.py musl` 导出；新增 `components/musl/patches/src/{fcntl/fcntl.c,misc/syscall.c,misc/getrlimit.c}.patch` 与 `series` 三条（**按路径字典序**）。
- `components/musl/changelog.md` 追加 `- **2026-… `INFRA-092t`**` 一条（列表式、追加在 `## M8` 节内按日期序）。

### E. 禁止项

- **禁止**用 `(void *)` 强转掩盖类型错（本册正是要把 bank 选对）；**禁止**改 ABI（`va_list`/调用约定/`syscall_arch.h` 的 mask 表）、**禁止**改 `spec/`/`.tao/contracts/`/`contracts/`、**禁止**改测试语料或期望值、**禁止**改 QEMU 侧 mask。
- 若现场发现 mask 表**本身**有误（如某号指针槽位与内核原型不符）：**不在本册改**（三载体 + QEMU 面 = 跨模块）⇒ 登记 issue 并在完成区写明。

## 接口规范

- **输入**：
  - `.work/source/musl/`（端口源；补丁集真源 = `components/musl/patches/**` + `series`）
  - `.dadao/cross-toolchain/`（安装根；clang/ld.lld/qemu-dadao）
  - `.work/source/libc-test/`（`patchless = true` ⇒ **只读**，禁改）
  - 现场日志：`.work/log/testcases/libc-test-user-{static,dynamic}.log`
- **输出**：
  - `components/musl/patches/src/{fcntl/fcntl.c,misc/syscall.c,misc/getrlimit.c}.patch` + `series` + `changelog.md`
  - `.work/evidence/<任务ID>/run.sh`（一键、非交互、任一失败非零、**含可达 FAIL 注入**）+ 探针源/ELF/日志（长日志另存 `.work/log/infra/`）
  - 本任务书完成区（与真实输出逐条对齐）
- **约束**：只改上述 3 个上游文件（+ 本任务书/台账/证据）；临时产物一律 `/tmp/opencode/INFRA-092t/`；**不跑** `install-host`/`build-*` 以外无关门控（本册必须重编 musl：`make build-musl` / `make build-musl-shared`）。

## 验收标准

1. **全量审计表复核**：执行期重跑 `grep -rn "va_arg" .work/source/musl/src/`（现场派生数字）+ 逐点复核本表；若发现表中遗漏/误判，**补正表并说明依据**（表是交付物之一）。「需改」集合若与初判不同，须逐条给出 bank 判据。
2. **`047t functional/fcntl` 两档 pass**：
   `python3 tools/testcases/run_libc_test_user_suite.py --link-mode static --filter 'functional/fcntl' --json-out .work/log/testcases/INFRA-092t-fcntl-<mode>.json --report-out .work/log/testcases/INFRA-092t-fcntl-<mode>.log`，动态档同法（`--link-mode dynamic`）⇒ 两档 `pass 1 / fail 0`、`first_error` 空。
3. **10 例小样本两档 10/10**（独立 oracle = 用例自身 `t_status`）：
   `--filter '^(functional/(argv|fcntl|env|fnmatch|inet_pton|time)|math/(sin|exp)|api/main|regression/daemon-failure)$'`
   ⇒ 静态 10/10、动态 10/10（`klass == pass`，无 `fail`/`blocked`）。
4. **最小探针（改到的每个封装各一对：指针类 + 整型类）**，期望值独立给出（非从实现反推），全绿：
   - `fcntl`：指针类 `fcntl(fd, F_SETLK, &flk) == 0`、`fcntl(fd, F_GETLK, &flk) == 0` 且写者 pid 一致；整型类 `fcntl(fd, F_SETFD, FD_CLOEXEC) == 0` 后 `fcntl(fd, F_GETFD) == FD_CLOEXEC`、`fcntl(fd, F_DUPFD, 5) >= 5`。
   - `syscall`：指针类 `syscall(SYS_uname, &u) == 0` 且 `u.sysname` 非空；整型类 `syscall(SYS_getpid) == getpid()`（>0）。
   - 复核不改项：`semctl(…, IPC_STAT, arg)`（`union semun`）返回 0 且 `sem_perm.mode & 0x1ff == 0666`（同 `ipc_sem.c` 期望）——用于支撑注 ①。
5. **无回归**：`make build-musl` rc=0、`make build-musl-shared` rc=0、`make check-musl-freshness` PASS、`make check-patch-tree` PASS（新增 3 补丁 + `series` 字典序）。
6. **L1**：`make check` rc=0（含 `check-syscall-abi`、`check-musl-freshness`、`check-milestones-fresh`、`check-knowledge-refs`、`check-no-residue`）。
7. **可达 FAIL**：证据脚本给出「注入 ⇒ FAIL ⇒ 还原 ⇒ 回绿」的真实输出 —— 注入方式 = 把 `fcntl` 的读取分支临时改回 `va_arg(ap, unsigned long)`（`cp` 备份 + md5 对账；**禁** `git checkout`/`restore`/`stash`），重编 musl 后 `functional/fcntl` 必须 FAIL（同一 `Bad address`），还原后回 `pass`；另给 `syscall(SYS_uname)` 的同类注入（读 `syscall_arg_t`）一条。注入不得留在最终补丁里（`git diff` 核对）。
8. **记录**：完成区贴真实命令 + 退出码 + 关键输出；长输出留 `.work/log/infra/`。**禁**用叙述替代输出。

## 残留风险（必须如实写入完成区，不得宣称全覆盖）

- **变参里的「指针/整数双关」是 C 标准 UB** ⇒ 用户代码自己把指针按整数传、或把整数按指针传，本册**不覆盖**：典型 = `ioctl(fd, TIOCSCTTY, 0)`（整型请求，注 ③）、`prctl(op, ptr)`（文档外用法，注 ②）、`syscall(SYS_ioctl, fd, req, 0)` / `syscall()` 传 `0` 占地址槽（新增：mask 驱动后这类调用会取到 RB 垃圾 —— 本册已修 musl 自身的 1 处，用户代码不代修）。
- `syscall()` **未登记的号** ⇒ `__dadao_argmask` 返回 0 ⇒ 全部按 RD 读（既有覆盖口径；新增号须同步三载体，`make check-syscall-abi` 管）。
- `fcntl` 的**新命令**（内核新增）若第三参是指针而本册默认分支按 `int` 读 ⇒ 需补表；现状已覆盖 `include/fcntl.h` 里全部指针类命令。
- `ioctl` 的整型请求未修（见注 ③）⇒ 已在 `ISS-271` 备注，属**能力缺口**（需 request→类型表），不是本册返工项。

## 完成区
**测试结果**：证据脚本 `.work/evidence/INFRA-092t/run.sh` **45/45 PASS、rc=0**（log `.work/log/infra/INFRA-092t-evidence.log`）；`make build-musl` rc=0（**13.6 s**，10/10 ELF 检查）、`make build-musl-shared` rc=0（**12.9 s**，38 PASS）、`check-musl-freshness` PASS（sha256 `ceca1fe0…`）。`047t`：`functional/fcntl` **静态 1/1、动态 1/1**（原 `Bad address`）；10 例小样本 **静态 10/10、动态 10/10**；无回归 **静态 16/16**（`ipc_msg/ipc_sem/ipc_shm/socket/stat/utime/iconv_open/dirname` + 6 `regression/*` + `math/{sin,exp}`）。
**修改文件**：`.work/source/musl/src/{fcntl/fcntl.c,misc/syscall.c,misc/getrlimit.c}`（组件检出收敛 `base+1`，commit `e02280b`，worktree 干净）；`components/musl/patches/src/{fcntl/fcntl.c,misc/syscall.c,misc/getrlimit.c}.patch` + `series`（**19 → 22**，字典序）+ `changelog.md`（M8 追加一条）；`.work/evidence/INFRA-092t/{run.sh,probe.c,probe-accept.c,scan_callsites.py,probe*.{out,elf},scan*.txt,run.log}`；本任务书（审计补正 + 完成区 + 自审）。**未碰** `LLVM-102t` 的 13 改 + 3 新。
**验收结果**：
1. 审计复核：`va_arg` 81（22 文件）/`va_start` 43/18 文件仅 `va_start`/x32 2 —— 与表一致；补正 3 条（`F_GETOWNER_UIDS` 指针类、宏路径边界、mprotect 行）见「执行期复核补正」。
2. `047t fcntl` 两档：`mode=static … total=1 pass=1 fail=0`、`mode=dynamic … total=1 pass=1 fail=0`（json/log `INFRA-092t-fcntl-{static,dynamic}.*`）。
3. 10 例小样本：静态/动态均 `total=10 pass=10 fail=0 blocked=0`。
4. 探针（改前 → 改后，见 `probe.out` → `probe-after.out`）：`A` 0→0、`B` addr→addr、`C` 77→77、`D` 39f10→39320（RB 仍空，符合 ABI）、`E` `-1 errno=14 sysname=''`→**`0 errno=0 sysname='Linux'`**、`F` 3→3、`G` 0→0、`H` 0→1→0→1、`I` **`-1 errno=14`→`0 errno=0`**。oracle = POSIX/Linux 语义手算：`uname` 成功填非空 `sysname`、`F_SETLK` 对空文件成功 0、`F_GETLK` 无他人锁 ⇒ `F_UNLCK`、子进程 `F_GETLK` 的 `l_pid == getppid()`、`F_DUPFD>=5`、`F_SETFL` 后 `F_GETFL` 带 `O_NONBLOCK`、`getrlimit` `rlim_cur>0`、`semctl` 0666 回读 `0666`、`prlimit64(NULL,&rl)` 0；`probe-accept` **30/30 PASS**。
5. 无回归：见上；`check-patch-tree` **180 补丁**（177 → 180，+3）。
6. L1：`make check` **rc=0「repository checks (L1): PASS」**。
7. 可达 FAIL（同次前台闭合、`cp`+md5、`git diff` 证明注入非空）：① `fcntl` 读回 `va_arg(ap, unsigned long)` ⇒ 重编后 `functional/fcntl` **fail=1 / Bad address**，还原（md5 `6f906d67…` 一致）后 **pass=1**；② `syscall()` 读回 6×`syscall_arg_t` ⇒ `probe E` **`= -1 errno=14`**，还原（md5 `9ed9d13d…`）后 **`= 0 errno=0 sysname='Linux'`**；收尾 `musl worktree clean` + freshness PASS。
8. 记录：长输出在 `.work/log/infra/INFRA-092t-*.log` 与 `.work/log/testcases/INFRA-092t-*`。
**新发现/坑**：① **musl 内部 `syscall()` 是宏**（`src/internal/syscall.h:45`）⇒ 内部调用点不进变参封装、bank 由桩按掩码搬；`libc.a` 内 **0** 个未定义 `syscall` 引用。所以「调用点 C 类型 vs 掩码」对 musl 自身是**空约束**，本册的真缺陷只在**变参封装**（`fcntl`）与**外部调用者的 C 封装**（`syscall`）。② 本表漏了 `F_GETOWNER_UIDS`（内核 `f_getowner_uids` 解引用 `arg`）——已补。③ `build_musl.py` 在源摘要变化时 `make clean`，静态档重编会删掉 `lib/libc.so` ⇒ 证据脚本必须在注入循环**之后**重跑 `build-musl-shared` 才能过 freshness。④ `va_arg(ap, syscall_arg_t)` 读调用方按 `int` 传的槽是 C 标准 UB（8 B canonical 槽使其可行）——既有做法，未扩大。
**遗留问题**：① `ioctl` 整型请求（注 ③，需 request→类型表，`ISS-271`）**不修**；② 用户代码自身把指针按整数传（`ioctl(TIOCSCTTY,0)`、`prctl(op,ptr)`、`syscall(SYS_ioctl,fd,req,0)`）不代修；③ `__dadao_argmask` 未登记号 ⇒ 全 RD（既有覆盖口径）；④ `fcntl` 新增内核命令若第三参为指针需补 `fcntl_arg_is_ptr` 表；⑤ `src/mman/mprotect.c:10` 的 `size_t`→地址槽形状不一致**保留**（非本册范围、实测无影响）。本册**未**跑 `install-host`/`build-qemu`/L2/L3，**未** commit/push 仓库，**未**改 `**状态**`。

## 审阅记录

#### 第 1 轮 engineer 自审

- 逐行审查 `src/misc/syscall.c`：`m` 只算一次；6 条赋值**独立语句**（不在同一表达式中放多个 `va_arg`，避免求值顺序未定义）；每条只在命中位时取 `void *`、否则取 `syscall_arg_t`，与 `ADR-0031 D1/D3` 的「bank 游标只按声明序推进」一致；`__dadao_argmask` 由 `"syscall.h"`→`syscall_arch.h` 引入（`static inline`，无新符号）。查 `llvm-objdump --syms`：`syscall` 仍是单一定义、无内部引用。
- 逐行审查 `src/fcntl/fcntl.c`：`fcntl_arg_is_ptr` 覆盖 `include/fcntl.h` + `arch/generic/bits/fcntl.h` 的全部指针类命令（复核内核 `fs/fcntl.c` 的 `case` 表后补 `F_GETOWNER_UIDS`）；`F_NOTIFY` 按 `long`、其余按 `int`（与 `man 2 fcntl` 的 `int`/`long` 声明一致）；`F_SETLKW` 仍走 `syscall_cp`（固定 `long` 形参，不动）；`F_GETOWN` 回退路径仍走 `__syscall`（不动）。`arg` 仍为 `unsigned long`，后续 `arg |= O_LARGEFILE`、`F_DUPFD*` 用法语义不变。
- 逐行审查 `src/misc/getrlimit.c`：仅槽 2 由 `0` 改 `(void *)0`（槽 3 `rlim` 原本即指针），`ret`/`FIX`/`#ifdef SYS_getrlimit` 分支未动。
- 反造假：所有结论取自本次真实命令输出；`run.sh` 两次全量跑（`--no-gates` 修 2 个自身缺陷后全绿），注入用 `cp`+md5、未用 `git checkout/restore/stash`；`git -C .work/source/musl status` 收尾为空。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `syscall()` 6 槽须按掩码分 bank | ✅已修 | 6 个 `va_arg` 改条件取型 | 探针 E/I、raw `prlimit64`、注入②红→绿 |
| F2 `fcntl` 指针类清单漏 `F_GETOWNER_UIDS` | ✅已修 | 加入 `fcntl_arg_is_ptr` | 内核 `fs/fcntl.c:522/:308`；`make build-musl` rc=0、fcntl 两档 1/1 |
| F3 §调用点一致性 前提对 musl 内部不成立（宏） | ✅已核实并披露 | 无代码改动，写入审计补正 + 完成区 | `internal/syscall.h:45`；`libc.a` 0 个未定义 `syscall`；`mprotect.o` 反汇编 |
| F4 `mprotect.c:10` 形状不一致 | ⏸延后（非本册范围） | 不改 | `mprotect` 探针 0 + `-strace` 正确页地址 |
| F5 证据脚本静态重编后 freshness 必红（`libc.so` 被 clean） | ✅已修 | 注入循环后补 `build-musl-shared` | `run.sh` 由 rc=1 → rc=0（45 PASS） |
| F6 探针 B 断言恒 FAIL（`0x?` 正则要求前导 0） | ✅已修 | 正则改 `(?:0x)?` | `probe-checks.txt` 10/10 PASS |

#### 第 1 轮 reviewer 验收
**重跑（2026-10-18 独立）**：`run.sh` **45 PASS / 0 FAIL rc=0** ✓（含 build+probes+suites+injects+gates）。
- **注入①**（fcntl 读回 `va_arg(ap, unsigned long)`）：functional/fcntl **fail=1 / Bad address**，cp+md5 还原后 **pass=1** ✓。
- **注入②**（syscall 读回 6×`syscall_arg_t`）：probe E **`= -1 errno=14`**，cp+md5 还原后 **`= 0 errno=0 sysname='Linux'`** ✓。
**逐条核验**：① 审计表 va_arg HEAD~1=81、HEAD=84（+3 fcntl 分支 +1 注释），表达式 83 ✓；② functional/fcntl 静态/动态 1/1 ✓；③ 10 例两档 10/10 ✓；④ 探针 E=0 errno=0 sysname='Linux'、I=0 errno=0、probe-accept 30/30 ✓；⑤ build-musl/musl-shared rc=0、check-musl-freshness PASS、check-patch-tree 180 ✓；⑥ L1 rc=0 ✓；⑦ 两注入+还原+回绿 ✓。
**约束**：只改 musl 3 个文件 + series/changelog ✓；一文件一补丁 ✓；未碰 spec/contracts/LLVM-102t ✓。
**如实性抽查**：va_arg HEAD~1=81（`git grep -c`）✓；probe E/I exact match ✓；series=22、patches 180 ✓。
**判决**：**Accepted**。

#### 第 1 轮 architect 提交（待验收）
**档位**：`待验收`（实现完成 + 自审通过；reviewer 未验）⇒ 正常提交（本任务分支第 2 笔）；`**状态**` 由 `待开始` 置 `待验收`（不改写完成区述评）。
**文件集对账**：`git diff --cached --name-only` = **9 项** = 3 新补丁（`src/fcntl/fcntl.c`/`src/misc/syscall.c`/`src/misc/getrlimit.c`）+ `components/musl/series`（19→22）+ `components/musl/changelog.md` + 本册 + 台账 3（`milestones.md` 本行 / `INTEG-036m` 进展条 / `issues.yaml`：`ISS-271` 收口 + `ISS-267` 追加）；与完成区「修改文件」逐条对齐，**无漏提 / 无多提 / 无越界**（`components/llvm-project/**` 全归第 1 笔 `LLVM-102t`）。
**门控（真实 rc）**：`make check`(L1) rc=0「repository checks (L1): PASS」；`check-patch-tree` **180 patches OK**；`check-musl-freshness`/`check-syscall-abi`/`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-milestones-fresh` 各 rc=0；`check_issues` rc=0（67 open / 27 closed，`ISS-271` `closed` + `resolved_by: INFRA-092t`）。
**证据**：本册完成区 + `.work/evidence/INFRA-092t/run.sh`（45/45 PASS，engineer 提供；architect 未重跑）。
