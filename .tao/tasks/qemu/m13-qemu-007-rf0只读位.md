# m13-qemu-007: `ld.t rf0` 的只读位（QEMU 侧）

**模块**：qemu
**项目里程碑**：M13
**依赖**：无
**可并行分片**：否
**状态**：已验证

## 背景（争议 6，用户 2026-11-13 裁定 A）

`rf0` 是 FCSR 伪寄存器，同时是 fo 格式 qNaN。`spec/SimRISC-00` 规定 `[63:51]` 与 `[31:22]` **只读、写无效**。

- chipyard：按 spec（写无效）✅
- 模型：按 spec ✅
- **QEMU：会覆盖只读位** ❌ ⇒ `ld.t rf0` 类用例只能 model-only

## 目标

`target/dadao/` 的 `store_rf`（或等价路径）对 `rf0` 加写掩码：只允许写 `[33:32]`（舍入模式）与 `[4:0]`（标志），其余位忽略。

## 验收

1. `ld.t rf0` 写入 `0xFFFF_FFFF_FFFF_FFFF` 后读回：`[63:51]`/`[31:22]` 保持只读 qNaN 图样，`[4:0]`/`[33:32]` 为写入值
2. 与 chipyard、模型逐字节一致
3. `check-inst` rc=0；273 例 md5 不变
4. 可达 FAIL 注入（去掉掩码 ⇒ 用例红）

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 待裁定（交主会话）

1. **gem5（任务书所称「模型」）在 `ld.t rf0` 上不合规 ⇒ 验收 #2 本任务范围内不可满足。**
   - 实测（评测节点，同一份探针 ELF）：chipyard 与改后 QEMU **逐字节一致**；gem5 在 tetra 探针第 2 点红（guest exit=2）。gem5 `target/dadao/inst.cc` 的 `writeFloatLow32()` 写整低 32 位，覆盖只读 `[31:22]`（实测 `ld.t rf0 ← 0xFFFF_FFFF` 读回 `0x7FF8_0000_FFFF_FFFF`）；`ld.o`/`rd2rf` 走 `writeFcsr()` 掩码、**octa 探针在 gem5 上全绿** ⇒ 缺口只在 tetra 路径。
   - 结论：任务书前提「模型：按 spec ✅」不成立；本任务禁改 gem5 组件源。
   - 建议：新立 gem5 任务，把 tetra 目的写改成经 FCSR 写掩码（同一探针应转绿）。本任务 QEMU 侧已按 chipyard/规格实现并在证据脚本中**钉住**该缺口（tetra 红@2、octa 绿），不静默跳过。
   - 临时处置（本任务自决、已实现）：按 chipyard + 规格完成 QEMU 侧，三平台项记「未满足（跨模块）」。
2. **spec/合约措辞冲突（需 spec 侧澄清）**：`SimRISC-00 §2.3.1` 写语义（只更新 `[33:32]`/`[4:0]`）与 `SimRISC-01 §存取RF寄存器` 注 / `contract-fp §1` 的「`ld.t`/`ldm.t` 的 `[63:32]` **不变**」字面冲突：tetra 装入按既有语义**符号扩展**到 64 位（`ld.t ← 0xFFFF_FFFF` 的写数据是 `0xFFFF_FFFF_FFFF_FFFF`），施加写掩码后 `[33:32]=3`（chipyard 实测如此，任务书验收 #1「`[33:32]` 为写入值」亦如此）。
   - 建议把该注改为：「只读位 `[63:51]`/`[31:22]` 不变；`[33:32]`/`[4:0]` 取 64 位写数据（tetra 装入按符号扩展后的值）」。
   - 临时处置（本任务自决、已实现）：按「写掩码 + 符号扩展写数据」实现（= chipyard = 验收 #1）。若裁定相反（`[33:32]` 保持原值），QEMU 侧需改回窄掩码，且 chipyard 也要改。

## 完成区

