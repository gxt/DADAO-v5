# m16-gem5-020: gem5 cache 前置与接线（StaticInst flags + `--caches`）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-testcases-004`（盘点）已合入；`m16-gem5-019`（D21 差异）
**可并行分片**：否
**预估**：2–3 h（flags + 配置，不含 cfx5 命令；标定：同档最近 5 件派单→合入实测中位）
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

`m16-gem5-019` 的 D21：`src/arch/dadao/inst.cc` 只置 `IsInteger/IsFloating/IsInvalid/IsNonSpeculative`，`opClass` 恒 `IntAluOp`，未置 `IsLoad/IsStore/IsAtomic`。

**实测订正（本任务 reviewer 核验，2026-11-22）**：原假设「不置 flags ⇒ 开 cache 后 cache 不工作」**不成立**。`AtomicSimpleCPU::readMem/writeMem` 直接 `sendPacket(dcachePort)`，不经 `isMemRef()`；`isMemRef()` 只在 `base.cc` 的 `numMemRefs` 统计与 `timing.cc` 的 timing 访存分支被消费，`numLoadInsts/numStoreInsts` 由 flags 门控。因此去 flags 后 dcache 仍命中（`93/17`），只有 `loads/stores` 由 `55/55` 变 `0/0`。但置 flags 后 Timing 会到达 `StaticInst::initiateAcc` 的默认 panic ⇒ 必须同时补 `initiateAcc()`。

裁定（`discussing.md`「M16 三方差分（Vast arch）批次裁定」）：gem5 用 Classic cache，`cache-model=on` 映射 `--caches`；cache 只服务 arch 功能覆盖，周期判据不进本轮。**本任务只做前置与接线，不实现 cfx5 命令**（下一任务）。

## 要做

1. **StaticInst flags**：在 `src/arch/dadao/inst.cc` 按解码结果设置 `IsLoad`/`IsStore`/`IsAtomic`（以及必要的 `opClass`：`MemReadOp`/`MemWriteOp`），来源用现有 decoder 的 mm/load/store 分类；不得引入第二套分类表。
2. **`--caches` 接线**：`configs/dadao/fs.py` 增加 L1 I/D cache 参数（大小/相联/行宽，默认与 RTL 一致：8 路 × 128 组 × 64 B），由 `cache-model=on` 或 shim 映射打开；`off` 路径（默认）不加 cache，行为与现在逐字节相同。
3. **`qemu_gem5_shim.py`**：把 `-machine ...,cache-model=on` 映射为 gem5 `--caches` + L1 参数；`off` 不加。
4. **不回归**：Atomic/Timing 现有测试（`run_inst_tiny` 01 册、`run_m5_e2e --profile vast`）在 `off` 下不变；`on` 下至少能启动并完成一个最小访存程序。

## 不做

- 不实现 cfx5 寄存器/命令（`m16-gem5-021`）；
- 不改 `src/cpu/simple/**`、不改 cache 组件；
- 不设周期阈值、不改周期表口径。

## 约束

- 独立 `git worktree`；**不提交 git**；组件改动按 `docs/Process-01` 导出补丁（`make_patch.py gem5` 幂等），显式 staging；
- 不改 `spec/`/契约；术语「寄存器组」；
- 不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. **可达 FAIL 两路**（按实测口径，原文「去 flags ⇒ cache 不命中」已证伪）：① 去掉 `IsLoad/IsStore` 注入 ⇒ `numLoadInsts/numStoreInsts` 归零（`55/55→0/0`）⇒ 红；② 让 `fs.py` 忽略 `--caches` ⇒ `dcache demandHits/Misses=0/0` ⇒ 红。两路均 `cp`+md5 还原后回绿；
2. `cache-model=off`：`run_inst_tiny` 01 册 38/38、`run_m5_e2e --profile vast` 10/10，与改前逐字节/逐例相同；
3. `cache-model=on`：最小访存程序跑通，`dcache` 有命中/缺失统计；与 `off` 的签名一致（功能不因 cache 改变）；
4. `check-gem5-decode`、`check-patch-tree`（gem5 段 0 problem）、`check-index-blobs` 记录 rc；
5. `--inject` 至少 2 路（去 flags / 去 `--caches` 映射）⇒ 各自红，还原回绿；
6. `make check-tasks` 记录 rc。

