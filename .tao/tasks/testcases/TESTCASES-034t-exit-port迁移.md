# TESTCASES-034t: exit-port → `SYS_EXIT` 迁移（范围 = 全部）

**模块**：testcases
**项目里程碑**：M5
**依赖**：`QEMU-046t`、`TESTCASES-033t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **定位**：M1–M4 的停机协议依赖 **exit port**（`ADR-0004 D3`，MMIO `0xffff_8000_0000` 8B 只写）。M5 起 `SYS_EXIT` **替代** exit-port（`ADR-0020 D8`）；**迁移范围 = 全部**（`INTEG-019k` 裁定 7）：M1–M4 **所有**依赖 exit-port 的向量/harness/oracle 全迁到 `SYS_EXIT`。
- **输入**：
  - `QEMU-046t`（semihosting `EXIT`/`EXIT_EXTENDED` → host `$?`；exit port 仍并存）+ `TESTCASES-033t`（semihosting 向量 + 退出码约定）。
  - `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，**D8**）；`adr-0004` 修订（**R2**：`SYS_EXIT` 替代 exit-port，迁移 = 全部）。
  - **现状（实测，`grep` 为准）**：依赖 exit-port 的向量/harness——如 `tests/vectors/**`（`expected_exit` 通过 `st.o` 写 exit port 的用例构造）、`tests/scripts/**`（`codegen_crt0.s`/`trampoline.bin`）、`tools/qemu/min_rom_probe_*.py`、`tools/integ/run_{codegen,elf}_e2e.py`、`tests/llvm/lit/**` 中依赖退出码的用例、`tools/testcases/build_test_binary.py` 等。**逐个 `grep` 列表（`0xffff_8000_0000`/`exit`/`st.o`）后迁移，不臆测**。
  - `.tao/knowledge/issues.yaml` 的 `ISS-147`（exit 码与 fault 区重叠：`137==0x89==UNDI` false-PASS 风险）。
- **输出**：
  - **逐个迁移**：把上列**全部**依赖 exit-port 的向量/harness/oracle 的**退出机制**改为经 `SYS_EXIT`（semihosting `EXIT`/`EXIT_EXTENDED`），并**同步更新期望值**（退出码语义/构造序列）。
  - **迁移后全量重跑确认绿**（`INTEG-019k` `/plan` 审阅 6 项建议）：`test-codegen` 15/15、`test-elf` 5/5、`check-lit`、`check-qemu-semantics`、`validate-vectors` 等逐项与改前**逐项相等**（`git` 差分/对拍）。
  - **`ISS-147` 随迁处置**：把 E2E/向量期望退出码**约束到 `0x00–0x7F`**（避开 fault 区 `0x80–0xFF`）；如迁到 `SYS_EXIT` 后语义已天然规避，则**结案**（`status: closed`，`resolved_by: TESTCASES-034t`），否则登记处置结论。
  - **兼容性说明**：exit-port 机制**不删**（`QEMU-046t` 保留）；本任务只把**测试侧**迁移到 `SYS_EXIT`；若个别用例因架构原因必须留 exit-port，须**逐条披露理由**（默认 = 全部迁）。
- **约束（硬）**：
  - **范围 = 全部迁移**（用户裁定）；**不得**只迁部分、**不得**保留 exit-port 兼容为默认。
  - **RAM@0 迁移不在本任务**（`ADR-0004 R3`/`ADR-0020 D15`）：把旧向量/harness 迁到 RAM@0（`0x0000_0000_0000`）= C1 **step2**，**另立、M5 之外**（编号待 M6 规划/另立时确定）；本任务只迁**退出机制**（exit-port → `SYS_EXIT`），**不动** RAM 段地址（`QEMU-049t` 双映射后旧 RAM 段过渡保留）。
  - **迁移 = 改退出机制 + 同步期望值 + 迁移后全量重跑确认绿**（三者齐备；`INTEG-019k` `/plan` 建议）。
  - 不改 `components/**`/`spec/`；`contracts/**` 如需（`expected_exit` 字段）须**停下报告**（跨组件）。
  - **期望值独立派生**；`test-codegen`/`test-elf` 通过数**逐项不回归**。
  - 临时目录 `/tmp/opencode/TESTCASES-034t/`；**不提交 git**；复杂命令输出留存 `.work/log/testcases/`（**禁 `tee`**）。
  - **重建成本申报**：依赖 `build-mc`/`build-lld`/`build-qemu`（增量；`build-qemu` 5–20 分钟）；开工前说明。

## 验收标准

1. **迁移覆盖**：`grep -rln "0xffff_8000_0000\|exit.port\|exit_port" tests/ tools/ | grep -v __pycache__ | grep -v archive` **为空**（或仅剩**逐条披露**的例外，附理由）；给真实 `grep` 输出列表（迁移前/后对照）。
2. **退出机制**：迁移后向量/harness 经 `SYS_EXIT` 获退出码（给 ≥2 条真实链路逐步输出）。
3. **期望值同步**：迁移后 `test-codegen` 15/15、`test-elf` 5/5、`check-lit`（通过数）、`check-qemu-semantics` 与改前**逐项相等**（给对拍/差分）。
4. **`ISS-147`**：E2E/向量期望退出码**全部落 `0x00–0x7F`**（`grep`/脚本枚举，真实输出）；`issues.yaml` 处置（closed 或登记结论）。
5. **反例门控**：注入反例（把某用例期望退出码改错 ⇒ 门控**非零退出** ⇒ 还原 ⇒ 回绿）；给真实输出。
6. **门控**：`make check` EXIT=0；`make check-no-residue` EXIT=0。
7. **一键证据脚本**：`.work/evidence/TESTCASES-034t/run.sh`——非交互、失败非零、逐项打印、含注入自检、结尾**禁 `tee`**。
8. **无残留**：`git status --untracked-files=all` 仅迁移的向量/harness/oracle + `issues.yaml` + 本任务书。

## 完成区

