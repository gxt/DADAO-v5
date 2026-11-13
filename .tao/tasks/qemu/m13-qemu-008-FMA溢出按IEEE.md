# m13-qemu-008: 融合乘加溢出按 IEEE 舍入模式（QEMU）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-spec-006`
**可并行分片**：否
**状态**：已验证

## 背景（`ISS-399`）

QEMU 的 `fofma` 溢出恒 ±Inf；按 `spec-006` 改为按舍入模式，并覆盖轻微溢出（只 NX）。

## 验收

四档 × 正负实测；与 chipyard 逐字节；`check-inst` rc=0；273 md5 不变；注入可达 FAIL。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-13）

- **前提实测证伪（核心）**：任务书称 `fofma` 溢出恒 ±Inf。未改源码、用当前二进制（`helper.c` md5 `233532639d88cb4633e9659dac9c1334`；安装根与 build 同一 md5 `b366e49102bb7adcbd1349461fc24a2d`）实测 `SimRISC-07 §2.5` 表 **70/70 全对**；对「恒 ±Inf」表恰红 **40/70**（差异集由两表动态计算）⇒ 现行 QEMU 已按方向分档、轻微溢出不置 OF，**无需改实现**，故本任务零源码改动。
- **根因**：`helper_fp_muladd()` 委托 upstream softfloat `float{32,64}_muladd()`，`partsN(uncanon_normal)` 的 `overflow_norm` 按 `FloatRoundMode` 取 `±Inf`/`±max`；轻微溢出时「无界指数舍入结果仍为 max」⇒ 只由 inexact 置 NX。`fo2ft` 的窄化路径不提供该分档，故 `m13-qemu-005` 才需手写 `fo2ft_overflow_result()`（两族实现路径不同）。
- **期望独立派生**：操作数按 spec 解析构造、不从实现反推——`±max×2+0`（严重）、`±1×max±2^(e−1)`（1/4 ulp 轻微）、`±1×max±2^e`（RNE 半 ulp 分界）、`±1×max±最小次正规`（粘滞位）、`2.0×2^emax−max=2^(emax−p+1)`（单次舍入控制）。
- **自审发现（均处置）**：① 首版把 boundary 全档写 `OF|NX` ⇒ 实测 8 格红；按 IEEE 复核：非 RNE 档在分界仍舍回 max ⇒ 只 NX ⇒ ✅ 改为「结果为 `±Inf` 才 `OF|NX`」（`flags_for()`），复跑 70/70；② 负数加数用取补拼位型易错 ⇒ ✅ 改为符号位 OR；③ 断言可失败性：注入后红集与「恒 ±Inf」差异集逐元素相等（40 格）、12 例轻微 NX-only 全红、`git diff --name-only` 非空、还原 md5 一致。
- **范围**：`git -C .work/source/qemu status -uall` 全程空、补丁树/changelog 零改动；工作树仅本任务书。无未修 finding，状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-13）

**判决：Accepted**（3 条文档级 finding + 1 条台账观察，architect 收尾处置；不返工）

**重跑（我亲自执行，workdir=任务 worktree、相对路径）**
- `./该任务的运行期证据脚本`：首跑被**我自己**生成的 `vecspec/vspec.check.yaml` 污染（批次 140 例、红集索引翻倍）⇒ `PASS=94 FAIL=1`、`RUN_EXIT=1`；清掉该临时文件后干净重跑 ⇒ `== summary: PASS=95 FAIL=0 ==`、`RUN_EXIT=0`。现场：spec `Results: 70 total, 70 passed, 0 failed`；前提表 `70 total, 30 passed, 40 failed`；`check-inst` `1141 total, 1136 passed, 0 failed, 5 deferred, 0 errors` + `44 total, 44 passed`；`covered=273, 2d4d94651346ef673c5a855e024c1489`；注入 `70 total, 30 passed, 40 failed` 且红集==两表差异集；还原 `70 total, 70 passed`。
- 逐格独立核：按 `spec/SimRISC-07 §2.5` 自行推 70 格位型+flags，与 `spec.tsv` 逐行相符；抽 14 格亲跑（轻微 4 方向 1/7/13/19、RNE 分界 24/60、粘滞 2/52、控制 32/33、严重 0/12/44/53）⇒ `spot: OK=14 MISMATCH=0`。
- **独立注入（改被测产物，非 engineer 自检）**：`fpu/softfloat-parts.c.inc` 的 `uncanon_normal` 把 RNE 平局改判向下（+4 行）⇒ `run.sh --no-inject` → `RUN_EXIT=1`、`FAIL spec table … (red: 24 25 59 60)`、前提红集 `44` ≠ `40` ⇒ 集合运算是活的、非写死 40；`cp`+md5 还原至 `ed61388baa93a6c353b14b52daea3c4e`、marker 消失、源树空 diff ⇒ 复跑 `RUN_EXIT=0`、`PASS=83 FAIL=0`。
- 该注入同时**因果证明** FMA 结果确实经 `uncanon_normal`（非 host-FMA 旁路），支撑根因归属。

