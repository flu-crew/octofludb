from octofludb.util import log
from octofludb.colors import bad

import sys


def write_as_fasta(results, outfile=sys.stdout):
    """
    Write a SPARQL query result as a FASTA file
    """
    header_fields = results["head"]["vars"][:-1]
    seq_field = results["head"]["vars"][-1]
    for row in results["results"]["bindings"]:
        fields = []
        for f in header_fields:
            if f in row:
                fields.append(row[f]["value"])
            else:
                fields.append("")
        header = "|".join(fields)
        sequence = row[seq_field]["value"]
        print(">" + header, file=outfile)
        print(sequence, file=outfile)


def write_as_table(results, header=True, outfile=sys.stdout):
    """
    Write a SPARQL query result as a TAB-delimited table with an optional header
    """

    def val(xs, field):
        if field in xs:
            return xs[field]["value"]
        else:
            return ""

    if header:
        print("\t".join(results["head"]["vars"]), file=outfile)
    for row in results["results"]["bindings"]:
        fields = (val(row, field) for field in results["head"]["vars"])
        print("\t".join(fields), file=outfile)


def write_constellations(results, outfile=sys.stdout):
    """
    Prepare constellations
    """

    rows = _parse_constellation_query(results)

    consts = _make_constellations(rows)

    print("strain_name\tconstellation", file=outfile)
    for (strain, const) in consts:
        print(f"{strain}\t{const}", file=outfile)


def _parse_constellation_query(results):
    return [
        (row["strain"]["value"], row["segment"]["value"], row["clade"]["value"])
        for row in results["results"]["bindings"]
    ]


def _make_constellations(rows):

    segment_lookup = dict(PB2=0, PB1=1, PA=2, NP=3, M=4, MP=4, NS=5)

    clade_lookup = dict(
        pdm="P", LAIV="V", TRIG="T", humanSeasonal="H", classicalSwine="C"
    )

    const = dict()
    for (strain, segment, clade) in rows:

        if strain in const:
            if const[strain] is None:
                continue
        else:
            const[strain] = list("------")

        try:
            index = segment_lookup[segment]
        except KeyError as e:
            log(
                f"{bad('WARNING:')} segment/segment_subtype mismatch, {str((strain, segment, clade))}"
            )
            continue

        if clade in clade_lookup:
            char = clade_lookup[clade]
        else:
            char = "X"

        if const[strain][index] == "-":
            const[strain][index] = char
        elif const[strain][index] != char:
            const[strain] = None

    rows = []
    for (k, c) in const.items():
        if c is None:
            rows.append((k, "mixed"))
        else:
            rows.append((k, "".join(c)))
    return rows
