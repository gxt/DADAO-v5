# M13 回顾（三平台差分：qemu / gem5 / chipyard 逐例对照 + 浮点 IEEE 对齐）

> **状态**：M13 已于 2026-11-15 达成并归档。本文件是里程碑回顾（历史摘要），不是现行判据；现行规则见 `spec/`、`.tao/contracts/`、`docs/`。

## 1 里程碑目标

M13 的定位（用户 2026-11-09）是**三平台的多方差分对比**——不再只问「某实现能不能跑」，而是逐例问「三个实现是否给出同一结果」：

- **差分基础设施**：差分产物归属规则 + 三平台矩阵生成器（chipyard 列未就绪时记 `N/A` 而不是跳过）；
- **指令语义全覆盖**：非 cfx 整数/访存全量、FP 全量（含舍入×标志矩阵）、cfx 与 misc 族；
- **浮点按 IEEE 754-2019 对齐**：把「三家各写各的」改成「逐条对条文 + 三实现实测」；
- **收口判据**：矩阵冻结（镜像级逐例一致 + 字节级结果流断言 + 记 `input commit`），差异必须**归因**到具体实现，不留「未归因」。

> 平台**实现**（chipyard RTL 新指令、gem5/QEMU Tiny 支持）在 M12 及以前完成；M13 消费它们做差分，并顺带补齐差分暴露的实现缺陷。

## 2 主要交付

- **rf2rf 批（一条指令改五处，M13 最大单体变更）**：`m13-spec-010` 删 `ft2ft`/`fo2fo`、加 `rf2rf`（OPC-octa/opx `111-100`，id 264→263、单精写宽归位）⇒ 四实现同批跟进：`m13-llvm-001`（.td/AsmParser/Printer/copyPhysReg，lit 167/167、矩阵 accept 263/0）、`m13-qemu-016`（decode 重生成 263、trans 整 64 位 + 六类非法 ILLI）、`m13-gem5-015`（解码表 263、`CopyNoRf0` 零读写 ILLI、周期表行 71 改指 `1+N`）、`m13-chipyard-003`（`blockCopy forbidRf0Dst`、六类非法译码期判定；sim md5 `4e072a71…`、三平台 7/7）⇒ 向量 `m13-testcases-047`（载体 265→264、镜像 901→896）。
- **伪指令体系迁章**：`m13-spec-011` 把伪指令并入 `SimRISC-00 §5`（§5.1/5.2/5.3），`SimRISC-03` 按 rd/rb/rf **拆三章**，`set.ft` 写宽对照表 + 锁/引用同步；配套 7 个专用载体（`m13-testcases-048`，`00-isa-design`，113 点，rb 四 wyde + 64 位校验，三平台一致）。
- **原子三层**：① 向量层 `m13-testcases-028`（`12-misc` 原子 24 id，66/66 三平台、408 点）+ `m13-testcases-037`（`sc` 保留粒度正式向量，点 17–21）；② 合成序层 `m13-testcases-049`（`atomic_rmw.S`，13 点：fetch_* / exchange / CAS 两路 + 失败不写 + 重试重读）；③ 执行型端到端 `m13-testcases-050`（`atomics_e2e` 20 点真跑 guest）+ 五探针退役 + **多 hart GAP 节**（`ISS-440`/`ISS-443` 明列不覆盖）。
- **`set.fo` 最小展开**：`m13-llvm-002` 把 `set.fo rf, imm64` 从「固定 4 条」改为**最小指令数**（`rd2rf rd0` + 非零 wyde，`k=4` 才退回 4 条），lit 五形态。
- **差分与矩阵**：`m13-integ-001`（差分产物归属 + 矩阵生成器，165 行）、`m13-integ-002`（FP 66 条 / 232 镜像、差异 0；舍入×标志 4×6 = 24 格）、`m13-integ-003`（整数/访存 194 载体 / 629 镜像、差异 0）、`m13-integ-004`（riscv-tests 移植 114 条、可移植 35 + 474 例一致）、`m13-integ-009`（FP-IEEE 全面审计 66 条：一致 48 / 未规定 14 / 偏离 4）。
- **收口冻结**：`m13-integ-005` 矩阵 `docs/TestReports/M13-三平台差分-矩阵.md` —— **整数 637 + FP 227 = 864 镜像 864/864 `AGREE_PASS`，平台差异 0、未归因 0**；三平台 `.out` 逐字节断言（长度 = 8×点数）；产物记 `input commit` 与引擎 md5；两批独立重跑逐镜像 rc + 流 md5 全等。
- **测试资产重构**：YAML 全退役（`m13-testcases-043`：27 册/1315 例删除）、`.S` 入门控（`030`）、入索引双向断言（`041`）、每 id ≤127 字段域门控（`042`）、批量测试池 + 分通道判据（`005`/`006`）、长尾口径（`001`/`002`/`003`/`009`）。
- **平台实现缺口修复（差分暴露）**：gem5 SE 页表故障与句柄越界（`gem5-003`/`004`）、gem5 `ext.*` `hd` 取 `rdHD[5:0]`（`gem5-012` + `spec-008`）、`ldm` 地址寄存器重叠 ILLI（`spec-005` + `qemu-006`/`gem5-008`）、quiet 比较 sNaN 置 `NV` 与 `rootn(±0,2)⇒+0`（`spec-007` + `qemu-004`/`gem5-011` + 向量 `testcases-032`）、`fo2ft` 溢出按 IEEE（`spec-002` + `qemu-005`/`gem5-007` + 向量 `testcases-011`）、FMA 溢出按 IEEE（`spec-006` + `qemu-008`/`gem5-009`）、`ra0` 写口丢弃 SBZ（`qemu-012`/`gem5-014`）、`ld.t` 写 `rf0` 只放行 `[4:0]`（`qemu-015`/`gem5-013`）、单精写入宽度（`chipyard-001`/`qemu-013`）、`sc` 保留粒度严格化（`chipyard-002`/`qemu-014`）。
- **基础设施**：工具缺陷修复 + 核验册机制删除（`m13-infra-001`）、四台新节点引导（`m13-infra-002`）、**写者护栏**（`m13-infra-003`：写者登记 + 读方 fail-closed + md5 前后比，27/27）。

