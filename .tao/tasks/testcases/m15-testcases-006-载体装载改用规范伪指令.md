# m15-testcases-006: 载体装载改用规范伪指令（`__LI`/`__LI_RB`/`__LI_RF` → `set.rd`/`set.rb`/`set.fo`）

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-005`（**已验证**：前缀 `__PREP_` + 剔 `__LI2`，已合入）
**可并行分片**：可（按册；同一册单写者），但建议按册分批、每批独立对账
**预估**：8–10 h（254 文件、1691+133+128 处调用 + lds 统一与 12 册重验）
**档位**：大改（判据口径切换 + 全仓结构重构；复核 ≥4 路注入 + 行为级全量对账）
**状态**：已验证

## 背景（用户 2026-11-16 裁定「同意」）

用户原话：「`__LI` 没必要，就用 `set.rd` 即可；`__LI_RF` 更没必要，就用 `set.ft/fo` 即可」，随后确认三点：**① `__LI_RF` 一律用 `set.fo`（不用 `set.ft`）② `__LI_RB` 一并换 `set.rb` ③ 等价判据改为行为等价**。

现状（现场统计）：

- `__LI`（`rd`）：**214 个 `.S` / 1691 处**；`__LI` 是"固定 4 条"（`set.zw` + 3×`or.w`，**不做最少指令数优化**）；
- `__LI_RB`（`rb`）：33 个 `.S` / 133 处；同构（`set.zw-rb` + 3×`or.w-rb`）；
- `__LI_RF`（`rf`）：7 个 `.S` / 128 处；实现是 `__LI rd20, val` + `rd2rf`（**整 64 位**）。

**为什么改**：`set.rd`/`set.rb`/`set.fo` 是**规范里的伪指令**（`Toolchain-01 §6`），载体另造一套"装载宏"= 测试层重复实现 + 绕过伪指令覆盖；改后 2691 处调用点都在**测伪指令展开**，且测试层与规范单一真源。

## 目标

1. **`__LI rd, imm` → `set.rd rd, imm`**（214 文件 / 1691 处，含 `.inc` 宏体内调用）；
2. **`__LI_RB rb, imm` → `set.rb rb, imm`**（33 文件 / 133 处）；
3. **`__LI_RF rf, imm` → `set.fo rf, imm`**（7 文件 / 128 处）——**只用 `set.fo`**（整 64 位：`rd2rf rf, rd0` + 非零 wyde 的 `set.w`）。**禁用 `set.ft`**：它是**窄写**（只写低 32、高 32 保持），与 `__LI_RF` 的整 64 位语义不同，而 FP 用例依赖"源 = 精确 64 位模式"（`__FP_CHK64` 逐位比整 64 位）。
4. **删除三个装载宏定义**（`inst_test.inc` 内），并核全仓 `grep -c '__LI\b'` = **0**（含 `.inc`）；
5. **`tests/inst/README.md`** 写明：「**载体准备段一律用规范伪指令**（`set.rd`/`set.rb`/`set.fo`；`set.ft` 仅用于被测指令本身的窄写场景），不再另造装载宏」。
6. **lds 统一为 FP 布局**（用户 2026-11-16 裁定「同意用 fp 的布局」）——见下节。

## lds 统一为 FP 布局（与装载伪指令同轮验，只重跑一轮 904 镜像）

现状两份布局只差**地址偏移**，结构相同：

```
                    01-load-store/inst-tiny.lds   07-floating-point/inst-tiny-fp.lds
