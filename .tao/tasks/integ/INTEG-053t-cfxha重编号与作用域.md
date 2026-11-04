# INTEG-053t: cfxha 重编号与 per-task/per-system 作用域统一

**模块**：integ
**项目里程碑**：M11
**依赖**：`QEMU-082t`、`GEM5-019t`、`SPEC-183t`（均已 `已验证`：QEMU/gem5 Node/Tiny 与 Machine-v5 基线）；串行约束 `SPEC-184t`、`SPEC-186t`（同改 `DADAO-12`/`Machine-v5` 与 `manifests/spec-readonly.lock.toml`，三者**不得并发**；本任务可在其前或其后执行，最后由执行顺序末尾的任务基于最终文本重算锁）
**状态**：待开始

## 执行环境
本地（仓库根）。QEMU/gem5 组件源树为 `base+1` 单提交、`git status` 干净；实现落任务分支 `INTEG-053t`，不 merge、不 push。

## 用户口径（本任务依据）

用户已明确（2026-11-03/05，原话摘要已落 `.tao/knowledge/discussing.md`「2026-11-03 cfxha 重编号与作用域」条）：

- M11 收尾前统一重排一次 cfxha：`cfx_pmem` → **32**、`cfx_llc` → **33**、`cfx_time` → **34**。
- 作用域：`cfx16`–`cfx31` = **per-task**；`cfx32`–`cfx63` = **per-system**；`cfx0`–`cfx15` 保持 per-hart。
- per-task 含义：内核或进程需**申请后使用**，用完**释放**；使用过程中发生上下文切换不影响该 cfx，**不需要**上下文切换保存/恢复。
- 该改动跨 spec/contracts/QEMU/gem5/tests，必须统一，不能零散改号。
- 不改退出码设计、不改 `DADAO-12 §5.2` 同步异常路由（仅允许编号字面替换）、不改 Node/Tiny 地址几何、不改 E2E 语义。

## 问题根源（现场核对，2026-11-05）

1. **DADAO-12 §1 的 cfxha 表仍是旧号**：`16 llc`、`17 pmem`、`18 time`，保留集为 `6–14、19–61`；§1 作用域表仍是 `cfx0–cfx15 per-hart`、`cfx16–cfx63 per-system`，没有 per-task。
2. **编号散落到多处真源/投影**：DADAO-12 §2.1 的 pmem SRAM 表与 §4.9 的 `cfxha 17`；Machine-v5 的 `17 / pmem` 与 SRAM 基址；DADAO-22 的 `cfx_time = cfx18` 示例；`contracts/opcodes.yaml` 的 5 条 `15–18` 合法式；`legality_rules.yaml` 的保留集/已分配集。**SimRISC-11/00 不再列具体编号**：ISA 层只保留“保留 cfxha 由 SEE/DADAO-12 定义，指向保留 cfxha ⇒ ILLI”的描述性规则。
3. **实现硬编码**：QEMU `DADAO_CFXHA_PMEM=17`/`DADAO_CFXHA_TIME=18`、`DADAO_CFX_IS_RESERVED`、`dadao_cfxha_map`；gem5 `CfxhaPmem=17`/`CfxhaTime=18`、`kCfxhaMap`、`nodeCfxReserved`、`kTraceCfxha`、`cg7SpaceReg` case 17、`fs.py`/`DadaoNodeTlb.py` 的 pmem 基址；生成的 QEMU/gem5 decode 表也内嵌旧合法式。
4. **测试/探针**：`smon.S` 9 处硬编码 `0x47ff`；`machine-*.inc` 由生成器产出 `PMEM_BASE=0x47ff00000000`；探针 `PMEM_BASE`、`PMEM_HA=17`、`TIME_HA=18`、`cfx16 (llc)`、`FULL_ADDR[17]`；lit `cfx2-space-stride.s` 硬编码 cfxha=17 的编码 `7a44c0c1`；umon 向量/期望说明写 `cfxha 16`。
5. **pmem 核内基址随 cfxha 变化**：`(17<<42)|0x3ff_0000_0000 = 0x47ff_0000_0000`；改为 32 后为 `(32<<42)|0x3ff_0000_0000 = 0x83ff_0000_0000`。这是 cfx 内部窗口地址，**不是** Node/Tiny 的 BootROM/RAM/hmon/smon 几何。
6. **保留集必须同步变化**：`16–18` 让出后，`16–31` 整段成为未分配的 per-task 段，`35–61` 仍保留；否则 `trap cfx16` 等会错误地进入“已分配”路径。

