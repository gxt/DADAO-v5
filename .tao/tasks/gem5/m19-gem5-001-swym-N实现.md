# m19-gem5-001: gem5 实现 swym N（12 位、1+N 拍、原子）

**模块**：gem5
**项目里程碑**：M19
**依赖**：`m19-spec-001`（语义与契约）
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：已验证

## 背景

`swym N` 在 gem5 当前只按 `swymCycles = row.cycles + immu18` 计延迟，未限制 N 的 12 位，也没有“高位 SBZ ⇒ ILLI”的合法性与“执行期间不取中断”的口径。用户 2026-11-27 定：N=12 位、总时延 1+N、原子中断。

## 目标

1. 解码/合法性：`immu18[17:12]` 非零 ⇒ `ILLI`；`N = immu18[11:0]`。
2. `swymCycles` 改为 **1 + N**（N 已 12 位，不再按 18 位直接相加；不再有“上限”分支）。
3. 原子：`swym` 作为一条长延迟指令建模，**不在 1+N 期间注入中断**；中断在下一个指令边界取。
4. 更新 gem5 侧单测/周期用例：N=0、1、4095；高位非零 ILLI；中断不被中途插入。
5. QEMU 保持 NOP，不改。

## 验收（逐条贴真实 rc）

1. `make build-gem5` rc=0；`--source-state` gem5 段 `OK clean`。
2. 新增/更新的 gem5 测试：N=0 ⇒ 1 拍、N=1 ⇒ 2 拍、N=4095 ⇒ 4096 拍；`immu18[17:12] != 0` ⇒ ILLI；中断测试证明 1+N 期间不取中断。
3. **可达 FAIL ≥2 路**：① 去掉高位检查 ⇒ ILLI 用例红；② 把 `1+N` 写成 `N` 或 `1` ⇒ 周期用例红。
4. `check-gem5-decode` / `check-wuming-cycles` 真实 rc；若为既有基线红，按“错误集逐行相同”给对照。

## 约束

独立 `git worktree`；**不提交 git**；只动 gem5 补丁/测试与必要契约派生；不改 QEMU；不接板；完成区不写具体 `.work/**` 路径。


## 完成区

**测试结果**：真机 rc 逐项见下（证据脚本 `run.sh` 在运行期证据目录，整体 rc=0）：
`make build-gem5` rc=0；`make check-gem5-decode` rc=0（positive 263/263、negative 391/391、legality 30/30、legacy 2/2、failures 0）；`check_b6.py` rc=0（B6 30/30、PASS 1436、rule_refs 5/15/12）；新增 `check_swym.py` rc=0（12 PASS：N=0/1/0x7FF/4095 → total 1/2/2048/4096、extra=N、高位被掩）；新增 `check_swym_atomic.py` rc=0（gem5 FS `--cpu-type timing --wuming-cycles`，cycle 差 d0=26 d1=27 d2=4121 ⇒ d1−d0=1、d2−d0=4095；TIMER 在窗口内到期时 cause_ip=0xffffffff10b8=swym 后边界、entry_cycle=10855 ≥ t0+4095、count=1）；`check_converge.py` rc=0；`check_b1..b7` 全 rc=0；`check-wuming-cycles` rc=2（基线红，见下）。
**修改文件**：`components/gem5/patches/**`（b6.cc/b6.hh/b6_test.cc/isa.cc/wuming_latency.hh/decode_{table,assertions}.inc/decode_test.cc 共 8 份补丁，`make_patch.py gem5` 重导出：8 written/98 unchanged）；`components/gem5/{README.md,changelog.md,decode-assertions.tsv}`；`tools/gem5/{check_b6.py,check_converge.py,compare_chipyard.py,gen_decode_table.py}`；新增 `tools/gem5/{check_swym.py,check_swym_atomic.py,swym_policy_test.cc}`；本任务书。
**验收结果**：① 可达 FAIL（真实输出）：删 `b6.cc` 的高位 ILLI 检查 ⇒ `check_b6` rc=1（`swym immu18=0x1000 high bits: fault None, expected Illegal`），cp+md5 还原后 rc=0；把 `swymCycles` 写成 `N` ⇒ `check_swym` rc=1（`swym 0: total cycles 0 == 1 + N`），还原后 rc=0。② 探针自身 FAIL 路径：`--mutate ip/window/count` 分别得到 guest exit 0xd4/0xd5/0xd3；无 1+N 模型（`--cpu-type timing` 不带 `--wuming-cycles`，`--skip-cycles`）⇒ 0xd3，证明“1+N 期间不取中断”断言不是恒真。③ 基线红对照：`check-wuming-cycles` 唯一 FAIL 行 = `contracts/wuming-cycles.yaml 与现解析结果不一致`，与 `m19-spec-001` 基线逐行相同；`wuming_cycles.{hh,cc}` 两条 artifact PASS。④ `check-patch-tree --source-state` gem5 `OK HEAD=cb99ad38 count=1 clean=True`；`check_patch_tree.py` 全量 rc=0（12 套 464 补丁 OK）。
**新发现/坑**：`contracts/wuming-cycles.yaml` 是生成物而 `docs/core-wuming-cycle-model.md` 未同步 ⇒ `check-wuming-cycles` 基线红；C++ 表仍按文档生成，`swymCycles()` 成为契约 `1+N` 的唯一覆盖点（已在注释写明）。`gen_decode_table.py` 插入一条 legality 会整体重编号 `kRules*/kLegality*` 数组（预期）。探针编码坑：`cmp.uo`/`sub.o` 的 dbb 形态 ha 与 bbd 不同（0x32/0x33，bbd 是 0x31），须按 `opcodes.yaml` 的 `value` 反查，勿凭助记符猜。`check_converge.py` 的 `PASS_BASELINE` 中 b1/b5/b7 在本任务前已漂移（基线红），已一并重冻；`tests/data/GEM5-002t-semantic-matrix.tsv` 的 swym 行仍是 2026-11-01 快照（“约 N+1 倍/可设上限”），未改（`refresh_matrix_notes --check` 会重写非目标单元）。
**遗留问题**：首轮后台 `make build-gem5` 在 `manifest-check` 后以 rc=2 静默退出（未进 `build_gem5.py`，疑与并发/锁竞争有关，日志仅 manifest 段）；第 1 次重试 rc=0，`run.sh` 复跑亦 rc=0，未复现。`docs/core-wuming-cycle-model.md` 与生成物同步未做（任务书要求不扩范围，按基线红逐行对照记录）。QEMU 按任务书保持 NOP，未改。未加 Makefile 目标（避免改共享文件），测试入口为 `tools/gem5/check_swym.py` / `check_swym_atomic.py`。

