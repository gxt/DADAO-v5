# Changelog

任务对仓库代码的实质改动记录（由 `/complete` 追加）。

| 日期 | 描述 | 执行方 |
| --- | --- | --- |
| 2026-09-12 | INFRA-002t：建立仓库骨架（`.gitignore`、`components/`/`scripts/`/`containers/` 骨架、`docs/repository-layout.md`） | engineer |
| 2026-09-12 | INFRA-003t：manifest 系统（`manifests/components.lock.toml`、`manifests/references.lock.toml`、`scripts/manifest_check.py`） | engineer |
| 2026-09-12 | INFRA-004t：组件获取与打补丁工具（`scripts/fetch.py`、`apply_series.py`、`make_patch.py`、`fetch_refs.py`；`.cache/` 持久 bare mirror + `.work/` 可再生工作树） | engineer |
| 2026-09-12 | INFRA-005t：环境与状态工具（`scripts/doctor.py`、`status.py`、`clean_work.py`；clean_work 保护 `.cache/`） | engineer |
| 2026-09-12 | INFRA-006t：顶层 `Makefile` 编排（help/manifest-check/doctor/status/fetch/apply-series/prepare/build-*/docker-*/check；build stub 不假装成功） | engineer |
| 2026-09-12 | INFRA-007t：开发容器 `containers/dev/Dockerfile`（ubuntu:24.04 + LLVM/QEMU 依赖 + clang，M1 scope 不含 gem5；容器内 `make doctor` 报 native） | engineer |
| 2026-09-12 | INFRA-008t：补 v5 自身 ADR（`adr-0001-greenfield-rebuild.md`、`adr-0002-build-orchestration.md`，含 `.cache/` mirror 决策；改 5 文件引用） | engineer |
| 2026-09-12 | SPEC-002t：ISA 规范合约按 M1 范围重新生成（`contract-isa.md`；**RA 进 M1**，浮点 RF/特权/原子 Excluded） | engineer |
| 2026-09-12 | SPEC-003t：编码表按 M1 范围重生成（`contracts/opcodes.yaml`：M1 178 + `excluded_m1` 78；修正旧版 2 处 ha 错误 + 5 条块赋值 legality 字段） | engineer |
| 2026-09-12 | SPEC-004t：ABI 合约收窄到 M1 最小事实（`contract-abi.md` + `contracts/abi.yaml`；完整调用约定 `Deferred to M2`） | engineer |
| 2026-09-12 | SPEC-005t：Object ABI ADR-0003（M1：ELF 头字段 + 段/流水线；重定位 `Deferred to M2`） | engineer |
| 2026-09-13 | SPEC-005t 修订：ADR-0003 `e_flags` 由 1 位标志改为 bits0–7 版本字段（M1=1，bits8–31 保留） | engineer |
| 2026-09-13 | SPEC-006t：Test Machine ADR-0004（内存映射/复位值/exit port/异常可观测，D1–D6 冻结；Status=Candidate） | engineer |
| 2026-09-13 | ADR-0004 重判修订：D1 改核内地址空间模型（ROM `0xffff_ffff_0000`/RAM `0xffff_0000_0000` 16MiB/Exit `0xffff_8000_0000`）、D5 fault 码改 spec cause 派生（ILLI `0x88`…IALIGN `0x8D`，unmapped `0x87`）、D3 harness 超时兜底、D6 示例修正；同步下游任务书 QEMU-003t/QEMU-015t/INTEG-002t/TESTCASES-006t/008t | architect |
| 2026-09-13 | SPEC-006t 返工复验：ADR-0004 修订后重开验收（更新验收脚本至 109/109 PASS；reviewer+architect 双模型 Accepted；ADR 修正 D6.4 距离与状态说明两处），任务置 `已验证` | architect |
| 2026-09-14 | ADR-0003 rev. 2026-09-14：D2 登记补充（绝对地址并入「绝对 64-bit 数据地址」、不单列 wyde 地址构造场景；相对分支/call/jump `<<2`、有效范围=位宽+2；`rela.si` `<<12`、4KB 对齐、与页无关、无 `<<2`） | architect |
| 2026-09-14 | SPEC-007t：ELF 合约（`.tao/knowledge/contract-elf.md`；§1 头字段 + §5 段对齐/VA=PA + §6 pipeline；§2/§3/§4 重定位 `Deferred to M2`） | engineer |
| 2026-09-14 | 模块重划：`verif` 解散——通用 CI 检查→`infra`（`INFRA-010t` issue registry/`INFRA-011t` spec 引用审计/`INFRA-012t` drift）、验证依据→`spec`（`SPEC-008t` legality/`SPEC-009t` QFC）、组件自测→`qemu`（`QEMU-014t`~`019t` harness×5+trans lint）/`llvm`（`LLVM-012t` lit oracle）、集成→新模块 `integ`（`INTEG-002t` E2E/`INTEG-003t` 接口对齐）；目录 `verif/`→`contracts/`（数据）+`tools/<module>/`（脚本）、`scripts/`→`tools/infra/`；里程碑顺延（`INFRA-013m`/`SPEC-011m`/`LLVM-013m`/`QEMU-020m`/`INTEG-004m`） | architect |
| 2026-09-14 | SPEC-008t 重做+返工：`contracts/legality_rules.yaml` 重新生成（增补 RA 规则；删除 `ra0_no_exception`——ra0 可读写无异常；fault 枚举限定 6 值 `ILLI/UNDI/MALIGN/IALIGN/RASOF/RASUF`；对齐 `legality` 字段引用；修正 `spec_cite` 重复键/行号与 RF/LR/CFX 规则状态） | engineer |
| 2026-09-14 | SPEC-009t：QFC 覆盖校验（`tools/spec/check_qfc_coverage.py`；QFC 表 ↔ `contracts/opcodes.yaml` 双向比对，256/256 差异 0，只读 informational） | engineer |
| 2026-09-14 | SPEC-010t：Spec 冻结（`docs/impact-matrix.md` 逐节覆盖 + `README.md` 冻结状态标 `已冻结`）；`contract-elf.md` Status → Accepted | engineer |
| 2026-09-14 | SPEC-011m：M1 spec 里程碑达成（`002t`~`010t` 已验证，合约/编码表/ADR/impact-matrix 齐备） | architect |
| 2026-09-15 | TESTCASES 任务集二次重排：按运算族/load-store/控制转移/jump-call-ret/misc 分解为 `002t`~`009t`+`010m`；文件布局方案 A（14 个 `isa/*.yaml`）；F1→`003t`、F10 分摊、F5→`008t`、F7 采用 `expected_pc` 方案全 active；旧 `004t`/`005t`/`006t` 已达成关闭（证据见 `001k`） | architect |
| 2026-09-15 | TESTCASES-002t 返工（从零重建向量基础设施）：`schema.md` 新增可选 `expected_pc` + encoding 类对恒 fault 指令（`illi`）豁免；`inventory.md` 增 `format` 列（178 行唯一可辨）+ 机械同步；`validate_vectors.py` 补 R2/R4/F9②③④；覆盖率门控改为**声明级**（数据级归 `009t`） | engineer |
| 2026-09-16 | TESTCASES-003t：寄存器族 ISA 向量从零生成（`reg-arith`/`reg-logic`/`reg-shift-extend`/`reg-compare`/`reg-cond-assign`/`reg-imm-block`，130 身份/366 条）；含 **F1**（`orrr` shamt 取寄存器形式）、**F10**（encoding 可执行无 fault）、`rela.si` 改 active；validator 追加 F9① + class↔fault/state 守卫；生成器提交至 `tools/testcases/generate_isa_vectors.py` | engineer |
| 2026-09-16 | TESTCASES-003t 两轮返工：R1 定宽有符号运算补符号扩展（`.s*` 符号 / `.u*` 零扩展）；R2 16 条 `div`/`rem` encoding 预置非零除数；R3 `rela.si` notes 补 PC 来源；R4 `rem.s*` 改 truncate-toward-zero 余数。第 2 轮 reviewer 独立全量重算 366 条 **0 mismatch**，判决 Accepted（architect 交叉复核确认） | engineer |
| 2026-09-16 | 治理规则（用户裁定）：`AGENTS.md`「临时目录」增「生成器/脚本随产物保留」（判据=产物是否入库；"一次性"≠可丢弃）；「中间验证规范」增「数据/期望值类任务附加要求」（size/sign 敏感用例独立全量重算、不得以 validator 绿灯为唯一判据、错值当场修） | architect |
| 2026-09-16 | TESTCASES-004t：访存向量从零生成（`mem-rd`/`mem-rb`/`mem-ra`，30 身份/172 条）；**F10** 访存 encoding 一律可解码执行无 fault（base=`rb3` 未使用寄存器 + 预置 RAM 基址、dest/源非 rd0、`immu6≥1`）；validator 追加 F10 守卫；生成器提交至 `tools/testcases/generate_mem_vectors.py` | engineer |
| 2026-09-16 | TESTCASES-004t 返工：F-1 rrii 偏移编入 `imms12`（原误用无作用的 `rd2`，15 条 semantic EA≠memory）；F-2 rrii MALIGN 令 EA 真未对齐（12 条）；F-3 删 2 条 `base=rb0` 无效 case；F-5/F-6 inventory `boundary` 列与 fault `spec_cite` 补正。第 2 轮 reviewer 独立全量重算 172 条 **0 mismatch**，判决 Accepted（architect 交叉复核确认） | engineer |
| 2026-09-16 | TESTCASES-005t：`ctrl-br.yaml` 从零生成（10 个 `br.*` 身份/30 条）；**F7** 每身份 taken+not-taken 全测（`expected_pc`：taken=`rb0+8`（`imm=2`）、not-taken=`rb0+4`，`rb0=0xffff00000000`）；F10 encoding 无 fault 不自跳；validator 追加 F7 `expected_pc` 存在性规则（作用域 `br.*`，供 `006t` 扩展）；生成器 `tools/testcases/generate_ctrl_br.py` | engineer |
| 2026-09-16 | TESTCASES-005t 返工：F1 10 条 encoding 的 `imm` 由 `0` 改 `2`（原 5 条条件默认为真 → 确定性自跳）；F3 生成器统计口径修正。第 2 轮 reviewer 独立全量重算 20 条 semantic **0 mismatch**、10/10 encoding 不自跳，判决 Accepted（architect 交叉复核确认） | engineer |
| 2026-09-16 | TESTCASES-006t：`ctrl-jump`/`ctrl-call`/`ctrl-ret` 从零生成（5 身份/16 条）；**F7** `jump`/`call` 生成即 active（`expected_pc`：`imm=2` → `rb0+8`）；`call` 压栈用 `expected_state.ra`（`ra63` 高16 计数 + 低48 `PC+4`）；`ret` 弹栈；validator 的 F7 规则**就地扩展**至 `jump`/`call`/`ret`；生成器 `tools/testcases/generate_ctrl_jump_call_ret.py` | engineer |
| 2026-09-16 | TESTCASES-006t 返工：G-1 补生成器（消除虚假 provenance，md5 确定性一致）；G-2 inventory 措辞；G-3 补 `call` §5.6.1 case 2/3 semantic；G-4 记录 harness 依赖。第 2 轮 reviewer 独立全量重算 16 cases/39 checks **0 mismatch**，判决 Accepted（architect 交叉复核确认） | engineer |
| 2026-09-16 | TESTCASES-007t：`misc.yaml` 从零生成（3 身份/6 条：`swym-iiii`/`illi`/`fence`）；**F6** `illi` 恒 ILLI → encoding/semantic 豁免、覆盖率由 `legality` 满足；F10 `swym`/`fence` encoding 无 fault；`fence` 的 SBZ（`bits[17:4]` 非零）→ ILLI（legality）；生成器 `tools/testcases/generate_misc.py` | engineer |
| 2026-09-16 | TESTCASES-008t：F5 落地「保留编码 → UNDI」向量层表达（方案 A：复用 `class: legality` + `encoding.reserved: true`，不立 ADR）；`schema.md` 增规范；`validate_vectors.py` 加 reserved 分支 + **R8 交叉校验**（word 不得匹配 `opcodes.yaml` 任何记录，含 `excluded_m1`）；新建 `tests/vectors/isa/reserved.yaml`（2 条 UNDI）；`inventory.md` 登记；反造假脚本 `tools/testcases/test_anti_forgery_008t.py`；顺带消解 `007t` 遗留的 `legality.expected_fault` 非 null 守卫 | engineer |
| 2026-09-16 | TESTCASES-009t：ISA 向量全量再审计（15 文件/597 条逐族独立重推导，**0 残留错值**）；新增审计记录 `.tao/knowledge/testcases-009t-audit.md` 与脚本 `tools/testcases/009t-audit.py`（318/320, 0 mismatch）；`validate_vectors.py` 追加**数据级覆盖率门控**（按 inventory 每行 ✓ 类逐 `(insn,format)` 校验 active case，**只报不拦**，用户裁定 B）；`reg-cond-assign.yaml` +5 条 C-27 deferred overlap；**发现 154 数据级缺口**（141 legality+2 boundary+11 overlap）并登记 `deferred.md` | engineer |
| 2026-09-16 | TESTCASES-009t 经 6 轮 reviewer 验收收敛（5 次打回全在审计脚本/记录：`.sb`/`rwii`/`rb` 分支/`rd2ra`/计数口径/`cmp` 符号），**数据自第 1 轮即 0 mismatch**；architect 交叉复核确认 Accepted；登记「工具交付物 vs 数据交付物分层验收」教训；建议新建 `010t` 补数据 + 里程碑顺延 `011m` | architect |
| 2026-09-16 | LLVM 模块计划级复核 + reviewer S1–S13 修订落盘：S1 分支偏移公式去 +4（`contract-isa.md` §5.2–5.4 `Addr=rb0+(imm<<2)`，无流水线偏移）+ fixup kind 改自定义 `DADAO_FK_PCRel_2`；S2 格式数 12→9（`crrr`/`crii`/`ciii` Excluded from M1）+ §2.2→§2.3；S3/S13 `LLVM-010t` 改名「系统指令助记符与 smoke 修正」+ 重写（`escape`/`trap` Excluded，M1 = `swym`/`illi`/`fence`）；S4 补 `SPEC-003t` 依赖到 `006t`/`007t`/`008t`/`009t`/`010t` + 回写 `001k` 任务表；S5 `011t` 同名助记符消歧方案（方案 A：`insn` 全名作 AsmName）+ 补 `LLVM-005t` 依赖；S6 `012t` 依赖补 `LLVM-011t`；S7 `012t` oracle 增强（mnemonic ↔ 命中记录 + N 下限）；S8 `deferred.md` 修 `LLVM-012t` 陈旧引用；S9 DecoderMethod 归属澄清（`.td` 注解在 `005t`，C++ 实现在 `008t`）；S10 `002t` LLVM_SRC 已知坑标注已解决；S11 `013m` 核验清单补全；`LLVM-001k` 状态置 `已验证` | architect |
| 2026-09-17 | 新增规则「大文件下载与镜像」（用户裁定）：`AGENTS.md` 增该节 + 知识库 `.tao/knowledge/mirrors.md`（执行细则）。要点：从国外站下载较大软件（LLVM/QEMU/linux-kernel 等）**先查教育网联合镜像站** <https://mirrors.cernet.edu.cn/list/> → 逐个测连通性/速度 → 给建议（含直连对照）→ **用户确定**；有明确 release/tag 时**默认浅下载但仍先问** | architect |
