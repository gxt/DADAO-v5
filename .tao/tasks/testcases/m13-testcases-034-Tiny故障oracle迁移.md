# m13-testcases-034: Tiny `expected_fault` oracle 迁到 hmon 分派口径

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m12-chipyard-019`（已完成）；与 `m13-qemu-011` **同批合入**
**可并行分片**：否（`tests/inst` 串行）
**预估**：2–3 h
**状态**：待开始

## 用户裁定（2026-11-13，渠道 = 主会话问答）

> 选 ①：把依赖「hmon 向量不可达 ⇒ 机器 fault」的 44 例 Tiny oracle 迁到新口径，再删 legacy 窗口。

## 目标

`tests/inst` Tiny 子集中依赖「向量不可达 ⇒ 机器 fault」的 `expected_fault` 用例（现场核数，任务书写 44 例中 43 例）改为**经 hmon 分派**的期望（异常码/退出码按 `Machine-v5 §4.4` + `DADAO-13` 现场口径），不再依赖 `-bios` legacy 窗口。

## 范围

- `tests/inst/**` 相关 YAML/`.S` 的 `expected_fault` 期望值（只改口径，不改用例意图）。
- `tools/testcases/**` 中 Tiny 故障判定逻辑（若以「退出码 0xFC/0xF1 等机器 fault」写死）。
- 不改 QEMU 实现（归 `m13-qemu-011`）、不改 spec。

## 验收

1. 现场枚举依赖旧口径的用例（脚本列出 id + 旧期望），迁移后清单为空。
2. `check-inst` Tiny 子集 rc=0（与 `m13-qemu-011` 同批）；`check-tests-index`/`check-case-ledger`/`validate_vectors` rc=0；273 md5 不变。
3. 三平台（chipyard/qemu/gem5）对迁移后的故障例**逐例一致**（同异常码）。
4. ≥1 路注入（改回旧期望）⇒ 三平台同点号红；`cp`+md5 还原回绿。
5. 完成区 ≤30 行；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 worktree；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git；禁止重建组件。
3. 完成区与真实输出逐条对齐；计数现场统计。
4. 需语义裁定写「待裁定」返回。
5. 禁 `git checkout/restore/stash`；用 `cp`+md5。

## 待裁定

（实现中写。）

## 审阅记录

（待填）