## 目标

1. **单一新编号真源**：DADAO-12 §1 表改为 `32 pmem / 33 llc / 34 time`，保留集改为 `6–14、16–31、35–61`；§2.1 pmem 行与 §4.9 改为 cfxha 32、核内基址 `0x83ff_0000_0000`；append 一条未发布变更记录（不重写旧记录）。
2. **三段作用域**：DADAO-12 §1 增加 `cfx16–cfx31 per-task`、`cfx32–cfx63 per-system` 两行，并给出 per-task 的申请/释放/不随上下文切换保存恢复定义；`cfx0–cfx15 per-hart` 不变。
3. **契约/编码真源同步**：`SimRISC-11` 与 `SimRISC-00` **删除具体 cfx 编号/范围**，只保留描述性规则（“保留 cfxha 由 SEE/DADAO-12 定义；指向保留 cfxha ⇒ ILLI”）；`contracts/opcodes.yaml` 的合法式、`legality_rules.yaml`、`contract-isa`/`contract-see` 投影、Machine-v5/DADAO-22 中与新号有关的字面同步；所有生成物由各自生成器重生成，且生成器不得把具体保留集重新写回 SimRISC。
4. **QEMU/gem5 实现同步**：pmem=32、time=34、llc=33（llc 仍未实现，访问 ⇒ `CFXREG`）；保留集 `6–14、16–31、35–61`；pmem SRAM guest 基址 `0x83ff_0000_0000`；QEMU/gem5 Node/Tiny 构建与代表测试通过。
5. **测试资产同步**：bootrom、机器头、探针、lit、向量、`case-ledger` 按新号重生成/更新；Tiny 无 cfx 的语义不变，Node 的 cfx/PTW/DMA/时间语义不变。
6. **只读锁**：本任务改到的 spec 册（`DADAO-12`、`DADAO-22`、`Machine-v5`、`SimRISC-00`、`SimRISC-11`）同笔重算 sha256 并写授权注记；与 `SPEC-184t`/`SPEC-186t` 串行，不并发改锁。
7. 门控全绿、至少两处注入可达 FAIL、证据与完成区真实 rc；状态置 `待验收`。

## 接口规范

### 1. 新编号表（唯一权威值）

`spec/DADAO-12` §1 的 cfxha 表按下列值改写（其余行不动）：

| cfxha | cfxname | 说明 |
|:---:|------|------|
| 16-31 | reserved | 保留（per-task 段，未分配） |
| 32 | pmem | 物理存储器管理 |
| 33 | llc | 最后一级缓存，跨 hart 共享 |
| 34 | time | 全局时间计数器 |
| 35-61 | reserved | 保留，未定义 |

DADAO/合约/实现层的保留集统一写 **`6–14、16–31、35–61`**，已分配/合法集统一写 **`0–5、15、32–34、62、63`**（0 = all cfx，汇编别名 `cfx0`/`cfx_umon`）。`SimRISC-11/00` 不写具体范围，只保留“由 SEE/DADAO-12 定义”的描述。

### 2. 作用域表与 per-task 定义（DADAO-12 §1）

作用域表改为三行：

| 资源 | 作用域 |
|------|:--:|
| rd/rb/rf/ra、inner_* | per-hart |
| cfx0-cfx15 | per-hart |
| cfx16-cfx31 | per-task |
| cfx32-cfx63 | per-system |

表后必须有一段逐字表达（语义等价即可，但“申请/释放/不随上下文切换保存恢复”三点不得缺）：

> `per-task`：`cfx16`–`cfx31` 由内核或进程在**申请后使用**，使用完毕**释放**；持有期间即使发生进程上下文切换，该 cfx 的状态与运行不受影响，**不需要**随上下文切换保存/恢复。

### 3. 地址（只改 cfx 内部窗口）

