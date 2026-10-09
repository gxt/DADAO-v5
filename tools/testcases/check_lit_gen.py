#!/usr/bin/env python3
"""check_lit_gen.py — 生成 lit 用例的结构 + 编码校验（TESTCASES-037t）。

**独立于生成器**：本脚本**不 import** `generate_lit_vectors`；它自行从
`contracts/opcodes.yaml` 重新装载真源、重新分类（正例/反例）、重新解析
`; @src <id> <enc>` 与 `; OBJ:` 行，并对生成物做：

  1. **结构断言（成对/条数，§8.35）**：每个 `gen-<fmt>.s` 的 `@src` 集合必须
     等于 `opcodes.yaml` 中该 format 的正例记录集合（删任一用例/整文件 ⇒ FAIL）；
     正例文件内 `@src` 与 `OBJ` 条数必须相等且 >0；全部正例记录必须被覆盖。
  2. **正则命中自证（§8.34）**：逐文件打印 `@src`/`OBJ` 命中计数并断言 >0，
     不得「0 命中却全绿」。
  3. **编码一致性**：`; @src <id> <enc>` 的 enc 必须等于同行 `OBJ` 的 4 字节，
     且 `(enc & mask) == value`、`enc 匹配记录的 mnemonic`（独立自 opcodes.yaml）。

退出码：任一断言失败 ⇒ 打印 FAIL 行并 `exit 1`；全通过 ⇒ `exit 0`。
"""

import argparse
import glob
import os
import re
import sys

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPCODES = os.path.join(REPO, "contracts", "opcodes.yaml")
DEFAULT_FULL = os.path.join(REPO, "tests", "llvm", "lit", "MC", "DADAO-gen")
DEFAULT_FAST = os.path.join(REPO, "tests", "llvm", "lit", "MC", "DADAO",
                            "gen-fast.s")

# `; @src <id> [<enc-hex>] | <cite>`
SRC_RE = re.compile(r";\s*@src\s+(\S+)(?:\s+([0-9a-fA-F]{8}))?")
# `; OBJ: {{[0-9a-f]+:}} b0 b1 b2 b3{{.*}}<mnemonic>`
OBJ_RE = re.compile(
    r";\s*OBJ:\s+\{\{\[0-9a-f\]\+:\}\}\s+"
    r"([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})"
    r"\{\{.*?\}\}([A-Za-z][A-Za-z0-9._]*)")


class Checker:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def check(self, name, ok, detail=""):
        if ok:
            self.passed += 1
            print("PASS %s%s" % (name, (" — " + detail) if detail else ""))
        else:
            self.failed += 1
            print("FAIL %s%s" % (name, (" — " + detail) if detail else ""))
        return ok


def load_contract():
    with open(OPCODES, "r", encoding="utf-8") as fh:
        recs = _yaml.safe_load(fh)
    by_id = {r["id"]: r for r in recs}
    pos_by_fmt = {}
    positives = set()
    negatives = set()
    for r in recs:
        if r.get("scope") == "excluded" and r["mnemonic"] != "fence":
            negatives.add(r["id"])
        else:
            positives.add(r["id"])
            pos_by_fmt.setdefault(r["format"], set()).add(r["id"])
    return by_id, pos_by_fmt, positives, negatives


def parse_file(path):
    """返回 (sources, objs)；sources: [(lineno, id, enc_or_None)]；objs: [(lineno, word, mnem)]。"""
    sources, objs = [], []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            ms = SRC_RE.search(line)
            if ms:
                sources.append((i, ms.group(1), ms.group(2)))
            mo = OBJ_RE.search(line)
            if mo:
                b = "".join(mo.groups()[:4])
                objs.append((i, int(b, 16), mo.group(5)))
    return sources, objs


