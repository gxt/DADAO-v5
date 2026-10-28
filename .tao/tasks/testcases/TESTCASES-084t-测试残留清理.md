# TESTCASES-084t: 测试残留清理（e2e/llvm 链接/wrapper/spec 路径）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-076t（已 `已验证`）
**状态**：待开始

## 背景
`076t` 收口后仍有旧口径残留：

- `tests/e2e/`（31 个工具链 E2E `.c/.s/.lds` + `lit/`）不在四 scope；当前仍被 `check-lit` 的 Makefile 引用；
- `tests/llvm/` 只剩 `lit`/`codegen`/`ir-lli` 三个兼容符号链接；`tools/llvm` 部分默认路径仍指向它；
- `tools/qemu/min_rom_probe_*`（32 个）是 `073t` 留下的薄 wrapper，真实实现在 `tools/testcases/arch/`；
- `spec/README.md` 仍有 `tests/e2e`、`tools/integ/check_interface_alignment.py` 旧路径（`spec/` 只读锁，用户 2026-10-27 已授权修改）；
- 4 个组件补丁注释仍引用旧测试路径（`tests/scripts`/`tools/integ`）；
- 5 个 `.gitkeep`、若干 `__pycache__` 为冗余/运行垃圾。

## 目标
1. **e2e 归位**：`tests/e2e/` → `tests/unit/llvm/e2e/`（工具链 E2E 属 unit/lit）；更新 Makefile `check-lit`、`tests/e2e/lit/lit.cfg.py` 相对路径、`tests/unit/llvm/lit` 引用、README/INVENTORY。
2. **删除 `tests/llvm` 符号链接**：先把 `tools/llvm/{check_lit_bytes,gen_isa_coverage,...}` 默认路径改到 `tests/unit/llvm/...`，重生成 ISA 矩阵，再删链接。
3. **删除 32 个 `tools/qemu/min_rom_probe_*` wrapper**：确认 `tools/testcases/arch/` 原件可用、引用已改；保留旧命令说明或删除。
4. **spec/README**：`tests/e2e` → `tests/unit/llvm/e2e`；`tools/integ/...` → `tools/infra/...`；更新 `manifests/spec-readonly.lock.toml` 的 sha（用户已授权）。
5. **组件补丁注释**：4 个 patch 文件里的旧路径改为语义说明（不交叉引用测试路径），重新生成补丁树并 `check-patch-tree`。
6. **清垃圾**：删 5 个 `.gitkeep`、`__pycache__`；确认无断链。
7. 不改测试期望/断言；只做路径/归属/注释清理。

## 验收
- `tests/e2e/`、`tests/llvm/` 不存在；`tools/qemu/min_rom_probe_*` 0 个；旧路径代码/配置面 grep 0；
- `make check` rc=0；`make check-modules` rc=0；`check-tests-index`/`check-case-ledger` rc=0；`check-patch-tree` rc=0；`check-spec-readonly` rc=0；
- `check-lit` 全绿（当前 158 基线，现场统计）；e2e 用例从新路径可跑；
- 证据 `.work/evidence/<任务号>/run.sh`（注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-084t/`。

## 约束
- 只改测试/路径/文档/补丁注释；不改 spec 正文语义、不改 QEMU/LLVM 语义。
- **不跑 `check-full`/夜跑**；长构建申报。
- **不提交、不 push**；`spec/` 修改须同步锁 sha。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