- `cfx_pmem` 的 64 KiB SRAM 内部偏移仍为 `0x3ff_0000_0000`；完整核内基址 = `(32 << 42) | 0x3ff_0000_0000 = 0x83ff_0000_0000`。
- Node/Tiny 的 BootROM、RAM、hmon/smon SRAM、entry/SP、页表几何**一律不动**；Tiny 仍不实现任何 cfx。
- cfx_pmem 主机侧 SRAM backing、DMA 的 CFX/PA 位宽与语义不变。

### 4. 精确改动面（按真源/生成物分类）

**spec（只读册，改后重算锁）**

- `spec/DADAO-12-SEE-主管系统运行环境.md`：§1 表/作用域/per-task 定义、§2.1 pmem 行与说明、§4.9 `cfxha 17`、§5.2 中的保留集字面（**只替换编号，不改路由/步骤/屏蔽语义**）、附录 `0.7.3-rc` 追加一条（不重写旧条目）。`§5.2` 若与 `SPEC-186t` 重叠，按串行顺序后者基于前者最终文本只做编号字面替换。
- `spec/DADAO-22-SBI-主管系统二进制接口.md`：`cfx_time = cfx18` 示例注释改 34；附录 `0.7.3-rc` 追加一条。§8/§9/§10 已分别写明 llc/time 为 per-system；pmem 若补作用域，只写“per-system”，不改 SBI 语义。
- `spec/Machine-v5-测试机运行环境.md`：Node 表的 `17 / pmem` → `32 / pmem` 与 SRAM 基址；§1.1/§1.2/§2 中的 `cfx17`、保留集、附录 `0.3.2-rc` 同步。Node/Tiny 几何与装载语义不动。
- `spec/SimRISC-11-核芯功能扩展指令.md`：删除 §1/§4/§5/§6 中的具体 cfx 编号/范围（含 `6–14、19–61`），改为“保留 cfxha 的分配由 SEE/DADAO-12 定义；指向保留 cfxha ⇒ ILLI”的描述性规则；附录 B 由 `gen_legality_list.py --apply` 重生成，但生成器必须跳过/改写字面范围，不得把具体保留集重新写回本册。
- `spec/SimRISC-00-指令系统设计.md`：删除 `0.5.6-rc` 变更记录中的具体 `6–14、19–61`，改为“保留 cfxha 具体分配由 SEE/DADAO-12 定义”；不新增具体范围，不把范围写回 ISA 册。

**contracts / 生成物（禁手改生成物）**

- `tools/spec/generate_opcodes.py`：`CFX_RESERVED_EXPR` 改为 `cfxha <= 5 || cfxha == 15 || (cfxha >= 32 && cfxha <= 34) || cfxha >= 62`，注释同步；运行生成器写 `contracts/opcodes.yaml`。
- `contracts/legality_rules.yaml`：`encode_cfx_reserved` 的 description 改为新保留集，已分配集改为 `1–5、15、32–34、62、63`。
- `tools/spec/gen_legality_list.py`：`encode_cfx_reserved` 摘要改新保留集；`--apply` 重生成各册 LEGALITY 段，`--verify` 回归；**生成 SimRISC-11 附录时不得写入具体 cfx 编号/范围**，改为描述性说明。
- `tools/spec/check_legality_invariants.py`：`CFX_RESERVED_EXPR` 与 description 断言 token 改 `6–14`/`16–31`/`35–61`。
- `.tao/contracts/contract-isa.md`：4 处保留集（§ legality 说明/屏障/核芯功能扩展）改新集。
- `.tao/contracts/contract-see.md`：`cfx_pmem`/`cfx_time` 的 cfxha 与 SRAM 基址、保留集、测试机 cfx 实现集（`cfx17`/`cfx18` → `cfx32`/`cfx34`）同步。
- `tools/spec/gen_cfx_aliases.py` 与 `tools/llvm/gen_cfx_alias_table.py`：不手改输出，运行生成器重生成 `.tao/contracts/contract-cfx-aliases.md` 与 `contracts/cfx-aliases.txt`（标量 32/33/34、寄存器行、`DADAO-12` 行号随之变化）。
- `tools/qemu/generate_decodetree.py`、`tools/gem5/gen_decode_table.py`：运行生成器重生成 QEMU `insn.decode` 与 gem5 `decode_table.inc`/`decode_assertions.inc`/根级 `decode-assertions.tsv`；`--check` 必须回绿。

