# m13-gem5-013: `ld.t rf0` 的只读位（gem5 侧）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-qemu-007`（已合入，QEMU 侧口径已定）；与 `m16-gem5-*` 串行（组件单写者）
**可并行分片**：否
**预估**：2–3 h
**状态**：已验证

## 背景（实测）

`m13-qemu-007` 的三平台探针显示：**gem5 的 tetra 装入路径覆盖 `rf0[31:22]`（只读位）**——
`ld.t rf0 ← 0xFFFF_FFFF` 得 `0x7FF8_0000_FFFF_FFFF`（chipyard/QEMU 为 `0x7FF8_0003_7FC0_001F`）；
octa 路径（`ld.o rf0`）在 gem5 上正确 ⇒ 缺口只在 tetra。

## 范围补充（用户 2026-11-14 裁定后）

- **`ld.t`/`ldm.t` 只写低 32 位、高 32 位保持原值**（gem5 的 `writeFloatLow32` 已是此行为，**不要改成符号扩展**）；`rf0` 仍须经 FCSR 写掩码（只放行 `[33:32]`+`[4:0]`），低 32 位里只有 `[4:0]` 真正生效。
- **凡产生 ft 结果的指令只写低 32 位**：请现场核查 gem5 的 ft 算术/取余/开方/取整/缩放/最小最大/转换到 ft 路径是否都只写低 32 位（若是，给证据；若否，按裁定改并列出）。
- **`ft2ft` 也须改为只搬低 32 位、目的高 32 位保持原值**；`fo2fo` 与跨组复制 `rd2rf`/`rf2rd` 仍是 64 位二进制搬移，不得改。
- 探针须覆盖：`ld.t rf0 ← 0xFFFF_FFFF` ⇒ `0x7FF8_0000_7FC0_001F`；`ld.t rf5` 后 `rf2rd` 高半保持；`ftadd` 后高半保持；**`ft2ft` 只搬低 32 位**（目的高半保持）；`fo2fo`/`rd2rf` 仍 64 位不变（反向）。

## 范围

- `src/arch/dadao/**` 里 `ld.t`/`ldm.t` 目的为 `rf0` 的写入路径：改为经 FCSR 写掩码（只放行 `[33:32]` 与 `[4:0]`，`[63:51]`/`[31:22]` 保持、SBZ `[21:5]` 忽略），与 QEMU 的 `RF0_WRITE_MASK` 同口径。
- 不改其它 FP 写路径；不改 spec/契约。

## 验收

1. tetra 探针 9 点与 chipyard/QEMU **逐字节一致**（`ld.t rf0 ← 0xFFFF_FFFF` ⇒ `0x7FF8_0003_7FC0_001F`）；octa 3 点不变。
2. `check_b7`/`check-gem5-decode`/`check-component-changelog` rc=0；`check-patch-tree` gem5 段 0 问题。
3. ≥2 路注入可达 FAIL + `cp`+md5 还原。
4. 安装根 == 构建树（gem5 为源码构建，无 install 根则豁免，写清）。
5. 完成区 ≤30 行；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 worktree；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git；组件补丁 `make_patch.py gem5` 导出。
3. 完成区与真实输出逐条对齐；计数现场统计。
4. 需裁定写「待裁定」返回。
5. 禁 `git checkout/restore/stash`；用 `cp`+md5。

## 待裁定

1. **QEMU 跨模块缺口（建议当面立任务，非本任务范围）**：`ld.t`/`ldm.t` 写 `rf0` 时 QEMU **清掉** `[33:32]`（`store_rf_tetra()` 把零扩展的 64 位值交给 `RF0_WRITE_MASK`），与 `spec/SimRISC-01 §ld.t` 注「`[33:32]` 不在写入宽度内 ⇒ 保持原值」及 chipyard/改后 gem5 不一致。
   - 实测：本任务探针 `rf0_write_mask.S` 第 4 / 8 点 QEMU 红（rc=4）；把这两点期望改成「模式被清 0」后 QEMU 9 点全绿（值见证探针）⇒ QEMU 实际值为 `0x7FF8_0000_7FC0_0000` / `0x7FF8_0000_7FC0_001F`。
   - 既有探针（`ld.t`/ft 写入宽度两册、`m13-qemu-013` 的 29 点）都不含「模式非零后再做 tetra rf0 写」场景，故此前三平台绿未暴露。
   - 建议：立 QEMU 任务，令 rf0 的 tetra 写只落 `[4:0]`（`[33:32]` 保持）；本任务不擅自改 QEMU。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

