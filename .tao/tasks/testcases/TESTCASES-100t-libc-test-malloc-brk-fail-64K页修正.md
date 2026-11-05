# TESTCASES-100t: libc-test malloc-brk-fail 64K 页可移植性修正

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-099t`（已验证；根因 = musl dynamic 启动堆/64K 页 LOAD 空洞）、`TESTCASES-076t`（夜跑）、`TESTCASES-083t`（libc-test 驱动）
**状态**：待开始

## 执行环境
本地；改 libc-test 语料 + 组件补丁策略，不改 spec/QEMU/gem5。

## 背景

`regression/malloc-brk-fail` dynamic 在 DADAO 64K 页上失败：

- libc.so LOAD 段之间有 54880 B 的 64K 对齐空洞
- musl dynamic loader `reclaim_gaps` 把空洞捐给 mallocng
- `malloc(10000)` 直接落在该空洞，无 brk/mmap 系统调用
- 测试假设“填满 VA + RLIMIT_DATA=0 后 malloc 必失败”不成立

4K 页 ISA 的空洞 <4K，`malloc(10000)` 放不进去，测试通过；64K 页系统会失败。属测试可移植性问题。

## 目标（C 方案）

在 libc-test 语料侧修正，使测试对 64K 页也成立：

1. 把 `libc-test` 从 `patchless = true` 转为受补丁组件：
   - `manifests/components.lock.toml`：`patchless = false`、`patch_dir`、`patch_series`、role 注记
   - `components/libc-test/series`、`components/libc-test/patches/src/regression/malloc-brk-fail.c.patch`
2. 补丁在测试开始、`t_vmfill` 之前**消耗 dynamic loader 捐赠的启动堆**：
   - 申请并保留若干块，确保 64K 空洞被占用（例如先 `malloc(50000)`，再 `malloc(10000)`；按 64K 页/4K 页都成立）
   - 不改变测试断言、magic、退出码、`t_vmfill`/`t_setrlim` 逻辑
   - 注释写明“64K 页 dynamic loader gap”原因
3. 源树 base+1 干净；补丁由 `make apply-series` 应用；`check-source-state`/`check-patch-tree` 通过。
4. 重跑 libc-test static/dynamic full、`make check`（L1）、`make check-night`（或至少 `tset:libc-test` + `check-night-report`），确认夜跑转绿。

## 接口规范

- 补丁只改 `src/regression/malloc-brk-fail.c`；一文件一补丁，符合 `docs/Process-01`。
- 不修改测试的 `t_error`/`t_status` 语义；不跳过测试；不降低覆盖。
- `components/libc-test/changelog.md`（若存在）记录补丁原因与 commit。
- 不改 `tests/tset` 驱动的 judge 逻辑；不改 spec/QEMU/gem5/musl。

## 范围 / 非范围

**在范围内**：`manifests/components.lock.toml`（仅 libc-test 条目）、`components/libc-test/**`、本任务书、`milestones.md`、运行期证据。

**不在范围内**：`spec/**`、`.tao/contracts/**`、`contracts/**`、`components/qemu/**`、`components/gem5/**`、`components/musl/**`、`tests/**` 其它文件、`tools/testcases/tset/**` 判据。

## 验收标准

1. **补丁生效**：`.work/source/libc-test` 为 base+1；`git diff` 仅 `malloc-brk-fail.c`；`make apply-series`/`check-source-state`/`check-patch-tree` rc=0。
2. **64K 页通过**：`make check-tset-libc-full` static+dynamic rc=0；`malloc-brk-fail` dynamic 不再报“malloc succeeded after memory is filled”。
3. **4K 页不退化**：补丁在 4K 页布局下仍保持原测试语义（prime 只消耗堆，不改变断言）；无法现场跑 4K 页时，用静态推理 + 代码审查说明。
4. **夜跑转绿**：`make check-night`（或等价 libc-test full + 其它三项）后 `check-night-report` rc=0；若只跑 libc-test，须说明其余三项沿用上一轮结果，不得伪称 full green。
5. **门控**：`make check`（L1）rc=0；`check-components`/`check-source-state`/`check-patch-tree` rc=0；`check-run-artifacts` rc=0。
6. **反例可达 FAIL**：删补丁中的 prime/回退原语义 ⇒ dynamic 用例 FAIL；`cp`+`md5sum -c` 还原后回绿。
7. **范围**：无 spec/QEMU/gem5/musl 改动；完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是**测试输入侧**的可移植性修正，不是放宽判据；static 仍覆盖原行为，dynamic 仍执行同一用例。
- 若 prime 方案在 4K/64K 页上无法同时成立，保留现场并留问；不改成“dynamic 排除”或 known-fail。
- 修改 `patchless` 属组件策略变更，须在完成区明确记录；不改 libc-test 的 lock commit。

## 未决（下发前确认）

1. prime 大小/数量：默认 `malloc(50000)` + `malloc(10000)` 保留；若 64K 空洞 class 不同，按现场调整并记录。
2. 是否要求本任务直接跑完整 `check-night`（小时级）；默认先跑 libc-test full，再按 M11 收口跑 night。
3. `components/libc-test/changelog.md` 是否存在；不存在则在任务书完成区记录。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
