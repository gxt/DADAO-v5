# QEMU-076t: semihosting 调用点迁移至 0x3FF00–0x3FFFF（ADR-0038 D4）

**模块**：qemu
**项目里程碑**：M10
**依赖**：SPEC-176t（ADR-0038 D1/D2/D4/D5）
**状态**：已验证

## 执行环境
本地（QEMU 补丁 + 测试/探针迁移；会触发 QEMU 重建）

## 接口规范

### 背景
semihosting 判定已由 `immu18[17:16]==0b11` 改为 `immu18[17:8]==0x3FF`（`0x3FF00–0x3FFFF`）；`HBI_<name>_INIT` `0x30001` 在区外。本任务把 QEMU 译码与全部 semihosting 调用点迁到新 tag，**不改变** semihosting 语义/服务号。

### 改动清单
1. **QEMU 译码**（组件补丁树）：
   - `components/qemu/patches/target/dadao/insn_trans/trans_ctrl.c.inc.patch`：
     `if (((immu18 >> 16) & 0x3) == 0x3)` → `if (immu18 >= 0x3FF00)`；相关注释同步。
   - 遵守 `docs/Process-01`（一文件一补丁、`git apply` 校验、`check-patch-tree`）。
2. **调用点** `0x30000` → **`0x3FF00`**（低 8 位 op 不变；注释里的 `immu18[17:16]==2'b11` 改新判据）：
   - `tests/scripts/bootrom_app.S`、`tests/scripts/codegen_crt0.s`、`tests/scripts/build_test_binary.py`（`SEMIHOST_TAG`）。
   - `tests/llvm/codegen/m5/`：`m5_semi_exit.s`、`m5_semi_exit_extended.s`、`m5_semi_write.s`、`m5_semi_writec.s`、`m5_semi_write0.s`、`m5_trap_escape.s`、`m5_perm_*.s`、`expected.yaml`（说明文字）。
   - `tests/e2e/smoke_add.s`、`tests/e2e/smoke_jump.s`。
   - `tools/qemu/min_rom_probe_*.py`：`SEMIHOST_TAG` 与注释。
   - `tests/case-ledger.tsv`：改完用 `python3 tools/infra/check_case_ledger.py --write` 重生成（**禁手改**）。
3. **组件侧调用点（architect 授权的必要扩围，2026-10-26）**：`0x30000` → `0x3FF00` + 注释判据同步：
   - `components/picolibc/patches/libos/semihost/machine/dadao/semihost-dadao.S.patch`（+ `components/picolibc/README.md` 文字）。
   - `components/embench-iot/patches/examples/dadao/boardsupport.c.patch`。
   - `components/musl/patches/arch/dadao/syscall_arch.h.patch`（**仅注释** `immu18[17:16] != 2'b11` → `immu18 < 0x3FF00`，无功能改动）。
   - 三个组件 changelog 各追加 `QEMU-076t` 条（`Process-01 §10`）。
4. **明确不动**：
   - `tests/vectors/isa/mem-rd.yaml` 等里的指令字（`0x30043081`/`0x30043080` 是编码，不是 semihosting）。
   - `0x30001`（HBI INIT，服务号）。
   - `spec/DADAO-22:863` 的 `0x3FFFF`（D3 待定，ISS-334）。
   - 任何 `0x3FFFF` 的 immu18 掩码常量（SBI 示例里的掩码提取）。

### 构建与验证
- 改 QEMU 补丁 ⇒ **必须重建**：`make build-qemu`（申报预计耗时；`JOBS=8`，禁 `-j$(nproc)`；>10 min 用 `setsid nohup` + `XXX_EXIT=$rc` 落盘，不阻塞会话）。
- `make build-bootrom`（bootrom_app 改动）。
- 门控：
  - `make check`
  - `make check-qemu-smoke`、`make check-qemu-semantics`（semihosting 用例）
  - `make check-lit`、`make check-case-ledger`、`make check-patch-tree`
  - `make check-milestones-fresh`
- grep 断言（贴输出）：
  - semihosting 上下文 `0x30000` / `immu18[17:16]` 计数 = 0；
  - `0x3FF00` 就位；`0x30043081`/`0x30043080` 编码行未变；`0x30001` 未变。
- 证据脚本 `.work/evidence/QEMU-076t/run.sh`（含注入→FAIL→还原→PASS）。

### 约束
- 只改上述文件；不改 spec/contracts/LLVM 模型。
- 临时目录 `/tmp/opencode/QEMU-076t/`；不提交、不 push。
- 反例还原用 `cp`+md5，禁 `git checkout/restore/stash`。
- 完成区 ≤30 行，贴命令/退出码/计数；状态 `待验收`，`milestones.md` 行同步。

