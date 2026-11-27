# m16-qemu-005: cfx5 通用 `cg0-cg7`

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-qemu-003`（cfx5 命令）合入
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-23 纠正）

`contract-see §3` 明确：**每个 cfx 提供 `cg0–cg7` 共有寄存器**，`cg3 rc12`（`hypv_cg_reg_deleg`）也是每个 cfx 都有。cfx5 目前只实现 `cg8`，其余 cg 报 `CFXREG`（qemu-001 的 CACHE-04 口径）——这是实现缺口，不是设计取舍。

后果：cfx5 的 `cg3` 不可写 ⇒ supv 无法访问 cfx5（017 的 supv 阻塞）。

## 要做

1. **cfx5 走通用行**：`cfx2rd`/`cfx2rc` 对 cfx5 的 `cg0–cg7` 走 `cfx_reg_ptr` 的通用表（模式掩码、`switch_run_mode`/`excp_vector`、`cg3 rc12` deleg、`cg4` 计数、`cg5` 异常帧、`cg6` scratch、`cg7` 空间描述）；`cg8` 保持 CACHE-03 的专属寄存器。
2. **deleg**：`cg3 rc12` 复位全 1、RW、bit3 固定 1（软件写 0 无效、读回 1）；hmon 写 `0x8` 后 supv 可访问 cfx5。
3. **两模型**：`cache-model=off|on` 都不改变 `cg0–cg7` 的存在；`cg8` 按 CACHE-27（off=`exist=0`/合法命令 no-op、on=`0b11`/真维护）。
4. **契约对齐**：按 `contract-see §3` 通用表；`contract-cache` CACHE-03/04 只描述 `cg8` 专属，不改契约正文（用户已认定 cg0-cg7 是契约要求）。
5. **验证**：cfx5 的 `cg0–cg7` 读写/保留、`cg3 rc12` 可写且 bit3 固定 1；supv 访问 cfx5 成功（hmon 写 `0x8` 后）；off/on 两模型都可用；`arch-umon-002` 等回归。

## 不做

- 不改 cfx5 的 `cg8` 专属语义（001/003）；
- 不改 gem5/RTL（另由 024/019 覆盖）；
- 不改影子数据通路。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py qemu` 幂等；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. cfx5 的 `cg0–cg7` 读写/保留；`cg3 rc12` 写 `0x8` 后读回 `0x8`、bit3 恒 1；
2. supv 访问 cfx5（hmon 写 deleg 后）成功；未写 deleg 时 `CFXPERM`；
3. off/on 两模型下 `cg0–cg7` 都在；`cg8` 按 CACHE-27；
4. **可达 FAIL**：注入「cfx5 仍走 `CFXREG`」⇒ 红；注入「deleg bit3 可清 0」⇒ 红；`cp`+md5 还原回绿；
5. `check-patch-tree` qemu 段 0 problem、`check-index-blobs`、`check-tasks`、`check-issues` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` rc=0 **16/16**；`run.sh --inject` rc=0 **29/29**（INJ-1「cfx5 非 `cg8` ⇒ `CFXREG`」注入后 `cg0_2_roundtrip` 转红 rc=1；INJ-2「`cg3 rc12` 写不再或 bit3」注入后 `deleg_bit3` 转红 rc=1；两路均 `cp` 备份 + md5 对账还原后重建回绿）。cfx5 探针 **13 例（10 例 off/on 各一次 + `cache_off`/`cache_on` 各一次 + `cache_illegal` 两次）= 24 次全 PASS**：`cg0`–`cg2` mask/`switch_run_mode`/`excp_vector`、`cg3` hypv 行、`cg3 rc12` 复位/RW/bit3、`cg4` 配置与计数、`cg5` 现场、`cg6` scratch、`cg7` 空间、15 组保留组合 ⇒ `CFXREG`、supv 三例（未写 deleg ⇒ `CFXPERM`；写 `0x8` ⇒ 读 `cg4 rc0` 成功；`cg3` 恒拒）、`cg8` off/on/非法编码。回归：`integ042t` rc=0、`integ048t` rc=0、`arch-umon-002` rc=0。
**修改文件**（4）：`components/qemu/patches/target/dadao/helper.c.patch`、`components/qemu/README.md`、`components/qemu/changelog.md`、本任务书。
**验收结果**（真实 rc）：`make build-qemu` 0（未新增 warning）；`make_patch.py qemu` 首跑/二跑均 0 且二跑 `0 written`（幂等）；`check_patch_tree.py` rc=0，qemu **69 patch / 0 problem**；`check-index-blobs`/`check-tasks`/`check-issues`/`check-component-changelog`/`check-dirs`/`check-no-residue` 均 0。组件源树 `base..HEAD` 恰 1 commit、工作树干净（隔离 worktree 从 pinned base 重放 69 补丁，再仅改 `target/dadao/helper.c`，净 diff 2 处删除 + 注释订正）。未改契约正文、`spec/`、gem5/RTL、影子数据通路，未升版本号，未提交仓库 git。
**新发现/坑**：① 共享 QEMU 源树起点与 master 补丁集不一致（停在 002/003 之前的旧态）；本任务改用隔离的 qemu git worktree（pinned base + 本分支 series）重建后再实现，否则 `make_patch` 会把 002/003 的代码从补丁里删掉。② `cg4` 的 rc0–rc6 在既有通用表里**全部只读**（计数/配置由硬件维护），写任何 rc ⇒ `CFXREG`；不是 RW。③ cfx5 `cg7` 无内部空间：16 块全 0，写任意 rc ⇒ `CFXREG`。④ supv 访问 cfx5 是**两轴**：除目标 cfx 的 `cg3 rc12` 外还要目标 cfx 的 supv `cfxreg` 行允许源 cfx；未写 deleg 与未开 `cfxreg` 都报 `CFXPERM`。⑤ Tiny 的 `cg3 rc12` 写忽略逻辑不影响 Vast cfx5（`switch_run_mode_write_ignored` 只对 Tiny）。
**遗留问题**：无本任务未完成项。共享 QEMU 源树与 master 补丁集不一致的状态建议 infra/architect 复核并统一（本任务实现与最终导出在隔离 worktree 内完成；共享源树的起点异常未在本任务内修复）。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（本深度无嵌套子代理）：`cfx2rd`/`cfx2rc` 删除特判后两条路径与 `cfx_reg_ptr` 的交接（cg0-2 模式行、cg3 hypv 行 + rc12、cg4 RO、cg5 现场、cg6 scratch 边界、cg7 只读表）、cg8 专属分支未被绕过、两轴权限与 deleg 的判序（`cfx_perm_denied` → `cfx_deleg_denied` → 通用表）、off/on 只影响 `cache_exist`/命令效果而不影响 cfx5 存在性、证据脚本每条断言的可达 FAIL 与 `cp`+md5 还原纪律。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 共享 QEMU 源树起点停在 002/003 之前；首次导出把 002/003 的 457 行从 `helper.c.patch` 删除 | ✅已修 | 改用隔离 qemu git worktree：pinned base → `apply_series.py --component qemu`（69 补丁）→ 仅改 `helper.c` → 收敛 base+1 | `make_patch` 只写 `helper.c.patch`（1 written），diff 仅 2 处删除 + 注释；`check-patch-tree` qemu 69/0 |
| F2 探针把 `cg3 rc4`（`cfx_intr_mask`）误期望为默认 mask | ✅已修 | rc0–3 = 默认 mask，rc4 = 全 1 | `cg3_rows[off/on]` PASS |
| F3 探针写 `cg4` 计数（rc2/rc5），契约/实现均为 RO ⇒ 误报 `CFXREG` | ✅已修 | 改为读 rc2–5 = 0，另加写 rc0/rc2 ⇒ `CFXREG` 的保留用例 | `cg4_config`/`reserved_cfxreg` PASS |
| F4 探针 `cache_illegal` 用 `Checks` 分支但未定义 fail 标签，`Seq.resolve` 会 KeyError | ✅已修 | 改用原始字列表，只用故障观察 | `cache_illegal[off/on]` PASS |
| F5 保留组合覆盖不足（未含 cg0/cg3 的 rc9/rc11、cg5 rc2/4 写、cg6 rc4 写） | ✅已修 | 扩到 15 组保留组合 | `reserved_cfxreg[off/on]` PASS |
| F6 `arch-umon-002` 在 worktree 缺 `.dadao` 工具链/BootROM ⇒ rc=2（非实现失败） | ✅已修 | 运行期把已安装的交叉工具链与 Vast BootROM 链入 worktree 的 `.dadao`（不改仓库文件） | `arch-umon-002` PASS rc=0 |
| F7 supv 只测 cg4，未验证「开 0x8 后 cg3 仍拒」 | ✅已修 | supv 增 `open_cg3_still_denied` | `supv[off/on]` PASS |

**约束核验**：`git status -uall` = 3 项补丁/文档 + 本任务书；组件源树 `base..HEAD` 恰 1 commit、工作树干净；未改 `spec/`、契约正文、gem5/RTL、影子数据通路；未升版本号；未提交仓库 git；本记录与完成区无运行期具体路径；术语「寄存器组」。
**判决**：**待验收**（F1–F7 已修，无未修 finding）。

### 第 1 轮 reviewer 验收

**重跑记录**（仓库根执行运行期证据目录内的 `run.sh`，独立重跑、不采信完成区）：
1. `run.sh` ⇒ `checks: PASS=16 FAIL=0 / RESULT: PASS`，退出码 **0**：`make build-qemu` 0；探针 **24 例全 PASS**；`integ042t` / `integ048t` / `arch-umon-002` 各 **rc=0**；`make_patch` 二跑 `0 written, 69 unchanged`、qemu patches=69；`check-patch-tree` qemu 段 **rc=0 qemu=69 problems=0**；index-blobs/tasks/issues/changelog/dirs/no-residue 全 0。
2. `run.sh --inject` ⇒ `checks: PASS=29 FAIL=0`，退出码 **0**：INJ-1 后 `cg0_2_roundtrip` 转红 **rc=1**、INJ-2 后 `deleg_bit3` 转红 **rc=1**；两路均 `cp` 备份 + md5 相等还原、重建回绿、源树 `git status` 空。
3. **reviewer 独立注入 1 路**（换锚点：在 `cfx_reg_ptr` 入口加「`cfx5` 非 `cg8` ⇒ `return NULL`」，非工程师的 `cfx2rd/cfx2rc` 锚点）⇒ 同一脚本 `checks: PASS=10 FAIL=6`、退出码 **1**，探针 `fail=16`（`cg3_rows`/`deleg_bit3`/`cg4`/`cg5`/`cg6` → `exit 0x7e`，`supv` 超时），并连带触发 `check-patch-tree` 断言⑥⑦ 与 `make_patch` E1 拒绝 ⇒ 断言可达 FAIL、非恒真；`cp` + md5（`a7fbb40b…`）还原后重跑 ⇒ `PASS=16 FAIL=0` 退出码 0。
4. 快照对账：验收前后 3 个交付文件 md5 逐项相同（`helper.c.patch` `2959e229…`、README `9c94aad1…`、changelog `f16445dd…`），任务书仅因本轮审阅记录新增而变化；`git status` 同为 4 项、`git log` 仍停在派单提交（未新增提交）、源树 `base..HEAD` 恰 1 commit 且干净。

**语义核验**：cfx5 `cg0–cg7` 已全部走 `cfx_reg_ptr` 通用表（`cfx2rd/cfx2rc` 中两处 `cg != 8` 特判已删，`cg8` 两处专属分支与 cache 面未动）；保留 rc / 写 RO ⇒ `CFXREG`（15 组组合 PASS）；`cg3 rc12` 复位全 1、可写、写 0 读回 `0x8`（bit3 恒 1）；hmon 写 `0x8` 后 supv 读 `cg4 rc0` 成功，未写 deleg ⇒ `CFXPERM`，开后 `cg3` 仍拒；off/on 两模型 `cg0–cg7` 均在，`cg8` 按 CACHE-27（off `exist=0`+合法 no-op、on `0b11`、非法编码两模型 `CFXREG`）。导出补丁以 `manifests` 锁定 base 为父提交，逐字节复现隔离源树内容（md5 一致），与 master 补丁集仅差本任务 5+/18-（两处特判删除 + 注释订正）⇒ **含 002/003 全部改动**。

**Finding（非本任务交付物缺陷，报 architect 定夺）**：共享源树与 master 补丁集不一致——master 侧 `check_patch_tree.py` 实跑 **rc=1**（qemu 断言⑥⑨ 8 条：缺 002/003 共 476 行；另有 chipyard 8、musl 10 条，属既有基线红）；且该源树满足 E1，master 侧若跑 `make_patch.py qemu` 会**静默导出旧内容、删掉 002/003**（本任务首次导出即踩中）。**修复建议**（AGENTS §4「组件补丁重建」/`docs/Process-01`，禁 `reset --hard`）：先确认本任务已合并、隔离 linked worktree 随任务工作树清理（共享源树的 `.git` 是主工作树对象库，先删会连带破坏它）⇒ 删共享 qemu 源树（按 `docs/Process-01` 组件源树重建口径）⇒ `make fetch` ⇒ `apply_series.py --component qemu` ⇒ `make build-qemu` ⇒ 判据 `check_patch_tree.py` qemu 段 0 problem + `--source-state` E1；chipyard/musl 同法，全程写者互斥、门控串行。

**判决**：**Accepted**（验收命令块在 reviewer 自己的重跑下全部通过、独立注入红→还原→回绿、约束无违反；共享源树 finding 由 architect 处置）。
