# m16-chipyard-026: RTL 异步捕获缓冲（ADR-0061 R2）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-024` 已合入（在其上改）；`m18-spec-005`（R2 规格）已合入
**可并行分片**：否（同改 `components/chipyard`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（R2，`spec/DADAO-12 §5.4`）

`m18-spec-005` 把 `cfx_hart cg9` 改为**进入瞬间的捕获缓冲**：每次异步进入都整体覆盖（`prev_*`/`cause_ip`/`src_frame`），**没有"帧活动期"、没有 `frame_valid`，硬件不因 `src_frame != 0` 拒绝进入或只置 pending**；软件在关中断窗口把 `cg9` 与 GPR 搬到任务现场，再 handoff 到 `cfx_smon`；返回走 smon/umon，`escape` **不以 `cg9` 为返回帧**（`imms18 = 2` ⇒ 当前 cfx 的 `CFXESC`，不改 cfx/mode/cg9）。来源掩码仍在当前运行模式 monitor 的 `cg8 rc1`，pending 跟随源、投递即清。

`m16-chipyard-024` 实现的是 pre-R2（`src_frame != 0` 防重入、`escape` 释放帧），本任务改到 R2。

## 要做

1. **仲裁去帧门控**：删除 `src_frame != 0` 的"只置 pending/不进入"分支；同一指令边界把 `pending & ~mask` 一次投递、整体覆盖 `cg9`；`pending` 扣除、`excp_async_num` 每次进入 +1。
2. **`escape`**：`imms18[1] = 1`（`imms20 = 8`）**不再异步返回**——按"所选帧无效"报当前 cfx 的 `CFXESC`，不改变 cfx/运行模式/`cg9`；`imms18 = 3` ⇒ `ILLI` 保持；同步 `cg5` 帧语义不变。
3. **探针**（`tests/arch/hart/cfx15.S` + `check_cfx15.py`）：
   - `cg9` 七槽与 RO（写忽略、读回不变、无异常）；捕获快照 `prev_*`/`cause_ip`/`src_frame` 位 = 15；
   - **覆盖语义**：第一次进入后不搬走，再次到期 ⇒ 整体覆盖（`cause_ip`/计数变化），**不是**只置 pending；
   - 掩码屏蔽时只置 pending、放行后投递；ack 源（重装 `timer_cmp`）后 pending 落；
   - `escape imms18=2` ⇒ `CFXESC`、`cg9` 不变；`3`/`[17:2]≠0` ⇒ `ILLI`；
   - H/S/U 三模式（各写自己 monitor 的 `cg8 rc1`）。
4. **不回归**：同步 cg5 帧（020 的 U/S 路由、同步 `escape`）、Tiny（无 cfx15）、cfx5/cfx02 探针。

## 不做