**测试结果**：一键证据脚本（运行期证据目录）`run.sh` → **PASS=49 FAIL=0**、**rc=0**；`--no-node`/`--no-inject` 可选。逐项真实输出见下。
**修改文件**：`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`（`make_patch.py qemu`：1 written / 65 unchanged）、`components/qemu/changelog.md`（M13 一条）、本任务书；与 `git status --porcelain -uall` **三条逐条一致**。组件源树收敛为 base+1 单提交、clean（不入本仓库）。
**验收结果**：
1. **探针（QEMU 安装根）**：tetra 9 点/72 B、octa 3 点/24 B，输出字节序列 == 探针内联 spec 期望（现场导出、逐字节比）。`ld.t rf0 ← 0xFFFF_FFFF` ⇒ `0x7FF8_0003_7FC0_001F`（`[63:51]`/`[31:22]` 保持 qNaN 图样、`[33:32]=3`、`[4:0]=0x1F`）；`ld.t ← 0x7FFF_FFFF` ⇒ `0x7FF8_0000_7FC0_001F`；`ld.t ← 0` ⇒ 可写域清零 `0x7FF8_0000_7FC0_0000`；`ld.o`/`rd2rf` 全 1/全 0 同上；`ldm.t {rf0:rf1}` 元素 0 同掩码。
2. **改前/改后对比**：改前二进制（md5 `389ffb96…`）tetra 红 @ 第 2 点（旧代码写整低 32 ⇒ `0x7FF8_0000_FFFF_FFFF`）、octa 全绿 ⇒ 缺陷**只在 tetra 路径**；改后全绿。
3. **三平台（评测节点）**：chipyard == 改后 QEMU **逐字节一致**（tetra md5 `a06b14d6…`、octa md5 `59b4e105…`）；gem5 tetra 红 @2（其 `writeFloatLow32()` 覆盖 `[31:22]`）、octa 绿 ⇒ 见「待裁定」1（验收 #2 未满足，跨模块）。
4. **`check-inst` rc=2**：Vast `1141 total / 1135 passed / 1 failed / 5 deferred / 0 errors`；红集**恰** `divrem.yaml[23]`（既有 pin，未扩大）。
5. **273 例 sweep**：md5 `2d4d9465…` 不变、`covered=273`（现场）。
6. **门控**：`check-patch-tree` qemu 子集 **0 问题**（整树问题全在 gem5/chipyard/llvm/linux 的在飞改动）；`--source-state` qemu **OK**（base+1、clean）；`check-component-changelog` rc=0；`check_qemu_trans` **264/264**。
7. **可达 FAIL 注入（2 路）**：A 恢复 rf0 tetra 旁路 ⇒ tetra 红@2、octa 绿；B 关掉 `RF0_WRITE_MASK` ⇒ tetra 红@2、octa 红@1。均 `cp`+md5+`touch` 还原 ⇒ 重建二进制 md5 回 `9837631c…`、探针回绿、组件源树 clean（未用 git 还原）。
8. **安装根一致性**：首末各一次 `install-host` rc=0，`md5(构建树)==md5(安装根)==9837631c…`。
**新发现/坑**：① 任务前提「模型（gem5）按 spec」不成立 —— gem5 只在 octa 路径合规，tetra 路径覆盖 `[31:22]`；② spec/合约「`ld.t`/`ldm.t` 的 `[63:32]` 不变」与符号扩展写数据下的 `[33:32]` 冲突（见「待裁定」2）；③ 非 rf0 的 `ld.t`/`ldm.t` 目的**高 32 位 spec 未规定**（chipyard/QEMU 符号扩展、gem5 零扩展）⇒ 不得进三平台判据（初版探针曾因此误红）；④ `__PRINT` 长度 0 会死循环（`br.nz` 递减到 −1），调试变体踩过一次；⑤ QEMU 二进制含源码 commit（`commit --amend` 后 md5 会变）⇒ 跨轮次不得钉死二进制 md5；⑥ `check-inst` 的 rc=2 是基线钉（`divrem.yaml[23]`），`m13-testcases-032` 收口后须同步放宽。
**遗留问题**：① 验收 #2（三平台逐字节一致）**未满足**：gem5 tetra 路径不合规（跨模块、本任务禁改，建议新立 gem5 任务）——证据脚本已钉住该缺口；② `check-inst` 余 1 红 `divrem.yaml[23]`（既有 pin，由 `m13-testcases-032` 收口）；③ spec/合约措辞待澄清（「[63:32] 不变」vs 符号扩展写数据的 `[33:32]`）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`trans_fp.c.inc` 全 diff（删 rf0 专用旁路 + 两处调用点）、导出补丁、changelog 条目、两份探针 `.S`、`run.sh`/`node-run.sh`。

