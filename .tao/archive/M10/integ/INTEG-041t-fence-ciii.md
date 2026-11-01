# INTEG-041t: fence ciii 落地（编码/移册/汇编/测试）

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0044（fence ciii）
**状态**：已验证

## 背景

ADR-0044 已定：`fence` 改为 `ciii`，`opc=0x79`，`cfxha` 选择资源域，`hb=0`，`hc=pred`，`hd=succ`；`pred/succ` 为 cr/cw/ci/co/mr/mw 六位掩码；`cfx0`/`cfx_umon` 表示 all cfx；`immu18` 整体书写、不拆三段；删除 `fm`/TSO；从 SimRISC-12「其它指令」移到 SimRISC-11「核芯功能扩展指令」。旧 `fence 0` 不再接受。

## 目标

1. **spec/文档**
   - SimRISC-11：加入 `fence` 的编码/语义/pred-succ 表；
   - SimRISC-12：删除 `fence`，同步索引；
   - DADAO-12/Toolchain-01：汇编语法、`cfx0`/`cfx_umon`=all、`fence 0` 拒绝；
   - 删除 `fm`/TSO 描述；`hb`/保留位明确 SBZ。
2. **contracts**
   - `contracts/opcodes.yaml`：旧 fence 记录替换为 `opc=0x79`、`ciii`、`cfxha/hb/hc/hd`；更新 legality/spec_cite；
   - 相关 alias/索引/生成物同步。
3. **LLVM**
   - MC 编码/解码、汇编器语法：`fence cfx0, immu18` / `fence cfx_umon, immu18`；
   - 拒绝 `fence 0`；`immu18` 为单个 18 位表达式；
   - 补 lit（正例/负例：hb!=0、reserved cfx、旧语法拒绝、pred/succ 组合）。
4. **QEMU**
   - 若当前有 fence 解码/trans：更新到 0x79/ciii；语义按“本 hart、资源域顺序”实现或明确 no-op hint；
   - 不改 DMA/TLB/cache 维护语义。
5. **测试**
   - 汇编接受 `cfx0`/`cfx_umon`/具体 cfx；
   - `immu18` 位映射、零掩码 no-op；
   - `hb!=0`/reserved cfx → ILLI；
   - 旧 `fence 0` 汇编失败；
   - 不改变现有访存/异常测试。

## 验收

- `make check`、`make check-lit`、`check-spec-readonly`、`check-spec-changelog`、`check-patch-tree`、`check-source-state` rc=0；涉及 QEMU/LLVM 时补对应构建/定向测试。
- 证据 `.work/evidence/<任务号>/run.sh`：注入→FAIL→cp+md5 还原→PASS。
- 不改 `fence.vma`/`fence.i`/DMA 语义；不跑 full/夜跑。
- 完成区 ≤30 行；任务书与 `milestones.md` 置 `待验收`；临时 `/tmp/opencode/INTEG-041t/`。

## 约束

- 只做 ADR-0044 范围；不改 cfx 编号/cfx 权限。
- 不提交、不 push；重建先申报；失败保留现场。

## 完成区

**状态**：已验证

**测试结果**：`make check` rc=0；`check-modules` rc=0；`check-lit` 159/159；fence 向量 17/17；`run.sh` 12/12（含注入 FAIL）。
**新发现/坑**：① `check-run-artifacts` 禁止 `.work/log/**/*.EXIT`，完成标记须写进 `.log`；② `check-cfx-aliases` 依赖 DADAO-12 行号，spec 插入后须重跑 `gen_cfx_aliases.py`；③ `gen_isa_coverage` 依赖安装根，`install-host` 前会误报 `fence` reject。

### 修改文件
- spec：SimRISC-00/11/12、DADAO-12、Toolchain-01（`fence ciii` 正文/移册/语法）；`manifests/spec-readonly.lock.toml` 同步 5 册 sha256。
- contracts：`contracts/opcodes.yaml`（生成器 `tools/spec/generate_opcodes.py`）、`legality_rules.yaml`（新增 `encode_cfx_reserved`）、`.tao/contracts/{contract-isa,contract-asm,contract-asm-list,contract-cfx-aliases}.md`。
- LLVM：7 份组件补丁（InstrInfo/Formats/AsmParser/Printer/ISelDAG/ISelLowering）；QEMU：`insn.decode` + `trans_ctrl.c.inc`；musl：`atomic_arch.h`。
- 测试/工具：lit 正负例与 CodeGen 期望、`gen-*`/`gen-fast`、`atomics-fence.yaml`、arch 探针 padding、case-ledger、backend matrix；`.tao/knowledge/{MEMORY,milestones}.md`、DD-A002/A011。

