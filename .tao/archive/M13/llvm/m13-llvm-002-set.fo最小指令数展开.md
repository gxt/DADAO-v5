# m13-llvm-002: `set.fo rf, imm64` 最小指令数展开（rd0 清零 + 只改非零 wyde）

**模块**：llvm
**项目里程碑**：M13
**依赖**：`m13-spec-011`（已合；`set.*` 伪指令正文在 `SimRISC-00 §5`）
**可并行分片**：否
**预估**：1.5–2 h（构建 ~2–5 min）
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：已验证

## 用户裁定（2026-11-15，原话）

> 「set.fo rf, imm64完全可以进行优化，先用rd0初始化为64位全0，然后修改非零的wyde，可能节省一至两条指令，而对于正0，则只需一条」

## 现状（doc 与实现不一致）

- **spec 已是优化口径**：`Toolchain-01 §6.1` 明确「`set.fo rf, imm64` 展开为 `rd2rf rf, rd0` + 仅对**非零** wyde 的 `set.w`；`set.fo rf, 0` ⇒ **1 条**」；
- **实现没跟上**：`DADAOAsmParser::expandPseudoInstruction` 现在是「`imm==0` ⇒ `rd2rf`；否则 **4 条 `set.w`**」（源码注释也这么写）；
- **契约陈旧**：`.tao/contracts/contract-asm.md:188` 写「`set.fo rf, imm64`（4 条 `set.w`）」，与 `Toolchain-01` 冲突。

## 任务

1. **实现最小指令数展开**（`k` = 非零 16 位 wyde 个数，0–4）：
   - `cost_rd0 = 1 + k`（`rd2rf rf, rd0` + k 条 `set.w`）；`cost_w4 = 4`（4 条 `set.w`）；
   - **取较小者**：`k ≤ 3` 用 `rd0` 方案、`k == 4` 用 4 条 `set.w`（避免出现 5 条的反向优化）；
   - `imm == 0` ⇒ 仅 `rd2rf rf, rd0`（1 条）；
   - **`set.ft rf, imm32` 不变**（仍 2 条 `set.w`）：它是**窄写**（高 32 必须保持），**不得**用 `rd2rf` 清零；
2. **同步契约**：`.tao/contracts/contract-asm.md:188` 的「4 条 `set.w`」改为「`rd2rf rd0` + 非零 wyde 的 `set.w`；`k=4` 时退回 4 条 `set.w`（最小指令数）」，并指 `Toolchain-01 §6.1`；
3. **lit 期望更新**：`tests/unit/llvm/e2e/...` 与 `tests/unit/llvm/lit/MC/DADAO/{m4-pseudo-set.s,set-ft-fo.s}` 里 `set.fo` 的期望按新展开改（含 `imm=0`、k=1、k=2、k=3、k=4 五种形态各一例）；
4. 补丁 `make_patch.py llvm` 导出 + `check-patch-tree` **llvm 段 0 问题** + `--source-state` llvm OK + `check-component-changelog`。

## 验收（真实 rc）

1. `llvm-mc` 实测五种形态的**指令条数**与操作数序列：`imm=0` ⇒ 1 条；k=1 ⇒ 2 条；k=2 ⇒ 3 条；k=3 ⇒ 4 条；k=4 ⇒ 4 条（**不是 5**）；`set.ft rf, imm32` ⇒ **仍 2 条**；
2. 语义不变：`set.fo` 写入值与 `imm64` 逐位相等（抽 3 例 dump 目的 rf）；
3. lit：`check-lit`（现场计数）、`check_lit_gen`、`validate_mc_vectors` rc=0；
4. **≥2 路注入**（`cp`+md5 还原）：① 把 `k==4` 误判成走 `rd0` 方案 ⇒ 应出现 5 条（断言红）；② 让 `set.ft` 也走 `rd0` 清零 ⇒ 高 32 被破坏（应红）；
5. 门控：`check-lit`、`check-patch-tree`（llvm 段）、`--source-state` llvm、`check-component-changelog`、`check-asm-list-drift`、`check-asm-prose`、`check-isa-coverage`；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `components/llvm-project/**`、`tests/unit/llvm/**`、`.tao/contracts/contract-asm.md`（仅该条）、本任务书；
- **不改** `spec/`（`Toolchain-01` 已是优化口径）、`tests/inst/**`、其它组件；
- 构建 `JOBS=32`（申报耗时）；禁 `install-host`/`check-modules`（用构建树 `llvm-mc`/`llvm-lit`）；不 sync/reset 节点；不提交 git；注入还原 `cp`+md5。