def check_positive_file(ck, path, ids_expected, by_id, tag):
    fname = os.path.basename(path)
    sources, objs = parse_file(path)
    src_ids = [s[1] for s in sources]
    # §8.34 命中自证
    ck.check("%s-src-hits[%s]" % (tag, fname), len(sources) > 0,
             "src=%d" % len(sources))
    ck.check("%s-obj-hits[%s]" % (tag, fname), len(objs) > 0,
             "obj=%d" % len(objs))
    # §8.35 成对（条数相等）
    ck.check("%s-paired[%s]" % (tag, fname), len(sources) == len(objs),
             "src=%d obj=%d" % (len(sources), len(objs)))
    # §8.35 结构：@src 集合 == 真源该 format 正例集合
    if ids_expected is not None:
        got, want = set(src_ids), set(ids_expected)
        ck.check("%s-id-set[%s]" % (tag, fname), got == want,
                 "missing=%s extra=%s" % (sorted(want - got), sorted(got - want)))
    # 编码一致性：逐条 @src(enc) ↔ OBJ ↔ opcodes
    bad = 0
    for (sln, sid, senc), (oln, oword, omn) in zip(sources, objs):
        rec = by_id.get(sid)
        if rec is None:
            bad += 1
            continue
        mask = int(rec["mask"], 16)
        value = int(rec["value"], 16)
        if senc is None or int(senc, 16) != oword:
            bad += 1
        if (oword & mask) != value or omn != rec["mnemonic"]:
            bad += 1
    ck.check("%s-enc[%s]" % (tag, fname), bad == 0,
             "mismatches=%d/%d" % (bad, len(sources)))
    return src_ids


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--full-dir", default=DEFAULT_FULL)
    ap.add_argument("--fast-file", default=DEFAULT_FAST)
    args = ap.parse_args()

    by_id, pos_by_fmt, positives, negatives = load_contract()
    ck = Checker()

    print("== check_lit_gen (TESTCASES-037t) ==")
    print("opcodes.yaml: positives=%d negatives=%d formats=%d"
          % (len(positives), len(negatives), len(pos_by_fmt)))
    print("-" * 72)

    # ── 全量档 ──
    files = sorted(glob.glob(os.path.join(args.full_dir, "gen-*.s")))
    file_fmts = set()
    covered = set()
    for path in files:
        stem = os.path.basename(path)[len("gen-"):-len(".s")]
        if stem == "excluded":
            sources, objs = parse_file(path)
            got = set(s[1] for s in sources)
            ck.check("full-id-set[gen-excluded.s]", got == negatives,
                     "missing=%s extra=%s"
                     % (sorted(negatives - got), sorted(got - negatives)))
            ck.check("full-no-obj[gen-excluded.s]", len(objs) == 0,
                     "obj=%d" % len(objs))
            continue
        file_fmts.add(stem)
        want = pos_by_fmt.get(stem)
        covered |= set(check_positive_file(ck, path, want, by_id, "full"))

    # 结构：文件集合 == 有正例的 format 集合（删整文件 ⇒ FAIL）
    ck.check("full-file-set", file_fmts == set(pos_by_fmt),
             "missing=%s extra=%s"
             % (sorted(set(pos_by_fmt) - file_fmts),
                sorted(file_fmts - set(pos_by_fmt))))
    # 结构：全量档覆盖全部正例记录
    ck.check("full-coverage", covered == positives,
             "missing=%s extra=%s"
             % (sorted(positives - covered), sorted(covered - positives)))

    # ── 快档（受控子集：非空、∈ 正例、成对、编码一致）──
    if os.path.isfile(args.fast_file):
        src_ids = check_positive_file(ck, args.fast_file, None, by_id, "fast")
        ck.check("fast-subset", set(src_ids) <= positives,
                 "extra=%s" % sorted(set(src_ids) - positives))
    else:
        ck.check("fast-exists", False, "missing %s" % args.fast_file)

    print("-" * 72)
    print("checks: %d passed, %d failed" % (ck.passed, ck.failed))
    return 1 if ck.failed else 0


if __name__ == "__main__":
    sys.exit(main())
