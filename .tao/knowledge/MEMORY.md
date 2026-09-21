# MEMORY — DADAO-v5 项目记忆

## 这是什么

DADAO-v5 基于 11 份 spec/ 规范文档（SimRISC 0.5.3），从零构建 LLVM/QEMU/Chipyard/Linux 全栈。核心方法是"Agent 写代码、你写约束"——角色分工见全局 `AGENTS.md` 与 `.tao/README.md`。

## 当前进度

| 项目 | 状态 |
|------|------|
| SimRISC 规范 | ✅ 0.5.3 |
| spec 模块 | ✅ M1 完成（`002t`~`010t` 已验证；`011m` 里程碑） |
| testcases 模块 | 🔄 `002t` 已验证（向量基础设施：schema+`expected_pc`、inventory+`format` 列+机械同步、validator 补强；覆盖率门控为**声明级**，数据级归 `009t`）；`003t` 已验证（寄存器族 6 文件：`reg-arith`/`reg-logic`/`reg-shift-extend`/`reg-compare`/`reg-cond-assign`/`reg-imm-block`，130 身份/366 条；生成器 `tools/testcases/generate_isa_vectors.py` 已入 git）；`004t` 已验证（访存 3 文件：`mem-rd`/`mem-rb`/`mem-ra`，30 身份/172 条；生成器 `tools/testcases/generate_mem_vectors.py` 已入 git；validator 追加 F10 守卫）；`005t` 已验证（`ctrl-br.yaml`，10 个 `br.*` 身份/30 条，taken+not-taken 全测；生成器 `tools/testcases/generate_ctrl_br.py` 已入 git；validator 追加 F7 `expected_pc` 存在性规则，作用域 `br.*`）；`006t` 已验证（`ctrl-jump`/`ctrl-call`/`ctrl-ret`，5 身份/16 条；F7 全 active；生成器 `tools/testcases/generate_ctrl_jump_call_ret.py` 已入 git；validator 的 F7 规则扩展至 `jump`/`call`/`ret`）；`007t` 已验证（`misc.yaml`，3 身份/6 条：`swym`/`illi`/`fence`；**F6** `illi` 恒 ILLI → encoding/semantic 豁免、覆盖率由 legality 满足；`fence` SBZ→ILLI；生成器 `tools/testcases/generate_misc.py` 已入 git）；`008t` 已验证（保留编码 → UNDI 的向量层表达（方案 A：`class: legality` + `encoding.reserved: true`）；`tests/vectors/isa/reserved.yaml` 2 条；validator 加 reserved 分支 + R8 交叉校验（word 不得匹配 opcodes 任何记录，含 `excluded_m1`）；反造假脚本 `tools/testcases/test_anti_forgery_008t.py`）；`009t` 已验证（ISA 向量全量再审计：15 文件/597 条逐族重推导，**0 残留错值**；审计记录 `.tao/knowledge/testcases-009t-audit.md`、脚本 `tools/testcases/009t-audit.py`（318/320, 0 mismatch）；`validate_vectors.py` 加数据级覆盖门控（只报不拦）；**发现 154 缺口**（141 legality+2 boundary+11 overlap））；`010t` **已创建**（154 缺口消解，补 active case 或降级 ✓ → `deferred`；里程碑顺延 `011m`） |
| M1 任务规划（infra/spec/testcases/llvm/qemu/integ） | ✅ 已生成（参考 DADAO-0628；**testcases 已计划级复核**，其余未逐任务审核） |
| M1 实现 | 🔄 进行中（spec ✅ M1 完成；infra：`002t`~`009t`、`013t` 已验证（`013t` = 按原始仓库名命名；里程碑顺延为 `014m`）；`010t`~`012t` 待开始；testcases：`001k`~`009t` 已验证（15 个 `isa/*.yaml`、597 条；154 数据级缺口待补）；llvm：`002t`~`007t` 已验证（`004t` = Register TableGen；`005t` = 指令格式 TableGen；`006t` = AsmParser + CodeEmitter；`007t` = 反汇编器（原 008t，重排后提前）+ 15 条 DISASM lit（仓库侧、CHECK 钉字节）+ 178 条 assemble↔disassemble 往返一致）；`012t` = **lit 字节 oracle**（`tools/llvm/check_lit_bytes.py`：`# OBJ:` 手写字节 ↔ `opcodes.yaml` mask/value 独立校验，纯 Python+yaml、不跑 LLVM；`N==独立计数` 才 exit 0；**41 patterns OK**；反例三组均 exit 1；reviewer **Accepted**）；`011t` = **RA 指令 lit 补齐 + 复验**（新建 `ra.s` 11 用例 + oracle 57→68；**预检：RA MC 已由 `005t`/`006t`/`007t` 完成**（def 在 patch `0004`）→ 缩窄为 lit+验证、不改补丁；**消歧已实现方案 B**（AsmName=`"ld.o"` + 寄存器类消歧）且与 `contract-isa §4.9` 一致，原「方案 A」偏离 spec 作废；删除错误的 `set.rd` 条；reviewer **Accepted**：lit 17/17、oracle 68/68、11 条三方比对 0 mismatch）；`008t` = **全量 lit（迁移+统一）**（14 个格式族文件强模板 `--check-prefix=OBJ`+`=ASM`；`disassembly.s` 15 组用例迁移后**删除**；`basic-encoding.s` 统一为强模板；`triple-smoke.s` 不动；**复用并扩展 `tools/llvm/test_encoding_oracle.py`** 作独立字节 oracle（31→57）；**engineer 第 1 版覆盖缺失（`add.si rd8,-1`）+ 完成区不实（对照表自相矛盾）+ 错误「新发现」（`ext.uo` 实为 orrr/orri 两 insn，非歧义）**→ 主会话证伪退回、第 2 版修复；reviewer **Accepted**：覆盖**脚本化逐条**零缺失、lit **16/16**、oracle **57/57**、抽验 7 条字节**亲自手算**全一致、反例门控含 oracle 注入）；qemu：`002t`~`004t` 已验证（`002t` = QEMU **v11.1.1** 基线（`ADR-0008 Accepted`）；`003t` = **Target Skeleton**（`0001` 20 文件，`qemu-system-dadao`、`-M ?` 含 `dadao-m1`、全指令 ILLI 0x88、`build-qemu` out-of-tree）；`004t` = **Decodetree 解码**（`0002`：`insn.decode` 256 pattern 与 `opcodes.yaml` 一致、256 个 `trans_*` 存根全部 ILLI（`swym` NOP）；`tools/qemu/` 生成器+校验器入库；**N-1 修正**：78 条 `excluded_m1` `decode: UNDI`→`ILLI`，与 ADR-0004 D5.1 对齐））；`014t` = **语义测试 harness**（`tests/scripts/`：`build_test_binary.py`（raw encoding → 4 段 loader/test/dumper/exit）+ `run_qemu_test.py`（只看 `$?`）+ `gen_trampoline.py` + `trampoline.bin` + `verify_harness_dump.py`（通道验证）+ `README.md`；**ADR-0009**（Candidate，D1–D7 用户逐条确认：raw-encoding 独立于 LLVM / guest 内 XOR+ORR 比较 / ROM trampoline / scratch `rd60`–`rd63`+`rb60`–`rb63`（RA 不作 scratch）/ 退出码协议 / schema 消费契约 / 诊断模式 guest 自旋 + QMP `pmemsave`）；验收 2/4/5(生成加载)/6/7/9/10a PASS，1/3/5(进入 BINARY_BASE)/8/10b 待 005t 语义；reviewer 五轮 Needs Revision→Accepted + architect 复核确认）；`005t` = **RD 整数语义**（`0003-dadao-rd-arith.patch`：12 指令族 / 97 insn 由 ILLI 桩替换为真实 TCG；关键修复：**运行时条件异常路径不得设 `NORETURN`**（用 `cpu_loop_exit_restore(cs, GETPC())` 恢复精确现场，否则 TB 起点重放致退出码被覆盖）、`gen_zero_extend` 的 `1ULL<<63` UB、`ext.*_orrr` 按 `rdhd` **值**取起始位且 `hd>N`→ILLI 须先于掩码、定宽 `add/sub/mul.{sb,sw,st}` 符号/零扩展；reviewer **四轮** Needs Revision→Accepted（独立 oracle：`-d cpu` 寄存器 dump 111/111 + 仓库独立向量回放 **220/220**）+ architect 复核确认；harness 端到端顺延至 `QEMU-020t` 完成后统一复跑（ADR-0010 D1））；`006t` = **RD 存取与 MALIGN**（`0004-dadao-load-store.patch`：22 条 RD 单/多 load/store + MALIGN 精确异常（`EXCP_MALIGN`/`cpu_do_unaligned_access`/`MO_ALIGN_N`）+ 前置的 `jump-rrii`/`br.nz`；**关键修复**：`jump-rrii` 缺 `tcg_gen_exit_tb` 致 SIGABRT、`rb0` 须用**翻译期 PC**（非 `env.rb[0]`，否则 TB 内取值陈旧）、`st.o-rd` 缺 `MO_ALIGN_8`、exit port 改 `.impl.max_access_size=8` 防 TCG 拆 8B MMIO + `stm.*`→exit 运行期 ILLI、ROM store 按 D5.6 返 ILLI、**MALIGN 优先级高于访问种类**（`gen_check_exit_port_illi` 加自然对齐门控）；reviewer **四轮** Needs Revision→Accepted（独立探针 46/46 + 反例门控）+ architect 复核确认；harness e2e 待 `020t` 回补）；`007t` = **translate.c 拆分**（`0005-dadao-translate-split.patch`：把 3685 行/256 个 `trans_*` 按 §-级族拆入 `target/dadao/insn_trans/` 的 10 个 `.c.inc`，`translate.c` 只留 decodetree include + helper + 寄存器宏；**纯重构**，以「256/256 函数体逐字节一致 + 探针回归 20/20+34/34」为语义未变证据——对象级 diff 不可作判据（`decodetree.py` 非确定性）；reviewer Accepted + architect 复核确认；并修「树/补丁不一致」：0005 提交 amend 为 `99a4dda`，补丁重生成后 diff 一致）；`008t` = **控制流 + RB**（`0006-dadao-ctrl-flow.patch`：`br.*`（含 `-rb`）/`jump-iiii`/`call` 两形式/`ret`/`rela.si`/`swym` + RB 存取/块复制/立即数/**全 64 位算术**/比较；**RegRAS 按 §5.3/§5.4 完整实现**（引用计数 + 移位压弹栈 + RASOF/RASUF）；**关键修复**：压栈/弹栈移位方向相反（F1/F2）、RASOF 深调用不可达（F3）、RASOF 前已写 RA 违反精确异常（F4）、探针 6 组用例 FAIL 路径不可达致恒 PASS（F5）、完成区反例表数字不实（N1）、工作区污染致结论不可复现（N2）；reviewer **三轮** Needs Revision→Accepted（`-no-shutdown`+`info registers` 直读 RA + 逐用例注入反例）+ architect 复核确认；MemRAS/`ra0` 限制登记 deferred→`013t`；harness e2e 待 `020t`）；`009t` = **rela 基址定向回归验证**（**验证任务，不改补丁**；`trans_rela` 与 §4.7 一致——基址取 `rb0`（PC）非 `rb[ha]`、`(PC & ~0xFFF) + sext(imms18<<12)`、高 16 位保持、`ha==0`→ILLI；新增 `tools/qemu/min_rom_probe_009t.py`（12 用例：`cmp.uo-rb` **精确值断言** + 4 类注入门控全检出；教训：`br.ne` 极性写反致正确实现全红）；reviewer 两轮 Needs Revision→Accepted（独立 `-d cpu` oracle `MISMATCH=0`）+ architect 复核确认；**engineer 子代理连续 3 次空返回，主会话代行修改**并登记 deferred）；`010t` = **`ldm.o-rb` 实现 + 补 008t 漏项 `stm.o-rb`**（`0006` 补丁用 `git format-patch` 重生成；二者对称——EA 48 位截断、**循环内逐次再掩码**、`MO_BEUQ|MO_ALIGN_8`、ILLI 先于写；新增 `tools/qemu/min_rom_probe_010t.py` 28 用例 + 反例门控）；reviewer **五轮** Needs Revision→Accepted（探针 `cmp_uo` 误用致语义断言恒真、EA 截断判别用例缺失、循环内未逐次掩码、T28 首断言 `br_nz` 偏移指向 PASS、文档矛盾）——**探针分支偏移/极性错误本模块已 3 次**，规则入 `AGENTS.md`、标签化探针框架建议入 `deferred.md`；008t 验收遗漏（`stm.o-rb` 被误标 PASS）登记 deferred；`011t` = **`div.*`/`rem.*` label 顺序定向回归验证**（**验证任务，不改补丁**；结论：label 结构正确、除零与各 size `INT_MIN÷−1` → ILLI `0x88`、truncate-toward-zero 与余数符号=被除数符号均正确，**无缺陷**；新增 `tools/qemu/min_rom_probe_011t.py` 28 用例 + `rd2rb`/`rb2rd` 回读校验 + 反例门控）；reviewer **四轮** Needs Revision→Accepted（关键教训：**手算分支偏移极易错**——`br.ne` 基址是分支指令**自身**地址，off 算错会致恒真/掩蔽；探针值构造 `add.si` 仅 18 位致被除数静默变 0；**陈旧二进制未重建**致误判回归）；`AGENTS.md` 补「还原须含重建」「探针值构造须回读校验」，标签化探针框架建议入 deferred；`012t` = **分支 PC 公式 + `call` RA 压栈 §5.6.1 定向回归验证**（**验证任务，不改补丁**；新增 `tools/qemu/min_rom_probe_012t.py` 13 用例 + CTL；结论：§5.2/§5.4/§5.5/§5.6 公式全部正确、**无缺陷**）；**两轮 reviewer**（F1 R2 误标 case 2——`[call_iiii(1)]*64` 实为异址 64 深=case 3，改为**同址递归**并加 R2b 异址对照；F2 R1 往返不能证 high16=0x0001；F3 R4 实为 2 级；F4 B2 未钉住负偏移）；**实测确认 harness 控制流能力缺口**：`ctrl-br/jump/call` 的 encoding+semantic 全 TIMEOUT、`ctrl-ret` semantic 因 loader 的 `rd2ra` 为 ILLI 桩（属 `013t`）报 ILLI → 归 `017t`/`018t`/`013t`（**非** `020t`）；`-d cpu` 可直读 `ra63`；`013t` = **RA 指令语义**（`0007-dadao-ra-semantics.patch`：`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`/`rd2ra`/`ra2rd` 由 ILLI 桩替换为真实 TCG（MALIGN/ILLI/`ra2rd` 目的 rd0→ILLI/范围越界）+ **补全 MemRAS**（008t 的 M1 简化版 → §5.6.1/§5.6.2 case 3 的 `ra0` 指针/计数语义）；新增 `tools/qemu/min_rom_probe_013t.py` 22 用例 + `-d cpu` 回读；**四轮 reviewer**：D1 阻断（`gen_ras_pop` case 3 的 RASUF **非精确异常**——先写 `ra0` 再判无效，违反 §1.3.4/ADR-0004 D5.5 → 有效性判定前移）、F2（补 X1–X3 异常路径 + `ra0` 回读）、F3（`rd2ra`/`ra2rd` 源目的分属不同寄存器组，§4.9.3「重叠先读后写」为**空条件**）、F4（B2 同源互比无判别力；且 `br_nz` 落点越位致恒 PASS，**本模块第 5 次**分支偏移事故）、R1（**空测试**：`call_iiii(3*65)` 跳过全部 64 组链式 call，MemRAS 从未被触碰）、X4（断言未观测自身主张的 `ra63` 存回 + 落点算错）；`rd2ra`/`ra2rd` 向量缺口登记 deferred→TESTCASES；`015t` = **harness 语义验证修复**（`tests/scripts/`：普通模式不 emit dumper（ADR-0010 D1 修法 a 落地）+ CLI fail-closed（0 case/全 SKIP → exit 2）；语义 PASS 恢复，batch `597 total/562 passed`）；**验收中 reviewer 证伪 engineer 根因（「TCG 代码量超限」），发现 QEMU 核心缺陷**：`dadao_tr_tb_stop` 用 `goto_tb(1)+exit_tb(NULL,0)` 且**缺 `gen_update_pc`** → TB 被切（op buffer ≈100 store-heavy 条 / `TCG_MAX_INSNS=512`）后 `env->pc` 不更新 → **执行期死循环**（`-d exec` 46185 次、PC 恒 `0xFFFF00000000`），影响**任意长 TB 的 guest 程序**；新建 `QEMU-022t`（补丁 `0008`）修复、`020t` 缩窄为「TB 安全分段 dumper + `--dump` 端到端」；015t 验收 #6（`--dump` 的 `rb`/`pc`）原 **BLOCKED**，已由 `022t` 回补（`--dump` 的 `rd2/rd3/rd4` 与 `rb1/rb2/rb62`、`pc=0xffff00000210` 均正确；`020t` 的分段 dumper 降为防御性措施）；24 条 `mem-rd` 向量内存模型不一致归 TESTCASES；`fence` ILLI 桩（与 007t「fence=nop」矛盾）登记 deferred；**待处置（deferred，用户裁定暂缓）**：`fence` 实现缺失（`trans_fence` ILLI 桩）→ 全量基线 `597/590/2/5/0`，**`021m` 继续阻塞**；`023t` = **harness `input_state.memory` 按宽度写入**（`build_loader()` 按 mnemonic 宽度用 `st.b/w/t/o`；`derive_width_from_mnemonic()` 扩为 3-tuple；**契约**：`value` = `address` 处 N 字节值，补注 `ADR-0009`（续二）；方案裁决 A 不可行/B′ 撤回/E 可行/B 退化/**C 采纳**）；**成果**：24 条窄 load FAIL→PASS、48 条 memory 向量全 PASS、全量 `597/590/2/5/0`（仅余 2 条 `fence` ILLI 桩）、8B 场景逐字节不变；reviewer **Accepted**；`019t` = **trans lint**（`tools/qemu/check_qemu_trans.py`：insn 派生 `trans_*` 名 + 复用 `validate_decodetree.build_unique_func_names()`，按 `static bool trans_<name>(` 精确匹配定义；报 `256/256 (M1 178/178)`；`--strict` 有缺失 exit 1；`--src` 可覆盖源供反例门控）；**实测 0 缺失**、`swym`/`illi` 也有 trans；reviewer **Accepted**（反例门控含前缀碰撞 `br_n_rd`/`cs_n_rd`、`excluded_m1` 计数隔离、DRY 核对）；`018t` = **call/ret 语义 + RA 重定位**（`build_call_ret_binary()` 合成 `[call imm=2][跳板 jump→exit][ret][exit 段]` 往返；`expected_state.ra` 低 48 位按 `loader_bytes` 重定位（RA=`<count:16><返回地址:48>`，返回地址=call 自身地址+4）；call 的 `input_state.ra` 同步重定位（保递归语义）；`build_loader` 改返回元组；**补注 `ADR-0009 D6`（续）**；**engineer 连续 2 次空返回 + 第 1 版 ret 布局错误（RASUF 0x8B）**→ 主会话证伪退回；reviewer **Accepted**（全量 `597/566/26/5/0`、子集 `11/11/0/0`、`-d cpu` 独立 oracle、双向门控））；`017t` = **分支语义 harness 扩展**（`build_branch_test_binary()` + `expected_pc` 调度；`expected_pc` 按 **delta**（`- BINARY_BASE`）消费：`delta==8`→taken / `==4`→not-taken，**不比对绝对地址**（补注 `ADR-0009 D6`）；not-taken poison 偏移 **`+2`**（v5 基址=分支自身地址）；改前 20 条 `ctrl-br` semantic **真空 PASS**（`expected_pc` 被忽略）→ 改后 poison pattern 真实判定；**engineer 第 1 次空返回 + 第 1 版 not-taken poison 不可达（恒真）**→ 主会话证伪退回、第 2 版加 trampoline `[branch][jump→exit][illi][exit段]`；reviewer **Accepted**（双向反例门控、22/22 字节级布局核对、偏移敏感性、全量 `597/562/29/5/1` 与基线 diff IDENTICAL）；交接 `018t`：`ret`(delta=4) 不适配 not-taken layout）；`016t` = **harness `expected_state.memory` 比对**（`build_exit_section()` 新增 memory 比对循环：宽度推导的无符号 load（`ld.ub/uw/ut/o` = 0x10/0x11/0x12/0x20）读实际值到 `DUMP_RD`，与期望 XOR+ORR 进 `ACCUM_RD`；地址用 `MEM_RB`(61)）；**预检订正任务书 6 处**（`emit_state_compare()` 不存在、`n_patch` 机制 v5 无、`TEMP_RB` 误用、依赖 004t、BLOCKED 归因）；**engineer 第 1 轮阻断缺陷 + 完成区不实**（224 条向量 `ValueError` 却报无新增失败）→ 主会话证伪退回、第 2 轮修复；reviewer **Accepted**（全量 `597/562/29/5/1` 与基线逐字节一致、24 条 store 向量逐条 PASS、反例门控 + 反向注入 + 宽度反解析核对 + 多 entry 合成）；#6 仍 BLOCKED（24 条窄 load 向量归 TESTCASES）；`022t` = **TB 续接缺陷修复 + exit-port 可靠 halt**（`0008` 单原子补丁 3 文件：`translate.c` 的 `gen_update_pc`+`translator_use_goto_tb` 守卫、`dadao-machine.c` 的 exit-port handler 改 `cpu_loop_exit`、`helper.c` 的 `dadao_cpu_do_interrupt` shutdown 守卫；**`ADR-0011`（Accepted，D1–D4 用户逐条确认）**：exit-port 写后立即 halt（`cpu_loop_exit` longjmp）、exit code 优先于后续 fault、补丁不可分离、ADR-0004 D3 增补「写入后立即停止 guest 执行」；**关键**：修复暴露 exit-port 退出码竞态——`cpu_exit()`+`EXCP_INTERRUPT` 不能停外层 `cpu_exec`（最小复现 40 次中 5 次不一致、008t/009t/010t/013t 假失败）→ 改 `cpu_loop_exit` 后 reviewer 独立复现 **2100 次全一致**；`--dump` 的 `rb`/`pc` 恢复正常（`pc=0xffff00000210`）；遗留：`cpu_loop_exit` 的 longjmp 泄漏 MMIO re-entrancy 守卫（登记 deferred）；integ 待推进） |

