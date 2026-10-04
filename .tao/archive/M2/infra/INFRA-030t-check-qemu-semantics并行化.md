# INFRA-030t: check-qemu-semantics 并行化（降低 `make check` 耗时）

**模块**：infra
**项目里程碑**：M2
**依赖**：无（纯本地 Python/Makefile 改造；不改被编译的组件源码）
**状态**：已验证

## 背景与动机（事实）

- 实测 `make check` 单次 **67.2s**，其中 **`check-qemu-semantics` 46.3s（69%）**，其余 15 个门控合计约 21s。
- 根因：`tests/scripts/run_qemu_test.py::run_batch()` **严格串行**逐用例调用 `run_single_test()`，每个用例**启动一次 `qemu-system-dadao`**；当前 gate 目录含 `reg-shift-extend.yaml`(113) + `reg-compare.yaml`(36) = **149 用例**。
- 每个子代理每任务都会重跑数次 `make check` ⇒ 该 46s 被放大数倍。

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `tests/scripts/run_qemu_test.py`（`run_batch()` L485–546；`run_single_test()` 产物经 `uuid` 命名 ⇒ **并行安全**；`artifact_dir` 为共享目录但文件名唯一）
  - `Makefile` 的 `check-qemu-semantics` 目标（L322；`JOBS ?= 8`，见项目「构建并行度」规则：**默认 8，禁止全核**）

- **输出**：
  1. `tests/scripts/run_qemu_test.py`：
     - `run_batch(..., jobs=1)` 支持并行执行用例（`concurrent.futures.ThreadPoolExecutor`，子进程 I/O 密集 ⇒ 线程即可）；
     - 新增 CLI `--jobs N`（默认取环境变量 `JOBS`，无则 1 —— **默认保持串行语义**，只有显式传入才并行）；
     - **结果聚合必须确定有序**（按 `(文件序, 用例序)` 回填），`fail_details` 顺序与串行一致；
     - `main()` 的汇总格式与退出码语义（0 / 1 / 2，ADR-0009 fail-closed）**不得改变**。
  2. `Makefile`：`check-qemu-semantics` 调用追加 `--jobs $(JOBS)`。
  3. `tests/scripts/README.md`：补一句 `--jobs` 说明（若该文件有相应章节）。

- **约束**：
  - **纯 Python + Makefile 改动，无需重建**任何组件；**不碰** `.work/source/**`、`components/**`、`tests/vectors/**`。
  - 并行度**只用 `JOBS`（默认 8）**，禁止 `nproc` 全核。
  - 失败/异常**即停、禁自动重试**。
  - 不提交 git。

## 验收标准（逐条真实命令 + 输出 + 退出码；**每条须能失败**）

1. **功能不变**：`make check-qemu-semantics` PASS，汇总计数与串行**一致**（149 total / 149 passed / 0 failed；记录真实数字）。
2. **耗时下降**：给出 `--jobs 1` 与 `--jobs 8` 的**实测墙钟**（`date +%s.%N` 或 `time`），并给出提升倍数；同时给 `make check` 整体前后对比（前值 **67.2s**）。
3. **逐用例等价（关键）**：对同一向量目录，`--jobs 1` 与 `--jobs 8` 的**逐用例 PASS/FAIL 集合完全相同**——用机器可读方式（如 `-v` 输出排序后 diff，或临时脚本导出 `file[idx]=status`）比对，给出 `diff` 为空/非空的**真实输出**。**不接受**只比总数。
4. **失败不被吞（关键，反例门控）**：在**隔离副本**里注入一个反例（改坏某用例的 `expected_fault` 期望值，或改坏某 `encoding.word`）⇒ `--jobs 8` 必须 **rc=1** 且报出与 `--jobs 1` **同一个** FAIL 条目；还原后回绿。给出注入→FAIL→还原→回绿的完整真实输出与还原证据（副本可用 `/tmp/opencode/INFRA-030t/`）。
5. **确定性**：`--jobs 8` 连跑两次，汇总行与 `fail_details` **完全一致**（给两次输出）。
6. **超时语义不变**：说明并行下 `INCONCLUSIVE`（timeout，`DEFAULT_TIMEOUT=9`）的计数与串行一致；如成本允许，构造 1 个用例的超时验证（否则说明理由）。
7. **无残留**：并行跑完后 `make check-no-residue` EXIT=0；`.dadao/tests/harness/`（`artifact_dir`）无遗留 `dadao-test-*.bin` / `dadao-qmp-*.sock`。
8. **回归**：`make check` 全量 **EXIT=0**，且 lit 26/26、semantics 计数不变。

