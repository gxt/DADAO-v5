# TESTCASES-053t: 陈旧证据脚本族按新规重建（`ISS-270`/`ISS-273`/`ISS-282`/`ISS-288`）

**模块**：testcases
**项目里程碑**：M9
**依赖**：`INFRA-093t`（运行产物/日志规矩 + `check-run-artifacts`，已验证）、`TESTCASES-052t`（libc-test 驱动现状，`待验收`）、`LLVM-117t`（最新工具链，`待验收`）、`INFRA-098t`（安装根 `llvm-nm`/`llvm-readelf`；本册可能需要它们取证，**按现状用构建树工具并披露**）
**状态**：待开始

> **编号（现场取号，2026-10-20）**：`testcases` 现存最大 = `TESTCASES-052t` ⇒ 取 **`053`**（编写前 `grep -rn 'TESTCASES-053' .tao/` 零命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实（四条，逐条带 `file:line`）

- **`ISS-270`（驱动文案 stale）**：`tools/testcases/run_libc_test_user_suite.py:374-377` 的 `CASE_NOTES["functional/setjmp"]` 仍写「declared port gap -- sigsetjmp is not implemented」；`:1210` 在 `attribute_port_gaps()` 中**无条件** append `CASE_NOTES`（`pass` 也照打）⇒ `INFRA-089t` 已实现 `sigsetjmp` 后仍打印旧根因，与真实状态矛盾。
- **`ISS-273`（`LLVM-098t` 证据脚本过时）**：`.work/evidence/LLVM-098t/run.sh:176` 的 S9 静态基线（取自 `.work/evidence/INFRA-085t/baseline`）与 `:186-234` 的 S10「XFAIL：`libc.so` 链接必须失败（22 errors = 6 ABS48 + 16 undefined）」已被现工具链推翻（`LLVM-117t` 现场 `make build-musl-shared` rc=0）⇒ 期望与实际反向，脚本 default 5 FAIL / 注入段亦受影响。
- **`ISS-282`（`INFRA-093t` 验收三项遗留）**：① 子集跑（`--filter`）写 `authoritative/` 只有文档约束（`docs/Process-08 §1.2`「由调用者负责选择」）；② `tools/infra/check_run_artifacts.py:162-185` 的 `_meta_problems()` 只校验 `command`/`started_utc`/`toolchain.{clang,qemu,libc}`，**不校验 `finished_utc`**（文档 `§1.1` 要求）；③ `:57-60` 的 `INFLIGHT_LEGACY`（`^llvm-ts-user-.*`）过渡豁免须在 `.work/log/testcases/` 搬迁完成后删除——**搬迁未做**（`ISS-278`「另起一笔」）。
- **`ISS-288`（`LLVM-111t` 基线随 `Align(16)` 失效）**：`.work/evidence/LLVM-111t/run.sh:147` 把 `$BASE/P3.s` 列为前提、`:167-168` 断言 `P3-asm-identical`，而现 `.work/evidence/LLVM-111t/baseline/` **只有 `P3.out`**（`P3.s` 已不存在）⇒ 前提即缺；`ISS-288` 记录的差异 = `Align(16)` 后帧大小 `-24→-32` 等**合法**变化，P3 stdout 语义一致（`cmp` rc=0）。
- **共同性质**：四者均为**历史证据脚本/文案随世界变化而 stale**，**非产品缺陷**；判据口径 = `docs/Process-08`（运行产物三件套 / 命名 / 权威跑）+ `AGENTS.md`「验证脚本反例门控」（**必须能失败**；禁恒真、禁「两支写同一结果」）。

## 接口规范

