# M17 归档（Archive）

> **归档日期**：2026-11-27 ｜ **范围**：M17 里程碑（**2026-11-27 达成**）的全部任务书与相关记录 —— **IDL 可执行参考模型 + 四方差分（IDL / QEMU / gem5 / RTL，golden = IDL）**
> **归档判据**：任务书字段 `**项目里程碑**：M17` 且状态 ∈ {`已验证`,`里程碑`}（**46** 册 = idl 25 / spec 7 / testcases 7 / chipyard 2 / infra 2 / gem5 1 / qemu 1 / integ 1；45 册 `已验证` + 本归档册 `里程碑`）；任务流水冻结 **46** 条；`issues-*.yaml` 中 `closed_in: M17` 关闭项 **21** 条（`issues-m17.yaml` 20 + `issues-left.yaml` 的 `ISS-left-003`，见 `issues-closed.md`，`tools/infra/archive_issues.py --verify` 可复核）；`MEMORY.md` 纯 M17 行移除、摘要见 §4。
> **自归档说明**：`m17-integ-001`（本归档任务自身）按 `docs/Process-04 §4.1` 迁入 `integ/`；§1 `integ` 计数（1）与 §2 流水（46 行）均已含它。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见 `m17-retrospective.md`，后续路线见 `.tao/knowledge/milestones-m18.md`–`milestones-m20.md`。

## 1 任务清单（46 个，按模块）

| 模块 | 数量 |
|---|---|
| idl | 25 |
| spec | 7 |
| testcases | 7 |
| chipyard | 2 |
| infra | 2 |
| gem5 | 1 |
| qemu | 1 |
| integ | 1 |

> 任务书位于同目录下模块子目录（`git mv` 保留 `R` rename 历史，逐册 md5 搬前/搬后相等）。模块目录按 M17 实际出现者建（M17 无 `linux`/`llvm` 册）。

## 2 任务流水（冻结）