## 待裁定

1. **越界文件 `tools/testcases/validate_mc_vectors.py`（已改，待确认纳入范围）**：该脚本是 `m4-*.s` 的 `@exp` **独立 oracle**，其 `set.fo` 派生仍是「固定 4 条 `set.w`，且 `imm==0` 直接 `AssignError`」，与 spec `Toolchain-01 §6.1`（已是优化口径）冲突。不改它，则「`@exp` 跟着实现走」与验收项 3（`validate_mc_vectors` rc=0）不可能同时成立。选项：A) 纳入本任务（**已按此执行**：派生改为 spec 口径 `rd2rf {dst}, {rd0}` + 非零 wyde）；B) 回退该文件、把验收项 3 记 BLOCKED。建议 A（投影实现跟 spec，与契约同性质）。
2. **DDLN 讲义未同步（不改，仅登记）**：`docs/DDLN/A-指令系统/DD-A005-…:87,103` 与 `DD-A002-…:156` 仍写「`set.ft`/`set.fo` 展开为 2/4 条 `set.w`（含零片），仅全零用 `rd2rf`」。讲义非实现判据且在任务硬约束的改动面之外，建议另立收尾或由主会话裁定同步方式。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-15）

逐行复查 `expandPseudoInstruction` 的 `set.fo` 分支（k 计数 → 两方案取舍 → 高位优先发射）、`set.ft` 分支未动、寄存器形式未动、符号形式仍报错；核补丁 `@@ -0,0 +1,2737 @@` 与源树行数一致（+19 行）、`index` blob 随导出更新；核 lit 两文件的 `CHECK`/`OBJ-NEXT` 串联顺序与文件语句顺序一致（跨例串联使「多出一条」必红）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `ASM-EMPTY:` 断言不可用（`-filetype=asm` 的空行只在语句行**无行尾注释**时出现，注释行会抑制空行） | ✅已修 | 删全部 `ASM-EMPTY:`，改用 objdump 侧 `CHECK-NEXT` **跨例串联**钉条数 | `m4-pseudo-set.s` 由红转绿；注入①（k=4→5 条）下该串必红，见证据脚本 |
| 字节级期望首版按 `ha=1` 手算（`4f 07 3f f0`）与实际编码不符 | ✅已修 | 改以 `opcodes.yaml` 的 `set.w` 字段（`ha[23:18]` = **目的 rf 号**、`wpN[17:16]`、`immu16[15:0]`）复算并取实测字节（`4f 0b 3f f0` 等） | `check_lit_bytes` 258 patterns OK；`set-ft-fo.s` 绿；注入②的 `rd2rf` 序列可读 |
| `validate_mc_vectors` 的 `set.fo` 派生与 spec 冲突（**越界文件**，见待裁定 1） | ✅已修（按选项 A 临时执行，范围待 architect 确认） | 派生改为 spec 口径：`rd2rf {dst}, {rd0}` + 非零 wyde（k=4 仍 4 条） | 83 向量 / 0 错；`@exp` 与实现逐字一致 |
| 证据脚本里注入①原打算「复用主断言再翻转计数」 | ✅已修 | 改为直接断言「注入后实测 5 条且序列 ≠ 期望」，语义清晰、无计数翻转 | `--inject` 28/28，注入① 打印 `count=5 seq=[rd2rf…]` |

### 第 1 轮 reviewer 验收（2026-11-15）—— **Needs Revision**

