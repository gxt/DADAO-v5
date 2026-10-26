# TESTCASES-072t: inst 迁移（vectors/isa + 探针 + harness）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-071t
**状态**：已验证

## 目标（P2）
1. `tests/vectors/isa/*` + `atomics/clmul/fma/minmax/roundint` 探针 → `tests/inst/<ext>/`。
2. harness：`tests/scripts/{build_test_binary.py,run_qemu_test.py,run_qemu_smoke.py,...}` → `tools/testcases/{lib,inst}/`；`tests/scripts` 留薄 wrapper。
3. 新门控：`check-inst-smoke`（L2，代表集）、`check-inst`（L3，全量）；旧 `check-qemu-smoke`/`check-qemu-semantics` 保持别名。
4. 更新 `tests/inst.yaml`、`case-ledger.tsv`、Makefile/文档引用。

## 验收
- 新路径可跑；旧入口仍可跑（等价结果）；`check-inst-smoke` 绿；`make check` 绿；无期望改动。

## 约束
- 只改本任务范围内的 `tests/`、`tools/testcases/`、`Makefile`、索引/`case-ledger`、`milestones.md`；不改 spec/qemu/LLVM 语义。
- **旧路径/旧门控在本任务内保留**（薄 wrapper/别名）；删除旧入口只在 `TESTCASES-076t` 做。
- 不改测试期望、不放宽断言；只做“搬家 + 接线 + 兼容层”。
- 只跑 smoke/定向；全量 `check-full`/夜跑留到 `TESTCASES-076t` 或任务空档。
- 临时目录 `/tmp/opencode/<任务号>/`；不提交。

## 完成区

**测试结果**：`.work/evidence/TESTCASES-072t/run.sh` ⇒ **52/52 PASS, RESULT: PASS（rc=0）**；内置 2 处注入（重复 ID / wrapper 指向不存在实现）→ 各自 FAIL → `cp`+md5 还原 → 回绿。

**修改文件**（只搬家/接线/兼容；无期望值改动）：
- 搬迁：`tests/vectors/{isa→base,rol,atomics,clmul,rev,bitcnt}` + `tests/{atomics,clmul,fma,minmax,roundint}/*` → `tests/inst/<ext>/`（`README/schema/inventory.md` 随迁）；旧目录删除
- harness：`tests/scripts/{build_test_binary,run_qemu_test,gen_trampoline,verify_harness_dump,test_harness_exit_path}.py` + `trampoline.bin` → `tools/testcases/lib/`；`run_qemu_smoke.py` → `tools/testcases/inst/`；`tests/scripts/` 留 6 个薄 wrapper + `trampoline.bin` 符号链接 + README
- 门控：`Makefile`（+`check-inst`/`check-inst-smoke`；旧 `check-qemu-{semantics,smoke}` = 指向新目标的别名；L2/L3 成员表只列新名；L3 载体根 = `tests/inst`）
- 接线：`tools/qemu/{semantics_gate,generate_{atomics,clmul,rol}_vectors,check_005t_coverage,check_harness_ops,min_rom_probe_010t}`、`tools/testcases/{validate_vectors,generate_isa_vectors,generate_misc,generate_bitcnt_vectors,generate_rev_vectors,run_{atomics,clmul,fma,minmax,rnd}_probe,009t-audit,picolibc_tests}`、`tools/infra/check_case_ledger`、`tools/integ/check_interface_alignment`
- 索引/台账/文档：`tests/inst.yaml`（40 条）、`tests/case-ledger.tsv`（重生成）、`tests/{README,INVENTORY,qemu/README,llvm/ir-lli/README}`、`docs/{Process-05,07,09,Machine-00,fp-oracle-design}`、`spec/README.md`、`AGENTS.md`、`.opencode/commands/dispatch.md`、`.tao/knowledge/milestones.md`、本任务书

