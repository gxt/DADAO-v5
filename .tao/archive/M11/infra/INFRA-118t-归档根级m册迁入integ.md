# INFRA-118t: 归档根级 m 册迁入 integ

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-116t` / `INFRA-117t`
**状态**：已验证

## 用户授权

用户 2026-11-01：`.tao/archive/M9/` 根目录多出 `INTEG-037m-M9里程碑核验.md`；经确认，**M9/M10 两个根级 m 册都移入各自的 `integ/`**，归档根只保留三件套 + 模块任务书。

## 目标

1. `git mv`：
   - `.tao/archive/M9/INTEG-037m-M9里程碑核验.md` → `.tao/archive/M9/integ/INTEG-037m-M9里程碑核验.md`
   - `.tao/archive/M10/INTEG-052m-M10里程碑核验.md` → `.tao/archive/M10/integ/INTEG-052m-M10里程碑核验.md`
2. README 同步：
   - M9 §1 增加 `integ | 1`，总数 68→69，去掉「根级 `INTEG-037m`」措辞。
   - M10 §1 将 `integ` 14→15，去掉「integ（核验册，顶层）|1」特殊行（总数仍 71）。
   - 两册 §2 流水不变（M9 含 m、M10 不含 m 的既有口径不变）。
3. 门控/规范：
   - `check_archive.py` 删除根级 `INTEG-*m` 历史例外；m 册统一在模块目录；流水 ID 允许「t 册集合」或「t 册 + m 册集合」。
   - `docs/Process-04 §5` 根级只允许三件套；`docs/Process-07` 同步。
   - `--self-test` 保留可达 FAIL；新增/调整根级 m 拒收或 m 可选流水断言。
4. **不改**任何归档任务书内容、不增删 m、不改流水数据、不改 spec/contracts/代码。

## 文件范围

- `.tao/archive/M9/README.md`、`.tao/archive/M10/README.md`
- M9/M10 两个根级 m 册的 `git mv`
- `tools/infra/check_archive.py`、`Makefile`（仅注释）、`docs/Process-04`、`docs/Process-07`
- 本任务书、`.tao/knowledge/milestones.md`

## 验收

1. `find .tao/archive/M9 .tao/archive/M10 -maxdepth 1 -type f` 只有三件套；m 册在 `integ/`。
2. M9 README 模块计数 `integ=1`、总 69；M10 `integ=15`、总 71；`check_archive` 严格 rc=0。
3. `check_archive.py --self-test` rc=0；根级 `INTEG-*m` 注入可达 FAIL；m 在模块内且流水缺 m 的 M10 形态可达 PASS。
4. `make check` L1 rc=0；`check_milestones_fresh` rc=0；`check_tasks --strict` rc=0（收尾后）。
5. 证据 `运行期证据脚本（已清理，未归档）` 一键重跑；反例注入 `cp`+md5 还原；不跑夜跑。
6. 任务书完成区 ≤30 行、状态 `已验证`；milestones 行同步。

## 完成区

**测试结果**：`运行期证据脚本（已清理，未归档）` 12/12 PASS、rc=0；`check_archive` 严格 rc=0、self-test 14/14；`make check` rc=0；`check_milestones_fresh` rc=0；`check_tasks --strict` rc=0；根级 m 注入 rc=1 并已移除。
**修改文件**：M9/M10 README；M9/M10 根级 m 册 `git mv` 到各自 `integ/`；`tools/infra/check_archive.py`；`Makefile`（注释）；`docs/Process-04`/`docs/Process-07`；本任务书；`milestones.md`。
**验收结果**：M9/M10 根级均只有 README/retro/issues 三件套；M9 `integ=1` 总数 69，M10 `integ=15` 总数 71；流水 69/70 不变；`check_archive` 严格 PASS；m 册均在模块目录。
**新发现/坑**：check_archive 原「根级 m 历史例外」与「流水 ID == 全部任务书集合」需同时改：m 册移入 integ 后成为模块册，流水必须允许「t 集合」或「t+m 集合」；已按此实现并加根级 m 注入反例。
**遗留问题**：无。

## 审阅记录
