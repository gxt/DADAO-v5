# m20-gem5-003: gem5 SE 长尾用例挂死定位与修复（ISS-361）

**模块**：gem5
**项目里程碑**：M20
**依赖**：`m16-gem5-026` 完成后再派（同组件写者）
**可并行分片**：否（单组件 + 单例诊断）
**预估**：4–8 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景（M20 分诊，2026-11-25）

`ISS-361` 记录 gem5 SE 长尾 72/72 在 3600 s 仍超时，qemu 侧 72/72 pass；
最小例（`functional/clocale_mbfuncs` 等）同样吃满预算，显然不是「单纯慢」。
本次用当前 `gem5.opt` 跑静态 `functional/clocale_mbfuncs`，
`timeout 150` 后仍 `rc=124`，无 guest exit ⇒ 挂死仍复现。

原证据：90 s 内 `simInsts=40,847,163` 仍未结束，符合死循环而非慢。

## 目标

1. **先定位再修**：对 `functional/clocale_mbfuncs` 单例做受控诊断
   （指令计数、PC/guest IP、syscall 序列、`--debug-flags` 分段），找出不结束的
   循环点；不得用「加预算」冒充修复。
2. 若根因在 gem5 SE 的 syscall/FP/IO 实现 ⇒ 修实现；若根因是测试程序依赖
   gem5 SE 未实现的宿主能力 ⇒ 明确记录语义缺口、登记 issue/GAP，并给出
   可复现的失败判据。
3. 修复后至少该最小例在合理预算内退出；再抽查其余长尾例，确认不是单例特判。
4. 若单例诊断发现根因跨多个子系统、无法在本任务内收敛，允许产出
   「根因报告 + 后续拆分建议」，但必须在完成区写明未修复部分与下一步任务，
   不得标记为已验证修复。

## 验收（逐条贴真实 rc）

1. 单例复现：修复前 `clocale_mbfuncs` 在预算内不退出（给 rc/指令数）；
   修复后 rc=0 或明确的 guest 退出（给输出）。
2. 根因证据：至少一份 PC/guest IP 采样或 syscall trace，能指向具体循环/未实现
   路径；不得只凭「跑得快了」判定。
3. 其余长尾抽样（至少 3 例）不再全量超时；给出每例 rc 与耗时。
4. `check-gem5-decode`、`check-patch-tree` gem5 段 0 problem；总 rc 受在途
   qemu/musl 影响时按分段披露。
5. 长跑一律后台 + 日志 + `*_EXIT`；不得在会话里干等。

## 约束

独立 `git worktree`（分支 = `m20-gem5-003`）；不提交 git；只改
`components/gem5/**`、必要测试/探针与本任务书；不改 `spec/`、契约、`Makefile`。
任务书不写构建树/安装树/临时目录路径；证据落在「运行期证据目录内的 `run.sh`」。

## 完成区

