# M13 归档（Archive）

> **归档日期**：2026-11-15 ｜ **范围**：M13 里程碑（2026-11-09 起，**2026-11-15 达成**）的全部任务书与相关记录
> **归档判据**：任务书字段 `**项目里程碑**：M13` 且状态 ∈ {`已验证`,`里程碑`}（**106** 册 = chipyard 3 / gem5 15 / infra 3 / integ 7 / llvm 2 / qemu 16 / spec 11 / testcases 49）；任务流水冻结 **106** 条；`MEMORY.md` 的 M13 事实行摘录见 §4（活台账**未删**）；`issues.yaml` `closed_in: M13` 关闭项 **17** 条（见 `issues-closed.md`，`tools/infra/archive_issues.py` 现生成、`--check` 可复核）。
> **自归档说明**：`m13-integ-006`（本归档任务自身）于收尾时按 `docs/Process-04 §4.1` 迁入本目录；§1 `integ` 计数（**8**）与 §2 流水（**107 行**）均已含它。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见 `m13-retrospective.md`，后续路线见 `.tao/knowledge/milestones-m14.md` / `milestones-m16.md`。

## 1 任务清单（106 个，按模块）

| 模块 | 数量 |
|---|---|
| chipyard | 3 |
| gem5 | 15 |
| infra | 3 |
| integ | 8 |
| llvm | 2 |
| qemu | 16 |
| spec | 11 |
| testcases | 49 |

> 任务书位于同目录下模块子目录（`git mv` 保留 `R` rename 历史，逐册 md5 搬前/搬后相等）。`chipyard`/`linux` 早已在归档白名单内（用户 2026-11-15 裁定，只加模块名、不改归档语义）；M13 无 `linux` 册。

## 2 任务流水（冻结）

