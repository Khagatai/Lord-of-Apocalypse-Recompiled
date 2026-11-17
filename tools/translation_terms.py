"""Protect literal names and numerical/rating information during local drafting."""
from collections import Counter
import re
import unicodedata

MARKER = re.compile(r"<(?:cmd|fixed):\d+>")
FIXED = re.compile(r"<fixed:(\d+)>")


def protect(text, glossary):
    if "<fixed:" in text:
        raise ValueError("Source collides with protected-term syntax")
    terms = {}

    def keep(value):
        marker = f"<fixed:{len(terms)}>"
        terms[marker] = value
        return marker

    # Protect only terms actually present. Supplying unrelated character names
    # in a global prompt can make a small model invent antecedents for pronouns.
    names = sorted(glossary, key=len, reverse=True)
    if names:
        pattern = re.compile("|".join(re.escape(name) for name in names))
        text = pattern.sub(lambda match: keep(glossary[match[0]]), text)
    parts = re.split(r"(<(?:cmd|fixed):\d+>)", text)
    literal = re.compile(r"[★☆]+|[+\-−＋－]?\d+(?:[.．]\d+)?[%％]?", re.UNICODE)
    for index in range(0, len(parts), 2):
        parts[index] = literal.sub(lambda match: keep(unicodedata.normalize("NFKC", match[0])), parts[index])
    return "".join(parts), terms


def restore(text, source, terms):
    expected = Counter(MARKER.findall(source))
    if Counter(MARKER.findall(text)) != expected:
        raise ValueError("Protected markers were added, removed or duplicated")
    # Preserve the original ordered command stream, including invisible operands.
    if [m for m in MARKER.findall(text) if m.startswith("<cmd:")] != [m for m in MARKER.findall(source) if m.startswith("<cmd:")]:
        raise ValueError("Protected game commands were reordered")
    return FIXED.sub(lambda match: terms[match[0]], text)