改动面：`inst.cc` 的 `writeFloatLow32`（新增 `idx == 0` 分支，`~lowMask` 为 uint64 ⇒ 保留 `[63:5]`，`uint64_t(val) & 0x1F` 取低 5 位，读旧值先于写）、`b1_test.cc` 的桩（同步掩码）与两条 `rf0` 断言（写前塞 `[31:22]` qNaN 图样 + `[21:5]` 非零 + 模式 3，断言 `0xF0F0F0F3FFF00018`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 只修 `ld.t`/`ldm.t` 调用点会漏掉 b7 的 ft 结果路径 | ❌不修（已覆盖） | 掩码放在两条路径共用的 `writeFloatLow32` 里 | `grep` 生产调用点仅 `b1.cc:171`/`b7.cc:279`，均经该口 |
| F2 原断言只验高半保持，低半 `[31:5]` 是否被覆盖不可见 | ✅已修 | 两条断言改为塞满 `[31:22]` qNaN 图样 + SBZ 位并断言 `0xF0F0F0F3FFF00018` | 注入 A 下该两例可达 FAIL（探针 cp2 红）；`check_b1` 2156 断言 0 失败 |
| F3 是否 `writeFloat64` 也需掩码（b7 `cs.*-rf` 用它写目的） | ❌不修 | 未改 | B7 目的 `rf0` 一律带 `dst_rf0` 合法性 ⇒ ILLI；`writeFloat64` 无可达的 `idx==0` 路径 |
| F4 b5/b6/b7 测试桩的 `writeFloatLow32` 未加掩码 | ❌不修 | 未改 | 同上：无可达 `rf0` 目的；b7 参考模型差分 4098 向量 mismatch=0 |
| F5 任务书验收 #1 的 `0x7FF8_0003_7FC0_001F` 与「范围补充」的 `0x7FF8_0000_7FC0_001F` 冲突 | ✅已修（按后出的口径） | 期望值按 spec `SimRISC-01 §ld.t` 注 + 范围补充取 `0x7FF8_0000_7FC0_001F`（chipyard 实测同值） | 本任务探针 cp2 三平台逐字节一致 |

**判决**：F1/F3/F4 为「无缺陷（已覆盖/不可达）」结论并附证据，F2/F5 已闭环；无未修 finding ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收

**判决：Accepted**（3 条非阻断 finding）。以下均为 reviewer 亲自执行的命令与真实输出，不采信完成区。

