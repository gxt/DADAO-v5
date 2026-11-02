# GEM5-005t: scaleB C1 与 sc rd0 解码更新

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-004t`、`SPEC-181t`
**状态**：待验收

## 用户授权

用户 2026-11-01：scaleB C1 第三源 `rfHD → rdHD`（同 `orrr` 编码）；`sc rdHB=rd0 ⇒ ILLI`；授权 gem5 独立任务。

## 目标

1. 更新 `components/gem5` 的 decode 表/断言：
   - `ftsclb`/`fosclb` 第三字段 `rfhd → rdhd`，编码/opc/ha 不变；
   - 旧 `rf,rf,rf` 断言删除/更新；
   - `sc.*` 的 12 条 `rdHB=rd0` 新增 `dst_rd0` 合法性断言。
2. 更新 `tools/gem5/gen_decode_table.py` 从当前 `contracts/opcodes.yaml` 生成；`decode-assertions.tsv` 同步。
3. 只改 `components/gem5/**`、`tools/gem5/**`、本任务书/milestones；不改 tests/spec/contracts/LLVM/QEMU/Makefile。
4. 执行语义实现不在本任务；B6 后续处理。

## 验收

1. `make check-gem5-decode` rc=0（264 正例 + 负例；新/旧字段反例）。
2. `check-patch-tree`/`check-source-state` rc=0；`make build-gem5`（增量）rc=0。
3. 旧 `ftsclb/fosclb rf` 必须 FAIL；`sc rd0` 负例必须 FAIL。
4. 证据 `.work/evidence/<任务ID>/`；完成区 ≤30 行，状态待验收。

## 完成区

**测试结果**：`make check-gem5-decode` rc=0：`summary: positive 264/264, negative 388/388, legality 28/28, legacy 2/2, failures 0`；证据 `.work/evidence/GEM5-005t/run.sh` rc=0（3 次注入→FAIL→`cp`+md5 还原→回绿）。失败 0。
**修改文件**：`tools/gem5/gen_decode_table.py`；`components/gem5/{README.md,changelog.md,decode-assertions.tsv}`；`components/gem5/patches/src/arch/dadao/decode/{decode_table.inc,decode_assertions.inc,decode_test.cc}.patch`（worktree 提交 `3bb64c72`，26 补丁不变）；本任务书、`milestones.md`。
**验收结果**：
- `make check-gem5-decode` rc=0（见上）；`gen_decode_table.py --check` rc=0（264 行，批次 38/8/42/63/28/30/55）。
- `make check-source-state` rc=0：`gem5: OK HEAD=3bb64c721a24 count=1 clean=True`；gem5 单组件 `check-patch-tree` 断言 1–9 全 0 problem。全量 `make check-patch-tree` rc=2：16 problem 全在 llvm-project(10)/qemu(6)（并行 LLVM-142t/QEMU-078t 占用共享工作树），gem5 无 problem。
- `make build-gem5` 增量 rc=0：`gem5.opt` 712,225,416 B，`--help` rc=0。
- 断言：264 正例行新增 `rules` 逐行校验；12 条 `sc.*` 断言 `rdhb != rd0` + `dst_rd0`；28 条合法性用例（sc dst=rd0⇒ILLI、rdhc=rd0 合法、scaleB rdhd=0 合法、scaleB dst=rf0⇒ILLI）；2 条旧 `rfhd/rf` 负例守护。
- 注入（`cp`+md5，未用 git checkout/restore）：① ftsclb 第三字段期望改回 `rfhd/rf` → harness rc=1 `[FAIL] row 246`；② sc.o.nn legality 1→0 → `[FAIL] legality sc.o.nn_orrr_rd`；③ 反转 sc rd0 期望 → 同上；三次还原 md5 一致、`git diff` 空、回绿。
**新发现/坑**：① `GEM5-002t` 矩阵仍写 `ftsclb/fosclb` 第三操作数 `rfhd[rf]`、`sc` legality 为空；矩阵在 `.tao/knowledge/refs/`（不在本任务可改范围），生成器只交叉核对 mnemonic/format/scope/opc/mask/value/opx，字段/legality 以 `contracts/opcodes.yaml` 为准。② B0 的 `decodeWord` 仍只做编码层判定，`dst_rd0/dst_rf0` 由 B1–B6 执行期映射 ILLI；本任务只落数据+断言（与 README 的 B0/B1 分层一致）。③ 共享工作树下全量 `check-patch-tree` 会因并行任务红（见验收结果）。
**遗留问题**：B1–B7 执行语义（`dst_rd0`/`dst_rf0` 的 ILLI 映射、scaleB 指数读取）未实现；GEM5-002t 矩阵未刷新（需另立任务）。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：逐行审 `tools/gem5/gen_decode_table.py` 新增校验/用例生成、`decode_test.cc` 合法性求值/旧字段负例、补丁导出与 README/changelog；重跑全部门控与 3 次注入。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 证据脚本 `legacy-rf` 注入命中首个 `{"rdhd",…}`（and.o，row 117）而非 ftsclb | ✅已修 | 按行定位 `{"ftsclb_orrr_rf", "ftsclb",` 再替换 | 复跑证据：`[FAIL] row 246 ftsclb_orrr_rf`，脚本 rc=0 |
| F2 `Entry.inst_with()` 对未知字段名静默忽略（错误用例会“空注入”） | ✅已修 | 增加 `unknown = set(overrides) - field names` 校验 | `inst_with({"rdhx":1})` → `no field named ['rdhx']`；`--check` rc=0 |
| F3 生成器无效分支/未用常量：`(third.name,third.bank)==LEGACY_SCALE_THIRD` 不可达、`ZERO_REGS` 未用 | ✅已修 | 删无效分支与常量（`LEGACY_SCALE_THIRD` 仅供负例表） | `py_compile` + `--check` rc=0；harness 2/2 legacy |
| F4 changelog 新条目插在 11-01 前，违反“节内日期升序” | ✅已修 | 改为 11-01 之后追加 | `check-component-changelog` rc=0（2 条/1 节） |
| F5 全量 `check-patch-tree` rc=2（llvm 10 + qemu 6） | ⏸延后 | 未动他组件（并行任务占用共享工作树） | gem5 单组件断言 1–9：0 problem；全量日志仅 llvm/qemu |
| F6 sc 的 ILLI 由“legality 数据判定”给出，`decodeWord` 不拒绝该字 | ❌不修（设计） | 文档化 B0 只发布 legality、B1–B6 抛 fault | `decode_test.cc` 头注释 + README；legality 28/28 |
| F7 合法性与旧字段断言可被篡改绕过（恒真风险） | ✅已证伪 | 2 条注入（删 legality / 反转期望） | harness rc=1 + `[FAIL] legality sc.o.nn_orrr_rd`，还原回绿 |

**判决**：finding 全部已修/已给理由；264/264 + 388/388 + 28/28 + 2/2、`build-gem5` rc=0、3 次注入可 FAIL 且 `cp`+md5 还原回绿。状态置 `待验收`。

### 第 1 次提交（architect 文件集审核）

档位：`WIP:`（reviewer 未验收，状态 `待验收`）。对账：显式 staging 9 项 = 完成区「修改文件」(`tools/gem5/gen_decode_table.py`、`components/gem5/{README.md,changelog.md,decode-assertions.tsv}`、三份 `decode/*.patch`、本任务书、`milestones.md`)，无多提/漏提；`tests|spec|contracts|manifests|llvm|qemu|Makefile` 越界 grep 无命中；`milestones.md` 仅单行状态 `待开始`→`待验收`。提交落分支 `GEM5-005t`，见 `git log GEM5-005t`；未 push。
