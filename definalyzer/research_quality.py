"""Local evidence repairs and conservative research presentation filters."""
import re
from .source_quotes import original_quote


def repair_quote(text, quote):
    """Recover a contiguous original span from ordered, exact quoted lines.

    Missing intervening lines are restored, never fabricated. The independent
    semantic check still receives the original context, including those lines.
    """
    try:
        return original_quote(text, quote)
    except ValueError:
        parts = [p.strip() for p in quote.splitlines() if p.strip()] if isinstance(quote, str) else []
        if len(parts) < 2:
            raise
        start, end = None, 0
        for part in parts:
            found = text.find(part, end)
            if found < 0 or text.find(part, found + 1) >= 0:
                raise ValueError('Quote lines must uniquely match in source order.')
            start = found if start is None else start
            end = found + len(part)
        if end - start > 4000:
            raise ValueError('Repaired quote exceeds its original context allowance.')
        return text[start:end]


def source_gap(block):
    text = block['text']
    if re.search(r'\bHypothetical\b', text) and re.search(r'\bIllustrative only\b', text, re.I):
        return 'Illustrative calculator values are not current market observations.'
    # A mixed methodology/legal block may contain clickwrap at its end. Do not
    # discard that block or its material token-rights restriction.
    if 'certify that you are over 18 years old' in text and 'Methodology' not in text and len(text) < 2000:
        return 'The saved trading page contains a welcome/terms screen, not price or market-cap observations.'
    return None


def same_claim(left, right):
    """Exact provenance and conservative wording equivalence, not entity merging."""
    if any(left[k] != right[k] for k in ('subject_id', 'applicability')):
        return False
    refs = lambda f: {(r['block_id'], r['quote']) for r in f['evidence']}
    if refs(left) != refs(right):
        return False
    def wording(fact):
        words = re.findall(r'(?:\d+(?:\.\d+)?|\.\d+)%?|[a-z_]+', fact['statement'].casefold())
        # Moving the adverb "exactly" does not change a requirement. Keep all
        # other word order: "A controls B" and "B controls A" are not duplicates.
        return words.count('exactly'), [w for w in words if w != 'exactly']
    return wording(left) == wording(right)


def unique_claims(facts):
    result = []
    for fact in facts:
        if not any(same_claim(fact, old) for old in result):
            result.append(fact)
    return result
