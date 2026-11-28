# m18-gem5-002: gem5 `CFXESC` 交付路由（fallback 进当前 cfx，而非当前模式 monitor）

**模块**：gem5
**项目里程碑**：M18
**依赖**：`m18-gem5-001`（`escape` frame selector 语义/断言）合入；`m18-spec-005`（R2 规格）已验证
**可并行分片**：否（同改 `components/gem5`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（`m18-gem5-001` 现场发现，2026-11-24）

`m18-gem5-001` 已按 R2 让 `imms18=2`（`imms18[1]=1` 走 `cg9`）在 `exec/b6.cc::executeEscape()` 里恒投 `Fault::CfxEsc`。但该故障在 `exec/inst.cc` 的既有 fallback 分支里走：

```cpp
case exec::Fault::CfxEsc:
    // Tiny's escape hook raises CFXESC into the current cfx itself; this
    // branch is only a fallback and still enters the current monitor.
    if (fs) return DadaoISA::machineFaultAt(DadaoISA::FaultCfxEsc, ip, word);
```

`machineFaultAt(...)` 进的是**当前运行模式的 monitor**：`m18-gem5-001` 的 reviewer 已实测确认——Tiny 上 `Fault::CfxEsc` 走 `machineFaultAt(target=-1)` ⇒ `target<0` 时 `TinyCfxhaHmon`；Node 上 `target = runMode` ⇒ 当前运行模式 monitor。而 `spec/DADAO-12 §5.1/§5.3` 要求 `CFXESC`（escape 帧/目标错误）交付给**当前核芯功能扩展**、不属于 monitor 路由。对照：`cg5` 帧走 hook（`target = cfxCode`）是**正确**的，**只有 cg9/无帧路径错**。
  ⇒ 修点明确：`inst.cc.patch` 里 `Fault::CfxEsc` 的 fallback 需把目标从 `-1`/`runMode` 改成**当前 cfx 编号**（若该处拿不到，就从 decoder/helper 带下来）。

## 目标

1. **坐实差异**（先做）：构造最小例（`escape` 合法帧但目标 cfx 走 fallback 路径），在 gem5 上观测到「进当前模式 monitor」；与同 ELF 的 QEMU 行为对比（QEMU 应进当前 cfx），给出两侧 trace/日志。
2. **修路由**：fallback 改为投递给**当前 cfx**（与 `cfx` 的处理入口一致，权重/优先级按 `DADAO-12 §5.1`），删除 `inst.cc` 里「only a fallback and still enters the current monitor」的自述注释；若 gem5 侧确实无法在 fallback 里定位当前 cfx，应在 decoder/exec helper 层把 cfx 编号带下来，**不得**降级为「进当前 monitor」。
3. **三方一致**：同一 ELF 的 QEMU / gem5（/ chipyard 若可跑）签名流逐字节一致；不一致项逐条归因。

## 验收（逐条贴真实 rc）

1. 最小例在修前红（进错 monitor）、修后绿（进当前 cfx），两侧证据齐全。
2. `escape` 合法帧 + `CFXESC` 可达路径至少 2 例覆盖（cg5 帧、cg9 捕获缓冲各一），且**不影响** `imms18=3`/`[17:2]` 非零/reserved cfx 的 ILLI 判定顺序。
3. 可达 FAIL ≥2 路（把路由改回 monitor ⇒ 红；把 `imms18` 判定顺序改坏 ⇒ `check-gem5-decode` 红），`cp`+md5 还原。
4. 补丁由 `make_patch.py gem5` 重导出，`check-patch-tree` gem5 段 0 problem；`check-gem5-decode`（positive/negative 全量）rc=0。
5. `build-gem5` rc=0；长命令 `setsid nohup` + 日志 + `*_EXIT`。
6. 若 QEMU/RTL 侧同样存在「fallback 进 monitor」⇒ 在完成区列出并建议后续任务，**不在本任务扩范围**。

## 约束