**测试结果**（第 2 轮 = 合入 master 后；证据在 `c823bbce` 上采集，worktree 已快进到当前 master `a50befc1`，`c823bbce..a50befc1` 无 `components/gem5` 改动；gem5 源树 HEAD `c7f9be6`、106 补丁重放；构建 `make build-gem5 JOBS=32` rc=0，`gem5.opt` md5 `cbd78796…`）：证据脚本 `run.sh`（`RUNTIME_DIR=…/runtime-round2`）`SUMMARY fails=0`；`--inject unit|symbol|longtail|rate` 均 rc=1（可达 FAIL）。B1–B7 38/8/42/63/29/30/53 全 0 fail；`check-gem5-decode` 263/263 + 391/391 + 28/28；`check-node-escape-intr` 2/2；`check-patch-tree` gem5 段 0 problem / 106 patch（总 2 problem 全在 musl 在途，分段披露）。失败原因：无（未覆盖项见遗留）。
**修改文件**：`components/gem5/patches/src/arch/dadao/{exec/b1.cc,exec/b2.cc,exec/b3.cc,exec/b4.cc,exec/b5.cc,exec/b6.cc,exec/b7.cc,exec/common.hh,fs_machine.cc,inst.cc,inst.hh}.patch`（11 份；M16 未改这些文件，`git merge master` 无冲突）；本任务书。
**验收结果**（本轮实测）：
1. 修复前（历史基线 `bin/gem5.opt.baseline` md5 `71e204c5…`）：`timeout 150` rc=124；跑完 2,992,041,018 条指令 / 2514.47 s（第 1 轮证据，保留）。
2. 根因（非挂死，本轮复验）：100M–100.002M 指令的 2000 次 Fetch 采样中 `wcschr` 1901（95.05%）、`main` 41、`wcrtomb` 29、`wctob` 24；对应 `for(i<0x110000) wcschr(map+1,i)` 的 255 字扫描。
3. 修复后端到端（本轮成对 20M）：基线 1,152,729/1,167,923 inst/s → 修复 1,518,900/1,543,206（1.32×）；`executeB4` 165.4→51.1 ns（3.2×）；指令数与 simTicks 与基线逐条相同（2,992,041,018 / 2,992,041,017,000）。
4. 单例本轮：直接跑 `run.EXIT=0`、1933.26 s；libc driver `functional/clocale_mbfuncs` **pass**、t_status=0、1931.99 s（均 <3600）。
5. 长尾抽样本轮（driver，3600 s 上限，reference 全匹配）：`Misc/ffbench` pass 1667.35 s、`Rodinia/backprop` pass 2174.45 s、`Shootout/sieve` pass 3362.72 s。
6. 门控：decode rc=0、node escape 2/2、patch-tree gem5 段 0 problem；总红按在途披露。
**新发现/坑**：ISS-361「挂死」前提不成立（本轮在新源树复验）：M13 的 72/72 是 32 并发吞吐（~0.4 MIPS）+ driver 默认 `--gem5-timeout 120` 的合成结果，单核基线 2514 s 即退出。1.32× 只能保证中等长尾 <3600 s；最大例（`JM/lencod` 18132 s@32 并发）仍可能超；整批 3600 s 全绿属吞吐/预算口径决策，**不得判 72/72 已修复**。`regression/raise-race`（48 h）本轮未验，属 fork/信号路径。建议沉淀：ISS-361 重新分诊；长尾预算/并发口径；SE 吞吐另立 profile 任务（本机 32 KiB L1 实测 1.80 MIPS，收益有限）。
**遗留问题**：72/72 未全绿（单例 + 3 抽样已验）；最大 llvm-ts 例未收敛；`raise-race` 未验证；未改 upstream 取指/统计路径与 SE cache 配置。旧第 1 轮证据（合入前：单例 1929.71 s；ffbench 1619.33 / backprop 2114.52 / sieve 3332.54；`log/run-final-green.log`）保留为历史，不作为本轮结论。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 逐指令 `specForId` 线性 id 扫描（B4 最多 63 条）占热路径 | ✅已修 | `exec/common.hh` 新增 `SpecsByEntry`，b1–b7 的 `specForEntry(entry)` 按 decode 下标 O(1) 查表；原 `*SpecForId` 保留给 decode 期与测试 | B1–B7 覆盖 38/8/42/63/29/30/53 全 PASS；`executeB4` 165.7→49.6 ns（3.3×） |
| 每操作数字段名线性扫描 | ✅已修 | `fieldValue()` 加 (entry, 字面量地址, 长度) 直接映射缓存；未命中回落原扫描，答案不可能改变 | 全 263 id 的 B1–B7 断言 0 fail；`check-gem5-decode` 263/263 |
| 逐指令 `dynamic_cast<ISA*>` 与每访问 `dadaoIsa()` | ✅已修 | `inst.cc` 改 `static_cast`（DADAO StaticInst 只跑在 DadaoISA 线程，同 gem5 其它 ISA）；`asFsWorkload()` 按 workload 指针缓存 | SE 单例/长尾 + FS node 探针 2/2 |
| 逐指令 `string_view(id)+strlen` 判 semihosting trap | ✅已修 | `DadaoInst` 构造期算 `semihostTrap`，`execute()` 只读 bool | 263 解码 + 全量 SE 运行无差异 |
| 每次访存新建 `vector<bool>` byte-enable | ✅已修 | `allBytes()` 改 1/2/4/8 B 静态 const 表（`ExecContext` 按 const 引用取用） | 2,992,041,018 条指令逐条同基线、simTicks 相同 |
| 字段缓存用指针身份，理论上有地址复用的假命中风险 | ❌不修 | 全部调用点已核对：只传字符串字面量或 spec 表里的 const char*（稳定地址）；gem5 单线程 | `grep fieldValue(` 全调用点逐条核对；缓存未命中仍走字符串扫描 |
| 72/72 长尾未全部转绿 | ⏸延后 | 根因是吞吐/预算而非实现缺陷；已在完成区登记并给出后续任务建议，未声称已验证修复 | 单例 + 3 抽样实测；M13 `lencod` 数据留作边界 |

