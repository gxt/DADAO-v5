# `tests/tset/llvm-ts/` — llvm-test-suite（外部套件，user 成品系统）

上游语料 **不入库**：由 `manifests/components.lock.toml` 锁定，`make fetch` 后位于
`.work/source/llvm-test-suite/`。

## 入口

| 用途 | 命令 |
|---|---|
| L2 代表集 | `make check-tset-llvm-smoke` |
| 套件全量（按需/夜跑） | `python3 tools/testcases/tset/llvm-ts/run_llvm_ts_user.py --link-mode static --jobs 4 --json-out /tmp/.../llvm.json` |
| 代表集规则（不跑 guest） | `python3 tools/testcases/tset/llvm-ts/run_smoke.py --list` |

- 驱动实现：`tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`
  （`TESTCASES-075t` 从 `tools/testcases/` 迁入；旧路径 = 薄 wrapper，命令行等价）。
- 运行目录 / 三件套：`<test-artifacts>/llvm-ts-user/<UTC>-llvm-ts-user-<档>/`
  （`docs/Process-08`；目录名**未改**）。

## 代表集（L2）

`run_smoke.py` 用驱动自身的 `discover()` 现场枚举，**类别 = 上游三棵树**
（`MultiSource/Applications`、`MultiSource/Benchmarks`、
`SingleSource/Benchmarks`），每棵取**源码字节数最小**的用例（ties 按 case id）。
套件含 mafft/nbench 等分钟级基准，整树不能进 L2；该规则既保证每棵树有代表，
又把耗时压在受控范围。计数与选中项每次现场打印，不写死；结构断言 = 树全覆盖 /
无重复 / 驱动 census 自洽。

## 口径

- 期望值来自上游 `*.reference_output*`（byte-exact / md5）或 exit 0，驱动内
  分类器（`pass` / `fail` / `known-fail` / `blocked`）**未改**。
- 子集跑（`--only` / `--limit`）不写 `authoritative/`（`docs/Process-08 §1.2`）。
