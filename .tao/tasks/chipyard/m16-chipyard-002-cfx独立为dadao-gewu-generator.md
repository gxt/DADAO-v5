# m16-chipyard-002: cfx 独立为 `dadao-gewu` generator（chipyard）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`ADR-0053`（Accepted，D1–D7）；`m12-chipyard-001`（补丁集接入与骨架）；`m13-chipyard-003`（当前基线，sim md5 `4e072a711afdca8a36788f9a9958e896`）
**可并行分片**：否（chipyard 组件单写者 + 同一 sim 构建）
**预估**：3–5 h（增量构建约 2 min/次、全量约 9 min；含 4 路注入重建）
**档位**：大改（RTL 结构重构 + 组件重建；复核需独立重跑 + ≥4 路注入）
**状态**：待验收

## 背景

cfx（机器级控制面：寄存器堆 + 判权 + 异常帧 + 向量 + `escape`/`power`/`hmon`）目前**内联**在 `generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala`（1,531 行）：

- 寄存器声明（`cfxTrapMask`/`cfxMemMask`/`cfxRegMask`/`cfxExeMask`/`cfxIntrMask`/`cfxVector`/`cfxPrevMode`/`cfxCauseId`/`cfxCauseIp`/`cfxCauseInfo`）在 line 188–220 一带；判权/分发在 line 274–294；写回与向量更新在 line 1430 一带；`escape` 合法性依赖 `cfxHasFrame`（line 1139）；向量直驱 PC（line 936–937）；
- 与 `cfx|CFX|cg[0-9]` 相关的行 **152 行**，散布 line 30–1522（与流水控制交织）；
- `WumingCore` 已实例化 8 个子模块（`rf`/`dec`/`alu`/`fpClassify`/`fpConvert`/`fpArith`/`fpSlow`/`fpMisc`），**cfx 是唯一没有独立模块的部件**；
- gem5 已有 `tiny_cfx.{cc,hh}`/`node_cfx.{cc,hh}`，chipyard 落后。

按 `ADR-0053`（D1–D7，用户 2026-11-15 确认）把它独立成 generator，供 `wuming` 及后续设计复用。

## 目标（逐条对应 ADR-0053）

1. **D1 装箱**：新建 `generators/dadao-gewu/`（in-tree 形态，照 `dadao-wuming`：根 `build.sbt` 为准，generator 内 `build.sbt` 只作文档），源码 `src/main/scala/gewu/GewuFile.scala` 内含 `class GewuFileIO` + `class GewuFile extends Module`；sbt 项目名 `gewu`。
2. **D2 接线 + 依赖方向**：根 `build.sbt` 三处——`lazy val gewu = freshProject("gewu", file("generators/dadao-gewu")).dependsOn(rocketchip)`、`baseProjects` 加入 `gewu`、`wuming` 改为 `.dependsOn(rocketchip, gewu)`；`gewu` **不得**依赖 `wuming`。
3. **D3 IO 契约**：`GewuFileIO` 覆盖 cfx 读/写（`cg`/`rc`/`ha`/数据/写使能/地址匹配）、异常入口（cause id/ip/info、vector、prev run mode）、帧存在与清除、运行模式、IP、中断 mask、`escape`、`power`、`hmon`、重定向请求；输入只接**架构级事件**。
4. **D4 重定向归 core**：`Gewu` 只输出 `redirectReq`/`redirectTarget`（附 cause 信息），PC 与 flush 由 core 驱动（替换现 `cfxVector(0)` 直驱 `ip :=`/`continueAt(...)`）。
5. **D5 参数化**：hart 数、帧数、实现的 cfx 集与位宽经 `Parameters`（新增 `GewuParams` 由调用核注入）；`gewu` 源码内**不得**出现具体核常量（现 `Seq.fill(2)` 之类）。
6. **D6 术语**：模块/文件名 `Gewu`，**寄存器名保持 `cfx_*`**；`GewuFile.scala` 文件头写「Gewu ≡ cfx 寄存器堆（类比 Rocket `CSRFile`）」；**spec 不改名**。
7. **D7 范围**：只搬 cfx 的状态与判权/分发（含 trap/escape/power/hmon）；`WumingDecoder.scala` 的 cfx 指令类解码（现 37 处）**留在 wuming**，作为 `Gewu` 的输入信号。
8. **补丁树**（`docs/Process-01`）：一文件一补丁，新增 `components/chipyard/patches/generators/dadao-gewu/**`，更新根 `build.sbt` 补丁与 `WumingCore.scala` 补丁，同步 `components/chipyard/series`。

## 验收（逐条贴真实 rc 与输出）

