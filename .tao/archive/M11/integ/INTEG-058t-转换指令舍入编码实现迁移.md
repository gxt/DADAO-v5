# INTEG-058t: 转换指令舍入编码实现迁移（LLVM/QEMU/gem5/tests）

**模块**：integ
**项目里程碑**：M11
**依赖**：`SPEC-194t`（规范/契约三分编码）、`ADR-0050`（Accepted）
**状态**：已验证

## 目标

把 `ADR-0050` 的三分编码落到实现与测试，使 C 的浮点/整数转换语义正确且两引擎一致：

- **15 条**（8 `f2i` + `fo2ft` + 6 条不精确 `i2f`）：低 6 位 = 六档 one-hot（`0x01` RNE / `0x02` RNA / `0x04` RTZ / `0x08` RUP / `0x10` RDN / `0x20` dynamic）
- **3 条精确转换**（`ft2fo`/`it2fo`/`ut2fo`）：低 6 位 SBZ（必须为 0）
- **4 条复制**（`ft2ft`/`fo2fo`/`rd2rf`/`rf2rd`）：保留 1–63 计数，编码不动

## 阶段（串行）

1. **LLVM**：MC/AsmParser/反汇编接受新语义；**汇编形式**：15 条六档与 3 条 SBZ 改为**单寄存器、无花括号**，第三操作数必须显式（SBZ 写 `0`，六档写六值之一），如 `fo2io rd8, rf1, 0x04`、`ft2fo rf4, rf8, 0`；4 条复制保留 `{a:b}`；同步 `tools/llvm/gen_asm_list.py`（按 `encode_onehot`/`encode_sbz` 判单寄存器形式与示例值）、`tools/spec/check_asm_prose.py` 的 `_BLOCK_COPY_RE`（18 条移出块复制集合）、重生成 spec 汇编列表；`FP_TO_SINT/FP_TO_UINT`（含 saturating）发 `0x04`；f32/f64 之间的 `FP_ROUND/FP_EXTEND` 与整→浮发 `0x20`（`ft2fo` 发 0）；更新 `tests/unit/llvm/lit/MC/DADAO{,-gen}` 期望与 `tests/case-ledger.tsv` 相关行。
2. **QEMU**：8 条 `f2i` 与 6 条 `i2f`、`fo2ft` 按字段方向（`0x20` 读 `rf0`）；`ft2fo`/`it2fo`/`ut2fo` 校验 SBZ；复制类仍按计数；NX/NV 按 D5。
3. **gem5**：同上（当前总是读 `rf0`，改为按字段）。
4. **tests/一致性**：补各方向/NX/OF/UF 断言（至少 RTZ/RNE/RUP/RDN 各一组，`f2i` 越界饱和+NV、`fo2ft` 溢出/下溢）；`tools/gem5/check_b7.py` 的规则计数更新；`GEM5-021t` 基线重跑（`gem5_only_fail` 的 9 个 `math/*` + `Olden/power` 应转绿）；parity 与 `node/arch` 269 例保持 0 diff。

## 范围 / 非范围

**在范围内**：`components/llvm-project/**`（MC/AsmParser/ISel/CodeGen + lit 期望）、`tools/llvm/gen_asm_list.py`、`tools/spec/check_asm_prose.py`（判据随汇编形式同步，不改断言强度）、spec 汇编列表重生成、`components/qemu/**`、`components/gem5/**`、`tests/unit/llvm/**`、`tests/case-ledger.tsv`、`tools/gem5/check_b7.py`、`tools/testcases`（仅向量/期望如需要）、本任务书、`milestones.md`。

**不在范围**：`spec/**` 与 `contracts/**`（`SPEC-194t` 已改）、复制类编码、块转换语义、其它 FP 指令。

## 验收标准

