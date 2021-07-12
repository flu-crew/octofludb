import sys
from rdflib import Literal
import pandas as pd
import octofludb.classes as classes
from octofludb.colors import bad
import octofludb.classifiers.flucrew as flu
import octofludb.token as tok
import octofludb.domain.identifier as identifier
import parsec
from octofludb.nomenclature import P, O, make_uri, make_tag_uri
from octofludb.util import log, file_str
import re
import math
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
                    ### I don't need your annotations, I can do my own, thank you very much
                    #  flu.US_Clade(els[13], field_name="us_clade", na_str=na_str),
                    #  flu.GlobalClade(els[14], field_name="gl_clade", na_str=na_str),
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
            subtype_tok = flu.Subtype(d["Subtype"][i], field_name="gisaid_subtype")
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


def default_access(row, field):
    try:
        return row[field]["value"].split("+")
    except:
        return []


def append_add(entry, field, values):
    if len(values) > 0:
        if field in entry:
            for value in values:
                if not value in entry[field]:
                    entry[field].append(value)
        else:
            entry[field] = values
    elif field not in entry:
        entry[field] = []


def quarter_from_date(date):
    year, month = date.split("-")[0:2]
    quarter = str(math.ceil(int(month) / 3))
    return f"{year}Q{quarter}"


def _ustr(s):
    return s.upper().strip()


def _clean_subtype(s):
    try:
        (ha, na) = re.search(".*(H\\d+).*(N\\d+).*", _ustr(s)).groups()
        return ha + na
    except:
        return ""


def _get_subtype(strain, has, nas, gisaid_subtypes, genbank_subtypes):
    # subtype annotations that where either determined in the past or retrieved from epiflu
    gisaid_subtypes = list(
        {_clean_subtype(subtype) for subtype in gisaid_subtypes if len(subtype) > 0}
    )
    # genbank_subtypes annotations from genbank
    genbank_subtypes = list(
        {
            _clean_subtype(genbank_subtype)
            for genbank_subtype in genbank_subtypes
            if len(genbank_subtype) > 0
        }
    )
    # unique ha and na clades from octoFLU
    has = list({_ustr(ha) for ha in has if len(ha) > 0})
    nas = list({_ustr(na) for na in nas if len(na) > 0})

    # good subtype - trust octoFLU more than anything
    if len(nas) == 1 and len(has) == 1:
        subtype = has[0] + nas[0]
    # no subtype found based on HA/NA subtypes, so use genbank subtype field
    elif (
        len(gisaid_subtypes) > 1
        or len(genbank_subtypes) > 1
        or len(nas) > 1
        or len(has) > 1
    ):
        return "mixed"
    else:
        # if we have no octoFLU data
        # prefer genebank data over subtype data (e.g., from epiflu)
        if len(genbank_subtypes) == 1:
            subtype = genbank_subtypes[0]
        elif len(gisaid_subtypes) == 1:
            subtype = gisaid_subtypes[0]
        else:
            subtype = None

    return subtype


def mk_subtypes(results):
    entries = dict()

    for row in results["results"]["bindings"]:
        strain = row["strain_name"]["value"]

        if strain not in entries:
            entry = dict(isolates=set(), ha_subtypes=[], na_subtypes=[], subtypes=[], serotypes=[])
        else:
            entry = entries[strain]

        isolates = entry["isolates"].update([i for i in row["isolates"]["value"].split("+") if i])

        append_add(entry, "genbank_subtypes", default_access(row, "genbank_subtypes"))
        append_add(entry, "gisaid_subtypes", default_access(row, "gisaid_subtypes"))

        maybe_segment_subtype = default_access(row, "segment_subtypes")
        if len(maybe_segment_subtype) == 1:
            segment_subtype = maybe_segment_subtype[0]
            if re.fullmatch("H\d+", segment_subtype):
                append_add(entry, "ha_subtypes", [segment_subtype])
            elif re.fullmatch("N\d+", segment_subtype):
                append_add(entry, "na_subtypes", [segment_subtype])

        entries[strain] = entry

    print("strain_name\tsubtype")
    for strain, entry in entries.items():
        subtype = _get_subtype(
            strain,
            has=entry["ha_subtypes"],
            nas=entry["na_subtypes"],
            gisaid_subtypes=entry["gisaid_subtypes"],
            genbank_subtypes=entry["genbank_subtypes"],
        )
        if subtype:
          print("\t".join([strain, subtype]))
          for isolate in entry["isolates"]:
            print("\t".join([isolate, subtype]))



MASTERLIST_HEADER = [
    "Barcode",
    "Date",
    "Collection_Q",
    "State",
    "Subtype",
    "H_Genbank",
    "N_Genbank",
    "PB2_Genbank",
    "PB1_Genbank",
    "PA_Genbank",
    "NP_Genbank",
    "M_Genbank",
    "NS_Genbank",
    "Strain",
    "US_Clade",
    "GL_Clade",
    "H1",
    "H3",
    "N1",
    "N2",
    "PB2",
    "PB1",
    "PA",
    "NP",
    "M",
    "NS",
    "Constellation",
    "Motif",
    "Sa_Motif",
    "Sb_Motif",
    "Ca1_Motif",
    "Ca2_Motif",
    "Cb_Motif",
]