1. **补丁与源树一致**：`make apply-series`、`make check-source-state`、`make check-patch-tree` 全 rc=0；`python3 tools/infra/make_patch.py chipyard` 再跑一次**无 diff**（幂等）。
2. **静态边界**（现场 grep，非声明）：
   - `generators/dadao-gewu/` 内出现 `wuming` **0 次**（D2 反向依赖为 0）；
   - `generators/dadao-gewu/` 内无硬编码 hart/帧数常量（D5，改为取自 `Parameters`）；
   - `WumingDecoder.scala` 中 `cfx` 命中数**与改前相同**（D7：解码未搬走）。
3. **构建**：`make verilog CONFIG=WumingTinyConfig -j32` 与 `make CONFIG=WumingTinyConfig -j32` 均 rc=0，日志 `%Error` 计数 0；**记录新 sim md5**（旧 `4e072a71…` 作废），并确认两次重建 md5 一致（构建确定性）。
4. **功能与周期等价（核心证据）**：取 4 例——`trap_ciii_cfx`、`escape_ciii_cfx`（cfx 异常入口 / escape 返回）+ 1 个浮点例 + 1 个整数例；**改前 / 改后**各跑一遍，逐例比较：
   - ① guest 输出字节（`semi.out`）逐字节相同；
   - ② guest 退出码相同；
   - ③ 日志中 `cycle=` 值逐条相同（cfx/excp/cfxtrap 打印行）；对日志无 `cycle=` 的样例，允许在**两版上加同一临时探针**读结束周期后比较（探针不入库、不提交）。
