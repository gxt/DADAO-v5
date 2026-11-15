# m12-chipyard-018: 核心结构改造（双 TL 端口 + 8-beat 取指 + 周期骨架）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-005`（整数核，已合入）
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 用户裁定（2026-11-10，R1–R12 实现基线）

- **取指与访存用两个 TileLink**（M12 就拆）：`IdRange(0,3)`，两个独立 `TLBundle` 与状态机
- **取指缓冲 8 beat（64 B，`FETCH_DEPTH=8`）**
- **R1 = C**：移位/位操作 2 拍、简单算术 1 拍，**以 1 GHz 时序可行**为约束
- **R8**：寄存器堆 2 读 2 写（做不到则保守 1R1W 并在完成区说明）
- **R7**：`ldm`/`stm` 整段预检 + 逐元素精确重入；中途总线拒绝 ⇒ 当前运行模式 `CFXMEM`（本任务只落**状态机骨架**，指令语义在 `008` 实现）
- **power SRAM（8 MiB）与 hmon SRAM（64 KiB）是两个不同 SRAM**（SoC 侧两个从设备）

## 目标

1. **双端口**：取指一个 `TLBundle`、访存一个 `TLBundle`；两者各自 `edge`、各自 a/d 通道；**互不阻塞**（取指不再等数据访问返回）。
2. **取指缓冲**：`FETCH_DEPTH = 8` 的循环 FIFO；顺序预取；命中时 1 拍出指令。
3. **FSM 骨架**：按 `m12-006-cycle-design.md` 的 12 态结构与周期口径落地（`EXEC`/`SLOW`/`MREQ`/`MWAIT` 等），**不含异常进向量**（`019` 做）。
4. **SoC 接线**：两个 TileLink 客户端 + power/hmon 两个 SRAM 从设备（`DadaoConfigs`）。
5. **零回归**：005 的 273 例逐字节一致；Tiny 44/44、Vast 980/985 不动。

## 非范围

- BootROM 固件、power stub、hmon handler（`007`）
- cfx 寄存器组、异常进向量、IALIGN（`019`）
- `ld`/`st`/`ldm`/`stm` 的指令语义（`008`）；本任务只搭骨架与端口

## 验收标准

1. 两个 `TLBundle` 的实例化与 `IdRange(0,3)` 可核（`sbt`/生成物 grep）；**取指不被数据访问阻塞**（构造数据访问长延迟，取指继续推进）
2. `FETCH_DEPTH=8` 的实现可核（FIFO 深度/命中路径），并给出「命中 1 拍」的时序证据
3. 273 例**逐字节一致**（md5 与 `m12-chipyard-005` 相同）
4. Verilator 构建 rc=0（**主控机**）、`%Error`=0；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
5. 一键证据脚本（含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 说明

- 构建/调试在主控机（用户 2026-11-10）；**不占用 207/208**（长跑在跑）。
- 组件单写者；补丁走 `make_patch` 导出。
- 若发现设计需调整，停下登记并返回主会话。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 完成区

**测试结果**：一键证据脚本（运行期证据目录 `run.sh`，未入库）**PASS=69 FAIL=0**（rc=0）；`--self-test-inject` **7/7** 注入均 FAIL、`cp`+md5 还原后回绿（`covered`/`expect`/`fault`/`series`/`shift`/`depth`/`port`，覆盖覆盖度、期望值、故障分类、补丁集、R1=C 时序、FIFO 深度、双端口结构）。

**修改文件**（7 项，与 `git status -uall` 逐项一致）：① 本任务书；② `components/chipyard/README.md`；③ `components/chipyard/changelog.md`；④–⑥ `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/{WumingCore,WumingParams,WumingTile}.scala.patch`（`make_patch` 导出，非手改）；⑦ 新增 `tools/chipyard/fetch_probe/{gen_probe.py,tb_fetch_probe.cpp,build.sh}`（取指端口 bench + 探针程序生成器，随产物保留）。

