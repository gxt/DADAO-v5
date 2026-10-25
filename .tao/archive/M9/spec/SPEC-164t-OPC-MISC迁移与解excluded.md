# SPEC-164t: `OPC-MISC` 迁 `op 0x47`（含 `ctpop/ctlz/cttz` 并入）+ `fence`/`lr`/`sc` 解 `excluded`

**模块**：spec
**项目里程碑**：M9（收尾前）
**依赖**：`SPEC-166t`（已验证）、`INFRA-102t`（已验证，`master 9fd5974e`；门控已无写死常量）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源（用户裁定，2026-10-22）

- 「还有一个编码改动过：OPC-MISC的编码改为：0100-0111」
- 「修改编码：`ctpop_orri_rd` `ctlz_orri_rd` `cttz_orri_rd` 从 `OPC-octa` 改为 `OPC-MISC`，opx：`100-101`/`100-110`/`100-111`」
- 「同意」（`ISS-328`：`fence` + 24 条 `lr/sc` 已实现但账面仍 `excluded`/`ILLI`）
- 结构收益：迁后所有 `OPC-*` 表集中在 `0100` 行（`0x40–0x44` + `0x47`），`0x45`/`0x46` 留空

## 现场事实（执行前须复核）

- `contracts/opcodes.yaml`：`op = 0x77` 的记录 **26 条** = `fence_oiii_imm`、`swym_oiii_imm`、`lr`×12、`sc`×12；其中 `fence`+`lr/sc` 共 **25 条** `scope: excluded` + `decode: ILLI`
- 另 **3 条** 从 `OPC-octa` 迁入：`ctpop_orri_rd`（`op 0x40 / ha 0x1D`）、`ctlz_orri_rd`（`0x40 / 0x1E`）、`cttz_orri_rd`（`0x40 / 0x1F`），`scope: m8`
- `OPC-MISC` 内 `ha = 0x25/0x26/0x27` **空闲**（现用：`fence 0x20`、`swym 0x22`、`lr 0x10–0x13`、`sc 0x18–0x1B`）
- `spec/SimRISC-00` 主表：`0111-0111` 单元格 = `OPC-MISC`；`0100-0111` **为空**
- QEMU：`insn.decode.patch` 有 **26 条** `01110111…` pattern；`trans_fence_oiii_imm`（`trans_ctrl`）、`trans_lr_*`/`trans_sc_*`（`trans_mem`）已实现
- LLVM：`DADAOInstrInfo.td.patch` / `DADAOAsmBackend.cpp.patch` 有 `0x77…` 硬编码；`fence` 由原子降级路径发射
- 计数现值：`total 264 / m1 156 / fp 64 / excluded 27 / m3 1 / m8 7 / m9 9`

## 目标

1. **编码迁移**：26 条 `op: 0x77 → 0x47`，重算 `value`/`mask`（`value = (0x47 << 24) | (ha << 18)`，`mask` 不变）。
1b. **3 条并入**：`ctpop`/`ctlz`/`cttz` 改 `op 0x40 → 0x47`、`ha 0x1D/0x1E/0x1F → 0x25/0x26/0x27`；`scope: m8` 不变、无位宽后缀不变。
   - 规范侧：从 `SimRISC-00 §4.2 OPC-octa` 子表移入 `§4.1 OPC-MISC` 子表；**删除**原「无位宽后缀指令借用 MISC-octa 格位」的例外说明（迁入 MISC 后不再需要）。
   - 连带：`SimRISC-04`「Bit manipulating」章节里关于"借用 octa 格位"的注同步删/改。