## 关键目录速查

| 路径 | 用途 |
|------|------|
| `spec/` | 11 份原始规范文档（只读） |
| `manifests/` | 锁文件（规范/参考组件） |
| `.tao/tasks/<module>/` | 按模块分的任务文件（`<PREFIX>-nnn<suffix>`） |
| `.tao/knowledge/` | 知识沉淀（MEMORY/milestones/contract/adr） |
| `.tao/knowledge/milestones.md` | 项目里程碑路线图（M1/M2） |
| `.tao/knowledge/deferred.md` | 各模块暂缓/备忘（避免遗忘） |
| `contracts/` | 机器可读合约数据（编码表/ABI/合法性规则） |
| `tools/<module>/` | 各模块工具脚本（infra/spec/llvm/qemu/testcases） |
| `tests/` | 测试向量（`tests/vectors/`）、harness（`tests/scripts/`）、lit、e2e |
| `components/` | 组件补丁（llvm/qemu/gem5） |
| `sail/` | Sail 形式化规范 |
| `.cache/<原始仓库名>.git` | 上游组件持久 bare mirror（gitignored；避免重下大仓库）；目录名 = 原始仓库名（见「重要决策」） |

## 重要决策

- **数据/工具分离**：机器可读合约数据放 `contracts/`，各模块工具脚本放 `tools/<module>/`（`scripts/` 并入 `tools/infra/`）
- **模块重划（2026-09-14）**：`verif` 解散——通用 CI 检查→`infra`、领域验证依据→`spec`、组件自测→`llvm`/`qemu`、集成→新模块 `integ`
- `.tao/` 集中存放所有 agent 中间文件（对齐 t.a.o 全局约定）
- **模块清单**：`infra`/`spec`/`testcases`/`golden`/`llvm`/`qemu`/`integ`/`gem5`/`sail`（`abi` 并入 `spec`；`verif` 已解散）
- **任务编号**：`<PREFIX>-nnn<suffix>`，suffix `k`=启动/`t`=普通/`m`=里程碑；模块内递增
- **项目里程碑**：M1/M2，见 `.tao/knowledge/milestones.md`
- **去阶段化**：任务不按 Phase 组织，直接参考 DADAO-0628；已删除 `docs/phases/`
- **执行前确认**：任务分解参考 DADAO-0628 生成、未逐一审核，执行前须与用户确认任务书（见 `AGENTS.md`）
- **跨模块交互**：里程碑核验须考虑其它模块影响；需修复时里程碑后移或增加交互任务（见 `AGENTS.md`）
- **QEMU 任务重构（ADR-0010 Accepted，2026-09-19）**：D1 harness 前置（`jump-rrii`/`br.nz` → 006t，修法 a 普通模式不 emit dumper）、D2 translate.c 拆分（10 个 `.c.inc`）、D3 任务重排（006t 合并 MALIGN、007t 改为拆分、补丁 0004–0007）、D4 验收规范化（逐条标注「现在可跑/BLOCKED」）；新增 `QEMU-020t`（harness dumper 改造；**2026-09-21 已关闭**——交付物 #1 由 `015t` 落地、分段 dumper 因 `022t` 根治 TB 缺陷而不再必要）。`QEMU-014t` 依赖修正为 `004t+006t`；`QEMU-016t` 依赖修正为 `TESTCASES-004t`
- **测试机地址图（ADR-0004，2026-09-13 修订）**：采用 spec 核内地址空间模型（cfxcode 63/power）——boot ROM `0xffff_ffff_0000`（= `cfx_power_hypv_excp_vector`）、RAM `0xffff_0000_0000`(16MiB)、Exit port `0xffff_8000_0000`(8B)；机器 fault 退出码 = `0x80 | spec_cause_bit`（ILLI `0x88`、UNDI `0x89`、RASOF `0x8A`、RASUF `0x8B`、MALIGN `0x8C`、IALIGN `0x8D`），unmapped `0x87`（测试机约定）
- **标识符 = 原始仓库名（2026-09-17，`INFRA-013t`）**：组件 `name` 取 GitHub 仓库名（如 `llvm-project`，非简称 `llvm`）、参考仓库 `id` 取原始仓库名含大小写（如 `DADAO-0628`）；manifest 值必须与 `ADR-0002` 的 `.cache/<name>.git`、`.cache/refs/<id>.git` 占位符一致。缓存目录因此为 `.cache/llvm-project.git`、`.cache/refs/DADAO-0628.git`；工作树为 `.work/source/llvm-project`（`LLVM_SRC=.work/source/llvm-project/llvm`）
- **DADAO target 经 `LLVM_ALL_TARGETS` 注册（2026-09-17，ADR-0007）**：DADAO 通过加入 `llvm/CMakeLists.txt` 的 `LLVM_ALL_TARGETS` 列表注册，使 `-DLLVM_TARGETS_TO_BUILD=DADAO` 生效；否决 experimental 通道。`LLVM-003t` 补丁须包含此增项
- **LLVM 基线 = 23.1.1（2026-09-17，ADR-0006）**：lock 值 = commit `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`（`llvmorg-23.1.1` 附注 tag 对象 `e7ce3600…` 仅溯源）；获取源 = SJTU 浅 bare 镜像 `.cache/llvm-project.git`（`--depth 1`，无完整历史，见 ADR-0006 Consequences）；`repository` 仍为 github 规范 URL；M1 期间不 bump
- 角色规则由全局 `opencode/agent/` 提供，工作仓库不含 agent 文件

