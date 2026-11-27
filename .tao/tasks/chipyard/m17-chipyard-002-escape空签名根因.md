# m17-chipyard-002: `escape_ciii_cfx` 在 Tiny 上空签名（rc=0）根因定位

**模块**：chipyard
**项目里程碑**：M17
**依赖**：`m18-chipyard-002/003`（cg15/出口帧）、`m18-testcases-004/005`（向量迁移）、`m16-chipyard-033`（RegRAS 环形）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（诊断为主；复核 ≤20 min）
**状态**：已验证

## 背景（M17 收口唯一红，2026-11-27 实测）

`make check-idl-full`：**273/274**，唯一红 `escape_ciii_cfx`：

- 四方退出码全 0：`{idl:0,qemu:0,gem5:0,chipyard:0}`；
- **chipyard 签名字节流为空**（`.chipyard.out` 0 字节），IDL/QEMU/gem5 三份**逐字节相同**（md5 `25f3d355…`）；
- chipyard 日志末行：`SYS_EXIT op=0x18 arg=0xffffff017900 … reason=0x20026 code=0x0`，`pc=0xffffff014170`。

该 pc 反汇编为 `.faultpad::__pad_fail` 的 `trap cfx_umon, SYS_EXIT` 处。`__pad` 逻辑（`tests/inst/macros/inst_test.inc` §`__TEST_SECTIONS`）：`cause_id[15:0]` 与 `TEST_FAULTV[0]` 不等 ⇒ `__pad_fail`，退出码 = `TEST_FAULTV[8]`（点号）。实测退出码 **0** ⇒ 进入 pad 时点号槽仍为 0，即**在任何故障例武装之前出现了非预期异常**（或 `TEST_FAULTV` 数据在 Tiny 上读回 0）。

对照：11-27 03:20/03:50 的 `m18-chipyard-003` 证据里同一用例的 `.chipyard.out` **也是 0 字节**；11-25 之前该例是 `rc=13`（ILLI）。即形态已从「ILLI」变为「未武装即入 pad，静默 rc=0」。

## 要做（只定位，不修）

1. 复现：用既有 harness 只跑该例（`idl_four_way.py --only escape_ciii_cfx` 或 `run_inst_tiny.py --id escape_ciii_cfx --platforms chipyard`），固定证据目录；
2. **找出第一个非预期异常的指令与 cause_id**：用 Tiny sim 的 trace/日志（或分段裁剪 ELF、或在 handler 记录槽加临时观测）定位到 `.S` 的具体检查点，给出：pc、指令字、cause_id/子原因、当时的 run mode / cfx；
3. **判定归属**（三选一并给证据）：
   - RTL（cg15/出口帧/RegRAS 改动引入）——给出与哪个任务/改动相关、注入/回退哪一段可复现；
   - 测试载体（`m18-testcases-004/005` 迁移后不适用于 Tiny，如 `cg4 rc5`/`cg15 rc3` 访问或固件向量）——给出应改的点；
   - harness/固件（`run_inst_tiny`、Tiny hmon/power 入口）——给出证据；
4. 结论写入完成区，**不改 RTL/测试/固件**；若发现一行级测试载体修复即可验证归属，可在**独立 worktree** 内临时试验证，但只在完成区给 diff 建议，不提交。
5. 走查 `git log` 对应改动时间线（11-26 10:04 / 17:55 测试迁移；11-27 03:20 证据；04:44 RTL cg15；07:48 RegRAS），指出形态变化（rc=13 → 空签名）首次出现的 commit 附近。

## 不做

- 不改 RTL/测试/固件/契约；不登记/修改 `expected-divergences.yaml`；
- 不动其它用例。

## 约束

- 独立 `git worktree`；不提交 git；证据（日志、trace、反汇编片段）落运行期证据目录内 `run.sh` 可复跑；完成区 ≤30 行。

## 验证

1. `run.sh` 能复现「chipyard 0 字节 + rc=0」并输出第一个非预期异常的 pc/指令/cause；
2. 给出归属结论与「下一步应立什么任务（模块 + 一句话范围）」；
3. `git status -uall` 仅本任务书（诊断不改代码）。

## 完成区

