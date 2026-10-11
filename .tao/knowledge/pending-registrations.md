> **升格指针**（INFRA-058t，用户 2026-10-11 裁定「被引用材料不得只放 `.work/`」）：本文档由 `.work/log/integ/` 下同名文件升格至 `.tao/knowledge/`（原 `.work/` 副本已移出，该目录 gitignored、不再保留）。
# 待登记（用户 2026-10-10 裁定「先只登记，暂不改」）

> 因 `LLVM-065t` 正在同一工作树跑（分支占用），本批**暂不切分支/不混提**；待其落地后的第一个 git 窗口，由 **architect** 正式写入 `.tao/knowledge/issues.yaml`（+ `milestones.md`「规划中」/`deferred`）并入库。

## R1 — 数据指示符口径（用户裁定方向已定，落地待批）

**用户原话/结论**：
- **`.word`/`.long` 语义在汇编与高级语言间不一致 ⇒ 完全禁用**；**连带 `.quad` 也不用**。
- 规范名 = **`.dd.b08` / `.dd.w16` / `.dd.t32` / `.dd.o64`**（`DADAO-11 §汇编兼容性`、`Toolchain-01 §7`）。
- **`.dd.128` 不需要**（实测 `llc` 对 `i128` 发**两条 `.quad`**，语义等价；`i128` 传参/返回本就不支持）。
- **`.align` 有歧义**（实测我们的 `.align N` = **字节数**，非 2^N）⇒ **删 `.align`，只留 `.p2align`**（2^N）。
- **范围未定**：`.byte`/`.short` 是否也一并禁（待用户裁定）；受理侧是否**拒绝** GAS 名（需先核实能否 target-scoped 实现，否则要动通用 MC 代码）⇒ 成本↑。

**已知事实（实测）**：
- `.word` 已被拒（`unknown directive`）；`.octa` 已被显式拒（提示 GAS 16 字节语义）。
- `.byte/.short/.long/.quad` 与 `.dd.b08/.dd.w16/.dd.t32/.dd.o64` **两套名字当前都能汇编**（各 rc=0）。
- `llc` 生成侧：`i8→.byte`、`i16→.short`、`i32→.long`、`i64/指针→.quad`、`i128→两条 .quad`；数据段对齐发 **`.p2align N, 0x0`**。
- 改动面：生成侧 = `DADAOMCAsmInfo` directive 串（target 内小改）；受理侧拒 GAS 名可能**需动通用 `MCParser/AsmParser.cpp`**；跟改面 = `tests/**`（lit CHECK 行/e2e `.s`/`tests/scripts/*.s）。
- **ADR 建议**：命中「外部契约 + 结论固化 + 跨模块」⇒ 建议**立 ADR**（用户尚未表态）。

## R2 — 真缺陷：`.p2align` 在可执行段使 `llvm-mc` 崩溃（**建议优先修**）

- **现象**：`.text` 内 `.p2align N`（N≥1）或 `.align N`（N≥2）⇒ `llvm-mc` **rc=134/141**，断言 `MCAssembler.cpp:588 The stream should advance by fragment size`；**`.rodata` 内同指令正常**（rc=0）。
- **最小复现**：`printf '.text\n.byte 1\n.p2align 3\n.byte 2\n' | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /tmp/x.o /dev/stdin`。
- **可疑根因**：`DADAOAsmBackend::writeNopData`（`Source: MCTargetDesc/DADAOAsmBackend.cpp:299`，**已实现**）行为不对，或对齐 fragment 尺寸算错。
- **影响**：真实 C 代码在 `.text` 内做块对齐即触发（`llc` 会发 `.p2align`）。
- **用户裁定**：本轮「先只登记，暂不改」⇒ **仅登记**；**待用户决定是否提前修**。

## R3 — 窄位指令利用不足（**M7 优化候选，非缺陷**；用户 2026-10-10 提问引出）

**ISA 事实（`contracts/opcodes.yaml`）**：SimRISC **8/16/32 位指令齐全**——算术有 `.sb/.sw/.st`（有符号）与 `.ub/.uw/.ut`（无符号）各 10–12 条；乘除有 `mul/div/rem × {ub,uw,ut,sb,sw,st,uo,so}`；且 **`mul.uo`/`mul.so` 为 4 操作数（128 位双目的），`mul.ut/uw/ub` 等为 3 操作数（单目的）**。

**实测（`llc -march=dadao -O2`）**：
- **窄位访存：已有效利用 ✓** —— `i8→ld.ub`、`i16→ld.uw`、`i32→ld.ut`（`setLoadExtAction`/`setTruncStoreAction` 登记为 Legal）。
- **窄位算术：未利用 ✗** —— `add8/add16/add32/add64` **全部**→ `add.uo`（64 位）。
- **窄位乘除：未利用 ✗ 且用重形式** —— `mul32` → **`mul.uo {rd0, rd8}, …`（128 位双目的）**，而 ISA 有单目的 `mul.ut`。

**根因**：后端**只注册 `MVT::i64` 为 legal**（`DADAOISelLowering.cpp:51 addRegisterClass(MVT::i64, GPRD)`），i8/i16/i32 一律 **promote 到 i64**；指令选择只登记 64 位模式。

**影响**：**正确性无影响 ✓**（promote + 截断/扩展语义正确）⇒ **不是缺陷、不阻塞 M6**；**性能待量化**——同 4 字节编码、同 64 位数据通路 ⇒ **加减/逻辑收益可能≈0**；**乘除最可能有收益**（省掉 128 位双目的形式）。

**建议（M7）**：① **先量化**（Embench/微基准对比 `mul.ut` vs `mul.uo`、窄 ALU vs `add.uo` 的周期与尺寸）；② 有收益才立项（把 i8/i16/i32 注册 legal + 增补 `Pat`/自定义 lowering，**改动面不小**：`CodeGen.td`/`ISelLowering`/`ISelDAGToDAG` + lit）；③ 收益≈0 ⇒ **不做**（避免过度设计）。
