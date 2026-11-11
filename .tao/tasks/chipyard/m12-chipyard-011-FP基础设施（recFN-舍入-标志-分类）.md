# m12-chipyard-011: FP 基础设施（recFN/舍入/标志/分类）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-010`（位操作+原子+杂项，已合入）
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 背景

用户 2026-11-08 确认 FP 全做 5 组，参考 berkeley-hardfloat 的原语边界。

## 目标

1. **recFN 编解码**：`recFNFromFN` / `fNFromRecFN` / `rawFloatFromFN` 等价实现（硬float 语义）。
2. **六档舍入**：`RoundAnyRawFNToRecFN` 等价；舍入方向读 `rf0[33:32]`（dynamic）或立即数（按 `ADR-0050`）。
3. **异常标志**：NV/DZ/OF/UF/NX 的设置与 `rf0[4:0]` 读回。
4. **分类与符号**：`classifyRecFN`、符号位操作（`fosgnj` 等）。

## 验收标准

1. 与 hardfloat 的 `RoundAnyRawFNToRecFN` 在六档舍入下逐例一致（可用 `tools` 的 FP 测试向量）
2. 异常标志五类各有至少 2 例
3. 分类（NaN/Inf/subnormal/zero）全覆盖
4. Verilator 构建 rc=0（主控机）；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
5. 一键证据脚本（含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 非范围

转换/算术/除开方/取整（`010`–`013`）

## 说明

- **FP 实现方式（用户 2026-11-09）**：**参考** berkeley-hardfloat 的 recFN 语义，**自写**组合逻辑；**不引入 `hardfloat` 子模块依赖**。任务书/代码注释须**逐处注明来源**（`berkeley-hardfloat` 的哪个原语、对应的语义点）。
- **wuming 不是「单周期指令」而是「无流水线」**（用户 2026-11-09）：多寄存器/ldm/stm 等指令本就多周期；FP 除法/开方等长延迟操作允许走**多周期状态机**。
- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 可作结构参考（**只读溯源，非执行依赖**）。
- 构建/运行在节点（**单任务单机，不迁移**）；仓库修改在主控机。

## 硬约束

1. 临时目录 `/tmp/opencode/m12-chipyard-009/`；禁仓库内临时文件（**此前有任务留过 `scratch/`、`pico-math/`**）。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存 运行期日志目录；命令在 worktree 根内、相对路径。
6. **组件单写者**：chipyard 源树独占；发现其它任务在改先停下报告。
7. 长构建先申报耗时，落 PID/日志/`*_EXIT`；构建期间同机不得跑基线。
8. **单任务单机**：整个任务固定在一台节点做完，不跨机迁移。
9. 节点构建/运行后 `DADAO_NODES='gxt@100.79.255.16,gxt@100.81.9.54' make sync-node-repo` 并记录。
10. 不要删除其它任务的临时目录。


## 完成区

**测试结果**：一键证据脚本 **PASS=96 FAIL=0**（A 结构 / B 独立模型自检 / C 构建 / D 单元台 / E 273 回归 / F 指令扫 / G QEMU 对照 / H 周期 / I 门控）；注入自检 **2/2**（分类 sNaN↔qNaN 位对调 ⇒ D 红 14 项；oracle 的 negInf 位篡改 ⇒ F 红 2 项；均 `cp`+md5 还原回绿）。
**修改文件**（14 项 + 本任务书，与 `git status -uall` 逐项一致）：①–② `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/{WumingFP,WumingFPUnitHarness}.scala.patch`（新）；③–⑥ 同目录 `{WumingALU,WumingCore,WumingDecoder,WumingRegFile}.scala.patch`；⑦ `components/chipyard/series`；⑧ `components/chipyard/README.md`；⑨ `components/chipyard/changelog.md`；⑩ `tools/chipyard/fp_ref.py`（新）；⑪ `tools/chipyard/fp_sweep.py`（新）；⑫ `tools/chipyard/fp_unit/tb_fp_unit.cpp`（新）；⑬ `tools/chipyard/fp_unit/unit_run.py`（新）；⑭ `tools/chipyard/inst_sweep.py`（「已定义未实现」探针 `ld.t rf` → `ftadd`）。工作树无临时产物。

