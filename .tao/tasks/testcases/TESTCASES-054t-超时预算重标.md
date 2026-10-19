# TESTCASES-054t: `llvm-test-suite` 超时预算重标（`lua`/`XSBench`/`unix-smail`）—— 分开「真慢」与「空转」

**模块**：testcases
**项目里程碑**：M9
**依赖**：`QEMU-063t`（宿主信号/卡死根因批次，已收口；本册复核其遗留注记）、`TESTCASES-053t`（同模块改 `tools/testcases/**`，**串行**）、`TESTCASES-052t`（当前全量跑口径，`待验收`）
**状态**：待开始

> **编号（现场取号，2026-10-20）**：`testcases` 现存最大 = `TESTCASES-053t` ⇒ 取 **`054`**（编写前 `find .tao -name 'TESTCASES-054t*'` = 0 命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实（主会话 2026-10-20 实测，**不要重测**；本册只按此重标 + 补两档证据）

- **`lua`（`MultiSource/Applications/lua`）**：`--timeout 3600` 下实测 **1144.64 s 跑完 PASS**，`md5(stdout+stderr+exit)` = `6badfbeedd84d040f153876007407785` == `lua.reference_output` 正文（上游 `HASH_PROGRAM_OUTPUT 1`）⇒ 现有 `CASE_TIMEOUTS["MultiSource/Applications/lua"] = 840`（`tools/testcases/run_llvm_ts_user.py:308`）**偏小**。
- **`lua` 的 840 秒来历已过时**：`CASE_TIMEOUT_BASIS`（`:320-323`）写「670.52 s 时 qemu 宿主 SIGSEGV（静态档 `bench/process.lua`）+ 120 s ⇒ 840」，`QEMU_SIGNAL_ISSUES`（`:609-611`）也指 `QEMU-063t`；该崩溃属 **`QEMU-063t` 批次（已修）**，现测 1144.64 s **跑完且无宿主信号** ⇒ 注释与条目都过时。
- **`XSBench`（`MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench`）**：实测 **530.13 s 跑完 PASS**（stdout byte-exact vs `XSBench.reference_output`）⇒ **不在 `CASE_TIMEOUTS`**，吃 `DEFAULT_TIMEOUT = 300`（`:291`）⇒ 每次全量跑都误判 `blocked`（历史现场：`20261019T205339Z-llvm-ts-user-static/run.json` 记 `timeout after 300s`）。
- **对照 `mafft`**：实测 1452.82 s，表值 **1620**（`:310`）——这类是「**真慢**」，预算本来就对，**不要动**。
- **`unix-smail`（`MultiSource/Benchmarks/Prolangs-C/unix-smail`）**：`CASE_NOTES`（`:538-543`）与三处 `DEFAULT_TIMEOUT` 注释（`:229-230`、`:288-290`、`:303-305`）写「打印一行后卡死、归 `QEMU-063t`」，但最新全量跑里它 **`pass` 0.11 s**（stdout 35 B byte-exact、exit 0）⇒ 疑已随 `QEMU-063t` 修复，**须两档实测确认**。
- **成本口径（写进本册，供决策）**：重标后**每档**预计增加约 **14 分钟**（`lua` 840→1320 = +480 s = 8 min；`XSBench` 300→660 = +360 s = 6 min），换回 **2 个真 PASS**；原先 840 s 属**纯空转**（实测要 1144.64 s 才跑完），而「超时即 `blocked`」会把「能跑过」误报成「跑不过」。

## 接口规范

- **输入**：`tools/testcases/run_llvm_ts_user.py`（`CASE_TIMEOUTS` `:306-313`、`CASE_TIMEOUT_BASIS` `:316-333`、`CASE_NOTES` `:536-543`、`QEMU_SIGNAL_ISSUES` `:609-611`、`DEFAULT_TIMEOUT` 注释 `:229-230`/`:288-290`/`:303-305`）、`.dadao/tests/llvm-ts-user/**/run.json`（历史实测）、`.work/source/llvm-test-suite/**`（`reference_output`）、安装根工具链 + `qemu-dadao`。
- **输出**：
  1. `CASE_TIMEOUTS` 按公式重标：`value = ceil((实测 run_seconds + 120 s) / 60) * 60`（`lua` 1144.64 → **1320**；`XSBench` 530.13 → **660**）；`CASE_TIMEOUT_BASIS` 每条写**本次实测秒数 + 公式推导**，旧叙述删净。
  2. 过时注记清理：`QEMU_SIGNAL_ISSUES` 的 `lua` 条目、`CASE_TIMEOUT_BASIS["lua"]` 的 SIGSEGV 叙述、`CASE_NOTES[unix-smail]` 的卡死文案、三处 `DEFAULT_TIMEOUT` 注释（按第 3 条判据处置）。
  3. 两档实测证据（`--json-out` + `run.json` 路径）、证据脚本 `.work/evidence/<任务ID>/run.sh`、日志 `.work/log/testcases/TESTCASES-054t-*.log`。
