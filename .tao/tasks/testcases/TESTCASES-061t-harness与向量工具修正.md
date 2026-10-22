# TESTCASES-061t: harness 与向量工具修正（失败路径可信化 + 工具去陈）

**模块**：testcases
**项目里程碑**：M9（**必须早于终局全量复跑**）
**依赖**：`SPEC-164t`（编码迁移已完成，历史探针里的 `0x77` 全部失效，须一并清理）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源（用户 2026-10-22：「issue 只装缺陷，M9 内尽量关」）

本册收口以下 7 条缺陷（全部为"工具/用例本身错"，非新功能）：

| issue | 一句话 |
|---|---|
| `ISS-309` | `build_test_binary.py` 的 `br.nz` 偏移按 `PC+4` 算，而 ISA 分支基准 = `PC + imm*4` ⇒ 失败时落到 semihosting trap |
| `ISS-319` | 超时路径打印 `Unknown exit code: 0x-6`（负数 `%x`） |
| `ISS-323` | `run_rnd_probe.py` 的 `seen` 在 `for fmt` 内重置 ⇒ 805 含 20 条重复计数 |
| `ISS-120` | `min_rom_probe_{006t,008t,009t,010t,013t,028t}.py` 群 FAIL（pre-existing 漂移） |
| `ISS-234` | `min_rom_probe_009t.py` 顶注/公式仍按已废止口径（`0x5A`=UNDI、`PC & ~0xFFF`） |
| `ISS-125`+`ISS-190` | 生成器 ↔ 已提交向量漂移（全量重跑会破坏 5 文件；`st.*` 源 = `rd0`） |
| `ISS-326` | `tests/llvm/ir-lli/manifest.yaml` 11 个未分类 `*.ll` + 1 悬空项 |

## 目标

1. **`ISS-309`（最高优先）**：`br.nz` 偏移按 `PC + imm*4` 计算；所有用例的 PASS/FAIL 分支落点重新对齐；补 1 条"故意失败"用例，断言落到 FAIL 标签而不是 semihosting trap。
2. `ISS-319`：负数退出码格式化（`0x-6` → `-6 (SIG...)` 或 `0xFFFFFFFA`），并用 1 条超时用例验证。
3. `ISS-323`：`seen` 移出 `for fmt`；计数去重后现场统计（不写死 805）；完成区数字与之对齐。
4. `ISS-120`/`234`：6 个探针按现行口径重跑并对齐；公式/顶注过时的直接改。
5. `ISS-125`/`190`：以生成器为准重生成向量，确保 `make` 幂等（二次运行零 diff）；`st.*` 源寄存器口径统一。
6. `ISS-326`：11 个 `.ll` 补分类（pass/fail + 依据），删悬空项；补一条"manifest ↔ 文件集合双向一致"断言（可进门控）。
7. **编码残留清理**（`SPEC-164t` 遗留）：`tools/qemu/min_rom_probe_*.py` 与 `tests/scripts/**` 中 `0x77`/`0x77000000`/`0111-0111` 残留全部改 `0x47` 系（`OPC-MISC` 迁移后旧值已失效）；改完 `grep -rn '0x77' tools/ tests/` 仅允许出现在无关上下文（逐条判定并记录）。

## 验收

1. `ISS-309` 复现用例：改前落 semihosting trap、改后落 FAIL 标签（两条真实输出贴完成区）。
2. `run_rnd_probe.py` 输出计数 = 去重后唯一用例数（现场统计）；报告里不再有重复项。
3. 6 个探针直跑 PASS（逐个 rc=0）。
4. 生成器二次运行 `git status --porcelain` **无变化**（幂等）。
5. `ir-lli` 集合与 manifest **双向相等**（文件 ⊆ 条目、条目 ⊆ 文件）。
6. `make check`(L1) + `make check-modules`(L2) 绿；`validate-vectors` 绿。
7. **可达 FAIL ≥3**：① 回退 `br.nz` 修复 ⇒ 故意失败用例落到 trap（红）；② 重复一条用例 ⇒ 去重计数断言红；③ 给 manifest 加一条悬空 ⇒ 双向一致断言红。

## 接口规范

- **输入**：`tests/scripts/**`、`tests/vectors/**`、`tools/testcases/**`、`tools/qemu/min_rom_probe_*.py`、`tests/llvm/ir-lli/**`。
- **输出**：修正后的 harness/工具 + 重生成的向量 + manifest 补全。
- **约束**：不改 ISA 语义、不改 QEMU/LLVM 实现；不 commit/push；临时目录 `/tmp/opencode/TESTCASES-061t/`。

## 风险与纪律

- 修正 `br.nz` 会让**所有**失败路径行为改变 ⇒ 必须全量重跑受影响的用例集（不是抽样）。
- 重生成向量前先备份到 `.work/<任务ID>/before/`，逐文件 diff 审阅，禁 `git checkout` 还原。
- 若某条 issue 的根因实为 QEMU/LLVM 缺陷 ⇒ 停下报告，不在此册硬改。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