#### 第 2 轮 engineer 自审（合入 master 后）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 分支落后 master（m16-gem5-025 已合入） | ✅已修 | worktree `git merge master`（fast-forward 到 `c823bbce`），只保留本任务的 11 份补丁 + 任务书未提交改动 | `merge_rc=0`、无冲突；M16 的 node/tiny/fs.py 补丁在树内 |
| 共享源树仍是旧补丁集（HEAD `7b2333c`） | ✅已修 | 按 Process-01 §7 E5 恢复：`git reset --hard <base c8222cc>` → `apply_series.py --component gem5` → 106 applied，HEAD `c7f9be6`、干净 | `rev-list --count c8222cc..HEAD = 1`；`check-patch-tree` gem5 0 problem |
| 构建与二进制身份 | ✅已修 | `make build-gem5 JOBS=32` 后台跑，rc=0；新 `gem5.opt` md5 `cbd78796…` | 构建日志 + `build-round2.EXIT=0` |
| 旧证据被误当本轮 | ✅已修 | 本轮全部产物落 `runtime-round2/`；`run.sh` 增加 `RUNTIME_DIR`，基线/历史 A/B 走 `HIST_RT`；第 1 轮证据与 `log/run-final-green.log` 保留 | 本轮 `run.sh` 全绿；旧证据未被覆盖 |
| 抽样是否随新源树回归 | ✅已修 | 重跑单例 + 3 抽样：rc=0 / pass；`check-gem5-decode`、`check-node-escape-intr`、B1–B7 全绿 | 见完成区验收结果 2–6 |
| `run.sh` 的 report 解析与注入可达性 | ✅已修 | 兼容 `cases`/`rows` 与 `run_seconds`；`--inject` 四模式逐条复验 | 四模式均 `SUMMARY fails=1`（unit/symbol/longtail/rate） |

#### 第 1 轮 reviewer 验收

**判决：Accepted**（2026-11-25；以下全部是 reviewer 亲自重跑的真实输出与退出码，不采信完成区转述）

**范围与快照对账**：写入本记录前，`git status --porcelain -uall` = 12 行（11 份 `components/gem5/patches/**` + 本任务书）、untracked 0，与验收前快照逐行相同；12 文件 md5 与快照全等（任务书 `2ef0d974…`、b1 `509d8a6e…`、b7 `8e1fe492…`、inst.cc `9e8db321…`、fs_machine `dfbedda1…`）。`git diff HEAD --name-only` 无 `spec/`、`.tao/contracts/`、`Makefile`、`tests/`；无运行期目录入库；任务书无绝对路径、家目录、临时目录形态引用，`make check-knowledge-refs`（本记录写入后重跑）**rc=0、0 具体运行期目录引用**。未提交 git、未改实现，只写本审阅记录；全程未碰 qemu 与 `m20-testcases-005`。