**重跑（我自己的终端输出/退出码）**：`run.sh` **19/19 `RESULT: PASS` rc=0**；`run.sh --inject` **28/28 rc=0**（内含 lit `MC+CodeGen+e2e` 176/176、`MC/DADAO-gen` 11/11、`check_lit_gen` 62/62、`validate_mc_vectors` 83 向量/0 错、`check_lit_bytes` 258 patterns、`check-asm-list-drift`/`-asm-prose`/`-isa-coverage`/`-component-changelog` rc=0、`check-patch-tree` llvm 段 99 补丁 0 断言、`--source-state` llvm OK）；补跑 `check-knowledge-refs`/`check-no-residue`/`check-contracts-pending` 均 rc=0。
**最小性证明**：llvm-mc 现场枚举 k=0/1/2/3/4 ⇒ **1/2/3/4/4（k=4 无 `rd2rf`）**、高半 `0x3FF0…` k=1 ⇒2、`0xFFFF000000000000` k=1 ⇒2、`set.ft imm32` ⇒2 ⇒ `min(1+k,4)` 由代码分支 `if (Nz <= 3)`（rd2rf+k 条；否则 4 条 `set.w`）成立，非测试硬编码。
**语义锚点（我自写双向 `cmp.uo`+`br.n` 探针 + qemu）**：k=4（`0xDEADBEEFCAFEBABE`）/ k=1 高半（`0x8000…`）/ k=0 / `set.ft` 窄写（期望 `0xAABB000011223344`）全 **exit=0**；错值对照 **exit=21** ⇒ 探针可达 FAIL；`set.ft` 后高 32 保持（`SimRISC-00 §5.3` 写宽对照）。
**注入（我自设计，`cp`+md5 还原，3 路）**：① `Nz<=3→<=4` ⇒ k=4 变 **5 条**，`llvm-lit MC/DADAO` **rc=1**（`m4-pseudo-set.s`+`set-ft-fo.s` FAIL、83 PASS）⇒ **`CHECK-NEXT` 跨例串联真能红**；还原 md5 `56e297fd…` 重建后 85/85 rc=0。② `rd2rf` 挪到 `set.w` 之后 ⇒ 探针 **exit=22**（k=1 高半被清零）+ lit rc=1；还原回绿 exit=0。③ 临时树副本改坏一条 `@exp` ⇒ `validate_mc_vectors` **rc=1** 并打印「独立派生」（基线 83/0）；该脚本仅 import `glob/os/re/sys/yaml`、不调 `llvm-mc`、不 import 实现 ⇒ **独立 oracle 且未放松**。
**越界核对**：`git show b1118aea --name-only` = 7 文件（`components/llvm-project/**`×2、`tests/unit/llvm/**`×2、`tools/testcases/validate_mc_vectors.py`（主会话已授权）、`.tao/contracts/contract-asm.md`（**已改**，仅 §6「保留 8 条」一行，指 `Toolchain-01 §6.1`）、任务书）；`spec/`、`tests/inst/` 未动；`git status -uall` 前后均空、目标文件 md5 注入前后逐行相同；完成区 16 行、无运行期路径。
**阻断（Needs Revision）**：证据脚本 `run.sh` 的 **case5 断言不合格**——① 期望常量写错 `0x1234FFFFFFFF`，按 `SimRISC-00 §5.3`（`set.ft imm32` 只写低 32、高 32 保持）应为 **`0x12340000FFFFFFFF`**（我实测：正确常量 exit=0、完成区常量 **exit=25**）；② 比较**单向**（`cmp.uo` 结果 -1/0/1 + `br.n` 负才分支，只判 `actual<expected`）⇒ 把期望故意改错仍 **exit=0**（我双向探针同输入 exit=25）⇒「语义不变 case5」是假绿、「探针可达 FAIL」只覆盖 `<` 方向。
**修法（engineer，不改实现）**：case5 期望改 `0x12340000FFFFFFFF`；比较改**双向**（交换操作数再比一次，或 `br.ne {rd1,rd2}?`），并补一条 `actual>expected` 反例自证可达 FAIL；重跑 `run.sh` 回绿、完成区该行同步更正。**实现/lit/契约/oracle 无需改**（实现正确性已由我独立探针证明）。
**Finding（不阻断）**：`set-ft-fo.s` 头部注释仍是旧口径「otherwise 4x set.w cover the full octa」，与本文件新用例矛盾，随返工改一句。
**未决（转 architect）**：`SimRISC-00 §5.3` 写「`set.ft rf1, 0` ⇒ `rd2rf`」而 `Toolchain-01 §6.1` 表为「2 条 `set.w`」、实现为 2 条（任务书明令 `set.ft` 不变）——spec 内部口径差，非本任务引入。

