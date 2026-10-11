# Picolibc 组件（picolibc）

DADAO 的 C 库组件（**M7 test 重心**：picolibc 自带 test 套件）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定（`shallow_ref = "release-1.8.12"`，精确 commit `2ae376c6…`）；工作树由 `make fetch` + `make apply-series` 在 `.work/source/picolibc` 建立（**浅裸镜像** `.cache/picolibc.git`）。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`。
- 规范：`spec/Process-01-组件补丁组织与构建编排.md`；上位决策：`ADR-0005`（多源锁）、`ADR-0006`（浅裸镜像）。
- 现状（`INFRA-055t`）：**骨架占位**——`dadao/README.md`（**声明无行为**，真移植（board/machine 支持、cross file、syscall stub、构建集成）归 **M7**）。
- **test 重心**：picolibc 自带 `test/` 目录随 `make fetch` 一并检出，供 M7 规划"以 picolibc 自带 test 为主"的测试向量与门控。

## 校验

```
make check              # 含 check-patch-tree（9 断言）+ check-index-blobs
python3 tools/infra/check_patch_tree.py
```