- **约束**：**不改** `spec/` / `contracts/` / `.tao/contracts/**` / `tests/vectors/**`；**不改**用例分类判据（`pass`/`fail`/`blocked`/`excluded` 语义）、**不放宽**任何 oracle/断言；不 commit/push。

## 验收标准

1. **两档实测**（`--link-mode both`、`--timeout 3600`、`--only` 单例、`--json-out` 必填）：`lua` / `XSBench` / `unix-smail` **各自两档**给出 PASS（md5 或 byte-exact oracle 命中）**或**崩溃/挂死证据（rc / 宿主信号 / 日志 / `run.json`）；**单档结论不得冒充两档**。
2. **表值重标**：`CASE_TIMEOUTS` 的 `lua` / `XSBench` 值 = 按公式现场复算的结果（实测有变则以实测为准，须写明推导）；`CASE_TIMEOUT_BASIS` 的秒数能与 `run.json` 的 `run_seconds` 对账；`mafft`/`lemon`/`SimpleMOC`/`nbench` 四条**不动**（对照）。
3. **过时注记清理（逐条给判据）**：
   - `QEMU_SIGNAL_ISSUES[".../lua"]`：本次两档实测**无**宿主信号终止 ⇒ **删**；若复现 ⇒ 保留并附证据（照实写）。
   - `CASE_TIMEOUT_BASIS[".../lua"]`：改成本次实测秒数 + 公式，**删** SIGSEGV/`QEMU-063t` 叙述。
   - `unix-smail`：两档 PASS ⇒ 删 `CASE_NOTES` 卡死段 + 改三处 `DEFAULT_TIMEOUT` 注释口径（**不入表**：0.11 s ≪ 300 s）；若仍卡死 ⇒ 保留文案 + 附本次两档实测证据（不得只凭旧结论保留）。
4. **不许把真实失败改成 pass（硬判据）**：新增/保留的 `pass` 必须 oracle 命中（`pass_reference`）；`pass_exit_only` 计数**不增**；禁删断言、禁放宽阈值、禁把 `blocked` 改标 `pass`。
5. **可达 FAIL ≥ 2**（真实输出 + `cp` + md5 还原后回绿）：
   - (a) 临时把 `lua` 表值改回 **840** ⇒ 该例 `blocked`（`timeout after 840s`）——证明表值是**有效**预算而非装饰；
   - (b) 临时删掉 `XSBench` 表项 ⇒ `timeout after 300s` 红；
   - (c) 把 `CASE_NOTES[unix-smail]` 旧文案恢复 + 一条「无 stale 卡死注记」的文本断言 ⇒ 红（若本册采用该断言）。
6. **结论可判**：逐例明确回答「**给更多时间是能跑过、还是跑不过**」，附实测秒数与 oracle 结果；不得以「加超时」掩盖真实失败（若某档确实跑不过，照实给证据，**不许**靠调大预算改判）。
7. **门控**：`make check`(L1) rc=0（含 `check-run-artifacts` / `check-tasks` / `check-knowledge-refs` / `check-no-residue`）；**不跑** L2/L3 全量（本册只改驱动预算与注释）。
8. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` 按实况回填（`ISS-266` 的 `lua` 实例是否不复现、`unix-smail` 卡死面是否闭合），**不擅自**关 issue。
9. **不跑** `git commit`/`push`；越界改动须披露。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/TESTCASES-054t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. **长跑**：单例 `lua` 约 19 min/档、`XSBench` 约 9 min/档 ⇒ 先申报耗时、`setsid nohup` 落 `XXX_EXIT=$rc`，**不在会话内空等**；一次只跑一个、`JOBS ≤ 8`。
6. 复杂命令输出留 `.work/log/testcases/`；运行产物按 `docs/Process-08`（`--json-out` 必填、命名规矩）。
7. 失败保留现场并继续推进；只在需用户语义裁定（如两档结论冲突、是否接受某例「跑不过」）时留问。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

#### 提交记录（architect，2026-10-20）
- 档位：`待开始`（立册，按主会话指令正常提交）
- 提交：`f261fef`（同上分支）⇒ `master` squash `84a5231`
- 文件集对账：2 文件 = 本册（新建）+ `milestones.md`（流水行 + 未完成块）；号唯一（`find .tao -name 'TESTCASES-054t*'` 立册前 0 命中）
