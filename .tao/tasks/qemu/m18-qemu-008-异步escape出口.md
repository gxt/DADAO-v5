# m18-qemu-008: QEMU 实现异步 escape 出口（cg5 rc8–rc11、cg9 新布局、escape cfxHA）

**模块**：qemu
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入：DADAO-12/22 0.8.0、ADR-0061 R3）
**可并行分片**：否（同 `components/qemu` 写者）
**预估**：3–5 h（标定：同档 qemu-006 捕获缓冲修订 2–3 h；本任务含 cg5/cg9 重排 + escape 重写 + 入口自动填，取 1.5–2×）
**档位**：大改（QEMU 异常进入/退出模型）
**状态**：待开始
**执行环境**：本地（`qemu-system-dadao`，Vast/Tiny）

## 背景

`m18-spec-007` 定稿并合入：`cg5` 分“入口记录（`rc0`–`rc3`，只读）+ 出口意图（`rc8`–`rc11`，进入时硬件复制、软件可写）”；`cg9` 重排为 `rc0`–`rc3` 同序记录、`rc4` 源集合、`rc5` pending、`rc14` switch、`rc15` vector；`escape` 改为 `escape cfxHA`（`imms18` 恒 0），按 `cg5 rc8`–`rc11` 返回并把 `rc11` 整字写入目标模式 monitor 的 `cg8 rc1`。

QEMU 现实现仍是 R2：`m->switch_run_mode`=`rc8`、`m->excp_vector`=`rc10`、`cg5 rc0/1/3` 可写、`cg5 rc5` 是死状态 pending、`escape` 有 `imms18` 偏移并检查 `cause_id != 0`、异步写 `cg9 rc0`–`rc6`。本任务把 QEMU 对齐到 0.8.0 规范。

## 目标

1. **`cg5`**：`rc0`–`rc3` 改 `HW/RO`（软件写 ⇒ `CFXREG`）；`rc4` cause id、`rc5` cause info；删除 `pending` 字段；`rc8`–`rc11` 为出口意图（RW，进入时硬件复制，`rc11` 复位全 1）；`rc6`/`rc7` 保持 reserved。
2. **`cg9`（`cfx_hart`）**：`rc0`–`rc3` 同序记录（`HW/RO`）；`rc4` 本次源集合（`HW/RO`）；`rc5` `async_src_pending`（`HW/RO`）；`rc14` `async_switch_run_mode`（RW，复位 2）；`rc15` `async_excp_vector`（RW，48 位、低 2 位写忽略）；`rc6`–`rc13` reserved ⇒ `CFXREG`。
3. **`cg0`–`cg3`**：`<mode>_switch_run_mode` 由 `rc8` → `rc14`、`<mode>_excp_vector` 由 `rc10` → `rc15`；原 `rc8`/`rc10` 访问 ⇒ `CFXREG`。
4. **同步进入（含 `trap` 进目标 cfx）**：写目标 cfx `cg5 rc0`–`rc3`（入口记录）+ `rc4`/`rc5`（cause）+ `rc8`–`rc11`（出口意图；`rc11` = 被打断模式的 `cg8 rc1` 当前字）。
5. **异步进入（`cfx_hart`）**：写 `cg9 rc0`–`rc4`（记录 + 源集合）与 **hart 自己的 `cg5 rc8`–`rc11`**（`rc11` = 被打断模式的 mask）；**不写** hart `cg5 rc0`–`rc3`。
6. **`escape cfxHA`**：`imms18` 必须 0（非 0 ⇒ `ILLI`）；`cfxha` 必须等于当前 cfx（否则 `CFXESC`）；目标模式（`rc8`）不得高于当前模式（否则 `CFXESC`）；目标 cfx 未实现或无对应 monitor（jail→jmon）⇒ `CFXESC`；跳转精确取 `rc10`；把 `rc11` **整字**写入目标模式 monitor 的 `cg8 rc1`（与切模式/切 cfx/跳转同一状态转换）；`escape_num` +1；**删除** `cause_id != 0` 的帧有效性检查；不设有效位。
7. 更新受影响的 QEMU 侧探针/单测（`tests/arch/**`、`tests/unit/qemu/**`、`tools/testcases/arch/**`）；`vast-arch-inventory.md` 与保留差异表按新口径标注。
8. **不做**：不删 `cfx_jmon`（`m18-qemu-007`）、不改内核/IDL/LLVM/gem5/RTL。

## 验收（逐条贴真实 rc）

1. 单元探针（新增/改造）：`cg5` 写入 `rc0`–`rc3` ⇒ `CFXREG`；`rc8`–`rc11` 读写正常；`rc11` 复位全 1；`cg9` 新槽位读写/保留槽 `CFXREG`；`cg0`–`cg3` 的 `rc14`/`rc15` 生效、`rc8`/`rc10` ⇒ `CFXREG`。
2. 进入探针：同步 `trap` 后目标 cfx 的 `cg5 rc0`–`rc5`/`rc8`–`rc11` 正确；异步进入后 `cg9 rc0`–`rc4` 与 hart `cg5 rc8`–`rc11` 正确、hart `cg5 rc0`–`rc3` 保持不变。
3. `escape` 探针：正常返回（mode/cfx/ip/mask 四者都对）；`rc11` 整字写目标 monitor；`imms18 != 0` ⇒ `ILLI`；错误 cfxha / 升权 / 未实现目标 ⇒ `CFXESC`；`escape_num` +1。
4. **可达 FAIL ≥2 路**：① 把 `rc11` 改成增量写 ⇒ 探针红；② 恢复 `cause_id != 0` 检查或把 `rc8` 当 switch ⇒ 探针红；`cp`+md5 还原并重建回绿。
5. 不回归：M16 cfx5/cache 代表集、Tiny 基线（Tiny 无 hart/umon 的路径按既有规则）；`check-patch-tree` qemu 段 0 problem；`check-component-changelog`、`check-knowledge-refs`、`check-qemu-forms` rc=0。
6. **KNOWN-RED 披露**：Linux 侧（K2/K5/K6、IDL 四方比对、LLVM 向量）在实现任务跟进前会红——逐条列出并归因，**不得改内核/IDL/LLVM/tests 去凑绿**。
7. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/qemu/patches/**`、`components/qemu/changelog.md`、`tests/arch/**`、`tests/unit/qemu/**`、`tools/testcases/arch/**`、`tests/arch/vast-arch-inventory.md`、本任务书。
3. 不改 `spec/`、`.tao/contracts/`、`Makefile`、内核/musl/busybox/gem5/RTL/LLVM/IDL；不改版本号。
4. 组件补丁经 `make_patch.py qemu` 重导；还原 `cp`+md5；还原后重建；术语「bank = 寄存器组」。
5. 顺序：先实现进入/布局，再实现 `escape` 与 `rc11` 原子写；每步用探针验证。

## 待裁定

无。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
