# m18-linux-010: ISS-486 措辞订正（libc 侧检查）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-infra-002`（musl 组件写者；避免与 ldso 任务并发改同一组件）
**可并行分片**：否
**预估**：30 min（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为 3 处注释/文档措辞订正，按 1/3 中位）
**档位**：小改（注释与文档）
**状态**：待开始
**执行环境**：本地

## 背景

`ISS-486`【P3】（`m14-infra-005` 复核登记，非阻断）：两处措辞把 libc 行为归给内核。

- 任务书 `m14-infra-005` 的「新发现①」写「建议内核侧确认 `do_sigaltstack` 的 `min_ss_size`」，实际是 musl `src/signal/sigaltstack.c` 的 `sysconf(_SC_MINSIGSTKSZ)` 在用户态先拦（`MINSIGSTKSZ=2376`），内核那条轮不到；engineer 建议已撤销。
- `components/musl/patches/arch/dadao/bits/signal.h.patch` 与 `tools/infra/musl_sigframe_probe*.{py,c}` 头注释里「kernel refuses / kernel's bounds rules」同源措辞。

## 目标

把上述 3 处改为「libc 侧检查」口径；**不动判据与实现**。

## 验收（逐条贴真实 rc）

1. 3 处措辞逐条订正，`grep -rn "kernel refuses\|kernel's bounds rules"` 在允许范围内 0 命中（历史归档文件除外，逐条说明）。
2. `make build-musl` rc=0；`libc.a` 与改前 md5 相同（仅注释，产物不应变）。
3. `check-patch-tree` 的 musl 段与基线**逐行相同**（`ISS-507` KNOWN-RED 判据）；`check-component-changelog` rc=0。
4. `ISS-486` 在 `issues.yaml` 关闭（`closed_in: M18`、`resolved_by` 指向本任务）。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/musl/patches/arch/dadao/bits/signal.h.patch`、`components/musl/changelog.md`（如需）、`tools/infra/musl_sigframe_probe*.{py,c}`、`.tao/knowledge/issues.yaml`、本任务书。
3. 不改版本号；不改判据/实现；术语「bank = 寄存器组」。
4. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`。

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
