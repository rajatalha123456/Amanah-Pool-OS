"""Keyword side of hybrid retrieval: BM25 over the candidate chunks, with tokenising that works for Urdu and Arabic."""

import math
import re
import unicodedata

_TOKEN = re.compile(r"\w+", re.UNICODE)
_ARABIC_MARKS = re.compile("[ً-ٰٟۖ-ۭـ]")  # harakat, tatweel, small marks
_ARABIC_LETTERS = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا",  # alef forms -> alef
    "ى": "ي", "ی": "ي", "ې": "ي",  # yeh forms -> yeh
    "ک": "ك",  # keheh -> kaf
    "ہ": "ه", "ۃ": "ة",  # heh goal / teh marbuta goal
})


def normalise(text):
    text = unicodedata.normalize("NFKC", text or "").lower()
    return _ARABIC_MARKS.sub("", text).translate(_ARABIC_LETTERS)


def tokenize(text):
    return _TOKEN.findall(normalise(text))


def bm25_rank(query, texts, k1=1.5, b=0.75):
    """Returns [(index, score)] for texts with a positive score, best first."""
    docs = [tokenize(t) for t in texts]
    query_terms = set(tokenize(query))
    if not docs or not query_terms:
        return []
    n = len(docs)
    avg_len = sum(len(d) for d in docs) / n or 1.0
    df = {term: sum(1 for d in docs if term in d) for term in query_terms}
    scored = []
    for index, doc in enumerate(docs):
        if not doc:
            continue
        frequencies = {}
        for token in doc:
            if token in query_terms:
                frequencies[token] = frequencies.get(token, 0) + 1
        score = 0.0
        for term, tf in frequencies.items():
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(doc) / avg_len))
        if score > 0:
            scored.append((index, score))
    return sorted(scored, key=lambda x: x[1], reverse=True)