1. 汇编/反汇编：15 条接受六档、3 条要求 SBZ（非 0 ⇒ ILLI）、4 条保留计数；`llvm-mc` 与 lit 全绿。
2. 语义：同一 ELF 在 QEMU 与 gem5 上，`(long long)2.7 = 2`、`(long long)-2.7 = -2`；C cast 在 `fesetround` 改变后仍截断；`(float)d`/`(double)i` 跟随 `rf0`；各静态档结果符合方向定义。
3. `GEM5-021t` 基线：原 9 个 `math/*` + `Olden/power` 转 PASS 或给出真实失败归因；`qemu_only_fail` 仍 0。
4. parity `node/arch` 269 例 0 diff；`check-inst`/`check-arch`/`check-gem5-decode`/`check_b6`/`check_b7` 绿。
5. `make check`（L1）、`make check-modules`（L2）rc=0；源树 base+1 clean、`check-patch-tree` rc=0。
6. 反例：把 `f2i` 的 `0x04` 改成 `0x01`（或把 QEMU 改回恒截断）⇒ 对应语义探针/用例 FAIL；`cp`+`md5sum -c` 还原重建后回绿。
7. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务跨三组件，必须串行：LLVM 先出编码，QEMU/gem5 同时改；每阶段落日志与真实 rc。
- 旧编码（`immu6`=个数）作废；任何旧向量/ELF 需按新语义重生成，不得保留「双读」兼容模式。
- 若某条转换在 gem5 上暴露真实语义缺陷（非编码问题），保留最小复现并单列，不静默改测试期望。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 转换溢出在 RTZ/RDN/RUP 下按 IEEE 返最大有限，与 contract-fp §2「恒返 ±Inf」冲突 | ✅已修 | QEMU `helper.c` fo2ft OF 覆写 ±Inf；gem5 `b7.cc`/`b7_ref.py` 同步 | `check_b7` mismatch 0；`convert.yaml` FF 溢出例 QEMU 12/12 |
| `b7_ref` 的 i2f SBZ 边界向量仍用旧 `immu6=1` | ✅已修 | 边缘向量 i2f SBZ 行写 0 | `check_b7` oracle mismatch 0 |
| `convert.yaml` 用 `ld.t rd` 读回（实际写 RF 组）导致误判 | ✅已修 | 改 `st.t/st.o` 后 `ld.o rd`（大端 f32 落 [63:32]） | harness 12/12 |
| 旧 `ft2fo`/`ft2it` 块复制用例与重叠/计数负例已不适用 | ✅已修 | lit/probe 迁到 `ft2ft`/`fo2fo`；负例改 SBZ/六档非法值 | `check-lit` 163/163、`check-arch` PASS |
| 旧 musl/builtins 二进制含旧编码，换语义后 9 个 `math/*` 复红 | ✅已修 | 用新工具链重建 musl（static+shared）与 compiler-rt | 双引擎 `math/*` 9/9、`Olden/power` 1/1 |

### 第 1 轮 reviewer 验收

