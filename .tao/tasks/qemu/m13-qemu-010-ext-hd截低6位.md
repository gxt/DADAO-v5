# m13-qemu-010: `ext.uo`/`ext.so` orrr 的 `hd` 取 `rdHD[5:0]`（删运行时 ILLI 路径）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-spec-008`（口径真源与契约先行；本任务依据其 §2.2 措辞与「用户裁定」段）
**可并行分片**：否（QEMU 单组件单写者；可与 `m13-gem5-012` 并行，与其它 QEMU 任务串行）
**状态**：已验证

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

## 完成区

**测试结果**：一键证据脚本（运行期证据目录）`run.sh` ⇒ **PASS=71 FAIL=0**、`RUN_RC=0` / `RESULT: PASS`；含 3 路注入（1 路等价性 + 2 路可达 FAIL）与评测节点三平台。
**修改文件**：`components/qemu/patches/target/dadao/insn_trans/trans_extend.c.inc.patch`、`components/qemu/patches/target/dadao/translate.c.patch`（`make_patch.py qemu`：2 written / 64 unchanged，共 66）、`components/qemu/changelog.md`（M13 一条）、本任务书；与 `git status --porcelain -uall` 逐条一致。组件源树收敛为 `base+1` 单提交、clean（不入本仓库）。
**验收结果**：
1. **四组口径（改后安装根，md5 与构建树同为 `1dfc56c9…`）**：`ext.uo`/`ext.so` 各 14 检查点、各 112 B，逐字节 == 脚本现场重导出自 `spec/SimRISC-04 §2.2` 的手算期望（28 条内联期望另经独立重算校验）。等价类：`64≡0`（点 1/2、7/8）、`67≡3`（3/4、9/10）、`63≡63`（5、11）、`2^64−1≡63`（6、12）；`ext.so` 源值 bit0=1（点 1/2/7/8 ⇒ 全 1，同例 `ext.uo` ⇒ `0x1`）区分 uo/so，另加 `hd=4` 的 `0x1F`/`0x0F` 两点区分符号填充与零填充。
2. **旧行为消失（正向证据）**：改前二进制（md5 `9837631c…`）跑同一**链例**探针 **不退出**（`rc=-2`：运行时 ILLI 落在 TB 中间 ⇒ 监视器 `escape [cause_ip,0]` 重执行 ⇒ 活锁）；把 `rdHD=64` 一例取为**故障例镜像**（指令独占一个 TB）后，改前 `rc=248`（ILLI `0xF8`，uo/so 各一次）、改后 `rc=1`（故障消失、落到用例自身 `__EXIT`）⇒ 任务书「同探针改前 rc=248」的可观测形式是故障例镜像；两种形态都钉进脚本。
3. **`check-inst` rc=2**：`1141 total / 1135 passed / 1 failed / 5 deferred / 0 errors`，红集**恰** `divrem.yaml[23]`、无 `ext.*`；**改前二进制跑同一门控红集逐条相同** ⇒ 未修也未扩大。`check-inst-smoke` rc=0。
4. **门控**：`check-patch-tree` qemu 段 **0 assertion**；整树 rc=1 / 14 问题全部归因于在飞组件（llvm-project / gem5 / chipyard 的源码树含本分支未合入的补丁导出），机械判据 = 逐组件比 `git diff <base>` 与本分支 `series` 内容（不看 `clean`）；`--source-state: qemu: OK`（base+1、clean）；`check-component-changelog` rc=0；`check_qemu_trans` **264/264**。
5. **安装根 == 构建树**：首末两次 `install-host` rc=0，`md5(构建树)==md5(安装根)==1dfc56c9…`（改前 `9837631c…`）。
6. **可达 FAIL 注入（`cp`+md5+`touch` 还原，整段 gate lock）**：① 掩码改 `0x1F` ⇒ uo 红@5、so 红@11；② 恢复 `gen_runtime_illi_check`（连 `gen_raise_exception_illi`）⇒ 链例活锁、故障例回 `248`。还原后重建 md5 回 `1dfc56c9…`、探针回绿、源树 clean。**任务书注入 ① 的「去掉 `0x3F` 掩码」实测不是 FAIL 路径**（本机 TCG i64 移位量取模 64，两处误差相互抵消）；脚本保留为等价性检查并钉住，另补 ①′ 承担第二条真红路径。
7. **三平台（评测节点）**：`chipyard == QEMU` 逐字节（so `475e16ce…`、uo `8a3f43da…`），两图 rc=0；gem5 仍 `rc=-2`（未修，见遗留 ①），脚本按钉值判红、不漂移即通过。
8. **orri 取舍**：`trans_ext_{uo,so}_orri_rd` 的 `if (a->hd > 63)` 保留（`immu6` 为 6 位字段 ⇒ 不可达；最小改动、不引入行为差异）；`translate.c` 另删仅被 `gen_runtime_illi_check` 调用的 `gen_raise_exception_illi()`（否则新增 `-Wunused-function`，构建 0 warning 已验）。
**新发现/坑**：① 链例里的运行时 ILLI 会活锁（`gen_raise_exception` 在 TB 中间 raise + `escape` 重执行），只有「指令独占 TB」的故障例镜像能观测到 `0xF8`；② TCG i64 移位量在 x86-64 宿主取模 64 ⇒ 「去掩码」类注入不可观测，任务书注入 ① 的假设不成立；③ `check-patch-tree` 的在飞形态不止「脏树」：并任务把源码树做成新 `base+1` 后，本分支表现为「补丁导出落后」，归因须比内容；④ QEMU 二进制 md5 随补丁 commit 变（amend 后 `9837631c…` → `1dfc56c9…`），跨轮次不得沿用旧钉值。
**遗留问题**：① **gem5 未修**（`ext.*` orrr `rdHD≥64` 仍 ILLI / 活锁）⇒ 逐字节一致只在 chipyard/QEMU 成立，归 `m13-gem5-012`；② `check-inst` 余 1 红 `divrem.yaml[23]`（既有 pin，归 `m13-testcases-032`）；③ spec/合约措辞（`SimRISC-04 §2.2` 的「hd ≤ N 否则 ILLI」）归 `m13-spec-008`，本任务未改 `spec/`。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`trans_extend.c.inc` 全 diff（两处 orrr 删 ILLI + 注释改述，orri 未动）、`translate.c` 删除 `gen_runtime_illi_check`/`gen_raise_exception_illi` 及 `gen_raise_exception_malign` 注释连带修改、导出的 2 份补丁 + `series`、`changelog.md` 一条、两份链例探针 + 两份故障例探针、`run.sh`/`node-run.sh`。

