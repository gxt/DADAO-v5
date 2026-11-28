# m18-linux-031: supv 返回路径的出口意图重写（ISS-m18-014，029 的对称缺口）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-029`（umon 侧已修，`ISS-m18-011` 闭合）
**可并行分片**：否（改 `components/linux`）
**预估**：1–2 h（同档单点修复中位 86 min；本任务只加与 029 同口径的四字重写 + 回归）
**档位**：中改（trap 出口意图）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`，本 worktree 自建）

## 背景

`m18-linux-029` 查明：`cfx_umon cg5` 是**单帧**共享出口意图，umon 返回路径只重写 `rc10`；C 半睡眠时另一任务的 `dadao_enter_user()`（supv→user）会把 `rc8/rc9/rc11` 覆盖成 supv/smon 掩码，恢复的任务 `escape cfx_umon` 便回到 **supv** 执行用户代码、并用陈旧向量进用户（`ISS-m18-011`）。修法是 `DADAO_UMON_USER_EXIT_INTENT` 在 `escape` 前重写全部四字。

`cfx_smon cg5` 的 supv 返回路径（`DADAO_TRAP_RESTORE_AND_ESCAPE` + `escape cfx_smon`）结构相同、同样只重写 `rc10` ⇒ 存在**同类覆盖**风险（`ISS-m18-014`）。本轮未观测到签名，不等于不存在。

## 目标

1. 按 029 的口径，在 supv 返回路径 `escape` 前重写 `rc8=supv`、`rc9=cfx_smon`、`rc10=任务帧 ip`、`rc11=现场 smon 掩码`（掩码取值须与进入时语义一致，不得放宽屏蔽）。
2. **不得**改变同步异常语义（`escape cfx_smon` 的返回点、`rc11` 整字写目标行）。
3. 若发现 smon 侧另有独立缺陷 ⇒ 记录并停下写「待裁定」，不顺手扩围。

## 验收（逐条贴真实 rc）

1. 静态：`trap.S` 的 supv 返回路径 `escape` 前四字重写齐全；补丁与源树逐行一致。
2. **可达 FAIL**：① 回退该重写 ⇒ 构造「C 半睡眠 + 另一任务 enter_user」场景下必须红（可用 029 的探针思路构造；若无签名则须给“为何不可达”的论证与频率上界）；② 只删 `rc8` 写 ⇒ 红。
3. 不回归：K2 170/170、K5 285/285、K6 82/82、`run_suite.py --suite ltp` 两轮逐例一致、`amb_window_probe` 14/14、`--soak 300 --soak-strict` 窗口 0；`m18-linux-029` 的忙等探针 0/≥20。
4. 门控：`check-patch-tree` linux 段 0、`check-config-pins`、`check-component-changelog`、`check-knowledge-refs`。
5. 闭合 `ISS-m18-014`（`resolved_by` 指本任务）；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`；每次跑次独立目录。
2. 只动：`components/linux/patches/**`、`components/linux/changelog.md`、`tests/unit/linux/**`、`tools/linux/**`、`.tao/knowledge/issues-m18.yaml`、本任务书。
3. 构建 `JOBS=32`；QEMU 本 worktree 自建（记 md5）；不覆盖共享安装根；低频签名单独计数（`ISS-m18-005/006`）。
4. 组件补丁经 `make_patch.py linux` 重导；还原 `cp`+md5；还原后重建。

## 待裁定

无。

## 完成区

