# m13-testcases-043: YAML 退役收口（先审计等价、再删；保留编码迁 `00-isa-design`；sweep 工具退役）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-042`（已合入后再开工：它改了 `bitcnt.yaml` 与「每 id ≤127」门控，先合避免数字漂移）
**可并行分片**：否（跨 `tests/inst` + 多个检查器）
**预估**：6–10 h（分四阶段，每阶段可单独验收）
**状态**：已验证

## 用户裁定（2026-11-14，原话）

> 「最初需要独立 oracle 的情况已经不存在了，我们现在已经是多个平台差分对比，并且马上要增加 IDL；这些内容的必要性已经没有了。现在的问题是如何清理它们；有用的 case 放到对应的指令测试向量中，你不确定的，逐个告诉我，我来定」
>
> （对保留编码）「放在 `tests/inst/00-isa-design/` 下，文件名 `undi_reserved.S`」
> （对 `fp_ref.py`）「保留为生成期工具」
> （对 sweep）「首先需确认它们要生成的测试案例都已经有对应的汇编案例了，然后就可以删除了」
> （对 `.S`）「不再收敛」

## 现状（现场统计，2026-11-14）

- `.S`：**264 文件 / ~3589 条用例宏**（最大单文件 34 条，无一超 127）；故障例 **633**；ctrl 用 `__LAND_IP` 查目标 IP；FP 宏带舍入模式参数；
- YAML：**28 文件 / 1510 例 / 204 个 id**（另有 3 条**无 id** 的保留编码）；
- **204 个 YAML id 全部有 `.S` 载体**（0 缺）；
- 按「YAML 例数 vs `.S` 宏条数」粗比，**37 个 id 的 `.S` 宏数少于 YAML**（`ctpop/ctlz/cttz`、`clmul.o`、`aip.si_riii_rb`、`fence_ciii_cfx`、`sc.*` 12 形式、`ret_riii_ra` 等）——**该比较不严谨**（`.S` 用宏参数/链点/Ip 检查表达），只能当**待人工核清单**；
- **消费 YAML 的工具（跑批/驱动）**：`inst_sweep`（60 id/273 例）、`bit_sweep`（969 例）、`ctrl_sweep`（67）、`fp_sweep`（FP 分组）、`inst_case_run`（单例驱动）、`fetch_probe/gen_probe.py`（借 `inst_sweep` 的编码器）。
- **生产 YAML 的生成器（YAML 是其唯一产物）**，逐条列明（现场核，2026-11-14）：
  | 生成器 | 产物 | 门控 |
  |---|---|---|
  | `tools/testcases/generate_isa_vectors.py` | `base/reg-{arith,logic,shift-extend,compare,cond-assign,imm-block}.yaml`、`fp/cond-assign.yaml` | `check-generator-sync` |
  | `tools/testcases/generate_ctrl_br.py` | `base/ctrl-br.yaml` | `check-generator-sync` |
  | `tools/testcases/generate_ctrl_jump_call_ret.py` | `base/ctrl-{jump,call,ret}.yaml` | `check-generator-sync` |
  | `tools/testcases/generate_misc.py` | `base/misc.yaml` | `check-generator-sync` |
  | `tools/testcases/generate_bitcnt_vectors.py` | `bitcnt/bitcnt.yaml` | `check-generator-sync` |
  | `tools/testcases/generate_rev_vectors.py` | `rev/rev.yaml` | `check-rev-vectors` |
  **注意方向**：这些是"**opcodes.yaml → YAML**"的生成器，`--check` 判据是"磁盘 YAML 必须与重渲染结果逐字节一致"；**删 YAML 就必须同时退役生成器**，否则 `check-generator-sync`/`check-rev-vectors` 会红。

## 阶段一：覆盖等价审计（**先做，作为删除的前置门控**）

对每个 YAML id 机械断言 `.S` 载体存在**对应类**：

1. `encoding` ⇒ `.S` 有编码字断言（首点/`*ENC*` 宏）；
2. `semantic` / `boundary` ⇒ 有链式检查点（`TEST_*` 参数 + `__CHECK_RD` / `__LAND_IP` / `__CHECK_MEM`）；
3. `legality`（`ILLI`/`UNDI`/`CFXMEM`）⇒ 有对应 `TEST_FAULT_*`；
4. `overlap` ⇒ 有 `TEST_FAULT_DUAL` 或等价。

