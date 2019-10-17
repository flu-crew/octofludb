import sys
from rdflib import Literal
import src.classes as classes
import src.classifiers.flucrew as flu
import src.token as tok
from src.nomenclature import P, O, make_uri, make_tag_uri
from src.util import log, file_str
import re
from tqdm import tqdm
import datetime as datetime


def load_blast(g, filehandle, tag=None):
    timestr = datetime.datetime.now()
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

        huid = make_uri(f"blast/{qseqid}-{sseqid}-{bitscore}")

        if tag:
            taguri = make_tag_uri(tag)
            g.add((taguri, P.name, Literal(tag)))
            g.add((taguri, P.time, Literal(timestr)))
            g.add((taguri, P.file, Literal(file_str(filehandle))))
            g.add((huid, P.tag, taguri))

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


def load_influenza_na(g, filehandle) -> None:
    def extract_strain(x):
        strain_pat = re.compile("[ABCD]/[^()\[\]]+")
        m = re.search(strain_pat, x)
        if m:
            return m.group(0)
        else:
            return None

    for line in tqdm(filehandle.readlines()):
        els = line.split("\t")
        try:
            classes.Phrase(
                [
                    flu.Genbank(els[0]),
                    tok.Unknown(els[1].lower(), field_name="host"),
                    flu.SegmentNumber(els[2]),
                    flu.Subtype(els[3]),
                    flu.Country(els[4]),
                    flu.Date(els[5]),
                    tok.Integer(els[6].lower(), field_name="length"),
                    flu.Strain(extract_strain(els[7])),
                    # skip 8
                    # skip 9
                    tok.Unknown(els[10].strip(), field_name="genome_status"),
                ]
            ).connect(g)
        except IndexError:
            log(line)
            sys.exit(1)

def load_ird(g, filehandle) -> None:
    na_str = "-N/A-"
    for line in tqdm(filehandle.readlines()):
        els = line.split("\t")
        try:
            classes.Phrase(
                [
                    flu.SegmentNumber(els[0], na_str=na_str),
                    # skip protein name
                    flu.Genbank(els[2], field_name="genbank_id", na_str=na_str),
                    # skip complete genome
                    tok.Integer(els[4], field_name="length", na_str=na_str),
                    flu.Subtype(els[5], na_str=na_str),
                    flu.Date(els[6], na_str=na_str),
                    flu.Unknown(els[7].replace("IRD:", "").lower(), field_name="host", na_str=na_str),
                    flu.Country(els[8]),
                    # ignore state - can parse it from strain name
                    tok.Unknown(els[10], field_name="flu_season", na_str=na_str),
                    flu.Strain(els[11], field_name="strain_name", na_str=na_str),
                    # curation report - hard pass
                    flu.US_Clade(els[13], field_name="us_clade", na_str=na_str),
                    flu.GlobalClade(els[14], field_name="gl_clade", na_str=na_str),
                ]
            ).connect(g)
        except IndexError:
            log(line)
            sys.exit(1)
