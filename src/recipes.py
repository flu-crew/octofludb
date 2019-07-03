import sys
import math
from rdflib import ConjunctiveGraph, Literal
import src.domain.flu as flu
from src.nomenclature import P, O, uidgen, make_uri, make_literal, make_property
from src.util import replace, fixLookup, make_maybe_add
import src.parser as p
from src.fasta import parse_fasta, print_fasta, graph_fasta
import src.entrez as entrez
import re
import pandas as pd
from tqdm import tqdm

# TODO: replace these with parsers

STRAIN_PAT = re.compile("[ABCD]/[^()\[\]]+")
BARCODE_PAT = re.compile("A0\d{7}|\d+TOSU\d+|EPI_ISL_\d+")


def load_fasta(g, filename, tag=None, columns=None, sep="|", fastaout=False):
    entries = parse_fasta(filename, sep=sep)
    if fastaout:
        print_fasta(entries, tag=tag)
    return graph_fasta(g, entries, tag=tag)


def load_blast(g, filename, tag=None):
    igen = uidgen(base=f"blast/{filename}", pad=0)

    with open(filename, "r") as f:
        for row in tqdm(f.readlines()):
            try:
                (
                    qseqid,
                    sseqid,
                    pident,
                    length,
                    mismatch,
                    gapopen,
                    qstart,
                    qend,
                    sstart,
                    send,
                    evalue,
                    bitscore,
                ) = row.split("\t")
            except ValueError:
                sys.exit(
                    "Expected blast file to have exactly 12 fields (as per default blast outfmt 6 options)"
                )

            huid = next(igen)

            if tag:
                g.add((huid, P.tag, Literal(tag)))

            g.add((huid, P.qseqid, make_uri(qseqid)))
            g.add((huid, P.sseqid, make_uri(sseqid)))
            g.add((huid, P.pident, Literal(float(pident))))
            g.add((huid, P.length, Literal(int(length))))
            g.add((huid, P.mismatch, Literal(int(mismatch))))
            g.add((huid, P.gapopen, Literal(int(gapopen))))
            g.add((huid, P.qstart, Literal(int(qstart))))
            g.add((huid, P.qend, Literal(int(qend))))
            g.add((huid, P.sstart, Literal(int(sstart))))
            g.add((huid, P.send, Literal(int(send))))
            g.add((huid, P.evalue, Literal(float(evalue))))
            g.add((huid, P.bitscore, Literal(float(bitscore))))

    g.commit()


def tag(g: ConjunctiveGraph, filename: str, tag: str) -> None:
    print(filename)
    with open(filename, "r") as f:
        for identifier in (s.strip() for s in f.readlines()):
            g.add((make_uri(identifier), P.tag, Literal(tag)))
    g.commit()


def infer_property(x):
    if p.parse_match(p.p_strain, x):
        return P.strain_name
    elif p.parse_match(p.p_gisaid_isolate, x):
        return P.gisaid_isolate
    elif p.parse_match(p.p_A0, x):
        return P.barcode
    elif p.parse_match(p.p_tosu, x):
        return P.barcode
    elif p.parse_match(p.p_gb, x):
        return P.gb
    elif p.parse_match(p.p_gisaid_seqid, x):
        return P.gisaid_seqid
    return None


def load_excel(g: ConjunctiveGraph, filename: str, tag=None) -> None:
    d = pd.read_excel(filename)

    for i in tqdm(range(d.shape[0])):
        s = d.iloc[i][0]  # subject - the id from the table's key column
        # the subject URI cannot have spaces
        uri = make_uri(s)

        if tag:
            g.add((uri, P.tag, Literal(tag)))

        # associate the ID with a name, there may be multiple names for this
        # entity, due to the sameAs rules.
        g.add((uri, P.name, Literal(s)))

        # try to determine the type of the ID (e.g., strain, genebank or barcode)
        # if successful, add a triple linking the id to its type
        prop = infer_property(s)
        if prop is not None:
            # associate the ID with its specific name
            g.add((uri, prop, Literal(s)))

        # associate the ID with each element in the row with column names as predicates
        for j in range(1, d.shape[1]):
            p = d.columns[j]  # predicate - the column name
            o = d.iloc[i][j]  # object - the value in the cell

            # the predict shouldn't have spaces and I convert to lower case to avoid
            # case mismatches in lookups
            p = p.lower().replace(" ", "_")

            #  print(f'{type(o)} {str(o)} {type(o) == "float" and math.isnan(o)}')
            #  if not (o == None or (type(o) == "float" and math.isnan(o))):
            if not (o == None or o != o):
                g.add((uri, make_property(p), make_literal(o)))

    g.commit()


def load_influenza_na(g: ConjunctiveGraph, filename: str) -> None:
    with open(filename, "r") as f:
        field = dict()
        for row in tqdm(f.readlines()):
            els = row.split("\t")
            try:
                field["gb"] = els[0]
                field["host"] = els[1]
                field["segment"] = els[2]
                field["country"] = els[4]
                field["date"] = els[5]
                is_complete = els[10].strip() == "c"
            except IndexError:
                print(
                    f"Expected 11 columns, found only {len(els)}. This is unexpected and a little frightening.",
                    file=sys.stderr,
                )

            gb_uid = make_uri(field["gb"])
            g.add((gb_uid, P.gb, Literal(field["gb"])))
            g.add((gb_uid, P.segment_number, Literal(field["segment"])))
            g.add((gb_uid, P.segment_name, Literal(flu.SEGMENT[int(els[2]) - 1])))
            if is_complete:
                g.add((gb_uid, P.tag, Literal("complete_genome")))

            # Skip entries where no strain name can be extracted
            # * A good column 7 should look like this:
            #     Influenza A virus (A/Arequipa/FLU3833/2006(H3))
            #     Influenza B virus (B/Jiangsu/10e9/2003)
            # * Here are a few pathological ones:
            #     Influenza A virus
            #     Influenza A virus (swine/Finistere/127/99(H3N2))
            #     Influenza A virus (St Jude H5N1 influenza seed virus 163222)
            #     Influenza A virus H3N2
            #     unidentified influenza virus
            # * In the current database (06/04/2019) 541/712177 entries are pathological
            strain_match = re.search(STRAIN_PAT, els[7])
            if strain_match:
                strain = strain_match.group(
                    0
                ).strip()  # yes, some of them can end in space

                strain_uid = make_uri(strain)
                maybe_add = make_maybe_add(g, field, strain_uid)
                g.add((strain_uid, P.has_segment, gb_uid))
                g.add((strain_uid, P.strain_name, Literal(strain)))

                barcode_match = re.search(BARCODE_PAT, strain)
                if barcode_match:
                    barcode_name = barcode_match.group(0)
                    barcode_uid = make_uri(barcode_name)
                    g.add((strain_uid, P.barcode, Literal(barcode_name)))
                    g.add((barcode_uid, P.sameAs, strain_uid))

                maybe_add = make_maybe_add(g, field, strain_uid)
                maybe_add(P.host, "host")
                maybe_add(P.country, "country")
                maybe_add(P.date, "date")

                if field["date"] != None:
                    g.add((strain_uid, P.date, make_literal(field["date"])))
            else:
                print(
                    f'  could not parse strain: {"|".join(els)}',
                    file=sys.stderr,
                    end="",
                )
    g.commit()
