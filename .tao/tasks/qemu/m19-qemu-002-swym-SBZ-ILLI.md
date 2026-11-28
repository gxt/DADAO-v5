# m19-qemu-002: QEMU 侧 `swym` 的 SBZ/ILLI 功能语义

**模块**：qemu
**项目里程碑**：M19
**依赖**：`m19-spec-001`、`m19-qemu-001`、`m19-testcases-001`
**可并行分片**：否
**预估**：2–4 h
**档位**：小改
**状态**：已验证

## 背景

`m19-spec-001` 定了 `swym N`：`N = immu18[11:0]`，`immu18[17:12]` 为 SBZ、非 0 ⇒ `ILLI`；总时延 `1 + N`。

`m19-qemu-001` 只迁移了几何与装载，**没有**实现这条功能语义：QEMU 的 `trans_swym_oiii_imm` 仍是无条件 NOP，高位非零也照常执行。`m19-testcases-001` 的完整载体因此在 QEMU 上 `rc=12`（4 条 `ILLI` 用例全部落空），其功能子集（去故障例）三平台 88 B 签名逐字节一致。

QEMU 不承担周期（`NOP` 时延保持），但 **SBZ/ILLI 是功能维度**，参考模型必须与 spec 一致，否则三平台一致性没有基线。

## 目标

1. 在 QEMU 的 `swym` 译码/执行路径加入 `immu18[17:12] != 0 ⇒ ILLI`（与被删的 `fence`/`ret` 同类静态判据的风格一致），非法时不产生任何副作用。
2. 保持 `swym N` 合法编码仍为 NOP（QEMU 不做 1+N 时延）。
3. 同步 QEMU 侧解码表/断言（如 `insn.decode` 或 `check_qemu_trans` 的非法用例）与组件 changelog/README。
4. 不引入新补丁文件；只改既有补丁（`target/dadao/insn_trans/*`、必要时 `helper.c`）。

## 验收（逐条贴真实 rc）

1. `make build-qemu` rc=0；`make check-qemu-trans`（或等价）rc=0，含高位非零 ILLI 用例。
2. `m19-testcases-001` 的完整载体（含 4 条故障例）在 QEMU 下 rc=0；签名流与 gem5/chipyard 的 88 B 逐字节一致。
3. **可达 FAIL ≥2 路**：① 去掉 SBZ 检查 ⇒ 4 条故障例全落空、rc≠0；② 把合法 N 也判 ILLI ⇒ 功能例红；均 `cp`+md5 还原回绿。
4. `check-patch-tree` qemu 段 0 problem（须在共享源树同步后）；`check-component-changelog` rc=0。
5. 不改 gem5/chipyard/testcases 资产；版本号未升。

## 约束

