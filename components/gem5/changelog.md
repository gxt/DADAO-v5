# gem5 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文，逐字保留>`；原表其余列各占一条缩进行（如 `  - 执行者：engineer`）。节 = `## M<k>`（节序 M1→M2→…），**节内按日期升序**；**新里程碑到来时在文末开新节**（不留空节）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M11

- **2026-11-01 GEM5-004t**
  - 摘要：**B0 解码核心 + 264 条断言**。新建 `components/gem5` 树形补丁集（**26 份** = 新增 24 + 修改 2：`src/arch/Kconfig`、`src/arch/SConscript`），在 gem5 v25.1.0.1 上注册 `USE_DADAO_ISA` / `build_opts/DADAO`；`src/arch/dadao/**` 提供纯 C++ 解码核心（`decode/{decode.hh,decode.cc}` + 生成的 `decode_table.inc`）与 gem5 `DadaoInst` 骨架：格式/字段/opcode/6 位子表（`[23:18]`）分派、`rule_refs` + `legality` 规则数据、264 条 ID/格式/字段/编码/批次断言、388 条非法/保留/身份回归（同编码异义 0x5E/0x5F、0x76；删除 cfxld/cfxst；老 swym/coarse-mask 回归）。执行语义不实现：解码成功 ⇒ `UnimplementedInstruction`，未匹配/保留 ⇒ `IllegalInstruction`（ILLI），不静默成功。批次边界 38/8/42/63/28/30/55 由矩阵 `contract_ref` 派生并断言。生成器 `tools/gem5/gen_decode_table.py`（`--check` 漂移门控）；`make build-gem5`（SCons 缺失 ⇒ rc=2 BLOCKED）、`make check-gem5-decode`。manifest 启用 gem5。
  - 执行者：engineer
