# TESTCASES-078t: SPASS/lemon 语料 UB 修复与 SPASS 参考重定

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-076t、TESTCASES-069t
**状态**：已验证

## 背景（自包含，2026-10-27 全量实测）
1. **SPASS**（`MultiSource/Applications/SPASS`）：
   - `cnf.c:2760` 把 `int symbol_Equal(int,int)` 强转 `BOOL(*)(POINTER,POINTER)`；bank 分离 ABI 下 caller 传 `rb16/rb17`、callee 读 `rd16/rd17`（`0x510fc` → `0x46758`）⇒ 自由变量过滤错 → `list_Top(NULL)`，guest SIGSEGV（si_addr=0x8）。
   - `TESTCASES-069t` 在 `/tmp` 副本改成匹配原型 wrapper 后，DADAO `-O2` 构建 rc=0，stdout+exit md5 `74365d61…`，与**宿主 gcc 构建逐字节相同**；但仍 ≠ 上游 `SPASS.reference_output.small` 的 `b0b56c51…`（已登记 **ISS-338**）。
2. **lemon**（`MultiSource/Applications/lemon`）：
   - `lemon.c:334` 以空参数表声明 `Configtable_clear`；`:1127-1133` 以 `Configtable_clear(0)` 调用；`:4839-4840` 定义参数为 `int(*f)(struct config *)`。C11 6.5.2.2p6 下 `0` 保持 int，与指针参数不兼容 ⇒ UB；DADAO 下调用读到 stale 指针，输出 `Error while running on: <input>`，md5 oracle 不可达（已登记 **ISS-277**）。
   - x86-64/riscv64 因 int/pointer 共用寄存器而「碰巧可用」。

## 目标
1. **语料 UB 修复（可控、可审计；用户 2026-10-27 选 A）**：以**测试胶水 patch** 修复两处 UB——补丁落 `tests/tset/llvm-ts/patches/`，驱动在编译前应用到 `.work/` 工作副本并记录补丁 sha；**`llvm-test-suite` 保持 `patchless=true`，不改 components.lock，不新建组件 patch set**：
   - SPASS：把 `symbol_Equal` 调用改为匹配原型（或等价、语义等价的 wrapper），保留 SPASS 原逻辑；
   - lemon：给 `Configtable_clear` 加原型/正确调用，使 `0` 以空指针传递。
2. **SPASS 参考重定**：先做**判别实验**——用宿主 gcc 分别构建「未修改语料」与「修 UB 后语料」，跑同一输入/选项，比较输出+exit md5 与上游 `b0b56c51…`：① 若未修改 == 上游参考、修 UB 后 == `74365d61…`，则修 UB 确实改变了行为，上游参考对修复后语料失效，需按**可复现、独立于 LLVM/QEMU**的方式重定（记录 gcc 版本/选项/输入/哈希）；② 若未修改 != 上游参考，先查参考的输入/选项/版本来源，不得直接改参考。不得用 DADAO 自身输出作 oracle。
3. 不把 SPASS/lemon 降级为 known-fail；修复后两者须 **pass**（输出+exit 与重定参考一致）。

