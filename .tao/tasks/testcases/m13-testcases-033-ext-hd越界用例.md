# m13-testcases-033: `ext.uo`/`ext.so` orrr 的 `rdHD` 越界值（64 / 0x43 / 63）三平台用例

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-008` + `m13-qemu-010` + `m13-gem5-012`（三平台实现须先合入，否则用例必红）**+** `m13-testcases-017`（同目录 `ext.uo_orrr_rd.S` / `ext.so_orrr_rd.S` 载体由该任务建立，现为「进行中」⇒ 必须串行在其后）
**可并行分片**：否（共享 `tests/inst/04-arith-logic-octa/`）
**状态**：待开始

**预估**：2–3 h（约 6–8 条用例 × 三平台各一轮）

## 用户裁定（2026-11-13）

> 「`ext.*` 的 orrr 形式，`rdHD` 取**低 6 位**作起始位 `hd` 后继续执行，**不抛 ILLI**。」

- **渠道**：用户 2026-11-13 裁定，由主会话转达；原话登记于 `ISS-422`（`.tao/knowledge/issues.yaml`）。
- **对本任务的含义**：`rdHD=64`、`rdHD=0x43`（=64+3）、`rdHD=0xFFFF_FFFF_FFFF_FFFF` 等**都是合法输入**，期望按 `hd = rdHD & 0x3F` 计算；**禁止**写成 ILLI / `TEST_FAULT` 期望。

## 背景

- `m13-testcases-017` 正在把 `04-arith-logic-octa` 的 14 个 id 迁成「一 id 一 `.S`」，其中 `ext.uo_orrr_rd` / `ext.so_orrr_rd` 的原 YAML（`tests/inst/base/reg-shift-extend.yaml`）只覆盖 `shamt=2` 与 `shamt=63`（边界）两类，**没有** `rdHD > 63` 的取值。
- `ISS-422` 记录：`m13-testcases-017` 实测到三平台差异（chipyard 正常执行、QEMU/gem5 判 ILLI），因此**未**把该例作为 ILLI 故障例收录——本任务在实现修好后按新口径补齐。
- 宏层既有能力足够，无需改宏：`TEST_AR_ORRR pt, mnem, dst, dstinit, c, cval, d, dval, exp`（`d` = `rdHD` 寄存器，`dval` 可直接给 64/67/63/2^64−1）。

## 范围（只改 `tests/inst/04-arith-logic-octa/`）

1. 在 `ext.uo_orrr_rd.S`、`ext.so_orrr_rd.S` 的**链例尾部追加**边界用例（点号**连续递增、≤127**，**不改既有用例的点号**；若 017 已含同类 63 边界例，则去重保留一条并注明）：
   - **`rdHD=0` 对照**（若 017 未建则补 1 条）：`hd=0` ⇒ `ext.uo` 结果 = `src & 0x1`；`ext.so` 结果 = `bit0` 的符号扩展（源值取 `0x…01` 与 `0x…FF` 各 1）。
   - **`rdHD=64`** ⇒ 与 `rdHD=0` **同值**（`ext.uo`/`ext.so` 各 ≥1，`ext.so` 必须取「bit0=1」源值以暴露符号扩展）。
   - **`rdHD=0x43`（67）** ⇒ `hd=3`：结果 = `src & 0xF`（uo）/ bit3 符号扩展（so）。
   - **`rdHD=63`** ⇒ `hd=63`：结果 = 源值原样（uo）/ 源值原样（so，N=63）。
   - **`rdHD=0xFFFF_FFFF_FFFF_FFFF`** ⇒ `hd=63`（高分位全忽略），至少 1 条（uo 或 so）。
2. 每条用例在文件注释写清：spec 依据（`SimRISC-04 §2.2`「`hd = rdHD[5:0]`」）+ 手算过程（位段复制 / 符号扩展）+ 本任务「用户裁定」指向；**不得**照抄任一平台输出当期望。
3. 索引/台账：若 `check-tests-index` / `check-case-ledger` 因新增用例要求同步，按其 `--write` 重生成并在完成区给出命令与 rc；不需要则贴出「无需同步」的判据（门控 rc=0 即证据）。
4. 可在证据脚本里额外加一条**跨用例不变量**断言：`rdHD=64` 与 `rdHD=0` 两组用例的回读值/结果缓冲**逐字节相同**（不只各自比期望）。

**非范围**：不改宏层（`tests/inst/macros/inst_test.inc`）、不改实现（`components/**`）、不改 spec/合约、不改其它 `.S`。

## 验收标准（可执行、可失败）

1. **三平台逐字节一致**：`python3 tools/testcases/inst/run_asm_suite.py --id ext.uo_orrr_rd --id ext.so_orrr_rd --platforms chipyard,qemu,gem5` `rc=0`，新增用例全部一致（用例数/检查点数现场值）；任一平台不一致 ⇒ **不得放宽期望**，登记 issue 并如实记红。
2. **不变量**：`rdHD=64` 组与 `rdHD=0` 组的实测结果**逐字节相同**（脚本显式比对，输出两组的原始 8 字节值）。
3. **`make check-inst` 红集不扩大**：红集恰等于施工前现场枚举集合（当前应为 `divrem.yaml[23]`，若 `m13-testcases-032` 已合入则为空），**不含任何 `ext.*` 项**；`make check-inst-smoke` rc=0。
4. **可达 FAIL 注入（≥2 路；`cp` 备份 + md5 对账 + `touch` 还原 ⇒ 回绿；禁 `git checkout/restore/stash`）**：
   ① 把 `rdHD=64` 那条的期望改成 `hd=2` 的值（即 `src & 0x7`）⇒ 对应点号在**三平台同点号**红；
   ② 把该条改成 `TEST_FAULT ..., ILLI` ⇒ 三平台均**不**抛异常 ⇒ 红（证明「不抛 ILLI」被用例真正守护）。
5. **结构**：点号连续、每文件 ≤127；`check-tests-index` / `check-case-ledger`（如涉及）rc=0。
6. 一键证据脚本 `rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 说明

- 三平台当前状态：chipyard 已按截低 6 位实现（可直接绿）；QEMU/gem5 依赖 `m13-qemu-010`/`m13-gem5-012` 合入。若某平台**未重建/未合入** ⇒ 标 **BLOCKED（原因 + 替代证据）**，禁写「推定一致」。
- 若 `m13-testcases-017` 尚未把两个 `.S` 落到盘（其状态为非 `已验证`）⇒ 本任务**不得**自建同名文件（避免双写冲突），先返回主会话等 017 收口。
- 三平台运行可能耗时较长（chipyard 单例上限按 runner 默认），开工前申报预计墙钟。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数取现场值；「修改文件」与 `git status -uall` 对账。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入 → FAIL → 还原（`cp`+md5）→ 回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。

## 审阅记录

（待填）
