# m15-testcases-010: 01 册 ld/st 修正（opc 注释 + boundary 极值 + rb0 基址用例）

**模块**：testcases
**项目里程碑**：M15
**依赖**：无（`tests/inst/01-load-store/` 现状；`m15-testcases-009` 已合入）
**可并行分片**：否（同册共享 `.inc` 与布局）
**预估**：5–7 h
**档位**：中改（注释 1 行 + 4 个文件加用例 + 01 册加 rb0 用例；复核 diff + 1 路注入 + 受影响门控）
**状态**：待验收

## 背景（用户 2026-11-17 发现）

用户在 `tests/inst/01-load-store/ld.o_rrii_rd.S` 发现三处问题，均已核实：

1. **opc 注释错误**：`ld.o_rrii_rd.S:3` 写 `opc：0x16`，`contracts/opcodes.yaml` 的 `ld.o_rrii_rd` 是 `0x20`。全仓 272 个 `.S` 机械比对只有这一处不一致（`ld.t_rrii_rf` 的 0x16 是正确的，`ld.t` 真实 opc 就是 0x16）。
2. **boundary 极值不全**：`ld.o_rrii_{rd,rb,ra,rf}.S` 的 boundary 段已有 `0x7FFFFFFFFFFFFFFF`（正向极大）、`0x0000000000000080`、`0x0`、`0x5555…`、`-0x800`、`-0x7F8`，但**缺** `0xFFFF_FFFF_FFFF_FFFF`（无符号全 1）与 `0x8000_0000_0000_0000`（有符号极小；后者目前只在 `semantic` 段出现）。
3. **`rb0` 作基址未覆盖**：`spec/SimRISC-01` 只禁**目的** `rbHA = rb0`（ILLI）；**基址 `rbHB = rb0` 合法**（`spec/SimRISC-00`：`rb0` 读出 = 当前指令地址 IP，只读）。当前 01 册的 `rb0` 只出现在控制流 `[rb0, …]`，没有数据访问用例。

> 用户 2026-11-17 指示：**本任务只修这三处，不建门控**（不做 opc↔opcodes.yaml 的机械校验器）。

## 目标

1. **opc 注释**：`ld.o_rrii_rd.S:3` 的 `opc：0x16` → `opc：0x20`（只改注释，编码/mask 不变）。
2. **boundary 极值补全**（**01 册全部 38 个 `ld/st/ldm/stm` 文件**：`ld.o`×4、`ld.sb/st/sw/ub/ut/uw`+`ld.t_rrii_rf`=7、`ldm.o`×4、`ldm.sb/st/sw/t/ub/ut/uw`=7、`st.b`×1、`st.o`×4、`st.t`×2、`st.w`×1、`stm.b`×1、`stm.o`×4、`stm.t`×2、`stm.w`×1；按各自宽度）：按各自宽度补齐「正向极大 / 负向极小 / 全 1」三条（8 位 `0x7F`/`0x80`/`0xFF`；16 位 `0x7FFF`/`0x8000`/`0xFFFF`；32 位 `0x7FFFFFFF`/`0x80000000`/`0xFFFFFFFF`；64 位 `0x7FFF…`/`0x8000…`/全 1）。**`TEST_DATA` 已含全部所需值，不得改 `inst_test.inc`**；各条从现有 beat 偏移引用（8 位：`+0x30`(`0x80`)/`+0x59`(`0x7F`)/`+0x58`(`0xFF`)；16 位：`+0x50`/`+0x58`/`+0x48`；32 位：`+0x20`(高字 `0x80000000`)/`+0x2C`(高字 `0x7FFFFFFF`)/`+0x40`；64 位：`+0x20`/`+0x28`/`+0x88`）。每个文件至少补
   - `0xFFFF_FFFF_FFFF_FFFF`（无符号全 1）
   - `0x8000_0000_0000_0000`（有符号极小）
   期望值用**已有测试数据/现场派生**，禁在 `.S` 里写死「看起来对」的常量（现有 `TEST_DATA` 24 个 beat 的字面量见 `tests/inst/macros/inst_test.inc`；若目标 beat 已含上述值，直接引用其地址即可）。
3. **`rb0` 基址用例**（01 册**所有后缀形式**，每个 `ld/st/ldm/stm` 的 `.b/.w/.t/.o`）：**每条指令形式须覆盖 `imm` 的 `负 / 零 / 正` 三档**（用户 2026-11-17 要求）；
   - `ld.o rd, [rb0, imm]`、`st.o rd, [rb0, imm]`、`ldm.o {…}, [rb0, rdHC]`、`stm.o {…}, [rb0, rdHC]`；
   - EA = **当前指令地址 + imm**（`iprefix` 语义见 `spec/SimRISC-00`；`rb0` 读当前 IP、**不是**下一条）；
   - **期望值必须现场派生**：用链接期符号/`aip` 或已知布局计算目标地址上的内容（例如读回该地址的指令字），**不得写死**；写入用例同理（写到代码区需谨慎，优先选可写的只读无关区/预先布置的数据区）。
   - 若某条在现有布局下不可构造（例如 `st` 写入代码区会破坏执行），在完成区写明原因并给出替代（如 `ldm/stm` 只测 `[rb0]` 的 `ldm` 方向），**不得静默跳过**。
