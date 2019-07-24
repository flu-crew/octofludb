import parsec as p
import re
import rdflib
from typing import List

from src.nomenclature import (
    P,
    O,
    make_uri,
    make_literal,
    make_property,
    make_usa_state_uri,
)


def parse_match(parser, text):
    try:
        parser.parse_strict(text)
    except p.ParseError:
        return False
    return True


def regexWithin(regex: re.Pattern, context: p.Parser):
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
