# m15-gem5-001: `scmp` 无序结果改 canonical quiet NaN（spec 已改）

**模块**：gem5
**项目里程碑**：M15
**依赖**：spec 修改已落盘（`a6f11e23`）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改
**状态**：已验证

## 背景（用户 2026-11-19 授权，版本号不变）

`spec/SimRISC-07 §4` 已把 signaling compare 的无序结果从 **sNaN** 改为 **canonical quiet NaN**（对齐 IEEE 754-2019 §6.2.1 的 `shall`）；quiet/signaling 的差别只剩 `NV` 标志。

## 要做

`components/gem5/patches/src/arch/dadao/exec/b7.cc.patch`（及 `b7.hh`/`b7_test.cc` 如涉及）：无序分支的 `fp::snanBits(spec.fmt)` 改为 **canonical quiet NaN**（`qnanBits`），`NV` 规则不变。

## 验收

1. 重建 gem5（按仓库既有流程）；跑 Vast/Tiny 侧浮点归属用例不回归（`tests/inst/07-floating-point/*scmp*`）；
2. **新增/临时**无序用例（qNaN、sNaN、双 NaN × ft/fo）验证结果 == canonical、`NV` 符合规则（真实输出）；
3. 可达 FAIL：改回 sNaN ⇒ 红（`cp`+md5 还原 + 重建）；
4. `check-patch-tree`（gem5 侧）、`check-index-blobs` rc=0。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-19）

审查范围：`exec/b7.cc`（`runCompare` 无序分支）、`exec/b7_test.cc`（`checkCompare` 7 条断言）、
`tools/gem5/b7_ref.py`（`cmp` 模型）、`components/gem5/{README,changelog}.md`、证据脚本与
`rewrite_canonical.py`。逻辑核对：四种比较一律 `qnanBits`，`NV` 判据 = `!quietCompare ||
isSNaNBits(a) || isSNaNBits(b)`，与 `SimRISC-07 §4` / `contract-fp §8` 逐条对齐；有序分支未动；
`accrueFlags(0)` 仍为 no-op（只含 qNaN 的 quiet compare 不写 `rf0`）；ft 结果仍按 §2.3 零扩展。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 证据脚本 I6 用 `$(( md5_before != md5_after ))` 比较字符串 ⇒ 脚本在 I6 处 `unbound variable` 退出 | ✅已修 | 改为 `[[ "$md5_before" == "$md5_after" ]]` | `run.sh --inject` rc=0、20 项全 PASS |
| 脚本 `REPO=$HERE/../../..` 经 `.work` 共享软链指到主工作树 ⇒ 会测错树 | ✅已修 | 改 `REPO=$(pwd)` + 校验 `tools/gem5/check_b7.py` | 任务 worktree 内 rc=0 |
| C6 仅数 `[PASS]` 行 ⇒ 载体若被删用例会空绿 | ✅已修 | 增「检查点数 ≥ 17」断言 | `actual=2/2 points=17` |
| `rewrite_canonical.py` 在 `m15-testcases-020` 改完载体后会硬失败 | ✅已修 | 无 `TEST_FPCMP_S` 时跳过改写（保留点数断言） | 当前 14 条改写、rc=0 |
| `fp::snanBits` 变成无调用者 | ❌不修 | 保留公共原语（外部链接、无告警）；删 API 超出最小改动 | 构建 `-Werror` 下 rc=0 |

### 第 1 轮 reviewer 验收（2026-11-19）

