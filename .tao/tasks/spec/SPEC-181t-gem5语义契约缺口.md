# SPEC-181t: gem5 语义契约缺口收口

**模块**：spec
**项目里程碑**：M11
**依赖**：`GEM5-002t`（语义矩阵，已验证）
**状态**：待验收

## 用户授权

用户 2026-11-01 接受 G1 语义矩阵，允许修 SPEC/契约任务；本任务只修规范/契约/ADR 状态，不写 gem5 实现。

## 已确认口径（2026-11-01 用户裁决）

- **F2**：`ADR-0044` 置 `Accepted`（decision 已确认）。
- **F5.1**：`ftrem/forem` 按 IEEE 754 remainder；`y=0`/`x=Inf`/sNaN ⇒ NV+qNaN；`y=Inf` ⇒ x；不置 NX/OF/UF。
- **F5.2 C1**：`ftsclb`/`fosclb` 第三操作数 `rfHD → rdHD`；同 `orrr` 编码，不新增 opcode/格式；`rdHD` 为 64 位有符号整数指数；`rd0` 作指数 = 0；旧 `rf,rf,rf` 写法失效。
- **F5.3**：`convert_f2i` 按 IEEE 754-2019；有限 inexact ⇒ NX；NaN/Inf/超范围 ⇒ 饱和 + NV。
- **F7**：`call` 返回地址 = 当前指令地址 + 4（相对/绝对两种形式一致）。
- **F8.1**：M11 保留粒度 = 精确地址 + 访问宽度。
- **F8.2**：`sc` 的 `rdHB = rd0` ⇒ ILLI（新增 `dst_rd0` 规则）。

## 目标

按 `GEM5-002t` 的矩阵与报告，处理已识别的规范缺口，形成可实现的明确口径：

1. **F1 `lr` 合法性**：当前矩阵 12 行 `legality` 为空，但 `SimRISC-12 §1.1` 要求 `hb == rd0`，否则 ILLI；确认并同步 `contracts`/`spec`，补测试项。
2. **F2 ADR-0044 状态**：`ADR-0044` 仍 `Proposed`，而 spec/contracts 已按 `fence ciii` 冻结；核对 decision 是否全部成立，按用户逐条确认后再改状态（不得自行 `Accepted`）。
3. **F5 FP 未明点**：`ftrem`/`ftsclb` 边界、`convert_f2i` NX 等；逐条定口径或明确保留为未实现/异常。
4. **F7 `call` 返回地址**：确认并写明 `IP+4` 语义（当前 spec 未逐字写）。
5. **F8 `lr/sc`**：保留标记粒度、`sc` 目的 `rd0` 合法性；明确平台/ISA 边界。
6. 输出逐条「结论 → 修改文件/章节 → 矩阵行 → 测试影响」，供 B1–B7 引用。

## 文件范围

- `spec/` 对应册（只改经确认的语义文字）
- `contracts/` 机器数据（`opcodes.yaml`/`legality_rules.yaml` 等）
- `.tao/adr/adr-0044-*`（仅状态/decision 经用户确认后）
- 本任务书、`.tao/knowledge/milestones.md`

**不改**：gem5 代码、tests、components、Makefile。

## 验收

1. F1/F2/F5/F7/F8 逐条有结论；每条注明用户授权/ADR decision 状态。
2. `contracts` 与 `spec` 同步；`check-legality-invariants`、`check-spec-*`、`check-contracts-*` 按现场实际跑并留真实 rc。
3. 矩阵行可回溯到修改后的 spec/contracts 依据；无“同助记符默认复用”。
4. 不自行把 ADR-0044 置 Accepted；如 decision 未确认，保持 Proposed 并登记遗留。
5. 完成区 ≤30 行，状态 `待验收`。

## 完成区

