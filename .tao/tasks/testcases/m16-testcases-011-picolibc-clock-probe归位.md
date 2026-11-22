# m16-testcases-011: picolibc clock 探针归位

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（`m15-infra-010` 已合入）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景

`tests/ee-tiny/ansibench_clock_probe.c` 与 ansibench 四件没有依赖关系：它只比较 `clock()/CLOCKS_PER_SEC` 与 `gettimeofday()`（ADR-0058 D5 ①），验证 picolibc `times()` 按 `SYS_TICKFREQ` 缩放（`m15-infra-010`，ISS-502 已闭合）。现在它被塞在 `run_ansibench_tiny.py` 的 `probe` 子用例里，命名与驱动归属都误导。

用户 2026-11-22 裁定：归到 picolibc，**单独一个 py 驱动**；ansibench 四件保持原样，不退役。

## 要做

1. **改名**：`tests/ee-tiny/ansibench_clock_probe.c` → `tests/ee-tiny/picolibc_clock_probe.c`；内容（忙等、`clock`/`gettimeofday`、5% 判据）不变，只改注释里的文件名/归属。
2. **新驱动**：`tests/ee-tiny/run_picolibc_clock_probe.py`，单独构建/链接/运行探针：
   - 链接契约与 `run_ansibench_tiny.py` 的 probe 相同（`picolibc_noflash.ld` + `crt0_tiny_picolibc.S` + `crt0-semihost` 改名 + `libc.a`/`libm.a`/`libsemihost.a`/builtins）；
   - 判据：guest exit 0；`clock()/CLOCKS_PER_SEC` 与 `gettimeofday` 相对差 ≤5%；最短忙等 `PROBE_MIN_WALL` 保留；
   - 退出码：0 PASS / 1 FAIL / 2 环境或参数错误；
   - `--inject`：把容差改坏（或改期望）必须 FAIL，证明断言是活的。
3. **从 ansibench 驱动移除 probe**：`run_ansibench_tiny.py` 只保留四件；删除 `probe` 子用例、`CLOCK_PROBE` 常量、`--only probe` 语义与相关输出；四件判据不变。
4. **清单/引用同步**：`tests/ee-tiny/.manifests.toml` 登记新文件/删除旧文件；`run_ansibench_tiny.py` 不再引用旧探针；相关 README/注释更新。
5. **不改**：picolibc 组件、ansibench 四件的参数/判据、`Process-09` 的 ansibench 归属文本。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集限 `tests/ee-tiny/{picolibc_clock_probe.c,run_picolibc_clock_probe.py,run_ansibench_tiny.py,.manifests.toml}`、相关 README、本任务书；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. `python3 tests/ee-tiny/run_picolibc_clock_probe.py` rc=0，打印 `clock`/`wall`/`rel`，`|rel| ≤ 0.05`；
2. `python3 tests/ee-tiny/run_ansibench_tiny.py` 四件仍 `4/4 PASS`（probe 不再出现在该驱动）；
3. `run_picolibc_clock_probe.py --inject` 必须 FAIL（容差/期望注入），`cp`+md5 还原后回绿；
4. 旧文件不存在、全仓无 `ansibench_clock_probe` 可执行引用（历史任务书/归档除外）；
5. `make check-manifests-guard`、`check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；
6. `--inject` ≥2 路（探针容差 + 清单登记）。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
