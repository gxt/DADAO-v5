# m13-chipyard-001: 单精写入宽度（`ld.t`/`ldm.t` 不扩展 + ft 结果只写低 32 位）

**模块**：chipyard
**项目里程碑**：M13
**依赖**：无（spec 已裁定并落文：`SimRISC-01 §4` 注 + `SimRISC-07` 单精写宽 + `contract-fp §1`）
**可并行分片**：否（chipyard 组件单写者）
**预估**：3–5 h（含 Verilator 重建；开工前申报）
**状态**：已验证

## 背景（用户 2026-11-14 裁定）

`SimRISC-00 §2.3.1` 的 FCSR 写语义是正确口径，其余按它修订。裁定要点：

1. **`ld.t`/`ldm.t` 只写目的寄存器低 32 位，高 32 位保持原值**（不符号扩展、不零填）；
2. 写入 `rf0` 时，低 32 位里位于可写域的只有 `[4:0]`（异常状态）⇒ `[33:32]`/`[31:22]`/`[21:5]` **全部保持原值**；
3. **凡产生 ft（单精）结果的指令，只写低 32 位、高 32 位保持原值**；`ft2ft` 只搬低 32 位；`fo2fo`/`rd2rf`/`rf2rd` 按整 64 位逐位复制，不受此限。

chipyard 现状（`m13-qemu-007` 实测）：`ld.t` 的写数据是**符号扩展**到 64 位（`MO_BESL` 同源语义），`WumingRegFile.writeRf` 对 `idx≠0` 写整个 64 位 ⇒ `ld.t rf0 ← 0xFFFF_FFFF` 得 `0x7FF8_0003_7FC0_001F`（`[33:32]` 被改成 `11`）。按新裁定应为 `0x7FF8_0000_7FC0_001F`（只有 `[4:0]` 被写）。

## 目标

1. `ld.t`/`ldm.t` 的 32 位数据**不扩展**：只写 `rf[idx][31:0]`，`[63:32]` 保持原值。
2. 其余产生 ft 结果的指令（算术/取余/开方/取整/缩放/最小最大/转换到 ft）同样**只写低 32 位**；实现方式自选（如把 ft 结果的写使能改为按半字写），但必须**逐条列出你改了哪些指令族**并给证据。
3. **`ft2ft` 也按本裁定改**：只搬低 32 位、目的高 32 位保持原值（不再是 64 位二进制搬移）。`fo2fo`、跨组复制 `rd2rf`/`rf2rd`、`ld.o`/`ldm.o` 等 64 位通路**行为不变**。

## 验收

1. **探针（三平台同一 ELF）**：
   - `ld.t rf0 ← 0xFFFF_FFFF` ⇒ `0x7FF8_0000_7FC0_001F`（`[33:32]` 保持、`[4:0]` 被写）；
   - `ld.t rf5 ← 0xFFFF_FFFF` 后 `rf2rd rdX, rf5` ⇒ 高 32 位 == 写前 `rf5` 的高 32 位（先 `rd2rf rf5, rdY` 填入已知图案再验）；
   - `ld.t ← 0x7FFF_FFFF`、`ld.t ← 0`、`ldm.t {rf0:rf1}` 各一例；
   - `ftadd`（产生 ft 结果）后 `rf2rd` 验高 32 位保持；
   - `ft2ft` 只搬低 32 位：目的高 32 位保持写前值（反向对照：`fo2fo`/`rd2rf`/`rf2rd` 仍 64 位不变）。
