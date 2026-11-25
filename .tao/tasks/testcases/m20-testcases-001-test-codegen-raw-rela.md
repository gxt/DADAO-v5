# m20-testcases-001: 修复 `test-codegen` raw 单 TU 的未解析 RELA（ISS-509）

**模块**：testcases
**项目里程碑**：M20
**依赖**：无（`m14-llvm-007` 的「同节 global 仍发重定位」行为已合入）
**可并行分片**：否（单驱动脚本 + 单门控）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待验收

## 背景（M20 分诊，2026-11-25）

`ISS-509` 记录 `check-unit` 的 `test-codegen` 基线红：raw single-TU 组装 19/19 报
`SHT_RELA present`，`Results: 0/19 passed`。本次现场复核仍复现：

- 用当前工具链跑驱动脚本的 `--build-only`，19 例全部失败，理由均为
  `raw single-TU object is not fully resolved: SHT_RELA present`。
- 根因不在 QEMU，也不在 LLVM 语义：`llc` 输出的程序带 `.globl main`，
  `llvm-mc` 对同节 global 符号仍发 `R_DADAO_REL26`（`m14-llvm-007` 有意保留
  该重定位，供链接器使用）；而 raw 管线把 crt0 与程序拼成一个 TU，没有链接器，
  `llvm-objcopy` 不会施加重定位。
- 受控验证：把 raw 合并文本里的 `.globl main` 改为 `.local main` 后重汇编，
  `llvm-readelf -r` 输出 `There are no relocations in this file`。

## 目标

1. raw 管线在**只改测试驱动**的前提下，让 crt0 对 `main` 的调用在汇编期解析：
   合并文本中程序侧 `main` 必须按 TU 内局部符号处理（`m14-llvm-007` 的 global
   重定位行为不得改）。
2. 19/19 用例在 QEMU Tiny 上按 `expected.yaml` 的退出码通过；不得删除或放宽
   「raw 对象必须无 RELA」断言。
3. 不改变 linked-ELF 管线（`test-elf`）与既有多 TU 语义。

## 验收（逐条贴真实 rc）

1. `run_codegen_e2e.py --build-only`：19/19 通过、0 条 `SHT_RELA present`。
2. 完整 `test-codegen`（或 Makefile 目标的等价命令）：19/19 pass，退出码 0；
   若当前有在途 QEMU 任务占用 `install-host` 窗口，允许用 `make -n test-codegen`
   解析工具路径后直跑同一驱动，并在完成区写明未跑 `make` 目标的原因。
3. **可达 FAIL**：把本次「局部化 `main`」改动还原为原始 `.globl main` ⇒
   build-only 回 0/19（`SHT_RELA present`）；`cp` + md5 还原后回 19/19。
4. `check-inst-asm`、`check-tests-index` 真 rc；`check-patch-tree` 只要求
   **llvm/testcases 未被本任务改坏**，总 rc 受在途 qemu/musl 漂移影响时按分段披露。
5. 完成区记录实际工具 md5（`llc`/`llvm-mc`/`llvm-objcopy`）与 QEMU md5，证明
   验的是同一批二进制。

## 约束

独立 `git worktree`（分支 = `m20-testcases-001`）；不提交 git；只改
`tools/testcases/unit/run_codegen_e2e.py`（必要的最小范围）与本任务书；不改
`components/**`、`spec/`、契约、`Makefile`；不新增运行期文档。任务书不写
构建树/安装树/临时目录的具体路径，证据统一落在「运行期证据目录内的 `run.sh`」。

## 完成区

**测试结果**：运行期证据脚本 7/7 PASS（rc=0）。修复前 `--build-only`：rc=1、`Results: 0/19`、19 条 `SHT_RELA present`；修复后：rc=0、`Results: 19/19`、0 条；完整 QEMU：rc=0、19/19（逐例 `actual == expected`）；驱动 `--inject` 自检：rc=0（`INJECT: PASS`）。
**修改文件**：`tools/testcases/unit/run_codegen_e2e.py`（+47/−4，新增 `_localize_defined_globals`）；本任务书。运行期证据在运行期证据目录内 `run.sh`（含 logs/，不入库）。
**验收结果**：
1. build-only：rc=0，`Results: 19/19 passed, 0 failed`，`SHT_RELA present` 0 条（例数现场取自 `expected.yaml`，未写死）。
2. 完整 QEMU Tiny：rc=0，19/19 PASS。未跑 `make test-codegen`：按任务书约束，其前置 `install-host` 会写共享安装根，证据窗口内确有其他会话的 `build-mc`/`install-host` 写者进出；改用同一驱动 + 与 Makefile 同源的工具路径（`tools/infra/paths.py`）直跑，工具 md5 见第 5 条。
3. 可达 FAIL：禁用局部化（`prog_text = _localize_defined_globals(...)` → `pass`，锚点命中恰 1 处，驱动 md5 `2affa9a5…`→`641980ba…`）⇒ build-only rc=1、`0/19`、19 条 `SHT_RELA present`；`cp` 备份还原后 md5 回 `2affa9a5…` ⇒ rc=0、19/19、0 条。
4. `check-inst-asm` rc=0（274/274 镜像，链例+故障链 632 例）；`check-tests-index` rc=0（504 条）；`check-patch-tree` rc=2：20 problem = linux 12 + musl 2 + qemu 6，`llvm-project` 与 `tests` 段 0 条（在途漂移，分段披露）。
   linked-ELF 未受影响：直跑 `run_elf_e2e.py` rc=0、5/5（第 1/3 次 rc=75 被写入中的 `build-mc` 拒绝，第 2/3 次在写者释放后通过；`run_elf_e2e.py`/链接管线零改动）。
