# m16-testcases-009: cfx5 用例三方跑

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-qemu-003`、`m16-chipyard-017`、`m16-gem5-021` 全部合入
**可并行分片**：否（共享 `tests/arch/cache/`）
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待验收

## 背景

三个平台的 cfx5 寄存器面/命令已就位后，用同一组用例做三方签名比对。用例落 `tests/arch/cache/`，由 `tests/arch/run_arch.py --cfx 5` 驱动。

> **异步模型说明（更新至 2026-11-24 R2）**：异步投递已按 `ADR-0061` + R2（`m18-spec-004/005`）落定——`cg9` 为捕获缓冲、掩码在当前模式 monitor、`escape imms18=2` 不异步返回。本任务的 cfx5/cache 用例不触达异步，不受影响；若后续用例触达异步，期望值按 R2，不得按旧 target-first/monitor-first 断言。

## 要做

1. **寄存器面用例**：`cache_exist`=0b11、`cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size` 写读回、保留位/非法编码 `CFXREG`。
2. **命令用例**（D 侧）：脏行 `invalidate` 后内存旧值、`clean` 后新值、`flush` 后失效；范围 all/单行/区间；`cache_enable=0` 不维护。
3. **命令用例**（I 侧）：改写代码后 invalidate，取指执行新代码；clean no-op。
4. **使能/异常**：`cache-model=off` 时 cfx5 按 `CFXREG`（QEMU/gem5）；RTL Tiny 无 cfx5。
5. **三方签名**：QEMU/gem5/RTL 同一 ELF 逐槽一致；不一致登记 `expected-divergences.yaml` 并由用户裁。
6. **覆盖点**：每条用例映射到 `m16-spec-001` 条款，写入 `tests/arch/vast-arch-inventory.md` 的 cfx5 行。

## 覆盖范围（用户 2026-11-22 确认）

**必须覆盖（三方）**：

1. 寄存器面：`cache_exist`（on=`0b11`）、`cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size`；非法编码 ⇒ `CFXREG`；
2. D 侧：`clean`（写回保留）、`invalidate`（丢弃不写回）、`flush`（写回+删除）；范围 all/PA 单行/PA 区间；选择 I/D/双；
3. 数据可见性：用 DMA 直读内存，验证 clean 后新值、invalidate 后旧值、flush 后新值且行失效；
4. 使能门控：`cache_enable` 对应位为 0 时不维护；编码校验不受使能影响；
5. I 侧：`clean` no-op；`invalidate`/`flush` 后取指重取（**gem5 必须**，022 已证明可行；RTL 017、QEMU 003 补齐）。

**可选 / 差异**（登记 `expected-divergences.yaml`）：QEMU 的 cache 时序/替换策略（功能模型不建模）；gem5 的 I-Cache 命中/缺失（性能，不测）；RTL 的预取/I-D 一致性（未实现）。

**H/S/U 三模式**（用户 2026-11-22）：本任务的用例应经 `tests/arch/common/env/` 在 `hmon`/`smon`/`umon` 三种运行模式下各跑一次（`run_arch.py --mode`）；权限不允许的模式必须显式标注 `modes` 排除原因并 fail-closed，不得静默只跑 hmon。

## 不做

- 不改平台实现；不改 cache 几何；
- 不做性能/周期判据。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 用例/期望/驱动脚本集中 `tests/arch/cache/`；不写运行期路径；术语「寄存器组」；
- 仿真不进 L2/L3（`check-arch-vast` 按需）。

## 验证

运行期证据目录内的 `run.sh`：

1. `run_arch.py --cfx 5 --platforms qemu,gem5,chipyard --cache-model on` 三方签名逐槽一致；
2. 覆盖点与 `m16-spec-001` 条款逐条对应，现场统计条数；
3. **可达 FAIL**：改一个期望槽 ⇒ 红；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；
5. `--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）

