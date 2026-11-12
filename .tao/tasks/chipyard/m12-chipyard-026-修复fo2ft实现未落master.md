# m12-chipyard-026: 修复 `fo2ft` 实现未落 master（补丁与源树不一致）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-025`（已验证，但实现未合入）+ `m13-testcases-011`（待验收，其 chipyard 侧依赖本修复）
**可并行分片**：否（单组件单写者）
**状态**：待开始

## 事故（`ISS-405`，P1）

`m12-chipyard-025` 的**实现改动没有进入 master**：合入提交 `be447dbc` 只含任务书（`1 file changed, 54 insertions(+), 23 deletions(-)`）。

后果：

- 仓库内 `components/chipyard/patches/.../WumingFP.scala.patch` **仍含 5 处 `forceInfOnOverflow`**（`fo2ft` 传 `true` ⇒ 恒 ±Inf），而**共享源树 `.work/source/chipyard` 里是 0 处**（已是新逻辑：`common_overflow = (sRoundedExp >> (outExpWidth-1) >= 3)`）
- 即 **仓库补丁 ≠ 实际源树**；fresh checkout 重建会在 14 格上红；`check-patch-tree` 的 chipyard 4 条红正源于此
- 丢失的还有：`tools/chipyard/fp_ref.py` 的 `f2f_exact` 去 force-inf、`fp_sweep.py` / `fp_unit/unit_run.py` 的口径、`README`/`changelog` 条目

**根因**：上一轮把改动写进了共享源树与主工作树而非任务 worktree（`ISS-402`）；主会话合入时只带了任务书，随后 `git worktree remove --force` 销毁了 worktree 内未提交的实现文件。

## 目标

1. **以共享源树为准重新导出 chipyard 补丁**：`python3 tools/infra/make_patch.py chipyard`（源树当前 clean @ `89b7f9a`，含正确实现）。导出后 `grep -c forceInfOnOverflow` 于 `WumingFP.scala.patch` 必须为 **0**。
2. **恢复模型侧**：`tools/chipyard/fp_ref.py` 的 `f2f_exact` 去掉「恒 ±Inf」覆盖；`fp_sweep.py` / `fp_unit/unit_run.py` 的 `force_inf_on_overflow` 默认 False（与 `m13-testcases-011` 已改的两处保持一致，避免两边打架——**先看该分支的改法**）。
3. **`components/chipyard/{README,changelog}.md`** 补本任务与 025 的条目。
4. **验证**：
   - `check-patch-tree` rc=0（chipyard 子集 0 错误）
   - `check-source-state` rc=0
   - `apply-series` 后源树内容 == 导出补丁（幂等）
   - 单元台 `fo2ft ovf` 40 例三方 0 差（`force_inf` 关闭后）
   - 核上 `cvt_ff_ovf` **38 例**（18 severe + 4 轻微 + 10 中点 + 8 动态）mismatch 0
   - 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
   - L2 rc=0
5. **可达 FAIL 注入**：把 `WumingFP.scala` 的溢出判定改回「恒 ±Inf」⇒ 至少 RTZ 正/负、RDN 正、RUP 负 4 格红 ⇒ `cp`+md5 还原回绿。

## 硬约束（子代理必读）

1. **必须在独立 worktree 内作业**（`/tmp/opencode/m12-chipyard-026`，分支同名），**禁改主工作树**；**所有改动必须落在该 worktree 内**，结束贴**该 worktree 的** `git status -uall`。
2. **禁止 `git reset --hard` / `checkout -- .`**（`ISS-402`）；需要干净树重放就另建 `-verify` 临时树。
3. 不提交 git（提交权归 architect）。
4. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值（`ISS-388`/`ISS-391`）。
5. 失败保留现场并继续推进；需要裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 命令作用域 = workdir（仓库根），用相对路径。

## 说明

- 共享源树 `.work/source/chipyard` 是**当前唯一可信的实现来源**（已含 025 的新逻辑），不要重置它。
- 若 `make_patch` 导出导致大量无关补丁变动（行号漂移），**如实记录数量**，并确认其中「实质变化」只有 `WumingFP.scala.patch` / `WumingFPUnitHarness.scala.patch`。

## 审阅记录

（待填）