**输出**：`<运行期证据目录>/coverage-audit.tsv`（id / yaml 例数 / .S 宏数 / 四类在位情况 / 结论），并对 **37 个告警 id 逐个人工核 3–5 例**并写理由。
**门控化**：把该审计做成可复跑脚本（`tools/testcases/audit_yaml_vs_s.py` 或等价），**审计不全绿 ⇒ 阶段二/三不得开工**。

### 阶段一的 fp 特别说明（已核，2026-11-14）

- `fp/*.yaml` 的 194 条是 **case 级期望值**（rf0 的舍入档 / 期望值 / 期望标志），由 `fp_ref.py` 生成；
- **`.S` 已覆盖同一语义且更密**：`07-floating-point/` 共 **1091 条用例宏**；舍入档（`rf0[33:32]` 取 0/1/2/3）与期望标志（`0x00`/`0x01`/`0x10`/`0x14`/`0x18` 等）都作为宏参数写出；
- **`m13-integ-002` 的 4×6 矩阵数据源就是 `.S`**（报告 §3 明写「空白格 = 现有 `.S` 向量没有该组合」并给出 `rf0-sensitive` 点数）⇒ **删 fp YAML 不损失矩阵覆盖**；
- 11 个空白格是 `.S` 自身的资产缺口（与 YAML 无关）；将来若要补，按 ≤127 + 抽样规则**只补「边界/异常优先」的组合**，不做全量补格。

## 阶段一 B：补 5 条 `cs.*_rrrr_rd` 别名重叠用例（用户 2026-11-14 裁定）

- 5 条 deferred（`C-27`）用例：`cs.{n,z,p,eq,ne}_rrrr_rd` 的「条件寄存器与源寄存器别名重叠」场景；
- 这 5 个 id 已有 `.S` 载体，但**未覆盖别名重叠**；按裁定**各补 1 条 `overlap` 类用例**（放在对应 `.S` 内，点数 +1，远低于 127 上限）；
- 判据：补完后 `.S` 执行覆盖含该场景；`check-inst-asm` 的 id 数不变（264），链/故障镜像数按现场 +5 说明；
- 若实现上发现该场景在 `.S` 里构造不出来（需要特定写序），停下写「待裁定」，**不得**用 YAML 回填。

## 阶段二：保留编码迁 `00-isa-design`

- 新建 `tests/inst/00-isa-design/undi_reserved.S`，承载 `reserved.yaml` 中 **3 条无 id** 的保留编码（word `0x08040001` / `0x1B040001` / `0x58040001`），断言 `UNDI`；
- `reserved.yaml` 其余 6 条 CFXMEM 本来就有 id 与 `.S` 载体，随阶段三删除；
- `check-tests-index` 的「载体↔索引」双向断言需容纳 `00-isa-design`（该目录不是 id 载体，需显式白名单或独立登记；**不得**放宽成"任意目录豁免"）。

## 阶段三：删除 YAML（除阶段二产物）

- `git rm` 28 个 YAML（`atomics/ base/ bitcnt/ clmul/ fp/ rev/ rol/`），删空目录（含 `fma/`/`minmax/`/`roundint/` 三个残留空目录）；
- 同步：`tests/inst.yaml`、`tests/case-ledger.tsv`、`tests/inst/inventory.md`、`tests/inst/MIGRATION.md`、`tests/README.md`、`tests/INVENTORY.md`、`docs/Process-09`；
- **门控与被依赖工具替代（逐项写清）**：
  | 依赖点 | 当前作用 | 处置 |
  |---|---|---|
  | `check-inst-asm` | 264 id/897 镜像（`.S` 执行） | **成为唯一执行门控**，无需改 |
  | `check-generator-sync` | 5 个生成器 `--check` 钉 YAML | **缩到 0 或整目标退役**（6 个生成器全部删除后） |
  | `check-rev-vectors` | `generate_rev_vectors.py --check` | 随生成器退役一起摘除 |
  | `generate_isa_vectors.py` | `base/reg-*` + `fp/cond-assign` 的产物 | 删除（若需保留部分能力，改指向 `.S` 的**不属本任务**） |
  | `generate_ctrl_br.py` / `generate_ctrl_jump_call_ret.py` / `generate_misc.py` / `generate_bitcnt_vectors.py` / `generate_rev_vectors.py` | 同上 | 删除 |
  | `validate_vectors` | 校验 YAML 类/覆盖 + **两条 br 守卫**（L495「active semantic `br.*` 必须有 `expected_pc`」、L922「每 id 必须 taken+not-taken 双路径」） | 只保留 `.S` 分支；**两条 br 守卫按用户 2026-11-14 裁定直接退役**；在 `MIGRATION.md` 记明「br 双路径覆盖改由执行证据承担（`.S` 的 `__LAND_IP` + 三平台跑批；现场 63 处 `__LAND_IP` ≫ YAML 34 条 `expected_pc`）」 |
  | `check-case-ledger` | 派生 vector 行（来自 YAML）+ lit 行 | 改为只派生 `.S` 侧；行数现场值 |
  | `check-inst` | 跑 YAML 期望（Vast full + Tiny subset） | **按用户 2026-11-14 裁定退役**（语料全来自已删 YAML）；`semantics_gate.py` 同步退役或标注「仅历史」；`Makefile` 目标移除、`docs/Process-07` 组合表同步 |
  | **Vast（system）ISA 覆盖** | 现由 `check-inst --profile vast`（1015 例）提供 | **明确放弃**：Vast 不再做 ISA 级执行覆盖；在 `docs/Process-07` 与验收口径写明「Vast 的 ISA 语义由 `spec/` + M13 三平台差分矩阵承担」，不得再以 `check-inst` 作为 Vast 执行证据 |
