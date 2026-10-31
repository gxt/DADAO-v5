# SPEC-180t: escape 只允许偏移 0 / +4

**模块**：spec
**项目里程碑**：M10
**依赖**：`SPEC-177t`（已验证，SEE/SBI 现行口径）、`INTEG-045t`（已验证，cfx 指令清理）；决策依据 **ADR-0004 D5.3**（SBZ 非零 ⇒ ILLI，架构自定义）、**ADR-0045 D8**（escape：偏移为编译期固定立即数）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户已确认的设计（原样落纸）

> `escape` 限制：`imms18[0]` 只允许 0/1，`imms18[17:1]` SBZ；汇编器拒绝非法值，QEMU 执行非法值 ⇒ `ILLI`；`excp_cause_ip` 仍 RW，不构成任意返回安全边界。

## 执行范围（主会话按已确认设计拟定）

> 落地上述设计的必要改动：spec 正文（仅 escape 偏移合法值/异常语义/表）、contracts、LLVM 汇编器、QEMU 执行期检查、测试向量/lit；**不改** `excp_cause_ip` RW、不改异常帧恢复、不改 SBI 示例（除必要合法性）。

> 说明：本任务书不新增用户原话；上述引文即本任务对 spec 4 册改动的授权依据。若执行时认为授权不足，engineer 停并索取，不自行扩大范围。

## 背景

现行 `escape` 的偏移合法集是「`imms20 ∈ [-524288, 524284]` 且 `%4==0`」（编码 `imms18` 是 **18 位有符号**指令字偏移），等价于 **±512 KiB 相对跳转**：`DADAO-12 §5.1` 的「常见用法表」第 3 行明文写着「跳过 N 条指令（N 可为负数表示回退）| `escape cfxha, [excp_cause_ip, N*4]`」。而 `escape` 实际只有两种语义：**重试**触发指令（偏移 0）与**跳过**它（偏移 +4）。

放宽的合法集带来两处问题：① 语义上把「异常退出」放大成任意相对控制转移，与「偏移是编译期固定立即数、不支持任意地址跳转」的设计意图自相矛盾；② 编码层 18 位有符号解释需要额外说明，未使用位没有 SBZ 约束，手工编码可写入任意值。

本任务把合法集收窄为 **{0, +4}**，未使用位定为 **SBZ（非零 ⇒ ILLI）**，并在汇编器与 QEMU 两侧机械落实。**注意边界**：`excp_cause_ip` 仍是 RW（`DADAO-12` L382「软件可写」），软件写该寄存器仍可任意跳转 ⇒ 本任务**不是**安全边界改造，只把「编码/汇编期可表达的偏移」钉死为 0/+4。

## 目标（范围）

### 1. spec 正文（4 册）

1. **`spec/DADAO-12-SEE-主管系统运行环境.md` §5.1**（现 L755–L761）：
   - 参数段改为：合法值**只有 0 与 4**（字节，`imms20`）；编码层 `imms18 = imms20 >> 2 ∈ {0,1}`（`imms18[0]` = 字节偏移 bit2）；`imms18[17:1]` 为 **SBZ**，手工编码非零 ⇒ `ILLI`。
   - **常见用法表**：删除第 3 行（`N*4` / 负回退）；保留「0 = 重试触发指令」「4 = 跳过触发指令」两行。
   - §5.3 步骤 0 与伪代码：在同一处（目标/帧检查，**任何状态切换之前**）补 `imms18[17:1] != 0 ⇒ ILLI`。
2. **`spec/SimRISC-11-核芯功能扩展指令.md` §3 退出指令**（现 L44 散文）：`imms20` 由「字节，须 `%4==0`」改为「**只允许 0 或 4**」；补 `imms18` 位域口径（`[0]` ∈ {0,1}、`[17:1]` SBZ 非零 ⇒ ILLI）。
   > **只改散文**：本册 L143–L154 是 `ASSEMBLY_LIST` 生成块、L156– 起是 `LEGALITY` 生成块，**禁止手改**；后者只能经 `contracts/opcodes.yaml` + `tools/spec/gen_legality_list.py --apply` 重生成。
3. **`spec/Toolchain-01-汇编语言.md` §3.2（现 L43）/§5（现 L172）**：`escape` 的 `imms20` 校验由「`%4==0` 与范围」改为「**只接受 0 与 4**，其它值报错」；「单位字节、右移 2 位写入 `imms18`」与 ×4 组映射不变。
4. **`spec/Machine-01-测试机运行环境.md` §4.2**（现 L100）：同步合法集与 ILLI 口径（本册现为 0.3.2-rc）。

### 2. contracts（机器可读 + 人读）

5. **`contracts/opcodes.yaml::escape_ciii_cfx`**：
   - `legality` 增加一条 `imms18[17:1] == 0`（写法对齐同文件 `fence_ciii_cfx` 的 `immu18[17:12] == 0`）；
   - `rule_refs` 增加既有规则 **`encode_sbz`**（`contracts/legality_rules.yaml`：`fault: ILLI`、`kind: static`、`status: active`、ADR-0004 D5.3）；
   - `op/mask/value/fields` **不动**（`mask 0xFF000000`、`value 0x7E000000`）；`imms18.signed: true` **保留**（合法集收窄后符号性无实际影响，改它会牵动派生脚本）。
6. **`contracts/legality_rules.yaml::encode_sbz`**：`description` 的枚举补一句「`escape` 的 `imms18[17:1]`（`escape` 合法偏移 0/+4）」。**不新增规则 id**。
7. **重生成生成物**（逐个 `--apply` 后 `--verify`，不得手改）：
   - `python3 tools/spec/gen_legality_list.py --apply` ⇒ `spec/SimRISC-11` 附录 B 的 `encode_sbz` 行由「`fence_ciii_cfx`（1 条）」变「`escape_ciii_cfx`, `fence_ciii_cfx`（2 条）」；
   - `python3 tools/llvm/gen_asm_list.py --apply`（`--verify` 现场判定是否需要）；
   - `.tao/contracts/contract-asm-list.md` 投影同步。