**测试结果**：**通过**（迁移后各门控与改前**逐项相等**）。
- `test-codegen` **15/15 EXIT=0**；`test-elf` **5/5 EXIT=0**；`check-lit` **62/62 EXIT=0**；`check-qemu-semantics` **149/149 EXIT=0**；`validate-vectors` **155/155**；`validate_codegen_vectors` **PASS(58)**、`validate_elf_vectors` **PASS(42)**、`validate_mc_vectors` **73 向量 0 错**、`validate_m5_vectors` **PASS(141)** 均 EXIT=0。
- `make check` **EXIT=0**（`check-patch-tree: 2 component(s), 92 patches OK`、`check-qemu-semantics: PASS 149/149`、lit 62/62、`check-no-residue: PASS`、`check-spec-readonly: 21`、`repository checks: PASS`、`check-issues: 39 open/3 closed`）；`make check-no-residue` **EXIT=0**。
- 探针（全部 26 个 `min_rom_probe_*.py`）迁移后**与改前逐条等价**（PASS 保持 PASS、pre-existing FAIL 保持 FAIL，见「验收结果」表）。
- 一键证据脚本 `.work/evidence/TESTCASES-034t/run.sh` ⇒ **`EVIDENCE: PASS` / `SCRIPT_EXIT=0`**（3 类注入各自 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿；结尾无 `tee`）。

**改前基线 vs 迁移后对拍**（逐项，实跑）：

| 门控 | 改前 | 迁移后 |
|------|------|--------|
| `test-codegen`（`run_codegen_e2e`） | 15/15 EXIT=0 | 15/15 EXIT=0 |
| `test-elf`（`run_elf_e2e`） | 5/5 EXIT=0 | 5/5 EXIT=0 |
| `check-lit` | 62/62 EXIT=0 | 62/62 EXIT=0 |
| `check-qemu-semantics` | 149/149 EXIT=0 | 149/149 EXIT=0 |
| `validate-vectors` | 155/155 | 155/155 |
| `validate_codegen_vectors` | PASS 58 | PASS 58 |
| `validate_elf_vectors` | PASS 42 | PASS 42 |
| `validate_mc_vectors` | 73/0 | 73/0 |
| `validate_m5_vectors` | PASS 141 | PASS 141 |
| `make check` | EXIT=0 | EXIT=0（92 patches / lit 62 / semantics 149） |

> **退出码语义保持**：SYS_EXIT 的退出码 = `@main` 返回值低字节（M3/M4）、或 harness 构造的 code 低字节（ISA 向量），与旧 exit-port 的低字节语义一致 ⇒ 除 ISS-147 主动收窄的 7 条外，**期望值不变**。

**修改文件**（与 `git status --untracked-files=all` 一致，45 个 + 本任务书；`.work/**` gitignored 不入库）：
- **核心退出机制（M3/M4/M5 门控路径）**：
  - `tests/scripts/codegen_crt0.s`（改）——`_start` 由「写 exit-port」改为 **semihosting `SYS_EXIT`**（块 `{0x20026, rd31}` @ `0xffff_00ff_f000`，`rd16=0x18`，`trap cfx_umon, 0x30000`）。
  - `tools/integ/run_codegen_e2e.py` / `tools/integ/run_elf_e2e.py`（改）——QEMU 调用加 `-semihosting-config enable=on,target=native`；docstring/容错注释同步（ISS-147）。
  - `tests/scripts/build_test_binary.py`（改）——退出段由「写 exit-port」改为 `emit_sys_exit`（块 @ `0xffff_00fd_0000`）；移除 `EXIT_PORT`/`TEMP_RB`，新增 `EXIT_BLOCK`/`encode_trap`/`emit_sys_exit`；PASS/FAIL 段用动态 br 偏移。
  - `tests/scripts/run_qemu_test.py`（改）——`run_qemu` 加 `-semihosting-config`；文档块注释同步。
  - `tests/e2e/smoke_{add,arith,fp,jump}.s`（改）——退出改 semihosting `SYS_EXIT`（`rb16`=块指针，非旧的 `rb3`=exit port）；`tests/e2e/lit/smoke_*.test`（改）——RUN 行加 `-semihosting-config`。
- **ISS-147（收窄期望退出码到 0x00–0x7F）**：`tests/llvm/codegen/{arith_add_sub_neg,arith_const_hi_wyde,mem_narrow_be_wide,call_multiarg_stack,call_narrow_args,ptr_add_offset,ptr_diff_neg}.ll`（改，末次掩码 `255→127`）、`tests/llvm/codegen/expected.yaml`（改，7 条期望值 + derivation）、`tools/testcases/validate_codegen_vectors.py`（改，oracle `&0x7F`，range 检查收紧为 `0..0x7F`）。
- **探针迁移（16 个）**：`tools/qemu/min_rom_probe_{022t,028t,031t,032t,033t,034t,035t,036t,037t,038t,040t,042t,044t,045t,046t,049t}.py`（改）——退出通道改 `SYS_EXIT`（部分含 no-op `jump` 强制 TB dump，见「新发现 3」）。
- **文档/台账**：`tests/llvm/codegen/README.md`、`tests/llvm/codegen/m4/README.md`、`tests/llvm/codegen/m4/expected.yaml`（头注）、`tests/scripts/README.md`、`tests/vectors/schema.md`、`tools/integ/check_interface_alignment.py`（retire `harness.EXIT_PORT` 子检查，保留 QEMU 侧常量校验并注明为保留设备）、`.tao/knowledge/issues.yaml`（ISS-147 closed + 新增 ISS-169 披露例外）。
- 本任务书（完成区/自审/状态）。
- **未改** `spec/`、`contracts/`、`components/`、`Makefile`。

**验收结果**（真实命令输出/rc；日志在 `.work/log/testcases/`、`/tmp/opencode/TESTCASES-034t/`）：
1. **迁移覆盖（grep 前后对照）**：改前 `grep -rln "0xffff_8000_0000\|exit.port\|exit_port" tests/ tools/`（排除 `__pycache__`/`archive`）= **38 文件**（见 `/tmp/opencode/TESTCASES-034t/baseline-grep.txt`）；迁移后 = **7 文件**，且**恰好等于逐条披露的例外集**（脚本断言，见证据脚本第 1 步 `PASS residual exit-port refs == disclosed exceptions (7 files)`）：
   - `tools/integ/check_interface_alignment.py` —— 仅校验 **QEMU 保留的 exit-port 设备常量**（`DADAO_EXIT_PORT_BASE/SIZE`；`ADR-0020 D8` 只取代「停机协议」，设备仍保留），非测试退出通道。
   - `tools/qemu/min_rom_probe_{006t,008t,009t,010t,012t,013t}.py` —— 见「遗留问题 / ISS-169」逐条披露（006t = exit-port 设备测试；009t = OBSOLETE；008t/010t/012t/013t = 退出与手算 PC 偏移交错）。