1. **spec 回核（自己推算，不采信其结论）**：`spec/SimRISC-01 §4 注`「`ld.t`/`ldm.t` 只写低 32 位、高 32 位保持原值；`[33:32]` 因不在写入宽度内同样保持原值」+ `SimRISC-00 §2.3.1`「写 `rf0` 只更新 `[33:32]`/`[4:0]`，其余保持」⇒ 在复位 `0x7FF80000_7FC00000` 上做 `ld.t rf0←0xFFFF_FFFF`：`(old & ~0x1F) | (val & 0x1F)` = **`0x7FF80000_7FC0001F`**。验收 #1 的 `0x…0003…` 是旧探针「模式已置 3」的取值，与本探针复位态（cp1 无任何置模式指令）不自洽；任务书「范围补充」行 21 亦已写 `0x…0000…`，且 chipyard 实测同值（见第 4 条）⇒ **取值判断正确，非擅改判定值**。
2. **改前正证**（重跑 `run.sh` stage0–2）：`pre-change gem5.opt md5=49e600e33621ac6af845a588f50abd3f` ✓；`--dump-mem` WSCRATCH 24 B = `7ff80000ffffffff0000…` ⇒ 覆盖只读 `[31:22]` 与 SBZ `[21:5]` ✓；ld.t 镜像 rc=2、rf0 镜像 rc=2、ft 镜像 rc=0 ✓。
3. **改后探针**：gem5 51 点全绿（cp2 = `7ff800007fc0001f`）；`ld.t rf5` 高半保持（ld.t 探针 cp5/6/7 = `aaaabbbb…/11112222…/33334444…`）、`ftadd`/`ft2ft` 等 29 点未受影响 ✓。
4. **三平台逐字节（按纠正派节点）**：目标节点 **server207**（派前 `remote.py status`：loadavg 0.16、mem_avail 125834 MB、disk_use 26%、`running=none`）；`sync_node_artifacts.sh server207` **PASS**（逐件 md5 校验 OK）。**并行度 62**，墙钟 **38 s**（18:33:38→18:34:16），rc=0、3/3 镜像。节点与主控机 md5 一致：gem5.opt `6e436d1bfe5935ed949491b509e63a29`、qemu `725c5da788cf4ca7ceba569221f9f1f6`、chipyard `ac35dffbc90cef736e5e0788cecb51d2`。输出 md5：`ld_t` 13 点 `4ba8734d3c716599f510538e3d0ff226`、ft 29 点 `6a345591eb284f317dcd5b65f7ac2416`、rf0 9 点 `5237c3bab66edf9e3c30f244764dcd7f`，**三平台逐字节相同**，与完成区一致。
5. **门控（`$?` 直取，不经管道）**：`check-gem5-decode` rc=0 / 694 PASS；`check-wuming-cycles` rc=0 / 11；`check_b1` rc=0（38/38、2156 断言）；`check_b3` rc=0（42/42）；`check_b7` rc=0（`oracle vectors=4098`、`oracle mismatch=0`）；`check_component_changelog` rc=0 PASS；`check_patch_tree` **gem5 段 0 问题**；`--source-state` gem5 `OK count=1 clean=True`；`ls .dadao/cross-toolchain/bin | grep gem5` 无命中 ⇒ 验收 #4「无安装根豁免」成立。
6. **独立注入（自设计，非其 A/B 两路）**：`inst.cc` 的 `lowMask 0x1F → 0x3F`（放行 `[5:0]`）→ `git diff` 非空 → `JOBS=32 make build-gem5` rc=0（139 s）→ 探针 **rc=1**、`ld_t` rc=2、`rf0` rc=2、ft 29 点仍绿（12 s）；`cp` 还原后 md5 `741a35bf685dd2c0eff9ce23f5af9fea` 与注入前**逐字节相同**、gem5 源树 clean → 重建 rc=0（118 s）→ 51 点回绿（11 s）。
7. **QEMU 跨模块缺口（独立实测）**：用**改前** QEMU（安装根 `b34ed7f99d8b1d90821f4b819eeb15c9`，mtime 15:01 早于修复）跑同一 ELF：rf0 探针 **rc=1（首个红点 cp4）**、ld.t/ft 绿；见证探针 **rc=0**、72 B = `7ff800007fc00000 … 7ff800007fc0001f …` ⇒ **改前 QEMU 的 `ld.t` 写 rf0 确实清掉 `[33:32]`**。master 侧 `components/qemu/patches/target/dadao/translate.c.patch` 的 `store_rf_tetra()` 把零扩展 64 位值交 `RF0_WRITE_MASK`（reviewer 读源核实）⇒ **缺口属实**；`m13-qemu-015` 任务已在册，共享树已含 `RF0_WRITE_MASK_TETRA`（现 QEMU `725c5da7…` 跑 rf0 探针 9 点全绿、见证反红 rc=4）⇒ **该缺口已被并行任务关闭，无需新立 QEMU 任务**。
8. **`run.sh` 重跑（1 次，8 m58 s）**：`summary: PASS=51 FAIL=10`、`RUNSH_EXIT=1`；10 条 FAIL **全部**为 `rc=75 writer-guard: REFUSED: a writer is active … component=qemu, target=build-qemu, pid=1868672`（m13-qemu-015 并发 `build-qemu` 触发的共享写者互斥），**无一条是数值不符**；stage0–3 / 7 / 8 / 9（含其两路注入的可达 FAIL、还原回绿、`741a35bf` 还原 md5）均 PASS。因该环境拦截，第 2–7 条改为逐条直跑复核（全部通过）；另 stage6 的 QEMU 缺口钉值在缺口被修后将恒红，见 F1。
9. **范围与快照**：`git diff --name-only master...HEAD` = 4 个文件（本任务书 + `components/gem5/changelog.md` + 2 份 gem5 补丁），**无** spec/contracts/tests/Makefile/台账/discussing；worktree `git status -uall` 审前/审后快照均 0 行且逐行相同，4 个目标文件 md5 前后一致；gem5 源树 clean；完成区 12 行 ≤30；未跑 `install-host`/`check-modules`/`build-chipyard`，`build-gem5` 前均 `pgrep` 确认无并发写者、`JOBS=32`、构建与测试未同时进行。

**Finding（均不阻断）**：F1 `run.sh` stage6 把「QEMU 清 `[33:32]`」钉成 PASS 判据，缺口被 `m13-qemu-015` 修掉后该脚本将永久红，建议改为观察性记录（不作断言）；F2 stage5 三处 `md5of` 比较在两文件同时缺失时 `"" == ""` **空转 PASS**（本轮实测出现 3 条 `expected= actual=`），建议补「文件非空」断言；F3 完成区「`check-patch-tree` 全局 rc=1 的 10 条全在 chipyard 段」现为 **14 条**（+4 条 qemu，来自并行任务改共享 `.work/source/qemu`），gem5 段仍 0 —— 属并发引起的文档数字漂移，收尾提交时改。

