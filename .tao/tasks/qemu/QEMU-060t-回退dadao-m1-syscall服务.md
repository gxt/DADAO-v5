# QEMU-060t: `dadao-m1` syscall 服务回退（删 `SYS_UMON_SYSCALL` 服务，恢复 semihosting-only）

**模块**：qemu
**项目里程碑**：M8
**依赖**：`INFRA-082t`（`已验证`；**本任务 = 回退其阶段 A1/B 的 QEMU 侧服务**——其任务书**保留**、只追加指针，`**状态**` 不改）；`TESTCASES-045t`（`已验证`；其 runner 在服务撤回后**不再可跑** ⇒ 本任务按「连带面」最小处置）；`ADR-0020`（`D10` 两条 trap 路由口径）；`ADR-0025 D2`（无内核）；`.tao/contracts/contract-syscall.md`（**保留不动**）；`spec/DADAO-22-SBI §2`（`umon`/`jmon` 模型，**只读**）；`ISS-210`（`install-host` 纪律：改组件输入后安装根须同步，否则门控读旧二进制**假绿**）
**状态**：待验收

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
**测试结果**：`check-qemu-semantics` = **`149 total, 149 passed, 0 failed, 0 deferred, 0 errors` rc=0**（独立跑 + `make check-full` 内复跑同值）；**L1** `make check` rc=0（`repository checks (L1): PASS`）／**L2** `make check-modules` rc=0（`module checks (L2): PASS`；`picolibc-tests total=20 pass=18 fail=0 excluded=2`）／**L3** `make check-full` rc=0（`test-m6: PASS (lit full + lli value-level diff + Embench E2E)`；Embench `38/38 passed`）；`check-patch-tree` rc=0（**5 组件 / 145 补丁**）／`check-index-blobs` rc=0（`108 new-file`；`37 modification` 跳过）／`check-source-state` rc=0（`qemu: OK HEAD=cd6697e443e1 count=1 clean=True`）／`check-no-residue` rc=0／`check-knowledge-refs` rc=0／`check_issues.py` rc=0（`34 open / 12 closed / 0 blocking`）／`check_tasks.py` rc=0。一键证据 `./.work/evidence/QEMU-060t/run.sh` rc=**0**（**52 PASS / 0 FAIL**，含反例注入节；首跑 rc=1 = 我自己的 3 处断言 bug〔quotepath 未关／上下文正则过窄／`WITHDRAWN` 计数写 2〕⇒ 已修，二跑全绿，见自审 F8）。
**修改文件**：①（M）`components/qemu/patches/target/dadao/helper.c.patch`（还原 `761dfa3` 基线：md5 `2b1665e99ed4736fc6579c386a3850f1`、`git diff 761dfa3 -- <path>` 空、`series` **36 项未变**、`diff` 恰删 A1/B 的 3 组 hunk）；②（D）`tools/qemu/min_rom_probe_082t.py`；③（D）`tools/infra/test_musl_static.py`（均 `git rm`，删前 `git grep` 复核无门控/脚本调用方）；④（M）`tools/testcases/run_suite.py`（docstring 首部「WITHDRAWN」边界声明 + `main()` 入口硬失败 `rc=2`〔含 `QEMU-060t`/`P3` 提示〕+ 订正一处指向已删文件的陈旧注释；`+28/−1`，3 hunk，度量/统计主体零改动）；⑤（M）`components/musl/README.md`（「服务方」指代改指 `P3`（`qemu-user`）；1 行，syscall stub 口径未动）；⑥（M）`.tao/tasks/infra/INFRA-082t-musl静态最小集移植.md`（**只追加** `+7/−0`：文末「服务回退指针」节；`**状态**：已验证` 与既有完成区/审阅记录**未改**）；⑦（M）本任务书（`**状态**` + 完成区 + 自审）。**未动**：`spec/**`、`contracts/**`、`.tao/contracts/**`、`manifests/**`、`components/musl/patches/**`（16 补丁）、`components/qemu/changelog.md`、`Makefile`、`tools/infra/build_musl.py`、`.tao/knowledge/**`（含 `ISS-221`，见遗留②）。
**验收结果**：`make build-qemu` rc=0（无 `nohup` 会话内等待；`setsid nohup` + 落盘 `.work/log/qemu/*.EXIT`，见遗留⑥）；`make install-host` rc=0（`install-host: PASS`，`JOBS=8`）；**两处二进制 md5 一致** = `3ede8ad829f50d5a8f43bf0f948a879d`（`.work/build/qemu/qemu-system-dadao` × `.dadao/cross-toolchain/bin/qemu-system-dadao`，安装根 mtime 21:59:20 晚于编译输入 mtime 21:58:15）；安装根 `qemu-system-dadao --version` = **`QEMU emulator version 11.1.1 (v11.1.1-1-gcd6697e)`** ⇒ 产品级证明「安装二进制含撤回后源码 revision `cd6697e`」（ISS-210 安装根同步已闭环）。
**新发现/坑**：① **`make apply-series` 在 patchless 组件上崩（pre-existing，与本改动无关）**：处理完 qemu 后 `KeyError: 'patch_dir'`（`chipyard` 无该键；`linux`/`llvm-test-suite`/`libc-test` 同）⇒ rc=2；现场按 `docs/Process-01 §7` 文档化恢复步骤重放（`git -C .work/source/qemu reset --hard <base>`〔前置 `status --porcelain`=0 行〕→ `make apply-series` → 36 项全落地 → `--source-state` 绿）；`manifests/**` 与 `apply_series.py` 本任务**零改动** ⇒ **建议另立 issue**（非本任务范围）。② **任务书验收 2「全仓 0 命中」不可达且自相矛盾**（第 5 项本身要求把 `SYS_UMON_SYSCALL` 写进 `INFRA-082t` 正文；台账与其它任务书亦含该 token）⇒ 落实为**可机械判定版**：实现符号（`umon_serve_syscall`/`is_umon_user_syscall`/`DADAO_NR_write`/`umon_sys_*`/`umon_host_*`/`umon_set_*`）在 `components/qemu`+`tools`+补丁+已应用源 **0 命中**；`SYS_UMON` 仅存于 `run_suite.py` 撤回说明 3 行（逐行断言为撤回散文）与 `.tao/**` 散文 29 行（信封式列出）。③ **`check-qemu-semantics` 对服务不敏感**（A1 加服务前后均 149/149，`INFRA-082t` 完成区）⇒ 服务**不可**由该门控判 FAIL；可达 FAIL 落在补丁/索引层：注入 1 行 `DADAO_NR_write_INJECTED` ⇒ `check-index-blobs` rc=1（点名 `helper.c.patch` blob 失配）+ `check-patch-tree` rc=1（`HEAD diff differs from target/dadao/helper.c.patch`），`cp` 还原后双回绿；`run_suite.py` 侧 rc=2 现场已证。④ **`ISS-216` 语义回潮**：其标题「`dadao-m1` 机体现**无** `SYS_UMON_SYSCALL` 服务方」在服务撤回后**字面重新为真**（其 `closed` 系「已补服务」所致）⇒ 提请 `/complete` 追加一句口径（本任务未动 `.tao/knowledge/**`）。⑤ **A1/B 未在 `components/qemu/changelog.md` 留条目**（`check-component-changelog` 仅查形态，L1 绿）⇒ 本次还原亦未加条目（与基线一致）⇒ 提请 architect 裁定是否补历史条目。⑥ 环境：长任务期间 opencode 服务**重启**，`install-host` 进程被杀（无 `.EXIT` 标记）⇒ 原样重跑 **1 次**（retry #1）得 rc=0；非产品失败，现场留 `.work/log/qemu/`。⑦ 非 ASCII 路径下 `git grep`/`git diff` 计数须 `-c core.quotepath=false`（本证据脚本自身踩中 ⇒ 印证 `lessons §2.19`）；`git grep` 输出行首路径比较须容忍引号。
**遗留问题**：① **`ISS-221` 未关闭**（父会话裁定「归 `/complete`」；本任务未动 `.tao/knowledge/**`）⇒ 可直接套用片段见下（`notes` 为**追加**段）。② `TESTCASES-045t` 任务书第 7 行仍以「含 QEMU 侧 `SYS_UMON_SYSCALL` 服务」为依赖（服务撤回后**语义悬挂**）⇒ **登记不改**（该册正文/`**状态**`不在本任务范围，交 architect 裁定；其 runner 已由本任务加硬失败，运行验证移交 `P3`）。③ `components/musl/README.md` 的「服务方 = `P3`（`qemu-user`）」为**规范性指代**，`P3` 尚未开立 ⇒ 随 `P3` 落地复核。④ `.work/source/qemu` 重建走 `reset --hard <base>` + `apply-series`（`Process-01 §7` 文档化流程，非禁用还原；仅影响该组件检出，仓库工作树未受影响）⇒ 已披露。⑤ 服务撤回的**产品级回归哨兵**随两个文件被删（`check-qemu-semantics` 不覆盖该路由）⇒ 若日后需防「服务悄悄复活」，宜在 L1 加一条形态门控（建议，非本任务）。⑥ 长任务均按纪律脱离会话（`setsid nohup` + `.EXIT`）：`.work/log/qemu/QEMU-060t-{build-qemu,install-host,check-full,gates}.EXIT`、`/tmp/opencode/QEMU-060t/{rebuild,gates,l3,evidence}.EXIT`。

