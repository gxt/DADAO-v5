# 测试运行产物与日志组织规范

> **状态**：生效（2026-10-19）｜**上位依据**：无——属**工程过程规范**（可逆、单项目、无外部契约，不命中 ADR 判据，见 `docs/Process-03`）。
> **缘起**：用户 2026-10-19 当场质问「`.work/log` 乱成这样，还有文件是公用的」，见 `ISS-278`。
> **关键词**：**必须**（MUST）／**应当**（SHOULD）／**可以**（MAY）。
> **分工**：门控的**层归属**见 `docs/Process-07` §1.1；本规范只定**产物与日志的组织规矩**。`check-run-artifacts` 的实现真源 = `tools/infra/check_run_artifacts.py`。

---

## 1. 规矩（7 条，MUST）

### 1.1 每次测试跑 = 一个独立目录

每次驱动调用**必须**新建独立运行目录：

```
<--work-dir>/<YYYYMMDDTHHMMSSZ>-<套件>-<档>/
    run.json   逐例结果记录（与 --json-out 同一对象）
    run.log    人读日志（与 --report-out 同一文本）
    meta.json  命令行 / UTC 起止时间 / 工具链摘要
```

- 目录名时间戳 = **UTC**，格式 `YYYYMMDDTHHMMSSZ`；档 = `static` / `dynamic` / `both` 轮次中的单档。
- `meta.json` **必须**含：`command`（非空）、`started_utc`、`finished_utc`、`toolchain`；`toolchain` 的 `clang` / `qemu` / `libc` **必须**各带**非空** `sha256`（或 `md5`），`lld` 与 `libc.a` / `libc.so` 两味一并记录。
- **禁止**两次跑写同一目录。同秒碰撞由驱动等待到下一秒，**不得**复用目录或改目录名形状。
- 默认 `--work-dir` = `manifests/install-dirs.lock.toml` 的 `test_artifacts_dir`（当前 `.dadao/tests`）下的套件子目录；`--json-out` 相对路径按**调用者 CWD** 解析。

### 1.2 权威跑

权威跑**只**写：

```
.work/tests/authoritative/<YYYYMMDDTHHMMSSZ>-<套件>-<档>/
```

- 各次权威跑**并列、永不覆盖**；`authoritative/latest` 指向最新权威跑目录（符号链接或内容为目录路径的文本文件）。
- **子集跑**（`--filter` / `--only` / `--limit`）**不得**写 `authoritative/`。
- 当前三个驱动默认把运行目录建在 `--work-dir` 下；把 `--work-dir` 指向 `authoritative/` 即构成权威跑，由调用者负责选择。

### 1.3 驱动约束

三个 user-mode 驱动（`run_libc_test_user_suite.py` / `run_llvm_ts_user.py` / `run_embench_user_suite.py`）：

- `--json-out` **必填**；未给 ⇒ argparse **报错、非 0 退出**。**不得**存在 `DEFAULT_LOG_DIR` 一类的固定默认回落。
- `--report-out` 缺省 = 与 `--json-out` **同目录、同名换 `.log`**；不得回落到固定目录。
- `llvm-ts-user` 的 `--link-mode both` 只在调用者给定的 `--json-out` 词干后**追加一次**档后缀（`-static` / `-dynamic`），不得叠加两次。
- 驱动**必须**按第 1 条建运行目录（三件套）；即使调用者给了 `--json-out` 也不例外。

### 1.4 门控 / 手工日志命名

`.work/log/<模块>/<任务号>-<用途>.log`

- `<任务号>` = `INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG` + `-` + 三位数字 + 可选小写后缀（如 `INFRA-093t`）。
- **禁止**无任务前缀的文件名。
- 门控自身日志统一 `check-<name>.log`（连字符），**禁** `check_<name>.log`。
- 后缀允许 `.log` / `.json` / `.txt`。

### 1.5 归档

历史文件按**任务前缀**移入 `.work/tests/archive/<任务号>/`；**只移不删**，删不删由用户定。本规范只定规矩，**不执行搬迁**。

