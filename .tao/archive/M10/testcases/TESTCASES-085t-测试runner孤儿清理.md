# TESTCASES-085t: 测试 runner 被外部终止时的 qemu 孤儿清理

**模块**：testcases
**项目里程碑**：M10
**依赖**：`TESTCASES-084t`（已验证；测试残留清理后工作树干净）、`TESTCASES-075t`（已验证；tset 三套 runner 归属本模块）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库 `/mnt/tao/DADAO-v5`，分支 `TESTCASES-085t`）。工具链安装根 `.dadao/cross-toolchain/bin/`（`qemu-dadao` 11.1.1、`clang`、`ld.lld`）、suite `.work/source/llvm-test-suite`、musl `.work/source/musl` 均在（预检实测）。

## 用户授权原话（逐字节选）

> 在 /mnt/tao/DADAO-v5，master 已含 INTEG-049t 任务书，工作树干净。创建 `TESTCASES-085t` 任务书：修复测试 runner 被外部终止时 qemu 子进程变孤儿。文件名放 `.tao/tasks/testcases/`；先确认 085 未占用（若占用顺延）。
>
> 5. 检查同类 runner（libc-test/embench 等）是否有相同模式，若同源则提取最小公共清理工具或分别补；不要扩大成测试框架重构。
> 6. 不改 QEMU/spec/测试向量语义；不跑夜跑/长套件；只用小规模受控运行。
>
> 3. 显式 staging，commit `docs: 立 TESTCASES-085t 测试 runner 孤儿清理`；不 push、不实现、不跑夜跑。

## 背景（实测，非推测）

1. **症状**：夜跑 `check-tset-llvm-full` 的 dynamic 段父 runner 被外部 `SIGTERM` 后，留下 3 个 `qemu-dadao` 孤儿（`ppid=1`）：`lua.elf`、`SimpleMOC.elf`、`XSBench.elf`。
2. **本轮 architect 复现**：`python3 tools/testcases/tset/llvm-ts/run_llvm_ts_user.py --link-mode dynamic --only 'MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench' ...` 起 runner（pid `3772330`，`setsid` 后自成一 session），qemu pid `3772407`（`ppid=3772330`、`sid=3772407`）；`kill -TERM 3772330` 后 2 s：runner 消失，`qemu-dadao` **仍活**、`ppid=1`、`sid=3772407`；随后手工 `kill -9` 清理并确认 `pgrep -x qemu-dadao` 为空。
3. **机制**（`tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`）：
   - 三处 `subprocess.Popen(..., start_new_session=True)`：`run_bytes`（约 :947）、`run_stream`（约 :987）、`run_to_file`（约 :2038）⇒ qemu 在**独立 session/进程组**；
   - 超时路径有 `os.killpg(proc.pid, SIGKILL)`（:960 / :995 / :2045），正常结束会回收；
   - **没有** `signal.signal` / `atexit` / 任何清理钩子（`grep -rn 'atexit|signal.signal|SIGTERM|SIGINT|SIGHUP' tools/ --include=*.py` ⇒ 0 命中）⇒ 父 runner 被外部杀死时，独立 session 的 qemu 不会被回收。
4. **同类 runner**：`tools/testcases/tset/libc-test/run_libc_test_user_suite.py::run()`（:578，`subprocess.run` 于 :587）与 `tools/testcases/tset/embench/run_embench_user_suite.py::run()`（:166，`subprocess.run` 于 :169）**未** `start_new_session` ⇒ 子进程与 runner 同进程组：整组被杀（Ctrl-C / `kill -TERM -<pgid>`）时不会泄漏；**只杀 runner 单个 pid 时同样会留孤儿**。同缺陷类、不同机制；无公共实现可复用（三套各自 `run*()`）。

## 问题根源

缺少「**run 期进程登记 + 外部信号清理**」：子进程被刻意放进独立 session（为超时可 `killpg` 整棵 qemu 进程），但进程的 owner（runner）没有任何退出/信号路径去回收这些 session；`SIGTERM` 的默认动作直接终止 runner，Python 的 `finally`/`atexit` 都来不及生效（默认信号动作不抛异常、不跑 `finally`）。夜跑脚本按 pid `kill` runner（而非整组）时即出现 `ppid=1` 的 qemu 长期占用 CPU。

## 目标（范围）

1. **登记**：runner 内所有活动 qemu 的 PID/PGID（含 own-session 与同组两种模式）。
2. **清理钩子**：安装 `SIGTERM`/`SIGINT`/`SIGHUP` 处理 + `atexit` 兜底；收到信号时终止所有**已登记**的活动 qemu（own-session 用 `killpg`，同组用 `kill(pid)`），随后按默认动作重发信号（进程以信号退出，rc=143/130/129）。
3. **不误杀**：只对「本 runner 亲自 spawn 并登记」或「`ppid == 本 runner` 的直系子进程」下手；不按进程名全局 `pkill`；不杀自身/自身进程组；PID 复用用 `/proc/<pid>/stat` 起始时间校验；**不引入外部依赖**（仅标准库），Python ≥3.8 兼容，`/proc` 缺失时退化为仅注册表（不 FAIL）。
4. **可重复自检**：新增 `tools/testcases/check_runner_reap.py`（与 `check_l3_report.py`/`check_night_report.py` 同级），至少四种模式——合成驱动（信号 3 种 + 超时路径）、被改造的两个同类 runner、真 runner + 假 qemu、真 runner + 真 qemu（受控单例）；断言「子进程被回收、诱饵进程存活」。
5. **同类 runner**：抽取最小公共助手 `tools/testcases/proc_reap.py`（与 `run_artifacts.py` 同级的扁平模块，三套 runner 已把 `tools/testcases` 加入 `sys.path`），三套 runner 复用；libc/embench 的 `subprocess.run` 改为等价 `run_tracked`（**保持**返回值元组与 `TimeoutExpired.stdout/stderr` 语义、单 pid kill、不新增 session）。
6. **触达范围**：只改上述助手/三套 runner/自检脚本/Makefile 一行门控/一处门控登记文档/任务书/里程碑行；**不**改 QEMU、spec、测试向量、`contracts/`、`tests/**` 语义；不跑夜跑与 tset full。

## 接口规范

### 1. 最小公共清理助手 `tools/testcases/proc_reap.py`（新增，扁平模块）

只依赖 `os`、`signal`、`atexit`、`subprocess`（+ `threading` 仅当需要）；对外接口：

