# m13-testcases-033: `ext.uo`/`ext.so` orrr 的 `rdHD` 越界值（64 / 0x43 / 63）三平台用例

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-008` + `m13-qemu-010` + `m13-gem5-012`（三平台实现须先合入，否则用例必红）**+** `m13-testcases-017`（同目录 `ext.uo_orrr_rd.S` / `ext.so_orrr_rd.S` 载体由该任务建立，现为「进行中」⇒ 必须串行在其后）
**可并行分片**：否（共享 `tests/inst/04-arith-logic-octa/`）
**状态**：已验证

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

1. **三平台逐字节一致**：`python3 tools/testcases/inst/run_asm_suite.py --vectors tests/inst/04-arith-logic-octa --id ext.uo_orrr_rd --id ext.so_orrr_rd --platforms chipyard,qemu,gem5` `rc=0`，新增用例全部一致（用例数/检查点数现场值）；任一平台不一致 ⇒ **不得放宽期望**，登记 issue 并如实记红。
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

### 第 1 轮 engineer 自审

逐行审查两 `.S` 的新增段（点 17–22 + 故障点号顺延）与证据脚本（`run.sh` / `inject.py` / `check_points.py` / `probe_fault.py`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 点 19 的不变量配对选错源值：我按 `0xFFFF…FE` 写，既有 `rdHD=0` 边界例（点 4/5）源值是 `0x…00FE` ⇒ 配对 0 个、C3 红 | ✅已修 | 两文件点 19 源值改 `0x00000000000000FE`，注释改「与点 4/5 同源值 0x…FE」 | 证据 run：配对 4 组、不变量 12 行全 PASS |
| F2 注入② 的预期按「点号断档 ⇒ runner rc=2」写；实测故障行落在链例区中间 ⇒ 点号仍 1..N 连续、rc=1 | ✅已修 | `run.sh` 注入②判据改为「唯一红镜像 = 该故障镜像 + 三平台 rc=18≠248」，并保留 `probe_fault.py` 直跑三平台复核 | C6f/C6g/C6h 全 PASS |
| F3 C2c 用全输出 grep 计数 ⇒ 两 id 同值互相串（期望 1 实得 2） | ✅已修 | 先 `grep -F "$id.S"` 按 id 过滤再计数 | C2c 两 id 各 PASS |
| F4 还原判据原用「`git diff` 空」⇒ 本分支实现未提交、恒非空（恒假红） | ✅已修 | 改用「内容 md5 == 施工态」对账；注入生效改用「md5 已变化」判定 | 两次还原 md5 对账 PASS；C6j 收尾 md5 一致 |
| F5 文件头「待 spec 修正 / QEMU·gem5 判 ILLI 为缺陷」已过期，且措辞会暗示 issue 已关 | ✅已修 | 改「§2.2 已定稿 `hd=rdHD[5:0]`；QEMU/gem5 已按此修（`m13-qemu-010`/`m13-gem5-012`）」；故障段注释改「已收录为链例 17–22」 | `grep 待修/未收录` 两文件均 0；suite 全绿 |
| F6 期望值是否「抄平台输出」 | ❌不修（非缺陷） | 无 | `check_points.py` 按 spec 模型独立复算 40 点，与行内期望双向一致；平台输出只作比对 |
| F7 故障例点号 17→23 是否违「不改既有点号」 | ❌不修（必要） | 无 | 链例必须先于 `__TEST_END`，追加后故障点号顺延是唯一合法写法（`m13-testcases-031` 同例）；链例 1–16 点号未动 |

判决：finding 全部处置 ⇒ 状态置「待验收」。

### 第 1 轮 reviewer 验收

**重跑（HEAD=`8e847b05`；下列 rc 全部是我方实跑，不采信完成区转述）**
1. **spec 回核**：`spec/SimRISC-04-64位数据运算.md` L171–173（位段复制 + 符号/零扩展）、L177「`orrr` 形式 `hd = rdHD[5:0]`，更高位被忽略、不触发异常」、L181 约束列 ⇒ 与用户 2026-11-13 裁定一致，用例语义有 spec 依据。
2. **独立复算 40 点**（我方 `recompute.py`，按 `inst_test.inc` 别名跳过规则模拟寄存器态 + §2.2 模型，不读其 `check_points.py`/注释）：`reviewer 复算合计 40 点，不符 0 点` rc=0；再自读三平台 `.out`（我方 `read_out.py`，含点 1/2 编码字例共 44 点）：`不符 0 项` rc=0，不变量 12 行（2 id × 2 对 × 3 平台）全 PASS：uo `pt18=…0001≡pt17=…0001`、`pt19=0≡pt04=0`；so `pt18=…ffff≡pt17=…ffff`、`pt19=0≡pt05=0`。
3. **结构**：`run_asm_suite.py --vectors … --scan-only` rc=0 ⇒ 两文件各 `链例 22 + 故障例 1（点号 1..23 连续；≤127）`；`git diff --name-only 8e847b05^ 8e847b05` = 本任务书 + 2 片段 + `ext.uo_orrr_rd.S`/`ext.so_orrr_rd.S`，**无其它 `.S`**、未动根清单/`MIGRATION.md`/宏层/`run_asm_suite.py`。
4. **三平台逐字节**（任务书验收 1 原文缺 `--vectors` ⇒ 缺省 `01-load-store` 会 0 载体 rc=2，engineer 已在「坑②」披露，我按正确路径跑）：`… --platforms chipyard,qemu,gem5 --jobs 62` **rc=0，`4/4 镜像`**；链例各 22 检查点 =176 B、三方 rc 全 0，三方 md5 同值 uo `b9438efdb254adb6afd71344f281f10f`、so `a8f2d0012e365738034f86f20552bf89`；故障例三方 rc=248（`0xF8` ILLI）。
5. **改前对照**：`old-gem5.opt.pre-hd` md5 `b6440f19c19e02ab6408ffcf4b7acf75`（与 `m13-gem5-012` 任务书一致）跑同一批 ELF ⇒ 链例 rc=**-2**（240 s 超时：改前 ILLI 在链例里活锁）、0 B，故障例 248 PASS。因链例拿不到干净 248，我另写故障形探针复现点 18（`ext.uo rdHD=64`）：**改前 gem5 `GEM5_EXIT_CODE=248`、0 B；改后 gem5 rc=1；现行 QEMU rc=1** ⇒ 「新增点在改前抛 ILLI、改后继续执行」被实证。
6. **门控**：`make check-inst` **rc=2**，现场枚举红集与 `.work/evidence/m13-testcases-033/red-baseline.txt` `diff` **rc=0**（仅 `FAIL divrem.yaml[23]` + `Results: 1141 total, 1135 passed, 1 failed, 5 deferred…`），红集内 `ext.` 计数 **0**；`check-inst-smoke` rc=0（`QEMU: total=90 passed=90`）；`check-tests-index` rc=0（489）、`check-case-ledger` rc=0（2184）、`merge_fragments.py --check` rc=0（片段 1 / 新增 0）、`inst_sweep emit` rc=0 `covered=273`、`sweep_expect.bin` md5 `2d4d94651346ef673c5a855e024c1489` 不变。
7. **独立注入 1 路**（自设计，非其两路）：点 20（`rdHD=67`）期望 `0x0000000000000009` → `0x00000000000000E9`（= hd=7 的值）⇒ 三平台同点号红 `rc {'chipyard': 20, 'qemu': 20, 'gem5': 20}`、runner rc=1；`cp` 还原后 md5 `66f7bd6154d37210cd3255452b1d8b1b` == `git show HEAD:` 版本 ⇒ 回绿 rc=0。全程未用 `git checkout/restore/stash`。
8. **重跑其证据脚本**：`bash .work/evidence/m13-testcases-033/run.sh` **rc=0**，`总计：检查 48 项，失败 0 项`（100 行 `[PASS]`）；逐条断言有可达 FAIL 路径（第 7 项已独立复现 FAIL），计数为现场派生。
9. **对账**：`git status --porcelain -uall` 与 `git diff --stat` 均空（本审阅记录写入前）；完成区 14 行（≤30）；两 `.S` 施工态 md5 == HEAD 版本。

**并行度/资源（用户 2026-11-14 新规）**：预检 `tools/infra/remote.py status --hosts ics160,server208 --repo /home/ubuntu/DADAO-v5` rc=0（`disk_use_pct=25`、`mem_avail_mb=125031`、`running=none`、两 host 均 PASS）+ 主控机 `make check-disk` rc=0（5%）+ `free -g` available=119 GiB + 无 `build-*` 在跑 ⇒ 未触发停跑阈值。跑批用 `--jobs 62`（=64−2；本分支 `run_asm_suite.py` 默认仍 `nproc//2=32`，`cec70447` 未入本分支，故显式传 62，未手写 20/32 经验值），**实际并发 = 4 镜像**（任务数上限），三平台墙钟 **12 s**、证据脚本 **110 s**。本任务在主控机本地跑（本地 qemu/gem5/chipyard，md5 已记：qemu `b34ed7f9…`、gem5 `49e600e3…`、chipyard `ac35dffb…`），未向节点派测试 ⇒ 未执行 `sync_node_artifacts.sh`；全程未构建。