**验收结果**（真实输出；日志 `.work/log/testcases/TESTCASES-072t-*.log`、`/tmp/opencode/TESTCASES-072t/`）：
- `make check` rc=0（`repository checks (L1): PASS`）；`make check-interface`（L2 静态）rc=0
- `make check-inst-smoke` rc=0：代表集 90/90（= 独立派生 `(class,mnemonic)` 组数）；旧 `make check-qemu-smoke`（别名）rc=0，同 90/90
- `check-inst` 结构派生（`--check-only`）：载体 20 册 / 980 例 == 独立统计；L2 3 册登记一致
- `make check-tests-index` rc=0（inst=40 = 用例文件数）；`make check-case-ledger` rc=0（1962 行；排序后 == 旧清单仅路径重映射）
- 生成器 `--check` ×5（rev/bitcnt/atomics/clmul/rol）byte-identical ⇒ 用例与期望值未改
- 旧入口：`python3 tests/scripts/run_qemu_test.py tests/inst/base/reg-arith.yaml --case 0` PASS；旧路径 `tests/vectors/isa/...` 经兼容层 PASS；`tests/scripts/test_harness_exit_path.py` 5/5
- 探针抽检（单档）：rnd 785/785、clmul 627/627、fma 626/626、minmax 3102/3102、atomics 711/711

**新发现/坑**：① `check-inst` 的「git 索引缺册」断言在**未提交树**上必红 ⇒ 证据改用 `GIT_INDEX_FILE=/tmp/...` 临时索引（不动真实 index）；reviewer 同法。② 旧向量路径兼容层放在 lib runner（`resolve_legacy_vector_path`，仅平移已登记目录）。③ `tests/vectors/rol` 任务书未逐字列出，按「rev/bitcnt 一并按同样规则」归位 → `tests/inst/rol/`（L3 载体集不变：20 册/980 例）。④ 迁移前基线快照不可用（提交后漂移）⇒ 证据以「最近一次删旧路径提交的父提交」为基线。

**遗留问题**：① 全量 `check-inst`（980 例实跑）与旧名 `make check-qemu-semantics` 端到端未跑（任务约束：不跑全量 L3），留 `TESTCASES-076t` 全量验证。② `rev`/`bitcnt` 仍未入 L2/L3（语义同迁移前）。③ bootrom/lds/crt0/embench 胶水仍在 `tests/scripts/`（归 P3/P5）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `lib/run_qemu_test.py` 的 `_REPO_ROOT` 少上溯一层（`tools/` ≠ 仓库根）⇒ 首次 smoke 红 | ✅已修 | 改为 4 层 `dirname` | `make check-inst-smoke` rc=0（90/90） |
| 证据脚本根目录算成 `.work/` ⇒ 11 项「0==0」假绿 | ✅已修 | `ROOT` 改 3 层 + 新增「迁移前基线非空」防 vacuous 检查 | 脚本 52/52；`base_n=16+...` 非零 |
| 证据脚本以 `git HEAD` 为迁移前基线 ⇒ architect 提交后全红 | ✅已修 | `old_ref()`：取「删旧路径提交」的父提交，无则 HEAD | 预提交跑通；逻辑对提交后仍指向迁移前树 |
| `run_qemu_smoke` 迁到 `inst/` 后 `_REPO_ROOT`/trampoline 默认路径失效 | ✅已修 | 显式 3 层 + `tools/testcases/lib` 入 `sys.path` + trampoline 指 lib | smoke rc=0，代表集 90 |
| `check_harness_ops.py` 默认仍读 `tests/scripts/build_test_binary.py`（wrapper 无 `encode_*`）⇒ 22 项静默 SKIP | ✅已修 | 默认改 `tools/testcases/lib/...` | 运行输出 `all 22 ops match`，rc=0 |
| Makefile 旧名若保留独立实现会双跑/双份真源 | ✅已修 | 旧名改为 `_locked-*: check-inst(-smoke)` 别名；L2/L3 只列新名 | 证据「门控接线」检查 ok；旧别名 rc=0 |
| `case-ledger` 换目录后排序位置变化（`base` < `bitcnt`）易被误判内容改动 | ✅已修 | 证据按「排序后多重集」比对，另核对行数/vector 前缀 | `cmp` sorted 一致；行数 1962 不变 |

