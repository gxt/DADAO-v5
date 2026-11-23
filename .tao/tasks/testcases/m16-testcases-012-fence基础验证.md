# m16-testcases-012: fence 基础验证（三方）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-qemu-004`（ISS-432 保留集对齐）合入
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待验收

## 背景（用户 2026-11-22 选 A，并明确完整覆盖暂不做）

`fence cfxHA, immu18` 是 M16 纳入的语义之一。`ISS-432` 修好后，先做**基础验证**；**完整覆盖（全部 cfx × 六位组合）不作为本任务验收要求**。

## 要做

1. 用例落 `tests/arch/`（cfx 选择相关的 fence 用例），由 `run_arch.py` 驱动；三方（QEMU/gem5/RTL）签名一致。
2. **基础验证**至少覆盖：
   - `cfx0` / `cfx_umon` = all cfx；
   - 指定 cfx（至少 cfx3 hmon、cfx4 ptw、cfx5 cache、cfx32 pmem、cfx34 time）；
   - 六位资源域（`cr`/`cw`/`ci`/`co`/`mr`/`mw`）各至少 1 个基本组合；
   - 保留集采样：cfx16/17/18 ⇒ `ILLI`、cfx32/33/34 ⇒ 放行；
   - `hb`（`immu18` 的高位/保留位）非 0 ⇒ `ILLI`（按契约）。
3. **未覆盖项登记**：在 `tests/arch/` 或任务书列明“未做的完整组合”，不假装全覆盖。
4. **不回归**：cfx3/4/5 现有语义与 `check-arch` 不回归。

**H/S/U 三模式**（用户 2026-11-22）：fence 用例应经 `tests/arch/common/env/` 在 `hmon`/`smon`/`umon` 三种运行模式下各跑一次（`run_arch.py --mode`）；权限不允许的模式必须显式标注 `modes` 排除原因并 fail-closed。

## 不做

- 不做全部 cfx × 六位组合的穷举；
- 不把“完整覆盖”写进验收；
- 不改实现（ISS-432 由 qemu-004 修）。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 用例/期望集中 `tests/arch/`；不写运行期路径；术语「寄存器组」；
- 仿真不进 L2/L3（按需 `check-arch-vast`）。

## 验证

运行期证据目录内的 `run.sh`：

1. 基础验证用例三方签名逐槽一致；
2. 保留集采样 6 条（16/17/18/32/33/34）与 `hb≠0` 逐条；
3. **可达 FAIL**：改一条期望 ⇒ 红；`cp`+md5 还原回绿；
4. 未覆盖项清单存在且可读；
5. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录 `run.sh` 全绿 **18/18 rc=0**；`run.sh --inject` **14/14 rc=0**（A 改 `expected.yaml` 013 首槽、B 改 `FENCE_OPC`，两路均先红后绿，`cp`+md5 还原）。

**修改文件**：
- 新增：`tests/arch/umon/{umon_fence.py,check_fence.py,gen_fence_rtl.py,check_fence_rtl.py,fence_rtl.lds}`；
- 修改：`tests/arch.yaml`（+`arch-umon-012/013`，`kind: driver`、`level: full`）、`tests/arch/modes.yaml`（012 三模式；013 只 hmon + 两条排除原因）、`tests/arch/umon/expected.yaml`（`cases:` 两段签名流，17/10 槽）、`tests/arch/README.md`（目录表 + fence 小节 + 未覆盖项）。

**验收结果**：
- **三方签名逐槽一致**：012 hmon `qemu==gem5`、`rtl==qemu` 各 17 槽；012 smon/umon `qemu==gem5` 各 17 槽（smon 观测 `MODE=[2,3]`、umon `MODE=[0,3]`）；013 hmon `qemu==gem5`、`rtl==qemu` 各 10 槽。
- **保留集/hb 逐条**（013，实跑 `actual` 全 = `0x100`）：`reserved_cfx16/17/18`、边界 `cfx6/14/31/35/61`、`hb_bit12`（hb=1）、`hb_all`（hb=0x3F）；**放行** `cfx32_pmem/33_llc/34_time` 三模式 `actual=0`（012）。
- **三模式**：012 在 hmon/smon/umon 各跑一次（两平台）；013 只 hmon，smon/umon 排除原因已写入 `modes.yaml`（当前模式监视器不可用）。
- **不回归**：`run_arch --level smoke` 10/10、cfx4 ptw carrier 29/29、25 服务覆盖、`check-tests-index` rc=0（490 条）、`check-tasks` rc=0、`check-knowledge-refs` rc=0、`run_arch --self-test` rc=0。
- **未覆盖项**：`tests/arch/README.md`「fence 基础验证未覆盖项」5 条（穷举/交叉掩码/顺序语义/jmon/其余保留编号）。