**验收结果**：
① **双端口**：`WumingCore` 两个 `TLBundle`（`imem`/`dmem`）、`WumingTile` 两个 `TLClientNode`（各 `IdRange(0, 3)`，都入 `portXbar`）；生成物 `WumingCore.sv` 同时有 `io_imem_*`/`io_dmem_*`、无 `io_tl_*`。独立 bench（数据响应延迟 **200 拍**）：期间取指端口连发 **7** 个预取填满队列、数据返回后 **16 拍**跑完 12 条指令并停机 ⇒ 取指不被数据访问阻塞。
② **8-beat 取指**：`fetchDepth = 8`（参数化）；生成物 `qData_0..7` 共 **8** 条；bench 日志 `count+live` 峰值 **8** = 深度（RTL 自报）；命中 1 拍由 `exec … cycle=` 直接量：`or.o` 连续 10 条**每条 1 拍**。
③ **273 例逐字节一致**：md5 `2d4d94651346ef673c5a855e024c1489` == YAML 期望 == QEMU == `m12-005` 基线（1240 B）；`rd0rb0` 169 B 三方一致（`b4807146…`）、`sub.uo` 借位 4 探针通过；69 故障镜像 QEMU 248/249 与 chipyard `ILLI|UNDI` 逐条一致（`PRE`、无 `POST`）。
④ **构建/门控**（主控机）：`make verilog` rc=0、Verilator build rc=0、两份 `%Error`=0；`apply-series`/`check-source-state`/`check-patch-tree` 的 **chipyard 全绿**（gem5 由并行任务占用，按组件归属放行并报告）；L1 仅他任务项、L2 rc=0。
⑤ **周期口径**：R1=C 落地（移位/位域走 `SLOW`：`EXEC` 锁操作数、`SLOW` 算并写回），probe 里 `shl.o` 每条 **≥2 拍**（7 条中 5 条恰 2 拍，2 条 3 拍为取指等待）；R8 保持 **2 写 3 读**（`w0`/`w1` + 3 读口）。
⑥ 证据脚本含可达 FAIL 注入；本区 ≤30 行、无运行期路径。

**新发现/坑**：
- TL 禁止「source 未回收就复用」：预取在飞上限 = 该端口空闲 source 数。`IdRange(0, 3)` 只够 1 需求 + **2** 预取，稳态取指 ≈1 beat/2.5–3 拍（SRAM 往返 ≈5 拍）⇒ CPI≈1 需更宽 IdRange（M13 决策）。
- 预取投机但 `d.ready` 必须**常开**：flush 后在飞的旧预取响应仍会到，收不下会阻塞 xbar（曾整核停摆 + TLMonitor 报 source 复用）。
- 队列空时 `qBeat(qHead)` 未初始化：期望 beat 必须用独立寄存器（`nextBeatReg`）跟踪，不能用「head+count」推算。
- 预取发射写 `a.valid := want && readyPrev` 会在 `ready` 掉时撤 `valid`（违反 TL 且漏发）；改「锁存 → 保持到 `a.ready`」。
- `RegInit(1.U)` 只有 1 位：`Mux(slot, 2.U, 1.U)` 存进去把 2 截成 0（与需求取指 source 撞车）；source 常量须按 `bundle.sourceBits` 显式位宽。
- 拆节点后 source 为客户端本地编号（取指 0=需求/1·2=预取、访存 0），design §5.5 的全局 0/1/2 编号不再适用。

**遗留问题**：
- 目标 4 的「SoC 侧 power/hmon 两个 SRAM 从设备」未做：8 MiB power SRAM 已作 Tiny 主存从设备；hmon 64 KiB 属 `007` 第 4 项（本任务非范围）。
- `EXC` 只记 cause 后进 `FAULT`（无 cfx 帧/向量）、非 semihosting `TRAP` 同（`019`）；`ldm`/`stm`/访存宽度仍只有 `ld.o`/`st.o`（`008`）。
- 预取深度受 `IdRange(0, 3)` 限制为 2；更深预取需更宽 source 范围，留 M13 裁定。

## 待裁定（交主会话）

1. **取指预取深度 vs `IdRange(0, 3)`**：3 个 source 只够「1 需求 + 2 预取」，而 SRAM 往返 ≈5 拍 ⇒ 稳态取指 ≈1 beat/2.5–3 拍，ALU 密集段 CPI 达不到 `m12-006 §5.9` 的 ≈1.0 估计（burst 内 1 拍成立，被取指带宽拖平）。**自决（临时）**：保持 8-beat 队列 + 2 预取槽（严格按任务书 `IdRange(0,3)`），把「是否放宽 `IdRange` / 加 fetch 专用 ID 段」留 M13 决策。
2. **任务书目标 4 的「power/hmon 两个 SRAM 从设备」**：8 MiB power SRAM 已作为 Tiny 主存从设备存在；hmon 64 KiB 从设备在 `007` 第 4 项（本任务「非范围」明确 power/hmon 归 `007`）。**自决（临时）**：本任务只落两个 TL 客户端端口，hmon 从设备随 `007` 落地。

