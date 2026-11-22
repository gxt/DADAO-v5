# m16-testcases-011: picolibc clock 探针归位

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（`m15-infra-010` 已合入）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

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

**测试结果**：通过 27/27（运行期证据目录内 `run.sh`：checks=27 fails=0 rc=0，含 3 路注入）；探针基线 rc=0、ansibench 四件 rc=0。
**修改文件**：`tests/ee-tiny/picolibc_clock_probe.c`（新，由旧名改名：正文逐字节相同，仅注释）、`tests/ee-tiny/ansibench_clock_probe.c`（删）、`tests/ee-tiny/run_picolibc_clock_probe.py`（新驱动）、`tests/ee-tiny/run_ansibench_tiny.py`（移除 probe）、`tests/ee-tiny/.manifests.toml`、`tests/unit/picolibc/README.md`；证据脚本在运行期证据目录内 `run.sh`。
**验收结果**：
- ① `python3 tests/ee-tiny/run_picolibc_clock_probe.py` rc=0：`probe clock=0.311911 wall=0.312179 rel=-0.0009`（|rel|=0.09% ≤5%），text+data+bss=18560 B；符号 clock/times/gettimeofday/printf 已链接（只记录）。
- ② `python3 tests/ee-tiny/run_ansibench_tiny.py` rc=0：`4/4 PASS`（coremark 35288 B/16.1 s、dhrystone 43584 B/7.1 s、linpack 26224 B/28.1 s、whetstone 30432 B/10.7 s，均 ≤65536）；输出无 probe 子用例；`--only probe` rc=2「未知项」。
- ③ 注入 3 路：⒜ `--inject`（容差 0.05→−1.00）rc=1 +「注入后判定为 FAIL」；⒝ 忙等源码注入 `i < 1UL` ⇒ rc=1「忙等太短（0.000747s < 0.05s）」→ `cp` 还原 md5 `45e5bdad…` → rc=0；⒞ 清单删 `picolibc_clock_probe.c` 登记 ⇒ manifests-guard rc=1「多出文件 picolibc_clock_probe.c」→ 还原 md5 `d9f50ba0…` → rc=0。
- ④ 旧文件不存在；全仓 `ansibench_clock_probe` 可执行引用 0 处（`*.py`/`*.toml`/`*.yaml`/`*.md`，历史任务书/归档除外）。
- ⑤ `check-manifests-guard` / `check-tests-index` / `check-tasks` / `check-knowledge-refs` 均 rc=0。
**新发现/坑**：
- `tests/ee-tiny/__pycache__` 由 `check-tests-index`（import `run_inst_tiny`）现场生成，会让 manifests-guard 报「多出子目录」；证据脚本每次跑该门控前清一次。
- `run_ansibench_tiny.py --inject` 原有 `tuple(str)` 缺陷（把期望字符串拆成逐字符元组 ⇒ 注入退化为「缺任一字符」）；在本任务编辑的同一注入块内改为单元素元组，复验消息恢复为整条期望。
- 任务 worktree 默认没有运行期目录的符号链接，须先链到主工作树才能跑驱动（与其它任务树一致）。
- 新驱动不启用 `writer_guard`：任务书要求退出码只有 0/1/2，而读守卫拒绝码为 75。
**遗留问题**：`tests/README.md` 的 `ee-tiny/` 行写「3 个驱动」且不含 ansibench 驱动（本任务前即如此），未扩大范围；建议后续测试资产清单任务统一收口。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-22）

自审方式：自主逐行审查全部改动（新驱动 + ansibench 驱动 diff + 清单 + README + 证据脚本），并复跑真实命令核对完成区数字。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `judge()` 里 `clk` 未使用（可读性/易误删） | ✅已修 | 解包为 `_clk` 并注明「结果行已含 clock 秒数，判定只用 wall/rel」 | 重跑 `run_picolibc_clock_probe.py` rc=0 |
| `--inject` 在基线已 FAIL 时也会「翻红」＝假证据 | ✅已修 | 注入前要求 `status == PASS`，否则 rc=2 并点名 | `--inject` rc=1；rc=2 分支由代码路径审查确认（未制造假基线） |
| `--inject` 退出码语义（任务「必须 FAIL」vs 自检语义） | ✅已定 | 注入后判定为 FAIL ⇒ rc=1（与真实 FAIL 同路径）；注入未生效 ⇒ rc=2，均写入 docstring | `python3 … --inject; echo $?` = 1，日志「注入后判定为 FAIL」 |
| ansibench `--inject` 的 `wrong = tuple(case.expect[0]+…)` 把字符串拆成逐字符 | ✅已修 | 改单元素元组 `(case.expect[0] + " (injected-wrong)",)` | `--only coremark --inject` 打印整条期望，`INJECT: PASS` rc=0 |
| 证据脚本断言是否可失败（防恒真） | ✅已核 | 每条检查都有可达 FAIL：容差注入/忙等注入/清单注入/`--only probe`/旧名 grep；计数现场统计 | 注入三路各自红→还原回绿（见完成区③） |
| `.manifests.toml` 双向集合（新文件登记、旧文件删除） | ✅已核 | 删 `ansibench_clock_probe.c` 行、增 `picolibc_clock_probe.c` + `run_picolibc_clock_probe.py`（保持字母序） | manifests-guard rc=0；删登记注入 rc=1 |
| 旧探针正文是否被改动 | ✅已核 | 仅注释；正文 `#include` 起逐字节相同 | `diff`（旧 `HEAD` 版 vs 新版，`#include` 起）无输出 |

