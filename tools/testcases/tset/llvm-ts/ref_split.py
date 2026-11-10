#!/usr/bin/env python3
"""Split an upstream single-stream reference into stdout / stderr channels.

The corpus' reference output is one *interleaved* document: upstream's
``RunSafely.sh`` points the program's stdout and stderr at the same file and
then appends a bare ``exit N`` line (``tools/timeit.c``), so comparing one
engine's captured stream against that document byte-for-byte also pins the
*interleaving* -- a libc buffering artefact, not ISA behaviour.

This module derives the per-channel references **once, deterministically**,
using the program's own sources as the authority:

1. the ``exit N`` tail is split off (RunSafely's bytes, not the program's);
2. every ``fprintf``/``vfprintf``/``fputs`` call whose stream argument is
   ``stderr`` (directly or through a ``#define X stderr`` alias) contributes a
   byte pattern built from its format string; a ``#define NAME "text"`` macro
   used as the format is resolved to its literal text;
3. the body is scanned left to right: at each position the patterns are tried
   longest-regex-first and the first *allowed* match wins; its bytes go to the
   stderr channel, every other byte goes to stdout.  Order inside each channel
   is therefore the write order of that channel;
4. pattern classes keep short literals from eating stdout text: a numeric-only
   format ("%d\\n") is only used when it covers a whole line; a short literal
   text ("Rolled ") may open or continue a stderr run but not appear mid-line;
   pure whitespace ("\\n") may only *continue* a stderr run.

Everything is a partition: no byte is invented, dropped or reordered, and
``stdout 行数 + stderr 行数 == 原参考行数`` (asserted; a mid-line boundary is
counted and reported, not silently accepted).

A document that cannot be split raises :class:`SplitError` -- never a guess,
never a silent skip.  Hash-form references (``HASH_PROGRAM_OUTPUT``: the whole
reference is one md5 line) are rejected explicitly: a digest carries no bytes
to attribute.

CLI::

    python3 tools/testcases/tset/llvm-ts/ref_split.py --stats
    python3 tools/testcases/tset/llvm-ts/ref_split.py --write
    python3 tools/testcases/tset/llvm-ts/ref_split.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
# Append, not insert: this file lives next to the real
# ``run_llvm_ts_user.py`` and must import *that* one, not the legacy flat
# wrapper under ``tools/testcases/`` (same module name).
sys.path.append(os.path.join(REPO_ROOT, "tools", "testcases", "lib"))
sys.path.append(os.path.join(REPO_ROOT, "tools", "testcases"))
sys.path.insert(0, HERE)

# The committed split lives next to the llvm-ts assets, not in the fetched
# corpus (which is a regenerable checkout).
SPLIT_DIR = os.path.join(REPO_ROOT, "tests", "tset", "llvm-ts", "refs")
INDEX_NAME = "index.tsv"

# A format whose literal text (outside conversions) is shorter than this cannot
# identify a line: "%s\n" / "%d\n" would match almost anything.
MIN_LITERAL = 8

_EXIT_TAIL = re.compile(rb"exit ([0-9]+)\n\Z")
_INCLUDE = re.compile(rb'^\s*#\s*include\s+"([^"]+)"', re.M)
_STDERR_DEFINE = re.compile(rb"#\s*define\s+([A-Za-z_]\w*)\s+stderr\b")
_STRING_DEFINE = re.compile(
    rb'#\s*define\s+([A-Za-z_]\w*)\s+("(?:[^"\\]|\\.)*"(?:\s*"(?:[^"\\]|\\.)*")*)')
_CALL = re.compile(
    rb"\b(fprintf|vfprintf)\s*\(\s*([A-Za-z_]\w*)\s*,\s*", re.S)
# fputs/fputc/putc take their stream as the *last* argument.
_SIMPLE_CALL = re.compile(rb"\b(fputs|fputc|putc)\s*\(\s*", re.S)
_FWRITE_CALL = re.compile(
    rb"\b(fwrite)\s*\([^;{}]*?,\s*([A-Za-z_]\w*)\s*\)", re.S)
_CHAR_LITERAL = re.compile(rb"'(?:[^'\\]|\\.)+'")
_BLOCK_COMMENT = re.compile(rb"/\*.*?\*/", re.S)
_LINE_COMMENT = re.compile(rb"//[^\n]*")
_HEX32 = re.compile(rb"^[0-9a-fA-F]{32}\n?$")

# Declared unsplittable references: the interleaved document cannot attribute
# these bytes to one channel, so the case gets an explicit BLOCKED verdict
# instead of a guessed split.  Each entry carries the source evidence.
UNSPLITTABLE = {
    "MultiSource/Benchmarks/Prolangs-C/bison": (
        "the same message text is emitted on both channels: conflicts.c:346/349 "
        "writes 'State %d contains' + ' %d shift/reduce conflict' to foutput "
        "(stdout -- the -v report) while conflicts.c:381/384 writes the same "
        "literals to stderr; the interleaved reference cannot say which line "
        "came from which channel"),
}


class SplitError(Exception):
    """The reference cannot be split into stdout/stderr without guessing."""


# Declared per-case additions: a program may print to stderr through a FILE*
# *parameter* (``fprintf(ofile, ...)`` with the caller passing stderr), which a
# per-file scan cannot follow.  The entry records the derived fact together
# with the source evidence; the formats are exactly the ones that text emits.
EXTRA_STDERR_FORMATS = {
    "MultiSource/Benchmarks/MiBench/consumer-lame": (
        "version.c:30-31 print the banner through the FILE* parameter "
        "`ofile`; lame's caller passes stderr (lame.c:main -> "
        "lame_print_config(stderr)), so the literal `stderr` never appears at "
        "those fprintf calls; the reference shows both lines before the "
        "encoder's own stderr lines",
        [
            (b"version.c", b"LAME version %s (www.sulaco.org/mp3) \n"),
            (b"version.c",
             b"GPSYCHO: GPL psycho-acoustic and noise shaping model version "
             b"%s. \n"),
        ],
    ),
}


# ---------------------------------------------------------------------------
# C literals -> byte patterns
# ---------------------------------------------------------------------------
_ESCAPES = {
    b"n": b"\n", b"t": b"\t", b"r": b"\r", b"0": b"\0", b"\\": b"\\",
    b'"': b'"', b"'": b"'", b"a": b"\a", b"b": b"\b", b"f": b"\f",
    b"v": b"\v", b"?": b"?",
}


def c_unescape(lit: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(lit):
        c = lit[i:i + 1]
        if c != b"\\" or i + 1 >= len(lit):
            out += c
            i += 1
            continue
        n = lit[i + 1:i + 2]
        if n in _ESCAPES:
            out += _ESCAPES[n]
            i += 2
            continue
        if n == b"x":
            j = i + 2
            while j < len(lit) and lit[j:j + 1] in b"0123456789abcdefABCDEF":
                j += 1
            if j == i + 2:
                raise SplitError(f"bad \\x escape in literal {lit!r}")
            out.append(int(lit[i + 2:j], 16) & 0xFF)
            i = j
            continue
        if n.isdigit():
            j = i + 1
            while j < len(lit) and lit[j:j + 1] in b"01234567" and j < i + 4:
                j += 1
            out.append(int(lit[i + 1:j], 8) & 0xFF)
            i = j
            continue
        out += n          # Unknown escape: C keeps the escaped character.
        i += 2
    return bytes(out)


_CONV = re.compile(
    rb"%[-+ #0']*[0-9]*(?:\.[0-9]+)?(?:hh|h|ll|l|j|z|t|L)?([diouxXeEfFgGaAcsp%])")
_NUM = rb" *[+-]?[0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?"
_CONV_RX = {
    b"d": rb" *[+-]?[0-9]+", b"i": rb" *[+-]?[0-9]+",
    b"o": rb" *[0-7]+", b"u": rb" *[0-9]+",
    b"x": rb" *[0-9a-fA-F]+", b"X": rb" *[0-9A-F]+",
    b"e": _NUM, b"E": _NUM, b"f": _NUM, b"F": _NUM, b"g": _NUM, b"G": _NUM,
    b"a": rb" *0x[0-9a-fA-F]*\.?[0-9a-fA-F]*p[+-]?[0-9]+",
    b"A": rb" *0X[0-9A-F]*\.?[0-9A-F]*P[+-]?[0-9]+",
    b"c": rb"[^\n]", b"s": rb"[^\n]*", b"p": rb" *0x[0-9a-fA-F]+",
    b"%": rb"%",
}


def fmt_to_regex(fmt: bytes):
    """Return ``(regex, literal_length)`` for one C format string.

    The regex is unanchored: the scanner matches it *at* a position
    (``rx.match(body, pos)``), which is what a ``fprintf`` emits there.
    """
    rx = bytearray()
    literal = 0
    pos = 0
    for m in _CONV.finditer(fmt):
        chunk = fmt[pos:m.start()]
        rx += re.escape(chunk)
        literal += len(chunk)
        conv = m.group(1)
        if conv not in _CONV_RX:
            raise SplitError(f"unsupported conversion %{conv.decode()!r}")
        else:
            rx += _CONV_RX[conv]
        pos = m.end()
    tail = fmt[pos:]
    rx += re.escape(tail)
    literal += len(tail)
    return re.compile(bytes(rx)), literal


# ---------------------------------------------------------------------------
# source -> stderr format strings
# ---------------------------------------------------------------------------
class StderrFormats:
    """What one case's sources say about its stderr channel."""

    def __init__(self):
        self.strong = []      # [(file, fmt, regex)]
        self.weak = []        # [(file, fmt, regex)]  -- numeric-only, line-start
        self.tail = []        # [(kind, file, fmt, regex)] -- text / whitespace
        self.opaque = []      # [(file, why)]         -- no literal at all
        self.files = []

    def add(self, where, fmt, opaque=False):
        if opaque:
            self.opaque.append((where, fmt))
            return
        rx, literal = fmt_to_regex(fmt)
        if literal >= MIN_LITERAL:
            self.strong.append((where, fmt, rx))
        elif any(tag in fmt for tag in (b"%s", b"%c", b"%p")):
            # "%s\n" & co. match *any* line: a locator, not an identifier.
            self.opaque.append((where, fmt))
        elif _CONV.search(fmt) is not None:
            # A numeric-only format ("%d\n"): trusted only as a whole line.
            self.weak.append((where, fmt, rx))
        elif not fmt.strip():
            # Pure whitespace ("\n"): only trusted *inside* a stderr run,
            # otherwise every blank line of stdout would be claimed.
            self.tail.append(("ws", where, fmt, rx))
        elif len(fmt) >= 3:
            # Short literal text ("Rolled "): may open a stderr run or
            # continue one, never arbitrary stdout text in mid-line.  A 1-2
            # byte literal ("." / "!") is too generic even for that.
            self.tail.append(("text", where, fmt, rx))
        else:
            self.opaque.append((where, fmt))

    def all_patterns(self):
        return self.tail + self.strong + self.weak


