# m20-testcases-005: picolibc harness `.done` 复用键纳入输入指纹（ISS-504）

**模块**：testcases
**项目里程碑**：M20
**依赖**：无（picolibc 安装根已就绪）
**可并行分片**：否（单 harness）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（issues-left 分诊，2026-11-25）

`ISS-504`：`tests/ee-tiny/run_picolibc_tests_tiny.py` 的 `.done` 复用键在 **qemu**
引擎下 `sim_md5` 恒为 `None`（`obs` 只在 chipyard 分支产生），
`info.get("sim_md5") == sim_md5` 退化为 `None == None` ⇒ 换库/换 lds 后仍复用旧判决
（`m15-infra-009` 的 `pass=6` 假绿即此因）。

## 目标

1. `.done` 复用键不得依赖引擎分支产生的 `sim_md5`：
   - 把被测输入指纹（至少 `libc.a`、安装版 lds、工具链/编译器版本或 md5）纳入 key；
   - qemu 与 chipyard 使用同一套语义；无法取得的字段使用稳定占位并在报告中明示。
2. 提供 `--force`/`--no-reuse`（至少一个）用于强制重跑；旧 `.done`（无输入指纹）
   必须自动失效，不允许复用。
3. 证据脚本不再需要「先删运行期 `run/` 目录」才能避免假绿。

## 验收（逐条贴真实 rc）

1. 复现：同一 `run/` 下改 `libc.a` 或安装版 lds（或 touch 相关输入）后再跑，旧 harness
   复用旧判决（给 rc/输出）；修复后强制重跑并更新 `.done`。
2. 相同输入二次运行仍可复用（证明没有退化为永远重跑）；不同输入必须重跑。
3. `--force`/`--no-reuse` 行为真实（给两次运行对照）。
4. 运行 picolibc fast 或最小代表性例（qemu）rc=0；不改 picolibc 组件源码。
5. 至少 1 路可达 FAIL：把输入指纹从 key 去掉 ⇒ 换输入仍复用（红）；`cp`+md5 还原后回绿。
6. `check-tests-index`/`check-knowledge-refs` 真 rc；`check-patch-tree` 按未触碰组件披露。

## 约束

独立 `git worktree`（分支 = `m20-testcases-005`）；不提交 git；只改
`tests/ee-tiny/run_picolibc_tests_tiny.py`、必要 harness 测试与本任务书；不改
`components/**`、`tests/inst/**`、`spec/`、契约、`Makefile`。证据落运行期证据目录内
`run.sh`；不写具体构建/安装/临时路径。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
