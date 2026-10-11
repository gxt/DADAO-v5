# QEMU-056t: RAM 基址改为 `0xFC00_0000_0000`（cfxha 63 段）

**模块**：qemu
**项目里程碑**：M7
**依赖**：无（M6 已验证态；`INTEG-033k` 裁定 #10）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定原话（2026-10-11；`INTEG-033k §裁定汇总 #10`）：「不想在此阶段引入其它 cfx 支持 ⇒ **有效地址空间只能在 `[47:42]` 为全 1 的情况下进行**；RAM 通常从 0 寻址 ⇒ **改为 `0xFC00_0000_0000`**；后续加 cfx 后此配置可不变」；「**16 MiB 够用 ⇒ 不改大**」。
  - `ADR-0004` rev. 2026-10-11（**就地修订**，覆盖 `R3` 的 RAM 基址口径）：RAM 基址 `0x0000_0000_0000` → **`0xFC00_0000_0000`**；复位向量/ROM（`0xffff_ffff_0000`，64 KiB）与 RAM 容量（16 MiB）不变。
  - `spec/DADAO-12 §2.1`：48 位核内地址 `bits[47:42]` = cfxha；cfxha 63 = `power` 段。`0xFC00_0000_0000` 的 `bits[47:42] = 63`。
  - 现行（M6 `QEMU-053t` 收口后）：`DADAO_RAM_BASE = 0x000000000000`（**唯一 RAM 段**，RAM@0）；`DADAO_RAM_SIZE = 16 MiB`；旧 RAM 段（`0xffff_0000_0000`）与 exit-port 设备已删。
- **输出**：
  1. QEMU 侧 RAM 唯一段基址改为 `0xFC00_0000_0000`：`components/qemu/patches/target/dadao/cpu.h.patch`（`DADAO_RAM_BASE`）、`hw/dadao/dadao-machine.c.patch`、`target/dadao/helper.c.patch`、`cpu.c.patch` 等以 `DADAO_RAM_BASE` 宏为真源的引用**随之生效**（**不写死地址**）。
  2. 测试侧跟改：`tests/scripts/dadao.lds`（`MEMORY RAM ORIGIN`）、`tests/scripts/codegen_crt0.s`、`tests/scripts/bootrom.S`/`bootrom_app.S`、`tests/e2e/*`、`tests/llvm/codegen/**`（如含地址）、`tests/vectors/isa/{ctrl-*,mem-*}.yaml`（地址类期望值，**重派生、禁反填**）。
  3. `tools/testcases/build_test_binary.py`（`BINARY_BASE`/`EXIT_BLOCK`/`DUMP_BASE`）、`tools/qemu/min_rom_probe_*.py`（`SEMI_BLOCK`/栈/数据地址）、`tools/qemu/gen_trampoline.py`（`trampoline.bin`）随地址跟改。
  4. `tools/integ/check_interface_alignment.py`：`RAM_BASE` 断言改为新基址（**从单一真源派生、不写死**）。
  5. `spec/Machine-01-测试机运行环境.md §1`（地址图正文）+ 该册 `sha256` 锁同步。
  6. **`components/qemu/README.md` 补丁规模刷新**（`INTEG-036t §收口核对` 并入的 M6 遗留）：`README.md:10` 现述「规模（2026-09-23 M1 重整后）：31 份 = 新增 25 + 修改 6」为**旧值**——**现场统计**（脚本从 `components/qemu/patches/` 实数）后刷新为实值，**计数不写死**。
- **约束**：
  - **`ADR-0004 D5.8` fault 码表冻结不重排**（`0x81`–`0x8D`）；越界分类规则不变（`cfxha==0` 段 ⇒ `CFXMEM 0x81`、其余含 power 段 ⇒ `unmapped 0x87`），但**地址区间随新基址重算**。
  - **不改规范正文以外内容**；`ADR-0004` 正文（决策节点）不改写（`Process-03`）。
  - **计数/地址不写死**：门控计数、地址断言须**派生自单一真源**（`DADAO_RAM_BASE` 宏 / `dadao.lds`）。
  - 只动任务范围，越界须披露。

