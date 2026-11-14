#!/usr/bin/env bash
# engine_parity_collect.sh — 拉回报告引用的逐例运行期产物（semi.out + sim.log），
# 让复核者不重跑批次也能抽查若干用例。
#
# 本文件是 `m12-chipyard-016` 证据脚本 `collect.sh` 的入仓版
# （`m12-chipyard-017`）：搬运内容与源路径原样保留，只把「脚本自身位置」的推导
# 换成 `--repo` / `--dest` / `--remote-repo` / `--node-map`，落点改证据目录。
#
#   bash tools/testcases/parity/engine_parity_collect.sh [embench|picolibc|all]
#        [--repo <根>] [--dest <目录>]
#        [--remote-repo <节点上的仓库根>] [--node-map <日志名>=<节点>]
#
# 落点默认 `<repo>/.work/evidence/<TASK>/cases/<node>/...`（运行期证据，永不入库）。
# **不落 `.work/log/`**：该目录受 L1 `check-run-artifacts` 的平铺命名约束
# （只允许 `check-<name>.log` 或 `<TASK-ID>-<purpose>.(log|json|txt)`），而这里
# 是 `<node>/<suite>/<case>/` 的逐例嵌套结构 —— 属证据树，放 `.work/evidence/`。
# 退出码 0 当且仅当每次复制都成功。
set -uo pipefail

TASK=m12-chipyard-016
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
DEST=
REMOTE_REPO=/home/ubuntu/DADAO-v5
WHAT=all

# 分片 → 节点（与 engine_parity_report.py 的 `SHARD_NODE` 同源，可覆盖）
NODE_server208=server208
NODE_ics180=ics180
NODE_ics160=ics160
NODE_ics150=ics150

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO=$2; shift 2 ;;
    --dest) DEST=$2; shift 2 ;;
    --remote-repo) REMOTE_REPO=$2; shift 2 ;;
    --node-map)
      kv=$2; shift 2
      key=${kv%%=*}; node=${kv#*=}
      case "$key" in
        m12-chipyard-016-embench.log) NODE_server208=$node ;;
        m12-chipyard-016-embench-a.log) NODE_ics180=$node ;;
        m12-chipyard-016-embench-b.log) NODE_ics160=$node ;;
        m12-chipyard-016-picolibc-chipyard) NODE_ics150=$node ;;
        *) echo "collect: unknown --node-map key $key" >&2; exit 2 ;;
      esac
      ;;
    embench|picolibc|all) WHAT=$1; shift ;;
    *) echo "collect: unknown argument $1" >&2; exit 2 ;;
  esac
done

[ -n "$DEST" ] || DEST="$REPO/.work/evidence/$TASK/cases"
mkdir -p "$DEST"
rc_all=0

# embench: <node repo>/.dadao/tests/m6-embench/<opt>/<bench>/{semi.out,sim.log}
for pair in "$NODE_server208:m12-chipyard-016-embench.log" \
            "$NODE_ics180:m12-chipyard-016-embench-a.log" \
            "$NODE_ics160:m12-chipyard-016-embench-b.log"; do
  node=${pair%%:*}
  [ "$WHAT" = "picolibc" ] && continue
  mkdir -p "$DEST/$node/embench"
  rsync -a --prune-empty-dirs \
    --include='*/' --include='semi.out' --include='sim.log' --exclude='*' \
    "$node:$REMOTE_REPO/.dadao/tests/m6-embench/" \
    "$DEST/$node/embench/" || rc_all=1
  n=$(find "$DEST/$node/embench" -name semi.out | wc -l)
  printf '  [collect] %-9s embench semi.out=%s\n' "$node" "$n"
done

# picolibc: <node repo>/.work/build/picolibc-tests-run/run/<name>/{semi.out,sim.log}
for pair in "$NODE_ics150:m12-chipyard-016-picolibc-chipyard.json"; do
  node=${pair%%:*}
  [ "$WHAT" = "embench" ] && continue
  mkdir -p "$DEST/$node/picolibc"
  rsync -a --prune-empty-dirs \
    --include='*/' --include='semi.out' --include='sim.log' --exclude='*' \
    "$node:$REMOTE_REPO/.work/build/picolibc-tests-run/run/" \
    "$DEST/$node/picolibc/" || rc_all=1
  n=$(find "$DEST/$node/picolibc" -name semi.out | wc -l)
  printf '  [collect] %-9s picolibc semi.out=%s\n' "$node" "$n"
done

echo "collect: dest=$DEST rc=$rc_all"
exit $rc_all