## 完成区

**测试结果**：一键证据脚本 `run.sh`（运行期证据目录；`--no-inject` 可选）**PASS=61 FAIL=0 rc=0**，含 4 次 SCons 重建、总墙钟 8m31s；逐项「检查名/期望/实际/rc」见运行期日志。
**修改文件**：`components/gem5/patches/src/arch/dadao/inst.cc.patch`、`components/gem5/patches/src/arch/dadao/exec/b1_test.cc.patch`（`make_patch.py gem5`：2 written / 104 unchanged）、`components/gem5/changelog.md`、本任务书；与 `git status --porcelain -uall` 逐条一致。组件源树收敛为 base+1 单提交、clean（不入本仓库）。
**验收结果**：
1. **改前正证**：改前二进制 md5 `49e600e3…`；`ld.t rf0 ← 0xFFFF_FFFF` 的 `st.o rf0` 落盘（用 gem5 `--dump-mem` 独立观测 WSCRATCH）为 **`0x7FF8_0000_FFFF_FFFF`**（覆盖只读 `[31:22]` 与 SBZ `[21:5]`）；ld.t 与 rf0 两镜像各红于第 2 检查点，ft 目的族 29 点全绿 ⇒ 缺陷只在 rf0 写路径。
2. **改后**：同一 ELF 三个探针 51 检查点全绿；`ld.t rf0 ← 0xFFFF_FFFF` ⇒ **`0x7FF8_0000_7FC0_001F`**（任务书验收 #1 的 `0x…0003…` 早于 2026-11-14 裁定，按「范围补充」+ `spec/SimRISC-01 §ld.t` 注取 `0x…0000…`，与 chipyard 一致）；「先 `set.w rf0 wp2=1` 再 `ld.t rf0 ← 0`」读回 `0x7FF8_0001_7FC0_0000`（`[33:32]` 不在写入宽度内 ⇒ 保持）；`ld.o rf0 ← 全 1` ⇒ `0x7FF8_0003_7FC0_001F`（octa 仍可写 `[33:32]`）；`ld.t rf5`/`ftadd`/`ft2ft` 高半保持，`ld.o`/`rd2rf`/`fo2fo` 仍整 64 位。
3. **三平台逐字节**：`ld.t` 13 点（104 B，md5 `4ba8734d…`）与 ft 目的族 29 点（232 B，md5 `6a345591…`）gem5==chipyard==QEMU==spec 期望；rf0 掩码探针 9 点 chipyard==gem5（md5 `5237c3ba…`）且 == spec 期望。QEMU 在该探针第 4/8 点红 ⇒「待裁定」1（既有两册探针不含该场景）。
4. **门控**：`check-gem5-decode` 694/694 rc=0、`check-wuming-cycles` 11/11 rc=0、`check_b7` 4098 向量 mismatch=0 rc=0、`check_b1` 38/38（2156 断言）、`check_b3` 42/42、`check_component_changelog` PASS；`check-patch-tree` gem5 段 **0 问题**（全局 rc=1 的 10 条全在 chipyard 段，属并行任务）；`--source-state` gem5 `OK count=1 clean=True`。gem5 为源码构建、无安装根 ⇒ 验收 #4 豁免。
5. **注入（2 路，均可达 FAIL）**：A 删掉 rf0 分支 ⇒ ld.t 红@2、rf0 红@2；B 掩码套在零扩展 64 位值上（QEMU 读法）⇒ rf0 红@4、ld.t 仍绿；两路注入前均验证 `git diff` 非空，`cp`+md5 还原（`741a35bf…` 逐字节回原）、重建后 51 点回绿、组件源树 clean。
**新发现/坑**：① `[33:32]` 是否保留是「写入宽度 vs 全 64 位掩码」的歧义点，只有「先置非零模式再做 tetra rf0 写」的用例能区分（探针 cp4/cp8 专为此设）；② 既有两册探针不含该场景 ⇒ 三平台绿不等于掩码读法一致；③ b5/b6/b7 测试桩的 `writeFloatLow32` 未加掩码：B7 目的 `rf0` 一律 `dst_rf0` ⇒ ILLI、b5/b6 不经该口写 rf0，故不改（已在 b1 桩同步掩码）。
**遗留问题**：本任务范围无；QEMU 跨模块缺口见「待裁定」1。
