import parsec as p
import re
import rdflib
from typing import List
from collections import defaultdict


def wordset(words, label, f=lambda x: x.lower().replace(" ", "_")):
    """
    Create a log(n) parser for a set of n strings.
    @param "label" is a arbitrary name for the wordset that is used in error messages
    @param "f" is a function used to convert matching strings in the wordset and text (e.g to match on lower case).
    """
    d = defaultdict(set)
    # divide words into sets of words of the same length
    # this allows exact matches against the sets
    for word in words:
        d[len(word)].update([f(word)])
    # Convert this to a list of (<length>, <set>) tuples reverse sorted by
    # length. The parser must search for longer strings first to avoid matches
    # against prefixes.
    d = sorted(d.items(), key=lambda x: x[0], reverse=True)

    @p.Parser
    def wordsetParser(text, index=0):
        for k, v in d:
            if f(text[index : (index + k)]) in v:
                return p.Value.success(index + k, text[index : (index + k)])
        return p.Value.failure(
            index, f'a term "{f(text[index:(index+k)])}" not in wordset {d}'
        )

    return wordsetParser


def parse_match(parser, text):
    try:
        parser.parse_strict(text)
    except p.ParseError:
        return False
    return True


def regexWithin(regex, context: p.Parser):
    @p.Parser
    def regexWithinParser(text, index=0):
        try:
            contextStr = context.parse(text[index:])
        except p.ParseError:
            return p.Value.failure(index, "Context not found")
        m = re.search(regex, contextStr)
        if m:
            return p.Value.success(index + len(contextStr), m.group(0))
        else:
            return p.Value.failure(index, "Could not match regex")

    return regexWithinParser


def splitMatchFirst(psr: p.Parser, splitStr: str, text: str):
    """
    Rethink whether this is needed ...
    """
    fields = text.split(splitStr)
    for field in fields:
        try:
            return psr.parse_strict(field)
        except:
            continue
    return None