2. **回归**：`01-load-store`、`05-arith-addr`、`06-control-flow`、`07-floating-point` 四册三平台全绿（数值与改前一致；高 32 位相关检查点按新口径更新）。
3. **RTL 单元台/仿真**：`tools/chipyard/fp_*`、`tools/chipyard/fp_unit/` 的既有断言全绿；如有「ft 结果高半」相关旧期望，按新口径修并说明。
4. 门控：`check_patch_tree` chipyard 段 0 问题、`--source-state` chipyard OK（base+1）、`check-component-changelog`、`check-index-blobs`。
5. **≥2 路注入可达 FAIL** + `cp`+md5 还原（例：恢复符号扩展 ⇒ 探针第 1 点红；把 ft 结果改回写全 64 ⇒ 高半检查点红）。
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前 `git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 不提交 git；补丁 `make_patch.py chipyard` 导出。
3. **chipyard 构建后必须删 `.classpath_cache/chipyard.jar` 与 `generated-src/<cfg>` 再 `make verilog`**，否则静默沿用旧固件/RTL（`m12-chipyard-028` 踩过）；判「新 RTL 真进模拟器」要独立解析产物（如 `TLROM.sv`/`Wuming*` 生成物）而非只看 `make` rc。
4. 完成区与真实输出逐条对齐；计数现场统计；日志 `<运行期日志目录>`。
5. 禁 `git checkout/restore/stash`/`git show <commit>:<path>`；注入还原用 `cp`+md5。
6. 三平台对比在节点（`server207`/`server208`）；节点 chipyard sim 需与主控机一致（`ISS-429`），无 JDK 不能自建 ⇒ 同步主控机构建产物。
7. 大文件落 `/tmp/opencode/m13-chipyard-001/` 并测完即删。

## 待裁定

无。用户 2026-11-14 的裁定已落 spec（`SimRISC-01 §4` 注 / `SimRISC-07 §1.3` / `contract-fp §1`），实现按裁定执行，无新增待裁定项。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-14）

逐行审查 `WumingRegFile`/`WumingDecoder`/`WumingCore`/`WumingFP`（FCSR）/`WumingFPUnitHarness` 的改动与 `fp_sweep.py` 的组/期望；判决：**可标「待验收」**（findings 全部已修或已归属，复验见右列）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 共用分支上 `ft2ft` 仍是 64 位拷贝（旧工具期望），与裁定 4 抵触 | ✅已修 | `fpCopy(isFo: Boolean)`：`ft2ft` 走 `fpCopy(false)`（`w0Ft` 置位，只搬低 32）、`fo2fo` 走 `fpCopy(true)`；`ftwidth_ft2ft_*` 与 `cvt_ff` 的 ft2ft 期望改为「目的高半保持」 | `ftwidth` 29/29、`cvt_ff` 27/27 逐字节；注入 3（`ft2ft` 改回 64 位）⇒ 恰 2 例红、其余 27 例绿 |
| F2 `fp_sweep` 的 `DATA` 在 `ENTRY+0x2000`：组代码长过 4 KiB 时运行期 seed 写坏程序尾部（展开的 `SYS_WRITEC` 循环）⇒ 镜像空转到 `+max-cycles`、输出暴涨 | ✅已修 | `DATA → ENTRY+0x30000`；`build_group` 把 print/exit 尾部计入长度并断言「镜像不得触到 DATA」 | 修前 29 例镜像 rc=124、输出 54 850 B；修后 264 B 逐字节；把 `DATA` 临时改回 `+0x2000` 跑 emit ⇒ **rc=1** 且打印 `program image (8756 B) would overlap the scratch DATA area`（可达 FAIL 实测） |
| F3 只去掉 `ld.t` 的符号扩展不够：不置 `w0Ft` 时整 64 位仍被写 | ✅已修 | `singleMem`/`multiMem` 对「RF 银行 + tetra 装载」与 `signed=false` **成对**置 `w0Ft` | 注入 2（还原符号扩展并去掉该 `w0Ft`）⇒ `ld.t` 4 例红、算术族 17 例仍绿 |
| F4 ft 目的寄存器若在同一镜像里被前一个 fo 用例整 64 位写过，旧的零扩展期望会随新写宽失效 | ✅已修 | `sign`/`sign_flags`/`divrem_special`/`divrem_nan`/`rnd_*` 的 ft 目的先 `load_rf(dst, 0)`；`ftwidth` 每例先 seed 非零高半 | 全量 sweep 51 组 **2243 例**逐字节一致 |
| F5 证据脚本首轮 A 段红：`ft2ft`/`DATA` 两处断言锚点跨行、字面量不连续 | ✅已修 | 断言改单行/连续子串（`scratch DATA area at +0x`、`fpCopy(false) }  // ft2ft`） | 证据脚本完整重跑（见完成区 `PASS/FAIL`） |
| F6 QEMU/gem5 探针各 2 格差异是否属本任务缺陷 | ❌不修（跨组件，已立案） | 只记录并归属：QEMU 的 `ftsgnj/ftsgnn` 仍走 `store_rf`（整 64 位）⇒ 归 `m13-qemu-013`；gem5 的 `ld.t/ldm.t → rf0` 未过 FCSR 掩码（覆盖只读 qNaN/SBZ）⇒ 已有 `m13-gem5-013` | 探针逐例差异见完成区「遗留问题」；chipyard 侧 29/29 |

