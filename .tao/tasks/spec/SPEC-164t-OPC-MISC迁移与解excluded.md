# SPEC-164t: `OPC-MISC` 迁 `op 0x47`（含 `ctpop/ctlz/cttz` 并入）+ `fence`/`lr`/`sc` 解 `excluded`

**模块**：spec
**项目里程碑**：M9（收尾前）
**依赖**：`SPEC-166t`（已验证）、`INFRA-102t`（已验证，`master 9fd5974e`；门控已无写死常量）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源（用户裁定，2026-10-22）

- 「还有一个编码改动过：OPC-MISC的编码改为：0100-0111」
- 「修改编码：`ctpop_orri_rd` `ctlz_orri_rd` `cttz_orri_rd` 从 `OPC-octa` 改为 `OPC-MISC`，opx：`100-101`/`100-110`/`100-111`」
- 「同意」（`ISS-328`：`fence` + 24 条 `lr/sc` 已实现但账面仍 `excluded`/`ILLI`）
- 结构收益：迁后所有 `OPC-*` 表集中在 `0100` 行（`0x40–0x44` + `0x47`），`0x45`/`0x46` 留空

## 现场事实（执行前须复核）

- `contracts/opcodes.yaml`：`op = 0x77` 的记录 **26 条** = `fence_oiii_imm`、`swym_oiii_imm`、`lr`×12、`sc`×12；其中 `fence`+`lr/sc` 共 **25 条** `scope: excluded` + `decode: ILLI`
- 另 **3 条** 从 `OPC-octa` 迁入：`ctpop_orri_rd`（`op 0x40 / ha 0x1D`）、`ctlz_orri_rd`（`0x40 / 0x1E`）、`cttz_orri_rd`（`0x40 / 0x1F`），`scope: m8`
- `OPC-MISC` 内 `ha = 0x25/0x26/0x27` **空闲**（现用：`fence 0x20`、`swym 0x22`、`lr 0x10–0x13`、`sc 0x18–0x1B`）
- `spec/SimRISC-00` 主表：`0111-0111` 单元格 = `OPC-MISC`；`0100-0111` **为空**
- QEMU：`insn.decode.patch` 有 **26 条** `01110111…` pattern；`trans_fence_oiii_imm`（`trans_ctrl`）、`trans_lr_*`/`trans_sc_*`（`trans_mem`）已实现
- LLVM：`DADAOInstrInfo.td.patch` / `DADAOAsmBackend.cpp.patch` 有 `0x77…` 硬编码；`fence` 由原子降级路径发射
- 计数现值：`total 264 / m1 156 / fp 64 / excluded 27 / m3 1 / m8 7 / m9 9`

## 目标

1. **编码迁移**：26 条 `op: 0x77 → 0x47`，重算 `value`/`mask`（`value = (0x47 << 24) | (ha << 18)`，`mask` 不变）。
1b. **3 条并入**：`ctpop`/`ctlz`/`cttz` 改 `op 0x40 → 0x47`、`ha 0x1D/0x1E/0x1F → 0x25/0x26/0x27`；`scope: m8` 不变、无位宽后缀不变。
   - 规范侧：从 `SimRISC-00 §4.2 OPC-octa` 子表移入 `§4.1 OPC-MISC` 子表；**删除**原「无位宽后缀指令借用 MISC-octa 格位」的例外说明（迁入 MISC 后不再需要）。
   - 连带：`SimRISC-04`「Bit manipulating」章节里关于"借用 octa 格位"的注同步删/改。
2. **主表迁移**：`SimRISC-00` 主表把 `OPC-MISC` 从 `0111-0111` 移到 `0100-0111`（`0111-0111` 置空 = reserved UNDI）。
3. **翻转**：`fence` + 24 条 `lr/sc`：`scope: excluded → m9`、删 `decode: ILLI`；`swym` 保持原 scope。
4. **QEMU**：26 条 decode pattern 前缀 `01110111 → 01000111`；trans 不变。
5. **LLVM**：`fence`/`lr`/`sc` 的编码常量同步（若用 TableGen 由 opcodes 生成则重生成）。
6. **生成物**：向量（`atomics-*`、`isa/misc`）、lit（`gen-excluded.s` 等）、探针中的期望编码重生成。
7. **账面**：`excluded 27 → 2`（仅 `cfxld`/`cfxst`）、`m9 9 → 34`、`m8` 仍 7；`total` 不变（264）。
   - 注：`018` `check_scope` 若已由 `INFRA-102t` 去常量，则本册不改常量。
8. **ADR**：`ADR-0034` 加 `## 修订`，记录 op 变更（决策依据 = 用户原话，逐字）；`ADR-0032`/`ADR-0012`（提及 `ctlz/ctpop/cttz` 格位）同理；`MEMORY.md` 第 6 项同步。
9. **门控补位**：`check_tables.py` 增加 `OPC-MISC`（`op 0x47`）表覆盖（`INFRA-102t` 遗留：现只到 `op 0x44`）。

## 验收

1. `check_scope` / `check-isa-coverage` / `check_qemu_trans --strict`（应仍 **264/264**）全绿；`grep '0x77' contracts/opcodes.yaml` ⇒ **0**（26 条全部 `0x47`）。
2. QEMU 实机：`fence`/`lr`/`sc` 与 `ctpop/ctlz/cttz`（各 1 条）能执行（原子冒烟 1 例：`__atomic_add_fetch` 跑通），且 `swym 0` 仍为 no-op。
3. spec 主表：`0100-0111 = OPC-MISC`、`0111-0111` 空；`check_spec_codeblocks`/`check_tables` 绿。
4. LLVM：`install-host` + lit 全绿；`objdump` 反汇编 `fence` 显示新编码。
5. **编码核验**：`objdump` 反汇编 `ctpop` 显示 `0x47…`；`ctlz`/`cttz` 同理；`OPC-octa` 子表不再出现这三条。
6. **可达 FAIL ≥4**：① 留一条 `op: 0x77` ⇒ 编码一致性门控红；② 删一条 decode pattern ⇒ `check_qemu_trans` 263/264 红；③ 把一条改回 `excluded` ⇒ `check_scope`/`check_fp_contract` 类不变量红；④ `ctlz` 的 `ha` 写回 `0x1E` ⇒ 编码一致性红。
7. 重建：`make install-host` + `build-builtins` + `build-musl-shared`（`.td` 改动）；`make check`(L1) + `make check-modules`(L2) 绿。

## 接口规范

- **输入**：`contracts/opcodes.yaml`、`spec/SimRISC-00`、`components/qemu/patches/**`、`components/llvm-project/patches/**`、`tests/**`、`tools/**`、`.tao/adr/adr-0034-*.md`、`.tao/knowledge/MEMORY.md`。
- **输出**：迁移后的编码 + 翻转后的 scope + 重生成的向量/lit/探针 + ADR 修订。
- **约束**：不改指令语义；不新增指令；不 commit/push；临时目录 `/tmp/opencode/SPEC-164t/`。

## 风险与纪律

- **机器码不兼容**：`0x77…` → `0x47…`，所有已编产物须重编（工具链、bootrom、测试二进制）；旧 ELF 不得再用于验收。
- **ADR 修订**：`ADR-0034`（`D1`/`D5`：fence/lr/sc 编码）、`ADR-0032`/`ADR-0012`（提及 `ctlz/ctpop/cttz` 格位）属 `Accepted` ⇒ 只加 `## 修订`，不改决策正文；决策依据一律引用用户原话。
- 逐条比对 `insn.decode.patch` 的 26 条 mask/pattern，禁批量正则一把梭。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
