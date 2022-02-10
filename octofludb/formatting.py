from __future__ import annotations
from typing import List, Tuple, TextIO, Dict

from octofludb.util import log
from octofludb.colors import bad

import sys


def write_as_fasta(results: dict, outfile: TextIO = sys.stdout) -> None:
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


def write_as_table(
    results: dict, header: bool = True, outfile: TextIO = sys.stdout
) -> None:
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


def write_constellations(results: dict, outfile: TextIO = sys.stdout) -> None:
    """
    Prepare constellations
    """

    rows = _parse_constellation_query(results)

    consts = _make_constellations(rows)

    print("strain_name\tconstellation", file=outfile)
    for (strain, const) in consts:
        print(f"{strain}\t{const}", file=outfile)


def _parse_constellation_query(results: dict) -> List[Tuple[str, str, str]]:
    return [
        (row["strain"]["value"], row["segment"]["value"], row["clade"]["value"])
        for row in results["results"]["bindings"]
    ]


def _make_constellations(rows: List[Tuple[str, str, str]]) -> List[Tuple[str, str]]:

    segment_lookup = dict(PB2=0, PB1=1, PA=2, NP=3, M=4, MP=4, NS=5)

    clade_lookup = dict(
        pdm="P", LAIV="V", TRIG="T", humanSeasonal="H", classicalSwine="C"
    )

    const: Dict[str, List[str]] = dict()
    for (strain, segment, clade) in rows:

        if strain not in const:
            const[strain] = list("------")

        try:
            index = segment_lookup[segment]
        except KeyError:
            log(
                f"{bad('WARNING:')} segment/segment_subtype mismatch, {str((strain, segment, clade))}"
            )
            continue

        if clade in clade_lookup:
            char = clade_lookup[clade]
        else:
            log(
                f"{bad('WARNING:')} expected internal gene clade to be one of  'pdm', 'LAIV', 'TRIG', 'classicalSwine', or 'humanSeasonal'. Found clade {clade}, assigning constellation character 'X'"
            )
            char = "X"

        if const[strain][index] == "-":
            const[strain][index] = char
        elif const[strain][index] != char:
            const[strain][
                index
            ] = "M"  # conflicting internal gene clades, this means the strain is probably mixed

    output_rows = []
    for (k, c) in const.items():
        if "M" in c:
            output_rows.append((k, "mixed"))
        else:
            output_rows.append((k, "".join(c)))
    return output_rows
