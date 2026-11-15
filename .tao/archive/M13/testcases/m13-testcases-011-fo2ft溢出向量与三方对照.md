# m13-testcases-011: `fo2ft` 溢出按 IEEE 舍入模式（向量与三方对照）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-002` + `m12-chipyard-025` + `m13-qemu-005` + `m13-gem5-007`（三实现都要先改完，本册才能做三方对照）
**可并行分片**：否（共享 `tests/inst/fp/`）
**状态**：已验证

## 背景（共同，5 个子任务共用）

用户 2026-11-12 定规则（`MEMORY.md`）：**浮点差分一律以 IEEE-754 2019 为准**。

**条款**：`fo2ft` 溢出。IEEE 754-2019 §7.4：`RNE`/`RUP` ⇒ ±Inf；`RTZ`/`RDN` ⇒ ±最大有限；均置 `OF|NX`。现行 spec/实现恒 ±Inf。

## 本任务目标（只改测试向量）

1. 在 `tests/inst/fp/` 的对应册补/改 `fo2ft` 溢出用例：
   - 四档舍入 × 正/负 × （轻微溢出、严重溢出）≥ 8 例
   - 每例期望值**独立派生自 spec 定稿 + IEEE 条文**，不得从任何实现反推
2. 让这些例进入**三方对照**（chipyard == QEMU == gem5），不再留 model-only。
3. `spec_cite` 写到 `SimRISC-07` 的具体条目（改后的条目）+ IEEE 754-2019 §7.4。

## 非范围

- 不改实现（三个实现各有独立任务）
- 不改其它 FP 指令的向量

## 验收标准

1. 新增/修改例数按现场统计给出（分四档列出），`validate_vectors` rc=0
2. `check-inst`（Vast/Tiny）rc=0；`check-tests-index` rc=0；`check-case-ledger` PASS
3. 三方一致：chipyard == QEMU == gem5 逐字节；若某平台暂缺，明确写「缺哪一平台、原因」而不是静默降级
4. **可达 FAIL 注入**：把某例期望改回「恒 ±Inf」⇒ 该例必须红（证明断言能抓住旧行为）
5. 273 例 md5 不变
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- 向量册由生成器产出时**禁手改 YAML**（沿用 `m13-testcases-010` 的做法）。
- `.work` 必须软链（`ISS-389`）。

## 硬约束（子代理必读）

1. 独立 `git worktree` 作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

**自主逐行审查**（`tests/inst/fp/convert.yaml` 新增 29 例全文、`tools/chipyard/fp_sweep.py` 两处、`tools/chipyard/fp_unit/unit_run.py` 一处、`tests/case-ledger.tsv`、证据脚本 `oracle.py`/`check_matrix.py`/`gem5_probe.py`/`inject.py`/`run.sh`）：重点核「期望值是否独立派生」「动态档 `rf0` 预置是否正确」「注入是否可达 FAIL 且可还原」「是否越界改文件」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 矩阵审计按输入位型分类 ⇒ 若某格输入被改，该格会**静默退出**审计 | ✅已修 | `check_matrix.py` 增「非矩阵 fo2ft 用例须恰为 1 个（下溢对照）」+ 重复格检测 `(输入, imm6, rf0 码)` | A 段现场 30 格、对照 `[11]`、重复 0 |
| F2 `oracle.py` 对 tiny/次正规输入会算出非 f32 可表示值（静默错算） | ✅已修 | 显式抛 `TinyInput`（矩阵不涉 tiny）；`f32_bits` 补次正规/零 | 与 `fp_ref(force_inf=False)` 15 例 0 差 |
| F3 动态档 6 例 `(输入, 编码字)` 相同（仅 `set.w` 预置不同），易误判重复 | ✅确认非重复 | 不改 | 三元组唯一；`rf0[33:32]` 四码各 2 例 |
| F4 `fp_sweep.cases_cvt_ff` 与 `fp_unit/unit_run` 仍 pin「溢出恒 ±Inf」，与定稿 spec 及 RTL 相反（`m12-chipyard-025` 的代码改动未落 master） | ✅已修（越界披露） | `force_inf_on_overflow` 由 `True`→`False`（签名不变）；docstring 改按 §1.4 | `cvt_ff` 27 例核上逐字节 0 差（改前 3 格必红）；单元台 400 例 `TOTAL failed=0`（改前 `oracle-diff=66`） |
| F5 用 `git diff --name-only` 证「非空注入」不可靠（本任务 YAML 本就未提交） | ✅已修 | 改「注入前后 md5 不同 + 被退役期望计数 +1」 | G 段两条 PASS（md5 different；9 = 8+1） |
| F6 C2 段取数一行混用 grep 重定向 | ✅已修 | 改纯 `python3 -c` 读 json | C2 段现场 27 |
| F7 调试临时件落 worktree `scratch/` | ✅已清 | 删除 | `git status -uall` 仅 4 个改动文件 |