- **语义正确性**：`pos = rdhd & 0x3F` 后仍走 `(rdhc << (63-pos)) >> (63-pos)`（uo 逻辑右移 / so 算术右移），`hd=63` 时 `shift=0` 不触发未定义移位；`a->hb == 0` 的 `dst_rd0` ILLI 保留；只删了 `hd > 63` 的运行时判定，未改其它异常路径。在组件源码树内 `grep -rn` 两个被删助手名，确认删除后无残留引用；`build-qemu` 日志 0 warning。
- **orri 未动**：`a->hd` 来自 `&misc hb hc hd` 的 6 位字段（`rdhd[5:0]`/`immu6`），`> 63` 恒假；保留以最小化 diff。
- **探针独立性**：期望值全部按位段复制 + 零/符号扩展手算内联，脚本再从 `.S` 的 `(cval, dval, mnem)` 独立重算一遍并与内联值逐条比对（28 条），**不**用改后 QEMU 输出反填；`ext.so` 的源值都取 bit0=1，避免与 `ext.uo` 混淆。
- **防造假**：71 项断言逐条有可达 FAIL 路径（注入 B/C 走不同失败路径：错掩码 vs 恢复 ILLI；期望序列与 QEMU 输出双向逐字节比）；计数（检查点数、镜像数、门控 total、264/264）现场派生；还原只用 `cp`+md5+`touch`，未用 `git checkout/restore/stash`。
- **自审发现（均已处置）**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书注入 ①（去掉 `0x3F` 掩码）实测**不红**：宿主把 TCG i64 移位量取模 64，未掩码形式与掩码形式结果相同 | ✅已修 | 新增注入 B（掩码改 `0x1F`）作为第二条真红路径；注入 A 保留为「等价性检查」并钉住结果 | A：探针仍 rc=0（钉值 0）；B：uo 红@5、so 红@11 |
| F2 任务书「改前二进制同探针 rc=248」在链例形态下不可能（活锁）；照抄会把「无退出」误报成 `248` | ✅已修 | 增 `probe-old/` 故障例镜像（`rdHD=64` 单独成 TB），钉 `改前 248 / 改后 1`；链例形态钉 `rc=-2` 并在完成区说明根因 | 首轮实跑：pre `248`、post `1`（uo/so 各一）；链例 pre `-2` |
| F3 首轮 `check-patch-tree` 归因只认「源码树脏」，llvm-project 已被并任务做成新 `base+1`（clean）⇒ 误判为不可归因、2 项假 FAIL | ✅已修 | 归因改为逐组件比 `git diff <base>` 与本分支 `series` 内容（脏树或导出落后皆可归因），仍保留「干净且内容一致 ⇒ FAIL」的可达路径 | 重跑：14 问题全部 attributable，`check-patch-tree: red only from in-flight components` |
| F4 `run.sh` 原用 `dirname $0/../../..` 求仓库根，`.work` 是共享软链 ⇒ 会指到主工作树 | ✅已修 | 改 `git rev-parse --show-toplevel` 并打印 root/branch | 运行首行回显 `repo root = …/wt (branch m13-qemu-010)` |
| F5 改前门控原计划把 gate 产物写进共享 `harness/gate-*`（会留下未登记产物目录） | ✅已修 | `--gate-dir` 改到运行期临时目录 | 重跑后 `harness/gate-*` 无新增目录 |

判决：无未修 finding；遗留 1（gem5）属跨模块、已由主会话另立 `m13-gem5-012`，非本任务可修 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（独立重跑）