### 第 1 轮 reviewer 验收（2026-11-14）

**判决：Accepted**（4 条 findings 均非阻断；跨组件红点按归属登记）。逐条原始输出：`<运行期日志目录>`、`<运行期日志目录>`、运行期临时目录的 `{sweep-run,inject-run}.log` 与 `revft*.check`。

**重跑记录（reviewer 亲自执行 → 命令 / 真实输出 / 退出码）**

1. **独立强制重建**（先删 `.classpath_cache/chipyard.jar` 与 `generated-src/<cfg>`）：`make verilog CONFIG=WumingTinyConfig -j32 && make CONFIG=WumingTinyConfig -j32` ⇒ `ELAB_EXIT=0 / SIM_EXIT=0`（11:22:15→11:23:56），sim md5 `45748f3f0f9269f9bb99eac47fec48fa`。**生成物现场解析（非只看 rc）**：`WumingRegFile.sv:422 _GEN_80 = io_w0Ft ? {_GEN_1[io_w0Idx][63:32], io_w0Data[31:0]} : io_w0Data`、`:3330 .io_writeFlagsOnly (w0Fcsr & io_w0Ft)`；`WumingFcsr.sv:65 if (io_writeEn & ~io_writeFlagsOnly)`；`WumingCore.sv:2203 .io_w0Ft(_dec_io_dec_w0Ft)`；`WumingDecoder.sv:426 assign io_dec_w0Ft = _GEN_…`（68 条源行引用）。
2. **独立探针**（自写 `rev-probe.py`，35 例，期望逐条按 spec 现场推导）：sim rc=0、`cases=35 mismatch=0`——`ld.t rf0←0xFFFFFFFF ⇒ 0x7ff800037fc0001f`（mode=3 保持、flags=0x1f）、`ld.t rf5 ⇒ 0x123456780000001f / 0xfedcba9880000000 / 0x7654321000000000`、`ldm.t {rf0:rf1} ⇒ 0x7ff800037fc00004 + 0xaaaabbbb55667788`、ftadd/sub/mul/div/rem/fma/root/rnd/sclb/min/max/it2ft/ut2ft/io2ft/fo2ft/ftsgnj/ftsgnn 高半保持、`ft2ft` 单例+三元素块只搬低 32、反向 `fo2fo/rd2rf/rf2rd/ld.o/ldm.o/ft2fo/fosgnj/fosgnn` 整 64、`ftsgnj 取 bit31` 与 `fosgnj 取 bit63` 判别例。
3. **证据脚本重跑** `bash <运行期证据目录>` ⇒ `summary: PASS=57 FAIL=3`、`RUNSH_EXIT=1`；3 红均为 `PermissionError …/.work/source/gem5/build/DADAO/gem5.opt`（并行 `m16-gem5-008` 正在 scons 重建，现场 `ls -l` 当时无 x 位）⇒ 环境干扰，**重试 1/3**：`01 235/235 RC=0`、`06 34/34 RC=0`、`07 38/38 RC=0`（07 用 `inst-tiny-fp.lds`），`05 12/12` 首轮即绿 ⇒ 四册三平台全绿。
4. **`run.sh --self-test-inject`** ⇒ `injection summary: PASS=19 FAIL=0`、`SELF_INJECT_PIPE_RC=0`（inj1 23 例红 / inj2 4 例红且算术族仍绿 / inj3 恰 `ft2ft` 2 例红；三次 `restore md5 matched` + `source tree clean=0` + 还原 byte-exact）。
5. **独立注入（自设计，非其 3 路）**：仅把 `WumingFcsr` 的 `when(!io.writeFlagsOnly) { modeReg := … }` 改为 `when(true.B)`（`cp` 备份 md5 `4b5d3e18…`→`ff137870…`），删 jar + generated-src 重建 `0/0`、生成物中 `~io_writeFlagsOnly` 计数 0 ⇒ 探针 `check_rc=1`、**恰 2 例红**：`rev_ldt_rf0_mode_kept got=7ff800007fc0001f want=7ff800037fc0001f`、`rev_ldmt_rf0_rf1 got=…0004 want=…37fc00004`，其余 33 例绿；`cp` 还原 md5 相等、重建 `0/0`、`cases=35 mismatch=0` 回绿，组件树 `git status` 0 行。
6. **全量回归**（自跑）：`semantic groups: pass=51 fail=0 total=51`、`fault images: pass=58 fail=0 total=58`、`SWEEP_EXIT=0`（2243 语义例逐字节 + 58 个 cause）；`fp_ref` 三自检 `0 mismatches`（RC=0）；RTL 单元台 `TOTAL failed=0`、`spec points (m12-030) vectors=20 failed=0`、45 个 op 组全 `failed=0`。
7. **门控**：`check-patch-tree` RC=2 但 chipyard 段仅 `21 patch(es)`、0 problem（15 个 problem 全在 qemu/gem5 在途）；`check-source-state` RC=0（`chipyard: OK HEAD=cc98c2dc count=1 clean`）；`check-component-changelog` RC=0；`check-index-blobs` RC=0；`apply-series` 21 补丁 / 二次 0 写入 / 树 hash `25d51e7c…` 一致；L2 `check-modules` `L2_EXIT=2`，唯一红 `diff_ir_lli: FAIL (structural)`（`tests/unit/llvm/lit/CodeGen/DADAO/stack-protector*.ll` 未分类，llvm 既有），`check-inst-smoke`/`check-arch-smoke`/`check-install-tools`/`check-cfx-alias-install` 均 PASS。
8. **DATA 断言可达 FAIL**（自验）：`ftwidth image = 8664 B`；把 `DATA` 改回 `ENTRY+0x2000` ⇒ `SystemExit: program image (8664 B) would overlap the scratch DATA area at +0x2000`（emit rc=1），恢复即绿。

