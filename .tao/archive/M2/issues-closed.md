# M2 阶段已关闭 Issue（≤ 2026-10-04）

> **来源**：INTEG-010t（2026-10-04）从 `.tao/knowledge/issues.yaml` 提取——**M2 阶段（2026-09-23 ~ 2026-10-04）已 `closed` 的 issue**。
>
> **判据**：M2 达成 = **2026-10-04**（commit `4753fe2`，`milestones.md` M2 置达成）。`resolved_by` 对应任务提交日 ≤ 2026-10-04（实测 `git log --grep <taskID>`；边界「≤ 达成日」）。
>
> **未提取**：M1 阶段（≤ 2026-09-22）的 8 条见 `.tao/archive/M1/issues-closed.md`；本次提取后活台账 `.tao/knowledge/issues.yaml` 仅保留 open 项。

**共 41 条**（按原 `issues.yaml` 顺序）。

| id | title | scope | resolved_by |
| --- | --- | --- | --- |
| `ISS-002` | SPEC-002t/003t 产出（contract-isa.md、opcodes.yaml）在 spec 重排后需重新生成，旧文件暂作参考 | [spec, M1] | SPEC-016t/018t（2026-09-28，合约重组 + 版本引用同步）+ SPEC-019t（2026-09-28，工具脚本重新生成） |
| `ISS-004` | 浮点支持（M1 不含）——路线已由用户 2026-10-03 裁定为原生浮点，soft-float libcall 方案被否决 | [post-M1] | 用户 2026-10-03 裁定原生浮点（全工具链），否决 0628 的 soft-float libcall 路线（SPEC-086t §裁定 / SPEC-087t）；FP 60/60 已实现（SPEC-086t~089t、LLVM-029t~031t、QEMU-034t~038t） |
| `ISS-007` | Object ABI（SPEC-005t）：EM_DADAO 注册状态、e_flags 命名空间策略、M1 是否用 target linker | [M1] | e_flags 由 ADR-0003（+修订）+ LLVM-014t（2026-09-22）落地；EM_DADAO 注册状态已文档化；M1 无 link 步骤 |
| `ISS-009` | Spec 冻结（SPEC-010t）：impact matrix 是否覆盖 M1 之外的实现目标 | [M1] | SPEC-010t 定稿：impact matrix 明确 M1-only by design（docs/impact-matrix.md L3/L27） |
| `ISS-010` | 编码表变更的下游影响：legality_rules.yaml 中 M1 排除项规则仍 active，需在 SPEC-009t/INFRA-010t 明确 M1 流程过滤 | [M1] | SPEC-086t（2026-10-03，scope 分区 m1\|fp\|excluded）+ SPEC-089t（2026-10-04，rule_refs 按 scope 计算） |
| `ISS-016` | make prepare 非幂等——apply_series.py 要求 HEAD 等于基线 commit，已 patched 的组件会整体失败 | [infra] | 补丁集重整（2026-09-23）：apply_series.py 重写为 git apply 路径 + 幂等检测，工作树 HEAD 恒等于 base commit |
| `ISS-017` | F5 — UNDI（保留编码）的向量层表达——已改由 TESTCASES-008t 承载（方案 A：class=legality + encoding.reserved=true） | [testcases] | TESTCASES-008t（2026-09-16，方案 A） |
| `ISS-018` | F6 — encoding 类对恒 fault 指令（illi）豁免——schema.md 已澄清，覆盖率由 legality active 满足 | [testcases] | TESTCASES-002t/schema.md 澄清（F6） |
| `ISS-020` | 覆盖率门控分层：validate_vectors.py 覆盖率为声明级（177/177），数据级覆盖率不在该 validator 内 | [testcases] | TESTCASES-009t/011t：数据级覆盖率门控已入 validate_vectors.py |
| `ISS-021` | 并行前提不成立：002t 未交付 inventory 生成脚本，各数据任务须手改 inventory.md → 默认全串行 | [testcases] | M1 达成（2026-09-22）：数据向量任务已全部收敛，inventory 由 validate_vectors 机械核对 |
| `ISS-022` | 数据已随上一版 002t 一并丢弃——003t~007t 的向量数据须从零生成（003t/004t/005t 已完成 10 个 isa/*.yaml） | [testcases] | TESTCASES-003t~007t 完成；M1 覆盖 152/152（TESTCASES-012m 里程碑） |
| `ISS-027` | mem-* 边界覆盖未穷尽所有 format 组合——rrri 的 MALIGN 未生成，属 M1 最小覆盖 | [testcases] | M1 达成：M1 最小覆盖已接受（mem-rd 含 22 项 boundary；M1 152/152） |
| `ISS-028` | br.* 无 legality/boundary 用例——br.* 不产生 fault，由 009t 兜底确认 | [testcases] | TESTCASES-005t/011t（boundary）+ TESTCASES-009t（兜底确认） |
| `ISS-029` | schema.md 新增 encoding.reserved 字段——下游消费者须识别 reserved case 的 UNDI 处理 | [testcases] | TESTCASES-008t（schema）+ validate_vectors 落地消费者处理 |
| `ISS-030` | notes 文本笔误（006t 遗留 N-1）：ctrl-call.yaml case[7] notes 写 'low 48=0xAAAA000000000000'（多 4 个 0） | [testcases] | TESTCASES-018t（2026-09-29）：notes 订正为 0xAAAA00000000（48 位），生成器 + ctrl-call.yaml 同步，幂等；reviewer Accepted |
| `ISS-031` | call/ret 覆盖维度未穷尽：call-iiii shift-push 无独立 semantic，ret 仅覆盖单级 pop | [testcases] | TESTCASES-006t/011t/018t/022t：shift-push semantic + 多级 pop/MemRAS 用例已补 |
| `ISS-042` | rela.si fixup 占位语义与 M2 不兼容：getFixupKindForInstr 按 >>2 计算，但 rela.si 实际为 imms18<<12 | [llvm, M2] | SPEC-056t |
| `ISS-056` | fence 已移出 M1（excluded_m1）——trans_fence 恒 ILLI 现为合规行为（excluded 指令应 ILLI） | [qemu] | SPEC-039t |
| `ISS-057` | MemRAS 路径（ra0 低 48≠0）未实现——gen_ras_push/pop 硬编码走 ra0==0 分支 | [qemu] | QEMU-013t 实现；ADR-0012 D7 取代 MemRAS 引用计数语义（QEMU-030t，2026-09-30 核实） |
| `ISS-060` | rd2ra/ra2rd 缺独立测试向量——QEMU-013t 不改向量，归属 TESTCASES 侧补 | [qemu, testcases] | TESTCASES 侧已覆盖（reg-imm-block.yaml 含 rd2ra/ra2rd 的 encoding/semantic/legality/overlap；TESTCASES-003t 起） |
| `ISS-061` | harness 普通模式 TIMEOUT（QEMU-014t 后续实测）——根因 = TB 续接缺陷，015t 以 workaround 消除 | [qemu] | QEMU-022t（2026-09-21，TB 续接缺陷根治）+ QEMU-015t（workaround） |
| `ISS-062` | --dump 的 rb[1..63] 全 0、pc=0——根因 = TB 续接缺陷，dumper 超 TB 上限后死循环 | [qemu] | QEMU-022t（2026-09-21，TB 续接 + exit-port halt 修复） |
| `ISS-063` | QEMU dadao target 的 TB 续接缺陷——tb_stop 缺 gen_update_pc，已由 QEMU-022t 新建补丁 0008 | [qemu] | QEMU-022t（2026-09-21，补丁 0008） |
| `ISS-065` | 源树提交作者为 Reviewer <reviewer@example.com>——git config 未设置项目约定身份 | [infra, qemu] | 补丁集重整（2026-09-23）：git apply 路径不再产生 patch commit，作者信息问题自然消失 |
| `ISS-070` | test_encoding_oracle.py 用例去重：扩展后 TESTS=57 但去重后仅 50 条（7 条旧用例被重复登记） | [llvm] | LLVM-022t（2026-09-29，oracle 去重 68→61 + 交叉检查） |
| `ISS-071` | fence 的 LLVM 侧 lit 缺口——fence 无任何 lit 指令行，LLVM 侧实测可汇编且编码正确 | [llvm] | SPEC-039t（2026-09-29）：fence 移出 M1 ⇒ scope: excluded |
| `ISS-073` | check_lit_bytes.py 两项可选增强：无 CLI（LIT_DIR 硬编码）+ 独立计数门控不能捕获整行 # OBJ: 被删除 | [llvm] | LLVM-022t（2026-09-29，check_lit_bytes 加 `--lit-dir`/`--min-obj`） |
| `ISS-075` | 文档分层改造 T1/T2/T3 收尾遗留（adr-0017 指针、assembly-list 旧路径、contract-asm-list 漂移门控、Toolchain-01 陈旧计数、docs/README 措辞、fetch.py 注释、E5 恢复步骤）——全部消解 | [spec, infra] | SPEC-085t（T2）+ INFRA-027t（收尾，2026-10-03） |
| `ISS-076` | cls 多寄存器化后 spec 正文/内嵌速查表/assembly-list 暂不一致——已由 LLVM-023t 消解 | [spec] | LLVM-023t（2026-09-29）：gen_asm_list.py _MULTI_REG_MNEMONICS 加 focls/ftcls 并重生成 |
| `ISS-083` | rf2rd 目的 rd0 的 dst_rd0 缺口（合约↔spec 不一致）——SPEC-089t 已收口 | [spec, llvm, qemu] | SPEC-089t（2026-10-04）：R2b (A) 全补 15 条（含 rf2rd）dst_rd0，opcodes.yaml + fp_semantics.yaml 双边 + Check 8 交叉断言；汇编期 LLVM-031t、运行期 QEMU-038t（2026-10-04）两侧落地 |
| `ISS-084` | FP 实现期：FP 专属规则翻 active + 回填 rule_refs（SPEC-087t）——SPEC-089t 已完成 | [spec] | SPEC-089t（2026-10-04）：_compute_rule_refs 收窄为 scope==excluded 才置空、EXPR_TO_RULE +7、dst_rf0/encode_fp_root_n 翻 active、重跑 gen_legality_list |
| `ISS-085` | mreg_range_overlap 落地任务 B1/B2/B3（QEMU-033t / LLVM-028t / TESTCASES-023t）——全部完成 | [spec, qemu, llvm, testcases] | QEMU-033t + LLVM-028t + TESTCASES-023t（均 2026-10-03） |
| `ISS-086` | check-spec-refs 的 76 条历史既存违规（18 Check1 + 58 Check2；standalone，非本任务引入） | [spec, infra] | SPEC-094t（2026-10-04）：check-spec-refs 76→0（含返工收窄 rule b/c 假阴性） |
| `ISS-091` | 13 个历史任务书「完成区已填但状态仍待验收」（漏 /complete）——已消解 | [infra] | 2026-10-03 回填台账 + 状态（用户批准）；check-tasks 现列 0 |
| `ISS-092` | LLVM/QEMU 缓存重新浅克隆——已完成 | [infra] | 2026-09-29：llvm-project.git 378M(shallow) + qemu.git 52M(shallow)，2m50s，pinned commit 均存在 |
| `ISS-095` | check-lit 接入 make check + check-asm-prose 转 --strict——已落地 | [infra] | INFRA-021t（2026-10-02） |
| `ISS-096` | 既有 reg-imm-block.yaml 同组重叠用例与 mreg_range_overlap 相违——TESTCASES-023t 已消解 | [testcases] | TESTCASES-023t（2026-10-03）：两条改 ILLI + 各新增完全重合用例，向量 692→694 |
| `ISS-101` | SPEC-024t 暴露的测试向量 src 预置缺口（15 条）为误报——已订正 | [testcases] | SPEC-031t（2026-09-28）：role 字段恢复，hb 实为目的寄存器 |
| `ISS-105` | FP 汇编期静态合法性检查（dst_rf0/mreg_range_overlap/mreg_range_overflow/encode_fp_root_n）——LLVM-030t 已完成 | [llvm] | LLVM-030t（2026-10-03）；lit 28→29 |
| `ISS-113` | check_interface_alignment.py 非递归 glob 致 23 项 FAIL——INTEG-005t 已消解 | [integ] | INTEG-005t（2026-09-25）：iter_patch_files() 递归 glob + 空集硬错误，80/80 EXIT 0 恢复 |
| `ISS-127` | QEMU-037t FP softfloat 算术族（arith 12 + root 2）已完成——FP 执行层 60/60 收口 | [qemu] | QEMU-037t（2026-10-03）；探针 91/91、make check EXIT=0 |

## 原始 YAML（提取前逐条）

```yaml
- id: ISS-002
  title: "SPEC-002t/003t 产出（contract-isa.md、opcodes.yaml）在 spec 重排后需重新生成，旧文件暂作参考"
  status: closed
  scope: [spec, M1]
  blocks: []
  resolved_by: "SPEC-016t/018t（2026-09-28，合约重组 + 版本引用同步）+ SPEC-019t（2026-09-28，工具脚本重新生成）"
  notes: "INFRA-033t（2026-10-04）判定：contract-isa.md / contracts/opcodes.yaml 已按 spec 0.5.4 重排重生成（现 227 条 = M1 152 + fp 60 + excluded 15），『旧文件暂作参考』已不适用 ⇒ closed。"

- id: ISS-004
  title: "浮点支持（M1 不含）——路线已由用户 2026-10-03 裁定为原生浮点，soft-float libcall 方案被否决"
  status: closed
  scope: [post-M1]
  blocks: []
  resolved_by: "用户 2026-10-03 裁定原生浮点（全工具链），否决 0628 的 soft-float libcall 路线（SPEC-086t §裁定 / SPEC-087t）；FP 60/60 已实现（SPEC-086t~089t、LLVM-029t~031t、QEMU-034t~038t）"
  notes: "原主张『以 soft-float libcall 接入、不注册 FP 寄存器类』已被否决。否决策略去向：原生浮点（`scope: fp` 60 条）——执行层 QEMU-034t~037t、编码层 LLVM-029t、汇编期合法性 LLVM-030t/031t、运行期合法性 QEMU-038t；语义合约 contract-fp.md + contracts/fp_semantics.yaml（SPEC-087t/088t/089t）。"

- id: ISS-007
  title: "Object ABI（SPEC-005t）：EM_DADAO 注册状态、e_flags 命名空间策略、M1 是否用 target linker"
  status: closed
  scope: [M1]
  blocks: []
  resolved_by: "e_flags 由 ADR-0003（+修订）+ LLVM-014t（2026-09-22）落地；EM_DADAO 注册状态已文档化；M1 无 link 步骤"
  notes: "INFRA-033t（2026-10-04）逐项判定：① e_flags 命名空间策略 = ADR-0003 §D1（`e_flags=0x00000001`）+ LLVM-014t 实测落地（e_flags.s lit）；② EM_DADAO=0x0DA0 project-custom、未注册，已由 contract-elf.md §1.3 显式文档化（非缺口）；③ M1 单 TU 自包含、无 link 步骤（contract-elf.md §6）⇒ 三项均已消解，closed。"

- id: ISS-009
  title: "Spec 冻结（SPEC-010t）：impact matrix 是否覆盖 M1 之外的实现目标"
  status: closed
  scope: [M1]
  blocks: []
  resolved_by: "SPEC-010t 定稿：impact matrix 明确 M1-only by design（docs/impact-matrix.md L3/L27）"
  notes: "INFRA-033t（2026-10-04）判定：`docs/impact-matrix.md` 显式限定「实现目标标签（仅 M1）」，M1 外（LLVM CodeGen/gem5/Sail）统一标 `Deferred（M1 外）`；这是设计选择而非缺口，M1 已达成 ⇒ closed。"

- id: ISS-010
  title: "编码表变更的下游影响：legality_rules.yaml 中 M1 排除项规则仍 active，需在 SPEC-009t/INFRA-010t 明确 M1 流程过滤"
  status: closed
  scope: [M1]
  blocks: []
  resolved_by: "SPEC-086t（2026-10-03，scope 分区 m1|fp|excluded）+ SPEC-089t（2026-10-04，rule_refs 按 scope 计算）"
  notes: "INFRA-033t（2026-10-04）判定：旧『M1 排除布尔字段』已退役，改为逐条 `scope ∈ {m1,fp,excluded}`；`check_scope.py` 机械断言 `scope!=m1 ⇔ decode:ILLI`，`_compute_rule_refs` 按 scope 过滤 ⇒ M1 流程过滤已机械化，closed。"

- id: ISS-016
  title: "make prepare 非幂等——apply_series.py 要求 HEAD 等于基线 commit，已 patched 的组件会整体失败"
  status: closed
  scope: [infra]
  blocks: []
  resolved_by: "补丁集重整（2026-09-23）：apply_series.py 重写为 git apply 路径 + 幂等检测，工作树 HEAD 恒等于 base commit"
  notes: "原 backlog L81 标 ✅已消解；本次合并据此关闭。"

- id: ISS-017
  title: "F5 — UNDI（保留编码）的向量层表达——已改由 TESTCASES-008t 承载（方案 A：class=legality + encoding.reserved=true）"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-008t（2026-09-16，方案 A）"
  notes: "INFRA-033t（2026-10-04）判定：`tests/vectors/schema.md` §保留编码 case（L40–72）落地 `encoding.reserved: true`；`tests/vectors/isa/reserved.yaml` 已存在 ⇒ closed。"

- id: ISS-018
  title: "F6 — encoding 类对恒 fault 指令（illi）豁免——schema.md 已澄清，覆盖率由 legality active 满足"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-002t/schema.md 澄清（F6）"
  notes: "INFRA-033t（2026-10-04）判定：`tests/vectors/schema.md` §「encoding 类对恒 fault 指令的豁免（F6）」（L167+）已澄清；illi 等恒 fault 指令不构造 encoding case，覆盖率由 legality active 满足 ⇒ closed。"

- id: ISS-020
  title: "覆盖率门控分层：validate_vectors.py 覆盖率为声明级（177/177），数据级覆盖率不在该 validator 内"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-009t/011t：数据级覆盖率门控已入 validate_vectors.py"
  notes: "INFRA-033t（2026-10-04）判定：`tools/testcases/validate_vectors.py` L730–754 已实现数据级门控——inventory 声明 `✓` 的 (id,class) 若无 active 数据 case 即 `DATA COVERAGE GAP` 并 `sys.exit(1)`（TESTCASES-011t 转严）⇒ 数据级覆盖已入 validator，closed。"

- id: ISS-021
  title: "并行前提不成立：002t 未交付 inventory 生成脚本，各数据任务须手改 inventory.md → 默认全串行"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "M1 达成（2026-09-22）：数据向量任务已全部收敛，inventory 由 validate_vectors 机械核对"
  notes: "INFRA-033t（2026-10-04）判定：该 issue 是 M1 期『任务可并行性』的过程前提；M1 已达成、003t~007t 全部完成，`validate_vectors.py` 现已机械校核 inventory 行集与 opcodes M1 身份集一致（无缺/无多/无重复）⇒ 并行前提问题不再成立，closed。"

- id: ISS-022
  title: "数据已随上一版 002t 一并丢弃——003t~007t 的向量数据须从零生成（003t/004t/005t 已完成 10 个 isa/*.yaml）"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-003t~007t 完成；M1 覆盖 152/152（TESTCASES-012m 里程碑）"
  notes: "INFRA-033t（2026-10-04）判定：`tests/vectors/isa/` 现含 15 个 yaml（含 reserved.yaml），`validate_vectors` M1 152/152、gap 0，向量已从零重建完成 ⇒ closed。"

- id: ISS-027
  title: "mem-* 边界覆盖未穷尽所有 format 组合——rrri 的 MALIGN 未生成，属 M1 最小覆盖"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "M1 达成：M1 最小覆盖已接受（mem-rd 含 22 项 boundary；M1 152/152）"
  notes: "INFRA-033t（2026-10-04）判定：题面自述『属 M1 最小覆盖』；M1 已达成（2026-09-22）、M1 覆盖 152/152、gap 0，未穷尽的 format 组合属 M1 之外的非阻塞增强 ⇒ closed。"

- id: ISS-028
  title: "br.* 无 legality/boundary 用例——br.* 不产生 fault，由 009t 兜底确认"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-005t/011t（boundary）+ TESTCASES-009t（兜底确认）"
  notes: "INFRA-033t（2026-10-04）判定：`tests/vectors/isa/ctrl-br.yaml` 现含 10 项 boundary case（无 legality，因 br.* 不产生 fault）；009t 全量再审计已验证 ⇒ closed。"

- id: ISS-029
  title: "schema.md 新增 encoding.reserved 字段——下游消费者须识别 reserved case 的 UNDI 处理"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-008t（schema）+ validate_vectors 落地消费者处理"
  notes: "INFRA-033t（2026-10-04）判定：`tools/testcases/validate_vectors.py` L222–292 已实现 `encoding.reserved` 消费（class/expected_fault/status/word 约束校验），下游消费者已识别 reserved→UNDI ⇒ closed。"

- id: ISS-030
  title: "notes 文本笔误（006t 遗留 N-1）：ctrl-call.yaml case[7] notes 写 'low 48=0xAAAA000000000000'（多 4 个 0）"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-018t（2026-09-29）：notes 订正为 0xAAAA00000000（48 位），生成器 + ctrl-call.yaml 同步，幂等；reviewer Accepted"

- id: ISS-031
  title: "call/ret 覆盖维度未穷尽：call-iiii shift-push 无独立 semantic，ret 仅覆盖单级 pop"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-006t/011t/018t/022t：shift-push semantic + 多级 pop/MemRAS 用例已补"
  notes: "INFRA-033t（2026-10-04）判定：`ctrl-call.yaml` 现含 C3a shift-push semantic（call-iiii 与 call-rrii 各有）；`ctrl-ret.yaml` 现含 D2 count>1、D3 pop、D4b MemRAS 多级用例及 ret rd1 semantic ⇒ 覆盖维度已补全，closed。"

- id: ISS-042
  title: "rela.si fixup 占位语义与 M2 不兼容：getFixupKindForInstr 按 >>2 计算，但 rela.si 实际为 imms18<<12"
  status: closed
  scope: [llvm, M2]
  blocks: []
  resolved_by: "SPEC-056t"
  notes: "`rela.si` 已删除（ADR-0012 D5，2026-09-30），编码 0x5A → UNDI，问题消失。"

- id: ISS-056
  title: "fence 已移出 M1（excluded_m1）——trans_fence 恒 ILLI 现为合规行为（excluded 指令应 ILLI）"
  status: closed
  scope: [qemu]
  blocks: []
  resolved_by: "SPEC-039t"
  notes: "SPEC-039t：fence 标 `excluded_m1: true`（与浮点/特权 cfx/LR-SC 一致），M1 身份集 178→177。trans_fence 恒 ILLI 对 excluded 指令合规，本 issue 不再是缺陷。"

- id: ISS-057
  title: "MemRAS 路径（ra0 低 48≠0）未实现——gen_ras_push/pop 硬编码走 ra0==0 分支"
  status: closed
  scope: [qemu]
  blocks: []
  resolved_by: "QEMU-013t 实现；ADR-0012 D7 取代 MemRAS 引用计数语义（QEMU-030t，2026-09-30 核实）"
  notes: "原 backlog L165 标「已关闭」；本次合并据此关闭。"

- id: ISS-060
  title: "rd2ra/ra2rd 缺独立测试向量——QEMU-013t 不改向量，归属 TESTCASES 侧补"
  status: closed
  scope: [qemu, testcases]
  blocks: []
  resolved_by: "TESTCASES 侧已覆盖（reg-imm-block.yaml 含 rd2ra/ra2rd 的 encoding/semantic/legality/overlap；TESTCASES-003t 起）"
  notes: "INFRA-033t（2026-10-04）判定：`tests/vectors/isa/reg-imm-block.yaml` 现含 `rd2ra_orri_ra`（encoding/semantic/legality/overlap）与 `ra2rd_orri_ra`（encoding/semantic/legality×2/overlap）用例（自 TESTCASES-003t 存在，2026-09-28 TESTCASES-013t/015t 对齐）⇒ 向量缺口已补，closed。"

- id: ISS-061
  title: "harness 普通模式 TIMEOUT（QEMU-014t 后续实测）——根因 = TB 续接缺陷，015t 以 workaround 消除"
  status: closed
  scope: [qemu]
  blocks: []
  resolved_by: "QEMU-022t（2026-09-21，TB 续接缺陷根治）+ QEMU-015t（workaround）"
  notes: "INFRA-033t（2026-10-04）判定：根因（TB 续接）已由 QEMU-022t（补丁 0008，gen_update_pc + 可靠 halt）根治；`make check-qemu-semantics` 现 149/149 ⇒ closed。"

- id: ISS-062
  title: "--dump 的 rb[1..63] 全 0、pc=0——根因 = TB 续接缺陷，dumper 超 TB 上限后死循环"
  status: closed
  scope: [qemu]
  blocks: []
  resolved_by: "QEMU-022t（2026-09-21，TB 续接 + exit-port halt 修复）"
  notes: "INFRA-033t（2026-10-04）判定：QEMU-022t 修复后 `--dump` 的 rb1/rb2/rb62 与 pc=0xffff00000210 均正确（见 `.tao/archive/M1/README.md`）⇒ closed。"

- id: ISS-063
  title: "QEMU dadao target 的 TB 续接缺陷——tb_stop 缺 gen_update_pc，已由 QEMU-022t 新建补丁 0008"
  status: closed
  scope: [qemu]
  blocks: []
  resolved_by: "QEMU-022t（2026-09-21，补丁 0008）"
  notes: "INFRA-033t（2026-10-04）判定：题面已述『已由 QEMU-022t 新建补丁 0008』；ADR-0011 固化，0008 已在补丁集 ⇒ closed。"

- id: ISS-065
  title: "源树提交作者为 Reviewer <reviewer@example.com>——git config 未设置项目约定身份"
  status: closed
  scope: [infra, qemu]
  blocks: []
  resolved_by: "补丁集重整（2026-09-23）：git apply 路径不再产生 patch commit，作者信息问题自然消失"
  notes: "原 backlog L173 标 ✅已消解；本次合并据此关闭。"

- id: ISS-070
  title: "test_encoding_oracle.py 用例去重：扩展后 TESTS=57 但去重后仅 50 条（7 条旧用例被重复登记）"
  status: closed
  scope: [llvm]
  blocks: []
  resolved_by: "LLVM-022t（2026-09-29，oracle 去重 68→61 + 交叉检查）"
  notes: "INFRA-033t（2026-10-04）实测：`tools/llvm/test_encoding_oracle.py` `len(TESTS)=121`、`unique=121`、重复 0 条；dedup 发生于 LLVM-022t（commit 9a7ea95，68→61）⇒ closed。"

- id: ISS-071
  title: "fence 的 LLVM 侧 lit 缺口——fence 无任何 lit 指令行，LLVM 侧实测可汇编且编码正确"
  status: closed
  scope: [llvm]
  blocks: []
  resolved_by: "SPEC-039t（2026-09-29）：fence 移出 M1 ⇒ scope: excluded"
  notes: "INFRA-033t（2026-10-04）判定：fence 已 `scope: excluded`（ADR-0014；`contracts/opcodes.yaml` fence_oiii_imm）；excluded 指令无 M1 lit 覆盖要求（cfx/LR-SC 同样无 lit 行），其 M1 行为为 decode ILLI ⇒ 原 M1 口径下的『lit 缺口』不再成立，closed。（LLVM 仍可汇编 `fence` 为现状；若未来支持 fence 再补 lit。）"

- id: ISS-073
  title: "check_lit_bytes.py 两项可选增强：无 CLI（LIT_DIR 硬编码）+ 独立计数门控不能捕获整行 # OBJ: 被删除"
  status: closed
  scope: [llvm]
  blocks: []
  resolved_by: "LLVM-022t（2026-09-29，check_lit_bytes 加 `--lit-dir`/`--min-obj`）"
  notes: "INFRA-033t（2026-10-04）实测：`tools/llvm/check_lit_bytes.py` 现有 `--lit-dir`（L61–65）与 `--min-obj`（L66–71，L137–141 用于「整行 OBJ 被删」保护）；由 LLVM-022t（commit 9a7ea95 提交说明）落地 ⇒ 两项可选增强均已提供，closed。（接入 Makefile 时的 min-obj 阈值仍可选。）"

- id: ISS-075
  title: "文档分层改造 T1/T2/T3 收尾遗留（adr-0017 指针、assembly-list 旧路径、contract-asm-list 漂移门控、Toolchain-01 陈旧计数、docs/README 措辞、fetch.py 注释、E5 恢复步骤）——全部消解"
  status: closed
  scope: [spec, infra]
  blocks: []
  resolved_by: "SPEC-085t（T2）+ INFRA-027t（收尾，2026-10-03）"
  notes: "原 backlog L9–L30。T1-①② 由 SPEC-085t 消解；T2-①②③、T3-1/2 由 INFRA-027t 消解；跨任务汇总（L23–30）同此，不重复登记。"

- id: ISS-076
  title: "cls 多寄存器化后 spec 正文/内嵌速查表/assembly-list 暂不一致——已由 LLVM-023t 消解"
  status: closed
  scope: [spec]
  blocks: []
  resolved_by: "LLVM-023t（2026-09-29）：gen_asm_list.py _MULTI_REG_MNEMONICS 加 focls/ftcls 并重生成"

- id: ISS-083
  title: "rf2rd 目的 rd0 的 dst_rd0 缺口（合约↔spec 不一致）——SPEC-089t 已收口"
  status: closed
  scope: [spec, llvm, qemu]
  blocks: []
  resolved_by: "SPEC-089t（2026-10-04）：R2b (A) 全补 15 条（含 rf2rd）dst_rd0，opcodes.yaml + fp_semantics.yaml 双边 + Check 8 交叉断言；汇编期 LLVM-031t、运行期 QEMU-038t（2026-10-04）两侧落地"

- id: ISS-084
  title: "FP 实现期：FP 专属规则翻 active + 回填 rule_refs（SPEC-087t）——SPEC-089t 已完成"
  status: closed
  scope: [spec]
  blocks: []
  resolved_by: "SPEC-089t（2026-10-04）：_compute_rule_refs 收窄为 scope==excluded 才置空、EXPR_TO_RULE +7、dst_rf0/encode_fp_root_n 翻 active、重跑 gen_legality_list"

- id: ISS-085
  title: "mreg_range_overlap 落地任务 B1/B2/B3（QEMU-033t / LLVM-028t / TESTCASES-023t）——全部完成"
  status: closed
  scope: [spec, qemu, llvm, testcases]
  blocks: []
  resolved_by: "QEMU-033t + LLVM-028t + TESTCASES-023t（均 2026-10-03）"

- id: ISS-086
  title: "check-spec-refs 的 76 条历史既存违规（18 Check1 + 58 Check2；standalone，非本任务引入）"
  status: closed
  scope: [spec, infra]
  blocks: []
  resolved_by: "SPEC-094t（2026-10-04）：check-spec-refs 76→0（含返工收窄 rule b/c 假阴性）"
  notes: "原 backlog L58。SPEC-094t 消解：Check1 18（3 占位符 + 15 陈旧 §名）全机械修正；Check2 58 = 4 节标题（跳过）+ 44 前导/结构化覆盖 + 10 补引；改后总引用 680、Check1/Check2 = 0、EXIT=0。SPEC-087t 新增 contract-fp.md 零新增违规。"

- id: ISS-091
  title: "13 个历史任务书「完成区已填但状态仍待验收」（漏 /complete）——已消解"
  status: closed
  scope: [infra]
  blocks: []
  resolved_by: "2026-10-03 回填台账 + 状态（用户批准）；check-tasks 现列 0"

- id: ISS-092
  title: "LLVM/QEMU 缓存重新浅克隆——已完成"
  status: closed
  scope: [infra]
  blocks: []
  resolved_by: "2026-09-29：llvm-project.git 378M(shallow) + qemu.git 52M(shallow)，2m50s，pinned commit 均存在"

- id: ISS-095
  title: "check-lit 接入 make check + check-asm-prose 转 --strict——已落地"
  status: closed
  scope: [infra]
  blocks: []
  resolved_by: "INFRA-021t（2026-10-02）"

- id: ISS-096
  title: "既有 reg-imm-block.yaml 同组重叠用例与 mreg_range_overlap 相违——TESTCASES-023t 已消解"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-023t（2026-10-03）：两条改 ILLI + 各新增完全重合用例，向量 692→694"

- id: ISS-101
  title: "SPEC-024t 暴露的测试向量 src 预置缺口（15 条）为误报——已订正"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "SPEC-031t（2026-09-28）：role 字段恢复，hb 实为目的寄存器"

- id: ISS-105
  title: "FP 汇编期静态合法性检查（dst_rf0/mreg_range_overlap/mreg_range_overflow/encode_fp_root_n）——LLVM-030t 已完成"
  status: closed
  scope: [llvm]
  blocks: []
  resolved_by: "LLVM-030t（2026-10-03）；lit 28→29"

- id: ISS-113
  title: "check_interface_alignment.py 非递归 glob 致 23 项 FAIL——INTEG-005t 已消解"
  status: closed
  scope: [integ]
  blocks: []
  resolved_by: "INTEG-005t（2026-09-25）：iter_patch_files() 递归 glob + 空集硬错误，80/80 EXIT 0 恢复"

- id: ISS-127
  title: "QEMU-037t FP softfloat 算术族（arith 12 + root 2）已完成——FP 执行层 60/60 收口"
  status: closed
  scope: [qemu]
  blocks: []
  resolved_by: "QEMU-037t（2026-10-03）；探针 91/91、make check EXIT=0"
```