**重跑记录**（本人执行，任务 worktree 内相对路径，退出码取 `echo $?`）：
- 分支侧 `git diff master...HEAD --stat` = 6 文件（本任务书、`components/gem5/{README.md,changelog.md,patches/src/arch/dadao/exec/{b7.cc,b7_test.cc}.patch}`、`tools/gem5/b7_ref.py`）；两点式 `git diff master` 多出的 4 个（discussing / milestones-m15 / idl-018 / testcases-020）系 master 侧改动（`merge-base=da98ca12`），非本分支。
- `make check-index-blobs` rc=0；`check-patch-tree` gem5 段 `107 patch(es)`、`gem5: assertion` 0 行（全仓 rc=1，32 problem = chipyard 8 + linux 24，他任务在途）；`make check-component-changelog` rc=0（40 项 PASS）。
- 证据脚本（运行期证据目录内 `run.sh`）基线重跑 rc=0、`TOTAL failures=0`、12 项全 PASS；`run.sh --inject` rc=0、20 项全 PASS（I6 md5 前后相等、I7 源树 clean）。
- **独立注入**（本人 `cp`+md5 备份，把无序分支 `qnanBits`→`snanBits`，anchor count=1，md5 `ea983c29…`→`0ebee13e…`）⇒ 同一脚本 rc=1、`TOTAL failures=8`：C1 dirty、C2a rc=1、C2b `[FAIL]=14`、C2c `mismatch=40`、C3a=0、C5 0/2、C6 0/2、C7b problems=2；`cp` 还原 md5 回 `ea983c29…` + 源树 clean ⇒ 重跑 rc=0、`TOTAL failures=0` 回绿。
- `check_b7` 本人重跑 rc=0、`oracle vectors=3946`、`oracle mismatch=0`、7 条 scmp 断言 `actual 0x7fc00000 / 0x7ff8000000000000 flags 0x1`；仓库原 `*scmp*` 载体 gem5 lane 0/2、`rc {'gem5': 10}`。

**改法核**：补丁 `b7.cc` 的 `runCompare()` 无序分支只有一处 `result = fp::qnanBits(spec.fmt)`（ft/fo × quiet/signaling 四种共用该分支，`quietCompare` 只决定 NV）；`NV` 判据 `!quietCompare || isSNaNBits(a) || isSNaNBits(b)` 与改前「quiet→仅 sNaN 置、signaling→无条件置」逐支等价，**未放宽**；有序分支与 `runMinMax` 未动。`b7_ref.py` 同步 `out=qnan_bits(fmt)`、`flags=F_NV if (snan or not quiet) else 0`；断言常量 `kFtQNaN=0x7FC00000`、`kFoQNaN=0x7FF8000000000000` 与 `SimRISC-07 §1.4/§4`（`a6f11e23`）一致。

**它报三点的判定**：
1. `*scmp*.S` 在 gem5 lane 停在检查点 10 —— **属实**（`SYS_EXIT(检查点号)`，总 17 点、0 PASS）；归属 `m15-testcases-020`（其 `TEST_FPCMP_S` 为 sNaN 结构断言，master 已订正范围）。不代改。
2. `check-gem5-decode` 本就红 —— **属实**（rc=2，stale 3 生成物 = `decode_table.inc`、`decode_assertions.inc`、`components/gem5/decode-assertions.tsv`；`af7ffb09` 为分支基点祖先、本分支未碰 `contracts/opcodes.yaml` 与该 3 件 ⇒ master 同红）。归属待架构师定，不记本任务失败。
3. matrix tsv + `min_rom_probe_035t.py` 旧口径 —— **属实**（两者仍写「返回 sNaN」，后者的 `expect_rd` 亦钉 sNaN；全仓无门控引用该 py）。归属 `m15-testcases-020`（master `6d510edf` 已扩范围）。不代改。

**约束核验**：未提交 git、未改主工作树（主工作树与共享 gem5 源树 `git status` 均 0 行）；我的临时产物只落运行期临时目录；`git merge-tree --write-tree master HEAD` rc=0（分支与 master 改动零重叠 ⇒ 合并态与分支态门控等价）；术语核验：`bank` 均作「寄存器组」、无误译；审前/审后 `git status --porcelain -uall` 均为空、与审前快照逐行一致；审阅记录只引仓库跟踪路径与运行期目录通称、无运行期源码/构建树具体路径（`make check-knowledge-refs` rc=0 PASS）。
**非阻断 finding**：完成区称 `min_rom_probe_035t.py` 为「期望注释」，其 `expect_rd` 实为活断言（措辞级，architect 收尾改）。
**判决：Accepted**