## 完成区

**测试结果**：运行期证据目录内的 `run.sh` → 28/28 PASS（rc=0）；`--inject all` → 43/43 PASS（3 路注入：flags / fs.py 忽略 `--caches` / shim 去映射；各「注入红→`cp`+md5 还原→回绿」）。关键：atomic 01 册 38/38、`--cpu-type timing` 01 册 38/38、timing `--max-insts 500` 停在 500、`run_m5_e2e --profile vast` 10/10、cache-on `dcache demandHits/Misses=93/17` 且签名与 off 逐字节相同（`cmp` rc0）。
**修改文件**：组件源 `src/arch/dadao/inst.cc`、`src/arch/dadao/inst.hh`、`configs/dadao/fs.py`（已收敛 base+1 并导出补丁）；`components/gem5/patches/{configs/dadao/fs.py,src/arch/dadao/inst.cc,src/arch/dadao/inst.hh}.patch`；`components/gem5/changelog.md`；`tools/testcases/parity/qemu_gem5_shim.py`；运行期证据目录内的 `run.sh`。
**验收结果**：`build_gem5.py` PASS；`check-gem5-decode` rc0；`check-index-blobs` rc0；`make check-tasks` rc0；`make_patch.py gem5` 重跑 `0 written`（幂等）；`check-patch-tree` 整树 **rc2**，其中 **gem5 段 0 problem**，10 个 problem 全在 **musl 段**（共享 `.work/source/musl` 与 `components/musl/patches` 预存漂移，非本任务改动；证据脚本按 gem5 段断言并注记整树 rc）。
**新发现/坑**：① 任务书 D21 的「不置 flags ⇒ 开 cache 后 cache 不工作」**不成立**：`AtomicSimpleCPU::readMem/writeMem` 在 `accessMem()` 里被直接调用，不经 `isMemRef()` 门控；实测去掉 flags 后 `dcache demandHits/Misses` 仍 93/17，只有 `commitStats0.numLoadInsts/numStoreInsts` 55/55→0/0。故 flags 注入的红改以「分类统计归零」为可达判据，cache 统计另以「fs.py 忽略 `--caches`」注入证明可红（hits=0）。② 仅置 flags 会让 `TimingSimpleCPU` 改走两段式并 panic「initiateAcc not defined」⇒ `inst.{hh,cc}` 增 `initiateAcc()`（同步完成 `execute()` 并镜像 `countInst()`，否则 `totalInsts()`/`--max-insts` 漏掉全部 ld/st）；timing 38/38 与 max-insts=500 已验。③ `check-patch-tree` 整树红勿误归因本任务。
**遗留问题**：① musl 段 10 problem 为共享树预存漂移，未处置（非本任务文件集）；② 只验 classic L1 功能覆盖，周期判据/PTW 延迟不在本轮（任务书「不做」）；③ cache 规模 N35（256/512 KiB）仍未裁定，本任务按任务书 64 KiB/L1 落地。**待裁定**：无（D21 判据按实测口径调整，见「新发现/坑」①）。

## 审阅记录

### 第 1 轮 engineer 自审

