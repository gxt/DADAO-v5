# m16-testcases-005: 签名脚本迁 `tests/shared/`

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（与 `m16-testcases-004` 可并行）
**可并行分片**：否（机械迁移，单点收口）
**预估**：小（机械迁移）
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-22 裁定）

签名机制要集中到 `tests/shared/`：汇编侧 `tests/shared/asm/signature.inc` 已在该处，host 侧 `tools/testcases/lib/signature.py` 仍在 `tools/` 下。用户要求「签名区的脚本移动到 `tests/shared` 目录下」，避免 `tools/` 继续膨胀。

## 要做

1. `tools/testcases/lib/signature.py` → `tests/shared/signature.py`（保留文件内容与 API，只改必要的路径注释）。
2. 更新全部引用（现场至少 6 处，以 `git grep -n "testcases/lib"` 与 `grep -rn "import signature"` 现场核实为准）：
   - `tests/ee-tiny/run_inst_tiny.py`
   - `tools/testcases/arch/min_rom_probe_tlb.py`
   - `tools/testcases/arch/node_probe_prelude.py`
   - `tools/testcases/inst/check_inst_sig.py`
   - `tools/testcases/lib/inst_expected.py`
   - `tools/idl/qemu_final_state.py`
   以及 `sys.path` 插入点、`__pycache__` 清理。
3. 更新说明文档：`tests/shared/README.md`（谁用）、`tests/arch/README.md`（host 侧路径）。
4. 删除旧文件 `tools/testcases/lib/signature.py`，不留转发壳（避免两份实现）。

## 不做

- 不改 `signature.py` 的语义/API；
- 不改 `tests/shared/asm/signature.inc`；
- 不动其它 `tools/testcases/lib/*` 文件。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集 = {本任务书, `tests/shared/signature.py`, 6 处引用文件, 两份 README, 删除旧文件}；不改组件源码；
- 不写运行期路径到入库文件；
- 逐项 staging 语义（本任务不提交，只保证完成区清单与 `git status` 对账）。

## 验证

运行期证据目录内的 `run.sh`，至少检查：

1. `tests/shared/signature.py` 存在，导入成功（`python3 -c "import signature"` 在 `tests/shared` 下）；
2. 全仓 `grep -rn "testcases/lib/signature"` 0 命中（排除 `.tao/archive/**` 与历史任务书）；
3. 迁移前后同一输入/期望的 `parse`/`compare` 结果逐字节相同（构造固定 blob，本地断言）；
4. `check-inst-asm` 代表册（01 册）与 `check-arch-smoke` 冒烟跑通，记录 rc；
5. `--inject` 1 路（把旧路径写回一个引用）⇒ FAIL，`cp`+md5 还原后回绿；
6. `make check-knowledge-refs` 与 `make check-tasks` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