**新发现/坑**：
- `common/env-*` 的权限准备在 gem5 上**过不了**（收窄 cfx5 `hypv.row.rc0` 回读写入 `0x8` 读回 `0x4`）⇒ env 三模式路径当前 QEMU-only；本任务改用 `node_probe_prelude` 自建 4 MiB BootROM（QEMU/gem5 同一份字节），模式切换用同一协议，两引擎均 `MODE:` 实测。
- `llvm-mc` 静态拒绝 `fence` 的 `hb≠0`（`encode_sbz`），RTL 生成器对**全部** probe 用 `.dd.t32` 原始编码（DADAO 无 `.word`）。
- `run_arch` 的跨引擎 `checks_equal` 按**行首**比对（不 strip）⇒ 驱动顶层 PASS/FAIL 行不得缩进，否则 `check_count=0`（假等）。
- RTL 固件 hmon 的 cause 槽 `HMON_BASE+0xE0` 会残留；故障 probe 前必须显式清零，否则「应异常未异常」可假绿。

**遗留问题**：
- 完整 cfx × 六位组合穷举不做（用户 2026-11-22 裁定），已在 README 登记；
- RTL 未接入 `run_arch`（chipyard 后端仍 fail-closed，归 `m16-chipyard-018`/按需 `check-arch-vast`），当前由 `check_fence_rtl.py` 按需跑；RTL 测试体固定 hypv、同步异常固定进 hmon；
- smon/umon 下「放行 fence 意外异常」走未装载的当前模式监视器（镜像中止/超时，非 PASS），无本地处理程序（要装载 `cfx_smon`/U 页处理程序，超出本任务）；
- cfx1（jmon）在 arch 范围外，只按合法性间接覆盖、未单列 probe。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`umon_fence.py`（合约派生、探针表拆分、两遍地址回填、hmon 处理程序、三模式切换、模式观测、selfcheck）、`check_fence.py`、`gen_fence_rtl.py`、`check_fence_rtl.py`、`fence_rtl.lds`、`arch.yaml`/`modes.yaml`/`expected.yaml`/README 的登记与原因；运行期 `run.sh`/`inject.sh`/`check_slots.py` 的 rc 捕获、注入与还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 放行面边界 probe `cfx5` 标成 `hmon`（cfx5 是 cache），误导且与 `cfx5_cache` 重复 | ✅已修 | 删除该 probe（18→17 槽）；`expected.yaml`/README 同步 | selfcheck 17 槽一致；run.sh 全绿 |
| F2 驱动 PASS 行缩进 ⇒ `run_arch` 的 `checks_equal` 计数 0（假等） | ✅已修 | 顶层 PASS/FAIL 行不缩进 | run.json `check_count={qemu:1,gem5:1}` |
| F3 `MODE_CODE` 硬编码 3/2/0，与 spec 漂移无防护 | ✅已修 | 新增 `mode_codes()` 从 `spec/Kaiwu §7.1` 现场解析并校验 | selfcheck/三模式 PASS |
| F4 `--cfx-access` 被静默忽略（本用例不访问 cfx） | ✅已修 | 显式报错 rc=2 | 手跑 `--cfx-access 0` 打印拒绝 |
| F5 模式窗口用 `_body_words()` 二次重建镜像（重复派生、可能不一致） | ✅已修 | `build_rom` 返回 body 字节数，run_case 直接用 | selfcheck/三模式 PASS |
| F6 RTL selfcheck 仍数 `.word`（生成已改 `.dd.t32`）⇒ 恒 FAIL | ✅已修 | 计数/回读改 `.dd.t32` | `check_fence_rtl --selfcheck` PASS |
| F7 `check_slots.py` 在 qemu 流缺失时仍可打印 `rtl==qemu`（空 ref 假绿） | ✅已修 | 无 qemu 参考流 ⇒ 直接 FAIL | 删/缺文件场景不通过（逻辑复核） |
| F8 smon/umon 的意外异常无本地处理程序（中止/超时，非 PASS） | ⏸延后 | 需装载 `cfx_smon`/U 页处理程序；已登记遗留 | 现状 fail-closed（rc≠0/短流） |
| F9 完整 cfx × 六位组合穷举 | ❌不做（用户裁定） | 未实现；README 登记 5 条未覆盖项 | README 小节可读（run.sh 检查） |
| F10 RTL 未由 `run_arch` 驱动 | ⏸延后 | chipyard 后端 fail-closed（`m16-chipyard-018`/`check-arch-vast`）；先交付按需 `check_fence_rtl.py` | RTL 012/013 实跑 PASS |

### 第 1 轮 reviewer 验收

**重跑记录（全部本人执行；rc 取被检命令自身，不采信完成区）**
- 运行期证据目录内 `run.sh` → `SUMMARY: 18/18 检查通过；FAILS=0` / `RESULT: PASS` / `RC=0`（73 s）。
- 运行期证据目录内 `run.sh --inject` → `INJECT: PASS（2 路注入均先红后绿，cp+md5 还原）` / `RC=0`（14/14；A/B 的 selfcheck rc=1、run_arch rc=1，还原 md5 与前值相等并回绿 rc=0）。
- `make check-tests-index` → `结果: PASS（490 条）` rc=0；`make check-tasks` rc=0；`make check-knowledge-refs` → `结果: PASS（0 悬空）` rc=0。
- 未跑 `make check-arch-smoke`（其依赖 `install-host` 动共享安装根，避免并发写）；run.sh 已覆盖其三段核心：smoke 代表集 10/10、cfx4 ptw carrier 29/29、25 服务覆盖，均 rc=0。