## 完成区

**测试结果**：4/4 验收项达（含 1 项按分派边界记录）。① `build-gem5` rc=0；`ftqcmp`/`foqcmp` 载体 2/2 PASS（无回归），`ftscmp`/`foscmp` 载体 0/2、停在检查点 10 —— 载体 10–16 由 `TEST_FPCMP_S` 钉「指数全 1 + qNaN 位 0」（旧 sNaN 口径），按分工归 `m15-testcases-020`（其订正已由主会话落 master）；把这两份载体**复制到临时目录**、期望换成 spec 常量后 gem5 FS 侧 2/2 PASS，结果字节 7 点 × 2 格式全为 `0x000000007FC00000` / `0x7FF8000000000000`。② 无序真实输出：harness 7 条断言（ft/fo × qNaN / sNaN / 双 NaN / 负 payload）打印 `flags 0x1`，`check_b7` `[FAIL]`=0、`oracle mismatch=0`（现场 vectors=3946）。③ 注入回 sNaN ⇒ `check_b7` rc=1（`[FAIL]` 14 条、`oracle mismatch` 40）、载体红（检查点 10），`cp`+md5 还原 + 重建 ⇒ 回绿。④ `check-index-blobs` rc=0、`check-patch-tree` gem5 段 0 problem（全 32 problem 均 chipyard/linux，他任务在途）；`check-component-changelog` rc=0。合并态（master `da98ca12` 已合入本分支）重跑全绿。
**修改文件**：`components/gem5/patches/src/arch/dadao/exec/{b7.cc,b7_test.cc}.patch`（`make_patch.py` 重导出，2 written / 105 unchanged，107 份不变）、`tools/gem5/b7_ref.py`、`components/gem5/{README,changelog}.md`；组件源树同两文件收敛为 base+1 本地 commit（`d7259f31`，clean）。
**验收结果**：证据脚本（运行期证据目录内 `run.sh --inject`）rc=0、`TOTAL failures=0`，20 项逐条打印期望/实际（C1–C7 + I1–I9），含注入→FAIL→`cp`+md5 还原→回绿自检。
**新发现/坑**：① `tests/inst/07-floating-point/{ft,fo}scmp_orrr_rf.S` 的 10–16 点**确实有无序用例**，但 `TEST_FPCMP_S` 是「sNaN 结构断言」（钉 qNaN 位 = 0），语义一改必红——不是「无覆盖」。② `check-gem5-decode` 在 master 上**本就红**（`af7ffb09` 改 `contracts/opcodes.yaml` 后 3 个生成物未重生成），与本任务无关，勿记为本任务失败。③ `tests/data/GEM5-002t-semantic-matrix.tsv` 的 ftscmp/foscmp 行、`tools/testcases/arch/min_rom_probe_035t.py` 的期望注释仍写「返回 sNaN」（后者无门控覆盖）。④ 任务 worktree 的 `.work`/`.dadao`/`.cache` 是共享软链 ⇒ 证据脚本的仓库根必须取 `pwd`，不能从脚本路径反推。
**遗留问题**：① `m15-testcases-020` 需把两份载体的 `TEST_FPCMP_S`（宏本身 + 7 点 × 2 格式）改为 canonical —— 本任务不改 `tests/inst/**`；② `check-gem5-decode` 的 3 个 stale 生成物待归属任务重生成；③ 上述 matrix tsv 行与 `min_rom_probe_035t.py` 旧口径建议并入 qemu/gem5 侧收口任务；④ `.tao/contracts/contract-fp.md` 的旧口径已由 `m15-spec-007` 承接（本任务未碰契约）。