## 3 关键缺陷与修复

| 缺陷 | 根因与修复 |
|---|---|
| gem5 SE 句柄越界（`m13-gem5-003`） | 边界判断写成 `handle > files.size()`（应 `>=`）⇒ 未 `SYS_OPEN` 时读越界 segfault；同册修非对齐 `.bss` 装载的 fatal |
| gem5 SE 页表故障不投递 guest（`m13-gem5-004`） | `lemon` 全量 panic；修故障投递 + 脏页/帧回收后 0 panic |
| gem5 `ext.*` 越界即 ILLI（`gem5-012`） | 误把 `hd` 越界当非法；按 spec 改 `hd = rdHD[5:0]`（`m13-spec-008` 同笔），B3 断言 +70 |
| quiet 比较遇 sNaN 不置 `NV`（`qemu-004`/`gem5-011`） | 缺 sNaN 路径；改前差分恰 4 例，改后对齐 IEEE |
| `fo2ft` 溢出恒 ±Inf（`qemu-005`/`gem5-007`） | 未按舍入模式；轻微溢出只置 NX（`m13-testcases-011` 31 例 + 496 B 逐字节） |
| `ldm` 地址寄存器落入传送范围未报 ILLI（`qemu-006`/`gem5-008`） | 三平台补判定；`stm` 允许、RA/RF 不适用（`m13-spec-005` 8 条引用同步） |
| `ra0`/`ld.t rf0` SBZ 未丢弃（`qemu-012`/`gem5-014`/`015`/`013`） | 写口掩码 / `[4:0]` 放行；51 点三平台一致；`ISS-426` 的 `ld.o ra0` 半边留活 |
| `sc` 保留粒度按整字值比较（`chipyard-002`/`qemu-014`） | 与 `spec/SimRISC-12 §1` 冲突；改精确地址+宽度（改前 8 点探针 4 红 → 改后全绿）；多 hart/异常清保留仍缺（`ISS-440`/`ISS-443`） |
| `trap cfx_power` 三平台不一致（`m13-testcases-027`） | chipyard 报 ILLI、另两平台进 power 向量 ⇒ 登记 `ISS-433`，本轮不定夺 |

## 4 判据演进