**验收结果**：
1. recFN 布局 = `sign(1) ## exp(ew+1) ## sig(sw-1)`（ft 33 位 / fo 65 位），比 IEEE 多一位指数 ⇒ 次正规在内部仍规格化。
2. 舍入：4 配置（ft→ft、fo→fo、fo2ft、ft2fo）× 5 档（RNE/RTZ/RDN/RUP/RNA）× 2640 向量 = **13200 例，RTL == hardfloat RTL == 精确有理数 oracle**（值差 0 / 标志差 0）；编码解码分类符号 7920 例 vs oracle 0 失败；FCSR 10 步 0 失败。
3. 五类标志：`rf0[4:0]` 各≥5 例（核上 `set.w rf0` wp0 写入 + 读回；单元台验 sticky 累积、`[33:32]`/`[4:0]` 写掩码、只读 qNaN 位）。
4. 分类：ft+fo × 10 类 **20/20** 各落独立一位；块形式 2/3/4/8 元素 + 62+2 边界共 36 例；`ft` 只取低 32 位（高半垃圾不影响）。
5. 核上字节级 96 例（classify/sign/rfmem/fcsr/rf0ldt）== 独立模型；QEMU 同镜像逐字节一致（4 组；`ld.t rf0` 单独成组，见新发现）。
6. 周期（trace 实测，非估计）：`ftcls`/`focls` = 1+元素数（1 元素 2 拍、3 元素 4 拍）；符号注入/`set.w rf`/`cs.* rf` 1 拍；`rd2rf`/`rf2rd` = 1+个数；`ld.o rf` 13 拍。
7. 273 例 md5 `2d4d94651346ef673c5a855e024c1489`（= m12-005 基线）不变；故障镜像 8/8 ILLI（分类 dst_rd0/mreg_zero/两处范围、符号 dst_rf0、cs rf dst_rf0）。
8. 门控：elab/Verilator rc=0（`%Error`=0）；`apply-series`/`check-source-state`/`check-patch-tree` rc=0；L2 rc=0；L1 红仅 `check-run-artifacts`/`check-temp-dirs`（offender 均他任务）。
9. 完成区 ≤30 行、无运行期路径；未使用节点（构建/运行均主控机）。

**新发现/坑**：
- hardfloat 用「增长 roundMask + 只右移 2 位」表达反规格化，等价于「按 quantum 取整后左归 `<< extra`」；漏了左归，次正规结果会差 2^k。
- `asSInt` 读 1 位进位 = −1（指数整批差 2）；须 `asUInt.zext`。
- 零值的 `sExp` 在上游是 don't-care（Chisel `PriorityEncoder` 全零回 `w-1`）；实现钉成 0，模型/RTL 才逐位可比。
- 三处与 hardfloat/QEMU 的**有意差异**（均按 spec 取）：标志位序用 `rf0[4:0]`；qNaN 输入**传播 payload**（hardfloat 规整化，单元台比 NaN 只比「是否 NaN」）；`ld.t rf0` 保只读 qNaN(`ft`) 位（QEMU 明示覆盖该只读位）。
- `cs.n/.z/.p` 第一类**总是**写两源之一；m12-010 的 `csTaken` 把第一类也做成条件写（仅第二类才条件写）⇒ 本任务修正并补覆盖。
- `ld.t rf` 的 `[63:32]` spec 未定 ⇒ 按 QEMU `MO_BESL` 符号扩展，两引擎逐位一致。

**遗留问题**：舍入原语在 011 只作为库（无指令使用，012+ 接入）；`rf.io.fflags` 端口已就位但当前恒 0，标志「由硬件抬起」的 OF/UF/NX 用例随 012–015 到位；`WumingFPUnitHarness` 属单元台（不入 SoC，由证据脚本断言守住）。

## 审阅记录

### 第 1 轮 engineer 自审

