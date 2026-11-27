# m16-testcases-021: 证据脚本与探针收尾（恒真式 / 默认 profile / 探针写反 / 挂死 fail 路径）

**模块**：testcases
**项目里程碑**：M16
**依赖**：相关任务均已合入（chipyard-003/009/010、testcases-003、qemu-001/002/003、11-cfx）
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

`m16-testcases-020` 处理 tests/arch 的 cfx5 I+D 与失败时限；本任务收口**证据脚本/探针自身的正确性**（恒真式、默认 profile、写反的探针、挂死的 fail 路径），这些不改变被检语义，但会让"看起来绿"或"失败形态不可判"。

## 要做

1. **恒真式（ISS-467⑤ / ISS-489 f1–f2 / ISS-492）**
   - 证据脚本 `rebuild … && eq … "$?"`：改为先取 `rc=$?` 再断言，禁止 `&&` 短路吞掉重建失败；
   - `merge-tree` 判据在无提交时恒真：改为"改动集 ∩ `HEAD..master`"兜底；
   - Tiny FIRRTL 计数在文件缺失时默认 0：缺文件应判红/显式跳过，不得静默；
   - `bin.qemu.install_eq_build` 在 `QEMU=` 覆盖时两侧同路径：覆盖时显式标 `N/A`，不得恒真。
2. **默认 profile 与信息行（ISS-m16-001）**
   - `patch_tree_judge` 把"源树缺失、skipping"信息行计为问题 ⇒ 按 `check_patch_tree.py` 的信息行清单对齐；
   - `integ042t` 的 `_MACH` 默认 tiny 与 `node_probe_prelude` 默认 vast 不一致 ⇒ 统一默认 profile（或强制显式），漏设时给具名错误而非对称假红。
3. **探针写反（ISS-519②）**：`m16-qemu-001` 探针的 `SEL_I`/`SEL_D` 与 `cache_ctrl[15:14]`（2=I、1=D）写反 ⇒ 补正，并在该例加一条能暴露的断言。
4. **挂死 fail 路径（ISS-473）**：`tests/inst/11-cfx/escape_ciii_cfx.S` 链例 12 的注释与实测不符（第 3 次到达是双 lane 挂死，不是具名判红）⇒ 让 probe 在计数超限时走具名 `__EXIT`（或按实际改注释并登记该例不可用于回归）。
4. **`ptw_carrier_tlb` 缺参超时（`m16-testcases-020` 复核发现）**：`run_arch --cfx 4` 15/15 rc=0，但载体在缺 `--cfx-access` 时 20 s TIMEOUT（不走 `runlimit` env）；补齐调用参数或让缺参给具名 SETUP 错误，别表现为 20 s 超时。
5. **孤儿 QEMU（ISS-522 残余）**：外部强杀驱动会留下孤儿 QEMU 写满磁盘；证据脚本统一 `ulimit -f` + 显式 `killpg` 兜底（`runlimit` 已覆盖自身超时/超限）。
5. **写入证据**：每条改动在 `run.sh` 里配一条可达 FAIL（注入回退 ⇒ 红；`cp`+md5 还原回绿）。
6. **不改**被检语义、不改 `tests/arch` 的 cfx5 I+D/时限（属 `m16-testcases-020`）。

## 不做

- 不修 `ISS-519①`（QEMU I 侧不可独立观测，已由 `DIV-15` 登记）；
- 不修 chipyard `changelog`/`README` 的文档笔误（ISS-467①②③④、ISS-485、ISS-489 f3–f5 已关闭）。

## 约束

- 独立 `git worktree`；**不提交 git**；变更集限 `tools/**`、`tests/inst/**`、`tests/arch/**`、`tests/data/inst-signature/**`（`.S` 注释改动的签名数据重生成，已在完成区披露）、运行期证据脚本、本任务书；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 每个恒真式改后都有"注入重建失败/缺文件/覆盖 ⇒ 红"的可达 FAIL 证据；
2. `SEL_I`/`SEL_D` 纠正后有一条能区分 I/D 的断言；
3. 11-cfx case12 的 fail 路径为具名退出（或注释与实际一致并登记）；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、相关 `run_arch --self-test` 记录 rc。

## 完成区