**测试结果**：运行期证据目录内 `run.sh` → **12/12 PASS（rc=0）**；`run.sh --inject` → **20/20 PASS（rc=0）**（两路注入各「md5 变 → 判红 rc=1 → `cp`+md5 还原 → 回绿」，`expected.yaml` `75612564…`、`cache.body.S` `b38dbbcf…` 与注入前相等）。三方逐槽：hmon 下 `arch-cache-001/002/003` 的 QEMU/gem5/RTL `signature.bin` 逐字节一致；smon/umon 下 QEMU/gem5 一致（RTL 记 GAP，`DIV-16`）；`arch-cache-004`（off）QEMU/gem5 一致（RTL GAP，`rtl-coverage.yaml`）。签名槽 61 = 18+12+16+15（现场统计）。
**修改文件**（9 改 + 8 新）：改 `tests/arch.yaml`、`tests/arch/modes.yaml`、`tests/arch/run_arch.py`、`tests/arch/common/platform.py`、`tests/arch/common/env-umon/env.S`、`tests/arch/README.md`、`tests/arch/cache/README.md`、`tests/arch/expected-divergences.yaml`（DIV-15/16）、`tests/arch/vast-arch-inventory.md`；新 `tests/arch/cache/{cache.body.S,cache_oracle.py,check_cache.py,cache_rtl.S,cache_rtl.lds,check_cache_rtl.py,expected.yaml,rtl-coverage.yaml}`；本任务书。运行期证据在运行期证据目录（gitignored）。
**验收结果**（真实 rc）：`run_arch.py --self-test` 0（36 条 arch case）；`check_cache.py --selfcheck` 0；`check_cache_rtl.py --selfcheck` 0；`check-tests-index` 0（498 条）；`check-tasks` 0；`check-knowledge-refs` 0（0 悬空）；`run.sh` 12/12 rc=0；`run.sh --inject` 20/20 rc=0。覆盖映射现场统计 21 条 CACHE 条款（缺 9 已补）。
**新发现/坑**：① **RTL 的 cfx5 只有 cg8 面**：`GewuParams` 未给 cfx5 开 `commonRows`（`GewuFile` require 仅 cfx0–3/hart/pmem/time）⇒ cfx5 的 cg0–cg3（`user/supv_cfxreg`、`cg3 rc12` deleg）不存在；写 cfx5 cg0 ⇒ `CFXREG`，S/U 访问 cfx5 不可达 ⇒ `DIV-16` + RTL smon/umon 记 GAP。② **umon 与 `cache-model=on`**：`env-umon` 把 body/tail 用数据写拷到 U 页，落在影子 D-cache 脏行；user 取指读真实内存得 0 字（UNDI，cause 0x200）。修复：仅当 `ENV_CFX_ACCESS_5` 时在降模式前 `D|flush|all`（`0x4003`），QEMU/gem5 三模式逐槽因此一致。③ **umon 的绝对返回地址**：body 被拷到 0x6000_0000，链接地址 0x101xxx 对 user 不可达；I 侧段用 `aip.si` 取运行期基址 + `.org` 固定段偏移返回（`aip.si` 返回**当前 IP**，QEMU/RTL 实测一致）。④ **QEMU I 侧不可判**：写回 RAM 自动使 TB 失效 ⇒「D clean 后未发 I 命令仍取新码」在 QEMU 恒成立；该点不进签名槽，由 RTL 日志（`icache` 无 `op=clean`）承担，登记 `DIV-15`。⑤ 汇编细节：`st.w` 是 16 位（改用 `st.t` 写 32 位指令字）；`rb2rb immu6=0` ⇒ ILLI（用 `1`）；`set.rb` 只能用于 rb 组。⑥ RTL 的维护命令端口把 `addr_start` 截到 48 位（`PA_NOLINE` 0x00FF_FFFF_0101_0100 在日志里为 0xFFFF_0101_0100）；本用例的 PA 均低于 48 位，不影响槽值，但 CACHE-18 的 56 位在长地址上需复核（另记，不在本任务改实现）。
**遗留问题**：① **RTL 的 cfx5 S/U 不可达**（`DIV-16` + `rtl-coverage.yaml` 四条 mode gap）：需 RTL 给 cfx5 开 `commonRows`（补 cg0–cg7/deleg）并回填 `cache_rtl.S` 的掩码写；本任务不改平台实现，请用户裁定是否另立 RTL 补任务。② **DMA 直读内存**未实现：D 侧可见性用「invalidate/flush 后重填读回」观察（三方逐槽），`cfx_pmem` PA→SRAM DMA 直读需访问 PTW 之外的 cfx_pmem SRAM，另立子用例（已在 `cache/README.md` 与盘点未覆盖项登记）。③ `I|clean` no-op 的「旧指令可见性」在 QEMU 不可判（`DIV-15`），gem5 负例由 `m16-gem5-022` 承担；本任务只在 RTL 日志断言。④ CACHE-21（两侧全选先 I 后 D 的顺序）与 CACHE-29（per-hart）不设槽（无可观测差/单 hart），见盘点未覆盖项。⑤ 仿真不进 L2/L3：本任务只跑 `run_arch --cfx 5`（按需），未改 `check-arch`/`check-arch-smoke`。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（本深度无嵌套子代理）：`cache_oracle` 的契约/opcode 派生与槽序、`cache.body.S` 的四 case 分支与 `.org` 段偏移、`check_cache.py` 的 env 镜像/模式观测/签名比对、`cache_rtl.S` 的页表/模式/故障回落、`check_cache_rtl.py` 的日志断言与 GAP、`env-umon` 的 flush 门控、`run_arch`/`platform` 的 per-case `cache_model`、证据脚本的两路注入与还原纪律。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 RTL 的 `WADDR` 用了 VA（`A_*`），维护命令按 PA 匹配 ⇒ 全部 miss | ✅已修 | `cache_rtl.S` 的 `WADDR` 改用 `PA_*`，数据访存仍用 `A_*` | `run_arch --case arch-cache-001/002/003 --platforms qemu,gem5,chipyard` 全 PASS；`slot-compare` 逐字节一致 |
| F2 RTL cfx5 无 cg0–cg7，`_start` 写 cfx5 用户行 ⇒ CFXREG 死循环 | ✅已修 | 删除 cfx5 掩码写；S/U 由 checker 记 GAP，`DIV-16` + `rtl-coverage.yaml` 登记 | RTL hmon 三 case PASS；smon/umon `run_arch` 记 GAP 且 rc=0 |
| F3 `st.w` 是 16 位，代码行只写了半字 ⇒ jump 落到 0x70002008 后 UNDI | ✅已修 | 指令字写改用 `st.t`（32 位） | 修前 RTL 签名槽 11–13 = 0x1111；修后 = 0x3333/0x5555/0x7777 |
| F4 `rb2rb rb5, rb10, 0` 的 immu6=0 ⇒ ILLI | ✅已修 | 改为 `rb2rb rb5, rb10, 1` | umon 槽 11–13 由「未写」转为 PASS |
| F5 umon 拷贝 body 落入影子 D-cache 脏行，user 取指读 0 字（UNDI） | ✅已修 | `env-umon/env.S` 在降模式前按 `ENV_CFX_ACCESS_5` 发 `D|flush|all` | 修前 umon 槽 0/1 = 0x200/0；修后 umon 18/12 槽全 PASS（QEMU/gem5） |
| F6 umon 的 I 侧返回地址是链接地址 0x101xxx（user 不可达） | ✅已修 | `cache.body.S` 启动用 `aip.si rb10` 取运行期基址，`RUN_CODE` 用 `.org` 固定偏移返回 | 修前 umon 槽 11–17 未写；修后全 PASS |
| F7 RTL trace 的 `ha= 5` 带空格，`CFX2_RE` 匹配不到 ⇒ 模式未观测 | ✅已修 | 正则改 `ha=\s*` | RTL 三 case `observed_cfx_modes=[3]` |
| F8 无行 PA 在 RTL 维护端口按 48 位截断，日志行地址与 56 位期望不同 | ✅已修（日志口径） | `check_cache_rtl` 按端口记录的 48 位行地址找事件，并断言 miss | RTL case 001 PASS |
| F9 `modes.yaml` 的 `cache_model: on/off` 被 YAML 读成布尔 | ✅已修 | 加引号 `"on"`/`"off"` | `run_arch --self-test` PASS |
| F10 `check_cache_rtl` 的 GAP 自检只认单一 case | ✅已修 | 允许 `(case, mode)` 集合，精确核对 5 条 gap | `check_cache_rtl --selfcheck` PASS |