**约束核验**：独立 worktree ✓｜不提交 git ✓｜完成区与真实输出逐条对齐 ✓（48/48、22 点/176 B、248、489/2184/273 均现场复核）｜只动任务书范围 ✓｜临时文件仅在 `/tmp/opencode/m13-testcases-033/` ✓｜禁 `install-host`/`check-modules`/`build-*` ✓｜反例注入 `cp`+md5 还原并回绿 ✓。

**判决：Accepted** —— 验收标准 1–6 在我方重跑下全过，硬约束无违反（40 点独立复算 0 不符、三平台逐字节一致、改前对照证守护、红集不扩大、注入可达 FAIL 并回绿）。遗留（不阻断，归主会话/架构师）：① 任务书验收 1 的命令缺 `--vectors`，建议补字；② `cec70447` 未入本分支 ⇒ 合并后 `run_asm_suite` 默认才变 62；③ 完成区「坑④」两处既有 L1 红（`check-knowledge-refs`、`check-patch-tree`）与本任务无关，待收口；④ `ISS-422` 关闭归主会话。

## 完成区

**测试结果**：通过 48/48（一键证据脚本 `.work/evidence/<任务ID>/run.sh` rc=0）。
- 三平台 `run_asm_suite.py --vectors tests/inst/04-arith-logic-octa --id ext.uo_orrr_rd --id ext.so_orrr_rd --platforms chipyard,qemu,gem5` rc=0：4/4 镜像，两 id 链例各 22 检查点 / 176 B（三方字节流逐字节相同），故障例三方 rc=248（`0xF8` ILLI）。
- 不变量（原始 8 字节，三方各自成立）：uo `rdHD=64(pt18)=0000000000000001` ≡ `rdHD=0(pt17)=0000000000000001`、`pt19=0000000000000000` ≡ `pt04=0000000000000000`；so `pt18=ffffffffffffffff` ≡ `pt17=ffffffffffffffff`、`pt19=0000000000000000` ≡ `pt05=0000000000000000`。
- 独立复算（`hd=rdHD&0x3F` + 零/符号扩展模型，读结果缓冲）：40 点、不符 0；配对 4 组 × 3 平台全等。
- `check-inst` rc=2，红集 == 施工前基线（`FAIL divrem.yaml[23]`；`Results: 1141 total, 1135 passed, 1 failed, 5 deferred`），红集内 `ext.*` 计数 0（该门控载体为 YAML，不跑 `.S`）；`check-inst-smoke` 90/90 rc=0。
- 门控：`check-tests-index` rc=0（489）、`check-case-ledger` rc=0（2184）、`merge_fragments --check` rc=0（片段 1 / 新增 0）、`check-dirs`、`check-no-residue` rc=0；`inst_sweep emit` covered=273、`sweep_expect.bin` md5 `2d4d94651346ef673c5a855e024c1489`（不变）。
- 注入（`cp`+md5 还原，生效以 md5 变化判定）：① 点 18 期望改 `0x7` ⇒ 三平台同点号红（`rc {'chipyard':18,'qemu':18,'gem5':18}`），还原后回绿；② 点 18 改 `TEST_FAULT_ALU3 …, ILLI` ⇒ 三平台实测 exit=18（**不**抛 `0xF8`）⇒ 唯一红镜像即该例（点号仍连续，红来自行为），还原后回绿。
**修改文件**：`tests/inst/04-arith-logic-octa/ext.uo_orrr_rd.S`、`ext.so_orrr_rd.S`（各 +6 链例 = 点 17–22；故障例点号 17→23）、`tests/inst/.fragments/m13-testcases-033.inst.yaml`（空列表：两 id 已由 017 登记）、`tests/inst/.fragments/m13-testcases-033.migration.md`；`git status -uall` = 3 改（2 个 `.S` + 本任务书）+ 2 新增片段，与清单一致。
**验收结果**：见上（真实 rc 逐条）；三平台日志落运行期日志目录。
**新发现/坑**：① 把链例行原地改成故障宏时，故障行落在链例区中间 ⇒ 点号仍 1..N 连续、runner **不**结构拒绝，红来自行为（fault 镜像 exit=pt≠0xF8）——注入②预期须按此写。② `run_asm_suite.py` 默认 `--vectors` 是 `01-load-store`，跑本册须显式给 `--vectors tests/inst/04-arith-logic-octa`（缺省会 0 载体 rc=2）。③ 既有 `rdHD=0` 边界例源值是 `0x…00FE`（非全 1 尾），不变量配对须按源值现场派生、不能凭印象。④ 两处**既有** L1 红与本任务无关（现场在证）：`check-knowledge-refs` 的唯一具体 `.work/**` 引用在 `m13-gem5-012` 任务书；`check-patch-tree` 因并发组件任务改动共享源码树（qemu/chipyard worktree 脏）。建议主会话后续收口（不代改他任务文件）。
**遗留问题**：无（本任务范围内）；`ISS-422` 的 issue 关闭归主会话。