判决：全部 finding 已处置，无未修项 ⇒ 状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-22）

**重跑记录（本人执行，非采信完成区）**：
- 运行期证据目录内 `run.sh`：`checks=27 fails=0`、`evidence run.sh: PASS`、`RUN_RC=0`；27 条逐项 PASS（C1 `rel=-0.0010` ≤0.05；C2 `--inject` rc=1；C3/C6 注入红→还原 md5 `45e5bdad…`/`d9f50ba0…`→回绿 rc=0；C4 `4/4 PASS`、`--only probe` rc=2；C7 四门控 rc=0）。
- 门控另单独自跑：`check-manifests-guard` rc=0（清单 7/受检 7/文件 74/sha256 36 全符）、`check-tests-index` rc=0（487 条）、`check-tasks` rc=0（报告项「①漏收尾 1」即本任务，非阻断）、`check-knowledge-refs` rc=0（悬空 0、具体运行期路径引用 0）。
- 探针基线 `rc=0`、`PASS（|rel| ≤ 5%）`、`size=18560`；ansibench `4/4 PASS`、size 35288/43584/26224/30432（耗时与完成区有运行期波动 16.0/7.2/28.5/10.8 s，非差异）。

**独立注入（`cp`+md5，未用 git checkout/restore/stash）**：
- 忙等 `10000000UL → 1UL` ⇒ 基线 rc=1「忙等太短（0.000726s < 0.05s）」；同态下 `--inject` rc=2「基线判定 FAIL，注入无意义」（rc=2 分支实测通过）；`cp` 还原 md5 `45e5bdad…` 相等 ⇒ 回绿 rc=0。
- 另一路 `PROBE_TOLERANCE 0.05 → -1.0` ⇒ rc=1；还原 md5 `e6531223…` 相等 ⇒ rc=0。

**约束核验**：① 正文逐字节相同——`#include` 起 diff 无输出、双侧 md5 `522116dc…`，仅头注释改名；② 链接契约相同——同一 `BASE_CFLAGS`、`llvm-mc -I 仓库根` 栈桩 + `--redefine-sym _start=_picolibc_start`、lld 顺序 stub→crt→obj→`libc.a/libm.a/libsemihost.a/builtins`、QEMU 参数一致；③ ansibench 已无 `CLOCK_PROBE`/`probe` 子用例/`--only probe`（残留 2 处仅为指向新驱动的说明），四件 `CASES`/`judge`/`window` 未动（diff hunk 未触及）；④ `PROBE_MIN_WALL=0.05` 与 `|rel|≤5%` 保留并被 `judge()` 使用；⑤ 清单双向集合正确（删旧增新、字母序），旧名全仓可执行引用 0 处（本人 grep 仅排除仓库元数据、归档与运行期目录，命中仅新 `.c` 注释与本任务书文字）；⑥ 变更集 7 项与完成区「修改文件」逐行对账一致，无越界；⑦ 任务书无运行期路径；⑧ `tuple(str)` 缺陷修复在本任务文件 `run_ansibench_tiny.py` 注入块内，改法为单元素元组，`expect_override` 只在 `--inject` 分支生效，四件判据不受影响（实测 `--only coremark --inject` 打印整条期望、`INJECT: PASS` rc=0）。

**finding（均非阻断）**：① 证据脚本 C5 排除面宽于任务口径（整目录 `tasks` + 单文件 `picolibc_clock_probe.c`），已由本人独立 grep 补证为 0 处，建议收窄；② 新驱动未接 `writer_guard`（同目录 4 个驱动均接），docstring 已给理由（任务限退出码 0/1/2、守卫拒绝码 75），且 `check_writer_guards.READER_ENTRIES` 未登记故门控不红 —— 是否补登记/把 75 映射为 2 请架构师裁定；③ `tests/README.md`「3 个驱动」为本任务前既有遗留（已披露，未扩大）。

**判决：Accepted**（验收命令块在本人重跑下全绿、约束无违反、注入红→还原→回绿均实测）。
