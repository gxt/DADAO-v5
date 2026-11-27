# m16-chipyard-018: cfx4 RTL PTW/TLB 探针纳管

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-testcases-010`（cfx4 case id/期望已落 `tests/arch/ptw`）
**可并行分片**：否
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

现有 RTL 的 cfx4 探针散在 `tools/chipyard/ptw/{vastptw,vastwalk}` 与 `tlb/vasttlb`，检查点与 QEMU 的 15 条不完全对应。`m16-testcases-010` 已把 QEMU 侧纳管；本任务把 RTL 侧接入同一 case id / expected，形成三方中的 RTL 一方。

## 要做

1. **迁入**：`tools/chipyard/ptw/**`、`tlb/vasttlb*` 的载体/生成器/check 脚本落 `tests/arch/ptw/`（RTL 后端），迁完删旧目录（按 `discussing` 落点）。
2. **对齐 case id**：RTL 探针的检查点映射到 `m16-testcases-010` 的 15 条 case；缺的补、多的登记为额外检查点。
3. **签名统一**：RTL 侧用 `tests/shared/signature.py` 与 `tests/shared/asm/signature.inc`（`__REC`→`SIGUPD` 已是同机制），host 侧不另写解析器。
4. **三方跑**：`run_arch.py --cfx 4 --platforms qemu,gem5,chipyard` 三方逐槽一致；不一致登记 `expected-divergences.yaml`。
5. **Tiny 不回归**：Tiny 无 PTW，既有代表例不变。

6. **HSU 覆盖**（用户 2026-11-22：HSU 纳入、J 不纳入）：RTL 侧 PTE 的 `H`/`S`/`U` 与 `R/W/X` 组合逐条对齐 QEMU/gem5；J 位不测，未覆盖项写入清单。

**H/S/U 三模式**（用户 2026-11-22）：cfx4 的 RTL 探针应在 `hmon`/`smon`/`umon` 三种运行模式下各跑一次（复用 `tests/arch/common/env/`）；权限不允许的模式显式标注 `modes` 排除原因。

## 不做

- 不改 PTW/TLB 的实现语义（只纳管探针；实现缺口另立任务）；
- 不改 QEMU/gem5。

## 约束

- 独立 `git worktree`；**不提交 git**；RTL 探针集中 `tests/arch/ptw/`；
- 重建环境写进证据脚本；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. RTL 探针逐条跑通，签名与 QEMU/gem5 逐槽一致（或登记差异）；
2. 15 条 case 的 RTL 在位情况现场统计（缺的写「缺」+ 原因）；
3. **可达 FAIL**：改一条 RTL 记录值 ⇒ 红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：返工后 `run.sh` 的 **A 段 11/11 PASS（rc=0）**（新增「旧基名 0 命中」「`gen_vastdcache_tables --emit inc` rc=0」）；此前 `run.sh --full` **PASS=68 FAIL=0**（rc=0，A 段新增 3 项后口径为 71），`run.sh --inject` **PASS=13 FAIL=0**（rc=0，3 路：RTL 记录值、DIV-14 登记值、删除 DIV-14）。cfx4 的 RTL 承载 **12/15 measured**（signature 3 + guest 9）、**3/15 gap**（013/014/015，原因与 `close_when` 在 `rtl-coverage.yaml`）；三方 `run_arch --cfx 4 --platforms qemu,gem5,chipyard` **12 ok / 3 gap / 0 failure**。Tiny 未改动（无 PTW 路径）。
**修改文件**：`tools/chipyard/dcache/{gen_vastdcache_tables.py,check_vastdcache.py}`（返工：cfx4 checker 迁址后的加载路径 + 注释）；新增 `tests/arch/ptw/{ptw_regs.S,ptw_regs.lds,check_ptw_regs.py,ptw_walk.S,ptw_walk.lds,gen_ptw_walk_tables.py,check_ptw_walk.py,ptw_tlb.S,ptw_tlb.lds,gen_ptw_tlb_tables.py,check_ptw_tlb.py}`（由 `tools/chipyard/{ptw,tlb}/` 迁入，命名规范化）、`tests/arch/ptw/{ptw_sig.S,ptw_sig.lds,gen_ptw_sig_tables.py,check_ptw_rtl.py,rtl-coverage.yaml,README.md}`；删 `tools/chipyard/ptw/**`、`tools/chipyard/tlb/**`（11 个文件）；改 `tests/arch/{common/platform.py,common/signature.py,run_arch.py,modes.yaml,expected-divergences.yaml,README.md,PLAN.md,vast-arch-inventory.md}`、`components/chipyard/README.md`；本任务书。
**验收结果**：① 三方签名逐字节：002 = `1122334455667788 1122334455667788 800000006100ffe1`、006 = `800000006000ffe1 800000006000ffed 800000006100ffe1`（qemu/gem5/chipyard 全同）；007 前两槽全同，后两槽 RTL `0/0` 按 **DIV-14** 判（QEMU/gem5 为 `0xfffffffffff8/2`）。② RTL 探针：`ptw_walk` rc=0、31 槽/248 B；`ptw_tlb` rc=0、54 槽/432 B（781 s，`PTW_TLB_FULL=1`）；`ptw_regs` 保持既有 TL `A' channel re-used a source ID` 断言（KNOWN-RED，非本任务引入）。`gen_vastdcache_tables.py --emit inc` 返工后 **rc=0**（109 个 `.equ`），旧基名在 `tools/tests/Makefile*/components` **0 命中**。③ H1 改 RTL 记录值 ⇒ 002 rc=1；H2 DIV-14 值 0→1 ⇒ 007 rc=1；H3 删 DIV-14 ⇒ `--selfcheck` rc=1；均 `cp`+md5 还原后回绿（md5 相等）。④ 模式：`--mode smon/umon` 显式 rc=2 + 原因；hmon rc=0；`modes.yaml` 15 条 ptw 均 `[hmon]`。⑤ `check-tests-index`/`check-tasks`/`check-knowledge-refs`/`check-dirs`/`check-no-residue` rc=0；`check-patch-tree` 的 chipyard 段 **0 problem**（26 补丁；全局 rc=1 为 qemu/gem5/linux/musl 的并发源树 KNOWN-RED，ISS-463/507）。⑥ 013 的 RTL 实测（运行期证据目录 `diag-013`）：hmon 读 `cfx_pmem SRAM` ⇒ cause `0200000000000002`（CFXMEM + [57] NONPTW）、info `000083ff00001000`（= 该地址）⇒ 该窗口不是 cfx 旁路，登记 gap。
**新发现/坑**：① `WumingPtw:` 的 `ad-wb`/evict 事件只在仿真器 `+verbose` 下输出，`chipyard_engine` 默认不传 ⇒ 迁入 checker 的日志面未纳入判据（记录面已覆盖）；建议引擎加可选 verbose。② RTL 的 `ptw_tlb` 镜像 loadmem 逐字验证约 781 s（1.5 MB），证据脚本用 `PTW_TLB_FULL=1` 否则跳过——不得进 L2。③ RTL 的 PA RAM 全可写 ⇒ 运行期构造不出 A/D 回写失败（与 DIV-04 同源）⇒ DIV-14。④ L1 表项 `SP=0` 是**表指针**，不能直接放叶 PTE（008 首版把它当叶 ⇒ 走查读数据页当表、挂死）；`L1B→L2B→叶` 后通过。⑤ `clean` 只回写**已挂起**的位：只读不写 ⇒ A=1/D=0；QEMU 的 006 先 store 再 clean 才得 A1D1（首版漏 store ⇒ 断言 30 红）。⑥ U/S 进入链不在 RTL step5 测试路径（`tests/ee-vast/README.md`），S/U 运行模式与 S/U PTE 轴登记为缺口；H 轴由 011 覆盖。⑦ RTL 复用 Tiny 地址图（`ENTRY=0xffffff010100`），DIV-12 的 BootROM 几何同样适用。⑧ 跨目录 import 用 `HERE.parent / "ptw" / "check_vastptw.py"` 这类**拼接路径**，全路径 grep 抓不到；迁移必须按**基名** grep + 跑一遍所有引用方的生成器/自检（返工 blocker 即此）。
**遗留问题**：① 013（cfx 空间旁路）/014（ADWBFAIL 停止点）/015（ILLI `cause_info`）是 `rtl-coverage.yaml` 登记的 gap（`close_when` 已写），需后续任务补探针/承载。② smon/umon 三模式未跑（`modes.yaml` 显式原因）：需把 ptw case 迁到 `common/env-{smon,umon}` 并补 U/S 进入链。③ `ptw_regs` 的 TL 断言是既有 KNOWN-RED（016/019 已记录），未追根因。④ Tiny 代表例未实跑，只做「源文件 0 改动」断言（无 Tiny/PTW 路径）。⑤ 未登记 `tests/arch.yaml` 新条目（RTL 走同 case 的 chipyard 后端，不新增 case）；若后续要把 gap 升为 case，须同步索引与台账。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：迁移/改名后的 11 个文件路径与判据来源；`ptw_sig.S`（12 个 case 的地址/PTE/故障回落/槽序）；`gen_ptw_sig_tables.py`（几何、cause 解析、与 `expected.yaml`/DIV 的双向核对）；`check_ptw_rtl.py`（构建/运行/差异/自检/gap 退出码）；`platform.py`/`run_arch.py`（chipyard 后端、GAP、逐槽差异、cross 比较）；证据脚本（rc 捕获、注入还原、防空注入）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `ptw_tlb.S` 仍在用已删除的 `LOAD_ADDR`（无法汇编） | ✅已修 | 全部改 `set.rb`（迁入后命名/工具链一致） | mc/ld rc=0，54 槽/432 B |
| F2 三个 checker 各带 `unpack` 解析器，违反「host 侧不另写解析器」 | ✅已修 | 改 `tests/shared/signature.parse`；`grep struct.unpack/int.from_bytes`=0 | 三个 `--self-test` rc=0；证据 B 断言 0 |
| F3 RTL 的旧探针数据 magic/几何与 QEMU 不同，无法逐槽比较 | ✅已修 | 新增 `ptw_sig.S` 用 QEMU 同一组 DA/DB/DC/PTE；002/006 逐字节相同 | 三方 `signature_slots` 3/3/3，hex 相同 |
| F4 007 的 ADWBFAIL 后半在 RTL 不可构造 | ✅已修 | `rtl-coverage.yaml` 记 gap 语义 + DIV-14 两槽，`--selfcheck` 核对登记 | 007 前两槽相同；PASS with 2 DIVERGED slots |
| F5 005 在 PTE 改成 DC 后仍期望 M1（断言 22 红） | ✅已修 | 期望改 M3 | 单跑 rc=0 |
| F6 006 首版 clean 前没有挂起 D ⇒ A1D0（断言 30 红） | ✅已修 | clean 前先 store M4（与 QEMU 006 同序） | 单跑槽 = expected.yaml |
| F7 008 把叶 PTE 放 L1（SP=0 被当表指针）⇒ 挂死 | ✅已修 | 新增 `PT_L2B`，`L1B→L2B→DB 叶` | 单跑 rc=0，断言 41–45 通过 |
| F8 gap case 的 work 目录不存在，写 `run.json` 崩溃 ⇒ rc=1 | ✅已修 | `work.mkdir` 前置 | 013/014/015 rc=77 |
| F9 驱动缺 `--sim` 时默认成 Tiny 仿真器 | ✅已修 | `DEFAULT_SIM` 固定 WumingVastConfig | `--only 013` 默认路径 rc=77 |
| F10 chipyard 后端接入后，`run_arch` 仍会把登记 gap 当 FAIL；cross 按原始字节比会误判 DIV | ✅已修 | `platform._collect` 识别 77=GAP；`run_arch` 逐槽比较 + `diverged_slots`；GAP 不进比较 | 三方 rc=0，12 ok/3 gap，007 2 槽 DIV-14 |
| F11 迁入 checker 的日志面需要 `+verbose`，共享引擎默认不传 | ✅已修（判据面） | 以记录面为判据（签名槽即观测通道）；日志面不改共享引擎，转入遗留 | `ptw_walk` 31 槽、`ptw_tlb` 54 槽 rc=0；遗留② |
| F12 未使用的 import / 旧路径文档残留 | ✅已修 | 删 `shutil`；更新 README/PLAN/inventory/components README | `check-knowledge-refs` rc=0 |
| F13（reviewer 阻断）`tools/chipyard/dcache/gen_vastdcache_tables.py` 仍按拼接路径加载已删的 cfx4 checker ⇒ `--emit inc` rc=1 | ✅已修 | 改为 `HERE.parents[2]/tests/arch/ptw/check_ptw_regs.py` 的 `bit_table`；两处注释同步；证据 A 段加「11 个旧基名 0 命中」+「dcache 生成器 rc=0」 | `--emit inc` rc=0（109 `.equ`）；`ONLY=A` 11/11 rc=0；`check_vastdcache --self-test` 11 case/0 surprise |

判决：F1–F13 全部处置（F11 以记录面为判据、日志面转遗留，不改共享引擎；F13 为 reviewer 阻断项，返工已修）。状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（运行期证据目录内的 `run.sh`，按档位分段 `ONLY=`，覆盖 A–H，合计 PASS=68/FAIL=0 与完成区一致）**：
- `ONLY=A,B,F,G` **rc=0（PASS=24）**：旧目录 absent、迁入 16 文件在位、`check-tests-index`/`check-tasks`/`check-knowledge-refs`/`check-dirs`/`check-no-residue` 均 rc=0；`check-patch-tree` chipyard 段 problem=0（26 补丁），`--selfcheck`/`--self-test` 全 rc=0；`--mode smon/umon` rc=2+原因、hmon rc=0、modes 15 条 `[hmon]`；Tiny/其它 cfx 改动数 0。
- `ONLY=C PTW_TLB_FULL=1` **rc=0（PASS=9）**：ptw_walk 248 B/31 槽、ptw_tlb 432 B/54 槽、ptw_regs guest=None 且 TL 断言 present。
- `ONLY=D` **rc=0（PASS=20）**：12 measured rc=0（002/006/007 签名字节逐槽 = expected.yaml+DIV-14）、3 gap rc=77、measured=12/gap=3 现场统计。
- `ONLY=E` **rc=0（PASS=2）**：`cases=15 ok=12 gap=3 failures=0`，007 `diverged_slots={2,3}=DIV-14`；`run.sh --inject` **rc=0（PASS=13）**（H1/H2/H3 红→还原 md5 相等→回绿）。

**独立注入（我本人，`cp`+md5，未用 git checkout/restore/stash）**：I1 改 `ptw_sig.S` case6 槽0 +1 ⇒ `ONLY=D` **rc=1**（006 两条 FAIL），还原 md5=`d68f908d…` ⇒ **rc=0**；I2 `rtl-coverage.yaml` 002 改 guest ⇒ `ONLY=B` **rc=1**，还原 md5=`858ae2e3…` ⇒ **rc=0**；I3 DIV-14 槽2 值 0→1 ⇒ `ONLY=B` **rc=1**（gen/rtl selfcheck 双红），还原 md5=`a8fec471…` ⇒ **rc=0**。

**逐项核验**：迁移=旧目录已删、17 新件+11 删+10 改与完成区逐项对账、无 `data/`、命名合 018；期望真源 `tests/arch/ptw/expected.yaml` 由 m16-testcases-010 提交且本任务 `git diff` 空（非从 RTL 反推）；三方三引擎实证不同二进制（qemu-system-dadao / shim 实跑 gem5.opt 留 wrapper 留痕 / Verilator RTL），非同源自比；007 真差异（qemu/gem5 `0xfffffffffff8`/2 vs RTL `0/0`，我从 run.json 独立解码），DIV-14 只作用登记两槽（其余槽仍比规范值）、`close_when` 在、值漂移即红（H2/I3 同一 `g != declared` 判据）；gap 013 我独立解码 semi 流（cause `0x0200000000000002`、info `0x83ff00001000`）属实，014/015 原因属实；KNOWN-RED：ptw_regs 断言 3 行与 019 基线 diff rc=0/md5 同，`check-patch-tree` 错误集与 master 基线 22 行逐行相同（计数断言，无 `|| true` 掩盖）。

**阻断 finding（判 Needs Revision 的根因）**：`tools/chipyard/dcache/gen_vastdcache_tables.py:146-148` 仍加载已删除的 `tools/chipyard/ptw/check_vastptw.py` ⇒ 本树实跑 `python3 tools/chipyard/dcache/gen_vastdcache_tables.py --emit inc` **rc=1 FileNotFoundError**，master 基线 **rc=0**；`vastdcache_tables.inc` 不入库 ⇒ dcache 探针无法重建；完成区 F12「grep 旧路径 0」不实（漏了拼接路径）。**修法**：加载目标改 `tests/arch/ptw/check_ptw_regs.py` 的 `bit_table`（迁入同源），同步 `check_vastdcache.py:5`/`vastdcache.S:5` 注释；证据脚本 A 段加「已删文件基名在 `tools/ tests/ Makefile* components/` 0 命中 + 该生成器 rc=0」断言；改后重跑 `ONLY=A`。
**非阻断 finding**：① `check_ptw_rtl.py` 文档串把 004 写作 `partial`，清单实为 `guest`（文档级，architect 收尾改）；② 两个 issue 均**应立**：S/U 模式迁移（必立，对应用户 2026-11-22 三模式要求）、`chipyard_engine` 可选 `+verbose`（低优，记录面已覆盖判据）。
**快照对账**：验收前后 `git status --porcelain -uall` 均 38 行、md5 相同，与完成区「修改文件」17 新+11 删+10 改逐项一致（本审阅记录只追加于任务书，不新增文件）。

**判决：Needs Revision** —— 仅迁移残留一处（上段阻断 finding，命令与 rc 见上）；其余验收项在我自己的重跑下全部通过。

### 第 2 轮 engineer 返工（回应 reviewer Needs Revision）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1（阻断）dcache 生成器按拼接路径加载已删的 cfx4 checker ⇒ `--emit inc` rc=1 | ✅已修 | `tools/chipyard/dcache/gen_vastdcache_tables.py` 改 `HERE.parents[2]/tests/arch/ptw/check_ptw_regs.py` 的 `bit_table`（同一 contract-see 解析）；`check_vastdcache.py` 注释同步；`tests/arch/PLAN.md`、`tests/arch/ptw/README.md` 去掉旧基名（改目录级描述） | `python3 tools/chipyard/dcache/gen_vastdcache_tables.py --emit inc` **rc=0**（109 个 `.equ`）；`check_vastdcache.py --self-test` 11 case/0 surprise；旧基名 11 个在 `tools/tests/Makefile*/components` **0 命中** |
| R2（非阻断）`check_ptw_rtl.py` 文档串把 004 写成 `partial` | ✅已修 | 004 归入 `guest`；`partial` 标为「当前无条目」 | `grep "partial（004）"` 0 命中；`--selfcheck` PASS |
| R3 证据 A 段缺「旧基名 0 命中」与 dcache 生成器 rc 断言 | ✅已修 | A 段新增 3 条：11 个基名 0 命中（按基名，不按全路径）、`--emit inc` rc=0、inc 非空 | `ONLY=A` **rc=0（PASS=11 FAIL=0）** |
| R4 注入仍须红/还原绿 | ✅已复跑 | 未改注入逻辑 | `ONLY=H` **rc=0（PASS=13 FAIL=0）**；H1/H2/H3 红后 `cp`+md5 还原均相等（`d68f908d…` / `a8fec471…`） |

返工约束核验：未提交 git；未用 `git checkout/restore/stash`；还原一律 `cp`+md5；未改 `spec/`、契约、QEMU/gem5 实现。状态 `待验收`。

### 第 2 轮 reviewer 验收（返工复核，小改档）

**阻断项闭环（全部我本人重跑）**：
- `python3 tools/chipyard/dcache/gen_vastdcache_tables.py --emit inc` **rc=0**、**109 个 `.equ`**，输出 md5 与 master 基线**逐字节相同**（`b3dc462b…`）⇒ `bit_table` 语义未变（仍 `contract-see §6.1/§6.1.1` + ADR-0056 现场解析与互校，只换加载路径 `HERE.parents[2]/tests/arch/ptw/check_ptw_regs.py`，该文件模块级无副作用）；`tools/chipyard/dcache/check_vastdcache.py --self-test` **rc=0**（11 case/0 surprise）。
- 基名 grep（我做：11 个旧基名 × `tools/ tests/ Makefile* components/`）：**0 命中**（`grep -rn "vastptw|vastwalk|vasttlb" … | wc -l = 0`）。
- 运行期证据目录内的 `run.sh`：`ONLY=A` **rc=0，PASS=11/FAIL=0**（含新增 3 条：11 基名 0 命中、dcache 生成器 rc=0、inc 非空=109）；`run.sh --inject` **rc=0，PASS=13/FAIL=0**（H1/H2/H3 红 → `cp`+md5 还原 `d68f908d…`/`a8fec471…` 相等 → 回绿）。
- **新断言可达 FAIL（我独立注入）**：给 `gen_vastdcache_tables.py` 追加 `vastptw.S` 注释 ⇒ `ONLY=A` **rc=1**（`HIT 旧基名 vastptw.S` + `expected=0 actual=1`），`cp`+md5 还原 `c3402785…` 相等 ⇒ 重跑 `ONLY=A` **rc=0（PASS=11）**。
- 文档/对账：`check_ptw_rtl.py` 004 归 `guest`（文档串改「`partial`（当前无条目）」）；`tests/` 内旧基名 0 残留；完成区「修改文件」已补 2 个 dcache 文件，与 `git status`（40 行，与本轮开工快照 md5 相同 `75c01643…`）逐项一致；本轮 diff 仅 2 个 dcache 文件 + 任务书，未触及第 1 轮已核项。

**判决：Accepted** —— 第 1 轮阻断项（迁移残留）已闭环，验收命令在我自己的重跑下全部通过、约束无违反；遗留两条 issue 仍应立（S/U 模式迁移为必立、`chipyard_engine` 可选 `+verbose` 低优），最终接受由 architect 终审。
