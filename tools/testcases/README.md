# tools/testcases — 原子探针（TESTCASES-056t）如何跑

本目录的 `run_atomics_probe.py` 是 `tests/inst/atomics/` 五个探针的驱动；期望值全部来自
`oracle_atomics.py`（纯 Python 语义模型，不 import 任何组件产物），探针只打印观测。

```sh
# 一次一种链接模式（static 先、dynamic 后，--json-out 必填）
python3 tools/testcases/run_atomics_probe.py --link-mode static \
    --json-out /tmp/opencode/TESTCASES-056t/static.json
python3 tools/testcases/run_atomics_probe.py --link-mode dynamic \
    --json-out /tmp/opencode/TESTCASES-056t/dynamic.json

# 可达 FAIL 自测（3 个注入：去互斥丢更新 / CAS 失败当成功 / a_barrier 退化）
python3 tools/testcases/run_atomics_probe.py --link-mode static \
    --json-out /tmp/opencode/TESTCASES-056t/inject.json --inject

# 全量证据（两档 + 047t 19 例 + QEMU-065t --strict + L1 + 注入）
bash .work/evidence/TESTCASES-056t/run.sh
bash .work/evidence/TESTCASES-056t/run.sh --inject
```

参数：`--rounds`（并发轮数，默认 5）、`--threads`/`--iters`（互斥计数，默认 4×250000）、
`--aba-iters`（Treiber 每线程 push/pop 对数，默认 10000）、`--jobs`、`--timeout`。
`--work-dir` 只放构建/运行中间物（默认 `/tmp/opencode/TESTCASES-056t/probe-work`）。

## 探针

| 文件 | 覆盖 |
| --- | --- |
| `tests/inst/atomics/counter.c` | N 线程 × M 次互斥自增，共享计数与各线程私有槽双路对账 |
| `tests/inst/atomics/c11_alltypes.c` | `_Atomic char/short/int/long/unsigned/size_t/void*` × load/store/exchange/fetch_*/CAS × 五种 ordering；另有共享对象单元 |
| `tests/inst/atomics/atomic_builtins.c` | `__atomic_*` 九种内建 × {1,2,4,8} 字节 × 五种 ordering；子字宽邻域字节不变；链接期无 `__atomic_*` 未定义符号 |
| `tests/inst/atomics/aba_treiber.c` | 版本号打包的 Treiber 栈（`{ver:16,ptr:48}`），不变量 + 确定性 ABA 重放 |
| `tests/inst/atomics/barrier_probe.c` | `a_barrier()` 结构断言（`fence` 计数 == 源码站点数，立即数 0xFFF） |

## ctrl 向量生成器（jump / call / ret / br）

```sh
python3 tools/testcases/generate_ctrl_jump_call_ret.py          # 写 tests/inst/base/ctrl-{jump,call,ret}.yaml
python3 tools/testcases/generate_ctrl_br.py                     # 写 tests/inst/base/ctrl-br.yaml
python3 tools/testcases/generate_ctrl_jump_call_ret.py --check  # 只读校验（byte-identical ⇒ rc=0）
python3 tools/testcases/generate_ctrl_br.py --check
```

`--check` 用与写盘**同一个渲染函数**重渲染后与磁盘逐字节比较：全部一致 → `PASS（N 册 byte-identical）`
rc=0；缺失/不一致 → 逐册 `FAIL` rc=1；未知参数 → rc=2。`--check` **不写盘、不建目录**。
落点受守卫约束：`OUT_DIR` 必须在 `tests/inst/` 之下，否则 `ERROR` + 非零退出
（防静默写回旧 `tests/vectors/isa`）。

## 已知缺陷（XFAIL 机制保留，登记已清空）

驱动把登记为 `xfail` 的单元按**精确缺陷签名**判 `XFAIL`；一旦恢复语义值即报 `XPASS`
并判红，提示删除对应 xfail 条目。语义面细节见 `tests/inst/atomics/*.c` 文件头与任务书完成区。

`ISS-312`（`atomic-store-address`）与 `ISS-313`（`narrow-cas-sext`）已随 `LLVM-121t`
返工修复，**登记表已清空**（20 条转为普通语义断言，两档 711/711 PASS）。机制本身仍保留：
`oracle_atomics.selftest_xfail()` 用合成观测在 `--inject` 下验证「签名命中→XFAIL /
语义恢复→XPASS 红 / 签名变化→红」。

原缺陷（存档）：
- `atomic-store-address`：`atomic_store`/`__atomic_store_n` 写共享对象时写入**对象地址**
  （后端 `LowerATOMIC_STORE` 取错 ATOMIC_STORE 操作数）。
- `narrow-cas-sext`：1/2/4 字节对象的 `compare_exchange`，比较值最高位置 1 时永不成功
  （提升后的 i64 比较值符号扩展 vs `lr.{b,w,t}` 零扩展）。