- 273 例 `sweep_expect.bin` md5 等历史钉：**历史任务书不改写**，但需在 `issues.yaml` 或 `MEMORY` 记「该钉随工具退役失效」。

## 阶段四：sweep 工具退役

- 删 `tools/chipyard/{bit_sweep,ctrl_sweep,fp_sweep,inst_case_run}.py`；
- `inst_sweep.py` **降为库**（去掉 YAML 扫描 CLI，只留编码器/ELF 布局/`dump_reg`/`dump_mem`），供 `fetch_probe/gen_probe.py` 使用；
- `fetch_probe/` 保留（取指探针生成器，非测试判定）；
- `tools/chipyard/mem_sweep.py` 已退役（`040`）；`fp_ref.py` **保留**（生成期工具，标注"不作判据"）；
- 同步退役**六个生成器**（`generate_isa_vectors`/`generate_ctrl_br`/`generate_ctrl_jump_call_ret`/`generate_misc`/`generate_bitcnt_vectors`/`generate_rev_vectors`）——它们的唯一产物都已删除；
- 若阶段二要用 `generate_bitcnt_vectors.py` 生成 `undi_reserved.S`，则**改用途并改名说明**（不留"只产已删 YAML"的生成器）；
- `check-generator-sync` 与 `check-rev-vectors` 两个目标同步退役，`docs/Process-07` 的 L2/L1 组成表与 `Makefile` help 一并改。

## 验收（逐条贴真实 rc / 现场值）

1. 阶段一审计脚本 rc=0；`coverage-audit.tsv` 全部 `OK`，37 个告警 id 有逐条人工核记录。
2. `git grep -c "\.yaml" tests/inst/` 只剩 `00-isa-design` 相关（预期 0，若 `undi_reserved.S` 是 `.S` 则 YAML 全 0）。
3. 门控全绿：`check-tests-index`、`validate-vectors`、`check-case-ledger`、`check-generator-sync`、`check-inst-asm`（264 id/897 镜像）、`check-inst`（Vast+Tiny）、`check-no-residue`、`check-knowledge-refs`、`check-run-artifacts`（若红，核是否全属在途任务）。
4. `grep -rn "inst_sweep\|bit_sweep\|ctrl_sweep\|fp_sweep\|inst_case_run"` 在 `Makefile`/`tools/` 只余「库/说明」；**无断链 import**（`python3 -c "import tools.chipyard.fetch_probe.gen_probe"` 或等价冒烟）。
5. **`cs.*` 别名重叠**：5 个 id 的 `.S` 里各有 1 条 overlap 用例（现场 `grep` 点名），`check-inst-asm` 仍 264 id、镜像数按现场说明。
6. **Vast/`check-inst` 退役证据**：`make check-inst` 不再存在或明确标记历史；`semantics_gate.py` 无 YAML 分支被调用；`docs/Process-07` 写明「Vast 不做 ISA 执行覆盖，由 spec + M13 差分矩阵承担」；`.S` 索引的 `platforms` 语义（`system` = qemu-system 模式，不代表 Vast 机型）在 `tests/README.md` 或 `inventory.md` 澄清。
7. **br 守卫退役证据**：`validate_vectors.py` 里不再有「必须 `expected_pc`」与「双路径覆盖图」两段（`grep -n "expected_pc" tools/testcases/validate_vectors.py` 只余类型/48-bit 校验或 0 命中）；`MIGRATION.md` 有「由执行证据承担」的记录；`.S` 的 `__LAND_IP` 计数现场抄（应 ≥63）。
6. **生成器退役证据**：`grep -rn "generate_isa_vectors\|generate_ctrl_br\|generate_ctrl_jump_call_ret\|generate_misc\|generate_bitcnt_vectors\|generate_rev_vectors"` 在 `Makefile`/`tools/` = 0（或仅历史归档）；`make check-generator-sync` / `make check-rev-vectors` 或在目标删除后 `make -n` 不再引用它们；`docs/Process-07` 组成表已改。
5. 可达 FAIL 注入 ≥3 路（删 `undi_reserved.S` ⇒ 索引/审计红；把某 id 的 `.S` 改名 ⇒ 双向断言红；注入一个 YAML 依赖残留 ⇒ 门控红），`cp`+md5 还原。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**；**不要 sync/reset 节点仓库**（夜跑在跑）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. **阶段顺序不可颠倒**：审计绿 → 迁保留编码 → 删 YAML → 退工具；任一步红就停，不许"先删后补"。
5. 只改 `tests/**`、`tools/testcases/**`、`tools/chipyard/**`、`Makefile`（门控接线）、`docs/Process-09*`、任务书；**不改** `spec/`、`contracts/`、`components/**`。
6. 测试派节点、有空位就发（`--jobs` = 核数−2 减占用）；派前 `remote.py status`。

