# m16-testcases-017: env 权限准备（H/S/U 下 cfx 可访问）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-015`（运行模式 env）已合入
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22 选 A）

每个 cfx 测试都要在 H/S/U 下跑，但默认两轴掩码只允许 hmon 访问大多数 cfx；smon/umon 访问会 `CFXPERM`。015 的 env 只负责进入模式，不处理 cfx 访问权限。

## 要做

1. **用例声明**：`tests/arch/modes.yaml`（或 case 元数据）增加 `cfx_access: [cfx5, …]`，声明该用例在目标模式下需要访问哪些 cfx。
2. **env 权限准备**：`tests/arch/common/env/{smon,umon}/env.S` 在降模式前，由 hmon 把目标 cfx 的 `<mode>_cfxreg`/`<mode>_cfxmem`/`<mode>_cfxtrap`/`<mode>_cfxexe` 掩码对目标模式打开（按 `DADAO-12 §3` 的 RW 行）；hmon 模式无需准备。
3. **顺序**：hmon 打开掩码 → `switch_run_mode`/进入 → body；退出时恢复原掩码（或记录原值并还原）。
4. **代表验证**：选 cfx5（cache 寄存器面）或 cfx4（ptw 寄存器面）在 smon/umon 下跑一次，确认不再 `CFXPERM`；未声明 `cfx_access` 的用例保持默认权限。
5. **失败语义**：声明了 `cfx_access` 但 env 未打开对应掩码 ⇒ 用例收到 `CFXPERM` 并红；未声明但访问 ⇒ 红（防止静默放宽）。

## 不做

- 不改 cfx 实现、不改 RTL 的 U/S 路由（020）；
- 不改 015 的进入模式逻辑（只加权限准备步骤）；
- 不放宽默认掩码（只在用例声明的范围内、由 hmon 临时打开）。

## 约束

- 独立 `git worktree`；**不提交 git**；变更集限 `tests/arch/common/env/**`、`tests/arch/modes.yaml`、`tests/arch/run_arch.py`（若需读 `cfx_access`）、`tests/arch/README.md`、本任务书；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. 代表用例在 smon/umon 下访问声明的 cfx 成功；未声明的 cfx 仍 `CFXPERM`；
2. 三模式（hmon/smon/umon）各跑一次，签名一致；
3. **可达 FAIL**：注入「env 不打开掩码」⇒ 代表用例 `CFXPERM` 红；注入「默认放宽」⇒ 未声明用例红；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
