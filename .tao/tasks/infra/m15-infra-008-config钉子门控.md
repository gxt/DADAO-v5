# m15-infra-008: 门控切片 `CONFIG_DADAO_*` 钉子全集检查

**模块**：infra
**项目里程碑**：M15
**依赖**：**`m14-linux-017` 收口**（同改 `tools/linux/check_k*.py` 与 `k4_*_probe.py`；必须串行）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改
**状态**：待验收

## 背景（`ISS-470`，两次复发）

`m14-linux-017` 的 F30 与 F41 是同一类事故、**两次复发**：

- F30：新增 `CONFIG_DADAO_K4_SWITCH_SELFTEST` 后，`check_k3` 的切片没钉它 ⇒ pf1 镜像继承 `y`，跑了 `rdinit=/init.musl` 覆盖 ⇒ k3 **227/247 假红**。
- F41：新增 `CONFIG_DADAO_K4_STACK_SELFTEST` 后，switch 探针镜像继承 `=6` ⇒ 在 K4 边界就结束（14 条红）。

两次都靠人发现。这**可以机械判**：Kconfig 里有多少个 `CONFIG_DADAO_*`，每个门控切片的镜像配置就必须**显式**覆盖全部。

## 目标

1. **真源**：`components/linux/patches/arch/dadao/Kconfig.debug.patch` 里所有 `config DADAO_*` 符号（**现场解析，不写死数量**；当前 13 个，017 收口后会增加）。
2. **每个门控脚本声明自己的钉子**：在 `tools/linux/check_k0.py`、`check_k1.py`、`check_k2.py`、`check_k3.py`、`k4_fork_probe.py`、`k4_switch_probe.py`、`k4_stack_probe.py`（以现场为准）里各加一个模块级常量，例如：
   ```python
   CONFIG_PINS = {
       "CONFIG_DADAO_K2_TRAP_SELFTEST": "n",
       ...
   }
   ```
   —— 该常量必须是**完整集合**（不是增量），并被脚本实际使用来生成镜像配置（不能只声明不用）。
3. **新门控** `check-config-pins`（L1）：
   - 解析 Kconfig 符号全集；
   - `ast` 解析每个脚本的 `CONFIG_PINS`（或等价常量）；
   - 断言 `set(CONFIG_PINS) == set(Kconfig 符号)`，**缺一个 ⇒ 红并点名「脚本 X 未钉住符号 Y」**；多一个不存在的符号 ⇒ 红（防拼写错）。
   - 新增的 `tools/linux/*probe*.py` / `check_k*.py` 若没有该常量 ⇒ 红（防新脚本逃逸）。
4. `--self-test` 覆盖：缺符号、多符号、脚本无常量、Kconfig 新增符号（临时构造）。

## 验收（逐条贴真实 rc）

1. `make check-config-pins` rc=0；`--self-test` 全绿且每例原因命中。
2. **可达 FAIL（核心）**：临时从 `check_k3.py` 的 `CONFIG_PINS` 删一个符号 ⇒ rc≠0 且点名；还原 ⇒ rc=0。
3. **模拟 F30 复发**：临时在 Kconfig 加一个新 `config DADAO_FAKE_SELFTEST`（不改任何脚本）⇒ rc≠0，提示「所有门控脚本均未钉住」；还原 ⇒ rc=0。
4. **模拟 F41**：临时给某脚本加一个 `CONFIG_DADAO_K4_STACK_SELFTEST=6` 但其它脚本缺该符号 ⇒ 红。
5. 各门控脚本改完后仍真跑绿：`check-linux-k0` 130/130、`k1` 112/112、`k2` 170/170、`k3` 263/263、`k4_fork_probe` 101/101、`k4_switch_probe --no-inject`（与收口时基线一致）。
6. `check-writer-guards`（新增脚本需登记）、`check-manifests-guard`、`check-knowledge-refs` rc=0。
7. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. **不改内核侧 Kconfig 与补丁**（只读解析）；不改任何门控的**判据语义**（只加「钉子完整性」这一条）。
3. 与 `m14-linux-017` **串行**：017 未合入前不得开工（同改这些脚本）。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。
5. **禁并发构建与门控**（017 已踩过）；5 个内核门控逐个串行跑。

