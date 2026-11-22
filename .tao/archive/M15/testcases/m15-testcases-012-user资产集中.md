# m15-testcases-012: user 执行环境资产集中到 `tests/ee-user/`

**模块**：testcases
**项目里程碑**：M15
**依赖**：无（纯目录/路径迁移；测试集内容不变）
**可并行分片**：否（跨目录引用唯一）
**预估**：2–3 h
**档位**：中改（迁移 + 引用更新 + 门控回绿）
**状态**：已验证

## 背景（用户 2026-11-17）

`tests/` 下执行环境资产统一用 `ee-` 前缀：`tests/ee-tiny/`（已立 `m14-testcases-007`）、**`tests/ee-user/`**（本任务）、`tests/ee-vast/`（后续）。本任务把 qemu-user / gem5-se 的**脚本、crt、lds、runtime** 集中到 `tests/ee-user/`；**平铺、不建子目录**；测试集目录不移动。

## 目标（迁移清单，共 17 个文件）

**脚本（12）**

1. `tools/testcases/tset/embench/run_embench_user_suite.py`
2. `tools/testcases/tset/libc-test/run_libc_test_user_suite.py`
3. `tools/testcases/tset/libc-test/run_smoke.py`
4. `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`
5. `tools/testcases/tset/llvm-ts/run_smoke.py`
6. `tools/testcases/tset/llvm-ts/ref_split.py`
7. `tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py`
8. `tools/testcases/tset/gem5-se-baseline/sample_insts.py`
9. `tools/testcases/tset/gem5-se-baseline/make_blocked_case_lists.py`
10. `tools/testcases/tset/gem5-se-baseline/run_engine_ratio.py`
11. `tools/testcases/tset/gem5-se-baseline/run_pool.py`
12. `tools/testcases/parity/se_tset_matrix.py`

**crt / lds / runtime（5）**

13. `tests/shared/crt0/minimal_crt0.s`
14. `tests/shared/runtime/dadao_mem_runtime.ll`
15. `tests/shared/runtime/dadao_user_dyn_probe.c`
16. `tests/shared/linker/dadao-common.lds`
17. `tests/shared/linker/dadao-dyn.lds`

**不移动**：`tests/tset/{embench,libc-test,llvm-ts}/**`（测试集源码/patches）；`tools/testcases/parity/three_platform_matrix.py`、`qemu_gem5_shim.py`（跨 tiny/vast 的三平台差分/桥接）；`tests/arch/**`；`tests/inst/**`；`tests/ee-tiny/**`。

## 引用更新（必须全量 grep）

- `tools/testcases/tset/*/run_smoke.py` 与 suite 驱动自身的 `--help`/默认路径。
- `Makefile` 的 `check-libc-test*`/`check-llvm-ts*`/`check-embench*`/`check-unit`（若引用这些脚本）。
- `tests/README.md`、`tests/INVENTORY.md` 的路径。
- `tools/testcases/check_tests_index.py` 等门控的扫描面。
- 迁移后的脚本要能 `--help` 运行（相对导入/`ROOT` 解析按新位置修正）。

## 验收（逐条贴真实 rc）

