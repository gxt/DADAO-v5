# LTP 子集（m18-linux-006）

第二块套件：把 **Linux Test Project**（`manifests/components.lock.toml` 锁定的
commit `2279d708…`，tag `20260930`）按 `tests/unit/linux/suite/ltp/suite.yaml`
选出的用例，静态构建进 `m18-linux-005` 的同一套运行骨架，在 QEMU
`-M kaiwu-vast` 上逐例执行并在库记录分诊。

一条命令（与 kselftest 试点共用 runner，只换套件名）：

```sh
python3 tools/linux/suite/run_suite.py --suite ltp
```

它依次做：**交叉构建 LTP 子集 → 生成 suite initramfs → 重建带该镜像的内核 →
启动 QEMU → 按用例归属输出 → 写 `results.json` + `summary.txt` → 跑本套件的校验**。
退出码只反映骨架自身（构建/启动/记录/校验失败才非零）；单个用例判红本身不决定退出码。

## 文件

| 文件 | 作用 |
| --- | --- |
| `suite.yaml` | 子集清单：`kind: ltp`、`dir`（LTP `testcases/` 下的相对目录）、`prog`、guest 侧超时、**记录的基线 verdict**、`stall` 标记 |
| `triage.yaml` | 在库分诊台账：每条非 PASS 一行（分类 + 证据 + 复评条件） |
| `config.h` | 交叉目标要用的 `config.h`（见下「为什么要自己的 config.h」） |
| `../check_suite.py` | 校验入口，加 `--suite ltp` |

本轮子集（14 例）：**14 例全部 PASS**。`m18-linux-018` 补齐了套件镜像环境：
supervisor 为每个用例导出 `PATH=<用例镜像目录>:/bin`（`fcntl07` 的 `execlp`），
镜像带最小 `/etc/passwd`（`mlockall02` 的 `getpwnam("nobody")`）；`mlockall02`
此前的 `die-no-vma va=0x10` 是缺 passwd 导致的 NULL 解引用，内核的 SIGSEGV 投递
本身正确，不是内核缺陷。`triage.yaml` 现为空。

构建器是 `tools/linux/suite/build_ltp.py`，补丁集是**组件补丁**
`components/ltp/{series,patches/}`（`docs/Process-01`），由
`python3 tools/infra/apply_series.py --component ltp` 落到
`.work/source/ltp`。

## 子集怎么选、怎么扩

选型口径 = M18 出口条件点名的系统调用面（文件 I/O、`mmap/mprotect/munmap`、
`brk`、`clone/futex`、`execve/wait4`、基本信号、`clock_*`/`timerfd`），每个面取
代表用例，优先选**不依赖 LTP 安装树**（`LTPROOT`/`datafiles`）、不依赖帮助程序
在 `PATH` 里的用例。`suite.yaml` 每条 `note` 写明选它的理由与**预期 TCONF 条件**。

新增一条用例：

1. 在 `suite.yaml` 加一行：`id`（唯一，建议 `ltp-` 前缀）、`kind: ltp`、
   `dir`（LTP `testcases/` 下的相对目录）、`prog`（该目录里的程序名）、
   `timeout`（**guest 侧**秒数）、`expect`（**当前实况**）。
2. 跑 `run_suite.py --suite ltp`；若非 PASS，就在 `triage.yaml` 加一行，写清
   分类、证据（用例输出原文一行 + 退出码）与复评条件。
3. 依赖本机没有的设施（安装树、`PATH`、`/etc/passwd`、信号帧）就记
   `SUITE_ENV`/`UNSUPPORTED`，**不要**改测试去凑绿。

用例若**会让整机停摆**（本轮 `mlockall02` 即如此），在 `suite.yaml` 标
`stall: true`：它单独占一次启动、排在最后，其余用例不受影响；结果记
`HOST_TIMEOUT`（guest 侧 alarm 不会触发，宿主看门狗是唯一兜底）。

