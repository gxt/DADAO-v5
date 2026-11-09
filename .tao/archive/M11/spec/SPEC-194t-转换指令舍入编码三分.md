# SPEC-194t: 转换指令舍入编码三分（ADR-0050 D1–D7）

**模块**：spec
**项目里程碑**：M11
**依赖**：`ADR-0050`（Accepted，2026-11-06 用户确认 D1–D7）
**状态**：已验证

## 依据

`ADR-0050` 已冻结：

- **D1**：18 条格式转换按「结果是否依赖舍入」分三类 —— 15 条六档 one-hot、3 条精确 SBZ、4 条复制保留计数
- **D2**：六档 = `0x01` RNE / `0x02` RNA / `0x04` RTZ / `0x08` RUP / `0x10` RDN / `0x20` dynamic（读 `rf0`）
- **D3**：精确转换（`ft2fo`、`it2fo`、`ut2fo`）低 6 位 SBZ
- **D4**：复制类（`ft2ft`、`fo2fo`、`rd2rf`、`rf2rd`）保留 1–63 计数
- **D5**：inexact ⇒ NX（只实现 Exact 族）；NaN/Inf/越界 ⇒ 饱和 + NV，不置 NX
- **D6**：工具链映射（C f2i cast → `0x04`；i2f/`fo2ft` → `0x20`；固定方向语言 → 静态档）
- **D7**：QEMU/gem5 按字段方向；旧「`immu6`=个数」的转换编码作废（不兼容）

## 目标

1. `contracts/opcodes.yaml`：15 条转换的 `immu6` 语义改 one-hot，`rule_refs` 改为 `dst_rd0`/`dst_rf0` + `encode_onehot`，删除 `mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap`；3 条精确转换改为 `encode_sbz`（`immu6 == 0`），保留 `dst_rf0`；4 条复制完全不动。
2. `contracts/legality_rules.yaml`：`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap` 的覆盖范围描述收窄到「复制类与其它块指令」；`encode_onehot` 增列「转换族六档」；`encode_sbz` 增列「精确转换低 6 位」。
3. `spec/SimRISC-07`（格式转换指令节）：
   - 低 6 位语义按三类写明；
   - 六档方向定义与 `0x20` = dynamic；
   - NX/NV 口径（D5）；
   - 精确转换的 SBZ；
   - 删除「块转换/范围重叠」对转换族的适用（复制类保留）。
4. `.tao/contracts/contract-fp.md` §3/§12 同步（叙述 + 规则引用）。
5. `spec` 的 LEGALITY 块用 `tools/spec/gen_legality_list.py --apply` 重生成，`--verify` 必须一致。
6. 不改任何实现（LLVM/QEMU/gem5）与测试向量；实现迁移归 `INTEG-058t`。

## 范围 / 非范围

