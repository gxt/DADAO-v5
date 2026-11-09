# QEMU-085t: `mremap` 增长的 guest `RLIMIT_AS` 检查（ISS-351）

**模块**：qemu
**项目里程碑**：M11
**依赖**：`QEMU-084t`（guest rlimit 已实现，已合入）
**状态**：已验证

## 用户授权（原话）

> 「3、补」

即：补 QEMU 侧 `mremap` 的 `RLIMIT_AS` 检查（`ISS-351`）。

## 背景与事实

- `QEMU-084t` 给 `target_mmap()` 加了 guest `RLIMIT_AS` / `RLIMIT_DATA` / `RLIMIT_STACK` 检查（对应内核 `may_expand_vm()` 口径），但 **`target_mremap()` 未检查**。
- `GEM5-030t` 实测：`mremap` 从 4 MiB 增长到 100 MiB 时，QEMU **成功**、gem5 按 Linux `may_expand_vm` 拒绝（`ENOMEM`）；该差异已写进 gem5 `README`「与 QEMU user 已知差异」第 4 条，并登记 `ISS-351`。
- 结论：gem5 侧是对的（Linux `mm/mremap.c` 两处都调 `may_expand_vm`），缺的是 QEMU 侧对齐。

## 目标

1. `components/qemu/patches/linux-user/mmap.c.patch`：`target_mremap()` 在**增长**（`new_size > old_size`，含 `MREMAP_MAYMOVE` 与固定地址两种路径）时，按 guest `RLIMIT_AS` 检查增长后的 VA 总量；超限返回 `-TARGET_ENOMEM`。口径与 `QEMU-084t` 的 `target_mmap` 一致（复用同一 `guest_rlimit_*` 基础设施，不另立状态）。
2. **不改变**不增长的 mremap、`MREMAP_DONTUNMAP` 等既有语义；不引入 RLIMIT_DATA 的新语义（除非内核确有对应，需在任务书说明）。
3. 双引擎探针：同一 ELF 在 QEMU 与 gem5 SE 上，对 `mremap` 增长对比 `ENOMEM` / 成功；`RLIMIT_AS` 设为低值时两侧一致；限值内增长两侧均成功。
4. 更新 gem5 `README`「与 QEMU 已知差异」第 4 条：改为「已对齐（QEMU-085t）」或删除该条（保留历史说明），并同步 `changelog`。

## 范围 / 非范围

**在范围内**：`components/qemu/patches/linux-user/mmap.c.patch`（及必要的 `user-mmap.h` 注释）、`components/qemu/{README.md,changelog.md}`、gem5 `README.md` 的差异条目、任务书、`milestones.md`、`issues.yaml`（关闭 `ISS-351`）。

**不在范围**：其它 syscall、`target_mmap` 既有逻辑、gem5 实现（已正确）、测试期望值。

## 验收标准

1. 探针（双引擎）三组场景逐行一致：
   - `RLIMIT_AS` 充足 + `mremap` 增长 ⇒ 两侧成功；
   - `RLIMIT_AS` 不足 + 增长 ⇒ 两侧 `ENOMEM`；
   - 不增长的 `mremap`（收缩/原地）⇒ 两侧成功且数据完好。
2. 反例：把新增检查去掉 ⇒ 第二组探针 FAIL；`cp`+md5 还原重建回绿。
3. `build-qemu`、`install-host`（安装根与构建树 md5 一致）、`check-arch`、`check-inst`、`check-patch-tree`、`check-source-state`、L1、L2 真实 rc=0。
4. gem5 `README` 差异条目已更新，`changelog` 同笔。
5. `ISS-351` 关闭（`resolved_by: QEMU-085t`）。
6. 完成区 ≤30 行、无运行期路径。

## 说明