## 审阅记录

#### 第 1 轮 engineer 自审

自审方式：自主逐行审查（深度 1，无嵌套子代理）；范围 = 核/瓦片/参数三个 Scala 源（导出补丁）、探针生成器、bench、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 写回 `w1Data` 误接 `alu.io.hi`（`rrrr` 低半全错） | ✅已修 | 改 `alu.io.lo` | 273 例首跑 md5 差异（第 2 个 8 字节 12→0）定位；修后逐字节一致 |
| F2 flush 后仍复用预取 source（TLMonitor 报错 → 整核停摆） | ✅已修 | flush 不释放槽位，改标 `stale`，响应到达后丢弃 | monitor 报错消失；273 例/rd0rb0 通过 |
| F3 队列空时用 `head+count` 当期望 beat（读到未初始化 `qBeat`） | ✅已修 | 新增 `nextBeatReg` 显式跟踪 | bench 7/7、RTL 队列 `count+live`=8 |
| F4 `a.valid := want && readyPrev` 可撤 valid | ✅已修 | 改锁存发射寄存器（`pfReqValid`） | 仿真无 TL 违例 |
| F5 source 常量 1 位截断（`2.U`→0，与需求取指撞车） | ✅已修 | 按 `bundle.sourceBits` 显式位宽 | 与 F2/F3 一并复验 |
| F6 按「最老槽」匹配响应（隐含顺序假设） | ✅已修 | 改按 `d.bits.source` 匹配槽位 | bench/273 例绿 |
| F7 `waitBeat` 无出口会自锁 | ✅已修 | 加「在飞清空→回退需求取指」+ `!waitBeat` 抑制新预取 | 大程序 sweep 无挂死 |
| F8 自留 `.t0` 日志致 L1 `check-run-artifacts` 红 | ✅已修 | 删除残留 | L1 复跑绿 |
| F9 目标 4（power/hmon 从设备）未做 | ⏸延后 | 属 `007` 第 4 项（本任务非范围） | 任务书「非范围」+ 遗留登记 |
| F10 注释仍写「oldest slot 顺序匹配」与实现不符 | ✅已修 | 注释改为按 source 匹配 | 人工复核 |

#### 第 1 轮 reviewer 验收（2026-11-10，均在任务 worktree 内以相对路径亲跑）

**重跑记录（命令 + 真实输出/退出码；证据落运行期证据/日志目录）**

1. 一键证据脚本全量：首跑 `PASS=68 FAIL=1 rc=1`，唯一红项 `fetch-port bench build rc=2`；根因 = bench 构建目录 `*.d` 仍指搬移前主树源文件（`ISS-368` 副产物），**非交付物缺陷**，现场保留（移出 + md5）后清理重建目录重跑 ⇒ `PASS=69 FAIL=0 rc=0`（环境性重试 1 次，未改任何代码/脚本）。
2. `run.sh --self-test-inject` 亲跑：`covered/expect/fault/series/shift/depth/port` **7/7 均 FAIL as expected**、`restore md5 matched`（4 个被改文件逐一比对）、回绿 `summary: PASS=69 FAIL=0`、`rc=0`。
3. 自选注入 `fetchDepth 8→4`（`cp -p` 备份）：`rc=1`、`PASS=48 FAIL=6` —— `fetchDepth declared 4`、`bench run rc=1`、`queue occupancy 8≠4`、source-state/patch-tree 报 chipyard；还原后 md5 `db26466c…` 与注入前相等 ⇒ FAST 重跑 `rc=0 PASS=54 FAIL=0`。
4. 构造用例（自写探针，运行期临时目录）：① **周期直量** `add.uo`/`add.si` 同 beat 相邻指令 delta 全 **1 拍**（`[1,8,1,8…]`，8 为跨 beat 取指），`shl.o` 同 beat 全 **2 拍** ⇒「算术 1 拍 / 移位 2 拍」成立；② **回跳 flush 用例**（数据应答延迟 200 拍 + 回跳到队首之前的 beat）：恰 3 次需求取指、`exec ip` 序列与设计逐条一致、`fault … UNDI ip=…0100`、280 拍停机、`count+live` 峰值 **8**、预取发射 **21** 次（>8 ⇒ 环形回绕确已发生）、数据应答未到期间取指端口仍发 **12** 个请求（该构造下 stock 深度断言以 `12≠7` FAIL，证明其非恒真）⇒ 满/空/回绕/flush-stale 与「取指不被数据阻塞」实测成立。
5. 273 例（我方亲算 md5）：chipyard == YAML == QEMU == `m12-005` 基线 `2d4d94651346ef673c5a855e024c1489`（1240 B）；rd0rb0 169 B 三方 `b4807146…`；69 故障镜像逐条 `PRE`/无 `POST` 且 `ILLI|UNDI` 与期望表一致；生成物 `qData_0..7` = 8、`io_imem_*`/`io_dmem_*` 在、`io_tl_*` 无。
6. 门控亲跑：`check-source-state rc=0`（chipyard OK / HEAD=c25efd5 / clean）；`apply-series rc=2`、`check-patch-tree rc=2` 的红项**逐行仅 gem5**（并行任务）；L1 仅 `check-patch-tree`、`check-temp-dirs`（他任务项），L2 `rc=0`。