## 验收
- 定向（static+dynamic）：`SPASS`、`lemon` 均 pass；SPASS 参考哈希与重定记录一致；lemon 输出 oracle 可达。
- `make check-tset-llvm-full`（static+dynamic）rc=0（与 077/079 合并后全量无未知 fail/blocked）。
- 参考重定证据：宿主 gcc 版本/命令/输入/输出 md5，及与 DADAO 输出的逐字节对账；`ISS-338`/`ISS-277` 更新或关闭（按实际）。
- `make check` rc=0；证据 `.work/evidence/<任务号>/run.sh`（含注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-078t/`。

## 约束
- 只改本任务范围内的 `tests/tset/llvm-ts/`、`tools/testcases/tset/llvm-ts/`、补丁/胶水、索引/ledger、任务书/milestones；不改 spec/qemu/LLVM 语义。
- 上游源码只读：补丁/胶水必须可重复应用、可审计；**不修改 `manifests/components.lock.toml` 的 `patchless`，不建 `components/llvm-test-suite/patches/`**；不得把 `tests/tset/llvm-ts/` 变成上游源码副本。
- **不提交、不 push**；长构建/长跑申报预计耗时；不跑无关全量。

## 完成区

**状态**：已验证
**用户裁定**（2026-10-27，原话摘要）：「A：测试胶水 patch」——补丁落 `tests/tset/llvm-ts/patches/`，驱动应用到 `.work/` 副本；`llvm-test-suite` 保持 `patchless=true`，不改 components.lock；本批不跑全量/夜跑。

### 修改文件
- `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`：新增 `CASE_SOURCE_PATCHES`（逐例源码补丁 → run 副本；dry-run + 声明文件/补丁 `+++` 集合对账 + 逐文件 sha256 前后断言）+ 打补丁后编译 run 副本；删 lemon `PLATFORM_GAP_SIGNATURES` 行（根因已修，回归应记 `fail`）。
- `tests/tset/llvm-ts/patches/glue/spass_symbol_equal_ptr.patch`、`lemon_configtable_clear_prototype.patch`（新，胶水补丁）。
- `tests/tset/llvm-ts/README.md`、`tests/tset/llvm-ts/patches/README.md`（口径/来源）。
- `.tao/knowledge/issues.yaml`（ISS-338 → closed）、`.tao/knowledge/milestones.md`、本册。
- `.work/evidence/TESTCASES-078t/run.sh`（证据，不入库）。

### 验收命令与结果
- **判别实验**（宿主 gcc 13.3.0；`-O2 -DNDEBUG -w -DCLOCK_NO_TIMING -fno-strict-aliasing`；输入 = 上游 `RUN_OPTIONS` `small_problem.dfg`）：
  未改语料 `md5(stdout+stderr+"exit 0\n") = b0b56c51…` **== 上游 `SPASS.reference_output.small`**；修 UB 后同值 `b0b56c51…`；同构建多传 `-DocProof` = `74365d61…`（**069t 的哈希来源，非参考方差**）。lemon 未改/修 UB 均 `8c485439…`（上游 `lemon.reference_output`）⇒ **无需重定参考**。
- **DADAO 定向两档**（`--link-mode both --only 'SPASS$' --only 'lemon$'`）：static/dynamic 均 `total=2 pass=2 fail=0 known-fail=0 blocked=0`；两例 `md5(output+exit)` 命中上述上游参考，且 stdout sha256 与宿主修 UB 构建**逐字节相同**。
- **一键证据**：`./.work/evidence/TESTCASES-078t/run.sh` → **29/29 PASS**（含 corpus patchless、补丁 dry-run、注入“仅 `#include`”补丁 ⇒ SPASS `fail`+guest SIGSEGV → `cp`+md5 还原 → 回绿）。
- **L1**：`make check` rc=0（`/tmp/opencode/TESTCASES-078t/evidence/make-check.log`）。

### 新发现/坑
- 069t 的 `74365d61…` = 同构建多传 `-DocProof`（上游 RUN_OPTIONS 只有输入文件）；bank 分离 ABI 的 UB 修复在宿主上不改变输出，目标侧修后即命中上游参考。
- 源码补丁必须校验“声明文件确实变化”，否则空/陈旧补丁会假绿；并须核对补丁 `+++` 文件集合 == 声明集合，否则未声明文件的 hunk 会应用却不参与编译。

### 遗留
- 全量 `check-tset-llvm-full` 两档未跑（用户 2026-10-27 裁定本批不下发全量/夜跑），留待全量批次；其它非本册 fail/blocked 项（gawk/make/p2c/archie-client/plot2fig、ClamAV）不在本册范围。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 补丁声明的文件集合可能与补丁实际 `+++` 文件不一致 ⇒ 未声明 hunk 应用但不编译 | ✅已修 | `apply_source_patches` 解析 `+++ b/…` 并与 `files` 对账 | dry-run 两例 OK；注入补丁（仅 `cnf.c`）仍通过声明对账并复现 fail |
| F2 dry-run 依赖 `patch` 的英文 `checking file` 文案（locale 脆弱、且非必需） | ✅已修 | 去掉文案断言，改为 rc + 逐文件 sha256 前后比对（更强） | 两例 normal run PASS；注入“无变化补丁”路径由 sha 断言覆盖（代码级） |
| F3 证据脚本多处 `report ... "$(cmd)" "$?"` 会把 `$?` 取成命令替换的状态 | ✅已修 | 先 `rc=$?` 再 `report` | 29/29 全绿，失败项均带真实 rc |
| F4 删除 lemon gap 行是否放宽分类 | ❌不修（有据） | 保留删除 | 该行原为 `blocked` 逃逸；根因已修，回归应记 `fail`；`static.declarations` 断言其不存在 |

**自审判定**：F1–F3 已修并复验，F4 有据不改；无未修项 → `待验收`。

