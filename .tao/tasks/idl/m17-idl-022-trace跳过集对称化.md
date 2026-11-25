# m17-idl-022: trace「跳过集」两侧对称化（关闭 `ISS-537`）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-004`（trace 比较器）、`m17-idl-021`（复核遗留）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（`ISS-537`，用户 2026-11-25 指示「立任务修掉」）

`python3 idl/tools/idl_check_trace.py` 全量 **273/274**：唯一红是 `ld.o_rrii_ra` 第 205 条（pc `0x0000ffffff01071c`），只差 `dst` 字段：

- exec 侧：`ra0,ra1,ra2,ra4,ra5,ra6,ra7,ra8,ra61,ra62,ra63`
- QEMU 侧：`ra0,ra1,ra2,ra3,ra4,ra6,ra7,ra8,ra9,ra10,ra62,ra63`

**根因不是平台语义分歧**，而是比较器的 E4 判定**逐侧独立**：

- `spec/SimRISC-00 §2.4`：`ra1..ra63` 只有 `RACNT` 有效区内（`ra[64−RACNT..63]`）是架构可见的，有效区外内容未定义；
- `idl/tools/idl_trace_common.py:reg_delta()` 用**每侧各自维护**的 `ra_ok` 集合决定「这个条目内容来源未定义 ⇒ 不列入 `dst`」；QEMU 与执行器的物理布局不同（环形缓冲 vs 搬移），同一逻辑状态下「来源未定义」的条目集合不同；
- 于是两侧用**不同规则**过滤同一字段，再逐字比较，必然假红（该例 `ra_skip=2131`）。

## 要做

1. `reg_delta()` 把「被跳过」的 RA 条目**名字**一并返回（当前只返回计数）；`ra_skips` 统计口径保持为条目数；
2. QEMU 侧派生（`idl_qemu_trace.py:derive_trace`）与执行器侧派生（`idl_exec_trace.py`）在每条内存记录上附加该跳过集（建议字段名 `skip`，值为寄存器名列表）；
3. `idl_check_trace.py:compare_records()`：逐条取 `skip = set(exec.skip) | set(qemu.skip)`，把两侧 `dst`/`val` 中命中 `skip` 的条目**同时**剔除后再比较（`dst`/`val` 并列，须成对过滤）；
4. 落盘 JSONL 的字段面**保持不变**（写出前剔除 `skip`）；若选择把 `skip` 落到 JSONL，则必须同步 `idl/docs/trace-format.md` §1 并重生成 `idl/docs/trace-sample.jsonl`（`--sample-out`）；
5. 全量 `idl_check_trace` 复跑应 **274/274**；`ra_skips` 计数与 `--self-test`/`--sample-check` 行为不变。

## 不做

- 不改 QEMU/gem5/chipyard 的 RAS 实现（物理布局归各平台任务）；
- 不改 `dst` 的架构语义（「值变化的写回集合」），不放松有效区内的值比较；
- 不改 spec/契约/版本号。

## 约束

- 独立 `git worktree`；不提交 git；只动 `idl/tools/{idl_trace_common.py,idl_qemu_trace.py,idl_exec_trace.py,idl_check_trace.py}`、必要时 `idl/docs/{trace-format.md,trace-sample.jsonl}`、本任务书；
- 证据脚本固定为运行期证据目录内的 `run.sh`；完成区 ≤30 行；`**状态**` 改 `待验收`。

## 验证

1. 全量 `idl_check_trace`：**274/274**、rc=0（`--only ld.o_rrii_ra` 单独绿）；
2. **可达 FAIL ①**：临时禁用第 3 步的并集剔除 ⇒ `ld.o_rrii_ra` 第 205 条复红；`cp`+md5 还原 ⇒ 回绿；
3. **可达 FAIL ②（防掩盖）**：故意把执行器侧有效区内某条目值改错（如 `ra62`，须在窗口内且被写）⇒ 仍必红；还原后回绿——证明剔除只作用于「来源未定义」条目；
4. `make check-idl`（L2 冒烟）rc=0；`check-idl-parse`/`check-knowledge-refs`/`check-spec-refs` rc=0；
5. `git status -uall` 仅上述文件 + 任务书；越界 0。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