1. `git mv` 后旧路径不存在、新路径存在；17 文件 md5 一致。
2. `check-tests-index`、`check-dirs`、`check-no-residue`、`check-run-artifacts` 全 rc=0。
3. 迁移后的 12 个脚本各自 `--help`（或等价轻量入口）可运行；至少 1 个 suite 冒烟（如 `run_smoke.py`）能跑或给出环境 BLOCKED 理由。
4. 1 路注入：引用改回旧路径 ⇒ 门控/脚本红；`cp`+md5 还原 ⇒ 回绿。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：上述 17 文件、调用方（`Makefile`/`tools/`/文档/门控扫描面）、本任务书。**不动**测试集内容、`spec/`、`.tao/contracts/`、组件补丁。
3. **不改版本号**；不提交 git；`cp`+md5 还原。
4. 迁移用 `git mv`。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查 17 迁移件 + 20 个调用面改动；判决：**无未修 finding**。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `libc-test/run_smoke.py` 与 `llvm-ts/run_smoke.py` 平铺后同名冲突 | ✅已修 | 改名 `run_libc_test_smoke.py`/`run_llvm_ts_smoke.py`，文件名自带套件名 | 两脚本 `--help` rc=0；`check-tests-index` 扫描无重名告警 |
| F2 `dadao-common.lds` 迁出后 3 份 `INCLUDE` 解析失败（lld 只搜 cwd 与 `-L`，实测） | ✅已修 | 8 处链接点补 `-L tests/ee-user`（driver 各 1 处 + lit/engine_parity/min_rom_probe） | 真实链接 rc=0；去掉该 `-L` ⇒ `cannot find linker script dadao-common.lds` rc=1 |
| F3 `check_run_artifacts.py` 的 `DRIVERS` 基准目录是 `tools/testcases/`（改成 repo 相对后 A1 全红） | ✅已修 | `_driver_dir()` 返回 repo root；自检树拷贝同步到 `tests/ee-user/` | `make check-run-artifacts` rc 0→2→0（修前真红） |
| F4 3 个薄 wrapper 的 `_IMPL` 拼接被批量替换破坏语法 | ✅已修 | 手工改写为 `".." , "..", "tests", "ee-user", "<impl>"` | 3 个 wrapper `--help` rc=0 |
| F5 `se_tset_matrix` 生成表头含旧路径（与冻结的 M11 快照逐字节比对） | ❌不修 | 保持生成文本不变（改了会与 `docs/TestReports/M11-三平台一致矩阵.md` 不一致） | `se_tset_matrix --self-test` rc=0；M11 快照未改 |

### 第 1 轮 reviewer 验收

**判决：Accepted**（中改档；下列均为本轮独立重跑，未采信 engineer 转述）

**重跑记录**（worktree 分支 `m15-testcases-012`，注入前 `git status -uall` 干净）
- 证据脚本 `run.sh`（运行期证据目录）：**15/15 PASS，exit=0**；须设 `M15_TC_BIN` 指共享安装根——本 worktree 无 `.dadao/cross-toolchain`，裸跑在 link 项 rc=127 FAIL（环境非交付物缺陷，脚本据此真红，非恒真）。
- 门控独立重跑：`check-tests-index` rc=0（**472 条**）、`check-dirs` rc=0、`check-no-residue` rc=0、`check-run-artifacts` rc=0、`check-case-ledger` rc=0（5666 现场派生）、`check-index-blobs` rc=0（325+94）、`check-interface` rc=0；另 `check-knowledge-refs`/`check-runner-reap`/`check-test-reports` rc=0；`check-writer-guards` rc=2（23/27，W1a/b/c+W5b）→ 独立定位 `run_asm_suite: ERROR: llvm-mc 不存在 …/.dadao/…`（rc=2），与本 diff 无关，采信。
- 12 脚本 `--help` **12/12 rc=0**；6 个无 guest 自检 6/6 rc=0。
- 真实链接：`llvm-mc` crt0+p2align main rc=0/0；`ld.lld -L tests/shared/linker -L tests/ee-user -T kaiwu-tiny-app.lds` **rc=0**（prog.elf 1432 B）；去 `-L tests/ee-user` ⇒ **rc=1** `cannot find linker script dadao-common.lds`。
- 迁移完整性：`tests/ee-user/` **17/17 平铺**、17 件旧文件全 gone；我独立 `git show 96a74ad4:<old>` 与 `md5-before.txt` **17/17 相等**、`md5-after-move` 与 before **17/17 相等** ⇒ git mv 逐字节；终态 4 资产同 BASE blob，`dadao_mem_runtime.ll` 仅 1 行注释（sed 替换后 md5 相等）；12 脚本 diff 共 104 行**全为** `REPO_ROOT` 层级/DRIVERS/文档串，无断言弱化；两处 `run_smoke.py` 改名对应正确（同目录各自指向 driver）。
- 越界：`96a74ad4..HEAD` 54 文件 = 任务书改名 + 17 迁移件 + 调用方/文档；`spec/`、`.tao/contracts/`、`components/**`、`contracts/`、`tests/inst/**`、测试集源/补丁**零改动**（唯一命中的 `tests/tset/llvm-ts/patches/README.md` 是文档非补丁）。