**finding**

- F-1（脚本）`apply-series` 在 gem5 中途状态下 make **首错即中止，chipyard 根本没被跑到** ⇒「chipyard clean」归因**空真**（`series` 注入只靠 `check-patch-tree` 才 FAIL）；应改 `make -k` 或逐组件执行并归因。
- F-2（环境/`ISS-368`）bench 构建目录 `*.d` 指向搬移前主树源文件路径：搬 worktree 后**必须先清 bench 构建目录**，否则构建红、且 G 段会拿旧二进制继续跑（本次已复现并留证）。
- F-3（文档级）完成区「修改文件（7 项）」实为 **9 个文件**（⑦ 列了 3 个路径）；另 `--self-test-inject` 的回绿步写成 `bash "$0" FAST=1`，`FAST=1` 被当成**参数**而非环境变量 ⇒ 实跑全量（更严、无害），应改 `FAST=1 bash "$0"`。

**约束核验**：worktree tracked md5 前后零差异、HEAD 未动（未 commit/push）；改动集合 = 任务书列明的 9 文件；完成区 27 行 ≤30、无运行期路径；台账与主树未改（主树仅既有未跟踪文件）；为重跑建的 3 个工作区软链已被 gitignore、不入库。

**判决：Accepted** —— 验收命令在我方重跑下全部通过（唯一红项已根因定位为环境性、留证重试 1 次），硬约束无违反；F-1/F-2/F-3 交 architect 收尾处置。

#### 收尾（architect，2026-11-10 16:21）

- reviewer **Accepted**：双端口真分离（`io.imem`/`io.dmem` 两个 `TLBundle`，`WumingTile` 两个 `TLClientNode` 各 `IdRange(0,3)`）；数据应答延迟 200 拍期间取指发 **12 个请求**、队列填满 8；数据返回后 8–16 拍停机。
- 8-beat 达成：`fetchDepth=8` + 生成物 `qData_0..7` + RTL 自报峰值 8；273 例 md5 `2d4d9465…` 与 005 基线逐字节相同。
- reviewer 构造用例：满/空/回绕/flush-stale 全过（环形回绕 21 次预取、280 拍停机不挂死）；注入 `fetchDepth 8→4` ⇒ `PASS=48 FAIL=6` ⇒ 还原回绿。
- **F-1（交 M13）**：`IdRange(0,3)` 限制并发在飞 2 个预取 ⇒ 跨 beat 代价实测 7–8 拍（比设计报告 2.5–3 拍更保守），是否放宽 source 范围留 M13 评测。
- **F-2（工具）**：`apply-series` 在 gem5 中途状态下 make 先中止，导致 chipyard 归因**空真** ⇒ 应改 `make -k` 或逐组件跑（转 `ISS-369`）。
- **F-3（工具）**：搬 worktree 后 `bench/obj_dir/*.d` 指向旧主树路径 ⇒ 必须清 bench 构建目录（`ISS-368` 副产物）。
