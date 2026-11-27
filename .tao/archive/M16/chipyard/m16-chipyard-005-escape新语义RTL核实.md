# m16-chipyard-005: chipyard RTL 的 `escape` 新语义核实/补（`prev_cfx_code`）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m14-spec-009`（spec + QEMU 已实现）、`spec/Kaiwu` 已对齐（`ede7f6b3`）、`m15-testcases-017`（11-cfx 载体已按新语义重写）
**可并行分片**：可与 `m16-gem5-013` 并行（不同组件）
**预估**：3–4 h（若需补 RTL 则含 `make verilog` 与 sim md5 登记）
**档位**：中改（跨 RTL + 补丁集）
**状态**：已验证

## 背景（用户 2026-11-18 裁定）

`m14-spec-009` 把 `escape` 改为**恢复 `inner_cfx_code ← excp_prev_cfx_code`**（`cg5 rc1`，异常进入时保存），spec + QEMU 已落地，`spec/Kaiwu` 已同笔对齐。

三方里 **chipyard RTL 是否实现该语义尚未核实**——RTL 若按旧语义（escape 不改 `inner_cfx_code`），则与 spec 冲突，且会影响任何依赖 cfx 切换的探针/仿真结论。

**本任务必须先核、后决定补不补**，不允许「假定 RTL 没问题」。

## 目标

### 1. 核实（先做，产出结论）

在 `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/**`（`WumingCore.scala`、cfx 相关文件）与 `dadao-gewu/**` 中确认：

- 是否存在「异常进入时保存当前 cfx」的寄存器（对应 `cg5 rc1`）；
- `escape` 路径是否恢复该寄存器；
- `cg5 rc1` 的读写在 RTL 里如何实现（reserved？可读写？）。

**产出**：代码位置（文件 + 行/信号名）+ 结论（已实现 / 未实现 / 部分实现）。

### 2. 若未实现（或部分实现）⇒ 补

- 补 `prevCfxCode` 寄存器：异常进入时在改写 `cfxCode` **之前**保存；`escape` 通过步骤 0 检查后恢复；`cg5 rc1` 可读写。
- 按 `AGENTS.md` 单二进制纪律：`make verilog` rc=0、**sim md5 登记**（与既有冻结基线对比要说明）。
- 补丁经 `make_patch chipyard` 重导出（禁手改 index）。

### 3. 行为验证（无论补不补，都要有可失败证据）

- 用现有 cfx 探针（`tools/chipyard/excp/`）构造「supv 帧内投递异步事件 ⇒ 该帧 escape 成功、cfx 回到进入前值」；
- 若补了 RTL：**删掉恢复那行 ⇒ 必须复现 `CFXESC`** ⇒ 还原 ⇒ 恢复；
- 若确认 RTL 已是新语义：给出**代码位置 + 一条断言**（探针里断言 `cfx` 回退值），不能只靠读代码。

## 验收（逐条贴真实 rc）

1. 核实结论：代码位置 + 判定（已实现/未实现/部分）；若「已实现」必须附探针断言。
2. 若补：`make verilog` rc=0、sim md5 记录、`make_patch chipyard` 幂等、`--source-state chipyard` = `base+1 clean`。
3. 行为验证：删恢复 ⇒ `CFXESC`（或对应断言红）⇒ 还原 ⇒ 绿。
4. `make check-patch-tree` 的 chipyard 段 0 problem。
5. `check-component-changelog` rc=0（若改组件需追加 changelog）。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. **不碰 `components/gem5`、`components/qemu`**（分别由 `m16-gem5-013` 与已完成的 spec-009 负责）。
3. **不改 spec**；不改 `tests/inst`。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。
5. 严格串行：先 `make verilog`、再跑探针，不并发。

## 待裁定

**Q1：hmon SRAM 的上电口径（chipyard 随机 vs QEMU 0）谁来收敛？**

