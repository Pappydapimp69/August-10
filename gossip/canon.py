"""Reading the canon.

Parsing deliberately mirrors `Brain/bin/brain`'s rules so that gossip and
`brain analyze` see the same entries; where gossip departs it is on purpose and
recorded in the module that departs, never here.
"""

import os
import re

ENTRY_MARKER = "## E"
NULL_COMPOSED = {"", "n/a", "na", "none", "-", "—"}


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def blocks(text, marker):
    """Split a project file into per-entry blocks starting at `marker`."""
    out, cur = [], None
    for line in text.splitlines():
        if line.startswith(marker):
            if cur is not None:
                out.append("\n".join(cur))
            cur = [line]
        elif cur is not None:
            cur.append(line)
    if cur is not None:
        out.append("\n".join(cur))
    return out


def field(block, name):
    """Value of a `- Label: ...` field, joined across wrapped lines.

    The label match is a PREFIX match, because the canon's own labels carry
    parentheticals — the provenance field is written `Provenance
    (verified/assumed):`. An exact match silently returns "" for it, which reads
    downstream as 'no lesson here is verified' rather than as a parse failure.
    Continuation lines are joined too: a `Got right:` that wraps would otherwise
    lose everything after its first line, and that text is what decides whether
    an edge counts as safe.
    """
    lab = name.lower()
    out, capturing = [], False
    for line in block.splitlines():
        s = line.strip()
        m = re.match(r"^-\s*([^:]+):\s*(.*)$", s)
        if m and m.group(1).strip().lower().startswith(lab):
            capturing = True
            if m.group(2):
                out.append(m.group(2))
            continue
        if capturing:
            if re.match(r"^-\s*[^:]+:", s) or s.startswith("## "):
                break
            out.append(s)
    return " ".join(out).strip()


def tags_of(block):
    return re.findall(r"\[([a-z0-9._-]+)\]", field(block, "tags"))


def load_entries(bases):
    """Every promoted lesson under the given canon bases, newest-first per file."""
    entries = []
    for base in bases:
        pdir = os.path.join(base, "projects")
        if not os.path.isdir(pdir):
            continue
        for fn in sorted(os.listdir(pdir)):
            if not fn.endswith(".md"):
                continue
            text = read(os.path.join(pdir, fn))
            for block in blocks(text, ENTRY_MARKER):
                m = re.match(r"##\s*(E\d+)", block.splitlines()[0])
                if not m:
                    continue
                entries.append({
                    "file": fn,
                    "id": m.group(1),
                    "block": block,
                    "tags": tags_of(block),
                    "provenance": field(block, "provenance"),
                    "gotright": field(block, "got right"),
                    "composed": field(block, "composed"),
                    "date": field(block, "date"),
                })
    return entries


def slug_index(bases):
    """Map every reasonable spelling of a project slug to its filename."""
    idx = {}
    for base in bases:
        pdir = os.path.join(base, "projects")
        if not os.path.isdir(pdir):
            continue
        for fn in sorted(os.listdir(pdir)):
            if not fn.endswith(".md"):
                continue
            stem = fn[:-3]
            keys = {stem}
            if "__" in stem:
                keys.add(stem.split("__", 1)[1])
            for k in list(keys):
                if k.startswith("sandbox-"):
                    keys.add(k[len("sandbox-"):])
            for k in keys:
                idx.setdefault(k, fn)
    return idx


def resolve_slug(slug, idx):
    slug = slug.strip().lower()
    if slug in idx:
        return idx[slug]
    cands = {f for k, f in idx.items() if k.endswith(slug) or slug.endswith(k)}
    return next(iter(cands)) if len(cands) == 1 else None


def short(fn):
    stem = fn[:-3] if fn.endswith(".md") else fn
    return stem.split("__", 1)[1] if "__" in stem else stem


def is_verified(provenance):
    return bool(re.match(r"\s*verified", provenance.lower()))


def newest_date(entries):
    """Latest ISO date present in the canon — the deterministic stand-in for
    'now'. Reading the clock would make every report unreproducible."""
    dates = sorted(e["date"] for e in entries if re.match(r"\d{4}-\d{2}-\d{2}", e["date"]))
    return dates[-1][:10] if dates else "1970-01-01"


def days_between(earlier, later):
    """Whole days between two ISO dates. Returns 0 if either is unparseable."""
    from datetime import date

    def parse(s):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

    a, b = parse(earlier), parse(later)
    return max(0, (b - a).days) if a and b else 0