独立 `git worktree`（分支 = `m18-gem5-002`）；不提交 git；只改 `components/gem5/**`（含重导补丁）与必要探针/任务书；不改 `spec/`/契约；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**（运行期证据目录内 `run.sh` 与 `run.sh --inject`，日志 `<证据目录>/logs/`）：
- `run.sh` **28/28 PASS rc=0**；`run.sh --inject` **39/39 PASS rc=0**（3 条注入→红→还原→绿 + 基线红判据）。
- 门控真 rc：`check-gem5-decode` 0、`check-qemu-forms` 0、`check-legality-drift` 0、`check-component-changelog` 0、`check-no-residue` 0、`check-patch-tree` gem5 段 **0 problem**（106 patch(es)）、`--source-state` gem5 `HEAD=230879da258b count=1 clean=True`；`build-gem5` rc=0；`tools/gem5/check_b6.py` rc=0（30/30、`encode_sbz=14`/`encode_cfx_reserved=5` ⇒ `imms18` 判定顺序未改坏）。
- 长命令：`build-gem5`（含注入回路共 4 次增量重建）与 gem5/QEMU 跑例全部 `setsid nohup` + 日志 + `*_EXIT`；日志见 `<证据目录>/logs/`（`rebuild-*.log`、`run-inject.log`）。
- `tests/unit/gem5/check_tiny_hmon.py` rc=1（29 条 FAIL）＝**基线即红**（陈旧 oracle，遗留 1）；注入 A 下其 FAIL 集与修复后逐行相同（`logs/run-inject.log`）。

**关键真实输出**（64 B 见证 = 8 个大端 64 位字；gem5 与 QEMU 用 `cmp` 逐字节相同）：
- Tiny：`...0001 ...0008 7efc0002 ...0001 7f0f0001 0 ...0001 ...0021` ⇒ marker=cfx63、cfx63 `cause_id=1<<3`、`info=0x7E<<24|63<<18|2`、cfx3 未被改写、退出 0x21。
- Vast（在 cfx2 smon 执行 cg9 escape）：`...0001 ...0008 7e080002 0 0 0 ...0001 ...0021` ⇒ CFXESC 落 cfx2、hmon `FAULT_RECORD`=0、退出 0x21。
- 注入 A（路由回 `machineFaultAt(...,-1)`）rc=113、见证 `...0002 0 0 ...0008 7efc0002 ...71`（落 hmon、cfx63 未写）＝修前红，还原后 0x21；注入 B（`imms18` 两条 legality 换序）`check-gem5-decode` rc=2，还原后 0；注入 C（去掉 `nodeEscape` 的 cg9⇒CFXESC）Vast rc=113、见证 `...0002 1 7f080000 0100 ...71`，还原后 0x21。

**修改文件**：`components/gem5/patches/src/arch/dadao/{inst.cc,fs_machine.hh,fs_machine.cc,node_cfx.cc,tiny_cfx.cc}.patch`、`components/gem5/changelog.md`、本任务书；探针与 `run.sh` 在运行期证据目录（不入库）。

**新发现/坑**：
- `tests/unit/gem5/tiny_hmon` 的 CFXESC 记录是**陈旧 oracle**：应用实以 cfx63 运行（`escape` 恢复 `excp_prev_cfx_code`；QEMU 同结论），目标/帧错误进 cfx63 而非 hmon；该例 `imms18=1` 走 `tinyEscape`、不经本次 fallback ⇒ 与本次改动无关（基线即红）。
- QEMU Vast `-kernel` 只接受 K0 ABI（`p_paddr = p_vaddr − 2 TiB`、`e_entry == kernel base VA`）；与 gem5 step5 固件（identity map、跳固定 `ENTRY`）对比必须用 **raw binary** kernel。
- semihosting `SYS_OPEN` 第二参数是**模式号**（5 = `"wb"`）不是字符串指针；`set.rb` 只写给定 wyde，其余 wyde 保持原值（探针改用 `set.zw wp0,0` + `or.w`）。
- gem5 Node 的 `escape` 在 `inst.cc` 被提前拦截（不走 B6），故 fallback 在 Node 上不可达；本次顺带把 `nodeEscape` 的 cg9 语义对齐 QEMU。
- 建议沉淀：CFXESC/CFXTRAP 交付与 §7.1 停机码口径（当前 cfx / other-cfx 段，唯 `escape` 帧错误不属于 monitor 路由）；两 profile 启动后当前 cfx 链；arch/unit 用例的 kernel 装载差异（ELF vs raw bin）。

**审阅后注记（第 1 轮 finding 处置）**：① evidence `run.sh` 先跑探针后建 binary——纯跑时可能吃旧二进制，**后续同类脚本须先建后跑**；② `check-patch-tree` 只断言 gem5 段、忽略总 rc（linux/musl 基线在途）；③ `check-knowledge-refs` 的 `milestones-m17.md:37 ADR-0063` 悬空属他人改动（`4d7a0d30`），与本任务无关；④ `tests/unit/gem5/check_tiny_hmon.py` rc=1 为**基线即红**（已用 `git archive HEAD` 逐行 diff 证明），oracle 陈旧另立任务。