**三方逐槽 / 非同源自比**：`check_slots.py` 逐元素比（`zip` 逐槽、不等打印槽号，非长度/摘要）：012 hmon/smon/umon `qemu==gem5` 各 17 槽 + 逐 probe expected/actual；013 hmon `qemu==gem5` 10 槽；`rtl==qemu` 012 17 槽、013 10 槽 → `SLOT-CHECK: PASS（6 组流）`。签名来自三个不同二进制：qemu-system-dadao / gem5.opt（经 qemu_gem5_shim）/ chipyard Verilator（`+loadmem`，sim.log 有 `SYS_EXIT … cycle=17205 → host exit status 0`，`+semiout` 现场产出）；期望值由契约/规范现场派生，非从引擎反推。

**保留集/hb/放行**：013 实跑 actual 全 `0x100`——cfx16/17/18、边界 cfx6/14/31/35/61、`hb_bit12`、`hb_all`；放行 `cfx32/33/34` 在 hmon/smon/umon 三模式 actual 全 `0x0`（逐行核过）。

**风险 1（smon/umon 意外异常）**：独立注入 `trap cfx7` 于放行分支 → 012/smon 与 012/umon 均 `rc=-2 模拟器超时` + `签名字节数 0 ≠ 136` → 载体 `FAIL` **rc=1（非 PASS）**；hmon 对照注入 → `actual=0x100` rc=1；`cp`+md5 还原后 smon `PASS rc=0`、selfcheck rc=0。⇒ `run_case` 的超时/退出码、签名长度与逐槽、模式观测三条断言均可达 FAIL。`modes.yaml` 排除 013 的 smon/umon 理由成立（env-README 模式表 smon→cfx_smon、umon→cfx_umon + 已知限制「step5 链不装载 cfx_smon」），且已登记遗留（完成区遗留第 3 条）。

**风险 2（RTL 按需）**：`check_fence_rtl.py` 经 `chipyard_engine.run` 跑真 Verilator；`run.sh` 第 2 节无条件执行 `RTL 012/013`（均 rc=0）；缺仿真器/缺件走 `SetupError` → rc=2 → `run_chk` 计 FAIL，无静默跳过路径。

**期望值/索引/未覆盖**：`expected.yaml` 是唯一登记源（`gen_fence_rtl.py`、`check_fence.py` 都调 carrier `expected_values`，grep 签名数组仅 `expected.yaml` 命中）；`arch-umon-012/013` 均 `kind: driver` `level: full`，`run_arch --level smoke --list` 不含二者（grep rc=1），L2/L3 只跑 smoke ⇒ 不进 L2/L3。未覆盖项现场抽取 5 条可读、措辞诚实；`.dd.t32` 理由实证：`llvm-mc` 对 `fence cfx0, 0x1000` 报 `reserved encoding (hb … must be zero)` rc=1，hb=0 rc=0。

**独立注入（本人 ≥2 路，均 `cp`+md5 还原、md5 与注入前逐字相等；未用 git 还原）**：① `expected.yaml` 013 首槽 `0x100→0x101`：selfcheck rc=1、run_arch rc=1，还原后均 rc=0；② `fence_word` 的 `cfx<<18→cfx<<16`（绕过 opc/mask 交叉核对）：selfcheck rc=0 但 run_arch 012/013 **均 rc=1（行为红）**，还原后 rc=0；③④ 上述 smon/umon、hmon 异常路径注入。快照对账：`git status --porcelain -uall` 前后逐行相同，6 个目标文件 md5 前后相等（`MD5-EQUAL`）。

**findings（非阻断，交 architect 收尾改）**：F1 `run.sh` 的 SUMMARY 分母漏计「run.json 跨平台一致性」「未覆盖项」两块（只加 FAILS 不加 NRUN），失败时计数偏小，退出码判据不受影响；F2 `modes.yaml` 的 umon 排除理由引用 env-README「已知限制」不够贴切（该节 umon 条目讲页表 PTE，U 页向量在「进入方式」表），结论本身成立；F3 smon/umon 异常路径的失败形态是 60 s 超时且 carrier 开 `-d cpu`，实测单次失败写约 11.7 GB 日志，建议登记「短 timeout/禁 dump」遗留；F4 `inject.sh` 的 B 路红来自载体 rc=2（opc 交叉核对），建议补上②这类字段位移注入；F5 README 未覆盖项第 1 条「6 × 6 × 6 × 6 位域组合」与 cfxha(64) 口径不符。

**判决：Accepted**——验收命令块在本人重跑下全绿、逐条硬约束无违反；F1–F5 为文档级/健壮性小错，按裁定不阻断。

