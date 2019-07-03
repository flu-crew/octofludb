import parsec

import src.parser as parser
import src.util as U
from rdflib import Literal
from src.hash import chksum
from src.nomenclature import P, O, make_uri, make_literal

fastaHeaderFieldParsers = (
    # strain ids
    ("A0", parser.p_A0),
    ("tosu", parser.p_tosu),
    ("gisaid_isolate", parser.p_gisaid_isolate),
    ("strain", parser.p_strain),
    # sequence ids
    ("gb", parser.p_gb),
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
        parsec.sepBy1(parsec.regex("[^>\n]*"), sep=parsec.regex("[\r\n\t ]+")).parsecmap(U.concat)
        << parsec.spaces()
    )
    p_entry = p_header + p_seq
    p_fasta = parsec.many1(p_entry)

    with open(filename, "r") as f:
        entries = p_fasta.parse(f.read())
        row = (h.split(sep) + [q] for (h, q) in entries)
        return parser.resolve(parser.guess_fields(row, parserSet=fastaHeaderFieldParsers))

def print_fasta(fields, tag=None, sep="|"):
    if tag:
        tag += sep
    else:
        tag = ""
    for entry in fields:
        header = sep.join(
            (
                f"{str(entry[i][0])}={str(entry[i][1])}"
                for i in range(len(entry) - 1)
            )
        )
        seq = entry[-1][1]
        print(">" + tag + header)
        print(seq)

def graph_fasta(g, fieldss, tag=None):
  # - Create foaf:name links as needed, munging as needed
  fastaName = {
      "A0": U.upper,
      "tosu": U.upper,
      "gb": U.upper,
      "strain": U.compose(U.strip, U.underscore),
      "gisaid_seqid": U.upper,
  }

  # - If no strain ID exists, create a new one
  # - Link strain ID to each strain property
  # - Link segment ID to each segment property
  fastaRelationSets = [
      parser.RelationSet (
          {"strain", "A0", "tosu", "gisaid_isolate"},
          {
              "global_clade" : P.global_clade,
              "constellation" : P.constellation,
              "host" : P.host,
              "date" : P.date,
              "state" : P.state,
              "country" : P.country,
              "subtype" : P.subtype,
              "gb" : P.hasPart,
              "gisaid_seqid" : P.hasPart,
              "dnaseq" : P.hasPart,
          },
          {},
          {
              "global_clade" : Literal,
              "constellation" : Literal,
              "host" : Literal,
              "date" : make_literal, 
              "state" : Literal,
              "country" : Literal,
              "subtype" : Literal,
              "gb" : make_uri,
              "gisaid_seqid" : make_uri,
              "dnaseq" : U.compose(make_uri, chksum),
          },
          "unknown_strain",
      ),
      parser.RelationSet (
          {"gb", "gisaid_seqid"},
          {
              "segment_name" : P.segment_name,
              "segment_number" : P.segment_number,
              "proseq" : P.proseq,
              "dnaseq" : P.dnaseq,
              "unknown" : P.unknown_unknown
          },
          {"dnaseq" : ("md5", U.compose(make_uri, chksum))},
          {
              "segment_name" : Literal,
              "segment_number" : Literal,
              "proseq" : Literal,
              "dnaseq" : Literal,
              "unknown" : Literal
          },
          "unknown_sequence"
      ),
  ]

  # - Specify is_a relationships
  fastaIsaMap = {
      "A0": O.strain,
      "tosu": O.strain,
      "gisaid_isolate": O.strain,
      "strain": O.strain,
      "gb": O.sequence,
      "gisaid_seqid": O.sequence,
      "unknown_strain": O.sequence,
      "unknown_sequence": O.sequence,
  }

  fastaMungeMap = {"date": make_literal, "host": U.lower}

  def generateChksums(g, fields):
      for (t,v) in fields:
          if t == "proseq":
              uri = make_uri(chksum(v))
              g.add((uri, P.is_a, O.proseq))
              for (t2,v2) in fields:
                  if t2 in {"gb", "gisaid_seqid"}:
                      g.add((make_uri(v2), P.hasPart, uri))
          if t == "dnaseq":
              uri = make_uri(chksum(v))
              g.add((uri, P.is_a, O.dnaseq))
              for (t2,v2) in fields:
                  if t2 in {"gb", "gisaid_seqid"}:
                      g.add((make_uri(v2), P.sameAs, uri))


  # - Generate additional triples
  fastaGenerateAdditional = [generateChksums]

  fluRdfBuilder = parser.RdfBuilder(
      make_name=fastaName,
      relation_sets=fastaRelationSets,
      isa_map=fastaIsaMap,
      munge_map=fastaMungeMap,
      sub_builders=fastaGenerateAdditional,
      unknown_tag="unknown",
      tag=tag
  )

  fluRdfBuilder.build(g, fieldss)
  g.commit()
