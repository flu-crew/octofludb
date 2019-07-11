import parsec

import src.parser as parser
import src.util as U
from rdflib import Literal
from src.hash import chksum
from src.nomenclature import P, O, make_uri, make_literal, make_usa_state_uri, make_country_uri, make_date
from tqdm import tqdm

fastaHeaderFieldParsers = (
    # strain ids
    ("A0", parser.p_A0),
    ("tosu", parser.p_tosu),
    ("gisaid_isolate", parser.p_gisaid_isolate),
    ("strain_name", parser.p_strain),
    # sequence ids
    ("genbank_id", parser.p_gb),
    ("gisaid_seqid", parser.p_gisaid_seqid),
    # other flu info
    ("global_clade", parser.p_global_clade),
    ("constellation", parser.p_constellation),
    #
    ("host", parser.p_host),
    ("date", parser.p_date.parsecmap(str)),
    ("subtype", parser.p_HANA),
    ("segment_name", parser.p_segment),
    ("state", parser.p_usa_state),  # Pennslyvania (PA) conflicts with the segment PA
    ("country", parser.p_country),  # country Turkey conflicts with the host
    ("segment_number", parser.p_segment_number),
    ("dnaseq", parser.p_dnaseq),
    ("proseq", parser.p_proseq),
)


def parse_fasta(filename, sep="|"):
    p_header = parsec.string(">") >> parsec.regex(".*") << parsec.spaces()
    p_seq = (
        parsec.sepBy1(
            parsec.regex("[^>\n]*"), sep=parsec.regex("[\r\n\t ]+")
        ).parsecmap(U.concat)
        << parsec.spaces()
    )
    p_entry = p_header + p_seq
    p_fasta = parsec.many1(p_entry)

    with open(filename, "r") as f:
        entries = p_fasta.parse(f.read())
        row = (h.split(sep) + [q] for (h, q) in entries)
        return parser.resolve(
            parser.guess_fields(row, parserSet=fastaHeaderFieldParsers)
        )


def print_fasta(fields, tag=None, sep="|"):
    if tag:
        tag += sep
    else:
        tag = ""
    for entry in fields:
        header = sep.join(
            (f"{str(entry[i][0])}={str(entry[i][1])}" for i in range(len(entry) - 1))
        )
        seq = entry[-1][1]
        print(">" + tag + header)
        print(seq)


def graph_fasta(g, fieldss, tag=None):
    # - If no strain ID exists, create a new one
    # - Link strain ID to each strain property
    # - Link segment ID to each segment property
    fastaRelationSets = [
        parser.RelationSet(
            subjects={"strain_name", "A0", "tosu", "gisaid_isolate"},
            relations={
                "global_clade": P.global_clade,
                "constellation": P.constellation,
                "host": P.host,
                "date": P.date,
                "state": P.state,
                "country": P.country,
                "subtype": P.subtype,
                "genbank_id": P.has_segment,
                "gisaid_seqid": P.has_segment,
                "dnaseq": P.has_segment,
            },
            generators={},
            objectifier={
                "global_clade": Literal,
                "constellation": Literal,
                "host": Literal,
                "date": make_date,
                "state": make_usa_state_uri,
                "country": U.compose(lambda x: x[0], make_country_uri),
                "subtype": Literal,
                "genbank_id": make_uri,
                "gisaid_seqid": make_uri,
                "dnaseq": U.compose(make_uri, chksum),
            },
            default="unknown_strain",
        ),
        parser.RelationSet(
            subjects={"genbank_id", "gisaid_seqid"},
            relations={
                "segment_name": P.segment_name,
                "segment_number": P.segment_number,
                "proseq": P.proseq,
                "dnaseq": P.dnaseq,
                "unknown": P.unknown_unknown,
            },
            generators={"dnaseq": ("chksum", U.compose(make_uri, chksum))},
            objectifier={
                "segment_name": Literal,
                "segment_number": Literal,
                "proseq": Literal,
                "dnaseq": Literal,
                "unknown": Literal,
            },
            default="unknown_sequence",
        ),
    ]

    fastaMungeMap = {"date": make_literal, "host": U.lower}

    def generateChksums(g, fields):
        for (t, v) in fields:
            if t == "proseq":
                # use the chksum of the protein sequence as a URI
                uri = make_uri(chksum(v))
                for (t2, v2) in fields:
                    if t2 in {"genbank_id", "gisaid_seqid"}:
                        # link the segment ids to the protein feature
                        g.add((make_uri(v2), P.has_feature, uri))
                        # link the protein feature to the protein sequence
                        g.add((uri, P.proseq, Literal(v)))
            if t == "dnaseq":
                uri = make_uri(chksum(v))
                for (t2, v2) in fields:
                    if t2 in {"genbank_id", "gisaid_seqid"}:
                        g.add((make_uri(v2), P.sameAs, uri))

    # - Generate additional triples
    fastaGenerateAdditional = [generateChksums]

    fluRdfBuilder = parser.RdfBuilder(
        relation_sets=fastaRelationSets,
        munge_map=fastaMungeMap,
        sub_builders=fastaGenerateAdditional,
        unknown_tag="unknown",
        tag=tag,
    )

    fluRdfBuilder.build(g, fieldss)
    g.commit()
