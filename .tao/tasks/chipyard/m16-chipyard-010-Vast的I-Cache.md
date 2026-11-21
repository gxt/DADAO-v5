# m16-chipyard-010: Kaiwu-Vast 的 I-Cache（8 路 × 128 组，64 KiB，无 dirty）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-009`（D-Cache，复用 `WumingCache` 参数化类）
**可并行分片**：否（改 `dadao-wuming` 核）
**预估**：1–2 天
**档位**：中改
**状态**：已验证

## 用户已定口径（2026-11-20）

- **I/D 各 128 组**（8 路 × 128 组 × 64 B = 每侧 **64 KiB**）；
- **设计参照 TLB**：与 D-Cache 共用 `WumingCache` 类，I 侧 `withDirty=false`（**I 表无 dirty 位**，与 `m16-chipyard-008` 的 I-TLB 无 D 位同构）；
- **暂不做 stack/PTE cache**。

## 目标

1. 在核内实例化 I-Cache（`withDirty=false`、只读）；
2. 取指命中不访存；缺失按 8 beat 填充；
3. 与 D-Cache **共用同一个类**（不得复制第二份实现）；
4. **Tiny 零增益**：Tiny 不实例化。

## 验收（逐条贴真实 rc）

1. **命中/缺失**：顺序取指 1 miss + 同 line 后续 hit；探针记录；
2. **8 路 × 128 组**：同组 8 行共存、第 9 行按 LRU；
3. **无 dirty**：I 侧无写回路径（结构断言：dirty 寄存器数 = 0）；
4. **与 D 共用类**：`WumingCache` 只有一份实现（grep 计数现场派生）；
5. **Tiny 零增益**：Tiny 的 FIRRTL/SV 里 `WumingIcache` = 0；38 镜像不回归；
6. **可达 FAIL ≥2 路**：① 把 I 侧改成带 dirty ⇒ 结构断言红；② 索引位改 6 ⇒ 组冲突断言红；
7. `check-patch-tree` chipyard 段 0 问题。

## 约束

