# m16-chipyard-009: Kaiwu-Vast 的 D-Cache（8 路 × 128 组，64 KiB）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-008`（I/D TLB）、`m16-chipyard-007`（PTW 两级步查）
**可并行分片**：否（改 `dadao-wuming` 核）
**预估**：2–3 天
**档位**：大改
**状态**：已验证

## 用户已定口径（2026-11-20，不得自决）

- **I/D 各 128 组**（8 路 × 128 组 × 64 B = **每侧 64 KiB**，合计 128 KiB）；
- **设计参照 TLB**：参数化类 + 每核一个实例（I/D 各一），Tiny 不实例化；
- **暂不做 stack cache / PTE cache**（前者等 VA 区间与一致性规则，后者另议）。

## 参数与硬约束

- **line 64 B**（8 个 64 位 beat）、**8 路**、**128 组**；
- **索引位必须在 64 KiB 页内**：line offset 6 位 + 组索引 7 位 = 13 位 < 16 位 ⇒ **VIPT 无别名**（每路 8 KiB）；
- **D-Cache：写回 + 写分配**，每行一个 dirty 位；
- **PTW 的页表读走 D-Cache 端口**（与 BOOM/rocket 同构，`m16-chipyard-008` 已有 PTW）；
- 阻塞式（单未决缺失）作为首版；非阻塞另立任务；
- 资源：每侧 **16 块 RAMB36**（64 位宽折算 4 KiB/块），合计 32 块。

## 目标

1. `WumingCache.scala`：参数化类（`sets`/`ways`/`lineBytes`/`writeBack`/`withDirty`），**参照 `WumingTlb.scala` 的写法**（`m16-chipyard-008`）；
2. 在核内实例化 D-Cache（`withDirty=true`），接 PTW 的 PTE 读端口；
3. **命中/缺失**：命中不访存；缺失按 8 beat 填充；
4. **写回**：脏行在淘汰或 clean 时写回；写命中只改 cache；
5. **clean/flush 操作**（内部接口先行，`cfx5` 接线另立任务）：按 PA 单行 clean/invalidate、全表 flush；
6. **Tiny 零增益**：Tiny 不实例化（FIRRTL 里 0 命中）。

## 验收（逐条贴真实 rc）

1. **命中/缺失**：同址重复访问 1 miss + N hit；探针记录（`WumingDcache` 计数）；
2. **8 路**：同组 8 行共存、第 9 行按 LRU 淘汰（给替换序列）；
3. **写回**：写后读命中不回内存；淘汰后才见写回（记录内存值变化时机）；
4. **PTW 端口**：PTE 读经 D-Cache；核内改 PTE（经 D-Cache 写）后 PTW 立即读到新值；
5. **Tiny 零增益**：Tiny 的 FIRRTL/SV 里 `WumingDcache` = 0；首册 38 镜像不回归；
6. **可达 FAIL ≥3 路**：① 把 8 路改成全相联 ⇒ 替换序列红；② 去掉 dirty 位（写穿）⇒ 写回时机红；③ 索引改用 PA 或改 6 位 ⇒ 同组/容量断言红（`cp`+md5 还原 + 强制重建）；
7. `check-patch-tree` chipyard 段 0 问题；`check-component-changelog` rc=0。

## 约束

独立 `git worktree`；不提交 git；只动 `dadao-wuming` 与组件补丁树；不改 `spec/`/契约/`manifests/`；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：证据脚本（运行期证据目录内的 `run.sh`）最终一轮 **PASS=35 FAIL=0**（`FINAL_EXIT=0`）：A 8/8、B 11/11、C 1/1（判据自检 11 case / 0 surprise）、D 11/11（35 条记录 + 事件 + `vastwalk` 31 记录）、E 4/4；另 `--inject` **PASS=5 FAIL=0**（三路注入全红、还原 md5 相等）、`--rebuild` **PASS=7 FAIL=0**（还原后重建回绿）。