5. **≥4 路可达 FAIL 注入**（`cp` 备份 + md5 还原 + 重建）：① `cfxVector` 写回值 +4 ⇒ `trap`/`escape` 例红；② 去掉 `escape` 的 `cfxHasFrame` 判断 ⇒ `escape` 例红；③ 改 `GewuParams` 的 hart 数（或中断 mask 宽度）⇒ 至少一例红；④ `redirectTarget` 接常量 0 ⇒ 红。每路贴「注入后真实红色输出 + 还原后回绿」。
6. **越界核对**：`spec/`、`contracts/`、`tests/`、`tools/`、`gem5`/`qemu` 组件 **0 改动**；L1 `make check` rc=0。
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只动 `components/chipyard/**`（补丁 + `series`）与 chipyard 组件源树（运行期检出）、本任务书；
- **chipyard 组件单写者**：本任务在跑期间不得有其它任务改同一组件；
- 构建与跑批**不得同时**进行；构建日志与 `*_EXIT` 落运行期日志目录；`JOBS=32`；
- 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore/stash`）；
- 不动 `WumingTile` 的对外签名（若必须动，在完成区披露原因）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-16）

逐行审查 `GewuFile.scala`（新 generator）、`WumingCore.scala` 的 cfx 接口替换、`WumingParams.scala` 的参数注入与根 `build.sbt` 接线；判决：**可标「待验收」**（findings 全部已修/已归属，复验见右列）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 首版把异常入口落点接 `redirect.target`（该 mux 受 `excp.valid` 选）⇒ elaboration 报组合环：`excpValid → redirect.target → finish` 的 IALIGN 判据 `→ enterHmon → excpValid` | ✅已修 | 入口落点改用 `gewu.io.vector`（寄存器输出），`redirect.target` 的 mux 只按 `escapeOk` 选（异常入口与合法 `escape` 不同拍） | `firtool` 通过（`%Error`=0）；37 镜像等价复验 |
| F2 `escape` 目标 IALIGN 失败那拍 `escapeOk` 仍为真 ⇒ 跳到未对齐的 `escape` 目标而非 `vector`（`escape_ciii_cfx` 链例 rc=9，输出空） | ✅已修 | 同 F1 的改法（入口一律走 `vector`） | 改前/改后逐例：`escape_ciii_cfx` 输出 md5 `cff360ff…`、rc 0、3068 条 `cycle=` 全等 |
| F3 `GewuParams` 的 `require` 用 `1 << dataBits`，64 位时 Int 溢出 ⇒ `switchModeValue` 误判超宽、elaboration 直接失败 | ✅已修 | 三条 `require` 改 `BigInt(1) << n` | elaboration 与 sim 均 rc=0、`%Error`=0 |
| F4 `gewu.io.escape.ha/off` 起初写在 `d`（decoder 输出）之前且漏接 ⇒ `sink not fully initialized` | ✅已修 | 接线移到 cfx 访问段（`d` 之后），`valid` 用 `false.B` 默认 + `escape` 分支内断言 | 同上 |
| F5 D2 静态门控抓到 `generators/dadao-gewu/build.sbt` 的说明文字里出现 `wuming` 一词（0 次要求） | ✅已修 | 改写为「consuming core's dependency set」并重导该补丁 | `grep -rn --exclude-dir=target wuming generators/dadao-gewu/` = 0 |
| F6 未实现 `cfxha`（如 `cfx_umon`=0）的**读数据**：旧码按 `monIdx=1`（power）选，新码按 `PriorityEncoder` 选到 0 号，`cfx2` 的 `data=` 跟踪字段会不同 | ❌不修（无架构影响） | 保持按「命中的实例」选；未命中时 `readOk=0` ⇒ 精确 CFXREG、写不落盘、读值不回写 | 交付的 6 个 id / 37 镜像逐条 trace（含 `cfx2rd` 的 cg3/cg5/cg7 读）全等；该字段只出现在 `ok=0` 的打印里 |
| F7 注入可能让镜像跑飞：`+max-cycles=20M` + `+verbose` 会写出 GB 级 trace 并跑几十分钟 | ✅已修 | 每镜像 `timeout` + 日志 5 MB 上限，超时/截断记为「与交付值不同」的红 | 注入 inj3a/inj4：29/29 镜像红（rc=141 截断），单轮 ≤ 5 min |
| F8 前两次 `--inject` 被外层 timeout 杀掉，源码停在注入态；备份文件放在 git 树里也污染「树是否干净」自检 | ✅已修 | 备份移到运行期证据目录；恢复用 `cp`+md5（与 HEAD blob 逐字相同）+ 重建 | `git -C <chipyard> status` 0 行；`restored GewuFile md5 == delivered` |
| F9 `escape` 的「帧有效」半条判据在本 profile 不可观测（`excp_cause_id` 无清零路径，`cg5 rc2` 是 HW-RO；`escape_ciii_cfx.S` 自记 GAP ③） | ⏸延后（记录不修） | 注入按「必须红」的期望改为「实测 0/37 差异」并在完成区写明原因；另用**可观测**的另半条（当前 cfx 判据）作红色路径 | inj2a：0/37 差异（如实记录）；inj2b：`escape_ciii_cfx` 链例红 |
| F10 注入红点的退出码是 141（日志上限截断）而非 guest 码 | ❌不修（如实记录） | 判据同时看 `semi.out` 字节、退出码、`cycle=` 序列三项 | inj1/inj3b 的红点是字节/周期差异（rc 仍 0）；inj2b/3a/4 是不终止 |
| F11 L1 `make check` rc=2：`check-patch-tree` 在 **qemu** 处中止（并行会话正在重导 qemu 补丁），非本任务 | ⏸延后（外部阻塞，已归因） | 证据脚本把判据落在 chipyard 段，并打印全局 rc 与出错组件 | L1 内 `check-patch-tree: chipyard: 23 patch(es)`、chipyard 断言 0 问题；同一交付树 22:47 的 L1 全绿日志已存档 |

### 第 1 轮 reviewer 验收（2026-11-16）

**判决：Accepted**（以下全部为 reviewer 亲自重跑；注入前后 `git status -uall` 快照逐行一致、组件树净、4 个交付文件 md5 回登记值）

- **门控重跑**：`apply_series.py --component chipyard` rc=0（`already applied (base+1, matches patches)`）；`make check-source-state` rc=0（chipyard `OK HEAD=0e0e37e clean`）；`make check-patch-tree` chipyard `23 patch(es)` / chipyard 断言 **0**（全局 rc=2，红=linux 27 + qemu 7 断言；在 master 主树同跑证 qemu 在 master 侧绿 ⇒ 归属并行任务 + 本分支落后 master，非本任务）；`make_patch.py chipyard` rc=0 `0 written, 23 unchanged`；证据脚本 `ONLY=B,C,D run.sh` **rc=0，PASS=56 FAIL=0**（含 37 镜像 before/after 的 `semi.out`/退出码/`cycle=` 全等）；L1 `make check` rc=2（同上归因，本任务 chipyard 段 0 problem、0 处 `VIOLATION: …m16-chipyard-002`）。
- **D1–D7 逐条**：D1 ✓ `generators/dadao-gewu/{build.sbt,src/main/scala/gewu/GewuFile.scala}`，内层 build.sbt 与 `dadao-wuming` 同形（ADR 指定形态）；D2 ✓ gewu 内 `wuming` **0** 次、`import` 仅 chisel3，根 `build.sbt` 三处接线齐（`freshProject("gewu",…).dependsOn(rocketchip)`、`baseProjects` 加 `gewu`、`wuming .dependsOn(rocketchip, gewu)`）；D3 ✓ `GewuFileIO` 现场 awk **19** 字段（读写地址/数据/许可、excp、escape、redirect、状态输出）；D4 ✓ 核内 `ip := gewu.io.vector`、`finish(gewu.io.redirect.target)`，gewu 源内无 `ip :=`，PC/flush 归 core；D5 ✓ `GewuParams/GewuCfxParams` 承载 cfx 集/帧归属/位宽/模式，gewu 内 `Seq.fill(`/mask 字面量/`cfx_hmon|cfx_power` 均 0 命中，机器常量只在 `WumingGewuParams`；D6 ✓ 文件头「Gewu ≡ cfx 寄存器堆（类比 Rocket `CSRFile`）」、寄存器仍 `cfx_*`、`spec/` 0 改动；D7 ✓ `git diff 983612df HEAD -- '*WumingDecoder*'` 为空，decoder `cfx` **35 行/42 处**与改前一致，核内 cfx 寄存器声明 0。
- **等价独立复现（含改前二进制自建）**：从 `983612df` 补丁态自建改前源树（反向应用新 3 补丁→应用旧 3 补丁→移除 gewu；核 1531 行、`build.sbt` 无 `gewu`）⇒ `make verilog`+`make` rc=0、`%Error`=0，sim `3efebd252c04888b175bfc7cac5ff77b`；该二进制与交付态 `idx-delivered` 在 6 个链例（trap/escape/cfx2rc/cfx2rd/fodiv/add）上 `semi.out`+`cycle=` **逐条全等**，与存档 `idx-before` 亦全等。存档 `sim-baseline` md5=`4e072a71…`＝m13-chipyard-003 登记值，且 `1b66e5c9..983612df` 间 chipyard 0 提交 ⇒ 存档基线可信。**独立重建 3 次**（03:52 / 04:03 / 04:12）sim md5 均 `bd5e75b3a64044b4cb69d20c298f080d`，每次还原后 6/6 回绿。
- **注入 5 路**（自设计、`cp`+md5 还原、逐轮真重编）：R1a `WumingCfxHa.hmon` 3→4 ⇒ **elaboration 红**（`requirement failed: UInt literal … is negative`）；R1b 3→2 ⇒ 4/4 例红（rc 0→141 不终止）；R2 `escapeTarget` 位切片 `(63,0)`→`(63,1)` ⇒ 4/4 红；R3 `io.writeOk := true.B` ⇒ **cfx2rc 的 CFXREG 负例 rc 242→20/21/22/23 红**（cfx2rd 读侧不变，符合 `readOk` 未注入的预期）；R4 `intrMask` 复位 `allOnes`→0 ⇒ `cfx2rd` rc 0→18 红（**掩码复位值有用例覆盖，无覆盖缺口**）。每轮还原后 md5 回 `c5e1f389…`/`9dcac763…`，末轮重建回 `bd5e75b3…`、树净。
- **越界**：`git diff 983612df HEAD` 仅 `.tao/tasks/chipyard/` + `components/chipyard/**`（9 文件）；`spec/`、`contracts/`、`tests/`、`tools/`、gem5/qemu/linux 组件 **0** 改动。
- **findings（不阻断，交 architect 收尾订正）**：① `components/chipyard/README.md` 写「29 镜像」而完成区为「37 镜像」（29 是首轮套件、37 是补入 cfx2rd 后的终版）；② 完成区「三次重建字节相同」未注明三次均在同一晚——reviewer 跨时段自建改前二进制得 `3efebd25…`（同源码、行为全等、字节不同），「字节可复现」应写明时段/环境口径；③ 证据存档 `work/bin/sim-after1`=`56dbeda2…`（早期源码态）与登记值不同且未在完成区说明。



## 完成区

**测试结果**：证据脚本 `run.sh` → `PASS=71 FAIL=1`（唯一红为 L1，见遗留问题）；`run.sh --inject` → `PASS=63 FAIL=0`（6 轮注入）；`run.sh --rebuild` 的确定性项绿；`run.sh --self-test` 的 FAIL 路径自检绿。等价：6 个 id / **37 镜像**（链例 6 + 故障例 31）逐例 `semi.out` 字节、退出码、`cycle=` 序列**全等**（0 差异）。

**修改文件**（8 项，与 `git status -uall` 逐项一致）：① 新增 `components/chipyard/patches/generators/dadao-gewu/build.sbt.patch`；② 新增 `components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch`；③ 重导 `components/chipyard/patches/build.sbt.patch`；④ 重导 `…/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch`；⑤ 重导同目录 `WumingParams.scala.patch`；⑥ `components/chipyard/series`（23 条）；⑦ `components/chipyard/README.md`（generator 节 + 补丁集一行）；⑧ `components/chipyard/changelog.md`（`## M16` 一条）；另本任务书。组件源 HEAD `0e0e37e`（base+1、clean）。

**验收结果**：
- 补丁/门控：`apply_series.py --component chipyard` rc=0（base+1、与补丁一致）；`check-source-state` chipyard `OK clean base+1`；`check-patch-tree` chipyard `23 patch(es)`、断言 0 问题；`make_patch.py chipyard` 二次 `0 written, 23 unchanged`（幂等）；`check-component-changelog` PASS。
- 静态（现场 grep）：`generators/dadao-gewu/` 内 `wuming` **0** 次；D5 模式（`Seq.fill(`、mask 字面量、地址基址、`cfx_hmon|cfx_power`、`runMode := <数>`、`= 3.U(6.W)`）全 **0**；`WumingDecoder.scala` 的 `cfx` 命中 **35 行 / 42 处**（== 改前存档）；核内 cfx 寄存器声明 **0**；`GewuFileIO` 19 字段。
- 构建：`make verilog CONFIG=WumingTinyConfig -j32` 与 `make CONFIG=WumingTinyConfig -j32` 均 rc=0、日志 `%Error`=0；sim md5 **`bd5e75b3a64044b4cb69d20c298f080d`**（旧 `4e072a71…` 作废）；`make clean-sim` 后从零重建 + 注入还原后重建，三次 md5 相同（确定性）；生成物含 `module GewuFile` 与 `io_redirect_target`。
- 等价（改前二进制 vs 改后，同一批 ELF）：`trap_ciii_cfx` 2821 / `escape_ciii_cfx` 3068 / `cfx2rc_crrr_cfx` 3139 / `cfx2rd_crrr_cfx` 3743 / `fodiv_orrr_rf` 4475 / `add.so_rrrr_rd` 2962 条 `cycle=` 逐条相同；链例输出 md5 与退出码全等（如 `escape` `cff360ff…`、`cfx2rd` `f716c583…`）；31 个故障例 rc 全等（`0xF2`/`0xF8`）。
- 注入（`cp`+md5 还原 + 重建，6 轮）：① `cfxVector` 写回 +4 ⇒ `cfx2rc_crrr_cfx` 链例红（rc 0→8）；② `escape` 去掉「当前 cfx」判据 ⇒ `escape_ciii_cfx` 链例红（不终止）；③ `GewuParams.monitor` 0→1（帧归属）⇒ **29/29** 红；④ `GewuParams.runModeReset` 3→1 ⇒ `cfx2rc` 红（cg3 行变 CFXREG，输出字节变）；⑤ `redirectTarget` 接常量 0 ⇒ **29/29** 红；⑥ `escape` 去掉「帧有效」判据 ⇒ 0/37（不可观测，见遗留）。每轮还原后 md5 回登记值、37 镜像 0 差异。
- 越界：`spec/`、`contracts/`、`tests/`、`tools/`、gem5/qemu 组件 **0** 改动（脚本现场统计）。

**新发现/坑**：① cfx 搬进独立项目后，异常入口落点**不能**接「按事件选的 redirect mux」——那会把 `finish` 的 IALIGN 判据接成组合环，且 `escape` 目标非法那拍会跳错地址（`escape_ciii_cfx` 点 9 立刻抓到）；② `gewu` 项目须 `.settings(chiselSettings)` 才有 chisel 插件（`IO(new GewuFileIO(params))` 的 cloneType），`dependsOn(rocketchip)` 只带库不带插件；③ 注入到「向量/帧」这类寄存器会让镜像不终止，证据脚本必须给每镜像 `timeout` + 日志上限，否则 trace 能写到 GB 级；④ D2 的「0 次 `wuming`」也约束注释与 inert `build.sbt` 的文字。

**遗留问题**：L1 `make check` rc=2 —— 唯一红点在 `check-patch-tree` 的 **qemu** 段（并行会话正在重导 qemu 补丁，7 条 assertion）；同一交付树早前一轮 L1 全绿日志已存运行期证据目录，且 L1 运行内 chipyard 段为 `23 patch(es)` / 0 问题、无 violation 指向本任务。`escape` 的「帧有效」半条判据在本 profile 不可观测（`excp_cause_id` 无清零路径、`cg5 rc2` 为 HW-RO，`escape_ciii_cfx.S` 自记 GAP ③）⇒ 该半条判据无行为覆盖（另半条「当前 cfx」判据已由注入 ② 证明可达红）。