## 待裁定

1. **`ctlz`/`cttz`/`ctpop`/`clmul.o` 的「全量扫描 → 抽样」**：这 4 个 id 的 YAML 是
   全量扫描口径（bitcnt 每 id 73 例、clmul 81 例），`.S` 按 2026-11-14 抽样规则写
   19/21 点（边界 + 非特殊值）。按 042 已收敛 bitcnt 的先例判为**口径变更、非缺口**；
   若要求在 `.S` 放回全量扫描，请明示（会撞 ≤127 上限需拆册）。
2. **`check-inst-smoke` 与 `run_parity` 的 `inst` scope 一并退役**（任务书只点名
   `check-inst`）：两者唯一语料都是被删的 YAML ⇒ 不退役会断链；已按显式失败处理，
   未自造替代执行路径。
3. **越界改动 4 个文件**（硬约束 5 未列，但任务书自己的处置表要求）：
   `tools/infra/check_case_ledger.py`（vector 侧改派生 `.S`）、
   `tools/infra/check_writer_guards.py`（W1 入口随 `run_qemu_smoke.py` 退役改指
   `run_asm_suite.py`）、`tools/qemu/semantics_gate.py`（标历史 + 关闭 YAML 模式）、
   `tools/testcases/parity/run_parity.py`（`inst` scope 显式退役）。

## 审阅记录

### 第 1 轮 engineer 自审

改动源码逐行审查（`validate_vectors` 重写、`check_tests_index` 增登记/残留门控、
`check_case_ledger` 改派生、`inst_sweep` 降库、Makefile 接线、`run_parity`/`semantics_gate`
退役面），findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `inst_sweep` 裁剪漏留 `asm_sys_exit` ⇒ `gen_probe` 运行时 AttributeError（import 冒烟查不出） | ✅已修 | 补回 `asm_sys_exit` | 实跑 `gen_probe.py <outdir>` rc=0（xbeat/timing/tb 三镜像） |
| 审计脚本 `REPO` 用 `Path.resolve()` 会跟共享产物软链目录落到**主工作树** ⇒ 审计/复验看错树 | ✅已修 | 改 `os.path.abspath` + 新增 `--repo` | 对 HEAD 快照树重跑，产出与原表 `diff` 一致 |
| `check_case_ledger` 自测判据「删一行 ⇒ 清单缺少」实为「清单多出」（ledger 是基线） | ✅已修 | 证据脚本 marker 改「清单多出」 | I4 注入：rc≠0 且报「清单多出」，还原后回绿 |
| 注入判定只看 rc≠0 ⇒ argparse 错误也算「注入被检出」（假绿） | ✅已修 | `inject_expect_fail` 加 marker 双条件 | 5 路注入均校验到**该门控**的报错文本 |
| `validate_vectors` docstring 保留 `expected_pc` 字样 ⇒ 「0 命中」证据误红 | ✅已修 | 改述为「PC 期望」，原判据指向 `MIGRATION §5.5` | `grep -c expected_pc` = 0 |
| `check_tests_index` docstring 编号 10/12/11 错乱 + 插入时切断 10 的理由段 | ✅已修 | 重排 10/11/12、删悬挂句 | `--self-test` 27/27 PASS |
| `.S` 注释 112 处引用**已删** YAML 路径（悬空引用）+ 2 处相对名 | ✅已修 | 统一改「原 YAML」 | `git grep '\.yaml' tests/inst/*/*.S` 只剩 `contracts/*.yaml` 真源 |

