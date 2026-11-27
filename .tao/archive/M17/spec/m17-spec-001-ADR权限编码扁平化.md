# m17-spec-001: ADR-0062——权限异常编码扁平化（设计 + 影响清单）

**模块**：spec
**项目里程碑**：M17
**依赖**：无（本任务只写 ADR 与影响清单，不改 spec 正文）
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-24 裁定）

现行 `ADR-0056 D2` 把异常原因编码为「低 16 位 cause one-hot + wyde 子原因」，PTW 权限/访存故障挂在 `CFXPERM`/`CFXMEM` 下。用户裁定改为**扁平位图**、两类权限正交：

- PTW 权限拒绝 ⇒ 只置 `[32..38]` 之一（HSJU / R/W/X），**`CFXPERM` = 0**；
- PTW 访存/页缺失 ⇒ 只置 `[48..55]` 之一或 `[56] ADWBFAIL`，**`CFXMEM` = 0**；
- `CFXPERM`（`1<<7`）**只**表示 cfx 来源掩码拒绝；`CFXMEM`（`1<<1`）**只**表示非 PTW 的核内访存故障；
- **删除** `[39] NCFXPERM` 与 `[57] NONPTW`；
- **不新增任何 cause 位**（现有 11 个 cause 已覆盖全部异常）。

## 要做

1. 新增 `.tao/adr/adr-0062-*.md`（编号 0062；`ADR-0056` 的 **D2/D3 + D4** 标「由 0062 取代/修订」，不删原文）：
   - 决策 D1 扁平位图模型（64 位 `excp_cause_id` 直接给出原因；高位位图可在低 16 位 cause 为 0 时独立成立）；
   - D2 两类权限正交（cfx 来源掩码 vs PTW）；
   - D3 删除 `[39]`/`[57]`，`CFXPERM`/`CFXMEM` 仅保留各自单一含义；
   - D4 `cause_info` 口径（cfx 掩码 = 指令地址；非 PTW 访存 = 访问地址；PTW 权限/缺失 = 访问 VA；`ADWBFAIL` = PTE PA）；
   - D5 影响面与迁移顺序（spec/contract → QEMU → gem5 → RTL → IDL → 测试 → Linux）；
   - **明确未定**：PTW 故障的 monitor 路由与退出码（Tiny 无 PTW；属 Vast，待用户裁定）。
2. 影响清单（落 ADR 附录或任务书）：逐文件列出需改的 spec/contract 段落（§2.2.6 第 6/7 步、§3.6 两张 wyde 表、§4.1 各行、contract-see §6.1/§6.1.1、contract-tlb TLB-34/41）与平台/测试/内核文件。
3. **不改** `spec/`、`contracts/` 正文，不升版本号（正文改动归 `m17-spec-002`）。

## 不做

- 不改 QEMU/gem5/RTL/IDL/测试/Linux；
- 不裁定 Vast 路由与退出码（写进 ADR 的「未定」）。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只新增 ADR + 本任务书；完成区 ≤30 行。

## 验证

1. ADR 文件存在、状态 `Candidate`（decision 逐条待用户确认后才可 `Accepted`）；
2. 影响清单里每个候选文件都用 `grep` 现场核实存在（禁凭记忆）；
3. **可达 FAIL**：把 ADR 里「删除 `[39]`」一句删掉 ⇒ 任务书的核对脚本（grep 关键词）红；`cp`+md5 还原回绿；
4. 不产生任何 spec/contract 改动（`git status` 只含 ADR 与任务书）。

## 待裁定（交用户）

1. Vast 的 PTW 故障 monitor 路由（smon/umon？按什么位选？）与退出码（Vast 是否沿用 `0xF0|index`）；
2. spec/contract 是否允许升版（`DADAO-12` 与 `contract-see` 当前版本段）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-24，自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 初稿写「8 个校验器」为定数，违规（计数须现场派生） | ✅已修 | 改「各校验器」并指向附录 A21–A29 | 全文 grep 无「8 个校验器」；run.sh 影响清单 53 条现场计数 |
| `iss-469` 大小写不符仓库规范 | ✅已修 | 头部关联改 `ISS-469` | grep `ISS-469` 命中 1 |
| Consequences 写「约 20 处段落」（估算值） | ✅已修 | 改列章节名 + 指向 A1 逐处行号 | ADR L91 |
| Context 第 3 条「是否定位」笔误、表意不清 | ✅已修 | 改「是「否定位」」 | ADR L13 |
| D4 粗口径（cfx 掩码 = 指令地址）与原 0056 D4 三形态（cfxmem 轴 = 访存地址、cfxexe = 目标 IP）不完全一致 | ⏸延后 | 不自行改口径；列 ADR「未定 3」（非阻塞，待 002 定稿） | ADR L65/L100 |
| 注入自检初版只验单条 grep，未验「全量套件转红」 | ✅已修 | `--inject` 增加：注入后跑完整 suite 要求 rc≠0 且红点 = 目标检查 | `inject-suite.log` 红点 1（目标关键词），其余 72 绿 |
| spec/DADAO-12 §5.2 与 contract-see §6.1 仍写「`[31:16]` 保留」，与 2026-11-23 异步 cause 17/18 裁定不一致 | ⏸延后 | 超出本任务（只写 ADR），记入完成区「新发现」，建议 002 订正 | 两处原文照旧（本任务不改正文） |

