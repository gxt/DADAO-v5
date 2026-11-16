# m16-chipyard-001: 周期模型收口复测（M13 收尾后全量重测并更新文档）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：**M13 收尾**（三平台差分矩阵冻结、`07-floating-point` 与 `06-control-flow` 全册完成；预取修复 `m12-chipyard-022` 已在基线内）；`m16-gem5-002…008`（表与接入已就绪）
**可并行分片**：否（chipyard 组件单写者 + 同一测量台）
**预估**：2–3 天（按族分批测量 + 文档回填 + 生成器重跑）
**状态**：待开始

## 背景（用户 2026-11-14 裁定）

`docs/core-wuming-cycle-model.md` 是 wuming 核周期数的**唯一真源**。其数值必须可审计：**权威版本 = M13 收尾后在 chipyard wuming 上全量复测的那一组**；M13 收尾前的数字（`008`–`015` 期）标「暂定/推断/未测」，其中：

- `jump`/`call`/`ret` 的 8/26/15 测于**预取失效期**（`008` 引入、`022` 已修）⇒ 是**上界**；
- `ext`、16 条 FT 侧 FP 族、`trap`/`escape`/`cfx2rd` 等属**推断/未测**；
- 整数乘/除（B1/B2/B3）是**可配/设计值**，从未实测。

现状计数（264 行）：实测 218 / 可配 8 / 设计值 12 / 推断 20 / 未测 6。

## 目标

1. **全量复测** §3 的每一行（按族抽样 ≥2 组操作数，方法沿用 §5：trace 里相邻指令进入 `EXEC` 的拍差，`cycle=` 差值；**不使用估计值或不相关任务的旧数字**）。
2. 把结果回填 §3「周期」列 + §5 实测表（含测量条件、采样数、来源任务），并把「来源」列改为 `实测`；确实无法测的（需 SEE 执行模型者）保留 `未测` 并写明原因与阻塞条件。
3. 重新推导受影响的结论：`jump/call/ret` 的预取修复后值、`ext`、FT 侧 16 条、块传送/多元素宽度分档等。
4. **重跑生成器**：`python3 tools/gem5/gen_wuming_cycles.py` → 更新 `tools/gem5/wuming_cycles.yaml` 与 gem5 源树 `wuming_cycles.{hh,cc}`；按 `docs/Process-01` 重导出 gem5 补丁（`make_patch.py gem5`）。
5. 重跑 `m16-gem5-003/004/008` 的对照证据（表值变了，逐类差异必须仍为 0 或给出归因）。

## 验收

1. §3 **每行**都有「来源」列取值；`推断`/`待实测` 计数降为 **0**（`未测` 仅剩确实需要 SEE 执行模型的行，并逐条写明阻塞）。
2. 每族至少 2 组操作数的实测记录（拍数 + 采样数 + 条件），写进 §5；与旧值不同的行**逐条列出差异与原因**（例：跳转类从 8 降到 X）。
3. `make check-wuming-cycles` 11/11 rc=0；`check-patch-tree` gem5 段 0 问题；`--source-state` gem5 OK；`make_patch gem5` 幂等。
4. gem5 侧：`check-gem5-decode` 694 PASS；`003/004/008` 证据重跑全绿（provisional 行数应大幅减少）。
5. **独立性**：期望值不得从 gem5/QEMU 反推；只从 chipyard wuming 的仿真 trace 取（三平台一致只作旁证，不作真值）。
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前 `git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 不提交 v5 仓库 git；chipyard 组件补丁按 `docs/Process-01` 导出；gem5 补丁重导出后需重建复跑。
3. **构建后必须删 `.classpath_cache/chipyard.jar` 与 `generated-src/<cfg>`** 再 `make verilog`（`m12-chipyard-028` 踩过：不删会静默沿用旧 RTL）；判「新 RTL 真进模拟器」要独立解析生成物。
4. 三平台/节点跑批用**独占 work-dir**（`ISS-431`）；节点 chipyard sim 必须与主控机一致（`ISS-429`，节点无 JDK 不能自建）。
5. 禁 `git checkout/restore/stash`/`git show <commit>:<path>` 还原；注入还原用 `cp`+md5。
6. 大文件落 `/tmp/opencode/m16-chipyard-001/` 并测完即删；日志 `.work/log/chipyard/<任务ID>-<用途>.log`。
7. **不要**改 `spec/`、`contracts/`、`Makefile` 门控集合；`docs/core-wuming-cycle-model.md` 与本任务范围相关，允许改（且是本任务的核心产出）。

## 待裁定

1. **C 类 `ld.*`/`st.*` 拍数（已裁定，用户 2026-11-17 选 ①）**：承认 chipyard 实测 `ld.*`=9、`st.*`=10 为真值；文档 C 行「4–7」记为**外推失效**，回填 9/10、来源改 `实测`。

## 审阅记录

（待填）
