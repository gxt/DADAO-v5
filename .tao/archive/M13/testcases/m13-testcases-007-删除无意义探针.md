# m13-testcases-007: 删除无意义探针 `start_busy_returns_busy`（保留 doc 级检查）

**模块**：testcases
**项目里程碑**：M13
**依赖**：无
**可并行分片**：否（arch 探针单写者）
**状态**：已验证

## 用户裁定（2026-11-10）

> 「trap指令应该引发陷入，陷入返回才会执行下一条指令；这个探针本身没有任何意义！！！」
> 「B」——删除该探针，只在 `--doc` 层保留检查，接受运行时无覆盖。

## 背景

`integ047t` 的 `start_busy_returns_busy` 用「两条相邻 `trap`」测「BUSY 期间重复 `START` 必须返回 `-5`」。**前提错误**：`trap` 是陷入，第二次 `trap` 在**整条异常进入+处理+退出**之后才执行，间隔不是「几百 ns」而是 handler 的全部耗时 ⇒ 是否能落在 1 ms/1 µs 的 BUSY 窗口内纯属运气。

实测约 **5% 偶发失败**（`got=0x62`），两个 reviewer 都在**基线源码**上复现过、重跑即过 ⇒ 噪声，且会掩盖真回归（`ISS-364`）。

## 目标

1. **删除** `tools/testcases/arch/min_rom_probe_integ047t.py` 中的 `start_busy_returns_busy` 用例（含其汇编生成与注册表项）。
2. **保留** `--doc` 层检查（离线校验规范伪代码/表项存在性），不得因删除运行时用例而删掉 doc 断言。
3. **同步外围**：若 `Makefile`/smoke/`check-arch` 的用例计数或名单写死了该例，一并更新；不得留下「期望 N 例实际 N-1」的假绿或假红。
4. **记录理由**：在该文件的模块 docstring 与该任务的完成区写明「为何删除」（陷入往返不是时间窗；`ISS-364`）。
5. **不做**：不新增替代探针（B 选项），不改设备模型，不改 `DADAO-22`。

## 验收标准

1. `grep -rn 'start_busy_returns_busy' tools/ Makefile tests/` 为 0（或仅剩注释说明已删除）
2. `min_rom_probe_integ047t.py --doc` rc=0，且 doc 用例数与删除前一致
3. `make check-arch` rc=0；用例数与删除前**恰少 1**（现场统计，不写死）
4. 连跑 `check-arch` **20 次** rc 全 0（证明 5% 噪声消失；这是本任务的核心判据）
5. 一键证据脚本（含可达 FAIL 注入：例如把删掉的用例名重新加回注册表 ⇒ 应 FAIL）
6. 完成区 ≤30 行、无运行期路径

## 说明

- 删除后「BUSY 期间拒绝 `START`」在**运行时无覆盖**，仅 `--doc` 层校验规范文本 —— 用户已知悉并接受（B）。
- 必须在独立 `git worktree` 内作业（`ISS-368`）；不占用 207/208。
- 若发现其它探针也用「相邻 `trap`」当时间窗（同类缺陷），**登记并返回主会话**，不要顺手改。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`tools/testcases/arch/min_rom_probe_integ047t.py` 全量 diff（-41/+8 行）。

- 删除完整性：`@case("start_busy_returns_busy")` 注册项、`_start_busy_returns_busy()` 汇编生成、仅它使用的 `EXIT_BUSY_FIRST/SECOND` 均删除；`grep` 仅剩 docstring 说明 1 处；`--list` 6 行（5 runtime + 1 doc）。
- doc 层零改动：`# doc case:` 至文件尾与 `merge-base` 版本逐字节相同（证据脚本 `doc_and_driver_section_unchanged`=0）；`--doc` 17 checks 前后一致。
- 残留符号：`SBI_SUCCESS`/`NEG5`/`NEG2`/`EXIT_PASS` 仍被其它用例与 provider 使用，无孤儿；`py_compile` 通过。
- 语义：删除理由按用户裁定原话写清（`trap` 是陷入，两次 `trap` 之间是完整异常往返，不是时间窗）；未新增替代探针（B 选项）。
- 外围：`Makefile` 仅在 `ARCH_CFX_PROBES` 注册探针、无写死用例数；`tools/testcases/arch/README.md` 与 `tests/` 无该用例名或计数 ⇒ 无需改动。
- 同类缺陷扫描：无其它探针把「相邻 trap」当时间窗。`integ050t::sbi_time_monotonic` 两次 `trap` 间有 5000 次循环（测严格单调，合法）；`integ042t::dma_busy_*` 是寄存器级相邻写（窗口差 3 个数量级），非异常往返类缺陷。
- 防造假：`--doc`/runtime/`check-arch` 均真实执行并落证据日志；注入「重加注册项」⇒ 守卫 rc=1，`cp`+md5 还原后回绿。