**结论**：只动 3 个组件源文件 + shim + 组件 changelog；未改 `src/cpu/simple/**`、未实现 cfx5、未动 `spec/`/契约；组件源 worktree 干净且 `base..HEAD == 1`；补丁重导出幂等；证据脚本 3 路注入均真红、还原真绿。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 无条件置 `IsLoad/IsStore` 使 TimingSimpleCPU 走 `initiateAcc` 并 panic | ✅已修 | `inst.hh` 声明、`inst.cc` 实现 `initiateAcc()` = `execute()` + 镜像 `countInst()` | FS timing 01 册 38/38；`--max-insts 500` → `simInsts=500`；SE timing crc32 输出==atomic |
| F2 任务书「去 flags ⇒ cache 不命中」不可达（cache 访问不经 flags 门控） | ✅已证伪并换可达判据 | flags 注入判据改为 `commitStats0.numLoad/numStore==0`；另加 fs.py 去 `--caches` 注入使 dcache hits=0 | 去 flags：hits/misses=93/17、loads/stores=0；fs 注入：hits=0 |
| F3 shim 模块 docstring 初版重复一段 `[,cache-model=...]` | ✅已修 | 删除重复，保留两行说明 | `--help` 与 diff 复核 |
| F4 证据脚本 `cache_probe` 未建 outdir，首跑 rc=1 | ✅已修 | 加 `mkdir -p "$dir"` | 重跑 28/28 |
| F5 整树 `check-patch-tree` rc2 易误读为本任务红 | ✅已隔离 | 脚本断言 gem5 段 0 problem，整树 rc 仅记录并注记 musl | 日志 `gem5: assertion` 计数 0 |
| F6 `parse_machine` 返回项 3→4，调用点已同步 | ✅已修 | 唯一调用点解包 4 元组 | shim `--help`/on/off/bogus 三例 rc0/0/2 |
| F7 `initiateAcc` 用 `dynamic_cast<SimpleExecContext*>`；O3/Minor 未接 | ❌不修 | — | 任务范围仅 atomic/timing 两类；O3/Minor 本就不支持 DADAO 同步访存 |
| F8 注入重建可能未真生效（假红/假绿） | ✅已防 | 注入/还原后都比对 `gem5.opt` md5，且还原比源文件 md5 | 脚本 `binary rebuilt`/`restored (cp+md5)` 全 PASS |

### 第 1 轮 reviewer 验收

**重跑（本人执行，worktree 根，不采信完成区）**：`bash 运行期证据目录内的 run.sh` → `SUMMARY: pass=28 fail=0 inject=none`，**rc=0**；`bash 运行期证据目录内的 run.sh --inject all` → `SUMMARY: pass=43 fail=0 inject=all`，**rc=0**（3 路注入各自「注入红 → `cp`+md5 还原 → 回绿」：flags 路 hits/misses 93/17、loads/stores 55/55→0/0，还原 md5 `848927ea…` 相等后回绿；fs 路 hits=0→回绿 93/17；shim 路无 `--caches`→回绿）。与完成区 28/28、43/43 完全一致。

**独立注入（reviewer 自做，非采信脚本）**：把运行期 gem5 源树 `configs/dadao/fs.py` 的 `if args.caches:` 改为 `and False`（注入后 md5 `70d52721…`）⇒ 同一 `run.sh` → `SUMMARY: pass=21 fail=7`，**rc=1**，含 `on: … hits=0 misses=0`、`dcache/icache size`、`on timing … icacheHits=0` 诸红；`cp` 回写后 md5 `b6f68ec5…`（与注入前逐位相等）⇒ 重跑 `SUMMARY: pass=28 fail=0`，**rc=0**。全程未用 `git checkout/restore/stash`；前后 `git status --porcelain -uall` 快照逐行相等，7 个改动文件 md5 前后相同，运行期 gem5 源树 clean。

