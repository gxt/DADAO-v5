# m15-spec-003: 伪指令 `set.ft rf, rs` / `set.fo rf, rs` 合并为 `set.rf rf, rs`

**模块**：spec
**项目里程碑**：M15
**依赖**：`m15-spec-002`（已合入：伪指令正文分层，`§6.1` 表是唯一展开表）、`m15-testcases-003`（在跑：改同一载体文件，须**先合入**再派本任务）
**可并行分片**：否（两册 spec + LLVM + 载体 + 契约，跨模块单写者）
**预估**：3–4 h（含 LLVM 重建 + 三平台回放）
**档位**：大改（跨 spec/llvm/testcases 的 ISA 表述 + 实现；复核 ≥4 路注入 + 独立重建）
**状态**：待开始

## 背景（用户 2026-11-16 裁定）

用户提出把 `set.ft rf, rs` 与 `set.fo rf, rs` 合并为 **`set.rf rf, rs`**，并裁定「立册」。

依据（现场核实）：

- 两种写法**展开完全相同**：`rd2rf`/`rf2rf`（**整 64 位复制**）——`SimRISC-00 §5` 表两行与 `Toolchain-01 §6.1` 表两行都这么写；
- 现有载体 `tests/inst/00-isa-design/pseudo_set.fx_reg.S` **本来就是"一个文件覆盖 ft/fo 两族"**，文件头注释写着「两者从 rf 源展开都是 `rf2rf`、语义一致（用户 2026-11-15 裁定方案 A）」⇒ 合并是**把既有事实写进名字**；
- 命名规则因此统一为「**名字只编码有歧义的那一维**」：寄存器源无宽度歧义 ⇒ 按**目的 bank** 叫 `set.rf`；立即数源有宽度歧义（窄写 vs 整 64 位）⇒ 保留 `set.ft rf, imm32` / `set.fo rf, imm64`。

## 目标

1. **规范（两册 + 一处指针）**
   - `spec/SimRISC-00 §5` 表：**8 行 → 7 行**（两行寄存器源合并为 `set.rf | rf, rs | rd2rf/rf2rf`），引导句里的伪指令清单 `set.rd/set.rb/set.ft/set.fo` 改为 `set.rd/set.rb/set.rf/set.ft/set.fo`；
   - `spec/Toolchain-01 §6.1` 表同改（8→7），「保留（实现，8 条合成型）」改为 **7 条**；`§6.2` 的 `6.2.3 set.ft / set.fo` 小节改名为覆盖 `set.rf` + 立即数两形（内容按新助记符替换，语义不变）；
   - `spec/Toolchain-01` 的**写宽对照表**（`set.ft` 两种源形式对照）改为 `set.ft rf, imm32`（窄写）vs **`set.rf rf, rs`**（整 64 位）；
   - `spec/SimRISC-03 §4` 的指针句同步（该册只引 `Toolchain-01 §6.2`）；
   - 两册附录 `-rc` 段各加一条变更痕迹；`SimRISC-00`/`Toolchain-01`（若 `SimRISC-03` 也动则三册）sha256 **同笔重算**。
2. **LLVM 实现**（`components/llvm-project`）
   - `DADAOAsmParser.cpp`：新增助记符 `set.rf`，寄存器源分支走 `rd2rf`/`rf2rf`；`set.ft`/`set.fo` **只保留立即数形式**（寄存器源若仍出现 ⇒ 报明确错误，不静默接受）；
   - printer/disassembler：反汇编仍只出真实指令（伪指令不进反汇编），但 **MC 层的别名/助记符表**要同步；
   - lit：新增 `set.rf` 的展开用例（立即数不适用，覆盖 `rd2rf`/`rf2rf` 两路 + 目的 rf0 边界），并把 `set-ft-fo.s` 里寄存器源的旧用例改为 `set.rf`；更新 `README-m4.md` 的伪指令清单；
   - 改完 **`make install-host`**（否则 `check-lit` 读旧二进制 ⇒ 假绿，`ISS-210`）。
3. **载体与登记**
   - `tests/inst/00-isa-design/pseudo_set.fx_reg.S` → **`pseudo_set.rf_reg.S`**（`git mv`），文件内 `set.ft/set.fo` 的寄存器源调用改 `set.rf`，头注释同步（"fx = ft/fo 两族"的说明删除）；
   - 三处登记同步：`tests/inst.yaml`（`file:` 与 `name`）、`tools/testcases/check_tests_index.py`（`NON_ID_CARRIERS`）、`tools/testcases/validate_vectors.py`；
   - `tests/inst/MIGRATION.md`、`tests/inst/README.md` 若有旧名，一并更新（历史迁移记录**不改**）。
4. **契约**：`contract-asm.md` §6.1 的 8 条表改 7 条并加 `set.rf` 行；`contract-isa.md` 的伪指令指针若列了 `set.ft/set.fo` 寄存器源，改为 `set.rf`。

## 验收（真实 rc + 输出）

1. **规范自洽**：`grep -c "set\.ft" spec/` 后，`set.ft` 的每一次出现都只跟 **`imm32`**（无 `rs` 形）；`set.fo` 同理只跟 `imm64`；两册表行数 7/7 且第三列逐字相同；`check-spec-readonly`（锁与实测 sha 一致）、`check-spec-refs`、`check-spec-purity`、`check-spec-changelog`、`check-rule-refs` 全 rc=0；
2. **LLVM**：`make install-host` rc=0（贴新 `llvm-mc` md5）；`make check-lit` **全绿**（条数现场统计，不低于改前 177）；`set.rf` 的正例/负例（`set.rf rf, imm` ⇒ 报错）都有 lit 覆盖；
3. **载体三平台一致**：改名后的 `pseudo_set.rf_reg.S` 在 QEMU/chipyard/gem5 上**逐字节一致**（贴每平台镜像数与 `semi.out` md5）；`make check-inst-asm` 镜像数与改前一致、904/904；
4. **登记一致**：`check-tests-index`（条数不变）、`check-case-ledger`（行数不变）、`check-dirs`、`check-no-residue`、`check-inst-macro-scope` 全绿；
5. **≥4 路注入**（`cp`+md5 还原）：① 把 `set.rf` 展开错成两条 `set.w`（窄写）⇒ 载体检查点红；② 让 `set.ft rf, rs` 仍被接受 ⇒ 新负例判据红（证明旧形确实停用）；③ 表行数改回 8 ⇒ 表一致性判据红；④ 锁 sha 改 1 字符 ⇒ `check-spec-readonly` 红；
6. L1 `make check` rc=0；完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **语义不变**：合并只是**换名 + 去冗余**；`set.rf rf, rs` 的展开、写宽、rf0 边界行为与合并前的寄存器源形态**逐条一致**；立即数两形（`ft`/`fo`）**行为不动**；
- **不保留旧名别名**（v5 未发布、仓内只有那一个载体用寄存器源；用户口径与 QEMU 机器名一致）；
- 不动 `tests/inst` 其它载体（`m15-testcases-003` 正在改同一册的文件，本任务只动 `pseudo_set.fx_reg.S` → `.rf_reg.S`）；
- 不提交 git；注入还原 `cp`+md5；证据基线钉死 commit（`ISS-458`）；脚本按 `git rev-parse --show-toplevel` 推根（`ISS-456`）。

## 审阅记录

（待填）