## 分诊四类（与 kselftest 试点同一口径）

- `KERNEL_BUG`：内核行为错（复现 + 证据 + 复评条件，本任务不修）。
- `TEST_ADAPT`：用例把别处的假设写死（4 KiB 页、大端、glibc 扩展、系统调用重启）；
  修法在 `components/ltp/patches/`（一文件一补丁，`docs/Process-01`）。
- `UNSUPPORTED`：本移植**没有**该设施。
- `SUITE_ENV`：环境暂不具备（镜像无 `/etc/passwd`、无 `PATH`、无安装树），
  写明依赖与重跑条件。

**判定源**：LTP 把结果类 OR 进退出码（`lib/tst_test.c::do_exit`）——
`1`=FAIL、`2`=TBROK、`32`=TCONF（全跳过）、`4`=仅告警。`run_suite.py` 按位
判读（`ltp_verdict`），不按数值猜；被信号杀记 `SIGNAL`，无 `SUITE CASE END`
记 `HOST_TIMEOUT`。

## 本轮的适配补丁（components/ltp/patches）

- `lib/safe_macros.c.patch`（TEST_ADAPT）：`safe_waitpid()` 对 `EINTR` 重试。
  本移植把 `-ERESTARTSYS` 直接变成用户可见的 `EINTR`、**没有系统调用重启**
  （`arch/dadao/kernel/signal.c` 明写「Syscall restart is not this file's
  business … m14-linux-023」）。LTP 的 `tst_test` 在子进程启动时向父进程发
  `SIGUSR1` 心跳，父进程正在 `waitpid`，于是每个新接口用例都在第一条断言之前
  被记成 `TBROK: waitpid(...): EINTR`——这是**测试脚手架的等待**，不是断言，
  所以重试；缺系统调用重启本身仍作为内核缺口记录在「已知边界」，没有隐藏。
  该内核缺口已登记 **`ISS-m18-007`**（`-ERESTARTSYS` 一律转 `-EINTR`），
  复评条件 = 内核引入系统调用重启后删除本补丁；验收口径同任务书 #3：
  优先 64 KiB/大端，本子集实测无 4 KiB 假设时接受 harness 级适配，但缺口必须入 ISS。

  补丁前后对照（同一内核、同一 QEMU）：
  - 前：`open01`/`mmap01`/`munmap01` … 全部 `TBROK rc=2`，`case_output` =
    `waitpid(18,…,0) failed: EINTR (4)`；
  - 后：`open01`、`read01`、`lseek01`、`fstat02`、`wait01`、`clock_gettime01`、
    `mmap01`、`munmap03` 等给出真实 `PASS`。

**没有 64 KiB 专用补丁**（结果，不是漏项）：返工点名的 64 KiB 候选
`mmap01` 在干净内核上 **PASS**——它把 12 字节文件映射成一个 64 KiB 页、越过
EOF 写、再 `msync(MS_SYNC)`，所有长度都来自 `getpagesize()`，没有 4 KiB 字面量
可改；`munmap03` 的非法地址也由 `getpagesize()` 派生。**14 例源码里 `4096`
字面量计数为 0**，即本子集确实没有 4 KiB 假设可适配；唯一的 `TEST_ADAPT`
是 harness 级的 `safe_waitpid`（对应内核缺口 `ISS-m18-007`）。`brk01` 的阻塞是 musl
`brk()` 桩（`src/linux/brk.c` 返回 `ENOMEM`），与页大小无关。

## 为什么要自己的 `config.h` / `config.mk`

LTP 的构建依赖 Autotools 生成的 `configure`，但上游**不发布**生成物（只有
`configure.ac`），本机也没有 autoconf/automake；而它的探测大多是
`AC_RUN_IFELSE`（跑一个程序看结果），交叉目标根本跑不了。所以
`build_ltp.py` 直接写出 configure 会写的两个文件：