**自决**：`tests/inst/fp/convert.yaml` **无生成器**（`check-generator-sync` 的六册不含它，`--check` 也不覆盖）⇒ 本任务直接编辑该册；`tests/case-ledger.tsv` 是生成物，只能 `check_case_ledger.py --write`。

**判决**：finding 全部处置完毕，状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-12）

**重跑（命令 → 我方真实输出/退出码；长输出存运行期日志目录，文件名前缀 `m13-testcases-011-reviewer-`）**
1. `bash .work/evidence/<任务ID>/run.sh --inject`（`UNIT_BIN`=当前共享 RTL 的单元二进制 md5 `44b7d4ae`）→ **`RUN_RC=1`、`PASS=33 FAIL=1`**；唯一红 = C3 `fp unit bench rc`（`TOTAL failed=16`，全在 `qcmp ft/fo`，同轮 `f2f fo2ft 400 例 oracle-diff=0`）。其余 33 项与完成区逐条同值：QEMU `44 total/44 passed`、核 `31/31`、同镜像 QEMU `31/31`、gem5 `31/31`、三方拼接 `cmp` `496 B` 0 差、`cvt_ff` 27 例 0 差、`1085 total/1080 passed/5 deferred` + Tiny `44/44`、index `244`、ledger `2114`、validate `156/156·723`、273 md5 `2d4d94651346ef673c5a855e024c1489`、脚本自带注入 17 号格 QEMU/核双红→`cp`+md5 还原双绿。
2. 同脚本换 `UNIT_BIN`=025 的（12:56 构建）→ **`RUN_RC=0`、`PASS=34 FAIL=0`**，复现完成区声明；两轮逐行仅 C3 一项不同。
3. C3 红根因（我方定位，非本任务）：`tools/chipyard/fp_ref.py:935 cmp_exact` 仍「quiet 恒不置 NV」（master 同款），与 IEEE 裁定（`m13-qemu-004`）及 master 补丁 `Mux(io.signaling, unordered, rawA.isSigNaN || rawB.isSigNaN)` 冲突 ⇒ 用当前共享 RTL 的单元二进制必红 16 格；该同步明写在 `m12-chipyard-024` 任务书第 2 条（在途）。`git diff db8a7e1c master` 中 qcmp/`cmp_exact` 区域零差异 ⇒ 非本任务引入。
4. 独立复算（reviewer 自写 struct+Fraction 无界舍入，不 import 任何 oracle/实现）：矩阵 **30/30 格 `yaml == mine`**；分布 `sev10/mild10/exact2/dyn8` + 下溢对照 1（fo2ft 共 31、册 15→44、新增 29 = 9+10+2+8）；4 格 mild 仅 `0x10`、14 格结果为 ±ft_max，与 `check_matrix` 现场打印一致（其断言为下限 4/6，计数现场派生、未写死）。
5. 自选注入（与脚本不同格）：「恰为 `ft_max`」格（idx14）`rd6` 加 OF ⇒ md5 `2f562b10…`→`2e07a288…`；QEMU `Result: FAIL` rc=1；核上 `cmp` 差 byte16（实测核 `7fc00000` vs 注入期望 `7fc00004`）；`cp`+`touch` 还原 md5 回 `2f562b10…`、QEMU rc=0、核上 `cmp` rc=0。
6. 门控亲跑：`make -s check-modules` → **rc=0**（`module checks (L2): PASS`）；`make -k check` → **rc=2、5 红**（`check-patch-tree` 6 条=chipyard 4+qemu 2、`check-knowledge-refs` 2 条全他任务、`check-milestones-fresh` 1 条=`m12-chipyard-026` 有 worktree 未入台账、`check-run-artifacts` 57 条本任务 0、`check-temp-dirs` 5 条本任务 0）；主工作树 master 上 `check-patch-tree` rc=0（333 patches OK）。
7. `unit_run` 改前口径复现（临时树把 `op23 force_inf` 翻回 `True`）→ `oracle-diff=66`、`TOTAL failed=66` ⇒ 完成区「改前 66」属实。

