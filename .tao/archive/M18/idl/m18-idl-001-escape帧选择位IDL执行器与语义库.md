# m18-idl-001: escape 帧选择位在 IDL 执行器/语义库/向量同步

**模块**：idl
**项目里程碑**：M18
**依赖**：`m18-spec-003`（SimRISC-11/IDL/Toolchain-01/contract-asm 编码真源）
**可并行分片**：否
**预估**：3–5 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务跨 IDL 执行器/语义库/向量，取 2–3× 中位）
**档位**：中改（IDL 执行语义 + 向量）
**状态**：已验证
**执行环境**：本地

## 背景

`m18-spec-003` 已把 `escape` 的编码真源改成：

- `imms18` bit1 = frame selector（0=cg5，1=cg9）；
- 合法 `imms18 ∈ {0,1,2}`，`3 ⇒ ILLI`；
- `imms20 ∈ {0,4,8}`（8=cg9/偏移 0），cg9 只允许偏移 0。

但以下消费方仍旧口径，导致 L2/向量不一致：

- `idl/tools/idl_exec.py::_op_escape` 仍只处理 cg5/旧立即数；
- `spec/IDL-ISA语义描述语言与语义库.md §4.6` 的 `cfx_escape_enter` 未含帧选择；
- `tests/inst/11-cfx/escape_ciii_cfx.S` case 13/14 仍把 `imms18=2` 当 ILLI；
- `idl/data/exec_anchor.toml` / `idl/.manifests.toml` 需随 IDL/执行器重算。

## 目标

1. `idl/tools/idl_exec.py::_op_escape`：按 `imms18` bit1 选 cg5/cg9；cg5 偏移 0/+4，cg9 仅 0；`3 ⇒ ILLI`；cg9 帧有效判据 `cfx_hart cg9 rc3 != 0`、返回 `prev_run_mode/prev_cfx_code/cause_ip` 并恢复 saved global mask（与 `DADAO-12 §5.3` 一致）；无 cg9 帧 ⇒ `CFXESC`。
2. `spec/IDL-ISA-… §4.6` `cfx_escape_enter` 签名/语义增加 frame selector；IDL 语义库版本/变更记录按需（不升 spec 版本，内容同步）。
3. `tests/inst/11-cfx/escape_ciii_cfx.S`：case 13/14 改为合法 `imms18=2` 的 cg9 路径（另加 `3 ⇒ ILLI` 新用例）；`tests/inst.yaml` 索引同步。
4. 重算 `idl/data/exec_anchor.toml`、`idl/.manifests.toml`；IDL 渲染/锚点门控回绿。

## 验收（逐条贴真实 rc）

1. `check-idl-sync`/`check-idl-parse`/`check-idl-exec-anchor`/`check-spec-codeblocks`/`check-asm-list`/`check-legality-drift`/`check-inst-macro-scope`/`check-tests-index` 全 rc=0。
2. `idl_exec` 对 `imms18=0/1/2/3` 的行为与 spec 一致：0/1 走 cg5、2 走 cg9、3 为 ILLI；cg9 帧无效/有效、返回寄存器/mask 恢复逐条覆盖。
3. `make check-inst-asm` 中 `escape` 向量全绿；新增 `3 ⇒ ILLI` 用例；`check-inst-sig`（如适用）与基线一致。
4. **可达 FAIL ≥2 路**：① 执行器仍把 2 当 ILLI ⇒ 新用例红；② cg9 帧不恢复 mask ⇒ 探针红；`cp`+md5 还原后回绿。
5. 不回归：`check-idl`/L2 相关、`make check` 与基线逐行相同；`check-knowledge-refs` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`idl/tools/idl_exec.py`、`idl/SimRISC-11.idl`（如需）、`spec/IDL-ISA-语义描述语言与语义库.md`、`idl/data/exec_anchor.toml`、`idl/.manifests.toml`、`tests/inst/11-cfx/**`、`tests/inst.yaml`、本任务书。
3. 不改 QEMU/RTL/gem5/LLVM/内核；不改版本号；IDL/生成锁用仓库工具重算。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；术语「bank = 寄存器组」。
5. 若发现 spec/契约与实现冲突，按 spec 改实现并写「待裁定」，不得反向改 spec。

## 待裁定