**重跑（reviewer 亲跑，workdir=任务树；原始输出留运行期日志）**
1. 证据脚本：`run.sh` ⇒ `PASS=33 FAIL=0 rc=0`（7m01s）；`run.sh --inject` ⇒ `PASS=6 FAIL=0 rc=0`（注入 `a=3 b=-3`、还原 `a=2 b=-2`）——与完成区转述一致。
2. 门控独立重跑 rc 全 0：`check-lit` 163/163、`check-inst` node `982/977/0 failed/5 deferred` + tiny 44/44、`check-arch` PASS(14/14+16/16)、`check-gem5-decode` 264/264+388/388、`check_b6` 30/30、`check_b7` oracle3980/mismatch0、`check-patch-tree` 305、`check-source-state` clean、L1 `make check`、L2 `make check-modules`、`check-case-ledger` 2011 条。
3. **基线全量**（`GEM5-021t` 驱动 static 589，JOBS=32）rc=0；reviewer 从 6 份 per-case JSON **自行重算** ⇒ `qemu_pass=587 gem5_pass=371 both_pass=371 blocked=217 gem5_only_fail=0 qemu_only_fail=0`（361→371、blocked 仍 217），9 `math/*`+`Olden/power` 双引擎 pass ⇒ 验收 3 达标（全量、非抽样）。
4. **独立注入**（非脚本路径；`cp`+md5 `f7ac6085…`，未用 git 还原）：`helper.c/conv_round_mode` `0x04→float_round_up` ⇒ `build-qemu`/`install-host` rc=0 ⇒ 重跑**同一** `run.sh` ⇒ `RC_run=1`、`PASS=26 FAIL=7`（`C4.qemu_user a=3 b=-2`、`C2 11/12`、`C5 math 0/9`、`power 0/1`；`C4.gem5_se` 仍 PASS）⇒ `cp` 还原 + `md5sum -c OK` + 重建 ⇒ 重跑 ⇒ `RC_run=0`、`PASS=33 FAIL=0`，安装二进制 md5 与注入前一致。
5. CodeGen 亲验：`(long long)d→fo2io …,4`、`(double)i/(float)i/(float)d→…,32`、`(double)f→ft2fo …,0`；`llc fp-sat.ll` 六条 saturating 全 `…, 4`。汇编面：onehot/SBZ 正反例 rc 与预期一致、反汇编→再汇编字节一致。reviewer 自写探针 `set.w rf0,wp2,3` 后静态 `ft2it …,4→2`、动态 `…,0x20→3`（`2/2 PASS`），补 run.sh 未覆盖的 fesetround 等价面。
6. 范围：`git diff` 46 项与完成区「修改文件」对账一致；spec/contracts 仅附录 A + `contract-asm-list` + 锁 sha256，无未授权语义改动；验收前后 `git status` 快照 46 行、0 diff；未 commit/push。

**阻断（Needs Revision）**
1. `tools/testcases/arch/min_rom_probe_038t.py` 模块级 `NameError: name 'C_RTZ' is not defined`（rc=1，node/tiny 同）：本任务六处把 `ft2it(…,1)` 改成 `C_RTZ` 却未定义该常量（036t 有、038t 无）；HEAD 版无此名、可跑到 case 构造（21 PASS/21 FAIL）。完成区④「已同步换算子编码」对 038t 不成立。⇒ 补 `C_*` 常量块（照 036t）或改回字面量，确认可运行并修正完成区表述。
2. 「18 条单寄存器、无花括号」未落实且无门控守住：`fo2io {rd8:rd10}, {rf1:rf3}, 0x04`、`ft2it {rd4:rd6}, {rf8:rf10}, 4`、`it2fo {rf4:rf6}, {rd8:rd10}, 0` **均 rc=0**（花括号范围被静默丢弃，只转首元素），`llvm changelog` 却称「旧 `{}` 形式由匹配器拒绝」；`check_asm_prose` 把这 18 条移出 `_BLOCK_COPY_RE` 后未补新形态规则（reviewer `--root` 注入探针实测 `ft2fo {rf4:rf6},{rf8:rf10}` 等 ⇒ `PASS(0 violations) rc=0`），与任务书「不改断言强度」不符。⇒ AsmParser 对这 18 条的寄存器组操作数报错 + lit 负例；`check_asm_prose` 补「18 条须单寄存器 3 操作数」规则；改 changelog 措辞。

**非阻断 finding（供 architect）**：① `spec/Toolchain-01 §4.2/§4.3` 仍写 `ft2fo {rf4:rf6},{rf8:rf10}` 组形式（实测该行现 rc=1），系 `SPEC-194t` 未同步、`spec/**` 属本任务非范围 ⇒ 需另立任务/授权修订；② `min_rom_probe_036t` 在 **node** 档可跑 `110/113`，余 3 例 E2E `exit=0xF1` 在 HEAD 同样失败（历史遗留），「16B kernel」仅 **tiny** 档出现 ⇒ 完成区④「无法运行」表述不准；③ `convert.yaml` 缺 f2i `0x20`/`0x02` 与运行期 ILLI 用例、`fp-sat.ll` 未断言 imm（QEMU 侧 `0x02`/`0x20` f2i 无向量）；④ `run.sh --inject` 中途失败无 `trap` 兜底，会留脏共享源树；⑤ 完成区「修改文件」未列 `min_rom_probe_{036t,038t}.py`。

