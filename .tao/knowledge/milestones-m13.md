# 项目里程碑

> **项目里程碑 = M13**（M13 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；`milestones-m12.md` 是 M12；M11 台账已随归档删除）

> **本页只维护 M13 任务台账**：M11 及以前已归档（`.tao/archive/M11/`）；M12 见 `milestones-m12.md`；历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **M13 定位（用户 2026-11-09）**：三平台（qemu / gem5 / chipyard）的**多方差分对比**，含指令语义，尤其是**浮点**；起点 = gem5 超时与运行时间可比性。

本页分三张**任务表**，**表位置 = 任务状态**（不另设状态列）：

| 表 | 收录 | 列 |
| --- | --- | --- |
| 待开始（未开工） | 尚未派单的 `待开始` | `编号` / `预估时间` / `一句改动` |
| 进行中（已派单） | 已派单未合并：`待开始`（实现中）、`待验收`、`待返工` | `编号` / `派单时间` / `预估时间` / `一句改动` |
| 已验证 | `已验证` | `编号` / `完成时间` / `一句改动` |

- **派单即移入**：「待开始」表 = 尚未派单；**派单时**把该行移入「进行中」表并填**派单时间**（不引入新状态）。
- **派单时间**：`YYYY-MM-DD HH:MM`，派单动作发生时由主会话填写。
- **预估时间**：人工估值，只作参考；格式 `N h` / `N–M h` / `N 天` / `N–M 天` / `N min`。
- **完成时间**：`YYYY-MM-DD HH:MM`；「已验证」表按完成时间**倒序**（同时间按编号升序）。
- **testcases 系列估时口径**（2026-11-13 校准）：按 `012`/`013` 实测折算，约 **12–20 min/id**（FP/原子/控制流取上限，寄存器复制/位操作取下限）；不再用「天」级估值。
- **一句改动**：≤120 字符，只作索引，细节在任务书。

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| m13-integ-005 | 3–4 h | M13 收口（差异归因 + 矩阵冻结） （**暂不进行**，用户 2026-11-11） |
| m13-spec-010 | 3–5 h | 删 `ft2ft`/`fo2fo`、加 `rf2rf`（OPC-octa/opx `111-100`）；单精写宽归位 `SimRISC-00 §2.3`+`07` 开头 （**等 M12 收尾**） |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m13-testcases-045 | 2026-11-15 01:50 | 3–4 h | riscv-tests 精选值迁移进 `.S` + 退役（不归档不溯源） |
| m13-integ-003 | 2026-11-15 01:05 | 4–6 h | 整数与访存三平台差分（inst 全量非 cfx） |
| m13-testcases-037 | 2026-11-15 01:05 | 2–3 h | `sc` 保留粒度正式向量（同字异址/不同宽度/同址同宽/另一 lr/自消费/异常；`ISS-435`） |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
| m13-testcases-046 | 2026-11-15 03:20 | 退役后收口（`fp_spec_*` 迁 `lib/`、`check_b7` 资产断言改吃 10 个 `.S` 载体、044 覆盖矩阵入仓） |
| m13-testcases-044 | 2026-11-15 01:45 | 三探针收窄（+34 边界点进 `.S`；退役 3 探针与 3 个 L3 门控；`oracle_*` 保留待迁） |
| m13-chipyard-002 | 2026-11-15 01:25 | RTL `sc` 去掉 `resvWord` 整字比较（严格按 spec；`ISS-435`；24 id × 三平台 66/66） |
| m13-testcases-043 | 2026-11-15 00:20 | YAML 全退役（27 册/1315 例删除）+ `00-isa-design` + 5 条 cs overlap + 6 生成器/4 sweep/`check-inst` 退役（265 id/901 镜像） |
| m13-testcases-042 | 2026-11-14 21:55 | 字段域收敛（`bitcnt` 414→219；`ctpop/ctlz/cttz` 144→92）+ 每 id ≤127 门控 |
| m13-testcases-041 | 2026-11-14 21:30 | 补 15 条载体索引（490→505）+ `check-tests-index` 加「载体↔索引」双向断言（缺/多/重复三类） |
| m13-testcases-040 | 2026-11-14 21:10 | 4 条 `.S` 入索引（486→490）+ `mem_sweep` 退役（helper 迁 `inst_sweep`）+ trampoline 文档收口 |
| m13-testcases-039 | 2026-11-14 20:35 | 修 `11-cfx/trap_ciii_cfx.S` 的 immu18 低 8 位过时注释（编码零改动、897/897） |
| m13-integ-002 | 2026-11-14 20:25 | FP 三平台差分：`scope:fp` 66 条 / 232 镜像，差异 0；舍入×标志 4×6 矩阵 24 格 |
| m13-spec-009 | 2026-11-14 20:05 | semihosting 服务号定死 `rd16`（contract §1/Machine-v5/DD-D002 三处旧句 + 锁） |
| m13-gem5-013 | 2026-11-14 19:40 | gem5 `ld.t`/`ldm.t` 写 `rf0` 经 FCSR 掩码（只放行 `[4:0]`；51 点三平台一致） |
| m13-testcases-030 | 2026-11-14 19:35 | `.S` 入门控（`check-inst-asm` 264 id/897 镜像）+ 三册 YAML 退役 + trampoline 退役 |
| m13-qemu-015 | 2026-11-14 19:20 | `ld.t`/`ldm.t` 写 `rf0` 只放行 `[4:0]`（不再清 `[33:32]`；51 点三平台一致） |
| m13-testcases-036 | 2026-11-14 18:50 | lit E2E（176/176）+ codegen E2E（19/19）改用 64 KiB 固定固件 |
| m13-qemu-014 | 2026-11-14 18:35 | `sc` 保留粒度改精确地址+宽度（去整字值 CAS；8 点探针改前 4 红→改后全绿） |
| m13-testcases-033 | 2026-11-14 18:20 | `ext.*` `rdHD=0/64/67/63/2^64−1` 跨平台用例（各 22 链点；改前 248 正证） |
| m13-qemu-011 | 2026-11-14 18:05 | `-bios` 收紧为 64 KiB 固定固件、删 Tiny legacy trampoline（3 条反例具名拒绝） |
| m13-testcases-034 | 2026-11-14 18:05 | Tiny `expected_fault` oracle 迁到 hmon 分派口径（43 例，数值期望不变） |
| m13-testcases-032 | 2026-11-14 17:45 | rootn ±0 / NaN canonical / quiet-sNaN 向量（18 例）；`divrem.yaml[23]` 退役、Vast 红集清空 |
| m13-infra-003 | 2026-11-14 17:25 | 写者护栏：写者登记 + 读方 fail-closed（md5 前后比）+ `check-writer-guards` 27/27（`ISS-373`） |
| m13-gem5-012 | 2026-11-14 16:20 | gem5 `ext.*` orrr 的 `hd = rdHD[5:0]`（去 ILLI；B3 测试 +70 断言） |
| m13-spec-008 | 2026-11-14 16:05 | `ext.*` orrr 的 `hd = rdHD[5:0]`（spec/契约/讲义/锁同笔；删「否则 ILLI」） |
| m13-testcases-029 | 2026-11-14 15:55 | `12-misc` 其余 4 id（`swym`/`ctlz`/`cttz`/`ctpop`）改汇编+宏；67 链点三平台逐字节 |
| m13-testcases-027 | 2026-11-14 14:40 | `11-cfx` 5 id（40/40 三平台；GAP 4 项实测钉住） |
| m13-testcases-024 | 2026-11-14 14:20 | `08-arith-logic-tetra` 21 id（55/55 三平台；362 点；YAML 114/114 并入） |
| m13-testcases-028 | 2026-11-14 14:10 | `12-misc` 原子 24 id（66/66 三平台；408 点；粒度分歧登记 ISS-435） |
| m13-testcases-023 | 2026-11-14 13:40 | `07-floating-point` 取整/缩放/符号 8 id（22/22 三平台；166 点） |
| m13-chipyard-001 | 2026-11-14 13:20 | 单精写入宽度（RTL：`w0Ft` 窄写 + `ld.t` 不扩展 + `ft2ft`/`ftsgn*` 只写低 32） |
| m13-testcases-035 | 2026-11-14 12:50 | 07 FP 补边界（余数零符号 ±0、无符号 f2i 负向 ⇒0；24/24） |
| m13-testcases-026 | 2026-11-14 12:40 | `10-arith-logic-byte` 21 id（52/52 三平台；293 点） |
| m13-testcases-025 | 2026-11-14 12:30 | `09-arith-logic-wyde` 21 id（77/77 三平台；335 点） |
| m13-qemu-013 | 2026-11-14 11:50 | 单精写入宽度（`ld.t` 不扩展；ft 结果与 `ftsgnj/ftsgnn` 只写低 32） |
| m13-testcases-022 | 2026-11-14 11:30 | `07-floating-point` 转换/比较/分类 26 id（110/110 三平台；577 点） |
| m13-gem5-014 | 2026-11-14 10:20 | `ra0` 写口丢弃 SBZ（`ISS-426` gem5 侧；单平台 235/235） |
| m13-qemu-012 | 2026-11-14 09:20 | `ra0` 写口丢弃 SBZ（`ISS-426` QEMU 侧；RAS 路径逐字节不变） |
| m13-testcases-021 | 2026-11-14 08:40 | `07-floating-point` 18 id（38/38 三平台；318 点；两套独立复算 0 不符） |
| m13-testcases-031 | 2026-11-14 06:45 | `st.o rb0`（三路取 IP）+ `ld.o ra0` 读写（234/235，点 20 红=ISS-426） |
| m13-testcases-020 | 2026-11-14 04:30 | `06-control-flow` 15 id（34/34 三平台；203 点；RAS 压/弹） |
| m13-qemu-007 | 2026-11-14 03:20 | `ld.t rf0` 只读位（掩码写入；tetra/octa 与 chipyard 逐字节） |
| m13-qemu-010 | 2026-11-14 02:35 | `ext.*` orrr 的 `hd` 取 `rdHD[5:0]`（去 ILLI；uo/so 71/71，gem5 缺口钉 GAP） |
| m13-testcases-019 | 2026-11-14 01:20 | `05-arith-addr` 6 id（12/12 三平台；节点跑批） |
| m13-testcases-018 | 2026-11-14 01:15 | `04-arith-logic-octa` 位操作 4 id（12/12 三平台；节点跑批） |
| m13-testcases-017 | 2026-11-13 22:35 | `04-arith-logic-octa` 逻辑/移位/扩展 14 id（28/28 三平台；ext hd 归属按裁定） |
| m13-testcases-016 | 2026-11-13 21:45 | `04-arith-logic-octa` 算术 15 id 改汇编+宏（36/36 三平台） |
| m13-testcases-015 | 2026-11-13 20:28 | `03-wyde-imm` 8 个 id 改汇编+宏（15/15 三平台；证据 31 项） |
| m13-qemu-009 | 2026-11-13 18:32 | `rootn(±0,2)⇒+0`、结果 NaN ⇒ canonical（QEMU；check-inst 余 1 红归 032） |
| m13-gem5-011 | 2026-11-13 16:49 | quiet compare sNaN 置 NV、`rootn(±0,2)⇒+0`、convert NaN ⇒ canonical（gem5；vectors 4098） |
| m13-spec-007 | 2026-11-13 16:29 | 定稿 rootn(±0,2)=+0、结果 NaN canonical、比较族 NV 条款（spec + contract-fp） |
| m13-testcases-014 | 2026-11-13 16:01 | `02-reg-copy` 16 个 id 改汇编+宏（58/58 三平台逐字节） |
| m13-integ-009 | 2026-11-13 14:51 | FP-IEEE 对齐审计（66 条；一致 48 / 未规定 14 / 偏离 4，R1/R2 待裁定） |
| m13-testcases-013 | 2026-11-13 13:01 | `01-load-store` 多元素 19 id 改汇编+宏（235/235 三平台；`ldm` 禁重叠/`stm` 允/RA·RF 不适用） |
| m13-qemu-008 | 2026-11-13 11:34 | 融合乘加溢出（QEMU 本就合规：upstream softfloat `uncanon_normal` 按模式分派；70 格实测 + 注入因果自证） |
| m13-gem5-009 | 2026-11-13 10:16 | 融合乘加溢出（gem5 本就合规；补 48 格断言 + oracle 48 向量，oracle 3998→4046） |
| m13-gem5-010 | 2026-11-13 09:41 | gem5 的 hmon fixture 迁到最小 handler（删第二份 handler；`records` 改槽派生；`[PENDING]` 清零） |
| m13-spec-006 | 2026-11-13 09:38 | FMA 溢出按 IEEE 舍入模式（`SimRISC-07 §2.5` 四档×正负 + 轻微溢出只置 NX） |
| m13-gem5-008 | 2026-11-13 08:32 | `ldm` 地址寄存器重叠 ⇒ ILLI（gem5；解码表 8 条、`check_b1` 2156 PASS） |
| m13-qemu-006 | 2026-11-13 08:25 | `ldm` 地址寄存器重叠 ⇒ ILLI（QEMU；translate 期静态、TCG dump 证零副作用） |
| m13-spec-005 | 2026-11-13 07:54 | `ldm` 禁止地址寄存器落入传送范围（8 条引用）；`stm` 允许、RA/RF 不适用 |
| m13-testcases-009 | 2026-11-13 07:45 | A 组无上限 17/17 收口（16 pass / 1 blocked@172800 s）；脚本双向差集断言修复 |
| m13-spec-004 | 2026-11-13 07:20 | 多元素内存指令允许部分生效（例外收窄到 ldm/stm；寄存器类 12 条仍精确） |
| m13-testcases-012 | 2026-11-12 23:58 | `01-load-store` 单元素 19 个 id 改汇编+宏（331 例 / 68 镜像 / 三方逐字节） |
| m13-testcases-011 | 2026-11-12 18:18 | `fo2ft` 溢出向量 31 例（含轻微 10）+ 三方 496 B 逐字节 |
| m13-qemu-004 | 2026-11-12 16:13 | quiet compare 遇 sNaN 置 `NV`（nf_rule 两档；改前差分恰 4 例） |
| m13-gem5-007 | 2026-11-12 13:24 | `fo2ft` 溢出按 IEEE（gem5 + checker；18 格与 QEMU 逐字节，另测 8 格轻微溢出） |
| m13-spec-003 | 2026-11-12 12:38 | `forem` 的 NaN 优先级按 IEEE §7.2 f)（qNaN×±0 不置 NV、sNaN 置） |
| m13-qemu-005 | 2026-11-12 12:03 | `fo2ft` 溢出按 IEEE 舍入模式（QEMU 18 格 + 改前基线 8 格差） |
| m13-spec-002 | 2026-11-12 11:21 | `fo2ft` 溢出按 IEEE 754-2019 舍入模式（spec + 合约 + 13 册版本互锁升 0.5.7-rc） |
| m13-testcases-003 | 2026-11-12 10:53 | 长尾 7200 s 复跑：A 组 60 例（40/17/3）+ B 组 90 例（85/3/2），逐例表入 TestReports |
| m13-infra-002 | 2026-11-12 01:27 | 引导 ics150–ics180 四台（8 步全绿、check-inst 991/996+44/44、余 252 GB） |
| m13-qemu-003 | 2026-11-12 00:46 | 比较族标志对齐 IEEE（signaling compare 任一 NaN ⇒ `NV`；补上原本缺失的 sNaN 路径） |
| m13-testcases-010 | 2026-11-11 21:12 | 补 `cs.*` 的 not-taken 覆盖（rd 5 条 + rf 6 条；ISS-387 行动项） |
| m13-spec-001 | 2026-11-11 10:23 | 退出码表：`0x00`=PASS、`0x01`–`0x7F`=FAIL（127 点）+ ADR-0004 就地修订 |
| m13-integ-007 | 2026-11-11 05:48 | hmon 改「最小保存-跳转」（11 条指令/44 B，QEMU 先行验证通过） |
| m13-gem5-006 | 2026-11-11 04:52 | 补齐 gem5 hmon 检查器文件（handler/lds/layout + checker 动态派生 md5） |
| m13-integ-004 | 2026-11-11 03:07 | riscv-tests 移植（114 条，可移植 35）+ qemu/gem5 差分（474 例一致） |
| m13-qemu-002 | 2026-11-11 00:33 | QEMU 对齐 Tiny hmon 装载契约（共用 chipyard 同一 BootROM 镜像；L2 全绿） |
| m13-gem5-005 | 2026-11-10 23:58 | gem5 对齐 Tiny hmon 装载契约（共用 chipyard 同一 BootROM 镜像） |
| m13-testcases-008 | 2026-11-10 22:41 | 208 接跑 B 组差集（Y=0，前提过期；登记 4 项 run_pool 缺陷） |
| m13-testcases-007 | 2026-11-10 22:03 | 删除无意义探针 `start_busy_returns_busy`（陷入往返不是时间窗） |
| m13-testcases-006 | 2026-11-10 21:41 | 输出判据改分通道（stdout/stderr 分离；参考按源码拆两路） |
| m13-testcases-005 | 2026-11-10 21:04 | case 级批量测试池（多节点、即产即落、可续跑、xlong 隔离） |
| m13-gem5-004 | 2026-11-10 20:01 | gem5 SE 页表故障投递 guest + 脏页/帧回收修复（`lemon` 全量 0 panic） |
| m13-gem5-003 | 2026-11-10 11:27 | gem5 SE 缺陷：`SYS_WRITE` 句柄越界 + 非对齐 `.bss` 装载（ISS-358/359） |
| m13-integ-001 | 2026-11-10 10:50 | 差分产物归属 + 三平台矩阵生成器（165 行，chipyard 列 N/A） |
| m13-infra-001 | 2026-11-10 09:24 | 工具缺陷修复（gem5 首建 `ValueError`）+ 删除核验册机制 + 台账自动发现 |
| m13-testcases-004 | 2026-11-10 08:27 | 测试报告目录规范（`docs/TestReports/`）+ `check-test-reports` 门控 |
| m13-gem5-002 | 2026-11-10 06:34 | gem5 Tiny 恒 `hypv` + `cg3` 访问限制（ISS-363，与 QEMU 逐字节一致） |
| m13-gem5-001 | 2026-11-10 04:31 | gem5 的 Tiny `cfx_power` + `cfx3 hmon`（36 用例/oracle 148 条，与 QEMU 逐条一致） |
| m13-qemu-001 | 2026-11-10 03:54 | QEMU 的 Tiny `cfx_power` + `cfx3 hmon`（56 条断言，语义逐条对 spec） |
| m13-testcases-002 | 2026-11-09 23:46 | 3–4 h |
| m13-testcases-001 | 2026-11-09 18:26 | static 长尾 72 例 gem5 3600s + QEMU 计时，输出运行时间比率 |
