# GEM5-020t: gem5 CFXREG 目标对齐当前 monitor

**模块**：gem5
**项目里程碑**：M11
**依赖**：`QEMU-083t`（已验证；QEMU 已把 CFXREG 目标改为当前 monitor）、`SPEC-186t`（DADAO-12 §5.2 A/A1）
**状态**：已验证

## 执行环境
本地；只改 gem5 实现/补丁，不改 spec/QEMU/tests 期望。

## 背景

`QEMU-083t` 已把 `cfx2rd`/`cfx2rc` 的 `CFXREG` 目标从“被访问 cfx”改为“当前运行模式 monitor”，并同步了 arch 探针期望。gem5 仍为旧语义，导致：

- `TESTCASES-098t` 现场矩阵 14 条 `GEM5_ONLY_FAIL`，全在 `node/arch`
- `m5_perm_badcombo_cfxreg` gem5 自环超时
- 13 个 cfx/PTW/模式探针目标不符

## 目标

1. 在 gem5 的 `cfx2rd`/`cfx2rc` 非法寄存器组合路径，把 `CFXREG` 目标从 `cfxha` 改为当前运行模式 monitor（`inner_run_mode` 对应 umon/jmon/smon/hmon），与 QEMU-083t / §5.2 一致。
2. 对齐 QEMU-083t 已同步的 arch 探针语义；不改测试期望值。
3. 源树 base+1 干净；按 `docs/Process-01` 重导出 gem5 补丁；不改 QEMU/LLVM/spec。
4. 重跑 gem5 Node/Tiny 代表测试，验证 14 条 node/arch 红行转 `AGREE_PASS`。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/**`（cfx/isa/异常路径）、`components/gem5/changelog.md`、`components/gem5/README.md`（若需）、本任务书、`milestones.md`、`ISS-342` 关闭。

**不在范围内**：`spec/**`、`.tao/contracts/**`、`contracts/**`、`components/qemu/**`、`components/llvm/**`、`tests/**` 期望值、`tools/testcases/parity/**`（矩阵由 TESTCASES-098t 重生成）。

## 验收标准

1. **目标正确**：gem5 非法 `cfx2rd/cfx2rc` 组合 ⇒ `CFXREG` 进当前 monitor；`m5_perm_badcombo_cfxreg` 不再自环/超时。
2. **矩阵转绿**：`TESTCASES-098t` 重跑后 `node/arch` 14 条 `GEM5_ONLY_FAIL` → `AGREE_PASS`；`GEM5_ONLY_FAIL=0`、`DIFF=0`、`QEMU_ONLY_FAIL=0`。
3. **构建/回归**：`make build-gem5`、`check-gem5-decode`、`check_b6.py`、`make check-arch`、`make check-inst`、`make check`（L1）rc=0；源树 base+1 干净。
4. **反例可达 FAIL**：把目标改回 `cfxha` ⇒ `m5_perm_badcombo` timeout/FAIL；`cp`+`md5sum -c` 还原后回绿。
5. **范围**：无 spec/QEMU/tests 改动；完成区 ≤30 行；状态 `待验收`。

## 说明

- 以 QEMU-083t 的 10 处 `cfxha`→`env->inner_run_mode` 为参照，逐处核对 gem5 对应路径；不要只改一处。
- `CFXPERM`/`CFXMEM`/`ILLI`/`CFXESC`、合法读写、Tiny 直通 fault 不要动。
- 不改 `tests/arch/umon/expected.yaml` 等期望；QEMU-083t 已同步，gem5 只对齐实现。

## 完成区

**测试结果**：全部通过。`build-gem5` rc=0；`check-gem5-decode` rc=0（264/264+388/388+28/28+2/2）；`check_b6.py` rc=0（30/30）；`apply-series` rc=0（gem5 already applied）；`check-source-state` rc=0（gem5 HEAD=1ad69d23b130 count=1 clean=True）；`check-patch-tree` rc=0（7 components / 303 patches）；`check-arch` rc=0；`check-inst` rc=0（Node 965/970、5 deferred、skipped_profile=44；Tiny 44/44）；L1 `check` rc=0；证据脚本 rc=0（29/29 PASS）。
**修改文件**：`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch`（`make_patch.py` 重导出：1 written / 96 unchanged）；`components/gem5/changelog.md`；`components/gem5/README.md`；`.tao/knowledge/milestones.md`（状态 待验收）；本任务书。
**验收结果**：`node_cfx.cc` 的 10 处（read 4 + write 6）`nodeCfxRaise(..., CauseCfxReg, cfxha, ...)` → `s.runMode`；终态 `CauseCfxReg+s.runMode`=13（3 处为 HEAD 既有：`nodeTrap`/read/write 的 `ci<0`）、`+cfxha`=0；`CFXPERM`/`CFXMEM`/`ILLI`/`CFXESC`、合法读写、Tiny `machineFault(CFXREG)` 未动。`m5_perm_badcombo_cfxreg`（gem5）：修复前 TIMEOUT，修复后 `expected=83 actual=83 exit=83 cause=CFXREG`。`run_parity.py --profiles node --scopes arch`：total 269 → agree_pass **249**（前 235）、gem5_only_fail **0**、diff 0、qemu_only_fail 0、blocked 20；`TESTCASES-098t` 的 14 条 red 行逐条核对为 `AGREE_PASS`。反例：目标改回 `cfxha` ⇒ 注入构建 rc=0、复现用例 FAIL（rc=1）、044t probe FAIL（exit 0x45→0x87）；`cp`+`md5sum -c` 还原 + 强制重编后复现用例 PASS（rc=0）、源树干净。
**新发现/坑**：① 注入还原后 `make build-gem5` 曾未重编 `node_cfx.o`（SCons 陈旧签名），"还原后仍红"；证据脚本改为删 `node_cfx.o` 强制重编（`force_build`）。② 自环用例的 `run_m5_e2e` 只杀 shim，gem5 孙进程继续写 `-d cpu` trace；`TESTCASES-098t` 的一个 orphan 已写满磁盘（单文件 369GB，已 kill）；证据脚本用 `prlimit --fsize=128MiB` 限流并在注入后 `pkill`。为恢复构建删除了该 orphan 的 scratch log（098t 的 运行期 scratch trace；matrix/json/md5/logs 保留）。
**遗留问题**：`ISS-342` 关闭与 `milestones.md` 终态 `已验证` 归主会话；`TESTCASES-098t` 矩阵全量重生成由其重跑（本任务只做 node/arch 局部复跑）。未改 `spec/**`/`contracts/**`/QEMU/LLVM/tests 期望。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 需逐处对齐 QEMU-083t 的 10 处（4 read + 6 write），不能只改一处 | ✅已修 | `nodeCfxRead` 4 处、`nodeCfxWrite` 6 处 target→`s.runMode` | 补丁 diff 恰 10 行；source/patch 计数 13/0；14 case AGREE_PASS |
| F2 避免误改 `CFXPERM`/`CFXMEM`/`ILLI`/`CFXESC`、合法路径与 3 处既有 `ci<0` | ✅已修（限定） | 仅替换 `CauseCfxReg, cfxha` 精确串；permission/illi/esc 保持 | `grep CauseCfxReg, cfxha`=0；check-arch/check-inst 全绿；Tiny 未动 |
| F3 证据脚本把"注入后的预期 FAIL"计为脚本失败 | ✅已修 | 新增 `run_probe_fail`，注入分支按 rc≠0 判 PASS | 证据脚本 29/29 PASS |
| F4 cp 还原后 SCons 未重编，可能假红/假绿 | ✅已修 | `force_build` 先删 `node_cfx.o` 再构建 | 还原后复现用例 PASS；`.o` mtime 更新 |
| F5 自环 trace 无限增长 + scratch 目录触发 L1 A3 | ✅已修 | `prlimit --fsize=128MiB`、`pkill` 清理、work dir 移到仓库外 | L1 rc=0；证据 rc=0；无 orphan |
| F6 磁盘写满事故 | ✅已处置 | kill orphan gem5、删除其 369GB scratch cpu.log | df 375G 可用；构建恢复 |

判决：全部 finding 已修，状态 `待验收`。

#### 第 1 轮 reviewer 验收

**判决：Accepted**（2026-11-05；全程未 commit/push；审查前后快照对账一致）

**重跑记录（reviewer 亲自执行，真实 rc）**：`check-source-state` rc=0（gem5 HEAD=`1ad69d23b130` count=1 clean=True）；`check-patch-tree` rc=0（7 components / 303 patches）；`python3 tools/infra/make_patch.py gem5` rc=0 → **0 written / 97 unchanged**、97 个补丁 md5 前后无变化；`make build-gem5 JOBS=32` rc=0；`check-gem5-decode` rc=0（264/264+388/388+28/28+2/2）；`check_b6.py` rc=0（30/30）；`check-arch` rc=0（末行 `check-arch: PASS`、FAIL 计数 0）；`check-inst` rc=0（Node **965/970**、5 deferred、skipped_profile=44；Tiny **44/44**）；L1 `check` rc=0（`repository checks (L1): PASS`）；`apply-series` rc=0（gem5 already applied）。长输出留 运行期日志。

**关键验收**：`run_m5_e2e --only m5_perm_badcombo_cfxreg --profile node` rc=0 → `expected=83 actual=83 exit=83 cause=CFXREG`（83=0x53）；`run_parity.py --profiles node --scopes arch --json` rc=0，**我独立统计 JSON**：total **269** = AGREE_PASS **249** + BLOCKED_SIDE **20**，无第三种 verdict ⇒ gem5_only_fail=0、diff=0、qemu_only_fail=0；`former-red.txt` 14 条逐条核对 **14/14 AGREE_PASS**（均 profile=node/scope=arch）。旁证（非我产出，采信）：TESTCASES-098t 全量 `matrix.json` 2586 行 red=0。

**反例注入（reviewer 独立做，非 engineer 自检）**：`cp`+md5（`dcbc77a5…`）→ **只改 1 行**（`node_cfx.cc:1018`，cg==10 time 写路径）`s.runMode`→`cfxha`，`git diff` 恰 1 行、计数 13→12 / 0→1 → 重跑**同一** `run.sh` → **rc=1，6 项 FAIL**（`check-source-state` rc=2、`check-patch-tree` rc=2 断言⑦+⑥、source 计数 12/1、末态 source dirty）→ 用注入后二进制补跑 13 条探针：12 绿 **1 红**（`i050t/time_ro_cfxreg` rc=1 `exit exp=0 got='0xe1'`）⇒ 行为面可达 FAIL → `cp` 还原 + `md5sum -c` OK + 源树 clean + 13/0 → 删 `node_cfx.o` 强制重编 rc=0（gem5.opt 735410704→735421032）→ 重跑 `run.sh` → **rc=0，29 PASS / 0 FAIL**。全程未用 `git checkout/restore/stash`。

**约束逐条核验**：① 10 处 ✓——补丁 diff 恰 10 对 +/-（read 4：pmem/time/hart/cfxRegPtr；write 6：pmem/time/hart/cg7/cfxRegPtr/tlb），与 QEMU-083t 的 10 处**同序同路径**逐一对应；源树 `CauseCfxReg+s.runMode`=13、`+cfxha`=0；`CFXPERM`/`CFXMEM`/`ILLI`/`CFXESC`、合法读写、Tiny 直通未动（diff 无其它行）；入口 `ci<0` 三处（865/932/998）不在 diff 内。② 源树 base+1 干净、补丁幂等、两门控 rc=0 ✓。③ 构建/回归全 rc=0 ✓。④ 关键验收数字与现场一致 ✓。⑤ 反例可达 FAIL + 还原回绿 ✓。⑥ 范围 ✓——工作树仅 5 个 M（补丁/changelog/README/任务书/milestones），`spec`/`qemu`/`llvm`/`tests`/`tools`/`contracts` diff **为空**，`ISS-342` `status: open` 未关闭。⑦ 事故 ✓——`df /mnt/tao` **374G 可用**、全盘 >5G 文件 **0**、**无 gem5 进程**、最大 `*.cpu.log` 13MB；`run.sh` 已含 `prlimit --fsize=128MiB` 与 `pkill`（142/190 行）。⑧ 体例 ✓——完成区 9 行（≤30）、无绝对运行期路径。

**快照对账**：审查前后 `git status --porcelain -uall` 同为 5 个 M，5 文件 md5 逐一相同（补丁 `697aab2c…` 等）；gem5 源树 clean @`1ad69d2`；`components/gem5/patches` 97 文件 md5 前后无变化。

**Findings（均文档级，不阻断，交 architect 收尾改）**：
- **F1** 任务书「范围」把「`ISS-342` 关闭」列为在范围内，完成区「遗留问题」又写「归主会话」，`issues.yaml` 仍 `open` —— 两处口径不一致。
- **F2** 完成区「新发现/坑」写 运行期 scratch trace（具体运行期证据路径），与「任务书不写运行期路径」口径略有出入。
- **F3** 完成区写 `make_patch.py`「1 written / 96 unchanged」，我重跑为「0 written / 97 unchanged」（幂等稳态；「恰 1 份改」已由 `git diff` 证实，非矛盾）。
- **F4（建议）** 证据脚本第 2 步（注入前复现/探针）用的是**既有二进制**、未先 `force_build`；单点源改动若未重编则行为面不立即红（本次靠静态计数与 `check-source-state` 判红）。建议第 2 步前加一次 `force_build`。

#### 收尾（architect，2026-11-05）

- F1：`ISS-342` 在本收尾关闭（`resolved_by: GEM5-020t`），与任务书范围一致。
- F2/F3：运行期路径已改为通用描述；`make_patch.py` 首轮 1 written/96、reviewer 复跑 0/97 属幂等稳态，均以 `git diff` 恰 10 行为准。
- F4：证据脚本第 2 步未先 `force_build` 的建议记入遗留，不阻断本任务。
- 判决 Accepted，状态置 `已验证`。
