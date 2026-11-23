# m16-testcases-016: cfx63 power 基础用例（三方）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-015`（运行模式环境）合入（同改 `tests/arch`，串行）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待验收

## 背景（用户 2026-11-22 选 A）

9 个 cfx 里 cfx63 是唯一“三方都有实现、但用例覆盖不均”的：QEMU 有 step5 启动链（`integ046t`），gem5 Vast 无用例，RTL 只有 `prevcfx.S`/`causeid.S` 手工探针。本任务补一件 cfx63 **基础用例**，把三方签名对齐。

## 要做

1. **寄存器面**：`cfx_power` 的 cg7 BootROM 块（start/size）、power ctrl、复位 `inner_cfx_code=63`；位域/读写属性按 `contract-see`/`Kaiwu §3` 现场解析。
2. **移交语义**：power→hmon 的 `trap cfx_hmon`；hmon 收到的 `prev_cfx`/`inner_cfx_code` 与 `cg5 rc1` 一致（复用 `prevcfx.S` 的检查点）。
3. **载体**：复用 step5 启动链（`tests/ee-vast/power_vast.S` + hmon），QEMU/gem5/RTL 各后端；RTL 侧把现有 `tools/chipyard/excp/prevcfx.S` 的检查点纳入统一 case。
4. **三方**：QEMU + gem5 先跑；RTL 侧可直接接（power 已实现），签名逐槽一致；不一致登记 `expected-divergences.yaml`。
5. **不回归**：step5 启动链（`integ046t`）、Tiny 的 power/hmon、cfx3/4/5 现有用例不变。

**H/S/U 三模式**（用户 2026-11-22）：cfx63 的寄存器面/移交应在 `hmon`/`smon`/`umon` 三种运行模式下各跑一次（`run_arch.py --mode`）；权限不允许的模式显式标注 `modes` 排除原因。

## 不做

- 不做 cfx63 的电源域/时钟等平台功能（只做 cfx 寄存器 + 移交）；
- 不改 QEMU/gem5/RTL 实现；
- 不做 cfx0/2/15/32/34（各自任务）。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语「寄存器组」；
- 仿真不进 L2/L3（按需 `check-arch-vast`）。

## 验证

运行期证据目录内的 `run.sh`：

1. cfx63 寄存器面：cg7 BootROM 块、power ctrl、复位 `inner_cfx_code=63` 逐项；
2. power→hmon 移交：`prev_cfx`/`inner_cfx_code`/`cg5 rc1` 与期望一致；
3. 三方同一 ELF 签名逐槽一致（RTL 侧可直接接；若暂不可用，显式 fail-closed 并登记）；
4. **可达 FAIL**：注入「移交后 `prev_cfx` 错」/「cg7 块错」⇒ 红；`cp`+md5 还原回绿；
5. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录 `run.sh` 全绿 **21/21 rc=0**（79 s）；`run.sh --inject` **17/17 rc=0**（56 s，3 路注入均先红后绿，`cp`+md5 还原）。另有 `check_slots.py` 逐槽 **10 组流** PASS、`check_power(_rtl) --selfcheck` rc=0、`run_arch --self-test` rc=0。

**修改文件**：
- 新增：`tests/arch/power/{power_vast.py,check_power.py,gen_power_rtl.py,check_power_rtl.py,power_rtl.lds,expected.yaml}`；
- 修改：`tests/arch.yaml`（+`arch-power-001/002`，`kind: driver`、`level: full`）、`tests/arch/modes.yaml`（001 三模式；002 只 hmon + 两条排除原因）、`tests/arch/expected-divergences.yaml`（DIV-12/DIV-13 + 可选 `slots` 逐槽例外）、`tests/arch/README.md`（目录表 + power 小节 + 三方差异 + 5 条未覆盖项）。