> **冻结日期**：2026-11-27。45 条「已验证」行按活台账 `.tao/knowledge/milestones-m17.md`「已验证」表**原值**搬入（状态按任务书规范化 `已验证`；次序 = 完成时间倒序，与台账一致），另加本归档任务（`里程碑`）一行；台账文件随本归档删除。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| m17-integ-001 | 里程碑 | 2026-11-27 16:19 | M17 归档（46 册迁 `.tao/archive/M17/`；台账/MEMORY/README/issue 快照收口） |
| m17-testcases-008 | 已验证 | 2026-11-27 16:03 | `escape_ciii_cfx` Tiny 验证 CFXREG + `DIV-18` 逐槽声明（四方 274/274） |
| m17-idl-026 | 已验证 | 2026-11-27 14:54 | `idl_four_way` 支持 `expected-divergences` 逐槽例外（未生效必红） |
| m17-idl-025 | 已验证 | 2026-11-27 14:39 | trace 入口态 seed cfx 计数/掩码（计数严格相等；trace 274/274） |
| m17-chipyard-002 | 已验证 | 2026-11-27 12:34 | `escape_ciii_cfx` 空签名根因：Tiny 缺 `cg4`/`cg15 rc3` ⇒ CFXREG 未武装即入 pad |
| m17-idl-024 | 已验证 | 2026-11-26 21:40 | trace 全 64 槽按值比（删窗口/来源过滤与 `skip`；pre-cg15 QEMU 274/274） |
| m17-idl-023 | 已验证 | 2026-11-26 20:16 | IDL 执行器 RegRAS 改环形缓冲（去搬移；自检 133/133） |
| m17-idl-022 | 已验证 | 2026-11-25 23:51 | trace 跳过集两侧对称化（`ISS-537`）；全量 274/274 |
| m17-spec-007 | 已验证 | 2026-11-25 22:32 | 契约交叉引用/数字引用收敛（`ISS-484`；来源去版本号、删「60 条」） |
| m17-spec-006 | 已验证 | 2026-11-25 22:12 | ADR-0004/0020 退出码分段指针化（接 `ISS-384` 口径） |
| m17-spec-005 | 已验证 | 2026-11-25 16:59 | ADR-0009 D5 + chipyard README 退出码指针化（`ISS-384`） |
| m17-chipyard-001 | 已验证 | 2026-11-25 12:05 | RTL 扁平位图 + 关闭 `DIV-07`（`GewuCauseId` 一条异常一位、删 `[39]/[57]`；`perm_hypv.inc` 15 探针；31+2 补丁） |
| m17-spec-004 | 已验证 | 2026-11-25 06:31 | ADR-0063 Accepted（opcodes 单一写者；16 直接读点；用户确认 D1–D5） |
| m17-idl-021 | 已验证 | 2026-11-25 00:40 | IDL 复核遗留清理（可达自检 + trace 限制文档；`ISS-490/491` 关闭） |
| m17-infra-002 | 已验证 | 2026-11-24 23:48 | `check-spec-refs` 支持 `Kaiwu` 前缀（1416 引用/0 失败；`ISS-521`） |
| m17-idl-020 | 已验证 | 2026-11-24 23:47 | cfx 权限轴 `cfxreg`/`cfxexe` + 2 条拒绝路径载体（272→274；`check-idl` 274/274、L1 十门控 0；ADR-0062 口径） |
| m17-spec-003 | 已验证 | 2026-11-24 23:46 | opcodes 生成一致性 L1 门控（`check-opcodes-repro`；yaml 零改动） |
| m17-gem5-001 | 已验证 | 2026-11-24 21:43 | gem5：权限编码扁平化（删两位；PTW 位图；`checkCauseId`） |
| m17-testcases-006 | 已验证 | 2026-11-24 21:37 | `stm` 注释按寄存器订正 + `immu6=63` 边界（+19 槽；4556） |
| m17-qemu-001 | 已验证 | 2026-11-24 21:24 | QEMU：`CFXPERM cause_info`=指令地址；扁平位图；删两位 |
| m17-spec-002 | 已验证 | 2026-11-24 20:21 | spec/contract 扁平位图（删 `[39]`/`[57]`；迁移期运行红属预期） |
| m17-spec-001 | 已验证 | 2026-11-24 19:45 | ADR-0062 权限编码扁平化（Accepted；D1–D6；32 条影响清单） |
| m17-testcases-005 | 已验证 | 2026-11-23 21:52 | 测试向量去除内存实现术语：`beat`/`拍`/字节通道 → 数据单元/字节（59 输入文件；272 镜像 `.text` 零漂移、`expected.tsv` 零变化） |
| m17-testcases-004 | 已验证 | 2026-11-23 21:05 | `st.o` 4 文件语义行（整 64 位/整 8 字节全部写入）+ 窄写 4 文件显式字节数 + `st.o_rrii_rf` 补 `rf0` 作源用例（272/272、三平台 168 B 全等） |
| m17-idl-019 | 已验证 | 2026-11-23 08:37 | `idl_check_trace --cases` 兼容 `image`/`id`（`ISS-518`） |
| m17-infra-001 | 已验证 | 2026-11-23 08:36 | `check-spec-refs` 标题型引用同时校章号（`ISS-447`；1381 引用/0 失败） |
| m17-testcases-003 | 已验证 | 2026-11-23 01:18 | 退役 `check-inst-sig`（`check-idl` 为超集；保留期望值生成器） |
| m17-idl-017 | 已验证 | 2026-11-23 01:04 | 执行器依据锁（263 op + `lib/*.idl` sha；`check-idl-exec-anchor` 进 L1） |
| m17-idl-016 | 已验证 | 2026-11-23 00:52 | spec 263 块生成注记改稳定写法（`spec/` 内 `idl/render.py` 命中 0） |
| m17-idl-015 | 已验证 | 2026-11-23 00:32 | manifest `ignore` 字段（`__pycache__`；三条防滥用校验；`ISS-480` 关闭） |
| m17-idl-014 | 已验证 | 2026-11-23 00:19 | 全四方进 `night-run`（第 9 成员 `idl:four-way`；L2 仍两方） |
| m17-idl-013 | 已验证 | 2026-11-22 23:25 | 阶段二：FP 50 例纳入四方差分（272/272、4539 槽；A 路线复用 `idl_fp`） |
| m17-idl-012 | 已验证 | 2026-11-22 22:25 | IDL 脚本归拢到 `idl/{tools,data,docs}` + `idl_` 前缀（行为零改动、222/222） |
| m17-idl-011 | 已验证 | 2026-11-22 22:02 | 补 IDL 语言语义 U04–U10（UDB 原文 + U10 取低 N 位；未定义只剩 U01–U03） |
| m17-idl-010 | 已验证 | 2026-11-22 19:54 | 门控硬断言：收口后 `pending` 必须为空（堵静默降覆盖） |
| m17-idl-009 | 已验证 | 2026-11-22 19:32 | 阶段一收口：222 例四方零红、`pending` 0；L2 门控与抽样复核 |
| m17-idl-008 | 已验证 | 2026-11-22 19:00 | 执行器补齐：窄位宽 ALU（08/09/10 + 03 全册；222 例四方绿、pending 0） |
| m17-idl-007 | 已验证 | 2026-11-22 18:31 | 执行器补齐：八元算术与杂项（04/12 册 + `atomic_rmw`，49 个新 id；155 例四方绿） |
| m17-idl-006 | 已验证 | 2026-11-22 17:50 | 执行器补齐：访存/寄存器复制/控制流/异常（01/02/05/06/11 + `pseudo_set`/`undi`，41 个新 id；101 例四方绿） |
| m17-idl-005 | 已验证 | 2026-11-22 17:08 | 四方差分驱动（签名槽+退出码）与 `check-idl` 进 L2（28 例基线） |
| m17-idl-004 | 已验证 | 2026-11-21 23:09 | 逐指令 trace 与 QEMU 比对（24790 条记录全等；CFXMEM 子原因改 [57] NONPTW） |
| m17-idl-003 | 已验证 | 2026-11-21 22:27 | 执行器核心（四寄存器组/ELF/最小 trap；28/28 与 QEMU 最终状态全等） |
| m17-testcases-002 | 已验证 | 2026-11-20 21:12 | `ldm.t` 注释订正 + `rf0` 作目的用例 + `ldm.ut/uw` 补 `immu6=63`（签名 4528 槽、ledger 5681） |
| m17-testcases-001 | 已验证 | 2026-11-20 20:25 | `tests/inst` 签名槽级比对（272 镜像/4519 槽；期望从 `.S` 派生；`check-inst-sig` 进 L2） |
| m17-idl-002 | 已验证 | 2026-11-20 17:49 | Python 解析器（263 operation 全量、拒绝集 13/13、fixture + 独立 oracle；`check-idl-parse` 进 L1） |
| m17-idl-001 | 已验证 | 2026-11-20 17:21 | 语法子集 66 类 + 宽度规则 28 条 + 未定义 10 条（263 三处自洽；`subset_stats.py` 校验） |

