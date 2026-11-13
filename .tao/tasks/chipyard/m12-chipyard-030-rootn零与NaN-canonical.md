# m12-chipyard-030: `rootn(±0,2) ⇒ +0` 与自写 FP 的结果 NaN 统一 canonical（RTL + 模型）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m13-spec-007`（口径定稿；本任务不据 QEMU/gem5 结论推定 RTL 行为）
**可并行分片**：否（单组件单写者）
**状态**：待开始

**预估**：3–4 h（含 elab + Verilator 重建）

## 用户裁定（2026-11-13，落盘 `.tao/knowledge/discussing.md`）

1. **R1**：`rootn(±0,2)` 收严为 IEEE `+0`（IEEE 754-2019 §9.2.1；NOTE 明确 `rootn(−0,2) ≠ squareRoot(−0)`）。
2. **R2**：结果 NaN 统一 **canonical quiet NaN**（符号 0、payload 全零；ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）。依据：IEEE §6.2.3 payload 传播只是 *should*、§6.3 不规定符号；**Berkeley hardfloat 即 canonical**（`RoundAnyRawFNToRecFN.scala`：`signOut = Mux(isNaNOut, false.B, …)`、NaN 时有效位只置 quiet 位）。

审计来源：`docs/TestReports/M13-FP-IEEE对齐审计.md` §D2 / §D3。

## 背景（RTL 现状现场）

`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingFP.scala.patch`：

- 取整/转换包装（`invalidExc` / `isNaNOut` 那一段）已把 **符号清 0**（`signOut = Mux(isNaNOut, false.B, io.in.sign)`），但注释自陈「DADAO: a quiet NaN input keeps its payload（窄化截断位 OR 进 payload 末位、加宽左移）」⇒ qNaN 输入的 payload 被传播、窄化还额外 OR 截断位。
- `WumingDivSqrtRecFN` 另有独立的一处 NaN 传播：`nanSrc`/`nanSig = (nanSrc.sig << 2)(sw+2,0)` → `nanSigZ` → 送进 rounder 的 `io.in.sig`（`Mux(nanInZ, nanSigZ, …)`）⇒ 除法/开方同样传播首 NaN payload。
- `WumingDivSqrtRecFN` 注释：「`rootn(-0, 2)` is unspecified by spec §2.2; -0 is returned」⇒ `foroot(−0,2) = −0`；实现上零结果走 `zeroOut = Mux(io.sqrtOp, rawA.isZero, …)`，符号取 `sign = Mux(io.sqrtOp, rawA.sign, rawA.sign ^ rawB.sign)`，rounder 对非 NaN 结果保号 ⇒ 零结果继承 `−0`。
- 模型 `tools/chipyard/fp_ref.py`：`round_bits(...)` 的 `nan_fract` 传播 payload；`sqrt_exact(...)` 零分支返回 `ra["sign"] << (...) `（保号）⇒ 与 RTL 同现状。

## 范围（RTL + 模型 + 单元/扫描覆盖；不含向量文件）

1. **R1**：`WumingDivSqrtRecFN` 的 sqrt 路径——源为 `+0`/`−0` 时结果 `+0`（符号位 0），不置标志；`±Inf`、负有效数（`NV` + canonical qNaN）、有限正数行为不变。
2. **R2**：结果 qNaN 一律 canonical（符号 0、payload 只置 quiet 位）：
   - 取整/转换包装：删除 qNaN 输入的 payload 传播与窄化截断位 OR（`nanFract` 恒为 `quietBit`）；
   - 除法/开方：删除 `nanSig`/`nanSigZ` 通路对 rounder 的 payload 注入（NaN 时只由 rounder 置 quiet 位）；
   - 适用面：算术 add/sub/mul/div、scaleB、root、remainder、FMA、rnd、minmax（双 NaN 已 canonical）、`fo2ft`/`ft2fo` 转换；
   - **不适用**（须保持）：`ft2ft`/`fo2fo` 复制（纯位搬移）；`ftscmp`/`foscmp` 的 sNaN 结果（signaling 位型、符号 0）；`minmax` 单 NaN 返回数字。
