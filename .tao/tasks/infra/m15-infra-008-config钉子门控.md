# m15-infra-008: 门控切片 `CONFIG_DADAO_*` 钉子全集检查

**模块**：infra
**项目里程碑**：M15
**依赖**：**`m14-linux-017` 收口**（同改 `tools/linux/check_k*.py` 与 `k4_*_probe.py`；必须串行）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改
**状态**：待开始

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

（待填）