**D21 订正核验（源码 + 我的实测）**：任务书「不置 flags ⇒ 开 cache 后 cache 不工作」**不成立**，订正成立——
- `src/cpu/simple/atomic.cc`：`AtomicSimpleCPU::readMem/writeMem` 自建 Packet 后 `sendPacket(dcachePort…)`，全文件无 `isMemRef`/flags 门控；`atomic.cc:684` 恒走 `curStaticInst->execute()` + `postExecute()` + `countInst()`，不经 `initiateAcc`；
- `isMemRef()` 只在 `src/cpu/simple/base.cc:441`（`numMemRefs` 统计）与 `src/cpu/simple/timing.cc:862`（timing 访存分支）被消费；`numLoadInsts/numStoreInsts` 在 `base.cc` 由 `isLoad()/isStore()/isAtomic()` 门控。
- 原假设错在把「flags 只喂统计与 TimingSimpleCPU 分支」当成「cache 访存的门控」；我重跑注入路实测：去 flags 后 dcache 仍 `hits/misses=93/17`，仅 `loads/stores` 55/55→0/0。timing 数据面本就 functional（m16-gem5-006/015），flags 也不影响 timing 的 dcache。

**`initiateAcc()`**：必须补——`src/cpu/static_inst.hh` 默认 `panic("initiateAcc not defined!")`，置 flags 后 timing `isMemRef()` 分支必达该 panic；实现 = `execute()` + 镜像 `countInst()`（timing 访存分支只调 `postExecute()`、不调 `countInst()`），与非访存分支逐项等价（`numInst`/`numOp` 同一 `SimpleExecContext`，DADAO 无 microop）；atomic 路径根本不调它，故无影响；**未越界**改 `src/cpu/simple/**`（仓库 diff 仅 6 个文件）。旁证：timing 01 册 38/38、`--max-insts 500` → `simInsts=500`。

**配置/接线**：`fs.py` 默认 `L1_SIZE=64KiB`、`L1_ASSOC=8`、`L1_LINE_SIZE=64`（8 路 × 128 组 × 64 B），`system.cache_line_size` 取 `--l1-line-size`；实测 `config.ini` `size=65536`、`assoc=8`、`block_size=64`（icache 同）；`off` 路 0 个 `type=Cache`、端口直连 membus；atomic 与 timing 两路径都建 L1（timing `icache demandHits=1091`、dcache 无数据访问＝既有设计）。

**不回归/补丁/门控（我自跑）**：off 01 册 `38/38 镜像通过` 且 0 条 `[FAIL]`（atomic、`--cpu-type timing` 各一遍）、`run_m5_e2e --profile vast` → `Results: 10/10 passed` + `run_m5_e2e: PASS`；on 下最小访存程序跑通、签名与 off `cmp` 相同；`check-gem5-decode` rc=0、`check-index-blobs` rc=0、`check-tasks` rc=0、`check-knowledge-refs` rc=0；`make_patch.py gem5` 重跑 `0 written, 106 unchanged`；`check-patch-tree` gem5 段 0 problem、整树 rc=2（10 problem 全在 musl 段；本任务未碰 musl、musl 源树 clean、仓库无 musl 改动 ⇒ 预存漂移，与完成区注记一致）。

**约束逐条**：独立 worktree、**未提交 git** ✓；未改 `spec/`/契约（git status 无）✓；术语无「银行」✓；组件源 `base..HEAD == 1` 且工作树 clean ✓；任务书「验证」节未被改动（diff 仅 状态+完成区+审阅记录，无凑绿）✓；断言均有可达 FAIL（我注入实证 7 条红）✓。

**finding（非阻断，交 architect）**：F-a 任务书「背景/验证 1」的 D21 因果原文已被实测证伪，engineer 换成「分类统计归零 + 另加 fs.py 去 `--caches`」两条可达判据（更强、非弱化），但任务书原文未同步，建议收尾时按实测订正措辞；F-b `run.sh` 的 `inject shim: mapping probe goes red` PASS 行 rc 字段显示 1（探针预期值），纯显示问题，不影响判定。

**判决：Accepted** —— 我的重跑 28/28、43/43 均 rc=0；独立注入红→`cp`+md5 还原→回绿；D21 订正经源码与实测双证成立；约束无违反。采信项：逐例跨平台比较由 `run_inst_tiny`/`run_m5_e2e` 自身 harness 判定（我核了 38/38、10/10、0 FAIL 行）。