- **事实**：`tests/inst/11-cfx/escape_ciii_cfx.S` 链例 12 用 hmon SRAM `+0xC0`（catcher 的 cause_id 槽）与 `+0xC8`（到达计数）当"未调用/未到达"哨兵，读前不写。本 profile 的 TLRAM 上电不为 0（实测 `+0xC8` = `0xad3555700e50e7e2`），QEMU 为 0 ⇒ 该链例在 chipyard 结构性红（rc=12、0 B）；把两槽显式清零的同一副本在 chipyard/QEMU **96 B 全绿**，说明 escape 语义已对齐，差别只在 SRAM 上电口径。
- **选项**：① 另立 chipyard 任务给 hmon SRAM 做复位清零（`WumingCore`/tile 侧 FSM 或 scratchpad init，~8K 拍启动开销）；② 由 testcases 侧把载体改成"读前先写"（`tests/inst` 属他人范围）；③ 在 QEMU 差异表登记"SRAM 上电内容不属架构契约、载体不得依赖"，只留本记录。
- **自决的临时处置**：本任务按 ③ 交付——不碰 `tests/inst`（硬约束 3）、不给 SRAM 加复位清零（超出"escape 语义"范围且改启动时序），改用自建载体 `tools/chipyard/excp/prevcfx.S`（自己的槽显式清零）取证。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `escape` 提交那拍若返回地址 IALIGN，旧实现「进入优先」会丢掉本拍的模式/cfx 恢复，帧被写成进入前的 cfx（应用之后停在 hmon）——11-cfx `escape` 链例 9 之后的用例全红 | ✅已修 | `GewuFile` 在 `excp.valid && escapeOk` 时把帧写成**恢复后**的 `prevCfx/prevMode`（先恢复再进入，与 QEMU 同序） | `escape_ciii` 改前红在点 9、改后 1–11 全过（verbose 轨迹 `excp cause=0x2000` 处 `prev_cfx=3f`）；`prevcfx` 探针带 IALIGN 无关路径全绿 |
| `CFXESC` 恒交 monitor（`enterHmon` 用 `vector(monitor)`），而 `§5.3` 步骤 0 要求交当前 cfx：11-cfx `escape` 链例 10/11 的落点错 | ✅已修 | `GewuFileIO.excp` 增 `toCurrent`、增输出 `entryVector`；`WumingCore.enterHmon` 增 `toCurrent` 参数并改用 `entryVector` | `prevcfx` 探针点 5/6（CFXESC 由 cfx_power 入口接住、cause_ip = escape 地址）；11-cfx 链例 10/11 通过 |
| 注入还原用 `cp -p` 带回旧 mtime ⇒ chipyard classpath 缓存不重编，生成物仍是注入版（首轮 `--inject save` 出现"还原后仍红"） | ✅已修 | `run.sh` 还原后 `touch` 源文件再重建 | 第二轮 `--inject save`/`--inject restore`：INJ6/INJ7 全绿，交付态 PASS=24 FAIL=0；sim md5 回到 `9b6928e0…`（与注入前一致） |
| `tools/chipyard/excp/causeid.S` 的 CFXREG 例用 `cg5 rc1`（`m14-spec-009` 起已是 RW，不再是保留寄存器） | ✅已修（载体本身另有既有断裂） | 该例改 `cg5 rc63`（`spec/DADAO-12 §3.6` 明写 reserved） | 该载体自 m15 宏层改造后缺 `__TEST_SECTIONS` ⇒ 链接 `undefined symbol: __fault_chain`（既有、非本次引入，见遗留 ③）；CFXREG 路径已由 `tests/inst/11-cfx/cfx2rd` 的 `cg3 rc9` 例覆盖并通过 |
| `11-cfx/escape_ciii` 链例 12 在本 profile 结构性红（hmon SRAM 上电非 0） | ⏸延后 | 未改 `tests/inst`（硬约束）、未给 SRAM 加复位清零（超范围）；改换自建载体取证 | 见「待裁定 Q1」：清零副本 chipyard/QEMU 96 B 全绿 |

### 第 1 轮 reviewer 验收（2026-11-19，中改 / ≥2 路注入）

