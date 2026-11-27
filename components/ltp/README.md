# LTP 组件（Linux Test Project）

DADAO Linux 的**系统调用/ABI 广度测试语料**（M18 `m18-linux-006`：`kselftest` 之后
的第二块套件）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定
（`shallow_ref = "20260930"`，精确 commit `2279d708…`）；工作树由 `make fetch`
+ `python3 tools/infra/apply_series.py --component ltp` 在 `.work/source/ltp`
建立（浅裸镜像 `.cache/ltp.git`）。

本组件是**语料组件**：上游树只读，任何 DADAO 适配都是一份可审计的树形补丁
（`patches/<上游相对路径>.patch`，`docs/Process-01`）。语料本身**不入库**——只有
锁条目、补丁集与台账在仓库里；构建产物、镜像与运行记录都在运行期目录。

## 版本与来源（2026-11-22 用户裁定 + 实测）

- **源 = `https://github.com/linux-test-project/ltp`**，版本 = tag `20260930`。
  身份只认 40 字符 commit：`2279d708c817db657611a30c427c7d06c4360049`。
- tag 是 **annotated**：`git ls-remote` 报 tag object `a6bade7f…`，其 `^{}` 才是上面
  的 commit（与本仓 qemu / linux 同口径：tag object 不是 commit，不入锁）。
- 取用形态：裸镜像 `git clone --bare --depth 1 --branch 20260930`（`shallow = true`）。
  实测直连 github 的 `ls-remote` 与浅克隆均成功，故未登记镜像源。

## 补丁集

- 形态：**树形补丁集**，清单 `series`（路径相对 `patches/`，按字典序，一行一个）。
- 当前补丁：见 `series` 与 `changelog.md`；一文件一补丁、目标路径全局唯一。
  校验：`make check-patch-tree`（ltp 段 0 problem）。

## 与套件的关系

用例清单（跑哪些、guest 侧超时、记录基线）**不在本组件**，在
`tests/unit/linux/suite/ltp/suite.yaml`；构建器
`tools/linux/suite/build_ltp.py` 只消费本组件工作树，按上游自己的 Makefile
做**树外构建**（`top_srcdir=<锁定树>`，`top_builddir=<运行期目录>`），不改源树。
运行骨架、分诊台账与口径见 `tests/unit/linux/suite/ltp/README.md`。

## 已知边界

- 本组件不是 LTP 的安装树：`LTPROOT`、`testcases/data`、`bin` 都不存在，依赖它们的
  用例（`resource_files`、`tst_get_path($PATH)`）由套件记 `SUITE_ENV`。
- 用例的通过与否**不改变**补丁集：补丁只表达「测试把别处假设写死」的适配，
  内核缺陷一律记在套件台账里，不在本组件修。
