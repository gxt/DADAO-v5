# m17-idl-024: trace 比较改为全 64 槽按值比（删除窗口/来源过滤）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-023`（IDL 执行器环形缓冲）、`m17-idl-022`（现有并集剔除，作对照基线）；四平台统一环形约定（见 023 任务书「统一环形约定」）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-25）

四平台统一改用**环形缓冲 + 隐藏基准**后，同一指令流下物理槽内容（含窗口外残留）也逐槽一致 ⇒ trace 比较**直接比全 64 槽**即可，规则最简单，且能抓「布局漂移」（比只比有效窗口更强）。

现状（`m17-idl-022` 后）：`reg_delta()` 仍按 `RACNT` 有效区过滤、并做「来源槽继承」跳过，比较器按两侧 `skip` 并集剔除——这是在「搬移 vs 环形」混合期的兼容措施；`m17-idl-023` 合入后不再需要。

## 要做

1. `idl/tools/idl_trace_common.py:reg_delta()`：取消 `idx < ra_lo` 的窗口过滤与 `_ra_shift` 来源继承判定，`ra1..ra63` 的值变化**全部**列入 `dst`/`val`（`ra0` 照旧）；
2. 删除 `skip` 字段、并集剔除（`idl_check_trace.py:_without_skip`）与 `TraceWriter` 落盘剔除逻辑；`ra_skips` 统计口径同步删除或置 0（不再有跳过）；
3. `idl/docs/trace-format.md`：E4 改写为「全 64 槽（`ra0` + `ra1..ra63`）按值比；统一环形约定由 `SimRISC-00 §2.4.3` 与各平台实现约定保证（映射 `1+((base+i)%63)`）」；重生成 `trace-sample.jsonl`；
4. 全量 `idl_check_trace` **274/274**。

## 不做

- 不改各平台实现（归 `m16-gem5-027` / `m16-chipyard-033` / `m17-idl-023`）；
- 不改 spec/契约/版本号；不放松 `rd8` 等其它既有等价口径。

## 约束

- 独立 `git worktree`；不提交 git；只动 `idl/tools/{idl_trace_common.py,idl_qemu_trace.py,idl_exec_trace.py,idl_check_trace.py}`、`idl/docs/{trace-format.md,trace-sample.jsonl}`、本任务书；完成区 ≤30 行。

## 验证

1. `grep -c "_ra_shift\|skip"` 在 4 个工具文件 = 0（除文档说明）；全量 trace **274/274**；
2. **可达 FAIL ①**：把执行器侧任一**窗口外**槽的残留值改错 ⇒ 必红（证明真的全比、不再跳过）；`cp`+md5 还原回绿；
3. **可达 FAIL ②**：破坏环形约定（`base` 不推进）⇒ 必红；还原回绿；
4. `--sample-check` 与重生成一致；`make check-idl` 274/274、`check-idl-parse`/`check-spec-refs`/`check-knowledge-refs` rc=0；
5. `git status -uall` 仅允许文件 + 任务书。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
