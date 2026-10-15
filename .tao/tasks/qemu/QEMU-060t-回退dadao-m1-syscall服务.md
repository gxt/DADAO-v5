# QEMU-060t: `dadao-m1` syscall 服务回退（删 `SYS_UMON_SYSCALL` 服务，恢复 semihosting-only）

**模块**：qemu
**项目里程碑**：M8
**依赖**：`INFRA-082t`（`已验证`；**本任务 = 回退其阶段 A1/B 的 QEMU 侧服务**——其任务书**保留**、只追加指针，`**状态**` 不改）；`TESTCASES-045t`（`已验证`；其 runner 在服务撤回后**不再可跑** ⇒ 本任务按「连带面」最小处置）；`ADR-0020`（`D10` 两条 trap 路由口径）；`ADR-0025 D2`（无内核）；`.tao/contracts/contract-syscall.md`（**保留不动**）；`spec/DADAO-22-SBI §2`（`umon`/`jmon` 模型，**只读**）；`ISS-210`（`install-host` 纪律：改组件输入后安装根须同步，否则门控读旧二进制**假绿**）
**状态**：待开始

> **模块判定（architect，2026-10-15）**：归 **`qemu`** 而非 `infra` —— 本任务的**实质改动与判据全在 qemu 面**：① 改 `components/qemu/patches/target/dadao/helper.c.patch`（组件补丁树）；② 删 `tools/qemu/min_rom_probe_082t.py`（`tools/<模块>/` 落点约定 ⇒ qemu 面）；③ 重建 QEMU + `install-host`；④ 验收主判据 = `check-qemu-semantics` **149/149**。infra 侧只余**连带清理**（`tools/infra/test_musl_static.py` 删除、`components/musl/README.md` 一句指代），可并入同一 engineer 范围。

## 执行环境
**执行环境**：本地

## 立项来源（用户裁定原话，原样引录）
- 用户裁定（2026-10-15，渠道 = 经主会话问答）：
  - 「**我不需要在dadao-m1上实现另外一套syscall的模拟，没有意义！！！从一开始就没有意义！！！**」
  - 「**1、删；2、P1/P2/P3/P4解释一下，我已经不记得了**」（第 1 项 = 撤掉 `dadao-m1` 上的 syscall 服务 ✓）
- 落纸链路：`TESTCASES-045t`「§收尾裁定与范围重定义」第 4 项（服务回退「实施待落任务」）⇒ `milestones.md`「M8 任务链」原 **【待实施】ⓑ** ⇒ **本任务**（该待办已作废 ✗，改指本册）。

## 目标
把 `dadao-m1` 机器恢复到 **A1 之前的 semihosting-only 两条路由**：① 一般 `trap`（`immu18[17:16] != 2'b11`）⇒ 进 cfx 向量；② semihosting 短路（`immu18[17:16] == 2'b11`）⇒ 译码层 `DADAO_EXCP_SEMIHOST`（`ADR-0020 D10`）。**不引入**任何替代服务；**运行验证改由 `P3`（`qemu-user`）承担**。

## 现场事实（architect 预核，2026-10-15；执行时须复核）

### ① 基线判定（**关键**；用户给的候选含一枚**不可用**项，已现场判 ✗）
| 候选 commit | `components/qemu/patches/target/dadao/helper.c.patch` md5 | 判定 |
| --- | --- | --- |
| `0986dc9^` = **`761dfa3`**（= A1 的直接父） | **`2b1665e99ed4736fc6579c386a3850f1`** | **✓ 正确基线** |
| `61a497e`（`INFRA-071t`） | `2b1665e99ed4736fc6579c386a3850f1` | ✓ 同值（旁证） |
| `0994699^` / `0994699`（A2+A3） | `11f764c15d1e67fcfd5a340fdf04d33d` | **✗ 不可用**（该版本**已含**服务）；现场判据 = `git diff 0994699 61a497e -- <path>` = `+3 −241` |
> 基线副作用：`761dfa3` 版本里 `grep -c umon` = **1**，唯一命中是既有注释「inside the umon segment (cfxha 0), which now holds no RAM => illegal」（**非**服务代码）⇒ 勿以「`umon` 计数 = 0」作判据。

