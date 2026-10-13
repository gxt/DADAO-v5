# TESTCASES-040m: M6 testcases 里程碑

**模块**：testcases
**项目里程碑**：M6
**状态**：里程碑
**目标**：M6 测试资产就位——新能力向量（调用约定/reloc/大帧/FP-RF 的 L1 编码 + L3 执行，**独立 oracle**）；lit 量产（骨架生成 + 期望值**从 `spec`/`contracts` 机械派生**、**禁反填**；快档入 `make check`、全量档 opt-in）；上游 IR 素材 + `lli` **值级对拍**；**Embench 接入**（board shim + 最小运行时 + `md5sum` 大端适配；首验收 = 最小基准 QEMU 正确退出码）。
**关联任务**：`TESTCASES-036t`、`TESTCASES-037t`、`TESTCASES-038t`、`TESTCASES-039t`、`TESTCASES-041t`

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tests/vectors/**`（新能力 L1/L3）、`tests/llvm/lit/**`（快档）、`tests/llvm/codegen/m6/**`、上游 IR 素材与 `lli` 对拍驱动、Embench 接入产物（`tests/**` 或 `components/embench-iot/**` 依赖）
- L1/L3 期望值**独立派生**（非从 LLVM/QEMU 反填）；计数由脚本/门控现场统计（**不写死**）
- 不回归：`make check`/`check-lit` EXIT=0
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）

## 完成区

**核验结论**：**通过**（关联任务 5/5 均 `已验证`；产出齐、oracle 独立、门控全绿；另闭合 1 处跨模块遗留——见「新发现」）。

**关联任务状态**：`TESTCASES-036t`/`037t`/`038t`/`039t`/`041t` 现场 `grep '**状态**'` 均 = `已验证`（5/5）。

**产出存在**（现场 `ls`）：
- L1 编码：`tests/llvm/lit/MC/DADAO/{m6-callconv.s,m6-ldst-symbol.s,m6-data-narrow-reject.s}`（符号偏移 `REL12`/`ABS12` 已随 `LLVM-065t` 转正、不再 `UNSUPPORTED`）；
- L3 执行：`tests/llvm/codegen/m6/**`（8 `.ll` + `expected.yaml`〔7 raw-bin〕+ `expected-elf.yaml`〔1 ELF〕）；
- lit 量产：快档 `tests/llvm/lit/MC/DADAO/gen-fast.s`（入 `make check`）、全量档 `tests/llvm/lit/MC/DADAO-gen/*.s`（12 文件，opt-in `check-lit-full`）；
- 上游 IR + `lli` 对拍驱动：`tests/llvm/ir-lli/{manifest.yaml,README.md}` + `tools/testcases/diff_ir_lli.py`；
- Embench 接入：`components/embench-iot/patches/examples/dadao/{boardsupport.c,h,README}.patch` + `src/md5sum/md5.c.patch` + `series`/`changelog.md`；`tests/scripts/embench_runtime.c` + `embench_include/*.h`。
（注：M6 L1/L3 向量实际落 `tests/llvm/**`；`tests/vectors/**` 为 M1/M2 ISA 编码层、M6 未改。）

**L1/L3 期望值独立派生**：`python3 tools/testcases/validate_m6_vectors.py` → `PASS (102 checks)` rc=0；无 `subprocess/Popen/os.system`；L1 编码派生自 `contracts/opcodes.yaml`、reloc 类型解析自 `.tao/knowledge/contract-elf.md §2.2`；L3 期望值主机侧 IR 语义重算（补码/IEEE-754/大端）。各任务书 oracle 证据见 `036t`/`038t`/`041t` 完成区。

**门控**（逐条 EXIT，一次一个 `make`）：`make check` **EXIT=0**（lit **89/89**）；`make check-lit` **EXIT=0**（89/89）；`make check-lit-full` **EXIT=0**（`check_lit_gen` 64 passed + `llvm-lit` 12/12）；`make check-no-residue` **EXIT=0**。

**执行向量重跑**：M6 raw-bin L3 **7/7**、M6 ELF L3 **1/1**（`run_codegen_e2e`/`run_elf_e2e --expected …/m6/…`）、`make test-codegen` **15/15**、`make test-elf` **5/5**。

**Embench 现场统计**：`-O0` **19/19**、`-O2` **19/19**（编译 rc=0，证据 `.work/log/llvm/LLVM-078t-evidence-functional.out`）；钉子③首验收 E2E：`-O0` 10/19 基准 QEMU `exit=0`（`TESTCASES-039t`）+ md5/gdata E2E `exit=0`。

**新发现/坑（跨模块遗留，已闭合）**：`diff_ir_lli.py` 结构闭包断言（§8.35）在核验时 **FAIL**——`LLVM-069t/071t/073t/074t/076t/077t/078t` 向 `tests/llvm/lit/CodeGen/DADAO/` 新增 8 个结构型 lit `.ll`（均无 `@main` 值通道）却未登记入 `tests/llvm/ir-lli/manifest.yaml`（`unclassified=8`）。**处置**：按既有 `no-value-entry` 口径补 8 条 `exclude`（`manifest.yaml` 仅此一处改动）⇒ 重跑 `diff_ir_lli` **PASS**（`on-disk=49 include=19 exclude=30 unclassified=0`，值级 **19/19 matched**）。

**遗留问题**：`036t` REL12/ABS12 已随 `LLVM-065t` 收口；`037t` `DADAO-gen` 完整性仅 opt-in；`038t` 驱动 opt-in；`039t` G1–G6 已由 `LLVM-070t…077t` 收口。`make test-m6` 接线归 `INTEG-025t`。

## 审阅记录

#### 第 1 轮 reviewer 验收
（审查者独立验证：关联任务状态、产出存在性、oracle 独立性、门控重跑、判决）