自审方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = `WumingFP.scala`、`WumingFPUnitHarness.scala`、`WumingALU/WumingCore/WumingDecoder/WumingRegFile` 的增量、`tools/chipyard/{fp_ref,fp_sweep}.py`、`tools/chipyard/fp_unit/*`、证据脚本与 README/changelog。缺陷均在「单元台 vs hardfloat / vs 精确 oracle」「核上字节级对比」「QEMU 同镜像」「273 例回归」中被真实输出暴露，逐条修复后复跑。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 舍入进位用 `asSInt` 读 1 位 carry（= −1）⇒ 指数整批差 2 | ✅已修 | 改 `expCarry.asUInt.zext` | 单元台 ft/fo 值差 0（此前 24/49） |
| F2 次正规结果缺「按 quantum 取整后左归」⇒ 差 2^k、UF 误置 | ✅已修 | `roundedSig = ((kept +& inc) << extraDrop)`，extra 上限改 `sigWidthBits` | 单元台 4 配置值差/标志差 0；`fp_ref` 位模型 vs 精确 oracle 60560 例 0 mismatch |
| F3 分类 bit9（+Infinity）误用 `sign && isInf`（与 bit2 重复） | ✅已修 | 改 `!sign && isInf`（RTL 与模型同步） | 单元台 classify 0 失败；核上 20/20 单类别命中 |
| F4 `signInject` 的 32 位掩码把 64 位 `rf` 截成 32 位 | ✅已修 | 掩码/操作数统一 64 位（`U(64.W)` + `pad`） | 单元台 op10–13 0 失败 |
| F5 零值 `sExp` 取上游 don't-care（`PriorityEncoder` 全零回 `w-1`）⇒ 模型/RTL 编码不可比 | ✅已修 | `rawFloatFromFN` 把零值指数钉成 0 并注明 | recFN 往返 0 mismatch；编码组 0 失败 |
| F6 `fp_sweep.dump_mem_word` 只返回尾部（丢了地址装载与 `ld.o`）⇒ 内存 dump 恒 0 | ✅已修 | `return words + dump_rd(...)` | rfmem 组 `core == 模型` 通过（rf 读回一直是对的，据此定位） |
| F7 向量期望本身有错：FCSR 跨用例累积、65 位字面量、fault `cause` 用位号而非 one-hot 字 | ✅已修 | 每用例前 `set.w rf0` 复位；改正字面量；fault `cause = 1<<bit` | fcsr 组通过；故障镜像 8/8 |
| F8 `cs.n/.z/.p`（第一类）被 m12-010 的 `csTaken` 当成条件写 ⇒ 谓词不成立时不写 | ✅已修（披露） | `csTaken = !isCs \|\| csCond <= 2 \|\| csCondTrue`（第二类才条件写） | `cs.z rf` 假支通过；QEMU 一致；273 例 md5 不变 |
| F9 在任务 worktree 里作业（含把 jar 解包/扫图产物落在 worktree 根） | ✅已修 | 迁移到任务 worktree，md5 对账后还原主工作树；产物移出 worktree | `git status -uall` 仅任务文件 |
| F10 证据脚本两处 heredoc 硬编码主工作树路径 | ✅已修 | 改用 `$ROOT` 参数 | 从任务 worktree 跑通 PASS=96 |
| F11 注入 (B) 篡改被 `emit` 重生成的期望文件（不可达 FAIL） | ✅已修 | 改为篡改 oracle（negInf 位） | 注入 (B) 红 2 项 → 还原回绿 |
| F12 `ld.t rf0` 与 QEMU 行为不同（QEMU 明示覆盖只读 qNaN 位） | ✅已修（披露） | 单独成 `rf0ldt` 组，只与模型比；QEMU 对照跳过该组 | 组内通过；QEMU 4 组逐字节一致 |

**判决**：finding 全部已修；证据脚本 96/96 全绿 + 注入 2/2 先红后绿（RTL 注入 14 项红、oracle 注入 2 项红）。

### 第 1 轮 reviewer 验收

**重跑记录（均为本人执行，2026-11-11）**
- `bash <运行期证据目录>/run.sh` → `== summary: PASS=96 FAIL=0 ==`、`REVIEW_FULL_EXIT=0`（16:30:32–16:38:23，日志见运行期日志目录 `m12-chipyard-011-reviewer-full.log`）。关键现场：4 配置各 `2640 vectors | hf-value-diff=0 hf-flag-diff=0 oracle-diff=0`；ctrl `6620 vectors failed=0`、`fcsr 10 steps mismatches=0`；273 例 `2d4d94651346ef673c5a855e024c1489`（=m12-005 基线）逐字节；5 组 core==模型、`classify_single_bit_hits=20`、`flag coverage … min=5`、fault `n=8 good=8`；QEMU 4 组一致；周期 `ftcls x1=2 / x3=4`、`sgnj/sgnn=1`、`set.w rf=1`、`cs.z rf=1`、`rf2rd/rd2rf=2`、`ld.o rf=13`；`apply-series`/`check-source-state`/`check-patch-tree` rc=0、L2 rc=0、L1 仅归他任务。
- `bash … --self-test-inject` → `REVIEW_INJECT_EXIT=0`：分类位对调 ⇒ D 红 14 项、oracle negInf 位 ⇒ F 红 2 项（20/20→18），两次 `restore md5 matched` 后回绿。
- **独立 oracle（自写 exact-rational，未参考 fp_ref/RTL）**：`indep_round.py` 5083 例（4 配置×5 档，含 85 个手挑边界：RNE 平局→偶、0.75/1.5 ULP、次正规半值→±0+UF+NX 与 peg-min+UF+NX、**舍入后进到最小正规⇒仅 NX**、溢出→Inf/maxfinite+OF+NX、±0/±Inf/qNaN/sNaN payload）⇒ `rtl mismatches=0`，与 `fp_ref.round_exact` `oracle diffs=0`；`indep_class.py` 832 例 ⇒ 0 mismatch、16/16 单位命中。
- **独立注入**：把 `roundIncr` 的 RNE 平局条件改成恒舍 → `ONLY=D` `PASS=15 FAIL=5`（ft 37 / fo 51 值差）exit=1；`cp`+md5（`b67f95ec6ca8e77d9906bb9d0848e81b`）还原 → `PASS=20 FAIL=0` exit=0；芯片组件源树 `git status` 干净。

