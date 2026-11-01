# TESTCASES-068t: qemu-user OOM 修复（`-R 4G` + `flockfile-list` known-fail）

**模块**：testcases
**项目里程碑**：M10
**依赖**：QEMU-075t（诊断）
**状态**：已验证

## 背景（范围：只修 ISS-255/257 的 OOM 面）
QEMU-075t 结论：
- `setenv-oom`、`pthread_create-oom`：guest 把 VA 填满 ⇒ qemu 自身 `g_malloc` 失败 → `QEMU internal SIGTRAP`；**`-R 4G` 实测四例转绿**（静态+动态）。
- `flockfile-list`：语料自带 `malloc` 基址 4 mod 8 ⇒ guest `SIGBUS`（语料问题，**修不了**）⇒ known-fail。
- **不做**：llvm-ts/ISS-266（另立 `TESTCASES-069t`）、判据全面重构、全量夜跑。

## 改动
1. `tools/testcases/run_libc_test_user_suite.py`：
   - qemu 启动行加 `-R 4G`（`:1142` 附近）；新增 `--reserved-va`（默认 `4G`，可 `none` 关闭），说明 guest VA 限 4 GiB。
2. `flockfile-list` 记 **known-fail**（用现有 `GAP_SIGNATURES`/known-fail 机制，精确 case，附 ISS-255 指针）；**不削弱**其它断言。
3. 若 `setenv-oom`/`pthread_create-oom` 仍需特判，优先靠 `-R` 让其自然 pass；不要为过测而放宽判据。
4. issue：ISS-255（setenv-oom 修 + flockfile known-fail）、ISS-257 可关；ISS-266 不动。

## 验证（定向，分钟级；**不跑全量、不跑 llvm-ts**）
```bash
python3 tools/testcases/run_libc_test_user_suite.py --link-mode static \
  --filter 'setenv-oom|pthread_create-oom|flockfile-list' --json-out /tmp/opencode/TESTCASES-068t/static.json
python3 tools/testcases/run_libc_test_user_suite.py --link-mode dynamic \
  --filter 'setenv-oom|pthread_create-oom|flockfile-list' --json-out /tmp/opencode/TESTCASES-068t/dynamic.json
```
- 期望：setenv-oom / pthread_create-oom **pass**；flockfile-list **known-fail**；**0 blocked**。
- 回归：至少 2 个不相关 libc 用例（如 `heapsort`/`qsort`）在带 `-R` 下输出与不带一致。
- `make check` rc=0；`--help` 含 `--reserved-va`。

## 约束
- 只改 `run_libc_test_user_suite.py` + `issues.yaml` + 任务书/`milestones.md`；不改 qemu/spec/contracts/其它 driver。
- 反例注入还原用 `cp`+md5；临时目录 `/tmp/opencode/TESTCASES-068t/`；不提交。
- 无夜跑全量；定向验证即可收口。

## 完成区

**状态**：已验证

**测试结果**：通过 37/37（`.work/evidence/TESTCASES-068t/run.sh`；含注入→FAIL→`cp`+md5 还原→回绿）。定向两档 `--filter 'setenv-oom|pthread_create-oom|flockfile-list'`：static/dynamic 均 `pass=2 known-fail=1 blocked=0 fail=0`；负控 `--reserved-va none` 下 `setenv-oom` = `blocked`（rc=1）；`make check` rc=0。

**修改文件**：
- `tools/testcases/run_libc_test_user_suite.py`（qemu 启动加 `-R`；新增 `--reserved-va`；ISS-255 known-fail 基据；宿主信号记 `first_error`）
- `.tao/knowledge/issues.yaml`（ISS-255/ISS-257 → `closed`，`resolved_by: TESTCASES-068t`；ISS-266 未动）
- `.tao/knowledge/milestones.md`（068t 行 → 待验收/时间）
- `.tao/tasks/testcases/TESTCASES-068t-qemu-user-OOM修复.md`（本册）
- `.work/evidence/TESTCASES-068t/run.sh`（新增，非入库证据）

**验收结果**：
- static：`qemu guest VA: -R 4G`；`PASS setenv-oom exit=0`、`PASS pthread_create-oom exit=0`、`KNOWN-FAIL flockfile-list`（basis `ISS-255`：语料 `regression/flockfile-list.c:31` bump `malloc` + 宿主 `SIGBUS`）⇒ `blocked=0`；dynamic 同。
- 回归：`functional/strptime`（非空诊断输出）+ `functional/qsort` 带/不带 `-R` 的 stdout/stderr/rc 逐字节一致（strptime md5 `67153d0181c4f7e209d2a887d38b6c14`；qsort 空）。
- `--help` 含 `--reserved-va`（默认 `4G` = 4 GiB，`none` 关闭）；非法值 rc=2。
- `make check` rc=0（`check_issues: 1 open, 14 closed`，resolved_by 约束 OK）。
- 注入（证据脚本）：删 `-R` 启动行（md5 变、`git diff --name-only` 非空）⇒ 定向 rc=1、`blocked=2`；`cp` 还原 + md5 一致 ⇒ rc=0、`blocked=0`。

**新发现/坑**：`-R` 只解 OOM 族；`flockfile-list` 仍为宿主 SIGBUS(7)（语料 8 B 对齐），按基据登记 known-fail，未改 qemu。原 known-fail 机制只收 `fail` 行，本轮仅对 ISS-255 开放**精确** `blocked` 行（cid + 信号 + 语料标记三重校验），其余 blocked（timeout/编译/链接）不可被误升。