## 完成区

**测试结果**：通过 8/8 验收项（逐条真实输出见下）。

**修改文件**（3 个；仅任务书范围内文件）：
- `tests/scripts/run_qemu_test.py`：新增 `_load_cases()`（按 `abspath+mtime_ns+size` 记忆化向量 YAML）；`run_batch(..., jobs=1)` 用 `ThreadPoolExecutor` 并行执行、按 `(文件序,用例序)` 有序回填聚合；`--jobs N` CLI（默认 `$JOBS`，无则 1）；批量 `-v` 增加有序逐用例状态行；dump 模式批量并行不安全时强制串行并 stderr 提示。
- `Makefile`：`check-qemu-semantics` 追加 `--jobs $(JOBS)`（`JOBS ?= 8`，不用 nproc）；更新陈旧注释。
- `tests/scripts/README.md`：补 `--jobs`/`$JOBS` 说明。

**验收结果**（真实命令 + 输出 + 退出码）：

- ① **功能不变**：`make check-qemu-semantics` → `EXIT=0`，`Results: 149 total, 149 passed, 0 failed, 0 deferred, 0 errors`，`check-qemu-semantics: PASS`（日志 `.work/log/infra/INFRA-030t-final-make-sem.log`）。
- ② **耗时下降**（真实测量）：
  - `check-qemu-semantics` 前值（`git HEAD` 原版脚本串行跑同目录）：**45.66s**（149/149，EXIT=0，`.work/log/infra/INFRA-030t-before-orig-serial.log`）——与任务所述 46.3s 一致。
  - 现值：CLI `--jobs 1` **3.06s** / `--jobs 8` **0.99s**（日志 `.work/log/infra/INFRA-030t-final-jobs{1,8}.log`，含解释器启动与 `-v` 输出开销），故 CLI 比值 3.1x；去 CLI/`-v` 开销的精测：serial 2.43s vs thread8 **0.38s → 6.4x**（与进程池 0.36s 相当）；`make check-qemu-semantics`（走 `JOBS=8`）**1.43s**（较 45.66s **≈32x**）。
  - `make check` 整体：**前 67.2s → 后 22.37s（≈3.0x）**。前值由任务给定且由本地 45.66s（semantics）＋其余约 21s 佐证。
  - **重要事实（需沉淀）**：46s 的真实根因**不是**「串行启动 QEMU」（QEMU 合计仅 ~2.4s），而是 `build_binary()` **每例重新 `yaml.safe_load` 整个向量文件**（`cProfile`：占 `build_binary` 的 99.6%），且为 GIL 绑定 → 单纯上线程 **0 提速**（未加缓存时 `thread8`≈45s）。消除重复解析后线程才生效。故本次**同时**做了「缓存解析」与「并行」两件事，缓存须先行。