1. **向量层 cg9 合法路径的落点**（需主会话决定：接受现状 or 立后续任务）：`tests/inst/11-cfx/escape_ciii_cfx.S` 写不出「`imms18 = 2` ⇒ `cfx_hart cg9` 现场」的可判定断言——① Tiny 不实现 `cfx_hart`（无 cg9 现场可注入）；② QEMU `helper_cfx_escape` 仍按 `imms18 & ~1 ⇒ ILLI`（`m18-qemu-004` 未开工，本任务依赖表无该任务），写成 CFXESC/成功断言会让 `check-inst-asm`/`check-idl` 必红；③ 共享宏层 `__FAULT_GUARD` 无 `CFXESC` 种类，链例新增检查点要重生 `tests/data/inst-signature/expected.tsv`。本任务处置：向量只保留三平台可共同判定的口径（`3 ⇒ ILLI`、`imms18 = 2` 不改变 reserved 判定、SBZ 先于 CFXESC），cg9 现场语义由 `idl_exec.py --self-test`（14 条 escape 断言）覆盖。**建议 `m18-qemu-004` 合入后立任务把 case 13 改成 CFXESC 链例并重生成 expected.tsv。**

## 完成区

**测试结果**：`check-inst-asm` 272/272 镜像通过（rc=0，含 escape）；`check-idl` 272/272 例 IDL+QEMU 一致（rc=0，`parties=idl,qemu`）；`idl_exec.py --self-test` 44/44（新增 14 条 escape 断言）；静态门控 12 条 rc=0（idl-sync/parse/exec-anchor、spec-codeblocks、asm-list、legality-drift、inst-macro-scope、tests-index、case-ledger、manifests-guard、spec-changelog、knowledge-refs）；`make check` rc=2 与基线失败集**逐行相同**（KNOWN-RED：`components/chipyard/changelog.md` 里程碑节序 M[16,13,14,16]，master 既有，非本任务）；`check-milestones-fresh` rc=2 亦为基线红（A4 台账逆序 `m18-spec-003`/`m18-spec-002`，master `b5f97058` 同样；另 A1/R1 两条因本分支基线早于派单提交 `b5f97058`，合并后消失）。
**修改文件**：`idl/tools/idl_exec.py`（`_op_escape` 帧选择 + `Machine.escape` cg9 分支 + 自检 14 条）、`spec/IDL-ISA语义描述语言与语义库.md`（§4.6 `cfx_escape_enter`/`cfx_frame_valid` + 0.1.1-rc 变更条）、`tests/inst/11-cfx/escape_ciii_cfx.S`（case 13/14/19 与头部编码说明）；**生成物重算**（越界披露）：`spec/.manifests.toml`（IDL-ISA sha256）、`tests/case-ledger.tsv`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`。`idl/data/exec_anchor.toml` / `idl/.manifests.toml` **重算无差异**（md5 `9a8c3837…` / `a8a44e37…`，未改 IDL 源）。
**验收结果**：见运行期证据目录内 `run.sh`（RESULT: PASS，0 失败；`--inject` 两路可达 FAIL：`s/if imms18 == 3:/if imms18 >= 2:/` ⇒ 点名 `escape_cg9_on_non_hart_cfxesc`；删 cg9 mask 恢复 ⇒ 点名 `escape_cg9_restore_global_mask`；`cp`+md5 还原后回绿，md5 `69bec33d…` 前后一致）。
**新发现/坑**：① L2 `check-idl` 原为假绿（IDL 与 QEMU 同按旧口径判 `imms18 = 2` 为 ILLI）；本任务后 `.S` 不再断言该错口径，cg9 判别留待 `m18-qemu-004`（见待裁定 1）。② 改 `.S` 用例行必须同批重生成 `tests/case-ledger.tsv` + `tests/data/inst-signature/{expected.tsv,inputs.sha256}`（前者逐例行文本、后两者行号/输入 sha），否则 `check-case-ledger`/槽位数据漂移。③ 执行器自检放 `idl_exec.py --self-test` 是本仓唯一能覆盖「Tiny 无 cfx_hart」语义的落点（白盒注入 cg9 现场），建议后续 cfx 语义照此办理。④ 基线红两条（chipyard changelog 分节序、台账 A4 逆序）与 L2 无关，主会话收尾时需各自登记 issue（本任务未擅自改 `components/`/台账）。
**遗留问题**：无（待裁定 1 属跨任务排序，不计遗留）。

## 审阅记录

### 第 1 轮 engineer 自审

**自主逐行审查范围**：`idl/tools/idl_exec.py`（`_op_escape`、`Machine.escape`、`Cfx.cg9`、`self_test` 第 8 节）、`spec/IDL-ISA…§4.6`、`tests/inst/11-cfx/escape_ciii_cfx.S`、4 个重算生成物。
**判决**：无未修 finding；逻辑与 spec `SimRISC-11 §3` / `DADAO-12 §5.1/§5.3/§3.9` 逐条对齐；证据全部真实执行（见完成区 rc）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `Machine.escape` 形参语义由字节偏移改为 `imms18`，易被旧调用方误用 | ✅已修 | 仅 `_op_escape` 一处调用，同步传 `imms18`；docstring 写明帧选择与偏移派生 | `grep -rn "\.escape(" idl/tools` 仅 2 处（定义 + 调用）；`--self-test` 44/44 |
| F2 判定顺序：SBZ / `imms18 = 3` / reserved / 目标 / 帧 | ✅已修 | `_op_escape` 前三级 + `escape()` 后两级，与 IDL operation 语句次序逐条对照 | 自检 3 条 ILLI + 2 条 CFXESC 断言（用例 13/14/19/20 在 QEMU 亦同口径） |
| F3 cg9 分支恢复的三项（mode/prev_cfx/cause_ip）与 mask（rc4→rc8）是否齐全 | ✅已修 | 按 `DADAO-12 §3.9` 表逐项落地；`escape_num` 记在 cfx_hart 的 cg4 | 自检 4 条 cg9 断言（含 `ip` 忽略偏移）；注入②击穿 mask 一条 |
| F4 自检新增断言是否恒真 | ✅已修 | 每条都喂可达 FAIL：注入旧口径/删恢复行 | `run.sh --inject` 两路 rc=1 且点名预期检查，还原后 md5 一致回绿 |
| F5 向量层无「合法 `imms18 = 2` ⇒ cg9」判别（任务目标 3 的偏差） | ⏸延后 | 改由自检覆盖；向量留三平台共同可判定口径，GAP ⑤ 写明原因 | 见待裁定 1：QEMU 旧口径 + 宏层无 CFXESC + expected.tsv 生成物，现写必红 |
| F6 改 `.S` 连带生成物（ledger/expected/inputs）越界 | ✅已修 | 用仓库工具 `check_case_ledger.py --write`、`make inst-signature-data` 重生成并披露 | `check-case-ledger` rc=0；`sha256sum -c inputs.sha256` rc=0 |
| F7 `spec/.manifests.toml` sha256 未列入允许路径但必须随 spec 改动更新 | ✅已修 | 只更新 IDL-ISA 一行 sha256 | `check-manifests-guard` rc=0（88 文件/36 sha），`check-spec-changelog` rc=0 |

### 第 1 轮 reviewer 验收

**重跑记录（全部本人执行，退出码现场取，未采信完成区转述）**
1. 仓库根执行运行期证据目录内 `run.sh`（全量，`LOG` 指向运行期日志目录）⇒ rc=0，`RESULT: PASS（0 失败）`：静态 19 条（执行器 8 / 语义库 5 / 向量 6）、self-test `44/44`（escape 断言 `grep -c '^PASS escape_'` = **14**）、12 条静态门控全 rc=0、escape 向量 QEMU rc=0、`idl_four_way.py --only escape_ciii_cfx` rc=0、`idl_check_anchor.py --check` rc=0；脚本自带 2 路注入 md5 `69bec33d…` → 变 → `cp` 还原同值回绿。
2. `python3 idl/tools/idl_exec.py --self-test` ⇒ rc=0，`self-test: 44/44 checks passed`，14 条 `PASS escape_*`。
3. `make check-inst-asm` ⇒ rc=0，`272/272 镜像通过（链例+故障链 632 例）`；`make check-idl` ⇒ rc=0，`272/272 例四方一致（parties=idl,qemu；pending 0）`。
4. `make check` ⇒ rc=2；与本人以 `git clone` + `23b81ad5` 独立搭的基线树**逐行 diff**：唯一差异 `bullets=291→292`（本任务在 IDL-ISA `0.1.1-rc` 追加 1 条变更记录，该门两侧均 PASS），失败集两侧同为 `check-component-changelog` 的 chipyard `M[16,13,14,16]`，行数均 511、尾部 `make: *** [Makefile:198: check] Error 2` 相同。
5. `make check-milestones-fresh` ⇒ rc=2；基线与本分支均恰 1 条 `VIOLATION: A4 次序 L69 m18-spec-003 / L68 m18-spec-002 逆序`（R1 在跑号计数差为运行位置所致，两侧均无 R1 VIOLATION）。
6. `sha256sum -c tests/data/inst-signature/inputs.sha256` ⇒ rc=0（284 OK / 0 非 OK）；`spec/.manifests.toml` IDL-ISA `sha256=c59ca978…` 与本人 `sha256sum spec/IDL-ISA…md` 实测一致。
7. **独立注入 2 路（脚本未列）**：① `cg9[CG9_CAUSE_ID]==0` 判据改 `if False:` ⇒ 自检 rc=1 点名 `escape_cg9_no_frame_cfxesc`；② 删 `if imms18 == 3:` 段 ⇒ 自检 rc=1 点名 `escape_imms18_3_illi`；均 `cp` 还原、md5 回 `69bec33d…`、回绿 `44/44`、`git status --porcelain -uall` 空。

**约束核验**：`git diff --name-status master...HEAD` 恰 8 条，与完成区「修改文件」逐项一致；无 QEMU/RTL/gem5/LLVM/内核/`Makefile`/台账改动；4 个越界生成物由仓库工具重算且 `check-manifests-guard`/`check-case-ledger` rc=0、`inputs.sha256` 全 OK、`spec/.manifests.toml` 锁与实测相符；版本号未升（IDL-ISA 仍 `0.1.1-rc`，仅追加变更条，DADAO-12 未动）；执行器语义与 `DADAO-12 §5.3` 步骤 0–3、`§3.9` cg9 `rc0–rc8` 布局逐项对齐（`escape_num` 记在当前 cfx=cfx_hart、`async_cause_id` 不由 escape 清零、`rc4→rc8` 恢复）；§4.6 `cfx_escape_enter`/`cfx_frame_valid` 描述与之一致；向量 case 13/14/19/20 与 `SimRISC-11 §3`/`DADAO-12 §5.1` 一致且 IDL/QEMU 双侧同判 ILLI；完成区 8 行 ≤30；状态 `待验收`；本人注入一律 `cp`+md5，未用 `checkout/restore/stash`。

**偏差判定（目标 3「cg9 向量」）**：客观阻塞成立——QEMU `helper_cfx_escape` 实测仍 `if (imms18 & ~0x1u) ⇒ ILLI`（`components/qemu/patches/target/dadao/helper.c.patch`），Tiny `IMPLEMENTED_CFX={3,63}` 无 `cfx_hart` 现场，共享宏层无 `CFXESC` 故障种类，且 QEMU/宏层不在本任务允许路径；已由 `m18-testcases-002`（状态待开始、台账行在册、依赖 `m18-qemu-004`）承接；任务书「待裁定 1」与 `.S` GAP ⑤ 均已披露。⇒ 判 **Accepted（带 finding）**，cg9 向量延期由后续任务覆盖。

**finding（不阻断，architect 收尾处置）**：F1 `run.sh` escape 计数断言写死 `>= 12` 且注释写「12 条」，实际新增 14 条（建议现场派生或同步注释）；F2 完成区「`check-milestones-fresh` 另 A1/R1 两条」与实测不符（基线与本分支均仅 A4 一条 VIOLATION）；F3 case 14 在 QEMU 侧因旧口径同样判 ILLI（不同因同果），其「reserved 先于帧选择」判别力目前只在 IDL 侧，随 `m18-testcases-002` 一并补强。

### 提交记录（architect，WIP）

- 档位：**WIP**（状态 `待验收`，reviewer 未验收）。
- 提交：`ecdf8dcc`；先 `git merge --no-edit master` fast-forward 至 `23b81ad5`（仅 3 个台账/任务书文件，与 8 个改动文件零交集，无冲突）。
- 文件集对账：8 文件与完成区「修改文件」逐项一致；其中 `spec/.manifests.toml`（IDL-ISA 锁）、`tests/case-ledger.tsv`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}` 为仓库工具重算生成物（越界已披露；`check-manifests-guard`/`check-case-ledger` rc=0）。无 QEMU/RTL/gem5/LLVM/内核改动，无 `__pycache__`/日志/未跟踪文件。
- 门控：`run.sh` 全量 PASS（12 静态门控 + self-test 44/44 + 2 路注入 FAIL 回绿 + escape QEMU + IDL 四方差分 + anchor 幂等）；`make check` 未重跑（基线已知红，留 reviewer）。
- 锁哈希：IDL-ISA sha256 `c59ca978…` 与 `spec/.manifests.toml` 一致；`inputs.sha256` 全量 `sha256sum -c` 0 条非 OK；`idl/.manifests.toml`/`exec_anchor.toml` 重算无差异未提交。
- `--no-verify`：是（`ISS-510`）。
- engineer 偏差/待裁定（原样）：向量层未写 cg9 可判定断言（Tiny 无 `cfx_hart`、QEMU `helper_cfx_escape` 未改、宏层无 `CFXESC`、签名需重生成），cg9 判别落在 `idl_exec --self-test`；建议 `m18-qemu-004` 合入后另立向量任务。