**验收结果**（逐条，均由证据脚本现场统计）：
1. **命中/缺失**：A 行（PA 0x4_1000）日志 `fill-done`=1、`hit`=4，5 条记录全 = `M_A`（同址 1 miss + 4 hit）。
2. **8 路**：B0..B7 同组（事件 `idx=64`）8 条共存；L9 填表淘汰 `victimLine=0x4_5000`（B1），B7 再 touch 后 L10 填表淘汰 `victimLine=0x4_7000`（B2）；B1 再读即重填（`miss`+`fill-done`）且数据仍 = `M_B1`。
3. **写回**：代码页存 `trap cfx_hmon` 后读回 = 指令字（`hit ... write=1`），此时 **取指端口（无 I-Cache）仍读内存旧值 0**（UNDI，hmon 后按期望 cause 返回）；同组再填 8 行后出现唯一一次 `wb line=0x8_1000`，其后取指读到 `trap`（CFXTRAP）、再读该行 = 指令字。写回发生在「写后读命中」之后、重填之前。
4. **PTW 端口**：读 VA_PAGE ⇒ `M_PAGE_OLD`；经自映射页把 L2[7] 的 PTE **经缓存写**成新目标后 `invalid/all` 重走查 ⇒ `M_PAGE_NEW`；日志有 `req=1` 的 `hit line=0x1_0000`（走查读到缓存行），核内再读同一 PTE = 新值。
5. **Tiny 零增益**：Tiny FIRRTL 中 `WumingDcache` = 0（Vast 里 >0 且 `io.cmd.bits.addr` 端口存在）；首册 `01-load-store` **38/38** 在改前/改后 Tiny 二进制上都通过、结果目录逐字节相同。
6. **可达 FAIL（3 路，`cp`+md5 还原 + 强制重建）**：① 替换策略改成 MRU（`victim` 取 age 最小）⇒ 受害者序列判据红；② `writeBack = false`（写穿）⇒ 淘汰前第二次取指就执行 `trap`（CFXTRAP 而非期望 UNDI），探针非零退出；③ 组索引改 6 位（`PA[11:6]`）⇒ 同组断言（数据行 `idx=64`）与替换序列红。
7. **门控/合并态**：`check-patch-tree` chipyard 段 **26 补丁 0 问题**（rc=0）、`check-index-blobs` rc=0、`check-component-changelog` rc=0、`git merge-tree --write-tree master HEAD` 无冲突；改动集恰为 11 个允许文件、不触碰 `spec/`/契约/`manifests/`/`Makefile`；chipyard 源树 clean+base+1。

**修改文件**：任务书；`components/chipyard/{README.md,changelog.md,series}`；补丁 `components/chipyard/patches/.../WumingCore.scala.patch`、`WumingPtw.scala.patch`（重导）与新增 `WumingDcache.scala.patch`；新增 `tools/chipyard/dcache/{vastdcache.S,vastdcache.lds,gen_vastdcache_tables.py,check_vastdcache.py}`。

**新发现/坑**：① **填充的最后一拍**不能只写寄存器再在同拍引用（`fillBuf` 是 Reg）——必须在同一拍用 wire 并入，否则 beat 7 永远保留旧内容；实测表现为 L2 表第 7 项读成 0 ⇒ 走查 `DGPTRAP`。② **淘汰回写地址是受害者行**，不是新请求的行；用 `reqLineBase` 会把脏行写到刚发起缺失的行（探针第 8 条 fresh 读到指令字）。③ 合并最后一拍时直接用 `finalBuf(reqBeat)` 会形成组合环（动态写口自读）⇒ firtool `detected combinational cycle`；改用 `fillBuf`/`lastBeat` 的 Mux 作旧值。④ Vast 的核内直连访问（SRAM/hmon/BootROM）与翻译后访问共用数据端口时，**响应选择必须按路由**（`memCacheRoute`）；只看缓存响应会让直连访问永远等不到 D。⑤ **PA RAM 上电不是 0**（TLRAM 随机）：探针的「旧值 0」必须由 PT_LOAD 显式装入（否则第一次跳转就执行随机字）。⑥ 宏层 `TEST_PAD = ENTRY+0x4000`，`.faultpad` 必须放在同一地址（不是 `ENTRY+0x4000-0x100`），否则 `__pad` 落在零区、第二次异常把探针打死。⑦ 普通页 PTE 的页基址是 `PTE[55:16]`（64 KiB 对齐）：目标 PA 必须 64 KiB 对齐，否则被掩掉低位、指向错误页。⑧ 判据正则要容忍 Chisel `printf` 十进制字段的前导空格（`idx= 64`）；十六进制 48 位字段是 12 位、64 位寄存器是 16 位。

