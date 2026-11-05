# INFRA-125t: embench-iot/libc-test 补丁集迁入 tests/tset

**模块**：infra
**项目里程碑**：M11
**依赖**：`TESTCASES-100t`（已验证；libc-test 补丁集）、`INFRA-123t`（已验证；DDLN 规则）
**状态**：待开始

## 执行环境
本地；移动测试集补丁资产与 manifest 路径，不改上游 commit、不改测试语义。

## 用户裁定（2026-11-05）

> 「我要把 components/embench-iot 目录和 components/libc-test 目录清理掉，这些内容应该放在 tests/tset 下面，并且已经有这两个测试集的对应目录了」

## 现状

`components/` 下有两个测试集的补丁资产：

- `components/embench-iot/`
  - `patches/examples/dadao/{README,boardsupport.c,boardsupport.h}.patch`
  - `patches/src/md5sum/md5.c.patch`
  - `series`、`README.md`、`changelog.md`
- `components/libc-test/`
  - `patches/src/regression/malloc-brk-fail.c.patch`
  - `series`、`README.md`、`changelog.md`

`tests/tset/embench` 与 `tests/tset/libc-test` 已存在，前者是 Embench 用户态驱动/板级 shim，后者目前只有 README。

## 目标

1. 把两个补丁集整体迁到现有 tset 目录：
   - `components/embench-iot/patches/**` → `tests/tset/embench/patches/**`
   - `components/embench-iot/series` → `tests/tset/embench/series`
   - `components/embench-iot/changelog.md` → `tests/tset/embench/changelog.md`
   - `components/embench-iot/README.md` → 合并进 `tests/tset/embench/README.md`
   - `components/libc-test/patches/**` → `tests/tset/libc-test/patches/**`
   - `components/libc-test/series` → `tests/tset/libc-test/series`
   - `components/libc-test/changelog.md` → `tests/tset/libc-test/changelog.md`
   - `components/libc-test/README.md` → 合并进 `tests/tset/libc-test/README.md`
2. 删除 `components/embench-iot/` 与 `components/libc-test/` 目录。
3. `manifests/components.lock.toml`：
   - 两个 component 的 upstream `commit`/`repository` 不变；
   - `patch_dir`/`patch_series` 改为 `tests/tset/{embench,libc-test}/...`；
   - 注释/role 同步，不再说“components 下”。
4. 更新依赖这些路径的活文件：
   - `tools/testcases/tset/embench/run_embench_user_suite.py`
   - `tools/testcases/tset/libc-test/run_libc_test_user_suite.py`
   - `tests/tset/embench/embench_user_boardsupport.c` 注释
   - `tools/infra/check_patch_tree.py` 文档字符串中 `components/<name>/series` 的旧措辞
   - `ADR-0022` 的历史位置指针加 `rev. 2026-11-05` 注记（不改决策）
5. `check-component-changelog.py`：
   - 扫描面从仅 `components/*/changelog.md` 扩为 `components/*/changelog.md` + `tests/tset/*/changelog.md`；
   - 保持 5 条形态断言；不得 vacuous PASS；
   - self-test 覆盖新扫描面。
6. 不改上游源树内容、不改补丁语义、不改测试判据。

## 范围 / 非范围

**在范围内**：`components/embench-iot/**`、`components/libc-test/**`（删除）、`tests/tset/embench/**`、`tests/tset/libc-test/**`、`manifests/components.lock.toml`、`tools/infra/check_component_changelog.py`、`tools/infra/check_patch_tree.py`（仅注释）、`tools/testcases/tset/{embench,libc-test}/*.py`（仅路径/文案）、`.tao/adr/adr-0022-embench-upstream.md`（仅指针/rev）、本任务书、`milestones.md`。

**不在范围内**：`components/qemu/**`、`components/gem5/**`、其它 `components/**`、`spec/**`、`contracts/**`、QEMU/gem5 实现、测试期望值。

## 验收标准

1. `components/embench-iot`、`components/libc-test` 不存在；对应 `tests/tset/{embench,libc-test}` 含 patches/series/changelog/README。
2. `manifests/components.lock.toml` 的 patch_dir/series 指向新路径；`manifest_check` rc=0。
3. `check-patch-tree`/`check-index-blobs` rc=0；源树 base+1 不变；`apply-series`/`check-source-state` rc=0。
4. `check-component-changelog` 扫描面含 `tests/tset/*/changelog.md`，5 条断言全绿，非 vacuous。
5. `make check-tset-embench-smoke`、`make check-tset-libc-smoke`（或现场可用等价）rc=0；L1 rc=0。
6. 活文件对 `components/embench-iot`/`components/libc-test` 的引用 0 命中（历史归档/任务书除外）。
7. 反例：把 manifest patch_dir 改回旧路径或删除一个 tset changelog ⇒ 门控 FAIL；`cp`+`md5sum -c` 还原回绿。
8. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是资产位置迁移，不是组件删除：upstream commit lock 保留，只是补丁集归 `tests/tset`。
- `check-component-changelog` 扩展扫描面时，不能把 `tests/tset/*/changelog.md` 排除；否则新位置无人校验。
- 先移动、改 manifest，再改生成/门控；最后删除空 components 目录。
- 与 `INTEG-054t` 并行时只改不同文件；若 `make check` 因并发构建红，区分环境红并重试。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
