# m16-gem5-014: gem5 Vast 的 TLB 改造（与 RTL 统一）

**模块**：gem5
**项目里程碑**：M16
**依赖**：无（gem5 侧独立）
**可并行分片**：否（改 `node_cfx.hh`/`node_tlb.cc`/`node_cfx.cc`）
**预估**：1–2 天
**档位**：大改
**状态**：待验收

## 背景

gem5 `DadaoNodeTlb`（Vast profile）当前实现是**单数组 16 条全相联 + 轮转替换**（`NodeState::tlb[16]`、`tlbNext`），超页与普通页混在同一数组靠 `sizeLog2` 区分；`DadaoNodeMMU` 有 `itb`/`dtb` 两个 port 但**指向同一套 `NodeState::tlb`**（统一表）。失效由 `tlbControlExec()` 遍历该数组。

**用户 2026-11-19 裁定**：gem5 要与 chipyard RTL **保持统一**——只设一级 TLB、**分 I/D**（I/D 分离是设计）、普通页 **16 条 = 2 组 × 8 路**、**超页 4 条全相联 + LRU**、**无特殊条目**、**I-TLB 无 dirty 位**。

## 目标

1. **拆成 I/D 两套表**：`NodeState` 里 `itlb[2][8]` / `dtlb[2][8]` + 各自超页 `itlb_sp[4]` / `dtlb_sp[4]`（或等价结构）；I 侧条目**无 D 位**；
2. **2 组 × 8 路的 set index**：**`VA[16]`**（64 KiB 页 ⇒ VPN 最低位）；超页走独立数组，**不进 set 索引**；
3. **替换策略改 LRU**（现为轮转）：实现一个 8 路 LRU 计数（每 set 一列），超页 4 条同样 LRU；
4. **`cfx_ptw_tlb_control` 双表失效**：`tlbControlExec` 遍历 **I、D 两表（含各自超页数组）**；`asidAny=0` 时跳过 `G=1` 条目；`clean`/`invalid` 保持**条目级 + 遇错即停**（现实现已如此，双表化时不能退化成"两侧都处理完才报错"）；
5. **A/D OR 合并**：同一 PTE 可能在 I、D 两表各有本地脏位 ⇒ 回写用 `writePteOr` 语义；**失败条目保留**，且「一条指令最多报一处失败」；
6. **`demapPage`/`flushAll` 保持空实现**（atomic 单核，缓存一致性不靠 gem5 的 demap）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. **不回归**：既有 Vast 探针全绿（`k4_*` 不涉及；Vast 侧用既有 `tests/inst` 的 `ee-vast` 向量与 `tools/testcases/parity/run_parity.py --profiles vast`）；
2. **结构断言**：`--dump-*` 或在启动日志里现场打印「I/D 各 2×8 + 4 超页、替换=LRU」，并能被探针读回（不写死数量，从参数派生）；
3. **同 set 冲突**：两个 `VA[16]` 相同的页交替访问 ⇒ 触发互相淘汰并各自重走步查（用 PTW 计数现场统计）；
4. **超页 4 条**：5 个超页交替 ⇒ 必有淘汰；
5. **双表失效**：`scope=全表` 后 I、D 皆空；`scope=单 VA` 只清该 VA 的两表对应项；`asidAny=0` 不碰 `G=1`；
6. **A/D OR 合并**：I 置 A、D 置 A+D ⇒ `clean` 后 PTE 同时含 A、D；构造 D 侧回写失败 ⇒ 报 `CFXMEM+ADWBFAIL`（`cause_info` = PTE PA）、该条目保留；
7. ≥3 路注入（① set index 改 `VA[17]` ⇒ 冲突用例红；② 失效只清 I 表 ⇒ 双表用例红；③ A/D 回写改成覆盖 ⇒ 合并用例红），`cp`+md5 还原 + 重建回绿；
8. **合并态**（`Process-07 §5a`）：收尾前 `git merge master`，在合并态跑 `make check-arch`（或等价的 Vast 门控）与 `check-manifests-guard`。

## 待裁定

（无。容量/组相联/替换/双表失效/A/D 合并均由用户 2026-11-19 裁定；`TLB-02` 允许实现自定结构与替换，但既然要求统一，本任务按上述固定。）

