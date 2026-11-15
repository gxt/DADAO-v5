# m13-testcases-048: 伪指令专用汇编载体（7 个展开形态，`tests/inst/00-isa-design/`）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-010`（`rf2rf` 已合）、`m13-spec-011`（伪指令正文迁入 `SimRISC-00 §5`、写宽对照表）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：待验收

## 用户裁定（2026-11-15）

> 「同意A，两个补充也可以。SimRISC-03 中的伪指令应该移动到 SimRISC-00的第5章…；此外，在tests/inst/00 目录下，新增这7种伪指令的专门的汇编测试」
> 随后确认口径 **a（按展开形态 7 个）**：「a；或者，就以伪指令名称来区分也可以，那就4个；你的建议」

**采纳 (a) 7 个展开形态**（主会话建议，理由：失败归因可定位到具体形态；`set.ft` 的 imm 窄写 vs reg 整 64 位正是本次裁定点，合并会互相掩盖）。

> **追加裁定（2026-11-15，文件名）**：「文件名定了（用户 2026-11-15 裁定：方案 A，第 7 个用 `fx`）」——
> 名字里保留助记符点号（`pseudo_set.rd_imm.S` … `pseudo_set.fx_reg.S`，与 `ld.o_*`/`sc.b.nn_*` 同风格）；
> 第 7 个用 **`fx`**（= `ft`/`fo` 两族，两者从 rf 源展开都是 `rf2rf`、语义一致）。
>
> **追加硬要求（2026-11-15，rb 覆盖）**：「rb 寄存器应该要测到完整 64 位」——载体 3/4 须四个 wyde
> （wp3/wp2/wp1/wp0）各有非零且被校验的用例；须测「高 32 全 1」「稀疏位型」「`set.rb rb, 0` 清其余
> 48 位」；校验必须 64 位（沿 `st.o` + `__CHECK_MEM`，禁只比低半）；载体 4 两种源各至少一例源值
> 高半非零。

## 7 个载体（`tests/inst/00-isa-design/`）

| # | 载体 | 覆盖的展开形态 | 关键点 |
|---|---|---|---|
| 1 | `pseudo_set.rd_imm.S` | `set.rd rd, imm64` → 1–4 条 `set.zw/set.ow` + `or.w/andn.w` | 零/全 1/±小值/稀疏位型；**只能一条 `set.zw`/`set.ow`**；指令数最少化 |
| 2 | `pseudo_set.rd_reg.S` | `set.rd rd, rs` → `rb2rd`/`rf2rd`/`ra2rd`/`rd2rd` | 四种源银行各 1 点；整 64 位 |
| 3 | `pseudo_set.rb_imm.S` | `set.rb rb, imm64` → `set.zw-rb` + `or.w-rb` | **rb 无 `set.ow`** ⇒ 负值形态与 rd 不同；只能一条 `set.zw`；**四个 wyde 各专例** |
| 4 | `pseudo_set.rb_reg.S` | `set.rb rb, rs` → `rd2rb`/`rb2rb` | 两种源各含高半非零例；**四个 wyde 各专例**；整 64 位校验 |
| 5 | `pseudo_set.ft_imm32.S` | `set.ft rf, imm32` → 2× `set.w` | **只写低 32、高 32 不动**（写宽对照表第一行）；边界 imm=0 / 0xFFFFFFFF |
| 6 | `pseudo_set.fo_imm64.S` | `set.fo rf, imm64` → 4× `set.w`（imm=0 ⇒ `rd2rf` from `rd0`） | 整 64 位；`imm=0` 走 `rd2rf` 特例 |
| 7 | `pseudo_set.fx_reg.S` | `set.ft/set.fo rf, rf` → **`rf2rf`** | **整 64 位**（写宽对照表第二行，`m13-spec-010` 后可观察变化）；高半必须被覆盖；`fx` = `ft`/`fo` |

## 任务