- **写语义**：`store_rf()` 的 `new = (old & ~RF0_WRITE_MASK) | (val & RF0_WRITE_MASK)` 同时支持置位与清零（注入 A 之外的初版「只置位」实现被探针点 3 抓住，见 F2）；`RF0_WRITE_MASK` 未改（`[33:32]+[4:0]`），故只读域与 SBZ 恒不变。
- **路径覆盖**：写 rf0 的全部路径 = `ld.t`/`ldm.t`（本轮改）、`ld.o`/`ldm.o`/`rd2rf`/`set.w`（既有 `store_rf()`）、FP helper 的标志（`env->rf[0] |= flags & 0x1F`）；`grep -rn 'rf\\['` 现场核对无其它直写点。
- **边界**：tetra 符号扩展（`MO_BESL`）与 chipyard `memLdElem` 一致；`bit31=0` 时 `[33:32]` 取 0（清舍入模式）亦按写语义生效；非 rf0 目的行为不变。
- **防造假**：证据 49 项断言逐条有可达 FAIL 路径（两路注入分别走 tetra/掩码两条不同失败路径）；还原用 `cp`+md5+`touch`，未用 `git checkout/restore/stash`；计数（探针点数、镜像数、覆盖数）现场派生。
- **自审发现（均已处置）**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 初版把 tetra 的 rf0 掩码收窄为 `[4:0]`（`[33:32]` 保持原值）⇒ 与 chipyard 不一致、违反验收 #1「[33:32] 为写入值」 | ✅已修 | tetra 目的统一走 `store_rf()`（完整 `RF0_WRITE_MASK`） | 三平台 chipyard==QEMU 逐字节一致（tetra md5 `a06b14d6…`） |
| F2 初版掩码合并写成 `old | (val & mask)`（只置位不清零）⇒ `ld.t` 无法清标志 | ✅已修 | 改用 `store_rf()` 的「清掩码位再或」 | 探针点 3/4/5 绿 |
| F3 初版探针断言 `ldm.t` 非 rf0 元素的高 32 位 = 符号扩展值（spec 未规定，gem5 零扩展） | ✅已修 | 删该检查点，非 rf0 高半不进判据 | tetra 9 点、三平台可比 |
| F4 初版探针用 `__PRINT rb27,8`（`LOAD_ADDR` 只收立即数）与 `\\@` 标签 ⇒ 汇编失败 | ✅已修 | 改 `__PRINT WSCRATCH,8`、改普通标签/改落盘比较 | `llvm-mc` rc=0、9 点全绿 |
| F5 修复后 `store_rf_tetra_dst()` 与 `store_rf()` 无差别（死抽象） | ✅已修 | 删除包装，`ld.t`/`ldm.t` 调用点直接 `store_rf()` | 重新导出补丁；49/0 回绿 |

判决：无未修 finding（「待裁定」2 项属跨模块/规格措辞，非本任务可修）⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14）

**脚本审阅**：逐行审 `run.sh`/`node-run.sh`——每条 `ck/expect_rc` 均有可达 FAIL 路径（锚点 `assert count==1`、红集/覆盖数现场派生、字节比对双向），无恒真、无「两支写同一结果」；两路注入走不同失败路径（旁路 vs 掩码）；还原只用 `cp`+`md5`+`touch`，未用 `git checkout/restore/stash`；退出码捕获被检命令自身（无 `| tee` 吞码）。

