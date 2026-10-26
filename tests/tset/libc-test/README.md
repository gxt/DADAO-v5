# `tests/tset/libc-test/` — libc-test（外部套件，user 成品系统）

上游语料 **不入库**：由 `manifests/components.lock.toml` 锁定，`make fetch` 后位于
`.work/source/libc-test/`（`src/*/*.c`，上游 Makefile 的语料视图）。

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