## 避坑清单（blast radius）

- **M6 `QEMU-053t` 刚把 RAM@0 收口 ⇒ 本次要再改一遍**（`INTEG-033k §避坑`）；改动面横跨 QEMU 补丁、`tests/scripts`、`tests/**`、`tools/**`、`spec/Machine-01`+锁。
- **旧「RAM@0 在 umon 段」越界断言失效**：`0xFC00_0000_0000` 与 boot ROM 同属 cfxha 63（`power`）段但偏移不同 ⇒ `umon` 段（`addr[47:42]==0`）越界 ⇒ `0x81` 的既有用例须复核（新 RAM 已不在 umon 段）。
- **补丁导出纪律**：补丁写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥（`AGENTS.md`「组件补丁」）。
- **失败保留现场并继续推进**（`AGENTS.md`「最小安全设计」）。

## 验收标准

1. **地址真源**：QEMU `DADAO_RAM_BASE = 0xFC00_0000_0000`（`grep` 真实输出）；`DADAO_RAM_SIZE = 16 MiB`；**唯一 RAM 段**（无旧 RAM 段/退出端口）。
2. **测试侧一致**：`tests/scripts/dadao.lds` 的 `MEMORY RAM ORIGIN = 0xFC0000000000`；`bootrom`/`crt0`/harness 地址随改；无遗留旧基址（`grep` 现场统计，**不写死计数**）。
3. **门控全绿**：`make check`、`make check-interface`、`make check-qemu-semantics`、`make check-patch-tree` **EXIT=0**；`make test-codegen`/`test-elf`/`test-semihost` PASS。
4. **E2E**：至少一条 ELF 直载 + 一条 raw-bin 路径在新基址下正确退出码（真实输出）。
5. **反例门控**：`check_interface_alignment.py` 注入反例（把断言期望改回 `RAM_BASE=0` 或篡改 `cpu.h` 基址）⇒ **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿（有鉴别力）。
6. **规范同步**：`spec/Machine-01 §1` 地址图改为 `0xFC00_0000_0000`；`sha256` 锁同步（`check-spec-readonly` EXIT=0）。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区
**测试结果**：通过。`make check` rc=0；`make check-modules`(L2) rc=0（`check-interface` 83/83、`check-lit` 89/89、`check-qemu-smoke` 86/86、`test-codegen` 15/15、`test-elf` 5/5、`test-semihost` m5 10/10 + `046t` 25 服务）；`make check-qemu-semantics` 149/149 rc=0；`check-patch-tree` 110 patches rc=0。证据脚本 `.work/evidence/QEMU-056t/run.sh` 28/28 rc=0（含注入 FAIL⇒`cp`+md5 还原⇒回绿）。失败项：无（命令原始日志见 `.work/log/qemu/QEMU-056t-*.log`）。

**修改文件**（68 个；`git status` 无 untracked）：QEMU 补丁 `components/qemu/patches/{target/dadao/cpu.h,helper.c, hw/dadao/dadao-machine.c}.patch` + `components/qemu/{README.md,changelog.md}`；测试 `tests/scripts/{dadao.lds,codegen_crt0.s,bootrom.S,bootrom_app.S,build_test_binary.py,gen_trampoline.py,trampoline.bin,run_qemu_test.py,README.md}`、`tests/e2e/smoke_*.s`、`tests/llvm/codegen/m5/*.s`+`m5/{expected.yaml,README.md}`、`tests/llvm/lit/MC/DADAO/README-m5.md`、`tests/vectors/{schema.md,isa/{ctrl-br,ctrl-call,ctrl-jump,ctrl-ret,mem-rd,mem-rb,mem-ra}.yaml}`；工具 `tools/testcases/{validate_vectors,009t-audit,generate_ctrl_br,generate_ctrl_jump_call_ret,generate_mem_vectors}.py`、`tools/qemu/min_rom_probe_*.py`（24）、`tools/integ/{check_interface_alignment.py,run_m5_e2e.py}`；规范/台账 `spec/Machine-01-…md`、`manifests/spec-readonly.lock.toml`、`README.md`、`.tao/knowledge/milestones.md`、`.work/evidence/QEMU-056t/run.sh`。