**根因核（读码）**：`helper_fp_muladd` → `float{32,64}_muladd`（`fp_status_init` 后 flags=0 ⇒ `can_use_fpu` 恒 false ⇒ soft 路径）→ `parts64_muladd` → `parts64_uncanon` → `uncanon_normal`：`overflow_norm` 按 `FloatRoundMode` 取 ±max/±Inf、两支均 `OF|NX`；轻微溢出舍回后 `exp < exp_max` ⇒ 只 NX；`rf0[33:32]` → `rf0_round_mode`。`git diff c3d48b7..0e544b5 -- fpu/` 为空 ⇒ 确为 upstream（DADAO 补丁未碰 `fpu/`）。`helper.c` md5 `233532639d88cb4633e9659dac9c1334` 与交付态一致。

**约束逐条**：① `git diff --name-only master...HEAD` 仅任务书（WIP `82b308fb` 也只含该 1 文件，+25/−2）；② `git -C .work/source/qemu status --porcelain -uall` 空、`components/qemu` 零 diff；③ 安装根 `.dadao/cross-toolchain/bin/qemu-system-dadao` md5 = build `b366e49102bb7adcbd1349461fc24a2d`；④ 验收前后 4 个 md5 快照 `MD5-ALL-MATCH`；⑤ 完成区 9 行、本节 ≤40 行；⑥ 未 commit/push、未改台账。

**Finding（文档级，不阻断）**
- **F1** 遗留问题把「三平台逐字节 / 70 格入库」的载体写成 `m13-testcases-013`，但该任务是 `01-load-store` 多元素（其逐字节对象为 `ldm`/`stm`），与 FP 无关 ⇒ 应改指 `m12-chipyard-029`（验收含与 QEMU/gem5 逐字节）、`m13-gem5-009`（与 QEMU 逐字节）或 `m13-integ-002`（FP 三平台差分，现「暂不进行」）。
- **F2** 根因对照句「`fo2ft` 窄化路径没有这条」不准确：`float64_to_float32`→`float32_round_pack_canonical`→`parts64_uncanon` 走的是**同一个** `uncanon_normal`；`m13-qemu-005` 前的恒 ±Inf 来自 `helper.c` 硬编码 `res=(src>>63)?0xFF800000:0x7F800000`（`git show 91d8591c`），005 是把硬编码换成方向分派。主结论不受影响。
- **F3** 验收项「与 chipyard 逐字节」本轮未跑 ⇒ 收尾须显式记 **BLOCKED/移交**，不得记作已满足（已披露：`m12-chipyard-027` 08:33 派单占用构建树、chipyard 侧同名前提未测）。

**台账观察（我不改台账）**：`m13-qemu-008`、`m13-gem5-009` 两行仍留在 `milestones-m13.md`「待开始」表（派单即应移入「进行中」）；`m13-gem5-009` 本树任务书仍 `待开始`/审阅记录「待填」，但 `该任务引用的 reviewer 运行日志`（10:07，PASS=33 FAIL=0 EXIT=0）显示它已在跑 ⇒ 请 architect 核对。

**外溢判定**：**不能**推定 chipyard。QEMU 结论依赖 upstream softfloat `uncanon_normal` 的实现细节；chipyard 是独立 RTL（`m12-chipyard-013`，hardfloat recFN 路径），`m12-chipyard-029` 仍 `待开始`、其任务书前提仍写「恒 ±Inf」且未经实测；hardfloat 是否有同类分派属**推测**，不作依据。gem5 亦为独立实现，其自身证据我未独立核验，同样不作依据。

## 完成区

**测试结果**：`run.sh` → `PASS=95 FAIL=0`、rc=0（9m12s）。未改代码二进制对 spec 表 **70/70**（ft/fo 各 35 = 8 严重 + 8 轻微 + 8 粘滞 + 8 分界 + 3 控制）；对「恒 ±Inf」表 40/70 红（=两表差异集）。

