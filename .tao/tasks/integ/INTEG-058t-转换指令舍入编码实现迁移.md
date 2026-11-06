# INTEG-058t: 转换指令舍入编码实现迁移（LLVM/QEMU/gem5/tests）

**模块**：integ
**项目里程碑**：M11
**依赖**：`SPEC-194t`（规范/契约三分编码）、`ADR-0050`（Accepted）
**状态**：待开始

## 目标

把 `ADR-0050` 的三分编码落到实现与测试，使 C 的浮点/整数转换语义正确且两引擎一致：

- **15 条**（8 `f2i` + `fo2ft` + 6 条不精确 `i2f`）：低 6 位 = 六档 one-hot（`0x01` RNE / `0x02` RNA / `0x04` RTZ / `0x08` RUP / `0x10` RDN / `0x20` dynamic）
- **3 条精确转换**（`ft2fo`/`it2fo`/`ut2fo`）：低 6 位 SBZ（必须为 0）
- **4 条复制**（`ft2ft`/`fo2fo`/`rd2rf`/`rf2rd`）：保留 1–63 计数，编码不动

## 阶段（串行）

1. **LLVM**：MC/AsmParser/反汇编接受新语义；`FP_TO_SINT/FP_TO_UINT`（含 saturating）发 `0x04`；f32/f64 之间的 `FP_ROUND/FP_EXTEND` 与整→浮发 `0x20`（`ft2fo` 发 0）；更新 `tests/unit/llvm/lit/MC/DADAO{,-gen}` 期望与 `tests/case-ledger.tsv` 相关行。
2. **QEMU**：8 条 `f2i` 与 6 条 `i2f`、`fo2ft` 按字段方向（`0x20` 读 `rf0`）；`ft2fo`/`it2fo`/`ut2fo` 校验 SBZ；复制类仍按计数；NX/NV 按 D5。
3. **gem5**：同上（当前总是读 `rf0`，改为按字段）。
4. **tests/一致性**：补各方向/NX/OF/UF 断言（至少 RTZ/RNE/RUP/RDN 各一组，`f2i` 越界饱和+NV、`fo2ft` 溢出/下溢）；`tools/gem5/check_b7.py` 的规则计数更新；`GEM5-021t` 基线重跑（`gem5_only_fail` 的 9 个 `math/*` + `Olden/power` 应转绿）；parity 与 `node/arch` 269 例保持 0 diff。

## 范围 / 非范围

**在范围内**：`components/llvm-project/**`（MC/AsmParser/ISel/CodeGen + lit 期望）、`components/qemu/**`、`components/gem5/**`、`tests/unit/llvm/**`、`tests/case-ledger.tsv`、`tools/gem5/check_b7.py`、`tools/testcases`（仅向量/期望如需要）、本任务书、`milestones.md`。

**不在范围**：`spec/**` 与 `contracts/**`（`SPEC-194t` 已改）、复制类编码、块转换语义、其它 FP 指令。

## 验收标准

1. 汇编/反汇编：15 条接受六档、3 条要求 SBZ（非 0 ⇒ ILLI）、4 条保留计数；`llvm-mc` 与 lit 全绿。
2. 语义：同一 ELF 在 QEMU 与 gem5 上，`(long long)2.7 = 2`、`(long long)-2.7 = -2`；C cast 在 `fesetround` 改变后仍截断；`(float)d`/`(double)i` 跟随 `rf0`；各静态档结果符合方向定义。
3. `GEM5-021t` 基线：原 9 个 `math/*` + `Olden/power` 转 PASS 或给出真实失败归因；`qemu_only_fail` 仍 0。
4. parity `node/arch` 269 例 0 diff；`check-inst`/`check-arch`/`check-gem5-decode`/`check_b6`/`check_b7` 绿。
5. `make check`（L1）、`make check-modules`（L2）rc=0；源树 base+1 clean、`check-patch-tree` rc=0。
6. 反例：把 `f2i` 的 `0x04` 改成 `0x01`（或把 QEMU 改回恒截断）⇒ 对应语义探针/用例 FAIL；`cp`+`md5sum -c` 还原重建后回绿。
7. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务跨三组件，必须串行：LLVM 先出编码，QEMU/gem5 同时改；每阶段落日志与真实 rc。
- 旧编码（`immu6`=个数）作废；任何旧向量/ELF 需按新语义重生成，不得保留「双读」兼容模式。
- 若某条转换在 gem5 上暴露真实语义缺陷（非编码问题），保留最小复现并单列，不静默改测试期望。