独立 `git worktree`；**不提交 git**；只动 `components/qemu/**` 与必要门控；不接板；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` 全段（A–D）**PASS 36 / FAIL 0**（rc=0；A 16 / B 15 / D 5）；`run.sh --inject`（A–D+C）**PASS 56 / FAIL 0**（rc=0；C 段 20/0）。
**修改文件**：`components/qemu/patches/target/dadao/insn_trans/trans_ctrl.c.inc.patch`（`trans_swym_oiii_imm`：先判 `hb = immu18[17:12] != 0` ⇒ `gen_exception_illegal`（译码期、无副作用，与 `fence`/`ret` 同形），合法 `swym N` 仍 NOP；`@@` 新增行数 561→573、blob `07af472`→`cac2028`）、`components/qemu/changelog.md`（M19 追加 `m19-qemu-002` 一条）。补丁份数 69 不变，未新增补丁文件。
**验收结果**（真实 rc）：`make build-qemu` **0**；`tools/qemu/check_qemu_trans.py --strict` **0**（263/263、orphan 0）；`check_decodetree_repro.py` **0**（`insn.decode` 未改，seed0 两次一致）；`check_patch_tree.py` **qemu 段 0 problem**（**全仓 78 problem 属共享源树并发态基线红**，返工时点现场派发：linux 50 / chipyard 14 / llvm-project 4 / musl 4 / picolibc 4 / gem5 2；脚本直跑 **rc=1**、`make check-patch-tree` 同一 recipe 报 **rc=2**——make 把 recipe 失败统一记为 2，故判据只取「qemu 段 0 条 assertion」，不取全仓 rc）、`--source-state` qemu **OK**（HEAD `b1d4f0c`、clean、`base+1`）；`check_component_changelog.py` **0**；`semantics_gate --form-check` **0**；`check_legality_invariants`/`check_legality_drift` **0**。载体 `tests/inst/12-misc/swym_oiii_imm.S` **完整镜像（链例 11 + 故障例 4）** 在本次构建的 `qemu-system-dadao`（md5 `c5a46ef7…`）+ 新 Tiny bootrom（`f8ef553e…`）上 **rc=0**、**88 B** 签名 `79893035…`，与 gem5/chipyard 参考流 `cmp` 逐字节相同；同册 28 个载体 **28/28** 绿（邻居回归）。**无 `check-qemu-trans` make 目标 ⇒ 等价物 = `check_qemu_trans.py --strict` + `check_decodetree_repro.py`，「高位非零 ILLI 用例」由载体 4 条故障例在 QEMU 上实跑覆盖。**
**可达 FAIL 2 路**（`cp`+md5 还原后均回绿）：① 去掉 SBZ 检查 ⇒ 4 条故障例落空：`[FAIL] swym_oiii_imm.S … {'qemu': 0} B / rc {'qemu': 12}`、载体 rc=1；② 合法 N 也判 ILLI ⇒ 第 3 例 `swym 1` 触发意外 ILLI、hmon 返回默认地址成环（载体 rc=1、QEMU **rc=-2** 超时、0 B）。
**新发现/坑**：① `check_qemu_trans` 只做 `trans_*` 存在性双向 lint，无非法用例位；「SBZ ⇒ ILLI」只能由 `.S` 载体实测证明。② 不能在 `insn.decode` 写死 hb 零位：decodetree 未匹配会落成 **UNDI(0xF9)**，与 spec 的 **ILLI(0xF8)** 不符，故判据必须留在 `trans`。③ 共享 `llvm` 写者（`build-mc-lite`）会让 `run_inst_tiny` 的 reader-guard 以 rc=75 拒绝，证据脚本按 15 s×40 次重试并打印次数（本次均 1 次即得）；`build-qemu` 只声明 qemu 组件，不受该写者影响。④ 注入②的红是**超时**（rc=-2）而非 guest 退出码：链例内意外 ILLI 的返回地址是默认值，hmon 环回（既有行为，非本次引入）。
**遗留问题**：无。`make check-inst-asm` 全量重跑属 integ 收口（依赖几何迁移与安装根），本任务判据 = swym 完整载体 + 同册 28/28。

## 审阅记录

### 第 1 轮 engineer 自审

依据：`spec/SimRISC-12 §2`（SBZ/ILLI）+ `.tao/contracts/contract-isa §13.1` + `contracts/legality_rules.yaml: encode_sbz`；逐行读补丁新增块、`insn.decode` 字段映射（`%hb 12:6`、`@misc`）、`insn_trans` 同文件对比（`fence`/`ret`），并核对证据脚本每条断言的 FAIL 可达性。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `a->hb` 是否确为 `immu18[17:12]` | ✅已核 | 读 `insn.decode`（`%hb 12:6`、`@misc`）+ 与 `trans_fence_ciii_cfx`/`trans_ret_riii_ra` 同一取法比对 | A1b/A1c 绿；4 条故障例（H=0x1/0x20/0x3F/0x20+合法低位）实跑 ILLI 且 pad 核对通过 |
| F2 非法路径是否产生副作用 | ✅已核 | 判据置于任何 TCG 生成之前；`gen_exception_illegal` 内部设 `DISAS_NORETURN` | 故障例 guest rc=0（pad 核 one-hot cause）；注入②证明位置正确 |
| F3 手工改补丁后 `@@` 计数/blob 头易错（2026-10-02 事故同型） | ✅已修 | 按实际 `+` 行数重算 573；`git hash-object` 重算 `cac2028` | `apply_series.py --component qemu` 重放成功（69 applied）；A2a/A2b md5 一致；`check-patch-tree` qemu 0 problem |
| F4 C1e/C2e 的 grep pattern 漏引号 ⇒ 恒 0（对声称条件不可失败） | ✅已修 | pattern 改 `{.qemu.: …}`（`.` 匹配 `'`） | 修复前实测 `actual=0`（两处 FAIL）；修复后同两条日志命中 1、C 段 20/0 rc=0 |
| F5 注入②红因是 QEMU 超时 rc=-2，而非 guest 退出码 | ❌不修 | 如实记录（成因：链例内意外 ILLI 返回默认地址 ⇒ hmon 环回，属既有行为） | 脚本注释/完成区均按 `-2` 写；还原后回绿 |
| F6 单册回归是否受牵连（同表 `lr`/`sc`/`ct*`） | ✅已验 | 不改它们；加 B10–B12 现场统计断言 | 12-misc 28/28 绿（册内载体数现场统计，不写死） |

