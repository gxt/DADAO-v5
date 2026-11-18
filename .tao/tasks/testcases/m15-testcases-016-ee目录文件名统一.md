# m15-testcases-016: `tests/ee-*` 文件名统一为 `<role>_<ee>` 规则

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-011`/`012`/`013`/`014`/`015`（ee-* 三目录已建立并集中完毕）、`m15-infra-001`（`machine_profile.py` 与 `ee-*/runtime.yaml` 已迁；**必须串行**，同改 tests 路径）
**可并行分片**：否（跨三目录 + 全仓引用）
**预估**：2–3 h
**档位**：中改
**状态**：待开始

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

## 改名清单（共 51 个 `git mv`，其中 D1 待定 1 个；其余 2 件保持原名）

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

### `tests/ee-vast/`（13 改 / 2 保持）

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

保持不变：`README.md`（目录级说明，文档类不套 `<role>_<ee>`）；`k0_README.md` → 见待裁定 D1。

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

**D1 `tests/ee-vast/k0_README.md` 是否也套规则？** 建议 `README_k0_vast.md`（与 `README.md` 并存、不冲突）；若选「文档类一律不套规则」则保持原名。**建议：改 `README_k0_vast.md`**，使 ee-vast 仅 `README.md` 一个例外。