**遗留问题**：① clean/invalidate/flush 只有**内部端口 + FSM**，未由 `cfx5` 接线（任务范围明确另立任务）⇒ 无软件触发的运行期证据，只有端口存在性（Vast FIRRTL `io.cmd.bits.addr`）与代码级审查；② 写回失败（bus denied）路径保留脏行并返回错误，未构造总线失败用例（TLRAM 全可写；`ADWBFAIL` 由 007/008 的注入覆盖）；③ 既有 `vasttlb` 探针用当前工具链无法重编（`LOAD_ADDR` 未识别，**非本任务引入**），故 008 探针未重跑，同构建以 `vastwalk`（007，31 记录）作 Vast 回归；④ 非阻塞/多未决缺失、stack/PTE cache 不在本任务；⑤ Tiny FIRRTL 正文有 1406 行命名节点差异（无逻辑变化；38 镜像结果逐字节证明）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`WumingDcache.scala`（查找/命中/填充/淘汰回写/写穿/命令 FSM/TL 通道）、`WumingCore.scala`（缓存实例化、双端口路由、响应选择、PTW 接线）、`WumingPtw.scala`（TL → 缓存端口的替换）、探针/生成器/判据、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 填充最后一拍未并入行（beat 7 保留旧值） | ✅已修 | `finalBuf` wire 同拍并入 `lastBeat` | 修后 VA_PAGE 走查不再 `DGPTRAP`、35 记录全对 |
| F2 淘汰回写地址用了新请求行 | ✅已修 | 新增 `wbBase`（受害者行），`linePut`/日志用它 | `wb line=0x8_1000`，第 8 条 fresh 读回 `M_F8` |
| F3 合并最后一拍形成组合环 | ✅已修 | 旧值取 `Mux(reqBeat===fillCount, lastBeat, fillBuf(reqBeat))` | firtool 无 `combinational cycle`、Vast 构建 rc=0 |
| F4 Tiny 直连访问等不到响应（按缓存响应判 fire） | ✅已修 | `dataRespFire/Error/Beat` 按 `memCacheRoute` 选择 | 启动/首册 38/38 通过 |
| F5 探针 PA RAM 上电随机、代码页未初始化 | ✅已修 | 新增 `.code_old` PT_LOAD（0x8_1000 = 0） | 第一次跳转得到 UNDI |
| F6 `.faultpad` 放错 0x100 | ✅已修 | 移到 `ENTRY+0x4000` | `__pad` 命中、三次期望故障都按 cause 返回 |
| F7 PTE 目标 PA 非 64 KiB 对齐（0x7_8000/0x7_C000） | ✅已修 | 改为 0x7_0000 / 0x9_0000 | r32/r33 = `M_PAGE_OLD`/`M_PAGE_NEW` |
| F8 判据正则不认 `idx= 64` 的前导空格 | ✅已修 | `KV` 允许 `\s*` | 35 记录 + 事件判据 rc=0 |
| F9 证据脚本在运行中被编辑导致汇总行损坏 | ✅已修 | 最终脚本定稿后再跑；不再边跑边改 | 最终 A–E/F/R 分段跑完 |

判决：全部 finding 已修，无未修项；任务状态置「待验收」。

### 第 1 轮 reviewer 验收（2026-11-21；档位 60 min，实际超时——9 次强制 Verilator 重建，系派单估时不足，非交付物缺陷）

**重跑记录（reviewer 亲自执行，真实输出/退出码；证据脚本 = 运行期证据目录内的 `run.sh`）**

1. `run.sh` ⇒ **PASS=35 FAIL=0，rc=0**（39 min）。A 8/8：26 补丁、`check-patch-tree` chipyard 行问题 0/0（rc=0）、`check-index-blobs` rc=0、`check-component-changelog` rc=0、`git merge-tree --write-tree master HEAD` rc=0、改动集 diff 为空、不触 `spec/`·契约·`manifests/`·`Makefile`、chipyard 源树 0 脏；B 11/11：Vast+Tiny 强制重建 rc=0 且 `.fir`/模型目录/`chipyard.jar` 均删、`Nothing to be done`=0、`%Error`=0、Tiny `WumingDcache`=0、Vast=10218、`io.cmd.bits.addr`=3、Tiny 正文 diff 1406 行；C 1/1：自检 11 case/0 surprise；D 11/11：探针 rc=0、10 段 `p_vaddr==p_paddr`、22/22 覆盖、35 记录、victim `0x45000→0x47000`、`wb line=0x8_1000`=1、A 填充 1/命中 4、PTW `req=1` 命中 6、`vastwalk` 31 记录 rc=0；E 4/4：before/after 各 rc=0、镜像数 38/38、结果目录逐字节 same。
2. `run.sh --inject` ⇒ **PASS=5 FAIL=0，rc=0**：① 改 MRU ⇒ 判据 rc=1（`L9 victim 0x43000 != B1 0x45000`、`L10 victim 0x51000 != B2 0x47000`）；② `writeBack=false` ⇒ 探针 rc=33（`SYS_EXIT code=0x21 → host exit status 33`）；③ 组索引 6 位 ⇒ 判据 rc=1（`falls outside group 64: [0]`、`L9 victim 0x24000`）；还原 md5 `0770955d…`/`9401a0ea…` = pristine。
3. reviewer 独立注入 2 路（`cp`+md5 备份 → 改被测产物 → 强制重建 → 证据脚本同款探针与判据 → `cp` 还原对账；不用脚本自带注入充数）：
   - **I-A 淘汰回写地址改用新请求行**（`wbBase := Cat(victim.tag,…)` → `wbBase := reqLineBase`）：`PRE 0770955d → INJ 5e02aee3`，`ELAB_RC=0 SIM_RC=0`（30.6 min），**探针 rc=26 / 判据 rc=1**，红项 `code line write-backs 0 != 1`；日志 `miss line=0x6_5000 … victimLine=0x8_1000 dirty=1` → `wb line=0x6_5000`（回写落到新请求行）；`POST_MD5=0770955d == PRE`、chipyard 树 0 脏。
   - **I-B PTW 不读缓存副本**（`when(anyHit)` → `when(anyHit && !reqPtw)`）：`PRE 0770955d → INJ b7be4434`，`ELAB_RC=0 SIM_RC=0`（30.7 min），**探针 rc=28 / 判据 rc=1**，红项 `no PTW read hit on the PTE line`、`the rewritten PTE never reached the new target`；日志 PTW 恒 `miss … req=1`；`POST_MD5=0770955d == PRE`、chipyard 树 0 脏。