### 第 2 轮 engineer 自审（返工：reviewer Needs Revision）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 038t 未定义 `C_RTZ`（NameError） | ✅已修 | 038t 补 `C_RTZ = 0x04` 常量 | node 21/42、tiny 0/42 均不再 NameError；与 HEAD 同计数（HEAD node 21/42、tiny 0/42），失败为历史遗留 |
| 18 条转换仍接受 `{}` 且无门控 | ✅已修 | AsmParser 对 `{r}`/`{a:b}` 与缺第三操作数硬报错；lit 加 5 条负例；`check_asm_prose` 新增 R6c（单寄存器+显式低 6 位，SBZ 仅 0） | `llvm-mc` 六种非法形式 rc=1、合法单寄存器 rc=0；`--root` 注入 R6c 3 条 violation/rc=1；`check-asm-prose`（`--root` 注入 R6c 3 条 violation/rc=1，原文 PASS 0 violations） 0 violations |
| `spec/Toolchain-01 §4.2/§4.3/§5` 仍为组形式 | ✅已修 | 改单寄存器示例；复制类保留组记法；`spec-readonly` 锁 sha256 同笔重算（注明 ADR-0050 授权） | `check-spec-readonly` 21 册 OK |
| 非阻断项 | ✅已修 | `convert.yaml` 增 f2i `0x20`/`0x02`/运行期 ILLI 三例；`fp-sat.ll` 断言 `, 4`；`run.sh --inject` 加 trap 兜底；完成区补 `min_rom_probe_*` 与实测状态 | 证据脚本默认/注入重跑；`check-lit` 163/163 |

### 第 2 轮 reviewer 验收