def _strip_comments(blob: bytes) -> bytes:
    return _LINE_COMMENT.sub(b"", _BLOCK_COMMENT.sub(b" ", blob))


def _include_closure(sources, include_dirs):
    seen = set()
    todo = [os.path.normpath(p) for p in sources]
    bases_extra = [os.path.normpath(d) for d in include_dirs]
    while todo:
        path = todo.pop()
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        try:
            with open(path, "rb") as fh:
                blob = fh.read()
        except OSError:
            continue
        for m in _INCLUDE.finditer(blob):
            name = os.fsdecode(m.group(1))
            for base in [os.path.dirname(path)] + bases_extra:
                cand = os.path.normpath(os.path.join(base, name))
                if os.path.isfile(cand):
                    todo.append(cand)
                    break
    return sorted(seen)


def _literal_at(blob: bytes, pos: int):
    """Read the (concatenated) string literal starting at ``pos``.

    Returns ``(literal, ok, end)``; ``ok`` is False when the argument is not a
    plain string literal (the caller must treat it as opaque).
    """
    while pos < len(blob) and blob[pos:pos + 1] in b" \t\r\n":
        pos += 1
    if blob[pos:pos + 1] != b'"':
        return b"", False, pos
    literal = b""
    while True:
        m = re.match(rb'"((?:[^"\\]|\\.)*)"', blob[pos:], re.S)
        if not m:
            return b"", False, pos
        literal += m.group(1)
        pos += m.end()
        nxt = re.compile(rb'\s*"').match(blob[pos:])
        if not nxt:
            return c_unescape(literal), True, pos
        pos += nxt.end() - 1


