# m17-idl-024: trace 比较改为全 64 槽按值比（删除窗口/来源过滤）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-023`（IDL 执行器环形缓冲）、`m17-idl-022`（现有并集剔除，作对照基线）；四平台统一环形约定（见 023 任务书「统一环形约定」）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

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

## 审阅记录

### 第 1 轮 engineer 自审

- **逻辑**：`reg_delta` 只看值变化、无窗口过滤；两侧均为逻辑视图（QEMU dump 经 `ra_phys` 映射、IDL `snapshot` 经 `get`），故全 64 槽可直接按值比。`rd8` E3 跳过保留。
- **边界**：窗口外槽值不变不列入（只比变化）；`ra0` 仍按值比；`rb0`/`rd0` 不变量不变。
- **防造假**：全量/注入均现场执行；注入先 `cp` 备份、`md5sum -c` 对账还原；注入①另证记录 20 `ra0=0`（RACNT=0，窗口空）⇒ `ra1` 确为窗口外。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 死代码 `tc.snapshot()` 无调用方且返回物理视图 | ✅已修 | 改为逻辑视图（`machine.snapshot()`），由 `idl_exec_trace._snapshot` 调用 | `make check-idl`/trace 全量绿；grep 无物理视图导出 |
| `m18-qemu-009` 把 dump `PEND:` 改名 `PIM:`，旧正则匹配失败 ⇒ QEMU 异常帧全 0（基线红，非本任务引入） | ✅已修 | `_CFX5_RE` 兼容 `PEND|PIM` | 当前 QEMU 异常用例 `trap/call/ret/ld-ra` 全 PASS |
| `_exc_of_step` 沿用旧 `cg5[2:5]`，`m18-idl-002` 布局已变为 `PREV_IP/INTR_MASK/CAUSE_ID/CAUSE_INFO` | ✅已修 | 改用 `idl_exec.CG5_CAUSE_ID/PREV_IP/CAUSE_INFO` | 同上；`trap_ciii_cfx` exc 三字段全等 |
| 文档 §1/§2.1/§3/自检行残留 E4 旧口径 | ✅已修 | 同步 `trace-format.md`；样例脚本重生成 | `--sample-check` PASS |
| 任务书 `grep skip=0` 与保留 E3 `rd8_skips` 字面冲突 | ❌不修 | 保留 `rd8_skips`（E3 语义需要） | grep `ra_skips|_without_skip|"skip"` = 0，`rd8_skips` 单独说明 |

### 第 1 轮 reviewer 验收

- **重跑 3 次（仓库根执行运行期证据目录内的 `run.sh`，均本人执行）**：基线 `PASS=24 FAIL=0` rc=0；注入后 `PASS=16 FAIL=8` rc=1；`cp`+`md5sum -c` 还原（8 个目标文件 md5 与注入前快照逐字节相同）后再跑 `PASS=24 FAIL=0` rc=0。
- **口径自跑**：pre-cg15 QEMU（md5 `90b6bba5…`）**274/274** rc=0（248319 条）；canonical cg15 QEMU（`1896525d…`）**273/274**，唯一红 `escape_ciii_cfx`（`记录数 55 != QEMU 1731`）；基线 `git archive HEAD` 同红同 detail；`--sample-check` PASS；两自检 9/9 rc=0；`check-idl-parse`/`check-spec-refs`/`check-knowledge-refs` rc=0。
- **既有红独立确认**：`m18-idl-004`=待开始（IDL 未迁 cg15）、`m18-qemu-009`=已验证、`m18-spec-007`=已验证；pre-cg15 QEMU 下 escape **PASS**、cg15 QEMU 下 HEAD 亦红 ⇒ 红源于 IDL/QEMU cg15 不同步，非本任务引入（`dup` 在 0/1 间随 QEMU 运行抖动，「逐字相同」只对 detail 成立）。
- **grep/语义**：`_ra_shift|_without_skip|ra_skips|init_ra_ok|ra_valid_lo`=0，`"skip"` 字段访问=0（E3 `rd8_skips` 保留 11 处）；`reg_delta` 全 64 槽按值进 `dst/val`，`compare_records` 直比 `FIELDS` 全字段、无剔除路径 ⇒ 语义只增强、无吞差异。
- **独立注入（自选 FAIL①，非复用 engineer 自检）**：在 `idl_exec_trace.build_trace` 对执行器侧窗口外 `ra1` 翻转 ⇒ 单例 `call_iiii_ra` rc=1 `dst: exec ['rb30','ra1'] != QEMU ['rb30']`；注入后重跑同一脚本报 FAIL、还原后回绿（见第 1 行）。
- **两处一行修复**：① `_CFX5_RE` `(?:PEND|PIM)`——两个 QEMU 二进制实测均只含 `PIM:`，HEAD 正则永不匹配（自跑 HEAD `trap_ciii_cfx` ⇒ QEMU exc 全 0 红）⇒ 成立且在允许文件内；② `_exc_of_step` 改 `CG5_*`——`spec/DADAO-12` R3 重排 `rc2=prev_ip/rc4=cause_id/rc5=cause_info`，旧 `frame[2:5]` 自 `m18-idl-003` 合入起错位 ⇒ 成立；两处均修既有 bug，未放松任何口径。
- **范围**：`git status -uall` 注入前后快照逐行相同（4 工具 + 2 docs + 本任务书），非任务书文件 md5 前后一致，无越界、无注入残留。
- **finding（文档级，不阻断）**：① 完成区把 `PEND→PIM` 归到 `m18-qemu-009`，实为 `m18-qemu-008` 记载；② 完成区把 cg5 布局变化归到 `m18-idl-002`，实为 `m18-idl-003` 合入（`git log -S CG5_CAUSE_ID`）；③ `trace-format.md` 引用的 `check_trace_parity.py` 全仓不存在（既有陈旧引用）。
- **判决：Accepted**

