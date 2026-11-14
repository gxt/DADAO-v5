# m13-gem5-012: `ext.uo`/`ext.so` orrr 的 `hd` 取 `rdHD[5:0]`（删 ILLI 路径）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-spec-008`（口径真源与契约先行；本任务依据其 §2.2 措辞与「用户裁定」段）
**可并行分片**：否（gem5 单组件单写者；可与 `m13-qemu-010` 并行，与其它 gem5 任务串行）
**状态**：已验证

**预估**：2–3 h（含 gem5 增量重建 10–25 min，开工前申报实际耗时）

## 用户裁定（2026-11-13）

> 「`ext.*` 的 orrr 形式，`rdHD` 取**低 6 位**作起始位 `hd` 后继续执行，**不抛 ILLI**。」

- **渠道**：用户 2026-11-13 裁定，由主会话转达；原话登记于 `ISS-422`（`.tao/knowledge/issues.yaml`）。
- **口径**：`hd = rdHD & 0x3F`；`rdHD` 高位忽略、不抛异常。`orri` 形式的 `immu6` 天然 6 位、行为不变。

## 背景（现状与缺陷）

- `components/gem5/patches/src/arch/dadao/exec/b3.cc.patch`：
  - `extendStartBit()` 注释自陈「orrr = the full 64-bit rdhd *register value*, so >63 is checkable; contract-isa §6.4.2」——把「可检查」当成了「须报错」。
  - `case B3Op::ExtUo/ExtSo` 内：`const uint64_t start = extendStartBit(inst, ctx);` 后紧跟 `if (start > 63) return Fault::Illegal;`（注释「orrr takes the whole register value, so 64..2^64-1 is ILLI」），再 `hd = start`、`mask = lowMask(hd + 1)`、符号位取 `(value >> hd) & 1`。
  ⇒ `rdHD=64` 等取值被判 ILLI（实测退出码 `0xF8`=248），与 chipyard 相反（`ISS-422`）。
- `components/gem5/patches/src/arch/dadao/exec/b3_test.cc.patch` **把旧行为钉成了期望**：「orrr hd comes from the whole rdhd register value: 64 and 2^64-1 are illegal, and nothing is written.」，`badHds[] = {64, 65, 0xFFFFFFFFFFFFFFFF, 1<<40}` 逐个断言 `Fault::Illegal` + `writes.empty()` ⇒ 本任务必须同步改这组断言，否则 `check_b3.py` 必红。
- chipyard RTL 对照（只读溯源，非执行依赖）：`WumingDecoder.orrrShift` 把 `rdHD` 值送 ALU 的 6 位 `shamt` 端口 ⇒ 天然截低 6 位。

## 范围（只改 gem5 组件）

1. **`.../exec/b3.cc.patch`**：`ExtUo`/`ExtSo` 分支删 `if (start > 63) return Fault::Illegal;` 与其理由注释；`hd` 改为截低 6 位——**二选一**（实现须自洽、注释同步改述为「`hd = rdHD[5:0]`，高位忽略（spec §2.2 / `ISS-422`）」）：
   - 甲：`hd = static_cast<unsigned>(start & 0x3F)`（调用点掩码）；
   - 乙：`extendStartBit()` 内 orrr 分支返回 `value & 0x3F`（若该函数**仅** ext 使用；先 `grep` 确认调用者，若另有 shamt 使用者则只能取甲）。
   `dst == 0 ⇒ Fault::Illegal` 保留不变。
2. **`.../exec/b3_test.cc.patch`**：把「`badHds ⇒ Illegal` + 无写」一组**替换**为截低 6 位口径，并与「高位被忽略」互证：
   - `rdHD=64` ⇒ 与 `hd=0` **同值**、**恰一次写**；`65 ⇒ hd=1`；`0xFFFF_FFFF_FFFF_FFFF ⇒ hd=63`；`1<<40 ⇒ hd=0`；`0x43(67) ⇒ hd=3`；
   - 期望由 spec 口径在测试内独立手算：`mask = lowMask((start & 63) + 1)`、`result = value & mask`、`ExtSo` 且 `(value >> (start & 63)) & 1` 为 1 时 `|= ~mask`；每个新用例附 `spec_cite`（`SimRISC-04: ext.uo` / `ext.so`）与「低 6 位」依据；
   - `dst rd0 ⇒ Illegal`、`orri immu6` 既有断言保持不变。
3. `components/gem5/changelog.md` 记一条。
4. **oracle 向量（独立派生）**：新增/改动的期望**不得**由被测实现输出反填；除 harness 断言外，另建一组 ≥6 条的 oracle 表（覆盖 `ext.uo`/`ext.so` × `hd∈{0,3,63}` × 源值「全 1」「bit_hd=1 的最小数」），逐条写出「位段复制 + 符号/零扩展」的手算过程，落完成区或证据脚本注释。
5. **增量重建**：`make build-gem5`（改单文件，预计 10–25 min；开工前申报，完成后记录实测墙钟）。

