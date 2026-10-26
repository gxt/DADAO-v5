# TESTCASES-072t: inst 迁移（vectors/isa + 探针 + harness）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-071t
**状态**：待验收

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