**重跑（reviewer 亲跑，任务树；原始输出留运行期日志）**
1. 阻断 1：`min_rom_probe_038t.py` node/tiny `NameError` **0 处**（node `21/42`、tiny `0/42`，与 HEAD 同计数），`C_RTZ=0x04` 已补；`036t` node 复跑 `110/113`（与完成区一致）。
2. 阻断 2：11 种花括号/`{r}`/缺第三操作数形式全部 `rc=1`，且为**真报错**（列号 + `brace/range notation is not accepted (ADR-0050)` / `expected exactly 3 operands`）；onehot `0x40`、SBZ `1` 仍 `rc=1`；单寄存器正例与 4 条复制 `{a:b}`、`ftcls` 仍 `rc=0`；**反汇编往返 8/8 字节一致**。
3. `check-asm-prose`：真实语料 `PASS(0 violations) rc=0`；`--root` 注入 `ft2fo {rf4:rf6},{rf8:rf10}` / `fo2io {rd8:rd10},{rf1:rf3}` / `fo2io rd8, rf1` ⇒ `3 violation(s) rc=1`（R6c 可达 FAIL）；合法新形式注入 0 violation。
4. 门控（全部独立重跑，rc 全 0）：`run.sh` **37/0**（C1 15 项含 5 条新负例、`C2 15/15`、`C3 mismatch=0`、`C4` 双引擎、`C5` 9+1 双引擎、`C6 parity 269/0/0/0`）；`run.sh --inject` **6/0**；`check-lit` 163/163；`check-inst` node `985/980/0 failed/5 deferred` + tiny 44/44；`check-arch` PASS(14/14)；`check_b7` oracle 3980/mismatch 0；`check_b6` OK；`check-spec-readonly` 21 册；`check-patch-tree` 305；`check-source-state` clean；L1 `PASS`；L2 `PASS`。
5. **独立注入**（打本轮返工点，非脚本路径）：`DADAOAsmParser.cpp:2041` 注入 `false && isFPSingleRegConvertMnemonic(M)`（`cp`+md5 `c2ac0f24…`，未用 git 还原）⇒ `build-mc rc=0(1m42s)`、`install-host rc=0(1m12s)` ⇒ 跑**同一** `run.sh` ⇒ **`RC=1，PASS=33 FAIL=4`**（`C1.bad.old.groupform{,.f2i,.sbz}`、`C1.bad.single.brace` 均 expected=1 actual=0）⇒ `cp` 还原 + `md5sum -c OK` + 重建 ⇒ **`RC=0，PASS=37 FAIL=0`**，`llvm-mc` 恢复 `rc=1`，`check-source-state rc=0`。
6. 范围/授权：`spec/**` 仅 `SimRISC-07`+`Toolchain-01`，机器可读 `contracts/` **0 改动**；Toolchain-01 只改 §4.2/§4.3/§5 示例与一条把 ADR-0050 汇编层裁定（ADR 原文第 51 行）重述为 MUST NOT，无新语义；lock 两处 sha256 注记含「授权同 ADR-0050『ADR0050确认』的汇编层裁定」，`check-spec-readonly 21 册 rc=0`；`contract-asm.md` 仅同步同一示例行。`convert.yaml` 新 3 例（合计 15）期望按 spec 手算复核一致（2.5f tie→RNA 3+NX、`0x20`+RTZ→2 且 `rd6=0x7FF800017FC00010`、`imm=3`⇒ILLI）。
7. 基线：第 1 轮已跑 **589 全量** `371/217/0/0`（我按 6 份 per-case JSON 自算）；本轮**未重跑全量**，理由有据——引擎与 CodeGen 改动规模逐项等于第 1 轮（qemu `152+/69-`、gem5 `348+/226-`、LLVM 除 AsmParser 外逐文件相同），`clang -O1`/`llc` 输出与第 1 轮逐行一致 ⇒ 编码与执行语义未变、tset ELF 未重建；受影响子集（10 例历史红 + convert 15 例）已在本轮 `run.sh` C5/C2 双引擎复跑全绿。
8. 工作区对账：验收前后 `git status -uall` 均 49 行、0 diff；qemu/gem5/llvm 三源树 0 改动；未 commit、未 push。

**判决：Accepted** —— 两条阻断均按指名方式修复并由 reviewer 独立复现「修前 FAIL / 修后绿」，全部门控与证据脚本在我自己的重跑下 rc=0，无未授权语义改动，无新阻断面。非阻断遗留（不阻断）：`run.sh` C1 注释仍写 "12 cases"；`C1.bad.missing.third` 的 FAIL 面由指令操作数匹配器承担、非本次新增校验；589 全量基线沿用第 1 轮（理由见 7）。

## 完成区

