# M3 阶段已关闭 Issue（≤ 2026-10-05）

> **来源**：`INTEG-014t`（2026-10-05）从 `.tao/knowledge/issues.yaml` 提取——**M3 阶段已 `closed` 的 issue**。
>
> **判据**：M3 达成 = **2026-10-05**（commit `6c4d1ac`，`milestones.md` M3 置达成）。`resolved_by` 对应任务提交日 ≤ 2026-10-05（实测 `git log --grep <taskID>`；边界「≤ 达成日」）。**灰区不计**（`Process-04 §3.4`）。
>
> **未提取**：M1 阶段（≤ 2026-09-22）的 8 条见 `.tao/archive/M1/issues-closed.md`；M2 阶段（2026-09-23 ~ 2026-10-04）的 41 条见 `.tao/archive/M2/issues-closed.md`；本次提取后活台账 `.tao/knowledge/issues.yaml` 仅保留 open 项。

**共 56 条**（按原 `issues.yaml` 顺序）。

| id | title | scope | resolved_by |
| --- | --- | --- | --- |
| `ISS-149` | 〔已交付·M3〕标量调用约定（原 ISS-005 的 M3 子集）：CC_DADAO/RetCC_DADAO/CSR、指针→rb16-31、标量→rd16-31、call/ret、callee-save | [M3] | SPEC-097t（契约）+ LLVM-039t（实现） |
| `ISS-150` | 〔已交付·M3〕最小重定位：同-section PCRel 符号就地解析 (target−PC)>>2（原 ISS-008 的 M3 子集） | [M3] | LLVM-041t |
| `ISS-013` | fetch.py 选源标签逻辑重复（INFRA-009t 遗留，DRY）——select_source() 返回值建议含 label | [infra] | INFRA-017t |
| `ISS-015` | make doctor 不检查 QEMU 构建依赖（glib-2.0/pixman-1/libfdt 等）——doctor PASS 但 configure 失败 | [infra] | INFRA-016t |
| `ISS-023` | F10④ 守卫的 RB 覆盖缺口：validate_vectors.py 只提取 rdha，未覆盖 rbha——rbha=0 的 ILLI 未被捕获 | [testcases] | TESTCASES-019t |
| `ISS-025` | br.* 双路径覆盖无结构性守卫：删掉 taken 或 not-taken 整条用例不会被捕获 | [testcases] | TESTCASES-028t |
| `ISS-039` | F4 — e_flags 未设置：contract-elf.md 要求 e_flags=0x00000001，当前为 0 | [llvm] | LLVM-014t |
| `ISS-040` | DADAOFrameLowering 未覆写纯虚 hasFPImpl——M1 安全（无实例化），M2 会阻塞 | [llvm, M3] | LLVM-038t |
| `ISS-041` | 4 个 LLVM 文件缺末尾换行：DADAOFrameLowering.{h,cpp}、DADAORegisterInfo.cpp、DADAOTargetMachine.h | [llvm] | LLVM-021t |
| `ISS-046` | DecodeGPRFRegisterClass 未使用告警：M1 无 RF 指令 → -Wunused-function | [llvm] | LLVM-029t |
| `ISS-049` | QEMU-003t 补丁 3 个源文件缺末尾换行：helper.c、helper.h、translate.c | [qemu] | QEMU-027t |
| `ISS-051` | v11.x 目录结构变更：target/riscv/translate.c 移到 target/riscv/tcg/translate.c | [qemu] | INFRA-040t |
| `ISS-052` | harness 端到端依赖跨任务（QEMU-005t/006t/008t）——ADR-0010 D1 修法 a 使 006t 后可跑 RD-only | [qemu] | QEMU-005t/006t/008t |
| `ISS-053` | andn.w-rb 在 006t 实现（translate.c:906）——名义归 008t，architect 裁定保留在 006t | [qemu] | QEMU-006t |
| `ISS-067` | check_qemu_trans.py 的 patch 行分类：collect_trans_defs() 对 +/-/上下文行一视同仁，理论上后序删除会误判 | [qemu] | QEMU-027t |
| `ISS-068` | 24 条 mem-rd 窄 load 向量 FAIL 归因变更：根因 = harness build_loader() 无条件用 st.o（8 字节），归 QEMU-023t | [qemu] | QEMU-023t |
| `ISS-069` | harness 内硬编码 op 常量 ↔ opcodes.yaml 无交叉校验——encode_* helper 硬编码 op 值，存在漂移风险 | [qemu] | QEMU-027t |
| `ISS-077` | spec 正文代码块无永久门控——12 章正文新汇编格式正确性仅靠任务级 reviewer 脚本 | [spec] | SPEC-103t |
| `ISS-079` | SPEC-067t F4 门控覆盖缺口：ftroot/foroot n=2 约束与规则改名无机械门控 | [spec] | SPEC-103t |
| `ISS-080` | SPEC-066t/067t 完成区「修改文件」字段未逐一提取（台账回填缺口，非阻断） | [infra, spec] | INFRA-040t |
| `ISS-082` | L1 — fp「未实现，decode ILLI」文案残留（SimRISC-00 L290/L379、contract-isa.md L25/821/823） | [spec] | SPEC-102t |
| `ISS-089` | check-qemu-semantics 的 gate 目录为瞬态（symlink 静默失败致假失败） | [qemu, infra] | QEMU-041t |
| `ISS-094` | check_asm_prose.py 域外场景 stdout 仍打 PASS（rc=1 但 stdout 语义不一致） | [infra] | INFRA-037t |
| `ISS-097` | class: overlap 同组用例缺语义门控（覆盖≠语义再现） | [testcases] | TESTCASES-028t |
| `ISS-099` | 009t-audit.py 对 ctrl-ret 全部 skip（旧 id 判据 ret-riii，应 ret_riii_ra） | [testcases] | TESTCASES-028t |
| `ISS-100` | 新规则 dst_rd0_nonzero 无 ISA 合法性向量 | [testcases] | TESTCASES-022t |
| `ISS-103` | generate_instrinfo.py / validate_instrinfo.py 陈旧、非真源（命名漂移 + 基线过期，EXIT≠0，均不在 make check） | [llvm] | LLVM-046t |
| `ISS-104` | M1 rd2rd/rb2rb 不等 count 静默取末组（FP 侧已加严，M1 未改） | [llvm] | LLVM-044t |
| `ISS-106` | M1 RD 多寄存器 {rd0:rd63} 仍静默截断（M1 RD 侧 mreg_range_overflow 未加） | [llvm] | LLVM-044t |
| `ISS-107` | ret rd0,<符号> 拒绝属规则完整性扩展（可选后续） | [llvm] | SPEC-102t |
| `ISS-109` | # 行首仍被静默当注释（AllowAdditionalComments 默认 true） | [llvm] | LLVM-025t |
| `ISS-111` | QEMU-033t 任务书层面遗留（探针 pre-existing 失败 + 验收项 4「保持 PASS」措辞不符实际） | [qemu] | INFRA-040t |
| `ISS-112` | check_interface_alignment.py 第三处调用的 isdir 守卫不一致 | [integ] | INTEG-006t |
| `ISS-114` | check_spec_drift.py 的 --test-mode 自测判别力不足 | [infra] | INFRA-017t |
| `ISS-115` | gen_asm_list.py 默认输出会覆盖已入库文件（--plain 无显式 --output 时写 docs/assembly-list.md） | [llvm] | LLVM-022t |
| `ISS-116` | validate_encoding.py 的 no_overlap 标识符未注册（rd2rd/rb2rb；pre-existing，不在 make check） | [spec] | INTEG-008t |
| `ISS-119` | new file mode 补丁的 index blob hash 失配 9 项（pre-existing，不影响 git apply） | [infra, qemu, llvm] | INFRA-038t |
| `ISS-121` | excp_rasof/excp_rasuf 描述仍用已废弃的 MemRAS 引用计数模型（legality_rules.yaml） | [spec] | SPEC-102t |
| `ISS-122` | gen_legality_list.py --verify 检出 MISMATCH 仍 return 0 | [spec] | SPEC-103t |
| `ISS-123` | check_rule_refs.py 的 gate2_fail 分支不可达 | [spec] | SPEC-103t |
| `ISS-124` | imm_range 移出 legality_rules.yaml 后规范侧通用说明未落位 | [spec] | SPEC-085t |
| `ISS-128` | 汇编器错误接受裸数字 0–3 作 wyde 位置（rwii: set.zw/set.ow/or.w/andn.w）——须仅接受 wp0–wp3，裸数字须报错 | [llvm] | LLVM-045t |
| `ISS-129` | spec SimRISC-05 §RB 加减“地址计算仅在低 48 位有效”与同段“全 64 位参与运算”字面矛盾——须澄清为“算术=64 位；访存取低 48 位；高 16 位表示溢出” | [spec] | SPEC-102t |
| `ISS-130` | 新增指令候选 sub rd, rb, rb（RB − RB → RD）用于 ptr−ptr/地址差值——spec 变更 + ADR，M3 用到前加入 | [spec, llvm, qemu, M3] | SPEC-100t/QEMU-040t/LLVM-043t |
| `ISS-131` | 5 处文档/注释的 opcodes 计数仍写 227，应随新增指令（SPEC-100t）统一改 228 | [spec, llvm, qemu] | SPEC-102t |
| `ISS-132` | `build-mc` 的 help 文本仍写 "LLVM MC tools"，未提 `llc`（INFRA-035t 追加后） | [infra] | INFRA-037t |
| `ISS-133` | `components/llvm-project/README.md` 补丁数 36 陈旧（LLVM-033t 后实为 45） | [infra, llvm] | INFRA-037t |
| `ISS-134` | `tools/llvm/gen_m1_asm.py`/`test_m1_asm.py` 用旧 i 后缀语法，实测 148/152（4 失败） | [llvm] | INFRA-041t |
| `ISS-135` | `make help` 预存故障：`Makefile:83` echo 内三反引号致 dash `EOF in backquote substitution`（EXIT=2） | [infra] | INFRA-041t |
| `ISS-136` | opcodes/rule_refs 计数残留：legality_rules.yaml:18（227）、check_scope.py:15 docstring（227）、gen_legality_list.py:7（190→191） | [spec] | INFRA-041t |
| `ISS-137` | C14 D1：指针算术直落 GPRB（单条 add.o） | [llvm] | LLVM-048t（新增 SelectPointerAdd：base(rb)+offset(rd)→add_o_bbd；不判 offset bank） |
| `ISS-140` | README.md 中 LLVM 补丁数陈旧（新增 DADAOCallingConv.td 后计数未更新） | [docs] | INFRA-041t |
| `ISS-141` | LLVM-040t §验收 2 记法「call callee」与 ADR-0013 D4「call [rb0, callee]」字面不一致 | [docs] | LLVM-040t（用户 2026-10-05 确认按 ADR-0013 D4 接受；任务书 §验收2 已订正为 call [rb0, callee]） |
| `ISS-143` | 后端缺口：sext i8/i16/i32 形参（sign_extend_inreg）无 ISel → 有符号窄参数扩展（C4）无法编译（abort 134） | [llvm] | LLVM-047t（新增 sext_inreg → ext.so pattern；显式 sext 不再 abort） |
| `ISS-144` | components/llvm-project/changelog.md 缺 LLVM-040t / LLVM-041t 两条组件条目 | [infra] | INFRA-041t |
| `ISS-145` | 043t/045t 证据脚本硬编码 MC 计数陈旧（114/27/28 → 110/29/29），产生假回归信号 | [infra] | INFRA-041t |