2. **退出机制（≥2 条真实链路）**：
   - **链路 A（M3）**：`run_codegen_e2e.py`：`crt0.s → llvm-mc → llvm-objcopy → qemu -bios trampoline.bin -kernel <bin> -semihosting-config enable=on,target=native`；逐例 `expected==actual`（如 `call_direct_ret.ll expected=9 actual=9`；`arith_add_sub_neg.ll expected=118 actual=118`）——退出码经 `SYS_EXIT` 从 host `$?` 取得。
   - **链路 B（M4）**：`run_elf_e2e.py`：`llc→ld.lld→qemu -kernel <elf> -semihosting-config …`；`multi_tu_call expected=42 actual=42`。
   - **链路 C（ISA 向量/harness）**：`run_qemu_test.py` + `build_test_binary.emit_sys_exit`：`check-qemu-semantics` 149/149（含 fault 用例仍走 QEMU fault 码）。
   - **链路 D（M5 semihosting 向量，回归）**：`run_m5_e2e.py` 10/10（`SYS_EXIT`/`SYS_EXIT_EXTENDED` 本就用于 M5；本任务不改）。
   - **反证**：注入 B/C 破坏 `SYS_EXIT` 服务号（`0x18→0x19`）⇒ 链路 A/C 门控**非零退出**（见证据脚本）。
3. **期望值同步（对拍）**：见上「改前基线 vs 迁移后对拍」表，逐项相等；`test-codegen` 15 条逐例实跑（118/110/77/41/108/45/16/25/9/43/9/42/43/7/121）、`test-elf` 5 条（42/30/108/8/126）。
4. **`ISS-147`**：`tests/llvm/codegen/expected.yaml` **全部 15 条** `expected_exit_code` **落 `0x00–0x7F`**（脚本枚举：`all 15 expected_exit_code values in 0x00..0x7F`）；M4 manifest 全部本已 ≤0x7F。`issues.yaml`：`ISS-147` **closed**（`resolved_by: TESTCASES-034t`）。validator 的 range 检查收紧为 `0..0x7F`（超界即 FAIL，机器可查）。
5. **反例门控**：证据脚本 3 类注入（`expected.yaml` 期望值 118→119 / `codegen_crt0.s` `SYS_EXIT 0x18→0x19` / `build_test_binary.py` `SYS_EXIT 0x18→0x19`）**各自 ⇒ 对应门控非零退出**（rc=1/1/2）⇒ `cp`+**md5 相等**还原 ⇒ 回绿（真实输出见证据脚本运行日志）。
6. **门控**：`make check` **EXIT=0**；`make check-no-residue` **EXIT=0**。
7. **一键证据脚本**：`.work/evidence/TESTCASES-034t/run.sh` ⇒ **`EVIDENCE: PASS` / `SCRIPT_EXIT=0`**（非交互、失败非零、逐项打印、3 类注入自检、结尾 `exit $rc`、**无 `tee`**）。
8. **无残留**：`git status --untracked-files=all` = 45 个改动文件 + 本任务书；无 `*_tmp*`/`*_gate*`/`*.orig`/`*.rej`/`*.preinject`；注入后 md5 与注入前一致（`.work/evidence/...` 备份在 `/tmp`，非仓库内）。
9. **探针等价（逐条）**：26 个探针改前/改后**逐条一致** —— PASS 保持：005t/011t/012t/022t/030t/031t/032t/033t/034t/035t/036t/037t/038t/040t/042t/044t/045t/046t/047t/049t；pre-existing FAIL 保持（ISS-120）：006t/008t/009t/010t/013t/028t（028t 改后与改前逐行 diff 相同）。

**新发现/坑**（建议沉淀知识库）：
1. **semihosting 约定「块指针 = `rb16`、退出码在内存块、非寄存器」**：旧 exit-port 是「`st.o rdN, [rb16=0xffff_8000_0000, 0]`（写寄存器到 MMIO）」；`SYS_EXIT` 是「内存块 `{0x20026, code}` + `rd16=0x18` + `trap`」。迁移初版把块指针放 **`rb3`**（沿用 exit-port 的寄存器习惯）⇒ 全部 FAIL（`SYS_EXIT` 读 `rb16`）；**必须用 `rb16`**。（`contract-semihosting §2`；`ADR-0020 D2/D14`）
2. **`-semihosting-config enable=on,target=native` 必须由 harness 显式给**：否则 `SYS_EXIT` 不可达。与 `ADR-0020 D7`（建议默认 `gdb`/沙箱、`native` 显式开）的关系：测试侧**显式**开 `native` 属合规（`native` 不被默认，正合 D7）。**补充实测**：QEMU 共享层 `SYS_EXIT` 处理段为 `gdb_exit(ret); exit(ret);`——`exit()` 无条件执行，故 `target=gdb|native` 均应传播 `$?`；本任务按 architect 指令统一用 `native`。
3. **`-d cpu`「最后一次 dump」观测陷阱（探针）**：旧 exit-port 的 `st.o` 是 **MMIO**，QEMU 会强制在 store 前切分 TB（`CF_LAST_IO`）⇒ 「最后一次 dump」恰好落在 store 前、捕获到 `ld_o` 等前置结果；而 `SYS_EXIT` 的 `trap` 由 `raise_exception`→`cpu_loop_exit_restore` 结束 TB，**不在 trap 前切分** ⇒ 若「读取观测值的 `ld_o`」与 exit 序列同处一个 TB，最后一次 dump 落在 `ld_o` 之前、观测到旧值（`svc_read`/`svc_get_cmdline` 曾因此 FAIL）。**修法**：exit 序列**前置一条 no-op `jump`（`jump-iiii imms24=1`，跳转至下一条指令）**，强制 TB 边界 + 回主循环 + 记录下一 TB 的 dump。已在 046t/049t 应用。
4. **ISS-147 实为 7 条而非 5 条**：初判只列 5 条超 0x7F，脚本枚举发现另有 `call_multiarg_stack`=171、`ptr_add_offset`=171（均为 0xAB，亦落 fault 区）。**教训：判据须脚本枚举全量，不靠目测抽样。**
5. **一份 `codegen_crt0.s` 同时服务两条管线**：同一 stub 在 M3（`cat crt0.s prog.s` 单 TU、无 link）与 M4（`llvm-mc crt0.o` + `ld.lld`）下均可用 ⇒ 迁移点收敛为 1 文件 + 2 driver。
6. **`trap` 在 raw-bin（`-bios trampoline.bin`）路径下即经译码层短路工作**，不依赖 SEE bundle/向量（`SYS_EXIT` 只需 `-semihosting-config`）。故 M3/M4 老管线无需 bootrom 即可用 semihosting 停机。