## 如何参考 DADAO-0628 和 DADAO

- `DADAO-0628`：基于 SimRISC 0.4.1 的完整实现，包含补丁集和任务文件
- `DADAO`：各阶段早期的代码实现（已不再更新），包含 LLVM/QEMU/Chipyard 等组件的具体实现
- 两者 commit 锁定于 `manifests/references.lock.toml`（由 `INFRA-003t` 建立）
- 路线图与任务拆解直接参考 DADAO-0628：`docs/development-roadmap.md`（M0/M1/M2/M2.5）、`code-agent/designs/0002-detailed-roadmap.md`、`code-agent/tasks/`

## 规范版本对应

规范版本与冻结状态的**唯一来源**是 `README.md`「当前版本号」表（SimRISC 0.5.3 / AEE·ABI 0.9.2 / SEE·SBI 0.7.1 / HEE·HBI 0.1.2）。v5 不使用 `manifests/spec.lock.toml`。

## 关键差异提示（相比 DADAO-0628）

DADAO-v5 基于 SimRISC 0.5.3 规范，与 DADAO-0628（锁定在 SimRISC 0.4.1）相比有以下关键差异：

### 0.5.3 vs 0.4.1 的变化

1. **指令命名重构**：所有指令使用 `.b`/`.w`/`.t`/`.o` 位宽后缀，有符号/无符号用 `s`/`u` 区分（如 `add.uo`/`add.so`、`mul.uw`/`mul.sw`）。原 0.4.1 的 `add`/`sub`/`muls`/`mulu`/`divs`/`divu`/`cmps`/`cmpu`/`exts`/`extz`/`shrs`/`shru`/`shlu` 等命名已废弃。此外，LR/SC 原子指令使用 `_nn`/`_nr`/`_an`/`_ar` 后缀标记 acquire/release 语义