- `track(proc) -> proc`：登记一条记录 `(pid, pgid, own_group, starttime)`。`pgid = os.getpgid(pid)`；`own_group = (pgid == pid)`（即 `start_new_session=True` 的会话首进程）；`starttime` 取 `/proc/<pid>/stat` 第 22 字段（解析时以**最后一个 `)`** 之后计数），取不到则记 `None`。
- `release(proc) -> None`：从注册表移除（在 `finally` 调用）。
- `kill_tracked(signo=signal.SIGKILL) -> list[int]`：对快照逐条处置，规则见下；返回实际发信号的 pid 列表（用于日志/断言）。
- `install() -> None` / `uninstall() -> None`：幂等安装/卸载 `SIGTERM`、`SIGINT`、`SIGHUP`；`install()` 同时 `atexit.register(kill_tracked)`（重复 `register` 需去重）。
- `popen_tracked(cmd, **kwargs) -> subprocess.Popen`：`Popen` 后立即 `track`；**不**替调用方决定 `start_new_session`。
- `run_tracked(cmd, timeout=None, **kwargs)`：`subprocess.run` 的等价替身——`communicate(timeout=...)`；超时则 kill **该 pid**（与 `subprocess.run` 一致，不 `killpg`）、`communicate()` 收尾后 `raise subprocess.TimeoutExpired(cmd, timeout, output=out, stderr=err)`；`finally: release`。`input=`/`cwd=`/`stdout=`/`stderr=` 透传；`OSError` 照常上抛。

**安全判据（逐条实现，缺一即视为未完成）**：

1. 跳过 `pid == os.getpid()`；own-session 杀组时跳过 `pgid == os.getpgrp()`。
2. 记录过 `starttime` 且当前可读时，两者不等 ⇒ **跳过**（PID 已被复用）。
3. `own_group and pgid == pid` ⇒ `os.killpg(pgid, signo)`；否则 `os.kill(pid, signo)`。
4. 信号处理器：先 `kill_tracked()`，再 `signal.signal(signo, SIG_DFL)` 并 `os.kill(os.getpid(), signo)`（**不得** `sys.exit(128+signo)`，须保留“被信号杀死”语义）；处理器内**不得**获取可能被主线程持有的锁（避免自死锁）。
5. **直系兜底 sweep**：关闭 `Popen`→`track` 之间的窗口——清理时若 `/proc` 可读，额外枚举 `ppid == os.getpid()` 的直系子进程，未登记者也按 3/4 处置；`/proc` 不可读则跳过该步（不报错）。
6. 注册表只由 `track/release` 修改（GIL 下 add/discard 原子），处理器只读快照 `tuple(...)`；不遍历 `ps`/`pgrep` 输出做匹配。

### 2. llvm-ts runner 接线（`tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`）

1. `sys.path` 已含 `tools/testcases`（:359）⇒ `import proc_reap  # noqa: E402`（与既有 `import run_artifacts` 同级、同风格，不新建包）。
2. `run_bytes`/`run_stream`/`run_to_file` 的 `Popen` 改用 `proc_reap.popen_tracked(...)`，**保留** `start_new_session=True`；三处 `finally` 增 `proc_reap.release(proc)`（注意 `run_stream` 的 `proc` 在 `try` 内定义、异常路径可能未定义 ⇒ 先置 `proc = None` 再判空）。
3. `main()` 在**任何 spawn 之前**调用 `proc_reap.install()`（建议紧随 `args = ap.parse_args()` 之后的 `try` 块开头）。不新增 CLI 选项。
4. **不改**：超时 `os.killpg` 语义、返回元组、JSON 字段、case 判定、`--jobs` 线程模型。
5. 正常路径回归：单例 `--only 'SingleSource/Benchmarks/Stanford/Queens'` 仍 `PASS`（预检 23.2 s）。

### 3. 同类 runner 接线（libc-test / embench）

- `run()` 内的 `subprocess.run(...)` 整体替换为 `proc_reap.run_tracked(...)`，参数一一对应（libc 的 `input=stdin_data`、`cwd=cwd`；embench 的 `timeout=`）。
- **不**加 `start_new_session`（保持同组；清理用 `kill(pid)`）；**不改**返回值 `(rc, out, err, timed_out)` 与 `except subprocess.TimeoutExpired` 分支（`run_tracked` 必须填 `output`/`stderr`）。
- 各自 `main()` 在首个 spawn 前 `proc_reap.install()`。
- 其它逻辑（case 枚举、判定、JSON）零改动。

### 4. 自检/测试 `tools/testcases/check_runner_reap.py`（新增）

统一约定：退出码 `0` = PASS / `1` = FAIL / `2` = 用法错误；每例打印 `[PASS]/[FAIL] <name>: <evidence>`（含 pid 与 `ps -o pid,ppid,pgid,sid,stat,cmd` 行）；所有等待有上限（默认 `--timeout-cap 180`，超时判 FAIL）并清理自己起的进程；临时目录 `/tmp/opencode/TESTCASES-085t/`（`--keep` 可保留现场）。

- `--mode helper`（快，无编译，约 2 s；入 L1）：临时生成 `driver.py`（`sys.path` 指向本仓库 `tools/testcases`），内部 `install()` 后分别 spawn：
  (a) own-session 子进程（`start_new_session=True`，`python3 -c "import time;time.sleep(60)"`）；
  (b) 同组子进程（不加 session）；
  (c) 超时路径：`run_tracked([...sleep 30], timeout=1)` ⇒ 断言抛 `TimeoutExpired` 且子进程消失；
  外层再起一个**不属于 driver** 的诱饵进程（`python3 -c sleep 60`，命令行带唯一 marker）。对 `SIGTERM`/`SIGINT`/`SIGHUP` 各跑一轮（3 个独立 driver 实例）：发信号后 5 s 内断言 driver 已退出（`rc == -signo`）、(a)(b) 子进程均 `kill -0` 失败、诱饵仍存活；`pgrep -f <marker>` 为空。
- `--mode converted-runners`（约 3 s）：driver 以 `importlib` 按路径加载 libc/embench runner（两者 import 无副作用，预检已验证），各起一个线程调用其 `run([python3, "-c", sleep 30])`；对 driver 发 `SIGTERM`，断言两个子进程消失、诱饵存活。
- `--mode runner-fake`（约 30 s，真 runner + 假 qemu）：生成 `/tmp/.../qemu-dadao`（shell：`echo $$ > pidfile; sleep 120`），跑真 runner `--link-mode dynamic --only 'SingleSource/Benchmarks/Stanford/Queens' --qemu <fake> --json-out/--work-dir` 指向临时目录；等 pidfile（≤180 s）后对 runner 发 `SIGTERM`；断言 runner 以信号退出（`rc == -15` 或 shell 观测 143）、fake pid 5 s 内消失、`pgrep -f <fake 路径>` 为空。
- `--mode runner-real`（约 60–180 s，真 qemu 受控单例）：跑真 runner `--link-mode dynamic --only 'MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench'`（编译后起 qemu，**不**等它跑完）；等 `pgrep -x qemu-dadao` 出现且 `ppid == runner pid`（≤180 s）；对外层诱饵 `qemu-dadao-decoy` 不计；对 runner 发 `SIGTERM`；10 s 内断言目标 qemu pid 消失、`pgrep -x qemu-dadao` 为空、诱饵存活、runner `rc == -15`。