**约束核验**：验收 1–6 全过（1 现场分档统计+`validate_vectors` rc=0；2 `check-inst`/`check-tests-index`/`check-case-ledger` rc=0，5 deferred 恰为既有 C-27 `reg-cond-assign.yaml[15..19]`；3 三方 496 B 逐字节 0 差、无缺平台；4 可达 FAIL 脚本与我方各一次；5 273 md5 不变；6 完成区 19 行 ≤30、无运行期绝对路径、4 项+本任务书与 `git status` 一一对应）。硬约束 1–8 守住：仅 5 文件、验收前后 md5 逐一相同、HEAD 仍 `db8a7e1c` 未 commit、`.work` 软链、计数现场值、全程本地（未占 207/208）；环境监视 186 采样全程 `dirty=0`、`WumingFP.scala md5=58d58776`、sim mtime 不变。

**非阻断 finding（交 architect）**：① **合并须以 026 为准**：本分支 `fp_sweep.py`/`unit_run.py` 仍给 `f2f_exact` 传第 7 参 `force_inf=False`，026 已改 6 参并删除该概念 ⇒ 两文件必冲突，**取 026**（本任务的 force_inf 改动作废，docstring/`QEMU_GROUPS` 注释可择留）；向量 `convert.yaml`/`case-ledger` 与 026 无冲突。② 完成区「新发现①②/遗留」已被 026（16:50 合入）解决（补丁 `forceInfOnOverflow`=0、`cvt_ff_ovf`/ovf 组已回 master），建议收尾改写。③ 完成区「L1 4 红」我方现场 5 红（多 `check-milestones-fresh`，属 026/主会话）；`check-patch-tree` 实测 6 条（完成区只列 chipyard 4 条）。④ 完成区只写「附 `UNIT_BIN`」未记路径/md5 ⇒ C3 不可复现（我方两二进制分别得 33/1、34/0），建议补记。⑤ 期望块由 `.work/evidence/<任务ID>/gen_block.py` 渲染，该脚本仅在 gitignored 的 `.work` ⇒ 建议随产物落 `tools/testcases/` 或在任务书明确「本册手维护」。

**判决：Accepted**（工程师达标；最终接受由 architect 终审）。

## 完成区