4. 不改任何非 01 册文件；不新增 `.S` 文件（用例加在现有文件内，保持镜像数不变）。

## 验收（逐条贴真实 rc）

1. `ld.o_rrii_rd.S:3` 的 opc = `0x20`；与 `contracts/opcodes.yaml` 一致。
2. 四个文件的 boundary 段各含 `0xFFFF…`/`0x8000…` 两条，期望值来源可追溯（测试数据 beat 地址或链接期计算），**不写死**。
3. 01 册存在 `[rb0, …]` 的数据访问用例（至少 `ld.o`/`st.o`/`ldm.o`/`stm.o` 各一），期望值现场派生；`ip=当前指令` 的语义被断言到（不是下一条）。
4. **镜像与门控**：`check-inst-asm` **272/272**（镜像数不变）、`check-case-ledger`、`check-tests-index`、`check-inst-macro-scope`（含 S9）、`check-dirs`、`check-no-residue` 全 rc=0。
5. **1 路注入**（`cp`+md5 还原）：把 opc 注释改回 `0x16` ⇒ 验收 1 的核对断言必红（用一次性脚本核对，不入仓）；还原后回绿。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 只动：`tests/inst/01-load-store/ld.o_rrii_{rd,rb,ra,rf}.S`（+ 若 rb0 用例需加在 `ld.o_rrii_rb.S`/`st.o_rrii_rb.S`/`ldm.o_rrri_rb.S`/`stm.o_rrri_rb.S` 内则一并）、本任务书。**不动** `spec/`、`contracts/`、`tools/`、`Makefile`、其它册。
3. **不改任何版本号**（版本号升级须用户认可，见 `AGENTS.md`）。
4. 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore/stash/show`、禁 `reset --hard`）。

## 待裁定

（无；用户 2026-11-17 已明确：只修三处、不建门控）

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

- 审查范围：38 个 `.S` 的追补段（点号连续、`.org` 单调、保留寄存器不冲突）、`01-load-store.inc` 4 个新宏、`ld.o_rrii_rd.S` 两行注释、`tests/case-ledger.tsv` 生成物。
- 逐项核对：① 点号 = 用例序号（`run_asm_suite` 的 `pts_ok` 全 38 文件过）；② `.faulttab` 槽位 ≤ 0x480（最大点号 32）、结果缓冲 ≤ 1016 B（最大 26 点）；③ 用例只用非保留寄存器（rb3/rb30/rd20–23/rb21/rb16/rd4/rb29/rb27/rb24 未被占用；rd19/rb12/rb25/rb26/rb28/rd2 为宏内临时）；④ 未改版本号、未新增 `.S`、未动 `spec/`/`contracts/`/`tools/`/`Makefile`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 零档宏内「读回」与「被测」为同一条指令 ⇒ 若实现取「下一条」，两侧 EA 同错也自洽（假绿） | ✅已修 | 宏内插入 `add.si rd2, 0` 填充，使 EA+4 处字节必与被测指令不同；独立核对加「8/16/32/64 位前缀必须不同」判据 | C 项 228/228 过；4 个 8 位文件早先被该判据判红 ⇒ 修后回绿 |
| F2 `ldm.o/stm.o` 零档最初把被测指令放在 `≡4 (mod 8)` 地址 ⇒ MALIGN 死循环 | ✅已修 | ldm 零档钉子改 `0x2080`（被测 @0x2088）；stm/st.o 零档钉子 `0x20C0`（被测 @0x20D0） | 修复前 rc=-2（超时）；修复后 38/38 PASS |
| F3 st/stm 正档最初把目标写在 `.org` 零区之外（写进其后校验代码） | ✅已修 | st 正档加 `jump` 跳过 + `.org 0x2188/0x2190` 显式零槽；stm 正档目标改 `MSTORE+0x1C0+(8−w)` | st.b/stm.b/stm.w 修复前 rc=21/16/16，修复后 PASS |
| F4 文件头用例统计被脚本改出重复/缺项（`rb0 1 / rb0 3`、ldm 册缺 boundary 计数） | ✅已修 | 以原始头部为基重写统计行（boundary +3、rb0 合并 +3、链例/故障例按现场点数） | 38 个头部逐条打印复核一致 |
| F5 `llvm-objdump -d` 在 `.text` 内嵌数据上触发 LLVM 断言崩溃（证据脚本受影响） | ✅已修 | 证据脚本改用 `llvm-nm` 取 `_start`/标签 + `llvm-objcopy --only-section=.text` 取字节，自行重算 opcode 与 EA | C 项稳定 228/228；无崩溃 |

### 第 1 轮 reviewer 验收（2026-11-17，中改 ≤60 min）

**重跑记录（全部本人执行，退出码如实）**
- 自证：`git rev-parse --show-toplevel` = 本 worktree；分支 `m15-testcases-010`、HEAD `30f0a706`；`git status --porcelain -uall` 基线 0 行。
- opc：自写脚本核 38 文件头部两处 opc + mask ↔ `contracts/opcodes.yaml` ⇒ **38/0，mismatch=0**；全仓 `0x16` 仅剩 `ld.t_rrii_rf`；`git diff` 中 opc 注释变化**只有** `ld.o_rrii_rd` 第 1、3 行；`contracts/spec/tools/Makefile` diff 为空。
- boundary/rb0：自写脚本（独立解析 24 拍 + MSTORE 模式现场重算）⇒ **190 项 / 0 失败**（boundary 114 + rb0 三档覆盖 76）；大端推导独立复核 `+0x020/0x028/0x088` 首字节=0x80/0x7F/0xFF（负极小/正极大/全1），与各行期望逐条一致。
- 门控（本人重跑）：`check-case-ledger` rc=0（现场 5666 条）、`check-tests-index` rc=0（**472** 条）、`check-inst-macro-scope` rc=0（含 S9，2 条 WARN 非阻断）、`check-dirs` rc=0、`check-no-residue` rc=0、`check-inst-asm` rc=0（**272/272 镜像、633 例**）。
- 证据脚本：审毕（A/B/C 断言均有可达 FAIL 路径）；重跑 `run.sh` ⇒ `RUNSH_EXIT=0`（A 38/0、B 114/0、C 228/0；其 3 路注入各自 rc=1、md5 还原回绿）。
- **独立注入 3 路**（`cp`+md5，禁 checkout/reset）：① opc 0x20→0x16（任务书验收5 列举）⇒ `chk_opc` rc=1；② boundary 全1 期望 0xFF→0xFE（任务书未列）⇒ rc=1；③ `stm.o` 负档 `set.rd rd19, -0x020` 去负号（任务书未列）⇒ rc=1「负=0」。三次还原 md5 与 BASE 逐一相等，回绿 rc=0，`git status` 空。

**约束核验**：越界 0（41 文件 = 任务书 + `case-ledger.tsv` + `01-load-store.inc` + 38 `.S`；`spec/contracts/tools/Makefile`/其它册零改动）；未新增 `.S`（镜像 272 不变）；未改版本号；完成区 25 行 ≤30、状态=待验收；未提交 git。

**finding（文档级，不阻断，architect 收尾顺手改）**
- F-r1：`ldm/stm` 正档注释地址差 0x10——`LOAD_ADDR` 展开 4 指令 ⇒ `aip.si` 实 @0x2190、被测实 @0x2198（本人 `llvm-nm`+`objcopy` 取字节验证：`__rb0p`=+0x2180、0x2198 首字节 0x38 = `ldm.o` opc），注释写「rb25=ENTRY+0x2180、被测 @0x2188」；头注释「正档 EA=ENTRY+0x2188」对 ldm/stm 亦不成立（实为 TEST_DATA+0x088 / MSTORE+0x1C0+w）。EA 数学因 aip→被测恒为 8 而自洽，实跑绿、C 项 pospin=0x2198 检查过 ⇒ 仅注释错。
- F-r2：`st.*` rb0 正档写 `ENTRY+0x2188`（.text 内 `.org` 死槽、jump 跳过、`__CHECK_MEM` 读回断言）而非 MSTORE——rrii imm12 量程（±2 KiB）自 .text 不可达 MSTORE（差 0x4940），结构上唯一可行；任务书允许「预先布置的数据区」，实跑绿。`stm.*` 正档已写 MSTORE ✓。

**判决：Accepted**（验收 1–6 在本人重跑下全过、硬约束无违反；F-r1/F-r2 按「文档级小错」记档，不返工）。

## 完成区

**测试结果**：独立核对 380/380（A opc 38 项 / B boundary 期望**现场重算** 114 项 / C rb0 EA 布局 228 项）全过；`check-inst-asm` **272/272 镜像**、633 例全过；01 册 38 镜像 197 例全过；L1 五门控（case-ledger / tests-index / inst-macro-scope（含 S9）/ dirs / no-residue）全 rc=0。注入 **3 路**（要求 1 路）：opc 0x20→0x16、boundary 全 1 期望 −1、rb0 负档 imm −0x040→−0x044 ⇒ 各自必红；`cp`+md5 还原后回绿（md5 对账一致）。

**修改文件**：
- 01 册全部 **38** 个 `ld/st/ldm/stm` `.S`（38 镜像不变，未新增 `.S`）：每文件 +3 boundary +3 rb0 基址，故障例点号 +6，文件头用例统计更新。
- `tests/inst/01-load-store/01-load-store.inc`：+4 个**册**宏承载 rb0 零档（一行宏调用 = 一个检查点）——`__CHECK_RD_IP` / `__CHECK_RD_LDM_IP`（EA = 自身地址，`aip.si` + 显式基址读回比对；中间插一条 `add.si rd2, 0` 使「下一条」处字节不同 ⇒ 真能判别 IP 口径）/ `__CHECK_RD_ST_IP` / `__CHECK_RD_STM_IP`（8 B 宽：预读 8 B 拍、只改高 32 位后幂等写回，保留其后的指令字）。
- `ld.o_rrii_rd.S`：opc 注释 `0x16`→`0x20`（第 1、3 行；`ld.t_rrii_rf` 的 0x16 未动）。
- `tests/case-ledger.tsv`：`check-case-ledger --write` 重生成（点号计数变化；生成物）。**越界披露**：清单外文件（`01-load-store.inc` 与台账）为 38 文件范围 + 门控所必需。

**验收结果**：`run_asm_suite: 272/272 镜像通过（272 个 id；链例 + 故障链 633 例）/ check-inst-asm: PASS`；`check-case-ledger: PASS`、`check-tests-index: PASS（472 条）`、`check-inst-macro-scope: PASS`、`check-dirs: PASS`、`check-no-residue: PASS`；独立核对 `[A] 38/0 [B] 114/0 [C] 228/0`（失败数 0）；注入输出逐条见运行期证据目录。

**逐类统计**（每文件 3+3 条，明细见各 `.S` 的 `m15-testcases-010 追补` 段）：
- `ld.o`×4、`ld.sb/ub/sw/uw/st/ut`、`ld.t_rrii_rf`（11）：boundary 取 `TEST_DATA + 0x028/0x020/0x088`（正向极大/负向极小/全 1，按宽度与符号/零扩展写期望）；rb0 三档 = 负 `-0x040`→死槽 `ENTRY+0x2000`、零 `[rb0,0]`→自身指令地址、正 `+0x008`→死槽 `ENTRY+0x2188`。
- `st.o`×4、`st.b/st.w`、`st.t`×2（8）：boundary 写 `MSTORE + 0x1C0/0x1C8/0x1D0` 的**低 w 字节**（期望 = 保持区模式按宽度替换）；rb0 三档同 ld（零档写回自身地址，`w<8` 只覆写本指令首 w 字节）。
- `ldm.o`×4、`ldm.sb/ub/sw/uw/st/ut`、`ldm.t_rrri_rf`（11）：boundary 用 `TEST_LDM`（count=1，回写 `MDUMP + 0x1C0/0x1C8/0x1D0`）；rb0 三档 = 偏移寄存器 `-0x020`、`rd0`、`TEST_DATA+0x088−(IP)`。
- `stm.o`×4、`stm.b/stm.w`、`stm.t`×2（8）：boundary 用 `TEST_STM`（源 = `TEST_DATA + 0x028/0x020/0x088`）；rb0 三档同 ldm（正档目标 `MSTORE + 0x1C0 + (8−w)`）。

**新发现/坑**：
- 用户给的窄宽度 beat 偏移（`+0x59`/`+0x58`、`+0x2C` 高字 等）是**小端读法**；`TEST_DATA` 按**大端**存放 ⇒ 8/16/32 位极值实际取 `+0x028`/`+0x020`/`+0x088` 三拍的**首字节起**（B 项由 `inst_test.inc` 现场重算，禁改数据块已遵守）。
- `ldm.o/stm.o`（8 B 宽）作零档时被测指令必须**自身 8 B 对齐**，否则 EA 未对齐 ⇒ MALIGN 死循环（定位：QEMU `-d exec` 见固件 trap 环）。
- `llvm-objdump -d` 在 `.text` 内嵌数据（`0x8000…`）上会触发 LLVM 寄存器断言崩溃 ⇒ 证据脚本改用 `llvm-nm` + `llvm-objcopy --only-section=.text` 取字节**自行重算** EA/opcode。
- 建议沉淀：「rb0 作基址三档」的布局与断言手法（`.org` 双端钉住 + 同指令显式基址读回 + 「下一条处字节必须不同」的判别力检查）可写成 `01 册` 用例模板。

**遗留问题**：无（`/tmp` 被并行任务占满 ⇒ 工作树迁至仓库内 `.work/wt/<任务ID>`（gitignored），证据目录未入仓；不影响交付内容）。