- **输入**：`tools/testcases/run_libc_test_user_suite.py`（`:374-377`、`:1197-1212`）、`tools/infra/check_run_artifacts.py`（`:57-60`、`:162-185`、`:208+`）、`docs/Process-08`、`.work/evidence/{LLVM-098t,LLVM-111t}/**`（**不入 git**）、现有 `.work/log/testcases/**` 存量。
- **输出**（逐条，**修 / 按新规重建 / 有据登记** 三选一，**不得放宽**）：
  1. `ISS-270`：驱动 note 改为「已由 `INFRA-089t` 实现（`src/signal/dadao/sigsetjmp.s`）」或删除；且 `pass` 不再带 port-gap note（顺序/条件修）；
  2. `ISS-273`：S10 期望改「`libc.so` rc=0 且产物非空」+ **保留可达 FAIL**（注入 `-fno-pic`/损坏对象 ⇒ 红）；S9 基线按**当前**工具链刷新（同源同名口径）或改语义断言 + 注入；
  3. `ISS-282①`：驱动在 `--filter`/`--only`/`--limit` 与 `--work-dir` 指向 `authoritative/` 同时出现时**显式拒绝**（rc≠0 + 提示）；② `_meta_problems()` 增 `finished_utc` 非空校验 + `--self-test` 新注入；③ 搬迁未做 ⇒ **不删**豁免，给「搬迁完成后删除」的机械判据与登记（不得借此放宽其它断言）；
  4. `ISS-288`：`baseline/P3.s` 按当前工具链重生成（或明确改为语义断言）；**不得**只删 `P3-asm-identical`；`P3-stdout-identical` 保留为语义 oracle；
  5. 证据脚本（本册自证）`.work/evidence/<任务ID>/run.sh` + 日志 `.work/log/testcases/TESTCASES-053t-*.log`。
- **约束**：**不改** `spec/` / `contracts/` / `.tao/contracts/**` / `tests/vectors/**`；不改用例分类（`pass`/`fail`/`blocked` 语义）；`.work/evidence/**` 不入 git ⇒ 可提交面 = 驱动/门控/文档 + 台账；不 commit/push。

## 验收标准

1. **四条逐条闭合**：每条给出「处置 + 依据 + 修前/修后真实输出」；`ISS-270/273/288` 的脚本 default **0 FAIL**；`ISS-282` 的 ①② 已实现（③ 有机械登记）。
2. **不许放宽（硬判据）**：每条被替换/更新的断言都必须**保留一条可达 FAIL 路径**（注入 → 红 → 还原 → 绿），并给出**真实**输出；仅删断言 / 改期望迎合现状（如把 XFAIL 改成「忽略」）⇒ 判 FAIL；`check-run-artifacts --self-test` 全绿且**新增注入各可达 FAIL**。
3. **`ISS-270` 语义**：`functional/setjmp` 单例跑（`--filter` + `--json-out` 落 `/tmp`）⇒ 报告中不含旧根因 note；把 `CASE_NOTES` 临时改回旧文案（`cp` 备份）⇒ 断言红；还原后绿。
4. **`ISS-282①` 机械判**：`--filter` + `--work-dir .work/tests/authoritative/...` ⇒ 驱动 **rc≠0** 且不创建运行目录；正常 `--filter` + `/tmp` work-dir ⇒ rc=0；去掉 guard（临时树）⇒ 组合跑 rc=0（证明断言可失败）。
5. **`ISS-282②` 机械判**：构造一个缺 `finished_utc` 的 `meta.json`（临时树）⇒ `check-run-artifacts` 红；补齐 ⇒ 绿；`--self-test` 覆盖该注入。
6. **`ISS-273`/`ISS-288` 基线口径**：刷新后的基线必须与「同源同参数重跑」逐字节一致（脚本内可重生成校验），并用一次注入证明能失败（如 `-O0`/`-fno-pic`/改源 ⇒ 红）。
7. **证据组织**：本册运行产物遵循 `docs/Process-08`（`.work/tests/**` 三件套、日志命名 `check-*.log` / `<任务号>-<用途>.log`、`--json-out` 必填）；`make check-run-artifacts` rc=0。
8. **门控**：`make check`(L1) rc=0；`check-tasks` / `check-knowledge-refs` / `check-no-residue` rc=0；不跑 L2/L3 全量（本册不改语义实现；单例跑属证据）。
9. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml`：`ISS-270`/`ISS-273`/`ISS-288` 与 `ISS-282` 的 ①② 按实况回填（`closed` 或「保留 open + 剩余项」；③ 保持 open 并注记搬迁前置）。
10. **不跑** `git commit`/`push`；越界改动须披露。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/TESTCASES-053t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账；`.work/evidence/**` 亦遵守）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（是否接受某证据脚本「有据登记、不修」；是否启动 `.work/log/testcases/` 搬迁）时留问。
6. 复杂命令输出留 `.work/log/testcases/`；单例跑用 `--filter` + 显式 `--json-out`。

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