2. **主表迁移**：`SimRISC-00` 主表把 `OPC-MISC` 从 `0111-0111` 移到 `0100-0111`（`0111-0111` 置空 = reserved UNDI）。
3. **翻转**：`fence` + 24 条 `lr/sc`：`scope: excluded → m9`、删 `decode: ILLI`；`swym` 保持原 scope。
4. **QEMU**：26 条 decode pattern 前缀 `01110111 → 01000111`；trans 不变。
5. **LLVM**：`fence`/`lr`/`sc` 的编码常量同步（若用 TableGen 由 opcodes 生成则重生成）。
6. **生成物**：向量（`atomics-*`、`isa/misc`）、lit（`gen-excluded.s` 等）、探针中的期望编码重生成。
7. **账面**：`excluded 27 → 2`（仅 `cfxld`/`cfxst`）、`m9 9 → 34`、`m8` 仍 7；`total` 不变（264）。
   - 注：`018` `check_scope` 若已由 `INFRA-102t` 去常量，则本册不改常量。
8. **ADR**：`ADR-0034` 加 `## 修订`，记录 op 变更（决策依据 = 用户原话，逐字）；`ADR-0032`/`ADR-0012`（提及 `ctlz/ctpop/cttz` 格位）同理；`MEMORY.md` 第 6 项同步。
9. **门控补位**：`check_tables.py` 增加 `OPC-MISC`（`op 0x47`）表覆盖（`INFRA-102t` 遗留：现只到 `op 0x44`）。

## 验收

1. `check_scope` / `check-isa-coverage` / `check_qemu_trans --strict`（应仍 **264/264**）全绿；`grep '0x77' contracts/opcodes.yaml` ⇒ **0**（26 条全部 `0x47`）。
2. QEMU 实机：`fence`/`lr`/`sc` 与 `ctpop/ctlz/cttz`（各 1 条）能执行（原子冒烟 1 例：`__atomic_add_fetch` 跑通），且 `swym 0` 仍为 no-op。
3. spec 主表：`0100-0111 = OPC-MISC`、`0111-0111` 空；`check_spec_codeblocks`/`check_tables` 绿。
4. LLVM：`install-host` + lit 全绿；`objdump` 反汇编 `fence` 显示新编码。
5. **编码核验**：`objdump` 反汇编 `ctpop` 显示 `0x47…`；`ctlz`/`cttz` 同理；`OPC-octa` 子表不再出现这三条。
6. **可达 FAIL ≥4**：① 留一条 `op: 0x77` ⇒ 编码一致性门控红；② 删一条 decode pattern ⇒ `check_qemu_trans` 263/264 红；③ 把一条改回 `excluded` ⇒ `check_scope`/`check_fp_contract` 类不变量红；④ `ctlz` 的 `ha` 写回 `0x1E` ⇒ 编码一致性红。
7. 重建：`make install-host` + `build-builtins` + `build-musl-shared`（`.td` 改动）；`make check`(L1) + `make check-modules`(L2) 绿。

## 接口规范

- **输入**：`contracts/opcodes.yaml`、`spec/SimRISC-00`、`components/qemu/patches/**`、`components/llvm-project/patches/**`、`tests/**`、`tools/**`、`.tao/adr/adr-0034-*.md`、`.tao/knowledge/MEMORY.md`。
- **输出**：迁移后的编码 + 翻转后的 scope + 重生成的向量/lit/探针 + ADR 修订。
- **约束**：不改指令语义；不新增指令；不 commit/push；临时目录 `/tmp/opencode/SPEC-164t/`。

## 风险与纪律

- **机器码不兼容**：`0x77…` → `0x47…`，所有已编产物须重编（工具链、bootrom、测试二进制）；旧 ELF 不得再用于验收。
- **ADR 修订**：`ADR-0034`（`D1`/`D5`：fence/lr/sc 编码）、`ADR-0032`/`ADR-0012`（提及 `ctlz/ctpop/cttz` 格位）属 `Accepted` ⇒ 只加 `## 修订`，不改决策正文；决策依据一律引用用户原话。
- 逐条比对 `insn.decode.patch` 的 26 条 mask/pattern，禁批量正则一把梭。

## 完成区