### ② 须删的三组 hunk（现场清单 = `git diff 61a497e 7255af8 -- <path>`）
1. `@@ -1,9 +1,9 @@`：wrapper 头（`index 0000000..41e7f64` / `@@ -0,0 +1,992 @@` 行数）——随 ② 一并回退；
2. `@@ -845,11 +845,259 @@`：**`umon` 服务段**（说明注释块 / `DADAO_NR_{write,writev,exit,exit_group,set_tid_address}` 宏 / `umon_set_ret`·`umon_set_errno` / `umon_host_write`·`umon_host_fd` / `umon_sys_write`·`umon_sys_writev`·`umon_sys_set_tid_address` / `umon_serve_syscall` / `is_umon_user_syscall`）；
3. `@@ -882,6 +1130,22 @@`：`helper_cfx_trap` 内的接管分支（`if (is_umon_user_syscall(...)) { … }` + 相关注释改动）。

### ③ 现况（`HEAD` 侧）
- 本文件现内容 md5 = `b8565adac3306328b483e8ee0b7e8631`（== `7255af8` 版本）；A1 提交 = `0986dc9`、B 提交 = `7255af8`。
- `series` **36 项**（删 hunk **不改**项数）。
- 仅为该服务存在、将删的两个文件：`tools/qemu/min_rom_probe_082t.py`、`tools/infra/test_musl_static.py`。**调用方复核（现场 `git grep`）**：无 Makefile / 门控 / 其它脚本调用 ⇒ 删之**不动**任何门控输入。
- **不受影响（现场已核）**：`tools/infra/build_musl.py`（`make build-musl`）smoke 仅「编译 → 链接 → ELF 结构校验」，**不跑 QEMU** ⇒ 依赖服务者**只有** `tools/testcases/run_suite.py`（on-demand、刻意不入 L1/L2/L3）。

## 范围（做项）
1. **还原 `helper.c.patch` 到 `761dfa3` 基线**（删上列三组 hunk ⇒ semihosting-only 两条路由）。
   - 手段自选：**手工删 hunk** 或以 `/tmp/opencode/QEMU-060t/` 内的反向 diff `git apply`（`git diff 7255af8 761dfa3 -- <path>` 生成，**写在 `/tmp`、不入库**）。
   - 判据：`git diff 761dfa3 -- components/qemu/patches/target/dadao/helper.c.patch` **空** 且 `md5sum` = `2b1665e99ed4736fc6579c386a3850f1`。
2. **删** `tools/qemu/min_rom_probe_082t.py`、`tools/infra/test_musl_static.py`（`git rm`）。删前现场复核无其它调用方（`git grep -n <名> -- .` 仅命中 `INFRA-082t` 任务书与本文件自身 ⇒ 存量引用留给第 5 项处理）。
3. **连带面（必做，显式处置、不静默）**：
   - a. `tools/testcases/run_suite.py`（`TESTCASES-045t` 产物）：**加显式边界声明 + 硬失败**——服务撤回后其 `-M dadao-m1`（path B）路径**不再可跑**；在 `main()` 入口以明确信息 + 非零 rc 退出（提示「`dadao-m1` 的 syscall 服务已按用户 2026-10-15 裁定撤回；运行验证改由 `P3`（`qemu-user`）承担」），并在模块 docstring 首部写明同一句。**不重写**为 `qemu-user` 版（= `P3` 任务）。
   - b. `components/musl/README.md`：把「该表必须与**服务方**（`dadao-m1` 的 `umon` 服务，`INFRA-082t` 阶段 A1）逐槽一致」的**服务方指代**改为指向 `P3`（`qemu-user`）；一句话、**只改指代**，不动 syscall stub 口径（号 `rd15`/沿用 RISC-V 编号/`rd8` 返回/errno 负值）。
   - c. 若 `git grep` 另发现悬挂引用（如文档/脚本指向两文件）⇒ **逐条列出并最小修**，或如实登记到完成区「遗留问题」（**不留静默悬挂**）。
4. **保留不动 ✗**：`components/musl/**`（**16 补丁**）/ `make build-musl` + `tools/infra/build_musl.py` / `tools/testcases/run_suite.py` 的**度量口径与统计**（只加边界声明，不删主体）/ `.tao/contracts/contract-syscall.md` / `spec/**` / `manifests/**` / `INFRA-082t` 任务书**正文**。
5. **`INFRA-082t` 任务书追加指针**（**只追加**、`**状态**` 与既有完成区/审阅记录**不改** ✗）：文末新增一节，写明「A1/B 的 `SYS_UMON_SYSCALL` 服务与裸机 E2E 已由用户 2026-10-15 裁定撤回（执行 = `QEMU-060t`）；运行验证改由 `P3`（`qemu-user`）承担；musl 补丁集 / `make build-musl` / syscall 契约**保留**」。
6. **`ISS-221` 撤销**：`.tao/knowledge/issues.yaml` ⇒ `ISS-221` 置 `status: closed` + `resolved_by: QEMU-060t` + `notes` **只追加**关闭段（「服务已撤回 ⇒ `spec/Machine-01 §4.3` 的规范缺口**不存在**（第三条路由不再存在）；`spec/` 全程**零改动**、无需授权」）。若判「关 issue」属 architect `/complete` 职责 ⇒ **至少在完成区给出可直接套用的 YAML 片段**，不得静默略过。
7. **重建 + 安装（编译输入已变）**：`make build-qemu` rc=0；`make install-host` rc=0（`JOBS=8`、**禁** `-j$(nproc)`；照 `AGENTS.md`「改 MC（`.td`/InstrInfo）后必须补跑 `make install-host`」**同类纪律**——安装根与构建树须同步，否则 `check-qemu-semantics` 读**旧二进制**得**假绿**〔`ISS-210`〕）。**启动前申报预计耗时**；单次只跑一个长任务、日志落 `.work/log/qemu/`。
8. **一键证据脚本** `.work/evidence/<任务ID>/run.sh`（含反例注入节，见验收 5）。

