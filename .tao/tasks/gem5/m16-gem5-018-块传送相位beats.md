# m16-gem5-018: 块传送 `beats` 按起始相位算（N19，用户 2026-11-19 裁定改）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-016`（改同一份 `docs/core-wuming-cycle-model.md` 与生成表 `contracts/wuming-cycles.yaml`）⇒ **必须等 016 收尾再派**
**可并行分片**：否
**预估**：3–4 h
**档位**：中改
**状态**：待验收

## 背景（N19，`m16-chipyard-004` 实测发现）

现行 `components/gem5/patches/src/arch/dadao/wuming_latency.hh` 的 `multiElementCycles()`：

```cpp
const unsigned bytes = elements * row.elemWidth;
const unsigned beats = (bytes + 7u) / 8u;          // 只看元素总字节
```

即「元素不跨 8 B 拍」。**chipyard 实测要求把起始相位算进去**：

```
beats = ⌈(addr % 8 + N·w) / 8⌉
```

非 8 B 相位起址时每组恰多 8 拍——`ldm.ub` N=8、起址相位 2 ⇒ **24 拍**，而当前模型给 16。影响：**所有非 8 B 对齐起址的 `ldm`/`stm` 都被低估**（`ldm.ub` N=8 = 16 只是 8 B 相位上的值，不能外推）。

**用户裁定（2026-11-19）**：改模型。「相位」是**运行期**量（`addr % 8`），**不新增表格维度**；表里的 `perElement`/`perBeat` 仍是标定出来的系数。

> 附：另有两个 N=1 地址特例（SRAM 尾拍 +11、`.text` 内 off-queue 取指 −1），是既有实测例外，**本任务不解释、不改**（仅记录，避免被当成公式的一部分）。

## 要做

1. **把起始有效地址传进模型**：
   - `wuming::DynamicState` 加起始 EA 字段（块传送基址）；
   - `fillDynamicState()` 的 `dyn == "N"` / `"beats"` 分支填充它（`ldm`/`stm` 的基址寄存器 + 偏移；**hook 时点拿不到 EA 就换到能拿到的时点**——在任务书里写清你选了哪个时点、为什么，以及是否影响 `simInsts` 口径）；
2. **改公式**：`multiElementCycles(row, elements, addr)` 用 `beats = (addr%8 + N·w + 7) / 8`；
3. **重算 `nBase`**（若有影响）：`nBase` 是 §5 实测表的残差，来自 8 B 相位的点。改公式后必须**逐项复核**：8 B 相位下所有既有实测点（`ldm.ub` N=8 = 16、`ldm.o` N=8 = 72、`stm` 类等）**结果一分不差**；若 `nBase` 需变，说明为什么、并把新值写进生成器/表（**不得**为了让旧点凑绿而给公式加特例）；
4. **文档**：在 `docs/core-wuming-cycle-model.md` 的 D 类说明处写清 beats 含起始相位（`beats = ⌈(addr%8 + N·w)/8⌉`），并注明「N=8 = 16 是 8 B 相位值」；**改了文档就必须重跑** `python3 tools/gem5/gen_wuming_cycles.py`，`make check-wuming-cycles` rc=0（门控绑文档 sha256）；
5. **不动** `blockCopyCycles`（D′ 寄存器复制无内存拍）。

## 验收（逐条贴真实 rc）

1. **8 B 相位零回归**：所有既有实测点逐项不变（列表 + 旧值/新值）；同一 ELF 在 8 B 对齐场景下 `numCycles` 与改前**完全相等**；
2. **相位正确**：`ldm.ub` N=8 相位 2 ⇒ **24 拍**（改前 16）、N=1 各相位、`stm` 同式；给 gem5 `--debug-flags=Exec` 的逐指令拍差实测；
3. **与 chipyard 对照**：用 `m16-chipyard-004` 的实测点（若数据仍可用）核方向与数值；若不可用，说明替代证据；
4. **可达 FAIL**：把公式改回 `(N·w+7)/8` ⇒ 相位用例红（`cp`+md5 还原 + 重建）；
5. `check-wuming-cycles`/`check-gem5-decode`/`check-index-blobs` rc=0；`check-patch-tree` gem5 段 0 问题；合并态（`Process-07 §5a`）。

## 完成区

