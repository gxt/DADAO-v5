#!/usr/bin/env python3
"""``CONFIG_DADAO_*`` pins: the Kconfig source of truth and the slice builder.

Why (``ISS-470``, seen twice as ``m14-linux-017`` F30/F41): a gate that pins only
the symbols it happens to know about inherits whatever the shared build tree was
configured with last.  A symbol nobody pinned silently keeps another image's
value (`=y` runs someone else's probe, `=6` ends the boot at a boundary) and the
gate goes red for a reason that has nothing to do with what it tests.

So every script that slices the kernel config carries a module-level
``CONFIG_PINS`` dict that names **every** ``CONFIG_DADAO_*`` symbol of the
Kconfig for the image it builds, and its slice is produced from that dict by
:func:`config_lines` -- never by hand-written ``"CONFIG_X=y"`` literals.
``tests/unit/linux/check_config_pins.py`` (L1 ``make check-config-pins``) asserts the
key set equals the Kconfig set and that no script hand-writes a slice.

Shape of ``CONFIG_PINS`` (checked mechanically, keep it a plain literal so the
gate can read it with ``ast.literal_eval`` -- no comprehensions, no calls)::

    CONFIG_PINS = {
        "CONFIG_DADAO_K1_EARLY_STOP": "y",
        "CONFIG_DADAO_K2_TIME_CASE": "n",     # int left unset: see below
        ...
    }

    #: optional, per-image overrides; every key must also be in CONFIG_PINS
    IMAGE_PINS = {
        "pf1": {"CONFIG_DADAO_K3_PF_SELFTEST": "1"},
    }

Values are ``y``/``n`` for bool symbols and the literal value for int symbols.
One wrinkle: Kconfig has **no spelling for "unset" on an int symbol** -- when a
``depends on`` is not met the symbol is dropped from ``.config`` entirely, and
writing ``=0`` for it makes ``olddefconfig`` drop the line (``apply_config_lines``
then FAILs "did not survive").  Such a symbol is pinned ``"n"`` here, which
:func:`config_lines` renders as "write nothing"; the gate verifies the choice is
honest by evaluating the Kconfig ``depends on`` against the same pins (an int
pinned ``"n"`` must really be invisible in that image).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: The Kconfig fragment that declares the milestone symbols (patch of a new
#: file: every `+` line is content).  The only source of the symbol set.
KCONFIG_REL = Path("components/linux/patches/arch/dadao/Kconfig.debug.patch")

SYMBOL_PREFIX = "CONFIG_"
_CONFIG_RE = re.compile(r"^config\s+(\w+)\s*$")
_TYPE_RE = re.compile(r"^\s*(bool|tristate|int|hex|string|def_bool|def_tristate)\b")
_DEPENDS_RE = re.compile(r"^\s*depends\s+on\s+(.+?)\s*$")
_RANGE_RE = re.compile(r"^\s*range\s+(\S+)\s+(\S+)\s*$")
_ASSIGN_RE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")

_TYPES = {"def_bool": "bool", "def_tristate": "tristate"}


class Symbol:
    """One ``config DADAO_*`` block: its type, ``depends on``, and range."""

    __slots__ = ("name", "type", "depends", "range")

    def __init__(self, name: str, type_: str, depends: str | None,
                 range_: tuple[str, str] | None) -> None:
        self.name = name
        self.type = type_
        self.depends = depends
        self.range = range_

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Symbol({self.name!r}, {self.type!r}, {self.depends!r})"


def parse_kconfig(path: Path | str) -> dict[str, Symbol]:
    """Parse the fragment: symbol -> :class:`Symbol` (``CONFIG_`` prefixed names).

    Accepts both the patch form (only ``+`` lines are content) and a plain file.
    Returns an empty dict when the file declares none -- the caller decides
    whether that is a failure (the gate treats it as "fail closed").
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    is_patch = text.lstrip().startswith(("diff --git", "--- "))
    symbols: dict[str, Symbol] = {}
    current: Symbol | None = None
    seen_type = False
    for raw in text.splitlines():
        if is_patch:
            if not raw.startswith("+") or raw.startswith("+++"):
                continue
            line = raw[1:]
        else:
            line = raw
        match = _CONFIG_RE.match(line.strip())
        if match:
            current = Symbol(SYMBOL_PREFIX + match.group(1), "unknown", None, None)
            symbols[current.name] = current
            seen_type = False
            continue
        if current is None:
            continue
        if not seen_type:
            type_match = _TYPE_RE.match(line)
            if type_match:
                kind = type_match.group(1)
                current.type = _TYPES.get(kind, kind)
                seen_type = True
                continue
        dep_match = _DEPENDS_RE.match(line)
        if dep_match:
            current.depends = dep_match.group(1)
            continue
        range_match = _RANGE_RE.match(line)
        if range_match:
            current.range = (range_match.group(1), range_match.group(2))
    return symbols