- 严重溢出（±2·max；ft/fo 各 8 例，flags 全 `0x14`）：ft RNE `7f800000/ff800000`、RTZ `7f7fffff/ff7fffff`、RDN `7f7fffff/ff800000`、RUP `7f800000/ff7fffff`（正/负）；fo 同构 `7ff0…/fff0…`、`7fefff…/ffefff…`、`7fefff…/fff0…`、`7ff0…/ffefff…`。
- 轻微溢出（max+1/4 ulp；ft/fo 各 8 例）：正向 RNE/RTZ/RDN、负向 RNE/RTZ/RUP ⇒ `±max` 仅 `NX (0x10)`（共 12 例）；正向 RUP、负向 RDN ⇒ `±Inf` + `OF|NX`。
- 粘滞位（+最小次正规，16 例）与 RNE 分界（+半 ulp，16 例）：结果同轻微规则；分界上 RNE 双向 ties-to-even ⇒ `±Inf`+`OF|NX`，RTZ/RDN/RUP 按方向 `±max` 仅 NX。
- 控制 6 例：`±max` 精确、`2.0×2^emax−max=2^(emax−p+1)` ⇒ flags 全 0（乘积先舍入即溢出，单次舍入不溢出）。

**修改文件**：无组件改动（`components/qemu/**` 零 diff，源树干净）；证据脚本/向量/日志在运行期证据目录（不入库）；工作树 `git status -uall` 仅本任务书。

**验收结果**：`check-inst` rc=0——Vast `1141 total, 1136 passed, 0 failed, 5 deferred, 0 errors`；Tiny `44 total, 44 passed`（现场抄）；273 例 sweep `covered=273`、md5 `2d4d94651346ef673c5a855e024c1489` 不变。独立 oracle `fp_ref.fma_exact`（`ew,sw`=8,24 / 11,53）对 70 格 70/70 与 spec 表一致。注入「恒 ±Inf + OF」⇒ 40 格红（含 12 例轻微 NX-only）；`cp`+`touch` 还原 md5 `233532639d88cb4633e9659dac9c1334`、标记消失、源树干净、重建后 70/70 回绿。

**新发现/坑**：① 本任务前提不成立——QEMU 的 FMA 走 softfloat muladd，`overflow_norm` 已按 `rf0[33:32]` 分档；与 `fo2ft` 窄化路径不同（后者需手写分档），建议核对 `ISS-399` 的 qemu 部分（chipyard/gem5 两条仍需各自实测）。② 轻微溢出不能只测 1/4 ulp：粘滞位（最小次正规）与 RNE 半 ulp 分界（ties-to-even ⇒ 溢出）须单列，否则漏分界。③ 判据可归一为「结果为 `±Inf` 才置 OF」，逐档写表易错（首版即错 8 格）。

**遗留问题**：三平台逐字节对照本轮**未做（BLOCKED / 移交）**——chipyard 侧移交 `m12-chipyard-029`（其在 `WumingFP.scala` 的 hardfloat 路径上按同一张 spec 表实测，**不得用本任务结论推定**）；常驻门控载体移交 FP 汇编套件任务（`m13-testcases-021`/`022`：FMA 用例进 `tests/inst` 后由三平台套件守护），70 例矩阵本轮只在运行期证据目录。

#### 收尾（architect，2026-11-13 11:34）

- reviewer **Accepted**：清掉 reviewer 自己造成的证据污染后重跑 `run.sh` ⇒ **`PASS=95 FAIL=0`、EXIT=0**；`check-inst` 1141/1136/0 failed/5 deferred + 44/44；273 md5 不变。
- **「早已合规」证伪成立**：三条独立链——源码（`helper_fp_muladd → float{32,64}_muladd → uncanon_normal`，`overflow_norm` 按 `FloatRoundMode` 取 `±max/±Inf`，两支均 `OF|NX`；`git diff` 显示 `fpu/` 为 upstream 未改）、70/70 实测（reviewer 独立派生 + 14 格抽跑 0 mismatch）、reviewer 自己的 RNE 平局注入（红集恰 `24 25 59 60`，且证明结果确实经 `uncanon_normal` 而非 host-FMA 旁路）。
- **零源码改动可接受**：不是巧合，但常驻约束不足——已按 F1 把载体改指 FP 汇编套件任务（`m13-testcases-021`/`022`），chipyard 侧移交 `m12-chipyard-029`。
- **F2 已订正**：`m13-qemu-005` 之前的恒 ±Inf 来自 `helper.c` 硬编码结果选择（`git show 91d8591c`），不是窄化路径缺分档（`float64_to_float32` 与 fma 共用同一 `uncanon_normal`）。
- **F3 已记 BLOCKED/移交**：三平台逐字节未做；chipyard 用本任务结论推定属禁止项，须在 `m12-chipyard-029` 按同一张 spec 表实测。
\n