### 1.6 搬迁边界（本册不搬）

搬迁**拆两步**：

1. 本册（`INFRA-093t`）只落**驱动 / 门控 / 文档**；
2. `.work/log/testcases/` 的实际搬迁**另起一笔**，且**必须等当前动态跑结束**。

本册**不得**移动 / 删除 / 改写 `.work/log/**` 任何存量文件。

### 1.7 门控 `check-run-artifacts`（L1）

断言 A1–A3（见 §2），并入 `make check`；`--self-test` 内置每条断言的可达 FAIL；真实注入一次「FAIL → `cp` 备份 + md5 还原 → 回绿」。

---

## 2. 门控口径（`tools/infra/check_run_artifacts.py`）

### A1 驱动无固定默认输出（源码级）

- 三个驱动的 `--json-out` **必须** `required=True`；
- 源码**不得**再出现 `DEFAULT_LOG_DIR`（固定回落已删除）；
- `--report-out` 缺省**必须**由 `--json-out` 派生（`os.path.splitext(json_out)[0] + ".log"`）；
- 驱动**必须**调用运行目录助手 `run_artifacts.create_run_dir`。

反例注入：把 `required=True` 改回 `default=None`，或重新引入 `DEFAULT_LOG_DIR` ⇒ **FAIL**。

### A2 运行目录三件套

- 扫描面：`.work/tests/**`（若存在）＋ 配置的 test-artifacts 根（当前 `.dadao/tests/**`）；两者都不存在 ⇒ **SKIP**（明文打印，不 vacuous PASS）。
- 每个匹配 `^\d{8}T\d{6}Z-` 的目录**必须**同时有非空 `run.json` / `run.log` / `meta.json`；
- `meta.json` 的 `command` 非空、`started_utc` 存在、`toolchain.clang` / `.qemu` / `.libc` 各带非空 `sha256` 或 `md5`；
- `authoritative/` 存在时，`authoritative/latest` **必须**存在且指向存在的目录。

### A3 `.work/log/**` 新增文件命名

- **存量豁免**：落地时在 `.work/log/` 写 `.run-artifacts-epoch`（内容 = 创建时刻 UTC）。`mtime <= epoch` 的文件豁免；落地时另写 `.run-artifacts-baseline`（当时全部相对路径的快照），快照内路径一律豁免（防止**正在被改写**的旧文件因 mtime 变新而误判）。标记不存在 ⇒ **SKIP**。
- 新增文件**必须**是 `check-<name>.log` 或 `<任务号>-<用途>.(log|json|txt)`；其余 ⇒ **FAIL**。
- 过渡豁免：本册落地时仍在写的 `llvm-ts-user-*` 旧固定名（当前动态跑）不判红；搬迁任务完成后删除该豁免。
- 不得把豁免写成「只查某个目录」。

### 退出码

`0` = PASS（或明文 SKIP）/ `1` = FAIL；`--root DIR` 供 self-test 临时树使用；不依赖网络、不跑被测语义。

---

## 3. 迁移说明（向后兼容）

`--json-out` 由「可选」改为「必填」是**有意的破坏性收紧**。现有调用点若省略该参数，升级后立即 `rc=2` 并打印 `the following arguments are required: --json-out`。迁移方式：

```bash
# 旧
python3 tools/testcases/run_libc_test_user_suite.py --link-mode static
# 新（--report-out 可省，自动同目录同名 .log）
python3 tools/testcases/run_libc_test_user_suite.py --link-mode static \
    --json-out .work/tests/<UTC>-libc-test-static/results.json
```

- 已带 `--json-out` 的调用（`/dispatch` 证据脚本多数如此）**行为不变**，只是额外多写一个运行目录三件套。
- 省略 `--report-out` 时不再写 `.work/log/testcases/`，改写到 `--json-out` 同目录。
- `--json-out` 为相对路径时按**调用者 CWD** 解析（与 Python `open` 一致）。
- 存量证据脚本（`.work/evidence/**`）不在本册修改范围；重跑前按上述方式补参数。