2. **格式体系重构**：引入 MISC-byte/wyde/tetra/octa 四个子表，通过 `orrr`/`orri` 格式覆盖各固定位宽的 and/or/xor/xnor/ext/shr/shl/add/sub/cmp/mul/div/rem 操作

3. **QFC 编码表重组**：opcode 分配完全改变（见 SimRISC-00 QFC 表），涉及所有指令的 mask/value

4. **新指令**：`add.si`（riii 格式自增自减）、`br.z-rb`/`br.nz-rb`（rb0 零/非零分支）、`cs.n-rf`/`cs.z-rf`/`cs.p-rf`/`cs.eq-rf`/`cs.ne-rf`（浮点条件赋值）

5. **寻址语义变化**：RB 算术改为全 64 位运算（原 48 位限制移除，bits[63:48] 为运算结果可用于溢出检测）

6. **立即数格式变化**：`add.si` 从 rrii（两寄存器 + 12 位 imm）改为 riii（一寄存器 + 18 位 imm）；`rela.si` 同理

7. **浮点扩展**：新增 `ft2ft`/`fo2fo`（浮点内部格式转换）

8. **命名风格统一**：`.` 作为命名分隔符（`cs.n`/`cs.z`/`cs.p`、`br.n`/`br.nn`/`br.z`、`set.zw`/`set.ow`、`or.w`/`andn.w`）

