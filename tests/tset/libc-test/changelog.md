# libc-test 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文>`。节 = `## M<k>`（节序 M1→M2→…），**节内按日期升序**；规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M11

- **2026-11-05 `TESTCASES-100t`**
  - 摘要：**`malloc-brk-fail` 64 KiB 页可移植性修正（C 方案：改语料，不 known-fail/不排除）**。组件由 `patchless = true` 转为受补丁组件（`patch_dir = "components/libc-test/patches"`、`patch_series = "components/libc-test/series"`，锁 commit `b7ec4679…` 不变）；新增一文件一补丁 `src/regression/malloc-brk-fail.c`。根因（`TESTCASES-099t`）：64 KiB 页下 musl dynamic loader `reclaim_gaps` 把可写 `PT_LOAD` 段两端空洞捐给 mallocng，`malloc(10000)` 落在捐赠的 class-39 单槽组内、无 `brk`/`mmap`，测试「填满 VA + `RLIMIT_DATA=0`」假设不成立。补丁在 `t_vmfill` 之前申请并保留 6 个 32736 B（class 39、16 B 对齐）块，消耗捐赠组及随后的 class-40 组；static（lite_malloc）线下 6 块合计 196416 B，仅余 192 B brk，同一首个 `malloc(10000)` 仍须增长 `brk`/`mmap` 并失败。断言、magic、退出码、`t_vmfill`/`t_setrlim` 逻辑不改，不跳过、不降低覆盖。
  - 执行者：engineer

- **2026-11-06 `TESTCASES-101t`**
  - 摘要：**`malloc-brk-fail` 改用 `{cur=0, max=infinity}`**。guest `RLIMIT_*` 真正生效后，该用例的 `t_setrlim(RLIMIT_DATA, 0)` 会把 `rlim_cur` 与 `rlim_max` 同时降到 0；内核 `may_expand_vm()` 的 Valgrind workaround（`rlimit(RLIMIT_DATA)==0` 且请求量 ≤ `rlimit_max`）因此失效，`munmap` 64 KiB 后的 `mmap` 仍 `ENOMEM`，static/dynamic 两档皆红。补丁改为 `getrlimit` + 只设 `rlim_cur = 0` + `setrlimit`、保留 `rlim_max`，意图不变（VA 满时 `malloc(10000)` 必须 `ENOMEM`、腾出 64 KiB 后成功）；`TESTCASES-100t` 的 6×32736 prime 与全部断言、退出码不变；锁 commit 不变。
  - 执行者：engineer
