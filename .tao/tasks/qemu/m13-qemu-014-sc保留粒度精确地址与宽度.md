# m13-qemu-014: `sc` 保留粒度改为「精确地址 + 访问宽度」（严格按 spec）

**模块**：qemu
**项目里程碑**：M13
**依赖**：无
**可并行分片**：否（改 `target/dadao/` 的 LR/SC 路径）
**预估**：2–3 h
**状态**：待开始

## 用户裁定（2026-11-14，原话）

> 「ISS-435：严格按spec来」

- 落地含义：保留标记粒度 = **精确地址 + 访问宽度**（`spec/SimRISC-12 §1`「保留机制」段原文：以 `lr` 的地址与 `.b`/`.w`/`.t`/`.o` 宽度为键；**不按 cache line 扩大，也不因不同地址或不同宽度的访问清除**）。
- 同一裁定也覆盖 chipyard（`m13-chipyard-002`，RTL 侧）与测试（`m13-testcases-037`，把探针升为正式向量）；gem5 已合规，无需改。

## 现状（现场，`m13-testcases-028` 实测）

- QEMU 现按 **8 字节对齐字 + 整字值 CAS** 实现（`target/dadao/cpu.h` 的 `lock_addr`/`lock_val` + `translate.c` 的 `gen_lr`/`gen_sc`）⇒ `lr.b [A]` 后另一处写 `[A+1]`（同字异址）会因**字值改变**而让 `sc.b [A]` 失败（返回 1）。
- spec 要求的清除事件只有：**另一 hart 对同一精确地址、相同访问宽度的 store**、当前 hart 执行另一条 `lr`、异常/中断进入（`sc` 自身成败都清）。
- 实测差异：`probe_gran.S` 同 ELF，`rc {chipyard: 2, qemu: 1, gem5: 0}`（gem5 三点全过）。

## 目标

1. 保留记录改为 **(精确地址, 访问宽度)** 二元键：`lr.<w>` 记 `{addr, w}`；`sc.<w>` 仅当 `addr`/`w` 与记录**逐位相等**时成功（返回 0），否则失败（返回 1）；成败都清除记录。
2. **删除整字值比较**（`lock_val` 及 CAS 路径）：同字异址、同字同址不同宽度、同 hart 对邻居字节的写入**都不得**使 `sc` 失败。
3. 清除事件严格按 spec：另一条 `lr`（同 hart）、异常/中断进入、`sc` 自身。**同一 hart 的普通 store 不清除**（spec 未列；多 hart 场景属 GAP，见下）。
4. `sc` 的 `rdHB` 结果方向与 MALIGN 检查不变（成功 0、失败 1；`rdHB=rd0 ⇒ ILLI`）。

## 验收（逐条贴真实 rc）

1. **反例复现（改前正证）**：用改前二进制跑 `probe_gran.S` 等价的 3 点探针 ⇒ 点 1（同字异址）**红**（`sc` 返回 1）；贴真实输出与二进制 md5。
2. **改后**：点 1 转绿（`sc` 返回 0）；点 2（同 hart 改同字另一字节）绿；点 3（同精确地址同宽度写后 `sc`）按 spec 仍为「同 hart 写不清除」⇒ `sc` 成功（若你判断该点应失败，停下写「待裁定」，不要私自改口径）。
3. **既有 `lr`/`sc` 用例全绿**：`tests/inst/12-misc/` 的 24 个原子 id 三平台（chipyard/qemu/gem5）逐字节；`check-inst` 红集**不扩大**。
4. 探针 `probe_gran.S` 的 5 个观测点（同字异址 / 同字另一字节 / 同地址同宽度 / 另一条 lr 后 / 异常进入后）逐点给 QEMU 实测值与 spec 期望的对照表。
5. 补丁 `make_patch.py qemu` 导出；`check_qemu_trans` 264/264；`check-patch-tree` qemu 段 0 问题；`--source-state` qemu OK；`check-component-changelog` rc=0（M13 一条）。
6. ≥2 路可达 FAIL 注入 + `cp`+md5 还原。
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账；`**状态**` → `待验收`；不改台账/`discussing.md`。

## GAP（不伪造，写进完成区）

- **多 hart 对同一精确地址+宽度 store 的清除**：Tiny 当前单 hart，无观测载体 ⇒ 只写实现（记录键 + 清除时机），不造用例。
- 宿主线程级真并发（TCG 多线程）不可达 ⇒ 以功能语义为准。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host` / `check-modules` / 真 `build-chipyard`**；`build-qemu` 可（先 `pgrep -af "build-qemu|install-host|build-gem5|build-chipyard"` 确认无并发写者）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `target/dadao/{cpu.h,translate.c}`（必要时 `helper.c` 的清除点）+ `components/qemu/patches/**` + `components/qemu/changelog.md`；**不改** `spec/`、`contracts/`、`tests/**`。
5. 大文件落 `/tmp/opencode/m13-qemu-014/` 并测完即删。

## 待裁定

（实现中写）

## 审阅记录

（待填）