**验收结果**：
- **寄存器面逐项**（`arch-power-001`，28 槽；`expected.yaml` 与现场派生双向核对）：`cg7` 块 0 `desc=0x5`、`start=0x3ff_ffc0_0000`、`size=0x40_0000`、`attr=0x5`（`R|X`）；块 1–15 的 `desc` 全 0、块 15 的 `start/size/attr` 全 0；`cfx_power_ctrl`（`cg8 rc1`，WO）**读 ⇒ `CFXREG`**（`arch-power-002`）；`cg7` 写 ⇒ `CFXREG`；`cg8 rc2` 读 ⇒ `CFXREG`。
- **移交三值**（power→hmon 帧，hmon 读 `cfx_hmon cg5`）：`prev_cfx=0x3f`（= 复位 `inner_cfx_code=63`）、`prev_mode=0x3`（hypv）、`cause_id=0x1`（`CFXTRAP`）、`cause_ip` 落在 BootROM 窗口（归一化 1）；`cg5 rc1` 三值一致（读 0x3f、写哨兵 0x25 读回 0x25、写回 0x3f 读回 0x3f）。
- **三方签名逐槽**（QEMU/gem5 同一份 4 MiB BootROM 字节；RTL 同一探针表生成 `.S`）：26 槽三方全一致；槽 5/6 按登记 **DIV-12** 判（RTL `0x3ff_ffff_0000`/`0x1_0000`，QEMU/gem5 规范值 `0x3ff_ffc0_0000`/`0x40_0000`），`DIVERGED` 行落日志，例外被修好时承载判红。
- **三模式**：`arch-power-001` 在 hmon/smon/umon 各一次（qemu+gem5 两引擎 × 三模式签名逐槽同）；`-d cpu` 的 `MODE:` 现场观测到 3/2/0 均落在 body 窗口；`arch-power-002` 只 hmon（smon/umon 排除原因已登记）。
- **不回归**：`run_arch --level smoke` 10/10、`check-tests-index` rc=0（492 条）、`check-tasks` rc=0、`check-knowledge-refs` rc=0（0 悬空）；`--level smoke --list` 不含 power 用例（不进 L2/L3）。

**新发现/坑**：
- **RTL 的 Vast BootROM 几何复用 Tiny**（`WumingVastAddressMap.bootROMBase` = Tiny 的 `0xffff_ffff_0000`/64 KiB）⇒ `cfx_power cg7` 块 0 与 `spec/Kaiwu §3`/`machine.yaml` 的 4 MiB 不符 ⇒ **DIV-12**（实测发现，非猜测）。
- **RTL 的 `cfx_power` 未开 common face**（`commonRows=false`）⇒ `cg4`/`cg6` ⇒ `CFXREG`，QEMU/gem5 有 ⇒ **DIV-13**（不纳入比较面，`--diagnose` 逐方报告）。
- **`cfx_power_ctrl` 三个实现都没有**：写 0 收 `CFXREG`，而 `spec/Kaiwu §3` + `DADAO-12 §4.12` 的 WO 语义要求写被接受 ⇒ 不写进判据（不拿实现当期望），建议立 issue（scope qemu/gem5/chipyard）。
- `node_probe_prelude.Seq.resolve()` 只支持 `eq/ne/nz/z/nn`（无 `br.n`/`br.np`）⇒ 载体自带 `_BrFix` 回填；`cmp.uo` 的编码取 `contracts/opcodes.yaml` 的 `value`（`0x40A80000`）。
- **supv 下「源 cfx」= 3**（`trap cfx_hmon` 后 `inner_cfx_code` 取目标 cfx）：`cfx_power` 的 supv `cfxreg` 位本就允许（bit3=0），只需 `cg3 rc12` deleg；`user` 不查 deleg ⇒ umon 无权限准备（smon 的 deleg 注入 B 证明它在生效）。
- **失败路径形态**：`-d cpu` + `-dfilter` 限定 body 窗口 + 15 s 超时 ⇒ smon 授权失败实跑 dump **291 KB**（012 的同类失败是 11.7 GB/tmpfs 打满，`ISS-522`）。