## 验收标准
1. 上述门控 rc=0；QEMU 重建成功（`build-qemu: PASS`）。
2. semihosting 用例（`m5_semi_*`、bootrom_app、e2e smoke）全绿；旧 tag 计数 0。
3. 未误改指令编码字/`0x30001`/`0x3FFFF` 掩码（diff 对照）。
4. 证据脚本自检可达 FAIL；完成区与真实输出逐条对齐。

## 完成区

**状态**：已验证

**测试结果**：授权门控 7/7 全绿；扩围后组件侧全绿（picolibc `pass=18 excluded=2 blocked=0`、Embench 38/38、musl freshness PASS）；`test-m6` rc=2 仅卡既有 `diff_ir_lli` 结构缺口（见遗留）。

**修改文件**（56）：
- `components/qemu/patches/target/dadao/{insn_trans/trans_ctrl.c.inc,helper.c}.patch`：判据 `((immu18 >> 16) & 0x3) == 0x3` → `immu18 >= 0x3FF00`（helper 同源防御分支与注释同步）；源树 `commit --amend` 后 `make_patch.py qemu` 导出（Process-01，未手编 `.patch`）。
- 调用点 `0x30000` → `0x3FF00`：`tests/scripts/{bootrom_app.S,codegen_crt0.s,build_test_binary.py}`、`tests/llvm/codegen/m5/`（9 个 `.s` + `expected.yaml`）、`tests/e2e/smoke_{add,jump}.s` + **`smoke_arith.s`/`smoke_fp.s`（清单漏列，`check-lit` 红后补迁）**、`tools/qemu/min_rom_probe_*.py`（28 个）。
- **组件扩围（architect 授权）**：`components/picolibc/patches/libos/semihost/machine/dadao/semihost-dadao.S.patch` + `components/picolibc/README.md`、`components/embench-iot/patches/examples/dadao/boardsupport.c.patch`、`components/musl/patches/arch/dadao/syscall_arch.h.patch`（仅注释）。
- `components/{qemu,picolibc,embench-iot,musl}/changelog.md` 各追加 `QEMU-076t` 条；`tests/case-ledger.tsv` 用 `--write` 重生成（身份集未变，无 diff）。

**验收结果**（真实命令/退出码，日志 `.work/log/qemu/QEMU-076t-*`）：
- `build-qemu` rc=0 `build-qemu: PASS`；`install-host` rc=0；`build-bootrom` rc=0；`build-picolibc` rc=0；`build-musl-shared JOBS=8` rc=0（24 s）。
- `make check` rc=0 `repository checks (L1): PASS`；`check-milestones-fresh` rc=0；`check-component-changelog` rc=0；`check-musl-freshness` rc=0。
- `check-qemu-smoke` 90/90 rc=0；`check-qemu-semantics` 975/980（0 failed / 5 deferred）rc=0；`check-lit` 153/153 rc=0。
- `test-semihost` 10/10 + 25 服务 rc=0；`test-codegen`/`test-elf` PASS rc=0；`check-patch-tree` 202 patches rc=0；`check-case-ledger` rc=0。
- `check-picolibc-tests` rc=0：`total=20 pass=18 excluded=2 fail=0 blocked=0`（0 `CFXMEM 0x81`）。
- Embench E2E 单跑 rc=0：`Results: 38/38 passed, 0 failed`（25 s）。
- `make test-m6` rc=2：`[1/3]` lit-full 12/12 PASS、`[2/3]` `diff_ir_lli` 结构断言报 2 个未分类 `.ll`（既有 manifest 缺口）、`[3/3]` 未执行（已单跑，见上）。
- grep：迁移面 `\b0x30000\b`=0、`immu18[17:16]`/`2'b11`=0；`components/`（除 qemu）= **0**；安装根 `libsemihost.a` 的 `sys_semihost` 编码 `7f 03 ff 00`（trap 261888）；`mem-rd.yaml` 编码字、`0x30001`、`0x3FFFF` 原样（`git diff -- spec tests/vectors`=0）。
- 证据 `bash .work/evidence/QEMU-076t/run.sh` rc=0：**20/20 PASS**；注入 probe → 32 FAIL、注入 `libsemihost.a`（196608）→ C14 FAIL，均 `cp`+md5 还原回绿。

**新发现/坑**：
- 任务清单漏列 `tests/e2e/smoke_{arith,fp}.s`（同族调用点）；`check-lit` 先红 2/153，补迁后 153/153。`helper.c` 防御性 tag 分支与 `trans_ctrl` 同源，必须同步（最小必要扩围）。
- 组件侧 3 处调用点改补丁后必须重建产物：picolibc 走 `build-picolibc`、embench 每次 E2E 现编、musl 的**注释改动**也会让 `check-musl-freshness` 红（已 `build-musl-shared` 24 s 复绿）。
- `make test-m6` 的 `diff_ir_lli` 结构门控自 2026-10-24 后未随新 lit 向量更新：`cmp-u-branch.ll`/`code-model-large.ll` 未分类（LLVM-131t/133t 引入，与本任务无关）。

