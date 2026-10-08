# MEMORY — DADAO-v5 项目记忆

## 这是什么

DADAO-v5 基于 19 份上游 spec/ 规范文档（SimRISC-00~12 + DADAO-11~23，SimRISC 0.5.4）与 v5 自定规范（`spec/Toolchain-01`、`spec/Process-0x`；索引 `spec/README.md`），从零构建 LLVM/QEMU/Chipyard/Linux 全栈。核心方法是"Agent 写代码、你写约束"——角色分工见全局 `AGENTS.md` 与 `.tao/README.md`。

## 当前进度

| 项目 | 状态 |
|------|------|
| **M1 归档**（2026-10-03） | ✅ M1 历史（testcases 模块 / M1 任务规划 / M1 实现 三行）已归档至 `.tao/archive/M1/README.md`；76 个 M1 任务书同在该目录。 |
| **M2 归档**（2026-10-04） | ✅ M2 历史（45 行 + 2 条混合行〔`spec 模块`/`integ 模块`〕的 M2 段落）已归档至 `.tao/archive/M2/README.md`；150 个 M2 任务书同在该目录。 |
| **M3 归档**（2026-10-05） | ✅ M3 历史（1 行〔`M3 进行中`〕）已归档至 `.tao/archive/M3/README.md`；41 个 M3 任务书同在该目录。 |
| **M4 归档**（2026-10-07） | ✅ M4 历史（1 行〔`M4 规划`〕）已归档至 `.tao/archive/M4/README.md`；32 个 M4 任务书同在该目录。 |
| **M5 进行中**（2026-10-07） | `INFRA-047t`（`ADR-0016` install 落地：host 工具链 `.dadao/cross-toolchain` + target sysroot + 门控/执行器改从 install 根取可执行）**已验证**；`INFRA-048t`（生成物落点迁移：`test-codegen`/`test-elf`/lit 运行产物 → `.dadao/tests/`，reviewer `Accepted`、architect 交叉复核通过）**已验证**；`SPEC-117t`（`Process-05 §6` 落点规则补正：默认 `.dadao/tests/` + 判据，reviewer `Accepted`、architect 交叉复核通过）**已验证**；`SPEC-113t`（ADR 决策落地：`ADR-0020` 新建 `D1–D15` + `ADR-0004` 修订 `R1`/`R2`/`R3` + `ADR-0016 S1` 沿用，reviewer `Accepted`、architect 交叉复核通过）**已验证**；`SPEC-114t`（SEE/semihosting 规范正文：新建 `spec/Machine-01-测试机运行环境.md`〔①–⑦ 七节〕+ 投影 `contract-see.md`/`contract-semihosting.md` + 登记 `spec/README.md`；**上游只读册零改动**、round1 擅改 `DADAO-12`/`DADAO-22` 已还原，reviewer `Accepted`、architect 交叉复核通过）**已验证**；`SPEC-119t`（spec 目录保护：`manifests/spec-readonly.lock.toml`〔上游 20 册 `sha256` 锁〕+ `tools/infra/check_spec_readonly.py`〔`if errors` fail-closed〕+ `make check-spec-readonly`〔纳入 `make check`〕+ `spec/Process-06-spec目录保护规范.md`〔①–⑤ 均 MUST〕；**上游只读册零改动**、6 类反例注入均 FAIL 且还原回绿，reviewer `Accepted`、architect 交叉复核通过）**已验证**；`LLVM-060t`（`trap`/`escape`/`cfx2rc`/`cfx2rd` MC+编码：`.td` def〔op/mask/value 与 `opcodes.yaml` 一致〕+ AsmParser〔`cfx<ha>`/`cfx_<name>` 等价、简化 regname 展开、`escape` 位宽〕+ InstPrinter + 生成别名表 `DADAOCfxAlias.inc`〔生成器 `tools/llvm/gen_cfx_alias_table.py` **随产物入库**〕；**5b 门控前置**〔lit `crrr`/`ciii` 的 `; OBJ:` + `MC_ONLY_EXCLUDED_IDS` += 4 条，由 `SPEC-115t` re-scope 时移除〕满足 ⇒ **解除 `SPEC-115t` BLOCKED 的 `.td`/lit 前置**，reviewer `Accepted`、architect 交叉复核通过〔独立重跑生成器 + `cmp` 复现 patch、`check-patch-tree` 90 patches/断言⑥、oracle 14 向量 0 错、注入有鉴别力、未越界无 `spec/`〕）**已验证**；`SPEC-115t`（re-scope 收口：`trap`/`escape`/`cfx2rc`/`cfx2rd` 由 `scope: excluded` → `m1`；**改 `generate_opcodes.py` + 重跑**产出 `contracts/opcodes.yaml`〔4 条 `op`/`mask`/`value` **逐字段未变**、`legality`/`rule_refs` 保持 `[]`；计数 `155`/`60`/`11`/`227`〕、`check_scope.py` 计数同步、门控载体 `inventory.md`（+4 行 `deferred`）/`validate_instrinfo.py`（`MC_ONLY_EXCLUDED_IDS` 移除 4 条）收口、投影三件同步；**经用户授权**改上游只读册 `spec/SimRISC-11-其它.md` + 同步其 `sha256` 锁〔其余 19 册零变动〕；reviewer `Accepted`、architect 交叉复核通过〔独立重跑 `check_scope`/`validate-vectors`/`check-instrinfo`/`check-interface`/`check-spec-readonly` 全绿、temp 注入改 scope ⇒ FAIL ⇒ 回绿有鉴别力、`spec/` 变更仅 `SimRISC-11`〕）**已验证**；`SPEC-116t`（上游只读册 `Toolchain-01` 修订：`§2.1` **撤销**「助记符与寄存器名大小写不敏感」→ 大小写敏感〔用户授权「允许（撤销不敏感条款）」+ 裁定 `INTEG-019k D16`；`ISS-157` 以「条款撤销」结案，非实现缺口〕+ `§1` 格式类 **9 种 → 11 类**〔`crrr`/`ciii` 不再 `excluded`、`crii` 据实测仍 `excluded`；用户授权「1、并入SPEC-116t」，**收口 `SPEC-115t` 遗留**〕；**仅两处 hunk** + 同步该册 `sha256` 锁〔其余 19 册零变动〕+ 投影 `contract-asm.md`〔§1/§2.1/§11 表〕；`make check`/`check-spec-readonly` EXIT=0、证据脚本 40/40 + I1/I2/I3 注入自检；reviewer `Accepted`、architect 交叉复核通过〔独立实测 `m1` 集逐项相等、锁 `sha256` 相符；reviewer 独立注入 `§2.1`→「不敏感」⇒ 6 断言 FAIL ⇒ 还原回绿，有鉴别力〕；遗留 `Toolchain-01` `§5`/`§11`/`§13` 旧口径属授权范围外，须另请授权后另立任务收口）**已验证**；`SPEC-120t`（用户裁定 3 落地：`encode_cfx` 规则**删除**〔**候选 A**——该规则把「执行期 reserved `cfxha` ⇒ ILLI」误登记为 `kind: static` **编码合法性**；实测**全仓 0 引用**〔`opcodes.yaml` `rule_refs` 0 条引用它 ⇒ 不进任何 `LEGALITY` 渲染〕、`deferred` 1 条无下游挂靠 ⇒ 删除后**无渲染变化**、**未触 `spec/`**〕——`contracts/legality_rules.yaml` 删规则块〔16→15 条，`deferred` 1→0〕+ `tools/spec/gen_legality_list.py` 移除 `SEMANTIC_MAP`/`RULE_SUMMARY` 两条目 + docstring 计数 `16→15`；`check_rule_refs`〔15 条〕/`check_legality_drift`〔12 章〕/`gen_legality_list --verify`〔12/12〕/`make check`〔62/62〕EXIT=0，证据脚本 EXIT=0 + 注入自检有鉴别力；reviewer **`Accepted`**〔**round1 `Accepted` 由主会话依 `lessons §8.7` 推翻改判 `Needs Revision`**〔C10 由工作树 `git status` 计算改动集 ⇒ 提交后必然为空 ⇒ 假 FAIL〕，round2 改 `$BASE_COMMIT..HEAD` 后 `Accepted`〕、architect 交叉复核通过〔0 引用独立实测、`spec/` 交集为空〕；遗留 `gen_legality_list.py` docstring `228 entries` vs 实况 `227`〔**既有陈旧**，非本任务引入，未改，仅登记〕）**已验证**。`QEMU-044t`（SEE/HEE 运行模式 + cfx 寄存器文件/掩码/权限/异常进入流程：`inner_run_mode` 四编码 0/1/2/3 与 cfx 正交；`cfx0/1/2/3/63` 的 cg0–cg7 寄存器文件含 `global_cfx_mask` **跨 cfx 全局共享**、`trap_num`/`excp_sync_num`/`escape_num` 计数、`scratch_regs`，复位值依 `DADAO-12 §3`/`DADAO-13 §1`；`DADAO-12 §5` 异常进入步骤 1–10 + 退出；`trap`/`escape`/`cfx2rd`/`cfx2rc` 由 ILLI 桩改为路由到流程；reserved cfxha ⇒ `ILLI`、未实现 cfx ⇒ `CFXREG`；探针 `tools/qemu/min_rom_probe_044t.py` **随产物入库** 13/13、`check-patch-tree` 90 patches/断言⑥；证据脚本 `run.sh` EVIDENCE: PASS〔3 反例注入 ⇒ FAIL ⇒ `cp`+md5 还原+**重建** ⇒ 回绿〕；reviewer `Accepted`、architect 交叉复核通过〔独立核四模式编码 / `global_cfx_mask` 跨 cfx 共享 / 复位值逐项对 `DADAO-12 §3`+`DADAO-13 §1` / 权限反例 4 类 / `spec/` 交集空〕；遗留 PTBR 权限层不在 M5、`excp_cause_mask`/inner·global mask 屏蔽路径不可观测〔`ISS-164`〕、`escape`/`trap` 深化归 `QEMU-045t`）**已验证**。`QEMU-049t`（RAM@0 双映射 C1 step1 + 越界/取指异常：机器模型**同时映射 RAM@0〔`0x0000_0000_0000`，16 MiB，cfxha 0 = umon〕+ 保留旧 RAM 段〔`0xffff_0000_0000`〕**；越界访问/取指按 cfxha 分类——**umon 段 ⇒ `CFXMEM`〔`0x81`〕**、**其余含旧 power 段 63 ⇒ 测试机约定 `unmapped`〔`0x87`〕**，取指与数据同等对待〔同一 `tlb_fill`〕；`check-interface` 新增 6 断言〔`RAM0_BASE=0x0`/`RAM0_SIZE=16MiB`/`init_ram`/`add_subregion`/`EXIT_CFXMEM=0x81`/`CFXHA_UMON=0`〕+ 旧断言保留，**80→86**；探针 `tools/qemu/min_rom_probe_049t.py` **随产物入库** 9/9；`check-patch-tree` 90 patches；证据脚本 `run.sh` EVIDENCE: PASS〔3 反例注入 ⇒ FAIL ⇒ `cp`+md5 还原+**重建** ⇒ 回绿〕；reviewer `Accepted`〔独立注入改 `DADAO_RAM0_SIZE` 16→8 MiB ⇒ `ram0_top` FAIL ⇒ 还原+**重建** ⇒ 9/9〕、architect 交叉复核通过〔独立核两段不重叠 / `check-interface` 86/86 / 越界路由 / `0x87–0x8D` 未重排 / `check-patch-tree` 90 patches / `git diff 00c9540` 10 文件·`spec/` 交集空〕；**step2 迁移**〔旧向量/harness/crt0/e2e 迁 `0` + 删旧 RAM 段 + 收紧断言〕另立、M5 之外〔`ISS-165`〕；越界路由口径的 spec 覆盖缺口见 `ISS-166`〔`Machine-01 §1` 待用户授权收口，`spec/` 零改动；教训 `lessons §7.16`/`§8.10`〕）**已验证**。`QEMU-045t`（`trap`/`escape` 语义深化验证 + `cfx2rd`/`cfx2rc` 全寄存器面专探针；**无组件补丁改动**：经「`044t`/`045t` 边界处置说明」收缩为「`QEMU-044t` 基线之上**深化/验证 + 专探针**」，`QEMU-044t` 已落接线与基础执行，**未发现 044t 基线缺口** ⇒ 无补丁导出。交付新专探针 `tools/qemu/min_rom_probe_045t.py`〔**随产物入库**，**14 用例**〕：一般 `trap` 进入向量 + `cause` 帧 / `trap_mask` ⇒ ILLI / reserved ⇒ ILLI；`escape` 正偏移 + **负偏移回退**（18 位有符号、`%4==0`）+ 跨 cfx 禁止 ⇒ ILLI / 跨 cfx 允许 ⇒ 恢复**非复位** `prev_run_mode`/`prev_cfx_mask` + `escape_num`++；`cfx2rd`/`cfx2rc` **cg0–cg7 全寄存器面**（RO/RW、`scratch_regs_num` 边界、cg3 仅 hypv、cfx0↔cfx63 共享）；reserved ⇒ ILLI；不存在组合 ⇒ **CFXREG 4 类**。`make build-qemu`/`make check`〔`check-patch-tree` 90 patches、`check-qemu-semantics: PASS`〕/`test-codegen`〔15/15〕/`test-elf`〔5/5〕EXIT=0；证据脚本 `run.sh` **EVIDENCE: PASS**〔6 反例合并注入 ⇒ 8 用例 FAIL ⇒ `cp`+md5 还原+**重建** ⇒ 回绿〕；reviewer `Accepted`〔**独立注入** `<<2`→`<<4`，与 A–F 不同、**特异**：只命中 escape 偏移路径 ⇒ 2 用例 FAIL 而 `reserved_illi` 仍 PASS ⇒ 还原+**重建** ⇒ 14/14〕、architect 交叉复核通过〔独立核 `git show 2b49946 --stat` = **2 文件**、`components/qemu/**` **零改动**、`.work/source/qemu` clean、helper.c md5 一致、无注入残留；14 用例覆盖输出范围 ⇒「未发现基线缺口」有覆盖依据；`spec/` 交集**空**〕；**新发现** ① `DADAO-12 §5` 异常退出**不恢复 `inner_cfx_code`**（实现与伪代码一致 ⇒ `lessons §7.18`）；② §5 **prose 与伪代码跨 cfx escape 措辞张力**（**伪代码为权威** ⇒ 登记 **`ISS-167`**、建议另立 spec 任务，**`spec/` 零改动**；规范 `lessons §8.12`）；③ `ILLI` 观测语义已说明清楚；遗留 semihosting 短路归 `QEMU-046t`）**已验证**。**重排（2026-10-07，用户裁定 1/2/3）**：`SPEC-115t` engineer BLOCKED（`scope: excluded→m1` 撞 3 跨模块门控）⇒ `LLVM-060t` **前置**于 `SPEC-115t`（裁定 1）；`SPEC-115t` 改 `tools/spec/generate_opcodes.py` + 重跑（裁定 2）、文件集 += `tests/vectors/inventory.md`/`tools/llvm/validate_instrinfo.py`；`encode_cfx` 另立 **`SPEC-120t`**（裁定 3；`**项目里程碑**=M5`，待复核）；M5 任务书 23 → 24；教训见 `lessons §7.6`。`SPEC-121t`（承 `ISS-166`：`Machine-01 §1` 越界路由/RAM@0 容量**落纸**〔§1.1 表 RAM@0 = **16 MiB**；§1.2 **新增「精确路由」条**＝**`umon` 段〔`addr[47:42]==0`〕越界访问/取指 ⇒ `CFXMEM`〔`0x81`〕；其余含旧 `power` 段 63 ⇒ 测试机约定 `unmapped`〔`0x87`〕**；§1.2 末条改落地陈述〕+ 该册**纳入只读锁**〔`manifests/spec-readonly.lock.toml` 新增 1 条，锁 **20→21**；既有 **20 册 `sha256` 逐字未变**〕+ `spec/Process-06 §5/§6` **语义扩面**〔「只保护上游 20 册」→「**含 v5 自定册**」〕+ 门控措辞去「upstream」〔`check_spec_readonly.py`/`Makefile`，**逻辑零改动**〕；`spec/` 改动**仅** `Machine-01 §1`〔3 处〕+ `Process-06 §5/§6`；`check-spec-readonly` **21 OK EXIT=0**；reviewer `Accepted`〔独立注入改真仓库 RAM@0 容量 ⇒ checker MISMATCH ⇒ `cp`+md5 还原回绿，有鉴别力〕、architect 交叉复核通过〔独立核 `§1.1`=16 MiB / 锁 21 且 `Machine-01` `sha256` 相符 / 既有 20 册 `sha256` 逐条未变 / `Process-06 §1` 未改 / checker 去 upstream〕；`ISS-166` 结案；遗留 `Process-06 §1`「上游只读册（清单见 §6）」括注因扩面字面略不精确〔**授权范围外未改**，待另授权一行措辞修正〕；教训 `lessons §7.17`/规范 `§8.11`）**已验证**。`QEMU-046t`（semihosting：译码层短路 + 共享层复用 + 完整 25 服务 + `SYS_EXIT`——`trap cfxHA, immu18` 中 `immu18[17:16]==2'b11` ⇒ semihosting〔**与 `cfxha` 无关**〕，`trans_ctrl.c.inc` 译码层抛内部 `DADAO_EXCP_SEMIHOST`（与 `RISCV_EXCP_SEMIHOST` 同构）⇒ `dadao_cpu_do_interrupt` 短路 `do_common_semihosting(cs)` + `env->pc += 4`，**不进入 cfx 向量**；共享层 `arm-compat-semi.c` **零改动复用**，v5 钩子 `target/dadao/common-semi-target.c`〔**新增**〕＝ `common_semi_arg(cs,0)=rd16`/`(cs,1)=rb16`/`common_semi_set_ret=rd31`/`is_64bit_semihosting` 恒真/`common_semi_stack_bottom=rb1`；服务表 **完整 25 个**〔含 `SYSTEM`/`HEAPINFO`/D2 文件档〕；**`SYS_EXIT` 取代 exit port**〔退出码忠实传 host `$?`〕、exit port **过渡保留**〔迁移归 `TESTCASES-034t`〕；**越界披露 2 项〔最小必要接线〕** ① `cpu.c` 新增 `dadao_cpu_translate_for_debug` 接入 `SysemuCPUOps`〔缺则共享层经 `cpu_memory_rw_debug` 回退 NULL ⇒ **SIGSEGV**〕② `qemu-options.hx` 两处 `DEF(...)` arch mask 增 `QEMU_ARCH_DADAO`〔缺则 CLI 被拒〕，另 `Kconfig` `select ARM_COMPATIBLE_SEMIHOSTING if TCG` + `meson.build` 条件编译；探针 `tools/qemu/min_rom_probe_046t.py`〔**随产物入库**〕**32/32 PASS**〔判定两条路 / 钩子 bank〔与 `rd17`·`rb17` 解相关〕/ 25 服务各 ≥1 / `SYS_EXIT` 码传播 / 64 位大端 `iserror_be64`〕；补丁 **32 → 34**、`check-patch-tree` **92 patches**；`make check`/`check-qemu-semantics`(149/149)/`test-codegen`(15/15)/`test-elf`(5/5) EXIT=0；证据脚本 `run.sh` **EVIDENCE: PASS**〔3 反例隔离注入 ⇒ FAIL ⇒ `cp`+md5 还原+**重建** ⇒ 回绿〕；reviewer `Accepted`〔**独立注入** tag 阈值 `0x3`→`0x0` ⇒ 2 用例 FAIL ⇒ 还原+**重建** ⇒ 32/32，有鉴别力、还原含重建〕、architect 交叉复核通过〔独立核 tag 门限 / 钩子 bank 逐条 / 32 用例 / 25 服务 / 共享层零 diff / `TARGET_BIG_ENDIAN=1` 证大端 / `check-patch-tree` 92 patches / `.work/source/qemu` clean / `git diff e0f2632..HEAD` 12 文件·`spec/` 交集空〕；**新发现** 复用上游共享层须同时落地**接入点清单**〔`translate_for_debug`/arch mask/Kconfig/meson〕，「只写钩子」式范围低估〔教训 `lessons §7.19`、规范 `§8.13`〕；遗留 `D7` harness 默认〔`target=gdb`〕归 `TESTCASES-034t`/`INTEG-020t`、exit port 迁移归 `TESTCASES-034t`、`SYS_SYSTEM` 已知风险已登记〕`QEMU-047t`（新 bootrom：构建 + 链接 + 端到端启动——固件 `tests/scripts/bootrom.S`〔自有汇编；`cfx2rc`/`trap`/`escape` 首个真实用户〕+ 链接脚本 `tests/scripts/bootrom.lds`〔ROM 段 `0xffff_ffff_0000`/64 KiB〕+ 样例应用 `tests/scripts/bootrom_app.S` + `Makefile::build-bootrom` + 探针 `tools/qemu/min_rom_probe_047t.py`〔13 用例，随产物入库〕；**path B raw-bin**〔`ADR-0004 D2.3`〕：bootrom `-bios` 载 ROM 基址、应用 `-kernel` 载旧 RAM 基址、**栈/数据置 RAM@0**、复位 PC 不变 `0xffff_ffff_0000`、hypv→user 直跳、无 supv；探针 13/13、`check-patch-tree` 92/`check-qemu-semantics` 149/149/lit 62/62/手工码 15/15/ELF 5/5 全绿、**无组件补丁**；reviewer `Accepted`〔独立注入移除 SP 初始化 ⇒ 3 FAIL ⇒ 还原+重建 ⇒ 13/13〕、architect 交叉复核通过〔独立核 `bootrom.lds`/`readobj` `e_entry`·`PT_LOAD VA`/`-d cpu` 首块 `PC`/探针 13/13，**临时树独立注入**回绿〕；**方法论偏差**：reviewer 还原用 `git show HEAD:<path> > <path>`〔非 `cp`+md5〕，本次未造成损失但属偏差〔教训 `lessons §7.20`/规范 `§8.14`〕；**前置风险**「`-bios`+ELF」组合缺口**待用户裁定**〔倾向 A；`INTEG-020t` 审阅记录〕〕**已验证**。`TESTCASES-033t`（M5 SEE/semihosting 向量：L1 MC〔`trap`/`escape`/`cfx2rd`/`cfx2rc` 编码/往返〕由前置 `LLVM-060t` 自带并接入 `check-lit`〔62/62，**无 `UNSUPPORTED:`**〕、本任务**复用**〔DRY〕；L3 执行向量 `tests/llvm/codegen/m5/` **10 条**〔承载形态 = **bin**，用户 2026-10-08 M5 范围简化〕＝ semihosting 服务 **5**〔`WRITEC`/`WRITE0`/`WRITE`/`EXIT`/`EXIT_EXTENDED`〕+ **cfx 级权限反例 4 类**〔`ILLI`：reserved/mask；`CFXREG`：unimpl/badcombo〕+ 一般 `trap`+`escape` **1**；独立 oracle `tools/testcases/validate_m5_vectors.py`〔**随产物入库**〕**141 checks PASS**〔服务表从 `contract-semihosting §3` **机械解析 25 条**；cfx 规则/cause 位/token 为**带 contract 引用的硬编码**、与既有范式一致；**无** `subprocess`/`Popen`〕；M5 E2E 驱动 `tools/integ/run_m5_e2e.py`〔**随产物入库**〕逐例核「退出码/控制台/故障码/**bootrom 生效**」**10/10 PASS**、逐例含实际命令行〔**全含 `-bios`**〕+ `-d cpu` 复位 PC `0xffff_ffff_0000`/bootrom user 向量/`MODE 0`；`make check`/`check-lit`(62/62)/`check-no-residue` EXIT=0；一键证据脚本 `run.sh` **EVIDENCE: PASS**〔4 类注入 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿，无 `tee`〕；reviewer `Accepted`〔**独立注入**改 `expected_cause` `ILLI`→`CFXREG` ⇒ oracle FAIL ⇒ 还原回绿，有鉴别力〕、architect 交叉复核通过〔独立核 L1 复用无 `UNSUPPORTED:` / oracle `grep` 无子进程 0 命中 / 服务表 25 条机械解析 / **独立注入**改 `expected_console` ⇒ oracle FAIL ⇒ `cp`+md5 还原回绿 / `git diff f23bcc4..HEAD` 17 文件·`spec/` 交集空·`.dadao/**`/`.work/**` 未入库〕；遗留 `Makefile`/`make test-semihost` 接线归 `INTEG-020t`；教训 `lessons §7.22`/规范 `§8.16`）**已验证**。`TESTCASES-034t`（exit-port → `SYS_EXIT` **全量迁移**：把 M1–M4 **全部**依赖 exit-port〔MMIO `0xffff_8000_0000`〕的向量/harness/oracle 迁到 semihosting `SYS_EXIT`〔`ADR-0020 D8`/`ADR-0004 R2`，默认全迁、例外逐条披露〕——`tests/scripts/codegen_crt0.s`〔`SYS_EXIT` = **64 位大端参数块** `{0x20026, rd31}` + **`rb16`=块指针** + `rd16=0x18` + `trap cfx_umon, 0x30000`〕/`build_test_binary.py`〔`emit_sys_exit`，移除 `EXIT_PORT`/`TEMP_RB`〕/`run_qemu_test.py`/`run_codegen_e2e.py`/`run_elf_e2e.py`〔QEMU 显式 `-semihosting-config enable=on,target=native`〕+ 4 e2e smoke〔`.s`/`.test`〕+ **16 探针**；**`ISS-147` 结案**〔M3 全部 15 条 `expected_exit_code` 收窄 `0x00–0x7F`，7 条掩码 `255→127` + `expected.yaml`/oracle `validate_codegen_vectors.py` range 收紧 `0..0x7F`〕；**`ISS-169`** 登记 **6 探针例外**〔`006t` 设备测试 / `009t` OBSOLETE / `008t`·`010t`·`012t`·`013t` 退出与手算 PC 偏移交错 ⇒ 建议另立/随 M6 重写后移除例外〕；`check_interface_alignment.py` 退役 `harness.EXIT_PORT` 子检查〔保留 QEMU 侧设备常量校验〕；迁移后各门控与改前**逐项相等**〔`test-codegen` 15/15、`test-elf` 5/5、`check-lit` 62/62、`check-qemu-semantics` 149/149、`make check` EXIT=0〕、26 探针逐条等价；证据脚本 `.work/evidence/TESTCASES-034t/run.sh` **`EVIDENCE: PASS`/`SCRIPT_EXIT=0`**〔3 类注入 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿，无 `tee`〕；reviewer `Accepted`〔**独立注入** 2 类有鉴别力：期望值 118→119 ⇒ `test-codegen` 14/15 FAIL；`crt0` `0x18→0x19` ⇒ 0/15 FAIL〕、architect 交叉复核通过〔独立核残留 exit-port **恰 7 文件**且与披露集逐一相符 / `validate_codegen_vectors` PASS(58)·`validate_elf_vectors` PASS(42)·`validate_mc_vectors` 73/0·`check-interface` 85 项 PASS·`check_issues` 39 open/3 closed·`check-no-residue` PASS 均 rc=0 / `ISS-120` 6 探针改前改后日志**逐字节相同**〔未扩大〕/ `git diff 783ba9f..HEAD` 46 文件·`spec/` 交集空·未触 `components/**`·`Makefile`〕；教训 `lessons §7.23`/规范 `§8.17`）**已验证**。M5 其余任务与门槛见 `.tao/knowledge/milestones.md`。 |
| SimRISC 规范 | ✅ 0.5.4 |
| spec 模块 | ✅ M1 完成（`002t`~`010t` 已验证；`011m` 里程碑）。 |
| integ 模块 | ✅ M1 完成（`001k`~`003t` 已验证；`004m` 里程碑）：`002t` = E2E 冒烟（`tests/e2e/*.s` + `tests/lit/E2E/`，lit 3/3，`.test` 消费 `.s` + `timeout`，反例门控）；`003t` = 跨模块接口对齐核对（`docs/integ-interface-alignment.md` + `tools/integ/check_interface_alignment.py`，80 项 0 FAIL，4 轮 reviewer）——**发现 ELF `e_flags=0x0` 违约**（另建 `LLVM-014t` 修复） |

## 关键目录速查

| 路径 | 用途 |
|------|------|
| `spec/` | 规范：上游 19 份（SimRISC-00~12 + DADAO-11~23）+ v5 自定 `Toolchain-01`/`Process-0x`；索引 `spec/README.md`（spec 模块任务可改） |
| `manifests/` | 锁文件（规范/参考组件） |
| `.tao/tasks/<module>/` | 按模块分的任务文件（`<PREFIX>-nnn<suffix>`） |
| `.tao/knowledge/` | 知识沉淀（MEMORY/milestones/contract；ADR 已迁 `.tao/adr/`） |
| `.tao/knowledge/milestones.md` | 项目里程碑路线图（M1/M2） |
| `.tao/knowledge/issues.yaml` | Issue 注册表（M1-gate 判据 + 各模块 issue 台账；已吸收原 backlog 散文台账的 issue 部分） |
| `.tao/knowledge/lessons.md` | 经验与教训（教训/方法论/过程记录；原 backlog 散文台账拆分） |
| `.tao/adr/` | 架构决策记录（ADR，决策层） |
| `.cache/refs/<id>/` | 参考仓库只读工作树（`DADAO-0628`/`DADAO`；`make fetch-refs` 重建，不入库） |
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
- **项目里程碑**：M1/M2/M3，见 `.tao/knowledge/milestones.md`
- **去阶段化**：任务不按 Phase 组织，直接参考 DADAO-0628；已删除 `docs/phases/`
- **执行前确认**：任务分解参考 DADAO-0628 生成、未逐一审核，执行前须与用户确认任务书（见 `AGENTS.md`）
- **跨模块交互**：里程碑核验须考虑其它模块影响；需修复时里程碑后移或增加交互任务（见 `AGENTS.md`）
- **QEMU 任务重构（ADR-0010 Accepted，2026-09-19）**：D1 harness 前置（`jump-rrii`/`br.nz` → 006t，修法 a 普通模式不 emit dumper）、D2 translate.c 拆分（10 个 `.c.inc`）、D3 任务重排（006t 合并 MALIGN、007t 改为拆分、补丁 0004–0007）、D4 验收规范化（逐条标注「现在可跑/BLOCKED」）；新增 `QEMU-020t`（harness dumper 改造；**2026-09-21 已关闭**——交付物 #1 由 `015t` 落地、分段 dumper 因 `022t` 根治 TB 缺陷而不再必要）。`QEMU-014t` 依赖修正为 `004t+006t`；`QEMU-016t` 依赖修正为 `TESTCASES-004t`
- **测试机地址图（ADR-0004，2026-09-13 修订）**：采用 spec 核内地址空间模型（cfxha 63/power）——boot ROM `0xffff_ffff_0000`（= `cfx_power_hypv_excp_vector`）、RAM `0xffff_0000_0000`(16MiB)、Exit port `0xffff_8000_0000`(8B)；机器 fault 退出码 = `0x80 | spec_cause_bit`（ILLI `0x88`、UNDI `0x89`、RASOF `0x8A`、RASUF `0x8B`、MALIGN `0x8C`、IALIGN `0x8D`），unmapped `0x87`（测试机约定）
- **标识符 = 原始仓库名（2026-09-17，`INFRA-013t`）**：组件 `name` 取 GitHub 仓库名（如 `llvm-project`，非简称 `llvm`）、参考仓库 `id` 取原始仓库名含大小写（如 `DADAO-0628`）；manifest 值必须与 `ADR-0002` 的 `.cache/<name>.git`、`.cache/refs/<id>.git` 占位符一致。缓存目录因此为 `.cache/llvm-project.git`、`.cache/refs/DADAO-0628.git`；工作树为 `.work/source/llvm-project`（`LLVM_SRC=.work/source/llvm-project/llvm`）
- **DADAO target 经 `LLVM_ALL_TARGETS` 注册（2026-09-17，ADR-0007）**：DADAO 通过加入 `llvm/CMakeLists.txt` 的 `LLVM_ALL_TARGETS` 列表注册，使 `-DLLVM_TARGETS_TO_BUILD=DADAO` 生效；否决 experimental 通道。`LLVM-003t` 补丁须包含此增项
- **LLVM 基线 = 23.1.1（2026-09-17，ADR-0006）**：lock 值 = commit `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`（`llvmorg-23.1.1` 附注 tag 对象 `e7ce3600…` 仅溯源）；获取源 = SJTU 浅 bare 镜像 `.cache/llvm-project.git`（`--depth 1`，无完整历史，见 ADR-0006 Consequences）；`repository` 仍为 github 规范 URL；M1 期间不 bump
- **性能排查先定位主因，勿默认瓶颈在"重量级外部进程"（`INFRA-030t`，2026-10-03）**：`check-qemu-semantics` 的 46s 主因**不是**串行启动 QEMU（149 例 QEMU 合计仅 **~2.4s**），而是 `build_binary()` **每例重复 `yaml.safe_load` 整个向量 YAML**（纯 Python SafeLoader、GIL 绑定；149 次 ≈33–43s）。**GIL 下限速必须先消除重复工作（缓存）再并行**——只上线程池零提速（实测未加缓存 `thread8`≈45s，加缓存后 0.38s）。方法：先 profiling/独立计时，再决定优化手段
- 角色规则由全局 `opencode/agent/` 提供，工作仓库不含 agent 文件

## 上游 ↔ v5 偏离台账

> M2 门槛⑤交付物：登记 **7 项**上游 spec 与 v5 决策之间的**规范性偏离**。每项均已由**已 `Accepted` 的 ADR**（或 M1→M2 过渡任务 `SPEC-086t`）固化；本节只做**归一化登记 + 指针**，不新增决策。`scope`、`RACNT`、`MRPTR`、exit 码等写法与 `contracts/opcodes.yaml`、ADR 一致。

| # | 偏离点 | 上游依据 | v5 决策 | ADR / 契约指针 |
|---|--------|----------|---------|----------------|
| 1 | **exit port（程序停机）** | `SimRISC-11 §退出指令`：`escape cfxHA, [excp_cause_ip, imms20]`（**退出特权态**，非停机；编码层 `imms18`） | 自定 **exit port** MMIO（`0xffff_8000_0000`，8 B，只写）；退出码 = `0x80 \| cause_bit`；写入后 `cpu_loop_exit()` 锁定 | **ADR-0004 §D3**（Exit Port 协议）+ **ADR-0011 §D1–D4**（可靠 halt） |
| 2 | **`fence` SBZ 非零** | `SimRISC-12 §fence指令`：`immu18 bits[17:4]` 为 SBZ，**非零值行为保留** | v5 定**非零 SBZ → ILLI**（`0x88`）；且 `fence` 整体 `scope: excluded`（未实现，decode ILLI） | **ADR-0004 §D5.3**（SBZ 非零 → ILLI）+ **ADR-0014 §D1–D3**（fence 移出 M1）；`contracts/opcodes.yaml::fence_oiii_imm` |
| 3 | **测试机地址映射 / 复位值** | `spec/` **无测试机层**（`DADAO-12 §2.1` 仅给核内地址空间模型，无内存映射 / 复位值全集 / exit 协议） | 采用 spec 核内地址空间模型（cfxha 63/power）：boot ROM `0xffff_ffff_0000`、RAM `0xffff_0000_0000`(16 MiB)、Exit port `0xffff_8000_0000`；复位 PC=`rb0`=boot ROM；`rd0`/`rb1`–`rb63`/`ra0`–`ra63`/`rf1`–`rf63` 复位 `0`、`rf0` 复位 `0x7FF8_0000_7FC0_0000`（架构自定义确定性复位） | **ADR-0004 §D1/D2**（内存映射、复位向量与复位值） |
| 4 | **`ra0` 语义（MemRAS 简化）** | `SimRISC-00 §返回地址栈`（v5 修订前；对照归档 `.tao/archive/SimRISC-0.5.3/SimRISC-00`）：`ra0` 高 16 位 = **MemRAS 引用计数** | v5 `ra0` = `[63:54]` SBZ + `[53:48]` **`RACNT`** + `[47:0]` **`MRPTR`**；**取消 MemRAS 引用计数**；有效性判据 = `RACNT` | **ADR-0012 §D7**（D7.1–D7.7） |
| 5 | **`e_flags` 版本字段** | `spec/` **无 ELF/Object ABI**（`e_machine`/`e_flags` 无依据） | `e_machine = EM_DADAO (0x0DA0)`（project-custom，未注册）；`e_flags = 0x00000001`（bits 0–7 = 对象/ABI 格式版本 = 1；bits 8–31 保留 0） | **ADR-0003 §D1**（含 `## 修订` 的 `e_flags` 版本字段）；投影 `contract-elf.md §1.3` |
| 6 | **M1/M2 排除口径**（**订正**） | 上游把浮点（`SimRISC-07`）、特权 cfx（`SimRISC-11 §特权指令` + `DADAO-12/13`）、LR-SC（`SimRISC-12 §LR-SC指令`）、`fence`（`SimRISC-12 §fence指令`）均定义为架构指令 | v5 用 `scope ∈ {m1, fp, excluded}` 划范围：`m1` 已实现；**`fp` 60 条已实现（不再是 ILLI）**；`excluded` 15 条（cfx 6 + fence 1 + LR-SC 8）仍 decode **ILLI** | **ADR-0012 §D3.1**（0 号寄存器/范围）+ **ADR-0014**（fence excluded）+ `SPEC-086t`（scope 口径，`contracts/opcodes.yaml` + `check_scope.py`） |
| 7 | **汇编伪指令集收缩**（删上游 5 类伪指令） | `SimRISC-0.5.4 §伪指令`：定义 18 条伪指令，含 `nop`/`return`/`not.{b,w,t,o}`/`neg.{b,w,t,o}` 共 10 条 1:1 别名 | v5 只保留「ISA 无法直接表达、需多指令合成」的 **8 条合成型**（`set.rd`×2/`set.rb`×2/`set.ft`×2/`set.fo`×2）；删除 10 条 1:1 别名（`nop`→`swym 0`、`return`→`ret rd0, 0`、`not.*`→`xnor.o`、`neg.*`→`sub.sX`）；`ret` 不加无参形态；反汇编只显真实指令 | **ADR-0013 §D11** |

> **订正说明（第 6 项）**：历史表述「浮点未实现 ⇒ decode ILLI」在 `QEMU-034t`~`037t`（执行层 60/60）后**已不成立**；现行口径为「**浮点已实现**（`scope: fp`），**仅** cfx/LR-SC/fence（`scope: excluded`）仍 ILLI」。本台账以此为准。
>
> **章节订正（实测）**：任务书/`docs/m2-spec-planning.md` 沿用 **SimRISC 0.5.3 编号**；v5 现行规范为 **0.5.4**，章节已重排——上游依据「exit port vs `escape`」现位于 `SimRISC-11 §退出指令`（0.5.3 为 `SimRISC-04`）、`fence` SBZ 位于 `SimRISC-12 §fence指令`（0.5.3 为 `SimRISC-04`）、浮点规范为 `SimRISC-07`（0.5.3 为 `SimRISC-03`）。均以 `contracts/opcodes.yaml` 的 `spec_cite` 实测为准。

## 如何参考 DADAO-0628 和 DADAO

- `DADAO-0628`：基于 SimRISC 0.4.1 的完整实现，包含补丁集和任务文件
- `DADAO`：各阶段早期的代码实现（已不再更新），包含 LLVM/QEMU/Chipyard 等组件的具体实现
- 两者 commit 锁定于 `manifests/references.lock.toml`（由 `INFRA-003t` 建立）
- 路线图与任务拆解直接参考 DADAO-0628：`docs/development-roadmap.md`（M0/M1/M2/M2.5）、`code-agent/designs/0002-detailed-roadmap.md`、`code-agent/tasks/`

## 规范版本对应

规范版本与冻结状态的**唯一来源**是 `README.md`「当前版本号」表（SimRISC 0.5.4 / AEE·ABI 0.9.2 / SEE·SBI 0.7.1 / HEE·HBI 0.1.2）。v5 不使用 `manifests/spec.lock.toml`。

## 关键差异提示（相比 DADAO-0628）

DADAO-v5 基于 SimRISC 0.5.4 规范，与 DADAO-0628（锁定在 SimRISC 0.4.1）相比有以下关键差异：

### 0.5.4 vs 0.4.1 的变化

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
- 命名规范：wpN（非 ww）、pmem（非 phymem）（初版对比 0.4.1；`illi` 已删除，见 `ADR-0012 D3.5`——原对比 `unimp`）
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