**测试结果**：运行期证据目录 `run.sh` **29/29 PASS、RUN_RC=0**（含注入→还原自检）；基线复现 `run_inst_tiny --id escape_ciii_cfx --platforms chipyard` ⇒ chipyard rc=0 / 签名 **0 B** / `SYS_EXIT pc=0xffffff014170` / code=0x0（与 12:11 实测一致）。
**修改文件**：仅本任务书；诊断脚本与 diag ELF 全在运行期证据目录（`.work/` 已 gitignore）。未改 RTL/测试/固件/契约，未提交。
**验收结果**：
- **首个非预期异常**：`cause_id=0x4`（`1<<2`=CFXREG）、`cause_ip=0xffffff010160`、`cause_info=0x000000007b0cf0c5`（= 指令字）；指令 = `cfx2rc cfx_hmon, cg15, rc3, rd5`（`escape_ciii_cfx.S:82`，P0 写 async mask）；当时 `cg5 rc0=3`（hypv）、`cg5 rc1=0x3f`（cfx_power 63）。`TEST_FAULTV` 两槽均 0 ⇒ `__pad_fail` 取点号 0 作退出码 ⇒ rc=0、空签名。
- **第二个阻断（注入探针）**：把该行临时改到 Tiny legacy `cg3 rc4` 后，首个异常移到 `0xffffff010164` = `cfx2rd cfx_hmon, cg4, rc5`（`escape_ciii_cfx.S:84`），cause 仍 CFXREG（`cause_info=0x7a0c4145`）。即 Tiny 同时缺 `cg15 rc3` 与 `cg4`（`cg4` 读也被 `cfx_power` 用于点号 18）。
- 诊断副本 `.text` 与基线 ELF 逐字节相同（md5 `e4a52ca4…` ⇒ 首个异常数据不是观测插桩造成的伪影）；注入/还原用 `cp`+md5 对账（禁 `git checkout`）。
**归属结论**：**RTL（Tiny 寄存器面）为直接根因，测试载体为触发表征**。证据：`GewuFile.scala` 的 `asyncModel = gp.hart.isDefined`；`asyncIntrMaskOpt`/`cg15 rc3` 仅在 `asyncModel` 为真时创建；Tiny 的 `WumingCoreParams(useVM=false)` ⇒ `hart=None` ⇒ Tiny 只保留 legacy `cg3 rc4`，故 `cfx2rc cfx_hmon cg15 rc3` ⇒ CFXREG。`WumingParams.scala` 的 Tiny `cfx_hmon` 无 `commonRows` ⇒ `cg4` 亦不译码。此偏差已登记 `DIV-18`（active，用户 2026-11-26 裁定 Tiny 面保持 M16 基线），但 **DIV-18 只写了 `cg15 rc3`，漏了 `cg4`**；`escape_ciii_cfx.S` 头注释 GAP ① 称 escape_num「不计入链例」，实际第 84/149 行仍无条件读 `cg4` ⇒ 即便实现 `cg15 rc3` 仍会 CFXREG。
**时间线**：11-24 00:38 `1e1f3c81`（RTL 024）把 monitor mask 收进 `asyncModel`，Tiny 只剩 `cg3 rc4`；11-26 10:04 `f6f87ff2`（testcases-004）迁 R3 帧并新增 `cg4` 读；11-26 17:55 `4ea4eb32`（testcases-005）把 `cg8 rc1` 改 `cg15 rc3` ⇒ 当前形态（0 B）在此两笔测试迁移处首次可复现；11-27 04:44 `85e4e2d7`（RTL 002/003）只动 Vast、Tiny 面不变；07:48 `ecf4a16d`（RegRAS）与本题无关（HEAD 基线复现与注入结果不变）。11-25 前 `rc=13` 的旧记录未在本树现存证据中检索到，未采信。
**建议任务**：① `m18-testcases-006`（testcases，一句话：让 `escape_ciii_cfx` 在 Tiny 上可跑——`cg15 rc3` 与 `cg4 rc5` 访问按平台条件化/跳过并保持签名槽常量，同步订正头注释 GAP 与 DIV-18 文本）；若用户改判 Tiny 寄存器面，则改立 `m18-chipyard-004`（chipyard：给 Tiny `cfx_hmon` 打开 `commonRows` 并实现 `cfx0–3 cg15 rc3`，关闭 DIV-18）。② `m20-integ-002` 继续负责让 `check-idl-full` 识别 `expected-divergences`（当前 `idl_four_way.py` 不读该清单，DIV-18 仍被当红）。
**新发现/坑**：① 空签名 rc=0 是「未武装即入 pad」的退出码伪影，rc 轴不可作通过判据，只有签名长度/槽流能抓住；② `DIV-18` 漏记 `cg4`，且测试头注释与代码矛盾（称不计入链例却仍读）；③ `cfx2rd` 读未实现行与写一样触发 CFXREG，迁移时「读值仅用于 `__VERIFY`」不等于可安全读。
**遗留问题**：未复现/未定位 11-25 前 `rc=13` 的原始记录（无现存日志，未猜测其成因）；regRAS 前后均复现同一 0 B 形态，已排除。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`run.sh`（复现/诊断/注入/还原/静态归属）、诊断副本 `inst_test.inc` 的 `__pad_fail` 插桩、以及归属结论所引 RTL 源码行。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 插桩可能改变链例指令布局，使 cause_ip 失真 | ✅已修（加断言） | 诊断只改 `.faultpad` 副本；run.sh 比较基线与诊断 ELF 的 `.text` md5 | B0：`e4a52ca4…` 相等；C 行与基线反汇编同址同字 |
| F2 hmon 槽会被后续异常覆盖，不能证明「首个」 | ✅已修（证据链） | 依据 `TEST_FAULTV=0`（任何故障例都未武装）+ pad 立即到达 + 注入后异常精确前移一条 | B5/B6=0；D2/D7 往返 |
| F3 归属可能误记 harness | ✅已修（复核调用链） | 核对 `run_inst_tiny`/`signature.capture` 仅做取流与长度断言，rc 来自 guest | A1–A4、B2–B4 |
| F4 `run.sh` A1 断言「必须复现红」，修好后会变红 | ⏸延后（快照口径） | 不改成自适应；本任务只定位，脚本绑定当前基线 | 完成区已记基线 12:11/12:21 一致 |
| F5 E5 正则把注释里的 `commonRows` 当参数（曾假 FAIL） | ✅已修 | 收窄到 `hmon…sourceMaskReset = maskInitHmon)` 块 | 29/29 PASS |
| F6 worktree 内 `.dadao` 软链 | ✅已修（披露） | run.sh 缺链时建到主树只读产物；`.work/`/`.dadao/` 均 gitignore | `git status -uall` 仅本任务书 |

