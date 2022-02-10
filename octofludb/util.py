from __future__ import annotations
from typing import (
    List,
    NoReturn,
    TypeVar,
    TextIO,
    Union,
    Tuple,
    Optional,
    Any,
    Set,
)

from rdflib.term import Node
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


def rmNone(xs):
    """Remove all 'None' elements from a list"""
    return list(filter(lambda x: x is not None, xs))


def firstOne(xs):
    """Return the first defined value in a list"""
    return rmNone(xs)[0]


def concat(xs: List[str]) -> str:
    return "".join(xs)


def padDigit(x: str, n=2) -> str:
    """This is used, for example, to exapand the month '5' to '05'"""
    return "0" * (n - len(x)) + x


def replace(d, key, a, b):
    if d[key] is not None:
        d[key] = d[key].replace(a, b)
    return d


def fixRegexMap(d: dict, field: str, rexpr: str, m: dict, flags=0):
    if d[field] is not None:
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
    if d[key] is None:
        d[key] = default
    return d


def safeAdd(
    g: Set[Tuple[Node, Node, Node]],
    s: Optional[Node],
    p: Optional[Node],
    o: Optional[Node],
) -> None:
    if s is not None and p is not None and o is not None:
        g.add((s, p, o))