## 不属本任务 ✗
- 不在 `dadao-m1` 上**另建**任何 syscall 服务或替代路径（用户裁定：没有意义）；
- 不重写 `run_suite.py` 为 `qemu-user` 版（= `P3` 任务）；不改其三套件口径；
- 不改 `spec/**`（只读册）、`contracts/**`、`.tao/contracts/**`、`manifests/**`、`components/musl/**` 补丁内容；
- 不动 `TESTCASES-045t` / `INFRA-082t` 的 `**状态**`。

## 接口规范
- **输入**：`761dfa3:components/qemu/patches/target/dadao/helper.c.patch`（基线，**只读取值比对**）；`components/qemu/**`（补丁树 + `series`）；`tools/qemu/min_rom_probe_082t.py`、`tools/infra/test_musl_static.py`（待删）；`tools/testcases/run_suite.py`、`components/musl/README.md`（连带面）。
- **输出**：① 恢复 semihosting-only 的 `helper.c.patch`（== 基线）；② 安装根 QEMU 二进制（与服务撤回后源码一致）；③ 删除两文件后的仓库树；④ `run_suite.py` 边界声明 + 硬失败；⑤ `components/musl/README.md` 指代订正；⑥ `INFRA-082t` 文末指针；⑦ `ISS-221` `closed`。
- **约束**：`series` 36 项不变；树形补丁体例（`docs/Process-01`）；命令在 workdir 内、相对路径；临时文件只落 `/tmp/opencode/QEMU-060t/`；不留 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`。

## 验收标准
1. **基线等价**：`git diff 761dfa3 -- components/qemu/patches/target/dadao/helper.c.patch` **空**、`md5sum` = `2b1665e99ed4736fc6579c386a3850f1`（附现场输出）。
2. **服务与两文件确已不存在**：`git grep -n 'umon_serve_syscall\|is_umon_user_syscall\|DADAO_NR_write\|SYS_UMON' -- .` **0 命中**（`helper.c.patch` 及全仓）；`ls tools/qemu/min_rom_probe_082t.py tools/infra/test_musl_static.py` ⇒ 均不存在。
3. **重建与安装**：`make build-qemu` rc=0、`make install-host` rc=0（日志路径 + 耗时申报；安装根二进制 mtime 晚于源码改动）。
4. **门控（各捕自身 rc，无 `tee` 吞码）**：`check-qemu-semantics` = **149/149** rc=0；`check-patch-tree` rc=0；`make check`(**L1**) rc=0；`make check-modules`(**L2**) rc=0；`make check-full`(**L3**) rc=0；`python3 tools/infra/check_issues.py` rc=0；`check-no-residue` rc=0。
5. **可达 FAIL 证据（必做）**：先制造一处未回退（如保留 `DADAO_NR_write` 宏 / 或先只删服务函数体）⇒ 验收 2 的 `git grep` 或语义门控**必须 FAIL**（留输出）⇒ **`cp` 备份 + md5 对账还原**（**禁** `git checkout`/`restore`/`stash`/`git show <commit>:<path>` 回写）⇒ 回绿；另需 `run_suite.py` 硬失败的现场演示（rc≠0 + 明确提示）。
6. **指针与台账**：`INFRA-082t` 文末指针 `grep` 命中、其 `**状态**` 仍为 `已验证`；`ISS-221` = `closed` + `resolved_by: QEMU-060t`（`check_issues.py` rc=0）。
7. **一键证据** `.work/evidence/<任务ID>/run.sh` rc=0，断言覆盖 1–6，且含 5 的反例节。
8. 完成区「修改文件」与实际 `git diff` 逐条一致（含越界披露项）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

按轮次追加，每次返工新增一轮。

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
