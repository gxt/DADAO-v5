# m16-gem5-013: gem5 侧 `escape` 新语义对齐（`prev_cfx_code`）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m14-spec-009`（spec + QEMU 已实现）；`spec/Kaiwu` 已同笔对齐（`ede7f6b3`）
**可并行分片**：可与 `m16-chipyard-005` 并行（不同组件）
**预估**：3–4 h
**档位**：中改（单组件）
**状态**：已验证

## 背景（用户 2026-11-18 裁定）

`m14-spec-009` 按用户裁定 B 把 `escape` 改成**恢复 `inner_cfx_code ← excp_prev_cfx_code`**（`cg5 rc1`，异常进入时保存），spec 与 QEMU 已落地，`m15-testcases-017` 的 11-cfx 载体也已按新语义重写（272/272）。

但三方里还有两边没跟上：

- **gem5**：`components/gem5/patches/src/arch/dadao/node_cfx.hh` 只有 `prevRunMode`，**没有 `prevCfxCode`**；`node_cfx.cc` 的 trap/escape 路径也只保存/恢复运行模式。
- **chipyard**：见独立任务 `m16-chipyard-005`（RTL 核实/补），本任务**不碰** `components/chipyard`。

## 目标

### 1. gem5（`components/gem5/patches/src/arch/dadao/**`）

- `node_cfx.hh`：加 `uint64_t prevCfxCode = 0;`（注释 `cg5 rc1`）。
- `node_cfx.cc`：trap 进入时**在改写 `cfxCode` 之前**保存 `prevCfxCode = cfxCode`；`escape` 通过步骤 0 检查后恢复 `cfxCode = prevCfxCode`。
- cg5 rc1 的读写分发：从 reserved 改为可读写 `prevCfxCode`（与 QEMU `helper.c` 的 `case 1` 对齐）。
- 若 `tiny_cfx` 也有同类路径，一并核。

### 2. 一致性验证（gem5 侧，必须能失败）

- 构造「supv 帧内投递异步事件 ⇒ 该帧 escape 成功、`cfxCode` 回到进入前值」；
- **删掉恢复那行 ⇒ 必须复现 `CFXESC`** ⇒ 还原 ⇒ 恢复；
- 与 QEMU 的 cg5 rc1 值（复位 `cfx_power`=63、boot trap 后 0x3F）逐项对齐。

## 验收（逐条贴真实 rc）

1. gem5 补丁经 `make_patch gem5` 重导出；`--source-state gem5` = `base+1 clean`；`make check-patch-tree` 的 gem5 段 0 problem。
2. gem5 行为注入：删恢复行 ⇒ `CFXESC`；还原 ⇒ 绿（贴两侧 rc）。
3. `make check-wuming-cycles`、gem5 段 `check_component` rc=0。
4. **两方对照**：QEMU / gem5 对同一场景的 `inner_cfx_code` 与 `cg5 rc1` 值一致（chipyard 由 `m16-chipyard-005` 单独验收，其结论出来后由主会话补三方对照）。
6. `make check-inst-asm` 272/272（确认测试载体与新语义一致）。
7. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. **不改 spec**（已由 `ede7f6b3` 对齐）；不改 `tests/inst`（`m15-testcases-017` 已改）。
3. **不碰 `components/chipyard`**（由 `m16-chipyard-005` 负责）。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。
5. 严格串行：先构建、再跑门控。

## 待裁定