### 5. 门控接线（`Makefile`）

- 新增目标（L1，体例参照 `check-code-range` 的合成 fixture 自检）：
  ```make
  # check-runner-reap (TESTCASES-085t, L1): runner 被外部信号杀死后不留 qemu/子进程
  # 孤儿。合成驱动 + 伪 qemu，不编译、不跑被测语义；可达 FAIL 见任务证据注入。
  check-runner-reap:
  	@$(PYTHON) tools/testcases/check_runner_reap.py --mode helper
  ```
- 加入 `.PHONY` 列表与 `_locked-check` 前置清单（:994），**不**加入 `GATE_LOCKED_TARGETS`（无共享写状态，随 `check` 嵌套放行）、**不**加入 L2/L3/夜跑。
- 成本 ≤5 s；不满足则改回按需目标并在完成区说明。

### 6. 文档登记（一行）

- `docs/Process-07-门控分层规范.md` §1.1 表追加一行：`make check-runner-reap` / **L1** / 判据（合成驱动下 SIGTERM/INT/HUP 后子进程全部回收 + 诱饵存活；不跑 qemu/编译）。

## 修改文件范围

1. `tools/testcases/proc_reap.py`（新增）
2. `tools/testcases/check_runner_reap.py`（新增）
3. `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`
4. `tools/testcases/tset/libc-test/run_libc_test_user_suite.py`
5. `tools/testcases/tset/embench/run_embench_user_suite.py`
6. `Makefile`
7. `docs/Process-07-门控分层规范.md`
8. 本任务书（完成区 + 状态）
9. `.tao/knowledge/milestones.md`（本任务流水行状态）

**明确不动**：`spec/**`、`components/**`（含 QEMU 补丁/LLVM）、`contracts/**`、`tests/**`（含 `tests/inst` 向量与期望值）、`.tao/adr/**`、`manifests/**`、`.tao/contracts/**`、`tools/testcases/run_llvm_ts_user.py` 等薄 wrapper。

## 约束

1. **不改变被测语义**：qemu 调用参数、超时值、case 判定、JSON 结构均不动；只加登记/清理。
2. **不误杀**：禁 `pkill -f qemu`、禁按进程名全局匹配、禁 `killpg` 同组进程、禁杀自身进程组；只处置注册记录与自身直系子进程，且做 starttime（PID 复用）校验。
3. **无外部依赖**：仅 Python 标准库；Python ≥3.8 语法；`/proc` 缺失时 sweep 跳过而非失败。
4. **同类 runner 不许重构**：只把 `subprocess.run` 换成等价 `run_tracked` 并 `install()`；不改枚举/判定/报告逻辑；若替换导致行为差异且无法在 ≤30 行内修复 ⇒ 停手登记遗留，不扩改。
5. **不跑夜跑/长套件**：允许 `--only`/`--filter` 单例；`make check-modules`（L2 收尾门控）按需要跑；任一单成员预计 >10 min ⇒ 先申报。
6. **并发安全**：`runner-real` 启动前必须 `pgrep -x qemu-dadao` 为空；若发现他人夜跑/并发 qemu ⇒ **停手报告**，禁 kill 别人的进程；门控经 `make`（自动 `flock`），禁手工 `ninja`/`cp` 二进制。
7. **证据**：`.work/evidence/<任务ID>/run.sh`（+ `--inject`）一键复跑；注入用 `cp` 备份 + `md5sum` 对账还原，**禁** `git checkout/restore/stash/show` 还原；日志落 `.work/log/testcases/`（命名 `TESTCASES-085t-*.log` 或 `check-runner-reap.log`）。
8. **临时目录** `/tmp/opencode/TESTCASES-085t/`；仓库内不得留 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`*.bak` 与 `__pycache__`。
9. **提交权归 architect**：engineer 只改文件 + 填完成区；**不提交、不 push**。

## 验收标准

1. **文件集精确（9 项）**：`git status --porcelain -uall` 仅含「修改文件范围」9 项；`git diff --stat -- spec components contracts tests .tao/adr manifests` **为空**；越界即 FAIL。
2. **helper 自检**：`python3 tools/testcases/check_runner_reap.py --mode helper` rc=0，输出含 `SIGTERM`/`SIGINT`/`SIGHUP`/`timeout` 四类 `[PASS]`；诱饵存活；运行后 `pgrep -f <marker>` 为空、无遗留子进程。
3. **同类 runner 接线**：`--mode converted-runners` rc=0；两文件 `python3 -m compileall -q tools/testcases/tset/{libc-test,embench}` rc=0。
4. **假 qemu 端到端**：`--mode runner-fake` rc=0；打印 runner `rc=-15`（或 143）、fake pid 消失、`ps` 前后对照（含 `ppid`/`sid` 列）。
5. **真 qemu 端到端（用户要求的 ps 证据）**：`--mode runner-real` rc=0；证据须含
   (a) 信号前 `ps -o pid,ppid,pgid,sid,stat,cmd -p <runner>,<qemu>` 显示 qemu 的 `ppid=runner`；
   (b) `kill -TERM <runner>` 后 10 s 内 `pgrep -x qemu-dadao` **0 行**、`ps -p <qemu pid>` 空；
   (c) 诱饵 `qemu-dadao-decoy` 仍存活（证明未误杀）；
   (d) runner 退出码 = 143（或 Python `rc=-15`）。
   **前置**：启动前 `pgrep -x qemu-dadao` 为空（非空 ⇒ 停手报告）。
