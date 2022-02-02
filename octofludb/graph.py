from __future__ import annotations
from typing import List, Tuple

from octofludb.classes import Datum, Phrase

def showTriple(xs : List[str]) -> List[Tuple[str, str, str]]:
    """
    This is mostly for diagnostics in the REPL and test
    """
    g = Phrase([Datum(x).data for x in xs]).connect()
    s = sorted([(str(s), str(p), str(o)) for s, p, o in g])
    return s
