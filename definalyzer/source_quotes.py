"""Resolve readable Markdown quotes back to exact original byte-range text."""
import re


def original_quote(text, quote):
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError("A source quote is required.")
    if quote in text:
        return quote
    removed=set()
    for match in re.finditer(r"!?\[([^\]\n]*)\]\([^\n)]*\)",text):
        removed.update(range(match.start(),match.start(1)))
        removed.update(range(match.end(1),match.end()))
    # A list bullet must not consume the first delimiter of following bold
    # text. Match each inline form with non-whitespace boundaries separately.
    patterns = (r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1",
                r"(?<!\*)(\*)(?=\S)(.+?)(?<=\S)\1(?!\*)",
                r"(?<!\w)(_)(?=\S)(.+?)(?<=\S)\1(?!\w)",
                r"(?<!`)(`)(?=\S)(.+?)(?<=\S)\1(?!`)")
    for pattern in patterns:
        for match in re.finditer(pattern,text):
            removed.update(range(match.start(),match.start(2)))
            removed.update(range(match.end(2),match.end()))
    for match in re.finditer(r"\s*\(opens in a new tab\)",text):
        removed.update(range(match.start(),match.end()))
    characters=[]; offsets=[]
    for index,char in enumerate(text):
        if index in removed:continue
        if char.isspace():
            if characters and characters[-1]==' ':continue
            char=' '
        characters.append(char);offsets.append(index)
    plain=''.join(characters)
    wanted=' '.join(quote.split())
    start=plain.find(wanted)
    if start<0 or plain.find(wanted,start+1)>=0:
        raise ValueError("Evidence must uniquely match the supplied original block.")
    # Return original Markdown, not the readable projection. Source hashes and
    # independent checks continue to bind exact original text and surrounding context.
    return text[offsets[start]:offsets[start+len(wanted)-1]+1]
