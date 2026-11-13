# m14-spec-004: `contract-syscall` 内核入口口径补写（放行/自配）

**模块**：spec
**项目里程碑**：M14
**依赖**：`m14-spec-002`（已合入，契约 0.10.0）
**可并行分片**：否（单文件契约）
**预估**：2–3 h
**状态**：已验证

## 用户裁定（2026-11-13，渠道 = 主会话问答）

> ① 固件**只放行源位/deleg**、入口寄存器由**内核自配**；② `excp_cause_info` 与 `immu18` 的关系**只在合约推导**、不补上游；③ `clone` 双返回 / `execve` 清 `rbtp` **留 contract-syscall §10**，由 musl 移植任务实现并校准。

## 目标

把上述三条落进 `.tao/contracts/contract-syscall.md`：

1. §8（内核入口）明确「`hmon`/HBI 只放行 `cfx_umon`/`cfx_jmon` 所需源位与 `hypv_cg_reg_deleg`；**入口寄存器由内核自配**」；删去任何「固件代配」的歧义表述。
2. §8 保留 `immu18 = excp_cause_info & 0x3FFFF` 的**推导**写法，标注「上游未明文、按 `SimRISC-00 §3.1` 位段推导」，**不要求改 `DADAO-12`**。
3. §10 明确 `clone` 双返回属**用户态 wrapper（musl）**语义、内核只保证子进程入口返回 0；`execve` 的 `rbtp` 清零由 musl 移植校准（合约只写约束）。

## 验收

1. 上述三点在契约内有明确条款（逐条 grep 可命中）。
2. `check-syscall-abi` / `check-contracts-dir` / `check-contracts-pending` / `check-knowledge-refs` rc=0；**版本号不动**（`contract-syscall` 0.9.2 随 ABI 册；M14 扩展记 §12 变更记录，见 `ISS-423`）。
3. 不改 `spec/`、不改 `contracts/*.yaml`、不改 Makefile。
4. ≥1 路注入可达 FAIL + `cp`+md5 还原。
5. 完成区 ≤30 行；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 worktree；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git。
3. 完成区与真实输出逐条对齐。
4. 需语义裁定写「待裁定」返回。
5. 禁 `git checkout/restore/stash`；用 `cp`+md5。

## 待裁定

（无。三条口径已按用户裁定落入 §8/§10，变更记 §12。）

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-13；自主逐行）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 §8「放行/自配」与同节「内核清来源位」是否矛盾 | ❌不修（不矛盾） | 前者 = 固件清 `cfx_umon`/`cfx_jmon` 的源位 + deleg；后者 = 内核清**目标** cfx（如 `cfx_hmon`）源位，两处对象不同 | §8 两条并存；`check-contracts-pending` rc=0 |
| F2 注入自检是否恒真 | ✅已修 | 注入命中限定 `^- **入口可见状态` 行，改动 `0x3FFFF→0x7FFFF` 后该行检查不命中 | 注入后 actual=0（期望 FAIL）；`cp` 还原 md5 `1b436342…` 一致、回绿 actual=1 |
| F3 `check-knowledge-refs` 红是否本任务引入 | ❌不修（非本任务） | 未改他人任务记录；基线 HEAD 导出树重跑 | 基线/当前违规集逐条相同（2 条，均 `.tao/tasks/infra|spec` 既有记录） |
| F4 §12 存在后版本号是否被 drift 误判 | ✅已修 | 版本头保持 0.9.2，§12 只记 v5 扩展 | `make check-spec-drift` rc=0（0.9.2 == README AEE/ABI） |

判决：本任务 finding 均已处置，标 `待验收`；F3 属仓库既有门控红，移交主会话/architect。

### 第 1 轮 reviewer 验收（2026-11-13，本人重跑；判决只据自身命令输出/退出码）

**重跑记录（worktree 内，命令 → 真实退出码）**：
- `bash .work/evidence/m14-spec-004/run.sh` → **rc=0，21/21 PASS**（`RESULT: PASS`、FAIL=0）。
- `make check-syscall-abi` → rc=0（`80/80 checks passed`）；`make check-contracts-dir` → rc=0（13 md / 7 yaml）；`make check-contracts-pending` → rc=0（现场 4126 行、标记 0）；`make check-spec-drift` → rc=0（contract-syscall `spec-sourced 0.9.2` == README AEE/ABI，错误 0）。
- `make check-knowledge-refs`（本 worktree）→ **rc=2**（脚本 rc=1），违规恰 2 条 = `.tao/tasks/infra/m14-infra-001:157`、`.tao/tasks/spec/m14-spec-003:100`（他任务既有，本任务未触碰）；**主工作树重跑 → rc=0 PASS**（`0 具体 .work/** 引用`，已含 `8929d8ae` 清理）⇒ 红是本分支基线落后于 master，非本任务缺陷，合并后消。
- **独立注入 1 路（自设计，未复用 engineer 路）**：`cp` 备份 md5 `d2ddf0f9bb1c3dd875d5cf7050ddb4d4` → `sed` 把 §8/§12 `**入口寄存器由内核自配**` 改「由固件代配」（残留命中 2）→ `run.sh` **rc=1**、`[FAIL] §8 固件只放行 / 入口寄存器由内核自配(同一条) expected=1 actual=0`（`RESULT: FAIL`、FAIL=1）→ `cp` 还原 md5 `d2ddf0f9…` 相等、`代配` 残留 0 → `run.sh` **rc=0、21/21 PASS**。全程 `cp`+md5，未用 git checkout/restore。