def _format_argument(blob: bytes, pos: int, macros):
    """Resolve the format argument at ``pos`` to a list of candidate literals.

    A string macro may be defined more than once (``#ifdef SP`` / ``#ifdef DP``
    branches both present in the source); every candidate literal is returned
    and the locator accepts whichever one the reference actually shows.
    """
    while pos < len(blob) and blob[pos:pos + 1] in b" \t\r\n":
        pos += 1
    if blob[pos:pos + 1] == b'"':
        literal, ok, _end = _literal_at(blob, pos)
        return ([literal] if ok else []), ok
    m = re.match(rb"([A-Za-z_]\w*)", blob[pos:])
    if not m:
        return [], False
    name = m.group(1)
    if name in macros:
        return sorted(macros[name]), True
    return [], False


def stderr_formats(sources, unit_dir, include_dirs=(), extra=None):
    """Collect stderr format strings from the case's include closure."""
    files = _include_closure(sources, include_dirs)
    texts = {}
    aliases = {b"stderr"}
    macros = {}
    for path in files:
        try:
            with open(path, "rb") as fh:
                texts[path] = _strip_comments(fh.read())
        except OSError:
            continue
    for blob in texts.values():
        for m in _STDERR_DEFINE.finditer(blob):
            aliases.add(m.group(1))
    for blob in texts.values():
        for m in _STRING_DEFINE.finditer(blob):
            literal, ok, _end = _literal_at(blob, m.end(1))
            if ok:
                macros.setdefault(m.group(1), set()).add(literal)
    out = StderrFormats()
    out.files = [os.path.basename(p) for p in files]
    for path, blob in texts.items():
        where = os.path.basename(path)
        for m in _CALL.finditer(blob):
            if m.group(2) not in aliases:
                continue
            literals, ok = _format_argument(blob, m.end(), macros)
            if not ok:
                out.add(where, b"not-a-format", opaque=True)
                continue
            for literal in literals:
                out.add(where, literal)
        # fputs("text", stderr) / fputc('c', stderr) / putc('c', stderr):
        # parse the first argument, then require the stream to be an alias.
        for m in _SIMPLE_CALL.finditer(blob):
            pos = m.end()
            if blob[pos:pos + 1] == b"'":
                cm = _CHAR_LITERAL.match(blob, pos)
                if not cm:
                    continue
                arg = c_unescape(cm.group(0)[1:-1])
                end = cm.end()
            else:
                arg, ok, end = _literal_at(blob, pos)
                if not ok:
                    continue
            tail = re.match(rb"\s*,\s*([A-Za-z_]\w*)\s*\)", blob[end:])
            if not tail or tail.group(1) not in aliases:
                continue
            out.add(where, arg)
        # fwrite(buf, size, count, stderr): bytes, not a format string.
        for m in _FWRITE_CALL.finditer(blob):
            if m.group(2) in aliases:
                out.add(where, b"not-a-format", opaque=True)
    if extra:
        for where, fmt in extra[1]:
            out.add(where, fmt)
    return out