**测试结果**：运行期证据 `run.sh` **PASS=67 / FAIL=0 / N/A=0**（12 段注入：回退⇒红；其中对仓库文件做 `cp`+md5 还原的 4 段 = A/A8/B/C，其余用临时副本或只读对照，同样有可达 FAIL）；`run_arch --cfx 4 --platforms qemu` 15/15；`check_inst_sig` 274/274（静态槽 4526 逐槽）。
**修改文件**：新增 `tests/arch/common/runlimit.py`（**以 020 原件 `runlimit.py.preinject` 为基**，md5 `86aa51…`；仅并入 `RLIMIT_FSIZE`（`ulimit -f` 内核兜底），`finish_dump`/`KILL_GRACE`/`env=` 保持原件语义）；`tests/arch/ptw/ptw_carrier_tlb.py`；`tools/testcases/arch/node_probe_prelude.py`；`tools/infra/check_patch_tree.py`（输出契约）；`tests/inst/11-cfx/escape_ciii_cfx.S`（注释 + GAP⑥）；`tests/data/inst-signature/{expected.tsv,inputs.sha256}`（**越界披露**：`.S` 注释改动必刷行号/源 md5，仅该镜像 14 行）；运行期脚本就地修：`m16-testcases-003`（覆盖⇒N/A）、`m16-chipyard-003`（11 处 `rebuild && eq "$?"`→`rebuild_then_eq`）、`m16-chipyard-008`（merge-tree 无提交兜底、Tiny FIRRTL 缺文件/缺快照判红）、`m16-qemu-001/probe.py`（SEL 补正 + I/D 行为断言 + 合约自检）、本任务 `run.sh`+`checks.py`。
**验收结果**（逐项）：
- A `runlimit` 8 项：超时 rc=-2@1 s、dump 越界 rc=-3、孙进程被回收、失败/通过两态截断（失败截 1 MiB、通过保留）、非法 env 显式失败、`dfilter`、`RLIMIT_FSIZE` 内核封顶（去掉注入 ⇒ 300 MB 落盘、判据回红）。
- B profile：漏设 env 时 prelude/`machine_profile.load()` 同为 vast；`integ042t --only dma_cfx_to_pa` rc=0。
- C ptw：缺 `--cfx-access` rc=2 @0.13 s 含 SETUP（hmon/umon/smon 同）；补参 umon rc=0；`DADAO_ARCH_TIMEOUT=7` 生效。
- D `install_eq_build`：覆盖态 `pass=0 fail=0 na=1`；默认态 `pass=1`；**两侧不同 ⇒ `pass=0 fail=1`**（证明比较不像同源自比那样恒真）；旧恒等 eq 版在覆盖态回红。
- E merge-tree：无提交+master 前进同文件 ⇒ 红，无交集 ⇒ 绿；裸 merge-tree 注入 ⇒ 假绿。Tiny FIRRTL 缺文件 ⇒ 红；`${tiny_tlb:-0}` 注入 ⇒ 假绿。
- F escape：注释三项断言 + 镜像执行 rc=0（旧措辞注入回红）。
- G judge：干净日志 0 问题、真问题 1、全行计数 23（复现 ISS-518 假红）。
- H SEL：D-only `clean` 写回脏行、I-only 不写回（经 cfx_pmem DMA 旁路观测）；写反 ⇒ 两例都红，且静态合约自检 SETUP。
- K 磁盘兜底：`m16-testcases-003`/`m16-chipyard-003`/`m16-chipyard-008` 加 `ulimit -f 131072`，`probe.py` 加 `RLIMIT_FSIZE`（子孙继承，孤儿也封顶）；删行注入回红。
- L「重建失败 ⇒ 红」：静态（003 有 `rebuild_then_eq`、008 用 `; eq … "$?"`，两处都无 `&& eq … "$?"`；注释行不计）+ 动态（真实 helper/真实调用行 + 失败 `rebuild` 桩 ⇒ fail=1；旧式 `&&` ⇒ fail=0 被吞）；临时副本回退 ⇒ 同一判据回红，`cp`+md5 还原 ⇒ 回绿。
- 门控 rc：`check-tests-index` 0 / `check-tasks` 0 / `check-knowledge-refs` 0 / `run_arch --self-test` 0。
**新发现/坑**：① `tests/arch/common/runlimit.py` **git 里没有，但盘上可恢复**：020 复核备份 `runlimit.py.preinject`（md5 `86aa51…`，与 020 记录一致）。本任务先前的重建件（`1353dfdc…`）与原件有语义差异（`finish_dump` 无条件截断、未 unlink/建 dump 父目录、`KILL_GRACE` 0.5、无 `env=`），已弃用并改为「原件 + `RLIMIT_FSIZE`」。② `check_inst_sig` 的 `inputs.sha256` 含 `.S` 源 md5 ⇒ 任何注释改动都需 `--write`。③ `m16-chipyard-010`/`m16-qemu-002` 的 `run.sh` 已随 worktree 删除 ⇒ 同类修复落在存活副本 `m16-chipyard-008`。④ `integ042t` 缺省已是 vast（509fa470），残留不一致在库级缺省 tiny。
**遗留问题**（返工轮处置见下段）：① `m16-chipyard-016/017` 仍有同型 `rebuild … && eq "$?"`（范围外，建议登记 issue 随下次触碰修）；② `ISS-467⑤` 的 `--jobs 8`→核数−2 未改；③ `ISS-518`/`ISS-489` 中指向已删脚本的两处判定只有契约 + 可复现判据，无原文件可改；④ worktree 内 `.dadao/{cross-toolchain,host-tools,dadao-unknown-elf,tests/bootrom}` 软链与 `.dadao/tests/` 是跑门控所需、已被 `.gitignore` 覆盖，随 worktree 收尾清理（不进提交）。
**返工处置（第 1 轮 reviewer Needs Revision）**：① **`runlimit` 以原件为基** ✅已修 —— 用 `runlimit.py.preinject`（md5 `86aa51…`）覆盖重建件，仅并入 `RLIMIT_FSIZE`；`finish_dump`/`KILL_GRACE`/`env=` 保持原件；A5 改测「失败截断 1 MiB / 通过保留完整」两态，新增 a8（去掉 RLIMIT ⇒ 300 MB 落盘、回红）。合并时 `runlimit.py` 以本分支为准（覆盖 master hotfix 的 `1353dfdc…`）。② **「重建失败 ⇒ 红」覆盖** ✅已修 —— 新增 L 段：静态（003 含 `rebuild_then_eq`、008 用 `; eq … "$?"`，两处均无 `&& eq … "$?"`，注释行不计）+ 动态（真实 helper/真实调用行 + 失败 `rebuild` 桩 ⇒ `fail=1`；旧式 `&&` ⇒ `fail=0` 被吞）+ 临时副本回退注入回红、`cp`+md5 还原回绿。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-25）

