# m16-testcases-015: `tests/arch` 运行模式环境（hmon/smon/umon）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-006`（骨架）、`m16-testcases-005`（签名）已合入
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景（用户 2026-11-22）

`tests/arch` 现在每个载体自己决定运行模式：`umon/*.s` 有的经 SEE bootrom 进 user、有的 body 在 hypv；`ptw` 的 body 固定 hmon；`cache` 的 RTL 探针固定 hmon。用户要求：**增加 hmon/smon/umon 的构建环境，让多数测试能在不同运行模式下运行**。

目标是把「测试 body」与「运行模式环境」分离：body 一份，env 负责进入指定模式、设栈、装异常向量、退出与签名区；`run_arch.py --mode hmon|smon|umon` 选择环境。

## 要做

1. **env 目录**：`tests/arch/common/env/{hmon,smon,umon}/`，每个含：
   - 启动/进入：从 BootROM 或 prelude 进入目标模式（`switch_run_mode`/`trap`）；
   - 链接布局与栈；
   - 异常向量/回落槽；
   - 退出：semihosting `SYS_EXIT`；
   - 签名区：复用 `tests/shared/signature.inc`。
2. **驱动**：`run_arch.py` 增加 `--mode hmon|smon|umon`；默认 `hmon`；不支持的组合 fail-closed。
3. **用例元数据**：`tests/arch.yaml` 或用例旁增加 `modes: [hmon,smon,umon]`（每用例允许集）；不能在该模式运行的用例显式标注原因（如 cfx0 的 user 进入本身依赖 U-mode）。
4. **代表迁移**：选 1 个不依赖特定模式的用例（建议 ptw 的寄存器面或 cache 寄存器面）迁移为「body + env」，在 hmon/smon/umon 三模式各跑一次；签名一致（或按权限差异登记）。
5. **未覆盖登记**：列出仍需逐件迁移的用例清单；本任务不迁全部。

## 不做

