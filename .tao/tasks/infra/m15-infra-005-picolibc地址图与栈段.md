# m15-infra-005: picolibc 的 Tiny 地址图与栈段（删掉仓库里的 lds 副本）

**模块**：infra
**项目里程碑**：M15
**依赖**：无
**可并行分片**：否（组件补丁 + 测试驱动 + 门控）
**预估**：0.5 h
**档位**：小改（组件补丁语义 + 测试资产删除）
**状态**：已验证

## 背景（用户 2026-11-21）

`tests/ee-tiny/tests_picolibc_tiny.lds` 是 `picolibc_noflash.ld` 的 513 行副本（491 行上游 + 22 行改动），之所以存在，是因为：
1. cross 文件里的默认内存图是移植期占位 `0xfc0000000000`/16 MiB，不是 Tiny；
2. 上游模板把 `.stack` 放在 `:ram`，导致单个 `PT_LOAD` 的 `memsz` 覆盖整个 RAM（chipyard `+loadmem` 要推几 MB 零字）。

用户裁定：把 cross 文件改对，删掉副本。

## 要做

1. `components/picolibc/patches/scripts/cross-dadao.txt.patch`：默认值改 Tiny 地址图（flash `0xffffffff0000`/64 KiB、ram `0xffffff010100`/`0x007dfe00` ⇒ 派生 `__stack = 0xffffff7eff00`）；
2. `picolibc.ld.in`：`.stack` 从 `:ram` 改为 `:NONE`（不进入任何 `PT_LOAD`）；
3. 删除 `tests/ee-tiny/tests_picolibc_tiny.lds`；`run_picolibc_tiny.py` 的 `PICOLIBC_LDS` 直接指向安装版 `SYSROOT/lib/picolibc_noflash.ld`；
4. `check_tests_index.py` 的 picolibc 断言改为「harness 必须使用 `picolibc_noflash.ld`」。

## 验收（真实 rc）

1. `make build-picolibc` rc=0；安装版 `lib/picolibc_noflash.ld` 的 ram/flash 值与 `__stack` 派生正确；
2. 用安装版脚本链接 picolibc 程序：`_start = 0xffffff010100`、`__stack_bottom = 0xffffff7eef00`、`PT_LOAD memsz = 0xa70`（改前 `0x7dfe00`）；QEMU rc=0；
3. `make check-picolibc-tests`（fast）⇒ `fail=0, blocked=0`、rc=0；
4. `check-tests-index` PASS、`check-component-changelog` PASS、`check-knowledge-refs` PASS、`check-patch-tree` picolibc 段 0 问题（全局红仅来自在途 010/028 的共享源树）。

## 约束

组件补丁经源树编辑 → 单个本地 commit → `make_patch picolibc` 重导；不改 `spec/`、契约；术语「寄存器组」。

## 完成区

**测试结果**：
1. `make build-picolibc` rc=0（`libc.a` 2053170 B、`libsemihost.a` 71716 B）；安装版 `lib/picolibc_noflash.ld` 的 `ram ORIGIN=0xffffff010100`/`LENGTH=0x007dfe00`，派生 `__stack = 0xffffff7eff00`、`__stack_bottom = 0xffffff7eef00`。
2. 安装版脚本直链（picolibc `crt0-semihost` + `tests_picolibc_crt0.S` + `libc.a`/`libsemihost.a`）：链接 rc=0，`_start = 0xffffff010100`、`__stack_bottom = 0xffffff7eef00`；`PT_LOAD memsz = 0xa70`（改前 `0x7dfe00`）；QEMU `-machine kaiwu-tiny` 运行 rc=0。
3. `make check-picolibc-tests`（fast）：`total=20 pass=6 fail=0 excluded=0 blocked=0 skipped=14`、rc=0。
4. `check-tests-index` PASS（472 条）、`check-component-changelog` PASS、`check-knowledge-refs` PASS；`check-patch-tree` 的 picolibc 段 0 assertion（全局 rc 红仅来自在途 `m16-chipyard-010`/`m14-linux-028` 的共享 `.work/source`）。

**修改文件**：`components/picolibc/patches/scripts/cross-dadao.txt.patch`、新增 `components/picolibc/patches/picolibc.ld.in.patch`、`components/picolibc/{series,changelog.md}`；`tests/ee-tiny/run_picolibc_tiny.py`；删 `tests/ee-tiny/tests_picolibc_tiny.lds`；`tools/testcases/check_tests_index.py`；`tests/README.md`、`tests/shared/README.md`。