### 不变的差异（从 0.4.1 延续）

- 浮点架构完整定义（SimRISC-03），需 golden model 骨架和 LLVM 寄存器类
- 系统指令：cfx2rd/cfx2rc/cfxld/cfxst/trap/escape 指令族（SimRISC-04）
- 原子操作：lr/sc LR-SC 指令
- 命名规范：wpN（非 ww）、pmem（非 phymem）、illi（非 unimp）
- Scope 更广（含浮点/系统），实现优先级可先聚焦标量核心

## 文件映射：spec → contracts

| spec/ 文件 | 对应 contract（在 `.tao/knowledge/` 下） | 主要消费者 |
|-----------|------------------------------------------|-----------|
| SimRISC-00 ~ 04 | `contract-isa.md` | golden model, LLVM, QEMU, gem5, Sail |
| DADAO-11 AEE | `contract-abi.md` | LLVM CodeGen |
| DADAO-12 SEE | `contract-exception.md`（推迟）+ `contract-sbi.md` | QEMU, Linux |
| DADAO-13 HEE | `contract-exception.md`（推迟） | Chipyard |
| DADAO-21 ABI | `contract-abi.md` | LLVM CodeGen |
| DADAO-22 SBI | `contract-sbi.md` | QEMU, Linux |
| DADAO-23 HBI | `contract-sbi.md` | Chipyard, Linux |

## 职责边界

| 内容 | 位置 | 说明 |
|------|------|------|
| 数据表示（byte/wyde/tetra/octa） | SimRISC-00 | ISA 基础概念 |
| 寄存器模型（rd/rb/rf/ra） | SimRISC-00 | ISA 核心组成部分 |
| 浮点状态寄存器（rf0） | SimRISC-00 | 浮点指令基础 |
| 返回地址栈（RAS） | SimRISC-00 | 函数调用支持 |
| 存储模型 | SimRISC-00 | 地址空间定义 |
| 不同宽度数据的运算处理 | AEE | 运行环境相关 |
| 地址空间布局 | AEE | 应用程序运行环境 |
| 汇编兼容性 | AEE | 汇编器支持 |
| 函数调用规范 | ABI | 软件约定 |
| 系统调用规范 | ABI | 软件约定 |
