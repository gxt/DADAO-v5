# ADR-0053: chipyard 侧 cfx 独立为 `dadao-gewu` generator

**状态**：Candidate
**日期**：2026-11-15
**关联**：ADR-0045（cfx 权限）、ADR-0046（cfx 寄存器 profile）、`m16-chipyard-001`（周期模型收口复测）、`spec/Machine-v5`、`spec/DADAO-12/13`

## Context（背景）

cfx 是**机器级控制面**（寄存器堆 + 判权 + 异常帧 + 向量 + escape/power/hmon），不是某个流水专用的部件。当前三平台分层不一致：

- **chipyard**：cfx **内联**在 `generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala`（1,531 行）；`cfxTrapMask`/`cfxVector`/`cfxCause*` 等寄存器声明在 line 188–220 一带，判权/分发在 line 274–294，**152 行**与 `cfx|CFX|cg[0-9]` 相关、散布 line 30–1522，与流水控制交织；`WumingCore` 已实例化 8 个子模块（`rf`/`dec`/`alu`/`fpClassify`/`fpConvert`/`fpArith`/`fpSlow`/`fpMisc`），**cfx 是唯一没有独立模块的部件**；
- **gem5**：已分开（`src/arch/dadao/tiny_cfx.{cc,hh}` + `node_cfx.{cc,hh}`）；
- **QEMU**：内联在 `target/dadao/helper.c`（411 处）/`cpu.c`（77 处）。

用户 2026-11-15 裁定方向：**在 `generators/` 下用 `dadao-gewu` 承载 cfx 相关功能模块，`dadao-wuming` 及后续设计都复用它**（格物致知，故模块名 `Gewu`）。

chipyard 惯例支持该形态：`generators/` 31 个目录中除核以外还有多个**纯库型 generator**（`hardfloat` 浮点库 `build.sbt:124`、`testchipip` 外设库、`diplomacy`、`rocc-acc-utils`、`rocket-chip-blocks`、`rocket-chip-inclusive-cache`），即"一个功能设施一个 generator"是既有做法，不是新发明。

## Decision（决策）

- **D1 装箱形态**：cfx 独立成 generator `generators/dadao-gewu/`（**in-tree 补丁树**，形态照 `dadao-wuming`：根 `build.sbt` 为准、generator 内 `build.sbt` 只作文档），sbt 项目名 `gewu`，scala 包 `gewu`，模块文件 `src/main/scala/gewu/GewuFile.scala`（`class GewuFileIO` + `class GewuFile extends Module`）。
- **D2 依赖方向单向**：`gewu` **只**依赖 `rocketchip`（需要 `CoreBundle`/`Parameters`/Diplomacy 类型），**禁止**依赖 `wuming` 或任何具体核；`wuming` 与后续核一律 `.dependsOn(gewu)`。
- **D3 IO 契约显式**：`GewuFileIO` 覆盖 cfx 读/写（`cg`/`rc`/`ha`/数据/写使能/匹配）、异常入口（cause id/ip/info、vector、prev run mode）、异常帧存在与清除、运行模式、IP、中断 mask、`escape`、`power`、`hmon` 与重定向请求；**输入只接受架构级事件**（"提交一条 cfx 写"/"进入异常"/"escape 返回"），不得依赖某条流水的内部信号。
- **D4 重定向责任归 core**：`Gewu` 只输出 `redirectReq`/`redirectTarget`（附 cause 信息），**PC 与 flush 一律由 core 驱动**（现状 `cfxVector(0)` 直驱 `ip :=` / `continueAt(...)`，`WumingCore.scala:936–937`，需改为端口）。
- **D5 参数化**：hart 数、帧数、实现的 cfx 集与位宽走 `Parameters`（现状硬编码 `Seq.fill(2)` 等），新增 `GewuParams` 由调用核注入；`gewu` 源码内不得出现具体核的常量。
- **D6 术语单一**：模块/文件名 `Gewu`，**寄存器名保持 `cfx_*`**（与 `spec/Machine-v5`、`ADR-0046` 一致）；`GewuFile.scala` 文件头写明「Gewu ≡ cfx 寄存器堆（类比 Rocket `CSRFile`）」。**spec 不改名**——规范描述的是 cfx 寄存器，不是 Gewu。
- **D7 搬迁范围**：只搬 cfx 的**状态与判权/分发**（含 trap/escape/power/hmon 相关）；**decoder 的 cfx 指令类解码留在 `wuming`**（`WumingDecoder.scala` 现有 37 处），作为 `Gewu` 的输入信号，不搬。

## Rationale（理由）

- **为什么独立成 generator**：cfx 要被"后续设计复用"，跨核复用必须有物理边界；chipyard 的 sbt 项目边界天然强制 public API（跨项目只能走公开类型），比"同项目内自觉"更硬。`hardfloat` 已验证这种"设施即 generator"的形态可行。
- **为什么依赖不能反向**：cfx 若 `import wuming.*`，第二个核就接不上，"复用"是假的（这是本次拆分最容易做错的一点）。
- **为什么重定向归 core**：异常入口与 `escape` 会同时改动 cfx 帧与 PC；若 `Gewu` 自驱 PC，会与 core 的 flush/重定向产生组合环或双驱动。
- **为什么 decoder 不搬**：cfx 指令类解码属指令集解码职责（每个核的解码器不同），搬进 `Gewu` 会把共享设施绑到某一种解码器上。

## Consequences（影响）

- `build.sbt` 三处接线（补丁内）：`lazy val gewu = freshProject("gewu", file("generators/dadao-gewu")).dependsOn(rocketchip)`、`baseProjects` 加入 `gewu`、`wuming` 改为 `.dependsOn(rocketchip, gewu)`；
- 新增补丁树 `components/chipyard/patches/generators/dadao-gewu/**`，须过 `check-patch-tree`；
- **sim md5 变化** ⇒ 单二进制基线需重做（现 `4e072a711afdca8a36788f9a9958e896` 作废），cfx 相关周期行（trap/escape/power）需重新实测；与他任务的先后不作规定，只要不冲突；
- `WumingTile`/`WumingCore` 的参数透传多一层（hart 数、profile），用 `Parameters` 隐式传递避免样板代码；
- `docs/core-wuming-cycle-model.md` 的寄存器命名**不变**（仍 `cfx_*`），文档无需改名；
- 后续核复用 cfx 的成本从"复制 152 行 + 隐式耦合"降为"`dependsOn(gewu)` + 接端口"。

## 状态说明

2026-11-15 由主会话起草为 `Candidate`；**D1–D7 须逐条与用户确认**，确认后置 `Accepted` 并立实施任务（不得先动 RTL）。
