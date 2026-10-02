"""Company-name normalization, shared by everything that has to match one.

state.soft_key compares company names written by different people for the
same employer ("Whatnot" vs "Whatnot, Inc.", "Infosys" vs "Infosys Limited")
to decide whether a LinkedIn row and an ATS row are the same posting. This
module supplies the shared core and lets a caller widen the suffix list.
"""
import re

# Anything that is not a letter, a digit or a space. Punctuation is the most
# common difference between two spellings of one employer ("Whatnot, Inc." /
# "Whatnot Inc"), so it goes before anything else is decided.
NOISE = re.compile(r"[^a-z0-9 ]+")

# Legal-entity words that say nothing about which company this is. Deliberately
# not a place to put industry words: dropping "Technologies" or "Systems" here
# would make the visa matcher confuse companies that differ only by that word.
LEGAL_SUFFIX = ("inc|llc|ltd|corp|corporation|co|company|plc|gmbh|sa|nv|ag"
                "|holdings|group|limited|pvt|private|llp|india")


def suffix_pattern(*extra: str) -> re.Pattern:
    """The legal-suffix pattern, optionally widened by the caller's own words."""
    parts = "|".join((LEGAL_SUFFIX, *extra)) if extra else LEGAL_SUFFIX
    return re.compile(rf"\b({parts})\b", re.I)


def normalize(text: str, strip: re.Pattern | None = None) -> str:
    """Lowercase, drop punctuation, optionally drop suffixes, collapse spaces."""
    s = NOISE.sub(" ", (text or "").lower())
    if strip is not None:
        s = strip.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def squash(text: str, strip: re.Pattern | None = None) -> str:
    """normalize(), with the spaces removed too.

    The one thing normalization alone cannot reconcile is a word break that
    only one side writes: DOL files Walmart as "WAL-MART ASSOCIATES", which
    normalizes to "wal mart" and never meets "walmart". Removing spaces makes
    those meet, at the cost of also letting genuinely different names collide,
    so callers try it only after an exact match has failed.
    """
    return normalize(text, strip).replace(" ", "")