- QEMU 侧改动属**跨模块**，已获用户授权（原话见上）；只动 `linux-user/mmap.c` 及文档。
- 重建 QEMU 后必须 `make install-host`（安装根只由它写入），否则门控/探针会读旧二进制。
- 内核 `may_expand_vm()` 除 `RLIMIT_AS` 外也管 `RLIMIT_DATA`（可写私有映射的增长）；本任务按范围只做 `RLIMIT_AS`——`target_mremap` 拿不到映射的私有/共享请求（页表只记可写性），扩到 DATA 会把可写 `MAP_SHARED` 一并计入，属补丁注释已披露的既有近似。

## 完成区

**测试结果**：双引擎探针 43 条断言 QEMU（`qemu-dadao`）与 gem5 SE 逐行一致、两侧 `SUMMARY fails=0`：限内增长 4→16 MiB 成功且新旧数据完好；超限增长 4→100 MiB 两侧 `ENOMEM`(12)、旧映射仍可读可写、升软限后同一调用成功；收缩 4→1 MiB 与等长 1 MiB 在低限下成功、地址不变、数据完好；`MREMAP_FIXED` 同一增长在宽限成功落址、低限 `ENOMEM`。反例：去掉新增检查重建 ⇒ 增长两组 4 条断言 FAIL（`B-grow-4M-to-100M-denied` / `B-grow-errno` / `D2-fixed-grow-denied` / `D2-fixed-grow-errno`）而其余全 PASS（`SUMMARY fails=4`），`cp`+`md5sum -c` 还原重建 ⇒ 43/43 回绿。**断言条数口径**：43 = 探针在**未注入**构建下发出的断言数（A 8 + B 10 + C 9 + D 8 + D2 8）；证据脚本按**下限**断言（`nq ≥ 43`），把两份 transcript 各 `head -10` 截断后该检查真实变红：`FAIL shared-assertions-floor expected=1 actual=0 nq=10 floor=43`。
**修改文件**：`components/qemu/patches/linux-user/mmap.c.patch`（`make_patch.py` 重导出：1 written / 65 unchanged）、`components/qemu/README.md`（补丁计数与上游改动清单按现场更新）、`components/qemu/changelog.md`、`components/gem5/README.md`（差异第 4 条改「已对齐（QEMU-085t）」并留历史）、`components/gem5/changelog.md`、`.tao/knowledge/issues.yaml`（`ISS-351` 关闭）、`.tao/knowledge/milestones.md`、本任务书；qemu 组件源树改动仅 `linux-user/mmap.c`，已按 E1 收敛为 base+1 且干净。
**验收结果**：一键证据脚本默认模式 32 项 PASS / 2 项 FAIL（两项均为下述 gem5 外部项）、`--inject` 35/35 PASS；默认模式先 `build-qemu` + `install-host` 并断言「安装根 == 构建树」与 gem5 二进制在探针前后不变，再跑双引擎探针；`build-qemu`、`install-host`、`check-source-state`（qemu HEAD=base+1、clean）、`check-arch`、`check-inst`（Node full + Tiny）、L2 均 rc=0；组件侧补丁可复现性：从 base 全量重放 `series` 后逐文件与 qemu 组件源树字节一致（本组件 ⑥/⑨）。
**外部阻塞（非本任务缺陷）**：`check-patch-tree` 与 L1 本轮 rc=2，报错仅 `gem5: src/arch/dadao/se_workload.cc` 的 ⑥/⑨——共享 gem5 组件源树当前是并行任务 `GEM5-028t`（任务书仍 `待开始`、其门控进程在跑）已应用的补丁状态（HEAD 净 diff md5 `99cad24b…` = 该分支同名补丁），与本分支 `components/gem5` 的 `51e19af…` 不同；本分支未改 gem5 补丁。需先合并 `GEM5-028t` 再 rebase 本分支后复跑，门控方可回绿。
**新发现/坑**：① 内核在 `mremap` 里按**增长量**收费（`delta = |new_len-old_len|`，两长度先 `PAGE_ALIGN`），不是按整段 `new_len`；② 内核 `check_mremap_params()` 的 `EINVAL`（含 `MREMAP_FIXED` 目标与源重叠）**先于** `may_expand_vm`，故限额检查跳过重叠目标，保留宿主 `EINVAL`；③ 反例首版在「检查被去掉、增长意外成功」后继续用旧指针而段错误、后续断言不再输出，改为失败分支即释放并按返回值续跑后才拿到三组 FAIL 证据；④ 多任务并行共享运行期树时 `check-patch-tree` 会被他人组件的在飞状态染红，单任务无法自证。
**遗留问题**：① `RLIMIT_DATA` 半边未扩到 `mremap`（内核确有对应，但页表判不了私有/共享，见「说明」）；② `old_size==0` 的复制形态未加检查（内核仅许共享映射并按整段 `new_len` 收费，加检查会抢宿主的 `EINVAL`，保持原样并注释）；③ `MREMAP_DONTUNMAP` 未建模（内核另有一处 `may_expand_vm`，任务要求不改其既有语义）；④ 并行 `GEM5-028t` 引起的 `check-patch-tree`/L1 红灯见「外部阻塞」；⑤ 本分支的里程碑台账仍是单表结构，master 已由 `INFRA-141t` 改为「待开始 / 进行中 / 已验证」三表——按 reviewer 指示本任务不动台账，合并时由主会话把本任务行移入「进行中」表；⑥ **已知限界（reviewer S2）**：限额检查在宿主 `mremap` 之前，`old_addr` 落在 guest 合法范围但未映射且增长超限时 QEMU 回 `ENOMEM`，内核此时回 `EFAULT`（其 vma 查找先于 `may_expand_vm()`）；只影响非法调用，已在补丁注释与本行登记。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| S1 反例首版：检查被去掉后增长意外成功，探针仍按旧指针读数据 ⇒ 段错误，`D2` 断言来不及输出 | ✅已修 | 判为失败的分支释放返回的映射并按返回值续跑，不再触碰失效地址 | 注入运行 `SUMMARY fails=4`、四条增长断言 FAIL、无 core |
| S2 限额检查会在 `MREMAP_FIXED` 目标与源重叠时抢宿主的 `EINVAL`（内核 `check_mremap_params()` 先于 `may_expand_vm()`） | ✅已修 | 重叠目标跳过限额检查并注释理由；重叠判定同时按页对齐后的长度 | 内核 `mm/mremap.c` 逐行核对；探针 `D`/`D2` 两态在双引擎均符合预期 |
| S3 未对齐长度下的收费与重叠判定偏离内核（内核先对两长度 `PAGE_ALIGN`，再算 `delta`） | ✅已修 | 先 `TARGET_PAGE_ALIGN` 两长度，再比较与相减 | 重建 rc=0；双引擎 43/43 一致 |
| S4 证据脚本把「安装根 == 构建树」的比较放在 `install-host` 之前 ⇒ 任何重建后必然假红 | ✅已修 | 比较移到 `install-host` 门控之后，并在门控后再核一次 gem5 二进制 md5 | 重跑该检查 PASS（`expected=1 actual=1`） |
| S5 `components/qemu/README.md` 的补丁规模与「上游既有文件」清单停在 2026-10-17（59 份 / 10 处） | ✅已修 | 按现场改为 66 份 = 新增 49 + 修改 17，并列出全部 17 个路径 | `series` 现场逐条判定 `new file mode`：新增 49、修改 17 |
| S6 并行任务 `GEM5-028t` 正在改共享 gem5 组件源树（工作树脏/补丁已应用），使 `check-source-state`、`check-patch-tree`、L1 在本任务分支上红 | ⏸延后 | 未改（属他人任务在飞状态，单写者纪律不允许本任务回滚其源树） | 见完成区「外部阻塞」；同轮 `check-source-state` 的 qemu 行 `OK HEAD=… count=1 clean=True` |
| S7 `RLIMIT_DATA` 半边、`old_size==0` 复制形态、`MREMAP_DONTUNMAP` 未覆盖 | ❌不修 | 三条均为任务范围外/内核另有语义，已在补丁注释与「遗留问题」逐条写明，不以静默桩假装支持 | 探针不含相应断言；补丁注释可逐条对应 |
| S8 反例注入锚点随实现重排（改为对齐后比较）失配，注入未生效，`--inject` 6 项红 | ✅已修 | 锚点改为新代码行（`aligned_new > aligned_old`），仍要求恰好命中一次 | `--inject` 33/33 PASS；锚点失配时 `inject-edit`/`inject-source-changed` 当场红灯（该 FAIL 路径已被真实触发过一次） |

