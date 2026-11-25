# m20-testcases-005: picolibc harness `.done` 复用键纳入输入指纹（ISS-504）

**模块**：testcases
**项目里程碑**：M20
**依赖**：无（picolibc 安装根已就绪）
**可并行分片**：否（单 harness）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

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

**测试结果**：运行期证据目录内的 `run.sh` rc=0，`ALL PASS`；picolibc qemu 代表性例 `semihost-exit` 每次 rc=0。
**修改文件**：`tests/ee-tiny/run_picolibc_tests_tiny.py`；本任务书。证据脚本/辅助脚本在运行期证据目录。
**验收结果**：
1. 旧行为复现：分叉点 `38b0111f` 的 harness 首跑 `.done` 为 `fingerprint=""`、`sim_md5=null`；改沙箱 lds `895e…`→`7a47…` 后二跑 rc=0，输出 `reused (same sim md5)`（`old2.log`）。
2. 修复后同一 run 目录（旧 `.done` + 换 lds）：重跑并写 `fingerprint=82c8…`；相同输入二跑 `reused (same input fingerprint 82c8fe9d1667)` 且 `.done` mtime 未变（复用）；不同输入必须重跑。
3. `--force`/`--no-reuse`：同输入仍强制重跑，`.done` mtime 前移；`--help` 同时列出两别名。
4. 指纹字段（现场打印）：libc.a `aac3…`、picolibc.ld `895e…`、clang `6f8e…`、ld.lld `022e…`、bootrom `a5d7…`、qemu `8b49…`、simulator `n/a (engine=qemu)`；chipyard 走同一函数，`simulator=md5:<sim>`（指纹探针全 PASS）。
5. 可达 FAIL：临时副本去掉 `fingerprint == fingerprint` 比较后，换 lds 仍 `reused`（红）；`cp` 还原（md5 `ab5f4c1f…`）后同输入重跑（绿）；真实 harness md5 全程未变。
6. 门控：`check-tests-index` rc=0（504 条）、`check-knowledge-refs` rc=0；`check-patch-tree` rc=2，24 条仅 gem5/musl（未触碰组件，KNOWN-RED `ISS-507`）。
**新发现/坑**：`writer_guard.md5_of` 已给稳定占位（`missing`/`unreadable:<errno>`），指纹直接复用；`ReadGuard.before` 复用 4.1 GiB clang 的哈希，避免每轮二次哈希。指纹输入同时加入 read guard 路径（lds/libsemihost/crt0），中途被重建会按 ISS-373 判 fail，而不是写出旧 key 的 `.done`。任务 worktree 的运行期目录是共享软链，`--work-dir` 必须显式指到临时目录以免污染主仓默认 run 目录。
**遗留问题**：无（`check-patch-tree` 的 24 条为既有 KNOWN-RED `ISS-507`，与本任务无关）。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| qemu 下 `sim_md5=None` 使复用键退化为 `None==None` | ✅已修 | 新增 `input_fingerprint()`（libc.a/libsemihost/lds/crt0×2/crt0 stub/clang/ld.lld/llvm-mc/llvm-objcopy/bootrom/qemu/engine/simulator），`.done` 存并比较该 sha256 | 旧 harness 换 lds 仍 `reused (same sim md5)`；新 harness 同场景重跑 |
| 旧 `.done`（无指纹）可能被复用 | ✅已修 | `info.get("fingerprint") == fingerprint`，缺失即不匹配 | 手工剥离 fingerprint 的 `.done` 触发重跑（mtime 前移） |
| 缺强制重跑开关 | ✅已修 | `--force`，别名 `--no-reuse`；同时忽略陈旧 `.claim`/`sim.log` 终态 | 同输入 `--force` 重跑、mtime 前移；`--help` 两别名可见 |
| qemu/chipyard 语义不一致 | ✅已修 | 两引擎共用 `input_fingerprint()`；不可得字段用稳定占位并随运行头/JSON 打印 | 指纹探针：chipyard `simulator=md5:deadbeef`、qemu `n/a (engine=qemu)` |
| 输入在批次中途被替换会写出旧 key 的 `.done` | ✅已修 | read guard 路径加入 lds/libsemihost/crt0 | `check-writer-guards` 未改列表；实跑 writer-guard start/finish 正常 |
| 断言无 FAIL 路径 / 证据依赖先删 `run/` | ✅已修 | 临时树注入（去掉指纹比较）＋ `cp`+md5 还原；证据显式复用同一 `--work-dir` | 红：换 lds 仍复用；绿：还原后重跑；真实 harness md5 `ab5f4c1f…` 未变 |
| 编辑期重复 executor 块 / `%`+`+` 表达式 | ✅已修 | 自审清理重复块并 `py_compile` | 4 次真实 harness 运行均 rc=0，输出符合预期 |