**遗留问题**：
- `make test-m6` rc=2（阻断在 `[2/3] diff_ir_lli`，**既有缺口**）：需把上述 2 个 `.ll` 加入 `tests/llvm/ir-lli/manifest.yaml` 的 `include`/`exclude`（越出本任务文件集，建议另立测试类小任务）；步骤 `[3/3]` Embench 已独立跑绿 38/38。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务清单漏列 `tests/e2e/smoke_arith.s`/`smoke_fp.s`，`check-lit` 2/153 红 | ✅已修 | 两文件 `trap cfx_umon, 0x30000` → `0x3FF00`（共 4 处） | `check-lit` rc=0 153/153；证据 C6 覆盖 16 个显式文件 |
| F2 `helper.c` 防御性分支仍用旧判据（与译码同源，留则守卫失效） | ✅已修 | `helper.c.patch` 条件与 3 处注释同步；`make_patch` 重导出 | C2 `new=1 old=0`；`check-patch-tree` 断言⑥⑨通过 |
| F3 注释残留 `0x3000_0` 与嵌套括注、判据措辞不统一 | ✅已修 | `m5_semi_writec.s` 两行、`expected.yaml`、046t/045t 文本改写 | C4 迁移面 `immu18[17:16]`/`2'b11`=0 |
| F4 证据脚本 C7 用 `awk -F:` 解析单文件 `grep -rc` ⇒ `hbi=0` 假 FAIL | ✅已修 | 改 `grep -rho ... | wc -l` | 14/14 PASS（`hbi=5`） |
| F5 证据注入是否真生效未断言 | ✅已修 | C12a 断言 md5 改变 + `FAIL>0` + rc≠0；C12b `src==backup==orig` | 注入 32 FAIL → 还原 md5 `0c9bc2f9…` → 33 PASS |
| F6 picolibc/embench 组件 stub 未迁移 ⇒ L2 回归 | ⏸延后 | 未改（越出任务允许文件集，需重建组件） | `check-picolibc-tests` rc=2（20 blocked CFXMEM）已留证 |

**自审判决**：F1–F5 已修并复验；F6 越界需 architect 裁定（已登记遗留）⇒ 置 `待验收`。

#### 第 2 轮 engineer 自审（architect 授权扩围后）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F6→F7 组件侧 3 处调用点未迁移（上轮 ⏸，本轮 architect 授权） | ✅已修 | picolibc/embench/musl 3 个 `.patch` + picolibc `README.md`；源树 amend + `make_patch` 导出 | `check-picolibc-tests` rc=0（18 pass/2 excluded/0 blocked）；Embench 38/38；`check-patch-tree` 202 |
| F8 musl 仅注释改动仍使 `check-musl-freshness` 红（产物与源不同源） | ✅已修 | `make build-musl-shared JOBS=8`（24 s） | freshness rc=0、`make check` rc=0 |
| F9 changelog 摘要复述旧 tag token 使组件侧 grep 非 0 | ✅已修 | 3 条 changelog 摘要改为「旧 tag → `0x3FF00`」 | `components/`（除 qemu）旧 tag/旧判据 = **0** |
| F10 证据未覆盖组件侧 | ✅已修 | 增 C13（3 patch）、C14（安装根 stub 编码）、C15（Embench）；C14 增注入/还原 | 20/20 PASS；注入 `libsemihost.a` → 196608 ⇒ FAIL ⇒ md5 还原回绿 |
| F11 `make test-m6` `[2/3] diff_ir_lli` 报 2 个未分类 `.ll` | ⏸延后 | 未改（既有 manifest 缺口，LLVM-131t/133t 引入，越出任务集） | `git diff -- tests/llvm/ir-lli tests/llvm/lit/CodeGen/DADAO`=0；`[1/3]` 12/12、`[3/3]` 单跑 38/38 |

**第 2 轮判决**：F7–F10 已修并复验；F11 为既有缺口（不影响 semihosting 迁移）⇒ 保持 `待验收`。

#### 第 1 轮 reviewer 验收（2026-10-26，全部为 reviewer 自己的重跑输出；日志 `/tmp/opencode/QEMU-076t/review/`）

