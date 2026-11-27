# m16-testcases-020: tests/arch 收尾（cfx5 I+D 同选 + 失败形态时限/日志）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-009` 合入；`m16-testcases-012` 已合入
**可并行分片**：否（共享 `tests/arch/cache/`、`common/`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

- `ISS-517`：`m16-chipyard-017` 的 cfx5 维护探针缺「I+D 同选 + 合法操作」用例（`CTRL_ID_*` 只有 none/非法）⇒ `CACHE-21` 的"先 I 后 D"只有静态核验；`m16-testcases-009` 已补三方 cache 用例，但同选项仍缺。
- `ISS-522`：`tests/arch` 的 smon/umon 异常路径失败形态过重——载体未装载当前模式监视器时只能等 60 s 超时，且 carrier 开 `-d cpu`，实测单次失败写约 11.7 GB 日志（tmpfs 16 G 被打满）。

## 要做

1. **I+D 同选用例**：在 `tests/arch/cache/` 增加 `cache_ctrl` 的 I+D 同选 + 合法操作组合（至少 `I|invalidate` + `D|clean`、`I|clean` + `D|invalidate` 各一），三方逐槽或登记差异；映射到 `CACHE-21` 并更新 `vast-arch-inventory.md`。
2. **失败形态收紧**：`tests/arch` 的 carrier/`run_case` 增加"短 timeout"（默认 ≤10 s，可用环境变量放宽）与"失败时关闭/截断 `-d cpu` dump"；确保异常路径判红的形态不再写满磁盘（可注入"未装载监视器"复现）。
3. **不回归**：fence/power/ptw/pmem/time/cache 代表集；`run_arch --self-test`。

## 不做

- 不改模拟器/内核实现；
- 不改用例语义（只补用例与失败路径参数）。

## 约束

- 独立 `git worktree`；**不提交 git**；变更集限 `tests/arch/**`、`tools/testcases/arch/**`、本任务书；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. I+D 同选用例三方（或登记差异）通过，映射 `CACHE-21`；
2. 失败路径：超时 ≤10 s 且日志 ≤ 数百 MB（注入"未装载监视器"实测，贴实际大小）；
3. **可达 FAIL ≥2**：注入"删同选用例"、"把 timeout 改回 60 s/dump 全开" ⇒ 红/可观测；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、`run_arch --self-test` 记录 rc。

## 完成区