6. **反例注入（可达 FAIL）**：`bash .work/evidence/<任务ID>/run.sh --inject` rc=0 且内部完成「禁用清理钩子 ⇒ `--mode runner-fake` FAIL（打印遗留 pid + `ps` 证明）⇒ `kill` 残留 ⇒ `cp` 还原 + `md5sum` 与备份一致 ⇒ 重跑 PASS」；注入只动 `proc_reap.py` 的 `install()`（或 `kill_tracked()`）一行，不改测试断言。
7. **正常路径回归**：
   - llvm-ts 单例：`--link-mode dynamic --only 'SingleSource/Benchmarks/Stanford/Queens'` rc=0 且 `run_llvm_ts_user: PASS`（约 25 s，预检 23.2 s）；
   - libc 单例：`--link-mode static --filter <1 例> ...` rc=0（用例名与耗时现场记录）；
   - 两套输出元组/JSON 字段与改前一致（抽检 `run.json` 关键字段）。
8. **门控**：`make check` rc=0（日志含 `check-runner-reap` 通过）；`make check-modules` rc=0；`make check-milestones-fresh` rc=0；`make check-no-residue` rc=0；`make check-dirs` rc=0。
9. **无外部依赖/兼容**：`grep -nE '^(import|from) ' tools/testcases/proc_reap.py` 仅标准库；`python3 -c "import ast; ast.parse(open('tools/testcases/proc_reap.py').read())"` 通过；代码不含 `psutil`/`pgrep` 调用（`grep` 0）；`/proc` 不存在时的降级分支存在（人工核）。
10. **收尾**：完成区 ≤30 行、`**状态**` = `待验收`、`milestones.md` 流水行状态同步；证据脚本 `bash .work/evidence/<任务ID>/run.sh` rc=0；仓库无临时残留。

## 下发前预检（5 项，architect 本轮实测）

1. **任务书内部一致**：目标 6 项 ↔ 接口规范 6 节（helper / llvm-ts / 同类 runner / 自检脚本 / Makefile / 文档）↔ 修改文件 9 项 ↔ 验收 10 条逐条对应；安全判据 6 条在验收 2/4/5/6 均有着落；无悬空引用（仅引用 `084t`/`075t`/`050t`/`054t` 等已入流水或已归档任务号）。结论：**PASS**。
2. **验证手段前置实际可用（本轮实测）**：
   - `python3 --version` = `Python 3.12.3`；`.dadao/cross-toolchain/bin/qemu-dadao --version` rc=0（`qemu-dadao version 11.1.1 (v11.1.1-1-g84f1b66)`，11998912 B，10-31 10:16）；`clang`/`ld.lld` 在安装根；`.work/source/llvm-test-suite`、`.work/source/musl/lib/{crt1.o,libc.a}` 均在。
   - 单例正常路径：Queens dynamic rc=0，`run_llvm_ts_user: PASS`，`real 0m23.175s`（日志 `/tmp/opencode/TESTCASES-085t/precheck/pilot/run.log`）。
   - L1 基线：`make check` rc=0，`real 0m48.689s`（日志 `/tmp/opencode/TESTCASES-085t/precheck/check.log`），含 `repository checks (L1): PASS`。
   - **缺陷复现（真 qemu）**：XSBench dynamic，runner `3772330` → qemu `3772407`；`kill -TERM 3772330` 后 qemu 存活、`ppid=1`；已 `kill -9` 清理并确认 `pgrep -x qemu-dadao` 空（现场见本轮会话记录）。
   - **合成复现**：`start_new_session` 子进程在父 `SIGTERM` 后 `ppid=1` 存活（`/tmp/opencode/TESTCASES-085t/precheck/orphan_repro.py`）。
   - 注：`/tmp/opencode/**` 预检日志易失；正式证据须落 `.work/evidence/<任务ID>/`。结论：**PASS**。
3. **验收逐条可跑性**：1–10 现在均可跑，**无 BLOCKED**。成本警示：验收 8 的 `make check-modules` 含 embench smoke（全量 38 例），按 `Process-07` 为「几十 ~ 几百秒」；验收 5 的 XSBench 编译至 qemu 起跑实测 <2 min（本轮复现）；验收 6 注入仅跑 fake 模式（约 30 s）。结论：**PASS**。
4. **与 `contracts/`、`tests/inst/` 一致**：`grep -rn 'start_new_session\|killpg\|qemu-dadao' contracts/ tests/inst/` ⇒ 0 命中（runner 行为无契约面）；本任务不改任何期望值/向量；`tests/**` 零改动。结论：**PASS**。
5. **拟改文件 × `spec/` 清单**：命中 **0**（`grep -rl 'start_new_session' spec/` = 0；9 项全在 `spec/` 之外）。ADR：**无需新建**——这是 runner 健壮性修复，不涉跨组件契约/多方案取舍/外部契约固化。结论：**PASS（无 spec 授权需求）**。

## 风险与已知缺口

1. **信号 ↔ 线程池竞态**：`Popen` 返回后到 `track` 之间的窗口靠「`ppid == 本 runner` 直系兜底 sweep」覆盖；若宿主无 `/proc`，窗口不可兜底（记入完成区，仍不影响既有测试）。测试用 3 次信号变体 + 重复运行观察稳定性。
2. **误杀风险**：判据只在注册表与直系子进程内生效；`runner-real` 有诱饵断言；若同机有并发夜跑 ⇒ 前置 `pgrep -x qemu-dadao` 非空即**停手报告**（禁 kill 他人进程）。
3. **PID 复用**：`starttime` 不可读时退化为 pid 判据（极短窗口），在完成区登记为已知限制。
4. **同类 runner 行为变化**：`run_tracked` 必须逐字保持 `subprocess.run` 的超时/输出语义；若 libc/embench 单例回归出现差异且 >30 行才能修 ⇒ 按约束 4 停手登记遗留，只保留 llvm-ts 修复与 helper。
5. **L1 新增门控的成本/假红**：仅合成驱动（无编译、无 qemu），成本 ≤5 s；若在无 `/proc` 环境出现假红 ⇒ 改按需目标并在 `docs/Process-07` 标注，不静默降级。
6. **夜跑/长套件禁令**：`check-tset-llvm-full`、`check-night`、tset full 一律不跑；`make check-modules` 是收尾 L2 门控（非夜跑），如耗时异常按约束 5 申报。
7. **清理后的退出码**：handler 采用「清理 + 默认动作重发」⇒ 进程以信号退出（143/130/129）；不要把 rc 改成 0/1，否则夜跑会把「被外部终止」误判为正常完成。

## 完成区