**遗留问题**：
- **6 个 M1/M2 期手写 ROM 探针未随迁**（`006t/008t/009t/010t/012t/013t`）——**逐条披露**（登记 `ISS-169`）：
  1. `006t`：显式测**保留的 exit-port MMIO 访问矩阵**（T22/T23/T28–T34：非 8B/multi 写 ⇒ ILLI、对齐优先级 ⇒ MALIGN；`ADR-0004 D5.6`）——是**设备测试**而非退出通道。
  2. `009t`：文件头标注 **OBSOLETE / DO NOT RUN**（`rela.si` 已删、op=0x5A 现为 UNDI），仅存历史物。
  3. `008t/010t/012t/013t`：用例是手排字面指令表，退出为**单条 `st.o rdN,[rb16,0]` 且与手算 PC 相对分支偏移交错**（PASS/FAIL 臂、跳过臂）；展开为多指令 `SYS_EXIT` 会改变字长、使手算偏移失效（而分支偏移恰是 012t 的被测对象）。→ 建议另立/随 M6 任务重写这 6 个探针的退出通道（含按新字长重算分支偏移），届时移除例外。
  - **不影响 M5 门槛**：迁移面中**所有进入 `make` 门控**的向量/harness/驱动均已迁 `SYS_EXIT` 且门控全绿。
- **`tools/integ/check_interface_alignment.py` 保留 QEMU 侧 exit-port 常量校验**（`DADAO_EXIT_PORT_BASE/SIZE`）：exit-port 为**保留设备**（`QEMU-046t`），校验其常量仍属正当接口对齐；已加注释说明。
- **`ISS-147` 的 M3 期望值语义经程序掩码 `255→127` 收窄**：被改的 7 个程序（及其 derivation）语义未变（仍测同一指令：`and`/`add`/`sub`/`xor`/`lshr`/`zext`/`sub.o`），仅末次掩码位宽改窄以避开 fault 区。
- **未改** `spec/`、`contracts/`、`components/`、`Makefile`（本任务按预检结论；`contracts/opcodes.yaml` 的 `expected_exit` 字段无需改动）。
- `.work/evidence/TESTCASES-034t/run.sh`、`.work/log/testcases/**` 为 gitignored 非入库证据。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：逐行审查全部改动（45 个产品/台账文件 + 本任务书）——3 条门控核心（`codegen_crt0.s`/`build_test_binary.py`/`run_codegen_e2e.py`/`run_elf_e2e.py`/`run_qemu_test.py`）+ 4 个 e2e smoke（`.s`+`.test`）+ 7 个 `.ll` + 2 个 expected.yaml + oracle + 16 个探针 + 文档/台账；核对 Spec-first（`contract-semihosting §1–§5`、`Machine-01 §5`、`ADR-0020 D1/D2/D7/D8/D14`、`ADR-0004 D3(superseded)/D5.7/D5.8/R2`）、边界（不改 `spec/`/`contracts/`/`components/`/`Makefile`）、防造假（真实执行、完成区逐条对齐、证据脚本无 `tee`、注入可达 FAIL 且还原）。

**结论**：逻辑正确、边界受控、验证真实；改前基线已留存并对拍；16 个探针迁移后与改前**逐条等价**（无回归）。发现并当场处置如下表（无未修 finding）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 迁移初版把 semihosting 块指针放 **`rb3`**（沿用 exit-port 习惯）⇒ smoke 全 FAIL | ✅已修 | 4 个 smoke `.s` 改用 **`rb16`** = 块指针 | 4 个 smoke 经 `-bios trampoline` + `-semihosting-config` 跑出 `QEMU EXIT=0`（PASS 路径） |
| F2 `test-codegen`/`test-elf` 需 `-semihosting-config`，否则 `$?` 不传播 | ✅已修 | 两个 driver 的 qemu 调用加参数；`run_qemu_test.py` 同 | `test-codegen` 15/15、`test-elf` 5/5、`check-qemu-semantics` 149/149 EXIT=0 |
| F3 ISS-147 初判 5 条，实为 **7 条**（漏 171=0xAB×2） | ✅已修 | `call_multiarg_stack.ll`/`ptr_add_offset.ll` 亦改掩码 `&127`；oracle/expected.yaml 同步 | 脚本枚举 `all 15 … in 0x00..0x7F`；`test-codegen` 15/15 |
| F4 探针 `-d cpu` 观测：`SYS_EXIT` 的 trap 不在 store 前切 TB ⇒ 最后一次 dump 落 `ld_o` 之前（`svc_read`/`svc_get_cmdline` FAIL） | ✅已修 | 046t/049t 的 `exit_seq` 前置 no-op `jump-iiii(1)` 强制 TB 边界 | 046t/049t 由 FAIL 回绿（`RESULT: PASS`） |
| F5 `032t` 的 `case_positive_ret_rd0_0` 手写用 `st_o_rd_pass()`（旧 exit-port 写）⇒ 落到 `fence` 成 0x88 | ✅已修 | 该用例末尾改为 `semi_exit(18)`（并按新字长重排 call 目标） | `032t` 4/4 PASS |
| F6 各探针遗留的 `exit port`/`EXIT_PORT` 注释/用例名（会命中 acceptance-1 grep） | ✅已修 | 统一改写为 `SYS_EXIT`/`legacy MMIO halt device` | 证据脚本第 1 步 grep 断言 = 7 文件例外集；各探针 `grep -c` 归零（除披露集） |
| F7 移除了 `build_test_binary.py` 的 `EXIT_PORT`/`TEMP_RB`，需确认无孤儿引用 | ✅已核 | 全仓 `grep` 无残留引用；`py_compile` 通过 | `grep TEMP_RB/EXIT_PORT` 空；`py_compile OK` |
| F8 反例门控：注入须**可达 FAIL 且可还原**（禁 `git checkout`/`git show` 读回） | ✅已证 | 证据脚本 3 类注入（期望值 / crt0 服务号 / harness 服务号） | 注入 ⇒ rc=1/1/2；`cp`+md5 相等还原 ⇒ 回绿（脚本输出） |
| F9 6 个探针未随迁（设备测试/OBsolete/手算偏移交错） | ⏸**披露**（登记 `ISS-169`，附逐条理由；默认全迁、例外须披露） | 无（保留 exit-port；未强改） | 证据脚本第 1 步显式断言例外集；`ISS-169` |

