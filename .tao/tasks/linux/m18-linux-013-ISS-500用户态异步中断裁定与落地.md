# m18-linux-013: ISS-500 用户态异步中断行为裁定与落地

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-003`、`m18-linux-004`（K6 与用户入口现状）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；含裁定落地与回归，取 1.5–2× 中位）
**档位**：中改（异常投递行为 + 文档/契约口径）
**状态**：待开始
**执行环境**：本地（QEMU system）

## 背景

`ISS-500`【P2】（`m18-linux-004` 收尾登记）：K6 之后用户态**不再接收任何异步中断**——`dadao_enter_user()` 把 `cfx_umon` user 行写 `~0`，全仓无第二处写回；长用户态窗口内同源事件按契约合并为一次补投 ⇒ `jiffies` 滞后。K6 无用户态可观测面（busybox 无 `date`/`sleep`/`time`、无 `/proc`），当次可接受，但属**行为变化待追认**。另：`dadao_user_entry_install()` 注释仍称「用户态投递」已成死代码；`dadao_user_fault_return` 在 `enter_from_user_mode()` 前开中断（与上游顺序相反，本配置无断言）；F2/F3：changelog `12/12` 应为 `checks=11`、`2/150`/`4/150`/实测 `3/150` 数字不一致。

## 待裁定（执行前必须由用户选择）

- **A 追认现状**：用户态不接收异步中断是有意设计（进入/退出边界补投）。改文档/注释/口径使其自洽；若涉及 `contract-*` 语义变更，按 `AGENTS.md §1` 停下等用户确认。
- **B 恢复投递**：改为「用户态可投递 + 入口安全栈/按任务帧」，恢复异步事件在用户态的可见性；需补可观测证据（长用户态窗口 `jiffies` 推进或等价事件）。

## 目标（按裁定分支落地）

1. 裁定结论落盘（`discussing.md` 或 ADR，按判据），并写明理由与否决项。
2. 按分支改实现/文档/注释；不改无关语义。
3. 补可 FAIL 的断言：A 分支断言「进入用户态屏蔽、回内核补投」；B 分支断言「用户态长窗口内异步事件可见且不破坏入口栈」。
4. 订正 F2/F3 的数字不一致（`checks=11`、注入次数与实测一致）。

## 验收（逐条贴真实 rc）

1. 裁定落盘，含用户选择与理由；实现/文档与裁定一致。
2. A 分支：K6 长脚本仍 27 条通过、`check-linux-k6` rc=0；补投行为有断言与注入（屏蔽点被去掉 ⇒ 判红）。
3. B 分支：用户态长窗口可观测到异步事件（`jiffies` 或等价），无 `die-no-vma`/panic；K6/K5 回归绿；注入回退 ⇒ 判红。
4. F2/F3 数字订正，证据脚本标签与实况一致。
5. 不回归：`check-linux-k5`、`check-linux-k6` rc=0；`check-config-pins`、`check-patch-tree`（linux 段 0 problem）、`check-component-changelog`、`check-knowledge-refs` rc=0。
6. `ISS-500` 关闭；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（最小）、`components/linux/changelog.md`、`tests/unit/linux/**`、`tools/linux/**`、`docs/Process-07*.md`（仅 F2/F3 数字）、`.tao/knowledge/issues.yaml`、本任务书。
3. **不改** `spec/`、`.tao/contracts/`（语义变更须用户确认后另立）；不改版本号。
4. 组件补丁经 `make_patch.py linux` 重导；术语「bank = 寄存器组」；大端/64 KiB 页口径按 `MEMORY.md`。
5. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