## 待裁定

（执行中如有 → 写入本节并返回）

## 审阅记录

### 第 1 轮 engineer 自审

**自审逐行核过**：Kconfig 解析（patch 的 `+` 行 / 纯文件两形态）、`depends on` 求值、13 个脚本的
`CONFIG_PINS`/`IMAGE_PINS` 与派生切片、`check_config_pins.py` 的 C1–C5 与 6 类自检、Makefile/文档接线。
逐脚本对照 HEAD 的既有 `CONFIG_X=v` 对**零丢失**（新增项只有新符号的显式 `n`/`0`）；
31 个镜像的切片写进临时树 `.config` 跑 `olddefconfig` 全部存活（int 钉 `n` = 不落行且必须不可见）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `check_k2` 的 `IMAGE_CONFIG` 以 `k2` 命名基础镜像，检查器只认无名基础镜像 ⇒ C5 误红 | ✅已修 | `IMAGE_PINS` 增 `"k2": {}`（空覆盖 = 给基础镜像命名），检查器把空覆盖登记为别名 | `check-config-pins` rc=0 |
| C3 逐符号打印 877 行，L1 噪声过大 | ✅已修 | 改为一脚本一行汇总（问题逐条进失败列表）；覆盖镜像只复核被覆盖的值 | 63 项检查、rc=0 |
| 自检里「注入生效」可能空编辑（F41 注入点出现 2 次）⇒ 假绿 | ✅已修 | 证据脚本加 `inject_ok`：编辑失败即红；F41 注入点改成注释+条目两行唯一锚 | `run.log` 32 PASS / 0 FAIL |
| `eval_depends` 里有一段无意义的长度自检残留（no-op） | ✅已修 | 删除该分支 | `compileall` + 全绿 |
| Kconfig 空时逐脚本刷 13 行「多出符号」噪声 | ✅已修 | 空符号集直接判红并 `[INFO]` 短路（fail-closed） | `--self-test` 注入③ 命中 `fail-closed` |
| K0–K4 执行本体未重跑 | ⏸延后 | 派单口径明确「不需要重跑完整 K0–K4」；以切片语义等价 + 31 镜像 config 存活替代 | 见完成区 |

### 第 1 轮 reviewer 验收（2026-11-19；中改，≥2 路注入，独立重跑）