**验收结果**：
- 验收1 地址真源：`DADAO_RAM_BASE = 0xFC0000000000`（grep）、`DADAO_RAM_SIZE = 16 MiB`、唯一 RAM 段（1×`init_ram(ram…)`/1×`add_subregion(…DADAO_RAM_BASE…)`，无旧 RAM/exit-port）。
- 验收2 测试侧：`dadao.lds` `ORIGIN = 0xFC0000000000`；`bootrom`/`crt0`/harness 随改；live 树 `RAM@0` 残留 **0** 文件（现场统计）。
- 验收3 门控全绿：见「测试结果」。
- 验收4 E2E：ELF 直载 `multi_tu_call exit=42`；raw-bin `call_ptr_bank exit=42`（真实输出，`.work/log/qemu/QEMU-056t-test-{elf,codegen}.log`）。
- 验收5 反例门控：篡改 `cpu.h.patch` 基址→`check-interface` 断言 FAIL（`RAM_BASE=… FAIL`）→`cp`+md5 还原→回绿（`check_interface_*` 日志）。
- 验收6 规范同步：`Machine-01 §1` = `0xFC00_0000_0000`（cfxha 63）、版本 `0.2.1→0.3.0`+changelog、`sha256` 锁同步；`check-spec-readonly` rc=0、根 README `Machine=0.3.0`。
- 验收7 无残留：`git status --porcelain -uall` 仅本任务改动，无 `*_tmp*`/`*.orig`/`*.rej`。

**新发现/坑**：① 手工编辑 patch 文本会破坏 `@@` 计数与 `index` 新哈希（`git apply` 静默容忍）——`check-patch-tree` 断言⑨/`check-index-blobs` 兜底，修复用 `check_index_blobs.py --fix`+重放 series（教训建议沉淀）。② 源地址 `0xFC00_0000_0000` 是 48-bit ⇒ `0xFC00` 在 wyde **wp2**（非 wp3）。③ RAM 迁 cfxha 63 ⇒ umon(0) 段无 RAM：addr=0 越界由 `UNMAPPED` 改判 **`CFXMEM 0x81`**；须补 `validate_vectors`/`schema.md`/`run_qemu_test FAULT_NAMES` 的 `CFXMEM`。④ 生成器与已提交向量存在**历史漂移**（`mem-rd/rb`、`ctrl-call/ret`；st.* 源=rd0 的 ILLI vs LEGAL），本次以生成器为准**重派生**。⑤ `046t svc_heapinfo` 隐含依赖「地址 0 属 RAM」（参数块 [0]=0 作输出指针），迁基址后暴露 ⇒ 改为 RAM 内输出指针。⑥ 任务书 §输出 3 路径失真：`tools/testcases/build_test_binary.py`→实为 `tests/scripts/…`；`tools/qemu/gen_trampoline.py`→实为 `tests/scripts/…`。⑦ spec 授权：`INTEG-033k §裁定汇总 #10` 原话见任务书「接口规范·输入」。

**遗留问题**：非门控历史探针（`005t`–`049t`，除 `046t`）已按同一规则（SEMI_BLOCK/SP/块/RAM 基址/MRPTR）迁移但**未逐例运行**（其 QEMU 行为未逐一验证）；若干寄存器载荷类注释未改写为最终值（仅地址构造改）。生成器/已提交向量历史漂移（`st.*` 源=rd0 语义）未裁决，仅按生成器重派生。以上均不影响本任务门控与验收。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-10-11）

