# M12 归档（Archive）

> **归档日期**：2026-11-15 ｜ **范围**：M12 里程碑（2026-11-08 起，**2026-11-15 达成**）的全部任务书与相关记录
> **归档判据**：任务书字段 `**项目里程碑**：M12` 且状态 ∈ {`已验证`,`里程碑`}（**41** 册 = chipyard 29 / gem5 1 / infra 3 / integ 2 / qemu 1 / spec 4 / testcases 1）；任务流水冻结 **41** 条；`MEMORY.md` 纯 M12 行 **2** 行（摘录见 §4，活台账未删）；`issues.yaml` `closed_in: M12` 关闭项 **27** 条（见 `issues-closed.md`，工具现生成）。
> **自归档说明**：`m12-integ-003`（本归档任务自身）于收尾时按 `docs/Process-04 §4.1` 迁入本目录；§1 `integ` 计数与 §2 流水均已含它（册 42 / 流水 42）。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见 `m12-retrospective.md`，后续路线见 `.tao/knowledge/milestones-m13.md`。

## 1 任务清单（41 个，按模块）

| 模块 | 数量 |
|---|---|
| chipyard | 29 |
| gem5 | 1 |
| infra | 3 |
| integ | 3 |
| qemu | 1 |
| spec | 4 |
| testcases | 1 |

> 任务书位于同目录下模块子目录（`git mv` 保留 `R` rename 历史）。`chipyard/` 为 M12 新增模块：归档白名单已同步（`chipyard` 自 M12、`linux` 自 M14；用户 2026-11-15 裁定，只加模块名、不改归档语义）。

## 2 任务流水（冻结）