- `include/mk/config.mk`：CC wrapper（静态 musl）、工具、前缀（都在运行期目录内，不入库）；
- `include/config.h`：**入库数据** `config.h`，逐条注明「为什么这个目标是 1」，
  并由 `PROBES` 里每宏一条编译探针验证——探针不过即构建失败
  （`python3 tools/linux/suite/build_ltp.py --check-config`），绝不静默退回 LTP
  自带的 fallback shim。

链接口径：静态 musl，**只用公共头**（`include`、`arch/dadao`、`arch/generic`、
`obj/include`）。kselftest 的 wrapper 额外带 musl 源码内 `src/internal`，那里把
`weak` 定义成宏，LTP 的普通标识符会被替换掉，因此 LTP 单独生成 wrapper。

`lib/tlibio.c`（旧 `test.h` 的 LIO 封装）显式过滤掉（`FILTER_OUT_LIBSRCS`），
它只被老接口的 lio 用例使用，本子集不用；过滤项进库指纹，取消过滤即强制重建。

## 运行期环境的三个前置（必须对账）

- **写者互斥**：`.work/source/linux` 与 `.work/build/linux` 是共享的。别的任务
  （本轮 `m18-linux-023`）就地改源/重建时，读方的内核是「半改写」的，会出现
  假红（本任务实测：`cause=CFXMEM(0x10000000000002)`、随机的 `die 0xe1/0xec`）。
  跑内核相关套件前要么等写者结束，要么用 `DADAO_LINUX_SOURCE` /
  `DADAO_LINUX_BUILD` 指向自己重放的锁定树（两者会把 suite 根一起搬走）。
  本轮用**本 worktree 的私人重放**：`.work/source/{linux,qemu,musl}` 从锁定
  commit 重建并按当前 `components/{linux,qemu,musl}/series` 打补丁（105 / 69 /
  26 条），`.work/build/{linux,qemu}` 与共享安装根完全分离；
  `check-patch-tree` 三个组件段均 0 problem。
- **QEMU 与内核必须是同一套 cause 模型**。私人构建的 `qemu-system-dadao`
  （md5 `4f762023…`，`--version` 尾部 `g53e83aa` = 当前 qemu 补丁提交）与
  0.8.1-rc 内核配对；安装根二进制是**旧的 jmon 时代构建**，`check-patch-tree`
  的 qemu 段对它报 8 个 assertion，故本轮不用它，也不覆盖安装根。
  `run_suite.py` 支持 `SUITE_QEMU=<path>` 固定二进制并把它写进
  `results.json` 的 `qemu_cmd`；本任务两轮均用该私有二进制。
- **`make fetch` 只把组件拉到锁定 commit，不打补丁集**：构建/门控前必须
  `python3 tools/infra/apply_series.py`（全组件）或 `--component ltp`。

## 已知边界（本轮实况 + 阻塞证据）

- **用户态信号投递已恢复**（`m18-linux-024`）：上一轮 `MALIGN(0x1000)
  ip=0x200001533fc info=0xfffeffff7fff` → `die mode=2 code=0xec` 与
  `die 0xe1`（`va=0x208`）在本轮 17 次完整跑与 1 次单例跑中 **0 次**出现；
  `mlockall02` 的 NULL 解引用现在是正常投递（`die-no-vma` 后 LTP 捕获
  SIGSEGV → TBROK），不再打死内核。