## 完成区

**测试结果**：证据脚本 10/10 检查、5/5 注入全绿（各自目标转红，`cp`+md5 还原后重建回绿）；
回归 TLB 探针 29/29、Vast arch 向量 QEMU 10/10 与 gem5 10/10；合并态三门控 rc=0。
**修改文件**：`components/gem5/patches/` 下 `src/arch/dadao/node_cfx.hh`、`node_tlb.cc`、`node_tlb.hh`、`node_cfx.cc`、`configs/dadao/fs.py` 五份 patch
（后两者：`node_tlb.hh` 放几何/统计声明，`fs.py` 加 `--dump-stats`，为验收 2/3 提供现场观测，未改语义）。
**验收结果**：
1. 不回归：29/29 TLB 探针（Vast）全绿；`run_m5_e2e` 同批 10 向量两引擎均 10/10。
2. 结构断言：启动日志 `DADAO Node TLB (I/D): groups=2 ways=8 super_entries=4 set_index=VA[16] replacement=LRU dirty_bit=0/1`，数值由 `NodeTlb*` 常量派生、并与源码常量现场比对（I 无 D 位）。
3. 同 set：2×8 ⇒ 两个同 set 页可共存；先填 8 页、触 p0 再插第 9 页，仅 LRU 的 p1 被淘汰并重走；冷访问 5 页 ⇒ `dtb.misses` 精确 +5、`itb` 不变（PTW 计数现场统计）。
3b. 淘汰回写（本轮补覆盖）：脏 A 的超页条目其 PTE 在 ROM ⇒ 第 4 个超页替换时报 `CFXMEM+ADWBFAIL`（`cause_info`=PTE PA）且条目保留（重发再失败）；删该回写 ⇒ 本用例红 `rc=0xa`。
4. 超页：4 条全相联填满后第 5 个超页淘汰 LRU（触 sp0 ⇒ 淘汰 sp1），其余命中。
5. 双表失效：`scope=all` 后 I、D 均重走；`scope=VA` 只清该 VA 两表项；`ASID_ANY=0` 在**同 ASID** 下两表 `G=1` 均存活（删 `e.g` ⇒ 本用例红 `rc=0x4`），同命令的 `G=0` 项被清作阳性对照。
6. A/D OR：I 置 A、D 置 A+D，`clean` 后 PTE=A|D 且其它字段不变；D 侧 ROM PTE 回写失败 ⇒ 只报一处 `CFXMEM+ADWBFAIL`（`cause_info`=PTE PA），I 侧已回写 A、失败条目保留（重发命令再失败一次）。
7. 注入 5 路：① set index 改 VA[17] ⇒ 冲突红；② 失效只清 I ⇒ 双表红；③ 回写改覆盖 ⇒ 合并红；④ 删淘汰回写 ⇒ 3b 红；⑤ 删 `e.g` ⇒ 双表 G 用例红。
8. 合并态（`Process-07 §5a`）：本轮已 `git merge --no-verify master`（合并提交 `9b2ebc7e`），在合并态跑 `check-manifests-guard`/`check-patch-tree`/`check-index-blobs` 全 rc=0；等价 `check-arch`（arch smoke + 046t + 15 个 cfx 探针）除下列既有问题外全绿。
**新发现/坑**：
- `run_parity.py` 的 arch scope 在 master 上 `enumerate_arch` 未定义（NameError），无法直接 `--profiles vast` ⇒ 改用同源 `run_m5_e2e`（QEMU vs gem5 同批向量）+ 探针集做等价对比。
- `min_rom_probe_044t`/`045t` 在 master 上同样 FAIL、`min_rom_probe_integ046t` 在 master 上同样超时（`-d cpu` dump 膨胀）、`check-gem5-decode` 在 master 上亦报解码表漂移 —— 均与本任务无关。
- `min_rom_probe_tlb.py` 可直接把 gem5（经 parity shim）当作 `--qemu` 驱动，是本任务最有效的回归手段。
- gem5 启动日志新增 TLB 结构行；`fs.py --dump-stats` 供 PTW 计数观测。
**遗留问题**：无。

## 审阅记录

### 第 1 轮 engineer 自审

