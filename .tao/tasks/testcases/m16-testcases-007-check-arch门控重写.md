# m16-testcases-007: `check-arch` / `check-arch-smoke` 按新 `tests/arch` 重写

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-006`（`run_arch.py` 骨架）已合入
**可并行分片**：否（共享 Makefile）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22 裁定）

`check-arch-smoke` 要按新的 `tests/arch` 重写；`check-arch` **与 `check-arch-smoke` 一致**（同一代表集），L3 的 arch 成员保留，不再跑旧的 15 个 `ARCH_CFX_PROBES` min-ROM 探针（文件保留，后续 cfx4 迁移任务处理）。

## 要做

1. **代表集来源**：从 `tests/arch.yaml` 的 `level: smoke` 条目现场派生（不写死条数），经 `tests/arch/run_arch.py --level smoke --platforms qemu --cache-model on` 执行（arch 固定 on，off 会 rc=2）；输出 rc 与逐 case 签名结果。
2. **`check-arch-smoke`**：Makefile 的 `_locked-check-arch-smoke` 改为调用上述命令；保留 25 服务覆盖（`min_rom_probe_046t`）作为 smoke 的一部分。
3. **`check-arch`**：与 `check-arch-smoke` **一致**——同一 recipe（别名或直接复用），不再遍历 `ARCH_CFX_PROBES`；L3 的 `l3_run.DEFAULT_MEMBERS` 仍指向 `make check-arch`，`check-l3-report` 四 scope 覆盖不变。
4. **旧探针**：`ARCH_CFX_PROBES` 变量保留（010 后 14 项），对应 min-ROM 探针文件保留，但不再被 `check-arch` 调用；在 Makefile 注释与 `tests/arch/README.md` 写明"待 cfx4 迁移任务处理"。
5. **fail-closed**：代表集为空、`run_arch.py` 缺失、case 失败都必须非零；不得 `|| true`。

## 不做

- 不删旧探针文件、不改其判据；
- 不新增 cfx 语义用例；
- 不改 `tests/arch.yaml` 的条目语义（只读 level）；
- 不改 Process-07/09（004 已改）。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集限 `Makefile`、`tests/arch/README.md`、`tests/arch/run_arch.py`（若需 `--level`）、本任务书；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-arch-smoke` 与 `make check-arch` 均 rc=0；**结构断言**：`_locked-check-arch` 只有「依赖 `check-arch-smoke` + echo」、无其它 recipe 行（两次 `run.json` 相同属同源拷贝，不能单独作证据）；
2. 代表集条数现场派生，与 `tests/arch.yaml` 的 smoke 条目数一致；**可达 FAIL 用「清空代表集 ⇒ rc=2」或「删载体 ⇒ rc=2」**（删 1 条后仍 9 条会绿，不作判据）；
3. 旧 `ARCH_CFX_PROBES` 不再被 `check-arch` 调用（日志无 min-ROM probe）；**15 个 min-ROM 探针文件保留**（010 已删 `min_rom_probe_tlb.py`，以合并后 master 为准）；
4. `make check-tests-index`、`make check-tasks`、`make check-knowledge-refs` 记录 rc；
5. **签名流口径**：`run_arch.py --case arch-ptw-002` 改错一槽 ⇒ `rc=1`；smoke 的 10 条 umon 无签名流，签名门控归 carrier（L3），**不要求 smoke 红**；
6. `--inject` ≥2 路；
7. **合并处置（010 已合入 master `a388baa4`）**：把 `ARCH_PTW_CARRIER = tests/arch/ptw/carrier_tlb.py` 的调用**并入 `_locked-check-arch-smoke`**（让两目标同跑、维持「一致」裁定）；`ARCH_CFX_PROBES` 取 010 版（14 项、无 `tlb`）；`run_arch.py`/`README` 保留 010 的 gem5/`cross_platform` 改动；合并后重跑 `check-arch-smoke` 与 `check-arch`。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
