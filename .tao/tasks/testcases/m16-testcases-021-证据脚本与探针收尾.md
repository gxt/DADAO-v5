# m16-testcases-021: 证据脚本与探针收尾（恒真式 / 默认 profile / 探针写反 / 挂死 fail 路径）

**模块**：testcases
**项目里程碑**：M16
**依赖**：相关任务均已合入（chipyard-003/009/010、testcases-003、qemu-001/002/003、11-cfx）
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

`m16-testcases-020` 处理 tests/arch 的 cfx5 I+D 与失败时限；本任务收口**证据脚本/探针自身的正确性**（恒真式、默认 profile、写反的探针、挂死的 fail 路径），这些不改变被检语义，但会让"看起来绿"或"失败形态不可判"。

## 要做

1. **恒真式（ISS-467⑤ / ISS-489 f1–f2 / ISS-492）**
   - 证据脚本 `rebuild … && eq … "$?"`：改为先取 `rc=$?` 再断言，禁止 `&&` 短路吞掉重建失败；
   - `merge-tree` 判据在无提交时恒真：改为"改动集 ∩ `HEAD..master`"兜底；
   - Tiny FIRRTL 计数在文件缺失时默认 0：缺文件应判红/显式跳过，不得静默；
   - `bin.qemu.install_eq_build` 在 `QEMU=` 覆盖时两侧同路径：覆盖时显式标 `N/A`，不得恒真。
2. **默认 profile 与信息行（ISS-518）**
   - `patch_tree_judge` 把"源树缺失、skipping"信息行计为问题 ⇒ 按 `check_patch_tree.py` 的信息行清单对齐；
   - `integ042t` 的 `_MACH` 默认 tiny 与 `node_probe_prelude` 默认 vast 不一致 ⇒ 统一默认 profile（或强制显式），漏设时给具名错误而非对称假红。
3. **探针写反（ISS-519②）**：`m16-qemu-001` 探针的 `SEL_I`/`SEL_D` 与 `cache_ctrl[15:14]`（2=I、1=D）写反 ⇒ 补正，并在该例加一条能暴露的断言。
4. **挂死 fail 路径（ISS-473）**：`tests/inst/11-cfx/escape_ciii_cfx.S` 链例 12 的注释与实测不符（第 3 次到达是双 lane 挂死，不是具名判红）⇒ 让 probe 在计数超限时走具名 `__EXIT`（或按实际改注释并登记该例不可用于回归）。
4. **`ptw_carrier_tlb` 缺参超时（`m16-testcases-020` 复核发现）**：`run_arch --cfx 4` 15/15 rc=0，但载体在缺 `--cfx-access` 时 20 s TIMEOUT（不走 `runlimit` env）；补齐调用参数或让缺参给具名 SETUP 错误，别表现为 20 s 超时。
5. **孤儿 QEMU（ISS-522 残余）**：外部强杀驱动会留下孤儿 QEMU 写满磁盘；证据脚本统一 `ulimit -f` + 显式 `killpg` 兜底（`runlimit` 已覆盖自身超时/超限）。
5. **写入证据**：每条改动在 `run.sh` 里配一条可达 FAIL（注入回退 ⇒ 红；`cp`+md5 还原回绿）。
6. **不改**被检语义、不改 `tests/arch` 的 cfx5 I+D/时限（属 `m16-testcases-020`）。

## 不做

- 不修 `ISS-519①`（QEMU I 侧不可独立观测，已由 `DIV-15` 登记）；
- 不修 chipyard `changelog`/`README` 的文档笔误（ISS-467①②③④、ISS-485、ISS-489 f3–f5 已关闭）。

## 约束

- 独立 `git worktree`；**不提交 git**；变更集限 `tools/**`、`tests/inst/**`、运行期证据脚本、本任务书；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 每个恒真式改后都有"注入重建失败/缺文件/覆盖 ⇒ 红"的可达 FAIL 证据；
2. `SEL_I`/`SEL_D` 纠正后有一条能区分 I/D 的断言；
3. 11-cfx case12 的 fail 路径为具名退出（或注释与实际一致并登记）；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、相关 `run_arch --self-test` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