- ③ **逐用例等价（关键）**：`--jobs 1 -v` 与 `--jobs 8 -v` 各导出 149 行 `  <status> <file>[<idx>]` 排序后比对 → `diff` **空**，`DIFF_EXIT=0`（持久化证据 `.work/log/infra/INFRA-030t-status-jobs{1,8}.txt` 与 `.work/log/infra/INFRA-030t-status-diff.log`；源日志 `INFRA-030t-final-jobs{1,8}.log`）。非仅比总数。
- ④ **失败不被吞（关键，反例门控）**：隔离副本 `/tmp/opencode/INFRA-030t/inject/`（`cp` 两份 yaml），把 `reg-shift-extend.yaml` 第 26 行（用例 `[1]` `ext.uo_orrr_rd`）`expected_state.rd.rd1` 由 `0x...07` 注入为 `0x...08`：
  - `--jobs 1` → `EXIT=1`，`FAIL reg-shift-extend.yaml[1]: Test failed with code 0x01`（`Results: 149 total, 148 passed, 1 failed`）。
  - `--jobs 8` → `EXIT=1`，**同一个** FAIL（`148 passed, 1 failed`）；两 jobs 的 FAIL 集合 `diff` 空（`DIFF_EXIT=0`）。
  - 还原（第 26 行改回 `0x...07`）→ `--jobs 8` → `EXIT=0`，`149 total, 149 passed, 0 failed`。注入前/后 md5 与还原行见日志；`git status --porcelain tests/vectors/ = 0 行`（未触碰真实向量）。
- ⑤ **确定性**：`--jobs 8` 连跑两次 gate → 完整输出 `diff` **空**（`GATE_DIFF_EXIT=0`）；注入态连跑两次 `--jobs 8` → `diff` 空（`INJ_DIFF_EXIT=0`），两次 `fail_details` 同为 `FAIL reg-shift-extend.yaml[1]: Test failed with code 0x01`。
- ⑥ **超时语义不变**：用 `--timeout 0` 强制超时（`reg-compare` 36 例）：`--jobs 1` 与 `--jobs 8` 均 `36 errors`（INCONCLUSIVE），逐用例集合 `diff` 空（`DIFF_EXIT=0`），两者 `EXIT=1`；不变量保持。
- ⑦ **无残留**：`make check-no-residue` `EXIT=0`；干净并行跑后 `.dadao/tests/harness/` 中 `dadao-test-*.bin`/`dadao-qmp-*.sock` **各 0 个**（注：清理了 1 个由本轮早前被中断的后台探针残留 `dadao-test-a11b7a06.bin`，非并行跑产生）。
- ⑧ **回归**：`make check` `EXIT=0`（22.37s）；lit `PASS: ... (26 of 26)`；`check-qemu-semantics` 149/149；`repository checks: PASS`（`.work/log/infra/INFRA-030t-final-make-check.log`）。

**新发现/坑**：
1. **真实根因是重复 YAML 解析，不是串行 QEMU**：`build_binary()` 每例 `yaml.safe_load(整个向量文件)`，占其耗时 99.6%；149 例即重复解析 149 次。纯 Python（GIL 绑定），因此只上 `ThreadPoolExecutor` **零提速**（实测 thread8≈45s）。→ 必须先加解析缓存，线程才生效（serial 45.9s→2.4s，thread8 0.38s）。建议沉淀到知识库。
2. **缓存不能在 miss 时 `clear()`**：初版为限大小在 miss 时清空整个缓存，多线程下造成颠簸（大文件被反复重解析），thread8 反而无提速。改为纯赋值后解决。
3. **`yaml.safe_load` 是纯 Python（SafeLoader）**；本机虽有 libyaml 但 `safe_load` 不走 C 解析器，故 GIL 占用高。
4. **dump 模式批量不并行安全**：`_attempt_qmp_dump` 写固定路径 `<harness>/dumps/state.bin`，并行会互相覆盖 → 已显式降级为串行并 stderr 提示（非静默）。
5. `run_batch` 默认 `jobs=1` 且 `__main__` 默认 `$JOBS`/1：无标志直跑仍串行；只有 Makefile 显式传 `--jobs $(JOBS)` 才并行（默认 8）。
6. 线程池 `max_workers=1`（`--jobs 1`）与纯串行基本等价（2.45s vs 2.43s）。

**遗留问题**：
- 无阻塞项。次要注意：缓存为**进程内**、键含 `mtime_ns+size`；单进程一次运行内安全，不跨进程共享（无需）。
- `deferred.md` 已登记的门控目录瞬态问题（`QEMU-032t` reviewer 观察）与本改动无关，未处置。

## 自审记录

### 第 1 轮 engineer 自审