独立 `git worktree`；不提交 git；不改 `spec/`/契约；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：证据脚本（运行期证据目录内的 `run.sh`）默认运行 **PASS=48 FAIL=0**（A 13 / B 8 / C 6 / D 5 / D3 3 / E 5 / R 8；本次运行期已有 pristine 基线，故还原段一并跑了）；`--inject` **PASS=11 FAIL=0**（两路注入全红、还原 md5 = pristine）；`--rebuild` **PASS=8 FAIL=0**。
**验收结果**：① 命中/缺失：10 段各 64 B 的代码块共 12 次访问 × 8 beat = 96 次取指 = **11 次填充 + 85 次命中**；A1 首访 1 fill + 7 hit，命中拍 `fetchresp latency=1`、缺失拍 41（核自己的计数器，独立于缓存日志）。② 8 路 × 128 组：A1..A8 均 `idx=64` 且缺失 `invalid=1`（共存、无淘汰），A9 `victimLine=0x21000`(A1)、A1 重填 `0x31000`(A2)（LRU）；C1（PA[12:6]=0）`idx=0`/`invalid=1` 不淘汰 A 组，其后 A3 仍命中（15 hit / 1 fill）；FIRRTL 两实例都是 8 个 `UInt<64>[8] [128]` 阵列。③ 无 dirty：I 模块 **0** 处 `dirty`、**0** 条 `wb` 打印（`dcache` 两者都有，对照）；运行期 I 实例 0 条 `write=1`、0 `wb`/`wt-fail`。④ 共用类：`class WumingCache(` 现场 grep **1** 处、旧名残留 **0**、`WumingCore` 两处实例化参数不同（D：`writeBack=true, withDirty=true`；I：`writeBack=false, withDirty=false, readOnly=true`）。⑤ Tiny：FIRRTL `WumingCache`=**0**；首册 **38/38** 改前/改后逐字节相同。⑥ 可达 FAIL：I 侧 `sets=64`（索引 PA[11:6]）⇒ 判据 rc=1（A3 被 C1 挤掉：`fills 2 != 1`、组索引红）；I 侧带 dirty+写回 ⇒ 结构 rc=1（I 模块 4236 处 `dirty`、2 条 `wb`）；两路 `cp`+md5 还原并强制重建后回绿。⑦ 门控：`check-patch-tree` chipyard 段 26 补丁 0 问题（rc=0）、`check-index-blobs`/`check-component-changelog`/`merge-tree` rc=0；改动集 15 个文件 + 1 个改名删除，不触 `spec/`/契约/`manifests/`/`Makefile`。
**修改文件**：任务书；`components/chipyard/{README.md,changelog.md,series}`；补丁改名 `.../WumingCache.scala.patch` 与重导出的 `WumingCore.scala.patch`、`WumingPtw.scala.patch`；`tools/chipyard/dcache/{check_vastdcache.py,gen_vastdcache_tables.py,vastdcache.S,vastdcache.lds}`（类名同步 + 取指行 I-Cache 淘汰步）；新增 `tools/chipyard/icache/{vasticache.S,vasticache.lds,gen_vasticache_tables.py,check_vasticache.py}`。
**新发现/坑**：① 009 的 D 探针把「取指端口」当内存的独立观测量（当时无 I-Cache）；010 后取指行会被 I-Cache 命中，写回落地后必须先按 LRU 把那条取指行挤出（8 条同组一行块）才看得到内存里的 `trap`，否则第三次跳转仍执行缓存旧 0（UNDI，退出码 33）。② dirty 是 tag bundle 的字段（`{valid,dirty,tag}`）而不是独立寄存器，结构判据要按模块体内 `dirty` 出现次数（I=0 / D>0），不能按「寄存器名含 dirty」grep。③ 生成器按「VA 页号 = 数组下标」写 L2 表，一个 off-by-one 会让 8 个淘汰块只填 7 条（代码行不淘汰）⇒ 已加 `L2[page] == pte(page<<16)` 现场断言。④ Chisel `printf` 的十进制字段有前导空格（`latency=  41`），判据正则须 `\s*`；十六进制按位宽补零（48 位 = 12 位）。⑤ 组索引注入只能改 I 侧参数（`sets=64`），改共享类的 `indexOf` 会连 D 侧一起坏，红因就不在目标语义上。
**遗留问题**：① I 侧 `cmd`（clean/invalidate/flush）端口接空（`cfx5` 接线另立任务，与 D 侧同）；② Vast 仍不发射投机预取（故同时只有一个请求在飞），预取 × I-Cache 的交互另立任务；③ 无 I/D 一致性（未做自修改代码用例，与 009 口径一致）；④ D 探针新增 8 条淘汰块属本任务适配（35 条记录不变）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`WumingCache.scala`（参数/`readOnly` 展开裁剪/条件生成 dirty 与写回/LRU/填充/A 通道）、`WumingCore.scala`（两处实例化、取指端口路由与响应视图、`fetchRouteReg` 锁存）、`WumingPtw.scala`（端口类型改名）、探针/生成器/判据、证据脚本、D 探针适配。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `WumingCore` 残留 `WumingDcacheCmd`，elab 编译失败 | ✅已修 | 改名 `WumingCacheCmd` | Vast/Tiny elab rc=0 |
| F2 判据首版把「无效受害者 victimLine」当 0、二次访问命中数按 7 算、latency 正则不容空格 ⇒ 真探针 9 条假红 | ✅已修 | `victimLine=idx<<6`、命中期数按「驻留访问 8 拍」、`latency=\s*` | `--self-test` 14/14、真探针 rc=0 |
| F3 结构判据按「寄存器名含 dirty」grep，真实 FIRRTL 是 bundle 字段 ⇒ D 侧对照假红 | ✅已修 | 按模块体 `dirty` 计数 + `smem ... [8] [128]` 形状 | `--structure` rc=0、`--structure-test` 2/2 |
| F4 D 探针在 I-Cache 存在后失效（第三次跳转命中缓存旧行 ⇒ rc=33） | ✅已修 | D 探针加 8 条同组一行淘汰块（`IC_EVICT`）+ L2/lds/生成器常量 | D 判据 35 记录 rc=0 |
| F5 淘汰块 L2 表 off-by-one（`PTE_EV2` 放在 L2[9]）⇒ 8 块只填 7 条 | ✅已修 | 表项对齐页号 + 生成器 `L2[page]==pte(page<<16)` 断言 | 生成器 `--check-geometry` rc=0、I-Cache 日志 8 次 fill |
| F6 注入② 的 `structure.log` 目录不存在 ⇒ 重定向失败被当成「rc=1 通过」（假绿） | ✅已修 | `mkdir -p` + 「红项数 > 0」断言；并在注入产物上手工复核 | 注入② 真 RTL：4236 处 dirty / 2 条 wb |
| F7 `run.sh` 默认也跑 R 段（pristine md5 不存在）⇒ 2 条假红 | ✅已修 | R 段加 `-f pristine md5` 前置 | `--rebuild` 独立跑 PASS=8 |
| F8 「I 侧实例参数」grep 命中注释里的 `readOnly = true`（2 vs 1） | ✅已修 | 收紧为整行参数模式 | A 段 13/13 |
| F9 改动集判据漏算「改名删除」的旧补丁路径 | ✅已修 | 期望集补 1 项并写清「15 文件 + 1 改名删除」 | A 段改动集 PASS |

判决：全部 finding 已修，无未修项；任务状态置「待验收」。

### 第 1 轮 reviewer 验收（2026-11-21）

