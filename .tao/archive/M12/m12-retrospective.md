# M12 回顾（chipyard 上跑通 Machine-v5-Tiny：全非 cfx 指令 + 启动链 + engine parity）

> **状态**：M12 已于 2026-11-15 达成并归档。本文件是里程碑回顾（历史摘要），不是现行判据；现行规则见 `spec/`、`.tao/contracts/`、`docs/`。

## 1 里程碑目标

M12 的目标是**把 `Machine-v5-Tiny` 真正跑在 chipyard（RTL 三平台之一）上**，让「QEMU / gem5 / RTL」从双引擎对照走向**三平台**：

- 全部**非 cfx 指令**在 `WumingTinyConfig` 上实现（解码 → 执行 → 访存 → 控制流 → 位操作/原子 → FP 全套）；
- **启动链**闭环：Tiny BootROM 固定固件 → `power` 搬运 → 最小 hmon handler，同步异常按 `escape` 0/+4 进 hmon；
- **semihosting** 由 harness 侧应答者承担（`SYS_EXIT`/`SYS_WRITE` 闭环、参数块回写）；
- **engine parity**：`embench` 与 `picolibc-full` 在 chipyard Tiny 上与 qemu **逐例状态一致**；
- 基线可重放：`bootrom.tiny.hex` 与 RTL 组件补丁集入库、`check-patch-tree` 0 问题。

> 三平台**差分**（逐条归因、矩阵）不在本里程碑，归 M13。

## 2 主要交付

- **RTL 核心**：补丁集接入 + `dadao-wuming` 骨架（`m12-chipyard-001`），解码器/整数 ALU/寄存器堆（005），12 态多周期 FSM（006），访存 `ld`/`st` 全宽度 + `ldm`/`stm`（008），控制流 + RAS（009），位操作/原子/`fence`/`swym`（010），FP 基础设施→转换→算术→除法/开方/取余→取整/缩放/符号（011–015）。
- **平台与启动链**：Tiny 地址图（002）、BootROM + `loadmem` 最小闭环（003）、harness semihosting 应答者（004）、BootROM 固件 + power 搬运 + 最小 hmon（007）、双 TL 端口 + 8-beat 取指 + FSM 骨架（018）、`cfx` 寄存器组与五类同步异常进 hmon（019）、取指预取优化（020）。
- **一致性证据**：`embench`（38 例）+ `picolibc-full` 在 chipyard Tiny 达 engine parity（016）；parity 报告生成器入仓并可 `--check` 逐字节复现（017）；FP 各组（011–015）各带三方逐字节向量证据；超时口径与报告重生成（031）。
- **规范/工具/测试**：机器命名 `dadao-tiny`/`dadao-vast`（`m12-spec-001`）、Tiny hmon 规范（002）、`Machine-v5` 口径统一（003）、hmon 装载契约与 `cfx2*` 口径（004）；QEMU 拆两台机器（`m12-qemu-001`）、gem5 FS profile 改 `vast`（`m12-gem5-001`）、测试与 profile 迁移（`m12-testcases-001`）。
- **基础设施**：M12 编号与独立台账脚手架（`m12-infra-001`）、取消 `m` 册门控（002）、子模块补丁机制（003）。

## 3 关键缺陷与修复

| 缺陷 | 根因与修复 |
|---|---|
| 取指预取回归（`m12-chipyard-022`） | `pfAddrLegal` 未判待发 beat ⇒ prefetch 命中 0；修后 0→338、p50 8→1，并补 `prefetch>0` 门控防回退 |
| quiet compare 遇 sNaN 未置 `NV`（024） | RTL + 模型 + 向量三处对齐 IEEE；三方 14/14 逐字节 |
| `fo2ft` 溢出未按 IEEE 舍入模式（025/026） | 轻微溢出只置 NX；另修「补丁未落 master」的流程缺陷（重导出补丁后 5→0、38 例） |
| FMA 溢出未按 IEEE（029） | RTL 本就合规，补 96 格实测 + 防回退用例（74/74） |
| `rootn(±0,2)`/结果 NaN 未 canonical（030） | RTL + 模型同改；50 组 2118 例逐字节 |
| `ldm` 地址寄存器落入传送范围未报 ILLI（027） | RTL 补判定；`stm` 允许、RA/RF 不适用 |
| `SYS_FLEN` 未实现致 parity 不闭环（016） | semihosting 侧补齐后 `picolibc-full` 达逐例一致 |
| BootROM hex 与 hmon 自装 workaround（028） | 重生成 `bootrom.tiny.hex` 并撤销 workaround（235/235） |
| 超时口径混入能力缺口（031） | `blocked` 只留构建/环境缺口，超时统一 `timeout(12h)` 并重生成报告 |

## 4 判据演进

