from __future__ import annotations
from typing import (
    List,
    NoReturn,
    TypeVar,
    Iterator,
    TextIO,
    Union,
    Tuple,
    Optional,
    Any,
)

from rdflib import Literal
import math
import sys
import re

A = TypeVar("A")
B = TypeVar("B")


def log(msg: str, end: str = "\n") -> None:
    print(msg, file=sys.stderr, flush=True, end=end)


def die(msg: str) -> NoReturn:
    print(msg, file=sys.stderr, flush=True)
    sys.exit(1)


def file_str(f: Union[str, TextIO]) -> str:
    if isinstance(f, str):
        return f
    else:
        try:
            return f.name  # get the name from a filehandle
        except:
            return str(f)


def strOrNone(x: Any) -> Optional[str]:
    try:
        if math.isnan(x):
            x = None
    except:
        pass
    if x is not None:
        x = str(x)
    return x


def upper(x: str) -> str:
    return x.upper()


def lower(x: str) -> str:
    return x.lower()


def underscore(x: str) -> str:
    return x.replace(" ", "_")


def strip(x: str) -> str:
    return x.strip()


def make_maybe_add(g, meta, sid):
    def maybe_add(p, key, formatter=Literal):
        if key in meta and meta[key] != None:
            try:
                g.add((sid, p, formatter(meta[key])))
            except:
                pass

    return maybe_add


def rmNone(xs):
    """Remove all 'None' elements from a list"""
    return list(filter(lambda x: x != None, xs))


def firstOne(xs):
    """Return the first defined value in a list"""
    return rmNone(xs)[0]


def concat(xs: List[str]) -> str:
    return "".join(xs)


def padDigit(x: str, n=2) -> str:
    """This is used, for example, to exapand the month '5' to '05'"""
    return "0" * (n - len(x)) + x


def replace(d, key, a, b):
    if d[key] != None:
        d[key] = d[key].replace(a, b)
    return d


def fixRegexMap(d: dict, field: str, rexpr: str, m: dict, flags=0):
    if d[field] != None:
        key = rmNone([re.fullmatch(rexpr, k, flags) for k in m.keys()])
        if len(key) > 0:
            d[field] = m[key[0].string]
    return d


def fixLookup(d: dict, field: str, m: dict, f=lambda x: x):
    try:
        d[field] = m[f(field)]
    except:
        pass
    return d


def addDefault(d: dict, key: str, default: str):
    if d[key] == None:
        d[key] = default
    return d