判决：无未修 finding（2 条 ⏸ 均属「需用户/后续任务裁定」，已在 ADR「未定」与完成区留痕）。

### 第 1 轮 reviewer 复核（2026-11-24，独立重跑）

**重跑记录**（worktree 根执行运行期证据目录内的 `run.sh`）：全量 `rc=0`，`PASS=73 FAIL=0`；**独立注入**（当前版 ADR，md5 `7676a787`→`333ce9f9`→还原 `7676a787`）：删 D3 句后关键词 `rc=1`、全量套件 `rc=1` 且**红点恰 1 条**（目标关键词）/其余 72 绿，`cp`+md5 还原一致，回绿 `rc=0`；注入后 `git status -uall` 仍仅 ADR + 任务书。
**约束核验**：① D1–D5 与用户裁定逐条一致（扁平位图；PTW 权限仅置 `[32..38]` 且 `CFXPERM`=0；PTW 访存仅置 `[48..56]` 且 `CFXMEM`=0；删 `[39]`/`[57]`；不新增 cause；两类权限正交；D4 四口径 `cause_info`）✅；② 影响清单：脚本 53 对全绿，我另**现场抽 27 条目**（spec/contract/QEMU/gem5/RTL/IDL/测试/Linux 八类，含行号）与附录 A 逐条相符（如 DADAO-12 L297、contract-see L96/L124/L134、cpu.h L346、fs_machine.hh L84/L96、GewuFile L164/L176、idl_exec L88、check_ptw_regs L9、cause-sub.h L72、fault.c L947）✅；③ `git diff HEAD -- spec .tao/contracts contracts` = 0 行；`adr-0056` diff 空、无 0062 注记（注记只在 0062 头部）✅；④ 未定 4 条齐（Vast 路由/退出码/版本号/`cause_info` 细分），checker 解析 0056 作 oracle 的迁移写在 Consequences「校验器改指」✅；⑤ `git status -uall` 仅 ADR + 任务书 ✅；⑥ 完成区 12 行 ≤30、全文无「银行」。

| # | finding | 分档 | 处置 |
|---|---------|------|------|
| 1 | 完成区「新发现 4」与自审表第 7 行称「`[31:16]` 保留与 2026-11-23 异步 cause 17/18 裁定不一致」——经核 `adr-0061`（Accepted 2026-11-23）已**取消** `1<<17`/`1<<18` 宏 cause、异步源不占 `excp_cause_id`，正文 `[31:16]` 保留与 0061 **一致**；真正过时的是 `DADAO-12` 变更记录 L1112（属 0061 落地面，非本任务） | 文档级 | architect 收尾改措辞 |
| 2 | 任务书 L23 称取代范围「D2/D4」，ADR 头部写「D2/D3 + D4」；0056 实际 D3 = 位分配表（`[39]`/`[57]` 所在），ADR 口径更准 | 文档级 | 不阻断，收尾对齐措辞 |
| 3 | 工程师注入备份 `175fa0ce…` ≠ 当前 ADR `7676a787…`（其自检跑于 4 处 self 审修复**之前**，完成区 md5 描述对应旧版） | 证据时序 | 已由我独立注入复验通过，不阻断 |

**判决：Accepted**（验收命令块在我自己的重跑下全绿，硬约束无违反；3 条均为文档级 finding，按裁定不阻断，交 architect 收尾修订）