**判决**：无未修 finding；状态 `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无 | — | — | — |

### 第 2 轮 reviewer 验收

**重跑（全部本人执行，输出为真实终端摘录）**

1. `grep -rn 'start_busy_returns_busy\|EXIT_BUSY_FIRST\|EXIT_BUSY_SECOND' tools/ Makefile tests/` ⇒ 仅 `min_rom_probe_integ047t.py:30`（docstring 删除说明）1 处；`EXIT_BUSY_*` 0 处；`__pycache__/*.pyc` 被 `.gitignore:11` 忽略。
2. `--doc` rc=0、`doc: 17 checks, 0 failed`；基线（`git show HEAD~1:` 取出后同目录跑）同为 17 checks；`# doc case:` 至文件尾与基线 **md5 均 `f727481d3ea06427a3696536e0e4e618`**（逐字节相同）。
3. `--list`：现 6 行（5 runtime + 1 doc），基线 7 行（含 `start_busy_returns_busy`）⇒ **恰少 1**；`--list` rc=0/0。
4. `make check-arch`：本人独立连跑 **11 次 rc 全 0**（1 次 + 10 次后台），10 份日志各含 1 条 `check-arch: PASS`、0 条 `check-arch: FAIL`；`check-arch-probe-integ047t.log` 为 `5/5 runtime passed`。engineer 的 20 份日志复核：20 条 PASS、0 FAIL。
5. 证据脚本：`run.sh` rc=0（15 项 PASS）、`run.sh --inject` rc=0（`inject_guards_detected=1`、md5 还原一致）、`run.sh --soak 2` rc=0（历史日志隔离后跑，见 finding 2）。
6. **reviewer 独立注入**：`cp`+md5 备份 ⇒ 在 `# doc case:` 区加 `REMOVED_CASE = "start_busy_returns_busy"` ⇒ `run.sh` **rc=1**，`FAIL mentions_only_in_docstring (1 vs 2)`、`FAIL doc_and_driver_section_unchanged (0 vs 1)` ⇒ `cp` 还原、`md5sum -c` = `4878a872… OK` ⇒ 重跑 `run.sh` rc=0 回绿。
7. 同类扫描：机械扫描全部 `min_rom_probe_*.py` 无「相邻 `trap`」对；`integ050t::sbi_time_monotonic` 两 `trap` 间有 `delay_loop(N=5000)` 且断言 `t2 >= t1+1`（单调性，非短窗）；`integ042t::dma_busy_start_ignored` 先 `pmem_r` 断言 `BUSY` 可见（rd5=ST_BUSY）再发第二次 `START`，窗口前提被显式断言 ⇒ 均非同类缺陷。
8. 纪律：改动文件仅 2 个（`git diff HEAD~1 --name-only`）；`git status --porcelain -uall` 干净；完成区 17 行、无运行期路径；未 commit/push；未占用 207/208。

**约束核验**：验收 1–6 全部满足；不新增替代探针、未改 Makefile/`tests/`/`DADAO-22`（diff 零命中）；理由已入 docstring。

**非阻断 finding**（architect 收尾时顺手处理即可）：① `run.sh` 的 `doc_checks_count` 期望与实际同源于同一公式（`8+len(FIDS_0_5)+len(FIDS_6_8)`），保护实由 `doc_and_driver_section_unchanged` 承担；② `--soak` 的 `soak_run_count` 用 `ls check-arch-*.log` 计数，历史日志未清时会假红，复跑需先隔离旧日志。

**判决**：**Accepted**（全部验收命令本人重跑通过，注入→FAIL→还原→回绿属实）。

## 完成区

**测试结果**：`--doc` rc=0（17 checks）；runtime 5/5（删除前 6/6）；`make check-arch` **连跑 20 次 rc 全 0**（每次含 arch-smoke + 13 探针，integ047t 均 `5/5 runtime passed`，0 FAIL）；一键证据脚本默认 `--inject`/`--soak 20` 三种模式均 rc=0。

**修改文件**：`tools/testcases/arch/min_rom_probe_integ047t.py`（删用例/常量，docstring 记理由）；本任务书（状态 + 审阅记录 + 完成区）；运行期证据脚本（未归档）。

**验收结果**（逐条）：
1. `grep -rn 'start_busy_returns_busy' tools/ Makefile tests/` = 1 处，且仅在模块 docstring 说明内（`mentions_only_in_docstring` 通过）。
2. `--doc` rc=0，用例数 17 checks = 删除前；`# doc case:` 至文件尾与基线逐字节相同。
3. `make check-arch` rc=0；integ047t 用例数 **6 runtime → 5 runtime**（`--list` 7 → 6 行，含 doc 例），恰少 1，证据脚本按 `merge-base` 基线现场统计。
4. 20 次连跑 rc 全 0；20 份日志均 `check-arch: PASS`、integ047t `5/5`、零 `check-arch: FAIL`。
5. 注入：重加 `@case("start_busy_returns_busy")` 注册项 ⇒ 守卫 rc=1；`cp`+md5 还原（md5 一致）后回绿。
6. 完成区行数合规、无运行期路径。

**新发现/坑**：证据脚本基线必须取 `git merge-base HEAD master` 而非 `HEAD`——本任务提交后 HEAD 已含删除，用 HEAD 会把「恰好少 1」判成 0 差异。同类扫描结论见自审记录（无第二处相邻 trap 时间窗）。

**遗留问题**：「BUSY 期间重复 START 返回 -5」删除后运行时无覆盖，仅 `--doc` 校验规范文本——用户裁定 B 已知悉并接受；未发现其它同类缺陷需登记。

#### 收尾（architect，2026-11-10 22:02）

- reviewer **Accepted**：删除干净（仅 docstring 留 1 条说明）；`--doc` 17 checks 与基线**逐字节相同**（md5 `f727481d…`）；用例 7 → 6（`@case(` 6→5）。
- **连跑 31 次 0 红**（engineer 20 + reviewer 11），5% 噪声随探针删除消失。
- reviewer 独立注入（doc 区加 `REMOVED_CASE`）⇒ 2 条断言红 ⇒ 还原 md5 `4878a872…` 回绿。
- 同类扫描（机械扫全部 `min_rom_probe_*.py` 的「连续两条 `emit(trap…)`」）：除已删者 **0 命中**；`integ050t`（中间 5000 次循环）、`integ042t`（先显式断言 BUSY 可见）均非同类缺陷。
- 非阻断（转 `ISS-371`）：`run.sh` 的 `doc_checks_count` 与实现同源；`--soak` 用 `ls` 计数会受历史日志影响。