**在范围内**：`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`spec/SimRISC-07-浮点运算.md`、`.tao/contracts/contract-fp.md`、本任务书、`milestones.md`。

**不在范围**：LLVM/QEMU/gem5 实现、`tests/**`、`tools/**`（除 `gen_legality_list` 的生成动作）、其它 spec 册。

## 验收标准

1. `make check-legality-drift` rc=0；`make check-legality-invariants` rc=0；`gen_legality_list.py --verify` rc=0。
2. `make check-scope`、`validate-encoding`、`check-isa-coverage`、`check-asm-list`、`check-asm-list-drift` rc=0。
3. `make check-spec-refs`、`check-spec-numbering`、`check-spec-changelog`、`check-spec-purity`、`check-spec-cite-targets` rc=0；`make check`（L1）rc=0。
4. 编码位值（`opc`/`ha`/`mask`/`value`）不变；只改 `immu6` 语义与合法性/叙述。
5. 抽样核对：15 条 one-hot、3 条 SBZ、4 条计数，逐条与 ADR-0050 D1 对照；计数（22 条）现场统计，不写死。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务只改「规范与契约」，因此 `check-legality-drift`（spec LEGALITY 块 vs contracts）必须同步重生成，不能手改两块中的一块。
- 实现侧（LLVM 发码、QEMU/gem5 解码）在 `INTEG-058t` 落地前会与新契约不一致，属预期；本任务不跑依赖实现的语义门控（`check-inst` 等）作为验收项，但 L1 必须绿。

## 完成区

**测试结果**：一键证据脚本默认档 19/19 PASS；`--inject` 20/20 PASS（2 次注入→可达 FAIL→`cp`+md5 还原→回绿）。`make -k check`（L1）除 `check-patch-tree` 外全绿；该项失败为**预存环境问题**（gem5 `patches` 与共享组件检出不一致），在**主工作树同 HEAD、未含本任务改动**独立复现 rc=2，与本任务改动无交集（见遗留问题）。
**修改文件**：`contracts/opcodes.yaml`（15 条 `encode_onehot` / 3 条 `encode_sbz` / 4 条不动）、`contracts/legality_rules.yaml`、`spec/SimRISC-07-浮点运算.md`（§1 重写 + 附录 B 重生成）、`.tao/contracts/contract-fp.md`（§1/§2/§3/§4/§12/§15）、`.tao/knowledge/milestones.md`、本任务书。**越界披露（3 处，均为 L1/流程必需）**：`contracts/fp_semantics.yaml`（18 条 `legality_refs` 随 `rule_refs` 同步，否则 `check-fp-contract` 双源断言必红）、`tools/spec/check_fp_contract.py`（文法表 +3 行：`immu6 == 0 → encode_sbz`，否则 SBZ 表达式判「未识别」）、`manifests/spec-readonly.lock.toml`（本册 sha256 + 授权原话登记；未更新则 `check-spec-readonly` 红）。
**验收结果**：① 顺序 = 先改 contracts（opcodes + legality_rules + fp_semantics）→ `gen_legality_list.py --apply`（仅本册 `Injected`，其余 11 册 `idempotent`）→ `--verify` 12/12 OK。② 现场计数（脚本派生，不写死）：六档 15 / SBZ 3 / 复制 4 = 22；fp `rule_refs` = `encode_onehot` 17、`encode_sbz` 3、`mreg_zero` 10、`mreg_range_overflow` 10、`mreg_range_overlap` 2、`dst_rf0` 41、`dst_rd0` 15。③ 逐条核对：15 = 8 f2i + `fo2ft` + 6 不精确 i2f；3 = `ft2fo`/`it2fo`/`ut2fo`；4 = `ft2ft`/`fo2fo`/`rd2rf`/`rf2rd`，与 ADR-0050 D1–D4 一致；`opc/ha/mask/value` 与 HEAD 逐条相同（diff 仅 legality/rule_refs 行）。④ rc=0：`check-legality-drift`、`check-legality-invariants`、`gen_legality_list --verify`、`check-scope`、`validate-encoding`(264)、`check-isa-coverage`、`check-asm-list`、`check-asm-list-drift`、`check-asm-prose`、`check-spec-codeblocks`、`check-spec-refs`、`check-spec-numbering`、`check-spec-changelog`、`check-spec-purity`、`check-spec-cite-targets`、`check-spec-readonly`、`check-rule-refs`、`check-fp-contract`。
**新发现/坑**：① `.work` 是主树符号链接：证据脚本用 `resolve()` 推仓库根会指到主树、读到旧 contracts（首版因此假 FAIL）⇒ 仓库根必须显式传参。② `check_fp_contract.py` 的「legality 表达式 → 规则」是**封闭文法表**，新增形状（`immu6 == 0`）必须登记，否则判「未识别」（fail-closed）。③ 只读 spec 册的 sha256 锁须与 spec 改动**同笔**更新，注释留授权原话（本任务用 ADR-0050 确认记录「ADR0050确认」）。
**遗留问题**：① **汇编层仍是过渡态**（勿误读为最终形态）：本册只改「编码语义与合法性」；生成式 `附录 A` 汇编列表与 `check-asm-prose` 的块复制判据仍为窗口记法（`{a:b}`）。最终汇编形态（ADR-0050「2026-11-06 追加裁定（汇编层细化）」）：15 条六档与 3 条 SBZ 为**单寄存器、无花括号、第三操作数显式**（SBZ 写 `0`，六档写六值之一，如 `fo2io rd8, rf1, 0x04`、`ft2fo rf4, rf8, 0`），4 条复制保留 `{a:b}`；切换须 TD AsmString + `gen_asm_list.py` + `check_asm_prose.py` + spec 列表**同笔**改（`gen_asm_list.py` 会用 `llvm-mc` 校验，必须与 TD 同步），归实现线统一处理。② `encode_onehot` 生成摘要仍写「或 ≥ S」，对 FP 两族不适用（生成器固定文案）。③ `docs/fp-oracle-design.md` 仍描述「块形式（`immu6` 连续个数）」，待实现线更新（`docs/**` 不在范围）。④ `check-patch-tree` 预存失败（见测试结果），需在组件检出一致处复核，非本任务引入。

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：实现完成、可交独立验收。**逐行审查要点**：① YAML 锚点迁移核对——`&id002` 定义移到 `ft2ft`（唯一使用者 `fo2fo` 在其后）、新增 `&id007` 于 `it2fo`（`ut2fo` 在其后），全部 `*id00x` 使用点均在定义之后，无「先引用后定义」。② 15 条六档 legality 与 `ftrnd`/`fornd` 现有表达式**逐字符同形**（含 YAML 折行），确保走同一文法分类。③ 3 条 SBZ 用 `immu6 == 0`（而非删 legality），保证「非 0 ⇒ ILLI」仍机械可判。④ `mreg_*` 收窄后残余清单与现场一致（10/10/2），复制类 4 条保持原表达式（`no_overlap` 只余 `ft2ft`/`fo2fo`）。⑤ 规则描述计数与现场引用数一致（21 / 3 / 10）。⑥ spec §1 自洽：15+3+4=22（本册 20 + SimRISC-02 的 2 条）；目的/源字段逐条对照 opcodes；D5 的 NX/NV、`0x20` 动态、SBZ 均落文；无 `scope`/任务号/ADR 号（purity 0 命中）。⑦ 反例可达：`extra-ref` 命中分类断言 + drift + fp-contract；`sbz-to-count` 命中四处；无恒真检查。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 证据脚本按 `resolve()` 定位仓库根，`.work` 为符号链接 ⇒ 读到主树旧 contracts（假 FAIL） | ✅已修 | 分类脚本改由 `run.sh` 传仓库根；3 处调用点同步 | 分类 PASS；`--inject` 20/20 |
| F2 注入器锚点写错致「半注入」，且注入失败未被计为 FAIL（曾留下未还原文件） | ✅已修 | 改为「先全量校验锚点唯一、再一次性落盘」；失败即 `cp` 还原并置 `fail=1` | 两次注入均「非空注入」且 md5 复原 28ddfbb3 |
| F3 只读册 sha256 锁未随 spec 改动更新 ⇒ `check-spec-readonly` 红 | ✅已修 | 锁内本册 sha256 + 授权原话注释 | `check-spec-readonly: 21 read-only spec volume(s) OK` rc=0 |
| F4 `tools/spec/check_fp_contract.py` 文法表缺 `immu6 == 0` ⇒ SBZ 表达式判「未识别」 | ✅已修（披露） | 文法表 +3 行；`--self-test` 复跑 | `check-fp-contract: PASS`（含 self-test PASS） |
| F5 附录 A 生成列仍是窗口记法，与新叙述不一致 | ⏸延后（已裁定） | 按 ADR-0050「2026-11-06 追加裁定（汇编层细化）」：汇编形态由实现线统一切换（单寄存器无花括号 + TD/gen_asm_list/check_asm_prose 同笔改）；本册不改 `tools/**` | §1 尾注 + 完成区遗留① 明示「过渡态」 |

#### 第 1 轮 reviewer 验收

**判决**：**Accepted**（附 4 条 finding，其中 F1/F2 为文档级数字笔误，交 architect 收尾提交直改，不返工）。以下均为 reviewer 在任务 worktree（分支 `SPEC-194t`，HEAD `7fb1ed14` + 未提交改动）以相对路径**独立重跑**的真实结果，不采信完成区转述。

**重跑记录（真实 rc）**
- 运行期证据脚本 → `RC=0`，`PASS=19 FAIL=0`（13.3s）；运行期证据脚本 `--inject` → `INJECT_RC=0`，`PASS=20 FAIL=0`（两模式非空注入 → 可达 FAIL → `cp`+md5 复原 `28ddfbb3` → 回绿）。
- 逐条独立重跑，**全部 rc=0**：`check-legality-drift`、`check-legality-invariants`、`check-scope`、`validate-encoding`（`264 条记录 OK`）、`check-isa-coverage`、`check-asm-list`、`check-asm-list-drift`、`check-asm-prose`、`check-spec-refs/numbering/changelog/purity/cite-targets/readonly/codeblocks`、`check-rule-refs`、`check-fp-contract`（17 项 PASS）、`check-knowledge-refs`、`gen_legality_list.py --verify`（12 册 OK）、`check_fp_contract.py --self-test`（11 例 PASS、fail-closed 保留）。
- `gen_legality_list.py --apply` → 12 册全 `unchanged (idempotent)`，apply 前后 `md5sum spec/*.md` 逐册相同 ⇒ LEGALITY 块确为生成器产物、非手改。
- `make -k check`（L1）→ **rc=2**：唯一失败 `check-patch-tree`（`Error 1`），日志 `[FAIL]` 行 = 0、`[PASS]` 1092 行，其余全绿；`check-patch-tree` 在**主工作树（master `d8a7af8b`，未含本任务改动）**独立复现 **rc=2、同样 6 条 gem5 补丁问题**（`src/arch/dadao/{process.cc,process.hh,se_workload.cc}` 断言⑨/⑥）⇒ 共享 gem5 源树/补丁集预存问题，与本任务改动无交集（本任务不碰 `components/`），按裁定不判返工。
- **独立注入（reviewer 自做，非 engineer 自检）**：`cp contracts/opcodes.yaml` 备份 + 记 md5 `28ddfbb3`；改 `ut2fo` `encode_sbz → mreg_zero`（md5 → `ca3f4d3f`）⇒ `check-legality-drift rc=2`（`LEGALITY content drift`，`1 violation(s), 11 OK`）、`check-fp-contract rc=2`（`rule_refs == legality_refs 实际=1 条`）、`gen --verify rc=1`（`SimRISC-07 MISMATCH`）；`cp` 还原 + `md5sum -c` OK ⇒ 三项回 rc=0；`git status` 与验收前快照逐行一致、7 个目标文件 md5 全部复原。

**约束核验**
1. **分类**：现场派生 20 条 `x2y` 转换 + `rd2rf`/`rf2rd` = 22；六档 15（8 `f2i` + `fo2ft` + `it2ft/io2ft/ut2ft/uo2ft/io2fo/uo2fo`）、SBZ 3（`ft2fo`/`it2fo`/`ut2fo`）、复制 4（`ft2ft`/`fo2fo`/`rd2rf`/`rf2rd`），与 ADR-0050 D1–D4 逐条一致（`it2fo`/`ut2fo` 确在 SBZ、`io2fo`/`uo2fo`/`it2ft`/`ut2ft`/`io2ft`/`uo2ft`/`fo2ft` 确在六档）。
2. **合法性**：15 条 legality 恰为六值 `1/2/4/8/16/32` 且 `rule_refs` 恰 `{dst_rd0|dst_rf0, encode_onehot}`；3 条 `immu6 == 0` + `{dst_rf0, encode_sbz}`；4 条复制的 `legality`/`rule_refs` 与 HEAD 解析值完全相同；全 264 条 `opc/ha/mask/value` **零差异**（脚本逐字段比对 + diff 无相关改动行）；`legality_rules.yaml` 收窄后 `mreg_zero`/`mreg_range_overflow` 各 10 条、`mreg_range_overlap` 4 条（`rd2rd`/`rb2rb`/`ft2ft`/`fo2fo`），复制类未被误伤；`encode_onehot` 现场 21 条与描述一致。
3. **规范一致**：spec §1（六档表、`0x20` 动态读 `rf0[33:32]`、inexact⇒NX / 饱和+NV 不置 NX、SBZ、18 条非块）与 `contract-fp` §1/§3/§4/§12 口径一致；`--verify` 12/12。
4. **越界 3 处必要且最小**：`fp_semantics.yaml`（18 条 `legality_refs` 同步，否则 Check 8 必红）、`check_fp_contract.py`（+3 行登记 `immu6 == 0 → encode_sbz`，封闭文法仍 fail-closed）、`spec-readonly.lock.toml`（sha256 + 授权原话「ADR0050确认」，ADR-0050 §确认记录在案，满足 `docs/Process-06 §2/§5`）；`git diff --name-only` 9 项与完成区「修改文件」逐一对齐，无其它越界。
5. **过渡态**：spec §1 尾注明示附录 A 仍为窗口记法；完成区遗留① 归 `INTEG-058t`（master 上该任务书已含「单寄存器、无花括号、第三操作数显式 + `gen_asm_list.py`/`check_asm_prose.py` 同笔」），ADR-0050 追加裁定在 master 在案。
6. **完成区**：8 行（≤30），全文无绝对/运行期路径；状态 `待验收`；证据落主树运行期证据目录（非易失）。

**Finding（均不阻断）**
- **F1（文档级数字笔误）**：`spec/SimRISC-07` §1.5「目的为 `rf` 组的 **14 条**（`fo2ft`/`ft2fo`/`ft2ft`/`fo2fo`、8 条整数→浮点）」——括号内 4+8=**12**，应写 12 条；改册须同笔重算只读锁 sha256。
- **F2（文档级数字笔误）**：`.tao/contracts/contract-fp.md` §12 `mreg_range_overlap`「其余 **16 条**格式转换」应为 **18 条**（与同段「18 条非复制类」、`legality_rules.yaml` 三处「18 条」、spec §1 一致；现场 20−2=18）。
- **F3（脚本健壮性提示）**：`check_classes.py` 无参默认 `Path(__file__).resolve().parents[3]` 在任务 worktree 内因 `.work` 符号链接解析到主树，单独调用会读主树 contracts；`run.sh` 已显式传仓库根，当前无影响。
- **F4（生成器固定文案）**：spec LEGALITY 块 `encode_onehot` 短语「非 one-hot 或 ≥ S」对 FP 六档不适用（engineer 已列遗留②；`legality_rules.yaml` 正文已写清两族差异）。

#### 收尾（architect，2026-11-06）

- F1/F2 已直改：`spec/SimRISC-07 §1.5` 目的 rf 组计数 14→12；`contract-fp §12` 其余格式转换计数 16→18；`spec-readonly` 锁 sha256 同笔重算（授权同 ADR-0050「ADR0050确认」）。
- F3：`check_classes.py` 无参默认根在任务 worktree 内会解析到主树（`run.sh` 已显式传根），记遗留。
- F4：LEGALITY 生成器 `encode_onehot` 文案「非 one-hot 或 ≥ S」对 FP 六档不适用（生成器固定文案），记遗留。
- 判决 Accepted，状态置 `已验证`。
