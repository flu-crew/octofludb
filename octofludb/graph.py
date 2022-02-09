from __future__ import annotations
from typing import List, Tuple, Set

from octofludb.classes import Datum, Phrase


def showTriple(xs: List[str], levels: Set[str] = set()) -> List[Tuple[str, str, str]]:
    """
    This is mostly for diagnostics in the REPL and test
    """
    g = Phrase([Datum(x).data for x in xs], levels=levels).connect()
    s = sorted([(str(s), str(p), str(o)) for s, p, o in g])
    return s