**QEMU（`components/qemu/**`，改后重导出补丁）**

- `cpu.h.patch`：`DADAO_CFXHA_PMEM` 32、`DADAO_CFXHA_TIME` 34（llc 无需新增 define，仍不实现）；`DADAO_CFX_IS_RESERVED` 改三段；`DADAO_NUM_CFX`/map 注释同步。
- `helper.c.patch`：`dadao_cfxha_map` → `{0,1,2,3,4,15,32,34,63}`；PMEM_DMA cause 表注释、异步仲裁“按目标 cfxha 升序（15→32）”注释、reserved/phmem 注释同步；pmem SRAM 路由仍按 `DADAO_CFXHA_PMEM`。
- `cpu.c.patch`、`insn_trans/trans_ctrl.c.inc.patch`、`hw/dadao/dadao-machine.c.patch`：所有 cfxha 比较/注释同步；**不得**按字面盲替换寄存器号 `17`/`18`。
- 补丁由 `tools/infra/make_patch.py qemu` 重导出，源树收敛为 `base+1`；重建 `qemu-system-dadao` 并 `make install-host`。

**gem5（`components/gem5/**`，改后重导出补丁）**

- `node_cfx.hh.patch`：`CfxhaPmem=32`、`CfxhaTime=34`；`kCfxhaMap`、实现注释、`nodeCfxReserved`（`6–14`、`16–31`、`35–61`）、`cg7SpaceReg` 的 pmem case 32 同步。
- `node_cfx.cc.patch`：`kCfxhaMap`、reserved 判定、pmem case、cg7 case 同步；异步仲裁顺序/注释同步。
- `isa.cc.patch`：`kTraceCfxha` → `{0,1,2,3,4,15,32,34,63}`。
- `exec/b6.cc.patch`、`exec/b6_test.cc.patch`：reserved 判定与“合法边界”矩阵改 `{0,5,15,32,33,34,62,63}`、保留边界 `{6,14,16,31,35,61}`；原先用 `cfxha=16/17` 的正例改为新号（**语义：16 现为保留，不能再作正例**）。
- `configs/dadao/fs.py.patch`、`DadaoNodeTlb.py.patch`、`node_tlb.cc.patch`：pmem guest 基址 `0x83ff_0000_0000`，注释 cfxha 32。
- 补丁由 `tools/infra/make_patch.py gem5` 重导出；`make build-gem5` 通过。

**tests/tools（按语义逐处改，禁全文件盲替换 17/18）**

- `tests/shared/bootrom/step5/smon.S`：9 处 `LD64 ..., 0x47ff, ...` → `0x83ff`（字节序分段不变）。
- `tests/shared/bootrom/step5/hmon.S`：使用 `PMEM_BASE` 宏，不手改；由生成器更新。
- `tools/testcases/arch/gen_machine_inc.py`：`PMEM_BASE` → `0x83ff00000000`；重生成 `tests/shared/asm/machine-{tiny,node}.inc`。
- `tools/testcases/arch/node_probe_prelude.py`：`PMEM_BASE` → `0x83ff_0000_0000`，注释 cfxha 32。
- 探针：`min_rom_probe_integ042t.py`、`044t`、`046t`、`047t`、`048t`、`049t`、`050t`、`051t`、`async_094t.py` 中的 `PMEM_HA/PMEM_BASE/TIME_HA`、`FULL_ADDR[17]`、`cfx16 (llc)`、bit15/bit17/bit18 掩码、`OFF_FH18` 等逐处改；`integ050t` 的 `TIME_HA=34`、`OFF_FH34`、hmon mask bit34；`integ051t` 的 PMEM 目标 32、优先级注释“15 先于 32”。
- `tests/unit/llvm/lit/MC/DADAO/cfx2-space-stride.s`：`cfx_pmem_start[3]` 的编码期望按 `cfxha[23:18]=32` 重算（不得沿用 `7a44c0c1`），注释同步；`check-lit-bytes`/lit 回归。
- `tests/arch/umon/m5_perm_unimpl_cfxreg.s` 与 `expected.yaml`：`cfx_llc` 的 cfxha 说明改 33；`m5_perm_reserved_illi.s`/`README-m5.md` 的保留集改新集。
- `tests/inst/base/reserved.yaml`：CFXMEM 边界覆盖扩为 6 例——`6`、`14`、`16`、`31`、`35`、`61`；注释/notes 同步；`tests/inst/inventory.md` 相应改为 6 条。
- 生成向量：`tools/qemu/generate_atomics_vectors.py`、`tools/testcases/generate_ctrl_jump_call_ret.py` 的保留集注释更新后重生成 `tests/inst/atomics/atomics-fence.yaml`、`tests/inst/base/ctrl-ret.yaml`；`tools/testcases/validate_m5_vectors.py` 注释同步。
- `tests/case-ledger.tsv`：用例增减/改名后 `python3 tools/infra/check_case_ledger.py --write` 重生成。
- `tools/testcases/arch/README.md`、`tests/arch/README.md` 及任务提及的 cfxha 说明同步。