**非范围**：不改 `tests/inst/**`（归 `m13-testcases-033`）、不改 spec/合约（归 `m13-spec-008`）、不改 qemu/chipyard、不改 B3 之外的 `exec/*.cc`。

## 验收标准（可执行、可失败）

1. **组件 harness**：`python3 tools/gem5/check_b3.py` `rc=0` —— `B3 coverage 42/42`、harness 与 live 集合双向差集为空、`PASS` 计数现场值（较施工前增加新用例数、`FAIL=0`；施工前计数先抄一份做对照）。
2. **真实 gem5 二进制（非 harness）**：`.S` 探针经 `tools/testcases/inst/run_asm_suite.py --platforms gem5`（或等价 SE/FS 单例）执行 —— `rdHD=64` 与 `hd=0` 结果**逐字节相同**，`rdHD=67 ≡ hd=3`、`rdHD=63 ≡ hd=63`；**不再出现 ILLI**（旧为 `0xF8`）。
3. **旧行为可达 FAIL**：施工前 gem5 二进制（`md5`/构建 commit 钉住并抄进完成区）跑同一探针 ⇒ ILLI；改后 ⇒ 正常。若旧二进制已被覆盖无法复原 ⇒ 用「注入 ② 恢复 `start > 63 ⇒ Illegal`」作为等价 FAIL 路径，并在完成区说明替代理由（禁写「推定」）。
4. **回归**：`make check-gem5-decode` rc=0（264 行 decode 断言不退化）；`python3 tools/gem5/check_b7.py` rc=0（FP 族不受影响，作回归项；ext 不属 B7）。
5. **可达 FAIL 注入（≥2 路；`cp` 备份 + md5 对账 + `touch` 还原 ⇒ 回绿；禁 `git checkout/restore/stash`）**：
   ① 掩码改恒等（`hd = start`，且 ILLI 已删）⇒ `check_b3.py` 红（`rdHD=64` 期望不符 / 移位量越界）；
   ② 恢复 `if (start > 63) return Fault::Illegal;` ⇒ 新用例红（`64/65/0xFFFF…/1<<40` 四条 Fault 不符）。
