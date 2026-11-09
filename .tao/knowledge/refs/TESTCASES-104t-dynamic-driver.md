# TESTCASES-104t：gem5 SE 动态档驱动与试点结果

> 范围：**驱动层**（`gem5_se_engine` + 三个 tset 驱动 + 基线编排器的 `--link-mode`）与**小规模试点**。
> 三套件 dynamic **全量**由主会话按套件跨机分片执行；本文不写全量计数，只给可复算的试点与复跑口径。

## 1. 驱动契约（实现事实）

- `static_gate(elf, interp_dir=...)` 取代原「只放行静态 ET_EXEC」：
  - `ET_DYN` 作**主程序** ⇒ `BLOCKED`（理由含 `ET_DYN main program`），语义保持；
  - 无 `PT_INTERP` 的 `ET_EXEC` ⇒ 放行（static 路径不变）；
  - `ET_EXEC + PT_INTERP` ⇒ 需 `interp_dir`（guest root）；未给或解释器在该 root 下不存在 ⇒ 在**启动 gem5 前**返回 `BLOCKED`（`cmd` 为空），不落成模拟器崩溃。
- `loader_args(guest_root)`：返回 `interp_dir=<root>` 与 `redirect=[("/lib", <root>/lib)]`。
  - **只映射库目录**：gem5 的 `RedirectPath` 在构造时给每条前缀补尾 `/`（`/lib` → `/lib/`），`Process::checkPathRedirect` 按表序做**纯前缀**匹配、命中即改写（不取最长）。因此 `("/", root)` 会把所有 guest 绝对路径（`/dev/null`、`/dev/zero`、`/tmp/...`）都劫持进只含 `lib/` 的 root。
  - QEMU 的 `-L` 只影响解释器/库搜索，不改 `/dev`、`/tmp`；`("/lib", <root>/lib)` 与之等价，其余路径原样落到宿主文件系统（与 static 路径一致）。
  - 不映射 `/usr/lib`：本工具链的动态程序只依赖 `libc.so`（musl 视为 self），root 里也只有 `lib/ld-musl-dadao.so.1`；需要时按同一形式追加。
- 三个 tset 驱动在 `--link-mode dynamic` 时把上述参数交给引擎；`--engine gem5-se --link-mode dynamic` 成为正式组合。
- `run_embench_user_suite.py` 增 `--filter`（试点用）：被过滤的运行是**声明子集**，closure 对 selected 集判定，不掩盖未执行项。
- 基线编排器 `run_gem5_se_baseline.py` 增 `--link-mode static|dynamic`（默认 static）：驱动命令按模式生成；dynamic 摘要写 `GEM5-021t-baseline-dynamic-summary.{json,md}`，不覆盖 static 快照；summary 记录 `link_mode`。
- SE 引擎层新增「ldso 在 main 前失败」判定：仅当错误指名**主程序**（`…(needed by <主 ELF>)` 或 `Error relocating <主 ELF>: …`）时记 `BLOCKED`，`gap=dynamic loader (ldso)`/`kind=ldso-abort`；`dlopen()` 失败属程序自身可观察行为，仍交语料 oracle。

## 2. 试点结果（每套件 3–4 例，gem5 SE 与 QEMU 同例）

- **libc-test dynamic**（`functional/argv`、`functional/memstream`、`api/main`）：gem5 SE 3/3 pass（约 2.1–2.4 s/例，含引擎固定开销）；QEMU 同 3 例 pass。
- **llvm-ts dynamic**（`SingleSource/Benchmarks/Shootout/{hello,nestedloop,objinst}`、`SingleSource/Benchmarks/Misc/lowercase`）：gem5 SE 4/4 pass（约 2.2–2.4 s/例）；QEMU 4/4 pass（0.1–0.2 s/例）。
- **embench dynamic**（`-O0`：`aha-mont64`、`crc32`、`edn`、`matmult-int`）：gem5 SE 4/4 pass（9.4–15.3 s/例）；QEMU 4/4 pass。
- **auxv**（自建动态探针，双引擎）：`AT_PAGESZ=65536` 两侧相等；gem5 侧 `AT_BASE=0x200000000`（GEM5-028t 的解释器基址）、QEMU 侧非零；两侧 `AT_BASE` 均页对齐且该地址为 ELF 魔数（解释器确实被装载）。
- **静态不退化**：同一驱动 `--link-mode static --engine gem5-se` 抽 2 例仍 pass，`run_cmd` 不含 `--interp-dir`。
- **反例**：`--interp-dir` 指向错误目录 ⇒ 驱动侧 `BLOCKED`（`interpreter missing`，未启动 gem5）；裸 gem5 同参数 ⇒ rc=1、`Failed to open file …/ld-musl-dadao.so.1`，失败明确。