### 第 2 轮 engineer 收尾（2026-11-24，按用户补充裁定 + reviewer finding）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1-1 完成区「新发现 4」/自审表第 7 行把「`[31:16]` 保留」说成与 0061 不一致（过时） | ✅已修 | 第 1 轮表第 7 行保留为历史记录（以本轮为准）；完成区「新发现 4」重写：`[31:16]` 保留与 `ADR-0061` 一致（宏 cause `1<<17`/`1<<18` 已取消）；过时的是 `DADAO-12` 变更记录 L1112（仍记 17/18 宏 cause，属 0061 落地面） | `grep -n "1<<17\|1<<18"` DADAO-12 → L1112 |
| R1-2 取代范围措辞 | ✅已修 | 本任务书 L23 改「D2/D3 + D4」（ADR 头部原本即此口径） | ADR 头部 L5；本文件 L23 |
| R1-3 完成区 md5 与自检时序不符 | ✅已修 | 完成区改记**收尾后** ADR md5 并注明「自检跑于收尾改稿之后、收尾前版本 md5 为历史值」 | 收尾后重跑 `run.sh`（77 PASS）+ 注入链路 md5 对账 |
| 用户裁定：补 D6（Vast 路由 + 退出码）、版本口径、未定收敛 | ✅已修 | ADR 新增 D6；新增「已定」段（路由/退出码/版本号「不升号、`contract-tlb` 不设版本号」）；「未定」由 4 条收敛为 1 条（`cause_info` 细分）；状态改 `Accepted`（2026-11-24） | run.sh 新增 D6/已定/未定=1/`不设版本号` 断言，全绿 |

判决：无未修 finding（R1-1/R1-3 已按 reviewer 结论订正，R1-2 为措辞对齐）。



## 完成区

**测试结果**：收尾改稿后重跑 `bash /tmp/opencode/m17-spec-001/run.sh` → **PASS=77 FAIL=0**（rc=0）；`--inject`：删 D3 行 ⇒ suite rc=1、红点恰 1（目标关键词）/其余 76 绿 ⇒ `cp`+md5 还原（`542cc94a…` → `5910c83c…` → `542cc94a…`）⇒ 回绿 rc=0。**ADR 当前 md5 = `542cc94a140b735dadd8961d2862a409`**（收尾前旧版为 `175fa0ce…`/`7676a787…`，那两次自检跑于本轮改稿**之前**，已由本轮重跑覆盖）。
**修改文件**：`.tao/adr/adr-0062-flat-cause-bitmap.md`（D6 + 已定/未定 + 状态 `Accepted` + 版本口径）、本任务书（措辞 + 第 2 轮记录 + 完成区）；证据脚本在任务 worktree 外 `/tmp/opencode/m17-spec-001/run.sh`（用户指定位置）。
**验收结果**：ADR `**状态**：Accepted`（2026-11-24）、D1–D6、「已定」3 条（路由 / 退出码 / 版本号不升且 `contract-tlb` 不设版本号）、「未定」1 条、附录 A 影响清单 32 条；`git diff $BASE -- spec .tao/contracts contracts` 为空；ADR-0056 原文未改；contract-see `[39]`/`[57]` 仍在；`git status` 仅两文件。
**新发现/坑**：
1. 现有校验器（`check_ptw_regs`/`check_ptw_walk`/`check_ptw_tlb`/`check_mode_entry`/`check_causeid`/`check_vastdcache`/`k4_cow_probe` 等）现场解析 `adr-0056` 位表当 oracle ⇒ 0062 落地时必须改指 `contract-see`/`ADR-0062`。
2. 退出码冲突已由 **D6** 落定：Vast 不沿用 `0xF0|bit3:0`（Tiny 专有），PTW 故障测试直接读 `cause_id`；`m17-spec-002` 改正文时须同步 `contract-tlb TLB-36` 与 `Kaiwu §7.1` 的**适用范围**（不是删码表）。
3. 0056 D4 的 `CFXPERM.info` 实有三形态（页表/`cfxmem` 轴 = 访存地址、`cfxexe` = 目标 IP、`cfxtrap`/`cfxreg` = 指令地址），与 D4 粗口径（cfx 掩码 = 指令地址）不同 ⇒ 保留为**未定 1 条**（非阻塞）。
4. `[31:16]` **保留与 `ADR-0061` 一致**（宏 cause `1<<17`/`1<<18` 已取消、异步源不占 `excp_cause_id`）；真正过时的是 `DADAO-12` 变更记录 **L1112**（仍记 `TIMER=1<<17`/`PMEM_DMA=1<<18` 宏 cause），属 `ADR-0061` 落地面、非本任务（`contract-see §7` 2026-11-23 同口径一条宜一并核）。
**遗留问题**：未定 1 条（D4 `cause_info` 细分）待用户裁定；ADR-0056 顶部「已被 0062 取代」注记待另立任务（本任务禁改其原文）；spec/contract 正文与 `contract-tlb` 版本段删除归 `m17-spec-002`。
