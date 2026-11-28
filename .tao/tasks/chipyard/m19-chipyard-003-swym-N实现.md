# m19-chipyard-003: chipyard 实现 swym N（12 位、1+N 拍、原子）

**模块**：chipyard
**项目里程碑**：M19
**依赖**：`m19-spec-001`（语义与契约）
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待验收

## 背景

当前 `WumingCore` 把 `fence`/`swym` 都当 1 拍 no-op，`swym N` 的 N 被忽略。用户 2026-11-27 定：N=12 位、`immu18[17:12]` SBZ（非零 ILLI）、总时延 1+N、原子（执行期间不取中断）。这条会作为后续流水线/超标量“长延迟原子指令”的基线。

## 目标

1. 解码/合法性：`immu18[17:12]` 非零 ⇒ `ILLI`；`N = immu18[11:0]`。
2. `WumingCore` 增加 `swym` 多拍状态：`swym 0` 仍 1 拍；`swym N` 数 N 个额外拍，总 1+N。
3. **原子**：`swym` 执行期间不检查/不取中断；完成后回到正常指令边界再取。
4. 更新 trace/cycle 口径与 `contracts/wuming-cycles.yaml` 派生；不改其它指令语义。
5. Verilator 仿真可测：N=0/1/4095 的周期与高位 ILLI。

## 验收（逐条贴真实 rc）

1. `make build-chipyard`（或等价）rc=0；Verilator 跑通新增用例。
2. 周期：N=0 ⇒ 1 拍、N=1 ⇒ 2 拍、N=4095 ⇒ 4096 拍（trace/cycle 实测）；`immu18[17:12] != 0` ⇒ ILLI。
3. **原子性**：构造 `swym` 期间到达的 pending 中断，确认不中途进入，完成后才取；若 Tiny 当前无可用中断源，须在任务书披露并给出替代验证（如 gem5 对照 + RTL 静态检查）。
4. **可达 FAIL ≥2 路**：① 计数器少一拍/多一拍 ⇒ 周期用例红；② 去掉高位 SBZ ⇒ ILLI 用例红。
5. `check-patch-tree` chipyard 段 0 problem；`check-component-changelog` rc=0。

## 约束