**判决**：全部 finding 已修，无未修项；状态 `待验收`。

### 第 1 轮 reviewer 验收

**文件分析**：`git show --stat 7fce080d`（101 文件）核对搬家映射：`vectors/{isa→inst/base, rol, atomics, clmul, rev, bitcnt}`、顶层探针 →`inst/*`、harness →`tools/testcases/{lib,inst}`、`tests/scripts` 留 6 薄 wrapper（全含 `runpy.run_path`）+ `trampoline.bin` 符号链接（`git ls-tree` mode=120000）；`tests/vectors/` 已不存在；Makefile：L2 只含 `check-inst-smoke`、L3 只含 `check-inst`、`_locked-check-qemu-{smoke,semantics}` 为别名；docs/spec/AGENTS 旧路径引用仅剩 `.tao/archive`/历史任务书（历史层，豁免）与 Process-09 已加迁移注记。

**重跑记录（reviewer 亲自执行，均在 workdir 内）**：
- `make check` rc=0（`repository checks (L1): PASS`；含 check-case-ledger/check-tests-index）
- `make check-inst-smoke` rc=0：`QEMU: total=90 passed=90 failed=0`（90 = 独立派生 (class,mnemonic) 组数）
- `make check-tests-index` rc=0：`inst=40`；独立用 yaml 解析复核 40 条、file 全存在、ID 唯一
- `make check-case-ledger` rc=0（1962 行；vector 1456 条全为 `tests/inst/` 前缀）
- `bash .work/evidence/TESTCASES-072t/run.sh` rc=0：**52/52 PASS, RESULT: PASS**（脚本逐条断言有可达 FAIL 路径，非恒真）
- 生成器 `--check`：bitcnt/atomics 亲跑 rc=0（byte-identical + oracle 重算）；rev 由 `make check`（check-rev-vectors）覆盖；clmul/rol 由证据脚本 rc=0 覆盖 ⇒ 期望值未改
- 旧入口：`python3 tests/scripts/run_qemu_test.py tests/inst/base/reg-arith.yaml --case 0` rc=0 `Result: PASS`；旧路径 `tests/vectors/isa/...` rc=0（打印「兼容层」映射后 PASS）；`make check-qemu-smoke`（别名）rc=0 90/90

**独立反例注入（非 engineer 注入项）**：`cp tests/inst/base/reg-compare.yaml → /tmp/.../review/`（md5 `ab0b6e7e…`），`sed` 改第 30 行期望 `rd1: 0x1→0x2` ⇒ `make check-inst-smoke` rc=2（`total=90 passed=89 failed=1`，`结果: FAIL`）；`cp` 还原 + md5 相等 ⇒ 复跑 rc=0 回绿（90/90）。注：首次 sed 行号偏移未命中（md5 未变、门控仍绿——非假绿），第 2 次命中后验证有效。

**快照对账**：验收前/后 `git status --porcelain -uall` 均 0 行（无残留、无注入遗留）；临时产物仅在 `/tmp/opencode/TESTCASES-072t-review/`。

**Findings（均不阻断）**：① 全量 `check-inst`（980 例实跑）与旧名 `check-qemu-semantics` 端到端未跑——任务约束明示留 `TESTCASES-076t`，已由结构派生（载体 20 册/980 例 == 独立统计）替代；② 约束字面只列 `tests/`、`tools/testcases/`、`Makefile`、索引/ledger、milestones.md，实际还改了 `tools/{qemu,infra,integ}`、`docs/*`、`spec/README.md`、`AGENTS.md`、`dispatch.md` 的路径接线/引用（目标 4 与完成区已列明，属接线必需，口径差为文档级）；③ Process-09 正文保留迁移前快照计数（已加注记声明）。

**判决**：**Accepted**（验收命令在 reviewer 重跑下全部通过；约束无实质违反；反例注入证明门控可失败且已还原）。
