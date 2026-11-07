# INFRA-134t: 工具清理与 `remote.py` 仓库根校验

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-130t` / `INFRA-131t`（已合入）
**状态**：待开始

## 背景与事实

两处已登记但未修的工具缺陷（验收时被 reviewer 判为「不阻断、可后修」）：

- `ISS-347`：`tools/infra/bootstrap_node.sh` 的 `DEV_OK` 实为「问题标志」（0=正常），名实相反，曾被改出反逻辑（依赖齐全反而退出 2）；另缺「仅 dev 缺失、工具齐全」的隔离用例，全缺时待安装清单 `- binutils` 重复 3 次。
- `ISS-348`：`tools/infra/remote.py` 的 `--repo` 指向某仓库的**子目录**时 `cd` 成功、`git rev-parse` 读到父仓库 commit，会报出「不是目标仓库」的状态而不报错。

两者都只改 `tools/infra/`，不触碰 `components/`、`Makefile`、门控判据与 SPEC，可独立于 gem5 线推进。

## 目标

1. **`bootstrap_node.sh` 语义改名**：`DEV_OK` → `DEV_BAD`（或等价：变量名与「有问题=真」一致），三处引用（step 1 主判、待安装清单、注释）同步；行为不变，仅消歧。
2. **待安装清单去重**：`ar/ranlib/nm` 只出现一次 `- binutils`。
3. **补隔离用例**：证据脚本新增「仅 dev 缺、工具齐全」场景（伪造 `pkg-config` 恒失败），断言 `[step 1] rc=2` + `- pkg-config … libfdt-dev` + **不进入 step 4**。现有 S15 是全缺场景，覆盖不到该分支。
4. **`remote.py` 仓库根校验**：`--repo` 解析后，在节点执行 `git rev-parse --show-toplevel`，若与 `--repo`（规范化后）不一致 ⇒ 该节点 FAIL，提示「`--repo` 不是仓库根」；`--repo` 指向子目录、或指向父目录下的其它仓库，都要判 FAIL。
   - 注意：`/worktrees` 类布局下 `--show-toplevel` 返回工作树根，需与 `--repo` 一致即可，不要求等于 `--git-common-dir`。

## 范围 / 非范围

**在范围内**：`tools/infra/bootstrap_node.sh`、`tools/infra/remote.py`、两者证据脚本、本任务书、`milestones.md`、`issues.yaml`（关闭 `ISS-347`/`ISS-348`）。

**不在范围**：`fetch.py`、`sync_cache.py`、`Makefile`、门控判据、`components/`、`spec/`/`contracts/`、`nodes.md`（仅当行为口径变化才补一句）。

## 验收标准

1. `bash -n tools/infra/bootstrap_node.sh` rc=0；`python3 -m py_compile tools/infra/remote.py` rc=0。
2. 改名后行为等价：依赖齐全 ⇒ step 1 rc=0 并继续；缺任一工具或 dev ⇒ rc=2 + 清单（逐项真实执行）。
3. 新增隔离用例真实可达 FAIL：把 `pkg-config` 探测改回恒真 ⇒ 该用例转红；`cp`+md5 还原回绿。
4. `remote.py`：`--repo` 指向仓库根 ⇒ rc=0；指向子目录 ⇒ 该节点 FAIL + 明确提示；指向非仓库 ⇒ FAIL；指向不可达 host ⇒ FAIL。真实 rc 逐条给出。
5. 既有证据脚本回归：`bootstrap_node.sh` 与 `remote.py` 的 default/`--inject` 全部 PASS；`sync_cache.py` 与 `remote.py` 的旧证据仍绿。
6. `make check`（L1）rc=0；`check-run-artifacts` PASS（日志按任务号命名）。
7. 关闭 `ISS-347`、`ISS-348`（`resolved_by` 填本任务号）。
8. 完成区 ≤30 行、无运行期路径。

## 说明

- 纯工具语义修正，不改任何构建产物或测试期望。
- 若发现 `--show-toplevel` 在 worktree/裸仓库场景有歧义，如实记录并给出判据，不要用 `realpath` 之外的重写规则静默兜底。