> **冻结日期**：2026-11-15。M12 期 41 册流水按原 M12 台账「已验证」表现值搬入（状态按任务书规范化 `已验证`；次序 = 完成时间倒序）。原台账已于 2026-11-15 **合并至本归档并删除**（见 `m12-retrospective.md` 附录 C）。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| m12-integ-002 | 已验证 | 2026-11-15 12:05 | M12 收口（README/DDLN 沉淀 + 遗留清单；不做逐条表/不跑测试，用户 2026-11-15 重定范围） |
| m12-chipyard-031 | 已验证 | 2026-11-15 11:20 | 超时口径改 `timeout(12h)`（`blocked` 只留构建/环境缺口）+ 报告重生成（`PASS 36 / timeout(12h) 2`） |
| m12-chipyard-017 | 已验证 | 2026-11-15 09:55 | 引擎 parity 报告生成器入仓（`--check` 逐字节复现；两个 `.sh` 按新规则待迁出） |
| m12-chipyard-016 | 已验证 | 2026-11-15 01:10 | embench（38）+ picolibc-full 在 chipyard Tiny 达 engine parity（`SYS_FLEN` 修复；单二进制证据） |
| m12-chipyard-028 | 已验证 | 2026-11-14 07:00 | 重生成 `bootrom.tiny.hex`（514300…/c499803a…）+ 撤 hmon 自装 workaround（235/235） |
| m12-chipyard-029 | 已验证 | 2026-11-14 02:20 | 融合乘加溢出按 IEEE（RTL 本就合规；96 格实测 + 防回退用例，74/74 证据） |
| m12-chipyard-030 | 已验证 | 2026-11-13 19:02 | `rootn(±0,2)⇒+0`、结果 NaN ⇒ canonical（RTL + 模型；50 组 2118 例逐字节） |
| m12-chipyard-027 | 已验证 | 2026-11-13 11:43 | `ldm` 地址寄存器落入传送范围 ⇒ ILLI（chipyard RTL；`stm` 允许、RA/RF 不适用） |
| m12-chipyard-015 | 已验证 | 2026-11-12 21:49 | FP 取整/缩放/符号（6 档舍入/scalB 三类/符号无标志；四条各 1 拍） |
| m12-chipyard-024 | 已验证 | 2026-11-12 19:04 | quiet compare 遇 sNaN 置 `NV`（RTL + 模型 + 向量；三方 14/14 逐字节） |
| m12-chipyard-026 | 已验证 | 2026-11-12 16:50 | 修复 `fo2ft` 未落 master（补丁重导、`forceInfOnOverflow` 5→0、38 例） |
| m12-chipyard-025 | 已验证 | 2026-11-12 13:35 | `fo2ft` 溢出按 IEEE 舍入模式（RTL + 模型；轻微溢出只置 NX，与 QEMU 38/38 一致） |
| m12-chipyard-014 | 已验证 | 2026-11-12 11:25 | FP 除法/开方/取余（fo 56 拍恒定、`forem` 53+d+1；`DZ` 端到端首个生产者） |
| m12-chipyard-013 | 已验证 | 2026-11-12 01:26 | FP 算术（加/乘/FMA 单次舍入/比较/最小最大；FMA NaN×Inf 缺陷修复；compare NV 对齐 IEEE） |
| m12-chipyard-012 | 已验证 | 2026-11-11 20:32 | FP 转换（8 条 f2i + 格式转换 + SBZ + 复制；`NV`/`DZ` 标志端到端接入） |
| m12-chipyard-011 | 已验证 | 2026-11-11 17:48 | FP 基础设施（recFN 编解码 + 六档舍入 + 五类标志 + 分类，RTL==hardfloat 逐例） |
| m12-chipyard-010 | 已验证 | 2026-11-11 14:36 | 位操作 + 原子（`lr`/`sc` 24 形式、保留标记四路径）+ `fence`/`swym`（621/141/202 例） |
| m12-chipyard-022 | 已验证 | 2026-11-11 10:34 | 修预取回归（`pfAddrLegal` 判待发 beat；prefetch 0→338、p50 8→1）+ 补 `prefetch>0` 门控 |
| m12-chipyard-009 | 已验证 | 2026-11-11 09:29 | 控制流 + RAS（63 槽、溢出写 MRPTR-8、下溢先读再判，精确 RASOF/RASUF） |
| m12-chipyard-008 | 已验证 | 2026-11-11 07:12 | 访存：`ld`/`st` 全宽度 + `ldm`/`stm`（8B beat、byte mask、精确 MALIGN/CFXMEM） |
| m12-chipyard-019 | 已验证 | 2026-11-11 04:18 | `cfx_power`/`cfx3` 寄存器组 + 五类同步异常进 hmon（`escape` 0/+4） |
| m12-chipyard-020 | 已验证 | 2026-11-11 00:38 | 取指预取优化：4 预取槽 + 数据优先仲裁（跨 beat 8→p50=1） |
| m12-chipyard-007 | 已验证 | 2026-11-10 19:24 | Tiny BootROM 固定固件 + power 搬运 + 最小 hmon handler（56 B） |
| m12-chipyard-018 | 已验证 | 2026-11-10 16:21 | 核心结构改造：双 TL 端口 + 8-beat 取指 + FSM 骨架 |
| m12-spec-004 | 已验证 | 2026-11-10 12:14 | hmon 装载契约（BootROM→power 搬运）+ rc10 初值/对齐 + `cfx2*` 口径 + 退出码只定编码 |
| m12-spec-003 | 已验证 | 2026-11-10 09:30 | `Machine-v5` 口径统一（reserved 改为引用上游 / `switch_run_mode` 读回 3 / 修 `DADAO-12` 笔误） |
| m12-chipyard-005 | 已验证 | 2026-11-10 02:16 | 解码器 + 整数 ALU + 寄存器堆（273 例三方一致，含 ILLI/UNDI） |
| m12-spec-002 | 已验证 | 2026-11-10 02:16 | Tiny 引入 cfx_power + cfx3 hmon 规范 + 只读锁（0.4.2-rc） |
| m12-chipyard-006 | 已验证 | 2026-11-10 00:48 | 多周期状态机设计（12 态 FSM + 转移表 + hmon 异常/ip 语义 + §9 spec 偏差清单） |
| m12-infra-003 | 已验证 | 2026-11-09 19:02 | 子模块补丁机制（manifest/apply/make_patch/check_patch_tree + testchipip 试点） |
| m12-chipyard-004 | 已验证 | 2026-11-09 14:06 | harness 侧 semihosting 应答者（最小 5 服务 + 核内抬边界） |
| m12-chipyard-003 | 已验证 | 2026-11-09 11:24 | BootROM + `loadmem` 最小闭环（ELF 落 SRAM、复位跳转、可观测结果） |
| m12-chipyard-002 | 已验证 | 2026-11-09 05:22 | Tiny 地址图落地（BootROM `0xffff_ffff_0000` + SRAM 8 MiB，paddrBits≥48） |
| m12-integ-001 | 已验证 | 2026-11-09 03:17 | 移除过渡别名（`dadao-m1`、`profile=node`） |
| m12-testcases-001 | 已验证 | 2026-11-09 02:27 | 测试与 profile 迁移到 `tiny`/`vast`（yaml/inc/env/46 文件） |
| m12-chipyard-001 | 已验证 | 2026-11-09 01:25 | chipyard 补丁集接入 + `dadao-wuming` 最小骨架（外壳 B，core 桩） |
| m12-infra-002 | 已验证 | 2026-11-09 01:25 | 取消 m 册门控（m 册从必需改为可选，其余校验项保留） |
| m12-gem5-001 | 已验证 | 2026-11-09 00:25 | gem5 FS profile `node`→`vast`（保留 node 过渡别名） |
| m12-qemu-001 | 已验证 | 2026-11-08 23:19 | QEMU 拆两台机器 `dadao-tiny`/`dadao-vast`（保留 m1 过渡别名） |
| m12-spec-001 | 已验证 | 2026-11-08 22:25 | 机器命名定稿 Tiny/Vast（spec + contracts + docs，含锁更新） |
| m12-infra-001 | 已验证 | 2026-11-08 21:38 | M12 编号与独立台账脚手架（新旧编号并存 + A6 路由 + `--file`） |
| m12-integ-003 | 已验证 | 2026-11-15 13:50 | M12 归档（三件套 + 42 册迁入，含自归档） |

