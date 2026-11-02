# gem5 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文，逐字保留>`；原表其余列各占一条缩进行（如 `  - 执行者：engineer`）。节 = `## M<k>`（节序 M1→M2→…），**节内按日期升序**；**新里程碑到来时在文末开新节**（不留空节）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M11

- **2026-11-01 GEM5-004t**
  - 摘要：**B0 解码核心 + 264 条断言**。新建 `components/gem5` 树形补丁集（**26 份** = 新增 24 + 修改 2：`src/arch/Kconfig`、`src/arch/SConscript`），在 gem5 v25.1.0.1 上注册 `USE_DADAO_ISA` / `build_opts/DADAO`；`src/arch/dadao/**` 提供纯 C++ 解码核心（`decode/{decode.hh,decode.cc}` + 生成的 `decode_table.inc`）与 gem5 `DadaoInst` 骨架：格式/字段/opcode/6 位子表（`[23:18]`）分派、`rule_refs` + `legality` 规则数据、264 条 ID/格式/字段/编码/批次断言、388 条非法/保留/身份回归（同编码异义 0x5E/0x5F、0x76；删除 cfxld/cfxst；老 swym/coarse-mask 回归）。执行语义不实现：解码成功 ⇒ `UnimplementedInstruction`，未匹配/保留 ⇒ `IllegalInstruction`（ILLI），不静默成功。批次边界 38/8/42/63/28/30/55 由矩阵 `contract_ref` 派生并断言。生成器 `tools/gem5/gen_decode_table.py`（`--check` 漂移门控）；`make build-gem5`（SCons 缺失 ⇒ rc=2 BLOCKED）、`make check-gem5-decode`。manifest 启用 gem5。
  - 执行者：engineer

- **2026-11-02 GEM5-005t**
  - 摘要：**scaleB C1 与 sc rd0 解码更新**。按 SPEC-181t 重生成 `components/gem5` 解码表/断言：`ftsclb`/`fosclb` 第三操作数由 `rfhd/rf` 改为 `rdhd/rd`（编码/opc/ha 不变，旧 rf 字段成为负例守护）；12 条 `sc.*` 的 `rdhb != rd0`（`dst_rd0`）写入 legality/rule 断言，`rdhc=rd0` 保持合法。生成器新增 SPEC-181t 守护与 28 条合法性用例（sc dst rd0⇒ILLI、rdhc=rd0 合法、scaleB 指数 rdhd=0 合法、scaleB dst rf0⇒ILLI）+ 2 条旧 rf 负例；断言表增加 `rules` 列并逐行校验。`make check-gem5-decode` 264/264 + 388/388 + 28/28 + 2/2。执行语义仍在 B1–B7。
  - 执行者：engineer

- **2026-11-02 GEM5-006t**
  - 摘要：**B1 取数存数执行核心（38 条）**。新增纯 C++ 执行核 `src/arch/dadao/exec/b1.hh` / `b1.cc`（38 个 id 显式分派：RD/RB/RA/RF × 单/多 load-store），实现 48 位有效地址与回绕、大端字节序、符号/零扩展、块传输（原始 rdhc 快照、i 递增、先读后写、immu6/范围 ILLI、宽度 MALIGN）、`rd0`/`rb0`/`ra0`/`rf0` 边界（rf0 目的 FCSR 写掩码、`ld.t`/`ldm.t` 高 32 位保持）；`inst.cc` 增加 `Gem5B1Context` 适配（int/float 寄存器组、`readMem`/`writeMem`）与 `executeB1` 分派，`faults.hh` 新增 `MalignInstruction`（先 panic 报地址/宽度），`SConscript` 加入 `exec/b1.cc`；B2–B7 仍返回 `UnimplementedInstruction`。组件内断言 `exec/b1_test.cc`（38/38 覆盖 + ILLI/MALIGN/端序/块/rf0/高位立即数）由新增 `tools/gem5/check_b1.py` 编译运行，不新增 `tests/**`、不改解码表。
  - 执行者：engineer

- **2026-11-02 GEM5-007t**
  - 摘要：**B2 16 位立即数执行核心（8 条）**。新增纯 C++ 执行核 `src/arch/dadao/exec/b2.hh` / `b2.cc`（按 `entry->id` 分派 8 条 rwii：`or.w`/`andn.w`/`set.zw`/`set.ow` 的 RD/RB 变体与 `set.w` RF；`wpN` wyde 选择、`immu16` 无符号 16 位分片、其余 48 位清 0/置 1/保持；`rd0`/`rb0` 目的静态 ILLI；`set.w rf0` 按 FCSR 写掩码，`wp1`/`wp3` 完全写无效）。新增共享头 `exec/common.hh`（`Fault` 增 `NotB2`、`Bank`/`Target`/`RegAccess`/`fieldValue`），`b1.hh` 改为派生 `RegAccess`、`b1.cc` 改用 `fieldValue`（等价重构，B1 2102 PASS/0 FAIL 不变）；`inst.cc` 增加 batch 2 分派（共用 `Gem5B1Context`），`SConscript` 加入 `exec/b2.cc`，`inst.hh` 头注释更新为 B0+B1/B2。组件内断言 `exec/b2_test.cc` 由新增 `tools/gem5/check_b2.py` 编译运行（8/8、wp0–wp3×立即数分片、48 位清置保持、ILLI/单写、rf0 掩码、rule/spec_cite 对照），不改 `tests/**`、解码表与 B3–B7。
  - 执行者：engineer
