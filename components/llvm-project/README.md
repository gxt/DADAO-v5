# LLVM 组件（llvm-project）

DADAO 的 LLVM 后端（MC 层 + 后续 CodeGen）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定；工作树由 `make fetch` + `make apply-series` 在 `.work/source/llvm-project` 建立。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`。
- 规范：`docs/spec/component-patching.md`；上位决策：`ADR-0002 D4`（rev. 2026-09-23）。
- 规模（2026-09-23 M1 重整后）：**36 份** = 新增 32 + 修改 4。
- 主要内容：`DADAO` target 注册与骨架、寄存器/指令 TableGen、AsmParser、反汇编器、`wyde-position` 操作数解析修复、ELF `e_flags` 设置；另有 4 处对上游既有文件的修改（`llvm/CMakeLists.txt`、`TargetParser/{Triple.h,Triple.cpp,TargetDataLayout.cpp}`）。

## 校验

```
make check              # 含 check-patch-tree（五断言）
python3 tools/infra/check_patch_tree.py
```