**边界核查**：改动仅落在 `tests/**`、`tools/**`、`.tao/knowledge/issues.yaml`、本任务书；**`spec/` 交集空**、**未改 `contracts/**`/`components/**`/`Makefile`**；`.work/**`/`.dadao/**` 未入库。**状态**：无未修 finding（F9 为按规则披露的例外）⇒ 置「待验收」，返回主会话 `/complete`。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立验证）
**审查范围**：`run.sh` 审核 + 逐项独立重跑 + **独立注入2类反例** + 独立核 `grep` 覆盖/退出码区/对拍 + ISS-120 探针核验 + 判决

##### 验收项逐条核验

**1. 审证据脚本** `.work/evidence/TESTCASES-034t/run.sh`

逐条核对：
- `run_ok`/`run_fail`：捕获 `rc=$?` 直接赋值（第22/28行），**非 `tee`** ✓
- 3 类注入（A: `expected.yaml` 期望值 118→119 / B: `codegen_crt0.s` SYS_EXIT 0x18→0x19 / C: `build_test_binary.py` SYS_EXIT 0x18→0x19）：
  - 每类注入前 `cp` 备份 + `md5f` 记录 ✓
  - 注入后 `md5f` 比对确认非空注入 ✓
  - 还原用 `cp`（**禁 `git checkout/restore/stash`**）✓
  - 还原后 `md5f` 比对确认还原 ✓
- 结尾 `exit 0` 或 `exit 1`（基于 `$fail`），**无 `tee`** ✓
- `set -u` ✓
- 可达 FAIL 路径：3 类注入各自导致不同门控非零退出（A→test-codegen, B→test-codegen, C→check-qemu-semantics），**无恒真** ✓
- **结论：脚本合格**

**2. 重跑（逐项独立验证）**

未重跑完整脚本（含3次 `make check-qemu-semantics`，单次约2分钟），改为逐项独立验证脚本中每个检查项：

| 检查项 | 命令 | 真实输出 | EXIT |
|--------|------|---------|------|
| check-no-residue | `make check-no-residue` | `check-no-residue: PASS` | 0 |
| validate_codegen_vectors | `python3 tools/testcases/validate_codegen_vectors.py` | `validate_codegen_vectors: PASS (58 checks)` | 0 |
| validate_elf_vectors | `python3 tools/testcases/validate_elf_vectors.py` | `validate_elf_vectors: PASS (42 checks)` | 0 |
| test-codegen | `python3 tools/integ/run_codegen_e2e.py` | `15/15 passed` | 0 |
| test-elf | `python3 tools/integ/run_elf_e2e.py` | `5/5 passed` | 0 |
| test-semihost | `python3 tools/integ/run_m5_e2e.py` | `10/10 passed` | 0 |
| check-qemu-semantics | `make check-qemu-semantics JOBS=8` | `149 total, 149 passed` | 0 |
| check-lit | `make check-lit JOBS=8` | `62/62 passed` | 0 |
| validate-vectors | `make validate-vectors JOBS=8` | `155/155` | 0 |
| make check | `make check JOBS=8` | 全绿（92 patches / lit 62 / semantics 149 / 85 接口项） | 0 |

**3. 独立注入（自行执行）**

**注入 A**：改 `tests/llvm/codegen/expected.yaml` 期望值 118→119
- 备份：`cp` 到 `/tmp/opencode/TESTCASES-034t-review/expected.yaml.preinject`，md5=`a649d07d98bf9d0067617b31cd6edabc`
- 注入后 md5=`4ba36dd87121e364be4f9ff123cc4310`（非空 ✓）
- 重跑 `run_codegen_e2e.py`：**14/15 passed, 1 failed**（`arith_add_sub_neg.ll expected=119 actual=118`），**EXIT=1** ✓
- 还原：`cp` 回，md5=`a649d07d98bf9d0067617b31cd6edabc`（与备份一致 ✓）
- 重跑：**15/15 passed, EXIT=0** ✓

**注入 B**：改 `tests/scripts/codegen_crt0.s` SYS_EXIT 服务号 0x18→0x19
- 备份：`cp` 到 `/tmp/opencode/TESTCASES-034t-review/codegen_crt0.s.preinject`，md5=`730bbf2454eb43f5d48a2b79280fe90e`
- 注入后 md5=`36b5be9f9cb217c74bb567c0344cd5b4`（非空 ✓）
- 重跑 `run_codegen_e2e.py`：**0/15 passed, 15 failed**（全部 `machine fault RASUF (0x8B)`），**EXIT=1** ✓
- 还原：`cp` 回，md5=`730bbf2454eb43f5d48a2b79280fe90e`（与备份一致 ✓）
- 重跑：**15/15 passed, EXIT=0** ✓

**4. 迁移覆盖**