### 第 2 轮 engineer 返工（2026-11-15，按 Needs Revision）

只改证据脚本与注释，**实现/lit 断言/契约/oracle 未动**（reviewer 已证其正确）。

| reviewer finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| case5 期望常量写错（`0x1234FFFFFFFF` = `0x0000_1234_FFFF_FFFF`） | ✅已修 | 改 **`0x12340000FFFFFFFF`**（高半来自 `set.fo rf5, 0x1234000000000000` 的 `0x1234_0000`，低半是 `set.ft` 写的 `0xFFFF_FFFF`，按 `SimRISC-00 §5.3` 窄写） | 正确常量 ⇒ `guest_exit=0`；旧错常量 ⇒ `guest_exit=5` |
| 比较单向（`cmp.uo`+`br.n` 只判 `actual<expected`）⇒ 假绿 | ✅已修 | 5 例全改 **`br.ne {rdA, rdB}?, [rb0, failN]`**（两寄存器不等即失败，天然双向；case4 用 `{rd1, rd0}?`） | 四路方向反例全红：case1 `+1`/`-1` ⇒ 1/1；case5 改小/改大 ⇒ 5/5 |
| `set-ft-fo.s` 头部注释仍旧口径「otherwise 4x set.w cover the full octa」 | ✅已修 | 改为「`rd2rf rf, rd0` 清零 + 每个**非零** wyde 一条 `set.w`（k≤3 ⇒ 1+k；k==4 ⇒ 退回 4 条）」 | `llvm-lit set-ft-fo.s` PASS；`make check-lit` **176/176** rc=0 |
| 完成区「语义不变 case5」结论为假绿 | ✅已修 | 按新证据重写（见完成区第 7 条：正确常量 + 双向 + 四路反例） | `run.sh` 22/22 rc=0、`--inject` 31/31 rc=0 |

**返工后门控**：`run.sh` **22/22 `RESULT: PASS` rc=0**；`run.sh --inject` **31/31 rc=0**（含 lit `MC+CodeGen+e2e` 176/176、`MC/DADAO-gen` 11/11、`check_lit_gen` 62/62、`validate_mc_vectors` 83 向量/0 错、`check-patch-tree` llvm 段 99 补丁 0 断言、`--source-state` llvm OK）；`make check-lit` **rc=0 / 176/176**（构建树工具，未 `install-host`）。注入①/② 还原 md5 `56e297fd…` 与注入前一致。

### 第 2 轮 reviewer 验收（2026-11-15）—— **Accepted**