8. **人读合约**：`contract-isa.md` §13.6（L1206）、`contract-see.md` §4（L65）、`contract-asm.md` §4/§5（L175）——「须 `%4==0`」改为「只允许 0 或 4；`imms18[17:1]` SBZ 非零 ⇒ ILLI」，保留原有 spec 引用。

### 3. LLVM 汇编器

9. `DADAOAsmParser.cpp` 的 `escape` 分支（现两条校验：`Bytes % 4 != 0`、`Bytes < -524288 || Bytes > 524284`）改为**只接受 0 与 4**：
   - `Bytes == 0 || Bytes == 4` ⇒ 通过，`imms18 = Bytes >> 2 ∈ {0,1}`；
   - 其它（`2`/`6`/`8`/`-4`/`-8`/`524288`/非 4 倍数）⇒ **硬报错、非零退出**，信息明确「escape offset must be 0 or 4」；
   - 保留「非常量 ⇒ 报错」「基址必须是 `excp_cause_ip` ⇒ 报错」两条。
10. 反汇编/打印（`DADAOMCInstPrinter.cpp` `FK_ciii`：`imm << 2`）**不改**：合法值 0/4 往返一致；非法编码不要求反汇编报错（由执行期 ILLI 兜底）。
11. 导补丁 `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（一文件一补丁；`series` 不新增文件）。

### 4. QEMU 执行期检查

12. `helper_cfx_escape`（`.work/source/qemu/target/dadao/helper.c`，现 L2416 起）在**函数最前**（先于 reserved-cfxha 检查、先于任何状态切换）加：

```c
if (imms18 & ~0x1u) {                 /* imms18[17:1] SBZ 非零 ⇒ ILLI */
    cfx_raise(env, DADAO_CAUSE_ILLI, env->inner_run_mode, pc, info);
    return;
}
```

   与既有 reserved-cfxha ⇒ ILLI **同路径、同 `pc`/`info` 口径**（`excp_cause_ip` = 该 `escape` 指令地址）；**不**递增 `escape_num`、**不**改 `inner_cfx_mask`/`inner_run_mode`/`global_cfx_intr_mask`。
   检查放 helper（与 reserved/CFXESC 同处，一处覆盖全部译码路径）；`trans_escape_ciii_cfx` 的 `imms18` 拼装（`hb<<12|hc<<6|hd`）不变。
13. 导补丁 `components/qemu/patches/target/dadao/helper.c.patch`。

### 5. 测试向量 / lit

14. **L1 lit 正例** `tests/unit/llvm/lit/MC/DADAO/cfx2-trap-escape.s`：offset `8`（`7e000002`）与 `-8`（`7e03fffe`）两例改为 offset `0`（`7e000000`）与 `4`（`7e000001`）；注释里的 `imms18` 推导同步。
15. **L1 lit 反例** `tests/unit/llvm/lit/MC/DADAO/cfx2-trap-escape-err.s`：`RANGE`（524288 / -524292）与 `ALIGN`（6）三行改为「非 0/4」反例集（`2`、`6`、`8`、`-4`、`524288`），`CHECK` 串对齐新错误信息；`NONCONST`/`BASE` 两行保留。
16. **生成档** `tests/unit/llvm/lit/MC/DADAO-gen/gen-ciii.s` 与 `gen-fast.s`：由 `tools/testcases/generate_lit_vectors.py` **重生成**——把 `ciii-escape` 分支（现 L185–L187 硬编码 `8 >> 2`）改为合法值（取 4 ⇒ `imms18 = 1`），注释同步；`python3 tools/testcases/generate_lit_vectors.py` 后 `check_lit_gen.py` 须 PASS。
17. **inst 语义/合法性向量（QEMU 侧）**：`tests/inst` 增加 `escape_ciii_cfx` 用例，载体按其生成器归口（`tests/inst/base/misc.yaml` + `tools/testcases/generate_misc.py`，或新生成器——**生成器随产物入库**）：
    - **合法（偏移 0/+4）单指令 inst 向量：BLOCKED（architect 2026-11-01 核定）**——inst harness 无 cfx 帧/异常向量预置，裸 `escape` 必先撞目标/帧检查（CFXESC/CFXMEM）；且 offset 0 会重执行 trap，不宜作终止用例。**替代证据**：`045t::escape_fwd_offset`（trap→escape +4，`PC = cause_ip + 4`，exit `0x66`，14/14 PASS）与 `m5_trap_escape`（真实 trap→escape +4，`expected=96 actual=96` = 0x60）。
    - 非法（`expected_fault: ILLI`）：落地为 `cfxha=63` 形式（`cfxha=63` 合法，差异只在 SBZ）——`0x7EFC0002`/`0x7EFC0003`（`imms18`=2/3）、`0x7EFFFFFE`（`0x3FFFE`）、`0x7EFDFFFF`（`0x1FFFF`）；每条以 `sequence` 装 cfx3 HYPV `cause_id` 判别器，使 monitor-entry ILLI 可观测（注入 B 证明有鉴别力）。
    - 同步 `tests/inst/inventory.md`（`escape_ciii_cfx` 行现仍 `deferred TESTCASES-033t`）与 `tests/case-ledger.tsv`（`check-case-ledger` 现场重派生）。
18. **既有 escape 覆盖零回退**：`tests/arch/umon/m5_trap_escape.s`（offset 4）、bootrom 与 SBI 示例（全为 0/4）不改，跑通即可。

### 6. 锁 / 台账 / 版本

19. `manifests/spec-readonly.lock.toml`：本任务触及的**每册**（DADAO-12 / SimRISC-11 / Toolchain-01 / Machine-01）sha256 同笔重算，其余不变。
20. 各册**现行 `-rc` 段**补一条变更行（不发布、不去 `-rc`；`check-spec-changelog`/`check-spec-numbering` 机械判定，版本号以现场为准）。
21. `.tao/knowledge/MEMORY.md`：仅在偏离台账第 2 项（`fence` SBZ）括号内加一句同口径指针——**不新增条目**。

### 非目标（明确不做）

- **不改** `excp_cause_ip` 的 **RW** 属性（`DADAO-12` L382「软件可写」保持）；spec 正文**不得**写「由此保证返回地址受限」一类结论。
- **不改**异常帧保存/恢复（`excp_prev_run_mode`/`excp_prev_cfx_mask`/`saved_global_cfx_intr_mask`）。
- **不改** SBI 示例与调用约定（`DADAO-22` 全为 0/4，天然合法）。
- **不改** `ciii` 操作码/掩码、`cfxha` 合法性（`encode_cfx_reserved` 不变）、`imms20 ⇔ imms18` 的「字节 ⇒ 右移 2」映射关系。
- **不新增 ADR**（是否开 ADR 见「待裁定」）。

## 接口规范（编码规则，逐位）

```
汇编层  escape cfxha, [excp_cause_ip, imms20]      imms20 = 字节偏移 ∈ {0, 4}
编码层  escape_ciii_cfx  0111-1110  cfxha[5:0]  imms18[17:0]
        imms18 = imms20 >> 2                       ⇒ ∈ {0, 1}
        imms18[0]    = 字节偏移 bit2                （0 ⇒ 偏移 0；1 ⇒ 偏移 +4）
        imms18[17:1] = SBZ，MUST 全 0               （手工编码非 0 ⇒ ILLI）