- 不做软件侧 handoff 到 `cfx_smon`（内核任务 `m18-linux-022`）；
- 不改 QEMU/gem5/spec；
- 不引入 `frame_valid`/软件清 `src_frame`。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 覆盖语义（不搬走再到期 ⇒ 整体覆盖，不是只置 pending）；
2. `escape imms18=2` ⇒ `CFXESC` 且 `cg9` 不变；`3`/SBZ 非零 ⇒ `ILLI`；
3. 掩码/pending/ack、RO、三模式；
4. **可达 FAIL ≥2**：注入"恢复 `src_frame != 0` 门控"、"`escape imms18=2` 返回" ⇒ 红；`cp`+md5 还原并强制重建后回绿；
5. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog`/`check-no-residue`、`run_arch.py --self-test` 记录 rc。

## 完成区

**测试结果**：运行期证据目录内 `run.sh`：A 16/16、B 10/10、C 7/7、D 9/9、E 6/6、F 8/8（首次含 pre-026 基线重建时 20/20；末次整体跑 A–F 合计 **56/56，rc=0**）；`--inject` G 36/36（rc=0）。三模式（同一份 `cfx15.S`，汇编期 `TMODE=3/2/0`）H 74 槽、U/S 各 34 槽逐槽等于现场从 `spec/DADAO-12` §1/§3/§4.1–§4.7/§5.1/§5.4、`ADR-0061`、`contract-see` §3/§6.1 与 `contracts/opcodes.yaml` 派生的期望。

**修改文件**：`components/chipyard/patches/generators/dadao-gewu/.../GewuFile.scala.patch`（仲裁去帧门控；删除 `escapeCg9Ok`、cg9 返回/释放路径；目标/cause/prev 收口到 cg5）；`components/chipyard/patches/generators/dadao-wuming/.../WumingCore.scala.patch`（异步投递注释改 R2 口径，行为不变）；`components/chipyard/{README.md,changelog.md}`；`tests/arch/hart/{cfx15.S,check_cfx15.py,README.md}`；`tests/arch/README.md`；`tests/arch/expected-divergences.yaml`（DIV-11 改 R2 口径）；本任务书；运行期证据目录内 `run.sh`。未改 spec/contracts/QEMU/gem5/工具链；`series` 仍 30 条。

**验收结果**：① 覆盖语义：handler 内不搬走现场再武装 ⇒ 第 2 次进入（prev_mode=supv、prev_cfx=15、`cause_ip`=再次武装后边界、`src_frame`=0x8000、pending=0、`excp_async_num`=2），**不是**只置 pending；第 3 次（放开掩码后）=3。② `escape imms18=2`：`cfx_hart cg5` cause=CFXESC、info=`0x7e3c0002`、prev=supv/15，`cg9` rc0–rc3 与捕获槽逐槽相同；`imms18=3`/`4` ⇒ ILLI（info `…0003`/`…0004`）；同步 cg5 escape 照常（esc9 返回、h_fault 返回）。③ 掩码/pending/ack：hmon/umon/smon 各自 `cg8 rc1` 屏蔽 ⇒ pending=0x8000、frame 不变；放开 ⇒ 下一指令边界投递（`cause_ip` 精确等于等待标签）；supv 下屏蔽 smon 行 ⇒ pending=0x8000；重装 `timer_cmp` ⇒ pending=0；再武装 ⇒ 0x8000。④ RO：`cg9 rc3/rc4` 写 PATTERN 读回不变且不报异常；`rc7/rc8/rc15`、写 `cg8 rc0`、读 `cg8 rc1` ⇒ CFXREG。⑤ 三模式：U prev=user/umon、S prev=supv/smon、H prev=hypv/hmon，投递目标均为 cfx_hart+supv。⑥ 注入：① 恢复 `src_frame != 0` 门控 ⇒ H slot58=`0xDEAD0001` 红；② 恢复 `escape imms18=2` 的 cg9 返回 ⇒ 探针回到被中断处、slot50=`0xDEAD0003` 红；两路 `cp`+md5（`e906ab02…`）还原、强制重建后 stream==reference 回绿。⑦ 构建：Vast 282–291 s（注入轮 289–295 s）、Tiny 104 s（pre-026 基线 109 s、恢复 113 s）；elab/verilator rc=0、`%Error`=0；末版 sim md5 Vast `984984f3…`、Tiny `e2c20bf9…`（只作记录，ISS-453）。⑧ 门控：`check-patch-tree` chipyard 段 0 problem（30 patches，全局 rc=0）、`make_patch` 幂等（0 written）、`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog`/`check-no-residue`/`run_arch.py --self-test` rc=0。⑨ Tiny：从 HEAD 的 024 补丁重建 pre-026 RTL 基线，对**同一份当前测试源** 11-cfx 5 镜像 + 01-load-store 38 镜像逐字节相同、rc 相同（`escape_ciii_cfx` 在 Tiny 上 rc=1 是 DIV-11 既有口径）。

**新发现/坑**：① supv handler 访问 cfx_smon 还受**目标 cfx 的 `cg3 rc12` deleg** 约束（不只 cfxreg 行）；未放开时写 `cg8 rc1` ⇒ CFXPERM，而 H/U 未设 smon 向量 ⇒ 跳 0 后 CFXMEM 死循环（900 s timeout）。修：init 放开 smon deleg 并挂 `smon_fault` 兜底。② 重新武装时 enable 已为 1，写 `timer_cmp` 当拍就产生事件 ⇒ 投递边界提前一条指令、`cause_ip` 精确定位失效；改为先关 enable→写 cmp→最后使能。③ handler 分派不能复用 hmon 入口的 `phase`（hmon 置 1 会跳过 phase1）；用独立 `hphase`。④ 020 的 Tiny 基线已过时（m17/m18 改过 11-cfx/01-load-store 源）；改用「HEAD 补丁重建 pre-026 GewuFile + 同一当前测试源」做基线。⑤ 注入 ② 只恢复 `escapeOk` 不恢复目标 mux 会用 cg5 旧 `cause_ip` 跳回 escape 自身（死循环），注入需同时恢复目标选择。⑥ 注释级改动会移动 Scala 行号 ⇒ Vast sim md5 变化（`8ddb8fd4…`→`984984f3…`），构建身份以末版源为准。

**遗留问题**：① 单源（TIMER）机器仍不能端到端观测「一帧多源」并集；PMEM_DMA 归 `m16-chipyard-022`。② `DIV-11`（Tiny 不认 `imms18 = 2`）维持，属 testcases 域。③ `run_arch.py` 的 chipyard 后端仍 fail-closed，`cfx15` 未登记 `tests/arch.yaml`（既有 DIV-06）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`GewuFile.scala` 的异步投递（`io.intr.valid`/`asyncAllowed`/`src_pending` 更新）、`escape`（`escapeOk`/target/cause/prev 写回）、异步入口（`cg9` 覆盖）、计数；`WumingCore` 注释；`cfx15.S` 全部槽序与三分支（H/U/S、handler phase1–3、esc9、fault 兜底）；`check_cfx15.py` 的 `facts`/`expected`/`check`/`self_test`；`run.sh` A–G。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 handler 复用 hmon 入口的 `phase`（hmon 置 1）⇒ 首次异步进入跳过 phase1 | ✅已修 | 新增 `hphase`，hmon 分派单独用 | H 74 槽全绿 |
| F2 supv 写 `cfx_smon cg8 rc1` 被目标 cfx deleg 拒绝 ⇒ CFXPERM 跳 smon 向量 0 死循环 | ✅已修 | init 放开 `cfx_smon cg3 rc12` bit8/9；`cfx_smon` 向量挂 `smon_fault` 快速失败 | 三模式全绿，trace 无 smon_fault |
| F3 `build_probe` 未把 `TMODE` 传给 `llvm-mc` ⇒ 三个镜像都是 H | ✅已修 | `llvm-mc -defsym TMODE=$mode` | C 期望槽 74/34/34，D 三模式绿 |
| F4 timer 已使能时重写 `timer_cmp` 当拍产生事件 ⇒ 投递边界提前一条指令 | ✅已修 | 关 enable→写 cmp→最后使能 | 覆盖槽 `cause_ip` 精确 = rearm 标签 |
| F5 020 的 Tiny 基线早于当前测试源（11-cfx/01-load-store 已改） | ✅已修 | F 段用 HEAD 补丁重建 pre-026 GewuFile + 当前测试源做基线 | 5+38 镜像逐字节相同、rc 相同 |
| F6 注入②只恢复 `escapeOk` ⇒ target 用 cg5 旧 `cause_ip` 死循环 | ✅已修 | 注入同时恢复 target 的 async 分支 | inj2 红（slot50=0xDEAD0003），无超时 |
| F7 `escape imms18=2` 后 `swym 0` 在 esc9 返回路径执行 | ❌不修 | 无架构副作用（trace 证实正常收尾） | H/U/S 均 rc=0 |
| F8 注释改动使 Vast sim md5 变化 | ❌不修（记录口径） | 构建身份以末版源为准 | B 段末版 md5 `984984f3…` |

判决：F1–F6 已修并复验，F7/F8 为有据的不修项；无未修 finding。状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-24）

**重跑记录**（均在任务 worktree 根执行运行期证据目录内的 `run.sh`，逐段取真实 rc，不采信完成区）：
- `ONLY=A` → `summary: PASS=16 FAIL=0` rc=0：apply 幂等 base+1、`check-patch-tree` 到达 chipyard 段且 0 error 行、30 条=series、`make_patch` 0 written、组件源树 clean、chipyard-only rc=0、`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog`/`check-no-residue`/`run_arch.py --self-test` 全 rc=0。
- `ONLY=B` → PASS=10 rc=0：Vast 284 s / Tiny 98 s，elab+verilator rc=0、`%Error`=0，sim md5 `984984f3…`/`e2c20bf9…` 与完成区一致。
- `ONLY=C,D,E` → PASS=22 rc=0：期望槽现场 74/34/34；三模式 guest rc=0、592/272/272 字节、oracle rc=0；`--self-test` 三模式 0 条未检出 mutation。
- `ONLY=F` → PASS=8 rc=0：`tiny026-cfx rc=1`、`tiny026-ls rc=0` 与基线 `1 0` 相同；reviewer 另用 `cmp` 现场重比 pre-026 vs 当前：11-cfx 5/5、01-load-store 38/38 逐字节相同、0 差异、0 缺失。
- `--inject INJ_ONLY=1` → PASS=18 rc=0：恢复 `src_frame != 0` 门控 ⇒ 红（`guest rc=1 oracle rc=1`），slot58=`0xdead0001`、slot59–61=`0xdeadbeef`；`cp`+md5 还原 `e906ab02…`、强制重建 291 s ⇒ `stream == reference` 回绿。
- `--inject INJ_ONLY=2` → PASS=21 rc=0：恢复 `escapeOk`+async 目标两处 ⇒ 红，slot50=`0xdead0003`、51–53 哨兵；两处还原（`e906ab02…`/`07b9a001…`）、重建 294 s 回绿。两路与共享前置去重后 36 = 完成区 G 36/36。
- A–F 合计 16+10+7+9+6+8 = **56/56 rc=0**，与完成区一致。

**R2 语义**：`io.intr.valid := asyncModel.B && asyncAllowed =/= 0.U`（`asyncFrameLive` 分支已删，全 patch 仅剩 reg 声明/读 mux/入口写三处 `asyncSrcFrame`）；入口 `prev_mode/prev_cfx/cause_ip/src_frame` 无条件整体覆盖、`src_pending` 投递即清、`excp_async_num` 每次 +1；`escapeOk = escapeCg5Ok`，`escapeCg9Ok`、target/cause 的 frame mux、`asyncSrcFrame := 0.U` 释放路径全删 ⇒ `imms18=2` 由 core `enterHmon(toCurrent)` 报当前 cfx `CFXESC` 且 cfx/mode/cg9 不变；`3`/`4` ⇒ ILLI（探针槽绿）；同步 cg5 返回由 `h_fault`/`esc9_entry` 覆盖且 D 段绿。

**探针/判据**：期望现场派生自 `spec/DADAO-12`/`ADR-0061`/`contract-see`/`opcodes.yaml`（非同源自比）；`--self-test` 每槽 mutation + 截断/多槽可达 FAIL；覆盖语义由注入①证伪（不覆盖 ⇒ 哨兵）；掩码/pending/ack、`cg9 rc3/rc4` RO、H/U/S prev（hypv/hmon、user/umon、supv/smon，目标 cfx_hart+supv）均绿。

**Tiny 对照成立**：基线 = 从 HEAD 的 024 补丁抽 pre-026 `GewuFile`（含 `asyncFrameLive`，md5 `e4a14b2a…`）重建，与**同一份当前测试源**比对；reviewer 独立 `cmp` 复核 43 镜像 0 差异、套件 rc 相同（1/0），Tiny 镜像与行为未变；`DIV-11` 的 Tiny `withHart` 口径与实际一致（`escape_ciii_cfx` 失败点=检查点 13）。

**门控与「全局 rc」真伪**：本树独立重跑 `make check-patch-tree` rc=0（11 patch set、462 patches OK）——但其余 10 个组件因源树不存在被跳过；**master 侧重跑 rc=2、26 problem**（qemu/gem5/linux/chipyard/linux 既有基线，`GewuFile`/`WumingCore` 不在问题清单；chipyard 段 8 条为 build.sbt/System.scala/IOBinders/bootrom 等 025 既有）。任务书验收只要求「chipyard 段 0 problem」，我这轮与 master 均逐行核过该段本任务文件无 problem。

**Findings（均文档级、不阻断）**：F1 完成区「全局 rc=0」未注明「本树仅 chipyard 源树、其余组件 apply 检查跳过」，master 全局实为 rc=2/26 problem（与本任务无关）——收尾补口径。F2 `DIV-11`「该链例在 Tiny 上 rc=1」是套件级 rc；镜像级 guest rc=13（`SYS_EXIT code=0xd`＝检查点 13）。F3 `run.sh` 的 `global rc=…（KNOWN-RED outside chipyard）` 提示语与实测 rc=0 过时（不参与断言）。

**工作区对账**：验收前后 `git status --porcelain -uall` 同为同一 10 行、10 个目标文件 md5 逐一相同；组件源 `GewuFile.scala` md5 `e906ab02…` 且源树 clean；`spec/`、`.tao/contracts/`、`contracts/` 零改动；未提交 git。

**判决：Accepted**——A–F 56/56、G 两路注入红→`cp`+md5 还原→强制重建回绿，全部为 reviewer 亲自重跑的真实输出/退出码；F1–F3 交 architect 收尾订正，不另开一轮。