**判决**：全部 finding 已处置（4 修、1 核、1 不修有据），状态 `待验收`。

### 第 1 轮 reviewer 验收

依据：任务书验收 1–5 + 约束；`spec/SimRISC-12 §2`、`.tao/contracts/contract-isa §13.1`、`contracts/opcodes.yaml::swym_oiii_imm`（`legality: immu18[17:12] == 0`）、`spec/SimRISC-00 §6.1`（空白单元格 ⇒ UNDI）。以下全部为 reviewer 本人重跑。

**重跑记录（仓库根）**：`make build-qemu` **rc=0**（`qemu-system-dadao` md5 `c5a46ef7…`）；`tools/qemu/check_qemu_trans.py --strict` **rc=0**（`263/263 … orphan 0`）；`check_decodetree_repro.py` **0**；`check_component_changelog.py` **0**；`semantics_gate.py --form-check` **0**；`check_legality_invariants.py` / `check_legality_drift.py` **0**；`tools/infra/check_patch_tree.py` rc=1（基线红）但 **qemu 段 `69 patch(es)`、qemu assertion 0**，`--source-state` qemu `OK HEAD=b1d4f0c clean=True`。
**证据脚本**：运行期证据目录内 `run.sh` → **rc=1，PASS 35 / FAIL 1**（唯一失败 `D1 … actual=`；A 16 / B 15 / D 4）；`run.sh --inject` → **rc=1，PASS 55 / FAIL 1**（同 D1；C 段 **20/0**，两路注入均红、均 `cp`+md5 还原回绿）。
**载体**：`tests/inst/12-misc/swym_oiii_imm.S` 在本次构建 QEMU + Tiny bootrom（`f8ef553e…`）**rc=0、88 B `79893035…`**，与 gem5/chipyard 参考流 `cmp` 逐字节相同；同册 12-misc 现场 **28 PASS / 0 FAIL**。
**独立注入（reviewer 自做，不采信 engineer 自检）**：共享 qemu 源树去掉 SBZ 判据 → 同一 `run.sh` **PASS 24 / FAIL 12**（A2b/A3d/B4–B12 全红，源树 `git diff` 非空）→ `cp` 还原 md5 `63e3e649…` 相等、`make build-qemu` rc=0 → 回到 **35/1**（仅余 F1）。
**快照对账**：写入本记录前，任务 worktree `git status --porcelain -uall` 空、三文件 md5 与验收前逐一一致（补丁 `e22fd9ad…`、changelog `bc6cb9ed…`、任务书 `e577ca12…`）；写入本记录后仅任务书一文件为 `M`（reviewer 产出）。共享 qemu 源树 `git diff` 空、md5 `63e3e649…`、无 `*.preinject` 残留；主仓 `milestones-m19.md` 由 M 转净属他会话并发写，与本任务无关。写入后重跑 `make check-knowledge-refs` **rc=0**（0 具体 `.work/**` 引用）。