**判决**：finding 全部处置或披露；`run.sh` 29/29、RUN_RC=0；状态对账「待验收」。

### 第 1 轮 reviewer 复核

**重跑**（仓库根执行运行期证据目录内 `run.sh`）：`RUN_RC=0`、`29 passed, 0 failed`；A1 harness rc=1、A2 签名 `0 B`、A3 `code=0x0`、A4 `pc=0xffffff014170`、A5 现场派生 28 槽；B2–B8：`cause_id=0x4`、`cause_ip=0xffffff010160`、`cause_info=0x7b0cf0c5`、`FV0=0`、`FV8=0`、`cg5 rc0=0x3`、`rc1=0x3f`；D1–D8 注入→前移 `0xffffff010164`/`0x7a0c4145`→还原回 `0xffffff010160`（md5 对账）；E1–E5 全过。
**独立核（不采信完成区转述）**：基线 ELF 反汇编 `ffffff010160: 7b 0c f0 c5  cfx2rc cfx_hmon_async_intr_mask, rd5`、`ffffff010164: 7a 0c 41 45  cfx2rd cfx_hmon_escape_num, rd5`，与 `.S:81–85`（`set.rd P0` → 写 `cg15 rc3` → 读 `cg4 rc5` → `st.o [rb4,0x58]`）逐条对齐；`inst_test.inc:553/561/570–576` 证实 `__pad_fail` 退出码取 `TEST_FAULTV[8]` ⇒ 未武装即 rc=0 链成立；`GewuFile.scala:819/838/843/1062`（`asyncModel`、legacy `cg3 rc4`、`asyncIntrMaskOpt`、`filter(_.commonRows)` 含 `escapeNum`）、`WumingParams.scala:77/300/364` + `DadaoConfigs.scala:135`（Tiny `WumingCoreParams()` ⇒ `useVM=false` ⇒ `hart=None`）；`DIV-18` 的 impact/close_when 确无 `cg4`；`.S` 头 GAP① 称「不计入链例」而 84/125/149 无条件读 `cg4`（12/18 仍挂在链检查）⇒ 注释与代码矛盾成立；`idl/tools/idl_four_way.py` grep `divergence` **0 命中**（rc=1）⇒ DIV-18 不被豁免。
**时间线**（`git show` / `git log -S` 现场核）：`1e1f3c81` 11-24 00:38 引入 `asyncModel` 收编 → `f6f87ff2` 11-26 10:04 首次引入 `cg4` 读（其父无任何 `cg4` 行）→ `4ea4eb32` 11-26 17:55 把 82/122/146 的 `cg8 rc1` 改 `cg15 rc3` → `85e4e2d7` 11-27 仅 Vast `cfx_hart` 面与注释 → `ecf4a16d` 仅 `WumingRegFile` 补丁；当前 0 B 形态首次可复现于 11-26 两笔测试迁移。
**约束核验**：审前/审后 `git status -uall` 逐行相同、仅本任务书；未改 RTL/测试/固件/契约、未提交；`make check-knowledge-refs` PASS（0 具体 `.work/**` 引用）；完成区 11 行 ≤30。
**未独立复跑（采信）**：`check-idl-full` 273/274 与三方 md5 `25f3d355…`、11-25 前 rc=13 旧记录（完成区已声明未采信）。
**判决**：**Accepted** —— 验证 1/2/3 在我重跑下全过；归属证据链独立复核成立，`DIV-18` 漏 `cg4`、GAP 注释矛盾均为现场核实。提示（不阻断，交 architect）：按 2026-11-26 用户裁定 Tiny 面保持 M16 基线，可执行修复侧实际落在测试载体，建议任务二选一（`m18-testcases-006` 或改判后 `m18-chipyard-004`）。