**约束核验**：9 项修改文件与 commit、`git status --porcelain -uall`（空）逐项一致；交付文件 md5 首/尾两次快照 `diff ⇒ MD5_SNAPSHOT_MATCH_OK`；完成区 16 行（≤30）；未提交 git；未动 `tests/`、`spec/`、`contracts/`；还原一律 `cp`+md5（未用 checkout/restore/stash）；未跑 `install-host`；临时产物在运行期临时目录。

**findings（非阻断，交 architect）**：

- F1 任务书 §验收1「复制类 `ft2ft` 64 位二进制不变（反向证据）」与 `spec/SimRISC-07 §1.3` + 用户 2026-11-14 裁定（`ft2ft` 只搬低 32）冲突；实现按 spec 正确，需订正任务书该行。
- F2 证据脚本对 `WumingFcsr.writeFlagsOnly` 只有文本断言、无行为覆盖（其 `ftwidth`/`rf0ldt` 用例 mode 恒 0，守卫失效也绿）⇒ 已由 reviewer 探针 + 注入补验；建议 `ftwidth` 增「mode≠0 + `ld.t rf0`」一例。
- F3 完成区「`check-patch-tree` 全局 6 条」与我实测 `15 problem(s)` 不符（在途组件数随时间变，chipyard 段仍 0）；F4 首轮三册红为并发 gem5 重建（环境），重试 1/3 全绿。
- 遗留：gem5 探针 `2/29` 红（`ftwidth_ldt_rf0_ffffffff`、`ftwidth_ldmt_rf0_rf1`）归 `m13-gem5-013`（待开始）；QEMU 探针本轮 `0/29`（`m13-qemu-013` 已合入）。

## 完成区

**测试结果**：通过 60/60 + 注入 19/19（证据脚本 `run.sh` → `PASS=60 FAIL=0` `EXIT=0`；`run.sh --self-test-inject` → `PASS=19 FAIL=0` `EXIT=0`）；失败原因：无。另：L2 `make check-modules` rc=2，红点是 `check-unit`/`ir-lli` 的结构扫描（`m14-llvm-002` 已合入的两个 `*.ll` 未分类），属 llvm 既有红、非本任务；已跑到 `check-inst-smoke`/`check-arch-smoke`/`check-install-tools`/`check-cfx-alias-install` 全 PASS。

**修改文件**（与 `git status -uall` 逐项一致，9 项）：① 5 份补丁 `…/{WumingCore,WumingDecoder,WumingFP,WumingFPUnitHarness,WumingRegFile}.scala.patch`（`make_patch.py chipyard`：5 written / 16 unchanged）；② `components/chipyard/README.md`（新节「单精写入宽度」+ 两处旧表述订正）；③ `components/chipyard/changelog.md`（M13 一条）；④ `tools/chipyard/fp_sweep.py`；⑤ 本任务书。证据脚本与 `probe_diff.py` 落运行期证据目录（不入 git）。组件源 HEAD=`cc98c2d`（base+1、clean）。