4. `run.sh --rebuild` ⇒ **PASS=7 FAIL=0，rc=0**：pristine md5 ×2、源树 0 脏、强制重建 rc=0 且真的发生、探针 rc=0、判据 rc=0 ⇒ 脚本三路与 reviewer 两路注入全部回绿。

**参数逐条**：`WumingDcacheParams(sets=128, ways=8, lineBytes=64, writeBack=true, withDirty=true)`；`indexOf = a(indexBits+offsetBits-1, offsetBits)` = **PA[12:6]**、`offsetBits`=6、`require(indexBits+offsetBits<16)`（7+6=13<16 ⇒ VIPT 无别名）；`beats=8`、每路 128×64 B = 8 KiB × 8 路 = 64 KiB，数据阵列每路一个 `SyncReadMem(128, Vec(8, 64b))` ⇒ 2 RAMB36/路 ⇒ 16/侧（与任务书资源口径一致）；FIRRTL 中 cmd 路径索引实测 `bits(...,12,6)`。

**Tiny 零增益**：Vast `WumingDcache`=10218（`io.cmd.bits.addr` 3 处全在 `WumingDcache`/`WumingCore.dcache`，PTW 的 `WumingPtwCommand` 无 `addr` 字段）；Tiny=0；改前 Tiny 二进制 md5 `25c1d3f4…`（=015 收尾 MEMORY 基线）vs 改后 `331de34e…`（非同源自比）；首册 before/after 各 38 PASS/0 FAIL、`diff -r` rc=0、各 114 文件、聚合 md5 相同。

**语义抽查**：① 淘汰回写地址 = 受害者行（`wbBase` 取 `victim` tag），运行级 `wb line=0x8_1000`=1，I-A 注入证可达 FAIL；② 填充末拍同拍并入（`finalBuf(fillCount):=lastBeat` + `oldBeat` Mux），覆盖点 = L2 表第 7 项（beat 7）→ r32 `M_PAGE_OLD`；③ 写后读命中不碰总线（`writeBack` 分支只写行+置 dirty），独立观测量 = 取指端口（r19/r21 UNDI、r30 CFXTRAP，非自比）；④ PTW 读到经缓存写入的新 PTE（`io.mem <> dcache.io.ptw` 单一阵列，r33/r34）；⑤ 直连窗口按 `memCacheRoute` 选 `dataRespFire/Error/Beat`，全部消费点已换。

**约束核验**：独立 worktree、未提交 git、改动集恰 11 个允许文件、不触 `spec/`/契约/`manifests/`/`Makefile`、无「银行」、任务书无具体 `.work/**` 运行期路径；`vasttlb`（008）无法重编的披露属实（实测 `llvm-mc` 报 `LOAD_ADDR` unrecognized，该宏全仓无定义，非本任务引入）。

**文档级 finding（非阻断，交 architect 收尾一并修或另立小任务）**：① `tools/chipyard/dcache/vastdcache.lds` 头注释引用判据脚本**不存在**的 `--check-layout`（实际互校由证据脚本的段覆盖检查 + 生成器 `--check-geometry` + 链接器 `ASSERT` 承担），且仍写旧地址 `0x7_8000`/`0x7_C000` 与「代码页…无需装入」——现值为 `0x7_0000`/`0x9_0000` 且 `.code_old` 显式装入 0；修法：按生成器常量改注释并删去 `--check-layout` 字样。② `check_vastdcache.py` 自检日志路径写死在任务目录之外的固定临时目录（自检段 `log = pathlib.Path(...)`）；修法：改到本任务的 `/tmp/opencode/<任务ID>/` 或 `tempfile.mkdtemp()`。

**判决：Accepted** —— 任务验收 1–7 全部在 reviewer 自己的重跑下通过，5 路可达 FAIL 全红且红在目标语义上，参数/零增益/门控/改动集逐条对上，无阻断项。