## 完成区

**测试结果**：`run.sh` 24 PASS/0 FAIL rc=0。`--sample-check` PASS；`idl_exec_trace`/`idl_check_trace` 自检各 9/9；`make check-idl` **273/274**（唯一红 `escape_ciii_cfx`，既有）；全量 `idl_check_trace` 对与 IDL 匹配的 pre-cg15 QEMU **274/274** rc=0（248319 条指令）；当前 cg15 QEMU 273/274（唯一红同，基线 `git archive HEAD` 逐字相同）；`check-idl-parse`/`check-spec-refs`/`check-knowledge-refs` rc=0。
**修改文件**：`idl/tools/{idl_trace_common.py,idl_qemu_trace.py,idl_exec_trace.py,idl_check_trace.py}`、`idl/docs/{trace-format.md,trace-sample.jsonl}`、本任务书；`git status -uall` 无越界。
**验收结果**：
- grep `_ra_shift|_without_skip|ra_skips|init_ra_ok|ra_valid_lo` = 0；`"skip"` 字段/访问 = 0（仅 E3 `rd8_skips` 保留）。
- FAIL①：执行器侧窗口外 `ra1`（记录 20，`ra0=0` ⇒ RACNT=0）改 `0xdead…` ⇒ rc=1 `val: exec […0xdead000000000001] != QEMU […0x0001ffffff010178]`；`cp`+md5 `c157f3c8…` 还原后 rc=0。
- FAIL②：`ras_push` C3a 不推进 base ⇒ rc=1（记录数 121 != QEMU 811）；`cp`+md5 `1b9f1117…` 还原后 rc=0。
- 样例重生成后 `--sample-check` PASS；`run.sh` 内置 24 项逐项打印期望/实际/rc。
**新发现/坑**：① 基线 `escape_ciii_cfx` 红源于 IDL 未迁 cg15（`m18-idl-004` 待开始）而 QEMU 已 `m18-qemu-009`，与 trace 口径无关；匹配 pre-cg15 QEMU（md5 `90b6bba5…`）即 274/274。② `m18-qemu-009` 把 dump `PEND:` 改名 `PIM:`，旧 `_CFX5_RE` 解析不到 ⇒ QEMU 异常帧全 0，已兼容两种字段名。③ `_exc_of_step` 仍按旧 `cg5[2:5]` 取字段（`m18-idl-002` 后布局已变），已改用 `CG5_*` 常量。④ 任务书「grep skip=0」与保留 E3 `rd8_skips` 字面冲突，按「E4 skip 字段/`_ra_shift`=0」核。
**遗留问题**：`m18-idl-004` 完成前 canonical `make check-idl`/全量 trace 保持 273/274（唯一红 `escape_ciii_cfx`）；本任务未改 IDL escape 语义（任务书「不做」）。