### 验收命令与结果
- `make check` rc=0；`make check-modules JOBS=8` rc=0（L2）；`make check-lit` 159/159 rc=0。
- `check-spec-readonly` 21/21 OK；`check-spec-changelog` PASS；`check-patch-tree` 205 OK；`check-source-state` 5 组件 clean/1 commit；`check-instrinfo` 0 errors；`check-isa-coverage` accept 264/reject 2；`check_qemu_trans --strict` 266/266；`check-decodetree-repro` PASS。
- QEMU 定向：`atomics-fence.yaml` 17/17 PASS（零掩码 no-op、保留 cfx、hb≠0 均覆盖）；`build-mc`/`build-qemu`/`install-host`/`build-musl-shared`/`check-musl-freshness` rc=0。
- 证据 `.work/evidence/INTEG-041t/run.sh`：12 项 PASS；注入错误编码 ⇒ lit FAIL ⇒ `cp`+md5 还原 ⇒ 回绿。

### 遗留
- `min_rom_probe_030t.py` 的 C2/D2/D4b 5 例为既有失败（M9 归档已登记），与 fence padding 无关；未动其逻辑。
- 未跑 `check-full`/夜跑/全量 arch、musl 运行套件（按派单）；`fence.vma`/`fence.i`/DMA/TLB/cache 维护未改。
- **说明**：本任务派单原话「范围严格按 ADR-0044…同步更新 opcodes/contracts/汇编器/LLVM/QEMU（如已实现 fence）/测试/索引」即 spec 改动授权；`.tao/adr/adr-0004` 仅改旧 `fence 0` 示例为新语法，决策未变。

### 审阅记录 → 第 1 轮 engineer 自审
**判决**：可交 reviewer（未修 finding：无）。
- F1 `SimRISC-11 §1` 把 `fence` 列进「受 cfx mask 控制」的指令集合，语义过强 → ✅已修（移除该句中的 `fence`，保留 §6 独立屏障语义）；复验 `check-spec-purity`/`check-legality-drift` rc=0。
- F2 spec 插入导致 `check-cfx-aliases` 的 DADAO-12 行号漂移 → ✅已修（重跑 `gen_cfx_aliases.py`）；复验 `check-cfx-aliases`/`check-cfx-alias-table` rc=0。
- F3 `.work/log/**/*.EXIT` 触发 `check-run-artifacts` → ✅已修（删除 `.EXIT`，完成标记并入 `.log`）；复验 `check-run-artifacts` rc=0。
- F4 `gen_isa_coverage` 在 `install-host` 前读旧安装根，误报 `fence` reject → ✅已修（`install-host` 后重生成 matrix）；复验 `check-isa-coverage` accept 264/reject 2 rc=0。
- F5 musl changelog 先写「未重跑构建」，与实际已跑 `build-musl-shared` 不符 → ✅已修（改为真实 rc=0）；复验 `check-musl-freshness` PASS。
- F6 旧 `fence 0`/`fm` 残留示例（ADR-0004、contract-asm、DD-A011/A002、测试注释）→ ✅已修（仅示例/说明更新，决策未变）；复验 `check-asm-prose` rc=0、`grep` 无 live `fence_oiii_imm`。

### 审阅记录 → 第 1 轮 reviewer 验收
**判决**：Accepted（2026-10-30，独立重跑，全部以本人终端输出/退出码为准）。