.text               0x0000（≤0x1E00）              0x0000（≤0x4000）
.faultpad           0x1F00                         0x4000
TEST_FAULTV         0x1F80                         0x4080
.testdata           0x2000                         0x5000
TEST_DATA           0x2800                         0x5800
TEST_BUF（结果）    0x4000                         0x7000
TEST_EXITB          0x5000                         0x7800
```

改动：

1. **删两份册内 lds**，留**单一** `tests/inst/linker/inst-tiny.lds`（用 FP 布局，段址/ASSERT 原样搬运）；
2. **宏层删 `__FP_LAYOUT` 分支**（`tests/inst/macros/inst_test.inc` 顶部 `.equ` 只留 FP 那一套）；
3. 删 `07-floating-point/*.S` 里的 `.equ __FP_LAYOUT, 1`（8 个文件）；
4. `tools/testcases/inst/run_asm_suite.py` 的「每册目录内唯一 `.lds`、无则退默认」改为「**单一默认布局 + `--lds` 覆盖**」；
5. 收益（要写进完成区）：地址表从「宏层 `.equ` + lds 段址/ASSERT 两处逐项对应」变为**单点**；`.text` 窗口 7.5 KiB → 16 KiB，后续加用例不必为某册单开布局；
6. 代价：904 个镜像的**地址全变** ⇒ 判据只用行为等价（`semi.out` 字节 + 退出码），**不用**镜像字节比；镜像体积约 +8–10 KiB/个，只落工件盘。

## 三个已识别的风险点（必须逐个验证并留证）

1. **符号/地址表达式**：现存调用如 `__LI rd5, (0x003F000000000000 + MEMRAS + 0x80)`、`(0x0001000000000000 + ENTRY + 0x1000)`。`set.rd` 对**符号/可重定位**走"偏移地址 = 有符号、不限指令数"路径（`Toolchain-01 §6.1`），与 `__LI` 的纯常量 4 条展开不同 ⇒ 必须逐处验证**装入位型不变**（尤其 > 2^47 的 48 位常量、以及含 `ENTRY`/`MEMRAS` 的表达式）。若某处 `set.rd` 语义不等价 ⇒ **保留现场停下报告**，不擅自改写常量。
2. **`.org` 钉地址**：`01-load-store/ld.o_rrii_ra.S`（`.org 0x1000`）、`01-load-store/st.o_rrii_rb.S`（`.org 0x1800`）用 `.org` 钉被测指令地址；代码缩短后 `.org` 仍成立（填零），但须核 `TEST_PAD` 与 `inst-tiny.lds` 段上限 ASSERT 仍通过。
3. **宏体内调用**：`__LI` 在共享层/册宏体里也有调用（`__PREP_*`/`TEST_*` 等），必须**连宏体一起换**，否则 `.S` 换了、宏里还是旧的。

## 验收（真实 rc + 输出；判据 = 用户 2026-11-16 裁定的**行为等价**）

1. **行为等价（核心）**：全仓 **272 id / 904 镜像**，改前/改后逐镜像比 **`semi.out` 字节 + 退出码**。判据按三段分解（用户 2026-11-16 口径）：**A′↔C（只差装载手段）903/904**、**A↔A′（只差布局）899/904**，其余差异须逐条定性为「地址类/布局类且 rc=0」；`A2↔C` 的 rc 差必须为 0；
2. **检查点不变**：逐文件比「链例数 + 故障例数 + 点号序列」，0 处不一致；
3. **镜像数/id 数不变**（904 / 272），`check-inst-asm` **904/904 PASS**；**12 册全部用同一份 `tests/inst/linker/inst-tiny.lds`**（`grep -rn '__FP_LAYOUT' tests/inst` = 0；册内无 `.lds`），lds 的段上限 `ASSERT` 全过；
4. **装载宏清零**：`grep -c '__LI\b\|__LI_RB\|__LI_RF'`（含 `.inc`）= **0**；`set.rd`/`set.rb`/`set.fo` 的调用数分别 ≈ 1691 / 133 / 128（现场统计，允许因宏体合并而不同，须解释）；
5. **三个风险点**逐项留证：① 符号表达式逐个列出并给"值不变"证据；② `.org` 两例的段上限 ASSERT 通过；③ 宏体已一并替换（grep 证据）；
6. **≥4 路注入**（`cp`+md5 还原）：① 把某 `set.fo` 改成 `set.ft` ⇒ 该 FP 用例行为红（**证明这条禁则是必要的**）；② 把某 `set.rb` 改成 `set.rd`（装错 bank）⇒ 红；③ 把某符号表达式里的 `ENTRY` 常量挪 1 ⇒ 红；④ 把某 `set.rd` 的最小展开改成固定 4 条（人为）⇒ 若行为仍同，说明等价判据靠行为而非字节（记录）；若红则解释；
7. 门控：`check-inst-asm`、`check-case-ledger`、`check-inst-macro-scope`（含 S9）、`check-tests-index`、`check-dirs`、`check-no-residue`、L1 `make check`；
8. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **不改变任何用例的期望值/检查点/用例顺序**；只换"装载手段"；
- **不得**用 `set.ft` 替代 `__LI_RF`（见目标 3）；
- 只动 `tests/inst/**`（`.S`/`.inc`/`README.md`/`linker/`）、`tools/testcases/inst/run_asm_suite.py`（仅 lds 选择逻辑）、本任务书；不动 `tests/arch/**`、`components/**`、`spec/`、`contracts/`；
- 构建/跑批不得与其它任务并行（`ISS-462`：共享 linux 构建树 / 共享 QEMU 安装根）；
- 不提交 git；注入还原 `cp`+md5（**禁 `git checkout/restore`**）；基线钉死 commit（`ISS-458`）。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-16）：**Accepted**

**重跑（全部本人执行，输出/退出码为实测）**：① `bash 运行期证据目录内的 `run.sh`` ⇒ **50/50 PASS、rc=0**；A′↔C **903/904**（唯一差异 `st.o_rrii_rb.S#0`，两侧 rc=0，cp15 −0x120 / cp16 −0x134）、A↔A′ **899/904**（5 镜像 7 检查点全 `+0x3000`、两侧 rc=0）、检查点 272 id/0 不一致、`check-inst-asm` 904/904、门控 6 项 PASS。② 抽查 `ld.o_rrii_ra`/`st.o_rrii_rb`/`foadd_orrr_rf` ⇒ 3/3、3/3、2/2 全 rc=0。③ `make check -k` ⇒ L1 rc=2，**5 项失败逐项归因**（均非本任务，见下）。

**行为等价两处定性（独立复现，非采信）**：① `st.o_rrii_rb` — objdump 两树 ELF：A′ `aip.si@…0990`/`rb2rb@…0a04`、C `aip.si@…0870`/`rb2rb@…08d0`，差 **0x120/0x134 恰等于 cp15/16 的 delta**，且两值各自 = 指令地址+8 ⇒ 差异**纯为指令流变短致 IP 前移**，检查点期望由 `__CHECK_MEM_RB` 运行期从 rb12/rb13 派生、断言两侧各自成立（rc=0），**被测语义未改坏**。**结论：检查点记录 IP 值可接受**——README 判据是「同一份 ELF 三平台比」，同 ELF ⇒ 指令流固定 ⇒ IP 固定 ⇒ 仍可比；改成相对偏移反而弱化本用例「IP 取值正确性」的被测语义，不必改。② A↔A′ 7 个 `+0x3000` — 逐值核：`…4078/4080/4008`=TEST_BUF、`…2988`=TEST_DATA、`…3a00`=MSTORE，+0x3000 恰为布局上移量，期望均为符号派生（两侧 rc=0）⇒ **确为数据区上移、断言仍全过**。

**判据未被偷换**：判据 = `semi.out` 字节+rc（非镜像字节）；三棵树**全量 904 逐例 rc** 现场统计分布逐例相同（`{0:271,248:469,241:96,252:50,249:5,242:9,250:2,251:2}`），A2↔C rc 不同 = 0；**自设计注入②**（`andn.w_rwii_rd` 的 `set.rd` 人工拆成等价固定 4 条）⇒ **rc=0 不红**，证明判据靠行为而非指令流/字节，非只挑通过镜像报数。

**`set.ft`/`set.fo` 逐条**：`set.ft`=15 处**全在** `00-isa-design/pseudo_set.ft_imm32.S`（被测窄写；基线同 15 处、diff 中 **±set.ft 助记符行 = 0**，未新增任何装载用 `set.ft`）；`set.fo`=82 处 = 07 册 45 + `rf2rf_orri_rf` 20 + `pseudo_set.fo_imm64` 15（被测）+ `pseudo_set.rd_reg` 2，**全为整 64 位写**，07 册 `set.ft`=0。

**lds 统一**：`__FP_LAYOUT`=0、册内 `.lds`=0、`tests/inst` 下 `.lds` **唯一**=`linker/inst-tiny.lds`、`DEFAULT_LDS` 指向它（`--lds` 仅覆盖，册内不再自动挑选）、13 载体目录（00+01–12）同一份；**ASSERT 余量**：全 904 ELF 的 `.text` 实测最大 **0x1C54**（`br.eq/br.ne_rrii_rd_fault013`）≤ 0x4000。

**自设计 4 路注入**（`cp`+md5、未用 git checkout；还原 md5 全对账）：① `pseudo_set.rd_reg.S` `set.fo→set.ft` ⇒ **rc=1** 红（检查点10）→ 回绿 rc=0；② `set.rd` 拆固定 4 条 ⇒ **rc=0 不红**（判据靠行为，见上）→ 回绿；③ `ret_riii_ra.S` `ENTRY+0x1000→+0x1001` ⇒ **rc=1** 红（检查点18，qemu −2 跑飞）→ 回绿 rc=0；④ lds `.testdata` 段址 `0x5000→0x5001` ⇒ **rc=1** 红（检查点15）→ 回绿 rc=0。

**门控真数**：`check-inst-asm` 904/904（272 id、链例 271+故障 633）、`check-case-ledger` PASS（5438 条）、`check-inst-macro-scope` PASS（含 S6/S7/S8/S9、死宏 0）、`check-tests-index`/`check-dirs`/`check-no-residue` PASS。**L1 5 项红逐项归因**：① `check-patch-tree` = 共享 qemu 树 `target/dadao/helper.c` 脏（并发 `m14-qemu-003`；本任务 diff 全清单不含 `components/**`）；② `check-knowledge-refs` = `m14-linux-011:88`、`m15-testcases-004:88` 两处 `.work/**`（非本任务书，二者相对基线无改动）；③ `check-milestones-fresh` R1 = `m14-qemu-003` 有 worktree 但台账在「待开始」（主会话台账动作）；④ `check-run-artifacts` 43/43 全在 ``<运行期日志目录>` 的 qemu 子目录`；⑤ `check-temp-dirs` 5 个 = `m15-testcases-005-review`+`m14-linux-005/007/008/009`（**无一属本任务**，006 目录因在跑豁免）。

**约束核验**：基线钉死 `92fdb9d3`（HEAD 祖先断言过）；改动仅 `tests/inst/**`+`tests/case-ledger.tsv`+`run_asm_suite.py`+本任务书；`case-ledger.tsv` 2 行 = `stm` 两处字面量→`MSTORE` 的生成物连带、`MIGRATION.md` 1 处口径，**均为强制连带**（逐行 diff 已核）；注入全 `cp`+md5；未提交 git；跑批未撞 `guard=FAIL`（run.sh/门控日志 0 处 guard 失败），**安装根 md5 = `babd01d7ddea05cbe81abb7d3dbc380d`**（与并发协调通报一致，重试 0 次）。

**Finding（文档级，不阻断，交 architect 收尾改）**：① `MIGRATION.md:657/470` 仍写「初值一律 `__LI`+`rd2rf`」「rd 用 `__LI`」（判据只查 `.S`/`.inc`，已清零）；② 任务书**验收 1** 仍写「904/904 相同」，未同步用户裁定的三段口径（A′↔C/A↔A′），门控读的是 `run.sh`、不受影响。

### 第 1 轮 engineer 自审（2026-11-16）

审查范围：相对基线 `92fdb9d3` 的全量 diff（`tests/inst/**`、运行器、`case-ledger`、本任务书）逐行 + 三棵树行为对账 + 位型探针。**判决：全部 finding 已修，可标「待验收」。**

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 规范伪指令**按银行绑定**（`set.rd` 只收 rd、`set.rb` 只收 rb），而 `TEST_FAULT_CF1` 的寄存器参数跨银行（`12-misc` 传 `rb3`/`rb6`、`06` 传 `rd1`）⇒ 首轮 34 个故障镜像建镜像失败 `destination register is in the wrong bank` | ✅已修 | 该宏体内改用 `set.zw`+`or.w` 展开（与 `LOAD_ADDR` 同型；展开与旧装配逐字节相同），宏头写明原因 | 建镜像失败 0；904/904 PASS；`sc.w.nr_orrr_rd` 两故障例 rc 248/252 与基线同 |
| 2 | `stm.o_rrri_rb` 检查点 9/14 的期望是**布局地址字面量**（旧 MSTORE），布局一改即红（rc=9） | ✅已修 | 两处字面量改符号 `MSTORE`（语义 = 源组里 rb3 的值，与布局无关） | 该镜像 rc 9 → 0；`check-case-ledger` 重生成 2 行；904/904 |
| 3 | 6 个 `pseudo_set.*` 若用**被测伪指令**铺初值，「旧值被覆盖 / 高位保持」断言会退化恒真（实测：把 `set.fo` 注入成窄写后，用 `set.fo` 铺的旧值也同窄 ⇒ 仍绿） | ✅已修 | 初值改走另一条通路：`set.rb`+`rb2rd`、`set.rd`+`rd2rb`、`set.rd`+`rd2rf`；文件头写明「被测伪指令不得铺自己的初值」 | 注入①（`set.fo`→`set.ft`）在 `foadd_orrr_rf` 上 rc=3 红；`pseudo_set.*` 全 PASS |
| 4 | 任务书/README 的装载点数（1691/133/128、2691）与现场不符（旧估数） | ✅已修 | README 改为现场统计 1389（1173/95/121）；完成区写明口径 | `count_loaders.py` 现算，与逐文件对账一致 |
| 5 | `.S` 头注释写「12 册共用」，实际载体目录 13 个（含 `00-isa-design`） | ✅已修 | 206 个文件统一为「全部册（00 + 01–12）共用」 | `grep '12 册'` 只剩 `01`–`12` 的既有语义处 |
| 6 | `MIGRATION.md` 仍提已删除的 `__FP_LAYOUT` 分支 | ✅已修 | 1 行口径同步（历史段落不动，见遗留问题） | `grep -rn __FP_LAYOUT tests/inst` = 0 |
| 7 | 首轮「新装载 + 旧布局」组合跑出大面积超时（`.equ` 单点后 `TEST_PAD` 与旧 lds 的 `.faultpad` 不再对应，故障例跳飞） | ✅已修（判据重构） | 改为三棵树分解（A 基线 / A′ 基线装载+新布局 / C 现状），不再使用不存在的组合 | 证据脚本 50/50 |
| 8 | 计数用 `grep '^<tab>set.rd<tab>'` 会漏掉空格分隔的行（如 `set.rd    rd19`），口径不一 | ✅已修 | 统一 `count_loaders.py`（`^\s*set\.(rd|rb|fo|ft)\s`） | A 段计数与 `reconcile.py` 互相对上 |

**自审时的额外核对**：① 非 `.md` 文件的 diff 逐行分类，除「装载行 / 注释 / 删 `__FP_LAYOUT` 块 / 删三个宏定义 / `TEST_FAULT_CF1` 展开 / `stm` 两处期望 / `rd2rf`-`rd2rb`-`rb2rd` 转接行」外无其它改动；② 注入全部 `cp` 备份 + 还原后 md5 对账（4/4）；③ 未用 `git checkout/restore/stash`，未提交 git。

## 完成区

**测试结果**：证据脚本 `run.sh`（运行期证据目录，含 6 个辅助脚本）**50/50 PASS、rc=0**（1m45s，含三棵树各 904 镜像对账 + 4 路注入 + 门控）；`make check-inst-asm` **904/904**（272 id；链例 271 + 故障例 633）；`check-case-ledger` / `check-inst-macro-scope`（含 S9）/ `check-tests-index` / `check-dirs` / `check-no-residue` 全 PASS。L1 `make check -k`：除 **5 项外部红**外全绿——① `check-patch-tree`（共享构建树的 qemu 补丁工作树被并发任务 `m14-qemu-003` 改动）；② `check-milestones-fresh`（R1：`m14-qemu-003` 有 worktree 但台账仍在「待开始」，属主会话台账动作）；③ `check-knowledge-refs`（2 处具体 `.work/**` 引用分别在本任务之外的 `m14-linux-011` / `m15-testcases-004` 任务书，二者相对基线无改动）；④ `check-run-artifacts`（43 个非法名全在并发任务 `m14-qemu-006` 的日志目录）；⑤ `check-temp-dirs`（5 个陈旧临时目录属 `m14-linux-005..009`）。本任务目录/文件 0 命中。
**验收结果**（真实输出）：
1. **装载清零**：`grep '__LI\b|__LI_RB|__LI_RF' tests/inst --include=*.S --include=*.inc` = **0**；`.macro __LI*` = 0。口径：仅载体与宏层（`.S`/`.inc`）——`tests/inst/clmul/` 只有 `.c/.ll`、无 `.S`，不参与，故与 `m15-testcases-008` 退役无关；`.md` 保留「这三个宏已删除」的说明与历史台账（非装载点）。
2. **伪指令计数**（行首助记符，现场派生）：`set.rd=1257` / `set.rb=116` / `set.fo=82`（`set.ft=15` 全是被测窄写）；基线 `__LI=1173` / `__LI_RB=95` / `__LI_RF=121`。`reconcile.py` 逐文件对账 **274 文件逐项精确相等**；7 个例外全可解释——6 个 `pseudo_set.*`（54 处 `set.fo` 初值改 `set.rd`+`rd2rf`、2 处 rb 初值改 `set.rd`+`rd2rb`、1 处改 `set.rb`+`rb2rd`）+ `inst_test.inc`（−2：`__LI_RF` 宏体 1 行、`TEST_FAULT_CF1` 银行多态 1 行）。
3. **行为等价（拆两段，判据 = 行为）**：A（基线）/A′（基线装载 + 新 lds）/C（现状）各 904 镜像。**A′↔C 只差装载手段：903/904 rc+字节相同**，唯一差异 `st.o_rrii_rb` 检查点 15/16 记的是 `aip.si`/`rb2rb` 取出的 **IP**（指令流变短 ⇒ −0x120/−0x134，断言仍 rc=0）——这正是「判据只能是行为」的原因：`set.rd` 最少 1–4 条 vs `__LI` 定长 4 条，指令流必变。**A↔A′ 只差布局：899/904 相同**，7 个检查点全 +0x3000（TEST_DATA 上移），两侧 rc 均 0。检查点对账 272 id **0 处不一致**。
4. **风险①（符号/地址表达式、>2^47 常量）**：位型探针 45 表达式 × 2 种装载逐字节相同（md5 一致）**且与独立复算相同**：`(0x003F…+MEMRAS+0x80)`=0x003FFFFFFF017080、`(0x0001…+ENTRY+0x1000)`=0x0001FFFFFF011100、`(ENTRY+4)`=0x0000FFFFFF010104、`BOOTROM_BASE`=0x0000FFFFFFFF0000；`--perturb` 注入 ⇒ FAIL（可达）。
5. **风险②（`.org`）**：`.org 0x1000` → `__r4_land` @0xffffff011100；`.org 0x1800` → `__rb0_abs` @0xffffff011900；`.text` 0x11CC / 0x18F4 ≤ 0x4000；段上限 ASSERT 在 904 次链接中全过（另有注入④证明 lds 缺失即 setup 错）。
6. **风险③（宏体）**：共享层/册层 `.inc` 内 `__LI*` = 0；宏层装载行 `set.rd=17`。
7. **lds 统一**：`__FP_LAYOUT` = 0；册内 `.lds` = 0；`tests/inst/linker/inst-tiny.lds` 唯一；13 个载体目录（00 + 01–12）同一份；`DEFAULT_LDS` 指向它，`--lds` 仅覆盖；册目录不再自动挑选布局。
8. **4 路注入**（cp+md5 还原，4/4 md5 对账）：① `set.fo`→`set.ft` ⇒ `foadd_orrr_rf` **rc=3 红**；② `set.rb`→`set.rd` ⇒ 汇编器「wrong bank」红；③ 48 位常量 +1 ⇒ **rc=18 红**；④ 移走 lds ⇒ **rc=2**；每条还原后回绿。
**修改文件**：`tests/inst/**` 256 个 `.S`/`.inc`（装载行 + 注释；`README.md` 新增「装载一律用规范伪指令」节与布局表；`MIGRATION.md` 1 行口径；`stm.o_rrri_rb.S` 2 处布局字面量→`MSTORE`）；删两册内 `.lds`、新增 `tests/inst/linker/inst-tiny.lds`；`tools/testcases/inst/run_asm_suite.py`（仅 lds 选择：单一默认 + `--lds` 覆盖）；`tests/case-ledger.tsv`（生成物重生成 2 行）；本任务书。
**新发现/坑**：① **规范伪指令按银行绑定、无「任意银行」形态** ⇒ 银行多态宏用不上（`TEST_FAULT_CF1` 落 `set.zw`+`or.w`，与 `LOAD_ADDR` 同型）；② **被测伪指令不得铺自己的初值**，否则「旧值被覆盖/高位保持」断言退化恒真（6 个 `pseudo_set.*` 改道，注入①证明禁则必要）；③ **`semi.out` 不是布局无关的**——5 个镜像记录 IP/地址，布局一变字节即变 ⇒ 等价判据必须拆「装载 / 布局」两段；④ `stm` 两处期望原是布局地址字面量，已改符号；⑤ 计数须用 `^\s*set\.(rd|rb|fo)\s`（空格分隔行会被漏），任务书 1691/133/128 与现场 1173/95/121 不符（旧估数）。
**遗留问题**：① `LOAD_ADDR`（`tests/shared/asm/machine.inc`）仍是 4 条硬件指令的 rb 装载宏，不属本任务范围（`tests/inst/**` + 运行器），建议另立任务评估改 `set.rb`；② `tests/inst/MIGRATION.md` 的历史段落仍写旧布局/旧路径（历史记录，未改）。