**重跑（命令 → 我自己的输出/退出码）**
1. `make check-config-pins`（任务 worktree）⇒ `结果：PASS（检查 63 项，失败 0 项，退出码 0）`，rc=0；现场统计「切片脚本 13、Kconfig 符号 15、镜像 41」。
2. 合并态（`Process-07 §5a`）：临时 worktree 取**当前 master `3a415038`（含 `43a51c47`）** + 拷入本任务 18 个改动文件 ⇒ `make check-config-pins` rc=0、63 PASS、13/15/41；核后已 `git worktree remove`。
3. `python3 tools/linux/check_config_pins.py --self-test` ⇒ rc=0，「6 类注入，失败 0 项」，每例注入 rc≠0 且原因命中、还原后 rc=0。
4. 现场独立计数（自写正则、不 import 被测模块）：patch 内 `+config DADAO_*` = **15**；`CONFIG_PINS` 脚本 = **13**；镜像 = **41**（1+1+3+5+1+1+4+6+11+1+1+5+1）；13 个脚本键集合逐一对真源 ⇒ **0 缺 0 多**。
5. 可达 FAIL（均 `cp`+md5 还原、md5 相等后回绿）：① 删 `check_k3` 的 `CONFIG_DADAO_K2_SELFTEST_CFXESC` ⇒ rc=1 点名「check_k3.py 缺 …」；② `IMAGE_ON` pf1 `1→2` ⇒ C5 红（**不在 engineer 的 6 路内**）；③ `IMAGE_PINS` pf1 键拼错 ⇒ C3「多出不存在符号/未声明」+C5 红（**不在其 6 路内**）；④ 临时树 Kconfig 尾部加 `config DADAO_FAKE_SELFTEST` ⇒ 13/13 脚本逐一点名、rc=1（验收 3 形态）；⑤ 探针：`k4_switch_probe` bool `y→n` ⇒ **rc=0（未捕获，见 finding 1）**。
6. C2/C4 逃逸（临时树）：新 `zz_fake_probe.py` 调 `config_lines()+apply_config_lines` 却无 `CONFIG_PINS` ⇒ rc=1 点名；`check_k0` 删 `config_lines()` 改手写切片 ⇒ C2+C4 双红并点名三行字面量；还原后均 rc=0。
7. 语义等价（AST 解析 HEAD 手写切片 vs `config_lines()`）：`check_k3`（5 镜像）与 `k4_switch_probe` 共享键 **0 遗漏、0 值变**；新增项仅 6 个 K2 符号显式 `n` + int `K2_TIME_CASE` 置空（= 任务要求的完整集合），非漂移。
8. L1 接线：`make -qp` 显示 `_locked-check` 前置含 `check-config-pins`；`check` ∈ `GATE_LOCKED_TARGETS`（gate-locked → `_locked-check`）；`make help` 第 34 行已登记；`docs/Process-07` 计数 63→64、64→65 与现场 `grep -c "^check-[a-z0-9-]*:" Makefile`=**64** 一致（master=63）。
9. 其它门控：`check-manifests-guard`/`check-knowledge-refs`/`check-dirs`/`check-no-residue`/`check-tasks` rc=0；`check-writer-guards` 首跑 **23/27**（新 worktree 缺 gitignore 的本地交叉工具链，**pristine master 同样 23/27 ⇒ 环境性、非本任务**），补同款本地链接后 **27/27、rc=0**，与完成区声明一致。
10. 快照对账：注入前后 `git status --porcelain -uall` 与 18 文件 md5 **逐行/逐值相同**；改动清单 == 完成区「修改文件」18 项；无「银行」、完成区无 `.work/**` 路径、完成区 11 行 ≤30；未提交 git、未改主工作树、临时文件全在本任务运行期临时目录、还原只用 `cp`+md5（未用 checkout/restore/stash）。

**未核 / 采信**：K0–K4 执行本体与 31 镜像 `olddefconfig` 存活未重跑（本派单口径未列、需构建）；证据 `run.sh` 32 PASS 未核（运行期证据目录不在仓库，不作验收依据）。

**Findings（不阻断，交 architect 收尾处置）**
1. bool 钉子值 `y↔n` 翻转不被捕获（`k4_switch_probe` rc=0）：门控契约 = 键集合 + 类型/range + int 可见性 + 期望表，**值语义不全覆盖**；建议在 `docs/Process-07` 行文点明该边界。
2. C2 逃逸判据 = 「调 `apply_config_lines`」（只调 `config_lines()` 不落地 ⇒ rc=0）；任务书字面写「新增 `*probe*.py`/`check_k*.py` 无常量 ⇒ 红」，实现与 docs 同按**调用点**口径；按文件名判会把既有 `k1_boot_probe.py`（只读 `.config`、不切片）误红 ⇒ 收尾时把任务书措辞对齐实现口径。
3. `check-tasks` 报告型提示「① 漏收尾 1」即本任务（完成区已填、状态仍待验收），属正常流程，不阻断。

**判决：Accepted** —— 验收 1/2/3/4/6/7 在我自己的重跑下全过（输出/退出码如上），硬约束无违反；验收 5（K0–K4 真跑）按本派单口径不要求，已列「未核」。

## 完成区