> **冻结日期**：2026-11-15。M13 期 106 册流水按活台账 `.tao/knowledge/milestones-m13.md`「已验证」表**原值**搬入（状态按任务书规范化 `已验证`；次序 = 完成时间倒序，与台账一致）。台账行本身由主会话在收尾时处理，本归档任务**未改台账**。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| m13-integ-005 | 已验证 | 2026-11-15 19:15 | M13 收口：矩阵冻结（整数 637 + FP 227 = 864 镜像三平台一致、差异 0）+ 归因/HEAD/字节级断言 |
| m13-testcases-048 | 已验证 | 2026-11-15 19:15 | 伪指令 7 个展开形态载体（`00-isa-design`，113 点；rb 四 wyde + 64 位校验；三平台一致） |
| m13-spec-011 | 已验证 | 2026-11-15 18:05 | 伪指令迁入 `SimRISC-00 §5`（§5.1/5.2/5.3）；`SimRISC-03` 按 rd/rb/rf 拆三章；`set.ft` 写宽对照表；锁/引用同步 |
| m13-testcases-050 | 已验证 | 2026-11-15 17:44 | atomics 5 探针退役 + 执行型 `atomics_e2e`（20 点，真跑 guest）+ 多 hart GAP 节 |
| m13-llvm-002 | 已验证 | 2026-11-15 17:43 | `set.fo rf, imm64` 最小指令数展开（`rd2rf rd0` + 非零 wyde；`k=4` 退回 4 条），lit 五形态 |
| m13-testcases-049 | 已验证 | 2026-11-15 17:21 | 原子 RMW 合成序载体（`00-isa-design/atomic_rmw.S`，13 点；fetch_* / exchange / CAS 两路 + 失败不写 + 重试重读） |
| m13-chipyard-003 | 已验证 | 2026-11-15 17:18 | chipyard 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（`blockCopy forbidRf0Dst`、六类非法译码期判定；sim `4e072a71…`；三平台 7/7） |
| m13-gem5-015 | 已验证 | 2026-11-15 15:04 | gem5 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（解码表 263、`CopyNoRf0` 零读写 ILLI、周期表行 71 改指 `1+N`） |
| m13-testcases-047 | 已验证 | 2026-11-15 14:18 | `.S` 对齐 `rf2rf`（删 2 加 1 落 `02-reg-copy`）；载体 265→264、镜像 901→896；7 例待装 llvm/qemu 后转绿 |
| m13-qemu-016 | 已验证 | 2026-11-15 14:17 | QEMU 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（decode 重生成 263、trans 整 64 位 + 六类非法 ILLI） |
| m13-llvm-001 | 已验证 | 2026-11-15 14:06 | LLVM 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（.td/AsmParser/Printer/copyPhysReg + lit 167/167 + 矩阵 accept 263/0） |
| m13-spec-010 | 已验证 | 2026-11-15 13:50 | 删 `ft2ft`/`fo2fo`、加 `rf2rf`（OPC-octa/opx `111-100`）；单精写宽归位；id 264→263 |
| m13-integ-003 | 已验证 | 2026-11-15 04:45 | 整数/访存三平台差分（194 载体/629 镜像，差异 0；`int_diff.py` 生成器入仓） |
| m13-testcases-037 | 已验证 | 2026-11-15 04:30 | `sc` 保留粒度正式向量（`sc.b.nn_orrr_rd.S` 点 17–21，三平台一致；点 6 记 GAP） |
| m13-testcases-045 | 已验证 | 2026-11-15 04:00 | riscv-tests 精选 32 点并入 `.S`（+32 检查点）+ 语料/工具/报告退役（不归档不溯源） |
| m13-testcases-046 | 已验证 | 2026-11-15 03:20 | 退役后收口（`fp_spec_*` 迁 `lib/`、`check_b7` 资产断言改吃 10 个 `.S` 载体、044 覆盖矩阵入仓） |
| m13-testcases-044 | 已验证 | 2026-11-15 01:45 | 三探针收窄（+34 边界点进 `.S`；退役 3 探针与 3 个 L3 门控；`oracle_*` 保留待迁） |
| m13-chipyard-002 | 已验证 | 2026-11-15 01:25 | RTL `sc` 去掉 `resvWord` 整字比较（严格按 spec；`ISS-435`；24 id × 三平台 66/66） |
| m13-testcases-043 | 已验证 | 2026-11-15 00:20 | YAML 全退役（27 册/1315 例删除）+ `00-isa-design` + 5 条 cs overlap + 6 生成器/4 sweep/`check-inst` 退役（265 id/901 镜像） |
| m13-testcases-042 | 已验证 | 2026-11-14 21:55 | 字段域收敛（`bitcnt` 414→219；`ctpop/ctlz/cttz` 144→92）+ 每 id ≤127 门控 |
| m13-testcases-041 | 已验证 | 2026-11-14 21:30 | 补 15 条载体索引（490→505）+ `check-tests-index` 加「载体↔索引」双向断言（缺/多/重复三类） |
| m13-testcases-040 | 已验证 | 2026-11-14 21:10 | 4 条 `.S` 入索引（486→490）+ `mem_sweep` 退役（helper 迁 `inst_sweep`）+ trampoline 文档收口 |
| m13-testcases-039 | 已验证 | 2026-11-14 20:35 | 修 `11-cfx/trap_ciii_cfx.S` 的 immu18 低 8 位过时注释（编码零改动、897/897） |
| m13-integ-002 | 已验证 | 2026-11-14 20:25 | FP 三平台差分：`scope:fp` 66 条 / 232 镜像，差异 0；舍入×标志 4×6 矩阵 24 格 |
| m13-spec-009 | 已验证 | 2026-11-14 20:05 | semihosting 服务号定死 `rd16`（contract §1/Machine-v5/DD-D002 三处旧句 + 锁） |
| m13-gem5-013 | 已验证 | 2026-11-14 19:40 | gem5 `ld.t`/`ldm.t` 写 `rf0` 经 FCSR 掩码（只放行 `[4:0]`；51 点三平台一致） |
| m13-testcases-030 | 已验证 | 2026-11-14 19:35 | `.S` 入门控（`check-inst-asm` 264 id/897 镜像）+ 三册 YAML 退役 + trampoline 退役 |
| m13-qemu-015 | 已验证 | 2026-11-14 19:20 | `ld.t`/`ldm.t` 写 `rf0` 只放行 `[4:0]`（不再清 `[33:32]`；51 点三平台一致） |
| m13-testcases-036 | 已验证 | 2026-11-14 18:50 | lit E2E（176/176）+ codegen E2E（19/19）改用 64 KiB 固定固件 |
| m13-qemu-014 | 已验证 | 2026-11-14 18:35 | `sc` 保留粒度改精确地址+宽度（去整字值 CAS；8 点探针改前 4 红→改后全绿） |
| m13-testcases-033 | 已验证 | 2026-11-14 18:20 | `ext.*` `rdHD=0/64/67/63/2^64−1` 跨平台用例（各 22 链点；改前 248 正证） |
| m13-qemu-011 | 已验证 | 2026-11-14 18:05 | `-bios` 收紧为 64 KiB 固定固件、删 Tiny legacy trampoline（3 条反例具名拒绝） |
| m13-testcases-034 | 已验证 | 2026-11-14 18:05 | Tiny `expected_fault` oracle 迁到 hmon 分派口径（43 例，数值期望不变） |
| m13-testcases-032 | 已验证 | 2026-11-14 17:45 | rootn ±0 / NaN canonical / quiet-sNaN 向量（18 例）；`divrem.yaml[23]` 退役、Vast 红集清空 |
| m13-infra-003 | 已验证 | 2026-11-14 17:25 | 写者护栏：写者登记 + 读方 fail-closed（md5 前后比）+ `check-writer-guards` 27/27（`ISS-373`） |
| m13-gem5-012 | 已验证 | 2026-11-14 16:20 | gem5 `ext.*` orrr 的 `hd = rdHD[5:0]`（去 ILLI；B3 测试 +70 断言） |
| m13-spec-008 | 已验证 | 2026-11-14 16:05 | `ext.*` orrr 的 `hd = rdHD[5:0]`（spec/契约/讲义/锁同笔；删「否则 ILLI」） |
| m13-testcases-029 | 已验证 | 2026-11-14 15:55 | `12-misc` 其余 4 id（`swym`/`ctlz`/`cttz`/`ctpop`）改汇编+宏；67 链点三平台逐字节 |
| m13-testcases-027 | 已验证 | 2026-11-14 14:40 | `11-cfx` 5 id（40/40 三平台；GAP 4 项实测钉住） |
| m13-testcases-024 | 已验证 | 2026-11-14 14:20 | `08-arith-logic-tetra` 21 id（55/55 三平台；362 点；YAML 114/114 并入） |
| m13-testcases-028 | 已验证 | 2026-11-14 14:10 | `12-misc` 原子 24 id（66/66 三平台；408 点；粒度分歧登记 ISS-435） |
| m13-testcases-023 | 已验证 | 2026-11-14 13:40 | `07-floating-point` 取整/缩放/符号 8 id（22/22 三平台；166 点） |
| m13-chipyard-001 | 已验证 | 2026-11-14 13:20 | 单精写入宽度（RTL：`w0Ft` 窄写 + `ld.t` 不扩展 + `ft2ft`/`ftsgn*` 只写低 32） |
| m13-testcases-035 | 已验证 | 2026-11-14 12:50 | 07 FP 补边界（余数零符号 ±0、无符号 f2i 负向 ⇒0；24/24） |
| m13-testcases-026 | 已验证 | 2026-11-14 12:40 | `10-arith-logic-byte` 21 id（52/52 三平台；293 点） |
| m13-testcases-025 | 已验证 | 2026-11-14 12:30 | `09-arith-logic-wyde` 21 id（77/77 三平台；335 点） |
| m13-qemu-013 | 已验证 | 2026-11-14 11:50 | 单精写入宽度（`ld.t` 不扩展；ft 结果与 `ftsgnj/ftsgnn` 只写低 32） |
| m13-testcases-022 | 已验证 | 2026-11-14 11:30 | `07-floating-point` 转换/比较/分类 26 id（110/110 三平台；577 点） |
| m13-gem5-014 | 已验证 | 2026-11-14 10:20 | `ra0` 写口丢弃 SBZ（`ISS-426` gem5 侧；单平台 235/235） |
| m13-qemu-012 | 已验证 | 2026-11-14 09:20 | `ra0` 写口丢弃 SBZ（`ISS-426` QEMU 侧；RAS 路径逐字节不变） |
| m13-testcases-021 | 已验证 | 2026-11-14 08:40 | `07-floating-point` 18 id（38/38 三平台；318 点；两套独立复算 0 不符） |
| m13-testcases-031 | 已验证 | 2026-11-14 06:45 | `st.o rb0`（三路取 IP）+ `ld.o ra0` 读写（234/235，点 20 红=ISS-426） |
| m13-testcases-020 | 已验证 | 2026-11-14 04:30 | `06-control-flow` 15 id（34/34 三平台；203 点；RAS 压/弹） |
| m13-qemu-007 | 已验证 | 2026-11-14 03:20 | `ld.t rf0` 只读位（掩码写入；tetra/octa 与 chipyard 逐字节） |
| m13-qemu-010 | 已验证 | 2026-11-14 02:35 | `ext.*` orrr 的 `hd` 取 `rdHD[5:0]`（去 ILLI；uo/so 71/71，gem5 缺口钉 GAP） |
| m13-testcases-019 | 已验证 | 2026-11-14 01:20 | `05-arith-addr` 6 id（12/12 三平台；节点跑批） |
| m13-testcases-018 | 已验证 | 2026-11-14 01:15 | `04-arith-logic-octa` 位操作 4 id（12/12 三平台；节点跑批） |
| m13-testcases-017 | 已验证 | 2026-11-13 22:35 | `04-arith-logic-octa` 逻辑/移位/扩展 14 id（28/28 三平台；ext hd 归属按裁定） |
| m13-testcases-016 | 已验证 | 2026-11-13 21:45 | `04-arith-logic-octa` 算术 15 id 改汇编+宏（36/36 三平台） |
| m13-testcases-015 | 已验证 | 2026-11-13 20:28 | `03-wyde-imm` 8 个 id 改汇编+宏（15/15 三平台；证据 31 项） |
| m13-qemu-009 | 已验证 | 2026-11-13 18:32 | `rootn(±0,2)⇒+0`、结果 NaN ⇒ canonical（QEMU；check-inst 余 1 红归 032） |
| m13-gem5-011 | 已验证 | 2026-11-13 16:49 | quiet compare sNaN 置 NV、`rootn(±0,2)⇒+0`、convert NaN ⇒ canonical（gem5；vectors 4098） |
| m13-spec-007 | 已验证 | 2026-11-13 16:29 | 定稿 rootn(±0,2)=+0、结果 NaN canonical、比较族 NV 条款（spec + contract-fp） |
| m13-testcases-014 | 已验证 | 2026-11-13 16:01 | `02-reg-copy` 16 个 id 改汇编+宏（58/58 三平台逐字节） |
| m13-integ-009 | 已验证 | 2026-11-13 14:51 | FP-IEEE 对齐审计（66 条；一致 48 / 未规定 14 / 偏离 4，R1/R2 待裁定） |
| m13-testcases-013 | 已验证 | 2026-11-13 13:01 | `01-load-store` 多元素 19 id 改汇编+宏（235/235 三平台；`ldm` 禁重叠/`stm` 允/RA·RF 不适用） |
| m13-qemu-008 | 已验证 | 2026-11-13 11:34 | 融合乘加溢出（QEMU 本就合规：upstream softfloat `uncanon_normal` 按模式分派；70 格实测 + 注入因果自证） |
| m13-gem5-009 | 已验证 | 2026-11-13 10:16 | 融合乘加溢出（gem5 本就合规；补 48 格断言 + oracle 48 向量，oracle 3998→4046） |
| m13-gem5-010 | 已验证 | 2026-11-13 09:41 | gem5 的 hmon fixture 迁到最小 handler（删第二份 handler；`records` 改槽派生；`[PENDING]` 清零） |
| m13-spec-006 | 已验证 | 2026-11-13 09:38 | FMA 溢出按 IEEE 舍入模式（`SimRISC-07 §2.5` 四档×正负 + 轻微溢出只置 NX） |
| m13-gem5-008 | 已验证 | 2026-11-13 08:32 | `ldm` 地址寄存器重叠 ⇒ ILLI（gem5；解码表 8 条、`check_b1` 2156 PASS） |
| m13-qemu-006 | 已验证 | 2026-11-13 08:25 | `ldm` 地址寄存器重叠 ⇒ ILLI（QEMU；translate 期静态、TCG dump 证零副作用） |
| m13-spec-005 | 已验证 | 2026-11-13 07:54 | `ldm` 禁止地址寄存器落入传送范围（8 条引用）；`stm` 允许、RA/RF 不适用 |
| m13-testcases-009 | 已验证 | 2026-11-13 07:45 | A 组无上限 17/17 收口（16 pass / 1 blocked@172800 s）；脚本双向差集断言修复 |
| m13-spec-004 | 已验证 | 2026-11-13 07:20 | 多元素内存指令允许部分生效（例外收窄到 ldm/stm；寄存器类 12 条仍精确） |
| m13-testcases-012 | 已验证 | 2026-11-12 23:58 | `01-load-store` 单元素 19 个 id 改汇编+宏（331 例 / 68 镜像 / 三方逐字节） |
| m13-testcases-011 | 已验证 | 2026-11-12 18:18 | `fo2ft` 溢出向量 31 例（含轻微 10）+ 三方 496 B 逐字节 |
| m13-qemu-004 | 已验证 | 2026-11-12 16:13 | quiet compare 遇 sNaN 置 `NV`（nf_rule 两档；改前差分恰 4 例） |
| m13-gem5-007 | 已验证 | 2026-11-12 13:24 | `fo2ft` 溢出按 IEEE（gem5 + checker；18 格与 QEMU 逐字节，另测 8 格轻微溢出） |
| m13-spec-003 | 已验证 | 2026-11-12 12:38 | `forem` 的 NaN 优先级按 IEEE §7.2 f)（qNaN×±0 不置 NV、sNaN 置） |
| m13-qemu-005 | 已验证 | 2026-11-12 12:03 | `fo2ft` 溢出按 IEEE 舍入模式（QEMU 18 格 + 改前基线 8 格差） |
| m13-spec-002 | 已验证 | 2026-11-12 11:21 | `fo2ft` 溢出按 IEEE 754-2019 舍入模式（spec + 合约 + 13 册版本互锁升 0.5.7-rc） |
| m13-testcases-003 | 已验证 | 2026-11-12 10:53 | 长尾 7200 s 复跑：A 组 60 例（40/17/3）+ B 组 90 例（85/3/2），逐例表入 TestReports |
| m13-infra-002 | 已验证 | 2026-11-12 01:27 | 引导 ics150–ics180 四台（8 步全绿、check-inst 991/996+44/44、余 252 GB） |
| m13-qemu-003 | 已验证 | 2026-11-12 00:46 | 比较族标志对齐 IEEE（signaling compare 任一 NaN ⇒ `NV`；补上原本缺失的 sNaN 路径） |
| m13-testcases-010 | 已验证 | 2026-11-11 21:12 | 补 `cs.*` 的 not-taken 覆盖（rd 5 条 + rf 6 条；ISS-387 行动项） |
| m13-spec-001 | 已验证 | 2026-11-11 10:23 | 退出码表：`0x00`=PASS、`0x01`–`0x7F`=FAIL（127 点）+ ADR-0004 就地修订 |
| m13-integ-007 | 已验证 | 2026-11-11 05:48 | hmon 改「最小保存-跳转」（11 条指令/44 B，QEMU 先行验证通过） |
| m13-gem5-006 | 已验证 | 2026-11-11 04:52 | 补齐 gem5 hmon 检查器文件（handler/lds/layout + checker 动态派生 md5） |
| m13-integ-004 | 已验证 | 2026-11-11 03:07 | riscv-tests 移植（114 条，可移植 35）+ qemu/gem5 差分（474 例一致） |
| m13-qemu-002 | 已验证 | 2026-11-11 00:33 | QEMU 对齐 Tiny hmon 装载契约（共用 chipyard 同一 BootROM 镜像；L2 全绿） |
| m13-gem5-005 | 已验证 | 2026-11-10 23:58 | gem5 对齐 Tiny hmon 装载契约（共用 chipyard 同一 BootROM 镜像） |
| m13-testcases-008 | 已验证 | 2026-11-10 22:41 | 208 接跑 B 组差集（Y=0，前提过期；登记 4 项 run_pool 缺陷） |
| m13-testcases-007 | 已验证 | 2026-11-10 22:03 | 删除无意义探针 `start_busy_returns_busy`（陷入往返不是时间窗） |
| m13-testcases-006 | 已验证 | 2026-11-10 21:41 | 输出判据改分通道（stdout/stderr 分离；参考按源码拆两路） |
| m13-testcases-005 | 已验证 | 2026-11-10 21:04 | case 级批量测试池（多节点、即产即落、可续跑、xlong 隔离） |
| m13-gem5-004 | 已验证 | 2026-11-10 20:01 | gem5 SE 页表故障投递 guest + 脏页/帧回收修复（`lemon` 全量 0 panic） |
| m13-gem5-003 | 已验证 | 2026-11-10 11:27 | gem5 SE 缺陷：`SYS_WRITE` 句柄越界 + 非对齐 `.bss` 装载（ISS-358/359） |
| m13-integ-001 | 已验证 | 2026-11-10 10:50 | 差分产物归属 + 三平台矩阵生成器（165 行，chipyard 列 N/A） |
| m13-infra-001 | 已验证 | 2026-11-10 09:24 | 工具缺陷修复（gem5 首建 `ValueError`）+ 删除核验册机制 + 台账自动发现 |
| m13-testcases-004 | 已验证 | 2026-11-10 08:27 | 测试报告目录规范（`docs/TestReports/`）+ `check-test-reports` 门控 |
| m13-gem5-002 | 已验证 | 2026-11-10 06:34 | gem5 Tiny 恒 `hypv` + `cg3` 访问限制（ISS-363，与 QEMU 逐字节一致） |
| m13-gem5-001 | 已验证 | 2026-11-10 04:31 | gem5 的 Tiny `cfx_power` + `cfx3 hmon`（36 用例/oracle 148 条，与 QEMU 逐条一致） |
| m13-qemu-001 | 已验证 | 2026-11-10 03:54 | QEMU 的 Tiny `cfx_power` + `cfx3 hmon`（56 条断言，语义逐条对 spec） |
| m13-testcases-002 | 已验证 | 2026-11-09 23:46 | 3–4 h |
| m13-testcases-001 | 已验证 | 2026-11-09 18:26 | static 长尾 72 例 gem5 3600s + QEMU 计时，输出运行时间比率 |
| m13-integ-006 | 已验证 | 2026-11-15 19:45 | M13 归档（三件套 + 106 册迁入，含自归档） |

