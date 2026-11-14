#!/usr/bin/env bash
# sync_node_artifacts.sh — 把主控机的**评测产物**同步到评测节点（幂等，md5 校验）。
#
# 背景（用户 2026-11-14）：ics 节点上产物是 11-13 的旧构建，没人用导致全空转；
# 本脚本只同步**必要的二进制/工具链**，并用 md5 逐件校验，使各节点与主控机一致。
#
# 同步对象（可重建，节点侧只读用）：
#   .work/source/chipyard/sims/verilator/simulator-chipyard.harness-WumingTinyConfig
#   .work/build/qemu/qemu-system-dadao
#   .work/source/gem5/build/DADAO/gem5.opt
#   .dadao/cross-toolchain/{bin,lib}            （默认同步；TOOLCHAIN=0 可跳过）
#
# 用法:
#   tools/infra/sync_node_artifacts.sh                       # 用 $DADAO_NODES
#   tools/infra/sync_node_artifacts.sh ics150,ics160,...
#   REPO=~/DADAO-v5 TOOLCHAIN=0 tools/infra/sync_node_artifacts.sh ...
#   DRY_RUN=1 ...                                            # 只打印计划
#
# 退出码: 0 = 全部节点逐件 md5 与主控机相同；非零 = 任一失败。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

HOSTS="${1:-${DADAO_NODES:-}}"
REMOTE_REPO="${REPO:-~/DADAO-v5}"
DRY="${DRY_RUN:-0}"
TOOLCHAIN="${TOOLCHAIN:-1}"

if [ -z "$HOSTS" ]; then
    echo "sync_node_artifacts: ERROR: 没有节点清单；传参数或用 DADAO_NODES" >&2
    exit 2
fi

FILES=(
  ".work/source/chipyard/sims/verilator/simulator-chipyard.harness-WumingTinyConfig"
  ".work/build/qemu/qemu-system-dadao"
  ".work/source/gem5/build/DADAO/gem5.opt"
)
DIRS=()
[ "$TOOLCHAIN" = "1" ] && DIRS=(".dadao/cross-toolchain/bin" ".dadao/cross-toolchain/lib")

fail=0
IFS=',' read -ra ARR <<< "$HOSTS"
for host in "${ARR[@]}"; do
    echo "---- $host"
    if ! ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" true 2>/dev/null; then
        echo "  ssh FAIL"; fail=1; continue
    fi
    ssh -o BatchMode=yes "$host" "mkdir -p '$REMOTE_REPO/.work/source/gem5/build/DADAO' '$REMOTE_REPO/.work/build/qemu' '$REMOTE_REPO/.work/source/chipyard/sims/verilator'" </dev/null
    for f in "${FILES[@]}"; do
        src_md5=$(md5sum "$f" 2>/dev/null | cut -d' ' -f1 || true)
        if [ -z "$src_md5" ]; then echo "  skip (missing): $f"; continue; fi
        dst_md5=$(ssh -o BatchMode=yes "$host" "md5sum '$REMOTE_REPO/$f' 2>/dev/null | cut -d' ' -f1" || true)
        if [ "$src_md5" = "$dst_md5" ]; then
            echo "  same: $f"
            continue
        fi
        if [ "$DRY" = "1" ]; then echo "  [dry-run] rsync $f -> $host:$REMOTE_REPO/${f%/*}/"; continue; fi
        if rsync -a "$f" "$host:$REMOTE_REPO/${f%/*}/" >/dev/null 2>&1; then
            after=$(ssh -o BatchMode=yes "$host" "md5sum '$REMOTE_REPO/$f' | cut -d' ' -f1")
            if [ "$after" = "$src_md5" ]; then echo "  synced+md5 OK: $f"; else echo "  md5 MISMATCH: $f"; fail=1; fi
        else
            echo "  rsync FAIL: $f"; fail=1
        fi
    done
    for d in "${DIRS[@]}"; do
        [ -d "$d" ] || { echo "  skip (missing dir): $d"; continue; }
        if [ "$DRY" = "1" ]; then echo "  [dry-run] rsync $d/ -> $host:$REMOTE_REPO/$d/"; continue; fi
        if rsync -a --delete "$d/" "$host:$REMOTE_REPO/$d/" >/dev/null 2>&1; then
            echo "  synced dir: $d"
        else
            echo "  rsync FAIL (dir): $d"; fail=1
        fi
    done
    # 逐件最终校验
    if [ "$DRY" != "1" ]; then
        ok=1
        for f in "${FILES[@]}"; do
            a=$(md5sum "$f" 2>/dev/null | cut -d' ' -f1 || true)
            b=$(ssh -o BatchMode=yes "$host" "md5sum '$REMOTE_REPO/$f' 2>/dev/null | cut -d' ' -f1" || true)
            [ -n "$a" ] && [ "$a" != "$b" ] && { echo "  verify FAIL: $f"; ok=0; }
        done
        [ "$ok" = "1" ] && echo "  verify: OK" || fail=1
    fi
done

[ "$fail" = "0" ] && echo "sync_node_artifacts: PASS" || echo "sync_node_artifacts: FAIL"
exit "$fail"