### 第 1 轮 reviewer 验收

**重跑（本人前台执行，真实输出/退出码）**
- `bash .work/evidence/TESTCASES-078t/run.sh` → `TESTCASES-078t evidence: PASS (29/29 checks)`，`RC=0`（real 8m05s；`grep -c '^  OK'`=29、`^  FAIL`=0）。
- `python3 tools/testcases/tset/llvm-ts/run_llvm_ts_user.py --link-mode both --only 'SPASS$|lemon$' …` → `RC=0`；static/dynamic 均 `total=2 pass=2 fail=0 known-fail=0 blocked=0`；SPASS `md5==b0b56c51bc8f86a45423934c5ad42b9f`、lemon `md5==8c4854398b356b594ac3bbe1f0e3f4dc`，两档 `stdout sha256` 与宿主修 UB 构建逐字节相同。
- `make check` → `RC=0`，尾行 `repository checks (L1): PASS`。
- 判别实验（脚本实测）：宿主 gcc 13.3.0 未改/修 UB 均 `b0b56c51…`，多传 `-DocProof` = `74365d61…`；lemon 未改/修 UB 均 `8c485439…` ⇒ 参考无需重定，与完成区一致。

**独立反例（与 engineer 的 include-only 注入不同）**
- 从补丁删「调用点 hunk」（留 include + wrapper 定义）：md5 `9a35dafe…`→`d7bf3481…`；语料副本 `patch --dry-run` `DRYRUN_RC=0` ⇒ 走真编译路径非 blocked。
- 静态跑 SPASS → `DRIVER_RC=1`、`klass=fail`、`guest_signal=SIGSEGV`、`si_addr=0x0000000000000008`、`counts={'pass':0,'fail':1,…}`。
- `cp` 备份回 + md5 `9a35dafe95c727bff8318997fe4c6300` 相等、`git status -- <patch>` 空 → 重跑 `DRIVER_RC=0`、`klass=pass`（未用 git checkout/restore/stash）。

**约束核验**
- 范围：`git show c41e4e57` 8 文件全在完成区；`manifests/`+`components/` 改动 0 行；`components/llvm-test-suite/patches/` 不存在；语料 `git status -uall` 0 行、HEAD `2919e551`；spec/qemu/LLVM 语义未动。
- 补丁只作用 run 副本：`apply_source_patches` 声明 `files` ↔ 补丁 `+++` 集合对账 + dry-run + 逐文件 sha256 前后不等（日志 `cnf.c 1ea4a30f2053 -> 9645c922b390`）。
- 快照对账：审前/审后 `git status --porcelain -uall` 均 0 行；三目标文件 md5 审前后一致（`6c8cefaf…`/`9a35dafe…`/`017df340…`）；无 `*_tmp`/`_gate`/`*.orig`/`*.rej`。
- 过程注：上轮 reviewer 遗留的同脚本后台进程（01:37:35 起）与本轮注入竞争，已等其 `RUNSH_EXIT=0` 退出后才注入。

**finding F-R1（阻断）**
- `run.sh:114-117 static.corpus_patchless` 只把 `git status` 的退出码当 rc；脏树 git 仍返回 0（本人实测临时仓：dirty → `rc=0` 3 行、clean → `rc=0`），全仓 grep 确认 driver 也无语料清洁门控 ⇒ 「语料就地改脏 ⇒ FAIL」路径不可达、对自身条件恒真，而它是「补丁只应用 run 副本、未改上游树」的唯一门控（假绿风险）。
- 修法：按现场行数算 rc——`n=$(git -C "$SUITE" status --porcelain | wc -l); rc=$([ "$n" -eq 0 ] && echo 0 || echo 1)`（`actual` 保留 `"$n line(s)"`）；勿用 `git status --exit-code`：本机 git 2.43 实测 `error: unknown option 'exit-code'`。改后重跑 `run.sh` 应仍 29/29。

**判决**：**Needs Revision**（仅 F-R1；其余验收命令与约束全部由本人重跑实测通过）。

### architect 收尾（2026-10-28）
- reviewer 唯一阻断 F-R1 = 证据脚本 `static.corpus_patchless` 把 `git status` 退出码当 rc（脏树仍 0，假绿）；已修：脏行数 >0 或 git rc≠0 ⇒ rc=1。
- 修复后重跑 `.work/evidence/TESTCASES-078t/run.sh` = **29/29 PASS**（rc=0）；交付语义未改，按文档级小错收尾。