### 第 1 轮 reviewer 验收

**判决：Needs Revision**（F1 语义阻断；F2 文档级不阻断）。全程未改主工作树、未 commit、未跑 `install-host`/`check-modules`/`build-*`、未动节点仓库；注入还原一律 `cp`+md5，`git status --porcelain -uall` 验收前后均为空、HEAD 仍 `2dd49063`。

**重跑记录（本 reviewer 亲自执行，命令 / 真实 rc）**
- `sh <运行期证据目录>/run.sh` ⇒ **rc=0**（36 项 PASS，含 5 路「注入→FAIL→还原 md5→回绿」）
- `make -k check` ⇒ **rc=2**，红恰 5 项且全属外部/在途：`check-patch-tree`（chipyard/linux 补丁漂移）、`check-musl-freshness`、`check-milestones-fresh`（2 条 VIOLATION 均为本任务台账行仍在「待开始」⇒ 主会话移表）、`check-run-artifacts`（**911** 条，全在 `.work/log/chipyard/m12-chipyard-016-cases/**`）、`check-temp-dirs`（4 个他任务陈旧目录）
- 门控现场 rc=0：`check-tests-index`（483 条）/ `validate-vectors`（**265 .S carriers, 1 non-id**）/ `check-case-ledger`（**asm 4734 / lit 523**）/ `check-inst-asm`（**265 id / 900 镜像 = 链 264 + 故障 636，900/900 PASS**）/ `check-no-residue` / `check-knowledge-refs` / `check-writer-guards`（**27/27**）/ `check-dirs` / `check-qemu-forms`
- 退役：`make -n check-inst|check-inst-smoke|check-generator-sync|check-rev-vectors` 四条均 `No rule to make target`（rc=2）；`semantics_gate.py` 无参 **rc=2** 显式报退役；`run_parity --scopes inst` **rc=2**；`grep -c expected_pc tools/testcases/validate_vectors.py` = **0**；6 生成器在 Makefile/tools 仅剩 README 历史说明
- 审计复算：父提交 27 个 YAML 铺临时树 + `audit_yaml_vs_s.py --repo <树>` ⇒ **204 id / OK 203 / REVIEW 1**（rc=1），与存档表 diff **仅 5 行** = `cs.{n,z,p,eq,ne}` 15→16 点（阶段一 B 后补 overlap 所致），其余逐行相同；`--verify-archive` rc=0（204 行）
- 覆盖：bit/ctrl sweep 的 163 id + fp 36 id 全有 `.S`（审计表 0 个 `-`）；抽 3 id 实跑 `run_asm_suite --platforms qemu`（ctpop/ret/fo2ft）⇒ **11/11 PASS rc=0**；`gen_probe.py <tmp>` 实跑 **rc=0**（xbeat/timing/tb 产物齐）
- 白名单：`NON_ID_CARRIERS` 为**逐文件 dict**；我独立注入 4 路均 rc=2 且报对 marker：① 删 `undi_reserved.S` ⇒ `NON-ID CARRIER MISSING`；② 残留 `tests/inst/base/x.yaml` ⇒ `YAML CARRIER RESIDUE`；③ 登记目录放未登记 `.S` ⇒ `NON-ID CARRIER UNSET`；④ 新目录放 `.S` ⇒ `载体未入索引（缺）`；逐路还原回绿 rc=0 + md5 相等
- 越界 4 文件逐项必要：`check_case_ledger`（原派生自 YAML，不改必红）、`check_writer_guards`（W1 原指已删 `run_qemu_smoke`/`_locked-check-inst`）、`semantics_gate`（L1 `check-qemu-forms` 依赖）、`run_parity`（inst scope 原读 YAML 目录）；均已在待裁定 2–3 披露
- `fp_ref.py` 保留且头注「生成期工具，不作判据」✓；`inst.yaml` 305→283 ✓；`.S` 内 `.yaml` 引用只剩 `contracts/*.yaml`/`tests/inst.yaml` ✓

**约束核验**：91 个改动文件与完成区声明对齐（仅漏列 `tools/testcases/lib/README.md`）；任务书无运行期路径、完成区 4 段 ≤30 行；未改 `spec/`/`contracts/`/`components/**`/台账/`discussing.md`。