**测试结果**：运行期证据目录内的 `run.sh` **19/19 PASS**（内层：策略探针 1316/1316、gem5 逐指令 80/80、chipyard 10/10、门控 4 项）；`run.sh --inject full` **25/25 PASS**（策略级红 + 真实重建红 → `cp`+md5 还原 → 重建回绿）。

**修改文件**：`docs/core-wuming-cycle-model.md`（§5 块传送段写相位公式与「N=8 = 16 是 8 B 相位值」）、`contracts/wuming-cycles.yaml`（重跑生成器；263 条拍数 0 变化，仅 `source_doc_sha256` 更新）、gem5 源树 4 个文件（`wuming_latency.hh`、`isa.{hh,cc}`、`inst.cc`）及其补丁（`components/gem5/patches/src/arch/dadao/{wuming_latency.hh,isa.hh,isa.cc,inst.cc}.patch`，`make_patch.py` 重导出 4 写 102 跳）、`components/gem5/changelog.md`、本任务书。

**验收结果**：
1. **8 B 相位零回归**：§5 实测点旧值/新值全等——`ldm.ub` N=1/2/3/5/8/16/63 = 9/10/11/13/16/32/127、`ldm.o` N=1/2/3/8/16/63 = 9/18/27/72/144/567、`stm.o` N=1/8/63 = 10/73/568、`stm.b` N=8 = 17；同一对齐 ELF（md5 `10ceddca…`）`numCycles` 改前/改后均为 **2257（模型开）/1950（关）**（改前基线由改前二进制 md5 `dfc91359…` 实测记录）。
2. **相位正确**（Exec 轨迹 on/off 差值 = 每指令总拍）：`ldm.ub` N=8 相位 0 ⇒ 16、相位 1–7 ⇒ **24**；`ldm.ub` N=1 各相位 ⇒ 9；`stm.b` N=8 相位 0 ⇒ 17、1–7 ⇒ **25**；`ldm.uw` N=4 相位 0/2 ⇒ 12/20；`ldm.ut` N=2 相位 0/4 ⇒ 10/18；整趟 `numCycles` 2548+**128**=**3276**（跨相位样本 16 个 ×8 拍）。
3. **与 chipyard 对照**：`m16-chipyard-004` 的 362 个原始样本，相位式命中 **356/362（98%）**，6 个不符全是该任务已登记的 `stm.o` N=1 地址特例（+11×3、−1×3，非相位）；对齐式则错 **42 = 36 跨相位 + 6 特例**；头号样本 `ldm.ub` N=8 相位 2 = **24**（chipyard 与模型一致）。
4. **可达 FAIL**：策略级把公式改回 `(N*w+7)/8` ⇒ 8 条相位用例红（对齐用例仍绿）；真实源树注入 + 重建 ⇒ 相位用例全部红（16/17），`--expect injected` 全绿（证明红的正是相位项），`cp`+md5 还原 + 重建后回绿。
5. 门控：`check-wuming-cycles`/`check-gem5-decode`/`check-index-blobs` **rc=0**；`check-patch-tree` **gem5 段 0 问题、106 patch**（整仓 rc=2 来自 chipyard `m16-chipyard-012` 与 linux `m14-linux-024`，非本任务）。合并态：临时树套本任务 diff 到 master `795ff93e` 后上述门控同样 rc=0 / gem5 段 0 问题（master 期间只前进 ledger+linux 文件，与本任务文件不相交）。
   **实现口径（任务书要求写明）**：hook 时点**不变**（仍在 `timing.cc advanceInst` 之后），因此 `simInsts` 仍是「一条架构指令 = 1」（整块仍未拆微操作）。EA 在 hook 时读取：`ldm`/`stm` 的基址组与偏移寄存器在指令后仍是原值（`ldm` 拒绝目的块与地址寄存器重叠、`stm` 不写寄存器），唯独 `rb0` 是「当前 IP」而非寄存器 ⇒ 由 `DadaoInst::execute()` 入口新记的 `ISA::wumingInstAddr`（`advancePC` 之前）还原；D′ 寄存器复制不读该字段。