**遗留问题**：无。qemu 侧 `RLIMIT_AS` 虚拟化未做（当前不需要）；llvm-ts/ISS-266 归 `TESTCASES-069t`。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-27）

- 逻辑：`-R` 只进 qemu 启动行（编译/链接命令不变）；`none` 走无 `-R` 分支。ISS-255 三重校验（精确 cid / 宿主 SIGBUS(7) / 语料 bump `malloc` 标记），并加 `missed_iss255` 反向校验，防「删登记掩盖」。
- 风险：`attribute_known_fail_bases` 仅对 `blocked` 试 ISS-255，cid 不匹配立即 False ⇒ 其它 blocked 不会误升；`fail` 行仍只认 ISS-251/ADR-0030。
- 边界：宿主信号路径新增 `first_error`（仅基据/报告用，不改分类与判据）。
- 防造假：每条断言有可达 FAIL——注入删 `-R` 实测 rc=1/blocked=2，还原后 rc=0/blocked=0；回归用非空输出（strptime）对比，非「空 == 空」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 注释把 4 GiB 说成 "DADAO guest cap"（无规范依据） | ✅已修 | 改为「`-R 4G` 预留 4 GiB，形态由 QEMU-075t 实测」 | `run.sh` 37/37 回绿 |
| `CASE_NOTES` 两条旧结论（"a QEMU-side fault"）与新基据矛盾 | ✅已修 | 改为语料对齐 / `-R` 修法说明 | 两档输出 `note:` 与 `known-fail basis` 一致 |

### 第 1 轮 reviewer 验收（2026-10-27）：Accepted

**重跑（reviewer 本人执行，非采信 engineer 转述）**
- `bash .work/evidence/TESTCASES-068t/run.sh` ⇒ `EVIDENCE_EXIT=0`，`TESTCASES-068t evidence: PASS (37 checks, 0 failed)`；其中 `static/dynamic` 均 `pass=2 known-fail=1 blocked=0 fail=0`、`flockfile-class=known-fail`、`basis=ISS-255`；`invalid-reserved-va-rejected rc=2`；`without--R-setenv-blocked=1 rc=1`；`strptime` 带/不带 `-R` stdout/stderr/rc 逐字节一致且非空；engineer 自身注入→FAIL→还原→回绿全绿。
- 定向两档（脚本内）：static `discovered=367 total=3 pass=2 fail=0 known-fail=1 blocked=0`；dynamic 同计数；日志实录 `qemu guest VA: -R 4G`、`PASS setenv-oom exit=0`、`PASS pthread_create-oom exit=0`、`KNOWN-FAIL flockfile-list base=ISS-255 ... observed: qemu killed by host signal 7`（契约指针 `legality_rules.yaml:152 MALIGN` 现场行号属实）。
- `make check` ⇒ `MAKE_CHECK_RC=0`（`check_issues: 1 open, 14 closed`；resolved_by 约束 OK）。

**独立反例注入（不复用 engineer 向量）**：注入向量 = 把 `DEFAULT_RESERVED_VA = "4G"` 改 `"none"`（`cp` 备份 + md5 `efca349e…`→`e3556b35…`，非空改动）⇒ 定向 static `INJ_RC=1`、`counts: pass=0 known-fail=1 blocked=2`（setenv-oom / pthread_create-oom 均 `qemu killed by host signal 5`）⇒ **回绿**：`cp` 还原 + `md5sum -c` OK ⇒ `POST_RC=0`、`pass=2 blocked=0`。全程未用 `git checkout/restore/stash`；结束 `git status --porcelain -uall` 干净、driver md5 复原一致（快照对账通过）。

**语义/防放水核验**：① `-R` 只进 qemu 启动行，编译/链接命令不含 `-R`（日志 compile/link 行实证）；`--reserved-va` 默认 `4G`、`none` 关闭、非法值 rc=2（重跑证实）。② `attribute_known_fail_bases`：`fail` 行基据集合未变（仍仅 ISS-251/ADR-0030）；`blocked` 行只试 ISS-255，`iss255_evidence` 三重校验（精确 cid + `first_error` 含 host signal 7 + 语料三标记 + 契约 MALIGN 行）不满足即 False ⇒ 其它 blocked（timeout/编译/链接/其它信号）不可被误升；`missed_iss255` 反向校验加进 `classification_ok`。③ issues.yaml：ISS-255/257 `closed` + `resolved_by: TESTCASES-068t`；ISS-266 仍 `open` 未动（逐字核对）。④ 越界：commit `c39e6faa` 仅 4 文件（driver/issues.yaml/milestones.md/本册），未碰 qemu/spec/contracts/llvm-ts。

**Finding（非阻断，文档级）**：`CASE_NOTES` 把语料标记行写作 `src/regression/flockfile-list.c:11,30-31`，实际标记在 `:15`（buf 声明）/`:31`/`:34`（`:11` 为笔误，应为 `:15`）；不影响任何门控判据（evidence 用现场 `find_line` 取行号）⇒ 由 architect 收尾提交顺手改。

**判决：Accepted**（验收命令全绿于 reviewer 重跑；约束无违反；注入/还原纪律守住）。