**遗留问题**：
- **DIV-12 / DIV-13 待用户裁定**（temporary 定性、修 RTL 还是改 spec 口径）；本次只登记，未改 RTL/spec/contracts。
- `cfx_power_ctrl` 写侧不测（三实现缺寄存器），已登记 README 未覆盖项第 1 条；建议立 issue 后补写侧探针。
- RTL 未进 `run_arch`（chipyard 后端仍 fail-closed，归 `m16-chipyard-018`/按需 `check-arch-vast`）；RTL 侧固定 `cfx_power`/hypv，无 U/S 进入链。
- umon 的寄存器面读取与 hmon 同权限（掩码看源 cfx=3）⇒ umon 的模式见证只有 `MODE:`（没有「user 才失败」的负例）；smon 有 deleg 注入 B 作强证据。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`power_vast.py`（合约派生/探针表/phase 发射/模式切换/deleg 准备与还原/失败路径/诊断）、`check_power.py`、`gen_power_rtl.py`、`check_power_rtl.py`（逐槽 + 登记例外）、`power_rtl.lds`、索引/模式/期望/差异登记、README 小节，以及运行期 `run.sh`/`inject.sh`/`check_slots.py`/`check_uncovered.py` 的 rc 捕获与还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 移交 4 槽放在模式切换**之后** ⇒ umon 读到降模式那次 `trap` 自己的帧（槽 0 = 3 而非 63） | ✅已修 | 槽表加 `phase`（pre/mid/post），pre 在降模式前发 | umon 槽 0 由 3→63；三模式 28 槽全一致 |
| F2 `cause_bits()` 的正则少了名字后的反引号 ⇒ 恒抛「缺原因」 | ✅已修 | 正则改 `` `([A-Z_]+)` `` | `--selfcheck` 打印 `CFXTRAP=0x1 CFXREG=0x4` |
| F3 `Seq.resolve()` 不支持 `br.n`/`br.np` ⇒ 构造 body 即 `ValueError` | ✅已修 | 新增 `br_cond()` + `_BrFix`（resolve 后回填） | `ip_in_rom` 槽三方实测 = 1 |
| F4 `--diagnose` 只记 cause 不记读回值 ⇒ 看不出「被接受但值是多少」 | ✅已修 | 每探针两槽（cause, 值） | `cfx_id` 诊断 qemu/gem5 = 63、RTL = CFXREG |
| F5 故障处理程序用 rd5，与诊断的「读回值」槽同寄存器 ⇒ 值被 cause 污染 | ✅已修 | 处理程序改 rd9 | 诊断 `power_ctrl_write0.value` 由 4→0 |
| F6 `run.sh` 抓「未覆盖项」的 awk 命中 fence 小节 ⇒ 计数 0（假红） | ✅已修 | 改为 `check_uncovered.py` 只取 power 小节 | `POWER-SECTION-UNCOVERED: 5 条` |
| F7 `run.sh` 的 diagnose 日志名与解析器大小写不一致 ⇒ rtl 读不到（假红） | ✅已修 | 统一小写 `diagnose rtl` | 诊断对账 rc=0，三方值齐全 |
| F8 `check_power_rtl --selfcheck` 里 `[rb20,0xE0]` 计数留了自相矛盾的两段 | ✅已修 | 收敛为 `2 × 故障槽数` + `n_fault + 1` 回落点 | selfcheck rc=0（001 0 次、002 6 次） |
| F9 `expected.yaml` 的 `schema` 写成自定义名，与 arch 既有（`1`）不一致 | ✅已修 | `schema: 1` | `check-tests-index` rc=0（492 条） |
| F10 RTL 的 `cg7` start/size 与规范不符 | ⏸延后（登记） | 不改实现（任务「不改 QEMU/gem5/RTL」）⇒ DIV-12 + `slots` 例外 | 注入 C：改例外值 ⇒ RTL 判红；还原 ⇒ 回绿 |
| F11 RTL 缺 `cfx_power cg4/cg6` | ⏸延后（登记） | 不纳入比较面（不把缺口写进判据）⇒ DIV-13 + `--diagnose` | 诊断三方值逐方落日志 |
| F12 `cfx_power_ctrl` 写侧（WO）三实现皆缺 | ⏸延后（登记） | README 未覆盖项 1 + 建议立 issue；判据只写「读 ⇒ CFXREG」 | 诊断 `power_ctrl_write0` 三方均 `CFXREG` |
| F13 `--bootrom`/`--cache-model` 被接受但不用（run_arch 对多模式 driver 无条件传） | ❌不修（有据） | 载体自建 4 MiB BootROM、arch 固定 cache 语义；拒绝会让 run_arch 无法调用 | 两参数在 `argparse` 里带说明；run_arch 三模式 rc=0 |