**验收结果**：
- **ft 目的指令族逐条**（均改为只写 `[31:0]`）：`ld.t`/`ldm.t`（同时去掉符号扩展）、`ftadd/ftsub/ftmul`、`ftfma`、`ftdiv/ftrem/ftroot`、`ftrnd`、`ftsclb`、`ftmin/ftmax`、`it2ft/io2ft/ut2ft/uo2ft`、`fo2ft`、`ftsgnj/ftsgnn`、`ft2ft`；**64 位不变**：`fo2fo`、`rd2rf`/`rf2rd`、`ld.o`/`ldm.o`、`ft2fo`（`ftcls` 写 rd，不涉）。
- **探针真实值**（chipyard，`ftwidth` 29/29 逐字节）：`ld.t rf0←0xFFFF_FFFF` ⇒ `0x7FF8_0000_7FC0_001F`（旧 `…_0003_…`）；`ld.t rf5` ⇒ `0xDEADBEEF_FFFFFFFF` / `0xDEADBEEF_7FFFFFFF` / `0xDEADBEEF_00000000`；`ldm.t {rf0:rf1}` ⇒ `0x7FF8_0000_7FC0_001F` / `0xCAFEBABE_00000000`；`ftadd` ⇒ `0xDEADBEEF_40400000`；`ft2ft` 单例/块 ⇒ 高半 `0x11111111`/`0x22222222`/`0x33333333` 保持；`fo2fo`/`rf2rd` ⇒ `0xDEADBEEF_CAFEBABE`、`rd2rf`/`ld.o` ⇒ `0x0123456789ABCDEF`。旧实现同一镜像 24/29 红（5 个 64 位反向对照绿）。
- **生成物独立核验**：`WumingRegFile.sv` 有 `io_w0Ft ? {_GEN_1[io_w0Idx][63:32], io_w0Data[31:0]} : io_w0Data`；`WumingFcsr.sv` 有 `if (io_writeEn & ~io_writeFlagsOnly)`；`WumingCore.sv` 的 `_dec_io_dec_w0Ft` 接线、`WumingDecoder.sv` 的 `io_dec_w0Ft` 为解码 mux（68 条源行引用）；模拟器新于 Scala 源与生成物。
- **回归**：四册三平台全绿——`01` 235/235、`05` 12/12、`06` 34/34、`07` 38/38（`07` 用 `inst-tiny-fp.lds`）；RTL 单元台 `TOTAL failed=0`（45 组 + spec points 20/20，各 op oracle/hf 差 0）；另跑全量 `fp_sweep` 51 组 **2243 例**逐字节一致 + 58 个合法性镜像 cause 全命中；`fp_ref` 三自检 0 mismatch。
- **门控**：`check-patch-tree` chipyard 段 0 问题（全局 6 条 = 并行 qemu/gem5 在途）、`check-source-state` chipyard+testchipip OK、`check-component-changelog`/`check-index-blobs` rc=0、`apply-series` 幂等（21 补丁 / 二次 0 写入 / 树 hash 不变）。

**新发现/坑**：① `fp_sweep` 的 `DATA` 原在 `ENTRY+0x2000`，组代码长过 4 KiB 时运行期 seed 写坏程序尾部 `SYS_WRITEC` 循环（本任务 29 例组已越过）⇒ 改为 `ENTRY+0x30000` + `build_group` 断言（可达 FAIL 实测：8756 B 镜像在 `+0x2000` 下 rc=1）；② `07-floating-point` 必须用 `--lds tests/inst/07-floating-point/inst-tiny-fp.lds`，用默认 lds 时故障镜像跳到镜像外、每个烧满 20M 拍；③ QEMU 的 `ftsgnj/ftsgnn` 仍走 `store_rf`（整 64 位）⇒ 探针 2 格红，归 `m13-qemu-013`；④ gem5 的 `ld.t/ldm.t→rf0` 未过 FCSR 掩码（把整低 32 写进 rf0、覆盖只读 qNaN/SBZ）⇒ 探针 2 格红，已有 `m13-gem5-013`；⑤ `ft2ft` 按「只搬低 32 位」实现（用户 2026-11-14 裁定，旧 spec 曾按 64 位）。

**遗留问题**：三平台探针一致性待 `m13-qemu-013`（sign 2 格）+ `m13-gem5-013`（rf0 掩码 2 格）合入后复验（chipyard 29/29 已绿）；L2 见上（llvm 既有红）。