## 3 终局证据

| 套件 | 结果 |
|---|---|
| 收口门控（2026-11-15，`m12-integ-002` 现跑） | `check-knowledge-refs` / `check-milestones-fresh` / `check-dirs` / `check-no-residue` 均 rc=0（M12 段：待开始 0 / 进行中 1 / 已验证 40） |
| engine parity（`m12-chipyard-031` 重生成报告） | `embench` PASS 36 + `timeout(12h)` 2（`depthconv-O0`/`matmult-int-O0`，无判决）；`picolibc-full` 与 qemu 逐例状态一致、chipyard 独有失败 0 |
| 补丁树 / 基线（`m12-chipyard-028`） | `check-patch-tree` chipyard 段 0 问题；`bootrom.tiny.hex` 重生成、hmon 自装 workaround 撤销（235/235） |
| 归档门控（2026-11-15，本任务现跑） | `check-archive` **rc=0**（册 41 / 流水 41 行；`--self-test` 14/14）；`check-knowledge-refs` / `check-milestones-fresh` / `check-dirs` / `check-no-residue` 均 rc=0。编号正则缺口已由主会话解除（见 `m12-retrospective.md` 附录 B） |
| L1 / L2 / L3 | M12 收口按用户 2026-11-15 重定范围**未跑**（`m12-integ-002`）；本归档任务亦不跑测试/构建 ⇒ **无该期 rc 记录，不代填** |
| 已知缺口 | 见 §5 指针的 `issues.yaml`（M12 期关闭 27 条已冻结，open 项留活台账） |

## 4 MEMORY 摘录（M12 时期）

| 项目 | 内容 |
|---|---|
| 收口动作 | 台账标「M12 已收口」；根 `README.md` 加 M12 成就与遗留要点；`docs/DDLN/` 沉淀 4 条判据（engine parity / 单二进制 / `timeout` 口径 / 脚本入仓） |
| 关键事实 | 全部非 cfx 指令在 chipyard Tiny 实现；启动链 + semihosting 闭环；`embench` 36 PASS + 2 `timeout(12h)`；`picolibc-full` 达 engine parity（qemu 自身 5 例缺口登记在册） |

> 摘录自 `.tao/knowledge/MEMORY.md`「M12 收口」两条纯 M12 行（混合了 M13+/M14/M16 的行不摘）。活台账**保留**同内容（本归档任务不改台账）。

## 5 指针

- 里程碑定义/达成：**本目录** `README.md §1/§2`（原 `milestones-m12.md` 已合并入此并于 2026-11-15 删除，git 历史可回溯）
- 里程碑回顾：本目录 `m12-retrospective.md`
- 关闭 issue 快照：本目录 `issues-closed.md`（27 条；`tools/infra/archive_issues.py --milestone M12 --check` 可复核）
- 遗留台账：`.tao/knowledge/issues.yaml`、`.tao/knowledge/discussing.md`、`.tao/knowledge/lessons.md`
- 归档规范：`docs/Process-04-里程碑归档规范.md`；门控：`tools/infra/check_archive.py`
- 跨文件引用说明：本归档**未更新**历史引用；凡引用 `.tao/tasks/**` 中 M12 任务书路径者，其内容现位于本目录（历史指针）。