### 第 1 轮 reviewer 验收（2026-11-23）

**重跑（仓库根；证据脚本 = 运行期证据目录内的 `run.sh`，参数 `--inject`）**
- `bash run.sh` → **rc=0**：`SUMMARY: 21/21 检查通过；FAILS=0`、`RESULT: PASS`，实测 1 m20 s；其 PASS/FAIL 行与 engineer 首轮记录 `diff` 逐行一致。逐条 rc：`driver/RTL generator/run_arch --self-test`=0；`arch-power-001` hmon/smon/umon、`arch-power-002` hmon（qemu+gem5）=0（28/28/28/3 槽）；`RTL arch-power-001/002`=0；`逐槽比对`=0（`SLOT-CHECK: PASS（10 组流）`、`DIVERGED 槽 5/6（登记 DIV-12）`）；`diagnose`×3+诊断对账=0；`check-tests-index`=0（492 条）、`check-tasks`=0、`check-knowledge-refs`=0（0 悬空）；`run_arch --level smoke`=0（10/10）；`modes 对账`=0；`POWER-SECTION-UNCOVERED: 5 条`。
- `bash run.sh --inject` → **rc=0**：`INJECT: PASS（3 路注入均先红后绿，cp+md5 还原；未用 git 还原）`，17 步全 PASS。
- 审查前后 `git status --porcelain -uall` 与 10 个交付文件 md5 **逐行/逐值相同**（还原一律 `cp`+md5，未用 git 还原）。

**寄存器面 / 移交 / 三方**
- 寄存器面来源：`machine.yaml(vast)` base `0xffff_ffc0_0000` − (63<<42) = `0x3ff_ffc0_0000`、size `0x40_0000`，与 `spec/Kaiwu §3` 的 Vast 显式值**双向核对**（不符即 SetupError）；`desc=exists|ROM=0x5`、`attr=R|X=0x5` 的位号从 `DADAO-12 §3.8` 现场解析；块 1–15 `desc=0`（15 槽）、块 15 `start/size/attr=0`（3 槽）；派生不读任何实现（实现未参与期望值）。
- 移交：body 在降模式**前**读 `cfx_hmon cg5`（写者是硬件 trap 帧，非测试自写）= `0x3f/0x3/0x1`，`cause_ip` 归一化 1；`cg5 rc1` 初读 `0x3f` → 写哨兵 `0x25` 读回 `0x25` → 写回 `0x3f` 读回 `0x3f`（槽 0/26/27），qemu/gem5×三模式 + RTL 现场值全等（非自证）。
- 三方：28 槽中 **26 槽一致**，仅槽 5/6 按登记 DIV-12 判；`observed_body_modes` = hmon[3] / smon[2,3] / umon[0,3]；`arch-power-002` 只 hmon、两条排除原因在位。

