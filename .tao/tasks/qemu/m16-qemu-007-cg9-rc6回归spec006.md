# m16-qemu-007: QEMU `cg9 rc6` 回归 spec-006（写落地、进入取 rc6）

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m18-spec-006`（已合入：`cg9 rc6` 复位 2、异步进入取该值）；`m16-qemu-006` 已合入（其 rc6「写忽略」实现与 spec-006 相反，由本任务回归）
**可并行分片**：否（`components/qemu` 单写者）
**预估**：1–1.5 h
**档位**：小改（复核 ≤20 min）
**状态**：待验收

## 背景（用户 2026-11-25 在 `m18-spec-006` 裁定①）

`cg9 rc6`（`async_switch_run_mode`）口径统一为：**RW、复位 2（supv）、异步进入取该寄存器当前值**；QEMU/IDL 实现不动、RTL 后补（`m16-chipyard-028`）。

但 `m16-qemu-006` 按更早的 `ISS-m16-003`（当时按「固定 supv」理解）把 QEMU 改成了「写接受但忽略、读回恒 2、投递固定 supv」——**与 spec-006 相反**。本任务把它改回 spec-006 行为。

## 要做

1. `cfx2rc` 写 `cg9 rc6`（`helper.c` 的 `case 6` 路径）：`a->switch_run_mode = val & 0x3` **落地**（去掉 `switch_run_mode_write_ignored` 门控）；读回该值；复位 2。
2. 异步进入：`inner_run_mode = a->switch_run_mode & 0x3`（当前已有 `helper.c:3209` 路径，确认没被 qemu-006 改掉；若有硬编码 2 则改回取 rc6）。
3. 探针/期望：`arch-hart-001` 增加「写 rc6=0/1/3 后读回」「异步进入按 rc6 切换」断言（与 `m16-chipyard-028` 的 RTL 面同场景）；`DIV-18` 收窄/关闭（`close_when` = QEMU 回归 + RTL 028 + 用例断言）。
4. **不改** spec（spec-006 已是真源）、不改 RTL。

## 不做

- 不改 RTL（028）；
- 不改其它 `cg9` 槽语义。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出、`make_patch.py qemu` 幂等；
- 不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 写 rc6=0/1/3 读回同值；复位 2；异步进入 `inner_run_mode == rc6`（含 rc6=0 进 user、rc6=2 进 supv 两条）；
2. 与 `m18-idl-002` 的 IDL 向量同场景一致（可只读对照，不在本任务改 IDL）；
3. **可达 FAIL ≥2**：注入"写忽略（恒 2）"、"进入硬编码 2" ⇒ 红；`cp`+md5 还原并重建回绿；
4. `check-patch-tree` qemu 段 0 problem、`check-component-changelog`、`check-knowledge-refs`、`run_arch --self-test` 记录 rc。

## 完成区

**测试结果**：运行期证据目录 `run.sh` **26/26 PASS、EXIT=0**：`arch-hart-001/hmon` 89 槽、`arch-hart-002` smon/umon 各 40 槽均 PASS；两路注入（读回恒 2 + 写不落地；异步进入硬编码 2）各 `FAIL`（命中 slot 18-20/84 与 slot 86）→ `cp`+md5 还原（`ed9b853f…` 逐字节相同）→ 重建回绿；arch 代表集 QEMU `--level all` 38 case PASS（cfx15/pmem/cache/time/umon/ptw/power）。
**修改文件**：`components/qemu/patches/target/dadao/{cpu.c,cpu.h,helper.c}.patch`、`components/qemu/changelog.md`、`tests/arch/hart/{cfx15.S,check_cfx15.py,check_hart.py,check_hart_rtl.py,expected.yaml,README.md}`、`tests/arch/expected-divergences.yaml`、`tests/arch.yaml`、`tests/arch/README.md`、`tests/arch/vast-arch-inventory.md`、`tests/arch/hart/cfx15_qemu.lds`（槽数注记）、本任务书；证据脚本在运行期证据目录。
**验收结果**：
- `cg9 rc6` 行为：读回 `switch_run_mode`（复位 2）；写 `val & 0x3` 落地；`dadao_async_enter()` 进入模式 = `rc6 & 0x3`（删除硬编码 supv）。
- 探针：`arch-hart-001` 增 rc6 复位 2、写 0/1/3 读回、supv 下 rc6=0/2 连续投递并以 `prev_run_mode` 证明 0→user、2→supv（89 槽）；`arch-hart-002` 仍 40 槽。
- `make build-qemu JOBS=32` PASS；qemu md5 `8b49d6d9ea9c39dc2dffc1ca7d02739b`（构建产物；未 `install-host`：共享安装根正被 m18-linux-024 内核长跑占用，证据脚本显式传 `--qemu`）。
- `make_patch.py qemu` 两次导出 md5 不变（幂等），69 补丁（3 改）；`check-patch-tree` qemu 段 **0 problem**（总 rc=1 仅 musl 段：运行期共享源树被其它会话改动，非本任务）；`check-component-changelog`/`check-knowledge-refs`/`run_arch --self-test` rc=0；IDL 只读对照 `idl_exec.py --self-test` 72/72（含 `async_switch_reset`/`write`/`entry`/`entry_uses_rc6`）。
**新发现/坑**：共享 `.work/source/qemu` 停在 m17 旧态（缺 m16-qemu-006 补丁）⇒ 按 `docs/Process-01` 删源树 → `make fetch` → `apply_series.py --component qemu` 收敛后再改；`switch_run_mode_write_ignored` 是 `spec/Kaiwu §2` 的 Tiny `cg0–cg3 rc8` 约定（非 cg9 rc6），删它会破 Tiny，保留；QEMU hmon 体进 user 需把镜像超页 PTE 置 U=1，`PTW_UMAP` 现同时传给 hmon（仅 QEMU 承载，hmon 内需在 hypv 相位写 PTE，supv 相位写会 `CFXPERM`）；arch 驱动会 `cd` 到 work-dir，`--qemu` 相对路径会 FileNotFound，证据脚本用绝对路径；`make_patch` 在源树脏时拒绝导出（E1），注入不会混进补丁。
**遗留问题**：`DIV-18` 保留并收窄为 RTL（`m16-chipyard-028`）/gem5（`m16-gem5-025`）：新 rc6 槽由各平台 oracle 先判，逐槽例外不能豁免，故这两方在补齐前红；QEMU 的 rc6 面已由本任务对齐。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 任务书要求「去掉 `switch_run_mode_write_ignored` 门控」，但该 flag 只服务 Tiny 的 `cg0–cg3 rc8`（`spec/Kaiwu §2` 测试机约定），与 `cg9 rc6` 无关；删它会回归 Tiny | ❌不修（口径披露） | 保留 flag 与 `rc == 8` 分支；仅改 `cg9 rc6` 的读写与进入模式 | 全仓 grep：该 flag 唯一使用点是 mode-row `rc == 8`；Tiny 的 `cfx_impl_mask` 无 cfx_hart（`dadao_async_enter()` 在 `a == NULL` 早退），`cg9 rc6` 读写与进入改动对 Tiny 不可达；QEMU Vast 38 case 全 PASS |
| hmon 体首次进 user 时程序挂死（0 槽）：镜像超页 PTE 的 U=0，user 取指/写签名不通过 | ✅已修 | `check_hart.py` 对 hmon 也传 `PTW_UMAP=1`；PTE 写移到 init 的 hypv 相位（supv 相位写 `cfx_ptw` ⇒ `CFXPERM`） | `arch-hart-001` 89 槽 PASS；注入 B 精确红在 slot 86 |
| 插入 4 个寄存器面槽后 handler 的 `slot` 基址 42 未改，`same(base+k)` 会指错槽 | ✅已修 | `expected()` H 分支基址 42 → 46，self-test 的逐槽 mutation 全 PASS | `check_cfx15.py --mode 3 --self-test` PASS（89 槽、每条可达 FAIL） |
| `async_jump` 尾段改成进 `rc6_setup` 会连带 U/S 体多录 5 槽 | ✅已修 | 用 `.if TMODE == 3` 门控跳转，并把 rc6 场景整块 `.if TMODE == 3` | `arch-hart-002` smon/umon 仍 40 槽 PASS |
| 探针/驱动登记的槽数（80、expected 80 个 1）未同步 | ✅已修 | `SIG_SLOTS`/`sig_bytes` 89、`expected.yaml` 89 个 1、两驱动 selfcheck want=89、README/arch.yaml 注记 | `run_arch --self-test` PASS；probe「（89 槽）」 |
| 注入 A 只改读回不足以覆盖「写不落地」 | ✅已修 | 注入同时把写分支改 no-op，读回恒 2 | 注入 A 红在 slot 18/19/20/84 |
| 证据脚本按 `--qemu` 相对路径跑 arch 驱动会 FileNotFound（驱动 `cd` 到 work-dir） | ✅已修 | `run.sh` 用 `$ROOT` 拼绝对路径 | 代表集 38 case PASS |
| 证据脚本首跑「oracle 槽数」期望写 10，实际含 phase1 的 `cg9 rc6` 读共 11 | ✅已修 | 槽名正则收紧为 `^(N) (cg9 rc6|async rc6=)`（10 条） | 重跑 26/26 PASS、EXIT=0 |
| `check-patch-tree` 总 rc=1（musl）是否本任务引入 | ❌不修（非本任务） | 不改 musl；qemu 段单独判 0 problem | 首跑（改前）即有同两条 musl assertion；qemu 段 0 problem、69 补丁 |

### 第 1 轮 reviewer 验收（2026-11-25，自跑不采信完成区）

**重跑记录（证据：仓库根执行运行期证据目录内的 `run.sh`）**
- 第 1 次完整重跑：**25/26，EXIT=1**——唯一红 `arch 代表集 qemu rc=75`，现场原文 `writer-guard: REFUSED: a writer is active for bootrom,llvm,qemu … target=install-host, pid=1239321`（他方会话抢共享安装根，非交付物缺陷）；其余 25 项 PASS。
- 第 2 次完整重跑（同脚本同参数）：**26/26，EXIT=0**；`build-qemu rc=0`、qemu md5 `8b49d6d9ea9c39dc2dffc1ca7d02739b`、`arch-hart-001` 89 槽、`arch-hart-002` smon/umon 各 40 槽、oracle 现场 89 行/10 rc6 行、patch-tree qemu 0 problem·69 补丁、changelog/knowledge-refs/run_arch self-test rc=0、`make_patch` 幂等 md5 不变、注入 A/B 各 `rc=1` 且命中、`cp`+md5 `ed9b853f…` 还原→重建→回绿、源树 0 dirty、补丁 md5 不变。
- 同命令代表集重试（第 1/3 次，环境干扰记次数）：`run_arch --level all` **rc=0、23 case PASS**；`--mode smon` rc=0 8 case、`--mode umon` rc=0 8 case ⇒ 现场合计 **39 PASS**。
- **独立注入（reviewer 自做，非脚本内）**：`cpu.c` 复位 `DADAO_MODE_SUPV → 0` ⇒ 重建 md5 `363c8e01…` ⇒ 探针 **rc=1，slot 17 `cg9 rc6 reset = 2` expected 2 / actual 0** ⇒ `cp` 还原 md5 回 `2c69ce45…`、源树 clean ⇒ 重建 md5 回 `8b49d6d9…` ⇒ 探针 **rc=0（89 槽）**。
- 附加门控：`make check-qemu-forms` rc=0；`idl/tools/idl_exec.py --self-test` **72/72 rc=0**（含 `async_switch_reset/write/entry/entry_uses_rc6`）；`check_cfx15.py --root . --mode 3 --self-test` rc=0（逐槽 mutation 全拒）。

**约束核验**
- **rc6 语义**：补丁与源树一致——读 `a->switch_run_mode & 0x3`、写 `val & 0x3` 落地、复位 `DADAO_MODE_SUPV`、进入 `env->inner_run_mode = a->switch_run_mode & 0x3`（无硬编码 2）；探针 17–21（复位/写 0/1/3/恢复）与 84–88（rc6=0/2 连续投递、`prev_run_mode` 证 0→user、2→supv）全 PASS。
- **`switch_run_mode_write_ignored` 保留成立**：全仓唯一使用点是补丁内 `rc == 8` 分支；`spec/Kaiwu §2` 明写 Tiny `switch_run_mode` 写忽略、读回保存值、异常进入强制 hypv（同步进入路径仍 `!user_mode ⇒ HYPV`）；HEAD（qemu-006）同在 `rc==8`，从未门控 rc6；Tiny `cfx_impl_mask = bit3|bit63` 无 cfx15，`dadao_async_enter()` 在 `a == NULL` 早退 ⇒ cg9 rc6 改动对 Tiny 不可达。删该 flag 会破 Tiny §2，保留正确（engineer 披露属实）。
- **探针/期望**：`arch-hart-001` 89 槽（`SIG_SLOTS`/`expected.yaml` 89 个 1/selfcheck want=89 一致），`arch-hart-002` 40 槽；期望由 `check_cfx15.py` 现场派生（模式表/符号），非同源自比。
- **DIV-18**：scope 收窄 `[chipyard, gem5]`、**未加 `slots` 例外**（该文件 `slots:` 仅 DIV-06 一条）⇒ RTL/gem5 在本组槽仍红；注入 A∪B 失败槽 `{18,19,20,84} ∪ {86}` = **恰 5 槽**，与「5 槽红、逐槽例外不可豁免」一致；`run_arch` 仅对 chipyard 侧吃 `slots` 登记，gem5 无豁免通道。
- **补丁/源树**：qemu 段 **0 assertion、69 补丁**；改动补丁 3 份（`cpu.c/cpu.h/helper.c`）；`make_patch` 幂等。总 rc=1 = musl 2 条（与**不含本任务**的主仓跑出的 musl 段 `diff` 为空，逐行相同）+ llvm 2 条（他方会话改共享源树 `DADAODisassembler.cpp`）⇒ 均非本任务。
- **构建/安装**：`build-qemu` rc=0、md5 `8b49d6d9…`；**安装根 qemu md5 同为 `8b49d6d9…`**，writer 日志无本任务 cwd 的 install 记录 ⇒ 完成区「未 install-host」属实、产物已由他方 `install-host` 落盘；现 writers 无活动写锁（窗口空闲）。证据脚本 `--qemu` 指构建树**等价**（install 即构建树原子拷贝，两侧 md5 相等）。
- **快照对账**：审查前后 `git status -uall` 均 16 行逐行相同、目标文件 md5 相同；**未提交 git**；注入用 `cp`+md5 还原（未用 checkout/restore）。

**发现（文档级，不阻断，交 architect 收尾订正）**：① 完成区「代表集 38 case」与现场 39（23+8+8）不符；② 完成区注入 A「slot 18-20/84」实跑另有 slot 86；③ 任务书「去掉 `switch_run_mode_write_ignored` 门控」与代码不符（该 flag 只在 `rc==8`），engineer 保留+披露正确，建议措辞订正；④ 完成区「总 rc=1 仅 musl」已因他方会话改共享源树过期（现为 llvm+musl 各 2 条）。

**判决：Accepted**（验收口径在自跑重跑下全部达成、硬约束无违反；证据脚本 26 条断言均有可达 FAIL，注入→FAIL→还原→回绿由 reviewer 亲跑证实）。
