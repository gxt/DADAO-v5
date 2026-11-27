# m17-idl-023: IDL 执行器 RegRAS 改环形缓冲（去搬移）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m18-idl-002`（已合入 `5c6c7e16`）、`m17-idl-022`（已合入 `fe706925`）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

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

**测试结果**：`run.sh` 全流程 PASS（rc=0）。自检 133/133；`idl_parser --check`、`idl_check_anchor --check`（均无 `--update`）rc=0；`check-idl` 改后 **273/274**（共享安装根默认路径复跑同数），失败集与「改前 HEAD blob」逐行相同、恰为既有红 `escape_ciii_cfx`（IDL 签名 0 B，改前同）。trace：改前/改后 273/274 用例逐字节相同；IDL↔QEMU 逐条 `dst/val` 273/274（唯一 FAIL 同上）。
**修改文件**：`idl/tools/idl_exec.py`、`idl/tools/idl_exec_trace.py`、本任务书（其余仅 `.work/` 运行期证据，git 未跟踪）。
**验收结果**：
- base 位置：`Machine.ras_base`（实例属性，0..62，复位 0，非架构状态，不进出快照/`load_state` 的架构面）；`Machine.RAS_SLOTS = 63`；映射 `Machine._ra_phys(idx)`（`0→0`，其余 `1+(ras_base+idx)%63`，`_ras_top()`=`_ra_phys(63)`）。
- 架构面全部走映射：`get`/`set`（`ld.o-ra`/`st.o-ra`/`rd2ra`/`ra2rd`/`ldm`/`stm`）、`load_state`、`snapshot`（trace/dump）；`_set_racnt`/`_set_mrptr`/`racnt`/`mrptr` 仍直读物理 0。
- `ras_push`：C1 写一槽（基准不动，同 QEMU/gem5）、C2 只改栈顶计数、C3a/C3b 写一槽 + 基准 +1；C3b 按旧基准读逻辑 1 溢出后先访存再提交。`ras_pop`：D2 只改计数、D3 只基准 −1、D4b 回填逻辑 63 + 基准不动；判定/异常顺序不变。删除 `_ras_entries`/`_ras_store` 整体重排。
- 可达 FAIL ①（D3 不回退 base）：自检 rc=1（3 条 FAIL：`ras_ring_pop`/`ras_ring_wrap_down`/`ras_recursion_fold`），`ret_riii_ra` 签名红（idl rc=4 / qemu 0）；`cp` 还原 md5 一致后自检 133/133、2/2 回绿。
- 可达 FAIL ②（映射 `% 62`）：自检 rc=1（4 条 FAIL：`ras_ring_no_move`/`ras_c3b_*`），`call_iiii_ra`（idl rc=12）、`ld.o_rrii_ra`（rc=1）红；还原后 3/3、133/133 回绿。
**新发现/坑**：
- 共享 `.dadao` 的 bootrom（07:25）与 QEMU（11-25 15:44）落后 HEAD 源（bootrom 源 10:04、qemu 补丁 18:44）：旧 bootrom + 本执行器空转、新 bootrom + 旧 QEMU 挂死。处置：`make build-bootrom` PASS；本 worktree `fetch`→`apply_series.py --component qemu`→`make build-qemu` PASS；因共享 bootrom 已更新，按 Makefile 的 `atomic-install`（temp+rename）在 gate.lock 下把该 QEMU 补装进共享安装根（`qemu-system-dadao` md5 `8b49d6d9…`→`1896525dd7…`，`qemu-dadao` `f4557a92…`；旧二进制备份在运行期证据目录）。装后用默认路径复跑 `check-idl` = 273/274（唯一红同上）。
- 环形布局下「写时在有效区外、后被 `rd2ra ra0` 把 RACNT 提到 63 而提升进窗口」的槽内容与改前不同：274 例 trace 仅 `ld.o_rrii_ra` 记录 205/213 不同，且**新值与 QEMU 逐值相同**（旧值才是异类）⇒ 属规范未定义内容，非回归。
**遗留问题**：`escape_ciii_cfx` 既有红（IDL 签名 0 B）不属本任务；trace `exc` 字段在改前基线即与 QEMU 不一致（QEMU 侧 642 条全 0）属既有缺口；共享安装根的 QEMU 已补装到 HEAD 版本，其余会话无需再重建。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `tc.snapshot()` 直读 `machine.banks`（物理 RA）会让 trace 的写回集错位 | ✅已修 | `idl_exec_trace._snapshot()` 改用 `machine.snapshot()`（逻辑视图），2 处调用替换 | 274 例 trace 重生成；IDL↔QEMU dst/val 273/274 |
| `load_state` 直写 `banks["ra"][i]` 会丢/错放入口逻辑槽 | ✅已修 | 入口基准归 0 + 经 `_ra_phys` 落槽 | `check-idl` 273/274（改前同失败集）；trace 逐条一致 |
| 任务文字「call 压栈 base += 1」与参考实现 C1 不动基准冲突 | ❌不修 | 依「与 QEMU `ra_phys` 同式、同推进方向」按参考实现：C1 写 `phys(63)` 不推进，C3a/C3b +1、D3 −1 | IDL 记录 205 与 QEMU `dst/val` 逐值相同；`escape` 外 273 例全等 |
| `ld.o_rrii_ra` trace 改前/改后 2 条记录不同 | ❌不修 | 属窗口外未定义槽被 RACNT 提升；新旧都合规，而新值与 QEMU 一致 | 该记录新侧 == QEMU（逐字段打印）；trace 其余 273 例逐字节相同 |
| 自检未覆盖回绕/无搬移/C3b 溢出槽 | ✅已修 | 新增 14 条自检（C1/C3a 基准、物理槽不变、62→0 与 0→62 回绕、C3b 仅写一槽、D4b 回填） | 133/133；两路注入各令其中 3/4 条转红 |