1. 新建 7 个 `.S`：**检查点内联期望**（`inst_test.inc` 现有宏优先，缺宏时在 `.S` 内 `.macro`），每册 **≤127 点**、点号连续；期望全部由 `SimRISC-00 §5` + `SimRISC-03`（新三章）+ `SimRISC-02` 推导，**不得从 qemu/llvm 反推**；
2. **双注册表**：`tools/testcases/validate_vectors.py::NON_ID_CARRIERS` 与 `tools/testcases/check_tests_index.py::NON_ID_CARRIERS` **逐文件**登记（现只有 `undi_reserved.S` 一条）；`tests/inst.yaml` 增 7 条索引（`platforms: [system]`、`level: full`）；
3. `tests/case-ledger.tsv` 重生成；`tests/inst/README.md` 与 `MIGRATION.md` 同步（新增一节说明伪指令载体）。
4. **写宽对照**：载体 5 与 7 必须各自断言"高 32 保持" vs "高 32 被覆盖"，成为这次语义变化的第一道回归。

## 验收（逐条贴真实 rc）

1. 7 个载体均能汇编（安装根 `llvm-mc` 已支持 `rf2rf`）并在 qemu 上执行：贴 `run_asm_suite --platforms qemu` 的 id/镜像/检查点计数与 rc；
2. 每册 ≤127 点、点号连续；`validate-vectors`（非 id 载体 8 条：`undi_reserved` + 7）、`check-tests-index`（现场条数）、`check-case-ledger` rc=0；
3. **注入 ≥2 路**（`cp`+md5 还原）：① 把载体 5 的期望改成"高 32 被覆盖" ⇒ 应红（证明它守的是窄写）；② 把载体 7 的期望改成"高 32 保持" ⇒ 应红；
4. `check-inst-asm` 现场计数（id 数不变 264；镜像数 +新增）；`check-no-residue`、`check-knowledge-refs` rc=0；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 命名裁定（用户 2026-11-15）

- 采用**方案 A**（保留助记符点号）：`pseudo_set.rd_imm.S`、`pseudo_set.rd_reg.S`、`pseudo_set.rb_imm.S`、`pseudo_set.rb_reg.S`、`pseudo_set.ft_imm32.S`、`pseudo_set.fo_imm64.S`、**`pseudo_set.fx_reg.S`**（`fx` = `ft`/`fo` 两族寄存器源，二者都展开 `rf2rf`）；
- 索引 id 顺延：`inst-00-isa-design-002` … `-008`（`-001` 归 `undi_reserved.S`）。

## 硬约束

