# `tests/tset/libc-test/` — libc-test（外部套件，user 成品系统）

上游语料 **不入库**：由 `manifests/components.lock.toml` 锁定，`make fetch` 后位于
`.work/source/libc-test/`（`src/*/*.c`，上游 Makefile 的语料视图）。上游基线
（`b7ec4679…`，`shallow = false`，完整裸镜像 `.cache/libc-test.git`）由 `make fetch` +
`make apply-series` 建工作树。

musl/Linux 用户态一致性测试语料（`TESTCASES-044t`，`ADR-0025 D6`）：判定 musl 移植
（`P1` 静态 / `P2` 动态）是否成立的**独立**输入，不参与实现。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见
  `series`；规范见 `docs/Process-01-组件补丁组织与构建编排.md`。
- 现行补丁 **1** 个：`src/regression/malloc-brk-fail.c`（`TESTCASES-100t`）。
  - 原因：64 KiB 页下，musl dynamic loader 把可写 `PT_LOAD` 段两端按页对齐的空洞
    「捐赠」给 mallocng（`ldso/dynlink.c` 的 `reclaim_gaps`）。测试原先假设「填满
    VA + `RLIMIT_DATA=0` 后 `malloc(10000)` 必失败」；在 64 KiB 页上该请求直接落在
    捐赠空洞里、无 `brk`/`mmap` 系统调用，于是假绿。补丁在 `t_vmfill` 之前申请并
    保留 6 个 32736 B（size class 39）块，先消耗这些捐赠组；断言、magic、退出码、
    `t_vmfill`/`t_setrlim` 逻辑均不改；4 KiB 页布局下按同一 size-class 表推导不退化
    （本机 QEMU 只有 64 KiB 页，无法现场跑 4 KiB，理由见 `TESTCASES-100t` 完成区）。
- 补丁只做**测试输入侧的可移植性修正**，不放宽判据：static 档仍覆盖原行为，
  dynamic 档仍执行同一用例。
- 补丁集由 `INFRA-125t` 归位到本目录（上游 commit 不变）。
- 校验：`make check-patch-tree check-source-state`（补丁集 / 源树自检）、
  `make check-component-changelog`。

## 入口

| 用途 | 命令 |
|---|---|
| L2 代表集 | `make check-tset-libc-smoke` |
| 套件全量（按需） | `python3 tools/testcases/tset/libc-test/run_libc_test_user_suite.py --link-mode static --json-out /tmp/.../libc.json` |
| 代表集规则（不跑 guest） | `python3 tools/testcases/tset/libc-test/run_smoke.py --list` |

- 驱动实现：`tools/testcases/tset/libc-test/run_libc_test_user_suite.py`
  （`TESTCASES-075t` 从 `tools/testcases/` 迁入；旧路径 = 薄 wrapper，命令行等价）。
- 运行目录 / 三件套：`<test-artifacts>/libc-test-user/<UTC>-libc-test-user-<档>/`
  （`docs/Process-08`；目录名**未改**）。

## 代表集（L2）

`run_smoke.py` 用驱动自身的 `discover()` 现场枚举，**类别 = 语料顶层目录**
（`api` / `functional` / `math` / `musl` / `regression`，由上游目录结构决定），
每类取**源码字节数最小**的用例（ties 按 case id）。计数与选中项每次现场打印，
不写死；结构断言 = 类别全覆盖 / 无重复 / 驱动 census 自洽。

## 口径

- 期望值来自语料自身（每个 case 返回自己的 `t_status`，通过即 exit 0）；
  分类器（`pass` / `fail` / `known-fail` / `blocked`）在驱动内，**未改**。
- 子集跑（`--filter`）不写 `authoritative/`（`docs/Process-08 §1.2`）。