6. **门控**：`check-patch-tree` 的 **gem5 子集 problem=0**（整树红若来自并行任务在飞，须现场归因并给子集判据）；`check-component-changelog` rc=0；`check-source-state` 的 **gem5 OK**（`base+N`、`clean=True`）。
7. **脚本与对账**：一键证据脚本 `rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 说明

- gem5 侧「B 组探针」指 **B3 断言 harness（`exec/b3_test.cc` + `tools/gem5/check_b3.py`）**；`check_b7.py` 是浮点 B7 的门控、与 `ext` 无关，只作回归。
- 组件补丁须走 `make_patch`（一文件一补丁）导出；`check-patch-tree` 保持 problem=0。
- 重建期间 `free -g` 可用内存 < 8 GiB ⇒ 降 `JOBS` 并记录次数；禁 `-j$(nproc)`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树；组件源树改动收敛为 `base+1` 且干净（不入本仓库）。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数取现场值；「修改文件」与 `git status -uall` 对账。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入 → FAIL → 还原（`cp`+md5）→ 回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查改动（`b3.cc.patch` 的 ext 分支与 `extendStartBit`、`b3_test.cc.patch` 的 oracle/宽 rdHD 用例、证据脚本）后的意见与处置：

- **F1** 掩码放在调用点（`extendStartBit(...) & 0x3F`）而 helper 仍返回 64 位原值：若将来新增调用者会静默拿到未截值。核实 `extendStartBit` 仅 ext 分支一处调用（`grep` 全树），且 orri 分支 `immu6` 本为 6 位、掩码幂等；保留调用点掩码以贴合「起始位在此处定义」的注释。处置：❌不修（附调用点唯一性证据）。
- **F2** 证据脚本把 harness PASS 计数写死为 4318：任何合法新增断言都会转红，且属「覆盖类计数写死」。处置：✅已修——改为 `>= 4318`（施工前 4248 + 70，差值来源写进脚本注释），删除断言仍会跌下界。
- **F3** 证据脚本对 `check-patch-tree` 的 gem5 问题用 `.*problem` 匹配，而真实问题行格式是 `gem5: assertion ⑨: …` ⇒ 该断言恒真、无 FAIL 路径。处置：✅已修——改匹配 `^check-patch-tree: gem5: assertion`，并新增「checker 确实检查了 gem5（106 patches 行存在）」；把注入一行多余文本进 `b3.cc.patch` 实测出现 `gem5: assertion ⑨`（rc=1），`cp` 还原后 md5 一致、gem5 段回 0。
- **F4** 旧 gem5 在链例中遇意外 ILLI 不会返回 248（hmon 返回槽未武装 ⇒ 重复执行故障指令挂死）。处置：✅已修——探针链例开头写 hmon+0xF8=pad 与 `TEST_FAULTV={ILLI one-hot,248,248}`；旧二进制稳定 rc=248、无输出，改后二进制不受影响，三平台仍共用同一 ELF。
- **F5** 任务 worktree 基线落后 master，共享组件源码树含 master 新补丁 ⇒ `make_patch.py` 顺带改写了 4 份无关补丁。处置：✅已修——FF 到 master 后用 `git archive HEAD <4 文件>` 还原（未用 checkout/restore），`git status` 仅余 2 份目标补丁；并记录为「新发现/坑」。
- **F6** 全树 `check-patch-tree` rc=1（chipyard 8 条，`m12-chipyard-016` 在飞）：非本任务文件，按 gem5 子集判据（0 问题）通过。处置：⏸延后（归并行任务），不计本任务遗留。
- **F7** 复核验收映射：`ext.so` 用 bit0=1 源值（`0x1`/`0x8`）区分 uo/so；12 行 oracle 期望由 spec 手算，三平台实测逐字节相同（md5 `7c5058f4…`）反证手算正确；`dst==rd0 ⇒ ILLI`、orri 两例回归均保留。无新问题。

### 第 1 轮 reviewer 验收（2026-11-14）

**重跑（本人执行；`rc=$?` 现取，workdir=任务 worktree）**
- 一键证据 `./.work/evidence/m13-gem5-012/run.sh`：**rc=0、30 PASS/0 FAIL**（41–52 s）；注入后同脚本 rc=1（6 FAIL）；还原后回绿 rc=0、30 PASS。
- 独立探针：自建 ELF `81852ba1…`，期望**由我手算**得 md5 `7c5058f40f7b769587a1b80f16a0efcf`（80 B）；gem5/QEMU/chipyard 三侧 `cmp` 对我手算值及相互全 `rc=0`，`xxd` 十槽 = `1,f,~0,80…0,~0,…f8,80…0,7,~0,…f8`。
- 改前正证：`old-gem5.opt.pre-hd` md5 `b6440f19c19e02ab6408ffcf4b7acf75` 同 ELF ⇒ **rc=248（`GEM5_EXIT_CODE=248`）、0 B**。
- 快门控：`check_b3 rc=0 PASS=4318 FAIL=0`、`check-gem5-decode rc=0 PASS=694`、`check-wuming-cycles rc=0 PASS=11`、`check_b7 rc=0`、`check-component-changelog rc=0 PASS(9 文件×4=36)`、`--source-state` ⇒ `gem5: OK … clean=True`；施工前基线二进制 `dadao-b3-test-baseline` ⇒ **PASS=4248 FAIL=0**（+70 与 `12×3+5×5×2−16` 算式一致）。
- `check-patch-tree`（任务 worktree）：rc=1，`gem5: 106 patch(es)`、`gem5: assertion` **0 条**；全树 8 条 = chipyard 6 + qemu 2（`dadao-machine.c`）。
- **独立注入（自设计第 3 路，非其两路）** `& 0x3F`→`& 0x1F`：`check_b3 rc=1 FAIL=19`（`rdHD=63` oracle 行与 `rdHD=0xFFFF…` 宽用例转红，orri hd=32/62/63 亦红 ⇒ 反证 `&0x3F` 对 orri 恒等）；同一 `run.sh` ⇒ rc=1、6 项 FAIL；`cp` 还原 md5 `b721c73c…` 与备份一致、源树 `git status` 空；重跑回绿 rc=0。
- 披露①：`48e6c614` 父 = `c4002ae8`，`git diff` 仅 4 文件（2 目标补丁 + changelog + 任务书），`components/**` 补丁仅 2 份，`tests/ spec/ contracts/` 0 文件。
- 披露②：探针删去 hmon 武装 ⇒ 旧二进制 **rc=124 挂死**（60 s 超时、无 EXIT_CODE），新二进制 rc=0、80 B ⇒ 解释成立。
- 解码表：4 条 `ext.*` 行 `kRules128..131={"dst_rd0"}`、`kLegality={"rdhb != rd0"}`，无 hd 范围约束 ⇒ 无需改。

**约束核验**：范围 4 文件✓；不改 spec/契约/qemu/chipyard/tests✓；`dst==rd0⇒ILLI` 保留✓、orri `immu6` 不变✓；完成区 17 行≤30✓；任务工作树/源树/主工作树 `status -uall` 全空、4 文件 md5 与开工快照逐个相等（本记录写入后仅任务书 1 文件为 `M`，其余 3 交付物 md5 未变）✓；未跑 `install-host`/`check-modules`✓。

**Findings（文档级，不阻断，交 architect 收尾改）**：① 完成区「8 条问题全部来自 chipyard」与现场不符（实为 chipyard 6 + qemu 2，`hw/dadao/dadao-machine.c` ⑨/⑥；gem5 子集 0 不变）；② 任务书「每个新用例附 `spec_cite`」实为块注释引用（逐行仅 `why` 给低 6 位依据）；③ **依赖状态在审查期间变化**：开审时 `m13-spec-008` 为「待开始」、四处仍写 `hd>63⇒ILLI`，收尾时已「已验证」，我在主工作树现场 grep 确认 `spec/SimRISC-04 §2.2`、`contract-isa §6.4.2`、`legality_rules.yaml`、`DD-A008` 均已改为 `hd=rdHD[5:0]` 口径 ⇒ 实现与真源现已一致，无需返工；④ F5 用 `git archive HEAD <4 文件>` 还原（近 `git show|>` 禁例），作用域限本任务独占 worktree、终态已对账。

**环境观察（非本任务）**：主工作树在验收窗口内被并行会话写入（`m13-spec-008` 落地，`UU manifests/spec-readonly.lock.toml` 合并未完）；本任务三份交付物 md5 与开工快照逐个相等、任务工作树与 gem5 源树 `status -uall` 空，核验未受影响。

**判决：Accepted** —— 验收命令块在我本人重跑下全过、注入→FAIL→还原→回绿实证、硬约束无违反。

## 完成区

**测试结果**：一键证据脚本 rc=0（30 项全 PASS）；`check_b3.py` PASS 4248→4318（+70，FAIL=0）；`check-gem5-decode` 694 行 PASS；`check-wuming-cycles` 11/11；`check_b7` OK；`check-component-changelog` PASS；`check-patch-tree` gem5 段 0 问题；`--source-state` gem5 OK（`base+1`、`clean=True`）。全树 `check-patch-tree` rc=1，8 条问题全部来自并行任务在飞的 chipyard（`WumingSemi.*`/`WumingCore.scala`/`WumingDecoder.scala`，非本任务文件）。

**修改文件**：`components/gem5/patches/src/arch/dadao/exec/b3.cc.patch`（orrr `hd = extendStartBit(...) & 0x3F`，删 `>63 ⇒ Illegal`，注释改述 spec §2.2/ISS-422）；`components/gem5/patches/src/arch/dadao/exec/b3_test.cc.patch`（旧「64/65/2^64−1/1<<40 ⇒ Illegal 且无写」→ 12 行手算 oracle + 5 个宽 rdHD 等价用例，头注释去 ext hd>63）；`components/gem5/changelog.md`（M13 一条）；本任务书（状态/完成区）。组件源码树与 `git status -uall` 对账一致，补丁经 `make_patch.py gem5` 重导出（106 份、2 written），源码树 `base+1` 且 clean。

**验收结果**：
- 探针（同一 ELF，10 检查点 × 8 B = 80 B）：QEMU / gem5 / chipyard 三平台逐字节相同且等于手算 oracle（md5 `7c5058f4…`）。
- 四组：rdHD=64≡0（uo `0x1`；so 取 bit0=1 源值 ⇒ `0xFF…FF`，用以区分 uo/so）、67≡3（uo `0xF`；so `0xFF…F8`）、2^64−1≡63、63≡63；另 2 例 orri 回归。
- 改前二进制（md5 `b6440f19…`，改动前构建，备份于证据目录）跑同一 ELF ⇒ rc=248（ILLI）、0 字节；改后 ⇒ rc=0、80 字节。
- 注入 2 路（`cp` 备份 + md5 对账还原，每次还原后回绿）：① 去 `& 0x3F` ⇒ `check_b3` rc=1、FAIL=16；② 恢复 `>63 ⇒ Illegal` ⇒ rc=1、FAIL=40；两次还原 md5 均 `b721c73c…`、回绿 rc=0。
- B3 解码表：4 条 `ext.*` 行规则仅 `dst_rd0`、无 `hd` 范围约束 ⇒ 无需改动（`check-gem5-decode` 694 行不变）。

**新发现/坑**：任务 worktree 基线落后 master，共享组件源码树含 master 新补丁 ⇒ `make_patch.py` 会顺带改写无关补丁（已 FF 到 master，只保留 2 份目标补丁）。旧 gem5 对链例中意外 ILLI 会因 hmon 返回槽未武装而挂死（非 248）；探针在链例开头写 hmon+0xF8=pad 与 TEST_FAULTV={ILLI one-hot, 248, 248} 后，旧二进制稳定 rc=248，且三平台共用同一 ELF。

**遗留问题**：无。

