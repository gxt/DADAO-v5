# SPEC-180t: escape 只允许偏移 0 / +4

**模块**：spec
**项目里程碑**：M10
**依赖**：`SPEC-177t`（已验证，SEE/SBI 现行口径）、`INTEG-045t`（已验证，cfx 指令清理）；决策依据 **ADR-0004 D5.3**（SBZ 非零 ⇒ ILLI，架构自定义）、**ADR-0045 D8**（escape：偏移为编译期固定立即数）
**状态**：待开始

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
    - 合法：`0x7E000001`（偏移 +4）不 fault；`0x7E000000`（偏移 0）不 fault（按 harness 可判定字段）；
    - 非法（`expected_fault: ILLI`）：`0x7E000002`、`0x7E03FFFE`（= `imms18` 0x3FFFE）、`0x7E01FFFF`；
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
- **锁/证据**：`manifests/spec-readonly.lock.toml`、`.work/evidence/SPEC-180t/**`、`.work/log/spec/SPEC-180t/**`
- **禁止触碰**：`excp_cause_ip` 的 RW 定义、§5.3 异常帧恢复伪代码、`spec/DADAO-22` SBI 示例、`cfxha` 合法性、`ciii` 操作码/掩码、`.tao/knowledge/milestones.md`（流水行由 architect 落）

## 5 项预检（下发前）

① **任务书内部一致**：编码规则（汇编 {0,4} ⇒ `imms18` {0,1}）与范围 1–5、验收 1–4 逐条对应；「非目标」与「用户设计」一致（`excp_cause_ip` RW 保留已写入非目标与背景）。
② **验证手段前置可用**（本机实测）：
   - 工具链四件在盘：`.dadao/cross-toolchain/bin/{llvm-mc,llvm-objdump,llvm-lit,qemu-system-dadao}`；
   - 门控/生成器脚本在盘：`tools/spec/{check_legality_drift,check_legality_invariants,check_rule_refs,gen_legality_list}.py`、`tools/llvm/gen_asm_list.py`、`tools/infra/{check_case_ledger,check_spec_readonly,check_milestones_fresh}.py`、`tools/testcases/{generate_lit_vectors,check_lit_gen}.py`、`tools/qemu/{semantics_gate,check_decodetree_repro}.py`；
   - inst harness 支持 `expected_fault: ILLI`（`tests/inst/schema.md`）；`tests/inst/base/misc.yaml` 由 `tools/testcases/generate_misc.py` 生成（`DO NOT EDIT`）；
   - **需重建**：改 `DADAOAsmParser.cpp` + `helper.c` ⇒ `make install-host`（前置 `build-mc`/`build-qemu`/`build-builtins`）；engineer 须**申报预计耗时**，>10 min 交主会话后台（`setsid nohup` + `EXIT` 标记）。
③ **验收逐条可跑性**：1–11 **现在可跑**（前提：② 的重建完成）；**无 BLOCKED 项**。
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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
