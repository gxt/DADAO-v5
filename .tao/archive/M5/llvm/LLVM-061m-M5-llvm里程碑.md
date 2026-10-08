# LLVM-061m: M5 llvm 里程碑

**模块**：llvm
**项目里程碑**：M5
**状态**：里程碑
**目标**：LLVM 支持 M5——实现 `trap`/`escape`/`cfx2rc`/`cfx2rd`（`SimRISC-11 §其它`）的 MC（parser/printer/disassembler/编码）+ 必要 CodeGen/内建；`escape` 位宽关系落地（汇编 `imms20`（字节，`%4==0`）⇔ 编码 `imms18`（`>>2`））；两写法 `cfx<ha>`/`cfx_<name>` 等价 + `cfx2rd/cfx2rc` 简化 regname 写法；L1 MC 向量 + 编码 oracle；`make check`/`check-patch-tree`/`check-lit` 绿。`SimRISC-12`（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）保持 deferred。
**关联任务**：`LLVM-060t`（1 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（trap/escape/cfx2* 编码/AsmParser/InstPrinter/Disassembler）+ `series` + `changelog.md`；L1 MC 向量与独立 oracle
- `make build-mc` EXIT=0；`llvm-mc` 对 4 条指令正例 EXIT=0 且字节 == `contracts/opcodes.yaml` 派生期望；`cfx_<name>`/`cfx<ha>` 等价 ≥2 对；简化 regname 写法等价；`escape` 位宽/非 4 倍数报错/越界报错
- 往返（汇编↔反汇编）≥1
- 不回归：`make check` EXIT=0；`make check-patch-tree` EXIT=0（断言⑥）；`make check-lit` EXIT=0
- `check-source-state`：`.work/source/llvm-project` worktree clean、HEAD = base+1
- `SimRISC-12` 范围未越界（`grep` 证据）

## 核验记录（主会话）

**M5 llvm 里程碑核验（2026-10-08，architect 代主会话）**　**判决：满足，置 `里程碑`**

证据来源：`LLVM-060t` 完成区/审阅记录、`.work/log/llvm/LLVM-060t-*.log`、`.work/evidence/LLVM-060t/`；独立只读复核（`ls`/`grep series`/`check_patch_tree.py`〔含 `--source-state`〕）。

| # | 核验项 | 证据（真实） | 结论 |
| --- | --- | --- | --- |
| 1 | 关联任务 `LLVM-060t` `已验证` | 头部 `**状态**：已验证` | ✅ |
| 2 | 产出：`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + `series` + `changelog.md` | `patches/llvm/lib/Target/DADAO/{AsmParser/DADAOCfxAlias.inc.patch,DADAOInstrFormats.td.patch,DADAOInstrInfo.td.patch,MCTargetDesc/DADAOMCInstPrinter.cpp.patch,Disassembler/…}`；`series` 58 条；`changelog.md` 存在 | ✅ |
| 3 | 产出：L1 MC 向量与独立 oracle | `tests/llvm/lit/MC/DADAO/cfx2-trap-escape.s`（+`-err.s`）+ oracle `validate_cfx_vectors.py`；生成器 `tools/llvm/gen_cfx_alias_table.py` | ✅ |
| 4 | `make build-mc` EXIT=0 | `LLVM-060t-build-mc2.log` 末 `build-mc: PASS` | ✅ |
| 5 | 4 条指令正例字节 == `contracts/opcodes.yaml` 派生期望 | 完成区：`trap`=`7f 08 00 01`、`escape`=`7e 00 00 01`、`cfx2rd`=`7a 00 50 c2`、`cfx2rc`=`7b fc 80 42`（`op` 0x7F/0x7E/0x7A/0x7B，`mask 0xFF000000`） | ✅ |
| 6 | `cfx_<name>`/`cfx<ha>` 等价 ≥2 对 | `trap cfx_power,0` ≡ `trap cfx63,0` = `7f fc 00 00`；`trap cfx_umon,0` ≡ `trap cfx0,0` = `7f 00 00 00` | ✅ |
| 7 | 简化 regname 写法等价 | `cfx2rd cfx_umon_excp_cause_ip, rd2` ≡ `cfx2rd cfx_umon, cg5, rc3, rd2` = `7a 00 50 c2`；`cfx2rc cfx_power_ctrl, rd2` 同理 | ✅ |
| 8 | `escape` 位宽/非 4 倍数报错/越界报错 | `…,8`=`7e 00 00 02`（`imms18=2`）；`,6` ⇒ rc=1「multiple of 4」；`524288`/`-524292` ⇒ rc=1「out of range」 | ✅ |
| 9 | 往返（汇编↔反汇编）≥1 | `llvm-objdump -d` 还原助记符；`llvm-mc -filetype=asm` 规范化 → 重汇编 → `cmp` 对象一致（roundtrip rc=0） | ✅ |
| 10 | 不回归：`make check`/`check-patch-tree`/`check-lit` EXIT=0 | `LLVM-060t-check.log` `repository checks: PASS`（lit 62/62）；`check-patch-tree` EXIT=0；`LLVM-060t-check-lit3.log` `Passed: 62 (100.00%)` | ✅ |
| 11 | `check-source-state`（`.work/source/llvm-project` clean、HEAD=base+1） | 本次跑 `check_patch_tree.py --source-state`：`llvm-project: OK HEAD=0e9e52f7baee count=1 clean=True`（base `6dfe1677a`） | ✅ |
| 12 | `SimRISC-12` 范围未越界（`grep`） | 完成区遗留 4：`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*` 保持 `excluded`/decode ILLI；`check_scope` `excluded=11` | ✅ |
| 13 | `check-patch-tree` 断言⑥ | 本次跑 `check-patch-tree: 2 component(s), 92 patches OK`（`LLVM-060t` 时点 90，后随 `QEMU-046t` 增至 92） | ✅ |

**注**：`check-patch-tree` 计数随时点演进（`LLVM-060t`=90 → `QEMU-046t`=92），非本模块回归；本次独立跑为 **92 OK**。

**跨模块影响处置**：
- `ISS-110`（cfx 指令 MC 实现，`scope[llvm,M5]`）：本模块交付 4 条（`trap`/`escape`/`cfx2rd`/`cfx2rc`）⇒ **部分收口**；剩余 `cfxld`/`cfxst` = `SimRISC-12`，M5 明列范围外。非阻断。
- `ISS-162`（`DADAOAsmParser` 诊断枚举缺 `FIRST_TARGET_MATCH_RESULT_TY` 偏移）：**llvm-only 既有隐患**（本任务已规避），登记跟踪，非 M5 门槛项、无跨模块影响。
- `ISS-148`/`ISS-159`/`ISS-161`（llvm 既有遗留）：llvm 模块内，非 M5 引入、非阻断。

**无未处置跨模块项。**

## 审阅记录

#### M5 模块里程碑核验（architect，2026-10-08）

**判决**：**满足 ⇒ `**状态**` 置 `里程碑`**。`LLVM-060t` 全 `已验证`；13 项核验逐条通过（4 指令编码/字节、两写法等价、`escape` 位宽诊断、往返、`check`/`check-patch-tree`/`check-lit` 不回归、`check-source-state`=`base+1` clean、`SimRISC-12` 未越界）。跨模块项（`ISS-110` 部分收口 = `SimRISC-12` 范围外）已处置，无未处置项。

**边界**：本次仅改本文件（`**状态**` 字段 + `## 核验记录（主会话）` + 本记录）；**`spec/` 交集为空**；未触 `components/**`/`contracts/**`/`Makefile`/`tools/**`；未新增/删除任务。
