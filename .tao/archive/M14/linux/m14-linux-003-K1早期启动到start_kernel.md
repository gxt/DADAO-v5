# m14-linux-003: K1 内核早期启动到 `start_kernel`（Vast）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-002`（vmlinux 骨架）、`m14-qemu-001`（Vast smon 交接）、`m14-spec-003`（VA 窗口）——均已验证
**可并行分片**：否
**预估**：2–3 h
**状态**：已验证

## 用户裁定（2026-11-14，原话）

> 「1、现在启动K1；内核所有开发都是在qemu-system vast上进行；…smon的时候应该就开启了PTBR，能进入start_kernel，开启时钟之前打印信息退出，我觉得K1就算完成」
> （控制台）「semihosting」

## 现状（K0 已完成，现场）

- Vast 上 `power → hmon → smon` 已通：smon 预建单超页表、`PTBR=0`、`ptw_enable=1`、VA 入口 `0x0200_0001_0100`、boot info 15 字段（`m14-qemu-001` 实测）；
- `vmlinux` 由 `arch/dadao` 骨架产出（56 补丁），能**进入内核窗口**但不自行退出（`m14-linux-002`）；
- 进入时：模式 `supv`、`rb17`=boot info VA、`rb16`=入口 VA、`rb3`=0、**SP 未定义**、异步中断全屏蔽（`ADR-0051 D6`）。

## 范围

1. `arch/dadao/kernel/head.S`：在任何栈使用前自建 **early stack**；保存 `rb17`（boot info VA）/`rb16`；按 `Kaiwu §6.3` 解析 boot info 15 字段（校验 magic/version/size，非法即早退）；
2. 跳到 C 的 `start_kernel()`：本任务只要求"到达并打印"，**不做**子系统初始化；
3. **early console**：`supv` 下 `trap cfx, 0x3FF00` + semihosting `SYS_WRITE`/`SYS_WRITEC` 输出（**不引入 UART、不新增 cfx**）；打印内容至少含 `bootinfo.magic/version/kernel_size/hart_id` 与一行动工标记；
4. **退出**：在开启任何时钟/中断之前，用 semihosting `SYS_EXIT(0)` 正常退出（K1 的判据边界就到这里）。

## 验收（逐条贴真实输出）