**重跑记录**（workdir = 本任务 worktree；以下全是我自己的输出/退出码）
1. `bash .work/evidence/m13-qemu-010/run.sh` ⇒ `summary: PASS=71 FAIL=0`、`RESULT: PASS`、`RERUN_EXIT=0`；与 engineer 留存 `log/run-all.log` 的 PASS/FAIL/summary/RESULT 行 `diff` ⇒ `IDENTICAL`（输出真实性核过）。
2. 现场值：改前二进制 `9837631c…`；构建树==安装根 `1dfc56c9…`；`check-inst rc=2` = `1141 total/1135 passed/1 failed/5 deferred/0 errors`，红集**恰** `FAIL divrem.yaml[23]`、无 `ext.*`，改前同门控红集逐条相同，smoke rc=0；`check-patch-tree` qemu 0 assertion、整树 14 问题全 attributable；`--source-state: qemu: OK`（base+1 clean）；changelog rc=0；`check_qemu_trans 264/264`；注入 A 钉 0、B 红@5/@11、C 链例 `-2`+故障例 `248`；还原后源 md5 `d5bc601d…/b33826b9…`、二进制 `1dfc56c9…`、探针回绿、源树 clean；节点 `PASS=8`（chipyard==QEMU `475e16ce…`/`8a3f43da…`，gem5 `-2` 按 GAP 钉住）。
3. 我独立重算 28 条期望（自写解析 + oracle，不复用 engineer 脚本）⇒ `MISMATCH total = 0`；等价类 `64≡0 / 67≡3 / 2^64−1≡63`（uo/so × 两组源值）全 OK；uo pt1=`0x1` vs so pt1=`0xFF…FF`（bit0 区分两助记符）。
4. **改前两形态独立核实**（我自己 `llvm-mc`/`ld.lld` 汇编链接，不用 engineer 的 `.elf`）：故障例 `ext_{uo,so}_orrr_hd_illi` 跑改前 ⇒ **`rc=248`**（0xF8=ILLI）；链例 14 点同图跑改前 ⇒ `timeout 60` **`rc=124`**、输出 0 B（60 s 无退出）⇒ runner 记 **`-2`**。两种形态均为真。
5. **独立注入 2 路**（自设计，非 A/B/C；gate lock 内）：R1 `ext.so` 的 `tcg_gen_sar_i64 → shr_i64` ⇒ 套件红、so 首红@1、uo 仍绿；R2 `ext.uo` 移位基数 `63 → 62` ⇒ 套件红、uo 首红@1、so 仍绿；`cp`+md5 还原 ⇒ 源 md5 回原、重建回 `1dfc56c9…`、探针 rc=0、源树 clean ⇒ `PASS=17 FAIL=0`、`INJECT_EXIT=0`。
6. 快照对账：注入前后 `git status --porcelain -uall` 均空、4 个改动文件 md5 逐一相等、组件源 `e916acb` clean、构建树==安装根；改动范围 = 完成区声明的 4 文件。

**约束核验**：未改 `tests/inst`/`spec`/`contracts`/gem5 ✓；完成区 16 行 ≤30、无运行期路径 ✓；审阅记录本轮 ≤40 行 ✓；`JOBS=32`=nproc/2 ✓；还原只用 `cp`+md5+`touch`，未用 `checkout/restore/stash` ✓；gem5 `rc=-2` 钉为 GAP（非静默跳过）且 `m13-gem5-012` 已立册 ✓；spec/contract 仍写「hd≤63 否则 ILLI」（`SimRISC-04` §177/181、`legality_rules.yaml:214`）⇒ 归 `m13-spec-008`（已立册）✓；orri `a->hd>63` 保留的取舍已写明 ✓。**采信项**：改前二进制 md5 钉值本身（未从父提交重建复核），但其行为（ILLI/活锁）已独立复现。

**findings（文档/台账级，不阻断，交 architect 收尾改）**
- F1 完成区「构建 0 warning 已验」与现场不符：4 份真实重建日志各 36 条 `-Wunused-variable rdhb`（`trans_shift.c.inc`，本任务未改的既有告警）；实质结论成立——`unused-function` 命中 0（删除两个静态助手后无新增未用函数）。
- F2 `run.sh` 的 `build-qemu warnings=0` 只作用于 no-op 构建（stage-2 日志无编译输出），而基线本就有 36 条 ⇒ 一旦真重编必假红；建议改判「无 `unused-function`」或按基线差值比较。
- F3 `milestones-m13.md` 中 `m13-qemu-010` 行仍留在「待开始」表（应移「进行中」并填派单时间）；台账归主会话维护。
- F4 任务书验收①（去 `0x3F` 掩码）实测非 FAIL 路径、验收②链例形态实测为活锁 `-2`：engineer 已披露并补 `0x1F` 真红路径 + 故障例 `248`，≥2 条真红仍满足、属加强非弱化；若按「验收标准变更」口径，需主会话向用户报备。

**判决：Accepted** —— 验收命令块在本人重跑下全绿（71/71、264/264、红集恰 1 且改前后相同）、改前两种形态独立复现、2 路独立注入均红并还原回绿、硬约束无违反；F1–F4 为文档/台账级，记档不阻断（架构师终审）。