**独立注入（reviewer 自做 4 路，均先红后绿、`cp`+md5 复等）**
1. 期望首槽 `0x3f→0x3e`：`check_power.py --selfcheck` rc=1（`expected.yaml 签名与现场派生不一致`）；`run_arch --case arch-power-001 --mode hmon --platforms qemu` rc=1（`槽 0 期望 …003e 实际 …003f`）→ 还原后两者 rc=0。
2. smon deleg `P.load_rd(6, 0x8)` 两处 `→0xFF`：`run_arch --mode smon` rc=1（进 smon 后 `cfx_power` 读被拒、无该模式 handler ⇒ 15 s 超时、无签名）→ 还原 rc=0 ⇒ deleg 写确在生效。
3. DIV-12 槽 5 例外值改成规范值：`check_power_rtl --only arch-power-001` rc=1（`槽 5 实测 … ≠ 登记差异 DIV-12 的值 …需更新/删除登记`；同轮槽 6 仍 `DIVERGED` ⇒ **例外只作用于指定槽位**）→ 还原 rc=0。
4. 删除 DIV-12 的 `slots` 整段：`check_power_rtl` rc=1（槽 5/6 按规范值判红）⇒ 无登记即 fail-closed、不静默跳过 → 还原 rc=0。

**判定**
- **DIV-12 是真差异**（`spec/Kaiwu §3` 要 4 MiB、`machine.yaml(vast)` 同；chipyard `WumingVastAddressMap.bootROMBase/Size` 复用 Tiny 的 `0xffff_ffff_0000`/64 KiB，推导值 = RTL 实测 `0x3ff_ffff_0000`/`0x1_0000`）：`temporary`+`close_when`+机器可读 `slots`+`DIVERGED` 落日志 ⇒ 临时登记合理；`user_ruling` 仍「待裁定」⇒ 请 architect 收尾交用户裁定。
- **DIV-13 应立 issue 修 RTL**（登记为过渡合理）：`DADAO-12 §3.5/§3.7` 明写「每个核芯功能扩展都有」cg4/cg6 ⇒ RTL 对 `cfx_power` 返回 `CFXREG` 是实现缺口，QEMU/gem5 合规范；方向是修 RTL 而非改 spec，本次「不纳入比较面 + `--diagnose` 逐方报告」不把缺口写进判据 ✓。
- **载体偏离可接受但披露不足**：任务书点名 `tests/ee-vast/power_vast.S`，实际用 `node_probe_prelude` 的 step5 同序链（三方同一字节；RTL 本就不能吃 4 MiB step5 ROM）；step5 链由 smoke 的 asm 用例以 `bootrom-image=bootrom_step5.bin`（由 `tests/ee-vast/power_vast.S` 构建）承载，本次 smoke 实跑 10/10 且日志见该 `bootrom-image` ⇒ step5 链有覆盖；完成区未把该偏离列为遗留（F-R1）。
- **未覆盖项诚实**：`cfx_power_ctrl` 写侧三实现均 `CFXREG`，只进 README 未覆盖项第 1 条与 `--diagnose`，未写进判据（未拿实现当期望）✓；建议立 issue。

**约束核验**：独立 worktree、未提交（`git status` 与开工快照一致）✓；改动 = `tests/arch.yaml`、`tests/arch/{modes,expected-divergences}.yaml`、`tests/arch/README.md` 追加（`git diff` tests/ 删除行 0）+ 新增 `tests/arch/power/*` ✓；`level: full` 且 `--level smoke --list` 不含 power 用例 ⇒ 未进 L2/L3 ✓；术语「寄存器组」无「银行」✓；本记录不含任何运行期目录具体路径 ✓。

**findings（均不阻断）**：F-R1 完成区未披露载体偏离（README 有、完成区无；提示中的「遗留 4」实为 umon 模式见证，编号对不上）；F-R2 既有 `.tao/contracts/contract-see.md` 的 power `start=0x3_ffc0_0000` 与 `spec/Kaiwu §3` 不符（非本次改动，建议收尾立 issue）；F-R3 `cfx_power_ctrl`「与规范不符」措辞偏强（`Kaiwu §3` 只明写 **Tiny** 未实现，Vast 口径未定，立 issue 前需 spec 先明确）；F-R4 DIV-12/DIV-13/`cfx_power_ctrl` 均「待裁定或建议立 issue」但尚无 issue 落账。

**判决：Accepted**（验收命令块在我自己的重跑下全绿、4 路独立注入先红后绿、约束无违反；4 条 finding 交 architect 收尾处理）。