- 不迁移全部用例（后续逐件）；
- 不改测试语义/期望；
- 不改 QEMU/gem5/RTL 实现。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集限 `tests/arch/**`、`tests/arch.yaml`、`tests/arch/README.md`、本任务书；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. 代表用例在 hmon/smon/umon 三模式各跑一次，签名逐槽一致；若某模式因权限不可用，必须显式 fail-closed 并写明原因，不得静默跳过；
2. `modes` 元数据现场校验（缺项/非法模式 ⇒ 红）；
3. **可达 FAIL**：注入「env 模式写错」⇒ 进入错误模式/签名红；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路；
5. 未迁移用例清单存在且可读。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` 正向 **19/19 PASS**（rc=0）；`run.sh --inject` **31/31 PASS**（rc=0，3 路注入）；`run_arch --self-test` rc=0；`run_arch --level smoke --platforms qemu` 10/10 PASS（rc=0）。L2 `make check-arch-smoke` 因 gate 锁被其它会话的 build-qemu 长期占用未启动（等价冒烟已直接跑过，见下）。

**修改文件**：
- 新增 `tests/arch/common/env/{README.md,MIGRATION.md,env.lds,hmon/env.S,smon/env.S,umon/env.S}`
- 新增 `tests/arch/umon/mode_regs.body.S`、`tests/arch/umon/check_mode_env.py`
- 新增 `tests/arch/modes.yaml`（每用例允许集 + 被排除模式的显式原因）
- `tests/arch.yaml`（新增 `arch-umon-011` 条目；字段集不变，避免 `check-tests-index` 白名单）
- `tests/arch/run_arch.py`（`--mode`、modes 双向校验、`N/A`+原因、全排除 exit 2）
- `tests/arch/common/platform.py`（多模式 driver 传 `--mode`；asm 非 hmon 显式失败）
- `tests/arch/README.md`、本任务书

**验收结果**（真实输出摘要）：
- 三模式签名 md5 相同：`1f113d8a…b4ea`，各 64 B / 8 槽；`-d cpu` 观测 body 窗口 MODE = hmon 3 / smon 2 / umon 0。
- 注入：env smon `switch_run_mode` 2→3 ⇒ rc=1「运行模式未观测到」；body 暂存写值 EF→EE ⇒ rc=1「签名流」；modes.yaml 去 smon 且不给原因 ⇒ self-test rc=1「缺 reasons.smon 原因」；均 `cp`+md5 还原回绿。
- 门控：`check-tests-index` rc=0；`check-tasks` rc=0；`check_manifests_guard.py` rc=0；`check-knowledge-refs` rc=2，但悬空集与 HEAD 基线逐行相同（ADR-0059 ×2，KNOWN-RED）。

**新发现/坑**：
- `check-tests-index` 对 `tests/arch.yaml` 有字段白名单，不能直接加 `modes`；改用并列 `modes.yaml` 并与 arch.yaml 双向校验。
- Vast `-kernel` 的 ELF 路径走 K0 契约（VA=PA+2 TiB），测试 body 只能用 flat bin；umon 需在 env 内把 body 拷到 U 页。
- `ld.o/st.o` 必须 8 字节对齐；按 4 字节拷贝会 MALIGN 且被 hmon resume 静默掩盖。
- step5 页表 HSJU=0xC；supv 访问 cfx_umon cg4–cg8 还需 `cg_reg_deleg=0x8`；cfx_smon 的 supv 向量从 cfx_umon 写不进去（缺省掩码），已在 env README 登记。
- 跑门控会导入 `tests/ee-tiny` 产生 `__pycache__`，使 `check-manifests-guard` 红；证据脚本统一 `PYTHONDONTWRITEBYTECODE=1`。

**遗留问题**：未迁移清单见 `tests/arch/common/env/MIGRATION.md`（umon 10 条 asm、ptw 15 条 driver、cache cfx5 未登记）；smon 同步异常向量 / umon U 页受 step5 固件与 L1[3] 布局约束，后续按件迁移；L2 `make check-arch-smoke` 待门控锁空闲时补跑（本任务改动已由等价冒烟覆盖）。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 `run_arch.py`（modes 解析/过滤/退出码）、`platform.py`（`--mode` 仅多模式 driver；asm 非 hmon 显式失败）、`check_mode_env.py`（期望派生、模式观测、签名解析、还原）、三份 `env.S` 与 body（`rb1`/`rb6` 契约、8 字节对齐、跨 1.5 GiB 的分支范围）、`modes.yaml`（26 条全覆盖）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `modes` 写进 `tests/arch.yaml` 被判未知字段 | ✅已修 | 改 `tests/arch/modes.yaml` 并列清单 + 双向校验 | `check-tests-index` rc=0；注入 3 rc=1 |
| QEMU 以 work 为 cwd，相对 `-kernel` 路径 rc=1 | ✅已修 | `work.resolve()`，命令参数全绝对路径 | 三模式 rc=0 |
| 4 字节增量拷贝触发 `MALIGN`（被 hmon resume 掩盖） | ✅已修 | umon 拷贝改 8 字节粒度（`ENV_COPY_OCTAS`） | 三模式签名一致 |
| umon 退出例程在 ENTRY 页（U=0）⇒ user 取指 NUPERM | ✅已修 | `.envtail` 随 body 拷到 U 页，`rb6` 指向拷贝 | umon rc=0 / MODE=0 |
| 注入 2 首次替换命中注释而非指令，假绿 | ✅已修 | 锚点改为 `set.rd rd6, 0x…` 指令行 | 注入 2 rc=1「签名流」 |
| `tests/ee-tiny/__pycache__` 使 manifests 门控红 | ✅已修 | 证据脚本 `PYTHONDONTWRITEBYTECODE=1` + 清理 | 直接脚本 rc=0 |

判决：findings 已全部修复，状态置「待验收」。

### 第 1 轮 reviewer 验收

**重跑（我自跑，不采信完成区）**：仓库根执行运行期证据目录内的 `run.sh` → **19/19 PASS，rc=0**；`run.sh --inject` → **31/31 PASS，rc=0**（3 路注入先红后 `cp`+md5 还原回绿）。门控我自跑：`check-tests-index` rc=0（488 条）、`check-tasks` rc=0、`check-knowledge-refs` rc=2（悬空 ADR-0059 ×2；`.tao/knowledge`、`.tao/contracts` 相对 HEAD 干净 ⇒ 与基线同集，KNOWN-RED 属实）。等价冒烟 `run_arch --level smoke --platforms qemu` → **10/10 rc=0**。

**独立注入 3 路（备份入临时目录，`cp`+md5 对账，未用 git 还原）**：
- A env 模式写错：umon `switch_run_mode` 0→2 ⇒ rc=1「运行模式未观测到…实际 [2]」+ 签名 0≠64；还原 md5 `3f98cd79…` ⇒ 回绿 rc=0。
- B 签名值错：body 槽 3 掩码 `0xFFFF`→`0xFFFE` ⇒ rc=1「槽 3 期望 0x0000000000000001 实际 0x0」；还原 `9079a7dd…` ⇒ 回绿 rc=0。
- C 元数据放开：`modes.yaml` 给 asm 用例 `arch-umon-001` 开 smon 并删其原因 ⇒ `--case arch-umon-001 --mode smon` rc=1 显式「kind=asm 载体尚未接运行模式环境…不得静默按 hmon 跑」；还原 `6fed7327…` ⇒ self-test rc=0、该组合回 rc=2。注入后全量 md5 与注入前快照逐项一致，无备份残留。

**三模式/环境判定**：三模式签名 md5 同 `1f113d8a…`，64 B / 8 槽（`0x0123456789ABCDEF`、全 1、3、1、0×4）；`-d cpu` body 窗口观测 `[3]/[2]/[0]`（hmon 不再进模式；smon = `switch_run_mode=2` + `trap cfx_umon, 0`；umon = 0），模式由模拟器现场观测、不由 body 自述。umon 的 L1[3] 处理 = 写 PA0+24 的 PTE3（HSJU=0xF）+ 8 字节粒度拷 body/tail 进 U 页；smon 只写 `cfx_umon` 行、不装 `cfx_smon` 向量（回落 `0xE1`）——与 README「已知限制」一致且属实。`--mode` 缺省 hmon；`--mode bad`、`--case 不允许`、`全被排除` 三种组合均 rc=2；gem5（缺件）与 chipyard（SKIP）对代表用例均 FAIL rc=1，fail-closed 属实。

**未迁移清单**：`MIGRATION.md` 覆盖 `tests/arch.yaml` 全 26 条（umon 001-010 段、ptw 001-015 段按区间写、011 已迁移）+ cache `cfx5`（未登记），可读。

**合并冲突点（供 architect 定夺，我不代判）**：`tests/arch/run_arch.py` **3 处**——① docstring 用法示例（master 把 smoke 改 `--cache-model off` 并加注释行 / 015 保留 `on` 并加 `--mode` 行，**两方都留**）；② `run()` 横幅（master `cache-model=%s`+`args.cache_model` / 015 加 `mode=%s`+`args.mode`，**合成一行两参数都留**）；③ `run.json` 字段（master `"cache_model": args.cache_model` / 015 加 `"mode": args.mode`，**两者都留**）。`tests/arch/README.md` **1 处**：代码块示例（master 三行 off 示例+注释 / 015 的 `--case … --mode smon` 行，**双方都留**）。自动合并但须复核语义：master 删除了 `run()`/`list_plan()` 里 `cache_model != "on"` 的护栏（015 未改该行 ⇒ 取 master 删除），合并后 `--mode` 与 `--cache-model off` 共存；`tests/arch.yaml`（master 改注释路径 + 015 追加条目）与 `platform.py`（master 未改）无冲突。合并后一致性我已试算：合并版 `arch.yaml` + 本分支 `modes.yaml` 过 `load_index` ⇒ 26 条 OK（master 未新增 arch 用例，id 集与基点相同）。

**findings（均文档级，不阻断）**：① `MIGRATION.md` 称「只登记 `hmon`（`tests/arch.yaml` 的 `modes`）」，字段实际在 `tests/arch/modes.yaml`；② `modes.yaml` 头注释「缺省条目 = [hmon]」与实现不符（每条必须显式非空 `modes`，缺项即红）；③ L2 `make check-arch-smoke` 仍未跑成——我自跑时 gate 锁**空闲**，失败根因是本 worktree 未 fetch LLVM 源树（`_locked-build-mc` 的 CMake 找不到源目录 ⇒ rc=2），与完成区「锁被占用」的记述不同；等价冒烟我已自跑 10/10 rc=0，合并入主仓后须补 L2；④ master 侧 README「`--cache-model` 固定 `on`；传 `off` 退出 2」与其已允许 `off` 的代码不符（既有陈旧，合并时顺手订正）。

**约束核验**：变更集 = 5 改 + 9 新，全部落在任务书允许范围（`tests/arch/**`、`tests/arch.yaml`、`tests/arch/README.md`、本任务书）；任务书与新增文档无具体运行期路径；术语「银行」0 处；我未提交 git；注入全部 `cp`+md5 还原，收尾 `git status --porcelain -uall` 与开工快照逐行一致。

**判决：Accepted**