独立 `grep -rln "0xffff_8000_0000\|0xFFFF_8000_0000\|exit.port\|exit_port\|EXIT_PORT" tests/ tools/ | grep -v __pycache__ | grep -v archive | sort` 返回**恰 7 文件**：
```
tools/integ/check_interface_alignment.py
tools/qemu/min_rom_probe_006t.py
tools/qemu/min_rom_probe_008t.py
tools/qemu/min_rom_probe_009t.py
tools/qemu/min_rom_probe_010t.py
tools/qemu/min_rom_probe_012t.py
tools/qemu/min_rom_probe_013t.py
```
与披露集/`ISS-169` **逐一相符** ✓。逐条理由核验：
- `check_interface_alignment.py`：仅校验 QEMU 保留的 exit-port 设备常量（`DADAO_EXIT_PORT_BASE/SIZE`），非测试退出通道 ✓
- `006t`：显式测保留的 exit-port MMIO 访问矩阵（T22/T23/T28–T34），是设备测试 ✓
- `009t`：文件头标注 OBSOLETE / DO NOT RUN ✓
- `008t/010t/012t/013t`：退出与手算 PC 相对分支偏移交错，展开为多指令 SYS_EXIT 会改变字长使偏移失效 ✓

**5. 不回归（对拍）**

独立实跑全部门控，与改前基线逐项相等：

| 门控 | 改前基线 | 独立实跑 | 回归？ |
|------|---------|---------|--------|
| test-codegen | 15/15 EXIT=0 | 15/15 EXIT=0 | 无 ✓ |
| test-elf | 5/5 EXIT=0 | 5/5 EXIT=0 | 无 ✓ |
| check-lit | 62/62 EXIT=0 | 62/62 EXIT=0 | 无 ✓ |
| check-qemu-semantics | 149/149 EXIT=0 | 149/149 EXIT=0 | 无 ✓ |
| validate-vectors | 155/155 EXIT=0 | 155/155 EXIT=0 | 无 ✓ |
| validate_codegen_vectors | PASS(58) EXIT=0 | PASS(58) EXIT=0 | 无 ✓ |
| validate_elf_vectors | PASS(42) EXIT=0 | PASS(42) EXIT=0 | 无 ✓ |
| make check | EXIT=0 | EXIT=0（92 patches / lit 62 / semantics 149） | 无 ✓ |

**6. 退出机制**

≥2 条真实链路经 `SYS_EXIT` 取退出码：
- **链路 A（M3）**：`run_codegen_e2e.py`：`codegen_crt0.s` → `SYS_EXIT`（`set.zw rd16, wp0, 0x0018` + `trap cfx_umon, 0x30000`）→ QEMU `-semihosting-config enable=on,target=native` → host `$?`。15/15 逐例 expected==actual ✓
- **链路 B（M4）**：`run_elf_e2e.py`：同 `codegen_crt0.s` → `SYS_EXIT` → QEMU semihosting。5/5 ✓
- **链路 C（ISA 向量）**：`build_test_binary.py` 的 `emit_sys_exit()` → `check-qemu-semantics` 149/149 ✓
- **ADR-0020 D7 合规性**：所有 QEMU 调用显式传 `-semihosting-config enable=on,target=native`（native 非默认，由 harness 显式开启，符合 D7）✓

**7. `ISS-147`**

独立枚举 `tests/llvm/codegen/expected.yaml` 全部15条 `expected_exit_code`：
```
arith_add_sub_neg:    118 (0x76) [OK]
arith_const_hi_wyde:  110 (0x6e) [OK]
mem_store_load_offset: 77 (0x4d) [OK]
mem_narrow_be_bytes:   41 (0x29) [OK]
mem_narrow_be_wide:   108 (0x6c) [OK]
branch_loop_sum:       45 (0x2d) [OK]
branch_eq_ne:          16 (0x10) [OK]
branch_ptr:            25 (0x19) [OK]
call_direct_ret:        9 (0x09) [OK]
call_multiarg_stack:   43 (0x2b) [OK]
call_narrow_args:       9 (0x09) [OK]
call_ptr_bank:         42 (0x2a) [OK]
ptr_add_offset:        43 (0x2b) [OK]
ptr_diff_pos:           7 (0x07) [OK]
ptr_diff_neg:         121 (0x79) [OK]
```
全部落 `0x00–0x7F` ✓（engineer 报7条改掩码：`arith_add_sub_neg`/`arith_const_hi_wyde`/`mem_narrow_be_wide`/`call_multiarg_stack`/`call_narrow_args`/`ptr_add_offset`/`ptr_diff_neg`，与 git diff 一致 ✓）。`issues.yaml`：`ISS-147` **closed**（`resolved_by: TESTCASES-034t`）✓

**8. `ISS-120` pre-existing FAIL 未被引入或扩大**

独立实跑2个未迁移探针：
- `min_rom_probe_006t.py`：**32/34 passed, 2 failed**（T8 `st.o rd0` exit=0x00 expect 0x88 / T12 `stm.o+ldm.o round-trip` exit=0x89 expect 0x88），CTL 自检3项 FAIL，EXIT=1。与 ISS-120 同因（QEMU `st.o rd0` 行为不符预期）✓
- `min_rom_probe_010t.py`：**24/28 passed, 4 failed**（T6/T14/T18/T21 exit=0x89 expect 0x87/0x88），CTL 自检6项 FAIL，EXIT=1。与 ISS-120 同因 ✓

独立实跑迁移后探针（应 PASS）：
- `min_rom_probe_032t.py`：**4/4 PASS, EXIT=0** ✓
- `min_rom_probe_044t.py`：**13/13 PASS, EXIT=0** ✓
- `min_rom_probe_046t.py`：**32/32 PASS, EXIT=0** ✓
- `min_rom_probe_049t.py`：**9/9 PASS, EXIT=0** ✓

**9. 门控**

- `make check` **EXIT=0**（check-patch-tree: 92 patches OK / check-qemu-semantics: 149/149 / check-lit: 62/62 / check-no-residue: PASS / check-spec-readonly: 21 / repository checks: PASS / check-issues: 39 open/3 closed）✓
- `make check-no-residue` **EXIT=0** ✓

**10. 未越界**