独立 `git worktree`；**不提交 git**；只动 `dadao-wuming` 核/测试与必要补丁；不改 QEMU/gem5；不接板；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：证据脚本 `run.sh` A+B+C **PASS=35 FAIL=0**（运行期证据目录，含 `run-final.log`）；`tools/chipyard/swym/check_swym.py` **46/46**（周期 + ILLI + 原子静态 + 退出码），`--self-test` **5/5**（合成坏流全红）；`check-inst-asm` **274/274**（QEMU 腿）。
**修改文件**：`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/{WumingCore,WumingDecoder}.scala.patch`、`components/chipyard/{README.md,changelog.md}`、`docs/core-wuming-cycle-model.md`、`contracts/wuming-cycles.yaml`、新增 `tools/chipyard/swym/{swym.S,swym.lds,check_swym.py}`、本任务书。
**验收结果**：① Tiny `make verilog`+`make` rc=`0/0`、`%Error`=0（sim md5 `8733c7a2…` 仅记录，ISS-453）；探针汇编/链接 rc=`0/0`、sim rc=0、`host exit status 0`。② 周期（`+verbose` trace，`swym-done - swym` +1；下一条 `exec` 同步为 done+1）：N=0/1/4095 ⇒ **1/2/4096 拍**（`52177→52177`、`52178→52179`、`52180→56275`）。③ 高位 SBZ：`0x47881000`/`0x478BFFFF`/`0x478A0007` 各 **1 条 `excp cause=0x100`**，`cause_ip`=`sw_illi0/1/2`（`0xffffff01012c/168/1a4`）、`cause_info`=原字（`0x47881000/478bffff/478a0007`）。④ 注入 2 路（计数器多一拍 ⇒ checker 42/4 红；删高位 SBZ ⇒ 39/5 红），`cp`+md5 还原 + `touch` 重建后回绿（46/46）。⑤ 门控：`check-patch-tree` rc=0（chipyard **31 patch / 0 problem**）、`--source-state` rc=0（chipyard `OK HEAD=cad31d2b count=1 clean=True`）、`make_patch` 二次 **0 written**、`check-component-changelog` rc=0、`check-dirs`/`check-no-residue`/`check-knowledge-refs`/`check-index-blobs`/`check-tests-index`/`check-contracts-pending`/`check-spec-drift`/`check-width-sizes` 全 rc=0。
**新发现/坑**：① `swym-done` 是唯一不受取指影响的周期观测点（`done-start`），guest 侧下一条 `exec` 与之相差 1 拍（同 beat）；② 文档 §3 行必须带 `N=`（写在括号里、反引号内）生成器才输出 `dynamic: 'N'`，重生成的 `contracts/wuming-cycles.yaml` 与 `m19-spec-001` 手改逐字节一致（仅 `source_doc_sha256`/`doc_lines` 随文档更新）；③ 高位 SBZ 词需按 `base|imm` 手算：`0x47BFFFFF` 会改坏 `ha` 变成 UNDI（本任务首轮实测 `cause=0x200`，已改 `0x478BFFFF`）；④ 还原必须 `cp`+md5+`touch`，`cp -p` 会因 classpath 缓存按 mtime 判定而不重编。
**遗留问题**：① **原子性**：Kaiwu-Tiny `WumingTile` 无任何中断源（无 cfx_hart/TIMER/外部 IRQ），按任务书披露口径以 RTL 静态检查替代（`asyncTake`/`intrFreqTake` 仅在 `sExec`/`sFreq`；`sSwym` 块无中断采样/`intrAck`），行为对照待 `m19-gem5-001`（Vast 侧另见下条）；② **跨任务 KNOWN-RED**：`tests/inst/12-misc/swym_oiii_imm.S` 在 chipyard 上超时（`max-cycles` `%Fatal`，rc=255）——其 `swym 0x3FFFF/0x20000/0x1FFFF` 高位置位用例按新语义为 ILLI，hmon 默认返回槽回到 BootROM 重启；该文件由 `m19-testcases-001` 负责改（QEMU 腿仍 274/274）；③ **既有 KNOWN-RED**：`check-wuming-cycles` 的 gem5 `wuming_cycles.cc` 行 272 `swym` 仍 `1u`（diff 仅此 1 行，与基线逐行相同），归 `m19-gem5-001`；④ `check-temp-dirs` 红 5 项均为他任务陈旧 `/tmp/opencode` 目录（本任务目录不在列表）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| checker 的「sSwym 无中断采样」匹配到注释里的 `intr`/`gewu.io.intr` ⇒ 假红 | ✅已修 | 先剥 `//` 注释、再匹配代码 token | 46/46 绿 |
| `0x47BFFFFF` 不是合法 `swym` 编码（改坏 `ha`） | ✅已修 | 改 `0x478BFFFF`；`.S` 期望同步 | ILLI `cause=0x100`、info 相等 |
| 周期只看 `exec` 差会被取指抬拍 | ✅已修 | RTL 增 `swym-done`，判据 `done-start+1` | 1/2/4096 与 guest 下一条 `exec` 一致 |
| 文档 §3 行写成 `1+N` 生成器只给 `expr` | ✅已修 | 括号内写 `N=immu18[11:0]` ⇒ `dynamic: 'N'` | YAML 与 spec-001 逐字节一致 |
| 还原后不重建会拿注入版二进制 | ✅已修 | `cp`+md5+`touch`+重建 | 两路注入回绿、源树 clean |

**待裁定**：无。

### 第 1 轮 reviewer 验收

