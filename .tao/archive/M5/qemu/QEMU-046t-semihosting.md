# QEMU-046t: semihosting（译码层短路 + 共享层复用 + 完整 25 服务 + `SYS_EXIT`）

**模块**：qemu
**项目里程碑**：M5
**依赖**：`QEMU-045t`、`SPEC-114t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-114t`（semihosting 调用表正文）+ `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，D1–D8/D14）+ `QEMU-045t`（trap 译码路径）。
  - `spec/SimRISC-11-其它.md`（`trap cfxHA, immu18` —— semihosting 判定基于 `immu18`，**与 `cfxha` 无关**）。
  - `.tao/knowledge/contract-abi.md §4.1`（`rd16–rd31` 数据参数、`rb16–rb31` 地址参数）、`§4.4`（标量返回 `rd31`；指针返回才用 `rb31`，semihosting 不用）。
  - **QEMU 共享层（实测锁定，只读对照/复用）**：`semihosting/arm-compat-semi.c`（`do_common_semihosting(CPUState *cs)`；`nr = common_semi_arg(cs,0)`、`args = common_semi_arg(cs,1)`；**ARM 号值** `OPEN 0x01 … TICKFREQ 0x31`）；`include/semihosting/common-semi.h`（声明）；`target/riscv/common-semi-target.c`（钩子范式：`common_semi_arg`= `gpr[xA0+argno]`、`common_semi_set_ret`= `gpr[xA0]`）；接入点 `target/riscv/tcg/cpu_helper.c`（`RISCV_EXCP_SEMIHOST` → `do_common_semihosting(cs); pc += 4`）。
- **输出**（组件源码改在 `.work/source/qemu`；**导出补丁**）：
  1. **入口判定 + 译码层短路**：`trap cfxHA, immu18` 中 **`immu18[17:16] == 2'b11`** ⇒ semihosting（**与 `cfxha` 无关**）。**QEMU 译码层短路**（与 RISC-V `RISCV_EXCP_SEMIHOST` 同构）：**不进入 cfx 向量**、直接调 `do_common_semihosting(cs)`、**服务后 PC 步进**（`env->pc += 4`）+ 写回返回寄存器（`ADR-0020 D1/D4/D5/D10`）。
     - **与一般 trap 的对照**：一般 trap（`immu18[17:16]≠2'b11`）走 `DADAO-12 §5` 进入向量，见 `QEMU-045t`；本任务只做 semihosting 短路分支。
  2. **`target/dadao/common-semi-target.c` 钩子（按 `n` 选 bank，小适配非重写）**：v5 **三组分离**（`rd`/`rb`/`rf` 各自计数），共享层 `common_semi_arg(cs,n)` 假定"同一组 `a0+n`" ⇒ 实现：
     - `common_semi_arg(cs, 0)` → **`rd16`**（号/标量）；
     - `common_semi_arg(cs, 1)` → **`rb16`**（参数块指针/地址）；
     - `common_semi_set_ret` → **`rd31`**；
     - `is_64bit_semihosting` → 恒真（v5 64 位）；`common_semi_sys_exit_is_extended`、`common_semi_stack_bottom`、`common_semi_has_synccache` 按 v5 语义实现。
  3. **复用 `do_common_semihosting`**（**不重写**共享层）+ 接入内部异常（类比 `RISCV_EXCP_SEMIHOST`）→ `pc += 4`。
  4. **服务表 = 完整 25 个**（含 D2 文件档；**`SYSTEM`、`HEAPINFO` 都做**）：`OPEN 0x01`/`CLOSE 0x02`/`WRITEC 0x03`/`WRITE0 0x04`/`WRITE 0x05`/`READ 0x06`/`READC 0x07`/`ISERROR 0x08`/`ISTTY 0x09`/`SEEK 0x0a`/`FLEN 0x0c`/`TMPNAM 0x0d`/`REMOVE 0x0e`/`RENAME 0x0f`/`CLOCK 0x10`/`TIME 0x11`/`SYSTEM 0x12`/`ERRNO 0x13`/`GET_CMDLINE 0x15`/`HEAPINFO 0x16`/`EXIT 0x18`/`SYNCCACHE 0x19`/`EXIT_EXTENDED 0x20`/`ELAPSED 0x30`/`TICKFREQ 0x31`；`SYSTEM` 的「执行宿主命令」风险为**已知风险**（ADR/spec 已登记）。
  5. **`SYS_EXIT` 替代 `exit port`**（`ADR-0020 D8`）：semihosting `EXIT`/`EXIT_EXTENDED` 使 guest 退出并把退出码传播到 host `$?`（沿用 `ADR-0004 D3`/`ADR-0011` 的**确定性 halt** 机制——写入后 `cpu_loop_exit()` 锁定）。**保留** exit port 机制（`ADR-0004 D3`）直到 `TESTCASES-034t` 全量迁移（本任务**不**删 exit port）。
  6. **host 侧安全**：默认值由 harness/Makefile 的 `-semihosting-config` 给（`target=native|gdb|auto`、`chardev=`、`arg=`）；**建议默认 `gdb`/沙箱**，`native` 显式开（`ADR-0020 D7`）。
  7. **探针**：`tools/qemu/min_rom_probe_046t.py`（或 `.work/evidence/QEMU-046t/`）——判定（tag 命中/不命中分别走 semihosting/一般 trap 两条路）、`n=0→rd16`/`n=1→rb16`/返回 `rd31`、≥1 例每类服务、`SYS_EXIT` 码传播、`SYSTEM`/D2 文件档可调用。