- **重跑（我的终端）**：`run.sh` **22/22 `RESULT: PASS` rc=0**、`run.sh --inject` **31/31 rc=0**（注入① k=4→5 条、注入② `set.ft`→`rd2rf` ⇒ guest_exit=5；两次还原 md5 `56e297fd…` 与注入前一致）；`make check-lit`（构建树工具、未 `install-host`）**rc=0、Passed 176 (100.00%)、Failed 0**。
- **双向性（我自注入，`cp`+md5 还原）**：`EXP5` 改**小**（actual>expected）⇒ `semantics good` **FAIL `guest_exit=5`、脚本 rc=1**；改**大**（actual<expected）⇒ 同样 **FAIL `guest_exit=5`、rc=1**；旧错常量 `0x1234FFFFFFFF` ⇒ **FAIL `guest_exit=5`**（完成区「原 exit=0 是单向撞出来的假绿」成立）；还原后 md5 `8439c91e…` 与备份逐字节一致。
- **注释自洽**：`set-ft-fo.s` 头部已改新口径（`rd2rf` 清零 + 每个非零 wyde 一条 `set.w`、k≤3 ⇒ 1+k、k==4 退回 4 条），与本文件五形态用例、`NOPSEUDO-NOT` 及实测一致。
- **完成区第 7 条**：与我实测逐条对齐（good=0；case1 `+1`/`-1` ⇒ **1/1**；case5 改小/改大 ⇒ **5/5**；旧常量 ⇒ **5**），期望常量已是 `0x12340000FFFFFFFF`，无残留「撞出来的绿」。
- **`2741009b` spec 订正 vs lit**：lit 的 `RUN:` 行不引用 `spec/`/`.md`（grep **0 命中**）⇒ spec 订正不可能影响 lit；我在 master 直跑同三条 suite 得 **174/176、2 FAIL**，根因是 **`.work` 为共享符号链接**（任务 worktree `.work -> /mnt/tao/DADAO-v5/.work`，`llvm-mc` 同 inode `25063900`）⇒ master 处于「新 `llvm-mc` + 尚未合入的旧测试文件」在途态，与 spec 订正无关；任务 worktree 侧 **176/176 rc=0**，合入后 master 即回绿。
- **越界/还原**：`git status -uall` 仅 `本任务书` + `tests/unit/llvm/lit/MC/DADAO/set-ft-fo.s` 两处（均属返工面），实现/补丁/契约/oracle 未动；全部注入 `cp`+md5 还原、md5 相等。

## 完成区

