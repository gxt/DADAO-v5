# TESTCASES-068t: qemu-user OOM 修复（`-R 4G` + `flockfile-list` known-fail）

**模块**：testcases
**项目里程碑**：M10
**依赖**：QEMU-075t（诊断）
**状态**：待开始

## 背景（范围：只修 ISS-255/257 的 OOM 面）
QEMU-075t 结论：
- `setenv-oom`、`pthread_create-oom`：guest 把 VA 填满 ⇒ qemu 自身 `g_malloc` 失败 → `QEMU internal SIGTRAP`；**`-R 4G` 实测四例转绿**（静态+动态）。
- `flockfile-list`：语料自带 `malloc` 基址 4 mod 8 ⇒ guest `SIGBUS`（语料问题，**修不了**）⇒ known-fail。
- **不做**：llvm-ts/ISS-266（另立 `TESTCASES-069t`）、判据全面重构、全量夜跑。

## 改动
1. `tools/testcases/run_libc_test_user_suite.py`：
   - qemu 启动行加 `-R 4G`（`:1142` 附近）；新增 `--reserved-va`（默认 `4G`，可 `none` 关闭），说明 guest VA 限 4 GiB。
2. `flockfile-list` 记 **known-fail**（用现有 `GAP_SIGNATURES`/known-fail 机制，精确 case，附 ISS-255 指针）；**不削弱**其它断言。
3. 若 `setenv-oom`/`pthread_create-oom` 仍需特判，优先靠 `-R` 让其自然 pass；不要为过测而放宽判据。
4. issue：ISS-255（setenv-oom 修 + flockfile known-fail）、ISS-257 可关；ISS-266 不动。

## 验证（定向，分钟级；**不跑全量、不跑 llvm-ts**）
```bash
python3 tools/testcases/run_libc_test_user_suite.py --link-mode static \
  --filter 'setenv-oom|pthread_create-oom|flockfile-list' --json-out /tmp/opencode/TESTCASES-068t/static.json
python3 tools/testcases/run_libc_test_user_suite.py --link-mode dynamic \
  --filter 'setenv-oom|pthread_create-oom|flockfile-list' --json-out /tmp/opencode/TESTCASES-068t/dynamic.json
```
- 期望：setenv-oom / pthread_create-oom **pass**；flockfile-list **known-fail**；**0 blocked**。
- 回归：至少 2 个不相关 libc 用例（如 `heapsort`/`qsort`）在带 `-R` 下输出与不带一致。
- `make check` rc=0；`--help` 含 `--reserved-va`。

## 约束
- 只改 `run_libc_test_user_suite.py` + `issues.yaml` + 任务书/`milestones.md`；不改 qemu/spec/contracts/其它 driver。
- 反例注入还原用 `cp`+md5；临时目录 `/tmp/opencode/TESTCASES-068t/`；不提交。
- 无夜跑全量；定向验证即可收口。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