（执行中如有 → 写入本节并返回）

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-19，自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `prevCfxCode` 若在 step 6 之后采样会存成目标 cfx（恢复无意义） | ✅已修 | `node_cfx.cc` step 5：置于 `prevRunMode` 之后、`s.cfxCode = target` 之前（`§5.2` step 5/6） | G.save 反例：删该行 ⇒ `boot_prev_code` 0x3F→0、guest rc 0x61 |
| `escape` 只恢复 `runMode` 时，帧内收到异步事件的帧退不出去（`CFXESC`） | ✅已修 | `node_cfx.cc` step 2 加 `s.cfxCode = prevCfxCode & 0x3F` | G.restore 反例：删该行 ⇒ `async_in_frame` guest rc 0x7E；`cp`+md5 还原后 0x00 |
| `cg5 rc1` 仍 `reserved`（`cfxRegPtr` 无 `case 1`）⇒ 读即 `CFXREG` | ✅已修 | `cfxRegPtr` 与 Tiny `regPtr` 各加 `case 1: return &r.prevCfxCode;` | `boot_prev_code` 0x3F、`prev_code_rw` 写 0x25 读回 0x25 |
| Tiny 同路径（`tinyEnter`/`tinyEscape`/`regPtr`）未同步 | ✅已修 | `tiny_cfx.{hh,cc}` 三处 | G.tiny 反例：删 Tiny 恢复行 ⇒ 载体 gem5 lane rc=9 且字节流不一致；还原后 same |
| 探针在 supv 帧内读 `cg5` 被 `cg3 rc12 cg_reg_deleg`（重置 ~0）拦成 `CFXPERM` ⇒ 落 poison 向量 | ✅已修（探针侧） | 探针 setup 清 cfx_smon / cfx_hart 的 hypv `cgRegDeleg` | 修前 0x7C/0x7D；修后 A 组 6/6 |
| 探针 `async_in_frame` 检查 `RAM_CID15`，但 hart handler 未写该槽 | ✅已修（探针侧） | handler 里补存 cause_id | 修前 0x72；修后 0x00 |
| 证据脚本 E1 的 grep 前缀写错（`^gem5:` vs `^check-patch-tree --source-state: gem5:`） | ✅已修（脚本侧） | `run.sh` group_E | 第一轮 23/24 → 24/24 |
| 证据脚本 tiny 反例的比较方向写反（拿「绿」当期望值） | ✅已修（脚本侧） | `run.sh` G.tiny 分支 | `--inject tiny` 7/7 PASS |
| 软件可写 `cg5 rc1` ⇒ `escape` 可把当前 cfx 置为未实现的 cfx；是否加防护 | ❌不修 | — | QEMU `helper.c` 同口径（`*p = val`，escape 直接取用）；`§3.6` 定为 RW，加防护即偏离 |
| `isa.cc` 的 `-d cpu` dump 只输出 `prevRunMode`，未加 `prevCfxCode` | ⏸延后 | — | 该文件不在任务清单；语义与证据不依赖它（观测面 = RAM 槽 + guest rc） |

### 第 1 轮 reviewer 验收（2026-11-19，中改：≥2 路注入含 1 路未列）

**自证与范围**：独立任务 worktree（`git rev-parse --show-toplevel` 自证 ≠ 主工作树）、分支 `m16-gem5-013`、`git status -uall` **0 行**（动作前后快照均 0 行，HEAD 恒 `d2a9a871`）；`git show --stat d2a9a871` = **恰 6 文件**（本任务书 + `components/gem5/changelog.md` + 4 份 gem5 补丁，66+/14−）。越界 `git diff d2a9a871^ d2a9a871 -- spec/ tests/inst components/{linux,qemu,chipyard}` = **0 行**；6 文件之外零改动 ⇒ **版本号未动**。

**重跑记录（我方真实输出/退出码，不采信完成区转述）**
1. 运行期证据目录内的 `run.sh` ⇒ `RESULT: PASS (24 checks)`、**exit=0**（PASS 24 / FAIL 0）：A、B 各 6/6；C 组 `0x3f/0x02/0x03` gem5==QEMU==spec 共 9 项；D 组 `cmp` 逐字节相同（96 B / 184 B，两侧 md5 `1fb42c10…`、`11a0169b…`）；E1 `--source-state: gem5: OK HEAD=43ec73b1b7d4 count=1 clean=True`；E2 `gem5: 107 patch(es)` problem=0；F1 `check-wuming-cycles` rc=0、F2 `check-component-changelog` rc=0、F3 `check-inst-asm` `272/272` rc=0。
2. 同一脚本 `--inject all` ⇒ `RESULT: PASS (22 checks)`、**exit=0**：`save`⇒`0x61`、`restore`⇒**`0x7e`（CFXESC 复现）**、`tiny`⇒`rc=9 bytes=differ`，三路均「注入红 → `cp`+md5（`b7ec31a5…`/`9f0e2472…` 相等）→ 重建 → 回绿」。**重试 1 次**：第 1 次在 G.save 还原后重建阶段被环境中断（脚本进程消失、根因未定位；同时段 ≥3 个并发写会话），当时源树已 `cp`+md5 还原、`git status` 空、`make build-gem5` rc=0、探针 `async_in_frame`/`boot_prev_code` 均 `rc=0x00` 确认回绿后才重跑 ⇒ 未以重试掩盖根因。
3. **未列注入（reviewer 独立，非 engineer 自检）**：把 `nodeCfxEnter` 的 `prevCfxCode = s.cfxCode & 0x3F` 由 step 5 **挪到 step 6 之后**（源树 `1 insertion, 1 deletion`）⇒ 重跑**同一** `run.sh` ⇒ **exit=1**、`RESULT: FAIL (9/24)`（`A gem5 … got=1 5 1`、`C dump_boot_prev gem5 vs spec exp=0x3f got=0x03`）⇒ `cp`+md5 还原（`b7ec31a5…` 相等、源树 `git status` 空）⇒ 重建 rc=0 ⇒ 同一脚本 **exit=0**、`RESULT: PASS (24 checks)`。
4. 门控（我方执行）：`check-index-blobs` **rc=0**（`327 new-file patch(es) OK`）、`check-knowledge-refs` **rc=0**（悬空 0）、`check-wuming-cycles`/`check-component-changelog`/`check-inst-asm`（`272/272`）rc=0（见 1 的 F 组）；`make check-patch-tree` rc=2 但 **gem5 段 0 problem / 107 补丁**，11 条问题**全 `linux:` 前缀**（`m14-linux-017` 在「进行中」表 ⇒ 非本任务）。
5. 补丁纪律：`python3 tools/infra/make_patch.py gem5` ⇒ **rc=0、`0 written, 107 unchanged`**、重导出后 `git status` **仍空**（幂等；与完成区 `4 written/103 unchanged` 仅导出时机之差，4+103=0+107=107）；4 份补丁 `index 0000000..<h>` 与源文件 `git hash-object` **逐个相等**（`7dafa3e`/`d234e57`/`07ac9fe`/`84d4143`）⇒ **无手改 index**。

