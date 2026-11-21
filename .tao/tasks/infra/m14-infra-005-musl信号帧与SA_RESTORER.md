# m14-infra-005: musl 信号帧与 `SA_RESTORER`（2048 B 四组布局）

**模块**：infra
**项目里程碑**：M14
**依赖**：`m14-linux-046`（信号帧 uapi 定稿并合入）
**可并行分片**：否（改 musl 组件补丁）
**预估**：3–4 h
**档位**：大改（ABI 布局 + arch 汇编）
**状态**：待验收

## 背景

musl 的 DADAO `arch/dadao/bits/signal.h` 现在是**明确标注的临时占位**：

```
[OPEN] mcontext_t / gregset_t / struct sigcontext below are a PROVISIONAL,
COMPILE-ONLY definition ... NO field offset or array size below is load-bearing
```

`m14-linux-046` 已按用户 2026-11-20 裁定定下真实帧：**2048 B，四组各 64 槽**（`rd[0]`=`status`、`rb[0]`=`ip`、`ra[64]`、`rf[64]`），且 kernel uapi 的 `struct ucontext` 已按 musl 现有成员次序写（`uc_flags, uc_link, uc_stack, uc_sigmask, uc_mcontext`，**mcontext 在最后，偏移 168**），kernel 侧 `sigset_t` 用 `__unused[120]` 把掩码区凑到 128 B。

## 目标

1. **`mcontext_t` / `gregset_t` / `sigcontext` 改成真实布局**：四组各 64 个 `unsigned long`；`sigcontext` ≡ kernel 的 `struct user_regs_struct`（2048 B）；`rd[0]` 作 `status`、`rb[0]` 作 `ip`（匿名 union 或宏别名均可）；
2. **`MC_PC` 指到 `ip` 槽**（偏移 512）：`arch/dadao/pthread_arch.h` 里的 `MC_PC` 定义随之改；
3. **`MINSIGSTKSZ`**：≥ 2376（2048 帧 + 余量），`SIGSTKSZ` 相应；
4. **`SA_RESTORER` + `__restore_rt`**：值 `0x04000000`；arch 汇编（`SYS_rt_sigreturn` + `trap`）；`sigaction` 在无 vDSO 时自动填 `sa_restorer`；
5. **不动 `sigset_t` 宽度**（musl 全局 128 B 类型，ABI 既定）。

## 验收（逐条贴真实 rc）

1. **构建**：`make build-musl` 与 `make build-musl-shared` rc=0；`check-musl-freshness` rc=0；
2. **端到端（关键）**：在 K5 内核上跑一个装 `SIGUSR1` handler 的程序：投递 → handler 执行 → `rt_sigreturn` 返回 → 主流程继续；打印四组寄存器的哨兵值与 `ip` 返回点；
3. **`sigaltstack`**：备栈生效（`SA_ONSTACK`），越界拒绝行为与内核一致；
4. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 帧尺寸/偏移写错（如 rd 组少一槽）⇒ 程序 SIGSEGV；② `sa_restorer` 不填 ⇒ handler 返回跳到空地址；
5. `check-patch-tree` musl 段 0 问题；`check-index-blobs` rc=0。

## 约束