def kconfig_path(root: Path | str | None = None) -> Path:
    return (REPO if root is None else Path(root)) / KCONFIG_REL


_CACHE: dict[Path, dict[str, Symbol]] = {}


def symbols(root: Path | str | None = None) -> dict[str, Symbol]:
    """Kconfig symbols for @root, parsed once per process."""
    path = kconfig_path(root)
    cached = _CACHE.get(path)
    if cached is None:
        cached = parse_kconfig(path)
        _CACHE[path] = cached
    return cached


def is_int(symbol: str, root: Path | str | None = None) -> bool:
    spec = symbols(root).get(symbol)
    return spec is not None and spec.type == "int"


#: ``PAGE_BLOCK_MAX_ORDER`` cap for every image of this port.
#:
#: It is not a ``CONFIG_DADAO_*`` symbol, so it is not part of the per-script
#: pins; the slice builder states it once instead.  ``m14-linux-028`` raised
#: ``ARCH_FORCE_MAX_ORDER`` to 13 (512 MiB, one superpage) and generic
#: ``mm/Kconfig`` then defaults the *pageblock* order to the same value, i.e.
#: one pageblock per 512 MiB of RAM.  On the 2 GiB Vast zone that makes every
#: migratetype fallback and every direct-compaction round operate on a whole
#: 512 MiB region, and the K5 probe images stop making progress (measured: the
#: m14-linux-023 image never returns from its first user trap).  The generic
#: pageblock size (64 MiB, the order generic ``mm/Kconfig`` uses when
#: ``ARCH_FORCE_MAX_ORDER`` is unset) is kept.
PAGE_BLOCK_MAX_ORDER = 10
PAGE_BLOCK_SYMBOL = "CONFIG_PAGE_BLOCK_MAX_ORDER"


def config_lines(pins: dict[str, str], overrides: dict[str, str] | None = None,
                 root: Path | str | None = None) -> list[str]:
    """``SYMBOL=value`` lines for @pins (+@overrides), in dict order.

    An int symbol pinned ``"n"`` means "this image leaves it unset" and yields no
    line: Kconfig drops invisible ints from ``.config`` and has no ``n`` value
    for them (see the module docstring).

    The slice also carries :data:`PAGE_BLOCK_SYMBOL` (a port-wide invariant, not
    a per-image pin); a caller that says otherwise in @overrides wins.
    """
    merged = dict(pins)
    merged.update(overrides or {})
    known = symbols(root)
    lines: list[str] = []
    for symbol, value in merged.items():
        spec = known.get(symbol)
        if value == "n" and spec is not None and spec.type == "int":
            continue
        lines.append(f"{symbol}={value}")
    if PAGE_BLOCK_SYMBOL not in merged:
        lines.append(f"{PAGE_BLOCK_SYMBOL}={PAGE_BLOCK_MAX_ORDER}")
    return lines
