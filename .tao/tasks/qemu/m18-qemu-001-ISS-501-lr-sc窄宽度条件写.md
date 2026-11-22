# m18-qemu-001: ISS-501 lr/sc 窄宽度条件写丢失

**模块**：qemu
**项目里程碑**：M18
**依赖**：无（QEMU 参考实现修复；`m18-infra-001` 的窄 CAS 口径可作回归素材）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；TCG 存储路径定位，取 1.5–2× 中位）
**档位**：中改（QEMU 执行语义 + 新增向量）
**状态**：待开始
**执行环境**：本地（`qemu-dadao` / `qemu-system-dadao`）

## 背景

`ISS-501`【P2】：`lr`/`sc` 的**窄宽度条件写会被静默丢弃**（参考机器 `qemu-dadao`/`qemu-system-dadao`，`target/dadao/translate.c` 的 `gen_sc`）：

- 触发形状：同一 TB 内先有同址窄加载（`ld.ut`）再 `lr`/`sc`，且该地址的 8 字节字里另有被写过的 `int` ⇒ `sc` 报成功（`rdHB=0`）、内存保持旧值；`a_or`/`a_cas` 型 RMW 因此丢更新。
- 最小复现：`m18-infra-001` 运行期证据的 `probe/narrow_cas_probe.c`（两次 `st.o` + `ld.ut` + `lr.t`/`sc.t` ⇒ 写丢失；去掉 `ld.ut` 即正常），`word_cas_probe.c` 的 `lr.o`/`sc.o` 同场景正常。
- 后果：`m18-infra-001` 之前 musl `mallocng` 的 `avail_mask`/`freed_mask` 记账被破坏（`ISS-497`/`ISS-499`，musl 侧已改用字 CAS 规避）。
- 期望值以 `spec/DADAO-*` 的 `lr`/`sc` 语义与 `contract-isa.md` 为准；**不得**以「musl 已规避」当作保留缺陷的理由。

## 目标

1. 定位 `gen_sc` 的 `MO_ALIGN`/窄宽度大端存储路径与 TCG load/store 交互，修复「`sc` 成功但窄写被丢」。
2. 补一条覆盖「同 TB 内前置窄加载 + `lr.t`/`sc.t` 同址 CAS」的指令向量，修前可复现红、修后可绿。
3. 保留 `ISS-497` 的最小复现作为回归素材（运行期证据可引用，不入库为依赖）。
4. 明确 `sc` 失败/成功的 `rdHB` 与内存可见性语义，排除「报失败但已写」的反向错误。

## 验收（逐条贴真实 rc）

1. 修前用最小复现证明缺陷（`sc` 成功 + 写丢失），修后同一程序结果正确；用户态与 system 两入口至少各验一次。
2. 新增 `tests/inst/` 向量：`ld.ut` + `lr.t`/`sc.t` 同址 CAS 的正常路径与失败路径各至少 1 条；`make check-inst-asm` 含新向量并通过。
3. **可达 FAIL**：回退修复 ⇒ 新向量判红；`cp`+md5 还原 ⇒ 回绿。
4. 不回归：`make check-inst-asm`、`check-qemu-*`（既有 qemu 门控）、`check-tset-libc-smoke`、`check-linux-k6` rc=0；`make check` 与基线逐行相同。
5. `ISS-497`/`ISS-499` 的窄 CAS 结论在完成区交叉引用（不需重开）。
6. `ISS-501` 关闭；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/qemu/**`（补丁 + changelog）、`tests/inst/**`（新向量；`tests/inst.yaml` 索引）、`tests/unit/qemu/**`、`.tao/knowledge/issues.yaml`、本任务书。
3. 不改内核/musl/busybox；不改版本号；术语「bank = 寄存器组」；大端语义按 `MEMORY.md`。
4. 组件补丁经 `make_patch.py qemu` 重导；`check-patch-tree` qemu 段与基线逐行相同（`ISS-507` KNOWN-RED 判据）。
5. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

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