## 3 终局证据

| 套件 | 结果 |
|---|---|
| 三平台差分矩阵（`m13-integ-005` 冻结） | `docs/TestReports/M13-三平台差分-矩阵.md`：整数 637 + FP 227 = **864 镜像 864/864 `AGREE_PASS`**、平台差异 **0**、三方一致非通过 **0**、未归因 **0**；产物记 `input commit` 与三引擎 md5；新增链例字节级断言（三平台 `.out` 逐字节 + 长度 = 8×点数） |
| 收口门控（2026-11-15，`m13-integ-005` 现跑） | `check-inst-asm`（904/904）、`check-tests-index`、`validate-vectors`、`check-case-ledger`、`check-no-residue`、`check-knowledge-refs`、`check-test-reports` 均 rc=0；证据脚本 40 PASS / 0 FAIL / 0 BLOCKED |
| FP-IEEE 对齐审计（`m13-integ-009`） | `docs/TestReports/M13-FP-IEEE对齐审计.md`：`scope: fp` 66 条逐条对 IEEE 754-2019 —— 一致 48 / 未规定 14 / 偏离 4（R1/R2 待裁定） |
| L1 终态（MEMORY 2026-11-15） | `check-inst-asm` 904/904、`check-lit` 177/177、`check-interface` 89/89、`check-musl-freshness` PASS |
| 归档门控（2026-11-15，本任务现跑） | `check-archive` **rc=0**（册 106 / 流水 106 行）；`check-knowledge-refs` / `check-milestones-fresh`（M13/M14/M15/M16 四册）/ `check-dirs` / `check-no-residue` 均 rc=0 |
| L1 / L2 / L3 全量 | 本归档任务**不跑测试/构建**（硬约束）；M13 期亦未做里程碑级全量重跑 ⇒ **无该期全量 rc 记录，不代填** |
| 已知缺口 | 见 §5 指针的 `issues.yaml`（M13 期关闭 17 条已冻结在本目录；open 项留活台账）+ `m13-retrospective.md §5` |