独立 `git worktree`；不提交 git；不改内核（帧定义以 `046` 的 uapi 为准）；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：K5 端到端探针 36/36 PASS（四组哨兵 `rd32`/`rb32`/`rf32`=0x1234/0x5678/0x9abc、`status`=1、`ra0`=0x0004_0000_0000_0000、`handler.ip` == raise trap 后 4 B 的标签、`rt_sigreturn` 后主流程继续）；plain handler 走 `__restore`；`SA_ONSTACK` 帧落备栈且 handler SP 在栈内；内核 `sigaltstack` 下限 1024/2375 拒（ENOMEM）、2376/8192 收；`make build-musl`、`build-musl-shared`、`check-musl-freshness`、`check-patch-tree`（452 patch / musl 26）、`check-component-changelog`、`check-index-blobs` 全 rc=0。证据脚本 24 项检查全 rc=0（含 3 路注入 → 红 → `cp`+md5 还原 → 重建 → 回绿）。
**修改文件**：`components/musl/patches/arch/dadao/bits/signal.h.patch`、`patches/arch/dadao/pthread_arch.h.patch`、`patches/src/thread/dadao/syscall_cp.s.patch`（注释）、新增 `patches/src/signal/dadao/restore.s.patch`、`components/musl/{series,changelog.md,README.md}`；新增 `tools/infra/musl_sigframe_probe.py`、`tools/infra/musl_sigframe_probe_user.c`（越界披露：任务书未列文件，属用户授权范围内的「必要 tools」）。
**验收结果**：真帧 = 内核 uapi：`mcontext_t` 2048 B（`rd`/`rb`/`ra`/`rf` 偏移 0/512/1024/1536，匿名 union 暴露 `status`/`ip`），`struct sigcontext` = 同形 + uapi 的 4 个保留字（2080 B），`uc_mcontext` 168、`uc_sigmask` 128 B 未动；`MINSIGSTKSZ` 2376（= 128 + 2248 的内核 `rt_sigframe`）、`SIGSTKSZ` 8192；`SA_RESTORER` 0x04000000；`src/signal/dadao/restore.s` 的 `__restore`/`__restore_rt` 同址（`set.zw rd15, 139` + `trap cfx_umon, 0`，反汇编已核对），`sigaction()` 经上游 `#ifdef SA_RESTORER` 自动填 `sa_restorer`；`MC_PC` = `rb[0]`。可达 FAIL：①rd 组 63 槽 ⇒ 帧镜像全错（`handler.rb32=0`、`ip` 不再等于恢复标签）；②`sa_restorer` 不填 ⇒ 内核 `-EFAULT`→`force_sigsegv`，init 死于 SIGSEGV（`exitcode=0x0b`）；③`MINSIGSTKSZ` 512 ⇒ 下限断言红。
**新发现/坑**：①K5 上 `sigaltstack` 的运行时下限实测 **2376**（2375 拒 / 2376 收），而内核源码传的是 asm-generic `MINSIGSTKSZ`=2048 —— 现象可复现、与 `ss_sp` 无关，建议内核侧确认（`do_sigaltstack` 的 `min_ss_size` 参数）；②`get_sigframe()` 只在「中断时 SP 已在备栈」才查帧是否放得下，所以 `MINSIGSTKSZ` 必须覆盖真帧；③`__builtin_frame_address(0)` 在本 ABI 返回 0，读 SP 要 `rb2rd {rd9}, {rb1}`；④inline asm 写 callee-saved 哨兵必须声明 clobber（否则调用方依赖的 `rb32` 等被改，曾把备栈地址读成 0x5678）；⑤K5 无「普通镜像直接跑 `/init`」路径（`dadao_k4_boundary` 无自检即退出），musl 程序靠 K5 syscall 自检的 U7 `kernel_execve("/init.musl")` 进入用户态；⑥ip=0 的用户故障在 K5 直接终止整机（`die-no-vma`，SIGSEGV 投递属未合入的 `m14-linux-027`），故「写 MC_PC=0 ⇒ 进程 SIGSEGV」无法在本机断言。
**遗留问题**：无代码遗留；`check-temp-dirs` 红（5 项均为**其它**任务的陈旧 `/tmp/opencode/*`，与本任务无关，已保留现场）。

## 审阅记录

### 第 1 轮 engineer 自审（逐行、自主）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 哨兵 asm 写 `rd32/rb32/rf32` 未声明 clobber ⇒ 调用方寄存器变量被改（备栈地址读成 0x5678） | ✅已修 | clobber 列表加 `rd32`/`rb32`/`rf32` | 修后 `altstack.base` = 0x36b30、`insideness`=1 |
| F2 `__builtin_frame_address(0)` 在本 ABI 为 0 ⇒ handler SP 检查恒真/无意义 | ✅已修 | 新增 `read_sp()`（`rb2rd {rd9}, {rb1}`） | `altstack.sp` 落在 `[base,end)` |
| F3 缺键时 `rep.check(x, None, None)` 假绿 | ✅已修 | `num()` 取不到即 None + `*-present` 断言；注入 1/3 的红点即来自缺键 | 注入 1 报 `handler.rb32`/`ip` FAIL；注入 3 报 `minsigstksz` FAIL |
| F4 探针把 cpio 写进共享 initramfs 暂存目录，会覆盖 `make linux-initramfs` 产物 | ✅已修 | cpio 落探针自己的 scratch，`CONFIG_INITRAMFS_SOURCE` 直指该文件 | probe 36/36；`.config` 的 SOURCE 指向 scratch |
| F5 新树上没有 `.config`，`apply_config_lines` rc=2 | ✅已修 | 缺 `.config` 时先跑 `make_defconfig.py` | 干净树首跑 rc=0 |
| F6 头注释写 EINVAL、且称「帧放不下就在投递时拒绝」——与内核实测不符 | ✅已修 | 改为 ENOMEM，并写明 `get_sigframe` 只在已处备栈时查 | 2375 拒/2376 收、1024 拒（errno 12） |
| F7 探针/用户程序注释仍写 `/init` 与「fork 子进程」 | ✅已修 | 改为 `/init.musl` + K5 U7，删掉子进程段 | 头注释与实现一致 |
| F8 证据脚本最后只跑静态档，`clean` 已删 `lib/libc.so` ⇒ freshness rc=2 | ✅已修 | 末尾补 `make build-musl-shared` | 末次 freshness rc=0 |
| F9 脚本写死「26 patches」 | ✅已修 | 由 `series` 现场计数 | 期望=26（现场派生） |
| F10 inject2 断言读错文件且假定 ip=0；实际 restorer=0 时内核直接 `-EFAULT`→`force_sigsegv` | ✅已修 | 断言改为「init 死于 SIGSEGV（exitcode=0x0b）」+「handler 未进入」 | 注入 2 两项均 rc=0 |

**判决**：10 条 finding 全部已修并有复验；无未修项，状态 → `待验收`。