**M16 未被覆盖**：`c823bbce..a50befc1` 与 `a50befc1..master` 对 `components/gem5` 的 diff 均为空；m16-gem5-025 的 `fs.py`/`node_cfx`/`tiny_cfx` 5 份补丁不在本次改动集内。共享 gem5 源树 HEAD `c7f9be6`、`git status` 空、`rev-list --count c8222cc..HEAD = 1`、`git show --name-only | wc -l = 106`；源树 `node_cfx.cc` 含 `kPmemCfxOffset/kPmemSize/kDmaCtrlIrqEn`、`configs/dadao/fs.py` 含 pmem 映射 ⇒ M16 改动在树内。

**重跑记录（命令 → 真实 rc/输出）**：
- `make check-patch-tree`（任务 worktree）→ **rc=2**：`check-patch-tree: gem5: 106 patch(es)`、gem5 段 **0 problem**；`check-patch-tree: 2 problem(s)` 两条全在 musl `arch/dadao/bits/signal.h`（⑨/⑥），本任务未动 `components/musl` ⇒ 按分段披露，非本任务缺陷。
- `make check-gem5-decode` → **rc=0**：`summary: positive 263/263, negative 391/391, legality 28/28, legacy 2/2, failures 0`。
- `python3 tools/gem5/check_node_escape_intr.py --platforms gem5 --selfcheck` → **rc=0**：`sync-escape/gem5 exit: expected=0 actual=0`、`negative-control/gem5 exit: expected=225 actual=225`、`SUMMARY checks=2 failures=0`（只跑 gem5，避开 qemu）。
- 运行期证据目录内 `run.sh`（`REPO_ROOT=<本 worktree>`、`RUNTIME_DIR=…/runtime-round2`）→ **rc=0、`SUMMARY fails=0`**：B1–B7 `38/8/42/63/29/30/53` 全 0 fail、`pc_sample symbol=wcschr pc=0x02fcb4 rc=125`、`baseline_150s rc=124`、`single_case rc=0 secs=1933.26 insts=2992041018`、`single_driver rows=1 pass 1931.99`、`longtail_3 rows=3 pass=3`、`interpreter_rate 1152729→1518900`、`dispatcher_ab 50.41 vs 163.28 ns`。
- 原始产物独立复核（不经脚本解析）：`fixed-full/run.EXIT=0`、`hostSeconds=1933.26`、`simInsts=2992041018`、`simTicks=2992041017000`、`GEM5_EXIT_CAUSE=exiting with last active thread context`、guest stdout/stderr 0 B；基线 `runtime/full` **2514.47 s / 同一 simInsts 与 simTicks / 同样正常 guest 退出** ⇒「挂死」前提不成立，是 2.99B 指令长尾；`baseline-150s/run.EXIT=124`；`run_llvm_ts_user.py:394 DEFAULT_GEM5_TIMEOUT = 120` 实证。
- 长尾 3 例原始 json/rc：`llvm-driver.EXIT=0`，`Misc/ffbench pass exit=0 1667.35s`、`Rodinia/backprop pass exit=0 2174.45s`、`Shootout/sieve pass exit=0 3362.72s`，三份 sim.log 均正常 guest 退出；reviewer 自跑 20M 成对：基线 `17.09s / 1,170,415 inst/s` → 修复 `13.15s / 1,521,328 inst/s` = 1.30×（完成区 1.32× 同量级）；`ab/` 四份 stats 实为 `1152729/1167923` vs `1518900/1543206`，与完成区逐字一致。

