from octofludb.classes import Datum, Phrase


def addTriples(g, triples):
    for triple in triples:
        g.add(triple)


def showTriple(xs):
    """
    This is mostly for diagnostics in the REPL and test
    """
    g = set()
    Phrase([Datum(x).data for x in xs]).connect(g)
    s = sorted([(str(s), str(p), str(o)) for s, p, o in g])
    return s