- `git diff --name-only 783ba9f..HEAD` = **46 文件**（与声明一致）✓
- `spec/` 交集 = 空（`grep '^spec/'` 无输出）✓
- 未触 `components/`/`Makefile` ✓
- `.work/**`、`.dadao/**` 未入库 ✓
- `git status --porcelain -uall` 仅本任务书（审查写入中）✓

##### 审查结论

**判决：Accepted**

全部10项验收标准通过。证据脚本结构合格（无恒真、可达 FAIL、cp+md5 还原、无 tee）；独立注入2类反例均导致门控 FAIL 并成功还原回绿；迁移覆盖恰7文件与披露集逐一相符；全部门控实跑与改前基线逐项相等无回归；退出机制经 SYS_EXIT + semihosting 取码且符合 ADR-0020 D7；ISS-147 结案（15条全落 0x00–0x7F）；ISS-120 pre-existing FAIL 未被引入或扩大；未越界。

#### 第 1 轮 architect 提交（WIP）

**档位**：**`WIP:`**（reviewer 未验收、本任务 `状态` = `待验收` ⇒ 非「正常提交」）——**只本地 `commit`，未 `push`**。提交信息 = `WIP: TESTCASES-034t exit-port→SYS_EXIT 全量迁移（45 文件；6 探针逐条披露保留；ISS-147 结案）（待 reviewer 验收）`（**不写死 SHA**：后续 `/complete` 收尾会 squash/amend，SHA 会变）。

**文件集对账**（显式 staging、逐个路径；**未用 `git add -A`**）：

- staging **46** 条 = engineer 声明 **45 条**产品/台账文件 + **本任务书**（`TESTCASES-034t-exit-port迁移.md`）；`git diff --cached --name-only`（46）与 `git status --porcelain -uall`（46）**逐条一致**，无第 47 项、无未跟踪项。
- **漏提 = 0**（无「`git status` 有而 staged 无」者）；**多提 / 越界 = 0**（无「staged 而 `git status` 无」者；唯一非产品项 = 本任务书，属正常）；**`spec/` 交集 = 空**（`git diff --cached --name-only | grep '^spec/'` 无输出）；**`.work/**`、`.dadao/**` 未入库**（`git status`/`git diff --cached` 均无命中，且 `git ls-files` 无 `*.work/`）；**未触 `components/**`、`Makefile`**（staged/status 均无命中）。
- `git diff --cached --stat` = **46 files changed, 959 insertions(+), 433 deletions(-)**。

**例外披露核实（迁移后仍含 exit-port 的 7 文件）**：`grep -rln "0xffff_8000_0000\|exit.port\|exit_port" tests/ tools/`（排除 `__pycache__`/`archive`）**恰返回 7 文件**，与披露集**逐一相符**：`tools/integ/check_interface_alignment.py` + `tools/qemu/min_rom_probe_{006t,008t,009t,010t,012t,013t}.py`。逐条理由已在完成区「遗留问题」+ `issues.yaml` **`ISS-169`** 记录（006t = exit-port 设备测试；009t = OBSOLETE/DO NOT RUN；008t/010t/012t/013t = 退出与手算 PC 相对分支偏移交错）。**不影响 M5 门槛**：迁移面中所有进入 `make` 门控的向量/harness/驱动均已迁 `SYS_EXIT`（engineer 完成区门控全绿）。`issues.yaml`：**`ISS-147`** 已 **closed**（`resolved_by: TESTCASES-034t`）。

**注**：本留痕于**提交之后**追加（architect 标准流程：先提交、再留痕），**未随该 WIP 提交入库**，将由 `/complete` 收尾时一并纳入；本条与「第 1 轮 reviewer 验收」占位条并存（reviewer 尚未验收）。

#### 第 1 轮 architect 提交（正常）

**档位**：**正常提交**（reviewer 判 **`Accepted`** ⇒ 验收完成；`/complete` 收尾完成、本任务 `**状态**` 由 `待验收` 置 **`已验证`**）——**只本地 `commit`，未 `push`**。提交信息 = `TESTCASES-034t exit-port→SYS_EXIT 全量迁移（45 文件；6 探针披露保留；ISS-147 结案）（reviewer Accepted）`（**不写死 SHA**：`push` 时由主会话将该任务本地提交 squash/amend 为单一「已验证」提交，SHA 会变）。

**本次纳入**：上轮 WIP 提交（`WIP: …`）**之后**追加的「第 1 轮 reviewer 验收」全文 + 上轮「architect 提交（WIP）」留痕（二者**均未随 WIP 提交入库**，本次一并纳入）；本任务书 `**状态**` `待验收`→`已验证`；`/complete` 知识沉淀 4 件（`lessons.md` §7.23/§8.17、`changelog.md` 1 行、`milestones.md` M5 段 `✅ TESTCASES-034t 落地`、`MEMORY.md` M5 摘要行）。

**文件集对账**（显式 staging、逐个路径；**未用 `git add -A`**）：

- 入库 = 本任务书 `.tao/tasks/testcases/TESTCASES-034t-exit-port迁移.md` + **4** 个知识文件 `.tao/knowledge/{lessons.md,changelog.md,milestones.md,MEMORY.md}`（`git diff --cached --name-only` = 5 路径）。
- **漏提 = 0**（`git status --porcelain -uall` 仅这 5 个文件，全部 staged）；**多提 / 越界 = 0**；**`spec/` 交集 = 空**（`git diff --cached --name-only -- spec/` 无输出）；**`.work/**`、`.dadao/**` 未入库**（gitignored）；未触 `contracts/**`/`components/**`/`Makefile`；无并行会话改动卷入。