**独立注入 2 路**（均 `cp` 备份 + md5 还原，未用 checkout/restore/stash/show）
1. `min_rom_probe_integ007t.link()` 去掉 `-L tests/ee-user` ⇒ 真实调用点 **rc=2** `cannot find linker script dadao-common.lds`；还原 md5 `3225c20d…` 相等 ⇒ rc=0。
2. `check_tests_index.py` ALLOWED 键改回旧路径 ⇒ 脚本 **rc=1** `OLD GEOMETRY`（`make` rc=2）；还原 md5 `38168977…` 相等 ⇒ `make check-tests-index` rc=0（472 PASS）。engineer 自报的 `check_run_artifacts` 注入另在 run.sh 内复跑：注入 rc=1 / 还原 md5 一致 / 回绿 rc=0。

**约束核验**：独立 worktree ✓ 未改主工作树 ✓ 未提交 git ✓ 17 件 `git mv` ✓ 不改版本号 ✓ 只动声明范围 ✓（diff 无 spec/契约/补丁）✓

**发现（均不阻断）**
- F-a 本地空目录残留 `tests/shared/crt0/`、`tests/shared/runtime/`（git 不跟踪、两门控绿）⇒ 建议 `rmdir`。
- F-b 旧路径注释：`tests/unit/**` **14** 处、`tests/tset/**` **4** 处（完成区写 15/3，各差 1，笔误）——按「不动测试集内容」保留可接受；另 `docs/TestReports/M11-…凡例.md`(3)、`M13-…md`(1)、`components/picolibc/README.md`(1) 仍给已失效命令/路径，完成区未披露 ⇒ 归路径清理任务。
- F-c `se_tset_matrix` 生成表头仍写旧路径（F5 不修）：**可接受**（冻结 M11 快照逐字节一致优先，不进任何门控/执行路径）；失效命令同 F-b。
- F-d **合入冲突（阻断面在合不在改）**：master 已合 `m15-testcases-011`（`4a980df3`，kaiwu 3 lds → `tests/ee-tiny/`）；只读 `git merge-tree master HEAD` 实测 **17 处 CONFLICT**（任务书 rename/add-add、Makefile、lit.cfg.py、build_musl、min_rom_probe、engine_parity_run、run_elf_e2e、run_suite、fp/int_diff、check_writer_guards、test_picolibc_smoke、README/INVENTORY×4、`tests/ee-tiny/run_embench_e2e.py`）。**建议**：012 后合，先并 master 解冲突，逐点复核 8 个链接点同时含 `-L tests/ee-tiny`(011) 与 `-L tests/ee-user`(012)，再重跑 `check-tests-index` + 真实链接冒烟；`run_embench_e2e.py` 的 011 改名与 012 的 `-L` 须并存。
- F-e `run.sh` refs 检查用手工 SURFACE 清单且 `grep -v run_embench_e2e.py` 整文件豁免（该文件合法自指，但会吞其内部真回归）；我另做全仓 grep，非豁免旧路径 0。

**未闭合项**：guest 端到端 suite 冒烟仍 BLOCKED（worktree 无上游语料，需 `make fetch`），已披露；台账/合并归主会话。

## 完成区

**测试结果**：证据脚本 `run.sh`（交付于运行期证据目录）**15/15 PASS（rc=0）**；含反例注入自检（注入红 / cp+md5 还原绿）。suite **guest 冒烟 BLOCKED**：本 worktree 无上游套件语料（`run_libc_test_smoke.py --list` rc=2「source not found」，需先 `make fetch`）；改以 6 个无 guest 自检代替（`se_tset_matrix` / `run_pool` / `sample_insts` / `make_blocked_case_lists` / `run_engine_ratio` / `run_gem5_se_baseline` 全 rc=0，覆盖迁入模块的路径加载器）。

**修改文件**：17 件 `git mv` 到 `tests/ee-user/`（12 脚本 + `minimal_crt0.s`/`dadao_mem_runtime.ll`/`dadao_user_dyn_probe.c`/`dadao-common.lds`/`dadao-dyn.lds`；两处 `run_smoke.py` 改名见 self-review F1）；调用面：`Makefile`、3 个薄 wrapper、`tools/testcases/{check_tests_index,check_runner_reap,night_run,diff_ir_lli,run_suite,picolibc_test_crt0.s,unit/run_{codegen,elf}_e2e,tset/embench/run_embench_e2e,arch/min_rom_probe_integ007t,parity/{README,engine_parity_run.sh,fp_diff,int_diff,three_platform_matrix}}`、`tools/infra/{check_run_artifacts,check_writer_guards,test_picolibc_smoke,build_musl}`、`tests/unit/llvm/e2e/lit/lit.cfg.py`、`tests/{README,INVENTORY,shared/README,tset/*/README}`、`docs/Process-08`/`Process-09`、本任务书（改名 + 里程碑 M15）。

