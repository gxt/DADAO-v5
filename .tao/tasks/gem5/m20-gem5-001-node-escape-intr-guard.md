# m20-gem5-001: `nodeEscape` 的全局中断掩码恢复守卫（ISS-472）

**模块**：gem5
**项目里程碑**：M20
**依赖**：`m16-gem5-026`（gem5 R2 异步面，待验收/合并）完成后再派；`m18-gem5-002` 已合入
**可并行分片**：否（单组件补丁，同改 `components/gem5`）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（M20 分诊，2026-11-25）

`ISS-472` 记录 gem5 `nodeEscape` 缺 `savedIntrValid` 守卫
（`m16-gem5-013` 复核查出）：从**同步异常帧** `escape` 时，gem5 会把
`cfx0.global_cfx_intr_mask` 写成旧值/0；Tiny 侧 `tinyEscape` 已有
`savedIntrValid` 判定，Node 侧没有。（QEMU 当前已不建模该内部 mask，
不能再以 QEMU 的 `saved_intr_mask_valid` 作对照；口径以 Tiny 与
`spec/DADAO-12 §5.2/§5.3` 的“trap 保存、同步异常不保存”为准。）

现场确认：

- `node_cfx.cc` 的 `nodeEscape` 无条件执行
  `s.cfx[mon].globalCfxIntrMask = s.cfx[ci].savedGlobalIntrMask`；
- `tiny_cfx.cc` 的 `tinyEscape` 用 `s.cfx[ci].savedIntrValid` 守卫；
- Node 侧 `NodeCfxState` 没有 `savedIntrValid` 字段。

当前探针不触发该路径，所以是潜在三平台分叉；按 Tiny 现有口径补守卫即可。

## 目标（2026-11-25 主会话裁定 A 后收口）

1. **Node 不加 `savedIntrValid`**：`m16-gem5-026` 已按现行 `spec/DADAO-12
   §5.2(三)4`/`§5.3 3` 与 `contract-see §3` 删除 Node 的掩码保存/恢复；再加该
   状态即死代码且改变异步掩码语义，故本任务不改引擎。
2. **交付 = 回归探针 + 入口**：`tools/gem5/check_node_escape_intr.py`（同步异常
   帧 `escape` 前后两个 monitor 的 `cg8 rc1` 逐位不变；含负控与可达 FAIL）+
   `components/gem5/README.md` 的构建/校验入口一行。
3. Tiny 的旧 save/restore（`savedIntrValid`）由 `m16-gem5-025` 第 6 项
   （`ISS-m16-009`）跟踪，不在本任务范围；`globalCfxIntrMask` 字段保留（仍是
   monitor 的 `cg8 rc1` 异步来源掩码，`§5.4(一)`），本任务不删除、不重定义。

## 验收（逐条贴真实 rc）

1. `check-gem5-decode` rc=0；`check-tiny-hmon`/相关 gem5 unit 真 rc。
2. 新增探针：原始实现 ⇒ FAIL（mask 被改写）；加守卫后 ⇒ PASS；`cp` + md5
   还原后回绿。
3. Node 侧现有代表集（arch cfx0/2/3/4/5/15/32/34 或 `tests/arch` 最小代表）
   不回归；给出改动前后 rc 对照。
4. `check-patch-tree` 的 **gem5 段 0 problem**；总 rc 受在途 qemu/musl 影响时
   按分段披露。

## 约束

独立 `git worktree`（分支 = `m20-gem5-001`）；不提交 git；只改
`components/gem5/**` 与必要探针/本任务书；不改 `spec/`、契约、`Makefile`；
不新增平台语义。任务书不写构建树/安装树/临时目录具体路径；证据落在
「运行期证据目录内的 `run.sh`」。

## 裁定记录

1. **已裁定 A（主会话 2026-11-25）**：`ISS-472` 的 Node 现场已由 `m16-gem5-026` 按现行 spec/契约消解，本任务**不改引擎代码**；以「回归探针 + README 入口 + 关闭 issue 的证据」交付。
   判断依据：`m16-gem5-026` 已按 `spec/DADAO-12 §5.2(三)4`、`§5.3 3` 与 `contract-see §3`（“`trap`/`escape` 不保存、不恢复任何来源掩码”）删除保存/恢复；QEMU 的 `cfx_enter`/`helper_cfx_escape` 同标 “no independent cfx-mask state”（Node 已与之对齐）；gem5 侧只剩 Tiny 仍保存/恢复。按 Spec-first 不加 `savedIntrValid`（加了即死代码且改变异步掩码语义）。
2. **已确认（不在本任务范围）**：Tiny 仍保留 `savedIntrValid`/保存恢复（与 0.8.0-rc 不一致），由 `m16-gem5-025` 第 6 项（`ISS-m16-009`）跟踪；本任务不动。
3. **已确认（不删除）**：`globalCfxIntrMask` 仍是 monitor 的 `cg8 rc1` 异步来源掩码（`§5.4(一)`），本任务未重定义。