**测试结果**：通过 10/10 验收项。`check_runner_reap.py` 四模式 rc=0（helper 4 s / converted 0.4 s / fake 3 s / real 4 s）；`bash .work/evidence/TESTCASES-085t/run.sh` rc=0（5m46s，`[SUMMARY] failures=0`，日志 `.work/log/testcases/TESTCASES-085t-evidence-final.log`）；`--inject` rc=0（注入后 runner-fake rc=1 + 遗留 `ppid=1` ps 证据 ⇒ cp 还原 md5 一致 ⇒ 回绿，日志 `...-evidence-inject.log`）；`make check` rc=0（52 s）、`check-modules` rc=0、`check-milestones-fresh`/`check-no-residue`/`check-dirs` rc=0；Queens dynamic rc=0 `run_llvm_ts_user: PASS`（23.3 s）、libc `functional/argv` static rc=0 `PASS`（20.2 s）。
**修改文件**：`tools/testcases/proc_reap.py`(新)、`tools/testcases/check_runner_reap.py`(新)、`tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`、`tools/testcases/tset/libc-test/run_libc_test_user_suite.py`、`tools/testcases/tset/embench/run_embench_user_suite.py`、`Makefile`、`docs/Process-07-门控分层规范.md`、本任务书、`.tao/knowledge/milestones.md`（`git status -uall` 恰为这 9 项；`git diff --stat -- spec components contracts tests .tao/adr manifests` 为空）。
**验收结果**：真 qemu 受控单例（XSBench dynamic）信号前 `ps` 显示 qemu `ppid=runner`（3803031←3802985，sid=3803031）；`kill -TERM` 后 runner `rc=-15`、qemu 10 s 内消失、`pgrep -x qemu-dadao` **0 行**、诱饵存活；helper 三信号轮次均 `rc=-15/-2/-1` 且 own-session/同组子进程与诱饵断言全绿；证据脚本逐项打印 expected/actual rc（见上日志）。
**新发现/坑**：① 单次 sweep 不够：llvm-ts 在 qemu 被 SIGKILL（rc=-9）后会立即启动 `-strace` 探针 spawn 第二个 qemu，可能落在 sweep 之后（自检 1/11 次复现，现场含 `qemu-strace.log`）⇒ handler 改为 2×50 ms 重扫；② shell 脚本的 `/proc/<pid>/comm` = **脚本文件名**，故伪 qemu 与真 qemu 同名 `qemu-dadao`，runner-real 前置检查须在启动前做；③ 注册表只由 track/release 改、handler 只读快照，无锁。
**遗留问题**：① handler 的 100 ms 重扫为经验窗口，理论上 >100 ms 的连续 spawn 仍可能漏（已登记，未扩大改动）；② `/proc` 缺失时 starttime 校验与直系 sweep 退化为仅注册表（不 FAIL，已在脚本注释声明）；③ `runner-real` 需 qemu 空闲，若同机并发夜跑 ⇒ 自检 FAIL 并停手（不 kill 他人进程）；④ 未取得新用户裁定，无裁定需落盘。
**返工说明（第 1 轮 Needs Revision）**：仅改 `.work/evidence/TESTCASES-085t/run.sh` 文件集检查为「`diff master...HEAD` ∪ `status -uall` 去重」现场比较（不写死脏树行数），并加可达 FAIL 自检 + 保护路径覆盖提交态 + `EVIDENCE INJECT: PASS` 标记；`run.sh` 连跑 2 次均 rc=0/`failures=0`（committed=9 dirty=2 union=9），`--inject` rc=0/md5 还原一致/`EVIDENCE INJECT: PASS`；功能主体未动，无 BLOCKED。

## 审阅记录

#### 第 1 轮 engineer 自审
逐行审查 `proc_reap.py` / `check_runner_reap.py` / 三 runner 接线 / Makefile / Process-07，并实测。finding 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `run_tracked` 把 `input=` 原样传给 `Popen` ⇒ TypeError（converted 模式首跑 FAIL） | ✅已修 | `kwargs.pop("input")` 后再按 `subprocess.run` 语义设 `stdin=PIPE` | `--mode converted-runners` rc=0 |
| runner-real 用 `wait_until` 取 qemu pid 返回 bool ⇒ `ps -p True` 报错、断言假红 | ✅已修 | 新增 `wait_value`；`ps_snapshot` 只接受正整数 pid | `--mode runner-real` rc=0，ps 行含 pid/ppid/pgid/sid |
| handler 单次 `kill_tracked()` 遗漏被 SIGKILL 后 probe 二次 spawn 的 qemu（真残留） | ✅已修 | handler 改 `kill_tracked` + 2×50 ms 等待重扫 + 收尾再扫 | 连跑 `--mode runner-fake` ×10 全 PASS、`pgrep -x qemu-dadao` 0 行 |
| 自检失败时 cleanup 只 kill pid 不 kill 组 ⇒ 注入后 fake 的 `sleep` 可能残留 | ✅已修 | `Checker.track_group` + cleanup 先 `killpg` | `--inject` rc=0，遗留 pid 断言 gone |
| 证据脚本 import 白名单漏 `time` ⇒ 自检 FAIL | ✅已修 | 白名单加 `import time` | 全量证据 rc=0（0 failures） |
| `proc_reap` 文档串含 `pgrep` 字样触发“grep 0”验收 | ✅已修 | 改为“external process-listing output” | `grep -cE 'psutil|pgrep' proc_reap.py` = 0 |
| 安全判据 1–6 逐条核对（自身 pid/pgid 跳过、starttime 复用校验、own-session 才 killpg、`/proc` 缺失降级、不遍历 ps 输出） | ❌不修（无 finding） | — | 见 `--mode helper` 诱饵/子进程断言与代码注释 |

判决：全部 finding 已修且复验通过；状态 `待验收`，无未修项。用户新裁定：无。

#### 第 1 轮 architect 提交与文件集审核
- **档位**：正常提交（协调者本轮显式指定消息 `feat(testcases): …`）。**偏离默认规则披露**：状态仍为 `待验收`、reviewer 未判决，按默认应 `WIP:`；本次按用户指令执行，reviewer 通过后无需再改消息。
- **提交**：`fa763558 feat(testcases): TESTCASES-085t 测试 runner 孤儿清理`（分支 `TESTCASES-085t`，**未 push**）。
- **文件集对账**：显式 staging 9 项 = 完成区「修改文件」9 项；无漏提 / 多提 / 越界；`git diff --stat -- spec components contracts tests .tao/adr manifests` 为空。
- **独立复核**：`make check-runner-reap` rc=0（4.8 s，SIGTERM/SIGINT/SIGHUP + timeout 全 `[PASS]`、诱饵存活、无 marker 残留）；`--mode converted-runners` rc=0；`py_compile`/`ast.parse` OK；`proc_reap.py` 仅标准库、无 `psutil|pgrep`。
- **安全边界抽查**：`kill_tracked` 只遍历注册表快照 + `ppid==self` 直系子进程；`_still_same` 比对 starttime（复用即跳过）；仅 `pgid==pid` 且非自身进程组才 `killpg`；证据注入使 `install()` 不装钩子 ⇒ runner-fake rc=1 + `ppid=1` ps ⇒ `cp` 还原 md5 一致 ⇒ 回绿。
- **结论**：可进 reviewer。