- **残余偶发停摆（内核侧，未闭合）**：把 13 个普通用例放在同一个 guest boot
  连跑时，偶发出现**无 die 停摆**——控制台最后一段是一条 `K3 pf`（末次
  `result=fill-file`）或 `K2 async user`，之后无输出；宿主 120 s 无进展判
  `stop_reason=idle`（qemu_rc=124），其后的用例 `MISSING`。**合并样本 13 轮
  （engineer 4 + reviewer 9）flake 8 轮，Wilson 95% ≈ [0.36, 0.82]**
  （engineer 2/4 [0.15, 0.85]、reviewer 6/9 [0.35, 0.88]）；用例名随机
  （munmap03 / mmap01×2 / fcntl07 / fstat02×3 / read01），最长连续 flake 3
  ≤ 每轮上限 3。每次 flake 都**没有** `handle_softirqs`/`die mode=` 签名，
  `ISS-m18-006` 计数 0，归 `ISS-m18-005` 族（随机 `HOST_TIMEOUT`，已见
  `mm-pfnmap`/`mm-map-populate`/`futex-wait-timeout`）。套件基线取连续两次
  无停摆完整跑的逐例 verdict（两轮完全相同）。`m18-linux-025` 已闭合其
  `ISS-m18-001` 自旋根因（umon 返回路径关 supv 异步门），本项是残余的另一签名。
- **系统调用重启未实现**（`-ERESTARTSYS` → `EINTR`，见上，`ISS-m18-007`）：
  适配补丁只让 LTP 脚手架的等待重试，不是内核修复；复评条件 = 内核实现系统调用
  重启后删掉该补丁。
- **`brk01` 不可用**：musl 的 `brk()` 是 `-ENOMEM` 桩（`src/linux/brk.c`），测试
  的 libc 变体直接 `TCONF`，随后退出路径也会停摆；记在「候选但未入子集」。
- **需要 `PATH` 的用例**（`fcntl07`、`execve01` 用 `execlp`/`tst_get_path`）：
  supervisor 已为每个用例导出「自身镜像目录 + `/bin`」，`fcntl07` 因此 PASS；
  `execve01` 可按下节条件复评后入子集。
- **需要块设备/mkfs 的用例**（`mmap16`、`stat04`、`lstat03`）不在子集：镜像
  没有 `/dev` 块设备。
- **`mprotect04` 的 PROT_EXEC 子例 TCONF**：`config.h` 没有 `HAVE_CLEAR_CACHE`
  （`__clear_cache` 可用性未探测），子例记 `SUITE_ENV`；补该宏 + 探针后即可运行。
- **静态链接**：镜像内无动态加载器（`m18-infra-002` 已打通构建侧，镜像未启用），
  需要 DSO 的用例记 `SUITE_ENV`。

## 候选但未入子集（复评条件）

- `msync01/02/03`、`mmap02/03/04/11/13/17`、`mprotect01/02/03`、`munmap01/04`、
  `timerfd01`、`fcntl34`、`clone02`、`futex_wait01`、`nanosleep01`：在共享树被
  并发改写期间跑过，判定不可信；其中 `msync01`/`mmap02`/`mprotect02`/`munmap04`
  命中上面的信号投递故障。复评：`m18-linux-024` 修复后在私人重放里逐个
  `--only` 复跑，通过的再入子集。
- `execve01`：`PATH` 已由 `m18-linux-018` 补入 supervisor，可按 `--only` 复跑确认后入子集。
- `brk01`：见「已知边界」。

## 复现与复评

```sh
make fetch                                   # 取到锁定 commit（.work/source/ltp）
python3 tools/infra/apply_series.py --component ltp
python3 tools/linux/suite/run_suite.py --suite ltp
python3 tools/linux/suite/run_suite.py --suite ltp --only ltp-mmap01   # 单例调试
python3 tests/unit/linux/suite/check_suite.py --suite ltp --latest
python3 tests/unit/linux/suite/check_suite.py --suite ltp --patches-only  # 源树来源核查

# 与写者互斥时（另一个任务在改共享内核树）：私人重放
DADAO_LINUX_SOURCE=<replay> DADAO_LINUX_BUILD=<build> \
  python3 tools/linux/suite/run_suite.py --suite ltp
```

运行期产物（控制台全日志、`results.json`、逐例构建日志）在
`tools/linux/suite/suite_paths.py` 解析出的运行期目录里；每例原始输出由
`SUITE CASE BEGIN <id>` / `SUITE CASE END <id> rc=… status=…` 包住，可逐字定位。