**审查范围**：`tests/scripts/run_qemu_test.py`（`_load_cases`/`build_binary`/`run_batch`/`main`）、`Makefile`、`tests/scripts/README.md`。逐行检查逻辑正确性、边界、惯用法、防造假，并用真实反例/回归验证。

**结论**：所有 finding 已处置，无未修项 → 状态置 `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `run_batch` docstring 称「工作 I/O 密集、线程即可」，与实测不符（真实瓶颈是 GIL 绑定的重复解析） | ✅已修 | 改写 docstring：说明缓存消除 GIL 绑定解析后、每例由 QEMU 子进程 wait 主导（释放 GIL）故线程有效 | `git diff` 见新 docstring；thread8 实测 0.38s（见验收②） |
| F2 批量 `--dump --jobs>1` 会并发写同一 `<harness>/dumps/state.bin` 相互覆盖 | ✅已修 | `run_batch` 内 `dump_mode and workers>1` → 强制 `workers=1` 并向 stderr 显式提示（非静默） | 代码审查 + `--help`/运行无回归；非 dump 路径未受影响（149/149 仍绿） |
| F3 初版缓存 miss 时 `_VECTOR_CACHE.clear()`，多线程下颠簸致大文件反复重解析、线程零提速 | ✅已修 | 去掉 `clear()`，改为纯 `_VECTOR_CACHE[key]=cases`（dict 操作 GIL 下原子） | 修前 thread8≈3.56s（无提速）→ 修后 thread8=0.38s（见验收②） |
| F4 曾给批量 banner 加 `(N job(s))`，属改动既有输出格式，超出任务对 `main()` 汇总格式不变的要求 | ✅已修 | banner 还原为原文；仅新增「`-v` 时」的有序逐用例状态行（不改变无 `-v` 输出） | `--jobs 1 -v` / `--jobs 8 -v` 的 `Results:` 行与串行一致（验收①②） |
| F5 重写 `run_batch` 后聚合用的 `passed/failed/errors/fail_details` 需在各分支前定义完整 | ✅已修 | 在聚合段前统一初始化；`run_cursor` 严格对应 `run_items` 顺序 | 149/149 计数正确（验收①）；确定性连跑 diff 空（验收⑤） |
| F6 `main()` 新增 `--jobs` 参数校验分支的退出码语义 | ✅已修（沿用 argparse 约定） | 非法 `JOBS`/`--jobs<1` → `sys.exit(2)`；正常 fail-closed 0/1/2 不变 | `JOBS=abc` → `EXIT=2` 且打印 `Error: invalid JOBS value 'abc'`；`--timeout 0` 仍 `EXIT=1`（验收⑥） |
| F7 聚合循环中 `vf`/`case` 对 `run` 项未使用（仅 deferred 用 `case`） | ❌不修 | 保留元组解包以维持 `plan` 结构清晰；无功能影响 | 代码审查；无 lint 工具（AGENTS.md 未启用） |

**关键决策记录**：任务规定的机制为 `ThreadPoolExecutor`。核查发现「子进程 I/O 密集」前提不成立——真实瓶颈是 `build_binary()` 每例重复 `yaml.safe_load`（占比 99.6%，GIL 绑定），故**单靠线程零提速**。为既满足任务指定的 `ThreadPoolExecutor` 又达成验收②，本实现**先消除重复解析（`_load_cases` 缓存）**，再以线程池并行；两条改动的因果链由实测证明（缓存后 thread8 0.38s）。未采用 `ProcessPoolExecutor`（仅用于诊断探针，未进入产物）。

---

### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理
**审查日期**：2026-10-03
**审查范围**：`tests/scripts/run_qemu_test.py`、`Makefile`、`tests/scripts/README.md`，对照任务书 8 条验收标准 + 额外缓存正确性/反例门控要求。

#### 重跑记录（真实命令 + 输出 + 退出码）

**① 功能不变**
```
$ make check-qemu-semantics
check-qemu-semantics: running shift+compare (all cases)...
Running batch tests from /mnt/tao/DADAO-v5/.dadao/tests/harness/gate...
Results: 149 total, 149 passed, 0 failed, 0 deferred, 0 errors
check-qemu-semantics: PASS
EXIT=0
```
✅ 149/149，EXIT=0。

**② 耗时下降**
```
$ time make check-qemu-semantics
real  0m1.426s  user  0m1.711s  sys  0m1.176s
EXIT=0

