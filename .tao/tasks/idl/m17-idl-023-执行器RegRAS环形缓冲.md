# m17-idl-023: IDL 执行器 RegRAS 改环形缓冲（去搬移）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m18-idl-002`（已合入 `5c6c7e16`）、`m17-idl-022`（已合入 `fe706925`）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-25）

`spec/SimRISC-00 §2.4.3` / `ADR-0012 D7.5` 允许并推荐**环形缓冲 + 隐藏基准索引**；用户确认 IDL/gem5/RTL 都不应使用搬移（性能与口径一致）。

现状：`idl/tools/idl_exec.py` 的 `_ras_entries()` / `_ras_store()` / `ras_push()` / `ras_pop()` 每次把有效窗口 `ra[64−RACNT..63]` 整体重排（`ld.o_rrii_ra` 等用例下重排量大）。QEMU 的 `ras_base` + `ra_phys()` 是参考实现。

## 统一环形约定（硬约束；用户 2026-11-25）

四平台必须用**同一套**隐藏布局，否则「全 64 槽按值比」会因窗口外残留不同而假红：

- 物理槽：`0` = `ra0` 元数据（`{SBZ,RACNT,MRPTR}`，不占窗口），`1..63` = 环形数据槽；
- 映射：`phys(i) = 1 + ((base + i) % 63)`，`i ∈ 1..63`；`base` 为 6 位隐藏基准（0..62，复位 0，不可架构访问）；
- 推进方向与 QEMU `ra_phys()` 一致：`call` 压栈 `base += 1`、`ret` 弹栈 `base −= 1`（模 63），写入/读出均经映射；
- 架构视图（`ld.o-ra`/`st.o-ra`/`rd2ra`/`ra2rd` 与 trace/`-d cpu` 导出）一律按映射换算。

## 要做

1. 引入隐藏基准 `ras_base`（0..62，非架构状态，复位 0）与逻辑→物理映射（`1 + (ras_base + i) % 63`；`ra0` 不占槽）；
2. **所有** RA 架构访问走映射：`banks["ra"]` 的读写点（`_set_racnt`/`_set_mrptr` 之外）、`ld.o-ra`/`st.o-ra`、`rd2ra`/`ra2rd`、C3b 溢出源、trace/快照导出；
3. `ras_push`/`ras_pop`：C1/C3a/D3 改为「写一个槽 + 基准 ±1」，删除整体重排；C2/C3b/D2/D4b 判定与提交顺序、精确异常不变；
4. 对外观测（trace 的 `banks`、`--dump`）仍为**逻辑视图**，与改前逐例一致；
5. 复跑 `check-idl`（IDL+QEMU 274）、`check-idl-parse`、`check-idl-exec-anchor`；`.idl` 文件不改。

## 不做

- 不改 `.idl` 语义库/契约/spec/版本号（`check-idl-exec-anchor` 锁不动）；
- 不改 QEMU/gem5/RTL；不改 trace 比较器（归 `m17-idl-022`）。

## 约束

- 独立 `git worktree`；不提交 git；只动 `idl/tools/idl_exec.py`（必要时 `idl/data/exec_anchor.toml` 不动）+ 本任务书；完成区 ≤30 行。

## 验证

1. `check-idl` 274/274、`check-idl-parse` rc=0、`check-idl-exec-anchor` 无 `--update` 通过；
2. **可达 FAIL ①**：D3 不前进基准 ⇒ RAS 相关用例签名槽红；`cp`+md5 还原回绿；
3. **可达 FAIL ②**：映射写成 `% 62` ⇒ 溢出/回绕用例红；还原回绿；
4. 改前/改后同一批用例 trace 逐条一致（逻辑视图不变）；
5. `git status -uall` 仅允许文件 + 任务书。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