def mk_masterlist(results):
    entries = dict()

    for row in results["results"]["bindings"]:
        barcode = row["barcode"]["value"]
        if barcode in entries:
            entry = entries[barcode]
        else:
            entry = dict()
            # initialize fields
            for field in MASTERLIST_HEADER:
                entry[field] = []

        gb = row["genbank_id"]["value"]
        segment = row["segment"]["value"]

        genbank_id = default_access(row, "genbank_id")[0]
        segment = default_access(row, "segment")[0]
        subtype = default_access(row, "subtypes")[0]
        # Use the earliest date since occasionally people resequence a sample
        # and incorrectly set the sequence date to the collection date (among
        # other issues)
        date = default_access(row, "earliest_date")[0]
        states = default_access(row, "states")
        strains = default_access(row, "strains")
        us_clades = default_access(row, "us_clades")
        gl_clades = default_access(row, "gl_clades")
        consts = default_access(row, "consts")
        h3_motifs = default_access(row, "h3_motifs")
        sa_motifs = default_access(row, "sa_motifs")
        sb_motifs = default_access(row, "sb_motifs")
        ca1_motifs = default_access(row, "ca1_motifs")
        ca2_motifs = default_access(row, "ca2_motifs")
        cb_motifs = default_access(row, "cb_motifs")

        append_add(entry, "Date", [date])
        append_add(entry, "Collection_Q", [quarter_from_date(date)])
        append_add(entry, "State", states)

        if segment == "HA":
            append_add(entry, "H_Genbank", [genbank_id])
            append_add(entry, "US_Clade", us_clades)
            append_add(entry, "GL_Clade", gl_clades)
        elif segment == "NA":
            append_add(entry, "N_Genbank", [genbank_id])
            append_add(entry, segment, us_clades)
        else:
            append_add(entry, segment + "_Genbank", [genbank_id])
            append_add(entry, segment, us_clades)

        maybe_segment_subtype = default_access(row, "segment_subtypes")
        if maybe_segment_subtype:
            segment_subtype = maybe_segment_subtype[0]

            if segment_subtype == "H1":
                append_add(entry, "H1", us_clades)
            elif segment_subtype == "H3":
                append_add(entry, "H3", us_clades)

            if segment_subtype == "N1":
                append_add(entry, "N1", us_clades)
            elif segment_subtype == "N2":
                append_add(entry, "N2", us_clades)

        append_add(entry, "Strain", strains)
        append_add(entry, "Subtype", [subtype])
        append_add(entry, "Constellation", consts)
        append_add(entry, "Motif", h3_motifs)
        append_add(entry, "Sa_Motif", sa_motifs)
        append_add(entry, "Sb_Motif", sb_motifs)
        append_add(entry, "Ca1_Motif", ca1_motifs)
        append_add(entry, "Ca2_Motif", ca2_motifs)
        append_add(entry, "Cb_Motif", cb_motifs)

        entries[barcode] = entry

    print("\t".join(MASTERLIST_HEADER))

    for barcode, entry in entries.items():
        entry["Barcode"] = [barcode]
        row = [",".join([f for f in entry[field] if f]) for field in MASTERLIST_HEADER]
        print("\t".join(row))


class IrregularStrain(flu.StrainToken):
    """
    Matches anything and treats it as a strain.

    This is useful when you want to force a field to refer to a strain, such as
    when you are loading unpublished data that use idiosyncratic identifiers.
    """

    typename = "strain_id"
    parser = parsec.regex(".+")


class IrregularFasta(classes.Ragged):
    """
    Load a FASTA file where the first field is treated as a strain identifier.
    """

    def cast(self, data):
        strain_ids = [IrregularStrain(d[0]) for d in data]
        phrases = super().cast([d[1:] for d in data])
        for i in range(len(strain_ids)):
            phrases[i].tokens.append(strain_ids[i])
        return phrases

    def connect(self, g):
        for phrase in self.data:
            for token in phrase.tokens:
                if token.group == "sequence":
                    g.add((token.as_uri(), P.tag, make_tag_uri("unpublished")))
        super().connect(g)


class IrregularSegment(flu.SegmentToken):
    """
    Matches anything and treats it as a segment.

    Also see IrregularStrain
    """

    typename = None
    parser = parsec.regex(".+")


class IrregularSegmentTable(classes.Table):
    """
    Load a table; where the kth field is treated as a segment identifier.
    """

    def cast(self, data):
        segment_ids = data[self.header[0]]
        del data[self.header[0]]
        phrases = super().cast(data)
        for i in range(len(segment_ids)):
            phrases[i].tokens.append(IrregularSegment(segment_ids[i]))
        return phrases
