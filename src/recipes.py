import sys
import math
from rdflib import ConjunctiveGraph, Literal
import src.domain.flu as flu
from src.nomenclature import P, O, nt, ne, make_uri, uidgen, make_literal
from src.util import replace, fixLookup, make_maybe_add
import src.parser as p
from src.fasta import parse_fasta, graph_fasta
import src.entrez as entrez
import re
import pandas as pd

# TODO: replace these with parsers

STRAIN_PAT = re.compile("[ABCD]/[^()\[\]]+")
BARCODE_PAT = re.compile("A0\d{7}|\d+TOSU\d+|EPI_ISL_\d+")

from src.parser import p_date


def load_fasta(g, filename, event=None, columns=None, sep="|"):
    entries = parse_fasta(filename, sep=sep)
    return graph_fasta(g, entries)


def load_blast(g, filename, event=None):
    igen = uidgen(base="blast/" + filename, pad=0)
    if event:
        event_uri = ne.term(event)
        g.add((event_uri, P.is_a, O.event))
        g.add((event_uri, P.name, Literal(event)))

    with open(filename, "r") as f:
        for row in f.readlines():
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

            if event:
                g.add((event_uri, P.related_to, huid))

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


def add_seq_meta_triples(g, meta):

    strain_uid = make_uri(meta["strain"])

    g.add((strain_uid, P.has_segment, make_uri(meta["gb"])))
    g.add((strain_uid, P.is_a, O.strain))
    g.add((strain_uid, P.name, Literal(str(meta["strain"]))))

    maybe_add = make_maybe_add(g, meta, strain_uid)
    maybe_add(P.ref_reason, "ref_reason")
    maybe_add(P.subtype, "subtype")
    maybe_add(P.country, "country")
    maybe_add(P.state, "state")
    maybe_add(P.ha_clade, "ha_clade")
    maybe_add(P.date, "date")


def tag_strains(g: ConjunctiveGraph, filename: str, tag: str) -> None:
    with open(filename, "r") as f:
        for strain in (s.strip() for s in f.readlines()):
            uri = make_uri(strain)
            g.add((uri, P.tag, Literal(tag)))
            g.add((uri, P.is_a, O.strain))
            g.add((uri, P.name, Literal(strain)))
    g.commit()


def tag_gb(g: ConjunctiveGraph, filename: str, tag: str) -> None:
    with open(filename, "r") as f:
        for gb in (s.strip() for s in f.readlines()):
            uri = make_uri(gb)
            g.add((uri, P.tag, Literal(tag)))
            g.add((uri, P.is_a, O.gb))
            g.add((uri, P.name, Literal(gb)))
    g.commit()


def load_factor(
    g: ConjunctiveGraph, table_filename: str, relation: str, key_type: str = "strain"
) -> None:
    if key_type == "strain":
        o = O.strain
    elif key_type == "barcode":
        o = O.barcode
    elif key_type == "gisaid":
        o = O.gisaid
    elif key_type == "gb":
        o = O.gb
    else:
        sys.exit("please choose key_type from strain, barcode, and gb")
    with open(table_filename, "r") as f:
        for (key, val) in (
            (k.strip(), v.strip()) for k, v in f.readlines().split("\t")
        ):
            uri = make_uri(key)
            g.add((uri, nt.term(relation), Literal(tag)))
            g.add((uri, nt.is_a, o))
    g.commit()


def infer_type(x):
    x_is_a = None
    if p.parse_match(p_strain, x):
        x_is_a = O.strain
    elif p.parse_match(p_barcode, x):
        x_is_a = O.barcode
    elif p.parse_match(p_gb, x):
        x_is_a = O.gb
    elif p.parse_match(p_gisaid_seqid, x):
        x_is_a = O.gisaid
    return x_is_a


def load_excel(g: ConjunctiveGraph, filename: str, event=None) -> None:
    d = pd.read_excel(filename)

    if event:
        event_uri = ne.term(event)
        g.add((event_uri, P.is_a, O.event))
        g.add((event_uri, P.name, Literal(event)))

    for i in range(d.shape[0]):
        s = d.iloc[i][0]  # subject - the id from the table's key column
        # the subject URI cannot have spaces
        uri = make_uri(s)

        if event:
            g.add((event_uri, P.related_to, uri))

        # associate the ID with its name
        g.add((uri, P.name, Literal(s)))

        # try to determine the type of the ID (e.g., strain, genebank or barcode)
        # if successful, add a triple linking the id to its type
        s_type = infer_type(s)
        if s_type != None:
            g.add((uri, P.is_a, s_type))

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
                g.add((uri, nt.term(p), make_literal(o)))

    g.commit()


def load_influenza_na(g: ConjunctiveGraph, filename: str) -> None:
    with open(filename, "r") as f:
        field = dict()
        for row in f.readlines():
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
            g.add((gb_uid, P.is_a, O.gb))
            g.add((gb_uid, P.name, Literal(field["gb"])))
            g.add((gb_uid, P.segment, Literal(field["segment"])))
            g.add((gb_uid, P.encodes, Literal(flu.SEGMENT[int(els[2]) - 1])))
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
                g.add((strain_uid, P.is_a, O.strain))
                g.add((strain_uid, P.name, Literal(strain)))

                barcode_match = re.search(BARCODE_PAT, strain)
                if barcode_match:
                    barcode_name = barcode_match.group(0)
                    barcode_uid = make_uri(barcode_name)
                    g.add((strain_uid, P.xref, barcode_uid))
                    g.add((barcode_uid, P.xref, strain_uid))
                    g.add((barcode_uid, P.is_a, O.barcode))
                    g.add((barcode_uid, P.name, Literal(barcode_uid)))

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
