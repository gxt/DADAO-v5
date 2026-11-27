# LTP 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号>**`，**摘要另起缩进行** `  - 摘要：<正文>`。节 = `## M<k>`（节序 M1→M2→…，**节内按日期升序**）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M18

- **2026-11-23 `m18-linux-006`**
  - 摘要：**建 LTP 组件（Linux Test Project 20260930，浅克隆锁 commit）**。锁条目 `name = "ltp"`：`repository = https://github.com/linux-test-project/ltp.git`、`shallow_ref = "20260930"`、commit `2279d708…`（annotated tag object `a6bade7f…` 的 peel commit，tag object 不入锁）、`patch_dir`/`patch_series` 指向本目录。构建入口 `tools/linux/suite/build_ltp.py`（树外构建 + 入库 `config.h` + 每宏编译探针）；用例清单与分诊在 `tests/unit/linux/suite/ltp/`。
  - 执行者：engineer
- **2026-11-25 `m18-linux-006`**
  - 摘要：**返工：补首个适配补丁 `lib/safe_macros.c.patch`（TEST_ADAPT）**。`safe_waitpid()` 对 `EINTR` 重试——本移植把 `-ERESTARTSYS` 变成用户可见 `EINTR`（无系统调用重启，`arch/dadao/kernel/signal.c`），LTP 的 SIGUSR1 心跳会打断父进程的 `waitpid`，使每个 `tst_test` 用例在第一条断言前 `TBROK`。补丁后 `open01`/`read01`/`lseek01`/`fstat02`/`wait01` 等给出真实判定。补丁集由空首态转为 1 条（`.gitkeep` 随之删除）。同时按返工口径订正台账：`sigaction01`/`open01` 记 PASS（信号帧 ABI 落地）、`mlockall02` 记 TBROK、`mmap01` 记 HOST_TIMEOUT（64 KiB 短文件 `msync(MS_SYNC)` 停摆，KERNEL_BUG）。
  - 执行者：engineer
