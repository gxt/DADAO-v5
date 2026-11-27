# m16-gem5-023: `cache-model=off` 下 cfx5 存在但 no-op

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-021`/`022` 已合入；`m16-spec-002`（CACHE-27 补维度）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-22 已定）

Linux 内核缺省带 cache 维护逻辑，不能为“无 cache”单独编译内核。因此 `cache-model=off` 时 cfx5 必须**存在但 no-op**（`cache_exist=0`，命令被接受、不报 `CFXREG`、不产生效果），而不是 021 现在的“cfx5 不在 `kCfxhaMap` ⇒ `CFXREG`”。

## 要做

1. **cfx5 存在**：`node_cfx.cc` 的 `kCfxhaMap` 加入 cfx5（或在 `CfxhaCache` 路径单独处理），使 `cfx2rd`/`cfx2rc` 在 `exist=0` 时仍可访问寄存器，不报 `CFXREG`。
2. **off no-op**：`exist=0` 时 `cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size` 可读写（或按契约），`cache_ctrl` 合法编码被接受但不发维护、不产生效果；非法编码仍按契约报 `CFXREG`。
3. **on 不变**：`exist=0b11` 时按 021 的 D/I 维护语义执行（clean/invalidate/flush、范围/使能/异常）。
4. **契约对齐**：按 `m16-spec-002` 更新后的 CACHE-27 实现，不自行扩语义。

## 不做

- 不改 021 的 D/I 维护实现（只改 off 的存在/门控）；
- 不改 QEMU/RTL；
- 不升契约版本号。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py gem5` 幂等；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. `cache-model=off`：`cache_exist=0`；读/写 cfx5 寄存器不报 `CFXREG`；`cache_ctrl` 合法编码 no-op；非法编码仍 `CFXREG`；
2. `cache-model=on`：021 的 D/I 语义（A–F 0x10）不回归；
3. `off` 下 01 册 38/38、vast 10/10；
4. **可达 FAIL**：注入「off 下 cfx5 仍 `CFXREG`」⇒ 判据红；注入「off 下命令真发维护」⇒ 统计/行为红；`cp`+md5 还原并重建后回绿；
5. `check-gem5-decode`、`check-patch-tree` gem5 段、`check-index-blobs`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` → **17/17 PASS（EXIT=0）**；`run.sh --inject all` → **37/37 PASS（EXIT=0）**。`off`（Vast，无 `--caches`）：自检向量逐检查点全绿（guest rc 0x10）——0x0101 起 `cache_exist` 读 0 且**不报 `CFXREG`**、0x0102/0x0104 `cache_enable` 复位/写 0b11 后均读回 0、0x0105/0x0106 `addr_start` 只留 `PA[55:0]`/`addr_size` 往返、0x0107 读 `rc9`（只写）仍 `CFXREG`、0x0108 写 `cache_exist`（RO）仍 `CFXREG`；0x0201–0x0209 五条合法命令（D/I 单行、`all`、两侧）被接受（无异常）、数据全保留（store 后 `D|invalidate`/`D|flush` 单行读回仍是新值）、命令后 `cache_exist` 仍 0；0x0301/0x0302 **非法编码仍 `CFXREG`**（`[3:2]=11`、`PA 区间` 且 `size=0`），0x0303/0x0304 的 `sel=00`/`op=none` 不检查不报，0x0305 寄存器面未被非法命令改动；`stats.txt` 无任何 `system.cpu.[id]cache.*`（off 机器根本没有 L1 对象）。`on`（`--caches`）不回归：021 的 A–F 向量 guest rc 0x10，dcache demand hits/misses `clean=686/20`、`invalidate=685/21`、`flush=685/21`；同一 off 向量在 `on` 下按设计红在 0x0101（`cache_exist=0b11`），说明 off 断言在 on 机器上不空转。`off` 回归：01 册 **38/38**（0 FAIL 行，三平台逐字节）、`run_m5_e2e --profile vast` **10/10**。三路注入（`cp`+md5 还原、无 git checkout/restore/stash，每路「变更→重建 114 s→判红→还原→重建→回绿」各约 5 min）：① `offcfxreg`（恢复 021 的 `exist != 0` 前置）→ 红 **0x0101**；② `offmaint`（`exist` 归零 + 去掉 no-op 门与 enable 门，配 `--caches` 观测）→ 红 **0x0203**（脏行被丢弃，数据不再保留），无注入时同一 hybrid 运行红在 0x0101（对照）；③ `offnoenc`（把 no-op 门移到 CACHE-14 校验之前）→ 红 **0x0301**（非法编码未报 `CFXREG`）。三路还原后 md5 均回到 `a2ebcd8d…`，off/on 均回 0x10。
**修改文件**：组件源 5 个：`src/arch/dadao/node_cfx.cc`（寄存器面无条件解码 + CACHE-14 之后 `exist==0` 早返回）、`node_cfx.hh`、`isa.hh`、`isa.cc`、`configs/dadao/fs.py`（后四个只改口径注释）；`components/gem5/patches/` 对应 5 份补丁（`make_patch.py gem5` 首跑 `5 written, 101 unchanged`，重跑 `0 written, 106 unchanged`）；`components/gem5/changelog.md`（M16 追加一条）；本任务书；运行期证据（`run.sh` + `cfx5_off_noop.s` + 021 逐字的 `cfx5_main.s`/`cfx5_drop.s`，md5 记录在输出里，gitignored）。
**验收结果**（真实 rc）：`check-gem5-decode` 0；`check-tasks` 0；`check-index-blobs` 0；`check-component-changelog` 0；`check-patch-tree` **gem5 段 0 problem**（整树 rc=2，24 条断言全在既有段：musl 10 / qemu 10 / chipyard 4，非本任务文件）；`make_patch.py gem5` 0（幂等）；`check_patch_tree.py --source-state` gem5 `OK HEAD=38df3bd count=1 clean=True`。环境 Linux 6.8.0-149 x86_64 / nproc=64；`gem5.opt` 首建 **142 s**、每次注入/还原重建 **114 s**（6 次实测 116–117 s 相邻间隔）；Vast BootROM md5 `d5571847…`。未改 `src/mem/cache/**`、`src/cpu/**`、QEMU/RTL、`spec/`/契约版本，未提交 git。
**新发现/坑**：① 纯 `cache-model=off` 机器**没有任何 L1 对象**，「off 下命令真发维护」在行为上不可观测 ⇒ 该路 FAIL 只能造一个「有观测硬件、但 cfx5 报 off」的配置（注入把 `exist` 归零 + `--caches`），脚本已把这一步写成注释并加「无注入时该 hybrid 必须红」的对照，避免把造出来的配置当成真实维度。② 契约 `CACHE-27` 的 `cache-model` 维度已由 `m16-spec-002` 合入（`f7ed832c`），实现按任务书口径 + 用户 2026-11-22 补充裁定（非法编码仍 `CFXREG`）落地；契约合入后需复核措辞。③ 共享运行期产物两类竞态：他会话重建 Chipyard Tiny sim 时路径短暂缺失（01 册 rc=2），`/tmp` 一度写满使 `check-gem5-decode` 与 `check-patch-tree`（`git read-tree` rc=128）双红 —— 均非本改动，重试后转绿，旧日志留作 attempt 证据。④ 自检向量头部注释的检查点区间在跑批后订正为 `0x0201–0x0209`（`@@` 注释，重建出的 bin md5 仍 `486789f7…`，与跑批所用二进制相同；跑批日志里打印的是订正前的 `.s` md5）。
**遗留问题**：① `cfx5` 仍不进 `kCfxhaMap`（021 遗留 ③）⇒ `trap`/`escape cfx5` 与 cfx 两轴权限未接，本任务「不做」范围内不动；② 未跑 L2 `check-modules`（会装共享安装根、并行任务窗口内禁跑，期间另有会话在跑 `check-arch`），留 `/complete`；③ `m16-testcases-009` 可把 `cfx5_off_noop.s` 收编进 `tests/arch/cache/`（off 维度的 gem5 载体）；④ 无周期判据（任务书「不做」）。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（本深度无嵌套子代理）：`cacheRegRead`/`cacheRegWrite` 去掉 `exist` 前置后**仍**保留「rc 之外一律 `CFXREG`」（CACHE-04）；`cacheControlExec` 的判序（CACHE-11/12/13/14 → `exist==0` 早返回 → 逐侧 enable 门 → 维护），确认 off 下非法编码在早返回**之前**就报；`exist` 在 off 下的其它消费点（`nodeFlushDAtHandoff` 的 bit1 早退、`cache_enable` 的 `& exist` 掩码）逐处核过；`on` 路径是否逐字节不变（`exist=0b11` 时早返回不触发）；证据脚本的注入构造、md5 还原与「假绿」可能（hybrid 对照断言、`stats.txt` 无 cache 对象、off 向量在 on 下必须红）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `offmaint` 注入的替换串缺尾部换行，注释与 `auto *isa` 拼行 ⇒ 编译失败、该路注入误判 | ✅已修 | 替换串补 `\n` | 修前 `rebuild after offmaint rc=1`（`‘isa’ was not declared`）→ 修后重建 0、红 0x0203 |
| F2 `offmaint` 首版同时去掉 `cache_enable` 的 `exist` 掩码 ⇒ 红在 0x0104（寄存器读回），不是「真发维护」的行为红 | ✅已修 | 掩码保留（只加注释标记），只去掉 no-op 门与两侧 enable 门 | 红检查点由 0x104 改为 **0x0203**（脏行被丢弃）；`on` 还原后仍 0x10 |
| F3 「off 下真发维护」在纯 off 配置不可观测（无 L1 对象） | ❌不修（无更优构造） | 脚本改成带注释的 hybrid 构造 + 「无注入时 hybrid 必须红 0x0101」对照 | `offmaint control` PASS |
| F4 01 册首跑 rc=2（`chipyard 不存在`）：他会话正在重建共享 Tiny sim | ✅已修（脚本） | 仅在日志命中该缺失时等待 sim 出现并**重试一次**，两次日志都留盘 | 重试后 38/38；attempt1 日志保留 |
| F5 基线二跑双红：`/tmp` 写满（`No space left on device`）+ `check-patch-tree` 的 `git read-tree` rc=128 | ✅已修（环境） | 未改代码；隔离旧日志为 `base-run.diskfull-attempt.log`，重跑 | `check-gem5-decode` rc=0、patch-tree gem5 段 0 problem；基线 17/17 |
| F6 off 下 `cache_exist` 读 0 但寄存器仍可访问 ⇒ 需确认没有别处把 `exist==0` 当「cfx5 不存在」 | ✅核过（无需改） | — | `nodeFlushDAtHandoff` bit1 早退、`enable & exist` 掩码；off 向量 0x0101–0x0108 全绿 |
| F7 `check-patch-tree` 整树 rc=2 的 24 条断言是否含本任务文件 | ❌非本任务 | — | 逐行统计：musl 10 / qemu 10 / chipyard 4，gem5 段 0 |
| F8 未跑 L2 `check-modules` | ⏸延后 | — | 并行窗口内会装共享安装根（`AGENTS.md §4`），留 `/complete` |

**约束核验**：改动集 = 组件源 5 + 补丁 5 + `changelog.md` + 本任务书（证据在运行期证据目录，gitignored）；`src/mem/cache/**`、`src/cpu/**`、QEMU/RTL、`spec/`/契约未改；未提交 git；术语「寄存器组」；组件源 `base..HEAD == 1` 且工作树干净；补丁/源码无 `INJECT` 残留。
**判决**：**待验收**（F1/F2/F4/F5 已修，F3/F6/F7/F8 有处置或为口径并已披露）。

### 第 1 轮 reviewer 验收（2026-11-22）

**重跑**（仓库根执行运行期证据目录内的 `run.sh`，本人执行、不采信完成区）：
- `run.sh` → `SUMMARY: pass=17 fail=0 inject=none`、`EXIT=0`（首跑 + 两轮还原后各 1 次，共 3 次同值；BootROM md5 `d5571847…`、off 向量 md5 `fd0bba1c…` / bin `486789f7…`）
- `run.sh --inject all` → `SUMMARY: pass=37 fail=0 inject=all`、`EXIT=0`（offcfxreg 红 0x0101、offmaint 红 0x0203 且无注入对照红 0x0101、offnoenc 红 0x0301；三路还原 md5 均 `a2ebcd8d…` 并回绿）
- off：`cache_exist`=0 无 `CFXREG`、`cache_enable` 读回 0、`addr_start`/`addr_size` 往返、`rc9` 只写 `CFXREG`、写 `cache_exist` `CFXREG`、5 条合法命令接受且数据保留、0x0301/0x0302 非法编码仍 `CFXREG`、`stats` 0 条 cache 对象
- on：A–F guest rc 0x10；dcache `clean=686/20`、`invalidate=685/21`、`flush=685/21`；off 向量在 on 下红 0x0101（反空转）
- off 回归：01 册 38/38 无 FAIL、`run_m5_e2e --profile vast` 10/10；静态门控 decode/tasks/index-blobs/changelog 全 rc=0、`make_patch.py gem5` `0 written`、`check-patch-tree` gem5 段 0 problem（整树 rc=2）

**独立注入**（自写变异 + `cp`+md5 + `build_gem5.py --jobs 32` 重建 + 重跑同一 `run.sh`，无 git checkout/restore/stash）：
- 路① `REVIEWER-INJECT-R1`（`nodeCfxRead` 的 `CfxhaCache` 分支加 `exist != 0`）→ `rc=1`、`pass=14 fail=3`，行为红 = off 向量 guest rc=257(0x0101)；另 2 条 FAIL 系源树变脏（patch-tree gem5 2 problems、make_patch 拒绝导出 rc=1），非交付物缺陷；还原 md5 `a2ebcd8d…` 相等 → `rc=0`、17/17
- 路② `REVIEWER-INJECT-R2`（CACHE-14 两条校验在 `exist==0` 时放行）→ `rc=1`、`pass=14 fail=3`，行为红 = guest rc=769(0x0301)；还原 md5 相等 → `rc=0`、17/17；收尾 `grep REVIEWER-INJECT` 于组件源与补丁 = 0

**补丁核验**：5 份补丁与 `git diff c8222cc HEAD` 逐字 MATCH；`make_patch.py gem5` 幂等；`check-patch-tree` gem5 段 0 problem；组件源树干净、`base..HEAD=1`（106 文件）；`git status` 快照前后逐行相同（7 文件，与完成区声明一致）。

**CACHE-27 一致性**：对 master 已合入的 `m16-spec-002` 文本逐条比对——off「五寄存器可达、其余 rc 仍 `CFXREG`、`cache_exist` 读 0、`enable` 写 1 读回 0、`ctrl`(WO) 与 addr 可访问、合法命令不报异常不维护、编码与 `addr_size` 校验不受维度影响仍 `CFXREG`」与实现判序（CACHE-11/12/13/14 → `exist==0` 早返回 → enable 门 → 维护）逐条一致；on `exist=0b11` 一致；与已合入的 `m16-qemu-001` 同口径。本 worktree 分支点早于合入，任务书内契约副本无该维度属预期。

**遗留①判定（不阻断 023，必须登记后续任务）**：`cfx5` 不进 `kCfxhaMap` ⇒ `trap cfx5`→`CFXREG`、`escape cfx5` 恒 `CFXESC`、cg0–cg3 两轴权限/委派行不可达。与本任务口径**不冲突**——用户 2026-11-22 口径限定「寄存器面 + 命令面存在但 no-op」，该缺口 on/off 两态同在、021 已作设计取舍并披露，023 未引入也未扩大 on 态行为。
- 但契约侧 `contract-see §3`（Vast 实现 cfx5、每个 cfx 提供 cg0–cg7）与 `contract-cache CACHE-26`（`cfx_cache` 自身只报 `CFXTRAP`/`CFXESC`）要求 trap/escape 与两轴权限 ⇒ 现实现属**合约一致性缺口**。请架构师裁定：另立任务接线（gem5，必要时连同 QEMU/RTL 三方）或由 spec 明确豁免；**不得随 023 关闭丢失**。

**Finding（均文档级、不阻断）**：F1 完成区「整树 22 条断言（qemu 8）」与实测不符——本轮三次跑 22/24/24，收尾 `gate-patch-tree.log` 为 24 条（qemu 10 / musl 10 / chipyard 4），gem5 段恒 0，判据不受影响；F2 证据头注释 `A 0x0101..0x0107` 实为 `…0x0108`，且「contract entry still pending in m16-spec-002」已过期（`f7ed832c` 已合入）；F3 完成区新发现②「m16-spec-002 仍待开始」已过期；F4 `discussing.md` 仍写「失败则立 `m16-gem5-023` 改取指侧模型」，与本任务同号不同事（队列文档，交架构师）。

**约束核验**：独立 worktree、未提交 git；未改 `src/mem/cache/**`、`src/cpu/**`、QEMU/RTL、`spec/`、契约版本号；术语「寄存器组」、任务书与本记录无运行期路径；证据脚本三路注入均有可达 FAIL（off 向量在 on 下必红、offmaint 无注入对照必红），无恒真、无两支同果。
**判决：Accepted** —— 验收命令块在 reviewer 自己的重跑下全部通过、两路独立注入均「红 → `cp`+md5 还原 → 重建回绿」、约束无违反；F1–F4 记文档级 finding、遗留①须登记后续任务，最终接受由架构师定。


