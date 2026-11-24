# m17-spec-001: ADR-0062——权限异常编码扁平化（设计 + 影响清单）

**模块**：spec
**项目里程碑**：M17
**依赖**：无（本任务只写 ADR 与影响清单，不改 spec 正文）
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-24 裁定）

现行 `ADR-0056 D2` 把异常原因编码为「低 16 位 cause one-hot + wyde 子原因」，PTW 权限/访存故障挂在 `CFXPERM`/`CFXMEM` 下。用户裁定改为**扁平位图**、两类权限正交：

- PTW 权限拒绝 ⇒ 只置 `[32..38]` 之一（HSJU / R/W/X），**`CFXPERM` = 0**；
- PTW 访存/页缺失 ⇒ 只置 `[48..55]` 之一或 `[56] ADWBFAIL`，**`CFXMEM` = 0**；
- `CFXPERM`（`1<<7`）**只**表示 cfx 来源掩码拒绝；`CFXMEM`（`1<<1`）**只**表示非 PTW 的核内访存故障；
- **删除** `[39] NCFXPERM` 与 `[57] NONPTW`；
- **不新增任何 cause 位**（现有 11 个 cause 已覆盖全部异常）。

## 要做

1. 新增 `.tao/adr/adr-0062-*.md`（编号 0062；`ADR-0056` 的 D2/D4 标「由 0062 取代/修订」，不删原文）：
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

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
