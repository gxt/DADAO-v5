# m16-chipyard-002: cfx 独立为 `dadao-gewu` generator（chipyard）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`ADR-0053`（Accepted，D1–D7）；`m12-chipyard-001`（补丁集接入与骨架）；`m13-chipyard-003`（当前基线，sim md5 `4e072a711afdca8a36788f9a9958e896`）
**可并行分片**：否（chipyard 组件单写者 + 同一 sim 构建）
**预估**：3–5 h（增量构建约 2 min/次、全量约 9 min；含 4 路注入重建）
**档位**：大改（RTL 结构重构 + 组件重建；复核需独立重跑 + ≥4 路注入）
**状态**：待开始

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

（待填）