**测试结果**：证据脚本 44 项全过（`run.sh` rc=0）；RTL 腿 BLOCKED（遗留 1）。
**修改文件**：新增 `tests/arch/common/runlimit.py`；`tests/arch/cache/{cache.body.S,cache_rtl.S,cache_oracle.py,expected.yaml,check_cache.py,check_cache_rtl.py,README.md}`；`tests/arch/common/check_mode_env.py`、`umon/umon_fence.py`、`time/check_time.py`、`hart/check_hart.py`、`pmem/check_pmem_dma.py`、`power/power_vast.py`；`tools/testcases/arch/{node_probe_prelude.py,run_m5_e2e.py}`；`tests/arch/{README.md,vast-arch-inventory.md}`。
**验收结果**：
- 门控 rc：`check-tests-index` 0、`check-tasks` 0、`check-knowledge-refs` 0、`run_arch --self-test` 0。
- I+D 同选：`arch-cache-001` 18→21 槽（新增 `id_invalidate_nodrop`/`id_flush_refetch`/`id_clean_writeback`），qemu+gem5 × hmon/smon/umon 全 PASS 且跨平台逐槽一致（21 槽）；`expected.yaml` 与现场派生双向一致。
- 失败形态：smon「未装载监视器」注入实测 `dump_bytes=17171`（落盘 17 171 B、`timeout_s=10`、墙钟 10 s、`capped=False`）；注入「60 s / dump 全开」⇒ 13 s 写 2 466 145 985 B（按速率 60 s ≈ 11.4 GB）⇒「有界」断言不成立（可达 FAIL）；上限调 4 KiB ⇒ rc=-3、`dump_capped=True`、判据红。
- 可达 FAIL ≥2：删 `id-combined` 登记 ⇒ selfcheck 红 + run_arch 红；60 s/全开 ⇒ 有界断言红。还原：`cp`+md5 三项对账一致（expected.yaml `699d70…`、body `b870bc…`、runlimit `86aa51…`），还原后 hmon/selfcheck 回绿。
**新发现/坑**：
1. 控制字的操作（`[1:0]`）/范围（`[3:2]`）两维**两侧共用**（CACHE-09/10）⇒ 任务书写的「`I|invalidate` + `D|clean`」逐侧不同操作不可编码；同选面按 clean/invalidate/flush 三条覆盖，`11|flush` 的 D 侧即「写回+丢弃」，先 I 后 D 由 RTL 日志核。
2. 本机 `-d cpu` 实测 ~200 MB/s（60 s ≈ 11–12 GB）；`-dfilter` 只压正常路径，失败路径**必须**靠运行中上限才有界。
3. 外圈 `timeout` 杀驱动会留下孤儿 QEMU 继续写 dump（曾写满 `/`）；证据脚本用 `ulimit -f` + 显式 kill 兜底。
4. 直接调 `check_mode_env` 必须带 `--cfx-access 0`（`modes.yaml` 声明 `umon`），否则 CFXPERM 也表现为同一超时形态。
**遗留问题**：
1. **RTL 腿未验证（基线红）**：本机 Vast Verilator（07:44 重建）上未改动的 `arch-cache-002` 与本任务 `arch-cache-001` 同样在 ENTRY+4 陷入 trap/escape 循环（cfx5 访问 0 次；200k cycle 探针 389 次 escape）⇒ 基线红非本任务引入；`cache_rtl.S` 的三条同选命令 + 日志「先 I 后 D」断言按同一槽序写好，待 sim 修复后复跑三方。
2. `ptw_carrier_tlb.py` 本机基线红（master 同 rc=TIMEOUT、0/30），与本任务无关，疑与 ISS-520 安装根/共享 probes 状态相关。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `runlimit.run` 只杀直接子进程（gem5 shim 会再起 gem5） | ✅已修 | `start_new_session=True` + `killpg(SIGTERM→SIGKILL)` | 证据 7b 外圈杀后无孤儿（脚本再兜底 kill） |
| 失败后 dump 仍留满量（数十 MB~GB） | ✅已修 | `finish_dump()` 失败/超限截断到 1 MiB | 7a 落盘 17 171 B |
| 长跑正常路径也可能写爆 dump（无窗口的载体） | ✅已修 | `check_mode_env`/`umon_fence`/`check_time` 补 `-dfilter`（观测过滤，不改语义） | 无窗口注入 1 s 写 208 MB（前测）；加窗口后 17 KB |
| 「I+D 同选」按逐侧不同操作写用例（合约不允许） | ✅已修 | 改为三条合法命令（clean/invalidate/flush）；inventory/README 写明编码约束 | `check_cache --selfcheck` PASS；qemu/gem5 三模式 PASS |
| oracle 槽序插在中间 vs body 写在末尾 | ✅已修 | `SLOTS`/`expected()` 移到末尾（与 body 一致） | selfcheck「登记 == 派生」PASS |
| `check_hart.py` 的 `_toolchain` try/except 被误删 | ✅已修（编辑期发现） | 恢复并补 `RunLimitError` | `check_hart --selfcheck` PASS、regress PASS |
| 证据脚本 `check` 第 4 参数误用（期望判红的项记成检查失败） | ✅已修 | 判红项第 4 参数记 0 | `run.sh` 44/44 PASS |
| zsh/bash 反引号在双引号 echo 里被执行 | ✅已修 | 改单引号 | 复跑无 `command not found` |
| RTL 三项同选命令未实跑 | ⏸延后 | — | 基线红（遗留 1），已给基线同形态证据 |

### 第 2 轮 reviewer 验收（独立重跑，2026-11-25）

**重跑记录（本机现场 rc，不采信完成区）**
- 运行期证据目录内 `run.sh`（全量含 RTL 腿）连跑两次：`RESULT: PASS（44 项）`、`RUNSH_RC=0`；`--inject` 单独跑 `PASS（16 项）` rc=0。
- 门控独立重跑：`make check-tests-index`=0、`make check-tasks`=0、`make check-knowledge-refs`=0；`run_arch --self-test`=0、`check_cache --selfcheck`=0（「arch-cache-001 期望 21 槽」命中）。
- 失败形态实测（我方）：缺省 `dump_bytes=17171 / timeout_s=10 / elapsed=10s / capped=False`、driver rc=1（内部 -2）；`DADAO_ARCH_DUMP_MAX=4096` ⇒ `exit_code=-3、dump_capped=True`；注入「60 s+dump 全开」⇒ 13 s 写 2 416 619 520 B（≈11.2 GB/60 s）⇒「有界」断言不成立。
- 缺省等价：`check_mode_env` hmon/smon/umon 全 rc=0（dump 188 881 B）、`run_m5_e2e` 10/10 rc=0（4 s）、gem5 `arch-power-001` 3 s / `arch-time-001` 1 s rc=0、`DADAO_ARCH_TIMEOUT=42` ⇒ `timeout_s=42`（非法值显式抛错、不回退）。
- 回归（run.sh §5，qemu）：fence 012/013、power-001、time-001、hart-001、pmem-001、cache-002/003/004、cfx4 15 probes 全 rc=0。
- 注入 3 路（脚本自带）：删 `id-combined` ⇒ selfcheck 红 + run_arch 红；60 s/全开 ⇒ 有界断言红；未装载监视器 ⇒ 17 KB/10 s 判红；`cp`+md5 还原回绿（runlimit `86aa51…`、expected `699d70…`、body `b870bc…`）。
- 我方独立注入（非脚本自带）：`runlimit.py` `DEFAULT_TIMEOUT 10→60`（注入前 `cp`+md5=86aa51…）⇒ `run.sh --inject` **FAIL（2/16）rc=1**（`时限=60`、有界断言成立）⇒ `cp` 还原 md5 相等 ⇒ 复跑 **PASS（16/16）rc=0**。