**测试结果**：P13 探针 **26/26**（base + 5 注入 + 还原回绿）；K2 **170/170**、K5 **285/285**、K6 **82/82**；LTP 两轮 **14/14 PASS、逐例 verdict 一致**（各 20/20 checks，`qemu_cmd` 同一自建 QEMU）；`amb_window_probe` **14/14**；`--soak 300 --soak-strict` **窗口 0/300、静默自旋 0**；029 忙等探针 **20/20**（`M18A_SPIN=20000000`、`M18A_NTHREADS=4`，即 029 run.sh 口径）。QEMU 本 worktree 自建 `c2b4b2f78738ba0865beed2abf830bf0`（11.1.1），证据脚本固定。
**修改文件**：`components/linux/patches/arch/dadao/kernel/trap.S.patch`、`components/linux/changelog.md`、`tests/unit/linux/m18_supv_exit_intent_probe.py`（新）、`tests/unit/linux/m18_supv_exit_intent_probe_kernel.patch`（新，仅证据期 K2 P13 镜像）、`.tao/knowledge/issues-m18.yaml`、本任务书。
**验收结果**：`escape cfx_smon` 前四字重写：`rc8=supv`、`rc9=入口记录 prev cfx`（入口存 callee-saved `rb33`）、`rc10=frame.ip(+4 on SKIP)`、`rc11=现场 cfx_smon cg15 rc3`。可达 FAIL（P13 handler 内按另一任务入口写 rc8=user/rc9=保留 cfx/rc10=landing/rc11=0）：base `P13 PASS mask=0xffff… hits=1`；回退整段 ⇒ `die mode=2 code=0x82`（CFXESC）；删 rc8 ⇒ `USER-MODE escaped …`（rc 0xed）；删 rc9 ⇒ `0x82`；删 rc10 ⇒ K1 PTW 探针撞命中上限 `0xf`；删 rc11 ⇒ `P13 FAIL mask expected=0xffff… got=0x0`（rc 0xef）；每次 `cp`+md5 还原（trap.S `ef5bdc99…`）后重建回绿。静态：`check-patch-tree` **12 组 464 patches 0 problem**（`--source-state linux` HEAD=f279e3b7a322 count=1 clean）、`check-config-pins` 109/109、changelog/knowledge-refs/check_issues rc=0。源树按私有树重放（`private_source.sh linux m18-linux-031`，105 applied）；`trap.S` md5 `ef5bdc99…` 与旧路径一致、补丁 md5 `acda4b54…`，故未重跑全部旧门控，但上列门控均在私有树上重跑。
**新发现/坑**：① 硬编码 `rc9=cfx_smon` **改变同步语义**：post-syscall 内核缺页/`FROM_USER` 交接的 prev cfx 是 `cfx_umon`，返回后 current cfx 变 smon，用户入口下一条 `trap cfx_umon` 被其 supv cfxtrap 掩码拒绝（`0xffff…7ff2` bit2=1）⇒ K5 S 组停在首个 fill-file 超时；必须用入口记录值（`rb33`）。② 本 QEMU 上先写 rc10 再写 rc8/9/11 会丢掉刚写的 rc10（删 rc10 注入实测退回硬件值并自旋），故 **rc10 最后写**。③ `cp -p` 还原保留旧 mtime，Kbuild 不重编 ⇒ “还原后回绿”会静默测到注入镜像；还原后 `touch`（脚本已处理，首轮曾误判）。④ 029 忙等探针的证据口径是 `SPIN=20M`；默认 400M 会暴露 011 族残余，即使在 029-only 内核上也 5/6 红（非本任务引入，勿用 400M 判 0/20）。⑤ 派单称基线含 028/029/030，实测 master `cc63098d` 一个都未合；已本地 merge 030→029→master 构造对称基线（见遗留）。⑥ K5/K6/amb 不接 `--qemu`，本 worktree 用**局部 `.dadao` overlay**（cross-toolchain/bin 软链共享工具、仅 `qemu-system-dadao` 指向自建；gate.lock/writers 仍软链共享）让它们解析到同一 QEMU；证据复现需保留该 overlay。⑦ `amb_window_probe` 的 scratch 硬编码 `/tmp/opencode/m18-linux-026/check-linux-amb`，并发会话会碰撞；本证据串行执行。
**遗留问题**：① 本分支含 030/029 的 prerequisite merge commits（非本任务内容）；`trap.S.patch` 内容 = master(029+030)+031，architect 合并 029 后按协调通知重导即可，勿文本合并整文件补丁。② 400M 忙等变体的 011 族残余仍见（029-only 亦复现），未在本任务扩围；若 reviewer 要求 400M，先与 029 口径对齐。③ 无其它未完成项。④（reviewer F1）证据 preflight 的 md5 与 HEAD 差 3 行注释（029 第 3 轮注释订正后补同步），汇编等价；完成区已按 HEAD 重跑全绿。⑤（reviewer F3）P13 六轮原始 console 未归档（`mkdtemp` 不清理、判据只在内存），后续同类任务按 029 教训按跑次归档。⑥（reviewer F2 处置）本 worktree 共享源树在 12:08 前被写过（新规之前），故不带 `DADAO_SOURCE_ROOT` 时 patch-tree 有 linux 2 problem + qemu 2 条基线；本任务验收以私有树为准，合并后 master 侧按 `replay_source.sh` 重放即可。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`trap.S` 的 supv 入口/出口（`rb33` 保存、四字重写、rc10 顺序）、`m18_supv_exit_intent_probe.py`（P13 注入/还原）、`m18_supv_exit_intent_probe_kernel.patch`（仅证据镜像）、changelog/issues/任务书。逐条核对：`rb33` 在 capture 之后写、C 半 callee-saved、restore 从帧恢复；`rc9` 取入口记录而非硬编码；`rc11` 现场读；`rc10` 最后写且 SKIP 加 4；P13 的五路注入各有独立终态；`cp`+md5+touch 还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书要求 `rc9=cfx_smon` 硬编码，但 post-syscall 内核缺页/`FROM_USER` 的 prev cfx 是 `cfx_umon`；硬编码后用户入口 `trap cfx_umon` 被 cfx_umon 的 supv cfxtrap 掩码（bit2=1）拒绝 | ✅已修 | 入口 `cfx2rd cfx_smon cg5 rc1` 存 `rb33`（callee-saved）；出口 `rb2rd rd2, rb33, 1` 写 rc9 | 硬编码版 K5 S 组停在首个 fill-file 超时（rc=124）；改 prev cfx 后 K5 **285/285**、K6 82/82 |
| F2 先写 rc10 再写 rc8/9/11 时，删 rc10 注入实测退回硬件值（K1 PTW 自旋 0xf），clobber 的 rc10 未生效 | ✅已修 | rc10 移到四字最后写（frame.ip/+4） | P13 base PASS；删 rc10 ⇒ 0xf（K1 命中上限），证明 rc10 写是唯一返回地址来源 |
| F3 `cp -p` 还原保留旧 mtime，Kbuild 复用注入镜像，首轮“还原回绿”实为假绿 | ✅已修 | `restore()`/finally 还原后 `os.utime` | 首轮 `--inject all` 末尾 base 假红（mask=0），touch 后 26/26 全绿 |
| F4 P13 是**对抗性 clobber**（rc8=user/rc9=保留 cfx/rc11=0），非某个真实入口的逐字快照 | ✅声明 | 文档写明它是“任意陈旧四字都不得被采信”的充分触发；真实入口的逐字值见 F5 | 五路注入均有独立终态；真实忙等 20/20 |
| F5 真实「C 半睡眠 + 另一任务 supv 入口」窗：写 `cfx_smon cg5` 的只有另一任务的 delegate（四字与本任务 delegate 相同 ⇒ 无害）或内核态 supv 缺页（rc10 不同 ⇒ 危险）；后者要求 A 在 `mmap_read_lock`/`GFP_KERNEL` 上睡眠，2 GiB 无竞争时内核不可抢占、tick 不切任务 | ⏸论证+上界 | 未构造出真实签名；P13 提供确定性充分触发 | 029 忙等 20/20；LTP 两轮 14/14；030 的 140 启忙等 0 次 014；合并样本 188 启 0 ⇒ 95% 上界 ≈3/188≈1.6%/启（受 workload 限定的频率上界，不是不可达证明） |
| F6 基线不含 028/029/030（派单称含），无法跑 029 探针/030 帧 | ✅处置 | 本地 merge 030→029→master 构造对称基线；私有树重放 | `check-patch-tree` 464/0；trap.S 同时含 umon/smon 宏与 rb32 帧；029 忙等 20/20 |
| F7 证据 QEMU 必须本 worktree 自建且全门控统一 | ✅ | `.work/build/qemu` 自建，`.dadao` 局部 overlay 让 K5/K6/amb 也解析到同一二进制；run.sh 打印 md5 | 全部门控/证据 `c2b4b2f7…`；LTP `qemu_cmd` 逐轮同路径 |
| F8 私有树迁移后补丁是否与旧路径一致 | ✅ | `private_source.sh linux m18-linux-031`，`make_patch --source` 重导（0 written） | `trap.S` md5 `ef5bdc99…`、patch md5 `acda4b54…` 两侧一致；`--source-state` clean |

