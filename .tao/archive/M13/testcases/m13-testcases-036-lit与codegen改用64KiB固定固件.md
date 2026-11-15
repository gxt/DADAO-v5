# m13-testcases-036: lit E2E 与 codegen E2E 改用 64 KiB 固定固件（去 legacy trampoline）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-qemu-011`（`-bios` 只收 64 KiB 固定固件，已合入/待合入）
**可并行分片**：否（同一批测试入口）
**预估**：1–2 h
**状态**：已验证

## 背景（2026-11-14 实测）

- `m13-qemu-011` 把 Tiny 的 `-bios` 收紧为「必须恰好 64 KiB，与 `bootrom-image` 同一固定固件」（`spec/Machine-v5 §6`；用户 2026-11-13 裁定），并删掉 Tiny 的 flat trampoline 旁路。
- 但两条 E2E 通路仍在用旧的 56 B `tools/testcases/lib/trampoline.bin` 当 `-bios`：
  - `tests/unit/llvm/e2e/lit/` 的 **5 个**测试（`smoke_add`/`smoke_arith`/`smoke_fp`/`smoke_jump`/`tool_env`）用 `-bios %trampoline -kernel %t.raw`（live count 现场核）；
  - `tools/testcases/unit/run_codegen_e2e.py` 用 `--trampoline` 默认 `tools/testcases/lib/trampoline.bin` 作 `-bios`（L100/L329）。
- 后果（现场）：`make check-lit` 4 FAIL、`make test-codegen` 19/19 FAIL，QEMU 报 `-bios … is 56 bytes; the Machine-v5-Tiny -bios path accepts only the fixed 65536-byte BootROM firmware`。
- 注意：安装根里的 qemu 已被刷新为含该收紧的版本（事故记录见 `ISS-373` 复核），这不是「安装根坏了」，而是**测试侧落后于 spec**。

## 目标

1. **lit E2E**：`%trampoline` 不再用于 `-bios`；改用已在 `lit.cfg.py` 里定义的 `%bootrom`（`bootrom/tiny/bootrom_tiny.bin`，64 KiB）。`-kernel %t.raw` 的 raw 应用路径**保留**（`-bios` 固定固件 + raw `-kernel` 仍是契约路径）。`tool_env.test` 的存在性检查同样改成 `%bootrom`。
2. **codegen E2E**：`run_codegen_e2e.py` 的 `-bios` 改用固定固件（`tools/testcases/lib/` 或 `dadao_paths` 的 bootrom 路径，**复用既有解析方式**，不要新造第二套）；`--trampoline` 参数与 `trampoline.bin` 依赖删除或改名（若外部脚本引用，保留兼容别名并在帮助里标注 deprecated）。
3. **`gen_trampoline.py` 的处置**：其「把 hmon 向量指到不可达地址」的第 0 步属 legacy 口径（`m13-testcases-034` 已迁 oracle）。本任务**只**处理测试入口改用固定固件；`gen_trampoline.py` 是否整体退役留给 `m13-testcases-030`，请在完成区写明边界。

## 验收（逐条给真实 rc）