寻址    Addr = excp_cause_ip + (imms18 << 2)        ⇒ cause_ip 或 cause_ip + 4
```

- **`imms18[0]` 就是「字节偏移的 bit2」**：`imms18` 的单位是 **4 字节字**，`imms18 = 0` ⇒ 字节偏移 0，`imms18 = 1` ⇒ 字节偏移 4。文档必须同时写出「**编码 0/1 ⇔ 字节 0/4**」，避免被误读成「`imms18[0]` = 字节偏移 bit0」。
- 汇编层**仍是字节**（`imms20`）；收窄的是**合法集**，不是单位。
- 非法 `imms18` 的 ILLI **先于**任何状态变更，`excp_cause_ip` = 该 `escape` 指令地址，进入当前模式 monitor（与 reserved-cfxha ⇒ ILLI 完全同路径）。
- 汇编层拒绝与执行期 ILLI 是**两道独立防线**：汇编器拒绝是「书写错误」；执行期检查兜住手工编码/外部产生的非法指令字。

## 验收标准

1. **汇编接受**：`llvm-mc --show-encoding` 对 `[excp_cause_ip, 0]` ⇒ `0x7e000000`、`[excp_cause_ip, 4]` ⇒ `0x7e000001`；`llvm-objdump -d` 反汇编回 `0` / `4`。
   命令示例：`echo 'escape cfx0, [excp_cause_ip, 4]' | .dadao/cross-toolchain/bin/llvm-mc --triple=dadao-unknown-elf --show-encoding`
2. **汇编拒绝**：`2`、`6`、`8`、`-4`、`-8`、`524288` 全部**非零退出**且信息含「must be 0 or 4」；`sym` 仍报「must be a constant」；`[rb0, 4]` 仍报「base must be 'excp_cause_ip'」。
3. **QEMU 合法仍正确**：`0x7E000000` / `0x7E000001` 不 fault，返回地址分别为 `cause_ip` / `cause_ip + 4`；`tests/arch/umon/m5_trap_escape.s`（offset 4 的真实 trap→escape 往返）跑通、退出码 `0x60`。
4. **QEMU 非法 ⇒ ILLI**：`imms18 ∈ {2, 3, 0x3FFFE, 0x1FFFF}` 手工编码 ⇒ `ILLI`（inst 向量 `expected_fault: ILLI`）。
   状态不变（`escape_num` 未递增、`inner_run_mode`/mask 未变、`excp_cause_ip` = `escape` 指令地址）：由 `tests/arch` 探针（复用 `min_rom_probe_*` 框架）断言；若判为超范围，须在完成区给出**替代证据**（helper 前置 `return` 的顺序 + 反例注入 B 现场）并经 reviewer 认可。
5. **spec/contract 文字一致**：`grep` 现场证明 4 册 + 3 份 contract 均为「0 或 4」，且全仓（除 `.tao/archive/`）无残留「`%4==0`」适用于 escape、「N 可为负数」表述；生成块与 yaml 逐字节一致。
6. **门控 L1**：`make check` 全绿（含 `check-legality-drift`、`check-legality-invariants`、`check-rule-refs`、`check-asm-prose`、`check-asm-list-drift`、`check-spec-codeblocks`、`check-spec-readonly`、`check-case-ledger`、`check-decodetree-repro`、`check-patch-tree`、`check-milestones-fresh`）。
7. **lit 零回退**：`make check-lit` 全绿；`make check-lit-full` 全绿（生成档已重生成、`check_lit_gen.py` PASS）。
8. **L2 零回退**：`make check-modules` 全绿（`install-host` 后跑）。
9. **反例注入**（三条都必须能红，各给「注入 → FAIL → `cp` 还原 + md5 对账 → 回绿」真实输出，**禁** `git checkout/restore/stash` 还原）：
   - A：AsmParser 恢复为接受 `8` ⇒ `cfx2-trap-escape-err.s` 红；
   - B：删除 `helper_cfx_escape` 的 `imms18 & ~0x1u` 检查 ⇒ inst ILLI 向量红；
   - C：删掉 `opcodes.yaml` 的 `imms18[17:1] == 0` 行 ⇒ `gen_legality_list.py --verify` 与 `check-legality-drift` 红。
10. **一键证据脚本**：`.work/evidence/<任务ID>/run_all.sh` 通过（断言数 >0、覆盖 1–9），完整输出落 `.work/log/spec/<任务ID>/`。
11. **补丁树**：`make check-patch-tree` 绿；LLVM/QEMU 两处各一补丁、非空、`series` 无新增文件。

## 文件范围（预计修改）

- **spec**：`spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/SimRISC-11-核芯功能扩展指令.md`、`spec/Toolchain-01-汇编语言.md`、`spec/Machine-01-测试机运行环境.md`
- **contracts**：`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`.tao/contracts/contract-isa.md`、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-asm.md`、`.tao/contracts/contract-asm-list.md`
- **LLVM**：`components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`
- **QEMU**：`components/qemu/patches/target/dadao/helper.c.patch`
- **测试**：`tests/unit/llvm/lit/MC/DADAO/cfx2-trap-escape.s`、`cfx2-trap-escape-err.s`、`tests/unit/llvm/lit/MC/DADAO-gen/gen-ciii.s`、`gen-fast.s`、`tools/testcases/generate_lit_vectors.py`、`tests/inst/base/misc.yaml`（或其生成器产物）、`tools/testcases/generate_misc.py`、`tests/inst/inventory.md`、`tests/case-ledger.tsv`
- **联动（必要，不扩大范围）**：`tools/testcases/arch/min_rom_probe_045t.py`（INTEG-045t 探针按新语义必红：`escape_fwd_offset` 偏移 `3→1`、原负偏移用例原位替换为 `escape_illegal_offset`）；`tools/llvm/gen_asm_list.py`（`contract-asm-list.md` 投影生成器）与 `tools/llvm/llvm-isa-backend-matrix.tsv`（`gen_isa_coverage.py` 派生件）随 `imms20` 口径同步
- **锁/证据**：`manifests/spec-readonly.lock.toml`、`.work/evidence/SPEC-180t/**`、`.work/log/spec/SPEC-180t/**`
- **禁止触碰**：`excp_cause_ip` 的 RW 定义、§5.3 异常帧恢复伪代码、`spec/DADAO-22` SBI 示例、`cfxha` 合法性、`ciii` 操作码/掩码、`.tao/knowledge/milestones.md`（流水行由 architect 落）

## 5 项预检（下发前）

① **任务书内部一致**：编码规则（汇编 {0,4} ⇒ `imms18` {0,1}）与范围 1–5、验收 1–4 逐条对应；「非目标」与「用户设计」一致（`excp_cause_ip` RW 保留已写入非目标与背景）。
② **验证手段前置可用**（本机实测）：
   - 工具链四件在盘：`.dadao/cross-toolchain/bin/{llvm-mc,llvm-objdump,llvm-lit,qemu-system-dadao}`；
   - 门控/生成器脚本在盘：`tools/spec/{check_legality_drift,check_legality_invariants,check_rule_refs,gen_legality_list}.py`、`tools/llvm/gen_asm_list.py`、`tools/infra/{check_case_ledger,check_spec_readonly,check_milestones_fresh}.py`、`tools/testcases/{generate_lit_vectors,check_lit_gen}.py`、`tools/qemu/{semantics_gate,check_decodetree_repro}.py`；
   - inst harness 支持 `expected_fault: ILLI`（`tests/inst/schema.md`）；`tests/inst/base/misc.yaml` 由 `tools/testcases/generate_misc.py` 生成（`DO NOT EDIT`）；
   - **需重建**：改 `DADAOAsmParser.cpp` + `helper.c` ⇒ `make install-host`（前置 `build-mc`/`build-qemu`/`build-builtins`）；engineer 须**申报预计耗时**，>10 min 交主会话后台（`setsid nohup` + `EXIT` 标记）。
③ **验收逐条可跑性**：1–11 **现在可跑**（前提：② 的重建完成）；**唯一 BLOCKED**：范围 17 的「合法（0/+4）inst 单指令向量」（harness 无 cfx 帧/向量预置），以 `045t::escape_fwd_offset` + `m5_trap_escape` 替代（见范围 17 与完成区）。
④ **与 `contracts/`、`tests/inst/` 一致**：`opcodes.yaml::escape_ciii_cfx` 现 `mask 0xFF000000` / `value 0x7E000000`，本任务只加 `legality`/`rule_refs` 不改编码；`encode_sbz` 已在 `legality_rules.yaml`（`fault: ILLI`、`static`、`active`），`check-rule-refs` 双向成立；`fence_ciii_cfx` 的 `immu18[17:12] == 0` 是同一表达式写法的既有先例。
⑤ **拟改文件 × `spec/` 清单命中**：4 册**全部在** `manifests/spec-readonly.lock.toml`（上游 20 册 + v5 自定 1 册的 sha256 锁）内 ⇒ **需用户授权原话**；本任务书「用户已确认的设计」已给出 escape 限制原文，「执行范围」把 spec 4 册限定在上述改动内；`/dispatch` 时须原样引用；若届时缺该原话，engineer **停并索取**。

## 冲突点与处置

1. **`DADAO-12 §5.1` 常见用法表第 3 行**（`[excp_cause_ip, N*4]`，N 可为负）与「只允许 0/+4」**直接冲突** ⇒ 删除该行（范围 1）。
2. **「须 `%4==0`」表述分布**：`Toolchain-01` L43/L172、`SimRISC-11` L44、`Machine-01` L100、`contract-isa` L1206、`contract-see` L65、`contract-asm` L175 ⇒ 全部收窄（范围 2–3）。
3. **现有向量含非法偏移**：`cfx2-trap-escape.s`（8、-8）、`gen-ciii.s`/`gen-fast.s`（8，且由 `generate_lit_vectors.py` L185–L187 硬编码 `8 >> 2`）、`cfx2-trap-escape-err.s`（524288/-524292 作 `RANGE` 反例）⇒ 全部改写（范围 5）。
4. **`excp_cause_ip` 可写（`DADAO-12` L382 `RW`「软件可写」）**：与本任务**不矛盾但必须显式声明**——软件写该寄存器仍可任意跳转，收窄偏移**不构成**安全边界（已按用户设计原话写入「背景」与「非目标」）。
5. **`opcodes.yaml::escape_ciii_cfx` 的 `imms18.signed: true`**：收窄后合法集 {0,1}，符号性无实际影响 ⇒ **保留不动**（改它牵动派生脚本），只在 `legality` 加位域约束。
6. **生成块不可手改**：`SimRISC-11` 的 `ASSEMBLY_LIST`（L143–154）/`LEGALITY`（L156–）由生成器产出；手改会被 `check-legality-drift`/`check-asm-list-drift` 判红。

## 待用户裁定

1. **是否为「`escape` 偏移合法集 = {0,+4}、`imms18[17:1]` SBZ 非零 ⇒ ILLI」开 ADR？** 按 `docs/Process-03` 判据命中 3 条（外部契约变更 / 多方案 / 结论固化）。若开，decision 须逐条与用户确认；可先执行本任务、ADR 后补。
2. **`escape` 偏移 `0` 在异步帧下的语义**（异步 `excp_cause_ip` = 下一条指令，`+0` ⇒ 重执行该指令、`+4` ⇒ 跳过一条指令）是否需在 spec 说明：属既有语义，本任务未纳入；请裁定是否扩入。

## 完成区

**测试结果**：L1/L2/L3 与构建依赖验收全绿。`make check` PASS；`check-lit` 161/161、`check-lit-full` 11/11、`check-inst` 977/982（5 deferred）、`check-modules` PASS、`check-arch` PASS（含 045t 14/14）；证据 `run_all.sh --require-build` PASS（0 failures），含注入 A/B/C。
**修改文件**：spec 4 册；`contracts/{opcodes,legality_rules}.yaml`；`.tao/contracts/contract-{isa,see,asm,asm-list}.md`；LLVM/QEMU 各 1 补丁；lit 正/反例、`gen-{ciii,fast}.s`、`generate_lit_vectors.py`、`generate_misc.py`、`tests/inst/base/misc.yaml`、`inventory.md`、`case-ledger.tsv`；`manifests/spec-readonly.lock.toml`；`.tao/knowledge/MEMORY.md`；`tools/testcases/arch/min_rom_probe_045t.py`（联动）；`.tao/knowledge/milestones.md`（仅状态行 `待开始→待验收`）。越界披露：`tools/llvm/gen_asm_list.py`、`tools/llvm/llvm-isa-backend-matrix.tsv`（生成物/生成器同步）。
**验收结果**：验收 1：`0/4` ⇒ `7e000000/7e000001`，`llvm-objdump` 回显 `0/4`。验收 2：`2/6/8/-4/-8/524288` 全 rc=1 且含 `must be 0 or 4`；`sym`/`[rb0,4]` 仍报原有错误。验收 3：`m5_trap_escape` `expected=96 actual=96`（0x60）。验收 4：4 条 inst `expected_fault: ILLI` PASS；045t `escape_illegal_offset` 断言 `cid=ILLI, escn:0=0`。注入 A：`check-lit` rc=2 红 ⇒ cp+md5 还原 ⇒ 161/161 绿；注入 B：inst FAIL（got UNDI 0x89）、045t FAIL（cid=CFXESC）⇒ 还原 ⇒ 双双绿。045t 联动：`escape_fwd_offset` 改 `imms18=+1`（目标 `cause_ip+4`，exit 0x66）；原负偏移改 `escape_illegal_offset`（`imms18=-1` ⇒ ILLI、`escn:0=0`），14/14 PASS。
**新发现/坑**：① 注入 C 原描述（删 `imms18[17:1] == 0`）不能让生成门控红——生成块只读 `rule_refs`；实际注入为删 `rule_refs: encode_sbz`（已注明）。② inst harness 无 cfx 帧/向量预置，monitor-entry ILLI 原本不可观测（只得 CFXMEM）；现由生成器的 `sequence` 安装 cfx3 HYPV cause_id 判别器（非 ILLI 走 UNDI）使 ILLI 可见，且注入 B 有鉴别力。③ `045t` 改前改后**均为 14 例**（`@case` 计数 14→14；原 `escape_neg_offset` 被 `escape_illegal_offset` 原位替换，非新增）；`check-arch` 的 045t 段只跑 2 例子集（`reserved_illi`/`trap_reserved_illi`），全量 14 例由 `tools/testcases/arch/min_rom_probe_045t.py` 直接跑（14/14 PASS）。④ `install-host` 重建后 `check-musl-freshness` 因 clang/ld.lld stamp 变化红，已跑 `build-builtins`+`build-musl-shared` 恢复。
**遗留问题**：① 合法 0/+4 无 inst 单指令向量（BLOCKED，替代证据见范围 17：`045t::escape_fwd_offset` + `m5_trap_escape`）。② ADR 未决：本任务「是否开 ADR」（待裁定 1）仍未裁定；`ADR-0013 D10` 仍写 `imms20=[-524288, 524284]` 且 `%4==0`（未含 escape 收窄），须经用户逐条确认后就地修订或新增 ADR；`ADR-0017`（cfx 汇编别名）经核实全文不含 escape 偏移表述，无需改。③ 旧口径残留（范围外）：`docs/DDLN/.../DD-C002`、`components/llvm-project/changelog.md` 仍写 escape 旧 `%4==0`；`tests/inst/schema.md` L34 仍写 `sequence` 仅 `tests/inst/atomics/*.yaml` 使用。④ 未 push（由主会话 `/complete` 后执行）。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 注入 C 描述与生成器真源不符 | ✅已修 | 证据脚本改为删 `rule_refs: encode_sbz`，并在脚本注释/完成区说明 | 脚本输出 `inject C ... gate FAIL` ×2 + 还原回绿 |
| F2 合法 inst 向量无法表达 | ⏸延后 | 未加合法 inst 向量；inventory/生成器注明由 arch 探针覆盖 | `validate-vectors` PASS；044t/m5_trap_escape 既有 |
| F3 045t 旧非法偏移按新语义必红 | ⏸延后 | 未改（任务书明令不改其它测试） | `git grep` 仅此文件含 `escape(0,3)`/负偏移 |
| F4 生成投影需同步 | ✅已修 | `gen_asm_list.py` 示例偏移 8→4 + imms20 行注明 escape 0/4；`gen_isa_coverage.py` 重派生 tsv | `check-asm-list-drift` PASS；`check-isa-coverage` PASS |
| F5 自审核对编码/检查顺序 | ✅已修 | QEMU 检查置于 `info` 后、reserved/CFXESC/状态切换前；LLVM 仅接受 0/4 且错误串含 `must be 0 or 4` | 补丁内容 grep + `check-patch-tree` PASS |

#### 第 2 轮 engineer 自审（构建后）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| G1 inst 非法 escape 仅得 CFXMEM（monitor 向量未设） | ✅已修 | `generate_misc.py` 为 4 条 legality 生成 `sequence`：设 cfx3 HYPV 向量 → cause_id 判别（ILLI→poison 0x88；非 ILLI→UNDI 0x89） | `check-inst` PASS；注入 B inst FAIL(UNDI) |
| G2 045t fwd/负偏移旧语义 | ✅已修 | fwd `imms18=3→1`（目标 +4，exit 0x66）；负偏移改 `escape_illegal_offset`（-1 ⇒ ILLI、escn:0=0）；docstring 同步 | `045t` 14/14 PASS；注入 B 该例 FAIL(cid=CFXESC) |
| G3 日志名触发 `check-run-artifacts` | ✅已修 | 证据脚本名清洗改为 `s/[^A-Za-z0-9_.-]+/_/g`；非法历史日志更名/清理 | `check-run-artifacts` PASS；`make check` PASS |
| G4 install-host 后 musl/builtins stamp 陈旧 | ✅已修 | 跑 `make JOBS=8 build-builtins` + `build-musl-shared`（非源码改动） | `check-musl-freshness` 回绿；`make check` PASS |
| G5 里程碑行仍 `待开始` | ✅已修 | 仅改该行为 `待验收`（用户授权） | `check-milestones-fresh`/L1 PASS |

#### 第 1 轮 architect 复核与提交（2026-11-01）

- **文件集**：`git status -uall` 28 项，逐项对账「文件范围 + 联动」——spec 4 册、`contracts/{opcodes,legality_rules}.yaml`、4 份 `.tao/contracts`、LLVM/QEMU 各 1 补丁、lit 正/反例 + `gen-{ciii,fast}.s`、`generate_lit_vectors.py`、`generate_misc.py`、`tests/inst/base/misc.yaml`、`inventory.md`、`case-ledger.tsv`、`manifests/spec-readonly.lock.toml`、`MEMORY.md`、`milestones.md`（仅状态行）、`tools/testcases/arch/min_rom_probe_045t.py`、`tools/llvm/gen_asm_list.py`、`llvm-isa-backend-matrix.tsv`、任务书。无漏提/多提，无 `docs/**` 越界。
- **语义复核**（读补丁/生成物，不依赖叙述）：汇编器仅 `Bytes==0||Bytes==4`；QEMU 检查在 `info` 后、reserved-cfxha/CFXESC/状态切换前（`imms18 & ~0x1u`）；`excp_cause_ip` RW（`DADAO-12` L382）与异常帧恢复未动；`opcodes.yaml` mask/value 与 `cfxha` 合法性未动；`imms18[0] ∈ {0,1}` 表述 4 册一致；lock 21 册 sha256 现场重算全对。
- **独立抽跑**：`make check` **rc=0**（`check-spec-readonly` 21 册、`check-legality-drift` 12 章、`check-patch-tree` 205 补丁、`check-asm-prose`/`check-asm-list-drift`/`check-case-ledger`/`check-run-artifacts` 全 PASS）；`make check-arch` **rc=0**（045t 14/14）；`make check-inst` **rc=0**（982 total / 977 passed / 0 failed / 5 deferred）；验收 1/2 现场重跑（`7e000000`、`7e000001` 且 `llvm-objdump` 回显 0/4；`2/6/8/-4/-8/524288` 全 rc=1 含 `must be 0 or 4`）；`check-isa-coverage` rc=0。
- **首跑 `make check` rc=2 根因**：architect 把复核日志误落到 `.work/log/` 下的临时子目录（事后已删除，该目录不留任何文件），触发 `check-run-artifacts` A3「illegal name（须 `check-<name>.log` 或 `<TASK-ID>-<purpose>.(log|json|txt)`）」，与任务内容无关；日志改存 `/tmp/opencode/SPEC-180t/arch-review/recheck-L1.log` 后重跑 rc=0。
- **任务书订正**：范围 17 合法 inst 向量登记 **BLOCKED** + 替代证据（`045t::escape_fwd_offset`、`m5_trap_escape`）；文件范围新增「联动」条；新发现③按实测订正（045t `@case` 14→14，原位替换非新增）；遗留补 ADR-0013 D10 / 本任务 ADR 未决 / DDLN 与 `schema.md` 旧口径。
- **白空格**：`git diff --check` 仅报 `llvm-isa-backend-matrix.tsv` 行尾 tab——该文件 218 行既有格式即行尾 tab（生成器输出，`check-isa-coverage` rc=0），非新增脏字符。
- **提交**：`feat(spec): SPEC-180t escape 偏移限制`（按用户明确指令；AGENTS.md 默认 `<任务ID>: <subject>` 与「未 Accepted ⇒ `WIP:`」两条被该指令覆盖）；分支 `SPEC-180t`，**不 push**。

#### 第 1 轮 reviewer 验收（Needs Revision）

- 判决：**Needs Revision**（唯一阻断）——`make check` rc=2：`check-knowledge-refs` 报本审阅记录中 architect 复核轮引用的 `.work/log/**` 临时日志路径悬空（该日志已移至 `/tmp/opencode/SPEC-180t/arch-review/L1.log`）。其余项（文件集 / 语义 / lit / inst / arch / 证据）通过。

#### 第 1 轮 architect 修复（Needs Revision 后，2026-11-01）

- 任务书：删去该悬空路径，改述为「误落 `.work/log/` 下的临时子目录（事后已删除，目录不留文件）」+ 现址 `/tmp/opencode/SPEC-180t/arch-review/recheck-L1.log`；`check-knowledge-refs` 现场 **0 悬空**。
- 证据脚本补 3 门控：`check-knowledge-refs`、`check-run-artifacts`、`check-milestones-fresh`（`.work/evidence/SPEC-180t/run_all.sh`，未跟踪文件，不入库）。
- 复跑：`make check` **rc=0**；`run_all.sh --require-build` **rc=0**（新增 3 门控均 PASS；注入 A/B 仍「红 → `cp`+md5 还原 → 回绿」）。
- 提交：`fix(spec): SPEC-180t 修正悬空引用与证据覆盖`（仅任务书一笔；不 push）。

#### 第 1 轮 reviewer 验收（独立重跑详录，2026-11-01）

**重跑记录（以下全部为我自己的命令与退出码，不采信完成区转述）**
- 树：分支 `SPEC-180t`、HEAD `7ad17a42`、`git status -uall` 空；commit 28 文件与完成区「修改文件」逐项对账一致；`spec/**` 恰 4 册、`docs/**` 0 项；注入前后两次快照均空，`check-source-state` rc=0、`check-patch-tree` rc=0（205 补丁）。
- **`make check` ⇒ rc=2**：唯一红项 `check-knowledge-refs`（`结果: FAIL (1 悬空 .work/** 引用)`）＝本任务书 **L211** 引用的 arch-review 复核日志旧路径（该日志已移出仓库日志目录、现存于 `/tmp/opencode/SPEC-180t/arch-review/L1.log`，任务书仍写旧路径故门控判悬空）；`make -k check` 其余检查全绿。
- `make check-lit` rc=0（161/161）、`check-lit-full` rc=0（11/11）、`check-inst` rc=0（982 total / 977 passed / 0 failed / 5 deferred）、`check-arch` rc=0、`make check-modules` rc=0。
- 验收1：`0/4 ⇒ 7e000000 / 7e000001`，`llvm-objdump` 回显 `0/4`；验收2：`2/6/8/-4/-8/524288` 全 rc=1 且含 `must be 0 or 4`，`sym`／`[rb0,4]` 原错误不变。
- 验收3：`m5_trap_escape` `expected=96 actual=96`（0x60）rc=0；验收4：`misc.yaml` 6/6（4 条 `Expected ILLI, got ILLI`）rc=0；045t 直跑 14/14（`escape_fwd_offset` +4 ok、`escape_illegal_offset` ILLI 且 `escn:0=0` ok）。
- lock 21 册 sha256 现场重算 0 不符；`gen_legality_list --verify` rc=0、`check_lit_gen` 62/0；`%4==0` 现存仅跳转/分支与 Toolchain-01 `-rc` 历史行，`N*4`／「可为负」仅 `.tao/archive/`（历史）与任务书自述。
- 证据脚本 `bash .work/evidence/SPEC-180t/run_all.sh --require-build` ⇒ **rc=0（0 failures）**，其内注入 A/B/C 均「红 → `cp`+md5 还原 → 回绿」。
- **独立注入（变异不与脚本相同）**：A' 把 `Bytes != 0 && Bytes != 4` 换回旧 `Bytes % 4 != 0` ⇒ `check-lit` **rc=2**（`cfx2-trap-escape-err.s` FAIL）→ `cp`+md5（`3f7ffce0…` 相等）→ 重建后 161/161 rc=0；B' **删除**整个 `if (imms18 & ~0x1u){…}` 块（脚本用 `if (false)`）⇒ inst case2 FAIL（`Expected ILLI, got UNDI`）+ 045t FAIL（`cid:3 exp=0x100 got=0x8`）→ `cp`+md5（`41aca53a…` 相等）→ 双双 rc=0。全程未用 `git checkout/restore/stash`。

**约束核验**：`excp_cause_ip` RW（DADAO-12 L382）未动；§5.3 异常帧恢复步骤未动；`escape` 的 mask/value 与 `cfxha` 合法性未动；两补丁非空、`series` 0 改动；`milestones.md` 仅状态行、`MEMORY.md` 仅括号内指针；无 `docs/**` 越界。
**finding（不阻断，交 architect 收尾改）**：① 完成区「`check-arch` PASS（含 045t 14/14）」与实况不符——`check-arch` 的 045t 段只跑 2 例，14/14 是直跑（新发现③已自纠）；② `generate_misc.py` docstring（无帧）与内联注释/notes（cfx0 目标错配）口径不一，两路径同归 `CFXESC`，行为不受影响；③ `tests/inst/schema.md` L34「当前由 atomics 使用」已过时；④ `run_all.sh` 未覆盖 `check-knowledge-refs`/`check-run-artifacts`/`check-milestones-fresh`，故「一键证据 PASS」与 L1 实况不一致。
**裁定**：范围 17 合法 inst 向量 BLOCKED、以 `045t::escape_fwd_offset`+`m5_trap_escape` 替代 → **接受**（inst harness 无 cfx 帧属实；`integ044t::escape_return` 与 m5 覆盖合法 +4 执行）；045t 联动 → **必要**（旧 `imms18=+3`／负偏移按新语义必红），不降覆盖（任意偏移能力已由 spec 删除，负偏移原位换成 SBZ 反例）；`generate_misc.py` docstring 与 notes 不一致、`schema.md` 旧口径、ADR 未开、`ADR-0013 D10` 旧范围、DDLN/changelog 旧口径 → **非阻断遗留**（ADR 须用户逐条确认后补）。
**判决：Needs Revision** —— 验收 6 `make check` 在我的重跑下 **rc=2**（`check-knowledge-refs` 悬空引用；根因是本任务书 L211 写了已移出 `.work/log` 的日志路径，属本任务新增内容）。**修法**：L211 的旧日志路径改为实际路径 `/tmp/opencode/SPEC-180t/arch-review/L1.log`（或删该路径），改后重跑 `make check-knowledge-refs` 与 `make check` 期望 rc=0；建议同时给 `run_all.sh` 补跑 `check-knowledge-refs`，使一键证据覆盖验收 6。

#### 第 1 轮 architect 修复收口（Needs Revision 后复跑，2026-11-01）

- 悬空引用已修：本审阅记录不再引用 `.work/log/**` 下的临时路径；`make check-knowledge-refs` ⇒ **rc=0（0 悬空 `.work/**` 引用）**；`check-run-artifacts` rc=0（2573 files / 0 illegal）、`check-milestones-fresh` rc=0（68 行）。
- 证据脚本补 3 门控后：`bash .work/evidence/SPEC-180t/run_all.sh --require-build` ⇒ **rc=0**（新增 `check-knowledge-refs`/`check-run-artifacts`/`check-milestones-fresh` 三行 PASS；注入 A/B 仍红→还原→回绿）。
- `make check` ⇒ **rc=0**（`repository checks (L1): PASS`）；复跑原始日志 `/tmp/opencode/SPEC-180t/fix-round/`（`L1_EXIT=0`、`EVIDENCE_EXIT=0`）。
- 提交：`fix(spec): SPEC-180t 修正悬空引用与证据覆盖`（仅任务书一笔；**不 push**）；待 reviewer 复审。

#### 第 2 轮 reviewer 复审（2026-11-01，独立重跑）

- **提交核对**：复审首查 `git log -2` 仍为 `7ad17a42`/`def5673c`（fix commit 当时未落盘，属并发）；随后 `git log -3` ⇒ HEAD **`0a10a727 fix(spec): SPEC-180t 修正悬空引用与证据覆盖`**（05:46:16；`git show --name-status` 仅任务书 1 文件，`git diff 7ad17a42 0a10a727` 亦仅任务书 33+/2−，其余交付物与上轮逐字节相同）。
- `git status -uall` ⇒ **空**（`.work/` 由 `.gitignore:2` 忽略，证据脚本不入库属预期）。
- L211 已不再是 `.work/**` 具体路径：现文为「误落 `.work/log/` 下的临时子目录（事后已删除，目录不留文件）」+ 现址 `/tmp/opencode/SPEC-180t/arch-review/recheck-L1.log`；`make -s check-knowledge-refs` ⇒ **rc=0、悬空 0**。
- **`make check` ⇒ rc=0**（我独立跑，`repository checks (L1): PASS`；`check-knowledge-refs` 段 `.work/` 引用 515 条、悬空 0；无任何 `结果: FAIL`）。
- **`bash .work/evidence/SPEC-180t/run_all.sh --require-build` ⇒ rc=0**（`SPEC-180t evidence: PASS (build-dependent + injections A/B, 0 failures)`、`EXIT=0`、`^FAIL` 计数 0）：新增第 82–84 行 `run_check check-knowledge-refs / check-run-artifacts / check-milestones-fresh` 三行均 PASS（`run_check` 门控非 0 即 `bad()` 计数 → 脚本 rc=1，可达 FAIL；断言 42→45）；注入 A 红 `check-lit rc=2` → `cp`+md5（`3f7ffce0…`）→ 回绿，注入 B 红 inst+045t → `cp`+md5（`41aca53a…`）→ 回绿；`final check-source-state`/`check-patch-tree` rc=0。
- 脚本其余断言未弱化：验收 1–3、`check-lit/lit-full/inst/arch/modules`、`probe 045t`、注入 C 与三处还原行逐行 grep 均在；复审后源码 md5 与上轮注入前一致（`3f7ffce0…`/`41aca53a…`），树复归干净。
- 上轮已核、且本轮交付物未变的项（28 文件对账、spec 4 册语义、`excp_cause_ip` RW／异常帧恢复／ciii-cfxha 编码未动、lock 21 sha256、验收 1–4、独立注入 A'/B'）不再重跑，采信上轮我自己的输出。
- **finding（不阻断，交 architect 收尾）**：① architect 将我上轮记录节名改为「第 1 轮 reviewer 验收（Needs Revision）」并把正文挪入「第 1 轮 architect 修复」节下，记录结构被打乱（正文未删改）——建议只补节名、不移动正文；② 上轮 4 条 finding 与遗留（ADR 未开、`ADR-0013 D10`、DDLN/changelog 旧口径、`schema.md`、`generate_misc.py` docstring/notes、完成区 045t 计数）维持原判，非阻断。
- **判决：Accepted** —— 本复审三条（树干净、L211 不再悬空、`make check` rc=0）与一键证据 rc=0 均在我自己的重跑下成立，上轮唯一阻断项已消除；其余交付物与上轮已验收状态一致。

#### 第 2 轮 architect `/complete` 交叉复核（Accepted 后，2026-11-01）

- **结构 finding ① 处置**：只补节名（`第 1 轮 reviewer 验收（独立重跑详录）`），reviewer 正文未移动、未删改。
- **独立抽核**：`make check` **rc=0**（`repository checks (L1): PASS`）；`make -s check-knowledge-refs` **rc=0（0 悬空）**；一键证据 `bash .work/evidence/SPEC-180t/run_all.sh --require-build` **rc=0**（`SPEC-180t evidence: PASS (build-dependent + injections A/B, 0 failures)`，含新增 3 门控 PASS）。
- **交付物抽核**：`7ad17a42` = 28 文件；`spec/` 恰 4 册；`excp_cause_ip` 寄存器行（`DADAO-12` L382 `RW`／软件可写）父/子提交内容逐字节相同（md5 一致）；045t 联动在位（`escape(0, 1)`、`escape(0, -1)`、`escape_illegal_offset`）；范围 17 的 BLOCKED 与替代证据在册。
- **收尾**：任务书 `**状态**：已验证`；`milestones.md` 本行 `已验证`（同一提交）。遗留：ADR 未开（须用户逐条确认）、`ADR-0013 D10`、`DDLN/DD-C002`、LLVM `changelog.md`、`tests/inst/schema.md` L34、`generate_misc.py` docstring 与 notes 口径不一（均非阻断）。
- **提交**：`review: SPEC-180t Accepted（reviewer + architect 交叉复核）`；**不 push、不 merge**。