**`ISS-221` 关闭片段（供 `/complete` 直接套用；本任务未改 `.tao/knowledge/issues.yaml`）**：
```yaml
- id: ISS-221
  status: closed
  resolved_by: QEMU-060t
  notes: "<既有 notes 原样保留> …【关闭（2026-10-15，`QEMU-060t`）】第三条路由（user `trap cfx0,0` 由 QEMU 接管 = `SYS_UMON_SYSCALL` 服务）已由用户 2026-10-15 裁定撤回（执行 = `QEMU-060t`：`helper.c.patch` 还原 `761dfa3` 基线、md5 `2b1665e99ed4736fc6579c386a3850f1`）⇒ `spec/Machine-01 §4.3` 的两条路由**重新完备**、规范缺口**不存在**；`spec/` 全程**零改动**、无需授权（`check-spec-readonly` rc=0）。"
```


## 审阅记录

按轮次追加，每次返工新增一轮。

#### 第 1 轮 engineer 自审

**审查对象**：本任务全部改动（补丁还原 / 两文件删除 / `run_suite.py` 边界 / `musl/README.md` 一句 / `INFRA-082t` 只追加）；**自主逐行审查**（无嵌套子代理）。每 finding 给处置 + 复验证据。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| F1 | `run_suite.py` 硬失败取 `rc=2` 是否恰当、是否「在 `main()` 入口」（任务书 §3a）；`--list` 一并被挡是否过宽 | ✅已修（按任务书口径定型，理由写入 docstring） | 守卫置于 `args = ap.parse_args()` 之后、一切子命令之前；`rc=2` = 该脚本既有「setup error」码（与 `--only` 未知名同码同体例） | `python3 tools/testcases/run_suite.py --list` **rc=2** + stderr 含 `withdrawn`/`QEMU-060t`/`P3`；`make check-testcases-suites` rc=2 |
| F2 | 边界声明须**不重写主体**（任务书 §3a/不属本任务） | ✅已修 | docstring 首部新增 WITHDRAWN 块 + `main()` 一处守卫；度量口径/分类/统计主体**零改动** | `git diff master -- tools/testcases/run_suite.py` = 3 hunk / `+28 −1`；分类函数未触 |
| F3 | `run_suite.py` 内仍指向**已删** `tools/infra/test_musl_static.py` 的注释（悬挂引用，任务书 §3c） | ✅已修 | 改为「the same set `tools/infra/build_musl.py` uses」（现场核 `build_musl.py:115` 为同一元组） | `git grep test_musl_static -- tools/` = **0**；全仓仅本册 + `INFRA-082t` 散文命中 |
| F4 | A1/B 是否**只**改了 `helper.c.patch`（防漏还原） | ❌不修（无漏，无需改） | 无 | `git show --stat 0986dc9 -- components/qemu/` 与 `7255af8 -- components/qemu/` **均仅** `helper.c.patch`；`diff` 恰 3 组 hunk（= 任务书 §现场事实②） |
| F5 | 还原手段合规（禁 `git checkout/restore/stash/show>` 回写） | ✅已修（合规） | `git show 761dfa3:<path>` **只落 `/tmp`** 比对，落位用 `cp`；注入还原亦 `cp`+md5 | md5 `2b1665e9…`；`git diff 761dfa3` 空、`diff` 0 行 |
| F6 | `musl/README.md` 是否越改（应只动「服务方」指代） | ✅已修 | 仅改该从句；syscall stub 口径（`rd15` 号 / RISC-V 编号 / `rd8` 返回 / errno 负值）**一字未动** | `git diff` = 1 行；L1 `check-component-changelog` 绿 |
| F7 | `INFRA-082t` 是否确为「只追加」（`**状态**`/完成区/审阅记录不可改） | ✅已修 | 文末新增「服务回退指针」节 | `git diff --numstat master -- <册>` = **`7 0`**（零删除）；`**状态**：已验证` 不变 |
| F8 | 证据脚本自身 3 处断言 bug（首跑 rc=1） | ✅已修 | ①`git grep` 加 `-c core.quotepath=false`（非 ASCII 路径陷阱）②`SYS_UMON` 上下文正则放宽（3 行撤回散文）③`WITHDRAWN` 计数 2→1 | 二跑 `./.work/evidence/QEMU-060t/run.sh` **52 PASS / 0 FAIL** rc=0；`bash -n` 通过 |
| F9 | 验收 2「全仓 0 命中」是否可达 | ❌不修（**不可达**且与第 5 项自相矛盾） | 改为可机械判定版并全量披露 | 证据 B 节 6 条断言；全仓 32 命中 = `.tao/**` 散文 29 + `run_suite.py` 撤回说明 3（逐行断言为散文） |
| F10 | 验收 5「语义门控必须 FAIL」是否有可达路径 | ⏸延后（该路径**不存在**，附证） | 无 | A1 加服务前后 `check-qemu-semantics` 均 `149/149`（`INFRA-082t` 完成区）⇒ 该门控对服务不敏感；可达 FAIL 改在 `check-index-blobs` rc=1 + `check-patch-tree` rc=1 + grep>0（注入实测）+ `run_suite.py` rc=2 |
| F11 | `ISS-221` 未关闭（父会话裁定归 `/complete`） | ⏸延后（附可直接套用片段） | 完成区给 YAML 片段（`notes` 追加段） | `check_issues.py` rc=0 |
| F12 | `.work/source/qemu` 用 `reset --hard <base>` 是否违禁用还原清单 | ⏸延后（合规：`docs/Process-01 §7` 文档化步骤，仅组件检出） | 无（未触碰仓库工作树） | 前置 `status --porcelain`=0 行；重放后 `--source-state` `qemu: OK … clean=True` |