#### 第 1 轮 reviewer 验收

**重跑（不信叙述，逐项自跑）**：分支 `TESTCASES-085t`、HEAD=`33cd83bc`/实现 `fa763558`、`git status -uall`=0 行（树干净）、`git diff master...HEAD --name-only`=9 项、边界 `git diff --stat -- spec components contracts tests .tao/adr manifests`=0 字节；`proc_reap.py` md5=`7c2bec65` 与 HEAD 一致。

- 四模式独立跑：helper rc=0(4.3s，SIGTERM/INT/HUP `rc=-15/-2/-1`+timeout 全 PASS、诱饵活、marker 空)；converted rc=0(0.55s)；runner-fake rc=0(3.2s，fake ppid=runner、rc=-15、reaped、pgrep 空)；runner-real rc=0(3.9s，前置 `pgrep -x qemu-dadao` 空；真 qemu 3829458 ppid=3829416=runner、SIGTERM 后 gone、诱饵活)。
- 独立注入（非 engineer 点）：`kill_tracked` 首行短路 ⇒ runner-fake rc=1、孤儿 `ppid=1`(3842982)+ps；`cp`+md5 还原(`7c2bec65` 一致) ⇒ 回绿。engineer `--inject` rc=0(禁 install 钩子 ⇒ fake rc=1+ppid=1 ⇒ 还原 md5 一致 ⇒ 回绿)。
- 独立真实 SIGTERM（不经 checker）：真 runner+真 qemu，信号前 ps 显示 qemu 3856377 ppid=3856295=runner、sid=自身；`kill -TERM` 后 runner/qemu 双 gone、`pgrep -x qemu-dadao` 空、诱饵存活。
- 门控：`make check` rc=0(53s，含 check-runner-reap PASS)、`check-modules` rc=0(240s)、`check-runner-reap` rc=0(4.8s)、`check-run-artifacts` rc=0、`compileall` rc=0；proc_reap 仅标准库、无 psutil/pgrep、ast.parse 通过。

**约束核验**：只杀登记或 `ppid==self` 直系(sweep)、`/proc` starttime 防 PID 复用、own-session 才 killpg、不误杀诱饵、handler 2×50ms 重扫、`run_tracked` 保持 `subprocess.run` 超时/输出语义、不改 spec/contracts/tests/QEMU —— 逐条核过无违反；完成区 5 行(≤30)、milestones 同步「待验收」、无 `__pycache__`/`*_tmp*` 残留。

**唯一失败（阻断）**：`bash .work/evidence/TESTCASES-085t/run.sh` rc=**1**（两次重跑均 `[SUMMARY] failures=1`，`grep '^\[FAIL\]'` 唯一命中第 2 行 `file set mismatch`；其余全绿含 make check/check-modules/回归）。根因：run.sh L151-168 把「工作树恰好含 9 个**未提交**文件」写死为期望值，architect 已提交 `fa763558`、树已干净 ⇒ ACTUAL=[] ≠ 9 项 ⇒ 必然红，证据脚本提交后**不可复跑**；违反验收 #10「run.sh rc=0」与「覆盖/计数不写死（须现场值）」纪律（完成区「rc=0(5m46s)」系提交前所跑、非伪造，但当前交付状态重跑即红）。

**修复建议**：run.sh 文件集检查改为同时接受提交态——`git status --porcelain -uall` 为空 **且** `git -c core.quotepath=false diff master...HEAD --name-only | sort` == 9 项期望（保留原「树脏=9 项」分支以兼容提交前），改后重跑应 rc=0。

**判决：Needs Revision**（仅此 1 项；其余验收 1-9 我自跑全过，修 file-set 一处即可直接进 `/complete`）。

#### 第 1 轮返工（Needs Revision 处置）

**改动**：只改证据脚本 `.work/evidence/TESTCASES-085t/run.sh`（`check.py` 无同类问题，未动）。文件集期望改为「`git -c core.quotepath=false diff --name-only master...HEAD` ∪ `git status --porcelain -uall`，按路径 `sort -u` 去重」后与 9 项期望比较，**不再写死脏树行数**；期望/实际条数现场统计打印（`committed=/dirty=/union=`）。另新增两项不削弱检查的配套：① 可达 FAIL 自检（多一项、少一项都必须判 mismatch，防恒真）；② 保护路径检查扩到「提交集 + 工作树」两态（`diff master...HEAD` 与 `diff HEAD`），避免提交后该断言变空真空。`--inject` 末尾补 `EVIDENCE INJECT: PASS` 标记（仅输出，不改断言）。

**返工后真实输出**（日志 `/tmp/opencode/TESTCASES-085t/rework/`）：
- `run.sh` 第 1 次：rc=**0**，5m50s，`[INFO] file set: committed=9 dirty=2 union=9`、`[PASS] file set: union(committed,dirty) = exactly 9 expected paths (actual=9)`、`[PASS] file set assertion: rejects extra and missing path (FAIL path reachable)`、`[SUMMARY] failures=0`（§966 条 PASS）。
- `run.sh` 第 2 次（紧接着）：rc=**0**，5m49s，`committed=9 dirty=2 union=9`，`[SUMMARY] failures=0`。
- `run.sh --inject`：rc=**0**，11s，注入后 runner-fake rc=1 + 孤儿 `ppid=1`(3894543) ps ⇒ `cp` 还原 md5 `7c2bec65…` 与 HEAD 一致 ⇒ 回绿，`[SUMMARY] inject: failures=0`、`EVIDENCE INJECT: PASS`。
- 提交态（树干净）复跑等价验证：`diff <(期望 9 项) <(diff master...HEAD | sort -u)` 为空 ⇒ 同一脚本在干净树同样判 PASS（联集退化为提交集）。
- 披露：上述两次全量跑完成后，只在 `--inject` 分支末尾加了 `EVIDENCE INJECT: PASS` 一行（非注入路径不可达）；该行加完已重跑 `--inject` rc=0 复验，全量路径代码未再变动（`bash -n` 通过）。
- 现状（返工收尾时现场复算）：`git status -uall` 仅本任务书 1 项（`milestones.md` 改回 HEAD 的「待验收」后无 diff），`committed=9 dirty=1 union=9` 与期望一致；`tools/testcases/proc_reap.py` md5=HEAD（`7c2bec65…`）；无遗留进程（`pgrep -x qemu-dadao` 空）。