**reviewer F1 已修、F2 状态已订正**：`tests/data/GEM5-002t-semantic-matrix.tsv` 的 swym 行 `semantics` 改为「总时延 1 + N 拍（N = immu18[11:0]，12 位、无上限；immu18[17:12] 为 SBZ，非 0 ⇒ ILLI）且执行期间不取中断」（仅该单元格；`refresh_matrix_notes --check` rc=0、`check_b6.py` rc=0）；任务书状态 `待验收`（分支内自 `9bef6e29` 起即为该值，主工作树副本不在本 worktree 写域）。

## 待裁定

1. 是否把 `swym` 的 `1 + N` / 12 位 N 写回 `docs/core-wuming-cycle-model.md` 并重跑生成器（会同时改变 `contracts/wuming-cycles.yaml` 与 gem5 生成 C++ 表；涉及契约版本号，须用户认可）。
2. 是否把 `check_swym.py` / `check_swym_atomic.py` 接入 `make` 与 L2 门控（触及共享 `Makefile` 与门控分层）。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查了 `exec/b6.cc`（swym 分支：ILLI 先于 hint/IP、`0x3F000` 恰为 immu18[17:12]）、`wuming_latency.hh`（`1 + (immu18 & 0xFFF)`，N 上限 4095、total≤4096；provisional 仍返回 0）、`isa.cc`（整块时延一次计入，`extraFromTotal`⇒N）、`decode_test.cc`（新 `field[hi:lo] == 0` 求值器：越界/畸形表达式一律 Unsupported，不静默合法）、`gen_decode_table.py`（N=4095 合法 / 0x1000 ILLI 两条）、`b6_test.cc`（4 个合法 N + 5 个高位非零 ILLI + 精确 fault/IP 不变）、两个新探针与 `run.sh`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `swymCycles` 不再取 `row.cycles`，与“图中无手抄拍数”原则冲突 | ❌不修（记录） | 文件头/函数注释注明唯一例外来自契约，生成表未动 | `check-wuming-cycles` C++ artifact 2/2 PASS |
| 探针初版 `sub.o` dbb 误用 bbd 的 ha=0x31 | ✅已修 | `sub_o_dbb` 改 ha=0x33；rd 目标用 `sub.o rd, rb, rb` | 反汇编逐指令核对 + 探针 PASS |
| `check_converge` 期望值未随新增断言更新 | ✅已修 | b6 1384→1436、legality 28→30；b1/b5/b7 一并重冻 | `check_converge` rc=0 |
| `compare_chipyard` 的 Python 镜像把 swym 当静态值 | ✅已修 | `model_total_cycles` 先判 swym → `1 + (immu18 & 0xFFF)` | 与 C++ 逐行同式（审读） |
| 中断探针可能恒真 | ✅已修 | 加 `--mutate ip/window/count` 与无 1+N 模型反例 | exit 0xd4/0xd5/0xd3 逐项 |

### 第 1 轮 reviewer 验收