- **重跑（仓库根执行运行期证据目录内的 `run.sh`）**：`bash …/run.sh` ⇒ `evidence: PASS=35 FAIL=0`、`RC=0`，35 条与完成区 `run-final.log` 逐条一致（含 sim md5 `8733c7a2…`）；`ONLY=B bash …/run.sh` ⇒ `PASS=8 FAIL=0`、`RC=0`。
- **判据直跑**：`tools/chipyard/swym/check_swym.py --log <运行期证据目录>/swym.log --elf … --source <源树 WumingCore.scala>` ⇒ `PASS=46 FAIL=0`、rc=0；`--self-test` ⇒ `5/5`、rc=0（good 绿；timing-off-by-one / no-illi-fault / wrong-illi-ip / wrong-guest-status 四路均红）。
- **周期（我从 `+verbose` 原始 trace 现场算，非引述）**：N=0 `52177→52177` ⇒ **1 拍**；N=1 `52178→52179` ⇒ **2 拍**；N=4095 `52180→56275` ⇒ **4096 拍**；三条 start/done 与 `n=` 一一对应、无多余 start。
- **ILLI 逐条（原始 `excp` 行）**：`cause=0x100` ×3；`cause_ip=0xffffff01012c/168/1a4`、`info=0x47881000/0x478bffff/0x478a0007`，checker 以 ELF 符号/指令字独立比对全部相等；`N = immu18[11:0]`（译码 `imm18 = inst(17,0)`、核内 `inst(11,0)`）、SBZ = `immu18[17:12]` 位号正确。
- **原子性披露口径**：源树实证 `asyncTake`/`intrFreqTake` 只在 `sExec`/`sFreq`、`sSwym` 块无 `intr`/`intrAck`；`useVM=false ⇒ hart=None ⇒ asyncModel=false ⇒ intr.valid≡0`（WumingParams/GewuFile）⇒ Tiny 无中断源成立；完成区/README/changelog 均写「以 RTL 静态检查替代、行为对照待 `m19-gem5-001`」，**未**写成已行为验证（按此口径核过措辞）。
- **契约同步**：`docs/core-wuming-cycle-model.md` R10/§3/§5 三处 `1+N`；`contracts/wuming-cycles.yaml` swym 行 `cycles: '1+N'`、`dynamic: 'N'`、`source_doc_sha256` = 文档实测 `4f502752…`、`doc_lines.sram=154`；`tools/gem5/gen_wuming_cycles.py --check` rc=0（0 FAIL，幂等）；与 `spec/SimRISC-12 §2`（12 位 / SBZ / 1+N / 原子 / `ILLI = 1<<8` / `cause_info` = 指令字）逐条一致；**版本号未升**（SimRISC-12 仍 0.5.8-rc）。
- **门控**：`check-patch-tree` rc=0（chipyard `31 patch(es)`、`problem` 行 0、全局 `464 patches OK`）、`--source-state` OK、`make_patch` 二跑 `0 written`、`check-component-changelog` PASS（11 文件 × 4 = 44）、`check-dirs`/`check-no-residue`/`check-index-blobs`/`check-tests-index`/`check-contracts-pending`/`check-spec-drift`/`check-width-sizes`/`check-knowledge-refs` 我均亲跑 rc=0；`check-temp-dirs` rc=1 的 5 项与完成区披露逐条相同（他任务陈旧目录，本任务不在列）。
- **注入（脚本 C 段，我重跑）**：计数器多一拍 ⇒ `check_swym 42/4`、rc=1；删高位 SBZ ⇒ `39/5`、rc=1；两路 `cp`+md5 还原（`32c764cb…` / `ce15b2d7…`）+ `touch` 重建后 `46/46`、源树 clean。
- **独立注入（我自选锚点，非 engineer 那两路）**：`swymLeft := inst(11,0) - 1.U` → `- 2.U` ⇒ `ONLY=B` 跑出 `check_swym 42/4`、`PASS=7 FAIL=1`、`RC=1`（构建仍 `0/0`，红来自周期断言）；`cp`+md5 双向 `32c764cb…` 相等 + `touch` 重建 ⇒ `PASS=8 FAIL=0`、`RC=0`、源树 clean。
- **约束逐条**：独立 worktree、审查前后 `git status -uall` 均为空、未提交 git；只动核/补丁/测试资产/本任务书与周期契约文档，未改 QEMU/gem5（gem5 源树只读）；完成区无 `.work/**` 路径；`tests/inst/12-misc/swym_oiii_imm.S` 超时如实归 `m19-testcases-001`（该任务目标 1 即同目录/同文件扩展；`check-inst-asm` 仅 `--platforms qemu`、我复核 274/274）。
- **findings（文档/登记级，不阻断，交 architect 收尾）**：① `check_swym.py` docstring 称 E 段含「译码器 SBZ 断言」，实际 `check_source()` 只读 `WumingCore.scala`（该点由仿真 ILLI 用例覆盖）⇒ 改 docstring；② 两条 KNOWN-RED（gem5 `wuming_cycles.cc` 行 272、`swym_oiii_imm.S` chipyard 手跑超时）只在完成区登记、未落 `issues-m19.yaml`，后者在 `m19-testcases-001` 任务书内亦未写明归属 ⇒ 建议补登记（两者均不进 L1/L2/L3：`check-wuming-cycles` 不在 L1 `_locked-check` 与 L2 `_locked-check-modules` 依赖内，`check-inst-asm` 仅 `--platforms qemu`）。
- **快照对账**：审查前任务 worktree 与主仓 `git status --porcelain -uall` 均为空；审查后主仓仍为空、任务 worktree 仅本任务书 `M`（`git diff --stat` = 本任务书 `16 insertions`，即本审阅记录 15 行）；`contracts/wuming-cycles.yaml` `2b2c8112…`、`docs/core-wuming-cycle-model.md` `58a0ccb6…`、`tools/chipyard/swym/check_swym.py` `a636a3c9…` 前后 md5 相等；源树 `WumingCore.scala` 还原后 md5 `32c764cb…` 与注入前相等、`git status` 空。
- **判决：Accepted** —— 验收 5 条在我自己的重跑下全部通过、约束无违反；上列两条为文档/登记级 finding。
