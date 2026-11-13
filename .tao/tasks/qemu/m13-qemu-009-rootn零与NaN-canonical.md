# m13-qemu-009: `rootn(±0,2) ⇒ +0` 与结果 NaN 统一 canonical

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-spec-007`（口径定稿）
**可并行分片**：否（单组件单写者）
**状态**：待开始

**预估**：2–3 h

## 用户裁定（2026-11-13，落盘 `.tao/knowledge/discussing.md`）

1. **R1**：`rootn(±0,2)` 收严为 IEEE `+0`（IEEE 754-2019 §9.2.1；NOTE 明确 `rootn(−0,2) ≠ squareRoot(−0)`）。
2. **R2**：结果 NaN 统一 **canonical quiet NaN**（符号 0、payload 全零；ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）。审计依据见 `docs/TestReports/M13-FP-IEEE对齐审计.md` §D2 / §D3。

## 背景（现状现场）

- `components/qemu/patches/target/dadao/helper.c.patch` 的 `helper_fp_root()`（`foroot`/`ftroot`，`immu6 = 2`）直接调 `float64_sqrt` / `float32_sqrt`：`sqrt(−0) = −0` ⇒ `foroot(−0,2) = 0x8000_0000_0000_0000`（应为 `+0`）。
- 同文件 `fp_status_init()` 现设 `set_float_2nan_prop_rule(float_2nan_prop_ab, st)`，注释自陈「We match the current host（x86_64 SSE）」⇒ 算术/scaleB/取余/开方把**首个 NaN 的 payload 与其符号**传播出去（例：`forem(qNaN=0x7FF8_0000_0000_0123, 2.0) = 0x7FF8_0000_0000_0123`；`ftadd(0x7FC12345,1.0)` 得 `0x7FC12345`）。
- 对比：`roundint` / `minmax` / `fma` 三个 helper 已各自 `set_default_nan_mode(1, &st)`（canonical）。
- softfloat 侧事实（`fpu/softfloat-parts.c.inc`）：`partsN(pick_nan)` 与 `partsN(return_nan)` 在 `get_default_nan_mode(s)` 为真时**短路**返回 `default_nan`（早于 2-NaN 规则分派）；`set_float_default_nan_pattern(0b01000000, st)` 已把默认 NaN 设为 canonical ⇒ **在 `fp_status_init()` 置 `set_default_nan_mode(1, &st)` 即可让全部软浮点路径产出 canonical qNaN**，且不再依赖 2-NaN 规则（原 `g_assert_not_reached` 路径不会到达）。

## 范围（只改 QEMU 组件）

1. **R1**：`helper_fp_root()`（sqrt 分支）——源为 `+0`/`−0` 时结果 `+0`（符号位清 0），不置任何标志；`±Inf`、负有效数（`NV` + canonical qNaN）、有限正数行为不变。
2. **R2**：在 `fp_status_init()` 置 `set_default_nan_mode(1, &st)`，使全部 qNaN 结果为 canonical；随之 `float_2nan_prop_ab` 的规则与其「match host」注释的前提作废——保留或删除规则由 engineer 实测决定（**判据**：删后不得出现 `g_assert_not_reached` / softfloat abort；保持 `set_float_default_nan_pattern` 不变）。`roundint`/`minmax`/`fma` 中既有的 per-op `set_default_nan_mode(1,&st)` 变冗余，最小改动可保留，须在完成区披露。
3. `components/qemu/changelog.md` 记一条。
4. 不得顺带改其它标志路径（`NV`/`DZ`/`OF`/`UF`/`NX`）与舍入逻辑。

**非范围**：不改 `tests/inst/**`（既有 pin「传播 payload」的期望由 `m13-testcases-032` 改）、不改 spec/合约、不改 chipyard/gem5。

## 验收标准（可执行、可失败）

1. **R1 逐例**（改后安装根，`rd5` = `rf2rd` 读回、`rd6` = FCSR）：
   - `foroot(−0, 2)` ⇒ `0x0000_0000_0000_0000`、`rd6[4:0] = 0`
   - `ftroot(−0, 2)` ⇒ 低 32 位 `0x0000_0000`（符号 0；高 32 位按该例装载值）
   - `foroot(+0, 2)` / `ftroot(+0, 2)` ⇒ `+0`、无标志（回归）
   - `foroot(−4.0, 2)` ⇒ canonical qNaN `0x7FF8_0000_0000_0000` + `NV`（回归，值不变）
2. **R2 逐例**（改后安装根）：
   - `ftadd(0x7FC1_2345, 1.0)` ⇒ `0x7FC0_0000`；`foadd(fo qNaN 带 payload 且**负号**, 1.0)` ⇒ `0x7FF8_0000_0000_0000`（符号清 0）
   - `ftsclb(qNaN 带 payload, 3)` ⇒ `0x7FC0_0000`
   - `fo2ft(0xFFF8_0000_0000_0123)` ⇒ `0x7FC0_0000`（符号 0、payload 0）；`ft2fo(qNaN 带 payload)` ⇒ `0x7FF8_0000_0000_0000`
   - `forem(0x7FF8_0000_0000_0123, 2.0)` ⇒ `0x7FF8_0000_0000_0000`、无标志
   - `ftadd(sNaN, 1.0)` ⇒ canonical qNaN + `NV`（回归）
   - **排除项对照（必须保持不变）**：`ft2ft`/`fo2fo` 复制带 payload NaN ⇒ 位型原样搬移；`foscmp(qNaN,1.0)` ⇒ `0x7F80_0001` 且 `NV=1`
3. **`make check-inst` 的红集必须是「既有 pin 非 canonical NaN 的期望」且可穷举**：施工前用 `grep` 现场枚举 `tests/inst/fp/*.yaml` 中结果为非 canonical qNaN（payload≠0 或符号 1）的期望项（例：`divrem.yaml` 的 `forem` qNaN 传播 case `rd5=0x7FF8_0000_0000_0123`），逐条列在完成区；改后 `check-inst` 的 FAIL 集**必须恰等于该清单**（不得有其它红），并注明由 `m13-testcases-032` 收口回绿。若出现清单外红 ⇒ 判本任务缺陷。
4. `check-patch-tree`（qemu 子集 problem=0）、`check-component-changelog` rc=0；`check-source-state` rc=0。
5. **可达 FAIL 注入（≥2 路）**：① 去掉 `set_default_nan_mode(1,&st)` ⇒ canonical 例红（且 `check-inst` 红集扩大）；② 去掉 root 的零符号修正 ⇒ `foroot(−0,2)` 回 `0x8000…` 红。均 `cp`+md5+`touch` 还原 ⇒ 回绿。
6. **安装根一致性**（`ISS-373` 并发坑）：测量前后各断言 `md5(构建树二进制) == md5(安装根二进制)`，末尾必须再跑一次 `make install-host` 收口；注入整段建议用 gate lock 包住。
7. 一键证据脚本 `.work/evidence/<任务ID>/run.sh` `rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账；`.work` 须软链（`ISS-389`）、`JOBS=8`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数从脚本现场输出直接抄（`ISS-388`/`ISS-391`）。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）；补丁改动走 `make_patch` 导出。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。

## 审阅记录

（待填）