## 完成区

**测试结果**：运行期证据目录内 `run.sh --inject` **rc=0（31 项检查 / 0 失败）**，日志 `run-sh.log`。探针 `sync-escape`（gem5/qemu）+ 负控各 1：4/4 PASS；`check-gem5-decode` positive 263/263、negative 391/391、legality 28/28、legacy 2/2、failures 0；`check_b6` 30/30、`[FAIL]` 0、rc=0；`check_tiny_hmon` 213 checks/45 records、rc=0；Node 代表集 `run_arch --cfx 34`（2 case）与 `--case arch-ptw-001` gem5 PASS；`arch-hart-001` gem5 为**已知基线红**（5 条 `cg9 rc6`，`m16-gem5-025` 第 5 项），失败集全部属于该已知项且 QEMU 同用例 PASS。
**修改文件**：`tools/gem5/check_node_escape_intr.py`（新增）、`components/gem5/README.md`（构建/校验入口一行）、本任务书；**未改** `components/gem5/patches/**`（理由见「裁定记录」1）。
**验收结果**：注入 026 前的无条件恢复行（`s.cfx[ci].globalCfxIntrMask = ~0ULL;`——本 ROM 的 `savedIntrMonitor`=3、保存值=cfx3 复位掩码）⇒ 重建后探针 `sync-escape/gem5` 返回 **225（0xE1，FAIL）**；`cp` 还原后 md5 `446c4a68…` 与注入前一致、重建后探针回 **0（PASS）**，源树 `git status` 干净；引擎源/补丁全程未改（md5 与基线一致），故 Node 代表集 rc 与基线相同（cfx34/arch-ptw-001 PASS，cfx15 仅既有 rc6 红）。`check-patch-tree` gem5 段 **106 patch / 0 problem**（总 rc=1 的 16 problem 全在 llvm-project/linux/musl，属在途会话，按分段披露）。
**新发现/坑**：① `ISS-472` 的现场已被 `m16-gem5-026` 删除（该任务要求「`trap`/`escape` 不保存/恢复掩码」）——M20 分诊文本基于 026 前实现，需在台账/issue 更正；② `arch-hart-001` gem5 基线红 = 5 条 `cg9 rc6`（026 遗留②），不是本任务引入；③ `run_arch --case arch-umon-011` 的 gem5 载体未接（`check_mode_env` 只接 QEMU，rc=2），不能作 Node 代表集。
**遗留问题**：无代码遗留；按「裁定记录」1（裁定 A）关闭 `ISS-472`。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：`tools/gem5/check_node_escape_intr.py`（新）、`components/gem5/README.md` 一行、证据 `run.sh`；引擎源未改。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 目标 1/2（补 `savedIntrValid`）与现行 spec/契约冲突，照做会引入死代码并改变异步掩码语义 | ✅已裁定 A（不改引擎） | 未加状态；依据入「裁定记录」1 | `spec/DADAO-12 §5.2(三)4`/`§5.3 3`、`contract-see §3`、`m16-gem5-026` 摘要、`m16-gem5-025` 第 6 项 |
| F2 探针可能恒真（掩码不可写/初始写入未生效） | ✅已修 | 先写后读回同值，否则 0xE3 退出 | 探针 `fail_seed` 分支 |
| F3 比较可能恒真（引擎未走到 escape；或返回后读被拒而沿用初始值） | ✅已修 | handler 对 rd9 累加（重复/嵌套进入 ⇒ 2 ≠ 1 ⇒ 0xE2，不比较陈旧 rd7）；另设负控 ROM（handler 改写掩码 ⇒ 0xE1） | `--selfcheck`：gem5/qemu 均 225；探针 PASS 4/4 |
| F4 FAIL 路径是否真能触发（026 前的实现是否真的改写帧 monitor） | ✅已修 | 注入 026 前那行（`s.cfx[ci].globalCfxIntrMask = ~0ULL`）并重建 ⇒ 225；还原重建 ⇒ 0 | `run-sh.log` 第 6 段 |
| F5 初版探针只观测 `cfx0`，但 026 前实现按 `savedIntrMonitor` 写；本 ROM 的 power→hmon `trap cfx3` 已把该值置 3 ⇒ 只测 `cfx0` 会漏掉历史实现（假绿） | ✅已修 | 改为观测帧 monitor `cfx3`（可达 FAIL）+ `cfx0`（跨 monitor 守护），负控同步改 cfx3 | gem5/qemu PASS + 注入 225 |
| F6 还原是否可靠 | ✅已修 | `cp`+md5（`446c4a68…`）+ 源树干净 + 重建回绿 | `run-sh.log`、`git -C .work/source/gem5 status` |
| F7 `run.sh` 中途编辑导致 bash 读到半截脚本（首次整跑 rc=2） | ✅已修 | 改为整跑前定稿；最终 `run.sh --inject` 31/31 PASS、rc=0 | `run-sh.log`/`run-sh.EXIT` |