**语义核验**：S1 `trans_swym_oiii_imm` 首句即 `if (a->hb != 0) { gen_exception_illegal(ctx); return true; }`，该路径无任何寄存器/内存 TCG 写（`DISAS_NORETURN` 收尾）；合法 `swym N` 仅 `return true`（NOP）；与同文件 `trans_fence_ciii_cfx`/`trans_ret_riii_ra` 静态判据同形；`a->hb` = `insn.decode` `%hb 12:6` = `immu18[17:12]`（opc 0x47/ha 0x22 由模式前 14 位固定，`@misc` 取 hb/hc/hd）。S2 「`insn.decode` 不写死零位」成立：`translate.c` `if (!decode_insn(...)) gen_exception_undi(ctx)` ⇒ 不匹配落 **UNDI**；`SimRISC-00 §6.1` 明确空白单元格 ⇒ UNDI 而非 ILLI；模式前 14 位 `01000111100010` 在 263 条中唯一，hb 写 0 后高位非零编码将无匹配；`DADAO_EXIT_MONITOR(3,8)=0xF8`(ILLI) 而 UNDI index 9 ⇒ `0xF9`。

**判决：Needs Revision**（仅证据脚本 D 段；代码/语义/门控/载体全绿，无代码返工）。
- **F1（阻断：门控/退出码）** `run.sh` D 段用**裸 `git status`** 推导变更集：分支已提交（`638ac7fc4`）后 D1 实际值恒空 ⇒ **假红 rc=1**，同时 D1b/D2/D3/D4 在干净树上**恒过（恒真）**，违反 `AGENTS.md §4`「变更集 = 未提交 ∪ `$BASE..HEAD`、禁裸 `git status`」。改法：五条断言实际值改为 `{ git status --porcelain -uall -- <目录>; git diff --name-only master...HEAD -- <目录>; } | sort -u`（D4 另加 `--diff-filter=A`），预期值不变；预期 `run.sh` **PASS 36 / FAIL 0 rc=0**、`run.sh --inject` **PASS 56 / FAIL 0 rc=0**。
- **F2（非阻断，文档数字）** 完成区「全仓 94 problem 全属 linux/musl」与现场 **78**（chipyard 14 / gem5 2 / linux 50 / llvm 4 / musl 4 / picolibc 4，共享源树并发态）不符，改写为现场统计口径；qemu 段 0 为验收判据，已满足。
- **约束逐条**：只动 `components/qemu/**` + 任务书 ✓（变更集 = 未提交 ∪ `master...HEAD` = 3 文件，与完成区一致）；未改 gem5/chipyard/testcases ✓；`manifests/` 无改动（版本未升）✓；`series` 69、无新增补丁文件 ✓；`insn.decode` 未改 ✓；补丁头 `@@ -0,0 +1,573` 与 573 个 `+` 行、blob `cac20288…` 现算一致 ✓；完成区无具体 `.work/**` 路径 ✓。

### 第 1 轮返工处置（Needs Revision 后）

只改证据脚本 D 段与完成区数字；实现、补丁、changelog、载体未动（reviewer 已复核部分不再触碰）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1（阻断）D 段裸 `git status` ⇒ 分支提交后 D1 假红、D1b/D2/D3/D4 恒真 | ✅已修 | 新增 `changeset()` / `changeset_added()`：`{ git status --porcelain -uall -- <dirs> \| cut -c4-; git diff --name-only [--diff-filter=A] "$BASE...HEAD" -- <dirs>; } \| sort -u`（`BASE=master`，porcelain 路径自第 4 字符起）；五条断言期望值不变 | 分支已提交（`638ac7fc4`）状态下 `run.sh` **PASS 36 / FAIL 0 rc=0**（A16/B15/D5）、`run.sh --inject` **PASS 56 / FAIL 0 rc=0**（C20）。**可达 FAIL 两验**：`BASE=HEAD`（无提交差）⇒ D1 红 `actual=` 空；`touch tests/inst/.canary…` ⇒ D1 / D1b / D3 三红（`actual` 含该文件），删除后回 5/0 |
| R2（文档数字）完成区「94 problem 全属 linux/musl」与现场不符 | ✅已修 | 改为现场统计口径：**78** problem = linux 50 / chipyard 14 / llvm-project 4 / musl 4 / picolibc 4 / gem5 2（共享源树并发态）；并注明脚本直跑 **rc=1** 与 `make check-patch-tree` **rc=2** 的区别（make 把 recipe 失败统一记 2），判据只取 qemu 段 0 条 assertion | `make check-patch-tree` rc=2 与脚本直跑 rc=1 输出同一 `78 problem(s)`，qemu 段 `69 patch(es)`、0 条 `assertion` |