$ time make check
real  0m22.297s  user  0m20.695s  sys  0m4.772s
EXIT=0
lit 26/26 (100%)
check-qemu-semantics: PASS
repository checks: PASS
```
- `check-qemu-semantics`：1.43s（工程师报告1.43s，一致）
- `make check` 整体：22.30s（工程师报告22.37s，一致；前值67.2s → ≈3.0x 提升）

**独立 YAML 解析计时（验证根因）**：
```
$ python3 -c "149 YAML parses: 66.368s (445.4ms/case); 2 YAML parses: 0.445s"
```
149 次 `yaml.safe_load` 合计66s（本机比工程师的45.66s 更慢），**远超**串行总耗时，强烈支持「重复解析是主因」的结论。

**③ 逐用例等价**
```
--jobs 1 -v → 149 行状态行（raw 顺序：reg-compare.yaml[0]...reg-shift-extend.yaml[112]）
--jobs 8 -v → 149 行状态行（raw 顺序：完全相同）
sorted diff: DIFF_EXIT=0（空）
raw（未排序）diff: 也完全相同 → 证实聚合按 (文件序,用例序) 确定性输出
```

**④ 反例门控（注入→FAIL→还原→回绿）**
```
注入：reg-shift-extend.yaml 第26行 rd1: '0x07' → '0x08'
  md5 前: 073f9fd7c742961283022aaf6a7501f3
  md5 后: 59b5f4a69663bfb93fb2c118cc0bac6c（不同，确认注入生效）

--jobs 1: Results: 149 total, 148 passed, 1 failed → FAIL reg-shift-extend.yaml[1]: Test failed with code 0x01; EXIT=1
--jobs 8: Results: 149 total, 148 passed, 1 failed → FAIL reg-shift-extend.yaml[1]: Test failed with code 0x01; EXIT=1
两 jobs FAIL 集合 diff: 空

还原：rd1: '0x08' → '0x07'
  md5 还原: 073f9fd7c742961283022aaf6a7501f3（byte-identical）
--jobs 8: Results: 149 total, 149 passed, 0 failed; EXIT=0
```
✅ 注入有效、FAIL 一致、还原 byte-identical、回绿确认。

**⑤ 确定性**
```
gate --jobs 8 连跑两次：
  第1次: 149 total, 149 passed, 0 failed; raw -v 输出 → raw-jobs8.txt
  第2次: 149 total, 149 passed, 0 failed; raw -v 输出 → 完全相同
  diff: 空
```

**⑥ 超时语义 / 边界**
```
--timeout 0 --jobs 1: Results: 149 total, 0 passed, 0 failed, 0 deferred, 149 errors; EXIT=1
--timeout 0 --jobs 8: Results: 149 total, 0 passed, 0 failed, 0 deferred, 149 errors; EXIT=1
逐用例 INCONCLUSIVE 集合 diff: 空（TIMEOUT_DIFF=0）

--jobs 0: Error: --jobs must be >= 1 (got 0); EXIT=2 ✅
JOBS=abc: Error: invalid JOBS value 'abc'; EXIT=2 ✅
```

**⑦ 无残留**
```
$ make check-no-residue
check-no-residue: PASS
EXIT=0