范围：`runlimit.py`（新）、`ptw_carrier_tlb.py`、`node_probe_prelude.py`、`check_patch_tree.py`、`escape_ciii_cfx.S`、`probe.py`、4 个运行期脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `run()` 形参 `timeout` 遮蔽模块函数（用 `globals()` 取值） | ✅已修 | 增 `_default_timeout` 别名 | A 段 7 项全绿 |
| F2 dump 越界但内核先 SIGXFSZ 时 rc 仍为 -25 | ✅已修 | `dump_capped` ⇒ rc 统一 -3 | a4 rc=-3 |
| F3 缺参守卫置于 `--selfcheck` 之前，打断 `check_tlb --selfcheck` | ✅已修 | 守卫移到 list/selfcheck 之后 | `check_tlb --selfcheck` rc=0；self-test PASS |
| F4 守卫以 `MODE != hmon` 为条件 ⇒ hmon 仍 20 s 超时 | ✅已修 | 改无条件 `not CFX_ACCESS`（body 三模式都要 cfx） | C1/C2：hmon 也 rc=2@0.13 s |
| F5 新用例无 handler 却 `setup_hmon_vector`（向量指向 padding） | ✅已修 | 去掉该调用 | H2 两例 PASS |
| F6 DMA 方向参数写反（DIR=1 是 PA→CFX） | ✅已修 | `pa_to_cfx` 语义 + 两处调用 | H2 两例由 rd7=0 转为 PASS |
| F7 A-inject 只改 `finally` 分支不触发（超时走 `_terminate`） | ✅已修 | 注入改在 `_signal_group`（不 killpg） | a3 注入后 FAIL |
| F8 merge 场景生成器把提交落在 feature（master 未前进） | ✅已修 | 回 master 提交后再 checkout feature | E1 `fail=1` |
| F9 judge 误判含冒号 label 的 `patch(es)` 行；问题行+汇总重复计数 | ✅已修 | 放宽正则；以 `N problem(s)` 为准 | G2=0、G4=1、G3=23 |
| F10 孤儿兜底会误杀其它会话的 QEMU | ✅已修 | 只杀带 `M16_021_EVI=1` env 的新进程 | J1 PASS / J-inject 存活 |
| F11 `.S` 注释改动使 `inputs.sha256`/行号失配 | ✅已修（越界披露） | `check_inst_sig.py --write` 仅刷该镜像 | `check_inst_sig` 274/274 |
| F12 证据脚本未统一磁盘兜底（ISS-522 残余） | ✅已修 | 三个脚本加 `ulimit -f`；probe 加 `RLIMIT_FSIZE` | K 段 4 项 + K-inject |
| F13 K-inject 只验 sed 结果、未走同一判据 | ✅已修 | 抽出 `has_limit()` 单一判据 | K-inject 走同一函数 |
| F14 重建件偏离 020 原件（`finish_dump` 无条件截断等） | ✅已修 | 以 `runlimit.py.preinject` 为基，仅加 `RLIMIT_FSIZE`；A5 改测「失败截断 / 通过保留」两态 | A 段 8 项；diff 仅 RLIMIT |
| F15 A-inject 锚点指向重建件函数 | ✅已修 | 锚点改为原件的 `os.killpg(pgid, sig)` | A-inject 回红/还原回绿 |
| F16 「重建失败 ⇒ 红」无覆盖 | ✅已修 | 新增 L 段：静态 + 动态 + 副本回退注入 | L1–L3b、L-inject |
| F17 L 段标题双引号内 `$?` 被提前展开 | ✅已修 | 标题改单引号 | 输出 `; eq $?` 字面 |
| F18 D3 两侧同文件（同源自比）无可达 FAIL | ✅已修 | 新增 D3b：两侧不同 ⇒ `pass=0 fail=1` | D3b PASS |

