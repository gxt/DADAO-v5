# tools/testcases — 测试驱动 / 生成器 / 共享工具登记

> **原子探针已退役**（`m13-testcases-050`，用户 2026-11-15 裁定 A）：
> `tests/inst/atomics/` 的 5 个 C 探针及其驱动 / oracle 两个脚本已删除。替代分工 = ① 指令层 RMW 合成序 → `tests/inst/00-isa-design/atomic_rmw.S`
> （`.S` 载体，L2 `check-inst-asm` 执行）；② 编译器语义层（`__atomic_*` builtin 与
> C11 `<stdatomic.h>` 的值语义、子字宽 RMW 邻域、`ISS-312`/`ISS-313` 回归）→
> `tests/unit/llvm/e2e/atomics_e2e.c` + `lit/atomics_e2e.test`（QEMU `kaiwu-tiny`
> 真跑，guest 退出码 = 判据）；③ 争用（ABA / 互斥计数 / `a_barrier`）与 `fence`
> 顺序强度 → **GAP 登记**（`tests/inst/MIGRATION.md`「多 hart / 内存序 GAP」，
> 挂 `ISS-440`/`ISS-443`）。

## YAML 向量生成器：**全部退役**（`m13-testcases-043`）

六个生成器（`generate_isa_vectors` / `generate_ctrl_br` /
`generate_ctrl_jump_call_ret` / `generate_misc` / `generate_bitcnt_vectors` /
`generate_rev_vectors`）与两个门控（`check-generator-sync`、`check-rev-vectors`）
已删除：它们的唯一产物 `tests/inst/**/*.yaml` 随 YAML 全退役删除（用户 2026-11-14
裁定）。现行向量载体 = `tests/inst/<册>/<id>.S`（期望值内联、由 L2 `check-inst-asm`
逐镜像执行），不再有「生成器 + 逐字节比对」这一层。

若需**新增**用例：直接写 `.S`（模板见 `tests/inst/01-load-store/*.S` 与
`tests/inst/macros/inst_test.inc`），再跑
`python3 tests/ee-tiny/run_inst_tiny.py --id <id> --platforms qemu`。

## 共享工具登记（路径 / 用途 / 入口 / 调用者）

- **路径**：`tools/testcases/lib/inst_expected.py`
  **用途**：从 `tests/inst/**/*.S` + 宏层派生「槽 → 期望值」（`__CHECK_*` 内联常量 / `WDATA` 数据区 / 运行期关系），并生成 `tests/data/inst-signature/{expected.tsv,inputs.sha256}`
  **入口**：`python3 tools/testcases/inst/check_inst_sig.py --write`（库 API：`derive`/`render_expected`/`render_inputs`）
  **调用者**：L2 `check-inst-sig`；期望值变更后重生成数据

- **路径**：`tools/testcases/inst/check_inst_sig.py`
  **用途**：签名区槽级门控（数据漂移 + 输入 sha256 + `case-ledger` 对账 + QEMU 逐槽比对；失败给「槽 N 期望/实际 + 来源 `.S:行`」；流缺失 ⇒ BLOCKED）
  **入口**：`make check-inst-sig`（L2）/ `python3 tools/testcases/inst/check_inst_sig.py --data-only`
  **调用者**：L2 `check-modules` / 任务收尾

- **路径**：`tools/testcases/tset/embench/progress.py`
  **用途**：跑批进度看板（只读节点日志的逐例完成行 + `ps` 的 `+loadmem=`，给 done / 在跑 + ETA / 未开始，末尾 `done/total` 与 `cycles/s`）
  **入口**：`python3 tools/testcases/tset/embench/progress.py --hosts <csv> [--expect-done N]`
  **调用者**：主会话 / 跑批值守（人工）；数据互补于 `run_embench_e2e.py --jsonl-out` 的增量行

## 历史缺陷（已修；回归断言随 `m13-testcases-050` 迁入 e2e）

`ISS-312`（`atomic-store-address`）与 `ISS-313`（`narrow-cas-sext`）随 `LLVM-121t`
返工修复。原 atomics 探针 oracle 的 XFAIL 登记机制（`selftest_xfail()`）已随探针退役删除，
两条回归改由 `tests/unit/llvm/e2e/atomics_e2e.c` 的**普通断言**承担（QEMU 真跑：
check 19 = 8 字节 `__atomic_store_n` 存**值**不存地址；check 20 = 1 字节
`compare_exchange` 比较值最高位置 1 时**必须成功**）。

原缺陷（存档）：
- `atomic-store-address`：`atomic_store`/`__atomic_store_n` 写共享对象时写入**对象地址**
  （后端 `LowerATOMIC_STORE` 取错 ATOMIC_STORE 操作数）。
- `narrow-cas-sext`：1/2/4 字节对象的 `compare_exchange`，比较值最高位置 1 时永不成功
  （提升后的 i64 比较值符号扩展 vs `lr.{b,w,t}` 零扩展）。