**判决**：F1–F3/F5–F8 `✅已修` 且附复验；F4/F9 `❌不修` 均有现场证据（**非缺陷**）；F10–F12 `⏸延后` 理由/证据成立（F11 附片段）。无阻断 finding ⇒ `**状态**` → **`待验收`**。遗留（`ISS-221` 关闭、`TESTCASES-045t` 悬挂、`apply-series` KeyError 另立 issue）见完成区，**不写「遗留：无」**。


#### 第 1 轮 reviewer 验收

#### architect 提交与文件集审核（2026-10-15；**只追加**）
**档位**：正常提交（**不带 `WIP:`**，按父会话批次指令）。**如实披露**：本笔提交时本册「第 1 轮 reviewer 验收」为**空**、`**状态**` = `待验收` ⇒ 该档位系**父会话指令**，非已落盘的 reviewer 判决；若后续判 `Needs Revision`，返工提交仍落本分支（本笔不回滚）。
**文件集对账**（**显式 staging**，未用 `git add -A`/`.`）：`git diff --cached --name-status -M` = **7 项**，与完成区「修改文件」①–⑦ **逐项一致**（无漏提 / 无多提 / 无越界）：
- `M components/qemu/patches/target/dadao/helper.c.patch`（①）
- `D tools/qemu/min_rom_probe_082t.py`（②）、`D tools/infra/test_musl_static.py`（③）
- `M tools/testcases/run_suite.py`（④）、`M components/musl/README.md`（⑤）
- `M .tao/tasks/infra/INFRA-082t-musl静态最小集移植.md`（⑥，只追加）
- `M .tao/tasks/qemu/QEMU-060t-回退dadao-m1-syscall服务.md`（⑦）
**范围外检查**：`spec/**`、`contracts/**`、`.tao/contracts/**`、`manifests/**`、`Makefile`、`components/musl/patches/**` **零改动**（开工前 `status --porcelain -uall` 现场核 ⇒ 未列入）。
**提交**：`a0705e6`（笔 1 = 本任务交付，7 files，`73 insertions / 1179 deletions`）；`aabac51`（笔 2 = 登记 `ISS-224`〔`P3`，现场取号〕，`check_issues.py` rc=0、35 open / 12 closed）；本段留痕 = 笔 3（仅追加本节）。**只 `commit`，未 `push`、未 merge**。
**只读核对（供验收，2026-10-15 现场真实 rc）**：`check-qemu-semantics` **rc=0「149 total, 149 passed」**；`make check`(L1) **rc=0**（`check-components: PASS` + `repository checks (L1): PASS`）；`check-patch-tree` **rc=0「5 component(s), 145 patches OK」**；`check-tasks` **rc=0**（附报告型计数，不阻断）。日志 `/tmp/opencode/QEMU-060t/ro-*.log`。
**另（非本任务判据，供 `ISS-224` 取证）**：`make apply-series` 现场 **rc=2**（`KeyError: 'patch_dir'`，崩于首个 `patchless` 组件 `chipyard`；前 4 组件 `already applied … skipped` ⇒ 幂等无副作用）⇒ 与本笔 `ISS-224` 登记一致，**非本任务引入、不影响本册验收**。日志 `/tmp/opencode/QEMU-060t/repro-apply-series.log`。