**新发现/坑**：① `rb0` 作为块传送基址时，hook 时点的 pc 已被 `advancePC` 推到下一条，不能靠寄存器或 pcState 取回。② SCons 用内容签名：一次**中途被 kill** 的构建会留下按注入内容编译的 `.o`，而后续 `touch` 不改内容 ⇒ 不重建，测到的仍是旧公式（本次被 E4 捕获，删 `isa.o`/`date.o` 后恢复）；正常（不中断）的注入—还原—重建流程不受影响。③ 生成器从仓库根跑时产物落在仓库内（`contracts/` + 源树），与任务书所述 cwd 坑一致，已确认。

**遗留问题**：无。整仓 `check-patch-tree` 的 chipyard/linux 段红属其它模块在途任务，未代修。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 首版 `run.sh` 用字符串比较 `"rc!=0"`/`">0"` ⇒ 恒 FAIL（或恒真） | ✅已修 | 加 `check_rc0`/`check_rcnz`/`check_gt0` 三个数值比较器 | `--inject full` 25/25 PASS |
| `check-patch-tree` 只匹配 `.*problem`，漏掉 `assertion ⑥/⑦` 行 ⇒ 导出前假绿 | ✅已修 | 改为统计「gem5 行中非 `N patch(es)` 的行数」 | 导出前实测 4（红）、导出后 0（绿） |
| 被 kill 的注入构建留下注入版 `isa.o`，SCons 内容签名不重建 ⇒ 实测旧公式 | ✅已修 | 删 `isa.o`/`date.o` 强制重编 | 重建后 E4/E0 回绿（19/19） |
| `rb0` 作基址时 hook 取不到当前 IP | ✅已修 | `inst.cc` 记 `ISA::wumingInstAddr`，`fillDynamicState` 用它还原 `rb0` | `ldm.o_rrri_rb` 等行相位用例、全 D 行扫描 |
| chipyard 对照把 aligned 失配数直接等同「跨相位样本数」，漏 6 个地址特例 | ✅已修 | 期望集 = 跨相位 ∪ 已登记特例（集合相等，不比值） | chipyard 10/10 |
| 注入还原只核 md5 不足以证明源树无残留 | ✅已做 | 同笔核 `git -C <源树> status --porcelain` 为空 | `I2 source tree clean after restore` PASS |

### 第 1 轮 reviewer 验收（中改档；命令全部我亲跑，输出/退出码为真实值）

**重跑记录**
1. 运行期证据目录内的 `run.sh` → `RESULT: PASS (19 checks)`、`EXIT=0`（注入还原后的终验亦 19/19）；内层探针 `checks=1316 fails=0`、gem5 逐指令 `checks=80 fails=0`、chipyard `checks=10 fails=0`。`run.sh --inject full` → `RESULT: PASS (25 checks)`、`EXIT=0`（与完成区 25/25 一致）。
2. 门控亲跑：`check-wuming-cycles rc=0`、`check-gem5-decode rc=0`、`check-index-blobs rc=0`；`check-patch-tree rc=2`，gem5 段仅 `106 patch(es)`、problem 行 **0**（红全在 chipyard 断言⑨/⑥ 与 linux 段，他任务）。
3. **独立改前基线**（固定 commit `e7fb353`，未用 HEAD/merge-base/`git log -1`；其源码确为旧式 `beats=(bytes+7u)/8u`、无 EA 字段）：4 文件换该 commit 内容（`cp`+md5 留档）→ 重建 `rc=0`（`isa.cc`/`inst.cc` 实际重编）→ **同一 ELF（md5 `10ceddca…`）phase0 = 2257/1950、phase1 = 3148/2548、simInsts 150/196**；当前构建 phase0 仍 **2257/1950**（8 B 相位零回归）、phase1 **3276** = 3148+128（16 跨相位 ×8）、simInsts 150/196 不变。
4. §5 实测点旧=新（探针 `aligned[]` 逐条断言通过、文档 §5 数字 `git diff` 0 改动）：`ldm.ub` N=1/2/3/5/8/16/63 = 9/10/11/13/16/32/127；`ldm.o` 1/2/3/8/16/63 = 9/18/27/72/144/567；`stm.o` 1/8/63 = 10/73/568；`stm.b` N=8 = 17（该点非 §5 表内，源自 `m16-gem5-001`/`005` 的实测记录，探针同断言）。
5. 相位实测（E4 轨迹，我亲跑）：`ldm.ub` N=8 相位 0 = 16、1–7 = **24**；N=1 各相位 **9**；`stm.b` N=8 = 17/25；`ldm.uw` N=4 = 12/20；`ldm.ut` N=2 = 10/18 —— 与任务书逐条一致。
6. 公式读代码核：`wuming_latency.hh` 为 `phase = addr % 8u; beats = (phase + bytes + 7u)/8u`、`bytes = elements*elemWidth` ⇒ 与 `beats=(addr%8+N*w+7)/8` 逐字一致；`nBase` 取值式与 `blockCopyCycles` 在补丁 diff 中 **0 行变化**；`contracts/wuming-cycles.yaml` 仅 `source_doc_sha256` 1 行变（263 条拍数 0 变化）。
7. chipyard 独立重算：14 文件 **362** 行；相位式失配 **6**、对齐式 **42**（= 36 跨相位 + 6 特例）；6 条全是 `stm.o` N=1、相位 0、地址 `0xffffff7ffff8`（+11）×3 与 `0xffffff012100`（−1）×3 ⇒ 正是 004 任务书登记的两个 N=1 地址特例（各 3 次），无其它误差混入。
8. **我的 1 路注入**（两路之外）：源树去掉 `addr%8` 项 → 重建 `rc=0` → `phase_measure` `EXIT=1`、`checks=80 fails=17`（相位用例 expected 24 got 16、`numCycles` 3148 ≠ 3276），`--expect injected` **80/80 全绿** ⇒ 红的正是相位项、对齐用例不受影响；`cp`+md5 还原 4 文件全等 → 重建 `rc=0` → 终验 `run.sh` **19/19**。
9. **坑核（陈旧 `.o`）**：基线/注入/还原三次构建二进制 md5 互不相同，且还原后相位用例实测回 24、`run.sh` 回绿 ⇒ 回绿是真绿，非内容签名漏重建。