5. 工具 md5：llc `7db28942c5e6300d7a519e197b1b2edc`，llvm-mc `fb68573312714b5db0097deb6958918b`，llvm-objcopy `3d840aafc65b382e49cff746cbf33f5d`，qemu-system-dadao `7148dbca468a9eb34fa8aee7e6091835`，bootrom `a5d78816a95469766639fa658b647ef3`；writer-guard 起止 md5 一致（同一批二进制）。
**新发现/坑**：
- 只局部化 `main` 不够：`call_direct_ret`/`call_multiarg_stack`/`call_narrow_args`/`call_ptr_bank`/`branch_ptr`/`m10-loop-pointer-bank`/`ptr_diff_*` 的 IR 把辅助函数留在 external linkage（`add3`/`sum18`/`narrow`/`advance`/`deref`/`ptr_checks`/`walk_sum`/`pdiff`），同样发 `R_DADAO_REL26`。修法：局部化全部 TU 内定义的 `.globl`；未定义的外部名保持 `.globl`，残留重定位由既有 SHT_RELA 断言 fail-closed。
- 任务 worktree 未自带 `.dadao` 软链（同批 M20 worktree 均缺），`paths.py` 会解析到不存在的安装根；按既有 worktree 约定补 `.dadao -> 主工作树/.dadao`（gitignored，不入库、不改仓库文件）。
**遗留问题**：`make test-codegen` / `make test-elf` 两个 **Makefile 目标**未跑（前置 `install-host` 会写共享安装根）；已用同一驱动 + 同源工具路径直跑替代（19/19 与 5/5，rc 均 0）。收尾快速复跑因另一会话 `install-host` 写者被 writer-guard 拒绝（rc=75），未重跑；正式证据取自写者空闲窗口且 guard 起止 md5 一致。`check-patch-tree` 的 20 条 linux/musl/qemu 漂移属在途任务，未处置。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 任务书写「局部化 `main`」，但实测 6/19 例还有辅助函数 global 重定位 | ✅已修 | 改为局部化全部 TU 内定义的 `.globl`（`_localize_defined_globals`），并在注释说明 `m14-llvm-007` 行为与 fail-closed 边界 | 修复前 19 条 RELA（syms 含 `main`+8 个辅助名）；修复后 0 条、19/19 |
| `.globl` 解析只覆盖单符号形态，多符号/异形名会漏改 | ✅已修（按 fail-closed） | 正则只认合法符号名字符集；不匹配即原样保留，由既有 SHT_RELA 断言报红，不静默放过 | 注入禁用局部化 ⇒ 19 例全部报 `SHT_RELA present` |
| 注入可能「空注入」（锚点不存在仍回绿） | ✅已修 | run.sh 断言锚点 `count == 1` 且注入前后 md5 必须不同 | 注入 md5 `2affa9a5…`→`641980ba…`，脚本 PASS |
| 还原须守纪律（禁 git checkout） | ✅已修 | `cp -p` 备份 + md5 前后对账 | 还原 md5 == 原 md5，build-only 回 19/19 |
| 计数写死风险 | ✅已修 | run.sh 从 `expected.yaml` 现场派生例数，断言 results 分母、RELA 行数与之一致 | 两轮日志均按 19 现场比对 |
| 未跑 `make test-codegen` 是否掩盖问题 | ❌不修 | 目标仅比直跑多 `install-host` 前置；工具路径经 `paths.py` 同源解析，避免写共享安装根打断在途任务 | 工具 md5 与 Makefile 变量的解析源一致；guard 起止一致 |
| linked-ELF 直跑第 1 次 `rc=75`（另一会话 `build-mc` 持 llvm 写者） | ✅已修 | 保留现场后等写者释放，按同一命令重试（第 2/3 次） | 第 2 次 rc=0、5/5 PASS；guard 起止 md5 一致 |