**语义核验（对照 spec 逐条）**
- `§5.2` 步骤 5/6：`node_cfx.cc:327` 采样位于 `:333 s.cfxCode = target` **之前**；`tiny_cfx.cc:183` 位于 `:204` **之前** ⇒ 同构 ✅
- `§5.3` 步骤 0/2：`nodeEscape` 先 `imms18`/reserved/`cfxha != cfxCode || causeId == 0` 检查（`:907-917`），再 `:929 cfxCode ← prevCfxCode`；`tinyEscape` 同序 ✅
- `§3.6` cg5 rc1：`cfxRegPtr`/`regPtr` 由 `reserved` 改 `case 1: return &r.prevCfxCode;`（读写同支 = **RW**，与 QEMU `helper.c:2025` 同形）、初值 0；`tiny_cfx.{hh,cc}` 字段/regPtr/enter/escape 与 node **四处同构** ✅
- **三值可由 spec 独立推出**：`Kaiwu §6.2` 步 6 power `trap cfx_hmon`（复位 cfx=63=`cfx_power`）⇒ hmon 帧 `0x3F`；body 在 hmon(3) 显式 `trap cfx_smon` ⇒ smon 帧 `0x03`；smon 帧内异步 TIMER 进入时 `inner_cfx_code=2` ⇒ hart 帧 `0x02` —— 与实测逐值一致 ✅

**「需上层知道」两项核验**
- ① **属实**：`tests/ee-tiny/run_inst_tiny.py:257 run_gem5()` 的 argv 无 `--semihost`（`fs.py.patch:84` 默认 `off`）⇒ semihosting trap 落 `machineFaultAt(FaultILLI)`（`inst.cc.patch:700`）⇒ 永不 `SYS_EXIT` ⇒ `m5.simulate()` 无界。实测 `--platforms gem5` ⇒ `[FAIL] … rc {'gem5': -2}` ×2、`0/2`、exit=1；同 ELF 的 QEMU lane 2/2、96/184 B。**⇒ 记 finding，交 architect 立 testcases 任务**。
- ② **实质准确、措辞略窄**：`§3.4 cg3 rc12` 初值全 1、`bit=0` 才放行 supv；但 `delegDenied()`（`node_cfx.cc:517`）按目标 cfx 的 hypv 行判定、**无自身例外**，故限制的是「supv 访问**任意** cfx（含自身）的 cg5」，完成区写「其它 cfx」⇒ 文档级小错，记 finding 不阻断。