## 2.1 回归修复：11 例假失败（首版全局 `/` redirect）

- **现象**：首版 `redirect=[(cwd,cwd), ("/", root)]` 在 libc-test dynamic 全量上产生 11 例 `gem5_only_fail`，全部 `ENOENT`：`functional/{fcntl,fdopen,fscanf,fwscanf,stat,ungetc,utime}`、`regression/{daemon-failure,fflush-exit,ftello-unflushed-append,syscall-sign-extend}`（`/dev/null`、`/dev/zero`、`/tmp` 被劫持进只含 `lib/` 的 root）。
- **根因**：gem5 `RedirectPath` 构造时给前缀补尾 `/`，`Process::checkPathRedirect` 按表序做纯前缀匹配、命中即改写；`("/")` 命中一切绝对路径。QEMU 的 `-L` 只影响解释器/库搜索，两者不等价。
- **修复**：`redirect=[("/lib", <root>/lib)]`，其余路径原样落宿主（与 static 路径一致）。
- **验证**：11 例 gem5 dynamic → **11/11 pass**；反向注入回 `("/", root)` → **11/11 fail**（其中 8 例输出直述 `errno`/`No such file`/`ENOENT`，3 例为 `writetemp`/`tmpfile` 的 "failed to make temp file"，同一根因）→ `cp`+`md5sum -c` 还原 → **11/11 pass**。
- **前后计数（libc-test dynamic 全量，340 例）**：`gem5_only_fail` 15（11 ENOENT + 4 已知环境）→ **0**；修复后 gem5 `pass=301 / fail=0 / known-fail=1 / blocked=38`（其中 timeout 4）、QEMU `pass=338 / known-fail=2`，交叉 `both_pass=301`、`qemu_only_fail=0`。
- 4 例环境缺口（`popen`/`spawn`/`vfork`/`execle-env`）由 static 下的 `fail` 变为 `blocked`（`gem5-fatal`：宿主无 DADAO `/bin/echo`，`--interp-dir` 下找不到其 x86 解释器），按已知环境缺口记、不计本次回归。

## 3. 已知能力缺口（回给实现任务，不在驱动里绕过）

- musl ldso 对**主程序**展开 `$ORIGIN` 时读 `/proc/self/exe`；gem5 SE 无该路径 ⇒ RUNPATH 失效。`functional/tls_align`（`tls_align_dso.so` 走 DT_NEEDED）因此 `BLOCKED`（`ldso-abort`），QEMU 同例 pass。
- 全量实测：`functional/dlopen` 通过（bare-name dlopen 没有走到 `$ORIGIN` 分支）；`regression/tls_get_new-dtv` 先撞 `syscall 283 (membarrier) not implemented`，`$ORIGIN` 缺口的可观察样本目前只有 `functional/tls_align`。
- 宿主无 DADAO `/bin/echo`：`popen`/`spawn`/`vfork`/`execle-env` 在 gem5 侧 `BLOCKED`（动态档为 `gem5-fatal`：`--interp-dir` 下找不到 `/bin/echo` 的 x86 解释器），QEMU 侧 pass；static 档同样存在（当时记 `fail`）。
- **ISS-357（输出写序）**：llvm-ts 4 例 `gem5_only_fail`（`FreeBench/analyzer`、`FreeBench/pifft`、`FreeBench/distray`、`Prolangs-C/bison`）全部复核为 fd1/fd2 分开捕获后串接、丢失真实写序；`analyzer`/`pifft` 的 `stderr+stdout+exit` 与参考逐字节相等、`distray` 的 md5 形式同值、`bison` 去掉中段 stderr 行后与 `stdout` 逐字节相等。修复前按 `fail` 记、不按能力缺口计。
- 不允许用 `LD_LIBRARY_PATH`/额外 `--redirect` 把 DSO 挪到搜索路径来「修绿」——那会掩盖 SE 的 `/proc` 缺口；同理不得把 `/dev`、`/tmp` 指进 guest root 来“修” ENOENT。

