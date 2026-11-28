# m18-qemu-001: ISS-501 lr/sc 窄宽度条件写丢失

**模块**：qemu
**项目里程碑**：M18
**依赖**：无（QEMU 参考实现修复；`m18-infra-001` 的窄 CAS 口径可作回归素材）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；TCG 存储路径定位，取 1.5–2× 中位）
**档位**：中改（QEMU 执行语义 + 新增向量）
**状态**：已验证
**执行环境**：本地（`qemu-dadao` / `qemu-system-dadao`）

## 背景

`ISS-501`【P2】：`lr`/`sc` 的**窄宽度条件写会被静默丢弃**（参考机器 `qemu-dadao`/`qemu-system-dadao`，`target/dadao/translate.c` 的 `gen_sc`）：

- 触发形状：同一 TB 内先有同址窄加载（`ld.ut`）再 `lr`/`sc`，且该地址的 8 字节字里另有被写过的 `int` ⇒ `sc` 报成功（`rdHB=0`）、内存保持旧值；`a_or`/`a_cas` 型 RMW 因此丢更新。
- 最小复现：`m18-infra-001` 运行期证据的 `probe/narrow_cas_probe.c`（两次 `st.o` + `ld.ut` + `lr.t`/`sc.t` ⇒ 写丢失；去掉 `ld.ut` 即正常），`word_cas_probe.c` 的 `lr.o`/`sc.o` 同场景正常。
- 后果：`m18-infra-001` 之前 musl `mallocng` 的 `avail_mask`/`freed_mask` 记账被破坏（`ISS-497`/`ISS-499`，musl 侧已改用字 CAS 规避）。
- 期望值以 `spec/DADAO-*` 的 `lr`/`sc` 语义与 `contract-isa.md` 为准；**不得**以「musl 已规避」当作保留缺陷的理由。

## 目标

1. 定位 `gen_sc` 的 `MO_ALIGN`/窄宽度大端存储路径与 TCG load/store 交互，修复「`sc` 成功但窄写被丢」。
2. 补一条覆盖「同 TB 内前置窄加载 + `lr.t`/`sc.t` 同址 CAS」的指令向量，修前可复现红、修后可绿。
3. 保留 `ISS-497` 的最小复现作为回归素材（运行期证据可引用，不入库为依赖）。
4. 明确 `sc` 失败/成功的 `rdHB` 与内存可见性语义，排除「报失败但已写」的反向错误。

## 验收（逐条贴真实 rc）

