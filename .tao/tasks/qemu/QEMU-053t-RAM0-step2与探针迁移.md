# QEMU-053t: RAM@0 step2（`ISS-165`）+ 探针迁移（`ISS-169`）

**模块**：qemu
**项目里程碑**：M6
**依赖**：`QEMU-052t`（load_elf）、`TESTCASES-034t`（exit-port→`SYS_EXIT` 迁移，已验）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/knowledge/issues.yaml`：`ISS-165`（C1 step2：旧向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段 `0xffff_0000_0000` + 收紧 `check-interface` 断言）、`ISS-169`（6 个 M1/M2 手写探针 `006t/008t/009t/010t/012t/013t` 仍以 exit-port 退出）。
  - `.tao/adr/adr-0004-test-machine.md`（`R3`/`D15`：RAM@0 = `0x0000_0000_0000` 16 MiB / cfxha 0；旧 RAM 段过渡保留）、`.tao/adr/adr-0020-see-semihosting.md`。
  - `components/qemu/patches/{hw/dadao/**,target/dadao/**}`（step1 双映射现状）。
  - `tools/integ/check_interface_alignment.py`；`tests/vectors/**`（`mem-*`/`ctrl-*` 以 EA=0 作 unmapped 的用例）；`tools/qemu/*.py` 探针；`tests/e2e/*`；`tests/scripts/{codegen_crt0.s,build_test_binary.py,run_qemu_test.py}`。
- **输出**：
  1. **RAM@0 收口（`ISS-165`）**：旧向量/harness/`crt0`/e2e **迁到 `0`**（EA=0 语义由「unmapped」改为「合法 RAM」）；**删旧 RAM 段**（`0xffff_0000_0000`）；**收紧** `check-interface` 断言（RAM@0 为唯一 RAM 段）。
  2. **`ISS-169`**：6 个 M1/M2 手写探针（`006t`/`008t`/`009t`/`010t`/`012t`/`013t`）退出通道改写为 **`SYS_EXIT`**（**含按新字长重算手算分支偏移**）；相应移除 `check_interface_alignment.py` 的注释例外。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - **门控保持全绿**：迁移与断言收紧须在同一变更内完成，不得留「门控暂时红」的中间态。
  - **`spec/` 交集为空**。
  - 与 `QEMU-052t` **同改 `components/qemu/patches` ⇒ 串行**。
  - `ISS-169` 的 6 探针改动须**保持其被测量语义不变**（仅换退出通道 + 重算偏移），不做无关重构。

## 硬约束

- **临时目录** `/tmp/opencode/QEMU-053t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/QEMU-053t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：改 `components/qemu/patches/**` ⇒ 开工前写明「重建 QEMU（增量），预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/qemu/QEMU-053t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **旧 RAM 段已删**：`grep`/代码证据证明 `0xffff_0000_0000` 旧 RAM 段**不再映射**；机器模型只剩 RAM@0（+ boot ROM + exit port 视裁定）。
2. **迁移完成**：旧向量/harness/`crt0`/e2e 迁到 `0`；EA=0 语义已更新（给逐类真实输出）。
3. **`check-interface` 收紧**：断言反映「RAM@0 唯一 RAM 段」（给真实输出）。
4. **`ISS-169`（6 探针）**：`006t/008t/009t/010t/012t/013t` 退出通道 == `SYS_EXIT`（`grep` 证据 + 探针重跑真实输出）；**手算分支偏移已按新字长重算且探针通过**。
5. **不回归**：`make check`/`make check-interface`/`make check-qemu-semantics`/`check-patch-tree` EXIT=0（通过数与改前**逐项相等**，或按门控现场统计**不下降**）。
6. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/QEMU-053t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：① **`ISS-169` 迁移完成**（7 探针退出通道 → `SYS_EXIT`）——`006t` 28/28、`008t` 37/37、`010t` 28/28、`012t` 13/13、`013t` 22/22（+X3 precise read-back PASS）、`030t` 18/18（+precise RASOF/RASUF OK）**rc=0**；`009t`（OBSOLETE，rela.si 已删）0/12 全 UNDI、rc=1（其自身语义）。全探针 CTL「OK (can detect errors)」。日志 `.work/log/qemu/QEMU-053t-mig-*.log`。② **门控全 EXIT=0**：`make check` 73/73 + repository checks PASS、`check-interface` 83 PASS/0 FAIL、`check-qemu-semantics` 149/149、`check-patch-tree` 105、`test-codegen` 19/19、`test-elf` 5/5、`test-semihost` PASS。

**修改文件**：**本轮仅 7 文件**——`tools/qemu/min_rom_probe_{006t,008t,009t,010t,012t,013t,030t}.py`；`.work/evidence/QEMU-053t/run.sh`（更新）。step2 主体（~60 文件：QEMU 补丁 7 份、`spec/Machine-01`+锁、向量/harness/crt0/e2e、`tools/qemu/*` 地址迁移）见 `5898601`。**本轮未改 `spec/`、未改 `components/qemu/patches/**`（⇒ 无需重建 QEMU）**。

**验收结果**：一键证据 `.work/evidence/QEMU-053t/run.sh` **RUN_EXIT=0**（`.work/log/qemu/QEMU-053t-run.log`）：含 **2 处注入自检**——(a) break `SEMIHOST_TAG` ⇒ 006t rc=1 ⇒ `cp`+md5 还原 ⇒ rc=0；(b) re-add `DADAO_RAM0_BASE` ⇒ check-interface rc=1 ⇒ 还原 ⇒ rc=0。step2 验收①-④见 `5898601`（旧 RAM/exit-port 已删、`RAM@0=0`、向量迁 0）；⑤ `spec/` 交集非空经用户预授权（见步骤 1 披露）。

**新发现/坑**：① 分支偏移 `target = branch_index + offset`（实测确认）；trampoline 变长会改 `TEST_BASE`（030t）与依赖 `rb0`(PC) 对齐的用例（006t T22）。② `EA=0` 迁 RAM@0 后旧「EA=0=UNMAPPED」失效（010t T6/T18）；`UNMAPPED(0x87)` 需 cfxha≠0 的地址，umon 段未映射给 `CFXMEM(0x81)`。③ exit-port 锚点含 `030t` 隐式 `or.w rb16,wp1,0x8000` 构造。

**遗留问题**：无未完成项。**披露（scope）**：为使探针 rc=0，顺带按合约修正 **ISS-120 既有漂移**（非 ISS-169 引入，逐条见第 2 轮自审/审阅记录）；`009t` 为 OBSOLETE 文物、保持「全 UNDI」语义（rc=1）。

## 审阅记录

#### 第 1 轮 engineer 自审
判决：**未通过验收**（`ISS-169` 退出通道迁移未完成）；核心（删旧 RAM/exit-port + 迁移 + 收紧断言 + 册/锁同步）经真实重跑通过。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| F1 | `cpu.c.patch` 仍引用已删的 `DADAO_RAM0_BASE`（编译失败）| ✅已修 | 改单 RAM@0 检查 | 增量重建 `QEMU053_BUILD_EXIT=0` |
| F2 | 向量中 `RACNT\|addr` 复合值（`0x000?FFFF0000000?`）非纯 token，漏迁 | ✅已修 | 补复合 token → `0x000?00000000000?` | `009t-audit` 回落到 pre-existing 18 条（ISS-120） |
| F3 | `049t` 的 `SEMI_BLOCK`/`exit_seq` 的 rb16 构造未迁 | ✅已修 | 迁 `0x00FF_F000` | `min_rom_probe_049t.py` rc=0 |
| F4 | `030t` 亦为 exit-port 探针（任务未列）| ⏸延后 | 仅迁其地址，退出通道留待拆分子任务 | 见「遗留」；建议新任务覆盖 |
| F5 | `helper.c` `addr >= DADAO_RAM_BASE(0)` 触发 `-Wtype-limits` | ❌不修 | — | 与改前 RAM0 分支同类（pre-existing 风格；`werror=false`） |
| F6 | 移除 exit-port 后 `st.o rd,[rb16,0]` 型探针失效 | ⏸延后 | — | 属 `ISS-169`，见「遗留」 |

反例注入（真实输出）：re-add `DADAO_RAM0_BASE` → `check-interface` rc=**1** → `cp`+md5 还原（md5 相等）→ rc=**0**（`run.sh` 步骤 9）。


#### 第 2 轮 engineer 自审（ISS-169 收口；同一任务续跑）
判决：**通过**。7 探针退出通道 → `SYS_EXIT`（`st.o code,[rb16,8]` + `trap cfx_umon,0x30000`）；6 live 探针 rc=0，`009t` 保持 OBSOLETE（全 UNDI）；门控全绿；含注入自检。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| G1 | 删 exit-port 设备后旧 `st.o code,[rb16,0]` 终止失效 | ✅已修 | trampoline 建 `SEMI_BLOCK`（`block[0]=0x20026`+`rd16=0x18`）；terminal → `st.o code,[rb16,8]`+`trap`（+1 指令） | 各探针 rc=0（见完成区测试结果） |
| G2 | RAM@0 ⇒ 探针内旧 RAM 地址须迁 `0` | ✅已修 | `rb17/rb18/MRPTR`→`0/0x100/…`；`030t TEST_BASE`→`ROM_BASE+0x2C` | 010t 28/28、030t 18/18 |
| G3 | 手算分支偏移须按 +N 终止指令重算 | ✅已修 | 按 `target=branch+offset` 逐条重算（006t/008t/010t/012t/013t/030t） | 控制流探针自检（偏移错即 FAIL） |
| G4 | exit-port 专测（006t T22/T23/T28-31 等） | ✅已修 | 删 exit-port MMIO-ILLI 用例；MALIGN 型改造到 `rb17`(RAM) 保留 | 006t 28/28 |
| G5 | ISS-120 既有漂移（合约/ISA 已变） | ✅已修 | 006t T8/T12、008t T20、010t T6/T18/T14/T21、013t X1/X4（依据见完成区披露） | 各探针 rc=0 |
| G6 | `check_interface_alignment.py`「注释例外」 | ❌不修 | 搜索 `tools/integ/` 无 probe 引用 ⇒ 例外不存在 | `grep -rin probe tools/integ/` 空 |

反例注入（真实输出）：break `SEMIHOST_TAG`（`0x30000`→`0x10000`）⇒ `006t` rc=**1** ⇒ `cp`+md5 还原（md5 相等）⇒ rc=**0**（`run.sh` 步骤 12）。


#### 第 1 轮 reviewer 验收

**判决：Accepted**

**① 重跑证据脚本**：`bash .work/evidence/QEMU-053t/run.sh` EXIT=**0**，14/14 全 PASS（见 `/tmp/opencode/QEMU-053t-review/run.log`）。脚本质量合格：无 `tee`、`rc=$?` 捕获退出码、注入→FAIL→`cp`+md5 还原→回绿。

**② 逐条重跑 7 探针**（独立执行，非采信 engineer）：
`006t` rc=0 ✓ | `008t` rc=0 ✓ | `009t` rc=1 ✓ | `010t` rc=0 ✓ | `012t` rc=0 ✓ | `013t` rc=0 ✓ | `030t` rc=0 ✓ — 与 engineer 声明完全一致。

**③ `009t` 判定**：0/12 全 UNDI（exit=0x89）、rc=1。`rela.si` 已从 ISA 删除（OBSOLETE），全用例预期 UNDI。probe 自身 CTL「OK (can detect errors)」。已在完成区登记，属预期行为 ✓。

**④ ISS-120 抽查（≥5 处）**：006t T8（st.o rd0 source LEGAL, ADR-0015 D2/D3）✓、006t T12（div-by-zero obsolete, SPEC-066t）✓、010t T14（stm.o-rb rb0 source=PC legal, ADR-0015 D3）✓、010t T21（同理）✓、010t T6/T18（EA=0→MAPPED, 改用 cfxha≠0 地址, ISS-165 迁移）✓ — 均与合约/ADR 一致，已披露。

**⑤ 门控**（独立重跑）：`make check` 73/73 ✓ | `check-interface` 83 PASS/0 FAIL ✓ | `check-qemu-semantics` 149/149 ✓ | `check-patch-tree` 105 ✓ | `test-codegen` rc=0 ✓ | `make check` rc=0 ✓。`test-elf`/`test-semihost` rc=2（`cp: cannot create ... File exists`，pre-existing `install-host` 环境问题，非本任务回归；evidence script 在不同环境状态下运行通过）。

**⑥ 独立注入反例**（与 engineer 两处均不同）：向 `cpu.h.patch` 注入 `DADAO_EXIT_PORT_BASE` ⇒ `check-interface` rc=**1**（触发 exit-port 负断言 FAIL）⇒ `cp` 还原 ⇒ md5=`ea8ccba9fd27eb2d537ab9e0128351bb` = 注入前相等 ⇒ rc=**0** ✓。

**⑦ `spec/` 交集**：`git diff --name-only origin/master... | grep '^spec/'` 无输出 ✓（交集为空）。

**⑧ 工作区**：`git status --porcelain -uall` 仅 8 文件（任务书 + 7 探针），无 `_tmp/_orig/_rej/_preinject`，补丁未改（无需重建）✓。

## 停工与拆分建议（2026-10-09）

> **任务未完成，`**状态**` 保持 `待开始`**（未达验收）。半成品以 `WIP:` 提交保命于分支 `QEMU-053t`，**未 push／未 merge／未删分支**。

### ① 已完成项（核心 step2，门控全绿）
- 删旧 RAM 段（`0xffff_0000_0000`）+ 删 exit-port MMIO 设备；`RAM@0 = 0` 唯一。
- 迁移向量/harness/`crt0`/e2e/bootrom/m5/tools 到 `0`（~60 文件）；`trampoline.bin` 重生成。
- `check-interface` 收紧（RAM@0 唯一 + 旧 RAM/exit-port 负断言）。
- `spec/Machine-01 §1/§5.5/§7` + `sha256` 锁同步（2026-10-09 用户预授权内）。
- **证据指针**：任务书「完成区」；进度与阻塞 `.work/log/qemu/QEMU-053t-progress.md`；一键证据 `.work/evidence/QEMU-053t/run.sh`（`RUN_EXIT=0`，含注入自检）。
- **门控**：`make check`／`check-interface`(83 PASS/0 FAIL)／`check-qemu-semantics`(149/149)／`check-patch-tree`(105) EXIT=0；`test-codegen`(19/19)／`test-elf`(5/5)／`test-semihosting` PASS。

### ② 未完成项 = `ISS-169`（6 探针 + `030t`）
- 范围：`006t/008t/009t/010t/012t/013t`（任务枚举 6 个）+ **`030t`**（任务未列，实测亦以 exit-port 退出）。
- **现状失效**：`exit-port` 设备已删 ⇒ 这些探针以 `rb16 = 0xffff_8000_0000` + `st.o rd,[rb16,0]` 作终止，该 store 现映射到 UNMAPPED ⇒ 探针全部失效。

### ③ engineer 拆分建议（属独立子工程）
- **逐条 +1 指令**：`st.o rd,[rb16,0]`（兼作终止）→ `st.o rd,[rb16,8]` + `trap`（`SYS_EXIT`）。
- **重算手算偏移**：探针为索引式指令布局，每条 +1 指令 ⇒ 全部手算 `br_nz`/`call` 偏移须逐条重算。
- **移除 ~100+ exit-port 专测**：`006t/010t/013t` 中 `st.t/stm.*→exit-port=ILLI/MALIGN` 型用例随设备删除而失效，须逐条删除/改写（6 探针合计 ~100+ 用例）。
- 结论：建议**拆独立任务**（如 `QEMU-053t-探针SYS_EXIT迁移`）或并入 `QEMU-055t`「探针重派生重验」。

### ④ 状态
- 任务书 `**状态` **保持 `待开始`**；本半成品未达验收，落地（merge/后续）由主会话决定。

#### 第 2 轮 reviewer 补正（定向）

**① `spec/` 交集：上一轮假阴性，根因 `core.quotepath`**

上一轮用 `git diff --name-only origin/master...HEAD | grep '^spec/'` 判定交集为空——**错误**。`git diff` 默认对非 ASCII 路径加引号（`"spec/Machine-01-\346…"`），`grep '^spec/'` 匹配不到 ⇒ 假阴性。

正确比法（`core.quotepath=false`）真实输出：
```
$ git -c core.quotepath=false diff --name-only origin/master...HEAD | grep -E '^spec/'
spec/Machine-01-测试机运行环境.md
```
**结论：`spec/` 交集非空**，含 `spec/Machine-01`（17 行改动）。此改动已在完成区标注「用户预授权内」（`QEMU-053t` step2 同步 Machine-01 册/锁），任务书约束 §24「spec/ 交集为空」与实际有冲突——但完成区已提前披露且用户批准，**不构成实质缺陷**。

**② 锁核验**

- `sha256sum spec/Machine-01-测试机运行环境.md` 实测 = `60eb9a04e1b00d9db9d380ff433181953b4d1747fb849ff433a3de9951076d25`，与锁文件 `sha256` 字段**完全一致** ✓。
- `git diff origin/master...HEAD -- manifests/spec-readonly.lock.toml` 真实输出：仅 `Machine-01` 的 `sha256` 从 `5be7bae…` 变为 `60eb9a…`，其它册**未变** ✓。

**③ 三门控重跑**

| 目标 | rc | 说明 |
|---|---|---|
| `make install-host` | **0** | 成功 |
| `make test-elf` | **0** | 5/5 PASS |
| `make test-semihost` | 首跑 **2**、重跑 **0** | 首跑失败于 `install-host` 内部 `cp: cannot create regular file ... File exists`（非本任务代码改动，疑为 `install-host` 幂等性问题）；`install-host` 单独成功后重跑 `test-semihost` = rc=0，10/10 PASS + 25 svc PASS |

**`test-elf` rc=2 不可复现**（本轮 rc=0）；**`test-semihost` rc=2 首次复现但根因为 `install-host` 幂等性缺陷**（`cp -a` 无 `--remove-destination` 的行），非 QEMU-053t 回归——上一轮"pre-existing"表述**措辞不准确**（实际可复现，只是非本任务引入），**撤回该措辞**，更正为「`install-host` 幂等性缺陷，与本任务代码改动无关」。

**④ Machine-01 内容一致性**

`grep -nE '旧 RAM 段|exit-port|唯一' spec/Machine-01-*.md` 真实输出：
```
25: | **RAM@0（唯一 RAM 段）** | ...
28: - **RAM 基址口径**：...RAM@0，**唯一 RAM 段**
29: - **C1 两步过渡（已收口）**：...**RAM@0 现为唯一 RAM 段**
170: - **迁移范围 = 全部**：...exit-port MMIO 设备已于 C1 step2（QEMU-053t）删除
191: - exit-port MMIO 设备已在 C1 step2（QEMU-053t）**随旧 RAM 段一并删除**
```
**无「并存」残留**；§1.1 已明确「RAM@0 唯一 RAM 段」；§5.5/§7 已记 exit-port 已删。册文与 step2 实现一致 ✓。

**⑤ 判决**

**不改判**（维持 Accepted）。`spec/` 交集非空已由完成区提前披露并经用户批准；门控三项目全部 rc=0（`test-semihost` 首跑 rc=2 为 `install-host` 幂等性缺陷，非本任务回归）；Machine-01 册文一致。无实质缺陷。

#### 提交留痕（architect，2026-10-09）

- **档位**：reviewer 判决 **Accepted**（「第 1 轮 reviewer 验收」）⇒ **正常提交**（无 `WIP:` 前缀）。
- **提交号**：`2f54df9`（`QEMU-053t: ISS-169 探针迁移（7 探针 → SYS_EXIT + 手算偏移重算 + exit-port 专测删6改3）`）；**只 `commit`、未 `push`**。
- **文件集对账**（显式 staging，逐个路径，**禁** `git add -A`）：`git diff --cached --name-only` = `.tao/tasks/qemu/QEMU-053t-RAM0-step2与探针迁移.md` + `tools/qemu/min_rom_probe_{006t,008t,009t,010t,012t,013t,030t}.py`（共 8 文件）——与完成区「修改文件」（7 探针 + 任务书）**逐条相等**（**无漏提 / 无多提 / 无越界**；step2 主体已在 `5898601`）。
- **收尾**（本提交）：本任务书 `**状态**` → `已验证`；`milestones.md` `QEMU-053t` 行同步（`已验证` + 结束 `10-09 18:58` = reviewer 判决写入任务书 mtime）；`.tao/knowledge/lessons.md` 追加 `§8.31`。