判决：18 条 finding 全部已修；证据脚本连跑两次 `PASS=67 FAIL=0`、PASS 项逐条 `diff` 一致（含全部注入与还原）；状态 → 待验收。

### 第 1 轮 reviewer 验收（2026-11-25）

**重跑记录（全部本人执行，不采信完成区）**
- 运行期证据目录内 `run.sh`（`REPO=<本 worktree>`）连跑两次：`checks: PASS=55 FAIL=0 / N/A=0`、`RESULT: PASS`、`EXIT=0`，两次 PASS 项名逐条 `diff` 一致。
- 独立注入（改被测产物 `tests/inst/11-cfx/escape_ciii_cfx.S`，先 `cp`+md5 `c5c3f7e9…` 备份）⇒ 同一脚本 `[FAIL] F1-3`、`checks: PASS=53 FAIL=2`、`EXIT=1` ⇒ `cp` 还原 md5 相等 ⇒ 复跑 `PASS=55 FAIL=0`、`EXIT=0`、PASS 项与首轮逐条一致。
- `check_inst_sig --data-only` ⇒ `rc=0`、`274 镜像 / 4564 槽（静态 4526 / 运行期 38）`；`inputs.sha256` 仅 `escape_ciii_cfx.S` 一行变（`21079e3e…`→`8c943909…`），`expected.tsv` 13 行只改行号（均 +4）⇒ 确为注释所致。
- `run_arch --cfx 4 --platforms qemu` ⇒ `PASS（15 case × 1 平台）`、`EXIT=0`；`run_arch --self-test` rc=0；`check-tests-index` rc=0（504 条）；`check-tasks` rc=0；`check-knowledge-refs` rc=0（本 worktree 与 master 均 0）。
- `make check-arch-smoke`（master，含 `eb9f456f`）⇒ `30/30 checks passed`、`EXIT=0`；分支同名目标 `EXIT=2`，失败在 `build-mc`（worktree 未 fetch 源树，CMake `source directory … does not exist`）＝环境缺源、非交付物缺陷。
- 合并验证（临时树：本分支改动落在 `5d8aecf3` 后 `git merge eb9f456f`）⇒ **无冲突**，合并文件同时含 `os.makedirs(WORKDIR, exist_ok=True)` 与 `SETUP: 需要 --cfx-access`；WORKDIR 缺失时载体 `rc=0`；删掉该行再跑 ⇒ `rc=2` 具名 `SETUP: llvm-mc … No such file or directory`（非 traceback、非挂死）⇒ 合并后保留该行、无 ENOENT。
- `runlimit` md5 `1353dfdc705113dcd8b68a764f162145` 与 master hotfix 同一份；10 个调用点静态核对 `run/timeout/finish_dump/dfilter/max_dump_bytes/DEFAULT_TIMEOUT/RunLimitError` 全在且签名兼容；`C1 rc=2 @107 ms`、`C4 DADAO_ARCH_TIMEOUT=7`、`TIMEOUT`/`DUMP-CAPPED` 分支（prelude `reason = …`）均实测。