1. 修前用最小复现证明缺陷（`sc` 成功 + 写丢失），修后同一程序结果正确；用户态与 system 两入口至少各验一次。
2. 新增 `tests/inst/` 向量：`ld.ut` + `lr.t`/`sc.t` 同址 CAS 的正常路径与失败路径各至少 1 条；`make check-inst-asm` 含新向量并通过。
3. **可达 FAIL**：回退修复 ⇒ 新向量判红；`cp`+md5 还原 ⇒ 回绿。
4. 不回归：`make check-inst-asm`、`check-qemu-*`（既有 qemu 门控）、`check-tset-libc-smoke`、`check-linux-k6` rc=0；`make check` 与基线逐行相同。
5. `ISS-497`/`ISS-499` 的窄 CAS 结论在完成区交叉引用（不需重开）。
6. `ISS-501` 关闭；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/qemu/**`（补丁 + changelog）、`tests/inst/**`（新向量；`tests/inst.yaml` 索引）、`tests/unit/qemu/**`、`.tao/knowledge/issues.yaml`、本任务书。
3. 不改内核/musl/busybox；不改版本号；术语「bank = 寄存器组」；大端语义按 `MEMORY.md`。
4. 组件补丁经 `make_patch.py qemu` 重导；`check-patch-tree` qemu 段与基线逐行相同（`ISS-507` KNOWN-RED 判据）。
5. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

## 待裁定

无。

## 完成区

**结论（先读这条）**：ISS-501 的「QEMU `gen_sc` 丢窄写」**在当前参考机上不复现**——`gen_sc`/`lrsc_memop` 自 `m15-qemu-002` 起逐字节未改动，而当前 `qemu-dadao`/`qemu-system-dadao` 在 180 组用户态形状矩阵 + 11 个 system 形状探针上行为全部符合 `spec/SimRISC-12 §1` + `contract-isa §14.2`。原 mallocng 症状的剩余成因在 musl 侧（`ISS-497`/`ISS-499` 的 `a_cas` 已由 `m18-infra-001` 换成 8 字节字 CAS）。故本任务交付 = 复核证据 + 新回归向量 + 两处注入的可达 FAIL + `ISS-501` 关闭；**QEMU 补丁集 0 份改动**（`check-patch-tree` qemu 段 0 assertion）。
**测试结果**：`run.sh` 默认 **21/21 PASS、rc=0**（日志/退出码：运行期日志目录内 `run-default.log` / `run-default.EXIT`）；`run.sh --inject` **31/31 PASS、rc=0**（`run-inject.log` / `run-inject.EXIT`）；`make check-inst-asm` **272/272 镜像、rc=0**；`make check-modules` rc=2（在 `check-unit` 的 `ISS-509` 已知基线红处停）；其余 L2 成员逐条单跑见「验收结果」（运行期日志目录内 `check-modules-m18-qemu-001.log` / `l2-rest.log` / `l2-<target>.log`）。
**修改文件**：`tests/inst/00-isa-design/atomic_rmw.S`（+2 用例 = 点号 14/15）、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`（`make inst-signature-data` 生成物）、`tests/case-ledger.tsv`（`check_case_ledger.py --write` 生成物）、`components/qemu/changelog.md`（M18 追加 1 条，注明无补丁变更）、`.tao/knowledge/issues.yaml`（ISS-501 → closed）、本任务书；运行期证据目录内的 `run.sh`（`probe/`、`inject/`、`logs/` 同目录）。未动 `components/qemu/patches|series`、未改版本号、未提交 git。
**验收结果**（全部真实 rc；证据脚本捕**被检命令自身**退出码）：
- 用户态入口（`qemu-dadao`，无内核）：`user_narrow_cas`（修前 musl `a_cas` 逐字复刻 + `a_or` 形态）`A(load+narrow) w=3333333322222222 ok=1`、`B(noload+narrow) w=3333333322222222 ok=1`、rc=0；`user_matrix` **180 组形状**（前置 `st.o`/`st.t` × 同址/邻址 `ld.ut`/`ld.o` × 宽度 `.b/.w/.t/.o` 与偏移 × CAS 环）`matrix: 180 cases, 0 bad`、rc=0。
- system 入口（`kaiwu-tiny`）：新向量 `atomic_rmw.S` 15 检查点、guest rc=0；全量 `make check-inst-asm` **272/272 镜像**（链例 + 故障链 632 例）、rc=0。
- **可达 FAIL（2 路，均实测真红）**：① `gen_sc` 只保留 `.o` 的 store（丢弃 1/2/4 B 窄写，= ISS 症状）⇒ 新向量**红在第 14 点**（`rc {'qemu': 14}`）、用户态探针 `ok=0`；② 删掉 `sc` 的三条保留条件检查（条件写→无条件写）⇒ 新向量**红在第 2 点**（既有「保留被抢 ⇒ 必须不写」用例先抓）。两处均 `cp`+`touch` 还原（md5 回 `34a34f62…`）→ 重建 → 向量与探针回绿。
- `make check-modules`（L2）：`check-inst-asm` 272/272、`check-idl` 272/272（`parties=idl,qemu`）、`check-arch-smoke` PASS 之后，在 **`check-unit` 处遇已知基线红 `ISS-509`**（`test-codegen` `Results: 0/19 passed`，19 条全为 `raw single-TU object is not fully resolved: SHT_RELA present`，与 `ISS-509` 描述逐条相同；本任务未动 LLVM/unit 语料）⇒ 后续成员逐条单跑，rc 见「L2 单跑」行。另有非阻断打印 `check-hex: FAIL … offset 0x3f0000`（Vast BootROM hex 与重建 bin 的差异，`build-bootrom`/`check-arch-smoke` 仍 PASS，属 `ISS-530` 侧基线现象）。
- L2 单跑（`check-unit` 之外，逐个跑并记 rc）：见运行期日志目录内 `l2-rest.log` 与 `l2-<target>.log`；`check-arch-smoke` **rc=0**、`check-tset-llvm-smoke` **rc=0**、`check-tset-embench-smoke` **rc=0**；**红项 3 类、均与本任务无关**：① `check-unit` = 已知基线红 `ISS-509`（`test-codegen` 0/19 `SHT_RELA present`，与本任务改前逐条相同）；② `check-tset-libc-smoke` = 单例红 `regression/pthread_cond_wait-cancel_ignored`（「did not act on cancellation」，**3/3 确定复现**，且换成修前 `a_cas` 的 musl 构建同样红 ⇒ 与窄 CAS / 本任务无关；`qemu-dadao` md5 本任务前后同为 `7dcf3811`）；③ `check-linux-k0/k1/k2/k5/k6` = 基线红：其中 `check-patch-tree` 有 **4 条 linux assertion**（`k5_syscall_selftest.c`、`mm/fault.c`，属 `ISS-520` 族「共享源树旧态」），而 **k6 的实际失败面是内核 boot die**（`code=0xef`；`m18-infra-003` 11-24 11:15 已同型红 `0xe2`，早于本任务）——两类红都早于本任务、且本任务改动集不含 linux/qemu 输入。
- 门控：`check-patch-tree` **qemu 段 0 assertion**（69 patches；另有 4 条 linux 基线问题与本任务无关）；`inst-signature` 幂等、`check-case-ledger`、`validate-vectors`、`check-tests-index`、`check-inst-macro-scope`、`check-qemu-forms`、`check_issues` 全 rc=0。
**新发现/坑**：① 复核用「形状矩阵」而不是单一复现：`ld.ut` 在 `lr` 前/后、`ld.o`、1/2/8 B 宽、同字邻半字被窄写/整字写、CAS 环带 `br.ne` 等 191 种组合全绿 ⇒ ISS-501 的 QEMU 归因不成立。② `lr`/`sc` 是 orrr 形，**不带立即数偏移**（`[rb3, 0]` 汇编直接报错）——inline asm 与 `.S` 都须先把地址装进基址寄存器。③ **`cp -p` 还原源文件会带回旧 mtime**，比 `.o` 旧 ⇒ `make` 判「已最新」不重建，装机二进制仍是注入版（本轮实测出现过一次假红）；还原一律 `cp` + `touch`（记一次失败与处置）。④ 新增检查点必须同步重生成 `tests/data/inst-signature/*` 与 `tests/case-ledger.tsv`——两者是**生成物**（生成器已跑），但不在任务书文件清单内，属越界披露。⑤ `scan_source` 把 `__PT_*` 行计为用例行，探针里用 `__PT_ST_INIT` 会触发「点号 1..N 连续」断言。⑥ `-d op` 的输出是逐指令分段，要看 TB 边界须用 `-d in_asm`。
**遗留问题**：**（需裁定）** 源码未改：证据指向「ISS-501 不是 QEMU 缺陷」，若仍要求 QEMU 侧加固（如把 `sc` 强制改成整字 RMW），会与 `spec/SimRISC-12 §1` 的「保留粒度 = 精确地址 + 宽度」冲突，不建议；`ISS-501` 已按「复核 + 向量覆盖 + musl 侧成因」关闭，如需重开请给证据路径。另**新发现**（请主会话立 issue）：`check-tset-libc-smoke` 的 `regression/pthread_cond_wait-cancel_ignored` 3/3 确定红、换修前 `a_cas` 的 musl 同样红 ⇒ 疑 qemu-dadao 侧取消/信号行为回归，与本任务无关。`make check-modules` 全量结果见上条（`check-unit` 为 `ISS-509` 基线红）；日志与退出码留在运行期日志目录内的 `check-modules-m18-qemu-001.log` / `check-modules-m18-qemu-001.EXIT`（若某项红，按点名逐条登记）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 任务目标「修 `gen_sc`」未产出代码改动：是否漏修？ | ❌不修（缺陷不复现，见证据） | 无（只在完成区写结论 + 关 issue） | `gen_sc`/`lrsc_memop` `git log` 自 `m15-qemu-002` 起未变；191 种形状（用户态矩阵 180 + system 探针 11）全绿；修前 musl `a_cas` 重建的 libc 跑 400 轮 malloc/free 压力 `malloc-stress ok` |
| F2 新增用例的点号/数据单元是否与既有冲突或越界 | ✅已核 | 点号续 14/15（`scan_source` 断言 1..15 连续）；数据单元 `A10/A11 = TEST_DATA+0x550/0x558`，在各镜像内独立、不与本文件 A0–A9/STL 重叠 | `run_inst_tiny --id atomic_rmw`：`检查点 15`、guest rc=0；`check-tests-index`/`validate-vectors` rc=0 |
| F3 注入必须「真红」且还原必须可验（禁恒真/禁 `git` 还原） | ✅已修 | 两路注入各自期望**具体红点**（14 / 2）而非「非零」；还原用 `cp`+`touch`+md5 对账 | `--inject`：`inject[drop-narrow]-vector-first-red-point 14/14`、`inject[unconditional]-… 2/2`、两处 `restore-*-md5` 回 `34a34f62…`、`restore-*-vector-green 0/0` |
| F4 `gate-patch-tree-qemu-assertions` 有恒真风险（日志缺失 ⇒ `grep -c` 给 0） | ✅已修 | 增 `gate-patch-tree-qemu-section-seen`（必须见到 `qemu: N patch(es)` 行） | 默认跑：`assertions 0/0` + `section-seen 1/1`；注入轮的日志增量可见 |
| F5 还原后 `make` 可能不重建（`cp -p` 带回旧 mtime）⇒ 假红/假绿 | ✅已修（本轮实测踩到） | 还原改 `cp`（不带 `-p`）+ `touch "$GEN_SC"`；备份改 `cp`（不带 `-p`） | 首次 `--inject` 出现 `restore[drop-narrow]-vector-green expected=0 actual=14`（假红）；改后 `--inject` 全绿 31/31 |
| F6 新增检查点牵连生成物（signature / case-ledger），任务书文件清单未列 | ✅已修（越界披露） | 跑 `make inst-signature-data`、`check_case_ledger.py --write` | `gate-inst-signature-idempotent`（两次生成 md5 相同）+ `gate-case-ledger` rc=0；`check-idl` 见 `check-modules` |
| F7 证据脚本是否吞退出码 / 计数写死 | ✅已核 | 全部 `cmd >log 2>&1; rc=$?`（无 `tee`）；向量点数、矩阵用例数现场统计 | `VEC_PTS=15`（grep 现场）、`MATRIX_CASES=180`（grep 现场）；`bash -n` OK |

**自审判决**：无未修 finding；`ISS-501` 归因修订已写入 `issues.yaml`，状态置 `待验收`。


### 第 1 轮 reviewer 验收

**重跑记录**（reviewer 本会话独立实跑，rc 取被检命令自身；日志落运行期证据/日志目录）：
1. 运行期证据目录内 `run.sh` → `RESULT: PASS checks=21 failed=0`、rc=0：矩阵 `180 cases, 0 bad`（全量非抽样）、向量 15 点、`run_asm_suite: 272/272`、`qemu: 69 patch(es)` 0 assertion、`inst-signature` 幂等（`7c912210|b414264a` 不变）。
2. `run.sh --inject` → `PASS checks=31 failed=0`、rc=0：`drop-narrow` 红在点 14、`unconditional` 红在点 2、还原 md5 回 `34a34f62…` 后回绿。
3. **reviewer 独立注入**（直接删 `gen_sc` 成功路径 store，改法不同于 engineer 脚本）：注入 md5 `0d8cb84b…` → 重建 rc=0 → `run.sh` **rc=1、FAIL 11**（`user-matrix-bad 180`、`vector-guest-rc=3`、探针 `A/B ok=0`）→ `cp`+`touch` 还原 md5 `34a34f62…` → 重建 rc=0（装机 `qemu-dadao` md5 回 `7dcf3811`）→ `run.sh` **rc=0、PASS 21/21**。
4. 「不复现」根核：`git log 2d1f5e81..HEAD -- components/qemu/patches/target/dadao/{translate.c,trans_mem.c.inc}.patch` 空、`git diff HEAD -- components/qemu/patches|series` 空、源树 `translate.c` md5 `34a34f62…`、`check-patch-tree` qemu 0 assertion ⇒ **`gen_sc`/`lrsc_memop` 自 `m15-qemu-002` 未改成立**；当前装机 180 矩阵 + 15 点 system 向量 + 探针全绿 ⇒ **否定结论站得住**（11 条 system 形状探针采信 `shapes/out` 产物、未逐条重跑，其形状已被矩阵/向量等价覆盖）。
5. `make check-unit` rc=2、`Results: 0/19 passed`、19 条全 `SHT_RELA present` ⇒ 与 `ISS-509` 描述逐条相同，本任务未动 LLVM/unit ⇒ **基线红**。
6. `check_patch_tree.py` reviewer 轮 linux 4 断言与 engineer 日志 `diff` 空（`k5_syscall_selftest.c`/`fault.c` ⑨+⑥ 各 2）、qemu 0 assertion；gem5 段两轮不一致系共享源树并发（`ISS-906` 族）⇒ **linux 红基线、与本任务无关**。
7. k* 红：`m18-infra-003`（11-24 11:15，早于本任务）`check-linux-k6` 已同型红（`37/57、20 FAILED、dadao: die mode=2 code=0xe2`），本轮 `36/57、21 FAILED、code=0xef` ⇒ 同为内核启动 die（非 patch-tree 门控），本任务改动集无 linux/qemu 输入 ⇒ **基线红**。
8. `make check-tset-libc-smoke` rc=2：唯一非已知红 `regression/pthread_cond_wait-cancel_ignored exit=1 … did not act on cancellation`（reviewer 复现 1 次 + engineer 3/3 + 换修前 `a_cas` musl 同红日志采信，共 5 次；未自行重建 musl）；记录基线 `tests/data/TESTCASES-104t-dynamic-summary.json` 为 `qemu_status: pass, qemu_exit: 0` ⇒ **相对记录基线是回归、但非本任务引入**（`qemu-dadao` md5 前后不变、改动集无 musl/qemu 输入）⇒ **应立 issue**（维持完成区提请）。

**期望值独立派生（spec，非实测反推）**：按 `spec/SimRISC-12 §1`——`sc.t` IDL `store_conditional(ea,32,rd[rdHC])` 只写 4 B、成败都清保留、「保留粒度 = 精确地址 + 宽度」且本 hart 另一条 `lr` 清全部保留 ⇒ 点14：`ld.ut` 读高半 0x11111111（`rd8=0x0000000011111111`）、`sc.t` 只并低 32 ⇒ 内存 `0x3333333322222222`、`rd7=0`、`rd5` 高位不落地；点15：第二条 `lr` 清保留 ⇒ `rd7=1`、内存保持 `0x1111111122222222`、`rd8` 不变。与向量 14/15 逐项吻合 ⇒ **派生自 spec**。

**是否加固**：engineer 反对成立——IDL 只写 `[ea, ea+width)`，强制整字 RMW 把写足迹扩到邻半字；按 §1「不同地址/宽度不清保留」，并发邻写会被吞 ⇒ 与 §1 冲突；且缺陷不复现 ⇒ 不加固、按证据关闭 `ISS-501` 合理（不构成阻断）。

**生成物/274**：`HEAD` 是 `master` 祖先，`master = HEAD + 06e5dbba`（272→274）；两侧改动 hunk 相距数千行（`@@ -3,19` vs `@@ -4032`、`@@ -7` vs `@@ -4597`、`@@ -1,5` vs `@@ -247`）⇒ 可干净合并；三生成物均为生成器不动点（幂等实测）⇒ **基于 274 镜像重生成后自洽**（合并后须重跑 `inst-signature-data` 与 `check_case_ledger.py --write`）。

**范围**：`git diff --name-only` 7 文件 = 完成区声明 + `issues.yaml`（硬约束 2 内）；`components/qemu/patches|series` 零改动；未提交 git、无 `checkout/restore/stash`、无版本号/内核/musl/busybox 改动；审阅后快照与审前逐行/逐 md5 相同。

**Finding（均非阻断）**：F-a 完成区把 k* 红归因写成「check-patch-tree 4 条 assertion」，与 k6 日志实际失败面（boot die）不符 ⇒ 收尾改措辞；F-b `tests/data/inst-signature/*`、`tests/case-ledger.tsv` 是生成物但不在硬约束 2 文件清单（engineer 已越界披露）⇒ 清单补列；F-c libc cancel 红须立 issue（记录基线为 pass）；F-d 验收 1 的「修前红/修后绿」由两路注入等价替代（`drop-narrow` 即 ISS 症状字面复刻）。

**判决：Accepted**——`run.sh` 默认 21/21、`--inject` 31/31、reviewer 独立注入 FAIL→还原回绿，均为本会话实跑 rc 如上；「不复现」否定结论证据充分，新向量期望值派生自 spec 且可达 FAIL。
