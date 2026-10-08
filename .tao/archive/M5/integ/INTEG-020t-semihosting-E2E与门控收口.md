# INTEG-020t: SEE/semihosting E2E + harness stdio 捕获 + 门控收口（`make test-semihost`）

**模块**：integ
**项目里程碑**：M5
**依赖**：`QEMU-046t`、`QEMU-047t`、`TESTCASES-033t`、`TESTCASES-034t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `QEMU-046t`（semihosting 共享层 + `SYS_EXIT`）、`QEMU-047t`（新 bootrom + `-bios`）、`TESTCASES-033t`（SEE/semihosting 向量）、`TESTCASES-034t`（exit-port→`SYS_EXIT` 迁移后）。
  - `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，**D7** host 侧安全：`-semihosting-config` 的 `target=`/`chardev=`/`arg=`；建议默认 `gdb`/沙箱）+ `adr-0004` 修订。
  - `spec/Process-05-里程碑TDD规范.md §6`（落点 + `INFRA-048t` 的 `.dadao/tests/`）；`tools/infra/paths.py`（`test_artifacts_dir`）。
  - 既有 `tools/integ/run_elf_e2e.py`/`Makefile::test-elf`/`check-lit`（E2E 驱动范式）。
  - **门槛（`INTEG-019k` §第 2 轮用户裁定 9；**正向口径已由 `INTEG-019k` §第 8 轮修订**）**：门控名 = **`make test-semihost`**（**不是** `test-see`）；组成 = ① **正向**（**bootrom（`-bios`）+ bin 应用**经 `-semihosting`、console 捕获、`SYS_EXIT` 码）；② **权限反例**（**M5 可观测 = cfx 级**：`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕；**`NUPERM/NJPERM/NSPERM/NHPERM` 出自 `DADAO-12 §2.2` PTBR 权限层、不在 M5**〔`ADR-0020 D9`〕）；③ **服务表各条至少 1 例**（**落点 = `QEMU-046t` 探针 `tools/qemu/min_rom_probe_046t.py` 承担**——全量跑 `svc_*` 逐服务 ≥1 例 + 覆盖计数断言 = 25〔机器可判：`--list` 末两行 `distinct … 25` / `required … 25`〕；依据/跨模块引用可接受性见审阅记录「下发前预检修订（architect，2026-10-08）」F1）；④ **不回归**（`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit`）；⑤ **`INTEG` 开闭**。
  - **RAM@0 双映射（C1 step1，`ADR-0004 R3`/`ADR-0020 D15`）**：M5 **正向**（bootrom/SEE + `-semihosting`）经 **RAM@0**（`QEMU-049t` 双映射提供）；**旧 RAM 段过渡保留** ⇒ 既有测试不回归；**step2**（旧向量/harness 迁到 RAM@0 + 删旧段 + 收紧断言）**另立、随 M6**（用户 2026-10-08 裁定；`ISS-165`），**不阻塞本门槛**。
- **输出**：
  1. **`tools/integ/` 驱动**（**复用 `tools/integ/run_m5_e2e.py`**〔`TESTCASES-033t` 产出〕，**只追加/最小改**，**不另建 `run_semihost_e2e.py`**）：fail-closed——bootrom（`-bios`，`QEMU-047t`）+ **bin 应用**（`objcopy -O binary`）经 `-semihosting`，跑通 semihosting 服务，**捕获 console 输出**，比对 `SYS_EXIT` 码；逐例打印「名字/期望/实际/退出码」。**integ 侧 E2E 范围 = console ≥3 类**（`WRITEC`/`WRITE0`/`WRITE`）+ **`EXIT`/`EXIT_EXTENDED`**；**25 服务覆盖由 `QEMU-046t` 探针承担**（门槛 ③）。**（原「单/多 TU ELF」正向用例移 M6——用户 2026-10-08 裁定。）**
  2. **harness stdio 捕获（细节展开，本任务明确落定）**：
     - **`-semihosting-config` 的 `target=`/`chardev=`/`arg=` 由谁传**：**落定 = 驱动脚本传**（`tools/integ/run_m5_e2e.py` **已在驱动内**传 `-semihosting-config enable=on,target=native,chardev=semi` + `-chardev file,id=semi,path=<console>`）；**`Makefile` 只负责调用驱动**（与 `ADR-0020 D7` 一致：`target=`/`chardev=` 由 harness 提供、`native` 显式开启；落点见审阅记录「下发前预检修订」F2）。
     - **console 输出捕获落点/比对方式**：捕获 = **chardev 文件**（`-chardev file,...`），落点 = 驱动 `--work-dir` 下 `<stem>.console`（**默认 `.dadao/tests/m5-e2e/`**，经 `paths.py` 解析，符合 `INFRA-048t`「`.dadao/tests/` 下」口径；**不另起 `semihost-e2e/`**——复用既有驱动、最小改，依据见「下发前预检修订」F2）；**比对方式 = 逐字节精确**（`console != expected_console` ⇒ FAIL），期望串来自 `expected.yaml` 的 `expected_console`（独立派生）。
  3. **`Makefile` 新目标 `test-semihost`**：见门槛五组成；**任何一类不符即非零退出**；与既有 `test-elf`/`test-codegen` **并存**。**门槛 ③（服务表覆盖）由 `test-semihost` 调用 `QEMU-046t` 探针** `tools/qemu/min_rom_probe_046t.py` 实现（**全量跑**，`--qemu $(QEMU_BIN)` 与 install 根一致；探针自身 fail-closed：缺任一服务即非零退出）。
  4. **`tests/e2e/lit/`**（如适用）：semihosting E2E lit 用例（`Process-05 §6`；`check-lit` 路径 `tests/e2e/lit`）。
  5. **`make check` 收口**：新目标接入/不破坏既有门控；`INTEG` 开闭登记（`INTEG-021m` 前置）。
- **约束（硬）**：
  - **门控名 = `make test-semihost`**（**不得**用 `test-see`——用户指出"没有 SEE"）。
  - **`SYS_EXIT` 为退出机制**（`TESTCASES-034t` 后）；**不回归** M1–M4 链。
  - **期望值独立派生**（`Process-05 §4`）；console 比对**不得**只凭 QEMU 输出反填。
  - **不回归**：`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit` 全绿。
  - `Makefile`/`tests/`/`tools/` 为共享文件，与其它改这些文件的任务**串行**。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/INTEG-020t/`；**不提交 git**；复杂命令输出留存 `.work/log/integ/`（**禁 `tee`**）。
  - **重建成本申报**：依赖 `build-mc`/`build-lld`/`build-qemu`（增量；`build-qemu` 5–20 分钟）；开工前说明。

## 验收标准