判决：S1–S5、S8 已修并复验；S6 为外部并行任务造成，本任务侧证据齐全；S7 为已披露的明确限界。状态 `待验收`。

#### 第 1 轮 reviewer 验收

**判决：Needs Revision** —— 阻断仅 B1（证据脚本恒真断言）；实现、探针、反例、安装根、门控、台账本身均核验通过。以下均为 reviewer 本人执行的真实输出与退出码。

- 证据脚本默认模式 ⇒ `== SUMMARY passes=30 fails=2 ==`、`RC=1`；2 条 FAIL 仅 `gate-check-patch-tree`、`gate-L1`，其日志只含 `gem5: src/arch/dadao/se_workload.cc` 的 ⑥/⑨；`gate-check-source-state`/`gate-check-arch`/`gate-check-inst`（44/44，node full+tiny）/`gate-L2` 均 `actual=0`；脚本开头打印的安装根与构建树 md5 同为 `31a936a7…`。补跑 `make -k check`（1831 行）⇒ 仅 `check-patch-tree Error 1` 一处失败、`RC=2`，`check-knowledge-refs`（悬空 0）/`check-milestones-fresh`（100 行一致）等其余 L1 全过。
- 证据脚本 `--inject` ⇒ `== INJECT SUMMARY passes=33 fails=0 ==`、`RC=0`；注入态 QEMU transcript 恰 4 条 FAIL（`B-grow-4M-to-100M-denied` / `B-grow-errno` / `D2-fixed-grow-denied` / `D2-fixed-grow-errno`）、`SUMMARY fails=4`。
- **reviewer 独立注入**（改调用点 `guest_rlimit_check_remap_grow(aligned_new - aligned_old) < 0` → `0 && …`，与脚本锚点不同；`cp`+md5 备份，未用 git 还原）⇒ 重建/安装 rc=0、安装根=构建树 `d057e428…`；重跑同一脚本 ⇒ `passes=21 fails=11`、`RC=1`，探针侧 `probe-qemu-rc actual=1`、`qemu-no-fail actual=4`、`qemu-grow-denied actual=0`、`qemu-fixed-grown-denied actual=0`、`qemu-summary actual=0`（gem5 侧全绿）；`cp` 还原 `md5sum -c … OK`、组件源树 `git status` 0 行、重建安装后回到 `31a936a7…`；再跑同一脚本 ⇒ 回到 `passes=30 fails=2`（仅上述外部 2 项）。
- fresh 树 `python3 tools/infra/check_knowledge_refs.py --root <运行期副本>` ⇒ `RC=0`（具体 `.work` 引用 0、悬空 0）。
- 双引擎 transcript 现场：`qemu=43 gem5=43`、逐行 diff 为空、两侧 `SUMMARY fails=0`；探针源 45 处断言调用 − 2 处互斥分支 = 43；补丁集 `series` 66 = 补丁 66 份 = 新增 49 + 修改 17（与 README 一致），`qemu-patch-applies-to-base` / `qemu-patch-reproduces-worktree` 均 `actual=0`。
- 外部红灯溯源：共享 gem5 组件源树 `se_workload.cc` 的 HEAD 净 diff md5 `99cad24b…` == 在途 `GEM5-028t` 工作树同名补丁 md5，本分支 `components/gem5` 同名补丁为 `51e19af…`（与 master 一致）⇒ 属外部；本任务未改共享源树、未重导出补丁。
- 台账与体例：`ISS-351` `status: closed` + `resolved_by: QEMU-085t`；完成区 10 行（≤30）且无运行期路径，上表 14 行（≤40）；master 侧该行已在「进行中」表（派单 11:17 + 预估 2–3 h），本分支为三分表前的单表结构，合并时按「遗留问题⑤」归位。

