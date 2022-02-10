from __future__ import annotations
from typing import Iterable, Callable, Set, Optional

from octofludb.util import underscore, lower, strip


def make_flat_wordfinder(
    wordlist: Iterable[str],
    alphabet: str = "abcdefghijklmnopqrstuvwxyz",
    depth: int = 1,
    clean: Callable[[str], str] = lambda x: underscore(lower(strip(x))),
) -> Callable[[str], Optional[str]]:
    """
    Build a function for finding the closest word in a list. This is not a
    spellchecker, since it will return None if not word is found. Also, it is
    not limited to words, but includes phrases. I may adapt it in the future to
    allow the deletion of words.
    """

    WORDS0 = {clean(w) for w in wordlist}
    WORDSN = [{e: w for w in WORDS0 for e in edits(w, alphabet)}]
    for i in range(2, depth + 1):
        WORDSN.append(
            {e2: w for (e1, w) in WORDSN[-1].items() for e2 in edits(e1, alphabet)}
        )

    def wordfinder(word: str) -> Optional[str]:
        clean_word = clean(word)

        if clean_word in WORDS0:
            return clean_word

        for words in WORDSN:
            if clean_word in words:
                return words[clean_word]

        return None

    return wordfinder


def edits(word: str, alphabet: str) -> Set[str]:
    """
    Borrowed directly from Peter Norvig's spell checker (https://norvig.com/spell-correct.html).
    """
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = [L + c + R[1:] for L, R in splits if R for c in alphabet]
    inserts = [L + c + R for L, R in splits for c in alphabet]
    return set(deletes + transposes + replaces + inserts)
