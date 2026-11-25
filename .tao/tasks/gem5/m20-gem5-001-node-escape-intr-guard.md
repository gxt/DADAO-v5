# m20-gem5-001: `nodeEscape` 的全局中断掩码恢复守卫（ISS-472）

**模块**：gem5
**项目里程碑**：M20
**依赖**：`m16-gem5-026`（gem5 R2 异步面，待验收/合并）完成后再派；`m18-gem5-002` 已合入
**可并行分片**：否（单组件补丁，同改 `components/gem5`）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（M20 分诊，2026-11-25）

`ISS-472` 记录 gem5 `nodeEscape` 缺 QEMU 的 `saved_intr_mask_valid` 守卫
（`m16-gem5-013` 复核查出）：从**同步异常帧** `escape` 时，gem5 会把
`cfx0.global_cfx_intr_mask` 写成旧值/0；Tiny 侧 `tinyEscape` 已有
`savedIntrValid` 判定，Node 侧没有。

现场确认：

- `node_cfx.cc` 的 `nodeEscape` 无条件执行
  `s.cfx[mon].globalCfxIntrMask = s.cfx[ci].savedGlobalIntrMask`；
- `tiny_cfx.cc` 的 `tinyEscape` 用 `s.cfx[ci].savedIntrValid` 守卫；
- Node 侧 `NodeCfxState` 没有 `savedIntrValid` 字段。

当前探针不触发该路径，所以是潜在三平台分叉；按 Tiny 现有口径补守卫即可。

## 目标

1. Node 侧增加与 Tiny 同形的 `savedIntrValid` 状态：只在 `trap` 进入确实保存
   过 `globalCfxIntrMask` 时置位；同步异常进入不置位。
2. `nodeEscape` 仅在 `savedIntrValid` 为真时恢复，并在恢复后清位；其它状态
   （`prev_run_mode`/`prev_cfx`/计数器/IP）不动。
3. **不**在本任务里删除或重定义 `globalCfxIntrMask` 字段；如果 reviewer 认为
   现行 `spec/DADAO-12 §5.2/§5.3` 要求彻底删除该内部状态，写入「待裁定」，
   不自行扩大改动。
4. 增加一条能观测该路径的探针/断言：同步异常帧 `escape` 后
   `global_cfx_intr_mask` 不被改写；若当前 testcase 无法观测内部寄存器，用
   最小 gem5 unit/FS 探针或现有 arch 探针扩展，必须给出可达 FAIL。

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

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