**测试结果**：`evidence run.sh` 默认 **47/47 rc=0**；`--inject all` **60/60 rc=0**（4 类注入均「红→cp+md5 还原→绿」）；L1 `make check` rc=0、L2 `make check-modules` rc=0；`check-lit` **131/131**、`check-lit-full` **12/12**；`check-qemu-semantics` **967/978 passed / 0 failed / 11 deferred（登记名单一致）PASS**；`check_qemu_trans --strict` **264/264（M1 156/156）**；`validate_decodetree` 264/264。
**修改文件**：`contracts/opcodes.yaml`（重生成；26 条 op 0x77→0x47 + ct* 3 条迁 MISC）+ `tools/spec/generate_opcodes.py`、`tools/spec/check_tables.py`（+OPC-MISC 表/注入）、`tools/spec/validate_encoding.py`（补 value==op/ha 校验）；`spec/SimRISC-00/04/11`（主表迁 `0100-0111`、§4.1 加/§4.2 删 ct*、删例外注、生成区重生成）+ `manifests/spec-readonly.lock.toml`；QEMU `insn.decode.patch`（重生成）+ `trans_ctrl/trans_bitcnt` 注释；LLVM `DADAOInstrInfo.td.patch`（26+3）+ `DADAOAsmBackend.cpp.patch`（nop 字节）；生成物 `tests/vectors/{atomics,bitcnt,isa/misc}`、`tests/llvm/lit/MC/DADAO{,-gen}/*`、`tests/case-ledger.tsv`、`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`、`.tao/contracts/contract-asm-list.md`；载体 `tests/scripts/build_test_binary.py`（毒饵改 cfxld）、`verify_harness_dump.py`、`tools/qemu/{generate_atomics_vectors,check_harness_ops,min_rom_probe_046t/071t/072t,smoke-dadao-m1.sh}`、`tools/testcases/generate_misc.py`、`tools/llvm/test_encoding_oracle.py`；账面 `contract-isa.md`、`components/*/changelog.md`、`ADR-0012/0032/0034`（`## 修订`）、`MEMORY.md` 第 6 项。
**验收结果**：`grep -c "op: 0x77" contracts/opcodes.yaml` ⇒ **0**；29 条 `op: 0x47`（fence/swym/lr12/sc12/ct3），计数 **excluded 2 / m9 34 / m8 7 / total 264**；QEMU 实机：`swym 0` 仍 no-op、`fence`、`lr`/`sc`（`__atomic_add_fetch` 静态 musl：rc=0、无 `__atomic_*` 未定义、反汇编 `fence 975`/`lr.t.an`/`sc.t.ar`）、`ctpop`/`ctlz`/`cttz` 各 1 例 PASS；LLVM：`fence 0`=`47 80 00 00`、`swym 0`=`47 88 00 00`、`ctpop/ctlz/cttz`=`47 94/98/9c 82 7f`、`lr.o.nn`=`47 00 02 02`、`sc.o.nn`=`47 40 82 42`，`objdump` 7/7 显示 `0x47`；`check_tables` **6 表 177 条 / 384 格 0 不符**；`check-isa-coverage --check` PASS（accept 262/reject 2）；`check-instrinfo` 0 errors（262 defs，M9 34/34）。
**新发现/坑**：① `validate_encoding` 原不校验 `value == (op<<24)|(ha<<18)` ⇒ 只改 op/ha 漏改 value 无门控可判；本册补该校验（注入①④的 FAIL 载体）。② `check_qemu_trans` 只看 trans 函数、不看 decode pattern，`validate_decodetree` 未入 L1/L2 ⇒ 删一条 decode 无门控可判（本册以 evidence 载体覆盖，建议另立 INFRA 接入）。③ `fence` 实现后旧 ILLI 毒饵 `0x77000000` 变空白 op ⇒ QEMU 报 **UNDI 0x89**（非 ILLI），分支 harness 毒饵改用 `cfxld` `0x7C000000`。④ `generate_atomics_vectors.fence_word`/`generate_misc.py` 曾硬编码 `0x77`，首轮重生成只改注释；已改为 opcodes.yaml 现场派生。⑤ lit 重生成顺带刷新 `@src`（SPEC-165t 后陈旧，13 文件 322 行）。⑥ `tests/llvm/test_encoding_oracle.py` 有 3 条**既存**失效用例（`ext.uo` 旧 ha、已删 `cs.eq/ne-rf`），非本册引入、非门控。⑦ 历史探针 005t–061t 仍含旧编码（非门控，ISS 已登记漂移），本册只改 live 的 046t 与近期 071t/072t。
**遗留问题**：`test_encoding_oracle.py` 3 条既存红（未修，非门控）；历史 `min_rom_probe_005t–061t` 未追改（非门控）；建议另立任务把 `validate_decodetree`/`check_tables` 接入门控。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `build_misc_amo` 新增 ct* 后 yaml 记录顺序前移，decode patch 行位移动 | ✅已修（确认预期） | 生成器/解码均由记录派生；逐 id 断言而非行号断言 | evidence「26+3 decode patterns per-id」29/29；`validate_decodetree` PASS |
| F2 `fence` 转 `m9` 后 `rule_refs` 由空变 `encode_sbz`，是否触发 rule_refs 门控 | ✅已修（复验） | 无额外改动 | `check_rule_refs` PASS（342 处引用）；`validate_instrinfo` M9 34/34 |
| F3 越界改动：`.tao/contracts/contract-isa.md`、`components/*/changelog.md` 不在任务「输入」清单 | ✅已修（披露保留） | 仅同步编码/计数/变更记录（`op 0x47`、A.6/A.7/A.9、excluded 2 / m9 34；两条 changelog） | `check_contracts_pending`/`check_component_changelog`/`check_spec_drift` PASS |
| F4 为让注入①④可达 FAIL，新增 `validate_encoding` 的 `value == op/ha` 断言（门控加强，非任务原文） | ✅已修（披露保留） | `tools/spec/validate_encoding.py` 新增 `check_op_ha_value` | 注入①④ rc=1；正常 rc=0；L1 PASS |
| F5 手写 lit/harness/oracle 硬编码旧编码，属「禁手改」但非生成物 | ✅已修（逐处机械替换+复验） | 7 个 MC lit、`build_test_binary.py`（毒饵改 cfxld）、`verify_harness_dump.py`、`test_encoding_oracle.py`（swym/fence 3 例） | `check-lit` 131/131；`check_case_ledger` PASS；`check_harness_ops` 22/22 |
| F6 生成器自身硬编码 `0x77`（fence_word/generate_misc）导致重生成不彻底 | ✅已修 | 两处改为从 `contracts/opcodes.yaml` 现场派生 | 重生成后 `atomics-fence.yaml` 19/19 = `0x47…`；misc `0x47880000`；L3 127 例 atomics 全过 |
| F7 证据脚本首版 `tr -d 'encoding: []'` 误删 hex 字符 `c` | ✅已修 | 改 `sed` 去 `0x`/逗号 | 默认 47/47 PASS（修复前 7 FAIL） |