**重跑记录（全部 reviewer 亲跑，不采信完成区）**
1. 证据脚本全量重跑 ×2：`bash .work/evidence/m13-qemu-007/run.sh` ⇒ 第 1 次 `summary: PASS=49 FAIL=0` / `RESULT: PASS`；第 2 次 `RUN_RC=0`、`PASS=49 FAIL=0`，两轮 `[PASS]` 集合 `diff` **完全一致**、`[FAIL]` 计数 0。
2. 改前 QEMU 复现：`xz -dc …/pre-change/qemu-system-dadao.xz` ⇒ md5 `389ffb969e503f291f8e1b7c718392d8`（= 钉值）；用它跑探针 `RC=1`、`rf0_ld_tetra.S rc=2`（首红@2）、`rf0_ld_octa.S rc=0` ⇒ 改前确红、缺陷只在 tetra 路径。
3. 三平台（server207）：`chipyard==QEMU` tetra md5 `a06b14d6d06afb17bed094a56208c6d4`、octa `59b4e10540c83217379f0ac6eea8f2e1`；gem5 tetra `rc=1`/`GEM5_EXIT_CODE=2`、octa `rc=0`；`node summary: PASS=8 FAIL=0`。reviewer 另独立 `xxd`/`md5sum` 本地 QEMU 输出得同一对 md5 ⇒ 与节点 chipyard 逐字节一致。
4. 门控（reviewer 亲跑/亲 grep）：`make check-inst` rc=2、红集恰 `FAIL divrem.yaml[23]`、`Results: 1141 total / 1135 passed / 1 failed / 5 deferred`；`inst_sweep` md5 `2d4d94651346ef673c5a855e024c1489`、`covered=273`；`check_qemu_trans` `264/264` rc=0；`check_patch_tree.py` qemu 段 `assertion` 命中 0（`qemu: 66 patch(es)`）、`--source-state: qemu: OK`；`check_component_changelog` rc=0。
5. **reviewer 独立注入 1 路（自设计，非脚本 A/B）**：`RF0_WRITE_MASK 0x000000030000001F → 0x000000020000001F`（只去 bit32）⇒ `make build-qemu` rc=0、二进制 `53b6102a…` ⇒ 探针 `RC=1`、tetra `rc=2`（红@2）/ octa `rc=1`；`cp` 还原 ⇒ md5 `96b8dff4ce5b3a02cbe8df779f46447a` 相等、`REVIEW-INJECT` grep 无命中、`git -C .work/source/qemu status` 空 ⇒ 重建 rc=0、二进制回 `9837631c…`、探针回绿（tetra 72B / octa 24B、rc=0）。
6. 快照对账：任务 worktree `git status --porcelain -uall` 审前/审后均**空**、逐行 diff 一致；qemu 源树 clean；构建树 == 安装根 `9837631c15667cd1822ff9c20986a3f0`。

**约束核验**：① 未改主工作树（主树期间被他会话提交 `75e51896/419dd67d/11bf417b`，与本任务无关，如实记录）；② 未提交 git；③ 完成区 13 行 ≤30、各数字与我重跑逐条一致；④ 越界检查：产出提交 `cc073035` 恰 3 文件（任务书 / `changelog.md` / `trans_fp.c.inc.patch`），补丁 diff 仅删 `store_rf_tetra_dst()` 旁路 + `ld.t`/`ldm.t` 两处调用点改走 `store_rf()`，与任务书范围一致；⑤ 任务书无运行期绝对路径（grep `/tmp|/mnt|~/|.work/` 无命中）。

**待裁定核对**：① gem5 缺口已由主会话立 `.tao/tasks/gem5/m13-gem5-013`（`待开始`），且 `src/arch/dadao/inst.cc:185 writeFloatLow32()` 确写整低 32 位、`writeFcsr()` 有掩码 ⇒ 与「tetra 红@2 / octa 绿」自洽，本任务不修；② `SimRISC-00 §2.3.1`（只读 `[63:51]`/`[31:22]`、写只更新 `[33:32]`/`[4:0]`）与 `SimRISC-01` 注 / `contract-fp §1`「`[63:32]` 不变」的冲突已在 `discussing.md` 登记；本任务实现 = masked write = chipyard = 验收 #1，与「以 masked write 为准」的临时口径一致。

**非阻断 finding（交 architect 收尾改）**：`m13-gem5-013` 依赖栏写「`m13-qemu-007`（已合入）」，实际 `cc073035` 尚未进 master（`merge-base --is-ancestor` 否）⇒ 措辞笔误，合入后改。

**判决：Accepted**（验收 #2 未满足属已登记、已立册的跨模块缺口，不阻断本任务；最终接受仍归 architect）。

