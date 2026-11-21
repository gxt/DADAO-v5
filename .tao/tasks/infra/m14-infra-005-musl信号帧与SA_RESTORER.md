# m14-infra-005: musl 信号帧与 `SA_RESTORER`（2048 B 四组布局）

**模块**：infra
**项目里程碑**：M14
**依赖**：`m14-linux-046`（信号帧 uapi 定稿并合入）
**可并行分片**：否（改 musl 组件补丁）
**预估**：3–4 h
**档位**：大改（ABI 布局 + arch 汇编）
**状态**：待开始

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