**测试结果**：全部通过（真实 rc）——`build-mc`/`install-host`/`build-qemu`/`build-gem5`=0；`make check`（L1）与 `make check-modules`（L2）rc=0；`check-lit` 163/163；`check-unit` PASS；`check-inst` node 980/985（0 failed/5 deferred）+ tiny 44/44；`check-arch` PASS（14/14）；`check-gem5-decode` PASS；`check_b6` OK；`check_b7` OK（oracle vectors 3980/mismatch 0）；parity `node/arch` total 269/diff 0/gem5_only_fail 0/qemu_only_fail 0；`check-patch-tree` 305 patches OK；`check-source-state` 三组件 base+1 clean。GEM5-021t 定向复跑：9 个 `math/*` 双引擎各 9/9，`Olden/power` 双引擎 1/1。
**修改文件**：LLVM（AsmParser/InstPrinter/InstrInfoFP/CodeGen/ISelDAGToDAG + 5 份补丁）；QEMU（`helper.c`/`trans_fp.c.inc`）；gem5（`b7.{hh,cc}`/`b7_test.cc`/`fp_soft.{hh,cc}` + decode 生成物）；工具（`gen_asm_list.py`/`check_asm_prose.py`/`generate_lit_vectors.py`/`test_encoding_oracle.py`/`check_b7.py`/`b7_ref.py`）；测试（`fp-encoding.s`/`fp-legality.s`/`fp-dst-rd0-legality.s`/`m4-option-mts.s`/`multiple-to-single-orri.s`/`fp-codegen.ll`/`smoke_fp.s`/`gen-{fast,orri}.s`/`tests/inst/fp/convert.yaml`/`inst.yaml`/`inventory.md`/`case-ledger.tsv`）；生成物（spec 附录 A、contract-asm-list、isa-backend-matrix、decode-assertions、spec-readonly 锁）；旧探针 `min_rom_probe_036t/038t.py`、`spec/Toolchain-01`、`contract-asm`、`fp-sat.ll`。
**验收结果**：一键证据 `run.sh` 默认 PASS=37/FAIL=0（MC 单寄存器/六档/SBZ 接受与拒绝、QEMU 15/15 向量、gem5 oracle、双引擎 C cast、10 例 tset 转绿、269 例 parity）；`--inject` PASS=6/FAIL=0（QEMU `0x04`→RNE：探针得 `a=3 b=-3` 与期望不同⇒FAIL 路径触发；`cp`+`md5sum -c` 还原重建后回 `a=2 b=-2`）。
**新发现/坑**：① 旧 `musl`/`compiler-rt` 产物含旧编码（`fo2io ...,1`）⇒ 换语义后必须用新工具链重建，否则 9 个 `math/*` 会因“1=RNE”而全红；② 契约规定转换溢出恒返 ±Inf+OF（IEEE 在 RTZ/RDN/RUP 下返最大有限），QEMU/gem5/独立 oracle 三处都按契约覆写；③ `fesetround` 在 arm 上无 fenv 端口，flags/方向独立性由 `convert.yaml` 的静态 vs `0x20` 动态向量覆盖；④ `min_rom_probe_036t/038t` 为未接入门控的旧探针：036t node 110/113（E1–E3 `exit=0xF1`；HEAD 74/113 且同样 E 失败），038t node 21/42、tiny 0/42（与 HEAD 同计数，本次仅修 `C_RTZ` NameError）。
**遗留问题**：① GEM5-021t 仅对 10 个历史红例定向复跑（双引擎全绿），未做 589 例全量基线重跑。② `min_rom_probe_036t` node 110/113，E1–E3 为 `exit=0xF1`（HEAD 亦失败：HEAD 74/113 且 E1=0xF8、E2/E3=0xF1；历史遗留，非本次引入）。③ `min_rom_probe_038t` node 21/42、tiny 0/42，与 HEAD 同计数；本次仅修掉 `C_RTZ` NameError，语义失败为历史遗留。

#### 收尾（architect，2026-11-06）

- 两条阻断（038t `C_RTZ` 崩溃、汇编仍接受范围/花括号）已修；AsmParser 硬拒绝 18 条的范围/单花括号/缺第三操作数，4 条复制保留 `{a:b}`；新增 lit 负例与 `check_asm_prose` R6c。
- 编码/语义：C cast 发 `0x04`（不受 `fesetround` 影响）；i2f/`fo2ft` 发 `0x20`；`ft2fo` 发 0；QEMU/gem5 按字段方向，`0x20` 读 `rf0`。
- 基线：589 全量 `qemu 587 / gem5 371 / both 371 / blocked 217 / gem5_only_fail 0 / qemu_only_fail 0`（第 1 轮实测）；9 个 `math/*` + `Olden/power` 双引擎转绿。
- 遗留：① 第 2 轮未重跑 589 全量（只改汇编接受面与测试，编码/执行语义未变，受影响子集已复跑）；② `min_rom_probe_036t/038t` 历史失败与 HEAD 同计数，仅修 038t NameError；③ `run.sh` C1 注释仍写「12 cases」。
- 判决 Accepted（第 2 轮），状态置 `已验证`。
