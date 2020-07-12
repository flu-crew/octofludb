import sys
from rdflib import Literal
import pandas as pd
import octofludb.classes as classes
import octofludb.classifiers.flucrew as flu
import octofludb.token as tok
import octofludb.domain.identifier as identifier
import parsec
from octofludb.nomenclature import P, O, make_uri, make_tag_uri
from octofludb.util import log, file_str
import re
from tqdm import tqdm
import datetime as datetime


def mk_blast(g, filehandle, tag=None):
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


def mk_influenza_na(g, filehandle) -> None:
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


def mk_ird(g, filehandle) -> None:
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
                    flu.Unknown(
                        els[7].replace("IRD:", "").lower(),
                        field_name="host",
                        na_str=na_str,
                    ),
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


def mk_gis(g, filehandle) -> None:
    fh = pd.read_excel(filehandle.name, sheet_name=0)
    d = {c: [x for x in fh[c]] for c in fh}
    epipat = re.compile(" *\|.*")
    for i in tqdm(range(len(d["Isolate_Id"]))):
        try:
            epi_isl_id_tok = flu.Isolate(d["Isolate_Id"][i])

            # remove the parenthesized garbage following the strain name
            strain_clean = identifier.p_strain.parse(d["Isolate_Name"][i])
            # don't use Strain token here, to avoid double linking
            strain_tok = flu.Unknown(strain_clean, field_name="strain_name")
            # and keep the full strain name, even if ugly
            full_strain_name_tok = flu.Unknown(
                d["Isolate_Name"][i], field_name="gisaid_strain_name"
            )

            host_tok = flu.Host(d["Host"][i], field_name="host")
            subtype_tok = flu.Subtype(d["Subtype"][i])
            lineage_tok = tok.Unknown(
                d["Lineage"][i], field_name="lineage", na_str=["", None]
            )
            try:
                country_tok = flu.Country(d["Location"][i].split(" / ")[1])
            except:
                country_tok = flu.Country(None)
            date_tok = flu.Date(d["Collection_Date"][i], field_name="collection_date")
            try:
                submission_date_tok = flu.Date(
                    d["Submission_Date"][i], field_name="submission_date"
                )
            except:
                submission_date_tok = flu.Date(None, field_name="submission_date")
            for segment in ("PB2", "PB1", "PA", "HA", "NP", "NA", "MP", "NS"):
                segment_tok = flu.SegmentName(segment)
                try:
                    epi_ids = [
                        re.sub(epipat, "", x)
                        for x in d[segment + " Segment_Id"][i].split(",")
                    ]
                except:
                    continue
                try:
                    gbk_ids = d[segment + " INSDC_Upload"][i].split(",")
                except:
                    gbk_ids = [None]
                for (epi_id, gbk_id) in zip(epi_ids, gbk_ids):
                    classes.Phrase(
                        [
                            epi_isl_id_tok,
                            flu.EpiSeqid(epi_id),
                            flu.Genbank(gbk_id),
                            strain_tok,
                            full_strain_name_tok,
                            segment_tok,
                            subtype_tok,
                            lineage_tok,
                            host_tok,
                            country_tok,
                            date_tok,
                            submission_date_tok,
                        ]
                    ).connect(g)
        except IndexError:
            log("Bad line - index error")
            for name, col in d.items():
                log(name + " : " + str(col[i]))
            sys.exit(1)
        except KeyError as e:
            log("This does not appear to be a valid gisaid metadata file")
            log(str(e))
            sys.exit(1)
        except:
            log("Bad line - other error")
            for name, col in d.items():
                log(name + " : " + str(col[i]))