**判决自审**：唯一阻断项 ✅已修并有达 FAIL/回绿证据；其余验收项未改动、未削弱。**无 BLOCKED**。状态 → `待验收`。

#### 第 2 轮 engineer 自审（返工）

逐行审查改后的 `run.sh`（L151-202）与两态复跑结果：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 文件集写死「脏树恰 9 行」⇒ 提交后必红（reviewer 阻断） | ✅已修 | 改为 `diff master...HEAD` ∪ `status -uall` 后 `sort -u`，期望/实际条数现场统计 | 脏态 ×2 rc=0 `failures=0`；干净态等价 diff 为空；`--inject` rc=0 |
| 保护路径检查提交后变「空真空」（同根因，自查） | ✅已修 | 同时查 `diff master...HEAD` 与 `diff HEAD`（提交集+工作树） | 两态输出均 `[PASS] protected paths untouched` |
| 文件集断言无可达 FAIL 自证（自查，防恒真） | ✅已修 | 增「多一项 / 少一项必须 mismatch」自检 | `[PASS] file set assertion: rejects extra and missing path` |
| `status --porcelain` 用 `awk $NF` 取路径，含空格路径会截断 | ⏸延后 | 未改 | 本仓库相关路径无空格；重命名条目取新路径；解析改造超范围 |
| `master...HEAD` 不可用（如无 master）时无显式报错 | ❌不修 | 未改 | 联集只剩 status ⇒ 与 9 项期望不匹配即 `[FAIL]`，非静默通过；脚本本身按任务分支语义设计 |

判决：阻断 finding 全部 ✅已修、复验通过；状态 `待验收`，无未修阻断项。用户新裁定：无。

#### 第 1 轮 architect 返工提交与文件集审核
- **档位**：正常提交（协调者本轮显式指定消息 `fix(testcases): …`；状态 `待验收`、reviewer 未重判，按默认应 `WIP:`，本次按用户指令执行并披露）。
- **提交**：`24be9d88 fix(testcases): TESTCASES-085t 证据脚本提交态复跑`（分支 `TESTCASES-085t`，**未 push**）。
- **文件集对账**：显式 staging 1 项 = 本任务书（返工说明 + 返工/自审记录）；`git diff master...HEAD --name-only` 仍为 9 项且与完成区「修改文件」逐项一致，无漏提/多提/越界；`git diff --stat -- spec components contracts tests .tao/adr manifests Makefile` 为空；证据脚本 `.work/evidence/**` 被 `.gitignore` 覆盖，不入库（修复只体现在任务书记录）。
- **独立复核**：现场按 `run.sh` 同款公式复算 `committed ∪ dirty` = 9 项且与 EXPECTED 完全一致（`dirty=1` 即本任务书）；`bash -n run.sh` OK；返工日志 `/tmp/opencode/TESTCASES-085t/rework/` 中 `run1/run2` 均 `[SUMMARY] failures=0`、`grep -c '^\[FAIL\]'`=0，`inject2.log` 4 条 `[FAIL]` 均为注入预期（fake 未被清理）、`restored md5=7c2bec65` 与 HEAD 一致、`EVIDENCE INJECT: PASS`。
- **实现未动**：`git status -uall` 提交后为空；`proc_reap.py` md5=HEAD；返工后全量跑仅在 `--inject` 分支末尾加输出行（已复验 `--inject` rc=0），跟踪代码零改动。
- **结论**：唯一阻断项（提交态不可复跑）已修且有可达 FAIL/回绿证据；可进 reviewer 重判（重点：干净树重跑 `run.sh` 应 rc=0）。

#### 第 2 轮 reviewer 验收（复审返工）

**快照对账**：开工/收工 `git status --porcelain -uall` 均 **0 行**；HEAD=`d23dc726`（留痕）/`24be9d88`（返工提交）；`git diff master...HEAD --name-only` = **9 项**，与完成区「修改文件」逐项一致（`diff` rc=0）；`git diff --stat master...HEAD -- spec components contracts tests .tao/adr manifests` **空**；6 个跟踪实现文件（`proc_reap.py`/`check_runner_reap.py`/三 runner/`Makefile`）工作树 md5 与 `git show HEAD:` **逐一 SAME**；`.work/evidence/**` 被 `.gitignore:2` 覆盖（`git check-ignore` 命中、`git ls-files .work`=0），不入库。

**干净树重跑（阻断项复验）**：`bash .work/evidence/TESTCASES-085t/run.sh` → **rc=0**、`grep -c '^\[FAIL\]'`=**0**、`[SUMMARY] failures=0`（972 条 PASS）；关键行 `[INFO] file set: committed=9 dirty=0 union=9` + `[PASS] file set: union(committed,dirty) = exactly 9 expected paths (actual=9)` + `[PASS] protected paths untouched`。随后回绿复跑（注入清理后第二次全量）同 **rc=0 / failures=0 / union=9**。上轮唯一阻断（提交态必红）**已消除**。

**注入（两处，均非凑绿）**：① `run.sh --inject` rc=**0**：禁 install 钩子 ⇒ runner-fake rc=1 + 孤儿 `3909122 ppid=1` ps 证据 ⇒ cp 还原 md5=`7c2bec65` 一致 ⇒ post-restore rc=0、`EVIDENCE INJECT: PASS`。② **reviewer 独立注入**（非 engineer 点：`kill_tracked()` 首行 `return []`）：`--mode runner-fake` **rc=1**、`[FAIL] fake qemu reaped: after: 3909365 1 ...`（孤儿 ppid=1）；`cp` 还原 + md5 回 `7c2bec65`（=HEAD）+ `git status` 0 行 ⇒ 重跑 **rc=0**。③ **文件集可达 FAIL**（多一项）：临时 `touch tools/testcases/__reviewer_extra__.py` 后重跑全量 → **rc=1**、唯一 `[FAIL] file set mismatch (actual=10 expected=9)`；删文件后重跑 rc=0。少一项：`git clone -s` 到 /tmp（master 态）复算同款公式 `union=0 ≠ 9` ⇒ mismatch 可达。

**文件集断言核**：`compute_fileset()` = `git diff master...HEAD --name-only` ∪ `git status --porcelain -uall`，`sort -u` 去重、期望 9 项与实际条数均现场统计打印；**无写死脏树行数**（grep `dirty=1|dirty=2` 于 run.sh 0 命中）；内建「多/少一项必须 mismatch」自检 `[PASS] ... (FAIL path reachable)`，叠加我方真实注入证非恒真。保护路径检查同时查 `master...HEAD` 与 `HEAD`（提交集+工作树），两态实测均 PASS。