**验收结果**：① `git mv` 后旧路径 0 个、新路径 17/17；移动当刻 md5 **17/17 逐字节一致**（迁移前/移动后两份 md5 记录同存于运行期证据目录），最终态 4 资产与 96a74ad4 旧 blob 逐字节一致、`dadao_mem_runtime.ll` 仅 1 行注释路径替换。② `make check-tests-index` rc=0（472 条）、`check-dirs` rc=0、`check-no-residue` rc=0、`check-run-artifacts` rc=0；另 `check-runner-reap`/`check-test-reports`/`check-knowledge-refs`/`check-case-ledger`/`check-index-blobs`/`check-interface` 全 rc=0。③ 12 脚本 `--help` 全 rc=0；真实链接冒烟 `llvm-mc crt0+main` → `ld.lld -L tests/shared/linker -L tests/ee-user -T kaiwu-tiny-app.lds` rc=0。④ 注入 2 路（`check_tests_index` ALLOWED 键改回旧路径 ⇒ `OLD GEOMETRY` rc=1；`check_run_artifacts` DRIVERS 改回旧路径 ⇒ A1 rc=1）均 `cp`+md5 还原后 rc=0；两门控 `--self-test`（`check_tests_index` / `check_run_artifacts`，含其自检树与注入）全 PASS。

**新发现/坑**：① **lld 的 `INCLUDE` 不按宿主脚本目录解析**（实测：只搜 cwd 与 `-L`），故 lds 分居两目录时必须给每个 `-T` 点补 `-L`；`m15-testcases-011` 把 `kaiwu-tiny*.lds` 迁到 `tests/ee-tiny/` 后同样依赖这些 `-L`（合入顺序需注意：两者都改同一批链接行）。② `tests/unit/**`(15 处) 与 `tests/tset/**`(3 处) 的**注释**仍写旧路径（`tests/shared/crt0/...`、`tests/shared/runtime/...`），按「不动测试集内容」未改，建议立术语/路径清理任务。③ `check-writer-guards` 本 worktree 23/27（4 项 W1/W5b 因本 worktree 未装工具链），在 96a74ad4 干净树复跑同为 23/27 ⇒ 与本任务无关。④ `check-milestones-fresh` 在本分支报 4 项：3 项在 master 同样存在（`milestones-m14` L39 内嵌 `|` 行 + linux-020/021 覆盖缺口），1 项 `m14-testcases-008 无任务书` 系本任务改名所致、master 已把该行移入 `milestones-m15`（合并后消失）；台账改动归主会话。

**遗留问题**：无（guest 端到端 suite 冒烟为环境 BLOCKED，理由见上；运行期证据目录内的 `run.sh` 已可复跑）。

**合并记录（2026-11-18，与已合入的 `m15-testcases-011` 解冲突，16 文件）**：按「012 → `ee-user`、011 → `ee-tiny`」并存解冲突——`crt0`/`runtime`/`dadao-common.lds`/`dadao-dyn.lds` 落 `tests/ee-user/`，`kaiwu-tiny{,-app}.lds`/`picolibc-tiny.ld` 落 `tests/ee-tiny/`；8 个链接点统一改成 `-L <lds 所在目录>` + `-L tests/ee-user`（`INCLUDE dadao-common.lds` 需后者），原 `SHARED_LDS_DIR` 语义拆为 `COMMON_LDS_DIR=tests/ee-user`；`run_embench_e2e.py`（011 迁入 `ee-tiny/`）取其 011 的 `DEFAULT_LDS=tests/ee-tiny/…` 与 012 的 `crt0`/`mem_runtime`=`tests/ee-user/…` 并存；README/INVENTORY/shared-README 表格 `ee-tiny/` 与 `ee-user/` 双行保留。