**测试结果**：`make check-config-pins` rc=0（63 项，现场统计：切片脚本 13 × Kconfig 符号 15 × 镜像 41）；`--self-test` 6 类注入、失败 0；运行期证据脚本 rc=0（32 项全 PASS）。
**修改文件**：新增 `tools/linux/config_pins.py`（Kconfig 解析 + `config_lines()`）、`tools/linux/check_config_pins.py`（C1–C5 + self-test）；13 个切片脚本各加模块级 `CONFIG_PINS`（`/IMAGE_PINS`）并改为由 `config_lines()` 生成切片：`check_k0/k1/k2/k3.py`、`k1_pt_probe`、`k2_irq_probe`、`k2_time_probe`、`k2_trap_probe`、`k3_page_probe`、`k3_pt_probe`、`k4_fork_probe`、`k4_stack_probe`、`k4_switch_probe`；`Makefile`（目标 + L1 + help）、`docs/Process-07`（§1.1/§2 + 计数 63→64、64→65）、本任务书。
**验收结果**（真实 rc）：
- 要求 3 路可达 FAIL，实交 **6 路**（运行期证据目录 `run.sh`，各 `cp`+md5 还原后断言回绿）：① `check_k3.py` 删 `K2_SELFTEST_CFXESC` ⇒ rc=1 点名脚本+符号；② `check_k0.py` 加假符号 ⇒ rc=1「多出不存在符号」；③ Kconfig 删空 ⇒ rc=1 `fail-closed`；④ Kconfig 新增 `config DADAO_FAKE_SELFTEST`、无脚本钉 ⇒ rc=1，**13/13 脚本逐一点名**；⑤ `k4_switch_probe.py` 丢 `K4_STACK_SELFTEST` 钉子（F41 形态）⇒ rc=1 点名；⑥ 脚本写死 `["CONFIG_DADAO_K1_EARLY_STOP=y"]` ⇒ rc=1「手写切片字面量」。
- 合并态（§5a）：当前 master（`19b0ed9f`，与分支基线 `c82ba564` 差异仅台账一册）+ 本任务文件树 ⇒ `check-config-pins` rc=0（脚本/符号/镜像 = 13/15/41）。
- 切片语义等价：13 个脚本 vs HEAD 的既有 `CONFIG_X=v` 对**零丢失**；运行期配置核验：31 镜像切片逐个写入临时树 `.config` 跑 `make olddefconfig` ⇒ 全部存活、0 失败（不构建）。
- 既有门控：`check-writer-guards` 27/27、`check-manifests-guard`、`check-knowledge-refs`、`check-dirs`、`check-no-residue`、`check-patch-tree`、`check-contracts-dir`、`check-component-changelog`、`check-tasks`、`check-archive`、`compileall tools` 全 rc=0。K0–K4 执行本体按派单口径未重跑。
**新发现/坑**：Kconfig 的 **int 符号没有 `n` 值**（依赖不满足时整行不写，写 `=0` 会被 `olddefconfig` 丢掉 ⇒ `apply_config_lines` rc=1）⇒ `CONFIG_PINS` 用 `"n"` 表「本镜像置空」，`config_lines()` 不落行，门控再按 `depends on` 确认该 int 确实不可见。`make check` 停在 `check-isa-coverage`（`ld.o_rrii_rf`/`st.o_rrii_rf` 的 lit 行与矩阵），**master 同样红**、与本任务无关，未代改。`check-temp-dirs` 红 5 项（他任务临时目录 >2 h）同属既存。worktree 基线 `c82ba564` 早于 master 的台账提交 `19b0ed9f`（后者把 008 移入「进行中」）⇒ 树内 `check-milestones-fresh` 报 A1/R1 两项属**基线陈旧**；合并态（master + 本任务文件）rc=0 已验。
**遗留问题**：无（K0–K4 执行本体按派单口径未重跑；证据 = 切片语义等价 + 31 镜像 config 存活）。