**四模式/残留抽查**：`make check-runner-reap` rc=**0**（4.9 s，SIGTERM/INT/HUP `rc=-15/-2/-1` + timeout 子进程回收、诱饵存活、marker 0 命中）；全量日志中 runner-real rc=0（前置 `pgrep -x qemu-dadao` 空；真 qemu 3922868 ppid=3922832=runner、`-s small` XSBench；SIGTERM 后 `no qemu-dadao left`、诱饵存活）；runner-fake / converted-runners / compileall / Queens+libc 回归 / `run.json` 字段校验 / `make check`(L1，含 check-runner-reap PASS)/ `check-modules`(L2，含三套 tset smoke)/ `check-milestones-fresh`/`check-no-residue`/`check-dirs` 全 rc=0。收工 `pgrep -x qemu-dadao` 空、`pgrep -af TC085t` 空、无 `__pycache__`/`*_tmp*`/`*.orig` 残留新增。

**约束核验**：只改 9 项、未碰 spec/components/contracts/tests/adr/manifests（两态 diff 空）；`proc_reap.py` 仅 5 个标准库 import、无 `psutil|pgrep`、`_HAS_PROC` 降级分支在；三 runner 仅 `import proc_reap` + `popen_tracked`/`run_tracked` + `install()` + `finally release`，`start_new_session` 位置未变、libc/embench 未加 session；handler 保留「信号重发」语义（`rc=-15/-2/-1` 实测）；完成区 6 非空行（≤30）、各审阅小节 ≤40 行、`**状态**`=待验收、milestones 行同步；无越界。

**发现（非阻断）**：run.sh 用 `awk '{print $NF}'` 解析 porcelain 路径，含空格路径会截断——engineer 已自查登记为遗留（本仓库相关路径无空格），不改判。

**判决：Accepted**——上轮唯一阻断项在我自己的干净树重跑下消除（rc=0/failures=0），注入 FAIL 路径与还原回绿全部实测，约束无违反，可进入 `/complete`。

#### 第 2 轮 architect 交叉复核（`/complete`）

**开工快照**：分支 `TESTCASES-085t`、HEAD=`d23dc726`；`git status -uall` 仅本任务书 1 项（reviewer 记录未提交）；`git diff master...HEAD --name-only` = 9 项且与完成区「修改文件」逐项一致；`git diff --stat master...HEAD -- spec components contracts tests .tao/adr manifests` 为空。

**功能代码未动**：`proc_reap.py`/`check_runner_reap.py`/三 runner/`Makefile`/`Process-07`/`milestones.md` 工作树 md5 与 `git show HEAD:` 逐一 **SAME**；`git show --name-only 24be9d88 d23dc726` 均**只含本任务书**（返工/留痕提交不触实现）。

**证据脚本本方独立重跑（不采信叙述）**：`bash .work/evidence/TESTCASES-085t/run.sh` **rc=0**、`[SUMMARY] failures=0`、`grep -c '^\[FAIL\]'`=**0**、981 条 PASS；关键行 `[INFO] file set: committed=9 dirty=1 union=9` + `[PASS] file set: union(committed,dirty) = exactly 9 expected paths (actual=9)` + `[PASS] protected paths untouched (… committed+worktree)`；所有 `run_cmd` 均 `actual_rc=0`（无一例外）。日志 `/tmp/opencode/TESTCASES-085t/complete/run.log`（约 6 min）。`dirty=1` 即本任务书，联集与干净树同（reviewer 已跑 `dirty=0` 一轮）。

**文件集断言核（防恒真）**：`compute_fileset()` = `git diff --name-only master...HEAD` ∪ `git status --porcelain -uall | awk $NF`，`sort -u` 去重，**无写死脏树行数**（`dirty=`/`committed=` 仅 INFO 现场打印）；内建「多一项/少一项必须 mismatch」自检为 `[PASS] … (FAIL path reachable)`；保护路径同查 `master...HEAD` 与 `HEAD` 两态。

**独立注入（补齐 reviewer 未覆盖的一点：L1 门控自身可达 FAIL）**：reviewer 注入点在 `install()`/`kill_tracked()` 但只对 `--mode runner-fake` 判定；我改在 `kill_tracked()` 首行 `return []`（md5 `7c2bec65`→`739d5328`）后直跑门控目标 `make check-runner-reap` ⇒ **rc=2**、`[FAIL] SIGTERM/SIGINT/SIGHUP children reaped` 各带 `ppid=1` 的 ps 证据；`cp` 还原 md5 回 `7c2bec65`（=HEAD）⇒ 重跑 **rc=0**、23 条 PASS、marker/qemu 均空。日志 `…/complete/gate-inject.log`、`…/complete/gate-restored.log`。

**过程事故（已闭环，无副作用）**：注入后清理残留时一条 `pkill -f` 模式串含在我自己 shell 的命令行里，误杀本命令（回执 `Killed by SIGTERM`）；改用变量拼接重跑，确认 marker 空、`proc_reap.py` 已还原为 HEAD md5。

**reviewer 是否遗漏/过松**：逐项对账无过松——9 项范围 ↔ 完成区一致；四模式/两回归/五个门控在本方重跑全绿；注入非凑绿（`sed` 目标行若不存在则 md5 不变即自判 FAIL）；`--inject` 用 `cp`+md5（未用 `git checkout/restore/show`）；唯一非阻断遗留（`porcelain` 路径含空格会截断）已登记，本仓库相关路径无空格。

**长度/状态**：完成区 6 非空行（≤30）；各审阅小节 7–17 行（≤40）；`**状态**`=待验收、`milestones.md` 流水行=待验收。

**残留**：收工 `pgrep -x qemu-dadao`、`pgrep -af TC085t` 均空；`git status -uall` 仅本任务书；`tools/**/__pycache__` 由 `make check` 内 `compileall -q tools` 生成（`.gitignore` 覆盖，`check-no-residue` rc=0）。

**结论**：无阻断，可进入 `/complete`（merge squash + push 归主会话；本会话不 push、不 merge）。

#### 主会话统一收尾

reviewer 复审与 architect 交叉复核均为 **Accepted**，无分歧；主会话采信并置任务 `已验证`。本任务只修测试 runner 外部终止时的 qemu 孤儿回收，未改 QEMU/spec/测试向量语义。遗留：handler 100 ms 重扫为经验窗口；无 `/proc` 时降级；porcelain 路径含空格时解析会截断（当前仓库无此路径）。