**判决**：F1 已按裁定 A 收口，其余无未修项；状态 `待验收`。

**裁定 A 后范围收口（2026-11-25 主会话）**：

- 目标改为「Node 不加 `savedIntrValid`；交付 = `tools/gem5/check_node_escape_intr.py` 回归探针 + `components/gem5/README.md` 入口 + 关闭 issue 的证据」；原目标 1/2 撤销，判断依据保留在「裁定记录」1（spec/契约/026/QEMU 对齐）。
- F1 处置由 ⏸延后（待裁定1）转为 **✅已裁定 A（不改引擎）**；Tiny 旧 save/restore 明确由 `m16-gem5-025` 第 6 项（`ISS-m16-009`）跟踪，不在本任务。
- 完成区实测数字不变（`run.sh --inject` 31/31、注入 225→还原 0、gem5 段 106 patch/0 problem 等），仅范围与结论表述收口；状态保持 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑（本人执行，workdir=仓库根，2026-11-25 16:45–16:58）**

- `python3 tools/gem5/check_node_escape_intr.py --platforms gem5,qemu --selfcheck` → `SUMMARY checks=4 failures=0`、**rc=0**；负控 gem5/qemu 均 `expected=225 actual=225`（0xE1，非恒真）。
- `make check-gem5-decode` → **rc=0**（positive 263/263、negative 391/391、legality 28/28、legacy 2/2、failures 0）。
- `python3 tests/unit/gem5/check_tiny_hmon.py` → **rc=0**（213 checks / 45 records、`[FAIL]` 0）。
- `python3 tools/infra/check_patch_tree.py`（= `make check-patch-tree`）→ 脚本 **rc=1**、make rc=2；16 problem = linux 12 + llvm-project 2 + musl 2（在途会话），**gem5 段 106 patch / 0 problem**（分段披露成立）。
- `python3 tools/gem5/check_b6.py` → **rc=0**（B6 coverage 30/30、failures 0）。
- Node 代表集：`run_arch --cfx 15 --platforms gem5` **rc=1**，5 条 FAIL 全为 `cg9 rc6`（非 rc6 计 0）＝ `m16-gem5-025` 第 5 项基线红；`--cfx 34` **rc=0**（2 case）；`--case arch-ptw-001` **rc=0**。
- `make check-writer-guards check-dirs check-no-residue check-tests-index` → **rc=0**。

**独立注入（`cp`+md5，未用 `git checkout`；注入点与 engineer 不同）**

- 备份运行期 gem5 源树 `node_cfx.cc`（md5 `446c4a68…`）；在 `s.cfx[ci].escapeNum++;` 后插入 `s.cfx[ci].globalCfxIntrMask = ~0ULL;`（md5 → `33ee3a80…`）。
- `make build-gem5 JOBS=32` **rc=0** ⇒ 探针 `sync-escape/gem5` `[FAIL] … actual=225`、**探针 rc=1**（0xE1 可达，探针非恒真）。
- `cp` 还原 ⇒ md5 `446c4a68…` 与注入前相等、源树 `git status` 干净；重建 **rc=0** ⇒ 探针 `--platforms gem5,qemu --selfcheck` **4/4 PASS、rc=0**（回绿）。gem5.opt 两次 md5 不同仅因二进制内嵌编译时间戳（banner `gem5 compiled …`），源字节全等。

**约束核验**

- 范围：验收前后 `git status --porcelain -uall` 快照逐行相同，仅 `tools/gem5/check_node_escape_intr.py`（untracked）、`components/gem5/README.md`（+2 行入口）、本任务书；`components/gem5/patches/**` diff=0，引擎源/补丁零改动。
- Oracle：判据引 `spec/DADAO-12 §5.2` 步 4「不保存任何中断来源掩码」、`§5.3` 步 3「不恢复任何来源掩码」、`contract-see §3`，非从 gem5 实测反推；探针含 seed 读回（0xE3）、同步进入计数 rd9（0xE2）、帧 monitor / 另一 monitor（0xE1 / 0xE4），四码可区分。
- 裁定记录：A（不改引擎）与 Tiny 归属（`m16-gem5-025` 第 6 项 / `ISS-m16-009`）写清；无未决「待裁定」（仅历史转移叙述）。finding（文档级，不阻断）：记录未具名被否的「B＝补 `savedIntrValid`」，但原目标 1/2 已撤销并附 spec 依据。
- `make check-knowledge-refs`（本记录写入后复跑）→ **rc=0**，`结果: PASS（0 具体 .work/** 引用；0 悬空）`。

**判决：Accepted**（engineer 达标；架构师终审）。

**遗留**：① `ISS-472` 在 issue 册仍 `status: open`——关闭动作留主会话（Accepted 后按裁定 A 执行）；② `arch-hart-001` 5 条 `cg9 rc6` 属 `m16-gem5-025` 第 5 项基线红，非本任务责任。