## 4 MEMORY 摘录（M13 时期）

| 项目 | 内容 |
|---|---|
| 收口事实 | 矩阵冻结 `docs/TestReports/M13-三平台差分-矩阵.md`（整数 637 + FP 227 = 864 镜像三平台逐例一致、差异 0、未归因 0）；报告记 `input commit`；新增链例字节级断言 |
| rf2rf 批（全部合入） | `spec-010`（264→263 id）+ llvm/qemu/gem5/chipyard 四实现 + 向量 `02-reg-copy/rf2rf_orri_rf.S`；伪指令体系迁入 `SimRISC-00 §5`、`SimRISC-03` 按 rd/rb/rf 拆三章；7 个伪指令载体（`pseudo_set.*`，113 点）；RMW 合成序 `atomic_rmw.S`；`atomics` 5 探针退役改执行型 `atomics_e2e`；`set.fo` 最小指令数展开 |
| 引擎与安装根 | chipyard sim md5 变为 `4e072a71…`（旧 `079ae015…` 作废）；安装根已刷新（`llvm-mc` 含 `rf2rf` 与 `set.fo` 最小展开）；musl 已重建 |

> 摘录自 `.tao/knowledge/MEMORY.md` 的 M13 事实行（混合了 M12/M14/M15/M16 的行只摘 M13 部分或整行不摘）。活台账**保留**同内容（本归档任务不改 `MEMORY.md`）。

## 5 指针

- 里程碑定义/达成：**本目录** `README.md §1/§2`；活台账 `.tao/knowledge/milestones-m13.md`（**未删**，仍承载 M13 三表）
- 里程碑回顾：本目录 `m13-retrospective.md`
- 关闭 issue 快照：本目录 `issues-closed.md`（17 条；`tools/infra/archive_issues.py --milestone M13 --check .tao/archive/M13/issues-closed.md` 可复核）
- 差分报告：`docs/TestReports/M13-三平台差分-矩阵.md`（冻结）、`M13-三平台差分-qemu-gem5.md`、`M13-三平台差分矩阵.md`、`M13-FP-IEEE对齐审计.md`、`M13-A组长尾计时.md`、`M13-长尾7200s.md`
- 遗留台账：`.tao/knowledge/issues.yaml`、`.tao/knowledge/discussing.md`、`.tao/knowledge/lessons.md`
- 归档规范：`docs/Process-04-里程碑归档规范.md`；门控：`tools/infra/check_archive.py`
- 跨文件引用说明：本归档**未更新**历史引用；凡引用 `.tao/tasks/**` 中 M13 任务书路径者，其内容现位于本目录（历史指针）。