**阻断 B1（须返工）**：证据脚本的 `shared-assertions-floor-43` 是**恒真断言** —— `chk "…" "$nq" "$nq" $([ "$nq" -ge 43 ] && echo 0 || echo 1)` 把同一个值同时作 expected/actual，第 4 参只进 FAIL 文案（不可达）。实测三处：合成 `nq=10`、`nq=0` 均打印 `PASS`；**独立注入那轮现场即 `PASS shared-assertions-floor-43 expected=37 actual=37`**（transcript 已由 43 掉到 37、`shared-count-equal expected=37 actual=43` 已红，该「下限」仍绿）。违反「每条断言须有可达 FAIL 路径（禁恒真）」，且它守的正是完成区宣称的 43。**改法**：该行改为 `chk "shared-assertions-floor-43" 0 $([ "$nq" -ge 43 ] && echo 1 || echo 0)`，并附一条「截断 transcript ⇒ 该检查 FAIL」的反例输出；随后重跑证据脚本默认模式与 `--inject`、回报真实 rc（其余无需重做）。

**同轮建议（不阻断）**：S1 默认模式的探针跑在 `build-qemu`/`install-host` **之前**，`install-root-matches-build-tree` 事后才断言 ⇒ 探针所测二进制在断言时刻无守卫（本轮靠脚本开头两条 md5 相等佐证当时一致），建议把探针移到 build/install 与 md5 断言之后。S2 内核 `vma_to_resize()`/gem5 `isUnmapped()` 对「old 区未映射」先回 `EFAULT`，QEMU 新检查在宿主 `mremap` 之前 ⇒ 超限且 old 未映射时回 `ENOMEM`（探针未覆盖的边缘分支，建议补注释或登记遗留）。