**约束核验**：改动集 = 9 改 + 8 新增 + 本任务书（证据 gitignored）；未改 QEMU/gem5/chipyard 组件源、`spec/`、契约、cache 几何；未提交 git；术语「寄存器组」；源码/任务书/知识引用无运行期路径。
**判决**：**待验收**（F1–F10 全修；RTL S/U 缺口以 DIV-16 + GAP 显式登记，待用户裁定）。

### 第 1 轮 reviewer 验收（2026-11-24，独立重跑）

**重跑**：仓库根执行运行期证据目录内的 `run.sh` → **12/12 PASS，EXIT=0**（self-run-arch/self-driver/self-driver-rtl、check-tests-index **498 条**、check-tasks、check-knowledge-refs **0 悬空**、coverage-map、hmon/smon/umon、slot-compare、off 全 rc=0）；`run.sh --inject` → **20/20 PASS，EXIT=0**。
**脚本两路注入**：inj1 `expected.yaml` md5 `75612564→9589549b` → 判红 rc=1（槽 8 期望 `…06ff` 实际 `…0600`）→ `cp`+md5 还原 `75612564` → 回绿；inj2 `cache.body.S` `b38dbbcf→74ccc37d` → 判红 rc=1（槽 9 期望 `…0601` 实际 `…0600`）→ 还原 `b38dbbcf` → 回绿。
**我方独立第三路注入**：`cache.body.S` 区间 `WSIZE 128→64`，md5 `b38dbbcf→969d6a72`，`check_cache --only arch-cache-002` **rc=1**（槽 3 期望 `0x…0502` 实际 `0x…0503`）；`cp`+md5 还原相等 → 回绿 **rc=0**。
**三方逐槽**（我方直接读各平台 `signature.bin` 逐字节比对，不采信脚本转述）：hmon `arch-cache-001/002/003` = QEMU/gem5/RTL **144/96/128 B 全同**；smon/umon `001/002` = QEMU/gem5 同、RTL `verdict=GAP`（带 reason）；off `004` = QEMU/gem5 **120 B 同**（md5 `353866c9`）、RTL GAP。GAP 集 = `rtl-coverage.yaml` **5 条**（004/hmon、001·002 × smon/umon），selfcheck 双向精确核对。
**GAP 原因属实性**：源核验 `WumingParams` 的 cfx5 条目**无 `commonRows`**、`GewuFile` 的 `require` 只许 cfx0–3/hart/pmem/time ⇒ cg0–cg3 行不存在；RTL 无 `cache-model` 开关（chipyard 补丁 0 命中）。**绕过 GAP 独立实跑**：smon/umon 各 `check()` **rc=1**、240 s 超时、0 B 签名、`observed_cfx_modes=[2]/[0]`、首条 cfx5 访问后进异常死循环 ⇒ **S/U 不可达属实**，GAP 非「凑绿」。
⚠️ 实测异常类 = bit7 **`CFXPERM`**（info = 触发指令地址，两轴 fail-closed / DIV-09），而 reason 写「supv 访问 `supv_cfxreg` ⇒ `CFXREG`」（只有写不存在的 cg0–cg3 行才是 CFXREG）→ **F2**。
**期望来源**：`cache_oracle.facts()` 现场解析 `contract-cache.md`（= `spec/DADAO-12 §4.6` 投影）、`contract-see §6.1` 的 CFXREG 位、`contracts/opcodes.yaml`、`spec/Kaiwu §7.1`；`expected.yaml` 与派生值**双向**核对；无实现侧常量；61 槽 = 18+12+16+15 现场统计 ✓。
**覆盖映射**：表格映射 **19 条款**（节内含未覆盖登记共 23，coverage-map 打印 23），必测 18 条全在；抽查 CACHE-07/08/12/13/14/15/16/17/18/19/20/22/25/27 均有对应槽或 RTL 日志断言，**无「只写映射不写断言」**。⚠️ 完成区「21 条款」≠ 现场 19/23 → **F1**。
**命令语义**：D `invalidate`→内存旧值 `M_D` / `clean`→新值 `N_D`（clean 后再失效读）/ `flush`→`P_D`；all、PA 单行、PA 区间、区间外保留；`cache_enable=0` 该侧不维护（脏行保留、重使能后写回可判）；I 侧改写→D clean→`I|clean` no-op→`I|invalidate`/`I|flush`/区间 invalidate→执行新立即数 `0x3333/0x5555/0x7777`。与 CACHE-15…20 对齐 ✓。
**off 口径（m16-spec-002 / CACHE-27）**：004 期望 `exist=0`、五寄存器可访问、合法命令接受无效果（见证值）、非法编码仍 `CFXREG`（cause+编码两槽）；QEMU/gem5 实跑 PASS；RTL 无该开关 ⇒ GAP 登记合理。
**DIV-15/16**：DIV-15 `permanent` **可接受**（与 DIV-01 同类：QEMU 无 I 阵列，`cputlb.c` 的 `notdirty_write→tb_invalidate_phys_range_fast` 属实；该点已移出签名槽、结构性不可判）；其 impact「同值/不进槽」措辞自相矛盾 → **F3**。DIV-16 `temporary` + `close_when` 明确 ✓；**号复用干净**（13 条 id 无重复、DIV-15 仅 1 条，024 已删旧条）。**RTL 补 cfx5 `commonRows`（cg0–cg7/deleg + 回填 `cache_rtl.S` 掩码写）当前无对应任务** → 遗留①应立任务，交 architect/用户裁定。
**umon env 回归**：`common/env-umon/env.S` 仅 +10 行、`.ifdef ENV_CFX_ACCESS_5` 门控（仅 4 条 cache 用例声明 `cfx_access:[cache]`）；代表集实跑 qemu+gem5：`arch-umon-012` umon/hmon、`arch-power-001` umon、`arch-time-001` umon、`arch-ptw-001` hmon **全 rc=0**；`check_pmem.py --root . --mode 3/2/0 --self-test` rc=0（pmem 未登记索引、无 run_arch case）。
**门控**：`run_arch --self-test` rc=0（36 case、cache 4 case 61 槽）；两个 `--selfcheck` rc=0；`check-tests-index` 498 条 rc=0；`check-tasks` rc=0；`check-knowledge-refs` 0 悬空 rc=0（**本记录写入后已重跑**）。
**约束核验**：改动集 = 9 改 + 8 新 + 本任务书，与验收前后 `git status` 18 行快照逐行一致、目标文件 md5 前后相等；未改 `spec/`、契约、平台实现、cache 几何；未提交 git；术语「寄存器组」；无运行期路径；GAP 记 77 非 PASS、fail-closed 未被绕过。
**遗留判定**：① RTL cfx5 S/U ⇒ 留 + **立 issue/任务**；② DMA 直读 ⇒ 留（范围外、已登记未覆盖项，建议入 backlog）；③ `I|clean` QEMU 不可判 ⇒ 留（DIV-15 + RTL 日志断言 + gem5-022）；④ CACHE-21/29 不设槽 ⇒ 留（单 hart/无可观测差，理由成立）；⑤ RTL 维护端口 48 位截断 ⇒ 留 + **应立 issue**（触碰 CACHE-18「56 位不截断」，本任务 PA 均 <48 位未触达）。
**finding（均不阻断）**：F1 完成区「21 条款」应为「表格 19 / 节内 23」；F2 `rtl-coverage.yaml`/DIV-16 reason 的异常类应写实测 `CFXPERM`；F3 DIV-15 impact 措辞；F4 `run_arch.py` 自检静态文案仍写「chipyard 的 cfx4/cfx34 已接…其余 fail-closed」未含 cfx5。
**判决**：**Accepted**（12/12、20/20、独立注入红→还原→绿、三方逐槽一致、门控全绿、约束无违反；F1–F4 交 architect 收尾订正）。