判决：以上 finding 全部已修，无未修项，状态置「待验收」。

#### 第 1 轮 reviewer 验收

**审了什么**：`run.sh` / `run_harness.py` / `fingerprint_probe.py` 逐条审（每条断言均有可达 FAIL，无恒真、无两支同果）+ harness diff + `writer_guard.md5_of`（`missing`/`unreadable:<errno>` 稳定占位）+ `claim_case`/`finish_case`/`input_fingerprint` 逻辑。
**重跑**（仓库根执行运行期证据目录内的 `run.sh`，取码用 `cmd; echo $?`）：
1. 干净树首跑 `m20-testcases-005 evidence: ALL PASS`、`RUN1_EXIT=0`（343 s）。旧行为复现：分叉点 `38b0111f` 首跑 `.done` 为 `fingerprint='' sim_md5='None'`，沙箱 lds `895e7cfa→7a477608` 后基线 harness 二跑 rc=0 且 `reused (same sim md5)`；修复后同 run 目录重跑写 `fingerprint=82c8fe9d1667…`、`相同输入二跑 reused (same input fingerprint 82c8fe9d1667)` mtime `1795618304` 不变、`--force` mtime `1795618304→1795618386`、手工剥离 fingerprint 的 `.done` mtime `1795618406→1795618428`。
2. **独立注入**（我改被测产物 `tests/ee-tiny/run_picolibc_tests_tiny.py`：`cp` 备份 md5 `ab5f4c1f…`，把 `info.get("fingerprint") == fingerprint` 换成 `True`，md5 `8dc40447…`）后重跑同一 `run.sh`：`evidence: FAIL`、`RUN2_INJECT_EXIT=1`，行为级红：`[FAIL] 旧 .done 未失效/未重跑（rc=0 fp=''）`、`[FAIL] 无指纹 .done 被复用（mtime 1795618792 -> 1795618792）`。
3. `cp` 还原 + `md5sum -c` OK（`ab5f4c1fe06c929afea707978610c3ef`）后重跑：`ALL PASS`、`RUN3_RESTORE_EXIT=0`；全程无 `git checkout/restore/stash`。
4. 门控（我自跑）：`check-tests-index rc=0`（结果: PASS，504 条）、`check-knowledge-refs rc=0`、`check-patch-tree rc=2`（第 1 次 25 条 = gem5 23 + musl 2，第 3 次 24 条），非 gem5/musl 组件集合为空 ⇒ 未触碰组件总红，KNOWN-RED `ISS-507`。
5. 独立探针（不依赖 `run.sh` 断言）：`claim_case` 同指纹无 force=`reused`；force 且无活 sim=`ok`；cmdline 含 `+loadmem=<elf>` 的活进程在跑时 force=`claimed`（仍拒绝），sim 结束后 force=`ok` ⇒ `--force` 仅绕过复用、不绕过运行中的 simulator。
6. 指纹真实性：运行头 `qemu=md5:8b49d6d9ea9c39dc2dffc1ca7d02739b`、`clang=6f8e185d…`、`ld.lld=022e1e85…`、`libc.a=aac3f8c6…` 与我直接 `md5sum` 磁盘文件逐字相同；`simulator=n/a (engine=qemu)`，chipyard 走同一 `input_fingerprint()`（probe `simulator=md5:deadbeef` PASS）。qemu 代表性例 `--stage fast --only semihost-exit` 每轮 rc=0；未跑 `make install-host`（安装根 qemu mtime 仍 15:44:57）。
**约束核验**：`git status --porcelain -uall` 前后均为 2 行 = `tests/ee-tiny/run_picolibc_tests_tiny.py` + 本任务书；`run.sh` 第 8 段同判；未触 `components/**`、`tests/inst/**`、`spec/`、契约、`Makefile`；任务书与本记录无具体 `.work/**`/临时/家目录路径；分支 `m20-testcases-005`，未提交 git。
**判决**：Accepted。
**遗留**：① `check-patch-tree` 条数现场 24↔25（并发 gem5 任务改补丁树），完成区写 24 属现场值笔误级差异，非门控判据；② `--force` 分支会 unlink 遗留 `.claim`，与另一池并发时有理论双写窗口（`_elf_running` 在其之前已拦活 sim），建议后续单独评估，不阻断本轮。
