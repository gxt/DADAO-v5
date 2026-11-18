# m16-chipyard-004: `stm` 的 store 偏置 N 扫描实测

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-001`（已有 C/D 类实测方法与 sim 基线）
**可并行分片**：否（单 sim 单写者）
**预估**：1.5–2 h
**档位**：小改（只测量与报告，不改交付代码/表）
**状态**：待验收

## 背景（用户 2026-11-18）

`m16-chipyard-001` 遗留 3：`st`/`stm` 的 +1 拍未进 gem5 模型。现有两个数据点（`st.o` N=1 = 10 vs `ld.o` 9；`stm.o` N=8 = 73 vs 模型 72；`stm.b` N=8 = 17 vs 16）都表现为「+1」，但**只覆盖 N=1 与 N=8**，不足以排除「每元素 +1/8」这类巧合。

用户裁定方向（2026-11-18）：表格按 ld/st/ldm/stm **分行给值、不加列**；`stm` 的常数项要先**实测确认**再定。

## 目标

实测 chipyard `WumingTinyConfig` 上 `stm`（并以 `ldm` 作对照）在 **N = 1 / 2 / 3 / 4 / 8 / 16** 的拍数，判定 store 偏置是「每指令固定 +1」还是与 N 相关。

## 方法（沿用 `m16-chipyard-001` 口径）

1. sim 二进制：`.work/source/chipyard/sims/verilator/simulator-chipyard.harness-WumingTinyConfig`（已有，先记 md5）。
2. 探针来源：优先复用 `tests/inst/01-load-store/stm.o_rrri_rd.S`（同一镜像内含 N=2/3/8/16 多条 `stm.o`）；N=1/4 若缺，另建**最小探针**（`stm` + `ldm` 各 N 一条，跑完 `SYS_EXIT`），放 `/tmp/opencode/m16-chipyard-004/`，**不入仓**。
3. 拍数口径：trace 中相邻指令**进入 EXEC** 的 `cycle=` 差值（与 `m16-chipyard-001` 同一算法）；同一 N 至少 **2 个样本**（不同基址/对齐/宽度）。
4. 独立性：真值只取 chipyard trace；**不得**用 gem5/QEMU 反推，也不得用周期模型的输出作期望。

## 验收（逐条贴真实 rc / 原始输出）

1. 表格：`N / 指令 / 宽度 / 实测拍 / 模型拍（per_element×N + per_beat×beats）/ 差值`，每个 N 至少 2 样本。
2. 给出**判定**：差值序列是否恒为 1；若是，结论为「固定偏置」；若不是，给出实测规律（如 `1 + ceil(N/k)`）并说明与哪些 N 相关。
3. `ldm` 同表对照（用于确认 load 侧无偏置）。
4. sim md5、探针源码、解析脚本路径全部记录（运行期证据目录）。
5. 结论一句话可直接写进 `docs/core-wuming-cycle-model.md` §5 的表行形式。
6. **不改** `tools/gem5/wuming_cycles.yaml`、不改 gem5 补丁、不改周期模型文档（回填由后续任务做）。
7. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**。
2. 只动本任务书；探针/脚本/日志放 `/tmp/opencode/m16-chipyard-004/` 与运行期证据目录。
3. 不改版本号；不动 `components/`（只运行已有 sim）。
4. 主控机可能有其它长任务在跑（`m14-linux-017`）⇒ 单例串行跑，不要并行占满核。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 首版「每 (助记符,N) 一镜像」= 48 次 sim（约 14 min），且每 N 仅 2 样本 | ✅已修 | 改为每助记符一镜像、每 N 4 个基址（含非 8 B 相位起址） | 8 次 sim、192 样本；`--full` 35/35 |
| 初版模型按 `beats=⌈N·w/8⌉` ⇒ 非 8 B 相位样本多 8 拍，被误判成「N 相关」 | ✅已修 | `report.py`/`check_evidence.py` 改为 `beats=⌈(addr%8+N·w)/8⌉` | 66 个 (指令,N,beats) 格差值收敛到 {+0}/{+1} |
| `check_evidence.py` 把「模型含 +1」与「差值应为 +1」混用 ⇒ 4 条假 FAIL | ✅已修 | 模型只含 `1×N+8×beats`，`stm` 期望 +1 | 95/95 PASS |
| 注入 I2 以固定 IP 定位 exec 行，探针改版后 IP 变化 ⇒ 空注入（假绿） | ✅已修 | 动态取「memop 行之后的第一个 exec 行」再删 | `I2 caught check_fails=1` |
| 注入 I3 只改临时树内 `sim-md5.txt`，而 md5 检查读原件 ⇒ 注入无效 | ✅已修 | `sim_check` 参数化到被注入树 | `I3 sim_fails=1` |
| `--full` 用整条 JSONL 的 md5 比对，探针 `src` 绝对路径不同 ⇒ 8 条假 FAIL | ✅已修 | 改比 `rows_digest`（rows + exit_status） | `--full` 14 镜像 35/35 |
| `set -u` 下 `--full` 引用已被局部化的 `$sim` ⇒ 崩溃 | ✅已修 | 引入全局 `SIM_PATH` | `--full` 跑完 14 镜像 |
| `measure.py` 残留未用常量、工具/仿真器路径硬编码 | ✅已修 | 删死码；路径支持 `DADAO_TOOLCHAIN`/`WUMING_SIM`/`WUMING_WORK` 覆盖 | default/inject/full 三门全绿 |
| 任务书「方法」与「硬约束」段（非本任务改动）含运行期路径（`.work/source/…`、`/tmp/opencode/…`），与「任务书不写运行期路径」不符 | ❌不修 | 属下发时原文，改动任务书正文超出本任务范围 | 已在自审登记，建议主会话收尾时统一清理 |

### 第 1 轮 reviewer 验收

**重跑（reviewer 亲跑，无 `| tee`，退出码取命令自身）**
- `./run.sh` → `EXIT=0`，`checks=10 fails=0 PASS`；内层 `check-base.log` **95 PASS / 0 FAIL**；与 engineer `log-default.txt` **逐字节一致**（`diff` 空）。
- `./run.sh --inject` → `EXIT=0`，`checks=16 fails=0 PASS`：I1 `check_fails=2`（`E stm.o ['+1','+3']`）、I2 删 exec 行 348 `check_fails=1`、I3 `sim_fails=1`；I4 原件 md5 前后同、I6 回绿；与 `log-inject.txt` 逐字节一致。
- 自选第 4 路（临时树 review/inj4：`stm.o_scan` N=16 行 + trace memop count 同改 17）→ `EXIT=1` 红：`D0 [1,2,3,4,8,16]→[…,17]`、`D1 56 vs 49`、`D2 0 vs 1`、`E stm.o ['+1','-8']`；原件 62 文件 md5 前后全等。
- `--full` 采信日志（未重跑 sim）：`log-full.txt` `checks=38 fails=0 PASS`（F1/F3 14 镜像 + F2/F4 14 行）。

**数字复核（独立全量重算，非抽样）**：样本 **362** = 探针 192 + `tests/inst` 170；(指令,N) **48** 格全 ≥2 样本；(指令,N,beats) **66** 格方差全 **0**；差值 ldm={+0}、stm={+1}；例外 `0xffffff7ffff8`(+12)、`0xffffff012100`(+0) 各 **3** 次（`E3 expected=3 actual=3`，期望由 3 个 stm repo 镜像现场推导）。
**抽查 3 格（原始 `cycle=` 行自算）**：`ldm.ub` N=8 相位2 `60861→60885 = 24`（模型 24，+0）；`stm.o` N=16 `61475→61620 = 145`（144，+1）；`stm.b` N=1 `60575→60585 = 10`（9，+1）。
**附带① beats 直读 trace**：按 memop→下一 exec 窗口数 `WumingCore: beat st/ld` 行，**362/362 与 `⌈(addr%8+N·w)/8⌉` 相等**（0 不符，含非 8 B 相位 ⇒ 非推算）；附带③ 台账 md5 过期属实（`71574df4…`），已由主会话 8957f053 更新为 `eb5220f9…`。
**独立性/sim md5**：脚本不读 `wuming_cycles.yaml`/gem5/QEMU（grep 仅命中注释行），期望为代码内 `1×N+8×beats`；reviewer `md5sum` 实测 sim = `eb5220f9…` = `sim-md5.txt` = `MEMORY.md` = `m16-chipyard-001` 记录。
**越界**：`bfe3d701..HEAD` 仅任务书（+39/−2，无版本号改动）；任务树与主树 `git status -uall` 均空；`contracts/wuming-cycles.yaml`、`tools/gem5/`、`docs/core-wuming-cycle-model.md`、`components/` 零改动；证据目录 62 文件 md5 验收前后全等；reviewer 未提交 git。
**finding（文档级，不阻断）**：① 完成区验收2「48 个 (指令,N) 格内样本完全同值（方差 0）」字面不成立——18/48 格因起始相位原始拍数不同（`ldm.ub N=8 = {16,24}`），成立的是「**差值**方差 0」与 66 格同值；② 同句「170 样本只有 +0/+1 两类」漏计例外（实测 stm.o `+0×3 / +1×74 / +12×3`，例外已在②段单列）；③ `run.sh` 临时目录 `/tmp/opencode/m16-chipyard-004-ev` 不在 `<任务ID>/` 目录下。三处属措辞/约定级，交主会话收尾改。
**判决：Accepted**——验收命令块在 reviewer 自己重跑下全绿；3 路 + 自选 1 路注入均「红→还原→绿」；硬约束（独立 worktree、只动任务书、不改版本号/受保护文件、不提交）无违反。

## 完成区

**测试结果**：`run.sh` **10/10 + 内层 95/95 PASS**；`--inject` **16/16**（3 路注入均被检出，临时树删除后原件回绿且 md5 不变）；`--full` **38/38**（14 镜像重跑，解析行与记录逐字节一致）。样本 **362**（专用探针 192 = 8 镜像 × 24；`tests/inst` 复核 170），48 个 (指令,N) 格全部 ≥2 样本（其中 18 格因起始相位不同而原始拍数有二值，差值仍方差 0）。

**修改文件**：仅本任务书。（探针/脚本/trace/解析结果落运行期证据目录，不入仓；未改 `tools/gem5/wuming_cycles.yaml`、gem5 补丁、`docs/core-wuming-cycle-model.md`、`components/`。）

**验收结果**：
1. 表格（`report-probes.txt`，列含 beats）：N=1/2/3/4/8/16 × b/w/t/o
   - `ldm.ub` 9/10/11/12/16/32、`ldm.uw` 9/10/11/12/24/48、`ldm.ut` 9/10/19/20/40/80、`ldm.o` 9/18/27/36/72/144 ⇒ 差值全 **+0**；
   - `stm.b` 10/11/12/13/17/33、`stm.w` 10/11/12/13/25/49、`stm.t` 10/11/20/21/41/81、`stm.o` 10/19/28/37/73/145 ⇒ 差值全 **+1**。
2. **判定：固定偏置，与 N 无关**——**差值**在 48 个 (指令,N) 格内方差 0（`ldm`={+0}、`stm`={+1}）；**66 个 (指令,N,beats) 格**内原始拍数完全同值。注：48 个 (指令,N) 格中 18 格因起始相位不同而原始拍数有二值（如 `ldm.ub` N=8 = {16,24}），故「原始拍数方差 0」只在 beats 维度成立。`tests/inst` 复核的 170 样本同样以差值计为 +0/+1，另有 6 个地址例外（`+12×3`、`+0×3`，已在「附带发现」单列）。
3. `ldm` 对照：4 宽度 × 6 个 N 全 +0（load 侧无偏置）。机制：同一 (宽度,N) 下 `exec→最后一个数据 beat` 跨度 stm 比 ldm **恰多 1 拍**（o 宽 N=8：ldm 71 / stm 72）⇒ +1 在**写完成拍**，不是下一条指令取指造成。
4. sim md5 `eb5220f978f690515a193524921349dc`（mtime 2026-11-17T08:52，与 `m16-chipyard-001` 实测同源）；探针由生成器可再生（重生成 diff 为空）。
5. 可写进 §5 的表行：**`stm.*` = `1×N + 8×beats` + 1（每指令固定；N∈{1,2,3,4,5,8,16,63}、b/w/t/o、beats 1–63 实测差值恒 +1）**。
6. 真值只取 chipyard trace；未用 gem5/QEMU/周期模型输出。

**新发现/坑**：
① beats 须按**起始相位**算：`⌈(addr%8 + N·w)/8⌉`；非 8 B 相位起址实测恰多 8 拍/拍（`ldm.ub` N=8 相位 2 ⇒ 24 而非 16）——「元素不跨 8 B 拍」只保证元素不跨界，不保证整组落在一个拍内。
② `stm` 两个 N=1 地址特例（与 N 无关）：SRAM 尾拍 `0xffffff7ffff8` 写完成 +11 拍（21 vs 10）；`.text` 内 `0xffffff012100`（紧随一次 off-queue 取指）9 拍（−1）；已作为显式例外进断言（各 3 次，勿用作 +1 的解释）。
③ 台账 `MEMORY.md` 的 chipyard sim md5（`71574df4…`）与当前二进制 `eb5220f9…` 不符（后者与 `m16-chipyard-001` 记录一致）⇒ 台账 md5 已过期，建议主会话更新。
④ 该 sim 逐拍确定：14 镜像重跑与记录一致（含 boot 到 exit 的 cycle 值）⇒ 可用于逐拍回归。

**遗留问题**：① 回填 `docs/core-wuming-cycle-model.md` §3/§5 与 `tools/gem5/wuming_cycles.yaml`（store 偏置字段）按用户裁定另立任务——本任务只测量。② SRAM 尾拍 +11 与 off-queue 取指 −1 未建模（N=1 特例，C 类 ±1 容差覆盖不了 +11），建议在 §5 偏差清单登记。