**基线红对照（`git archive HEAD` 解到运行期对照树，同 sim 同参跑 `arch-cache-002`）**：对照树 rc=1 / 工作树 rc=1，`run.json` 均 `exit_code=-2`，`ha= 5`（cfx5 访问）两侧均 0；sim 日志归一化后**前 174 919 行逐行相同**（diff 0 行），仅工作树多 688 行（墙钟超时点不同）⇒「与基线逐行相同」成立，RTL 阻塞非本任务引入；`arch-cache-001` 同形态 rc=1、cfx5=0。

**I+D 编码结论**：核 `spec/DADAO-12 §4.6`（`cfx_cache_ctrl` 单一操作 `[1:0]` + 范围 `[3:2]` + 选择 `[15:14]`）与 `contract-cache` CACHE-09/10/21 ⇒ 任务书的「逐侧不同操作」确不可编码；`11|invalidate/flush/clean` 即同选面全部合法操作，落 `arch-cache-001` 新 3 槽（合计 21 槽），登记↔派生双向一致、qemu+gem5×三模式 PASS；顺序在签名槽无可观测差、由 RTL 日志断言（未实跑）⇒ 判**正确的替代、非遗漏**；「是否改 spec 允许逐侧操作」属语义变更，只登记（inventory 未覆盖段 + cache/README）不改 spec。

**runlimit 接入（grep 清单）**：`check_cache / check_time / umon_fence / check_mode_env / power_vast / check_hart / check_pmem_dma / run_m5_e2e / node_probe_prelude` 全接入，`-d cpu` 使用者全覆盖；`ptw_carrier_tlb` 经 prelude 接入但 `dump=False`、`TIMEOUT=20` 写死。

**约束核验**：变更集 18 修改 + 1 新增，与完成区「修改文件」逐条一致，全在 `tests/arch/**`、`tools/testcases/arch/**`、本任务书内；审查前后 `git status --porcelain -uall` 快照**逐行相同**（19 行）、目标文件 md5 与注入前一致；任务书无运行期/临时/绝对路径；未提交 git。

**findings（不阻断，交 architect）**：① RTL 断言 #6 的 `if not i_side_code` 分支不可达（同 run 更早的 I invalidate/flush 已在代码行留 icache 事件）⇒ I 侧缺失时顺序检查静默通过，建议按 `d_flush_code[0]` 的 cycle 取窗（I 侧效果另有 `id_flush_refetch` 签名槽兜底）。② 完成区遗留②不可复现：`run_arch --cfx 4` 15/15 rc=0，载体补齐 modes.yaml 的 `--cfx-access` 后三模式均 <1 s PASS，仅缺参时复现 20 s TIMEOUT ⇒ 疑调用缺参而非 ISS-520，请改写。③ `ptw_carrier_tlb` 20 s 未走 env（无 dump、无磁盘风险）。④ 非法 `DADAO_ARCH_TIMEOUT` 抛未捕获 traceback、rc=1（非 SETUP rc=2），仍属显式失败。⑤ dump 运行中上限对「退出时一次性落盘」不触发（1024 B 上限下正常跑 dump 188 881 B、`dump_capped=False`），失败路径由 `finish_dump` 截 1 MiB 兜底。⑥ 遗留③（孤儿 QEMU 写满 `/`）建议并入 ISS-522 描述。

**判决：Accepted** —— 验收命令在我方重跑下全绿、约束无违反；RTL 腿 BLOCKED 与 ①–⑥ 为 finding（②⑥ 属文档级，由 architect 收尾改）。
