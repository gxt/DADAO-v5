# m15-testcases-016: `tests/ee-*` 文件名统一为 `<role>_<ee>` 规则

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-011`/`012`/`013`/`014`/`015`（ee-* 三目录已建立并集中完毕）、`m15-infra-001`（`machine_profile.py` 与 `ee-*/runtime.yaml` 已迁；**必须串行**，同改 tests 路径）
**可并行分片**：否（跨三目录 + 全仓引用）
**预估**：2–3 h
**档位**：中改
**状态**：待验收

## 背景（用户 2026-11-18）

`tests/ee-tiny/`、`tests/ee-user/`、`tests/ee-vast/` 建好后，目录已表达执行环境，但文件名仍混用机型前缀（`kaiwu-tiny*`、`inst-tiny`、`picolibc-tiny`、`tiny_*`、`dadao_*`、`dadao-*`），三目录规则不一致。

**用户裁定原话（2026-11-18）**：「1、我建议保留 tiny/user/vast 前缀或后缀；2、三个目录下的命名规则要一致」「run_asm_suite.py 是不是应该改为 run_inst」。

## 命名规则（本任务唯一判据）

1. 形式 **`<role>_<ee>.<ext>`**：角色在前、执行环境后缀 `_tiny` / `_user` / `_vast` 在后。
2. 同类以扩展名区分：`.S` 固件/载体、`.lds`/`.ld` 链接脚本、`.inc` 汇编宏、`.py` 驱动、`.s`/`.ll`/`.c` 载体。
3. 驱动脚本统一 `run_<scope>_<ee>.py`；gem5-se 非 `run_*` 的工具用 `gem5se_<scope>_<ee>.py`。
4. 同目录同角色并存时，用角色限定词插在扩展名前：`k0`（K0/K1 boot chain）、`semihost`、`smoke`。
5. **仅改文件名与引用路径，不改任何文件内容**（重命名文件逐字节不变；`git mv`）。
6. **本任务不改归属**：文件归哪个模块/里程碑由用户随后统一裁决。

## 改名清单（表列 51 个 `git mv` + 1 个 `git rm`；`README.md` 保持原名，`k0_README.md` 按 D1 删除）

### `tests/ee-tiny/`（22 改 / 0 保持）

| 旧 | 新 |
| --- | --- |
| `bootrom.S` | `bootrom_tiny.S` |
| `bootrom.lds` | `bootrom_tiny.lds` |
| `bootrom_app.S` | `bootrom_app_tiny.S` |
| `power.S` | `power_tiny.S` |
| `power.lds` | `power_tiny.lds` |
| `hmon.S` | `hmon_tiny.S` |
| `hmon.lds` | `hmon_tiny.lds` |
| `tiny_common.inc` | `common_tiny.inc` |
| `tiny_crt.S` | `crt0_tiny.S` |
| `tiny_smoke.S` | `smoke_tiny.S` |
| `tiny_smoke.lds` | `smoke_tiny.lds` |
| `semihost_msg.inc` | `semihost_msg_tiny.inc` |
| `semihost_smoke.S` | `semihost_smoke_tiny.S` |
| `semihost_smoke.lds` | `semihost_smoke_tiny.lds` |
| `kaiwu-tiny.lds` | `kernel_tiny.lds` |
| `kaiwu-tiny-app.lds` | `app_tiny.lds` |
| `inst-tiny.lds` | `inst_tiny.lds` |
| `picolibc-tiny.ld` | `picolibc_tiny.ld` |
| `picolibc_tests.py` | `run_picolibc_tiny.py` |
| `run_embench_e2e.py` | `run_embench_tiny.py` |
| `run_asm_suite.py` | `run_inst_tiny.py` |
| `run_semihosting_smoke.py` | `run_semihosting_tiny.py` |

### `tests/ee-user/`（16 改 / 1 保持）

| 旧 | 新 |
| --- | --- |
| `dadao-common.lds` | `common_user.lds` |
| `dadao-dyn.lds` | `dyn_user.lds` |
| `dadao_mem_runtime.ll` | `mem_runtime_user.ll` |
| `dadao_user_dyn_probe.c` | `dyn_probe_user.c` |
| `minimal_crt0.s` | `crt0_user.s` |
| `run_embench_user_suite.py` | `run_embench_user.py` |
| `run_libc_test_user_suite.py` | `run_libc_test_user.py` |
| `run_libc_test_smoke.py` | `run_libc_test_smoke_user.py` |
| `run_llvm_ts_smoke.py` | `run_llvm_ts_smoke_user.py` |
| `run_gem5_se_baseline.py` | `run_gem5se_baseline_user.py` |
| `run_engine_ratio.py` | `run_gem5se_ratio_user.py` |
| `run_pool.py` | `run_gem5se_pool_user.py` |
| `make_blocked_case_lists.py` | `gem5se_blocked_lists_user.py` |
| `sample_insts.py` | `gem5se_sample_insts_user.py` |
| `ref_split.py` | `gem5se_ref_split_user.py` |
| `se_tset_matrix.py` | `tset_matrix_user.py` |

保持不变（已符合规则）：`run_llvm_ts_user.py`。

### `tests/ee-vast/`（13 改 / 1 保持）

| 旧 | 新 |
| --- | --- |
| `power.S` | `power_vast.S` |
| `power.lds` | `power_vast.lds` |
| `hmon.S` | `hmon_vast.S` |
| `hmon.lds` | `hmon_vast.lds` |
| `smon.S` | `smon_vast.S` |
| `smon.lds` | `smon_vast.lds` |
| `kaiwu-vast.lds` | `kernel_vast.lds` |
| `k0_hmon.S` | `hmon_k0_vast.S` |
| `k0_hmon.lds` | `hmon_k0_vast.lds` |
| `k0_smon.S` | `smon_k0_vast.S` |
| `k0_smon.lds` | `smon_k0_vast.lds` |
| `k0_probe_kernel.S` | `probe_kernel_k0_vast.S` |
| `k0_probe_kernel.lds` | `probe_kernel_k0_vast.lds` |

保持不变：`README.md`（目录级说明，文档类不套 `<role>_<ee>`）；`k0_README.md` 按 D1 删除（`git rm`，内容已在册）。

## 引用更新（必须全量 grep，逐条贴命中）

- `Makefile`（`build-bootrom`/`linux-*`/`check-inst-asm` 等目标内的路径）。
- `tools/`（`qemu/k0_boot_probe.py`、`linux/check_k1.py`、`linux/semihost_*`、`testcases/lib/machine_profile.py`、`testcases/*.py`、`infra/build_*`）。
- `tests/`（`tests/README.md`、`tests/INVENTORY.md`、`tests/shared/README.md`、`tests/arch/README.md`、其它 ee-* 内部交叉引用：`.include`、`-T`、`--sysroot` 之外的资产路径）。
- `docs/`（`Process-09` 等已引用 ee-* 的段落）。
- 验收口径：`grep -rn "tests/ee-\(tiny\|user\|vast\)/" --include=*.py --include=*.S --include=*.inc --include=*.lds --include=*.s --include=*.c --include=*.ll --include=Makefile` 命中全部指向**存在的新文件名**。
- **冻结内容例外**：`tests/ee-vast/k0_smon.S:39` 等正文内提及旧目录名的注释，属 md5 冻结内容，内容零改动时允许保留（逐条列出，不得批量豁免）。

## 验收（逐条贴真实 rc）

1. 新旧映射逐条核对：50 个 `git mv` 全在位，旧名 0 残（`ls` 逐目录输出）；每个文件 md5 与改名前的 `git show HEAD:<old>` 一致（MISMATCH=0）。
2. `make build-bootrom` rc=0，10 产物 md5 与基线逐一致（`bootrom.bin b8c88a3e`、`bootrom_app.bin c0ef98d0`、`tiny/bootrom_tiny.bin 51430087`、`step5/*`、4 个 semihost ELF）。
3. `k0_boot_probe.py` rc=0（101 passed / 0 failed）；`make check-linux-k0` 119/119、`check-linux-k1` 112/112 rc=0。
4. `make linux-semihosting-smoke` rc=0（`failed checks: 0`）。
5. `check-tests-index`（472）、`check-dirs`、`check-no-residue`、`check-interface`、`check-inst-asm`（272/272）全 rc=0。
6. `m15-infra-001` 的 `machine_profile.py` 与 `ee-*/runtime.yaml` 在新路径下仍工作（`--profile tiny|vast` token 不变）。
7. **≥2 路注入**（含 1 路任务书未列）：把某引用改回旧名 ⇒ 构建/门控红；`cp`+md5 还原回绿。
8. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：50 个 `git mv` + 引用方 + 本任务书；**不动**文件内容、`spec/`、`.tao/contracts/`、`contracts/`、`components/`、`manifests/`、测试集语义。
3. **不改版本号**；不提交 git；`cp`+md5 还原（禁 checkout/restore/stash/show）。
4. 改名一律 `git mv`（保留历史）。
5. 与 `m15-infra-001` **串行**：infra-001 未合入 master 前不得派本任务。

## 待裁定

**D1 `tests/ee-vast/k0_README.md`：用户 2026-11-18 追加裁定「直接删除」——已执行。**

用户原话：「我个人感觉这是过程文档，没有必要保留」。已核实内容全部在册（失败码 `0xC1`–`0xC7`
→ `tests/ee-vast/smon_k0_vast.S` 头注释 + `tools/qemu/k0_boot_probe.py`；探针寄存器映射
`rd5`–`rd30` → `tests/ee-vast/probe_kernel_k0_vast.S` 头注释 + 探针断言；负例 → `smon_k0_vast.S`
的 `SMON_NEG_CASE` 块；boot 链与规范事实 → `spec/Kaiwu §6.3` + `contracts/linux-boot.yaml` + ADR-0051），
故 `git rm`，不做内容搬移。同一裁定还要求：删 `k0_boot_probe.py` docstring 里的悬空引用、
修 `tests/ee-vast/README.md` L4-5「smon 不被进入」的事实错误（step5 测试链不进入 / K1 内核启动链进入）。

## 本轮改名计数（实际执行）

- `tests/ee-tiny/` **22 件** + `tests/ee-user/` **16 件** + `tests/ee-vast/` 表列 **13 行** = **51 件 `git mv`**，另 **1 件 `git rm`**。
- ee-vast 13 行 = step5 6 + `kaiwu-vast.lds` 1 + K1 链 6（原先头注「12 / 共 50」为计数笔误，已由 architect 按表订正）。


## 完成区

**测试结果**：一键证据脚本（运行期证据目录，本任务证据已跑、未归档）**36/36 PASS（rc=0）**；**在已提交状态（HEAD `64fca82e`）下复跑**；注入模式 `run.sh --inject` **15/15 PASS（rc=0）**（3 路，含任务书未列 2 路）。下条 rc 均为实测。
**修改文件**：`git mv` 51 件（ee-tiny 22 / ee-user 16 / ee-vast 13）+ `git rm` 1 件（`tests/ee-vast/k0_README.md`）；改动 327 个文件 = 275 M + 35 R + 16 RM + 1 D（改名提交 `1f541c73` 的 `git show --stat`：327 files changed, 587 insertions(+), 676 deletions(-)；`git diff -M d868457c HEAD` 同为 327 files, 605(+), 673(−)）。其中 `tests/inst/**` 改动 = **202 `.S` + 1 `.inc` + 4 `.md`**（202 个 `.S` 每件仅 1 行 `@@` 注释，非注释行 0）。
**验收结果**：
- 映射：51 新名全在、旧名 0 残；`k0_README.md` 已删；目录普通文件数 tiny/user/vast = 23/17/15。
- md5：**35 件与改名前基线 `<BASE>:<old>`（`BASE=d868457c` 派单 commit）逐字节相同**；16 件仅改路径字面量（45 hunk/112 行，全量 diff 见证据 `content_changes.diff`，原因见遗留③）。
- `make build-bootrom` rc=0；18 个产物（含点名的 10 件）md5 与改名前后基线逐一致（`b8c88a3e…`/`c0ef98d0…`/`51430087…`）。
- `k0_boot_probe.py` rc=0：`result: 101 passed, 0 failed`。
- `make check-linux-k0` rc=2 → **116/119**（3 个失败全为 K12，预存红，见遗留①）；`check-linux-k1` rc=0 **112/112**；`make linux-semihosting-smoke` rc=0（`failed checks: 0`）。
- `check-tests-index` rc=0（**472 条**）/`check-dirs`/`check-no-residue`/`check-interface`/`check-inst-asm`（**272/272 镜像、633 例**）全 rc=0。
- 附带复核全绿：`check-case-ledger`/`check-asm-list-drift`/`check-index-blobs`/`check-writer-guards`(27/27)/`check-run-artifacts`/`check-runner-reap`/`validate-vectors`/`check-inst-macro-scope`/`make build-musl`(10/10)。
- `machine_profile.py --profile tiny|vast` token md5 `7bcc7ce1…`，与主工作树（未改）基线一致。
- 注入：A Makefile 源改回 `bootrom.S` ⇒ `llvm-mc: No such file`；B `kernel_tiny.lds` 的 `INCLUDE` 改回 `dadao-common.lds` ⇒ `LDS: … does not INCLUDE common_user.lds`；C 驱动 `_MSG_INC` 改回旧名 ⇒ `SETUP ERROR … not found`；三者 `cp`+md5+`cmp` 还原后回绿。
- `grep k0_README`（`.tao` 历史记录除外）= **0**；仓内命中全在 `.tao/tasks/testcases/` 两本任务书（`m15-testcases-015` 与本任务书，均属历史/裁定/审阅记录；命中行数随本任务书审阅记录追加而增长，**不钉数字**，以 `git grep -c` 现场计为准）。
**新发现/坑**：① **模块名即文件名**：`sys.path.insert(tests/ee-tiny)` 后 `import run_asm_suite`（check_tests_index/check_case_ledger/validate_vectors/check_inst_macro_scope/parity×4）、`import ref_split`、`import picolibc_tests`、`import se_tset_matrix` 全部要改成 `import <新名> as <旧别名>`，否则门控 `ModuleNotFoundError`（首跑 check-tests-index 即红）。② **`INCLUDE <file>` 是文件名即接口**：`dadao-common.lds→common_user.lds` 要同步 3 个 lds 的 `INCLUDE` + `check_tests_index` 的 INCLUDE 断言。③ `.include "tests/ee-tiny/<asset>"` 是编译期硬依赖（power/semihost_smoke）。④ **程序标识不是路径**：`run_asm_suite:`/`run_embench_e2e:` 日志前缀、writer-guard `label`、`inst-tiny:` ASSERT 前缀未改（`Makefile:1909` 的 grep 与 `progress.py` 正则依赖它们，改了等于改日志契约）。⑤ 证据脚本**不能用 `git diff/status` 判"已还原"**（这些文件相对 HEAD 本就改动；`app_tiny.lds` 注入后恰好回落到 HEAD 内容、`git diff` 反而变空）——一律 `cmp` 对备份。⑥ fresh worktree 的 `check-linux-k0` 需 linux/musl 源与构建树（环境接法见证据 `env_setup.md`）。
**遗留问题**：① **K12 预存红**：共享 linux 源树 HEAD `0a2d2cfcc` 与 76 补丁集不匹配，`apply-series` 拒绝执行（主控机同命令 rc=1，证据 `logs/apply-series-main.log`）⇒ 未处置（需重放补丁集，属破坏性操作，交用户/另案）。② **13 条冻结内容例外**（7 个 md5 冻结文件的旧名正文提及，均为 docstring/注释、无执行作用）：`dyn_user.lds:16`、`gem5se_ref_split_user.py:38-40`、`mem_runtime_user.ll:12`、`run_embench_user.py:28,159`、`run_libc_test_smoke_user.py:18,19`、`run_libc_test_user.py:62,538`、`run_llvm_ts_smoke_user.py:19,20`，逐条在证据 `freeze_exceptions.txt`（C3 双向校验：新增悬空必红、清单过期必红）。③ **16 件 md5 必变**（功能路径字面量，单靠改文件名无法保持）：power_tiny.S、semihost_smoke_tiny.S、kernel_tiny.lds、app_tiny.lds、kernel_vast.lds（`.include`/`INCLUDE`）、run_inst_tiny.py、run_embench_tiny.py、run_picolibc_tiny.py、run_semihosting_tiny.py、run_gem5se_{baseline,ratio,pool}_user.py、gem5se_{blocked_lists,sample_insts}_user.py、tset_matrix_user.py（资产/驱动路径常量）、smon_k0_vast.S（删指向已删 README 的 1 行引用）。④ 历史记录未改：`m15-testcases-01{1..5}` 任务书、`.tao/knowledge/milestones-m15.md`（主会话台账）、`tests/inst/MIGRATION.md`、`docs/TestReports/*`、`docs/Process-09` 的 2026-11-17/18 迁移史注记（明示日期的历史段落；同名行的**现状描述**已订正，见返工记录 F11）。⑤ 计数差异：表列 51 行 vs 头注 50（ee-vast 13 vs 12），按**表**执行，未自行增删。

## 审阅记录

### 第 2 轮 reviewer 验收（2026-11-18）

**判决：Accepted**（第 1 轮唯一阻断 C2「提交后失效」已闭合；上轮 5 条非阻断 finding 已订正）

**自证**：本任务 worktree、分支 `m15-testcases-016`、`git status -uall` 空 rc=0；HEAD=`bf05b5c7`。

**① 上轮阻断复验（我的重跑，rc 取被检命令自身）**
- `run.sh` → **36/36 PASS，rc=0**。C2 段实测：`C2z want=different got=different`、`C2d want=0 got=0`、`C2a want=35 got=35`、`C2b want=16 got=16`、`C2c want=0 got=0`（头部行已是 `git show d868457c:<old>`）。
- **可达 FAIL 闭环（脚本 `/tmp/…/inject_c2.sh`，cp+md5+cmp 还原）**：把 `BASE_COMMIT` 临时改 `"HEAD"` ⇒ **rc=1、36 项中 5 FAIL**，恰为 `C2z 基线 commit ≠ HEAD want=different got=same`、`C2d 空 blob want=0 got=51`、`C2a want=35 got=0`、`C2b want=16 got=0`、`C2c want=0 got=51`；还原 md5 `e4a439ba…` 相等 + `cmp` 一致 ⇒ **rc=0、36/36 PASS**。
- `grep -n 'HEAD:' run.sh` 仅命中**第 85 行注释**（记录根因），`c2_md5()` 内取旧名只有 `$BASE_COMMIT` 一处，无其它 `HEAD:` 取值点。

**② 上轮 5 条非阻断 finding 订正核验**
- ① 完成区已改「`tests/inst/**` = **202 `.S` + 1 `.inc` + 4 `.md`**」✓；③ 已改「`git show --stat` = **327 files, 587(+), 676(−)**」✓；④ `docs/Process-09` L237 `kaiwu-tiny{,-app}.lds`/`dadao-{common,dyn}.lds` 与 L238 `{bootrom,bootrom_app}.S` **均改为新名** ✓；⑤ `freeze_exceptions.txt` 顶部已加「7 行是 docstring 命令示例、照抄不可执行」注记 ✓；② 改为不钉行号的现场计法 ✓（见下条 finding）。

**③ 其余复验（全绿）**
- `run.sh --inject` → **15/15 PASS，rc=0**。
- `build-bootrom` rc=0 且 **18 产物 md5 与基线 diff=0**；`k0_boot_probe` rc=0 `result: 101 passed, 0 failed`；`check-inst-asm` rc=0 **272/272 镜像、633 例**；`check-linux-k1` rc=0 **112/112**；`linux-semihosting-smoke` rc=0 `failed checks: 0`；`check-tests-index` rc=0 **472 条**（inst 272/arch 11/unit 186/tset 3）；`check-dirs`/`check-no-residue`/`check-interface` 均 rc=0；`machine_profile` token `7bcc7ce1…` 一致。
- `check-linux-k0` **116/119**、3 FAIL 全为 `K12 apply-series` ⇒ 仍为共享 linux 树 HEAD 不匹配的 pre-existing（上轮已在主控机复现同报文 rc=1），**未计入本任务红/绿**。

**④ 约束核验**：`d868457c..HEAD` = `.tao` 1（本任务书）+ `Makefile` 1 + `docs` 3 + `tests` 276 + `tools` 46；`spec/`、`.tao/contracts/`、`contracts/`、`components/`、`manifests/` **0 行**；**51 R + 1 D + 275 M 结果未变**（R100=35、非 R100=16）；本轮返工提交 `1f541c73..HEAD` **仅改任务书 + `docs/Process-09` 两件**；`docs/Process-08`、`docs/core-wuming-cycle-model.md` 亦为纯路径引用更新（在任务书「引用更新」范围内，非越界）；未用 `cmd | tee` 取码。

**非阻断 finding（交 architect 收尾订正）**：完成区「本任务书 7 行」与现场 `git grep -c k0_README` = **8** 差 1（自指漂移：审阅记录本身会新增命中行）；完成区已声明「行号随记录增长漂移、按 `git grep -c` 现场计」，故不阻断。

### 第 1 轮 reviewer 验收（2026-11-18）

**判决：Needs Revision**（唯一阻断 = 证据脚本 `run.sh` C2 判据在提交后失效；产物本身无缺陷）

**自证**：worktree `/tmp/opencode/m15-testcases-016/wt`、分支 `m15-testcases-016`、`git status -uall` 空 rc=0；HEAD=`1f541c73`。

**重跑记录（我的输出，rc 取被检命令自身）**
- `run.sh` → **检查 34 项、失败 2 项、RESULT: FAIL（rc=1）**。FAIL 仅 `C2a want=35 got=0`、`C2b want=16 got=51`；C1/C3/C4/C5/C6/C7/C8 共 32 项全 PASS。根因：`c2_md5()` 用 `git show HEAD:<old>`，WIP 提交后 HEAD 已含改名 ⇒ 每次 `fatal: path ... does not exist in 'HEAD'` rc=128，`a` 落成空文件 md5 `d41d8cd9…`。违反 AGENTS.md「提交后仍须回绿」。
- `run.sh --inject` → **15/15 PASS，rc=0**（A/B/C 三路注入→红→cp+md5 还原→回绿均成立）。
- 独立用 `HEAD~1:<old>` 重核内容零改动 → **SAME=35 / DIFF=16**，与遗留③的 16 件逐条一致；16 件 diff 逐条核毕，改动全为路径字面量（`.include`/`INCLUDE`/`DEFAULT_*`/`_MSG_INC`、docstring 与 `@@` 注释里的文件名、D1 授权删 1 行 README 引用），**无逻辑变更**。
- `tests/inst` 下 **202 个 `.S` 每件仅 1 行、404 行 +/- 全为 `@@` 注释行（内容只 `inst-tiny.lds`→`inst_tiny.lds`），非注释行为 0**。
- 门控：`build-bootrom` rc=0 且 18 产物 md5 与基线 diff=0；`k0_boot_probe` rc=0 `101 passed, 0 failed`；`check-linux-k1` rc=0 **112/112**；`linux-semihosting-smoke` rc=0 `failed checks: 0`；`check-tests-index` rc=0 **472 条**、`check-dirs`/`check-no-residue`/`check-interface`/`check-inst-asm` rc=0（**272/272 镜像、633 例**）、附带 `check-case-ledger`(5666)/`check-asm-list-drift`/`check-index-blobs` 全 rc=0；`machine_profile --profile tiny|vast` token `7bcc7ce1…` 一致。
- **reviewer 独立注入 2 路（均任务书未列，脚本 `/tmp/opencode/m15-testcases-016/inject_review.sh`）**：D `power_tiny.S` 的 `.include` 改回 `tiny_common.inc` ⇒ `make build-bootrom` **rc=2**（`Could not find include file`）；E `run_inst_tiny.py` 的 `DEFAULT_LDS` 改回 `inst-tiny.lds` ⇒ `make check-inst-asm` **rc=2**。两路均 cp+md5 相等 + `cmp` 一致 + 还原后 **rc=0 回绿**。
- **K12 对照**：本树 `check-linux-k0` = **116/119**，3 个 FAIL 全为 `K12 apply-series`；主控机 master（`git status` 空、未改任何 ee-* 文件）跑 `apply_series.py --component linux` → 同报文 `linux HEAD (0a2d2cfcc42b) is neither base (7b20d05fd38d)`，**rc=1** ⇒ 确为共享 linux 树 HEAD 不匹配的 pre-existing 环境态，**未计入本任务红/绿**。

**约束核验**：51 `git mv` 全在位、旧名 0 残、`README.md` 文件名未动、`k0_README.md` 已 `git rm`；仓外 `grep k0_README`=0（仓内 10 行全在 `.tao` 两本任务书）；死引用 13 条 = `freeze_exceptions.txt` 13 条逐条相等（注释/docstring/链接脚本注释，无执行作用，C3 双向校验）；`$BASE..HEAD` 仅 `.tao` 2 + `Makefile` 1 + `docs` 3 + `tests` 276 + `tools` 46；`spec/`、`.tao/contracts/`、`contracts/`、`components/`、`manifests/` **0 行**；版本号未动；日志前缀 `run_asm_suite:`/`run_embench_e2e:` 保留有据（`Makefile:1909` 的 `grep -E "^run_asm_suite:"`、`progress.py:58,65` 正则）；未用 `cmd | tee` 取码。

**修改建议（仅此一处，产物无需改）**：证据脚本 `run.sh`（运行期证据目录）`c2_md5()` 把 `git show "HEAD:tests/$d/$o"` 改为钉住改名前基线 commit（如 `BASE=d868457c`；`git show "$BASE:tests/$d/$o"`），使后续再提交也不会失效；改后 `run.sh` 须 34/34 rc=0。

**非阻断 finding（交 architect 收尾订正）**：① 完成区「`tests/inst/**/*.S` 207 件」实为 202 `.S` + 1 `.inc` + 4 `.md`；② 完成区「剩 11 行」实为 10 行（015 任务书 4 + 本任务书 6）；③ 完成区「291 files / 586 / 543」与实际 `git show --stat HEAD`=**327 files / 587 / 676**（staging 对账时须按实际）；④ `docs/Process-09:237` 同一行内 `kaiwu-tiny{,-app}.lds`、`dadao-{common,dyn}.lds` 未随 `kernel_vast.lds`/`bootrom_tiny.lds` 一并更新（`.md` 不在验收 grep include 内）；⑤ 13 条冻结例外中 4 条是 docstring **命令示例**（如 `python3 tests/ee-user/ref_split.py --stats`），照抄会失败，已由任务书显式列为冻结例外并双向校验。

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `import run_asm_suite` 等模块名随文件改名失效 | ✅已修 | 10 个导入点改 `import <新名> as <旧别名>`（check_tests_index/check_case_ledger/validate_vectors/check_inst_macro_scope/parity×4、run_llvm_ts_user 的 `ref_split`） | 修前 `check-tests-index` = `ModuleNotFoundError`；修后 rc=0（472 条） |
| F2 链接脚本 `INCLUDE` 与 `check_tests_index` 断言不同步 | ✅已修 | `kernel_tiny.lds`/`app_tiny.lds`/`kernel_vast.lds` 的 `INCLUDE` + 检查器两处断言 + 自检树模板 | 注入 B 实测 `LDS: … does not INCLUDE common_user.lds`；`build-musl`/`build-bootrom`/`check-inst-asm` 全绿 |
| F3 证据脚本用 `git diff` 判"还原成功"（错误判据） | ✅已修 | 改 `cmp` 对 `cp` 备份 + md5 双向对账 | `run.sh --inject` 15/15 PASS（3 路） |
| F4 用 `git diff` 判"注入生效"也会假空（`app_tiny.lds` 注入后恰等于 HEAD 内容） | ✅已修 | 改 `cmp -s 备份 文件` | 同上；并据此把注入 B 目标改为 `kernel_tiny.lds`（`lds_map` 覆盖） |
| F5 `ls｜wc -l` 把 `__pycache__` 计入目录文件数 | ✅已修 | 改 `find -maxdepth 1 -type f`；并清理全部 `__pycache__` | C1e = 23/17/15 PASS |
| F6 `grep -c` 把日志重复行计成 2 | ✅已修 | 改 `-ge 1` 判存在 | C7h PASS |
| F7 改名后 ASCII 管线图箭头列错位、README 超长行 | ✅已修 | `run_embench_tiny.py:29-31`、`run_elf_e2e.py:10` 补空格；`ee-vast/README.md` 折行 | 目视 + 全量证据回绿 |
| F8 程序内部标识（日志前缀/label/ASSERT 前缀）是否也算"引用" | ❌不修（有据） | 保持原样 | `Makefile:1909` 用 `grep -E "^run_asm_suite:"` 解析跑批日志、`progress.py` 正则匹配 `run_embench_e2e:`；改它们等于改日志契约（超"只改文件名"） |
| F9 `smon_k0_vast.S` 头注释指向已删 README 的旧路径 | ✅已修 | 该行改为「identical in this source and `tools/qemu/k0_boot_probe.py`」 | 该项使该文件进入遗留③（md5 必变），已在解析中单列 |
| F10 未跑 `install-host`（worktree fresh，避免共享安装根在途冲突） | ⏸延后 | 改用主工作树工具链软链（只读）+ 复制 sysroot/构建树 | `build-bootrom`/`k0_boot_probe`/`check-inst-asm`/`check-linux-k*` 全部用该环境跑通，产物 md5 与基线一致 |

### 第 2 轮 engineer 返工（处置第 1 轮 reviewer 的 Needs Revision）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| **阻断** C2 用 `git show HEAD:<old>`：提交后 HEAD 已含改名 ⇒ rc=128、空 blob `d41d8cd9…`，`C2a 0/35`、`C2b 51/16` | ✅已修 | `c2_md5()` 基线钉到**改名前 commit** `BASE_COMMIT="d868457c"`（派单 commit）；并加两道守卫：`C2z 基线 commit ≠ HEAD`、`C2d 基线旧名全部可读（空 blob=0，不许算 SAME/DIFF）` | **提交状态**（HEAD `64fca82e`）下 `run.sh` = **36/36 PASS rc=0**（`C2z different / C2d 0 / C2a 35 / C2b 16 / C2c 0`）；可达 FAIL：把 `BASE_COMMIT` 临时改成 `"HEAD"` ⇒ **5 FAIL rc=1**（`C2z same`、`C2d 51`、`C2a 0`、`C2b 0`、`C2c 51`），`cp`+md5 还原（`e4a439ba…` 前后一致、`cmp` identical）⇒ 再跑 **36/36 rc=0**。 |
| NB① `tests/inst` 实为 202 `.S` + 1 `.inc` + 4 `.md` | ✅已订正 | 完成区「修改文件」改写为「327 files = 275 M + 35 R + 16 RM + 1 D；`tests/inst/**` = 202 `.S` + 1 `.inc` + 4 `.md`」 | `git diff --name-only <BASE> <改名提交> -- tests/inst \| sed 's/.*\.//' \| sort \| uniq -c` → `202 S / 1 inc / 4 md` |
| NB②「11 行」实为 10 行 | ✅已订正 | 改为不钉行号的现场计法（两本任务书 4 + 7 行，历史/裁定/审阅记录，行号随记录增长漂移） | `git grep -c k0_README` 现场输出 |
| NB③「291 files/586/543」 | ✅已订正 | 改为 `git show --stat` 的 **327 files, 587(+), 676(−)**（无 rename 检测），并并列 `git diff -M` 视角 291/+586/−543 | 两者实测输出 |
| NB④ `docs/Process-09:237` 同行旧名未更新 | ✅已修 | 该行 `kaiwu-tiny{,-app}.lds`/`dadao-{common,dyn}.lds` → `kernel_tiny.lds`/`app_tiny.lds`/`common_user.lds`/`dyn_user.lds`；**同段 238 行同类**（`{bootrom,bootrom_app}.S` → `bootrom_tiny.S`/`bootrom_app_tiny.S`）一并订正 | `sed -n '236,239p'` 现状行；`make check-asm-prose` rc=0 |
| NB⑤ 4 条冻结例外是 docstring 命令示例、照抄会失败 | ✅已加注 | `freeze_exceptions.txt` 顶部加 `#` 注记：7 行命令示例「仅示意、旧名照抄不可直接执行」，并给出当前应使用的脚本名 | `grep -vc '^#'` 仍 = 13（注记以 `#` 开头，不参与计数/双向校验） |

**返工附带订正（1 行，仅路径措辞）**：第 1 轮 reviewer 记录中的「修改建议」原写有具体运行期路径，按 `AGENTS.md`「任务书（含完成区/审阅记录）不得出现具体运行期路径」改为「证据脚本 `run.sh`（运行期证据目录）」；**finding 内容与判决未改**。改后 `make check-knowledge-refs` rc=0。（同段 reviewer 自证里的 worktree 绝对路径未动——非门控项，交 architect 收尾决定是否一并措辞化。）