**测试结果**：证据脚本 **22/22**（`--inject` **31/31**，2 路源码注入 + 4 路方向反例均可达 FAIL、`cp`+md5 还原回绿）；lit `MC/DADAO`+`CodeGen/DADAO`+`e2e` **176/176**（`make check-lit` rc=0，走构建树工具）、`MC/DADAO-gen` **11/11**、`check_lit_gen` **62/62**、`validate_mc_vectors` **83 向量/0 错**、`check_lit_bytes` 258 patterns；门控 `check-asm-list-drift`/`check-asm-prose`/`check-isa-coverage`/`check-component-changelog`/`check-contracts-pending` rc=0；`check-patch-tree` **llvm-project 段 99 补丁 0 断言问题**、`--source-state` llvm `OK clean=True count=1`（全仓 rc=1 仅 chipyard 段 4 问题，非本任务）。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（+19 行，`series` 99 不变）、`components/llvm-project/changelog.md`（M13 追加 1 条）、`tests/unit/llvm/lit/MC/DADAO/m4-pseudo-set.s`、`tests/unit/llvm/lit/MC/DADAO/set-ft-fo.s`、`.tao/contracts/contract-asm.md`（仅 §6「保留 8 条」那条）、`tools/testcases/validate_mc_vectors.py`（**越界，见待裁定 1**）、本任务书。
**验收结果**（`llvm-mc -filetype=asm` 实测序列，构建树工具）：
1. `set.fo rf1, 0` ⇒ **1 条** `rd2rf {rf1}, {rd0}`；
2. `set.fo rf2, 0x1234` ⇒ **2 条** `rd2rf {rf2}, {rd0}` / `set.w rf2, wp0, 0x1234`；
3. `set.fo rf3, 0x12345678` ⇒ **3 条** `rd2rf {rf3}, {rd0}` / `set.w rf3, wp1, 0x1234` / `set.w rf3, wp0, 0x5678`；
4. `set.fo rf4, 0x123456789ABC` ⇒ **4 条** `rd2rf {rf4}, {rd0}` / `wp2 0x1234` / `wp1 0x5678` / `wp0 0x9abc`；
5. `set.fo rf5, 0x123456789ABCDEF0`（k=4）⇒ **4 条** `set.w rf5, wp3/wp2/wp1/wp0 = 0x1234/0x5678/0x9abc/0xdef0`（**无 `rd2rf`，不是 5 条**）；`set.fo rf6, 0x3FF0000000000000`（k=1 高半非零）⇒ 2 条 `rd2rf {rf6}, {rd0}` / `set.w rf6, wp3, 0x3ff0`；
6. `set.ft rf7, 0x12345678` ⇒ **仍 2 条** `set.w rf7, wp1, 0x1234` / `set.w rf7, wp0, 0x5678`；
7. **语义不变**（第 2 轮返工后重测）：qemu `dadao-tiny` 跑 5 例探针，每例用 `br.ne {rdA, rdB}?` **双向**判不等（`cmp.uo`+`br.n` 只判「小于」，已弃用）：k=4 / 高半非零 / k=3 / k=0 / `set.ft` 窄写（期望 **`0x12340000FFFFFFFF`**：高半 `0x1234_0000` 由 `set.fo` 写下、低半 `0xFFFF_FFFF` 由 `set.ft` 覆盖，按 `SimRISC-00 §5.3`）⇒ guest exit=**0**；四路方向反例均红：case1 期望 **+1**（actual<expected）⇒**1**、case1 期望 **-1**（actual>expected）⇒**1**、case5 期望改小 ⇒**5**、case5 期望改大 ⇒**5**；旧（错）常量 `0x1234FFFFFFFF` 在双向比较下 ⇒**5**（即原「exit=0」是单向比较撞出来的假绿）。
8. **注入**（`cp`+md5）：① `Nz<=3`→`Nz<=4` ⇒ k=4 实测 **5 条** `rd2rf`+4×`set.w`（断言红）、还原 md5 `56e297fd…` 一致后回 4 条；② `set.ft` 两支 `set.w`→`rd2rf rf, rd0` ⇒ guest exit=**5**（case5 高 32 被清零）、还原后回 0。
**新发现/坑**：① `-filetype=asm` 的空行受「该语句行有无行尾注释」影响（同一文件里有无空行混排）⇒ 不能用 `ASM-EMPTY:` 钉条数；objdump 输出无空行，跨例 `CHECK-NEXT` 串联才是可靠的「条数」钉法。② `set.w` 的 `ha[23:18]` 是**目的 rf 号**（`wpN` 在 `[17:16]`），手算字节极易把 `ha` 当成常数 1。③ 改组件补丁须先让组件源树收敛为「base+1 且干净」才允许导出（`make_patch.py` 拒绝脏树）；`git commit --amend --no-edit` 即可，导出后源树/构建树不受影响。④ `check_lit_bytes.py` 只认 `@@ OBJ:` 字面，`OBJ-NEXT:` 行不被独立复算（本任务新字节全部落在 `OBJ-NEXT`，其真值为实测 objdump + `opcodes.yaml` 字段口径）。
**遗留问题**：① 越界文件 `validate_mc_vectors.py` 待确认（待裁定 1）；② DDLN 讲义 `DD-A005:87,103`、`DD-A002:156` 未同步（待裁定 2）；③ `.tao/contracts/contract-asm.md:192`「当前状态：v5 汇编器**尚未实现**伪指令展开」为陈旧陈述（早于 m4 实现），不在本任务「仅该条」改动面内；④ `check-patch-tree` 全仓 rc=1 仅因 chipyard 段 4 断言问题（在飞任务），llvm 段 0 问题；⑤ `make check-lit` 需 `LLVM_TOOLS_DIR=<构建树> DADAO_LIT_ALLOW_TOOLS_OVERRIDE=1`（禁 `install-host`，安装根仍是旧二进制；安装根刷新归主会话在组件合入后统一做）。
**耗时申报**：`ninja -j32 llvm-mc llvm-objdump` 增量 ~45 s；注入自检 4 次重建共 ~3 min；lit/门控 ~2 min；未 `install-host`、未 sync/reset 节点。
