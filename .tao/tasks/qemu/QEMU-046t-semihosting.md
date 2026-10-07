# QEMU-046t: semihosting（译码层短路 + 共享层复用 + 完整 25 服务 + `SYS_EXIT`）

**模块**：qemu
**项目里程碑**：M5
**依赖**：`QEMU-045t`、`SPEC-114t`
**状态**：待开始

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**（改 tag 判定/错接 bank → 重建 → FAIL → 还原+重建 → 回绿）+ 核 25 服务/共享层未重写 + 判决）