**三条口径**：① §8 同一条内「固件**只放行**源位/deleg + **入口寄存器由内核自配**」，全文无「固件代配」正表述（仅「固件不代写入口寄存器」「不得替内核配置入口」）；② `immu18 = excp_cause_info & 0x3FFFF` 标「本合约内推导、`DADAO-12`/`DADAO-22` 未明文写出、按 `SimRISC-00 §3.1` 位段推导、不要求上游补正」；③ §10 `clone` 双返回属 musl wrapper（内核只保证子入口 `rd8 = 0`、不实现两次返回）、`execve` 的 `rbtp` 清零「实现点由 musl 移植任务校准」。锚定 grep 四式各命中 1 行。

**版本/§12**：版本头 0.9.2 与基线逐字节相同（头 3 行 md5 `584cce74…` == merge-base），全文 `0.10.0` 计数 0；§12 变更记录存在，三小点与本次三条改动逐条对应（含「版本号不改」）。

**越界与快照**：`git diff --name-only $(git merge-base HEAD master)..HEAD` 仅 `.tao/contracts/contract-syscall.md` + 本任务书（2 文件）；`spec/`、`contracts/*.yaml`、`Makefile`、台账、`discussing.md` 0 改动；审查前后 `git status --porcelain -uall` 均为空，契约 md5 审前/注入后/还原后恒 `d2ddf0f9…`。完成区 11 行 ≤30、本轮审阅 ≤40 行。

**发现（文档级，不阻断，architect 收尾订正）**：F-R1 完成区「还原 md5 `1b436342…`」取自早期 `run-final.log`，最终文件（= 提交 blob）为 `d2ddf0f9…`（`run-final2.log` 同值），改此数字即可；F-R2「三点 grep 各命中 1 行」仅对锚定式成立（非锚定 2/1/4/1，因 §7 决策表/§12/附录 A 复述），建议措辞注明锚定。

**采信/未采信**：engineer 自审 F1–F4 的**文字描述**采信，其**复验证据命令**（run.sh 与四门控）已由我本人重跑核对，与完成区数字一致（除 F-R1 md5）。

**判决：Accepted** —— 验收命令块在我自己的重跑下全过、五项约束逐条守住；F-R1/R2 属完成区数字笔误，按文档级 finding 交 architect 收尾订正，不开返工轮。

## 完成区

**测试结果**：一键证据脚本（运行期）rc=0（21/21 PASS，含注入自检）。
**修改文件**：`.tao/contracts/contract-syscall.md`（§7 行 7、§8 两条、§10 三条、新增 §12、附录 A 三行）；本任务书（状态/审阅/完成区）。
**验收结果**：
- 三点 grep（各命中 1 行）：`只放行.*入口寄存器由内核自配` / `immu18 = excp_cause_info & 0x3FFFF.*未明文写出.*SimRISC-00 §3.1` / `` `clone`.*双返回.*musl.*wrapper `` 与 `` `execve`.*rbtp.*musl 移植任务校准 ``。
- `make check-syscall-abi` rc=0（80/80）；`check-contracts-dir` rc=0（13 md / 7 yaml）；`check-contracts-pending` rc=0（4126 行、标记 0）；`check-spec-drift` rc=0（0.9.2 == README 0.9.2）。
- `make check-knowledge-refs` rc=2（脚本 rc=1），但与基线 HEAD 导出树**逐条相同**（2 条既有违规，非本任务引入；主工作树 `05530d60` 同样红）。
- 注入：`0x3FFFF→0x7FFFF` ⇒ 该检查 actual=0（可达 FAIL）；`cp` 还原 md5 `d2ddf0f9bb1c3dd875d5cf7050ddb4d4` 一致、回绿 rc=0。
**新发现/坑**：既有两条已合并任务记录写 `.work/evidence/<任务>/run.sh` 具体路径（违 AGENTS「任务书不写运行期路径」），使 L1 `check-knowledge-refs` 在 master 常态红；本任务不越界改他人审阅记录。
**遗留问题**：`check-knowledge-refs` 清零需 infra 清理（两处改「运行期证据脚本」措辞或 `<>` 占位形），已在证据脚本留基线对比。