- **约束（硬）**：
  - **只写 `target/dadao/common-semi-target.c`（+ 接入点/异常枚举）**；**不重写**共享层 `semihosting/arm-compat-semi.c`（若必须改共享层，须先报告——属越界）。
  - **不改**一般 trap 路径（`QEMU-045t`）+ cfx 寄存器/异常进入流程（`QEMU-044t`）+ M1–M4 标量/exit port 语义。
  - **补丁纪律（`spec/Process-01`）**：改动**只能**在 `.work/source/qemu`；导出补丁写 `/tmp`、非空 blob；`make check-patch-tree`（含断言⑥）通过；不手改补丁。
  - **重建成本申报**：`make build-qemu`（**5–20 分钟**）；开工前写明预计耗时；受 `JOBS` 限制；失败即停、**禁自动重试**。
  - 临时目录 `/tmp/opencode/QEMU-046t/`；**不提交 git**；复杂命令输出留存 `.work/log/qemu/`（**禁 `tee`**）。
  - **注入/还原纪律**：注入后**还原须含重建**；`cp`+`md5` 对账，**禁 `git checkout`/`git restore`/`git stash`**。

## 验收标准

1. **构建**：`make build-qemu` EXIT=0；给真实输出。
2. **判定 + 短路**：`trap cfx0, immu18`（`immu18[17:16]==2'b11`）⇒ 走 semihosting（**不进入向量**、PC 步进）；`immu18[17:16]≠2'b11` ⇒ 走一般 trap（进入向量，`QEMU-045t`）。给真实探针输出。
3. **钩子 bank**：`n=0`→`rd16`、`n=1`→`rb16`、返回→`rd31`（探针构造并回读校验，≥2 例）。
4. **服务表**：**25 个服务各 ≥1 例**可调用（或至少逐条对每个服务号派发到共享层并返回合理值）；`grep`/探针计数=25；`SYSTEM`/`HEAPINFO`/D2 文件档各 ≥1 例。
5. **`SYS_EXIT`**：`EXIT`（含 `EXIT_EXTENDED`）⇒ host `$?` 等于 semihosting 退出码（给真实输出）；exit port 仍可用（并存）。
6. **端序/位宽**：参数块字段按 64 位 + 大端读取正确（探针含非零参数块用例）。
7. **不回归**：`make check`/`make check-qemu-semantics` EXIT=0；`make test-codegen`（15/15）/`make test-elf`（5/5）EXIT=0；`check-patch-tree` EXIT=0。
8. **一键证据脚本**：`.work/evidence/QEMU-046t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（改 `immu18[17:16]` 判定门限/把 `common_semi_arg(cs,1)` 错接 `rd17` ⇒ 期望 **FAIL** ⇒ 还原 + **重建** ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
9. **无残留**：`git status --untracked-files=all` 仅组件补丁 + 探针 + 本任务书；`.work/source/qemu` worktree clean。

## 完成区

**测试结果**：探针 `tools/qemu/min_rom_probe_046t.py` **32/32 PASS**（`RESULT: PASS`，EXIT=0）；**25 服务号全覆盖**（`service coverage: all 25 service ids exercised`）；一键证据脚本 `.work/evidence/QEMU-046t/run.sh` **`EVIDENCE: PASS` / `SCRIPT_EXIT=0`**（3 反例隔离注入：A 判定门限 / B `common_semi_arg(cs,1)`→rd17 / C `pc += 4`→`+= 8` → 对应用例 FAIL → `cp`+md5 还原 → **重建** → 全绿）；门控 `make check` **EXIT=0**（`check-patch-tree: 2 component(s), 92 patches OK`、`check-qemu-semantics: 149/149 PASS`、`check-no-residue`/`check-spec-readonly` PASS）、`test-codegen` **15/15 EXIT=0**、`test-elf` **5/5 EXIT=0**；回归 `min_rom_probe_{044t,045t,049t}.py` 全 PASS。

**修改文件**（与 `git status --untracked-files=all` 一致；`.work/**` gitignored 不入库）：
- **组件补丁**（`components/qemu/patches/`，qemu **32 → 34** 份）：
  - `target/dadao/common-semi-target.c.patch`（**新增**，非空 blob）——共享层 v5 钩子；
  - `qemu-options.hx.patch`（**新增**）——`-semihosting`/`-semihosting-config` 的 arch mask 增 `QEMU_ARCH_DADAO`；
  - `target/dadao/Kconfig.patch`（改）——`select ARM_COMPATIBLE_SEMIHOSTING if TCG`；
  - `target/dadao/meson.build.patch`（改）——条件编译 `common-semi-target.c`；
  - `target/dadao/cpu.h.patch`（改）——`DADAO_EXCP_SEMIHOST`；
  - `target/dadao/helper.c.patch`（改）——`do_interrupt` 短路 + `helper_cfx_trap` tag 分支注释；
  - `target/dadao/cpu.c.patch`（改）——`dadao_cpu_translate_for_debug` + `SysemuCPUOps` 接线；
  - `target/dadao/insn_trans/trans_ctrl.c.inc.patch`（改）——`immu18[17:16]==2'b11` 译码层短路；
  - `components/qemu/series`（改，字典序）、`components/qemu/changelog.md`（+1 行）。
- `tools/qemu/min_rom_probe_046t.py`（**新增，随产物入库**）。
- `.work/evidence/QEMU-046t/run.sh`（gitignored，非入库）。
- 本任务书（完成区/自审/状态）。

**验收结果**（真实命令输出/rc，日志在 `.work/log/qemu/`）：
1. **构建**：`make build-qemu JOBS=8` **EXIT=0**（改 `Kconfig`/`meson.build` 后实测 **自动触发 meson 重配置** 并重编 1504 targets，随后增量；`.work/log/qemu/QEMU-046t-build{1..4}.log`）。
2. **判定 + 短路**：`semihost_tag_path` PASS — `trap cfx0, immu18=0x30000`（`immu18[17:16]=2'b11`）⇒ **不进入向量**（cfx0 hypv `excp_vector` 已指向 `exit 0xEE` 的 handler；未命中）、`rd31=0x3b9aca00`、进程经 `trap+4` 的 `exit_seq(0x5A)` 退出 ⇒ **EXIT=0x5A**、`trapn:0=0`/`cid:0=0`；`general_trap_path` PASS — `trap cfx0, immu18=0x0123`（≠tag）⇒ `cid:0=CFXTRAP(1)`、`trapn:0=1`、经向量 handler `exit 0x42`；`semihost_cfxha_agnostic` PASS — `trap cfx7`（**reserved** cfxha）带 tag ⇒ 仍被服务（`rd31=1e9`、`exit 0x5E`）⇒ 与 `cfxha` 无关。
3. **钩子 bank**：`bank_num_rd16` PASS — `rd16=TICKFREQ(0x31)`、`rd17=TIME(0x11)` ⇒ `rd31=1000000000`（若读 `rd17` 会返回秒数）；`bank_arg_rb16` PASS — `ISERROR(block@rb16={-1})` 且 `rb17→零块` ⇒ `rd31=1`（若读 `rb17` 会得 0）；`ret_rd31` PASS — `rd31` 承载返回值且 `rd30` 恒 0。
4. **服务表（25/25）**：25 个服务号各 ≥1 例（`svc_open`/`close`/`writec`/`write0`/`write`/`read`/`readc`/`iserror`/`istty`/`seek`/`flen`/`tmpnam`/`remove`/`rename`/`clock`/`time`/`system`/`errno`/`get_cmdline`/`heapinfo`/`exit`/`synccache`/`exit_extended`/`elapsed`/`tickfreq`）全 PASS；`--list` 打印 `distinct service ids covered: 25` / `required service ids: 25`；`SYSTEM`（`exit 7` ⇒ `rd31=0x700`）、`HEAPINFO`（`rd31=0` + 回读参数）、D2 文件档（`OPEN`→`WRITE`/`READ`/`SEEK`/`FLEN`/`ISTTY`/`CLOSE`/`TMPNAM`/`REMOVE`/`RENAME`，含宿主文件真读写真校验）均有效。
5. **`SYS_EXIT`**：`svc_exit` PASS — `block={0x20026, 0x42}` ⇒ host `$? = 0x42`（`exit_seq(0xEE)` 不可达）；`svc_exit_extended` PASS — `block={0x20026, 0x43}` ⇒ `$? = 0x43`；**exit port 并存**：`semihost_tag_path` 等非 EXIT 用例经 exit port 退出、旧探针（044t/045t/049t、codegen/elf）全绿。
6. **端序/位宽**：`iserror_be64` PASS — `block={0x8000000000000001}`（bit63=1）按 **64 位大端**读 ⇒ `rd31=1`（LE/32 位读会得 0）；其余文件档用例参数块字段亦为非零 64 位大端。
7. **不回归**：`make check` **EXIT=0**（`.work/log/qemu/QEMU-046t-check.log`：`check-patch-tree: 2 component(s), 92 patches OK`；`check-qemu-semantics: PASS`〔`Results: 149 total, 149 passed`〕）；`test-codegen` **15/15 EXIT=0**；`test-elf` **5/5 EXIT=0**；`check_patch_tree.py --source-state` ⇒ qemu `count=1 clean=True`。
8. **一键证据脚本**：`.work/evidence/QEMU-046t/run.sh` ⇒ `EVIDENCE: PASS` **SCRIPT_EXIT=0**（`.work/log/qemu/QEMU-046t-evidence.log`）；3 反例隔离注入（每例独立重建、还原间不重建）：A `== 0x3`→`== 0x2` ⇒ `semihost_tag_path`/`svc_tickfreq` **FAIL**（`exit exp=0x5a got=0x87`）；B `rb[DADAO_SEMI_ARG_REG]`→`rd[17]` ⇒ `bank_arg_rb16`/`svc_iserror`/`svc_writec` **FAIL**；C `pc += 4`→`+= 8` ⇒ `semihost_tag_path`/`svc_tickfreq` **FAIL**（`exit exp=0x5a got=0x81`）；每轮 `git diff --name-only` 非空（A: `trans_ctrl.c.inc`；B: `common-semi-target.c`；C: `helper.c`）；`cp` 还原且 **md5 相等**（`trans_ctrl=0b1baaa2… helper=aefabd8f…`）→ **重建** → 32/32 回绿；全程无 `tee`。
9. **无残留**：`git status --untracked-files=all` = 组件补丁（6 改/2 新）+ `components/qemu/series` + `components/qemu/changelog.md` + 探针 `tools/qemu/min_rom_probe_046t.py`（+本任务书）；`.work/source/qemu` worktree **clean**（`--source-state` `count=1 clean=True`）；无 `*.rej`/`*.orig`/`*.preinject` 残留。

**新发现/坑**：
1. **DADAO CPU 缺 debug 地址翻译钩子 ⇒ 共享层读写 guest 内存崩溃（本次补齐）**：`cpu_memory_rw_debug()`（`get_user_*`/`lock_user` 的底层）在 `cpu->cc->sysemu_ops` 未实现 `translate_for_debug` 时回退调用 **NULL** 的 `get_phys_addr_debug` ⇒ **SIGSEGV**（实测 gdb 栈：`cpu_translate_for_debug`→`0x0`）。semihosting 复用共享层即必须补此钩子；已实现 `dadao_cpu_translate_for_debug`（无 MMU、VA=PA，仅暴露 RAM@0/旧 RAM/ROM 已映射区，越界返回 false 使访问干净失败）。
2. **`-semihosting-config` 受 arch mask 门控 ⇒ 必须扩展 `qemu-options.hx`**：`-semihosting`/`-semihosting-config` 的 `DEF(...)` 带 `QEMU_ARCH_*` 掩码，`system/vl.c:2947` 的 `qemu_arch_available()` 会以 `Option not supported for this target` 拒绝未列 arch（DADAO 原不在列）。**此项超出任务书「只写 `target/dadao/common-semi-target.c`（+接入点/异常枚举）」的字面范围，但为 `-semihosting-config`（输出 6）所必需，已披露**。
3. **共享层 `SYS_EXIT` 用 `exit(ret)` 而非 `cpu_loop_exit()`**：任务书措辞「写入后 `cpu_loop_exit()` 锁定」，实测共享层 `arm-compat-semi.c` 的 EXIT/EXIT_EXTENDED 直接 `gdb_exit(ret); exit(ret);`——**退出码忠实传播到 host `$?`**（同一确定性 halt 通道），满足 `ADR-0020 D8`/验收 5；按「不重写共享层」约束**保持原样**。
4. **`WRITEC` 的参数是地址而非内联字符**：共享层 `WRITEC` 以 `common_semi_arg(cs,1)`（=v5 `rb16`）作**字符指针**、长度 1；与 `contract-semihosting §3`「参数寄存器 = 字符指针」一致。`WRITE0` 同（`rb16`=字符串指针）。
5. **观测手法**：semihost `trap` 经 helper 结束其 TB，`-d cpu` 的**下一 TB 起始 dump** 即含 `rd31` 返回；`SYS_EXIT` 直接 `exit()` 不产生后续 dump，故只看 host `$?`。
6. **`SYS_SYSTEM` 返回值 = `system()` 的 wait status**：`exit 7` ⇒ `rd31=0x700`（非 7）；探针据此断言（`svc_system`）。
7. **`common_semi_stack_bottom` 用 `rb1`（`rbsp`）**：`READC`/FLEN(gdb 档) 经 `stack_bottom±off` 的 guest 内存访问；`contract-abi §2.1` 定 `SP=rb1`，故 READC 用例须把 `rb1` 指向可写 RAM（否则 `do_fault`/EFAULT）。

**遗留问题**：
- **`CONFIG_SEMIHOSTING` 开启方式（回报项）**：`target/dadao/Kconfig` 增 `select ARM_COMPATIBLE_SEMIHOSTING if TCG`（`ARM_COMPATIBLE_SEMIHOSTING select SEMIHOSTING`，`semihosting/Kconfig`）⇒ dadao-softmmu 构建启用共享层 `semihosting/arm-compat-semi.c`（实测编入 `libsystem.a`）。**meson 接线**：`target/dadao/meson.build` 以 `when: 'CONFIG_ARM_COMPATIBLE_SEMIHOSTING'` 加入 `common-semi-target.c`；并 **须** 在 `qemu-options.hx` 的 `-semihosting(-config)` arch mask 增 `QEMU_ARCH_DADAO`（见新发现 2），否则 CLI 被拒。改 `Kconfig`/`meson.build` 后 `make build-qemu`（build.ninja 已存在）实测**自动重生成并重编**，**无需** `build-qemu-reconfig`。
- **D7 harness 默认值不在本任务**：共享层默认 `target=AUTO`（有 GDB⇒gdb、否则 native）；本任务**不改** Machine/Makefile，探针**显式** `target=native`（显式开，符合 D7「native 显式开」）。「harness/Makefile 默认给 `-semihosting-config`（建议默认 gdb）」归 `TESTCASES-034t`/`INTEG-020t`。
- **exit port 未删**：按任务书保留（迁移范围=全部，归 `TESTCASES-034t`）；`ISS-147`（exit 码与 fault 区重叠）随迁处置。
- **`SYS_SYSTEM` 已知安全风险**（`ADR-0020 D3/D7`）已登记；探针仅用受控命令 `exit 7`。
- **探针宿主依赖性（非阻塞）**：`svc_system` 断言 `system("exit 7")==0x700`（POSIX wait status）；`svc_clock`/`svc_time` 以 `PRESENT`（非精确值）断言（时钟非确定性）。
- **未改 `spec/`**（本任务按预检结论 5）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：逐行审查全部改动源（`common-semi-target.c`/`Kconfig`/`meson.build`/`cpu.h`/`helper.c`/`cpu.c`/`trans_ctrl.c.inc`/`qemu-options.hx`）+ 探针 `min_rom_probe_046t.py` + 证据脚本 `run.sh`；核对 Spec-first（`Machine-01 §5`、`ADR-0020 D1–D8/D10/D14`、`contract-semihosting`、`contract-abi §2.1/§4`、Arm Semihosting `Release 2.0`）、边界（不改标量/exit port/一般 trap 路径、不重写共享层、不改 `spec/`）、防造假（真实执行、真实输出逐条对齐、`run.sh` 结尾无 `tee`）。

**结论**：逻辑正确、边界受控、共享层零改动（`arm-compat-semi.c` 及 `semihosting/**` 无 diff）。实现期发现 3 处基建缺口（均已当场修复/接线并复验）与 4 处判据/坑（见完成区「新发现」）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 共享层经 `cpu_memory_rw_debug` 访问 guest 内存 ⇒ DADAO 未实现 debug 翻译钩子致 **SIGSEGV**（gdb 栈 `cpu_translate_for_debug`→`0x0`） | ✅已修 | `cpu.c` 新增 `dadao_cpu_translate_for_debug`（VA=PA，仅已映射区）并接入 `SysemuCPUOps.translate_for_debug` | `svc_writec`/`svc_write0`/`svc_read`/`svc_open` 等读/写 guest 内存用例 32/32 PASS |
| F2 `-semihosting-config` 被 `qemu_arch_available` 按 arch mask 拒（DADAO 不在列） | ✅已修 | `qemu-options.hx` 两处 `DEF(...)` arch mask 增 `QEMU_ARCH_DADAO` | `-semihosting-config enable=on,target=native,...` 实测可用（探针全绿） |
| F3 `cpu.c` 初版 `translate_for_debug` 含 `addr >= DADAO_RAM0_BASE`（=0）恒真分支，`-Wtype-limits` 告警 | ✅已修 | 改为 `addr < DADAO_RAM0_BASE + DADAO_RAM0_SIZE` | 重建 `warning` 计数 **0**；`svc_read`（RAM@0 越界判 false）PASS |
| F4 探针初版 READC 未设 `rb1`、`common_semi_stack_bottom=0` ⇒ buffer 越界 ⇒ EFAULT | ✅已修 | READC 用例 `set_addr(1, RAM_BASE+K_BUF+1)` | `svc_readc` PASS（`rd31=0x51`='Q'） |
| F5 探针初版文件档 SEEK 复用 READ 块 ⇒ offset 误读成大值 ⇒ lseek 失败 | ✅已修 | SEEK 用独立 `{handle, offset}` 块 | `svc_seek` PASS（`rd31=0`） |
| F6 断言可达 FAIL（反例门控）/「与 cfxha 无关」缺正向证据 | ✅已证/已补 | `run.sh` 3 类隔离注入；新增 `semihost_cfxha_agnostic`（reserved cfxha7 带 tag 仍服务） | 注入 A/B/C ⇒ 对应用例 **EXIT=1**；还原+重建 ⇒ 32/32 回绿（见完成区 8） |

**状态**：无未修 finding ⇒ 置「待验收」，返回主会话 `/complete`。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查范围**：证据脚本审核 + 重跑 + 独立注入 + 验收 1–9 逐条 + 越界披露 + 补丁规范 + changelog 核对

---

##### 1. 证据脚本审核（`.work/evidence/QEMU-046t/run.sh`）

**结构**：`set -u`；`fail` 变量追踪失败；`rc=$?` 捕获退出码（无 `tee`）；5 段（构建→探针→注入 A/B/C→恢复+重建→结果）。

**可达 FAIL 路径**：
- 注入 A（`== 0x3`→`== 0x2`）：tag 不命中 ⇒ semihosting 不激活 ⇒ `semihost_tag_path`/`svc_tickfreq` 探针期望值与实际不一致 → **FAIL** ✅
- 注入 B（`rb[DADAO_SEMI_ARG_REG]`→`rd[17]`）：参数块指针从错误寄存器读取 ⇒ `bank_arg_rb16`/`svc_iserror`/`svc_writec` 读到错误值 → **FAIL** ✅
- 注入 C（`pc += 4`→`pc += 8`）：PC 步进错误 ⇒ 返回落到错误指令 ⇒ `semihost_tag_path`/`svc_tickfreq` exit 码不一致 → **FAIL** ✅

**3 轮隔离理由**：A 掩蔽整个 semihosting 入口（`immu18[17:16]` 条件不再匹配），若与 B/C 合并则 B/C 的效果不可观测（semihosting 不会被触发，钩子 bank 和 pc 步进均不会被执行）。理由成立 ✅

**md5 对账**：注入前记录 3 个 md5 → 恢复后逐一对比相等 ✅
**注入有效性**：每轮 `git diff --name-only` 非空（A: `trans_ctrl.c.inc`；B: `common-semi-target.c`；C: `helper.c`）✅
**还原含重建**：恢复后执行 `build restore` → 重建 → 探针回绿 ✅
**结尾**：`exit 0`（PASS）/ `exit 1`（FAIL），无 `tee` ✅

**结论**：脚本合格，不需修改。

---

##### 2. 重跑证据脚本（真实输出）

```
QEMU-046t evidence: semihosting short-circuit + hooks + 25 services

----- [1/5] make build-qemu -----
make build-qemu EXIT=0

----- [2/5] probe (all cases) -----
[PASS] semihost_tag_path    immu18[17:16]==2'b11 => semihosting, PC+=4, no vector -> ok
[PASS] semihost_cfxha_agnostic semihosting tag is honoured with a reserved cfxha (7) -> ok
[PASS] general_trap_path    immu18[17:16]!=2'b11 => CFXTRAP enters vector -> ok
[PASS] bank_num_rd16        common_semi_arg(cs,0) reads rd16 (rd17 decorrelated) -> ok
[PASS] bank_arg_rb16        common_semi_arg(cs,1) reads rb16 (rb17 decorrelated) -> ok
[PASS] ret_rd31             semihosting return is written to rd31 only -> ok
[PASS] svc_open ... svc_tickfreq (25 svc) ... iserror_be64
[PASS] service coverage: all 25 service ids exercised
RESULT: PASS
probe(all) EXIT=0

----- [3/5] injection self-check (A/B/C, isolated rounds) -----
pre-inject md5: trans_ctrl=0b1baaa209577f64d1f92bf5c83f0965 common-semi-target=2c2f1b214b280e8d08f69a106008ce33 helper=aefabd8fcc501d5263d3a8518643882d

-- injection A --
A applied (1 site); git diff: target/dadao/insn_trans/trans_ctrl.c.inc
rebuild(after A) EXIT=0
[FAIL] semihost_tag_path -> exit exp=0x5a got=0x87; rd31 exp=0x3b9aca00 got=0x0
[FAIL] svc_tickfreq -> exit exp=0x76 got=0x87; rd31 exp=0x3b9aca00 got=0x0

-- injection B --
B applied (1 site); git diff: target/dadao/common-semi-target.c
rebuild(after B) EXIT=0
[FAIL] bank_arg_rb16 -> rd31 exp=0x1 got=0x0
[FAIL] svc_iserror -> rd31 exp=0x1 got=0x0
[FAIL] svc_writec -> out exp=b'Y' got=b'\x00'

-- injection C --
C applied (1 site); git diff: target/dadao/helper.c
rebuild(after C) EXIT=0
[FAIL] semihost_tag_path -> exit exp=0x5a got=0x81
[FAIL] svc_tickfreq -> exit exp=0x76 got=0x81

----- [4/5] restore + rebuild + re-green -----
post-restore md5: trans_ctrl=0b1baaa209577f64d1f92bf5c83f0965 common-semi-target=2c2f1b214b280e8d08f69a106008ce33 helper=aefabd8fcc501d5263d3a8518643882d
rebuild(after restore) EXIT=0
probe(all, post-restore): 32/32 PASS, EXIT=0

----- [5/5] result ------
EVIDENCE: PASS
```

**脚本退出码**：`SCRIPT_EXIT=0` ✅

---

##### 3. 独立注入（reviewer 自行执行）

**注入方式**：改 `trans_ctrl.c.inc` 第 421 行 `== 0x3` → `== 0x0`（与 engineer 的 `== 0x2` 不同，仍属同类阈值改动但值不同）。

**注入前快照**：
```
md5: trans_ctrl=0b1baaa209577f64d1f92bf5c83f0965
     common-semi-target=2c2f1b214b280e8d08f69a106008ce33
     helper=aefabd8fcc501d5263d3a8518643882d
git status: clean
```

**注入后**：
```
git -C .work/source/qemu diff --name-only: target/dadao/insn_trans/trans_ctrl.c.inc
grep: 第 421 行 == 0x0 (REVIEWER INJECTED: was 0x3)
```

**重建**：`make build-qemu JOBS=8` → `BUILD_EXIT=0`（增量 21 targets）

**探针（注入后）**：
```
[FAIL] semihost_tag_path -> exit exp=0x5a got=0x87; rd31 exp=0x3b9aca00 got=0x0
PROBE_EXIT=1
[FAIL] svc_tickfreq -> exit exp=0x76 got=0x87; rd31 exp=0x3b9aca00 got=0x0
PROBE_EXIT=1
```

**还原**：`cp /tmp/opencode/QEMU-046t-review/trans_ctrl.c.inc.preinject .work/source/qemu/.../trans_ctrl.c.inc`
```
还原后 md5: 0b1baaa209577f64d1f92bf5c83f0965 ✓ 与注入前一致
```

**重建（还原后）**：`make build-qemu JOBS=8` → `BUILD_EXIT=0`

**探针（还原后）**：`32/32 PASS, PROBE_EXIT=0` ✅

**git status（结束后）**：`clean`（无残留）✅

---

##### 4. 验收 1–9 逐条

| # | 验收项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 构建 `make build-qemu` EXIT=0 | ✅ | 证据脚本 + 独立注入重建均 EXIT=0 |
| 2 | 判定 + 短路：tag 命中→不进向量+PC 步进；≠tag→进向量；与 cfxha 无关 | ✅ | `semihost_tag_path` PASS（excp_vector 指向 `exit 0xEE` 的 handler，未被调用）；`general_trap_path` PASS（`cid:0=CFXTRAP(1)`）；`semihost_cfxha_agnostic` PASS（reserved cfxha7 带 tag 仍服务，`rd31=1e9`） |
| 3 | 钩子 bank：n=0→rd16、n=1→rb16、返回 rd31 | ✅ | `bank_num_rd16` PASS（rd16=TICKFREQ, rd17=TIME ⇒ 若误读 rd17 则返回秒数而非1e9）；`bank_arg_rb16` PASS（rb16 有数据, rb17→零块 ⇒ 若误读 rb17 则 ISERROR 得 0）；`ret_rd31` PASS（rd31 承载返回值，rd30 恒 0） |
| 4 | 服务表 25/25 | ✅ | `--list` 输出 `distinct service ids covered: 25 / required: 25`；25 个 svc_* 用例 + iserror_be64 + 结构用例 = 32 个探针用例全 PASS；SYSTEM（`system("exit 7") ⇒ rd31=0x700`）；HEAPINFO（`rd31=0`）；D2 文件档（OPEN→WRITE/READ/SEEK/FLEN/ISTTY/CLOSE/TMPNAM/REMOVE/RENAME，真宿主文件读写校验） |
| 5 | SYS_EXIT：EXIT/EXIT_EXTENDED ⇒ host $? = 退出码；exit port 并存 | ✅ | `svc_exit` PASS（block={0x20026, 0x42} ⇒ $?=0x42）；`svc_exit_extended` PASS（block={0x20026, 0x43} ⇒ $?=0x43）；exit port 仍可用（044t/045t/049t 回归探针全绿） |
| 6 | 端序/位宽：64 位大端 | ✅ | `iserror_be64` PASS（block={0x8000000000000001}，bit63=1，64 位大端读 ⇒ rd31=1） |
| 7 | 不回归 | ✅ | `make check` EXIT=0（check-patch-tree 92 patches OK, check-qemu-semantics 149/149 PASS）；`test-codegen` 15/15 EXIT=0；`test-elf` 5/5 EXIT=0；`min_rom_probe_{044t,045t,049t}` 全 PASS |
| 8 | 一键证据脚本 | ✅ | `run.sh` 合格（见上 §1）；重跑 EXIT=0（见上 §2）；独立注入验证通过（见上 §3） |
| 9 | 无残留 | ✅ | `git status --untracked-files=all` = 干净（仅已提交文件）；`.work/source/qemu` clean（`--source-state count=1 clean=True`） |

---

##### 5. 越界披露可接受性判定

| 越界项 | 必要性论证 | 可接受性 |
|--------|-----------|---------|
| `qemu-options.hx.patch`：arch mask 增 `QEMU_ARCH_DADAO` | `-semihosting`/`-semihosting-config` 的 `DEF(...)` 带 `QEMU_ARCH_*` 掩码，`system/vl.c` 的 `qemu_arch_available()` 按此门控。DADAO 原不在列 ⇒ CLI 直接拒绝（`Option not supported for this target`）。无此补丁则验收 5（`-semihosting-config` 启用）不可达。**必要接线** ✅ | **可接受** |
| `cpu.c.patch`：`dadao_cpu_translate_for_debug` | 共享层 `do_common_semihosting` 经 `cpu_memory_rw_debug()` 读写 guest 内存，该路径调 `cpu->cc->sysemu_ops->translate_for_debug`；未实现时回退 NULL `get_phys_addr_debug` ⇒ SIGSEGV。无此钩子则 WRITEC/WRITE0/READ/OPEN 等全部崩溃。**必要接线** ✅ | **可接受** |

两项均属 semihosting 共享层复用的**最小必要接线**，不改一般 trap 路径、不改标量/exit port 语义、不重写共享层。与任务书约束「只写 `common-semi-target.c`（+ 接入点/异常枚举）」的精神一致（接入点包括 Kconfig/meson/arch 接线）。

---

##### 6. 补丁集与探针

- `check-patch-tree`：**92 patches OK**，EXIT=0 ✅
- 新增补丁 2 份（`common-semi-target.c.patch` 3000 字节、`qemu-options.hx.patch` 1485 字节）：非空 blob ✅
- `series` 字典序正确 ✅
- `changelog.md` 有 QEMU-046t 条目 ✅
- `tools/qemu/min_rom_probe_046t.py` 已入库 ✅
- `.work/source/qemu` clean（`--source-state count=1 clean=True`）✅

---

##### 7. 文件集对账

- `git diff --name-only e0f2632..HEAD` = 12 文件（与任务书声明一致）✅
- `spec/` 交集：空 ✅
- `.work/**`：未入库（gitignored）✅

---

##### 8. changelog 用例计数核实

- `components/qemu/changelog.md` 记「**31 用例**」
- `min_rom_probe_046t.py --list` 实际输出 **32 条**（25 svc + semihost_tag_path + semihost_cfxha_agnostic + general_trap_path + bank_num_rd16 + bank_arg_rb16 + ret_rd31 + iserror_be64 = 32）
- `probe(all)` 实跑 **32/32 PASS**
- **差异原因**：changelog 遗漏了 `iserror_be64`（端序/位宽验证用例），该用例覆盖验收 6（64 位大端参数块读取），属于有效用例。
- **结论**：以实跑 32 为准。changelog 计数措辞为**非阻塞**差异，收尾时可修正。

---

##### 判决

**Accepted**

全部验收项通过：证据脚本合格（3 轮注入均可达 FAIL、还原含重建、md5 对账一致）；重跑 32/32 PASS / EVIDENCE: PASS / EXIT=0；独立注入（改 tag 阈值 `0x3`→`0x0`）确认 FAIL→还原+重建→回绿；验收 1–9 全绿；越界披露 2 项均为必要接线且可接受；补丁规范合规；门控全绿（check 92 patches / semantics 149/149 / codegen 15/15 / elf 5/5 / 回归 044t/045t/049t 全 PASS）。changelog 计数 31 vs 实际 32 为非阻塞差异，收尾修正。

#### 第 1 轮 architect 提交（WIP）

**档位**：`WIP:`（reviewer 尚未验收，工程返回态 ⇒ 非正常提交）。

**文件集对账**（显式 staging，逐个路径，未用 `git add -A`）：
- `git diff --cached --name-only` = 12 项，与任务书「修改文件」声明**逐条一致**：组件补丁 2 新（`qemu-options.hx.patch`、`target/dadao/common-semi-target.c.patch`）+ 6 改（`Kconfig`/`meson.build`/`cpu.h`/`helper.c`/`cpu.c`/`insn_trans/trans_ctrl.c.inc`）+ `components/qemu/series` + `components/qemu/changelog.md` + 探针 `tools/qemu/min_rom_probe_046t.py` + 本任务书。
- **漏提**：无。**多提**：无。**越界**：无。
- **`spec/` 交集**：空（`git status --porcelain -uall | grep spec/` 无输出）。
- **`.work/**`**：未入库（`.gitignore:2:.work/` 命中；`git status` 无 `.work/` 条目）。
- 工作区无未 staged 残留。

**越界披露核实**（engineer 披露的 2 项超任务书字面范围的必要接线；**如实列明、未裁剪**，供 reviewer 判定；已给真实补丁输出）：
1. **`qemu-options.hx.patch`（新增）**：`-semihosting` 与 `-semihosting-config` 两处 `DEF(...)` arch mask 增 `QEMU_ARCH_DADAO`。**必要性依据**：`DEF` 的 `QEMU_ARCH_*` 掩码经 `system/vl.c` 的 `qemu_arch_available()` 门控，DADAO 原不在列 ⇒ CLI 被拒（`Option not supported for this target`），则任务书输出 6/验收 5（`-semihosting-config` 启用）不可达。真实 diff 已确认：两处 mask 均增 `QEMU_ARCH_DADAO`（见 `git show`/`cat` 输出）。
2. **`cpu.c.patch`（改）**：新增 `dadao_cpu_translate_for_debug`（无 MMU，VA=PA，仅暴露已映射区，越界返回 `false`）并接入 `SysemuCPUOps.translate_for_debug`。**必要性依据**：共享层 `do_common_semihosting` 经 `cpu_memory_rw_debug()` 读写 guest 内存，该路径在 `sysemu_ops` 未实现 `translate_for_debug` 时回退调用 NULL 的 `get_phys_addr_debug` ⇒ **SIGSEGV**（engineer gdb 栈 `cpu_translate_for_debug`→`0x0`）；semihosting 复用共享层即必须补此钩子，否则 WRITEC/WRITE0/READ/OPEN 等读写 guest 内存的服务崩溃。真实补丁已确认 `dadao_sysemu_ops = { .has_work, .translate_for_debug }` 且函数体存在。

**提交**：`WIP: QEMU-046t semihosting（译码层短路 + 共享层复用 + 25 服务 + SYS_EXIT）（待 reviewer 验收）`（**只 commit 不 push**；SHA 不写死）。

**非阻塞观察**：`components/qemu/changelog.md` 该行记「31 用例」，而完成区/探针报「32/32」——计数措辞不一致，不影响提交与验收（探针实跑为准），留待 reviewer/收尾核对。

#### 第 1 轮 architect 提交（正常）

**档位**：**正常提交**（reviewer 第 1 轮判决 = **`Accepted`**；非 `WIP:`）。

**A. 小修正（reviewer 指出的非阻塞差异）**：`components/qemu/changelog.md` 该条「**31** 用例」→「**32** 用例」（漏计端序/位宽用例 `iserror_be64`；`tools/qemu/min_rom_probe_046t.py --list` 实测 **32** 用例，以实跑为准）。**只改这一处计数措辞**，其余文字未动。

**文件集对账**（显式 staging，逐个路径，**未用 `git add -A`**）：
- `git diff --cached --name-only` = **14** 项：
  - 本任务书（完成区/自审/reviewer 验收/本记录）；
  - 组件补丁 2 新（`qemu-options.hx.patch`、`target/dadao/common-semi-target.c.patch`）+ 6 改（`Kconfig`/`meson.build`/`cpu.h`/`helper.c`/`cpu.c`/`insn_trans/trans_ctrl.c.inc`）；
  - `components/qemu/series`、`components/qemu/changelog.md`（含 A 修正）；
  - 探针 `tools/qemu/min_rom_probe_046t.py`（**随产物入库**）；
  - 知识沉淀 4 件：`.tao/knowledge/lessons.md`（§7.19/§8.13）、`.tao/knowledge/changelog.md`（+1 行）、`.tao/knowledge/milestones.md`（M5 段 QEMU-046t 块）、`.tao/knowledge/MEMORY.md`（M5 摘要行）。
- **漏提**：无。**多提**：无。**越界**：无（12 个产品文件与任务书「修改文件」声明**逐条一致**；4 个台账文件为收尾知识沉淀）。
- **`spec/` 交集**：**空**（`git diff --cached --name-only | grep '^spec/'` 无输出）。
- **`.work/**`**：未入库（`.gitignore` 命中；`git status` 无 `.work/` 条目）。

**独立核验（交叉复核）**：reviewer 判决**不过严/不过松**；独立注入（`trans_ctrl.c.inc` tag 阈值 `0x3`→`0x0` ⇒ `semihost_tag_path`/`svc_tickfreq` FAIL ⇒ `cp`+md5 还原 ⇒ **重建** ⇒ 32/32）**有鉴别力、还原含重建**；核心语义独立核实——tag 门限 `((immu18>>16)&0x3)==0x3`（`trans_ctrl.c.inc:421`）、钩子 bank 逐条对 `ADR-0020 D2/D14`（`common_semi_arg(0)=rd[16]`/`(1)=rb[16]`/`set_ret=rd[31]`）、32 用例计数、25 服务表（`SVC_TABLE`）、共享层 `semihosting/**` **零 diff**、`TARGET_BIG_ENDIAN=1` 证 64 位大端、`check-patch-tree` **92 patches**、`.work/source/qemu` clean（`--source-state count=1 clean=True`、三文件 md5 与 reviewer 还原态一致）、`git diff e0f2632..29f528d` **12 文件·`spec/` 交集空**；越界披露 2 项确属**最小必要接线**。

**提交**：`QEMU-046t semihosting（译码层短路 + 共享层复用 + 25 服务 + SYS_EXIT）（reviewer Accepted）`（**只 commit 不 push**；SHA 不写死）。

#### 主会话统一验收报告（`/complete`，2026-10-08）

- **reviewer**：`Accepted`。证据脚本重跑 **`EVIDENCE: PASS`**（探针 **32/32**）；3 轮注入（判定门限 / `common_semi_arg(cs,1)` 错接 `rd17` / `pc += 4` 改）各自 FAIL ⇒ `cp`+`md5` 还原 ⇒ **重建** ⇒ 回绿（分 3 轮之由：A 掩蔽入口 ⇒ B/C 不可观测，理由成立）；**独立注入**（tag 阈值 `0x3`→`0x0`）⇒ `semihost_tag_path`/`svc_tickfreq` **FAIL** ⇒ 还原 ⇒ 重建 ⇒ 32/32。
- **architect 交叉复核**：**通过**。独立核：`trans_ctrl.c.inc` 门限 `((immu18>>16)&0x3)==0x3`；钩子 `arg(0)=rd[16]`/`arg(1)=rb[16]`/`set_ret=rd[31]`/`is_64bit` 恒真/`stack_bottom=rb1`；`helper.c` 的 `DADAO_EXCP_SEMIHOST` ⇒ `do_common_semihosting(cs); pc += 4;`（**不进向量**）；`SVC_TABLE` **25** 项、`@case` **32**；**共享层零改动**（`semihosting/` diff 空）；`TARGET_BIG_ENDIAN=1` ⇒ 参数块按大端 64 位读；`check-patch-tree` **92 patches**；`.work/source/qemu` clean；`spec/` 交集空。
- **交付（M5 核心）**：**译码层短路**（`immu18[17:16]==2'b11` ⇒ 不进入向量 + PC 步进）+ **共享层复用**（`do_common_semihosting`，**不重写**）+ **`common-semi-target.c` 钩子（按 `n` 选 bank）** + **完整 25 服务**（含 `SYSTEM`/`HEAPINFO`/D2 文件档，均真校验）+ **`SYS_EXIT` 替代 exit port（码传 host `$?`）且 exit port 并存**；探针 `tools/qemu/min_rom_probe_046t.py` **随产物入库**。
- **越界披露（判为必要接线、可接受）**：① `qemu-options.hx` 的 `-semihosting(-config)` arch mask 增 `QEMU_ARCH_DADAO`（否则 CLI 被拒）；② `cpu.c` 新增 `dadao_cpu_translate_for_debug` 接入 `SysemuCPUOps`（共享层经 `cpu_memory_rw_debug` 读 guest 内存，缺则 **SIGSEGV**）。⇒ 已沉淀 `lessons §7.19`/`§8.13`（**复用上游共享层须列全接入点清单**）。
- **小修正**：`components/qemu/changelog.md` 用例计数 **31→32**（漏计 `iserror_be64`），随收尾提交闭合。
- **遗留（已登记）**：`D7` harness 默认（`target=gdb`/沙箱）归 `TESTCASES-034t`/`INTEG-020t`；**exit port 保留、迁移全量归 `TESTCASES-034t`**；`SYS_SYSTEM` 的执行宿主命令风险为 `ADR-0020 D3/D7` 已登记**已知风险**。
- **收尾检查**：`make check`（含 `check-patch-tree` 92、`check-qemu-semantics` 149/149）/`test-codegen` 15/15/`test-elf` 5/5 EXIT=0；`min_rom_probe_{044t,045t,049t}` 仍 PASS；`git status --porcelain -uall` 干净。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