1. `make check-lit` **rc=0**（现场例数；若仍有非本任务红，逐条归因并证明与本任务无关）。
2. `make test-codegen`（或 `check-unit` 中对应目标）**rc=0**，例数现场统计（原 19）。
3. **不得用「放宽 qemu」或「改安装根」凑绿**：`-bios` 仍必须是 64 KiB；核 QEMU 源码未改（`git diff` 无 `components/qemu/**`）。
4. 反例可达：把某个 lit 测试的 `%bootrom` 改回 `%trampoline` ⇒ 该例应红（贴注入→FAIL→还原→回绿，`cp`+md5）。
5. `check-lit-full` 不在本任务范围（opt-in）；`check-tests-index`/`check-case-ledger`/`check-no-residue` 不变。
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host` / `check-modules` / 真 `build-*`**（`check-lit`/`test-codegen` 依赖安装根里已有的二进制，直接跑即可；若缺 bootrom 用 `make build-bootrom`——该目标只产镜像、不装）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `tests/unit/llvm/e2e/lit/**`、`tools/testcases/unit/run_codegen_e2e.py`、必要时 `tools/testcases/lib/**`（bootrom 路径解析复用）；**不改** `spec/`、`contracts/`、`components/**`、`tests/inst/**`。
5. 大文件落**运行期临时目录**并测完即删。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 固件存在性检查放在 `--build-only` 之前 ⇒ 不需要 QEMU 的构建-only 路径被固件缺失拦住（原 trampoline 检查同样无差别继承） | ✅已修 | `run_codegen_e2e.py`：把 `bootrom` 存在性检查移入 `not args.build_only` 分支（与 qemu 检查同级） | `--build-only` rc=0、19/19；缺固件仍 rc=2（非 build-only） |
| F2 证据脚本 `--inject` 子进程开头 `rm -rf $OUT` 删掉父进程正在重定向的 inject.log ⇒ 「inject 失败」假红 | ✅已修 | 证据脚本：`--inject` 用独立 scratch 目录 | 重跑 9/9 INJECT ALL GREEN、父进程 32/32 |
| F3 I2 注入用非 `-v` lit 输出 ⇒ 证据日志无 64 KiB 规则报文，无法证明红的原因是尺寸规则 | ✅已修 | I1/I2 的 lit 调用全部加 `-v` | 日志含 `is 56 bytes; … accepts only the fixed 65536-byte BootROM firmware` |
| F4 删 `%trampoline` 替换后，`tool_env.test` 头部「每个替换一条 RUN」是否仍成立 | ❌不修（已满足） | 现场统计：`config.substitutions.append` 12 个 = `tool_env.test` 的 12 条 RUN | 12/12 |
| F5 `Makefile` 的 codegen recipe 仍传 `--trampoline tools/testcases/lib/trampoline.bin`（Makefile 不在本任务可改范围） | ⏸延后（归 030） | `--trampoline` 保留为 deprecated 空转（help 标注 + stderr NOTE），实际不再参与 `-bios` | codegen 19/19 rc=0；日志首行出现 deprecated NOTE |

**自审判决**：F1–F3 已修并复验，F4 无需改，F5 已在「遗留问题」登记边界；无未修 finding ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14）

**预检**：`make check-disk` rc=0（used 5%）、`free -g` available 119 GiB、无在跑构建、gate.lock 空闲；**未手写 `-j`**（codegen 为脚本内顺序 `for prog in programs`，llvm-lit 未传 `-j`，构建侧 `JOBS` 未触发）；未跑 `install-host`/`check-modules`/工具链 `build-*`（仅 check-lit 自带 `build-bootrom` 前置，任务书允许）。

**重跑（我的真实输出 + 退出码）**
- `make check-lit` → **rc=0**（墙钟 3 s）：`Total Discovered Tests: 176`、`Passed: 176 (100.00%)`、`^FAIL:` 0 行、5 个目标测试全 PASS。
- `make -o install-host _locked-test-codegen` → **rc=0**（9 s）：`Results: 19/19 passed, 0 failed`、`test-codegen: PASS`；完整日志首行 `NOTE: --trampoline is deprecated and ignored…`（recipe 仍传该参仍绿 ⇒ 确为空转）。
- 门控 4 条 → **rc=0**：`check-tests-index` PASS（489 条）/ `check-case-ledger` PASS / `check-no-residue` PASS / `check-knowledge-refs` PASS（0 具体引用）。
- **一键证据脚本 → rc=1（25 s）：`RESULT: 30/32 checks passed`、`FAILED: 2`** ⇒ 见「阻断」。

**改法核**（`git show --stat 27771183` = 8 文件）：5 个 lit `-bios %trampoline`→`%bootrom`（`-kernel %t.raw` 保留）✅；`tool_env.test` `ls %trampoline`→`ls %bootrom` ✅；`lit.cfg.py` 删 `%trampoline` 替换（现 12 替换 = tool_env 12 条 RUN）✅；`run_codegen_e2e.py` `DEFAULT_BOOTROM` 走 `tools/infra/paths.py`、新增 `--bootrom`、`--trampoline` deprecated 空转（help + stderr NOTE）✅。

**qemu 未改（独立实测）**：`git diff --stat 8cfe1fcd HEAD -- components/` 空、`git show --stat --format= HEAD -- components/` 空（8cfe1fcd = merge-base）；raw 直跑：56 B `-bios` ⇒ **rc=1** + 报文 `…is 56 bytes; …accepts only the fixed 65536-byte BootROM firmware…`；64 KiB 固件 + raw `-kernel` ⇒ **rc=0**。

**独立注入（cp+md5，自设计路径，非工程师 I1/I2）**：`DEFAULT_BOOTROM`→`trampoline.bin` ⇒ codegen **rc=2、`Results: 0/19 passed, 19 failed`**（writer-guard 显示 bios 已换成 trampoline），直跑脚本 rc=1、19 例 `exit=1`；还原后 md5 `c4011b48…` 与注入前逐项一致 ⇒ **回绿 rc=0、19/19**。

**`%trampoline` 残留**：`grep -rn "%trampoline" tests/` 空（rc=1）、`lit.cfg.py` 不再定义；全仓残留只在 `.tao/archive/**`（历史归档）+ 本任务书；`tools/testcases/lib/**`、`riscv_tests/**`、`parity/**`、`Makefile` 写的是 `trampoline.bin`/`--trampoline`，不产生 lit 未定义替换。

**越界/对账**：未触碰 `Makefile`/`components/**`/`tests/inst/**`/`spec/`/`.tao/knowledge/`；reviewer 注入/还原后 `git status -uall` 与 `27771183` 逐项一致、3 个被测文件 md5 与快照相同（本条审阅记录是 reviewer 追加的唯一改动，未提交）；完成区 16 行 ≤30；`**状态**` 仍 `待验收`（主会话改）。

**阻断（Needs Revision）**：证据脚本重跑 rc=1，红在 §4 两条 `*-diff-vs-master`——它们断言「`git diff --stat master -- components/` 为空」，但 `master` 在工程师提交（16:52）后于 **16:56 合入 `85b3c1f8 m13-qemu-011`（本任务依赖）**，断言测的其实是「分支是否落后 master」而非「本任务是否动了 qemu」，属未钉基线的裸 `git diff`（AGENTS 明令禁止）。
**给 engineer 的修改**：§4 改为 `BASE=$(git merge-base master HEAD); git diff --stat $BASE HEAD -- components/`（期望空）+ `git show --stat --format= HEAD -- components/`（期望空）；完成区验收 3 的「`git diff --stat master -- components/` 均空」改为「相对 merge-base `8cfe1fcd` 无 `components/` 改动」；改后重跑应 **32/32 rc=0**。
**非编造佐证**：`git diff --stat 8cfe1fcd 851ee5d7 -- components/` 空（工程师 16:50 首跑时 master tip = `851ee5d7`），当时确绿；但脚本本身不合格仍须返工。**披露**：该脚本自带 `rm -rf` 输出目录，我的重跑覆盖了工程师原始日志，故其原件未再逐条比对（`.work` 下脚本 md5 `59a95a95…` 未变，reviewer 侧已备份）。

**非阻断 finding（doc 级 → architect/030 收尾改）**：① `Makefile:1625/1653/1674` 注释与 `--trampoline` 传参仍写 trampoline——**同意归 `m13-testcases-030`**（Makefile 不在本任务可改范围，该参已无害、实测绿）；② 任务书硬约束 §5 含具体临时目录路径，建议改「运行期临时目录」措辞。

**未决**：无待用户裁定项。

### 第 2 轮 reviewer 验收（2026-11-14）

**环境预检**：`make check-disk` rc=0（used 2%）、available 118 GiB、nproc=64、无在跑构建；未手写 `-j`；未跑 `install-host`/`check-modules`。

**重跑（我的真实 rc / 输出）**
- 一键证据脚本 → **rc=0**（27 s）：`BASE (merge-base master HEAD) = 8cfe1fcd`、`RESULT: 32/32 checks passed`、`ALL GREEN`；§4 `components.clean-vs-base` 与 `components.clean-in-this-commit` 均 expect= actual= rc=0。
- 同脚本 `--inject` → **rc=0**（1 s）：`INJECT RESULT: 13/13`、`INJECT ALL GREEN`（I1×4、I2×5、I3×4；`I3.good-base-clean` 空/空、`I3.bad-base-dirty` dirty/dirty）。
- `make check-lit` → **rc=0**（3 s）：`Total Discovered Tests: 176`、`Passed: 176 (100.00%)`。
- `make -o install-host _locked-test-codegen` → **rc=0**（10 s）：`Results: 19/19 passed, 0 failed`、`test-codegen: PASS`。
- 门控 4 条 → **rc=0**：`check-tests-index` **489** / `check-case-ledger` PASS / `check-no-residue` PASS / `check-knowledge-refs` PASS（0 具体引用）。

**§4 可达 FAIL、非恒真（两路自构造，不依赖其 I3）**
- 路① `EVIDENCE_BASE=85b3c1f8`（master 上改过 `components/qemu` 的提交）→ **rc=1**、`RESULT: 31/32`、`FAILED: 1`，`BASE … = 85b3c1f8 [EVIDENCE_BASE override]`；**只有** `components.clean-vs-base` 红（actual 非空），`clean-in-this-commit` 仍 rc=0 ⇒ 断言可被精确打红。
- 路② `EVIDENCE_BASE=deadbeefno` → **rc=2**，`ERROR: cannot resolve the branch base …='deadbeefno'`，**无 `ALL GREEN`/`RESULT` 行** ⇒ 不可解析不会变绿（上轮「stdout 空即 clean」的假绿点已堵）。
- 补充：其 I3 现场派生的 `BADBASE=17c783d9` 下 `git diff --stat $BADBASE HEAD -- components/` 非空（3 文件）；`clean-in-this-commit` 所用 `git show --stat --format= <rev> -- components/` 在 `85b3c1f8` 上非空 ⇒ 该形态非恒真（其 FAIL 路径需 HEAD 触碰 `components/`，reviewer 无提交权故未直接触发，由「本提交零改动」佐证）。

**实现零改动**：`git diff --name-only 27771183 HEAD` 仅任务书；`git diff --stat 27771183 HEAD -- tests/ tools/` **空**；`git status -uall` 干净。证据脚本不在 git（`.work` 为符号链接且被忽略），只能靠 md5 追溯：`59a95a95…` → `3ed08687…`（17:19）。

**完成区核**：验收 3 已改「相对 merge-base `8cfe1fcd`」口径，与 §4 断言一致（我实跑打印同值）；完成区 **18 行 ≤30**；任务书无具体运行期路径（无 `.work` 引用、无宿主绝对路径、无临时目录）；**第 1 轮审阅记录原样保留**。

**上轮唯一阻断解除**：脚本 32/32 rc=0、`--inject` 13/13 rc=0、两路反例分别 rc=1（31/32）与 rc=2。

**非阻断 finding（沿用第 1 轮，doc 级 → architect/030 收尾改）**：① `Makefile:1625/1653/1674` 注释与 `--trampoline` 传参仍写 trampoline ⇒ 归 `m13-testcases-030`（同意工程师边界主张）；② 证据脚本经 `.work` 符号链接落在共享 `.work`，git 不可 diff，只能靠 md5 追溯（现状如此，非本任务引入）。

**判定：Accepted**（工程师达标；架构师仍终审）。**未决**：无待用户裁定项。

## 完成区

**测试结果**：证据脚本 32/32 检查通过（rc=0）；`make check-lit` rc=0（现场 176 discovered / 176 passed）；codegen E2E 目标 rc=0（现场 19/19）；`check-tests-index` rc=0（489 条）、`check-case-ledger` rc=0（2184 条）、`check-no-residue` rc=0、`check-knowledge-refs` rc=0（0 具体引用）。
**修改文件**：
- `tests/unit/llvm/e2e/lit/{smoke_add,smoke_arith,smoke_fp,smoke_jump}.test`：`-bios %trampoline` → `-bios %bootrom`（`-kernel %t.raw` 保留）
- `tests/unit/llvm/e2e/lit/tool_env.test`：存在性检查 `ls %trampoline` → `ls %bootrom`
- `tests/unit/llvm/e2e/lit/lit.cfg.py`：删掉已无引用的 `%trampoline` 替换（现场 12 个替换 = tool_env 的 12 条 RUN），注释改指固定固件
- `tools/testcases/unit/run_codegen_e2e.py`：`DEFAULT_TRAMPOLINE` → `DEFAULT_BOOTROM`（复用 `tools/infra/paths.py` 的 test-artifacts 解析，与 `%bootrom` 同源）；`-bios` 用固件；新增 `--bootrom`；`--trampoline` 保留为 deprecated 空转（help 标注 + stderr NOTE）；缺固件 ⇒ rc=2 并提示 `make build-bootrom`；读方护栏把固件纳入 md5 快照（组件 `bootrom`）
**验收结果**：
1. `make check-lit` rc=0：现场 176 discovered / 176 passed（5 个目标测试逐条 `PASS`）。
2. codegen 目标 rc=0：以 `make -o install-host _locked-test-codegen` 跑**同一 recipe**——其 `install-host` 前置是 phony、必然重建工具链+QEMU（本任务禁跑），故抑制该前置；recipe 未改。现场 19/19。
3. qemu 未改：相对 merge-base `8cfe1fcd` 无 `components/` 改动（`$BASE..HEAD` stat 与本提交 `git show --stat HEAD` 两条断言均空；`$BASE=git merge-base master HEAD`，脚本现场打印短哈希）。`-bios` 仍只收 64 KiB：56 B trampoline 直跑 ⇒ rc=1 + `accepts only the fixed 65536-byte BootROM firmware`；64 KiB 固件 + raw `-kernel` ⇒ rc=0。
4. 反例可达（`cp` 备份 + md5，未用 git 还原）：`smoke_add.test` 的 `%bootrom`→`%trampoline` ⇒ 该例红（rc≠0）；再注入 56 B 固件绝对路径 ⇒ 红且报文为 64 KiB 尺寸规则；还原后 md5 一致 ⇒ 回绿。注入/还原 9/9 符合预期。
5. `check-lit-full` 未跑（opt-in，验收 §5 明确不在范围）；四条静态门控均 PASS。
**新发现/坑**：① `_locked-test-codegen: install-host` 是真前置（phony ⇒ 必重建工具链+QEMU），验收须用 `-o install-host` 抑制，直接 `make test-codegen` 会触发 install-host。② lit 对未知 `%xxx` 不报「未知替换」而是原样透传（`%trampoline` 展开成 `…tmprampoline`），所以「删替换」后的误用只表现为「文件不存在」，不是「规则拒绝」。③ 读方护栏纳入固件后，`make build-bootrom` 与 codegen 跑批并发会被 rc=75 拒绝（预期，勿加 `--allow-concurrent`）。
**遗留问题**：
- **边界（归 `m13-testcases-030`，本任务未动）**：`trampoline.bin` 本体、`gen_trampoline.py`、`lib/run_qemu_test.py`、`lib/verify_harness_dump.py`、`lib/test_harness_exit_path.py`、`riscv_tests/run_riscv_tests.py`、`parity/run_parity.py` + `parity/README.md` 仍引用它；`Makefile` 的 codegen recipe 仍传 `--trampoline …/trampoline.bin`（现为 deprecated 空转，建议 030 一并删）、同处注释仍写 `-bios trampoline.bin`（本任务可改范围外）。
- 未跑 `check-lit-full`（opt-in）。

**返工（reviewer 第 1 轮）**：证据脚本 §4 两条断言改钉 merge-base（`BASE=git merge-base master HEAD`，现场打印短哈希 `8cfe1fcd`；`EVIDENCE_BASE` 仅为可达-FAIL 自检钩子）+ 本提交 `git show --stat HEAD -- components/`；重跑 `run.sh` **32/32 rc=0**（§4 两条均空）、`run.sh --inject` **rc=0（13/13 符合）**；反向 `EVIDENCE_BASE=<最新 components 提交的父提交，运行时由 git log 现场派生>` ⇒ `components.clean-vs-base` 红、**31/32 rc=1**（另加 I3 自检 4 项，未改任何仓库文件）。
**返工（reviewer 第 1 轮）2/2**：完成区验收 3 改 merge-base 口径（事实订正，非放宽）+ 硬约束 §5 具体临时目录改「运行期临时目录」；`tests/unit/llvm/e2e/lit/**` 与 `run_codegen_e2e.py` 语义零改动（本轮只改证据脚本与任务书）；审阅记录未动。