**重跑**（本 worktree、相对路径；日志在运行期证据目录内的 `logs/`，均我本人执行）
1. `bash 运行期证据目录内的 run.sh` 第 1 次 ⇒ `ALL CHECKS PASSED`、`RUN_RC=0`、19/19 record PASS：build-gem5 rc=0；check-gem5-decode rc=0（263/263、391/391、30/30、2/2、failures 0）；check-wuming-cycles rc=2（FAIL=1、yaml=1、C++=2）；apply-series rc=0；source-state gem5 `OK count=1 clean=True`；check_b6 rc=0（30/30、PASS 1436、FAIL 0、rule_refs 5/15/12）；check_swym rc=0（12 PASS：N=0/1/0x7FF/4095 → total 1/2/2048/4096、extra=N、高位被掩）；check_swym_atomic rc=0（`cause_ip=0xffffffff10b8 entry_cycle=10855 count=1`、`d0=26 d1=27 d2=4121` ⇒ 1/4095）；mutate ip/window/count ⇒ 0xd4/0xd5/0xd3；无 1+N 模型 ⇒ 0xd3；两条 DUT 注入 ⇒ rc=1、md5 相等、回绿 rc=0。
2. `python3 tools/gem5/check_converge.py` ⇒ `CONVERGE_RC=0`（b1 2196 / b2 1160 / b3 4318 / b4 3696 / b5 1316 / b6 1436 / b7 2960，legality 30，无 FAIL）。
3. `python3 tools/infra/check_patch_tree.py` ⇒ `PT_RC=0`、`12 patch set(s), 464 patches OK`（gem5 106 份）。
4. **独立注入**（非脚本自带）：cp 备份运行期 gem5 源树 `isa.cc`（md5 `164eed70f4af716e9e7fa5345e6306c3`），把 swym 分支改成 `else if (false)` ⇒ 重跑同一 `run.sh` ⇒ `RUN_RC=1`、7 FAIL（`check_swym_atomic positive` rc=1、`d1-d0/d2-d0 = 0, 0`、三条 mutation 全变 `0xd1`、apply-series/source-state 因源树被改而红）⇒ cp 还原 md5 相等 ⇒ 第 3 次 `run.sh` `RUN_RC=0`（19 PASS / 0 FAIL）。
5. `make check-knowledge-refs` ⇒ `KR_RC=0`（PASS，0 具体 `.work/**` 引用）。写入本记录后已复跑。

**约束核验**
- 1+N 与高位 ILLI ✓：`wuming_latency.hh` = `1u + (immu18 & 0xFFFu)`（无上限分支）；`b6.cc` `(immu18 & 0x3F000u) != 0 ⇒ Fault::Illegal` 先于 `swymHint`；解码表/断言新增 `immu18[17:12] == 0` + `encode_sbz`；gem5 实现与补丁内无「N+1 倍/上限」残留（changelog 只写「无上限」）。
- 原子性 ✓：`timing.cc` 对 extra>0 一次性 `reschedule(fetchEvent, clockEdge(extra))`，`checkForInterrupts()` 只在 `fetch()` 入口 ⇒ 中断在下一指令边界取；guest 三断言（IP=swym 后边界 / entry ≥ t0+4095 / count=1）各有可达 FAIL；4096 > TIMER_DELAY 2047 ⇒ 到期必在窗口内（早于 swym 则 0xd4/0xd5，晚于窗口不可能）。
- 基线红 ✓：唯一 FAIL = `contracts/wuming-cycles.yaml 与现解析结果不一致`；`git diff 2bf528dd..9bef6e29 -- docs contracts tools/gem5/gen_wuming_cycles.py Makefile .tao/contracts spec components/qemu` **为空** ⇒ 检查输入与 m19-spec-001 完成时逐字节相同 ⇒ 错误集与该基线逐行相同；两条 C++ artifact PASS。
- 披露 ✓：`docs/core-wuming-cycle-model.md` 仍写 swym 1 拍（§3 第 93 行）未同步；QEMU 仍 NOP（`trans_swym_oiii_imm` 注释 NOP，19 文件不含 `components/qemu`）；新探针未接 Makefile（`Makefile` 未动）；版本号未升（`manifests/` 未动）；changelog M19 新条目 + README（swym 语义、两个新探针、rule_refs 5/15/12）已同步。
- 变更集 ✓：`git diff 2bf528dd..9bef6e29 --name-only` = 19 文件，与完成区「修改文件」逐项一致（8 补丁 + 3 组件文档 + 4 改 + 3 新增 + 任务书）；`git status --porcelain -uall` 验收前 0 行，本记录写入后仅任务书 1 行。

**finding（不阻断，交 architect 收尾处理）**
- F1：`tests/data/GEM5-002t-semantic-matrix.tsv` swym 行 `semantics` 仍写「约 N+1 倍基准，硬件可设上限」，与契约 1+N/无上限冲突；完成区所给理由不成立——实测改该单元格后 `python3 tools/gem5/refresh_matrix_notes.py --check` 仍 `RC=0`（该脚本只改 lr/sc/f2i/arith 四族与 scaleB 两列），故是可就地修的引用漂移（实验后按 md5 `efa41c228d42a40d51ea694d51cd50af` 还原，工作树已净）。
- F2：任务书 `状态` 仍为「待开始」（收尾由主会话改）。

**判决：Accepted** —— 任务验收 1–4 与全部硬约束在我自己的重跑下全部成立，两条可达 FAIL 由脚本自带注入 + 我的独立注入双向证实；F1/F2 属文档/数据级，按「文档级小错」记 finding，不另开返工。
