# m13-qemu-010: `ext.uo`/`ext.so` orrr 的 `hd` 取 `rdHD[5:0]`（删运行时 ILLI 路径）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-spec-008`（口径真源与契约先行；本任务依据其 §2.2 措辞与「用户裁定」段）
**可并行分片**：否（QEMU 单组件单写者；可与 `m13-gem5-012` 并行，与其它 QEMU 任务串行）
**状态**：待开始

**预估**：2–3 h（含 QEMU 增量重建 + 安装根核对，量级 < 10 min，开工前申报）

## 用户裁定（2026-11-13）

> 「`ext.*` 的 orrr 形式，`rdHD` 取**低 6 位**作起始位 `hd` 后继续执行，**不抛 ILLI**。」

- **渠道**：用户 2026-11-13 裁定，由主会话转达；原话登记于 `ISS-422`（`.tao/knowledge/issues.yaml`）。
- **口径**：`hd = rdHD & 0x3F`；`rdHD` 高位忽略、不抛异常。`orri` 形式的 `immu6` 天然 6 位、行为不变。

## 背景（现状与缺陷）

- `components/qemu/patches/target/dadao/insn_trans/trans_extend.c.inc.patch` 的 `trans_ext_uo_orrr_rd` / `trans_ext_so_orrr_rd` 现为：
  1. `TCGv_i64 rdhd = load_rd(a->hd);`
  2. 注释「ILLI check BEFORE mask: hd > N (N=63 for octa)」+ `gen_runtime_illi_check(ctx, rdhd, 63);`
  3. `tcg_gen_andi_i64(pos, rdhd, 0x3F);`（截低 6 位——本身已正确）
  4. 其余为移位型零/符号扩展并 `store_rd`。
  ⇒ 步骤 2 使 `rdHD=64` 等取值**先抛 ILLI**（实测退出码 `0xF8`=248），与 chipyard 行为相反（`ISS-422`）。
- `gen_runtime_illi_check()` 定义于 `components/qemu/patches/target/dadao/translate.c.patch`，当前调用者**只有**上述两处（移位族的 `shamt > N` 检查走别的路径，不受影响）。
- chipyard RTL 对照（只读溯源，非执行依赖）：`WumingDecoder.orrrShift` 把 `rdHD` 值送 ALU 的 6 位 `shamt` 端口 ⇒ 天然截低 6 位。

## 范围（只改 QEMU 组件）

1. **`.../insn_trans/trans_extend.c.inc.patch`**：两处 orrr 分支删除 `gen_runtime_illi_check(ctx, rdhd, 63);` 与其「ILLI check BEFORE mask」注释；保留 `tcg_gen_andi_i64(pos, rdhd, 0x3F)`；把「pos = VALUE of rdhd register (masked to 6 bits)」注释改述为「`hd = rdHD[5:0]`，高位忽略、不抛异常（spec §2.2 / `ISS-422`）」。
2. **`.../translate.c.patch`**：`gen_runtime_illi_check` 若因此**无调用者** ⇒ 同步删除该静态函数（否则触发 `-Wunused-function`）；删除后 `check_patch_tree` 仍须 problem=0。
3. **orri 分支**：`if (a->hd > 63) { gen_exception_illegal(ctx); return true; }` 为不可达（`immu6` 天然 6 位）。保留（最小改动）或删除均可，**必须在完成区写明取舍与理由**。
4. `components/qemu/changelog.md` 记一条（一句话 + 依据）。
5. **探针（不改 `tests/inst`）**：在运行期证据目录内自建 `.S` 探针（可复用 `tools/testcases/lib/trampoline.bin` 的运行方式），对 `ext.uo`/`ext.so` 各断言：
   - `rdHD=64` 与 `rdHD=0` 结果**逐字节相同**（源值取 2 组：全 1 与交替 `0x…0F`，覆盖「零扩展」与「符号位=1 的符号扩展」两种分支）；
   - `rdHD=0x43`（=64+3）与 `rdHD=3` 相同；`rdHD=63` 与 `rdHD=63` 自身口径一致（N=63 ⇒ 结果 = 源值）；`rdHD=0xFFFF_FFFF_FFFF_FFFF` 与 `rdHD=63` 相同；
   - 探针**退出码 0 = 全通过**，失败点号用 `SYS_EXIT`（`spec/Machine-v5 §7.1`）。

**非范围**：不改 `tests/inst/**`（归 `m13-testcases-033`）、不改 spec/合约（归 `m13-spec-008`）、不改 gem5/chipyard、不改移位族语义。

## 验收标准（可执行、可失败）

1. **新口径逐例（改后安装根）**：探针 `rc=0`，逐条 PASS；`rdHD=64 ≡ hd=0`、`rdHD=67 ≡ hd=3`、`rdHD=2^64-1 ≡ hd=63`、`rdHD=63 ≡ hd=63`，`ext.uo`/`ext.so` 各覆盖（`ext.so` 必须含「符号位=1」的源值）。
2. **旧行为消失（可达 FAIL 的正向证据）**：施工前二进制（`md5` 钉住，抄进完成区）跑同一探针 ⇒ `rc=248`（ILLI）；改后 ⇒ `rc=0`。二者对比即「缺陷真实 + 探针能红」。
3. **`make check-inst` 红集不扩大**：红集必须**恰等于**施工前现场枚举集合（当前应为 `divrem.yaml[23]`，若 `m13-testcases-032` 已合入则为空）；**不得**出现任何 `ext.*` 相关红，不得新增红。`make check-inst-smoke` rc=0。
4. **安装根 == 构建树（`ISS-373`）**：断言 `md5(构建树 qemu-system-dadao) == md5(安装根 qemu-system-dadao)`；测量前后各跑一次 `make install-host` rc=0，末尾必须再跑一次收口；注入整段用 gate lock 包住。
5. **可达 FAIL 注入（≥2 路；`cp` 备份 + md5 对账 + `touch` 还原 ⇒ 回绿；禁 `git checkout/restore/stash`）**：
   ① 去掉 `0x3F` 掩码（`pos = rdhd`）⇒ 移位量为负/超范围 ⇒ 探针红；
   ② 恢复 `gen_runtime_illi_check(ctx, rdhd, 63)` ⇒ 探针 `rc=248` 红。
   两路还原后二进制 `md5` 回原值、探针回绿。
6. **门控**：`check-patch-tree` 的 **qemu 子集 problem=0**（整树红若来自并行任务在飞，须现场归因并给出子集判据）；`check-component-changelog` rc=0；`check-source-state` 的 **qemu OK**（`base+N`、`clean=True`）。
7. **脚本与对账**：一键证据脚本 `rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账；`JOBS` 按 AGENTS 默认（`nproc/2`），构建前申报预计耗时。

## 说明

- 组件补丁须走 `make_patch`（一文件一补丁）导出；`components/qemu/series` 与 `check-patch-tree` 断言须保持通过。
- 探针里的期望值按「位段复制 + 零/符号扩展」手算，**不得**用改后 QEMU 输出反填期望。
- 重建成本：只改 `target/dadao` 两个 `.c.inc`/`translate.c` ⇒ 增量重建；若因 `configure` 变动全量重建，先申报再执行。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树；组件源树改动须收敛为 `base+1` 且干净（不入本仓库）。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数取现场值；「修改文件」与 `git status -uall` 对账。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入 → FAIL → 还原（`cp`+md5）→ 回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。

## 审阅记录

（待填）