# ---------------------------------------------------------------------------
# document -> channels
# ---------------------------------------------------------------------------
class Split:
    def __init__(self, stdout, stderr, exit_code, lines_out, lines_err,
                 midline=0):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.lines_out = lines_out
        self.lines_err = lines_err
        self.midline = midline

    def as_note(self):
        tail = (f"; {self.midline} line(s) split at a channel boundary"
                if self.midline else "")
        return (f"split: stdout {self.lines_out} line(s) / "
                f"stderr {self.lines_err} line(s){tail}")


def split_document(doc: bytes, formats: StderrFormats) -> Split:
    """Partition one upstream reference document into the two channels."""
    if _HEX32.match(doc):
        raise SplitError(
            "hash-form reference (HASH_PROGRAM_OUTPUT): the reference is a "
            "single md5 line, so it carries no bytes that could be attributed "
            "to stdout or stderr")
    m = _EXIT_TAIL.search(doc)
    if not m:
        raise SplitError("reference has no trailing 'exit N' line "
                         "(RunSafely always appends one)")
    body = doc[:m.start()]
    exit_code = int(m.group(1))
    patterns = []
    for row in formats.all_patterns():
        kind = row[0] if len(row) == 4 else ""
        where, fmt, rx = row[-3], row[-2], row[-1]
        numeric = (kind == ""
                   and len(re.sub(_CONV, b"", fmt)) < MIN_LITERAL)
        patterns.append((len(rx.pattern), kind, numeric, where, fmt, rx))
    patterns.sort(key=lambda row: -row[0])

    def match_at(pos, line_start, prev_stderr):
        for _plen, kind, numeric, where, fmt, rx in patterns:
            m = rx.match(body, pos)
            if not m or len(m.group(0)) == 0:
                continue
            if kind == "ws":
                # Whitespace continues a stderr run; it never starts one.
                if not prev_stderr or line_start:
                    continue
            elif kind == "text":
                # Short literal text opens or continues a stderr run, but it
                # must not appear in the middle of an unrelated stdout line.
                if not (line_start or prev_stderr):
                    continue
            elif numeric:
                # Numeric-only format: only as a whole line.
                if not line_start or body[m.end() - 1:m.end()] != b"\n":
                    continue
            return where, fmt, m
        return None

    out = bytearray()
    err = bytearray()
    midline = 0
    line_start = True
    prev_stderr = False
    pos = 0
    n = len(body)
    while pos < n:
        hit = match_at(pos, line_start, prev_stderr)
        if hit is not None:
            where, fmt, m = hit
            if not line_start:
                midline += 1
            err += body[pos:m.end()]
            if body[m.end() - 1:m.end()] != b"\n":
                line_start = False
            else:
                line_start = True
            pos = m.end()
            prev_stderr = True
            continue
        chunk = body[pos:pos + 1]
        out += chunk
        line_start = chunk == b"\n"
        prev_stderr = False
        pos += 1

    total_lines = len(body.splitlines(keepends=True))
    lines_out = len(bytes(out).splitlines(keepends=True))
    lines_err = len(bytes(err).splitlines(keepends=True))
    if lines_out + lines_err < total_lines:
        raise SplitError(
            f"line accounting is not exhaustive ({lines_out}+{lines_err} < "
            f"{total_lines})")
    return Split(bytes(out), bytes(err), exit_code, lines_out, lines_err,
                 midline)