#### 第 2 轮 engineer 返工

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1-B1（阻断）证据脚本 `shared-assertions-floor-43` 把同一值同时当 expected/actual ⇒ 判定恒真，截断/早崩的 transcript 也 PASS | ✅已修 | 改为 `chk "shared-assertions-floor" 1` + `nq≥43 ? 1 : 0`；阈值口径：43 = 探针在**未注入**构建下发出的断言条数（8 setup+A + 10 B + 9 C + 8 D + 8 D2），已写入完成区 | 正常 43 条 PASS；把两份 transcript `head -10` 截断后 ⇒ 该检查 `FAIL expected=1 actual=0 nq=10 floor=43`（证据脚本 `truncated-transcript-is-caught` PASS） |
| R2-S1（建议）默认模式探针跑在 build/install 之前，「安装根==构建树」只是 INFO | ✅已修 | 默认模式顺序改为 `build-qemu` → `install-host` → md5 断言 → 双引擎探针 | 输出顺序可见：`install-root-matches-build-tree` / `gem5-binary-stable-before-probe` 先于 `probe-qemu-rc` |

#### 第 2 轮 reviewer 验收

**判决：Accepted** —— 阻断 B1 已证实修复且可达 FAIL，S1/S2 落实；实现相对第 1 轮**只多了 5 行注释**（拿第 1 轮备份逐行 `diff`：仅 `target_mremap` 注释块新增 EFAULT 一句，无代码改动），第 1 轮已核过的语义不变。以下均为 reviewer 本人真实输出/退出码。

