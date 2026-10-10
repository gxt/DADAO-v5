# Embench-iot 组件（embench-iot）

DADAO 的 Embench-iot 基准组件（M6 编译正确性测试）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定（`ADR-0022`：上游 `embench/embench-iot`，精确 commit）；工作树由 `make fetch` + `make apply-series` 在 `.work/source/embench-iot` 建立。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`。
- 规范：`spec/Process-01-组件补丁组织与构建编排.md`；上位决策：`ADR-0002 D4`、`ADR-0022`。
- 现状（`INFRA-051t` + `TESTCASES-039t`）：**DADAO 板级接入**——`examples/dadao/boardsupport.c`（board shim 3 函数）+ `src/md5sum/md5.c`（大端适配）。
- **最小运行时**（`mem*`/`str*`/`ctype`/`sqrt`，不引 libc）落 `tests/scripts/`：`dadao_mem_runtime.ll`（`mem*`，复用）+ `embench_runtime.c`（`str*`/`ctype`/`sqrt`/`abort`）+ `embench_include/`（freestanding 头）。

## 校验

```
make check              # 含 check-patch-tree（9 断言）+ check-index-blobs
python3 tools/infra/check_patch_tree.py
```
