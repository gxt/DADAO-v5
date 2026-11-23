# m17-idl-019: 修 `idl_check_trace --cases` 的清单键（ISS-518）

**模块**：idl
**项目里程碑**：M17
**依赖**：无
**可并行分片**：否
**预估**：30–60 min
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景

`ISS-518`：`idl/tools/idl_check_trace.py` 的 `--cases` 读取清单时强制 `id` 键，而现行清单 `idl/data/idl_exec_cases.toml` 用 `image`（`[[case]] image = "tests/inst/..."`）⇒ 直接传主清单会报缺键。阶段门控走 `idl_four_way.py` 不触发，属潜伏缺陷。

## 要做

1. `idl/tools/idl_check_trace.py`：`--cases` 同时接受 `image`（现状）与 `id`（旧格式），`id` 只作诊断别名；两者都缺 ⇒ 明确报错；
2. 若 `image` 是相对路径，按仓库根解析（与 `idl_four_way.py` 同口径）；
3. `--self-test` 增两路：`image` 清单可通过、缺键清单报错；
4. 不改清单内容、不改 trace 判据。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；只动该脚本 + 本任务书；完成区 ≤30 行。

## 验证

1. `python3 idl/tools/idl_check_trace.py --cases idl/data/idl_exec_cases.toml --self-test`（或对应子命令）rc=0；
2. 用主清单实际解析 1 例（不需要全量跑 trace）；
3. **可达 FAIL**：临时把清单 `image` 改成 `bogus` ⇒ 明确报错（非 KeyError 栈）；
4. `make check-idl` 仍 272/272（未触碰主路径）。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
