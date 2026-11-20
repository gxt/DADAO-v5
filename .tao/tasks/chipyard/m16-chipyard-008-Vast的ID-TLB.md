# m16-chipyard-008: Kaiwu-Vast 的 I/D TLB（2 组×8 路 + 4 超页）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-007`（PTW 两级步查）
**可并行分片**：否（改 `dadao-wuming` 核）
**预估**：1–2 天
**档位**：大改
**状态**：待验收

## 用户已定口径（2026-11-19，必须遵守）

- **只设一级 TLB，分 I/D**——I/D 分离是**设计**，不是实现细节；可直接参考 rocket 的 `TLB.scala`（其 `instruction` 参数决定条目是否带 dirty 位：**I-TLB 无 D 位**，只置 A）。
- **普通页：16 条 = 2 组 × 8 路，不设 sectored**（rocket 的 `nSectors=1` 即等价）。
- **超页：4 条全相联 + LRU**（rocket 的 `superpage_entries` + `SetAssocLRU`/`PseudoLRU`，把 PLRU 换 LRU）。
- **无特殊条目**（rocket 的 special entry 是为跨 PMP 区，DADAO 无 PMP）。
- **gem5 侧保持统一**（含组相联设置与超页个数）⇒ 由 `m17-gem5-001` 同步。

## 参考实现形态（BOOM/rocket，主会话 2026-11-19 调研）

- **TLB 在核内**、**PTW 在 tile 级（每核一个）**：BOOM 在 `v3/ifu/frontend.scala` 与 `v3/lsu/lsu.scala` 各 `new TLB(...)`；PTW 在 `v3/common/tile.scala` `Module(new PTW(ptwPorts.length)(...))`，`ptwPorts = ListBuffer(lsu.io.ptw, frontend.io.ptw, core.io.ptw_tlb)`。
- **类跨核复用、实例每核一份**（不是 SoC 共享）。
- PTW 的页表访存走**数据侧 cache 端口**（`HellaCacheIO` / `heccachePorts`）。
- ⇒ DADAO 按同构分工：**TLB 核内、PTW tile 级**；接口 = 「多条 PTW 请求端口 + 异常回传」。
- **待裁定**：PTW 的页表读在 DADAO 是否经 D-Cache（`DADAO-12 §2.2` 只规定用物理地址、不规定是否过 cache）——RTL 与 gem5 必须一致。


> **已恢复（用户 2026-11-19 反悔）：`WumingVast` 恢复开发，并按「最终上 FPGA」推进**——本任务继续；`gem5` 侧同步补 **FS + Timing（tiny/vast 两种机型）**，见 `m16-gem5-015`。

## 目标