**重跑门控**（真实输出/退出码，无 `| tee` 吞码）：
- `make check` → **rc=0**
- `make check-modules` → **rc=0**（check-interface 83/83、check-lit 89/89、check-qemu-smoke 86/86、test-codegen 15/15、test-elf 5/5、test-semihost m5 10/10 + 046t 25 服务）
- `make check-qemu-semantics` → **rc=0**（149/149 passed）
- `make check-patch-tree` → **rc=0**（110 patches）
- `make check-spec-readonly` → **rc=0**（21 volumes）
- `make check-spec-drift` → **rc=0**

**地址真源/唯一段/残留**：
- `cpu.h.patch`：`DADAO_RAM_BASE=0xFC0000000000ULL`，`DADAO_RAM_SIZE=(16*1024*1024)` ✓
- `dadao-machine.c.patch`：1×`memory_region_init_ram` + 1×`add_subregion(...,DADAO_RAM_BASE)` + 1×ROM `add_subregion`；无旧 RAM/exit-port 设备 ✓
- live 树旧基址残留（`0x000000000000` 作 RAM 基址）：仅任务书描述历史状态 + changelog 记录变更前值（2 处可留）；**0 处实现/测试残留** ✓

**向量重跑 diff**：运行 `generate_{mem,ctrl_br,ctrl_jump_call_ret}.py` 后与已提交7份yaml diff，**全部 IDENTICAL** ✓。地址抽查：`ctrl-br rb0=0xFC0000000000`（RAM entry），taken→+8=0xFC0000000008，not-taken→+4=0xFC0000000004，与 spec 推导一致 ✓

**CFXMEM 0x81 判据链**：`spec/DADAO-13 §1` cause `1<<1`=CFXMEM → `0x80|1=0x81`；`ADR-0004 D5.8` 码表 `0x81`–`0x86` 冻结不重排；RAM 迁 cfxha 63 后 umon(0) 段无 RAM ⇒ addr=0 越界 → `CFXMEM 0x81`（`ADR-0020 D15` 路由规则）。schema/`ALLOWED_FAULTS`/`FAULT_NAMES` 三处均含 `CFXMEM 0x81`（grep 确认）✓。该改动未越出任务范围（任务书 §避坑 明确预警）

**check-interface 派生证据**：`check_interface_alignment.py` 从 `dadao.lds` `ORIGIN(RAM)` regex 派生 `ram_base_exp`，再与 `cpu.h.patch` `DADAO_RAM_BASE` 交叉核对（代码行323–344）✓。**独立注入**：改 `dadao.lds` ORIGIN → `0xAAAA00000000` → check-interface rc=2（2 FAIL：RAM_BASE + BINARY_BASE）→ `cp`+md5 还原（`5a1aab3f…` 相等）→ rc=0 ✓

**规范侧**：`Machine-01 §1` RAM 地址图 = `0xFC00_0000_0000` ✓；版本 `0.3.0` + changelog ✓；`sha256` 独立重算=`37ef2e7c…`与锁一致且只有该册变动 ✓；根 README `Machine | 0.3.0` ✓

**E2E**：`test-elf` 5/5 rc=0；`test-codegen` 15/15 rc=0 ✓

**`qemu/README.md` 规模**：`find patches/ -name "*.patch"` =34；新增27（target/dadao 22 + hw/dadao 3 + configs 2）+ 修改7（上游既有文件）= README 所述34 ✓

**遗留 `st.*/rd0` 判定**：独立重跑生成器产出与已提交向量完全一致（IDENTICAL），**不存在本任务引入的漂移**。`st.*` 源=rd0 → ILLI 是生成器既有逻辑，与 spec `SimRISC-01 §存取RD寄存器` rd0 禁用一致。**建议登记 issue**（语义澄清是否需显式 spec 引用），**不阻塞本任务**。