**重跑记录（全部为我自己的命令与真实输出/退出码）**
1. `bash 运行期证据目录内的 `run.sh` ⇒ **`EXIT=0`，`PASS=17 FAIL=0`**：A1–A4/B1–B3/C1/C3–C6/D1/D2×4 全 PASS；`sim md5 = 9b6928e035c321835d81cef03542c6f7`；prevcfx **48 B**、`boot=63`、RW `37(0x25)`、`landing=2`、`cause_id=1/8`；11-cfx 4 载体 chipyard==QEMU（184/136/72/112 B，rc 0/0）；`escape_ciii` 未清零原载体复跑仍 `chipyard rc=12 / 0 B`、`qemu 96 B`。
2. `run.sh --inject save` ⇒ **`EXIT_SAVE=0`**：INJ3 `rc=1、semiout 0B`（真红）⇒ `cp`+md5 还原（`5fd5da7e…` 相等）⇒ 重建 ⇒ `INJ6/INJ7` 绿、**`PASS=24 FAIL=0`**；`run.sh --inject restore` ⇒ **`EXIT_RESTORE=0`**：INJ3 `rc=7、semiout 0B`（真红）⇒ 同上 **`PASS=24 FAIL=0`**；两路结束 sim md5 均回 `9b6928e0`。
3. **第 3 路（我独立注入，run.sh 未列）**：`curCfx := prevCfx(viewIdx)(5,0)` → `gp.cfx(monitor).id.U(6.W)`（恢复成 monitor）⇒ `probe rc=7 / 0 B / check rc=1`（真红，落点第 3 次到达）；`cp` 还原（md5 `5fd5da7e…` 相等）+`touch`+重建 ⇒ `probe rc=0 / 48 B / check rc=0`（回绿），sim md5 回 `9b6928e0`。
4. **核实结论对「改动前」补丁**（`git show HEAD~1:<patch>` 逐条）：① cg5 仅 `isPrevMode`(rc=0)（base L359），`readOk/writeOk` 不含 rc1（L365–372）⇒ 落 `CFXREG`；② `grep -c inner_cfx_code <base GewuFile> = 0`（无该状态）；③ `escapeOk = ha===io.monitorHa && hasFrame(causeId(monitor))`（L418/L433），恢复仅 `runMode := prevMode(monitor)`（L460）；④ base `WumingCore` `ip := gewu.io.vector` = `vector(monitor)`（L924–925），CFXESC 走 `enterHmon` ⇒ 交 monitor ⇒ **「部分实现」四条全部成立**。
5. **补的实现对照 `spec/DADAO-12`**：`prevCfx(entryIdx) := curCfx` 与 `curCfx := entryHa` 同在 `when(excp.valid)` 内（寄存器语义 ⇒ 步骤 5 先采样、步骤 6 再切）✓；`escapeOk = curImplemented && ha===curCfx && hasFrame(viewIdx)`（§5.3 步骤 0）✓；`.elsewhen(escapeOk) curCfx := prevCfx(viewIdx)(5,0)`（步骤 2）✓；`excp.toCurrent` ⇒ `entryVector`，CFXESC 传 `toCurrent=true`（交当前 cfx）✓；`excp.valid && escapeOk` 时帧写**恢复后**的 `prevCfx/prevMode`（先恢复再进入，与 QEMU 同序）✓。
6. **Q1 独立核实**：载体源码确为读前不写（`escape_ciii_cfx.S` L332/L335 读，写点仅 L315）；我自建 `srampower.S` 原样读 `HMON_BASE+0xC0/+0xC8` ⇒ chipyard `0xad3555700e50e7e2`（两次读数相同）、QEMU `0/0`；把两槽显式清零的副本跑 `run_inst_tiny.py --platforms chipyard,qemu` ⇒ **chipyard 96 B == QEMU 96 B（md5 `1fb42c10c7c1bdce824fd3e8bd8a8be7`）、rc 0/0，12 链例 + 8 故障例全过** ⇒ 「结构性红 / 清零后 96 B 全绿」成立。
7. **补丁纪律**：`make_patch chipyard` 连跑 2 次均 `0 written, 23 unchanged`（rc=0）；`check_patch_tree.py --source-state` rc=0（`chipyard: OK HEAD=2866839cf267 count=1 clean=True`）；`check_patch_tree.py` rc=0、`11 patch set(s), 423 patches OK`、0 problem（chipyard 23 patch）。
8. **门控**：`check-component-changelog` rc=0（10 文件×4 断言=40 项 PASS）、`check-dirs` rc=0、`check-knowledge-refs` rc=0（悬空 0）；**`check-temp-dirs` rc=2**：5 条 VIOLATION 全属他册陈旧目录（`m14-linux-016`/`INFRA-106t`/`LLVM-130t`/`TESTCASES-085t`/`m14-infra-001`，mtime 23:46 已超 2 h），本任务目录按活动 worktree 排除 ⇒ **非本任务交付物缺陷**，不代删、不凑绿，列未闭合项。

**约束核验**：diff = 本任务书 + `components/chipyard/{README,changelog,3 个补丁}` + `tools/chipyard/excp/{prevcfx.S,prevcfx.lds,check_prevcfx.py,causeid.S}`；未碰 gem5/qemu/linux/spec/`tests/inst`；版本号未动；注入还原全程 `cp`+md5（无 checkout/restore/stash/show）；未提交 git；工作区快照审前 `M components/chipyard/README.md`、审后同 + 本任务书，逐行对账一致。`causeid.S` 改 `cg5 rc63` 合 `§3.6`（rc1 已 RW、rc63 reserved）；其 `__fault_chain` 断链为既有（`HEAD~1` 同样 0 处 `__TEST_SECTIONS`，我复现 `ld.lld: undefined symbol: __fault_chain`）。

**发现（不阻断）**：① `README.md` 未进 WIP 提交（`git status` 仍为 `M`）⇒ architect 提交时须与完成区「修改文件」对账纳入；② `check-temp-dirs` rc=2（见上，归属他册，需各任务收尾清理）；③ 工程师措辞「TLRAM 上电随机」——实测同 sim 两次读数相同（固定垃圾值），宜写「上电非 0」；④ 完成区「`check-temp-dirs` rc=0」在其跑时为真、现因他册目录超龄变红（文档级，记 finding 不返工）。

**判决：Accepted** —— 验收命令在我自己的重跑下全绿（`run.sh` EXIT=0/17 项、两路注入 EXIT=0/PASS=24、第 3 路注入真红后回绿），核实结论四条对改动前补丁逐条坐实，5 项实现要点与 spec 步骤对齐，Q1 结论经我独立复核成立；唯一 rc≠0 的 `check-temp-dirs` 已判归属他册、非本任务缺陷。**Q1**：结论成立（非 0 上电值 + 读前不写 ⇒ 结构性红；清零后 96 B 全绿），建议按自决③ 由架构师在收尾时裁定 SRAM 上电口径归属。

## 完成区

**测试结果**：证据脚本（运行期证据目录内 `run.sh`）交付态 **PASS=17 FAIL=0**；`--inject restore` / `--inject save` 两路均「注入 ⇒ 真红（rc=7 / rc=1，semiout 0 B）⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿（PASS=24 FAIL=0）」。
**核实结论（改动前）= 部分实现**：`generators/dadao-gewu/.../GewuFile.scala` 的 cg5 只有 `rc0`（`prevMode`，`isPrevMode` 判据 L369/读写 L409/事件 L457），`cg5 rc1` 不在 `readOk/writeOk` ⇒ CFXREG；**无 `inner_cfx_code` 状态**（`escapeOk = ha === io.monitorHa && hasFrame`、帧恒取 monitor 的 `causeId/causeIp`）；`escape` 只 `runMode := prevMode(monitor)`；`WumingCore.enterHmon` 恒 `ip := gewu.io.vector`（monitor 向量 ⇒ CFXESC 也交 monitor）。
**修改文件**：`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch`、`.../dadao-wuming/src/main/scala/wuming/common/{WumingCore,WumingParams}.scala.patch`（`make_patch chipyard` 重导出：3 written / 20 unchanged，二次 0 written）、`components/chipyard/{README.md,changelog.md}`、`tools/chipyard/excp/causeid.S`；新增 `tools/chipyard/excp/{prevcfx.S,prevcfx.lds,check_prevcfx.py}`；本任务书。
**验收结果**：① **探针**（`prevcfx.S`，自建 hmon/cfx_power 入口、自己的槽显式清零）：`cg5 rc1` boot=63、RW 0x25 往返、hmon 帧 `escape` 回应用、应用再 `escape cfx_hmon` ⇒ **CFXESC** 且 `cause_ip` = 被拦 `escape` 地址、落点到达 2 次；chipyard 与 QEMU **48 B 逐字节相同**（`check_prevcfx.py` 现场解析 spec 位号 + 合约 cfx 编号，7 项全绿）。② `tests/inst/11-cfx`：`cfx2rd`（链例 23 = cg5 rc1=0x3F + RW）/`cfx2rc`/`trap`/`fence` **4/5 与 QEMU 逐字节相同**（改前基线：`cfx2rd` 点 23 红、`escape` 点 9 红）。③ **重建**：`make verilog` + `make`（`sims/verilator`，`JOBS=32`）均 rc=0、`%Error`=0，sim md5 **`9b6928e035c321835d81cef03542c6f7`**（旧 `eb5220f9…` 作废）。④ **门控**：`check-patch-tree` chipyard **23 patch / 0 problem**（全仓 11 集 423 patch OK）；`--source-state` chipyard `HEAD=2866839cf267 count=1 clean=True`；`check-component-changelog` rc=0；`check-dirs --residue`、`check-knowledge-refs` rc=0。
**新发现/坑**：① **`cp -p` 还原带回旧 mtime** ⇒ chipyard classpath 缓存按时间戳判定不重编、生成物仍是注入版（首轮注入"还原后仍红"的真因）⇒ 还原后必须 `touch` 再 `make verilog`；② 11-cfx `escape_ciii` 链例 12 依赖 hmon SRAM 上电为 0，本 profile TLRAM 上电随机（`+0xC8`=`0xad3555700e50e7e2`）⇒ 该链例结构性红；两槽显式清零的同一副本 chipyard/QEMU **96 B 全绿**（语义已对齐）；③ `tools/chipyard/excp/causeid.S` 自 m15 宏层改造（故障链 + `__TEST_SECTIONS`）后缺 `__TEST_SECTIONS` ⇒ 链接 `undefined symbol: __fault_chain`（既有、非本次引入）；④ `escape` 与「返回地址 IALIGN 进入」同拍时须**先恢复再进入**（帧写恢复后的 `prevCfx/prevMode`），否则该帧声称来自 handler、下一次 `escape` 把核留在 hmon（11-cfx 链例 9 之后全红）。
**遗留问题**：① `trap cfx_power` 仍报 ILLI（`§5.2` 通用 trap 应进 power 向量；`trap_ciii_cfx.S` 已记 GAP）⇒ 另立任务；② hmon SRAM 上电口径（随机 vs 0）待裁定 Q1 收敛（本任务按"载体不得依赖"处置）；③ `causeid.S` 缺 `__TEST_SECTIONS` 的既有断裂建议随 ②/独立任务修；④ **`make check` 未全绿，但与本任务无关**：`check-milestones-fresh` R1 报「`m15-testcases-018`：有 worktree（`/tmp/opencode/m15-testcases-018/wt`，branch `m15-testcases-018`）但未列入进行中/已验证表」⇒ 归属该任务/协调者清理；本任务相关的 L1 项（`check-patch-tree`/`--source-state`/`check-component-changelog`/`check-dirs --residue`/`check-knowledge-refs`/`check-temp-dirs`）全 rc=0。