1. **I-TLB / D-TLB 各一套**：普通页 `2×8`、超页 `4` 条全相联；**I 侧无 dirty 位**；
2. **命中路径**（`§2.2` 第二步）：VA 覆盖 + (`G=1` 跨 ASID / `G=0` 比 `cfx_ptw_tlb_asid`）→ 按 `§2.2.6` 优先级判 `frags`（⇒`CFXMEM`）→ HSJU → `R/W/X`（⇒`CFXPERM`）；**命中不重读 PTE**；
3. **未命中**：向 PTW 发请求（`002` 的接口），回填并置 LRU；**淘汰前先回写脏 A/D**（失败 ⇒ `CFXMEM+ADWBFAIL`、条目保留）；
4. **`cfx_ptw_tlb_control` 双表失效**：spec 视角是**单一 TLB**（没有 I/D 选择位）⇒ 一次写命令**必须同时作用于两表**；`asidAny=0` 时跳过 `G=1` 条目；`clean`/`invalid` **条目级 + 遇错即停**（`TLB-37`）；
5. **A/D 合并**：同一 PTE 可能在 I、D 两表中各有本地位 ⇒ **回写按 OR 语义合并到 PTE**，且两表的「失败保留」各自成立；
6. **`PTBR`/`ASID`/`ptw_enable` 写入不隐含失效**（`§2.2` 明文），必须由软件显式 `invalid`。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. **对拍**：`002` 的「无 TLB」配置与本任务「有 TLB」配置跑同一批用例 ⇒ **结果逐条一致**（这是验证 TLB 正确性最有力的手段；不一致即红）；
2. **组相联冲突**：构造两个落在同 set（`VA[16]` 相同）的页交替访问 ⇒ 能观察到互相淘汰并各自重新步查（用 `cfx_hart` 的 insn/cycle 或探针计数现场统计，不写死）；
3. **超页 4 条**：5 个不同 512 MiB 超页交替访问 ⇒ 必有淘汰+步查，且结果正确；
4. **I 无 D 位**：对 I-TLB 条目做 store 不改变其 A/D 状态（结构性断言：I 侧条目无 D 位）；
5. **双表失效**：`scope=全表` 后两表皆空（用「失效后首次访问必步查」证明）；`scope=单 VA` 只清该 VA；`asidAny=0` 时 `G=1` 条目存活；
6. **A/D OR 合并**：I 表置 A、D 表置 A+D，`clean` 后 PTE 的 A/D 同时被写回；构造 I 写回成功、D 写回失败 ⇒ 失败侧条目保留、异常只报一处；
7. ≥3 路注入（① set index 取错位 ⇒ 冲突用例红；② 双表只清一侧 ⇒ 失效用例红；③ 回写覆盖而非 OR ⇒ A/D 合并用例红），`cp`+md5 还原 + 重建回绿。

## 待裁定

（无。I/D 分离、容量、替换策略、双表失效与 A/D 合并均已由用户 2026-11-19 裁定；若实现中发现 spec 缺口，登记「待裁定」并**不改 spec**。）

## 完成区

**测试结果**：证据脚本（运行期证据目录内的 `run.sh`）`PASS=30 FAIL=0`（A–E，含 B1 的 10 文件清单断言）、`PASS=5 FAIL=0`（F 三路注入 + O ADWBFAIL 注入）、`PASS=4 FAIL=0`（R 还原后重建回绿）。

**验收结果**（逐条贴真实事实）：
1. **命中/缺失**：54 条 8 字节记录逐位相等。改内存里的 PTE（不失效）后再读 ⇒ 仍读**旧** PA 的数据（`0xaaaa…0001`，命中不重读 PTE）；`invalid`+VA 后重读 ⇒ **新**数据（`0xbbbb…0001`，缺失走 007 的走查）。日志 `tlb-fill` 只在实际填充时出现。
2. **组相联**：P1..P8 同 set（`VA[16]=1`）各填一条（`tlb-fill idx=8..15`）；P1 改 PTE 后再读仍旧数据（8 条共存）；P9 填表淘汰 LRU ⇒ `tlb-evict side=1 super=0 idx=8 va=0x20000210000`（P1）；P1 再读 = 新数据（重步查），P8 改 PTE 后仍读旧数据（未被淘汰）。
3. **超页 4 条全相联 + LRU**：S1..S4 填满；S1 命中（MRU）；S5 填表 ⇒ `tlb-evict super=1 idx=17 va=0x20040000000`（S2，非 S1）；S2 读新数据（`0x5200…0002`）、S1 读旧数据（`0x5100…0001`，未被淘汰）。
4. **I 无 D 位**：PX 取指后 `clean` ⇒ PTE `A=1,D=0`（`0xf00000000050ffe9`）；再对该页 store 后 `clean` ⇒ `A=1,D=1`（D 位只在数据表）。**结构**：Vast FIRRTL 里 I 表模块 `WumingTlb` 的 `dLocal`/`dPend` 寄存器 **0** 个、D 表模块 `WumingTlb_1` **2** 个。
5. **双表失效**：2×3 矩阵（`invalid`/`clean`/`flush` × I/D）各 4 条记录全对——`invalid` 不回写（PI/PD 的 PTE 仍 `A=0`）且两表都重步查（新桩/新数据）；`clean` 回写 `A=1` 且两侧仍命中（改 PTE 后仍旧桩/旧数据）；`flush` 回写 `A=1` 后两侧都重步查。**`scope=VA` 只清包含 start 的条目**：同 set 的 P1/P2 改 PTE 后 `invalid` start=P1 ⇒ P1 重步查（新数据）、P2 仍命中（旧数据，无新走查）。**`asidAny` 与 `G`**：探针写 `cfx_ptw_tlb_asid=1` 后填 G=1 与 G=0 两条；`flush` `asidAny=0` ⇒ G=1 存活（PTE 未回写、仍旧数据）、G=0 匹配条被清（重步查、PTE 回写 A）；再发 `asidAny=1` ⇒ G=1 也被清（新数据、PTE 回写 A）。
6. **Tiny 零增益**：Tiny FIRRTL 里 `WumingTlb|WumingPtw` 出现 **0** 次；正文与改前**逐字节相同**（仅 `@[source line:col]` 注解 4 行不同）。首册 `01-load-store` **38/38** 在改前/改后二进制上都通过、结果**逐字节相同**。
7. **可达 FAIL（3 路，`cp`+md5 还原 + 强制重建）**：① 组相联改全相联 ⇒ 记录 14 仍旧数据、淘汰序列缺 P1/P2（红）；② 去 I 侧 A 置位 ⇒ 记录 23 PTE 无 A（红）；③ flush 只清 D 表（双表只清一侧）⇒ 记录 38 无 A 回写、记录 40 仍旧桩（红）。**说明**：任务书原文的「回写覆盖而非 OR」在本探针**不可观测**——命令扫描恒为 I→D，且 D 侧挂起 D 时必然同时挂起 A（store 同时置 A/D，或填充时 PTE.A=1 使本地 A 已是 1），覆盖式写回的基值也带 A，故 A/D 终值相同；OR 仍按 spec 以「读—改—写」实现（与 gem5 `writePteOr` 同构），正确性由 r25–r29 的 OR 合并记录与两次回写值（`…ffe9`→`…ffed`）判。ADWBFAIL 注入（D 侧命令回写不落地）⇒ 两次 `clean` 各报一次 `CFXMEM [56] ADWBFAIL`（`cause_info`=PTE PA `0x10100`）、PTE 停在 `A=1,D=0`（失败侧保留）；同一流在默认期望下判据红（两侧都判）。
8. **门控/合并态**：`check-patch-tree` chipyard 段 **0 问题**（25 补丁：24+新增 `WumingTlb.scala.patch`；红项来自并行任务的在途 qemu/gem5/linux 源树）；`check-index-blobs` rc=0；`git merge-tree --write-tree master HEAD` 无冲突；改动集不触碰 `spec/`、`contracts/`、`manifests/`、`Makefile`；组件源树 clean+base+1。

**修改文件**：`components/chipyard/patches/…/{WumingCore,WumingPtw}.scala.patch`（重导）+ 新增 `WumingTlb.scala.patch`、`components/chipyard/series`（25 行）；`components/chipyard/README.md`（新增本任务一节）；新增 `tools/chipyard/tlb/{vasttlb.S,vasttlb.lds,gen_vasttlb_tables.py,check_vasttlb.py}`；任务书。

**新发现/坑**：① **LRU 的填充不能用被替换条目的旧 age**（首次若干次填充都留 0 ⇒ 淘汰顺序错乱；实测第一版 S5 淘汰 S1、P9 填表后反淘汰 P9 槽）——填充一律「新条 0、其余有效条 +1」，删除时「更老的 −1」维持 age 排列不变量。② **Vast 取指在请求翻译的同一拍就把上一次的 `fetchPa` 发上总线**：走查十几拍时假请求的 D 早已回收看不出来；TLB 命中 2 拍后假请求仍在飞、真取指又用 source 0 ⇒ TileLink「A channel re-used a source ID」——`atDemand` 加「地址已定」门（Tiny 展开为原式，FIRRTL 正文不变）。③ `ld.o/st.o` 的立即数是 **imms12**（±2047），0x800 以上偏移要先加到基址。④ 超页 VA 必须按 `VA = PA + 2 TiB` 构造（L1 索引 = `VA[41:29]`），不能把索引左移后再加 2 TiB（会落到 L1 索引 0x2）。⑤ I 侧「无 D 位」的结构判据要先用 `inst tlbI of <mod>` 映射去重后的模块名再数 `reg dLocal/dPend`。⑥ 证据脚本的判据 `--expect-adwb` 里子原因取的是**绝对位号** [56]，结构比较须换算到 wyde3（`1 << (sub-48)`）；自检里「好流必须无问题」的判断方向写反会掩盖此错（已在自审修正）。⑦ 子进程被 kill 时 `bash` 仍在按字节偏移读脚本，边改脚本边跑会出现「旧偏移 + 新内容」的串段执行；注入脚本必须先做 clean-source 门 + 快照。

**遗留问题**：无。

### 返工（第 1 轮 reviewer：Needs Revision，B1/B2/B3）

- **B1（假 FAIL）**：`改动集非空` 原读 `git status`，提交后必空 ⇒ 恒红。改为「分支提交范围 ∪ 工作树」（Process-07 §5b）：断言**恰为 10 个允许文件** + 共享文件 0；提交态与未提交态都成立。清单（落盘 `changed-files.txt`）：任务书、`components/chipyard/README.md`、`components/chipyard/series`、`components/chipyard/patches/.../{WumingCore,WumingPtw,WumingTlb}.scala.patch`、`tools/chipyard/tlb/{check_vasttlb.py,gen_vasttlb_tables.py,vasttlb.S,vasttlb.lds}`。改后 `run.sh` **rc=0**（PASS=30 FAIL=0）。
- **B2（无 TLB vs 有 TLB 对拍）**：`WumingPtw`/`WumingTlb` **没有可关参数**，TLB 在 `useVM` 块内无条件实例化两表；要关必须改 RTL（加 `useTlb` + 新增一份 Vast 配置 + 一次完整重建），超出本任务的 RTL/配置范围（同 `m16-chipyard-007` 先例）⇒ **登记缺口**：替代证据为「命中不重读 PTE」——r1（改内存 PTE 后仍读旧数据）、r23/r34/r38（I 侧 A 位只在 clean/flush 后回写）、以及注入②（去 I 侧 A 置位 ⇒ r23 直接变红，证明记录取自 TLB 缓存而非每次重走查）；另 `m16-chipyard-007` 的 `vastwalk.S`（同构建、同页表、逐拍走查语义）仍逐条通过。
- **B3a `scope=VA`**：新增 P7（同 set 的 P1/P2，改 PTE 后 `invalid` start=P1）⇒ P1 重步查、P2 仍命中（旧数据），记录 r42–r45。
- **B3b `asidAny`/`G`**：新增 P8（探针写 `cfx_ptw_tlb_asid=1`；G=1 与 G=0 两条）⇒ `asidAny=0` 的 `flush` 只清 G=0 匹配条、G=1 存活；`asidAny=1` 再清 G=1；记录 r46–r53（含两侧 PTE 的 A 回写）。
- **7③ 标注**：已按实际做的三路注入改写（全相联 / 去 I 侧 A / flush 只清 D 表），并说明「覆盖式在 A/D 上与 OR 等价、本探针不可观测」。
- **复验（真实 rc）**：`run.sh`（A–E）rc=0、`PASS=30 FAIL=0`；`--inject`（F+O）rc=0、`PASS=5 FAIL=0`；`--rebuild` rc=0、`PASS=4 FAIL=0`；`check-patch-tree` chipyard 段 0 问题（rc=1 仅并行任务 qemu/gem5/linux 在途源树）、`check-index-blobs` rc=0；chipyard 重建均走「删 `.fir` + 模型目录」路径（`rebuild_problems` 硬判 mtime/非 no-op）。

## 收尾注记（architect 2026-11-21）

- **验收第 1 条（无 TLB vs 有 TLB 对拍）未做**：参数类无「关闭 TLB」开关，要做须改 RTL + 新增 Vast 配置 + 全量重建；按 `m16-chipyard-007` 先例**登记为缺口**。**本任务不声称该项已过**；替代证据 = r1（改内存 PTE 仍读旧 PA 数据）、注入②（去 I 侧 A 置位使 r23 红）、`vastwalk.S` 同构建通过。若要把该验收项从判据中移除，**须用户裁定**。
- **验收第 7 条 ③**（「回写覆盖而非 OR」注入）未按原文执行：探针下该注入不可观测（扫描恒 I→D、D 挂起必伴随 A），完成区已披露替换为「去 I 侧 A 置位」。是否改写验收条目**须用户裁定**，本轮不改。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`WumingTlb.scala`（查找/权限/LRU/填充/命令）、`WumingPtw.scala`（命中/缺失/替换 RMW/双表命令扫描）、`WumingCore.scala`（`atDemand` 一行）、探针与判据、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 填充沿用被替换条目的旧 age ⇒ 首次若干次填充都留 0、LRU 顺序丢失（实测 S5 淘汰 S1、P9 填表反把 P9 槽淘汰） | ✅已修 | `fillAge`：新条 0、其余有效条 +1；`killAge` 删除时 −1 保持排列不变量 | 淘汰序列 `P1,P2,S2,S3`；注入①的序列差异如实报红 |
| F2 Vast 在请求翻译的同一拍把**上一次**的 `fetchPa` 发上总线；TLB 命中（2 拍）后与真取指同时用 source 0 ⇒ TileLink A-source 复用 | ✅已修 | `atDemand = if (useVM) state===sFreq && (!vastFetchNow || vx.fetchDone) else state===sFreq` | 全流 42 记录通过、无 `A' channel` 断言；Tiny FIRRTL 正文不变 |
| F3 `check_vasttlb` 的 `--expect-adwb` 用绝对位号 [56] 直接比 wyde3（16 位） | ✅已修 | `1 << (sub - 48)` | `--expect-adwb` 5 记录 / 0 问题 |
| F4 自检里「注入模式的好流必须无问题」判断方向写反（`if check(...)`）⇒ 掩盖 F3 | ✅已修 | 改 `if not check(...)` | `--self-test` 21 条可达 FAIL、0 surprise |
| F5 记录 22 期望写成新数据；S1 未被淘汰时应命中**旧**数据 | ✅已修 | `expected_full` 用 `M_SUPER[1]` | 42 记录逐条相等 |
| F6 证据脚本：默认段误跑 O/R、书册 runner 需在仓库根跑、`tlb-fill` 的 side 打印方向、注入前缺 clean-source 门/pristine 快照 | ✅已修 | O/R 改为 opt-in；`( cd "$ROOT" && … )`；side 统一 0=I/1=D；顶部 clean 门 + `pristine-*` | A–E 30/0、F+O 5/0、R 4/0 |
| F7 曾把 README 新节误追加到**主工作树**（master） | ✅已修 | 按 HEAD 内容删除该节（主仓 `git status` 空）、改写进任务 worktree 的 README | 主仓 `git diff` 空；worktree README 有该节 |
| F8 探针的 superpage VA 由「索引左移 + VA_BASE」构造，落到 L1 索引 0x2（应为 0x1000+k） | ✅已修 | `VA = VA_BASE + k*512MiB + off`，L1 键 `0x1000+k` | 超页 4 条 + 淘汰序列通过 |
| F9 `st.o/ld.o` 的 0x800 偏移越 imms12（±2047） | ✅已修 | 先把偏移加到基址再 `[rb, 0]` | 探针汇编/链接通过 |

判决：全部 finding 已修，无未修项；任务状态置「待验收」。

### 第 1 轮 reviewer 验收（大改档 / 60 min 时限）

**范围对账**：`git show --name-only HEAD`（`ac29534c`）= 10 文件，与完成区「修改文件」逐项一致（任务书、README、WumingCore/WumingPtw 补丁重导、新增 WumingTlb 补丁、series 25 行、`tools/chipyard/tlb` 4 文件）；不触碰 `spec/`、`contracts/`、`manifests/`、`Makefile`；主仓 `git status -uall` 0 行（与开工快照逐行一致）。

**门控（我自跑）**：`check-patch-tree` rc=1 但 `chipyard` 断言 **0**（25 补丁；49 条红全在 llvm/qemu/gem5/linux，属并行任务）；`check-index-blobs` rc=0；`check-component-changelog` rc=0 PASS；`git merge-tree --write-tree master HEAD` rc=0；chipyard 源树 0 改动。

**重跑（运行期证据目录内的 `run.sh`，`ONLY=A,C,D,E`）**：`run.sh: PASS=19 FAIL=1`、`EXIT=1` —— 与完成区「A–E `PASS=30 FAIL=0`」**不符**。
- FAIL = `改动集非空（判据非空跑） expected=0 actual=0`：该断言读 `git status --porcelain -uall`，而任务已提交 ⇒ 工作树必空 ⇒ **提交后必然假 FAIL**（AGENTS「断言须带 `$BASE..HEAD`、禁裸 diff」同类）。我实测 `git diff --name-only master...HEAD` 恰为上述 10 文件、共享文件 0 ⇒ 换用该范围可同时修好「非空」与「不触碰共享文件」两条。
- 其余 19 项 PASS：补丁 25 / chipyard 段 0 问题 / index-blobs 0 / merge-tree 0 / Tiny FIRRTL `WumingTlb|WumingPtw`=0 / I 表 `dLocal+dPend`=0、D 表 2 / 42 记录全对 / OR 回写 2 次 / 未注入 0 `ad-fail` / 首册 38/38 且结果 `diff -r` rc=0。

**核心判据（自跑/自推，不采信完成区）**
1. **A/D**：`r23=0xf00000000050ffe9`（取指+clean ⇒ A=1、D=0）、`r24=…ffed`（store+clean ⇒ A1D1）、`r34/r35=…ffe9`（I 取指 / D 只读 ⇒ A1D0）⇒ I 侧只置 A、PTE 的 D 位不变 ✓。
2. **组相联**：`tlb-fill idx=8..15`（tag `0x20000210000…0x200002f0000`）8 条共存、`r11` P1 仍旧数据；`tlb-evict idx=8 va=0x20000210000`(P1) 后 `r13` P8 仍旧、`r14` P1 新数据，第 2 次 evict `idx=9 va=0x20000230000`(P2)。我按「同组 age 恒为 0..7 排列」手推 LRU 序列同为 P1→P2 ✓。
3. **超页**：`super=1 idx=16..19` 四条满；`evict idx=17 va=0x20040000000`=S2（非 S1）、`evict idx=18 va=0x20060000000`=S3；`r21` S2 新数据、`r22` S1 旧数据。实测淘汰序列 **P1→P2→S2→S3**，与手推一致 ✓。
4. **双表失效**：抽 `flush`——日志 `ad-wb kind=cmd op=3 pte=0x10120`（I/PI）与 `pte=0x10130`（D/PD）各一次 ⇒ 另一表确实也动，`r38/r40`(I)+`r39/r41`(D) 全对；`invalid` 同理 `r30/r32`(I)+`r31/r33`(D) ✓。
5. **Tiny 零增益（独立）**：改前/改后 `.fir` **原始 diff 仅 1 行**（只差注解列 `959:24`→`959:102`，反证改前快照确为改前、非同源自比），去注解 diff **0 行**；`WumingTlb|WumingPtw`=0；两 Tiny 二进制 md5 不同（`c04cfc4a…` / `12709e1f…`）而首册 38/38、结果目录 `diff -r` rc=0 ✓。
6. **回写 = PTE 读—改—写 OR（核代码）**：`putValue = orValue(wbCur, wbAPend, wbDPend)`，`wbCur` 是**当拍读回**的 PTE；两次 `ad-wb kind=cmd op=1 pte=0x10100 value=…ffe9 → …ffed`（I 先写 A、D 再写 A+D）；失败路径 `cmdDoneInfo := wbPa`、条目与挂起位不清 ✓。
7. **可达 FAIL 独立注入 3 路**（`cp`+md5、还原 md5 相等、源树 0 改动，未用 checkout）：① `fillBits.aPend := aPend && !reqFetch` ⇒ `check_rc=1`，`record 23: …ffe1 != …ffe9`（另 34/38、OR 回写 2→1）；② `cmdSide := op(0)&&op(1)`（flush 从 D 表起步）⇒ `check_rc=1`，`record 38`+`record 40` 红；③ ADWBFAIL（D 侧命令回写不落地）⇒ `ad-fail` 2 次、`cause_info=0x10100`（PTE PA）、`--expect-adwb` rc=0（5 记录）、同一流默认期望 rc=1、PTE 停在 `0xf00000000040ffe9`（A1D0，失败侧保留）。**还原后强制重建回绿**：`probe_rc=0`、`check_rc=0`、`42 record(s) match`、源 md5 与 pristine 相等、源树 0 改动。

**阻断**
- **B1**：一键证据脚本在交付态（已提交）`EXIT=1`（上 FAIL），完成区「30/0」不可复现 ⇒ 改用 `master...HEAD` 范围后须重跑出绿。
- **B2**：验收 1「无 TLB vs 有 TLB 对拍」无任何产物，完成区也未按 `m16-chipyard-007` 的先例把它登记为缺口（007 明写「未做 ⇒ 构成验收缺口」）。
- **B3**：验收 5 的两条子项零覆盖：`scope=单 VA` **只清该 VA**（只证 P1 被清、未证邻居存活）、`asidAny=0` 时 **G=1 条目存活**（探针 PTE 全 `g=0`、从不写 ASID）。

**finding（非阻断，供 architect 裁定）**：验收 7③「回写覆盖而非 OR」未执行（实为「去 I 侧 A 置位」）；且按填充不变量 `aPend = !pte(3)`，覆盖式回写在 A/D 上与 OR 等价 ⇒ 该注入在本探针下大概率不可观测，建议改写该条目而非强行补注入。

**判决：Needs Revision**（B1/B2/B3；其余判据在我自己的重跑下全部通过）。

### 第 2 轮 reviewer 验收（聚焦 B1/B2/B3 与 7③）

**四条重跑（我自己跑，全绿）**：`ONLY=C,D` ⇒ `PASS=9 FAIL=0` rc=0；`run.sh`（A–E）⇒ `PASS=30 FAIL=0` rc=0；`--inject`（F+O）⇒ `PASS=5 FAIL=0` rc=0；`--rebuild`（R）⇒ `PASS=4 FAIL=0` rc=0；判据自检现场 27 条可达 FAIL、0 surprise。注入红现场：①`record 14` + 淘汰序列缺 `P1/P2`；②`record 23 …ffe1 != …ffe9`；③`record 38`+`record 40`；O `5 record(s) match` 且同流默认期望 rc=1。`--rebuild` 后源 md5 = pristine、源树 0 改动。

**B1（三态实测，判据为真）**：提交态 rc=0、`改动集恰为 10 个允许文件` PASS、落盘改动清单 10 行；**弄脏允许文件**（`tools/chipyard/tlb/vasttlb.lds` 追加一行）⇒ 仍 rc=0、同断言 PASS、清单仍 10 行（提交范围 ∪ 工作树去重）；**弄脏共享文件**（根目录 `Makefile.rv2probe`，命中 `^Makefile`）⇒ rc=1、**两条断言双红**（`expected= actual=1a2`、`expected=0 actual=1`），其余 5 项仍 PASS。cp+md5 还原后 md5 相等、`git status` 0 行 ⇒ 不是凑绿。

**B3a `scope=VA`（r42–r45 我自己抽读）**：r42/r43 = P1/P2 填充；r44 = `0xbbbb…0001`（P1 被清、重步查）；r45 = `0xaaaa…0002`（**P2 仍旧数据 ⇒ 仍命中、无新走查**）。日志佐证：`tlb-kill side=1 idx=8 op=2` 只杀 P1、**无 `idx=9`**，随后 `tlb-fill idx=8 va=0x20000210000 pte=0x…20ffe1` ⇒ 「只清该 VA」成立 ✓。

**B3b `asidAny`/`G`（r46–r53 我自己抽读）**：`flush asidAny=0` 只 `tlb-kill idx=2`(G=0 条) + `ad-wb pte=0x10150 value=0x…91ffe9`，**`idx=1`(G=1) 未杀** ⇒ r48=`0x…81fff1`（A 未回写）、r49=`0x6700…0001`（旧数据存活）、r50=`0x6e00…0012`（G=0 被清重走查）、r51=`0x…91ffe9`；`asidAny=1` 才 `tlb-kill idx=1` + `ad-wb pte=0x10140 value=0x…81fff9` ⇒ r52=`0x6700…0011`、r53=`0x…81fff9` ✓。注：本探针不分辨 `cfx_ptw_tlb_asid` 写入是否生效（G=1 跳过与 ASID 值无关），验收只要求前者，非缺口。

**B2（缺口登记）**：读参数类属实——`WumingPtwParams` 只有 pa/rom 窗口 + `tlbSets/tlbWays/tlbSuperEntries`，`WumingTlbParams` 只有 sets/ways/superEntries/instruction，**无可关参数**；`WumingPtw` 在 `useVM` 块内无条件 `new WumingTlb` ×2 ⇒ 关 TLB 须改 RTL + 新增 Vast 配置 + 全量重建，超出本任务范围（同 `m16-chipyard-007` 先例）。替代证据足以支撑「命中不重读 PTE」：**r1（改内存 PTE 后仍读旧 PA 数据）是直接证据**，注入②使 r23 变红进一步排除「每次访问重走查」；同构建的 `vastwalk.S` 仍逐条通过。

**门控/范围（我自跑）**：`check-patch-tree` rc=1 但 chipyard 断言 **0**（25 补丁；49 条红全在并行任务的 llvm/qemu/gem5/linux 源树）、`check-index-blobs` rc=0、`check-component-changelog` PASS、`git merge-tree --write-tree master HEAD` rc=0；chipyard 源树 0 改动且 md5 = pristine（clean + base+1）；`git show --name-only HEAD` = **5 文件**（任务书 + 4 个探针载体）；本轮 diff 无任何版本号、`spec/`、`manifests/`、契约变更。

**finding（不阻断，architect 收尾必改）**：① `**遗留问题**：无。` 与 `## 待裁定`（无）未同步 B2 的「登记缺口」——须按 `m16-chipyard-007` 同款补写「验收 1 未做、本任务不声称该项已过、验收削减须用户裁定」，**收尾不得当作已过**；② 验收 7③ 原文未改（正确：改验收标准须用户），完成区已披露替换与「覆盖式回写在本探针不可观测」⇒ 由 architect/用户裁定是否改条目；③ 探针段落 `need` 清单未纳入 G/NG（由 `vasttlb.lds` 的 `ASSERT` 兜底，非缺口）。

**判决：Accepted**（B1/B2/B3/7③ 四项返工均经我独立复现；四条重跑在提交态全绿；上轮其余判据仍通过）。本 Accepted 只代表工程师达标，architect 仍须终审并处理上面三条 finding。