并行跑后 dadao-test-*.bin: 0 个; dadao-qmp-*.sock: 0 个
（注：本轮 dump 超时测试遗留1个 bin +1个 state.bin，已手动清理；非并行跑产生）
```

**⑧ 回归**
```
$ make check
EXIT=0, 22.30s
lit PASS: 26 of 26 (100%)
check-qemu-semantics: PASS (149/149)
repository checks: PASS
```

#### 约束核验

| 约束 | 判定 | 证据 |
|------|------|------|
| 只动 `run_qemu_test.py`、`Makefile`、`README.md` | ✅ | `git diff --name-only` 仅3文件；`tests/vectors/`、`.work/source/`、`components/` 零改动 |
| 不碰被编译组件源码 | ✅ | 无 rebuild 触发；`components/` diff=0 |
| 并行度只用 `JOBS`（默认8），禁 nproc | ✅ | Makefile: `JOBS ?= 8`；`--jobs $(JOBS)`；代码无 `nproc` 引用 |
| 失败/异常即停、禁自动重试 | ✅ | `run_single_test` 无重试逻辑；`sys.exit(2)` 对非法输入 |
| 不提交 git | ✅ | `git status` 显示 modified（unstaged），无 commit |
| 汇总格式与退出码语义不变 | ✅ | `Results:` 行格式不变；EXIT 0/1/2 语义不变 |

#### 解析缓存正确性分析（独立判定）

**1. 缓存键 `mtime_ns+size` 足够性**：
- 单次 `make check` 运行期内，向量文件是只读符号链接（`ln -sf` 指向 `tests/vectors/isa/*.yaml`，git tracked），不会被修改。
- `mtime_ns`（纳秒精度）+ `size` 组合在同一次运行内几乎不可能碰撞（需文件恰好被修改且新 mtime+size 完全相同）。
- 即使跨进程，每次 `make check` 是新进程、新缓存，无跨进程污染。
- **判定：✅ 安全**，对本用例足够。

**2. 缓存返回同一对象的并行安全性**：
- `_load_cases` 返回 `_VECTOR_CACHE[key]`（同一 list 对象）给所有线程。
- `build_binary()` → `build_blob(case, ...)` → `build_test_binary(vector_case)` 中：
  - `build_loader`、`build_test_section`、`build_exit_section` 均只**读取** `vector_case`（`.get()` / 下标读取）。
  - 唯二的修改路径（`build_branch_test_binary` L496、`build_call_ret_binary` L580）均先 `copy.deepcopy(vector_case)` 再操作。
- AST 分析确认：无对原始 `vector_case` 的就地修改。
- **判定：✅ 线程安全**，deepcopy 保护了缓存数据。

**3. 单文件模式一致性**：
- 单文件模式走 `run_single_test()` → `build_binary()` → `_load_cases()`，缓存同样生效。
- 与改动前行为一致：单文件模式不涉及并行，缓存只加速重复调用场景。
- **判定：✅ 一致**。

#### 反例注入有效性验证

- 注入前 `git diff --name-only tests/vectors/` = 0（未触碰真实向量）
- 注入在隔离副本 `/tmp/opencode/INFRA-030t-review/inject/` 进行
- 注入后 md5 变化确认（`073f9...` → `59b5f...`）
- 还原后 md5 回到 `073f9...`（byte-identical）
- `git status --porcelain tests/vectors/` = 0（真实仓库未被污染）

#### 对「重复解析是46s 主因」的独立判定

**结论：✅ 被证据支持。**

独立测量：149 次 `yaml.safe_load` 合计66.4s（445ms/次），而串行总耗时45.66s（工程师测量）或约66s（本机）。缓存后降至2.4s（工程师）或约3s（本机）。提升倍数 ≈19x，与「解析占99.6%」的 cProfile 结论一致。

因果链：
1. 无缓存 + thread8 ≈45s（GIL 绑定，零提速）→ 瓶颈确实是 Python 代码（非 QEMU 子进程）
2. 有缓存 + serial ≈2.4s → 消除解析后单线程已大幅提速
3. 有缓存 + thread8 ≈0.38s → 剩余工作（QEMU 子进程 wait）释放 GIL，线程生效

三条数据点构成完整因果证据链。

#### 判决

**Accepted**。

所有8条验收标准在独立重跑下全部通过；约束无违反；缓存正确性经源码分析+AST 验证确认线程安全；反例注入/还原完整闭环；「重复解析是主因」的结论被独立计时支持。

修改范围精准（3文件、140+/40- 行），实现简洁（缓存 + 线程池 + 有序聚合），无越界改动。