**明确不改**

- `components/llvm-project`：cfx 别名是运行时数据表，改号不重建 LLVM；只需 `make install-cfx-aliases` 更新构建树/安装根副本。
- `.tao/adr/**`：ADR-0042/0043/0049 的 `cfx17`/旧地址是历史决策记录，不改写；如需以 ADR 固化新编号，另立任务/ADR（本任务不建）。
- `.tao/archive/**`、`components/{qemu,gem5,llvm-project}/changelog.md`、历史任务书：保留旧号，作为历史。
- `DADAO-12 §5.2` 的路由/步骤/屏蔽语义、退出码表、Node/Tiny 几何、E2E 判据。

## 实施顺序

1. **A 真源与契约投影**：DADAO-12/SimRISC-11/SimRISC-00/DADAO-22/Machine-v5 正文 + `legality_rules.yaml` + `contract-isa`/`contract-see`（`generate_opcodes.py` 会读 `contract-isa`，必须先改）。
2. **B 生成链**：`generate_opcodes.py` → `gen_legality_list.py --apply` → `gen_cfx_aliases.py` → `gen_cfx_alias_table.py` → QEMU/gem5 decode 生成器 → `gen_machine_inc.py`；各自 `--check/--verify` 回绿。
3. **C QEMU**：改源树 → `make_patch.py qemu` → `make build-qemu JOBS=8` → `make install-host`。
4. **D gem5**：改源树 → `make_patch.py gem5` → `make build-gem5 JOBS=8`。
5. **E 测试资产**：bootrom/机器头/探针/lit/向量/ledger → `make build-bootrom`。
6. **F 门控与注入**：见下；失败按“保留现场 → 自行处置 → 有据重试并记次数”推进。
7. **G 只读锁**：在本任务实现与门控全部通过后，按串行顺序重算 5 册 sha256 并写授权注记；若 `SPEC-184t`/`SPEC-186t` 后执行，由后者基于最终文本重算（本任务不抢占）。

## 验收标准

1. **新号一致**：`spec/DADAO-12`、`Machine-v5`、`DADAO-22`、`contract-isa`、`contract-see`、`contracts/cfx-aliases.txt`、`.tao/contracts/contract-cfx-aliases.md`、QEMU/gem5 实现与测试资产中，pmem/llc/time 的 cfxha 分别为 32/33/34；`cfx16`/`cfx17`/`cfx18` 不再被当作已分配 cfx 使用（历史记录除外）。
2. **保留集一致**：DADAO/合约/实现等活文件统一为 `6–14、16–31、35–61`；`encode_cfx_reserved` 合法式为 `cfxha <= 5 || cfxha == 15 || (cfxha >= 32 && cfxha <= 34) || cfxha >= 62`；边界测试覆盖 6/14/16/31/35/61。`SimRISC-11/00` 必须不含具体 cfx 编号/范围，只含描述性规则。
3. **作用域落地**：DADAO-12 §1 含三段作用域与 per-task 定义；活文件中不再出现“cfx16–cfx63 per-system”或“0–15 每核、16–63 全系统”的旧表述。
4. **地址自洽**：`(32<<42)|0x3ff_0000_0000 == 0x83ff_0000_0000`；QEMU/gem5 的 pmem SRAM 访问/越界 `CFXMEM`/DMA 双向搬运全部通过；Node/Tiny 几何常量逐项未变。
5. **全局扫描**：对 `spec/ contracts/ .tao/contracts/ components/qemu/ components/gem5/ tests/ tools/` 运行 `git grep` 扫描下列模式，命中必须清零或逐条登记为“历史/说明”并给文件:行：
   - `cfx16|cfx17|cfx18`（含 `cfxha 16/17/18`）；
   - `0x47ff|0x47FF`；
   - `19–61|19-61`（活文件）；
   - `15–18|15-18`、`cfxha >= 15 && cfxha <= 18`；
   - `cfx16-cfx63|16–63`（作用域旧表述）。
   豁免：`.tao/archive/**`、`.tao/adr/**`、各 `changelog.md`、spec 附录历史条目、历史任务书。