**重跑记录**（完整日志 `/tmp/opencode/INTEG-041t-review/rerun.log`）：
- `make check` rc=0；`make check-modules JOBS=8` rc=0（L2，四 scope 全 PASS）；`make check-lit` rc=0（**159/159**，Total Discovered 159 / Passed 159 100%）。
- `check-spec-readonly` rc=0（21/21 OK）；`check-spec-changelog` rc=0 PASS；`check-patch-tree` rc=0（5 组件 205 补丁 OK）；`check-source-state` rc=0（llvm/qemu/embench/picolibc/musl 均 clean=True count=1）。
- `check-instrinfo` rc=0（0 errors，M9 34/34，`fence` ciii 已入 allow-list 口径）；`check-isa-coverage` rc=0（真源 266、accept 264/reject 2）；`check_qemu_trans --strict` rc=0（266/266，orphan 0）。
- `validate_decodetree`：无参调用打印用法 rc=1（**本人调用方式问题，非产物缺陷**）；带参重跑 `python3 tools/qemu/validate_decodetree.py .work/source/qemu/target/dadao/insn.decode contracts/opcodes.yaml` rc=0 PASS（266/266，错误 0）。`check-decodetree-repro` rc=0 PASS；`check-musl-freshness` rc=0 PASS。
- `.work/evidence/INTEG-041t/run.sh` rc=0，**12/12 PASS**（与完成区声称逐条一致）。

**重点测试独立复核**：
- `fence cfx0,0` = `79 00 00 00`、`fence cfx63,0xfff` = `79 fc 0f ff`（本人跑 llvm-mc）；`fence 0` 汇编 rc=1 拒绝；`fence cfx0, 0x1000` rc=1 + `reserved encoding`。
- `atomics-fence.yaml` 17/17 PASS（含 hb=1/hb=63、reserved cfx 7/14/19/61 → ILLI、零掩码 no-op、cfx0/cfx63 各组合）；重跑生成器字节级一致（md5 不变），`atomics-lrsc.yaml` 未变。
- musl `a_barrier` 同步：安装根 `libc.so` 反汇编实测 59 处 `79 00 0f ff fence cfx_umon, 4095`，旧编码 0 处。

**独立注入→FAIL→还原→回绿**（禁 checkout/restore/stash；`cp` 备份 + md5）：
- 注入 `contracts/opcodes.yaml` fence `opc 0x79→0x78` ⇒ `run.sh` **rc=1，FAIL(2)**（contract 项红）；
- `cp` 还原 + `md5sum -c` OK（`3d87c921…` 复原）⇒ `run.sh` **rc=0 回绿**；工作区快照 `git status --porcelain -uall` 前后逐行一致、关键 3 文件 md5 复原。

**ADR-0044 逐条核验**：opc 0x79/ciii ✓（opcodes.yaml+InstrInfo.td+insn.decode+SimRISC-00 主表 0111-1001）；cfxha[23:18]、hb=immu18[17:12] SBZ、hc=pred/hd=succ ✓；pred/succ cr/cw/ci/co/mr/mw ✓（spec 表/AsmParser 12 常量/QEMU FENCE_CR..MW）；`cfx0`/`cfx_umon`=all ✓（同编码、反汇编打 cfx_umon）；immu18 整体不拆 ✓；`fence 0` 拒绝 ✓；fm/TSO 已删 ✓（live 树无 `fence_oiii_imm`/`PRED_R`）；SimRISC-12→11 移册+索引+lock 5 册 sha 同步 ✓。

**约束核验**：未改 `fence.vma`/`fence.i`/DMA/TLB/cache 语义（diff 仅 §7.2 fence 段）；未跑 full/夜跑；reviewer 未 commit/push；仓库无临时残留（`*_tmp*`/`_gate*`/`*.orig`/`*.rej` grep 无命中）；临时文件均在 `/tmp/opencode/`。

**Findings（非阻断，architect 收尾处置）**：① 完成区「check-source-state 3 组件 clean」口径偏窄——实跑 5 组件全 OK（本任务改 3 个），数字笔误级；② `docs/DDLN` TT-A011/TT-A002 草稿（gitignore 不跟踪）仍是旧 `fm/pred/succ` 描述，按 DDLN 规则编辑应先落 TT 再复制 DD——本次直接改了 DD，建议收尾时同步 TT 草稿防下次 TT→DD 覆盖回退；③ QEMU 屏障强度（TCG op 级）本轮 `run.sh` 未断言（单 hart 运行时不可见，沿用既有前提），仅向量+ILLI 覆盖。
