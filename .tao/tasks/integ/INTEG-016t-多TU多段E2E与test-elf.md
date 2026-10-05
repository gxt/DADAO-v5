# INTEG-016t: 多 TU/多段 E2E + `make test-elf`

**模块**：integ
**项目里程碑**：M4
**依赖**：`LLVM-056t`、`QEMU-042t`、`TESTCASES-029t`、`TESTCASES-030t`、`TESTCASES-032t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `LLVM-056t` 的 `ld.lld` + `dadao.lds`（ET_EXEC 产出与段布局）；`QEMU-042t` 的 ELF 加载器（`Ehdr`/`Phdr`/`e_entry`）。
  - `TESTCASES-030t` 的 `tests/llvm/codegen/m4/`（多 TU/多段 `.ll` + `expected.yaml` + `validate_elf_vectors.py`）；`TESTCASES-029t` 的 `tests/llvm/lit/MC/DADAO/`（L1 向量，带 `UNSUPPORTED:` 标记待接入）。
  - `TESTCASES-032t` 的 `not`/`neg` 功能向量（`tests/llvm/lit/MC/DADAO/` 的 `xnor.o`/`sub.sb/sw/st/so` 编码向量 + `tests/llvm/codegen/m4/` 的 `not`/`neg` 执行向量，均带标记/独立清单待接入）。
  - M3 既有 `tests/llvm/codegen/`（15 `.ll` + `expected.yaml`，`INFRA-045t` 迁移后）与 `make test-codegen`（raw-bin 链，**须保留并存**）；`tests/scripts/codegen_crt0.s`、`tests/scripts/trampoline.bin`。
  - `ADR-0004`（`SPEC-107t` 调整后）/`contract-elf §5/§6`；`spec/Process-05` §6（L3 落点 `tests/codegen/` + `tools/integ/`）。
- **输出**：
  - `tools/integ/run_elf_e2e.py`：fail-closed 多 TU 驱动——对每个程序：逐 TU `llc -march=dadao -filetype=obj` → `.o`；`ld.lld -T tests/scripts/dadao.lds`（含 `crt0`）→ `prog.elf`（ET_EXEC）；`qemu-system-dadao` **直接加载 ELF**（按 `SPEC-107t` 约定）→ 比较 guest 退出码 vs `expected.yaml`；逐例打印「名字/期望/实际/退出码」。
  - `Makefile` 新增 **`test-elf`** 目标（前置 `build-mc`/`build-lld`/`build-qemu`；任何用例不符即非零退出）；与 `test-codegen` **并存**。
  - **接入 L1 向量**：**移除** `tests/llvm/lit/MC/DADAO/` 中 M4 向量的 `UNSUPPORTED:` 标记（`TESTCASES-029t` 与 `TESTCASES-032t` 的向量），确认 `make check-lit` 转绿（实现已由 `LLVM-051t`~`054t` 落地）。
  - **差分**：M3 `tests/llvm/codegen/*.ll` 经**新 ELF 链**（多段、经 LLD）再跑一遍，与 `make test-codegen`（raw-bin）结果**逐一一致**（记录差分表）；`tests/llvm/codegen/m4/` 的多 TU/多段用例（`TESTCASES-030t`）与 `not`/`neg` 执行用例（`TESTCASES-032t`）经新链跑对。
  - **ELF 结构断言**：`llvm-readobj`/`llvm-readelf` 验证 `e_machine=0x0DA0`、`e_flags=0x1`、`Type=EXEC`、`SHT_RELA` 无残留（已解析）、`e_entry` 正确、`.text` file-offset 0。
  - **负例**：畸形 ELF → QEMU 显式拒绝（非零）；reloc 溢出 → `ld.lld` link-time error（非零）。
- **约束**：
  - **M3 链并存**：`make test-codegen`（raw-bin/trampoline）保持原样且绿；`test-elf` 为**新增**。
  - 判据：每用例 guest 退出码 == 期望；不等/超时/非预期 fault ⇒ FAIL（精确比较为主）。
  - 反例门控：驱动内置 `--inject`（改一条期望值 → 预期 FAIL → 还原 → 回绿）；完成区给真实输出；**还原含重建/重跑全链**。
  - 留证禁 `tee`（用 `cmd > log 2>&1; rc=$?`）；复杂输出留存 `.work/log/integ/`；临时目录 `/tmp/opencode/INTEG-016t/`；**不提交 git**。
  - `Makefile` 为共享文件，与其它改 `Makefile` 的任务**串行**。

## 验收标准

1. `make test-elf` EXIT=0；逐用例「名字/期望/实际/退出码」；**多 TU**（≥2 TU 链接）与**多段**（`.text`+`.data`+`.rodata`）各 ≥1 通过。
2. **链路每步真实执行**：`llc`/`ld.lld`/`qemu` 均 EXIT=0，完整命令与输出留存 `.work/log/integ/`（≥1 用例逐步展示）。
3. **ELF 结构断言**：`readobj` 输出满足 `e_machine`/`e_flags`/`ET_EXEC`/`e_entry`/`SHT_RELA` 已解析（给真实输出）。
4. **差分**：M3 15 向量经新 ELF 链结果 == `make test-codegen`（raw-bin）结果（差分表，0 分歧）。
5. **L1 接入**：移除 `tests/llvm/lit/MC/DADAO/` 中 M4 向量的 `UNSUPPORTED:` 标记后 `make check-lit` EXIT=0（L1 向量转绿）；`make check` EXIT=0。
6. **负例**：≥1 畸形 ELF 被 QEMU 拒绝（非零）；≥1 reloc 溢出被 `ld.lld` 判 link-time error（非零）——真实输出。
7. **反例门控**：`run_elf_e2e.py --inject`（改期望值）→ FAIL → 还原**重跑全链** → 回绿；完成区给真实输出。
8. 一键证据脚本 `.work/evidence/INTEG-016t/run.sh`（非交互、失败非零、逐项打印、含注入自检、结尾无 `tee`）；`git status` 仅本任务应有改动。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