- **差分产物归属 + 矩阵生成器**（`m13-integ-001`）：差分报告与 JSON 归 `docs/TestReports/` + `refs/`，生成器入仓可重派生；chipyard 列未就绪记 `N/A`（不是删行）。
- **矩阵必须记 `input commit`**（`m13-integ-005`）：三份产物与 JSON 均记被测 commit；换 commit 复算须显式传同一 sha，否则 `--check` 如实报不一致。
- **字节级断言**（`m13-integ-005`）：`AGREE_PASS` 之外，三平台 `.out` 逐字节相等 + 长度 = 8×点数；注入「只翻 1 字节、rc 不变」实测判红——防「状态一致但结果流不同」。
- **超时口径**（`m13-testcases-001`/`003`/`009`）：长尾统一 `timeout(3600 s)` / 复核 7200 s；`blocked` 只留构建/环境缺口，超时单列、不计能力缺口。
- **脚本入仓判据 = 会不会再跑**（用户 2026-11-15 改）：共享工具入 `tools/<module>/` 并在模块 README 登记一行；批次一次性编排（`run.sh`/`collect.sh`/注入脚本）不入仓，留运行期证据目录。
- **复核分档**（用户 2026-11-15）：小改 = diff + 1 路注入 + 受影响的 1–2 个门控（目标 ≤15 min）；中改 ≥2 路注入；大改/组件改 ≥4 路 + 独立重算——防「小改套大改模板」。
- **派单顺序 + 台账时间戳**（用户 2026-11-15）：先提交任务书再从该 commit 建 worktree（`check-milestones-fresh` R2 机械校验）；派单/完成时间只取 `date`/`git log` 输出。
- **写者护栏**（`m13-infra-003`）：共享安装根/组件树并发时，写者登记 + 读方 md5 前后比 fail-closed（`ISS-373` 的机械解）。

## 5 遗留（不阻塞达成）

- **平台语义分歧待裁定**（MEMORY 待裁定 ⑤）：`ISS-433`（`trap cfx_power`：chipyard ILLI vs 另两平台 power 向量）、`ISS-440`（另一 hart 同址写清保留：三平台均无实现路径）、`ISS-443`（异常/中断进入清保留：三平台均不实现，P1）——三件同族，建议合批并评估是否立 ADR。
- **保留粒度**：`ISS-435`（`sc` 整字 vs 精确地址+宽度在 qemu/chipyard 的历史实现差异）随 `chipyard-002`/`qemu-014` 收窄，剩余半边见 `ISS-440`。
- **门控缺口**：`ISS-447`（`check-spec-refs` 对标题型引用不校验章号，改 §号仍 rc=0）、`ISS-448`（`WumingDecoder.rfRows[2]/[3]` = `0x7F` vs `contracts/opcodes.yaml` = `0xFF`）。
- **报告口径**：`ISS-446`（picolibc long-double 阻塞仍引用已关闭的 `ISS-193`）。
- **矩阵不覆盖的空白**：**10 个 FP 空白格**（测试资产缺口，非实现差异；逐格原因见矩阵册 §4）；cfx 40/40 同批一致但不进矩阵（无 chipyard 列）。
- **`ISS-426` 半边**：`ld.o ra0`/`rd2ra {ra0}` 的 `[63:54]` SBZ 未丢弃（`ld.t rf0` 半边已在 M13 修）。

## 附录 A：归档边界

- 本归档收录字段 `**项目里程碑**：M13` 且状态 `已验证` 的任务书 **106** 册（chipyard 3 / gem5 15 / infra 3 / integ 7 / llvm 2 / qemu 16 / spec 11 / testcases 49）；流水冻结在本目录 `README.md §2`（与活台账 `.tao/knowledge/milestones-m13.md`「已验证」106 行逐条相等）。
- **留活**：`m13-integ-006`（**本归档任务自身**）——归档册须终态，本册搬迁时仍 `待验收`，故**不迁入**；它留在 `.tao/tasks/integ/`，收尾时台账行由主会话处理。
- **未改动的对象**（本任务范围限定，只搬册 + 写三件套）：`milestones-m13.md` 的 106 行「已验证」行**保留**；`MEMORY.md` M13 行保留；`issues.yaml` 中 17 条 `closed_in: M13` 项**保留在活台账**——本目录 `issues-closed.md` 由 `archive_issues.py` 现生成，`--check` 判定「快照 == 现场集」，日后从活台账移除关闭项时须同步更新快照。
- **`refs/` 未动**：`.tao/knowledge/refs/**`（含 `m13-005-acceptance.*`，refs 最后一批产物）**原样保留**，清空方式待用户定。
- **M14+ 不归档**：`m14-*` / `m15-*` / `m16-*` 任务书全部留在 `.tao/tasks/**`。
