# m15-testcases-006: 载体装载改用规范伪指令（`__LI`/`__LI_RB`/`__LI_RF` → `set.rd`/`set.rb`/`set.fo`）

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-005`（在跑：前缀改名 + 剔 `__LI2`）**必须先合入**（同改 `tests/inst/**`）
**可并行分片**：可（按册；同一册单写者），但建议按册分批、每批独立对账
**预估**：6–8 h（254 文件、1691+133+128 处调用）
**档位**：大改（判据口径切换 + 全仓结构重构；复核 ≥4 路注入 + 行为级全量对账）
**状态**：待开始

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

1. **行为等价（核心）**：全仓 **272 id / 904 镜像**，改前/改后逐镜像比 **`semi.out` 字节 + 退出码**，**904/904 相同**；
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

（待填）