**遗留问题**：
1. `tests/unit/gem5/tiny_hmon` 的 CFXESC 用例（`f_esc`/record 33-34/`trap_num`）是陈旧 oracle（基线即红 29 条），建议后续任务改为「cfx63 hypv 向量指向应用内落点、读 cfx63 `cg5`」并更新 `expected.yaml`；本任务不扩范围。
2. chipyard RTL 未跑；QEMU 侧无同类缺陷（`helper_cfx_escape()` 恒用 `inner_cfx_code`），RTL 侧建议后续用同一探针审。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

- 逐行复核 `inst.cc`：`currentCfx()` 三态（node/tiny/无 cfx）与 `cfxCode` 位宽一致；fallback 在 `fs` 且无 cfx 状态时 `panic`（不留静默/降级）；SE 分支的 `panic` 文本保持原样。
- `machineFaultToCfx()`：唯一调用点在本任务新增处（全仓无其它 caller），`MachineFault` 构造顺序（cause,target,ip,info,sub）核对无误；Tiny 向量不可达时 `machineFaultExit(cause, runMode, targetCfxha>=0)` ⇒ `0x80|cfxHA`。
- `nodeEscape()`：step 0 顺序 = SBZ → `imms18==3` → reserved → 目标/帧/cg9（与 QEMU 同序）；`imms18==1` 正常路径逐行未变（只多了一次 `ci` 之外的常量比较）。
- `tinyEscape()`：`imms18>3`/`==3` ⇒ ILLI 走 `-1`（monitor），`==2` ⇒ `s.cfxCode`；`imms18∈{0,1}` 路径与基线逐行等价（已用基线 patch 原文对照）。
- `nodeSyncEnter()`：`(toCfx || target > 3) ? target : -1` 的优先级已核对（`||` 高于 `?:`）；monitor 路由仍得 `-1`。
- 防造假：三份注入均以 `cp`+md5 备份/还原（`md5sum` 逐次打印），还原后重跑门控与探针回绿；见证值来自真实文件 `cmp`，无手写常量比较之外的估计。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| fallback 仍把 CFXESC 送当前模式 monitor | ✅已修 | `inst.cc` 改投 `currentCfx()`，新增 `machineFaultToCfx(cause,cfxha,ip,info)` | Tiny/Vast 探针 gem5↔QEMU 见证逐字节一致；注入 A 回红 |
| `inst.cc` 自述注释「only a fallback…monitor」误导 | ✅已修 | 注释改写为「交付当前 cfx + cg9 是编码级路径」 | `check-no-residue` rc=0；`git diff` 无该句 |
| Node `escape` cg9（`imms18=2`）被 `imms18 & ~1` 判成 ILLI（与 QEMU 不一致，且进 monitor） | ✅已修 | `node_cfx.cc::nodeEscape` step 0 重写 | 注入 C 复现旧行为（红）；修复后 Vast 探针绿 |
| Tiny `tinyEscape` 的 `byteOffset∈{0,4}` 判定把 cg9 编码当 ILLI | ✅已修 | 同 step 0 口径（`imms18>>2`/`==3`/`==2`） | `check_b6.py` rc=0（30/30）；探针绿 |
| `CFXTRAP`/`CFXESC` 向量不可达时用 monitor 段停机码（`target<=3`） | ✅已修 | `nodeSyncEnter` 按 cause 选段 | 代码复核 + `check-gem5-decode`/B6 无回归 |
| `tests/unit/gem5/tiny_hmon` 29 条 FAIL（陈旧 oracle） | ❌不修（任务书约束禁改 `tests/**`；已登记遗留 1） | 无 | 基线即红：注入 A 下 FAIL 集与修复后逐行相同（`logs/run-inject.log`） |

### 第 1 轮 reviewer 验收（2026-11-25，独立重跑）

**重跑（rc 取被检命令自身，无 `| tee`）**：运行期证据目录内 `run.sh` ⇒ `PASS (28/28)` rc=0；`run.sh --inject` ⇒ `PASS (39/39)` rc=0。三注入在我手上真红：A `Tiny` 探针 rc=113、见证 `…0002 0 0 …0008 7efc0002 …0071`；B `check-gem5-decode` rc=2；C `Vast` rc=113、见证 `…0002 1 7f080000 0100 …0071`；`cp`+md5 还原后分别回 0x21/0/0x21。