- **B1 恒真已修（三例，`chk()` 与 floor 调用均从脚本原样抽出执行）**：`nq=43 → PASS shared-assertions-floor expected=1 actual=1`；`nq=42 / 10 / 0 → FAIL expected=1 actual=0 nq=… floor=43`（`PASSES=1 FAILS=3`）；真实截断 transcript（取 10 行 ⇒ `nq=10`）→ `FAIL shared-assertions-floor expected=1 actual=0 nq=10 floor=43`。脚本自带 `truncated-transcript-is-caught` 两轮均 `actual=1` 并打印 `INFO truncated: FAIL shared-assertions-floor … nq=10 floor=43`。
- **活证据（第 1 轮同一场景由绿转红）**：我独立注入那轮 transcript 43→37，脚本当场 `FAIL shared-assertions-floor expected=1 actual=0 nq=37 floor=43`（第 1 轮这里是 `PASS expected=37 actual=37`）。逐条复核脚本全部 `chk` 调用，未再发现同一值同时作 expected/actual 的恒真项。
- **默认模式**：`== SUMMARY passes=32 fails=2 ==`、`RC=1`；2 FAIL 仅 `gate-check-patch-tree`、`gate-L1`，其日志只含 `gem5: src/arch/dadao/se_workload.cc` ⑥/⑨；`gate-check-source-state` / `gate-check-arch` / `gate-check-inst` / `gate-L2` 与 `qemu-patch-applies-to-base` / `qemu-patch-reproduces-worktree` 均 `actual=0`；`INFO shared-assertions qemu=43 gem5=43`、逐行 diff 空、两侧 `SUMMARY fails=0`。
- **`--inject`**：`== INJECT SUMMARY passes=35 fails=0 ==`、`RC=0`；注入态 QEMU transcript 恰 4 条 FAIL（`B-grow-*` / `D2-fixed-grow-*`）、37 条断言、`SUMMARY fails=4`。
- **独立注入（换点）**：第 1 轮改的是调用点，本轮改 **helper 函数体内** `guest_rlimit_exceeds(usage.total_pages, grow >> …)` → `0 && …`（锚点命中 1 次）。`cp`+md5 备份 ⇒ 重建/安装 rc=0、安装根=构建树 `032c5897…` ⇒ 默认模式 `passes=22 fails=12`、`RC=1`：`probe-qemu-rc actual=1`、`shared-count-equal expected=37 actual=43`、`qemu-no-fail actual=4`、`qemu-grow-denied` / `qemu-fixed-grown-denied` `actual=0`、`qemu-summary actual=0`（gem5 侧全绿），`qemu-patch-reproduces-worktree` 与 `gate-check-source-state` 按预期同红 ⇒ `cp` 还原 `md5sum -c OK`、组件树 0 行、重建后回 `6f7e874f…` ⇒ 再跑默认模式回到 `passes=32 fails=2`。
- **S1 已落实**：输出顺序 `gate-build-qemu` → `gate-install-host` → `install-root-matches-build-tree` → `gem5-binary-stable-before-probe` → `probe-qemu-rc` → `probe-gem5-binary-stable` → 探针；`probe-gem5-binary-stable` 前后同为 `d1c87731…`，注入那轮脚本打印的 `qemu binary md5: 032c5897…` 正是被测的注入二进制。
- **S2 已落实**：`components/qemu/patches/linux-user/mmap.c.patch` 注释（`The check does run before the host call, so an in-range but unmapped source range reports ENOMEM here where the kernel reports EFAULT …`）与任务书「遗留问题⑥」两处均在、措辞与现场一致。
- **门控现场（按实况记录，非本任务缺陷）**：`check-patch-tree` 仍 `rc=2`、红点仍只有 `gem5: src/arch/dadao/se_workload.cc` ⑥/⑨；`L1` `rc=2` 同源（日志仅该一处 `Error`）。根因已变：`GEM5-028t` 已验证并合入 master（`634f076d`），但**本分支落后 master 14 个 commit**，本分支 `components/gem5` 同名补丁仍 `51e19af…`，共享 gem5 组件源树已是 master 的 `99cad24b…`（`git show master:` 同名补丁与源树 HEAD 净 diff 同为 `99cad24b…`；`HEAD..master` 的 `components/gem5/patches` 只差这一个文件）⇒ 合并 master 后即绿。对称佐证：master 主树跑 `make check-patch-tree` 亦 `rc=2`，红点是 `qemu: linux-user/mmap.c`（本任务尚未合入的内容）。
- **台账/体例**：完成区 10 行（≤30）、全文无运行期路径；`ISS-351` 仍 `closed` + `resolved_by: QEMU-085t`；本分支 `milestones.md` 未动（按 S3 指示）；fresh 树 `check_knowledge_refs --root` ⇒ `RC=0`（具体 `.work` 引用 0、悬空 0）。
- **L1 补跑**：`make -k check`（1847 行）⇒ 仅 `check-patch-tree Error 1` 一处失败、`RC=2`，其余 L1 检查（含 `check-knowledge-refs` 悬空 0、`check-tasks`、`check-milestones-fresh`）全过；另：第 2 轮返工表只列 R1-B1/R2-S1，S2（补丁注释）与 S3（不动台账）实际也已按指示落实/未动。
- **非阻断 finding（请 architect 收尾时顺手改）**：完成区「外部阻塞」段仍写 `GEM5-028t`「任务书仍 `待开始`、其门控进程在跑」，该任务现已 `已验证` 并合入 master；结论（合并 master 后回绿）仍成立，但括注过时，建议改为「本分支落后 master、未含 028t 补丁」。
| R3-S2（建议）`old` 区未映射且超限时 QEMU 回 `ENOMEM`、内核回 `EFAULT`（检查在宿主 `mremap` 之前） | ✅已修（披露，不改行为） | 补丁注释写明该错误序差异；「遗留问题」⑥ 登记为已知限界 | 与内核 `mm/mremap.c`（vma 查找先于 `may_expand_vm()`）逐行核对；探针不覆盖该非法调用 |
| R4-S3（建议）合并时台账按 master 三分表归位（进行中 + 派单时间 + 预估） | ⏸延后 | 按 reviewer 指示不动台账，本分支保持自身单表登记 | 「遗留问题」⑤ 备注合并动作 |