- **任务编号与台账**（`m12-infra-001`）：M12 起 `mNN-<module>-<NNN[N]>`（无 `k`/`t`/`m` 后缀），台账拆为分册 `milestones-<mNN>.md`；新旧编号并存、按任务书 `**项目里程碑**` 路由（A6）。
- **核验册机制退役**（`m12-infra-002`）：`m` 册从「必需」改为「可选」；随后用户 2026-11-10 裁定彻底删除核验册机制（`m13-infra-001` 执行）。
- **补丁机制**：M12 立「子模块补丁集」（`m12-infra-003`：manifest / apply / make_patch / `check-patch-tree`），RTL 组件基线由此可重放。
- **机器命名口径**（`m12-spec-001`）：`dadao-tiny` / `dadao-vast` 定稿，QEMU/gem5/测试同批迁移；过渡别名随后由 `m12-integ-001` 移除。
- **归档白名单随模块演进**（用户 2026-11-15 裁定 A）：`check_archive.py` 的 `MODULES` 扩为含 `chipyard`（自 M12）/`linux`（自 M14），`docs/Process-04 §3/§5` 同步；只加模块名、不改归档语义。
- **engine parity 口径**（`m12-chipyard-016`/`031`）：以「逐例状态一致」为判据，`blocked` 只留构建/环境缺口，超时单列 `timeout(12h)`——已沉淀进 `docs/DDLN/`。

## 5 遗留（不阻塞达成）

- **`embench` 2 × `timeout(12h)`**（`depthconv-O0`、`matmult-int-O0` 打满预算、guest 无判决）——标签为 `timeout(12h)`，**不计入** chipyard 独有失败。
- **qemu 自身 5 例缺口**（long-double ×4 + CFX6 ×1）：登记在册，parity 时不计入 chipyard 失败，标签见 `tools/testcases/parity/README.md`。
- **`picolibc` 5 例多线程/TEE 类 `EXCLUDED`**；`test-memmem` 未跑。
- **平台分歧归 M13**：保留 cfx 集（`ISS-432`）、`trap cfx_power`（`ISS-433`）、`sc` 保留粒度（`ISS-435`）、`ra0`/`rd2ra` SBZ（`ISS-426`）、LLVM CodeGen RA 口径（`ISS-425`）。
- **多 hart 清除类**（`ISS-440`/`ISS-443`）建议同批处理并评估是否立 ADR；`ISS-444`（K1 阶段顺序证据间接）归 M14。
- **L1/L2/L3 未在 M12 收口时记录**（用户 2026-11-15 重定范围：不跑测试），归档 §3 因此不代填 rc。

## 附录 A：归档边界

- 本归档收录字段 `**项目里程碑**：M12` 且状态 `已验证` 的任务书 **41** 册（chipyard 29 / gem5 1 / infra 3 / integ 2 / qemu 1 / spec 4 / testcases 1）；流水冻结在本目录 `README.md` §2。
- **留活**：`m12-integ-003`（**本归档任务自身**）——按 `Process-04 §4.1`「归档任务自归档」，由收尾步骤迁入 `integ/`，届时须同步 §1 计数（`integ` 2→3）与 §2 流水行。
- **未改动的台账**（本任务范围限定，只搬册 + 写三件套）：`milestones-m12.md` 的 41 行「已验证」行**保留**（未按 `Process-04 §7` 删除）；`MEMORY.md` M12 行保留；`issues.yaml` 中 27 条 `closed_in: M12` 项**保留在活台账**——本目录 `issues-closed.md` 由 `archive_issues.py` 现生成，`--check` 可判定「快照 == 现场集」，日后从活台账移除时须同步更新快照。
- **M13+ 不归档**：`m13-*` / `m14-*` / `m15-*` / `m16-*` 任务书全部留在 `.tao/tasks/**`。

## 附录 B：归档门控缺口（`check-archive` 编号正则）— **已解除（2026-11-15）**

- **现象**：`tools/infra/check_archive.py` 的两处 ID 识别仍是旧式 `[A-Z][A-Z0-9]*-\d+[a-z]`（册名 `_TASK_ID_RE` + 流水「编号」列格式），M12 起的 `mNN-<module>-<NNN>` **两处都认不出**：
  - 册名不匹配 ⇒ `task_ids` 为空 ⇒ 报「归档内无任何任务书（扫描面 vacuous）」；
  - 流水行不匹配 ⇒ 报「流水编号列格式非法」。
- **影响**：本归档结构/内容/字段均已按 `Process-04` 备齐，仅因**门控编号正则未覆盖新编号**而 `check-archive` 红（其余 5 个文档门控 rc=0）。该缺口早在 `m12-integ-002` 判为「待 `check_archive.py` 支持新编号后再补」。
- **候选处置**（未自决，需用户裁定后在 `tools/` 内落地，本归档任务范围禁改 `tools/`）：
  - **A（建议）**：把两处正则扩为「旧式 `PREFIX-nnn[suffix]` 或新式 `mNN-<module>-<NNN[N]>`」，与 2026-11-15 扩 `MODULES` 同类（机械扩判据、不改归档语义），并在 `docs/Process-04 §6` 注明 M12 起的编号形。
  - **B**：流水改用「日期」列（M1–M6 历史别名形态）——可绕过编号列格式检查，但**仍挡不住**册名 `task_ids` 空导致的 vacuous 违规，且不符合 §6「M7+ 列固定」，不建议。
