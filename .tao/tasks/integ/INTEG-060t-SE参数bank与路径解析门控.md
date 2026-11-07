# INTEG-060t: gem5 SE syscall 参数 bank 与路径解析门控

**模块**：integ
**项目里程碑**：M11
**依赖**：`GEM5-026t`（线程/TLS；同改 gem5 补丁，须先合并）
**状态**：待开始

## 背景与事实

- musl 以 `__dadao_argmask(nr)` 决定「第 i 个参数进 RD 还是 RB」：指针走 RB、标量走 RD，两 bank 各自从 16 计数；QEMU 有同表副本，`tools/qemu/check_syscall_abi.py` 断言两侧**逐项相等**
- **gem5 SE 没有这张表**：每个 syscall 在 `switch` 里手写 `rd(16)`/`rb(16)`，写错 bank 不会触发任何门控
- 真实案例：`fcntl` 的锁指针原取 `rb16`，实际 musl mask 为全 RD，`GEM5-023t` 自审才发现并改为 `rd18`
- 路径解析：`resolveGuestPath()` 对「相对路径 + dirfd」用打开时记录的 guest 名拼接，再走 redirect；`..` 未归一化，空路径/`AT_EMPTY_PATH` 分支无专门探针

## 目标

1. **参数表统一**：在 gem5 SE 侧引入与 musl 同源的 `argmask` 表（或等价的「按 mask 取第 i 个参数」封装），dispatch 统一通过它取参，删除逐处手写的 bank 选择。
2. **三方门控**：`tools/qemu/check_syscall_abi.py` 扩为 musl / QEMU / gem5 三方逐项相等；新增/修改 syscall 时三方必须同时更新，否则门控红。
3. **路径解析探针**：覆盖绝对路径 + 非 `AT_FDCWD` dirfd（应忽略 dirfd）、相对路径 + dirfd（经 redirect）、`..` 归一化、空路径/`AT_EMPTY_PATH`、`/` 与非 `/` 结尾；与宿主 Linux 逐项对照。
4. 不改测试用例与期望；不改 QEMU 语义。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.cc,se_workload.hh}`（取参封装与 mask 表）、`tools/qemu/check_syscall_abi.py`（三方校验）、`tools/testcases/**` 的 SE 探针（路径解析）、本任务书、`milestones.md`。

**不在范围**：新增 syscall 语义（前序任务）、QEMU 实现、测试用例与期望、`spec/contracts`。

## 验收标准

1. gem5 侧的 mask 表与 musl/QEMU **逐项相等**（含 0x00 条目）；门控 rc=0。
2. 反例：把任一 syscall 的 mask 改错（或 dispatch 改成读另一个 bank）⇒ 门控/探针 FAIL；`cp`+`md5sum -c` 还原重建后回绿（禁 git 还原）。
3. 路径探针全绿：绝对+dirfd、相对+dirfd+redirect、`..`、空路径/`AT_EMPTY_PATH`；与宿主 Linux 结果一致。
4. 基线不退化：`GEM5-025t` 的 static 基线复跑 pass/blocked 不下降（环境缺口与 bison 例外保持登记）。
5. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是「防回归」任务，不新增能力；目的是让 rd/rb 混用与路径拼接错误**在门控里红**，而不是事后靠失败样本猜。
- 若发现某 syscall 的 mask 在 musl/QEMU 本身就分歧，先停下提交（不得自行选一边）。
