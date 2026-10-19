# INFRA-097t: L3 语义门控载体扩至 `tests/vectors/isa` 全量（`ISS-235`）

**模块**：infra
**项目里程碑**：M9
**依赖**：`QEMU-066t`（最新 qemu 语义/解码，`待验收`）、`INFRA-096t`（安装根新鲜度门控，`待验收`——安装根不新鲜会假 FAIL/假绿）、`INFRA-099t`（门控互斥；**同改 `Makefile` 门控区，须串行**）
**状态**：待开始

> **编号（现场取号，2026-10-20）**：`infra` 现存最大 = `INFRA-096t`（本批另占 `098`/`099`）⇒ 取 **`097`**（编写前 `grep -rn 'INFRA-097' .tao/` 零命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实

- **门控现场**：`Makefile:1033` 定义 `check-qemu-semantics`（L3 语义门控），`Makefile:1036` 的载体清单**硬编码 4 项**：`isa/reg-shift-extend.yaml isa/reg-compare.yaml isa/aip-si.yaml rol/rol.yaml`；`Makefile:599` `check-full: check-qemu-semantics test-m6`。
- **向量现场**：`tests/vectors/isa/*.yaml` = **16 册**（`aip-si`/`ctrl-br`/`ctrl-call`/`ctrl-jump`/`ctrl-ret`/`mem-ra`/`mem-rb`/`mem-rd`/`misc`/`reg-arith`/`reg-compare`/`reg-cond-assign`/`reg-imm-block`/`reg-logic`/`reg-shift-extend`/`reserved`，以 `ls` 现场为准）；另有 `tests/vectors/{rol,rev,bitcnt}/*.yaml` 各 1 册。
- **覆盖缺口（`ISS-235` 现场）**：除上述 4 项外，其余 isa 册在 L1/L2/L3 **零门控消费**（`grep -n '<name>.yaml' Makefile` 逐册）；L2 `check-qemu-smoke` 载体 = `tests/scripts/run_qemu_smoke.py:40` 的 3 册（代表性，**本册不改 L2**）。
- **口径漂移实例**：`tests/scripts/run_qemu_smoke.py:4-5`/`:37` 与 `Makefile:1054-1058` 仍称「全量留在 L3」，而 L3 实际只跑载体集内全量 ⇒ 覆盖声明与载体脱钩（`ISS-235`/`ISS-236` 族）。
- **依据**：`docs/Process-07 §1`（L3 = 「较完整 / 全量」）、`§3`（新检查定层规则、**代表集机械派生**、**计数不写死**）、`§4`（层间不重复：L2 代表集、L3 全量）；`lessons §2`（计数现场派生）；`AGENTS.md`「门控分层」。
- **范围边界**：本册口径 = **`tests/vectors/isa` 全部册**（现场 16）+ **保留** `rol/rol.yaml`；`tests/vectors/rev`、`tests/vectors/bitcnt`（M8 scope，2 册）**不在本册**，须在完成区显式登记，**不得**用「全量」措辞掩盖。

## 接口规范

- **输入**：`Makefile`（`check-qemu-semantics` 目标）、`tests/vectors/isa/*.yaml`、`tests/vectors/rol/rol.yaml`、`tests/scripts/run_qemu_test.py`（`--batch <dir>`；`tests/scripts/run_qemu_smoke.py` 的自证风格可作参照）、安装根 `qemu-system-dadao`。
- **输出**：
  1. `Makefile` **最小改动**：载体清单由 `tests/vectors/isa/*.yaml` **现场派生**（不得写死册名/册数），保留既有 symlink 校验（`Makefile:1037-1040`）并扩展为「逐册生成 + 总册数断言」；
  2. 门控默认档日志**自证覆盖**：打印载体名清单 + 载体数 + 用例总数（全部现场派生；形如 `run_qemu_smoke.py:103-107`）；
  3. 措辞订正：`Makefile:1054-1058`、`tests/scripts/run_qemu_smoke.py:4-5/:37` 的「全量」改为「L2 = 代表集 / L3 = `tests/vectors/isa` 全量」；`docs/Process-07 §1` L3 行同步；
  4. 覆盖登记：`tests/vectors/inventory.md` 增「门控覆盖（L2/L3）」列或等价登记（逐册「进门控 / 未进门控」；须机械可核，不得只写文字）；
  5. 证据 `.work/evidence/<任务ID>/run.sh`（default + inject）+ 日志 `.work/log/qemu/INFRA-097t-*.log`。
- **约束**：**不改** `tests/vectors/**`（除 inventory 登记列）/ `tests/scripts/run_qemu_test.py` 语义 / `spec/` / `contracts/`；**不新增**硬编码计数；不改 L2 载体；不 commit/push。

## 验收标准

1. **载体全量（现场派生）**：`make check-qemu-semantics` rc=0；日志打印的载体名 == `ls tests/vectors/isa/*.yaml` 现场清单（逐名比对）+ `rol.yaml`；载体数 == 现场计数（日志中数字由脚本派生，`Makefile` 内无字面册数，`grep` 无 `16` 之类的硬编码）。
2. **结构性断言**：缺册 / 重复 basename / symlink 指向错误 / 册数为 0 ⇒ 显式 FAIL（非静默跳过）；断言逻辑本身可注入触发。
3. **用例数与耗时**：日志给出 `total/passed/failed` 与旧值（`ISS-235` 现场 161）的差值，并**逐册**给出新增用例数（现场统计）；`time` 实测 L3 该目标耗时（数百~数千秒允许），写进完成区。
4. **可达 FAIL ≥ 2**（真实输出 + 还原回绿；还原用 `cp`+md5，禁 git 还原）：
   - (a) **定点注入**：在新纳入的册（任选 `mem-rd.yaml` / `ctrl-br.yaml` / `misc.yaml` 之一）改一个 case 的 `expected_state`/`expected_pc` ⇒ 门控 rc≠0 且日志出现该册名的 `FAIL` 行；
   - (b) **缺册注入**：把某册临时移到 `/tmp/opencode/INFRA-097t/` ⇒ 门控 FAIL（计数/缺册断言），还原后 rc=0；
   - (c) **计数硬编码反例**：把 `Makefile` 的载体数改成字面量（临时树）⇒ 结构断言（现场派生）应红；证明「不写死」可判。
5. **无回归**：`make check-qemu-smoke`（L2）rc=0 且代表集规模不变（现场 90）；`make check`(L1) rc=0；`check-run-artifacts` / `check-no-residue` rc=0。
6. **文档与登记**：`docs/Process-07 §1` L3 行、两处「全量」措辞、`inventory.md` 覆盖列三项落地；`rev`/`bitcnt` 未纳入一事在完成区与 inventory 中如实登记（给后续任务指针）。
7. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` 的 `ISS-235` 回填（`closed` + `resolved_by: INFRA-097t`；`ISS-236` 若因默认档自证而收口，一并注记）。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-097t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（扩大范围到 `rev`/`bitcnt`、或某册无法在 L3 执行）时留问。
6. 复杂命令输出留 `.work/log/qemu/`；L3 跑前确认无其它写门控并发（`INFRA-099t` 落地后由锁保证）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