**测试结果**：一键证据 `.work/evidence/<任务ID>/run.sh --inject`（附 `UNIT_BIN`）→ `PASS=34 FAIL=0`、`RUN_RC=0`。
**修改文件**（`git status -uall` 对账，4 项）：`tests/inst/fp/convert.yaml`、`tests/case-ledger.tsv`、`tools/chipyard/fp_sweep.py`、`tools/chipyard/fp_unit/unit_run.py` + 本任务书；无其它改动/无残留。
**验收结果**：
- 新增 **29 例**（册 15→44）：严重溢出 10（5 档 × 正负；RTZ 正为既有例，仅改本格 `spec_cite`）、轻微溢出 10、恰为 `ft_max` 2（RNE 正负）、动态 8（`rf0[33:32]` 00/01/10/11 × 正负）；30 格全部与独立 oracle 一致（`severe 10 / mild 10 / exact 2 / dyn 8`，现场统计）。
- 三方对照：chipyard 31/31（共享源树 RTL，见新发现②）、QEMU 同镜像 31/31、gem5 31/31；三者 16 B/例 拼接字节 `cmp` **0 差**（496 B）。gem5 侧 = `exec/b7.cc`+`fp_soft.cc` 的 probe（`check_b7` 自身 rc=0、3998 向量 0 差）。
- 可达 FAIL：把「轻微溢出 RTZ 正」的期望改回 `+Inf` ⇒ 该例 QEMU `Status: FAIL`、核上该格 mismatch；`cp`+`touch`+md5 还原（`2f562b10…`）后两方回绿；注入前后 md5 不同、退役期望计数 8→9→8。
- 门控：`validate_vectors`（156/156、723 例）、`check-spec-cite-targets`、`check-tests-index`（244）、`check-case-ledger`（2114）、`check-inst`（Vast `1080/1085`+5 deferred、Tiny `44/44`、载体 26 册）、L2 `check-modules` rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变。
**新发现/坑**：
① **`m12-chipyard-025` 的代码改动未落 master**（合入 `be447dbc` 只带任务书）：`cvt_ff_ovf` 38 格组、`fp_ref` 去 force_inf、`unit_run` ovf 组均缺；本任务按 spec 最小修了两处调用方（`fp_sweep`/`unit_run`）。
② **RTL 补丁与共享源树不一致（P1，需 chipyard 任务处置）**：仓库内 `WumingFP.scala.patch` 仍有 5 处 `forceInfOnOverflow`（`fo2ft` 传 `true` ⇒ 恒 ±Inf），共享源树 0 处（025 已删并编入本次所用的 sim）。⇒ 本任务 chipyard 侧的 31 例实测用的是共享源树 RTL（合 §1.4）；**fresh checkout 重建 master 会在 14 格上红**，`check-patch-tree` 4 条红即此因。修复 = 从共享源树重导 chipyard 补丁（实现改动，本任务范围外）。
③ 轻微溢出在取最大有限值的格**只置 NX**（无 OF）——§1.4 判据「无界指数舍入后 > `ft_max`」的直接推论；矩阵 4 格为此形。
④ `fo2ft` 的 f32 在 `rd5` 高 32 位（`st.t`+`ld.o` 惯例），gem5 `W rf` 在低 32 位，逐字节比较须移位对齐。
⑤ `convert.yaml` 无生成器 ⇒ 本任务手编该册；台账须 `--write` 重生成（生成物禁手改）。
**遗留问题**：
- **需 chipyard 任务重导补丁**（见新发现②）：否则三方对照的 chipyard 侧不可从 master 复现；`cvt_ff_ovf` 38 格组与 `unit_run` ovf 组亦待补回。
- L1 `make -k check` rc=2：4 红均为他任务/共享源树（`check-patch-tree` 4 条 chipyard `WumingFP*`、`check-knowledge-refs` 2 条、`check-run-artifacts` 57 条他人日志名、`check-temp-dirs` 5 个陈旧目录），本任务无命中。
- `ISS-401`/`ISS-404` 的两处过时表述已改（`convert.yaml` 头注释、`fp_sweep` 的 `QEMU_GROUPS`/`cases_cvt_ff` 注释），台账关闭归主会话。

#### 收尾（architect，2026-11-12 18:17）

- reviewer **Accepted**：**三方真逐字节一致**（chipyard 31/31、QEMU 31/31、gem5 `mismatches=0`，496 B `cmp` 0 差，取自实测输出而非期望对期望）；186 次环境采样全程 `dirty=0`。
- **独立复算 30/30 格**（自写 struct + Fraction 无界舍入）：`sev10 / mild10 / exact2 / dyn8` + 下溢对照 1 ⇒ `fo2ft` 31 例、册 15→44（新增 29）；4 格 mild 仅 `0x10`。
- `check-inst` rc=0（Vast 1085/1080/0 failed/5 deferred、Tiny 44/44、载体 26 册）；5 deferred 恰为既有 C-27；273 md5 不变；`validate_vectors`/`check-tests-index`/`check-case-ledger` rc=0；**L2 rc=0**。
- **合并处置**：本分支 `fp_sweep.py`/`unit_run.py` 仍传 `f2f_exact` 第 7 参，而 `026` 已改为 6 参 ⇒ **以 026（master）为准**，这两文件取 master 版；`convert.yaml`/`case-ledger.tsv` 无冲突保留。
- 时序说明：用当前共享 RTL 跑 `run.sh` 会红 C3（`qcmp`），因 `m12-chipyard-024` 尚未合入；用 025 时段二进制 `PASS=34 FAIL=0` ⇒ **时序问题、非本任务缺陷**。
- 文档级（转 `ISS-408`）：完成区「L1 4 红」实为 5 红、`check-patch-tree` 6 条；`UNIT_BIN` 路径/md5 未记；`gen_block.py` 只在 `.work`（应随产物落 `tools/testcases/` 或注明本册手维护）。