### 第 1 轮 reviewer 验收（2026-10-22，独立重跑）

**重跑记录（判决全部基于本人命令，工作树干净、快照前后 0 行一致）**

- **编码 29 条**：自建脚本现场重算（`yaml.safe_load` 全量）：`op==0x47` **恰 29**（fence+swym+lr12+sc12+ct3），`op==0x77` **0**；每条 `value == (0x47<<24)|(ha<<18)` 29/29 相符；`ctpop/ctlz/cttz` 的 `ha=0x25/0x26/0x27`、`scope=m8` 均 OK。
- **decode 一致性**：自建脚本逐 id 比对 `insn.decode.patch` 29 个 pattern 的 `op`/`ha` 与 yaml（非抽样）：**29/29 OK**；旧前缀 `01110111` 在新增行 **残留 0**。
- **scope 账面**：`total 264 / m1 156 / fp 64 / m9 34 / excluded 2 / m8 7 / m3 1` 全对；`excluded` 仅 `cfxld_crii_cfx`/`cfxst_crii_cfx`；`swym` scope 改前(`4d821836~1`)/改后均 `m1`，**未被顺手改动**。
- **实机（本人自编自跑）**：`rt2.c`（`__atomic_add_fetch` + `ctpop/ctlz/cttz` 内联 asm + 独立参考实现比对）clang+musl 静态链接 ⇒ `qemu-dadao` **rc=0**；反汇编 `swym 0=47 88 00 00`、`ctpop/ctlz/cttz=47 94/98/9c`、`fence 975=47 80`、`lr.t.an`/`sc.t.ar` 全 `0x47`；`swym 0` no-op 用例 rc=0。
- **LLVM**：`llvm-mc -show-encoding` 7 条全 `47 …`（fence `47 80 00 00`、swym `47 88 00 00`、ct* `47 94/98/9c 82 7f`、lr/sc `47 00/40 …`）；`objdump` 7/7 显示 `0x47`；`check-lit` **131/131 rc=0**。
- **生成物门控**：`check_tables` **6 表 177 条/384 格 0 不符**（含新增 OPC-MISC 29 条）、`validate-vectors` **156/156 rc=0**、`check-isa-coverage --check` PASS（accept 262/reject 2）、`check_qemu_trans --strict` **264/264 rc=0**、`validate_encoding`/`check_scope`/`validate_decodetree`/`check-instrinfo` 全 rc=0；向量旧编码残留 0（clmul 的 `0x77…` 为随机数据高位，非编码）。
- **ADR/MEMORY**：`ADR-0034/0032/0012` 各有 `## 修订`，`git diff --numstat` = **18/0、10/0、15/0 纯增**（决策正文未改），0034 修订含用户原话逐字；`MEMORY.md` 第 6 项已同步为「fence + lr/sc 24 条已实现（m9）；excluded 2 条」。
- **注入（cp+md5，本人独立执行）**：① `fence op` 改回 `0x77` ⇒ `validate_encoding` **rc=1** + `check-isa-coverage` **rc=1** 双红；② `ctlz ha` 改回 `0x1E` ⇒ `validate_encoding` **rc=1** 红。两次还原 md5 相等、回绿 rc=0，工作树干净。
- **遗留核实（既存非本册引入）**：`test_encoding_oracle.py` 现 **3 红**（`ext.uo`/`cs.eq`/`cs.ne`）；以 `4d821836~1` 临时 worktree 复跑为 **6 红**（另 3 条 `swym 0`/`fence 0xf`/`swym 42` 本册已修绿）⇒ 剩余 3 条改前已红。历史探针 `005t–061t` 仍含 `0x77`，本册 diff 只改 `046t/071t/072t`，其余改前改后一致 ⇒ 既存。
- **L1**：`make check` **rc=0**；**L2 采信日志** `.work/log/spec/SPEC-164t-check-L2.log`（`L2_EXIT=0`），另采信 `check-qemu-semantics` **967/978 PASS**、`check-lit-full` **12/12**。
- **无凑绿**：`check_scope.py`/`check_qemu_trans.py` **零改动**；`validate_encoding.py` 为纯增量加强（新增 `check_op_ha_value`），未删任何断言。

**约束核验**：29 条编码逐条相符 ✅；decode 逐 id 一致、旧前缀 0 ✅；scope 账面 6 项全对、`swym` 未动 ✅；实机 6 族全过 ✅；ADR 只注记未改正文 ✅；注入 2 次均红+还原 ✅；遗留 2 项确认既存 ✅。

**判决：Accepted**（29 条一条不差、decode 逐 id 全对、实机通过、门控全绿、注入可达红、遗留非本册引入；注入②下 `check-isa-coverage` 仍绿属预期——该门控看覆盖矩阵不看位级编码，编码门控已红，符合验收口径 6④）。