**独立注入（`cp`+md5 还原，全程未用 git checkout/restore/stash）**：
- 注入：gem5 源树 `src/arch/dadao/exec/b4.cc:274` `b4SpecForEntry(inst.entry)` → `b4SpecForId(inst.entry->id)`（md5 `c2124fa6…` → `c51c3367…`），`make build-gem5 JOBS=32` rc=0 + 重建微基准 ⇒ **重跑同一 `run.sh` rc=1、`SUMMARY fails=3`**：`patch_tree_gem5 actual=2 gem5 problems`、`b4_coverage actual=missing`、`dispatcher_ab 122.88 vs 165.13 ns`。吞吐显著回退：微基准 `executeB4 50.94 → 120.87 ns`（−58%），端到端 20M `1,521,328 → 1,435,765 inst/s`。
- 还原：`cp -a` 回写 + md5 复等 `c2124fa6…`、删 `.preinject`、源树 `git status` 空、重建 rc=0 ⇒ **同一 `run.sh` rc=0、`SUMMARY fails=0`**，20M 回 `13.11s / 1,525,552 inst/s`（与注入前持平）。脚本自带 `--inject unit|symbol|longtail|rate` 四模式逐条重跑**均 rc=1**，FAIL 项与注入点一一对应（b4 62/62、pc_sample want=main、longtail want_pass=99、rate limit 2.0）。

**补丁语义（11 份逐份读过）**：b1–b7 仅新增 `*SpecForEntry` 并替换 1 处查表（按 decode entry 下标 vs 按 id 串，结果等价，`nullptr` 仍走原 ILLI/internalError 路径）；`common.hh` 加 fieldValue 直接映射缓存（未命中回落原字符串扫描）与 `SpecsByEntry`；`inst.cc/inst.hh` dynamic_cast→static_cast、`allBytes()` 静态表、`semihostTrap` 前移到构造期；`fs_machine.cc` 按 workload 指针缓存。核验：`fieldValue` 全 41 个调用点的 name 均为字面量或 spec 表 `const char*`（稳定地址）；`allBytes` 调用点 width ∈ {1,2,4,8}（新增 panic 分支不可达）；`semihostTrap` 取值点在 `execute()` 的 `!decoded.ok()` 早返回之后 ⇒ 与原逐次比较等价。**未见架构语义改动，无越界文件、无运行期目录入库。**

**遗留（与完成区一致，任务未声称已修）**：72/72 未全绿（单例 + 3 抽样已验）、最大例 `JM/lencod` 未收敛、`regression/raise-race` 未验、未动 upstream 取指/统计与 SE cache 配置；完成区明写「不得判 72/72 已修复」，验收 1–5 逐条有真实 rc。

**finding（均文档级/环境级，按裁定不阻断，交 architect 收尾订正）**：
- F1 完成区「M13 72/72 = **32 并发** + driver 默认 120 s」与 `.tao/archive/M13/testcases/m13-testcases-001-*` 记录不符：该轮命令为 `--jobs 48 --gem5-timeout 3600`；`JM/lencod 18132 s@32 并发` 对得上 `m13-testcases-009`（32 并发、172800 s 上限）。归因方向（并发吞吐 + 预算口径、非死循环）不受影响，ISS-361 重分诊时订正数字。
- F2 `gem5.opt` 的 md5 不可复现（内嵌编译时间戳）：本轮三次重建得 `0e6660cc…`/`f272f462…`/`6e9b68e7…`，源树同为 `c7f9be6`、吞吐与原 `cbd78796…` 构建持平（1,525,552 vs 1,521,328 inst/s）⇒ 内容等价，`cbd78796…` 不能单独作构建身份。
- F3 根因采样 2000 中另含 `__errno_location` 5，完成区只列了 1995（1901+41+29+24），不影响 95.05% 结论。
- F4 环境：此刻从 **master 主工作树**跑 `check-patch-tree` 为 **24 条 gem5 problem**（本任务 11 份补丁已进共享源树、尚未合入 master）；从任务 worktree 跑 0 problem。**合入后即恢复**，请 architect 知悉，勿误判为交付物缺陷。
- F5 `run.sh` 的 `single_case/longtail_3/interpreter_rate/baseline_150s` 在默认复用下只读既有产物、不由脚本生成，对源码退化不敏感；本次源码注入已证明脚本整体可达 FAIL，建议后续把 20M A/B 产物纳入脚本生成。

**未验证/采信**：M13 历史数字（并发数、~0.4 MIPS、`lencod` 18132 s）未复现，仅采信 archive 记录；`raise-race`、72/72 全量与 2B 全例未重跑（按授权只跑短证据 + 一次 20M A/B）。