6. **QEMU**：`make build-qemu JOBS=8`、`make install-host`、`make check-arch`（Node 全 cfx 探针）、`make check-inst`（Node 全量 + Tiny 子集）均 rc=0；关键探针（integ042t/046t/047t/049t/050t/051t）逐项 PASS。
7. **gem5**：`make build-gem5 JOBS=8`、`make check-gem5-decode`、`python3 tools/gem5/check_b6.py --source <gem5 源树>` rc=0；Node FS 代表（arch 10/10、cfx 探针）与 Tiny FS 代表（inst 子集）按 GEM5-015t/016t 口径通过，且 `fs.py --profile {tiny,node} --dump-geometry` 与 `machine-profiles.yaml` 逐项相等。
8. **门控**：`make check`（L1）rc=0；至少包含并通过 `check-interface`、`check-spec-readonly`、`check-spec-drift`、`check-spec-refs`、`check-spec-numbering`、`check-spec-changelog`、`check-legality-drift`、`check-legality-invariants`、`check-asm-prose`、`check-cfx-aliases`、`check-cfx-alias-table`、`check-cfx-vectors`、`check-tests-index`、`check-case-ledger`、`check-milestones-fresh`、`check-decodetree-repro`、`validate-encoding`、`check-instrinfo`、`check-isa-coverage`、`check-patch-tree`、`check-source-state`、`check-no-residue`。
9. **至少两处注入可达 FAIL**（每处：注入 → 门控/探针 FAIL（rc≠0）→ `cp` 备份 + md5 还原 → 回绿；禁 `git checkout/restore/stash/show`）：
   - A：把 QEMU `DADAO_CFXHA_PMEM` 改回 17（只改一处）⇒ `make check-arch` 或 `integ049t` `space_pmem` FAIL；
   - B：把 `contracts/opcodes.yaml` 的合法式改回 `(cfxha >= 15 && cfxha <= 18)` ⇒ `check-legality-invariants`（或 `m5_perm_reserved_illi`）FAIL。
10. **只读锁**：本任务改到的 5 册 sha256 与当前文本一致，`make check-spec-readonly` rc=0；授权注记含日期与用户口径摘要；未改的册 sha256 不变。
11. **证据/完成区**：证据脚本 + 日志 + 真实 `*_EXIT` 落运行期目录，完成区只放结论与证据位置（≤30 行）；未提交、未 push；状态 `待验收`。

## 说明

- 本任务**不是**逐文件盲替换：`17`/`18` 同时可能是寄存器号、位索引、版本号、偏移；每处必须按语义判定并在完成区给出“改/不改”理由（至少覆盖 `min_rom_probe_integ042t.py`、`integ050t.py`、`integ051t.py`）。
- 生成物一律由生成器重生成；手改生成物视为未完成。生成器源（opcodes/legality/alias/decode/machine-inc）与输出必须同笔提交。
- 与 `SPEC-184t`/`SPEC-186t` 的锁冲突：严格串行；本任务先落地实现、锁更新按顺序执行；不得在对方未收口时并发改 `manifests/spec-readonly.lock.toml`。
- `docs/DDLN`（C001/F003）与 `docs/Process-09` 中“0–15 每核、16–63 全系统”的面向读者说明，如仍为旧两段，允许同笔做最小文字同步（非门控、非验收硬项）；不得改其技术结论。
- 若实现中发现 spec/契约语义确实无法自洽（例如某测试必须保留旧号才能表达），保留现场并留问，不自行改语义。