## 4. 速度基线（用于动态档预算，实测）

- 动态每例的 gem5 固定开销约 **2.2 s**（空载小程序也如此），来自装载器 + 进程建立。
- 重负载例 dynamic 与 static 同量级：`BitBench/five11` 动态约 280 M 指令 / 265 s ⇒ **≈1.1 M inst/s**；同一 ELF 的 static 运行实测亦 >2 min（未跑完，计时被截断），与「同程序指令数相近、同一 CPU 速率」一致；dynamic 的额外开销主要是装载器，不是逐条指令变慢。
- 因而 dynamic 沿用 `TESTCASES-103t` 的按套件预算（libc-test 300 s、llvm-ts 600 s、embench 300 s）即可；`llvm-ts` 静态轮已有 92/214 例在 600 s 到期，动态轮的 timeout 仍是预算问题、单列不计能力缺口。

## 5. 全量结果与复跑口径

- **三套件 dynamic 全量已完成（主控机同机 gem5+QEMU；libc-test 用 redirect 修复后的版本）**：QEMU `pass=590`、gem5 `pass=451`、`both_pass=451`；gem5 `blocked=43`（不含 timeout）+ `timeout=93`；`gem5_only_fail=4`、`qemu_only_fail=0`。分套件：libc-test 338/301（both 301，timeout 4）、llvm-ts 214/112（both 112，timeout 89，fail 4）、embench 38/38。完整计数与逐条归因见 `TESTCASES-104t-dynamic-summary.{json,md}`。
- 汇总命令：6 份驱动 JSON + `.driver.rc` 放同一目录后
  `python3 tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py --aggregate-only --link-mode dynamic --suites libc-test,llvm-ts,embench --work-dir <dir> --json-out <dir>/summary.json --summary-dir <dir>`
  （**`--json-out` 必需**，缺它 rc=2）；`absent` 即分片遗漏/并集不齐，须作废重跑。
- 实测耗时（`--jobs 32`）：libc-test gem5 约 5 min + QEMU 约 3 min；llvm-ts gem5 约 51 min（89 例 600 s 预算到期主导）+ QEMU 约 8 min；embench 两侧各约 1–2 min。
- 日志/EXIT：每套件驱动日志与 `*.drv-<suite>-<engine>.log`、`*.driver.rc` 落在运行期目录；外层命令落 `EXIT` 标记（禁 `tee` 吞退出码）。
- **跨机前提**：server208 的 QEMU-only 对照因 qemu/musl 二进制与主控机不同（md5/源 HEAD 均不同）**不可比**，未并入；其 `regression/malloc-brk-fail` fail 已隔离到该构建差异（非 ISS-343）。节点须先 `make sync-node-repo` + `make install-host`/`make build-musl` 并核对 md5。

## 6. 复跑

- 一键证据：运行期证据目录的 `run.sh`（`--quick` 跳过 llvm/embench 与 L1；`--inject-only` 只跑注入回环）。
- 试点命令等价于：三驱动 `--link-mode dynamic --engine {gem5-se,qemu}` + `--filter`/`--only`（embench 用 `--opt O0 --filter`）。

## 7. 门控状态（本任务现场）

- `check-knowledge-refs`、`check-run-artifacts`、`check-runner-reap`、编排器 `--self-test` 全 rc=0（A3 现场为 0 个非法新增日志名）。
- L1（`make check`）只有两项红，均为**外部**：`check-patch-tree`（共享 chipyard 源树被在途 m12 任务推进；本任务对 `components/chipyard` 的 diff 为 0）与 `check-temp-dirs`（5 个其它任务的非活动临时目录；未删除）。复跑 L1 前须先收口这两项。