- **门控重跑（退出码均为命令自身，非管道）**：`make check` rc=0（`repository checks (L1): PASS`）；`check-patch-tree` rc=0（`5 component(s), 202 patches OK`）；`check-case-ledger`/`check-component-changelog`/`check-musl-freshness`/`check-milestones-fresh` 各 rc=0；`check-qemu-smoke` rc=0（`total=90 passed=90`）；`check-lit` rc=0（`153/153`）；`check-qemu-semantics` rc=0（`980 total, 975 passed, 0 failed, 5 deferred`）；`check-picolibc-tests` rc=0（`total=20 pass=18 fail=0 excluded=2 blocked=0`）；Embench `python3 tools/integ/run_embench_e2e.py …` rc=0（`Results: 38/38 passed, 0 failed`）；`bash .work/evidence/QEMU-076t/run.sh` rc=0（`checks=20 pass=20 fail=0` / `EVIDENCE: PASS`）。
- **完成区声明追补核对**：`test-semihost` rc=0（10/10 + 25 服务 `RESULT: PASS`）、`test-codegen` rc=0（15/15）、`test-elf` rc=0（5/5）、`check-source-state` rc=0（6 源树 `clean=True`，base+1）。
- **独立反例（非 engineer 注入）**：`tests/e2e/smoke_add.s` 两处 `0x3FF00`→`0x30000`，md5 `ae6cf05556f0408d3b6746838d7716a9`→`b2f380a497f9a439f6ab48ebfaa3b524` ⇒ `make check-lit` **EXIT=2**（`FAIL: DADAO-E2E :: smoke_add.test`，`Passed: 152 / Failed: 1`）+ 证据脚本 **EXIT=1**（`C3 actual=2`、`C6 bad=1`，`checks=20 pass=18 fail=2 EVIDENCE: FAIL`）；`cp` 备份还原（md5 回 `ae6cf055…` 相等，**未用** `git checkout/restore/stash`）⇒ `check-lit` rc=0（153/153）、证据 rc=0（20/20）、`git status --porcelain -uall` 空。
- **语义/范围核对**：`trans_ctrl.c.inc` 与 `helper.c` 均为 `if (immu18 >= 0x3FF00)`（源树 `.work/source/qemu` 同文、HEAD `f8804ed` clean；build 12:59:59 晚于补丁 12:59:26；build==install md5 `d1f6bd61…`）；迁移面与组件侧（除 qemu changelog 叙述）`\b0x30000\b`、`immu18[17:16]`、`2'b11` 计数=0；`git diff master -- spec tests/vectors contracts` 空；`0x30001`、`spec/DADAO-22:863` 的 `0x3FFFF`、`mem-rd.yaml` 的 `0x30043081/0x30043080` 原样；4 个组件 changelog 各含 `QEMU-076t` 条；`check-case-ledger` 通过且 `tests/case-ledger.tsv` 对 master 无 diff。
- **`test-m6` rc=2 归因（复核）**：我跑 `make test-m6` **EXIT=2**（`[1/3]` 12/12 PASS；`[2/3] diff_ir_lli: FAIL (structural)` `unclassified=2` → `tests/llvm/lit/CodeGen/DADAO/{cmp-u-branch.ll,code-model-large.ll}`）。`git diff master -- tests/llvm/ir-lli tests/llvm/lit` 为空、master 的 `manifest.yaml` 对这两名 0 命中、两 `.ll` 在 master 存在、引入提交 `658afb1a`(LLVM-131t)/`8eec0cc5`(LLVM-133t) 均为 master 祖先 ⇒ **既有 manifest 缺口，非本任务引入**（finding，不改，建议另立小任务）。
- **越界/残留**：`git show --stat 5834e078` 58 文件全落在任务书清单 + architect 授权扩围内；未触 `Makefile`/`contracts/`/oracle/`tests/vectors`/`spec/`；无 `*_tmp*`/`*.orig`/`*.preinject` 残留；前后快照 md5 逐项相等。
- **Findings（均不阻断）**：① 完成区「修改文件（56）」vs `git show --stat`=58（含任务书 + `milestones.md`，口径差 2，文档级）；② 旧口径文档残留：`README.md:60`、`docs/Machine-00-执行环境分层-Draft.md:12`（标「现状」）、`docs/DDLN/*`、`.tao/knowledge/audits/cfx-audit-2026-10-26.md`——均在任务书未列文件、非门控扫描面，建议 architect 收尾统一措辞；③ 证据 C8 用工作树 `git diff`（提交后对「已提交的越界」无鉴别力），已由 reviewer 用 `git diff master -- spec tests/vectors contracts` 补核为空。
- **判决：Accepted** —— 验收命令在 reviewer 自己的重跑下全部 rc=0，反例注入有鉴别力且还原回绿，硬约束（文件集、不改 spec/契约、`cp`+md5 还原、不提交）无违反。