1. **端到端**：`make build-linux`（或等价目标）产出 vmlinux；在 `kaiwu-vast` 上以 `bootrom-image + -kernel` 启动，**guest rc=0**；
2. 输出**逐行可核**：至少一行 `K1 bootinfo magic=… version=… size=… hart=0`，且值与构建参数一致（不写死）；
3. **进入 `start_kernel` 的证据**：在 `start_kernel` 首行打印标记（如 `start_kernel`），或提供等价的可观测证据；
4. **栈自建证据**：SP 未定义进入 ⇒ `head.S` 在第一次压栈前设好 SP（代码 + 运行时打印 SP 值）；
5. **boot info 负例**：构造 magic 错 / size 错的 boot info（改 smon 侧或用探针镜像），内核应**具名拒绝并退出非零**，不得跑进 `start_kernel`；
6. 可达 FAIL 注入 ≥2 路（破坏 boot info 校验；把 early console 的 SYS_WRITE 参数块改错 ⇒ 输出乱/无输出），`cp`+md5 还原；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`**；`build-linux` 可用（`JOBS=32`），**禁边构建边测试**。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `components/linux/**`（`arch/dadao` 补丁）、`components/linux/changelog.md`、`tools/linux/**`（探针/门控如需）、必要时 `tools/qemu/k0_boot_probe.py` 的 **K1 模式**；**不改** `spec/`、`contracts/`、`tests/**`、QEMU/chipyard RTL。
5. **只在 `qemu-system vast` 上开发与验收**（内核不跑 Tiny）；派前查节点/主控机资源，测试与构建不并行。

## 待裁定

1. **semihosting 的参数指针是 PA 还是 VA**（自决：PA）。实测 QEMU 的 `dadao_cpu_translate_for_debug()` 只做 identity（不看页表），而 `SYS_WRITE0` 的长度探测 `uaccess_strlen_user()` 走 `probe_access_flags()`（看页表）⇒ 在 Vast+PTW 下**没有**任何地址能同时满足两条路。本任务改走 `SYS_WRITEC`（只走 identity 的拷贝路）并显式传 PA（与 `tests/shared/bootrom/k0/probe_kernel.S` 的既有口径一致）。建议后续二选一：(a) 修 QEMU，让 semihosting/debug uaccess 按 PTW 翻译（并统一 strlen 与 copy）；(b) 在 `contract-semihosting`/`Kaiwu §5` 明确「semihosting 指针 = PA」。未决期间不影响 K1 判据。
2. **`start_kernel()` 首句的钩子放在通用 `init/main.c`**（自决）。arch 侧既有钩子（如 `smp_setup_processor_id`）会被同 TU 的 `__weak` 空定义在编译期内联掉（实测调用落到 0x…330 的空 `ret`，arch 的强符号调不到），无法只靠 arch 实现「首句停住」。现用 `#ifdef CONFIG_DADAO_K1_EARLY_STOP`（默认 y）三行钩子，K2 关选项即恢复上游序列；若用户不接受通用文件改动，需另给替代方案。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `smp_setup_processor_id()` 钩子调不到（同 TU `__weak` 空定义被内联，`start_kernel` 实际 call 0x…330 的空 `ret`） | ✅已修 | 改 `start_kernel()` 首句 `#ifdef CONFIG_DADAO_K1_EARLY_STOP` → `dadao_k1_early_stop()`（新 Kconfig 选项，默认 y） | objdump：`start_kernel` 首条 call 指向 `dadao_k1_early_stop`；运行时 `ra=0x20000110364 base=0x20000110348 off=0x1c inside=yes` |
| F2 K0 `br.eq {rb2, rb3}?`：`br.eq` 只比较 **rd** 寄存器（SimRISC-06 §1），原写法比较的不是 bss 游标 | ✅已修 | 游标/上界镜像到 rd2/rd3 并同步递增 | 清零循环迭代数 = `(0x5c0000-0x560000)/8`（现场 49152），末次 PC 落在 `.Lbss_done` |
| F3 K0 把 semihosting 服务号放在 `immu18[7:0]`（`trap cfx0,0x3ff04`），与 `contract-semihosting §1`/QEMU（读 `rd16`）不符，一旦执行即 abort | ✅已修 | head.S / early_console.c / traps.c 统一为 `rd16`=服务号、`rb16`=参数块、`trap cfx0,0x3ff00` | 正向/负例输出与退出码均正常（含 `SYS_EXIT`） |
| F4 失败码 `0x100/0x101/0x102` 经 `SYS_EXIT` 回绕成宿主 0（`0x100&0xFF==0`）⇒「非零退出」判据失效 | ✅已修 | 失败码改 `0xE1`–`0xE8` 并注释理由 | 负例实测 rc=225(`0xE1`)/227(`0xE3`) |
| F5 `__pa()` 是 64 位减法，进位落在 bit48；semihosting 读寄存器原值（不像取指/访存会截 48 位）⇒ 指针越界、静默无输出 | ✅已修 | `DADAO_SEMIHOST_PA()` 显式截 48 位（`contract-abi §1.7`） | 注入 I2（传 VA）⇒ 无输出、probe 红；还原回绿 |
| F6 `__builtin_return_address(0)` 在 DADAO 上折叠为 0（未实现）⇒ `inside=no` 误拒 | ✅已修 | 用 `ra2rd {rd},{ra63}` 在首次 call 前读 RAS 顶（`SimRISC-06 §3`） | objdump：`ra2rd` 在首条 `call` 之前；运行时 `ra` 落在 `start_kernel` 内 |
| F7 `SYS_WRITE0`（0x04）在 Vast+PTW 下不可用：长度探测走页表、拷贝走 identity | ✅已修 | early console 改 `SYS_WRITEC`(0x03) 逐字节 + 文件头写明两条路差异 | 正向输出完整；负例/注入输出符合预期 |
| F8 还原用 `cp -p` 保留旧 mtime ⇒ Kbuild 不重编，probe 假「仍红」 | ✅已修 | 证据脚本改 `cp` + `touch`，md5 相等后再重构建 | I1/I2「还原后回绿」rc=0；`check-linux-k0` rc=0 |
| F9 证据脚本 `check ... "$?" "$?"` 两支读同一 `$?`（恒真） | ✅已修 | 显式 `RC=$?` + `eq/is_zero/is_nonzero` 助手；计数解析改 `n/m PASS` 现场取 | 脚本内在 red/green 两态分别落在 FAIL/PASS |
| F10 probe 遇缺失字段 `int('<missing>')` 崩栈，掩盖其余断言 | ✅已修 | `num()` 对非数字返回 -1，缺失字段单独计 FAIL | 注入态 probe 输出 0/52、2/52 而非 traceback |

### 第 1 轮 reviewer 验收（独立重跑，不采信完成区）

**重跑记录**（reviewer 自己执行）
- 证据脚本 `run.sh` 重跑：`== summary: PASS=28 FAIL=0 ==`、退出码 0；13 条 `[RUN]` 中 `build/probe/neg×2/I1-build|rebuild|green/I2-build|rebuild|green/k0` 全 rc=0，`I1-probe`/`I2-probe` 期望非零、实测 rc=1。日志里 3 行 `[FAIL]` 是被 `tail` 打出的**注入态 probe 输出**，非脚本断言失败。
- 正向 guest 输出逐行在案：`K1 bootinfo magic=0x4442494e version=0x1 size=0x60 hart=0` + kernel/ram 行 + initramfs/cmdline/ptbr/flags 行 + `K1 stack sp=0x20000564050 early_stack=0x20000560060..0x20000564060` + `start_kernel` + `K1 start_kernel ra=0x20000110364 … off=0x1c inside=yes` + `K1 done: …SYS_EXIT(0)…`；probe `30/30 PASS`。
- 负例 reviewer 自跑 `--neg magic`：`K1 bootinfo invalid: magic code=0xe1`、rc=225、无 boot info 行、无 `start_kernel` 行；`--neg size` rc=227（脚本内实测）。committed `hmon.S` md5 前后不变。
- `kernel_size` 由 reviewer 从 ELF 独立重算 `max(p_vaddr+p_memsz)−kernel_base = 0x4bb5f9`，与 guest 打印一致；`llvm-nm` 独立核 `start_kernel=0x20000110348`、`early_stack_top−early_stack = 16384`（= head.S `.zero`）、SP 与 ra 均落区间内。
- `llvm-objdump` 核「首句」：`start_kernel` 的**首个 `call`** 目标即 `dadao_k1_early_stop`（0x200001127ac），其返回地址 0x20000110364 = guest 打印的 `ra`、off=0x1c；该函数 `__noreturn` 且末句 `dadao_early_exit(0)` ⇒ `start_kernel` 后续序列（`time_init`/`arch_call_rest_init` 及以后）一律不执行。

**栈 / `br.eq`**：`_start` 首条指令即 `set.rb rb1, early_stack_top`，其前无任何压栈；SP 落 `.zero 16384` 区间内。`contracts/opcodes.yaml::br.eq_rrii_rd` 两源操作数 `bank: rd`（`rdha[23:18]`/`rdhb[17:12]`）⇒ K0 `br.eq {rb2,rb3}` 被编进 rd 字段、比的是未初始化的 rd2/rd3，**真 bug**；修法（镜像 rd2/rd3 并同步递增）正确。

**semihosting 指针口径（reviewer 独立判）**：① `contract-semihosting §1–§5` 与 `spec/Kaiwu §5.1–§5.6` **只写「参数块指针→rb16」，全无 PA/VA 表述** ⇒ spec 未明。② QEMU 两路确实不一致：`SYS_WRITEC`→`console_write`→`lock_user`→`cpu_memory_rw_debug`→`dadao_cpu_translate_for_debug`（**identity**，仅收 `[0,2GiB)`∪ROM∪SRAM）；`SYS_WRITE0` 先 `target_strlen`→`probe_access_flags`（**走页表**）再拷贝；`SYS_EXIT` 的 `GET_ARG` 同走 identity。Vast 页表只映 `VA [0x0200_0000_0000,0x0200_2000_0000)`，与 identity 窗口**不相交** ⇒「无地址能同时满足两条路」成立；`dadao_cpu_translate_for_debug` 注释仍称「DADAO has no MMU」，在 Vast+PTW 下已过时。③ **判定 = spec 未明 + QEMU 两路不一致叠加**；传 PA 且只用单路 `SYS_WRITEC` 自洽，与 `tests/shared/bootrom/k0/probe_kernel.S` 口径逐字一致。⚠️ `contract-linux-boot §7`「ABI 地址一律 VA」与之**有张力**，engineer 已列「待裁定 1」、未自行终局化 ⇒ **不阻断 K1，须 architect/用户裁定**（补契约口径 或 修 QEMU 统一翻译路径）。

**门控（reviewer 跑）**：`check-linux-k0` **119/119 rc=0**；`check-index-blobs` rc=0；`check-component-changelog` rc=0；`check-source-state` rc=0（`linux: OK count=1 clean=True expected=1`）；`check-patch-tree` rc=1，**10 problems 现场 grep 全部 `chipyard:`**、linux 段仅 `57 patch(es)` 计数行、0 problem（并行任务所致；本任务 14 文件无越界）。

**独立注入 1 路（reviewer 自设计，非 engineer 的 I1/I2）**：head.S `br.ne {rd4,rd5}?`→`br.ne {rd4,rd4}?`（绕过 magic 校验），md5 `80b4dff4…`→`b40b79d0…`；重建 rc=0 ⇒ `--neg magic` **rc=1、4/5 FAIL**（退出码期望 225 实际 0、出现 `magic=0x4442494f` 的 boot info 行、出现 `start_kernel` 行）；`cp`+`touch` 还原后 md5 相等、源树 status 空，重建 rc=0 ⇒ **回绿 5/5 rc=0**、正向 30/30 rc=0。

**约束核验**：越界 0（14 文件全在 `components/linux/**`、`tools/linux/**`、`tools/qemu/k0_boot_probe.py`、本任务书；未碰台账/`discussing.md`）；完成区 19 行 ≤30；未跑 `install-host`/`check-modules`；`JOBS=32` 且构建与测试串行未并行。快照对账：worktree `git status -uall` 前/后均空，6 交付物 + 4 源文件 md5 前后逐一相等，源树 `count=1 clean=True`。

**判决：Accepted**（1 条非阻断 finding：semihosting 指针 PA/VA 口径待裁定，见「待裁定 1」）。

## 完成区

**测试结果**：一键证据脚本（本任务证据目录 `run.sh`）⇒ **28/28 PASS、rc=0**：构建 1 + 正向 P1–P7（30/30）+ 负例 size/magic（各 5/5）+ 注入 I1/I2（各自 注入→红→`cp`+md5 还原→重构建→回绿）+ `check-linux-k0` + 源树状态。
**修改文件**：`components/linux/{series,README.md,changelog.md}`、`components/linux/patches/arch/dadao/**`（7 份修改）+ 新增 `components/linux/patches/init/main.c.patch`（共 57 份）、`tools/qemu/k0_boot_probe.py`（`build_firmware` 加 K1 变体参数）、新增 `tools/linux/k1_boot_probe.py`、本任务书。
**验收结果**（`qemu-system kaiwu-vast`，`bootrom-image + -kernel`，guest rc=0）：
- `K1 bootinfo magic=0x4442494e version=0x1 size=0x60 hart=0`；`kernel_base=0x20000100000 kernel_size=0x4bb5f9 ram_base=0x20000000000 ram_size=0x80000000`；`initramfs=0x20004000000+0x0 cmdline=0x0+0x0 ptbr=0x0 page_size_log2=0x10 flags=0x1`（与契约/ELF 现场派生一致）。
- `K1 stack sp=0x20000564050 early_stack=0x20000560060..0x20000564060 entry_va=0x20000100000`（16 KiB = head.S `.zero`，SP 在区间内）。
- `start_kernel` + `K1 start_kernel ra=0x20000110364 base=0x20000110348 off=0x1c inside=yes`（`ra` ∈ `[start_kernel, 下一符号)`）；`K1 done: semihosting SYS_EXIT(0) before any clock/interrupt init`。
- 负例（固件侧只改坏字段、内核不变）：magic ⇒ `K1 bootinfo invalid: magic code=0xe1`、rc=225；size ⇒ `… size code=0xe3`、rc=227；两者均无 boot info 行、无 `start_kernel`。
- 注入：I1 改坏 head.S 的 magic 常量 ⇒ probe 红（guest 报 magic 拒绝）、`cp`+md5 还原 + 重构建后回绿；I2 让 console 传 VA ⇒ 无输出、probe 红，还原后回绿。
- 修补丁：`make_patch.py linux` 重导出 57 份；`check-patch-tree` **linux 段 0 问题**（总 rc=1 的 10 项全在 chipyard，并行任务）；`--source-state` 全组件 OK（linux `count=1 clean=True`）；`check-index-blobs` rc=0；`check-component-changelog` rc=0；`check-linux-k0` rc=0（119/119）。
**新发现/坑**：
- semihosting 的 uaccess 在 QEMU 里有两条不一致的路（`probe_access` 看页表 / `cpu_memory_rw_debug` 走 identity）⇒ Vast+PTW 下 `SYS_WRITE0` 不可用；`SYS_WRITEC`/`SYS_EXIT` 走 identity ⇒ 指针必须传 **PA** 且截 48 位（见「待裁定」1）。
- 同 TU 的 `__weak` 空函数会被编译期内联，arch 的强定义调不到 ⇒「start_kernel 首句」只能靠 `init/main.c` 的 Kconfig 钩子（见「待裁定」2）。
- `__builtin_return_address()` 在 DADAO 后端未实现（折叠为 0），返回地址只能读 RAS（`ra2rd {rd},{ra63}`）。
- `cp -p` 还原保留旧 mtime 会让 Kbuild 跳过重编（K0 reviewer 已踩过一次）：还原必须 `cp`+`touch`，否则「还原后回绿」是假绿。
- semihosting `SYS_EXIT` 子码即宿主退出码（`&0xFF`）⇒ 失败码不能 ≥0x100。
**遗留问题**：
- K1 边界钩子属通用文件改动，K2 首件须把 `CONFIG_DADAO_K1_EARLY_STOP` 关掉并接 `setup_arch()` 起的正常初始化（`dadao_early_printf` 届时可换 `SYS_WRITE`/printk）。
- `dadao_console_write` 现在逐字节 `SYS_WRITEC`（K1 不走到 console_init）；K2 起若需 printk 吞吐，应改 `SYS_OPEN(":tt") + SYS_WRITE`。
- 未跑 L1 `make check` 全量：`check-patch-tree` 的 10 项红全在 chipyard（并行任务在途），linux 段为 0 问题。