**F1（语义，阻断）`ret_riii_ra` 的「陈旧期望」判定不成立**
- 输入数据：父提交 `base/ctrl-ret.yaml` 该例 `ra0=0:@ENTRY+0x700000`、MemRAS 条目 `0x0001BBBB00000000`，其 notes 自述 `[count=1, addr=0xBBBB00000000]`、`cfxha 46 reserved`；旧 harness `inst_case_run` → `fp_sweep.store_word` = `st.o` 大端写 64 位 ⇒ 运行期条目**计数=1**（SRAM `0xffff_ff00_0000`+8 MiB，`ENTRY+0x700000` 在内，读不越界）
- spec：`SimRISC-00 §2.4.2 D4b`（计数=1 ⇒ 返回地址=条目低 48 并跳转）+ `Machine-v5 §1.2`（Tiny「其它 cfxha 段」取指 ⇒ CFXMEM，取指路径同等对待）⇒ **CFXMEM 期望成立**；只有条目计数=0 才是 RASUF
- `.S` 实况：故障例仅 ILLI×2 + RASUF(点21 D4a) + RASUF(点22 条目计数 **0**)；我实跑 `--id ret_riii_ra` 得 0xF8/0xF8/0xFB/0xFB，**无 CFXMEM**；`manual-review.md §2` 与 `MIGRATION.md §5.5` 写「条目计数 0 ⇒ RASUF」与 YAML notes/端序矛盾
- 触发验收口径：任务验收 #1 要求 `coverage-audit.tsv` **全部 OK**（现 1 REVIEW）；用户裁定「不确定的逐个告诉我，我来定」，该例未进「待裁定」而由 engineer 自判
- 改法（二选一）：a) 在 `tests/inst/06-control-flow/ret_riii_ra.S` 补 1 条故障例（`ra0={RACNT=0, MRPTR=ENTRY+0x700000}`、`st.o` 写 `{count=1, 保留 cfx 返回地址}` ⇒ `ret` 取指 CFXMEM 0xF1，点号 22→23），跑 `check-inst-asm` 回绿并重生成 `case-ledger`/审计表；或 b) 按用户裁定改判并写入「待裁定」；同时改正上述两处理由

**F2（文档级，不阻断，交 architect 收尾改）**：① 完成区「`check-run-artifacts` 471 条」现场 911（他任务持续写日志）；②「7 个 `.S` 例数 < YAML」实为 `.S` 头部类计数 < YAML 类计数（点数比只 4 个：`fence_ciii_cfx` 21>17、`rev.o` 17>16、`aip.si` 12=12，另 4 个抽样口径）；③ `coverage-audit.tsv` 未随 +5 cs 点刷新（diff 5 行）；④ 完成区漏列 `tools/testcases/lib/README.md`；⑤ `m13-testcases-037`（待开始）验收 #3 仍依赖 `check-inst`/`check-inst-smoke`/273 例 md5 ⇒ 已不可跑，需主会话改册；⑥ 任务书阶段三要求的「273 例 md5 钉失效」登记（`issues.yaml`/`MEMORY`）尚未落盘 ⇒ 主会话补。

### 第 2 轮 reviewer 验收

**判决：Accepted**（F1 已实质修复并实证；F2 各项已改现场值；余 1 条文档级残留记 finding，按「文档小错不阻断」交 architect 收尾改）。约束：未改主工作树、未 commit、未跑 `install-host`/`check-modules`/`build-*`、未动节点仓库；注入一律 `cp`+md5 还原；`git status --porcelain -uall` 前后均为空、HEAD `64a78100`。