**约束核验**：改动 15 文件（14 项 + 本任务书）与 `git show --stat HEAD` 逐项一致；完成区 22 行、无运行期路径；HEAD = architect WIP `8bce21dd`，engineer/reviewer 均未提交；审查前后任务树与主树 `git status -uall` 干净（本轮仅改本任务书）；本人日志已改名 `<TASK-ID>-<purpose>.log`，`check-run-artifacts` 余 3 项均为他任务。

**披露核验**：① 标志位序＝`SimRISC-00 §2.3.1`（bit0 NV…bit4 NX）；② qNaN 传播 payload＝`SimRISC-07 §1.4`；③ `ld.t rf0` 保只读 qNaN＝`SimRISC-00 §2.3.1`（仅 [33:32]/[4:0] 可写）+ `SimRISC-01` 注（`[63:32]` 不变）——**三处均有 spec 原文**，非自决。`cs.*` 修复＝`SimRISC-02 §2` 第一类「恒写两源之一」、第二类才条件写；010 漏检根因＝`tests/inst/base/reg-cond-assign.yaml` 5 条语义例**全在 taken 支**（cs.n=−1 / cs.z=0 / cs.p=+1 / cs.eq 相等 / cs.ne 不等），else 支从未执行 ⇒ 期望态与 QEMU 双方都看不见（非 oracle 写错）；011 已补 rf 形式 false 支 1 例（core==模型==QEMU）。

**Findings（文档级，非门控，交 architect 收尾改）**：F-a 完成区「13200 例舍入」「7920 例编解码/分类/符号」与现场 **10560（4×2640）/ 6620** 不符，且括号内 4×5×2640=52800 自相矛盾；F-b 任务书硬约束 1 临时目录误写 `m12-chipyard-009`（应为 011）；F-c 建议补测 rd 形式 `cs.n/.z/.p` 的 not-taken 支（现仅 rf 形式 `cs.z` 一条）。

**判决：Accepted** —— 验收命令块在本人重跑下全部通过、硬约束无违反、三处偏离有 spec 依据、010 缺陷修复正确且漏检根因已定位。

#### 收尾（architect，2026-11-11 17:48）

- reviewer **Accepted**：三条独立链同时为零 —— DADAO RTL == hardfloat RTL（值 + 5 位标志逐位）、RTL == 自写精确有理数 oracle（**5083 例，0 mismatch**）、`fp_ref.round_exact` == 该 oracle（0 diff）。`drop = 2 + clamp(Emin−E, 0, …)`、左归、tininess 取**舍入后**逐例核过。
- 分类 20/20 单位命中（ft/fo 各 10 类）；FCSR sticky 累积 10 步 0 失败。
- **三处偏离 hardfloat/QEMU 均查到 spec 原文**（非自决）：标志位序 `SimRISC-00 §2.3.1`、qNaN payload 传播 `SimRISC-07 §1.4`、`ld.t rf0` 保只读 qNaN 位 `SimRISC-00 §2.3.1`（**QEMU 越界**，故该组不进 QEMU 对照）。
- **010 缺陷根因已定位**：`tests/inst/base/reg-cond-assign.yaml` 5 条语义例**全在 taken 支**，else 支从未执行 ⇒ oracle 与 QEMU 都看不见「不写」。修复正确（`csTaken = !isCs || csCond <= 2 || csCondTrue`），spec 依据 `SimRISC-02 §2`。**转 `m13-testcases-010` 补 rd 形式 not-taken 覆盖**。
- 计数订正（F-a）：实际 **10560** 舍入例、**6620** 编解码/分类/符号例（完成区写 13200/7920 与「4×5×2640」自相矛盾）；门控判据为现场 `ge 1000`，不阻断。
- 结构限制（已知）：`rf.io.fflags` 恒 0，`NV/DZ` 硬件抬起路径未比较 ⇒ 随 `012`–`015` 接入。
