# m14-spec-004: `contract-syscall` 内核入口口径补写（放行/自配）

**模块**：spec
**项目里程碑**：M14
**依赖**：`m14-spec-002`（已合入，契约 0.10.0）
**可并行分片**：否（单文件契约）
**预估**：2–3 h
**状态**：待开始

## 用户裁定（2026-11-13，渠道 = 主会话问答）

> ① 固件**只放行源位/deleg**、入口寄存器由**内核自配**；② `excp_cause_info` 与 `immu18` 的关系**只在合约推导**、不补上游；③ `clone` 双返回 / `execve` 清 `rbtp` **留 contract-syscall §10**，由 musl 移植任务实现并校准。

## 目标

把上述三条落进 `.tao/contracts/contract-syscall.md`：

1. §8（内核入口）明确「`hmon`/HBI 只放行 `cfx_umon`/`cfx_jmon` 所需源位与 `hypv_cg_reg_deleg`；**入口寄存器由内核自配**」；删去任何「固件代配」的歧义表述。
2. §8 保留 `immu18 = excp_cause_info & 0x3FFFF` 的**推导**写法，标注「上游未明文、按 `SimRISC-00 §3.1` 位段推导」，**不要求改 `DADAO-12`**。
3. §10 明确 `clone` 双返回属**用户态 wrapper（musl）**语义、内核只保证子进程入口返回 0；`execve` 的 `rbtp` 清零由 musl 移植校准（合约只写约束）。

## 验收

1. 上述三点在契约内有明确条款（逐条 grep 可命中）。
2. `check-syscall-abi` / `check-contracts-dir` / `check-contracts-pending` / `check-knowledge-refs` rc=0；版本号按契约惯例升位（0.10.0 → 0.10.1）。
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

（实现中写。）

## 审阅记录

（待填）