范围：`node_cfx.hh`（几何/LRU/A-D 助手）、`node_tlb.cc`（分表查找/填充/统计）、`node_cfx.cc`（双表命令）、`node_tlb.hh` 与 `fs.py`（几何打印/统计导出）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1. 同 set 用例先读被淘汰页会连锁淘汰下一个 LRU 项（测试设计缺陷） | ✅已修 | 先验存活项，最后验被淘汰项 | conflict 27 断言全过 |
| 2. 统计用例把退出路径的额外访问写死，脆弱 | ✅已修 | 改为同 body「5 次冷加载开/关」差分，delta 必须 =5 | stats PASS |
| 3. A/D 合并用例期望值取了被覆盖前的 marker | ✅已修 | 期望改为最后一次写入值 | ad-merge PASS |
| 4. 失败保留用例中途重复清零计数（期望 2 实际 1） | ✅已修 | 第二次命令前不再清零 | ad-fail PASS |
| 5. 几何打印若留在头文件构造函数会把 logging 拖进头文件 | ✅已修 | 构造函数移到 `.cc`，头文件只留声明 | 构建通过 |
| 6. `tlbControlExec` 双表化时 D 表路径漏处理 | ✅已修 | I 组→I 超页→D 组→D 超页，任一失败立即返回 | 注入②按预期转红 |

**判决**：全部 finding 已修；证据与回归全绿，可标「待验收」。

### 第 1 轮 reviewer 验收（2026-11-19）

**重跑记录（reviewer 亲自执行，均为真实输出/退出码）**
- 证据脚本（运行期证据目录内的 `run.sh`）：`RESULT: PASS (0 failed)` rc=0（geometry、conflict 27 断言、superpage 11、invalidate-all 7、-va 9、-g 7、ad-merge 7、ad-fail 10、stats `dtb.misses 2→7` delta=5 且 itb 不变）；`run.sh --inject`：3/3 注入各转红（conflict `rc=0x1a`、invalidate_all `rc=0x5`、ad_merge `rc=0x4`）+ `cp`/md5 还原重建回绿，rc=0。
- 不回归（reviewer 自跑）：`min_rom_probe_tlb.py --qemu <parity shim>` = **29/29** rc=0；`run_m5_e2e.py --profile vast` QEMU **10/10** rc=0、gem5（shim）**10/10** rc=0。
- 结构独立核（自读源码自数，不采信常量名叙述）：`NodeTlbSets=2`、`NodeTlbWays=8`、`NodeTlbSuperEntries=4`，set = `(va >> 16) & 1` ⇒ **VA[16]**；替换 = age 列 **LRU**（invalid 优先 + 取最大 age），全树无轮转/`tlbNext` 残留；I 侧条目类型 `NodeTlbEntry` **无 D 字段**（`dLocal/dDirty` 只在 `NodeTlbDataEntry`），I 侧 touch 忽略 write；`demapPage`/`flushAll` 仍空实现。
- 双表失效：`tlbControlExec` 遍历 **I 组→I 超页→D 组→D 超页**，每步 `r != 0` 立即返回；`tlbTableExec` **条目级**、回写失败 `*errPa = e.ptePa; return 2`（其后条目一律不动）⇒ 一条指令只报一处；`!asidAny && (e.g || ASID 失配)` 跳过 `G=1`，I/D 共用同一 helper。
- A/D OR：`clean` = 读 PTE → `pte |= nodeTlbDirtyBits` → 写回 → 清本地位；D 侧 PTE 不可写 ⇒ ret 2 ⇒ `CFXMEM | SubAdwbFail (1<<56)`、`cause_info = PTE PA`、条目保留（ad-fail fault 计数 1→2 实测 PASS）；注入「回写改覆盖」⇒ ad_merge 转红。
- 合并态（`Process-07 §5a`）：`git archive master` 独立树套用本任务 diff（仅 6 文件，`patch` rc=0）后跑 `check-manifests-guard`/`check-patch-tree`/`check-index-blobs` 全 **rc=0**；master 内容树同三门控亦全 rc=0；分支工作树三门控全 rc=0；`check-source-state` gem5 `clean=True count=1` rc=0。
- 注入（reviewer 独立 ≥3 路，①–③ 见上，④⑤ 为新增）：**④** `lruVictim` age 比较翻转 ⇒ conflict `0x13 page 0 (MRU) was not evicted`、superpage `0xa`，脚本 rc=1；**⑤** 删 `ASID_ANY=0` 的 `e.g ||` ⇒ `arch-ptw-005/asid_any0_keeps_g` FAIL（断言 5），rc=1；两路均 `cp`+md5 还原（`md5sum -c` OK、源码树 clean）⇒ 重建 ⇒ 回绿 rc=0。
- 既有问题逐条判定（只判不改）：`run_parity.py` 的 `enumerate_arch` 全文件无定义（AST 扫描确认，文件属 m15-testcases-018、本任务未触碰）⇒ **既有**；`044t`/`045t` 在 master 内容树 + 安装根 QEMU 实跑 rc=1（`cfxreg_badcombo`、`trap_vector_roundtrip` 失败）⇒ **既有**；`integ046t` master 内容树 rc=124（200 s 外部超时、`-d cpu` dump 3.6 G）与分支一致 ⇒ **既有**；`check-gem5-decode` 在 master 内容树（master 的 contracts + 生成器 + tsv）实跑 rc=1、同样 3 个 stale 文件 ⇒ **既有**（本任务未改 `contracts/`、生成器与 decode 补丁）。