1. **正向**：`make test-semihost` EXIT=0；bootrom（`-bios`）+ **bin 应用**经 `-semihosting`，console 捕获内容与 `SYS_EXIT` 码逐例比对正确；给真实输出（console ≥1）。**（原「单/多 TU ELF」正向用例移 M6——用户 2026-10-08 裁定。）**
2. **权限反例**（cfx 级）：**M5 可观测 = cfx 级**——`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕（≥1 类）——机器可判（真实输出）。**（`NUPERM/NJPERM/NSPERM/NHPERM` 出自 `DADAO-12 §2.2` PTBR 层、不在 M5；`ADR-0020 D9`。）**
3. **服务表覆盖**：**25 服务各 ≥1 例**（**落点 = `QEMU-046t` 探针 `tools/qemu/min_rom_probe_046t.py`**：全量跑逐服务 ≥1 例 + 覆盖计数 = 25 断言；`test-semihost` 调用该探针；**脚本计数 = 25 机器可判**——`--list` 打 `distinct 25`/`required 25`；给真实输出）。
4. **不回归**：`make test-elf` 5/5、`make test-codegen` 15/15、`make check`、`make check-lit` 全 EXIT=0（给真实输出）。
5. **harness stdio 落定**：完成区明确「`-semihosting-config` 传参方」与「console 捕获落点/比对方式」，且与实现一致（`grep`/真实输出）。**口径（落定）**：传参方 = **驱动脚本**（`run_m5_e2e.py`，`Makefile` 只调用驱动）；落点 = 驱动 `--work-dir` 下 `<stem>.console`（默认 `.dadao/tests/m5-e2e/`，`paths.py` 解析）；比对 = **逐字节精确**（见「下发前预检修订」F2）。
6. **反例门控**：注入反例（改一条期望退出码 / 改一条 console 期望串 ⇒ `test-semihost` **非零退出** ⇒ 还原 ⇒ 回绿）；给真实输出。
7. **一键证据脚本**：`.work/evidence/INTEG-020t/run.sh`——非交互、失败非零、逐项打印、含注入自检、结尾**禁 `tee`**。
8. **无残留**：`git status --untracked-files=all` 仅 `tools/integ/**` + `Makefile` + `tests/e2e/lit/**` + 本任务书；`.dadao/` 生成物不入库。

## 完成区

**测试结果**：**通过 5/5 组**（门控 `make test-semihost` EXIT=0，实测 59s；证据脚本 27 项断言全 PASS，235s）。失败原因：无。

- ①**正向**（`tools/integ/run_m5_e2e.py`）：**10/10**（5 semihosting〔`WRITEC`/`WRITE0`/`WRITE`/`EXIT`/`EXIT_EXTENDED`〕+ 4 cfx 权限反例 + 1 general trap）。
- ②**cfx 级权限反例 4/4**：`m5_perm_reserved_illi`(80, cause=`ILLI`)、`m5_perm_mask_illi`(81, `ILLI`)、`m5_perm_unimpl_cfxreg`(82, `CFXREG`)、`m5_perm_badcombo_cfxreg`(83, `CFXREG`)。
- ③**服务表覆盖 25/25**（`tools/qemu/min_rom_probe_046t.py` 全量跑）：`[PASS] service coverage: all 25 service ids exercised`、`RESULT: PASS`；`--list` → `distinct service ids covered: 25` / `required service ids: 25`。
- ④**不回归**：`test-elf` **5/5** EXIT=0、`test-codegen` **15/15** EXIT=0、`check` EXIT=0（`repository checks: PASS`）、`check-lit` **62/62**（MC 56 + CodeGen 2 + E2E 4）EXIT=0。
- ⑤**INTEG 开闭材料**：见下「遗留问题 → INTEG 开闭登记材料」。

**修改文件**（与 `git status --porcelain -uall` 一致）：

- `Makefile`：`.PHONY` += `test-semihost`；`help` += 1 行；新增 `test-semihost` 目标（组 ④ 作前置：`install-host build-bootrom test-elf test-codegen check`；组 ①+② 调 `run_m5_e2e.py`、组 ③ 调 `min_rom_probe_046t.py`，任一非零即 `exit $$rc`）。
- `tools/integ/run_m5_e2e.py`：**最小追加**（不改签名/流程）——`CaseResult` 增 `console_expected/console_actual/console_ok`；记录 chardev console 期望/实际/逐字节比对结果；`run_suite` 逐例打印 `console <name> expected=<repr> actual=<repr> match|MISMATCH (byte-exact)`。

> 未改：`tests/e2e/lit/**`（**判定不适用**，理由见自审 F3）、`spec/`（交集空）、`contracts/**`、`components/**`、`tools/qemu/min_rom_probe_046t.py`（复用其已验收产物）。

**验收结果**（真实命令 + 输出节选；完整输出见 `.work/log/integ/INTEG-020t-*.log`）：

1. **正向（`make test-semihost` EXIT=0）**：
   ```
   $ make test-semihost
   test-semihost: [1/2] forward semihosting + cfx-level permission counter-examples
   PASS  m5_semi_writec  expected=64 actual=64 exit=64  (match)
   console m5_semi_writec  expected=b'A' actual=b'A' match (byte-exact)
   PASS  m5_semi_write0  expected=65 actual=65 exit=65  (match)
   console m5_semi_write0  expected=b'OK\n' actual=b'OK\n' match (byte-exact)
   ...
   PASS  m5_semi_exit  expected=67 actual=67 exit=67  (match)
   PASS  m5_semi_exit_extended  expected=68 actual=68 exit=68  (match)
   Results: 10/10 passed, 0 failed
   run_m5_e2e: PASS
   test-semihost: [2/2] 25-service table coverage (QEMU-046t probe)
   [PASS] service coverage: all 25 service ids exercised
   RESULT: PASS
   test-semihost: PASS (forward + permission + 25-service + no-regression + INTEG registration)
   $ echo $?  ->  0        （实测 59s）
   ```
   console chardev 文件字节（`.dadao/tests/m5-e2e/*.console`）：`m5_semi_writec.console` = `41`（"A"）、`m5_semi_write0.console` = `4f 4b 0a`（"OK\n"）；`m5_semi_write.console` 空（`WRITE` 走 host 文件 `m5_write.txt`="WXYZ"）。
2. **cfx 级权限反例 4/4**（机器可判，真实输出）：
   ```
   PASS  m5_perm_reserved_illi   expected=80 actual=80 exit=80 cause=ILLI   (match)
   PASS  m5_perm_mask_illi       expected=81 actual=81 exit=81 cause=ILLI   (match)
   PASS  m5_perm_unimpl_cfxreg   expected=82 actual=82 exit=82 cause=CFXREG (match)
   PASS  m5_perm_badcombo_cfxreg expected=83 actual=83 exit=83 cause=CFXREG (match)
   ```
3. **服务表覆盖 25/25**：
   ```
   $ python3 tools/qemu/min_rom_probe_046t.py --list | tail -2   -> EXIT=0
   distinct service ids covered: 25
   required service ids: 25
   $ python3 tools/qemu/min_rom_probe_046t.py --qemu <install-root>/qemu-system-dadao | tail -2  -> EXIT=0
   [PASS] service coverage: all 25 service ids exercised
   RESULT: PASS
   ```
   （`test-semihost` 已把该探针纳入组 ③，其 `PASS/FAIL` 与门控退出码联动。）
4. **不回归**（各单独真实输出）：
   ```
   $ make test-elf       -> EXIT=0 ; Results: 5/5 passed, 0 failed ; test-elf: PASS
   $ make test-codegen   -> EXIT=0 ; Results: 15/15 passed, 0 failed ; test-codegen: PASS
   $ make check          -> EXIT=0 ; repository checks: PASS
   $ make check-lit      -> EXIT=0 ; Total Discovered Tests: 62 ; Passed: 62 (100.00%)
   ```
5. **harness stdio 落定（与实现一致，grep + 真实输出）**：
   - **`-semihosting-config` 传参方 = 驱动脚本**：`grep -n` 命中 `tools/integ/run_m5_e2e.py:255` `"-semihosting-config", "enable=on,target=native,chardev=semi"`（`target=native` **显式**，合规 `ADR-0020 D7`）+ `:256` `"-chardev", "file,id=semi,path=" + console_path`；`Makefile` 中 `run_m5_e2e.py` 仅被调用（`:514`），**不**传 `-semihosting-config`（`grep semihosting-config Makefile` 无命中）。
   - **console 捕获落点 = chardev 文件**，落点 = 驱动 `--work-dir` 下 `<stem>.console`（默认 `.dadao/tests/m5-e2e/`，`run_m5_e2e.py:89 DEFAULT_WORK_DIR = str(_TEST_ARTIFACTS / "m5-e2e")`，经 `tools/infra/paths.py` 解析；`Makefile` 显式传 `--work-dir $(SEMIHOST_E2E_WORK)=$(TEST_ARTIFACTS_DIR)/m5-e2e`）。
   - **比对 = 逐字节精确**：`run_m5_e2e.py:293 res.console_ok = (console == want)`（`console` 为 chardev 文件原始字节，`want = expected_console.encode("latin-1")`），不符即 FAIL；门控日志逐例打印期望/实际字节。
6. **反例门控（一键脚本内置，真实输出）**：
   ```
   $ .work/evidence/INTEG-020t/run.sh      -> EVIDENCE: PASS (EXIT=0)
   CHECK  inject-A-changed-file: expected=yes actual=yes  [PASS]
   RUN    injected exit-code => make test-semihost EXIT=2
   CHECK  inject-A-fails-gate: expected=nonzero actual=nonzero  [PASS]
   CHECK  inject-A-restored-md5: expected=e1d5942f... actual=e1d5942f...  [PASS]
   CHECK  inject-B-changed-file: expected=yes actual=yes  [PASS]
   RUN    injected console    => make test-semihost EXIT=2
   CHECK  inject-B-fails-gate: expected=nonzero actual=nonzero  [PASS]
   CHECK  inject-B-restored-md5: expected=e1d5942f... actual=e1d5942f...  [PASS]
   RUN    after restore       => make test-semihost EXIT=0
   CHECK  gate-green-after-restore: expected=0 actual=0  [PASS]
   ```
   注入真实原因（EV_LOG）：`FAIL m5_semi_writec expected=153 actual=64 exit=64 (rc=64 != expected 153)`（A）/ `... (console=b'A' != b'B')` + `console m5_semi_writec expected=b'B' actual=b'A' MISMATCH`（B）⇒ 两条比对通道**各自独立可失败**；还原用 **`cp` + md5**（`e1d5942f9ec2bd2ef6a76581b1a90005`），未用 `git checkout/restore/stash/show`。
7. **一键证据脚本**：`.work/evidence/INTEG-020t/run.sh`（非交互；失败非零；逐项打印「名/期望/实际」；内置 A/B 注入自检 + `cp`/md5 还原 + EXIT trap 兜底；结尾直接 `exit`，**无 `tee`**）。运行输出 `EVIDENCE: PASS`（27 项断言全 PASS，235s）。
8. **无残留**：
   ```
   $ git status --porcelain -uall
    M Makefile
    M tools/integ/run_m5_e2e.py
   ```
   （+ 本任务书；`.dadao/tests/m5-e2e/`、`.work/**` 均在 `.gitignore` 内，生成物不入库。）

**新发现/坑**：

1. **GNU make 对「recipe 失败」返回 2，而非子命令的 1**：注入反例时 `run_m5_e2e.py` 返回 1，`make test-semihost` 却返回 **2**。证据脚本的「注入须非零」判据若写成 `==1` 会假 FAIL ⇒ 须用 `-ne 0`。（已在 `run.sh` 用 `nonzero()` 实现。）
2. **门控前置链即「不回归」载体**：把组 ④（`test-elf`/`test-codegen`/`check`〔含 `check-lit`〕）作 `test-semihost` 的 **make 前置**，即可让「任一类不符 ⇒ 非零」由 make 机械保证，无需在 recipe 内重复调用；整轮实测仅 59s（`install-host` 增量 27s 为主，无组件重建）。
3. **console「≥3 类」口径**：`WRITEC`/`WRITE0` 产生 console 字节；`WRITE` 服务的载荷走 **host 文件**（`expected_file`），其 console 为空——三者均被 5 例 semihosting 覆盖，console 比对对「有输出的 2 例」逐字节校验、对「应无输出的 3 例」校验为空。

**遗留问题**：

- **无未修 finding**；本任务范围内无功能缺口。
- **`tests/e2e/lit/**` 未改（判定不适用）**：M5 门槛的唯一 E2E 载体是 `make test-semihost`（复用 `run_m5_e2e.py`）；再加 lit 用例会**重复同一 pipeline**（违反 DRY/「不另建 E2E 驱动」），且引入 lit→`build-bootrom` 的隐式构建耦合（lit 无该前置）。既有 `check-lit` 保持 62/62 全绿。
- **INTEG 开闭登记材料（供 `INTEG-021m` 核验）**：
  - 门槛名/结果：**`make test-semihost` EXIT=0**（五组成：正向 10/10 / cfx 权限反例 4/4 / 服务表 25/25 / 不回归 5-15-62-check 全绿 / 本登记）。
  - 证据路径：`.work/log/integ/INTEG-020t-test-semihost.log`（+ 目标自身 `test-semihost.log`、`test-semihost-probe.log`）、`INTEG-020t-test-elf.log`、`INTEG-020t-test-codegen.log`、`INTEG-020t-check.log`、`INTEG-020t-check-lit.log`、`INTEG-020t-evidence-run.log`、`.work/evidence/INTEG-020t/run.sh`。
  - 产出：`Makefile::test-semihost`、`tools/integ/run_m5_e2e.py`（复用 + 最小追加）。
  - **提醒**：`INTEG-021m`「核验」第 11 行仍写产出为 `tools/integ/run_semihost_e2e.py`，与本任务「复用 `run_m5_e2e.py`、不另建」的判定（主会话 2026-10-08 + 本任务书审阅记录）不一致 ⇒ 建议 `INTEG-021m` 收尾时把该行更正为 `tools/integ/run_m5_e2e.py` + `Makefile::test-semihost`（属 `INTEG-021m` 范围，本任务未越界改它）。

## 审阅记录

#### 第 1 轮 engineer 自审

（自主逐行审查；finding 处置表见下）

**审查范围**：`Makefile`（`test-semihost` 目标 + `.PHONY` + help）、`tools/integ/run_m5_e2e.py`（console 追加）、`.work/evidence/INTEG-020t/run.sh`；对真实执行输出逐条核（无伪造）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `make` recipe 失败返回 2（非子命令 1）；证据脚本若按 `==1` 判会假 FAIL | ✅已修 | `run.sh` 判据统一用 `nonzero()`（`-ne 0`），不写死 1 | `run.sh` 注入两轮 `RUN ... EXIT=2` + `CHECK ... [PASS]`；`EVIDENCE: PASS` |
| F2 `test-semihost` 的「不回归」若只在文档声明、不进目标，则「任一类不符即非零」不成立 | ✅已修 | 组 ④ 作 make **前置**（`test-elf test-codegen check`〔含 `check-lit`〕）；组 ①+②③ 在 recipe 内 `rc` 捕获 `exit $$rc` | `make test-semihost` EXIT=0；注入 A/B ⇒ EXIT=2（组 ① recipe 失败即整体非零） |
| F3 `tests/e2e/lit/**` 是否需新增 semihosting 用例 | ❌不修（判定不适用） | 未改 `tests/e2e/lit/**` | 需 DRY：唯一 E2E 载体是 `run_m5_e2e.py`，lit 复用同一 pipeline 属重复且引入 lit→bootrom 隐式耦合；`make check-lit` 62/62 EXIT=0 未破 |
| F4 console 比对是否「可见/可失败」（防恒真） | ✅已修+证伪 | 追加逐例 `console expected= actual= match/MISMATCH` 打印 | 注入 B（`"A"→"B"`）→ `MISMATCH` → `make test-semihost` EXIT=2；还原 md5 相同 → 回绿 |
| F5 注入还原方式（禁 `git checkout/restore/stash/show`） | ✅已修 | `run.sh` 用 `cp` 备份 + `md5sum` 对账 + EXIT trap 兜底 | `inject-A/B-restored-md5` 期望=实际=`e1d5942f...`；结尾 `final-manifest-md5` 同；`git status` 仅 2 文件 |
| F6 `build-bootrom` 与 `install-host` 在 `make -j` 下可能竞态 | ⏸延后（不改） | 未改 | 默认（无 `-j`）make 顺序执行，且前置列表 `install-host` 在 `build-bootrom` 前 ⇒ 顺序保证；本项目门控命令不并行（`AGENTS.md`）；`make build-bootrom` 本就注明「先 `make install-host`」。若要并行安全可另立（改 `build-bootrom` 依赖，超本任务最小范围） |
| F7 组 ③ 探针 fail-closed 是否真进入门控退出码 | ✅已核 | recipe 捕获探针 `rc`，`$$rc -ne 0` ⇒ FAIL | `test-semihost-probe.log` `[PASS] service coverage: all 25 ...`/`RESULT: PASS`；门控绿。探针自身 fail-closed 由 `QEMU-046t` 已验收 |

**判决**：全部 finding 已处置（✅已修 5、❌不修 1〔附证据〕、⏸延后 1〔附理由〕）；**无未修 finding** ⇒ 状态置 **待验收**。

**关键实测复核**：`make test-semihost` EXIT=0（59s，五组成逐项见「完成区/验收结果」）；`run.sh` EVIDENCE: PASS（235s，27 断言）；`git status --porcelain -uall` = `M Makefile` + `M tools/integ/run_m5_e2e.py`（+ 本任务书），无越界、无残留。

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 核 25 服务/反向例/不回归 + 判决）

**一、证据脚本审核（`.work/evidence/INTEG-020t/run.sh`）**

逐行审核结论：

| 检查项 | 结果 |
|--------|------|
| `set -u`（未定义变量保护） | ✅ 行24 |
| EXIT trap（`restore_manifest`）兜底还原 | ✅ 行45-51 |
| `check()` 函数：`exp == act` ⇒ PASS / FAIL + `FAILS++` | ✅ 行53-61 |
| `nonzero()` 用 `-ne 0`（非硬编码 `==1`） | ✅ 行63 |
| **注入 A**：`sed` 改 `0x40`→`0x99`（仅匹配 `m5_semi_writec` 一行）→ `make test-semihost` 须非零 | ✅ 行111-122；sed 模式唯一匹配 |
| **注入 B**：`sed` 改 `"A"`→`"B"`（仅匹配 `m5_semi_writec` 一行）→ `make test-semihost` 须非零 | ✅ 行124-136；sed 模式唯一匹配 |
| 还原方式 = `cp` 备份 + `md5sum` 对账（**未用** `git checkout/restore/stash/show`） | ✅ 行105-107,119-122,133-136 |
| 注入自检 = `has_str` 确认文件确实被改 | ✅ 行113-114,127-128 |
| 结尾 = `exit 0` / `exit 1`（**无 `tee`**） | ✅ 行149-154 |
| 恢复后回绿检查 | ✅ 行139-143 |
| `final-manifest-md5` 校验 | ✅ 行143 |
| 可达 FAIL 路径：两条注入通道（exit-code / console）各自独立可失败 | ✅ 非恒真 |

**脚本判定：合格。**

**二、重跑证据脚本（真实输出）**

```
$ bash .work/evidence/INTEG-020t/run.sh
== INTEG-020t evidence: make test-semihost (five components) ==
RUN    make test-semihost => EXIT=0 (log: .work/log/integ/INTEG-020t-evidence.log)
CHECK  gate-green: expected=0 actual=0  [PASS]
CHECK  console-writec-file: expected=present actual=present  [PASS]
CHECK  console-write0-file: expected=present actual=present  [PASS]
EVID   /mnt/tao/DADAO-v5/.dadao/tests/m5-e2e/m5_semi_writec.console bytes:[ 41]
EVID   /mnt/tao/DADAO-v5/.dadao/tests/m5-e2e/m5_semi_write0.console bytes:[ 4f 4b 0a]
CHECK  gate-log-console-lines: expected=yes actual=yes  [PASS]
CHECK  probe-distinct-ids: expected=25 actual=25  [PASS]
CHECK  probe-required-ids: expected=25 actual=25  [PASS]
CHECK  probe-fullrun-coverage: expected=yes actual=yes  [PASS]
CHECK  driver-target-native: expected=yes actual=yes  [PASS]
CHECK  driver-chardev-file: expected=yes actual=yes  [PASS]
CHECK  driver-default-workdir-m5-e2e: expected=yes actual=yes  [PASS]
EVID   manifest md5 (before injection) = e1d5942f9ec2bd2ef6a76581b1a90005
CHECK  inject-A-changed-file: expected=yes actual=yes  [PASS]
RUN    injected exit-code => make test-semihost EXIT=2
CHECK  inject-A-fails-gate: expected=nonzero actual=nonzero  [PASS]
CHECK  inject-A-restored-md5: expected=e1d5942f... actual=e1d5942f...  [PASS]
CHECK  inject-B-changed-file: expected=yes actual=yes  [PASS]
RUN    injected console    => make test-semihost EXIT=2
CHECK  inject-B-fails-gate: expected=nonzero actual=nonzero  [PASS]
CHECK  inject-B-restored-md5: expected=e1d5942f... actual=e1d5942f...  [PASS]
RUN    after restore       => make test-semihost EXIT=0
CHECK  gate-green-after-restore: expected=0 actual=0  [PASS]
CHECK  final-manifest-md5: expected=e1d5942f... actual=e1d5942f...  [PASS]
EVID   git status --porcelain -uall:
EVIDENCE: PASS
$ echo $?  → 0
```

**27/27 断言全 PASS，EXIT=0。**

**三、独立注入（reviewer 自行执行，未复用 engineer 的注入方式）**

注入对象：`tests/llvm/codegen/m5/expected.yaml` 的 **`m5_semi_write0`** 的 `expected_exit_code`（`0x41` → `0x99`）。与 engineer 脚本注入的 `m5_semi_writec`（`0x40`→`0x99`）**不同**。

```
# 注入前快照
$ md5sum tests/llvm/codegen/m5/expected.yaml
e1d5942f9ec2bd2ef6a76581b1a90005  tests/llvm/codegen/m5/expected.yaml

# cp 备份
$ cp tests/llvm/codegen/m5/expected.yaml /tmp/opencode/INTEG-020t-review/expected.yaml.back

# 注入
$ sed -i 's/expected_exit_code: 0x41/expected_exit_code: 0x99/' tests/llvm/codegen/m5/expected.yaml
$ grep -n 'expected_exit_code: 0x99' tests/llvm/codegen/m5/expected.yaml
58:    expected_exit_code: 0x99
$ git diff tests/llvm/codegen/m5/expected.yaml
-    expected_exit_code: 0x41
+    expected_exit_code: 0x99

# 门控验证：须非零退出
$ make test-semihost
  FAIL  m5_semi_write0  expected=153 actual=65 exit=65  (rc=65 != expected 153)
  console m5_semi_write0  expected=b'OK\n' actual=b'OK\n' match (byte-exact)
Results: 9/10 passed, 1 failed
test-semihost: FAIL (forward/permission rc=1)
$ echo $?  → 2

# 还原
$ cp /tmp/opencode/INTEG-020t-review/expected.yaml.back tests/llvm/codegen/m5/expected.yaml
$ md5sum tests/llvm/codegen/m5/expected.yaml
e1d5942f9ec2bd2ef6a76581b1a90005  tests/llvm/codegen/m5/expected.yaml
$ git diff tests/llvm/codegen/m5/expected.yaml
（空——无残留）

# 回绿验证
$ make test-semihost
Results: 10/10 passed, 0 failed
test-semihost: PASS (forward + permission + 25-service + no-regression + INTEG registration)
$ echo $?  → 0

# 最终快照对账
$ git status --porcelain -uall
（空）
$ md5sum tests/llvm/codegen/m5/expected.yaml
e1d5942f9ec2bd2ef6a76581b1a90005
```

**注入前 md5 = 注入后还原 md5 = `e1d5942f9ec2bd2ef6a76581b1a90005`；git status 干净；注入→FAIL→还原→回绿 循环完成。**

**四、门槛五组成逐项独立核验**

| 组成 | 验收命令 | 真实输出/退出码 | 判定 |
|------|---------|---------------|------|
| ① 正向 | `make test-semihost` | EXIT=0；10/10 passed（5 semihosting + 4 cfx + 1 trap）；bootrom(`-bios`)+bin 经 `-semihosting`；console：`writec`=41("A")、`write0`=4f4b0a("OK\n")、`write`=空(host file)；≥3 类覆盖 ✓ | ✅ |
| ② 权限反例 | 同上（含 4 例 cfx 级） | `m5_perm_reserved_illi` exit=80 cause=ILLI、`m5_perm_mask_illi` exit=81 cause=ILLI、`m5_perm_unimpl_cfxreg` exit=82 cause=CFXREG、`m5_perm_badcombo_cfxreg` exit=83 cause=CFXREG → 4/4 | ✅ |
| ③ 服务表覆盖 | `python3 min_rom_probe_046t.py --list` | `distinct service ids covered: 25` / `required service ids: 25`；全量跑 `[PASS] service coverage: all 25 service ids exercised` / `RESULT: PASS`；探针 SVC_TABLE=25 条、SERVICE_IDS=25 个（Python 实测） | ✅ |
| ④ 不回归 | `make test-elf` / `make test-codegen` / `make check` / `make check-lit` | test-elf EXIT=0 (5/5)；test-codegen EXIT=0 (15/15)；check EXIT=0 (`repository checks: PASS`)；check-lit EXIT=0 (62/62) | ✅ |
| ⑤ INTEG 开闭 | 完成区「遗留问题」段 | 门槛名=`make test-semihost`；结果=EXIT=0（五组成全绿）；证据路径=`INTEG-020t-*.log` + `run.sh`；产出=`Makefile::test-semihost` + `run_m5_e2e.py` | ✅ |

**五、harness stdio 落定核验**

| 检查项 | 证据 | 判定 |
|--------|------|------|
| `-semihosting-config` 由驱动传（非 Makefile） | `run_m5_e2e.py:255` 含 `target=native,chardev=semi`；`Makefile` grep 0 命中 | ✅ |
| `target=native` 显式 | 同上 | ✅ |
| console 落点 = chardev 文件（`.dadao/tests/m5-e2e/<stem>.console`） | QEMU 实际调用含 `-chardev file,id=semi,path=...m5-e2e/<stem>.console` | ✅ |
| 比对 = 逐字节精确 | `run_m5_e2e.py:293` `res.console_ok = (console == want)`；注入 B 验证 `MISMATCH` 可触发 | ✅ |
| Makefile 不重复传 `-semihosting-config` | `grep -c semihosting-config Makefile` = 0 | ✅ |

**六、门控不破坏**

| 命令 | 退出码 | 判定 |
|------|--------|------|
| `make check` | EXIT=0 | ✅ |
| `make check-no-residue` | EXIT=0 | ✅ |

**七、未越界（git diff b26f426..HEAD）**

4 文件，与完成区声明一致：
- `.tao/tasks/integ/INTEG-020t-*.md`（任务书）
- `.tao/tasks/integ/INTEG-021m-*.md`（里程碑任务书修正）
- `Makefile`
- `tools/integ/run_m5_e2e.py`

`spec/` 交集 = 空；`contracts/`、`components/` 未触；`.dadao/**`、`.work/**` 未入库。

**八、`tests/e2e/lit/**` 未改**

`git diff b26f426..HEAD -- tests/e2e/lit/` = 空。判定「不适用」成立：唯一 E2E 载体是 `make test-semihost`（复用 `run_m5_e2e.py`），加 lit 会重复 pipeline 且引入 lit→bootrom 隐式耦合；`check-lit` 62/62 未破。

**判决：Accepted**

全部8项验收标准通过：证据脚本合格（27/27 断言全 PASS）；独立注入（改 `m5_semi_write0` 期望退出码）成功触发 FAIL→还原→回绿；门槛五组成逐项独立核验全绿；harness stdio 与实现一致；`make check`/`check-no-residue` 未破；git diff 范围无越界。

#### architect 前置风险评估（QEMU-047t 遗留；2026-10-08，**只追加**，**待用户裁定**）

**背景**：`QEMU-047t` 选 **`ADR-0004 D2.3` 路径 B（raw-bin 双镜像）**——bootrom 经 `-bios` 载入 ROM 基址、应用 flat bin 经 `-kernel` 载入**旧 RAM 段**；**未实现「`-bios` bootrom + ELF 应用」组合**。实测（`.work/source/qemu/hw/dadao/dadao-machine.c`）：kernel 为 ELF 时走**路径 A 并整体忽略 `machine->firmware`**（无 `-bios`、PC=`e_entry`）；`dadao_load_regions[]` 仍仅 `{旧 RAM 0xffff_0000_0000, ROM 0xffff_ffff_0000}`，**未含 RAM@0**。

**（1）是否确为门槛前置缺口（实测核实）**

- 门槛正向组成原文（`milestones.md` M5 段 / `INTEG-019k` §第 2 轮裁定 9）= **「bootrom + 单/多 TU ELF 经 `-semihosting`、console 捕获、`SYS_EXIT` 码」**；本任务书「输出 1」「验收 1」同义复述。
- `ADR-0004`（`R1`）：`-bios` bootrom 路径与既有 M4 ELF 路径（`D2.2/D2.3` **路径 A，不用 `-bios`**）**并存、非替代**；`D2.3 路径 A` 正文明确「本路径**不使用**外部 `-bios` ROM blob」。⇒ **「`-bios`+ELF」组合语义未被任何 ADR 定义。**
- 现网三条可用路径：**(a) 路径 B** = bootrom + raw-bin（`QEMU-047t` 已实现）——**非 ELF**（手工 `.S` → `objcopy` flat，未过 `llc`/`ld.lld`、无多 TU）；**(b) 路径 A** = ELF 单独（**无 bootrom**；段须落 `dadao_load_regions[]` 已列区域 = 旧 RAM/ROM）；**(c) 「`-bios`+ELF」组合 = 不存在**。
- **结论**：**按字面耦合读**（bootrom 与单/多 TU ELF 同为一例）⇒ **确为门槛前置缺口**：(a) 缺「ELF」、(b) 缺「bootrom」、(c) 未实现，无任一现成路径可同时满足两者。**按拆分读**（正向含两个独立子例）⇒ ELF 子例可由路径 A 满足（semihosting 在译码层短路、与 cfx 无关，**不依赖 bootrom 初始化**）、bootrom 子例仅 raw-bin；但此时 ELF 子例**未经 SEE 初始化**，与 M5「SEE/HEE 运行环境」目的不符。**判据取舍待用户裁定。**

**（2）选项（代价 / 影响面）**

- **A（另立任务，串于 `QEMU-047t` 与 `INTEG-020t` 之间）**：扩 `dadao_load_regions[]`（+RAM@0）+ 定义「`-bios`+ELF」组合加载/入口约定（复位 PC=`0xffff_ffff_0000`、bootrom 先跑、初始化后跳 ELF `e_entry`；须定 `e_entry` 传递方式）+ 验证（含反例）。
  - 代价：新任务书 + `components/qemu/**` 补丁 + 重 `build-qemu`（5–20 min）；**新增组合语义属加载模型 / 外部契约变更 ⇒ 须 ADR 修订且逐条经用户确认**（`AGENTS.md`「ADR 逐条确认」）。
  - 影响面：`INTEG-020t` 依赖 += 新任务；`QEMU-048m` 关联任务 += 新任务；M5 任务数 +1；可能需 `check-interface` 断言更新。
- **B（调整 M5 门槛正向为 raw-bin 组合，保持现状）**：正向 = 「bootrom（`-bios`）+ raw-bin 应用经 `-semihosting`」。
  - 与 `R1`「并存」的关系：`R1` 并存**本就不含「组合」**语义 ⇒ 门槛不应要求组合 ⇒ **与 `R1` 自洽、无需改 ADR/组件**。
  - 代价：改门槛口径（`milestones.md` M5 段 + `INTEG-019k` 裁定 9 + 本任务书「输出 1」/「验收 1」）——**属规范/门槛变更 ⇒ 须用户裁定**。
  - 损失：「多 TU ELF」在 M5 门槛正向**不再被 E2E 覆盖**（多 TU ELF 仅由 M4 `test-elf` 覆盖，**不带** semihosting/bootrom）。
- **C（其它）**：**C1（并入本任务）**——把扩表 + 组合语义并入 `INTEG-020t`；本任务已重（E2E+harness+门控+lit+`make check` 收口），再叠组件补丁/组合语义/重构建 ⇒ 违反 Do-One-Thing、增大阻塞面 ⇒ **不推荐**。**C2（仅扩 `dadao_load_regions[]`+RAM@0，不定义组合）**——使路径 A 的 ELF 段可链进 RAM@0，但**仍无 bootrom** ⇒ 门槛正向「bootrom」仍缺，组合缺口**只解一半** ⇒ **不推荐作最终方案**。

**（3）建议（**待用户裁定**，架构师不擅自定）**

- **倾向 A**（若用户确认门槛正向按字面耦合读）：唯一能同时满足「bootrom」+「单/多 TU ELF」且**保留 `R1` 并存**（新增第三条组合路径，不删路径 A/B）的方案；与门控收口（`INTEG-020t`）解耦，合 Do-One-Thing。**但须先由用户裁定「是否承认『`-bios`+ELF』为门槛前置」，并逐条确认组合加载语义的 ADR 决策**，据此才可建任务 / 改 ADR。
- **次选 B**（若用户接受 M5 门槛正向不含组合、且「多 TU ELF」不在 M5 门槛 E2E 覆盖）：最小改动、零组件补丁、零回归风险，但降低门槛正向覆盖度。
- **本评估**：只写评估与选项；**未改任务范围、未动 `spec/`、未建新任务、未立 ADR**——均**待用户裁定后再行**。

#### architect M5 范围简化落纸（2026-10-08，用户裁定；只追加）

**背景**：上「architect 前置风险评估」（`QEMU-047t` 遗留）判「`-bios`+ELF 组合缺口」为**可能 M5 门槛前置**、倾向选项 A，**待用户裁定**。用户本轮就此裁定 → **M5 范围简化**（口径与上评估**选项 B** 一致：M5 门槛正向改为 bootrom + bin，与 `ADR-0004 R1`「并存」自洽；组合移 M6）。

**用户原话（逐字落盘；`AGENTS.md`「用户裁定落盘」/`lessons §7.3`）**：

> 「确实，这是两个分开的事情，用bios的时候，直接接bin，也就是objdump后的测试程序；而用elf的时候，则不需要bootrom，只需要semihosting即可。我们简化一下M5本身的任务目标，只做bootrom+bin的情况；elf加载放在M6，与完整LLVM的任务一起进行；你觉得呢」

**四条理解（主会话转达；architect 核对：与原话一致，无出入）**：

1. **M5 门槛正向**改为：`-bios <bootrom>` + **bin 应用**经 `-semihosting`（console 捕获 + `SYS_EXIT` 码）；原「单/多 TU ELF」用例**移 M6**。
2. **M4 既有 `test-elf`（path A：ELF、不用 bootrom）保留**为**不回归项**（不撤、不改）。
3. **`-bios`+ELF 组合 / ELF 加载器扩展（`dadao_load_regions[]`+RAM@0）/ 组合入口语义 ⇒ 移 M6**；**M5 不做**；**本阶段不立 ADR**（**推迟至 M6**，现只登记待办 + 理由）。
4. **连带**：`TESTCASES-033t` 改以 **bin 形态**承载；`TESTCASES-034t` 口径不变；`QEMU-049t` 挂到 `QEMU-047t` 的「ELF loader 未含 RAM@0」前置风险**改挂 M6**；`RAM@0` **step2（旧向量迁移）随 M6**。

**本任务受影响落点（已改）**：接口规范「门槛」/输出 1、验收 1——正向由「bootrom + 单/多 TU ELF」→「bootrom（`-bios`）+ **bin**」；**M4 `test-elf`（path A）仍为不回归项**（验收 4/6 不变）。

**ADR 推迟至 M6**：**本任务不涉组合 ADR**——「`-bios`+ELF 组合」加载/入口语义属加载模型/外部契约，**ADR 决策推迟至 M6**（`ISS-168`）；**M5 阶段不立 ADR**。

**未改范围**：本轮**未动 `spec/`**（本文件亦无 `spec/` 改动）；上「architect 前置风险评估」为**历史记录，保留不改**（只追加本节）。

#### 主会话判定落纸（architect，2026-10-08，只追加）

**背景**：`TESTCASES-033t` 审阅记录「下发前预检修订」末「**供裁定**」第 3 项登记——本任务输出 1 曾举 `run_semihost_e2e.py` 为例，与 `TESTCASES-033t` 产出的 `tools/integ/run_m5_e2e.py` 重复。主会话本轮**判定**：**去重、复用 `run_m5_e2e.py`**（属去重、非新增范围）。

**判定 3（`tools/integ/` 驱动复用）— 已落纸**

- **判定原话（主会话）**：「`INTEG-020t` 的输出 1 若举 `run_semihost_e2e.py` ⇒ 改为**复用 `tools/integ/run_m5_e2e.py`**（**只追加/最小改**，并在其审阅记录说明依据）。」
- **依据**：`run_m5_e2e.py` 由 `TESTCASES-033t` 产出（读 m5 清单 → 自有工具链编 bin → `qemu -bios <bootrom> -kernel <bin> -semihosting-config …` → 逐例比对 → `--inject` 反例自检）；本任务职责 = `make test-semihost` 接线 + harness stdio 捕获 + 门控收口 ⇒ **在其上追加/最小改**即可（DRY），**不另建 `run_semihost_e2e.py`**。
- **改法**：输出 1 的「（如 `run_semihost_e2e.py`）」→「（**复用 `tools/integ/run_m5_e2e.py`**〔`TESTCASES-033t` 产出〕，**只追加/最小改**，**不另建 `run_semihost_e2e.py`**）」。

**边界**：本轮仅改**本任务书**（输出 1 + 本审阅记录）；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`/`Makefile`；未新增/删除任务。

#### 口径全局对齐（architect，2026-10-08）

**依据**：已确认的 **`ADR-0020 D9`**——M5 权限范围只做 `cfx0/1/2/3/63`；`NUPERM/NJPERM/NSPERM/NHPERM` 属 `DADAO-12 §2.2` **PTBR 权限层、不在 M5**；**M5 可观测的权限反例 = cfx 级**：`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕。**性质 = 与既定决策的一致性修正，非新增范围**。

**逐处改动（本文件）**：

1. 接口规范「门槛」组成 ②（:18）：`未授权模式 ⇒ NUPERM/NJPERM/NSPERM/NHPERM` → **cfx 级 `ILLI`/`CFXREG`**（保留 `NUPERM…` 出处说明）。
2. 验收标准 2「权限反例」（:40）：同口径改（cfx 级 `ILLI`/`CFXREG` + 保留 `NUPERM…` 出处说明）。

**边界**：本轮仅改本任务书上述 2 处 + 本审阅记录；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`/`Makefile`；未新增/删除任务。

#### 下发前预检修订（architect，2026-10-08，只追加）

**背景**：本任务下发前预检发现两处缺口——**F1（必改）**：验收 3「25 服务各 ≥1 例」**未指明落点**；**F2（顺带核实）**：输出 2 对「`-semihosting-config` 由谁传 / console 捕获落点与比对方式」**尚未落定**。

**（F1）「25 服务覆盖」来源 —— 选定方案 A（探针承担），理由**

- **事实（实测）**：`TESTCASES-033t` 的 L3 向量 `tests/llvm/codegen/m5/expected.yaml` 仅含 **5 例** semihosting（`WRITEC`/`WRITE0`/`WRITE`/`EXIT`/`EXIT_EXTENDED`）；**25/25 服务覆盖**目前仅存在于 **`QEMU-046t` 探针 `tools/qemu/min_rom_probe_046t.py`**（实测 `python3 tools/qemu/min_rom_probe_046t.py --list` → 末两行 `distinct service ids covered: 25` / `required service ids: 25`，`RC=0`；全量跑时 `svc_*` 逐服务 ≥1 例、缺任一即 `[FAIL] service ids not covered` 非零退出）。
- **选定 = 方案 A**：门槛 ③ 的「服务表覆盖」**由 `tools/qemu/min_rom_probe_046t.py` 承担**（探针**全量跑**、逐服务 ≥1 例 + 覆盖计数断言 25、fail-closed）；**integ 侧 E2E（`run_m5_e2e.py`）只保证 console ≥3 类**（`WRITEC`/`WRITE0`/`WRITE`）+ **`EXIT`/`EXIT_EXTENDED`** 的端到端链；`make test-semihost` **调用该探针**（`--qemu $(QEMU_BIN)`，与 install 根一致）。
- **理由（DRY/最小）**：① 探针**已存在、已入库**（`0fba5eb`）、25/25 覆盖**已实测**、覆盖计数**机器可判** ⇒ 直接复用为门槛 ③ 落点**零新增向量/oracle**；② 方案 B（本任务扩 L3 向量至 25 例）须**同步 `expected.yaml` + 独立 oracle**（`tools/testcases/validate_m5_vectors.py`），成本高、且**触及 `TESTCASES-033t` 已 `Accepted` 的向量边界** ⇒ 非最小。
- **跨模块引用 QEMU 探针的可接受性/依据**：门槛 ④ 本已聚合跨模块门控（`test-elf`/`test-codegen`/`check`/`check-lit`）⇒ 门控「聚合既有各模块门控」是**既定范式**；`min_rom_probe_046t.py` 属 **`QEMU-046t` 已入库产物**（非本任务新建）、其 **25 服务覆盖即 `QEMU-046t` 的交付断言**（`milestones.md` M5 段 `QEMU-046t` 条）⇒ 在本任务门控中调用它是**复用既有已验收产物**，不新增跨模块契约、不改 `spec/`/`components/`。
- **未改门槛组成**：组成 ③ 文字（「服务表各条至少 1 例」）**不变**——本修订**只补落点**（原缺）⇒ `INTEG-019k`/`milestones.md` **无需同步**（最小改动；已核：两者门槛 ③ 表述与本任务书一致、本就不含落点承诺）。
- **未选 B 的记录**：见上「理由 ②」。

**（F2）harness stdio 口径 —— 补落定（原已明确处标注"已足够明确"）**

- **`-semihosting-config` 由谁传 = 驱动脚本**：实测 `tools/integ/run_m5_e2e.py`（`TESTCASES-033t` 产出）**已在驱动内**传 `-semihosting-config enable=on,target=native,chardev=semi` + `-chardev file,id=semi,path=<console>` ⇒ **落定 = 驱动脚本传、`Makefile` 只负责调用驱动**（与输出 2 原「建议驱动传参」一致；`ADR-0020 D7`：`target=`/`chardev=` 由 harness 提供、`native` **显式开启**）。
- **console 捕获落点/比对方式**：捕获 = **chardev 文件**（`-chardev file,...`），落点 = 驱动 `--work-dir` 下 `<stem>.console`（**默认 `.dadao/tests/m5-e2e/`**，经 `paths.py` 解析，符合 `INFRA-048t`「`.dadao/tests/` 下」口径）；比对 = **逐字节精确**（`console != expected_console` ⇒ FAIL），期望串来自 `expected.yaml` 的 `expected_console`（独立派生）。
- **修正原落点表述**：原输出 2 写「落点 = `.dadao/tests/semihost-e2e/`」与实际复用驱动（`m5-e2e`）**不一致** ⇒ 改为「驱动 work dir 下（默认 `.dadao/tests/m5-e2e/`）」，**不另起 `semihost-e2e/`**（复用既有驱动、最小改）。

**边界**：本轮**仅改本任务书**（门槛 ③ / 输出 1/2/3 / 验收 3/5 + 本审阅记录）；**`spec/` 交集为空**；**未改 `contracts/**`/`components/**`/`Makefile`/`tools/**`**；**未新增/删除任务**；`INTEG-019k`/`milestones.md` **未改**（门槛组成无变更）。

#### 第 1 轮 architect 提交（WIP）（2026-10-08，只追加）

**档位**：**`WIP:`**——engineer 已置 `待验收`、reviewer **尚未验收**（未判 `Accepted`）⇒ 按「提交分档」作 `WIP` 本地提交。

**提交信息**：`WIP: INTEG-020t semihosting E2E + harness stdio 捕获 + make test-semihost 门槛收口（待 reviewer 验收）`（**只 `commit`，未 `push`**）。

**文件集对账**（完成区「修改文件」+ 任务范围 vs 实际 staging）：

- **应提（完成区声明，均入）**：`Makefile`、`tools/integ/run_m5_e2e.py`、本任务书。
- **另附（本轮 A 修订，经主会话指示）**：`.tao/tasks/integ/INTEG-021m-M5-integ里程碑.md`——就地更正其「核验」旧驱动名 `tools/integ/run_semihost_e2e.py` → `tools/integ/run_m5_e2e.py`（依据：本任务「复用 `run_m5_e2e.py`、不另建」判定）；**相对本任务「修改文件」声明属新增项，已披露**。
- **漏提**：无。
- **多提**：无（无任务范围外文件）。
- **越界**：无——**未触 `components/**`**；**`spec/` 交集为空**；`.dadao/**`、`.work/**` 均**未入库**（在 `.gitignore` 内）。

**边界**：本记录**只追加**；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`。

#### 第 1 轮 architect 提交（正常）（2026-10-08，只追加）

**档位**：**正常提交**（无 `WIP:` 前缀）——reviewer 已判 **`Accepted`**（见上「第 1 轮 reviewer 验收」），engineer/reviewer 返回后由 architect 判断并本地提交（`AGENTS.md`「提交分档与角色」）。

**提交信息**：`INTEG-020t semihosting E2E + harness stdio 捕获 + make test-semihost 门槛收口（reviewer Accepted）`（**只 `commit`，未 `push`**）。

**文件集对账**（完成区「修改文件」+ 本记录 B 知识沉淀 vs 实际 staging，**显式逐个路径 staging，未用 `git add -A`**）：

- **应提（完成区「修改文件」声明，均已入库）**：`Makefile`、`tools/integ/run_m5_e2e.py`、本任务书 `.tao/tasks/integ/INTEG-020t-*.md`。
- **本轮新增（B 知识沉淀，经主会话指示，已披露）**：`.tao/knowledge/lessons.md`（+§7.24/+§8.18）、`.tao/knowledge/changelog.md`（+1 行）、`.tao/knowledge/milestones.md`（M5 段 +「M5 门槛达成」条）、`.tao/knowledge/MEMORY.md`（M5 摘要行追加 `INTEG-020t`）。
- **另附（`WIP` 轮已提交）**：`.tao/tasks/integ/INTEG-021m-M5-integ里程碑.md`（旧驱动名更正，已在 `WIP` 提交内、本轮无新改动）。
- **漏提**：无。
- **多提**：无（无任务范围外文件）。
- **越界**：无——**未触 `components/**`**；**`spec/` 交集为空**（`git diff --cached --name-only` 与 `spec/` 清单交叉为空）；`.dadao/**`、`.work/**` 均**未入库**（在 `.gitignore` 内）；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`*.preinject` 残留。

**边界**：本记录**只追加**；**未写死 SHA**、未改写既有「完成区」「审阅记录」；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`。

#### 主会话统一验收报告（`/complete`，2026-10-08）

- **reviewer**：`Accepted`。证据脚本重跑 **`EVIDENCE: PASS`（27/27）**；**独立注入**（改 `m5_semi_write0` 期望退出码 `0x41→0x99`）⇒ `make test-semihost` **EXIT=2** ⇒ `cp`+`md5` 还原 ⇒ 回绿；**未用** `git show … > …`（`lessons §7.20` 合规）。
- **architect 交叉复核**：**通过**。独立核：**五组成真实**——① 正向 `10/10`（逐例命令行**全含 `-bios`** + bin；console 逐字节 `A` / `OK\n` / 空；`SYS_EXIT` 码）；② cfx 级权限反例 `4/4`；③ **服务表 `25/25`**（`min_rom_probe_046t.py`，`SVC_TABLE`/`SERVICE_IDS` 独立计数、缺一即 `return 1` fail-closed）；④ 不回归作 **make 前置**（`test-semihost: … test-elf test-codegen check`）；⑤ INTEG 开闭材料齐。`-semihosting-config` **由驱动**传（`Makefile` 未重复传）；console 落 `.dadao/tests/m5-e2e/`、**逐字节**比对；`spec/` 交集空、未触 `components/`。
- **交付（M5 门槛）**：**`make test-semihost` EXIT=0（59s）** —— 门槛名/五组成/harness stdio 捕获细节（传参方 = 驱动、落点、比对方式）已落定；`INTEG-021m` 旧驱动名 `run_semihost_e2e.py` → **`run_m5_e2e.py`** 已修；`tests/e2e/lit/**` 判定不适用（理由：唯一 E2E 载体即该目标，加 lit 会重复 pipeline 且引入耦合）。
- **知识沉淀**：`lessons §7.24` + **`§8.18`**：① **GNU make recipe 失败返回 2（非 1）** ⇒ 注入判据须 `-ne 0`；② **「不回归」可作门控前置链**（机械保证「任一类不符即非零」）；③ **跨模块复用已验收产物**（QEMU 探针承担 25 服务覆盖）的判据。
- **M5 门槛结论与证据路径**（供 `INTEG-021m` 核验 / M5 收口）：`make test-semihost` **EXIT=0**；日志 `.work/log/integ/INTEG-020t-{test-semihost,test-elf,test-codegen,check,check-lit}.log`、证据 `.work/evidence/INTEG-020t/run.sh`。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