**EA 论证核查**：hook 调用点 `simple/timing.cc advanceInst` 本任务未改（diff 仅 8 文件）⇒ 时点与 `simInsts` 口径不变（150/196 全等）；`rd0` 硬连 0、`rb0` = 当前指令地址（`inst.cc` 语义），`ldm` 目的块与地址寄存器重叠判非法（`exec/b1.cc`）、`stm` 不写寄存器 ⇒ hook 读到的仍是指令前值；`fillDynamicState` 仅 `base == 0` 才用记录的指令地址，其余读寄存器组 ⇒ **只影响 `rb0` 作基址**；48 位回绕是 8 的倍数、不改相位。**另实测 `rb0`**：临时载体 `ldm.ub {rd5:rd12}, [rb0, rd19]`（rd19 = 0/1/2，PC …104/10c/114）逐指令拍差 **24/24/24** = 按 `PC+rd19`（相位 4/5/6）的期望；若误记 `PC+4` 首条应为 16 ⇒ 还原的确是当前指令地址。

**合并态**：master `82581810` + 本任务 8 文件 diff（`git apply` rc=0）临时树 ⇒ `check-index-blobs rc=0`、`check-patch-tree rc=0`（gem5 `106 patch(es)`）；`check-wuming-cycles`/`check-gem5-decode` 在该临时树因**缺生成产物**被环境挡下（语义子项全 PASS，缺 gem5 源码树内的生成表/解码产物），二者在本任务树均 `rc=0`。临时树已 `worktree remove rc=0`。

**约束核验**：未改仓库代码（本任务 worktree `git status -uall` 审前审后均空、仅本记录待提交；gem5 源码树 `status` 空）；未提交 git；构建落在运行期目录（跑前临时盘可用 15 G，未占临时盘）；证据一律写「运行期证据目录内的 `run.sh`」；术语用「寄存器组」。

**发现（不阻断）**：① `components/gem5/changelog.md` 写「策略探针 1310 条」，实测 **1316**（文档级笔误，收尾顺手改）；② `make check-knowledge-refs rc=2`：2 处具体运行期证据脚本路径引用全在 `m16-gem5-017` 任务书（master 已含、非本任务 diff），属 017 记录的文档问题；本记录写入后该计数仍为 2、未新增。

**判决：Accepted**（19/19 + 25/25、4 门控 gem5 段 0 问题、独立基线 2257/1950 相等、相位 24/17/12/10 逐条命中、我的注入红 → 还原回绿）