### 第 1 轮 reviewer 验收（独立复核 2026-11-21；以下 rc 均为本人实跑退出码）

1. **布局编译期探针**（`_Static_assert`/`offsetof`，非读注释）musl 侧 **rc=0**：mcontext 2048、rd@0/rb@512/ra@1024/rf@1536、status@0/ip@512、sigcontext 2080（保留字@2048）、`uc_mcontext`@168、`uc_sigmask`@40 且 128 B、`MINSIGSTKSZ` 2376、`SIGSTKSZ` 8192、`SA_RESTORER` 0x04000000、`offsetof(ucontext_t, uc_mcontext.MC_PC)==680`。
2. **内核 uapi 侧探针 rc=0**：`user_regs_struct` 2048（四组同偏移、status@0/ip@512）、`sigcontext` 2080（`__unused`@2048）⇒ 两侧同形。
3. **`llvm-objdump -d`**（运行期 musl 树 `obj/src/signal/dadao/restore.o`）rc=0：`set.zw rd15, wp0, 0x8b`（=139）+ `trap cfx_umon, 0`；`llvm-nm` 于 `lib/libc.a`：`__restore`/`__restore_rt` 同址 `00000000`。
4. **sigaction 走上游路径**：`src/signal/sigaction.c`（`series` 内无该文件补丁）`#ifdef SA_RESTORER → ksa.flags |= SA_RESTORER; ksa.restorer = (SA_SIGINFO) ? __restore_rt : __restore`。
5. **端到端**：`python3 tools/infra/musl_sigframe_probe.py` ⇒ **36/36、rc=0**；抽验：哨兵 rd32/rb32/rf32=4660/22136/39612、`status`=1、ra0 live、`handler.ip==resume-label`=140956（raise trap 后标签）、plain/after-plain `ran`、`SA_ONSTACK` 帧与 handler SP ∈ [base,end)、`sigaltstack` 1024/2375 拒 ENOMEM、2376/8192 收。
6. **门控**：`build-musl` 0、`build-musl-shared` 0、`check-musl-freshness` 0、`check-patch-tree` 0（452 OK / musl 26 现场计数）、`check-component-changelog` 0、`check-index-blobs` 0（首跑与收尾各一次均 0）。
7. **独立注入①**（源树 `signal.h` rb 组前插 8 B ⇒ 512→520，`cp`+md5 备份）：build 0 → 编译期探针 **rc=1（10 断言红**：rb@520、size 2056、MC_PC 688…）→ 端到端 **7 FAIL**（`handler.rb32`、`handler.ip==resume-label`、`ip-off` 等）**rc=1**；还原 md5 `c03bc93b…` 相等 → build 0 → 端到端 36/36 rc=0。
8. **独立注入②**（`MINSIGSTKSZ` 2376→2048）：端到端 **3 FAIL**（`minsigstksz`、`sigaltstack.2375.rc/.errno`）**rc=1**；还原 → 回绿 36/36 rc=0。
9. **证据脚本审核 + 重跑**（运行期证据目录内的 `run.sh --inject`）：3 路注入均按预期 rc=1、md5 还原相等、`restored -> probe green 0`、shared/freshness 0 ⇒ **RESULT: PASS，EVIDENCE_RC=0**；逐条断言有可达 FAIL、无恒真。
10. **越界**：`git status --porcelain -uall` 共 10 行 = 任务书 + `components/musl` 7 + `tools/infra` 2；`grep -E "components/linux|spec/|.tao/contracts"` **rc=1（无越界）**，与完成区「修改文件」逐行一致；tools 两文件判**越界但必要**（端到端必需）。
11. **安装根**：审查中在同一 `.dadao` 安装根多次重建（build-musl/shared），已记录，合入后由主会话从 master 重建。

**第 9 项定性：`sigaltstack` 下限 = 符合预期（libc 侧拦截），非内核 bug**。musl `src/signal/sigaltstack.c` 先 `sysconf(_SC_MINSIGSTKSZ)` 拒 `<min`（ENOMEM），而 `sysconf` = `max(AT_MINSIGSTKSZ, MINSIGSTKSZ−1024)+1024` ⇒ 基线 = 2376；注入②把 `MINSIGSTKSZ` 改 2048 后 **2375 被收** ⇒ 内核下限 ≤2375，基线 2375 之拒必来自 libc。结论：2375 拒 / 2376 收即本次 `MINSIGSTKSZ=2376` 生效，**engineer「建议内核侧确认 `do_sigaltstack` 的 `min_ss_size`」撤销**。
**文档级 finding（不阻断，architect 收尾改）**：F-a 完成区「新发现①」把现象归因内核；F-b `bits/signal.h.patch` 注释「The kernel's sigaltstack() refuses…」与探针头注释「the kernel's bounds rules」应改为 libc 侧拦截措辞。

**判决：Accepted** —— 验收命令全部由本人重跑 rc=0、2 路独立注入红/绿闭环、硬约束逐条守住；仅上述 2 条文档级 finding 待收尾修正。
