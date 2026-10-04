# QEMU-040t: 新增指令 `sub.o_orrr_dbb`（RB − RB → RD）的语义翻译（trans）

**模块**：qemu
**项目里程碑**：M3
**依赖**：`SPEC-100t`（编码/legality 已由 `adr-0012 D9` 定稿）
**状态**：待开始

> **决策依据（已定）**：`adr-0012 D9.1`（`Accepted`）——`id=sub.o_orrr_dbb`、助记符 `sub.o`、`op=0x40`/`ha=0x33`/`mask=0xFFFC0000`/`value=0x40CC0000`、legality `rdhb != rd0`、`scope=m3`。
>
> **原子落地集**：本任务与 `SPEC-100t` **必须同一集成波/同一提交**落地。`make check` 的 `check-interface` 要求 `contracts/opcodes.yaml` 每条 ↔ QEMU `trans_*` 一一对应（`check_qemu_trans --strict` + `QEMU trans_* 定义数 == 条目数`）；**单独提交 `SPEC-100t` 会红**。
>
> **串行**：本任务与 `SPEC-101t`（RB 算术改名/改编码，改同一 `insn.decode`/`trans_*`）**不得并行**；顺序 `SPEC-101t → SPEC-100t → QEMU-040t`。
>
> **背景**：M3 此前假定 qemu 无实现任务（执行层已由 M1 冻结）；本指令为**新 ISA 编码**（`scope:m3`），QEMU 侧需新增 decode + trans 才能执行（否则为保留编码 → UNDI）。

## 执行环境
**执行环境**：本地

## 接口规范

### 输入

- `SPEC-100t`/`adr-0012 D9` 事实：`id=sub.o_orrr_dbb`、`arg_misc` 字段 `rdhb`=a->hb（dst,rd）、`rbhc`=a->hc（src,rb）、`rbhd`=a->hd（src,rb）、`op=0x40`/`ha=0x33`/`mask=0xFFFC0000`/`value=0x40CC0000`、legality `rdhb != rd0`。
- 现有 QEMU 实现（补丁 `components/qemu/patches/target/dadao/`；`.work/source/qemu/` 为应用后工作树）：
  - `insn.decode`：`@misc` 子表；每条 `func  <14 位 op+ha 二进制>..................  @misc`（如 `cmp_uo_orrr_dbb  01000000110010..................  @misc`，`SPEC-101t` 后）。
  - `insn_trans/trans_compare.c.inc`：`trans_cmp_uo_orrr_dbb` ——**直接同形参照**（`a->hb==0` → ILLI；`load_rb(a->hc)`/`load_rb(a->hd)`；`store_rd(a->hb)`）。
  - `insn_trans/trans_arith.c.inc`：`trans_sub_o_orrr_bbd`（RB 目的版，用 `load_rb`/`load_rd`/`store_rb`）。
  - `translate.c`：`load_rd`/`store_rd`/`load_rb`/`store_rb` helper；`gen_exception_illegal`。
- 命名（**由 opcodes.yaml 派生，勿硬编码**）：`tools/qemu/validate_decodetree.py::build_unique_func_names` / `sanitize_name`——函数名 = `trans_<sanitize(id)>`（`sub.o_orrr_dbb` → `trans_sub_o_orrr_dbb`）；insn.decode 内 token = `<sanitize(id)>`。
- 门控：`tools/qemu/check_qemu_trans.py --strict`、`tools/qemu/validate_decodetree.py`、`tools/integ/check_interface_alignment.py`。

### 输出

1. `insn.decode.patch`：新增一行 pattern：`sub_o_orrr_dbb\t01000000110011..................\t@misc`（14 位 = op `0x40` + ha `0x33`；实际字符串以 `mask/value` 为准）。
2. `insn_trans/trans_arith.c.inc.patch`：新增 trans（**语义**）：
   ```c
   /* §7.1 sub.o rdhb, rbhc, rbhd (orrr, MISC-octa): 64-bit RB − RB → RD
    * result = rbhc - rbhd (full 64-bit two's-complement), written to rdhb.
    * ILLI: rdhb == 0 */
   static bool trans_sub_o_orrr_dbb(DisasContext *ctx, arg_misc *a)
   {
       if (a->hb == 0) { gen_exception_illegal(ctx); return true; }
       TCGv_i64 rbhc = load_rb(ctx, a->hc);
       TCGv_i64 rbhd = load_rb(ctx, a->hd);
       TCGv_i64 result = tcg_temp_new_i64();
       tcg_gen_sub_i64(result, rbhc, rbhd);
       store_rd(a->hb, result);
       return true;
   }
   ```
   （函数名/字段名以 `SPEC-100t` 定稿与 `arg_misc` 实际为准。）
3. 探针：`tools/qemu/min_rom_probe_040t.py`（或 `.work/evidence/QEMU-040t/` 下）——覆盖：正常差值（含 `rb−rb` 为负）、`rdhb==rd0` → ILLI(0x88)、保留槽 `ha` 邻位 → UNDI(0x89) 对照；含反例注入自检。
4. 完整命令输出留存 `.work/log/qemu/`。

### 约束

- **语义单一真源**：`rd = rb − rb`（64 位补码），与 `contract-isa §7` 一致；不得从 LLVM 反推。
- **不越界**：仅改本任务列出的 QEMU 补丁；不动 `SPEC-101t` 的改名 trans，不改其它指令。
- **补丁导出纪律**（`spec/Process-01`）：`make prepare` 应用；导出补丁写 `/tmp`、非空 blob、`make check-patch-tree`（含断言⑥）。
- **构建**：`make prepare` + `make build-qemu`（**5–20 分钟**，开始前在回复写明预计耗时；`JOBS` 限制）；失败即停、不自动重试。
- 临时目录 `/tmp/opencode/QEMU-040t/`；**不提交 git**。

## 验收标准

1. `make prepare` 后 `.work/source/qemu/target/dadao/insn.decode` 含新 pattern；`validate_decodetree.py` 对 `insn.decode` EXIT=0（mask/value 与 `opcodes.yaml` 一致、无 overlap）。
2. `make build-qemu` 退出 0。
3. **执行证据**：探针端到端真实输出——正常 `rb−rb`（含负结果）＝ 期望值；`rdhb==rd0` → ILLI(0x88)；保留槽（旧 `ha`）→ UNDI(0x89)（对照，证明解码生效）。
4. `check_qemu_trans.py --strict` EXIT=0（`228/228`；新条目有 trans）；`check_interface_alignment.py` EXIT=0（`QEMU trans_* 定义数` 与 opcodes 条目数 `228` 一致）。
5. `make check-patch-tree` EXIT=0；补丁 `git apply` 干净复现。
6. 反例门控：注入（把 trans 改错 / 改 insn.decode 选择位与邻条重叠）→ 探针或 `make build-qemu`/`validate_decodetree` **FAIL**；复原（**含重建**）→ 回绿；真实输出留存 `.work/log/qemu/`。
7. 一键证据脚本 `.work/evidence/QEMU-040t/run.sh`（规格同 `LLVM-033t`；含「注入→FAIL→还原（含重建）→回绿」自检）。
8. 未越界：`git status` 干净（除本任务应有改动）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