# ---------------------------------------------------------------------------
# case -> split files
# ---------------------------------------------------------------------------
def case_slug(cid: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", cid)


def split_paths(cid: str):
    slug = case_slug(cid)
    return (os.path.join(SPLIT_DIR, slug + ".ref.stdout"),
            os.path.join(SPLIT_DIR, slug + ".ref.stderr"))


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


INDEX_HEADER = ("case", "reference", "reference_sha256", "stdout_sha256",
                "stdout_size", "stderr_sha256", "stderr_size", "lines")


def read_index():
    """Read ``index.tsv`` -> {cid: row dict}."""
    path = os.path.join(SPLIT_DIR, INDEX_NAME)
    rows = {}
    if not os.path.isfile(path):
        return rows
    with open(path, "r", encoding="utf-8", newline="") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            if not line.strip():
                continue
            fields = line.rstrip("\n").split("\t")
            rows[fields[0]] = dict(zip(header, fields))
    return rows


def _split_one(case):
    include_dirs = case.cmake.include_dirs if case.cmake else []
    formats = stderr_formats(case.sources, case.unit_dir, include_dirs,
                             extra=EXTRA_STDERR_FORMATS.get(case.cid))
    with open(case.oracle, "rb") as fh:
        doc = fh.read()
    return doc, split_document(doc, formats), formats


def main() -> int:
    import run_llvm_ts_user as driver   # noqa: E402  (same directory)

    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite-src", default=driver.DEFAULT_SRC)
    ap.add_argument("--only", action="append", default=None,
                    help="only cases whose id matches this regex (repeatable)")
    ap.add_argument("--write", action="store_true",
                    help="write the split files + index (deterministic)")
    ap.add_argument("--check", action="store_true",
                    help="verify the committed split matches a fresh split")
    ap.add_argument("--stats", action="store_true",
                    help="print per-case channel sizes")
    args = ap.parse_args()

    root = driver.abspath(args.suite_src)
    cases, _excluded, _census = driver.discover(root)
    # The driver's own ``prepare_cases`` loads the committed split (it is the
    # consumer); the generator only needs the derived CMake config and the
    # upstream reference path.
    driver.prepare_cases(cases, root, load_channels=False)
    cases = [c for c in cases if c.oracle is not None]
    if args.only:
        rxs = [re.compile(p) for p in args.only]
        cases = [c for c in cases if any(rx.search(c.cid) for rx in rxs)]
        if not cases:
            sys.stderr.write("ref_split: ERROR: --only matched no case\n")
            return 2

    index_rows = []
    failures = []
    split_ok = 0
    md5_form = 0
    declared = 0
    for case in cases:
        if case.cid in UNSPLITTABLE:
            declared += 1
            print(f"SKIP  {case.cid}: declared unsplittable -- "
                  f"{UNSPLITTABLE[case.cid]}")
            continue
        if case.oracle_kind not in ("stdout", "raw"):
            md5_form += 1
            if args.only or args.stats:
                print(f"SKIP  {case.cid}: hash-form reference "
                      f"({case.oracle_kind}); a digest carries no bytes to "
                      f"attribute -- not splittable")
            continue
        try:
            doc, split, formats = _split_one(case)
        except SplitError as exc:
            failures.append((case.cid, str(exc)))
            print(f"FAIL  {case.cid}: {exc}")
            continue
        split_ok += 1
        if args.stats:
            print(f"{case.cid}\toracle={case.oracle_kind}"
                  f"\tstdout={len(split.stdout)}B/{split.lines_out}L"
                  f"\tstderr={len(split.stderr)}B/{split.lines_err}L"
                  f"\tstrong={len(formats.strong)}"
                  f"\tweak={len(formats.weak)}"
                  f"\topaque={len(formats.opaque)}")
        rel = os.path.relpath(case.oracle, root).replace(os.sep, "/")
        index_rows.append({
            "case": case.cid,
            "reference": rel,
            "reference_sha256": sha256(doc),
            "stdout_sha256": sha256(split.stdout),
            "stdout_size": str(len(split.stdout)),
            "stderr_sha256": sha256(split.stderr),
            "stderr_size": str(len(split.stderr)),
            "lines": f"{split.lines_out}+{split.lines_err}",
        })
        if args.write:
            os.makedirs(SPLIT_DIR, exist_ok=True)
            out_path, err_path = split_paths(case.cid)
            with open(out_path, "wb") as fh:
                fh.write(split.stdout)
            with open(err_path, "wb") as fh:
                fh.write(split.stderr)
        if args.check:
            out_path, err_path = split_paths(case.cid)
            problems = []
            for path, want in ((out_path, split.stdout),
                               (err_path, split.stderr)):
                try:
                    with open(path, "rb") as fh:
                        got = fh.read()
                except OSError as exc:
                    problems.append(f"{os.path.basename(path)}: {exc}")
                    continue
                if got != want:
                    problems.append(f"{os.path.basename(path)} is stale "
                                    f"({len(got)} B != {len(want)} B)")
            if problems:
                failures.append((case.cid, "; ".join(problems)))
                print(f"FAIL  {case.cid}: " + "; ".join(problems))

    print(f"ref_split: {split_ok} case(s) split, {declared} declared "
          f"unsplittable, {md5_form} hash-form (not splittable), "
          f"{len(failures)} explicit failure(s)")
    for cid, why in failures:
        print(f"  FAIL {cid}: {why}")

    if args.write:
        os.makedirs(SPLIT_DIR, exist_ok=True)
        index_rows.sort(key=lambda row: row["case"])
        path = os.path.join(SPLIT_DIR, INDEX_NAME)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("\t".join(INDEX_HEADER) + "\n")
            for row in index_rows:
                fh.write("\t".join(row[k] for k in INDEX_HEADER) + "\n")
        print(f"ref_split: wrote {len(index_rows)} row(s) to "
              f"{os.path.relpath(path, REPO_ROOT)}")

    if args.check:
        index = read_index()
        missing = sorted({row["case"] for row in index_rows} - set(index))
        extra = sorted(set(index) - {row["case"] for row in index_rows})
        stale = []
        for row in index_rows:
            old = index.get(row["case"])
            if old is None:
                continue
            for key in ("reference_sha256", "stdout_sha256", "stderr_sha256",
                        "stdout_size", "stderr_size"):
                if old.get(key) != row[key]:
                    stale.append(f"{row['case']}: {key} {old.get(key)} != "
                                 f"{row[key]}")
        if missing:
            failures.append(("index", f"missing row(s): {missing}"))
        if extra:
            failures.append(("index", f"stale row(s) for cases with no "
                                      f"reference: {extra}"))
        if stale:
            failures.append(("index", "; ".join(stale)))
        if failures:
            print("ref_split: CHECK FAIL")
            return 1
        print(f"ref_split: CHECK PASS ({len(index_rows)} case(s) in sync)")
    if args.stats and not args.check and not args.write:
        return 1 if failures else 0
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