**重跑记录**（本人终端实测，命令在仓库根执行，证据取自运行期证据目录内的 `run.sh`）：
1. `ONLY=A,C,D,E bash 运行期证据目录内的 run.sh` ⇒ **PASS=32 FAIL=0 rc=0**（A13 / C6 / D5 / D3 3 / E5）。
2. `bash 运行期证据目录内的 run.sh --rebuild` ⇒ **PASS=8 FAIL=0 rc=0**（Vast 强制重建、探针、结构、源树干净；elab 日志 `%Error`=0、无 `Nothing to be done`）。
3. 门控：`check-patch-tree` = `chipyard: 26 patch(es)` + 447 patches OK、chipyard 断言行 0、rc=0；`check-index-blobs` rc=0；`check-component-changelog` rc=0（10 文件 × 4 断言）；`git merge-tree --write-tree master HEAD` rc=0（见 f1）。
4. 现场 grep：`class WumingCache(`=1、`WumingDcache` 残留=0、`Module(new WumingCache(`=2、D 参数（writeBack+withDirty）=1、I 参数（readOnly/无 dirty/无写回）=1；补丁内 `indexOf = a(indexBits+offsetBits-1, offsetBits)` ⇒ PA[12:6]、`require(indexBits+offsetBits<16)`、I 侧未覆盖 sets/ways/lineBytes（=128/8/64 默认）。
5. 本人独立解析 Vast FIRRTL：icache 模块 `dirty`=0、wb printf=0、8 个 `[8][128]` 阵列；dcache `dirty`=4236、wb printf=2；两实例不同模块；**Tiny** FIRRTL `WumingCache`=0、`inst icache`=0。
6. I 功能（本人重跑探针）：12 条记录全对；**11 fill / 85 hit / 11 miss**；A9 `victimLine=0x21000`、A1 重填 `0x31000`（LRU）；C1 `idx=0 invalid=1` 不淘汰 A 组；I 事件 `write=1`=0、`wb`=0；`fetchresp latency` 85×`1` / 11×`41`。
7. D 侧适配：`check_vastdcache` **35 记录 rc=0**；记录宏数与 master 相同（30 `__CHECK_RD` + 7 `__REC`），check 文件除日志标签改名与自检日志改临时文件外**无断言删除** ⇒ 判为必要的 010 适配，非放宽判据。
8. E：before/after 各 **38/38 PASS**、`diff -r` rc=0；两 Tiny 二进制 md5 不同（改前 82ffcf14… / 改后 92bf11ae…），非同源自比。
9. 自检（本人跑）：`check_vasticache --self-test` 14 case / 0 surprise、`--structure-test` rc=0、`check_vastdcache --self-test` 11 case / 0 surprise、两处 `--check-geometry` rc=0。
10. **独立注入 1 路**（cp+md5 备份 → I 侧改 `writeBack/withDirty=true` → 强制重生成 FIRRTL → `--structure` **rc=1 红 2 条**（dirty 4236、wb 2 printf）→ `cp` 还原 md5=pristine → 重生成 FIRRTL md5 与注入前**逐字节相同** → `--structure` **rc=0 回绿**）；还原后 chipyard 源树 `git status` 0 行。
11. 快照对账：工作区 16 项改动与审查前快照**逐行一致**；证据脚本 md5 47da1dc9… 未变；审查期间未提交 git、未用 `checkout/restore/stash` 还原。

**未独立重跑（如实披露）**：B 段 Tiny 强制重建 3 项 + idx6 注入（验收⑥②）——需 2–3 次 Verilator 全量重建，超出 60 min 档位，按优先级截断。依据（已抽读核对）：工程师 `rebuild-*.meta` 均 `fir=1 model=1 jar=1`、各 elab/sim 日志 `%Error`=0 且无 `Nothing to be done`、idx6 注入 `check.log` 38 条 FAIL 原文；B 的 Vast 半边由第 2 条强制重建覆盖，Tiny FIRRTL 判据由本人 grep 覆盖。

**findings（均不阻断，交 architect 收尾）**：
- f1 `merge-tree` 判据在本状态恒真：分支无提交（HEAD==merge-base），比的是 master 与 base 树；本人另算改动集 ∩ `HEAD..master` 文件交集 = **0**，实际合入无冲突风险。
- f2 `run.sh` B 段 Tiny FIRRTL 计数在文件缺失时被默认值兜成 0（缺文件假绿）；E 段 before/after 缺失会静默跳过（本轮均未触发，38/38 实测在跑）。
- f3 判据自检把日志写到任务 ID 之外的共享临时目录（icache 侧固定名、dcache 侧 mkdtemp），且自检后不清理。
- f4 任务书 `**档位**：中改` 与派单档位（组件 + 大改 / 60 min）不一致。
- f5 changelog 历史条目仍用「银行」（非本任务改动行，属遗留）。
- f6 环境披露：本 worktree 无独立 conda 环境，证据脚本默认退回共享工作区的同一份环境（仅经 PATH/RISCV/LD_LIBRARY_PATH 只读引用）；风险是并行会话改动该共享环境会波及本轮工具链身份——本轮未观测到（探针汇编走仓库内 cross-toolchain，首册运行记录了 llvm-mc/ld.lld/qemu 的 md5），判据不依赖该环境的可变内容。

**判决：Accepted** —— 验收 ①–⑦ 在本人重跑下全部通过（未独立重跑项已披露），硬约束无违反；写入本记录后 `make check-knowledge-refs` **rc=0**。