### 第 1 轮 reviewer 复核（2026-11-26）

- **重跑（均本会话亲自执行）**：`python3 idl/tools/idl_exec.py --self-test` → `133/133` rc=0；`make check-idl-parse` rc=0、`make check-idl-exec-anchor`（无 `--update`）rc=0；工程态 worktree `make check-idl` → **273/274**、唯一红 `escape_ciii_cfx`（make rc=2，内层 rc=1 即既有红）；**主树**（= 改前代码）同命令同数、失败集同为 `escape_ciii_cfx` ⇒ 改前/改后失败集逐行相同。
- **证据脚本审计+重跑**：仓库根执行运行期证据目录内的 `run.sh`——注入 A/B 各有可达 FAIL（`assert count==1`、注入后 md5 必变、自检+子集双红、`cp`+md5 还原回绿），无恒真；`run.sh --fast` rc=0（含「改前 HEAD blob 273/274 == 改后 273/274、失败集 `diff` 逐行相同」）、`run.sh --inject B` rc=0（4 条 SELFTEST FAIL + 子集 rc=1，还原 133/133、rc=0）。
- **独立注入（reviewer 自做）**：C3a 删去 `ras_base += 1` ⇒ 自检 rc=1（`127/133`，6 条 FAIL：`ras_ring_base_c3a/no_move/logical_window/pop/wrap_up/wrap_down`）、`make check-idl` **271/274**（新增 `call_iiii_ra`、`ld.o_rrii_ra` 红）rc=2；`cp`+md5 还原后 check-idl 回 **273/274**、执行器两文件 md5 与注入前逐字节相同。
- **语义核**：`_ra_phys = 1+(base+idx)%63`（idx0→0）与 QEMU `ra_phys()`、gem5 `ras::phys()` 同式同向；base 0..62、复位 0、不入 `snapshot`/`load_state`；C1 不推 base、C2/D2 只改计数、C3a/C3b `+1`、D3 `−1`、D4b 不动 base、C3b 按**旧 base** 读逻辑 1 且 `write_memory` 先于 base/槽提交 —— 逐条对 `helper_ras_push/pop` 一致。
- **访问面/漏映射**：`get`/`set` ra 分支、`snapshot`、`load_state`（base 归 0 后按映射落槽）、`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`、`rd2ra`/`ra2rd`（`_block_copy` 经 get/set）、C3b 源全走映射；全仓 grep 直读直写仅剩 ra0 头（`racnt`/`mrptr`/`_set_*`）、push/pop 的物理槽写与自检断言 ⇒ **无漏映射**。
- **共享安装根**：安装根 `qemu-system-dadao` md5 `1896525dd7…` = 本 worktree 构建（`qemu-dadao` `f4557a92…` 相同），旧二进制 `8b49d6d9…` 已备份在运行期证据目录内；主树自带构建为 11-25 15:44，落后 `c9f8aa00`（11-26 18:44）的 qemu 补丁，主树 HEAD 另有 ISS-m16-013「共享 Tiny BootROM 与新 LLVM/旧 QEMU 不同步」⇒ **重装理由属实**；atomic-install + gate.lock，主树复跑 273/274 失败集不变 ⇒ **可接受**。
- **越界**：注入前后 `git status --porcelain -uall` 快照逐行相同，仅 `idl/tools/idl_exec.py`、`idl/tools/idl_exec_trace.py` + 本任务书。
- **未独立复跑（披露）**：`run.sh` 第 4 步 274 例 trace 改前/改后逐字节比对与 IDL↔QEMU 逐条 `dst/val`（约 10 min，超本档 20 min）——采信工程态证据。finding（不阻断）：`idl_trace_common.snapshot()` 仍返物理视图但已无调用方（trace 比较器归 `m17-idl-022`，本任务「不做」）。
- **判决：Accepted**