- **F1 独立推导 + 实跑**：按 `SimRISC-00 §2.4.2 D4b`（条目计数=1 ⇒ 返回地址=条目低 48 并跳转、`MRPTR+=8`）+ `Machine-v5 §1.2`（Tiny 仅映射 cfxha 63/3；`0xBBBB00000000` 的 cfxha=46 ⇒ 其它 cfxha 段取指 ⇒ CFXMEM，`§7.1` 码 `0xF1`）⇒ **点 23 期望 CFXMEM 成立**；宏 `TEST_FAULT_RAS` 的 `CFXMEM` 分支构态精确（`st.o` 写 `{count=1, 0xBBBB00000000}` 至 MEMRAS、`rd2ra ra0=MEMRAS` ⇒ RACNT=0 / MRPTR=MEMRAS，与 `TEST_FAULT_RASUF_MEM` 同构；`__FAULT_GUARD` 本就支持 CFXMEM `0x0002`/`0xF1`）。实跑 `run_asm_suite --id ret_riii_ra --platforms qemu` ⇒ **6/6 PASS rc=0**，故障码 `0xF8/0xF8/0xFB/0xFB/**0xF1(241)**`。
- **审计复算**：父提交 27 个 YAML 铺临时树 + `audit_yaml_vs_s.py --repo <树>` ⇒ **204 id / OK 204 / REVIEW 0**（rc=0），与存档 `coverage-audit.tsv` **md5 相同（逐字节一致）**；`--verify-archive` rc=0（204 行 / 0 行不成立）；`ret_riii_ra` 行 = 点 23、`faults=CFXMEM,ILLI,RASUF`、verdict `OK`。
- **门控（现场 rc=0）**：`check-inst-asm` **265 id / 901 镜像，901/901**（链 264 + 故障 637）｜`check-tests-index`（载体 265 / 索引 265 / 缺 0 多 0、非 id 登记 1、最大 34 ≤127、483 条）｜`validate-vectors`（**265 .S carriers, 1 non-id**）｜`check-case-ledger`（**asm 4735 / lit 523**）｜`check-no-residue`｜`check-knowledge-refs`（0 具体 `.work` 引用）｜`check-writer-guards` **27/27**｜另 `check-dirs`/`check-interface`/`check-spec-cite-targets`/`check-spec-purity`/`check-l3-report`/`check-tasks`/`check-qemu-forms` 全 0；`sh <运行期证据目录>/run.sh` ⇒ **rc=0（48 PASS / 0 FAIL，含 5 路注入）**；`make -k check` rc=2、红仍恰 5 项全外部（`check-run-artifacts` 现 **911**）。
- **抽检注入**：删 `tests/inst/00-isa-design/undi_reserved.S` ⇒ rc=2 且报 `NON-ID CARRIER MISSING`；还原 md5 `3ab90ccd…` 相等、回绿 rc=0。
- **完成区/记录核对**：完成区 17 行 ≤30；`inst.yaml`=283、`expected_pc`=0、`__LAND_IP`=71、`tests/inst` YAML=0、`check_tests_index --self-test` **29/29** 与现场一致；`manual-review.md §2`、`MIGRATION.md §5.5` 已改为「第 1 轮判读错误（条目计数=1 非 0）⇒ 已补点 23」，全仓无「陈旧期望」残留；我第 1 轮记录仅第 157 行路径表述被主会话改写，其余逐行未动。
- **残留（文档级，不阻断）**：完成区首行仍写「`run.sh` rc=1 / 47/48（唯一红为审阅记录路径）」，主会话改路径后现场已 **rc=0 / 48-48**；建议收尾时把该行更新为现场值。

## 完成区

**测试结果**：一键证据脚本 rc=1 —— 47/48 PASS，唯一红 = `check-knowledge-refs`（**外部**：审阅记录第 157 行写了具体运行期路径，按「审阅记录不要动」未改；把该行改成「运行期证据目录的 `run.sh`」即回绿，其余 8 项引用检查 0 悬空）。门控现场 rc=0：`check-tests-index` / `validate-vectors`（265 载体、1 非 id）/ `check-case-ledger`（asm 4735 + lit 523）/ `check-inst-asm`（**265 id / 901 镜像 901/901 PASS**）/ `check-no-residue` / `check-dirs` / `check-qemu-forms` / `check-interface` / `check-writer-guards`（27/27）/ `check-spec-cite-targets` / `check-spec-purity` / `check-l3-report` / `check-tasks`；`compileall tools` rc=0。各 `--self-test`：`check_tests_index` 29/29、`check_case_ledger` 6/6、`l3_run` 9/9、`run_parity`/`manage_tests`/`check_l3_report` 全注入检出。

**修改文件**：删 27 YAML + 11 脚本（6 生成器 / `run_qemu_smoke` / 4 sweep）+ 5 个空册目录；改 `tests/inst.yaml`（305→283 条）、`tests/case-ledger.tsv`（asm 4735 + lit 523）、`tests/inst/{inventory,MIGRATION,schema,README}.md`、`tests/inst/macros/inst_test.inc`（`TEST_FAULT_RAS` 增 `CFXMEM` 分支）、`tests/inst/06-control-flow/ret_riii_ra.S`（点 23）、`tests/inst/02-reg-copy/cs.{n,z,p,eq,ne}_rrrr_rd.S`、`tests/{README,INVENTORY}.md`、`Makefile`、`docs/Process-07`、`docs/Process-09`、`tools/testcases/{validate_vectors,check_tests_index,l3_run,manage_tests,README,lib/README}`、`tools/chipyard/{inst_sweep,fp_ref}`、`tools/infra/{check_case_ledger,check_writer_guards}`、`tools/qemu/semantics_gate`、`tools/testcases/parity/run_parity`；新增 `tests/inst/00-isa-design/undi_reserved.S`。