**新发现（不阻断，交 architect 定夺）**
- F1：gem5 `nodeEscape:920` 缺 QEMU 的 `saved_intr_mask_valid` 守卫（`helper.c:2889`）⇒ 从**同步异常帧**（`nodeCfxRaise` 不调 `nodeFrameBlockAsync`）escape 会把 `cfx0.global_cfx_intr_mask` 写成 0，而 QEMU 不写；本任务未改该行、探针场景不触发 ⇒ 不阻断，建议另立任务。
- F2（文档/卫生级）：任务书「验收」编号 1,2,3,4,**6**,7 缺 5；任务运行期临时目录残留 **10 个 23:49 起的孤儿 `gem5.opt` 进程**（收尾须杀掉；reviewer 各轮**未**新增孤儿）。

**硬约束逐条**：① 独立 worktree、未改主工作树、**未提交 git**（`git status` 全程 0 行、HEAD 恒 `d2a9a871`）✅ ② 未改 `spec/`、未改 `tests/inst` ✅ ③ 未碰 `components/chipyard`（及 `linux`/`qemu`）✅ ④ 反例还原全用 `cp`+md5，**未用** checkout/restore/stash/show ✅ ⑤ 构建与门控串行、未并行 ✅

**判决：Accepted** —— `run.sh` 24/24（exit=0）、`--inject all` 22/22（exit=0）、未列注入「红 exit=1 → `cp`+md5 还原 → 回绿 exit=0」；五项门控 rc=0；语义四条与 spec 逐条对齐；硬约束 1–5 无违反。

## 完成区

**测试结果**：默认证据脚本（运行期证据目录内的 `run.sh`）24/24 PASS；`--inject all` 3 路反例（save/restore/tiny）共 22 项全部「注入红 → `cp`+md5 还原 → 回绿」；门控 `check-wuming-cycles`、`check-component-changelog`、`check-inst-asm`（272/272）rc=0；`check_patch_tree --source-state` gem5 = `base+1 clean`；`check-patch-tree` gem5 段 0 problem / 107 补丁（repo-wide rc=2 的 11 条问题全为 `linux:` 前缀，属 `m14-linux-017` 在途，非本任务）。
**修改文件**：`components/gem5/patches/src/arch/dadao/{node_cfx.hh,node_cfx.cc,tiny_cfx.hh,tiny_cfx.cc}.patch`（`make_patch gem5` 重导出 4 written / 103 unchanged）、`components/gem5/changelog.md`、本任务书；`.work/source/gem5` 的 4 个源文件已收敛为 base+1 提交 `43ec73b`。
**验收结果**：
- Node/Vast（A/B/C 组）：supv 帧内投递 TIMER ⇒ 两层帧 `escape` 均成功；`cg5 rc1` 实测 boot 帧 0x3F、hart 帧 0x02、smon 帧 0x03，gem5 与 QEMU **逐值一致**（同场景 cg5 rc1 与 `inner_cfx_code` 两方对照成立）。
- 反例（G 组，真实 rc）：删恢复行 ⇒ guest rc `0x7E`（`CFXESC` 打回当前 cfx 的 handler）；删保存行 ⇒ `0x61`；删 Tiny 恢复行 ⇒ 载体 gem5 lane `rc=9` 且字节流不一致；三者还原后均回绿。
- Tiny（D 组）：`escape_ciii_cfx` / `cfx2rd_crrr_cfx` 在 gem5 FS 与 QEMU 的 semihosting 字节流逐字节相同（96 B / 184 B）。
- 补丁纪律：补丁由源树 `git diff` 导出（E1 拒绝脏树）；`--source-state` 与 patch-tree 断言⑥ 均过。
**新发现/坑**：① `tests/ee-tiny/run_inst_tiny.py` 的 gem5 lane 不传 `--semihost on`（`fs.py` 默认 off）⇒ 载体在 gem5 上把 semihosting trap 当普通 trap，必超时（rc=-2）；证据改用 parity shim 跑同一 ELF。② supv 下访问其它 cfx 的 `cg5` 还受 `cg3 rc12 cg_reg_deleg`（重置 ~0 = 全委派给 hypv）限制，「self bypass」不是唯一门。③ 帧内嵌套投递后，`escape` 的 `cause_ip` 语义分两类：异步用 `imms18=0`（重执行被打断指令）、trap 用 `imms18=1`（`cause_ip+4`）。
**遗留问题**：① `run_inst_tiny.py` 的 gem5 lane 缺 `--semihost on`（建议 testcases 模块另立任务；本任务范围外）；② chipyard 侧三方对照由 `m16-chipyard-005` 出结论后由主会话补；③ `isa.cc` dump 未加 `prevCfxCode`（见自审 ⏸延后行）。