**判决**：F1–F4、F6–F8 已修/已处置并有真实复验；F5 给出结构性论证、频率上界与确定性 P13 触发。状态 **待验收**。

### 第 1 轮 reviewer 验收

**重跑（本人执行，仓库根；证据 = 运行期证据目录内 `run.sh`）**
1. `bash 运行期证据目录内/run.sh` → **EXIT=0 / `evidence: PASS`**（16 步全 PASS）。preflight：`qemu md5=c2b4b2f78738ba0865beed2abf830bf0`、`trap.S md5=4b2fe4a8…`、`trap.S.patch md5=faf97019…`（= HEAD blob）。`check-patch-tree rc=0`（`12 patch set(s), 464 patches OK`）、`check-config-pins rc=0`（`检查 109 项，失败 0 项`）、changelog / knowledge-refs / check-issues rc=0（`34 closed → resolved_by/closed_in OK`）。P13 `PASS=26 FAIL=0`：五路注入各 `expected terminal 实际=1` + `P13 PASS line absent 实际=0`（no-rc11 另 `wrong-ip/user 实际=0`），5 次 `restore trap.S md5=4b2fe4a8…`，after-restores base 4 项全 PASS。回归：K2 `170/170`、K5 `285/285`、K6 `82/82`、LTP×2 各 `PASS=14`+`20/20 checks` 且 `equal=True`、`qemu=自建`、amb `14/14`、soak `窗口 0/300、静默自旋 0`、029 忙等 `20/20`（`qemu rc=0` 共 20 条；`M18A_SPIN=20000000` 由 run.sh export）。
2. **独立注入（不走脚本内置路径）**：`cp -p` 备份（`4b2fe4a8…`）→ 删 `rc8` 两行（`6cf11ce1…`）→ 同一探针 `--inject none` → **EXIT=1**（`P13 PASS line 期望=1 实际=0` 等 4 项 base 断言全红）→ `cp`+`touch` 还原（md5 与备份相等）→ 再跑 → **EXIT=0**（5 项 PASS）。事后：worktree `git status` 0 行、私有树 `git status` 干净、`trap.S.patch` md5 未变。
3. 本人另跑：`check-milestones-fresh`/`check-tests-index`/`check-dirs`/`check-no-residue`/`check-writer-guards` rc=0；`check-temp-dirs` rc=1，5 VIOLATION 全属 m19-testcases-005 / m19-gem5-003 / m20-llvm-005 / m19-testcases-006 / r009（基线，非本任务）。