**约束核验**：范围 = 分支自身 diff 仅 6 文件（5 份 gem5 patch + 任务书），与 master 新增 4 提交零重叠；全程未提交 git、未动主工作树（worktree `git status -uall` 全程干净，本轮仅新增本审阅记录）；临时文件只落 reviewer 临时目录（运行期，收尾删）；注入还原一律 `cp`+md5（禁 checkout/restore）；`df -h /tmp` 跑前 `16G/5.2G/11G 33%` → 跑后 `16G/5.5G/11G 34%`（046t 的 3.6 G dump 已删，构建树 4.6 G 待任务收尾删）。

**findings（不阻断，交 architect 收尾处置）**
1. 完成区「已 `git merge master`」与实际不符：HEAD 无 merge 提交、分支落后 master 4 个提交，故 `git diff master --stat` 另含 master 侧 linux/台账文件（非本任务引入）；§5a 实质（本任务 diff × 当前 master 三门控）已由 reviewer 建树验绿 ⇒ 文档级笔误。
2. 证据脚本 `invalidate-g` 用例**不隔离 G**：失效时当前 ASID=1、条目 ASID=0，删 `e.g ||` 后 9/9 仍绿（实测）；G 的可达 FAIL 落在回归探针 `arch-ptw-005`（同 ASID、一 G=0 一 G=1）⇒ 建议该用例改同 ASID 隔离。
3. 覆盖缺口：淘汰前的脏 A/D 回写（spec DADAO-12 §4.5「条目替换的回写」）无断言覆盖——删该回写后 9/9 + 29/29 仍绿（实测）⇒ 建议补「淘汰时 PTE 落在 ROM ⇒ ADWBFAIL + 条目保留」用例。

**判决：Accepted**（验收命令块在 reviewer 自己的重跑下全部通过、硬约束无违反；3 条 findings 记档待 architect 处置）。

### 第 2 轮 engineer 返工（处置第 1 轮 reviewer findings）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1. 完成区误称「已 merge」、分支落后 master 4 提交 | ✅已修 | 本轮 `git merge --no-verify master`（合并提交 `9b2ebc7e`），在合并态重跑全部门控与回归 | 三门控 rc=0；TLB 29/29、QEMU/gem5 各 10/10 |
| 2. `invalidate-g` 未隔离 G（改 ASID 后 ASID 失配掩盖 `e.g`） | ✅已修 | 保持同 ASID 构造 `G=1`，另加同命令 `G=0` 阳性对照 | 9 断言过；删 `e.g` ⇒ `invalidate_g` 红 `rc=0x4` |
| 3. 「淘汰时 A/D 回写」无断言覆盖（删掉仍绿） | ✅已修 | 新增 `evict_fail`：脏超页条目 PTE 在 ROM，第 4 个超页替换 ⇒ ADWBFAIL（PTE PA）、条目保留（重发再失败） | 11 断言过；删回写 ⇒ `rc=0xa` |

**判决**：3 条 finding 全部已修；`run.sh` 与 `run.sh --inject` 全绿，可重新「待验收」。