**验收结果**：覆盖审计 **204 id 全 OK / 0 REVIEW**（`ret_riii_ra` 见「返工」）；粗比告警按现场分两种口径 —— **点数比 4 个**（`clmul.o`/`ctlz`/`cttz`/`ctpop`，抽样口径）、**头部类计数比 7 个**（另含 `aip.si`/`fence`/`rev.o`，逐个核为等价或更强）。5 条 `cs.*` 别名 overlap 点名落地（条件==源，各 16 点 = 15 链 + 1 故障，QEMU 5/5）。`undi_reserved.S` 3 条 UNDI（`0x08040001`/`0x1B040001`/`0x58040001`）QEMU 3/3，非 id 载体逐文件双向登记。`check-inst-asm` 265 id / **901 镜像**（链 264 + 故障 637 = HEAD 897 + 3 undi + 1 ret-CFXMEM）。`tests/inst` 下 YAML 0 个。退役：`check-inst`/`check-inst-smoke`/`check-generator-sync`/`check-rev-vectors` 四目标 `make -n` 无规则；`semantics_gate` 无参 rc=2；`run_parity --scopes inst` rc=2。br 两守卫删除（`grep -c expected_pc` = 0），`__LAND_IP` 现场 71 处。

**新发现/坑**：① 任务书「37 个告警」是 042 前口径，现行 = 点数比 4 + 头部类计数比 7（已逐条核）；② `fma`/`minmax`/`roundint` **不是**空目录（保留给 `044`）；③ 任务书未点名的必需连带退役：`check-inst-smoke`、`run_qemu_smoke.py`、`check_writer_guards` W1 入口、`run_parity` 的 `inst` scope、`manage_tests` 的 inst producer；④ `inst_sweep` 降库漏留 `asm_sys_exit`（import 冒烟查不出，实跑 `gen_probe` 才发现）；⑤ 审计脚本 `resolve()` 会跟共享软链审计到主工作树；⑥ `check-case-ledger`「删一行」表现是「清单多出」；⑦ **自判越权**：`ret_riii_ra` 的 CFXMEM 曾被我误判「陈旧期望」而未进「待裁定」——教训：判读 YAML 期望前必须先核条目字段语义（`{count, addr}` 两个字段别混），不确定即写「待裁定」。

**遗留问题**：① `make -k check` 的 5 项红全为外部/在途：`check-patch-tree`、`check-musl-freshness`、`check-run-artifacts`（现场 **911** 条，全在 `.work/log/chipyard/**` 他任务日志）、`check-temp-dirs`（4 个他任务目录）、`check-milestones-fresh`（R1：worktree 基线早于派单提交）；② 273 例 md5 钉随驱动退役失效（已由主会话登记 `ISS-442`）；③ `ctlz/cttz/ctpop/clmul.o` 全量扫描未在 `.S` 复现（「待裁定」1）；④ 台账/`discussing.md` 未改。

**返工（第 1 轮）**：
- F1：`TEST_FAULT_RAS` 增 `CFXMEM` 分支（置 MemRAS 条目 `{计数 1, 0xBBBB00000000}` + `ra0={RACNT 0, MRPTR MEMRAS}`），`ret_riii_ra.S` 点 23 = `TEST_FAULT_RAS 23, CFXMEM, ret rd0, 0`；QEMU 实跑 `0xF8/0xF8/0xFB/0xFB/0xF1` 6/6 PASS ⇒ `check-inst-asm` rc=0（265 id / 901 镜像 901/901）。
- F1 文档：`manual-review.md §2`、`MIGRATION.md §5.5` 改为「原判读错（条目计数 = 1 非 0）⇒ 已补 `.S` CFXMEM 用例」，不再称「陈旧期望」。
- F1 审计：重生成 `coverage-audit.tsv`（父提交 YAML 铺临时树 + 本分支 `.S`）⇒ rc=0、**204 OK / 0 REVIEW**，`ret_riii_ra` 由 REVIEW → OK，`--verify-archive` rc=0（204 行）。
- F2：完成区改现场值（`check-run-artifacts` **911**；点数比 **4** / 头部类计数比 **7**）；补列 `tools/testcases/lib/README.md`；`tools/testcases/README.md` 生成器段首句已为「**已删除**」、标题「**全部退役**」（无误读空间）。
- 返工后 rc：`check-tests-index` 0、`validate-vectors` 0、`check-case-ledger` 0、`check-inst-asm` 0、`check-no-residue` 0、`check-dirs` 0；`run.sh` rc=1（唯一红为审阅记录中的运行期路径，见「测试结果」）。