**证据脚本**：五项要求均满足——28 项断言各有可达 FAIL 路径 ✓、计数现场统计 ✓、反例注入非空且还原 ✓、无 `| tee` 吞码 ✓、28/28 rc=0 ✓。独立注入（改 `dadao.lds` ORIGIN，与 engineer 的 `cpu.h.patch` 注入不同）：FAIL → cp+md5 还原 → 回绿 ✓

**工作区对账**：`git status --porcelain -uall` 快照审查前后一致；目标文件 md5 审查前后一致（7 个文件均相等）。无未授权改动。

**判定**：**Accepted**。门控 6/6 全绿，地址真源/唯一段/无残留确认，向量重跑一致，CFXMEM 0x81 有 spec/ADR 依据且未越界，check-interface 派生正确且注入有鉴别力，规范侧同步，E2E 通过。**无阻断项**。

---

### 第 1 轮 engineer 自审（2026-10-11）

**范围**：逐文件自主审查本轮全部改动（QEMU 补丁 / `tests/scripts` / `tests/e2e` / `tests/llvm/codegen/m5` / `tests/vectors`+生成器 / `tools/qemu/min_rom_probe_*` / `tools/integ` / `spec`+锁 / 版本表+台账）。

**审查要点**：① 逻辑与 48-bit 地址构造（wyde 位置）；② `DADAO_RAM_BASE` 宏是否仍为唯一真源（不写死）；③ 门控可达 FAIL / 反例注入真伪；④ 边界（RAM 顶/底、umon 段越界分类、MRPTR）；⑤ 是否越界 / 是否造假（完成区与真实输出逐条对齐）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `dadao-machine.c.patch` hunk 计数应 501→502（手工加注释行） | ✅已修 | `@@ … +1,501 @@`→`+1,502` | `check-patch-tree` rc=0（110 patches） |
| F2 3 份补丁 `index` 新哈希陈旧（`git apply` 静默容忍） | ✅已修 | `check_index_blobs.py --fix` | `check-index-blobs` rc=0 |
| F3 `m5_perm_*`/`m5_trap_escape` 漏改（块地址非 RAM ⇒ CFXMEM） | ✅已修 | 各 2 处加 `or.w rb16, wp2, 0xfc00` | `test-semihost` m5 10/10 |
| F4 `046t svc_heapinfo` 隐含「地址 0 属 RAM」 | ✅已修 | 输出指针改 RAM 内 | `046t` rc=0（25 服务） |
| F5 `010t` 冗余 `or_w_rb(1,2,0xFC00)` | ✅已修 | 删冗余行 | py_compile OK / 逻辑复核 |
| F6 `022t`/`028t` 重复 `encode_rwii(…2,0xFC00)` | ✅已修 | 删重复行 | py_compile OK |
| F7 初版误把 `0xFC00` 置于 wyde wp3（48-bit 地址 ⇒ wp2） | ✅已修 | 全部改 `wp2` | `trampoline.bin` 字节断言 `4e0500ff4a06fc00…` |
| F8 `CFXMEM` 未入 schema/validator/harness | ✅已修 | `ALLOWED_FAULTS`/`schema.md`/`FAULT_NAMES` 增 `CFXMEM` | `validate-vectors` rc=0；`check-interface` 83/83 |

**未修 / 延后 finding**：R1 非门控历史探针（除 `046t`）未逐例运行；R2 生成器—已提交向量历史漂移（`st.*` 源=rd0 语义）未裁决。二者均**已登记于「遗留问题」**，属能力/范围缺口（探针非门控、向量语义非本任务面），不阻塞本任务验收。

**判决**：门控全绿（L1/L2 + `check-qemu-semantics` + `check-patch-tree` 均 rc=0），完成区结论与真实输出/退出码逐条对齐；F1–F8 全部 ✅已修。**可标 `待验收`**。
