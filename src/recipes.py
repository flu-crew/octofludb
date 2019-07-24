import sys
import math
from rdflib import ConjunctiveGraph, Literal
import src.domain.flu as flu
import src.domain.geography as geo
import src.classes as classes
from src.nomenclature import (
    P,
    O,
    uidgen,
    make_uri,
    make_date,
    make_literal,
    make_property,
    make_usa_state_uri,
    make_country_uri,
)
from src.util import replace, fixLookup, make_maybe_add, rmNone, log, file_str
import src.parser as p
import src.entrez as entrez
import re
import pandas as pd
from tqdm import tqdm

# TODO: replace these with parsers

STRAIN_PAT = re.compile("[ABCD]/[^()\[\]]+")
BARCODE_PAT = re.compile("A0\d{7}|\d+TOSU\d+|EPI_ISL_\d+")


def load_blast(g, filehandle, tag=None):
    igen = uidgen(base=f"blast/{file_str(filehandle)}", pad=0)

    for row in tqdm(filehandle.readlines()):
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
        #  g.add((huid, P.mismatch, Literal(int(mismatch))))
        #  g.add((huid, P.gapopen, Literal(int(gapopen))))
        #  g.add((huid, P.qstart, Literal(int(qstart))))
        #  g.add((huid, P.qend, Literal(int(qend))))
        #  g.add((huid, P.sstart, Literal(int(sstart))))
        #  g.add((huid, P.send, Literal(int(send))))
        #  g.add((huid, P.evalue, Literal(float(evalue))))
        #  g.add((huid, P.bitscore, Literal(float(bitscore))))

    g.commit()


def load_influenza_na(g, filehandle) -> None:
    field = dict()
    for (i, row) in enumerate(tqdm(filehandle.readlines())):
        process_influenza_row(g, row)
        if i % 1000:
            g.commit()
    g.commit()


def process_influenza_row(g: ConjunctiveGraph, line: dict) -> None:
    els = line.split("\t")
    field = dict()
    try:
        field["gb"] = els[0]
        field["host"] = els[1]
        field["segment"] = els[2]
        field["country"] = els[4]
        field["date"] = els[5]
        is_complete = els[10].strip() == "c"
    except IndexError:
        log(
            f"Expected 11 columns, found only {len(els)}. This is unexpected and a frightening."
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
    if not strain_match:
        log(f'  could not parse strain: {"|".join(els)}', end="")
        return None
    else:
        # yes, sometimes they end in space
        strain = strain_match.group(0).strip()

        strain_uid = make_uri(strain)
        maybe_add = make_maybe_add(g, field, strain_uid)
        g.add((strain_uid, P.has_segment, gb_uid))
        # This field stores an unambiguous link to the Genbank ID. gb_uid is
        # SameAs with the sequence checksum, thus creating a many strains to
        # one Genbank sitution. has_genbank can resolve these duplicates.
        g.add((strain_uid, P.has_genbank, Literal(field["gb"])))
        g.add((strain_uid, P.strain_name, Literal(strain)))

        barcode_match = re.search(BARCODE_PAT, strain)
        if barcode_match:
            barcode_name = barcode_match.group(0)
            barcode_uid = make_uri(barcode_name)
            g.add((strain_uid, P.barcode, Literal(barcode_name)))
            g.add((barcode_uid, P.sameAs, strain_uid))

        # some entries do not have countries associated
        if field["country"]:
            (country_uri, alt_name) = make_country_uri(field["country"])
            g.add((strain_uid, P.country, country_uri))
            if alt_name:
                # The alternative name is used only if the given name is not recognized
                g.add((strain_uid, P.country_name, Literal(alt_name)))

        maybe_add = make_maybe_add(g, field, strain_uid)
        maybe_add(P.host, "host")

        if field["date"]:
            date = make_date(field["date"])
            if date:
                g.add((strain_uid, P.date, date))