**约束核验**：范围 `git diff --name-only master...HEAD` 恰 6 项（与两参数式同）；HEAD 不在任何 `refs/remotes`（未 push）；状态 `待验收`；`ISS-m18-014` `status: closed` + `resolved_by: m18-linux-031`。三特性共存：HEAD 补丁 `DADAO_UMON_USER_EXIT_INTENT` 4 处、`DADAO_GPR_SAVE_STAGED_AT`+`rb32` 帧逻辑在；`git diff master..HEAD -- trap.S.patch` 只有 smon 两段增量，`-` 侧行仅注释与被移动的 `ld.o`/`cfx2rc`，**无 029/030 回退**。修法①：C 调用前 `cfx2rd … cg5, rc1 → rd2rb rb33`（spec §3.6 `cg5 rc1 = excp_prev_cfx_code`；`rb32–rb63` contract-abi callee-saved、restore 从帧回填），出口 `rb2rd rd2, rb33, 1 → cfx2rc … rc9`，**未硬编码 `cfx_smon`**；修法②：写序 `rc8→rc9→rc11→rc10`，`rc10` 在 `DADAO_GPR_RESTORE_AT`/`escape` 前**最后写**（SKIP `+4` 在其内）。测试资产：探针补丁头部 `NOT part of the delivered series`、落 `tests/unit/linux/`，`check-patch-tree` 只按 `manifests/components.lock.toml` 扫（12 组 464）⇒ 未被误当组件补丁；`check-config-pins 109`。overlay：本 worktree 局部 `.dadao` 的 `gate.lock`/`writers`/`night.lock`/`host-tools`/`tests` 仍是指向共享根的软链（flock 串行与写者互斥未破坏），仅 `cross-toolchain/bin/qemu-system-dadao` 指向自建；`check_k5`/`check_k6` 确无 `--qemu`（读 `toolchain_bin()/qemu-system-dadao`）⇒ 必要且合法；该两条路径 md5 均 `c2b4b2f7…`，与证据记录一致。

**findings（均不阻断）**：F1 证据 preflight 记 `ef5bdc99…/acda4b54…`，HEAD 为 `4b2fe4a8…/faf97019…`——逐行 diff **仅 3 行注释**（029 第 3 轮的注释订正，提交前 13:37–13:39 补同步），汇编产物等价，且我以 HEAD 内容重跑全绿；完成区宜补一句「提交前注释同步」。F2 不带 `DADAO_SOURCE_ROOT` 跑 `check_patch_tree.py` → **EXIT=1、4 problem**：`linux trap.S` ⑨/⑥ 2 条（本 worktree 共享源树 12:08:53 被 `apply_series` 写入、其后补丁改注释未重放）+ `qemu trans_ctrl.c.inc` 2 条（基线）；run.sh 用私有树故 rc=0。共享源树写权归合并动作（`m20-infra-003` 12:08:56 合入，任务 12:17 起改走私有树）且该 worktree 运行期目录随收尾删除 ⇒ **交 architect 合并时处置/披露**，engineer 侧补进遗留即可。F3 P13 六轮原始 console 未归档（脚本 `mkdtemp` 且不清理、判据只在内存，证据目录只留期望/实际计数），建议按 029 教训⑤ 归档进证据目录。F4 遗留①属实（`git log --merges master..HEAD` 7 条；补丁内容 = master+031，squash 干净；但「architect 合并 029 后重导」一句已过时——029/030 已在 master）；遗留②**属实**（本人 `M18A_SPIN=400000000` 6 启 → 镜像 `spin=400000000`、6/6 `end line` 缺失、EXIT=1；20M 口径 20/20）。nit：changelog 031 条目后多一空行；trap.S 注释引 contract-abi §4.1（实为 §4.5），沿用 030 既有写法。

**判决：Accepted**（验收命令块在本人重跑下全过、硬约束 1–4 无违反；F2 为共享源树陈旧，属合并动作处置项，已在上标注）