**门控直跑**：`check-gem5-decode` rc=0（positive 263/263、negative 391/391、legality 28/28、legacy 2/2）、`check-qemu-forms` 0、`check-legality-drift` 0、`check-component-changelog` 0、`check-no-residue` 0、`tools/gem5/check_b6.py` 0（30/30、`encode_sbz=14`、`encode_cfx_reserved=5`）、`make build-gem5` rc=0、`--source-state` gem5 `OK HEAD=230879da258b count=1 clean=True`。`make check-patch-tree` 总 rc=2，但 gem5 段 `106 patch(es)`、0 assertion；6 条 assertion 全在 `linux`/`musl`（本 worktree HEAD 落后 master、共享源树属他方在改），非本任务面。

**三方见证**：我自行组装/链接/重跑 Tiny 探针：gem5 rc=33、QEMU rc=33、`cmp` 64 B 见证 rc=0 且与证据目录见证字节相同；Vast 由两次 `run.sh` 的 `cmp` 断言通过；Vast 用 raw-binary kernel 合规（`Kaiwu §6.3.2` raw 四规则，PA `0x100000` = `kernel_base` − 2 TiB，与 gem5 step5 固件 identity + 固定 `ENTRY` 同址；ELF 路径须 K0 ABI，故不可用）。

**补丁未手改**：`git diff c8222cc… --name-only` = 106 条，逐条与 `components/gem5/patches/**.patch` 字节相同（0 mismatch）；源树 5 文件 == 补丁正文；工作树快照与收尾逐行一致（仅声明的 7 个文件，`tests/` 0 改动）。

**第 6 条（基线即红，本轮重点，已证伪）**：`git archive HEAD` 取 5 份 HEAD 补丁覆写源树 → `make build-gem5` rc=0 → `tests/unit/gem5/check_tiny_hmon.py` rc=1、29 FAIL；`cp`+md5 还原 → `make build-gem5` rc=0 → 同门控 rc=1、29 FAIL；`diff` 逐行**为空**（两侧 md5 同 `bfcd47e600508b8da4f284431e05f2b8`）⇒ 基线即红、本任务零回归。因果核对：该例仅 3 处 `escape`、`imms18∈{0,1}`，B6 对 `imms18=2` 在调 hook 前即返回 `Fault::CfxEsc`，故 `inst.cc` fallback 与 `tinyEscape` step0 改写在本例不可达/逐行等价。

**独立注入（我自做，非 engineer 自检）**：`tiny_cfx.cc` 的 `TinyCauseCfxEsc` 目标 `s.cfxCode → TinyCfxhaHmon` ⇒ `run.sh` rc=1（2/28 FAIL，含 `tiny_hmon anchors` 行为性红）；`cp`+md5 还原（file==bak）⇒ `run.sh` rc=0（28/28）。

**代码核**：`currentCfx()` 三态（node→tiny→-1）+ `machineFaultToCfx(cause,cfxha,ip,info)` 构造序 `(cause,target,ip,info,sub)` 正确；`MachineFault::invoke` Tiny→`tinyCfxRaise(target=cfxCode)`、Node→`nodeSyncEnter(target=cfxCode)`；无 cfx 状态显式 `panic`；全仓无残留 `machineFaultAt(…FaultCfxEsc…)`/`runMode` 降级。step0 与 QEMU `helper_cfx_escape` 同序（SBZ→`==3`→reserved→目标/帧→cg9；三支同果、`||` 短路无越界）。`nodeSyncEnter` 的 `toCfx||target>3 ? target : -1` 符合 `Kaiwu §7.1`「CFXTRAP/CFXESC 恒 other-cfx 段」；同步异常不进 `!sync` 掩码分支。

**findings（不阻断）**：① `run.sh` 先跑探针、后跑 `make build-gem5`，纯跑时探针可能吃旧二进制（头注释声称的「比源码新」检查未实现）——建议把 build 提到探针前；② `run.sh` 的 `check-patch-tree` 只断言 gem5 段、忽略总 rc（与本任务验收口径一致）；③ `make check-knowledge-refs` 基线即红 1 条：`.tao/knowledge/milestones-m17.md:37 ADR-0063 目标文件不存在`（源自 `4d7a0d30 派单 m17-idl-021 / m17-spec-004`，与本任务无关；写入本记录前后输出逐字节相同）；④ changelog「`check_tiny_hmon` 不回归」与 rc=1 并存，建议 architect 收尾补「基线即红」字样。

**判决：Accepted**