**约束核验**：独立 worktree ✓；未提交 git ✓（开审/收审 `git status -uall` 逐行一致）；术语「寄存器组」✓；**变更集超行**——约束只列 `tools/**`、`tests/inst/**`、证据脚本、任务书，实际另有 `tests/arch/**`（「要做 4」要求的 ptw 载体 + runlimit）与 `tests/data/inst-signature/**`（已越界披露）：任务书自相矛盾，建议收尾改约束行。

**判决：Needs Revision**（两条必改）
1. 「验证 1」的**「注入重建失败 ⇒ 红」零覆盖**：`grep -n "rebuild" run.sh` 只命中 CY003 变量与 K 段 ulimit，`checks.py` 无 rebuild ⇒ 4 个恒真式里 merge-tree / 缺文件 / 覆盖各有注入，唯 `rebuild && eq "$?"` 回退后仍全绿（既无静态判据也无注入）。修复本身我实测正确（stub `rebuild` rc=1：新式 `FAIL=1`、旧式 `FAIL=0`）。**改法**：run.sh 加静态判据（CY003 含 `rebuild_then_eq`、不含 `&& eq "$?"`）+ 临时副本换回旧式 ⇒ 同一判据回红 ⇒ `cp` 还原回绿。
2. 遗留①「`runlimit` 原文件不可恢复、md5 记录作废」**不属实**：原文件（md5 `86aa516707d07289e22f8724ab2364a5`，与 020 三处记录一致）在 020 复核的注入前备份 `m16-testcases-020-review/runlimit.py.preinject`；git 侧属实（全对象 25231 blob 扫描 0 命中 `HEAD_BYTES = 1 << 20`）。且重建件与原件**行为不等价**：`finish_dump` 由「仅失败时截断、通过保留完整 dump」改为无条件截断（5 个调用点无条件调用）；`run()` 不再 unlink/建 dump 父目录（QEMU `-D` 实测会截断旧文件，风险低）；`KILL_GRACE` 3.0→0.5；删 `env=`（无调用方）；新增 `RLIMIT_FSIZE`（原件无）。**改法**：按原件 + `RLIMIT_FSIZE` 合并，或在完成区如实披露该差异并请 architect 定夺。

**非阻断 finding**：① 完成区「9 组注入」实为 10 段（`-- *-inject` 头），带 `cp`+md5 还原的仅 A/B/C 3 段；② D3 默认态两侧同一文件（同源自比），「安装根 vs 构建树不等 ⇒ FAIL」无可达 FAIL；③ `m16-chipyard-016/017` 仍有 `… && eq "$?"` 同型恒真式（任务未点名，范围外）；④ worktree `.dadao/` 下 3 个软链 + `tests/` 由 run.sh 所建、已被 `.gitignore` 覆盖，随 worktree 收尾清理；⑤ 遗留②（chipyard-010/qemu-002 证据目录确不存在）、遗留③（`--jobs 8` 未改，ISS-467⑤ 仍 open）属实。


### 第 2 轮 engineer 返工自审（2026-11-25）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 `runlimit` 重建件与 020 原件行为不等价 | ✅已修 | 原件为基 + `RLIMIT_FSIZE`；A5 两态、a8 内核封顶 | A 段 8 项；A8-inject 回红/还原回绿；diff 仅 RLIMIT |
| R1b `timeout(fallback=…)` 依赖重建件签名 | ✅已修 | 载体改 `runlimit.timeout(TIMEOUT)`（原件位置参数） | `run_arch --cfx 4` 15/15；self-test 0 |
| R2 「重建失败 ⇒ 红」零覆盖 | ✅已修 | 新增 L 段（静态 + 动态 + 副本回退注入） | L1–L3b、L-inject 回红/还原回绿 |
| R3 完成区「9 组注入」计数不实 | ✅已修 | 改「12 段（`-- *-inject`），仓库文件 cp+md5 还原 4 段」 | `grep '^say "  -- .*inject'` = 12 |
| R4 D3 同源自比无可达 FAIL | ✅已修 | 新增 D3b：两侧不同 ⇒ `pass=0 fail=1` | D3b PASS |
| R5 约束行缺 `tests/arch/**`/`tests/data/inst-signature/**` | ✅已修 | 约束行补两项并标注披露 | 本节 #约束 |