## 3 终局证据

| 套件 | 结果 |
| --- | --- |
| `make check-idl-full`（全四方 IDL/QEMU/gem5/chipyard，274 镜像） | **rc=0，274/274**（2026-11-27 16:05；`DIV-18` 逐槽标注 8 条；主清单 274 / pending 0 / 现场派生 274） |
| 逐指令 trace（IDL↔QEMU，274 镜像） | **274/274，249995 条记录**（`m17-idl-025`，2026-11-27 14:39；入口态 seed cfx 计数/掩码，计数严格相等） |
| L1 `make check` | **rc=2**：`check-patch-tree` **52 problem**，全部在 `linux`（51）/`musl`（1），其余组件 0；属既有基线红，已登记 `ISS-left-004`（非 M17 变更面） |
| L2 `make check-idl`（IDL+QEMU，274 镜像） | **rc=0，274/274**（本归档任务复跑；归档不改代码，见下方收尾门控） |
| L3 `make check-full` | **rc=2**：`arch` **rc=0**（`check-arch-smoke` / `check-arch` PASS，10 case × 1 平台）；`unit:full` 与 `tset:m6` 同根因 **rc=1**（`stack-protector*.ll` 未归类，既有基线红，已登记 `ISS-left-005`） |
| 收尾门控（本任务现跑） | `make check-archive` **rc=0**（M17 册 46 / 流水 46）；`check_archive.py --self-test` **rc=0（14/14）**；`check_issues` **rc=0**（53 open / 28 closed / 81 entries / 4 ledgers）；`check-knowledge-refs` **rc=0**（0 具体 `.work/**`、0 悬空）；`check-milestones-fresh` **rc=2**（M18 `m18-linux-027` 未列入台账，既有基线红，见 MEMORY；非 M17） |

## 4 MEMORY 摘录（M17 时期）

| 项目 | 状态 |
|---|---|
| 定位 | M17 = **IDL 可执行参考模型 + 四方差分**（IDL / QEMU / gem5 / RTL），**golden = IDL**；执行器用 Python（不依赖 Ruby/`idlc`） |
| 差分口径 | 底座 `tests/inst` **274** 镜像（Kaiwu-Tiny）；判据 = 签名槽 + 退出码四方一致；trace 只在红后归因；picolibc/embench 只抽样 |
| 交付 | 阶段一非 FP 222 镜像（`m17-idl-005`–`009`）、阶段二 FP 50 镜像（`013`）、逐指令 trace（`004`/`022`/`024`/`025`）、cfx 权限轴（`020`） |
| 关键裁定 | 权限编码扁平位图（ADR-0062，删 `[39]`/`[57]`）；`opcodes.yaml` 单一写者（ADR-0063）；RegRAS 统一环形缓冲（`phys(i)=1+((base+i)%63)`）；计数严格相等；Tiny `DIV-18` 用逐槽例外（不造假常量、不跳过）；多 hart 不在范围 |
| 门控 | `check-idl` 进 L2（IDL+QEMU）；`check-idl-full` 为 nightly 成员（全四方）；`check-idl-parse` / `check-idl-exec-anchor` / `check-opcodes-repro` 进 L1；`check-inst-sig` 退役（`check-idl` 为超集） |
| 基线红 | L1 `check-patch-tree` 的 linux/musl 52 problem（`ISS-left-004`）；L3 `unit:full`/`tset:m6` 的 `stack-protector*.ll` 未归类（`ISS-left-005`）；两者均非 M17 引入 |
| 归档 | `.tao/archive/M17/`（2026-11-27，`m17-integ-001`） |

## 5 指针

- 里程碑定义/达成：`.tao/knowledge/milestones-m18.md`–`milestones-m20.md`（活台账；M17 台账已随本归档删除）
- 里程碑回顾：本目录 `m17-retrospective.md`
- 关闭 issue 快照：本目录 `issues-closed.md`（21 条；`tools/infra/archive_issues.py --verify` 可复核）
- 遗留台账：`.tao/knowledge/issues-left.yaml`（含 `ISS-left-004/005`）、`discussing.md`
- 归档规范：`docs/Process-04-里程碑归档规范.md`；门控：`tools/infra/check_archive.py`
