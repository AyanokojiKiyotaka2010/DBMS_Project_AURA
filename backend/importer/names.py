"""Match a person's name as written in one document against the faculty directory (different order / initials)."""
import re

TITLES = {"dr", "prof", "professor", "mr", "mrs", "ms", "shri", "smt", "er", "sh", "captain", "mrs.", "mr."}


def tokens(name: str):
    name = re.sub(r"\(.*?\)", " ", name.lower())               # drop "(Mrs.)"
    return [t for t in re.sub(r"[^a-z\s]", " ", name).split() if t not in TITLES]


def _tok_match(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a)):       # vaishali ~ vaishaliben
        return True
    return False


def score(name_a: str, name_b: str) -> float:
    """0 = different people, higher = more certain they are the same."""
    ta, tb = tokens(name_a), tokens(name_b)
    fa, fb = [t for t in ta if len(t) > 1], [t for t in tb if len(t) > 1]
    ia, ib = {t[0] for t in ta if len(t) == 1}, {t[0] for t in tb if len(t) == 1}
    if not fa or not fb:
        return 0.0
    short, long_ = (fa, fb) if len(fa) <= len(fb) else (fb, fa)
    pool = list(long_)
    matched = 0
    for t in short:
        hit = next((u for u in pool if _tok_match(t, u)), None)
        if hit is None:
            return 0.0
        pool.remove(hit)
        matched += 1
    if matched < 2:
        # Only ONE real word is shared ("R. Kumar" vs "Vineet Kumar Rathore"). That is only credible when the shared word
        # is the surname (last word) in both names and every initial of the short form is explained by another word.
        s_tokens, l_tokens = (ta, tb) if len(fa) <= len(fb) else (tb, ta)
        w = next(t for t in s_tokens if len(t) > 1)
        if len(w) < 4 or s_tokens[-1] != w and not _tok_match(s_tokens[-1], w):
            return 0.0
        if not any(_tok_match(w, t) for t in l_tokens[-1:]):
            return 0.0
        s_init = [t for t in s_tokens if len(t) == 1]
        if not s_init:
            return 0.0
        others = [t for t in l_tokens[:-1]]
        for ini in s_init:
            hit = next((o for o in others if o == ini or (len(o) > 1 and o.startswith(ini))), None)
            if hit is None:
                return 0.0
            others.remove(hit)
        return 0.6
    extra = len(long_) - len(short)                            # unmatched words on the longer side lower confidence
    return 1.0 - 0.1 * extra


def best_unique(name: str, candidates):
    """candidates: iterable of (id, display_name). Returns the id only when exactly one candidate clearly wins."""
    scored = sorted(((score(name, n), i) for i, n in candidates), reverse=True)
    scored = [s for s in scored if s[0] > 0]
    if not scored:
        return None
    if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.15:
        return None                                            # ambiguous: better unlinked than wrong
    return scored[0][1] if scored[0][0] >= 0.6 else None