**交叉复核（architect，§2.5）**：reviewer 判决 **`Accepted`** 不过严/不过松/无遗漏；核其**独立注入**（改 `tests/llvm/codegen/expected.yaml` 期望值 `118→119` ⇒ `run_codegen_e2e` **14/15 FAIL**；改 `tests/scripts/codegen_crt0.s` `SYS_EXIT 0x18→0x19` ⇒ **0/15 FAIL**〔`RASUF 0x8B`〕；均 `cp`+md5 还原回绿）**有鉴别力**；核其还原 md5 与当前工作树一致（`expected.yaml` = `a649d07d…`、`codegen_crt0.s` = `730bbf24…`，逐字相符）；核其**未用** `git show <commit>:<path>` 读回（任务书全文仅 F8 一处「禁 `git show`」措辞，无实际调用）。**独立**核（按硬约束**未跑 `make`**，跑各门控底层脚本/校验器）：① 残留 exit-port `grep -rln "0xffff_8000_0000\|exit.port\|exit_port\|EXIT_PORT" tests/ tools/ | grep -v __pycache__ | grep -v archive` **恰 7 文件**（`check_interface_alignment.py` + `min_rom_probe_{006t,008t,009t,010t,012t,013t}.py`），与披露集**逐一相符**，逐条理由核验成立（`006t` 设备测试 / `009t` OBSOLETE / `008t`·`010t`·`012t`·`013t` 退出与手算偏移交错）；② 门控自核 ≥2 项：`validate_codegen_vectors` **PASS(58) rc=0**、`validate_elf_vectors` **PASS(42) rc=0**、`validate_mc_vectors` **73/0 rc=0**、`check_interface_alignment` **85 项全 PASS rc=0**、`check_issues` **39 open/3 closed rc=0**、`check-no-residue` **PASS rc=0**——与改前基线逐项相等；③ `ISS-147` **closed**（`resolved_by: TESTCASES-034t`）且 `expected.yaml` 15 条退出码**全落 `0x00–0x7F`**（枚举 [7,9,9,16,25,41,42,43,43,45,77,108,110,118,121]）；④ `ISS-120` **未扩大**（`006t`/`008t`/`009t`/`010t`/`013t`/`028t` 六探针**改前 base 日志与迁移后 final 日志逐字节相同**）；⑤ `git diff --name-only 783ba9f..HEAD` **46 文件**、`spec/` 交集**空**、未触 `components/**`·`Makefile`；⑥ 工作树无 `*_tmp*`/`*_gate*`/`*.orig`/`*.rej`/`*.preinject` 残留。**复核判决：通过（`Accepted` 维持）**。

**补充发现（供 `/complete` 统一报告）**：
1. **6 探针例外（`ISS-169`）**：`min_rom_probe_{006t,008t,009t,010t,012t,013t}.py` 未随迁 `SYS_EXIT`——**不影响 M5 门槛**（迁移面中所有进入 `make` 门控的向量/harness/驱动均已迁）。**建议**：另立任务（或随 M6）重写这 6 个探针的退出通道（`006t` 若仍测保留的 exit-port 设备则保留；`009t` OBSOLETE 可删；`008t`/`010t`/`012t`/`013t` 按新字长重算手算分支偏移）后，移除本例外与 `check_interface_alignment.py` 的注释例外。
2. **engineer 记录的关键坑（已沉淀 `lessons §7.23`/`§8.17`）**：① semihosting `SYS_EXIT` = **64 位大端内存块** `{0x20026, code}` 且**块指针在 `rb16`**（退出码在**内存块**，非「写寄存器」——初版沿用 exit-port 习惯放 `rb3` ⇒ 全 FAIL）；② harness 须**显式** `-semihosting-config enable=on,target=native`（`native` 非默认）；③ `-d cpu` 的「最后一次 dump」观测陷阱——`SYS_EXIT` 的 `trap` **不在 trap 前切 TB**（异于 exit-port 的 MMIO store 经 `CF_LAST_IO` 切分）⇒ exit 序列须**前置 no-op `jump` 强制 TB 边界**（已在 `046t`/`049t` 应用）；④ **范围计数须脚本枚举勿目测**（`ISS-147` 实为 **7** 条而非初判 5 条，另 `call_multiarg_stack`=171、`ptr_add_offset`=171）。

#### 主会话统一验收报告（`/complete`，2026-10-08）

- **reviewer**：`Accepted`。全门控与**改前逐项相等**（`test-codegen` 15/15、`test-elf` 5/5、`check-lit` 62/62、`check-qemu-semantics` 149/149、`validate-vectors` 155/155、`make check` EXIT=0）；**独立注入 2 类**（改期望值 `118→119` ⇒ 14/15 FAIL；改 `SYS_EXIT` 号 `0x18→0x19` ⇒ 0/15 FAIL）⇒ `cp`+`md5` 还原 ⇒ 回绿；**未用** `git show <commit>:<path>` 读回（`lessons §7.20` 合规）。
- **architect 交叉复核**：**通过**。独立核：**残留 exit-port 恰 7 文件**（`check_interface_alignment.py` + 6 探针）与披露集/`ISS-169` 逐条相符；`validate_codegen_vectors`(58)/`validate_elf_vectors`(42)/`validate_mc_vectors`(73)/`check_interface_alignment`(85) 全 PASS；`ISS-147` 结案且 15 条退出码全落 `0x00–0x7F`；**`ISS-120` 的 6 探针改前/改后日志逐字节相同**（未扩大）；`spec/` 交集空、未触 `components/**`/`Makefile`。
- **交付**：**全量迁移**——`codegen_crt0.s`/`build_test_binary.py`/`run_{codegen,elf}_e2e.py`/`run_qemu_test.py`、4 smoke、7 `.ll`+`expected.yaml`、**16 探针**、文档 + `schema.md` = **45 文件** 由 exit-port 改为经 **`SYS_EXIT`**；harness 显式 `-semihosting-config …target=native`（合规 `ADR-0020 D7`）；**`ISS-147` 结案**（`resolved_by: TESTCASES-034t`）。
- **例外（不影响 M5 门槛）**：**6 个 M1/M2 手写探针**保留 exit-port（`006t` 测保留设备 / `009t` OBSOLETE / `008t/010t/012t/013t` 退出与手算 PC 偏移交错），登记 **`ISS-169`**；建议另立/M6 重写后移除例外。
- **知识沉淀**：`lessons §7.23`（四条实现坑 + 根因）+ **`§8.17`**（停机协议迁移规范）：① `SYS_EXIT` 退出码在 **64 位大端内存块**、块指针 **`rb16`**；② harness 须显式 `target=native`；③ `-d cpu` 观测须前置 no-op `jump` **强制 TB 边界**；④ **范围计数须脚本枚举**（`ISS-147` 实为 7 而非 5）。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