判决：必改 2 条 + 文档订正 3 条全部完成；`run.sh` 连跑两次 `PASS=67 FAIL=0`、PASS 项逐条一致；`run_arch --cfx 4 --platforms qemu` 15/15；四门控 rc=0；状态保持「待验收」。

### 第 2 轮 reviewer 验收（2026-11-25）

**重跑（全部本人执行，不采信完成区）**
- 运行期证据目录内 `run.sh`（`REPO=<本 worktree>`）连跑两次：`checks: PASS=67 FAIL=0 / N/A=0`、`RESULT: PASS`、`EXIT=0`，PASS 项名与注入段 `[FAIL]` 行逐条 `diff` 一致。
- 独立注入（改**真实**运行期脚本 `m16-chipyard-003/run.sh`：`rebuild_then_eq …`→旧式 `rebuild … && eq … "$?"`，`cp`+md5 `53fec4ed…` 备份）⇒ 同一脚本 `[FAIL] L1 静态…` + `[FAIL] L-inject 还原后回绿`、`checks: PASS=65 FAIL=2`、`EXIT=1` ⇒ `cp` 还原 md5 相等 ⇒ 复跑 `PASS=67 FAIL=0`、`EXIT=0`、PASS 项与首次逐条一致。
- `runlimit.py` diff（原件 `86aa51…` → `bc2f4513…`）**仅 3 处**：docstring 补 RLIMIT 说明、`import resource`+`_set_fsize_limit`、`run()` 内 `preexec`；`KILL_GRACE=3.0`、`finish_dump(path, res, head=HEAD_BYTES)` 的「仅失败截断」守卫、`run(cmd, *, timeout, dump=None, env=None, cwd=None)` 的 `env=` 均保留；`preexec` 仅 `dump_path is not None` 时设置；`from common import runlimit` OK、`timeout(20)=20`（位置参数）；载体已改 `runlimit.timeout(TIMEOUT)`。
- L 段 L1/L2/L2b/L3/L3b + L-inject 全 PASS（新式 `fail=1 pass=0`、旧式 `fail=0 pass=0` 被吞、临时副本回退⇒红、`cp`+md5 还原⇒绿）；A/A8/B/C 四段对仓库文件 `cp`+md5 还原 PASS；注入段共 **12 段**、`cp`+md5 还原 **4 段**，与完成区一致；D3b `pass=0 fail=1` PASS；A 段 8 项（a5 两态、a8 RLIMIT）全绿。
- `run_arch --cfx 4 --platforms qemu` ⇒ `PASS（15 case × 1 平台）`、`EXIT=0`；`check-tests-index` rc=0（504 条）、`check-tasks` rc=0、`check-knowledge-refs` rc=0、`run_arch --self-test` rc=0、`check_inst_sig --data-only` rc=0（274 镜像 / 静态 4526 槽）。
- 文档：遗留①改「git 里没有、盘上可恢复」+ 返工处置「合并以本分支覆盖 master `1353dfdc…`」；约束行已含 `tests/arch/**`、`tests/data/inst-signature/**`；016/017 同型恒真式登记在遗留①（`issues-*.yaml` 未立条目，范围外）。`run.sh` **无 `--inject` 参数**（无参数解析），A/A8/L/C 注入含在全量跑内，已由上列 4 次全量覆盖。

**约束核验**：独立 worktree ✓；未提交 git ✓（审前/审后 `git status -uall` 逐行一致、7 个交付文件 md5 回审前值）；变更集与新约束行一致 ✓；术语「寄存器组」✓、无运行期路径（本记录写入后 `check-knowledge-refs` rc=0）。

**判决：Accepted** —— 上列重跑与独立注入全部由本人复现，约束无违反。

**非阻断 finding**：① `checks.py` 的 `a5/a8` 用 `tempfile.mkdtemp(dir=TMP)` 且不清理 ⇒ 每跑一次 `run.sh` 在运行期临时目录遗留约 300 MB（A8 注入态 `flood.bin`），本轮已由 reviewer 清理 896 MB；建议注入后删除该目录。② `issues-*.yaml` 未为 016/017 同型恒真式立条目（任务书遗留①已登记，范围外）。