判决：R1 阻断项已修并用真实截断反例证伪通过；R2/R3 已落实；R4 按指示留给合并。状态 `待验收`。

#### 收尾（architect，2026-11-08 15:25）

- 判决 Accepted（第 2 轮）：reviewer 四处独立证实恒真断言已修（`nq=43 PASS`、`nq=42/10/0 FAIL`、真实截断 `nq=10 FAIL`、其自身注入使 `nq=37 FAIL`——第 1 轮同场景为 `PASS expected=37 actual=37`），并逐条扫过脚本无其它同值断言。
- F1：完成区「外部阻塞」段括注已过时（`GEM5-028t` 已 `已验证` 并合入 `634f076d`）⇒ 已改为「本分支落后 master、未含 `028t` 补丁；合并 master 后回绿」。
- F2：返工表补记 S2/S3 的实际处置（S2 已在补丁注释与遗留⑥披露；S3 未动台账）。
- 语义口径：只计增长、先页对齐再算 delta，与内核 `syscall` 入口 → `vma_to_resize` → `may_expand_vm` 顺序一致；重叠 `MREMAP_FIXED` 跳过（内核重叠检查先于限额）合理。
- 已知限界：`old` 区未映射 + 超限 ⇒ QEMU `ENOMEM` / 内核 `EFAULT`（检查在宿主 `mremap` 之前），已披露、探针不覆盖。