**测试结果**：`make -k check` rc=2（唯一 FAIL=`check-isa-coverage`：LLVM 后端仍按旧 `ftsclb/fosclb rf,rf,rf` 汇编；重派生 accept 262/reject 2。按任务边界不改 LLVM）。证据脚本 `.work/evidence/SPEC-181t/run.sh` rc=0（23 个门控 + 语义检查 33/33 PASS；两次注入→FAIL→`cp`+md5 还原→回绿）。其余 L1 全 PASS：`check-legality-invariants`/`check-fp-contract`/`check-scope`/`check-rule-refs`/`check-legality-drift`/`check-asm-list`/`check-asm-list-drift`/`check-spec-drift`/`numbering`/`changelog`/`purity`/`cite-targets`/`refs`/`codeblocks`/`readonly`/`archive`/`archive-verify`/`check-contracts-dir`/`pending`/`check-contract-relocs`/`validate-encoding`/`check-instrinfo`/`check-milestones-fresh` 均 rc=0。
**修改文件**：`spec/SimRISC-00/06/07/12`；`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`；`.tao/contracts/contract-fp.md`、`contract-isa.md`、`contract-asm-list.md`（生成物）；`.tao/adr/adr-0044-fence-ciii.md`；`tools/spec/generate_opcodes.py`（生成器同步）；`manifests/spec-readonly.lock.toml`（4 册 sha256）；本任务书、`.tao/knowledge/milestones.md`。
**验收结果**：F2 `ADR-0044` 置 `Accepted`（D1–D8 原文未改）；F5.1 remainder 边界/flag 写明；F5.2 C1 `ftsclb/fosclb` 第三操作数 `rdHD`（有符号 64 位整数指数，`rd0`=0，同 `orrr` 编码，旧 rf 写法失效）；F5.3 `convert_f2i` 有限 inexact⇒NX、NaN/Inf/超范围⇒饱和+NV；F7 `call` 返回地址=当前指令地址+4（相对/绝对一致）；F8.1 保留粒度=精确地址+访问宽度；F8.2 `sc.rdHB=rd0⇒ILLI`（12 条挂 `dst_rd0`，sc 编码未改）。矩阵行回溯：`ftrem_orrr_rf`/`forem_orrr_rf`/`ftsclb_orrr_rf`/`fosclb_orrr_rf`→SimRISC-07 §2.1+opcodes；`ft2it…fo2uo`→§1；`call_iiii_ra`/`call_rrii_ra`→SimRISC-06 §3；`sc.*`（12）→SimRISC-12 §1.1+opcodes `rule_refs`。`fp_semantics` 66 条 id/family/legality_refs 与 opcodes 双向一致（无操作数字段，未改结构）。
**新发现/坑**：① `generate_opcodes.py` 原缺 SPEC-180t 的 escape `imms18[17:1] == 0`，直接重生成会回退该语义；已补生成器并重生成。② `manifests/spec-readonly.lock.toml` 未列在任务书文件范围，但 Process-06 要求改只读册同笔更新 sha256；已按授权更新并留注。③ `check-isa-coverage` 红是 LLVM 后端未同步的必然结果，不是规范/契约内部不一致。
**遗留问题**：① F1（spec 现行文字已要求 `lr.hb==rd0` 否则 ILLI，但 contracts/legality 的 12 条 `lr` 仍为空）不在「已确认口径」内，未改；需用户裁定。② LLVM/QEMU/gem5/tests 未同步新语义（`ftsclb`/`fosclb`、sc legality、call IP+4、`convert_f2i` NX、remainder 边界、保留粒度），需另立实现/测试任务；`check-isa-coverage` 待 LLVM 落地后回绿。③ 未新增测试（按任务边界）。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：逐行审 spec/contracts/adr/generator 改动；重跑全部相关门控。
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F-1 `generate_opcodes.py` 缺 escape SBZ，重生成会回退 | ✅已修 | 补 `imms18[17:1] == 0` legality 与 `EXPR_TO_RULE` | 重生成 diff 无 escape 回退；`check-legality-invariants` rc=0 |
| F-2 spec 只读锁未同步 | ✅已修 | 4 册 sha256 + 授权注记 | `check-spec-readonly` rc=0 |
| F-3 生成区手工修改风险 | ✅已修 | 附录 A/B 全由生成器重生成 | `check-asm-list-drift`/`check-legality-drift` rc=0 |
| F-4 `ftsclb`/`fosclb` 生成物与散文 bank 不一致 | ✅已修 | 生成器 field `rdhd` + spec 散文/速查同步 | `check-spec-codeblocks`/`check-asm-list` rc=0 |