**判决后状态**：`待验收`（本段只追加，未改写 reviewer 记录）。

### 第 2 轮 reviewer 验收

依据：第 1 轮 F1/F2 与返工 R1/R2；以下全部为 reviewer 本人重跑（分支 `9796e3ec2`，实现仍 `638ac7fc4`，`run.sh` mtime 11:38:57）。

**交付态重跑**（`git status -uall` 0 行；变更集 = 未提交 ∪ `master...HEAD` = 任务书 + changelog + 补丁 3 文件）：运行期证据目录内 `run.sh` → **rc=0，PASS 36 / FAIL 0**（A16/B15/D5）；`run.sh --inject` → **rc=0，PASS 56 / FAIL 0**（C 段 20/0；C1e/C2e 两路注入真红、C3/C3b `cp`+md5 还原回绿）。B4–B12 全绿：载体 **88 B `79893035…`**、与 gem5/chipyard 参考流 `cmp` 逐字节相同、12-misc 全册无 FAIL；A 段门控（trans 263/263、decodetree、patch-tree qemu 段、changelog）本轮随 run.sh 重跑全绿。

**D 段实现核验**：`changeset()` = `{ git status --porcelain -uall -- <dirs> | cut -c4-; git diff --name-only "$BASE...HEAD" -- <dirs>; } | sort -u`；`changeset_added()` = 同上但 untracked 取 `$1=="??"`、committed 取 `--diff-filter=A`；`BASE=${BASE:-master}`。前缀规范化经实测：canary 注入后 `actual` 只含纯路径，无 `?? `/` M ` 前缀。

**可达 FAIL 五验（reviewer 自做，非采信 engineer 自检；均复现→还原→回绿）**：
- A `BASE=HEAD ONLY=D` ⇒ **D1 红且 `actual=` 空**（PASS 4 / FAIL 1，rc=1）⇒ 无提交差时不再恒过；
- B `touch tests/inst/.canary-m19q2` ⇒ **D1/D1b/D3 三红**（actual 含该文件；PASS 2 / FAIL 3），删除后 **5/0 rc=0**；
- C `touch manifests/.canary-m19q2` ⇒ **D2 红**，删除回绿；
- D `touch components/qemu/patches/zz-canary-m19q2.patch` ⇒ **D4 红（1）**，删除回绿；
- E `cp` 备份后给既有 `target/dadao/Kconfig.patch` 追加一行（porcelain ` M`）⇒ **D4 保持 0**、D1/D1b 红 ⇒ 证明 D4 只取新增；`cp` 还原 md5 `195414df…` 相等后 **5/0 rc=0**。
五次还原后 `git status -uall` 均 0 行，无 canary 残留（途中误建的 `components/qemu/patches/Kconfig.patch` 已 `rm`，该路径本不存在）。

**完成区口径核验（现场）**：`check_patch_tree.py` **rc=1**、`78 problem(s)` = linux 50 / chipyard 14 / llvm-project 4 / musl 4 / picolibc 4 / gem5 2（求和 **78**）；`make check-patch-tree` **rc=2**（日志 `make: *** Error 1` ⇒ make 统一记 2）、同一 `78 problem(s)`；qemu 段 `69 patch(es)`、**0 条 assertion** —— 与完成区逐字一致。

**其余**：状态 `待验收` ✓；第 1 轮 reviewer 记录（64–79 行）**未被改写**：`git diff 638ac7fc4..HEAD` 仅替换完成区 problem 口径 1 行 + 纯追加，追加块与我第 1 轮写入原文逐字一致；实现侧 md5 与第 1 轮相同（补丁 `e22fd9ad…`、changelog `bc6cb9ed…`、共享源树 `63e3e649…`、源树 `git diff` 0 行）；`.work` 为符号链接（证据脚本属运行期证据目录、不在版本控制内，故返工提交只含任务书）；写入本记录后重跑 `make check-knowledge-refs` rc=0。

**判决：Accepted** —— 第 1 轮 F1（D 段变更集口径）与 F2（完成区数字）均已修复，且五路反例注入由本人复现红、还原回绿；代码/语义/门控/载体结论沿用第 1 轮全绿，本轮交付态 36/0 与 56/0 可复现。