3. **模型同步**：`tools/chipyard/fp_ref.py` 按 **spec 派生**改（`round_bits` 的 NaN payload、`sqrt_exact` 的零分支），**不是**按 RTL 现状反推；`tools/chipyard/fp_sweep.py` / `tools/chipyard/fp_unit/unit_run.py` 补覆盖点（root ±0、带 payload/负号 qNaN、`fo2ft` NaN），计数取现场。
4. `components/chipyard/changelog.md` 记一条；补丁经 `make_patch` 重导出（`series` 不变，一文件一补丁）。

**非范围**：不改 `tests/inst/**`（YAML 向量归 `m13-testcases-032`）、不改 `tests/case-ledger.tsv`、不改 QEMU/gem5/spec、不改 `WumingFPUnitHarness` 之外的公共接口（若 harness 需加断言可改，须披露）。

## 角色边界（用户 2026-11-13 裁定：节点只作评测用）

- **主控机 = 唯一仓库写者 + 构建调试 + L1 静态门控**：改 `components/chipyard/patches/**`、`tools/chipyard/**`、changelog；`make_patch` 导出补丁；跑 `check-patch-tree` / `check-source-state` / L1；elab + Verilator 构建亦在主控机（调试迭代不得外包）。
- **节点 = 评测执行机**：主控机 `make sync-node-repo` 后，节点 `make apply-series` → 节点**自行重建** chipyard（Verilator 产物与机器相关，**禁止跨机复制**）→ 节点跑 FP 评测（`fp_sweep` / `fp_unit`）。节点**不做**仓库修改、补丁导出、调试迭代、L1 静态门控。
- 评测就近判据（用户 2026-11-13）：单套件墙钟 `< 15 min` ⇒ 主控机就近跑（构建时间不计入）；`> 15 min` ⇒ 分片到节点并行。
- **不得用 QEMU/gem5 结论推定 RTL 行为**：RTL 结论只认 RTL 自身仿真（单元 harness 或 Verilator 探针）；QEMU/gem5 仅作对照，三方对照由 `m13-testcases-032` 汇总。

## 验收标准（可执行、可失败）

1. **逐点实测**（改后 RTL：单元 harness 或 Verilator 探针，给出装载值/读回路径）：
   - `foroot(−0,2)` ⇒ `0x0000_0000_0000_0000`；`ftroot(−0,2)` ⇒ 低 32 位全 0、符号 0；`foroot(+0,2)`/`ftroot(+0,2)` ⇒ `+0`、无标志；`foroot(−4.0,2)` ⇒ canonical qNaN + `NV`
   - `ftadd(0x7FC1_2345, 1.0)` ⇒ `0x7FC0_0000`；fo 侧带 payload 且负号 qNaN 的 `foadd` ⇒ `0x7FF8_0000_0000_0000`
   - `fo2ft(0xFFF8_0000_0000_0123)` ⇒ `0x7FC0_0000`；`ft2fo(qNaN 带 payload)` ⇒ `0x7FF8_0000_0000_0000`
   - 排除项：`ft2ft` 复制带 payload NaN ⇒ 原样；`foscmp(qNaN,1.0)` ⇒ `0x7F80_0001` + `NV=1`
2. **模型 == RTL 逐字节**：`fp_sweep`/`fp_unit` 全绿（`mismatch=0`），受影响格数/向量数取现场输出；`fp_ref.py` 改动须能追到 spec 条款（完成区写清「哪句 spec → 哪行模型」）。
3. **可达 FAIL 注入（≥2 路）**：① 把 `nanFract` 改回「传播首 NaN payload」⇒ 对应格红；② 把 root 零分支改回保号 ⇒ `−0` 例红。均 `cp`+md5+`touch` 还原（注意 `cp -p` 假绿坑）⇒ 回绿；注入期须断言组件源树 diff 非空、还原后 blob == `base+1` commit blob。
4. **门控**：`check-patch-tree`（chipyard problem=0）、`check-source-state` rc=0、`apply-series` 幂等（HEAD 不变）、`check-component-changelog` rc=0；elab + Verilator 构建 rc=0、`%Error`=0。
5. **整数套件不受影响**：整数 273 例 emit md5 与基线一致（现场值；FP 改动不应触及）。
6. 一键证据脚本 `.work/evidence/<任务ID>/run.sh` `rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账；`JOBS=8`，禁全核。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树（`ISS-368`）。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。

## 审阅记录

（待填）