- 只改 `tests/inst/00-isa-design/**`、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tools/testcases/{validate_vectors.py,check_tests_index.py}`（仅 `NON_ID_CARRIERS` 登记）、`tests/inst/{README.md,MIGRATION.md}`、本任务书；
- **不改** `spec/`、`contracts/`、`components/**`；禁 `install-host`/`check-modules`/`build-*`；不 sync/reset 节点；不提交 git；注入还原 `cp`+md5。

## 待裁定

1. `spec/Toolchain-01 §6.1` 的 `set.fo` 展开细节写「**零 wyde 不再逐条 `set.w`**」，而安装根 `llvm-mc`
   对非零立即数一律发 4 条 `set.w`（含零 wyde）——**可观察结果相同**（`rd2rf` 已清零，再发 `set.w 0`
   等价），但正文与实现的**形状**不一致。属 `m13-spec-011`（正文迁 `SimRISC-00 §5`）/ LLVM 侧口径，
   本任务不改 spec、不据此放宽断言（证据脚本只断言 spec 明示的「`imm=0` ⇒ 仅 1 条 `rd2rf`」）。

## 完成区

**测试结果**：通过 43/43（证据脚本 `run.sh`：A 门控 3 / B 展开形状 11 / B' 聚合形状 12 / B2 独立重算 8 / C 执行 1 / D 注入自检 8）；失败 0。
**修改文件**：`tests/inst/00-isa-design/pseudo_set.{rd_imm,rd_reg,rb_imm,rb_reg,ft_imm32,fo_imm64,fx_reg}.S`（新增 7）；
`tests/inst.yaml`（+7 条索引 `inst-00-isa-design-002`…`-008`）；`tests/case-ledger.tsv`（重生成，+113 行）；
`tools/testcases/{validate_vectors,check_tests_index}.py`（`NON_ID_CARRIERS` 各 +7 条，共 8）；
`tests/inst/{README.md,MIGRATION.md}`；本任务书。
**验收结果**：
- 载体规模：7 册检查点 20/10/20/20/15/15/13 = **113**，点号各 1..N 连续（`--scan-only` 现场统计）；全是链例，无故障例（伪指令的非法操作数由**汇编器**拒绝，非运行期异常）。
- 执行（三平台同轮 `--platforms qemu,gem5,chipyard`，`EXIT=0`）：**10/10 镜像通过**（7 链例 + UNDI 3 故障例）；链例字节数 120/120/104/160/160/160/80 B = 8×检查点，三平台**逐字节一致**、rc 全 `0`（`rd_imm 20 / rd_reg 10 / rb_imm 20 / rb_reg 20 / ft_imm32 15 / fo_imm64 15 / fx_reg 13` 点）。
- rb 覆盖（追加硬要求）：`rb_imm` 点 2/3/4/5 = wp0/wp1/wp2/wp3 专例、7 四 wyde 全非零、8 高 32 全 1、13 稀疏 `0x8000000000000001`、1 & 19 `set.rb rb,0` 清其余 48 位；`rb_reg` rd 源 1/2/3/4/5/6/7（含 wp3/wp2/wp1/wp0 专例）、rb 源 9/10/11/12/13/14 + 15 全 1 + 16 稀疏。校验宽度 **64 位**：`st.o <目的 rb>, [rb29,0]` + `__CHECK_MEM pt, SCRATCH, 0, <期望 64 位>`（整 8 字节 beat 比），无只比低半；既有宏够用，未新增 `.macro`。
- 门控 rc：`check-tests-index` 0（inst 索引 280、载体↔索引 271/271、非 id 8、每 id ≤34）、`validate-vectors` 0（156/156 M1、271 载体、8 非 id）、`check-case-ledger` 0、`check-no-residue`/`check-dirs` PASS、`check-knowledge-refs` 0。
- `check-inst-asm` 等价全量（`--books-root tests/inst --platforms qemu --jobs 32`）：**903/903 镜像通过**（271 个 `.S` 载体 = **263 个 id 载体 + 8 个非 id 载体**；链例 270 / 故障例 633），`EXIT=0`；改前 896 镜像 / 264 载体 ⇒ **+7 镜像、+7 载体**，**opcode id 0 变化**（`contracts/opcodes.yaml` 现 263 个 id，全被 `.S` 载体覆盖，缺 0；任务书写 264 是 `m13-spec-010` 前的旧数）。
- 独立重算（`recompute.py`，只读 `.S` + 宏层 RDATA 字面量，**不经 LLVM/QEMU**）：按 spec 规则（立即数 → 完整 64 位位型 / `set.ft` 窄写 / `rf2rf` 整 64 位）对 7 文件 **113 个检查点全量重算**，逐点与内联期望一致（7/7 文件 rc=0）；把点 1 期望改坏（临时副本）⇒ 重算非 0（可达 FAIL）。
- 注入（`cp` 备份 + md5 还原，禁 `git checkout`）：① `ft_imm32` 点 1 期望 `0xA5A55A5A00000000`→`0x0000000000000000`（假装「高 32 被覆盖」）⇒ 红（qemu rc=1，检查点 1）；② `fx_reg` 点 1 期望 `0x0000000012345678`→`0xAAAAAAAA12345678`（假装「高 32 保持」）⇒ 红（rc=1）。两侧还原 md5 逐个相等、注入后各自回绿。
**新发现/坑**：见「待裁定」1（`set.fo` 零 wyde 形状与正文不一致，观察等价）；载体行必须用 `__CHECK_RD`/`__CHECK_MEM` 等既有宏名开头才会被 `run_asm_suite.scan_source` 计入检查点（自定义宏名开头的行会被静默漏计）；rb 载体整文件 `set.zw` 计数含宏层 `__LI`/`LOAD_ADDR` 的种子（157 条），故「一条种子」只能对单个 probe 断言、不能按文件聚合；`tests/inst/MIGRATION.md §4` 的「合计 264 个 id」是 `m13-spec-010` 前的旧数（现 263），本任务未改（非本任务范围，留给主会话）。
**遗留问题**：无（`fx` 命名的任务书表格/注册表/索引/ledger 均已按方案 A 对齐）。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：7 个 `.S` 逐行（用例值 / 期望派生 / 保留寄存器 / 点号）+ 两处 `NON_ID_CARRIERS` + `inst.yaml` + ledger + 两个文档 + 证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 三元组期望与 spec 不符的风险：`set.ft imm32` 高半、`rf2rf` 高半 | ✅已修（初版即按 spec 写，补注入证明可达 FAIL） | 未改用例；补 2 路注入 | 注入①/② 均红，还原回绿 |
| F2 载体 3/4 只测到低 32 位（用户追加硬要求） | ✅已修 | 重写两册：各加 wp3/wp2/wp1/wp0 单 wyde 专例、高 32 全 1、稀疏位、`set.rb rb,0` | qemu 20/20 点绿；全文 `set.ow`=0、`set.w`=0；`#rd2rb`=11、`#rb2rb`=9 与源码计数一致 |
| F3 用例行宏名不符 harness 正则 ⇒ 静默漏计 | ✅已修 | 一律用 `__CHECK_RD`/`__CHECK_MEM` 作检查点行，未新增宏 | `--scan-only` 报 20/10/20/20/15/15/13 点，点号连续 |
| F4 保留寄存器被占用（初版 `rb21`/`rb22`） | ✅已修 | 改用 `rb25`/`rb26`/`rb31`（`rb21` 是 `__CHECK_MEM` 的临时寄存器） | qemu 全绿；`git diff` 无其它寄存器冲突 |
| F5 证据脚本 B12（聚合种子计数）恒真/错口径 | ✅已修 | 改为单 probe 断言（四 wyde 全非零 / 全 1），TAB 用 `printf` 生成 | 证据脚本 B12/B12b 实际=期望（4\|1\|0、4\|1\|3\|0） |
| F6 注释与实现的展开选择不符（「种子在最低非零 wyde」） | ✅已修 | 注释改为与实现无关的表述（一条种子 + 逐 wyde 修正） | 证据脚本 B6/B7/B12b 断言的形状成立 |
| F7 内联期望只靠「三平台一致」验证（同源自比风险） | ✅已修 | 新增独立重算脚本（按 spec 规则重算 113 点，不经 LLVM/QEMU）+ 其可达 FAIL 演示 | 7/7 文件 113/113 点一致；改坏一条期望 ⇒ 重算非 0 |

**判决**：全部 finding 已修，无未修项 ⇒ 状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（均本人执行，worktree 内相对路径）**
- 证据脚本 `WT=<本worktree> <运行期证据目录>/run.sh` ⇒ **PASS=43 FAIL=0，rc=0**（A 门控 3 / B 形状 11 / B' 聚合 12 / B2 重算 8 / C 执行 1 / D 注入 8）；其自带两路注入（`ft_imm32`「高32被覆盖」、`fx_reg`「高32保持」）均报 FAIL、还原 md5 相等后回绿。
- 门控：`check-tests-index` rc=0（inst **280** / 载体↔索引 **271/271** / 非 id **8** / 每 id ≤34）、`validate-vectors` rc=0（**156/156**、271 载体、8 非 id）、`check-case-ledger` rc=0（现场 5425，`pseudo_set` **113** 行）、`check-no-residue` rc=0、`check-knowledge-refs` rc=0（悬空 0）、`check-inst-asm` rc=0 ⇒ **903/903**（271 id；链例 270 / 故障例 633）。
- 执行：qemu **10/10**（点数 15/15/13/20/20/20/10 = **113**，字节 120/120/104/160/160/160/80 = 8×点数）；另跑 gem5+chipyard **10/10** 且字节与 qemu 相同 ⇒ 三平台逐字节一致（完成区该条属实）。

**用户点名两项**
- **rb 64 位**：`rb_imm` 点 2/3/4/5 = wp0/wp1/wp2/wp3 单 wyde、7 四 wyde 全非零、8 高 32 全 1、13 稀疏 `0x8000000000000001`、19 `set.rb rb,0` 清高 48；`rb_reg` rd 源 4/5/6/7 单 wyde、rb 源 11/12/13/14 单 wyde、rd 源 1 与 rb 源 10 高半非零。宏 `__CHECK_MEM` = `st.o` 8 B → `ld.o` 8 B → `__LI` 64 位期望 → `br.eq` 整 64 位（无只比低半）。抽点按 spec 复核：`set.rb rb, 0xFFFFFFFFCAFEBABE` ⇒ pt8、`set.rb rb, 0x8000000000000001` ⇒ pt13，期望 = 立即数完整 64 位位型，一致。
- **窄/宽对照**：`ft_imm32` pt1 期望 `0xA5A55A5A00000000`（高 32 保持写前值）、`fx_reg` pt1 期望 `0x0000000012345678`（高 32 被源覆盖，目的旧值 `0xAAAAAAAA…`）⇒ 两者确实相反且各自成立。

**独立性与注入**
- `recompute.py`：仅 import `re`/`sys`/`pathlib`，不读 qemu/llvm 输出、不 import 被测实现、逐行 fail-closed；本人把 `rb_imm` pt7 期望改坏（临时副本）⇒ **rc=1**「重算 0xDEADBEEFCAFEBABE ≠ 内联期望」。
- 本人 2+1 路注入（`cp` 备份 + md5 还原，非 engineer 那两路）：① `rb_reg` pt10 期望高半清零 ⇒ qemu **rc=10**；② `rb_imm` pt8 高 32 全 1 期望清零 ⇒ qemu **rc=8** 且 recompute rc=1；③ `rd_imm` pt1 拆成两条同值指令 ⇒ qemu 绿但 recompute fail-closed rc=1，拆成两条异值 ⇒ qemu rc=1。三文件 md5 还原后与注入前逐一相等、回绿 rc=0。

**命名 / 索引 / 注册表 / 越界**
- 7 个文件名与裁定逐字一致（`pseudo_set.rd_imm/rd_reg/rb_imm/rb_reg/ft_imm32/fo_imm64/fx_reg.S`）；`inst.yaml` `-001..-008` 顺延（`-001` = `undi_reserved`，无冲突），`platforms: [system]`、`level: full`；两处 `NON_ID_CARRIERS` 均**逐文件**键 + 理由，无目录级豁免。
- `git show a1baafe7 --name-only` 共 14 个文件，全在任务书允许清单内；`spec/`、`contracts/`、`components/`、`tests/inst/12-misc/**` 改动 **0**；`git status -uall` 干净（注入前后各记快照，md5 全等）。完成区 17 行、无运行期路径。

**未决（不阻断，留 architect）**：① `Toolchain-01 §6.1` 零 wyde 形状 vs `llvm-mc` 实发（可观察等价）；② `MIGRATION.md §4`「264 个 id」旧数（`opcodes.yaml` 实测 **263**，非本任务范围）。

**判决：Accepted**