#### 第 1 轮 reviewer 验收（2026-11-25 15:32–15:43，reviewer 自跑，不采信完成区）

**重跑记录（真实 rc）**
- 起始快照：`git status --porcelain -uall` 仅 2 行（本任务书 + `tools/testcases/unit/run_codegen_e2e.py`）；驱动 md5 `2affa9a5…`，与完成区一致。
- 运行期证据目录内 `run.sh`（md5 与 engineer 版逐字节一致的独立副本）重跑：`build_only rc=0 19/19 rela=0`；`full_qemu rc=0 19/19`；`driver_inject_selftest rc=0 INJECT: PASS`；`check_tests_index rc=0`（504 条，另单独重跑 `make check-tests-index` rc=0）；`check_inst_asm rc=0`（274/274 镜像、链例+故障链 632 例）；`inject_revert_localize PASS`（注入 rc=1、0/19、19 条 `SHT_RELA present` → `cp`+md5 还原 rc=0、19/19、0 条，md5 `2affa9a5→641980ba→2affa9a5`）。总 `RESULT: FAIL`、`EXIT=1`，唯一红项 `check_patch_tree`（下述）。
- `check-patch-tree` rc=2，20 problem = linux 12 + musl 2 + qemu 6 + **llvm-project 2**（`DADAODisassembler.cpp` 断言⑨/⑥）。根因是在途漂移：共享源码树该文件 mtime 15:23:59、其「patch series」本地 commit 15:24:08，且 `m20-llvm-001` 工作树同一 `.patch` md5 `2e6900de…` ≠ 本树/HEAD `d3ca27c8…`；在**不含本任务改动的主仓（master）**重跑 `make check-patch-tree` 得**同样 20 条、含同样 2 条 llvm**（rc=2）⇒ 非本任务所致，按任务书分段披露（完成区记「llvm 0 条」是其跑批时刻的状态，非笔误）。
- Makefile 目标（复核窗口已无 `install-host`/`build-mc` 写者 ⇒ 补跑）：`make test-codegen` **rc=0**（`install-host: PASS`、`Results: 19/19 passed, 0 failed`、`test-codegen: PASS`、`SHT_RELA present` 0 条）；`make test-elf` **rc=0**（`Results: 5/5 passed`、`test-elf: PASS`）——完成区两条「未跑 Makefile 目标」遗留已消解。
- linked-ELF 未受影响：直跑 `run_elf_e2e.py` rc=0、`Results: 5/5 passed`，writer-guard 起止 md5 一致。
- 工具 md5（`paths.py` 同源解析，全程同批）：llc `1e93fd9b…`、llvm-mc `ebaad000…`、llvm-objcopy `28c7f659…`、qemu-system-dadao `8b49d6d9…`、bootrom `a5d78816…`。与完成区 `7db28942…/fb685733…/3d840aa…/7148dbca…` 不同，因复核窗口前 `install-host` 更新了安装根；本审查复核的是**同一份源码 + 当前安装根**（bootrom 两者一致 `a5d78816…`）。

**独立注入（reviewer 自设，非 engineer 脚本）**：把 `defined = {…finditer(text)}` 改为 `defined = {"main"}`（只局部化 `main`，驱动 md5 `2affa9a5…`→`96b4c381…`，锚点命中 1 处）⇒ `--build-only` **rc=1、11/19、8 条 `SHT_RELA present`**（`branch_ptr`/`call_direct_ret`/`call_multiarg_stack`/`call_narrow_args` 等辅助函数残留）；`cp -p` 备份还原后 md5 回 `2affa9a5…`（相等）⇒ rc=0、19/19、0 条。断言可达 FAIL，且「只局部化 main 不够」独立复现。

**实现核验**：合成输入 + 19 例真实 `llc` 输出逐行比对——仅 `.globl <TU 内已定义名>` 行被改写（28→28），未定义外部名、注释行、带尾注/带引号等异形 `.globl` 一律原样保留（fail-closed），行数不变、无其它指令被误改；`run_elf_e2e.py` 与链接管线零改动。

**约束核验**：`git diff --name-only HEAD` = 本任务书 + `run_codegen_e2e.py` 两件；`components/**`、`spec/`、`.tao/contracts/`、`Makefile` 无改动；无 `.work/**` 入库（`!!` 忽略）；任务书正文无运行期绝对路径；未提交 git；工程证据目录 md5 未被本审查改写。

**判决：Accepted** —— 验收 1–3、5 在 reviewer 自己重跑下全绿，4 按任务书分段披露口径成立（唯一红项属他任务在途漂移，已用主仓对照复跑佐证）。**遗留**：llvm/linux/musl/qemu 的 20 条 patch 漂移归在途任务处置；本轮审阅记录写入后已复跑 `make check-knowledge-refs`（rc 见下一次门控记录）。
